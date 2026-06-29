# OPTIMIZATION VALIDATOR

Tools and results for benchmarking validator accuracy, cost, and latency across
models and batching configurations.

## DIRECTORY STRUCTURE

```
optimization_validator/
|__ README.md
|__ create_test_set.py
|__ summarize_results.py
|__ plot_experiment_scatter.py
|__ plot_experiment_tradeoffs.py
|__ plot_file_search_tokens_vs_chunks.py
|__ run_all_plots.py
|__ validator_optimization.py
|__ stm-rm0041/
    |__ test_set_rm0041.csv
    |__ hold_set_rm0041.csv
    |__ hold_set_results/
        |__ <model>/
            |__ validator_accuracy_*.csv
            |__ validator_output_*.csv
            |__ validator_reasoning_*.txt
            |__ validator_usage_*.csv
        |__ summary.md
        |__ summary_accuracy.csv
        |__ summary_usage.csv
    |__ experiments/
        |__ <experiment_name>/
            |__ <model_run>/
                |__ validator_accuracy_*.csv
                |__ validator_output_*.csv
                |__ validator_reasoning_*.txt
                |__ validator_usage_*.csv
            |__ validator_batch_info_*.csv
                |__ timing_stats.json
            |__ summary.md
            |__ summary_accuracy.csv
            |__ summary_usage.csv
            |__ summary_timing.csv
        |__ time_vs_f1_scatter.png
        |__ time_vs_tokens_f1_filtered.png
        |__ f1_vs_tokens_time_filtered.png
        |__ time_breakdown_bars.png
        |__ token_breakdown_bars.png
        |__ file_search_tokens_vs_chunks.png
```

## SCRIPTS

### `VALIDATOR_OPTIMIZATION.PY`
Runs the validator against a test or hold set with configurable batching and
embedding counts, then writes per-run outputs.

Outputs per model/run folder:
- `validator_accuracy_*.csv`: accuracy metrics (TP/FP/TN/FN, accuracy, precision, recall, F1)
- `validator_output_*.csv`: per-invariant validator decisions
- `validator_reasoning_*.txt`: raw model reasoning text
- `validator_usage_*.csv`: per-call token usage
- `validator_batch_info_*.csv`: per-batch metadata (batch size, context limits)
- `timing_stats.json`: aggregated timing stats from `utils/timing.py`

### `SUMMARIZE_RESULTS.PY`
Aggregates per-run results into a single summary in an experiment directory.
Produces:
- `summary.md`: markdown tables for accuracy, usage/costs, and timing
- `summary_accuracy.csv`
- `summary_usage.csv`
- `summary_timing.csv`

### `CREATE_TEST_SET.PY`
Builds synthetic test sets by perturbing a verified CSV with **realistic** incorrect
values and/or field names (see `corruption.py`). Useful for controlled accuracy
testing. Rows with an empty `correct_value` are dropped (never human-confirmed).

## VALIDATOR CROSS-VALIDATION (paper §"Benchmarking the Validator as a Noisy Labeler")

Benchmark the Validator as a noisy binary labeler with k-fold cross-validation at
(Peripheral, Register) granularity, then calibrate downstream measurements. The
authoritative spec + full results + divergence log live in
`docs/validator_paper_plan.md`; this is the operational summary.

### Current design (pipeline)

1. **Build benchmark** (`kfold.py`): load verified CSV, then —
   - **Expand `derivedFrom` peripherals** (`expand_derived_rows`, default on, mirrors
     `verified_datasheet/expand_derived.py`): materialize the prototype's register/field
     rows under every peripheral that derives from it (e.g. `gpiob..g` from `gpioa`), so
     the benchmark covers **all** peripherals, not just the annotated prototypes. Runs
     *before* the status gate (the `derived_from` markers it needs are not `verified`).
     rm0041: 30 → 48 peripherals, 3,356 → 5,321 verified invariants.
   - Keep only **ground-truth rows** — `select_ground_truth` gates on `status ==
     "verified"`, dropping `not-specified` / `datasheet-ambiguous` / pending rows. An
     unannotated slice (e.g. rm0394) raises a clear error here, not opaquely in k-fold.
   - **Corrupt 30%** of invariants (replace, no true/corrupted pairs) with realistic
     per-key errors (`corruption.py`: in-range bit fields, nibble-flip/neighbour hex,
     size ∈ {8,16,32,64}, access swaps, real sibling names / one-edit typos),
     **stratified by peripheral** (default) so the negative class spans every peripheral
     proportionally rather than clustering from a global uniform draw.
   - Assign whole **(peripheral, register)** groups to k folds (correlated invariants
     never straddle train/held-out).
