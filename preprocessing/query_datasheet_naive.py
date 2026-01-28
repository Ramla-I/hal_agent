#!/usr/bin/env python3
"""
Extract structural metadata from a datasheet using a naive/open-ended approach.

This script takes a zero-knowledge approach: instead of asking specific questions,
it explains the project context to the LLM and asks it to identify what formatting
information would be useful for register extraction and semantic retrieval.

This approach helps discover datasheet-specific patterns that predefined questions
might miss, and can suggest improvements to the extraction prompts.

Supports both OpenAI and Google Gemini models with large context windows.

Usage:
    # Using OpenAI (default)
    python preprocessing/query_datasheet_naive.py devices/stm/rm0041/rm0041.pdf

    # Using Gemini (larger context window)
    python preprocessing/query_datasheet_naive.py devices/stm/rm0041/rm0041.pdf --provider gemini

Environment Variables:
    OPENAI_API_KEY: Required for OpenAI models
    GOOGLE_API_KEY: Required for Gemini models

Dependencies:
    OpenAI: pip install openai
    Gemini: pip install google-genai
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.result_saver import ResultSaver, UsageStats

# Project context and open-ended prompt
NAIVE_PROMPT = """You are an expert at analyzing hardware datasheets and reference manuals.

## Project Context

We are building an automated system to extract register information from hardware datasheets. The pipeline works as follows:

1. **Chunking**: The datasheet (PDF) is split into smaller text chunks for processing.
2. **Semantic Search**: When we need to extract information about a specific register (e.g., "GPIO_CR1"), we use semantic search to retrieve the most relevant chunks from the datasheet.
3. **LLM Extraction**: The retrieved chunks are passed to an LLM that extracts structured register data including:
   - Register name and address offset
   - Reset value
   - Bit fields (name, bit range, access type, description)
   - Enumerated values for each field

## The Challenge

Different datasheets from different manufacturers (STM, Intel, NXP, TI, etc.) use different formatting conventions. These variations can affect:
- How well semantic search retrieves the right chunks
- How accurately the LLM extracts register information
- How we normalize and compare extracted data against reference files (SVD)

## Your Task

Analyze this datasheet and provide:

1. **Formatting Metadata**: What formatting conventions and patterns are used in this datasheet that would be important to know before processing it? Consider:
   - Naming conventions (registers, bitfields, peripherals)
   - How information is structured (tables, prose, diagrams)
   - Any compact notations or abbreviations used
   - Page ranges that contain actual register content vs. front/back matter

2. **Retrieval Optimization**: What information about this datasheet's format would help improve semantic search retrieval? For example:
   - How are registers referenced/named in the text?
   - Are there patterns that could help expand search queries?
   - What sections are most informative for register details?

3. **Extraction Hints**: What should the extraction LLM know about this specific datasheet to accurately parse register information? For example:
   - How are reset values formatted?
   - How are access types specified?
   - Any unusual conventions or edge cases?

4. **Suggested Prompt Improvements**: Based on your analysis, what specific instructions or examples should we add to our extraction prompts to handle this datasheet better?

