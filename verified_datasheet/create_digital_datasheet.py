import xml.etree.ElementTree as ET
import json
import csv
import os
from typing import Dict, List, Optional, Any


def convert_hex_string_to_int(hex_str):
    """Convert hex string to integer, handling various formats."""
    if isinstance(hex_str, str):
        # Remove spaces and handle hex strings
        hex_str = hex_str.strip().replace(' ', '')
        if hex_str.startswith('0x') or hex_str.startswith('0X'):
            try:
                return int(hex_str, 16)
            except ValueError:
                return hex_str
        # Try to parse as int
        try:
            return int(hex_str, 0)  # 0 means auto-detect base
        except ValueError:
            return hex_str
    return hex_str


def format_value(value: Any) -> str:
    """Format a value for CSV output."""
    if value is None:
        return ''
    if isinstance(value, int):
        return str(value)
    return str(value)


def parse_svd_registers(svd_path: str) -> Dict[str, Dict[str, Dict]]:
    """
    Parse SVD file and return a dictionary structure:
    {peripheral_name: {register_name: {address_offset, reset_value, size, fields: [...]}}}
    """
    tree = ET.parse(svd_path)
    root = tree.getroot()
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'
    
    peripherals = {}
    
    for p in root.findall(f'.//{ns}peripheral'):
        peripheral_name = p.find(f'{ns}name').text.strip().lower()
        
        registers = {}
        registers_elem = p.find(f'{ns}registers')
        if registers_elem is not None:
            for reg in registers_elem.findall(f'{ns}register'):
                reg_name = reg.find(f'{ns}name').text.strip().lower()
                # Remove peripheralname_ prefix from register name if present
                prefix = peripheral_name + '_'
                if reg_name.startswith(prefix):
                    reg_name = reg_name[len(prefix):]
                
                address_offset_elem = reg.find(f'{ns}addressOffset')
                # address_offset = convert_hex_string_to_int(address_offset_elem.text.strip()) if address_offset_elem is not None else None
                address_offset = address_offset_elem.text.strip() if address_offset_elem is not None else None
                
                reset_value_elem = reg.find(f'{ns}resetValue')
                # reset_value = convert_hex_string_to_int(reset_value_elem.text.strip()) if reset_value_elem is not None else None
                reset_value = reset_value_elem.text.strip() if reset_value_elem is not None else None
                
                size_elem = reg.find(f'{ns}size')
                size = int(size_elem.text.strip(), 0) if size_elem is not None else None
                
                # Fields
                fields = []
                fields_elem = reg.find(f'{ns}fields')
                if fields_elem is not None:
                    for field in fields_elem.findall(f'{ns}field'):
                        field_name = field.find(f'{ns}name').text.strip().lower()
                        bit_offset_elem = field.find(f'{ns}bitOffset')
                        bit_offset = int(bit_offset_elem.text.strip()) if bit_offset_elem is not None else None
                        bit_width_elem = field.find(f'{ns}bitWidth')
                        bit_width = int(bit_width_elem.text.strip()) if bit_width_elem is not None else None
                        
                        fields.append({
                            'name': field_name,
                            'bit_offset': bit_offset,
                            'bit_width': bit_width
                        })
                
                registers[reg_name] = {
                    'address_offset': address_offset,
                    'reset_value': reset_value,
                    'size': size,
                    'fields': fields
                }
        
        peripherals[peripheral_name] = registers
    
    return peripherals


