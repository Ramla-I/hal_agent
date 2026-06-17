"""Emit the per-SVD review CSV — the one persisted output of bug-finding.

One CSV per SVD file, rows grouped by bug class (one class → one prospective PR).
``proposed_svd_fix`` is pre-filled with the generator's value so reviewer
approval is a one-click confirm; if the datasheet evidence shows the generator's
value is wrong, the reviewer marks the row ``false_positive`` instead.
"""
from __future__ import annotations

import csv
import os

from .models import BugClass

REVIEW_CSV_FIELDS = [
    "bug_class_id",
    "svd_file",
    "peripheral",
    "register",
    "field",
    "key",
    "svd_value",
    "generator_value",
    "proposed_svd_fix",
    "datasheet_evidence",
    "confidence",
    "status",
]


def _collapse(text: str) -> str:
    """Flatten whitespace so multi-line evidence sits in a single CSV cell."""
    return " ".join((text or "").split())


def write_review_csv(bug_classes: list[BugClass], output_path: str) -> int:
    """Write the review CSV for one SVD file. Returns the number of bug rows.

    The file is always written (even with zero bugs) so a reviewer can see the
    SVD was processed.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    n_rows = 0
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_CSV_FIELDS)
        writer.writeheader()
        for bug_class in bug_classes:
            for bug in bug_class.bugs:
                d = bug.diff
                writer.writerow({
                    "bug_class_id": bug_class.bug_class_id,
                    "svd_file": bug_class.svd_file,
                    "peripheral": d.peripheral,
                    "register": d.register,
                    "field": d.field or "",
                    "key": d.key,
                    "svd_value": d.svd_value if d.svd_value is not None else "",
                    "generator_value": d.generator_value if d.generator_value is not None else "",
                    "proposed_svd_fix": bug.proposed_svd_fix if bug.proposed_svd_fix is not None else "",
                    "datasheet_evidence": _collapse(bug.datasheet_evidence),
                    "confidence": f"{bug.confidence:.2f}",
                    "status": bug.status.value,
                })
                n_rows += 1
    return n_rows
