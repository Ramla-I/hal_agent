# Retrieval Optimization

This folder holds the **manual parameter sweep + analysis tools** for retrieval.
`run_sweep.py` varies retrieval/generator parameters and reports both generator-output accuracy and direct retrieval-quality metrics (recall@k, precision@k, MRR, hit@k from retrieval literature — see `metrics_retrieval.py`) per config. `metrics_retrieval.py` and
`diff_retrieval_embeddings.py` are also usable standalone for post-hoc analysis of
existing run dirs.

The companion `openevolve_retrieval/` folder evolves the retrieval *code
itself*; this folder tunes its *settings* and measures the result.

## Purpose

The generator (`core/s1a_generator.py`) extracts register information from a
device datasheet. Before it can answer "what is the reset value of `CRC_CR`?"
it has to read the right slice of the datasheet — usually a few pages of mixed
prose and tables. The component that chooses that slice is the **retrieval
backend** (`context_retrieval/`), which dispatches to one of:

- `keyword_search` — section/page lookup by register name
- `openai_file_search` — OpenAI vector-store semantic search
- `local_vector_db` — local ChromaDB + FastEmbed + optional FlashRank reranker
- `openevolve` — the evolved program in `openevolve_retrieval/`

Each backend exposes knobs: how many embeddings to retrieve, how aggressively
to expand pages around a hit, whether to rerank, whether to filter by register
metadata, and so on. The space is too large to reason about analytically, so
this sweep brute-forces it.

## How the sweep works

`run_sweep.py` is the entry point. The script itself has no CLI flags — it's
configured by editing constants at the top of `main()`, because every sweep
run is meant to be a self-documenting experiment whose config lives in
source. (The analysis helpers, `metrics_retrieval.py`, `diff_retrieval_embeddings.py`,
and `metrics_generator_output.py`, *do* expose CLIs for ad-hoc use.)

The flow per configuration is:

1. **Build `ContextRetrievalParameters`** from the swept variables (`number_embeddings`, `pages_after`, `reranker_type`, `metadata_filter_enabled`, `neighbor_expansion_enabled`, etc.).
2. **Run the generator** (`run_generator_batched` by default) against the configured peripherals/registers. Each register hit calls retrieval → assembles context → calls the LLM → writes a JSON file under the run's output directory. Skipped if `RUN_GENERATOR=False` (retrieval still runs and `embedding_ids.jsonl` is still written).
3. **Compare against the verified datasheet** via `optimization/common/sweep_harness.run_comparison`: load the verified CSV (`verified_datasheet/<mfr>/<device>/<device>_<svd>_full.csv`), extract facts from each generator output, score correct / wrong / missing per `(peripheral, register, field, key)`. Skipped when `RUN_GENERATOR=False` or `SKIP_COMPARISON=True`.
4. **Compute retrieval-quality metrics** via `metrics_retrieval.measure_run`: for each `(peripheral, register)` query in `embedding_ids.jsonl`, score the retrieved chunks against the labels DB's `reg_`* ground truth → recall@k, precision@k, MRR, hit@k. Skipped when `RUN_RETRIEVAL_METRICS=False`.
5. **Write per-run artifacts** in `<output_dir>/info/`:
  - `comparison_results.json` — aggregated generator-output metrics (only if generator ran + comparison ran)
  - `comparison_register_results.csv` — one row per register (same gating)
  - `comparison_fact_errors.csv` — one row per wrong/missing fact (same gating)
  - `embedding_ids.jsonl` — the ranked chunk IDs returned per query (used by `diff_retrieval_embeddings.py` and `metrics_retrieval.py`)
  - `retrieval_quality.json` — per-query / per-peripheral / overall retrieval-quality metrics (only if `RUN_RETRIEVAL_METRICS=True` and labels loaded successfully)
  - `usage.csv`, `timing_stats.json` — token usage and wall-clock breakdown
6. **Aggregate across configurations** into `sweep_results.csv` at the output-parent root, one row per config. Both generator-output columns (`found_accuracy`, `coverage`, `complete_accuracy`) and retrieval-quality columns (`retrieval_quality_recall@k`, `retrieval_quality_mrr`, etc.) appear side by side; cells are empty for whichever side didn't run.

### What the sweep measures

Three accuracy axes — all computed from the verified CSV:


| Metric              | Definition                                                                                                                                                            |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `found_accuracy`    | `correct / (correct + wrong + missing)` over facts belonging to registers the generator actually produced output for. Measures quality given the generator showed up. |
| `coverage`          | `total_facts_found / total_facts_all`. Measures how much of the verified ground truth was in scope at all (i.e., the generator wrote a JSON file for that register).  |
| `complete_accuracy` | `correct / total_facts_all`. End-to-end metric — facts the generator got right out of every fact in the verified CSV.                                                 |


