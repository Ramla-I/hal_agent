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
    """Preprocess raw markdown chunks and attach metadata."""
    processed = []
    for idx, chunk in enumerate(raw_chunks):
        text = chunk["text"]
        text_lower = text.lower()

        has_offset = bool(re.search(r'(address\s+offset|offset)\s*[:=]?\s*0?x?[0-9a-fA-F]+|\(0x[0-9a-fA-F]+;\s*[A-Z/]+\)', text, re.I))
        has_reset = bool(re.search(r'reset\s+value\s*[:=]?', text_lower))
        has_tables = "|" in text and ("bits" in text_lower or "bit" in text_lower or "---" in text or bool(re.search(r'\|\s*31\s*\|', text)))

        processed.append({
            "text": text,
            "metadata": {
                "chunk_id": chunk["chunk_id"],
                "page_number": chunk["page_number"],
                "chunk_index": chunk.get("chunk_index", idx),
                "has_offset": has_offset,
                "has_reset": has_reset,
                "has_tables": has_tables,
            },
        })
    return processed


def build_query(peripheral_name: str, register_name: str) -> str:
    """Construct a targeted search query for register definition."""
    p = peripheral_name.upper().strip()
    r = register_name.upper().strip()
    p_base = re.sub(r'\d+$', '', p)
    return f"{p}_{r} {p_base}_{r} {r} register address offset reset value bit fields"


def _make_fuzzy_pattern(name: str) -> str:
    """Create regex pattern tolerant to PDF conversion whitespace/formatting artifacts."""
    chars = [c for c in name if c.isalnum()]
    if not chars:
        return re.escape(name)
    pat = r'[\s_\W]*'.join(re.escape(c) for c in chars)
    return r'(?<![A-Za-z0-9])' + pat + r'(?![A-Za-z0-9])'


def search_and_format(
    collection: "chromadb.Collection",
    query: str,
    embedding_fn,
    peripheral_name: str,
    register_name: str,
    all_processed_chunks: List[Dict[str, Any]],
) -> str:
    """Search for the authoritative register definition chunks and return formatted context."""
    p = peripheral_name.upper().strip()
    r = register_name.upper().strip()
    p_base = re.sub(r'\d+$', '', p)

    # Candidate naming variations
    reg_variants = [f"{p}_{r}", f"{p_base}_{r}", f"{p_base}x_{r}", f"{p}{r}", r]
    full_patterns = [_make_fuzzy_pattern(v) for v in reg_variants[:4]]
    reg_patterns = [_make_fuzzy_pattern(r)]

    # Heading patterns specific to register definitions (e.g. "# ... — BPRC (0x04078; RO)" or "### AFIO_EVCR")
    header_patterns = [
        re.compile(r'#+.*?(?:—|\-|\()\s*' + re.escape(r) + r'\b', re.IGNORECASE),
        re.compile(r'#+.*?\b' + re.escape(r) + r'\s*\(0x[0-9a-fA-F]+', re.IGNORECASE),
        re.compile(r'#+.*?\b' + re.escape(f"{p}_{r}") + r'\b', re.IGNORECASE),
        re.compile(r'#+.*?\b' + re.escape(f"{p_base}_{r}") + r'\b', re.IGNORECASE),
        re.compile(r'#+.*?\b' + re.escape(r) + r'\b', re.IGNORECASE),
    ]

    candidate_scores = []
    for idx, c in enumerate(all_processed_chunks):
        text = c["text"]
        text_lower = text.lower()
        meta = c.get("metadata", {})

        score = 0.0

        # Check explicit register section headers
        is_header_match = any(hp.search(text) for hp in header_patterns)
        if is_header_match:
            score += 75.0

        # Check full name matches (e.g. AFIO_EVCR)
        has_full_match = False
        for pat in full_patterns:
            if re.search(pat, text, re.IGNORECASE):
                has_full_match = True
                score += 45.0
                break

        # Check standalone register name match (e.g. EVCR, BPRC)
        if not has_full_match and not is_header_match:
            for pat in reg_patterns:
                if re.search(pat, text, re.IGNORECASE):
                    if p_base.lower() in text_lower or p.lower() in text_lower:
                        score += 35.0
                    elif meta.get("has_offset", False):
                        score += 25.0
                    else:
                        score += 5.0
                    break

        if score > 0:
            if meta.get("has_offset", False):
                score += 30.0
            if meta.get("has_reset", False):
                score += 20.0
            if meta.get("has_tables", False):
                score += 15.0

            # Register overview / summary map penalty
            if "register map" in text_lower and not meta.get("has_reset", False):
                score -= 30.0

            candidate_scores.append((idx, score))

    selected_indices = []
    if candidate_scores:
        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        top_idx, top_score = candidate_scores[0]

        if top_score >= 40.0:
            selected_indices.append(top_idx)

            # Check consecutive chunks for multi-chunk table / description continuation
            curr_idx = top_idx
            while curr_idx + 1 < len(all_processed_chunks) and len(selected_indices) < 5:
                next_chunk = all_processed_chunks[curr_idx + 1]
                next_meta = next_chunk.get("metadata", {})
                next_text = next_chunk["text"]
                next_text_lower = next_text.lower()

                # Check if next chunk starts a distinct new register header (e.g., "# ... — REG (0x...)" or "# ... Register")
                has_other_header = False
                header_matches = re.findall(r'#+.*?(?:—\s*([A-Z0-9_]+)\s*\(0x|\b([A-Z0-9_]+)\s*\(0x[0-9a-fA-F]+|\b([A-Z0-9_]+)_register\b)', next_text, re.IGNORECASE)
                for groups in header_matches:
                    for g in groups:
                        if g and g.upper() not in [r, f"{p}_{r}", f"{p_base}_{r}", f"{p}{r}"]:
                            has_other_header = True
                            break
                    if has_other_header:
                        break

                has_new_offset = bool(re.search(r'(address\s+offset|offset)\s*[:=]\s*0?x[0-9a-fA-F]+', next_text, re.I)) and not any(hp.search(next_text) for hp in header_patterns)

                if has_other_header or has_new_offset:
                    break

                # Continue if it is adjacent in page order and contains tables, bit fields, or register descriptions
                page_diff = abs(next_meta.get("page_number", 0) - all_processed_chunks[curr_idx]["metadata"].get("page_number", 0))
                is_continuation = (
                    next_meta.get("has_tables", False)
                    or "bits" in next_text_lower
                    or "bit " in next_text_lower
                    or "field" in next_text_lower
                    or "description" in next_text_lower
                    or "rw" in next_text_lower
                    or "ro" in next_text_lower
                    or "reset" in next_text_lower
                    or "|" in next_text
                )

                if page_diff <= 1 and is_continuation:
                    selected_indices.append(curr_idx + 1)
                    curr_idx += 1
                else:
                    break

    # Vector search fallback if heuristic found nothing strong
    if not selected_indices:
        query_embedding = embedding_fn([query])[0]
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=2,
            include=["documents", "metadatas", "distances"],
        )
        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []

        parts = []
        for doc, meta in zip(docs, metas):
            page = meta.get("page_number", "?")
            parts.append(f"[Page {page}]\n{doc}")
        return "\n\n---\n\n".join(parts)

    selected_indices = sorted(set(selected_indices))
    parts = []
    for idx in selected_indices:
        chunk = all_processed_chunks[idx]
        page = chunk.get("metadata", {}).get("page_number", chunk.get("page_number", "?"))
        parts.append(f"[Page {page}]\n{chunk['text']}")

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
