import xml.etree.ElementTree as ET
import ast
import sys
import os
from pathlib import Path
import argparse
import re

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from defs import RegisterInfo, BitField, BitNumber

def strip_bracket_suffix(s):
    if isinstance(s, str):
        idx = s.find('[')
        if idx != -1:
            return s[:idx]
    return s

def convert_hex_string_to_int(hex_str):
    if isinstance(hex_str, str) and hex_str.strip().startswith('0x'):
        try:
            return int(hex_str.strip().replace(' ', ''), 16)
        except Exception as e:
            # print(f"Error converting hex string to int: {hex_str} ({e})")
            return hex_str
    return hex_str

def parse_svd_registers(svd_path, peripheral_name):
    tree = ET.parse(svd_path)
    root = tree.getroot()
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'
    # Find the peripheral
    peripheral = None
    for p in root.findall(f'.//{ns}peripheral'):
        name_elem = p.find(f'{ns}name')
        if name_elem is not None and name_elem.text and name_elem.text.strip().lower() == peripheral_name.lower():
            peripheral = p
            break
    if peripheral is None:
        raise ValueError(f"Peripheral '{peripheral_name}' not found in SVD file.")
    # Get all registers
    registers = {}
    registers_elem = peripheral.find(f'{ns}registers')
    if registers_elem is not None:
        for reg in registers_elem.findall(f'{ns}register'):
            reg_name = reg.find(f'{ns}name').text.strip()
            address_offset = convert_hex_string_to_int(reg.find(f'{ns}addressOffset').text.strip())
            reset_value = convert_hex_string_to_int(reg.find(f'{ns}resetValue').text.strip()) if reg.find(f'{ns}resetValue') is not None else ''
            size = int(reg.find(f'{ns}size').text.strip(), 0) if reg.find(f'{ns}size') is not None else None
            # Fields
            fields = []
            fields_elem = reg.find(f'{ns}fields')
            if fields_elem is not None:
                for field in fields_elem.findall(f'{ns}field'):
                    field_name = field.find(f'{ns}name').text.strip()
                    description = field.find(f'{ns}description').text.strip() if field.find(f'{ns}description') is not None else ''
                    bit_offset = int(field.find(f'{ns}bitOffset').text.strip())
                    bit_width = int(field.find(f'{ns}bitWidth').text.strip())
                    # Enumerated values (optional)
                    enumerated_values = []
                    enum_elem = field.find(f'{ns}enumeratedValues')
                    if enum_elem is not None:
                        for enum in enum_elem.findall(f'{ns}enumeratedValue'):
                            value = enum.find(f'{ns}value').text.strip()
                            name = enum.find(f'{ns}name').text.strip()
                            enumerated_values.append({'name': name, 'value': value})
                    fields.append({
                        'name': field_name,
                        'description': description,
                        'bit_offset': bit_offset,
                        'bit_width': bit_width,
                        'enumerated_values': enumerated_values
                    })
            registers[reg_name] = {
                'address_offset': address_offset,
                'reset_value': reset_value,
                'size': size,
                'fields': fields
            }
    return registers

