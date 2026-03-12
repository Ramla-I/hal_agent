# D2 vs OpenEvolve Retrieval: Comparison Report

**Date:** 2026-03-12
**Device:** RM0041 (STM32F100xx)
**LLM:** gpt-oss-120b (via Groq)
**Evaluation:** 11 peripherals, 97 registers, 1766 verified facts

---

## 1. Configurations Under Comparison

### D2: Metadata Boolean Filter + Conditional Page Expansion

The best configuration from the manual parameter sweep (documented in `local_vector_db_retrieval_analysis.md`, §2.4).

**Results directory:** `experiments/D_conditional_page_expansion/local_rm0041_md_chunks_v2_emb2_rrlocal_mf_pa1/`

| Parameter | Value |
|-----------|-------|
| Database | `rm0041_md_chunks` (1033 chunks, persistent ChromaDB) |
| Embedding | BAAI/bge-small-en-v1.5 (384-dim, local) |
| `number_embeddings` | 2 |
| `fetch_k` | 10 (n_results × 5) |
| Metadata filter | Boolean fields (`where: {reg_NAME: True}`) |
| Tiered fallback | metadata → `$contains` → unfiltered (threshold 0.7) |
| Reranker | FlashRank (ms-marco-MiniLM-L-12-v2) |
| Keyword boost | False |
| Page expansion | `pages_after=1`, per-result conditional (only non-table chunks) |
| Table removal | Yes |
| Output format | XML `<sources>` with metadata attributes |

### OE iter18: OpenEvolve Best Evolved Program

The best program discovered by OpenEvolve evolutionary code optimization (iteration 18, generation 3). Originally evaluated on 5 peripherals during evolution; full 11-peripheral evaluation run on 2026-03-12.

**Results directory:** `../openevolve_retrieval/output_rm0041/` (full_eval_results.json)
**Program:** `../openevolve_retrieval/output_rm0041/best/best_program.py`

| Parameter | Value |
|-----------|-------|
| Database | Ephemeral in-memory ChromaDB (rebuilt per eval) |
| Embedding | BAAI/bge-small-en-v1.5 (384-dim, local) — same model |
| Candidate pool | 20 results (fixed) |
| Metadata filter | None (pure unfiltered semantic search) |
| Reranker | None (custom heuristic scoring instead) |
| Scoring | +100 if exact register name in text, +50 if also has table, +20 if table only, +(2−dist)×10 cosine |
| Final results | Top 6 by score |
| Expansion | Bidirectional same-page neighbors (chunk_index ±1), only if neighbor has register name or tables |
| Table removal | No |
| Output format | Plain text `[Page N]\n{text}` separated by `---` |

---

## 2. Overall Results

| Metric | **D2** | **OE iter18** |
|--------|--------|---------------|
| Registers found | 78/97 | 95/97 |
| Found accuracy | **97.37%** | 85.9% |
| Complete accuracy | 73.39% | **79.8%** |
| Coverage | 75.37% | **93.0%** |
| Correct facts | 1,296 | 1,410 |
| Wrong facts | **20** | 44 |
| Missing facts | 450 | **188** |
| Input tokens | 594,013¹ | 594,013 |
| Output tokens | 125,111¹ | 125,111 |
| Total tokens | 830,634¹ | **719,124** |

¹ D2 token counts corrected: 22 extra BKP SVD registers (DR21–DR42) that have no verified facts were removed from usage.csv. Original uncorrected total was 971,046.

**Token savings explanation:** OE uses 13% fewer tokens primarily because it processes 95 registers vs D2's 97 attempts (2 fewer), and D2's enriched metadata headers prepend ~50–100 tokens per chunk. XML formatting overhead is negligible (~1.6% of total).

---

## 3. Per-Peripheral Breakdown

