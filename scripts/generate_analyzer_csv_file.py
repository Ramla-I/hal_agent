import csv
import json
import argparse

def filter_csv_by_ids(ids_json_path, input_csv_path):
    """
    Filters rows from input_csv_path with the list of ids in ids_json_path and writes them to csv file in the same directory as the input_csv_path.
    
    Args:
        ids_json_path (str): Path to JSON file listing row ids.
        input_csv_path (str): CSV file to filter.
    """

    output_csv_path = input_csv_path.replace('.csv', '_analyzer.csv')

    # Read the set of IDs from ids_csv_path (assumed as first column, skipping header if present)
    with open(ids_json_path, 'r') as f:
        ids = json.load(f)['bugs']

    # Now filter rows from input_csv_path to output_csv_path
    with open(input_csv_path, 'r') as inf, open(output_csv_path, 'w') as outf:
        reader = csv.reader(inf)
        writer = csv.writer(outf)
        input_header = next(reader)
        writer.writerow(input_header)
        for row in reader:
            if row and (int(row[0]) in ids or row[3] == 'fields'):
                writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(description="Generate analyzer CSV file from JSON file.")
    parser.add_argument('ids_json_path', help='Path to JSON file listing row ids.')
    parser.add_argument('input_csv_path', help='Path to CSV file to filter.')
    args = parser.parse_args()

    filter_csv_by_ids(args.ids_json_path, args.input_csv_path)

if __name__ == "__main__":
    main()