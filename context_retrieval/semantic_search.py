import os
import sys

# HACK, remove this once we have a proper package structure
# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from config import client_openai
from utils.utils import setup_logger
from utils.timing import timed_operation

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