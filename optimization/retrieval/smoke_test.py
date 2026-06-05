#!/usr/bin/env python3
"""
Smoke tests for the evaluate_retrieval retrieval-side pipeline.

Three scenarios, all on CRC (3 registers, Groq gpt-oss-120b):

  test_smoke()                — local backend, full path: retrieve + LLM call
                                + comparison + retrieval-quality metrics.
  test_smoke_retrieval_only() — local backend, retrieval-only: skip the LLM
                                call, verify embedding_ids.jsonl is written
                                and retrieval-quality metrics still compute.
  test_smoke_openevolve()     — OpenEvolve backend, full path: exercises the
                                program-path-aware adapter, verifies OE rows
                                produce document_order rank_meaning.

Skip cleanly if API keys, the verified CSV, the local DB, or (for OE) the
chunks dir / evolved program are missing.

Usage (pytest):
    source .venv/bin/activate && pytest optimization/retrieval/smoke_test.py -s

Usage (standalone):
    source .venv/bin/activate && python3 optimization/retrieval/smoke_test.py
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
from optimization.common.sweep_harness import run_comparison, get_verified_csv_path
from optimization.retrieval.metrics_retrieval import load_db_labels, measure_run


DEVICE_NAME = "rm0041"
SVD = "stm32f100"
PERIPHERAL = "crc"
LOCAL_DB_NAME = "rm0041_md_chunks"
DEVICE_DIR = f"devices/stm/{DEVICE_NAME}"
VERIFIED_CSV = f"verified_datasheet/stm/{DEVICE_NAME}/{DEVICE_NAME}_{SVD}_full.csv"
OE_PROGRAM_PATH = f"openevolve_retrieval/output_{DEVICE_NAME}/best/best_program.py"
OE_CHUNKS_INDEX = f"chunked_datasheets/stm/{DEVICE_NAME}/chunks/md/chunks_index.csv"


def _skip(msg: str):
    if pytest is not None:
        pytest.skip(msg)
    print(f"SKIP: {msg}")
    sys.exit(0)


def _skip_if_missing_prereqs(require_groq: bool = True, require_oe: bool = False):
    if require_groq and not os.environ.get("GROQ_API_KEY"):
        _skip("GROQ_API_KEY not set")
    if not Path(VERIFIED_CSV).exists():
        _skip(f"verified CSV missing: {VERIFIED_CSV}")
    if not (Path("databases") / LOCAL_DB_NAME).exists():
        _skip(f"local DB missing: databases/{LOCAL_DB_NAME}")
    if require_oe:
        if not Path(OE_PROGRAM_PATH).exists():
            _skip(f"OE program missing: {OE_PROGRAM_PATH}")
        if not Path(OE_CHUNKS_INDEX).exists():
            _skip(f"OE chunks index missing: {OE_CHUNKS_INDEX}")


def _context_params() -> ContextRetrievalParameters:
    return ContextRetrievalParameters(
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


def _oe_context_params() -> ContextRetrievalParameters:
    return ContextRetrievalParameters(
        context_retrieval_method=ContextRetrievalMethod.OPENEVOLVE,
        pages_after_keyword=0,
        remove_tables=False,
        number_embeddings=6,        # OE retrieves 6 results internally
        re_ranking=False,
        score_threshold=0.0,
        vs_id="",
        regex="",
        oe_program_path=OE_PROGRAM_PATH,
    )


def _assert_retrieval_quality_pipeline(run_dir: Path, expected_rank_meaning: str = "relevance") -> dict:
    """Shared check: run metrics_retrieval on `run_dir` and assert the output shape.

    Args:
        expected_rank_meaning: "relevance" for normal semantic backends, or
            "document_order" for OpenEvolve (which sorts its output by page).

    Returns the quality dict so callers can print summary numbers.
    """
    sources_for_reg, _ = load_db_labels(LOCAL_DB_NAME, "")
    assert sources_for_reg, "no reg_* labels loaded from ChromaDB"

    quality = measure_run(run_dir, sources_for_reg, [1, 5])
    for key in ("queries", "overall", "per_peripheral", "per_query", "rank_meaning_breakdown"):
        assert key in quality, f"missing key {key} in retrieval-quality result"
    assert quality["queries"]["measurable"] >= 1, "no measurable queries"
    assert quality["rank_meaning_breakdown"].get(expected_rank_meaning, 0) >= 1, (
        f"expected at least one {expected_rank_meaning!r}-ranked query, got "
        f"breakdown={quality['rank_meaning_breakdown']}"
    )
    return quality


def test_smoke():
    """End-to-end: retrieve + LLM + comparison + retrieval-quality metrics."""
    _skip_if_missing_prereqs()

    with tempfile.TemporaryDirectory(prefix="evaluate_retrieval_test_") as tmp_out:
        run_generator_batched(
            client=config.client_groq,
            model_name="gpt-oss-120b",
            device_name=DEVICE_NAME,
            run_number=1,
            device_dir=DEVICE_DIR,
            agent_output_dir=tmp_out,
            context_retrieval_parameters=_context_params(),
            manufacturer=Manufacturer.STM,
            peripherals_registers_dict={PERIPHERAL: ["cr", "dr", "idr"]},
            max_fields_per_batch=50,
        )

        tmp_path = Path(tmp_out)

        # Generator should emit at least one register JSON file
        register_files = list(tmp_path.glob(f"{PERIPHERAL}_*"))
        assert register_files, f"no register files written to {tmp_out}"

        # retrieval logged its chunk IDs
        eids = tmp_path / "info" / "embedding_ids.jsonl"
        assert eids.exists() and eids.stat().st_size > 0, "embedding_ids.jsonl missing or empty"

        # Generator-side comparison
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

        # Retrieval-quality side
        quality = _assert_retrieval_quality_pipeline(tmp_path)

        print(
            f"\nevaluate_retrieval smoke: {result['registers_found']}/{result['total_registers']} regs, "
            f"{result['correct']}/{result['total_facts']} correct "
            f"({result['found_accuracy']:.1f}% found, {result['complete_accuracy']:.1f}% complete) | "
            f"retrieval recall@5={quality['overall']['recall@5']:.3f} "
            f"hit@5={quality['overall']['hit@5']:.3f}"
        )


def test_smoke_retrieval_only():
    """Retrieval-only path: no LLM call, but embedding_ids and retrieval-quality must still work."""
    _skip_if_missing_prereqs()

    with tempfile.TemporaryDirectory(prefix="ro_smoke_") as tmp_out:
        run_generator_batched(
            client=config.client_groq,
            model_name="gpt-oss-120b",
            device_name=DEVICE_NAME,
            run_number=1,
            device_dir=DEVICE_DIR,
            agent_output_dir=tmp_out,
            context_retrieval_parameters=_context_params(),
            manufacturer=Manufacturer.STM,
            peripherals_registers_dict={PERIPHERAL: ["cr", "dr", "idr"]},
            max_fields_per_batch=50,
            retrieval_only=True,
        )

        tmp_path = Path(tmp_out)

        # No register JSON files in retrieval-only mode
        register_files = list(tmp_path.glob(f"{PERIPHERAL}_*"))
        assert not register_files, f"unexpected generator output in retrieval_only mode: {register_files}"

        # But retrieval still logged its chunk IDs
        eids = tmp_path / "info" / "embedding_ids.jsonl"
        assert eids.exists() and eids.stat().st_size > 0, "embedding_ids.jsonl missing or empty"

        # Retrieval-quality computation works
        quality = _assert_retrieval_quality_pipeline(tmp_path)

        print(
            f"\nretrieval-only smoke: {quality['queries']['measurable']}/{quality['queries']['total']} "
            f"measurable, recall@5={quality['overall']['recall@5']:.3f} "
            f"hit@5={quality['overall']['hit@5']:.3f}"
        )


def test_smoke_openevolve():
    """End-to-end OpenEvolve backend: exercises the program-path-aware adapter."""
    _skip_if_missing_prereqs(require_oe=True)

    with tempfile.TemporaryDirectory(prefix="oe_smoke_") as tmp_out:
        run_generator_batched(
            client=config.client_groq,
            model_name="gpt-oss-120b",
            device_name=DEVICE_NAME,
            run_number=1,
            device_dir=DEVICE_DIR,
            agent_output_dir=tmp_out,
            context_retrieval_parameters=_oe_context_params(),
            manufacturer=Manufacturer.STM,
            peripherals_registers_dict={PERIPHERAL: ["cr", "dr", "idr"]},
            max_fields_per_batch=50,
        )

        tmp_path = Path(tmp_out)

        # Generator should emit at least one register JSON file
        register_files = list(tmp_path.glob(f"{PERIPHERAL}_*"))
        assert register_files, f"no register files written to {tmp_out}"

        # OE adapter logged its chunk IDs (with full-path chunk_ids that
        # cross-reference the persistent DB's reg_* labels)
        eids = tmp_path / "info" / "embedding_ids.jsonl"
        assert eids.exists() and eids.stat().st_size > 0, "embedding_ids.jsonl missing or empty"

        # Generator-side comparison
        verified_csv = get_verified_csv_path(DEVICE_DIR, SVD, PERIPHERAL)
        assert verified_csv, "verified CSV path resolution failed"
        result = run_comparison(tmp_out, verified_csv, PERIPHERAL)
        assert result["registers_found"] >= 1, "no registers recovered from OE+generator output"

        # Retrieval-quality side: OE sorts by document order, so MRR/precision@k
        # are nulled. recall@k / hit@k remain valid as set-membership metrics.
        quality = _assert_retrieval_quality_pipeline(tmp_path, expected_rank_meaning="document_order")
        assert quality["overall"].get("mrr") is None, "OE MRR should be None (document_order ranking)"

        print(
            f"\nopenevolve smoke: {result['registers_found']}/{result['total_registers']} regs, "
            f"{result['correct']}/{result['total_facts']} correct "
            f"({result['found_accuracy']:.1f}% found, {result['complete_accuracy']:.1f}% complete) | "
            f"retrieval recall@5={quality['overall']['recall@5']:.3f} "
            f"hit@5={quality['overall']['hit@5']:.3f} (mrr=N/A, document_order)"
        )


if __name__ == "__main__":
    test_smoke()
    test_smoke_retrieval_only()
    test_smoke_openevolve()
    print("PASS")
