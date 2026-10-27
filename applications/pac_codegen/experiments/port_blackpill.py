#!/usr/bin/env python3
"""port_blackpill.py -- the first whole APPLICATION built against an injected PAC.

WHY THIS ONE
------------
Everything compile-confirmed so far is a library: driver crates (the sweep),
BSPs and board frameworks (the ports). What has never been measured is an
APPLICATION -- a binary with a main loop that selects a concrete feature set --
compiled end-to-end against an injected chip crate through an unmodified,
current HAL. trace_hal approximates that statically; this does it with the
compiler.

blackpill-usb-pwdstore is the first candidate the ecosystem re-sweep found
that can do it with NO port at all: an encrypted USB password store on an
STM32F411 (RM0383, in the corpus), pinning stm32f4xx-hal 0.23 -- the release
built against the PAC generation we inject -- on stable Rust. The whole
experiment is one [patch.crates-io] line.

WHAT A HIT MEANS HERE. The app's own source contains no direct register
access; every access is inside the HAL. So a gate that fires in this build is
a HAL site that THIS APPLICATION'S feature selection actually compiles --
monomorphised driver code its binary would contain, not driver code that
merely exists. The sweep asks "does the driver violate the rule anywhere";
this asks "does the part of the driver THIS app uses violate it". Sites are
attributed app vs HAL and triaged with the same static pass as everything
else.

Usage:
    python applications/pac_codegen/experiments/port_blackpill.py --work DIR
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
PHASE1D = Path("/home/ramla/hal_agent-phase-1d")
RM, DEVICE, PAC_CRATE = "rm0383", "stm32f411", "stm32f4"
REPO_URL = "https://github.com/sjm42/blackpill-usb-pwdstore"
TARGET = "thumbv7em-none-eabihf"
FEATURES = "black_pill"
TIMEOUT = 2400
CHECK = ["cargo", "check", "--target", TARGET, "--features", FEATURES]


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd and str(cwd), capture_output=True,
                          text=True, timeout=TIMEOUT)


def clone(dest: Path) -> Path:
    if dest.is_dir():
        run(["git", "checkout", "--", "."], cwd=dest)
        run(["git", "clean", "-fdq", "-e", "target"], cwd=dest)
        return dest
    run(["git", "clone", "-q", "--depth", "1", REPO_URL, str(dest)])
    return dest


def copy_pristine(src: Path, dest: Path) -> None:
    """Fresh mtimes, or cargo reuses the previous run's INJECTED artifacts
    against a pristine-on-disk tree (see port_stm32_eth.py)."""
    if dest.is_dir():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("target"))
    now = time.time()
    for p in dest.rglob("*"):
        try:
            os.utime(p, (now, now))
        except OSError:
            pass


def errors(app: Path) -> list:
    """A build that never ran is not a build with no errors."""
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


def patch_applied(app: Path) -> bool:
    """Cargo does not fail an unapplied [patch]; it warns and uses the
    registry crate, and the whole experiment silently measures nothing."""
    lock = app / "Cargo.lock"
    if not lock.is_file():
        return False
    block, hit = [], False
    for line in lock.read_text().splitlines() + ["[[package]]"]:
        if line.strip() == "[[package]]":
            if any(l == 'name = "stm32f4"' for l in block):
                hit = True
                if any(l.startswith("source = ") for l in block):
                    return False
            block = []
        else:
            block.append(line.strip())
    return hit


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    app = clone(work / "blackpill-usb-pwdstore")
    pac = work / "pac-f4"
    copy_pristine(APP_DIR / "vendored" / "pac" / PAC_CRATE, pac)

    man = app / "Cargo.toml"
    t = man.read_text()
    if "[patch.crates-io]" not in t:
        man.write_text(t + f'\n[patch.crates-io]\n'
                           f'stm32f4 = {{ path = "{pac}" }}\n')

    run(["cargo", "clean", "-p", PAC_CRATE], cwd=app)
    base = errors(app)
    if not patch_applied(app):
        sys.exit("the [patch] did not apply; nothing was measured")
    if base:
        sys.exit(f"BASELINE FAILS ({len(base)} errors) against the pristine "
                 f"0.16 crate -- a gate hit could not be told from breakage")
    print("baseline PASS (whole application, pristine 0.16 PAC, no port)")

    report = work / "blackpill_inject.json"
    saved = work / "blackpill_constraints.json"
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
    rep = json.loads(report.read_text())
    saved_c = json.loads(saved.read_text()) if saved.is_file() else {}
    gated_specs = sorted({f"{r['register'].upper()}rs"
                          for r in rep.get("rows", [])
                          if r.get("fate") == "planned"},
                         key=lambda s: (-len(s), s))

    run(["cargo", "clean", "-p", PAC_CRATE], cwd=app)
    # register (lower) -> precondition fields, per peripheral+register, from
    # the constraints that built the gates (measure_ported's fixed shape).
    fields_by = collections.defaultdict(set)
    for e in saved_c.get("registers", []):
        per = (e.get("peripheral") or "").lower()
        reg = (e.get("register") or "").lower()
        conds = [c for v in (e.get("preconditions") or {}).values() for c in v]
        conds += [c for fg in (e.get("gated_fields") or {}).values()
                  for c in (fg.get("preconditions") or [])]
        for c in conds:
            head = c.split()[0] if c.split() else ""
            f = head.rsplit(".", 1)[-1].lower()
            if f:
                fields_by[(per, reg)].add(f)
                fields_by[reg].add(f)

    # Everything up to and including the crate dir: the row should read
    # `stm32f4xx-hal/src/i2c.rs`, not a registry hash with the crate eaten.
    hal_re = re.compile(r"^.*/(stm32f4xx-hal)-[0-9.]+/")
    hits, collateral, friction = [], [], []
    for d in errors(app):
        h = enforcement.classify_diagnostic(d)
        spans = [s for s in d.get("spans") or [] if s.get("is_primary")]
        loc = spans[0]["file_name"] if spans else "?"
        line = spans[0]["line_start"] if spans else 0
        if h is None:
            collateral.append({"file": loc, "message": d["message"][:140]})
            continue
        # The sweep's enforcement/friction split, drawn the same way: a
        # witness-shaped error naming a gated register is a gate firing; one
        # naming none (`<Self as UartRB>::SRrs` on a generic path) is the
        # encoding's adoption cost in generic code, not a finding. The first
        # published record counted both as hits -- 39 where 30 are gates.
        # Longest-first so `BDCRrs` never resolves as `CRrs`.
        blob = d["message"] + " " + enforcement.span_labels(d)
        named = next((s for s in gated_specs if s in blob), None)
        if named is None and h.spec not in gated_specs:
            friction.append({"file": hal_re.sub(r"\1/", loc), "line": line,
                             "spec": h.spec})
            continue
        where = ("app" if not hal_re.search(loc) and loc.startswith("src")
                 else "hal")
        reg = h.spec.split("::")[-1].lower().removesuffix("rs")
        parts = [s for s in str(h.spec).split("::") if s]
        periph = parts[-3].lower() if len(parts) >= 3 else ""
        fields = sorted(fields_by.get((periph, reg)) or fields_by.get(reg) or [])
        verdict = "untriaged"
        p = Path(loc)
        if p.is_file() and fields:
            start, snip = corroboration.enclosing_function(str(p), line)
            verdict = corroboration.deterministic_scan(
                snip, line - start, fields)["verdict"]
        hits.append({"file": hal_re.sub(r"\1/", loc), "line": line,
                     "register": h.spec, "operation": h.operation,
                     "where": where, "fields": fields, "verdict": verdict})

    v = collections.Counter(x["verdict"] for x in hits)
    result = {
        "project": "blackpill-usb-pwdstore", "rm": RM, "device": DEVICE,
        "pac": f"{PAC_CRATE} 0.16.0", "hal": "stm32f4xx-hal 0.23",
        "baseline": "PASS", "mechanical_edits": 0,
        "registers_gated": rep.get("registers_planned"),
        "gate_fired": len(hits),
        "hits": hits, "collateral": len(collateral),
        "generic_friction": len(friction),
        "friction_detail": friction[:6],
        "collateral_detail": collateral[:8],
        "app_hits": sum(1 for x in hits if x["where"] == "app"),
        "guarded": v.get("corroborated", 0),
        "possible_bug": v.get("unchecked", 0),
        "triage_caveat":
            "the first whole APPLICATION measured end-to-end: a binary with "
            "a concrete feature set, built against the injected crate through "
            "an unmodified stm32f4xx-hal 0.23, zero mechanical edits. Every "
            "hit is HAL code that THIS app's feature selection actually "
            "monomorphises -- driver code its binary would contain, not "
            "driver code that merely exists. The app's own source contains "
            "no direct register access, so app-attributed hits would mean a "
            "constraint reached application code itself",
    }
    print(f"registers gated {result['registers_gated']}  gate fired "
          f"{len(hits)} (app {result['app_hits']}, hal "
          f"{len(hits)-result['app_hits']})  guarded {result['guarded']}  "
          f"possible bug {result['possible_bug']}  "
          f"friction {len(friction)}  collateral {len(collateral)}")
    for x in hits[:10]:
        print(f"    [{x['where']}] {x['file']}:{x['line']}  "
              f"{x['register']} {x['operation']}  {x['verdict']}")
    p = Path(args.out) if args.out else OUT / "port_blackpill.json"
    p.write_text(json.dumps(result, indent=1) + "\n")
    print(f"report: {p}")


if __name__ == "__main__":
    main()
