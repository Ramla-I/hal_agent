import sys
import os
from pathlib import Path

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config.py')
DEVICES_PATH = os.path.join(os.path.dirname(__file__), '..', 'devices')

MANUFACTURER_MAP = {
    'rm': 'Manufacturer.STM',
    'stm': 'Manufacturer.STM',
    '82': 'Manufacturer.INTEL',
}

def get_manufacturer(device_name):
    for prefix, manufacturer in MANUFACTURER_MAP.items():
        if device_name.startswith(prefix):
            return manufacturer
    return 'Manufacturer.STM'  # default

def main():
    if len(sys.argv) < 2:
        print('Usage: python update_config.py <device_name>')
        sys.exit(1)
    device_name = sys.argv[1]
    device_dir = os.path.join(DEVICES_PATH, device_name)
    if not os.path.isdir(device_dir):
        print(f'Device folder not found: {device_dir}')
        sys.exit(1)
    # Find datasheet PDF
    pdfs = [f for f in os.listdir(device_dir) if f.endswith('.pdf')]
    if not pdfs:
        print('No datasheet PDF found.')
        sys.exit(1)
    datasheet_path = f'devices/{device_name}/{pdfs[0]}'
    # Find SVD files
    svds = [f for f in os.listdir(device_dir) if f.endswith('.svd')]
    svd_paths = [f'devices/{device_name}/{svd}' for svd in svds]
    # Prepare UserContext string
    manufacturer = get_manufacturer(device_name)
    user_context = f"    UserContext(device_name='{device_name}', peripheral_name='', manufacturer={manufacturer}, driver_path='', datasheet_path='{datasheet_path}', datasheet_sections_directory='', svd_path={svd_paths}, run=0, file_id='', vs_id=''),\n"
    # Insert before closing bracket in config.py
    with open(CONFIG_PATH, 'r') as f:
        lines = f.readlines()
    for i in range(len(lines)-1, -1, -1):
        if lines[i].strip() == ']':
            insert_idx = i
            break
    else:
        print('Could not find user_contexts list in config.py')
        sys.exit(1)
    lines.insert(insert_idx, user_context)
    with open(CONFIG_PATH, 'w') as f:
        f.writelines(lines)
    print(f'Added UserContext for {device_name} to config.py')

if __name__ == '__main__':
    main()
