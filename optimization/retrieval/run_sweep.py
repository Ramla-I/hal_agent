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

        python3 optimization/retrieval/run_sweep.py
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import config
from defs import ContextRetrievalParameters, ContextRetrievalMethod, Manufacturer, BatchedRetrievalStrategy
from agent_tools.tools import all_svd_file_paths
from agent_tools.svd_parsing import get_register_names_for_peripheral
from core.s1a_generator import run_generator, run_generator_batched
from utils.timing import get_timing_stats
from utils.vector_store_config import get_vector_stores
from optimization.common.sweep_harness import (
    get_user_context,
    get_verified_csv_path,
    get_verified_registers,
    run_comparison,
)


# Hardcoded defaults to keep the CLI small. If you want to tune these later,
# change them here (single source of truth for experiment runs).
DEFAULT_CONTEXT_METHOD = ContextRetrievalMethod.OPENAI_FILE_SEARCH
DEFAULT_PAGES_AFTER_KEYWORD = 2
DEFAULT_REMOVE_TABLES = False
DEFAULT_RE_RANKING = True
DEFAULT_SCORE_THRESHOLD = 0.25

# Short labels for batched retrieval strategies (used in output folder names)
STRATEGY_LABELS = {
    BatchedRetrievalStrategy.COMBINED_WITH_FILTER: "sA",
    BatchedRetrievalStrategy.COMBINED_NO_FILTER: "sB",
    BatchedRetrievalStrategy.PER_REGISTER: "sC",
    BatchedRetrievalStrategy.PER_REGISTER_TRIMMED: "sD",
}

