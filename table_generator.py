#!/usr/bin/env python3
"""
Script to generate a table with ID and calculated values.
Column 1: ID (0 to 50)
Column 2: 0x00F8 + (4 * ID)
"""

start_id = 11
end_id = 20
start_value = 0x40

def generate_table():
    """Generate and print the table with ID and calculated values."""
    print("ID\tValue (Hex)")
    print("-" * 20)
    
    for id_val in range(start_id, end_id):  # 0 to 50 inclusive
        # Calculate 0x00F8 + (4 * id)
        # 0x00F8 = 248 in decimal

        value = start_value + (4 * (id_val - start_id))
        print(f"{id_val}\t0x{value:04X}")

if __name__ == "__main__":
    generate_table()
