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
from types import ModuleType
from typing import Any, Dict, List, Optional, Tuple

from utils.utils import setup_logger

logger = setup_logger(__name__)

# Default OE program — used when callers don't pass an explicit program_path.
# Kept so the runtime pipeline (which doesn't know about per-device OE programs)
# still works without modification.
_DEFAULT_PROGRAM_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..",
    "openevolve_retrieval", "output_rm0041", "best", "best_program.py",
))

# Module cache: program_path → loaded module (the evolved program itself does not
# depend on which datasheet's chunks are used).
_module_cache: Dict[str, ModuleType] = {}
# Ephemeral-DB cache keyed by (program_path, chunks_index_csv) so DIFFERENT
# datasheets keep DISTINCT databases even under the same program. (Keying by
# program alone made multi-device runs in one process retrieve against the first
# device's chunks.)
_db_cache: Dict[Tuple[str, str], Tuple[Any, List[Dict[str, Any]]]] = {}


def _resolve_program_path(program_path: Optional[str]) -> str:
    """Resolve to an absolute path, falling back to the legacy default."""
    path = program_path or _DEFAULT_PROGRAM_PATH
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"OE program not found: {path}")
    return path


def _load_oe_module(program_path: Optional[str] = None) -> ModuleType:
    """Load an evolved program module (cached per absolute path)."""
    resolved = _resolve_program_path(program_path)
    cached = _module_cache.get(resolved)
    if cached is not None:
        return cached

    # Ensure _shared_cache is importable (lives in openevolve_retrieval/)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    oe_package_dir = os.path.join(project_root, "openevolve_retrieval")
    if oe_package_dir not in sys.path:
        sys.path.insert(0, oe_package_dir)

    # Use a path-derived module name so importlib doesn't collide when several
    # programs are loaded in the same process.
    module_name = f"oe_program_{abs(hash(resolved))}"
    spec = importlib.util.spec_from_file_location(module_name, resolved)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _module_cache[resolved] = mod
    return mod


def _ensure_database(
    chunks_dir: str,
    chunks_index_csv: str,
    program_path: Optional[str] = None,
) -> Tuple[Any, List[Dict[str, Any]]]:
    """Build the OE ephemeral database for (program, chunks) (cached after first call)."""
    resolved = _resolve_program_path(program_path)
    key = (resolved, os.path.abspath(chunks_index_csv))
    cached = _db_cache.get(key)
    if cached is not None:
        return cached

    mod = _load_oe_module(resolved)
    logger.info(
        f"Building OE ephemeral database for {os.path.basename(resolved)} "
        f"+ {os.path.basename(chunks_index_csv)}..."
    )
    collection, processed_chunks = mod.setup_database(chunks_dir, chunks_index_csv)
    _db_cache[key] = (collection, processed_chunks)
    logger.info("OE database ready")
    return collection, processed_chunks


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


def _parse_oe_page_blocks(
    context: str,
    seen_blocks: Optional[set] = None,
) -> List[Tuple[int, str]]:
    """Parse OE's `[Page N]\\n...\\n\\n---\\n\\n[Page M]\\n...` format into
    a list of `(page_number, block_text)` tuples.

    If `seen_blocks` is provided, it's a mutable set used to deduplicate
    across multiple calls (needed by the batched code path which unions
    blocks across registers). When None, no cross-call dedup happens.
    """
    if not context:
        return []
    blocks: List[Tuple[int, str]] = []
    for block in context.split("\n\n---\n\n"):
        block = block.strip()
        if not block:
            continue
        if seen_blocks is not None:
            if block in seen_blocks:
                continue
            seen_blocks.add(block)
        page = 0
        if block.startswith("[Page "):
            try:
                page = int(block.split("]")[0].replace("[Page ", ""))
            except (ValueError, IndexError):
                pass
        blocks.append((page, block))
    return blocks


