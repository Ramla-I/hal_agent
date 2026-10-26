#!/usr/bin/env python3
"""port_stm32_eth.py -- confirming a TRUE NEGATIVE against the compiler.

WHY THIS ONE
------------
anne-key checked the scanner where it claims a hit. This checks it where it
claims none. stm32-eth is an Ethernet MAC/DMA driver that programs 104
registers directly across 37 distinct ones, and the scan reports ZERO on
constrained registers. A zero from a text matcher is the easiest kind of number
to be wrong about, so it is worth making a compiler say it.

The gap was also the smallest left in the corpus, and only visible after the
scan started reading pinned versions out of manifests: stm32-eth pins
stm32f4 0.15 against the injector's 0.16, one minor version. It reaches the PAC
through stm32f4xx-hal 0.21, so the port is really a HAL bump to 0.23 -- the
release the sweep already builds against PAC 0.16.

RESULT

    baseline (pristine 0.16 PAC)                  0 errors
    injected, 24 gated registers from RM0386
      gate hits in stm32-eth's own source         0
      gate hits in stm32f4xx-hal                 49
      non-gate errors anywhere                    0

The scan's zero holds, and it is explained rather than merely observed: RM0386
constrains ADC1, CAN1, CRYP, DSI, I2C1, IWDG, QUADSPI, RNG, SPI1 and USART1,
and stm32-eth touches ETH_MAC, ETH_DMA and ETH_PTP. No overlap. The 49 hits are
the HAL's own, which the sweep measures separately; zero collateral errors means
injecting into a PAC this driver depends on cost it nothing.

TWO WAYS THIS DRIVER WOULD EVADE THE GATE
-----------------------------------------
Neither costs a finding here, because the registers involved are not
constrained in any of the 49 targets -- but both are real limits of the
mechanism and were found by reading code the port forced us to read.

  BIT BANDING. `bb::set(register: *const T, bit: u8)` writes a register
  through a RAW POINTER. Our enforcement is a trait bound on `Reg<REG>`'s
  methods, so a write that never calls `Reg::write` is never checked.
  stm32-eth drives RCC_AHB1ENR, RCC_AHB1RSTR, RCC_APB2ENR and SYSCFG_PMC this
  way. None of those four is constrained in any target we have, so nothing is
  lost today; a manual that constrained one would produce a silent miss.

  A GENERIC RE-WRAPPER. `DelayedReg<T: RegisterSpec>` re-exports read, modify
  and write with a 29-cycle delay for a silicon erratum. It calls
  `Reg<REG>`'s methods from ONE generic body, so a gate on any wrapped register
  fails to compile in the wrapper rather than at the access site. The violation
  is still caught -- it is a compile error either way -- but it is reported
  once, in library code, pointing at no particular caller.

THE PORT: stm32f4 0.15 -> 0.16 via stm32f4xx-hal 0.21 -> 0.23, 63 errors, all
in stm32-eth's own source. Every rule dictated by a compiler error:

  R0  `resolver = "2"`. THE BLOCKER, and not a PAC issue at all. stm32-eth is
      edition 2018 with no resolver key, so Cargo unifies features across
      normal, build and dev dependencies. cortex-m's
      `critical-section-single-core` selects `restore-state-u32` while another
      edge selects `restore-state-bool`, and critical-section refuses to
      compile with two widths. The error names critical-section and looks like
      a dependency conflict; the fix is one line in the manifest.
  R1  Register spec types renamed: `MACCR_SPEC` -> `MACCRrs`. 45 of the 63.
  R2  `Readable` no longer carries associated `Reader`/`Writer` types; the
      reader and writer are the free-standing `R<REG>` and `W<REG>`.
  R3  `modify`/`write` return the written value where they returned ().
  R4  Register-block fields became accessor methods, applied from the names
      rustc asks for. R4b: `bb::set(&rcc.apb2enr, BIT)` wants `*const T` --
      in 0.15 the register was a field so `&` made the reference, in 0.16 the
      accessor returns one, so the `&` goes rather than parens being appended.
  R5  Field writers' `bits()` is unsafe where it was safe, including two
      multi-line writer chains where the unsafe block wraps the whole closure.

Usage:
    python applications/pac_codegen/experiments/port_stm32_eth.py --work DIR
"""