Please structure your response as a JSON object with keys: "formatting_metadata", "retrieval_optimization", "extraction_hints", and "prompt_improvements". Each section should contain detailed findings with specific examples from the datasheet."""


def read_pdf_content(pdf_path: str, sample_pages: int = 0) -> str:
    """Extract text content from a PDF file.

    Args:
        pdf_path: Path to the PDF file
        sample_pages: If > 0, sample this many pages from beginning, middle, and end.
                     If 0, read all pages.
    """
    try:
        import pymupdf
    except ImportError:
        print("Error: pymupdf is required for PDF processing.")
        print("Install with: pip install pymupdf")
        sys.exit(1)

    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)

    # Determine which pages to read
    if sample_pages > 0 and total_pages > sample_pages:
        # Sample pages from beginning (40%), middle (40%), and end (20%)
        begin_count = int(sample_pages * 0.4)
        middle_count = int(sample_pages * 0.4)
        end_count = sample_pages - begin_count - middle_count

        # Beginning pages
        begin_pages = list(range(0, min(begin_count, total_pages)))

        # Middle pages (centered around the middle of the document)
        middle_start = (total_pages - middle_count) // 2
        middle_pages = list(range(middle_start, middle_start + middle_count))

        # End pages
        end_pages = list(range(max(0, total_pages - end_count), total_pages))

        # Combine and deduplicate while preserving order
        pages_to_read = []
        seen = set()
        for p in begin_pages + middle_pages + end_pages:
            if p not in seen:
                pages_to_read.append(p)
                seen.add(p)

        print(f"  Sampling {len(pages_to_read)} pages from {total_pages} total pages")
        print(f"  Pages: {begin_count} from start, {middle_count} from middle, {end_count} from end")
    else:
        pages_to_read = list(range(total_pages))

    text_parts = []
    for page_num in pages_to_read:
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

    doc.close()
    return "\n\n".join(text_parts)


def read_markdown_content(md_path: str) -> str:
    """Read content from a markdown file."""
    with open(md_path, 'r', encoding='utf-8') as f:
        return f.read()


def read_datasheet(file_path: str, sample_pages: int = 0) -> str:
    """Read datasheet content from PDF or markdown file.

    Args:
        file_path: Path to the datasheet file
        sample_pages: For PDFs, if > 0, sample this many pages instead of reading all
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix == '.pdf':
        return read_pdf_content(file_path, sample_pages=sample_pages)
    elif suffix in ['.md', '.markdown', '.txt']:
        return read_markdown_content(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .pdf, .md, or .txt")


def query_openai(
    content: str,
    model: str = "gpt-4.1",
    temperature: float = 0.0
) -> dict:
    """Query OpenAI model with datasheet content."""
    try:
        from openai import OpenAI
    except ImportError:
        print("Error: openai package is required for OpenAI models.")
        print("Install with: pip install openai")
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    user_prompt = f"""Here is the datasheet content:

{content}

---

{NAIVE_PROMPT}"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        response_format={"type": "json_object"}
    )

    # Build usage stats
    cached_tokens = 0
    if hasattr(response.usage, 'prompt_tokens_details') and response.usage.prompt_tokens_details:
        cached_tokens = getattr(response.usage.prompt_tokens_details, 'cached_tokens', 0) or 0

    usage_stats = UsageStats(
        model_name=model,
        input_tokens=response.usage.prompt_tokens,
        cached_tokens=cached_tokens,
        output_tokens=response.usage.completion_tokens,
        reasoning_tokens=0,
        total_tokens=response.usage.total_tokens
    )

    result = {
        "provider": "openai",
        "model": model,
        "raw_response": response.choices[0].message.content,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        },
        "usage_stats": usage_stats
    }

    try:
        result["answers"] = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        result["answers"] = {"error": "Failed to parse JSON response"}

    return result


def query_gemini(
    content: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.0
) -> dict:
    """Query Google Gemini model with datasheet content."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("Error: google-genai package is required for Gemini models.")
        print("Install with: pip install google-genai")
        sys.exit(1)

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable is not set.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    prompt = f"""Here is the datasheet content:

{content}

---

{NAIVE_PROMPT}

Respond with only the JSON object, no other text."""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json"
        )
    )

    # Extract usage metadata
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
        completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
        total_tokens = getattr(response.usage_metadata, 'total_token_count', 0)

    # Build usage stats
    usage_stats = UsageStats(
        model_name=model,
        input_tokens=prompt_tokens,
        cached_tokens=0,
        output_tokens=completion_tokens,
        reasoning_tokens=0,
        total_tokens=total_tokens
    )

    result = {
        "provider": "gemini",
        "model": model,
        "raw_response": response.text,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        },
        "usage_stats": usage_stats
    }

    try:
        result["answers"] = json.loads(response.text)
    except json.JSONDecodeError:
        result["answers"] = {"error": "Failed to parse JSON response", "raw": response.text}

    return result


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract datasheet metadata using a naive/open-ended approach.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script uses a zero-knowledge approach: instead of asking specific questions,
it explains the project context and asks the LLM to identify useful formatting
information and suggest prompt improvements.

Examples:
    # Using OpenAI (default)
    python %(prog)s devices/stm/rm0041/rm0041.pdf

    # Using Gemini (larger context window)
    python %(prog)s devices/stm/rm0041/rm0041.pdf --provider gemini

    # Sample pages for large PDFs
    python %(prog)s devices/stm/rm0041/rm0041.pdf --provider gemini --sample-pages 100

