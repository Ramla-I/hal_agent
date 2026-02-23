#!/usr/bin/env python3
"""
Ingest pre-existing chunks into a local ChromaDB vector database with enriched metadata.

Reads chunk .txt files produced by the preprocessing pipeline (p1+p2+p3),
along with chunks_index.csv and metadata.json, and ingests them into ChromaDB
with full enriched metadata for filtering and search.

Auto-registers the database in devices/{mfg}/{device}/vector_stores.json.

Usage:
    # Ingest pre-existing chunks from a directory
    python context_retrieval/preprocessing/ingest_local_vector_db.py rm0041 \
        --chunks-dir chunked_datasheets/stm/rm0041/chunks/md/ \
        --db-name rm0041_md_chunks

    python context_retrieval/preprocessing/ingest_local_vector_db.py rm0041 \
        --chunks-dir chunked_datasheets/stm/rm0041/chunks/md/ \
        --embedding-provider openai
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config as hal_config
from context_retrieval.vector_db import config as vdb_config
from context_retrieval.vector_db.vector_store import VectorStore, database_exists, create_database
from utils.vector_store_config import load_vector_stores, save_vector_stores, VectorStoreInfo


def ingest_from_chunks_dir(
    device_name: str,
    chunks_dir: str,
    db_name: str = "",
    db_path: str = "",
    embedding_provider: str = "local",
    entry_name: str = "",
):
    """Ingest pre-existing chunk files from a directory into ChromaDB.

    Reads chunk .txt files, chunks_index.csv for page numbers, and
    metadata.json (from p2 enrichment) for registers/tables/sections.

    Args:
        device_name: Device identifier (e.g., "rm0041")
        chunks_dir: Path to directory containing chunk .txt files + chunks_index.csv
        db_name: ChromaDB database name (default: {device}_md_chunks)
        db_path: Override databases directory path
        embedding_provider: "local" (FastEmbed) or "openai"
        entry_name: Name for vector_stores.json entry (default: local_md_chunks)

    Returns:
        0 on success, 1 on error
    """
    if db_path:
        vdb_config.DATABASES_DIR = Path(db_path)
    vdb_config.EMBEDDING_PROVIDER = embedding_provider

    chunks_dir_path = Path(chunks_dir)
    if not chunks_dir_path.exists():
        print(f"Error: Chunks directory not found: {chunks_dir_path}")
        return 1

    db_name = db_name or f"{device_name}_md_chunks"
    entry_name = entry_name or "local_md_chunks"

    # Find device context for manufacturer info
    ctx = next((c for c in hal_config.user_contexts if c.device_name == device_name), None)
    if not ctx:
        print(f"Error: Device '{device_name}' not found in config.user_contexts")
        return 1

    manufacturer = ctx.manufacturer.value.lower()
    device_dir = Path(f"devices/{manufacturer}/{device_name}")

    # --- Read chunks_index.csv for page numbers ---
    csv_path = chunks_dir_path / "chunks_index.csv"
    if not csv_path.exists():
        print(f"Error: chunks_index.csv not found in {chunks_dir_path}")
        return 1

    chunk_index = {}  # chunk_id -> row dict
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            chunk_index[row["chunk_id"]] = row

    print(f"Loaded {len(chunk_index)} entries from chunks_index.csv")

    # --- Read metadata.json (optional, from p2 enrichment) ---
    metadata_path = chunks_dir_path / "metadata.json"
    enriched_metadata = {}
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            enriched_metadata = json.load(f)
        print(f"Loaded enriched metadata for {len(enriched_metadata)} chunks")
    else:
        print("Warning: No metadata.json found. Ingesting with page numbers only.")

    # --- Read chunk files and build document list ---
    chunk_files = sorted(chunks_dir_path.glob("*.txt"))
    print(f"Found {len(chunk_files)} chunk files")

    chunks = []
    for chunk_file in chunk_files:
        chunk_id = chunk_file.stem
        text = chunk_file.read_text(encoding="utf-8")

        if not text.strip():
            continue

        # Get page number from CSV index
        csv_row = chunk_index.get(chunk_id, {})
        page_number = int(csv_row.get("page_number", 0))
        chunk_idx = int(csv_row.get("chunk_index", 0))
        total_on_page = int(csv_row.get("total_chunks_on_page", 0))

        # Get enriched metadata if available
        enriched = enriched_metadata.get(chunk_id, {})

        metadata = {
            "page_number": page_number,
            "chunk_index": chunk_idx,
            "total_chunks_on_page": total_on_page,
            "device": device_name,
            "source": str(chunk_file),
            "has_tables": bool(enriched.get("has_tables", False)),
        }

        # String fields from p2 enrichment (truncated to 100 chars for ChromaDB)
        for field in ("peripheral", "chapter", "subsection", "chunk_type",
                      "importance", "completeness", "primary_register"):
            val = enriched.get(field) or ""
            if val:
                metadata[field] = val[:100]

        # Only add non-empty section (backward compat)
        section = enriched.get("section") or ""
        if section:
            metadata["section"] = section[:100]

        # Integer fields
        for field in ("token_count", "num_registers"):
            val = enriched.get(field)
            if val is not None:
                metadata[field] = int(val)

        # Boolean fields
        for field in ("has_code_examples", "has_diagrams"):
            val = enriched.get(field)
            if val is not None:
                metadata[field] = bool(val)

        # Add registers as individual boolean fields for ChromaDB where-filtering
        regs = enriched.get("registers_mentioned", [])
        for reg_name in regs:
            metadata[f"reg_{reg_name}"] = True

        chunks.append({"text": text, "metadata": metadata})

    print(f"Prepared {len(chunks)} chunks for ingestion")

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

    chunks_dir_abs = chunks_dir_path.resolve()
    device_dir_abs = device_dir.resolve()
    try:
        rel_path = os.path.relpath(chunks_dir_abs, device_dir_abs)
    except ValueError:
        rel_path = str(chunks_dir_abs)

    rel_csv = os.path.join(rel_path, "chunks_index.csv")

    vs_config.vector_stores[entry_name] = VectorStoreInfo(
        name=entry_name,
        vs_id=None,
        description=f"Local ChromaDB from pre-existing md chunks ({len(chunks)} chunks)",
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
        description="Ingest pre-existing chunks into local ChromaDB with enriched metadata"
    )
    parser.add_argument("device_name", help="Device name (e.g., rm0041)")
    parser.add_argument(
        "--chunks-dir", required=True,
        help="Directory containing chunk .txt files + chunks_index.csv + metadata.json"
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
        help="Override database name (default: {device}_md_chunks)"
    )
    parser.add_argument(
        "--entry-name", default="",
        help="Name for vector_stores.json entry (default: local_md_chunks)"
    )
    args = parser.parse_args()

    sys.exit(ingest_from_chunks_dir(
        args.device_name,
        args.chunks_dir,
        args.db_name,
        args.db_path,
        args.embedding_provider,
        args.entry_name,
    ))


if __name__ == "__main__":
    main()
