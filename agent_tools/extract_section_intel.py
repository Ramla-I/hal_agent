#!/usr/bin/env python3
import re
import sys
import argparse
from pathlib import Path

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


def extract_tables_from_section(section_content):
    """
    Extract all tables from a given section.
    
    Args:
        content (str): The full markdown content
        start_line (int): Start line of the section
        end_line (int): End line of the section
    
    Returns:
        list: List of table strings
    """

    
    # Find all tables in the section
    # Tables start with a line containing | and end with a blank line or another header
    tables = []
    
    # Split by lines that start with # (headers) to separate content blocks
    blocks = re.split(r'^# ', section_content, flags=re.MULTILINE)
    
    for block in blocks:
        if not block.strip():
            continue
            
        # Look for table patterns in each block
        lines_in_block = block.split('\n')
        current_table = []
        in_table = False
        
        for line in lines_in_block:
            if '|' in line and line.strip():
                # This looks like a table line
                if not in_table:
                    in_table = True
                current_table.append(line)
            elif in_table:
                # End of table
                if current_table:
                    table_text = '\n'.join(current_table)
                    if table_text.strip():
                        tables.append(table_text)
                current_table = []
                in_table = False
        
        # Don't forget the last table if we're still in one
        if in_table and current_table:
            table_text = '\n'.join(current_table)
            if table_text.strip():
                tables.append(table_text)
    
    return tables


def extract_section_regex(file_path, section_name, tables_only=False, section_regex=None):
    """
    Extract a section from the markdown file.

    Args:
        file_path (str): Path to the markdown file
        peripheral_name (str): Name of the peripheral to extract
        tables_only (bool): If True, only extract tables from the section
        section_regex (str, optional): Custom regex pattern to identify the section header. If None, use default.

    Returns:
        str: The extracted content
    """
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
        tables = extract_tables_from_section(section_content)
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


# def list_available_sections(file_path, section_regex):
#     """
#     List all available peripherals in the document.
    
#     Args:
#         file_path (str): Path to the markdown file
    
#     Returns:
#         str: List of available peripherals
#     """
#     try:
#         with open(file_path, 'r', encoding='utf-8') as f:
#             content = f.read()
#     except FileNotFoundError:
#         return f"Error: File {file_path} not found."
#     except Exception as e:
#         return f"Error reading file: {e}"
    
#     lines = content.split('\n')
#     peripherals = set()
    
#     # Pattern to match section headers that likely contain peripheral names
#     pattern = re.compile(r'^# \d+\.\d+.*?(TIM\d+|GPIO|ADC|DAC|SPI|I2C|USART|DMA|CRC|RTC|IWDG|WWDG|FSMC|EXTI|NVIC|RCC|PWR|BKP)', re.IGNORECASE)
    
#     for line in lines:
#         match = pattern.search(line)
#         if match:
#             peripheral = match.group(1)
#             peripherals.add(peripheral.upper())
    
#     if not peripherals:
#         return "No peripherals found in the document."
    
#     result = "Available peripherals:\n"
#     for peripheral in sorted(peripherals):
#         result += f"  - {peripheral}\n"
    
#     return result


def main():
    parser = argparse.ArgumentParser(description='Extract peripheral section from markdown file')
    parser.add_argument('file', help='Path to markdown file')
    parser.add_argument('section', help='Name of section to extract (e.g. TIM12, GPIO)')
    parser.add_argument('--tables-only', action='store_true', help='Extract only tables from the section')
    parser.add_argument('--regex', help='Custom regex pattern to match section headers')
    args = parser.parse_args()
   
    
    result = extract_section_regex(args.file, args.section, args.tables_only, args.regex)
    print(result)


if __name__ == '__main__':
    main() 