2. **Retrieve** (`make_retriever` in `cross_validate.py`): default backend is the
   **OpenEvolve evolved program** (`--retrieval openevolve`) — needs the device's
   `chunked_datasheets/<mfr>/<dev>/chunks/md/` + Chroma DB (copy from main repo or
   preprocess). `--retrieval openai` uses OpenAI file_search (weaker: no register
   metadata filter).
3. **Evaluate** (`evaluate_rows`): per register, **chunk invariants to ≤`--max-per-call`
   (default 12) with split-and-retry** on JSON/truncation failure — prevents a large
   register's response from overflowing the output-token limit and defaulting the whole
   register to reject. The system prompt carries a **vendor access-notation legend**
   (see below).
4. **Cross-validate + curate** (`cross_validate`): **Pass 1 (baseline)** runs the
   Validator once per invariant with the base prompt (which carries static hand-written
   **reasoning examples**) and tunes the **gate threshold** per fold on training scores.
   The Validator's mistakes are exported as **curation candidates**
   (`curation_candidates_<model>.json`). **Pass 2 (curated, optional)** — *not* automatic
   mining: a human curates those candidates **once per manufacturer**, supplying a
   **datasheet excerpt + conclusion** for the instructive ones into a per-vendor JSON;
   pass `--curated-examples <file>` and the Validator is re-run with those grounded
   examples to measure the lift. Per-fold confusion matrices aggregate → α, β, F1
   (reported baseline vs curated).
5. **Operational gate + ranked review queue** (the system this benchmark stands in for).
   The pipeline's real use is: generator candidates → Validator → whatever it gates out
   (V=0) is **dropped unseen**, and the survivors (V=1) are **ranked by confidence** for a
   human to review top-down until labour runs out. So the gate threshold is tuned for a
   **target precision** (`--objective precision --target-precision 0.95`, the default):
   the lowest threshold whose training precision clears the target, **maximising yield
   (recall)** under that constraint. (`--objective f1` restores max-F1.) Because V=0 is
   dropped, a false negative is a *permanently lost bug*, so the harness reports both the
   reviewed-pile **precision** and the kept-bug **yield/recall**, plus a **precision@k**
   curve (front-loading quality) and a **calibration/reliability** table (mean confidence
   vs empirical precision per bin → a principled review-depth stopping rule).
6. **Calibrate** (`calibration.py`): π = (r̂−(1−β))/(α+β−1) (Rogan–Gladen) and
   validated-set precision P(C=1|V=1) = α·π/r̂, with α+β>1 identifiability + clamp guards.
   ⚠️ **π is a COUNT, not a SELECTOR.** π estimates *how many* of N candidates are real
   bugs (≈ π·N) — the device-level prevalence. It does **not** tell you *which* candidates
   they are, and "review the top π% by confidence" does **not** recover them: that only
   works if the ranking is perfect. What you actually catch at a given review depth is the
   **precision@k / recall@k curve** (`precision_at_k_*.csv`), driven by ranking quality —
   not π. (π·N is a sensible *depth* to aim for — the point where precision@k = recall@k —
   but completeness there is whatever recall@(π·N) the ranking achieves, not 100%.) So:
   **ranking → the order you review; precision@k → what you catch at each depth; π → how
   many exist (a claim/budget).**
   ⚠️ Within a single run π just recovers the benchmark's known prevalence (algebraic
   identity) — it's informative only when benchmark-measured α/β are applied to a
   *different* r̂ (see TODO), and even then it's an estimate with a confidence interval.
   Operationally (gate-and-review) π/count-correction is not on
   the critical path; the gate precision + yield + ranking are the load-bearing numbers.

