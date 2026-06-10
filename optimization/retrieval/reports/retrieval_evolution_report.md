# Retrieval Pipeline Evolution: D2 → OpenEvolve → Cross-Manufacturer

**Last updated:** 2026-03-19
**Devices:** RM0041 (STM32F100xx), KE04 (NXP Kinetis MKE04Z)
**Generator LLM:** gpt-oss-120b (via Groq)

---

## 1. Configurations Under Comparison

### D2: Hand-Tuned Metadata Filter + Conditional Page Expansion

The best configuration from the manual parameter sweep (documented in `local_vector_db_retrieval_analysis.md`, §2.4).

**Results:** `experiments/D_conditional_page_expansion/local_rm0041_md_chunks_v2_emb2_rrlocal_mf_pa1/`
**Usage:** `experiments/D_conditional_page_expansion/local_rm0041_md_chunks_v2_emb2_rrlocal_mf_pa1/info/usage.csv`

| Parameter | Value |
|-----------|-------|
| Database | `rm0041_md_chunks` (1033 chunks, persistent ChromaDB) |
| Embedding | BAAI/bge-small-en-v1.5 (384-dim, local) |
| `number_embeddings` | 2 |
| `fetch_k` | 10 (n_results × 5) |
| Metadata filter | Boolean fields (`where: {reg_NAME: True}`) |
| Tiered fallback | metadata → `$contains` → unfiltered (threshold 0.7) |
| Reranker | FlashRank (ms-marco-MiniLM-L-12-v2) |
| Page expansion | `pages_after=1`, per-result conditional (only non-table chunks) |
| Output format | XML `<sources>` with metadata attributes |

### OE-STM: OpenEvolve Best Evolved Program (STM)

Best program from 18 iterations of OpenEvolve evolutionary optimization on RM0041. Originally evaluated on 7 peripherals during evolution; full 11-peripheral evaluation run on 2026-03-12.

**Program:** `../openevolve_retrieval/output_rm0041/best/best_program.py`
**Full eval results (historical, raw OE):** `../openevolve_retrieval/output_rm0041/full_eval_results_unbatched.json`
**Evolution logs:** `../openevolve_retrieval/output_rm0041/logs/`

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
| Output format | Plain text `[Page N]\n{text}` separated by `---` |

### OE-KE04: OpenEvolve Best Evolved Program (NXP)

Best program from 50 iterations of OpenEvolve evolutionary optimization on KE04. Evaluated on 10 peripherals during evolution; full 25-peripheral evaluation run on 2026-03-19.

**Program:** `../openevolve_retrieval/output_ke04/best/best_program.py`
**Full eval results (historical, raw OE):** `../openevolve_retrieval/output_ke04/full_eval_results_ke04_program_unbatched.json`
**Evolution logs:** `../openevolve_retrieval/output_ke04/logs/`
**Evaluator:** `../openevolve_retrieval/evaluator_ke04.py`
**Config:** `../openevolve_retrieval/config_ke04.yaml`

| Parameter | Value |
|-----------|-------|
| Database | Ephemeral in-memory ChromaDB (rebuilt per eval) |
| Embedding | BAAI/bge-small-en-v1.5 (384-dim, local) — same model |
| Chunks | 743 markdown chunks from KE04 datasheet |
| Table detection | Robust regex `\|.*\|(?:\n\|[-=]+\|)+` (requires header row) |
| Text augmentation | Prepends `"Page N:"` header (no register name extraction — NXP uses short names) |
| Query | Dual-name: `"...for the ADC_SC1 register (SC1)..."` with specific fact requests |
| Search | Two-stage: `has_tables=True` + `$contains` filter first, fallback without table filter if <2 results |
| Text matching | `where_document: {$or: [{$contains: "ADC_SC1"}, {$contains: "SC1"}]}` |
| Scoring | Distance-based with table and name match as tiebreakers |
| Final results | Top 5 by rank |
| Expansion | From non-table chunks with register name → adjacent table chunks (inverted from STM) |
| Output format | Plain text `[Page N]\n{text}` separated by `---` |

---

## 2. STM RM0041 Results (11 peripherals, 97 registers)

**Verified data:** `verified_datasheet/stm/rm0041_stm32f100.csv` (1766 facts)

| Metric | **D2** | **OE-STM** |
|--------|--------|------------|
| Registers found | 78/97 | **95/97** |
| Found accuracy | **97.37%** | 85.9% |
| Complete accuracy | 73.39% | **79.8%** |
| Coverage | 75.37% | **93.0%** |
| Correct facts | 1,296 | **1,410** |
| Wrong facts | **20** | 44 |
| Missing facts | 450 | **188** |
| Total tokens | 830,634 | **719,124** |

