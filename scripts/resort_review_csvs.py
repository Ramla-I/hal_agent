"""Re-sort existing review CSVs in place by peripheral → register → field → key.

The writers in applications/bug_finding/report.py now emit rows in this grouped,
natural order; this backfills the files produced before that change. It is a pure
reorder — the header and every cell (including reviewer-filled tp_fp /
correct_value) are preserved — so it is safe to re-run and idempotent.

Covers both the consolidated per-RM file ({rm}_review.csv) and the per-SVD files
({svd}/{svd}_review.csv). The constraints review files ({rm}_constraints_review)
have a different schema and are intentionally left untouched.

Run: scripts/docker_run.sh run scripts/resort_review_csvs.py [eval_root]
"""
import glob
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from applications.bug_finding.report import resort_review_csv

root = sys.argv[1] if len(sys.argv) > 1 else "evaluation"

paths = set()
paths.update(glob.glob(os.path.join(root, "stm", "*", "*", "*_review.csv")))        # consolidated
paths.update(glob.glob(os.path.join(root, "stm", "*", "*", "*", "*_review.csv")))   # per-SVD
paths = sorted(p for p in paths if "constraints" not in os.path.basename(p))

n = 0
for p in paths:
    rows = resort_review_csv(p)
    n += 1
    print(f"  sorted {rows:5d} rows  {p}")
print(f"re-sorted {n} review CSV(s)")
