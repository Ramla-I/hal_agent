#!/usr/bin/env python3
"""What the generator extracted, and what survived to a judged verdict.

This covers the constraint pipeline UP TO the review files and no further.
Injection is a separate question with a separate denominator, and conflating
the two is easy to do by accident: the cascade figure in the injection repo
counts 16,338 constraints because it is built from injection reports, and a
manual with no chip crate never produces one. Nothing here depends on a chip
crate existing, so RM0475 (STM32MP13x) is present like any other manual.

THREE DENOMINATORS, AND THEY ARE NOT INTERCHANGEABLE

  generated       every `access_constraints_v2` entry in the generator's own
                  per-register output. The extraction denominator.
  reached review  what survived collection -- register and fields resolved
                  against the SVD, grammar checked -- and so got a row in
                  <rm>_constraints_review.jsonl. Roughly a third of generated
                  output never gets this far.
  judged          rows the validator actually returned a verdict on. NOT the
                  same as "reached review": the review files also carry
                  `encoding_error` rows and rows with an empty verdict, and
                  counting those as judgments flatters the validator.

Manuals are discovered from the data directories, and stages from the files
themselves; an unrecognised verdict or enforcement value is reported rather
than silently binned.

Usage:
    python scripts/stm_constraint_generation_statistics.py
    python scripts/stm_constraint_generation_statistics.py --by-rm
    python scripts/stm_constraint_generation_statistics.py --csv out.csv
"""

import argparse
import collections
import csv
import json
import statistics as stats
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AGENT = REPO / "agent_output" / "stm"
EVAL = REPO / "evaluation" / "stm"

# Verdicts that mean the validator actually ruled on the constraint. The others
# are pipeline failures wearing a verdict field, and they belong in their own
# line rather than in the denominator.
JUDGED = {"confirmed", "not_constraint"}


def manuals() -> list:
    """Every manual with generator output, discovered not listed."""
    if not AGENT.is_dir():
        sys.exit(f"no generator output under {AGENT}")
    return sorted(d.name for d in AGENT.iterdir()
                  if d.is_dir() and (d / "1").is_dir())


def generated(rm: str) -> collections.Counter:
    """Raw generator output for one manual, by grammar kind."""
    c = collections.Counter()
    run = AGENT / rm / "1"
    for f in run.iterdir():
        if not f.is_file() or f.name.startswith("."):
            continue
        try:
            d = json.loads(f.read_text())
        except (ValueError, UnicodeDecodeError, OSError):
            continue
        if not isinstance(d, dict):
            continue
        for g in (d.get("access_constraints_v2") or []):
            c[g.get("kind") or "?"] += 1
    return c


def reviewed(rm: str):
    """(rows, verdicts, enforcement, anchor tiers, kinds) for one manual."""
    f = EVAL / rm / "1" / f"{rm}_constraints_review.jsonl"
    v, e, a, k = (collections.Counter() for _ in range(4))
    n = 0
    if not f.is_file():
        return n, v, e, a, k
    for line in f.read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        n += 1
        v[d.get("verdict") or "(blank)"] += 1
        e[d.get("enforcement") or "(blank)"] += 1
        a[d.get("anchor_tier") or "(blank)"] += 1
        k[(d.get("constraint") or {}).get("kind") or "?"] += 1
    return n, v, e, a, k


def describe(name, xs):
    if not xs:
        return
    q = stats.quantiles(xs, n=4) if len(xs) > 3 else [float("nan")] * 3
    print("  %-16s total=%-8s mean=%-7.1f median=%-7.1f sd=%-7.1f "
          "Q1=%-6.0f Q3=%-6.0f min=%-5d max=%d"
          % (name, f"{sum(xs):,}", stats.mean(xs), stats.median(xs),
             stats.stdev(xs) if len(xs) > 1 else 0.0, q[0], q[2],
             min(xs), max(xs)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--by-rm", action="store_true", help="per-manual table")
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    rms = manuals()
    per, kinds_gen, kinds_rev = {}, collections.Counter(), collections.Counter()
    verd, enf, anch = (collections.Counter() for _ in range(3))
    for rm in rms:
        g = generated(rm)
        n, v, e, a, k = reviewed(rm)
        per[rm] = {"generated": sum(g.values()), "reviewed": n,
                   "judged": sum(v[x] for x in JUDGED),
                   "confirmed": v.get("confirmed", 0),
                   "enforce": e.get("enforce", 0)}
        kinds_gen.update(g); kinds_rev.update(k)
        verd.update(v); enf.update(e); anch.update(a)

    gen = [p["generated"] for p in per.values()]
    rev = [p["reviewed"] for p in per.values()]
    jud = [p["judged"] for p in per.values()]
    enfv = [p["enforce"] for p in per.values()]

    print(f"{len(rms)} ST reference manuals\n")
    print("PER MANUAL")
    describe("generated", gen)
    describe("reached review", rev)
    describe("judged", jud)
    describe("enforce", enfv)

    tg, tr = sum(gen), sum(rev)
    print("\nFUNNEL")
    print("  %-34s %7s" % ("generated", f"{tg:,}"))
    print("  %-34s %7s   (%.0f%% of generated)"
          % ("dropped at collection", f"{tg - tr:,}", 100 * (tg - tr) / tg))
    print("  %-34s %7s   (%.0f%% of generated)"
          % ("reached review", f"{tr:,}", 100 * tr / tg))
    for k, n in verd.most_common():
        mark = "  <- judged" if k in JUDGED else ""
        print("    %-32s %7s%s" % (k, f"{n:,}", mark))
    tj = sum(verd[x] for x in JUDGED)
    print("  %-34s %7s   (%.0f%% of reviewed)"
          % ("judged", f"{tj:,}", 100 * tj / tr if tr else 0))
    print("\n  enforcement (all reviewed rows)")
    for k, n in enf.most_common():
        print("    %-32s %7s" % (k, f"{n:,}"))
    print("\n  quote anchor tier")
    for k, n in anch.most_common():
        print("    %-32s %7s" % (k, f"{n:,}"))

    print("\nBY GRAMMAR KIND")
    print("  %-18s %8s %8s %8s" % ("kind", "generated", "reviewed", "kept%"))
    for k, n in kinds_gen.most_common():
        r = kinds_rev.get(k, 0)
        print("  %-18s %8s %8s %7.0f%%"
              % (k, f"{n:,}", f"{r:,}", 100 * r / n if n else 0))

    unknown = set(verd) - JUDGED - {"encoding_error", "(blank)"}
    if unknown:
        print(f"\n!! unrecognised verdicts, counted but not classified: "
              f"{sorted(unknown)}")

    if args.by_rm:
        print("\nPER-MANUAL DETAIL")
        print("  %-8s %10s %10s %8s %9s %8s"
              % ("rm", "generated", "reviewed", "judged", "confirmed", "enforce"))
        for rm in rms:
            p = per[rm]
            print("  %-8s %10d %10d %8d %9d %8d"
                  % (rm, p["generated"], p["reviewed"], p["judged"],
                     p["confirmed"], p["enforce"]))

    if args.csv:
        with open(args.csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["rm", "generated", "reviewed", "judged",
                        "confirmed", "enforce"])
            for rm in rms:
                p = per[rm]
                w.writerow([rm, p["generated"], p["reviewed"], p["judged"],
                            p["confirmed"], p["enforce"]])
        print(f"\ncsv: {args.csv}")


if __name__ == "__main__":
    main()
