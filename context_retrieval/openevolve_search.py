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
from typing import Any, Dict, List, Optional, Tuple

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


def _extract_embedding_ids(
    formatted: str,
    processed_chunks: List[Dict[str, Any]],
    chunks_dir: str = "",
) -> List[Dict[str, Any]]:
    """Parse a `[Page N]\\n{doc}` block string and recover one embedding_ids
    record per block by matching `doc` against the cached processed chunks.

    The chunk_id stored in each processed chunk's metadata is the original
    `chunked_datasheets/.../rm0041_pNNN_cNN.txt` source path, which is the
    same identifier the persistent local DB uses as `source`. That makes OE
    runs scoreable against the same per-chunk `reg_*` ground truth.

    Caveat: OE sorts its formatted output by page number, not retrieval
    relevance (see best_program.py:search_and_format). So the `rank` field
    we emit reflects document order, not score order — MRR computed from this
    is misleading; recall@k / precision@k / hit@k (set-membership) are valid.
    """
    if not formatted:
        return []

    text_to_meta: Dict[str, Dict[str, Any]] = {}
    for pc in processed_chunks:
        key = pc.get("text", "").strip()
        if key:
            text_to_meta[key] = pc.get("metadata", {})

    out: List[Dict[str, Any]] = []
    rank = 0
    for block in formatted.split("\n\n---\n\n"):
        block = block.strip()
        if not block.startswith("[Page "):
            continue
        try:
            first_newline = block.index("\n")
        except ValueError:
            continue
        doc_text = block[first_newline + 1:].strip()
        meta = text_to_meta.get(doc_text)
        if meta is None:
            continue
        bare_chunk_id = meta.get("chunk_id", "")
        if not bare_chunk_id:
            continue
        # OE stores chunk_id as the bare stem ("rm0041_p048_c01"); the persistent
        # local DB uses the full source path ("chunked_datasheets/.../rm0041_p048_c01.txt").
        # Emit the full-path form so OE records can be cross-referenced against the
        # persistent DB's `reg_*` ground truth for retrieval-quality scoring.
        full_source = (
            f"{chunks_dir.rstrip('/')}/{bare_chunk_id}.txt"
            if chunks_dir else bare_chunk_id
        )
        out.append({
            "rank": rank,
            "score": None,  # OE doesn't expose its rerank score outside the evolve block
            "source": full_source,
            "chunk_id": full_source,
            "page_number": meta.get("page_number", 0),
            "chunk_index": meta.get("chunk_index", 0),
            "rank_meaning": "document_order",
        })
        rank += 1
    return out


def search_openevolve(
    peripheral_name: str,
    register_name: str,
    chunks_dir: str,
    chunks_index_csv: str,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Retrieve context for a single register using OE's evolved retrieval.

    Returns:
        (formatted, embedding_ids) — formatted is OE's `[Page N]` block string;
        embedding_ids is a list of dicts compatible with the standard
        `info/embedding_ids.jsonl` schema (see _extract_embedding_ids).
    """
    _ensure_database(chunks_dir, chunks_index_csv)
    mod = _load_oe_module()

    formatted = mod.run_retrieval(
        peripheral_name, register_name,
        _oe_collection, _oe_processed_chunks,
    )
    embedding_ids = _extract_embedding_ids(
        formatted or "", _oe_processed_chunks or [], chunks_dir,
    )
    return formatted, embedding_ids


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
    seen_chunk_ids: set[str] = set()
    embedding_ids: List[Dict[str, Any]] = []

    for reg in register_names:
        context = mod.run_retrieval(
            peripheral_name, reg,
            _oe_collection, _oe_processed_chunks,
        )
        if not context:
            continue

        # Capture per-register embedding_ids and union across registers.
        # Each register's call retrieves chunks for that register; we record
        # the union (deduped by chunk_id) so the JSONL row reflects what the
        # generator actually sees for the batch.
        for item in _extract_embedding_ids(context, _oe_processed_chunks or [], chunks_dir):
            cid = item["chunk_id"]
            if cid in seen_chunk_ids:
                continue
            seen_chunk_ids.add(cid)
            embedding_ids.append({**item, "rank": len(embedding_ids)})

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
    return formatted, embedding_ids
