#!/usr/bin/env python3
"""Count distinct bugs from bug_tracker.csv + the reviewed reports in bug_reports/checked/.

Every CSV row (tracker and each checked ``{rm}_bug_report.csv``, same columns) is one
(fact x svd-value variant) — the right grain for dedup, but the same field+attribute
wrong with different original values across SVD families is ONE bug. This unions all
rows and collapses them to distinct (RM, location, key); a bug that appears in BOTH the
tracker and a checked report is counted once.

EXCLUDED from the count by default: rows with NO PR link and Status=Patched — those were
already patched upstream before we caught them, so they aren't our discoveries. Pass
--include-upstream to count them too.

  python scripts/count_bugs.py [--by rm|pr|status] [--family] [--include-upstream]
  python scripts/count_bugs.py --no-checked            # tracker only (old behaviour)
  python scripts/count_bugs.py <tracker.csv> --checked-dir <dir>
"""
import argparse, csv, collections, glob, os, re

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def _read(path: str) -> list:
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return [r for r in csv.DictReader(f) if (r.get("Bug Description") or "").strip()]
    except FileNotFoundError:
        return []


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tracker", nargs="?",
                    default=os.path.join(_REPO, "bug_reports", "bug_tracker.csv"))
    ap.add_argument("--checked-dir", default=os.path.join(_REPO, "bug_reports", "checked"),
                    help="folder of reviewed {rm}_bug_report.csv files (default bug_reports/checked)")
    ap.add_argument("--no-checked", action="store_true", help="count the tracker only")
    ap.add_argument("--by", choices=["rm", "pr", "status"])
    ap.add_argument("--family", action="store_true")
    ap.add_argument("--include-upstream", action="store_true",
                    help="also count the already-patched-upstream (no-PR + Patched) rows")
    args = ap.parse_args()

    sources = [("tracker", args.tracker)]
    if not args.no_checked:
        sources += [("checked", p) for p in sorted(glob.glob(os.path.join(args.checked_dir, "*.csv")))]

    rows, per_source = [], collections.Counter()
    for tag, path in sources:
        rs = _read(path)
        per_source[tag] += len(rs)
        rows += rs

    upstream = [r for r in rows if already_upstream(r)]
    ours = rows if args.include_upstream else [r for r in rows if not already_upstream(r)]

    bugs, fams = set(), set()
    breakdown, by_key = collections.defaultdict(set), collections.defaultdict(set)
    for r in ours:
        loc, key = parse_desc(r.get("Bug Description", ""))
        bug = (r.get("RM", "").strip(), loc, key)
        bugs.add(bug); fams.add((r.get("RM", "").strip(), family(loc), key))
        by_key[key or "(none)"].add(bug)
        if args.by:
            k = {"rm": r.get("RM", ""), "pr": r.get("PR", ""), "status": r.get("Status", "")}[args.by].strip()
            breakdown[k].add(bug)

    n_checked_files = sum(1 for tag, _ in sources if tag == "checked")

    def line(label, n, extra=""):
        print(f"  {label:<37}{n:>5}{extra}")

    line("tracker rows:", per_source["tracker"])
    if not args.no_checked:
        line(f"checked rows ({n_checked_files} files):", per_source["checked"])
    line("total rows:", len(rows))
    if not args.include_upstream:
        line("excluded (already patched upstream):", len(upstream), "   (no PR + Patched)")
    line("counted rows (facts x svd-variant):", len(ours))
    line("distinct bugs (RM, location, key):", len(bugs))
    if args.family:
        line("~root-cause families (heuristic):", len(fams))

    print("\n  distinct bugs by key:")
    for k, s in sorted(by_key.items(), key=lambda kv: -len(kv[1])):
        print(f"    {k:<18} {len(s)}")

    if args.by:
        print(f"\n  distinct bugs by {args.by}:")
        for k, s in sorted(breakdown.items(), key=lambda kv: -len(kv[1])):
            print(f"    {k or '(none)':<45} {len(s)}")


if __name__ == "__main__":
    main()
