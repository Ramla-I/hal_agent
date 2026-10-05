"""
OpenEvolve initial program: Datasheet retrieval pipeline.

This program defines the full retrieval pipeline that OpenEvolve will evolve:
  1. process_chunks()    — preprocess raw markdown chunks + build metadata
  2. build_query()       — construct search query for a register
  3. search_and_format() — search the vector DB, post-process, and format context

The code inside the EVOLVE-BLOCK is what the LLM mutates each iteration.
Everything outside (imports, DB setup, entry point) stays fixed.
"""

import os
import sys
import re
import csv
import json
from typing import List, Dict, Any, Optional, Tuple

# ---------------------------------------------------------------------------
# Fixed infrastructure (NOT evolved)
# ---------------------------------------------------------------------------

# Resolve project root so we can import hal_agent modules
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Ensure openevolve_retrieval package is importable for shared cache
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
if _PACKAGE_DIR not in sys.path:
    sys.path.insert(0, _PACKAGE_DIR)

import chromadb
from chromadb.config import Settings

# Use hal_agent's local embedding provider (FastEmbed, free, no API calls)
from context_retrieval.vector_db.embeddings import FastEmbedProvider

# Shared embedding cache — persists across dynamically-loaded evolved modules
from _shared_cache import compute_embeddings_cached

_embedding_provider = None


def get_embedding_provider():
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = FastEmbedProvider()
    return _embedding_provider