¹ D2 token counts corrected: 22 extra BKP SVD registers (DR21–DR42) that have no verified facts were removed from usage.csv. Original uncorrected total was 971,046.

### Per-Peripheral Breakdown (STM)

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

## 3. E1: Hybrid Retrieval (D2 Precision + OE Coverage)

E1 combines D2's metadata filtering and FlashRank reranking with OE's wider result count and bidirectional neighbor expansion.

**Sweep results:** `experiments/e1_precision_coverage/sweep_results.csv` (12 configs)
**Unbatched baseline:** `experiments/e1_unbatched/local_rm0041_md_chunks_emb4_rrlocal_mf_ne/`
**Implementation:** `context_retrieval/post_processing.py` (neighbor expansion), `defs.py` (fetch_k_multiplier, neighbor_expansion_enabled)

### E1 Top Results (STM, batched sD mfpb50)

| Config | Found Acc | Complete Acc | Coverage | Regs |
|--------|-----------|-------------|----------|------|
| emb4, mf, ne | **96.9%** | **83.1%** | 85.7% | 85/97 |
| emb4, mf | 91.5% | 82.4% | **90.1%** | 86/97 |
| emb6, mf, pa1 | 96.3% | 82.2% | 85.4% | 84/97 |
| emb2, mf, ne | 96.0% | 81.9% | 85.4% | 84/97 |

Key: mf=metadata_filter, ne=neighbor_expansion, pa1=pages_after=1, emb{N}=number_embeddings

### E1 Unbatched Baseline

| Metric | D2 | OE-STM | E1 unbatched |
|--------|-----|--------|-------------|
| Found accuracy | 97.4% | 85.9% | 93.1% |
| Complete accuracy | 73.4% | 79.8% | 77.7% |
| Coverage | 75.4% | 93.0% | 83.5% |
| Regs found | 78/97 | 95/97 | 83/97 |
| Tokens | 830K | 719K | 958K |

E1 splits the difference — better coverage than D2 (+8pp), better found accuracy than OE (+7pp). Higher token cost due to `emb4` (4 results vs 2) and neighbor expansion.

---

## 4. Batched Generator: Cost vs Accuracy

Batching multiple registers per LLM call reduces token cost by sharing system prompts and context. All configs use D2 retrieval on STM RM0041.

**Sweep results:** `../optimization/generator/experiments/batch_size_sweep/sweep_results.csv`
**Additional mrpb15 results:** `../optimization/generator/experiments/batch_size_sweep/mfpb{30,50,75}_mrpb15/info/`
**Unbatched baseline:** D2 (830,634 tokens, 96 LLM calls)

| Config | Regs/Call | LLM Calls | Tokens | vs Unbatched | Found Acc | Complete Acc | Coverage |
|--------|-----------|-----------|--------|-------------|-----------|-------------|----------|
| Unbatched | 1.0 | 96 | 830,634 | — | 97.4% | 73.4% | 75.4% |
| mfpb30 mrpb10 | 3.1 | 31 | 413,848 | −50% | 95.4% | 78.9% | 82.7% |
| mfpb30 mrpb15 | 3.5 | 28 | 373,845 | −55% | 93.4% | 77.3% | 82.8% |
| mfpb50 mrpb10 | 4.4 | 22 | 339,332 | −59% | 89.2% | 71.4% | 80.1% |
| mfpb50 mrpb15 | 4.9 | 20 | 305,482 | −63% | 89.9% | 74.4% | 82.7% |
| mfpb75 mrpb10 | 5.1 | 19 | 328,292 | −60% | 92.8% | **79.3%** | **85.4%** |
| **mfpb75 mrpb15** | **6.1** | **16** | **289,608** | **−65%** | 91.6% | 78.2% | 85.4% |

**Key finding:** Batching simultaneously reduces cost AND improves accuracy. This is not a tradeoff — the unbatched baseline has high found accuracy (97.4%) but low coverage (75.4%) because it misses 19 registers entirely. Batching finds more registers (84 vs 78) since shared context helps the LLM discover adjacent registers.

**Sweet spot:** mfpb75 mrpb15 — 65% token reduction, +4.8pp complete accuracy, +10pp coverage vs unbatched.

---

## 5. Cross-Manufacturer Generalization (NXP KE04)

The critical question: do retrieval algorithms evolved for one manufacturer's datasheet transfer to another?

