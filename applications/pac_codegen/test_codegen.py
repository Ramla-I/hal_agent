#!/usr/bin/env python3
"""test_codegen.py -- regression tests for the trait-gated PAC code generator.

WHAT THIS GUARDS
----------------
Changes to ``rust_codegen.py`` (or the shared schema in ``defs.py``) must not
silently break the generated Rust OR the enforcement it claims. Three layers:

  1. GOLDEN DIFF (fast, no toolchain) -- ``test_codegen_matches_golden``
     Regenerate the constraints module from the fixture and diff it against
     the committed golden. A mismatch means the emitter's output changed:
     review the diff and refresh the golden if intentional (see its header).

  2. LEGAL PATHS COMPILE -- ``test_constraint_test_compiles``
     Inject into the provisioned PAC (get_pac.py) and ``cargo check`` the
     constraint_test crate, whose ``main.rs`` exercises every legal access
     path (witnessed writes, when_ready, escapes, unconstrained registers).

  3. ENFORCEMENT (compile-fail table) -- ``test_illegal_programs_rejected``
     Inject once, then for each adversarial program assert cargo REJECTS it
     with the expected error code AND message substring. The table encodes
     the soundness properties the encoding claims -- including the exact
     bypass that compiled silently under the old shadowing design (PR 15
     defect 2), which must stay a compile error forever.

  The compile tests snapshot generic.rs + the whole device module tree and
  restore them afterward (injection is one-shot from a pristine PAC), then
  verify the restore byte-for-byte.

  Why ``cargo check`` not ``cargo build``: enforcement is a front-end type
  error; a full build would codegen the Cortex-M PAC for the host and fail
  for unrelated target reasons.

  SKIP POLICY: without cargo or the provisioned PAC the compile tests SKIP so
  a fresh clone still passes -- EXCEPT when ``LIDAR_REQUIRE_PAC_TESTS`` is set
  (CI sets it), which turns any would-be skip into a hard failure. Silently
  skipped enforcement tests are how a non-compiling generator once shipped.

Run directly (``python test_codegen.py``) or under pytest.
"""

import difflib
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# This application's directory: applications/pac_codegen/
APP_DIR = Path(__file__).resolve().parent

RUST_CODEGEN = APP_DIR / "rust_codegen.py"
CRATE_DIR = APP_DIR / "constraint_test"
FIXTURE = CRATE_DIR / "stm32f405_i2c1.json"
GOLDEN = CRATE_DIR / "i2c1_expected_constraints.rs"
MAIN_RS = CRATE_DIR / "src" / "main.rs"

# The generated stm32f4 PAC, provisioned from crates.io by get_pac.py.
PAC_ROOT = APP_DIR / "vendored" / "pac" / "stm32f4"
PAC_SRC = PAC_ROOT / "src"
PAC_GENERIC = PAC_SRC / "generic.rs"
DEVICE = "stm32f405"
DEVICE_DIR = PAC_SRC / DEVICE

PERIPHERAL = "i2c1"

# Separates the human-readable header in the golden file from the bytes that
# must match rust_codegen.py output. Appears on its own line, exactly once.
GOLDEN_MARKER = "//@@LIDAR-GOLDEN-GENERATED@@"

# When set (CI does), a compile test that would SKIP fails instead.
REQUIRE_ENV = "LIDAR_REQUIRE_PAC_TESTS"


def _skip(test_name: str, reason: str) -> None:
    """Record a skip -- or fail hard when the CI gate is armed."""
    if os.environ.get(REQUIRE_ENV):
        raise AssertionError(
            f"{test_name} would SKIP ({reason}), but {REQUIRE_ENV} is set: "
            "compile tests are required to run in this environment. "
            "Provision the PAC with `python applications/pac_codegen/get_pac.py`."
        )
    print(f"SKIP {test_name}: {reason}")


# --------------------------------------------------------------------------- #
# Test 1: golden diff
# --------------------------------------------------------------------------- #

