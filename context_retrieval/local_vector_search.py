"""
Local vector database search using ChromaDB (via context_retrieval.vector_db package).

Wraps VectorStore API to match hal_agent's retrieve_context() interface,
returning (formatted_xml_string, embedding_ids_list), matching the format of
openai_file_search.py.

Features:
- Metadata filtering: narrows search to chunks mentioning the target register
- Chunk expansion: appends contiguous page chunks after initial results
- Keyword boost: reorders results by exact keyword match
- Reranking: optional FlashRank/Cohere/BGE reranking
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from utils.timing import timed_operation
from context_retrieval.vector_db import config as vdb_config
from context_retrieval.vector_db.vector_store import VectorStore
from context_retrieval.vector_db.reranker import get_reranker


# Cached VectorStore instances: cache_key -> VectorStore
_store_cache: Dict[str, Any] = {}


def _get_store(db_name: str, db_path: str = "", embedding_provider: str = "local") -> VectorStore:
    """Get or create a cached VectorStore instance."""
    cache_key = f"{db_name}:{db_path}:{embedding_provider}"
    if cache_key not in _store_cache:
        if db_path:
            vdb_config.DATABASES_DIR = Path(db_path)
        vdb_config.EMBEDDING_PROVIDER = embedding_provider

        store = VectorStore(db_name)
        _store_cache[cache_key] = store
    return _store_cache[cache_key]


def format_local_results(results: List[Dict[str, Any]], expansion_chunks: Optional[List[Dict[str, Any]]] = None) -> str:
    """Format local search results in XML <sources> format matching openai_file_search.py output.

    Args:
        results: Primary search results
        expansion_chunks: Optional expansion chunks from contiguous pages
    """
    if not results:
        return ""

    formatted_parts = []
    for i, result in enumerate(results):
        source = result["metadata"].get("source", "unknown")
        section = result["metadata"].get("section", "")
        peripheral = result["metadata"].get("peripheral", "")
        chunk_type = result["metadata"].get("chunk_type", "")
        score = result.get("score", 0)
        text = result["text"]
        page = result["metadata"].get("page_number", 0)
        formatted_parts.append(
            f"<result source='{source}' section='{section}' peripheral='{peripheral}' "
            f"chunk_type='{chunk_type}' rank='{i}' score='{score:.3f}' page='{page}'>"
            f"<content>{text}</content>"
            f"</result>"
        )

    # Append expansion chunks
    if expansion_chunks:
        for chunk in expansion_chunks:
            chunk_id = chunk.get("chunk_id", "unknown")
            page = chunk.get("page_number", 0)
            text = chunk.get("text", "")
            formatted_parts.append(
                f"<result source='expansion' chunk_id='{chunk_id}' page='{page}' expansion='true'>"
                f"<content>{text}</content>"
                f"</result>"
            )

    return f"<sources>{''.join(formatted_parts)}</sources>"


def extract_local_embedding_ids(results: List[Dict[str, Any]]) -> List[Dict]:
    """Extract tracking metadata from local search results."""
    embedding_ids = []
    for i, result in enumerate(results):
        embedding_ids.append({
            "source": result["metadata"].get("source", ""),
            "section": result["metadata"].get("section", ""),
            "peripheral": result["metadata"].get("peripheral", ""),
            "chunk_type": result["metadata"].get("chunk_type", ""),
            "importance": result["metadata"].get("importance", ""),
            "chunk_index": result["metadata"].get("chunk_index", -1),
            "page_number": result["metadata"].get("page_number", 0),
            "rank": i,
            "score": float(result.get("score", 0)),
            "keyword_boost": float(result.get("keyword_boost", 0)),
        })
    return embedding_ids


def _build_register_filter(register_name: str) -> tuple[Optional[Dict[str, Any]], None]:
    """Build a ChromaDB where clause for register metadata filtering.

    Registers are stored as individual boolean metadata fields (reg_AFIO_MAPR: True)
    during ingestion. Uses ChromaDB where clause with exact match on the boolean field.
    """
    if not register_name:
        return None, None
    return {f"reg_{register_name.upper()}": True}, None


def _expand_chunks(
    results: List[Dict[str, Any]],
    chunk_index_path: str,
    pages_after: int,
    table_pages_only: bool,
) -> List[Dict[str, Any]]:
    """Expand search results with chunks from contiguous pages.

    Args:
        results: Primary search results with page_number in metadata
        chunk_index_path: Path to chunks_index.csv
        pages_after: Number of pages to expand after each result's page
        table_pages_only: Only expand pages containing tables

    Returns:
        List of expansion chunk dicts with chunk_id, page_number, text
    """
    from context_retrieval.chunk_index import get_chunk_index

    try:
        chunk_index = get_chunk_index(chunk_index_path)
    except FileNotFoundError:
        return []

    # Collect pages from results
    result_pages = set()
    for result in results:
        page = result["metadata"].get("page_number", 0)
        if page > 0:
            result_pages.add(page)

    # Get expansion pages
    expansion_pages = set()
    for page in result_pages:
        contiguous = chunk_index.get_contiguous_pages(page, pages_after, table_pages_only)
        expansion_pages.update(contiguous)

    # Remove pages already covered by primary results
    expansion_pages -= result_pages

    if not expansion_pages:
        return []

    # Read expansion chunk content
    expansion_chunks = []
    for chunk_info in chunk_index.get_chunks_for_pages(sorted(expansion_pages)):
        text = chunk_index.read_chunk_content(chunk_info)
        if text:
            expansion_chunks.append({
                "chunk_id": chunk_info["chunk_id"],
                "page_number": chunk_info["page_number"],
                "text": text,
            })

    return expansion_chunks


def search_local_vector_db(
    query: str,
    db_name: str,
    n_results: int = 5,
    keyword_boost: bool = True,
    reranker_type: str = "",
    score_threshold: float = 0.0,
    db_path: str = "",
    embedding_provider: str = "local",
    register_filter: str = "",
    chunk_index_path: str = "",
    pages_after: int = 0,
    table_pages_only: bool = False,
) -> Tuple[Optional[str], List[Dict]]:
    """
    Search local ChromaDB and return results in hal_agent's (formatted_text, embedding_ids) format.

    Args:
        query: Search query string
        db_name: ChromaDB database name (e.g., "rm0041_md")
        n_results: Number of final results to return
        keyword_boost: Whether to apply keyword boosting
        reranker_type: Reranker to use ("", "local", "cohere", "bge")
        score_threshold: Minimum score threshold for results
        db_path: Override path to databases directory
        embedding_provider: "local" (FastEmbed) or "openai" - must match ingestion
        register_filter: Register name for metadata filtering (e.g., "FSMC_BTR1")
        chunk_index_path: Path to chunks_index.csv for chunk expansion
        pages_after: Number of pages to expand after each result
        table_pages_only: Only expand pages containing tables

    Returns:
        Tuple of (formatted_xml_string, embedding_ids_list)
        Returns (None, []) if no results found
    """
    store = _get_store(db_name, db_path, embedding_provider)

    # Expand candidate pool only for reranking (not for keyword boost)
    do_rerank = bool(reranker_type)
    fetch_k = n_results * 5 if do_rerank else n_results

    with timed_operation("vector_store_search"):
        # Tiered filtering: metadata → where_document → unfiltered
        # 1. Metadata filter (most precise): reg_REGISTER_NAME boolean field
        # 2. Document text filter (broader): $contains on chunk text
        # 3. Unfiltered (last resort)
        where_clause, _ = _build_register_filter(register_filter)
        reg_upper = register_filter.upper() if register_filter else ""

        results = None
        if where_clause is not None:
            results = store.search(query, n_results=fetch_k, where=where_clause)

        # Fallback to where_document if metadata filter returns nothing
        if not results and reg_upper:
            results = store.search(query, n_results=fetch_k,
                                   where_document={"$contains": reg_upper})

        # Fallback to unfiltered if both filters return nothing
        if not results:
            results = store.search(query, n_results=fetch_k)

        if not results:
            return None, []

        # Apply reranking if requested
        if do_rerank:
            reranker = get_reranker(reranker_type)
            results = reranker.rerank(query, results, top_n=fetch_k)

            # Quality fallback: if filtered results rerank poorly, try
            # where_document then unfiltered, picking the best scoring set
            if where_clause is not None and results and results[0]["score"] < 0.7:
                # Try where_document as middle ground
                doc_results = store.search(query, n_results=fetch_k,
                                           where_document={"$contains": reg_upper}) if reg_upper else []
                if doc_results:
                    doc_results = reranker.rerank(query, doc_results, top_n=fetch_k)
                    if doc_results[0]["score"] > results[0]["score"]:
                        results = doc_results

                # Try unfiltered as last resort
                if results[0]["score"] < 0.7:
                    unfiltered = store.search(query, n_results=fetch_k)
                    unfiltered = reranker.rerank(query, unfiltered, top_n=fetch_k)
                    if unfiltered and unfiltered[0]["score"] > results[0]["score"]:
                        results = unfiltered

        # Apply keyword boost
        if keyword_boost:
            results = store._apply_keyword_boost(query, results)

    # Apply score threshold
    if score_threshold > 0:
        results = [r for r in results if r["score"] >= score_threshold]

    # Trim to requested count
    results = results[:n_results]

    if not results:
        return None, []

    # Chunk expansion — only expand results that lack table content.
    # Register definitions always include bit field tables; a chunk without
    # a table likely has a split definition (header in one chunk, bit fields
    # on the next page). We expand only those chunks, leaving table-containing
    # chunks untouched to avoid adding noise.
    expansion_chunks = None
    if chunk_index_path and pages_after > 0:
        no_table_results = [r for r in results if not r["metadata"].get("has_tables", False)]
        if no_table_results:
            expansion_chunks = _expand_chunks(no_table_results, chunk_index_path, pages_after, table_pages_only)

    formatted_text = format_local_results(results, expansion_chunks)
    embedding_ids = extract_local_embedding_ids(results)

    return formatted_text, embedding_ids
