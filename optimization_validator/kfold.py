"""Build a corrupted benchmark and split it into k folds at (Peripheral, Register)
granularity for Validator cross-validation.

Paper protocol (section "Benchmarking the Validator as a Noisy Labeler"):
  * Construct k folds at the (Peripheral, Register) granularity — NOT the invariant
    row level — so correlated invariants from the same register never appear in both
    the training and held-out partitions.
  * Before splitting, corrupt 30% of invariants by modifying values or field names,
    REPLACING the original with its corrupted version (no true/corrupted pairs).
  * Every fold must contain both positive (correct) and negative (corrupted) cases.

This module produces a single benchmark DataFrame with these added columns:
    is_correct       bool   — True for untouched (correct) invariants, False if corrupted
    corruption_type  str    — "" | "value" | "field_name"
    fold             int    — fold index in [0, k)
plus the verified-datasheet columns (peripheral, register, field_name, key,
correct_value). `correct_value` holds the *candidate* value shown to the Validator
(the true value for positives, the wrong value for negatives), matching the column
name the existing run_validator code already reads.
"""

from __future__ import annotations

import os
import random

import pandas as pd

from optimization_validator.corruption import build_register_contexts, corrupt_row

# Verified-datasheet columns we carry into the benchmark.
_BASE_COLUMNS = ["peripheral", "register", "field_name", "key", "correct_value"]
# Optional columns we carry through when present (else filled with ""). `alt_name` is the
# field/register name as printed in the datasheet when it differs from the SVD key; the
# Validator can use it to avoid rejecting a correct fact on a pure name mismatch.
_CARRIED_OPTIONAL = ["alt_name"]

# In the verified-datasheet schema (verified_datasheet/annotate.py) a row is
# authoritative ground truth only when its status is exactly this. Every other status
# (not-specified, datasheet-ambiguous, the per-peripheral `derived` marker rows, or an
# empty/pending status) has an empty correct_value by construction, so it is neither a
# trustworthy positive nor a corruptible base.
GROUND_TRUTH_STATUS = "verified"


def select_ground_truth(df: pd.DataFrame, source: str = "") -> pd.DataFrame:
    """Keep only rows usable as ground truth: status == 'verified' with a correct_value.

    Gating on status drops `derived` marker rows (peripheral-inheritance placeholders
    with no register/key/value), `not-specified`, `datasheet-ambiguous` and pending rows
    in one shot. Raises if nothing survives — typically an unannotated slice (e.g.
    rm0394), which should fail loudly here rather than as an opaque k-fold error.
    """
    if "status" not in df.columns:
        raise ValueError(
            f"{source or 'verified CSV'}: missing required `status` column. Verified "
            "datasheets must be produced by verified_datasheet/annotate.py."
        )
    df = df.copy()
    df["correct_value"] = df["correct_value"].astype(str).str.strip()
    n_before = len(df)
    status = df["status"].astype(str).str.strip().str.lower()
    df = df[(status == GROUND_TRUTH_STATUS) & (df["correct_value"] != "")].reset_index(drop=True)
    n_after = len(df)
    tag = source or "verified CSV"
    if n_after < n_before:
        print(f"[verified] {tag}: kept {n_after}/{n_before} ground-truth rows "
              f"(dropped {n_before - n_after}: pending / derived / not-specified / empty)")
    if n_after == 0:
        raise ValueError(
            f"{tag}: no usable ground-truth rows (status=='{GROUND_TRUTH_STATUS}' with a "
            "correct_value). The slice is likely unannotated (e.g. rm0394) — finish "
            "annotating it or point --verified-csv at a completed slice."
        )
    return df


def load_verified(csv_path: str) -> pd.DataFrame:
    """Load a verified datasheet, keep only ground-truth rows, return the base columns.

    See `select_ground_truth` for the row-selection contract (status gate + non-empty
    correct_value). Extra schema columns (alt_name, page, set_method, …) are ignored.
    """
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    missing = [c for c in _BASE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{csv_path} missing required columns: {missing}")
    df = select_ground_truth(df, source=os.path.basename(csv_path))
    keep = _BASE_COLUMNS + [c for c in _CARRIED_OPTIONAL if c in df.columns]
    out = df[keep].reset_index(drop=True)
    for c in _CARRIED_OPTIONAL:
        if c not in out.columns:
            out[c] = ""
    return out


def build_corrupted_benchmark(
    df: pd.DataFrame,
    corruption_fraction: float = 0.30,
    seed: int = 0,
    name_corruption_prob: float = 0.30,
) -> pd.DataFrame:
    """Corrupt `corruption_fraction` of invariant rows (replacing originals).

    Corruption is sampled at the row level (each row is one invariant) but uses
    per-register context so the wrong values stay realistic and in-range.
    """
    rng = random.Random(seed)
    contexts = build_register_contexts(df)

    n = len(df)
    n_corrupt = int(round(n * corruption_fraction))
    corrupt_idx = set(rng.sample(range(n), n_corrupt)) if n_corrupt > 0 else set()

    rows = []
    for i, row in enumerate(df.to_dict("records")):
        ctx = contexts[(row["peripheral"], row["register"])]
        if i in corrupt_idx:
            new_row = corrupt_row(row, ctx, rng, name_corruption_prob=name_corruption_prob)
        else:
            new_row = dict(row)
            new_row["is_correct"] = True
            new_row["corruption_type"] = ""
        rows.append(new_row)

    out = pd.DataFrame(rows)
    return out


def assign_folds(df: pd.DataFrame, k: int = 5, seed: int = 0) -> pd.DataFrame:
    """Assign each (peripheral, register) group to one of k folds (round-robin on a
    seeded shuffle of the groups). Returns df with an added integer `fold` column.

    Grouping by register guarantees correlated invariants share a fold.
    """
    if k < 2:
        raise ValueError("k must be >= 2 for cross-validation")
    rng = random.Random(seed)
    groups = list(df.groupby(["peripheral", "register"]).groups.keys())
    rng.shuffle(groups)
    if len(groups) < k:
        raise ValueError(
            f"only {len(groups)} (peripheral, register) groups for k={k} folds; "
            "reduce k or use a larger slice"
        )
    group_to_fold = {g: i % k for i, g in enumerate(groups)}
    df = df.copy()
    df["fold"] = df.apply(lambda r: group_to_fold[(r["peripheral"], r["register"])], axis=1)
    _warn_degenerate_folds(df, k)
    return df


def _warn_degenerate_folds(df: pd.DataFrame, k: int) -> None:
    for f in range(k):
        sub = df[df["fold"] == f]
        pos = int(sub["is_correct"].sum())
        neg = int((~sub["is_correct"]).sum())
        if pos == 0 or neg == 0:
            print(
                f"[kfold] WARNING fold {f} is degenerate (positives={pos}, negatives={neg}); "
                "F1 on this fold will be unreliable — consider a smaller k or larger slice"
            )


def make_benchmark_with_folds(
    csv_path: str,
    k: int = 5,
    corruption_fraction: float = 0.30,
    seed: int = 0,
    name_corruption_prob: float = 0.30,
) -> pd.DataFrame:
    """Convenience: verified CSV -> corrupted, fold-assigned benchmark DataFrame."""
    verified = load_verified(csv_path)
    benchmark = build_corrupted_benchmark(
        verified,
        corruption_fraction=corruption_fraction,
        seed=seed,
        name_corruption_prob=name_corruption_prob,
    )
    return assign_folds(benchmark, k=k, seed=seed)
