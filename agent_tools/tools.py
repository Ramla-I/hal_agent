from agents import function_tool, RunContextWrapper
import os
import sys
from pathlib import Path
import fitz

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

import agent_tools
from defs import UserContext, Manufacturer
from agent_tools.pdf_ops import extract_markdown_from_pdf, extract_part_of_pdf

@function_tool 
def read_file(path) -> str:
    with open(path, "r") as file:
        return file.read()

@function_tool(name_override="run_script") 
def save_and_run_python_script(script: str) -> str:
    with open("testing_script.py", "w") as file:
        file.write(script)
        import subprocess
        result = subprocess.run(["python3", "testing_script.py"], capture_output=True, text=True)
        return result.stdout + result.stderr

@function_tool(name_override="fetch_svd")  
def get_svd_file(wrapper: RunContextWrapper[UserContext], id: int) -> str:
    if id < 0 or id >= len(wrapper.context.svd_path):
        raise IndexError(f"SVD file id {id} is out of range (svd_path has {len(wrapper.context.svd_path)} entries).")
    with open(wrapper.context.svd_path[id], "r") as file:
        return file.read()
    
@function_tool(name_override="fetch_datasheet")  
def get_datasheet(wrapper: RunContextWrapper[UserContext]) -> str:
    # print("get_datasheet")
    with open(wrapper.context.datasheet_path, "r") as file:
        return file.read()

@function_tool(name_override="fetch_driver")  
def get_driver(wrapper: RunContextWrapper[UserContext]) -> str:
    with open(wrapper.context.driver_path, "r") as file:
        return file.read()

@function_tool(name_override="fetch_datasheet_section") 
def get_datasheet_section(wrapper: RunContextWrapper[UserContext], tables_only: bool = False) -> str:
    # print(f"get_datasheet_section {wrapper.context.peripheral_name}")
    if wrapper.context.manufacturer == Manufacturer.INTEL:
        return agent_tools.extract_section_regex(wrapper.context.datasheet_path, wrapper.context.peripheral_name, tables_only)
    elif wrapper.context.manufacturer == Manufacturer.STM:
        return agent_tools.extract_section_file(wrapper.context.datasheet_sections_directory, wrapper.context.peripheral_name, tables_only)
    else:
        raise ValueError(f"Manufacturer {wrapper.context.manufacturer} not supported")
    

@function_tool(name_override="split_datasheet")
def split_datasheet_get_section(wrapper: RunContextWrapper[UserContext], n: int, i: int) -> str:
    """
    Splits the datasheet into n sections and returns the ith section (0-based).
    """
    # Read the datasheet content
    with open(wrapper.context.datasheet_path, "r") as file:
        content = file.read()
    if n <= 0:
        raise ValueError("n must be a positive integer")
    if i < 0 or i >= n:
        raise IndexError(f"Section index i={i} is out of range for n={n}")
    # Split by lines for more even distribution
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)
    section_size = total_lines // n
    remainder = total_lines % n
    # Calculate start and end indices for the ith section
    start = i * section_size + min(i, remainder)
    end = start + section_size
    if i < remainder:
        end += 1
    section_lines = lines[start:end]
    return "".join(section_lines)


FUNCTION_CALL_COUNT = 0

@function_tool(name_override="get_table_of_contents")
def get_table_of_contents(wrapper: RunContextWrapper[UserContext]) -> str:
    """
    Returns the table of contents of the datasheet.
    """
    print(f"get_table_of_contents {wrapper.context.datasheet_path}")
    global FUNCTION_CALL_COUNT
    FUNCTION_CALL_COUNT += 1
    if FUNCTION_CALL_COUNT > 1:
        return "You have already called this function and have access to the table of contents."
    
    pages_to_search = 50

    # Get the datasheet path and replace .md with .pdf
    md_path = Path(wrapper.context.datasheet_path)
    pdf_path = md_path.with_suffix('.pdf')

    # Check if the PDF exists
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF {pdf_path}: {e}")
        return None

    toc_text = ""
    # Heuristic: extract text from first 30 pages for ToC.
    # This might need to be adjusted for different documents.
    for page_num in range(min(pages_to_search, doc.page_count)):
        page = doc.load_page(page_num)
        toc_text += page.get_text()

    if not toc_text.strip():
        print("Could not extract any text from the first pages of the PDF. Is it an image-based PDF?")
        doc.close()
        return None

    return toc_text

@function_tool
def get_table_of_contents_md(wrapper: RunContextWrapper[UserContext]) -> str:
    """
    Returns the table of contents of the datasheet.
    """
    print(f"get_table_of_contents_md {wrapper.context.datasheet_path}")
    global FUNCTION_CALL_COUNT
    FUNCTION_CALL_COUNT += 1
    if FUNCTION_CALL_COUNT > 1:
        return "You have already called this function and have access to the table of contents."
    
    pages_to_search = 50

    # Get the datasheet path and replace .md with .pdf
    md_path = Path(wrapper.context.datasheet_path)
    pdf_path = md_path.with_suffix('.pdf')

    # Check if the PDF exists
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    extracted_pdf_path = extract_part_of_pdf(pdf_path, 0, pages_to_search)
    toc_text = extract_markdown_from_pdf(extracted_pdf_path)

    return toc_text

def get_datasheet_pages(wrapper: RunContextWrapper[UserContext], pages: list[int]) -> str:
    """
    Returns the relevant datasheet pages in md format.
    """
