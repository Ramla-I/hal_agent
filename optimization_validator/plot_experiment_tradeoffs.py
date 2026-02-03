"""
Tradeoff plots for filtered experiments (F1 + time thresholds).

Outputs:
  - plot_time_vs_tokens_f1_filtered.png
  - plot_f1_vs_tokens_time_filtered.png
  - plot_time_breakdown_bars.png
  - plot_token_breakdown_bars.png
  - plot_batch_size_vs_usage_f1.png
  - plot_batch_size_embeddings_tokens_f1.png

Example:
    python optimization_validator/plot_experiment_tradeoffs.py \
      --experiment-dir optimization_validator/stm-rm0041/experiments/batch_sizes_embeddings \
      --min-f1 0.92 \
      --max-time 1000
"""

import argparse
import csv
import re
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import ticker as mticker


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


def _parse_batch_size(model_name: str) -> int | None:
    match = re.search(r"_bs(\d+)", model_name)
    if match:
        return int(match.group(1))
    return None


def _is_sequential(model_name: str) -> bool:
    return "sequential" in model_name


def _parse_embedding_count(model_name: str) -> int | None:
    match = re.search(r"_emb(\d+)", model_name)
    if match:
        return int(match.group(1))
    return None


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


def _build_batch_usage_points(experiment_dir: Path, usage_field: str) -> list[dict]:
    accuracy_rows = _read_csv_rows(experiment_dir / "summary_accuracy.csv")
    usage_rows = _read_csv_rows(experiment_dir / "summary_usage.csv")
    timing_rows = _read_csv_rows(experiment_dir / "summary_timing.csv")

    api_calls = _compute_api_calls(timing_rows)
    f1_by_model = {}
    for row in accuracy_rows:
        model_name = row.get("model_name", "").strip()
        if not model_name:
            continue
        try:
            f1_by_model[model_name] = float(row.get("f1_score", 0))
        except (TypeError, ValueError):
            f1_by_model[model_name] = 0.0

    points = []
    for row in usage_rows:
        model_name = row.get("model_name", "").strip()
        if not model_name:
            continue
        batch_size = _parse_batch_size(model_name)
        if batch_size is None:
            continue
        try:
            usage_value = float(row.get(usage_field, 0))
        except (TypeError, ValueError):
            usage_value = 0.0
        label = _format_label(model_name).replace("sequential", "seq")
        points.append({
            "model_name": model_name,
            "label": label,
            "batch_size": batch_size,
            "usage": usage_value,
            "f1_score": f1_by_model.get(model_name, 0.0),
            "api_calls": api_calls.get(model_name, 0),
        })
    return points


def _scatter_batch_size_vs_usage(points: list[dict], output_path: Path, usage_field: str):
    x_vals = [p["batch_size"] for p in points]
    y_vals = [p["usage"] for p in points]
    colors = [p["f1_score"] for p in points]

    plt.figure(figsize=(8, 5))
    scatter = plt.scatter(
        x_vals,
        y_vals,
        c=colors,
        cmap="viridis",
        s=120,
        alpha=0.8,
        edgecolors="k",
        linewidths=0.5,
    )
    plt.xlabel("Batch size (invariants per call)")
    plt.ylabel(usage_field.replace("_", " ").title())
    plt.title("Batch size vs usage (colored by F1 score)")
    plt.colorbar(scatter, label="F1 score")
    plt.xticks(sorted(set(x_vals)))

    for p in points:
        plt.annotate(
            f"{p['label']} (calls={p['api_calls']})",
            (p["batch_size"], p["usage"]),
            textcoords="offset points",
            xytext=(5, 3),
            fontsize=8,
        )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)


