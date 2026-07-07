# Validator Plan

Working plan for the Validator: what it does, why, and what's left. Design details live in
`optimization_validator/README.md`; measured numbers in
`optimization_validator/stmrm0041_run/RESULTS.md`; the frozen per-device config in
`optimization_validator/validator_cards/`.

## What it does

The generator extracts register-layout facts from a device datasheet (`address_offset`,
`reset_value`, `size`, `bit_offset`, `bit_width`, `access`). The **Validator** is an LLM
that reads each extracted fact plus retrieved datasheet context and judges whether the
datasheet supports it, emitting a binary `is_true` + a `confidence`. It runs per register,
batched (≤12 facts/call, split-and-retry). Facts it rejects are dropped; facts it accepts
that also disagree with the vendor SVD become candidate bugs.

How it's built, measured, and deployed:

- **Benchmark** (`kfold.py`): verified datasheet → expand `derivedFrom` peripherals →
  replace 30% of facts with realistic, peripheral-stratified corruptions → k=5 folds at
  (peripheral, register) granularity.
- **Cross-validate** (`cross_validate.py`): per held-out fold, tune the decision threshold
  τ on the training folds to the lowest cutoff hitting the 95% precision target (maximizing
  yield); aggregate held-out confusion matrices → α (sensitivity), β (specificity), gate
  precision, yield, plus a ranked review queue + precision@k.
- **Tune** (once per vendor, human-in-the-loop): the base prompt carries static reasoning
  examples + a vendor access-notation legend + `alt_name` aliasing; a curator turns the
  Validator's mistakes into datasheet-grounded examples in `curated_examples/<vendor>.json`,
  injected per-fold-excluded and count-equalized so the measurement stays honest.
- **Calibrate** (`calibration.py`): Rogan–Gladen π and validated-set precision (α·π/r̂).
- **Deploy** (`validator_card.py`): freeze the single full-data **deployment threshold** +
  curated set + α/β into a per-device validator card; on an unverified device, accept a
  candidate iff its pseudo-score ≥ τ — which sizes the human review queue.

## Purpose

The Validator is a **precision filter upstream of human PR review**: it removes the
generator's mistakes so the facts a human reviews (and we ultimately file as SVD/PAC
corrections) are mostly true. Human review time is the bottleneck and a false PR to a
maintainer is costly, so we operate at a **target precision (95%)** and rank survivors by
confidence for top-down review. We benchmark precision **per vendor** on verified
datasheets before trusting the Validator on that vendor's unverified devices — the
per-vendor amortization that lets a fixed annotation cost cover many devices. For vendors
with thin upstream communities (NXP, TI), this internal precision is the primary evidence
that filed bugs are real, standing in for slow upstream merges.

## TODOs

- [ ] **Wire curated examples into the production Validator (`core/s4_validator.py`).**
      Load `curated_examples/<vendor>.json` (the full set, no fold exclusion) so deployment
      runs the curated config we benchmarked, not the baseline.
- [ ] **Cross-distribution π test.** Measure α/β at 30% corruption, apply to a slice at a
      *different* rate (e.g. 50%), check π̂ ≈ 0.50 — the only test that exercises the
      Rogan–Gladen correction (within-run π is an algebraic identity).
- [ ] **Device-to-device transfer.** Freeze a device's card (threshold + curated set +
      α/β) and apply it, without re-tuning, to a second verified device of the same vendor
      (rm0041 → rm0090); check precision/yield hold. Needs the second slice annotated.
- [ ] **Benchmark the held-out vendors.** NXP `ke04` (verified slice now loads), then TI
      `msp430g2` — tests whether the method transfers across vendors. Needs each device's
      chunks/Chroma + a retrieval program (or `--retrieval openai`).
- [ ] **Fill real NXP / TI access notations** in `optimization_validator/access_notations.json`
      (currently stubs) when those slices are benchmarked.
- [ ] **gpt-5.4 threshold instability.** Its per-fold τ is bimodal (0.93 vs 0.98) → yield
      swings ±0.05 across seeds; decide whether it's deployable with a frozen threshold or
      needs a more stable objective (gpt-oss-120b is tight, ±0.01).
- [ ] **Fold-3 hard cases.** Recall craters on fold 3 for both models (~0.5), partly from
      registers not present in the retrieved context. Revisit retrieval granularity.
