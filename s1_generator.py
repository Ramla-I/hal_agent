import os
import json
from defs import PreprocessingMethod
from agent_tools.tools import all_svd_file_paths, calculate_address_offset
from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral
from agent_tools.pdf_ops import extract_pages_from_pdf
from agent_tools.md_ops import find_pages_with_tables, remove_markdown_tables
from agent_tools.get_pages_with_keyword import get_keyword_pages_for_svd_files
from prompts.register_info_stm import create_register_info_stm_system_prompt, create_register_info_stm_user_prompt
from parse_output import get_json_block_from_response
from groq import Groq
from openai import OpenAI

client_groq = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

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

def run_generator(
    device_name: str, 
    run_number: int, 
    device_dir: str, 
    agent_output_dir: str,
    model_name: str,
    preprocessing_method: PreprocessingMethod
):
    """
    Runs the generator agent for a given device and run number.
    Args:
        device_name: The name of the device to run the generator for.
        run_number: The run number to run the generator for.
        device_dir: The path to the datasheet file for the device.
        agent_output_dir: The directory to output the agent's output to.
        model_name: The name of the model to use for the generator.
        preprocessing_method: The preprocessing method to use for the generator.
    """
    print(f"Running generator for device {device_name} with run number {run_number}")

    run_number = str(run_number)
    
    # Create the directory for the agent's output
    output_dir = agent_output_dir
    
    # Create a sub output directory for information about the run
    info_dir = os.path.join(output_dir, "info")
    os.makedirs(info_dir, exist_ok=True)

    # Write information about the preprocessing method and model to a summary file
    summary_path = os.path.join(info_dir, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as summary_file:
        summary_file.write(f"CURRENT_PREPROCESSING_METHOD: {preprocessing_method}\n")
        summary_file.write(f"MODEL: {model_name}\n")

    # Create a usage csv file to store the token usage for each register
    usage_path = os.path.join(info_dir, "usage.csv")
    if not os.path.exists(usage_path):
        with open(usage_path, "w", encoding="utf-8") as usage_file:
            usage_file.write("peripheral_name,register_name,model_name,input_tokens,cached_tokens,output_tokens,reasoning_tokens,total_tokens\n")

    # Create a reasoning file to store the reasoning returned by the agentfor each register
    reasoning_path = os.path.join(info_dir, "reasoning.txt")
    if not os.path.exists(reasoning_path):
        with open(reasoning_path, "w", encoding="utf-8") as reasoning_file:
            reasoning_file.write("")

    # Get all SVD file paths for the device, and find the set of unique peripheral names
    svd_file_paths = all_svd_file_paths(device_dir)
    print(f"SVD file paths: {svd_file_paths}")
    peripheral_names = get_peripheral_names(svd_file_paths)
    print(f"Found {len(peripheral_names)} peripheral names in SVD files")

    # Check if keyword_infos.json exists, if not, call get_pages_with_keywords
    keyword_info_path = os.path.join(device_dir, "keyword_infos.json")
    if not os.path.exists(keyword_info_path):
        pdf_path = os.path.join(device_dir, f"{device_name}.pdf")
        svd_folder_path = os.path.join(device_dir, "svd")
        output_directory = os.path.join(device_dir)
        print(f"Gathering keyword page information for SVD files in {svd_folder_path}")
        get_keyword_pages_for_svd_files(pdf_path, svd_folder_path, output_directory)
        # peripheral_names = ["FSMC"]
    for peripheral_name in peripheral_names:
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

            # Search keyword_infos.json for an entry with keyword == f"{peripheral_name}_{register_name}" and non-empty pages
            keyword_info_path = os.path.join(device_dir, "keyword_infos.json")
            keyword_entry = get_keyword_entry(keyword_info_path, peripheral_name, register_name)
            
            if keyword_entry:  
                # print(f"Keyword entry: {keyword_entry}")
                pdf_path = os.path.join(device_dir, f"{device_name}.pdf")
                extended_pages = get_page_list_for_keyword_entry(pdf_path, keyword_entry)
                # print(f"Extended pages: {extended_pages}")
                datasheet_pages = extract_pages_from_pdf(pdf_path, extended_pages)
                # print(f"Datasheet pages: {datasheet_pages} \n\n")
                # datasheet_pages = remove_markdown_tables(datasheet_pages)
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
                    usage_file.write(f"{peripheral_name},{register_name},{model_name},{usage.input_tokens},{usage.input_tokens_details.cached_tokens},{usage.output_tokens},{usage.output_tokens_details.reasoning_tokens},{usage.total_tokens}\n")
                
                if json_data:
                    output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}")
                    with open(output_path, "w", encoding="utf-8") as f:
                        # review = RegisterInfo.model_validate(json.loads(result.choices[0].message.content))
                        # review = json.loads(response.output_text)
                        f.write(json.dumps(json_data, indent=2))
   
   #TODO: Update Run Number, make whole config json based so its easier to update



if __name__ == "__main__":
    run_generator()

