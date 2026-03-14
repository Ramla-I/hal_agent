#!/usr/bin/env python3
"""
Generator optimization script — sweeps batch sizing, prompt reasoning,
and context retrieval parameters.

Tracks accuracy, token usage, and wall-clock time per configuration.
Outputs a sweep_results.csv summary and per-config comparison files.

Usage:
    Edit the CONFIGURATION BLOCK below and run:

        python3 optimize_generator/optimize_generator.py
"""

import csv
import json
import os
import sys
import time
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from defs import (
    BatchedRetrievalStrategy,
    ContextRetrievalMethod,
    ContextRetrievalParameters,
    Manufacturer,
)
from agent_tools.tools import all_svd_file_paths
from agent_tools.svd_parsing import get_register_names_for_peripheral
from core.s1a_generator import run_generator_batched
from optimize_retrieval.run_sweep import run_comparison, _get_verified_csv_path
from utils.timing import get_timing_stats


# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION BLOCK  (edit-and-run)
# ═══════════════════════════════════════════════════════════════════════

# Device
DEVICE_NAME = "rm0041"
SVD = "stm32f100"
PERIPHERALS_TO_RUN = [
    "afio", "bkp", "cec", "crc", "dac", "exti",
    "flash", "fsmc", "iwdg", "pwr", "rcc",
]

# Model
CLIENT = "groq"                            # "openai" or "groq"
MODEL_NAME = "gpt-oss-120b"

# Generator sweep parameters
MAX_FIELDS_PER_BATCH_VALUES = [30]          # try [30, 50, 75, 100, 999]
MAX_REGISTERS_PER_BATCH_VALUES = [10]       # try [5, 10, 15, 30]
INCLUDE_REASONING_VALUES = [True]          # try [True, False]
SKIP_FUNCTION_FOLLOWUP_VALUES = [True]     # try [True, False]
SYSTEM_PROMPT_STYLE_VALUES = ["minimal"]           # try ["full", "minimal"]

# Context retrieval (fixed defaults — sD+mfpb50 experiment)
CONTEXT_METHOD = ContextRetrievalMethod.LOCAL_VECTOR_DB
LOCAL_DB_NAME = "rm0041_md_chunks"
NUM_EMBEDDINGS = 2
RERANKER_TYPE = "local"
METADATA_FILTER = True
PAGES_AFTER = 1
CHUNK_INDEX_PATH = "chunked_datasheets/stm/rm0041/chunks/md/chunks_index.csv"
BATCHED_STRATEGY = BatchedRetrievalStrategy.PER_REGISTER_TRIMMED

# Context retrieval sweep (empty = use fixed defaults above)
NUM_EMBEDDINGS_VALUES: List[int] = []      # e.g. [1, 2, 4]
PAGES_AFTER_VALUES: List[int] = []         # e.g. [0, 1, 2]

# Experiment name (output directory)
EXPERIMENT_NAME = "prompt_and_skipfn_sweep"

# ═══════════════════════════════════════════════════════════════════════


def _build_config_matrix() -> List[Dict]:
    """Cartesian product of sweep parameters → list of config dicts."""
    emb_values = NUM_EMBEDDINGS_VALUES or [NUM_EMBEDDINGS]
    pa_values = PAGES_AFTER_VALUES or [PAGES_AFTER]

    configs = []
    for mfpb, mrpb, reasoning, skip_fn, prompt_style, n_emb, pa in product(
        MAX_FIELDS_PER_BATCH_VALUES,
        MAX_REGISTERS_PER_BATCH_VALUES,
        INCLUDE_REASONING_VALUES,
        SKIP_FUNCTION_FOLLOWUP_VALUES,
        SYSTEM_PROMPT_STYLE_VALUES,
        emb_values,
        pa_values,
    ):
        configs.append({
            "max_fields_per_batch": mfpb,
            "max_registers_per_batch": mrpb,
            "include_reasoning": reasoning,
            "skip_function_followup": skip_fn,
            "prompt_style": prompt_style,
            "num_embeddings": n_emb,
            "pages_after": pa,
        })
    return configs


def _folder_name(cfg: Dict) -> str:
    """Generate a descriptive folder name from config dict."""
    parts = [
        f"mfpb{cfg['max_fields_per_batch']}",
        f"mrpb{cfg['max_registers_per_batch']}",
    ]
    if not cfg["include_reasoning"]:
        parts.append("noreas")
    if cfg["skip_function_followup"]:
        parts.append("skipfn")
    if cfg["prompt_style"] != "full":
        parts.append(cfg["prompt_style"])
    # Only include retrieval overrides when they differ from fixed defaults
    if NUM_EMBEDDINGS_VALUES:
        parts.append(f"emb{cfg['num_embeddings']}")
    if PAGES_AFTER_VALUES:
        parts.append(f"pa{cfg['pages_after']}")
    return "_".join(parts)


