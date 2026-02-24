"""
Shared post-processing pipeline for semantic search results.

Both OpenAI file search and local ChromaDB search normalize their raw results
into List[SearchResult], then feed them through post_process() which applies:
  1. Keyword boost (reorder by exact keyword match)
  2. Score threshold filtering
  3. Trim to n_results
  4. Chunk expansion (table-aware: only expand non-table results)
  5. Remove markdown tables from result text
  6. XML formatting
  7. Embedding ID extraction
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from defs import ContextRetrievalParameters
from utils.utils import setup_logger

logger = setup_logger(__name__)


@dataclass
class SearchResult:
    """Common intermediate format for search results from any backend."""
    text: str
    score: float
    page_number: int = 0
    chunk_id: str = ""
    source: str = ""
    has_tables: bool = False
    metadata: Dict = field(default_factory=dict)
    rank: int = 0
    keyword_boost: float = 0.0
    is_expansion: bool = False


# ---------------------------------------------------------------------------
# 1. Keyword boost
# ---------------------------------------------------------------------------

def _apply_keyword_boost(query: str, results: List[SearchResult]) -> List[SearchResult]:
    """Boost results that contain exact query keywords.

    Ported from VectorStore._apply_keyword_boost (vector_db/vector_store.py).
    Extracts REGISTER-style terms (e.g. AFIO_MAPR2, GPIO_CRL) and boosts
    results containing exact word-boundary matches.

    Boost tiers:
      +0.20  REGISTER DEFINITION match
      +0.10  KEY term match
      +0.05  body text match
    """
    term_pattern = r'\b([A-Z]{2,}[0-9]*_[A-Z0-9_]+)\b'
    query_terms = re.findall(term_pattern, query.upper())
    if not query_terms:
        return results

    boosted: List[SearchResult] = []
    for result in results:
        text_upper = result.text.upper()
        boost = 0.0
        for term in query_terms:
            exact_pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(exact_pattern, text_upper):
                if re.search(r'REGISTER DEFINITION:\s*' + re.escape(term) + r'\b', text_upper):
                    boost += 0.20
                elif "[KEY:" in result.text and re.search(exact_pattern, text_upper):
                    boost += 0.10
                else:
                    boost += 0.05

        new = SearchResult(
            text=result.text,
            score=result.score + boost,
            page_number=result.page_number,
            chunk_id=result.chunk_id,
            source=result.source,
            has_tables=result.has_tables,
            metadata=result.metadata,
            rank=result.rank,
            keyword_boost=boost,
            is_expansion=result.is_expansion,
        )
        boosted.append(new)

    boosted.sort(key=lambda x: x.score, reverse=True)
    return boosted


# ---------------------------------------------------------------------------
# 2. Score threshold
# ---------------------------------------------------------------------------

def _apply_score_threshold(results: List[SearchResult], threshold: float) -> List[SearchResult]:
    if threshold <= 0:
        return results
    return [r for r in results if r.score >= threshold]


# ---------------------------------------------------------------------------
# 3. Chunk expansion (table-aware)
# ---------------------------------------------------------------------------

def _expand_results(
    results: List[SearchResult],
    params: ContextRetrievalParameters,
) -> List[SearchResult]:
    """Expand search results with chunks from contiguous pages.

    Only expands results that lack table content — a chunk without a table
    likely has a split register definition (header in one chunk, bit fields
    on the next page).
    """
    if not params.chunk_index_path or params.pages_after <= 0:
        return []

    from context_retrieval.chunk_index import get_chunk_index

    try:
        chunk_index = get_chunk_index(params.chunk_index_path)
    except FileNotFoundError:
        return []

    # Only expand results without tables
    no_table_results = [r for r in results if not r.has_tables]
    if not no_table_results:
        return []

    # Collect pages from non-table results
    result_pages = {r.page_number for r in no_table_results if r.page_number > 0}
    # Also collect ALL result pages to avoid duplicating them in expansion
    all_result_pages = {r.page_number for r in results if r.page_number > 0}

    expansion_pages: set = set()
    for page in result_pages:
        contiguous = chunk_index.get_contiguous_pages(
            page, params.pages_after, table_pages_only=params.expand_table_pages_only,
        )
        expansion_pages.update(contiguous)

    # Remove pages already covered by primary results
    expansion_pages -= all_result_pages

    if not expansion_pages:
        return []

    # Collect original chunk_ids to avoid duplicates
    original_ids = {r.chunk_id for r in results if r.chunk_id}

    expansion_results: List[SearchResult] = []
    for chunk_info in chunk_index.get_chunks_for_pages(sorted(expansion_pages)):
        cid = chunk_info["chunk_id"]
        if cid in original_ids:
            continue
        text = chunk_index.read_chunk_content(chunk_info)
        if not text:
            continue
        expansion_results.append(SearchResult(
            text=text,
            score=0.0,
            page_number=chunk_info.get("page_number", 0),
            chunk_id=cid,
            source="expansion",
            is_expansion=True,
        ))

    logger.info(f"Expansion added {len(expansion_results)} chunks from pages {sorted(expansion_pages)}")
    return expansion_results


# ---------------------------------------------------------------------------
# 4. Remove markdown tables
# ---------------------------------------------------------------------------

def _remove_tables(results: List[SearchResult]) -> List[SearchResult]:
    """Strip markdown tables from result text."""
    from agent_tools.md_ops import remove_markdown_tables

    out: List[SearchResult] = []
    for r in results:
        out.append(SearchResult(
            text=remove_markdown_tables(r.text),
            score=r.score,
            page_number=r.page_number,
            chunk_id=r.chunk_id,
            source=r.source,
            has_tables=r.has_tables,
            metadata=r.metadata,
            rank=r.rank,
            keyword_boost=r.keyword_boost,
            is_expansion=r.is_expansion,
        ))
    return out


# ---------------------------------------------------------------------------
# 5. XML formatting
# ---------------------------------------------------------------------------

def format_results(
    results: List[SearchResult],
    expansion_results: Optional[List[SearchResult]] = None,
) -> str:
    """Format search results as XML <sources> string.

    Attributes are omitted when empty/zero to keep output clean.
    """
    if not results and not expansion_results:
        return ""

    parts: List[str] = []

    for i, r in enumerate(results):
        attrs = _build_attrs(r, i)
        parts.append(f"<result {attrs}><content>{r.text}</content></result>")

    if expansion_results:
        for r in expansion_results:
            attrs = _build_attrs(r)
            parts.append(f"<result {attrs}><content>{r.text}</content></result>")

    return f"<sources>{''.join(parts)}</sources>"


def _build_attrs(r: SearchResult, rank: Optional[int] = None) -> str:
    """Build XML attribute string for a SearchResult, omitting empty values."""
    pairs: List[Tuple[str, str]] = []
    if r.source:
        pairs.append(("source", r.source))
    if r.metadata.get("file_id"):
        pairs.append(("file_id", r.metadata["file_id"]))
    if r.metadata.get("file_name"):
        pairs.append(("file_name", r.metadata["file_name"]))
    if r.metadata.get("section"):
        pairs.append(("section", r.metadata["section"]))
    if r.metadata.get("peripheral"):
        pairs.append(("peripheral", r.metadata["peripheral"]))
    if r.metadata.get("chunk_type"):
        pairs.append(("chunk_type", r.metadata["chunk_type"]))
    if r.chunk_id:
        pairs.append(("chunk_id", r.chunk_id))
    if r.page_number:
        pairs.append(("page", str(r.page_number)))
    if rank is not None:
        pairs.append(("rank", str(rank)))
    if r.score:
        pairs.append(("score", f"{r.score:.3f}"))
    if r.is_expansion:
        pairs.append(("expansion", "true"))
    return " ".join(f"{k}='{v}'" for k, v in pairs)


# ---------------------------------------------------------------------------
# 6. Embedding ID extraction
# ---------------------------------------------------------------------------

def extract_embedding_ids(results: List[SearchResult]) -> List[Dict]:
    """Extract tracking metadata from results — unified across backends."""
    ids: List[Dict] = []
    for i, r in enumerate(results):
        entry: Dict = {"rank": i, "score": float(r.score)}
        if r.source:
            entry["source"] = r.source
        if r.chunk_id:
            entry["chunk_id"] = r.chunk_id
        if r.page_number:
            entry["page_number"] = r.page_number
        if r.keyword_boost:
            entry["keyword_boost"] = float(r.keyword_boost)
        # Include all backend-specific metadata
        for k, v in r.metadata.items():
            if k not in entry and v not in (None, "", 0, -1):
                entry[k] = v
        ids.append(entry)
    return ids


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def post_process(
    results: List[SearchResult],
    params: ContextRetrievalParameters,
    query: str,
) -> Tuple[Optional[str], List[Dict]]:
    """Shared post-processing pipeline for semantic search results.

    Steps (each controlled by ContextRetrievalParameters fields):
      1. Keyword boost  (params.keyword_boost)
      2. Score threshold (params.score_threshold) — no-op for OpenAI (already filtered)
      3. Trim to n       (params.number_embeddings) — no-op for OpenAI (already limited)
      4. Chunk expansion (params.chunk_expansion_enabled, params.pages_after, etc.)
      5. Remove tables   (params.remove_tables)
      6. Format to XML
      7. Extract embedding IDs

    Returns:
        (formatted_xml, embedding_ids) — same shape as search_context().
    """
    if not results:
        return None, []

    # 1. Keyword boost
    if params.keyword_boost:
        results = _apply_keyword_boost(query, results)

    # 2. Score threshold
    results = _apply_score_threshold(results, params.score_threshold)

    # 3. Trim to requested count
    n = max(1, params.number_embeddings)
    results = results[:n]

    if not results:
        return None, []

    # 4. Chunk expansion
    expansion_results: List[SearchResult] = []
    if params.chunk_expansion_enabled:
        expansion_results = _expand_results(results, params)

    # 5. Remove tables (applies to both primary and expansion results)
    if params.remove_tables:
        results = _remove_tables(results)
        if expansion_results:
            expansion_results = _remove_tables(expansion_results)

    # 6. Format to XML
    formatted = format_results(results, expansion_results)

    # 7. Extract embedding IDs (primary results only)
    embedding_ids = extract_embedding_ids(results)

    return formatted, embedding_ids
