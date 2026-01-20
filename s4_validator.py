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
from prompts.validator import create_validator_system_prompt, create_validator_file_search_query, create_validator_user_prompt
from context_retrieval.semantic_search import search_vector_store, format_results
from utils.result_saver import ResultSaver, UsageStats
from utils.utils import setup_logger

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
    if (
        os.path.exists(classification_csv_path)
        and os.path.exists(usage_csv_path)
        and os.path.exists(output_txt_path)
    ):
        logger.info(f"Output files already exist for validator in {output_dir}. Skipping.")
        return total_true, total_false
    
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
        usage_stats = UsageStats.from_response_usage(model_name, response.usage)
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

    


if __name__ == "__main__":
    model_names = ["gpt-4.1-nano", "gpt-5-nano", "gpt-5.2", "gpt-oss-120b"]
    reasoning_efforts = [None, "low", None, None]
    clients = [client_openai, client_openai, client_openai, client_groq]

    id = 3

    vs_id = "vs_6892501067b08191ac63cc6de06ee629"
    output_dir = os.path.join("validator_test_output")
    os.makedirs(output_dir, exist_ok=True)

    # input_invariants = [
    #     {
    #         'peripheral_name': 'afio',
    #         'register_name': 'evcr',
    #         'field_name': '',
    #         'key': 'address_offset',
    #         'value': '0x0'
    #     },
    #     {
    #         'peripheral_name': 'afio',
    #         'register_name': 'evcr',
    #         'field_name': 'vvayurpxfkp',
    #         'key': 'reset_value',
    #         'value': '0x00000000'
    #     },
    #     {
    #         'peripheral_name': 'afio',
    #         'register_name': 'evcr',
    #         'field_name': 'alwbxnn',
    #         'key': 'size',
    #         'value': '32'
    #     },
    #     {
    #         'peripheral_name': 'afio',
    #         'register_name': 'evcr',
    #         'field_name': 'evoe',
    #         'key': 'bit_offset',
    #         'value': '7'
    #     },
    #     {
    #         'peripheral_name': 'afio',
    #         'register_name': 'evcr',
    #         'field_name': 'evoe',
    #         'key': 'access',
    #         'value': 'read-write'
    #     }
    # ]

    input_invariants = build_invariants_from_agent_output("agent_output/stm/rm0041/16")
    print(f"Input invariants: {input_invariants}")
    run_validator(clients[id], model_names[id], input_invariants, output_dir, vs_id, reasoning_efforts[id])
