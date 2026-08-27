#!/usr/bin/env python3
"""Would a new svd2rust break the injector? Answer it by running it.

The corpus is pinned to stm32-rs v0.16.0, whose crates are generated with
svd2rust 0.36.1 -- the version stamped in all 21 vendored crates. That pin is
deliberate: v0.16.0 is the latest TAG, so it is what every downstream project
resolves to, and adoption numbers only mean something measured against crates
real projects depend on. stm32-rs master has since moved to a newer svd2rust,
and will eventually cut a release from it.

The question that matters is not "which version is newest" but "does the API
the injector matches on still exist, and still look the same". That is
checkable, so this checks it rather than arguing it.

FIVE INVARIANTS. The emitter reads and writes exactly these shapes; nothing
else about the generated code concerns it:

  1. register spec types      `CR1rs`      what a gate is implemented ON
  2. field reader types       `UE_R`       how a precondition is READ
  3. field writer types       `UE_W`       how a gated field is WRITTEN
  4. access traits            `impl crate::Writable for ..`, Readable,
                              Resettable -- which operations exist to gate
  5. the Bit1C marker         write-1-to-clear fields, which need
                              `clear_bit_by_one` rather than `set_bit`

A generator change that leaves all five intact cannot break the injector. One
that changes any of them needs emitter work -- which is not hypothetical: the
0.14 -> 0.16 jump turned register-block fields into accessor methods, and that
one change cost four community HALs a full port (experiments/port_hal.py).

TWO MODES.

  --compare   generate the same SVDs with the pinned baseline and a candidate
              svd2rust, and diff the five shapes. Exact set equality is
              expected: same input, same names. Exits non-zero on any
              difference, so it can gate a version bump.

  --ground    check the five shapes are actually present in the PUBLISHED
              crates we inject into. This is the one that catches a wrong
              assumption in the emitter itself rather than a change upstream:
              if an invariant is missing from a crate we already inject into,
              it was never an invariant.

Usage:
    python applications/pac_codegen/experiments/check_pac_generation.py --ground
    python applications/pac_codegen/experiments/check_pac_generation.py \\
        --compare --candidate $(which svd2rust)
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
OUT = APP_DIR / "experiments" / "out"
VENDORED = APP_DIR / "vendored" / "pac"
PHASE1D = Path("/home/ramla/hal_agent-phase-1d")
TIMEOUT = 1800

# The generator the pinned corpus was built with, per the doc header in all 21
# vendored crates. `--ident-formats-theme legacy` is not optional: the default
# theme names a spec `Cr1Spec` instead of `CR1rs`, and a crate generated that
# way compiles cleanly while being invisible to the emitter.
BASELINE = Path("/tmp/claude-1006/-home-ramla-hal-agent-pac-injection/"
                "777dc301-e753-406b-a6c8-f0cf2b5598fe/scratchpad/"
                "svd2rust036/bin/svd2rust")
BASELINE_VERSION = "0.36.1"
SVD2RUST_ARGS = ["--target", "cortex-m", "-g", "--ident-formats-theme", "legacy"]

# A sample spanning generations and core types, not one convenient chip: F1 is
# the oldest register style in the corpus, H7 the largest, WL dual-core.
SAMPLE = [
    ("rm0008", "stm32f103"), ("rm0090", "stm32f429"),
    ("rm0440", "stm32g474"), ("rm0433", "stm32h753v"),
    ("rm0453", "stm32wl5x_cm4"),
]

INVARIANTS = {
    "register spec types": re.compile(r"\b([A-Z][A-Z0-9_]*rs)\b"),
    "field readers (_R)": re.compile(r"\b([A-Z][A-Z0-9_]*_R)\b"),
    "field writers (_W)": re.compile(r"\b([A-Z][A-Z0-9_]*_W)\b"),
    "impl Writable": re.compile(r"impl\s+crate\s*::\s*Writable\s+for\s+(\w+)"),
    "impl Readable": re.compile(r"impl\s+crate\s*::\s*Readable\s+for\s+(\w+)"),
    "impl Resettable": re.compile(r"impl\s+crate\s*::\s*Resettable\s+for\s+(\w+)"),
    "Bit1C marker": re.compile(r"\b(Bit1C)\b"),
}


def shapes(text: str) -> dict:
    return {name: set(rx.findall(text)) for name, rx in INVARIANTS.items()}


def generate(binary: Path, svd: Path, into: Path) -> str:
    into.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([str(binary), "-i", str(svd)] + SVD2RUST_ARGS,
                       cwd=str(into), capture_output=True, text=True,
                       timeout=TIMEOUT)
    if r.returncode != 0:
        raise RuntimeError(f"{binary} failed on {svd.name}:\n"
                           f"{(r.stderr or r.stdout)[-800:]}")
    return (into / "lib.rs").read_text() + (into / "generic.rs").read_text()


def version_of(binary: Path) -> str:
    r = subprocess.run([str(binary), "--version"], capture_output=True,
                       text=True, timeout=60)
    return (r.stdout or r.stderr).strip()


def ground() -> dict:
    """Are the five shapes actually present in the crates we inject into?"""
    results, failed = [], False
    for crate_dir in sorted(VENDORED.iterdir()):
        src = crate_dir / "src"
        if not src.is_dir():
            continue
        # Read until every invariant has been seen at least once, rather than
        # capping at an arbitrary file count. stm32f4 has 5401 files and
        # rglob's order put every register file outside the first 400, so a
        # cap reported five crates as missing shapes they plainly have -- the
        # check failing rather than the crates.
        found = {k: 0 for k in INVARIANTS}
        scanned = 0
        for f in src.rglob("*.rs"):
            scanned += 1
            for k, v in shapes(f.read_text(errors="ignore")).items():
                found[k] += len(v)
            if all(found.values()):
                break
        missing = [k for k, n in found.items() if n == 0]
        if missing:
            failed = True
        results.append({"crate": crate_dir.name, "counts": found,
                        "files_scanned": scanned, "missing": missing})
        print("  %-10s %-4s (%d files scanned)"
              % (crate_dir.name, "OK" if not missing else "MISS", scanned)
              + (f"  MISSING {missing}" if missing else ""))
    return {"mode": "ground", "crates": results, "ok": not failed}


def compare(candidate: Path) -> dict:
    base_v, cand_v = version_of(BASELINE), version_of(candidate)
    print(f"  baseline  : {base_v}")
    print(f"  candidate : {cand_v}\n")
    rows, differing = [], False
    tmp = Path(tempfile.mkdtemp(prefix="svd2rust_cmp_"))
    try:
        for rm, device in SAMPLE:
            svd = PHASE1D / "devices" / "stm" / rm / "svd" / f"{device}.svd"
            if not svd.is_file():
                print(f"  {device:<15} SKIP (no SVD)")
                continue
            a = shapes(generate(BASELINE, svd, tmp / "base" / device))
            b = shapes(generate(candidate, svd, tmp / "cand" / device))
            diffs = {k: (sorted(a[k] - b[k])[:5], sorted(b[k] - a[k])[:5])
                     for k in a if a[k] != b[k]}
            if diffs:
                differing = True
            print("  %-15s %s" % (device, "identical" if not diffs
                                  else f"DIFFERS in {list(diffs)}"))
            for k, (only_a, only_b) in diffs.items():
                print(f"      {k}: only-baseline={only_a} only-candidate={only_b}")
            rows.append({"device": device,
                         "counts": {k: len(v) for k, v in a.items()},
                         "identical": not diffs,
                         "diffs": {k: {"only_baseline": x, "only_candidate": y}
                                   for k, (x, y) in diffs.items()}})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"mode": "compare", "baseline": base_v, "candidate": cand_v,
            "devices": rows, "ok": not differing}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ground", action="store_true",
                    help="check the invariants hold in the published crates")
    ap.add_argument("--compare", action="store_true",
                    help="diff a candidate svd2rust against the pinned one")
    ap.add_argument("--candidate", default=shutil.which("svd2rust") or "",
                    help="svd2rust to test (default: the one on PATH)")
    args = ap.parse_args()
    if not (args.ground or args.compare):
        sys.exit("pass --ground, --compare, or both")

    out = {}
    if args.ground:
        print("=== invariants in the published crates we inject into ===")
        out["ground"] = ground()
    if args.compare:
        if not BASELINE.is_file():
            sys.exit(f"pinned svd2rust {BASELINE_VERSION} not at {BASELINE};\n"
                     f"cargo install svd2rust --version {BASELINE_VERSION} "
                     f"--root <dir> --locked")
        if not args.candidate:
            sys.exit("no candidate svd2rust found; pass --candidate PATH")
        print("\n=== candidate vs pinned generator ===")
        out["compare"] = compare(Path(args.candidate))

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "check_pac_generation.json"
    p.write_text(json.dumps(out, indent=1))
    ok = all(v.get("ok") for v in out.values())
    print(f"\nreport: {p}")
    print("RESULT:", "the injector's assumptions hold" if ok
          else "SOMETHING MOVED — the emitter needs review")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
