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
# Only BKP qualifies: the SVD baseAddress absorbs a +4, so both values encode the
# same absolute address. Two other uniform-shift peripherals were investigated and
# are NOT tagged here:
#   rm0090 HASH  — genuine TP: the f417 SVD carries the F43x-only 0x310 digest bank
#                  (datasheet: HR0-4 @0x0C-0x1C for F415/417, 0x310-0x32C for F43x).
#   rm0316 ADC3  — genuine FP already labelled FP: the F303 SVD's JDR @0x80 is
#                  correct (0x3C is the old-ADC layout / SQR4 on F303), so the FP
#                  label already says "not a bug" — no note needed.
ANNOTATIONS: dict[tuple[str, str], str] = {
    ("rm0008", "bkp"): "GEN_AND_SVD_CORRECT",
    ("rm0041", "bkp"): "GEN_AND_SVD_CORRECT",
}

# Tags this script owns; it may overwrite/clear these but never a hand-written note.
# SVD_CORRECT_GEN_WRONG is retained so re-running clears any stale copies we wrote.
_OUR_TAGS = {"GEN_AND_SVD_CORRECT", "SVD_CORRECT_GEN_WRONG"}


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
        current = (r.get("Notes") or "").strip()
        note = _note_for(r) or ""
        # authoritative over our own tags (so removing a mapping clears stale tags);
        # never clobber a hand-written note we don't own.
        if current and current not in _OUR_TAGS:
            continue
        if note != current:
            r["Notes"] = note
            if note:
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