def parse_output_registers(output_path, peripheral_name):
    # The file contains a Python list of RegisterInfo objects
    with open(output_path, 'r') as f:
        content = f.read()
    # Evaluate the list safely
    local_vars = {}
    exec('from defs import RegisterInfo, BitField, BitNumber, EnumValue\n' + content, {}, local_vars)
    registers = local_vars['registers']
    reg_dict = {}
    for reg in registers:
        fields = []
        for field in reg.subfields:
            fields.append({
                'name': strip_bracket_suffix(field.name),
                'description': field.description,
                'bit_offset': min(field.bit_number.start_bit, field.bit_number.end_bit),
                'bit_width': abs(field.bit_number.end_bit - field.bit_number.start_bit) + 1,
                'enumerated_values': [ {'name': ev.name, 'value': ev.value} for ev in getattr(field, 'enumerated_values', []) ]
            })
        # If the datasheet_register_abbreviation contains the peripheral name + '_', strip it to just the register name
        reg_abbr = reg.datasheet_register_abbreviation
        # Remove any prefix that matches '<something>_' where <something> contains the peripheral_name
        # match = re.match(rf'([A-Za-z0-9]*{peripheral_name}[A-Za-z0-9]*)_(.*)', reg_abbr)
        # if match:
        #     reg_abbr = match.group(2)
        # Remove anything before the first underscore (including the underscore itself)
        if '_' in reg_abbr:
            reg_abbr = reg_abbr.split('_', 1)[1]
        reg_dict[reg_abbr] = {
            'address_offset': convert_hex_string_to_int(reg.address_offset),
            'reset_value': convert_hex_string_to_int(reg.reset_value),
            'size': reg.size,
            'fields': fields
        }
    return reg_dict

