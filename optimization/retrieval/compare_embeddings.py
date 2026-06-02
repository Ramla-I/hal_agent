#!/usr/bin/env python3
"""
Compare two embedding_ids.jsonl files side by side.

Shows which chunks were retrieved for each (peripheral, register) query,
highlighting differences between the two runs.

Usage:
    python3 optimization/retrieval/compare_embeddings.py FILE_A FILE_B --top 2
    python3 optimization/retrieval/compare_embeddings.py FILE_A FILE_B --top 1 --only-diffs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_embeddings(path: Path) -> Dict[Tuple[str, str], List[dict]]:
    """Load embedding_ids.jsonl into {(peripheral, register): [embedding_ids...]}."""
    result: Dict[Tuple[str, str], List[dict]] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            key = (rec["peripheral"], rec["register"])
            # If duplicate keys, keep the last one (matches behavior in sample data)
            result[key] = rec["embedding_ids"]
    return result


def get_filename(entry: dict) -> str:
    """Extract the filename from an embedding entry, handling both schemas."""
    if "filename" in entry:
        return entry["filename"]
    if "source" in entry:
        return Path(entry["source"]).name
    raise KeyError(f"Entry has neither 'filename' nor 'source': {entry}")


def short_filename(filename: str) -> str:
    """Strip .txt extension for display."""
    return filename.removesuffix(".txt")


def format_entry(e: dict) -> str:
    """Format a single embedding entry as 'filename (score)'."""
    return f"{short_filename(get_filename(e))} ({e['score']:.3f})"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two embedding_ids.jsonl files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 optimization/retrieval/compare_embeddings.py \\\n"
            "    experiments/afio_peripheral/md_emb2_pages0/info/embedding_ids.jsonl \\\n"
            "    experiments/afio_peripheral/md_enriched_emb2_pages0/info/embedding_ids.jsonl \\\n"
            "    --top 2\n"
        ),
    )
    parser.add_argument("file_a", type=Path, help="First embedding_ids.jsonl")
    parser.add_argument("file_b", type=Path, help="Second embedding_ids.jsonl")
    parser.add_argument(
        "--top", type=int, default=1,
        help="Compare top N results (default: 1)",
    )
    parser.add_argument(
        "--only-diffs", action="store_true",
        help="Only show registers where the top-N chunks differ",
    )
    args = parser.parse_args()

    data_a = load_embeddings(args.file_a)
    data_b = load_embeddings(args.file_b)
    top_k = args.top

    all_keys = sorted(set(data_a.keys()) | set(data_b.keys()))

    # Derive short labels from paths
    label_a = args.file_a.parent.parent.name if args.file_a.parent.name == "info" else args.file_a.parent.name
    label_b = args.file_b.parent.parent.name if args.file_b.parent.name == "info" else args.file_b.parent.name

    # Stats
    same_count = 0
    diff_count = 0
    only_a_count = 0
    only_b_count = 0

    lines: List[str] = []

    for periph, reg in all_keys:
        embs_a = data_a.get((periph, reg))
        embs_b = data_b.get((periph, reg))

        if embs_a is None:
            only_b_count += 1
            if not args.only_diffs:
                lines.append(f"  {periph}/{reg}: only in B")
            continue
        if embs_b is None:
            only_a_count += 1
            if not args.only_diffs:
                lines.append(f"  {periph}/{reg}: only in A")
            continue

        top_a = embs_a[:top_k]
        top_b = embs_b[:top_k]
        fnames_a = [get_filename(e) for e in top_a]
        fnames_b = [get_filename(e) for e in top_b]

        if fnames_a == fnames_b:
            same_count += 1
            if not args.only_diffs:
                chunks_str = ", ".join(format_entry(e) for e in top_a)
                lines.append(f"  {periph}/{reg}: SAME  [{chunks_str}]")
        else:
            diff_count += 1
            set_a = set(fnames_a)
            set_b = set(fnames_b)
            overlap = set_a & set_b
            a_str = ", ".join(format_entry(e) for e in top_a)
            b_str = ", ".join(format_entry(e) for e in top_b)
            overlap_pct = len(overlap) / max(len(set_a | set_b), 1) * 100
            lines.append(f"  {periph}/{reg}: DIFF  (overlap: {len(overlap)}/{top_k} = {overlap_pct:.0f}%)")
            lines.append(f"    A: {a_str}")
            lines.append(f"    B: {b_str}")
            # Show what's unique to each side
            unique_a = [short_filename(f) for f in fnames_a if f not in set_b]
            unique_b = [short_filename(f) for f in fnames_b if f not in set_a]
            if unique_a:
                lines.append(f"    only A: {', '.join(unique_a)}")
            if unique_b:
                lines.append(f"    only B: {', '.join(unique_b)}")

    # Print header
    total = same_count + diff_count + only_a_count + only_b_count
    print(f"Comparing top-{top_k} embeddings")
    print(f"  A: {label_a}  ({args.file_a})")
    print(f"  B: {label_b}  ({args.file_b})")
    print()
    print(f"Registers: {total} total")
    print(f"  same:    {same_count:3d}  ({same_count / total * 100:.0f}%)" if total else "  same:    0")
    print(f"  diff:    {diff_count:3d}  ({diff_count / total * 100:.0f}%)" if total else "  diff:    0")
    if only_a_count:
        print(f"  only A:  {only_a_count:3d}")
    if only_b_count:
        print(f"  only B:  {only_b_count:3d}")
    print()

    # Print per-register details
    if lines:
        print("Per-register breakdown:")
        for line in lines:
            print(line)


if __name__ == "__main__":
    main()
