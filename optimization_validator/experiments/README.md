# Validator experiment runs (raw outputs)

Every cross-validation run's raw per-fold outputs, in one place. This directory is
**git-ignored** except this README — the runs total ~240 MB, so they are shipped as a
**zipped release asset**, not committed. The *distilled* results (the numbers that go in
the paper) live in `../results/` and the frozen per-device calibration in
`../validator_cards/`.

To bundle the asset:
```
zip -r validator_experiments.zip optimization_validator/experiments \
    -x 'optimization_validator/experiments/README.md'
```

## Runs (dir → experiments → device/model)

| dir | experiments | device(s) / model | distilled in |
|---|---|---|---|
| `stmrm0041_run/` | A1 baseline, A2 cross-model, B1 curation lift, E1 per-class, E2 seed variance | STM rm0041 (STM32F1); gpt-oss-120b + gpt-5.4; subdirs `baseline/ curated/ seed1/ seed2/` | `results/stm_rm0041_original_run.md` |
| `stmrm0041_c1_50/` | C1 cross-distribution π (50% corruption arm) | STM rm0041; gpt-oss-120b | `results/transfer_and_calibration.md` + `results/pi_calibration_crossdist_rm0041_gpt-oss.json` |
| `stmrm0394_c2_run/` | C2 per-vendor transfer (STM device-2) | STM rm0394 (STM32L4); gpt-oss-120b; retrieval frozen from rm0041 | `results/transfer_and_calibration.md` + `results/transfer_stm_rm0041_to_rm0394_gpt-oss.json` |
| `nxpke04_run/` | held-out vendor + C2 device-1 (NXP) | NXP ke04 (MKE04Z4); gpt-oss-120b; `%s`-dim-expanded slice | `results/transfer_and_calibration.md` |
| `nxpk64_c2_run/` | C2 per-vendor transfer (NXP device-2) | NXP k64 (MK64F12); gpt-oss-120b; retrieval frozen from ke04 | `results/transfer_and_calibration.md` + `results/transfer_nxp_ke04_to_k64_gpt-oss.json` |

## What each run dir contains (per model subdir)

`summary_<model>.json` (headline + operational + deployment + usage), `judgments_<model>.csv`
(per-invariant: score, is_true, is_correct, fold, τ, reasoning), `review_queue_<model>.csv`,
`precision_at_k_<model>.csv`, `calibration_<model>.csv` (reliability bins),
`per_fold_<model>.csv`, `error_analysis_<model>.csv` (FP/FN), `usage_<model>.csv`,
`curation_candidates_<model>.json`.

## Experiment codes (see `../README.md` → EXPERIMENTS)

A = headline metrics · B = design ablations · C = calibration validity (★C1 cross-distribution
π, ★C2 per-vendor transfer) · D = external validation · E = per-class / seed variance.
