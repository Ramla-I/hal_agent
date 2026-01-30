#!/usr/bin/env python3
"""
Compare generator outputs from different embedding configurations against verified datasheet.

Usage:
    python3 optimization/compare_generator_with_verified.py -v VERIFIED_CSV GENERATOR_DIR [GENERATOR_DIR ...]

Examples:
    # Compare single generator run
    python3 optimization/compare_generator_with_verified.py \\
        -v verified_datasheet/stm/rm0041/rm0041_stm32f100_full.csv \\
        agent_output/stm/rm0041/run_1/

    # Compare multiple runs
    python3 optimization/compare_generator_with_verified.py \\
        -v verified_datasheet/stm/rm0041/rm0041_stm32f100_full.csv \\
        agent_output/stm/rm0041/run_1/ agent_output/stm/rm0041/run_2/

    # Filter by peripheral
    python3 optimization/compare_generator_with_verified.py \\
        -v verified_datasheet/stm/rm0041/rm0041_stm32f100_full.csv \\
        -p afio agent_output/stm/rm0041/run_1/
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to access project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
import csv
import re
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

def normalize_register(name):
    """Normalize register names for exact comparison (case-insensitive)."""
    if name is None:
        return ''
    return str(name).strip().lower()


def normalize_name(name):
    """Normalize field names for fuzzy comparison."""
    if name is None:
        return ''
    cleaned = str(name).strip().lower()
    # Remove bit-range suffixes like [3:0] or [7]
    cleaned = re.sub(r"\[[0-9:]+\]", "", cleaned)
    return ''.join(ch for ch in cleaned if ch.isalnum())


def match_name_score(left, right):
    """Score name match: 3 exact, 2 prefix/suffix, 1 substring, 0 no match."""
    if not left or not right:
        return 0
    if left == right:
        return 3
    if left.startswith(right) or right.startswith(left):
        return 2
    if left.endswith(right) or right.endswith(left):
        return 2
    # Allow partial substring match as a fallback
    if left in right or right in left:
        if min(len(left), len(right)) >= 4:
            return 1
    return 0


def build_generator_index(generator_facts):
    """Index generator facts for fuzzy lookup by (peripheral, key, register)."""
    index = defaultdict(list)
    for (peripheral, register, field_name, key), value in generator_facts.items():
        norm_register = normalize_register(register)
        index[(peripheral, key, norm_register)].append({
            'fact_key': (peripheral, register, field_name, key),
            'register': register,
            'field_name': field_name,
            'value': value,
            'norm_register': norm_register,
            'norm_field_name': normalize_name(field_name),
        })
    return index


def build_generator_exact_map(generator_facts):
    """Exact lookup by normalized register and field names."""
    exact_map = {}
    for (peripheral, register, field_name, key), value in generator_facts.items():
        norm_register = normalize_register(register)
        norm_field = normalize_name(field_name)
        exact_map[(peripheral, norm_register, norm_field, key)] = {
            'fact_key': (peripheral, register, field_name, key),
            'value': value,
        }
    return exact_map


def find_fuzzy_generator_fact(peripheral, register, field_name, key, generator_index, used_fact_keys):
    """Find best fuzzy match for a verified fact in generator output."""
    norm_register = normalize_register(register)
    candidates = generator_index.get((peripheral, key, norm_register), [])
    if not candidates:
        return None

    norm_field = normalize_name(field_name)
    is_register_level = field_name == ''

    best = None
    best_score = 0
    for candidate in candidates:
        if candidate['fact_key'] in used_fact_keys:
            continue

        if is_register_level:
            continue
        else:
            field_score = match_name_score(candidate['norm_field_name'], norm_field)

        if field_score > best_score:
            best_score = field_score
            best = candidate

    return best


def compare_outputs(verified_facts, generator_facts, registers_found):
    """Compare generator output against verified facts.

    Only compares facts for registers that are present in the generator output.

    Args:
        verified_facts: Dict of verified facts keyed by (peripheral, register, field_name, key)
        generator_facts: Dict of generator facts keyed by (peripheral, register, field_name, key)
        registers_found: Set of (peripheral, register) tuples that were found in generator output

    Returns:
        Tuple of (correct, wrong, missing) lists
    """
    correct = []
    wrong = []
    missing = []

    generator_index = build_generator_index(generator_facts)
    generator_exact_map = build_generator_exact_map(generator_facts)
    used_fact_keys = set()
    pending = []

    for fact_key, correct_value in verified_facts.items():
        peripheral, register, field_name, key = fact_key

        # Only consider facts for registers that are present in the generator output
        if (peripheral, register) not in registers_found:
            continue

        norm_register = normalize_register(register)
        norm_field = normalize_name(field_name)
        exact_match = generator_exact_map.get((peripheral, norm_register, norm_field, key))
        if exact_match:
            used_fact_keys.add(exact_match['fact_key'])
            generated_value = exact_match['value']
        else:
            pending.append((fact_key, correct_value))
            continue

        if generated_value is not None:

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

    for fact_key, correct_value in pending:
        peripheral, register, field_name, key = fact_key
        fuzzy_match = find_fuzzy_generator_fact(
            peripheral,
            register,
            field_name,
            key,
            generator_index,
            used_fact_keys,
        )
        generated_value = fuzzy_match['value'] if fuzzy_match else None
        if fuzzy_match:
            used_fact_keys.add(fuzzy_match['fact_key'])

        if generated_value is not None:
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


def save_errors_to_csv(wrong, missing, output_dir, dir_name):
    """Save wrong and missing facts to CSV files.

    Args:
        wrong: List of wrong facts with 'fact', 'correct', 'generated' keys
        missing: List of missing facts with 'fact', 'correct_value' keys
        output_dir: Directory to save the CSV files
        dir_name: Name of the generator directory (used in filename)
    """
    os.makedirs(output_dir, exist_ok=True)

    # Save wrong facts
    if wrong:
        wrong_file = os.path.join(output_dir, f"{dir_name}_wrong.csv")
        with open(wrong_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['peripheral', 'register', 'field_name', 'key', 'correct_value', 'generated_value'])
            for w in wrong:
                fact = w['fact']
                writer.writerow([fact[0], fact[1], fact[2], fact[3], w['correct'], w['generated']])
        print(f"  Saved wrong facts to: {wrong_file}")

    # Save missing facts
    if missing:
        missing_file = os.path.join(output_dir, f"{dir_name}_missing.csv")
        with open(missing_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['peripheral', 'register', 'field_name', 'key', 'correct_value'])
            for m in missing:
                fact = m['fact']
                writer.writerow([fact[0], fact[1], fact[2], fact[3], m['correct_value']])
        print(f"  Saved missing facts to: {missing_file}")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare generator outputs against verified datasheet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Compare single generator run
    python3 %(prog)s -v verified.csv agent_output/run_1/

    # Compare multiple runs
    python3 %(prog)s -v verified.csv run_1/ run_2/ run_3/

    # Filter by peripheral
    python3 %(prog)s -v verified.csv -p afio agent_output/run_1/

    # Save results to specific file
    python3 %(prog)s -v verified.csv -o results.csv run_1/ run_2/
        """
    )
    parser.add_argument(
        "-v", "--verified",
        required=True,
        help="Path to verified datasheet CSV file"
    )
    parser.add_argument(
        "generator_dirs",
        nargs="+",
        help="One or more generator output directories to compare"
    )
    parser.add_argument(
        "-p", "--peripheral",
        default=None,
        help="Filter by peripheral name (default: all peripherals)"
    )
    parser.add_argument(
        "-o", "--output",
        default="generator_comparison.csv",
        help="Output CSV file for summary results (default: generator_comparison.csv)"
    )
    parser.add_argument(
        "-e", "--errors-dir",
        default=None,
        help="Directory to save detailed wrong/missing facts CSVs (default: same directory as --output)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Validate inputs
    if not os.path.exists(args.verified):
        print(f"Error: Verified datasheet not found: {args.verified}")
        sys.exit(1)

    for gen_dir in args.generator_dirs:
        if not os.path.isdir(gen_dir):
            print(f"Error: Generator directory not found: {gen_dir}")
            sys.exit(1)

    # Determine errors output directory
    errors_dir = args.errors_dir if args.errors_dir else os.path.dirname(args.output) or "."

    peripheral_filter = args.peripheral
    peripheral_desc = peripheral_filter if peripheral_filter else "all peripherals"

    print(f"Comparing generator outputs for: {peripheral_desc}")
    print(f"Verified datasheet: {args.verified}")
    print(f"Generator directories: {args.generator_dirs}")
    print(f"Errors output directory: {errors_dir}\n")

    # Load verified datasheet
    print("Loading verified datasheet...")
    verified_facts = load_verified_datasheet(args.verified, peripheral_filter=peripheral_filter)
    print(f"Found {len(verified_facts)} verified facts\n")

    # Get list of (peripheral, register) pairs to check
    register_pairs = set()
    for (p, r, f, k) in verified_facts.keys():
        register_pairs.add((p, r))
    register_pairs = sorted(register_pairs)
    print(f"Register pairs to check: {len(register_pairs)}\n")

    # Compare each generator directory
    results = []

    for output_dir in args.generator_dirs:
        dir_name = os.path.basename(os.path.normpath(output_dir))

        print(f"{'='*80}")
        print(f"ANALYZING: {dir_name}")
        print(f"{'='*80}\n")

        # Collect all facts from this configuration
        all_generator_facts = {}
        registers_found = set()

        for peripheral, register in register_pairs:
            output_json = load_generator_output(output_dir, peripheral, register)
            if output_json:
                registers_found.add((peripheral, register))
                facts = extract_facts_from_generator_output(output_json, peripheral, register)
                all_generator_facts.update(facts)

        # Compare against verified (only for registers that are present)
        correct, wrong, missing = compare_outputs(verified_facts, all_generator_facts, registers_found)

        # Calculate metrics (for registers that are present)
        total_facts_for_present_registers = len(correct) + len(wrong) + len(missing)
        num_correct = len(correct)
        num_wrong = len(wrong)
        num_missing = len(missing)
        accuracy = (num_correct / total_facts_for_present_registers * 100) if total_facts_for_present_registers > 0 else 0

        print(f"Registers found: {len(registers_found)}/{len(register_pairs)}")
        if len(registers_found) <= 10:
            print(f"Registers: {sorted(registers_found)}\n")
        else:
            print()

        print(f"Results (for {len(registers_found)} present registers, {total_facts_for_present_registers} facts):")
        print(f"  Correct: {num_correct}/{total_facts_for_present_registers} ({num_correct/total_facts_for_present_registers*100:.1f}%)" if total_facts_for_present_registers > 0 else "  Correct: 0")
        print(f"  Wrong:   {num_wrong}/{total_facts_for_present_registers} ({num_wrong/total_facts_for_present_registers*100:.1f}%)" if total_facts_for_present_registers > 0 else "  Wrong: 0")
        print(f"  Missing: {num_missing}/{total_facts_for_present_registers} ({num_missing/total_facts_for_present_registers*100:.1f}%)" if total_facts_for_present_registers > 0 else "  Missing: 0")
        print()

        # Show sample wrong predictions
        if wrong:
            print(f"Sample wrong predictions (showing first 5):")
            for i, w in enumerate(wrong[:5]):
                fact = w['fact']
                print(f"  {i+1}. {fact[0]}.{fact[1]}.{fact[2]}.{fact[3]}: correct={w['correct']}, generated={w['generated']}")
            if len(wrong) > 5:
                print(f"  ... and {len(wrong)-5} more")
            print()

        # Show sample missing facts
        if missing:
            print(f"Sample missing facts (showing first 5):")
            for i, m in enumerate(missing[:5]):
                fact = m['fact']
                print(f"  {i+1}. {fact[0]}.{fact[1]}.{fact[2]}.{fact[3]}: correct_value={m['correct_value']}")
            if len(missing) > 5:
                print(f"  ... and {len(missing)-5} more")
            print()

        # Save detailed wrong and missing facts to CSV
        save_errors_to_csv(wrong, missing, errors_dir, dir_name)
        print()

        results.append({
            'directory': dir_name,
            'registers_found': len(registers_found),
            'total_registers': len(register_pairs),
            'correct': num_correct,
            'wrong': num_wrong,
            'missing': num_missing,
            'total_facts': total_facts_for_present_registers,
            'accuracy': accuracy
        })

    # Summary table
    print(f"\n{'='*80}")
    print("SUMMARY COMPARISON")
    print(f"{'='*80}\n")

    df = pd.DataFrame(results)
    print("Performance by Generator Directory:")
    print(df.to_string(index=False))
    print()

    # Save results
    df.to_csv(args.output, index=False)
    print(f"Results saved to: {args.output}")

if __name__ == "__main__":
    main()
