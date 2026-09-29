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
    """Preprocess raw markdown chunks and attach metadata.

    Called once per evaluation. Takes raw chunk dicts and returns processed
    chunk dicts ready for vector DB ingestion.

    Each returned dict must have:
        - "text": str  (the text to embed and store)
        - "metadata": dict  (searchable metadata — values must be str/int/float/bool)

    Available raw chunk fields:
        text, page_number, chunk_index, chunk_id, source, token_count

    You are free to:
        - Modify chunk text (add headers, extract key terms, summarize)
        - Split or merge chunks
        - Compute and attach metadata (register names, has_tables, section, etc.)
        - Filter out irrelevant chunks

    Keep `chunk_id` (or page_number + chunk_index) in the metadata. Scoring
    traces each returned block back to the chunk it came from; a block that
    cannot be traced counts as nothing retrieved, however good it was.
    """
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


def build_query(peripheral_name: str, register_name: str) -> str:
    """Construct a concise search query for retrieving register definition."""
    p = peripheral_name.upper()
    r = register_name.upper()
    return f"{p}_{r} {r} register address offset reset value bit fields table rw"


def _make_fuzzy_pattern(name: str) -> re.Pattern:
    """Build a regex pattern resilient to interleaved whitespace and markdown formatting."""
    escaped = [re.escape(c) for c in name]
    pattern_str = r"[\s\_*`\-]*".join(escaped)
    return re.compile(pattern_str, re.IGNORECASE)


def _get_peripheral_aliases(p_name: str) -> List[str]:
    """Generate family aliases for peripherals across MCU vendor manual conventions."""
    p = p_name.upper().strip()
    aliases = {p}
    base = re.sub(r"\d+$|[A-Z]$", "", p) if len(p) > 3 else re.sub(r"\d+$", "", p)
    if base:
        aliases.update([base, f"{base}x", f"{base}X"])

    if p.startswith("UART") or p.startswith("USART"):
        aliases.update(["USART", "USARTx", "USARTX", "UART", "UARTx", "UARTX"])
        num = re.search(r"\d+", p)
        if num:
            aliases.update([f"USART{num.group(0)}", f"UART{num.group(0)}"])
    elif p.startswith("TIM"):
        aliases.update(["TIM", "TIMx", "TIMX"])
    elif p.startswith("GPIO") or p.startswith("PORT"):
        aliases.update(["GPIO", "GPIOx", "GPIOX", "PORT", "PORTx"])
    elif p.startswith("ADC"):
        aliases.update(["ADC", "ADCx", "ADCX"])
    elif p.startswith("DMA"):
        aliases.update(["DMA", "DMAx", "DMAX"])
    elif p.startswith("SPI"):
        aliases.update(["SPI", "SPIx", "SPIX"])
    elif p.startswith("I2C"):
        aliases.update(["I2C", "I2Cx", "I2CX"])
    elif p.startswith("CAN"):
        aliases.update(["CAN", "CANx", "bxCAN"])
    elif p.startswith("FSMC") or p.startswith("FMC"):
        aliases.update(["FSMC", "FMC", "FSMCx", "FMCx"])
    elif p.startswith("BKP"):
        aliases.update(["BKP", "BKPx"])
    elif p.startswith("EXTI"):
        aliases.update(["EXTI", "EXTIx"])
    elif p.startswith("RTC"):
        aliases.update(["RTC", "RTCx"])
    elif p.startswith("DAC"):
        aliases.update(["DAC", "DACx"])
    elif p.startswith("CEC"):
        aliases.update(["CEC", "CECx"])
    elif p.startswith("PWR"):
        aliases.update(["PWR", "PWRx"])
    elif p.startswith("CRC"):
        aliases.update(["CRC", "CRCx"])

    return list(aliases)


