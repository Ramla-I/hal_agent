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
import json
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
MAIN_RS = CRATE_DIR / "src" / "main.rs"

# (fixture json, peripheral, golden file) — every entry is golden-diffed and
# all of them are injected together for the compile tests. The spi1/rcc
# fixtures are real generator output (cross-register read/write gates).
FIXTURES = [
    (CRATE_DIR / "stm32f405_i2c1.json", "i2c1",
     CRATE_DIR / "i2c1_expected_constraints.rs"),
    (CRATE_DIR / "stm32f405_spi1_txcrcr.json", "spi1",
     CRATE_DIR / "spi1_txcrcr_expected_constraints.rs"),
    (CRATE_DIR / "stm32f405_rcc_sscgr.json", "rcc",
     CRATE_DIR / "rcc_sscgr_expected_constraints.rs"),
]

# The generated stm32f4 PAC, provisioned from crates.io by get_pac.py.
PAC_ROOT = APP_DIR / "vendored" / "pac" / "stm32f4"
PAC_SRC = PAC_ROOT / "src"
PAC_GENERIC = PAC_SRC / "generic.rs"
DEVICE = "stm32f405"
DEVICE_DIR = PAC_SRC / DEVICE

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

def _generate_standalone(fixture: Path, peripheral: str, out_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(RUST_CODEGEN), str(fixture),
         "--peripheral", peripheral, "--output", str(out_path)],
        check=True, capture_output=True, text=True,
    )


def _golden_generated_section(golden: Path) -> str:
    lines = golden.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.strip() == GOLDEN_MARKER:
            return "\n".join(lines[i + 1:])
    raise AssertionError(
        f"Golden file {golden.name} is missing its marker line "
        f"'{GOLDEN_MARKER}'."
    )


def test_codegen_matches_golden():
    """Every fixture's output must match its committed golden, line for line."""
    for fixture, peripheral, golden in FIXTURES:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "constraints.rs"
            _generate_standalone(fixture, peripheral, out)
            generated = out.read_text()

        expected = _golden_generated_section(golden)
        if generated.splitlines() != expected.splitlines():
            diff = "\n".join(difflib.unified_diff(
                expected.splitlines(), generated.splitlines(),
                fromfile=f"{golden.name} (expected)",
                tofile=f"rust_codegen.py output for {fixture.name} (actual)",
                lineterm="",
            ))
            raise AssertionError(
                "Generated codegen output no longer matches the golden "
                f"{golden.name}. If this change is intentional, refresh the "
                "golden's generated section (see its header).\n\n" + diff
            )


def test_field_scoped_constraint_skipped_with_warning(tmp_path):
    """Field-scoped constraints (non-empty ``target_fields``) are not yet
    enforceable: the emitter skips each with a warning instead of over-gating
    the whole register (see the plan's "Field-level gating" section). A
    whole-register constraint on the same register is still emitted."""
    data = json.loads((CRATE_DIR / "stm32f405_i2c1.json").read_text())
    whole = data["access_constraints"][0]            # real whole-register gate
    field_scoped = json.loads(json.dumps(whole))     # a field-scoped sibling
    field_scoped["target_fields"] = ["PE"]
    data["access_constraints"] = [whole, field_scoped]
    fixture = tmp_path / "mixed.json"
    fixture.write_text(json.dumps(data))
    out = tmp_path / "constraints.rs"
    result = subprocess.run(
        [sys.executable, str(RUST_CODEGEN), str(fixture),
         "--peripheral", "i2c1", "--output", str(out)],
        check=True, capture_output=True, text=True,
    )
    assert "field-level gating is not yet supported" in result.stderr
    assert "PE" in result.stderr                      # the skipped field named
    # the whole-register constraint survived; only the field-scoped one dropped
    assert out.read_text().strip()


# --------------------------------------------------------------------------- #
# Compile-test machinery: snapshot -> inject -> check -> restore
# --------------------------------------------------------------------------- #

def _cargo_available() -> bool:
    return shutil.which("cargo") is not None


