#!/usr/bin/env python3
"""
Comprehensive analysis of generator markdown chunks results:
1. Accuracy comparison across embedding counts
2. Timing analysis
3. Embedding overlap analysis
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
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

    # Field-level facts
    fields_list = output_json.get('subfields', output_json.get('fields', []))

    for field in fields_list:
        field_name = field.get('name', field.get('field_name', '')).lower()

        if 'access' in field:
            fact_key = (peripheral, register, field_name, 'access')
            facts[fact_key] = str(field['access'])

        if 'bit_number' in field:
            bit_info = field['bit_number']
            if 'start_bit' in bit_info and 'end_bit' in bit_info:
                # Skip if either value is None
                if bit_info['start_bit'] is None or bit_info['end_bit'] is None:
                    continue
                start_bit = min(bit_info['start_bit'], bit_info['end_bit'])
                end_bit = max(bit_info['start_bit'], bit_info['end_bit'])

                fact_key = (peripheral, register, field_name, 'bit_offset')
                facts[fact_key] = str(start_bit)

                bit_width = end_bit - start_bit + 1
                fact_key = (peripheral, register, field_name, 'bit_width')
                facts[fact_key] = str(bit_width)
        else:
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

def load_timing_stats(output_dir):
    """Load timing statistics from timing_stats.json"""
    timing_file = os.path.join(output_dir, "timing_stats.json")

    if not os.path.exists(timing_file):
        return None

    try:
        with open(timing_file, 'r') as f:
            return json.load(f)
    except:
        return None

def load_embedding_ids(output_dir):
    """Load embedding IDs from info/embedding_ids.jsonl"""
    embedding_file = os.path.join(output_dir, "info", "embedding_ids.jsonl")

    if not os.path.exists(embedding_file):
        return []

    embeddings = []
    with open(embedding_file, 'r') as f:
        for line in f:
            if line.strip():
                embeddings.append(json.loads(line))

    return embeddings

def analyze_embedding_overlap(all_embeddings_data):
    """Analyze overlap between different embedding counts"""

    print(f"\n{'='*80}")
    print("EMBEDDING OVERLAP ANALYSIS")
    print(f"{'='*80}\n")

    # Group by register
    by_register = defaultdict(dict)

    for num_emb, emb_data in all_embeddings_data.items():
        for entry in emb_data:
            register = entry['register']
            chunk_ids = [emb['filename'] for emb in entry['embedding_ids']]
            by_register[register][num_emb] = set(chunk_ids)

    # Analyze overlap for each register
    for register in sorted(by_register.keys()):
        print(f"\nRegister: {register}")
        print("-" * 60)

        chunks_by_config = by_register[register]

        # Show chunks retrieved for each configuration
        for num_emb in sorted(chunks_by_config.keys()):
            chunks = chunks_by_config[num_emb]
            print(f"  {num_emb:2d} embeddings: {len(chunks)} chunks")

        # Calculate overlap between consecutive configs
        configs = sorted(chunks_by_config.keys())
        for i in range(len(configs) - 1):
            curr_config = configs[i]
            next_config = configs[i + 1]

            curr_chunks = chunks_by_config[curr_config]
            next_chunks = chunks_by_config[next_config]

            overlap = curr_chunks & next_chunks
            new_in_next = next_chunks - curr_chunks

            overlap_pct = len(overlap) / len(curr_chunks) * 100 if curr_chunks else 0

            print(f"\n  Overlap {curr_config} → {next_config}:")
            print(f"    {len(overlap)}/{len(curr_chunks)} chunks retained ({overlap_pct:.0f}%)")
            print(f"    {len(new_in_next)} new chunks added")

            if new_in_next and len(new_in_next) <= 5:
                print(f"    New chunks: {', '.join(sorted(new_in_next))}")

def main():
    # Change to repo root directory
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)

    # Configuration
    verified_csv = "verified_datasheet/stm/rm0041/rm0041_stm32f100_full.csv"
    peripheral = "afio"
    embedding_configs = [4, 8, 16, 50]
    base_dir = "optimization/generator_md_chunks"

    print(f"{'='*80}")
    print("COMPREHENSIVE GENERATOR MD CHUNKS ANALYSIS")
    print(f"{'='*80}\n")
    print(f"Analyzing peripheral: {peripheral}")
    print(f"Verified datasheet: {verified_csv}")
    print(f"Base directory: {base_dir}\n")

    # Load verified datasheet
    print("Loading verified datasheet...")
    verified_facts = load_verified_datasheet(verified_csv, peripheral_filter=peripheral)
    print(f"Found {len(verified_facts)} verified facts for {peripheral}\n")

    # Get list of registers
    registers = set()
    for (p, r, f, k) in verified_facts.keys():
        if p == peripheral:
            registers.add(r)
    registers = sorted(registers)
    print(f"Registers to check: {registers}\n")

    # Collect results for all configurations
    accuracy_results = []
    timing_results = []
    all_embeddings_data = {}

    for num_embeddings in embedding_configs:
        output_dir = os.path.join(base_dir, f"embeddings_{num_embeddings}")

        print(f"{'='*80}")
        print(f"ANALYZING: {num_embeddings} embeddings")
        print(f"Output directory: {output_dir}")
        print(f"{'='*80}\n")

        # === ACCURACY ANALYSIS ===
        all_generator_facts = {}
        registers_found = []

        for register in registers:
            output_json = load_generator_output(output_dir, peripheral, register)
            if output_json:
                registers_found.append(register)
                facts = extract_facts_from_generator_output(output_json, peripheral, register)
                all_generator_facts.update(facts)

        correct, wrong, missing = compare_outputs(verified_facts, all_generator_facts)

        total_verified = len(verified_facts)
        num_correct = len(correct)
        num_wrong = len(wrong)
        num_missing = len(missing)
        accuracy = (num_correct / total_verified * 100) if total_verified > 0 else 0

        print(f"Accuracy Results:")
        print(f"  Registers found: {len(registers_found)}/{len(registers)}")
        print(f"  Correct: {num_correct}/{total_verified} ({accuracy:.1f}%)")
        print(f"  Wrong:   {num_wrong}/{total_verified} ({num_wrong/total_verified*100:.1f}%)")
        print(f"  Missing: {num_missing}/{total_verified} ({num_missing/total_verified*100:.1f}%)")
        print()

        # === TIMING ANALYSIS ===
        timing_stats = load_timing_stats(output_dir)

        if timing_stats:
            gen_stats = timing_stats.get('generator_llm_call', {})
            vs_stats = timing_stats.get('vector_store_search', {})

            gen_total = gen_stats.get('total_time', 0)
            gen_avg = gen_stats.get('avg_time', 0)
            gen_count = gen_stats.get('count', 0)

            vs_total = vs_stats.get('total_time', 0)
            vs_avg = vs_stats.get('avg_time', 0)
            vs_count = vs_stats.get('count', 0)

            total_time = gen_total + vs_total

            print(f"Timing Results:")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Generator LLM: {gen_total:.2f}s total, {gen_avg:.2f}s avg ({gen_count} calls)")
            print(f"  Vector search: {vs_total:.2f}s total, {vs_avg:.2f}s avg ({vs_count} calls)")
            print()

            timing_results.append({
                'embeddings': num_embeddings,
                'total_time': total_time,
                'gen_total': gen_total,
                'gen_avg': gen_avg,
                'gen_count': gen_count,
                'vs_total': vs_total,
                'vs_avg': vs_avg,
                'vs_count': vs_count
            })

        # === LOAD EMBEDDING DATA ===
        embedding_data = load_embedding_ids(output_dir)
        all_embeddings_data[num_embeddings] = embedding_data

        accuracy_results.append({
            'embeddings': num_embeddings,
            'registers_found': len(registers_found),
            'total_registers': len(registers),
            'correct': num_correct,
            'wrong': num_wrong,
            'missing': num_missing,
            'total': total_verified,
            'accuracy': accuracy
        })

    # === SUMMARY TABLES ===
    print(f"\n{'='*80}")
    print("ACCURACY SUMMARY")
    print(f"{'='*80}\n")

    df_accuracy = pd.DataFrame(accuracy_results)
    print(df_accuracy.to_string(index=False))
    print()

    print(f"\n{'='*80}")
    print("TIMING SUMMARY")
    print(f"{'='*80}\n")

    if timing_results:
        df_timing = pd.DataFrame(timing_results)
        print(df_timing.to_string(index=False))
        print()

    # === EMBEDDING OVERLAP ANALYSIS ===
    if all_embeddings_data:
        analyze_embedding_overlap(all_embeddings_data)

    # === SAVE RESULTS ===
    output_file = os.path.join(base_dir, "comprehensive_analysis.csv")

    # Merge accuracy and timing data
    df_merged = df_accuracy
    if timing_results:
        df_merged = df_accuracy.merge(df_timing, on='embeddings', how='left')

    df_merged.to_csv(output_file, index=False)
    print(f"\n\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()