def get_datasheet_pages(wrapper: RunContextWrapper[UserContext], pages: list[int]) -> str:
    """
    Returns the relevant datasheet pages in markdown format.

    Args:
        wrapper: RunContextWrapper containing UserContext with datasheet_path
        pages: List of 0-based page numbers to extract

    Returns:
        str: Extracted text from the specified pages, concatenated as markdown.
    """
    from pathlib import Path

    # Get the datasheet PDF path
    md_path = Path(wrapper.context.datasheet_path)
    pdf_path = md_path.with_suffix('.pdf')

    # Check if the PDF exists
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF (fitz) is required to extract pages from PDF.")

    doc = fitz.open(pdf_path)
    extracted_text = ""
    for page_num in pages:
        if 0 <= page_num < doc.page_count:
            page = doc.load_page(page_num)
            extracted_text += f"\n\n--- Page {page_num + 1} ---\n\n"
            extracted_text += page.get_text()
        else:
            extracted_text += f"\n\n--- Page {page_num + 1} (out of range) ---\n\n"
    doc.close()
    return extracted_text

# @function_tool(name_override="search_datasheet")
# def search_datasheet(wrapper: RunContextWrapper[UserContext], search_string: str) -> dict:
#     """
#     Searches the datasheet for a string and returns a list of (start_line, end_line) tuples
#     for each match of the search string, including matches that are split over multiple lines.

#     Args:
#         wrapper: RunContextWrapper containing UserContext with datasheet_path
#         search_string: The string to search for

#     Returns:
#         dict: {
#             "matches": [
#                 {"start_line": int, "end_line": int, "line_content": str},
#                 ...
#             ]
#         }
#         Line numbers are 1-based.
#     """
#     matches = []
#     # Read all lines into a list for easier multi-line processing
#     with open(wrapper.context.datasheet_path, "r", encoding="utf-8") as file:
#         lines = file.readlines()

#     # Join all lines into a single string with line breaks preserved
#     full_text = "".join(lines)

#     # To find matches that may be split over multiple lines, we search in the full_text
#     # and then map the match's character positions back to line numbers.
#     import re

#     # Escape the search string for regex, but allow it to match across line breaks
#     # Replace spaces in search_string with \s+ to allow for line breaks and whitespace
#     pattern = re.escape(search_string)
#     pattern = pattern.replace(r"\ ", r"\s+")
#     regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)

#     for match in regex.finditer(full_text):
#         start_char = match.start()
#         end_char = match.end()

#         # Map character positions to line numbers
#         # Find the line number where start_char and end_char fall
#         char_count = 0
#         start_line = end_line = None
#         for idx, line in enumerate(lines):
#             next_char_count = char_count + len(line)
#             if start_line is None and start_char < next_char_count:
#                 start_line = idx + 1  # 1-based
#             if end_line is None and end_char <= next_char_count:
#                 end_line = idx + 1  # 1-based
#                 break
#             char_count = next_char_count
#         if start_line is None:
#             start_line = 1
#         if end_line is None:
#             end_line = len(lines)

#         # Extract the matched content, replacing newlines with spaces for readability
#         matched_content = match.group().replace("\n", " ").replace("\r", " ")

#         matches.append({
#             "start_line": start_line,
#             "end_line": end_line,
#             "line_content": matched_content
#         })

#     return {"matches": matches}

# @function_tool(name_override="find_table_by_name")
# def find_table_by_name(section_name: str, table_name: str):
#     """
#     Search for a table in a datasheet section by its name (header or caption).

#     Args:
#         section_name (str): The name of the datasheet section (markdown).
#         table_name (str): The name or header of the table to search for.

#     Returns:
#         dict: {
#             "found": bool,
#             "table_markdown": str or None,
#             "start_line": int or None,
#             "end_line": int or None,
#             "message": str
#         }
#     """
#     import re

#     datasheet_section = get_datasheet_section(section_name)
#     # Split section into lines for easier processing
#     lines = datasheet_section.splitlines()
#     table_start = None
#     table_end = None
#     table_lines = []
#     found = False

#     # Try to find a table whose header row contains the table_name (case-insensitive)
#     for idx, line in enumerate(lines):
#         # Markdown table header row: | ... | ... |
#         if re.search(r"\|.*\|", line):
#             # Check if table_name is in the header row (case-insensitive, ignore spaces)
#             if re.search(re.escape(table_name), line, re.IGNORECASE):
#                 # Found a header row with the table name
#                 table_start = idx
#                 # Now, find the end of the table (consecutive lines starting with |)
#                 table_lines = [line]
#                 for j in range(idx + 1, len(lines)):
#                     if lines[j].strip().startswith("|"):
#                         table_lines.append(lines[j])
#                     else:
#                         break
#                 table_end = table_start + len(table_lines) - 1
#                 found = True
#                 break

#     if found:
#         return {
#             "found": True,
#             "table_markdown": "\n".join(table_lines),
#             "start_line": table_start + 1,  # 1-based
#             "end_line": table_end + 1,      # 1-based
#             "message": f"Table '{table_name}' found."
#         }
#     else:
#         return {
#             "found": False,
#             "table_markdown": None,
#             "start_line": None,
#             "end_line": None,
#             "message": f"Table '{table_name}' not found in section."
#         }
