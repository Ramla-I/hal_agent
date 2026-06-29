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

1. **Build benchmark** (`kfold.py`): load verified CSV and keep only **ground-truth
   rows** — `select_ground_truth` gates on `status == "verified"` (the schema from
   `verified_datasheet/annotate.py`), which in one shot drops `derived` peripheral-
   inheritance marker rows, `not-specified` / `datasheet-ambiguous` cells, and pending
   (empty-status) rows. An unannotated slice (e.g. rm0394) raises a clear error here
   rather than failing opaquely in k-fold. Then corrupt 30% of invariants (replace, no
   true/corrupted pairs) with realistic per-key errors (`corruption.py`: in-range bit
   fields, nibble-flip/neighbour hex, size ∈ {8,16,32,64}, access swaps, real sibling
   names / one-edit typos), and assign whole (peripheral, register) groups to k folds
   (correlated invariants never straddle train/held-out).
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
4. **Cross-validate** (`cross_validate` + `cross_validate_mined`): the Validator is run
   once per invariant (baseline); then per fold, **in-context examples are mined from
   that fold's training-partition FP/FN** and the held-out fold is re-evaluated with the
   augmented prompt (tuned). The **gate threshold** is tuned per fold on training scores.
   Per-fold confusion matrices aggregate → α, β, F1.
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
  example mining, gate-threshold tuning, calibration, ranked review queue, outputs).
  `make_tuner` (precision-target vs F1), `build_review_queue` / `precision_at_k_table` /
  `reliability_table`. `MODELS` list / `--model`.
- **`tests/test_offline.py`** — offline unit tests (no network), incl. the operational gate.

### Run (in the project container)
```bash
scripts/docker_run.sh run -m optimization_validator.tests.test_offline                     # offline tests
scripts/docker_run.sh run -m optimization_validator.cross_validate --smoke --model gpt-oss-120b   # tiny e2e
scripts/docker_run.sh run -m optimization_validator.cross_validate --model gpt-5.5 --k 5 \
    --retrieval openevolve --vendor stm \
    --objective precision --target-precision 0.95                                          # full sweep (billable)
```

Outputs → `optimization_validator/<device>/cross_validation/<model|smoke>/` (gitignored):
`judgments_<model>.csv` (per-row + reasoning + `reg_in_context`/`file_search_chars`
coverage), `judgments_tuned_<model>.csv`, `error_analysis_<model>.csv` (FP/FN),
`per_fold_<model>.csv`, `summary_<model>.{csv,json}` (baseline vs tuned **+ an
`operational` block**: gate precision, yield/recall, bugs dropped unseen, precision@top-decile),
`prompts/` (the exact per-fold system prompt incl. legend + mined examples), and the
**operational artifacts**: `review_queue_<model>.csv` (gate survivors, ranked by
confidence — the reviewer-facing list), `precision_at_k_<model>.csv` (review-top-X% →
catch-Y% curve), `calibration_<model>.csv` (confidence reliability bins).

### Results so far (rm0041, k=5; OpenEvolve + chunked batching)
> ⚠️ Measured on the **pre-merge** rm0041 slice (~2,459 verified invariants). The merged
> verified datasheet now yields **3,356** `status=verified` rows, so these numbers should
> be **re-measured** before citing.
| Model | F1 (tuned) | validated precision | raw sens. | β |
|---|---|---|---|---|
| gpt-oss-120b | 0.91 | 0.95 | 0.85 | 0.90 |
| gpt-5.5 (+ access legend) | **0.975** | 0.96 | 0.98 | 0.90 |

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
- [ ] **Expand `derived` peripherals.** Verified CSVs dedup `derivedFrom` peripherals to a
      single marker row (`status=derived`), so the benchmark currently covers only the
      prototype (e.g. `gpioa`, not `gpiob..g`). The diff pipeline expands these; the
      validator benchmark should too if we want per-peripheral coverage numbers.
- [ ] **Tune the number of mined in-context examples** (`max_per_class`, currently 6/class
      → 12/fold). Sweep it and find where added examples stop improving F1 — each one
      grows every system prompt (× every call), so the prompt shouldn't balloon. Measure
      the accuracy-vs-prompt-size tradeoff and pick the smallest count that keeps the gain;
      consider dropping near-duplicate / low-information examples.
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
