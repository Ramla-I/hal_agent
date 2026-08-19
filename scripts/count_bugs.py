#!/usr/bin/env python3
"""Count distinct bugs from bug_tracker.csv (the tracker over-counts on purpose).

Each row is one (fact x svd-value variant) — the right grain for dedup, but the same
field+attribute wrong with different original values across SVD families is ONE bug.
This collapses rows to distinct (RM, location, key).

EXCLUDED from the count by default: rows with NO PR link and Status=Patched — those
were already patched upstream before we caught them, so they aren't our discoveries.
Pass --include-upstream to count them too.

  python scripts/count_bugs.py [bug_reports/bug_tracker.csv] [--by rm|pr|status]
                               [--family] [--include-upstream]
"""
import argparse, csv, collections, os, re


def parse_desc(desc: str):
    parts = (desc or "").split(":")
    loc = parts[0].strip().lower() if parts else ""
    key = parts[1].strip().lower().replace(" ", "_") if len(parts) > 1 else ""
    return loc, key


def family(loc: str) -> str:
    return "_".join(re.sub(r"\d+[a-z]?$", "", t) or t for t in loc.split("_"))


def already_upstream(r: dict) -> bool:
    """No PR link + Patched = fixed upstream before we submitted (not our discovery)."""
    return not (r.get("PR") or "").strip() and (r.get("Status") or "").strip().lower() == "patched"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tracker", nargs="?",
                    default=os.path.join(os.path.dirname(__file__), "..", "bug_reports", "bug_tracker.csv"))
    ap.add_argument("--by", choices=["rm", "pr", "status"])
    ap.add_argument("--family", action="store_true")
    ap.add_argument("--include-upstream", action="store_true",
                    help="also count the already-patched-upstream (no-PR + Patched) rows")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.tracker, newline="", encoding="utf-8")))
    upstream = [r for r in rows if already_upstream(r)]
    ours = rows if args.include_upstream else [r for r in rows if not already_upstream(r)]

    bugs, fams, breakdown = set(), set(), collections.defaultdict(set)
    for r in ours:
        loc, key = parse_desc(r.get("Bug Description", ""))
        bug = (r.get("RM", "").strip(), loc, key)
        bugs.add(bug); fams.add((r.get("RM", "").strip(), family(loc), key))
        if args.by:
            k = {"rm": r.get("RM", ""), "pr": r.get("PR", ""), "status": r.get("Status", "")}[args.by].strip()
            breakdown[k].add(bug)

    print(f"  tracker rows total:                 {len(rows)}")
    print(f"  excluded (already patched upstream):{len(upstream):>4}   (no PR + Patched)"
          if not args.include_upstream else "")
    print(f"  counted rows (facts x svd-variant): {len(ours)}")
    print(f"  distinct bugs (RM, location, key):  {len(bugs)}")
    if args.family:
        print(f"  ~root-cause families (heuristic):   {len(fams)}")
    if args.by:
        print(f"\n  distinct bugs by {args.by}:")
        for k, s in sorted(breakdown.items(), key=lambda kv: -len(kv[1])):
            print(f"    {k or '(none)':<45} {len(s)}")


if __name__ == "__main__":
    main()
