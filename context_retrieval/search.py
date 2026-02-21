"""
Unified search function for context retrieval.

Provides search_context() which handles both OpenAI file search and local
vector DB search, parameterised by ContextRetrievalParameters. This is the
single entry point that validators, coverage improvers, and other agents
should use for semantic search — rather than importing from
openai_file_search or local_vector_search directly.

For keyword-based retrieval (which requires device/PDF-specific logic),
use retrieve_context() from context_retrieval.retrieve_context instead.
"""

from typing import Optional, Tuple, List, Dict

from defs import ContextRetrievalParameters, ContextRetrievalMethod
from context_retrieval.openai_file_search import (
    search_vector_store, format_results, extract_embedding_ids,
    format_results_with_expansion
)
from context_retrieval.chunk_index import get_chunk_index
from context_retrieval.local_vector_search import search_local_vector_db


def search_context(
    query: str,
    context_retrieval_parameters: ContextRetrievalParameters,
    register_filter: str = "",
) -> Tuple[Optional[str], list]:
    """
    Run a semantic search against the configured backend and return formatted results.

    Args:
        query: The search query string.
        context_retrieval_parameters: Retrieval configuration (method, vs_id, etc.).
        register_filter: Register name for metadata filtering in local vector DB
                         (e.g. "FSMC_BTR1"). Ignored for OpenAI file search.

    Returns:
        (formatted_text, embedding_ids) — same shape as retrieve_context().
        formatted_text is None when no results are found.

    Raises:
        ValueError: If the configured method is KEYWORD_SEARCH or REGEX
                    (these require device-specific context; use retrieve_context()).
    """
    method = context_retrieval_parameters.context_retrieval_method

    if method == ContextRetrievalMethod.OPENAI_FILE_SEARCH:
        return _search_openai(query, context_retrieval_parameters)

    elif method == ContextRetrievalMethod.LOCAL_VECTOR_DB:
        return _search_local(query, context_retrieval_parameters, register_filter)

    elif method in (ContextRetrievalMethod.KEYWORD_SEARCH, ContextRetrievalMethod.REGEX):
        raise ValueError(
            f"search_context() does not support {method.value}. "
            "Use retrieve_context() for keyword/regex retrieval."
        )
    else:
        raise ValueError(f"Unknown context retrieval method: {method}")


def _search_openai(
    query: str,
    params: ContextRetrievalParameters,
) -> Tuple[Optional[str], list]:
    """OpenAI file search with optional chunk expansion."""
    num = max(1, min(params.number_embeddings, 50))

    results = search_vector_store(
        query, params.vs_id, num, params.re_ranking, params.score_threshold
    )
    if len(results.data) == 0:
        return None, []

    # Chunk expansion
    chunk_index = None
    expansion_enabled = params.chunk_expansion_enabled
    if expansion_enabled and params.chunk_index_path:
        try:
            chunk_index = get_chunk_index(params.chunk_index_path)
        except FileNotFoundError:
            expansion_enabled = False

    if chunk_index is not None and expansion_enabled:
        formatted = format_results_with_expansion(
            results,
            chunk_index=chunk_index,
            pages_after=params.pages_after,
            expansion_enabled=True,
            table_pages_only=params.expand_table_pages_only,
        )
    else:
        formatted = format_results(results)

    embedding_ids = extract_embedding_ids(results)
    return formatted, embedding_ids


def _search_local(
    query: str,
    params: ContextRetrievalParameters,
    register_filter: str = "",
) -> Tuple[Optional[str], list]:
    """Local ChromaDB vector search."""
    num = max(1, params.number_embeddings)

    return search_local_vector_db(
        query=query,
        db_name=params.local_db_name,
        n_results=num,
        keyword_boost=params.keyword_boost and num > 1,
        reranker_type=params.reranker_type,
        score_threshold=params.score_threshold,
        db_path=params.local_db_path,
        embedding_provider=params.local_embedding_provider,
        register_filter=register_filter if params.metadata_filter_enabled else "",
        chunk_index_path=params.chunk_index_path if params.chunk_expansion_enabled else "",
        pages_after=params.pages_after,
        table_pages_only=params.expand_table_pages_only,
    )
