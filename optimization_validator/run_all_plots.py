"""
Run all plotting scripts in one go.

Example:
    python optimization_validator/run_all_plots.py \
      --experiment-dir optimization_validator/stm-rm0041/experiments/batch_sizes_embeddings \
      --min-f1 0.92 \
      --max-time 1000
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from plot_experiment_scatter import build_scatter_data, plot_scatter
from plot_experiment_tradeoffs import _build_points, _scatter_time_vs_tokens, _scatter_f1_vs_tokens, _build_batch_usage_points, _scatter_batch_size_vs_usage, _build_batch_embedding_points, _bar_tokens_line_f1_by_batch
from plot_file_search_tokens_vs_chunks import plot_file_search_tokens_vs_chunks


def main():
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Generate all optimization plots.")
    parser.add_argument(
        "--experiment-dir",
        default="stm-rm0041/experiments/batch_sizes_embeddings",
        help="Path to experiment directory containing summary CSVs",
    )
    parser.add_argument(
        "--min-f1",
        type=float,
        default=0.92,
        help="Minimum F1 score to include in filtered plots",
    )
    parser.add_argument(
        "--max-time",
        type=float,
        default=1000.0,
        help="Maximum total time (s) to include in filtered plots",
    )
    args = parser.parse_args()

    experiment_dir = Path(args.experiment_dir)
    if not experiment_dir.is_absolute():
        experiment_dir = (script_dir / experiment_dir).resolve()

    # Plot 1: Time vs F1 (all points)
    scatter_points = build_scatter_data(experiment_dir)
    plot_scatter(scatter_points, experiment_dir / "plot_time_vs_f1_scatter.png")

    # Plot 2 & 3: Filtered tradeoff plots
    points = _build_points(experiment_dir)
    filtered = [
        p for p in points
        if p["f1_score"] >= args.min_f1 and p["total_time"] <= args.max_time
    ]
    if not filtered:
        raise SystemExit("No points found after F1/time filters.")

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

    # Plot 4: Batch size vs usage (colored by F1)
    batch_points = _build_batch_usage_points(experiment_dir, "total_tokens")
    if batch_points:
        _scatter_batch_size_vs_usage(
            batch_points,
            experiment_dir / "plot_batch_size_vs_usage_f1.png",
            "total_tokens",
        )
    batch_emb_points = _build_batch_embedding_points(experiment_dir)
    if batch_emb_points:
        _bar_tokens_line_f1_by_batch(
            batch_emb_points,
            experiment_dir / "plot_batch_size_embeddings_tokens_f1.png",
        )

    # Plot 5: File search tokens vs total chunk tokens
    plot_file_search_tokens_vs_chunks(
        experiment_dir=experiment_dir,
        test_set_path=script_dir / "stm-rm0041/test_set_rm0041.csv",
        peripheral_mapping_path=script_dir.parent / "devices/stm/rm0041/peripheral_pages_mapping.csv",
        token_column="total_tokens_chunks_800_400",
        min_f1=args.min_f1,
        max_time=args.max_time,
        output_path=experiment_dir / "plot_file_search_tokens_vs_chunks.png",
    )

    print(f"Saved plots to {experiment_dir}")


if __name__ == "__main__":
    main()
