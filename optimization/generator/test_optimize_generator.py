#!/usr/bin/env python3
"""
Smoke test for the optimize_generator sweep pipeline.

Exercises the generator-side knobs end-to-end on a minimal config:
  - max_fields_per_batch / max_registers_per_batch
  - skip_function_followup
  - minimal system-prompt override
Retrieval is held fixed (local ChromaDB, no OpenAI tokens). Runs on CRC
(3 registers) via Groq gpt-oss-120b.

Skips cleanly if API keys, the verified CSV, or the local DB are missing.

Usage (pytest):
    source .venv/bin/activate && pytest optimization/generator/test_optimize_generator.py -s

Usage (standalone):
    source .venv/bin/activate && python3 optimization/generator/test_optimize_generator.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    import pytest
except ImportError:
    pytest = None

import config
from defs import (
    BatchedRetrievalStrategy,
    ContextRetrievalMethod,
    ContextRetrievalParameters,
    Manufacturer,
)
from core.s1a_generator import run_generator_batched
from prompts.register_info_stm import (
    create_register_info_stm_system_prompt_batched_minimal,
)
from optimization.common.sweep_harness import run_comparison, get_verified_csv_path


DEVICE_NAME = "rm0041"
SVD = "stm32f100"
PERIPHERAL = "crc"
LOCAL_DB_NAME = "rm0041_md_chunks"
DEVICE_DIR = f"devices/stm/{DEVICE_NAME}"
VERIFIED_CSV = f"verified_datasheet/stm/{DEVICE_NAME}_{SVD}.csv"


def _skip(msg: str):
    if pytest is not None:
        pytest.skip(msg)
    print(f"SKIP: {msg}")
    sys.exit(0)


def _skip_if_missing_prereqs():
    if not os.environ.get("GROQ_API_KEY"):
        _skip("GROQ_API_KEY not set")
    if not Path(VERIFIED_CSV).exists():
        _skip(f"verified CSV missing: {VERIFIED_CSV}")
    if not (Path("databases") / LOCAL_DB_NAME).exists():
        _skip(f"local DB missing: databases/{LOCAL_DB_NAME}")


def test_optimize_generator_smoke():
    """One generator config exercising the knobs the sweep script varies."""
    _skip_if_missing_prereqs()

    context_params = ContextRetrievalParameters(
        context_retrieval_method=ContextRetrievalMethod.LOCAL_VECTOR_DB,
        pages_after_keyword=0,
        remove_tables=False,
        number_embeddings=2,
        re_ranking=False,
        score_threshold=0.0,
        vs_id="",
        regex="",
        local_db_name=LOCAL_DB_NAME,
        local_db_path="",
        keyword_boost=False,
        reranker_type="local",
        metadata_filter_enabled=True,
        chunk_expansion_enabled=False,
        pages_after=0,
        chunk_index_path="",
        expand_table_pages_only=False,
        batched_retrieval_strategy=BatchedRetrievalStrategy.PER_REGISTER_TRIMMED,
    )

    system_prompt = create_register_info_stm_system_prompt_batched_minimal(
        include_reasoning=True,
    )

    with tempfile.TemporaryDirectory(prefix="opt_gen_test_") as tmp_out:
        run_generator_batched(
            client=config.client_groq,
            model_name="gpt-oss-120b",
            device_name=DEVICE_NAME,
            run_number=1,
            device_dir=DEVICE_DIR,
            agent_output_dir=tmp_out,
            context_retrieval_parameters=context_params,
            manufacturer=Manufacturer.STM,
            peripherals_registers_dict={PERIPHERAL: ["cr", "dr", "idr"]},
            max_registers_per_batch=10,
            max_fields_per_batch=50,
            include_reasoning=True,
            skip_function_followup=True,
            system_prompt_override=system_prompt,
        )

        register_files = list(Path(tmp_out).glob(f"{PERIPHERAL}_*"))
        assert register_files, f"no register files written to {tmp_out}"

        verified_csv = get_verified_csv_path(DEVICE_DIR, SVD, PERIPHERAL)
        assert verified_csv, "verified CSV path resolution failed"

        result = run_comparison(tmp_out, verified_csv, PERIPHERAL)

        for key in (
            "registers_found", "total_registers",
            "correct", "wrong", "missing", "total_facts",
            "found_accuracy", "complete_accuracy", "coverage",
        ):
            assert key in result, f"missing key {key} in comparison result"
            assert result[key] is not None, f"{key} is None"

        assert result["registers_found"] >= 1, "no registers recovered from generator output"
        assert result["correct"] + result["wrong"] + result["missing"] == result["total_facts"]

        print(
            f"\noptimize_generator smoke: {result['registers_found']}/{result['total_registers']} regs, "
            f"{result['correct']}/{result['total_facts']} correct "
            f"({result['found_accuracy']:.1f}% found, {result['complete_accuracy']:.1f}% complete)"
        )


if __name__ == "__main__":
    test_optimize_generator_smoke()
    print("PASS")
