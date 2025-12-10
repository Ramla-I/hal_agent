import os
import json
from defs import ContextRetrievalParameters, ContextRetrievalMethod
from agent_tools.tools import all_svd_file_paths, calculate_address_offset
from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral
from agent_tools.pdf_ops import extract_pages_from_pdf
from agent_tools.md_ops import find_pages_with_tables, remove_markdown_tables
from agent_tools.get_pages_with_keyword import get_keyword_pages_for_svd_files
from prompts.register_info_stm import create_register_info_stm_system_prompt, create_register_info_stm_user_prompt
from parse_output import get_json_block_from_response

def create_keyword_info_json(device_name: str, device_dir: str):
    keyword_info_path = os.path.join(device_dir, "keyword_infos.json")
    if not os.path.exists(keyword_info_path):
        pdf_path = os.path.join(device_dir, f"{device_name}.pdf")
        svd_folder_path = os.path.join(device_dir, "svd")
        get_keyword_pages_for_svd_files(pdf_path, svd_folder_path, keyword_info_path)
    # else:
        # print(f"Keyword info json already exists for {device_name} at {keyword_info_path}")
    return keyword_info_path


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


def get_page_list_for_keyword_entry(pdf_path: str, keyword_entry: dict, num_pages_after_tables: int) -> list[int]:
    pages = keyword_entry.get("pages", [])

    if num_pages_after_tables > 0:
        pages_with_tables = find_pages_with_tables(pdf_path, pages)
        extended_pages = set(pages)
        for num in pages_with_tables:
            for i in range(1, num_pages_after_tables + 1):
                extended_pages.add(num + i)
        extended_pages = sorted(extended_pages)
        return extended_pages
    else:
        return pages


def retrieve_context(
    context_retrieval_parameters: ContextRetrievalParameters,
    device_name: str, 
    device_dir: str, 
    peripheral_name: str,
    register_name: str
):
    if context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.KEYWORD_SEARCH:
        keyword_info_path = create_keyword_info_json(device_name, device_dir)
        keyword_entry = get_keyword_entry(keyword_info_path, peripheral_name, register_name)
    
        if keyword_entry:  
            pdf_path = os.path.join(device_dir, f"{device_name}.pdf")
            extended_pages = get_page_list_for_keyword_entry(pdf_path, keyword_entry, context_retrieval_parameters.pages_after_keyword)
            datasheet_pages = extract_pages_from_pdf(pdf_path, extended_pages)
            if context_retrieval_parameters.remove_tables:
                datasheet_pages = remove_markdown_tables(datasheet_pages)
            return datasheet_pages
        else:
            return None

    elif context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.VECTOR_STORE:
        print(f"Retrieving context from vector store for {device_name} {peripheral_name} {register_name}")
        return None

    elif context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.REGEX:
        print(f"Retrieving context from regex for {device_name} {peripheral_name} {register_name}")
        return None

    else:
        raise ValueError(f"Context retrieval method {context_retrieval_parameters.context_retrieval_method} not supported") 

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

