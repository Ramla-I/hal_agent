from agents import function_tool, RunContextWrapper
import os
import sys
from pathlib import Path
import fitz
from pdf_ops import extract_markdown_from_pdf, create_pdf_from_pages, extract_text_from_pdf
from extract_section_regex import extract_section_regex
from get_pages_with_keyword import get_pages_with_keyword

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)
from defs import UserContext, Manufacturer, PreprocessingMethod
from config import CURRENT_PREPROCESSING_METHOD

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

def datasheet_path_md(device_name: str) -> str:
    return os.path.join(defs.DEVICE_DIRECTORY, device_name, f"{device_name}.md")

def datasheet_path_pdf(device_name: str) -> str:
    return os.path.join(defs.DEVICE_DIRECTORY, device_name, f"{device_name}.pdf")

def all_svd_file_paths(device_name: str) -> list[str]:
    device_dir = os.path.join(defs.DEVICE_DIRECTORY, device_name)
    svd_files = []
    if os.path.isdir(device_dir):
        for fname in os.listdir(device_dir):
            if fname.lower().endswith('.svd'):
                svd_files.append(os.path.join(device_dir, fname))
    return svd_files

@function_tool(name_override="fetch_svd")  
def get_svd_file(wrapper: RunContextWrapper[UserContext], id: int) -> str:
    svd_files = get_all_svd_file_paths(wrapper.context.device_name)
    if id < 0 or id >= len(svd_files):
        raise IndexError(f"SVD file id {id} is out of range (There are {len(wrapper.context.svd_path)} entries).")
    with open(wrapper.context.svd_path[id], "r") as file:
        return file.read()
    
@function_tool(name_override="fetch_datasheet_md")  
def get_datasheet_md(wrapper: RunContextWrapper[UserContext]) -> str:
    datasheet_path = datasheet_path_md(wrapper.context.device_name)
    if not os.path.exists(datasheet_path):
        # If the .md file doesn't exist, convert the PDF to markdown and save it
        pdf_path = datasheet_path_pdf(wrapper.context.device_name)
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Neither markdown nor PDF datasheet found for device {wrapper.context.device_name}")
        md_text = extract_markdown_from_pdf(pdf_path)
        # Save the generated markdown for future use
        os.makedirs(os.path.dirname(datasheet_path), exist_ok=True)
        with open(datasheet_path, "w") as md_file:
            md_file.write(md_text) 

    with open(datasheet_path, "r") as file:
        return file.read()

@function_tool(name_override="fetch_datasheet_pdf")  
def get_datasheet_pdf(wrapper: RunContextWrapper[UserContext]) -> str:
    datasheet_path = datasheet_path_pdf(wrapper.context.device_name)
    with open(datasheet_path, "r") as file:
        return file.read()

@function_tool(name_override="fetch_driver")  
def get_driver(wrapper: RunContextWrapper[UserContext]) -> str:
    with open(wrapper.context.driver_path, "r") as file:
        return file.read()

@function_tool(name_override="fetch_datasheet_section") 
def get_datasheet_section(wrapper: RunContextWrapper[UserContext], tables_only: bool = False) -> str:
    if wrapper.context.manufacturer == Manufacturer.INTEL:
        return extract_section_regex(datasheet_path_md(wrapper.context.device_name), wrapper.context.peripheral_name, tables_only, manufacturer="Intel")
    elif wrapper.context.manufacturer == Manufacturer.STM:
        if CURRENT_PREPROCESSING_METHOD == PreprocessingMethod.DDM:
            print("Preprocessing method is DDM, not completely implemented yet")
            return ""
        elif CURRENT_PREPROCESSING_METHOD == PreprocessingMethod.REGEX:
            return extract_section_regex(datasheet_path_md(wrapper.context.device_name), wrapper.context.peripheral_name, tables_only, manufacturer="STM")
        elif CURRENT_PREPROCESSING_METHOD == PreprocessingMethod.VECTOR_STORE:
            print("Preprocessing method is VECTOR_STORE, not implemented yet")
            return ""
        elif CURRENT_PREPROCESSING_METHOD == PreprocessingMethod.KEYWORD_SEARCH:
            return get_pages_with_keyword(datasheet_path_pdf(wrapper.context.device_name), wrapper.context.peripheral_name)
        else:
            raise ValueError(f"Preprocessing method {CURRENT_PREPROCESSING_METHOD} not supported")
    else:
        raise ValueError(f"Manufacturer {wrapper.context.manufacturer} not supported")
    

@function_tool(name_override="split_datasheet")
def split_datasheet_get_section(wrapper: RunContextWrapper[UserContext], n: int, i: int) -> str:
    """
    Splits the datasheet into n sections and returns the ith section (0-based).
    """
    # Read the datasheet content
    with open(datasheet_path_md(wrapper.context.device_name), "r") as file:
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
    # distributing any "leftover" lines to the earlier sections so that no lines are lost.
    start = i * section_size + min(i, remainder)
    end = start + section_size
    if i < remainder:
        end += 1
    section_lines = lines[start:end]
    return "".join(section_lines)


@function_tool
def get_table_of_contents(wrapper: RunContextWrapper[UserContext], md: bool = False) -> str:
    """
    Returns the table of contents of the datasheet.
    """ 
    pages_to_search = 50
    pdf_path = Path(datasheet_path_pdf(wrapper.context.device_name))

    # Check if the PDF exists
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    extracted_pdf_path = create_pdf_from_pages(pdf_path, 0, pages_to_search)
    toc_text = ""

    if md:
        toc_text = extract_markdown_from_pdf(extracted_pdf_path)
    else:
        toc_text = extract_text_from_pdf(extracted_pdf_path)
    return toc_text

    # try:
    #     doc = fitz.open(pdf_path)
    # except Exception as e:
    #     print(f"Error opening PDF {pdf_path}: {e}")
    #     return None

    # toc_text = ""
    # # Heuristic: extract text from first 30 pages for ToC.
    # # This might need to be adjusted for different documents.
    # for page_num in range(min(pages_to_search, doc.page_count)):
    #     page = doc.load_page(page_num)
    #     toc_text += page.get_text()