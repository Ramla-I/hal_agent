"""
OpenEvolve initial program: Datasheet retrieval pipeline.

This program defines the full retrieval pipeline that OpenEvolve will evolve:
  1. process_chunks()    — preprocess raw markdown chunks + build metadata
  2. build_query()       — construct search query for a register
  3. search_and_format() — search the vector DB, post-process, and format context

The code inside the EVOLVE-BLOCK is what the LLM mutates each iteration.
Everything outside (imports, DB setup, entry point) stays fixed.
"""

import os
import sys
import re
import csv
import json
from typing import List, Dict, Any, Optional, Tuple

# ---------------------------------------------------------------------------
# Fixed infrastructure (NOT evolved)
# ---------------------------------------------------------------------------

# Resolve project root so we can import hal_agent modules
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Ensure openevolve_retrieval package is importable for shared cache
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
if _PACKAGE_DIR not in sys.path:
    sys.path.insert(0, _PACKAGE_DIR)

import chromadb
from chromadb.config import Settings

# Use hal_agent's local embedding provider (FastEmbed, free, no API calls)
from context_retrieval.vector_db.embeddings import FastEmbedProvider

# Shared embedding cache — persists across dynamically-loaded evolved modules
from _shared_cache import compute_embeddings_cached

_embedding_provider = None


def get_embedding_provider():
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = FastEmbedProvider()
    return _embedding_provider


def load_raw_chunks(chunks_dir: str, chunks_index_csv: str) -> List[Dict[str, Any]]:
    """Load raw chunk texts and metadata from disk.

    Returns list of dicts with keys:
        text, page_number, chunk_index, chunk_id, source, token_count
    """
    chunks = []
    with open(chunks_index_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            chunk_id = row["chunk_id"]
            # Resolve chunk file: prefer chunks_dir/{chunk_id}.txt over CSV file_path
            file_path = os.path.join(chunks_dir, f"{chunk_id}.txt")
            if not os.path.exists(file_path):
                # Fallback to CSV file_path relative to project root
                file_path = os.path.join(
                    _PROJECT_ROOT,
                    row.get("file_path", ""),
                )
            if not os.path.exists(file_path):
                continue
            with open(file_path, "r") as cf:
                text = cf.read()
            chunks.append({
                "text": text,
                "page_number": int(row.get("page_number", 0)),
                "chunk_index": int(row.get("chunk_index", 0)),
                "chunk_id": chunk_id,
                "source": file_path,
                "token_count": int(row.get("token_count", 0)),
            })
    return chunks


def build_ephemeral_store(processed_chunks: List[Dict[str, Any]]) -> chromadb.Collection:
    """Build an in-memory ChromaDB collection from processed chunks.

    Uses the shared embedding cache so unchanged chunk texts are not re-embedded.
    """
    provider = get_embedding_provider()
    client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
    collection = client.get_or_create_collection("docs", metadata={"hnsw:space": "cosine"})

    texts = [c["text"] for c in processed_chunks]
    metadatas = []
    for c in processed_chunks:
        meta = dict(c.get("metadata", {}))
        # ChromaDB metadata values must be str, int, float, or bool
        for k, v in list(meta.items()):
            if isinstance(v, list):
                meta[k] = json.dumps(v)
            elif v is None:
                del meta[k]
        metadatas.append(meta)

    embeddings = compute_embeddings_cached(texts, provider)
    ids = [f"doc_{i}" for i in range(len(processed_chunks))]
    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    return collection


# EVOLVE-BLOCK-START
def process_chunks(raw_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Preprocess raw markdown chunks and attach metadata.

    Called once per evaluation. Takes raw chunk dicts and returns processed
    chunk dicts ready for vector DB ingestion.

    Each returned dict must have:
        - "text": str  (the text to embed and store)
        - "metadata": dict  (searchable metadata — values must be str/int/float/bool)

    Available raw chunk fields:
        text, page_number, chunk_index, chunk_id, source, token_count

    The LLM is free to:
        - Modify chunk text (add headers, extract key terms, summarize)
        - Split or merge chunks
        - Compute and attach metadata (register names, has_tables, section, etc.)
        - Filter out irrelevant chunks
    """
    processed = []
    for chunk in raw_chunks:
        processed.append({
            "text": chunk["text"],
            "metadata": {
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
            },
        })
    return processed


def build_query(peripheral_name: str, register_name: str) -> str:
    """Construct a search query for retrieving register information.

    Args:
        peripheral_name: e.g. "afio"
        register_name: e.g. "evcr"

    Returns:
        Query string for semantic search.
    """
    reg_key = f"{peripheral_name}_{register_name}".upper()
    return (
        f"For the {reg_key} register, retrieve all information about "
        f"its offset, reset value, size, readonly bits, writeonly bits, "
        f"readwrite bits, and subfields."
    )


def search_and_format(
    collection: "chromadb.Collection",
    query: str,
    embedding_fn,
    peripheral_name: str,
    register_name: str,
    all_processed_chunks: List[Dict[str, Any]],
) -> str:
    """Search the vector DB, post-process results, and return formatted context.

    Args:
        collection: ChromaDB collection to search
        query: Search query string
        embedding_fn: Callable that takes a list of strings, returns list of embeddings
        peripheral_name: e.g. "afio"
        register_name: e.g. "evcr"
        all_processed_chunks: All processed chunks (for expansion lookups)

    Returns:
        Formatted context string to feed to the generator LLM.
        Return empty string if no relevant results found.

    The LLM is free to:
        - Use metadata filtering (where clauses)
        - Adjust n_results
        - Run multiple queries (decompose by aspect)
        - Rerank results using heuristics
        - Expand results with adjacent chunks
        - Order results by page number
        - Format results in any way
    """
    query_embedding = embedding_fn([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0] if results["documents"][0] else []
    metas = results["metadatas"][0] if results["metadatas"][0] else []

    if not docs:
        return ""

    # Format results
    parts = []
    for doc, meta in zip(docs, metas):
        page = meta.get("page_number", "?")
        parts.append(f"[Page {page}]\n{doc}")

    return "\n\n---\n\n".join(parts)
# EVOLVE-BLOCK-END


# ---------------------------------------------------------------------------
# Entry point called by the evaluator
# ---------------------------------------------------------------------------

_collection_cache = None
_processed_chunks_cache = None


def setup_database(chunks_dir: str, chunks_index_csv: str) -> Tuple:
    """Build the vector DB from raw chunks. Called once per evaluation."""
    global _collection_cache, _processed_chunks_cache

    raw_chunks = load_raw_chunks(chunks_dir, chunks_index_csv)
    processed = process_chunks(raw_chunks)
    collection = build_ephemeral_store(processed)
    _collection_cache = collection
    _processed_chunks_cache = processed
    return collection, processed


def run_retrieval(
    peripheral_name: str,
    register_name: str,
    collection=None,
    processed_chunks=None,
) -> str:
    """Retrieve context for a single register. Called once per register."""
    col = collection or _collection_cache
    chunks = processed_chunks or _processed_chunks_cache
    if col is None:
        raise RuntimeError("Call setup_database() first")

    provider = get_embedding_provider()
    query = build_query(peripheral_name, register_name)
    return search_and_format(
        col, query, provider.embed, peripheral_name, register_name, chunks
    )
