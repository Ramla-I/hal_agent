#!/usr/bin/env python3
"""
Full evaluation of OpenEvolve checkpoint programs against ALL 11 verified peripherals.

Mirrors the evaluation pattern from evaluator.py but runs on the complete test set
(afio, bkp, cec, crc, dac, exti, flash, fsmc, iwdg, pwr, rcc — 97 registers).

Usage:
    source .venv/bin/activate && python3 openevolve_retrieval/full_eval.py
"""

import csv
import importlib.util
import json
import os
import sys
import time
import traceback
from typing import Dict, List, Optional, Tuple

# Resolve paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Ensure _shared_cache is importable
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from openai import OpenAI

from prompts.register_info_stm import (
    create_register_info_stm_system_prompt,
    create_register_info_stm_user_prompt,
)
from utils.parse_output import get_json_block_from_response, get_reasoning_from_response
from utils.generator_facts import extract_facts_from_generator_output
from optimization.common.compare_generator_with_verified import (
    load_verified_datasheet,
    compare_outputs,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHUNKS_DIR = os.path.join(
    _PROJECT_ROOT, "chunked_datasheets", "stm", "rm0041", "chunks", "md"
)
CHUNKS_INDEX_CSV = os.path.join(CHUNKS_DIR, "chunks_index.csv")
VERIFIED_CSV = os.path.join(
    _PROJECT_ROOT, "verified_datasheet", "stm", "rm0041", "rm0041_stm32f100_full.csv"
)

ALL_PERIPHERALS = [
    "afio", "bkp", "cec", "crc", "dac", "exti", "flash", "fsmc", "iwdg", "pwr", "rcc"
]

PROGRAMS = [
    {
        "name": "best_iter18",
        "path": os.path.join(
            _PROJECT_ROOT,
            "openevolve_retrieval/output_rm0041/best/best_program.py",
        ),
    },
]

GENERATOR_MODEL = "openai/gpt-oss-120b"
GENERATOR_TIMEOUT = 45  # slightly longer for complex registers
MAX_RETRIES = 2

OUTPUT_FILE = os.path.join(_SCRIPT_DIR, "output_rm0041", "full_eval_results.json")


def _get_generator_client() -> OpenAI:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable not set")
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def _get_test_registers(
    verified_facts: Dict, peripherals: List[str]
) -> List[Tuple[str, str]]:
    pairs = set()
    for (p, r, f, k) in verified_facts.keys():
        if p in peripherals:
            pairs.add((p, r))
    return sorted(pairs)


def _count_facts(verified_facts: Dict, peripheral: str, register: str) -> int:
    return sum(1 for (p, r, _, _) in verified_facts if p == peripheral and r == register)


def _run_generator_single(
    client: OpenAI,
    context: str,
    peripheral_name: str,
    register_name: str,
) -> Tuple[Optional[Dict], Optional[Dict]]:
    """Returns (generator_output, usage_dict)."""
    system_prompt = create_register_info_stm_system_prompt(
        function_calls_description=None, examples=None
    )
    user_prompt = create_register_info_stm_user_prompt(
        register_name, peripheral_name, context
    )

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=GENERATOR_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                timeout=GENERATOR_TIMEOUT,
            )
            text = response.choices[0].message.content
            usage = None
            if response.usage:
                usage = {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            if not text:
                continue

            _, rest = get_reasoning_from_response(text)
            json_str = get_json_block_from_response(rest)
            if json_str:
                return json.loads(json_str), usage
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(1)
                continue
    return None, None


def _compare_single_register(
    verified_facts: Dict,
    generator_output: Optional[Dict],
    peripheral: str,
    register: str,
) -> Tuple[int, int, int]:
    reg_verified = {
        k: v for k, v in verified_facts.items()
        if k[0] == peripheral and k[1] == register
    }
    if not reg_verified:
        return 0, 0, 0

    if generator_output is None:
        return 0, 0, len(reg_verified)

    gen_facts = extract_facts_from_generator_output(
        generator_output, peripheral, register
    )
    registers_found = {(peripheral, register)}
    correct, wrong, missing = compare_outputs(reg_verified, gen_facts, registers_found)
    return len(correct), len(wrong), len(missing)


def load_program(program_path: str, module_name: str):
    """Dynamically load an evolved program module."""
    spec = importlib.util.spec_from_file_location(module_name, program_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def evaluate_program(
    program_info: Dict,
    verified_facts: Dict,
    test_registers: List[Tuple[str, str]],
    client: OpenAI,
) -> Dict:
    """Evaluate a single program on all test registers.

    Returns per-peripheral and overall metrics.
    """
    name = program_info["name"]
    path = program_info["path"]
    print(f"\n{'='*70}")
    print(f"Evaluating: {name}")
    print(f"  Path: {path}")
    print(f"  Registers: {len(test_registers)}")
    print(f"{'='*70}")

    t_start = time.time()

    # Load module
    try:
        mod = load_program(path, f"evolved_{name}")
    except Exception as e:
        print(f"  ERROR: Import failed: {e}")
        return {"name": name, "error": f"Import failed: {e}"}

    # Setup database
    try:
        t_db = time.time()
        collection, processed_chunks = mod.setup_database(CHUNKS_DIR, CHUNKS_INDEX_CSV)
        db_time = time.time() - t_db
        print(f"  DB setup: {db_time:.1f}s")
    except Exception as e:
        print(f"  ERROR: setup_database() failed: {traceback.format_exc()}")
        return {"name": name, "error": f"setup_database() failed: {e}"}

    # Per-peripheral tracking
    peripheral_results = {}
    overall = {
        "found_correct": 0,
        "found_wrong": 0,
        "found_missing": 0,
        "not_found_facts": 0,
        "registers_found": 0,
        "total_registers": len(test_registers),
    }
    overall_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    # Group registers by peripheral
    from collections import defaultdict
    periph_regs = defaultdict(list)
    for p, r in test_registers:
        periph_regs[p].append(r)

    for periph in sorted(periph_regs.keys()):
        regs = periph_regs[periph]
        p_correct = 0
        p_wrong = 0
        p_missing = 0
        p_not_found_facts = 0
        p_regs_found = 0
        p_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        print(f"\n  [{periph}] {len(regs)} registers: ", end="", flush=True)

        for register in regs:
            # Retrieve context
            try:
                context = mod.run_retrieval(
                    periph, register, collection, processed_chunks
                )
            except Exception:
                context = None

            reg_fact_count = _count_facts(verified_facts, periph, register)

            if not context or len(context) < 20:
                p_not_found_facts += reg_fact_count
                print("x", end="", flush=True)
                continue

            # Run generator
            gen_output, usage = _run_generator_single(client, context, periph, register)
            if usage:
                for k in p_usage:
                    p_usage[k] += usage[k]

            if gen_output is None:
                p_not_found_facts += reg_fact_count
                print("o", end="", flush=True)
                continue

            p_regs_found += 1

            # Compare
            c, w, m = _compare_single_register(
                verified_facts, gen_output, periph, register
            )
            p_correct += c
            p_wrong += w
            p_missing += m
            print(".", end="", flush=True)

        # Per-peripheral metrics
        found_total = p_correct + p_wrong + p_missing
        complete_total = found_total + p_not_found_facts
        found_acc = (p_correct / found_total * 100) if found_total > 0 else 0
        complete_acc = (p_correct / complete_total * 100) if complete_total > 0 else 0
        coverage = (found_total / complete_total * 100) if complete_total > 0 else 0

        peripheral_results[periph] = {
            "registers_found": p_regs_found,
            "total_registers": len(regs),
            "correct": p_correct,
            "wrong": p_wrong,
            "missing": p_missing,
            "total_facts": found_total,
            "not_found_facts": p_not_found_facts,
            "total_facts_all": complete_total,
            "found_accuracy": round(found_acc, 2),
            "complete_accuracy": round(complete_acc, 2),
            "fact_coverage": round(coverage, 2),
            "usage": p_usage,
        }

        print(f" -> {p_regs_found}/{len(regs)} regs, {p_correct}/{complete_total} facts ({complete_acc:.1f}% complete)")

        # Accumulate overall
        overall["found_correct"] += p_correct
        overall["found_wrong"] += p_wrong
        overall["found_missing"] += p_missing
        overall["not_found_facts"] += p_not_found_facts
        overall["registers_found"] += p_regs_found
        for k in overall_usage:
            overall_usage[k] += p_usage[k]

    # Overall metrics
    found_total = overall["found_correct"] + overall["found_wrong"] + overall["found_missing"]
    complete_total = found_total + overall["not_found_facts"]
    found_acc = (overall["found_correct"] / found_total * 100) if found_total > 0 else 0
    complete_acc = (overall["found_correct"] / complete_total * 100) if complete_total > 0 else 0
    coverage = (found_total / complete_total * 100) if complete_total > 0 else 0

    total_time = time.time() - t_start

    result = {
        "name": name,
        "path": path,
        "registers_found": overall["registers_found"],
        "total_registers": overall["total_registers"],
        "correct": overall["found_correct"],
        "wrong": overall["found_wrong"],
        "missing": overall["found_missing"],
        "total_facts": found_total,
        "not_found_facts": overall["not_found_facts"],
        "total_facts_all": complete_total,
        "found_accuracy": round(found_acc, 2),
        "complete_accuracy": round(complete_acc, 2),
        "fact_coverage": round(coverage, 2),
        "db_build_time": round(db_time, 1),
        "total_time": round(total_time, 1),
        "usage": overall_usage,
        "per_peripheral": peripheral_results,
    }

    print(f"\n  OVERALL: {overall['registers_found']}/{overall['total_registers']} regs, "
          f"{overall['found_correct']}/{complete_total} facts")
    print(f"  Found accuracy: {found_acc:.1f}%, Complete accuracy: {complete_acc:.1f}%, "
          f"Coverage: {coverage:.1f}%")
    print(f"  Time: {total_time:.1f}s")
    print(f"  Usage: {overall_usage['input_tokens']:,} input, {overall_usage['output_tokens']:,} output, {overall_usage['total_tokens']:,} total tokens")

    return result


def print_summary(all_results: List[Dict]):
    """Print comparison table."""
    print(f"\n\n{'='*90}")
    print("FULL EVALUATION SUMMARY (11 peripherals, 97 registers)")
    print(f"{'='*90}")

    # Overall table
    header = f"{'Program':<16} {'Regs':>8} {'Correct':>8} {'Wrong':>6} {'Missing':>8} {'Found%':>8} {'Complete%':>10} {'Coverage%':>10} {'Time':>6} {'Tokens':>12}"
    print(header)
    print("-" * len(header))
    for r in all_results:
        if "error" in r:
            print(f"{r['name']:<16} ERROR: {r['error']}")
            continue
        total_tok = r.get("usage", {}).get("total_tokens", 0)
        print(
            f"{r['name']:<16} "
            f"{r['registers_found']:>3}/{r['total_registers']:<4} "
            f"{r['correct']:>8} "
            f"{r['wrong']:>6} "
            f"{r['missing']:>8} "
            f"{r['found_accuracy']:>7.1f}% "
            f"{r['complete_accuracy']:>9.1f}% "
            f"{r['fact_coverage']:>9.1f}% "
            f"{r['total_time']:>5.0f}s"
            f"{total_tok:>12,}"
        )
    print("-" * len(header))

    # Per-peripheral breakdown
    print(f"\nPer-peripheral breakdown:")
    print(f"{'Peripheral':<10}", end="")
    for r in all_results:
        if "error" not in r:
            print(f"  {r['name']:>16} (found/complete/cov)", end="")
    print()
    print("-" * (10 + 50 * len([r for r in all_results if "error" not in r])))

    all_periphs = sorted(set(
        p for r in all_results if "per_peripheral" in r
        for p in r["per_peripheral"]
    ))

    for periph in all_periphs:
        print(f"{periph:<10}", end="")
        for r in all_results:
            if "error" in r:
                continue
            pp = r.get("per_peripheral", {}).get(periph, {})
            if pp:
                print(
                    f"  {pp['found_accuracy']:>5.1f}% / {pp['complete_accuracy']:>5.1f}% / {pp['fact_coverage']:>5.1f}%",
                    end="",
                )
            else:
                print(f"  {'N/A':>20}", end="")
        print()


def main():
    print("OpenEvolve Full Evaluation")
    print(f"Peripherals: {ALL_PERIPHERALS}")

    # Load verified facts
    verified_facts = load_verified_datasheet(VERIFIED_CSV)
    test_registers = _get_test_registers(verified_facts, ALL_PERIPHERALS)
    print(f"Total test registers: {len(test_registers)}")

    # Get LLM client
    client = _get_generator_client()

    # Evaluate each program
    all_results = []
    for prog in PROGRAMS:
        result = evaluate_program(prog, verified_facts, test_registers, client)
        all_results.append(result)

    # Print summary
    print_summary(all_results)

    # Save results
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
