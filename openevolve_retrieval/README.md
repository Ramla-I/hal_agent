# OpenEvolve Retrieval Optimization

## Goal

Use [OpenEvolve](https://github.com/codelion/openevolve) — an evolutionary
code-optimization framework — to **discover** retrieval algorithms for
extracting register information from chunked datasheets, rather than
hand-tuning them. OpenEvolve mutates and recombines code inside an
`EVOLVE-BLOCK`, scores each candidate against a verified ground truth, and
keeps the best variants.

The result is plugged back into the runtime as one of the retrieval
backends. The companion folder `optimization/retrieval/` tunes the
*settings* of all four backends (including this one); this folder evolves
the *code itself* for one of them.

## Status

Two devices have been evolved separately. Both `best_program.py` files live
under their respective `output_<device>/best/` directories.


| Device     | Iter | Combined score (during evolution) | Found accuracy | Coverage           | Source                                      |
| ---------- | ---- | --------------------------------- | -------------- | ------------------ | ------------------------------------------- |
| STM RM0041 | 18   | 0.873                             | 89.8%          | 100% (66/66 regs)  | `output_rm0041/best/best_program_info.json` |
| NXP KE04   | 48   | 0.809                             | 87.5%          | 97.9% (23/24 regs) | `output_ke04/best/best_program_info.json`   |


Scores above are from each evaluator's own test set during evolution
(7 STM peripherals, 10 KE04 peripherals). Historical full evaluations
against the complete verified datasheet — produced by the now-deleted
`full_eval_*.py` scripts, which passed raw OE output to the generator
without the canonical `<sources>` XML envelope — are preserved at:

- `output_rm0041/full_eval_results_unbatched.json` — STM-evolved on STM:
95/97 registers, 1410/1642 correct facts, 85.9% found accuracy
- `output_ke04/full_eval_results_unbatched.json` — **STM-evolved tested on NXP**
(cross-manufacturer transfer): 80/87 registers, 645/1415 correct facts, 45.6% found accuracy
- `output_ke04/full_eval_results_ke04_program_unbatched.json` — **KE04-evolved
on NXP**: 80/87 registers, 1092/1524 correct facts, 71.7% complete accuracy

The cross-manufacturer drop (−29pp complete accuracy: 71.7% → 42.3%) is
the main motivation for evolving a separate KE04 program; the
per-manufacturer evolution closes the gap.

Going forward, full evaluations run through `optimization/retrieval/evaluate_retrieval.py`
with `USE_OPENEVOLVE=True` — see "Running a full evaluation" below. The new
path uses per-page XML wrapping (the canonical format every backend emits),
which scores higher on the same data (~+5pp complete accuracy vs the old raw
path) and is what the production pipeline actually delivers to the generator.

See `optimization/retrieval/reports/retrieval_evolution_report.md` for the
written-up analysis with figures (rendered to `figures/`).

## Layout

```
openevolve_retrieval/
├── README.md                       # this file
├── initial_program.py              # the EVOLVE-BLOCK template (starting point)
├── _shared_cache.py                # FastEmbed embedding cache (survives importlib reloads)
│
├── evaluator_rm0041.py             # fitness function (STM RM0041) used during evolution
├── evaluator_ke04.py               # fitness function (NXP KE04)
│
├── config_rm0041.yaml              # OpenEvolve config (STM)
├── config_ke04.yaml                # OpenEvolve config (NXP)
│
├── output_rm0041/                  # STM evolution output
│   ├── best/best_program.py        # the best evolved program
│   ├── best/best_program_info.json # its score + per-feature metrics
│   ├── checkpoints/                # intermediate evolution checkpoints
│   ├── logs/                       # per-iteration evolution logs
│   └── full_eval_results_unbatched.json  # frozen historical full-eval (raw OE → LLM)
│
├── output_ke04/                    # NXP evolution output (same shape)
│   ├── full_eval_results_unbatched.json              # frozen: best_stm on NXP
│   └── full_eval_results_ke04_program_unbatched.json # frozen: best_ke04 on NXP
│
├── plot_cross_manufacturer.py      # STM-vs-NXP comparison figures (frozen snapshot data)
└── figures/                        # PNGs produced by plot_cross_manufacturer.py
```

> Full evaluations now run through `optimization/retrieval/evaluate_retrieval.py` with
> `USE_OPENEVOLVE=True` — see "Running a full evaluation" below. The
> `full_eval_results_*_unbatched.json` files are preserved as historical
> baselines from before the consolidation.

## How it fits together

```
                     ┌──────────────────────────────────────┐
                     │ run_evolution()      (OpenEvolve)    │
                     │   reads:  initial_program.py         │
                     │           config_<device>.yaml       │
                     │   calls:  evaluator_<device>.py      │
                     │   writes: output_<device>/best/…     │
                     └──────────────┬───────────────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────────────┐
                     │  output_<device>/best/best_program.py│  ← the artifact
                     └──────────────┬───────────────────────┘
                                    │ loaded dynamically by
                                    ▼
                     ┌──────────────────────────────────────┐
                     │  context_retrieval/openevolve_search.py
                     │     (the runtime adapter — pipeline uses this)
                     └──────────────────────────────────────┘
```

Or, separately, for a post-hoc full evaluation:

```
optimization/retrieval/evaluate_retrieval.py  →  loads output_<device>/best/best_program.py
   (USE_OPENEVOLVE=True, DEVICE=...)  →  runs the generator on the preset peripheral list
                                     →  writes optimization/retrieval/experiments/oe_batched/
                                            openevolve_<device>_<mode>_mfpb<N>/info/
```

## The three pieces of an OpenEvolve run

### 1. `initial_program.py` — the EVOLVE-BLOCK template

Contains three functions inside `# EVOLVE-BLOCK-START` / `# EVOLVE-BLOCK-END`
markers that OpenEvolve is allowed to mutate:

- `**process_chunks(raw_chunks)**` — preprocesses ~1033 raw markdown chunks
before indexing. Initial version detects tables (`has_tables` metadata)
and regex-extracts register-style names like `AFIO_MAPR`.
- `**build_query(peripheral_name, register_name)**` — constructs the
semantic-search query string. Initial version is a natural-language
request mentioning offset, reset value, and field info.
- `**search_and_format(collection, query, embedding_fn, …)**` — runs the
ChromaDB query, optional reranking/expansion, returns formatted context.
Initial version retrieves 5 results with a `$contains` filter and
unfiltered fallback.

Outside the evolve block (fixed scaffolding):

- `load_raw_chunks()` reads chunks_index.csv + chunk text files
- `build_ephemeral_store()` builds an in-memory ChromaDB collection
- `setup_database()` / `run_retrieval()` are the entry points

### 2. `evaluator_rm0041.py` (and `evaluator_ke04.py`) — the fitness function

Two-stage cascade:

- **Stage 1 (fast reject):** Run on 3 representative registers. If any returns no
context, score 0 and stop.
- **Stage 2 (scoring):** Run on the full test set:
  - STM: 7 peripherals (afio, crc, exti, bkp, dac, pwr, rcc) — ~22 registers
  - NXP: 10 peripherals (irq, pmc, rtc, crc, acmp0, adc, uart0, wdog, ftmre, i2c0) — ~75 registers

Per register:

1. Retrieve context via the evolved pipeline
2. Call the generator LLM (Groq `gpt-oss-120b`)
3. Parse JSON, extract facts, compare to the verified CSV

**Scoring:** `combined_score = found_accuracy − (error_rate × 0.5)` — wrong
facts penalized more heavily than missing ones. MAP-Elites feature dimensions:
`avg_context_length` and `retrieval_time` (to keep the population diverse).

**Dependencies:**

- Generator prompts: `prompts/register_info_stm.py`
- Output parsing: `utils/parse_output.py`
- Fact extraction: `utils/generator_facts.py`
- Comparison logic: `optimization/common/compare_generator_with_verified.py`

### 3. `config_rm0041.yaml` (and `config_ke04.yaml`) — OpenEvolve settings

- **Evolution LLM:** Gemini 2.5 Flash (100% weight) via Google's OpenAI-compatible API
- **Iterations:** 50 max, diff-based evolution, 25k max code length
- **MAP-Elites:** 40 population, 15 archive, 3 islands, 70% exploitation
- **Evaluator:** 300s timeout, cascade threshold 0.1, sequential (Groq rate-limit-bound)

### Bonus: `_shared_cache.py` — embedding cache

OpenEvolve loads each evolved variant as a fresh module via `importlib`,
which means per-module caches would be lost between iterations. This module
sits in `sys.modules` for the life of the evolution run and caches
FastEmbed vectors by MD5 of the chunk text. Saves ~180s per evaluation
when chunk text hasn't changed.

## Running an evolution

```bash
# Prerequisites
export GROQ_API_KEY="..."      # generator LLM during evaluation
export GEMINI_API_KEY="..."    # OpenEvolve's evolution LLM

pip install openevolve         # if not already
source .venv/bin/activate

# STM RM0041
python -c "
from openevolve import run_evolution
result = run_evolution(
    initial_program='openevolve_retrieval/initial_program.py',
    evaluator='openevolve_retrieval/evaluator_rm0041.py',
    config='openevolve_retrieval/config_rm0041.yaml',
    output_dir='openevolve_retrieval/output_rm0041',
    cleanup=False,
)
print(f'Best score: {result.best_score}')
"

# NXP KE04 — same call, swap in the _ke04 variants
python -c "
from openevolve import run_evolution
result = run_evolution(
    initial_program='openevolve_retrieval/initial_program.py',
    evaluator='openevolve_retrieval/evaluator_ke04.py',
    config='openevolve_retrieval/config_ke04.yaml',
    output_dir='openevolve_retrieval/output_ke04',
    cleanup=False,
)
print(f'Best score: {result.best_score}')
"
```

## Running a full evaluation (post-hoc)

Once `best_program.py` exists under `output_<device>/best/`, evaluate it
against every verified peripheral via the sweep:

```bash
source .venv/bin/activate

# Edit optimization/retrieval/evaluate_retrieval.py:
#   DEVICE = "rm0041"  # or "ke04"
#   USE_OPENAI_VECTOR_STORE = False
#   USE_LOCAL_VECTOR_DB = False
#   USE_OPENEVOLVE = True
#   OE_PROGRAM_PATH = None    # auto-derives output_<DEVICE>/best/best_program.py
#                             # set explicitly to evaluate a checkpoint or cross-device program
#   USE_BATCHED_GENERATOR = True   # production default; set False to match old raw-call methodology

python3 optimization/retrieval/evaluate_retrieval.py
```

Writes per-config outputs under
`optimization/retrieval/experiments/oe_batched/openevolve_<device>_<mode>_mfpb<N>/info/`
(`comparison_results.json`, `comparison_register_results.csv`,
`comparison_fact_errors.csv`, `usage.csv`, `timing_stats.json`,
`embedding_ids.jsonl`, `retrieval_quality.json`) and a top-level
`sweep_results.csv` summarizing all configs in the run.

Useful for comparing the evolved program against hand-tuned baselines on
the same full test set — `sweep_results.csv` is one row per config
(OE/local/OpenAI all comparable side by side).

## Using the evolved program in the pipeline

The runtime side picks up the evolved program via
`context_retrieval/openevolve_search.py`, which loads it dynamically through
`importlib` and caches it per-path. The adapter wraps OE's
`run_retrieval(peripheral, register)` calls into the canonical
`<sources><result page='N' source='openevolve'>…</result></sources>` XML
format (same shape that `post_processing.format_results` produces for every
other backend) and emits `embedding_ids.jsonl` so the OE backend can be
scored by `optimization/retrieval/metrics_retrieval.py` like any other
backend.

The program path is configurable via `ContextRetrievalParameters.oe_program_path`.
`evaluate_retrieval.py` auto-derives it from `DEVICE` (→ `output_<device>/best/best_program.py`),
so swapping devices or evaluating a specific checkpoint is one flag.

## Relationship to `optimization/retrieval/`

`optimization/retrieval/` and `openevolve_retrieval/` are two orthogonal
optimization layers:

- `optimization/retrieval/evaluate_retrieval.py` varies **parameters** (number of
embeddings, reranker on/off, metadata filter, page expansion, batch
strategy, etc.) across all backends — including OpenEvolve. It tunes
knobs without touching code.
- `openevolve_retrieval/` evolves the **retrieval code itself**
(preprocessing, query construction, post-processing). The output of one
evolution run is then *consumed* as a single fixed backend by the sweep.

Both share `optimization/common/compare_generator_with_verified.py` for
fact-matching.

## Caveats

- During evolution the page-sort applied inside the evolved
`search_and_format()` means the final chunk order in the OE adapter
reflects document order, not relevance order. This is recorded in
`embedding_ids.jsonl` as `rank_meaning: "document_order"` so
`metrics_retrieval.py` nulls out MRR / precision@k for OE rows (recall@k
/ hit@k stay valid as set-membership metrics).
- The hardcoded ChromaDB metadata-key convention assumed by the labels DB
(`reg_{PERIPHERAL}_{REGISTER}` booleans) is set at ingestion time, not enforced anywhere. If you re-ingest with different rules, the runtime retrieval still works but the metric_retrieval script will silently lose its ground truth.
- Historical `full_eval_results_*_unbatched.json` files were produced by
the now-deleted `full_eval_*.py` scripts, which passed raw OE output to
the LLM without the canonical `<sources>` envelope. Numbers are ~5pp
lower on complete accuracy than the current sweep path on the same
program/device combination — the gap is the methodology change, not a
program regression. Keep the files for historical reference only.

