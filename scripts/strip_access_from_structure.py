#!/usr/bin/env python3
"""Remove the merged `access` rows from consolidated structure-review CSVs.

Access is kept as a SEPARATE {rm}_access_review.csv for the STM runs that already
happened (it stays part of the main pipeline for future runs). This drops every
`key == access` row from the consolidated {rm}_structure_review.csv, leaving the
non-access rows (and their reviewer tp_fp/correct_value labels) in their existing
canonical order. Idempotent; stdlib only.

  python scripts/strip_access_from_structure.py --dry-run
  python scripts/strip_access_from_structure.py                 # all
  python scripts/strip_access_from_structure.py --manufacturer stm
"""
from __future__ import annotations

import argparse
import csv
import glob
import os

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def strip_file(path: str, dry_run: bool) -> int:
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        fields = list(rd.fieldnames or [])
        rows = list(rd)
    kept = [r for r in rows if r.get("key") != "access"]
    dropped = len(rows) - len(kept)
    if dropped and not dry_run:
        tmp = path + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in kept:
                w.writerow({k: r.get(k, "") for k in fields})
        os.replace(tmp, path)
    return dropped


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manufacturer", default="*", help="limit to a vendor dir (default: all)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # consolidated files sit at the run root: evaluation/{mfr}/{rm}/{run}/{rm}_structure_review.csv
    pattern = os.path.join(_REPO, "evaluation", args.manufacturer, "*", "*", "*_structure_review.csv")
    total = 0
    for path in sorted(glob.glob(pattern)):
        d = strip_file(path, args.dry_run)
        if d:
            total += d
            print(f"  {os.path.relpath(path, _REPO):55} -{d} access rows")
    print(f"\n{'would drop' if args.dry_run else 'dropped'} {total} access rows from structure reviews")


if __name__ == "__main__":
    main()
