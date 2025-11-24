#!/usr/bin/env python3
"""
Script to create bug reports from CSV files.
Takes multiple CSV files as input, filters rows where Bug=1, and creates a new CSV
with bug descriptions.
"""
import argparse
import csv
import os
import sys
from typing import List, Dict, Optional, Set, Tuple


def normalize_header(name: str) -> str:
    """Normalize header name for case-insensitive matching."""
    return ''.join(ch.lower() for ch in name if ch.isalnum())


def find_column(headers: List[str], candidates: List[str]) -> Optional[str]:
    """Find a column by name (case-insensitive)."""
    normalized_to_original: Dict[str, str] = {normalize_header(h): h for h in headers}
    for cand in candidates:
        norm = normalize_header(cand)
        if norm in normalized_to_original:
            return normalized_to_original[norm]
    return None


def read_csv_files(csv_files: List[str]) -> List[Dict[str, str]]:
    """Read all CSV files and collect rows where Bug=1."""
    bug_rows = []
    
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                if not headers:
                    print(f"Warning: {csv_file} has no headers, skipping", file=sys.stderr)
                    continue
                
                # Find required columns
                bug_col = find_column(headers, ['bug'])
                peripheral_col = find_column(headers, ['peripheral'])
                register_col = find_column(headers, ['register'])
                key_col = find_column(headers, ['key'])
                just_svd_col = find_column(headers, ['just_svd'])
                just_output_col = find_column(headers, ['just_output'])
                actual_value_col = find_column(headers, ['actual value', 'actual_value'])
                field_name_col = find_column(headers, ['field_name', 'field name'])
                
                missing = []
                if bug_col is None:
                    missing.append('Bug')
                if peripheral_col is None:
                    missing.append('peripheral')
                if register_col is None:
                    missing.append('register')
                if key_col is None:
                    missing.append('key')
                if just_svd_col is None:
                    missing.append('just_svd')
                if just_output_col is None:
                    missing.append('just_output')
                
                if missing:
                    print(f"Warning: {csv_file} missing columns: {', '.join(missing)}, skipping", file=sys.stderr)
                    continue
                
                # Read rows and filter for Bug=1
                for row in reader:
                    bug_value = (row.get(bug_col) or '').strip()
                    if bug_value == '1':
                        bug_row = {
                            'peripheral': (row.get(peripheral_col) or '').strip(),
                            'register': (row.get(register_col) or '').strip(),
                            'key': (row.get(key_col) or '').strip(),
                            'just_svd': (row.get(just_svd_col) or '').strip(),
                            'just_output': (row.get(just_output_col) or '').strip(),
                            'actual_value': (row.get(actual_value_col) or '').strip() if actual_value_col else ''
                        }
                        # Add field_name if it exists
                        if field_name_col:
                            field_name = (row.get(field_name_col) or '').strip()
                            if field_name:
                                bug_row['field_name'] = field_name
                        bug_rows.append(bug_row)
        except FileNotFoundError:
            print(f"Error: File not found: {csv_file}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Error reading {csv_file}: {e}", file=sys.stderr)
            continue
    
    return bug_rows


def format_bug_description(row: Dict[str, str]) -> str:
    """Format bug description in the specified format."""
    peripheral = row['peripheral']
    register = row['register']
    key = row['key']
    just_svd = row['just_svd']
    just_output = row['just_output']
    actual_value = row['actual_value']
    
    # Check if field_name exists
    field_name = row.get('field_name', '').strip()
    
    # Format: peripheral_register_field: key: svd = just_svd, agent = just_output, RM = actual_value
    # or: peripheral_register: key: svd = just_svd, agent = just_output, RM = actual_value (if no field_name)
    if field_name:
        prefix = f"{peripheral}_{register}_{field_name}"
    else:
        prefix = f"{peripheral}_{register}"
    
    description = f"{prefix}: {key}: svd = {just_svd}, agent = {just_output}, RM = {actual_value}"
    return description


def extract_comparison_key(bug_description: str) -> str:
    """Extract the peripheral_register(_field): key: portion from bug description for comparison."""
    # Format is: peripheral_register(_field): key: svd = ..., agent = ..., RM = ...
    # We want everything up to and including the second colon
    parts = bug_description.split(':')
    if len(parts) >= 2:
        # Return peripheral_register(_field): key:
        return ':'.join(parts[:2]) + ':'
    return bug_description


