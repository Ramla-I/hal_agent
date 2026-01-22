#!/usr/bin/env python3
"""
Detailed analysis of generator errors by register and field.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to access project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import csv
from collections import defaultdict

def load_verified_datasheet(csv_path, peripheral_filter=None):
    """Load verified datasheet and return as dict keyed by (peripheral, register, field_name, key)"""
    verified = {}

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            peripheral = row['peripheral']
            register = row['register']
            field_name = row['field_name']
            key = row['key']
            correct_value = row['correct_value']

            if peripheral_filter and peripheral != peripheral_filter:
                continue

            if not correct_value:
                continue

            fact_key = (peripheral, register, field_name, key)
            verified[fact_key] = correct_value

    return verified

def load_generator_output(output_dir, peripheral, register):
    """Load generator output JSON for a specific register"""
    filename = f"{peripheral}_{register}"
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except:
        return None

def extract_facts_from_generator_output(output_json, peripheral, register):
    """Extract facts from generator output in same format as verified datasheet"""
    facts = {}

    if not output_json:
        return facts

    # Register-level facts
    for key in ['address_offset', 'reset_value', 'size']:
        if key in output_json:
            fact_key = (peripheral, register, '', key)
            facts[fact_key] = str(output_json[key])

    # Field-level facts (handle both 'subfields' and 'fields' key)
    fields_list = output_json.get('subfields', output_json.get('fields', []))

    for field in fields_list:
        # Get field name (handle both 'name' and 'field_name')
        field_name = field.get('name', field.get('field_name', '')).lower()

        # Access
        if 'access' in field:
            fact_key = (peripheral, register, field_name, 'access')
            facts[fact_key] = str(field['access'])

        # Bit offset and width (handle both formats)
        if 'bit_number' in field:
            # New format with start_bit/end_bit
            bit_info = field['bit_number']
            if 'start_bit' in bit_info and 'end_bit' in bit_info:
                # Ensure start_bit is the smaller value, end_bit is the larger
                start_bit = min(bit_info['start_bit'], bit_info['end_bit'])
                end_bit = max(bit_info['start_bit'], bit_info['end_bit'])

                # bit_offset is the smaller value (start_bit)
                fact_key = (peripheral, register, field_name, 'bit_offset')
                facts[fact_key] = str(start_bit)

                # bit_width is the difference + 1
                bit_width = end_bit - start_bit + 1
                fact_key = (peripheral, register, field_name, 'bit_width')
                facts[fact_key] = str(bit_width)
        else:
            # Old format with direct bit_offset/bit_width
            if 'bit_offset' in field:
                fact_key = (peripheral, register, field_name, 'bit_offset')
                facts[fact_key] = str(field['bit_offset'])

            if 'bit_width' in field:
                fact_key = (peripheral, register, field_name, 'bit_width')
                facts[fact_key] = str(field['bit_width'])

    return facts

def normalize_value(value):
    """Normalize values for comparison"""
    if not value:
        return None

    value = str(value).strip().lower()

    # Normalize hex values
    if value.startswith('0x'):
        try:
            return hex(int(value, 16))
        except:
            pass

    return value

def analyze_by_register(verified_facts, output_dir, peripheral, registers, num_embeddings):
    """Analyze results broken down by register"""
    print(f"\n{'='*80}")
    print(f"DETAILED ANALYSIS - {num_embeddings} embeddings")
    print(f"{'='*80}\n")

    register_stats = []

    for register in registers:
        output_json = load_generator_output(output_dir, peripheral, register)

        # Count verified facts for this register
        register_facts = {k: v for k, v in verified_facts.items() if k[1] == register}
        total = len(register_facts)

        if not output_json:
            print(f"{register}: MISSING OUTPUT FILE (0/{total} facts)")
            register_stats.append({
                'register': register,
                'found': 'NO',
                'correct': 0,
                'wrong': 0,
                'missing': total,
                'total': total
            })
            continue

        # Extract facts from generator
        generator_facts = extract_facts_from_generator_output(output_json, peripheral, register)

        # Compare
        correct = 0
        wrong = 0
        wrong_details = []

        for fact_key, correct_value in register_facts.items():
            if fact_key in generator_facts:
                generated_value = generator_facts[fact_key]
                norm_correct = normalize_value(correct_value)
                norm_generated = normalize_value(generated_value)

                if norm_correct == norm_generated:
                    correct += 1
                else:
                    wrong += 1
                    wrong_details.append({
                        'field': fact_key[2],
                        'key': fact_key[3],
                        'correct': correct_value,
                        'generated': generated_value
                    })

        missing = total - correct - wrong

        print(f"{register}: {correct}/{total} correct, {wrong} wrong, {missing} missing")

        if wrong_details:
            print(f"  Wrong predictions:")
            for w in wrong_details:
                field_str = f"{w['field']}.{w['key']}" if w['field'] else w['key']
                print(f"    {field_str}: correct={w['correct']}, generated={w['generated']}")

        register_stats.append({
            'register': register,
            'found': 'YES',
            'correct': correct,
            'wrong': wrong,
            'missing': missing,
            'total': total
        })

    return register_stats

def main():
    # Change to repo root directory
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)

    # Configuration
    verified_csv = "verified_datasheet/stm/rm0041/rm0041_stm32f100_full.csv"
    peripheral = "afio"
    embedding_configs = [4, 8, 16, 50]

    print(f"Detailed analysis for peripheral: {peripheral}")

    # Load verified datasheet
    verified_facts = load_verified_datasheet(verified_csv, peripheral_filter=peripheral)

    # Get list of registers
    registers = set()
    for (p, r, f, k) in verified_facts.keys():
        if p == peripheral:
            registers.add(r)
    registers = sorted(registers)

    # Analyze each configuration
    all_stats = {}

    for num_embeddings in embedding_configs:
        output_dir = f"generator_test_embeddings_{num_embeddings}"
        stats = analyze_by_register(verified_facts, output_dir, peripheral, registers, num_embeddings)
        all_stats[num_embeddings] = stats

    # Summary comparison across embeddings
    print(f"\n\n{'='*80}")
    print("REGISTER-LEVEL COMPARISON ACROSS EMBEDDINGS")
    print(f"{'='*80}\n")

    print(f"{'Register':<15} {'4 emb':<15} {'8 emb':<15} {'16 emb':<15} {'50 emb':<15}")
    print("-" * 80)

    for register in registers:
        row = f"{register:<15}"
        for num_emb in embedding_configs:
            stats = next((s for s in all_stats[num_emb] if s['register'] == register), None)
            if stats:
                if stats['found'] == 'NO':
                    cell = "MISSING"
                else:
                    pct = f"{stats['correct']/stats['total']*100:.0f}%"
                    wrong_marker = f"*{stats['wrong']}w" if stats['wrong'] > 0 else ""
                    cell = f"{stats['correct']}/{stats['total']} {pct}{wrong_marker}"
                row += f" {cell:<15}"
        print(row)

    print("\n*Nw = N wrong predictions")

if __name__ == "__main__":
    main()
