#!/usr/bin/env python3
"""Build the chip crates stm32-rs never published, so their gates can compile.

Five manuals in the corpus reach the end of extraction and stop: RM0475
(STM32MP13x) because the stm32mp1 crate ships only MP153/MP157, and four WB/WBA
manuals because stm32-rs publishes no crate for those families at all. Between
them they carry 675 constraints the validator judged enforceable and that
nothing has ever compiled.

Nothing about that is fundamental. A chip crate is generated from an SVD, we
have the SVDs -- the generator reads them to know what registers exist -- and
the tool is public. This runs the same pipeline stm32-rs runs:

    svd2rust 0.36.1  -g      the exact version the published 0.16 crates name
                             in their own doc header, so the emitted API is the
                             shape the injector is calibrated against
    form                     split the single lib.rs into per-peripheral files
    assemble                 nest under src/<device>/, generic.rs at the root,
                             cfg-gated module per device -- the stm32-rs layout
                             DeviceLayout already knows how to walk

WHAT WE LEARNED BY DOING IT. Generation works: 9 device modules across 4
manuals compile. Injection into them yields almost nothing, and the reason is
worth more than the crates are.

stm32-rs does not ship the vendor SVD. It ships the vendor SVD plus a large
layer of YAML patches, and those patches are load-bearing here. The raw
STM32WBA55 file gives SPI1.CRCPOLY no `<access>` element at all, so svd2rust
emits no `impl Writable` and the register is read-only in the generated crate;
the published stm32h7 crate has `impl crate::Writable` for the same register.
A write gate on a register the crate says cannot be written is not expressible,
so the injector drops it -- correctly. 62 of RM0493's registers go that way.
RM0475 does not even parse: its TIM2 CCMR1 declares an enumerated value of 8
in a 3-bit field.

So the missing piece was never the crate. It is the patched SVD, and the honest
conclusion is that these five manuals stay unenforceable until someone patches
their register maps -- which is what stm32-rs would have to do to publish them
anyway.

WHAT THIS DOES AND DOES NOT BUY. A generated crate is a real compile target:
gates go in, rustc checks them, and a constraint stops being a validator
opinion. It is NOT the artifact anyone depends on. stm32-rs crates are
generated from PATCHED SVDs -- vendor files with known errors corrected -- and
these are the raw vendor files, so the register maps may carry defects the
published crates do not. And no driver crate depends on a crate we made, so
there is no adoption measurement here, only enforceability.

Usage:
    python applications/pac_codegen/experiments/gen_pac.py --rm rm0505
    python applications/pac_codegen/experiments/gen_pac.py --all --check
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
OUT = APP_DIR / "experiments" / "out"
GEN = APP_DIR / "vendored" / "pac_generated"
PHASE1D = Path("/home/ramla/hal_agent-phase-1d")
SVD2RUST = Path("/tmp/claude-1006/-home-ramla-hal-agent-pac-injection/"
                "777dc301-e753-406b-a6c8-f0cf2b5598fe/scratchpad/"
                "svd2rust036/bin/svd2rust")
SVD2RUST_VERSION = "0.36.1"
TIMEOUT = 3600

# The manuals with no published chip crate, and the crate name we give the one
# we build. Named `<family>_gen` so it can never be mistaken for the crates.io
# crate in a Cargo.lock or a report.
# manual -> (crate name, why crates.io has none, target to type-check on).
# The target only has to match the ISA of the core the SVD describes; nothing
# is linked, so this is a type-check, not a build for real hardware.
CASES = {
    "rm0475": ("stm32mp13_gen", "stm32-rs ships stm32mp1 but no MP13x device",
               "thumbv7em-none-eabihf"),
    "rm0493": ("stm32wba_gen", "no crates.io crate for this family",
               "thumbv8m.main-none-eabihf"),
    "rm0505": ("stm32wb09_gen", "no crates.io crate for this family",
               "thumbv6m-none-eabi"),
    "rm0529": ("stm32wb05_gen", "no crates.io crate for this family",
               "thumbv6m-none-eabi"),
    "rm0530": ("stm32wb0x_gen", "no crates.io crate for this family",
               "thumbv6m-none-eabi"),
}

CARGO_TOML = """[package]
name = "{crate}"
version = "0.16.0"
edition = "2021"
description = "Generated from the vendor SVD with svd2rust {svdver}; NOT a crates.io crate"
license = "MIT OR Apache-2.0"