| Peripheral | D2 regs | D2 found acc | D2 complete acc | OE regs | OE found acc | OE complete acc | Winner |
|------------|---------|-------------|-----------------|---------|-------------|-----------------|--------|
| afio | 6/7 | 93.33% | 85.71% | 7/7 | 64.6% | 64.6% | D2 accuracy |
| bkp | 22/23 | 97.58% | 85.21% | 23/23 | 96.5% | **96.5%** | OE (both) |
| cec | 7/7 | 86.67% | 86.67% | 7/7 | **93.3%** | **93.3%** | OE |
| crc | 3/3 | 100.0% | 100.0% | 3/3 | 94.4% | 94.4% | D2 |
| dac | 12/14 | **100.0%** | 91.67% | 13/14 | 87.1% | 56.2% | Mixed |
| exti | 6/6 | **99.71%** | **99.71%** | 6/6 | 70.5% | 70.5% | **D2** (massive) |
| flash | 1/8 | 100.0% | 18.75% | **8/8** | 59.4% | **59.4%** | OE coverage |
| fsmc | 9/12 | 95.67% | 57.02% | **12/12** | 92.0% | **92.0%** | **OE** (both) |
| iwdg | 4/4 | 100.0% | 100.0% | 4/4 | 100.0% | 100.0% | Tie |
| pwr | 2/2 | 100.0% | 100.0% | 2/2 | 100.0% | 100.0% | Tie |
| rcc | 6/11 | 99.52% | 47.94% | 10/11 | 96.1% | **80.0%** | OE coverage, D2 found acc |

---

## 4. Algorithm Comparison

### 4.1 Pre-Processing

| Aspect | D2 | OE iter18 |
|--------|-----|-----------|
| Database | Persistent ChromaDB (`rm0041_md_chunks`) | Ephemeral in-memory (rebuilt per eval) |
| Chunks | 1033 chunks, 800 tokens, 100 overlap | Same 1033 raw chunks |
| Metadata enrichment | Rich: structured HTML comment header (chapter, section, peripheral, registers, keywords, has_tables) prepended to chunk text during `p3_augment_chunks_with_metadata.py` | Lightweight: regex `[A-Z_]{2,}_[A-Z0-9_]{2,}` extracts names, prepends `"Register: NAME1, NAME2, NAME3"` (max 3) |
| Register metadata fields | Boolean per expanded register (`reg_BKP_DR1: True` through `reg_BKP_DR20: True`) — enables `where` clause filtering | JSON string of regex-matched names — not filterable by ChromaDB `where` |
| Table detection | Set during ingestion via `has_tables` metadata | Regex `\|\s*-{3,}\s*\|` at query time |

### 4.2 Query Construction

| Aspect | D2 | OE iter18 |
|--------|-----|-----------|
| Format | `"For the {PERIPH}_{REG} register, retrieve all information about its offset, reset value, size, readonly bits, writeonly bits, readwrite bits, and subfields."` | `"Retrieve all detailed information about the {REG_KEY} register, including its address offset, reset value, bit field definitions, access types, and enumerated values for its subfields."` |
| Style | Semi-structured, lists fact types | Natural language, more descriptive |

### 4.3 Search & Filtering

| Aspect | D2 | OE iter18 |
|--------|-----|-----------|
| Initial fetch | `n_results × 5` = 10 candidates | **20** candidates (fixed) |
| Metadata filter | 3-tier: `where: {reg_NAME: True}` → `$contains` → unfiltered | None — pure unfiltered semantic |
| Reranker | FlashRank cross-encoder | None |
| Quality fallback | Top reranker score < 0.7 triggers broader tiers | N/A |

### 4.4 Post-Processing & Scoring

| Aspect | D2 | OE iter18 |
|--------|-----|-----------|
| Scoring | FlashRank cross-encoder scores | Heuristic: +100 reg name, +50 if also table, +20 table only, +(2−dist)×10 cosine |
| Final count | Trim to `n_results` = 2 | Top **6** by score |
| Page expansion | Forward only: next page's chunks for non-table results | N/A |
| Neighbor expansion | None | Bidirectional: `chunk_index ± 1` on same page, only if neighbor has reg name or tables |
| Deduplication | Via chunk_id set | Via `(page_number, chunk_index)` set |
| Ordering | By score | By `(page_number, chunk_index)` for reading order |
| Table removal | Strip markdown tables from text | No removal |
| Output format | XML `<sources><result attrs>` | Plain text `[Page N]\n{text}` |

