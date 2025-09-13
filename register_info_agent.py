from agents import Agent, Runner, GuardrailFunctionOutput, InputGuardrail, FunctionTool, function_tool, RunContextWrapper, handoff, FileSearchTool
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import asyncio
import os
from defs import UserContext, RegisterList, Manufacturer, RegisterNameList
from agent_tools.tools import get_datasheet, get_datasheet_section
import config
from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral
# from agent_tools.tools import get_datasheet_pages
from agent_tools.pdf_ops import extract_pages_from_pdf

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
        Name = OutputOpenDrain, Value = 
    You have been given relevant pages of the datasheet.
    """
    # You have access to a datasheet and the ability to retrive it a section at a time.  
    # For the peripheral {context.peripheral_name}, return the information requested.
    # You should first try to access the register table through the get_datasheet_section tool.
    # If the register table is not found, then you need to search the vector store.
 


info_extraction_agent = Agent[UserContext](
    name = "Register Information Extractor",
    model="gpt-4o",
    # instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    instructions=dynamic_instructions,
    # tools=[
    #     get_datasheet_section, 
    #     FileSearchTool(
    #         max_num_results=1,
    #         vector_store_ids=[CURRENT_VS_ID],
    #         include_search_results=True,
    #     )
    #     ],
    output_type=RegisterList,
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
        register_names = get_register_names_for_peripheral(user_context.svd_path, peripheral_name)
        for register_name in register_names:
            user_context.register_name = register_name
            # INSERT_YOUR_CODE
            # Search keyword_infos.json for an entry with keyword == f"{peripheral_name}_{register_name}" and non-empty pages
            import json

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
                pdf_path = user_context.datasheet_path
                if pdf_path.endswith(".md"):
                    pdf_path = pdf_path[:-3] + ".pdf"
                datasheet_pages = extract_pages_from_pdf(pdf_path, pages)
                # print(f"keyword_entry: {keyword_entry}")
                # print(f"Datasheet pages: {datasheet_pages}")
                # exit()
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

                output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(str(result.final_output))
   



if __name__ == "__main__":
    asyncio.run(main())

