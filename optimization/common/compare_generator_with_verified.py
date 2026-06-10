#!/usr/bin/env python3
"""
Compare generator outputs from different embedding configurations against verified datasheet.

Usage:
    python3 optimization/common/compare_generator_with_verified.py -v VERIFIED_CSV GENERATOR_DIR [GENERATOR_DIR ...]

Examples:
    # Compare single generator run
    python3 optimization/common/compare_generator_with_verified.py \\
        -v verified_datasheet/stm/rm0041_stm32f100.csv \\
        agent_output/stm/rm0041/run_1/

    # Compare multiple runs
    python3 optimization/common/compare_generator_with_verified.py \\
        -v verified_datasheet/stm/rm0041_stm32f100.csv \\
        agent_output/stm/rm0041/run_1/ agent_output/stm/rm0041/run_2/

    # Filter by peripheral
    python3 optimization/common/compare_generator_with_verified.py \\
        -v verified_datasheet/stm/rm0041_stm32f100.csv \\
        -p afio agent_output/stm/rm0041/run_1/
"""
import os
import sys
from pathlib import Path

# Add project root to path (file lives at optimization/common/X.py)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
import json
import csv
import re
from collections import defaultdict
import pandas as pd

from utils.generator_facts import extract_facts_from_generator_output

def _format_fact_key(fact):
    return f"{fact[0]}.{fact[1]}.{fact[2]}.{fact[3]}"

def load_verified_datasheet(csv_path, peripheral_filter=None):
    """
    Load the verified datasheet CSV into a fact dict.

    Assumptions about input:
    - CSV has columns: `peripheral`, `register`, `field_name`, `key`, `correct_value`
    - Rows with empty `correct_value` are ignored.
    - `field_name == ""` represents register-level facts.

    Args:
        csv_path: Path to verified CSV file.
        peripheral_filter: If provided, only keep rows where `peripheral == peripheral_filter`.

    Returns:
        Dict mapping `(peripheral, register, field_name, key)` -> `correct_value` (as read from CSV).
    """
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
    """
    Load a generator output JSON for a given peripheral/register.

    Assumptions about input:
    - Generator outputs are stored as files named exactly `<peripheral>_<register>` (no extension).
    - File contents are JSON-encoded register objects.

    Args:
        output_dir: Directory containing generator outputs.
        peripheral: Peripheral name used in filename prefix.
        register: Register name used in filename suffix.

    Returns:
        Parsed JSON object (dict) on success, or `None` if file missing/unreadable/invalid JSON.
    """
    filename = f"{peripheral}_{register}"
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except:
        return None

def normalize_value(value):
    """
    Normalize values for string comparison.

    Assumptions about input:
    - Values may be ints, strings, or other JSON-serializable types.
    - Hex strings may appear as `"0x..."`.

    Returns:
        Lowercased/trimmed string, with hex strings normalized to canonical `hex(int(...))` when possible.
    """
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
    """
    Normalize register names for exact matching (case-insensitive).

    Returns:
        Lowercased, trimmed string. (No fuzzy logic for registers in comparisons.)
    """
    if name is None:
        return ''
    return str(name).strip().lower()


def normalize_name(name):
    """
    Normalize subfield names for matching.

    Assumptions about input:
    - Names may include bit-range suffixes like `port[3:0]`.
    - Names may include separators/underscores; those are removed for matching robustness.

    Returns:
        Lowercased alphanumeric-only string with bracketed bit-ranges removed.
        Example: `"PORT[3:0]" -> "port"`.
    """
    if name is None:
        return ''
    cleaned = str(name).strip().lower()
    # Remove bit-range suffixes like [3:0] or [7]
    cleaned = re.sub(r"\[[0-9:]+\]", "", cleaned)
    return ''.join(ch for ch in cleaned if ch.isalnum())


