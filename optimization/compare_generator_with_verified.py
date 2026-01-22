#!/usr/bin/env python3
"""
Compare generator outputs from different embedding configurations against verified datasheet.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to access project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import csv
from collections import defaultdict
import pandas as pd

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

            # Filter by peripheral if specified
            if peripheral_filter and peripheral != peripheral_filter:
                continue

            # Skip if no correct value
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

def compare_outputs(verified_facts, generator_facts):
    """Compare generator output against verified facts"""
    correct = []
    wrong = []
    missing = []

    for fact_key, correct_value in verified_facts.items():
        if fact_key in generator_facts:
            generated_value = generator_facts[fact_key]

            # Normalize for comparison
            norm_correct = normalize_value(correct_value)
            norm_generated = normalize_value(generated_value)

            if norm_correct == norm_generated:
                correct.append({
                    'fact': fact_key,
                    'value': correct_value
                })
            else:
                wrong.append({
                    'fact': fact_key,
                    'correct': correct_value,
                    'generated': generated_value
                })
        else:
            missing.append({
                'fact': fact_key,
                'correct_value': correct_value
            })

    return correct, wrong, missing

def main():
    # Change to repo root directory
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)

    # Configuration
    verified_csv = "verified_datasheet/stm/rm0041/rm0041_stm32f100_full.csv"
    peripheral = "afio"
    embedding_configs = [4, 8, 16, 50]

    print(f"Comparing generator outputs for peripheral: {peripheral}")
    print(f"Verified datasheet: {verified_csv}\n")

    # Load verified datasheet
    print("Loading verified datasheet...")
    verified_facts = load_verified_datasheet(verified_csv, peripheral_filter=peripheral)
    print(f"Found {len(verified_facts)} verified facts for {peripheral}\n")

    # Get list of registers to check
    registers = set()
    for (p, r, f, k) in verified_facts.keys():
        if p == peripheral:
            registers.add(r)
    registers = sorted(registers)
    print(f"Registers to check: {registers}\n")

    # Compare each embedding configuration
    results = []

    for num_embeddings in embedding_configs:
        output_dir = f"generator_test_embeddings_{num_embeddings}"

        print(f"{'='*80}")
        print(f"ANALYZING: {num_embeddings} embeddings")
        print(f"{'='*80}\n")

        # Collect all facts from this configuration
        all_generator_facts = {}
        registers_found = []

        for register in registers:
            output_json = load_generator_output(output_dir, peripheral, register)
            if output_json:
                registers_found.append(register)
                facts = extract_facts_from_generator_output(output_json, peripheral, register)
                all_generator_facts.update(facts)

        # Compare against verified
        correct, wrong, missing = compare_outputs(verified_facts, all_generator_facts)

        # Calculate metrics
        total_verified = len(verified_facts)
        num_correct = len(correct)
        num_wrong = len(wrong)
        num_missing = len(missing)
        accuracy = (num_correct / total_verified * 100) if total_verified > 0 else 0

        print(f"Registers found: {len(registers_found)}/{len(registers)}")
        print(f"Registers: {registers_found}\n")

        print(f"Results:")
        print(f"  Correct: {num_correct}/{total_verified} ({num_correct/total_verified*100:.1f}%)")
        print(f"  Wrong:   {num_wrong}/{total_verified} ({num_wrong/total_verified*100:.1f}%)")
        print(f"  Missing: {num_missing}/{total_verified} ({num_missing/total_verified*100:.1f}%)")
        print()

        # Show sample wrong predictions
        if wrong:
            print(f"Sample wrong predictions (showing first 5):")
            for i, w in enumerate(wrong[:5]):
                fact = w['fact']
                print(f"  {i+1}. {fact[1]}.{fact[2]}.{fact[3]}: correct={w['correct']}, generated={w['generated']}")
            if len(wrong) > 5:
                print(f"  ... and {len(wrong)-5} more")
            print()

        # Show sample missing facts
        if missing:
            print(f"Sample missing facts (showing first 5):")
            for i, m in enumerate(missing[:5]):
                fact = m['fact']
                print(f"  {i+1}. {fact[1]}.{fact[2]}.{fact[3]}: correct_value={m['correct_value']}")
            if len(missing) > 5:
                print(f"  ... and {len(missing)-5} more")
            print()

        results.append({
            'embeddings': num_embeddings,
            'registers_found': len(registers_found),
            'total_registers': len(registers),
            'correct': num_correct,
            'wrong': num_wrong,
            'missing': num_missing,
            'total': total_verified,
            'accuracy': accuracy
        })

    # Summary table
    print(f"\n{'='*80}")
    print("SUMMARY COMPARISON")
    print(f"{'='*80}\n")

    df = pd.DataFrame(results)
    print("Performance by Embedding Count:")
    print(df.to_string(index=False))
    print()

    # Save results
    output_file = "generator_embedding_comparison.csv"
    df.to_csv(output_file, index=False)
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()
