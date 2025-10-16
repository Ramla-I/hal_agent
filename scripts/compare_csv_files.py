import csv
import sys

def compare_csv_files(file1_path, file2_path, output_path):
    with open(file1_path, newline='', encoding='utf-8') as f1, \
         open(file2_path, newline='', encoding='utf-8') as f2:

        reader1 = list(csv.reader(f1))
        reader2 = list(csv.reader(f2))

        if not reader1 or not reader2:
            print("One of the files is empty!", file=sys.stderr)
            return

        header1 = reader1[0]
        header2 = reader2[0]
        if header1 != header2:
            print("CSV files must have the same columns/headers!", file=sys.stderr)
            return

        rows1 = set(tuple(row) for row in reader1[1:])
        rows2 = set(tuple(row) for row in reader2[1:])

        only_in_1 = rows1 - rows2
        only_in_2 = rows2 - rows1

        output_header = header1 + ['SourceFile']

        with open(output_path, 'w', newline='', encoding='utf-8') as out_f:
            writer = csv.writer(out_f)
            writer.writerow(output_header)

            for row in only_in_1:
                writer.writerow(list(row) + [file1_path])

            for row in only_in_2:
                writer.writerow(list(row) + [file2_path])


import os

def main():
    """
    Compare all CSV files with matching names in two folders.
    Output a diff CSV for each common file, in output_dir, named <filename>_diff.csv.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Compare all matching CSV files in two folders.")
    parser.add_argument('folder1', help='Path to first folder containing CSV files')
    parser.add_argument('folder2', help='Path to second folder containing CSV files')
    parser.add_argument('output_dir', help='Directory to write the diff CSV files')
    args = parser.parse_args()

    folder1 = args.folder1
    folder2 = args.folder2
    output_dir = args.output_dir
    # List all CSV files in both folders
    files1 = set(f for f in os.listdir(folder1) if f.lower().endswith('.csv'))
    files2 = set(f for f in os.listdir(folder2) if f.lower().endswith('.csv'))
    
    common_files = files1 & files2

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    if not common_files:
        print("No matching CSV files found in both folders.")
        return
    
    for fname in sorted(common_files):
        file1_path = os.path.join(folder1, fname)
        file2_path = os.path.join(folder2, fname)
        output_path = os.path.join(output_dir, f"{fname}_diff.csv")
        compare_csv_files(file1_path, file2_path, output_path)

if __name__ == '__main__':
    main()