def match_name_score(left, right):
    """
    Score two normalized names for fuzzy matching.

    Assumptions:
    - Inputs are already normalized (typically via `normalize_name()`).
    - This is used for **subfield** matching only; registers are matched exactly elsewhere.

    Returns:
        Integer score:
        - 3: exact match
        - 2: prefix/suffix match (one side contains the other at the ends)
        - 1: substring match (guarded by min length >= 4)
        - 0: no match
    """
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
    """
    Build an index of generator facts for fuzzy subfield lookup.

    Assumptions about input:
    - `generator_facts` keys are `(peripheral, register, field_name, key)` tuples.

    Returns:
        Dict keyed by `(peripheral, key, norm_register)` with values as candidate dicts:
        `{fact_key, register, field_name, value, norm_register, norm_field_name}`.
    """
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
    """
    Build an exact lookup map for generator facts using normalized names.

    Assumptions:
    - Register matching is exact on `normalize_register(register)`.
    - Subfield matching is exact on `normalize_name(field_name)` in the first pass.

    Returns:
        Dict keyed by `(peripheral, norm_register, norm_field, key)` -> `{fact_key, value}`.
    """
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
    """
    Find the best unused fuzzy match for a verified **subfield-level** fact.

    Assumptions:
    - Register names must match exactly (case-insensitive) via `normalize_register()`.
      Fuzzy matching never crosses registers.
    - Only subfield-level facts (`field_name != ""`) are eligible for fuzzy matching.
    - `used_fact_keys` prevents a generator fact from being matched to multiple verified facts.

    Args:
        peripheral/register/field_name/key: Components of the verified fact key tuple.
        generator_index: Output of `build_generator_index()`.
        used_fact_keys: Set of generator fact keys already consumed by exact/fuzzy matches.

    Returns:
        Candidate dict from the generator index (includes `value` and `fact_key`), or `None`.
    """
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

    Matching policy:
    - Registers are compared only when `(peripheral, register)` is in `registers_found`.
    - Register names are treated as exact (no fuzzy matching across registers).
    - Subfields use a two-pass strategy:
      - Pass 1: exact match on normalized subfield name (`normalize_name`), reserving matched facts.
      - Pass 2: fuzzy match remaining subfields (prefix/suffix/substring), without stealing reserved facts.

    Args:
        verified_facts: Dict of verified facts keyed by (peripheral, register, field_name, key)
        generator_facts: Dict of generator facts keyed by (peripheral, register, field_name, key)
        registers_found: Set of (peripheral, register) tuples that were found in generator output

    Returns:
        Tuple `(correct, wrong, missing)` where each is a list of dicts:
        - correct: `{fact, value}`
        - wrong: `{fact, correct, generated}`
        - missing: `{fact, correct_value}`
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

    # Save missing facts
    if missing:
        missing_file = os.path.join(output_dir, f"{dir_name}_missing.csv")
        with open(missing_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['peripheral', 'register', 'field_name', 'key', 'correct_value'])
            for m in missing:
                fact = m['fact']
                writer.writerow([fact[0], fact[1], fact[2], fact[3], m['correct_value']])
    return {
        'wrong_csv': wrong_file if wrong else None,
        'missing_csv': missing_file if missing else None,
    }