def compare_registers(svd_regs, out_regs):
    summary = []
    svd_keys = set(svd_regs.keys())
    out_keys = set(out_regs.keys())
    missing_in_output = svd_keys - out_keys
    extra_in_output = out_keys - svd_keys
    if missing_in_output:
        summary.append(f"Registers in SVD but missing in output: {sorted(missing_in_output)}")
    if extra_in_output:
        summary.append(f"Registers in output but missing in SVD: {sorted(extra_in_output)}")
    summary.append(f"Registers present in both SVD and output: {sorted(svd_keys & out_keys)}")
    total_fields_svd = 0
    total_fields_output = 0
    matching_fields = 0
    total_equal_enums = 0
    for reg in svd_keys & out_keys:
        s = svd_regs[reg]
        o = out_regs[reg]
        diffs = []
        
        total_fields_svd += len(s['fields'])
        total_fields_output += len(o['fields'])

        if s['address_offset'] != o['address_offset']:
            diffs.append(f"address_offset: SVD={s['address_offset']} output={o['address_offset']}")
        if s['reset_value'] != o['reset_value']:
            diffs.append(f"reset_value: SVD={s['reset_value']} output={o['reset_value']}")
        if s['size'] != o['size']:
            diffs.append(f"size: SVD={s['size']} output={o['size']}")
        # Compare fields
        s_fields = {f['name']: f for f in s['fields']}
        o_fields = {f['name']: f for f in o['fields']}
        missing_fields = set(s_fields.keys()) - set(o_fields.keys())
        extra_fields = set(o_fields.keys()) - set(s_fields.keys())
        matching_fields += len(s_fields.keys() & o_fields.keys())
        if missing_fields:
            diffs.append(f"Fields in SVD but missing in output: {sorted(missing_fields)}")
        if extra_fields:
            diffs.append(f"Fields in output but missing in SVD: {sorted(extra_fields)}")
        for fname in s_fields.keys() & o_fields.keys():
            sf = s_fields[fname]
            of = o_fields[fname]
            if sf['bit_offset'] != of['bit_offset'] or sf['bit_width'] != of['bit_width']:
                diffs.append(f"Field {fname} bit range: SVD=({sf['bit_offset']},{sf['bit_width']}) output=({of['bit_offset']},{of['bit_width']})")
            # if sf['description'] != of['description']:
            #     diffs.append(f"Field {fname} description differs.")
            # Compare enumerated values
            svd_enum = {(e['name'], e['value']) for e in sf.get('enumerated_values', [])}
            out_enum = {(e['name'], e['value']) for e in of.get('enumerated_values', [])}
            if svd_enum != out_enum:
                diffs.append(f"Field {fname} enumerated values differ.")
            else:
                total_equal_enums += 1
        if diffs:
            summary.append(f"Register {reg} differs: " + "; ".join(diffs))
    
    # Print stats in a table form
    from collections import Counter
    # Combined stats and fine-grained stats calculation and printing

    num_missing = 0
    num_extra = 0
    num_both = 0
    num_diff = 0

    reg_diff_stats = {
        'registers_in_svd_but_missing_in_output': 0,
        'registers_in_output_but_missing_in_svd': 0,
        'registers_present_in_both_svd_and_output': 0,
        'registers_with_differences': 0,
        'address_offset': 0,
        'reset_value': 0,
        'size': 0,
        'missing_fields': 0,
        'extra_fields': 0,
        'field_bit_range': 0,
        'field_enum_diff': 0,
        'total_fields_svd': total_fields_svd,
        'total_fields_output': total_fields_output,
        'total_matching_fields': matching_fields,
        'total_equal_enums': total_equal_enums,
    }

    for line in summary:
        # Coarse stats
        if line.startswith("Registers in SVD but missing in output:"):
            try:
                reg_diff_stats['registers_in_svd_but_missing_in_output'] = len(eval(line.split(":", 1)[1].strip()))
            except Exception:
                reg_diff_stats['registers_in_svd_but_missing_in_output'] = 0
        elif line.startswith("Registers in output but missing in SVD:"):
            try:
                reg_diff_stats['registers_in_output_but_missing_in_svd'] = len(eval(line.split(":", 1)[1].strip()))
            except Exception:
                reg_diff_stats['registers_in_output_but_missing_in_svd'] = 0
        elif line.startswith("Registers present in both SVD and output:"):
            try:
                reg_diff_stats['registers_present_in_both_svd_and_output'] = len(eval(line.split(":", 1)[1].strip()))
            except Exception:
                reg_diff_stats['registers_present_in_both_svd_and_output'] = 0
        elif line.startswith("Register ") and "differs:" in line:
            reg_diff_stats['registers_with_differences'] += 1
            # Fine-grained stats
            diff_part = line.split("differs:", 1)[1]
            for diff in diff_part.split(";"):
                diff = diff.strip()
                if diff.startswith("address_offset:"):
                    reg_diff_stats['address_offset'] += 1
                elif diff.startswith("reset_value:"):
                    reg_diff_stats['reset_value'] += 1
                elif diff.startswith("size:"):
                    reg_diff_stats['size'] += 1
                elif diff.startswith("Fields in SVD but missing in output:"):
                    try:
                        fields = eval(diff.split(":", 1)[1].strip())
                        reg_diff_stats['missing_fields'] += len(fields)
                    except Exception:
                        reg_diff_stats['missing_fields'] += 1
                elif diff.startswith("Fields in output but missing in SVD:"):
                    try:
                        fields = eval(diff.split(":", 1)[1].strip())
                        reg_diff_stats['extra_fields'] += len(fields)
                    except Exception:
                        reg_diff_stats['extra_fields'] += 1
                elif "bit range:" in diff:
                    reg_diff_stats['field_bit_range'] += 1
                elif "enumerated values differ" in diff:
                    reg_diff_stats['field_enum_diff'] += 1

    # Print fine-grained stats
    # print(f"{'Fine-grained Stat':<40} {'Count':>10}")
    # print("-" * 52)
    # print(f"{'Registers in SVD but missing in output':<40} {reg_diff_stats['registers_in_svd_but_missing_in_output']:>10}")
    # print(f"{'Registers in output but missing in SVD':<40} {reg_diff_stats['registers_in_output_but_missing_in_svd']:>10}")
    # print(f"{'Registers present in both SVD and output':<40} {reg_diff_stats['registers_present_in_both_svd_and_output']:>10}")
    # print(f"{'Registers with differences':<40} {reg_diff_stats['registers_with_differences']:>10}")
    # print(f"{'Registers with address_offset diff':<40} {reg_diff_stats['address_offset']:>10}")
    # print(f"{'Registers with reset_value diff':<40} {reg_diff_stats['reset_value']:>10}")
    # print(f"{'Registers with size diff':<40} {reg_diff_stats['size']:>10}")
    # print(f"{'Fields in SVD but missing in output':<40} {reg_diff_stats['missing_fields']:>10}")
    # print(f"{'Fields in output but missing in SVD':<40} {reg_diff_stats['extra_fields']:>10}")
    # print(f"{'Fields with bit range diff':<40} {reg_diff_stats['field_bit_range']:>10}")
    # print(f"{'Fields with enum value diff':<40} {reg_diff_stats['field_enum_diff']:>10}")
    # print("-" * 52)
    return summary, reg_diff_stats

