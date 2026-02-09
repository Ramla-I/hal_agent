import xml.etree.ElementTree as ET
import ast
import sys
import os
from pathlib import Path
import argparse
import re
import json
import csv

# HACK, remove this once we have a proper package structure
# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from defs import RegisterInfo, BitField, BitNumber
from utils.generator_facts import convert_generator_register_to_svd_like

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
                # Remove peripheralname_ prefix from register name if present
                prefix = peripheral_name + '_'
                if reg_name.startswith(prefix):
                    reg_name = reg_name[len(prefix):]
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
                                if enum.find(f'{ns}value') is not None:
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

    # Convert the loaded json (RegisterInfo dict) to an SVD-like dict
    svd_like = convert_generator_register_to_svd_like(
        register,
        include_enums=True,
        default_zero=False,
    )
    return svd_like

def parse_output_registers_from_json(output_directory):
    peripherals = {}
    registers = {}
    for file in os.listdir(output_directory):
        if not os.path.isdir(os.path.join(output_directory, file)):
            peripheral_name = file.split('_')[0].lower()
            register_name = file.split('_')[1].lower()
            register = parse_output_register_from_json(os.path.join(output_directory, file))
            if peripheral_name not in peripherals:
                peripherals[peripheral_name] = {}
            peripherals[peripheral_name][register_name] = register

    return peripherals

def compare_registers_from_json(svd_peripherals, out_peripherals):
    register_summary = {}
    subfield_summary = {}
    register_diff = {}
    field_diff = {}

    svd_keys = set(svd_peripherals.keys())
    out_keys = set(out_peripherals.keys())
    peripherals_missing_in_output = len(svd_keys - out_keys)
    peripherals_missing_in_svd = len(out_keys - svd_keys)
    peripherals_present_in_both = len(svd_keys & out_keys)

    peripheral_summary = {
        'just svd': peripherals_missing_in_output,
        'just output': peripherals_missing_in_svd,
        'both': peripherals_present_in_both
    }

    for peripheral in svd_keys & out_keys:
        svd_registers = svd_peripherals[peripheral]
        out_registers = out_peripherals[peripheral]
        registers_missing_in_output = len(svd_registers.keys() - out_registers.keys())
        registers_missing_in_svd = len(out_registers.keys() - svd_registers.keys())
        registers_present_in_both = len(svd_registers.keys() & out_registers.keys())
        register_summary[peripheral] = {
            'just svd': registers_missing_in_output,
            'just output': registers_missing_in_svd,
            'both': registers_present_in_both,
        }
        subfield_summary[peripheral] = {} # initialize subfield_summary for this peripheral

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

                if key == "size" and svd_value == 16 and out_value == 32:
                    continue
                
                if key == "size" and out_value == 0:
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

            fields_missing_in_output = len(missing_fields)
            fields_missing_in_svd = len(extra_fields)
            fields_present_in_both = len(common_fields)

            subfield_summary[peripheral][register] = {
                'just svd': fields_missing_in_output,
                'just output': fields_missing_in_svd,
                'both': fields_present_in_both
            }   

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

    return peripheral_summary, register_summary, subfield_summary, register_diff, field_diff

def compare_agent_output_with_svd(svd_path, agent_output_folder, results_directory):
    svd_regs = parse_svd_registers(svd_path)
    print(f"Parsed {len(svd_regs)} peripherals from SVD file")
    out_regs = parse_output_registers_from_json(agent_output_folder)
    print(f"Parsed {len(out_regs)} peripherals from agent output folder")
    peripheral_summary, register_summary, subfield_summary, register_diff, field_diff = compare_registers_from_json(svd_regs, out_regs)

    # Prepare CSV output path
    results_dir = results_directory
    peripheral_summary_path = os.path.join(results_dir, "peripheral_summary.csv")

    # Stats
    total_peripherals = 0
    present_peripherals = 0

    total_registers_in_present_peripherals = 0
    present_registers = 0

    total_fields_in_present_registers = 0
    present_fields = 0

    # Ensure the directory exists before creating the CSV file
    id = 0
    os.makedirs(results_dir, exist_ok=True)
    with open(peripheral_summary_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "just_svd", "just_output", "both"])
        writer.writerow([id, peripheral_summary['just svd'], peripheral_summary['just output'], peripheral_summary['both']])
        
        total_peripherals += peripheral_summary['just svd'] + peripheral_summary['both']
        present_peripherals += peripheral_summary['both']
        
        id += 1
    
    id = 0
    register_summary_path = os.path.join(results_dir, "register_summary.csv")
    with open(register_summary_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "peripheral", "just_svd", "just_output", "both"])
        for peripheral in register_summary.keys():
            writer.writerow([id, peripheral, register_summary[peripheral]['just svd'], register_summary[peripheral]['just output'], register_summary[peripheral]['both']])
            
            total_registers_in_present_peripherals += register_summary[peripheral]['just svd'] + register_summary[peripheral]['both']
            present_registers += register_summary[peripheral]['both']
            
            id += 1
    
    id = 0
    subfield_summary_path = os.path.join(results_dir, "subfield_summary.csv")
    with open(subfield_summary_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "peripheral", "register", "just_svd", "just_output", "both"])
        for peripheral in subfield_summary.keys():
            for register in subfield_summary[peripheral].keys():
                writer.writerow([id, peripheral, register, subfield_summary[peripheral][register]['just svd'], subfield_summary[peripheral][register]['just output'], subfield_summary[peripheral][register]['both']])
                
                total_fields_in_present_registers += subfield_summary[peripheral][register]['just svd'] + subfield_summary[peripheral][register]['both']
                present_fields += subfield_summary[peripheral][register]['both']
                
                id += 1
    
    print(f"peripheral coverage: {present_peripherals / total_peripherals * 100}%")
    print(f"register coverage: {present_registers / total_registers_in_present_peripherals * 100}%")
    print(f"field coverage: {present_fields / total_fields_in_present_registers * 100}%")
    print(f"\n\n")

    id = 0
    register_diff_path = os.path.join(results_dir, "register_diff.csv")
    with open(register_diff_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "peripheral", "register", "key", "just_svd", "just_output", "both"])
        for peripheral in register_diff.keys():
            for register in register_diff[peripheral].keys():
                for key in register_diff[peripheral][register].keys():
                    if key == "fields":
                        writer.writerow([id, peripheral, register, key, register_diff[peripheral][register][key]['svd'], register_diff[peripheral][register][key]['output'], register_diff[peripheral][register][key]['both']])
                        id += 1
                    else:
                        writer.writerow([id, peripheral, register, key, register_diff[peripheral][register][key]['svd'], register_diff[peripheral][register][key]['output']])
                        id += 1

    id = 0
    field_diff_path = os.path.join(results_dir, "field_diff.csv")
    with open(field_diff_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "peripheral", "register", "field_name", "key", "just_svd", "just_output", "both"])
        for peripheral in field_diff.keys():
            for register in field_diff[peripheral].keys():
                for field_name in field_diff[peripheral][register].keys():
                    for key in field_diff[peripheral][register][field_name].keys():
                        if key == "enum_names":
                            writer.writerow([id, peripheral, register, field_name, key, field_diff[peripheral][register][field_name][key]['svd'], field_diff[peripheral][register][field_name][key]['output'], field_diff[peripheral][register][field_name][key]['both']])
                            id += 1
                        else:
                            writer.writerow([id, peripheral, register, field_name, key, field_diff[peripheral][register][field_name][key]['svd'], field_diff[peripheral][register][field_name][key]['output']])
                            id += 1


if __name__ == '__main__':
    main()
