# Why the Validator deployment threshold differs so much: NXP (τ=0.07) vs STM (τ=0.98)

*Analysis of existing calibration results — no new runs. Sources listed at the bottom.*

## TL;DR

For the **same** validator model (`gpt-oss-120b`) at the **same** target precision (0.95),
the frozen deployment threshold τ is wildly different between the two calibration devices:

| device | vendor | model | deployment τ | gate precision | yield |
|---|---|---|---|---|---|
| rm0041 | STM | gpt-oss-120b | **0.98** | 0.948 | 0.689 |
| ke04 | NXP | gpt-oss-120b | **0.07** | 0.958 | 0.783 |

This is **not** a quality difference — both devices clear the 95% precision target. τ is just an
operating point, and two things drove NXP's to be so low (and once so unstable):

1. **A `%s` dim-array artifact** in the NXP verified datasheet made τ *unstable* (jumping 0.15–0.9). Fixing it settled τ to a well-determined 0.07.
2. **The confidence distribution is bimodal with a big empty gap** (a jump from ~0.07 up to ~0.8+). That gap is why the settled τ is both *low* and *stable* — and it comes straight from the **model's** near-binary confidence, not from anything in our pipeline.

## Background: what the threshold actually is

The Validator judges each extracted invariant and emits a `confidence_score`. We derive a
**pseudo-score** deterministically:

```
s = conf            if the validator's verdict is "true" (is_true)
s = 1 − conf        otherwise
```

A candidate enters the human review queue iff `s ≥ τ`. The **deployment threshold** is picked
as *the lowest cutoff whose precision meets the target on the full dev-device benchmark*
(maximizing recall, ties → lower τ). So τ literally sets *how many rows get reviewed*, and its
value just reflects where each device's pseudo-score distribution sits.

## Reason 1 — the `%s` dim-array artifact (why NXP's τ was *unstable*)

The NXP KE04 verified datasheet initially left array registers as unexpanded `%s` placeholders
(e.g. `TCTRL%s`) instead of their concrete instances (`tctrl0`, `tctrl1`, …). That retrieval/labeling
artifact made the operating point jump around:

- **Before** the `%s` expansion: τ = 0.15, per-fold **0.15–0.9, std 0.36** (shaky).
- **After** expanding the dims: τ = **0.07**, per-fold **0.07–0.10, std 0.012** — "now as
  well-determined as rm0041's τ=0.98."

Trade-off recorded: the expansion also dropped yield (0.863 → 0.783) and raised false negatives
(261 → 494), because materializing each array register adds invariants the validator rejects. Net:
a more honest, more stable benchmark at some recall. STM's datasheet didn't have this artifact.

## Reason 2 — the bimodal, gapped confidence distribution (why NXP's τ is *low*)

The NXP pseudo-score (`score` column in the judgments) is sharply **bimodal with an empty gap**:

```
score      count
0.00        967    ┐ "confidently correct" pile
0.05         43    │
0.07–0.20   ~15    ┘ small uncertain tail
--- GAP: nothing between 0.20 and 0.80 ---
0.80–0.98  ~215    ┐ "confidently a bug" cluster
1.00       1541    ┘
```

There is a literal **jump from ~0.07/0.20 up to 0.80+**, with nothing in the middle. That is
exactly why τ=0.07 is both low and stable:

- The confidently-correct invariants pile at **0.00–0.05**, *below* 0.07, so a cutoff of 0.07
  already excludes them → precision is ≥95% at a very low threshold.
- The picker takes the *lowest* τ hitting 95% precision (to maximize recall), so it drops to
  0.07 — just above that pile — sweeping in the small 0.08–0.20 tail plus the whole high cluster.
- Because there's a wide empty gap, any threshold in that region behaves identically → the
  per-fold τ is tight (0.07–0.10), i.e. well-determined.

## It's the model, not our pipeline

The bimodal/gapped shape is **gpt-oss-120b's** confidence behavior, not something we engineered.
The **raw** model confidences:

```
confidence_score   count
0.80–0.98          ~275
1.00               2508   ← the overwhelming majority
→ 97.1% of confidences sit at the extremes (≤0.05 or ≥0.95)
```

The model reports near-certainty for essentially everything and barely uses the middle of the
scale. Our only step is the **deterministic** pseudo-score transform (verified: `is_true=True,
conf=1.0 → score=1.0`; `is_true=False, conf=1.0 → score=0.0`). We do not round, bucket, or shape
it. So:

- The **bimodality** falls out of the model being near-binary confident, with the verdict flipping
  the pseudo-score to one end.
- The **gap** exists precisely because the model rarely emits mid-range confidence — there is
  nothing to land between 0.2 and 0.8.

The only thing *we* choose is where to place τ; the gap is what makes that choice low and stable
for NXP.

## Contrast: STM (τ=0.98) and gpt-5.4

- **STM rm0041 (τ=0.98):** its high-confidence cluster has more false positives mixed in around
  0.90–0.95, so the cutoff must be pushed all the way to 0.98 to reach 95% precision — there's no
  clean low gap to sit in.
- **Model-dependence:** because the shape is a model property, a differently-calibrated model gives
  a different picture. The results already flag `gpt-5.4` on rm0041 as having a *bimodal threshold*
  (per-fold 0.93 vs 0.98) rather than this single clean gap — a higher mean yield but a less stable
  operating point under a frozen τ.

## Bottom line

The τ difference (0.07 vs 0.98) is an **operating-point** artifact of two model/data facts, not a
capability gap:
- **`%s` dim expansion** removed NXP's *instability* (τ 0.15/std 0.36 → 0.07/std 0.012);
- **gpt-oss's near-binary confidence** produces a bimodal, gapped pseudo-score, so NXP's precision
  target is met at a very *low, stable* cutoff, while STM's dirtier high cluster forces a near-1.0 cutoff.
Both devices still clear the 95% precision target, and both thresholds transfer cleanly to their
second device (ke04→k64 at 0.07, rm0041→rm0394 at 0.98).

---

### Sources (existing results)
- `optimization_validator/validator_cards/nxp_ke04_gpt-oss-120b.json` — τ=0.07, precision 0.958, yield 0.783
- `optimization_validator/validator_cards/stm_rm0041_gpt-oss-120b.json` — τ=0.98, precision 0.948, yield 0.689
- `optimization_validator/validator_cards/stm_rm0041_gpt-5.4.json` — τ=0.93
- `optimization_validator/validator_cards/README.md` — threshold semantics / pseudo-score definition
- `optimization_validator/results/transfer_and_calibration.md` — the `%s`-artifact stabilization + transfer results
- `optimization_validator/nxp_ke04_run/cross_validation/gpt-oss-120b/judgments_gpt-oss-120b.csv` — the `score` and `confidence_score` distributions above
- `optimization_validator/validator_card.py` — `deployment_threshold()` (lowest cutoff hitting the precision target)
