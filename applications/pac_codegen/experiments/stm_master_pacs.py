#!/usr/bin/env python3
"""Manuals whose chip crate exists only on stm32-rs master, not in a release.

Four manuals were listed for months as having no chip crate at all. They do:
stm32-rs master carries patch sets for every one of their devices, in two
crates -- `stm32wb0` (WB05/06/07/09) and `stm32wba` (WBA50/52/54/55) -- that
postdate the v0.16.0 tag the rest of the corpus is pinned to. Building them is
their own `make patch && make svd2rust && make form`; see
vendored/pac_master/README.md.

WHY THESE ARE MEASURED SEPARATELY FROM THE SWEEP

Not because the result is weaker, but because stm_sweep provisions crates from
crates.io through get_pac, and these have no release to provision. None of them
has a driver either -- nothing on crates.io can depend on an unpublished crate
-- so the sweep's HAL machinery would sit idle. What is measurable is
enforceability: how many registers carry a gate, and whether the crate still
compiles with them in.

The PAC version reads `latest` rather than `0.16.0` wherever these appear, so a
reader can tell at a glance which rows come from a release and which from
master.

Like the sweep, this writes a per-device constraints file to
applications/pac_codegen/constraints/ via --save-constraints, and applies the
same --attribution-check. It did neither for a while: these four were the
only injected targets with no reviewable artifact, and the only ones whose
constraints were never checked for target attribution. Both are closed, which
moved their gate counts down -- the numbers here supersede any earlier
measurement of these manuals.

Usage:
    python applications/pac_codegen/experiments/stm_master_pacs.py
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
REPO = APP_DIR.parent.parent
OUT = APP_DIR / "experiments" / "out"
MASTER = APP_DIR / "vendored" / "pac_master"
PHASE1D = Path("/home/ramla/hal_agent-phase-1d")
TIMEOUT = 3600

# (manual, crate, device, rust target). One device per manual, the same rule
# the rest of the corpus follows.
TARGETS = [
    ("rm0493", "stm32wba", "stm32wba55", "thumbv8m.main-none-eabihf"),
    ("rm0505", "stm32wb0", "stm32wb09", "thumbv6m-none-eabi"),
    ("rm0529", "stm32wb0", "stm32wb05", "thumbv6m-none-eabi"),
    ("rm0530", "stm32wb0", "stm32wb06", "thumbv6m-none-eabi"),
]


def pristine(crate: str) -> Path:
    """A fresh copy. Injection is one-shot from a clean crate, and stm32wb0
    serves three of these manuals, so each needs its own."""
    src = MASTER / crate
    if not src.is_dir():
        sys.exit(f"missing {src}; build it per vendored/pac_master/README.md")
    work = OUT / "pac_master_work" / crate
    if work.exists():
        shutil.rmtree(work)
    work.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, work)
    return work


def inject(rm: str, pac_dir: Path, device: str, field: bool) -> dict:
    suffix = "_master_field" if field else "_master"
    report = OUT / f"{rm}_{device}{suffix}.json"
    argv = [sys.executable, str(APP_DIR / "inject_from_run.py"),
            str(PHASE1D / f"agent_output/stm/{rm}/1"),
            "--pac", str(pac_dir), "--device", device,
            "--svd-dir", str(PHASE1D / f"devices/stm/{rm}/svd/{device}.svd"),
            "--constraints",
            str(PHASE1D / f"evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl"),
            # Same evidence check the sweep applies. Its unique work is target
            # attribution: a quote that says "this bit" and anchors outside the
            # target register's section supports the claim neither textually
            # nor positionally, so the gate is dropped.
            "--attribution-check", str(PHASE1D / "chunked_datasheets/stm"),
            "--report", str(report),
            # The same durable per-device record the sweep writes. Without it
            # these four targets reported fate counts and a PASS but never
            # WHICH registers they gate, so the only injected targets with no
            # reviewable artifact were the four nobody can download a crate
            # for. Mode-suffixed, like the report.
            "--save-constraints",
            str(OUT / "constraints" / f"{rm}_{device}"
                f"{'_fieldgate' if field else ''}.json")]
    if field:
        argv.append("--field-level-gating")
    r = subprocess.run(argv, capture_output=True, text=True, cwd=str(REPO),
                       timeout=TIMEOUT)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout)[-600:]}
    return json.loads(report.read_text())


def compiles(pac_dir: Path, device: str, target: str) -> str:
    r = subprocess.run(
        ["cargo", "check", "--target", target, "--no-default-features",
         "--features", device],
        cwd=str(pac_dir), capture_output=True, text=True, timeout=TIMEOUT)
    return "PASS" if r.returncode == 0 else "FAIL"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=[])
    args = ap.parse_args()

    commit = (MASTER / "STM32RS_COMMIT")
    commit = commit.read_text().strip() if commit.is_file() else "unknown"
    print(f"stm32-rs master @ {commit[:12]}\n")

    results = []
    for rm, crate, device, target in TARGETS:
        if args.only and rm not in args.only:
            continue
        row = {"rm": rm, "pac": crate, "device": device,
               "pac_version": "latest", "stm32rs_commit": commit}
        for field in (False, True):
            work = pristine(crate)
            rep = inject(rm, work, device, field)
            key = "field" if field else "whole"
            if "error" in rep:
                row[f"{key}_error"] = rep["error"]
                row[f"{key}_registers"] = 0
                continue
            row[f"{key}_registers"] = rep.get("registers_planned", 0)
            row[f"{key}_fates"] = rep.get("fates", {})
            if not field:
                row["probe"] = compiles(work, device, target)
            shutil.rmtree(work, ignore_errors=True)
        print("%-8s %-9s %-12s whole=%-4s field=%-4s compiles=%s"
              % (rm, crate, device, row.get("whole_registers"),
                 row.get("field_registers"), row.get("probe")))
        results.append(row)

    shutil.rmtree(OUT / "pac_master_work", ignore_errors=True)
    p = OUT / "stm_master_pacs.json"
    p.write_text(json.dumps(results, indent=1))
    print(f"\nregisters gated: whole={sum(r.get('whole_registers',0) for r in results)}"
          f"  field={sum(r.get('field_registers',0) for r in results)}")
    print(f"report: {p}")


if __name__ == "__main__":
    main()
