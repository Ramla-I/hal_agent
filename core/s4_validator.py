from agents import Agent, Runner, GuardrailFunctionOutput, InputGuardrail, FunctionTool, function_tool, RunContextWrapper, handoff, FileSearchTool
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import asyncio  
import os
import json
import csv

import config
from config import client_groq, client_openai
from utils.parse_output import get_json_block_from_response
from utils.utils import get_model_string
from groq import Groq
from openai import OpenAI
from defs import UserContext, RegisterList, Manufacturer, RegisterNameList, RegisterInfo,  EnumValue, BitNumber, BitField
from prompts.validator import (
    create_validator_system_prompt,
    create_validator_file_search_query,
    create_validator_user_prompt,
    create_batched_validator_system_prompt,
    create_batched_validator_file_search_query,
    create_batched_validator_user_prompt
)
from context_retrieval.semantic_search import search_vector_store, format_results
from utils.result_saver import ResultSaver, UsageStats
from utils.utils import setup_logger
from utils.timing import timed_operation
import tiktoken

logger = setup_logger(__name__)

def build_invariants_from_agent_output(agent_output_dir: str):
    """
    Build a list of invariant dicts from an agent output directory.
    Expected invariant format:
        {
            'peripheral_name': str,
            'register_name': str,
            'field_name': str,
            'key': str,
            'value': str
        }
    """
    invariants = []
    skip_dirs = {"info", "coverage_improver", "query_rewrite", "analyzer_iteration"}

    for name in sorted(os.listdir(agent_output_dir)):
        path = os.path.join(agent_output_dir, name)
        if os.path.isdir(path):
            if name in skip_dirs:
                continue
            # Skip all directories; only parse register JSON files
            continue
        if name.endswith(".csv") or name.endswith(".txt"):
            continue
        if "_" not in name:
            continue

        peripheral_name, register_name = name.split("_", 1)

        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception:
            continue

        # Register-level invariants
        if "address_offset" in data:
            invariants.append({
                "peripheral_name": peripheral_name,
                "register_name": register_name,
                "field_name": "",
                "key": "address_offset",
                "value": str(data.get("address_offset"))
            })
        if "reset_value" in data:
            invariants.append({
                "peripheral_name": peripheral_name,
                "register_name": register_name,
                "field_name": "",
                "key": "reset_value",
                "value": str(data.get("reset_value"))
            })
        if "size" in data:
            invariants.append({
                "peripheral_name": peripheral_name,
                "register_name": register_name,
                "field_name": "",
                "key": "size",
                "value": str(data.get("size"))
            })

        # Field-level invariants
        if "subfields" in data:
            for field in data.get("subfields", []) or []:
                field_name = field.get("name", "")
                bit_number = field.get("bit_number", {}) or {}
                start_bit = bit_number.get("start_bit")
                end_bit = bit_number.get("end_bit")
                if start_bit is not None:
                    invariants.append({
                        "peripheral_name": peripheral_name,
                        "register_name": register_name,
                        "field_name": field_name,
                        "key": "bit_offset",
                        "value": str(start_bit)
                    })
                if start_bit is not None and end_bit is not None:
                    start_bit = int(start_bit)
                    end_bit = int(end_bit)
                    if start_bit > end_bit:
                        start_bit, end_bit = end_bit, start_bit

                    bit_width = end_bit - start_bit + 1
                    invariants.append({
                        "peripheral_name": peripheral_name,
                        "register_name": register_name,
                        "field_name": field_name,
                        "key": "bit_width",
                        "value": str(bit_width)
                    })
                if field.get("access") is not None:
                    invariants.append({
                        "peripheral_name": peripheral_name,
                        "register_name": register_name,
                        "field_name": field_name,
                        "key": "access",
                        "value": str(field.get("access"))
                    })

    return invariants


