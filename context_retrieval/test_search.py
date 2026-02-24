#!/usr/bin/env python3
"""
Test harness for the context retrieval search pipeline.

Modes:
  search        End-to-end search_context() (OpenAI or local vector DB)
  retrieve      End-to-end retrieve_context() (keyword search needs device/PDF)
  post-process  Fetch raw results once, then run post_process() with different
                parameter combinations to compare their effects
  unit          Test post_process() with synthetic data (no DB needed)

Usage examples:

    # Quick unit test (no DB required)
    python context_retrieval/test_search.py --mode unit

    # End-to-end local vector DB search
    python context_retrieval/test_search.py --mode search --method local_vector_db

    # Compare post-processing parameter combinations on real data
    python context_retrieval/test_search.py --mode post-process

    # OpenAI file search
    python context_retrieval/test_search.py --mode search --method openai_file_search

    # Keyword search via retrieve_context()
    python context_retrieval/test_search.py --mode retrieve --method keyword_search

    # Override specific parameters
    python context_retrieval/test_search.py --mode search \\
        --num-embeddings 10 --score-threshold 0.3 --no-keyword-boost

    # Post-process sweep with custom register
    python context_retrieval/test_search.py --mode post-process \\
        --register-filter AFIO_MAPR --query "AFIO_MAPR register offset and bit fields"
"""

import os
import sys
import argparse
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from defs import ContextRetrievalParameters, ContextRetrievalMethod, Manufacturer
from context_retrieval.post_processing import SearchResult, post_process


# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_QUERY = (
    "For the CRC_DR register, retrieve all information about its offset, "
    "reset value, size, readonly bits, writeonly bits, readwrite bits, and subfields."
)
DEFAULT_REGISTER_FILTER = "CRC_DR"

# OpenAI defaults (rm0041)
DEFAULT_VS_ID = "vs_6892501067b08191ac63cc6de06ee629"
DEFAULT_NUM_EMBEDDINGS = 5

# Local vector DB defaults (rm0041)
DEFAULT_LOCAL_DB_NAME = "rm0041_md"
DEFAULT_LOCAL_DB_PATH = ""
DEFAULT_RERANKER = "local"
DEFAULT_EMBEDDING_PROVIDER = "local"
DEFAULT_CHUNK_INDEX_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "chunked_datasheets", "stm", "rm0041", "chunks", "local", "chunks_index.csv"
)

