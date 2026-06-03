"""
OpenEvolve evaluator: Score evolved retrieval pipelines against verified datasheets.

Pipeline per evaluation:
  1. Dynamically load the evolved program
  2. Build the in-memory vector DB (evolved preprocessing)
  3. For each test register, retrieve context (evolved query + search)
  4. Call the generator LLM with the retrieved context
  5. Compare generator JSON output to verified ground truth
  6. Return combined_score + feature dimensions

Uses cascade evaluation:
  - Stage 1: Run on 3 registers to quick-reject broken programs
  - Stage 2: Run on the full test set (~22 registers)
"""

import csv
import importlib.util
import json
import os
import re
import sys
import time
import traceback
from typing import Dict, List, Optional, Tuple

# Resolve paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from openai import OpenAI

# hal_agent imports for generator + comparison
from prompts.register_info_stm import (
    create_register_info_stm_system_prompt,
    create_register_info_stm_user_prompt,
)
from utils.parse_output import get_json_block_from_response, get_reasoning_from_response
from utils.generator_facts import extract_facts_from_generator_output
from optimization.common.compare_generator_with_verified import (
    load_verified_datasheet,
    compare_outputs,
    normalize_value,
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

# Test peripherals — mix of easy and hard peripherals
TEST_PERIPHERALS = ["afio", "crc", "exti", "bkp", "dac", "pwr", "rcc"]

# Stage 1 quick-check subset (3 registers for fast rejection)
STAGE1_REGISTERS = [("afio", "evcr"), ("rcc", "cr"), ("dac", "cr")]

# Generator LLM config — uses Groq (fast, cheap)
GENERATOR_MODEL = "openai/gpt-oss-120b"
GENERATOR_TIMEOUT = 30


def _get_generator_client() -> OpenAI:
    """Get the Groq client for generator LLM calls."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable not set")
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


# ---------------------------------------------------------------------------
# Verified data loading
# ---------------------------------------------------------------------------

def _get_test_registers(
    verified_facts: Dict, peripherals: List[str]
) -> List[Tuple[str, str]]:
    """Get unique (peripheral, register) pairs for the test peripherals."""
    pairs = set()
    for (p, r, f, k) in verified_facts.keys():
        if p in peripherals:
            pairs.add((p, r))
    return sorted(pairs)


def _count_facts(
    verified_facts: Dict, peripheral: str, register: str
) -> int:
    """Count verified facts for a single register."""
    return sum(1 for (p, r, _, _) in verified_facts if p == peripheral and r == register)


# ---------------------------------------------------------------------------
# Generator LLM call
# ---------------------------------------------------------------------------

def _run_generator_single(
    client: OpenAI,
    context: str,
    peripheral_name: str,
    register_name: str,
) -> Optional[Dict]:
    """Call the generator LLM with retrieved context and return parsed JSON output."""
    system_prompt = create_register_info_stm_system_prompt(
        function_calls_description=None, examples=None
    )
    user_prompt = create_register_info_stm_user_prompt(
        register_name, peripheral_name, context
    )

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
        if not text:
            return None

        _, rest = get_reasoning_from_response(text)
        json_str = get_json_block_from_response(rest)
        if json_str:
            return json.loads(json_str)
    except Exception as e:
        # LLM or parsing failure — return None (counts as missing)
        pass

    return None


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------

def _compare_single_register(
    verified_facts: Dict,
    generator_output: Optional[Dict],
    peripheral: str,
    register: str,
) -> Tuple[int, int, int]:
    """Compare generator output for one register against verified facts.

    Returns (correct, wrong, missing) counts.
    """
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


# ---------------------------------------------------------------------------
# Embedding cache pre-warming
# ---------------------------------------------------------------------------

_base_embeddings_warmed = False


def _prewarm_embedding_cache():
    """Pre-compute embeddings for raw (unmodified) chunk texts.

    Called once before the first evaluation. Populates the embedding cache
    in the initial_program module so that subsequent evaluations where
    process_chunks() doesn't modify text are nearly instant (~1s vs ~180s).
    """
    global _base_embeddings_warmed
    if _base_embeddings_warmed:
        return

    print("[evaluator] Pre-warming embedding cache for raw chunks...")

    # Ensure openevolve_retrieval dir is on path for _shared_cache import
    if _SCRIPT_DIR not in sys.path:
        sys.path.insert(0, _SCRIPT_DIR)

    spec = importlib.util.spec_from_file_location(
        "_prewarm", os.path.join(_SCRIPT_DIR, "initial_program.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    raw_chunks = mod.load_raw_chunks(CHUNKS_DIR, CHUNKS_INDEX_CSV)
    texts = [c["text"] for c in raw_chunks]
    provider = mod.get_embedding_provider()

    from _shared_cache import compute_embeddings_cached
    compute_embeddings_cached(texts, provider)
    _base_embeddings_warmed = True
    print(f"[evaluator] Cached {len(texts)} base embeddings")


# ---------------------------------------------------------------------------
# Main evaluation function
# ---------------------------------------------------------------------------


def _fail_result(error: str) -> Dict:
    """Return a zero-score result with all required feature dimensions."""
    return {
        "combined_score": 0.0,
        "error": error,
        "avg_context_length": 0,
        "retrieval_time": 0.0,
    }


def evaluate(program_path: str) -> Dict:
    """Evaluate an evolved retrieval program.

    Args:
        program_path: Path to the evolved initial_program.py

    Returns:
        Dict with combined_score and feature dimensions.
    """
    # Pre-warm embedding cache on first call (~180s one-time cost)
    _prewarm_embedding_cache()

    t_start = time.time()

    # Load the evolved module
    try:
        spec = importlib.util.spec_from_file_location("evolved_program", program_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        return _fail_result(f"Import failed: {e}")

    # Load verified facts
    verified_facts = load_verified_datasheet(VERIFIED_CSV)

    # --- Stage 1: Quick validation on 3 registers ---
    try:
        t_db_start = time.time()
        collection, processed_chunks = mod.setup_database(CHUNKS_DIR, CHUNKS_INDEX_CSV)
        db_build_time = time.time() - t_db_start
    except Exception as e:
        return _fail_result(f"setup_database() failed: {traceback.format_exc()}")

    # Quick test: can it retrieve anything?
    stage1_ok = 0
    for peripheral, register in STAGE1_REGISTERS:
        try:
            ctx = mod.run_retrieval(peripheral, register, collection, processed_chunks)
            if ctx and len(ctx) > 50:
                stage1_ok += 1
        except Exception:
            pass

    if stage1_ok == 0:
        return _fail_result("Stage 1 failed: no context retrieved for any test register")

    # --- Stage 2: Full evaluation ---
    client = _get_generator_client()
    test_registers = _get_test_registers(verified_facts, TEST_PERIPHERALS)

    # Per-register tracking for found vs complete metrics
    found_correct = 0
    found_wrong = 0
    found_missing = 0
    not_found_facts = 0
    retrieval_time = 0.0
    generator_time = 0.0
    context_lengths = []
    registers_found = 0

    for peripheral, register in test_registers:
        # Retrieve context
        try:
            t0 = time.time()
            context = mod.run_retrieval(
                peripheral, register, collection, processed_chunks
            )
            retrieval_time += time.time() - t0
        except Exception:
            context = None

        reg_fact_count = _count_facts(verified_facts, peripheral, register)

        if not context or len(context) < 20:
            not_found_facts += reg_fact_count
            continue

        context_lengths.append(len(context))

        # Run generator LLM
        t1 = time.time()
        gen_output = _run_generator_single(client, context, peripheral, register)
        generator_time += time.time() - t1

        if gen_output is None:
            not_found_facts += reg_fact_count
            continue

        registers_found += 1

        # Compare
        c, w, m = _compare_single_register(
            verified_facts, gen_output, peripheral, register
        )
        found_correct += c
        found_wrong += w
        found_missing += m

    # --- Compute scores ---
    total_registers = len(test_registers)

    # Found-register metrics (only registers that produced output)
    found_total = found_correct + found_wrong + found_missing
    found_accuracy = (found_correct / found_total) if found_total > 0 else 0.0

    # Complete metrics (all registers — not-found registers count as all-missing)
    complete_total = found_total + not_found_facts
    if complete_total == 0:
        return _fail_result("No facts to evaluate")

    complete_accuracy = found_correct / complete_total
    error_rate = found_wrong / complete_total

    # Coverage: fraction of verified facts from found registers vs total
    fact_coverage = found_total / complete_total if complete_total > 0 else 0.0

    # Primary score: accuracy with extra penalty for wrong facts
    combined_score = complete_accuracy - (error_rate * 0.5)
    combined_score = max(0.0, min(1.0, combined_score))

    avg_context_len = (
        sum(context_lengths) / len(context_lengths) if context_lengths else 0
    )
    total_time = time.time() - t_start

    return {
        "combined_score": combined_score,
        # Found-register metrics (matching sweep's found_accuracy)
        "found_accuracy": found_accuracy,
        "found_correct": found_correct,
        "found_wrong": found_wrong,
        "found_missing": found_missing,
        "found_total": found_total,
        # Complete metrics (matching sweep's complete_accuracy)
        "complete_accuracy": complete_accuracy,
        "complete_total": complete_total,
        # Register-level coverage (matching sweep's registers_found/total_registers)
        "registers_found": registers_found,
        "total_registers": total_registers,
        # Fact-level coverage (matching sweep's coverage)
        "fact_coverage": fact_coverage,
        # Feature dimensions for MAP-Elites diversity
        "avg_context_length": avg_context_len,
        "retrieval_time": retrieval_time,
        # Timing
        "db_build_time": db_build_time,
        "generator_time": generator_time,
        "total_time": total_time,
    }
