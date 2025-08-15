from agents import Agent, Runner, GuardrailFunctionOutput, InputGuardrail, FunctionTool, function_tool, RunContextWrapper, handoff
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from pydantic import BaseModel
import asyncio
from typing_extensions import Any
from dataclasses import dataclass
import os
from tools.tools import save_and_run_python_script, get_datasheet
from defs import UserContext


datasheet_script_generator_agent = Agent[UserContext](
    name = "Datasheet Script Generator",
    model="gpt-4o",
    instructions=f"""
        You are a helpful assistant that writes functions to process a datasheet.
        You will write a python function with the requested name, arguments and return type.
        It should only contain the function definition and a main function to test the function, and should be runnable without any changes.
        It should work with the datasheet file you can retrieve through the get_datasheet tool.

        You should test your function with suitable inputs with the save_and_run_python_script tool.
        If after 4 iterations you are not able to test your function or it is not working, you should stop and ask the user to help you.
    """,
    tools=[save_and_run_python_script, get_datasheet],
)

async def main():
    from dotenv import load_dotenv
    load_dotenv()
    
    user_context = UserContext(
        device_name=os.environ["DEVICE_NAME"],
        driver_path=os.environ["DRIVER_PATH"],
        datasheet_path=os.environ["DATASHEET_PATH"],
        orig_datasheet_path=os.environ["ORIG_DATASHEET_PATH"],
        svd_path=os.environ["SVD_PATH"]
    )

    print(user_context)

    output_dir = os.path.join("output", user_context.device_name, os.environ["RUN"])
    os.makedirs(output_dir, exist_ok=True)
    
    result = await Runner.run(
        datasheet_script_generator_agent,
        f"""
        Write a python function with the name "extract_section" that returns a specific section of the datasheet.
        Its arguments are:
        - a register or peripheral name corresponding to the section you want to extract
        - the datasheet path
        - an option to extract only the tables in that section
        The returned value is the portion of the datasheet that is relevant to the register or peripheral.
        Usually the register or peripheral name is part of the section header, and your function will return that section of the datasheet.
        Examine the datasheet to find the pattern for the section header that will leave to low false positives and negatives.
        """,
        context=user_context,
    )
    # print(result.final_output)
    output_path = os.path.join(output_dir, "extract_section.py")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(str(result.final_output))

   
    # run_number = str(int(run_number) + 1)

if __name__ == "__main__":
    asyncio.run(main())