def _build_batch_embedding_points(experiment_dir: Path) -> list[dict]:
    usage_rows = _read_csv_rows(experiment_dir / "summary_usage.csv")
    accuracy_rows = _read_csv_rows(experiment_dir / "summary_accuracy.csv")
    timing_rows = _read_csv_rows(experiment_dir / "summary_timing.csv")
    api_calls = _compute_api_calls(timing_rows)
    total_times = _compute_total_times(timing_rows)

    tokens_by_model = {}
    for row in usage_rows:
        model_name = row.get("model_name", "").strip()
        if not model_name:
            continue
        try:
            tokens_by_model[model_name] = float(row.get("total_tokens", 0))
        except (TypeError, ValueError):
            tokens_by_model[model_name] = 0.0

    f1_by_model = {}
    for row in accuracy_rows:
        model_name = row.get("model_name", "").strip()
        if not model_name:
            continue
        try:
            f1_by_model[model_name] = float(row.get("f1_score", 0))
        except (TypeError, ValueError):
            f1_by_model[model_name] = 0.0

    points = []
    for model_name, tokens in tokens_by_model.items():
        batch_size = _parse_batch_size(model_name)
        emb = _parse_embedding_count(model_name)
        is_seq = _is_sequential(model_name)
        if is_seq:
            continue
        if batch_size is None or emb is None:
            continue
        series_label = f"max {emb} emb"
        points.append({
            "model_name": model_name,
            "batch_size": batch_size,
            "embeddings": emb,
            "is_sequential": is_seq,
            "series_label": series_label,
            "tokens": tokens,
            "f1_score": f1_by_model.get(model_name, 0.0),
            "api_calls": api_calls.get(model_name, 0),
            "total_time": total_times.get(model_name, 0.0),
        })
    return points


