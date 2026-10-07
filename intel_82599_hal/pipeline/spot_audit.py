#!/usr/bin/env python3
"""Spot audit of the subfields no referee covers.

Builds the audit frame (named extracted subfields minus the externally scored
set: Linux-referee joins + driver-consumed fields), draws a fixed-seed random
sample, and emits a checklist for hand adjudication against the datasheet.
With --bound N_ERRORS it prints the rule-of-three / binomial 95% upper bound.

Usage: python3 spot_audit.py r006 [--n 30] [--seed 82599]
"""
import argparse
import glob
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from s4_emit_hal import find_field  # noqa: E402


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=82599)
    args = ap.parse_args()

    specs, named = {}, []
    for p in sorted(glob.glob(os.path.join(HERE, "register_info", args.run, "*.json"))):
        r = os.path.basename(p)[:-5]
        specs[r] = json.load(open(p))
        for sf in specs[r].get("subfields") or []:
            bn = sf.get("bit_number") or {}
            if bn.get("start_bit") is None:
                continue
            if norm(sf["name"]).startswith(("reserv", "rsv")):
                continue
            named.append((r, sf["name"], bn["start_bit"], bn["end_bit"]))

    scored = set()
    sc = json.load(open(os.path.join(HERE, "..", "reports", "subfield_scores.json")))
    for x in sc["scored_fields"]:
        r, f = x.split(".", 1)
        scored.add((r, norm(f)))
    cm = json.load(open(os.path.join(HERE, "config", "constants_map.json")))["constants"]
    consumed = [(c["register"], [c.get("field")] + c.get("alt", []))
                for c in cm if c["kind"] != "policy"]
    consumed += [(r, [f]) for r, f in (
        ("RXCTRL", "RXEN"), ("TXDCTL", "ENABLE"), ("EEC", "EE_GNT"), ("GPIE", "EIAME"),
        ("EIAC", "Reserved"), ("DMATXCTL", "VT"), ("HLREG0", "RXCRCSTRP"),
        ("RDRXCTL", "CRCStrip"), ("EEC", "EE_SK"), ("EEC", "EE_CS"), ("EEC", "EE_DI"),
        ("EEC", "EE_REQ"), ("EIAM", "Auto Mask"))]
    for reg, names in consumed:
        sf, matched = find_field(specs.get(reg.upper()), names)
        if matched:
            scored.add((reg.upper(), norm(matched)))

    frame = [x for x in named if (x[0], norm(x[1])) not in scored]
    print(f"frame: {len(frame)} unreferenced named fields "
          f"(of {len(named)} named; scored set {len(scored)})")
    rng = random.Random(args.seed)
    sample = sorted(rng.sample(frame, min(args.n, len(frame))))
    out = [{"register": r, "field": f, "extracted_bits": f"{hi}:{lo}"}
           for r, f, lo, hi in sample]
    json.dump({"run": args.run, "seed": args.seed, "frame_size": len(frame),
               "sample": out}, open(os.path.join(HERE, "..", "reports", "spot_audit_sample.json"), "w"),
              indent=2)
    for row in out:
        print(f"  {row['register']:10s} {row['field']:34s} {row['extracted_bits']}")
    print("rule of three: 0 errors in n -> 95% upper bound ~ 3/n "
          f"= {3 / len(sample):.1%} for n={len(sample)}")


if __name__ == "__main__":
    main()
