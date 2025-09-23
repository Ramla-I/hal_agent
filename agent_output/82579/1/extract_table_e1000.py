#!/usr/bin/env python3
"""
Script to find the line numbers where a register table starts and ends in a markdown file.
Usage: python find_register_table.py <register_name> [file_path]
"""

import sys
import re
import os

def find_register_table(register_name, file_path):
    """
    Find the line numbers where a register table starts and ends.
    
    Args:
        register_name (str): The name of the register to search for
        file_path (str): Path to the markdown file
    
    Returns:
        tuple: (start_line, end_line) or (None, None) if not found
    """
    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return None, None
    
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Match a header line (starting with #), followed by anything, then ' - REGISTER_NAME (' (case-insensitive)
    # This regex is used to match a markdown header line for a register section.
    # It looks for lines that start with '#' (indicating a markdown header), followed by any characters,
    # then ' - REGISTER_NAME (' (case-insensitive), where REGISTER_NAME is the register_name argument.
    # Example matched line: "# 12.0.3.6.1 CRC Error Count - CRCERRS (0x04000; RO)"
    register_pattern = re.compile(r'^#.* - ' + re.escape(register_name) + r' \(', re.IGNORECASE)
    
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines, 1):
        # Check if this line matches our register header
        if register_pattern.search(line):
            start_line = i
            # Look for the table start (next line with | characters)
            table_start = None
            for j in range(i, len(lines)):
                if '|' in lines[j] and lines[j].strip().startswith('|'):
                    table_start = j + 1
                    break
            
            if table_start:
                # Look for the table end (blank line or next section header)
                table_end = None
                for k in range(table_start, len(lines)):
                    current_line = lines[k].strip()
                    # Table ends at blank line or next section header
                    if not current_line or current_line.startswith('#'):
                        table_end = k
                        break
                
                if table_end:
                    end_line = table_end
                    break
    
    return start_line, end_line

def extract_table(register_name, file_path):
    """
    Extract the register table lines from a markdown file.
    
    Args:
        register_name (str): The name of the register to search for
        file_path (str): Path to the markdown file
    
    Returns:
        list: List of lines containing the register table, or None if not found
    """
    start_line, end_line = find_register_table(register_name, file_path)
    
    if start_line and end_line:
        with open(file_path, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()
            extracted_lines = lines[start_line-1:end_line]  # lines are 1-indexed
        return extracted_lines
    
    return None



def get_available_registers(file_path):
    """
    Get a list of available registers in the markdown file.
    
    Args:
        file_path (str): Path to the markdown file
    
    Returns:
        list: List of register names found in the file
    """
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        register_matches = re.findall(r'#.*Register\s*-\s*(\w+)\s*\(', content)
        return sorted(set(register_matches))




def main():
    if len(sys.argv) < 2:
        print("Usage: python find_register_table.py <register_name> [file_path]")
        print("Example: python find_register_table.py STATUS devices/82579/82579.md")
        sys.exit(1)
    
    register_name = sys.argv[1]
    
    # Default file path if not provided
    if len(sys.argv) >= 3:
        file_path = sys.argv[2]
    else:
        # Try to find a markdown file in the current directory or subdirectories
        file_path = None
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    break
            if file_path:
                break
        
        if not file_path:
            print("Error: No markdown file found. Please specify the file path.")
            sys.exit(1)
    
    start_line, end_line = find_register_table(register_name, file_path)
    
    if start_line and end_line:
        print(f"Register '{register_name}' table found:")
        print(f"  Start line: {start_line}")
        print(f"  End line: {end_line}")
        print(f"  Table spans {end_line - start_line + 1} lines")
    else:
        print(f"Register '{register_name}' not found in '{file_path}'")
        print("Available registers in the file:")
        
        # Show available registers
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            register_matches = re.findall(r'#.*Register\s*-\s*(\w+)\s*\(', content)
            if register_matches:
                for reg in sorted(set(register_matches)):
                    print(f"  - {reg}")
            else:
                print("  No registers found in the file.")
    
    # If the register table was found, extract those lines and save to a new file
    if start_line and end_line:
        with open(file_path, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()
            extracted_lines = lines[start_line-1:end_line]  # lines are 1-indexed
        
        return extracted_lines
    
    return None

        # output_filename = f"{register_name}.md"
        # with open(output_filename, 'w', encoding='utf-8') as outfile:
        #     outfile.writelines(extracted_lines)
        # print(f"Extracted table saved to '{output_filename}'")

if __name__ == "__main__":
    main() 