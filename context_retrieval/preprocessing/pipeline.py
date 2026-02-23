#!/usr/bin/env python3
"""
Unified Preprocessing Pipeline for Datasheet Chunking and Vector Store Creation.

This script consolidates the preprocessing workflow into a single command:
1. Chunk PDF into individual text/markdown files
2. Enrich chunks with metadata (register expansion, section hierarchy, etc.)
3. Optionally augment chunks with embedded metadata headers
4. Upload to OpenAI vector store with metadata attributes
5. Save chunk index CSV for contiguous chunk expansion during retrieval
6. Update device's vector_stores.json configuration

Usage:
    # Basic usage - chunk, enrich, and upload to OpenAI
    python context_retrieval/preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041

    # Upload to local ChromaDB instead of OpenAI
    python context_retrieval/preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
        --backend local --format markdown --embed-metadata

    # With custom output directory
    python context_retrieval/preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
        --output-dir chunked_datasheets/stm/rm0041/chunks

    # With metadata embedding and markdown format
    python context_retrieval/preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
        --embed-metadata --format markdown

    # Skip upload (for testing)
    python context_retrieval/preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
        --backend none

    # Dry run - show what would be done
    python context_retrieval/preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \
        --dry-run

Output:
    Chunks (in --output-dir, defaults to {pdf_dir}/chunks/):
        {output_dir}/
        ├── text/ or md/           # Chunk files
        │   ├── {name}_p001_c01.txt
        │   ├── ...
        │   ├── chunks_index.csv   # Chunk index (basic metadata + file_ids after upload)
        │   ├── metadata.json      # Enriched metadata for all chunks
        │   └── metadata_summary.json  # Summary statistics
        └── vector_store_info.json # Vector store ID and config (legacy)

    Config (in --device-dir, defaults to PDF's directory):
        {device_dir}/vector_stores.json  # Canonical vector store registry

    IMPORTANT: vector_stores.json belongs in the device directory (e.g., devices/stm/rm0041/),
    NOT in the chunked_datasheets directory. Use --device-dir to specify explicitly if needed.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.utils import setup_logger
from utils.vector_store_config import (
    load_vector_stores,
    update_vector_store,
    VectorStoreInfo,
    DeviceVectorStores
)

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
    from context_retrieval.preprocessing.p1_chunk_pdf_to_files import extract_and_chunk_pdf

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
    from context_retrieval.preprocessing.p2_enrich_chunk_metadata import enrich_chunk_directory, generate_metadata_summary

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
    file_extension: str,
    include_fields: list[str] | None = None,
) -> int:
    """Run the metadata augmentation step (embed metadata in chunks).

    Args:
        include_fields: which metadata fields to embed (see p3_augment_chunks_with_metadata.PRESETS).
    """
    from context_retrieval.preprocessing.p3_augment_chunks_with_metadata import augment_chunk_directory

    logger.info("Step 3: Augmenting chunks with embedded metadata")
    logger.info(f"  Chunks: {chunks_dir}")
    logger.info(f"  Metadata: {metadata_dir}")
    logger.info(f"  Output: {output_dir}")
    if include_fields:
        logger.info(f"  Fields: {include_fields}")

    chunks_path = Path(chunks_dir)
    metadata_path = Path(metadata_dir)
    output_path = Path(output_dir)

    processed = augment_chunk_directory(
        chunks_path,
        metadata_path,
        output_path,
        file_extension=file_extension,
        include_fields=include_fields,
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
    from context_retrieval.preprocessing.vector_store_uploader import (
        create_vector_store_with_enriched_chunks,
        save_upload_summary,
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

    # Save chunk index (includes file_ids from upload)
    summary_path = os.path.join(chunks_dir, "chunks_index.csv")
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
    """Save vector store info to JSON file (legacy per-run file)."""
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


def update_device_vector_stores(
    device_dir: str,
    store_name: str,
    vector_store_id: str,
    description: str,
    chunk_count: int,
    chunk_index_path: str,
    local_path: str = None
) -> str:
    """
    Update the device's vector_stores.json with new vector store info.

    Args:
        device_dir: Path to device directory (e.g., 'devices/stm/rm0041')
        store_name: Name for this vector store entry (e.g., 'md_enriched')
        vector_store_id: OpenAI vector store ID
        description: Human-readable description
        chunk_count: Number of chunks uploaded
        chunk_index_path: Relative path to chunks_index.csv
        local_path: Relative path to local chunk files

    Returns:
        Path to updated vector_stores.json
    """
    config_path = os.path.join(device_dir, "vector_stores.json")

    # Create default config if it doesn't exist
    if not os.path.exists(config_path):
        # Extract device info from path
        device_name = os.path.basename(device_dir)
        manufacturer = os.path.basename(os.path.dirname(device_dir))

        initial_config = {
            "device_name": device_name,
            "manufacturer": manufacturer,
            "vector_stores": {},
            "default": store_name
        }
        with open(config_path, 'w') as f:
            json.dump(initial_config, f, indent=2)
        logger.info(f"Created new vector_stores.json at {config_path}")

    # Update the config with new vector store
    config = update_vector_store(
        device_dir=device_dir,
        name=store_name,
        vs_id=vector_store_id,
        description=description,
        file_count=chunk_count,
        chunk_index_path=chunk_index_path,
        created_at=datetime.utcnow().strftime("%Y-%m-%d")
    )

    # Also update local_path if provided
    if local_path and store_name in config.vector_stores:
        config.vector_stores[store_name].local_path = local_path
        from utils.vector_store_config import save_vector_stores
        save_vector_stores(device_dir, config)

    logger.info(f"Updated vector_stores.json: {store_name} -> {vector_store_id}")
    return config_path


def run_local_ingestion(
    chunks_dir: str,
    metadata_dir: str,
    device_name: str,
    device_dir: str,
    db_name: str = "",
    db_path: str = "",
    embedding_provider: str = "local",
    entry_name: str = "",
) -> int:
    """Ingest chunks into local ChromaDB using ingest_from_chunks_dir().

    Args:
        chunks_dir: Directory containing chunk .txt files (may be augmented dir)
        metadata_dir: Directory containing metadata.json (always the base chunks dir)
        device_name: Device identifier (e.g., "rm0041")
        device_dir: Device directory for vector_stores.json registration
        db_name: ChromaDB database name
        db_path: Override databases directory path
        embedding_provider: "local" (FastEmbed) or "openai"
        entry_name: Name for vector_stores.json entry

    Returns:
        0 on success, 1 on error
    """
    from context_retrieval.preprocessing.ingest_local_vector_db import ingest_from_chunks_dir

    logger.info("Step: Ingesting into local ChromaDB")
    logger.info(f"  Chunks: {chunks_dir}")
    logger.info(f"  Metadata: {metadata_dir}")
    logger.info(f"  DB name: {db_name}")
    logger.info(f"  Embedding: {embedding_provider}")

    # ingest_from_chunks_dir reads metadata.json from the chunks_dir argument.
    # If chunks are augmented (different dir), we need metadata.json in the
    # upload dir. Copy it there if missing.
    import shutil
    meta_src = os.path.join(metadata_dir, "metadata.json")
    meta_dst = os.path.join(chunks_dir, "metadata.json")
    if chunks_dir != metadata_dir and os.path.exists(meta_src) and not os.path.exists(meta_dst):
        shutil.copy2(meta_src, meta_dst)

    # Same for chunks_index.csv
    csv_src = os.path.join(metadata_dir, "chunks_index.csv")
    csv_dst = os.path.join(chunks_dir, "chunks_index.csv")
    if chunks_dir != metadata_dir and os.path.exists(csv_src) and not os.path.exists(csv_dst):
        shutil.copy2(csv_src, csv_dst)

    return ingest_from_chunks_dir(
        device_name=device_name,
        chunks_dir=chunks_dir,
        db_name=db_name,
        db_path=db_path,
        embedding_provider=embedding_provider,
        entry_name=entry_name,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Unified preprocessing pipeline for datasheet chunking and vector store creation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage (OpenAI backend)
    python context_retrieval/preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041

    # Local ChromaDB backend
    python context_retrieval/preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \\
        --backend local --format markdown --embed-metadata

    # With markdown format and embedded metadata
    python context_retrieval/preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \\
        --format markdown --embed-metadata

    # Skip upload for testing
    python context_retrieval/preprocessing/pipeline.py devices/stm/rm0041/rm0041.pdf rm0041 \\
        --backend none
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
        help="Base output directory for chunks (default: {pdf_dir}/chunks/). Use this for chunked_datasheets/."
    )
    parser.add_argument(
        "--device-dir",
        help="Device directory for vector_stores.json (default: same directory as PDF). Keep this in devices/."
    )
    parser.add_argument(
        "--store-name",
        help="Name for entry in vector_stores.json (e.g., 'md_enriched', 'text_chunks')"
    )
    parser.add_argument(
        "--vector-store-name",
        help="Display name for the OpenAI vector store (default: {datasheet_name}_{store_name})"
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
    parser.add_argument(
        "--augment-preset",
        choices=["default", "minimal", "registers_only", "full", "none"],
        default="default",
        help="Preset for which metadata fields to embed (default: default). Use --list-augment-fields to see details.",
    )
    parser.add_argument(
        "--augment-include",
        nargs="*",
        default=None,
        help="Additional metadata fields to include (on top of preset)",
    )
    parser.add_argument(
        "--augment-exclude",
        nargs="*",
        default=None,
        help="Metadata fields to exclude from preset",
    )
    parser.add_argument(
        "--list-augment-fields",
        action="store_true",
        help="List available augmentation fields and presets, then exit",
    )

    # Backend options
    parser.add_argument(
        "--backend",
        choices=["openai", "local", "none"],
        default="openai",
        help="Upload backend: openai (vector store API), local (ChromaDB), none (skip upload) (default: openai)"
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Equivalent to --backend none"
    )

    # OpenAI backend options
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

    # Local backend options
    parser.add_argument(
        "--db-name",
        default="",
        help="ChromaDB database name (default: {datasheet_name}_md_chunks)"
    )
    parser.add_argument(
        "--db-path",
        default="",
        help="Override ChromaDB databases directory path"
    )
    parser.add_argument(
        "--embedding-provider",
        choices=["local", "openai"],
        default="local",
        help="Embedding provider for local backend: local (FastEmbed, free) or openai (default: local)"
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

    # Handle --list-augment-fields
    if args.list_augment_fields:
        from context_retrieval.preprocessing.p3_augment_chunks_with_metadata import ALL_FIELDS, PRESETS
        print("Available augmentation fields:")
        for f in ALL_FIELDS:
            print(f"  - {f}")
        print("\nPresets:")
        for name, fields in PRESETS.items():
            print(f"  {name}: {', '.join(fields) if fields else '(empty)'}")
        return 0

    # Resolve backend: --skip-upload is equivalent to --backend none
    backend = args.backend
    if args.skip_upload:
        backend = "none"

    # Validate inputs
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found: {args.pdf_path}")
        return 1

    # Determine output directories
    pdf_dir = os.path.dirname(os.path.abspath(args.pdf_path))
    device_dir = args.device_dir or pdf_dir
    base_output_dir = args.output_dir or os.path.join(pdf_dir, "chunks")

    # NOTE: `chunk_pdf_to_files.py` currently always writes chunk files as `.txt`
    # even when `--format markdown` is used (content is markdown, extension remains `.txt`).
    # Keep the directory name (`md/` vs `text/`) to reflect extraction mode, but always
    # use `.txt` for chunk file discovery/enrichment/augmentation unless/until the
    # chunker is updated to emit `.md` files.
    format_subdir = "md" if args.format == "markdown" else "text"
    chunks_dir = os.path.join(base_output_dir, format_subdir)
    # Metadata is now saved directly in chunks_dir (no separate metadata/ subdirectory)
    metadata_dir = chunks_dir
    augmented_dir = os.path.join(base_output_dir, f"{format_subdir}_enriched") if args.embed_metadata else None

    file_extension = ".txt"

    # Determine store name for vector_stores.json
    if args.store_name:
        store_name = args.store_name
    elif args.embed_metadata:
        store_name = f"{format_subdir}_enriched"
    else:
        store_name = f"{format_subdir}_chunks"

    # Display name for OpenAI vector store
    vector_store_name = args.vector_store_name or f"{args.datasheet_name}_{store_name}"

    # Print configuration
    print("\n" + "=" * 70)
    print("PREPROCESSING PIPELINE")
    print("=" * 70)
    print(f"\nInput PDF: {args.pdf_path}")
    print(f"Datasheet name: {args.datasheet_name}")
    print(f"Device directory: {device_dir}")
    print(f"Output directory: {base_output_dir}")
    print(f"Format: {args.format}")
    print(f"Chunk tokens: {args.max_tokens} (overlap: {args.overlap_tokens})")
    print(f"Embed metadata: {args.embed_metadata}")
    print(f"Backend: {backend}")
    if backend == "openai":
        print(f"Store name: {store_name}")
        print(f"Vector store name: {vector_store_name}")
    elif backend == "local":
        db_name = args.db_name or f"{args.datasheet_name}_md_chunks"
        print(f"Local DB name: {db_name}")
        print(f"Embedding provider: {args.embedding_provider}")
    print("=" * 70)

    if args.dry_run:
        print("\n[DRY RUN] Would execute the following steps:")
        print(f"  1. Chunk PDF to {chunks_dir}")
        print(f"  2. Enrich metadata (metadata.json in {chunks_dir})")
        if args.embed_metadata:
            print(f"  3. Augment chunks to {augmented_dir}")
        if backend == "openai":
            step = 3 if not args.embed_metadata else 4
            print(f"  {step}. Upload to OpenAI vector store: {vector_store_name}")
        elif backend == "local":
            step = 3 if not args.embed_metadata else 4
            print(f"  {step}. Ingest into local ChromaDB: {db_name}")
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
        # Build include_fields from preset +/- include/exclude
        from context_retrieval.preprocessing.p3_augment_chunks_with_metadata import PRESETS
        include_fields = list(PRESETS[args.augment_preset])
        if args.augment_include:
            for f in args.augment_include:
                if f not in include_fields:
                    include_fields.append(f)
        if args.augment_exclude:
            include_fields = [f for f in include_fields if f not in args.augment_exclude]

        print("\n" + "-" * 70)
        run_augmentation(
            chunks_dir,
            metadata_dir,
            augmented_dir,
            file_extension,
            include_fields=include_fields,
        )
        upload_chunks_dir = augmented_dir

    # Step 4: Upload / ingest
    vector_store_id = None
    chunk_index_path = ""
    vector_stores_json_path = None

    if backend == "openai":
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

        # Save legacy vector store info file
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

        # Update device's vector_stores.json
        print("\n" + "-" * 70)
        logger.info("Step 5: Updating device vector_stores.json")

        # Calculate relative paths from device_dir
        rel_chunk_index = os.path.relpath(chunk_index_path, device_dir)
        rel_local_path = os.path.relpath(upload_chunks_dir, device_dir)

        # Build description
        desc_parts = []
        if args.format == "markdown":
            desc_parts.append("Markdown")
        else:
            desc_parts.append("Text")
        desc_parts.append(f"chunks ({args.max_tokens} tokens, {args.overlap_tokens} overlap)")
        if args.embed_metadata:
            desc_parts.append("with embedded metadata")
        description = " ".join(desc_parts)

        vector_stores_json_path = update_device_vector_stores(
            device_dir=device_dir,
            store_name=store_name,
            vector_store_id=vector_store_id,
            description=description,
            chunk_count=len(file_infos),
            chunk_index_path=rel_chunk_index,
            local_path=rel_local_path
        )

    elif backend == "local":
        print("\n" + "-" * 70)
        db_name = args.db_name or f"{args.datasheet_name}_md_chunks"
        result = run_local_ingestion(
            chunks_dir=upload_chunks_dir,
            metadata_dir=metadata_dir,
            device_name=args.datasheet_name,
            device_dir=device_dir,
            db_name=db_name,
            db_path=args.db_path,
            embedding_provider=args.embedding_provider,
            entry_name=args.store_name or f"local_{format_subdir}_chunks",
        )
        if result != 0:
            print("Error: Local ingestion failed")
            return result

    # Summary
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"\nChunks created: {len(chunk_metadata)}")
    print(f"Metadata enriched: {len(enriched_metadata)}")
    if args.embed_metadata:
        print(f"Augmented chunks: {augmented_dir}")
    if backend == "openai" and vector_store_id:
        print(f"\nVector Store ID: {vector_store_id}")
        print(f"Store name: {store_name}")
        print(f"Chunk index: {chunk_index_path}")
        if vector_stores_json_path:
            print(f"\nUpdated: {vector_stores_json_path}")
            print(f"  Entry: {store_name}")
        print(f"\nTo use this vector store:")
        print(f"  from utils.vector_store_config import get_vector_stores")
        print(f"  config = get_vector_stores('{device_dir}')")
        print(f"  vs_id = config.get_vs_id('{store_name}')")
    elif backend == "local":
        db_name = args.db_name or f"{args.datasheet_name}_md_chunks"
        print(f"\nLocal ChromaDB: {db_name}")
        print(f"Embedding provider: {args.embedding_provider}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
