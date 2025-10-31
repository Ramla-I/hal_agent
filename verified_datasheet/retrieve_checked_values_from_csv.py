import csv
import sys
import argparse
import os

# Usage: python retrieve_checked_values_from_csv.py --input input.csv --output output.csv --mode register|field

def process_csv(input_csv_path, output_csv_path, mode):
    out_rows = []
    existing_rows = []
    existing_keys = set()
    conflict_rows = []

    # Determine the field names
    if mode == 'register':
        fieldnames = ['peripheral', 'register', 'key', 'correct_value']
        match_fields = ['peripheral', 'register', 'key']
    else:
        fieldnames = ['peripheral', 'register', 'field_name', 'key', 'correct_value']
        match_fields = ['peripheral', 'register', 'field_name', 'key']

    # If output file exists, read existing rows to avoid exact duplicates
    if os.path.isfile(output_csv_path):
        with open(output_csv_path, newline='', encoding='utf-8') as outcsv:
            reader = csv.DictReader(outcsv)
            for row in reader:
                existing_rows.append(row)
                key_tuple = tuple(row.get(field, '') for field in match_fields)
                existing_keys.add(key_tuple)
    
    # Read and process the input file
    with open(input_csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            bug_filled = row.get('Bug', '').strip() != ''
            fp_filled = row.get('FP', '').strip() != ''
            if not (bug_filled or fp_filled):
                continue
            if mode == 'register':
                out_row = {
                    'peripheral': row.get('peripheral', ''),
                    'register': row.get('register', ''),
                    'key': row.get('key', '')
                }
            else:
                out_row = {
                    'peripheral': row.get('peripheral', ''),
                    'register': row.get('register', ''),
                    'field_name': row.get('field_name', ''),
                    'key': row.get('key', '')
                }
            # For FP, fetch just_svd as correct_value
            if fp_filled:
                out_row['correct_value'] = row.get('just_svd', '')
            # For Bug, select Actual Value if it exists, otherwise just_output
            elif bug_filled:
                actual_val = row.get('Actual Value', '').strip()
                if actual_val:
                    out_row['correct_value'] = actual_val
                else:
                    out_row['correct_value'] = row.get('just_output', '')
            # Now check against existing rows
            key_tuple = tuple(out_row.get(field, '') for field in match_fields)
            if key_tuple in existing_keys:
                # Find existing row in output file
                corresponding = [r for r in existing_rows if all(r.get(field, '') == out_row.get(field, '') for field in match_fields)]
                if corresponding:
                    existing_correct_value = corresponding[0].get('correct_value', '')
                    if out_row['correct_value'] != existing_correct_value:
                        print("Discrepancy detected for row:")
                        for f in match_fields:
                            print(f"{f}: {out_row.get(f, '')}")
                        print(f"1. Existing correct_value: {existing_correct_value}")
                        print(f"2. New correct_value: {out_row['correct_value']}")
                        choice = input("Which correct_value would you like to keep? (1/2): ").strip()
                        while choice not in ('1', '2'):
                            choice = input("Please enter 1 or 2: ").strip()
                        if choice == '2':
                            corresponding[0]['correct_value'] = out_row['correct_value']
                continue  # Don't append duplicate or resolved row
            else:
                out_rows.append(out_row)
                existing_keys.add(key_tuple)
                existing_rows.append(dict(out_row))  # Add to existing_rows for further deduplication if multiple input rows duplicate

    # Alphabetically order existing_rows by peripheral, register, then (if exists) field_name, then key
    def sort_key(row):
        # Use empty string if field_name doesn't exist (mode == 'register')
        return (
            row.get('peripheral', ''),
            row.get('register', ''),
            row.get('field_name', ''),
            row.get('key', '')
        )
    existing_rows.sort(key=sort_key)
    # Write output
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        # Write preexisting (and possibly updated) rows
        for row in existing_rows:
            print(row)
            writer.writerow(row)
        # Write only new rows
        # for row in out_rows:
        #     writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(description='Filter and transform CSV according to bug/fp status.')
    parser.add_argument('input', help='Input CSV file path')
    parser.add_argument('output', help='Output CSV file path')
    parser.add_argument('--mode', '-m', required=True, choices=['register', 'field'], help='Operation mode: register or field')
    args = parser.parse_args()
    process_csv(args.input, args.output, args.mode)

if __name__ == '__main__':
    main()