import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
REPO = APP_DIR.parent.parent
sys.path.insert(0, str(APP_DIR / "experiments"))
import enforcement                                   # noqa: E402

OUT = APP_DIR / "experiments" / "out"
PHASE1D = Path("/home/ramla/hal_agent-phase-1d")
RM, DEVICE, PAC_CRATE = "rm0386", "stm32f469", "stm32f4"
REPO_URL = "https://github.com/stm32-rs/stm32-eth"
TARGET = "thumbv7em-none-eabihf"
FEATURES = "stm32f469"
TIMEOUT = 2400
CHECK = ["cargo", "check", "--target", TARGET, "--no-default-features",
         "--features", FEATURES]


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd and str(cwd), capture_output=True,
                          text=True, timeout=TIMEOUT)


def clone(dest: Path) -> Path:
    """Clone, or reset an existing clone. The port is a sequence of textual
    edits and re-running them on already-ported source does not compose."""
    if dest.is_dir():
        run(["git", "checkout", "--", "."], cwd=dest)
        run(["git", "clean", "-fdq", "-e", "target"], cwd=dest)
        return dest
    run(["git", "clone", "-q", "--depth", "1", REPO_URL, str(dest)])
    return dest


def errors(app: Path) -> list:
    """Compiler errors, and a hard stop if the compiler never ran -- cargo
    exits before compiling on a bad manifest and emits no diagnostics, which
    would read as a clean build."""
    r = run(CHECK + ["--message-format=json"], cwd=app)
    out = []
    for line in r.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") == "compiler-message" and \
                m["message"].get("level") == "error":
            out.append(m["message"])
    if r.returncode != 0 and not out:
        sys.exit(f"cargo exited without compiling anything:\n"
                 f"{(r.stderr or r.stdout)[-1200:]}")
    return out


