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
        text = chunk["text"]
        
        # Detect markdown tables (simple heuristic)
        has_tables = bool(re.search(r"\|\s*-{3,}\s*\|", text))
        
        # Extract potential register-like names (e.g., AFIO_EVCR, CRC_DR)
        # Regex: at least two uppercase letters/underscore, then underscore, then more uppercase/digits/underscore
        potential_reg_names = sorted(list(set(re.findall(r"\b[A-Z_]{2,}_[A-Z0-9_]{2,}\b", text))))
        
        # Prepend extracted register names to the chunk text to boost their embedding relevance
        header = ""
        if potential_reg_names:
            # Limit to a few names to avoid excessive header length
            header = "Register: " + ", ".join(potential_reg_names[:3]) + "\n\n"
        
        processed.append({
            "text": header + text, # Modified text for embedding
            "metadata": {
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
                "has_tables": has_tables,
                # Store register names as a JSON string for ChromaDB metadata
                "register_names_in_chunk": json.dumps(potential_reg_names) if potential_reg_names else "[]",
                "chunk_id": chunk["chunk_id"], # Keep chunk_id for potential lookups
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
        f"Retrieve all detailed information about the {reg_key} register, "
        f"including its address offset, reset value, bit field definitions, "
        f"access types, and enumerated values for its subfields."
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
    reg_key = f"{peripheral_name}_{register_name}".upper()
    query_embedding = embedding_fn([query])[0]

    # Map all processed chunks for efficient lookup during expansion
    chunk_map = {}
    for p_chunk in all_processed_chunks:
        page_num = p_chunk["metadata"]["page_number"]
        chunk_idx = p_chunk["metadata"]["chunk_index"]
        chunk_map[(page_num, chunk_idx)] = p_chunk # Store the full processed chunk

    # Perform a broad initial semantic search to get a pool of candidates
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=20, # Retrieve more to allow for better filtering/reranking
        include=["documents", "metadatas", "distances"],
    )

    if not results["documents"][0]:
        return ""

    scored_results = []
    for i in range(len(results["documents"][0])):
        doc = results["documents"][0][i]
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        
        score = 0
        # Boost for exact register name presence in the document
        if reg_key in doc:
            score += 100
            # Further boost if it's a table-rich chunk and contains the reg key
            if meta.get("has_tables", False):
                score += 50
        # Boost for table presence even if exact reg_key isn't a strong match
        elif meta.get("has_tables", False):
            score += 20
        
        # Add similarity score (lower distance is higher similarity)
        # Cosine distance ranges [0, 2], so (2 - dist) gives similarity [2, 0]
        score += (2 - dist) * 10 
        
        scored_results.append({"doc": doc, "meta": meta, "dist": dist, "score": score})

    # Sort by custom score (higher is better)
    scored_results.sort(key=lambda x: x["score"], reverse=True)

    # Collect final chunks, ensuring uniqueness and allowing for expansion
    final_collected_chunks = {} # Key: (page_number, chunk_index)
    
    # Add top N_CONTEXT_CHUNKS results after reranking
    N_CONTEXT_CHUNKS = 6 # Reduce target core chunks slightly to reduce overall context length
    for item in scored_results[:N_CONTEXT_CHUNKS]:
        page_num = item["meta"]["page_number"]
        chunk_idx = item["meta"]["chunk_index"]
        if (page_num, chunk_idx) not in final_collected_chunks:
            final_collected_chunks[(page_num, chunk_idx)] = item["doc"]

        # Simple expansion: look for immediate neighbors on the same page
        # if the current chunk is highly relevant or has tables.
        # This helps capture full definitions that might span multiple chunks.
        if item["score"] > 100 or item["meta"].get("has_tables", False): # Only expand from highly relevant/table chunks
            for offset in [-1, 1]:
                neighbor_page = page_num
                neighbor_chunk_idx = chunk_idx + offset
                if (neighbor_page, neighbor_chunk_idx) in chunk_map:
                    neighbor_p_chunk = chunk_map[(neighbor_page, neighbor_chunk_idx)]
                    neighbor_doc = neighbor_p_chunk["text"]
                    neighbor_meta = neighbor_p_chunk["metadata"]
                    
                    # Heuristic for neighbor relevance: contains peripheral name, register name, or is a table
                    is_neighbor_relevant = (reg_key in neighbor_doc or
                                           neighbor_meta.get("has_tables", False)) # Focus expansion on specific register key or tables

                    if is_neighbor_relevant and (neighbor_page, neighbor_chunk_idx) not in final_collected_chunks:
                        final_collected_chunks[(neighbor_page, neighbor_chunk_idx)] = neighbor_doc

    # Sort final selected chunks by page number and chunk index for coherent reading
    sorted_final_chunks = sorted(final_collected_chunks.items(), key=lambda x: x[0])

    # Format results
    parts = []
    for (page, _), doc in sorted_final_chunks:
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
