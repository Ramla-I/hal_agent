import os
import json
from defs import PreprocessingMethod
from agent_tools.tools import all_svd_file_paths, calculate_address_offset
from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral
from agent_tools.pdf_ops import extract_pages_from_pdf
from agent_tools.md_ops import find_pages_with_tables, remove_markdown_tables
from agent_tools.get_pages_with_keyword import get_keyword_pages_for_svd_files
from prompts.register_info_stm import create_register_info_stm_system_prompt, create_register_info_stm_user_prompt
from parse_output import get_json_block_from_response

def get_keyword_entry(keyword_info_path: str, peripheral_name: str, register_name: str) -> dict | None:
    keyword_entry = None
    if os.path.exists(keyword_info_path):
        with open(keyword_info_path, "r", encoding="utf-8") as kf:
            try:
                keyword_infos = json.load(kf)
                search_key = f"{peripheral_name}_{register_name}"
                for entry in keyword_infos:
                    if (
                        entry.get("keyword").lower() == search_key.lower()
                        and isinstance(entry.get("pages"), list)
                        and len(entry["pages"]) > 0
                    ):
                        keyword_entry = entry
                        break
            except Exception as e:
                print(f"Error reading {keyword_info_path}: {e}")
    return keyword_entry


def get_page_list_for_keyword_entry(pdf_path: str, keyword_entry: dict) -> list[int]:
    pages = keyword_entry.get("pages", [])
    pages_with_tables = find_pages_with_tables(pdf_path, pages)

    # For each number in pages, add number+1 and number+2, then deduplicate and sort
    extended_pages = set(pages)
    for num in pages_with_tables:
        extended_pages.add(num + 1)
        extended_pages.add(num + 2)
    extended_pages = sorted(extended_pages)
    return extended_pages


def retrieve_context(
    device_name: str, 
    device_dir: str, 
    output_dir: str,
    peripheral_name: str,
    register_name: str
):
    os.makedirs(output_dir, exist_ok=True)

    # Check if keyword_infos.json exists, if not, call get_pages_with_keywords
    keyword_info_path = os.path.join(device_dir, "keyword_infos.json")
    if not os.path.exists(keyword_info_path):
        pdf_path = os.path.join(device_dir, f"{device_name}.pdf")
        svd_folder_path = os.path.join(device_dir, "svd")
        output_directory = os.path.join(device_dir)
        print(f"Gathering keyword page information for SVD files in {svd_folder_path}")
        get_keyword_pages_for_svd_files(pdf_path, svd_folder_path, output_directory)

    # If the register name is prefixed with the peripheral name and an underscore, use only the part after the underscore
    prefix = f"{peripheral_name}_"
    if register_name.startswith(prefix):
        register_name = register_name[len(prefix):]

    output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}")

    # Search keyword_infos.json for an entry with keyword == f"{peripheral_name}_{register_name}" and non-empty pages
    keyword_info_path = os.path.join(device_dir, "keyword_infos.json")
    keyword_entry = get_keyword_entry(keyword_info_path, peripheral_name, register_name)
    
    if keyword_entry:  
        print(f"Keyword entry: {keyword_entry}")
        pdf_path = os.path.join(device_dir, f"{device_name}.pdf")
        extended_pages = get_page_list_for_keyword_entry(pdf_path, keyword_entry)
        # print(f"Extended pages: {extended_pages}")
        datasheet_pages = extract_pages_from_pdf(pdf_path, extended_pages)
        # print(f"Datasheet pages: {datasheet_pages} \n\n")
        datasheet_pages_wo_tables = remove_markdown_tables(datasheet_pages)
        # print(f"Datasheet pages after removing tables: {datasheet_pages_wo_tables} \n\n")

        with open(output_path, "w", encoding="utf-8") as output_file:
            output_file.write(f"Extended pages: \n{extended_pages}\n\n")
            output_file.write(f"Datasheet pages:\n {datasheet_pages}\n\n")
            output_file.write(f"Datasheet pages after removing tables: \n {datasheet_pages_wo_tables}\n\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <device_name> <device_dir> <output_dir> <peripheral_name> <register_name>")
        sys.exit(1)
    device_name = sys.argv[1]
    device_dir = sys.argv[2]
    output_dir = sys.argv[3]
    peripheral_name = sys.argv[4]
    register_name = sys.argv[5]
    retrieve_context( device_name, device_dir, output_dir, peripheral_name, register_name)