def port(app: Path, pac: Path) -> dict:
    counts = {}
    man = app / "Cargo.toml"
    t = man.read_text()
    t = t.replace('stm32f4xx-hal = { version = "0.21", optional = true }',
                  'stm32f4xx-hal = { version = "0.23", optional = true }')
    t = t.replace('stm32f4 = { version = "0.15", optional = true }',
                  'stm32f4 = { version = "0.16", optional = true }')
    if "resolver" not in t:                                          # R0
        t = t.replace('edition = "2018"', 'edition = "2018"\nresolver = "2"', 1)
    if "[patch.crates-io]" not in t:
        t += f'\n[patch.crates-io]\nstm32f4 = {{ path = "{pac}" }}\n'
    man.write_text(t)

    src = app / "src"
    n = 0
    for f in sorted(src.rglob("*.rs")):                              # R1
        s = f.read_text()
        s, k = re.subn(r"\b([A-Z][A-Z0-9_]*?)_SPEC\b",
                       lambda m: m.group(1) + "rs", s)
        n += k
        if k:
            f.write_text(s)
    counts["spec_renames"] = n

    p = src / "peripherals.rs"                                       # R2, R3
    s = p.read_text()
    for old, new in (
        ("use stm32f4::{Readable, Reg, RegisterSpec, Resettable, Writable, W};",
         "use stm32f4::{Readable, Reg, RegisterSpec, Resettable, Writable, R, W};"),
        ("pub fn read(&self) -> REG::Reader {", "pub fn read(&self) -> R<REG> {"),
        ("for<'w> F: FnOnce(&REG::Reader, &'w mut REG::Writer) -> &'w mut W<REG>,",
         "for<'w> F: FnOnce(&R<REG>, &'w mut W<REG>) -> &'w mut W<REG>,"),
        ("F: FnOnce(&mut REG::Writer) -> &mut W<REG>,",
         "F: FnOnce(&mut W<REG>) -> &mut W<REG>,"),
        ("            self.inner.modify(f)\n", "            self.inner.modify(f);\n"),
        ("            self.inner.write(f)\n", "            self.inner.write(f);\n"),
    ):
        s = s.replace(old, new)
    p.write_text(s)

    # R4: the accessor list comes from rustc, never from a guess.
    NAME = re.compile(r"(?:method|field) `([a-z0-9_]+)` (?:on type|of struct)")
    seen = {}
    for rnd in range(1, 9):
        err = run(CHECK, cwd=app).stderr
        names = sorted(set(NAME.findall(err)))
        if not names:
            break
        touched = 0
        for f in sorted(src.rglob("*.rs")):
            s = f.read_text()
            b = s
            for name in names:
                s = re.sub(rf"\.{name}\.(?![a-z_]*\()", f".{name}().", s)
                s = re.sub(rf"\.{name}\.(\w)", rf".{name}().\1", s)
                s = re.sub(rf"\.{name}\n(\s*)\.", rf".{name}()\n\1.", s)
                # R4b: `&rcc.apb2enr` -> `rcc.apb2enr()`, for *const T
                s = re.sub(rf"&(\w+)\.{name}\b(?!\()", rf"\1.{name}()", s)
            if s != b:
                f.write_text(s)
                touched += 1
        seen[rnd] = names
        if not touched:
            break
    counts["accessor_rounds"] = seen

    n = 0
    for f in sorted(src.rglob("*.rs")):                              # R5
        s = f.read_text()
        b = s
        s, k = re.subn(r"(\.write\(\|w\| )(w\.\w+\(\)\.bits\([^;]*?\))(\);)",
                       lambda m: f"{m.group(1)}unsafe {{ {m.group(2)} }}{m.group(3)}", s)
        n += k
        s, k = re.subn(r"(\.modify\(\|_, w\| )(w\.\w+\(\)\.bits\([^;]*?\))(\);)",
                       lambda m: f"{m.group(1)}unsafe {{ {m.group(2)} }}{m.group(3)}", s)
        n += k
        s, k = re.subn(r"\.modify\(\|_, w\| \{\n(\s*)w\.",
                       r".modify(|_, w| unsafe {\n\1w.", s)
        n += k
        s, k = re.subn(r"\.write\(\|w\| \{\n(\s*)w\.",
                       r".write(|w| unsafe {\n\1w.", s)
        n += k
        if s != b:
            f.write_text(s)
    counts["unsafe_bits"] = n
    # One writer chain the patterns above do not reach: a bare `w.pt().bits(..)`
    # as the sole expression of an already-braced closure.
    m = src / "mac" / "mod.rs"
    s = m.read_text()
    if "            w.pt().bits(0x100)" in s:
        m.write_text(s.replace("            w.pt().bits(0x100)",
                               "            unsafe { w.pt().bits(0x100) }"))
        counts["unsafe_bits"] += 1
    return counts


def copy_pristine(src: Path, dest: Path) -> None:
    """Copy the vendored crate, then stamp every file as just-written.

    `shutil.copytree` preserves mtimes, so a freshly restored PRISTINE tree
    looks OLDER than the injected build cargo has cached, and cargo reuses the
    injected artifacts -- a baseline that failed with gate errors against a
    crate carrying no gates, on one run out of two. `cargo clean -p` does not
    save you: the crates that DEPEND on the PAC are fingerprinted on its
    mtimes, so they stay stale too. Touching the tree is what actually tells
    cargo the contents changed."""
    if dest.is_dir():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("target"))
    now = time.time()
    for p in dest.rglob("*"):
        try:
            os.utime(p, (now, now))
        except OSError:
            pass
    os.utime(dest, (now, now))


