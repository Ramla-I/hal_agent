"""
Bar plot comparing file search tokens vs total_peripheral_tokens.

Example:
    python optimization_validator/plot_file_search_tokens_vs_chunks.py \
      --experiment-dir optimization_validator/stm-rm0041/experiments/batch_sizes_embeddings \
      --test-set optimization_validator/stm-rm0041/test_set_rm0041.csv \
      --peripheral-mapping devices/stm/rm0041/peripheral_pages_md/peripheral_pages_mapping.csv \
      --min-f1 0.92 \
      --max-time 1000
"""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def _read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def _compute_total_times(timing_rows: list[dict]) -> dict[str, float]:
    totals = {}
    for row in timing_rows:
        model_name = row.get("model_name", "").strip()
        operation = row.get("operation", "").strip()
        if not model_name or operation not in {"validator_llm_call", "vector_store_search"}:
            continue
        try:
            total_time = float(row.get("total_time", 0))
        except (TypeError, ValueError):
            total_time = 0.0
        totals[model_name] = totals.get(model_name, 0.0) + total_time
    return totals


def _compute_api_calls(timing_rows: list[dict]) -> dict[str, int]:
    api_calls = {}
    for row in timing_rows:
        model_name = row.get("model_name", "").strip()
        operation = row.get("operation", "").strip()
        if not model_name or operation != "validator_llm_call":
            continue
        try:
            count = int(float(row.get("count", 0)))
        except (TypeError, ValueError):
            count = 0
        api_calls[model_name] = count
    return api_calls


def _format_label(model_name: str) -> str:
    prefix = "gpt-oss-120b_test_"
    if model_name.startswith(prefix):
        return model_name[len(prefix):]
    return model_name


def _collect_peripherals(test_set_path: Path) -> set[str]:
    rows = _read_csv_rows(test_set_path)
    peripherals = set()
    for row in rows:
        name = row.get("peripheral", "").strip().lower()
        if name:
            peripherals.add(name)
    return peripherals


def _load_peripheral_token_map(mapping_path: Path, token_column: str) -> dict[str, int]:
    rows = _read_csv_rows(mapping_path)
    token_map = {}
    for row in rows:
        raw_name = row.get("peripheral_name", "").strip().lower()
        if not raw_name:
            continue
        try:
            token_value = int(float(row.get(token_column, 0)))
        except (TypeError, ValueError):
            token_value = 0
        for name in raw_name.split("/"):
            name = name.strip()
            if name:
                token_map[name] = token_value
    return token_map


def _sum_file_search_tokens(usage_csv_path: Path) -> int:
    if not usage_csv_path.exists():
        return 0
    rows = _read_csv_rows(usage_csv_path)
    total = 0
    for row in rows:
        try:
            total += int(row.get("file_search_tokens", 0))
        except (TypeError, ValueError):
            continue
    return total


def main():
    parser = argparse.ArgumentParser(description="Plot file search tokens vs total chunk tokens.")
    parser.add_argument(
        "--experiment-dir",
        default="optimization_validator/stm-rm0041/experiments/batch_sizes_embeddings",
        help="Path to experiment directory containing summary CSVs",
    )
    parser.add_argument(
        "--test-set",
        default="optimization_validator/stm-rm0041/test_set_rm0041.csv",
        help="Path to test set CSV",
    )
    parser.add_argument(
        "--peripheral-mapping",
        default="devices/stm/rm0041/peripheral_pages_md/peripheral_pages_mapping.csv",
        help="Path to peripheral pages mapping CSV",
    )
    parser.add_argument(
        "--token-column",
        default="total_tokens_chunks_800_400",
        help="Column in mapping CSV for chunk token totals",
    )
    parser.add_argument(
        "--min-f1",
        type=float,
        default=0.92,
        help="Minimum F1 score to include",
    )
    parser.add_argument(
        "--max-time",
        type=float,
        default=1000.0,
        help="Maximum total time (s) to include",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output PNG path (default: <experiment-dir>/plot_file_search_tokens_vs_chunks.png)",
    )
    args = parser.parse_args()

    experiment_dir = Path(args.experiment_dir)
    output_path = Path(args.output) if args.output else experiment_dir / "plot_file_search_tokens_vs_chunks.png"

    plot_file_search_tokens_vs_chunks(
        experiment_dir=experiment_dir,
        test_set_path=Path(args.test_set),
        peripheral_mapping_path=Path(args.peripheral_mapping),
        token_column=args.token_column,
        min_f1=args.min_f1,
        max_time=args.max_time,
        output_path=output_path,
    )
    print(f"Saved plot to {output_path}")


def plot_file_search_tokens_vs_chunks(
    *,
    experiment_dir: Path,
    test_set_path: Path,
    peripheral_mapping_path: Path,
    token_column: str,
    min_f1: float,
    max_time: float,
    output_path: Path,
):
    accuracy_rows = _read_csv_rows(experiment_dir / "summary_accuracy.csv")
    timing_rows = _read_csv_rows(experiment_dir / "summary_timing.csv")
    total_times = _compute_total_times(timing_rows)
    api_calls = _compute_api_calls(timing_rows)

    # Compute total chunk tokens for peripherals in test set
    peripherals = _collect_peripherals(test_set_path)
    token_map = _load_peripheral_token_map(peripheral_mapping_path, token_column)
    missing = sorted([p for p in peripherals if p not in token_map])
    total_chunk_tokens = sum(token_map.get(p, 0) for p in peripherals)

    # Filter experiments by F1 and time
    filtered_models = []
    for row in accuracy_rows:
        model_name = row.get("model_name", "").strip()
        if not model_name or model_name not in total_times:
            continue
        try:
            f1_score = float(row.get("f1_score", 0))
        except (TypeError, ValueError):
            f1_score = 0.0
        total_time = total_times.get(model_name, 0.0)
        if f1_score >= min_f1 and total_time <= max_time:
            filtered_models.append(model_name)

    # Build bars
    labels = []
    file_search_tokens = []
    for model_name in sorted(filtered_models):
        usage_csv = next((experiment_dir / model_name).glob("validator_usage_*.csv"), None)
        labels.append(f"{_format_label(model_name)} (calls={api_calls.get(model_name, 0)})")
        file_search_tokens.append(_sum_file_search_tokens(usage_csv) if usage_csv else 0)

    if not labels:
        raise SystemExit("No experiments found after F1/time filtering.")

    plt.figure(figsize=(9, 5))
    plt.bar(labels, file_search_tokens, color="#8CB4E0", label="File search tokens")
    plt.plot(range(len(labels)), [total_chunk_tokens] * len(labels), color="#F2A65A", linestyle="--", label="Total chunk tokens")
    plt.ylabel("Tokens")
    plt.title(
        f"File search tokens vs total_peripheral_tokens "
        f"(total={total_chunk_tokens:,})"
    )
    plt.xticks(rotation=30, ha="right")
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)

    if missing:
        print(f"Warning: missing peripherals in mapping: {', '.join(missing)}")


if __name__ == "__main__":
    main()
