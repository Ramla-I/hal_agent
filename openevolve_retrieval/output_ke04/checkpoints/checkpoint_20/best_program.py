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
        # Detect if the chunk contains a markdown table
        # A simple heuristic: check for lines containing multiple '|' characters
        has_tables = bool(re.search(r'\|.*\|', chunk["text"]))
        
        # Prepend a header with page number for better context in embeddings
        # and to make it easier for the LLM to identify page boundaries
        processed_text = f"Page {chunk['page_number']}:\n\n" + chunk["text"]

        processed.append({
            "text": processed_text,
            "metadata": {
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
                "has_tables": has_tables, # Add has_tables metadata
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
    # Use both full PERIPHERAL_REGISTER name and just the REGISTER name
    # NXP KE04 registers often use short names (c0, c1, sc1, bdh)
    reg_full_name = f"{peripheral_name.upper()}_{register_name.upper()}"
    reg_short_name = register_name.upper()
    return (
        f"Retrieve detailed information for the {reg_full_name} register "
        f"({reg_short_name}). Include its memory offset, reset value, "
        f"bit field definitions, access types (read-only, write-only, read/write), "
        f"and any enumerated values for its fields. Focus on tables describing bit fields."
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
    
    reg_full_name = f"{peripheral_name.upper()}_{register_name.upper()}"
    reg_short_name = register_name.upper()
    
    # Define text search keywords for where_document filter
    text_keywords = [reg_full_name, reg_short_name]
    # Add peripheral name + short name if it's a distinct useful pattern, e.g., "ADC SC1"
    if peripheral_name.upper() != reg_full_name.split('_')[0] and f"{peripheral_name.upper()} {reg_short_name}" not in text_keywords:
        text_keywords.append(f"{peripheral_name.upper()} {reg_short_name}")
    
    where_doc_clause = {"$or": [{"$contains": kw} for kw in text_keywords]}

    # --- Query 1: Prioritize chunks with tables and register name match ---
    # Retrieve more results initially to allow for reranking and selection
    results_primary = collection.query(
        query_embeddings=[query_embedding],
        n_results=7, # Retrieve a reasonable number to allow for filtering/reranking
        where={"has_tables": True},
        where_document=where_doc_clause,
        include=["documents", "metadatas", "distances"],
    )

    all_retrieved_items = []
    seen_chunk_ids = set()

    def add_unique_results(res_list):
        for i in range(len(res_list["documents"][0])):
            doc = res_list["documents"][0][i]
            meta = res_list["metadatas"][0][i]
            dist = res_list["distances"][0][i]
            # Use page_number and chunk_index as a proxy for unique chunk ID
            unique_id = (meta.get("page_number"), meta.get("chunk_index"))
            if unique_id not in seen_chunk_ids:
                all_retrieved_items.append({"doc": doc, "meta": meta, "dist": dist})
                seen_chunk_ids.add(unique_id)

    add_unique_results(results_primary)

    # --- Fallback Query: If primary query yields too few results, try without table filter ---
    # This helps catch introductory text or definitions without explicit tables in the chunk
    if len(all_retrieved_items) < 2: # If less than 2 strong results, broaden the search
        results_fallback = collection.query(
            query_embeddings=[query_embedding],
            n_results=5, # Get fewer additional results for fallback
            where_document=where_doc_clause, # Still try to match register name in text
            include=["documents", "metadatas", "distances"],
        )
        add_unique_results(results_fallback)
    
    if not all_retrieved_items:
        return ""

    # Rerank combined results
    def rank_key(item):
        doc = item["doc"]
        meta = item["meta"]
        distance = item["dist"]
        
        has_table_score = 1 if meta.get("has_tables", False) else 0
        
        # Check for register name presence in the document text
        reg_name_present = 0
        if re.search(r'\b' + re.escape(reg_full_name) + r'\b', doc, re.IGNORECASE):
            reg_name_present = 2
        elif re.search(r'\b' + re.escape(reg_short_name) + r'\b', doc, re.IGNORECASE):
            reg_name_present = 1
        
        # Sort by: distance (ascending), then has_table (descending), then reg_name_present (descending)
        return (distance, -has_table_score, -reg_name_present)

    all_retrieved_items.sort(key=rank_key)

    # Select top N chunks to control context length
    MAX_CHUNKS = 4 # Target a smaller number of highly relevant chunks to reduce context length
    final_context_items = all_retrieved_items[:MAX_CHUNKS]

    # Sort final selected chunks by page number and chunk index for coherent reading
    final_context_items.sort(key=lambda x: (x['meta'].get('page_number', 0), x['meta'].get('chunk_index', 0)))

    # Format results
    parts = []
    for item in final_context_items:
        page = item['meta'].get("page_number", "?")
        parts.append(f"[Page {page}]\n{item['doc']}")

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