Supported models:
    OpenAI: gpt-4.1 (default, 1M context)
    Gemini: gemini-2.5-flash (default, 1M context)
        """
    )

    parser.add_argument(
        "datasheet",
        nargs="?",
        default=None,
        help="Path to the datasheet file (PDF, markdown, or text)"
    )

    parser.add_argument(
        "-p", "--provider",
        choices=["openai", "gemini"],
        default="openai",
        help="LLM provider to use (default: openai)"
    )

    parser.add_argument(
        "-m", "--model",
        default=None,
        help="Model name (default: gpt-4.1 for OpenAI, gemini-2.5-flash for Gemini)"
    )

    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output file path for JSON results (default: preprocessing_naive_{model}.json alongside datasheet)"
    )

    parser.add_argument(
        "-t", "--temperature",
        type=float,
        default=0.0,
        help="Temperature for generation (default: 0.0)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "-s", "--sample-pages",
        type=int,
        default=0,
        help="Sample N pages from beginning/middle/end instead of reading all (useful for large PDFs with API limits)"
    )

    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Show the naive prompt and exit"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # Handle --show-prompt
    if args.show_prompt:
        print("Naive prompt:")
        print("-" * 70)
        print(NAIVE_PROMPT)
        return 0

    # Validate datasheet is provided
    if not args.datasheet:
        print("Error: datasheet argument is required")
        print("Usage: python query_datasheet_naive.py <datasheet> [options]")
        return 1

    # Validate datasheet path
    if not os.path.exists(args.datasheet):
        print(f"Error: Datasheet not found: {args.datasheet}")
        return 1

    # Determine model
    if args.model:
        model = args.model
    elif args.provider == "openai":
        model = "gpt-4.1"
    else:
        model = "gemini-2.5-flash"

    # Determine output path (default: alongside datasheet as preprocessing_naive_{model}.json)
    if args.output:
        output_path = args.output
    else:
        datasheet_dir = os.path.dirname(os.path.abspath(args.datasheet))
        # Sanitize model name for filename (replace slashes, etc.)
        model_safe = model.replace("/", "-").replace(":", "-")
        output_path = os.path.join(datasheet_dir, f"preprocessing_naive_{model_safe}.json")

    print(f"Provider: {args.provider}")
    print(f"Model: {model}")
    print(f"Datasheet: {args.datasheet}")
    print(f"Output: {output_path}")
    print(f"Approach: Naive (open-ended, no predefined questions)")
    print()

    # Read datasheet content
    print("Reading datasheet...")
    try:
        content = read_datasheet(args.datasheet, sample_pages=args.sample_pages)
        print(f"  Content length: {len(content):,} characters")
    except Exception as e:
        print(f"Error reading datasheet: {e}")
        return 1

    # Query the LLM
    print(f"\nQuerying {args.provider} ({model})...")
    try:
        if args.provider == "openai":
            result = query_openai(content, model, args.temperature)
        else:
            result = query_gemini(content, model, args.temperature)
    except Exception as e:
        print(f"Error querying LLM: {e}")
        return 1

    # Extract usage_stats before adding metadata (not JSON serializable)
    usage_stats = result.pop("usage_stats", None)

    # Add metadata
    result["datasheet"] = args.datasheet
    result["approach"] = "naive"
    result["prompt"] = NAIVE_PROMPT
    result["timestamp"] = datetime.utcnow().isoformat() + "Z"

    # Print usage info
    if result.get("usage"):
        usage = result["usage"]
        print(f"\nToken usage:")
        print(f"  Prompt: {usage.get('prompt_tokens', 'N/A'):,}")
        print(f"  Completion: {usage.get('completion_tokens', 'N/A'):,}")
        print(f"  Total: {usage.get('total_tokens', 'N/A'):,}")

    # Initialize ResultSaver for the output directory
    output_dir = os.path.dirname(output_path)
    result_saver = ResultSaver(output_dir)

    # Save results to JSON file
    output_filename = os.path.basename(output_path)
    result_saver.save_json(result, output_filename)
    print(f"\nResults saved to: {output_path}")

    # Save usage stats to CSV
    if usage_stats:
        usage_csv_path = result_saver.save_usage_stats(
            usage_stats,
            filename="preprocessing_naive_usage.csv",
            additional_fields={"datasheet": os.path.basename(args.datasheet)}
        )
        print(f"Usage saved to: {usage_csv_path}")

    # Print summary to terminal
    print("\n" + "=" * 70)
    print("ANALYSIS SUMMARY")
    print("=" * 70)

    answers = result.get("answers", {})

    sections = [
        ("formatting_metadata", "Formatting Metadata"),
        ("retrieval_optimization", "Retrieval Optimization"),
        ("extraction_hints", "Extraction Hints"),
        ("prompt_improvements", "Prompt Improvements")
    ]

    for key, title in sections:
        content = answers.get(key, "No content")
        print(f"\n{title}:")
        print("-" * 40)
        if isinstance(content, str):
            if len(content) > 500:
                print(content[:500] + "...")
            else:
                print(content)
        elif isinstance(content, dict):
            for k, v in list(content.items())[:3]:
                v_str = str(v)[:200] + "..." if len(str(v)) > 200 else str(v)
                print(f"  {k}: {v_str}")
            if len(content) > 3:
                print(f"  ... and {len(content) - 3} more items")
        elif isinstance(content, list):
            for item in content[:3]:
                item_str = str(item)[:200] + "..." if len(str(item)) > 200 else str(item)
                print(f"  - {item_str}")
            if len(content) > 3:
                print(f"  ... and {len(content) - 3} more items")

    if args.verbose:
        print("\n" + "=" * 70)
        print("RAW RESPONSE")
        print("=" * 70)
        print(result.get("raw_response", ""))

    return 0


if __name__ == "__main__":
    sys.exit(main())
