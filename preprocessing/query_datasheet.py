#!/usr/bin/env python3
"""
Extract structural metadata from a datasheet for preprocessing.

This script queries an LLM to identify formatting conventions and patterns in a datasheet,
which are used to improve automated register extraction. The extracted metadata includes:

- Register naming conventions (e.g., compact notation like "ABCx(x=1..3)")
- Subfield naming conventions (e.g., whether bit ranges are included like "PIN[3:0]")
- Format of essential information (tables vs text vs figures)
- Removable front/back matter (TOC, index pages that can be excluded)

Supports both OpenAI and Google Gemini models with large context windows.

Usage:
    # Using OpenAI (default)
    python preprocessing/query_datasheet.py devices/stm/rm0041/rm0041.pdf

    # Using Gemini (larger context window)
    python preprocessing/query_datasheet.py devices/stm/rm0041/rm0041.pdf --provider gemini

    # Save output to file
    python preprocessing/query_datasheet.py devices/stm/rm0041/rm0041.pdf -o output.json

    # List the default preprocessing questions
    python preprocessing/query_datasheet.py --list-questions

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

# Default questions to ask about the datasheet
DEFAULT_QUESTIONS = [
    # Register naming conventions
    """What are the register naming conventions used in this datasheet?
Identify patterns such as:
- How peripheral and register names are separated (e.g., underscores, no separator)
- Whether compact notation is used for multiple registers (e.g., "ABCx(x=1..3)" or "REG0-REG3")
- Any prefixes or suffixes commonly used
Provide specific examples from the datasheet.""",

    # Subfield naming conventions
    """What are the subfield/bitfield naming conventions used in this datasheet?
Identify patterns such as:
- Whether bit ranges are included in field names (e.g., "PIN[3:0]" vs "PIN")
- How reserved or unused bits are labeled
- Any numbering conventions for repeated fields
Provide specific examples from the datasheet.""",

    # Format of essential information
    """How is essential register information formatted in this datasheet?
Determine whether critical register details (addresses, reset values, bit definitions, access types) appear primarily in:
- Tables (structured tabular format)
- Text (prose descriptions)
- Figures (diagrams or visual representations)
- A combination of these
Describe the typical layout for register documentation in this datasheet.""",

    # Removable front matter
    """How many pages at the BEGINNING of this datasheet can be safely removed without losing register content?
Look for non-essential front matter such as:
- Table of contents
- Revision history
- General product overview pages
- Feature lists without register details
- Ordering information
Provide the page number where actual peripheral/register documentation begins.""",

    # Removable back matter
    """How many pages at the END of this datasheet can be safely removed without losing register content?
Look for non-essential back matter such as:
- Index pages
- Appendices without register information
- Package information
- Ordering codes
- Revision history at the end
Provide the last page number that contains actual peripheral/register documentation.""",

    # Other useful information
    """What other information in this datasheet would be useful for automated register extraction?
Consider aspects such as:
- How register reset values are formatted (hex, binary, or described in text)
- How access types are specified (e.g., "R/W", "read-only", "RO")
- Whether registers have dependencies or cross-references to other registers
- Any unusual formatting or organization patterns
- Peripheral base addresses and how they relate to register offsets
- Any errata or notes sections that clarify register behavior
Identify any patterns or conventions not covered by the previous questions.""",
]


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
    questions: list[str],
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

    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    system_prompt = """You are an expert at analyzing hardware datasheets and reference manuals for preprocessing purposes.
Your task is to extract structural metadata about how the datasheet is formatted, which will be used to improve automated register extraction.

You will be given the content of a datasheet and a list of questions to answer.
Focus on identifying patterns and conventions used throughout the document.
Provide specific examples from the datasheet to support your answers.
If information is not available or a pattern is not used, say so explicitly.
Format your response as a JSON object with question numbers as keys."""

    user_prompt = f"""Here is the datasheet content:

{content}

---

Please answer the following questions about this datasheet:

{questions_text}

Respond with a JSON object where keys are "q1", "q2", etc. and values are your answers."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
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
    questions: list[str],
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

    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    prompt = f"""You are an expert at analyzing hardware datasheets and reference manuals for preprocessing purposes.
Your task is to extract structural metadata about how the datasheet is formatted, which will be used to improve automated register extraction.

Here is the datasheet content:

{content}

---

Please answer the following questions about this datasheet:

{questions_text}

Focus on identifying patterns and conventions used throughout the document.
Provide specific examples from the datasheet to support your answers.
If information is not available or a pattern is not used, say so explicitly.
Respond with a JSON object where keys are "q1", "q2", etc. and values are your answers.
Only output the JSON object, no other text."""

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
        description="Extract structural metadata from a datasheet for preprocessing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script extracts metadata about datasheet formatting conventions:
  - Register naming conventions (e.g., "ABCx(x=1..3)")
  - Subfield naming conventions (e.g., "PIN[3:0]")
  - Format of essential information (tables/text/figures)
  - Removable front/back matter (TOC, index pages)

