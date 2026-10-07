#!/usr/bin/env python3
"""Standalone spot audit of extracted subfields.

An INDEPENDENT statistical check on subfield extraction quality: draw a
fixed-seed random sample of a run's named (non-reserved) extracted bit fields,
hand-adjudicate each against the datasheet, and bound the overall error rate.

Deliberately depends on NOTHING but the run's own output + a seed. It does not
read the other audits (score_subfields / audit_full / constants_map) — those
are what it cross-checks, not what it trusts, and relying on their coverage
claims would couple this estimate to their correctness. Sampling the WHOLE
named population (not an "unreferenced" subset) keeps the estimate unbiased and
valid even if every other audit were wrong.

Usage:
  python3 spot_audit.py r006                 # draw the sample to hand-check
  python3 spot_audit.py r006 --errors 1      # after adjudication: 95%% bound
"""
import argparse
import glob
import json
import os
import random
import re
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))


def is_reserved(name):
    return re.sub(r"[^a-z0-9]", "", str(name).lower()).startswith(("reserv", "rsv"))


def clopper_pearson_upper(k, n, conf=0.95):
    """One-sided (1-conf) upper bound on the error rate given k errors in n."""
    def pcum(p):
        return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k + 1))
    lo, hi = 0.0, 1.0
    for _ in range(200):
        m = (lo + hi) / 2
        if pcum(m) > 1 - conf:
            lo = m
        else:
            hi = m
    return hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=82599)
    ap.add_argument("--errors", type=int, default=None,
                    help="errors found by hand in the sample -> prints the exact "
                    "95%% upper bound on the subfield error rate")
    args = ap.parse_args()

    # population: every named (non-reserved) extracted bit field in the run
    named = []
    for p in sorted(glob.glob(os.path.join(HERE, "register_info", args.run, "*.json"))):
        reg = os.path.basename(p)[:-5]
        try:
            d = json.load(open(p))
        except Exception:
            continue
        for sf in d.get("subfields") or []:
            bn = sf.get("bit_number") or {}
            if bn.get("start_bit") is None or is_reserved(sf.get("name")):
                continue
            named.append((reg, sf["name"], bn["start_bit"], bn["end_bit"]))

    rng = random.Random(args.seed)
    sample = sorted(rng.sample(named, min(args.n, len(named))))
    out = [{"register": r, "field": f, "extracted_bits": f"{hi}:{lo}"}
           for r, f, lo, hi in sample]
    rec = {"run": args.run, "seed": args.seed, "population_named": len(named),
           "n": len(sample), "sample": out}
    if args.errors is not None:
        rec["errors"] = args.errors
        rec["point_estimate"] = args.errors / len(sample)
        rec["ci95_upper"] = clopper_pearson_upper(args.errors, len(sample))

    json.dump(rec, open(os.path.join(HERE, "..", "reports", "spot_audit_sample.json"), "w"),
              indent=2)

    print(f"population: {len(named)} named subfields; sample n={len(sample)} "
          f"(seed {args.seed}, run {args.run})")
    for row in out:
        print(f"  {row['register']:10s} {row['field']:34s} {row['extracted_bits']}")
    if args.errors is None:
        print("hand-check each against its datasheet register table, then rerun "
              "with --errors K.")
        print(f"(0 errors -> 95%% upper bound ~ 3/n = {3 / len(sample):.1%})")
    else:
        print(f"{args.errors} error(s) in {len(sample)}: point "
              f"{args.errors / len(sample):.1%}, 95%% upper bound "
              f"{clopper_pearson_upper(args.errors, len(sample)):.1%}")


if __name__ == "__main__":
    main()
