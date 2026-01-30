"""
Scatter plot of total time vs F1, sized by token usage.

Example:
    python optimization_validator/plot_experiment_scatter.py \
      --experiment-dir optimization_validator/stm-rm0041/experiments/batch_sizes_embeddings
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
        if not model_name or not operation:
            continue
        if operation not in {"validator_llm_call", "vector_store_search"}:
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


def _scale_sizes(values: list[float], min_size: float = 50.0, max_size: float = 450.0) -> list[float]:
    if not values:
        return []
    v_min = min(values)
    v_max = max(values)
    if v_max == v_min:
        return [0.5 * (min_size + max_size) for _ in values]
    return [
        min_size + (val - v_min) * (max_size - min_size) / (v_max - v_min)
        for val in values
    ]


def build_scatter_data(experiment_dir: Path) -> list[dict]:
    accuracy_path = experiment_dir / "summary_accuracy.csv"
    usage_path = experiment_dir / "summary_usage.csv"
    timing_path = experiment_dir / "summary_timing.csv"

    accuracy_rows = _read_csv_rows(accuracy_path)
    usage_rows = _read_csv_rows(usage_path)
    timing_rows = _read_csv_rows(timing_path)

    total_times = _compute_total_times(timing_rows)
    api_calls = _compute_api_calls(timing_rows)
    total_tokens = {
        row.get("model_name", "").strip(): float(row.get("total_tokens", 0))
        for row in usage_rows
    }

    points = []
    for row in accuracy_rows:
        model_name = row.get("model_name", "").strip()
        if not model_name:
            continue
        if model_name not in total_times:
            continue
        try:
            f1_score = float(row.get("f1_score", 0))
        except (TypeError, ValueError):
            f1_score = 0.0
        points.append({
            "model_name": model_name,
            "total_time": total_times[model_name],
            "f1_score": f1_score,
            "total_tokens": total_tokens.get(model_name, 0.0),
            "api_calls": api_calls.get(model_name, 0),
        })
    return points


def _format_label(model_name: str) -> str:
    prefix = "gpt-oss-120b_test_"
    if model_name.startswith(prefix):
        return model_name[len(prefix):]
    return model_name


def plot_scatter(points: list[dict], output_path: Path, annotate: bool = True):
    x_vals = [p["total_time"] for p in points]
    y_vals = [p["f1_score"] for p in points]
    token_vals = [p["total_tokens"] for p in points]
    sizes = _scale_sizes(token_vals)

    plt.figure(figsize=(8, 5))
    plt.scatter(x_vals, y_vals, s=sizes, alpha=0.7, edgecolors="k", linewidths=0.5)
    plt.xlabel("Total time (s) = vector store search + LLM call")
    plt.ylabel("F1 score")
    plt.title("Experiment tradeoff: Time vs F1 for 1000 invariants")
    plt.axhline(0.92, linestyle="--", color="red", linewidth=1)
    plt.axvline(1000, linestyle="--", color="red", linewidth=1)

    for p in points:
        plt.annotate(
            f"{_format_label(p['model_name'])} (calls={p['api_calls']})",
            (p["total_time"], p["f1_score"]),
            textcoords="offset points",
            xytext=(5, 3),
            fontsize=8,
        )

    max_x = max(x_vals) if x_vals else 0
    plt.xlim(0, max_x + 100)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)


def main():
    parser = argparse.ArgumentParser(description="Plot time vs F1 scatter from experiment summaries.")
    parser.add_argument(
        "--experiment-dir",
        default="optimization_validator/stm-rm0041/experiments/batch_sizes_embeddings",
        help="Path to experiment directory containing summary CSVs",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output PNG path (default: <experiment-dir>/time_vs_f1_scatter.png)",
    )
    parser.add_argument(
        "--annotate",
        action="store_true",
        help="Deprecated; labels are always shown",
    )
    args = parser.parse_args()

    experiment_dir = Path(args.experiment_dir)
    output_path = Path(args.output) if args.output else experiment_dir / "time_vs_f1_scatter.png"

    points = build_scatter_data(experiment_dir)
    if not points:
        raise SystemExit("No points found. Check summary CSVs and experiment directory.")

    plot_scatter(points, output_path)
    print(f"Saved plot to {output_path}")


if __name__ == "__main__":
    main()
