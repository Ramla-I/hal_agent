import os
import json
from defs import ContextRetrievalParameters
from agent_tools.tools import all_svd_file_paths, calculate_address_offset
from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral
from prompts.register_info_stm import create_register_info_stm_system_prompt, create_register_info_stm_user_prompt
from parse_output import get_json_block_from_response
from groq import Groq
from openai import OpenAI
from s1a_retrieve_context import retrieve_context

client_groq = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

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
    context_retrieval_parameters: ContextRetrievalParameters
):
    """
    Runs the generator agent for a given device and run number.
    Args:
        device_name: The name of the device to run the generator for.
        run_number: The run number to run the generator for.
        device_dir: The path to the datasheet file for the device.
        agent_output_dir: The directory to output the agent's output to.
        model_name: The name of the model to use for the generator.
        context_retrieval_parameters: The context retrieval parameters to use for the generator.
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
        summary_file.write(f"CONTEXT_RETRIEVAL_METHOD: {context_retrieval_parameters.context_retrieval_method.value}\n")
        summary_file.write(f"----PAGES_AFTER_KEYWORD: {context_retrieval_parameters.pages_after_keyword}\n")
        summary_file.write(f"----REMOVE_TABLES: {context_retrieval_parameters.remove_tables}\n")
        summary_file.write(f"----NUMBER_EMBEDDINGS: {context_retrieval_parameters.number_embeddings}\n")
        summary_file.write(f"----RE_RANKING: {context_retrieval_parameters.re_ranking}\n")
        summary_file.write(f"----REGEX: {context_retrieval_parameters.regex}\n")
        summary_file.write(f"----OTHER: {context_retrieval_parameters.other}\n\n")
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

    # Get the name of each register to find in the datasheet, that is our prompt granularity
    svd_file_paths = all_svd_file_paths(device_dir)
    peripheral_names = get_peripheral_names(svd_file_paths)
    print(f"Found {len(peripheral_names)} peripheral names in SVD files")

    register_names_to_process = {peripheral_name: [] for peripheral_name in peripheral_names}
    for peripheral_name in peripheral_names:
        register_names = get_register_names_for_peripheral(svd_file_paths, peripheral_name)
        register_names_to_process[peripheral_name].extend(register_names)
    
    # Now the Context Retrieval Part
    for peripheral_name in register_names_to_process.keys():
        for register_name in register_names_to_process[peripheral_name]:

            # check if output file exists, if so assume the agent already processed it, skip to the next register
            output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}")
            if os.path.exists(output_path):
                continue

            datasheet_pages = retrieve_context(context_retrieval_parameters, device_name, device_dir, peripheral_name, register_name)
            if datasheet_pages is None:
                continue
            
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
