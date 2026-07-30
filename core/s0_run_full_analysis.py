#!/usr/bin/env python3
"""
Multi-device pipeline for extracting hardware register information from datasheets.

Steps:
  1. Preprocess — chunk + enrich + ingest into local ChromaDB (skips if DB exists)
  2. Generator — extract register info from datasheet using LLMs
  3. Coverage Improver — iteratively improve coverage based on SVD comparison
  4. Validator — validate extracted info against the datasheet
  5. Evaluation — compare with SVD files, run analyzer, generate diff tables

Usage:
    # Run all steps for all configured devices
    python core/s0_run_full_analysis.py

    # Single device, skip preprocessing
    python core/s0_run_full_analysis.py --devices rm0041 --skip-preprocessing

    # Multiple devices in parallel
    python core/s0_run_full_analysis.py --devices rm0041 rm0008 --max-workers 2

    # Skip expensive steps
    python core/s0_run_full_analysis.py --devices rm0041 --coverage-improver-iterations 0 --skip-validator
"""

import argparse
import glob
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

# Ensure repo root and core/ are both on sys.path so that
# `import config`, `from scripts.X import ...`, and sibling
# `from s1a_generator import ...` all resolve correctly.
_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_CORE_DIR)
for _p in (_REPO_ROOT, _CORE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config
from config import client_openai, client_groq
from defs import (
    ContextRetrievalMethod,
    ContextRetrievalParameters,
    CoverageImproverOutput,
    UserContext,
)
from groq import Groq
from openai import OpenAI

# Lazy imports for heavy modules — only loaded when actually needed.
# Generator, coverage improver, validator, analyzer, and evaluation scripts
# are imported inside the functions that use them.


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DevicePaths:
    """All resolved filesystem paths for a device pipeline run."""
    device_name: str
    manufacturer: str  # lowercase, e.g. "stm"
    run_number: int

    device_dir: str      # devices/{mfg}/{device}/
    svd_dir: str         # devices/{mfg}/{device}/svd/
    pdf_path: str        # devices/{mfg}/{device}/{device}.pdf

    agent_output_dir: str   # agent_output/{mfg}/{device}/{run}/
    results_dir: str        # evaluation/{mfg}/{device}/{run}/
    verified_dir: str       # verified_datasheet/


@dataclass
class DeviceResult:
    """Summary of pipeline results for one device."""
    device_name: str
    success: bool = True
    error: str = ""

    # Step 1 — preprocessing
    preprocessing_done: bool = False
    chunks_created: int = 0

    # Step 2 — generator
    generator_done: bool = False
    truncated: bool = False

    # Step 3 — coverage improver
    coverage_iterations: int = 0
    final_run_number: int = 0

    # Step 4 — validator
    validator_done: bool = False
    true_count: int = 0
    false_count: int = 0

    # Step 5 — evaluation / bug finding
    evaluation_done: bool = False
    svd_files_compared: int = 0
    analyzer_used: bool = False
    bug_candidates: int = 0
    auto_fp: int = 0

    # Run metadata (for the manifest)
    retrieval_method: str = ""
    generator_models: list = field(default_factory=list)

    # Step 6 — constraint validation (v2 grammar)
    constraint_validation_done: bool = False
    constraints_extracted: int = 0
    constraints_anchored: int = 0
    constraints_confirmed: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def determine_client(model_name: str) -> Groq | OpenAI:
    """Route to Groq or OpenAI based on model name."""
    return client_groq if model_name == "gpt-oss-120b" else client_openai


def resolve_run_number(repo_root: str, ctx: UserContext, new_run: bool = False) -> int:
    """Resolve the run number for a device under agent_output/{mfg}/{device}/.

    Default is to **resume the latest existing run** (the generator skips
    registers whose output already exists, so an interrupted run continues into
    the same directory). With ``new_run=True`` a fresh run (max + 1) is started.
    Returns 1 when no run exists yet.
    """
    output_base = os.path.join(
        repo_root,
        config.OUTPUT_DIR,
        ctx.manufacturer.value.lower(),
        ctx.device_name,
    )
    if not os.path.isdir(output_base):
        return 1
    existing = [
        int(d)
        for d in os.listdir(output_base)
        if d.isdigit() and os.path.isdir(os.path.join(output_base, d))
    ]
    if not existing:
        return 1
    return max(existing) + 1 if new_run else max(existing)


def resolve_device_paths(
    ctx: UserContext,
    repo_root: str,
    run_number: int,
) -> DevicePaths:
    """Build a DevicePaths dataclass from UserContext and run number. No I/O."""
    mfg = ctx.manufacturer.value.lower()
    device_dir = os.path.join(repo_root, config.DEVICE_DIRECTORY, mfg, ctx.device_name)
    return DevicePaths(
        device_name=ctx.device_name,
        manufacturer=mfg,
        run_number=run_number,
        device_dir=device_dir,
        svd_dir=os.path.join(device_dir, "svd"),
        pdf_path=os.path.join(device_dir, f"{ctx.device_name}.pdf"),
        agent_output_dir=os.path.join(repo_root, config.OUTPUT_DIR, mfg, ctx.device_name, str(run_number)),
        results_dir=os.path.join(repo_root, config.RESULTS_DIR, mfg, ctx.device_name, str(run_number)),
        verified_dir=os.path.join(repo_root, "verified_datasheet"),
    )


def build_context_retrieval_params(
    device_dir: str,
    device_ctx: UserContext,
) -> ContextRetrievalParameters:
    """Resolve ContextRetrievalParameters for a device.

    Priority:
      1. vector_stores.json → local DB entry → LOCAL_VECTOR_DB params
      2. vector_stores.json → OpenAI entry → OPENAI_FILE_SEARCH params
      3. UserContext.vs_id → OPENAI_FILE_SEARCH params
      4. Fallback → KEYWORD_SEARCH params
    """
    from utils.vector_store_config import get_vector_stores

    try:
        vs_config = get_vector_stores(device_dir, use_cache=False)
    except FileNotFoundError:
        vs_config = None

    # 1. Check for local vector DB in vector_stores.json (prefer default entry)
    if vs_config:
        # Check default entry first, then iterate remaining
        check_order = []
        if vs_config.default:
            check_order.append(vs_config.default)
        for name in vs_config.list_all():
            if name not in check_order:
                check_order.append(name)

        for name in check_order:
            vs_info = vs_config.get(name)
            if vs_info and vs_info.is_local and vs_info.local_db_name:
                chunk_index_path = vs_config.get_chunk_index_path(name) or ""
                return ContextRetrievalParameters(
                    context_retrieval_method=ContextRetrievalMethod.LOCAL_VECTOR_DB,
                    pages_after_keyword=0,
                    remove_tables=False,
                    number_embeddings=config.CONTEXT_RETRIEVAL_PARAMETERS.number_embeddings,
                    re_ranking=config.CONTEXT_RETRIEVAL_PARAMETERS.re_ranking,
                    score_threshold=config.CONTEXT_RETRIEVAL_PARAMETERS.score_threshold,
                    vs_id="",
                    regex="",
                    local_db_name=vs_info.local_db_name,
                    local_db_path="",  # use default databases/ directory
                    chunk_index_path=chunk_index_path,
                    chunk_expansion_enabled=config.CONTEXT_RETRIEVAL_PARAMETERS.chunk_expansion_enabled,
                    pages_after=config.CONTEXT_RETRIEVAL_PARAMETERS.pages_after,
                    keyword_boost=config.CONTEXT_RETRIEVAL_PARAMETERS.keyword_boost,
                    reranker_type=config.CONTEXT_RETRIEVAL_PARAMETERS.reranker_type,
                    metadata_filter_enabled=config.CONTEXT_RETRIEVAL_PARAMETERS.metadata_filter_enabled,
                )

        # 2. Check for OpenAI vector store entry
        default_vs = vs_config.get_default()
        if default_vs and default_vs.vs_id:
            chunk_index_path = vs_config.get_chunk_index_path(vs_config.default) or ""
            return ContextRetrievalParameters(
                context_retrieval_method=ContextRetrievalMethod.OPENAI_FILE_SEARCH,
                pages_after_keyword=config.CONTEXT_RETRIEVAL_PARAMETERS.pages_after_keyword,
                remove_tables=config.CONTEXT_RETRIEVAL_PARAMETERS.remove_tables,
                number_embeddings=config.CONTEXT_RETRIEVAL_PARAMETERS.number_embeddings,
                re_ranking=config.CONTEXT_RETRIEVAL_PARAMETERS.re_ranking,
                score_threshold=config.CONTEXT_RETRIEVAL_PARAMETERS.score_threshold,
                vs_id=default_vs.vs_id,
                regex="",
                chunk_index_path=chunk_index_path,
                chunk_expansion_enabled=config.CONTEXT_RETRIEVAL_PARAMETERS.chunk_expansion_enabled,
                pages_after=config.CONTEXT_RETRIEVAL_PARAMETERS.pages_after,
            )

    # 3. Fallback to UserContext.vs_id
    if device_ctx.vs_id:
        return ContextRetrievalParameters(
            context_retrieval_method=ContextRetrievalMethod.OPENAI_FILE_SEARCH,
            pages_after_keyword=config.CONTEXT_RETRIEVAL_PARAMETERS.pages_after_keyword,
            remove_tables=config.CONTEXT_RETRIEVAL_PARAMETERS.remove_tables,
            number_embeddings=config.CONTEXT_RETRIEVAL_PARAMETERS.number_embeddings,
            re_ranking=config.CONTEXT_RETRIEVAL_PARAMETERS.re_ranking,
            score_threshold=config.CONTEXT_RETRIEVAL_PARAMETERS.score_threshold,
            vs_id=device_ctx.vs_id,
            regex="",
            chunk_expansion_enabled=config.CONTEXT_RETRIEVAL_PARAMETERS.chunk_expansion_enabled,
            pages_after=config.CONTEXT_RETRIEVAL_PARAMETERS.pages_after,
        )

    # 4. Last resort: keyword search
    return ContextRetrievalParameters(
        context_retrieval_method=ContextRetrievalMethod.KEYWORD_SEARCH,
        pages_after_keyword=config.CONTEXT_RETRIEVAL_PARAMETERS.pages_after_keyword,
        remove_tables=config.CONTEXT_RETRIEVAL_PARAMETERS.remove_tables,
        number_embeddings=config.CONTEXT_RETRIEVAL_PARAMETERS.number_embeddings,
        re_ranking=config.CONTEXT_RETRIEVAL_PARAMETERS.re_ranking,
        score_threshold=config.CONTEXT_RETRIEVAL_PARAMETERS.score_threshold,
        vs_id="",
        regex="",
    )


# Per-vendor reference OpenEvolve program, used when a device has no evolution of
# its own (NXP short-name retrieval differs enough that the STM program is a poor
# fallback — ke04 is the NXP reference, mirroring the vendor-default validator card).
_VENDOR_OE_DEFAULT = {"nxp": "output_ke04", "stm": "output_rm0041"}


def resolve_openevolve_program(device_name: str, repo_root: str, manufacturer=None) -> str:
    """Path to the device's evolved OpenEvolve best_program.py.

    Device-specific evolution if present; else the vendor's reference program
    (NXP -> ke04, STM -> rm0041); else rm0041.
    """
    def _prog(subdir):
        return os.path.join(repo_root, "openevolve_retrieval", subdir, "best", "best_program.py")

    device_specific = _prog(f"output_{device_name}")
    if os.path.exists(device_specific):
        return device_specific
    vendor = getattr(manufacturer, "value", "").lower() if manufacturer is not None else ""
    vendor_default = _prog(_VENDOR_OE_DEFAULT.get(vendor, "output_rm0041"))
    if os.path.exists(vendor_default):
        return vendor_default
    return _prog("output_rm0041")


def apply_retrieval_override(
    cr_params: ContextRetrievalParameters,
    retrieval: str,
    device_name: str,
    repo_root: str,
    manufacturer=None,
) -> ContextRetrievalParameters:
    """Override auto-resolved retrieval params when an explicit method is requested.

    ``auto`` (default) keeps whatever build_context_retrieval_params resolved
    (local vector DB / OpenAI / keyword). ``openevolve`` switches to the evolved
    STM retrieval program.
    """
    if retrieval in (None, "auto"):
        return cr_params
    if retrieval == "openevolve":
        program = resolve_openevolve_program(device_name, repo_root, manufacturer)
        if not os.path.exists(program):
            raise FileNotFoundError(f"OpenEvolve program not found: {program}")
        return ContextRetrievalParameters(
            context_retrieval_method=ContextRetrievalMethod.OPENEVOLVE,
            pages_after_keyword=0,
            remove_tables=False,
            number_embeddings=config.CONTEXT_RETRIEVAL_PARAMETERS.number_embeddings,
            re_ranking=False,
            score_threshold=0.0,
            vs_id="",
            regex="",
            oe_program_path=program,
        )
    raise ValueError(f"Unsupported --retrieval value: {retrieval!r}")


# ---------------------------------------------------------------------------
# Step 1: Preprocessing
# ---------------------------------------------------------------------------

def preprocess_device(
    paths: DevicePaths,
    fmt: str = "markdown",
    embed_metadata: bool = True,
    max_tokens: int = 800,
    overlap_tokens: int = 100,
) -> tuple[bool, int]:
    """Chunk + enrich + augment + ingest into local ChromaDB.

    Returns (done, chunks_created). Skips if the DB already exists.
    """
    from context_retrieval.preprocessing.pipeline import (
        run_chunking,
        run_enrichment,
        run_augmentation,
        run_local_ingestion,
    )

    db_name = f"{paths.device_name}_md_chunks"

    # Check if DB already exists (lazy import to avoid pulling in chromadb early)
    try:
        from context_retrieval.vector_db.vector_store import database_exists
        if database_exists(db_name):
            print(f"  [preprocessing] Local DB '{db_name}' already exists — skipping")
            return True, 0
    except Exception:
        pass  # vector_db not available; proceed with ingestion

    if not os.path.exists(paths.pdf_path):
        print(f"  [preprocessing] PDF not found: {paths.pdf_path} — skipping")
        return False, 0

    format_subdir = "md" if fmt == "markdown" else "text"
    base_output_dir = os.path.join(paths.device_dir, "chunks")
    chunks_dir = os.path.join(base_output_dir, format_subdir)
    metadata_dir = chunks_dir
    file_extension = ".txt"

    # Step 1: Chunk
    chunk_metadata = run_chunking(
        paths.pdf_path, chunks_dir, paths.device_name,
        max_tokens, overlap_tokens, fmt,
    )

    # Step 2: Enrich
    run_enrichment(chunks_dir, metadata_dir, file_extension)

    # Step 3: Augment (optional)
    upload_dir = chunks_dir
    if embed_metadata:
        augmented_dir = os.path.join(base_output_dir, f"{format_subdir}_enriched")
        run_augmentation(chunks_dir, metadata_dir, augmented_dir, file_extension)
        upload_dir = augmented_dir

    # Step 4: Ingest into local ChromaDB
    result = run_local_ingestion(
        chunks_dir=upload_dir,
        metadata_dir=metadata_dir,
        device_name=paths.device_name,
        device_dir=paths.device_dir,
        db_name=db_name,
        embedding_provider="local",
        entry_name=f"local_{format_subdir}_chunks",
    )
    if result != 0:
        print(f"  [preprocessing] Local ingestion failed for {paths.device_name}")
        return False, 0

    return True, len(chunk_metadata)


# ---------------------------------------------------------------------------
# Steps 2-5: Per-device pipeline
# ---------------------------------------------------------------------------

def run_constraint_validation_phase(
    run_dir: str,
    reference_manual: str,
    chunks_root: str,
    svd_dir=None,
    judge_model: str = "openai/gpt-oss-120b",
    batch_size: int = 1,
    min_confidence: float = 0.0,
) -> dict:
    """Step 6: the CHAINED grammar-v2 constraint stage on a fresh generator run.

    generator run -> collect_constraints (lint + enforceability, in-memory, no
    payload files) -> anchor the LINTED set -> closed-book LLM judge -> one
    ``validated.jsonl`` (+ ``anchors.jsonl`` / ``judgments.jsonl`` /
    ``manifest.json`` / ``summary.json``) under
    ``<run_dir>/constraint_validation/``. The judge only ever sees linted
    constraints (deterministic lint-rejects never reach the LLM), each record
    carries the codegen ``enforcement`` gate, and ids are minted on the linted
    object (peripheral + operation included). See ``core/constraint_pipeline.py``
    and ``docs/constraint_chain_refactor_plan.md``. Returns the funnel counts."""
    from constraint_pipeline import run_stage_live

    if not chunks_root:
        raise ValueError(
            "--constraint-chunks-root is required with --constraint-validation "
            "(static quote validation searches the chunked datasheet)")

    out_dir = os.path.join(run_dir, "constraint_validation")
    return run_stage_live(
        rm=reference_manual, run=os.path.basename(run_dir),
        run_dir=run_dir, svd_dir=svd_dir, chunks_root=chunks_root,
        judge_model=judge_model, out_dir=out_dir,
        batch_size=batch_size, min_confidence=min_confidence)


def run_pipeline_for_device(
    ctx: UserContext,
    args: argparse.Namespace,
    repo_root: str,
) -> DeviceResult:
    """Execute the full pipeline (steps 2-5) for a single device."""
    from s1a_generator import run_generator, run_generator_batched
    from s2_coverage_improver import run_coverage_improver
    from s4_validator import build_invariants_from_agent_output, run_validator, run_validator_batched
    from scripts.calculate_generator_coverage import calculate_generator_coverage
    from applications.bug_finding.pipeline import run_bug_finding

    result = DeviceResult(device_name=ctx.device_name)

    try:
        run_number = resolve_run_number(repo_root, ctx, new_run=args.new_run)
        paths = resolve_device_paths(ctx, repo_root, run_number)
        result.final_run_number = run_number

        # Resolve context retrieval parameters
        cr_params = build_context_retrieval_params(paths.device_dir, ctx)

        # Read settings from args (with config.py defaults)
        generator_model = args.generator_model or config.GENERATOR_MODEL_NAME
        # Model list passed to the generator's call layer: an explicit
        # --generator-model pins one model (no overflow); otherwise use the
        # stage's ordered list (Groq primary, OpenAI overflow).
        generator_models = [args.generator_model] if args.generator_model else config.STAGE_MODELS["generator"]
        ci_model = args.coverage_improver_model or config.COVERAGE_IMPROVER_MODEL_NAME
        validator_model = args.validator_model or config.VALIDATOR_MODEL_NAME
        ci_iterations = args.coverage_improver_iterations
        ci_reasoning = config.COVERAGE_IMPROVER_REASONING_EFFORT
        validator_reasoning = config.VALIDATOR_REASONING_EFFORT
        run_analyzer_flag = args.run_analyzer

        generator_client = determine_client(generator_model)
        ci_client = determine_client(ci_model)
        validator_client = determine_client(validator_model)

        print(f"\n{'='*70}")
        print(f"DEVICE: {ctx.device_name} (run {run_number})")
        print(f"{'='*70}")
        print(f"  Context retrieval: {cr_params.context_retrieval_method.value}")
        print(f"  Generator model:   {generator_model}")
        print(f"  CI iterations:     {ci_iterations}")
        print(f"  Validator model:   {validator_model}")
        print(f"  Output dir:        {paths.agent_output_dir}")

        # -- Step 1: Preprocessing --
        if not args.skip_preprocessing:
            print(f"\n--- Step 1: Preprocessing ---")
            done, chunks = preprocess_device(
                paths,
                fmt=args.format,
                embed_metadata=args.embed_metadata,
            )
            result.preprocessing_done = done
            result.chunks_created = chunks
            # Refresh cr_params after preprocessing (new DB may have been created)
            if done:
                cr_params = build_context_retrieval_params(paths.device_dir, ctx)

        # Apply explicit retrieval override (e.g. --retrieval openevolve) last, so
        # it wins over the auto-resolved params above.
        cr_params = apply_retrieval_override(cr_params, args.retrieval, ctx.device_name, repo_root, ctx.manufacturer)
        print(f"  Retrieval (effective): {cr_params.context_retrieval_method.value}")
        result.retrieval_method = cr_params.context_retrieval_method.value
        result.generator_models = list(generator_models)

        # -- Step 2: Generator --
        generator_fn = run_generator_batched if args.generator_batched else run_generator
        gen_mode = "batched" if args.generator_batched else "per-register"
        print(f"\n--- Step 2: Generator [{gen_mode}] (run {paths.run_number}) ---")
        truncated = generator_fn(
            client=generator_client,
            model_name=generator_model,
            device_name=ctx.device_name,
            run_number=paths.run_number,
            device_dir=paths.device_dir,
            agent_output_dir=paths.agent_output_dir,
            context_retrieval_parameters=cr_params,
            manufacturer=ctx.manufacturer,
            peripherals_registers_dict=None,
            models=generator_models,
        )
        result.generator_done = True
        result.truncated = truncated

        # -- Step 3: Coverage Improver (optional) --
        if ci_iterations > 0:
            svd_files = sorted(glob.glob(os.path.join(paths.svd_dir, "*.svd"))
                               + glob.glob(os.path.join(paths.svd_dir, "*.xml")))   # NXP SVDs use .xml
            if not svd_files:
                print(f"  No SVD files in {paths.svd_dir} — skipping coverage improver")
            else:
                svd_path = svd_files[0]  # Use first SVD for coverage calculation
                current_cr_params = cr_params
                current_output_dir = paths.agent_output_dir
                current_run = paths.run_number
                current_truncated = truncated

                for i in range(ci_iterations):
                    print(f"\n--- Step 3: Coverage Improver (iteration {i+1}/{ci_iterations}) ---")
                    coverage_info = calculate_generator_coverage(svd_path, current_output_dir)

                    ci_output_dir = os.path.join(current_output_dir, "coverage_improver")
                    os.makedirs(ci_output_dir, exist_ok=True)
                    run_coverage_improver(
                        ci_client,
                        ci_model,
                        coverage_info,
                        current_cr_params,
                        ci_output_dir,
                        ci_reasoning,
                        current_truncated,
                    )

                    ci_output = CoverageImproverOutput.model_validate_json(
                        open(os.path.join(ci_output_dir, "coverage_improver_output.json")).read()
                    )

                    result.coverage_iterations = i + 1

                    if ci_output.stop_improving:
                        print(f"  Coverage improver signaled stop at iteration {i+1}")
                        break

                    # Prepare next iteration: update params, increment run, re-run generator
                    current_cr_params = ci_output.context_retrieval_parameters
                    # Preserve vector store ID (model may have changed it)
                    if cr_params.context_retrieval_method == ContextRetrievalMethod.OPENAI_FILE_SEARCH:
                        current_cr_params.vs_id = cr_params.vs_id
                    if cr_params.context_retrieval_method == ContextRetrievalMethod.LOCAL_VECTOR_DB:
                        current_cr_params.local_db_name = cr_params.local_db_name

                    current_run += 1
                    new_paths = resolve_device_paths(ctx, repo_root, current_run)
                    current_output_dir = new_paths.agent_output_dir

                    print(f"\n--- Step 2: Generator [{gen_mode}] (run {current_run}, after CI iteration {i+1}) ---")
                    current_truncated = generator_fn(
                        client=generator_client,
                        model_name=generator_model,
                        device_name=ctx.device_name,
                        run_number=current_run,
                        device_dir=paths.device_dir,
                        agent_output_dir=current_output_dir,
                        context_retrieval_parameters=current_cr_params,
                        manufacturer=ctx.manufacturer,
                        peripherals_registers_dict=None,
                        models=generator_models,
                    )

                # Update paths to the final run for subsequent steps
                paths = resolve_device_paths(ctx, repo_root, current_run)
                result.final_run_number = current_run
                result.truncated = current_truncated

        # -- Step 4: Validator (optional) --
        if not args.skip_validator:
            print(f"\n--- Step 4: Validator ---")
            invariants = build_invariants_from_agent_output(paths.agent_output_dir)
            validator_output_dir = os.path.join(paths.agent_output_dir, "validator")
            os.makedirs(validator_output_dir, exist_ok=True)

            validator_fn = run_validator_batched if args.validator_batched else run_validator
            true_count, false_count = validator_fn(
                client=validator_client,
                model_name=validator_model,
                invariants=invariants,
                output_dir=validator_output_dir,
                context_retrieval_parameters=cr_params,
                reasoning_effort=validator_reasoning,
            )
            result.validator_done = True
            result.true_count = true_count
            result.false_count = false_count
            print(f"  Validator: {true_count} true, {false_count} false")

        # -- Step 6: Constraint validation (v2 grammar, optional) --
        # The generator emits grammar v2 natively; this stage runs the
        # constraint pipeline on that output: static quote validation (does
        # the quote exist in the manual, and name the register?) then the LLM
        # constraint validator (is the encoding faithful?).
        if args.constraint_validation:
            print(f"\n--- Step 6: Constraint Validation (v2 grammar) ---")
            cv = run_constraint_validation_phase(
                run_dir=paths.agent_output_dir,
                reference_manual=ctx.device_name,
                chunks_root=args.constraint_chunks_root,
                svd_dir=paths.svd_dir,
                judge_model=args.constraint_judge_model,
                batch_size=args.constraint_batch_size,
            )
            result.constraint_validation_done = True
            result.constraints_extracted = cv["extracted"]
            result.constraints_anchored = cv["anchored"]
            result.constraints_confirmed = cv["confirmed"]
            print(f"  Funnel: {cv['extracted']} extracted -> "
                  f"{cv['anchored']} quote-anchored -> "
                  f"{cv['static_pass']} static-pass -> "
                  f"{cv['confirmed']} validator-confirmed")

        # -- Step 5: Evaluation (optional) --
        if not args.skip_evaluation:
            print(f"\n--- Step 5: Bug finding ---")
            bug_results = run_bug_finding(
                svd_dir=paths.svd_dir,
                agent_output_dir=paths.agent_output_dir,
                results_dir=paths.results_dir,
                run_analyzer_enabled=run_analyzer_flag,
            )
            from applications.bug_finding.models import BugStatus
            result.svd_files_compared = len(bug_results)
            result.evaluation_done = True
            result.analyzer_used = run_analyzer_flag
            all_bugs = [b for classes in bug_results.values() for bc in classes for b in bc.bugs]
            result.bug_candidates = sum(1 for b in all_bugs if b.status == BugStatus.PENDING)
            result.auto_fp = sum(1 for b in all_bugs if b.status == BugStatus.FALSE_POSITIVE)
            total_bugs = len(all_bugs)
            print(f"  Bug finding: {len(bug_results)} SVD(s), {result.bug_candidates} candidate(s), {result.auto_fp} auto-FP")
            for svd_name, classes in bug_results.items():
                n = sum(len(bc.bugs) for bc in classes)
                print(f"    {svd_name}: {n} bug(s) in {len(classes)} class(es)")

    except Exception as e:
        result.success = False
        result.error = str(e)
        import traceback
        traceback.print_exc()

    _write_run_manifest(result, ctx, args, repo_root)
    return result


def _count_generated_registers(output_dir: str) -> int:
    """Count register JSON files (one per register) in a run's output dir."""
    if not os.path.isdir(output_dir):
        return 0
    skip = {"info", "coverage_improver", "validator", "analyzer_iteration"}
    return sum(
        1 for e in os.listdir(output_dir)
        if e != "run_manifest.json"
        and e not in skip
        and os.path.isfile(os.path.join(output_dir, e))
    )


def _write_run_manifest(result: "DeviceResult", ctx: UserContext, args: argparse.Namespace,
                        repo_root: str) -> None:
    """Persist a structured manifest for this run (best-effort; never raises)."""
    try:
        from datetime import datetime, timezone
        from utils.run_manifest import RunManifest, save_run_manifest

        run_number = result.final_run_number or 1
        paths = resolve_device_paths(ctx, repo_root, run_number)
        svd_files = sorted(
            os.path.basename(p) for p in (glob.glob(os.path.join(paths.svd_dir, "*.svd"))
                                          + glob.glob(os.path.join(paths.svd_dir, "*.xml")))
        )
        registers = _count_generated_registers(paths.agent_output_dir)
        manifest = RunManifest(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            device_name=ctx.device_name,
            manufacturer=ctx.manufacturer.value,
            datasheet=os.path.relpath(paths.pdf_path, repo_root),
            svd_files=svd_files,
            run_number=run_number,
            output_dir=os.path.relpath(paths.agent_output_dir, repo_root),
            results_dir=os.path.relpath(paths.results_dir, repo_root),
            retrieval_method=result.retrieval_method,
            generator_models=result.generator_models,
            generator_batched=args.generator_batched,
            coverage_improver_iterations=result.coverage_iterations,
            analyzer_used=result.analyzer_used,
            validator_used=result.validator_done,
            validator_true=result.true_count,
            validator_false=result.false_count,
            registers_generated=registers,
            svd_files_compared=result.svd_files_compared,
            bug_candidates=result.bug_candidates,
            auto_fp=result.auto_fp,
            truncated=result.truncated,
            success=result.success,
            error=result.error,
            valid=result.success and registers > 0,
        )
        save_run_manifest(manifest, paths.agent_output_dir)
    except Exception as e:
        print(f"  [manifest] could not write run manifest: {e}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-device pipeline for hardware register extraction from datasheets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Device selection
    parser.add_argument(
        "--devices", nargs="+", metavar="DEVICE",
        help="Device names to process (default: all in config.user_contexts)",
    )

    # Step control
    parser.add_argument(
        "--skip-preprocessing", action="store_true",
        help="Skip local vector store creation (Step 1)",
    )
    parser.add_argument(
        "--coverage-improver-iterations", type=int,
        default=config.COVERAGE_IMPROVER_ITERATIONS,
        help=f"Number of coverage improver iterations; 0 = skip (default: {config.COVERAGE_IMPROVER_ITERATIONS})",
    )
    parser.add_argument(
        "--skip-validator", action="store_true",
        help="Skip validation step (Step 4)",
    )
    parser.add_argument(
        "--skip-evaluation", action="store_true",
        help="Skip SVD comparison and diff tables (Step 5)",
    )
    parser.add_argument(
        "--run-analyzer", action="store_true",
        default=config.RUN_ANALYZER,
        help=f"Run analyzer on diffs (default: {config.RUN_ANALYZER})",
    )
    parser.add_argument(
        "--new-run", action="store_true",
        help="Start a fresh run (max+1) instead of resuming the latest existing run",
    )
    parser.add_argument(
        "--retrieval", choices=["auto", "openevolve"], default="auto",
        help="Context retrieval method. 'auto' (default) resolves local/OpenAI/keyword "
             "from the device's vector_stores.json; 'openevolve' uses the evolved STM "
             "retrieval program (per-device, rm0041 fallback).",
    )
    parser.add_argument(
        "--generator-batched", action="store_true", dest="generator_batched",
        default=config.GENERATOR_BATCHED,
        help="Per-peripheral batched generator, fewer LLM calls (default: on)",
    )
    parser.add_argument(
        "--no-generator-batched", action="store_false", dest="generator_batched",
        help="Use the per-register generator instead of batched",
    )
    parser.add_argument(
        "--validator-batched", action="store_true", dest="validator_batched",
        default=True,
        help="Batch the structure-validator full pass by register (default: on). "
             "(The structure-validator candidate pass, s6, is always batched.)",
    )
    parser.add_argument(
        "--no-validator-batched", action="store_false", dest="validator_batched",
        help="Use the per-invariant structure validator instead of batched",
    )

    # Model overrides
    parser.add_argument(
        "--generator-model", metavar="MODEL",
        help=f"Override generator model (default: {config.GENERATOR_MODEL_NAME})",
    )
    parser.add_argument(
        "--coverage-improver-model", metavar="MODEL",
        help=f"Override coverage improver model (default: {config.COVERAGE_IMPROVER_MODEL_NAME})",
    )
    parser.add_argument(
        "--validator-model", metavar="MODEL",
        help=f"Override validator model (default: {config.VALIDATOR_MODEL_NAME})",
    )

    # Parallelism
    parser.add_argument(
        "--max-workers", type=int, default=1,
        help="Number of devices to process in parallel (default: 1)",
    )

    # Preprocessing options
    parser.add_argument(
        "--format", choices=["text", "markdown"], default="markdown",
        help="Chunk format for preprocessing (default: markdown)",
    )
    parser.add_argument(
        "--embed-metadata", action="store_true", default=True,
        help="Embed metadata in chunks during preprocessing (default: True)",
    )
    parser.add_argument(
        "--no-embed-metadata", action="store_false", dest="embed_metadata",
        help="Do not embed metadata in chunks during preprocessing",
    )
    parser.add_argument(
        "--constraint-validation", action="store_true",
        help="Step 6: after the generator, run the v2 constraint pipeline "
             "(static quote validation + LLM constraint validator)",
    )
    parser.add_argument(
        "--constraint-chunks-root", default=None,
        help="Root of the chunked datasheets ({rm}/chunks/md) for static "
             "quote validation (required with --constraint-validation)",
    )
    parser.add_argument(
        "--constraint-judge-model", default="openai/gpt-oss-120b",
        help="Model for the constraint validator judge (default: Groq gpt-oss-120b)",
    )
    parser.add_argument(
        "--constraint-batch-size", type=int, default=8,
        help="Constraints per judge call (default 8; amortizes the system prompt; "
             "any item the batch response omits falls back to a solo call)",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _print_summary(results: list[DeviceResult]) -> None:
    """Print a summary table of pipeline results."""
    print(f"\n{'='*70}")
    print("PIPELINE SUMMARY")
    print(f"{'='*70}")

    # Header
    print(f"{'Device':<12} {'Status':<8} {'Run':<5} {'Preproc':<8} {'Gen':<5} "
          f"{'CI':<4} {'Val':<10} {'Eval':<6} {'Error'}")
    print("-" * 90)

    for r in results:
        status = "OK" if r.success else "FAIL"
        preproc = "done" if r.preprocessing_done else "-"
        gen = "yes" if r.generator_done else "-"
        ci = str(r.coverage_iterations) if r.coverage_iterations > 0 else "-"
        val = f"{r.true_count}T/{r.false_count}F" if r.validator_done else "-"
        evl = str(r.svd_files_compared) if r.evaluation_done else "-"
        err = r.error[:30] if r.error else ""
        print(f"{r.device_name:<12} {status:<8} {r.final_run_number:<5} {preproc:<8} {gen:<5} "
              f"{ci:<4} {val:<10} {evl:<6} {err}")

    print(f"{'='*70}")
    ok = sum(1 for r in results if r.success)
    print(f"Total: {ok}/{len(results)} succeeded")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    # Select devices
    all_contexts = config.user_contexts
    if args.devices:
        selected = []
        device_set = set(d.lower() for d in args.devices)
        for ctx in all_contexts:
            if ctx.device_name.lower() in device_set:
                selected.append(ctx)
                device_set.discard(ctx.device_name.lower())
        if device_set:
            print(f"Warning: devices not found in config.user_contexts: {device_set}")
        if not selected:
            print("Error: no matching devices found")
            sys.exit(1)
    else:
        selected = list(all_contexts)

    print(f"Processing {len(selected)} device(s): {[c.device_name for c in selected]}")

    results: list[DeviceResult] = []

    if args.max_workers <= 1:
        # Sequential execution
        for ctx in selected:
            result = run_pipeline_for_device(ctx, args, _REPO_ROOT)
            results.append(result)
    else:
        # Parallel execution across devices
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            futures = {
                executor.submit(run_pipeline_for_device, ctx, args, _REPO_ROOT): ctx
                for ctx in selected
            }
            for future in as_completed(futures):
                ctx = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = DeviceResult(
                        device_name=ctx.device_name,
                        success=False,
                        error=str(e),
                    )
                results.append(result)

    _print_summary(results)


if __name__ == "__main__":
    main()