### Access-notation legend (vendor-extensible)

Datasheets write access with vendor codes (`rc_w0`, `rw`, …); verified data uses
canonical `read-write`/`read-only`/`write-only`. The map is a **plain data file** —
`optimization_validator/access_notations.json`, keyed by vendor — so adding a vendor is a JSON
edit, no code change. `optimization_validator/access_notation.py` builds the legend injected into
the validator system prompt (batched + sequential, so production `s4` benefits too).
Select with `--vendor <key>` (default `stm`; `none` disables).

### Name aliasing (`alt_name`)

The benchmark keys each invariant by the **SVD** name, but a datasheet often prints a
field/register under a different name (the SVD adds a disambiguating suffix: SVD `D1` is
just `D` in the datasheet). A strict validator then rejects a *correct* fact on a pure
name mismatch — a false negative. Two-part handling, toggled by `--use-alt-name`
(default on; `--no-alt-name` ablates):
1. **General aliasing rule** (production-valid): the system prompt tells the model the
   SVD name may differ from the datasheet's and to match on *structural* identity (bit
   position / address), not an exact string.
2. **Per-row hint**: the verified datasheet's `alt_name` column is surfaced to the model
   as `datasheet_name` when present.
⚠️ `alt_name` is recorded **only** in verified datasheets, so the per-row hint is a mild
*oracle* — production has it only if the generator is extended to emit the datasheet's
printed name. Ablate with `--no-alt-name` to measure the gap. Coverage is currently thin
(rm0041: 9/3,356 rows carry an `alt_name`), so most of the lift here comes from the
general rule, not the per-row hint. On a `field_name` corruption we blank `alt_name` (a
fabricated name has no datasheet alias, and keeping it would leak the real name).

### Files
- **`corruption.py`** — realistic per-key corruption + field-name corruption.
- **`kfold.py`** — corrupted benchmark + (peripheral, register) group k-fold.
- **`calibration.py`** — `ConfusionMatrix` + Rogan–Gladen `calibrate()`.
- **`cross_validate.py`** — orchestrator (retrieval dispatch, chunked inference,
  gate-threshold tuning, curated-example loading + candidate export, calibration, ranked
  review queue, usage/cost, outputs). `make_tuner`, `render`/`load_curated_examples`,
  `export_curation_candidates`, `build_review_queue` / `precision_at_k_table` /
  `reliability_table`. `MODELS` list / `--model`.
- **`curated_examples/<vendor>.json`** — human-curated, datasheet-grounded examples for
  pass 2 (created once per vendor from the exported candidates).
- **`tests/test_offline.py`** — offline unit tests (no network), incl. the operational gate.

### Run (in the project container)
```bash
scripts/docker_run.sh run -m optimization_validator.tests.test_offline                     # offline tests
scripts/docker_run.sh run -m optimization_validator.cross_validate --smoke --model gpt-oss-120b   # tiny e2e

# Pass 1 (baseline) — also exports curation_candidates_<model>.json:
scripts/docker_run.sh run -m optimization_validator.cross_validate --model gpt-5.5 --k 5 \
    --retrieval openevolve --vendor stm --objective precision --target-precision 0.95 \
    --out-root optimization_validator/stmrm0041_run --price-in <$/1M> --price-out <$/1M>

# [human] curate candidates -> optimization_validator/curated_examples/stm.json
# Pass 2 (curated) — add the grounded examples, measure the lift:
scripts/docker_run.sh run -m optimization_validator.cross_validate --model gpt-5.5 --k 5 \
    --retrieval openevolve --vendor stm --out-root optimization_validator/stmrm0041_run \
    --curated-examples optimization_validator/curated_examples/stm.json
```
Token usage is always recorded; `--price-in/--price-out` (USD per 1M tokens) add a `$` estimate.

