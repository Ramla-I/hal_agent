from agents import Agent, Runner, GuardrailFunctionOutput, InputGuardrail, FunctionTool, function_tool, RunContextWrapper, handoff, FileSearchTool
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import asyncio
from typing_extensions import Any
import os
from defs import UserContext, RegisterList, Manufacturer, RegisterNameList
from tools import get_datasheet, get_datasheet_section
import config
import xml.etree.ElementTree as ET

CURRENT_VS_ID = "vs_6892501067b08191ac63cc6de06ee629"

name_translation_agent = Agent(
    name = "Register Name Translator",
    model="gpt-4o",
    instructions= "You search a device driver for the registers accessed, and then search the datasheet for the corresponding register name.",
    tools=[get_datasheet],
    output_type=RegisterNameList,
)

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

    You have access to a datasheet and the ability to retrive it a section at a time.  
    For the peripheral {context.peripheral_name}, return the information requested.
    You should first try to access the register table through the get_datasheet_section tool.
    If the register table is not found, then you need to search the vector store.
    """

def vector_store_id(context: RunContextWrapper[UserContext]) -> str:
    return context.vs_id

info_extraction_agent = Agent[UserContext](
    name = "Register Information Extractor",
    model="gpt-4o",
    # instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    instructions=dynamic_instructions,
    tools=[
        get_datasheet_section, 
        FileSearchTool(
            max_num_results=1,
            vector_store_ids=[CURRENT_VS_ID],
            include_search_results=True,
        )
        ],
    output_type=RegisterList,
)

def get_peripheral_names(svd_file_paths):
    """
    Given a list of SVD file paths, extract all unique peripheral names across all files.

    Args:
        svd_file_paths (list[str]): List of SVD file paths.

    Returns:
        list[str]: List of unique peripheral names.
    """
    if not svd_file_paths or not isinstance(svd_file_paths, list):
        raise ValueError("svd_file_paths must be a non-empty list of file paths")

    peripheral_names_set = set()
    for svd_file_path in svd_file_paths:
        if not os.path.exists(svd_file_path):
            raise FileNotFoundError(f"SVD file not found: {svd_file_path}")

        tree = ET.parse(svd_file_path)
        root = tree.getroot()
        peripherals = root.find("peripherals")
        if peripherals is None:
            raise ValueError(f"No <peripherals> section found in SVD file: {svd_file_path}")

        for periph in peripherals.findall("peripheral"):
            name_elem = periph.find("name")
            if name_elem is not None and name_elem.text:
                peripheral_names_set.add(name_elem.text)

    return list(peripheral_names_set)


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

    global CURRENT_VS_ID
    CURRENT_VS_ID = user_context.vs_id
    run_number = str(user_context.run)
    
    output_dir = os.path.join("output", device_name, run_number)
    os.makedirs(output_dir, exist_ok=True)

    if user_context.manufacturer == Manufacturer.STM:
        peripheral_names = get_peripheral_names(user_context.svd_path)
    else:
        with open(user_context.driver_path, "r") as file:
            driver = file.read()
            print(f"Driver Code: {driver}")
            result = await Runner.run(
                name_translation_agent,
                f"""
                Find the names of the registers accesed by the following device driver. You can access the datasheet through tools.
                Driver Code: {driver}
                """
            )
            peripheral_names = [item.datasheet_register_abbreviation for item in result.final_output.registers]

    # print(f"Peripheral names: {peripheral_names}")
    # exit()

    for peripheral_name in peripheral_names:
        user_context.peripheral_name = peripheral_name
        result = await Runner.run(
            info_extraction_agent,
            f"""
            For each register in the peripheral {peripheral_name}. Find the
                address_offset,
                reset_value,
                size,
                readonly_bits,
                write_only_bits,
                read_write_bits,
                subfields and their enumerated values (if they exist).
            You can access the datasheet through the provided tools.
            All the information you provide must be in the datasheet and accurate. If you cannot find a piece of information for a register, leave that field empty.
            """,
            context=user_context,
        )

        output_path = os.path.join(output_dir, peripheral_name)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(str(result.final_output))
   



if __name__ == "__main__":
    asyncio.run(main())

