from agents import Agent, Runner, GuardrailFunctionOutput, InputGuardrail, FunctionTool, function_tool, RunContextWrapper, handoff, FileSearchTool
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import asyncio  
import os
import json
import csv

import config
from defs import UserContext, RegisterList, Manufacturer, RegisterNameList, RegisterInfo,  EnumValue, BitNumber, BitField
from prompts.validator import create_validator_system_prompt, create_validator_file_search_query, create_validator_user_prompt
from context_retrieval.semantic_search import search_vector_store, format_results
from openai import OpenAI
from groq import Groq

client_groq = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

client_openai = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

def get_model_string(model_name: str) -> str:
    if model_name == "gpt-oss-120b":
        return f"openai/{model_name}"
    else:
        return model_name

def get_json_block_from_response(response: str) -> tuple[str|None, str]:
    extracted_json_blocks = []
    reasoning = ""
    if "```json" in response:
        # Split and extract all text blocks between ```json and ```

        idx = response.find("```json")
        reasoning = response[:idx].strip()

        split_blocks = response.split("```json")
        for block in split_blocks[1:]:
            # Only find up to the next ```
            end_idx = block.find("```")
            if end_idx != -1:
                extracted = block[:end_idx].strip()
            else:
                extracted = block.strip()
            if extracted:
                extracted_json_blocks.append(extracted)
    if extracted_json_blocks:   
        return extracted_json_blocks[0], reasoning
    else:
        return None, response


def run_validator(client: Groq|OpenAI, model_name: str, test_set_path: str, output_dir: str, vs_id: str):
    total_true_positives = 0
    total_false_negatives = 0
    total_false_positives = 0
    total_true_negatives = 0
    output_errors = 0

    output_file_path = os.path.join(output_dir, f"validator_output_{model_name}_rm0041.csv")
    output_file = open(output_file_path, "w", encoding="utf-8")
    output_file.write("peripheral_name, register_name, field_name, key, value, true_value, agent_judgement, confidence_score\n")

    reasoning_file_path = os.path.join(output_dir, f"validator_reasoning_{model_name}_rm0041.txt")
    reasoning_file = open(reasoning_file_path, "w", encoding="utf-8")

    usage_file_path = os.path.join(output_dir, f"validator_usage_{model_name}_rm0041.csv")
    usage_file = open(usage_file_path, "w", encoding="utf-8")
    usage_file.write("peripheral_name, register_name, field_name, key, input_tokens, cached_tokens, output_tokens, reasoning_tokens, total_tokens\n")
    
    accuracy_file_path = os.path.join(output_dir, f"validator_accuracy_{model_name}_rm0041.csv")
    accuracy_file = open(accuracy_file_path, "w", encoding="utf-8")
    accuracy_file.write("model_name, true_positives, false_negatives, false_positives, true_negatives, accuracy, precision, recall, f1_score\n")
    
    print(f"Running validator for {model_name} with test set {test_set_path}")

    test_set_rows = []
    with open(test_set_path, "r", encoding="utf-8") as test_set_file:
        reader = csv.DictReader(test_set_file)
        for row in reader:
            test_set_rows.append(dict(row))
    
    for row in test_set_rows:
        peripheral_name = row['peripheral']
        register_name = row['register']
        field_name = row['field_name']
        key = row['key']
        value = row['correct_value']
        true_value = row['is_correct']
        
        # print(f"Data: {data}")
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
        response = client.responses.create(
            model=get_model_string(model_name),
            input=input_list,
        )

        reasoning_file.write(f"{response.output_text}\n")
        reasoning_file.write(f"\n\n")

        json_block, reasoning = get_json_block_from_response(response.output_text)
        if json_block is not None:
            try:
                json_data = json.loads(json_block)
                output_file.write(f"{peripheral_name}, {register_name}, {field_name}, {key}, {value}, {true_value}, {json_data['is_true']}, {json_data['confidence_score']}\n")
                
                agent_judgement = True if json_data['is_true'] == True else False
                correct_judgement = True if true_value == "True" else False
                # print(f"json_data: {json_data['is_true']}, true_value: {true_value}")
                # print(f"Agent judgement: {agent_judgement}, Correct judgement: {correct_judgement}, Confidence score: {json_data['confidence_score']}   Peripheral: {peripheral_name}, Register: {register_name}, Field: {field_name}, Key: {key}, Value: {value}, True value: {true_value}")
                if agent_judgement == True and correct_judgement == True:
                    total_true_positives += 1
                elif agent_judgement == False and correct_judgement == True:
                    total_false_negatives += 1
                elif agent_judgement == True and correct_judgement == False:
                    total_false_positives += 1
                elif agent_judgement == False and correct_judgement == False:
                    total_true_negatives += 1
            
            except Exception as e:
                print(f"Error parsing JSON block for peripheral {peripheral_name}, register {register_name}, field {field_name}, key {key}, value {value}: {e}")
                output_errors += 1

        usage = response.usage
        usage_file.write(f"{peripheral_name}, {register_name}, {field_name}, {key}, {usage.input_tokens}, {usage.input_tokens_details.cached_tokens}, {usage.output_tokens}, {usage.output_tokens_details.reasoning_tokens}, {usage.total_tokens}\n")

    accuracy = (total_true_positives + total_true_negatives) / (total_true_positives + total_false_negatives + total_false_positives + total_true_negatives)
    precision = total_true_positives / (total_true_positives + total_false_positives)
    recall = total_true_positives / (total_true_positives + total_false_negatives)
    f1_score = 2 * (precision * recall) / (precision + recall)
    accuracy_file.write(f"{model_name}, {total_true_positives}, {total_false_negatives}, {total_false_positives}, {total_true_negatives}, {accuracy}, {precision}, {recall}, {f1_score}\n")
    accuracy_file.flush()
    accuracy_file.close()

    print(f"Total output errors: {output_errors}")


if __name__ == "__main__":
    # model_name = "gpt-5.2"
    # client = client_openai
    # model_name = "gpt-5-nano"

    client = client_groq
    model_name = "gpt-oss-120b"

    vs_id = "vs_6892501067b08191ac63cc6de06ee629"
    input_test_set_path = os.path.join("validator", "test_set_rm0041.csv")
    output_dir = os.path.join("validator", "output", model_name)
    os.makedirs(output_dir, exist_ok=True)

    run_validator(client, model_name, input_test_set_path, output_dir, vs_id)
