import os
import json
from typing import Optional, Dict, List
from defs import ContextRetrievalParameters, Manufacturer, ContextRetrievalMethod
from agent_tools.tools import all_svd_file_paths, calculate_address_offset
from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral
from prompts.register_info_stm import create_register_info_stm_system_prompt, create_register_info_stm_user_prompt
from utils.parse_output import get_json_block_from_response, get_reasoning_from_response
from utils.function_call_handler import create_default_handler
from utils.utils import get_model_string, setup_logger
from utils.result_saver import ResultSaver, UsageStats
from context_retrieval.retrieve_context import retrieve_context
from scripts.limit_context import truncate_message_by_tokens
from groq import Groq
from openai import OpenAI

logger = setup_logger(__name__)
def run_generator(
    client: OpenAI|Groq,
    model_name: str,
    device_name: str, 
    run_number: int, 
    device_dir: str, 
    agent_output_dir: str,
    context_retrieval_parameters: ContextRetrievalParameters,
    manufacturer: Manufacturer,
    peripherals_registers_dict: Optional[Dict[str, List[str]]] = None
) -> bool:
    """
    Runs the generator agent for a given device and run number.
    Args:
        device_name: The name of the device to run the generator for.
        run_number: The run number to run the generator for.
        device_dir: The path to the datasheet file for the device.
        agent_output_dir: The directory to output the agent's output to.
        model_name: The name of the model to use for the generator.
        context_retrieval_parameters: The context retrieval parameters to use for the generator.
        manufacturer: The manufacturer of the device.
        peripherals_registers_dict: Optional dict mapping peripheral names to lists of register names.
            Format: {peripheral_name: [register_name1, register_name2, ...]}
            If None, all peripherals and registers will be extracted from SVD files.
    """
    logger.info(f"Running generator for device {device_name} with run number {run_number}")

    run_number = str(run_number)
    truncated_at_any_register = False

    saver_info = ResultSaver(os.path.join(agent_output_dir, "info"))
    saver_output = ResultSaver(agent_output_dir)

    summary_content = (
        f"MODEL: {model_name}\n"
    )
    saver_info.save_text(summary_content, "summary.txt")

    # Initialize function call handler
    function_handler = create_default_handler()
    
    # Get the name of each register to find in the datasheet, that is our prompt granularity
    if peripherals_registers_dict is None:
        # Extract all peripherals and registers from SVD files
        svd_file_paths = all_svd_file_paths(device_dir)
        peripheral_names = get_peripheral_names(svd_file_paths)

        register_names_to_process = {peripheral_name: [] for peripheral_name in peripheral_names}
        for peripheral_name in peripheral_names:
            register_names = get_register_names_for_peripheral(svd_file_paths, peripheral_name)
            register_names_to_process[peripheral_name].extend(register_names)
        
        logger.info(f"Found registers for {len(register_names_to_process)} peripherals")
    else:
        # Use provided dict of peripherals and registers
        register_names_to_process = peripherals_registers_dict
        logger.info(f"Using provided dict with {len(register_names_to_process)} peripherals")
    
    # Now the Context Retrieval Part
    for peripheral_name in register_names_to_process.keys():
        for register_name in register_names_to_process[peripheral_name]:
            logger.debug(f"Processing {peripheral_name}_{register_name}")
            usage = []
            # check if output file exists, if so assume the agent already processed it, skip to the next register
            output_filename = f"{peripheral_name}_{register_name}"
            output_path = os.path.join(agent_output_dir, output_filename)
            if os.path.exists(output_path):
                continue
            
            datasheet_pages = retrieve_context(context_retrieval_parameters, device_name, device_dir, peripheral_name, register_name, manufacturer, agent_output_dir)
            if datasheet_pages is None:
                continue
            
            input_list = [
                {
                    "role": "developer",
                    "content": create_register_info_stm_system_prompt()
                },
                {
                    "role": "user",
                    "content": create_register_info_stm_user_prompt(register_name, peripheral_name, datasheet_pages)
                }
            ]
            truncated, input_list = truncate_message_by_tokens(input_list, model_name)
            truncated_at_any_register = truncated_at_any_register or truncated

            if truncated:
                logger.info(f"Truncated input list for {peripheral_name}_{register_name}")

            response = client.responses.create(
                # messages=messages,
                model=get_model_string(model_name),
                input=input_list,
                tool_choice = "none",
                truncation="auto",
                # tools=tools,
            )

            if response.output_text:
                input_list.append({
                    "role": "assistant",
                    "content": response.output_text
                })
            
            # logger.debug(f"Response")
            # for el in response.output:
            #     logger.debug(f"el: {el} \n\n")   

            # input_list += [{"role": el.role, "content": el.content} for el in response.output if el.type == "message"]
            
            reasoning, rest_of_response = get_reasoning_from_response(response.output_text)
            json_block = get_json_block_from_response(rest_of_response)
            usage.append(response.usage)

            # Process function calls using the abstraction
            function_results = function_handler.process_function_calls(rest_of_response)
            if function_results:
                for result in function_results:
                    logger.debug(f"FUNCTION CALL: {result.function_name} - Success: {result.success}")
                    if not result.success:
                        logger.error(
                            "Error in function call for %s: %s",
                            register_name,
                            result.error_message,
                        )
                    else:
                        logger.debug(
                            "Success in function call for %s: %s",
                            register_name,
                            result.result,
                        )
                                        
                    # Add the result message to the input list for the next response
                    input_list.append({
                        "role": "user",
                        "content": result.message
                    })

                truncated, input_list = truncate_message_by_tokens(input_list, model_name)
                truncated_at_any_register = truncated_at_any_register or truncated

                if truncated:
                    logger.info(f"Truncated input list for {peripheral_name}_{register_name} after function calls")

                # Get response after function calls
                response = client.responses.create(
                    model=get_model_string(model_name),
                    input=input_list,
                    tool_choice = "none",
                    truncation="auto",
                    # tools=tools,
                )
                reasoning, rest_of_response = get_reasoning_from_response(response.output_text)
                json_block = get_json_block_from_response(rest_of_response)
                usage.append(response.usage)

            total_input_tokens = sum(usage[i].input_tokens for i in range(len(usage)))
            total_cached_tokens = sum(usage[i].input_tokens_details.cached_tokens for i in range(len(usage)))
            total_output_tokens = sum(usage[i].output_tokens for i in range(len(usage)))
            total_reasoning_tokens = sum(usage[i].output_tokens_details.reasoning_tokens for i in range(len(usage)))
            total_total_tokens = sum(usage[i].total_tokens for i in range(len(usage)))
            usage_stats = UsageStats(
                model_name=model_name,
                input_tokens=total_input_tokens,
                cached_tokens=total_cached_tokens,
                output_tokens=total_output_tokens,
                reasoning_tokens=total_reasoning_tokens,
                total_tokens=total_total_tokens,
            )
            saver_info.save_usage_stats(
                usage_stats,
                "usage.csv",
                additional_fields={
                    "peripheral_name": peripheral_name,
                    "register_name": register_name,
                },
            )
            saver_info.save_reasoning(
                reasoning,
                "reasoning.txt",
                prefix=f"---{peripheral_name}_{register_name}---",
            )

            if json_block:
                try:
                    json_data = json.loads(json_block)
                except Exception as e:
                    logger.error(
                        "Error loading JSON for %s: %s. JSON block: %s",
                        register_name,
                        e,
                        json_block,
                    )
                    json_data = None
            else:
                json_data = None

            if json_data:
                saver_output.save_json(json_data, output_filename)

    return truncated_at_any_register


if __name__ == "__main__":
    import config

    context_retrieval_parameters = ContextRetrievalParameters(
        context_retrieval_method=ContextRetrievalMethod.SEMANTIC_SEARCH, 
        pages_after_keyword=2, 
        remove_tables=True, 
        number_embeddings=16, 
        re_ranking=True,
        score_threshold=0.25,
        query_rewrite=True,
        vs_id="vs_6892501067b08191ac63cc6de06ee629",
        regex="", 
        other=""
    )
    output_dir = "generator_test"
    os.makedirs(output_dir, exist_ok=True)
    truncated_at_any_register = run_generator(
        device_name="rm0041",
        run_number=1,
        device_dir="devices/stm/rm0041",
        agent_output_dir=output_dir,
        model_name="gpt-oss-120b",
        context_retrieval_parameters = context_retrieval_parameters,
        manufacturer=Manufacturer.STM,
        peripherals_registers_dict={
            "DMA": ["CCR2"],
        }
    )