#!/usr/bin/env python3
"""
Generator test run 4: Markdown chunks with embedded metadata headers + chunk expansion

This test evaluates the impact of:
1. Embedded metadata headers in chunks (md_enriched)
2. Contiguous chunk expansion (pulling in chunks from subsequent pages)

Test configuration:
- Vector store: vs_6973a4df01bc81919940212995712255 (md_enriched chunks)
- Chunk expansion: enabled (pages_after=2)
- Chunk index: devices/stm/rm0041/chunks/md/upload_summary.csv
- Embedding counts: 4, 8, 16, 50 (matching previous tests)
- Peripheral: AFIO (matching previous tests)
"""

import os
import sys
from pathlib import Path

# Add project root to path and change to it BEFORE importing project modules
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Now import project modules
import config
from defs import ContextRetrievalParameters, ContextRetrievalMethod, Manufacturer
from core.s1a_generator import run_generator
from agent_tools.tools import all_svd_file_paths
from agent_tools.svd_parsing import get_register_names_for_peripheral
from utils.timing import get_timing_stats

def main():
    # Configuration
    device_dir = "devices/stm/rm0041"
    svd_file_paths = all_svd_file_paths(device_dir)

    # Use AFIO peripheral - same as previous tests
    test_peripheral = "afio"
    test_registers = get_register_names_for_peripheral(svd_file_paths, test_peripheral)

    print(f"Testing with peripheral: {test_peripheral}")
    print(f"Processing {len(test_registers)} registers: {test_registers}\n")

    # Vector store ID for md_enriched chunks
    # Same as md chunks since they share the same vector store
    vs_id_md = "vs_6973a4df01bc81919940212995712255"

    # Chunk index path for contiguous expansion
    chunk_index_path = "devices/stm/rm0041/chunks/md/upload_summary.csv"

    print(f"Using vs_id: {vs_id_md}")
    print(f"Chunk index: {chunk_index_path}")
    print(f"Chunk expansion: ENABLED (pages_after=2)\n")

    # Test with different number_embeddings values
    embedding_counts = [4, 8, 16, 50]

    for num_embeddings in embedding_counts:
        print(f"\n{'='*80}")
        print(f"RUNNING TEST WITH number_embeddings={num_embeddings}")
        print(f"{'='*80}\n")

        context_retrieval_parameters = ContextRetrievalParameters(
            context_retrieval_method=ContextRetrievalMethod.SEMANTIC_SEARCH,
            pages_after_keyword=2,
            remove_tables=True,
            number_embeddings=num_embeddings,
            re_ranking=True,
            score_threshold=0.25,
            query_rewrite=False,  # Disabled for this test
            vs_id=vs_id_md,
            regex="",
            other="",
            # Chunk expansion parameters - NEW FEATURE
            chunk_expansion_enabled=True,
            pages_after=2,
            chunk_index_path=chunk_index_path,
        )

        output_dir = f"optimization/test_outputs/generator/4/md_enriched_expansion_embeddings_{num_embeddings}"
        os.makedirs(output_dir, exist_ok=True)

        # Reset timing stats for this test
        timing = get_timing_stats()
        timing.reset()

        truncated_at_any_register = run_generator(
            client=config.client_groq,
            device_name="rm0041",
            run_number=4,
            device_dir=device_dir,
            agent_output_dir=output_dir,
            model_name="gpt-oss-120b",
            context_retrieval_parameters=context_retrieval_parameters,
            manufacturer=Manufacturer.STM,
            peripherals_registers_dict={
                test_peripheral: test_registers,
            }
        )

        # Print timing summary for this test
        print(f"\n{'='*80}")
        print(f"TIMING SUMMARY - number_embeddings={num_embeddings}")
        print(f"{'='*80}")
        timing.print_summary()

        # Save timing stats
        timing_stats_path = os.path.join(output_dir, "timing_stats.json")
        timing.save_to_file(timing_stats_path)
        print(f"Timing statistics saved to: {timing_stats_path}")

    print(f"\n\n{'='*80}")
    print("ALL TESTS COMPLETE")
    print(f"{'='*80}")
    print(f"\nResults saved to: optimization/test_outputs/generator/4/")
    print("\nNext steps:")
    print("1. Run analysis: python optimization/compare_generator_with_verified.py")
    print("2. Update optimization/CHUNKS_COMPARISON.md with results")


if __name__ == "__main__":
    main()