def _pac_provisioned() -> bool:
    return PAC_GENERIC.is_file() and all(
        (DEVICE_DIR / f"{peripheral}.rs").is_file()
        for _, peripheral, _ in FIXTURES
    )


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
        cmd = [sys.executable, str(RUST_CODEGEN),
               str(FIXTURES[0][0]), "--peripheral", FIXTURES[0][1],
               "--inject-pac", str(PAC_ROOT), "--device", DEVICE]
        for fixture, peripheral, _ in FIXTURES[1:]:
            cmd += ["--constraint", f"{peripheral}={fixture}"]
        inject = subprocess.run(cmd, capture_output=True, text=True)
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
        # copy2 preserves the ORIGINAL (old) mtimes; cargo treats
        # older-than-recorded files as fresh and would replay the cached
        # diagnostics of the INJECTED build against the restored pristine
        # tree. Touch everything so the next check always re-reads sources.
        os.utime(PAC_GENERIC)
        for f in DEVICE_DIR.rglob("*"):
            if f.is_file():
                os.utime(f)

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
    #[allow(unused_variables)]
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
    (
        "witnessless_read_of_read_gated",
        "    let _ = dp.SPI1.txcrcr().read().bits();",
        "E0277", "read-constrained by its datasheet",
    ),
    (
        "witnessless_cross_register_write",
        "    dp.RCC.sscgr().write(|w| unsafe { w.bits(0) });",
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
# Test 4: the "real driver" demo — unmodified stm32f4xx-hal vs injected PAC
# --------------------------------------------------------------------------- #

EVAL_HAL_DIR = APP_DIR / "eval_hal"

# Both counts are pinned: the HAL version is pinned (=0.23.0) and the fixture
# set is committed, so the error inventory is deterministic.
#
# TRUE ENFORCEMENT: the HAL's I2C driver modifies CR1 at 14 sites; every one
# must fail with our datasheet diagnostic, and no other module may be hit by
# the CR1 constraint.
HAL_I2C_ERRORS = 14
HAL_I2C_FILES = {"src/i2c.rs", "src/i2c/dma.rs"}
# KNOWN FRICTION (documented in eval_hal/README.md and the plan's divergence
# log): the HAL's serial layer is written generically over UART register
# blocks via trait associated types; generic code calling read/write/modify
# now needs the Unconstrained* marker bounds it (predating us) does not
# declare, so its generic definitions fail to typecheck even though no USART
# register is constrained. This is the encoding's one adoption cost for
# trait-generic driver code — mechanical one-line bounds in one module.
HAL_GENERIC_ERRORS = 14
HAL_GENERIC_FILES = {"src/serial.rs", "src/serial/uart_impls.rs"}


def _hal_check_json() -> list[dict]:
    """cargo-check eval_hal and return E0277 diagnostics with their HAL
    source files attributed (primary spans + macro-expansion spans)."""
    import json as _json
    run = subprocess.run(
        ["cargo", "check", "--message-format=json"],
        cwd=str(EVAL_HAL_DIR), capture_output=True, text=True,
    )
    out = []
    for line in run.stdout.splitlines():
        try:
            m = _json.loads(line)
        except ValueError:
            continue
        if m.get("reason") != "compiler-message":
            continue
        d = m["message"]
        if d.get("level") != "error":
            continue
        files = set()

        def _walk(spans):
            for s in spans:
                fn = s.get("file_name", "")
                if "stm32f4xx-hal" in fn:
                    files.add(fn.split("stm32f4xx-hal-0.23.0/")[-1])
                exp = s.get("expansion")
                if exp and exp.get("span"):
                    _walk([exp["span"]])

        _walk(d.get("spans", []))
        for ch in d.get("children", []):
            _walk(ch.get("spans", []))
        out.append({
            "code": (d.get("code") or {}).get("code", ""),
            "message": d.get("message", ""),
            "hal_files": files,
        })
    return out


def test_hal_demo():
    """The unmodified stm32f4xx-hal, consumed exactly as a downstream user
    would (crates.io package + [patch.crates-io] PAC swap), must:
      (a) compile cleanly against the PRISTINE PAC (adoption costs nothing),
      (b) against the INJECTED PAC, fail ONLY with our datasheet diagnostics,
          at exactly the known I2C sites plus the documented generic-serial
          friction — nothing else in the ~30k-line HAL may break.
    """
    if not _cargo_available():
        _skip("test_hal_demo", "cargo not on PATH")
        return
    if not _pac_provisioned():
        _skip("test_hal_demo",
              f"provisioned stm32f4 PAC not found under {PAC_SRC} "
              "(run get_pac.py)")
        return

    # (a) baseline: pristine PAC, unmodified HAL -> clean check.
    baseline = subprocess.run(
        ["cargo", "check"], cwd=str(EVAL_HAL_DIR),
        capture_output=True, text=True,
    )
    assert baseline.returncode == 0, (
        "unmodified stm32f4xx-hal failed against the PRISTINE PAC — the "
        "baseline is broken, the demo means nothing:\n" + baseline.stderr[-2000:]
    )

    # (b) injected PAC.
    with _InjectedPac():
        errors = _hal_check_json()

    assert errors, "injected PAC produced no errors in the HAL — gate inert?"
    unexpected = []
    i2c = generic = 0
    for e in errors:
        if e["code"] != "E0277" or "constrained by its datasheet" not in e["message"]:
            unexpected.append(f"non-witness error: {e['code']} {e['message'][:120]}")
        elif "CR1rs" in e["message"]:
            i2c += 1
            if not e["hal_files"] <= HAL_I2C_FILES:
                unexpected.append(f"CR1 constraint hit outside I2C: {e['hal_files']}")
        elif e["hal_files"] and e["hal_files"] <= HAL_GENERIC_FILES:
            generic += 1
        else:
            unexpected.append(f"unexplained error location: {e['hal_files']} "
                              f"{e['message'][:120]}")
    assert not unexpected, "\n".join(unexpected)
    assert i2c == HAL_I2C_ERRORS, f"expected {HAL_I2C_ERRORS} I2C hits, got {i2c}"
    assert generic == HAL_GENERIC_ERRORS, (
        f"expected {HAL_GENERIC_ERRORS} generic-serial errors, got {generic} — "
        "if the HAL or encoding changed, re-derive and update the inventory"
    )


# --------------------------------------------------------------------------- #
# Direct runner (mirrors tests/test_prompt_schema_consistency.py style)
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    tests = [
        test_codegen_matches_golden,
        test_constraint_test_compiles,
        test_illegal_programs_rejected,
        test_hal_demo,
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
