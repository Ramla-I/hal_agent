#!/usr/bin/env python3
"""
Ingest a device datasheet into a local ChromaDB vector database with enriched metadata.

Uses context_retrieval.vector_db (self-contained package) for chunking and embedding.
Produces:
- ChromaDB database with enriched metadata (page_number, has_tables, registers_mentioned)
- Chunk text files in chunked_datasheets/{mfg}/{device}/chunks/local/
- chunks_index.csv for chunk expansion compatibility
- metadata.json for table-aware expansion
- Auto-registers in devices/{mfg}/{device}/vector_stores.json

Usage:
    python preprocessing/ingest_local_vector_db.py rm0041 --format md
    python preprocessing/ingest_local_vector_db.py rm0041 --format md --embedding-provider openai
    python preprocessing/ingest_local_vector_db.py rm0041 --format md --db-path ./local_databases
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config as hal_config
from context_retrieval.vector_db import config as vdb_config
from context_retrieval.vector_db.text_processor import TextProcessor
from context_retrieval.vector_db.vector_store import VectorStore, database_exists, create_database
from context_retrieval.vector_db.chunking import count_tokens
from utils.vector_store_config import load_vector_stores, save_vector_stores, VectorStoreInfo


def ingest_device(
    device_name: str,
    format: str = "md",
    db_path: str = "",
    embedding_provider: str = "local",
    db_name_override: str = "",
):
    """Ingest a device datasheet into local ChromaDB with enriched metadata.

    Args:
        device_name: Device identifier (e.g., "rm0041")
        format: Source format - "md" or "pdf"
        db_path: Override databases directory path
        embedding_provider: "local" (FastEmbed) or "openai"
        db_name_override: Override database name (default: {device}_{format})

    Returns:
        0 on success, 1 on error
    """
    # Override config before creating any stores
    if db_path:
        vdb_config.DATABASES_DIR = Path(db_path)
    vdb_config.EMBEDDING_PROVIDER = embedding_provider

    # Find the device directory
    ctx = next((c for c in hal_config.user_contexts if c.device_name == device_name), None)
    if not ctx:
        print(f"Error: Device '{device_name}' not found in config.user_contexts")
        return 1

    manufacturer = ctx.manufacturer.value.lower()
    device_dir = Path(f"devices/{manufacturer}/{device_name}")
    db_name = db_name_override or f"{device_name}_{format}"

    # Determine source file
    if format == "md":
        source_file = device_dir / f"{device_name}.md"
    elif format == "pdf":
        print("Error: PDF format not yet supported for enriched ingestion. Use --format md.")
        return 1
    else:
        print(f"Error: Unsupported format '{format}'. Use 'md'.")
        return 1

    if not source_file.exists():
        print(f"Error: Source file not found: {source_file}")
        return 1

    print(f"Processing: {source_file}")
    print(f"Embedding provider: {embedding_provider}")

    # Process file with enriched TextProcessor
    processor = TextProcessor()
    chunks = processor.process_file(source_file, extra_metadata={"device": device_name})
    print(f"Generated {len(chunks)} chunks with enriched metadata")

    # --- Save chunk files + chunks_index.csv + metadata.json ---
    chunks_dir = Path(f"chunked_datasheets/{manufacturer}/{device_name}/chunks/local")
    chunks_dir.mkdir(parents=True, exist_ok=True)

    csv_rows = []
    metadata_dict = {}

    # Track chunks per page for total_chunks_on_page
    page_chunk_counts = {}
    for chunk in chunks:
        page = chunk["metadata"].get("page_number", 0)
        page_chunk_counts[page] = page_chunk_counts.get(page, 0) + 1

    # Track chunk index per page for naming
    page_chunk_indices = {}

    for chunk in chunks:
        page = chunk["metadata"].get("page_number", 0)
        page_chunk_indices[page] = page_chunk_indices.get(page, 0) + 1
        chunk_on_page = page_chunk_indices[page]

        chunk_id = f"{device_name}_p{page:03d}_c{chunk_on_page:02d}"
        chunk_file = chunks_dir / f"{chunk_id}.txt"

        # Write chunk text file
        chunk_file.write_text(chunk["text"], encoding="utf-8")

        # Build CSV row
        token_count = count_tokens(chunk["text"])
        csv_rows.append({
            "chunk_id": chunk_id,
            "file_id": "",  # No OpenAI file ID for local
            "file_path": str(chunk_file),
            "page_number": page,
            "chunk_index": chunk_on_page,
            "total_chunks_on_page": page_chunk_counts.get(page, 0),
            "token_count": token_count,
            "datasheet": device_name,
        })

        # Build metadata entry
        registers_list = chunk["metadata"].get("registers_mentioned", [])
        metadata_dict[chunk_id] = {
            "has_tables": chunk["metadata"].get("has_tables", False),
            "registers_mentioned": registers_list,
            "section": chunk["metadata"].get("section", ""),
            "page_number": page,
            "token_count": token_count,
        }

    # Write chunks_index.csv
    csv_path = chunks_dir / "chunks_index.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "chunk_id", "file_id", "file_path", "page_number",
            "chunk_index", "total_chunks_on_page", "token_count", "datasheet"
        ])
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"Saved {len(csv_rows)} chunk files to {chunks_dir}")
    print(f"Saved chunks_index.csv: {csv_path}")

    # Write metadata.json
    metadata_path = chunks_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata_dict, f, indent=2)
    print(f"Saved metadata.json: {metadata_path}")

    # --- Ingest into ChromaDB ---
    vdb_config.ensure_databases_dir()
    if not database_exists(db_name):
        create_database(db_name)
        print(f"Created database: {db_name}")
    else:
        print(f"Database '{db_name}' already exists")

    store = VectorStore(db_name)
    existing = store.collection.count()
    if existing > 0:
        print(f"Database already has {existing} chunks. Skipping ingestion.")
        print(f"To re-ingest, delete the database first: "
              f"rm -rf {vdb_config.get_db_path(db_name)}")
    else:
        def progress(batch_num, total_batches):
            print(f"\r  Embedding batch {batch_num}/{total_batches}...", end="", flush=True)

        added = store.add_documents(chunks, progress_callback=progress)
        print(f"\nIngested {added} chunks into database '{db_name}'")

    print(f"Database path: {vdb_config.get_db_path(db_name)}")

    # --- Register in vector_stores.json ---
    try:
        vs_config = load_vector_stores(str(device_dir))
    except FileNotFoundError:
        print(f"Warning: vector_stores.json not found in {device_dir}, skipping registration")
        return 0

    entry_name = f"local_{format}"
    # Compute relative path from device_dir to chunks_dir
    chunks_dir_abs = chunks_dir.resolve()
    device_dir_abs = device_dir.resolve()
    try:
        rel_path = os.path.relpath(chunks_dir_abs, device_dir_abs)
    except ValueError:
        rel_path = str(chunks_dir_abs)

    rel_csv = os.path.join(rel_path, "chunks_index.csv")

    vs_config.vector_stores[entry_name] = VectorStoreInfo(
        name=entry_name,
        vs_id=None,
        description=f"Local ChromaDB with enriched metadata (page numbers, registers, tables)",
        local_db_name=db_name,
        local_path=rel_path,
        chunk_index_path=rel_csv,
        embedding_provider=embedding_provider,
    )
    save_vector_stores(str(device_dir), vs_config)
    print(f"Registered '{entry_name}' in {device_dir}/vector_stores.json")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Ingest device datasheet into local ChromaDB with enriched metadata"
    )
    parser.add_argument("device_name", help="Device name (e.g., rm0041)")
    parser.add_argument(
        "--format", choices=["md", "pdf"], default="md",
        help="Source format: md (markdown) or pdf (default: md)"
    )
    parser.add_argument(
        "--db-path", default="",
        help="Override databases directory path (default: vector_db/databases/)"
    )
    parser.add_argument(
        "--embedding-provider", choices=["local", "openai"], default="local",
        help="Embedding provider: local (FastEmbed, free) or openai (API) (default: local)"
    )
    parser.add_argument(
        "--db-name", default="",
        help="Override database name (default: {device}_{format})"
    )
    args = parser.parse_args()

    sys.exit(ingest_device(
        args.device_name,
        args.format,
        args.db_path,
        args.embedding_provider,
        args.db_name,
    ))


if __name__ == "__main__":
    main()
