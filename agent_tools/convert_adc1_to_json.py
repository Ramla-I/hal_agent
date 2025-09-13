import ast
import json
import re

INPUT_PATH = "/Users/ramla/Projects/hal_agent/output/rm0041/1/ADC1"
OUTPUT_PATH = "/Users/ramla/Projects/hal_agent/output/rm0041/1/ADC1.json"

# Read the file
with open(INPUT_PATH, "r") as f:
    content = f.read().strip()

# Remove the 'registers=' prefix
if content.startswith("registers="):
    content = content[len("registers="):]

# Replace class constructors with dicts for ast.literal_eval
# e.g., RegisterInfo(...) -> {'RegisterInfo': {...}}
# We'll use regex to replace RegisterInfo( with dict(
# and then later convert dicts with a single key to just their value

# Replace class names with dict(
content = re.sub(r"(RegisterInfo|BitNumber|BitField)\\(", r"dict(type='\1', ", content)

# Replace list brackets for empty lists (no change needed)

# Now, safely evaluate to Python objects
try:
    registers = ast.literal_eval(content)
except Exception as e:
    print(f"Failed to parse content: {e}")
    exit(1)

def convert(obj):
    if isinstance(obj, dict):
        t = obj.get('type')
        if t == 'RegisterInfo':
            return {
                'datasheet_register_abbreviation': convert(obj['datasheet_register_abbreviation']),
                'address_offset': convert(obj['address_offset']),
                'reset_value': convert(obj['reset_value']),
                'size': convert(obj['size']),
                'readonly_bits': [convert(x) for x in obj['readonly_bits']],
                'write_only_bits': [convert(x) for x in obj['write_only_bits']],
                'read_write_bits': [convert(x) for x in obj['read_write_bits']],
                'subfields': [convert(x) for x in obj['subfields']],
            }
        elif t == 'BitNumber':
            return {
                'start_bit': convert(obj['start_bit']),
                'end_bit': convert(obj['end_bit'])
            }
        elif t == 'BitField':
            return {
                'name': convert(obj['name']),
                'description': convert(obj['description']),
                'bit_number': convert(obj['bit_number']),
                'enumerated_values': [convert(x) for x in obj['enumerated_values']],
            }
        else:
            # Remove 'type' and convert rest
            return {k: convert(v) for k, v in obj.items() if k != 'type'}
    elif isinstance(obj, list):
        return [convert(x) for x in obj]
    else:
        return obj

json_data = convert(registers)

with open(OUTPUT_PATH, "w") as f:
    json.dump(json_data, f, indent=2)

print(f"Converted to JSON and saved to {OUTPUT_PATH}")
