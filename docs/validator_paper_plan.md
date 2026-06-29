# Phase 1b — Validator Plan (paper-anchored)

**Status:** authoritative spec for the Phase 1b validator-precision work.
**Source:** paper section "Validating Invariants at Scale" (`\label{sec:validator}`), provided by Ramla 2026-06-15.
**Rule:** implement to this spec. **If implementation diverges from it, log the divergence in the "Divergence log" section at the bottom** (what changed, why, and the consequence for the paper). At the end of the phase, this file is the diff between paper-as-written and what we actually did.

> ⚠️ **Conflict with project memory (flagged 2026-06-15):** the `lidar-hal-agent-project.md` memory records that *"the π / Rogan-Gladen noisy-labeler calibration is DROPPED (merges are the real adjudicator…)."* This paper section RE-INTRODUCES that calibration (§"Calibrating Downstream Measurements": α, β, π, Rogan-Gladen inversion). This doc treats the paper section as the current source of truth. **Memory needs reconciling** — pending Ramla's confirmation on whether π is back in.

---

## Paper section (verbatim — the target)

The Accuracy Validator agent (Validator) labels each invariant produced by the Generator as true or false to mitigate hallucinations and incorrect extractions. Because the Validator is itself imperfect, our design has two complementary components that explicitly *improve and quantify* its reliability. First, we build a small dataset of human-verified digital datasheets (one per manufacturer) and use it to tune prompts and in-context examples and to benchmark Validator accuracy (including false-positive and false-negative rates). Second, we treat the Validator as a noisy labeler and use its measured error rates to calibrate how much to trust validated invariants and to interpret downstream measurements that depend on Validator judgments (e.g., when estimating TRIE's extraction quality).

### Creating a Dataset of Digital Datasheets
To enable fast and reliable evaluation of the Validator, we convert datasheets into a tabular representation with fully human-verified values. Each datasheet is encoded as a CSV file with five columns, Peripheral, Register, Field, Key, and Value, where the first four identify a specific invariant and the final column stores the correct, human-checked value. This format captures all register-layout invariants relevant to our system while making automated evaluation straightforward.

We built a lightweight annotation tool that efficiently constructs the verified datasheet dataset. For each invariant row, the tool pre-populates two candidate values (one from the SVD and one from the Generator) and asks a human reviewer to select the correct value or enter a new one when both are wrong. This workflow minimizes annotation cost because selecting an existing value is much faster than typing values from scratch. In practice, when the SVD and Generator values agree, they are always correct, an observation that can further reduce human effort when scaling the dataset.

### Benchmarking the Validator as a Noisy Labeler
We benchmark the Validator as a noisy binary labeler using $k$-fold cross-validation on each verified datasheet. The goal of this evaluation is not merely to report the Validator's F1 score, but to quantify how uncertainty in Validator judgments propagates to downstream measurements that depend on those judgments. We report F1 score as the primary summary metric because it balances precision and recall, both of which are critical for downstream applications that must simultaneously limit incorrect invariants passing through (precision) and avoid discarding correct invariants (recall). We also retain the full confusion matrix of the Validator to correct downstream measurements.

We use a cross-validation protocol that avoids train/test contamination and matches how LIDAR is used in practice by grouping related invariants and adding realistic negative examples. Each verified datasheet contains approximately 1,500 invariants. We construct $k$ folds at the (Peripheral, Register) granularity (not the invariant-row level) so that correlated invariants from the same register do not appear in both training and held-out partitions. Before splitting into folds, we corrupt 30% of invariants by modifying invariant values or field names and replace the original invariant with its corrupted version, ensuring every fold contains both positive and negative cases without creating true/corrupted pairs across folds. In each fold, we tune prompt wording, in-context examples, and decision thresholds on the training partitions and evaluate on the held-out fold. During tuning, we request brief explanations and analyze false positives and false negatives to identify systematic failure modes and add targeted in-context examples, with particular attention to corner cases. At evaluation time, the Validator receives candidate invariants from the held-out set together with datasheet text chunks retrieved by our semantic retrieval pipeline and outputs a binary true/false judgment. We compute a per-fold confusion matrix, and then across folds we aggregate counts to get the final Validator confusion matrix to help calibrate downstream measurements.

Confusion matrix (C = true correctness, V = Validator judgment):

```
        C = 1     C = 0
V = 1    α       1-β
V = 0   1-α       β
```

Where C ∈ {0,1} denotes true invariant correctness and V ∈ {0,1} denotes the Validator judgment. Here, α = P(V=1 | C=1) is sensitivity (true-positive rate) and β = P(V=0 | C=0) is specificity (true-negative rate).

**[EXPERIMENT placeholder]** Results of cross-validation with different models.

### Calibrating Downstream Measurements
TRIE relies on the Validator to accept or reject invariants when ground-truth labels are unavailable. Because the Validator is imperfect, treating its judgments as ground truth would bias estimates of TRIE's accuracy. We instead use the Validator's benchmarked sensitivity and specificity to correct downstream measurements.

Let π = P(C=1) denote the true fraction of correct invariants produced by TRIE, and let r̂ = P(V=1) denote the observed acceptance rate according to the Validator.

Under the noisy-label model:

```
r̂ = P(V=1|C=1)·P(C=1) + P(V=1|C=0)·P(C=0)
r̂ = α·π + (1-β)·(1-π)
```

Solving for π yields:

```
π = (r̂ - (1-β)) / (α + β - 1)
```

The resulting π estimates TRIE's true correctness rate and its true overall error rate (1 - π), corrected for Validator errors. Unlike the Validator's acceptance rate r̂, π is an intrinsic measure of TRIE's extraction quality: it characterizes the fraction of invariants that are correct before any validation, and is therefore the appropriate quantity for comparing extraction performance across settings. This calibration assumes the Validator's sensitivity and specificity measured on our benchmark transfer to the distribution of invariants produced by TRIE.

For downstream applications, however, we primarily consume the subset of invariants that the Validator accepts (V=1), so we also require an estimate of the *precision* of the validated set, P(C=1 | V=1), which quantifies the expected fraction of accepted invariants that are truly correct. We estimate this quantity as:

```
P(C=1 | V=1) = α·π / r̂      (Bayes' rule)
```

and use it to decide when to insert human review (e.g., when the expected number of incorrect accepted invariants is too high).

Identifiability notes (from paper comments): the correction is identifiable when α + β > 1 (Validator better than random); when α + β ≈ 1 the estimate is unstable. Because α, β, r̂ are estimated from finite data, π may fall slightly outside [0,1]; clamp to [0,1] when reporting.

---

## Implementation checklist (derived from the spec)

Status legend: ✅ done · ◑ partial (see Divergence log) · ⬜ not started.

- [x] ✅ **Dataset format** — verified datasheet CSV = (Peripheral, Register, Field, Key, Value). Present: `verified_datasheet/stm/rm0041_stm32f100.csv`, `verified_datasheet/nxp/ke04_mke04z4.csv`. Annotation tool = `verified_datasheet/annotate.py` (Phase 0, done). Loader (`kfold.load_verified`) drops rows with empty `correct_value` (never human-confirmed) → rm0041 yields **2,459** usable invariants (see divergence #3).
- [x] ✅ **Corruption = 30%**, modifying values OR field names; **replace** the original (no true/corrupted pairs). Realistic per-key corruption in `optimization_validator/corruption.py`: in-range bit_offset/bit_width, nibble-flip / neighbour-stride hex, size ∈ {8,16,32,64}, access swaps, real sibling field names or one-edit typos. `create_test_set.py` rewritten to route through it; verified by `tests/test_offline.py`.
- [x] ✅ **k folds at (Peripheral, Register) granularity** — `optimization_validator/kfold.py` assigns whole registers to folds (round-robin on a seeded shuffle). Tested: each (per,reg) in exactly one fold; every fold has both classes.
- [x] ◑ **Per-fold tuning** — now **two** automated knobs, both fit on training only: (a) **in-context example mining** (`cross_validate.mine_examples` → `cross_validate_mined`): each fold mines the Validator's own FP/FN on its training partition, renders them as labelled few-shot examples, and re-evaluates the held-out fold with the augmented prompt; (b) **decision-threshold** max-F1 tuning. Prompt-*wording* rewriting remains manual. The exact augmented prompt per fold is persisted under `<out>/prompts/`. See divergence #1.
- [x] ✅ **Eval-time inputs** — held-out invariants + datasheet chunks from `context_retrieval.search.search_context` → binary true/false (`cross_validate.evaluate_benchmark`, per-register batched).
- [x] ✅ **Per-fold confusion matrix** aggregated across folds → final confusion matrix (α, β) in `calibration.ConfusionMatrix`.
- [x] ✅ **Primary metric = F1**; full confusion matrix retained (α, β, precision, recall, accuracy) in every summary.
- [x] ✅ **Run across models** — **two models swept** on rm0041 (k=5, 2,459 invariants, OpenEvolve retrieval): **gpt-oss-120b** (Groq) and **gpt-5.5** (OpenAI). See cross-model comparison in Results. More models = one more `--model` run each.
- [x] ✅ **Calibration** — `calibration.calibrate`: π = (r̂-(1-β))/(α+β-1); validated-set precision P(C=1|V=1) = α·π/r̂; guards α+β>1; clamps π to [0,1]; flags non-identifiable / clamped. Tested against a hand-computed case (π=0.7, α=0.9, β=0.8).
- [x] ◑ **Outputs** under `optimization_validator/<device>/cross_validation/<model|smoke>/` (gitignored). Did **not** also mirror into `optimization/test_outputs/validator/<run>/`; the device-local tree is self-contained. See divergence #6.

### How to run
```bash
# offline unit tests (no network)
scripts/docker_run.sh run -m optimization_validator.tests.test_offline
# tiny end-to-end smoke test (real API, 1 model, few registers)
scripts/docker_run.sh run -m optimization_validator.cross_validate --smoke --smoke-registers 4 --k 2
# full cross-validation across MODELS (billable, slow)
scripts/docker_run.sh run -m optimization_validator.cross_validate --k 5
```

---

## Divergence log

| # | Date | Spec said | We did instead | Why | Paper impact |
|---|------|-----------|----------------|-----|--------------|
| 1 | 2026-06-16 | Per-fold tuning of **prompt wording, in-context examples, and decision thresholds** on training partitions. | Automated **in-context example mining** (per fold: mine training-fold FP/FN → labelled few-shot examples → re-evaluate held-out with augmented prompt) **and** the **decision threshold** (max-F1). Prompt-*wording* rewriting stays manual. Augmented prompts persisted per fold. | Example mining is the lever that actually moves accuracy and is cleanly automatable from the existing per-row judgments; wording rewriting needs an APE-style loop. | Methods: report that in-context examples were selected automatically per fold from training-partition errors (12/fold here: 6 from FP, 6 from FN); only prompt wording was hand-edited. *(Updated 2026-06-16: was threshold-only on 06-15.)* |
| 2 | 2026-06-15 | Tune on training partitions, evaluate on held-out fold. | Run the Validator **once per invariant** (each row judged as a member of its held-out fold); reuse those per-row judgments as the *training* signal when tuning other folds' thresholds. | Cost: re-querying the LLM for every train partition would be ≈k× the API spend for no benefit — thresholding only needs the per-row scores, and no row's judgment is used to both tune and evaluate itself. | None on confusion-matrix semantics. Worth a one-line footnote that threshold tuning reuses cross-fold judgments rather than re-querying. |
| 3 | 2026-06-15 | "Each verified datasheet contains approximately **1,500** invariants." | rm0041 verified CSV has 3,866 rows; **1,407 have an empty `correct_value`** (never human-confirmed) and are dropped → **2,459** usable invariants. | Blank-value rows can be neither a trustworthy positive nor a corruption base. | Update the per-datasheet count (rm0041 ≈ 2,459 *verified* invariants, not ~1,500), or state ~1,500 refers to a different/earlier slice. Flag for Ramla. |
| 4 | 2026-06-15 | Validator outputs a binary true/false judgment. | It emits `is_true` **and** a `confidence_score` (confidence in its own judgment). We derive a tunable score `= confidence if is_true else 1−confidence` and threshold it (0.5 ⇒ raw `is_true`). | Need a continuous score for decision-threshold cross-validation. | Minor methods detail; document the score definition if thresholds are reported. |
| 5 | 2026-06-16 | "[EXPERIMENT] Results of cross-validation with different models." | Ran the **full sweep for one model** (gpt-oss-120b, rm0041, k=5). A second model is one more `--model` run. | Operator chose one model first. | Experiment table now has its first row (below); add ≥1 more model to make it a cross-model comparison. |

| 6 | 2026-06-15 | Outputs per STRUCTURE.md, incl. `optimization/test_outputs/validator/<run>/`. | Wrote a self-contained device-local tree `optimization_validator/<device>/cross_validation/<model\|smoke>/` (gitignored); did not also mirror to `optimization/test_outputs/`. | Keeps all CV artifacts beside the existing `optimization_validator/<device>/experiments/` outputs. | None; note the canonical CV output location. |
| 7 | 2026-06-16 | Validator uses the project's semantic retrieval pipeline. | First runs used **OpenAI file_search, 4 chunks, no register metadata filter** — neither the generator's `LOCAL_VECTOR_DB` nor the evolved `OPENEVOLVE` program. Switched the harness to the **OpenEvolve best program** (`--retrieval openevolve`) over copied rm0041 chunks + Chroma. | OpenAI file_search can't do register-name filtering and surfaced too little context; OpenEvolve is what the rest of the pipeline uses. | Report the validator's retrieval backend explicitly; results below use OpenEvolve. |
| 8 | 2026-06-17 | (harness correctness) | Found + fixed a **batching bug**: large registers (≤57 invariants) produced JSON that overflowed the output-token limit and failed to parse, defaulting the **whole register to reject** (834 rows; raw sensitivity looked like 0.52). Now chunk to ≤12 invariants/call with split-and-retry. | A measurement artifact was masquerading as validator over-rejection. | None on the paper's method; the *numbers* below supersede all earlier runs. Earlier F1/β figures were depressed by this bug. |
| 9 | 2026-06-29 | Ground truth = rows with a non-empty `correct_value`. | Merged main's new verified-datasheet schema (`status`, `alt_name`, `set_method`, `derived` marker rows). Ground-truth selection now gates on **`status == "verified"`** (`select_ground_truth`); legacy "non-empty correct_value" support dropped (old schema is being retired). rm0041 ≈ **2,459 → 3,356** verified invariants. rm0394 is unannotated → raises a clear error. | New schema makes `status` the authoritative trust signal and adds non-invariant `derived` marker rows that must not be benchmarked. | Update the per-datasheet count again (rm0041 ≈ 3,356); **re-run the sweep** — current results table is on the 2,459-row pre-merge slice. `alt_name` (datasheet-printed names) is an untapped lever against name-mismatch false negatives — logged as a TODO. Supersedes the count in divergence #3. |
| 10 | 2026-06-29 | Tune the **decision threshold to maximise F1**; report F1/α/β + calibration. | Reframed the gate to the **operational** model: validator gates candidates, V=0 dropped **unseen**, V=1 **ranked by confidence** for a human reviewer. Default gate objective is now **precision-targeted** (`--objective precision --target-precision 0.95`): lowest threshold with training precision ≥ target, maximising **yield (recall)** under it (`--objective f1` keeps the old behaviour). Harness now also emits a ranked **review queue**, **precision@k**, and a **calibration/reliability** table, and reports gate precision + yield (bugs dropped unseen). | The deployment always has a human review before filing, so the validator is a *prioritiser*, not an auto-filer: maximise true bugs surfaced per reviewer-hour at a precision the reviewer's time justifies; F1 is the wrong objective. Hard-drop makes a false negative a permanently lost bug → recall must be reported alongside precision. | Methods: report the gate as precision-at-a-target with yield, and the review-queue precision@k / calibration, instead of (or alongside) max-F1. π/Rogan–Gladen count-correction moves off the critical path for the operational claim. |

### Results — full sweep (gpt-oss-120b, rm0041, k=5, seed 0, 30% corruption)

2,459 verified invariants (1,721 correct / 738 corrupted), 219 registers. **Final config: OpenEvolve retrieval + chunked batching (≤12/call).**

Progression (baseline = threshold-only, cross-validated; each fixes a real issue):

| Run (baseline variant) | retrieval | batching | F1 | precision | β (spec.) | raw sens. | validated precision | π |
|---|---|---|---|---|---|---|---|---|
| 1 | OpenAI file_search (4 chunks) | unchunked (buggy) | 0.797 | 0.762 | 0.392 | 0.521 | 0.762 | 0.700 |
| 2 | OpenEvolve | unchunked (buggy) | 0.857 | 0.845 | 0.629 | 0.526 | 0.845 | 0.700 |
| **3 (final)** | **OpenEvolve** | **chunked + retry** | **0.898** | **0.954** | **0.904** | **0.849** | **0.954** | **0.700** |

Final tuned (mined examples + threshold): F1 **0.911**, α 0.872, β 0.901, validated precision **0.954**, π 0.700. Mining now gives a small positive lift (+0.013). Raw confusion (is_true): TP=1461, FP=71, TN=667, FN=260; **0 parse errors**.

**Reads:**
- **π is identical (0.6999) across every run — and that is an algebraic identity, NOT validation.** π=0.6999 is exactly 1721/2459, the benchmark's known correct fraction (same seed + 30% corruption in every run). Rogan–Gladen inverts `r̂ = α·π + (1−β)·(1−π)`; when α, β, **and** r̂ are all measured on the *same* confusion matrix, the inversion returns the empirical prevalence P/T **exactly, for any α, β** — so the validator's quality (β ranged 0.39→0.90 across runs) cannot move it. Within-run π recovery only confirms the arithmetic, not the calibration's usefulness. π becomes a genuine estimate only when benchmark-measured α, β are applied to a **different** r̂ — TRIE's real, unlabeled invariants (the paper's actual use), or a cross-run/held-out-distribution test. *(Corrected 2026-06-17: an earlier draft wrongly cited π-recovery as validation of the correction.)*
- **Retrieval + the batching fix together transformed the headline:** validated precision 0.76 → **0.95**, specificity 0.39 → **0.90**, raw sensitivity 0.52 → **0.85**. Most of the apparent "validator over-rejection" was a harness batch-truncation artifact (divergence #8), not the model.
- **Residual false negatives are now small and genuine: 260, almost all confident** (243 at conf≥0.99), **dominated by `access` (178).** The model finds the register's address/summary table (87% register-in-context) but confidently rejects correct field-level `access` values — likely datasheet access-notation (`rc_w0`, `rw`, reserved) vs the verified `read-write`/`read-only` label, plus some field-table granularity misses. This — not retrieval or batching — is the real remaining validator weakness to study next.

### Cross-model comparison (gpt-oss-120b vs gpt-5.5; OpenEvolve + chunked batching, same benchmark)

| Model | F1 (base) | precision | β | raw sens. | raw FN | validated precision | F1 (tuned) | π |
|---|---|---|---|---|---|---|---|---|
| gpt-oss-120b (Groq) | 0.898 | 0.954 | 0.904 | 0.849 | 260 | 0.954 | 0.911 | 0.700 |
| **gpt-5.5** (OpenAI) | **0.961** | 0.961 | 0.909 | **0.962** | **66** | 0.961 | **0.970** | 0.700 |

**Reads:**
- **gpt-5.5's gain is almost all sensitivity** (0.849 → 0.962; raw FN 260 → 66). Specificity (β ≈ 0.90) and validated precision (≈ 0.96) are tied — both models reject corruptions equally well; gpt-5.5 is just far less conservative on correct invariants.
- **`access` is the dominant error for *both* models, on *both* sides:** gpt-5.5 FN are 58/66 `access`; gpt-oss FN 178/260 `access`; gpt-5.5 FP (corrupted accepted) 46/67 `access`. A model-independent failure → **systematic access-notation mismatch** (datasheet `rc_w0`/`rt_w0`/`rw`/`reserved` vs verified `read-write`/`read-only`/`write-only`), not a capability gap. This is the next lever (a normalization/prompt fix, not a bigger model).
- π = 0.6999 for both — see the identity note above; cross-model invariance is expected, not informative.

*(Runtime: gpt-5.5 full sweep ≈ 15 min — the per-call latency is modest; the earlier "~hours" estimate was dominated by the one-time OpenEvolve index build in the tiny smoke.)*

### Access-notation legend (vendor-extensible) — fixing the dominant residual error

`access` was the top residual error for both models (notation mismatch: datasheet `rc_w0`/`rc_w1`/`rw` vs verified `read-write`). Fix: a vendor-keyed map (`optimization_validator/access_notations.json`, edit-only — no code change to add a vendor) → `optimization_validator/access_notation.py` builds a legend injected into the validator system prompt (both batched + sequential, so production `s4` benefits too). Selected via `--vendor` (default `stm`; `none` disables). Before/after, same benchmark:

| Model | access FN | access FP | raw sens. | β | F1 (tuned) |
|---|---|---|---|---|---|
| gpt-5.5 — no legend | 58 | 46 | 0.962 | 0.909 | 0.970 |
| **gpt-5.5 — legend** | **26** | 55 | **0.980** | 0.897 | **0.975** |
| gpt-oss-120b — no legend | 190 | 45 | 0.849 | 0.904 | 0.911 |
| gpt-oss-120b — legend | 176 | 47 | 0.865 | 0.902 | 0.906 |

**Reads:**
- **Legend cut gpt-5.5 access FN by 55% (58→26)**, lifting sensitivity 0.962→0.980 and tuned F1 to 0.975 — confirming those FN were genuinely the notation mismatch.
- **Expected tradeoff:** telling the model `rc_w0 ≡ read-write` also makes it slightly more accepting of *corrupted* access (gpt-5.5 access FP 46→55, β 0.909→0.897). Net clearly positive; validated precision held (~0.96).
- **gpt-oss-120b benefits little** (FN 190→176): it applies the instruction less reliably and more of its access FN are field-table *retrieval* misses (no `rc_w0` in context to remap) — a retrieval/model-capability issue, not notation.
- **Extensibility:** NXP/TI blocks are stubbed in the JSON; add real codes there when those slices are benchmarked.

> ⚠️ **π reconciliation still open** (see banner at top): this implementation *does* re-introduce the Rogan-Gladen π calibration per the paper section. The project memory says π was dropped. Pending Ramla's confirmation on whether π stays.
