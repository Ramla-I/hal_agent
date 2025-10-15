from agents import Agent, Runner, GuardrailFunctionOutput, InputGuardrail, FunctionTool, function_tool, RunContextWrapper, handoff, FileSearchTool
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import asyncio  
import os
import json

import config
from defs import UserContext, RegisterList, Manufacturer, RegisterNameList, RegisterInfo, PreprocessingMethod
from agent_tools.tools import get_datasheet_pdf, get_datasheet_section, all_svd_file_paths
from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral
from agent_tools.pdf_ops import extract_pages_from_pdf
from agent_tools.md_ops import find_pages_with_tables
from agent_tools.get_pages_with_keyword import get_keyword_pages_for_svd_files

def dynamic_instructions(
    context: RunContextWrapper[UserContext], agent: Agent[UserContext]
) -> str:
    return """You are an expert embedded systems engineer, highly familiar with understanding and parsing hardware datasheets. 
    For example, you can look at a datasheet section like this:
    ```
        **8.4.2** **GPIO port output type register (GPIOx_OTYPER)**
        **(x = A..I/J/K)**

        Address offset: 0x04

        Reset value: 0x0000 0000

        
        31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16
        Reserved
        |15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
        |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
        |OT15|OT14|OT13|OT12|OT11|OT10|OT9|OT8|OT7|OT6|OT5|OT4|OT3|OT2|OT1|OT0|
        |rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|

        Bits 31:16 Reserved, must be kept at reset value.

        Bits 15:0 **OTy** : Port x configuration bits (y = 0..15)

        These bits are written by software to configure the output type of the I/O port.
        0: Output push-pull (reset state)
        1: Output open-drain
    ```
    From the above sample you can understand that the GPIOx_OTYPER has a size of 32 bits.
    It's offset it 0x04 and its reset value is 0x00000000.
    Bits 31:16 are reserved do read-only.
    Bits 15:0 are read-write.
    For each bit from 15:0, they can be written with one of two enumerated values:
        Name = OutputPushPull, Value = 0 
        Name = OutputOpenDrain, Value = 1
    """
    # You have access to a datasheet and the ability to retrive it a section at a time.  
    # For the peripheral {context.peripheral_name}, return the information requested.
    # You should first try to access the register table through the get_datasheet_section tool.
    # If the register table is not found, then you need to search the vector store.
 


info_extraction_agent = Agent[UserContext](
    name = "Register Information Extractor",
    model = config.MODEL_NAME,
    # instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    instructions=dynamic_instructions,
    # tools=[
        # get_datasheet_section, 
        # FileSearchTool(
        #     max_num_results=1,
        #     vector_store_ids=[CURRENT_VS_ID],
        #     include_search_results=True,
        # )
    # ],
    output_type=RegisterInfo,
)


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

    # Write the current preprocessing method to a summary file in the output directory
    summary_path = os.path.join(output_dir, "summary")
    with open(summary_path, "w", encoding="utf-8") as summary_file:
        summary_file.write(f"CURRENT_PREPROCESSING_METHOD: {PreprocessingMethod.KEYWORD_SEARCH_PLUS}\n")
    print(f"Wrote summary to {summary_path}")

    # Create a usage csv file in the output directory with the headers: "peripheral_name", "register_name", "model_name", "input_tokens", "output_tokens", "total_tokens"
    usage_path = os.path.join(output_dir, "usage.csv")
    with open(usage_path, "w", encoding="utf-8") as usage_file:
        usage_file.write("peripheral_name,register_name,model_name,input_tokens,cached_tokens,output_tokens,reasoning_tokens,total_tokens\n")

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
        
    # peripheral_names = ["RCC"]
    for peripheral_name in peripheral_names:
        user_context.peripheral_name = peripheral_name
        register_names = get_register_names_for_peripheral(svd_file_paths, peripheral_name)
        # register_names = ["APB1ENR"]
        print(f"Found {len(register_names)} registers for peripheral {peripheral_name} in SVD files")
        for register_name in register_names:

            output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}")
            if os.path.exists(output_path):
                continue

            user_context.register_name = register_name
            # Search keyword_infos.json for an entry with keyword == f"{peripheral_name}_{register_name}" and non-empty pages
            keyword_info_path = os.path.join("devices", device_name, "keyword_infos.json")
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
            if keyword_entry:
                pages = keyword_entry.get("pages", [])
                pdf_path = os.path.join("devices", device_name, f"{device_name}.pdf")
                pages_with_tables = find_pages_with_tables(pdf_path, pages)
                # For each number in pages, add number+1 and number+2, then deduplicate and sort
                extended_pages = set(pages)
                for num in pages_with_tables:
                    extended_pages.add(num + 1)
                    extended_pages.add(num + 2)
                extended_pages = sorted(extended_pages)

                datasheet_pages = extract_pages_from_pdf(pdf_path, extended_pages)

                result = await Runner.run(
                    info_extraction_agent,
                    f"""
                    For the register {register_name} in the peripheral {peripheral_name}. Find the
                        address_offset,
                        reset_value,
                        size,
                        readonly_bits,
                        write_only_bits,
                        read_write_bits,
                        subfields and their enumerated values (if they exist).
                    These are relevant pages of the datasheet:
                    {datasheet_pages}
                    All the information you provide must be in the datasheet and accurate. If you cannot find a piece of information for a register, leave that field empty.
                    """,
                    context=user_context,
                )

                usage = result.context_wrapper.usage
                # print(f"Usage: {usage}")
                with open(usage_path, "a", encoding="utf-8") as usage_file:
                    usage_file.write(f"{peripheral_name},{register_name},{config.MODEL_NAME},{usage.input_tokens},{usage.input_tokens_details.cached_tokens},{usage.output_tokens},{usage.output_tokens_details.reasoning_tokens},{usage.total_tokens}\n")
                
                output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result.final_output.model_dump_json(indent=2))
   
   #TODO: Update Run Number, make whole config json based so its easier to update



if __name__ == "__main__":
    asyncio.run(main())

