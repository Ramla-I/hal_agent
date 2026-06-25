"""Re-sort existing review CSVs in place by their canonical grouping.

Two kinds of review CSV, each re-sorted by *its own writer's* helper (single
source of truth — no ordering logic is duplicated here):
  * bug review         ({rm}_review.csv and {svd}/{svd}_review.csv)
        -> peripheral -> register -> field -> key
  * constraints review ({rm}_constraints_review.csv)
        -> peripheral -> target_register -> target_operation

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
from applications.pac_codegen.constraints_review import resort_constraints_review_csv

root = sys.argv[1] if len(sys.argv) > 1 else "evaluation"

paths = set()
paths.update(glob.glob(os.path.join(root, "stm", "*", "*", "*_review.csv")))        # run-root files
paths.update(glob.glob(os.path.join(root, "stm", "*", "*", "*", "*_review.csv")))   # per-SVD files

n_bug = n_con = 0
for p in sorted(paths):
    if "constraints" in os.path.basename(p):
        resort_constraints_review_csv(p)
        n_con += 1
    else:
        resort_review_csv(p)
        n_bug += 1
print(f"re-sorted {n_bug} bug review + {n_con} constraints review CSV(s)")
