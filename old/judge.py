from agents import Agent, Runner, GuardrailFunctionOutput, InputGuardrail, FunctionTool, function_tool, RunContextWrapper, handoff, FileSearchTool
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import asyncio  
import os
import json
from typing import Literal
from dataclasses import dataclass
from pydantic import BaseModel

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

@dataclass
class EvaluationFeedback(BaseModel):
    feedback: str
    category: Literal["missing_information", "incorrect_information", "other"]
    field: Literal["address_offset", "reset_value", "size", "readonly_bits", "write_only_bits", "read_write_bits", "subfield_names", "subfield_bit_numbers", "enumerated_values"]

@dataclass
class EvaluationFeedbackList(BaseModel):
    feedback_list: list[EvaluationFeedback]

judge_agent = Agent[None](
    name="judge",
    instructions=(
        "You evaluate register information and decide if it is accurate, and has captured all information about the register from the portion of the datasheet provided to you. "
        "If there is any information that is missing, you provide feedback on what needs to be added. Be very clear and state the information that is missing."
        "If there is any information that is incorrect, you provide feedback on what needs to be corrected. Be very clear and state the information that is incorrect, and what the correct replacement is."
        "If the information is correct, return an empty list."
        "You should only prove feedback for: address_offset, reset_value, size, readonly_bits, write_only_bits, read_write_bits, subfield names, subfield bit numbers and their enumerated values."
        "Do not provide feedback for anything else, or provide feedback if you are not able to find the correct information in the datasheet."
        "Also, remember that reserved bits can be classified as read-only even if not explictly stated as read-only."
        "If something is correct, do not provide feedback for it."
        
    ),
    output_type=EvaluationFeedbackList,
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
    
    reg_info_output_dir = os.path.join("agent_output", device_name, run_number)

    output_dir = os.path.join("agent_output", device_name, run_number, "judge_iteration")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")

    # Create a usage csv file in the output directory with the headers: "peripheral_name", "register_name", "model_name", "input_tokens", "output_tokens", "total_tokens"
    usage_judge_path = os.path.join(output_dir, "usage_judge.csv")
    with open(usage_judge_path, "w", encoding="utf-8") as usage_file:
        usage_file.write("peripheral_name,register_name,model_name,input_tokens,cached_tokens,output_tokens,reasoning_tokens,total_tokens\n")

    usage_info_path = os.path.join(output_dir, "usage_info.csv")
    with open(usage_info_path, "w", encoding="utf-8") as usage_file:
        usage_file.write("peripheral_name,register_name,model_name,input_tokens,cached_tokens,output_tokens,reasoning_tokens,total_tokens\n")

    # Iterate over files in reg_info_output_dir, ignore summary and usage csv files, get peripheral_name and register_name
    all_filenames = [
        fname
        for fname in os.listdir(reg_info_output_dir)
        if not (fname.endswith(".csv") or fname.startswith("summary"))
        and "_" in fname
    ]

    keyword_info_path = os.path.join("devices", device_name, "keyword_infos.json")
    with open(keyword_info_path, "r", encoding="utf-8") as kf:
        keyword_infos = json.load(kf)

    for filename in all_filenames:
        basename = filename
        if "." in basename:
            # Remove potential extension (technically, they likely don't have an extension)
            basename = basename.rsplit(".", 1)[0]
        split_idx = basename.find("_")
        if split_idx == -1:
            continue
        peripheral_name = basename[:split_idx]
        register_name = basename[split_idx + 1:]

        keyword_entry = None
        search_key = f"{basename}"
        for entry in keyword_infos:
            if (
                entry.get("keyword") == search_key
                and isinstance(entry.get("pages"), list)
                and len(entry["pages"]) > 0
            ):
                keyword_entry = entry
                break

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

            reg_info_output_path = os.path.join(reg_info_output_dir, basename)
            with open(reg_info_output_path, "r", encoding="utf-8") as f:
                reg_info = json.load(f)

            result = await Runner.run(
                judge_agent,
                f"""
                For the register {register_name} in the peripheral {peripheral_name}, this is the information that was extracted by the Register Information Extractor:
                {reg_info}
                These are the relevant pages of the datasheet:
                {datasheet_pages}
                Judge the information and provide feedback on what needs to be added or corrected.
                """,
            )
            
            usage = result.context_wrapper.usage
            # print(f"Usage: {usage}")
            with open(usage_judge_path, "a", encoding="utf-8") as usage_file:
                usage_file.write(f"{peripheral_name},{register_name},{config.MODEL_NAME},{usage.input_tokens},{usage.input_tokens_details.cached_tokens},{usage.output_tokens},{usage.output_tokens_details.reasoning_tokens},{usage.total_tokens}\n")
            
            if result.final_output.feedback_list == []:
                continue

            output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}_judge_feedback")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.final_output.model_dump_json(indent=2))
            
            result = await Runner.run(
                info_extraction_agent,
                f"""
                For the register {register_name} in the peripheral {peripheral_name}, this is the information that was previously extracted by you:
                {reg_info}
                Here is the feedback from a judge agent critiquing the information you extracted:
                {result.final_output}
                These are the relevant pages of the datasheet:
                {datasheet_pages}
                Assess the feedback and if you agree with the feedback, incorporate it into the information you previously extracted.
                If any information should be corrected, provide the corrected information.
                If any information should be added, provide the added information.
                Return only the corrected or added information filled in, do not fill out any other field if it was originally correct.
                You do not have to fill out any information that was originally correct.
                """,
                context=user_context,
            )

            usage = result.context_wrapper.usage
            with open(usage_info_path, "a", encoding="utf-8") as usage_file:
                usage_file.write(f"{peripheral_name},{register_name},{config.MODEL_NAME},{usage.input_tokens},{usage.input_tokens_details.cached_tokens},{usage.output_tokens},{usage.output_tokens_details.reasoning_tokens},{usage.total_tokens}\n")

            output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.final_output.model_dump_json(indent=2))

        else:
            print(f"Warning: Keyword {search_key} not found in {keyword_info_path}")
            
if __name__ == "__main__":
    asyncio.run(main())