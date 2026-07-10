#!/usr/bin/env python3
"""
test_codegen.py -- regression test for the PAC constraint code generator.

WHAT THIS GUARDS
----------------
Make sure that changes to ``rust_codegen.py`` (or to the shared schema in
``defs.py``) do not silently break the generated Rust. There are two tests:

  1. GOLDEN DIFF (fast, no toolchain) -- ``test_codegen_matches_golden``
     Regenerate the constraints module from
     ``constraint_test/stm32f405_i2c1.json`` and diff it, line for line, against
     the committed golden ``constraint_test/i2c1_expected_constraints.rs``. A
     mismatch means the code generator's output changed: review the printed diff
     and, if the change was intentional, refresh the golden (see that file's
     header for the one-line command).

  2. COMPILE CHECK (needs cargo + a generated PAC) -- ``test_constraint_test_compiles``
     Inject the generated module into the vendored ``stm32f4`` PAC and ``cargo
     check`` the ``constraint_test`` crate, whose ``main.rs`` exercises only the
     token-bearing (legal) access paths. A clean check proves the generated code
     is real, type-correct Rust. The two PAC source files that injection mutates
     are backed up first and restored in a ``finally``; the test then asserts the
     PAC crate was left byte-for-byte as it started.

  3. ENFORCEMENT CHECK (needs cargo + a generated PAC) -- ``test_unconstrained_operations_fail_to_compile``
     Inject, then ``cargo check`` every ordinary write-capable CR1 operation
     WITHOUT the composite proof, and assert rejection with E0061.
     This proves the constraint is actually enforced, not merely that legal code
     compiles. The PAC and the swapped-in ``main.rs`` are restored and checked,
     exactly as above.

  Why ``cargo check`` and not ``cargo build``: the constraint enforcement is a
  front-end type/argument error, which ``cargo check`` reports without codegen. A
  full ``cargo build`` would try to generate code for the Cortex-M PAC against the
  host target, which fails for unrelated reasons (e.g. mach-o vector-table
  sections on macOS). ``cargo check`` is also much faster.

  NOTE: the ``stm32f4`` crate source (``generic.rs``, the device modules) is a
  *generated* svd2rust artifact that the ``stm32-rs`` submodule does NOT ship.
  Fetching the submodule alone is therefore not enough -- the PAC must already
  have been generated on disk. When it (or cargo) is absent, the two checks above
  SKIP rather than fail, so the suite still passes on a fresh clone.

Run directly (``python test_codegen.py``) or under pytest.
"""

import difflib
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# This application's directory: applications/pac_codegen/
APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(REPO_ROOT))

from defs import RegisterInfo
from rust_codegen import generate_constraint_module, normalize_constraints

RUST_CODEGEN = APP_DIR / "rust_codegen.py"
CRATE_DIR = APP_DIR / "constraint_test"
FIXTURE = CRATE_DIR / "stm32f405_i2c1.json"
GOLDEN = CRATE_DIR / "i2c1_expected_constraints.rs"

# The generated stm32f4 PAC (only present once the submodule is fetched AND the
# crate has been generated via svd2rust). Injection mutates exactly these two
# files.
PAC_SRC = APP_DIR / "vendored" / "stm32-rs" / "stm32f4" / "src"
PAC_GENERIC = PAC_SRC / "generic.rs"
PAC_MODRS = PAC_SRC / "stm32f405" / "mod.rs"

PERIPHERAL = "i2c1"

# Separates the human-readable header in the golden file from the bytes that must
# match rust_codegen.py output. Appears on its own line, exactly once.
GOLDEN_MARKER = "//@@LIDAR-GOLDEN-GENERATED@@"


# --------------------------------------------------------------------------- #
# Test 1: golden diff
# --------------------------------------------------------------------------- #

def _generate_standalone(out_path: Path) -> None:
    """Run rust_codegen.py in standalone mode, writing the module to out_path."""
    subprocess.run(
        [sys.executable, str(RUST_CODEGEN), str(FIXTURE),
         "--peripheral", PERIPHERAL, "--output", str(out_path)],
        check=True, capture_output=True, text=True,
    )


def _golden_generated_section() -> str:
    """Return the golden file's content below the marker line (the part that must
    match rust_codegen.py's output). The header above the marker is ignored."""
    lines = GOLDEN.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.strip() == GOLDEN_MARKER:
            return "\n".join(lines[i + 1:])
    raise AssertionError(
        f"Golden file {GOLDEN.name} is missing its marker line "
        f"'{GOLDEN_MARKER}'."
    )


