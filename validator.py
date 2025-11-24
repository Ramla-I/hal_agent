from agents import Agent, Runner, GuardrailFunctionOutput, InputGuardrail, FunctionTool, function_tool, RunContextWrapper, handoff, FileSearchTool
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import asyncio  
import os
import json
import csv

import config
from defs import UserContext, RegisterList, Manufacturer, RegisterNameList, RegisterInfo, PreprocessingMethod, EnumValue, BitNumber, BitField
from agent_tools.tools import get_datasheet_pdf, get_datasheet_section, all_svd_file_paths
from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral
from agent_tools.pdf_ops import extract_pages_from_pdf
from agent_tools.md_ops import find_pages_with_tables, remove_markdown_tables
from agent_tools.get_pages_with_keyword import get_keyword_pages_for_svd_files
from prompts.register_info_stm import create_register_info_stm_system_prompt, create_register_info_stm_user_prompt
from prompts.validator import create_validator_system_prompt, create_validator_user_prompt
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

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


def main():
    device_name = config.DEVICE_NAME

    # Find the user context for the current device_name
    user_context = None
    for ctx in config.user_contexts:
        if ctx.device_name == device_name:
            user_context = ctx
            break
    if user_context is None:
        raise ValueError(f"Device {device_name} not found in config.py user_contexts")

    run_number = "17" #str(user_context.run)
    
    vector_store_id = user_context.vs_id
    file_id = user_context.file_id

    output_dir = os.path.join("agent_output", device_name, run_number, "validator")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")
    
    info_dir = os.path.join(output_dir, "info")
    os.makedirs(info_dir, exist_ok=True)

    # Create a usage csv file in the output directory with the headers: "peripheral_name", "register_name", "model_name", "input_tokens", "output_tokens", "total_tokens"
    usage_path = os.path.join(info_dir, "usage.csv")
    if not os.path.exists(usage_path):
        with open(usage_path, "w", encoding="utf-8") as usage_file:
            usage_file.write("peripheral_name,register_name,model_name,input_tokens,cached_tokens,output_tokens,reasoning_tokens,total_tokens\n")

    results_path = os.path.join(info_dir, "results")
    if not os.path.exists(results_path):
        with open(results_path, "w", encoding="utf-8") as results_file:
            results_file.write("")

    results_file = open(results_path, "a", encoding="utf-8")
    # Get all SVD file paths for the device, and find the set of unique peripheral names
    generator_output_dir = os.path.join("agent_output", device_name, run_number)

    total_correct = 0
    total_incorrect = 0
    not_found = 0

    # all_filenames = [
    #     fname
    #     for fname in os.listdir(generator_output_dir)
    #     if not (fname.endswith(".csv") or fname.startswith("summary"))
    #     and "_" in fname
    # ]
    
    # for filename in all_filenames:
    #     basename = filename
    #     if "." in basename:
    #         # Remove potential extension (technically, they likely don't have an extension)
    #         basename = basename.rsplit(".", 1)[0]
    #     split_idx = basename.find("_")
    #     if split_idx == -1:
    #         continue
    #     peripheral_name = basename[:split_idx]
    #     register_name = basename[split_idx + 1:]

    #     output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}")
    #     if os.path.exists(output_path):
    #         continue
        
    #     with open(os.path.join(generator_output_dir, filename), "r", encoding="utf-8") as f:
    #         data = json.load(f)

    # INSERT_YOUR_CODE
    # Open the CSV file validator_eval_rm0041 for reading
    csv_eval_path = os.path.join("validator_eval_rm0041.csv")
    eval_rows = []
    if os.path.exists(csv_eval_path):
        with open(csv_eval_path, "r", encoding="utf-8") as eval_csv:
            reader = csv.DictReader(eval_csv)
            for row in reader:
                eval_rows.append(dict(row))
    else:
        print(f"Warning: Could not find validator_eval_rm0041.csv in current directory.")
    
    
    for row in eval_rows:
        peripheral_name = row['peripheral_name']
        register_name = row['register_name']
        field = row['field']
        value = row['value']
        confidence_score = float(row['confidence_expected'])
        
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
        
        input_list.append({
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": create_validator_user_prompt(register_name, peripheral_name, field, value)
                }
            ]
        })

        response = client.responses.create(
            model="gpt-5.1",
            input=input_list,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": 2,
            }],
            include=["file_search_call.results"]

        )

        # print(response.output_text)
        results_file.write(f"{peripheral_name}_{register_name}, {field}, {value}, {confidence_score}\n")
        results_file.write(f"{response.output_text}\n")
        results_file.write(f"\n\n")
        # print(f"{peripheral_name}_{register_name}")
        # json_block_reasoning = get_json_block_from_response(response.output_text)
        # json_block, reasoning = json_block_reasoning
        # if json_block:
        #     confidence_score_response = float(json.loads(json_block)['confidence_score'])
        #     if confidence_score_response == confidence_score:
        #         results_file.write(f"Confidence score is correct\n")
        #         total_correct += 1
        #     else:
        #         results_file.write(f"Confidence score is incorrect\n")
        #         results_file.write(f"Confidence Score Response: {confidence_score_response}\n")
        #         results_file.write(f"Confidence Score Expected: {confidence_score}\n")
        #         total_incorrect += 1
        #         # input()
        # else:
        #     results_file.write(f"No JSON block found in response, reasoning: {reasoning}\n")
        #     not_found += 1
            
        # usage = response.usage
        # # print(f"Usage: {usage}")
        input_list.pop()

                # # Check if response.output_text contains ```json
                # json_block_reasoning = get_json_block_from_response(response.output_text)
                # if json_block_reasoning:
                #     json_block, reasoning = json_block_reasoning

                #     with open(reasoning_path, "a", encoding="utf-8") as reasoning_file:
                #         reasoning_file.write(f"---{peripheral_name}_{register_name}---\n{reasoning}\n\n")

                #     try:
                #         json_data = json.loads(json_block)
                #     except Exception as e:
                #         print(f"Error loading JSON: {e}. {register_name} JSON block: {json_block}")
                #         json_data = None
                #     # print(f"JSON data: {json_data}")
                # else:
                #     json_data = None
                #     # print("No JSON block found in response")
                
                # print(f"DATASHEET_PAGES: {datasheet_pages}")


                # with open(usage_path, "a", encoding="utf-8") as usage_file:
                #     usage_file.write(f"{peripheral_name},{register_name},{config.MODEL_NAME},{usage.input_tokens},{usage.input_tokens_details.cached_tokens},{usage.output_tokens},{usage.output_tokens_details.reasoning_tokens},{usage.total_tokens}\n")
                
                # if json_data:
                #     output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}")
                #     with open(output_path, "w", encoding="utf-8") as f:
                #         # review = RegisterInfo.model_validate(json.loads(result.choices[0].message.content))
                #         # review = json.loads(response.output_text)
                #         f.write(json.dumps(json_data, indent=2))
   
   #TODO: Update Run Number, make whole config json based so its easier to update



if __name__ == "__main__":
    # asyncio.run(main())
    main()
