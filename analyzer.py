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

@dataclass
class ValidBugsList(BaseModel):
    bugs: list[int]

analyzer_agent = Agent[None](
    name="analyzer",
    instructions=(
        "You are an expert systems engineer."
        "You are given a csv file that contains a list of differences between the register information in an SVD file and that found by another agent from the datasheet."
        "The header of the csv file is: id,peripheral,register,key,just_svd,just_output,both."
        "Just_svd is the value in the svd file for the key."
        "Just_output is the value in the agent output for the key."
        "The key is the field that is different between the svd and the output."
        "If there are numbers is just_svd, just_output and both, that means they are reporting the number of items that are different between the svd and the agent output for that key."
        "You do not need to analyze those rows."
        "You are more interested in the rows where there is a value in the just_svd or just_output columns, and nothing in the both column."
        "You need to analyze the differences and determine if they actually represent bugs or are just differences in the way the information is represented."
        "It's also possible that some differences are because of filler words, and the different ways an agent could write N/A or something similar to indicate it couldn't find the information, which is also not a valid bug."
        "For example, if the just_output field has words like NA, Not found, Not specified, unknown, not found in datasheet, etc., then it is not a valid bug and should not be included in the returned list."
        "You return a list of row ids that are actual difference that could potentially be bugs."
    ),
    output_type=ValidBugsList,
)

async def main():
    device_name = config.DEVICE_NAME
    svd_file = config.SVD_FILE

    # Find the user context for the current device_name
    user_context = None
    for ctx in config.user_contexts:
        if ctx.device_name == device_name:
            user_context = ctx
            break
    if user_context is None:
        raise ValueError(f"Device {device_name} not found in config.py user_contexts")

    run_number = str(user_context.run)

    analyzer_input_orig = os.path.join("evaluation", "results", device_name, run_number, svd_file, f"Generator{config.GENERATOR_ITER}", "register_diff.csv")
    # analyzer_input_orig = os.path.join("evaluation", "results", device_name, run_number, svd_file, "critic_diff", "register_diff.csv")


    analyzer_output_dir = os.path.join("agent_output", device_name, run_number, "analyzer_iteration")
    # analyzer_output_dir = os.path.join("agent_output", device_name, run_number, "analyzer_iteration_critic")

    os.makedirs(analyzer_output_dir, exist_ok=True)
    print(f"Created output directory: {analyzer_output_dir}")

    # Create a usage csv file in the output directory with the headers: "peripheral_name", "register_name", "model_name", "input_tokens", "output_tokens", "total_tokens"
    usage_path = os.path.join(analyzer_output_dir, "usage_analyzer.csv")
    with open(usage_path, "w", encoding="utf-8") as usage_file:
        usage_file.write("svd_name,diff_version,model_name,input_tokens,cached_tokens,output_tokens,reasoning_tokens,total_tokens\n")

    # INSERT_YOUR_CODE
    with open(analyzer_input_orig, "r", encoding="utf-8") as f:
        analyzer_orig_file_contents = f.read()
    
    # INSERT_YOUR_CODE
    import csv
    import io

    # Convert CSV file contents into a list of dictionaries (one per row)
    analyzer_orig_rows = []
    reader = csv.DictReader(io.StringIO(analyzer_orig_file_contents))
    for row in reader:
        if row['key'] == 'fields':
            continue
        analyzer_orig_rows.append(row)

    result = await Runner.run(
        analyzer_agent,
        f"""
        This is the original register difference file:
        {analyzer_orig_rows}
        You are interested in the rows where there is a value in the just_svd or just_output columns, and nothing in the both column.
        You need to analyze the differences and determine if they actually represent bugs or are just differences in the way the information is represented.
        If the difference is that the agent whose output is just_output couldn't find the information, then it is not a bug and should not be included in the list.
        If the just_output field has words like NA, Not found, Not specifed, not found in datasheet, or anything else that means the information wasn't found, then it is not a valid bug and should not be included in the returned list.
        Return a list of row ids that are actual difference that could potentially be bugs.
        """,
    )
            
    usage = result.context_wrapper.usage
    with open(usage_path, "a", encoding="utf-8") as usage_file:
        usage_file.write(f"{svd_file},orig,{config.MODEL_NAME},{usage.input_tokens},{usage.input_tokens_details.cached_tokens},{usage.output_tokens},{usage.output_tokens_details.reasoning_tokens},{usage.total_tokens}\n")
            
    output_path = os.path.join(analyzer_output_dir, f"{svd_file}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.final_output.model_dump_json(indent=2))
            
if __name__ == "__main__":
    asyncio.run(main())