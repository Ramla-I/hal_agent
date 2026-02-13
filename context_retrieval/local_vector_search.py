"""
Local vector database search using ChromaDB (via ../vector_db project).

Wraps vector_db's VectorStore API to match hal_agent's retrieve_context() interface,
returning (formatted_xml_string, embedding_ids_list).
"""

import os
import sys
import importlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from utils.timing import timed_operation

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# Path to the vector_db project (sibling directory)
_VECTOR_DB_PATH = str(Path(__file__).resolve().parent.parent.parent / "vector_db")

# Cached module references (loaded once via importlib)
_vector_store_mod = None
_reranker_mod = None
_vdb_config_mod = None

# Cached VectorStore instances: cache_key -> VectorStore
_store_cache: Dict[str, Any] = {}


def _ensure_vector_db_imports():
    """Import vector_db modules using importlib to avoid config.py name collision.

    Temporarily swaps sys.modules['config'] so that vector_db's internal
    `import config` resolves to vector_db/config.py instead of hal_agent/config.py.
    """
    global _vector_store_mod, _reranker_mod, _vdb_config_mod
    if _vector_store_mod is not None:
        return

    if not os.path.isdir(_VECTOR_DB_PATH):
        raise ImportError(
            f"vector_db project not found at {_VECTOR_DB_PATH}. "
            f"Expected it as a sibling directory to hal_agent."
        )

    # Save and remove hal_agent's config from sys.modules
    saved_config = sys.modules.pop("config", None)
    vdb_module_names = ["config", "vector_store", "embeddings", "chunking", "reranker"]
    saved_modules = {name: sys.modules.pop(name, None) for name in vdb_module_names}

    original_path = sys.path.copy()
    try:
        sys.path.insert(0, _VECTOR_DB_PATH)
        _vdb_config_mod = importlib.import_module("config")
        _vector_store_mod = importlib.import_module("vector_store")
        _reranker_mod = importlib.import_module("reranker")
    finally:
        sys.path = original_path
        # Remove vector_db's config from sys.modules to prevent collisions,
        # then restore hal_agent's config if it was previously imported
        sys.modules.pop("config", None)
        if saved_config is not None:
            sys.modules["config"] = saved_config


def _get_store(db_name: str, db_path: str = "", embedding_provider: str = "local") -> Any:
    """Get or create a cached VectorStore instance."""
    _ensure_vector_db_imports()

    cache_key = f"{db_name}:{db_path}:{embedding_provider}"
    if cache_key not in _store_cache:
        if db_path:
            _vdb_config_mod.DATABASES_DIR = Path(db_path)
        # Override embedding provider (vector_db's .env may default to "openai")
        _vdb_config_mod.EMBEDDING_PROVIDER = embedding_provider

        store = _vector_store_mod.VectorStore(db_name)
        _store_cache[cache_key] = store
    return _store_cache[cache_key]


def format_local_results(results: List[Dict[str, Any]]) -> str:
    """Format local search results in XML <sources> format matching semantic_search.py output."""
    if not results:
        return ""

    formatted_parts = []
    for i, result in enumerate(results):
        source = result["metadata"].get("source", "unknown")
        section = result["metadata"].get("section", "")
        score = result.get("score", 0)
        text = result["text"]
        formatted_parts.append(
            f"<result source='{source}' section='{section}' rank='{i}' score='{score:.3f}'>"
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
            "chunk_index": result["metadata"].get("chunk_index", -1),
            "rank": i,
            "score": float(result.get("score", 0)),
            "keyword_boost": float(result.get("keyword_boost", 0)),
        })
    return embedding_ids


def search_local_vector_db(
    query: str,
    db_name: str,
    n_results: int = 5,
    keyword_boost: bool = True,
    reranker_type: str = "",
    score_threshold: float = 0.0,
    db_path: str = "",
    embedding_provider: str = "local",
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

    Returns:
        Tuple of (formatted_xml_string, embedding_ids_list)
        Returns (None, []) if no results found
    """
    _ensure_vector_db_imports()

    store = _get_store(db_name, db_path, embedding_provider)

    # Expand candidate pool only for reranking (not for keyword boost).
    # Keyword boost should only reorder within the top-N semantically relevant
    # results, not pull in lower-ranked chunks that happen to mention the term.
    do_rerank = bool(reranker_type)
    fetch_k = n_results * 5 if do_rerank else n_results

    with timed_operation("vector_store_search"):
        results = store.search(query, n_results=fetch_k)

        if not results:
            return None, []

        # Apply reranking if requested
        if do_rerank:
            reranker = _reranker_mod.get_reranker(reranker_type)
            results = reranker.rerank(query, results, top_n=fetch_k)

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

    formatted_text = format_local_results(results)
    embedding_ids = extract_local_embedding_ids(results)

    return formatted_text, embedding_ids
