#!/usr/bin/env python3
"""
Test run 6: md_enriched chunks with embedded metadata headers.

This test compares the md_enriched vector store (chunks with embedded metadata)
against the plain md_chunks to measure the effect of embedded metadata headers.
"""

import os
import sys
from pathlib import Path

# Add project root to path BEFORE any imports
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)  # Change to project root for relative imports

import json
from openai import OpenAI
from groq import Groq

from defs import ContextRetrievalParameters, ContextRetrievalMethod, Manufacturer
from core.s1a_generator import run_generator
from utils.vector_store_config import get_vector_stores


def run_test(
    vs_name: str,
    output_subdir: str,
    num_embeddings: int = 8,
    chunk_expansion_enabled: bool = True,
    pages_after: int = 2,
):
    """Run generator test with specified vector store."""

    # Load vector store config
    device_dir = str(project_root / "devices" / "stm" / "rm0041")
    vs_config = get_vector_stores(device_dir)

    vs_id = vs_config.get_vs_id(vs_name)
    chunk_index_path = vs_config.get_chunk_index_path(vs_name)

    if not vs_id:
        print(f"Error: No vs_id found for {vs_name}")
        return None

    print(f"\n{'='*60}")
    print(f"Running test: {vs_name}")
    print(f"  Vector Store ID: {vs_id}")
    print(f"  Embeddings: {num_embeddings}")
    print(f"  Chunk expansion: {chunk_expansion_enabled} (pages_after={pages_after})")
    print(f"  Chunk index: {chunk_index_path}")
    print(f"{'='*60}\n")

    # Set up output directory
    output_dir = Path(__file__).parent / output_subdir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Configure context retrieval
    context_params = ContextRetrievalParameters(
        context_retrieval_method=ContextRetrievalMethod.SEMANTIC_SEARCH,
        pages_after_keyword=0,
        number_embeddings=num_embeddings,
        re_ranking=False,
        query_rewrite=False,
        vs_id=vs_id,
        chunk_expansion_enabled=chunk_expansion_enabled,
        pages_after=pages_after,
        chunk_index_path=chunk_index_path or "",
    )

    # Test with AFIO peripheral (same as previous tests for comparison)
    test_peripherals = {
        "AFIO": ["EVCR", "MAPR", "EXTICR1", "EXTICR2", "EXTICR3", "EXTICR4"]
    }

    # Initialize client
    client = Groq()
    model_name = "gpt-oss-120b"

    # Run generator
    run_generator(
        client=client,
        model_name=model_name,
        device_name="rm0041",
        run_number=6,
        device_dir=device_dir,
        agent_output_dir=str(output_dir),
        context_retrieval_parameters=context_params,
        manufacturer=Manufacturer.STM,
        peripherals_registers_dict=test_peripherals,
    )

    return output_dir


def main():
    # Run tests with md_enriched vector store at different embedding counts
    test_configs = [
        ("md_enriched", "md_enriched_expansion_embeddings_4", 4),
        ("md_enriched", "md_enriched_expansion_embeddings_8", 8),
        ("md_enriched", "md_enriched_expansion_embeddings_16", 16),
    ]

    results = []
    for vs_name, output_subdir, num_embeddings in test_configs:
        output_dir = run_test(
            vs_name=vs_name,
            output_subdir=output_subdir,
            num_embeddings=num_embeddings,
            chunk_expansion_enabled=True,
            pages_after=2,
        )
        if output_dir:
            results.append((output_subdir, num_embeddings, output_dir))

    print("\n" + "="*60)
    print("Test runs complete!")
    print("="*60)
    for subdir, num_emb, path in results:
        print(f"  {subdir}: {path}")

    print("\nNext steps:")
    print("  1. Run comparison script to analyze results")
    print("  2. Compare with md_chunks results from run 5")


if __name__ == "__main__":
    main()
