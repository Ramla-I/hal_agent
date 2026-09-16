#!/usr/bin/env python3
"""What the gates find in HALs that only became measurable after the upgrade.

port_hal.py moves a released HAL onto PAC 0.16 -- the generation the injector
targets -- using only edits the compiler or the PAC dictates. This script then
does the actual experiment on those HALs: for each (manual, chip) pair it takes
the PRISTINE PAC, checks the HAL builds clean against it, injects that manual's
constraints, and rebuilds.

The baseline matters more than usual here. These HALs were ported by us, so
"it does not compile" has two possible causes, and only one of them is a
result. A pairing whose baseline is not zero is reported and skipped rather
than counted.

Each surviving error is triaged the way the rest of the project triages its
own, with corroboration.deterministic_scan: `guarded` means the driver does
establish the precondition nearby, `possible bug` means no check was found.

Usage:
    python applications/pac_codegen/experiments/measure_ported.py
    python applications/pac_codegen/experiments/measure_ported.py --only rm0367
"""

import argparse
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
REPO = APP_DIR.parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "experiments"))
import get_pac                                    # noqa: E402
import corroboration                              # noqa: E402

WS = APP_DIR / "experiments" / "ported"
OUT = APP_DIR / "experiments" / "out"
PHASE1D = Path("/home/ramla/hal_agent-phase-1d")
TIMEOUT = 2400

# (manual, PAC crate, PAC device, HAL, cargo features, rust target)
PAIRINGS = [
    ("rm0367", "stm32l0", "stm32l0x3", "stm32l0xx-hal",
     "stm32l0x3,mcu-STM32L053C6Tx", "thumbv6m-none-eabi"),
    ("rm0376", "stm32l0", "stm32l0x2", "stm32l0xx-hal",
     "stm32l0x2,mcu-STM32L052C6Tx", "thumbv6m-none-eabi"),
    ("rm0377", "stm32l0", "stm32l0x1", "stm32l0xx-hal",
     "stm32l0x1,mcu-STM32L011D3Px", "thumbv6m-none-eabi"),
    ("rm0091", "stm32f0", "stm32f0x1", "stm32f0xx-hal",
     "stm32f051", "thumbv6m-none-eabi"),
    ("rm0360", "stm32f0", "stm32f0x0", "stm32f0xx-hal",
     "stm32f030x8", "thumbv6m-none-eabi"),
]
# RM0451 (stm32l0x0) has no matching stm32l0xx-hal feature -- the HAL supports
# stm32l0x1/x2/x3 only -- so it stays unpaired and is NOT silently dropped.
UNPAIRED = {"rm0451": "stm32l0xx-hal 0.10.0 has no stm32l0x0 feature"}

_CONSTRAINED_RE = re.compile(r"`([^`]+)` is (\w+)-constrained by its datasheet")
# A WHOLE-REGISTER gate fires as E0277 on a missing marker trait, and the
# datasheet sentence rides in the message. A FIELD gate adds a witness
# parameter to the field's writer, so calling it is an ARITY error with no
# custom text; the witness TYPE is the only thing naming the register, and it
# sits in a span LABEL: "argument #1 of type `&CrHsebypFieldWitness` is
# missing". Matching the message alone counted every field-gate violation as
# collateral -- the bucket meaning the encoding broke something unrelated.
_FIELD_WITNESS_RE = re.compile(r"&(\w+?)([A-Z]\w*)FieldWitness")


def _field_hit(d: dict):
    """(register, field) if this diagnostic is a field gate firing, else None."""
    if (d.get("code") or {}).get("code") != "E0061":
        return None
    spans = list(d.get("spans", [])) + [
        sp for ch in d.get("children", []) for sp in ch.get("spans", [])]
    for sp in spans:
        m = _FIELD_WITNESS_RE.search(sp.get("label") or "")
        if m:
            return m.group(1).lower(), m.group(2).lower()
    return None


