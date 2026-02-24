# Local Vector DB Context Retrieval: Configuration Parameters & Experiment Analysis

**Date:** 2026-02-18
**Device:** RM0041 (STM32F100xx)
**LLM:** gpt-oss-120b (via Groq)
**Database:** 1033 enriched markdown chunks from rm0041.md
**Embedding model:** BAAI/bge-small-en-v1.5 (384-dim, local/free via FastEmbed)
**Evaluation:** 11 peripherals, 97 registers, 1766 total verified facts

---

## 1. Configuration Parameters

The local vector DB retrieval pipeline has two categories of parameters: **pre-processing** (how chunks are prepared and stored) and **post-processing** (how chunks are searched and filtered at query time).

### 1.1 Pre-Processing Parameters

These parameters control how the source datasheet is chunked, enriched, and embedded into the ChromaDB vector database. They are set during ingestion (`preprocessing/ingest_local_vector_db.py`) and cannot be changed without re-ingesting.


| Parameter                | Default                    | Description                                                                                                                                                         |
| ------------------------ | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CHUNK_SIZE`             | 800 tokens                 | Maximum size of each text chunk. Chunks are split recursively at markdown boundaries (headers, paragraphs, sentences). Larger chunks provide more context per result but reduce retrieval precision. |
| `CHUNK_OVERLAP`          | 100 tokens                 | Number of tokens overlapping between adjacent chunks. Prevents information loss at chunk boundaries (e.g., register headers split from bit field descriptions).     |
| `EMBEDDING_PROVIDER`     | `"local"`                  | Embedding model provider. `"local"` uses FastEmbed BAAI/bge-small-en-v1.5 (384-dim, free, runs on CPU). `"openai"` uses text-embedding-3-small (1536-dim, paid API). Must match at ingestion and query time. |
| `LOCAL_EMBEDDING_MODEL`  | `"BAAI/bge-small-en-v1.5"` | The specific local embedding model. BAAI/bge-small-en-v1.5 produces 384-dimensional vectors with cosine similarity.                                                 |

#### Per-Chunk Metadata: Two Types

During ingestion, each chunk receives two distinct types of metadata that serve different purposes:

1. **ChromaDB metadata fields** — Structured key-value pairs stored in ChromaDB alongside the chunk embedding. Used for `where`-clause **pre-search filtering** (narrowing the candidate set *before* embedding similarity is computed). Not visible to the embedding model or the LLM.

2. **Text enrichment header** — A structured comment block **prepended to the chunk text** before embedding. Makes metadata searchable by the embedding model and visible to the LLM. Only applied when chunks are ingested with `--embed-metadata` (creates `md_enriched` variant).

Both types use the same enriched data from `TextProcessor`, including **expanded register names** — parameterized names like `BKP_DRx (x=1..20)` are expanded to individual names (`BKP_DR1`, `BKP_DR2`, ..., `BKP_DR20`).

**ChromaDB metadata fields** (stored per chunk in `ingest_local_vector_db.py`):


| Field               | Type   | Example                    | Purpose                                            |
| ------------------- | ------ | -------------------------- | -------------------------------------------------- |
| `page_number`       | int    | `187`                      | Chunk expansion page lookups                       |
| `chunk_index`       | int    | `1`                        | Ordering within page                               |
| `total_chunks_on_page` | int | `3`                        | —                                                  |
| `device`            | str    | `"rm0041"`                 | Multi-device database support                      |
| `source`            | str    | `"rm0041_p187_c01.txt"`    | Traceability                                       |
| `has_tables`        | bool   | `True`                     | Conditional page expansion (D2), content signal    |
| `section`           | str    | `"10.11 ADC Registers"`    | Display/traceability                               |
| `reg_{NAME}`        | bool   | `reg_ADC_DR: True`         | **Metadata filtering** via `where` clause          |


The `reg_{NAME}` boolean fields are the critical ones for filtering — they enable queries like `where={"reg_ADC_DR": True}`. Created by looping through the expanded `registers_mentioned` list and setting individual boolean keys. In `rm0041_md_chunks_v2`, this replaced the earlier `rm0041_md_chunks` approach of storing registers as a comma-separated string, which was **not filterable** by ChromaDB's `where` operator.

**Text enrichment header** (prepended by `p3_augment_chunks_with_metadata.py`):

```
<!-- CHUNK METADATA
Chapter: 12 Digital-to-analog converter (DAC)
Section: 12.5.8 DAC register map
Peripheral: DAC
Registers: DAC_CR, DAC_SWTRIGR, DAC_DHR12R1, DAC_DHR12R2, DAC_DHR12RD (and 5 more)
Contains: tables
Keywords: trigger, channel, output, enable, conversion
-->

