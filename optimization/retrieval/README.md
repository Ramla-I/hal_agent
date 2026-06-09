# Retrieval Optimization

This folder holds the **manual parameter sweep + analysis tools** for retrieval. `evaluate_retrieval.py` varies retrieval/generator parameters and reports two families of metrics per config — a low-cost retrieval-quality measurement that skips the LLM, and an end-to-end generator-output measurement that runs it. Both are defined in [What the sweep measures](#what-the-sweep-measures) below. `metrics_retrieval.py` and `diff_retrieval_embeddings.py` are also usable standalone for post-hoc analysis of existing run dirs.

The companion `openevolve_retrieval/` folder evolves the retrieval *code itself*; this folder tunes its *settings* and measures the result. It is a manual optimization of the retrieval algorithm — we identify the parameters and their ideal values by sweeping.

## Purpose

The generator (`core/s1a_generator.py`) extracts register information from a device datasheet. Before it can answer "what is the reset value of `CRC_CR`?" it has to read the right slice of the datasheet — usually a few pages of mixed prose and tables. The component that chooses that slice is the **retrieval backend** (`context_retrieval/`), which dispatches to one of:

- `keyword_search` — section/page lookup by register name
- `openai_file_search` — OpenAI vector-store semantic search
- `local_vector_db` — local ChromaDB + FastEmbed + optional FlashRank reranker (with manually discovered pre and post-processing parameters)
- `openevolve` — the evolved program in `openevolve_retrieval/`  (with llm discovered parameters)

Each backend exposes different knobs: how many embeddings to retrieve, how aggressively to expand pages around a hit, whether to rerank, whether to filter by register metadata, and so on. The space is too large to reason about analytically, so this sweep brute-forces it.

## What the sweep measures

Two independent families of metrics. They can run together or separately — retrieval-quality needs no LLM, so it's the cheap one.

### Retrieval-quality — no generator (low-cost)

Scores the retrieved chunks *directly*, with no LLM call, at a cutoff `k` (the top-`k` retrieved chunks) against the set of chunks tagged as relevant to each register. Ground truth is each chunk's `reg_{PERIPHERAL}_{REGISTER}` boolean metadata in the **relevance labels DB** (a per-device ChromaDB collection); the only input needed is `embedding_ids.jsonl` (the ranked chunk IDs retrieval returned). Computed by `metrics_retrieval.py`.

- **recall@k** — of all chunks that *are* relevant to the register, the fraction that appear in the top `k`. "Did we fetch the right material?"
- **precision@k** — of the `k` chunks retrieved, the fraction that *are* relevant. "How much of what we fetched was on-target (vs noise)?"
- **MRR** (mean reciprocal rank) — `1 / rank` of the *first* relevant chunk, averaged over queries (e.g. first relevant hit at rank 3 → 0.333). Rewards putting a relevant chunk near the top.
- **hit@k** — 1 if *any* relevant chunk is in the top `k`, else 0; averaged over queries. The most lenient signal: "did we get at least one relevant chunk at all?"

These are computed at the configured cutoffs (`RETRIEVAL_QUALITY_K_CUTOFFS`, default `[1, 5, 10]`) **and at `@set`** — `k = the retrieved-set size`, i.e. over the *entire* returned set. `@set` is the natural top cutoff: there `top-k` is the whole set, so recall/precision/hit don't depend on ordering (valid for every backend, including document-ordered OpenEvolve) and precision is undiluted — the true "of everything we fetched, how much was relevant." A configured cutoff `≥` the retrieved-set size is reported as `N/A` (superseded by `@set`), so the largest reported cutoff is always the retrieved-set size.

This family exists because generator-output accuracy (below) judges retrieval **only through downstream output** — a config that surfaces the right page in a noisier form can look like a regression when the generator is the only judge. Retrieval-quality isolates the retrieval step. (Not every backend supports it — see [Backend support](#backend-support-for-retrieval-quality-metrics).)

These are low-cost metrics, but they are not highly accurate: they rely on the metadata flag, which only means a register is *mentioned* on the page, not that the page is genuinely relevant to it.

### Generator-output accuracy — runs the generator (expensive)

Runs the generator end-to-end, then compares each extracted "fact" (an address offset, reset value, bit range, access type, etc.) against the verified datasheet CSV. A register is "found" if the generator produced any output for it.

Every fact produced by the generator is scored *correct* (matches) or *wrong* (produced but disagrees); a third class, *missing*, is a fact in the verified datasheet the generator never produced.

The verified datasheet is a hand-checked ground-truth CSV under `verified_datasheet/<mfr>/<device>/` (e.g. `verified_datasheet/stm/rm0041/rm0041_stm32f100_full.csv`). Each row is one fact keyed by `(peripheral, register, field_name, key)` — `key` names the kind of fact (`address_offset`, `reset_value`, `size`, `bit_offset`, `bit_width`, access type, …) and `field_name` is blank for register-level facts. The `correct_value` column is what each generated fact is graded against; `svd_value` and `agent_value` are kept alongside for provenance (the value pulled from the SVD file and the generator's own value).

The metrics computed by `optimization/common/sweep_harness.run_comparison` are:

- **found accuracy** — `correct / (correct + wrong + missing)`, over only the registers the generator *found*. Fact-level quality given it attempted the register; ignores skipped ones. The assumption is that since it found some facts for the register, it was given the context to find all the facts so it is relevant that some facts per register are missing.
- **coverage** — fraction of facts found by the generator (`total_facts_found / total_facts_all`). How much of the ground truth was in scope at all.
- **complete accuracy** — `correct / total_facts_all`, over *every* verified fact. The honest end-to-end number. Unlike found accuracy, the facts about registers never found are included in the denominator.

High found accuracy + low coverage means "accurate on the few registers it tackled, but it missed many." Token usage and wall time are also recorded, but this sweep is accuracy-leaning; for an efficiency-leaning sweep at fixed accuracy see `optimization/generator/`.

## How the sweep works

`evaluate_retrieval.py` is the entry point. The script itself has no CLI flags — it's configured by editing constants at the top of `main()`, because every sweep run is meant to be a self-documenting experiment whose config lives in source. (The analysis helpers, `metrics_retrieval.py`, `diff_retrieval_embeddings.py`, and `metrics_generator_output.py`, *do* expose CLIs for ad-hoc use.)

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

## Layout

```
optimization/retrieval/
├── README.md                     # this file
├── evaluate_retrieval.py         # the sweep entrypoint — runs configs, writes both metric families
├── smoke_test.py                 # CRC smoke test (3 regs, end-to-end)
├── metrics_generator_output.py   # found/coverage/complete accuracy from comparison_results.json + plots
├── metrics_retrieval.py          # recall@k / precision@k / MRR / hit@k per run, from embedding_ids.jsonl
├── diff_retrieval_embeddings.py  # pairwise diff of two runs' retrieved chunk IDs (explains *why* one won)
├── reports/                      # written-up analyses (markdown)
└── experiments/                  # gitignored — sweep outputs land here
```

The `experiments/` tree is **gitignored**. Each leaf directory is one config's run (generator outputs + `info/`), and each `experiments/<sweep_name>/` contains a `sweep_results.csv` summarizing its children.

## Running the sweep

```bash
source .venv/bin/activate
python3 optimization/retrieval/evaluate_retrieval.py
```

You will not pass flags. Open `evaluate_retrieval.py`, edit the variables inside `main()` to describe the experiment, and run. The constants are grouped — see "Current default settings" below.

### Smoke test (no LLM-heavy sweep)

```bash
source .venv/bin/activate
python3 optimization/retrieval/smoke_test.py
```

Runs three checks on CRC (3 registers, Groq `gpt-oss-120b`) for the STM RM0041, each asserting its result schema:

- `test_smoke` — local-ChromaDB backend, full path (retrieve → LLM → comparison + retrieval-quality).
- `test_smoke_retrieval_only` — local backend, `RUN_GENERATOR=False`: no LLM, but `embedding_ids.jsonl` + retrieval-quality still produced.
- `test_smoke_openevolve` — OpenEvolve backend end-to-end; checks the program-path adapter and that OE rows carry `document_order` rank_meaning (MRR nulled).

Skips cleanly if `GROQ_API_KEY`, the verified CSV, the local DB, or (for the OE test) the evolved program / chunks index are missing. Useful as a post-refactor sanity check.

## Current default settings

These are the values currently committed in `evaluate_retrieval.py:main()`. To rerun the most recent experiment as-is, just execute the script.

**Target** — `DEVICE` selects an entry from `DEVICE_PRESETS` (module scope), which supplies the SVD name, peripheral list, local chunk index, and the relevance labels DB together. Switch device by changing the single `DEVICE` line.


| Setting              | Value                                                                  |
| -------------------- | ---------------------------------------------------------------------- |
| `DEVICE`             | `"rm0041"` (also available: `"ke04"`)                                  |
| `SVD`                | `stm32f100` (from the `rm0041` preset)                                 |
| `PERIPHERALS_TO_RUN` | `afio, bkp, cec, crc, dac, exti, flash, fsmc, iwdg, pwr, rcc` (preset) |
| `REGISTERS`          | `None` → all verified-CSV registers per peripheral                     |


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
| OpenEvolve          | `USE_OPENEVOLVE`          | **`True`** — the only backend in the current default run |


**OpenEvolve config (active)**


| Setting             | Value                                                                              |
| ------------------- | ---------------------------------------------------------------------------------- |
| `OE_PROGRAM_PATH`   | `None` → auto-derives `openevolve_retrieval/output_<DEVICE>/best/best_program.py`  |
| `number_embeddings` | `6` (handled internally by the evolved program)                                    |
| Output dir          | `optimization/retrieval/experiments/oe_batched/openevolve_<device>_batched_mfpb50` |


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
| `RELEVANCE_LABELS_DB_NAME`        | `rm0041_md_chunks` | ChromaDB collection whose `reg_{PERIPHERAL}_{REGISTER}` flags are the relevance labels. This is the *labels* DB, not necessarily the DB the backend retrieves from.              |
| `RETRIEVAL_QUALITY_K_CUTOFFS`     | `[1, 5, 10]`       | k values at which to compute recall@k / precision@k / hit@k.                                                                                                                      |


### Switching device

Change the single `DEVICE` line in `main()` to another key in `DEVICE_PRESETS` (currently `"rm0041"` or `"ke04"`). Everything device-specific — SVD, peripheral list, local chunk index, relevance labels DB, and the auto-derived OpenEvolve program path — follows from the preset. To add a device, add a `DEVICE_PRESETS` entry (and ingest its relevance labels DB / evolve its program first).

### Switching to a local-DB sweep

Flip `USE_OPENEVOLVE = False` and `USE_LOCAL_VECTOR_DB = True`. The default local-DB values above reproduce the "E1 batched" winner (`emb4 + neighbor expansion + metadata filter + local reranker`). To sweep alternatives, widen any of the `LOCAL_*` lists.

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

`sweep_results.csv` is the leaderboard. `metrics_generator_output.py` plots and filters it; `diff_retrieval_embeddings.py` diffs two configs' chunk IDs to explain *why* one beat the other. For written-up analyses see `reports/`.

### Standalone retrieval-quality measurement (post-hoc / ad-hoc)

The sweep already computes retrieval-quality metrics inline when `RUN_RETRIEVAL_METRICS=True`. If you want to (re-)measure historical run dirs that predate this feature, run `metrics_retrieval.py` directly:

```bash
source .venv/bin/activate
python3 optimization/retrieval/metrics_retrieval.py \
    optimization/retrieval/experiments/<sweep_name>/<config_prefix> \
    [<config_prefix_2> ...] \
    [--db-name ke04_md_chunks] \
    [--k 1 5 10]
```

`--db-name` defaults to `rm0041_md_chunks`; pass the matching relevance labels DB for other devices (e.g. `ke04_md_chunks`). Writes `info/retrieval_quality.json` inside each run dir and, if multiple runs are passed, a `retrieval_quality_summary.csv` at their common parent. Uses each chunk's `reg_{PERIPHERAL}_{REGISTER}` metadata as ground truth — no LLM calls. Skips queries whose register has no matching `reg_*` label in the labels DB (i.e., the ingestion step didn't tag any chunk for that register); these unmeasurable queries are also a useful chunker-side audit signal.

### Where retrieval and labels come from (per backend)

Retrieval-quality scoring has two corpora in play: the **retrieval index** each backend pulls chunks from, and the **relevance labels DB** that supplies the `reg_*` ground truth. Scoring is by chunk-`source` set membership (`recall@k = |retrieved_ids[:k] ∩ relevant_ids| / |relevant_ids|`), so the numbers are only meaningful when the retrieved chunk IDs live in the same ID space the labels are keyed on. The `reg_X=True` flag is a property of a chunk's *source content* — which register names appear in it — so it travels with the chunk's identity, not with whichever database stores it. Here is where each backend stands:

- **`local_vector_db`** — retrieves from, and is labeled by, the *same* collection: the per-device local ChromaDB (`rm0041_md_chunks` / `ke04_md_chunks`). The `reg_*` flags were written onto these exact chunks at ingestion, so the retrieval source and the labels source are literally identical. All metrics are exact.
- **`openevolve`** — builds its *own* ephemeral, in-memory ChromaDB at runtime, but from the *same source files* as the labels DB: both load `chunked_datasheets/<device>/chunks/md/*.txt` via the same `chunks_index.csv`, with the same `chunk_id` stems. The evolvable `process_chunks` in both current best programs is 1:1 and ID-preserving (it only prepends a header to each chunk's *embedding text*), so the retrieved chunk IDs map straight back to the labels DB and the `reg_*` flags still apply — scoring is valid. **But this is an invariant, not a guarantee.** OpenEvolve is explicitly allowed to merge, split, filter, or rename chunks in `process_chunks`; if a future evolved program does, the emitted IDs can fall outside the labels corpus and recall@k / hit@k will silently undercount. The divergence guard below exists to catch exactly that.
- **`openai_file_search`** — retrieves from an OpenAI vector store (per device, in `vector_stores.json`), a completely separate store from the labels ChromaDB, and doesn't emit chunk IDs that cross-reference the labels DB. It is not scored at all (skipped). `keyword_search` is page/section lookup rather than a vector DB and writes no `embedding_ids.jsonl`, so it is likewise not scored.

**Divergence guard.** Because the OpenEvolve invariant is not enforced anywhere, `measure_run` takes the labels DB's full chunk-source universe (`load_db_labels`'s third return value, `all_sources`) and counts any retrieved `source` that isn't in it. The count is written to `retrieval_quality.json` under `unknown_chunk_sources` and printed as a stderr warning. Zero is the healthy state (verified for both current best programs); a nonzero count means the retrieval index and the labels corpus have drifted apart, and the set-membership metrics for that run are undercounting.

### Backend support for retrieval-quality metrics


| Backend              | Supported? | Caveats                                                                                                                                                                                                                                                                                                                           |
| -------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `local_vector_db`    | yes        | Rank reflects retrieval relevance; all metrics meaningful.                                                                                                                                                                                                                                                                        |
| `openevolve`         | yes        | The evolved program sorts its output by page number before returning, so each chunk record's `rank_meaning` is `"document_order"`. **`MRR` is always nulled** (it depends on the first-relevant rank), and **fixed-cutoff `precision@k` is nulled for `k < n_retrieved`** (page order decides which chunks fall in `top-k`). The **`@set` metrics are all valid** — at `k = n_retrieved` the cutoff spans the whole returned set, so `recall@set` / `precision@set` / `hit@set` are order-independent (this is the meaningful precision for OE). `recall@k` / `hit@k` at fixed cutoffs are reported as set-membership signals (for `k < n_retrieved` they carry the same document-order caveat). |
| `openai_file_search` | no         | Doesn't emit chunk_ids that can be cross-referenced against the labels DB; skipped with `FileNotFoundError` swallowed silently.                                                                                                                                                                                                   |
| `keyword_search`     | no         | Doesn't write `embedding_ids.jsonl`; skipped.                                                                                                                                                                                                                                                                                     |