def parse_args():
    """
    Parse CLI arguments.

    Returns:
        argparse.Namespace with:
        - verified: path to verified CSV
        - generator_dirs: list of generator directories
        - parent_dirs: optional list of parent dirs to expand into generator_dirs
        - peripheral: optional peripheral filter
        - output: summary CSV filename (written under `analysis/`)
        - errors_dir: optional override for detailed error CSV directory
    """
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
        "--parent-dirs",
        nargs="*",
        default=[],
        help="Parent directories containing generator output subdirectories"
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
    """
    Entry point.

    Reads the verified CSV, loads generator outputs, extracts facts, compares outputs,
    prints metrics, and writes summary + per-run wrong/missing CSVs under `analysis/`.
    """
    args = parse_args()

    # Validate inputs
    if not os.path.exists(args.verified):
        print(f"Error: Verified datasheet not found: {args.verified}")
        sys.exit(1)

    # Expand parent directories into generator directories
    generator_dirs = list(args.generator_dirs)
    for parent_dir in args.parent_dirs:
        if not os.path.isdir(parent_dir):
            print(f"Error: Parent directory not found: {parent_dir}")
            sys.exit(1)
        for entry in sorted(os.listdir(parent_dir)):
            if entry == "analysis":
                continue
            full_path = os.path.join(parent_dir, entry)
            if os.path.isdir(full_path):
                generator_dirs.append(full_path)

    if not generator_dirs:
        print("Error: No generator directories provided.")
        sys.exit(1)

    for gen_dir in generator_dirs:
        if not os.path.isdir(gen_dir):
            print(f"Error: Generator directory not found: {gen_dir}")
            sys.exit(1)

    # Determine analysis output directory and output file path
    output_base_dir = os.path.dirname(args.output) or "."
    analysis_dir = os.path.join(output_base_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)

    output_filename = os.path.basename(args.output)
    output_path = os.path.join(analysis_dir, output_filename)

    # Determine errors output directory
    errors_dir = args.errors_dir if args.errors_dir else analysis_dir

    peripheral_filter = args.peripheral
    peripheral_desc = peripheral_filter if peripheral_filter else "all peripherals"

    # Console should stay quiet; only print startup info.
    print(f"Started comparison for {peripheral_desc}. Writing outputs under: {analysis_dir}")

    # Compact outputs:
    # - One summary CSV (per generator directory)
    # - One register-level CSV (per generator directory, per register)
    # - One fact-level error CSV (wrong + missing facts)
    output_stem = Path(output_filename).stem
    register_results_path = os.path.join(analysis_dir, f"{output_stem}_register_results.csv")
    fact_errors_path = os.path.join(analysis_dir, f"{output_stem}_fact_errors.csv")

    # Load verified datasheet
    verified_facts = load_verified_datasheet(args.verified, peripheral_filter=peripheral_filter)

    # Get list of (peripheral, register) pairs to check
    register_pairs = set()
    for (p, r, f, k) in verified_facts.keys():
        register_pairs.add((p, r))
    register_pairs = sorted(register_pairs)

    # Compare each generator directory
    results = []
    all_register_rows = []
    all_error_rows = []

    for output_dir in generator_dirs:
        dir_name = os.path.basename(os.path.normpath(output_dir))

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

        # Compare against verified (all registers in verified datasheet)
        all_registers_set = set(register_pairs)
        correct_all, wrong_all, missing_all = compare_outputs(
            verified_facts,
            all_generator_facts,
            all_registers_set,
        )

        # Calculate metrics (for registers that are present)
        total_facts_for_present_registers = len(correct) + len(wrong) + len(missing)
        num_correct = len(correct)
        num_wrong = len(wrong)
        num_missing = len(missing)
        accuracy = (num_correct / total_facts_for_present_registers * 100) if total_facts_for_present_registers > 0 else 0

        # Calculate metrics (for all registers)
        total_facts_all_registers = len(correct_all) + len(wrong_all) + len(missing_all)
        num_correct_all = len(correct_all)
        num_wrong_all = len(wrong_all)
        num_missing_all = len(missing_all)
        accuracy_all = (num_correct_all / total_facts_all_registers * 100) if total_facts_all_registers > 0 else 0

        # Per-register breakdown (one row per verified register)
        for peripheral, register in register_pairs:
            verified_reg_facts = {
                k: v for k, v in verified_facts.items()
                if k[0] == peripheral and k[1] == register
            }
            total_verified_reg_facts = len(verified_reg_facts)
            found = (peripheral, register) in registers_found

            if found:
                c_r, w_r, m_r = compare_outputs(
                    verified_reg_facts,
                    all_generator_facts,
                    {(peripheral, register)},
                )
                correct_r = len(c_r)
                wrong_r = len(w_r)
                missing_r = len(m_r)
            else:
                correct_r = 0
                wrong_r = 0
                missing_r = total_verified_reg_facts

            total_r = correct_r + wrong_r + missing_r
            acc_r = (correct_r / total_r * 100) if total_r > 0 else 0

            all_register_rows.append({
                "generator_directory": dir_name,
                "peripheral": peripheral,
                "register": register,
                "register_found": found,
                "correct": correct_r,
                "wrong": wrong_r,
                "missing": missing_r,
                "total_facts": total_r,
                "accuracy": acc_r,
            })

            # Fact-level errors for this register
            if found:
                for w_item in w_r:
                    fact = w_item["fact"]
                    all_error_rows.append({
                        "generator_directory": dir_name,
                        "error_type": "wrong",
                        "peripheral": fact[0],
                        "register": fact[1],
                        "field_name": fact[2],
                        "key": fact[3],
                        "correct_value": w_item["correct"],
                        "generated_value": w_item["generated"],
                    })
                for m_item in m_r:
                    fact = m_item["fact"]
                    all_error_rows.append({
                        "generator_directory": dir_name,
                        "error_type": "missing",
                        "peripheral": fact[0],
                        "register": fact[1],
                        "field_name": fact[2],
                        "key": fact[3],
                        "correct_value": m_item["correct_value"],
                        "generated_value": "",
                    })
            else:
                # If the register output is missing entirely, mark all its verified facts as missing.
                for fact_key, correct_value in verified_reg_facts.items():
                    all_error_rows.append({
                        "generator_directory": dir_name,
                        "error_type": "missing",
                        "peripheral": fact_key[0],
                        "register": fact_key[1],
                        "field_name": fact_key[2],
                        "key": fact_key[3],
                        "correct_value": correct_value,
                        "generated_value": "",
                    })

        # Coverage: what fraction of total facts come from found registers
        coverage = (total_facts_for_present_registers / total_facts_all_registers * 100) if total_facts_all_registers > 0 else 0

        results.append({
            'directory': dir_name,
            'registers_found': len(registers_found),
            'total_registers': len(register_pairs),
            'correct': num_correct,
            'wrong': num_wrong,
            'missing': num_missing,
            'total_facts': total_facts_for_present_registers,
            'found_accuracy': accuracy,
            'correct_all': num_correct_all,
            'wrong_all': num_wrong_all,
            'missing_all': num_missing_all,
            'total_facts_all': total_facts_all_registers,
            'complete_accuracy': accuracy_all,
            'coverage': coverage,
        })

    df = pd.DataFrame(results)

    # Save results
    df.to_csv(output_path, index=False)

    # Save compact detailed outputs
    df_registers = pd.DataFrame(all_register_rows)
    df_registers.to_csv(register_results_path, index=False)

    df_errors = pd.DataFrame(all_error_rows)
    df_errors.to_csv(fact_errors_path, index=False)

    print("Outputs:")
    print(f"  Summary:         {output_path}")
    print(f"  Per-register:    {register_results_path}")
    print(f"  Wrong + missing: {fact_errors_path}")

if __name__ == "__main__":
    main()
