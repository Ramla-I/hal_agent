"""Build synthetic Validator test sets by corrupting a verified datasheet.

Corruptions are now *realistic* (paper section "Benchmarking the Validator as a Noisy
Labeler"): wrong values are produced by the per-key strategies in `corruption.py`
(in-range bit fields, nibble-flipped / neighbour hex, size in {8,16,32}, real sibling
field names or one-edit typos) instead of the old uniform-random values
(`bit_width=69`) and gibberish names (`vvayurpxfkp`), which the Validator could reject
trivially and which therefore biased its measured specificity.

Two entry points:
  * create_test_set(...)            — legacy row-range API (kept for compatibility),
                                       now backed by realistic corruption.
  * make_benchmark_with_folds(...)  — preferred: a corrupted, (Peripheral, Register)-
                                       folded benchmark for cross-validation
                                       (see optimization_validator/kfold.py).

Output columns match what run_validator / run_validator_batched expect:
  peripheral, register, field_name, key, correct_value, is_correct
plus corruption_type for error analysis.
"""

from __future__ import annotations

import os
import random
import sys

import pandas as pd

# Allow `python optimization_validator/create_test_set.py` as well as package import.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimization_validator.corruption import (  # noqa: E402
    build_register_contexts,
    corrupt_field_name,
    corrupt_value,
)
from optimization_validator.kfold import make_benchmark_with_folds  # noqa: E402  (re-exported)

_OUTPUT_COLUMNS = ["peripheral", "register", "field_name", "key", "correct_value", "is_correct", "corruption_type"]


def create_test_set(
    csv_file_path,
    start_row,
    end_row,
    keep_percentage,
    incorrect_value_percentage,
    incorrect_name_percentage=0,
    seed: int = 0,
):
    """Create a test set from a verified CSV with *realistic* corruptions.

    Args:
        csv_file_path: Path to the verified datasheet CSV.
        start_row, end_row: Row slice of the verified CSV to use.
        keep_percentage: Percentage of rows left unchanged (correct positives).
        incorrect_value_percentage: Percentage of rows whose value is corrupted.
        incorrect_name_percentage: Percentage of rows whose field name is corrupted.
        seed: RNG seed for reproducibility.

    Returns:
        DataFrame with columns peripheral, register, field_name, key, correct_value,
        is_correct, corruption_type.

    Note: keep + incorrect_value + incorrect_name should sum to ~100. Rows with an
    empty correct_value are dropped (never human-verified, so not usable as ground
    truth or as a corruption base).
    """
    rng = random.Random(seed)

    df = pd.read_csv(csv_file_path, dtype=str, keep_default_na=False)
    df = df.iloc[start_row:end_row].reset_index(drop=True)
    df = df[["peripheral", "register", "field_name", "key", "correct_value"]].copy()
    df["correct_value"] = df["correct_value"].astype(str).str.strip()
    df = df[df["correct_value"] != ""].reset_index(drop=True)

    contexts = build_register_contexts(df)

    total = len(df)
    num_names = int(total * incorrect_name_percentage / 100)
    num_values = int(total * incorrect_value_percentage / 100)

    df["is_correct"] = True
    df["corruption_type"] = ""

    # Field-name corruptions only apply to rows that actually have a field name.
    field_row_indices = [i for i in range(total) if str(df.loc[i, "field_name"]).strip() != ""]
    rng.shuffle(field_row_indices)
    name_indices = set(field_row_indices[:num_names])

    for idx in name_indices:
        ctx = contexts[(df.loc[idx, "peripheral"], df.loc[idx, "register"])]
        df.loc[idx, "field_name"] = corrupt_field_name(str(df.loc[idx, "field_name"]), ctx, rng)
        df.loc[idx, "is_correct"] = False
        df.loc[idx, "corruption_type"] = "field_name"

    available = [i for i in range(total) if i not in name_indices]
    rng.shuffle(available)
    value_indices = available[: min(num_values, len(available))]

    for idx in value_indices:
        ctx = contexts[(df.loc[idx, "peripheral"], df.loc[idx, "register"])]
        field_name = str(df.loc[idx, "field_name"]).strip()
        df.loc[idx, "correct_value"] = corrupt_value(
            df.loc[idx, "key"], df.loc[idx, "correct_value"], ctx, field_name, rng
        )
        df.loc[idx, "is_correct"] = False
        df.loc[idx, "corruption_type"] = "value"

    return df[_OUTPUT_COLUMNS]


def save_test_set(df, output_path):
    df.to_csv(output_path, index=False)
    print(f"Test set saved to {output_path}")


if __name__ == "__main__":
    csv_path = "verified_datasheet/stm/rm0041_stm32f100.csv"
    result_df = create_test_set(
        csv_path,
        start_row=0,
        end_row=10_000,
        keep_percentage=70,
        incorrect_value_percentage=20,
        incorrect_name_percentage=10,
        seed=0,
    )
    print(f"Total rows:        {len(result_df)}")
    print(f"is_correct=True:   {int(result_df['is_correct'].sum())}")
    print(f"is_correct=False:  {int((~result_df['is_correct']).sum())}")
    print(result_df["corruption_type"].value_counts().to_dict())
