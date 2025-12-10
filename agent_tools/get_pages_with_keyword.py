from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral # to run main, remove agent_tools. at the beginning
from pydantic import BaseModel, Field
import json
import os
import tempfile
from pypdf import PdfReader, PdfWriter
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

class KeywordPage(BaseModel):
    keyword: str = Field(description="The keyword that was initially searched for")
    keyword_found: str = Field(description="The keyword that was found on the pages")
    pages: list[int] = Field(description="The list of page numbers where the keyword was found")


def extract_page_text(page, page_num):
    """Extract text from a single page - used for parallel processing"""
    try:
        text = page.extract_text()
        return page_num, text.lower() if text else ""
    except Exception:
        return page_num, ""

def get_all_pdf_text(pdf_path):
    with open(pdf_path, 'rb') as f:
        reader = PdfReader(f)
        total_pages = len(reader.pages)
        # Use parallel processing for text extraction
        with ThreadPoolExecutor(max_workers=min(4, total_pages)) as executor:
            future_to_page = {
                executor.submit(extract_page_text, page, i): i 
                for i, page in enumerate(reader.pages)
            }
            
            page_texts = {}
            for future in as_completed(future_to_page):
                page_num, text = future.result()
                page_texts[page_num] = text
        
        # Sort by page number and create list
        all_text = [page_texts[i] for i in range(total_pages)]

    return all_text

def all_svd_file_paths(svd_folder_path: str) -> list[str]:
    device_dir = svd_folder_path
    svd_files = []
    if os.path.isdir(device_dir):
        for fname in os.listdir(device_dir):
            if fname.lower().endswith('.svd'):
                svd_files.append(os.path.join(device_dir, fname))
    return svd_files

def find_keyword_page_numbers(pdf_path, keyword, all_text):
    """
    Returns a list of page numbers (0-based) where the keyword appears in the PDF.
    Optimized version with caching and parallel processing.
    """
    keyword = keyword.lower()
    pages_with_keyword = []
    
    # Search through cached text content
    for i, text in enumerate(all_text):
        if text and keyword in text:
            pages_with_keyword.append(i)
    
    return pages_with_keyword

def get_pages_with_keyword(pdf_path, keyword):
    """
    Returns the markdown content of the pages where the keyword appears in the PDF.
    """
    all_text = get_all_pdf_text(pdf_path)
    pages = find_keyword_page_numbers(pdf_path, keyword, all_text)
    if not pages:
        return ""

    # Extract the relevant pages into a temporary PDF
    with open(pdf_path, 'rb') as f:
        reader = PdfReader(f)
        writer = PdfWriter()
        for page_num in pages:
            writer.add_page(reader.pages[page_num])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            writer.write(temp_pdf)
            temp_pdf_path = temp_pdf.name

    # Convert the temporary PDF to markdown using pymupdf4llm
    import pymupdf4llm
    md_text = pymupdf4llm.to_markdown(temp_pdf_path)
    os.remove(temp_pdf_path)
    return md_text

def get_keyword_pages_for_svd_files(pdf_path, svd_folder_path, keyword_info_path):
    if not os.path.isfile(pdf_path):
        print(f"File not found: {pdf_path}")
        return
    if not os.path.isdir(svd_folder_path):
        print(f"Directory not found: {svd_folder_path}")
        return

    # Get all text content (cached and parallel processed)
    all_text = get_all_pdf_text(pdf_path)
    keyword_infos = []
    svd_file_paths = all_svd_file_paths(svd_folder_path)
    peripheral_names = get_peripheral_names(svd_file_paths)
    for peripheral_name in peripheral_names:
        register_names = get_register_names_for_peripheral(svd_file_paths, peripheral_name)
        for register_name in register_names:
            # If register_name already includes peripheral_name, just use register_name as the keyword
            if peripheral_name in register_name:
                joint_name = register_name
            else:
                joint_name = f"{peripheral_name}_{register_name}"

            # If joint_name ends with a number, create a new variable joint_name_no_number without the trailing number
            import re
            joint_name_no_number = None
            match = re.match(r"^(.*?)(\d+)$", joint_name)
            if match:
                joint_name_no_number = match.group(1)

            # If the peripheral name ends with a number, replace the number with 'x'
            joint_name_peripheral_x = None
            match = re.match(r"^(.*?)(\d+)_", joint_name)
            if match:
                joint_name_peripheral_x = f"{match.group(1)}x_{joint_name[len(match.group(0)):]}"
            
            joint_name_peripheral_x_no_number = None
            if joint_name_no_number is not None:
                match = re.match(r"^(.*?)(\d+)_", joint_name_no_number)
                if match:
                    joint_name_peripheral_x_no_number = f"{match.group(1)}x_{joint_name_no_number[len(match.group(0)):]}"

            # print(f"{joint_name} -> {joint_name_no_number} -> {joint_name_peripheral_x}")
            pages = find_keyword_page_numbers(pdf_path, joint_name, all_text)
            keyword_info = None
            if pages:
                keyword_info = KeywordPage(
                    keyword=joint_name,
                    keyword_found=joint_name,
                    pages=pages
                )

            if joint_name_no_number and keyword_info is None:
                pages = find_keyword_page_numbers(pdf_path, joint_name_no_number, all_text)
                if pages:
                    keyword_info = KeywordPage(
                        keyword=joint_name,
                        keyword_found=joint_name_no_number,
                        pages=pages
                    )

            if joint_name_peripheral_x and keyword_info is None:
                pages = find_keyword_page_numbers(pdf_path, joint_name_peripheral_x, all_text)
                if pages:
                    keyword_info = KeywordPage(
                        keyword=joint_name,
                        keyword_found=joint_name_peripheral_x,
                        pages=pages
                    )

            if joint_name_peripheral_x_no_number and keyword_info is None:
                pages = find_keyword_page_numbers(pdf_path, joint_name_peripheral_x_no_number, all_text)
                if pages:
                    keyword_info = KeywordPage(
                        keyword=joint_name,
                        keyword_found=joint_name_peripheral_x_no_number,
                        pages=pages
                    )
            
            if keyword_info is None:
                keyword_info = KeywordPage(
                    keyword=joint_name,
                    keyword_found="",
                    pages=[]
                )
            
            keyword_infos.append(keyword_info.model_dump())
    
    with open(keyword_info_path, "w") as f:
        json.dump(keyword_infos, f, indent=2, ensure_ascii=False)


def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Find pages in a PDF containing a given keyword.")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("keyword", help="Keyword to search for in the PDF")
    args = parser.parse_args()

    pdf_path = args.pdf_path
    keyword = args.keyword

    if not os.path.isfile(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    pages = get_pages_with_keyword(pdf_path, keyword)
    if pages:
        print(pages)
    else:
        print(f"Keyword '{keyword}' not found in the document.")


if __name__ == "__main__":
    main()