def inject(pac: Path, work: Path) -> dict:
    report, saved = work / "eth_inject.json", work / "eth_constraints.json"
    r = run([sys.executable, str(APP_DIR / "inject_from_run.py"),
             "--save-constraints", str(saved),
             str(PHASE1D / f"agent_output/stm/{RM}/1"),
             "--pac", str(pac), "--device", DEVICE,
             "--svd-dir", str(PHASE1D / f"devices/stm/{RM}/svd/{DEVICE}.svd"),
             "--constraints", str(PHASE1D /
                                  f"evaluation/stm/{RM}/1/{RM}_constraints_review.jsonl"),
             "--attribution-check", str(PHASE1D / "chunked_datasheets/stm"),
             "--report", str(report)])
    if r.returncode != 0:
        sys.exit(f"injection failed:\n{(r.stderr or r.stdout)[-800:]}")
    return json.loads(report.read_text())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    app = clone(work / "stm32-eth")
    # A COPY: the shared vendored crate feeds every other measurement here.
    pac = work / "pac-f4"
    copy_pristine(APP_DIR / "vendored" / "pac" / PAC_CRATE, pac)

    counts = port(app, pac)
    # BEFORE the baseline, not only after injection. The PAC on disk is freshly
    # pristine, but cargo's cache is not: a re-run in the same work directory
    # reused the .rmeta from the previous run's INJECTED crate and the baseline
    # failed with 49 gate errors against a crate that carries no gates.
    run(["cargo", "clean", "-p", PAC_CRATE], cwd=app)
    base = errors(app)
    if base:
        sys.exit(f"BASELINE FAILS ({len(base)} errors) -- a gate hit could not "
                 f"be told from a port defect, so nothing is measurable")
    print("baseline PASS (0 errors against the pristine 0.16 PAC)")

    rep = inject(pac, work)
    # The injector rewrote the tree cargo cached; a stale .rmeta would report
    # gates from a crate that is pristine on disk.
    run(["cargo", "clean", "-p", PAC_CRATE], cwd=app)

    own, hal, other = collections.Counter(), 0, []
    for d in errors(app):
        h = enforcement.classify_diagnostic(d)
        spans = [s for s in d.get("spans") or [] if s.get("is_primary")]
        loc = spans[0]["file_name"] if spans else "?"
        if h is None:
            other.append({"file": loc, "message": d["message"][:140]})
        elif loc.startswith("src/"):
            own[f"{loc}:{spans[0]['line_start']} {h.spec}.{h.field} {h.operation}"] += 1
        else:
            hal += 1

    result = {
        "project": "stm32-eth", "rm": RM, "device": DEVICE,
        "pac": f"{PAC_CRATE} 0.16.0", "hal": "stm32f4xx-hal 0.23.0",
        "baseline": "PASS", "port": counts,
        # The landscape page renders one shape for every measured project.
        "mechanical_edits": (counts.get("spec_renames", 0)
                             + counts.get("unsafe_bits", 0)
                             + sum(len(v) for v in
                                   (counts.get("accessor_rounds") or {}).values())
                             + 7),   # the manifest and generic-API edits
        "registers_gated": rep.get("registers_planned"),
        "gate_fired": sum(own.values()),
        "hits": [{"file": k.split()[0], "line": 0, "register": k.split()[1],
                  "operation": k.split()[-1], "verdict": "n/a"}
                 for k in own],
        "gate_fired_in_hal": hal,
        "collateral": len(other), "collateral_detail": other[:8],
        "triage_caveat":
            "a confirmed TRUE NEGATIVE: the scan reported 0 hits and the "
            "compiler agrees. RM0386 constrains ADC1, CAN1, CRYP, DSI, I2C1, "
            "IWDG, QUADSPI, RNG, SPI1 and USART1; stm32-eth touches ETH_MAC, "
            "ETH_DMA and ETH_PTP, so there is no overlap to fire on. The "
            f"{hal} hits are stm32f4xx-hal's own, measured separately by the "
            "sweep. Two access paths in this driver would evade the gate if a "
            "constrained register ever went through them: bit banding, which "
            "writes via a raw pointer and so never calls Reg::write, and the "
            "DelayedReg<T> wrapper, which would fail to compile in one generic "
            "body rather than at the call site. Neither costs a finding here",
    }
    print(f"registers gated {result['registers_gated']}  "
          f"hits in stm32-eth {result['gate_fired']}  "
          f"hits in the HAL {hal}  collateral {len(other)}")
    p = Path(args.out) if args.out else OUT / "port_stm32_eth.json"
    p.write_text(json.dumps(result, indent=1) + "\n")
    print(f"report: {p}")


if __name__ == "__main__":
    main()
