import os
import json
from prompts.query_rewriter import create_query_rewriter_file_search_query, create_query_rewriter_system_prompt, create_query_rewriter_user_prompt
from utils.parse_output import get_json_block_from_response, get_reasoning_from_response
from context_retrieval.semantic_search import search_vector_store, format_results
from config import client_groq
from utils.utils import setup_logger
from utils.result_saver import ResultSaver, UsageStats

logger = setup_logger(__name__)


def run_query_rewriter(
    original_query: str,
    peripheral_name: str,
    register_name: str,
    vs_id: str,
    output_dir: str
):
    """
    Runs the query rewriter agent for a given original query, peripheral name, register name, vs_id and output directory.
    Args:
        original_query: The original query to rewrite.
        peripheral_name: The name of the peripheral the register belongs to.
        register_name: The name of the register to rewrite the query for.
        vs_id: The id of the vs to use for the query rewrite.
        output_dir: The directory to output the query rewrite to.
    """

    model_name = "gpt-oss-120b"
    client = client_groq

    logger.info(
        "Running query rewriter for %s_%s",
        peripheral_name,
        register_name,
    )
    
    output_folder_path = os.path.join(output_dir, "query_rewrite")
    saver = ResultSaver(output_folder_path)

    file_search_query = create_query_rewriter_file_search_query(peripheral_name, f"{peripheral_name}_{register_name}", original_query)
    file_search = search_vector_store(file_search_query, vs_id, 4, True, 0.25)
    file_search = format_results(file_search)

    input_list = [
        {
            "role": "developer",
            "content": [
                {
                    "type": "input_text",
                    "text": create_query_rewriter_system_prompt()
                },
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": create_query_rewriter_user_prompt(peripheral_name, f"{peripheral_name}_{register_name}", original_query, file_search)
                },
            ]
        }
    ]

    response = client.responses.create(
        model="openai/gpt-oss-120b",
        input=input_list,
    )

    saver.save_text(
        f"---{peripheral_name}_{register_name}---\n{response.output_text}\n\n",
        "query_rewrite.txt",
        mode="a",
    )

    usage_stats = UsageStats.from_response_usage(model_name, response.usage)
    saver.save_usage_stats(
        usage_stats,
        "usage.csv",
        additional_fields={
            "peripheral_name": peripheral_name,
            "register_name": register_name,
        },
    )

    reasoning, rest_of_response = get_reasoning_from_response(response.output_text)
    json_block = get_json_block_from_response(rest_of_response)

    if json_block:
        try:
            json_data = json.loads(json_block)
            return json_data.get("rewritten_query", original_query)
        except Exception as e:
            logger.error(
                "Error loading JSON for %s: %s. JSON block: %s",
                register_name,
                e,
                json_block,
            )
            return original_query
    else:
        logger.warning("No JSON block found for %s", register_name)
        return original_query
   
if __name__ == "__main__":
    os.makedirs("query_rewriter_test", exist_ok=True)
    run_query_rewriter(
        original_query="Find the register layout information for the GPIOA_OTYPER register",
        peripheral_name="TIM2",
        register_name="CR2",
        vs_id = "vs_6892501067b08191ac63cc6de06ee629",
        output_dir="query_rewriter_test"
    )