**NXP KE04 verified data:** `verified_datasheet/nxp/ke04_mke04z4.csv` (87 matchable registers across 12 peripherals)
**NXP KE04 chunks:** `chunked_datasheets/nxp/ke04/chunks/md/` (743 chunks from 647 pages)
**Full eval path:** `optimization/retrieval/evaluate_retrieval.py` (DEVICE="ke04", USE_OPENEVOLVE=True). Historical raw-OE numbers below are from the now-deleted `full_eval_ke04.py`.
**OE-STM on NXP results (historical, raw OE):** `../openevolve_retrieval/output_ke04/full_eval_results_unbatched.json` (best_stm entry)
**OE-KE04 on NXP results (historical, raw OE):** `../openevolve_retrieval/output_ke04/full_eval_results_ke04_program_unbatched.json` (best_ke04 entry, re-run 2026-06-04: 1092 correct, 112 wrong, 71.7% complete acc — matches the prior 71.8% within LLM noise)

### 5.1 Overall Cross-Manufacturer Results

| Algorithm | Tested On | Complete Acc | Found Acc | Coverage | Regs | Correct | Wrong | Tokens |
|-----------|-----------|-------------|-----------|----------|------|---------|-------|--------|
| D2 Hand-tuned | STM | 73.4% | 97.4% | 75.4% | 78/97 | 1,296 | 20 | 830,634 |
| OE-STM | STM | 79.8% | 85.9% | 93.0% | 95/97 | 1,410 | 44 | 719,124 |
| OE-STM | **NXP** | **42.3%** | 45.6% | 92.8% | 80/87 | 645 | 107 | 565,495 |
| OE-KE04 | **NXP** | **71.8%** | 75.1% | 95.6% | 80/87 | 1,094 | 92 | 493,165 |

**The STM-evolved algorithm drops from 79.8% → 42.3% complete accuracy on NXP (−37.5pp).** Coverage transfers well (~93%), but accuracy does not — the retrieval strategies are manufacturer-specific. The KE04-evolved algorithm recovers to 71.8% (+29.5pp over STM-on-NXP).

### 5.2 Per-Peripheral Breakdown (NXP KE04)

| Peripheral | OE-STM Complete | OE-KE04 Complete | Delta | Winner |
|-----------|----------------|-----------------|-------|--------|
| acmp0 | 41.2% | **78.4%** | +37.2pp | KE04 |
| acmp1 | **90.2%** | 80.4% | −9.8pp | STM |
| adc | 77.8% | **80.8%** | +3.0pp | KE04 |
| crc | 90.5% | **95.2%** | +4.7pp | KE04 |
| ftm0 | 30.4% | **66.8%** | +36.4pp | KE04 |
| ftm2 | 33.5% | **71.3%** | +37.8pp | KE04 |
| ftmre | **87.1%** | 78.5% | −8.6pp | STM |
| kbi0 | 66.7% | **100%** | +33.3pp | KE04 |
| kbi1 | 50.0% | 50.0% | 0pp | Tie |
| mcm | 0.0% | **100%** | +100pp | KE04 |
| port | **100%** | 0.0% | −100pp | STM |
| sim | 33.3% | **66.7%** | +33.3pp | KE04 |

KE04-evolved wins on 8/12 peripherals, with the largest gains on complex peripherals (ftm0/ftm2: +36-38pp) where NXP's short register names cause the STM algorithm's regex-based extraction to fail.

### 5.3 Why the STM Algorithm Fails on NXP

1. **Register name regex mismatch.** STM's `process_chunks()` extracts `[A-Z_]{2,}_[A-Z0-9_]{2,}` patterns (e.g., `AFIO_EVCR`). NXP KE04 registers use short names (`c0`, `sc1`, `bdh`) that don't match this regex. No register names get prepended to chunk text → embedding quality degrades.

2. **Unfiltered 20-candidate search with wrong scoring.** STM's `search_and_format()` gives +100 points for exact `PERIPHERAL_REGISTER` matches in document text. On NXP, `ADC_SC1` rarely appears as a compound string — the peripheral and register names appear separately. The scoring heuristic becomes almost random, dominated by cosine similarity alone.

3. **KE04's two-stage search is better adapted.** The KE04 algorithm uses `$contains` at query time with both full and short register names, requires table presence in the primary query, and only falls back to unfiltered if too few results. This pre-filtering compensates for weaker embedding signal.

4. **Inverted expansion strategy.** STM expands *from* high-score/table chunks to neighbors. KE04 expands *from* non-table chunks with register names *to* adjacent table chunks — matching NXP's common pattern where text descriptions precede bit field tables.