def _generate_target_variations(peripheral_name: str, register_name: str) -> List[Tuple[re.Pattern, float, bool]]:
    """Generate prioritized regex patterns with weights and peripheral requirements."""
    p_name = peripheral_name.upper().strip()
    r_name = register_name.upper().strip()
    aliases = _get_peripheral_aliases(p_name)

    r_generic = re.sub(r"\d+$", "x", r_name)
    r_generic_upper = re.sub(r"\d+$", "X", r_name)
    r_base = re.sub(r"\d+$", "", r_name)

    patterns = []
    # Priority 1: Exact full names e.g. GPIOA_CRH, AFIO_EVCR, RCC_APB1ENR, EXTI_PR
    patterns.append((_make_fuzzy_pattern(f"{p_name}_{r_name}"), 145.0, False))
    patterns.append((_make_fuzzy_pattern(f"({p_name}_{r_name})"), 150.0, False))

    # Priority 2: Generic and aliased peripheral combinations e.g. FSMC_BWTRx, GPIOx_CRL
    for pa in aliases:
        is_primary = (pa == p_name)
        w_base = 135.0 if is_primary else 120.0
        if not is_primary:
            patterns.append((_make_fuzzy_pattern(f"{pa}_{r_name}"), w_base, True))
            patterns.append((_make_fuzzy_pattern(f"({pa}_{r_name})"), w_base + 5.0, True))

        if r_generic != r_name:
            patterns.append((_make_fuzzy_pattern(f"{pa}_{r_generic}"), w_base - 5.0, not is_primary))
            patterns.append((_make_fuzzy_pattern(f"({pa}_{r_generic})"), w_base, not is_primary))
            patterns.append((_make_fuzzy_pattern(f"{pa}_{r_generic_upper}"), w_base - 5.0, not is_primary))
            patterns.append((_make_fuzzy_pattern(f"({pa}_{r_generic_upper})"), w_base, not is_primary))
            patterns.append((_make_fuzzy_pattern(f"{pa}_{r_base}x"), w_base - 10.0, not is_primary))
            patterns.append((_make_fuzzy_pattern(f"{pa}_{r_base}X"), w_base - 10.0, not is_primary))

        # Banked ranges e.g. BKP_DRx (x = 1 ..20), FSMC_BCRx, FSMC_BWTRx, FSMC_BWTRX, DMA_CCRx (x = 1..7)
        if r_generic != r_name:
            patterns.append((re.compile(rf"{re.escape(pa)}[xX\d_]*{re.escape(r_base)}\s*[xX]", re.IGNORECASE), 120.0, True))
            patterns.append((re.compile(rf"{re.escape(pa)}[xX\d_]*{re.escape(r_base)}\s*\d+\s*(?:\.\.|\-)\s*\d+", re.IGNORECASE), 120.0, True))

    # Special handling for I2C markup artifacts e.g. I [2] C
    if p_name.startswith("I2C"):
        patterns.append((re.compile(rf"I\s*\[?\s*2\s*\]?\s*C[xX\d_]*{re.escape(r_name)}", re.IGNORECASE), 130.0, False))
        patterns.append((re.compile(rf"I\s*\[?\s*2\s*\]?\s*C[xX\d_]*{re.escape(r_generic)}", re.IGNORECASE), 120.0, False))

    # Priority 3: Short register names (strictly require peripheral context)
    patterns.append((_make_fuzzy_pattern(f"({r_name})"), 95.0, True))
    patterns.append((_make_fuzzy_pattern(f" {r_name} "), 70.0, True))
    if r_generic != r_name:
        patterns.append((_make_fuzzy_pattern(f"({r_generic})"), 90.0, True))
        patterns.append((_make_fuzzy_pattern(f"({r_generic_upper})"), 90.0, True))
        patterns.append((_make_fuzzy_pattern(f"({r_base}x)"), 85.0, True))
        patterns.append((_make_fuzzy_pattern(f"({r_base}X)"), 85.0, True))
        patterns.append((re.compile(rf"\({re.escape(r_base)}\s*[xX]\)", re.IGNORECASE), 90.0, True))

    return patterns


