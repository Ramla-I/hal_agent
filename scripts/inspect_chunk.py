#!/usr/bin/env python3
"""
Inspect a chunk from a local ChromaDB vector database by index.

Usage:
    python scripts/inspect_chunk.py rm0041_md 42
    python scripts/inspect_chunk.py rm0041_md 100-105
    python scripts/inspect_chunk.py rm0041_md 42 --db-path /path/to/databases
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from context_retrieval.vector_db import config as vdb_config
from context_retrieval.vector_db.vector_store import VectorStore


def main():
    parser = argparse.ArgumentParser(description="Inspect chunks from a local ChromaDB")
    parser.add_argument("db_name", help="Database name (e.g., rm0041_md)")
    parser.add_argument("index", help="Chunk index (e.g., 42) or range (e.g., 100-105)")
    parser.add_argument("--db-path", default="", help="Override databases directory path")
    args = parser.parse_args()

    # Parse index or range
    if "-" in args.index:
        start, end = args.index.split("-", 1)
        indices = list(range(int(start), int(end) + 1))
    else:
        indices = [int(args.index)]

    if args.db_path:
        vdb_config.DATABASES_DIR = Path(args.db_path)
    vdb_config.EMBEDDING_PROVIDER = "local"

    store = VectorStore(args.db_name)
    total = store.collection.count()
    print(f"Database: {args.db_name} ({total} chunks)\n")

    ids = [f"doc_{i}" for i in indices]
    results = store.collection.get(ids=ids, include=["documents", "metadatas"])

    for i, (doc_id, doc, meta) in enumerate(
        zip(results["ids"], results["documents"], results["metadatas"])
    ):
        idx = doc_id.replace("doc_", "")
        print(f"{'='*70}")
        print(f"Chunk {idx}")
        print(f"{'='*70}")
        if meta:
            for k, v in sorted(meta.items()):
                print(f"  {k}: {v}")
        print(f"{'─'*70}")
        print(doc)
        print()


if __name__ == "__main__":
    main()