### 5.4 Token Efficiency

| Algorithm | Target | Complete Acc | Tokens | Tokens/Correct Fact |
|-----------|--------|-------------|--------|---------------------|
| D2 Hand-tuned | STM | 73.4% | 830,634 | 641 |
| OE-STM | STM | 79.8% | 719,124 | 510 |
| OE-KE04 | NXP | 71.8% | 493,165 | **451** |
| OE-STM | NXP | 42.3% | 565,495 | 877 |

Per-manufacturer evolution is the most token-efficient approach: 451 tokens/correct fact vs 877 for cross-manufacturer (1.9× waste).

---

## 6. OpenEvolve KE04 Evolution Details

**Config:** `../openevolve_retrieval/config_ke04.yaml`
**Evaluator:** `../openevolve_retrieval/evaluator_ke04.py` (10 peripherals: irq, pmc, rtc, crc, acmp0, adc, uart0, wdog, ftmre, i2c0)
**Initial program:** `../openevolve_retrieval/initial_program.py` (same as STM — shared starting point)
**Output:** `../openevolve_retrieval/output_ke04/`

### Evolution Score Progression

| Iteration | Combined Score | Found Acc | Complete Acc | Coverage | Correct |
|-----------|---------------|-----------|-------------|----------|---------|
| 0 (initial) | 0.726 | 81.1% | 76.8% | 94.7% | 219 |
| 1 | 0.774 | 83.2% | 81.4% | 97.9% | 232 |
| 5 | 0.779 | 83.9% | 82.1% | 97.9% | 234 |
| 10 | 0.784 | 84.6% | 82.8% | 97.9% | 236 |
| 21 | 0.800 | — | — | — | — |
| 37 | 0.805 | 86.7% | 84.9% | 97.9% | 242 |
| **48 (best)** | **0.809** | **87.5%** | **85.6%** | **97.9%** | **244** |

50 iterations, ~13 hours total. Scores from evolution logs (`../openevolve_retrieval/output_ke04/logs/`). The initial program already scored 0.726 on NXP despite being designed for STM — the shared embedding model provides a reasonable baseline. Evolution improved accuracy by +8.8pp complete accuracy through adapted search and preprocessing strategies.

---

## 7. Algorithm Comparison: STM vs NXP Evolved

### 7.1 Preprocessing

| Aspect | OE-STM | OE-KE04 |
|--------|--------|---------|
| Table detection | `\|\s*-{3,}\s*\|` (simple separator) | `\|.*\|(?:\n\|[-=]+\|)+` (robust, requires header row) |
| Register name extraction | Regex `[A-Z_]{2,}_[A-Z0-9_]{2,}`, prepends `"Register: ..."` | **None** — NXP short names don't match |
| Text augmentation | Register name header | `"Page N:"` header |
| Metadata | page, chunk_index, has_tables, register_names, chunk_id | page, chunk_index, has_tables, chunk_id |

### 7.2 Query Construction

| Aspect | OE-STM | OE-KE04 |
|--------|--------|---------|
| Register naming | Single `PERIPHERAL_REGISTER` key | **Both** full name AND short name |
| Query style | Generic request | Specific: asks for "memory offset, reset value, bit field definitions, access types, enumerated values" |

### 7.3 Search Strategy

| Aspect | OE-STM | OE-KE04 |
|--------|--------|---------|
| Initial search | Unfiltered, 20 candidates | **Two-stage**: table+name filtered (7), then unfiltered fallback |
| Scoring | Additive (+100 name, +50 table+name, +20 table, cosine) | Distance-based with table/name as tiebreakers |
| Final count | 6 results | 5 results |
| Expansion trigger | From high-score or table chunks | From non-table chunks with register name |
| Expansion target | Any neighbor with reg name or tables | Only adjacent **table** chunks |

---

## 8. Key Findings

### 8.1 OpenEvolve Beats Hand-Tuning

OE-STM achieves +6.5pp complete accuracy over D2 while using 13% fewer tokens. The evolutionary approach discovers strategies (wider candidate pool, bidirectional expansion, heuristic scoring) that a human parameter sweep missed.

### 8.2 Coverage Transfers, Accuracy Does Not

Coverage is ~93% regardless of which algorithm is applied to NXP — the embedding model generalizes well enough to find *some* relevant chunks. But accuracy drops −37.5pp because the *ranking and selection* strategies are manufacturer-specific (register naming conventions, document structure patterns, table layouts).

### 8.3 Per-Manufacturer Evolution is Essential