# Mapping from CLI short names to vector_stores.json keys
VS_TYPE_MAPPING = {
    "text": "openai_text_chunks",
    "md": "openai_md_chunks",
    "md_enriched": "openai_md_enriched",
}


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
        store_key = vs_config.default or "openai_md_chunks"

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
    batched_strategy: str = "", max_fields_per_batch: int = 0,
    fetch_k_multiplier: int = 5, neighbor_expansion: bool = False,
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
    if fetch_k_multiplier != 5:
        parts.append(f"fk{fetch_k_multiplier}")
    if neighbor_expansion:
        parts.append("ne")
    if batched_strategy:
        parts.append(batched_strategy)
    if max_fields_per_batch > 0:
        parts.append(f"mfpb{max_fields_per_batch}")
    return "_".join(parts)


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
    USE_LOCAL_VECTOR_DB = False                # Skip — already have E1 batched results
    LOCAL_DB_NAMES = ["rm0041_md_chunks"]        # ChromaDB database names to sweep
    LOCAL_EMBEDDING_COUNTS = [4]                  # E1 winner: emb4+ne
    KEYWORD_BOOST_VALUES = [False]        # Keyword boost on/off
    RERANKER_TYPES = ["local"]                  # "" = no reranker, "local" = FlashRank
    LOCAL_DB_PATH = ""                          # Override databases directory (default: databases/)
    # Enriched local DB features
    LOCAL_METADATA_FILTER = [True]               # Filter by register name in metadata
    LOCAL_PAGES_AFTER = [0]                       # E1 winner: no page expansion
    LOCAL_TABLE_PAGES_ONLY = [False]             # Only expand table-containing pages
    LOCAL_CHUNK_INDEX_PATH = "chunked_datasheets/stm/rm0041/chunks/md/chunks_index.csv"
    LOCAL_FETCH_K_MULTIPLIER = [5]               # Candidate pool multiplier for reranking
    LOCAL_NEIGHBOR_EXPANSION = [True]             # E1 winner: neighbor expansion on

    # OpenEvolve retrieval
    USE_OPENEVOLVE = True                         # Include OE retrieval config
    OE_OUTPUT_PARENT = "optimization/retrieval/experiments/oe_batched"

    # Batched generator settings
    USE_BATCHED_GENERATOR = True
    MAX_FIELDS_PER_BATCH = 50                 # Adaptive batching: max SVD fields per batch (lower → more batches, higher accuracy for complex peripherals)
    BATCHED_STRATEGIES = [                    # Only relevant when USE_BATCHED_GENERATOR=True
        BatchedRetrievalStrategy.PER_REGISTER_TRIMMED,  # sD: per-register queries, trimmed to n_embeddings each (D2-identical)
    ]

    # Output
    # OpenAI experiments go to openai_file_search_baseline/, local to post_batched_strategy_sweep/
    OUTPUT_PARENT = "optimization/retrieval/experiments/openai_file_search_baseline"
    LOCAL_OUTPUT_PARENT = "optimization/retrieval/experiments/e1_vs_oe_batched"
    OUTPUT_PREFIX_BASE: Optional[str] = None   # e.g. "my_sweep"; if set, each config becomes "<base>_<auto>"

    # Verified comparison
    SKIP_COMPARISON = False
    VERIFIED_CSV_OVERRIDE: Optional[str] = None
    # =========================

    ctx = get_user_context(DEVICE_NAME)
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
        # When batched generator is enabled, wrap configs in a strategy loop
        strategies_to_sweep = BATCHED_STRATEGIES if USE_BATCHED_GENERATOR else [None]
        for strategy in strategies_to_sweep:
            for local_db in LOCAL_DB_NAMES:
                for num_embeddings in LOCAL_EMBEDDING_COUNTS:
                    for kb in KEYWORD_BOOST_VALUES:
                        for rt in RERANKER_TYPES:
                            for mf in LOCAL_METADATA_FILTER:
                                for pa in LOCAL_PAGES_AFTER:
                                    for tpo in LOCAL_TABLE_PAGES_ONLY:
                                        for fkm in LOCAL_FETCH_K_MULTIPLIER:
                                            for ne in LOCAL_NEIGHBOR_EXPANSION:
                                                cfg_entry = {
                                                    "backend": "local",
                                                    "local_db_name": local_db,
                                                    "num_embeddings": num_embeddings,
                                                    "keyword_boost": kb,
                                                    "reranker_type": rt,
                                                    "metadata_filter": mf,
                                                    "pages_after": pa,
                                                    "table_pages_only": tpo,
                                                    "fetch_k_multiplier": fkm,
                                                    "neighbor_expansion": ne,
                                                }
                                                if strategy is not None:
                                                    cfg_entry["batched_strategy"] = strategy
                                                configs.append(cfg_entry)

    # OpenEvolve retrieval configs
    if USE_OPENEVOLVE:
        os.makedirs(OE_OUTPUT_PARENT, exist_ok=True)
        configs.append({"backend": "openevolve"})

    openai_count = sum(1 for c in configs if c["backend"] == "openai")
    local_count = sum(1 for c in configs if c["backend"] == "local")
    oe_count = sum(1 for c in configs if c["backend"] == "openevolve")

    print(f"\n{'='*70}")
    print(f"GENERATOR EXPERIMENT SWEEP")
    print(f"{'='*70}")
    print(f"Device: {DEVICE_NAME}")
    if peripherals_to_run == [None]:
        print("Peripherals: (all)")
    else:
        print(f"Peripherals: {peripherals_to_run}")
    print(f"Configurations to run: {len(configs)} ({openai_count} OpenAI, {local_count} local, {oe_count} OE)")
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
        print(f"  Fetch K multiplier: {LOCAL_FETCH_K_MULTIPLIER}")
        print(f"  Neighbor expansion: {LOCAL_NEIGHBOR_EXPANSION}")
    if USE_BATCHED_GENERATOR:
        print(f"  Batched generator: ENABLED")
        print(f"  Max fields per batch: {MAX_FIELDS_PER_BATCH}")
        print(f"  Batched strategies: {[STRATEGY_LABELS[s] for s in BATCHED_STRATEGIES]}")
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
        num_embeddings = cfg.get("num_embeddings", 0)

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
            batched_strategy = cfg.get("batched_strategy")  # None when not batched

            fetch_k_multiplier = cfg.get("fetch_k_multiplier", 5)
            neighbor_expansion = cfg.get("neighbor_expansion", False)
            strategy_label = STRATEGY_LABELS.get(batched_strategy, "") if batched_strategy else ""
            print(f"\n[{run_idx}/{total_runs}] Running: backend=local, db={local_db_name}, emb={num_embeddings}, kb={keyword_boost}, mf={metadata_filter}, pa={pages_after}, ne={neighbor_expansion}"
                  + (f", fkm={fetch_k_multiplier}" if fetch_k_multiplier != 5 else "")
                  + (f", strategy={strategy_label}" if strategy_label else ""))

            # Chunk index needed for page expansion OR neighbor expansion
            needs_chunk_index = pages_after > 0 or neighbor_expansion

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
                chunk_index_path=LOCAL_CHUNK_INDEX_PATH if needs_chunk_index else "",
                expand_table_pages_only=table_pages_only,
                fetch_k_multiplier=fetch_k_multiplier,
                neighbor_expansion_enabled=neighbor_expansion,
                **({"batched_retrieval_strategy": batched_strategy} if batched_strategy else {}),
            )

            auto_prefix = _generate_local_output_prefix(
                local_db_name, num_embeddings, keyword_boost, reranker_type,
                metadata_filter, pages_after, table_pages_only,
                batched_strategy=strategy_label,
                max_fields_per_batch=MAX_FIELDS_PER_BATCH if USE_BATCHED_GENERATOR else 0,
                fetch_k_multiplier=fetch_k_multiplier,
                neighbor_expansion=neighbor_expansion,
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
            if fetch_k_multiplier != 5:
                print(f"  Fetch K multiplier: {fetch_k_multiplier}")
            if neighbor_expansion:
                print(f"  Neighbor expansion: {neighbor_expansion}")
            if strategy_label:
                print(f"  Batched strategy: {strategy_label} ({batched_strategy.value})")

        elif backend == "openevolve":
            print(f"\n[{run_idx}/{total_runs}] Running: backend=openevolve")

            context_retrieval_parameters = ContextRetrievalParameters(
                context_retrieval_method=ContextRetrievalMethod.OPENEVOLVE,
                pages_after_keyword=0,
                remove_tables=False,
                number_embeddings=6,  # OE retrieves 6 results internally
                re_ranking=False,
                score_threshold=0,
                vs_id="",
                regex="",
            )

            oe_prefix = "openevolve"
            if USE_BATCHED_GENERATOR:
                oe_prefix += f"_batched_mfpb{MAX_FIELDS_PER_BATCH}"
            else:
                oe_prefix += "_unbatched"
            output_prefix = oe_prefix
            output_dir = os.path.join(OE_OUTPUT_PARENT, output_prefix)

        os.makedirs(output_dir, exist_ok=True)
        print(f"  Output: {output_dir}")
        if peripherals_to_run == [None]:
            print("  Peripherals: (all)")
        else:
            print(f"  Peripherals: {peripherals_to_run}")

        # Reset timing stats per run
        timing.reset()

        # Build dict for all peripherals — prefer verified CSV registers over SVD
        # to avoid wasting LLM calls on registers we can't evaluate (e.g. BKP_DR21..DR42)
        peripherals_registers_dict = None
        if peripherals_to_run != [None]:
            peripherals_registers_dict = {}
            for p in peripherals_to_run:
                if p is None:
                    continue
                if REGISTERS:
                    peripherals_registers_dict[p] = list(REGISTERS)
                else:
                    verified_csv = VERIFIED_CSV_OVERRIDE or get_verified_csv_path(device_dir, SVD, p)
                    if verified_csv:
                        verified_regs = get_verified_registers(verified_csv, p)
                        if verified_regs:
                            peripherals_registers_dict[p] = verified_regs
                            continue
                    # Fall back to SVD if no verified CSV
                    svd_file_paths = all_svd_file_paths(device_dir)
                    peripherals_registers_dict[p] = get_register_names_for_peripheral(svd_file_paths, p)

        generator_fn = run_generator_batched if USE_BATCHED_GENERATOR else run_generator
        generator_kwargs = dict(
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
        if USE_BATCHED_GENERATOR:
            generator_kwargs["max_fields_per_batch"] = MAX_FIELDS_PER_BATCH
        generator_fn(**generator_kwargs)

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
                verified_csv = VERIFIED_CSV_OVERRIDE or get_verified_csv_path(device_dir, SVD, peripheral_name)
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
                result_row["fetch_k_multiplier"] = cfg.get("fetch_k_multiplier", 5)
                result_row["neighbor_expansion"] = cfg.get("neighbor_expansion", False)
                bs = cfg.get("batched_strategy")
                result_row["batched_strategy"] = STRATEGY_LABELS.get(bs, "") if bs else ""
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
