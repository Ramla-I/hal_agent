#!/usr/bin/env python3
"""
Unified Preprocessing Pipeline for Datasheet Chunking and Vector Store Creation.

This script consolidates the preprocessing workflow into a single command:
1. Chunk PDF into individual text/markdown files
2. Enrich chunks with metadata (register expansion, section hierarchy, etc.)
3. Optionally augment chunks with embedded metadata headers
4. Upload to OpenAI vector store with metadata attributes
5. Save chunk index CSV for contiguous chunk expansion during retrieval

Usage:
    # Basic usage - chunk, enrich, and upload
    python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041

    # With custom output directory
    python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
        --output-dir devices/stm/rm0041/chunks

    # With metadata embedding and markdown format
    python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
        --embed-metadata --format markdown

    # Skip upload (for testing)
    python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
        --skip-upload

    # Dry run - show what would be done
    python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
        --dry-run

Output:
    {output_dir}/
    ├── text/ or md/           # Chunk files
    │   ├── {name}_p001_c01.txt
    │   ├── ...
    │   ├── metadata/          # Enriched metadata JSON
    │   │   ├── {chunk_id}_metadata.json
    │   │   └── all_metadata.json
    │   ├── upload_summary.csv # Chunk index for retrieval expansion
    │   └── {name}_chunks_metadata.csv
    └── vector_store_info.json # Vector store ID and config
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.utils import setup_logger

logger = setup_logger(__name__)


def run_chunking(
    pdf_path: str,
    output_dir: str,
    datasheet_name: str,
    max_tokens: int,
    overlap_tokens: int,
    format: str
) -> list:
    """Run the PDF chunking step."""
    from preprocessing.chunk_pdf_to_files import extract_and_chunk_pdf

    logger.info(f"Step 1: Chunking PDF ({format} format)")
    logger.info(f"  Input: {pdf_path}")
    logger.info(f"  Output: {output_dir}")
    logger.info(f"  Max tokens: {max_tokens}, Overlap: {overlap_tokens}")

    chunk_metadata = extract_and_chunk_pdf(
        pdf_path,
        output_dir,
        datasheet_name,
        max_tokens,
        overlap_tokens,
        format
    )

    logger.info(f"  Created {len(chunk_metadata)} chunks")
    return chunk_metadata


def run_enrichment(
    chunks_dir: str,
    output_dir: str,
    file_extension: str,
    use_llm: bool = False
) -> dict:
    """Run the metadata enrichment step."""
    from preprocessing.enrich_chunk_metadata import enrich_chunk_directory, generate_metadata_summary

    logger.info("Step 2: Enriching chunk metadata")
    logger.info(f"  Chunks: {chunks_dir}")
    logger.info(f"  Output: {output_dir}")

    chunks_path = Path(chunks_dir)
    output_path = Path(output_dir)

    metadata_dict = enrich_chunk_directory(
        chunks_path,
        output_path,
        use_llm=use_llm,
        file_extension=file_extension
    )

    summary = generate_metadata_summary(metadata_dict)
    logger.info(f"  Enriched {len(metadata_dict)} chunks")
    logger.info(f"  Unique registers found: {summary.get('unique_registers', 0)}")

    return metadata_dict


def run_augmentation(
    chunks_dir: str,
    metadata_dir: str,
    output_dir: str,
    file_extension: str
) -> int:
    """Run the metadata augmentation step (embed metadata in chunks)."""
    from preprocessing.augment_chunks_with_metadata import augment_chunk_directory

    logger.info("Step 3: Augmenting chunks with embedded metadata")
    logger.info(f"  Chunks: {chunks_dir}")
    logger.info(f"  Metadata: {metadata_dir}")
    logger.info(f"  Output: {output_dir}")

    chunks_path = Path(chunks_dir)
    metadata_path = Path(metadata_dir)
    output_path = Path(output_dir)

    processed = augment_chunk_directory(
        chunks_path,
        metadata_path,
        output_path,
        file_extension=file_extension
    )

    logger.info(f"  Augmented {processed} chunks")
    return processed


def run_upload(
    chunks_dir: str,
    metadata_dir: str,
    vector_store_name: str,
    datasheet_name: str,
    chunking_strategy: str,
    max_chunk_tokens: int,
    chunk_overlap_tokens: int
) -> tuple:
    """Run the vector store upload step."""
    from preprocessing.upload_enriched_chunks import (
        create_vector_store_with_enriched_chunks,
        save_upload_summary
    )
    from openai import OpenAI

    logger.info("Step 4: Uploading to OpenAI vector store")
    logger.info(f"  Chunks: {chunks_dir}")
    logger.info(f"  Vector store name: {vector_store_name}")

    client = OpenAI()

    vector_store_id, file_infos = create_vector_store_with_enriched_chunks(
        client,
        chunks_dir,
        metadata_dir,
        vector_store_name,
        datasheet_name,
        chunking_strategy,
        max_chunk_tokens,
        chunk_overlap_tokens
    )

    # Save upload summary
    summary_path = os.path.join(chunks_dir, "upload_summary.csv")
    save_upload_summary(vector_store_id, file_infos, summary_path)

    logger.info(f"  Vector store ID: {vector_store_id}")
    logger.info(f"  Uploaded {len(file_infos)} files")
    logger.info(f"  Upload summary: {summary_path}")

    return vector_store_id, file_infos, summary_path


def save_vector_store_info(
    output_dir: str,
    vector_store_id: str,
    vector_store_name: str,
    chunk_count: int,
    chunk_index_path: str,
    format: str,
    metadata_enriched: bool,
    embed_metadata: bool
):
    """Save vector store info to JSON file."""
    info = {
        "vector_store_id": vector_store_id,
        "vector_store_name": vector_store_name,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "chunk_count": chunk_count,
        "chunk_index_path": chunk_index_path,
        "format": format,
        "metadata_enriched": metadata_enriched,
        "metadata_embedded": embed_metadata,
    }

    info_path = os.path.join(output_dir, "vector_store_info.json")
    with open(info_path, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2)

    logger.info(f"Vector store info saved to: {info_path}")
    return info_path


def main():
    parser = argparse.ArgumentParser(
        description="Unified preprocessing pipeline for datasheet chunking and vector store creation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041

    # With markdown format and embedded metadata
    python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \\
        --format markdown --embed-metadata

    # Custom output directory
    python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \\
        --output-dir devices/stm/rm0041/chunks

    # Skip upload for testing
    python preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \\
        --skip-upload
        """
    )

    # Required arguments
    parser.add_argument(
        "pdf_path",
        help="Path to the PDF datasheet"
    )
    parser.add_argument(
        "datasheet_name",
        help="Short name for the datasheet (e.g., 'rm0041')"
    )

    # Output options
    parser.add_argument(
        "--output-dir",
        help="Base output directory (default: same directory as PDF)"
    )
    parser.add_argument(
        "--vector-store-name",
        help="Name for the vector store (default: {datasheet_name}_enriched)"
    )

    # Chunking options
    parser.add_argument(
        "--format",
        choices=["text", "markdown"],
        default="text",
        help="Extraction format (default: text)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=800,
        help="Maximum tokens per chunk (default: 800)"
    )
    parser.add_argument(
        "--overlap-tokens",
        type=int,
        default=100,
        help="Token overlap between chunks (default: 100)"
    )

    # Enrichment options
    parser.add_argument(
        "--embed-metadata",
        action="store_true",
        help="Embed metadata headers in chunk content (creates augmented directory)"
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM for enhanced metadata extraction (slower, more accurate)"
    )

    # Upload options
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip vector store upload (for testing)"
    )
    parser.add_argument(
        "--chunking-strategy",
        choices=["auto", "static"],
        default="static",
        help="OpenAI's chunking strategy (default: static)"
    )
    parser.add_argument(
        "--openai-max-tokens",
        type=int,
        default=1200,
        help="Max tokens per chunk for OpenAI (default: 1200)"
    )
    parser.add_argument(
        "--openai-overlap-tokens",
        type=int,
        default=0,
        help="Overlap tokens for OpenAI (default: 0)"
    )

    # Control options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found: {args.pdf_path}")
        return 1

    # Determine output directories
    pdf_dir = os.path.dirname(os.path.abspath(args.pdf_path))
    base_output_dir = args.output_dir or os.path.join(pdf_dir, "chunks")

    format_subdir = "md" if args.format == "markdown" else "text"
    chunks_dir = os.path.join(base_output_dir, format_subdir)
    metadata_dir = os.path.join(chunks_dir, "metadata")
    augmented_dir = os.path.join(base_output_dir, f"{format_subdir}_augmented") if args.embed_metadata else None

    file_extension = ".md" if args.format == "markdown" else ".txt"
    vector_store_name = args.vector_store_name or f"{args.datasheet_name}_enriched"

    # Print configuration
    print("\n" + "=" * 70)
    print("PREPROCESSING PIPELINE")
    print("=" * 70)
    print(f"\nInput PDF: {args.pdf_path}")
    print(f"Datasheet name: {args.datasheet_name}")
    print(f"Output directory: {base_output_dir}")
    print(f"Format: {args.format}")
    print(f"Chunk tokens: {args.max_tokens} (overlap: {args.overlap_tokens})")
    print(f"Embed metadata: {args.embed_metadata}")
    print(f"Skip upload: {args.skip_upload}")
    if not args.skip_upload:
        print(f"Vector store name: {vector_store_name}")
    print("=" * 70)

    if args.dry_run:
        print("\n[DRY RUN] Would execute the following steps:")
        print(f"  1. Chunk PDF to {chunks_dir}")
        print(f"  2. Enrich metadata to {metadata_dir}")
        if args.embed_metadata:
            print(f"  3. Augment chunks to {augmented_dir}")
        if not args.skip_upload:
            print(f"  {3 if not args.embed_metadata else 4}. Upload to vector store: {vector_store_name}")
        return 0

    # Step 1: Chunk PDF
    print("\n" + "-" * 70)
    chunk_metadata = run_chunking(
        args.pdf_path,
        chunks_dir,
        args.datasheet_name,
        args.max_tokens,
        args.overlap_tokens,
        args.format
    )

    # Step 2: Enrich metadata
    print("\n" + "-" * 70)
    enriched_metadata = run_enrichment(
        chunks_dir,
        metadata_dir,
        file_extension,
        use_llm=args.use_llm
    )

    # Step 3: Augment chunks (optional)
    upload_chunks_dir = chunks_dir
    if args.embed_metadata:
        print("\n" + "-" * 70)
        run_augmentation(
            chunks_dir,
            metadata_dir,
            augmented_dir,
            file_extension
        )
        upload_chunks_dir = augmented_dir

    # Step 4: Upload to vector store
    vector_store_id = None
    chunk_index_path = ""

    if not args.skip_upload:
        print("\n" + "-" * 70)
        vector_store_id, file_infos, upload_summary_path = run_upload(
            upload_chunks_dir,
            metadata_dir,
            vector_store_name,
            args.datasheet_name,
            args.chunking_strategy,
            args.openai_max_tokens,
            args.openai_overlap_tokens
        )
        chunk_index_path = upload_summary_path

        # Save vector store info
        print("\n" + "-" * 70)
        save_vector_store_info(
            base_output_dir,
            vector_store_id,
            vector_store_name,
            len(file_infos),
            chunk_index_path,
            args.format,
            metadata_enriched=True,
            embed_metadata=args.embed_metadata
        )

    # Summary
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"\nChunks created: {len(chunk_metadata)}")
    print(f"Metadata enriched: {len(enriched_metadata)}")
    if args.embed_metadata:
        print(f"Augmented chunks: {augmented_dir}")
    if vector_store_id:
        print(f"\nVector Store ID: {vector_store_id}")
        print(f"Chunk index: {chunk_index_path}")
        print(f"\nAdd to config.py:")
        print(f'  vs_id = "{vector_store_id}"')
        print(f'  chunk_index_path = "{chunk_index_path}"')
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
