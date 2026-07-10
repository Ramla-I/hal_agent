# Transfer experiments (C1, C2) — gpt-oss-120b, STM

Distilled results for the two load-bearing transfer experiments. Raw run outputs live in
`stmrm0041_c1_50/` and `stmrm0394_c2_run/` (root-owned by Docker, untracked); the JSONs in
this directory + this file are the committed record. Scripts:
`optimization_validator/c1_cross_distribution.py`, `optimization_validator/c2_transfer.py`
(both offline-tested in `tests/test_offline.py`).

## ★ C1 — cross-distribution π (Rogan–Gladen instrument transfer)

Within a single run, π is an algebraic identity (calibrate() uses that run's own α/β/r̂), so
it proves nothing. C1 tests the real claim: α/β are properties of the *labeler*, not of the
prevalence. Freeze the **raw** labeler (V=1 iff `is_true`, threshold-independent) α/β on
rm0041 at 30% corruption, apply to a 50%-corrupted run, and check π̂ recovers the true
prevalence (1 − corruption).

| run | n | true π | α (raw) | β (raw) | r̂ |
|---|---|---|---|---|---|
| calibrate (30% corruption) | 5321 | 0.699 | 0.767 | 0.893 | 0.568 |
| apply (50% corruption) | 5321 | 0.501 | 0.744 | 0.903 | 0.421 |

- **Instrument is prevalence-stable:** Δα = 0.023, Δβ = 0.010.
- **Forward 30%→50%:** π̂ = 0.477 vs true 0.501 (error 0.025).
- **Reverse 50%→30%:** π̂ = 0.729 vs true 0.699 (error 0.029).
- **Verdict:** the 30%-calibrated instrument recovers a different distribution's true defect
  prevalence to ~2.5–3%. Rogan–Gladen works out-of-distribution here.

Artifact: `c1_rm0041_gpt-oss-120b.json`.

## ★ C2 — cross-family transfer, rm0041 (STM32F1) → rm0394 (STM32L4)

Hypothesis: the whole rm0041 calibration amortizes across STM devices — the evolved
OpenEvolve retrieval program, the deployment threshold τ, and the instrument (α, β). Freeze
all of it and run the Validator on rm0394 (same program on rm0394's chunks, 30% corruption,
baseline config); apply the frozen τ and compare to rm0394's own tuning.

- **Retrieval transfers:** the rm0041 evolved program hit **95%** register-coverage on
  rm0394 (vs 86% on rm0041 itself).
- **Threshold transfers:** rm0394 independently tunes to **τ = 0.98** — identical to the
  frozen rm0041 value.
- **Frozen τ = 0.98 on rm0394:** precision **0.941**, yield **0.843** (reviewed 1304/2078;
  tp 1227, fp 77, fn 228).
- **Amortization holds:** freezing costs **d_precision = 0.000, d_yield = 0.000** vs.
  re-tuning per-device.
- `reaches_target = False` **only** because rm0394's own precision *ceiling* is 0.941
  (< 0.95 target) — a device-hardness fact, not a transfer failure (its own best tuning tops
  out at the same 0.941). Yield (0.843) actually **exceeds** rm0041's (0.689).

| device | retrieval coverage | frozen τ | precision | yield | own-tuned τ | amortization cost |
|---|---|---|---|---|---|---|
| rm0041 (dev) | 86% | 0.98 | 0.948 | 0.689 | — | — |
| rm0394 (transfer) | 95% | 0.98 | 0.941 | 0.843 | 0.98 | d_prec 0.000, d_yield 0.000 |

Artifact: `c2_rm0041_to_rm0394_gpt-oss-120b.json`.

## Notes

- C1's α/β are the **raw** labeler (τ=0.5) — the fixed operating point cross-distribution
  transfer requires — so they differ from the validator card's tuned-gate α/β (0.689/0.912).
- Both experiments are gpt-oss-120b only (gpt-5.4 not run for transfer). NXP (ke04 → k64) is
  the remaining vendor pair and needs the `--manufacturer` plumbing fix first.
