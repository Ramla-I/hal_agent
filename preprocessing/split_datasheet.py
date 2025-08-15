#!/usr/bin/env python3
"""
This script finds chapter boundaries in a PDF document using GPT and splits it into sections.
It performs the following steps:
1. Extracts text from the first N pages to find the table of contents
2. Uses GPT to identify chapter start/end page numbers
3. Splits the PDF into separate files for each chapter
4. Converts each chapter to markdown format
5. Savesboth the pdf and the markdown files in the output directory
"""

import fitz  # PyMuPDF
import openai
import json
import os
import argparse
from pydantic import BaseModel, Field
import pymupdf4llm

class Chapter(BaseModel):
    title: str = Field(description="The title of the chapter")
    start_page: int = Field(description="The page number where the chapter starts")
    end_page: int = Field(description="The page number where the chapter ends")

class ChapterBoundaries(BaseModel): 
    chapters: list[Chapter] = Field(description="The list of chapters with their titles, start and end pages")

def find_chapter_boundaries(pdf_path, pages_to_search):
    """
    Finds the start page of chapters in a PDF by querying GPT.
    It returns a list of chapters with their titles and guessed start and end pages.
    """
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

    # Use OpenAI GPT to extract chapter boundaries.
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set.")
        doc.close()
        return None

    client = openai.OpenAI()

    prompt = f"""
    Based on the following table of contents from a technical reference manual, identify the starting page number for each main chapter.
    A chapter typically starts with a number (e.g., "4 CRC Calculation Unit", "5 Power controller (PWR)").
    Ignore sub-sections, list of figures, tables, and appendices unless they are major sections.

    Please return the result as a JSON object where keys are the full chapter titles and values are their corresponding page numbers (as integers).

    Table of Contents Text:
    ---
    {toc_text}
    ---

    JSON output:
    """


    response = client.chat.completions.parse(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You are an assistant that extracts structured data from text."},
            {"role": "user", "content": prompt}
        ],
        response_format=ChapterBoundaries
    )

    chapter_boundaries = response.choices[0].message.parsed
    
    if not chapter_boundaries:
        print("GPT could not identify any chapters.")
        doc.close()
        return None
        
    # Make chapter boundaries contiguous by updating end pages
    for i in range(len(chapter_boundaries.chapters) - 1):
        current_chapter = chapter_boundaries.chapters[i]
        next_chapter = chapter_boundaries.chapters[i + 1]
        # If there's a gap between chapters, update the end page of current chapter
        if current_chapter.end_page + 1 < next_chapter.start_page:
            current_chapter.end_page = next_chapter.start_page - 1

    doc.close()
    return chapter_boundaries


def split_pdf_by_chapters(pdf_path, chapter_boundaries, output_dir):
    """
    Splits a PDF into multiple PDFs, one for each chapter.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
        
    try:
        original_doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF {pdf_path}: {e}")
        return
    
    # Save chapter boundaries to JSON file
    boundaries_path = os.path.join(output_dir, "..", "chapter_boundaries.json")
    try:
        with open(boundaries_path, "w") as f:
            json.dump(chapter_boundaries.model_dump(), f, indent=2)
        print(f"Saved chapter boundaries to {boundaries_path}")
    except Exception as e:
        print(f"Error saving chapter boundaries to {boundaries_path}: {e}")

    for chapter in chapter_boundaries.chapters:
        title = chapter.title
        start_page = chapter.start_page
        end_page = chapter.end_page

        # Sanitize chapter title to create a valid filename
        sanitized_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip()
        sanitized_title = sanitized_title.replace(' ', '_')
        output_filename = f"{sanitized_title}.pdf"
        output_filepath = os.path.join(output_dir, output_filename)
        
        # Convert 1-indexed page numbers from ToC to 0-indexed for fitz
        start_idx = start_page - 1
        end_idx = end_page - 1 if end_page is not None else original_doc.page_count -1

        if start_idx < 0 or start_idx >= original_doc.page_count or end_idx >= original_doc.page_count or start_idx > end_idx:
            print(f"Warning: Invalid page range for chapter '{title}' ({start_page}-{end_page}). Skipping.")
            continue
            
        new_doc = fitz.open()
        new_doc.insert_pdf(original_doc, from_page=start_idx, to_page=end_idx)
        
        try:
            new_doc.save(output_filepath)
            # print(f"Successfully created '{output_filepath}' (pages {start_page}-{end_page}).")
        except Exception as e:
            print(f"Error saving file {output_filepath}: {e}")
        
        new_doc.close()

        # Now save the new document as markdown as well
        with open(output_filepath.replace('.pdf', '.md'), 'w', encoding="utf-8") as f:
            f.write(pymupdf4llm.to_markdown(output_filepath))


    original_doc.close()

def main():
    parser = argparse.ArgumentParser(
        description="Split a PDF reference manual into separate PDFs for each chapter using AI to find chapter boundaries.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("pdf_path", help="Path to the source PDF file.")
    parser.add_argument("output_dir", help="The directory where chapter PDFs will be saved.")
    parser.add_argument("--pages", help="Number of pages for the table of contents from the from the start of the pdf, default is 40", default=40, type=int)
    
    args = parser.parse_args()

    # print(f"Finding chapter boundaries for {args.pdf_path}...")
    # boundaries = find_chapter_boundaries(args.pdf_path, args.pages)
    # # print(boundaries)

    # if boundaries:
    #     print("Chapter boundaries found. Splitting PDF...")
    #     split_pdf_by_chapters(args.pdf_path, boundaries, args.output_dir)
    #     print("PDF splitting complete.")
    # else:
    #     print("Could not find chapter boundaries.")

    with open(args.pdf_path.replace('.pdf', '.md'), 'w', encoding="utf-8") as f:
        f.write(pymupdf4llm.to_markdown(args.pdf_path))

if __name__ == "__main__":
    main()
    