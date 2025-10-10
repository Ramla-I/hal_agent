from PyPDF2 import PdfWriter,PdfReader
import pymupdf4llm
import os

def split_pdf(pdf_path, num_split_pdfs=40, output_path="../datasheet/82599/82599_datasheet_split"):
    """
    Splits a PDF file into a specified number of smaller PDF files, each containing approximately
    an equal number of pages. The split PDFs are saved to disk with filenames based on the output_path.

    Args:
        pdf_path (str): Path to the input PDF file.
        num_split_pdfs (int, optional): Number of parts to split the PDF into. Defaults to 40.
        output_path (str, optional): Base path for the output split PDF files. Each split will be
            saved as output_path_<index>.pdf. Defaults to "../datasheet/82599/82599_datasheet_split".

    Raises:
        FileNotFoundError: If the input PDF file does not exist.

    Example:
        split_pdf("myfile.pdf", num_split_pdfs=10, output_path="output/split")
        # This will create files: output/split_0.pdf, output/split_1.pdf, ..., output/split_9.pdf
    """
    pdf_path = pdf_path.strip('\'"')
    pdf_path = os.path.normpath(pdf_path)

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"The file at {pdf_path} does not exist.")
    
    with open(pdf_path, 'rb') as file:
        input_pdf = PdfReader(file)
        pdf_len = int(len(input_pdf.pages))
        print(pdf_len)

        split_pdf_len = int(pdf_len / num_split_pdfs)
        remainder = pdf_len % num_split_pdfs

        pdfs = []

        for i in range(num_split_pdfs):
            pdfs.append(PdfWriter())
            for j in range(split_pdf_len):
                page = input_pdf.pages[i * split_pdf_len + j]
                pdfs[i].add_page(page)

        assert(len(pdfs) == num_split_pdfs)
        # add the remainder pages to the last pdf
        for i in range(remainder):
            page = input_pdf.pages[num_split_pdfs * split_pdf_len + i]
            pdfs[num_split_pdfs - 1].add_page(page)

        sum = 0
        for i in range(num_split_pdfs):
            sum += len(pdfs[i].pages)

        assert(sum == pdf_len)

        for i in range(num_split_pdfs):
            with open(output_path + "_" + str(i) + ".pdf", "wb") as f:
                pdfs[i].write(f)



def create_pdf_from_pages(pdf_path, page_start=None, page_end=None):
    """
    Extracts a specific range of pages from a PDF file and saves them as a new PDF.

    Args:
        pdf_path (str): Path to the input PDF file.
        page_start (int, optional): The starting page number (1-based). If None, starts from the first page.
        page_end (int, optional): The ending page number (1-based, exclusive). If None or greater than total pages, extracts to the last page.

    Returns:
        str: The path to the newly created PDF file containing the extracted pages.

    Raises:
        FileNotFoundError: If the input PDF file does not exist.
    """
    pdf_path = pdf_path.strip('\'"')
    pdf_path = os.path.normpath(pdf_path)

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"The file at {pdf_path} does not exist.")
    with open(pdf_path, 'rb') as file:
        input_pdf = PdfReader(file)

        if input_pdf.is_encrypted:
            input_pdf.decrypt("")

        total_pages = len(input_pdf.pages)
        if page_start is None:
            page_start = 0
        if page_end is None or page_end > total_pages:
            page_end = total_pages
        print("total_pages: ", total_pages)
        pdf = PdfWriter()
        if page_start != 0:
            page_start = page_start - 1
        for page_num in range(page_start, page_end):
            print(f"Adding page {page_num}")
            print(f"Page {page_num} is {input_pdf.pages[page_num]}")
            pdf.add_page(input_pdf.pages[page_num])
        # Save the new PDF path to a variable for later use
        new_pdf_path = pdf_path + "_" + str(page_start) + "_" + str(page_end) + ".pdf"
        with open(new_pdf_path, "wb") as f:
            pdf.write(f)    

        return new_pdf_path



def extract_pages_from_pdf(pdf_path, pages):
    """
    Extracts the specified pages from a PDF file, converts them to markdown using pymupdf4llm, and returns the resulting markdown string.

    Args:
        pdf_path (str): Path to the PDF file.
        pages (list[int]): List of page numbers to extract (0-based).

    Returns:
        str: Markdown content of the extracted pages.
    """
    pdf_path = pdf_path.strip('\'"')
    pdf_path = os.path.normpath(pdf_path)

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"The file at {pdf_path} does not exist.")

    with open(pdf_path, 'rb') as file:
        input_pdf = PdfReader(file)
        total_pages = len(input_pdf.pages)
        writer = PdfWriter()
        for page_num in pages:
            # Convert 1-based to 0-based index
            idx = page_num
            if idx < 0 or idx >= total_pages:
                raise ValueError(f"Page number {page_num} is out of range for file with {total_pages} pages.")
            writer.add_page(input_pdf.pages[idx])
        # Create a new PDF file with the extracted pages
        # Convert the extracted pages to markdown and return the markdown string
        import tempfile
        import pymupdf4llm

        base, ext = os.path.splitext(pdf_path)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            writer.write(temp_pdf)
            temp_pdf_path = temp_pdf.name

        md_text = pymupdf4llm.to_markdown(temp_pdf_path)
        os.remove(temp_pdf_path)
        # INSERT_YOUR_CODE
        with open("output.md", "w", encoding="utf-8") as out_md:
            out_md.write(md_text)
        return md_text



def extract_text_from_pdf(pdf_path, page_start=None, page_end=None):
    """
    Extracts the specified pages from a PDF file and returns the extracted text as a string.

    Args:
        pdf_path (str): Path to the PDF file.
        page_start (int, optional): The starting page number (1-based). If None, starts from the first page.
        page_end (int, optional): The ending page number (1-based, exclusive). If None or greater than total pages, extracts to the last page.

    Returns:
        str: Extracted text from the specified pages.
    """
    pdf_path = pdf_path.strip('\'"')
    pdf_path = os.path.normpath(pdf_path)

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"The file at {pdf_path} does not exist.")
        
    text = ''
    
    with open(pdf_path, 'rb') as file:
        reader = PdfReader(file)

        total_pages = len(reader.pages)
        if page_start is None:
            page_start = 0
        if page_end is None or page_end > total_pages:
            page_end = total_pages

        for page_num in range(page_start, page_end):
            text += reader.pages[page_num].extract_text()
    
    return text

def extract_markdown_from_pdf(pdf_path):
    md_text = pymupdf4llm.to_markdown(pdf_path)
    return md_text

def pdf_page_to_markdown(pdf_path, page_num):
    pdf_path = pdf_path.strip('\'"')
    pdf_path = os.path.normpath(pdf_path)

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"The file at {pdf_path} does not exist.")

    with open(pdf_path, 'rb') as file:
        input_pdf = PdfReader(file)
        total_pages = len(input_pdf.pages)
        writer = PdfWriter()
        
        idx = page_num
        if idx < 0 or idx >= total_pages:
            raise ValueError(f"Page number {page_num} is out of range for file with {total_pages} pages.")
        writer.add_page(input_pdf.pages[idx])
        # Create a new PDF file with the extracted pages
        # Convert the extracted pages to markdown and return the markdown string
        import tempfile
        import pymupdf4llm

        base, ext = os.path.splitext(pdf_path)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            writer.write(temp_pdf)
            temp_pdf_path = temp_pdf.name

        md_text = pymupdf4llm.to_markdown(temp_pdf_path)
        os.remove(temp_pdf_path)
        return md_text