def run_validator(
    client: OpenAI|Groq,
    model_name: str,
    invariants,
    output_dir: str,
    vs_id: str,
    reasoning_effort: str | None = None
):
    """
    Run the validator on a list of invariants for a given peripheral and register.

    Args:
        client: The LLM client (OpenAI or Groq)
        model_name: The name of the model to use
        invariants: List of invariant dicts to validate.
            Each invariant should be a dict with the following keys:
                'peripheral_name': str,
                'register_name': str,
                'field_name': str,
                'key': str,
                'value': str
        output_dir: Path to directory for storing output
        vs_id: Vector store ID for semantic search
        reasoning_effort: (Optional) string indicating effort for LLM reasoning

    Returns:
        (total_true, total_false): Tuple of total 'true' judgements and 'false' judgements

    Example of 'invariants' argument:
        [
            {
                'peripheral_name': 'afio',
                'register_name': 'evcr',
                'field_name': '',
                'key': 'address_offset',
                'value': '0x0'
            },
            {
                'peripheral_name': 'afio',
                'register_name': 'evcr',
                'field_name': 'evoe',
                'key': 'bit_offset',
                'value': '7'
            },
            ...
        ]
    """
    total_true = 0
    total_false = 0

    # Initialize ResultSaver for all file operations
    saver = ResultSaver(output_dir)
    
    # Define file names
    classification_csv_name = "classification.csv"
    usage_csv_name = "usage.csv"
    output_txt_name = "output.txt"

    classification_csv_path = os.path.join(output_dir, classification_csv_name)
    usage_csv_path = os.path.join(output_dir, usage_csv_name)
    output_txt_path = os.path.join(output_dir, output_txt_name)
    # if (
    #     os.path.exists(classification_csv_path)
    #     and os.path.exists(usage_csv_path)
    #     and os.path.exists(output_txt_path)
    # ):
    #     logger.info(f"Output files already exist for validator in {output_dir}. Skipping.")
    #     return total_true, total_false
    
    logger.info(f"Running validator for {len(invariants)} invariants")

    for invariant in invariants:
        peripheral_name = invariant['peripheral_name']
        register_name = invariant['register_name']
        field_name = invariant['field_name']
        key = invariant['key']
        value = invariant['value']
        
        input_list = [
            {
                "role": "developer",
                "content": [
                    {
                        "type": "input_text",
                        "text": create_validator_system_prompt()
                    },
                ]
            }
        ]
        
        query = create_validator_file_search_query(peripheral_name, register_name, field_name, key, value)
        file_search = search_vector_store(query, vs_id, 4, True, 0.25)
        file_search = format_results(file_search)

        # Count tokens in file search results
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            file_search_tokens = len(encoding.encode(file_search))
        except Exception as e:
            logger.warning(f"Could not count file search tokens: {e}")
            file_search_tokens = 0

        input_list.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": create_validator_user_prompt(peripheral_name, register_name, field_name, key, value, file_search)
                    }
                ]
            }
        )

        with timed_operation("validator_llm_call"):
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

        # Save output text
        saver.append_text(f"---{peripheral_name}_{register_name}_{field_name}_{key}_{value}---\n{response.output_text}\n\n", output_txt_name)

        json_block = get_json_block_from_response(response.output_text)
        if json_block is not None:
            try:
                json_data = json.loads(json_block)
                
                # Save validator output row
                saver.save_csv_row(
                    {
                        'peripheral_name': peripheral_name,
                        'register_name': register_name,
                        'field_name': field_name,
                        'key': key,
                        'value': value,
                        'agent_judgement': json_data['is_true'],
                        'confidence_score': json_data['confidence_score']
                    },
                    classification_csv_name
                )
                
                agent_judgement = True if json_data['is_true'] == True else False
                if agent_judgement == True:
                    total_true += 1
                else:
                    total_false += 1
            
            except Exception as e:
                logger.error(f"Error parsing JSON block for peripheral {peripheral_name}, register {register_name}, field {field_name}, key {key}, value {value}: {e}")

        # Save usage statistics
        usage_stats = UsageStats.from_response_usage(model_name, response.usage, file_search_tokens)
        saver.save_usage_stats(
            usage_stats,
            usage_csv_name,
            additional_fields={
                'peripheral_name': peripheral_name,
                'register_name': register_name,
                'field_name': field_name,
                'key': key
            }
        )
    
    logger.info(f"Total true: {total_true}, Total false: {total_false}")
    return total_true, total_false


