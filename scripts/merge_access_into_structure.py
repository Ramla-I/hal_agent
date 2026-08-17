#!/usr/bin/env python3
"""Merge the one-time {rm}_access_review.csv rows into {rm}_structure_review.csv.

Access is a first-class structure-review key now, so this folds the separately
generated access rows into the consolidated structure review: append the access
rows that aren't already present (dedup by row identity), then re-sort the whole
file into the canonical peripheral -> register -> field -> key order (the same
natural sort the pipeline writes), so the access rows land in their correct
positions rather than at the end.

Identity + sort mirror applications/bug_finding/report.py exactly, so the result
matches what a fresh pipeline run would produce (labels preserved on later regen).
Idempotent: re-running adds nothing (identities already present). Stdlib only.

  python scripts/merge_access_into_structure.py            # apply to all
  python scripts/merge_access_into_structure.py --dry-run  # preview counts
  python scripts/merge_access_into_structure.py --devices rm0041
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import re

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- identity + natural sort, verbatim from applications/bug_finding/report.py ---
_BUG_KEY_FIELDS = ("peripheral", "register", "field", "key", "svd_value", "generator_value")


def _bug_key(row: dict) -> tuple:
    return tuple((row.get(c) or "") for c in _BUG_KEY_FIELDS)


def _nat_chunks(s: str) -> tuple:
    return tuple((1, int(t)) if t.isdigit() else (0, t.lower())
                 for t in re.split(r"(\d+)", s or "") if t)


def _sort_key(row: dict) -> tuple:
    p, r, f, k, sv, gv = _bug_key(row)
    return (_nat_chunks(p), _nat_chunks(r), _nat_chunks(f), _nat_chunks(k), sv or "", gv or "")


def _read(path: str) -> tuple[list, list]:
    with open(path, newline="", encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames or []), list(rd)


def merge_one(structure_csv: str, access_csv: str, dry_run: bool) -> dict:
    fields, srows = _read(structure_csv)
    _, arows = _read(access_csv)
    have = {_bug_key(r) for r in srows}
    new = [r for r in arows if _bug_key(r) not in have]
    if not new:
        return {"added": 0, "total": len(srows)}
    merged = srows + new
    merged.sort(key=_sort_key)
    if not dry_run:
        tmp = structure_csv + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            for r in merged:
                w.writerow({k: r.get(k, "") for k in fields})
        os.replace(tmp, structure_csv)
    return {"added": len(new), "total": len(merged)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devices", nargs="*", help="limit to these RMs (default: all)")
    ap.add_argument("--dry-run", action="store_true", help="print counts, write nothing")
    args = ap.parse_args()
    want = {d.lower() for d in args.devices} if args.devices else None

    total_added = 0
    for access_csv in sorted(glob.glob(os.path.join(_REPO, "evaluation", "*", "*", "*", "*_access_review.csv"))):
        rm = os.path.basename(access_csv)[:-len("_access_review.csv")]
        if want and rm.lower() not in want:
            continue
        structure_csv = access_csv.replace("_access_review.csv", "_structure_review.csv")
        if not os.path.isfile(structure_csv):
            print(f"  {rm:10} SKIP: no structure review")
            continue
        res = merge_one(structure_csv, access_csv, args.dry_run)
        total_added += res["added"]
        print(f"  {rm:10} +{res['added']:4} access rows -> {res['total']} total"
              + ("  (dry-run)" if args.dry_run else ""))
    print(f"\n{'would add' if args.dry_run else 'added'} {total_added} access rows across the structure reviews")


if __name__ == "__main__":
    main()