[dependencies]
cortex-m = "0.7.7"
vcell = "0.1.3"

[dependencies.cortex-m-rt]
version = "0.7.5"
optional = true

[dependencies.critical-section]
version = "1.0"
optional = true

[dependencies.portable-atomic]
version = "1"
optional = true
default-features = false

[features]
default = []
rt = ["cortex-m-rt/device"]
atomics = ["dep:portable-atomic"]
{device_features}
"""

LIB_RS = """#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
#![no_std]
mod generic;
pub use self::generic::*;
{modules}"""

# form emits one long line with spaces around every token, so nothing here can
# anchor to line starts or assume `mod generic;` is tight.
_INNER_ATTR_RE = re.compile(r"#!\s*\[[^\]]*\]")
_GENERIC_MOD_RE = re.compile(
    r"(?:#\s*\[\s*allow\s*\(\s*unused_imports\s*\)\s*\]\s*)?"
    r"(?:pub\s+)?mod\s+generic\s*;"
    r"|(?:#\s*\[\s*allow\s*\(\s*unused_imports\s*\)\s*\]\s*)?"
    r"use\s+generic\s*::\s*\*\s*;")
_DOC_GENERIC_RE = re.compile(
    r'#\s*\[\s*doc\s*=\s*"Common register and bit access and modify traits"\s*\]')


def svds(rm: str):
    d = PHASE1D / "devices" / "stm" / rm / "svd"
    return sorted(d.glob("*.svd"))


def generate_device(svd: Path, crate_dir: Path, device: str) -> None:
    """svd2rust + form for one SVD, nested under src/<device>/."""
    tmp = crate_dir / ".build" / device
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    # `legacy` is the ident theme stm32-rs publishes with, and it is not
    # cosmetic. The default `new` theme names the register spec `Awd2crSpec`
    # and the field reader `Awd2ch0R`; legacy names them `AWD2CRrs` and
    # `AWD2CH0_R`. The injector's emitter matches the published shape, so a
    # crate generated with the default theme compiles fine and then rejects
    # nearly every gate as "not expressible against the generated PAC" -- a
    # failure that looks like a constraint problem and is entirely a naming
    # one.
    r = subprocess.run([str(SVD2RUST), "-i", str(svd), "--target", "cortex-m",
                        "-g", "--ident-formats-theme", "legacy"],
                       cwd=str(tmp), capture_output=True, text=True,
                       timeout=TIMEOUT)
    if r.returncode != 0:
        raise RuntimeError(f"svd2rust failed for {svd.name}:\n"
                           f"{(r.stderr or r.stdout)[-1500:]}")

    formed = tmp / "formed"
    formed.mkdir()
    r = subprocess.run(["form", "-i", str(tmp / "lib.rs"), "-o", str(formed)],
                       capture_output=True, text=True, timeout=TIMEOUT)
    if r.returncode != 0:
        raise RuntimeError(f"form failed for {svd.name}:\n"
                           f"{(r.stderr or r.stdout)[-1500:]}")

    dev_dir = crate_dir / "src" / device
    if dev_dir.exists():
        shutil.rmtree(dev_dir)
    dev_dir.mkdir(parents=True)
    for item in formed.iterdir():
        if item.name == "lib.rs":
            continue
        shutil.move(str(item), str(dev_dir / item.name))

    # svd2rust writes for a CRATE ROOT, so a derived peripheral refers to the
    # one it derives from as `crate::gpioa::..`. Nested under src/<device>/
    # that path no longer exists, and the crate does not build. The published
    # crates carry `crate::stm32wl5x_cm4::gpioa::..`, so rewrite the same way.
    #
    # Only peripheral modules move: generic items (`crate::R`, `crate::Reg`,
    # `crate::Periph`) stay at the root and must not be touched. The set of
    # names to rewrite is the set of directories form just produced, so this
    # cannot rewrite a name that is not a peripheral of this device.
    periphs = sorted(d.name for d in dev_dir.iterdir() if d.is_dir())
    if periphs:
        pat = re.compile(r"\bcrate\s*::\s*(" + "|".join(
            re.escape(x) for x in periphs) + r")\b")
        for f in dev_dir.rglob("*.rs"):
            src = f.read_text()
            new = pat.sub(rf"crate :: {device} :: \1", src)
            if new != src:
                f.write_text(new)

    # form's lib.rs becomes the device module. Its inner attributes and its
    # `mod generic` belong to the crate root, which we write ourselves; left
    # here they would be an inner attribute in a non-root module (an error)
    # and a second copy of the generic module.
    body = (formed / "lib.rs").read_text()
    body = _INNER_ATTR_RE.sub("", body)
    body = _DOC_GENERIC_RE.sub("", body)
    body = _GENERIC_MOD_RE.sub("", body)
    if periphs:
        body = pat.sub(rf"crate :: {device} :: \1", body)
    (dev_dir / "mod.rs").write_text(body.lstrip("\n"))

    # generic.rs and the linker pieces are per-crate, not per-device.
    shutil.copy(tmp / "generic.rs", crate_dir / "src" / "generic.rs")
    for extra in ("build.rs", "device.x"):
        if (tmp / extra).is_file():
            shutil.copy(tmp / extra, crate_dir / extra)


def build_crate(rm: str) -> dict:
    crate, why, target = CASES[rm]
    files = svds(rm)
    if not files:
        return {"rm": rm, "error": "no SVD in the corpus"}
    crate_dir = GEN / crate
    if crate_dir.exists():
        shutil.rmtree(crate_dir)
    (crate_dir / "src").mkdir(parents=True)

    devices = []
    for svd in files:
        device = svd.stem.lower()
        print(f"    {svd.name} -> {device}", flush=True)
        generate_device(svd, crate_dir, device)
        devices.append(device)

    (crate_dir / "Cargo.toml").write_text(CARGO_TOML.format(
        crate=crate, svdver=SVD2RUST_VERSION,
        device_features="\n".join(f"{d} = []" for d in devices)))
    (crate_dir / "src" / "lib.rs").write_text(LIB_RS.format(
        modules="".join(f'#[cfg(feature = "{d}")]\npub mod {d};\n'
                        for d in devices)))
    shutil.rmtree(crate_dir / ".build", ignore_errors=True)
    return {"rm": rm, "crate": crate, "devices": devices, "target": target,
            "why_no_published_crate": why, "path": str(crate_dir)}


def check(info: dict) -> dict:
    """Every device feature must compile, not just the first."""
    results = {}
    for d in info["devices"]:
        r = subprocess.run(
            ["cargo", "check", "--target", info["target"],
             "--no-default-features", "--features", d,
             "--message-format=short"],
            cwd=info["path"], capture_output=True, text=True, timeout=TIMEOUT)
        errs = [l for l in (r.stderr or "").splitlines() if ": error" in l]
        results[d] = "PASS" if r.returncode == 0 else f"FAIL ({len(errs)})"
        if r.returncode != 0:
            info.setdefault("errors", {})[d] = errs[:8]
    info["compiles"] = results
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rm", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not SVD2RUST.is_file():
        sys.exit(f"svd2rust {SVD2RUST_VERSION} not found at {SVD2RUST}\n"
                 f"install with: cargo install svd2rust --version "
                 f"{SVD2RUST_VERSION} --root <dir> --locked")

    rms = list(CASES) if args.all else args.rm
    if not rms:
        sys.exit("pass --rm <manual> or --all")

    results = []
    for rm in rms:
        if rm not in CASES:
            sys.exit(f"{rm} has a published crate already; nothing to generate")
        print(f"=== {rm} -> {CASES[rm][0]} ===", flush=True)
        try:
            info = build_crate(rm)
        except Exception as e:                                # noqa: BLE001
            print(f"    FAILED: {e}", flush=True)
            results.append({"rm": rm, "error": str(e)[:500]})
            continue
        if args.check and "error" not in info:
            info = check(info)
            print(f"    compiles: {info['compiles']}", flush=True)
        results.append(info)

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "gen_pac.json"
    p.write_text(json.dumps(results, indent=1))
    print(f"\nreport: {p}")


if __name__ == "__main__":
    main()
