from agents import Agent, Runner, GuardrailFunctionOutput, InputGuardrail, FunctionTool, function_tool, RunContextWrapper, handoff, FileSearchTool
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import asyncio  
import os
import json

import config
from defs import UserContext, RegisterList, Manufacturer, RegisterNameList, RegisterInfo, PreprocessingMethod, EnumValue, BitNumber, BitField
from agent_tools.tools import get_datasheet_pdf, get_datasheet_section, all_svd_file_paths
from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral
from agent_tools.pdf_ops import extract_pages_from_pdf
from agent_tools.md_ops import find_pages_with_tables, remove_markdown_tables
from agent_tools.get_pages_with_keyword import get_keyword_pages_for_svd_files
from prompts.register_info_stm import create_register_info_stm_system_prompt, create_register_info_stm_user_prompt
from groq import Groq
from openai import OpenAI

client_groq = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)


def calculate_address_offset(base_address_in_hex: str, start_register_number: int, register_number: int, register_size_in_bytes: int) -> str:
    base_address = int(base_address_in_hex, 16)
    decimal_offset = base_address + ((register_number - start_register_number) * register_size_in_bytes)
    return f"0x{decimal_offset:X}"


def get_keyword_entry(keyword_info_path: str, peripheral_name: str, register_name: str) -> dict | None:
    keyword_entry = None
    if os.path.exists(keyword_info_path):
        with open(keyword_info_path, "r", encoding="utf-8") as kf:
            try:
                keyword_infos = json.load(kf)
                search_key = f"{peripheral_name}_{register_name}"
                for entry in keyword_infos:
                    if (
                        entry.get("keyword") == search_key
                        and isinstance(entry.get("pages"), list)
                        and len(entry["pages"]) > 0
                    ):
                        keyword_entry = entry
                        break
            except Exception as e:
                print(f"Error reading {keyword_info_path}: {e}")
    return keyword_entry


def get_page_list_for_keyword_entry(pdf_path: str, keyword_entry: dict) -> list[int]:
    pages = keyword_entry.get("pages", [])
    pages_with_tables = find_pages_with_tables(pdf_path, pages)

    # For each number in pages, add number+1 and number+2, then deduplicate and sort
    extended_pages = set(pages)
    for num in pages_with_tables:
        extended_pages.add(num + 1)
        extended_pages.add(num + 2)
    extended_pages = sorted(extended_pages)
    return extended_pages

def get_json_block_from_response(response: str) -> tuple[str, str]:
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
    return None

tools = [
    {
        "type": "function",
        "name": "calculate_address_offset",
        "description": "Calculate the address offset of a register",
        "parameters": {
            "type": "object",
            "properties": {
                "base_address_in_hex": {"type": "string"},
                "start_register_number": {"type": "integer"},
                "register_number": {"type": "integer"},
                "register_size_in_bytes": {"type": "integer"}
            },
            "required": ["base_address_in_hex", "start_register_number", "register_number", "register_size_in_bytes"]
        },
        "strict": True,
    }
]

