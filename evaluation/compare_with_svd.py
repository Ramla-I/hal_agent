import xml.etree.ElementTree as ET
import ast
import sys
import os
from pathlib import Path

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from defs import RegisterInfo, BitField, BitNumber

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
            address_offset = reg.find(f'{ns}addressOffset').text.strip()
            reset_value = reg.find(f'{ns}resetValue').text.strip() if reg.find(f'{ns}resetValue') is not None else ''
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

def parse_output_registers(output_path):
    # The file contains a Python list of RegisterInfo objects
    with open(output_path, 'r') as f:
        content = f.read()
    # Evaluate the list safely
    local_vars = {}
    exec('from defs import RegisterInfo, BitField, BitNumber\n' + content, {}, local_vars)
    registers = local_vars['registers']
    reg_dict = {}
    for reg in registers:
        fields = []
        for field in reg.subfields:
            fields.append({
                'name': field.name,
                'description': field.description,
                'bit_offset': field.bit_number.start_bit,
                'bit_width': field.bit_number.end_bit - field.bit_number.start_bit + 1,
                'enumerated_values': [ {'name': ev.name, 'value': ev.value} for ev in getattr(field, 'enumerated_values', []) ]
            })
        reg_dict[reg.datasheet_register_abbreviation] = {
            'address_offset': reg.address_offset,
            'reset_value': reg.reset_value,
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
    for reg in svd_keys & out_keys:
        s = svd_regs[reg]
        o = out_regs[reg]
        diffs = []
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
        if missing_fields:
            diffs.append(f"Fields in SVD but missing in output: {sorted(missing_fields)}")
        if extra_fields:
            diffs.append(f"Fields in output but missing in SVD: {sorted(extra_fields)}")
        for fname in s_fields.keys() & o_fields.keys():
            sf = s_fields[fname]
            of = o_fields[fname]
            if sf['bit_offset'] != of['bit_offset'] or sf['bit_width'] != of['bit_width']:
                diffs.append(f"Field {fname} bit range: SVD=({sf['bit_offset']},{sf['bit_width']}) output=({of['bit_offset']},{of['bit_width']})")
            if sf['description'] != of['description']:
                diffs.append(f"Field {fname} description differs.")
            # Compare enumerated values
            svd_enum = {(e['name'], e['value']) for e in sf.get('enumerated_values', [])}
            out_enum = {(e['name'], e['value']) for e in of.get('enumerated_values', [])}
            if svd_enum != out_enum:
                diffs.append(f"Field {fname} enumerated values differ.")
        if diffs:
            summary.append(f"Register {reg} differs: " + "; ".join(diffs))
    return summary

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Compare SVD peripheral with output peripheral info.")
    parser.add_argument('svd_path', help='Path to SVD file')
    parser.add_argument('peripheral_name', help='Peripheral name (e.g. ADC1)')
    parser.add_argument('output_path', help='Path to output peripheral file')
    parser.add_argument('--summary', default='comparison_summary.txt', help='Output summary file')
    args = parser.parse_args()
    svd_regs = parse_svd_registers(args.svd_path, args.peripheral_name)
    out_regs = parse_output_registers(args.output_path)
    summary = compare_registers(svd_regs, out_regs)
    with open(args.summary, 'w') as f:
        for line in summary:
            f.write(line + '\n')
    print(f"Comparison complete. Summary written to {args.summary}")

if __name__ == '__main__':
    main()