Token usage and wall time are also recorded but the retrieval sweep is
primarily accuracy-leaning. For an efficiency-leaning sweep at fixed accuracy,
see `optimization/generator/`.

### What this sweep does *not* measure

It judges retrieval **only through downstream generator output**. A retrieval
config that surfaces the right page but in a noisier form can look like a
regression because the generator is the only judge.

For a direct retrieval-quality measurement that doesn't run the generator,
`run_sweep.py` invokes `metrics_retrieval.py` per config and joins the
results into `sweep_results.csv`. The metric uses each chunk's
`reg_{PERIPHERAL}_{REGISTER}` boolean metadata as ground truth. See the
"Comparison & retrieval metrics" section for the toggles and the
"Backend support" notes at the bottom for caveats per backend.

## Layout

```
optimization/retrieval/
├── README.md                       # this file
├── run_sweep.py                    # the sweep entrypoint
├── smoke_test.py                   # CRC smoke test (3 regs, end-to-end)
├── metrics_generator_output.py     # accuracy/coverage/complete_acc from comparison_results.json + plots
├── diff_retrieval_embeddings.py               # pairwise diff of two runs' retrieved chunk IDs
├── metrics_retrieval.py            # recall@k / precision@k / MRR / hit@k per run (no generator)
├── reports/                        # written-up analyses (markdown)
├── experiments/                    # gitignored — sweep outputs land here
└── __pycache__/
```

The `experiments/` tree is **gitignored**. Each leaf directory is one
config's run (generator outputs + `info/`), and each `experiments/<sweep_name>/`
contains a `sweep_results.csv` summarizing its children.

## Running the sweep

```bash
source .venv/bin/activate
python3 optimization/retrieval/run_sweep.py
```

You will not pass flags. Open `run_sweep.py`, edit the variables inside
`main()` to describe the experiment, and run. The constants are grouped — see
"Current default settings" below.

### Smoke test (no LLM-heavy sweep)

```bash
source .venv/bin/activate
python3 optimization/retrieval/smoke_test.py
```

Runs one local-ChromaDB config on CRC (3 registers, Groq `gpt-oss-120b`),
hits `run_comparison`, and asserts the result schema. Skips cleanly if
`GROQ_API_KEY`, the verified CSV, or the local DB are missing. Useful as a
post-refactor sanity check.

## Current default settings

These are the values currently committed in `run_sweep.py:main()`. To rerun
the most recent experiment as-is, just execute the script.

**Target**


| Setting              | Value                                                         |
| -------------------- | ------------------------------------------------------------- |
| `DEVICE_NAME`        | from `config.DEVICE_NAME` (`rm0041`)                          |
| `SVD`                | from `config.SVD` (`stm32f100`)                               |
| `PERIPHERALS_TO_RUN` | `afio, bkp, cec, crc, dac, exti, flash, fsmc, iwdg, pwr, rcc` |
| `REGISTERS`          | `None` → all verified-CSV registers per peripheral            |


**Generator**


| Setting                 | Value                                               |
| ----------------------- | --------------------------------------------------- |
| `CLIENT`                | `groq`                                              |
| `MODEL_NAME`            | from `config.GENERATOR_MODEL_NAME` (`gpt-oss-120b`) |
| `USE_BATCHED_GENERATOR` | `True`                                              |
| `MAX_FIELDS_PER_BATCH`  | `50`                                                |
| `BATCHED_STRATEGIES`    | `[PER_REGISTER_TRIMMED]` (label `sD`)               |


**Backends enabled**


| Backend             | Flag                      | State                                                    |
| ------------------- | ------------------------- | -------------------------------------------------------- |
| OpenAI vector store | `USE_OPENAI_VECTOR_STORE` | `False`                                                  |
| Local ChromaDB      | `USE_LOCAL_VECTOR_DB`     | `False` (already have E1 batched results)                |
| OpenEvolve          | `USE_OPENEVOLVE`          | `**True`** — the only backend in the current default run |


**OpenEvolve config (active)**


| Setting             | Value                                                                     |
| ------------------- | ------------------------------------------------------------------------- |
| `number_embeddings` | `6` (handled internally by the evolved program)                           |
| Output dir          | `optimization/retrieval/experiments/oe_batched/openevolve_batched_mfpb50` |


**Local-DB config (gated off, but the swept values are kept for reproducibility)**


| Setting                    | Value                                                 |
| -------------------------- | ----------------------------------------------------- |
| `LOCAL_DB_NAMES`           | `["rm0041_md_chunks"]`                                |
| `LOCAL_EMBEDDING_COUNTS`   | `[4]`                                                 |
| `RERANKER_TYPES`           | `["local"]` (FlashRank `ms-marco-MiniLM-L-12-v2`)     |
| `LOCAL_METADATA_FILTER`    | `[True]`                                              |
| `LOCAL_PAGES_AFTER`        | `[0]`                                                 |
| `LOCAL_FETCH_K_MULTIPLIER` | `[5]`                                                 |
| `LOCAL_NEIGHBOR_EXPANSION` | `[True]`                                              |
| `LOCAL_OUTPUT_PARENT`      | `optimization/retrieval/experiments/e1_vs_oe_batched` |