async def main():
    device_name = config.DEVICE_NAME

    # Find the user context for the current device_name
    user_context = None
    for ctx in config.user_contexts:
        if ctx.device_name == device_name:
            user_context = ctx
            break
    if user_context is None:
        raise ValueError(f"Device {device_name} not found in config.py user_contexts")

    run_number = str(user_context.run)
    
    output_dir = os.path.join("agent_output", device_name, run_number)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")
    
    info_dir = os.path.join(output_dir, "info")
    os.makedirs(info_dir, exist_ok=True)

    # Write the current preprocessing method to a summary file in the output directory
    summary_path = os.path.join(info_dir, "summary")
    with open(summary_path, "w", encoding="utf-8") as summary_file:
        summary_file.write(f"CURRENT_PREPROCESSING_METHOD: {PreprocessingMethod.KEYWORD_SEARCH_PLUS}\n")
    print(f"Wrote summary to {summary_path}")

    # Create a usage csv file in the output directory with the headers: "peripheral_name", "register_name", "model_name", "input_tokens", "output_tokens", "total_tokens"
    usage_path = os.path.join(info_dir, "usage.csv")
    if not os.path.exists(usage_path):
        with open(usage_path, "w", encoding="utf-8") as usage_file:
            usage_file.write("peripheral_name,register_name,model_name,input_tokens,cached_tokens,output_tokens,reasoning_tokens,total_tokens\n")

    # create a reasoning file in the output directory
    reasoning_path = os.path.join(info_dir, "reasoning.txt")
    if not os.path.exists(reasoning_path):
        with open(reasoning_path, "w", encoding="utf-8") as reasoning_file:
            reasoning_file.write("")

    # Get all SVD file paths for the device, and find the set of unique peripheral names
    svd_file_paths = all_svd_file_paths(device_name)
    peripheral_names = get_peripheral_names(svd_file_paths)
    print(f"Found {len(peripheral_names)} peripheral names in SVD files")

    # Check if keyword_infos.json exists, if not, call get_pages_with_keywords
    keyword_info_path = os.path.join("devices", device_name, "keyword_infos.json")
    if not os.path.exists(keyword_info_path):
        pdf_path = os.path.join("devices", device_name, f"{device_name}.pdf")
        svd_folder_path = os.path.join("devices", device_name)
        output_directory = os.path.join("devices", device_name)
        print(f"Gathering keyword page information for SVD files in {svd_folder_path}")
        get_keyword_pages_for_svd_files(pdf_path, svd_folder_path, output_directory)
        
    # peripheral_names = ["FSMC"]
    for peripheral_name in peripheral_names:
        user_context.peripheral_name = peripheral_name
        register_names = get_register_names_for_peripheral(svd_file_paths, peripheral_name)
        # register_names = ["BCR2"]
        print(f"Found {len(register_names)} registers for peripheral {peripheral_name} in SVD files")
        for register_name in register_names:
            # If the register name is prefixed with the peripheral name and an underscore, use only the part after the underscore
            prefix = f"{peripheral_name}_"
            if register_name.startswith(prefix):
                register_name = register_name[len(prefix):]

            output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}")
            if os.path.exists(output_path):
                continue

            user_context.register_name = register_name
            # Search keyword_infos.json for an entry with keyword == f"{peripheral_name}_{register_name}" and non-empty pages
            keyword_info_path = os.path.join("devices", device_name, "keyword_infos.json")
            keyword_entry = get_keyword_entry(keyword_info_path, peripheral_name, register_name)
            
            if keyword_entry:  
                # print(f"Keyword entry: {keyword_entry}")
                pdf_path = os.path.join("devices", device_name, f"{device_name}.pdf")
                extended_pages = get_page_list_for_keyword_entry(pdf_path, keyword_entry)
                # print(f"Extended pages: {extended_pages}")
                datasheet_pages = extract_pages_from_pdf(pdf_path, extended_pages)
                # print(f"Datasheet pages: {datasheet_pages} \n\n")
                datasheet_pages = remove_markdown_tables(datasheet_pages)
                # print(f"Datasheet pages after removing tables: {datasheet_pages} \n\n")

                input_list = [
                    {
                        "role": "developer",
                        "content": [
                            {
                                "type": "input_text",
                                "text": create_register_info_stm_system_prompt()
                            },
                        ]
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": create_register_info_stm_user_prompt(register_name, peripheral_name, datasheet_pages)
                            }
                        ]
                    }
                ]

                response = client.responses.create(
                    # messages=messages,
                    model="openai/gpt-oss-120b",
                    input=input_list,
                    tools=tools,
                )
                
                input_list += response.output 

                for item in response.output:
                    if item.type == "function_call":
                        if item.name == "calculate_address_offset":
                            arguments = json.loads(item.arguments)
                            offset = calculate_address_offset(arguments["base_address_in_hex"], arguments["start_register_number"], arguments["register_number"], arguments["register_size_in_bytes"]) 
                            input_list.append({
                                "type": "function_call_output",
                                "call_id": item.call_id,
                                "output": json.dumps({
                                    "offset": offset
                                })
                            })

                response = client.responses.parse(
                    model="openai/gpt-oss-120b",
                    input=input_list,
                    tools=tools,
                )

                # print(response.output)

                usage = response.usage
                # print(f"Usage: {usage}")

                # Check if response.output_text contains ```json
                json_block_reasoning = get_json_block_from_response(response.output_text)
                if json_block_reasoning:
                    json_block, reasoning = json_block_reasoning

                    with open(reasoning_path, "a", encoding="utf-8") as reasoning_file:
                        reasoning_file.write(f"---{peripheral_name}_{register_name}---\n{reasoning}\n\n")

                    try:
                        json_data = json.loads(json_block)
                    except Exception as e:
                        print(f"Error loading JSON: {e}. {register_name} JSON block: {json_block}")
                        json_data = None
                    # print(f"JSON data: {json_data}")
                else:
                    json_data = None
                    # print("No JSON block found in response")
                
                # print(f"DATASHEET_PAGES: {datasheet_pages}")


                with open(usage_path, "a", encoding="utf-8") as usage_file:
                    usage_file.write(f"{peripheral_name},{register_name},{config.MODEL_NAME},{usage.input_tokens},{usage.input_tokens_details.cached_tokens},{usage.output_tokens},{usage.output_tokens_details.reasoning_tokens},{usage.total_tokens}\n")
                
                if json_data:
                    output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}")
                    with open(output_path, "w", encoding="utf-8") as f:
                        # review = RegisterInfo.model_validate(json.loads(result.choices[0].message.content))
                        # review = json.loads(response.output_text)
                        f.write(json.dumps(json_data, indent=2))
   
   #TODO: Update Run Number, make whole config json based so its easier to update



if __name__ == "__main__":
    asyncio.run(main())

