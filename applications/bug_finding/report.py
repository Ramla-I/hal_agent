"""Emit the per-SVD review CSV — the one persisted output of bug-finding.

One CSV per SVD file, rows grouped by bug class (one class → one prospective PR).
``proposed_svd_fix`` is pre-filled with the generator's value so reviewer
approval is a one-click confirm; if the datasheet evidence shows the generator's
value is wrong, the reviewer marks the row ``false_positive`` instead.
"""
from __future__ import annotations

import csv
import os

from .models import BugClass, BugStatus

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
    "tp_fp",  # reviewer-filled ground-truth label: TP / FP (left blank for manual review)
]


def _collapse(text: str) -> str:
    """Flatten whitespace so multi-line evidence sits in a single CSV cell."""
    return " ".join((text or "").split())


# Columns that identify a row across regenerations (so reviewer labels can be
# carried over). Includes svd_file so the consolidated per-run file disambiguates
# identical registers across sibling SVDs. Excludes volatile fields like
# confidence/evidence/status.
_ROW_KEY_FIELDS = ("svd_file", "peripheral", "register", "field", "key", "svd_value", "generator_value")


def _row_key(row: dict) -> tuple:
    return tuple(row.get(c, "") for c in _ROW_KEY_FIELDS)


def _load_existing_tp_fp(output_path: str) -> dict[tuple, str]:
    """Map row-identity -> filled tp_fp value from an existing review CSV."""
    if not os.path.exists(output_path):
        return {}
    preserved: dict[tuple, str] = {}
    try:
        with open(output_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                val = (row.get("tp_fp") or "").strip()
                if val:
                    preserved[_row_key(row)] = val
    except Exception:
        return {}
    return preserved


def write_review_csv(bug_classes: list[BugClass], output_path: str) -> int:
    """Write the review CSV for one SVD file. Returns the number of bug rows.

    The file is always written (even with zero bugs) so a reviewer can see the
    SVD was processed. Any reviewer-filled ``tp_fp`` labels in an existing file at
    *output_path* are preserved (matched by row identity) so a re-run doesn't wipe
    them.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    preserved_tp_fp = _load_existing_tp_fp(output_path)

    n_rows = 0
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_CSV_FIELDS)
        writer.writeheader()
        for bug_class in bug_classes:
            for bug in bug_class.bugs:
                d = bug.diff
                row = {
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
                }
                row["tp_fp"] = preserved_tp_fp.get(_row_key(row), "")  # carry over reviewer label
                writer.writerow(row)
                n_rows += 1
    return n_rows


# Consolidated run-level file: one row per distinct bug (deduped across the RM's
# SVDs), dropping per-SVD confidence in favour of which SVDs share the bug.
CONSOLIDATED_REVIEW_FIELDS = [
    "bug_class_id",
    "peripheral",
    "register",
    "field",
    "key",
    "svd_value",
    "generator_value",
    "proposed_svd_fix",
    "datasheet_evidence",
    "status",
    "svd_count",
    "svd_files",
    "tp_fp",
]

# A bug's identity for cross-SVD dedup (the discrepancy itself; no svd_file).
_BUG_KEY_FIELDS = ("peripheral", "register", "field", "key", "svd_value", "generator_value")


def _bug_key(row: dict) -> tuple:
    return tuple(row.get(c, "") for c in _BUG_KEY_FIELDS)


def _load_consolidated_tp_fp(output_path: str) -> dict[tuple, str]:
    if not os.path.exists(output_path):
        return {}
    preserved: dict[tuple, str] = {}
    try:
        with open(output_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                val = (row.get("tp_fp") or "").strip()
                if val:
                    preserved[_bug_key(row)] = val
    except Exception:
        return {}
    return preserved


def write_consolidated_review_csv(bug_classes: list[BugClass], output_path: str) -> int:
    """Write the run-level review file: one row per distinct bug, deduped across
    the RM's SVDs, with the sharing SVDs listed. Returns the number of rows.

    Identical discrepancies across sibling SVDs collapse to one row (``svd_files``
    lists them); a register that genuinely differs between SVDs stays its own row.
    Reviewer ``tp_fp`` labels are preserved across re-runs.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    preserved = _load_consolidated_tp_fp(output_path)

    groups: dict[tuple, list[tuple[str, object]]] = {}
    order: list[tuple] = []
    for bug_class in bug_classes:
        for bug in bug_class.bugs:
            d = bug.diff
            key = (
                d.peripheral, d.register, d.field or "", d.key,
                d.svd_value if d.svd_value is not None else "",
                d.generator_value if d.generator_value is not None else "",
            )
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append((bug_class.svd_file, bug))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CONSOLIDATED_REVIEW_FIELDS)
        writer.writeheader()
        for key in order:
            members = groups[key]
            peripheral, register, field, dkey, svd_value, generator_value = key
            svds = sorted({svd for svd, _ in members})
            # candidate if it survived analysis in ANY SVD; FP only if FP everywhere.
            all_fp = all(bug.status == BugStatus.FALSE_POSITIVE for _, bug in members)
            status = BugStatus.FALSE_POSITIVE.value if all_fp else ""
            evidence = next((_collapse(b.datasheet_evidence) for _, b in members if b.datasheet_evidence), "")
            row = {
                "bug_class_id": f"{peripheral}:{dkey}",
                "peripheral": peripheral,
                "register": register,
                "field": field,
                "key": dkey,
                "svd_value": svd_value,
                "generator_value": generator_value,
                "proposed_svd_fix": generator_value,
                "datasheet_evidence": evidence,
                "status": status,
                "svd_count": len(svds),
                "svd_files": ";".join(svds),
                "tp_fp": preserved.get(key, ""),  # group key matches _BUG_KEY_FIELDS order
            }
            writer.writerow(row)
    return len(order)