def test_codegen_matches_golden():
    """Generated constraints must match the committed golden, line for line."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "constraints.rs"
        _generate_standalone(out)
        generated = out.read_text()

    expected = _golden_generated_section()
    if generated.splitlines() != expected.splitlines():
        diff = "\n".join(difflib.unified_diff(
            expected.splitlines(), generated.splitlines(),
            fromfile=f"{GOLDEN.name} (expected)",
            tofile="rust_codegen.py output (actual)",
            lineterm="",
        ))
        raise AssertionError(
            "Generated codegen output no longer matches the golden "
            f"{GOLDEN.name}. If this change is intentional, refresh the golden's "
            "generated section (see its header).\n\n" + diff
        )


def _synthetic_constraint(
    preconditions: list[tuple[str, str]],
    *,
    target_fields: list[str] | None = None,
    text: str = "Synthetic trusted constraint",
) -> dict:
    return {
        "target_register": "CTRL",
        "target_fields": target_fields or [],
        "target_operation": "write",
        "preconditions": [
            {
                "register_name": "CTRL",
                "field_name": field,
                "required_state": state,
            }
            for field, state in preconditions
        ],
        "postconditions": [],
        "severity": "error",
        "consequence": "Synthetic test consequence",
        "datasheet_text": text,
    }


def _synthetic_register(constraints: list[dict]) -> RegisterInfo:
    return RegisterInfo(
        datasheet_register_abbreviation="CTRL",
        address_offset="0x00",
        reset_value="0x00",
        size=32,
        subfields=[],
        access_constraints=constraints,
    )


def test_synthetic_constraint_matrix():
    """Exercise every state and normalization variation supported in Step 1."""
    empty = generate_constraint_module(_synthetic_register([]), "fake")
    assert "No access constraints defined for this register" in empty

    single = generate_constraint_module(
        _synthetic_register(
            [_synthetic_constraint([("READY", "set")])]
        ),
        "fake",
    )
    assert single.count("pub fn write<F>") == 1
    assert "r.ready().bit_is_set()" in single

    register = _synthetic_register(
        [
            _synthetic_constraint(
                [("BUSY", "cleared"), ("ENABLED", "set")],
                target_fields=["DATA"],
                text="First write rule",
            ),
            _synthetic_constraint(
                [("BUSY", "cleared"), ("MODE", "equals:0x3")],
                text="Second write rule",
            ),
        ]
    )
    plans = normalize_constraints(register)
    assert len(plans) == 1
    assert plans[0].target_fields == ["DATA"]
    assert [
        (pre.field_name, pre.required_state)
        for pre in plans[0].preconditions
    ] == [
        ("BUSY", "cleared"),
        ("ENABLED", "set"),
        ("MODE", "equals:0x3"),
    ]

    generated = generate_constraint_module(register, "fake")
    assert generated.count("impl crate::ConstrainedReg") == 1
    assert generated.count("pub fn write<F>") == 1
    assert generated.count("pub struct CtrlWriteReady(())") == 1
    proof_section = generated.split("// === Composite Proof ===", 1)[1].split(
        "// === Error Type ===",
        1,
    )[0]
    assert "#[derive" not in proof_section
    assert "r.busy().bit_is_clear()" in generated
    assert "r.enabled().bit_is_set()" in generated
    assert "r.mode().bits() == 0x3" in generated
    assert "pub fn verify_write_ready(&self)" in generated
    assert (
        "pub unsafe fn bypass_constraints(&self) -> "
        "&crate::Reg<super::ctrl::CTRLrs>"
    ) in generated
    assert "verify_enabled_set" not in generated
    assert "verify_mode_equals" not in generated
    for signature in (
        "pub fn write<F>",
        "pub fn modify<F>",
        "pub fn reset(",
        "pub fn write_with_zero<F>",
        "pub fn from_write<F, T>",
        "pub fn from_modify<F, T>",
    ):
        assert generated.count(signature) == 1
    assert "First write rule" in generated
    assert "Second write rule" in generated
    assert generated == generate_constraint_module(register, "fake")


# --------------------------------------------------------------------------- #
# Test 2: compile test (inject -> cargo build -> restore)
# --------------------------------------------------------------------------- #

def _cargo_available() -> bool:
    return shutil.which("cargo") is not None


def _pac_generated() -> bool:
    """True only if the *generated* stm32f4 crate source is on disk. The stm32-rs
    submodule does not ship these files, so a bare fetch is not enough."""
    return PAC_GENERIC.is_file() and PAC_MODRS.is_file()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_constraint_test_compiles():
    """Inject into the PAC, build constraint_test, then restore the PAC.

    Skips (does not fail) unless both cargo and a generated stm32f4 PAC are
    available.
    """
    if not _cargo_available():
        print("SKIP test_constraint_test_compiles: cargo not on PATH")
        return
    if not _pac_generated():
        print("SKIP test_constraint_test_compiles: generated stm32f4 PAC not "
              f"found under {PAC_SRC} (fetch the submodule and generate the PAC).")
        return

    # Capture the pristine bytes of the only two files injection touches.
    orig_generic = PAC_GENERIC.read_bytes()
    orig_modrs = PAC_MODRS.read_bytes()
    sha_generic_before = _sha(PAC_GENERIC)
    sha_modrs_before = _sha(PAC_MODRS)

    build_ok = False
    detail = ""
    try:
        inject = subprocess.run(
            [sys.executable, str(RUST_CODEGEN), str(FIXTURE),
             "--peripheral", PERIPHERAL, "--inject", str(PAC_MODRS)],
            capture_output=True, text=True,
        )
        if inject.returncode != 0:
            detail = "injection failed:\n" + inject.stdout + inject.stderr
        else:
            # cargo check (front-end only): the constraint enforcement is a type
            # error, so a check is enough; a full build would codegen the
            # Cortex-M PAC for the host and fail for unrelated target reasons.
            check = subprocess.run(
                ["cargo", "check"], cwd=str(CRATE_DIR),
                capture_output=True, text=True,
            )
            build_ok = check.returncode == 0
            if not build_ok:
                detail = "cargo check failed:\n" + check.stdout + check.stderr
    except Exception as exc:  # never leave the PAC mutated on an unexpected error
        detail = f"unexpected error during inject/build: {exc!r}"
    finally:
        # Always restore the PAC to its pre-test state.
        PAC_GENERIC.write_bytes(orig_generic)
        PAC_MODRS.write_bytes(orig_modrs)

    # Restore check: the original PAC crate must be back to byte-for-byte what it
    # was before the test ran. This runs whether or not the build succeeded.
    generic_restored = _sha(PAC_GENERIC) == sha_generic_before
    modrs_restored = _sha(PAC_MODRS) == sha_modrs_before
    assert generic_restored and modrs_restored, (
        "PAC crate was NOT restored after the test -- it has been left modified.\n"
        f"  {PAC_GENERIC}: restored={generic_restored}\n"
        f"  {PAC_MODRS}: restored={modrs_restored}"
    )

    # Compile result (reported after the restore check so a build failure never
    # leaves the PAC dirty).
    assert build_ok, detail


# --------------------------------------------------------------------------- #
# Test 3: enforcement (illegal program must NOT compile)
# --------------------------------------------------------------------------- #

# Illegal program: writes CR1 without the required composite proof. After
# injection the inherent CR1 write() shadow requires two arguments, so this is
# rejected at type-check time (E0061).
ILLEGAL_MAIN = """\
#![no_std]
#![no_main]
use stm32f4::stm32f405;

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {}
}