Outputs → the `--out-root` dir, `<model|smoke>/` subfolder:
`judgments_<model>.csv` (per-row + reasoning + tau + coverage), `judgments_baseline_<model>.csv`
(when a curated pass ran), `curation_candidates_<model>.json` (FP/FN for a human to curate),
`error_analysis_<model>.csv`, `per_fold_<model>.csv`, `summary_<model>.{csv,json}` (**baseline
vs curated** + an `operational` block: gate precision, yield/recall, bugs dropped unseen,
precision@top-decile + a `usage` block: tokens + `$`), `usage_<model>.csv` (per-call tokens),
`prompts/` (base prompt + curated-examples block), and the **operational artifacts**:
`review_queue_<model>.csv` (gate survivors ranked by confidence — the reviewer-facing list),
`precision_at_k_<model>.csv` (review-top-X% → catch-Y% curve), `calibration_<model>.csv`
(confidence reliability bins).

### Results so far (rm0041, k=5; OpenEvolve + chunked batching)
> ⚠️ Measured on the **pre-merge** rm0041 slice (~2,459 verified invariants). The merged
> verified datasheet now yields **3,356** `status=verified` rows, so these numbers should
> be **re-measured** before citing.
| Model | F1 (tuned) | validated precision | raw sens. | β |
|---|---|---|---|---|
| gpt-oss-120b | 0.91 | 0.95 | 0.85 | 0.90 |
| gpt-5.5 (+ access legend) | **0.975** | 0.96 | 0.98 | 0.90 |

### EXPERIMENTS (validator paper)

Status: ⬜ not started · 🟡 partial · ✅ done · 🔒 blocked. **★ = load-bearing for a paper claim.**

**A. Headline metrics — the main result**
- [ ] **★ A1. Per-vendor tuned metrics** — full k-fold after a tuning round on a
      representative STM (rm0041, 5,321 invariants) and NXP (ke04, 1,952) → gate precision,
      yield/recall, α, β, precision@k, calibration. STM runs now; **NXP 🔒 needs a retrieval
      backend** (no OpenEvolve program for ke04 → evolve one or use `--retrieval openai`).
- [ ] **A2. Cross-model** — gpt-oss-120b vs gpt-5.5 on both, so the headline isn't
      model-specific. Runs now (STM).

**B. Ablations that justify the design**
- [ ] **B1. Curation lift (baseline vs curated)** — emitted automatically when pass 2 runs
      (`summary_*` has baseline vs curated); quantifies what the human-curated,
      datasheet-grounded examples buy. Requires a `curated_examples/<vendor>.json`.
- [ ] **B2. `alt_name` on/off** (`--use-alt-name` / `--no-alt-name`) — lift vs specificity cost.
- [ ] **B3. Access legend on/off** (`--vendor stm` / `none`) — re-measure on the merged slice.
- [ ] **B4. Retrieval backend** — OpenEvolve vs OpenAI file_search; justifies the switch.
- [ ] **B5. Number of curated examples** — vary how many curated, datasheet-grounded
      examples go in the prompt; find where added examples stop helping vs prompt-size cost.

**C. Validity of the calibration — the scientific core**
- [ ] **★ C1. Cross-distribution π test** — measure α/β at 30% corruption, apply to a slice
      at a *different* rate (e.g. 50%), check π̂ recovers ~0.50. The only experiment that
      exercises Rogan–Gladen (within-run π is an identity). Runs now.
- [ ] **★ C2. Per-vendor transfer (amortization claim)** — calibrate/freeze on device 1,
      apply to device 2 of the same vendor (rm0041→rm0090, ke04→s32k116); check precision/
      yield holds. **🔒 second-device slices not annotated yet** (longest lead time).

**D. External validation — strongest evidence, slow**
- [ ] **D1. Validator-confirmed bugs vs upstream merges** (STM) — ties internal precision to
      real external ground truth. Ongoing, not a one-shot run.

**E. Characterization — cheap, high-value**
- [ ] **E1. Per-invariant-class breakdown** — precision/recall per key (`address_offset`,
      `reset_value`, `size`, `bit_offset`, `bit_width`, `access`); motivates per-class gating.
      Mostly in `error_analysis_*.csv`, needs aggregation.
