from agents import Agent, Runner, GuardrailFunctionOutput, InputGuardrail, FunctionTool, function_tool, RunContextWrapper, handoff
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from pydantic import BaseModel
import asyncio
from typing_extensions import Any
from dataclasses import dataclass
from extract_table_e1000 import extract_table
import os

device_name = "82579"
run_number = "2"

datasheet_path = "devices/82579/82579.md"
driver_path = "devices/82579/e1000_ebb2314.rs"

def divide_into_chunks(datasheet: str, num_chunks: int) -> list[str]:
    chunks = []
    for line in datasheet.split("\n"):
        if line.strip() == "":
            continue
        chunks.append(line)
    return chunks


@function_tool(name_override="fetch_datasheet")  
def get_datasheet(ctx: RunContextWrapper[Any]) -> str:
    with open(datasheet_path, "r") as file:
        return file.read()

@function_tool(name_override="fetch_driver")  
def get_driver(ctx: RunContextWrapper[Any]) -> str:
    with open(driver_path, "r") as file:
        return file.read()

class RegisterName(BaseModel):
    driver_register_name: str
    datasheet_register_name: str
    datasheet_register_abbreviation: str

class RegisterNameList(BaseModel):
    registers: list[RegisterName]

name_translation_agent = Agent(
    name = "Register Name Translator",
    model="gpt-4o",
    instructions= "You search a device driver for the registers accessed, and then search the datasheet for the corresponding register name.",
    tools=[get_datasheet],
    output_type=RegisterNameList,
)

class BitField(BaseModel):
    start_bit: int
    end_bit: int

class EnumValue(BaseModel):
    value: str
    description: str

class Subfield(BaseModel):
    name: str
    description: str
    bit_field: BitField
    enum_values: list[EnumValue]

class RegisterInfo(BaseModel):
    datasheet_register_abbreviation: str
    offset_in_hex: str
    readonly_bits: list[BitField]
    write_only_bits: list[BitField]
    read_write_bits: list[BitField]
    # subfields: list[Subfield]

class RegisterList(BaseModel):
    registers: list[RegisterInfo]

@dataclass
class UserContext:
    register_name: str

def dynamic_instructions(
    context: RunContextWrapper[UserContext], agent: Agent[UserContext]
) -> str:
    return """You are an expert embedded systems engineer, highly familiar with understanding and parsing hardware datasheets. 
    You have access to a datasheet and the ability to extract the register table.  
    For the register {context.register_name}, return the offset, read-only, read-write, and write-only bits.
    You should first try to access the register table through the fetch_reg_table tool.
    If the register table is not found, then you need to search the datasheet directly and find the information.
    """

@function_tool(name_override="fetch_reg_table") 
def get_register_table(register_name: str) -> str:
    return extract_table(register_name, datasheet_path)

info_extraction_agent = Agent[UserContext](
    name = "Register Information Extractor",
    model="gpt-4o",
    # instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    instructions=dynamic_instructions,
    tools=[get_datasheet, get_register_table],
    output_type=RegisterList,
)

dependency_agent = Agent(
    name = "Dependency Agent",
    model="gpt-4o",
    instructions=f"""
        Identify dependencies between registers in the portion of the datasheet provided.
        Here is an example:
        "The only time that software should write to this register is after a reset (hardware reset or CTRL.SWRST) and before enabling the receive function (RCTL.EN)."
        This means there is a dependency between the RDH and CTRL registers and between the RDH and RCTL registers.
        The output for this dependency would be formatted as: 
        {{"dependencies": [{{
                "dependee_register": 
                    {{"register_name": "CTRL",
                    "subfield_name_abbreviation": "SWRST",
                    "bit_range": "26"
                    "value": "1"}},
                "dependent_register":
                    {{"register_name": "RDH",
                    "subfield_name_abbreviation": "RDH",
                    "bit_range": "15:0"
                    "value": "N/A"}},
                "relevant_sentence": "The only time that software should write to this register is after a reset (hardware reset or CTRL.SWRST) and before enabling the receive function (RCTL.EN)."
            }},
            {{
                "dependee_register": 
                    {{"register_name": "RDH",
                    "subfield_name_abbreviation": "RDH",
                    "bit_range": "15:0"
                    "value": "N/A"}},
                "dependent_register":
                    {{"register_name": "RCTL",
                    "subfield_name_abbreviation": "EN",
                    "bit_range": "1"
                    "value": "1"}},
                "relevant_sentence": "The only time that software should write to this register is after a reset (hardware reset or CTRL.SWRST) and before enabling the receive function (RCTL.EN)."
            }}]
        }}
    """,
    tools=[get_datasheet],
    output_type=RegisterList,
)

# async def on_handoff(ctx: RunContextWrapper[None], input_data: RegisterNameList):
#     print(f"handed off register list to extraction agent")

# handoff_obj = handoff(
#     agent=info_extraction_agent,
#     on_handoff=on_handoff,
#     input_type=RegisterNameList,
# )

# hal_agent = Agent(
#     name="Hardware Abstraction Layer Agent",
#     model="gpt-4o",
#     instructions=f"""
#     You are an expert embedded systems engineer, highly familiar with understanding and parsing hardware datasheets. 
#     You need to coordinate with the name translation agent to determine the register names, and then coordinate with the info extraction agent to extract the register information.
#     """,
#     handoffs=[name_translation_agent, handoff_obj],
#     output_type=RegisterList,
# )


async def main():
    # # Example 1: History question
    # try:
    #     result = await Runner.run(triage_agent, "who was the first president of the united states?")
    #     print(result.final_output)
    # except InputGuardrailTripwireTriggered as e:
    #     print("Guardrail blocked this input:", e)

    # # Example 2: General/philosophical question
    # try:
    #     result = await Runner.run(triage_agent, "What is the meaning of life?")
    #     print(result.final_output)
    # except InputGuardrailTripwireTriggered as e:
    #     print("Guardrail blocked this input:", e)
    global run_number

    with open(driver_path, "r") as file:
        output_dir = os.path.join("output", device_name, run_number)
        os.makedirs(output_dir, exist_ok=True)

        driver = file.read()

        result = await Runner.run(
            name_translation_agent,
            f"""
            Find the names of the registers accesed by the following device driver. You can access the datasheet through tools.
            Driver Code: {driver}
            """
        )

        result_names = result.final_output
        register_names = [item.datasheet_register_abbreviation for item in result_names.registers]
        
        output_path = os.path.join(output_dir, "reg_list")
        with open(output_path, "w", encoding="utf-8") as f:
            for name in register_names:
                f.write(f"{name}\n")
        # print(register_names)

        user_context = UserContext(register_name="NA")
        
        for reg in register_names:
            user_context.register_name = reg
            result = await Runner.run(
                info_extraction_agent,
                f"""
                Find the offset, read-only, read-write, and write-only bits for the register {reg} in the datasheet. You can access the datasheet through tools.
                """,
                context=user_context,
            )
            # print(result.final_output)
            output_path = os.path.join(output_dir, reg)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(str(result.final_output))

        # Now divide datasheet into chunks and feed it to the dependency agent
        with open(datasheet_path, "r") as file:
            datasheet = file.read()
        chunks = divide_into_chunks(datasheet, 40)
        
        output_file = os.path.join(output_dir, "dependencies")
        with open(output_file, "w", encoding="utf-8") as f:
            for chunk in chunks:
                result = await Runner.run(dependency_agent, chunk)
                f.write(str(result.final_output))
                f.write("\n")

        run_number = str(int(run_number) + 1)

if __name__ == "__main__":
    asyncio.run(main())