def _generate_standalone(out_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(RUST_CODEGEN), str(FIXTURE),
         "--peripheral", PERIPHERAL, "--output", str(out_path)],
        check=True, capture_output=True, text=True,
    )


def _golden_generated_section() -> str:
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
            f"{GOLDEN.name}. If this change is intentional, refresh the "
            "golden's generated section (see its header).\n\n" + diff
        )


# --------------------------------------------------------------------------- #
# Compile-test machinery: snapshot -> inject -> check -> restore
# --------------------------------------------------------------------------- #

def _cargo_available() -> bool:
    return shutil.which("cargo") is not None


def _pac_provisioned() -> bool:
    return PAC_GENERIC.is_file() and (DEVICE_DIR / f"{PERIPHERAL}.rs").is_file()


def _tree_digest(*roots: Path) -> str:
    """One sha256 over every file under the given paths (order-stable)."""
    h = hashlib.sha256()
    for root in roots:
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        for f in files:
            if f.is_file():
                h.update(str(f.relative_to(APP_DIR)).encode())
                h.update(f.read_bytes())
    return h.hexdigest()


class _InjectedPac:
    """Context manager: snapshot the PAC + main.rs, inject, restore on exit,
    and assert the restore is byte-for-byte."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        backup = Path(self._tmp.name)
        shutil.copy2(PAC_GENERIC, backup / "generic.rs")
        shutil.copytree(DEVICE_DIR, backup / DEVICE)
        self._main = MAIN_RS.read_bytes()
        self._digest = _tree_digest(PAC_GENERIC, DEVICE_DIR)
        inject = subprocess.run(
            [sys.executable, str(RUST_CODEGEN), str(FIXTURE),
             "--peripheral", PERIPHERAL,
             "--inject-pac", str(PAC_ROOT), "--device", DEVICE],
            capture_output=True, text=True,
        )
        if inject.returncode != 0:
            self._restore()
            raise AssertionError(
                "injection failed:\n" + inject.stdout + inject.stderr)
        return self

    def cargo_check(self, main_source: str | None = None):
        if main_source is not None:
            MAIN_RS.write_text(main_source)
        return subprocess.run(
            ["cargo", "check"], cwd=str(CRATE_DIR),
            capture_output=True, text=True,
        )

    def _restore(self):
        backup = Path(self._tmp.name)
        shutil.copy2(backup / "generic.rs", PAC_GENERIC)
        shutil.rmtree(DEVICE_DIR)
        shutil.copytree(backup / DEVICE, DEVICE_DIR)
        MAIN_RS.write_bytes(self._main)

    def __exit__(self, *exc):
        self._restore()
        restored = _tree_digest(PAC_GENERIC, DEVICE_DIR) == self._digest
        self._tmp.cleanup()
        assert restored, (
            "PAC crate was NOT restored after the test -- it has been left "
            "modified. Re-provision with get_pac.py --force."
        )
        return False


# --------------------------------------------------------------------------- #
# Test 2: legal paths compile
# --------------------------------------------------------------------------- #

def test_constraint_test_compiles():
    """Inject, then the committed main.rs (all legal paths) must cargo-check."""
    if not _cargo_available():
        _skip("test_constraint_test_compiles", "cargo not on PATH")
        return
    if not _pac_provisioned():
        _skip("test_constraint_test_compiles",
              f"provisioned stm32f4 PAC not found under {PAC_SRC} "
              "(run get_pac.py)")
        return

    with _InjectedPac() as pac:
        check = pac.cargo_check()
        assert check.returncode == 0, (
            "legal-paths crate failed to compile against the injected PAC:\n"
            + check.stdout + check.stderr
        )


# --------------------------------------------------------------------------- #
# Test 3: enforcement — the compile-fail table
# --------------------------------------------------------------------------- #

_PRELUDE = """\
#![no_std]
#![no_main]
use stm32f4::stm32f405;
#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! { loop {} }
#[no_mangle]
pub extern "C" fn main() -> ! {
    let dp = unsafe { stm32f405::Peripherals::steal() };
    let i2c1 = &dp.I2C1;
    BODY
    loop {}
}
"""


def _program(body: str) -> str:
    return _PRELUDE.replace("    BODY", body)


# (name, body, expected error code, expected message substring)
# Each row is a soundness property of the encoding; a row that starts
# compiling is a hole. Rows 2-3 are PR 15's verified defect 2 (the safe
# Deref/UFCS bypass) pinned as regressions forever.
ILLEGAL_PROGRAMS = [
    (
        "witnessless_write",
        "    i2c1.cr1().write(|w| w.pe().enabled());",
        "E0277", "write-constrained by its datasheet",
    ),
    (
        "ascribed_ref_bypass",
        "    let r: &stm32f4::Reg<stm32f405::i2c1::cr1::CR1rs> = i2c1.cr1();\n"
        "    r.write(|w| w.pe().enabled());",
        "E0277", "write-constrained by its datasheet",
    ),
    (
        "ufcs_bypass",
        "    stm32f4::Reg::<stm32f405::i2c1::cr1::CR1rs>::write("
        "i2c1.cr1(), |w| w.pe().enabled());",
        "E0277", "write-constrained by its datasheet",
    ),
    (
        "witness_reuse",
        "    if let Ok(w) = i2c1.cr1().check_write_ready() {\n"
        "        i2c1.cr1().write_witnessed(|x| x.pe().enabled(), w);\n"
        "        i2c1.cr1().write_witnessed(|x| x.pe().enabled(), w);\n"
        "    }",
        "E0382", "",
    ),
    (
        "wrong_operation_witness",
        "    if let Ok(w) = i2c1.cr1().check_write_ready() {\n"
        "        i2c1.cr1().modify_witnessed(|_, x| x.pe().enabled(), w);\n"
        "    }",
        "E0308", "",
    ),
    (
        "witnessless_modify",
        "    i2c1.cr1().modify(|_, w| w.pe().enabled());",
        "E0277", "modify-constrained by its datasheet",
    ),
    (
        "witnessless_reset",
        "    i2c1.cr1().reset();",
        "E0277", "write-constrained by its datasheet",
    ),
    (
        "witnessless_write_with_zero",
        "    unsafe { i2c1.cr1().write_with_zero(|w| w.pe().enabled()) };",
        "E0277", "write-constrained by its datasheet",
    ),
    (
        "witnessless_from_write",
        "    i2c1.cr1().from_write(|w| { w.pe().enabled(); });",
        "E0277", "write-constrained by its datasheet",
    ),
]


def test_illegal_programs_rejected():
    """Every adversarial program must be rejected with the expected error."""
    if not _cargo_available():
        _skip("test_illegal_programs_rejected", "cargo not on PATH")
        return
    if not _pac_provisioned():
        _skip("test_illegal_programs_rejected",
              f"provisioned stm32f4 PAC not found under {PAC_SRC} "
              "(run get_pac.py)")
        return

    failures = []
    with _InjectedPac() as pac:
        for name, body, code, needle in ILLEGAL_PROGRAMS:
            check = pac.cargo_check(_program(body))
            out = check.stdout + check.stderr
            if check.returncode == 0:
                failures.append(f"{name}: COMPILED -- enforcement hole!")
            elif f"error[{code}]" not in out:
                failures.append(
                    f"{name}: rejected, but not with {code}:\n{out[-1500:]}")
            elif needle and needle not in out:
                failures.append(
                    f"{name}: {code} raised without the expected diagnostic "
                    f"({needle!r}):\n{out[-1500:]}")

    assert not failures, "\n\n".join(failures)


# --------------------------------------------------------------------------- #
# Direct runner (mirrors tests/test_prompt_schema_consistency.py style)
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    tests = [
        test_codegen_matches_golden,
        test_constraint_test_compiles,
        test_illegal_programs_rejected,
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