- [ ] **E2. Seed variance / CIs** — multiple corruption seeds → confidence intervals on
      α/β/precision for honest error bars.

**Prereqs before the NXP run (A1):** a retrieval backend for ke04 (evolve an OpenEvolve
program or accept `--retrieval openai`) and real NXP access notations in
`access_notations.json` (currently stubs).

### OPEN TODOS
- [ ] **Re-measure on the merged 3,356-row rm0041 slice** (see warning above) and refresh
      the results table; the prior numbers are on the smaller pre-merge slice.
- [x] **Use `alt_name` to cut name-mismatch false negatives** — done (see *Name aliasing*
      above): `--use-alt-name` adds a general structural-matching rule + a per-row
      `datasheet_name` hint. **Follow-ups:** (a) measure the ablation (`--no-alt-name`) to
      quantify the lift and the access-FP-style specificity cost; (b) `alt_name` coverage is
      thin (9 rows in rm0041) and the per-row hint is an oracle unless (c) the **generator
      emits the datasheet-printed name** in production, which would make the hint real —
      worth doing.
- [x] **Expand `derived` peripherals** — done (`expand_derived_rows`, default on): the
      benchmark now materializes `derivedFrom` peripherals (rm0041: 30 → 48 peripherals,
      3,356 → 5,321 invariants), matching what the generator actually extracts — it
      processes `gpioa`, `gpiob`, … as separate tasks, so the validator validates each in
      production. This is the representative population (no novel-family-generalization
      caveat applies for the operational per-chip precision/yield estimate).
- [ ] **Tune the number of curated examples** (see B5). Each grounded example (invariant +
      datasheet excerpt + reasoning) is ~60–120 tokens × every call, so find the smallest
      curated set that keeps the lift; drop near-duplicate / low-information examples.
- [ ] **Fill in real NXP / TI access notations** in `optimization_validator/access_notations.json`
      (currently stubs) when ke04 / msp430g2 slices are benchmarked.
- [ ] **Benchmark the held-out vendors** (NXP `ke04`, then TI) — verified slices exist;
      tests whether rm0041 numbers transfer. Needs each device's chunks/Chroma + an
      OpenEvolve program (or `--retrieval openai`).
- [ ] **Genuine calibration test for π**: measure α/β on the 30% benchmark, apply to a
      held-out slice with a *different* corruption rate (e.g. 50%), check π recovers
      ~0.50. Only this exercises the correction (within-run π is an identity).
- [ ] **Access FP tradeoff**: the legend lifts recall but accepts a few more corrupted
      access values (gpt-5.5 β 0.909→0.897). Consider a stricter legend wording or a
      specificity-aware threshold objective if precision matters more downstream.
- [ ] **Field-table retrieval misses**: gpt-oss access FN are partly fields whose
      bit-table isn't retrieved (legend can't help). Revisit retrieval granularity.
- [ ] **Second-model cost**: gpt-5.5 sweep ≈ 15 min/run; budget before broad sweeps.

### `PLOT_EXPERIMENT_SCATTER.PY`
Creates a scatter plot of total time vs F1 score, with point size proportional
to total tokens and labels including API call counts.

### `PLOT_EXPERIMENT_TRADEOFFS.PY`
Generates filtered tradeoff plots (time vs tokens, F1 vs tokens) and stacked
bar charts for time and token breakdowns. Filters are controlled by min F1 and
max time thresholds.

### `PLOT_FILE_SEARCH_TOKENS_VS_CHUNKS.PY`
Builds a bar chart comparing file search tokens per experiment against
the total_peripheral_tokens derived from the test set and mapping CSV.

### `RUN_ALL_PLOTS.PY`
Runs the scatter and tradeoff plotting scripts in one command.

## NOTES

- Experiment results are grouped under `stm-rm0041/experiments/<experiment_name>/`.
- Hold/test datasets live in `stm-rm0041/` and are referenced by the scripts.
