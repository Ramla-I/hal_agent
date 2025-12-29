import os
import json
import sys

# HACK, remove this once we have a proper package structure
# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from defs import Manufacturer
from agent_tools.md_ops import find_pages_with_tables
from agent_tools.get_pages_with_keyword import get_keyword_pages_for_svd_files

def create_keyword_info_json(device_name: str, device_dir: str, manufacturer: Manufacturer):
    keyword_info_path = os.path.join(device_dir, "keyword_infos.json")
    if not os.path.exists(keyword_info_path):
        pdf_path = os.path.join(device_dir, f"{device_name}.pdf")
        svd_folder_path = os.path.join(device_dir, "svd")
        get_keyword_pages_for_svd_files(pdf_path, svd_folder_path, keyword_info_path, manufacturer)
    # else:
        # print(f"Keyword info json already exists for {device_name} at {keyword_info_path}")
    return keyword_info_path


def get_keyword_entry(keyword_info_path: str, search_key: str) -> dict | None:
    keyword_entry = None
    if os.path.exists(keyword_info_path):
        with open(keyword_info_path, "r", encoding="utf-8") as kf:
            try:
                keyword_infos = json.load(kf)
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