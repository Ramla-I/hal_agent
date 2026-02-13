#!/usr/bin/env python3
"""
Ingest a device datasheet into a local ChromaDB vector database.

Uses the vector_db project's TextProcessor (for markdown) or PDFProcessor (for PDF)
to chunk the document, then stores it in ChromaDB with local or OpenAI embeddings.

Usage:
    python preprocessing/ingest_local_vector_db.py rm0041 --format md
    python preprocessing/ingest_local_vector_db.py rm0041 --format pdf
    python preprocessing/ingest_local_vector_db.py rm0041 --format md --db-path ./local_databases
    python preprocessing/ingest_local_vector_db.py rm0041 --format md --embedding-provider openai
"""

import argparse
import importlib
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config as hal_config

_VECTOR_DB_PATH = str(Path(__file__).resolve().parent.parent.parent / "vector_db")


def _import_vector_db_modules(embedding_provider: str = "local", db_path: str = ""):
    """Import vector_db modules with optional config overrides.

    Temporarily swaps sys.modules['config'] so that vector_db's internal
    `import config` resolves to vector_db/config.py instead of hal_agent/config.py.
    """
    # Save and remove hal_agent's config from sys.modules so vector_db gets its own
    saved_config = sys.modules.pop("config", None)
    # Also save any vector_db modules that may have been previously loaded
    vdb_module_names = ["config", "vector_store", "text_processor", "pdf_processor",
                        "embeddings", "chunking", "reranker"]
    saved_modules = {name: sys.modules.pop(name, None) for name in vdb_module_names}

    original_path = sys.path.copy()
    try:
        sys.path.insert(0, _VECTOR_DB_PATH)

        vdb_config = importlib.import_module("config")

        # Override config before other modules load
        if db_path:
            vdb_config.DATABASES_DIR = Path(db_path)
        if embedding_provider:
            vdb_config.EMBEDDING_PROVIDER = embedding_provider

        vector_store = importlib.import_module("vector_store")
        text_processor = importlib.import_module("text_processor")
        pdf_processor = importlib.import_module("pdf_processor")

        return vdb_config, vector_store, text_processor, pdf_processor
    finally:
        sys.path = original_path
        # Remove vector_db's config from sys.modules to prevent collisions,
        # then restore hal_agent's config if it was previously imported
        sys.modules.pop("config", None)
        if saved_config is not None:
            sys.modules["config"] = saved_config


def ingest_device(
    device_name: str,
    format: str = "md",
    db_path: str = "",
    embedding_provider: str = "local",
    db_name_override: str = "",
):
    """Ingest a device datasheet into local ChromaDB.

    Args:
        device_name: Device identifier (e.g., "rm0041")
        format: Source format - "md" or "pdf"
        db_path: Override databases directory path
        embedding_provider: "local" (FastEmbed) or "openai"
        db_name_override: Override database name (default: {device}_{format})

    Returns:
        0 on success, 1 on error
    """
    vdb_config, vector_store_mod, text_processor_mod, pdf_processor_mod = \
        _import_vector_db_modules(embedding_provider, db_path)

    # Find the device directory
    ctx = next((c for c in hal_config.user_contexts if c.device_name == device_name), None)
    if not ctx:
        print(f"Error: Device '{device_name}' not found in config.user_contexts")
        return 1

    manufacturer = ctx.manufacturer.value.lower()
    device_dir = Path(f"devices/{manufacturer}/{device_name}")
    db_name = db_name_override or f"{device_name}_{format}"

    # Determine source file and process
    if format == "md":
        source_file = device_dir / f"{device_name}.md"
        if not source_file.exists():
            print(f"Error: Markdown file not found: {source_file}")
            return 1
        print(f"Processing markdown: {source_file}")
        processor = text_processor_mod.TextProcessor()
        chunks = processor.process_file(source_file, extra_metadata={"device": device_name})
    elif format == "pdf":
        source_file = device_dir / f"{device_name}.pdf"
        if not source_file.exists():
            print(f"Error: PDF file not found: {source_file}")
            return 1
        print(f"Processing PDF: {source_file}")
        processor = pdf_processor_mod.PDFProcessor()
        chunks = processor.process_pdf(source_file, extra_metadata={"device": device_name})
    else:
        print(f"Error: Unsupported format '{format}'. Use 'md' or 'pdf'.")
        return 1

    print(f"Generated {len(chunks)} chunks")

    # Create database and ingest
    vdb_config.ensure_databases_dir()
    if not vector_store_mod.database_exists(db_name):
        vector_store_mod.create_database(db_name)
        print(f"Created database: {db_name}")
    else:
        print(f"Database '{db_name}' already exists")

    store = vector_store_mod.VectorStore(db_name)
    existing = store.collection.count()
    if existing > 0:
        print(f"Database already has {existing} chunks. Skipping ingestion.")
        print(f"To re-ingest, delete the database first: "
              f"rm -rf {vdb_config.get_db_path(db_name)}")
        return 0

    def progress(batch_num, total_batches):
        print(f"\r  Embedding batch {batch_num}/{total_batches}...", end="", flush=True)

    added = store.add_documents(chunks, progress_callback=progress)
    print(f"\nIngested {added} chunks into database '{db_name}'")
    print(f"Database path: {vdb_config.get_db_path(db_name)}")
    print(f"Embedding provider: {embedding_provider}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Ingest device datasheet into local ChromaDB vector database"
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
