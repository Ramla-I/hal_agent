#!/usr/bin/env python3
"""Show just the reviewer-TP rows of a structure review CSV.

  python scripts/show_tp.py evaluation/stm/rm0041/1/rm0041_structure_review.csv
  python scripts/show_tp.py <file> --key reset_value      # filter to one key
  python scripts/show_tp.py <file> --csv                  # raw CSV of the TP rows
"""
from __future__ import annotations

import argparse
import csv
import sys


def _loc(r: dict) -> str:
    s = f"{r.get('peripheral','')}.{r.get('register','')}"
    return s + (f".{r['field']}" if (r.get("field") or "").strip() else "")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", help="path to a {rm}_structure_review.csv")
    ap.add_argument("--key", help="only rows with this key (e.g. reset_value, access)")
    ap.add_argument("--csv", action="store_true", help="emit the TP rows as raw CSV")
    args = ap.parse_args()

    with open(args.file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        tp = [r for r in reader if (r.get("tp_fp") or "").strip().upper() == "TP"
              and (not args.key or (r.get("key") or "").strip() == args.key)]

    if args.csv:
        w = csv.DictWriter(sys.stdout, fieldnames=fields)
        w.writeheader()
        w.writerows(tp)
        return

    rm = tp[0].get("RM") if tp else args.file
    print(f"\n=== {rm} — {len(tp)} TP row(s){' [' + args.key + ']' if args.key else ''} ===")
    if not tp:
        return
    has_notes = any((r.get("Notes") or "").strip() for r in tp)
    print(f"  {'location':<34}{'key':<15}{'svd -> generator':<28}{'correct':<12}"
          f"{'Validator Verdict':<18}" + ("Notes" if has_notes else ""))
    print("  " + "-" * (110 if has_notes else 92))
    for r in tp:
        sv, gv = (r.get("svd_value") or "").strip(), (r.get("generator_value") or "").strip()
        print(f"  {_loc(r):<34}{(r.get('key') or ''):<15}"
              f"{(sv + ' -> ' + gv):<28}{(r.get('correct_value') or '').strip():<12}"
              f"{(r.get('validator_verdict') or '').strip():<18}"
              + ((r.get("Notes") or "").strip() if has_notes else "").rstrip())
    # small tally by key
    from collections import Counter
    by = Counter((r.get("key") or "").strip() for r in tp)
    print("\n  by key: " + ", ".join(f"{k}={n}" for k, n in by.most_common()))


if __name__ == "__main__":
    main()
