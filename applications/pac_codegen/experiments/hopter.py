#!/usr/bin/env python3
"""Hopter OS against a constraint-injected PAC.

Hopter (https://github.com/hopter-project/hopter) is a Rust embedded OS for
STM32. The question: does anything in it stop compiling once the chip crate
underneath carries our datasheet gates?

Three facts shape what can actually be measured, and the script establishes
each rather than assuming it:

  1. HOPTER'S CORE DOES NOT LINK A PAC. Its only hardware dependency is
     `cortex-m`; the stm32f4/stm32f0 names in `src/` are a vector table
     *copied* from the stm32f4 crate plus interrupt names in doc comments.
     Our injection therefore cannot reach Hopter's kernel at all — it reaches
     Hopter only through the HAL its examples use.

  2. HOPTER NEEDS A FORKED COMPILER. `rust-toolchain` pins `segstk-rust`, a
     Rust fork with segmented-stack support. On a stock toolchain the build
     dies inside Hopter's own allocator/unwinder (`asm!` in naked functions),
     long before any PAC is involved.

  3. ITS HAL PIN DOES NOT PAIR WITH OUR PAC. The examples use stm32f4xx-hal
     0.21, which requires stm32f4 ^0.15.1; the injector targets 0.16.0.
     Only 0.23.0 pairs (0.22 needs ^0.16.1, and no stm32f4 0.16.1 exists).

So the honest experiment is a SURFACE PROBE: take the exact HAL call sequence
Hopter's examples perform -- steal the peripherals, `RCC.constrain().freeze()`,
`GPIOA.split()` with alternate-function pins, `USART1.serial(...)`, then
`block!(read())` / `write()` -- and compile it against the pristine and the
injected PAC. It exercises the same driver paths Hopter does, on a paired HAL
version, without the forked compiler. It is a proxy, and reported as one.

Usage:
    python applications/pac_codegen/experiments/hopter.py [--hopter DIR]
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "experiments"))
import get_pac  # noqa: E402
from stm_sweep import (DATA, PacSnapshot, Target, cargo_check,  # noqa: E402
                       hal_errors, classify, run_inject)

OUT = APP_DIR / "experiments" / "out"
PAC_VERSION = "0.16.0"
REPO = "https://github.com/hopter-project/hopter"

# rm0368 -> stm32f401, a chip Hopter lists as a supported board.
TARGET = Target("rm0368", "stm32f4", "stm32f401", "stm32f401.svd")
HAL, HAL_VERSION = "stm32f4xx-hal", "0.23.0"

# The HAL surface Hopter's examples actually drive (examples/uart_echo.rs and
# the interrupt tests): clock tree, GPIO alternate function, USART setup, and
# blocking byte I/O.
# NOTE the API drift: Hopter's examples are written against stm32f4xx-hal
# 0.21 (`RCC.constrain().cfgr.freeze()`, `GPIOA.split()` with no argument,
# `uart::Config`). 0.23 -- the only version that pairs with PAC 0.16 -- takes
# `&mut rcc` through GPIO and serial and moved `Config` into `serial`. The
# probe below is Hopter's SEQUENCE expressed in the 0.23 API; that rewrite is
# itself part of the finding.
_PROBE = """#![no_std]
use stm32f4xx_hal::{gpio::GpioExt, prelude::*, rcc::RccExt,
                    serial::{Config, Serial}};

