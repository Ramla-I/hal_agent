#!/usr/bin/env python3
import re
import sys
import argparse
from pathlib import Path
import agent_tools.md_ops as md_ops

MANUFACTURER = 'Intel'
HEADER_PATTERN_INTEL = rf'^#\s*\d+(?:\.\d+)*\s+.*' # Works for Intel
HEADER_PATTERN_STM = rf'^#\s*(.+)\s*\(' # Doesn't really work due to difficulty detecting end of a section 

def header_pattern(section_name) -> re.Pattern:
    if MANUFACTURER == 'Intel':
        return re.compile(re.compile(HEADER_PATTERN_INTEL + re.escape(section_name)))
    elif MANUFACTURER == 'STM':
        return re.compile(re.compile(HEADER_PATTERN_STM + re.escape(section_name) + r'\)'))


def generic_header_pattern() -> re.Pattern:
    if MANUFACTURER == 'Intel':
        return  re.compile(HEADER_PATTERN_INTEL)
    elif MANUFACTURER == 'STM':
        return re.compile(HEADER_PATTERN_STM)


def find_section(content, section_name, section_header_regex=None):
    """
    Find the section boundaries for a given peripheral.

    Args:
        content (str): The full markdown content
        section_name (str): Name of the section to find (e.g., 'TIM12', 'GPIO', 'ADC')
        section_header_regex (str, optional): Regex pattern for section headers. If None, uses default patterns.

    Returns:
        tuple: (start_line, end_line) or (None, None) if not found
    """
    lines = content.split('\n')

    # Use provided section header regex or default patterns
    if section_header_regex is not None:
        pattern = re.compile(section_header_regex.format(section_name=re.escape(section_name)))#, re.IGNORECASE)
    else:
        # Default patterns for STM32-style markdown
        pattern = header_pattern(section_name)

    start_line = None
    end_line = None
    # print(pattern)

    # Find the start of the peripheral section
    for i, line in enumerate(lines):
        if pattern.search(line):
            start_line = i
            break

    if start_line is None:
        return None, None

    # Check if line starts with # followed by a number
    start_line_pattern = re.match(r'^#\s*(\d+(?:\.\d+)*)', lines[start_line])

    if start_line_pattern:
        # Get the number pattern (e.g. "10.3.6")
        section_depth = start_line_pattern.group(1)
        section_parts = section_depth.split('.')
        # Get all but last number to make prefix (e.g. "10.3")
        section_prefix = '.'.join(section_parts[:-1])
        # Get next number at same level (e.g. "10.3.7")
        next_num = int(section_parts[-1]) + 1
        # Match same prefix with next number
        section_end_pattern = re.compile(r'^#\s*' + re.escape(section_prefix) + r'\.' + str(next_num))
    else:
        # If no number pattern, match any header that doesn't contain section name and has no number.number pattern
        section_end_pattern = generic_header_pattern()

    for i in range(start_line + 1, len(lines)):
        line = lines[i].strip()
        if line.startswith('# ') and section_end_pattern.search(line) and section_name not in line:
            end_line = i
            break
    # If we didn't find an end, go to the end of the file
    if end_line is None:
        end_line = len(lines)

    return start_line, end_line


def extract_section_regex(file_path, section_name, tables_only=False, section_regex=None, manufacturer="Intel"):
    """
    Extract a section from the markdown file.

    Args:
        file_path (str): Path to the markdown file
        section_name (str): Name of the section to extract
        tables_only (bool): If True, only extract tables from the section
        section_regex (str, optional): Custom regex pattern to identify the section header. If None, use default.
        manufacturer (str, optional): Manufacturer name to determine header parsing rules. Default is "Intel".

    Returns:
        str: The extracted content
    """
    global MANUFACTURER
    old_manufacturer = MANUFACTURER
    MANUFACTURER = manufacturer
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return f"Error: File {file_path} not found."
    except Exception as e:
        return f"Error reading file: {e}"
    
    # Find the peripheral section
    start_line, end_line = find_section(content, section_name, section_regex)
    
    if start_line is None:
        return f"Error: Section '{section_name}' not found in the document."
    
    if tables_only:
        lines = content.split('\n')
        section_lines = lines[start_line:end_line]
        section_content = '\n'.join(section_lines)
        # Extract only tables from the section
        tables = md_ops.extract_tables_from_section(section_content)
        if not tables:
            return f"No tables found for section '{section_name}'."
        
        result = f"# Tables for {section_name}\n\n"
        for i, table in enumerate(tables, 1):
            result += f"## Table {i}\n\n{table}\n\n"
        
        return result
    else:
        # Extract the entire section
        lines = content.split('\n')
        section_lines = lines[start_line:end_line]
        return '\n'.join(section_lines)


def main():
    parser = argparse.ArgumentParser(description='Extract peripheral section from markdown file')
    parser.add_argument('file', help='Path to markdown file')
    parser.add_argument('section', help='Name of section to extract (e.g. TIM12, GPIO)')
    parser.add_argument('--tables-only', action='store_true', help='Extract only tables from the section')
    parser.add_argument('--regex', help='Custom regex pattern to match section headers')
    parser.add_argument('--manufacturer', default="Intel", help='Manufacturer name to determine header parsing rules (default: Intel)')
    
    args = parser.parse_args()

    result = extract_section_regex(args.file, args.section, args.tables_only, args.regex, args.manufacturer)
    print(result)


if __name__ == '__main__':
    main() 