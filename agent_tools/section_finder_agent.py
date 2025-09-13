from agents import Agent, Runner, FileSearchTool
import asyncio
import os
import sys
from tools import get_table_of_contents_md
from svd_parsing import get_peripheral_names  
import json
# from ..defs import Manufacturer, SectionInfo, UserContext # the dots will be when we use __init__.py files
# from ..config import CURRENT_VS_ID

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from defs import Manufacturer, SectionInfo, UserContext
import config


chapter_finder_agent = Agent[UserContext](
    name="chapter_finder_agent",
    instructions="""
    A agent that finds the chapter of a datasheet that contains the information about a given peripheral, 
    You should first get the table of contents and then use it to find the chapter that contains the information about the {context.peripheral_name}.
    Only retrieve the table of contents once.
    A chapter typically starts with a number (e.g., "4 CRC Calculation Unit", "5 Power controller (PWR)").
    If {context.peripheral_name} is a peripheral, it is usually in the chapter name, but not necessarily.
    If you cannot figure out which chapter contains the information, search the vector store for information about the {context.peripheral_name}.
    Then used the returned information to find the chapter that contains the information about the {context.peripheral_name}.
    Return the chapter name, the peripheral name, and the start and end page of the chapter. If it is not found, return false for section_exists, the requested periphernal name, NA for the section name and -1 as the page numbers.
    """,
    tools=[
        get_table_of_contents_md,
        FileSearchTool(
            max_num_results=1,
            vector_store_ids=[config.CURRENT_VS_ID],
            include_search_results=True,
        )
    ],
    output_type=SectionInfo,
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

    config.CURRENT_VS_ID = user_context.vs_id

    if user_context.manufacturer == Manufacturer.STM:
        peripheral_names = get_peripheral_names(user_context.svd_path)
    else:
        raise ValueError(f"Manufacturer {user_context.manufacturer} not supported")

    print(f"Found {len(peripheral_names)} peripherals")
    
    # First, try to find the chapter from the chapter boundaries JSON file
    chapter_boundaries_path = f"devices/{user_context.device_name}/chapter_boundaries.json"
    with open(chapter_boundaries_path, "r", encoding="utf-8") as f:
        chapter_data = json.load(f)
        chapters = chapter_data.get("chapters", [])
    
    section_infos = []
    for peripheral_name in peripheral_names:
        
        found_in_chapter = False
        chapter_title = None
        chapter_start = -1
        chapter_end = -1

        # Try to find a chapter whose title contains the peripheral name (case-insensitive, ignore case and some common formatting)
        for chapter in chapters:
            title = chapter.get("title", "")
            # Try to match peripheral name in title, ignoring case and some formatting
            if peripheral_name.lower() in title.lower():
                chapter_title = title
                chapter_start = chapter.get("start_page", -1)
                chapter_end = chapter.get("end_page", -1)
                found_in_chapter = True
                break

        if found_in_chapter:
            # If found, append the SectionInfo directly and skip the agent call
            print(f"Found {peripheral_name} in chapter {chapter_title} from {chapter_boundaries_path}")
            section_infos.append(SectionInfo(
                section_exists=True,
                peripheral_name=peripheral_name,
                section_name=chapter_title,
                start_page=chapter_start,
                end_page=chapter_end
            ))
            continue

        print(f"Finding chapter for {peripheral_name}")
        user_context.peripheral_name = peripheral_name
        result = await Runner.run(
            chapter_finder_agent,
            f"""
            For the peripheral {peripheral_name}, find the chapter that contains the information about the peripheral.
            You can access the datasheet through the provided tools.
            All the information you provide must be in the datasheet and accurate.
            """,
            context=user_context,
        )
        section_infos.append(result.final_output)
        
    # Save the section_infos to a file for later use
    output_path = f"results/{user_context.device_name}/section_infos.json"
    # Convert SectionInfo objects to dicts if needed
    def section_info_to_dict(info):
        if info is None:
            return None
        if hasattr(info, "__dict__"):
            return info.__dict__
        return info
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([section_info_to_dict(info) for info in section_infos], f, indent=2, ensure_ascii=False)
    print(f"Section infos saved to {output_path}")
   



if __name__ == "__main__":
    asyncio.run(main())