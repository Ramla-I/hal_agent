import xml.etree.ElementTree as ET
import ast
import sys
import os
from pathlib import Path
import argparse
import re
import json
import csv

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

def convert_int_to_hex_string(int_val):
    if isinstance(int_val, int):
        return f"0x{int_val:X}"
    return int_val

def parse_svd_registers(svd_path):
    tree = ET.parse(svd_path)
    root = tree.getroot()
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'
    
    peripherals = {}

    for p in root.findall(f'.//{ns}peripheral'):
        peripheral_name = p.find(f'{ns}name').text.strip().lower()
        peripheral = p

        # Get all registers
        registers = {}
        registers_elem = peripheral.find(f'{ns}registers')
        if registers_elem is not None:
            for reg in registers_elem.findall(f'{ns}register'):
                reg_name = reg.find(f'{ns}name').text.strip().lower()
                address_offset = convert_hex_string_to_int(reg.find(f'{ns}addressOffset').text.strip())
                reset_value = convert_hex_string_to_int(reg.find(f'{ns}resetValue').text.strip()) if reg.find(f'{ns}resetValue') is not None else ''
                size = int(reg.find(f'{ns}size').text.strip(), 0) if reg.find(f'{ns}size') is not None else None
                # Fields
                fields = []
                fields_elem = reg.find(f'{ns}fields')
                if fields_elem is not None:
                    for field in fields_elem.findall(f'{ns}field'):
                        field_name = field.find(f'{ns}name').text.strip().lower()
                        # description = field.find(f'{ns}description').text.strip() if field.find(f'{ns}description') is not None else ''
                        bit_offset = int(field.find(f'{ns}bitOffset').text.strip())
                        bit_width = int(field.find(f'{ns}bitWidth').text.strip())
                        # Enumerated values (optional)
                        enumerated_values = []
                        enum_elem = field.find(f'{ns}enumeratedValues')
                        if enum_elem is not None:
                            for enum in enum_elem.findall(f'{ns}enumeratedValue'):
                                value = enum.find(f'{ns}value').text.strip()
                                name = enum.find(f'{ns}name').text.strip().lower()
                                enumerated_values.append({'name': name, 'value': value})
                        fields.append({
                            'name': field_name,
                            # 'description': description,
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
        peripherals[peripheral_name] = registers
    return peripherals

def parse_output_register_from_json(output_path):
    # The file contains a JSON list of RegisterInfo objects
    with open(output_path, 'r') as f:
        content = f.read()
    register = json.loads(content)

    # The JSON file (output) uses the RegisterInfo model, which has a different structure from the SVD dicts expected by compare_registers_from_json.
    # We'll convert the loaded json (RegisterInfo dict) to an SVD-like dict:
    def bitfield_to_svd_field(field):
        # field: BitField-as-dict
        # SVD expects:
        #   name, description, bit_offset, bit_width, enumerated_values (with 'name', 'value')
        bit_number = field.get('bit_number', {})
        start = bit_number.get('start_bit', 0)
        end = bit_number.get('end_bit', 0)
        bit_offset = min(start, end)
        bit_width = abs(end - start) + 1
        # Enumerated values:
        enum_list = field.get('enumerated_values', [])
        enumerated_values = []
        for enum in enum_list:
            enumerated_values.append({
                'name': enum.get('name', '').lower(),
                'value': enum.get('value', '')
            })
        return {
            'name': field.get('name', '').lower(),
            'description': field.get('description', ''),
            'bit_offset': bit_offset,
            'bit_width': bit_width,
            'enumerated_values': enumerated_values
        }

    fields = []
    for f in register.get('subfields', []):
        fields.append(bitfield_to_svd_field(f))

    svd_like = {
        'address_offset': register.get('address_offset', ''),
        'reset_value': register.get('reset_value', ''),
        'size': register.get('size', None),
        'fields': fields
    }
    register = svd_like
    return register

def parse_output_registers_from_json(output_directory):
    peripherals = {}
    registers = {}
    for file in os.listdir(output_directory):
        if not file.endswith(".csv") and "summary" not in file:
            peripheral_name = file.split('_')[0].lower()
            register_name = file.split('_')[1].lower()
            register = parse_output_register_from_json(os.path.join(output_directory, file))
            if peripheral_name not in peripherals:
                peripherals[peripheral_name] = {}
            peripherals[peripheral_name][register_name] = register

    return peripherals

def compare_registers_from_json(svd_peripherals, out_peripherals):
    register_summary = {}
    register_diff = {}
    field_diff = {}

    svd_keys = set(svd_peripherals.keys())
    out_keys = set(out_peripherals.keys())
    peripherals_missing_in_output = len(svd_keys - out_keys)
    peripherals_present_in_both = len(svd_keys & out_keys)

    peripheral_summary = {
        'total': len(svd_keys),
        'just svd': peripherals_missing_in_output,
        'both': peripherals_present_in_both
    }

    for peripheral in svd_keys & out_keys:
        svd_registers = svd_peripherals[peripheral]
        out_registers = out_peripherals[peripheral]
        registers_missing_in_output = len(svd_registers.keys() - out_registers.keys())
        registers_present_in_both = len(svd_registers.keys() & out_registers.keys())
        register_summary[peripheral] = {
            'just svd': registers_missing_in_output,
            'both': registers_present_in_both,
        }

        for register in svd_registers.keys() & out_registers.keys():
            svd_register = svd_registers[register]
            out_register = out_registers[register]

            # Compare top-level register values (excluding 'fields')
            top_keys = set(svd_register.keys()) | set(out_register.keys())
            top_keys -= {'fields'}
            for key in top_keys:
                svd_value = svd_register.get(key)
                out_value = out_register.get(key)
                if key == "reset_value" or key == "address_offset":
                    svd_value = convert_hex_string_to_int(svd_value)
                    out_value = convert_hex_string_to_int(out_value)
                
                if key == "size" and svd_value == 32 and out_value == 16:
                    continue

                if out_value == "":
                    continue

                if svd_value != out_value:
                    if peripheral not in register_diff:
                        register_diff[peripheral] = {}
                    if register not in register_diff[peripheral]:
                        register_diff[peripheral][register] = {}
                    if key == "reset_value" or key == "address_offset":
                        svd_value = convert_int_to_hex_string(svd_value)
                        out_value = convert_int_to_hex_string(out_value)
                    register_diff[peripheral][register][key] = {
                        'svd': svd_value,
                        'output': out_value
                    }

            # Compare all fields except description
            fields_svd = {f['name']: f for f in svd_register.get('fields', [])}
            fields_out = {f['name']: f for f in out_register.get('fields', [])}

            fields_svd_names = set(fields_svd.keys())
            fields_out_names = set(fields_out.keys())

            missing_fields = fields_svd_names - fields_out_names
            extra_fields = fields_out_names - fields_svd_names
            common_fields = fields_svd_names & fields_out_names

            if missing_fields or extra_fields:
                if peripheral not in register_diff:
                    register_diff[peripheral] = {}
                if register not in register_diff[peripheral]:
                    register_diff[peripheral][register] = {}
                # register_diff[peripheral][register]['fields'] = {
                #     'svd': sorted(missing_fields),
                #     'output': sorted(extra_fields),
                #     'both': sorted(common_fields)
                # }
                register_diff[peripheral][register]['fields'] = {
                    'svd': len(missing_fields),
                    'output': len(extra_fields),
                    'both': len(common_fields),
                }

            for field_name in common_fields:
                svd_field = fields_svd[field_name]
                out_field = fields_out[field_name]

                # bit offset
                if svd_field.get('bit_offset') != out_field.get('bit_offset'):
                    if peripheral not in field_diff:
                        field_diff[peripheral] = {}
                    if register not in field_diff[peripheral]:
                        field_diff[peripheral][register] = {}
                    if field_name not in field_diff[peripheral][register]:
                        field_diff[peripheral][register][field_name] = {}
                    field_diff[peripheral][register][field_name]['bit_offset'] = {
                        'svd': svd_field.get('bit_offset'),
                        'output': out_field.get('bit_offset')
                    }
                
                # bit width
                if svd_field.get('bit_width') != out_field.get('bit_width'):
                    if peripheral not in field_diff:
                        field_diff[peripheral] = {}
                    if register not in field_diff[peripheral]:
                        field_diff[peripheral][register] = {}
                    if field_name not in field_diff[peripheral][register]:
                        field_diff[peripheral][register][field_name] = {}
                    field_diff[peripheral][register][field_name]['bit_width'] = {
                        'svd': svd_field.get('bit_width'),
                        'output': out_field.get('bit_width')
                    }
                
                # enums
                svd_enum_names = set(ev['name'] for ev in svd_field.get('enumerated_values', [])) if isinstance(svd_field.get('enumerated_values'), list) else set()
                out_enum_names = set(ev['name'] for ev in out_field.get('enumerated_values', [])) if isinstance(out_field.get('enumerated_values'), list) else set()
                if svd_enum_names != out_enum_names:
                    if peripheral not in field_diff:
                        field_diff[peripheral] = {}
                    if register not in field_diff[peripheral]:
                        field_diff[peripheral][register] = {}
                    if field_name not in field_diff[peripheral][register]:
                        field_diff[peripheral][register][field_name] = {}
                    field_diff[peripheral][register][field_name]['enum_names'] = {
                        'svd': len(svd_enum_names - out_enum_names),
                        'output': len(out_enum_names - svd_enum_names),
                        'both': len(svd_enum_names & out_enum_names)
                    }

    return peripheral_summary, register_summary, register_diff, field_diff

def main():
    parser = argparse.ArgumentParser(description="Compare SVD peripherals with output peripheral info in out folder.")
    parser.add_argument('svd_path', help='Path to SVD file')
    parser.add_argument('agent_output_folder', help='Path to agent output folder containing registerfiles')
    parser.add_argument('results_directory', help='Folder to save the results')
    args = parser.parse_args()

    
    svd_regs = parse_svd_registers(args.svd_path)
    print(f"Parsed {len(svd_regs)} peripherals from SVD file")
    out_regs = parse_output_registers_from_json(args.agent_output_folder)
    print(f"Parsed {len(out_regs)} peripherals from agent output folder")
    peripheral_summary, register_summary, register_diff, field_diff = compare_registers_from_json(svd_regs, out_regs)

    # Prepare CSV output path
    results_dir = args.results_directory
    peripheral_summary_path = os.path.join(results_dir, "peripheral_summary.csv")

    # Ensure the directory exists before creating the CSV file
    os.makedirs(results_dir, exist_ok=True)
    with open(peripheral_summary_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["total", "just_svd", "both"])
        writer.writerow([peripheral_summary['total'], peripheral_summary['just svd'], peripheral_summary['both']])
    
    register_summary_path = os.path.join(results_dir, "register_summary.csv")
    with open(register_summary_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["peripheral", "just_svd", "both"])
        for peripheral in register_summary.keys():
            writer.writerow([peripheral, register_summary[peripheral]['just svd'], register_summary[peripheral]['both']])
    
    register_diff_path = os.path.join(results_dir, "register_diff.csv")
    with open(register_diff_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["peripheral", "register", "key", "just_svd", "just_output", "both"])
        for peripheral in register_diff.keys():
            for register in register_diff[peripheral].keys():
                for key in register_diff[peripheral][register].keys():
                    if key == "fields":
                        writer.writerow([peripheral, register, key, register_diff[peripheral][register][key]['svd'], register_diff[peripheral][register][key]['output'], register_diff[peripheral][register][key]['both']])
                    else:
                        writer.writerow([peripheral, register, key, register_diff[peripheral][register][key]['svd'], register_diff[peripheral][register][key]['output']])

    field_diff_path = os.path.join(results_dir, "field_diff.csv")
    with open(field_diff_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["peripheral", "register", "field_name", "key", "just_svd", "just_output", "both"])
        for peripheral in field_diff.keys():
            for register in field_diff[peripheral].keys():
                for field_name in field_diff[peripheral][register].keys():
                    for key in field_diff[peripheral][register][field_name].keys():
                        if key == "enum_names":
                            writer.writerow([peripheral, register, field_name, key, field_diff[peripheral][register][field_name][key]['svd'], field_diff[peripheral][register][field_name][key]['output'], field_diff[peripheral][register][field_name][key]['both']])
                        else:
                            writer.writerow([peripheral, register, field_name, key, field_diff[peripheral][register][field_name][key]['svd'], field_diff[peripheral][register][field_name][key]['output']])


if __name__ == '__main__':
    main()