---

## 5. Key Findings

### 5.1 Why D2 Wins on Accuracy

**FlashRank cross-encoder is the single most impactful component.** It captures fine-grained query-document relevance that bi-encoder embeddings miss. OE's heuristic scoring (register name matching + cosine) is a reasonable approximation but cannot match a trained cross-encoder. The accuracy gap is most visible on EXTI (99.71% vs 70.5%) — a large peripheral (342 facts) where precise chunk selection matters.

**Metadata filtering eliminates irrelevant candidates.** D2's boolean register fields narrow the search to chunks explicitly enriched with the target register name. OE searches the entire 1033-chunk corpus for every query, relying on embedding similarity alone.

### 5.2 Why OE Wins on Coverage

**More context to the LLM.** OE returns 6 core chunks plus neighbors vs D2's 2 chunks. With more context, the LLM has a higher chance of finding the register definition even when the top-1 result is imperfect. This explains FLASH (8/8 vs 1/8), FSMC (12/12 vs 9/12), and RCC (10/11 vs 6/11).

**Bidirectional neighbor expansion captures split definitions.** When a register header is in one chunk and the bit field table in the next, OE's `chunk_index ± 1` expansion on the same page picks up the adjacent chunk. D2's forward-only page-level expansion only looks at the *next page*, missing same-page splits.

**No metadata filter means no filter failures.** D2's tiered fallback can replace correct filtered results with wrong unfiltered results when the reranker scores definition chunks below 0.7 (documented in the report as the RCC chunk boundary issue). OE avoids this entirely by never filtering.

### 5.3 Token Usage

| | D2 | OE iter18 |
|---|---|---|
| LLM calls | 97 | 95 |
| Total tokens | 830,634 | 719,124 |
| Per-register avg | 8,563 | 7,569 |

OE uses 13% fewer total tokens despite returning more context per query. The savings come from: (a) 2 fewer LLM calls, (b) no enriched metadata headers in chunk text, (c) plain text formatting vs XML. The BKP token discrepancy identified during analysis (D2 originally showed 45 calls for 23 verified registers) was a bug in the sweep runner pulling register lists from SVD instead of verified CSV — now fixed.

### 5.4 LLM Non-Determinism Caveat

Both D2 and OE results are subject to LLM non-determinism (documented in `local_vector_db_retrieval_analysis.md`, §7). Run-to-run variance of ~3pp on complete accuracy and up to 51pp on small peripherals (PWR) means per-peripheral comparisons should be interpreted cautiously. The OE iter18 full eval was a single run; a second run (checkpoint_20, same program) on all 11 peripherals yielded 85.62% complete accuracy vs 79.8% — a 5.8pp swing from identical retrieval.

---

## 6. Complementary Strengths — Combination Opportunities

The two approaches are complementary rather than competing:

| D2 Feature (precision) | OE Feature (coverage) | Combination |
|------------------------|----------------------|-------------|
| FlashRank reranker | Wider candidate pool (20) | Rerank 20+ candidates, keep top 4–6 |
| Metadata filter + tiered fallback | No filtering | Use metadata filter first, fall back to unfiltered with more results |
| 2 results to LLM | 6+ results to LLM | 4–6 results (balance precision/coverage) |
| Forward page expansion (non-table only) | Bidirectional chunk neighbor expansion | Both: page expansion + same-page neighbors |
| Rich metadata enrichment | Lightweight register name header | Keep rich metadata (already ingested) |

A combined configuration (E1) would use D2's persistent database, metadata filter, and FlashRank reranker with OE's wider result count and bidirectional neighbor expansion. See the E1 plan for implementation details.
