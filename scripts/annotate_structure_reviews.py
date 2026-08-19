#!/usr/bin/env python3
"""Add a `Notes` column to every structure-review CSV and tag the known
whole-peripheral uniform address-shift false positives (see
scripts/scan_base_shift_fps.py).

Two verified tags (idempotent — re-running only fills empty Notes):
  GEN_AND_SVD_CORRECT   both values encode the same absolute address, the SVD
                        just splits it between baseAddress and offset differently
                        than the datasheet (STM32 BKP: base 0x40006C04 + off 0x0
                        == datasheet base 0x40006C00 + off 0x4).
  SVD_CORRECT_GEN_WRONG the SVD is right; the generator anchored the whole
                        peripheral to the wrong register bank/generation (rm0090
                        HASH digest HR0-4 given the main bank's offsets; rm0316
                        F3 ADC3 JDR given F1-style 0x3C). Not submittable.

Applied to rows with key==address_offset and tp_fp==TP in the listed peripherals.

  python scripts/annotate_structure_reviews.py            # all evaluation/stm reviews
  python scripts/annotate_structure_reviews.py <review.csv> ...
"""
from __future__ import annotations

import csv
import glob
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (rm, peripheral) -> Notes tag, for key==address_offset TP rows.
ANNOTATIONS: dict[tuple[str, str], str] = {
    ("rm0008", "bkp"): "GEN_AND_SVD_CORRECT",
    ("rm0041", "bkp"): "GEN_AND_SVD_CORRECT",
    ("rm0090", "hash"): "SVD_CORRECT_GEN_WRONG",
    ("rm0316", "adc3"): "SVD_CORRECT_GEN_WRONG",
}


def _note_for(row: dict) -> str | None:
    if (row.get("key") or "") != "address_offset":
        return None
    if (row.get("tp_fp") or "").strip().upper() != "TP":
        return None
    key = ((row.get("RM") or "").lower(), (row.get("peripheral") or "").lower())
    return ANNOTATIONS.get(key)


def annotate(review: str) -> int:
    with open(review, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if "Notes" not in fields:
        fields.append("Notes")

    tagged = 0
    for r in rows:
        r.setdefault("Notes", "")
        note = _note_for(r)
        if note and not (r.get("Notes") or "").strip():
            r["Notes"] = note
            tagged += 1

    with open(review, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return tagged


def main() -> None:
    reviews = sys.argv[1:] or sorted(
        glob.glob(os.path.join(_REPO, "evaluation", "stm", "*", "*", "*_structure_review.csv")))
    total = 0
    for rv in reviews:
        n = annotate(rv)
        total += n
        if n:
            print(f"  {os.path.relpath(rv, _REPO)}: {n} row(s) tagged")
    print(f"\nNotes column added to {len(reviews)} review(s); {total} row(s) tagged")


if __name__ == "__main__":
    main()
