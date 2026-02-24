import os
import sys

# HACK, remove this once we have a proper package structure
# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from config import client_openai
from utils.utils import setup_logger
from utils.timing import timed_operation
from context_retrieval.chunk_index import ChunkIndex
from context_retrieval.post_processing import SearchResult

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


def normalize_openai_results(results, chunk_index: ChunkIndex = None) -> list[SearchResult]:
    """Convert OpenAI vector store search results to List[SearchResult].

    Args:
        results: OpenAI SDK search result object (has .data attribute)
        chunk_index: Optional ChunkIndex for has_tables metadata lookup

    Returns:
        List of SearchResult in the shared intermediate format.
    """
    import re as _re

    normalized: list[SearchResult] = []
    for idx, result in enumerate(results.data):
        text = "".join(part.text for part in result.content)

        # Extract page_number and chunk_id from filename (e.g. 'rm0041_p187_c01.txt')
        filename = result.filename or ""
        page_number = 0
        chunk_id = ""
        match = _re.search(r'_p(\d+)_c\d+', filename)
        if match:
            page_number = int(match.group(1))
        if '.' in filename:
            chunk_id = filename.rsplit('.', 1)[0]

        # Check has_tables from chunk_index metadata
        has_tables = False
        if chunk_index and chunk_id:
            has_tables = chunk_index.chunk_has_tables(chunk_id)

        normalized.append(SearchResult(
            text=text,
            score=result.score if hasattr(result, 'score') else 0.0,
            page_number=page_number,
            chunk_id=chunk_id,
            source=filename,
            has_tables=has_tables,
            metadata={
                "file_id": result.file_id,
                "file_name": filename,
            },
            rank=idx,
        ))
    return normalized


def main():
    query = "What is the maximum speed of the STM32F100?"
    vs_id = "vs_6892501067b08191ac63cc6de06ee629"
    num_results = 10
    re_rank = True
    score_threshold = 0.15

    results = search_vector_store(query, vs_id, num_results, re_rank, score_threshold)
    normalized = normalize_openai_results(results)
    print(f"Got {len(normalized)} results")


if __name__ == "__main__":
    main()