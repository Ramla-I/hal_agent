# OPTIMIZATION VALIDATOR

Benchmark and tune the **Validator** (the pipeline's precision filter) as a noisy binary
labeler: k-fold accuracy/calibration on a verified datasheet, human-curated
datasheet-grounded examples, usage/cost, and the frozen per-device **deployment
threshold + validator card** to apply on unverified devices.

## DIRECTORY STRUCTURE

```
optimization_validator/
|__ README.md
|__ cross_validate.py            # the cross-validation harness (entry point)
|__ kfold.py                     # benchmark build + (peripheral, register) k-fold
|__ corruption.py                # realistic per-key corruption
|__ calibration.py               # ConfusionMatrix + Rogan-Gladen calibrate()
|__ access_notation.py           # vendor access-notation legend
|__ access_notations.json        # editable vendor -> notation map
|__ validator_card.py            # build a per-device card: deployment threshold + alpha/beta
|__ curated_examples/
|   |__ README.md
|   |__ <vendor>.json            # human-curated, datasheet-grounded examples
|__ validator_cards/
|   |__ <vendor>_<device>_<model>.json   # frozen calibration to apply on other devices
|__ tests/test_offline.py        # offline unit tests (no network)
|__ <device>_run/                # run outputs (e.g. stmrm0041_run/), via --out-root
    |__ baseline/<model>/        # baseline pass + curation_candidates_<model>.json
    |__ curated/<model>/         # baseline-vs-curated + review queue / precision@k / usage
    |__ seed<N>/<model>/         # seed-variance runs (E2)
    |__ RESULTS.md               # measured results (baseline/cross-model/curation/variance)
```

> The legacy validator-optimization tooling (`validator_optimization.py`,
> `summarize_results.py`, the plot scripts, and the `stm-rm0041/` test/hold sets) has been
> **removed**; the cross-validation harness below supersedes it.

## SCRIPTS

### `CREATE_TEST_SET.PY`
Builds synthetic test sets by perturbing a verified CSV with **realistic** incorrect
values and/or field names (see `corruption.py`). Useful for controlled accuracy
testing. Rows with an empty `correct_value` are dropped (never human-confirmed).

## VALIDATOR CROSS-VALIDATION (paper §"Benchmarking the Validator as a Noisy Labeler")

Benchmark the Validator as a noisy binary labeler with k-fold cross-validation at
(Peripheral, Register) granularity, then calibrate downstream measurements. Measured
results are in `stmrm0041_run/RESULTS.md`; open work is in the TODOs at the end.

### Purpose

The Validator is a **precision filter upstream of human PR review**: it removes the
generator's mistakes so the facts a human reviews (and we ultimately file as SVD/PAC
corrections) are mostly true. Human review time is the bottleneck and a false PR to a
maintainer is costly, so we operate at a **target precision (95%)** and rank survivors by
confidence for top-down review. We benchmark precision **per vendor** on verified
datasheets before trusting the Validator on that vendor's unverified devices — the
per-vendor amortization that lets a fixed annotation cost cover many devices. For vendors
with thin upstream communities (NXP, TI), this internal precision is the primary evidence
that filed bugs are real, standing in for slow upstream merges.

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
   - **No-leakage + equal-count curation.** The curated pass is evaluated **per fold**:
     for held-out fold *f* the block uses only examples whose register is **not** in fold
     *f* (an example never judges its own register), and every fold is capped to the same
     count **N = total − max-fold-count** (override `--curated-per-fold`), sampled
     deterministically — so the folds are comparable. Balanced filling (≈equal per fold)
     keeps `max-fold-count` low → larger N → more of your curation effort is used. The
     `curated_examples/<vendor>.json` draft is **grouped by fold** (each entry tagged with
     its seed-0 fold) so you can fill ≥N-min per fold; runtime recomputes folds per seed.
5. **Operational gate + ranked review queue** (the system this benchmark stands in for).
   The pipeline's real use is: generator candidates → Validator → whatever it gates out
   (V=0) is **dropped unseen**, and the survivors (V=1) are **ranked by confidence** for a
   human to review top-down until labour runs out. So the gate threshold is tuned for a
   **target precision** (`--target-precision 0.95`, the default): the lowest threshold
   whose training precision clears the target, **maximising yield (recall)** under that
   constraint. Because V=0 is
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
7. **Freeze for deployment** (`summary.deployment` + `validator_card.py`): the per-fold τ's
   are for measurement; deployment uses **one** τ — the full-data cutoff hitting the target
   precision, emitted as `summary.deployment.threshold`. `validator_card.py` distils a run
   into `validator_cards/<vendor>_<device>_<model>.json`: the **deployment threshold** (freeze
   + apply on unverified devices — a candidate enters the review queue iff its pseudo-score ≥
   τ, which sizes the queue), the transferable **α/β**, the per-fold τ **stability**, the
   config to freeze (curated set, alias, target), and the held-out metrics to expect on
   transfer. This is the per-vendor amortized asset.

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
scripts/docker_run.sh run -m optimization_validator.cross_validate --model gpt-5.4 --k 5 \
    --retrieval openevolve --vendor stm --target-precision 0.95 \
    --out-root optimization_validator/stmrm0041_run --price-in <$/1M> --price-out <$/1M>

# [human] curate candidates -> optimization_validator/curated_examples/stm.json
# Pass 2 (curated) — add the grounded examples, measure the lift:
scripts/docker_run.sh run -m optimization_validator.cross_validate --model gpt-5.4 --k 5 \
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

### Results (rm0041, k=5, expanded **5,321** invariants, 3 seeds; curated config)
Full numbers + seed variance in `stmrm0041_run/RESULTS.md`; frozen config in `validator_cards/`.

