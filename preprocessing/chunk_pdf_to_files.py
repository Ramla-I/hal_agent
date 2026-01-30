"""
Chunk PDFs into individual text files with trackable IDs for better retrieval analysis.

Usage:
    python chunk_pdf_to_files.py <pdf_path> <output_dir> <datasheet_name> [options]

Examples:
    # Plain text extraction (default, faster)
    python chunk_pdf_to_files.py devices/stm/rm0041/rm0041.pdf chunks/rm0041 rm0041 --max-tokens 800

    # Markdown extraction (better table preservation, slower)
    python chunk_pdf_to_files.py devices/stm/rm0041/rm0041.pdf chunks/rm0041_md rm0041 --format markdown

Options:
    --max-tokens INT       Maximum tokens per chunk (default: 800)
    --overlap-tokens INT   Token overlap between chunks (default: 100)
    --format {text,markdown}  Extraction format (default: text)
                          - text: Plain text extraction (faster, tables broken)
                          - markdown: Markdown conversion (slower, better table structure)
"""

import argparse
import os
import sys
from pathlib import Path
import tiktoken
import pymupdf  # PyMuPDF
import pymupdf4llm  # For markdown conversion

# Import encoding from config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TIKTOKEN_ENCODING


def count_tokens(text: str) -> int:
    """Count tokens in text using the encoding specified in config."""
    encoding = tiktoken.get_encoding(TIKTOKEN_ENCODING)
    return len(encoding.encode(text))


def chunk_text(text: str, max_tokens: int = 800, overlap_tokens: int = 100) -> list[str]:
    """
    Split text into chunks of approximately max_tokens with overlap.

    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Number of tokens to overlap between chunks

    Returns:
        List of text chunks
    """
    encoding = tiktoken.get_encoding(TIKTOKEN_ENCODING)
    tokens = encoding.encode(text)

    chunks = []
    start = 0

    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)

        # Move to next chunk with overlap
        start = end - overlap_tokens

        # Avoid infinite loop on very small texts
        if end >= len(tokens):
            break

    return chunks


def extract_text_plain(pdf_path: str) -> dict[int, str]:
    """
    Extract plain text from PDF page by page.

    Returns:
        Dictionary mapping page number (0-indexed) to page text
    """
    doc = pymupdf.open(pdf_path)
    pages = {}

    for page_num in range(len(doc)):
        page = doc[page_num]
        pages[page_num] = page.get_text()

    doc.close()
    return pages


def extract_text_markdown(pdf_path: str) -> dict[int, str]:
    """
    Extract text from PDF as markdown (better table preservation).

    Returns:
        Dictionary mapping page number (0-indexed) to page text in markdown
    """
    # pymupdf4llm can convert entire document to markdown
    # It processes page by page internally but returns concatenated result
    md_text = pymupdf4llm.to_markdown(pdf_path)

    # We need to split by pages - pymupdf4llm includes page markers
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    # Split markdown by page markers (pymupdf4llm adds "-----" markers)
    # For now, we'll process the whole document and split by page using pymupdf
    # Then convert each page individually
    doc = pymupdf.open(pdf_path)
    pages = {}

    for page_num in range(total_pages):
        # Convert single page to markdown
        page_md = pymupdf4llm.to_markdown(pdf_path, pages=[page_num])
        pages[page_num] = page_md

    doc.close()
    return pages


def extract_and_chunk_pdf(
    pdf_path: str,
    output_dir: str,
    datasheet_name: str,
    max_tokens: int = 800,
    overlap_tokens: int = 100,
    format: str = "text"
) -> list[dict]:
    """
    Extract text from PDF, chunk it, and save to individual files.

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save chunk files
        datasheet_name: Short name for the datasheet (e.g., 'rm0041')
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Token overlap between chunks
        format: 'text' for plain text or 'markdown' for markdown conversion

    Returns:
        List of chunk metadata dictionaries
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Extract pages based on format
    print(f"Processing {pdf_path} (format: {format})...")

    if format == "markdown":
        pages_dict = extract_text_markdown(pdf_path)
    else:
        pages_dict = extract_text_plain(pdf_path)

    total_pages = len(pages_dict)
    print(f"Extracted {total_pages} pages")

    chunk_metadata = []
    global_chunk_id = 0

    for page_num in sorted(pages_dict.keys()):
        page_text = pages_dict[page_num]

        # Skip empty pages
        if not page_text.strip():
            print(f"  Page {page_num + 1}: Empty, skipping")
            continue

        # Chunk the page text
        page_chunks = chunk_text(page_text, max_tokens, overlap_tokens)

        print(f"  Page {page_num + 1}: {len(page_chunks)} chunks ({count_tokens(page_text)} tokens)")

        # Save each chunk as a separate file
        for chunk_idx, chunk_content in enumerate(page_chunks):
            global_chunk_id += 1

            # Create chunk ID: datasheet_pXX_cYY
            chunk_id = f"{datasheet_name}_p{page_num + 1:03d}_c{chunk_idx + 1:02d}"
            chunk_filename = f"{chunk_id}.txt"
            chunk_path = os.path.join(output_dir, chunk_filename)

            # Save chunk to file
            with open(chunk_path, 'w', encoding='utf-8') as f:
                f.write(chunk_content)

            # Track metadata
            metadata = {
                'chunk_id': chunk_id,
                'file_path': chunk_path,
                'datasheet': datasheet_name,
                'page_number': page_num + 1,
                'chunk_index': chunk_idx + 1,
                'total_chunks_on_page': len(page_chunks),
                'global_chunk_index': global_chunk_id,
                'token_count': count_tokens(chunk_content),
                'char_count': len(chunk_content)
            }
            chunk_metadata.append(metadata)

    print(f"\nTotal chunks created: {global_chunk_id}")
    print(f"Saved to: {output_dir}/")

    # Save metadata summary
    metadata_path = os.path.join(output_dir, f"{datasheet_name}_chunks_metadata.csv")
    save_metadata_csv(chunk_metadata, metadata_path)
    print(f"Metadata saved to: {metadata_path}")

    return chunk_metadata


def save_metadata_csv(chunk_metadata: list[dict], output_path: str):
    """Save chunk metadata to CSV file."""
    import csv

    if not chunk_metadata:
        return

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=chunk_metadata[0].keys())
        writer.writeheader()
        writer.writerows(chunk_metadata)


def main():
    parser = argparse.ArgumentParser(
        description="Chunk PDF into individual text files with trackable IDs"
    )
    parser.add_argument(
        "pdf_path",
        help="Path to PDF file"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save chunk files"
    )
    parser.add_argument(
        "datasheet_name",
        help="Short name for the datasheet (e.g., 'rm0041')"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=800,
        help="Maximum tokens per chunk (default: 800)"
    )
    parser.add_argument(
        "--overlap-tokens",
        type=int,
        default=100,
        help="Token overlap between chunks (default: 100)"
    )
    parser.add_argument(
        "--format",
        choices=["text", "markdown"],
        default="text",
        help="Extraction format: 'text' for plain text (default) or 'markdown' for better table preservation"
    )

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)

    # Extract and chunk
    chunk_metadata = extract_and_chunk_pdf(
        args.pdf_path,
        args.output_dir,
        args.datasheet_name,
        args.max_tokens,
        args.overlap_tokens,
        args.format
    )

    print(f"\n✓ Successfully created {len(chunk_metadata)} chunks")


if __name__ == "__main__":
    main()
