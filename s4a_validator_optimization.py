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

def run_validator(client: OpenAI|Groq, model_name: str, test_set_path: str, output_dir: str, vs_id: str, reasoning_effort: str | None = None):
    total_true_positives = 0
    total_false_negatives = 0
    total_false_positives = 0
    total_true_negatives = 0
    output_errors = 0

    # Initialize ResultSaver for all file operations
    saver = ResultSaver(output_dir)
    
    # Define file names
    output_csv_name = f"validator_output_{model_name}.csv"
    reasoning_txt_name = f"validator_reasoning_{model_name}.txt"
    usage_csv_name = f"validator_usage_{model_name}.csv"
    accuracy_csv_name = f"validator_accuracy_{model_name}.csv"
    
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

        # Save reasoning text
        saver.append_text(f"{response.output_text}\n\n", reasoning_txt_name)

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
                        'true_value': true_value,
                        'agent_judgement': json_data['is_true'],
                        'confidence_score': json_data['confidence_score']
                    },
                    output_csv_name
                )
                
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

    # Calculate accuracy metrics
    total = total_true_positives + total_false_negatives + total_false_positives + total_true_negatives
    if total > 0:
        accuracy = (total_true_positives + total_true_negatives) / total
    else:
        accuracy = 0.0
    
    if (total_true_positives + total_false_positives) > 0:
        precision = total_true_positives / (total_true_positives + total_false_positives)
    else:
        precision = 0.0
    
    if (total_true_positives + total_false_negatives) > 0:
        recall = total_true_positives / (total_true_positives + total_false_negatives)
    else:
        recall = 0.0
    
    if (precision + recall) > 0:
        f1_score = 2 * (precision * recall) / (precision + recall)
    else:
        f1_score = 0.0
    
    # Save accuracy metrics
    saver.save_csv_row(
        {
            'model_name': model_name,
            'true_positives': total_true_positives,
            'false_negatives': total_false_negatives,
            'false_positives': total_false_positives,
            'true_negatives': total_true_negatives,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score
        },
        accuracy_csv_name
    )

    print(f"Total output errors: {output_errors}")


if __name__ == "__main__":
    model_names = ["gpt-4.1-nano", "gpt-5-nano", "gpt-5.2", "gpt-oss-120b"]
    reasoning_efforts = [None, "low", None, None]
    clients = [client_openai, client_openai, client_openai, client_groq]

    id = 3

    vs_id = "vs_6892501067b08191ac63cc6de06ee629"
    input_test_set_path = os.path.join("validator", "stm-rm0041", "hold_set_rm0041.csv")
    output_dir = os.path.join("validator", "output", "rm0041", model_names[id])
    os.makedirs(output_dir, exist_ok=True)

    run_validator(clients[id], model_names[id], input_test_set_path, output_dir, vs_id, reasoning_efforts[id])
