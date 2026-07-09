#!/usr/bin/env python3
"""Quickstart: resume the rm0041 verified-datasheet annotation, breadth-first.

Runs annotate.py on rm0041 with --spread 3000 so a partial session touches
EVERY peripheral (one whole register per peripheral per cycle) instead of only
finishing the first few. Equivalent to:

    python3 verified_datasheet/annotate.py \
        --svd devices/stm/rm0041/svd/stm32f100.svd \
        --pdf devices/stm/rm0041/rm0041.pdf \
        --out verified_datasheet/stm/rm0041_stm32f100.csv \
        --spread 3000

Just run:

    source .venv/bin/activate
    python3 verified_datasheet/quickstart.py

Note: the SVD and PDF are device assets that may not be checked into every
branch (they can be migrated off git). Fetch them into devices/stm/rm0041/
before running, or the worklist build will error.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import annotate  # noqa: E402  (path set above)

SVD = os.path.join(ROOT, "devices/nxp/ke04/svd/MKE04Z4.xml")
PDF = os.path.join(ROOT, "devices/nxp/ke04/KE04.pdf")
OUT = os.path.join(HERE, "nxp/ke04_mke04z4.csv")
SPREAD = "3000"

if __name__ == "__main__":
    for label, path in (("SVD", SVD), ("PDF", PDF)):
        if not os.path.exists(path):
            print(f"  (missing {label}: {path} — fetch device assets first)")

    sys.argv = [
        "annotate.py",
        "--svd", SVD,
        "--pdf", PDF,
        "--out", OUT,
        "--spread", SPREAD,
    ]
    annotate.main()