def _bar_tokens_line_f1_by_batch(points: list[dict], output_path: Path):
    if not points:
        return
    batch_sizes = sorted({p["batch_size"] for p in points if p["batch_size"] is not None})
    has_sequential = any(p["is_sequential"] for p in points)
    embeddings = sorted({p["embeddings"] for p in points})
    series_labels = {emb: f"max {emb} emb" for emb in embeddings}

    emb_to_idx = {emb: idx for idx, emb in enumerate(embeddings)}
    group_gap = 0.6
    bar_width = 0.6 / max(1, len(embeddings))

    x_positions = []
    bar_values = []
    line_values = []
    time_values = []

    colors = ["#8FB6E3", "#EFB985", "#9FD99A", "#BFA2D3", "#E99B9B"]
    hatches = ["//", "\\\\", "xx", "..", "++"]

    group_keys = (["Sequential"] if has_sequential else []) + batch_sizes
    for g_idx, group_key in enumerate(group_keys):
        base = g_idx * (len(embeddings) * bar_width + group_gap)
        for emb in embeddings:
            match = next(
                (
                    p for p in points
                    if ((p["batch_size"] == group_key and not p["is_sequential"]) if group_key != "Sequential" else p["is_sequential"])
                    and p["embeddings"] == emb
                ),
                None,
            )
            if not match:
                continue
            pos = base + emb_to_idx[emb] * bar_width
            x_positions.append(pos)
            bar_values.append(match["tokens"])
            line_values.append(match["f1_score"])
            time_values.append(match["total_time"])

    fig, ax1 = plt.subplots(figsize=(9, 5))
    for emb in embeddings:
        emb_positions = []
        emb_values = []
        for g_idx, group_key in enumerate(group_keys):
            match = next(
                (
                    p for p in points
                    if ((p["batch_size"] == group_key and not p["is_sequential"]) if group_key != "Sequential" else p["is_sequential"])
                    and p["embeddings"] == emb
                ),
                None,
            )
            base = g_idx * (len(embeddings) * bar_width + group_gap)
            pos = base + emb_to_idx[emb] * bar_width
            emb_positions.append(pos)
            emb_values.append(match["tokens"] if match else 0.0)
        color = colors[emb_to_idx[emb] % len(colors)]
        hatch = hatches[emb_to_idx[emb] % len(hatches)]
        ax1.bar(
            emb_positions,
            emb_values,
            width=bar_width,
            color=color,
            hatch=hatch,
            edgecolor="black",
            label=series_labels[emb],
        )
    ax1.set_ylabel("Usage (tokens)")

    ax2 = ax1.twinx()
    ax2.plot(x_positions, line_values, color="#F2A65A", marker="o", linewidth=1.5, label="F1 score")
    ax2.axhline(0.92, linestyle=":", color="red", linewidth=1)
    ax2.set_ylabel("F1 score")
    max_f1 = max(line_values) if line_values else 1.0
    ax2.set_ylim(0, min(1.05, max_f1 + 0.05))

    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("outward", 40))
    ax3.plot(x_positions, time_values, color="#6B7280", linestyle="--", marker="s", linewidth=1.2, label="Total time (s)")
    ax3.set_ylabel("Total time (s)")
    ax3.tick_params(axis="y", colors="#6B7280")
    max_time = max(time_values) if time_values else 0.0
    ax3.set_ylim(0, max_time * 1.15 if max_time else 1.0)

    group_centers = [
        g_idx * (len(embeddings) * bar_width + group_gap) + (len(embeddings) - 1) * bar_width / 2
        for g_idx in range(len(group_keys))
    ]
    x_labels = []
    for group_key in group_keys:
        if group_key == "Sequential":
            api_vals = sorted({p["api_calls"] for p in points if p["is_sequential"]})
            api_label = api_vals[0] if api_vals else 0
            x_labels.append(f"Sequential\n(api={api_label})")
        else:
            api_vals = sorted({p["api_calls"] for p in points if p["batch_size"] == group_key})
            api_label = api_vals[0] if api_vals else 0
            x_labels.append(f"{group_key}\n(api={api_label})")
    ax1.set_xticks(group_centers)
    ax1.set_xticklabels(x_labels)
    ax1.tick_params(axis="x", bottom=True, labelbottom=True, labelrotation=0, labelsize=9, pad=8)
    ax1.set_xlabel("Batch size (registers per batch)\n(number of LLM API calls)")
    ax1.set_title("Usage, F1 Score and Time by Batch Size (grouped by max embeddings)")
    max_tokens = max(bar_values) if bar_values else 0.0
    ax1.set_ylim(0, max_tokens * 1.15 if max_tokens else 1.0)

    formatter = mticker.FuncFormatter(lambda x, pos: f"{x / 1_000_000:.1f}".rstrip("0").rstrip("."))
    ax1.yaxis.set_major_formatter(formatter)
    ax1.set_ylabel("Usage (tokens, millions)")

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    handles3, labels3 = ax3.get_legend_handles_labels()
    legend_items = {}
    for handle, label in zip(handles1 + handles2 + handles3, labels1 + labels2 + labels3):
        if label not in legend_items:
            legend_items[label] = handle
    ax1.legend(
        list(legend_items.values()),
        list(legend_items.keys()),
        loc="center right",
        bbox_to_anchor=(1.0, 0.6),
        fontsize=7,
        handlelength=1.1,
        labelspacing=0.2,
        borderpad=0.2,
    )

    fig.subplots_adjust(bottom=0.28, right=0.82)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    pdf_path = output_path.with_suffix(".pdf")
    fig.savefig(pdf_path)


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
    parser.add_argument(
        "--usage-field",
        default="total_tokens",
        help="Field from summary_usage.csv for batch size plot",
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
        experiment_dir / "plot_time_vs_tokens_f1_filtered.png",
        args.min_f1,
    )
    _scatter_f1_vs_tokens(
        filtered,
        experiment_dir / "plot_f1_vs_tokens_time_filtered.png",
        args.min_f1,
    )
    _bar_time_breakdown(
        filtered,
        experiment_dir / "plot_time_breakdown_bars.png",
        args.min_f1,
        args.max_time,
    )
    _bar_token_breakdown(
        experiment_dir,
        filtered,
        experiment_dir / "plot_token_breakdown_bars.png",
        args.min_f1,
        args.max_time,
    )
    batch_points = _build_batch_usage_points(experiment_dir, args.usage_field)
    if batch_points:
        _scatter_batch_size_vs_usage(
            batch_points,
            experiment_dir / "plot_batch_size_vs_usage_f1.png",
            args.usage_field,
        )
    batch_emb_points = _build_batch_embedding_points(experiment_dir)
    if batch_emb_points:
        _bar_tokens_line_f1_by_batch(
            batch_emb_points,
            experiment_dir / "plot_batch_size_embeddings_tokens_f1.png",
        )
    print(f"Saved plots to {experiment_dir}")


if __name__ == "__main__":
    main()