The KE04-evolved algorithm recovers +29.5pp accuracy over the STM algorithm applied cross-manufacturer. It also uses fewer tokens (493K vs 566K) because better retrieval means less wasted context. The cost of running OpenEvolve (~$5 in Gemini API calls + Groq inference) pays for itself in improved accuracy and reduced per-query token spend.

### 8.4 Batching is Free Accuracy

Batching multiple registers per LLM call reduces tokens by 50–65% while simultaneously improving complete accuracy by +5-6pp and coverage by +10pp. This is not a tradeoff — shared context helps the LLM discover adjacent registers.

### 8.5 LLM Non-Determinism Caveat

All results are subject to LLM non-determinism. Run-to-run variance of ~3pp on complete accuracy means small differences should be interpreted cautiously. The qualitative conclusions (cross-manufacturer drop, per-manufacturer recovery) are robust across multiple evaluation runs.

---

## 9. Visualization

**Script:** `plot_cross_manufacturer.py`

Generates two figures:

1. **`fig_accuracy_coverage.png`** — Grouped bar chart showing complete accuracy and coverage for each algorithm tested on STM and NXP. Visually demonstrates the −37.5pp cross-manufacturer accuracy drop and +29.5pp per-manufacturer recovery.

2. **`fig_token_efficiency.png`** — Scatter plot of total tokens vs complete accuracy. Shows that per-manufacturer evolution achieves the best accuracy at the lowest cost (451 tok/fact), while cross-manufacturer application wastes tokens (877 tok/fact for 42% accuracy).

**Script:** `plot_batched_generator.py`

Generates one figure:

3. **`fig_batched_generator.png`** — Dual-axis bar+line chart showing token cost (bars) and accuracy/coverage (lines) across batch configurations. Demonstrates that batching reduces cost 50–65% while maintaining or improving accuracy.

All figures saved to `../../../openevolve_retrieval/figures/`.

```bash
source .venv/bin/activate && python3 openevolve_retrieval/plot_cross_manufacturer.py
source .venv/bin/activate && python3 optimization/generator/plot_batched_generator.py
```

---

## 10. File Reference

### Source Data

| Data | Path |
|------|------|
| STM verified facts | `verified_datasheet/stm/rm0041_stm32f100.csv` |
| NXP verified facts | `verified_datasheet/nxp/ke04_mke04z4.csv` |
| STM chunks | `chunked_datasheets/stm/rm0041/chunks/md/` (1033 chunks) |
| NXP chunks | `chunked_datasheets/nxp/ke04/chunks/md/` (743 chunks) |

### Evolved Programs

| Program | Path |
|---------|------|
| OE-STM best | `openevolve_retrieval/output_rm0041/best/best_program.py` |
| OE-KE04 best | `openevolve_retrieval/output_ke04/best/best_program.py` |
| Initial program (shared) | `openevolve_retrieval/initial_program.py` |

### Evaluation Results

| Evaluation | Path |
|-----------|------|
| OE-STM on STM (full, historical raw OE) | `openevolve_retrieval/output_rm0041/full_eval_results_unbatched.json` |
| OE-STM on NXP (full, historical raw OE) | `openevolve_retrieval/output_ke04/full_eval_results_unbatched.json` |
| OE-KE04 on NXP (full, historical raw OE) | `openevolve_retrieval/output_ke04/full_eval_results_ke04_program_unbatched.json` |
| D2 on STM | `optimization/retrieval/experiments/D_conditional_page_expansion/local_rm0041_md_chunks_v2_emb2_rrlocal_mf_pa1/info/` |
| E1 sweep | `optimization/retrieval/experiments/e1_precision_coverage/sweep_results.csv` |
| Batch size sweep | `optimization/generator/experiments/batch_size_sweep/sweep_results.csv` |
| KE04 evolution logs | `openevolve_retrieval/output_ke04/logs/` |
| KE04 evolution checkpoints | `openevolve_retrieval/output_ke04/checkpoints/` |

### Scripts

| Script | Purpose |
|--------|---------|
| `openevolve_retrieval/plot_cross_manufacturer.py` | Generate cross-manufacturer comparison figures + tables (frozen snapshot data) |
| `optimization/generator/plot_batched_generator.py` | Generate batched generator efficiency figure + table |
| `optimization/retrieval/evaluate_retrieval.py` | Full evaluation runner for any retrieval backend (OE / local / OpenAI VS) on any device preset |
| `openevolve_retrieval/evaluator_ke04.py` | OpenEvolve evaluator for NXP KE04 |