def main():
    parser = argparse.ArgumentParser(description="Compare SVD peripherals with output peripheral info in out folder.")
    parser.add_argument('svd_path', help='Path to SVD file')
    parser.add_argument('out_folder', help='Path to output folder containing peripheral files')
    parser.add_argument('results_path', help='Output summary file')
    args = parser.parse_args()

    summary_lines = []
    out_files = [f for f in os.listdir(args.out_folder) if os.path.isfile(os.path.join(args.out_folder, f))]
    out_files = [f for f in out_files if f != "warnings"]

    if not out_files:
        summary_lines.append("No peripheral files found in output folder.")
    else:
        for fname in sorted(out_files):
            peripheral_name = fname
            output_path = os.path.join(args.out_folder, fname)
            try:
                svd_regs = parse_svd_registers(args.svd_path, peripheral_name)
            except Exception as e:
                summary_lines.append(f"Peripheral {peripheral_name}: Error parsing SVD: {e} \n")
                continue
            try:
                out_regs = parse_output_registers(output_path, peripheral_name)
            except Exception as e:
                summary_lines.append(f"Peripheral {peripheral_name}: Error parsing output file: {e} \n")
                continue
            summary, reg_diff_stats = compare_registers(svd_regs, out_regs)
            summary_lines.append(f"Comparison of {peripheral_name} registers")
            summary_lines.append(f"SVD file: {args.svd_path}")
            summary_lines.append(f"Output file: {output_path}")
            summary_lines.append(f"Summary:")
            if summary:
                summary_lines.extend(summary)
            else:
                summary_lines.append("No differences found.")
            summary_lines.append("")  # Blank line between peripherals

            # Store reg_diff_stats for later summing
            if 'all_reg_diff_stats' not in locals():
                all_reg_diff_stats = []
            all_reg_diff_stats.append(reg_diff_stats)

    # Ensure the summary file exists or is created if it doesn't
    # Create the directory for the results file if it doesn't exist
    results_dir = os.path.dirname(args.results_path)
    if results_dir:
        os.makedirs(results_dir, exist_ok=True)
    # Also create a file named 'summary' in the results directory
    summary_path = os.path.join(results_dir, "summary") if results_dir else "summary"
    with open(summary_path, "w") as summary_file:
        for line in summary_lines:
            summary_file.write(line + '\n')

    # Summarize all reg_diff_stats
    if 'all_reg_diff_stats' in locals():
        total_stats = {}
        for stats in all_reg_diff_stats:
            for key, value in stats.items():
                if key not in total_stats:
                    total_stats[key] = 0
                total_stats[key] += value

        # Print total stats
        # Write total statistics to a file named 'ptiny' in the results directory
        table_path = os.path.join(os.path.dirname(args.results_path), "table") if os.path.dirname(args.results_path) else "table"
        with open(table_path, "w") as table_file:
            table_file.write("Total Statistics:\n")
            table_file.write(f"{'Stat':<40} {'Count':>10}\n")
            table_file.write("-" * 52 + "\n")
            for key, value in total_stats.items():
                table_file.write(f"{key:<40} {value:>10}\n")
            table_file.write("-" * 52 + "\n")

    print(f"Comparison complete. Summary written to {args.results_path}")

def main2():
    parser = argparse.ArgumentParser(description="Compare SVD peripherals with output peripheral info in out folder.")
    parser.add_argument('out_file', help='Path to output file containing peripheral files')
    args = parser.parse_args()

    out_regs = parse_output_registers(args.out_file)
    print(out_regs)

if __name__ == '__main__':
    main()
