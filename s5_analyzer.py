from agents import Agent, Runner
from dataclasses import dataclass
from pydantic import BaseModel
import csv
import os
import asyncio
import tempfile

from utils.result_saver import ResultSaver, UsageStats
from utils.utils import setup_logger

logger = setup_logger(__name__)

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
    logger.info(
        "Running analyzer for %s with diff %s",
        svd_file_name,
        register_diff_csv_path,
    )
    saver = ResultSaver(analyzer_output_dir)

    register_diff_rows = _load_register_diff_rows(register_diff_csv_path)

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

    logger.info("Analyzer completed for %s", svd_file_name)
            
    usage = result.context_wrapper.usage
    usage_stats = UsageStats.from_response_usage(model_name, usage)
    saver.save_usage_stats(
        usage_stats,
        "usage.csv",
        additional_fields={
            "svd_name": svd_file_name,
            "diff_version": "orig",
        },
    )

    saver.save_json(result.final_output, f"{svd_file_name}")


def _load_register_diff_rows(register_diff_csv_path: str) -> list[dict[str, str]]:
    register_diff_rows = []
    with open(register_diff_csv_path, "r", encoding="utf-8") as f:
        # Convert CSV file contents into a list of dictionaries (one per row)
        reader = csv.DictReader(f)
        for row in reader:
            if row["key"] == "fields":  # skip rows that just list the number of fields
                continue
            register_diff_rows.append(row)
    return register_diff_rows


def main() -> None:
     # Full analyzer test using a real diff file.
    register_diff_csv_path = (
        "/Users/ramla/Projects/hal_agent/evaluation/stm/rm0041/16/stm32f100/"
        "register_diff.csv"
    )
    if not os.path.exists(register_diff_csv_path):
        raise FileNotFoundError(
            f"Expected diff file not found: {register_diff_csv_path}"
        )
    analyzer_output_dir = os.path.join("analyzer_test_output")
    os.makedirs(analyzer_output_dir, exist_ok=True)
    asyncio.run(
        run_analyzer(
            model_name="gpt-oss-120b",
            svd_file_name="stm32f100",
            register_diff_csv_path=register_diff_csv_path,
            analyzer_output_dir=analyzer_output_dir,
        )
    )
    print("s5_analyzer full analyzer test completed.")


if __name__ == "__main__":
    main()
        