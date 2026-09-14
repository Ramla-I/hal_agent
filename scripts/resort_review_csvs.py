"""Re-sort existing review CSVs in place by their canonical grouping.

Re-sorted by the writer's own helper (single source of truth — no ordering
logic is duplicated here): bug review ({rm}_structure_review.csv and
{svd}/{svd}_structure_review.csv) -> peripheral -> register -> field -> key.

Constraints review used to be handled here too, when it was a CSV. It is a
JSONL artifact now (core/constraints_review.py), written in a canonical order
and never re-sorted in place, so that half is gone along with the CSV writer.

Pure reorder — the header and every cell (incl. reviewer tp_fp / correct_value)
are preserved — so it is safe to re-run and idempotent. The writers now emit this
order natively; this backfills files produced before that change.

Run: scripts/docker_run.sh run scripts/resort_review_csvs.py [eval_root]
"""
import glob
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from applications.bug_finding.report import resort_review_csv

root = sys.argv[1] if len(sys.argv) > 1 else "evaluation"

paths = set()
paths.update(glob.glob(os.path.join(root, "stm", "*", "*", "*_review.csv")))        # run-root files
paths.update(glob.glob(os.path.join(root, "stm", "*", "*", "*", "*_review.csv")))   # per-SVD files

n_bug = 0
for p in sorted(paths):
    if "constraints" in os.path.basename(p):
        continue          # JSONL now; no CSV to re-sort
    resort_review_csv(p)
    n_bug += 1
print(f"re-sorted {n_bug} bug review CSV(s)")
