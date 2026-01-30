"""
Create a bar chart of total tokens per peripheral.

Bars use `total_tokens_chunks_800_400` (chunk_count * 800) from
`devices/stm/rm0041/peripheral_pages_mapping.csv`, and each bar is labeled
with the chunk count.

Example:
    python plots/plot_peripheral_chunk_tokens.py \
        --csv devices/stm/rm0041/peripheral_pages_mapping.csv \
        --output devices/stm/rm0041/peripheral_chunk_tokens.png
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def read_rows(csv_path: Path) -> list[dict]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot total tokens from chunk count per peripheral."
    )
    parser.add_argument(
        "--csv",
        default="devices/stm/rm0041/peripheral_pages_mapping.csv",
        help="Input mapping CSV",
    )
    parser.add_argument(
        "--output",
        default="devices/stm/rm0041/peripheral_chunk_tokens.png",
        help="Output PNG path",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    rows = read_rows(csv_path)

    names = []
    totals = []
    chunk_counts = []

    for row in rows:
        name = row.get("peripheral_name", "").strip()
        total_tokens = row.get("total_tokens_chunks_800_400", "").strip()
        chunk_count = row.get("chunk_count_800_400", "").strip()
        if not name or not total_tokens or not chunk_count:
            continue
        names.append(name)
        totals.append(int(total_tokens))
        chunk_counts.append(int(chunk_count))

    if not names:
        raise ValueError("No rows with total_tokens_chunks_800_400 found.")

    fig, ax = plt.subplots(figsize=(max(10, len(names) * 0.6), 6))
    bars = ax.bar(names, totals, color="#4C78A8")

    ax.set_xlabel("Peripheral")
    ax.set_ylabel("Total tokens from chunk count")
    ax.set_title("Total tokens by peripheral (800 tokens per chunk)")
    ax.tick_params(axis="x", rotation=45, labelsize=9)
    ax.margins(x=0.01)

    total_tokens_all = sum(totals)
    ax.text(
        0.99,
        0.98,
        f"Total tokens: {total_tokens_all:,}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=30,
        fontweight="bold",
    )

    for bar, count in zip(bars, chunk_counts):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            str(count),
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    fig.tight_layout()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    print(f"Saved chart to: {output_path}")


if __name__ == "__main__":
    main()