Examples:
    # Using OpenAI (default) - saves to devices/stm/rm0041/preprocessing_metadata_gpt-4.1.json
    python %(prog)s devices/stm/rm0041/rm0041.pdf

    # Using Gemini - saves to devices/stm/rm0041/preprocessing_metadata_gemini-2.5-flash.json
    python %(prog)s devices/stm/rm0041/rm0041.pdf --provider gemini

    # Save output to custom location
    python %(prog)s devices/stm/rm0041/rm0041.pdf -o custom_output.json

    # List default preprocessing questions
    python %(prog)s --list-questions

Supported models:
    OpenAI: gpt-4.1 (default), gpt-4.1, gpt-4.1-mini
    Gemini: gemini-2.5-flash (default, 1M context), gemini-3-pro (1M context)
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
        "-q", "--questions",
        nargs="+",
        default=None,
        help="Custom questions to ask (default: predefined preprocessing questions about naming conventions, formatting, etc.)"
    )

    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output file path for JSON results (default: preprocessing_metadata_{model}.json alongside datasheet)"
    )

    parser.add_argument(
        "-t", "--temperature",
        type=float,
        default=0.0,
        help="Temperature for generation (default: 0.0)"
    )

    parser.add_argument(
        "--list-questions",
        action="store_true",
        help="List the default questions and exit"
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

    return parser.parse_args()


def main():
    args = parse_args()

    # Handle --list-questions
    if args.list_questions:
        print("Default questions:")
        for i, q in enumerate(DEFAULT_QUESTIONS, 1):
            print(f"  {i}. {q}")
        return 0

    # Validate datasheet is provided
    if not args.datasheet:
        print("Error: datasheet argument is required")
        print("Usage: python query_datasheet.py <datasheet> [options]")
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

    # Determine questions
    questions = args.questions if args.questions else DEFAULT_QUESTIONS

    # Determine output path (default: alongside datasheet as preprocessing_metadata_{model}.json)
    if args.output:
        output_path = args.output
    else:
        datasheet_dir = os.path.dirname(os.path.abspath(args.datasheet))
        # Sanitize model name for filename (replace slashes, etc.)
        model_safe = model.replace("/", "-").replace(":", "-")
        output_path = os.path.join(datasheet_dir, f"preprocessing_metadata_{model_safe}.json")

    print(f"Provider: {args.provider}")
    print(f"Model: {model}")
    print(f"Datasheet: {args.datasheet}")
    print(f"Output: {output_path}")
    print(f"Questions: {len(questions)}")
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
            result = query_openai(content, questions, model, args.temperature)
        else:
            result = query_gemini(content, questions, model, args.temperature)
    except Exception as e:
        print(f"Error querying LLM: {e}")
        return 1

    # Extract usage_stats before adding metadata (not JSON serializable)
    usage_stats = result.pop("usage_stats", None)

    # Add metadata
    result["datasheet"] = args.datasheet
    result["questions"] = questions
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
            filename="preprocessing_usage.csv",
            additional_fields={"datasheet": os.path.basename(args.datasheet)}
        )
        print(f"Usage saved to: {usage_csv_path}")

    # Also print summary to terminal
    print("\n" + "=" * 70)
    print("ANSWERS SUMMARY")
    print("=" * 70)

    answers = result.get("answers", {})
    for i, q in enumerate(questions, 1):
        key = f"q{i}"
        answer = answers.get(key, answers.get(str(i), "No answer"))
        # Print first line of question and truncated answer
        q_short = q.split('\n')[0][:60] + "..." if len(q.split('\n')[0]) > 60 else q.split('\n')[0]
        print(f"\nQ{i}: {q_short}")
        print("-" * 40)
        if isinstance(answer, str):
            # Truncate long answers for terminal display
            if len(answer) > 300:
                print(answer[:300] + "...")
            else:
                print(answer)
        else:
            print(json.dumps(answer, indent=2)[:300] + "..." if len(json.dumps(answer, indent=2)) > 300 else json.dumps(answer, indent=2))

    if args.verbose:
        print("\n" + "=" * 70)
        print("RAW RESPONSE")
        print("=" * 70)
        print(result.get("raw_response", ""))

    return 0


if __name__ == "__main__":
    sys.exit(main())
