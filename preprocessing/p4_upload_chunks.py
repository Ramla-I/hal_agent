#!/usr/bin/env python3
"""
Upload pre-chunked datasheet files to an OpenAI vector store.

This is the unified CLI replacement for:
- `preprocessing/upload_chunks_to_vector_store.py` (basic attributes)
- `preprocessing/upload_enriched_chunks.py` (enriched metadata attributes)

If `--metadata-dir` is provided (or defaults to chunks_dir), the uploader uses
the combined `metadata.json` file to attach richer OpenAI file attributes.
Otherwise, it uploads with basic attributes sourced from `chunks_index.csv`
when present.
"""

from __future__ import annotations

import argparse
import os
import sys

from openai import OpenAI

from preprocessing.vector_store_uploader import (
    create_vector_store_with_chunks,
    create_vector_store_with_enriched_chunks,
    save_upload_summary,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload chunk files to an OpenAI vector store")

    parser.add_argument("chunks_dir", help="Directory containing chunk files")
    parser.add_argument("vector_store_name", help="Name for the vector store")
    parser.add_argument("datasheet_name", help="Datasheet identifier (e.g., 'rm0041')")

    parser.add_argument(
        "--metadata-dir",
        default=None,
        help="Directory containing enriched metadata JSON files. If provided, enables enriched upload.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to save chunk index CSV (default: <chunks_dir>/chunks_index.csv)",
    )
    parser.add_argument(
        "--chunking-strategy",
        choices=["auto", "static"],
        default="static",
        help="OpenAI chunking strategy (default: static)",
    )
    parser.add_argument(
        "--max-chunk-tokens",
        type=int,
        default=1200,
        help="Max tokens per chunk for OpenAI (100-4096). Use >= your chunk size (default: 1200)",
    )
    parser.add_argument(
        "--chunk-overlap-tokens",
        type=int,
        default=0,
        help="Overlap tokens for OpenAI chunking (default: 0)",
    )
    parser.add_argument(
        "--file-extension",
        default=".txt",
        help="Chunk file extension (default: .txt)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not os.path.exists(args.chunks_dir):
        print(f"Error: Chunks directory not found: {args.chunks_dir}")
        return 1

    # Validate chunking params for static mode (mirror prior scripts)
    if args.chunking_strategy == "static":
        if args.max_chunk_tokens and (args.max_chunk_tokens < 100 or args.max_chunk_tokens > 4096):
            print("Error: --max-chunk-tokens must be between 100 and 4096")
            return 1
        if args.chunk_overlap_tokens and args.max_chunk_tokens:
            if args.chunk_overlap_tokens > args.max_chunk_tokens / 2:
                print("Error: --chunk-overlap-tokens cannot exceed max-chunk-tokens / 2")
                return 1

    client = OpenAI()

    # Metadata is now stored in chunks_dir as metadata.json (simplified structure)
    metadata_dir = args.metadata_dir or args.chunks_dir
    metadata_file = os.path.join(metadata_dir, "metadata.json")
    enriched = os.path.exists(metadata_file)

    if args.metadata_dir and not enriched:
        print(f"Error: metadata.json not found in {metadata_dir}")
        print("Run `preprocessing/p2_enrich_chunk_metadata.py` first, or omit --metadata-dir for basic upload.")
        return 1

    if enriched:
        vector_store_id, file_infos = create_vector_store_with_enriched_chunks(
            client,
            args.chunks_dir,
            metadata_dir,
            args.vector_store_name,
            args.datasheet_name,
            args.chunking_strategy,
            args.max_chunk_tokens,
            args.chunk_overlap_tokens,
            file_extension=args.file_extension,
        )
    else:
        vector_store_id, file_infos = create_vector_store_with_chunks(
            client,
            args.chunks_dir,
            args.vector_store_name,
            args.datasheet_name,
            args.chunking_strategy,
            args.max_chunk_tokens,
            args.chunk_overlap_tokens,
            file_extension=args.file_extension,
        )

    # Always use chunks_index.csv as the output filename
    output_path = args.output or os.path.join(args.chunks_dir, "chunks_index.csv")

    save_upload_summary(vector_store_id, file_infos, output_path)
    print(f"\nUpload summary saved to: {output_path}")

    print(f"\n{'='*60}")
    print(f"Vector Store ID: {vector_store_id}")
    print(f"Total Files: {len(file_infos)}")
    print(f"Attributes: {'enriched' if enriched else 'basic'}")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