/// The HAL surface hopter/examples/uart_echo.rs drives: clock tree, GPIO
/// alternate function, USART setup, blocking byte I/O.
pub fn hopter_uart_echo_surface() -> ! {
    let dp = unsafe { stm32f4xx_hal::pac::Peripherals::steal() };
    let mut rcc = dp.RCC.constrain();
    let gpioa = dp.GPIOA.split(&mut rcc);
    let pins = (gpioa.pa9.into_alternate::<7>(), gpioa.pa10.into_alternate::<7>());
    let mut usart1: Serial<_, u8> = dp
        .USART1
        .serial(pins, Config::default().baudrate(115200.bps()), &mut rcc)
        .unwrap();
    loop {
        if let Ok(b) = nb::block!(usart1.read()) {
            let _ = nb::block!(usart1.write(b));
        }
    }
}
"""


def _clone(dest: Path) -> Path | None:
    try:
        subprocess.run(["git", "clone", "-q", "--depth", "1", REPO, str(dest)],
                       check=True, capture_output=True, timeout=600)
        return dest
    except Exception as e:                                    # noqa: BLE001
        print(f"  clone failed: {e}")
        return None


def inspect_hopter(root: Path) -> dict:
    """Facts 1 and 3: what Hopter links, and what its HAL pin requires."""
    manifest = (root / "Cargo.toml").read_text()
    toolchain = ""
    for name in ("rust-toolchain", "rust-toolchain.toml"):
        if (root / name).is_file():
            toolchain = (root / name).read_text().strip()
    dev_dep = next((l.strip() for l in manifest.splitlines()
                    if l.startswith("version") and "0.21" in l), "")
    # Does anything OUTSIDE [dev-dependencies] DEPEND on a PAC? Scan only
    # dependency tables -- the [features] section names every supported chip,
    # so a plain substring search over the manifest says "yes" for a crate
    # that links no PAC at all.
    links_pac = False
    section = ""
    for line in manifest.splitlines():
        s = line.strip()
        if s.startswith("["):
            section = s
            if s.startswith("[dependencies.") and "stm32f" in s:
                links_pac = True
            continue
        if section == "[dependencies]" and s.split()[0:1]:
            name = s.split("=")[0].strip()
            if name.startswith("stm32f") and name[6:7].isdigit():
                links_pac = True
    examples = list((root / "examples").rglob("*.rs"))
    using_hal = [p for p in examples
                 if "stm32f4xx_hal" in p.read_text()
                 or "stm32f0xx_hal" in p.read_text()]
    return {"toolchain": toolchain, "core_links_a_pac": links_pac,
            "examples": len(examples), "examples_using_a_hal": len(using_hal),
            "hal_dev_dependency": dev_dep or "stm32f4xx-hal 0.21.0"}


def try_native_build(root: Path) -> dict:
    """Fact 2: what happens on the toolchain we have."""
    installed = subprocess.run(["rustup", "toolchain", "list"],
                               capture_output=True, text=True).stdout
    have_fork = "segstk" in installed
    if have_fork:
        return {"attempted": True, "have_segstk_rust": True,
                "note": "the forked toolchain IS installed; a real build is possible"}
    nightly = next((l.split()[0] for l in installed.splitlines()
                    if l.startswith("nightly-")), None)
    if not nightly:
        return {"attempted": False, "have_segstk_rust": False,
                "note": "no nightly available to even attempt the build"}
    run = subprocess.run(
        ["cargo", f"+{nightly}", "check", "--example", "test-sync-mutex-basic",
         "--features", "stm32f405", "--target", "thumbv7em-none-eabihf"],
        cwd=str(root), capture_output=True, text=True, timeout=1800)
    codes: dict = {}
    for line in run.stderr.splitlines():
        if line.startswith("error["):
            code = line.split("]")[0] + "]"
            codes[code] = codes.get(code, 0) + 1
        elif line.startswith("error:") and "could not compile" not in line:
            codes["error (uncoded)"] = codes.get("error (uncoded)", 0) + 1
    return {"attempted": True, "have_segstk_rust": False, "toolchain": nightly,
            "compiled": run.returncode == 0, "error_codes": codes,
            "note": "failures are in Hopter's OWN kernel code, before any PAC "
                    "is involved" if codes else ""}


def surface_probe(pac_dir: Path, label: str) -> dict:
    ws = Path(tempfile.mkdtemp(prefix=f"hopter_probe_{label}_"))
    (ws / "src").mkdir()
    (ws / "src" / "lib.rs").write_text(_PROBE)
    (ws / "Cargo.toml").write_text(
        "[package]\n"
        f'name = "hopter-surface"\nversion = "0.1.0"\nedition = "2021"\n\n'
        "[dependencies]\n"
        f'{HAL} = {{ version = "={HAL_VERSION}", features = ["stm32f401"] }}\n'
        'nb = "1.1"\n\n'
        "[patch.crates-io]\n"
        f'stm32f4 = {{ path = "{pac_dir}" }}\n')
    errors = hal_errors(ws, f"{HAL}-{HAL_VERSION}")
    run = cargo_check(ws)
    return {"workspace": str(ws), "errors": errors or [],
            "compiles": run is not None and run.returncode == 0}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hopter", default=None,
                    help="existing Hopter checkout (default: clone a shallow copy)")
    args = ap.parse_args()

    tmp = None
    if args.hopter:
        root = Path(args.hopter)
    else:
        tmp = tempfile.mkdtemp(prefix="hopter_src_")
        root = _clone(Path(tmp) / "hopter")
        if root is None:
            sys.exit("could not obtain a Hopter checkout")

    print("=== what Hopter is ===")
    facts = inspect_hopter(root)
    for k, v in facts.items():
        print(f"  {k}: {v}")

    print("\n=== can we build it here? ===")
    native = try_native_build(root)
    for k, v in native.items():
        print(f"  {k}: {v}")

    print("\n=== surface probe: Hopter's HAL call sequence, paired HAL, "
          "pristine vs injected ===")
    pac_dir = get_pac.provision(crate=TARGET.pac, version=PAC_VERSION)
    base = surface_probe(pac_dir, "pristine")
    print(f"  pristine PAC : {'compiles' if base['compiles'] else 'FAILS'}")
    if not base["compiles"]:
        print("  baseline broken — the injected result would mean nothing")
        result = {"facts": facts, "native": native, "baseline": "FAIL"}
    else:
        snap = PacSnapshot(pac_dir, TARGET.device)
        try:
            report = OUT / "hopter_inject.json"
            run = run_inject(TARGET, pac_dir, report, dry=False)
            if run.returncode != 0:
                print("  injection failed:\n" + (run.stderr or run.stdout)[-1500:])
                result = {"facts": facts, "native": native, "baseline": "PASS",
                          "injected": "INJECT_FAILED"}
            else:
                summary = json.loads(report.read_text())
                specs = {f"{r['register'].upper()}rs" for r in summary["rows"]
                         if r["fate"] == "planned"}
                inj = surface_probe(pac_dir, "injected")
                cls = classify(inj["errors"], specs)
                # THE result: how many errors are in Hopter's own call
                # sequence rather than inside the HAL library. The HAL's own
                # count is already known from the sweep; what is new here is
                # whether an OS driving that HAL adds any of its own.
                own = [e for e in inj["errors"] if not e["hal_files"]]
                cls["errors_in_hopters_own_code"] = len(own)
                cls["hopter_own_samples"] = [e["message"][:200] for e in own[:5]]
                print(f"  injected PAC : "
                      f"{'compiles' if inj['compiles'] else 'errors'}")
                print(f"    errors in HOPTER'S OWN call sequence: {len(own)}")
                print(f"    true enforcement : {cls['true_enforcement']}")
                print(f"    generic friction : {cls['generic_friction']}")
                print(f"    other            : {cls['other']}")
                for s in cls["samples"]["true_enforcement"][:4]:
                    print(f"      {s['message'][:110]}")
                result = {"facts": facts, "native": native, "baseline": "PASS",
                          "registers_gated": summary["registers_planned"],
                          "injected": cls}
        finally:
            ok = snap.restore_and_verify()
            print(f"  restored pristine: {ok}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "hopter.json").write_text(json.dumps(result, indent=1, default=str) + "\n")
    print(f"\nreport: {OUT / 'hopter.json'}")
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
