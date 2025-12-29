import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# https://platform.openai.com/docs/guides/retrieval

def search_vector_store(query: str, vs_id: str, num_results: int, re_rank: bool, score_threshold: float):
    if re_rank:
        ranker = "auto"
    else:
        ranker = None

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

def main():
    query = "What is the maximum speed of the STM32F100?"
    vs_id = "vs_6892501067b08191ac63cc6de06ee629"
    num_results = 10
    re_rank = True
    
    results = search_vector_store(query, vs_id, num_results, re_rank)
    formatted_results = format_results(results)


if __name__ == "__main__":
    main()