| model | gate precision | yield (mean±std) | F1 | deploy τ | total cost |
|---|---|---|---|---|---|
| gpt-oss-120b (Groq) | 0.948 | 0.71 ± 0.01 | 0.80 | 0.98 | ~$9 |
| gpt-5.4 (OpenAI) | 0.951 | 0.76 ± 0.06 | 0.835 | 0.93 | ~$105 |

- Gate precision holds ~0.95 out-of-sample for both, all seeds.
- **Curation is model-dependent**: +0.026 ± 0.014 yield for gpt-5.4 (positive on all 3 seeds),
  ~0 for gpt-oss-120b (non-positive on all 3). Access, the targeted class, wasn't the driver;
  the grounded bit-tables lifted bit-field confidence.
- **gpt-oss-120b is the stable, ~11× cheaper default**; gpt-5.4 has higher but seed-variable
  yield (near a threshold cliff, τ 0.93 vs 0.98).

### EXPERIMENTS — remaining (validator paper)

Status: ⬜ not started · 🔒 blocked. **★ = load-bearing for a paper claim.** Done —
A1 headline metrics, A2 cross-model, B1 curation lift, E1 per-class, E2 seed variance —
are in the Results table above and `stmrm0041_run/RESULTS.md`.

**B. Ablations that justify the design**
- [ ] **B2. `alt_name` on/off** (`--use-alt-name` / `--no-alt-name`) — lift vs specificity cost.
- [ ] **B3. Access legend on/off** (`--vendor stm` / `none`).
- [ ] **B4. Retrieval backend** — OpenEvolve vs OpenAI file_search; justifies the switch.
- [ ] **B5. Number of curated examples** — vary how many curated, datasheet-grounded
      examples go in the prompt; find where added examples stop helping vs prompt-size cost.

**C. Validity of the calibration — the scientific core**
- [ ] **★ C1. Cross-distribution π test** — measure α/β at 30% corruption, apply to a slice
      at a *different* rate (e.g. 50%), check π̂ recovers ~0.50. The only experiment that
      exercises Rogan–Gladen (within-run π is an identity).
- [ ] **★ C2. Per-vendor transfer (amortization claim)** — calibrate/freeze on device 1,
      apply to device 2 of the same vendor (rm0041→rm0090, ke04→s32k116); check precision/
      yield holds. **🔒 second-device slices not annotated yet** (longest lead time).

**D. External validation — strongest evidence, slow**
- [ ] **D1. Validator-confirmed bugs vs upstream merges** (STM) — ties internal precision to
      real external ground truth. Ongoing, not a one-shot run.

**Prereqs for the NXP / held-out-vendor runs:** a retrieval backend for ke04 (evolve an
OpenEvolve program or accept `--retrieval openai`) and real NXP access notations in
`access_notations.json` (currently stubs).

### OPEN TODOS
- [ ] **Wire curated examples into the production validator (`core/s4_validator.py`).**
      Curated examples currently live only in the *measurement* harness (`cross_validate`);
      deployment doesn't load them. To deploy the validator we benchmarked, `s4` must load
      `curated_examples/<vendor>.json` and inject the **full** set (no fold exclusion / no
      equalisation — those are measurement-only) into the batched system prompt for the
      vendor it's running on. Without this, the production validator runs the *baseline*
      config, not the *curated* one we report.
- [ ] **Make `alt_name` production-real**: the per-row `datasheet_name` hint only helps in
      the benchmark unless the **generator emits the datasheet-printed name** at extraction
      time — add that so the hint transfers to deployment (the general aliasing rule already
      does). (`alt_name` handling and derived-peripheral expansion themselves are done — see
      *Name aliasing* and the pipeline above.)
- [ ] **Fill in real NXP / TI access notations** in `optimization_validator/access_notations.json`
      (currently stubs) when ke04 / msp430g2 slices are benchmarked.
- [ ] **Benchmark the held-out vendors** (NXP `ke04`, then TI) — verified slices exist;
      tests whether rm0041 numbers transfer. Needs each device's chunks/Chroma + an
      OpenEvolve program (or `--retrieval openai`).
- [ ] **Device-to-device transfer within a vendor** (the amortization claim; experiment
      C2). **Freeze** the validator calibrated on one device — its curated
      `curated_examples/<vendor>.json` *and* the chosen threshold — and benchmark it on a
      **second verified datasheet of the same vendor**, to check the precision/yield holds
      without re-tuning. Same-family second device (e.g. another STM32F1) is the trivial
      sanity check; the real test is **cross-family, same vendor** (rm0041 → rm0090),
      since same-family parts are near-identical. Needs the second device's verified slice
      annotated + its chunks/Chroma + retrieval program.
- [ ] **Genuine calibration test for π**: measure α/β on the 30% benchmark, apply to a
      held-out slice with a *different* corruption rate (e.g. 50%), check π recovers
      ~0.50. Only this exercises the correction (within-run π is an identity).
- [ ] **gpt-5.4 threshold instability**: its per-fold τ is bimodal (0.93 vs 0.98) → yield
      swings ±0.05 across seeds; decide whether it's deployable with a frozen threshold or
      needs a more stable objective (gpt-oss-120b is tight, ±0.01).
- [ ] **Fold-3 hard cases**: recall craters on fold 3 for both models (~0.5), partly from
      registers not present in the retrieved context. Revisit retrieval granularity.

## NOTES

- Cross-validation run outputs go to `--out-root` (e.g. `stmrm0041_run/<baseline|curated>/<model>/`).
- The benchmark is built directly from the verified datasheet (`verified_datasheet/<mfr>/<dev>.csv`);
  there are no standing test/hold-set CSVs.
