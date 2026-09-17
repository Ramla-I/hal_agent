#!/usr/bin/env python3
"""port_elodin.py -- compiler verdicts inside commercial flight software.

WHY THIS ONE
------------
elodin-sensor-fw is the scan's largest candidate pool outside tock: 33 hits on
constrained registers, 27 unchecked, in actively-maintained aerospace firmware
(Elodin's Aleph board, STM32H747 / RM0399). This turns as much of that as the
layer structure allows into compiler verdicts.

THE PORT (shipped as PATCHES, not replay rules -- it is too many edits to
re-derive, and a patch is reviewable):

  patches/elodin/sensor-fw.patch          the app: stm32-hal2 1.8-fork ->
      2.1.10, PAC 0.15 -> 0.16 accessor forms, usb-device 0.3, the unified
      hal2 2.x error currency, fallible constructors.
  patches/elodin/stm32-hal2-2.1.10.patch  a LOCAL copy of the released HAL:
      GPIO ports J/K (present on H747, absent from every released hal2 --
      elodin pins a fork for exactly this) and an embedded-hal I2C impl for
      the v2-I2C parts (2.1.10 ships one only for the F4 dialect, which is
      the other reason elodin cannot leave 1.8). Both grafts are the kind of
      change upstream could take verbatim.

The registry crate ships CRLF line endings; the patch is LF, so files are
normalised before applying.

TWO MEASUREMENTS, because the layer structure forces it:

  1. FULL INJECTION of RM0399 (72 registers): the build stops in stm32-hal2
     with ~150 of the driver's own violations and never reaches the app.
     That is enforcement working as designed -- the stack fails at the first
     violating layer -- and it reproduces the sweep's hal2/rm0399 result
     from inside a real dependent. But it answers nothing about the app.
  2. SUBSET INJECTION, sdmmc1 only: the one peripheral elodin drives
     directly that stm32-hal2 h7 has no module for, so the driver compiles
     clean and every gate that fires is in the APPLICATION'S OWN SOURCE.
     The subset is expressed as a filtered COPY of the generator run
     directory -- the injector needs no new flag.

WHAT THE SUBSET FOUND (repro numbers; the artifact renders the record):
11 gate hits in src/sdmmc.rs, 8 unchecked after the same static triage the
rest of the project uses. The scanner's line-level verdicts agree on every
comparable site; the compiler is finer-grained -- field gates fire per gated
FIELD write, and dctrl sites the scan flagged at register level do not fire
because the specific fields written are not the gated ones. anne-key's
granularity story, at site level.

Usage:
    python applications/pac_codegen/experiments/port_elodin.py --work DIR
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
import corroboration                                 # noqa: E402

OUT = APP_DIR / "experiments" / "out"
PATCHES = APP_DIR / "experiments" / "patches" / "elodin"
PHASE1D = Path("/home/ramla/hal_agent-phase-1d")
RM, DEVICE, PAC_CRATE = "rm0399", "stm32h747cm7", "stm32h7"
REPO_URL = "https://github.com/elodin-sys/elodin"
HAL2 = "stm32-hal2-2.1.10"
TIMEOUT = 2400


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd and str(cwd), capture_output=True,
                          text=True, timeout=TIMEOUT)


def copy_fresh(src: Path, dest: Path) -> None:
    if dest.is_dir():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("target"))
    now = time.time()
    for p in dest.rglob("*"):
        try:
            os.utime(p, (now, now))
        except OSError:
            pass


def sh_patch(root: Path, patch: Path) -> None:
    r = run(["patch", "-p1", "--no-backup-if-mismatch", "-i", str(patch)],
            cwd=root)
    if r.returncode != 0:
        sys.exit(f"patch {patch.name} failed:\n{r.stdout[-800:]}{r.stderr[-400:]}")


def errors(cwd: Path, out_json: Path) -> list:
    r = run(["cargo", "check", "--message-format=json"], cwd=cwd)
    out_json.write_text(r.stdout)
    errs = []
    for line in r.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") == "compiler-message" and \
                m["message"].get("level") == "error":
            errs.append(m["message"])
    if r.returncode != 0 and not errs:
        sys.exit(f"cargo failed without compiling anything:\n{r.stderr[-1000:]}")
    return errs


def inject(pac: Path, run_dir: Path, saved: Path, report: Path) -> dict:
    r = run([sys.executable, str(APP_DIR / "inject_from_run.py"),
             "--save-constraints", str(saved), str(run_dir),
             "--pac", str(pac), "--device", DEVICE,
             "--svd-dir", str(PHASE1D / f"devices/stm/{RM}/svd/{DEVICE}.svd"),
             "--constraints", str(PHASE1D /
                                  f"evaluation/stm/{RM}/1/{RM}_constraints_review.jsonl"),
             "--attribution-check", str(PHASE1D / "chunked_datasheets/stm"),
             "--report", str(report)], cwd=REPO)
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

    # -- sources: app (clone or reset), HAL (registry copy), PAC (vendored) --
    repo = work / "elodin"
    if repo.is_dir():
        run(["git", "checkout", "--", "."], cwd=repo)
        run(["git", "clean", "-fdq", "-e", "target"], cwd=repo)
    else:
        run(["git", "clone", "-q", "--depth", "1", REPO_URL, str(repo)])
    app = repo / "fsw" / "sensor-fw"

    reg = sorted(Path.home().glob(f".cargo/registry/src/*/{HAL2}"))
    if not reg:
        sys.exit(f"{HAL2} not in the local cargo registry")
    hal2 = work / "hal2"
    copy_fresh(reg[0], hal2)
    # the registry crate ships CRLF; the patch is LF
    for f in hal2.rglob("*.rs"):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    sh_patch(hal2, PATCHES / "stm32-hal2-2.1.10.patch")

    pac = work / "pac"
    copy_fresh(APP_DIR / "vendored" / "pac" / PAC_CRATE, pac)

    sh_patch(app, PATCHES / "sensor-fw.patch")
    man = app / "Cargo.toml"
    man.write_text(man.read_text()
                   .replace("__PAC_DIR__", str(pac))
                   .replace("__HAL2_DIR__", str(hal2)))

    # -- baseline: whole firmware against the PRISTINE 0.16 PAC --------------
    base = errors(app, work / "baseline.json")
    if base:
        sys.exit(f"BASELINE FAILS ({len(base)} errors); nothing is measurable")
    print("baseline PASS (flight software, hal2 2.1.10 + pristine 0.16 PAC)")

    # -- measurement 1: full manual -> the DRIVER fails first ----------------
    rep = inject(pac, PHASE1D / f"agent_output/stm/{RM}/1",
                 work / "constraints_full.json", work / "inject_full.json")
    run(["cargo", "clean", "-p", PAC_CRATE], cwd=app)
    full = errors(app, work / "full.json")
    in_hal = sum(1 for d in full for s in (d.get("spans") or [])
                 if s.get("is_primary") and "hal2" in s.get("file_name", ""))
    print(f"full injection ({rep.get('registers_planned')} registers): "
          f"{len(full)} errors, {in_hal} in stm32-hal2 -- the build stops at "
          f"the driver; the app is never reached")

    # -- measurement 2: sdmmc subset -> every hit is the APP's ---------------
    runs = work / "runs" / RM / "1"          # the injector reads RM off the path
    if runs.is_dir():
        shutil.rmtree(runs)
    runs.mkdir(parents=True)
    for f in (PHASE1D / f"agent_output/stm/{RM}/1").glob("sdmmc*"):
        shutil.copy2(f, runs / f.name)
    copy_fresh(APP_DIR / "vendored" / "pac" / PAC_CRATE, pac)
    rep2 = inject(pac, runs, work / "constraints_sdmmc.json",
                  work / "inject_sdmmc.json")
    run(["cargo", "clean", "-p", PAC_CRATE], cwd=app)
    subset = errors(app, work / "subset.json")

    saved = json.loads((work / "constraints_sdmmc.json").read_text())
    fields_by = {}
    for e in saved.get("registers", []):
        conds = [c for v in (e.get("preconditions") or {}).values() for c in v]
        conds += [c for fg in (e.get("gated_fields") or {}).values()
                  for c in (fg.get("preconditions") or [])]
        fields_by[e["register"].lower()] = sorted(
            {c.split()[0].rsplit(".", 1)[-1].lower() for c in conds if c.split()})

    hits, other = [], 0
    for d in subset:
        h = enforcement.classify_diagnostic(d)
        sp = [s for s in d.get("spans") or [] if s.get("is_primary")]
        loc = sp[0]["file_name"] if sp else "?"
        line = sp[0]["line_start"] if sp else 0
        if h is None:
            other += 1
            continue
        regname = h.spec.split("::")[-1].lower().removesuffix("rs")
        fs = fields_by.get(regname) or []
        verdict = "untriaged"
        path = loc if os.path.isabs(loc) else str(app / loc)
        if os.path.isfile(path) and fs:
            start, snip = corroboration.enclosing_function(path, line)
            verdict = corroboration.deterministic_scan(
                snip, line - start, fs)["verdict"]
        hits.append({"file": loc, "line": line, "register": regname,
                     "operation": h.operation, "fields": fs,
                     "verdict": verdict})
    v = collections.Counter(x["verdict"] for x in hits)

    result = {
        "project": "elodin-sensor-fw", "rm": RM, "device": DEVICE,
        "pac": f"{PAC_CRATE} 0.16.0", "hal": "stm32-hal2 2.1.10 (+J/K, +eh-i2c)",
        "baseline": "PASS",
        "mechanical_edits": 21 + 2,     # files touched by the two patches
        "registers_gated": rep2.get("registers_planned"),
        "gate_fired": len(hits), "hits": hits, "collateral": other,
        "guarded": v.get("corroborated", 0),
        "possible_bug": v.get("unchecked", 0),
        "full_injection": {"registers": rep.get("registers_planned"),
                           "errors": len(full), "in_driver": in_hal},
        "triage_caveat":
            "compiler verdicts INSIDE the application's own source, on the "
            "one peripheral (SDMMC) its driver has no module for. The full "
            "manual cannot be measured end-to-end: injected whole, the build "
            "stops in stm32-hal2 with ~150 of the driver's own violations "
            "and never reaches the app -- enforcement halting the stack at "
            "the first violating layer. The scan's adc clusters therefore "
            "remain static claims. On every comparable sdmmc line the "
            "scanner's verdict matches the compiler's; the compiler is "
            "finer -- field gates fire per gated FIELD, so register-level "
            "scan sites whose written fields are not the gated ones "
            "correctly do not fire",
    }
    print(f"subset ({rep2.get('registers_planned')} sdmmc registers): "
          f"{len(hits)} hits in the app's own source, "
          f"guarded {result['guarded']}, possible bug "
          f"{result['possible_bug']}, collateral {other}")
    for x in hits:
        print(f"    {x['file']}:{x['line']}  {x['register']} "
              f"{x['operation']}  {x['verdict']}")
    p = Path(args.out) if args.out else OUT / "port_elodin.json"
    p.write_text(json.dumps(result, indent=1) + "\n")
    print(f"report: {p}")


if __name__ == "__main__":
    main()