def check(hal: str, features: str, target: str, pac: str) -> list:
    """Errors from a clean build. The PAC's cached build is dropped first:
    the injector rewrites that same tree, so a stale .rmeta reports gates from
    a PAC that is pristine on disk."""
    subprocess.run(["cargo", "clean", "-p", pac], cwd=str(WS),
                   capture_output=True, text=True, timeout=TIMEOUT)
    run = subprocess.run(
        ["cargo", "check", "-p", hal, "--target", target,
         "--no-default-features", "--features", features,
         "--message-format=json"],
        cwd=str(WS), capture_output=True, text=True, timeout=TIMEOUT)
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
        out.append(d)
    return out


def inject(rm: str, pac: str, device: str, register_only: bool = False) -> dict:
    # Separate trees, never a filename suffix -- the two modes plan different
    # gate sets, and a shared path once let one overwrite the other's numbers.
    root = (OUT / "register_only") if register_only else OUT
    root.mkdir(parents=True, exist_ok=True)
    report = root / f"{rm}_{device}_ported.json"
    saved = root / f"{rm}_{device}_ported_constraints.json"
    argv = [sys.executable, str(APP_DIR / "inject_from_run.py"),
            "--save-constraints", str(saved),
            str(PHASE1D / f"agent_output/stm/{rm}/1"),
            "--pac", str(APP_DIR / "vendored" / "pac" / pac),
            "--device", device,
            "--svd-dir", str(PHASE1D / f"devices/stm/{rm}/svd/{device}.svd"),
            "--constraints",
            str(PHASE1D / f"evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl"),
            "--attribution-check", str(PHASE1D / "chunked_datasheets/stm"),
            "--report", str(report)]
    # Field gating is the default; --register-only is the baseline. This script
    # predates the flag and so measured only one mode, silently whichever the
    # default happened to be.
    if register_only:
        argv.append("--register-only")
    run = subprocess.run(argv, capture_output=True, text=True,
                         cwd=str(REPO), timeout=TIMEOUT)
    if run.returncode != 0:
        return {"error": (run.stderr or run.stdout)[-800:]}
    out = json.loads(report.read_text())
    out["_constraints"] = (json.loads(saved.read_text())
                           if saved.is_file() else {})
    return out


def precondition_fields(saved) -> dict:
    """register -> the fields its gate waits on.

    Scanning for the register's own name would ask "does the driver mention
    this register nearby", which is not the question. The gate fires because a
    PRECONDITION was not established, so the scan looks for that field's
    accessor -- the same thing the sweep's triage looks for. The saved
    constraints spell them `ADC_CR.ADEN set`, so the field is the part after
    the dot and before the state word."""
    out = collections.defaultdict(set)
    for entry in (saved or {}).get("registers", []):
        reg = (entry.get("register") or "").lower()
        # Field gates carry their own preconditions, in their own structure.
        # Reading only `preconditions` left every field-only register with
        # nothing for the scan to look for, so its hits came back untriaged
        # rather than guarded or candidate.
        cond_lists = list((entry.get("preconditions") or {}).values())
        cond_lists += [fg.get("preconditions") or []
                       for fg in (entry.get("gated_fields") or {}).values()]
        for conds in cond_lists:
            for c in conds:
                head = c.split()[0] if c.split() else ""
                field = head.rsplit(".", 1)[-1]
                if field:
                    out[reg].add(field.lower())
    return {k: sorted(v) for k, v in out.items()}