**Comparison & retrieval metrics**


| Setting                           | Value              | Effect                                                                                                                                                                            |
| --------------------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RUN_GENERATOR`                   | `True`             | False → skip LLM call entirely; retrieval still runs and `embedding_ids.jsonl` is still written. Useful for cheap retrieval-only sweeps that pair with retrieval-quality metrics. |
| `SKIP_COMPARISON`                 | `False`            | True → skip generator-output comparison against the verified datasheet. Has no effect when `RUN_GENERATOR=False` (comparison is also skipped then).                               |
| `VERIFIED_CSV_OVERRIDE`           | `None`             | Path override; `None` auto-resolves via `get_verified_csv_path`.                                                                                                                  |
| `RUN_RETRIEVAL_METRICS`           | `True`             | Compute recall@k / precision@k / MRR / hit@k per config and join into `sweep_results.csv`. Independent of `RUN_GENERATOR` — works in both modes.                                  |
| `RETRIEVAL_QUALITY_LABEL_DB_NAME` | `rm0041_md_chunks` | ChromaDB collection providing the `reg_{PERIPHERAL}_{REGISTER}` ground-truth labels. This is the *labels* DB, not necessarily the retrieval DB.                                   |
| `RETRIEVAL_QUALITY_K_CUTOFFS`     | `[1, 5, 10]`       | k values at which to compute recall@k / precision@k / hit@k.                                                                                                                      |


### Switching to a local-DB sweep

Flip `USE_OPENEVOLVE = False` and `USE_LOCAL_VECTOR_DB = True`. The default
local-DB values above reproduce the "E1 batched" winner (`emb4 + neighbor expansion + metadata filter + local reranker`). To sweep alternatives, widen
any of the `LOCAL_`* lists.

### Reading the output

After the sweep finishes:

```
optimization/retrieval/experiments/<sweep_name>/
├── sweep_results.csv                       # one row per config (joined: generator + retrieval-quality columns)
└── <config_prefix>/
    └── info/
        ├── comparison_results.json         # only if generator ran + compared
        ├── comparison_register_results.csv # same gating
        ├── comparison_fact_errors.csv      # same gating
        ├── embedding_ids.jsonl             # always (retrieval-side log)
        ├── retrieval_quality.json          # only if RUN_RETRIEVAL_METRICS=True
        ├── usage.csv
        └── timing_stats.json
```

`sweep_results.csv` is the leaderboard. `metrics_generator_output.py` plots
and filters it; `diff_retrieval_embeddings.py` diffs two configs' chunk IDs to explain
*why* one beat the other. For written-up analyses see `reports/`.

### Standalone retrieval-quality measurement (post-hoc / ad-hoc)

The sweep already computes retrieval-quality metrics inline when
`RUN_RETRIEVAL_METRICS=True`. If you want to (re-)measure historical run
dirs that predate this feature, run `metrics_retrieval.py` directly:

```bash
source .venv/bin/activate
python3 optimization/retrieval/metrics_retrieval.py \
    optimization/retrieval/experiments/<sweep_name>/<config_prefix> \
    [<config_prefix_2> ...] \
    [--k 1 5 10]
```

Writes `info/retrieval_quality.json` inside each run dir and, if multiple
runs are passed, a `retrieval_quality_summary.csv` at their common parent.
Uses each chunk's `reg_{PERIPHERAL}_{REGISTER}` metadata as ground truth —
no LLM calls. Skips queries whose register has no matching `reg_*` label in
the labels DB (i.e., the ingestion step didn't tag any chunk for that
register); these unmeasurable queries are also a useful chunker-side audit
signal.

### Backend support for retrieval-quality metrics


| Backend              | Supported? | Caveats                                                                                                                                                                                                                                                                                                                           |
| -------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `local_vector_db`    | yes        | Rank reflects retrieval relevance; all metrics meaningful.                                                                                                                                                                                                                                                                        |
| `openevolve`         | yes        | The evolved program sorts its output by page number before returning, so each chunk record's `rank_meaning` is `"document_order"`. `recall@k` and `hit@k` (set-membership at the cutoff) remain valid; `**MRR` and `precision@k` are nulled out** for these queries since rank-0 reflects lowest page number, not best relevance. |
| `openai_file_search` | no         | Doesn't emit chunk_ids that can be cross-referenced against the labels DB; skipped with `FileNotFoundError` swallowed silently.                                                                                                                                                                                                   |
| `keyword_search`     | no         | Doesn't write `embedding_ids.jsonl`; skipped.                                                                                                                                                                                                                                                                                     |


