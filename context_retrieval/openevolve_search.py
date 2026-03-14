"""
Adapter for OpenEvolve's evolved retrieval program.

Wraps the best evolved program (best_program.py) to provide the same interface
as the other retrieval backends (search_context / retrieve_context).

The OE program uses:
  - Ephemeral in-memory ChromaDB (built once, cached)
  - Unfiltered semantic search (20 candidates)
  - Heuristic reranking (register name match + tables + cosine)
  - Top 6 results + bidirectional neighbor expansion
"""

import os
import importlib.util
import sys
from typing import Optional, Tuple

from utils.utils import setup_logger

logger = setup_logger(__name__)

# Cache for the loaded module and its database
_oe_module = None
_oe_collection = None
_oe_processed_chunks = None


def _load_oe_module():
    """Load the best evolved program module."""
    global _oe_module

    if _oe_module is not None:
        return _oe_module

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    program_path = os.path.join(
        project_root, "openevolve_retrieval", "output_rm0041", "best", "best_program.py"
    )

    if not os.path.exists(program_path):
        raise FileNotFoundError(f"OE best program not found: {program_path}")

    # Ensure _shared_cache is importable (lives in openevolve_retrieval/)
    oe_package_dir = os.path.join(project_root, "openevolve_retrieval")
    if oe_package_dir not in sys.path:
        sys.path.insert(0, oe_package_dir)

    spec = importlib.util.spec_from_file_location("oe_best_program", program_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _oe_module = mod
    return mod


def _ensure_database(chunks_dir: str, chunks_index_csv: str):
    """Build the OE ephemeral database (cached after first call)."""
    global _oe_collection, _oe_processed_chunks

    if _oe_collection is not None:
        return

    mod = _load_oe_module()
    logger.info("Building OE ephemeral database...")
    _oe_collection, _oe_processed_chunks = mod.setup_database(chunks_dir, chunks_index_csv)
    logger.info("OE database ready")


def search_openevolve(
    peripheral_name: str,
    register_name: str,
    chunks_dir: str,
    chunks_index_csv: str,
) -> str:
    """Retrieve context for a single register using OE's evolved retrieval.

    Returns formatted context string (same format OE uses: [Page N] blocks).
    """
    _ensure_database(chunks_dir, chunks_index_csv)
    mod = _load_oe_module()

    return mod.run_retrieval(
        peripheral_name, register_name,
        _oe_collection, _oe_processed_chunks,
    )


def search_openevolve_for_peripheral(
    peripheral_name: str,
    register_names: list[str],
    chunks_dir: str,
    chunks_index_csv: str,
) -> Tuple[Optional[str], list]:
    """Retrieve context for a batch of registers using per-register OE retrieval.

    Calls OE's retrieval per register, deduplicates page blocks, and returns
    a single formatted context string. This matches the PER_REGISTER_TRIMMED
    strategy — each register gets its own retrieval, results are unioned.

    Returns:
        (formatted_text, []) — same shape as retrieve_context_for_peripheral().
    """
    _ensure_database(chunks_dir, chunks_index_csv)
    mod = _load_oe_module()

    seen_blocks: set[str] = set()
    all_blocks: list[tuple[int, str]] = []  # (page_number, block_text)

    for reg in register_names:
        context = mod.run_retrieval(
            peripheral_name, reg,
            _oe_collection, _oe_processed_chunks,
        )
        if not context:
            continue

        # Parse OE's format: "[Page N]\n..." blocks separated by "\n\n---\n\n"
        for block in context.split("\n\n---\n\n"):
            block = block.strip()
            if not block:
                continue
            # Deduplicate by content
            if block in seen_blocks:
                continue
            seen_blocks.add(block)

            # Extract page number for sorting
            page = 0
            if block.startswith("[Page "):
                try:
                    page = int(block.split("]")[0].replace("[Page ", ""))
                except (ValueError, IndexError):
                    pass
            all_blocks.append((page, block))

    if not all_blocks:
        return None, []

    # Sort by page number for coherent reading order
    all_blocks.sort(key=lambda x: x[0])

    # Wrap in XML format to match the pipeline's expected output
    parts = []
    for page, block in all_blocks:
        parts.append(f"<result page='{page}' source='openevolve' expansion='false'>"
                     f"<content>{block}</content></result>")

    formatted = f"<sources>{''.join(parts)}</sources>"
    return formatted, []
