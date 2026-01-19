#!/usr/bin/env python3
"""
Script to count tokens in a file using tiktoken.

Usage:
    python count_tokens.py <file_path> [--encoding <encoding_name>]

Examples:
    python count_tokens.py output.txt
    python count_tokens.py output.txt --encoding cl100k_base
    python count_tokens.py output.txt --encoding p50k_base
"""

import argparse
import sys
import tiktoken


def count_tokens(file_path: str, encoding_name: str = "cl100k_base") -> int:
    """
    Count tokens in a file using tiktoken.
    
    Args:
        file_path: Path to the file to count tokens in
        encoding_name: Name of the tiktoken encoding to use (default: cl100k_base)
    
    Returns:
        Number of tokens in the file
    """
    try:
        # Get the encoding
        encoding = tiktoken.get_encoding(encoding_name)
    except KeyError:
        print(f"Error: Unknown encoding '{encoding_name}'", file=sys.stderr)
        print(f"Available encodings: cl100k_base, p50k_base, r50k_base, gpt2", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Count tokens
    tokens = encoding.encode(content)
    return len(tokens)


def main():
    parser = argparse.ArgumentParser(
        description="Count tokens in a file using tiktoken",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s output.txt
  %(prog)s output.txt --encoding cl100k_base
  %(prog)s output.txt --encoding p50k_base

Common encodings:
  - cl100k_base: Used by GPT-4, GPT-3.5-turbo (default)
  - p50k_base: Used by Codex models
  - r50k_base: Used by GPT-3 models
  - gpt2: GPT-2 encoding
        """
    )
    parser.add_argument(
        'file_path',
        help='Path to the file to count tokens in'
    )
    parser.add_argument(
        '--encoding',
        default='cl100k_base',
        help='Tiktoken encoding to use (default: cl100k_base)'
    )
    
    args = parser.parse_args()
    
    token_count = count_tokens(args.file_path, args.encoding)
    
    print(f"File: {args.file_path}")
    print(f"Encoding: {args.encoding}")
    print(f"Token count: {token_count:,}")


if __name__ == "__main__":
    main()