#[no_mangle]
pub extern "C" fn main() -> ! {
    let dp = unsafe { stm32f405::Peripherals::steal() };
    let i2c1 = &dp.I2C1;
    // ILLEGAL: write without the required composite proof.
    i2c1.cr1().write(|w| w.pe().enabled());
    loop {}
}
"""

REUSED_PROOF_MAIN = """\
#![no_std]
#![no_main]
use stm32f4::stm32f405;

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {}
}

#[no_mangle]
pub extern "C" fn main() -> ! {
    let dp = unsafe { stm32f405::Peripherals::steal() };
    let i2c1 = &dp.I2C1;
    let proof = i2c1.cr1().verify_write_ready().unwrap();
    i2c1.cr1().write(|w| w.pe().enabled(), proof);
    // ILLEGAL: the non-Copy proof was consumed by the first write.
    i2c1.cr1().write(|w| w.pe().enabled(), proof);
    loop {}
}
"""


def test_unconstrained_operations_fail_to_compile():
    """Proof-less and proof-reusing writes must be rejected by the compiler.

    Proves the constraint is actually enforced -- not merely that legal code
    compiles. Skips under the same conditions as test_constraint_test_compiles.
    """
    if not _cargo_available():
        print("SKIP test_unconstrained_operations_fail_to_compile: cargo not on PATH")
        return
    if not _pac_generated():
        print("SKIP test_unconstrained_operations_fail_to_compile: generated stm32f4 "
              f"PAC not found under {PAC_SRC}.")
        return

    main_rs = CRATE_DIR / "src" / "main.rs"
    orig_generic = PAC_GENERIC.read_bytes()
    orig_modrs = PAC_MODRS.read_bytes()
    orig_main = main_rs.read_bytes()
    sha_before = {p: _sha(p) for p in (PAC_GENERIC, PAC_MODRS, main_rs)}

    checks: list[tuple[str, subprocess.CompletedProcess[str], str]] = []
    detail = ""
    try:
        inject = subprocess.run(
            [sys.executable, str(RUST_CODEGEN), str(FIXTURE),
             "--peripheral", PERIPHERAL, "--inject", str(PAC_MODRS)],
            capture_output=True, text=True,
        )
        if inject.returncode != 0:
            detail = "injection failed:\n" + inject.stdout + inject.stderr
        else:
            illegal_write = "i2c1.cr1().write(|w| w.pe().enabled());"
            for name, source, expected_error in (
                ("token-less write", ILLEGAL_MAIN, "E0061"),
                (
                    "token-less modify",
                    ILLEGAL_MAIN.replace(
                        illegal_write,
                        "i2c1.cr1().modify(|_, w| w.pe().enabled());",
                    ),
                    "E0061",
                ),
                (
                    "token-less reset",
                    ILLEGAL_MAIN.replace(
                        illegal_write,
                        "i2c1.cr1().reset();",
                    ),
                    "E0061",
                ),
                (
                    "token-less write_with_zero",
                    ILLEGAL_MAIN.replace(
                        illegal_write,
                        "i2c1.cr1().write_with_zero(|w| w.pe().enabled());",
                    ),
                    "E0061",
                ),
                (
                    "token-less from_write",
                    ILLEGAL_MAIN.replace(
                        illegal_write,
                        "i2c1.cr1().from_write(|w| { w.pe().enabled(); });",
                    ),
                    "E0061",
                ),
                (
                    "token-less from_modify",
                    ILLEGAL_MAIN.replace(
                        illegal_write,
                        "i2c1.cr1().from_modify(|_, w| { w.pe().enabled(); });",
                    ),
                    "E0061",
                ),
                ("reused proof", REUSED_PROOF_MAIN, "E0382"),
            ):
                main_rs.write_text(source)
                check = subprocess.run(
                    ["cargo", "check"], cwd=str(CRATE_DIR),
                    capture_output=True, text=True,
                )
                checks.append((name, check, expected_error))
    except Exception as exc:  # never leave files mutated on an unexpected error
        detail = f"unexpected error during inject/check: {exc!r}"
    finally:
        # Always restore the PAC and the test's own main.rs.
        PAC_GENERIC.write_bytes(orig_generic)
        PAC_MODRS.write_bytes(orig_modrs)
        main_rs.write_bytes(orig_main)

    # Restore check: PAC crate and main.rs must be back to byte-for-byte pristine.
    for p in (PAC_GENERIC, PAC_MODRS, main_rs):
        assert _sha(p) == sha_before[p], f"{p} was NOT restored after the test."

    assert checks, detail or "constraint injection did not run"
    for name, check, expected_error in checks:
        assert check.returncode != 0, (
            f"{name} compiled -- the composite proof is not enforced"
        )
        output = check.stdout + check.stderr
        assert expected_error in output, (
            f"{name} did not produce expected {expected_error}:\n{output}"
        )


# --------------------------------------------------------------------------- #
# Direct runner (mirrors tests/test_prompt_schema_consistency.py style)
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    tests = [
        test_codegen_matches_golden,
        test_synthetic_constraint_matrix,
        test_constraint_test_compiles,
        test_unconstrained_operations_fail_to_compile,
    ]
    print("Running codegen tests...\n")
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"✓ {t.__name__}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"✗ {t.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
    if failed:
        sys.exit(1)