def _build_context_params(cfg: Dict) -> ContextRetrievalParameters:
    """Build ContextRetrievalParameters from config dict + fixed defaults."""
    pa = cfg["pages_after"]
    return ContextRetrievalParameters(
        context_retrieval_method=CONTEXT_METHOD,
        pages_after_keyword=0,
        remove_tables=False,
        number_embeddings=cfg["num_embeddings"],
        re_ranking=False,
        score_threshold=0.0,
        vs_id="",
        regex="",
        local_db_name=LOCAL_DB_NAME,
        local_db_path="",
        keyword_boost=False,
        reranker_type=RERANKER_TYPE,
        metadata_filter_enabled=METADATA_FILTER,
        chunk_expansion_enabled=pa > 0,
        pages_after=pa,
        chunk_index_path=CHUNK_INDEX_PATH if pa > 0 else "",
        expand_table_pages_only=False,
        batched_retrieval_strategy=BATCHED_STRATEGY,
    )


def _load_usage_csv(info_dir: str) -> Dict:
    """Aggregate token usage from info/usage.csv."""
    usage_path = os.path.join(info_dir, "usage.csv")
    totals = {
        "total_input": 0,
        "total_cached": 0,
        "total_output": 0,
        "total_reasoning": 0,
        "total_total": 0,
        "context_tokens": 0,
        "llm_calls": 0,
    }
    if not os.path.exists(usage_path):
        return totals
    with open(usage_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            totals["total_input"] += int(row.get("input_tokens", 0))
            totals["total_cached"] += int(row.get("cached_tokens", 0))
            totals["total_output"] += int(row.get("output_tokens", 0))
            totals["total_reasoning"] += int(row.get("reasoning_tokens", 0))
            totals["total_total"] += int(row.get("total_tokens", 0))
            totals["context_tokens"] += int(row.get("file_search_tokens", 0))
            totals["llm_calls"] += 1
    return totals


def _load_timing_stats(info_dir: str) -> Dict:
    """Load timing stats from info/timing_stats.json."""
    path = os.path.join(info_dir, "timing_stats.json")
    result = {"llm_time": 0.0, "search_time": 0.0, "total_time": 0.0}
    if not os.path.exists(path):
        return result
    with open(path, "r") as f:
        data = json.load(f)
    result["llm_time"] = data.get("generator_llm_call", {}).get("total_time", 0.0)
    # Aggregate all search-related timing keys
    for key in ("local_vector_search", "vector_store_search", "keyword_search",
                "chunk_expansion", "reranker"):
        result["search_time"] += data.get(key, {}).get("total_time", 0.0)
    result["total_time"] = result["llm_time"] + result["search_time"]
    return result


def main():
    ctx = next((c for c in config.user_contexts if c.device_name == DEVICE_NAME), None)
    manufacturer = ctx.manufacturer if ctx else Manufacturer.STM
    device_dir = f"devices/{manufacturer.value.lower()}/{DEVICE_NAME}"

    client = config.client_groq if CLIENT == "groq" else config.client_openai

    # Build peripheral → register mapping
    svd_file_paths = all_svd_file_paths(device_dir)
    peripherals_registers_dict: Dict[str, List[str]] = {}
    for p in PERIPHERALS_TO_RUN:
        peripherals_registers_dict[p] = get_register_names_for_peripheral(svd_file_paths, p)
    total_registers = sum(len(v) for v in peripherals_registers_dict.values())

    configs = _build_config_matrix()
    experiment_dir = os.path.join("optimize_generator", "experiments", EXPERIMENT_NAME)
    os.makedirs(experiment_dir, exist_ok=True)

    print(f"\n{'='*70}")
    print("GENERATOR OPTIMIZATION SWEEP")
    print(f"{'='*70}")
    print(f"Device: {DEVICE_NAME}")
    print(f"Peripherals: {PERIPHERALS_TO_RUN}")
    print(f"Total registers: {total_registers}")
    print(f"Model: {MODEL_NAME} ({CLIENT})")
    print(f"Configurations: {len(configs)}")
    print(f"Output: {experiment_dir}")
    print(f"{'='*70}\n")

    timing = get_timing_stats()
    all_results: List[Dict] = []

    for idx, cfg in enumerate(configs, 1):
        folder = _folder_name(cfg)
        output_dir = os.path.join(experiment_dir, folder)
        os.makedirs(output_dir, exist_ok=True)
        info_dir = os.path.join(output_dir, "info")
        os.makedirs(info_dir, exist_ok=True)

        print(f"\n[{idx}/{len(configs)}] Config: {folder}")
        print(f"  mfpb={cfg['max_fields_per_batch']}, mrpb={cfg['max_registers_per_batch']}, "
              f"reasoning={cfg['include_reasoning']}, skip_fn={cfg['skip_function_followup']}, "
              f"emb={cfg['num_embeddings']}, pa={cfg['pages_after']}")

        context_params = _build_context_params(cfg)

        # Build system prompt based on style
        system_prompt_override = None
        if cfg["prompt_style"] == "minimal":
            from prompts.register_info_stm import create_register_info_stm_system_prompt_batched_minimal
            system_prompt_override = create_register_info_stm_system_prompt_batched_minimal(
                include_reasoning=cfg["include_reasoning"],
            )

        # Reset timing and run generator
        timing.reset()
        wall_start = time.time()

        run_generator_batched(
            client=client,
            model_name=MODEL_NAME,
            device_name=DEVICE_NAME,
            run_number=1,
            device_dir=device_dir,
            agent_output_dir=output_dir,
            context_retrieval_parameters=context_params,
            manufacturer=manufacturer,
            peripherals_registers_dict=peripherals_registers_dict,
            max_registers_per_batch=cfg["max_registers_per_batch"],
            max_fields_per_batch=cfg["max_fields_per_batch"],
            include_reasoning=cfg["include_reasoning"],
            skip_function_followup=cfg["skip_function_followup"],
            system_prompt_override=system_prompt_override,
        )

        wall_time = time.time() - wall_start
        timing.save_to_file(os.path.join(info_dir, "timing_stats.json"))

        # Run comparison per peripheral
        correct_sum = wrong_sum = missing_sum = 0
        total_facts_sum = total_facts_all_sum = 0
        correct_all_sum = wrong_all_sum = missing_all_sum = 0
        registers_found_sum = total_registers_sum = 0
        combined_register_results: List[Dict] = []
        combined_fact_errors: List[Dict] = []

        for peripheral_name in PERIPHERALS_TO_RUN:
            verified_csv = _get_verified_csv_path(device_dir, SVD, peripheral_name)
            if not verified_csv:
                print(f"  Warning: No verified CSV for {peripheral_name}; skipping comparison.")
                continue

            comparison = run_comparison(output_dir, verified_csv, peripheral_name)

            correct_sum += comparison["correct"]
            wrong_sum += comparison["wrong"]
            missing_sum += comparison["missing"]
            total_facts_sum += comparison["total_facts"]
            correct_all_sum += comparison["correct_all"]
            wrong_all_sum += comparison["wrong_all"]
            missing_all_sum += comparison["missing_all"]
            total_facts_all_sum += comparison["total_facts_all"]
            registers_found_sum += comparison["registers_found"]
            total_registers_sum += comparison["total_registers"]
            combined_register_results.extend(comparison.get("register_results", []))
            combined_fact_errors.extend(comparison.get("fact_errors", []))

        # Compute accuracy
        found_accuracy = (correct_sum / total_facts_sum * 100) if total_facts_sum > 0 else 0
        complete_accuracy = (correct_all_sum / total_facts_all_sum * 100) if total_facts_all_sum > 0 else 0
        coverage = (total_facts_sum / total_facts_all_sum * 100) if total_facts_all_sum > 0 else 0

        print(f"  Results: {correct_sum}/{total_facts_sum} correct ({found_accuracy:.1f}% found acc)")
        print(f"           {registers_found_sum}/{total_registers_sum} regs, "
              f"{coverage:.1f}% coverage, {complete_accuracy:.1f}% complete acc")

        # Save per-config comparison files
        comparison_combined = {
            "peripherals": sorted(PERIPHERALS_TO_RUN),
            "registers_found": registers_found_sum,
            "total_registers": total_registers_sum,
            "correct": correct_sum,
            "wrong": wrong_sum,
            "missing": missing_sum,
            "total_facts": total_facts_sum,
            "found_accuracy": found_accuracy,
            "correct_all": correct_all_sum,
            "wrong_all": wrong_all_sum,
            "missing_all": missing_all_sum,
            "total_facts_all": total_facts_all_sum,
            "complete_accuracy": complete_accuracy,
            "coverage": coverage,
        }
        with open(os.path.join(info_dir, "comparison_results.json"), "w") as f:
            json.dump(comparison_combined, f, indent=2)

        if combined_register_results:
            with open(os.path.join(info_dir, "comparison_register_results.csv"), "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(combined_register_results[0].keys()))
                writer.writeheader()
                writer.writerows(combined_register_results)

        if combined_fact_errors:
            with open(os.path.join(info_dir, "comparison_fact_errors.csv"), "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(combined_fact_errors[0].keys()))
                writer.writeheader()
                writer.writerows(combined_fact_errors)

        # Collect usage and timing
        usage = _load_usage_csv(info_dir)
        timing_stats = _load_timing_stats(info_dir)

        result_row = {
            "config": folder,
            "max_fields_per_batch": cfg["max_fields_per_batch"],
            "max_registers_per_batch": cfg["max_registers_per_batch"],
            "include_reasoning": cfg["include_reasoning"],
            "skip_function_followup": cfg["skip_function_followup"],
            "prompt_style": cfg["prompt_style"],
            "num_embeddings": cfg["num_embeddings"],
            "pages_after": cfg["pages_after"],
            # Quality
            "found_accuracy": round(found_accuracy, 2),
            "complete_accuracy": round(complete_accuracy, 2),
            "coverage": round(coverage, 2),
            "registers_found": registers_found_sum,
            "total_registers": total_registers_sum,
            "correct": correct_sum,
            "wrong": wrong_sum,
            "missing": missing_sum,
            # Tokens
            "total_input": usage["total_input"],
            "total_cached": usage["total_cached"],
            "total_output": usage["total_output"],
            "total_reasoning": usage["total_reasoning"],
            "total_total": usage["total_total"],
            "context_tokens": usage["context_tokens"],
            # Time
            "llm_time": round(timing_stats["llm_time"], 2),
            "search_time": round(timing_stats["search_time"], 2),
            "total_time": round(timing_stats["total_time"], 2),
            "wall_time": round(wall_time, 2),
            # Efficiency
            "llm_calls": usage["llm_calls"],
            "tokens_per_register": round(usage["total_total"] / total_registers, 1) if total_registers > 0 else 0,
            "time_per_register": round(wall_time / total_registers, 2) if total_registers > 0 else 0,
        }
        all_results.append(result_row)

    # ── Summary tables ──────────────────────────────────────────────────

    print(f"\n{'='*70}")
    print(f"SWEEP COMPLETE: {len(configs)} configurations")
    print(f"{'='*70}")

    if all_results:
        # Performance table
        print(f"\nPERFORMANCE:")
        print(f"{'-'*110}")
        print(f"{'Config':<30} {'LLM calls':>10} {'Wall time':>10} {'LLM time':>10} {'Search time':>12} {'Total tokens':>13}")
        print(f"{'-'*110}")
        for r in all_results:
            print(f"{r['config']:<30} {r['llm_calls']:>10} {r['wall_time']:>9.1f}s {r['llm_time']:>9.1f}s {r['search_time']:>11.1f}s {r['total_total']:>13,}")
        print(f"{'-'*110}")

        # Quality table
        print(f"\nQUALITY:")
        print(f"{'-'*110}")
        print(f"{'Config':<30} {'Regs':>8} {'Correct':>8} {'Wrong':>6} {'Missing':>8} {'Found%':>8} {'Complete%':>10} {'Coverage%':>10}")
        print(f"{'-'*110}")
        for r in all_results:
            regs = f"{r['registers_found']}/{r['total_registers']}"
            print(f"{r['config']:<30} {regs:>8} {r['correct']:>8} {r['wrong']:>6} {r['missing']:>8} {r['found_accuracy']:>7.1f}% {r['complete_accuracy']:>9.1f}% {r['coverage']:>9.1f}%")
        print(f"{'-'*110}")

        # Efficiency table (relative to first config)
        if len(all_results) > 1:
            baseline = all_results[0]
            print(f"\nEFFICIENCY (vs {baseline['config']}):")
            print(f"{'-'*90}")
            print(f"{'Config':<30} {'Tokens/reg':>12} {'Time/reg':>10} {'Token ratio':>12} {'Time ratio':>12}")
            print(f"{'-'*90}")
            for r in all_results:
                tok_ratio = (r["tokens_per_register"] / baseline["tokens_per_register"]) if baseline["tokens_per_register"] > 0 else 0
                time_ratio = (r["time_per_register"] / baseline["time_per_register"]) if baseline["time_per_register"] > 0 else 0
                print(f"{r['config']:<30} {r['tokens_per_register']:>12.1f} {r['time_per_register']:>9.2f}s {tok_ratio:>11.2f}x {time_ratio:>11.2f}x")
            print(f"{'-'*90}")

        # Save sweep_results.csv
        csv_path = os.path.join(experiment_dir, "sweep_results.csv")
        fieldnames = list(all_results[0].keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)
        print(f"\nSummary saved to: {csv_path}")

    print()


if __name__ == "__main__":
    main()