def triage(diags: list, fields_by_reg: dict) -> list:
    """guarded vs possible bug, per the project's own static pass."""
    rows = []
    for d in diags:
        m = _CONSTRAINED_RE.search(d.get("message", ""))
        fh = None if m else _field_hit(d)
        if not m and not fh:
            continue
        if m:
            reg = m.group(1).split("::")[-1]
            op = m.group(2)
        else:
            # A field gate rides the writer accessor, which serves write and
            # modify alike, so the operation is always a write.
            reg, _field = fh
            op = "write"
        for sp in d.get("spans", []):
            if not sp.get("is_primary"):
                continue
            path = WS / sp["file_name"]
            if not path.is_file():
                continue
            key = reg[:-2].lower() if reg.lower().endswith("rs") else reg.lower()
            fields = fields_by_reg.get(key)
            if not fields:
                # No precondition field recorded: the hit is real but the
                # static pass has nothing to look for, so it is neither a
                # guard nor a bug.
                rows.append({"file": sp["file_name"], "line": sp["line_start"],
                             "register": reg, "operation": op,
                             "verdict": "untriaged"})
                continue
            start, snippet = corroboration.enclosing_function(
                str(path), sp["line_start"])
            det = corroboration.deterministic_scan(
                snippet, sp["line_start"] - start, fields)
            rows.append({"file": sp["file_name"], "line": sp["line_start"],
                         "register": reg, "operation": op,
                         "fields": fields, "verdict": det["verdict"]})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--register-only", action="store_true",
                    help="BASELINE MODE: whole-register gating only, matching "
                         "stm_sweep --register-only. Results go to "
                         "out/register_only/ so the two modes never share a "
                         "path.")
    args = ap.parse_args()

    results = []
    for rm, pac, device, hal, features, target in PAIRINGS:
        if args.only and rm not in args.only:
            continue
        print(f"=== {rm} -> {pac}/{device} vs {hal} ===", flush=True)
        get_pac.provision(force=True, crate=pac, version="0.16.0")

        base = check(hal, features, target, pac)
        if base:
            codes = collections.Counter(
                (e.get("code") or {}).get("code", "?") for e in base)
            print(f"  baseline FAILS ({len(base)} errors {dict(codes)}) "
                  f"-- skipped, nothing measured here", flush=True)
            results.append({"rm": rm, "hal": hal, "baseline": "FAIL",
                            "baseline_errors": len(base)})
            continue
        print("  baseline PASS", flush=True)

        rep = inject(rm, pac, device, args.register_only)
        if "error" in rep:
            print(f"  injection FAILED: {rep['error'][:200]}", flush=True)
            results.append({"rm": rm, "hal": hal, "inject": "FAILED"})
            get_pac.provision(force=True, crate=pac, version="0.16.0")
            continue

        diags = check(hal, features, target, pac)
        rows = triage(diags, precondition_fields(rep.get("_constraints")))
        other = len(diags) - len(rows)
        v = collections.Counter(r["verdict"] for r in rows)
        files = collections.Counter(r["file"].split("/")[-1] for r in rows)
        print(f"  registers gated: {rep.get('registers_planned')}  "
              f"gate fired: {len(rows)}  "
              f"guarded: {v.get('corroborated', 0)}  "
              f"possible bug: {v.get('unchecked', 0)}  "
              f"untriaged: {v.get('untriaged', 0)}  "
              f"collateral: {other}", flush=True)
        print(f"    files: {dict(files.most_common())}", flush=True)
        results.append({
            "rm": rm, "pac": pac, "device": device, "hal": hal,
            "features": features, "baseline": "PASS",
            "registers_gated": rep.get("registers_planned"),
            "gate_fired": len(rows),
            "guarded": v.get("corroborated", 0),
            "possible_bug": v.get("unchecked", 0),
            "untriaged": v.get("untriaged", 0),
            "collateral": other,
            "files": dict(files), "hits": rows})
        get_pac.provision(force=True, crate=pac, version="0.16.0")

    for rm, why in UNPAIRED.items():
        results.append({"rm": rm, "baseline": "—", "unpaired_reason": why})
        print(f"=== {rm}: unpaired -- {why}")

    p = ((OUT / "register_only") if args.register_only else OUT) / \
        "measure_ported.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(results, indent=1))
    print(f"\nreport: {p}")


if __name__ == "__main__":
    main()