def search_and_format(
    collection: "chromadb.Collection",
    query: str,
    embedding_fn,
    peripheral_name: str,
    register_name: str,
    all_processed_chunks: List[Dict[str, Any]],
) -> str:
    """Search vector DB and heuristic index for authoritative register definitions."""
    p_name = peripheral_name.upper().strip()
    r_name = register_name.upper().strip()
    p_aliases = _get_peripheral_aliases(p_name)
    target_patterns = _generate_target_variations(peripheral_name, register_name)

    p_exact_pat = _make_fuzzy_pattern(p_name)
    p_patterns = [_make_fuzzy_pattern(pa) for pa in p_aliases]

    offset_pat = re.compile(r"address\s*offset\s*[:=]|offset\s*:\s*0?x|address\s*offset", re.IGNORECASE)
    reset_pat = re.compile(r"reset\s*value\s*[:=]?\s*0?x?", re.IGNORECASE)
    bit_table_pat = re.compile(r"\|\s*Bits?\s*\||\|\s*31|\|\s*15|\brw\b|\br/w\b|\bread/write\b|\bset by software\b|\bcleared by software\b", re.IGNORECASE)
    heading_pat = re.compile(r"(?:^|\n)\s*(?:#+\s*|\*\*[\d\.]+\*\*\s*)([^\n]+)", re.IGNORECASE)
    summary_map_pat = re.compile(r"register\s+(?:map|summary)|overview\s+table|\bmemory\s+map\b", re.IGNORECASE)

    p_num_match = re.search(r"\d+", p_name)

    # 1. Direct heuristic chunk scoring across corpus
    chunk_scores: Dict[int, float] = {}
    for idx, c in enumerate(all_processed_chunks):
        text = c["text"]
        has_offset = bool(offset_pat.search(text))
        has_reset = bool(reset_pat.search(text))
        has_table = bool(bit_table_pat.search(text))
        has_periph_exact = bool(p_exact_pat.search(text))
        has_periph_alias = any(pat.search(text) for pat in p_patterns)

        best_match_weight = 0.0
        for pat, weight, req_periph in target_patterns:
            if pat.search(text):
                if req_periph:
                    if has_periph_exact:
                        best_match_weight = max(best_match_weight, weight + 30.0)
                    elif has_periph_alias:
                        best_match_weight = max(best_match_weight, weight + 10.0)
                else:
                    best_match_weight = max(best_match_weight, weight)

        if best_match_weight > 0:
            score = best_match_weight
            if has_offset:
                score += 55.0
            if has_reset:
                score += 35.0
            if has_table:
                score += 25.0

            # Heading analysis with peripheral verification
            headings = heading_pat.findall(text)
            for h in headings:
                matched_heading = False
                for pat, _, req_periph in target_patterns:
                    if pat.search(h):
                        if req_periph and not (has_periph_exact or has_periph_alias):
                            continue
                        score += 75.0
                        if has_periph_exact or any(pa in h.upper() for pa in p_aliases):
                            score += 45.0
                        elif p_num_match:
                            h_nums = re.findall(r"\d+", h)
                            if h_nums and p_num_match.group(0) not in h_nums:
                                score -= 45.0
                        matched_heading = True
                        break
                if matched_heading:
                    break

            # Penalize register summary / overview tables
            if summary_map_pat.search(text) and not (has_offset and has_reset):
                score -= 100.0

            chunk_scores[idx] = score

    # 2. Vector search boost / fallback
    query_embedding = embedding_fn([query])[0]
    n_search = min(15, len(all_processed_chunks))
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_search,
        include=["metadatas", "distances"],
    )

    if results.get("metadatas") and results["metadatas"][0]:
        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            c_idx = meta.get("chunk_index")
            if c_idx is not None and 0 <= c_idx < len(all_processed_chunks):
                sim_score = max(0.0, 1.0 - (dist if dist is not None else 0.5)) * 20.0
                chunk_scores[c_idx] = chunk_scores.get(c_idx, 0.0) + sim_score

    if not chunk_scores:
        return ""

    # 3. Identify authoritative definition anchor
    sorted_candidates = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)
    best_idx, best_score = sorted_candidates[0]

    selected_indices = {best_idx}

    # 4. Multi-chunk bitfield expansion forward
    if best_score >= 70.0:
        curr_idx = best_idx + 1
        new_header_strict = re.compile(
            r"(?:^|\n)\s*(?:#+\s+|\*\*[\d\.]+\*\*\s+\*\*)[^\n]+\(([A-Z0-9_xX]+)\)",
            re.IGNORECASE,
        )
        offset_strict = re.compile(r"address\s*offset\s*[:=]\s*0x|offset\s*:\s*0x", re.IGNORECASE)

        # Check if query register is part of a paired or banked register group
        is_paired_or_banked = bool(re.search(r"[HL]$|\d+$|DHR", r_name))

        while curr_idx < len(all_processed_chunks):
            next_text = all_processed_chunks[curr_idx]["text"]

            # Stop if the chunk starts a summary section
            if summary_map_pat.search(next_text):
                break

            # Stop if starting an entirely distinct register (unless paired/banked like PRLH/PRLL or BCR1..4 or DHR)
            h_match = new_header_strict.search(next_text)
            if h_match and offset_strict.search(next_text):
                extracted_reg = h_match.group(1).upper()
                if not is_paired_or_banked or not any(pa in extracted_reg for pa in p_aliases):
                    break

            if offset_strict.search(next_text) and reset_pat.search(next_text) and not is_paired_or_banked:
                break

            # Continue if chunk contains bitfield descriptions, tables, or register field details
            lower = next_text.lower()
            if (
                bit_table_pat.search(next_text)
                or "bit" in lower
                or "description" in lower
                or "rw" in lower
                or "r/w" in lower
                or "set by software" in lower
                or "cleared by software" in lower
                or "field" in lower
                or "reserved" in lower
                or "table" in lower
                or "access" in lower
            ):
                selected_indices.add(curr_idx)
                curr_idx += 1
                if len(selected_indices) >= 5:  # Cap at max definition span
                    break
            else:
                break
    else:
        for idx, s in sorted_candidates[1:3]:
            if s > 30.0:
                selected_indices.add(idx)

    # Sort selected chunks by natural index order for coherent context
    ordered_indices = sorted(selected_indices)
    parts = []
    for idx in ordered_indices:
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
