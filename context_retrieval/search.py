"""
Unified search function for context retrieval.

Provides search_context() which handles both OpenAI file search and local
vector DB search, parameterised by ContextRetrievalParameters. This is the
single entry point that validators, coverage improvers, and other agents
should use for semantic search — rather than importing from
openai_file_search or local_vector_search directly.

Both backends produce raw results → normalize to SearchResult → feed into
a single post_process() pipeline (keyword boost, score threshold, trim,
expansion, table removal, XML formatting, embedding ID extraction).

For keyword-based retrieval (which requires device/PDF-specific logic),
use retrieve_context() from context_retrieval.retrieve_context instead.
"""

from typing import Optional, Tuple, List, Dict

from defs import ContextRetrievalParameters, ContextRetrievalMethod
from context_retrieval.openai_file_search import (
    search_vector_store, normalize_openai_results,
)
from context_retrieval.chunk_index import get_chunk_index
from context_retrieval.local_vector_search import (
    search_local_raw, normalize_local_results,
)
from context_retrieval.post_processing import SearchResult, post_process


def search_context(
    query: str,
    context_retrieval_parameters: ContextRetrievalParameters,
    register_filter: "str | list[str]" = "",
) -> Tuple[Optional[str], list]:
    """
    Run a semantic search against the configured backend and return formatted results.

    Args:
        query: The search query string.
        context_retrieval_parameters: Retrieval configuration (method, vs_id, etc.).
        register_filter: Register name (or list of names) for metadata filtering
                         in local vector DB (e.g. "FSMC_BTR1" or
                         ["FSMC_BTR1", "FSMC_BTR2"]). Ignored for OpenAI file search.

    Returns:
        (formatted_text, embedding_ids) — same shape as retrieve_context().
        formatted_text is None when no results are found.

    Raises:
        ValueError: If the configured method is KEYWORD_SEARCH or REGEX
                    (these require device-specific context; use retrieve_context()).
    """
    method = context_retrieval_parameters.context_retrieval_method

    if method == ContextRetrievalMethod.OPENAI_FILE_SEARCH:
        results = _search_openai(query, context_retrieval_parameters)

    elif method == ContextRetrievalMethod.LOCAL_VECTOR_DB:
        results = _search_local(query, context_retrieval_parameters, register_filter)

    elif method in (ContextRetrievalMethod.KEYWORD_SEARCH, ContextRetrievalMethod.REGEX):
        raise ValueError(
            f"search_context() does not support {method.value}. "
            "Use retrieve_context() for keyword/regex retrieval."
        )
    else:
        raise ValueError(f"Unknown context retrieval method: {method}")

    return post_process(results, context_retrieval_parameters, query)


def search_context_raw(
    query: str,
    context_retrieval_parameters: ContextRetrievalParameters,
    register_filter: "str | list[str]" = "",
) -> List[SearchResult]:
    """Like search_context() but returns raw SearchResult list (no post-processing).

    Useful when callers need to union results across multiple queries before
    applying a single post_process() pass.
    """
    method = context_retrieval_parameters.context_retrieval_method

    if method == ContextRetrievalMethod.OPENAI_FILE_SEARCH:
        return _search_openai(query, context_retrieval_parameters)

    elif method == ContextRetrievalMethod.LOCAL_VECTOR_DB:
        return _search_local(query, context_retrieval_parameters, register_filter)

    elif method in (ContextRetrievalMethod.KEYWORD_SEARCH, ContextRetrievalMethod.REGEX):
        raise ValueError(
            f"search_context_raw() does not support {method.value}. "
            "Use retrieve_context() for keyword/regex retrieval."
        )
    else:
        raise ValueError(f"Unknown context retrieval method: {method}")


def _search_openai(
    query: str,
    params: ContextRetrievalParameters,
) -> List[SearchResult]:
    """OpenAI file search → normalized SearchResult list."""
    num = max(1, min(params.number_embeddings, 50))

    results = search_vector_store(
        query, params.vs_id, num, params.re_ranking, params.score_threshold
    )
    if len(results.data) == 0:
        return []

    # Load chunk index for has_tables metadata (optional)
    chunk_index = None
    if params.chunk_index_path:
        try:
            chunk_index = get_chunk_index(params.chunk_index_path)
        except FileNotFoundError:
            pass

    return normalize_openai_results(results, chunk_index)


def _search_local(
    query: str,
    params: ContextRetrievalParameters,
    register_filter: "str | list[str]" = "",
) -> List[SearchResult]:
    """Local ChromaDB vector search → normalized SearchResult list."""
    num = max(1, params.number_embeddings)

    raw = search_local_raw(
        query=query,
        db_name=params.local_db_name,
        n_results=num,
        reranker_type=params.reranker_type,
        db_path=params.local_db_path,
        embedding_provider=params.local_embedding_provider,
        register_filter=register_filter if params.metadata_filter_enabled else "",
    )

    return normalize_local_results(raw)
