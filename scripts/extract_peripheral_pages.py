"""
Extract peripheral page ranges from a PDF, convert to markdown, and
update a mapping CSV with token and chunk counts.

Usage:
    python scripts/extract_peripheral_pages.py \
        --pdf-path devices/stm/rm0041/rm0041.pdf \
        --mapping-csv devices/stm/rm0041/peripheral_pages_mapping.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sys
from pathlib import Path

import pymupdf  # PyMuPDF
import pymupdf4llm  # Markdown conversion
import tiktoken

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TIKTOKEN_ENCODING


def sanitize_filename(name: str) -> str:
    cleaned = name.strip().lower()
    cleaned = cleaned.replace("/", "_")
    cleaned = re.sub(r"[^a-z0-9._-]+", "_", cleaned)
    return cleaned.strip("_") or "peripheral"


def count_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding(TIKTOKEN_ENCODING)
    return len(encoding.encode(text))


def count_chunks(total_tokens: int, max_tokens: int, overlap_tokens: int) -> int:
    if total_tokens <= 0:
        return 0
    if total_tokens <= max_tokens:
        return 1
    step = max_tokens - overlap_tokens
    if step <= 0:
        raise ValueError("overlap_tokens must be smaller than max_tokens")
    return 1 + math.ceil((total_tokens - max_tokens) / step)


def read_mapping(mapping_csv: str) -> list[dict]:
    rows = []
    with open(mapping_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("peripheral_name"):
                continue
            rows.append(row)
    return rows


def write_mapping(mapping_csv: str, rows: list[dict]) -> None:
    if not rows:
        return
    base_fields = [
        "peripheral_name",
        "start_page",
        "end_page",
        "total_tokens",
        "chunk_count_800_400",
        "total_tokens_chunks_800_400",
    ]
    extra_fields = []
    for row in rows:
        for key in row.keys():
            if key not in base_fields and key not in extra_fields:
                extra_fields.append(key)
    fieldnames = base_fields + extra_fields
    with open(mapping_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def extract_markdown_pages(pdf_path: str, start_page: int, end_page: int) -> str:
    # Pages are 1-indexed in the CSV; pymupdf is 0-indexed.
    page_indices = list(range(start_page - 1, end_page))
    page_md = pymupdf4llm.to_markdown(pdf_path, pages=page_indices)
    return page_md.strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract peripheral page ranges from a PDF to markdown and update token counts."
    )
    parser.add_argument(
        "--pdf-path",
        default="devices/stm/rm0041/rm0041.pdf",
        help="Path to the rm0041 PDF",
    )
    parser.add_argument(
        "--mapping-csv",
        default="devices/stm/rm0041/peripheral_pages_mapping.csv",
        help="CSV mapping file with peripheral_name,start_page,end_page",
    )
    parser.add_argument(
        "--output-dir",
        default="devices/stm/rm0041/peripheral_pages_md",
        help="Directory to write per-peripheral markdown files",
    )
    parser.add_argument(
        "--peripheral-name",
        help="Process only the row matching this peripheral name",
    )
    parser.add_argument(
        "--only-first",
        action="store_true",
        help="Process only the first row (after filtering, if any)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=800,
        help="Chunk size for chunk count",
    )
    parser.add_argument(
        "--overlap-tokens",
        type=int,
        default=400,
        help="Chunk overlap for chunk count",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute rows even if totals already exist",
    )
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        raise FileNotFoundError(f"PDF not found: {args.pdf_path}")

    os.makedirs(args.output_dir, exist_ok=True)

    doc = pymupdf.open(args.pdf_path)
    total_pages = len(doc)
    doc.close()

    rows = read_mapping(args.mapping_csv)
    target_rows = rows
    if args.peripheral_name:
        target_rows = [
            row
            for row in rows
            if row["peripheral_name"].strip().lower()
            == args.peripheral_name.strip().lower()
        ]
    if args.only_first:
        target_rows = target_rows[:1]

    for row in target_rows:
        if (
            not args.force
            and row.get("total_tokens")
            and row.get("chunk_count_800_400")
        ):
            continue
        start_page = int(row["start_page"])
        end_page = int(row["end_page"])
        if start_page < 1 or end_page > total_pages or start_page > end_page:
            raise ValueError(
                f"Invalid page range {start_page}-{end_page} for {row['peripheral_name']}"
            )

        md_text = extract_markdown_pages(args.pdf_path, start_page, end_page)
        token_count = count_tokens(md_text)
        chunk_count = count_chunks(token_count, args.max_tokens, args.overlap_tokens)

        row["total_tokens"] = str(token_count)
        row["chunk_count_800_400"] = str(chunk_count)
        row["total_tokens_chunks_800_400"] = str(chunk_count * args.max_tokens)

        filename = f"{sanitize_filename(row['peripheral_name'])}.md"
        output_path = Path(args.output_dir) / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_text)

    write_mapping(args.mapping_csv, rows)
    print(f"Updated mapping CSV: {args.mapping_csv}")
    print(f"Markdown files written to: {args.output_dir}")


if __name__ == "__main__":
    main()
