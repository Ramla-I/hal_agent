#!/usr/bin/env python3
"""
Run generator experiments with configurable retrieval parameters.

This script sweeps over different configurations to find optimal retrieval settings:
- Vector store type (text, md, md_enriched)
- Number of embeddings to retrieve
- Contiguous chunk expansion (pages after)
- Table-only expansion filter

After each run, it automatically compares the output against a verified datasheet
(if available) and reports accuracy metrics.

Usage:
    Edit the variables at the top of `main()` and run:

        python3 optimization_generator/optimize_generator.py
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from defs import ContextRetrievalParameters, ContextRetrievalMethod, Manufacturer
from agent_tools.tools import all_svd_file_paths
from agent_tools.svd_parsing import get_register_names_for_peripheral
from core.s1a_generator import run_generator
from utils.timing import get_timing_stats
from utils.vector_store_config import get_vector_stores
from utils.generator_facts import extract_facts_from_generator_output
from optimization_generator.compare_generator_with_verified import (
    load_verified_datasheet,
    load_generator_output,
    compare_outputs,
)


# Hardcoded defaults to keep the CLI small. If you want to tune these later,
# change them here (single source of truth for experiment runs).
DEFAULT_CONTEXT_METHOD = ContextRetrievalMethod.OPENAI_FILE_SEARCH
DEFAULT_PAGES_AFTER_KEYWORD = 2
DEFAULT_REMOVE_TABLES = False
DEFAULT_RE_RANKING = True
DEFAULT_SCORE_THRESHOLD = 0.25

# Mapping from CLI short names to vector_stores.json keys
VS_TYPE_MAPPING = {
    "text": "text_chunks",
    "md": "md_chunks",
    "md_enriched": "md_enriched",
}


def _get_user_context(device_name: str):
    return next((ctx for ctx in config.user_contexts if ctx.device_name == device_name), None)


def _resolve_vs_info(device_dir: str, vs_type: Optional[str], vs_id: Optional[str]) -> tuple[str, str]:
    """
    Resolve the vector store ID and chunk index path.

    Args:
        device_dir: Path to device directory (e.g., 'devices/stm/rm0041')
        vs_type: Vector store type ('text', 'md', 'md_enriched') or None
        vs_id: Explicit vector store ID override

    Returns:
        Tuple of (vs_id, chunk_index_path)

    Priority:
    - explicit `--vs-id` (chunk_index_path will be empty)
    - `--vs-type` lookup from vector_stores.json
    - default from vector_stores.json
    """
    if vs_id:
        # Explicit vs_id, no chunk_index_path available
        return vs_id, ""

    try:
        vs_config = get_vector_stores(device_dir)
    except FileNotFoundError:
        raise ValueError(f"No vector_stores.json found in {device_dir}")

    # Map CLI short name to vector_stores.json key
    if vs_type:
        store_key = VS_TYPE_MAPPING.get(vs_type, vs_type)
    else:
        store_key = vs_config.default or "md_chunks"

    resolved_vs_id = vs_config.get_vs_id(store_key)
    if not resolved_vs_id:
        raise ValueError(f"Vector store '{store_key}' not found in {device_dir}/vector_stores.json")

    chunk_index_path = vs_config.get_chunk_index_path(store_key) or ""

    return resolved_vs_id, chunk_index_path


def _build_peripherals_registers_dict(device_dir: str, peripheral: Optional[str], registers: Optional[List[str]]) -> Optional[Dict[str, List[str]]]:
    """
    Build the `peripherals_registers_dict` input to `run_generator()`.

    Assumptions:
    - Generator output filenames are `<peripheral>_<register>`, so this dict controls granularity.

    Returns:
        - `{peripheral: [registers...]}` when `peripheral` is set
        - `None` when `peripheral` is not set (meaning: run_generator will discover all from SVD)
    """
    if not peripheral:
        return None

    svd_file_paths = all_svd_file_paths(device_dir)
    if registers:
        reg_list = registers
    else:
        reg_list = get_register_names_for_peripheral(svd_file_paths, peripheral)

    return {peripheral: reg_list}


def _generate_output_prefix(vs_type: str, num_embeddings: int, pages_after: int, table_pages_only: bool) -> str:
    """Generate a descriptive output folder name from configuration."""
    parts = [vs_type, f"emb{num_embeddings}", f"pages{pages_after}"]
    if table_pages_only:
        parts.append("tableonly")
    return "_".join(parts)


def _generate_local_output_prefix(
    db_name: str, num_embeddings: int, keyword_boost: bool, reranker_type: str,
    metadata_filter: bool = False, pages_after: int = 0, table_pages_only: bool = False,
) -> str:
    """Generate a descriptive output folder name for local vector DB configuration."""
    parts = [f"local_{db_name}", f"emb{num_embeddings}"]
    if keyword_boost:
        parts.append("kb")
    if reranker_type:
        parts.append(f"rr{reranker_type}")
    if metadata_filter:
        parts.append("mf")
    if pages_after > 0:
        parts.append(f"pa{pages_after}")
    if table_pages_only:
        parts.append("tpo")
    return "_".join(parts)


def _get_verified_csv_path(device_dir: str, svd: str, peripheral: Optional[str] = None) -> Optional[str]:
    """
    Find the verified datasheet CSV for a device.

    Looks for files matching patterns:
    - verified_datasheet/{mfr}/{device}/{device}_{svd}_full.csv
    - verified_datasheet/{mfr}/{device}/{device}_{svd}_{peripheral}.csv
    """
    # Extract manufacturer and device name from device_dir
    # e.g., "devices/stm/rm0041" -> mfr="stm", device="rm0041"
    parts = device_dir.rstrip('/').split('/')
    if len(parts) >= 2:
        device_name = parts[-1]
        mfr = parts[-2]
    else:
        return None

    # Look for verified CSV files
    verified_base = f"verified_datasheet/{mfr}/{device_name}"

    # Try peripheral-specific if requested
    if peripheral:
        peripheral_csv = os.path.join(verified_base, f"{device_name}_{svd}_{peripheral}.csv")
        if os.path.exists(peripheral_csv):
            return peripheral_csv

    # Try full CSV
    full_csv = os.path.join(verified_base, f"{device_name}_{svd}_full.csv")
    if os.path.exists(full_csv):
        return full_csv

    return None


def run_comparison(
    output_dir: str,
    verified_csv: str,
    peripheral_filter: str = None
) -> Dict:
    """
    Compare generator output against verified datasheet and return accuracy metrics.

    Args:
        output_dir: Directory containing generator outputs
        verified_csv: Path to verified datasheet CSV
        peripheral_filter: Optional peripheral to filter by

    Returns:
        Dict with accuracy metrics plus compact detailed outputs:
        - registers_found, total_registers, correct, wrong, missing, total_facts, accuracy
        - register_results: List[Dict] (one row per verified register)
        - fact_errors: List[Dict] (one row per wrong/missing fact)
    """
    # Load verified facts
    verified_facts = load_verified_datasheet(verified_csv, peripheral_filter=peripheral_filter)

    # Get list of (peripheral, register) pairs to check
    register_pairs = set()
    for (p, r, f, k) in verified_facts.keys():
        register_pairs.add((p, r))
    register_pairs = sorted(register_pairs)

    # Collect all facts from generator output
    all_generator_facts = {}
    registers_found = set()

    for peripheral, register in register_pairs:
        output_json = load_generator_output(output_dir, peripheral, register)
        if output_json:
            registers_found.add((peripheral, register))
            facts = extract_facts_from_generator_output(output_json, peripheral, register)
            all_generator_facts.update(facts)

    # Compare outputs (present registers only)
    correct, wrong, missing = compare_outputs(verified_facts, all_generator_facts, registers_found)
    # Compare outputs (all registers — treats not-found registers as fully missing)
    correct_all, wrong_all, missing_all = compare_outputs(
        verified_facts, all_generator_facts, set(register_pairs),
    )

    # Per-register breakdown + errors (compact)
    register_results: List[Dict] = []
    fact_errors: List[Dict] = []

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

            for w_item in w_r:
                fact = w_item["fact"]
                fact_errors.append({
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
                fact_errors.append({
                    "error_type": "missing",
                    "peripheral": fact[0],
                    "register": fact[1],
                    "field_name": fact[2],
                    "key": fact[3],
                    "correct_value": m_item["correct_value"],
                    "generated_value": "",
                })
        else:
            correct_r = 0
            wrong_r = 0
            missing_r = total_verified_reg_facts
            for fact_key, correct_value in verified_reg_facts.items():
                fact_errors.append({
                    "error_type": "missing",
                    "peripheral": fact_key[0],
                    "register": fact_key[1],
                    "field_name": fact_key[2],
                    "key": fact_key[3],
                    "correct_value": correct_value,
                    "generated_value": "",
                })

        total_r = correct_r + wrong_r + missing_r
        acc_r = (correct_r / total_r * 100) if total_r > 0 else 0

        register_results.append({
            "peripheral": peripheral,
            "register": register,
            "register_found": found,
            "correct": correct_r,
            "wrong": wrong_r,
            "missing": missing_r,
            "total_facts": total_r,
            "accuracy": acc_r,
        })

    # Found-register metrics (only facts belonging to registers the generator produced)
    found_total = len(correct) + len(wrong) + len(missing)
    found_accuracy = (len(correct) / found_total * 100) if found_total > 0 else 0

    # Complete metrics (all verified facts, including those from not-found registers)
    complete_total = len(correct_all) + len(wrong_all) + len(missing_all)
    complete_accuracy = (len(correct_all) / complete_total * 100) if complete_total > 0 else 0

    # Coverage: what fraction of total verified facts come from found registers
    coverage = (found_total / complete_total * 100) if complete_total > 0 else 0

    return {
        'registers_found': len(registers_found),
        'total_registers': len(register_pairs),
        # Found-register metrics
        'correct': len(correct),
        'wrong': len(wrong),
        'missing': len(missing),
        'total_facts': found_total,
        'found_accuracy': found_accuracy,
        # Complete metrics (all registers)
        'correct_all': len(correct_all),
        'wrong_all': len(wrong_all),
        'missing_all': len(missing_all),
        'total_facts_all': complete_total,
        'complete_accuracy': complete_accuracy,
        # Coverage
        'coverage': coverage,
        # Legacy alias for backward compatibility
        'accuracy': found_accuracy,
        # Details
        'register_results': register_results,
        'fact_errors': fact_errors,
    }


def main():
    # =========================
    # EDIT THESE VARIABLES
    # =========================
    DEVICE_NAME = getattr(config, "DEVICE_NAME", "rm0041")
    # If you want to run a single peripheral, set PERIPHERAL.
    # If you want to run multiple peripherals, set PERIPHERALS_TO_RUN and leave PERIPHERAL=None.
    PERIPHERAL: Optional[str] = None
    # Peripherals that appear in the first 1500 rows of:
    #   verified_datasheet/stm/rm0041/rm0041_stm32f100_full.csv
    PERIPHERALS_TO_RUN: Optional[List[str]] = [
        "afio",
        "bkp",
        "cec",
        "crc",
        "dac",
        "exti",
        "flash",
        "fsmc",
        "iwdg",
        "pwr",
        "rcc",
    ]
    REGISTERS: Optional[List[str]] = None      # e.g. ["evcr", "mapr"]; None = all registers for the peripheral
    SVD = getattr(config, "SVD", "stm32f100")

    # Model/client
    CLIENT = "groq"                            # "openai" or "groq"
    MODEL_NAME = getattr(config, "GENERATOR_MODEL_NAME", "gpt-oss-120b")
    RUN_NUMBER = getattr(config, "GENERATOR_ITER", 1)

    # Sweep parameters (OpenAI vector store)
    USE_OPENAI_VECTOR_STORE = False             # Set to False to skip OpenAI vector store configs
    VS_TYPES = ["md", "md_enriched"]               # ["text", "md", "md_enriched"]
    EMBEDDING_COUNTS = [1, 2]                   # e.g. [4, 8, 16]
    PAGES_AFTER_VALUES = [0, 1]                    # e.g. [1, 2, 3]
    TABLE_PAGES_ONLY_EXPANSION_VALUES = [False, True]    # e.g. [False, True] to sweep both modes

    # Retrieval options (OpenAI)
    CHUNK_EXPANSION_ENABLED = True
    VS_ID_OVERRIDE: Optional[str] = None       # set to a vector-store ID to bypass vector_stores.json resolution
    CHUNK_INDEX_PATH_OVERRIDE: Optional[str] = None

    # Local vector DB sweep parameters
    USE_LOCAL_VECTOR_DB = True                 # Set to True to include local vector DB configs in sweep
    LOCAL_DB_NAMES = ["rm0041_md_chunks_v2"]        # ChromaDB database names to sweep
    LOCAL_EMBEDDING_COUNTS = [2]          # n_results values to sweep for local DB
    KEYWORD_BOOST_VALUES = [False]        # Keyword boost on/off
    RERANKER_TYPES = ["local"]                  # "" = no reranker, "local" = FlashRank
    LOCAL_DB_PATH = ""                          # Override databases directory (default: databases/)
    # Enriched local DB features
    LOCAL_METADATA_FILTER = [True]               # Filter by register name in metadata
    LOCAL_PAGES_AFTER = [0]              # Chunk expansion pages (0 = disabled)
    LOCAL_TABLE_PAGES_ONLY = [False]             # Only expand table-containing pages
    LOCAL_CHUNK_INDEX_PATH = "chunked_datasheets/stm/rm0041/chunks/md/chunks_index.csv"

    # Output
    # OpenAI experiments go to verified_peripherals_v2/, local to local_vector_db_v1/
    OUTPUT_PARENT = "optimization_generator/experiments/verified_peripherals_v2"
    LOCAL_OUTPUT_PARENT = "optimization_generator/experiments/local_vector_db_v7_meta_filter"
    OUTPUT_PREFIX_BASE: Optional[str] = None   # e.g. "my_sweep"; if set, each config becomes "<base>_<auto>"

    # Verified comparison
    SKIP_COMPARISON = False
    VERIFIED_CSV_OVERRIDE: Optional[str] = None
    # =========================

    ctx = _get_user_context(DEVICE_NAME)
    manufacturer = (ctx.manufacturer if ctx else Manufacturer.STM)
    device_dir = f"devices/{manufacturer.value.lower()}/{DEVICE_NAME}"

    if PERIPHERALS_TO_RUN:
        peripherals_to_run: List[Optional[str]] = list(PERIPHERALS_TO_RUN)
    else:
        peripherals_to_run = [PERIPHERAL] if PERIPHERAL else [None]

    # Parse sweep parameters (already lists)
    vs_types = VS_TYPES
    embedding_counts = EMBEDDING_COUNTS
    pages_after_values = PAGES_AFTER_VALUES
    table_pages_only_values = TABLE_PAGES_ONLY_EXPANSION_VALUES

    # Handle chunk expansion flags
    chunk_expansion_enabled = CHUNK_EXPANSION_ENABLED
    # (swept per-config)

    timing = get_timing_stats()
    if USE_OPENAI_VECTOR_STORE:
        os.makedirs(OUTPUT_PARENT, exist_ok=True)

    # Build configuration matrix - each entry is a dict with all config
    configs = []

    # OpenAI vector store configs
    if USE_OPENAI_VECTOR_STORE:
        for vs_type in vs_types:
            for num_embeddings in embedding_counts:
                for pages_after in pages_after_values:
                    for table_pages_only in table_pages_only_values:
                        configs.append({
                            "backend": "openai",
                            "vs_type": vs_type,
                            "num_embeddings": num_embeddings,
                            "pages_after": pages_after,
                            "table_pages_only": table_pages_only,
                        })

    # Local vector DB configs (if enabled)
    if USE_LOCAL_VECTOR_DB:
        os.makedirs(LOCAL_OUTPUT_PARENT, exist_ok=True)
        for local_db in LOCAL_DB_NAMES:
            for num_embeddings in LOCAL_EMBEDDING_COUNTS:
                for kb in KEYWORD_BOOST_VALUES:
                    for rt in RERANKER_TYPES:
                        for mf in LOCAL_METADATA_FILTER:
                            for pa in LOCAL_PAGES_AFTER:
                                for tpo in LOCAL_TABLE_PAGES_ONLY:
                                    configs.append({
                                        "backend": "local",
                                        "local_db_name": local_db,
                                        "num_embeddings": num_embeddings,
                                        "keyword_boost": kb,
                                        "reranker_type": rt,
                                        "metadata_filter": mf,
                                        "pages_after": pa,
                                        "table_pages_only": tpo,
                                    })

    # No filtering needed - single config

    openai_count = sum(1 for c in configs if c["backend"] == "openai")
    local_count = sum(1 for c in configs if c["backend"] == "local")

    print(f"\n{'='*70}")
    print(f"GENERATOR EXPERIMENT SWEEP")
    print(f"{'='*70}")
    print(f"Device: {DEVICE_NAME}")
    if peripherals_to_run == [None]:
        print("Peripherals: (all)")
    else:
        print(f"Peripherals: {peripherals_to_run}")
    print(f"Configurations to run: {len(configs)} ({openai_count} OpenAI, {local_count} local)")
    if openai_count > 0:
        print(f"  OpenAI VS types: {vs_types}")
        print(f"  OpenAI embedding counts: {embedding_counts}")
        print(f"  Pages after: {pages_after_values}")
        print(f"  Chunk expansion: {chunk_expansion_enabled}")
        print(f"  Table pages only (expansion): {table_pages_only_values}")
    if local_count > 0:
        print(f"  Local DB names: {LOCAL_DB_NAMES}")
        print(f"  Local embedding counts: {LOCAL_EMBEDDING_COUNTS}")
        print(f"  Keyword boost: {KEYWORD_BOOST_VALUES}")
        print(f"  Reranker types: {RERANKER_TYPES}")
        print(f"  Metadata filter: {LOCAL_METADATA_FILTER}")
        print(f"  Pages after: {LOCAL_PAGES_AFTER}")
        print(f"  Table pages only: {LOCAL_TABLE_PAGES_ONLY}")
    print(f"{'='*70}\n")

    client = config.client_groq if CLIENT == "groq" else config.client_openai

    # Collect results for summary
    all_results = []

    # Run sweep per configuration.
    # When multiple peripherals are provided, this creates ONE folder per configuration and stores
    # outputs for ALL peripherals inside that folder. Output filenames already include peripheral
    # (`<peripheral>_<register>`), so generator outputs do not collide.
    run_idx = 0
    total_runs = len(configs)
    for cfg in configs:
        run_idx += 1
        backend = cfg["backend"]
        num_embeddings = cfg["num_embeddings"]

        if backend == "openai":
            vs_type = cfg["vs_type"]
            pages_after = cfg["pages_after"]
            table_pages_only = cfg["table_pages_only"]

            print(f"\n[{run_idx}/{total_runs}] Running: backend=openai, vs_type={vs_type}, embeddings={num_embeddings}, pages_after={pages_after}, table_pages_only_expansion={table_pages_only}")

            # Resolve vector store info
            if VS_ID_OVERRIDE:
                vs_id = VS_ID_OVERRIDE
                chunk_index_path = CHUNK_INDEX_PATH_OVERRIDE or ""
            else:
                vs_id, chunk_index_path = _resolve_vs_info(device_dir, vs_type, None)

            if CHUNK_INDEX_PATH_OVERRIDE:
                chunk_index_path = CHUNK_INDEX_PATH_OVERRIDE

            context_retrieval_parameters = ContextRetrievalParameters(
                context_retrieval_method=DEFAULT_CONTEXT_METHOD,
                pages_after_keyword=DEFAULT_PAGES_AFTER_KEYWORD,
                remove_tables=DEFAULT_REMOVE_TABLES,
                number_embeddings=num_embeddings,
                re_ranking=DEFAULT_RE_RANKING,
                score_threshold=DEFAULT_SCORE_THRESHOLD,
                vs_id=vs_id,
                regex="",
                chunk_expansion_enabled=chunk_expansion_enabled,
                pages_after=pages_after,
                chunk_index_path=chunk_index_path,
                expand_table_pages_only=table_pages_only,
            )

            auto_prefix = _generate_output_prefix(vs_type, num_embeddings, pages_after, table_pages_only)
            if OUTPUT_PREFIX_BASE:
                output_prefix = f"{OUTPUT_PREFIX_BASE}_{auto_prefix}"
            else:
                output_prefix = auto_prefix

            output_dir = os.path.join(OUTPUT_PARENT, output_prefix)

            print(f"  VS ID: {vs_id}")
            print(f"  Chunk index: {chunk_index_path or '(none)'}")

        elif backend == "local":
            local_db_name = cfg["local_db_name"]
            keyword_boost = cfg["keyword_boost"]
            reranker_type = cfg["reranker_type"]
            metadata_filter = cfg.get("metadata_filter", False)
            pages_after = cfg.get("pages_after", 0)
            table_pages_only = cfg.get("table_pages_only", False)

            print(f"\n[{run_idx}/{total_runs}] Running: backend=local, db={local_db_name}, emb={num_embeddings}, kb={keyword_boost}, mf={metadata_filter}, pa={pages_after}")

            context_retrieval_parameters = ContextRetrievalParameters(
                context_retrieval_method=ContextRetrievalMethod.LOCAL_VECTOR_DB,
                pages_after_keyword=0,
                remove_tables=False,
                number_embeddings=num_embeddings,
                re_ranking=False,
                score_threshold=DEFAULT_SCORE_THRESHOLD,
                vs_id="",
                regex="",
                local_db_name=local_db_name,
                local_db_path=LOCAL_DB_PATH,
                keyword_boost=keyword_boost,
                reranker_type=reranker_type,
                metadata_filter_enabled=metadata_filter,
                chunk_expansion_enabled=pages_after > 0,
                pages_after=pages_after,
                chunk_index_path=LOCAL_CHUNK_INDEX_PATH if pages_after > 0 else "",
                expand_table_pages_only=table_pages_only,
            )

            auto_prefix = _generate_local_output_prefix(
                local_db_name, num_embeddings, keyword_boost, reranker_type,
                metadata_filter, pages_after, table_pages_only,
            )
            if OUTPUT_PREFIX_BASE:
                output_prefix = f"{OUTPUT_PREFIX_BASE}_{auto_prefix}"
            else:
                output_prefix = auto_prefix

            output_dir = os.path.join(LOCAL_OUTPUT_PARENT, output_prefix)

            print(f"  Local DB: {local_db_name}")
            print(f"  Keyword boost: {keyword_boost}, Metadata filter: {metadata_filter}")
            print(f"  Pages after: {pages_after}, Table pages only: {table_pages_only}")
            print(f"  Reranker: {reranker_type or '(none)'}")

        os.makedirs(output_dir, exist_ok=True)
        print(f"  Output: {output_dir}")
        if peripherals_to_run == [None]:
            print("  Peripherals: (all)")
        else:
            print(f"  Peripherals: {peripherals_to_run}")

        # Reset timing stats per run
        timing.reset()

        # Build dict for all peripherals (or None to run all)
        peripherals_registers_dict = None
        if peripherals_to_run != [None]:
            svd_file_paths = all_svd_file_paths(device_dir)
            peripherals_registers_dict = {}
            for p in peripherals_to_run:
                if p is None:
                    continue
                peripherals_registers_dict[p] = list(REGISTERS) if REGISTERS else get_register_names_for_peripheral(svd_file_paths, p)

        run_generator(
            client=client,
            model_name=MODEL_NAME,
            device_name=DEVICE_NAME,
            run_number=RUN_NUMBER,
            device_dir=device_dir,
            agent_output_dir=output_dir,
            context_retrieval_parameters=context_retrieval_parameters,
            manufacturer=manufacturer,
            peripherals_registers_dict=peripherals_registers_dict,
        )

        info_dir = os.path.join(output_dir, "info")
        os.makedirs(info_dir, exist_ok=True)
        timing.save_to_file(os.path.join(info_dir, "timing_stats.json"))

        # Run comparison across peripherals and write ONE combined set of files per configuration directory.
        if not SKIP_COMPARISON:
            compare_peripherals = [p for p in peripherals_to_run if p is not None] if peripherals_to_run != [None] else []
            if peripherals_to_run == [None]:
                print("  Warning: comparison requires explicit peripheral list; set PERIPHERALS_TO_RUN or PERIPHERAL.")

            per_peripheral: Dict[str, dict] = {}
            combined_register_results: List[dict] = []
            combined_fact_errors: List[dict] = []

            correct_sum = 0
            wrong_sum = 0
            missing_sum = 0
            total_facts_sum = 0
            correct_all_sum = 0
            wrong_all_sum = 0
            missing_all_sum = 0
            total_facts_all_sum = 0
            registers_found_sum = 0
            total_registers_sum = 0

            for peripheral_name in compare_peripherals:
                verified_csv = VERIFIED_CSV_OVERRIDE or _get_verified_csv_path(device_dir, SVD, peripheral_name)
                if not verified_csv:
                    print(f"  Warning: No verified CSV found for peripheral={peripheral_name}; skipping comparison.")
                    continue

                print(f"  Comparing peripheral={peripheral_name} against verified datasheet...")
                comparison = run_comparison(output_dir, verified_csv, peripheral_name)
                per_peripheral[peripheral_name] = {
                    "verified_csv": verified_csv,
                    "registers_found": comparison.get("registers_found"),
                    "total_registers": comparison.get("total_registers"),
                    "correct": comparison.get("correct"),
                    "wrong": comparison.get("wrong"),
                    "missing": comparison.get("missing"),
                    "total_facts": comparison.get("total_facts"),
                    "found_accuracy": comparison.get("found_accuracy"),
                    "correct_all": comparison.get("correct_all"),
                    "wrong_all": comparison.get("wrong_all"),
                    "missing_all": comparison.get("missing_all"),
                    "total_facts_all": comparison.get("total_facts_all"),
                    "complete_accuracy": comparison.get("complete_accuracy"),
                    "coverage": comparison.get("coverage"),
                }

                print(f"  Results ({peripheral_name}): {comparison['correct']}/{comparison['total_facts']} correct ({comparison['found_accuracy']:.1f}% found acc)")
                print(f"                    {comparison['registers_found']}/{comparison['total_registers']} registers found, {comparison['coverage']:.1f}% coverage")
                print(f"                    {comparison['complete_accuracy']:.1f}% complete acc, {comparison['wrong']} wrong, {comparison['missing']} missing")

                correct_sum += int(comparison.get("correct") or 0)
                wrong_sum += int(comparison.get("wrong") or 0)
                missing_sum += int(comparison.get("missing") or 0)
                total_facts_sum += int(comparison.get("total_facts") or 0)
                correct_all_sum += int(comparison.get("correct_all") or 0)
                wrong_all_sum += int(comparison.get("wrong_all") or 0)
                missing_all_sum += int(comparison.get("missing_all") or 0)
                total_facts_all_sum += int(comparison.get("total_facts_all") or 0)
                registers_found_sum += int(comparison.get("registers_found") or 0)
                total_registers_sum += int(comparison.get("total_registers") or 0)

                combined_register_results.extend(comparison.get("register_results", []))
                combined_fact_errors.extend(comparison.get("fact_errors", []))

            # Save combined comparison outputs (single file each)
            combined_found_accuracy = (correct_sum / total_facts_sum * 100.0) if total_facts_sum > 0 else None
            combined_complete_accuracy = (correct_all_sum / total_facts_all_sum * 100.0) if total_facts_all_sum > 0 else None
            combined_coverage = (total_facts_sum / total_facts_all_sum * 100.0) if total_facts_all_sum > 0 else None
            combined = {
                "peripheral_count": len(per_peripheral),
                "peripherals": sorted(per_peripheral.keys()),
                "per_peripheral": per_peripheral,
                "registers_found": registers_found_sum,
                "total_registers": total_registers_sum,
                "correct": correct_sum,
                "wrong": wrong_sum,
                "missing": missing_sum,
                "total_facts": total_facts_sum,
                "found_accuracy": combined_found_accuracy,
                "correct_all": correct_all_sum,
                "wrong_all": wrong_all_sum,
                "missing_all": missing_all_sum,
                "total_facts_all": total_facts_all_sum,
                "complete_accuracy": combined_complete_accuracy,
                "coverage": combined_coverage,
                # Legacy alias
                "accuracy": combined_found_accuracy,
                "details": {
                    # Filenames are relative to `info/`
                    "register_results_csv": "comparison_register_results.csv",
                    "fact_errors_csv": "comparison_fact_errors.csv",
                },
            }

            comparison_file = os.path.join(info_dir, "comparison_results.json")
            with open(comparison_file, "w") as f:
                json.dump(combined, f, indent=2)

            register_results_file = os.path.join(info_dir, "comparison_register_results.csv")
            with open(register_results_file, "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "peripheral",
                        "register",
                        "register_found",
                        "correct",
                        "wrong",
                        "missing",
                        "total_facts",
                        "accuracy",
                    ],
                )
                writer.writeheader()
                writer.writerows(combined_register_results)

            fact_errors_file = os.path.join(info_dir, "comparison_fact_errors.csv")
            with open(fact_errors_file, "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "error_type",
                        "peripheral",
                        "register",
                        "field_name",
                        "key",
                        "correct_value",
                        "generated_value",
                    ],
                )
                writer.writeheader()
                writer.writerows(combined_fact_errors)

            # One summary row per config (aggregated across peripherals)
            result_row = {
                "config": output_prefix,
                "backend": backend,
                "peripheral_count": len(per_peripheral),
                "peripherals": ",".join(sorted(per_peripheral.keys())),
                "embeddings": num_embeddings,
                "registers_found": registers_found_sum,
                "total_registers": total_registers_sum,
                "correct": correct_sum,
                "wrong": wrong_sum,
                "missing": missing_sum,
                "total_facts": total_facts_sum,
                "found_accuracy": combined_found_accuracy,
                "correct_all": correct_all_sum,
                "wrong_all": wrong_all_sum,
                "missing_all": missing_all_sum,
                "total_facts_all": total_facts_all_sum,
                "complete_accuracy": combined_complete_accuracy,
                "coverage": combined_coverage,
            }
            if backend == "openai":
                result_row["vs_type"] = cfg["vs_type"]
                result_row["pages_after"] = cfg["pages_after"]
                result_row["table_pages_only_expansion"] = cfg["table_pages_only"]
            elif backend == "local":
                result_row["local_db_name"] = cfg["local_db_name"]
                result_row["keyword_boost"] = cfg["keyword_boost"]
                result_row["reranker_type"] = cfg["reranker_type"]
                result_row["metadata_filter"] = cfg.get("metadata_filter", False)
                result_row["pages_after"] = cfg.get("pages_after", 0)
                result_row["table_pages_only"] = cfg.get("table_pages_only", False)
            all_results.append(result_row)

    # Print summary table
    print(f"\n{'='*70}")
    print(f"SWEEP COMPLETE: {len(configs)} configurations")
    print(f"{'='*70}")

    if all_results and not SKIP_COMPARISON:
        print(f"\nRESULTS SUMMARY:")
        print(f"{'-'*100}")
        print(f"{'Config':<30} {'Regs':>6} {'Correct':>8} {'Wrong':>6} {'Missing':>8} {'Found%':>8} {'Complete%':>10} {'Coverage%':>10}")
        print(f"{'-'*100}")
        for r in all_results:
            if 'found_accuracy' in r:
                print(f"{r['config']:<30} {r['registers_found']:>3}/{r['total_registers']:<2} {r['correct']:>8} {r['wrong']:>6} {r['missing']:>8} {r['found_accuracy']:>7.1f}% {r['complete_accuracy']:>9.1f}% {r['coverage']:>9.1f}%")
        print(f"{'-'*100}")

        # Save summary CSV - collect all unique field names across results
        all_fieldnames = []
        seen = set()
        for row in all_results:
            for k in row.keys():
                if k not in seen and k not in ("register_results", "fact_errors"):
                    all_fieldnames.append(k)
                    seen.add(k)

        # Save per-backend and combined summary CSVs
        summary_csvs = []

        # Save combined summary to the first output parent that has results
        combined_csv = os.path.join(OUTPUT_PARENT, "sweep_results.csv")
        with open(combined_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_fieldnames, extrasaction='ignore')
            writer.writeheader()
            for row in all_results:
                writer.writerow({k: row.get(k, "") for k in all_fieldnames})
        summary_csvs.append(combined_csv)

        # Also save local-only summary if there are local results
        local_results = [r for r in all_results if r.get("backend") == "local"]
        if local_results and LOCAL_OUTPUT_PARENT != OUTPUT_PARENT:
            local_csv = os.path.join(LOCAL_OUTPUT_PARENT, "sweep_results.csv")
            with open(local_csv, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=all_fieldnames, extrasaction='ignore')
                writer.writeheader()
                for row in local_results:
                    writer.writerow({k: row.get(k, "") for k in all_fieldnames})
            summary_csvs.append(local_csv)

        for csv_path in summary_csvs:
            print(f"\nSummary saved to: {csv_path}")

    print()


if __name__ == "__main__":
    main()