# Keyword search / retrieve_context defaults
DEFAULT_DEVICE_NAME = "rm0041"
DEFAULT_DEVICE_DIR = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "devices", "stm", "rm0041"
)
DEFAULT_PERIPHERAL = "CRC"
DEFAULT_REGISTER = "DR"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bool_flag(parser, name, default, help_text):
    """Add --flag / --no-flag boolean pair to argparse."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument(f"--{name}", dest=name.replace("-", "_"),
                       action="store_true", default=default, help=help_text)
    group.add_argument(f"--no-{name}", dest=name.replace("-", "_"),
                       action="store_false", help=f"Disable {name}")


def build_params(args, **overrides) -> ContextRetrievalParameters:
    """Build ContextRetrievalParameters from CLI args with optional overrides."""
    method = ContextRetrievalMethod(args.method)
    kwargs = dict(
        context_retrieval_method=method,
        pages_after_keyword=args.pages_after_keyword,
        remove_tables=args.remove_tables,
        number_embeddings=args.num_embeddings,
        re_ranking=args.re_ranking,
        score_threshold=args.score_threshold,
        vs_id=args.vs_id,
        regex="",
        chunk_expansion_enabled=args.chunk_expansion,
        pages_after=args.pages_after,
        chunk_index_path=args.chunk_index_path,
        expand_table_pages_only=args.expand_table_pages_only,
        local_db_name=args.db_name,
        local_db_path=args.db_path,
        keyword_boost=args.keyword_boost,
        reranker_type=args.reranker,
        local_embedding_provider=args.embedding_provider,
        metadata_filter_enabled=args.metadata_filter,
    )
    kwargs.update(overrides)
    return ContextRetrievalParameters(**kwargs)


def print_section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def print_result_summary(formatted_text, embedding_ids, elapsed=None):
    """Print a concise summary of search results."""
    if elapsed is not None:
        print(f"  Time:          {elapsed:.2f}s")
    print(f"  Embedding IDs: {len(embedding_ids)} results")
    if formatted_text:
        print(f"  Text length:   {len(formatted_text)} chars")
        print(f"  Preview:\n{formatted_text[:500]}{'...' if len(formatted_text) > 500 else ''}")
    else:
        print(f"  Text:          None (no results)")


def print_embedding_ids(embedding_ids, limit=10):
    """Print embedding IDs, truncated to limit."""
    for eid in embedding_ids[:limit]:
        print(f"  {eid}")
    if len(embedding_ids) > limit:
        print(f"  ... ({len(embedding_ids) - limit} more)")


# ── Mode: search ──────────────────────────────────────────────────────────────

def run_search_context(args):
    """Test the search_context() path (OpenAI or local vector DB)."""
    from context_retrieval.search import search_context

    params = build_params(args)
    query = args.query
    register_filter = args.register_filter

    print_section("search_context() — Unified Search")
    print(f"  Method: {params.context_retrieval_method.value}")
    print(f"  Query:  {query[:80]}{'...' if len(query) > 80 else ''}")
    print(f"  Filter: {register_filter or '(none)'}")
    print()

    method = params.context_retrieval_method
    if method == ContextRetrievalMethod.OPENAI_FILE_SEARCH:
        print(f"  Flow: search_vector_store() → normalize_openai_results() → post_process()")
        print(f"    vs_id={params.vs_id[:30]}..., n={params.number_embeddings}, "
              f"re_rank={params.re_ranking}, threshold={params.score_threshold}")

    elif method == ContextRetrievalMethod.LOCAL_VECTOR_DB:
        print(f"  Flow: search_local_raw() → normalize_local_results() → post_process()")
        print(f"    db={params.local_db_name}, n={params.number_embeddings}, "
              f"reranker={params.reranker_type or '(none)'}")
        if register_filter:
            print(f"    metadata filter: reg_{register_filter.upper()}")

    print(f"  Post-process: keyword_boost={params.keyword_boost}, "
          f"threshold={params.score_threshold}, "
          f"expansion={params.chunk_expansion_enabled}, "
          f"remove_tables={params.remove_tables}")

    print()
    print("  Executing...")
    t0 = time.time()
    formatted_text, embedding_ids = search_context(query, params, register_filter)
    elapsed = time.time() - t0

    print_section("Results")
    print_result_summary(formatted_text, embedding_ids, elapsed)

    if embedding_ids:
        print_section("Embedding IDs")
        print_embedding_ids(embedding_ids)


# ── Mode: retrieve ────────────────────────────────────────────────────────────

def run_retrieve_context(args):
    """Test the retrieve_context() path (keyword search needs device/PDF)."""
    from context_retrieval.retrieve_context import retrieve_context

    params = build_params(args)
    device_name = args.device or DEFAULT_DEVICE_NAME
    device_dir = args.device_dir or DEFAULT_DEVICE_DIR
    peripheral = args.peripheral or DEFAULT_PERIPHERAL
    register = args.register or DEFAULT_REGISTER

    print_section("retrieve_context() — Full Context Retrieval")
    print(f"  Method:     {params.context_retrieval_method.value}")
    print(f"  Device:     {device_name}")
    print(f"  Peripheral: {peripheral}")
    print(f"  Register:   {register}")
    print()

    method = params.context_retrieval_method
    if method == ContextRetrievalMethod.KEYWORD_SEARCH:
        print(f"  Flow: keyword_info → page extraction → PDF pages → text")
        if params.remove_tables:
            print(f"    + remove_markdown_tables()")
    elif method in (ContextRetrievalMethod.OPENAI_FILE_SEARCH, ContextRetrievalMethod.LOCAL_VECTOR_DB):
        print(f"  Flow: builds query → delegates to search_context()")

    print()
    print("  Executing...")
    t0 = time.time()
    formatted_text, embedding_ids = retrieve_context(
        context_retrieval_parameters=params,
        device_name=device_name,
        device_dir=device_dir,
        peripheral_name=peripheral,
        register_name=register,
        manufacturer=Manufacturer.STM,
        output_dir=".",
    )
    elapsed = time.time() - t0

    print_section("Results")
    print_result_summary(formatted_text, embedding_ids, elapsed)


# ── Mode: post-process ────────────────────────────────────────────────────────

def _fetch_raw_results(args):
    """Fetch raw SearchResult list from the configured backend (no post-processing)."""
    method = ContextRetrievalMethod(args.method)
    query = args.query
    register_filter = args.register_filter

    if method == ContextRetrievalMethod.LOCAL_VECTOR_DB:
        from context_retrieval.local_vector_search import search_local_raw, normalize_local_results

        n = max(1, args.num_embeddings)
        raw = search_local_raw(
            query=query,
            db_name=args.db_name,
            n_results=n,
            reranker_type=args.reranker,
            db_path=args.db_path,
            embedding_provider=args.embedding_provider,
            register_filter=register_filter if args.metadata_filter else "",
        )
        return normalize_local_results(raw)

    elif method == ContextRetrievalMethod.OPENAI_FILE_SEARCH:
        from context_retrieval.openai_file_search import search_vector_store, normalize_openai_results
        from context_retrieval.chunk_index import get_chunk_index

        n = max(1, min(args.num_embeddings, 50))
        results = search_vector_store(
            query, args.vs_id, n, args.re_ranking, args.score_threshold
        )
        if not results.data:
            return []

        chunk_index = None
        if args.chunk_index_path:
            try:
                chunk_index = get_chunk_index(args.chunk_index_path)
            except FileNotFoundError:
                pass
        return normalize_openai_results(results, chunk_index)

    else:
        print(f"  post-process mode requires openai_file_search or local_vector_db, not {method.value}")
        sys.exit(1)


# Post-processing parameter combinations to sweep
SWEEP_CONFIGS = [
    {
        "label": "Baseline (no post-processing)",
        "keyword_boost": False,
        "score_threshold": 0.0,
        "chunk_expansion_enabled": False,
        "remove_tables": False,
    },
    {
        "label": "Keyword boost only",
        "keyword_boost": True,
        "score_threshold": 0.0,
        "chunk_expansion_enabled": False,
        "remove_tables": False,
    },
    {
        "label": "Score threshold 0.30",
        "keyword_boost": False,
        "score_threshold": 0.30,
        "chunk_expansion_enabled": False,
        "remove_tables": False,
    },
    {
        "label": "Score threshold 0.50",
        "keyword_boost": False,
        "score_threshold": 0.50,
        "chunk_expansion_enabled": False,
        "remove_tables": False,
    },
    {
        "label": "Boost + threshold 0.30",
        "keyword_boost": True,
        "score_threshold": 0.30,
        "chunk_expansion_enabled": False,
        "remove_tables": False,
    },
    {
        "label": "Chunk expansion (pages_after=2)",
        "keyword_boost": False,
        "score_threshold": 0.0,
        "chunk_expansion_enabled": True,
        "remove_tables": False,
    },
    {
        "label": "Chunk expansion (table pages only)",
        "keyword_boost": False,
        "score_threshold": 0.0,
        "chunk_expansion_enabled": True,
        "expand_table_pages_only": True,
        "remove_tables": False,
    },
    {
        "label": "Remove tables",
        "keyword_boost": False,
        "score_threshold": 0.0,
        "chunk_expansion_enabled": False,
        "remove_tables": True,
    },
    {
        "label": "Full pipeline (boost + threshold + expansion + table removal)",
        "keyword_boost": True,
        "score_threshold": 0.25,
        "chunk_expansion_enabled": True,
        "remove_tables": True,
    },
    {
        "label": "Trim to 1 result",
        "keyword_boost": False,
        "score_threshold": 0.0,
        "number_embeddings": 1,
        "chunk_expansion_enabled": False,
        "remove_tables": False,
    },
    {
        "label": "Trim to 3 + boost (reorder then trim)",
        "keyword_boost": True,
        "score_threshold": 0.0,
        "number_embeddings": 3,
        "chunk_expansion_enabled": False,
        "remove_tables": False,
    },
]


def run_post_process(args):
    """Fetch raw results once, then sweep post-processing parameter combinations."""
    query = args.query

    print_section("Fetching raw results")
    print(f"  Method:   {args.method}")
    print(f"  Query:    {query[:80]}{'...' if len(query) > 80 else ''}")
    print(f"  Filter:   {args.register_filter or '(none)'}")
    print()

    t0 = time.time()
    raw_results = _fetch_raw_results(args)
    elapsed = time.time() - t0

    print(f"  Fetched {len(raw_results)} raw results in {elapsed:.2f}s")
    if not raw_results:
        print("  No raw results — nothing to post-process.")
        return

    # Show raw results
    print_section("Raw results (before post-processing)")
    for i, r in enumerate(raw_results):
        tables_flag = " [TABLE]" if r.has_tables else ""
        print(f"  [{i}] score={r.score:.3f} page={r.page_number} "
              f"chunk={r.chunk_id}{tables_flag}")
        print(f"      text={r.text[:100]}...")

    # Run each parameter combination
    print_section("Post-processing parameter sweep")
    print(f"  Running {len(SWEEP_CONFIGS)} configurations...\n")

    summary_rows = []

    for idx, config in enumerate(SWEEP_CONFIGS):
        label = config.pop("label")
        overrides = {
            "chunk_index_path": args.chunk_index_path,
            "pages_after": args.pages_after,
        }
        overrides.update(config)

        params = build_params(args, **overrides)
        # Restore label for next run
        config["label"] = label

        t0 = time.time()
        formatted, ids = post_process(list(raw_results), params, query)
        elapsed = time.time() - t0

        text_len = len(formatted) if formatted else 0
        n_results = len(ids)

        # Count expansion results by parsing XML
        n_expansion = formatted.count("expansion='true'") if formatted else 0

        # Top score from embedding IDs
        top_score = ids[0]["score"] if ids else 0.0

        # Collect ordering (chunk_ids in result order)
        ordering = [eid.get("chunk_id", eid.get("source", "?"))[:20] for eid in ids[:5]]

        summary_rows.append({
            "idx": idx,
            "label": label,
            "n_results": n_results,
            "n_expansion": n_expansion,
            "text_len": text_len,
            "top_score": top_score,
            "ordering": ordering,
            "elapsed": elapsed,
        })

        print(f"  [{idx}] {label}")
        print(f"      results={n_results}, expansion={n_expansion}, "
              f"text_len={text_len}, top_score={top_score:.3f}, "
              f"time={elapsed*1000:.0f}ms")
        print(f"      order: {' → '.join(ordering)}")
        print()

    # Summary table
    print_section("Summary comparison")
    hdr = f"  {'#':<3} {'Config':<52} {'N':>3} {'Exp':>3} {'Len':>6} {'Top':>6}"
    print(hdr)
    print(f"  {'─'*3} {'─'*52} {'─'*3} {'─'*3} {'─'*6} {'─'*6}")
    for row in summary_rows:
        print(f"  {row['idx']:<3} {row['label']:<52} {row['n_results']:>3} "
              f"{row['n_expansion']:>3} {row['text_len']:>6} {row['top_score']:>6.3f}")


# ── Mode: unit ────────────────────────────────────────────────────────────────

def _make_synthetic_results():
    """Build synthetic SearchResult list for unit testing (no DB needed)."""
    return [
        SearchResult(
            text=(
                "## REGISTER DEFINITION: CRC_DR\n"
                "The CRC data register contains the result of the CRC calculation.\n"
                "[KEY: CRC_DR]\n"
                "| Bits | Name | Access |\n|---|---|---|\n| 31:0 | DR | rw |\n"
            ),
            score=0.85,
            page_number=42,
            chunk_id="rm0041_p042_c01",
            source="rm0041_p042_c01.txt",
            has_tables=True,
            metadata={"section": "CRC", "peripheral": "CRC", "chunk_type": "register"},
            rank=0,
        ),
        SearchResult(
            text=(
                "The CRC calculation unit has a single 32-bit data register (CRC_DR).\n"
                "The reset value is 0xFFFFFFFF.\n"
                "Address offset: 0x00"
            ),
            score=0.80,
            page_number=41,
            chunk_id="rm0041_p041_c01",
            source="rm0041_p041_c01.txt",
            has_tables=False,
            metadata={"section": "CRC", "peripheral": "CRC", "chunk_type": "text"},
            rank=1,
        ),
        SearchResult(
            text=(
                "## CRC_IDR register\n"
                "General-purpose 8-bit data register.\n"
                "| Bits | Name |\n|---|---|\n| 7:0 | IDR |\n"
            ),
            score=0.72,
            page_number=43,
            chunk_id="rm0041_p043_c01",
            source="rm0041_p043_c01.txt",
            has_tables=True,
            metadata={"section": "CRC", "peripheral": "CRC", "chunk_type": "register"},
            rank=2,
        ),
        SearchResult(
            text=(
                "The independent data register (CRC_IDR) can be used to hold "
                "a temporary value. It is not affected by CRC_DR reads/writes."
            ),
            score=0.65,
            page_number=44,
            chunk_id="rm0041_p044_c01",
            source="rm0041_p044_c01.txt",
            has_tables=False,
            metadata={"section": "CRC", "peripheral": "CRC", "chunk_type": "text"},
            rank=3,
        ),
        SearchResult(
            text="Some unrelated GPIO text that shouldn't score well.",
            score=0.40,
            page_number=100,
            chunk_id="rm0041_p100_c01",
            source="rm0041_p100_c01.txt",
            has_tables=False,
            metadata={"section": "GPIO", "peripheral": "GPIO", "chunk_type": "text"},
            rank=4,
        ),
    ]


def run_unit_tests(args):
    """Test post_process() with synthetic data — no DB required."""
    query = "CRC_DR register offset, reset value, size, and subfields"
    results = _make_synthetic_results()

    print_section("Unit tests — synthetic SearchResult data")
    print(f"  Query:   {query}")
    print(f"  Results: {len(results)} synthetic items")
    print()

    tests = [
        (
            "Pass-through (no processing)",
            {"keyword_boost": False, "score_threshold": 0.0,
             "number_embeddings": 10, "chunk_expansion_enabled": False,
             "remove_tables": False},
            {"expect_n": 5, "expect_order_starts": ["rm0041_p042", "rm0041_p041"]},
        ),
        (
            "Keyword boost reorders by CRC_DR match",
            {"keyword_boost": True, "score_threshold": 0.0,
             "number_embeddings": 10, "chunk_expansion_enabled": False,
             "remove_tables": False},
            {"expect_top_boost_gt": 0, "expect_n": 5},
        ),
        (
            "Score threshold 0.70 removes low-scoring results",
            {"keyword_boost": False, "score_threshold": 0.70,
             "number_embeddings": 10, "chunk_expansion_enabled": False,
             "remove_tables": False},
            {"expect_n": 3},
        ),
        (
            "Score threshold 0.90 filters everything except boosted",
            {"keyword_boost": True, "score_threshold": 0.90,
             "number_embeddings": 10, "chunk_expansion_enabled": False,
             "remove_tables": False},
            {"expect_n_gte": 1},
        ),
        (
            "Trim to 2",
            {"keyword_boost": False, "score_threshold": 0.0,
             "number_embeddings": 2, "chunk_expansion_enabled": False,
             "remove_tables": False},
            {"expect_n": 2},
        ),
        (
            "Trim to 3 + boost (boost then trim changes which results kept)",
            {"keyword_boost": True, "score_threshold": 0.0,
             "number_embeddings": 3, "chunk_expansion_enabled": False,
             "remove_tables": False},
            {"expect_n": 3},
        ),
        (
            "Remove tables strips markdown tables",
            {"keyword_boost": False, "score_threshold": 0.0,
             "number_embeddings": 10, "chunk_expansion_enabled": False,
             "remove_tables": True},
            {"expect_no_pipe": True, "expect_n": 5},
        ),
        (
            "Empty input returns (None, [])",
            {"keyword_boost": True, "score_threshold": 0.0,
             "number_embeddings": 10, "chunk_expansion_enabled": False,
             "remove_tables": False},
            {"use_empty": True, "expect_none": True},
        ),
        (
            "High threshold eliminates all → returns (None, [])",
            {"keyword_boost": False, "score_threshold": 0.99,
             "number_embeddings": 10, "chunk_expansion_enabled": False,
             "remove_tables": False},
            {"expect_none": True},
        ),
    ]

    passed = 0
    failed = 0

    for label, overrides, checks in tests:
        params = ContextRetrievalParameters(
            context_retrieval_method=ContextRetrievalMethod.LOCAL_VECTOR_DB,
            pages_after_keyword=2,
            re_ranking=False,
            vs_id="",
            regex="",
            chunk_index_path="",
            pages_after=2,
            **overrides,
        )

        input_data = [] if checks.get("use_empty") else list(results)
        formatted, ids = post_process(input_data, params, query)

        # Run assertions
        errors = []

        if checks.get("expect_none"):
            if formatted is not None:
                errors.append(f"expected None, got text of length {len(formatted)}")
            if ids:
                errors.append(f"expected empty ids, got {len(ids)}")

        if "expect_n" in checks and not checks.get("expect_none"):
            if len(ids) != checks["expect_n"]:
                errors.append(f"expected {checks['expect_n']} results, got {len(ids)}")

        if "expect_n_gte" in checks:
            if len(ids) < checks["expect_n_gte"]:
                errors.append(f"expected >= {checks['expect_n_gte']} results, got {len(ids)}")

        if checks.get("expect_top_boost_gt", 0) == 0 and "expect_top_boost_gt" in checks:
            if ids and ids[0].get("keyword_boost", 0) <= 0:
                errors.append(f"expected keyword_boost > 0 on top result")

        if checks.get("expect_no_pipe") and formatted:
            # After table removal, no pipe characters should appear in content
            # (simplistic check — pipes inside code blocks would be preserved,
            # but our synthetic data doesn't have code blocks)
            import re
            content_matches = re.findall(r'<content>(.*?)</content>', formatted, re.DOTALL)
            for content in content_matches:
                if '|' in content:
                    errors.append(f"found '|' in content after table removal")
                    break

        if "expect_order_starts" in checks and ids:
            for i, expected_prefix in enumerate(checks["expect_order_starts"]):
                if i < len(ids):
                    actual = ids[i].get("chunk_id", ids[i].get("source", ""))
                    if not actual.startswith(expected_prefix):
                        errors.append(f"result[{i}] expected prefix '{expected_prefix}', got '{actual}'")

        # Report
        status = "PASS" if not errors else "FAIL"
        if errors:
            failed += 1
            print(f"  FAIL  {label}")
            for e in errors:
                print(f"        {e}")
        else:
            passed += 1
            print(f"  PASS  {label}")

        # Show detail
        if ids:
            detail_parts = []
            for eid in ids[:3]:
                cid = eid.get("chunk_id", "?")[:18]
                s = eid.get("score", 0)
                b = eid.get("keyword_boost", 0)
                detail_parts.append(f"{cid}({s:.2f}" + (f"+{b:.2f}" if b else "") + ")")
            print(f"        [{', '.join(detail_parts)}" +
                  (f", ...+{len(ids)-3}" if len(ids) > 3 else "") + "]")

    print()
    print(f"  {passed} passed, {failed} failed, {passed + failed} total")

    if failed:
        sys.exit(1)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Test context retrieval search pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--mode", choices=["search", "retrieve", "post-process", "unit"],
                        default="unit",
                        help="Test mode (default: unit)")
    parser.add_argument("--query", default=DEFAULT_QUERY,
                        help="Search query string")
    parser.add_argument("--register-filter", default=DEFAULT_REGISTER_FILTER,
                        help="Register name for metadata filtering")
    parser.add_argument("--method", default="local_vector_db",
                        choices=[m.value for m in ContextRetrievalMethod],
                        help="Context retrieval method")

    # OpenAI file search
    parser.add_argument("--vs-id", default=DEFAULT_VS_ID, help="Vector store ID")
    parser.add_argument("--num-embeddings", type=int, default=DEFAULT_NUM_EMBEDDINGS)
    _bool_flag(parser, "re-ranking", True, "Enable OpenAI re-ranking")
    parser.add_argument("--score-threshold", type=float, default=0.25)

    # Local vector DB
    parser.add_argument("--db-name", default=DEFAULT_LOCAL_DB_NAME)
    parser.add_argument("--db-path", default=DEFAULT_LOCAL_DB_PATH)
    parser.add_argument("--reranker", default=DEFAULT_RERANKER,
                        help="Reranker: '', 'local', 'cohere', 'bge'")
    parser.add_argument("--embedding-provider", default=DEFAULT_EMBEDDING_PROVIDER)
    _bool_flag(parser, "keyword-boost", True, "Apply keyword boosting")
    _bool_flag(parser, "metadata-filter", True, "Enable metadata filtering")

    # Chunk expansion
    _bool_flag(parser, "chunk-expansion", True, "Enable chunk expansion")
    parser.add_argument("--pages-after", type=int, default=2)
    parser.add_argument("--chunk-index-path", default=DEFAULT_CHUNK_INDEX_PATH)
    _bool_flag(parser, "expand-table-pages-only", False,
               "Only expand pages containing tables")

    # Keyword search / retrieve_context
    parser.add_argument("--pages-after-keyword", type=int, default=2)
    _bool_flag(parser, "remove-tables", False, "Remove markdown tables from results")
    parser.add_argument("--device", default="")
    parser.add_argument("--device-dir", default="")
    parser.add_argument("--peripheral", default="")
    parser.add_argument("--register", default="")

    args = parser.parse_args()

    print("=" * 60)
    print("  Context Retrieval Test Harness")
    print("=" * 60)

    if args.mode == "unit":
        run_unit_tests(args)
    elif args.mode == "search":
        run_search_context(args)
    elif args.mode == "retrieve":
        run_retrieve_context(args)
    elif args.mode == "post-process":
        run_post_process(args)


if __name__ == "__main__":
    main()