def _format_oe_blocks_as_xml(blocks: List[Tuple[int, str]]) -> Optional[str]:
    """Sort `[(page, block_text), ...]` by page and wrap as per-page XML.

    Produces the canonical `<sources><result page='N' source='openevolve' ...>
    <content>{block}</content></result>...</sources>` format that the other
    retrieval backends emit via `post_processing.format_results()`.

    Returns None if `blocks` is empty.
    """
    if not blocks:
        return None
    sorted_blocks = sorted(blocks, key=lambda x: x[0])
    parts = [
        f"<result page='{page}' source='openevolve' expansion='false'>"
        f"<content>{block}</content></result>"
        for page, block in sorted_blocks
    ]
    return f"<sources>{''.join(parts)}</sources>"


def search_openevolve(
    peripheral_name: str,
    register_name: str,
    chunks_dir: str,
    chunks_index_csv: str,
    program_path: Optional[str] = None,
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """Retrieve context for a single register using OE's evolved retrieval.

    Args:
        program_path: Path to an evolved best_program.py. None falls back to
            the legacy rm0041 default so the runtime pipeline still works.

    Returns:
        (formatted, embedding_ids) — formatted is the canonical per-page
        `<sources>...</sources>` XML (matches format_results from
        post_processing.py and the batched OE path). embedding_ids is a
        list of dicts compatible with the standard
        `info/embedding_ids.jsonl` schema (see _extract_embedding_ids).
    """
    collection, processed_chunks = _ensure_database(
        chunks_dir, chunks_index_csv, program_path,
    )
    mod = _load_oe_module(program_path)

    raw = mod.run_retrieval(
        peripheral_name, register_name,
        collection, processed_chunks,
    )
    # embedding_ids extraction needs the raw OE block format — must happen
    # before we wrap into XML.
    embedding_ids = _extract_embedding_ids(
        raw or "", processed_chunks or [], chunks_dir,
    )
    blocks = _parse_oe_page_blocks(raw)
    return _format_oe_blocks_as_xml(blocks), embedding_ids


def search_openevolve_for_peripheral(
    peripheral_name: str,
    register_names: list[str],
    chunks_dir: str,
    chunks_index_csv: str,
    program_path: Optional[str] = None,
) -> Tuple[Optional[str], list]:
    """Retrieve context for a batch of registers using per-register OE retrieval.

    Calls OE's retrieval per register, deduplicates page blocks, and returns
    a single formatted context string. This matches the PER_REGISTER_TRIMMED
    strategy — each register gets its own retrieval, results are unioned.

    Args:
        program_path: Path to an evolved best_program.py. None falls back to
            the legacy rm0041 default.

    Returns:
        (formatted_text, []) — same shape as retrieve_context_for_peripheral().
    """
    collection, processed_chunks = _ensure_database(
        chunks_dir, chunks_index_csv, program_path,
    )
    mod = _load_oe_module(program_path)

    seen_blocks: set[str] = set()
    all_blocks: list[tuple[int, str]] = []  # (page_number, block_text)
    seen_chunk_ids: set[str] = set()
    embedding_ids: List[Dict[str, Any]] = []

    for reg in register_names:
        context = mod.run_retrieval(
            peripheral_name, reg,
            collection, processed_chunks,
        )
        if not context:
            continue

        # Capture per-register embedding_ids and union across registers.
        # Each register's call retrieves chunks for that register; we record
        # the union (deduped by chunk_id) so the JSONL row reflects what the
        # generator actually sees for the batch.
        for item in _extract_embedding_ids(context, processed_chunks or [], chunks_dir):
            cid = item["chunk_id"]
            if cid in seen_chunk_ids:
                continue
            seen_chunk_ids.add(cid)
            embedding_ids.append({**item, "rank": len(embedding_ids)})

        # Parse + dedup OE page blocks (shared with single-register path).
        all_blocks.extend(_parse_oe_page_blocks(context, seen_blocks=seen_blocks))

    formatted = _format_oe_blocks_as_xml(all_blocks)
    if formatted is None:
        return None, []
    return formatted, embedding_ids
