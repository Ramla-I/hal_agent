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
import re

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


def _is_md_table_separator(line: str) -> bool:
    """
    Detect markdown table separator lines like:
      |---|---|
      |:---|---:|
    """
    s = line.strip()
    if "|" not in s:
        return False
    s_inner = s.strip("|").strip()
    if not s_inner:
        return False
    # A separator line is composed of pipes, colons, dashes and spaces.
    if re.fullmatch(r"[:\-\|\s]+", s) is None:
        return False
    # Require at least one dash to avoid matching random pipes.
    return "-" in s_inner


def _is_md_table_row(line: str) -> bool:
    """
    Heuristic for markdown table row lines: contain >=2 pipes and some non-pipe content.
    """
    s = line.rstrip("\n")
    if s.strip().startswith("```"):
        return False
    if s.count("|") < 2:
        return False
    # Must contain something besides pipes/spaces to avoid matching "||||".
    return re.search(r"[A-Za-z0-9]", s) is not None


def _is_table_block_start(lines: list[str], i: int) -> bool:
    """
    Detect the start of a markdown table block.

    Prefer canonical:
      header row + separator row
    But accept consecutive pipe rows as a fallback.
    """
    if i >= len(lines):
        return False
    if _is_md_table_row(lines[i]):
        if i + 1 < len(lines) and _is_md_table_separator(lines[i + 1]):
            return True
        if i + 1 < len(lines) and _is_md_table_row(lines[i + 1]):
            return True
    return False


def _extract_table_block(lines: list[str], start_idx: int) -> tuple[str, int]:
    """
    Extract a contiguous markdown table block starting at start_idx.

    Returns:
      (table_text, next_index_after_block)
    """
    i = start_idx
    table_lines: list[str] = []
    while i < len(lines):
        line = lines[i]
        if _is_md_table_row(line) or _is_md_table_separator(line):
            table_lines.append(line)
            i += 1
            continue
        break

    # Consume one trailing blank line if present.
    if i < len(lines) and lines[i].strip() == "":
        table_lines.append(lines[i])
        i += 1

    return "\n".join(table_lines).rstrip("\n"), i


def chunk_markdown_preserving_tables(
    md_text: str,
    max_tokens: int = 800,
    overlap_tokens: int = 100,
) -> list[str]:
    """
    Split markdown into token-limited chunks while preserving table blocks.

    - Tables are detected via pipe-row/separator heuristics and are never split across chunks.
    - If a single table block exceeds max_tokens, it will be emitted as a single oversize chunk.
    - For non-table text blocks that exceed max_tokens, we fall back to token-based chunking.

    Note: This preserves tables *within a page*. If a table spans multiple pages in the PDF,
    it may still be split across pages upstream (we chunk per page).
    """
    encoding = tiktoken.get_encoding(TIKTOKEN_ENCODING)
    lines = md_text.splitlines()

    # 1) Convert to blocks (either text or a full table block).
    blocks: list[tuple[str, str]] = []  # (kind, text)
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        text = "\n".join(paragraph_lines).strip("\n")
        if text.strip():
            blocks.append(("text", text))
        paragraph_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Keep fenced code blocks intact.
        if line.strip().startswith("```"):
            flush_paragraph()
            code_lines = [line]
            i += 1
            while i < len(lines):
                code_lines.append(lines[i])
                if lines[i].strip().startswith("```"):
                    i += 1
                    break
                i += 1
            blocks.append(("text", "\n".join(code_lines).strip("\n")))
            continue

        if _is_table_block_start(lines, i):
            flush_paragraph()

            # Include an immediately preceding caption line if it looks like a table caption.
            # (Common patterns: "Table 48.", "**Table 48. ...**")
            if i - 1 >= 0:
                prev = lines[i - 1].strip()
                if prev and re.search(r"\btable\b", prev, re.IGNORECASE) and not prev.startswith("#"):
                    blocks.append(("text", prev))

            table_text, next_i = _extract_table_block(lines, i)
            blocks.append(("table", table_text))
            i = next_i
            continue

        paragraph_lines.append(line)
        i += 1

    flush_paragraph()

    # 2) Pack blocks into chunks up to max_tokens, without splitting tables.
    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    def flush_chunk() -> None:
        nonlocal current_parts, current_tokens
        if not current_parts:
            return
        chunks.append("\n\n".join([p for p in current_parts if p.strip()]).strip("\n"))
        current_parts = []
        current_tokens = 0

    for kind, block_text in blocks:
        block_tokens = len(encoding.encode(block_text))

        if kind == "table":
            if current_parts and current_tokens + block_tokens > max_tokens:
                flush_chunk()
            current_parts.append(block_text)
            current_tokens += block_tokens
            # Emit immediately so subsequent text doesn't get glued to the table.
            flush_chunk()
            continue

        # kind == "text"
        if block_tokens > max_tokens:
            flush_chunk()
            chunks.extend([c.strip("\n") for c in chunk_text(block_text, max_tokens=max_tokens, overlap_tokens=overlap_tokens) if c.strip()])
            continue

        if current_parts and current_tokens + block_tokens > max_tokens:
            flush_chunk()

        current_parts.append(block_text)
        current_tokens += block_tokens

    flush_chunk()

    # 3) Apply token overlap between chunks (simple prepend).
    if overlap_tokens <= 0 or len(chunks) <= 1:
        return chunks

    out: list[str] = [chunks[0]]
    prev_tokens = encoding.encode(chunks[0])
    for idx in range(1, len(chunks)):
        current = chunks[idx]
        overlap = encoding.decode(prev_tokens[-overlap_tokens:]) if len(prev_tokens) > overlap_tokens else encoding.decode(prev_tokens)
        out.append((overlap + "\n\n" + current).strip("\n"))
        prev_tokens = encoding.encode(current)

    return out


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
        if format == "markdown":
            page_chunks = chunk_markdown_preserving_tables(page_text, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
        else:
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

    # Save chunk index CSV
    index_path = os.path.join(output_dir, "chunks_index.csv")
    save_metadata_csv(chunk_metadata, index_path)
    print(f"Chunk index saved to: {index_path}")

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
