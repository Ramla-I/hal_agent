#!/usr/bin/env python3
"""Read out loud the constraints a device's crate actually gates.

`constraints/<rm>_<device>.json` is the durable record of what a crate gates,
but it is JSON built for machines: one nested object per register, the same
datasheet sentence repeated once per operation. This prints it the way a person
reads it -- one block per register, the rule, the sentence it came from, and
how firmly that sentence anchored.

Usage:
    python applications/pac_codegen/show_injected_constraints.py rm0008
    python applications/pac_codegen/show_injected_constraints.py rm0008 --quotes
    python applications/pac_codegen/show_injected_constraints.py --all
"""
import argparse
import json
import textwrap
from pathlib import Path

DIR = Path(__file__).resolve().parent / "constraints"


def files(pattern: str):
    return sorted(DIR.glob(f"{pattern}*.json"))


def show(path: Path, quotes: bool) -> tuple[int, int]:
    d = json.loads(path.read_text())
    regs = d["registers"]
    mode = "field-level" if d.get("field_level_gating") else "whole-register"
    checked = "attribution-checked" if d.get("attribution_checked_against") \
        else "NOT attribution-checked"
    print(f"\n{path.stem}   {d['device']}   {mode}, {checked}")
    print("=" * 74)
    ops = 0
    for r in regs:
        head = f"{r['peripheral']}/{r['register']}"
        gated = ", ".join(r["gated_operations"]) or "-"
        print(f"\n  {head:<22} gates: {gated}"
              + (f"   [{','.join(r.get('constraint_ids') or [])}]"
                 if r.get("constraint_ids") else ""))
        ops += len(r["gated_operations"])
        # One line per distinct rule; the file repeats it per operation.
        seen = set()
        for op, pres in (r.get("preconditions") or {}).items():
            for p in pres:
                if p in seen:
                    continue
                seen.add(p)
                print(f"      requires  {p}")
        for field, g in (r.get("gated_fields") or {}).items():
            ops += 1
            print(f"      field {field}: {', '.join(g['preconditions'])}")
        if quotes:
            said = set()
            for texts in (r.get("datasheet_text") or {}).values():
                for t in texts:
                    if t not in said:
                        said.add(t)
                        for line in textwrap.wrap(t, 64):
                            print(f"        > {line}")
            tiers = {t for ts in (r.get("quote_verification") or {}).values()
                     for t in ts}
            if tiers:
                print(f"        anchored: {', '.join(sorted(tiers))}")
    return len(regs), ops


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("rm", nargs="?", default=None,
                    help="manual, e.g. rm0008 (prefix match)")
    ap.add_argument("--all", action="store_true", help="every manual")
    ap.add_argument("--quotes", action="store_true",
                    help="also print the datasheet sentence and anchor tier")
    ap.add_argument("--ids", action="store_true",
                    help="print only the review-ledger ids, one per line, so a "
                         "reviewer can pull exactly these rows out of "
                         "<rm>_constraints_review.jsonl and mark tp_fp on them")
    a = ap.parse_args()
    if not a.rm and not a.all:
        ap.error("name a manual, or pass --all")
    paths = files("" if a.all else a.rm)
    if not paths:
        ap.error(f"no constraints file matching {a.rm!r} in {DIR}")
    if a.ids:
        for path in paths:
            d = json.loads(path.read_text())
            for r in d["registers"]:
                for cid in r.get("constraint_ids", []):
                    print(cid)
        return
    tr = to = 0
    for p in paths:
        r, o = show(p, a.quotes)
        tr += r
        to += o
    if len(paths) > 1:
        print(f"\n{'=' * 74}\n{len(paths)} devices, {tr} registers, {to} gates")


if __name__ == "__main__":
    main()
