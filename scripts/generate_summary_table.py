#!/usr/bin/env python3
import argparse

"""
Script to generate a summary table from 4 CSV files:
- peripheral_summary.csv
- register_summary.csv  
- register_diff.csv
- field_diff.csv

The script creates a table with the following columns:
- Diff_version
- num_peripherals (from peripheral_summary)
- registers_not_found (just_svd from register_summary)
- num_registers (both from register_summary)
- address_offset (count of rows with key 'address_offset' in register_diff)
- reset_value (count of rows with key 'reset_value' in register_diff)
- size (count of rows with key 'size' in register_diff)
- fields in svd (just_svd from field_diff)
- fields in agent_output (just_output from field_diff)
- fields in both (both from field_diff)
- bit_offset (count of rows with key 'bit_offset' in field_diff)
- bit_width (count of rows with key 'bit_width' in field_diff)
- enums in svd (just_svd from field_diff where key='enum_names')
- enums in agent_output (just_output from field_diff where key='enum_names')
- enums in both (both from field_diff where key='enum_names')
"""

import pandas as pd
import sys
import os
from pathlib import Path

def process_csv_files(peripheral_summary_path, register_summary_path, register_diff_path, field_diff_path, analyzer):
    """
    Process the 4 CSV files and generate a summary table.
    """
    
    # Read the CSV files
    try:
        peripheral_summary = pd.read_csv(peripheral_summary_path)
        register_summary = pd.read_csv(register_summary_path)
        register_diff = pd.read_csv(register_diff_path)
        field_diff = pd.read_csv(field_diff_path)
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        return None
    
   
    # Extract data from peripheral_summary.csv
    # num_peripherals = both in peripheral_summary
    num_peripherals = peripheral_summary['both'].sum() if 'both' in peripheral_summary.columns else 0
    
    # Extract data from register_summary.csv
    # registers_not_found = just_svd in register_summary
    registers_not_found = register_summary['just_svd'].sum() if 'just_svd' in register_summary.columns else 0
    
    # num_registers = both in register_summary
    num_registers = register_summary['both'].sum() if 'both' in register_summary.columns else 0
    
    # Count specific keys in register_diff.csv
    address_offset_count = len(register_diff[register_diff['key'] == 'address_offset']) if 'key' in register_diff.columns else 0
    reset_value_count = len(register_diff[register_diff['key'] == 'reset_value']) if 'key' in register_diff.columns else 0
    size_count = len(register_diff[register_diff['key'] == 'size']) if 'key' in register_diff.columns else 0

    # Count field statistics from register_diff.csv
    fields_rows = register_diff[register_diff['key'] == 'fields'] if 'key' in register_diff.columns else pd.DataFrame()
    fields_rows = fields_rows.apply(pd.to_numeric, errors='coerce').astype(int, errors='ignore')
    fields_in_svd = fields_rows['just_svd'].sum() if 'just_svd' in fields_rows.columns else 0
    fields_in_agent_output = fields_rows['just_output'].sum() if 'just_output' in fields_rows.columns else 0
    fields_in_both = fields_rows['both'].sum() if 'both' in fields_rows.columns else 0
    
    # Count bit_offset and bit_width from field_diff.csv
    bit_offset_count = len(field_diff[field_diff['key'] == 'bit_offset']) if 'key' in field_diff.columns else 0
    bit_width_count = len(field_diff[field_diff['key'] == 'bit_width']) if 'key' in field_diff.columns else 0
    
    # Count enum statistics from field_diff.csv (where key='enum_names')
    enum_rows = field_diff[field_diff['key'] == 'enum_names'] if 'key' in field_diff.columns else pd.DataFrame()
    enums_in_svd = enum_rows['just_svd'].sum() if not enum_rows.empty and 'just_svd' in enum_rows.columns else 0
    enums_in_agent_output = enum_rows['just_output'].sum() if not enum_rows.empty and 'just_output' in enum_rows.columns else 0
    enums_in_both = enum_rows['both'].sum() if not enum_rows.empty and 'both' in enum_rows.columns else 0
    
    

    # Create the summary table
    summary_data = {
        'Diff_version': ['original' if not analyzer else 'analyzer'],
        'num_peripherals': [num_peripherals],
        'registers_not_found': [registers_not_found],
        'num_registers': [num_registers],
        'address_offset': [address_offset_count],
        'reset_value': [reset_value_count],
        'size': [size_count],
        'fields_in_svd': [fields_in_svd],
        'fields_in_agent_output': [fields_in_agent_output],
        'fields_in_both': [fields_in_both],
        'bit_offset': [bit_offset_count],
        'bit_width': [bit_width_count],
        'enums_in_svd': [enums_in_svd],
        'enums_in_agent_output': [enums_in_agent_output],
        'enums_in_both': [enums_in_both]
    }

    summary_df = pd.DataFrame(summary_data)
    return summary_df

def main():
    """
    Main function to process command line arguments and generate the summary table.
    """
    parser = argparse.ArgumentParser(
        description="Generate a summary table from comparison CSV files."
    )
    parser.add_argument(
        "input_directory",
        help="Input directory containing the CSV files.",
    )
    parser.add_argument(
        "--analyzer",
        action="store_true",
        default=False,
        help="If set, summary is for the register_diff_analyzer.csv files instead of default."
    )

    args = parser.parse_args()

    input_directory = args.input_directory
    analyzer = args.analyzer
    
    peripheral_summary_path = os.path.join(input_directory, "peripheral_summary.csv")
    register_summary_path = os.path.join(input_directory, "register_summary.csv")
    if analyzer:
        register_diff_path = os.path.join(input_directory, "register_diff_analyzer.csv")
    else:
        register_diff_path = os.path.join(input_directory, "register_diff.csv")
    field_diff_path = os.path.join(input_directory, "field_diff.csv")
    
    # Check if files exist
    for file_path in [peripheral_summary_path, register_summary_path, register_diff_path, field_diff_path]:
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} does not exist")
            sys.exit(1)
    
    # Process the CSV files
    summary_df = process_csv_files(peripheral_summary_path, register_summary_path, register_diff_path, field_diff_path, analyzer)

    if summary_df is not None and not summary_df.empty:
        # Save the summary table to a CSV file
        if analyzer:
            output_file = os.path.join(input_directory, "diff_table_analyzer.csv")
        else:
            output_file = os.path.join(input_directory, "diff_table.csv")
        with open(output_file, "w", encoding="utf-8") as f:
            summary_df.to_csv(f, index=False)
            print(f"Diff table saved to: {output_file}")
    else:
        print("Error: Could not generate summary table")
        sys.exit(1)

if __name__ == "__main__":
    main()
