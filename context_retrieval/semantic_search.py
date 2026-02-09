import os
import sys

# HACK, remove this once we have a proper package structure
# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from config import client_openai
from utils.utils import setup_logger
from utils.timing import timed_operation
from context_retrieval.chunk_index import ChunkIndex, get_chunk_index

# Set up logger for this module
logger = setup_logger(__name__)

client = client_openai

# https://platform.openai.com/docs/guides/retrieval

def search_vector_store(query: str, vs_id: str, num_results: int, re_rank: bool, score_threshold: float):
    if re_rank:
        ranker = "auto"
    else:
        ranker = None

    # Truncate the query string to max 4096 characters (if necessary)
    if len(query) > 4096:
        logger.warning(f"Query is too long, truncating to 4096 characters. Original length: {len(query)}")
        query = query[:4096]

    with timed_operation("vector_store_search"):
        results = client.vector_stores.search(
            vector_store_id=vs_id,
            query=query,
            max_num_results=num_results,
            ranking_options={
                "ranker": ranker,
                "score_threshold": score_threshold,
            },
        )
    return results

def format_results(results):
    formatted_results = ''
    for result in results.data:
        formatted_result = f"<result file_id='{result.file_id}' file_name='{result.filename}'>"
        for part in result.content:
            formatted_result += f"<content>{part.text}</content>"
        formatted_results += formatted_result + "</result>"
    return f"<sources>{formatted_results}</sources>"

def extract_embedding_ids(results):
    """
    Extract unique identifiers for each embedding result.

    Returns:
        list of dicts with file_id, chunk_id (if available), and score
    """
    embedding_ids = []
    for idx, result in enumerate(results.data):
        embedding_info = {
            "file_id": result.file_id,
            "filename": result.filename,
            "rank": idx,
        }
        # Add score if available
        if hasattr(result, 'score'):
            embedding_info["score"] = result.score
        # Add chunk ID if available
        if hasattr(result, 'id'):
            embedding_info["chunk_id"] = result.id

        embedding_ids.append(embedding_info)

    return embedding_ids


def extract_pages_from_results(results) -> set:
    """
    Extract unique page numbers from semantic search results.

    Args:
        results: OpenAI vector store search results

    Returns:
        Set of page numbers (1-indexed)
    """
    import re
    pages = set()

    for result in results.data:
        filename = result.filename
        # Parse page from filename like 'rm0041_p187_c01.txt'
        match = re.search(r'_p(\d+)_c\d+', filename)
        if match:
            pages.add(int(match.group(1)))

    return pages


def expand_with_contiguous_chunks(
    results,
    chunk_index: ChunkIndex,
    pages_after: int = 2,
    table_pages_only: bool = False
) -> tuple[str, set]:
    """
    Expand semantic search results with chunks from subsequent pages.

    This addresses the issue where semantic search finds the right initial chunk
    but misses contiguous chunks on subsequent pages that contain related information
    (e.g., register bit field descriptions that span multiple pages).

    Args:
        results: OpenAI vector store search results
        chunk_index: ChunkIndex instance for page-to-chunk lookups
        pages_after: Number of pages to expand after each retrieved chunk (default: 2)
        table_pages_only: Only expand pages that contain tables (default: False)

    Returns:
        Tuple of (formatted_expansion_content, set_of_chunk_ids_added)
    """
    # Extract unique pages from search results
    result_pages = extract_pages_from_results(results)

    if not result_pages:
        logger.debug("No pages found in search results for expansion")
        return '', set()

    # Collect all chunk IDs from original results to avoid duplicates
    original_chunk_ids = set()
    for result in results.data:
        # Extract chunk_id from filename
        filename = result.filename
        chunk_id = filename.rsplit('.', 1)[0] if '.' in filename else filename
        original_chunk_ids.add(chunk_id)

    # Compute expansion pages (with optional table filter)
    expansion_pages = set()
    for page in result_pages:
        contiguous = chunk_index.get_contiguous_pages(page, pages_after, table_pages_only=table_pages_only)
        expansion_pages.update(contiguous)

    # Remove pages that are already in results
    expansion_pages -= result_pages

    if not expansion_pages:
        logger.debug("No additional pages to expand (all contiguous pages already in results)")
        return '', set()

    logger.info(f"Expanding with chunks from pages: {sorted(expansion_pages)}")

    # Get chunks for expansion pages
    expansion_chunks = chunk_index.get_chunks_for_pages(list(expansion_pages))

    # Filter out any chunks that are already in results
    new_chunks = [c for c in expansion_chunks if c['chunk_id'] not in original_chunk_ids]

    if not new_chunks:
        logger.debug("No new chunks to add after deduplication")
        return '', set()

    # Format expansion chunks
    formatted_expansion = ''
    added_chunk_ids = set()

    for chunk_info in new_chunks:
        chunk_id = chunk_info['chunk_id']
        content = chunk_index.read_chunk_content(chunk_info)

        if content:
            formatted_expansion += f"<result file_name='{chunk_id}.txt' expansion='true'>"
            formatted_expansion += f"<content>{content}</content>"
            formatted_expansion += "</result>"
            added_chunk_ids.add(chunk_id)

    logger.info(f"Added {len(added_chunk_ids)} chunks from contiguous page expansion")

    return formatted_expansion, added_chunk_ids


def format_results_with_expansion(
    results,
    chunk_index: ChunkIndex = None,
    pages_after: int = 2,
    expansion_enabled: bool = True,
    table_pages_only: bool = False
) -> str:
    """
    Format search results with optional contiguous chunk expansion.

    Args:
        results: OpenAI vector store search results
        chunk_index: ChunkIndex instance (required if expansion_enabled)
        pages_after: Number of pages to expand after each result
        expansion_enabled: Whether to include contiguous chunk expansion
        table_pages_only: Only expand pages that contain tables (default: False)

    Returns:
        Formatted string with results and expansion chunks wrapped in <sources>
    """
    # Format original results
    formatted_results = ''
    for result in results.data:
        formatted_result = f"<result file_id='{result.file_id}' file_name='{result.filename}'>"
        for part in result.content:
            formatted_result += f"<content>{part.text}</content>"
        formatted_results += formatted_result + "</result>"

    # Add expansion if enabled
    expansion_content = ''
    if expansion_enabled and chunk_index is not None:
        expansion_content, _ = expand_with_contiguous_chunks(
            results, chunk_index, pages_after, table_pages_only=table_pages_only
        )

    return f"<sources>{formatted_results}{expansion_content}</sources>"

def main():
    query = "What is the maximum speed of the STM32F100?"
    vs_id = "vs_6892501067b08191ac63cc6de06ee629"
    num_results = 10
    re_rank = True
    score_threshold = 0.15

    results = search_vector_store(query, vs_id, num_results, re_rank, score_threshold)
    formatted_results = format_results(results)


if __name__ == "__main__":
    main()