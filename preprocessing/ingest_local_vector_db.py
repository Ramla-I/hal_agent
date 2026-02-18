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
    # Full pipeline: chunk + enrich + ingest
    python preprocessing/ingest_local_vector_db.py rm0041 --format md

    # Ingest pre-existing chunks from a directory
    python preprocessing/ingest_local_vector_db.py rm0041 --chunks-dir chunked_datasheets/stm/rm0041/chunks/md/ --db-name rm0041_md_chunks

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

        # Only add non-empty string fields (ChromaDB rejects None)
        section = enriched.get("section") or ""
        if section:
            metadata["section"] = section

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
        description="Ingest device datasheet into local ChromaDB with enriched metadata"
    )
    parser.add_argument("device_name", help="Device name (e.g., rm0041)")
    parser.add_argument(
        "--format", choices=["md", "pdf"], default="md",
        help="Source format: md (markdown) or pdf (default: md)"
    )
    parser.add_argument(
        "--chunks-dir", default="",
        help="Ingest pre-existing chunks from this directory (must contain .txt files + chunks_index.csv)"
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
        help="Override database name (default: {device}_{format} or {device}_md_chunks)"
    )
    parser.add_argument(
        "--entry-name", default="",
        help="Name for vector_stores.json entry (default: local_{format} or local_md_chunks)"
    )
    args = parser.parse_args()

    if args.chunks_dir:
        sys.exit(ingest_from_chunks_dir(
            args.device_name,
            args.chunks_dir,
            args.db_name,
            args.db_path,
            args.embedding_provider,
            args.entry_name,
        ))
    else:
        sys.exit(ingest_device(
            args.device_name,
            args.format,
            args.db_path,
            args.embedding_provider,
            args.db_name,
        ))


if __name__ == "__main__":
    main()