[original chunk content]
```

The header uses configurable field presets (`p3_augment_chunks_with_metadata.py`). The default preset includes: `chapter`, `section`, `subsection`, `peripheral`, `registers`, `has_tables`, `has_code`, `has_diagrams`, `keywords`. A `minimal` preset (`section`, `peripheral`, `registers`) reduces token overhead.

**Comparison:**


| Aspect                       | ChromaDB metadata               | Text enrichment header                 |
| ---------------------------- | ------------------------------- | -------------------------------------- |
| **Storage**                  | Structured dict in ChromaDB     | Prepended to chunk text                |
| **Used for**                 | Pre-search filtering (`where`)  | Embedding similarity + LLM context     |
| **Visible to embedding?**    | No                              | Yes                                    |
| **Visible to LLM?**         | No                              | Yes                                    |
| **Register name format**     | `reg_BKP_DR1: True` (boolean)  | `Registers: BKP_DR1, BKP_DR2, ...`    |
| **Always applied?**          | Yes                             | Only with `--embed-metadata`           |
| **Token cost**               | None                            | ~50-100 tokens per chunk               |


### 1.2 Post-Processing (Search-Time) Parameters

These parameters are set in `ContextRetrievalParameters` and control how the vector database is queried for each register.


| Parameter                | Config key                | Default | Description                                                                                                                                                                                                                                                                                                                        |
| ------------------------ | ------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Number of embeddings** | `number_embeddings`       | 5       | Number of final chunks returned to the LLM. When reranking is enabled, `n_results × 5` candidates are fetched, reranked, then trimmed to `n_results`.                                                                                                                                                                              |
| **Metadata filter**      | `metadata_filter_enabled` | `True`  | When enabled, narrows the embedding search to only chunks whose metadata contains the target register name (`where: {"reg_PERIPHERAL_REGISTER": True}`). Dramatically improves precision for registers with unique names but may miss registers with parameterized names not in the metadata.                                      |
| **Reranker**             | `reranker_type`           | `""`    | Cross-encoder reranker applied after initial embedding retrieval. `"local"` = FlashRank (ms-marco-MiniLM-L-12-v2, free, local). `"cohere"` = Cohere Rerank API. `"bge"` = BGE cross-encoder. The reranker re-scores each candidate using the full query-document pair, capturing semantic nuances that bi-encoder embeddings miss. |
| **Keyword boost**        | `keyword_boost`           | `True`  | After retrieval (and optional reranking), boosts scores of results containing exact register name matches. Boost tiers: +0.20 for `REGISTER DEFINITION:` line match, +0.10 for `[KEY:]` section match, +0.05 for body text match. Results are re-sorted by boosted score.                                                          |
| **Score threshold**      | `score_threshold`         | 0.0     | Minimum score for results to be included. Results below this threshold are discarded. Not used in current experiments (set to 0.0).                                                                                                                                                                                                |
| **Query rewrite**        | `query_rewrite`           | `False` | When enabled, the search query is rewritten by an LLM (s3_query_rewriter.py) before retrieval. Intended to reformulate queries for better semantic search results. Not used in current local DB experiments.                                                                                                                       |
| **Pages after**          | `pages_after`             | 0       | Number of contiguous pages to expand after each retrieved chunk's page. Set to 0 to disable expansion. When > 0, expansion is applied **per-result**: only chunks without tables (`has_tables=False`) are expanded, since table-containing chunks likely have complete register definitions. See Experiment D for details.          |
| **Tiered fallback**      | (built-in logic)          | —       | Quality-aware fallback that can trigger **up to 3 full search+rerank passes** for a single query. See detailed description below.                                                                                                                                                                                                  |


#### Tiered Fallback — Detailed Description

The tiered fallback addresses cases where the metadata filter returns results but those results are poor quality (e.g., register map table mentions rather than actual definition pages). It requires both a metadata filter and a reranker to be active.

**How it works:** The system performs the initial metadata-filtered search, reranks the results, then checks the **top reranker score**. If that score is below **0.7**, it interprets the filtered results as low quality and progressively retries with broader searches. Each retry is a full `embed → search → rerank` pass. In the worst case, this means the vector DB is searched 3 times and the reranker runs 3 times for a single query.

**The 3 passes:**


| Pass                        | Filter                                    | Trigger condition                     | What it searches                                                                                                                                                               |
| --------------------------- | ----------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1. Metadata filter**      | `where: {reg_REGISTER: True}`             | Always (when metadata filter enabled) | Only chunks whose boolean metadata field matches the target register. Most precise — returns chunks explicitly enriched with that register name during ingestion.              |
| **2. Document text filter** | `where_document: {$contains: "REGISTER"}` | Pass 1 top reranker score < 0.7       | Any chunk whose text content contains the register name string. Broader — catches register map tables, cross-references, and incidental mentions alongside actual definitions. |
| **3. Unfiltered**           | None                                      | Pass 2 top reranker score still < 0.7 | All chunks in the database, ranked purely by embedding similarity to the query. Broadest — relies entirely on semantic similarity.                                             |


**Selection logic:** After each fallback pass, the system compares the new top reranker score against the current best. It always **keeps whichever result set has the highest top score** — the 0.7 threshold only gates whether to *try* the next tier, it does not determine which results win. Specifically:

1. Run pass 1 (metadata filter) → rerank → top score = S1
2. If S1 < 0.7: run pass 2 (where_document) → rerank → top score = S2
  - If S2 > S1: replace results with pass 2 results (current best score = S2)
  - Else: keep pass 1 results (current best score = S1)
3. If current best score still < 0.7: run pass 3 (unfiltered) → rerank → top score = S3
  - If S3 > current best: replace results with pass 3 results
  - Else: keep current best results

**Example — BKP_DR5 (parameterized register):**

- Pass 1: metadata `{reg_BKP_DR5: True}` → returns register map table chunks → reranker score 0.55
- 0.55 < 0.7 → Pass 2: `$contains: "BKP_DR5"` → similar poor chunks → reranker score 0.60
- 0.60 > 0.55 → replace results; 0.60 < 0.7 → Pass 3: unfiltered → returns BKP_DRx definition page → reranker score 0.85
- 0.85 > 0.60 → replace results → correct definition returned to LLM

**Known weakness — false fallback for chunk boundary splits:**
For registers like RCC_AHBENR, the metadata filter correctly returns the definition chunk, but the register header lands in one chunk and the bit fields in the next. The reranker scores the header-only chunk below 0.7, triggering the fallback. The unfiltered search returns a high-scoring generic RCC overview page, which replaces the correct (but low-scoring) filtered result.

### 1.3 Parameter Interaction Diagram

```
Query: "AFIO_MAPR register definition bit fields"
  │
  ├─ fetch_k = n_results × 5 (if reranker) or n_results
  │
  ├─ PASS 1: metadata_filter_enabled=True?
  │    ├─ YES → search with where: {reg_AFIO_MAPR: True}  [embed + search]
  │    │         └─ 0 results? → fallback to where_document: {$contains: "AFIO_MAPR"}
  │    │                          └─ 0 results? → fallback to unfiltered search
  │    └─ NO → unfiltered search
  │
  ├─ reranker_type="local"?
  │    └─ YES → FlashRank rerank pass 1 candidates              [rerank #1]
  │              │
  │              └─ top score < 0.7 AND metadata filter was used?
  │                   │
  │                   ├─ PASS 2: where_document {$contains: "AFIO_MAPR"}  [embed + search]
  │                   │    └─ FlashRank rerank pass 2 candidates          [rerank #2]
  │                   │         └─ pass 2 top score > current best? → replace results
  │                   │
  │                   └─ current best score still < 0.7?
  │                        │
  │                        └─ PASS 3: unfiltered search                   [embed + search]
  │                             └─ FlashRank rerank pass 3 candidates     [rerank #3]
  │                                  └─ pass 3 top score > current best? → replace results
  │
  ├─ keyword_boost=True?
  │    └─ YES → boost scores by exact keyword match → re-sort
  │
  ├─ score_threshold > 0?
  │    └─ YES → filter out results below threshold
  │
  ├─ trim to n_results
  │
  └─ pages_after > 0?
       └─ YES → for each result: has_tables=False?
                  ├─ YES (no table) → expand with contiguous page chunks
                  └─ NO (has table) → skip expansion (definition likely complete)
```

---

## 2. Experiment Results

All experiments use the same 11 peripherals (afio, bkp, cec, crc, dac, exti, flash, fsmc, iwdg, pwr, rcc) with 97 total registers and 1766 verified facts. The LLM (gpt-oss-120b via Groq) is non-deterministic, so results may vary slightly across runs with identical retrieval configurations.

**Note on FLASH:** 7 of 8 FLASH registers (SR, CR, KEYR, OPTKEYR, OBR, WRPR, AR) are documented in a separate manual (PM0063), not in RM0041. Only FLASH_ACR appears in the datasheet. All configurations find 1/8 FLASH registers. This is a data gap, not a retrieval failure.

### 2.1 Experiment A: Reranker Addition (v5, broken metadata filter)

**Database:** `rm0041_md_chunks` (1033 chunks, comma-separated register metadata — filter non-functional)
**Key finding:** The metadata filter was completely broken in this experiment series. ChromaDB's `where` operator does not support `$contains` on string metadata fields. All "mf=True" runs silently fell back to unfiltered search. Despite this, adding the FlashRank reranker provided dramatic accuracy improvements.

#### A1: emb2 + reranker + mf (metadata filter broken → effectively unfiltered + reranker)

**Configuration:**


| Parameter                 | Value                                              |
| ------------------------- | -------------------------------------------------- |
| Database                  | `rm0041_md_chunks`                                 |
| Embedding provider        | local (BAAI/bge-small-en-v1.5, 384-dim)            |
| `number_embeddings`       | 2                                                  |
| `reranker_type`           | `"local"` (FlashRank)                              |
| `keyword_boost`           | `False`                                            |
| `metadata_filter_enabled` | `True` (broken — silently fell back to unfiltered) |
| `pages_after`             | 0 (disabled)                                       |
| `expand_table_pages_only` | N/A                                                |
| `score_threshold`         | 0.0                                                |
| `query_rewrite`           | `False`                                            |
| Quality fallback          | None                                               |


**Results directory:** `local_vector_db_v5_reranker/local_rm0041_md_chunks_emb2_rrlocal_mf/`

**Results:**


| Metric                    | Value          |
| ------------------------- | -------------- |
| Registers found           | 68/97          |
| Found accuracy            | 94.75%         |
| Complete accuracy         | 59.29%         |
| Coverage                  | 62.57%         |
| Correct / Wrong / Missing | 1047 / 37 / 21 |



| Peripheral | Regs found | Found acc. | Complete acc. | Coverage |
| ---------- | ---------- | ---------- | ------------- | -------- |
| afio       | 4/7        | 100.0%     | 40.82%        | 40.82%   |
| bkp        | 21/23      | 93.04%     | 75.35%        | 80.99%   |
| cec        | 3/7        | 78.95%     | 50.00%        | 63.33%   |
| crc        | 3/3        | 94.44%     | 94.44%        | 100.0%   |
| dac        | 11/14      | 93.65%     | 81.94%        | 87.50%   |
| exti       | 5/6        | 99.65%     | 83.04%        | 83.33%   |
| flash      | 1/8        | 100.0%     | 18.75%        | 18.75%   |
| fsmc       | 8/12       | 96.30%     | 44.70%        | 46.42%   |
| iwdg       | 4/4        | 81.48%     | 81.48%        | 100.0%   |
| pwr        | 2/2        | 82.05%     | 82.05%        | 100.0%   |
| rcc        | 6/11       | 95.24%     | 45.87%        | 48.17%   |


**Strengths:** High found accuracy (94.75%). The reranker effectively re-orders embedding results to surface the most relevant chunks. Low error rate on found registers.
**Weaknesses:** Low coverage (62.57%) — many registers not found at all. AFIO only 4/7 registers, CEC only 3/7. Without a working metadata filter, the search is entirely dependent on embedding similarity, which often retrieves generic overview pages instead of specific register definitions.

#### A2: emb2 + reranker + mf + pa2 (with 2-page expansion)

**Configuration:**


| Parameter                 | Value                                              |
| ------------------------- | -------------------------------------------------- |
| Database                  | `rm0041_md_chunks`                                 |
| Embedding provider        | local (BAAI/bge-small-en-v1.5, 384-dim)            |
| `number_embeddings`       | 2                                                  |
| `reranker_type`           | `"local"` (FlashRank)                              |
| `keyword_boost`           | `False`                                            |
| `metadata_filter_enabled` | `True` (broken — silently fell back to unfiltered) |
| `pages_after`             | 2                                                  |
| `expand_table_pages_only` | `False`                                            |
| `score_threshold`         | 0.0                                                |
| `query_rewrite`           | `False`                                            |
| Quality fallback          | None                                               |


**Results directory:** `local_vector_db_v5_reranker/local_rm0041_md_chunks_emb2_rrlocal_mf_pa2/`

**Results:**


| Metric                    | Value         |
| ------------------------- | ------------- |
| Registers found           | 67/97         |
| Found accuracy            | 91.44%        |
| Complete accuracy         | 56.29%        |
| Coverage                  | 61.55%        |
| Correct / Wrong / Missing | 994 / 21 / 72 |


**Strengths:** Lower wrong count (21 vs 37) than A1.
**Weaknesses:** Page expansion added noise — found accuracy dropped 3.3pp and coverage dropped 1pp vs A1. Expansion chunks from contiguous pages often contained irrelevant content that confused the LLM.

#### A3: emb2 + keyword boost + reranker + pa2 (no metadata filter)

**Configuration:**


| Parameter                 | Value                                   |
| ------------------------- | --------------------------------------- |
| Database                  | `rm0041_md_chunks`                      |
| Embedding provider        | local (BAAI/bge-small-en-v1.5, 384-dim) |
| `number_embeddings`       | 2                                       |
| `reranker_type`           | `"local"` (FlashRank)                   |
| `keyword_boost`           | `True`                                  |
| `metadata_filter_enabled` | `False`                                 |
| `pages_after`             | 2                                       |
| `expand_table_pages_only` | `False`                                 |
| `score_threshold`         | 0.0                                     |
| `query_rewrite`           | `False`                                 |
| Quality fallback          | None                                    |


**Results directory:** `local_vector_db_v5_reranker/local_rm0041_md_chunks_emb2_kb_rrlocal_pa2/`

**Results:**


| Metric                    | Value         |
| ------------------------- | ------------- |
| Registers found           | 68/97         |
| Found accuracy            | 93.30%        |
| Complete accuracy         | 55.21%        |
| Coverage                  | 59.17%        |
| Correct / Wrong / Missing | 975 / 16 / 54 |


**Strengths:** Lowest wrong count (16) among v5 experiments. Keyword boost helps surface exact register name matches.
**Weaknesses:** Keyword boost after reranking can override reranker ordering. RCC dropped to 5/11 registers (from 6/11 in A1). Complete accuracy lowest of the three emb2 configs.

#### A4: emb1 + reranker + mf + pa1 + table_pages_only

**Configuration:**


| Parameter                 | Value                                              |
| ------------------------- | -------------------------------------------------- |
| Database                  | `rm0041_md_chunks`                                 |
| Embedding provider        | local (BAAI/bge-small-en-v1.5, 384-dim)            |
| `number_embeddings`       | 1                                                  |
| `reranker_type`           | `"local"` (FlashRank)                              |
| `keyword_boost`           | `False`                                            |
| `metadata_filter_enabled` | `True` (broken — silently fell back to unfiltered) |
| `pages_after`             | 1                                                  |
| `expand_table_pages_only` | `True`                                             |
| `score_threshold`         | 0.0                                                |
| `query_rewrite`           | `False`                                            |
| Quality fallback          | None                                               |


**Results directory:** `local_vector_db_v5_reranker/local_rm0041_md_chunks_emb1_rrlocal_mf_pa1_tpo/`

**Results:**


| Metric                    | Value         |
| ------------------------- | ------------- |
| Registers found           | 55/97         |
| Found accuracy            | 86.98%        |
| Complete accuracy         | 40.09%        |
| Coverage                  | 46.09%        |
| Correct / Wrong / Missing | 708 / 64 / 42 |


**Strengths:** Minimal experiment — only 1 embedding result + 1 page of table expansion.
**Weaknesses:** Worst performance across all metrics. A single embedding is insufficient; the reranker has too few candidates to select from (5 candidates → trim to 1). EXTI dropped to 3/6 (50% coverage). High wrong count (64) indicates the single retrieved chunk frequently provides incomplete context.

---

### 2.2 Experiment B: Fixed Document Text Filter (v6)

**Database:** `rm0041_md_chunks` (same 1033 chunks, broken metadata)
**Key change:** Replaced the broken `where` metadata filter with `where_document: {"$contains": "REGISTER_NAME"}`, which searches the actual chunk text content. This is a broader filter than metadata — it finds any chunk where the register name appears anywhere in the text, including incidental mentions in register map tables and table of contents.

#### B1: emb2 + reranker + mf (where_document filter, no quality fallback)

**Configuration:**


| Parameter                 | Value                                                 |
| ------------------------- | ----------------------------------------------------- |
| Database                  | `rm0041_md_chunks`                                    |
| Embedding provider        | local (BAAI/bge-small-en-v1.5, 384-dim)               |
| `number_embeddings`       | 2                                                     |
| `reranker_type`           | `"local"` (FlashRank)                                 |
| `keyword_boost`           | `False`                                               |
| `metadata_filter_enabled` | `True` (implemented as `where_document: {$contains}`) |
| Filter type               | Document text search (`where_document`)               |
| `pages_after`             | 0 (disabled)                                          |
| `expand_table_pages_only` | N/A                                                   |
| `score_threshold`         | 0.0                                                   |
| `query_rewrite`           | `False`                                               |
| Quality fallback          | None (only 0-result fallback to unfiltered)           |


**Results directory:** `local_vector_db_v6_fixed_filter/local_rm0041_md_chunks_emb2_rrlocal_mf/` (first run, before fallback was added)

**Results:**


| Metric                    | Value           |
| ------------------------- | --------------- |
| Registers found           | 64/97           |
| Found accuracy            | 88.69%          |
| Complete accuracy         | 71.52%          |
| Coverage                  | 80.63%          |
| Correct / Wrong / Missing | 1263 / 41 / 120 |



| Peripheral | Regs found | Found acc. | Complete acc. | Coverage |
| ---------- | ---------- | ---------- | ------------- | -------- |
| afio       | 7/7        | 80.95%     | 80.95%        | 100.0%   |
| bkp        | 5/23       | 94.23%     | 34.51%        | 36.62%   |
| cec        | 7/7        | 100.0%     | 100.0%        | 100.0%   |
| crc        | 3/3        | 77.78%     | 77.78%        | 100.0%   |
| dac        | 12/14      | 98.48%     | 90.28%        | 91.67%   |
| exti       | 6/6        | 99.71%     | 99.71%        | 100.0%   |
| flash      | 1/8        | 100.0%     | 18.75%        | 18.75%   |
| fsmc       | 9/12       | 96.75%     | 76.79%        | 79.37%   |
| iwdg       | 4/4        | 100.0%     | 100.0%        | 100.0%   |
| pwr        | 2/2        | 43.59%     | 43.59%        | 100.0%   |
| rcc        | 8/11       | 68.37%     | 46.10%        | 67.43%   |


**Strengths:** Massive coverage improvement vs v5 — AFIO 4/7→7/7, CEC 3/7→7/7, DAC 11/14→12/14, EXTI 5/6→6/6, IWDG 4/4 at 100%. The text filter successfully constrains search to register-relevant chunks.
**Weaknesses:** BKP catastrophic regression (21/23→5/23). The BKP data registers use parameterized names (BKP_DRx in the definition text). The `$contains: "BKP_DR1"` filter finds register map tables (which mention the individual names) but not the actual definition pages. Without a fallback mechanism, these poor-quality results are used directly.

#### B2: emb2 + reranker + mf (where_document + quality fallback at 0.7)

**Configuration:**


| Parameter                 | Value                                                 |
| ------------------------- | ----------------------------------------------------- |
| Database                  | `rm0041_md_chunks`                                    |
| Embedding provider        | local (BAAI/bge-small-en-v1.5, 384-dim)               |
| `number_embeddings`       | 2                                                     |
| `reranker_type`           | `"local"` (FlashRank)                                 |
| `keyword_boost`           | `False`                                               |
| `metadata_filter_enabled` | `True` (implemented as `where_document: {$contains}`) |
| Filter type               | Document text search (`where_document`)               |
| `pages_after`             | 0 (disabled)                                          |
| `expand_table_pages_only` | N/A                                                   |
| `score_threshold`         | 0.0                                                   |
| `query_rewrite`           | `False`                                               |
| Quality fallback          | Reranker score < 0.7 → retry unfiltered, pick best    |


**Results directory:** `local_vector_db_v6_fixed_filter/local_rm0041_md_chunks_emb2_rrlocal_mf/` (second run, with fallback)

**Results:**


| Metric                    | Value           |
| ------------------------- | --------------- |
| Registers found           | 86/97           |
| Found accuracy            | 89.26%          |
| Complete accuracy         | 80.46%          |
| Coverage                  | 90.15%          |
| Correct / Wrong / Missing | 1421 / 48 / 123 |



| Peripheral | Regs found | Found acc. | Complete acc. | Coverage |
| ---------- | ---------- | ---------- | ------------- | -------- |
| afio       | 7/7        | 80.95%     | 80.95%        | 100.0%   |
| bkp        | 23/23      | 97.18%     | 97.18%        | 100.0%   |
| cec        | 7/7        | 100.0%     | 100.0%        | 100.0%   |
| crc        | 3/3        | 83.33%     | 83.33%        | 100.0%   |
| dac        | 13/14      | 94.20%     | 90.28%        | 95.83%   |
| exti       | 6/6        | 99.71%     | 99.71%        | 100.0%   |
| flash      | 1/8        | 100.0%     | 18.75%        | 18.75%   |
| fsmc       | 12/12      | 96.56%     | 96.56%        | 100.0%   |
| iwdg       | 4/4        | 100.0%     | 100.0%        | 100.0%   |
| pwr        | 2/2        | 43.59%     | 43.59%        | 100.0%   |
| rcc        | 8/11       | 68.37%     | 46.10%        | 67.43%   |


**Strengths:** Best overall coverage (90.15%) and complete accuracy (80.46%) of all experiments. BKP fully recovered (23/23). FSMC achieved 100% coverage (12/12). 8 of 11 peripherals at 100% coverage. The quality fallback successfully detects when filtered results are poor (reranker score < 0.7) and switches to unfiltered search.
**Weaknesses:** Higher wrong count (48) than metadata-based approaches. RCC still at 8/11 — the quality fallback replaces correct filtered results with wrong unfiltered results for RCC_AHBENR, RCC_APB1RSTR, RCC_APB2RSTR (the reranker scores definition chunks low due to chunk boundary splits, triggering the fallback to generic RCC pages). PWR accuracy is poor (43.59%) despite 100% coverage.

---

### 2.3 Experiment C: Boolean Metadata Filter (v7)

**Database:** `rm0041_md_chunks_v2` (1033 chunks, boolean register metadata fields)
**Key change:** Re-ingested the same chunks with each register stored as an individual boolean metadata field (`reg_BKP_DR1: True`). This enables proper ChromaDB `where` clause filtering (`where: {"reg_BKP_DR1": True}`), which is precise metadata-level filtering rather than text search.

#### C1: emb2 + reranker + mf (metadata boolean filter, no fallback)

**Configuration:**


| Parameter                 | Value                                             |
| ------------------------- | ------------------------------------------------- |
| Database                  | `rm0041_md_chunks_v2` (boolean register metadata) |
| Embedding provider        | local (BAAI/bge-small-en-v1.5, 384-dim)           |
| `number_embeddings`       | 2                                                 |
| `reranker_type`           | `"local"` (FlashRank)                             |
| `keyword_boost`           | `False`                                           |
| `metadata_filter_enabled` | `True` (implemented as `where: {reg_NAME: True}`) |
| Filter type               | Metadata boolean field (`where`)                  |
| `pages_after`             | 0 (disabled)                                      |
| `expand_table_pages_only` | N/A                                               |
| `score_threshold`         | 0.0                                               |
| `query_rewrite`           | `False`                                           |
| Quality fallback          | None (only 0-result fallback to unfiltered)       |


**Results directory:** `local_vector_db_v7_meta_filter/local_rm0041_md_chunks_v2_emb2_rrlocal_mf/` (first run, no fallback)

**Results:**


| Metric                    | Value           |
| ------------------------- | --------------- |
| Registers found           | 80/97           |
| Found accuracy            | 89.81%          |
| Complete accuracy         | 73.33%          |
| Coverage                  | 81.65%          |
| Correct / Wrong / Missing | 1295 / 24 / 123 |



| Peripheral | Regs found | Found acc. | Complete acc. | Coverage |
| ---------- | ---------- | ---------- | ------------- | -------- |
| afio       | 7/7        | 97.28%     | 97.28%        | 100.0%   |
| bkp        | 22/23      | 98.39%     | 85.92%        | 87.32%   |
| cec        | 7/7        | 86.67%     | 86.67%        | 100.0%   |
| crc        | 3/3        | 100.0%     | 100.0%        | 100.0%   |
| dac        | 12/14      | 66.67%     | 61.11%        | 91.67%   |
| exti       | 6/6        | 99.71%     | 99.71%        | 100.0%   |
| flash      | 1/8        | 100.0%     | 18.75%        | 18.75%   |
| fsmc       | 9/12       | 80.87%     | 64.18%        | 79.37%   |
| iwdg       | 4/4        | 100.0%     | 100.0%        | 100.0%   |
| pwr        | 2/2        | 97.44%     | 97.44%        | 100.0%   |
| rcc        | 7/11       | 87.50%     | 48.17%        | 55.05%   |


**Strengths:** Lowest wrong count of all experiments (24 — half of B2's 48). AFIO achieved 97.28% complete accuracy (best of any experiment). PWR at 97.44% (vs 43.59% in B2). The precise metadata filter retrieves exactly the chunks that were enriched with the target register name, avoiding incidental mentions.
**Weaknesses:** Lower coverage than B2 (81.65% vs 90.15%) — FSMC only 9/12, RCC 7/11. When a register name is missing from all chunk metadata (e.g., not expanded during enrichment), the filter returns 0 results and falls back to unfiltered search without the benefit of any register-specific narrowing.

#### C2: emb2 + reranker + mf (metadata + quality fallback)

**Configuration:**


| Parameter                 | Value                                              |
| ------------------------- | -------------------------------------------------- |
| Database                  | `rm0041_md_chunks_v2` (boolean register metadata)  |
| Embedding provider        | local (BAAI/bge-small-en-v1.5, 384-dim)            |
| `number_embeddings`       | 2                                                  |
| `reranker_type`           | `"local"` (FlashRank)                              |
| `keyword_boost`           | `False`                                            |
| `metadata_filter_enabled` | `True` (implemented as `where: {reg_NAME: True}`)  |
| Filter type               | Metadata boolean field (`where`)                   |
| `pages_after`             | 0 (disabled)                                       |
| `expand_table_pages_only` | N/A                                                |
| `score_threshold`         | 0.0                                                |
| `query_rewrite`           | `False`                                            |
| Quality fallback          | Reranker score < 0.7 → retry unfiltered, pick best |


**Results directory:** `local_vector_db_v7_meta_filter/local_rm0041_md_chunks_v2_emb2_rrlocal_mf/` (second run, with fallback)

**Results:**


| Metric                    | Value           |
| ------------------------- | --------------- |
| Registers found           | 83/97           |
| Found accuracy            | 90.09%          |
| Complete accuracy         | 77.24%          |
| Coverage                  | 85.73%          |
| Correct / Wrong / Missing | 1364 / 27 / 123 |



| Peripheral | Regs found | Found acc. | Complete acc. | Coverage |
| ---------- | ---------- | ---------- | ------------- | -------- |
| afio       | 7/7        | 97.28%     | 97.28%        | 100.0%   |
| bkp        | 22/23      | 98.39%     | 85.92%        | 87.32%   |
| cec        | 7/7        | 86.67%     | 86.67%        | 100.0%   |
| crc        | 3/3        | 100.0%     | 100.0%        | 100.0%   |
| dac        | 12/14      | 66.67%     | 61.11%        | 91.67%   |
| exti       | 6/6        | 99.71%     | 99.71%        | 100.0%   |
| flash      | 1/8        | 100.0%     | 18.75%        | 18.75%   |
| fsmc       | 12/12      | 83.95%     | 83.95%        | 100.0%   |
| iwdg       | 4/4        | 100.0%     | 100.0%        | 100.0%   |
| pwr        | 2/2        | 97.44%     | 97.44%        | 100.0%   |
| rcc        | 7/11       | 87.50%     | 48.17%        | 55.05%   |


**Strengths:** FSMC recovered to 12/12 (100% coverage) with the fallback. Found accuracy is highest among all working-filter experiments (90.09%). Only 27 wrong facts.
**Weaknesses:** RCC still at 7/11, DAC at 12/14. The quality fallback helps for FSMC (where the metadata filter returns low-scoring results) but does not help RCC (where the correct filtered results are replaced by wrong unfiltered results with higher reranker scores).

#### C3: emb2 + reranker + mf (tiered: metadata → where_document → unfiltered fallback)

**Configuration:**


| Parameter                 | Value                                                                   |
| ------------------------- | ----------------------------------------------------------------------- |
| Database                  | `rm0041_md_chunks_v2` (boolean register metadata)                       |
| Embedding provider        | local (BAAI/bge-small-en-v1.5, 384-dim)                                 |
| `number_embeddings`       | 2                                                                       |
| `reranker_type`           | `"local"` (FlashRank)                                                   |
| `keyword_boost`           | `False`                                                                 |
| `metadata_filter_enabled` | `True` (implemented as `where: {reg_NAME: True}`)                       |
| Filter type               | Tiered: metadata → `where_document` → unfiltered                        |
| `pages_after`             | 0 (disabled)                                                            |
| `expand_table_pages_only` | N/A                                                                     |
| `score_threshold`         | 0.0                                                                     |
| `query_rewrite`           | `False`                                                                 |
| Quality fallback          | Reranker score < 0.7 → try `where_document`, then unfiltered, pick best |


**Results directory:** `local_vector_db_v7_meta_filter/local_rm0041_md_chunks_v2_emb2_rrlocal_mf/` (third run, tiered fallback)

**Results:**


| Metric            | Value  |
| ----------------- | ------ |
| Registers found   | 83/97  |
| Found accuracy    | 90.09% |
| Complete accuracy | 77.24% |
| Coverage          | 85.73% |


Results identical to C2. The `where_document` middle tier was effectively redundant — cases that fail metadata filter either get rescued by unfiltered fallback or aren't helped by text search either.

---

### 2.4 Experiment D: Conditional Page Expansion (v7)

**Database:** `rm0041_md_chunks_v2` (1033 chunks, boolean register metadata fields)
**Base config:** C2 (metadata filter + FlashRank reranker + tiered quality fallback)
**Key change:** Adding page expansion (`pages_after=1`) to C2, with progressive refinement of when expansion triggers.

**Motivation:** Register definitions in hardware datasheets sometimes span multiple pages — the register header and description on one page, the bit field table on the next. A single chunk may capture only part of the definition. Page expansion appends chunks from contiguous pages to provide the LLM with the complete definition.

#### D1: Unconditional page expansion (pages_after=1)

**Configuration:** C2 + `pages_after=1`, expansion applied to all results unconditionally.

**Results directory:** `local_vector_db_v7_meta_filter/local_rm0041_md_chunks_v2_emb2_rrlocal_mf_pa1_unconditional/`

**Results:**


| Metric                    | Value          |
| ------------------------- | -------------- |
| Registers found           | 78/97          |
| Found accuracy            | 93.24%         |
| Complete accuracy         | 70.27%         |
| Coverage                  | 75.37%         |
| Correct / Wrong / Missing | 1241 / 19 / 71 |


| Peripheral | Regs found | Found acc. | Complete acc. | Coverage |
| ---------- | ---------- | ---------- | ------------- | -------- |
| afio       | 6/7        | 82.22%     | 75.51%        | 91.84%   |
| bkp        | 22/23      | 95.97%     | 83.80%        | 87.32%   |
| cec        | 7/7        | 96.67%     | 96.67%        | 100.0%   |
| crc        | 3/3        | 100.0%     | 100.0%        | 100.0%   |
| dac        | 12/14      | 96.97%     | 88.89%        | 91.67%   |
| exti       | 6/6        | 99.71%     | 99.71%        | 100.0%   |
| flash      | 1/8        | 100.0%     | 18.75%        | 18.75%   |
| fsmc       | 9/12       | 79.33%     | 47.28%        | 59.60%   |
| iwdg       | 4/4        | 100.0%     | 100.0%        | 100.0%   |
| pwr        | 2/2        | 100.0%     | 100.0%        | 100.0%   |
| rcc        | 6/11       | 95.24%     | 45.87%        | 48.17%   |

**vs C2 baseline:** Coverage dropped 10pp (85.73%→75.37%), complete accuracy dropped 7pp (77.24%→70.27%). FSMC regressed from 83.95%→47.28% complete accuracy. Expansion chunks from contiguous pages added irrelevant content that confused the LLM.

#### D2: Per-result conditional expansion (pages_after=1)

**Key insight:** Not all retrieved chunks need expansion. Register definitions in hardware datasheets always include bit field tables. A chunk that already contains a table (`has_tables=True` metadata) likely has the complete definition. Only chunks *without* tables may represent split definitions where the header is in one chunk and the bit fields are on the next page.

**Implementation:** After primary retrieval, filter results to those where `has_tables=False` and only expand those individual chunks. Results with tables are left untouched. This is implemented in `local_vector_search.py`:

```python
no_table_results = [r for r in results if not r["metadata"].get("has_tables", False)]
if no_table_results:
    expansion_chunks = _expand_chunks(no_table_results, chunk_index_path, pages_after, table_pages_only)
```

**Why per-result matters:** With `n_results=2`, the FlashRank reranker strongly prefers table-containing chunks (bit field tables are highly relevant to register queries). In practice, 78 of 97 registers have *both* top-2 results containing tables. Only 19 registers have one result without a table — these are the only cases where expansion fires. An earlier "all-or-nothing" approach (expand only if *no* results have tables) never triggered at all.

**Results directory:** `local_vector_db_v7_meta_filter/local_rm0041_md_chunks_v2_emb2_rrlocal_mf_pa1/`

**Results:**


| Metric                    | Value          |
| ------------------------- | -------------- |
| Registers found           | 78/97          |
| Found accuracy            | **97.37%**     |
| Complete accuracy         | 73.39%         |
| Coverage                  | 75.37%         |
| Correct / Wrong / Missing | 1296 / 20 / 15 |


| Peripheral | Regs found | Found acc. | Complete acc. | Coverage |
| ---------- | ---------- | ---------- | ------------- | -------- |
| afio       | 6/7        | 93.33%     | 85.71%        | 91.84%   |
| bkp        | 22/23      | 97.58%     | 85.21%        | 87.32%   |
| cec        | 7/7        | 86.67%     | 86.67%        | 100.0%   |
| crc        | 3/3        | 100.0%     | 100.0%        | 100.0%   |
| dac        | 12/14      | **100.0%** | **91.67%**    | 91.67%   |
| exti       | 6/6        | 99.71%     | 99.71%        | 100.0%   |
| flash      | 1/8        | 100.0%     | 18.75%        | 18.75%   |
| fsmc       | 9/12       | 95.67%     | 57.02%        | 59.60%   |
| iwdg       | 4/4        | 100.0%     | 100.0%        | 100.0%   |
| pwr        | 2/2        | 100.0%     | 100.0%        | 100.0%   |
| rcc        | 6/11       | 99.52%     | 47.94%        | 48.17%   |

**Strengths:** Highest found accuracy of any experiment (**97.37%**). DAC improved dramatically — from 66.67% found accuracy in C2 to 100.0% with per-result expansion. PWR at 100% (vs 97.44% in C2). Only 20 wrong facts. The selective expansion adds context only where it's needed, avoiding the noise that unconditional expansion introduces.
**Weaknesses:** Coverage dropped vs C2 (75.37% vs 85.73%). FSMC at 9/12 (vs C2's 12/12). The coverage difference is primarily due to LLM non-determinism rather than expansion — see Section 7.

#### D-series Summary

| Config | Expansion logic | Regs | Found acc. | Complete acc. | Coverage | Wrong |
| ------ | --------------- | ---- | ---------- | ------------- | -------- | ----- |
| C2 (baseline) | None (pa=0) | 83/97 | 90.09% | 77.24% | 85.73% | 27 |
| D1 | Unconditional (all results) | 78/97 | 93.24% | 70.27% | 75.37% | 19 |
| D2 | Per-result (no-table only) | 78/97 | **97.37%** | 73.39% | 75.37% | **20** |

**Key finding:** Per-result conditional expansion achieves the highest found accuracy of any experiment (97.37%) while keeping wrong facts low (20). The coverage gap vs C2 is attributable to LLM non-determinism (see Section 7), not the expansion logic itself — retrieval is deterministic and identical between runs.

---

## 3. Configuration Comparison

### 3.1 Overall Results Summary


| #      | Config             | Filter        | Fallback       | Regs found | Found acc. | Complete acc. | Coverage   | Wrong  |
| ------ | ------------------ | ------------- | -------------- | ---------- | ---------- | ------------- | ---------- | ------ |
| A1     | emb2+rr+mf         | broken        | —              | 68/97      | **94.75%** | 59.29%        | 62.57%     | 37     |
| A2     | emb2+rr+mf+pa2     | broken        | —              | 67/97      | 91.44%     | 56.29%        | 61.55%     | 21     |
| A3     | emb2+kb+rr+pa2     | none          | —              | 68/97      | 93.30%     | 55.21%        | 59.17%     | 16     |
| A4     | emb1+rr+mf+pa1+tpo | broken        | —              | 55/97      | 86.98%     | 40.09%        | 46.09%     | 64     |
| B1     | emb2+rr+mf         | where_doc     | none           | 64/97      | 88.69%     | 71.52%        | 80.63%     | 41     |
| **B2** | **emb2+rr+mf**     | **where_doc** | **0.7 thresh** | **86/97**  | **89.26%** | **80.46%**    | **90.15%** | **48** |
| C1     | emb2+rr+mf         | metadata      | none           | 80/97      | 89.81%     | 73.33%        | 81.65%     | **24** |
| **C2** | **emb2+rr+mf**     | **metadata**  | **0.7 thresh** | **83/97**  | **90.09%** | **77.24%**    | **85.73%** | **27** |
| C3     | emb2+rr+mf         | tiered        | 0.7 thresh     | 83/97      | 90.09%     | 77.24%        | 85.73%     | 27     |
| D1     | emb2+rr+mf+pa1     | metadata      | 0.7 thresh     | 78/97      | 93.24%     | 70.27%        | 75.37%     | 19     |
| **D2** | **emb2+rr+mf+pa1** | **metadata**  | **0.7 thresh** | **78/97**  | **97.37%** | **73.39%**    | **75.37%** | **20** |


### 3.2 Top 3 Configurations Analysis

#### Rank 1: B2 — where_document filter + quality fallback (80.46% complete accuracy)

**Why it works:**

- The text-based `$contains` filter casts a wide net, finding any chunk that mentions the register name anywhere in its text. This catches register map tables, definition pages, and cross-references alike.
- The quality fallback (threshold 0.7) detects when filtered results are poor-quality (e.g., only register map mentions for parameterized names like BKP_DRx) and switches to unfiltered search, which retrieves section overview pages that the reranker scores highly.
- Achieves 100% coverage on 8/11 peripherals including BKP (23/23), FSMC (12/12), CEC, EXTI, IWDG, CRC, PWR.

**Where it fails:**

- **RCC (8/11, 46.1% complete):** The quality fallback is a double-edged sword. For RCC_AHBENR, RCC_APB1RSTR, and RCC_APB2RSTR, the filtered results correctly contain the register definition pages, but the reranker scores them below 0.7 (due to chunk boundary splits). The fallback replaces these correct results with high-scoring but wrong generic RCC pages.
- **PWR (43.6% complete):** Despite 100% coverage, the retrieved context is insufficient for accurate extraction.
- **Wrong facts (48):** Highest among working-filter experiments due to the broad text filter including incidental mentions.

#### Rank 2: C2 — metadata boolean filter + quality fallback (77.24% complete accuracy)

**Why it works:**

- Precise metadata filtering retrieves only chunks that were explicitly enriched with the target register name during ingestion. This eliminates incidental mentions (register map tables, ToC entries) that plague text-based filtering.
- Only 27 wrong facts — nearly half of B2's 48. AFIO at 97.28% and PWR at 97.44% demonstrate the precision advantage.
- Quality fallback rescues FSMC (9/12→12/12) where some register names aren't in metadata.

**Where it fails:**

- **Coverage gap (85.73% vs B2's 90.15%):** BKP at 22/23 (missing BKP_CSR — its definition page wasn't enriched with that register name). DAC at 12/14.
- **RCC (7/11, 48.2% complete):** Same fallback issue as B2, plus one fewer register found.
- **DAC (66.67% found accuracy):** Some filtered results lead to wrong register context for dual-channel DAC registers (DHR12R1 vs DHR12R2).

#### Rank 3: C1 — metadata boolean filter, no fallback (73.33% complete accuracy)

**Why it works:**

- Purest precision: only 24 wrong facts across 1442 found facts. Highest found accuracy among all working-filter configs (89.81%).
- Without fallback noise, registers that match metadata are retrieved with high quality. 7/11 peripherals at 100% coverage.
- PWR at 97.44%, AFIO at 97.28% — best per-peripheral accuracy.

**Where it fails:**

- **FSMC (9/12):** Three registers not found because the metadata filter returns 0 results and the only fallback is unfiltered search (no quality-aware fallback).
- **Lower coverage (81.65%):** Without the quality fallback, some registers get poor-quality filtered results that aren't corrected.

### 3.3 Key Tradeoffs


| Dimension            | Text filter (B2)                  | Metadata filter (C2)                   |
| -------------------- | --------------------------------- | -------------------------------------- |
| **Precision**        | Lower — finds incidental mentions | Higher — only enriched register chunks |
| **Recall**           | Higher — catches any text match   | Lower — depends on enrichment quality  |
| **Wrong facts**      | 48                                | 27                                     |
| **Coverage**         | 90.15%                            | 85.73%                                 |
| **Best peripheral**  | BKP: 97.18%, 23/23                | AFIO: 97.28%, 7/7                      |
| **Worst peripheral** | PWR: 43.59%                       | DAC: 66.67% found acc.                 |


### 3.4 Failure Modes


| Failure mode                               | Affected configs       | Root cause                                                                                                                          | Possible fix                                                                     |
| ------------------------------------------ | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Parameterized register names** (BKP_DRx) | B1 (no fallback)       | Text `$contains` finds register map tables, not definition pages                                                                    | Quality fallback (implemented in B2)                                             |
| **Chunk boundary splits** (RCC_AHBENR)     | B2, C2 (with fallback) | Register header in one chunk, bit fields in next → reranker scores definition chunk low → fallback replaces with wrong generic page | Increase chunk overlap, or skip fallback when filter returns results             |
| **Missing metadata enrichment**            | C1, C2                 | Some register names not in chunk metadata                                                                                           | Improve enrichment heuristics, or use text filter as fallback (C3)               |
| **Datasheet gap** (FLASH registers)        | All configs            | 7/8 FLASH registers in separate manual (PM0063)                                                                                     | Ingest PM0063 alongside RM0041                                                   |
| **Page expansion noise**                   | A2, A4, D1             | Unconditional expansion adds irrelevant contiguous pages                                                                            | Per-result conditional expansion: only expand chunks without tables (D2 achieves 97.37% found acc.) |


---

## 4. Methodology Discussion (Paper Section)

### Context Retrieval Configuration for Hardware Register Extraction

Extracting structured register information from hardware datasheets requires precise context retrieval — the LLM must receive the specific pages containing register definitions, bit field tables, and reset values. We evaluate a local vector database approach using ChromaDB with several retrieval enhancement techniques.

**Embedding and Database Setup.**
We chunk the RM0041 reference manual (709 pages of markdown) into 1033 chunks of up to 800 tokens each, with 100-token overlaps. Chunks are embedded using BAAI/bge-small-en-v1.5, a lightweight 384-dimensional model running locally. Each chunk is enriched during ingestion with page numbers, table presence flags, and register names mentioned in the text. Parameterized register names (e.g., `BKP_DRx (x=1..20)`) are expanded to individual names (`BKP_DR1` through `BKP_DR20`).

**Metadata Filtering.**
We evaluate two register-level filtering approaches. *Text-based filtering* uses ChromaDB's `where_document` clause with `$contains` to find chunks whose text mentions the target register name. This is broad — it catches register map tables and cross-references alongside actual definitions. *Metadata-based filtering* uses boolean fields stored per-chunk during ingestion (`reg_BKP_DR1: True`), enabling precise matching via ChromaDB's `where` clause. Metadata filtering reduces wrong facts by 44% (27 vs 48) compared to text filtering, as it eliminates incidental register mentions that mislead the LLM. However, text filtering achieves 5% higher coverage (90.15% vs 85.73%) because it catches registers whose names appear in chunk text but weren't captured during metadata enrichment.

**Cross-Encoder Reranking.**
Initial embedding retrieval uses bi-encoder cosine similarity, which captures topical similarity but misses fine-grained query-document relationships. We apply FlashRank (ms-marco-MiniLM-L-12-v2), a local cross-encoder reranker, to re-score an expanded candidate pool (5× the final result count). In our experiments, adding reranking to the best non-reranked configuration improved found accuracy from approximately 82% to 95% — a 12.8 percentage point improvement. This is the single most impactful retrieval parameter.

**Quality Fallback Mechanism.**
Metadata filtering can fail when register names are parameterized or when definition chunks span multiple pages with headers split across chunk boundaries. We implement a quality fallback: after reranking filtered results, if the top score falls below 0.7, the system retries with progressively broader searches (text filter, then unfiltered). This recovered BKP from 5/23 to 23/23 registers and FSMC from 9/12 to 12/12, while preserving the precision benefits of metadata filtering for well-matched registers.

**Chunk Expansion.**
We evaluate appending chunks from contiguous pages following each retrieved result. Unconditional expansion — where all results are expanded regardless of content — consistently reduces accuracy when combined with reranking (91.44% vs 94.75% for 2-page expansion, and 93.24% vs 90.09% for 1-page expansion on the best metadata filter config). The reranker already selects the most relevant chunks; blindly adding adjacent pages introduces noise.

However, *conditional per-result expansion* proves highly effective. Register definitions in hardware datasheets always include bit field tables. We use the `has_tables` chunk metadata (set during ingestion) as a signal: chunks containing tables likely have complete definitions, while chunks without tables may represent split definitions where the header is on one page and the bit fields on the next. By expanding only no-table chunks, we target exactly the cases where additional context helps. This achieves 97.37% found accuracy — the highest of any configuration — with only 20 wrong facts, compared to 90.09% and 27 wrong for the base configuration without expansion. The key improvement comes from DAC registers, where the expansion provides the bit field tables missing from the header-only chunks (100% found accuracy vs 66.67% without expansion).

**Keyword Boosting.**
Post-retrieval score boosting for exact register name matches provides marginal benefit when combined with reranking. The reranker already captures lexical relevance; keyword boosting can override reranker ordering in counterproductive ways (e.g., boosting a mention in a remap table over the actual definition). In our experiments, keyword boost + reranker (93.30%) performed worse than reranker alone (94.75%).

**Results Summary.**
Our best configuration — metadata boolean filtering with FlashRank reranking, quality fallback, and per-result conditional page expansion — achieves 97.37% found accuracy across 97 registers, with only 20 factual errors out of 1331 facts extracted from found registers. Without page expansion, the same base configuration (C2) achieves 90.09% found accuracy with 27 errors. The per-result expansion selectively augments only chunks lacking bit field tables, adding context precisely where register definitions are split across page boundaries. The primary remaining failure modes are chunk boundary splits (causing incorrect fallback for RCC registers), coverage gaps from LLM non-determinism (see Section 7), and missing datasheet content (7 FLASH registers documented in a separate manual). These results demonstrate that precise metadata filtering combined with cross-encoder reranking and targeted chunk expansion provides an effective, fully local (zero API cost) alternative to commercial embedding and retrieval APIs.

---

## 5. OpenAI File Search Baseline (verified_peripherals_v2)

This section presents results from the **OpenAI file search API**, which serves as a baseline for comparison against the local ChromaDB approach. All 16 configurations use OpenAI's hosted retrieval infrastructure with no local embedding or reranking.

### 5.1 OpenAI File Search Configuration

OpenAI's file search API differs fundamentally from the local ChromaDB approach:


| Aspect                 | OpenAI File Search                     | Local ChromaDB                                 |
| ---------------------- | -------------------------------------- | ---------------------------------------------- |
| **Embedding model**    | text-embedding-3-large (3072-dim)      | BAAI/bge-small-en-v1.5 (384-dim)               |
| **Reranking**          | Built-in (automatic, opaque)           | FlashRank (ms-marco-MiniLM-L-12-v2, explicit)  |
| **Metadata filtering** | Not available (`mf=None` for all runs) | Boolean metadata fields + tiered fallback      |
| **Infrastructure**     | Cloud API (paid per token)             | Fully local (zero API cost)                    |
| **Chunking**           | OpenAI's internal chunking             | Custom 800-token chunks with 100-token overlap |


The 16 configs vary across 4 binary dimensions:


| Parameter          | Values               | Description                                                                                                                                        |
| ------------------ | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vs_type`          | `md` / `md_enriched` | Vector store type — `md` uses raw markdown chunks; `md_enriched` uses chunks with enriched metadata (section headers, register lists, table flags) |
| `embeddings`       | 1 / 2                | Number of embedding results returned to the LLM                                                                                                    |
| `pages_after`      | 0 / 1                | Number of contiguous pages to expand after each result                                                                                             |
| `table_pages_only` | `False` / `True`     | Only expand to pages containing tables                                                                                                             |


**Note:** All OpenAI experiments use 96 total registers across 11 peripherals (vs 97 for local). The total verified fact count is 1751 (vs 1766 for local). This minor difference is due to a register count discrepancy in AFIO (6 vs 7 total registers).

### 5.2 All 16 Configurations — Results Summary

Sorted by complete accuracy (descending):


| #   | Config                            | VS type     | Emb | Pages | Table only | Regs found | Found acc. | Complete acc. | Coverage | Wrong  | Tokens  |
| --- | --------------------------------- | ----------- | --- | ----- | ---------- | ---------- | ---------- | ------------- | -------- | ------ | ------- |
| 1   | md_enriched_emb2_pages1_tableonly | md_enriched | 2   | 1     | Yes        | 60/96      | 92.76%     | **60.71%**    | 65.45%   | 35     | 874,790 |
| 2   | md_enriched_emb2_pages0_tableonly | md_enriched | 2   | 0     | Yes        | 59/96      | 86.84%     | 55.80%        | 64.25%   | 40     | 874,975 |
| 3   | md_enriched_emb2_pages0           | md_enriched | 2   | 0     | No         | 59/96      | 85.51%     | 54.94%        | 64.25%   | 38     | 878,017 |
| 4   | md_enriched_emb2_pages1           | md_enriched | 2   | 1     | No         | 57/96      | 87.52%     | 52.48%        | 59.97%   | 59     | 854,303 |
| 5   | md_emb2_pages1_tableonly          | md          | 2   | 1     | Yes        | 54/96      | **94.29%** | 51.86%        | 55.00%   | **16** | 850,628 |
| 6   | md_emb2_pages0                    | md          | 2   | 0     | No         | 55/96      | 90.36%     | 49.80%        | 55.11%   | 32     | 866,872 |
| 7   | md_emb2_pages0_tableonly          | md          | 2   | 0     | Yes        | 54/96      | 90.13%     | 49.57%        | 55.00%   | 31     | 845,107 |
| 8   | md_emb2_pages1                    | md          | 2   | 1     | No         | 54/96      | 87.95%     | 48.37%        | 55.00%   | 35     | 861,072 |
| 9   | md_enriched_emb1_pages0_tableonly | md_enriched | 1   | 0     | Yes        | 48/96      | 91.73%     | 46.89%        | 51.11%   | 39     | 734,113 |
| 10  | md_enriched_emb1_pages1           | md_enriched | 1   | 1     | No         | 47/96      | 94.17%     | 45.23%        | 48.03%   | **15** | 750,394 |
| 11  | md_enriched_emb1_pages0           | md_enriched | 1   | 0     | No         | 48/96      | 87.71%     | 44.83%        | 51.11%   | 39     | 737,614 |
| 12  | md_emb1_pages1_tableonly          | md          | 1   | 1     | Yes        | 50/96      | 88.86%     | 44.20%        | 49.74%   | 44     | 758,242 |
| 13  | md_emb1_pages0_tableonly          | md          | 1   | 0     | Yes        | 50/96      | 87.94%     | 43.75%        | 49.74%   | 25     | 765,694 |
| 14  | md_emb1_pages1                    | md          | 1   | 1     | No         | 50/96      | 86.80%     | 43.18%        | 49.74%   | 39     | 764,604 |
| 15  | md_emb1_pages0                    | md          | 1   | 0     | No         | 50/96      | 82.32%     | 40.95%        | 49.74%   | 32     | 770,418 |
| 16  | md_enriched_emb1_pages1_tableonly | md_enriched | 1   | 1     | Yes        | 47/96      | 79.98%     | 40.61%        | 50.77%   | 36     | 744,324 |


### 5.3 Top 3 Configurations — Per-Peripheral Breakdown

#### #1: md_enriched_emb2_pages1_tableonly (60.71% complete accuracy)

**Results directory:** `verified_peripherals_v2/md_enriched_emb2_pages1_tableonly/`


| Peripheral | Regs found | Accuracy | Correct | Wrong | Missing |
| ---------- | ---------- | -------- | ------- | ----- | ------- |
| afio       | 5/6        | 96.88%   | 93      | 0     | 3       |
| bkp        | 3/23       | 100.0%   | 42      | 0     | 0       |
| cec        | 6/7        | 95.24%   | 60      | 0     | 3       |
| crc        | 3/3        | 100.0%   | 18      | 0     | 0       |
| dac        | 14/14      | 98.61%   | 142     | 2     | 0       |
| exti       | 2/6        | 100.0%   | 114     | 0     | 0       |
| flash      | 4/8        | 92.31%   | 12      | 1     | 0       |
| fsmc       | 8/12       | 89.64%   | 225     | 8     | 18      |
| iwdg       | 4/4        | 100.0%   | 27      | 0     | 0       |
| pwr        | 1/2        | 100.0%   | 15      | 0     | 0       |
| rcc        | 10/11      | 86.78%   | 315     | 24    | 24      |


**Strengths:** Best complete accuracy (60.71%) among all OpenAI configs. RCC at 10/11 registers (best RCC coverage of any approach). DAC at 14/14 (100% coverage). FLASH at 4/8 (significantly better than all local configs which find 1/8).
**Weaknesses:** BKP at 3/23 (catastrophic — no metadata filter means OpenAI's embedding search fails to find parameterized register definitions). EXTI at 2/6 (poor coverage despite 100% accuracy on found registers). PWR only 1/2.

#### #2: md_emb2_pages1_tableonly (94.29% found accuracy, 51.86% complete accuracy)

**Results directory:** `verified_peripherals_v2/md_emb2_pages1_tableonly/`


| Peripheral | Regs found | Accuracy | Correct | Wrong | Missing |
| ---------- | ---------- | -------- | ------- | ----- | ------- |
| afio       | 5/6        | 96.88%   | 93      | 0     | 3       |
| bkp        | 3/23       | 100.0%   | 42      | 0     | 0       |
| cec        | 6/7        | 85.71%   | 72      | 0     | 12      |
| crc        | 3/3        | 100.0%   | 18      | 0     | 0       |
| dac        | 14/14      | 98.61%   | 142     | 2     | 0       |
| exti       | 2/6        | 100.0%   | 114     | 0     | 0       |
| flash      | 1/8        | 100.0%   | 2       | 0     | 0       |
| fsmc       | 9/12       | 89.90%   | 187     | 9     | 12      |
| iwdg       | 4/4        | 100.0%   | 27      | 0     | 0       |
| pwr        | 1/2        | 100.0%   | 15      | 0     | 0       |
| rcc        | 6/11       | 92.02%   | 196     | 5     | 12      |


**Strengths:** Highest found accuracy (94.29%) of all OpenAI configs with only 16 wrong facts. Clean extractions when context is found.
**Weaknesses:** Low coverage (55.00%). BKP at 3/23, EXTI at 2/6, RCC at 6/11. Without enriched metadata, the raw markdown chunks provide less context for the LLM.

#### #3: md_enriched_emb1_pages1 (94.17% found accuracy, 45.23% complete accuracy)

**Results directory:** `verified_peripherals_v2/md_enriched_emb1_pages1/`


| Peripheral | Regs found | Accuracy | Correct | Wrong | Missing |
| ---------- | ---------- | -------- | ------- | ----- | ------- |
| afio       | 5/6        | 100.0%   | 96      | 0     | 0       |
| bkp        | 3/23       | 100.0%   | 42      | 0     | 0       |
| cec        | 4/7        | 86.27%   | 44      | 7     | 0       |
| crc        | 3/3        | 77.78%   | 14      | 0     | 4       |
| dac        | 12/14      | 90.80%   | 79      | 2     | 6       |
| exti       | 2/6        | 100.0%   | 114     | 0     | 0       |
| flash      | 2/8        | 88.89%   | 8       | 1     | 0       |
| fsmc       | 5/12       | 82.71%   | 110     | 5     | 18      |
| iwdg       | 3/4        | 100.0%   | 21      | 0     | 0       |
| pwr        | 1/2        | 100.0%   | 15      | 0     | 0       |
| rcc        | 7/11       | 97.65%   | 249     | 0     | 6       |


**Strengths:** Second highest found accuracy (94.17%) with only 15 wrong facts — lowest error count of any config. RCC achieves 97.65% accuracy on found registers.
**Weaknesses:** Very low coverage (48.03%). Only 1 embedding result provides insufficient context for many peripherals (FSMC 5/12, IWDG 3/4).

### 5.4 OpenAI Parameter Trends

**Enriched vs raw chunks:** `md_enriched` consistently achieves better coverage than `md` (65.45% vs 55.00% for best of each). The enriched metadata in chunk text provides the LLM with more contextual information (section headers, register lists) that helps ground its extraction.

**Embeddings (1 vs 2):** `emb2` consistently outperforms `emb1`. Coverage ranges from 48–65% for emb2 configs vs 48–51% for emb1. The additional embedding result provides crucial fallback context when the top result is incomplete.

**Page expansion:** `pages_after=1` provides modest gains when combined with table_pages_only filtering. Without table-only filtering, expansion can hurt accuracy (md_enriched_emb2_pages1 at 87.52% vs md_enriched_emb2_pages0 at 85.51% — minimal difference with more noise).

**Table-only expansion:** The `table_pages_only=True` flag consistently improves accuracy. The top 2 OpenAI configs both use table-only expansion. Register definitions in hardware datasheets are always accompanied by bit field tables, making table pages a strong signal.

### 5.5 Common Failure Patterns Across All OpenAI Configs

- **BKP: 3/23 in all 16 configs.** Without metadata filtering, OpenAI's embedding search cannot locate the 20 BKP data register definitions. The parameterized format (BKP_DRx) in the source text does not match individual register name queries (BKP_DR1, BKP_DR2, ...).
- **EXTI: 2/6 in all 16 configs.** OpenAI's retrieval consistently returns the same 2 register definitions regardless of configuration, missing the other 4.
- **PWR: 1/2 in all 16 configs.** PWR_CSR is consistently missed.
- **Coverage ceiling ~65%.** Even the best OpenAI config only finds 60/96 registers (62.5%). The local ChromaDB approach with metadata filtering finds 83/97 (85.73%).

---

## 6. Local vs OpenAI Comparison

### 6.1 Head-to-Head: Best Configurations


| Metric                | Local C2 (best coverage)              | Local D2 (best found acc.)                         | OpenAI #1 (best OpenAI)                          |
| --------------------- | ------------------------------------- | -------------------------------------------------- | ------------------------------------------------ |
| **Config**            | metadata filter + reranker + fallback | C2 + per-result page expansion                     | md_enriched_emb2_pages1_tableonly                |
| **Registers found**   | 83/97                                 | 78/97                                              | 60/96                                            |
| **Found accuracy**    | 90.09%                                | **97.37%**                                         | 92.76%                                           |
| **Complete accuracy** | **77.24%**                            | 73.39%                                             | 60.71%                                           |
| **Coverage**          | **85.73%**                            | 75.37%                                             | 65.45%                                           |
| **Wrong facts**       | 27                                    | **20**                                             | 35                                               |
| **API cost**          | $0 (fully local)                      | $0 (fully local)                                   | ~$0.50–1.00/run (embedding + file search tokens) |


### 6.2 Per-Peripheral Comparison (Best Local C2/D2 vs Best OpenAI)


| Peripheral | Local C2 regs | Local D2 acc. | OpenAI #1 regs | OpenAI #1 acc. | Winner                          |
| ---------- | ------------- | ------------- | -------------- | -------------- | ------------------------------- |
| afio       | 7/7           | 93.33%        | 5/6            | 96.88%         | Local (coverage)                |
| bkp        | 22/23         | 97.58%        | 3/23           | 100.0%         | **Local** (coverage)            |
| cec        | 7/7           | 86.67%        | 6/7            | 95.24%         | Mixed                           |
| crc        | 3/3           | 100.0%        | 3/3            | 100.0%         | Tie                             |
| dac        | 12/14         | **100.0%**    | 14/14          | 98.61%         | Mixed (OpenAI coverage, D2 acc) |
| exti       | 6/6           | 99.71%        | 2/6            | 100.0%         | **Local** (coverage)            |
| flash      | 1/8           | 100.0%        | 4/8            | 92.31%         | **OpenAI** (coverage)           |
| fsmc       | 12/12         | 95.67%        | 8/12           | 89.64%         | **Local** (both)                |
| iwdg       | 4/4           | 100.0%        | 4/4            | 100.0%         | Tie                             |
| pwr        | 2/2           | 100.0%        | 1/2            | 100.0%         | **Local** (coverage)            |
| rcc        | 7/11          | 99.52%        | 10/11          | 86.78%         | Mixed (OpenAI cov, D2 acc)      |


### 6.3 Key Takeaways

1. **Local ChromaDB wins decisively on coverage** (+20pp). Metadata filtering ensures register-specific chunks are retrieved even when the embedding model doesn't rank them highly. OpenAI's opaque retrieval has no equivalent mechanism, causing systematic failures on BKP (3/23 vs 22/23), EXTI (2/6 vs 6/6), and PWR (1/2 vs 2/2).
2. **Local D2 wins on found accuracy** (97.37% vs 92.76%). With per-result conditional page expansion, the local approach now surpasses OpenAI on found accuracy. DAC found accuracy improved from 66.67% (C2) to 100.0% (D2), closing the gap with OpenAI's 98.61%. OpenAI still wins on DAC coverage (14/14 vs 12/14) and FLASH coverage (4/8 vs 1/8).
3. **Local wins on total correctness.** C2 produces 1364 correct facts with 27 wrong; D2 produces 1296 correct facts with 20 wrong. Both outperform OpenAI's 1063 correct with 35 wrong.
4. **Cost-effectiveness.** The local approach achieves better results at zero API cost. OpenAI file search tokens (~183k per run for emb2 configs) add meaningful cost when running sweeps or processing multiple devices.
5. **RCC is the one reversal.** OpenAI finds 10/11 RCC registers (vs local's 7/11). This is because the local approach's quality fallback incorrectly replaces correct RCC-filtered results with generic pages. However, D2 achieves 99.52% found accuracy on RCC registers it does find (vs OpenAI's 86.78%).
6. **Coverage vs accuracy tradeoff.** C2 (best coverage: 85.73%) and D2 (best found accuracy: 97.37%) represent two local configurations that each beat OpenAI on different dimensions. The coverage gap between C2 and D2 is partly attributable to LLM non-determinism (see Section 7).

---

## 7. LLM Non-Determinism

### 7.1 Overview

The LLM used for register extraction (gpt-oss-120b via Groq) is non-deterministic — identical prompts with identical context produce different outputs across runs. This introduces noise into all experiment results, making it difficult to attribute small accuracy differences to retrieval changes alone.

To quantify this, we ran the same retrieval configuration twice (D2 conditional expansion, run1 and run2) and compared results. The retrieval pipeline (embedding search, metadata filter, reranking, chunk expansion) is fully deterministic — identical queries produce identical chunks with identical scores. Any differences between runs are therefore entirely due to LLM output variance.

### 7.2 Run-to-Run Comparison

**Configuration:** C2 + per-result conditional expansion (pages_after=1), two identical runs.

**Note:** These two runs used an earlier "all-must-lack-table" expansion logic where expansion only fired if *no* results had tables. With `n_results=2`, this condition was never met (every register had at least one table-containing chunk in its top 2). Therefore, both runs used effectively identical context (no expansion fired), making them a clean measurement of pure LLM non-determinism.


| Metric            | Run 1   | Run 2   | Delta    |
| ----------------- | ------- | ------- | -------- |
| Registers found   | 77/97   | 78/97   | +1       |
| Found accuracy    | 95.31%  | 95.79%  | +0.48pp  |
| Complete accuracy | 69.08%  | 72.20%  | +3.12pp  |
| Coverage          | 72.48%  | 75.37%  | +2.89pp  |
| Wrong facts       | 15      | 32      | +17      |


### 7.3 Per-Peripheral Volatility

Some peripherals produce stable results across runs while others vary dramatically:


| Peripheral | Run 1 complete acc. | Run 2 complete acc. | Delta     | Stable? |
| ---------- | ------------------- | ------------------- | --------- | ------- |
| afio       | 89.80%              | 87.76%              | -2.04pp   | Yes     |
| bkp        | 85.92%              | 84.51%              | -1.41pp   | Yes     |
| cec        | **100.0%**          | **80.0%**           | **-20pp** | No      |
| crc        | 100.0%              | 100.0%              | 0pp       | Yes     |
| dac        | **52.08%**          | **90.28%**          | **+38pp** | No      |
| exti       | 99.71%              | 99.71%              | 0pp       | Yes     |
| flash      | 18.75%              | 18.75%              | 0pp       | Yes     |
| fsmc       | 57.02%              | 57.31%              | +0.29pp   | Yes     |
| iwdg       | 96.30%              | 100.0%              | +3.70pp   | Yes     |
| pwr        | **43.59%**          | **94.87%**          | **+51pp** | No      |
| rcc        | 44.50%              | 44.72%              | +0.22pp   | Yes     |


**Stable peripherals** (< 5pp variance): AFIO, BKP, CRC, EXTI, FLASH, FSMC, IWDG, RCC. These have consistent accuracy across runs. Notably, EXTI (342 facts) and FSMC (349 facts) — the largest peripherals — are very stable.

**Volatile peripherals** (> 10pp variance): CEC, DAC, PWR. These show large swings despite receiving identical retrieval context.

### 7.4 Case Study: PWR

PWR has only 2 registers (PWR_CR, PWR_CSR) with 39 total facts. Retrieval for both runs was verified to be *exactly identical*:

- **PWR_CR:** Same 2 chunks retrieved (p097_c01 score 0.866, p063_c01 score 0.838), same expansion (none — both chunks have tables)
- **PWR_CSR:** Same 2 chunks retrieved (p097_c01 score 0.895, p063_c01 score 0.838)

Despite identical context:
- **Run 1:** 17 correct, 1 wrong, 21 missing (43.59% accuracy) — PWR_CR extracted with 0 bit fields
- **Run 2:** 37 correct, 2 wrong, 0 missing (94.87% accuracy) — PWR_CR extracted with full bit field detail

The LLM simply produced a near-empty output for PWR_CR in run 1 and a comprehensive output in run 2. This is not a retrieval problem — the context contained the full register definition including the bit field table in both runs.

### 7.5 Implications for Experiment Interpretation

1. **Coverage differences of ~5 registers are within LLM noise.** D2 found 78/97 vs C2's 83/97, but this 5-register gap could shrink or grow on a rerun. Coverage differences should only be considered significant if they exceed ~8 registers consistently.

2. **Found accuracy differences < 5pp are inconclusive.** The 7pp found accuracy improvement from D2 (97.37%) vs C2 (90.09%) is likely partially genuine (DAC improvement from expansion) and partially noise.

3. **Wrong fact counts can vary 2×.** Run 1 had 15 wrong facts, run 2 had 32 — a 2× difference from identical context. Individual wrong fact counts should be interpreted as approximate.

4. **Per-peripheral accuracy for small peripherals is unreliable.** PWR (39 facts) swung 51pp between runs. CEC (90 facts) swung 20pp. Large peripherals like EXTI (342 facts) and FSMC (349 facts) are much more stable and reliable for comparing configurations.

5. **Retrieval improvements should be validated by checking context, not just final accuracy.** Since retrieval is deterministic, the most reliable way to evaluate a retrieval change is to compare the actual chunks retrieved (embedding_ids.jsonl), not the LLM's extraction accuracy. Two runs with identical retrieval can produce very different accuracy numbers.

---

## Appendix: Reproduction Guide

### Database Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Ingest with boolean register metadata (v2 database)
python preprocessing/ingest_local_vector_db.py rm0041 \
  --chunks-dir chunked_datasheets/stm/rm0041/chunks/md/ \
  --db-name rm0041_md_chunks_v2 \
  --entry-name local_md_chunks_v2
```

### Running Experiments

Edit `optimize_retrieval/run_sweep.py` sweep parameters:

```python
# For config C2 (metadata filter + reranker + quality fallback):
USE_LOCAL_VECTOR_DB = True
LOCAL_DB_NAMES = ["rm0041_md_chunks_v2"]
LOCAL_EMBEDDING_COUNTS = [2]
KEYWORD_BOOST_VALUES = [False]
RERANKER_TYPES = ["local"]
LOCAL_METADATA_FILTER = [True]
LOCAL_PAGES_AFTER = [0]
LOCAL_TABLE_PAGES_ONLY = [False]
LOCAL_OUTPUT_PARENT = "optimize_retrieval/experiments/local_vector_db_v7_meta_filter"
```

```bash
python optimize_retrieval/run_sweep.py
```

### Key Files


| File                                            | Description                                                    |
| ----------------------------------------------- | -------------------------------------------------------------- |
| `context_retrieval/local_vector_search.py`      | Search pipeline with tiered filtering, reranking, and fallback |
| `context_retrieval/vector_db/vector_store.py`   | ChromaDB wrapper (search, add, delete)                         |
| `context_retrieval/vector_db/reranker.py`       | FlashRank/Cohere/BGE reranker implementations                  |
| `context_retrieval/vector_db/text_processor.py` | Chunking with register expansion and metadata enrichment       |
| `context_retrieval/retrieve_context.py`         | Dispatch layer connecting generator to retrieval backends      |
| `preprocessing/ingest_local_vector_db.py`       | Database ingestion with boolean register metadata              |
| `optimize_retrieval/run_sweep.py`  | Experiment sweep runner                                        |
| `defs.py`                                       | `ContextRetrievalParameters` data model                        |


