import os
import json

import config
from config import client_groq, client_openai
from utils.utils import get_model_string, setup_logger
from utils.timing import timed_operation
from defs import CoverageImproverOutput, ContextRetrievalParameters, CoverageInfo, ContextRetrievalMethod
from prompts import coverage_improver as prompts
from utils.parse_output import get_json_block_from_response, get_reasoning_from_response
from utils.result_saver import ResultSaver, UsageStats
from context_retrieval.semantic_search import search_vector_store, format_results
from scripts.limit_context import truncate_message_by_tokens
from groq import Groq
from openai import OpenAI

# Set up logger for this module
logger = setup_logger(__name__)

def run_coverage_improver(
    client: Groq|OpenAI, 
    model_name: str, 
    coverage_info: CoverageInfo, 
    context_retrieval_parameters: ContextRetrievalParameters, 
    output_dir: str, 
    vs_id: str, 
    reasoning_effort: str | None = None, 
    generator_truncated_at_any_register: bool = False
):
    logger.info(f"Running coverage improver for {model_name}")

    # If the expected output files already exist, return early
    output_json = os.path.join(output_dir, "coverage_improver_output.json")
    coverage_info_json = os.path.join(output_dir, "coverage_info.json")

    if os.path.exists(output_json) and os.path.exists(coverage_info_json):
        logger.info(f"Output files already exist for {output_json} and {coverage_info_json}. Skipping.")
        return

    # Create file search query and perform file search
    query = prompts.create_coverage_improver_file_search_query(coverage_info, context_retrieval_parameters)
    file_search = search_vector_store(query, vs_id, 4, True, 0.25)
    file_search = format_results(file_search)
    
    # Build input list for responses API
    input_list = [
        {
            "role": "developer",
            "content": prompts.create_coverage_improver_system_prompt()
        }
    ]
    
    input_list.append(
        {
            "role": "user",
            "content": prompts.create_coverage_improver_user_prompt(coverage_info, context_retrieval_parameters, generator_truncated_at_any_register, file_search)
        }
    )

    truncated, input_list = truncate_message_by_tokens(input_list, model_name)
    if truncated:
        logger.info(f"Truncated input list for coverage improver")

    # Call responses API
    with timed_operation("coverage_improver_llm_call"):
        if reasoning_effort is not None:
            response = client.responses.create(
                model=get_model_string(model_name),
                reasoning={"effort": reasoning_effort},
                input=input_list,
            )
        else:
            response = client.responses.create(
                model=get_model_string(model_name),
                input=input_list,
            )

    # Parse JSON response
    reasoning, rest_of_response = get_reasoning_from_response(response.output_text)
    json_block = get_json_block_from_response(rest_of_response)

    output = CoverageImproverOutput(
        context_retrieval_parameters=context_retrieval_parameters,
        reasoning="Failed to parse JSON block",
        stop_improving=True
    )

    if json_block is not None:
        try:
            json_data = json.loads(json_block)
            # Create CoverageImproverOutput from JSON
            output = CoverageImproverOutput(**json_data)
        except Exception as e:
            logger.error(f"Error parsing JSON block: {e}")
            logger.error(f"JSON block: {json_block}")
    else:
        logger.error("No JSON block found in response")

    saver = ResultSaver(output_dir)

    saver.save_json(output, "coverage_improver_output.json")
    saver.save_json(coverage_info, "coverage_info.json")

    if reasoning:
        saver.save_text(reasoning, "reasoning.txt")

    usage_stats = UsageStats.from_response_usage(model_name, response.usage)
    saver.save_usage_stats(usage_stats, "usage.csv")
    
    return output


if __name__ == "__main__":
    # Test function for coverage improver
    model_name = config.COVERAGE_IMPROVER_MODEL_NAME
    reasoning_effort = config.COVERAGE_IMPROVER_REASONING_EFFORT
    client = client_openai
    
    # Use config values for test of RM0041
    vs_id = config.CONTEXT_RETRIEVAL_PARAMETERS.vs_id
    output_dir = os.path.join(config.OUTPUT_DIR, "coverage_improver_test")
    os.makedirs(output_dir, exist_ok=True)
    
    # Create sample coverage info for testing
    coverage_info = CoverageInfo(
        peripheral_coverage=75.5,
        register_coverage=60.0,
        field_coverage=45.0,
        peripherals_only_in_svd=["TIM1", "UART2"],
        peripherals_only_in_agent_output=[],
        peripherals_present_in_both=["GPIO", "SPI1"],
        registers_only_in_svd={"GPIO": ["GPIOA_CRL", "GPIOA_CRH"]},
        registers_only_in_agent_output={},
        registers_present_in_both={"GPIO": ["GPIOA_IDR", "GPIOA_ODR"]},
        fields_only_in_svd={"GPIO": {"GPIOA_IDR": ["IDR0", "IDR1"]}},
        fields_only_in_agent_output={},
        fields_present_in_both={"GPIO": {"GPIOA_IDR": ["IDR15"]}}
    )

    # Use config context retrieval parameters
    context_retrieval_parameters = config.CONTEXT_RETRIEVAL_PARAMETERS
    
    print(f"Running coverage improver test with model {model_name}")
    print(f"Output directory: {output_dir}")
    
    try:
        result = run_coverage_improver(
            client=client,
            model_name=model_name,
            coverage_info=coverage_info,
            context_retrieval_parameters=context_retrieval_parameters,
            output_dir=output_dir,
            vs_id=vs_id,
            reasoning_effort=reasoning_effort
        )
        print(f"Test completed successfully!")
        print(f"Stop improving: {result.stop_improving}")
        print(f"Output saved to: {output_dir}")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise

