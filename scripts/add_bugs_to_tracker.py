#!/usr/bin/env python3
"""Turn a structure-review file's reviewer-TP rows into bug_tracker.csv rows.

Keeps only rows you marked `tp_fp == TP` and writes them, in the tracker's column
layout (SVD File, Crate, RM, Bug Description, PR, Status), to
`bug_reports/{rm}_bug_report.csv` (fresh file, NOT appended). Copy the rows into the
main `bug_reports/bug_tracker.csv` yourself.

One review row -> one tracker row (the review is already consolidated: one row per
bug with its SVDs `;`-joined). The description is
  {PERIPHERAL}_{REGISTER}[_{FIELD}]: {key}: svd = {svd_value}, agent = {generator_value}[, RM = {correct_value}]
matching the existing tracker; `, RM = …` is added only when you set a correct_value
(a human override of the generator's value).

  python scripts/add_bugs_to_tracker.py evaluation/stm/rm0041/1/rm0041_structure_review.csv
  python scripts/add_bugs_to_tracker.py <file> --pr https://github.com/stm32-rs/stm32-rs/pull/1282 --status Patched
"""
from __future__ import annotations

import argparse
import csv
import os

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HEADER = ["SVD File", "Crate", "RM", "Bug Description", "PR", "Status"]


def _description(r: dict) -> str:
    per, reg, fld = r.get("peripheral", ""), r.get("register", ""), (r.get("field") or "").strip()
    loc = f"{per.upper()}_{reg.upper()}" + (f"_{fld.upper()}" if fld else "")
    key = (r.get("key") or "").replace("_", " ")
    svd, gen = (r.get("svd_value") or "").strip(), (r.get("generator_value") or "").strip()
    correct = (r.get("correct_value") or "").strip()
    desc = f"{loc}: {key}: svd = {svd}, agent = {gen}"
    if correct:
        desc += f", RM = {correct}"
    return desc


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("review_file", help="path to a {rm}_structure_review.csv")
    ap.add_argument("--crate", default="stm32-rs")
    ap.add_argument("--pr", default="", help="PR URL to stamp on every row")
    ap.add_argument("--status", default="", help="Status to stamp (e.g. Patched, Merged)")
    ap.add_argument("--output", help="output path (default bug_reports/{rm}_bug_report.csv)")
    args = ap.parse_args()

    with open(args.review_file, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("tp_fp") or "").strip().upper() == "TP"]

    rm = (rows[0].get("RM") if rows else "") or \
        os.path.basename(args.review_file).replace("_structure_review.csv", "")
    out = args.output or os.path.join(_REPO, "bug_reports", f"{rm}_bug_report.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({
                "SVD File": (r.get("svd_files") or "").replace(";", ", "),
                "Crate": args.crate,
                "RM": r.get("RM") or rm,
                "Bug Description": _description(r),
                "PR": args.pr,
                "Status": args.status,
            })
    print(f"{rm}: {len(rows)} TP row(s) -> {os.path.relpath(out, _REPO)}"
          + ("  (no PR/Status set — pass --pr/--status or fill after pasting)"
             if not (args.pr or args.status) else ""))


if __name__ == "__main__":
    main()
