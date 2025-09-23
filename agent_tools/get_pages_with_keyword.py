from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral # to run main, remove agent_tools. at the beginning
from pydantic import BaseModel, Field
import json
import os
import tempfile
from PyPDF2 import PdfReader, PdfWriter

class KeywordPage(BaseModel):
    keyword: str = Field(description="The keyword that was initially searched for")
    keyword_found: str = Field(description="The keyword that was found on the pages")
    pages: list[int] = Field(description="The list of page numbers where the keyword was found")

def find_keyword_page_numbers(pdf_path, keyword):
    """
    Returns a list of page numbers (0-based) where the keyword appears in the PDF.
    """
    keyword = keyword.lower()
    pages_with_keyword = []
    with open(pdf_path, 'rb') as f:
        reader = PdfReader(f)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and keyword in text.lower():
                pages_with_keyword.append(i)
    return pages_with_keyword

def get_pages_with_keyword(pdf_path, keyword):
    """
    Returns the markdown content of the pages where the keyword appears in the PDF.
    """
    pages = find_keyword_page_numbers(pdf_path, keyword)
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

def main_svd():
    import sys
    if len(sys.argv) != 3:
        print("Usage: python test.py <pdf_path> <svd_path>")
        return
    pdf_path = sys.argv[1]
    svd_path = sys.argv[2]

    keyword_infos = []
    peripheral_names = get_peripheral_names([svd_path])
    for peripheral_name in peripheral_names:
        # If peripheral_name ends with a number, extract the part without the number
        # import re
        # match_periph = re.match(r"^(.*?)(\d+)$", peripheral_name)
        # if match_periph:
        #     peripheral_name_no_number = match_periph.group(1)

        register_names = get_register_names_for_peripheral([svd_path], peripheral_name)
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
                # Optionally, you could use joint_name_no_number for further processing or searching

            pages = find_keyword_pages(pdf_path, joint_name)
            keyword_info = None
            if pages:
                keyword_info = KeywordPage(
                    keyword=joint_name,
                    keyword_found=joint_name,
                    pages=pages
                )
            elif joint_name_no_number:
                pages = find_keyword_page_numbers(pdf_path, joint_name_no_number)
                if pages:
                    keyword_info = KeywordPage(
                        keyword=joint_name,
                        keyword_found=joint_name_no_number,
                        pages=pages
                    )
                else:
                    keyword_info = KeywordPage(
                        keyword=joint_name,
                        keyword_found="",
                        pages=[]
                    )
            else:
                keyword_info = KeywordPage(
                    keyword=joint_name,
                    keyword_found="",
                    pages=[]
                )
            
            keyword_infos.append(keyword_info.model_dump())
            print(keyword_info)
    
    with open("keyword_infos.json", "w") as f:
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
    # main_svd()