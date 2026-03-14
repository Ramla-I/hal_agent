"""
Local vector database search using ChromaDB (via context_retrieval.vector_db package).

Provides search_local_raw() for tiered metadata filtering + optional reranking,
and normalize_local_results() to convert raw results to the shared SearchResult format.
Post-processing (keyword boost, expansion, formatting) is handled by post_processing.py.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from utils.timing import timed_operation
from context_retrieval.vector_db import config as vdb_config
from context_retrieval.vector_db.vector_store import VectorStore
from context_retrieval.vector_db.reranker import get_reranker
from context_retrieval.post_processing import SearchResult


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


def _build_register_filter(register_names: "str | list[str]") -> tuple[Optional[Dict[str, Any]], None]:
    """Build a ChromaDB where clause for register metadata filtering.

    Registers are stored as individual boolean metadata fields (reg_AFIO_MAPR: True)
    during ingestion. Uses ChromaDB where clause with exact match on the boolean field.

    Accepts a single register name or a list of register names. When multiple names
    are provided, produces a ``$or`` clause so chunks matching *any* register are
    returned. Falls back to unfiltered search if the list exceeds 10 items (ChromaDB
    practical limit for ``$or`` clauses).
    """
    if not register_names:
        return None, None
    if isinstance(register_names, str):
        register_names = [register_names]
    register_names = [n for n in register_names if n]  # drop empty strings
    if not register_names:
        return None, None
    if len(register_names) == 1:
        return {f"reg_{register_names[0].upper()}": True}, None
    if len(register_names) > 10:
        # Too many clauses for ChromaDB $or — fall through to unfiltered search
        return None, None
    clauses = [{f"reg_{name.upper()}": True} for name in register_names]
    return {"$or": clauses}, None


def normalize_local_results(results: List[Dict[str, Any]]) -> List[SearchResult]:
    """Convert local ChromaDB search results to List[SearchResult].

    Args:
        results: List of dicts from VectorStore.search() with keys:
                 text, metadata (source, page_number, has_tables, section, etc.), score

    Returns:
        List of SearchResult in the shared intermediate format.
    """
    normalized: List[SearchResult] = []
    for i, result in enumerate(results):
        meta = result.get("metadata", {})
        normalized.append(SearchResult(
            text=result.get("text", ""),
            score=float(result.get("score", 0)),
            page_number=int(meta.get("page_number", 0)),
            chunk_id=meta.get("source", ""),
            source=meta.get("source", ""),
            has_tables=bool(meta.get("has_tables", False)),
            metadata={
                "section": meta.get("section", ""),
                "peripheral": meta.get("peripheral", ""),
                "chunk_type": meta.get("chunk_type", ""),
                "importance": meta.get("importance", ""),
                "chunk_index": meta.get("chunk_index", -1),
            },
            rank=i,
            keyword_boost=float(result.get("keyword_boost", 0)),
        ))
    return normalized


def search_local_raw(
    query: str,
    db_name: str,
    n_results: int = 5,
    reranker_type: str = "",
    db_path: str = "",
    embedding_provider: str = "local",
    register_filter: "str | list[str]" = "",
    fetch_k_multiplier: int = 5,
) -> List[Dict[str, Any]]:
    """Run tiered filtering + optional reranking on local ChromaDB.

    Returns the raw result dicts (text, metadata, score) WITHOUT keyword boost,
    score threshold, trim, expansion, or formatting. Those are handled by the
    shared post_process() pipeline.

    ``register_filter`` may be a single register name string or a list of
    register name strings (for batched / multi-register queries).
    """
    store = _get_store(db_name, db_path, embedding_provider)

    do_rerank = bool(reranker_type)
    fetch_k = n_results * fetch_k_multiplier if do_rerank else n_results

    with timed_operation("vector_store_search"):
        where_clause, _ = _build_register_filter(register_filter)

        # Build a $contains fallback string from the filter(s)
        if isinstance(register_filter, list):
            reg_upper = register_filter[0].upper() if register_filter else ""
        else:
            reg_upper = register_filter.upper() if register_filter else ""

        results = None
        if where_clause is not None:
            results = store.search(query, n_results=fetch_k, where=where_clause)

        if not results and reg_upper:
            results = store.search(query, n_results=fetch_k,
                                   where_document={"$contains": reg_upper})

        if not results:
            results = store.search(query, n_results=fetch_k)

        if not results:
            return []

        if do_rerank:
            reranker = get_reranker(reranker_type)
            results = reranker.rerank(query, results, top_n=fetch_k)

            if where_clause is not None and results and results[0]["score"] < 0.7:
                doc_results = store.search(query, n_results=fetch_k,
                                           where_document={"$contains": reg_upper}) if reg_upper else []
                if doc_results:
                    doc_results = reranker.rerank(query, doc_results, top_n=fetch_k)
                    if doc_results[0]["score"] > results[0]["score"]:
                        results = doc_results

                if results[0]["score"] < 0.7:
                    unfiltered = store.search(query, n_results=fetch_k)
                    unfiltered = reranker.rerank(query, unfiltered, top_n=fetch_k)
                    if unfiltered and unfiltered[0]["score"] > results[0]["score"]:
                        results = unfiltered

    return results


