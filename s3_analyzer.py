from agents import Agent, Runner
from dataclasses import dataclass
from pydantic import BaseModel
import csv
import os
import asyncio

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

async def run_analyzer(
    model_name: str, 
    svd_file_name: str, 
    register_diff_csv_path: str, 
    analyzer_output_dir: str
):
    usage_path = os.path.join(analyzer_output_dir, "usage.csv")
    if not os.path.exists(usage_path):
        with open(usage_path, "w", encoding="utf-8") as usage_file:
            usage_file.write("svd_name,diff_version,model_name,input_tokens,cached_tokens,output_tokens,reasoning_tokens,total_tokens\n")

    register_diff_rows = []
    with open(register_diff_csv_path, "r", encoding="utf-8") as f:
        # Convert CSV file contents into a list of dictionaries (one per row)
        reader = csv.DictReader(f)
        for row in reader:
            if row['key'] == 'fields': # skip rows that just list the number of fields
                continue
            register_diff_rows.append(row)

    result = await Runner.run(
        analyzer_agent,
        f"""
        This is the original register difference file:
        {register_diff_rows}
        You are interested in the rows where there is a value in the just_svd or just_output columns, and nothing in the both column.
        You need to analyze the differences and determine if they actually represent bugs or are just differences in the way the information is represented.
        If the difference is that the agent whose output is just_output couldn't find the information, then it is not a bug and should not be included in the list.
        If the just_output field has words like NA, Not found, Not specifed, not found in datasheet, or anything else that means the information wasn't found, then it is not a valid bug and should not be included in the returned list.
        Return a list of row ids that are actual difference that could potentially be bugs.
        """,
    )
            
    usage = result.context_wrapper.usage
    with open(usage_path, "a", encoding="utf-8") as usage_file:
        usage_file.write(f"{svd_file_name},orig,{model_name},{usage.input_tokens},{usage.input_tokens_details.cached_tokens},{usage.output_tokens},{usage.output_tokens_details.reasoning_tokens},{usage.total_tokens}\n")
            
    output_path = os.path.join(analyzer_output_dir, f"{svd_file_name}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.final_output.model_dump_json(indent=2))
            