def read_existing_output(output_file: str) -> Tuple[List[Dict[str, str]], Set[Tuple[str, str, str]]]:
    """Read existing output file and return rows and set of existing entries."""
    existing_rows = []
    existing_entries: Set[Tuple[str, str, str]] = set()
    
    if not os.path.exists(output_file):
        return existing_rows, existing_entries
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            if not headers:
                return existing_rows, existing_entries
            
            svd_col = find_column(headers, ['svd file'])
            rm_col = find_column(headers, ['rm'])
            bug_desc_col = find_column(headers, ['bug description'])
            crate_col = find_column(headers, ['crate'])
            pr_col = find_column(headers, ['pr'])
            status_col = find_column(headers, ['status'])
            
            if svd_col and rm_col and bug_desc_col:
                for row in reader:
                    svd = (row.get(svd_col) or '').strip()
                    rm = (row.get(rm_col) or '').strip()
                    bug_desc = (row.get(bug_desc_col) or '').strip()
                    
                    # Extract comparison key (peripheral_register: key:)
                    comparison_key = extract_comparison_key(bug_desc)
                    
                    # Normalize the entry key for comparison using only peripheral_register: key:
                    entry_key = (svd, rm, comparison_key)
                    
                    # Only add to existing_rows if it's not already in the set
                    if entry_key not in existing_entries:
                        existing_entries.add(entry_key)
                        # Store row with normalized column names for writing
                        normalized_row = {
                            'SVD File': svd,
                            'Crate': (row.get(crate_col) or '').strip() if crate_col else '',
                            'RM': rm,
                            'Bug Description': bug_desc,
                            'PR': (row.get(pr_col) or '').strip() if pr_col else '',
                            'Status': (row.get(status_col) or '').strip() if status_col else ''
                        }
                        existing_rows.append(normalized_row)
    except Exception as e:
        print(f"Warning: Could not read existing output file {output_file}: {e}", file=sys.stderr)
    
    return existing_rows, existing_entries


def main():
    parser = argparse.ArgumentParser(
        description="Create bug report CSV from multiple input CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--svd-file', required=True, help='SVD File name')
    parser.add_argument('--rm', required=True, help='RM (Reference Manual) name')
    parser.add_argument('--crate', default='stm32-rs', help='Crate name (optional)')
    parser.add_argument('csv_files', nargs='+', help='Input CSV files to process')
    parser.add_argument('--output', '-o', default='bug_report.csv', help='Output CSV file (default: bug_report.csv)')
    
    args = parser.parse_args()
    
    # Read all CSV files and collect bug rows
    bug_rows = read_csv_files(args.csv_files)
    
    if not bug_rows:
        print("No rows with Bug=1 found in any input files.", file=sys.stderr)
        return 1
    
    # Read existing output file if it exists
    existing_rows, existing_entries = read_existing_output(args.output)
    
    # Create output CSV
    output_headers = ['SVD File', 'Crate', 'RM', 'Bug Description', 'PR', 'Status']
    
    try:
        new_rows_count = 0
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=output_headers)
            writer.writeheader()
            
            # Write existing rows first
            for row in existing_rows:
                writer.writerow(row)
            
            # Add new rows that don't already exist
            for row in bug_rows:
                bug_description = format_bug_description(row)
                # Extract comparison key (peripheral_register: key:)
                comparison_key = extract_comparison_key(bug_description)
                entry_key = (args.svd_file, args.rm, comparison_key)
                
                if entry_key not in existing_entries:
                    output_row = {
                        'SVD File': args.svd_file,
                        'Crate': args.crate,
                        'RM': args.rm,
                        'Bug Description': bug_description,
                        'PR': '',  # Empty by default
                        'Status': ''  # Empty by default
                    }
                    writer.writerow(output_row)
                    # Add to existing_entries to prevent duplicates within the same run
                    existing_entries.add(entry_key)
                    new_rows_count += 1
        
        if new_rows_count > 0:
            print(f"Added {new_rows_count} new entries to bug report: {args.output}")
        else:
            print(f"No new entries to add (all {len(bug_rows)} entries already exist): {args.output}")
        return 0
    
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