def load_raw_chunks(chunks_dir: str, chunks_index_csv: str) -> List[Dict[str, Any]]:
    """Load raw chunk texts and metadata from disk.

    Returns list of dicts with keys:
        text, page_number, chunk_index, chunk_id, source, token_count
    """
    chunks = []
    with open(chunks_index_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            chunk_id = row["chunk_id"]
            # Resolve chunk file: prefer chunks_dir/{chunk_id}.txt over CSV file_path
            file_path = os.path.join(chunks_dir, f"{chunk_id}.txt")
            if not os.path.exists(file_path):
                # Fallback to CSV file_path relative to project root
                file_path = os.path.join(
                    _PROJECT_ROOT,
                    row.get("file_path", ""),
                )
            if not os.path.exists(file_path):
                continue
            with open(file_path, "r") as cf:
                text = cf.read()
            chunks.append({
                "text": text,
                "page_number": int(row.get("page_number", 0)),
                "chunk_index": int(row.get("chunk_index", 0)),
                "chunk_id": chunk_id,
                "source": file_path,
                "token_count": int(row.get("token_count", 0)),
            })
    return chunks


_MAX_ADD = 5000


def build_ephemeral_store(processed_chunks: List[Dict[str, Any]]) -> chromadb.Collection:
    """Build an in-memory ChromaDB collection from processed chunks.

    Uses the shared embedding cache so unchanged chunk texts are not re-embedded.
    """
    provider = get_embedding_provider()
    client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
    collection = client.get_or_create_collection("docs", metadata={"hnsw:space": "cosine"})

    texts = [c["text"] for c in processed_chunks]
    metadatas = []
    for c in processed_chunks:
        meta = dict(c.get("metadata", {}))
        # ChromaDB metadata values must be str, int, float, or bool
        for k, v in list(meta.items()):
            if isinstance(v, list):
                meta[k] = json.dumps(v)
            elif v is None:
                del meta[k]
        metadatas.append(meta)

    embeddings = compute_embeddings_cached(texts, provider)
    ids = [f"doc_{i}" for i in range(len(processed_chunks))]
    # ChromaDB rejects a single add above ~5461 records, and the larger
    # reference manuals are already at that scale (RM0433 is 5183 chunks, and it
    # is not the biggest one shipped). Both evolved winners were hand-patched
    # after the fact for exactly this; batching here means a run evolved on a
    # large manual does not die on its first evaluation.
    for start in range(0, len(ids), _MAX_ADD):
        stop = start + _MAX_ADD
        collection.add(
            ids=ids[start:stop],
            documents=texts[start:stop],
            embeddings=embeddings[start:stop],
            metadatas=metadatas[start:stop],
        )
    return collection


# EVOLVE-BLOCK-START
def process_chunks(raw_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    processed = []
    for chunk in raw_chunks:
        processed.append({
            "text": chunk["text"],
            "metadata": {
                "chunk_id": chunk["chunk_id"],
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
            },
        })
    return processed


def _build_spaced_regex(name: str, allow_bank: bool = False) -> str:
    """Build regex handling OCR spaces/markdown and parameterized digits/ports."""
    parts = []
    for c in name:
        if allow_bank and (c.isdigit() or c in 'xXnN'):
            parts.append(r'(?:[0-9xXnN]|\s*[0-9xXnN]\s*)')
        else:
            parts.append(re.escape(c))
    return r'[\s_\-\*`#]*'.join(parts)


def build_query(peripheral_name: str, register_name: str) -> str:
    p_up = peripheral_name.upper()
    r_up = register_name.upper()
    return f"{p_up}_{r_up} {p_up} {r_up} register address offset reset value bit fields table"


def search_and_format(
    collection: "chromadb.Collection",
    query: str,
    embedding_fn,
    peripheral_name: str,
    register_name: str,
    all_processed_chunks: List[Dict[str, Any]],
) -> str:
    p_up = peripheral_name.upper()
    r_up = register_name.upper()
    full_name = f"{p_up}_{r_up}"

    # Generate peripheral base families (e.g. FGPIOA -> GPIOA, GPIO; FTM0 -> FTM; UART0 -> UART)
    p_base = re.sub(r'\d+$', '', p_up)
    p_base_stripped = p_base[1:] if p_base.startswith('F') and len(p_base) > 2 else p_base
    p_core = re.sub(r'[A-Z]$', '', p_base_stripped) if len(p_base_stripped) > 2 else p_base_stripped

    # Generate specific banked register patterns without digit wildcards
    r_candidates = [r_up]
    if re.search(r'\d+', r_up):
        r_candidates.append(re.sub(r'\d+', 'n', r_up))
        r_candidates.append(re.sub(r'\d+', 'x', r_up))
        r_candidates.append(re.sub(r'(\d+)', r' \1 ', r_up))
        r_candidates.append(re.sub(r'(\d+)', r' n ', r_up))
        r_candidates.append(re.sub(r'(\d+)', r' x ', r_up))

    exact_full_pat = re.compile(r'\b' + _build_spaced_regex(full_name) + r'\b', re.I)

    p_patterns = list(set(filter(None, [p_up, p_base, p_base_stripped, p_core])))
    p_pat_str = '|'.join(_build_spaced_regex(p, allow_bank=True) for p in p_patterns)

    r_patterns = list(set(filter(None, r_candidates)))
    r_pat_str = '|'.join(_build_spaced_regex(r, allow_bank=False) for r in r_patterns)

    heading_pat = re.compile(
        rf'#+.*?(?:{p_pat_str})[\s_\-\*`#]*(?:x|n|\d)?[\s_\-\*`#]*(?:{r_pat_str})',
        re.I
    )
    paren_reg_pat = re.compile(
        rf'\([\s\*`#]*(?:(?:{p_pat_str})[\s_\-\*`#]*(?:x|n|\d)?[\s_\-\*`#]*)?(?:{r_pat_str})[\s\*`#]*\)',
        re.I
    )

    offset_pat = re.compile(r'(?:address\s*offset|offset)\s*[:=]?\s*0?x?[0-9a-fA-F]+', re.I)
    reset_pat = re.compile(r'reset\s*(?:value)?\s*[:=]?', re.I)
    table_pat = re.compile(r'\|(?:\s*Bits?\s*|\s*\d+\s*)\|', re.I)
    summary_map_pat = re.compile(r'memory\s*map|register\s*summary', re.I)

    # 1. Vector Search Candidates
    query_embedding = embedding_fn([query])[0]
    n_search = min(15, len(all_processed_chunks))
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_search,
        include=["documents", "metadatas", "distances"],
    )

    candidate_map = {}
    docs = results["documents"][0] if results.get("documents") and results["documents"] else []
    metas = results["metadatas"][0] if results.get("metadatas") and results["metadatas"] else []
    dists = results["distances"][0] if results.get("distances") and results["distances"] else []

    for doc, meta, dist in zip(docs, metas, dists):
        cid = meta.get("chunk_id")
        candidate_map[cid] = {
            "text": doc,
            "metadata": meta,
            "vec_sim": 1.0 - (dist if dist is not None else 0.5),
        }

    # 2. Add candidates with direct heading or pattern hits across whole corpus
    for chunk in all_processed_chunks:
        cid = chunk["metadata"]["chunk_id"]
        if cid not in candidate_map:
            text = chunk["text"]
            if heading_pat.search(text) or paren_reg_pat.search(text) or exact_full_pat.search(text):
                candidate_map[cid] = {
                    "text": text,
                    "metadata": chunk["metadata"],
                    "vec_sim": 0.0,
                }

    # 3. Score candidate chunks
    scored_candidates = []
    for cid, data in candidate_map.items():
        text = data["text"]
        score = data["vec_sim"] * 10.0

        has_heading = bool(heading_pat.search(text))
        has_paren = bool(paren_reg_pat.search(text))
        has_exact = bool(exact_full_pat.search(text))
        has_offset = bool(offset_pat.search(text))
        has_reset = bool(reset_pat.search(text))
        has_table = bool(table_pat.search(text) or "|" in text)
        is_summary = bool(summary_map_pat.search(text))

        if has_heading:
            score += 70.0
        if has_paren:
            score += 50.0
        if has_exact:
            score += 30.0

        if has_offset:
            score += 25.0
        if has_reset:
            score += 15.0
        if has_table:
            score += 10.0

        # Penalize pure memory map tables that list all registers without section headings
        if is_summary and not has_heading:
            score -= 50.0

        if score > 20.0:
            scored_candidates.append((score, data))

    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    if not scored_candidates:
        if candidate_map:
            best_c = next(iter(candidate_map.values()))
            page = best_c["metadata"].get("page_number", "?")
            return f"[Page {page}]\n{best_c['text']}"
        return ""

    # 4. Select top definition chunk and multi-chunk continuation
    top_score, top_candidate = scored_candidates[0]
    top_cid = top_candidate["metadata"]["chunk_id"]

    chunk_id_to_idx = {c["metadata"]["chunk_id"]: i for i, c in enumerate(all_processed_chunks)}
    best_idx = chunk_id_to_idx.get(top_cid, 0)

    # Check if preceding chunk was the definition header
    top_text = top_candidate["text"]
    if not (offset_pat.search(top_text) or heading_pat.search(top_text)) and best_idx > 0:
        prev_chunk = all_processed_chunks[best_idx - 1]
        prev_text = prev_chunk["text"]
        if (heading_pat.search(prev_text) or paren_reg_pat.search(prev_text) or exact_full_pat.search(prev_text)) and offset_pat.search(prev_text):
            best_idx = best_idx - 1

    selected_indices = [best_idx]

    # Expand forward for continuation chunks (up to 5 subsequent chunks)
    for next_idx in range(best_idx + 1, min(len(all_processed_chunks), best_idx + 6)):
        next_chunk = all_processed_chunks[next_idx]
        next_text = next_chunk["text"]

        # Stop expansion if next chunk introduces a completely new register definition
        has_new_reg = bool(re.search(r'(?:^|\n)\s*#{1,6}\s+.*?\([A-Z0-9_\s\*`#-]+\)', next_text))
        has_new_offset = bool(re.search(r'\b(?:address\s*offset|offset)\s*[:=]?\s*0?x?[0-9a-fA-F]+', next_text, re.I))
        has_section_num = bool(re.search(r'(?:^|\n)\s*#{1,6}\s+\d+\.\d+\.\d+', next_text))

        if (has_new_reg and has_new_offset) or (has_new_reg and has_section_num) or (has_new_offset and "register" in next_text.lower() and "#" in next_text):
            break

        # Check for field tables, bit descriptions, or register continuation markers
        is_continuation = (
            "|" in next_text
            or bool(re.search(r'\b(rw|ro|wo|w1c|bits?|field|fields|description|descriptions|reset|reserved|function|value|0x[0-9a-fA-F]+)\b', next_text, re.I))
        )
        if is_continuation:
            selected_indices.append(next_idx)
        else:
            break

    selected_chunks = [all_processed_chunks[i] for i in sorted(set(selected_indices))]

    parts = []
    for c in selected_chunks:
        page = c["metadata"].get("page_number", "?")
        parts.append(f"[Page {page}]\n{c['text']}")

    return "\n\n---\n\n".join(parts)
# EVOLVE-BLOCK-END


# ---------------------------------------------------------------------------
# Entry point called by the evaluator
# ---------------------------------------------------------------------------

_collection_cache = None
_processed_chunks_cache = None


def setup_database(chunks_dir: str, chunks_index_csv: str) -> Tuple:
    """Build the vector DB from raw chunks. Called once per evaluation."""
    global _collection_cache, _processed_chunks_cache

    raw_chunks = load_raw_chunks(chunks_dir, chunks_index_csv)
    processed = process_chunks(raw_chunks)
    collection = build_ephemeral_store(processed)
    _collection_cache = collection
    _processed_chunks_cache = processed
    return collection, processed


def run_retrieval(
    peripheral_name: str,
    register_name: str,
    collection=None,
    processed_chunks=None,
) -> str:
    """Retrieve context for a single register. Called once per register."""
    col = collection or _collection_cache
    chunks = processed_chunks or _processed_chunks_cache
    if col is None:
        raise RuntimeError("Call setup_database() first")

    provider = get_embedding_provider()
    query = build_query(peripheral_name, register_name)
    return search_and_format(
        col, query, provider.embed, peripheral_name, register_name, chunks
    )
