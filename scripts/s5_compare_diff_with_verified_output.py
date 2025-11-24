#!/usr/bin/env python3
import argparse
import csv
import sys
from typing import Dict, Tuple, Optional, List


def normalize_header(name: str) -> str:
    return ''.join(ch.lower() for ch in name if ch.isalnum())


def find_column(headers: List[str], candidates: List[str]) -> Optional[str]:
    normalized_to_original: Dict[str, str] = {normalize_header(h): h for h in headers}
    for cand in candidates:
        norm = normalize_header(cand)
        if norm in normalized_to_original:
            return normalized_to_original[norm]
    return None


def build_key(row: Dict[str, str], per_col: str, reg_col: str, key_col: str, field_col: Optional[str]) -> Tuple[str, str, Optional[str], str]:
    peripheral = (row.get(per_col) or '').strip()
    register = (row.get(reg_col) or '').strip()
    field_name = (row.get(field_col) or '').strip() if field_col else None
    key = (row.get(key_col) or '').strip()
    # Normalize empty field_name to None
    if field_col and field_name == '':
        field_name = None
    return peripheral, register, field_name, key


def compare_diff_with_verified_datasheet(diff_csv_path: str, verified_csv_path: str, verified_diff_csv_path: str):
    # Read verified CSV and index by key
    try:
        with open(verified_csv_path, newline='') as vf:
            vreader = csv.DictReader(vf)
            vheaders = vreader.fieldnames or []
            if not vheaders:
                raise ValueError('Verified CSV has no headers')

            per_col_v = find_column(vheaders, ['peripheral'])
            reg_col_v = find_column(vheaders, ['register'])
            key_col_v = find_column(vheaders, ['key'])
            field_col_v = find_column(vheaders, ['field_name'])
            correct_col = find_column(vheaders, ['correct_value'])

            missing = [name for name, col in [
                ('peripheral', per_col_v),
                ('register', reg_col_v),
                ('key', key_col_v),
                ('Correct Value', correct_col),
            ] if col is None]
            if missing:
                print(f"Verified CSV missing columns: {', '.join(missing)}", file=sys.stderr)
                raise ValueError(f"Verified CSV missing columns: {', '.join(missing)}")

            verified_index: Dict[Tuple[str, str, Optional[str], str], str] = {}
            for row in vreader:
                k = build_key(row, per_col_v, reg_col_v, key_col_v, field_col_v)
                # If duplicates, last one wins
                verified_index[k] = (row.get(correct_col) or '').strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Verified CSV not found: {verified_csv_path}")

    # Read diff CSV, compute flags, and write output
    try:
        with open(diff_csv_path, newline='') as df:
            dreader = csv.DictReader(df)
            dheaders = dreader.fieldnames or []
            if not dheaders:
                print('Diff CSV has no headers', file=sys.stderr)
                return 2

            per_col_d = find_column(dheaders, ['peripheral'])
            reg_col_d = find_column(dheaders, ['register'])
            key_col_d = find_column(dheaders, ['key'])
            field_col_d = find_column(dheaders, ['field_name'])

            js_col = find_column(dheaders, ['just_svd'])
            jo_col = find_column(dheaders, ['just_output'])

            missing_d = [name for name, col in [
                ('peripheral', per_col_d),
                ('register', reg_col_d),
                ('key', key_col_d),
                ('just_svd', js_col),
                ('just_output', jo_col),
            ] if col is None]
            if missing_d:
                raise ValueError(f"Diff CSV missing columns: {', '.join(missing_d)}")

            # Only include field_name in the key if both files have the column
            use_field = (field_col_d is not None) and (field_col_v is not None)

            # Prepare output headers: all diff columns plus Bug, FP, Neither (append if not already present)
            out_headers = list(dheaders)
            for extra in ['Bug', 'FP', 'Neither', 'Actual Value']:
                if extra not in out_headers:
                    out_headers.append(extra)

            rows_to_write: List[Dict[str, str]] = []
            for row in dreader:
                # Build key to query verified
                field_for_key = field_col_d if use_field else None
                k = build_key(row, per_col_d, reg_col_d, key_col_d, field_for_key)
                correct_value = verified_index.get(k)

                bug = ''
                fp = ''
                neither = ''
                actual_value = ''

                js_val = (row.get(js_col) or '').strip()
                jo_val = (row.get(jo_col) or '').strip()

                if correct_value is not None:
                    if js_val == correct_value:
                        fp = '1'
                    if jo_val == correct_value:
                        bug = '1'
                    if js_val != correct_value and jo_val != correct_value:
                        bug = '1'
                        actual_value = correct_value
                else:
                    # No matching verified row: leave all flags 0
                    pass

                out_row = dict(row)
                out_row['Bug'] = bug
                out_row['FP'] = fp
                out_row['Neither'] = neither
                out_row['Actual Value'] = actual_value
                # INSERT_YOUR_CODE
                # If the key is "fields" or "enum_names", skip appending this row
                key_val = (row.get(key_col_d) or '').strip()
                if key_val in ('fields', 'enum_names'):
                    continue
                rows_to_write.append(out_row)

        with open(verified_diff_csv_path, 'w', newline='') as of:
            writer = csv.DictWriter(of, fieldnames=out_headers)
            writer.writeheader()
            writer.writerows(rows_to_write)

    except FileNotFoundError:
        raise FileNotFoundError(f"Diff CSV not found: {diff_csv_path}")