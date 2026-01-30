"""
Tradeoff plots for filtered experiments (F1 + time thresholds).

Outputs:
  - time_vs_tokens_f1_filtered.png
  - f1_vs_tokens_time_filtered.png
  - time_breakdown_bars.png
  - token_breakdown_bars.png

Example:
    python optimization_validator/plot_experiment_tradeoffs.py \
      --experiment-dir optimization_validator/stm-rm0041/experiments/batch_sizes_embeddings \
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


def _compute_time_breakdown(timing_rows: list[dict]) -> dict[str, dict]:
    breakdown = {}
    for row in timing_rows:
        model_name = row.get("model_name", "").strip()
        operation = row.get("operation", "").strip()
        if not model_name or operation not in {"validator_llm_call", "vector_store_search"}:
            continue
        try:
            total_time = float(row.get("total_time", 0))
        except (TypeError, ValueError):
            total_time = 0.0
        breakdown.setdefault(model_name, {"llm_time": 0.0, "search_time": 0.0})
        if operation == "validator_llm_call":
            breakdown[model_name]["llm_time"] += total_time
        else:
            breakdown[model_name]["search_time"] += total_time
    return breakdown


def _read_usage_totals(usage_csv_path: Path) -> dict:
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "file_search_tokens": 0,
    }
    if not usage_csv_path.exists():
        return totals
    rows = _read_csv_rows(usage_csv_path)
    for row in rows:
        try:
            totals["input_tokens"] += int(row.get("input_tokens", 0))
            totals["output_tokens"] += int(row.get("output_tokens", 0))
            totals["file_search_tokens"] += int(row.get("file_search_tokens", 0))
        except (TypeError, ValueError):
            continue
    return totals


def _format_label(model_name: str) -> str:
    prefix = "gpt-oss-120b_test_"
    if model_name.startswith(prefix):
        return model_name[len(prefix):]
    return model_name


def _build_points(experiment_dir: Path) -> list[dict]:
    accuracy_path = experiment_dir / "summary_accuracy.csv"
    usage_path = experiment_dir / "summary_usage.csv"
    timing_path = experiment_dir / "summary_timing.csv"

    accuracy_rows = _read_csv_rows(accuracy_path)
    usage_rows = _read_csv_rows(usage_path)
    timing_rows = _read_csv_rows(timing_path)

    total_times = _compute_total_times(timing_rows)
    time_breakdown = _compute_time_breakdown(timing_rows)
    api_calls = _compute_api_calls(timing_rows)
    total_tokens = {
        row.get("model_name", "").strip(): float(row.get("total_tokens", 0))
        for row in usage_rows
    }

    points = []
    for row in accuracy_rows:
        model_name = row.get("model_name", "").strip()
        if not model_name or model_name not in total_times:
            continue
        try:
            f1_score = float(row.get("f1_score", 0))
        except (TypeError, ValueError):
            f1_score = 0.0
        points.append({
            "model_name": model_name,
            "label": _format_label(model_name),
            "total_time": total_times[model_name],
            "f1_score": f1_score,
            "total_tokens": total_tokens.get(model_name, 0.0),
            "time_breakdown": time_breakdown.get(model_name, {"llm_time": 0.0, "search_time": 0.0}),
            "api_calls": api_calls.get(model_name, 0),
        })
    return points


def _parse_batch_and_emb(label: str) -> tuple[int, int]:
    # Expected forms like "batched_test_emb16_bs3" or "batched_test_emb8"
    emb = 0
    bs = 0
    parts = label.split("_")
    for part in parts:
        if part.startswith("emb"):
            try:
                emb = int(part.replace("emb", ""))
            except ValueError:
                emb = 0
        if part.startswith("bs"):
            try:
                bs = int(part.replace("bs", ""))
            except ValueError:
                bs = 0
    return bs, emb


def _sort_points(points: list[dict]) -> list[dict]:
    return sorted(points, key=lambda p: _parse_batch_and_emb(p["label"]))


def _pareto_front(points: list[dict]) -> list[dict]:
    # Minimize time and tokens, within the filtered F1 set.
    sorted_points = sorted(points, key=lambda p: (p["total_time"], p["total_tokens"]))
    front = []
    best_tokens = float("inf")
    for p in sorted_points:
        if p["total_tokens"] < best_tokens:
            front.append(p)
            best_tokens = p["total_tokens"]
    return front


def _scatter_time_vs_tokens(points: list[dict], output_path: Path, min_f1: float):
    x_vals = [p["total_time"] for p in points]
    y_vals = [p["total_tokens"] for p in points]
    colors = [p["f1_score"] for p in points]

    plt.figure(figsize=(8, 5))
    scatter = plt.scatter(x_vals, y_vals, c=colors, cmap="viridis", s=120, alpha=0.8, edgecolors="k", linewidths=0.5)
    plt.xlabel("Total time (s) = vector store search + LLM call")
    plt.ylabel("Total tokens")
    plt.title(f"Time vs Tokens (F1 >= {min_f1:.2f})")
    plt.colorbar(scatter, label="F1 score")
    plt.xlim(0, 1000)
    plt.xticks([0, 300, 600, 900, 1000])

    for p in points:
        plt.annotate(
            f"{p['label']} (calls={p['api_calls']})",
            (p["total_time"], p["total_tokens"]),
            textcoords="offset points",
            xytext=(5, 3),
            fontsize=8,
        )

    # Pareto front (min time & tokens)
    front = _pareto_front(points)
    if front:
        front_x = [p["total_time"] for p in front]
        front_y = [p["total_tokens"] for p in front]
        plt.plot(front_x, front_y, linestyle="--", color="red", linewidth=1)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)


def _scatter_f1_vs_tokens(points: list[dict], output_path: Path, min_f1: float):
    x_vals = [p["total_tokens"] for p in points]
    y_vals = [p["f1_score"] for p in points]
    colors = [p["total_time"] for p in points]

    plt.figure(figsize=(8, 5))
    scatter = plt.scatter(x_vals, y_vals, c=colors, cmap="plasma", s=120, alpha=0.8, edgecolors="k", linewidths=0.5)
    plt.xlabel("Total tokens")
    plt.ylabel("F1 score")
    plt.title(f"F1 vs Tokens (colored by time, F1 >= {min_f1:.2f})")
    plt.axhline(min_f1, linestyle="--", color="red", linewidth=1)
    plt.colorbar(scatter, label="Total time (s)")
    max_x = max(x_vals) if x_vals else 0
    plt.xlim(0, max_x + 100)

    for p in points:
        plt.annotate(
            f"{p['label']} (calls={p['api_calls']})",
            (p["total_tokens"], p["f1_score"]),
            textcoords="offset points",
            xytext=(5, 3),
            fontsize=8,
        )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)


def _bar_time_breakdown(points: list[dict], output_path: Path, min_f1: float, max_time: float):
    points = _sort_points(points)
    labels = [f"{p['label']} (calls={p['api_calls']})" for p in points]
    search_times = [p["time_breakdown"]["search_time"] for p in points]
    llm_times = [p["time_breakdown"]["llm_time"] for p in points]

    plt.figure(figsize=(9, 5))
    plt.bar(labels, search_times, label="Vector store search", color="#8CB4E0", edgecolor="none")
    plt.bar(labels, llm_times, bottom=search_times, label="LLM call", color="#F2A65A", edgecolor="none")
    plt.ylabel("Total time (s)")
    plt.title(f"Time breakdown (F1 >= {min_f1:.2f}, time <= {max_time:.0f}s)")
    plt.xticks(rotation=30, ha="right")
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)


def _bar_token_breakdown(experiment_dir: Path, points: list[dict], output_path: Path, min_f1: float, max_time: float):
    points = _sort_points(points)
    labels = [f"{p['label']} (calls={p['api_calls']})" for p in points]
    file_search_tokens = []
    non_search_input_tokens = []
    output_tokens = []

    for p in points:
        usage_csv = next((experiment_dir / p["model_name"]).glob("validator_usage_*.csv"), None)
        totals = _read_usage_totals(usage_csv) if usage_csv else {"input_tokens": 0, "output_tokens": 0, "file_search_tokens": 0}
        fs_tokens = totals["file_search_tokens"]
        input_tokens = totals["input_tokens"]
        non_search = max(input_tokens - fs_tokens, 0)
        file_search_tokens.append(fs_tokens)
        non_search_input_tokens.append(non_search)
        output_tokens.append(totals["output_tokens"])

    plt.figure(figsize=(9, 5))
    plt.bar(labels, file_search_tokens, label="File search tokens", color="#8FCB9B")
    plt.bar(labels, non_search_input_tokens, bottom=file_search_tokens, label="Non-search input tokens", color="#8CB4E0")
    bottom = [a + b for a, b in zip(file_search_tokens, non_search_input_tokens)]
    plt.bar(labels, output_tokens, bottom=bottom, label="Output tokens", color="#F2A65A")
    plt.ylabel("Total tokens")
    plt.title(f"Token breakdown (F1 >= {min_f1:.2f}, time <= {max_time:.0f}s)")
    plt.xticks(rotation=30, ha="right")
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)


def main():
    parser = argparse.ArgumentParser(description="Plot tradeoffs for high-F1 experiments.")
    parser.add_argument(
        "--experiment-dir",
        default="optimization_validator/stm-rm0041/experiments/batch_sizes_embeddings",
        help="Path to experiment directory containing summary CSVs",
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
    args = parser.parse_args()

    experiment_dir = Path(args.experiment_dir)
    points = _build_points(experiment_dir)
    filtered = [
        p for p in points
        if p["f1_score"] >= args.min_f1 and p["total_time"] <= args.max_time
    ]
    if not filtered:
        raise SystemExit("No points found after F1 filter.")

    _scatter_time_vs_tokens(
        filtered,
        experiment_dir / "time_vs_tokens_f1_filtered.png",
        args.min_f1,
    )
    _scatter_f1_vs_tokens(
        filtered,
        experiment_dir / "f1_vs_tokens_time_filtered.png",
        args.min_f1,
    )
    _bar_time_breakdown(
        filtered,
        experiment_dir / "time_breakdown_bars.png",
        args.min_f1,
        args.max_time,
    )
    _bar_token_breakdown(
        experiment_dir,
        filtered,
        experiment_dir / "token_breakdown_bars.png",
        args.min_f1,
        args.max_time,
    )
    print(f"Saved plots to {experiment_dir}")


if __name__ == "__main__":
    main()
