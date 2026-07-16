#!/usr/bin/env python3
"""Cross-PAC generality experiment for the trait-gated constraint injection.

QUESTION: the injector (rust_codegen.py) was built and verified against
stm32f4 0.16.0. Does it work, unchanged, on OTHER PAC crates?

MATRIX (committed results: docs/cross_pac_generality.md):
  - stm32f1 0.16.0   (same stm32-rs release train)   <- rm0008 corpus fixture
  - stm32f0 0.16.0   (same train, NEWER I2C IP)      <- rm0091 corpus fixture
  - stm32l4 0.16.0   (same train)                    <- rm0394 corpus fixture
  - rp2040-pac 0.6.0 (NOT stm32-rs; svd2rust 0.31.5) <- SYNTHETIC fixture; the
    injector is EXPECTED to fail loudly on generic.rs template drift -- that
    refusal is the datum, not a bug to paper over.
  - stm32f1xx-hal 0.11.0 adoption repeat (its stm32f1 req is ^0.16.0, which
    pairs with the crate provisioned here), in a throwaway $TMPDIR workspace
    via [patch.crates-io], classified exactly like test_codegen.test_hal_demo.

Per target: provision -> snapshot -> inject fixture -> cargo check a LEGAL
probe (check_write_ready + write_witnessed + write_when_ready) and an ILLEGAL
probe (bare .write(..) must fail E0277 with the datasheet diagnostic) ->
restore -> verify the tree byte-for-byte pristine. A tree is snapshotted
BEFORE injection and restored even when a step fails.

This is a standalone experiment driver, deliberately NOT part of the pytest
suite -- the canonical CI crate stays stm32f4 (see test_codegen.py).

Usage:
    python applications/pac_codegen/experiments/cross_pac.py [--skip-hal] [--only NAME]
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent  # applications/pac_codegen
sys.path.insert(0, str(APP_DIR))
import get_pac  # noqa: E402
from rust_codegen import _GATED_METHODS  # noqa: E402  (template diagnosis)

RUST_CODEGEN = APP_DIR / "rust_codegen.py"
FIXTURES = APP_DIR / "experiments" / "fixtures"
STEP_TIMEOUT = 900  # seconds; time-box every injection / cargo step

HAL_CRATE = "stm32f1xx-hal"
HAL_VERSION = "0.11.0"  # index-verified: depends on stm32f1 ^0.16.0
HAL_FEATURES = ["stm32f103", "medium"]


# --------------------------------------------------------------------------- #
# The matrix
# --------------------------------------------------------------------------- #

@dataclass
class Target:
    name: str
    crate: str
    version: str
    device: str           # device module inside the PAC; "." = flat single-device crate
    feature: str | None   # cargo feature selecting the device (None = no features)
    peripheral: str       # peripheral module the constraint injects into
    fixture: Path
    fixture_note: str     # provenance, for the report
    periph_field: str     # field on the Peripherals struct (dp.I2C1)
    reg: str              # register accessor on the peripheral (p.cr1())
    legal_op: str         # a real field op for the write closures
    spec: str             # the RegisterSpec type the E0277 should name
    expect_drift: bool = False
    notes: str = ""


TARGETS = [
    Target(
        name="stm32f1", crate="stm32f1", version="0.16.0",
        device="stm32f103", feature="stm32f103",
        peripheral="i2c1",
        fixture=FIXTURES / "rm0008_i2c1_cr1.json",
        fixture_note="verbatim agent_output/stm/rm0008/1/i2c1_cr1 (RM0008)",
        periph_field="I2C1", reg="cr1", legal_op="w.pe().set_bit()",
        spec="CR1rs",
        notes="same I2C IP as the F4 reference target: same-register "
              "STOP/START/PEC write gate",
    ),
    Target(
        name="stm32f0", crate="stm32f0", version="0.16.0",
        device="stm32f0x1", feature="stm32f0x1",
        peripheral="i2c1",
        fixture=FIXTURES / "rm0091_i2c1_timeoutr.json",
        fixture_note="verbatim agent_output/stm/rm0091/3/i2c1_timeoutr (RM0091)",
        periph_field="I2C1", reg="timeoutr", legal_op="w.texten().clear_bit()",
        spec="TIMEOUTRrs",
        notes="NEWER I2C IP (no CR1 STOP/START/PEC): TIMEOUTR write gated on "
              "TEXTEN cleared, same-register",
    ),
    Target(
        name="stm32l4", crate="stm32l4", version="0.16.0",
        device="stm32l4x2", feature="stm32l4x2",
        peripheral="spi1",
        fixture=FIXTURES / "rm0394_spi1_cr1.json",
        fixture_note="verbatim agent_output/stm/rm0394/1/spi1_cr1 (RM0394)",
        periph_field="SPI1", reg="cr1", legal_op="w.crcen().clear_bit()",
        spec="CR1rs",
        notes="two corpus constraints (CRCEN, CRCL) sharing one SPE-cleared "
              "precondition; injector dedupes them into one gate",
    ),
    Target(
        name="rp2040-pac", crate="rp2040-pac", version="0.6.0",
        device=".",  # flat single-device crate: peripherals live at src/ top level
        feature=None,
        peripheral="i2c0",
        fixture=FIXTURES / "rp2040_i2c0_ic_enable.json",
        fixture_note="SYNTHETIC mechanics probe (real I2C0.IC_ENABLE register/fields)",
        periph_field="I2C0", reg="ic_enable", legal_op="w.enable().enabled()",
        spec="IC_ENABLE_SPEC",
        expect_drift=True,
        notes="not stm32-rs; svd2rust 0.31.5 vs the 0.36.1 template the "
              "injector pins -- expected to refuse loudly",
    ),
]


# --------------------------------------------------------------------------- #
# Snapshot / restore (mirrors test_codegen.py's _InjectedPac, generalized)
# --------------------------------------------------------------------------- #

class PacSnapshot:
    """Snapshot generic.rs + the device tree before injection; restore and
    byte-verify afterward. For a flat crate (device '.') the whole src/ tree
    is snapshotted."""

    def __init__(self, pac_root: Path, device: str):
        src = pac_root / "src"
        self.base = pac_root
        self.paths = [src] if device == "." else [src / "generic.rs", src / device]
        self._tmp = tempfile.TemporaryDirectory(prefix="cross_pac_snap_")
        self.digest = self._digest()
        for i, p in enumerate(self.paths):
            dst = Path(self._tmp.name) / str(i)
            if p.is_file():
                shutil.copy2(p, dst)
            else:
                shutil.copytree(p, dst)

    def _digest(self) -> str:
        h = hashlib.sha256()
        for root in self.paths:
            files = [root] if root.is_file() else sorted(root.rglob("*"))
            for f in files:
                if f.is_file():
                    h.update(str(f.relative_to(self.base)).encode())
                    h.update(f.read_bytes())
        return h.hexdigest()

    def restore_and_verify(self) -> bool:
        for i, p in enumerate(self.paths):
            saved = Path(self._tmp.name) / str(i)
            if saved.is_file():
                shutil.copy2(saved, p)
            else:
                shutil.rmtree(p)
                shutil.copytree(saved, p)
        ok = self._digest() == self.digest
        self._tmp.cleanup()
        return ok


# --------------------------------------------------------------------------- #
# Probe crate (throwaway, under $TMPDIR)
# --------------------------------------------------------------------------- #

_PROBE_MAIN = """\
#![no_std]
#![no_main]
{use_line}
#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {{ loop {{}} }}
#[no_mangle]
pub extern "C" fn main() -> ! {{
    let dp = unsafe {{ device::Peripherals::steal() }};
    #[allow(unused_variables)]
    let p = &dp.{periph_field};
{body}
    loop {{}}
}}
"""

_LEGAL_BODY = """\
    // Recommended path: check + write welded into one call.
    let _ = p.{reg}().write_when_ready(|w| {legal_op});
    // Two-step path: mint a witness, spend it once.
    if let Ok(witness) = p.{reg}().check_write_ready() {{
        p.{reg}().write_witnessed(|w| {legal_op}, witness);
    }}"""

_ILLEGAL_BODY = "    p.{reg}().write(|w| {legal_op});"

ILLEGAL_NEEDLE = "write-constrained by its datasheet"


def _make_probe(target: Target, pac_dir: Path) -> Path:
    ws = Path(tempfile.mkdtemp(prefix=f"cross_pac_{target.name}_"))
    (ws / "src").mkdir()
    feat = f', features = ["{target.feature}"]' if target.feature else ""
    (ws / "Cargo.toml").write_text(
        "[package]\n"
        'name = "cross-pac-probe"\n'
        'version = "0.1.0"\n'
        'edition = "2021"\n\n'
        "[profile.dev]\n"
        'panic = "abort"\n\n'
        "[dependencies]\n"
        f'{target.crate} = {{ path = "{pac_dir}"{feat} }}\n'
    )
    return ws


def _probe_main(target: Target, body_tpl: str) -> str:
    crate_ident = target.crate.replace("-", "_")
    use_line = (f"use {crate_ident} as device;" if target.device == "."
                else f"use {crate_ident}::{target.device} as device;")
    body = body_tpl.format(reg=target.reg, legal_op=target.legal_op)
    return _PROBE_MAIN.format(use_line=use_line,
                              periph_field=target.periph_field, body=body)


def _cargo_check(workdir: Path, extra: list[str] | None = None):
    try:
        return subprocess.run(
            ["cargo", "check"] + (extra or []), cwd=str(workdir),
            capture_output=True, text=True, timeout=STEP_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None


# --------------------------------------------------------------------------- #
# Template diagnosis (for the report when injection refuses)
# --------------------------------------------------------------------------- #

# generic.rs anchors the injector must find. _GATED_METHODS is imported from
# rust_codegen; the read/reset/Debug anchors are inline strings inside
# patch_generic_rs, replicated here VERBATIM for diagnosis only (rust_codegen
# stays the source of truth and fails loudly on its own).
_INLINE_ANCHORS = [
    ("fn read", "    pub fn read(&self) -> R<REG> {"),
    ("fn reset", "    pub fn reset(&self) {"),
    ("Debug impl",
     "impl<REG: Readable> core::fmt::Debug for crate::generic::Reg<REG>\n"
     "where\n"
     "    R<REG>: core::fmt::Debug,"),
]


def diagnose_template(pac_dir: Path) -> list[tuple[str, bool]]:
    content = (pac_dir / "src" / "generic.rs").read_text()
    rows = [(name, anchor in content) for name, anchor in _INLINE_ANCHORS]
    for sig, _bound in _GATED_METHODS:
        label = "fn " + sig.strip().splitlines()[0].split("fn ", 1)[1].split("(")[0]
        rows.append((label, sig in content))
    return rows


def svd2rust_version(pac_dir: Path) -> str:
    lib = (pac_dir / "src" / "lib.rs").read_text(errors="replace")
    m = re.search(r"svd2rust[^0-9]{0,20}v?(\d+\.\d+\.\d+)", lib)
    return m.group(1) if m else "unknown"


# --------------------------------------------------------------------------- #
# One target
# --------------------------------------------------------------------------- #

def run_target(target: Target) -> dict:
    res = {
        "target": target,
        "svd2rust": "?", "inject": "?", "legal": "-", "illegal": "-",
        "diagnostic": "", "pristine": False, "detail": [],
    }
    print(f"\n=== {target.name} {target.version} ===")
    pac_dir = get_pac.provision(crate=target.crate, version=target.version)
    res["svd2rust"] = svd2rust_version(pac_dir)

    snap = PacSnapshot(pac_dir, target.device)
    try:
        inject = subprocess.run(
            [sys.executable, str(RUST_CODEGEN), str(target.fixture),
             "--peripheral", target.peripheral,
             "--inject-pac", str(pac_dir), "--device", target.device],
            capture_output=True, text=True, timeout=STEP_TIMEOUT,
        )
        if inject.returncode != 0:
            err = (inject.stderr or inject.stdout).strip()
            res["inject"] = "REFUSED"
            res["detail"].append("injector output (loud refusal):\n" + err)
            print(f"  injection REFUSED (exit {inject.returncode})")
            # Which template anchors drifted?
            rows = diagnose_template(pac_dir)
            res["template"] = rows
            for name, ok in rows:
                print(f"    anchor {'MATCH  ' if ok else 'MISSING'} {name}")
            return res

        res["inject"] = "ok"
        print("  " + inject.stdout.strip().replace("\n", "\n  "))

        ws = _make_probe(target, pac_dir)
        main_rs = ws / "src" / "main.rs"
        print(f"  probe crate: {ws}")

        # LEGAL probe
        main_rs.write_text(_probe_main(target, _LEGAL_BODY))
        check = _cargo_check(ws)
        if check is None:
            res["legal"] = "TIMEOUT"
        elif check.returncode == 0:
            res["legal"] = "PASS"
        else:
            res["legal"] = "FAIL"
            res["detail"].append("legal probe errors:\n" + check.stderr[-3000:])
        print(f"  legal probe:   {res['legal']}")

        # ILLEGAL probe
        main_rs.write_text(_probe_main(target, _ILLEGAL_BODY))
        check = _cargo_check(ws)
        if check is None:
            res["illegal"] = "TIMEOUT"
        elif check.returncode == 0:
            res["illegal"] = "HOLE (compiled!)"
        else:
            out = check.stdout + check.stderr
            has_code = "error[E0277]" in out
            has_msg = ILLEGAL_NEEDLE in out
            names_spec = target.spec in out
            if has_code and has_msg:
                res["illegal"] = "PASS (E0277 + datasheet msg)"
                for line in out.splitlines():
                    if ILLEGAL_NEEDLE in line:
                        res["diagnostic"] = line.strip().lstrip("= ")
                        break
                if not names_spec:
                    res["illegal"] += f" [does not name {target.spec}]"
            else:
                res["illegal"] = (f"WRONG ERROR (E0277 {'yes' if has_code else 'no'}, "
                                  f"msg {'yes' if has_msg else 'no'})")
                res["detail"].append("illegal probe output:\n" + out[-3000:])
        print(f"  illegal probe: {res['illegal']}")
        if res["diagnostic"]:
            print(f"    diagnostic: {res['diagnostic']}")
        return res
    finally:
        res["pristine"] = snap.restore_and_verify()
        stamped = get_pac.provisioned(target.crate, target.version)
        print(f"  restored pristine: {res['pristine']} (stamp ok: {stamped})")
        if not res["pristine"]:
            print(f"  !! {target.crate} tree NOT byte-identical after restore; "
                  f"re-provision with get_pac.py --crate {target.crate} "
                  f"--version {target.version} --force", file=sys.stderr)


# --------------------------------------------------------------------------- #
# stm32f1xx-hal adoption repeat (mirrors test_codegen.test_hal_demo)
# --------------------------------------------------------------------------- #

def _hal_errors_json(workdir: Path, hal_dirname: str) -> list[dict] | None:
    """cargo-check with JSON messages; return error diagnostics with their
    HAL source files attributed (primary + macro-expansion spans)."""
    run = _cargo_check(workdir, ["--message-format=json"])
    if run is None:
        return None
    out = []
    for line in run.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") != "compiler-message":
            continue
        d = m["message"]
        if d.get("level") != "error":
            continue
        files: set[str] = set()

        def _walk(spans):
            for s in spans:
                fn = s.get("file_name", "")
                if hal_dirname in fn:
                    files.add(fn.split(f"{hal_dirname}/")[-1])
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


def run_hal_adoption(f1: Target) -> dict:
    res = {"ran": False, "baseline": "?", "true_enforcement": 0,
           "generic_friction": 0, "other": 0, "files": {}, "detail": [],
           "pristine": False, "workspace": ""}
    print(f"\n=== adoption repeat: {HAL_CRATE} {HAL_VERSION} on injected stm32f1 ===")
    pac_dir = get_pac.provision(crate=f1.crate, version=f1.version)
    ws = Path(tempfile.mkdtemp(prefix="cross_pac_hal_"))
    res["workspace"] = str(ws)
    (ws / "src").mkdir()
    (ws / "src" / "lib.rs").write_text(
        "//! Compiling this crate compiles the unmodified stm32f1xx-hal against\n"
        "//! the locally patched stm32f1 PAC. The build itself is the experiment.\n"
        "#![no_std]\npub use stm32f1xx_hal as hal;\n"
    )
    feats = ", ".join(f'"{f}"' for f in HAL_FEATURES)
    (ws / "Cargo.toml").write_text(
        "[package]\n"
        'name = "cross-pac-hal-f1"\n'
        'version = "0.1.0"\n'
        'edition = "2021"\n\n'
        "[dependencies]\n"
        f'{HAL_CRATE} = {{ version = "={HAL_VERSION}", features = [{feats}] }}\n\n'
        "[patch.crates-io]\n"
        f'{f1.crate} = {{ path = "{pac_dir}" }}\n'
    )
    print(f"  workspace: {ws}")

    # (a) baseline: pristine PAC must check cleanly.
    baseline = _cargo_check(ws)
    if baseline is None:
        res["baseline"] = "TIMEOUT"
        return res
    if baseline.returncode != 0:
        res["baseline"] = "FAIL"
        res["detail"].append("baseline (pristine PAC) errors:\n"
                             + baseline.stderr[-3000:])
        print("  baseline FAILED against the pristine PAC -- demo means nothing")
        return res
    res["baseline"] = "PASS"
    print("  baseline (pristine PAC): PASS")

    # (b) injected PAC.
    snap = PacSnapshot(pac_dir, f1.device)
    try:
        inject = subprocess.run(
            [sys.executable, str(RUST_CODEGEN), str(f1.fixture),
             "--peripheral", f1.peripheral,
             "--inject-pac", str(pac_dir), "--device", f1.device],
            capture_output=True, text=True, timeout=STEP_TIMEOUT,
        )
        if inject.returncode != 0:
            res["detail"].append("injection failed:\n" + inject.stderr)
            return res
        errors = _hal_errors_json(ws, f"{HAL_CRATE}-{HAL_VERSION}")
        if errors is None:
            res["detail"].append("injected check timed out")
            return res
        res["ran"] = True
        files: dict[str, set] = {"true_enforcement": set(),
                                 "generic_friction": set(), "other": set()}
        for e in errors:
            witness_msg = (e["code"] == "E0277"
                           and "constrained by its datasheet" in e["message"])
            if witness_msg and f1.spec in e["message"]:
                res["true_enforcement"] += 1
                files["true_enforcement"] |= e["hal_files"]
            elif witness_msg:
                res["generic_friction"] += 1
                files["generic_friction"] |= e["hal_files"]
            else:
                res["other"] += 1
                files["other"] |= e["hal_files"]
                res["detail"].append(
                    f"other error: {e['code']} {e['message'][:160]} "
                    f"@ {sorted(e['hal_files'])}")
        res["files"] = {k: sorted(v) for k, v in files.items()}
        print(f"  true enforcement ({f1.spec} datasheet msg): "
              f"{res['true_enforcement']} errors @ {res['files']['true_enforcement']}")
        print(f"  generic friction (datasheet msg, generic code): "
              f"{res['generic_friction']} errors @ {res['files']['generic_friction']}")
        print(f"  other: {res['other']} errors @ {res['files']['other']}")
        return res
    finally:
        res["pristine"] = snap.restore_and_verify()
        print(f"  restored pristine: {res['pristine']}")
        if not res["pristine"]:
            print("  !! stm32f1 tree NOT byte-identical after restore",
                  file=sys.stderr)


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", help="run a single matrix target by name")
    ap.add_argument("--skip-hal", action="store_true",
                    help="skip the stm32f1xx-hal adoption repeat")
    args = ap.parse_args()

    if shutil.which("cargo") is None:
        sys.exit("cargo is required for the cross-PAC experiment")

    targets = [t for t in TARGETS if not args.only or t.name == args.only]
    if not targets:
        sys.exit(f"no matrix target named {args.only!r}")

    results = [run_target(t) for t in targets]
    hal = None
    if not args.skip_hal and any(t.name == "stm32f1" for t in targets):
        hal = run_hal_adoption(next(t for t in targets if t.name == "stm32f1"))

    # ---- summary table (markdown) ----
    print("\n\n## Results\n")
    print("| crate | version | svd2rust | injection | legal probe | "
          "illegal probe | pristine after |")
    print("|---|---|---|---|---|---|---|")
    for r in results:
        t = r["target"]
        print(f"| {t.crate} | {t.version} | {r['svd2rust']} | {r['inject']} | "
              f"{r['legal']} | {r['illegal']} | {r['pristine']} |")
    for r in results:
        if r.get("template"):
            t = r["target"]
            print(f"\n### {t.crate} template diagnosis")
            for name, ok in r["template"]:
                print(f"- {'MATCH' if ok else 'MISSING'}: `{name}`")
        for d in r["detail"]:
            print(f"\n[{r['target'].name}] {d}")
    if hal is not None:
        print(f"\n### {HAL_CRATE} {HAL_VERSION} adoption")
        print(f"- baseline (pristine PAC): {hal['baseline']}")
        if hal["ran"]:
            print(f"- true enforcement: {hal['true_enforcement']} "
                  f"@ {hal['files']['true_enforcement']}")
            print(f"- generic friction: {hal['generic_friction']} "
                  f"@ {hal['files']['generic_friction']}")
            print(f"- other: {hal['other']} @ {hal['files']['other']}")
        print(f"- stm32f1 pristine after: {hal['pristine']}")
        for d in hal["detail"]:
            print(f"[hal] {d}")

    bad = [r for r in results if not r["pristine"]]
    if hal is not None and hal["baseline"] == "PASS" and not hal["pristine"]:
        bad.append(hal)
    if bad:
        sys.exit("ERROR: a PAC tree was left non-pristine (see above)")


if __name__ == "__main__":
    main()