def parse_agent_output_register(json_path: str) -> Optional[Dict]:
    """
    Parse a single agent output JSON file and return register info in SVD-like format.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            register_data = json.load(f)
    except Exception as e:
        print(f"Error reading {json_path}: {e}")
        return None
    
    # Convert agent output format to SVD-like format
    def bitfield_to_svd_field(field):
        """Convert agent BitField to SVD-like field format."""
        bit_number = field.get('bit_number', {})
        if isinstance(bit_number, dict):
            start = bit_number.get('start_bit', 0)
            end = bit_number.get('end_bit', 0)
            bit_offset = min(start, end)
            bit_width = abs(end - start) + 1
        else:
            bit_offset = None
            bit_width = None
        
        return {
            'name': field.get('name', '').lower(),
            'bit_offset': bit_offset,
            'bit_width': bit_width
        }
    
    fields = []
    for f in register_data.get('subfields', []):
        fields.append(bitfield_to_svd_field(f))
    
    # Convert address_offset and reset_value
    address_offset = register_data.get('address_offset', '')
    # if address_offset:
    #     address_offset = convert_hex_string_to_int(address_offset)
    
    reset_value = register_data.get('reset_value', '')
    # if reset_value:
    #     reset_value = convert_hex_string_to_int(reset_value)
    
    return {
        'address_offset': address_offset,
        'reset_value': reset_value,
        'size': register_data.get('size', None),
        'fields': fields
    }


def parse_agent_output_registers(output_directory: str) -> Dict[str, Dict[str, Dict]]:
    """
    Parse all agent output JSON files from a directory.
    Returns: {peripheral_name: {register_name: {address_offset, reset_value, size, fields: [...]}}}
    """
    peripherals = {}
    
    if not os.path.exists(output_directory):
        print(f"Warning: Output directory does not exist: {output_directory}")
        return peripherals
    
    for filename in os.listdir(output_directory):
        filepath = os.path.join(output_directory, filename)
        if os.path.isdir(filepath):
            continue
        
        # Skip CSV and other non-JSON files
        if filename.endswith('.csv') or filename.startswith('summary') or filename.startswith('usage'):
            continue
        
        # Parse filename: peripheral_register
        if '_' not in filename:
            continue
        
        parts = filename.split('_', 1)
        if len(parts) < 2:
            continue
        
        peripheral_name = parts[0].lower()
        register_name = parts[1].lower()
        
        register = parse_agent_output_register(filepath)
        if register is None:
            continue
        
        if peripheral_name not in peripherals:
            peripherals[peripheral_name] = {}
        peripherals[peripheral_name][register_name] = register
    
    return peripherals

def add_row_to_csv(rows: List[Dict], peripheral: str, register: str, field_name: str, key: str, correct_value: str, svd_value: str, agent_value: str):
    rows.append({
        'peripheral': peripheral,
        'register': register,
        'field_name': field_name,
        'key': key,
        'correct_value': correct_value,
        'svd_value': svd_value,
        'agent_value': agent_value
    })

def add_row_to_digital_datasheet(rows, peripheral_name, register_names, svd_registers, agent_registers):
    for register_name in sorted(register_names):
        if svd_registers is not None:
            svd_register = svd_registers[register_name]
        else:
            svd_register = {}

        if agent_registers is not None:
            agent_register = agent_registers[register_name]
        else:
            agent_register = {}
        
        if len(svd_register) > 0 & len(agent_register) > 0:
            for key in ['address_offset', 'reset_value', 'size']:
                add_row_to_csv(rows, peripheral_name, register_name, '', key, '', format_value(svd_register.get(key)), format_value(agent_register.get(key)))
        
        if len(svd_register) > 0 & len(agent_register) == 0:
            for key in ['address_offset', 'reset_value', 'size']:
                add_row_to_csv(rows, peripheral_name, register_name, '', key, '', format_value(svd_register.get(key)), '') 

        if len(svd_register) == 0 & len(agent_register) > 0:
            for key in ['address_offset', 'reset_value', 'size']:
                add_row_to_csv(rows, peripheral_name, register_name, '', key, '', '', format_value(agent_register.get(key)))

        # Add field-level properties
        svd_fields = {f['name']: f for f in svd_register.get('fields', [])}
        agent_fields = {f['name']: f for f in agent_register.get('fields', [])}
        
        common_fields = set(svd_fields.keys()) & set(agent_fields.keys())
        svd_fields_only = set(svd_fields.keys()) - common_fields
        agent_fields_only = set(agent_fields.keys()) - common_fields
        
        for field_name in sorted(common_fields):
            svd_field = svd_fields[field_name]
            agent_field = agent_fields[field_name]
            add_row_to_csv(rows, peripheral_name, register_name, field_name, 'bit_offset', '', format_value(svd_field.get('bit_offset')), format_value(agent_field.get('bit_offset')))
            add_row_to_csv(rows, peripheral_name, register_name, field_name, 'bit_width', '', format_value(svd_field.get('bit_width')), format_value(agent_field.get('bit_width')))

        for field_name in sorted(svd_fields_only):
            svd_field = svd_fields[field_name]
            add_row_to_csv(rows, peripheral_name, register_name, field_name, 'bit_offset', '', format_value(svd_field.get('bit_offset')), '')
            add_row_to_csv(rows, peripheral_name, register_name, field_name, 'bit_width', '', format_value(svd_field.get('bit_width')), '')

        for field_name in sorted(agent_fields_only):
            agent_field = agent_fields[field_name]
            add_row_to_csv(rows, peripheral_name, register_name, field_name, 'bit_offset', '', '', format_value(agent_field.get('bit_offset')))
            add_row_to_csv(rows, peripheral_name, register_name, field_name, 'bit_width', '', '', format_value(agent_field.get('bit_width')))

    return rows


def create_register_comparison_csv(
    svd_file_paths: List[str],
    agent_output_directory: str,
    output_csv_path: str,
    checked_csv_path: str
):
    """
    Create a CSV file comparing SVD and agent output values.
    
    Args:
        svd_file_paths: List of paths to SVD files
        agent_output_directory: Directory containing agent output JSON files
        output_csv_path: Path where the CSV file will be written
    
    CSV columns: peripheral, register, field_name, key, correct_value, svd_value, agent_value
    """
    # Parse SVD files
    svd_peripherals = {}
    for svd_path in svd_file_paths:
        if not os.path.exists(svd_path):
            print(f"Warning: SVD file not found: {svd_path}")
            continue
        svd_data = parse_svd_registers(svd_path)
        # Merge data from multiple SVD files
        for periph_name, registers in svd_data.items():
            if periph_name not in svd_peripherals:
                svd_peripherals[periph_name] = {}
            svd_peripherals[periph_name].update(registers)
    
    # Parse agent output
    agent_peripherals = parse_agent_output_registers(agent_output_directory)
    
    # Create CSV rows
    rows = []
    
    # Find common peripherals and registers
    common_peripherals = set(svd_peripherals.keys()) & set(agent_peripherals.keys())
    
    for peripheral_name in sorted(common_peripherals):
        svd_registers = svd_peripherals[peripheral_name]
        agent_registers = agent_peripherals[peripheral_name]
        
        common_registers = set(svd_registers.keys()) & set(agent_registers.keys())
        rows = add_row_to_digital_datasheet(rows, peripheral_name, common_registers, svd_registers, agent_registers)

        svd_registers_only = set(svd_registers.keys()) - common_registers
        rows = add_row_to_digital_datasheet(rows, peripheral_name, svd_registers_only, svd_registers, None)
        
        agent_registers_only = set(agent_registers.keys()) - common_registers
        rows = add_row_to_digital_datasheet(rows, peripheral_name, agent_registers_only, None, agent_registers)
        
    if checked_csv_path is not None:
        with open(checked_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Try to find a matching row in 'rows' (already accumulated) based on peripheral, register, field_name, and key
                checked_peripheral = row.get('peripheral', '').strip().lower()
                checked_register = row.get('register', '').strip().lower()
                checked_field_name = row.get('field_name', '').strip().lower()
                checked_key = row.get('key', '').strip()
                checked_correct_value = row.get('correct_value', '')
                for existing_row in rows:
                    existing_peripheral = (existing_row.get('peripheral') or '').strip().lower()
                    existing_register = (existing_row.get('register') or '').strip().lower()
                    existing_field_name = (existing_row.get('field_name') or '').strip().lower()
                    existing_key = (existing_row.get('key') or '').strip()
                    if (existing_peripheral == checked_peripheral and
                        existing_register == checked_register and
                        existing_field_name == checked_field_name and
                        existing_key == checked_key):
                        existing_row['correct_value'] = checked_correct_value
                        break


    # Write CSV file
    fieldnames = ['peripheral', 'register', 'field_name', 'key', 'correct_value', 'svd_value', 'agent_value']
    
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Created CSV file with {len(rows)} rows: {output_csv_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create CSV comparing SVD and agent output')
    parser.add_argument('--svd', nargs='+', required=True, help='Path(s) to SVD file(s)')
    parser.add_argument('--agent-output', required=True, help='Directory containing agent output JSON files')
    parser.add_argument('--output', required=True, help='Output CSV file path')
    parser.add_argument('--checked_csv', required=False, help='Checked CSV file path')
    
    args = parser.parse_args()
    
    create_register_comparison_csv(
        svd_file_paths=args.svd,
        agent_output_directory=args.agent_output,
        output_csv_path=args.output,
        checked_csv_path=args.checked_csv
    )

