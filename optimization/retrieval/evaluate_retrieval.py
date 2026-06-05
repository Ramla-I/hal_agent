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

        python3 optimization/retrieval/evaluate_retrieval.py
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
from optimization.retrieval.metrics_retrieval import (
    DEFAULT_K_CUTOFFS,
    load_db_labels,
    measure_run,
)


# Hardcoded defaults to keep the CLI small. If you want to tune these later,
# change them here (single source of truth for experiment runs).
# The OPENAI_DEFAULT_* values only apply to the OpenAI vector-store backend
# branch below; the local and OpenEvolve backends ignore them. DEFAULT_SCORE_THRESHOLD
# is shared by both the OpenAI and local branches.
OPENAI_DEFAULT_CONTEXT_METHOD = ContextRetrievalMethod.OPENAI_FILE_SEARCH
OPENAI_DEFAULT_PAGES_AFTER_KEYWORD = 2
OPENAI_DEFAULT_REMOVE_TABLES = False
OPENAI_DEFAULT_RE_RANKING = True
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

# Per-device presets — pick one with the `DEVICE` variable in main().
# Each preset bundles the four values that must change together when
# switching devices: SVD name, the peripheral list to sweep, the local
# ChromaDB collection that holds the reg_* ground-truth labels, and the
# chunks_index.csv used by local-backend page/neighbor expansion.
#
# To add a device: drop a new entry here. To override a single field for
# one run: edit DEVICE_NAME/SVD/etc. directly in main() AFTER the preset
# fields are unpacked.
DEVICE_PRESETS: Dict[str, Dict[str, object]] = {
    "rm0041": {
        "svd": "stm32f100",
        "peripherals_to_run": [
            "afio", "bkp", "cec", "crc", "dac", "exti",
            "flash", "fsmc", "iwdg", "pwr", "rcc",
        ],
        "retrieval_quality_label_db": "rm0041_md_chunks",
        "local_chunk_index": "chunked_datasheets/stm/rm0041/chunks/md/chunks_index.csv",
    },
    "ke04": {
        "svd": "mke04z4",
        "peripherals_to_run": [
            "acmp0", "acmp1", "adc", "crc", "ftm0", "ftm2", "ftmre", "gpioa",
            "i2c0", "ics", "irq", "kbi0", "kbi1", "mcm", "osc", "pit", "pmc",
            "port", "pwt", "rom", "rtc", "sim", "spi0", "uart0", "wdog",
        ],
        "retrieval_quality_label_db": "ke04_md_chunks",
        "local_chunk_index": "chunked_datasheets/nxp/ke04/chunks/md/chunks_index.csv",
    },
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
    # =====================================================================
    # SHARED PARAMETERS — apply to every backend, regardless of which
    # retrieval method(s) are enabled below.
    # =====================================================================

    # --- Device ---
    # Picks an entry from DEVICE_PRESETS (module scope). The preset supplies
    # SVD, peripheral list, local chunk index, and retrieval-quality label DB.
    # Override any unpacked field on the line below it for a one-off run.
    DEVICE = "rm0041"                          # "rm0041" or "ke04"

    if DEVICE not in DEVICE_PRESETS:
        raise ValueError(f"Unknown DEVICE={DEVICE!r}. Available: {list(DEVICE_PRESETS)}")
    _preset = DEVICE_PRESETS[DEVICE]
    DEVICE_NAME = DEVICE
    SVD = _preset["svd"]

    # --- Peripherals / registers ---
    # PERIPHERAL: run a single peripheral (leave None to use the list).
    # PERIPHERALS_TO_RUN: defaults to the preset list; override for a subset.
    PERIPHERAL: Optional[str] = None
    PERIPHERALS_TO_RUN: Optional[List[str]] = list(_preset["peripherals_to_run"])
    REGISTERS: Optional[List[str]] = None      # e.g. ["evcr", "mapr"]; None = all registers for the peripheral

    # --- Model / client ---
    CLIENT = "groq"                            # "openai" or "groq"
    MODEL_NAME = getattr(config, "GENERATOR_MODEL_NAME", "gpt-oss-120b")
    RUN_NUMBER = getattr(config, "GENERATOR_ITER", 1)

    # --- Generator mode (applies to every backend) ---
    USE_BATCHED_GENERATOR = True               # batch multiple registers per LLM call
    MAX_FIELDS_PER_BATCH = 50                  # adaptive batching: max SVD fields per batch (lower → more batches, higher accuracy for complex peripherals)
    RUN_GENERATOR = True                       # False → skip the LLM, run retrieval + retrieval-quality metrics only

    # --- Verified comparison (generator side) ---
    SKIP_COMPARISON = False
    VERIFIED_CSV_OVERRIDE: Optional[str] = None

    # --- Retrieval-quality metrics (recall@k / MRR / hit@k) ---
    RUN_RETRIEVAL_METRICS = True                       # compute per-config and join into sweep_results.csv
    RETRIEVAL_QUALITY_LABEL_DB_NAME = _preset["retrieval_quality_label_db"]   # ChromaDB collection providing reg_* ground-truth labels
    RETRIEVAL_QUALITY_K_CUTOFFS = DEFAULT_K_CUTOFFS    # k values at which to compute recall@k / precision@k / hit@k

    # --- Output naming ---
    # Per-config subdirs land inside each backend's own OUTPUT_PARENT (set in
    # the backend blocks below). The combined `sweep_results.csv` is written to
    # the first backend-parent that produced rows (see end of main()).
    OUTPUT_PREFIX_BASE: Optional[str] = None   # e.g. "my_sweep"; if set, each config becomes "<base>_<auto>"

    # =====================================================================
    # BACKEND SELECTION — enable one or more retrieval methods. The block
    # under each toggle only takes effect when that backend is enabled.
    # =====================================================================
    USE_OPENAI_VECTOR_STORE = False            # OpenAI file_search vector store
    USE_LOCAL_VECTOR_DB = False                # local ChromaDB (skip — already have E1 batched results)
    USE_OPENEVOLVE = True                      # evolved retrieval program

    # --- OpenAI vector store backend (only if USE_OPENAI_VECTOR_STORE) ---
    OPENAI_OUTPUT_PARENT = "optimization/retrieval/experiments/openai_file_search_baseline"
    VS_TYPES = ["md", "md_enriched"]                     # ["text", "md", "md_enriched"]
    EMBEDDING_COUNTS = [1, 2]                            # e.g. [4, 8, 16]
    PAGES_AFTER_VALUES = [0, 1]                          # e.g. [1, 2, 3]
    TABLE_PAGES_ONLY_EXPANSION_VALUES = [False, True]    # sweep table-only expansion on/off
    CHUNK_EXPANSION_ENABLED = True
    VS_ID_OVERRIDE: Optional[str] = None                 # bypass vector_stores.json resolution
    CHUNK_INDEX_PATH_OVERRIDE: Optional[str] = None

    # --- Local vector DB backend (only if USE_LOCAL_VECTOR_DB) ---
    LOCAL_OUTPUT_PARENT = "optimization/retrieval/experiments/e1_vs_oe_batched"
    LOCAL_DB_NAMES = ["rm0041_md_chunks"]      # ChromaDB database names to sweep
    LOCAL_EMBEDDING_COUNTS = [4]               # E1 winner: emb4+ne
    KEYWORD_BOOST_VALUES = [False]             # keyword boost on/off
    RERANKER_TYPES = ["local"]                 # "" = no reranker, "local" = FlashRank
    LOCAL_DB_PATH = ""                         # override databases directory (default: databases/)
    LOCAL_METADATA_FILTER = [True]             # filter by register name in metadata
    LOCAL_PAGES_AFTER = [0]                    # E1 winner: no page expansion
    LOCAL_TABLE_PAGES_ONLY = [False]           # only expand table-containing pages
    LOCAL_CHUNK_INDEX_PATH = _preset["local_chunk_index"]
    LOCAL_FETCH_K_MULTIPLIER = [5]             # candidate pool multiplier for reranking
    LOCAL_NEIGHBOR_EXPANSION = [True]          # E1 winner: neighbor expansion on
    BATCHED_STRATEGIES = [                     # swept only for local; needs USE_BATCHED_GENERATOR=True
        BatchedRetrievalStrategy.PER_REGISTER_TRIMMED,  # sD: per-register queries, trimmed to n_embeddings each (D2-identical)
    ]

    # --- OpenEvolve backend (only if USE_OPENEVOLVE) ---
    OE_OUTPUT_PARENT = "optimization/retrieval/experiments/oe_batched"
    # Path to the evolved best_program.py. None auto-derives from DEVICE:
    #   openevolve_retrieval/output_<DEVICE>/best/best_program.py
    # Override to evaluate a specific checkpoint or a cross-device program.
    OE_PROGRAM_PATH: Optional[str] = None
    # =====================================================================

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
        os.makedirs(OPENAI_OUTPUT_PARENT, exist_ok=True)

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
        oe_program_path = OE_PROGRAM_PATH or os.path.join(
            "openevolve_retrieval", f"output_{DEVICE_NAME}", "best", "best_program.py",
        )
        if not os.path.exists(oe_program_path):
            raise FileNotFoundError(
                f"OE program not found: {oe_program_path}. "
                f"Either evolve one for device='{DEVICE_NAME}' or set OE_PROGRAM_PATH explicitly."
            )
        configs.append({"backend": "openevolve", "oe_program_path": oe_program_path})

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

    # Load ground-truth chunk labels once (cheap; ChromaDB metadata read).
    # Cached for the duration of the sweep — every config's IR metrics use these.
    sources_for_reg = None
    if RUN_RETRIEVAL_METRICS:
        print(f"Loading retrieval-quality ground-truth labels from ChromaDB '{RETRIEVAL_QUALITY_LABEL_DB_NAME}'...")
        try:
            sources_for_reg, _ = load_db_labels(RETRIEVAL_QUALITY_LABEL_DB_NAME, "")
            print(f"  {len(sources_for_reg)} unique reg_* labels")
        except Exception as e:
            print(f"  WARN: could not load labels ({e}); retrieval-quality metrics will be skipped this sweep")
            sources_for_reg = None

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
                context_retrieval_method=OPENAI_DEFAULT_CONTEXT_METHOD,
                pages_after_keyword=OPENAI_DEFAULT_PAGES_AFTER_KEYWORD,
                remove_tables=OPENAI_DEFAULT_REMOVE_TABLES,
                number_embeddings=num_embeddings,
                re_ranking=OPENAI_DEFAULT_RE_RANKING,
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

            output_dir = os.path.join(OPENAI_OUTPUT_PARENT, output_prefix)

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
            cfg_oe_program_path = cfg["oe_program_path"]
            # Label derived from the program's grandparent dir (e.g. "output_rm0041" → "rm0041").
            oe_label = Path(cfg_oe_program_path).parts[-3].removeprefix("output_")
            print(f"\n[{run_idx}/{total_runs}] Running: backend=openevolve, program={oe_label} ({cfg_oe_program_path})")

            context_retrieval_parameters = ContextRetrievalParameters(
                context_retrieval_method=ContextRetrievalMethod.OPENEVOLVE,
                pages_after_keyword=0,
                remove_tables=False,
                number_embeddings=6,  # OE retrieves 6 results internally
                re_ranking=False,
                score_threshold=0,
                vs_id="",
                regex="",
                oe_program_path=cfg_oe_program_path,
            )

            oe_prefix = f"openevolve_{oe_label}"
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
            if not RUN_GENERATOR:
                # Retrieval-only mode: write embedding_ids.jsonl per batch but skip the LLM call.
                generator_kwargs["retrieval_only"] = True
        elif not RUN_GENERATOR:
            print("  WARN: RUN_GENERATOR=False is only supported with USE_BATCHED_GENERATOR=True; running generator anyway")
        generator_fn(**generator_kwargs)

        info_dir = os.path.join(output_dir, "info")
        os.makedirs(info_dir, exist_ok=True)
        timing.save_to_file(os.path.join(info_dir, "timing_stats.json"))

        # Run comparison across peripherals and write ONE combined set of files per configuration directory.
        if RUN_GENERATOR and not SKIP_COMPARISON:
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

            # Generator-side summary columns (populated this block only when generator ran)
            generator_cols = {
                "peripheral_count": len(per_peripheral),
                "peripherals": ",".join(sorted(per_peripheral.keys())),
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
        else:
            generator_cols = {}

        # Build the per-config row once, outside the comparison block, so retrieval-only
        # runs (RUN_GENERATOR=False or SKIP_COMPARISON=True) still produce a row with
        # backend params + IR metrics.
        result_row = {
            "config": output_prefix,
            "backend": backend,
            "embeddings": num_embeddings,
            **generator_cols,
        }
        if backend == "openai":
            result_row["vs_type"] = cfg["vs_type"]
            result_row["pages_after"] = cfg["pages_after"]
            result_row["table_pages_only_expansion"] = cfg["table_pages_only"]
        elif backend == "openevolve":
            result_row["oe_program_path"] = cfg["oe_program_path"]
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

        # Retrieval-quality metrics — joined into the same row.
        # Writes <output_dir>/info/retrieval_quality.json as a side effect of measure_run.
        if RUN_RETRIEVAL_METRICS and sources_for_reg:
            try:
                quality = measure_run(Path(output_dir), sources_for_reg, RETRIEVAL_QUALITY_K_CUTOFFS)
                # Persist the full per-query JSON for later analysis.
                with open(os.path.join(info_dir, "retrieval_quality.json"), "w") as f:
                    json.dump(quality, f, indent=2)
                # Flatten overall metrics into the result row with a `retrieval_quality_` prefix.
                for k, v in quality["overall"].items():
                    result_row[f"retrieval_quality_{k}"] = v
                result_row["retrieval_quality_measurable"] = quality["queries"]["measurable"]
                result_row["retrieval_quality_unmeasurable"] = quality["queries"]["unmeasurable"]
                result_row["retrieval_quality_rank_meaning"] = (
                    "document_order"
                    if quality["rank_meaning_breakdown"].get("document_order", 0) > 0
                    else "relevance"
                )
            except FileNotFoundError:
                # No embedding_ids.jsonl (e.g. OpenAI file_search doesn't emit one).
                pass

        all_results.append(result_row)

    # Print summary table
    print(f"\n{'='*70}")
    print(f"SWEEP COMPLETE: {len(configs)} configurations")
    print(f"{'='*70}")

    if all_results:
        # Detect which metric families are populated. Either or both may be present:
        # - generator-side: comparison ran (RUN_GENERATOR=True and SKIP_COMPARISON=False)
        # - retrieval-side: retrieval-quality metrics ran (RUN_RETRIEVAL_METRICS=True with labels loaded)
        has_generator = any("found_accuracy" in r for r in all_results)
        has_retrieval = any(
            any(k.startswith("retrieval_quality_recall@") for k in r.keys())
            for r in all_results
        )

        print(f"\nRESULTS SUMMARY:")

        if has_generator:
            print(f"{'-'*100}")
            print(f"{'Config':<30} {'Regs':>6} {'Correct':>8} {'Wrong':>6} {'Missing':>8} {'Found%':>8} {'Complete%':>10} {'Coverage%':>10}")
            print(f"{'-'*100}")
            for r in all_results:
                if "found_accuracy" in r:
                    print(f"{r['config']:<30} {r['registers_found']:>3}/{r['total_registers']:<2} {r['correct']:>8} {r['wrong']:>6} {r['missing']:>8} {r['found_accuracy']:>7.1f}% {r['complete_accuracy']:>9.1f}% {r['coverage']:>9.1f}%")
            print(f"{'-'*100}")

        if has_retrieval:
            # Pick a k cutoff to show in the print summary. Prefer 5; fall back to the
            # middle of whatever was configured. The CSV contains all k values regardless.
            display_k = 5 if 5 in RETRIEVAL_QUALITY_K_CUTOFFS else RETRIEVAL_QUALITY_K_CUTOFFS[len(RETRIEVAL_QUALITY_K_CUTOFFS) // 2]
            recall_col = f"retrieval_quality_recall@{display_k}"
            hit_col = f"retrieval_quality_hit@{display_k}"
            if has_generator:
                print()  # blank separator between the two tables
            print(f"RETRIEVAL QUALITY (k={display_k}):")
            print(f"{'-'*100}")
            print(f"{'Config':<30} {'Measurable':>11} {'recall@'+str(display_k):>10} {'hit@'+str(display_k):>8} {'MRR':>8} {'Rank':>16}")
            print(f"{'-'*100}")
            for r in all_results:
                if recall_col not in r:
                    continue
                mrr = r.get("retrieval_quality_mrr")
                mrr_str = f"{mrr:.3f}" if mrr is not None else "  N/A"
                rank_meaning = r.get("retrieval_quality_rank_meaning", "?")
                measurable = r.get("retrieval_quality_measurable", 0)
                unmeasurable = r.get("retrieval_quality_unmeasurable", 0)
                print(
                    f"{r['config']:<30} "
                    f"{measurable:>4}/{measurable + unmeasurable:<6} "
                    f"{r[recall_col]:>10.3f} {r[hit_col]:>8.3f} {mrr_str:>8} "
                    f"{rank_meaning:>16}"
                )
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

        # Save the combined summary to the first backend-parent that produced rows.
        # If multiple backends ran, the combined CSV lands in whichever parent owns the
        # first row's backend (typically the most-frequent backend in the sweep).
        backend_to_parent = {
            "openai": OPENAI_OUTPUT_PARENT,
            "local": LOCAL_OUTPUT_PARENT,
            "openevolve": OE_OUTPUT_PARENT,
        }
        primary_parent = None
        for r in all_results:
            cand = backend_to_parent.get(r.get("backend"))
            if cand:
                primary_parent = cand
                break
        if primary_parent is None:
            primary_parent = OPENAI_OUTPUT_PARENT  # fallback (no rows is already short-circuited)
        os.makedirs(primary_parent, exist_ok=True)
        combined_csv = os.path.join(primary_parent, "sweep_results.csv")
        with open(combined_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_fieldnames, extrasaction='ignore')
            writer.writeheader()
            for row in all_results:
                writer.writerow({k: row.get(k, "") for k in all_fieldnames})
        summary_csvs.append(combined_csv)

        # Also save local-only summary if there are local results
        local_results = [r for r in all_results if r.get("backend") == "local"]
        if local_results and LOCAL_OUTPUT_PARENT != primary_parent:
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
