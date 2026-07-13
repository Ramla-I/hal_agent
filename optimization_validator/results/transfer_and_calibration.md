# Cross-device transfer & calibration (experiments C1, C2)

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

Artifact: `pi_calibration_crossdist_rm0041_gpt-oss.json`.

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

Artifact: `transfer_stm_rm0041_to_rm0394_gpt-oss.json`.

## Held-out vendor — NXP ke04 (does the approach work off STM at all?)

Ran the full pipeline on NXP KE04 (`--manufacturer nxp`, ke04's own evolved program,
30% corruption, baseline), on the `%s`-dim-EXPANDED verified datasheet (3,267 invariants,
236 registers). **It works, comparable to STM:** gate precision **0.958** (clears target),
yield **0.783**, F1 0.861, retrieval coverage 97%.

The `%s`-dim expansion (fixing the earlier retrieval artifact) had a two-sided effect:
- **It stabilized the deployment threshold** — the earlier instability *was* the `%s`
  artifact. τ went from 0.15 (per-fold 0.15–0.9, **std 0.36**) to **0.07** (per-fold
  0.07–0.10, **std 0.012**), now as well-determined as rm0041's τ=0.98.
- **But yield dropped** (0.863 → 0.783) and total FN rose (261 → 494): materializing each
  `%s` array register into its concrete instances (tctrl0/tctrl1, …) added invariants the
  validator rejects, so `access`/`bit_offset`/`bit_width` are now the large FN classes. Net:
  a more honest (and more stable) benchmark, at some recall.

(Pre-expansion numbers, for the record: precision 0.953, yield 0.863, unstable τ=0.15.)

## ★ C2 (NXP) — transfer ke04 → k64 (MK64F12)

Froze the (expanded) ke04's evolved program + deployment τ (**0.07**) and applied to k64.

- **Retrieval transfers:** ke04 program → **90%** coverage on k64.
- **Frozen τ = 0.07 on k64:** precision **0.951**, yield **0.583** — **clears the target**,
  and freezing costs **exactly zero** (d_precision 0.000, d_yield 0.000): the frozen τ accepts
  the same rows as k64's own tuned τ=0.10 ⇒ **amortization holds**.
- With ke04's threshold now stable, the transfer is a clean exact match rather than the
  earlier overshoot (0.968) from an unstable frozen τ.

| device | retrieval coverage | frozen τ | precision | yield | own-tuned τ | amortization |
|---|---|---|---|---|---|---|
| ke04 (dev) | 97% | 0.07 | 0.958 | 0.783 | — | — |
| k64 (transfer) | 90% | 0.07 | 0.951 | 0.583 | 0.10 | holds (d_prec 0.000, d_yield 0.000) |

Artifact: `transfer_nxp_ke04_to_k64_gpt-oss.json`.

## Summary across both vendors (C2)

**Amortization holds for both STM and NXP** — freezing device-1's calibration costs ~nothing
vs. re-tuning on device-2 (STM d = 0.000/0.000; NXP d = 0.000/0.000). The two differ on
`reaches_target`: rm0394's own precision ceiling (0.941) sits just below 0.95, while k64
clears it (0.951). So the paper claim is "the frozen operating point is no worse than
per-device tuning," with the target-reachability caveat that some devices are intrinsically
harder. Threshold stability is a benchmark-quality signal: ke04's `%s`-dim artifact made its
τ swing 0.15–0.9 until the array registers were expanded, after which τ tightened to 0.07±0.01.

## Notes

- C1's α/β are the **raw** labeler (τ=0.5) — the fixed operating point cross-distribution
  transfer requires — so they differ from the validator card's tuned-gate α/β.
- All transfer results are gpt-oss-120b only (gpt-5.4 not run for transfer).
- C1 was run for STM only; NXP C1 (cross-distribution π on ke04/k64) is not yet done.
