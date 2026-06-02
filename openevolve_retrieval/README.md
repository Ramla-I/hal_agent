# OpenEvolve Retrieval Optimization

## Goal

Use [OpenEvolve](https://github.com/codelion/openevolve) (an evolutionary code optimization framework) to automatically discover an optimal retrieval algorithm for extracting hardware register information from chunked datasheets. Instead of manually tuning retrieval parameters, OpenEvolve uses LLM-guided evolution to mutate and improve the retrieval code itself.

## Status: Run 1 Complete

**Best score: 0.9921** (iteration 29) — 570/573 facts correct, 3 wrong, 0 missing.

| Metric | Baseline (iter 0) | Best (iter 29) | Improvement |
|--------|-------------------|----------------|-------------|
| Combined score | 0.924 | 0.992 | +7.4% |
| Correct facts | 533/573 | 570/573 | +37 |
| Wrong facts | 7 | 3 | -4 |
| Missing facts | 33 | 0 | -33 |
| Accuracy | 93.0% | 99.5% | +6.5% |
| Avg context length | 8,671 chars | 12,628 chars | +46% |
| Retrieval time | 0.41s | 0.35s | -15% |

The best evolved program is saved at `output/best/best_program.py`.

### Evolution Timeline

- **Iter 0 (baseline):** 0.924 — initial program with 5-result filtered+fallback search
- **Iter 10:** 0.961 — first improvement (552 correct, 3 wrong, 18 missing)
- **Iter 25:** 0.992 — major jump (569 correct, 1 wrong, 3 missing)
- **Iter 29:** 0.992 — tied best from different lineage (570 correct, 3 wrong, 0 missing)
- **Iters 30-50:** No further improvements found

### What the Evolution Changed

The only change was in `search_and_format()`. The evolved version:

1. **Increased results from 5 to 7** (`N_RESULTS_TO_RETRIEVE = 7`)
2. **Added deduplication** — tracks `(page_number, chunk_index)` pairs to avoid duplicate chunks across queries
3. **Two-phase retrieval with conditional fallback** — runs filtered `$contains` search first, only runs unfiltered search if fewer than 7 results found (vs. always falling back)
4. **Score-based reranking** — after combining results from both queries, sorts by score (descending), takes top 7, then re-sorts by page number for coherent reading order

`process_chunks()` and `build_query()` were **not modified** — the baseline implementations were already effective.

## Architecture

OpenEvolve requires three files:

### 1. `initial_program.py` — The Evolvable Program

Contains the retrieval pipeline with three functions inside an `EVOLVE-BLOCK` that OpenEvolve will mutate:

- **`process_chunks(raw_chunks)`** — Preprocesses ~1033 raw markdown chunks before indexing. Detects tables (`has_tables` metadata), extracts register-style names (e.g. `AFIO_MAPR`), passes through chunk text unmodified.

- **`build_query(peripheral_name, register_name)`** — Constructs the semantic search query. Builds a natural language query asking for offset, reset value, size, and field information.

- **`search_and_format(collection, query, embedding_fn, ...)`** — Searches ChromaDB and returns formatted context. Tries a `$contains` filter for the register name first, falls back to unfiltered semantic search, retrieves 5 results, sorts by page number, and formats with similarity scores.

Fixed infrastructure (outside the evolve block):
- `load_raw_chunks()` — Reads chunk texts and metadata from the preprocessed chunks directory
- `build_ephemeral_store()` — Builds an in-memory ChromaDB collection from processed chunks
- `setup_database()` / `run_retrieval()` — Entry points called by the evaluator

### 2. `evaluator.py` — The Fitness Function

Scores each evolved program by running the full pipeline end-to-end:

**Cascade evaluation (two stages):**
- **Stage 1 (quick reject):** Tests 3 registers (`afio/evcr`, `crc/dr`, `exti/imr`). If no context is retrieved for any of them, the program scores 0.0 immediately.
- **Stage 2 (full evaluation):** Runs all ~22 registers across 5 peripherals (`afio`, `crc`, `exti`, `iwdg`, `pwr`).

**Per-register evaluation loop:**
1. Retrieve context using the evolved pipeline
2. Call the generator LLM (Groq `gpt-oss-120b`) with the retrieved context
3. Parse JSON output and extract facts
4. Compare facts against verified ground truth (`rm0041_stm32f100_full.csv`)

**Scoring:**
- `combined_score = accuracy - (error_rate * 0.5)` — wrong facts penalized more than missing ones
- Feature dimensions for MAP-Elites diversity: `avg_context_length` and `retrieval_time`

**Dependencies:**
- Generator prompts from `prompts/register_info_stm.py`
- Output parsing from `utils/parse_output.py`
- Fact extraction from `utils/generator_facts.py`
- Comparison logic from `optimization/retrieval/compare_generator_with_verified.py`

### 3. `config.yaml` — OpenEvolve Configuration

- **LLM for evolution:** Gemini 2.5 Flash (100% weight) via Google's OpenAI-compatible API
- **Evolution:** 50 max iterations, diff-based evolution, 25k max code length
- **MAP-Elites:** 40 population, 15 archive, 3 islands, 70% exploitation ratio
- **Evaluator:** 300s timeout, cascade threshold at 0.1, sequential evaluations (Groq rate limits)

Note: Gemini 2.5 Pro was originally configured as secondary model but hit free-tier quota limits. Flash-only worked fine.

### 4. `_shared_cache.py` — Embedding Cache

A shared module that caches embedding vectors by text MD5 hash. Since OpenEvolve loads each evolved variant as a fresh module via `importlib`, per-module caches would be lost. This module persists in `sys.modules` across evaluations, avoiding re-embedding unchanged chunk texts (~180s savings per evaluation).

## How to Run

```bash
# Prerequisites
export GROQ_API_KEY="..."      # For generator LLM calls during evaluation
export GEMINI_API_KEY="..."    # For OpenEvolve's evolution LLM

# Install OpenEvolve (if not already)
pip install openevolve

# Run from project root (Python API)
source .venv/bin/activate
python -c "
from openevolve import run_evolution
result = run_evolution(
    initial_program='openevolve_retrieval/initial_program.py',
    evaluator='openevolve_retrieval/evaluator.py',
    config='openevolve_retrieval/config.yaml',
    output_dir='openevolve_retrieval/output',
    cleanup=False,
)
print(f'Best score: {result.best_score}')
"
```

## Relationship to `optimization/retrieval/`

The `optimization/retrieval/` folder contains a **manual** parameter sweep (`run_sweep.py`) that varies `number_embeddings` and `pages_after_keyword` across fixed values. The `openevolve_retrieval/` approach is fundamentally different — it evolves the actual retrieval *code* (preprocessing, query construction, and post-processing) rather than just tuning numeric parameters. The evaluator reuses `optimization/retrieval/compare_generator_with_verified.py` for the comparison logic.

## Next Steps

1. **Integrate best program:** Extract the winning `search_and_format()` into `context_retrieval/local_vector_search.py`
2. **Validate on more peripherals:** The test set only covers 5 peripherals (afio, crc, exti, iwdg, pwr) — run on the full device
3. **Evolve preprocessing:** The current best didn't change `process_chunks()` — try runs with more aggressive initial mutations to explore that space
4. **Try with different generator models:** Results may vary with gpt-4o vs gpt-oss-120b