def run_validator_batched(
    client: OpenAI|Groq,
    model_name: str,
    invariants,
    output_dir: str,
    vs_id: str,
    reasoning_effort: str | None = None
):
    """
    Run the validator on invariants, batching by register.
    All invariants for the same (peripheral, register) are validated in a single API call.

    Args:
        client: The LLM client (OpenAI or Groq)
        model_name: The name of the model to use
        invariants: List of invariant dicts to validate
        output_dir: Path to directory for storing output
        vs_id: Vector store ID for semantic search
        reasoning_effort: (Optional) string indicating effort for LLM reasoning

    Returns:
        (total_true, total_false): Tuple of total 'true' and 'false' judgements
    """
    total_true = 0
    total_false = 0

    # Initialize ResultSaver
    saver = ResultSaver(output_dir)

    # Define file names
    classification_csv_name = "classification.csv"
    usage_csv_name = "usage.csv"
    output_txt_name = "output.txt"

    # Group invariants by (peripheral_name, register_name)
    from collections import defaultdict
    batches = defaultdict(list)

    for inv in invariants:
        key = (inv['peripheral_name'], inv['register_name'])
        batches[key].append(inv)

    logger.info(f"Batched {len(invariants)} invariants into {len(batches)} register batches")

    # Process each batch
    for (peripheral_name, register_name), batch_invariants in batches.items():
        logger.debug(f"Processing batch for {peripheral_name}_{register_name} ({len(batch_invariants)} invariants)")

        # Single file search for the entire register
        query = create_batched_validator_file_search_query(peripheral_name, register_name)
        file_search = search_vector_store(query, vs_id, 4, True, 0.25)
        file_search = format_results(file_search)

        # Count tokens in file search results
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            file_search_tokens = len(encoding.encode(file_search))
        except Exception as e:
            logger.warning(f"Could not count file search tokens: {e}")
            file_search_tokens = 0

        # Build input for batched validation
        input_list = [
            {
                "role": "developer",
                "content": [
                    {
                        "type": "input_text",
                        "text": create_batched_validator_system_prompt()
                    },
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": create_batched_validator_user_prompt(
                            peripheral_name,
                            register_name,
                            batch_invariants,
                            file_search
                        )
                    }
                ]
            }
        ]

        # Single LLM call for all invariants in this register
        with timed_operation("validator_llm_call"):
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

        # Save output text
        saver.append_text(
            f"---{peripheral_name}_{register_name}---\n{response.output_text}\n\n",
            output_txt_name
        )

        # Parse JSON response
        json_block = get_json_block_from_response(response.output_text)
        if json_block is not None:
            try:
                results = json.loads(json_block)

                if not isinstance(results, list):
                    logger.error(f"Expected list of results, got {type(results)}")
                    continue

                # Process each result
                for result in results:
                    idx = result.get('invariant_index', -1)
                    if idx < 0 or idx >= len(batch_invariants):
                        logger.error(f"Invalid invariant_index: {idx}")
                        continue

                    inv = batch_invariants[idx]
                    is_true = result.get('is_true', False)
                    confidence = result.get('confidence_score', 0.0)

                    # Save to CSV
                    saver.save_csv_row(
                        {
                            'peripheral_name': inv['peripheral_name'],
                            'register_name': inv['register_name'],
                            'field_name': inv['field_name'],
                            'key': inv['key'],
                            'value': inv['value'],
                            'agent_judgement': is_true,
                            'confidence_score': confidence
                        },
                        classification_csv_name
                    )

                    if is_true:
                        total_true += 1
                    else:
                        total_false += 1

            except Exception as e:
                logger.error(f"Error parsing batch results for {peripheral_name}_{register_name}: {e}")
                logger.error(f"JSON block: {json_block}")

        # Save usage statistics (one row per batch/register)
        usage_stats = UsageStats.from_response_usage(model_name, response.usage, file_search_tokens)
        saver.save_usage_stats(
            usage_stats,
            usage_csv_name,
            additional_fields={
                'peripheral_name': peripheral_name,
                'register_name': register_name,
                'batch_size': len(batch_invariants)
            }
        )

    logger.info(f"Batched validation complete: {total_true} true, {total_false} false")
    return total_true, total_false


if __name__ == "__main__":
    from utils.timing import get_timing_stats
    import sys

    # Configuration
    model_name = "gpt-oss-120b"
    client = client_groq
    reasoning_effort = None
    vs_id = "vs_6892501067b08191ac63cc6de06ee629"

    # Use agent output from specified directory
    agent_output_dir = "agent_output/stm/rm0041/20"

    # Choose mode: "sequential" or "batched"
    MODE = "batched"  # Change this to "sequential" to compare

    if MODE == "batched":
        output_dir = "validator_test_batched"
    else:
        output_dir = "validator_test_sequential"

    os.makedirs(output_dir, exist_ok=True)

    print(f"Building invariants from: {agent_output_dir}")
    input_invariants = build_invariants_from_agent_output(agent_output_dir)
    print(f"Total invariants found: {len(input_invariants)}")

    # Only take first 500 invariants for testing
    input_invariants = input_invariants[:500]
    print(f"Testing with first {len(input_invariants)} invariants")
    print(f"Mode: {MODE.upper()}\n")

    # Reset timing stats
    timing = get_timing_stats()
    timing.reset()

    print(f"\nRunning validator with model: {model_name}")
    print(f"Output directory: {output_dir}\n")

    if MODE == "batched":
        true_count, false_count = run_validator_batched(
            client=client,
            model_name=model_name,
            invariants=input_invariants,
            output_dir=output_dir,
            vs_id=vs_id,
            reasoning_effort=reasoning_effort
        )
    else:
        true_count, false_count = run_validator(
            client=client,
            model_name=model_name,
            invariants=input_invariants,
            output_dir=output_dir,
            vs_id=vs_id,
            reasoning_effort=reasoning_effort
        )

    # Print timing summary
    print(f"\n{'='*80}")
    print(f"VALIDATOR TIMING SUMMARY - {MODE.upper()} MODE")
    print(f"{'='*80}")
    timing.print_summary()

    # Save timing stats
    timing_stats_path = os.path.join(output_dir, "timing_stats.json")
    timing.save_to_file(timing_stats_path)
    print(f"\nTiming statistics saved to: {timing_stats_path}")

    print(f"\n{'='*80}")
    print(f"Validation Results: {true_count} true, {false_count} false")
    print(f"{'='*80}")
