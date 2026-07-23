# STM rm0041 — validator accuracy, curation & seed variance (A1/A2/B1/E1/E2)

Device: stm/rm0041 (expanded 5,321 invariants, 30% peripheral-stratified corruption, k=5).
Retrieval: OpenEvolve. Access legend: stm. alt_name: on.

## A1 — baseline (gpt-oss-120b, NO curated examples yet)
| metric | value |
|---|---|
| gate precision | 0.9463 |
| yield / recall | 0.7009 |
| sensitivity alpha | 0.7009 |
| specificity beta | 0.9075 |
| F1 | 0.8053 |
| precision@top-decile | 0.942 |
| reviewed / candidates | 2756/5321 |
| real bugs dropped unseen | 1113 |
| pi (within-run identity) | 0.6993 |
| validated precision | 0.9463 |
| usage | 688 calls, 5,344,234 tok, est $1.20 |

## E1 — per-invariant-class (raw is_true judgment)
| key | n | precision | recall (=alpha) | beta |
|---|---|---|---|---|
| access | 2054 | 0.915 | 0.652 | 0.856 |
| address_offset | 200 | 1.000 | 0.942 | 1.000 |
| bit_offset | 1352 | 0.977 | 0.834 | 0.957 |
| bit_width | 1337 | 0.934 | 0.823 | 0.858 |
| reset_value | 189 | 0.991 | 0.821 | 0.982 |
| size | 189 | 0.927 | 0.913 | 0.857 |

Retrieval coverage: 85.8% of invariants. Of 868 false negatives, 360 (41%) are registers NOT in the retrieved context (retrieval gap, not model conservatism).

**Weakest class: access (recall 0.65)** — curated, datasheet-grounded examples target exactly this. **Strongest: address_offset (1.00/0.94).**

## Status
- A1 (baseline), E1, usage/cost: DONE (this file).
- B1 (curation lift): BLOCKED — fill curated_examples/stm.json from curation_candidates_gpt-oss-120b.json (80 candidates), then re-run with --curated-examples.
- A2 (gpt-5.5), C1 (50% corruption), E2 (seed variance): pending.
## A2 — cross-model BASELINE (before curation; gpt-oss=Groq, gpt-5.4=OpenAI)
| model | gate prec | yield | alpha | beta | F1 | est cost |
|---|---|---|---|---|---|---|
| gpt-oss-120b | 0.946 | 0.701 | 0.701 | 0.907 | 0.805 | $1.20 |
| gpt-5.4 | 0.952 | 0.709 | 0.709 | 0.916 | 0.813 | $15.77 |

Near-identical accuracy: **gpt-5.4 edges gpt-oss-120b by ~0.006-0.008 on precision/yield/F1, at ~13x the cost** ($15.77 vs $1.20). gpt-5.4 emitted 0 reasoning tokens and OpenAI reported 0 cached tokens (prompt caching did not engage).

## B1 / A2 — curation lift (baseline vs curated; gate precision target 0.95, N=8 examples/fold)
10 curated datasheet-grounded examples (2 per fold), per-fold-excluded + equalized. Single seed (0); E2 pending.

| model | precision base->cur | yield(alpha) base->cur | F1 base->cur | beta base->cur | cost baseline / curated pass |
|---|---|---|---|---|---|
| gpt-oss-120b | 0.946 -> 0.948 | 0.706 -> 0.689 (-0.017) | 0.809 -> 0.798 (-0.011) | 0.907 -> 0.912 | $1.21 / $1.55 |
| gpt-5.4 | 0.951 -> 0.951 | 0.708 -> 0.743 (+0.035) | 0.812 -> 0.835 (+0.023) | 0.916 -> 0.911 | $15.53 / $14.45 |

**Cost note:** the curation *experiment* runs two full passes over the benchmark — pass 1
(baseline, which also exports the curation candidates) + pass 2 (curated) — so its total is
their sum ($2.76 gpt-oss, $29.98 gpt-5.4). The paired per-pass costs above are taken from that
single experiment: **baseline = pass 1, curated = pass 2**. The curated-pass figure is what
*deploying* the curated validator actually costs (one pass); the doubled total is only the cost
to *measure* the lift. (For gpt-5.4 the curated pass is slightly cheaper than baseline because
its shared curated-example prefix caches at a 10x discount, $0.25 vs $2.50 / 1M input.)

**Curation is model-dependent:** it lifts gpt-5.4 yield +3.5pts / F1 +0.023 at constant precision, but marginally hurts gpt-oss-120b (-1.7 yield). For gpt-5.4 the raw-acceptance gains came from bit_offset/bit_width (+0.9/+1.8pts), not the access-targeted class (flat) — the grounded bit-tables raised confidence on bit-field facts rather than teaching access notation specifically.
## E2 — seed variance (3 seeds: 0,1,2; curated config, gate precision ~0.95)

| model | baseline yield | curated yield | curation Δyield | ΔF1 | Δyield range |
|---|---|---|---|---|---|
| gpt-oss-120b | 0.710±0.006 | 0.698±0.007 | -0.012±0.009 | -0.008±0.006 | [-0.020, +0.000] |
| gpt-5.4 | 0.737±0.051 | 0.763±0.061 | +0.026±0.014 | +0.016±0.008 | [+0.006, +0.037] |

**Curation lift is model-dependent and consistent in sign across all 3 seeds:** real for gpt-5.4 (Δyield always positive, +0.026±0.014) and absent for gpt-oss-120b (never positive, -0.012±0.009) — the noise floor (~±0.01 yield) is well below the gpt-5.4 lift. **Caveat: gpt-5.4 yield is far more seed-variable** (baseline ±0.051 vs gpt-oss ±0.006) — higher mean yield but a much less stable operating point under a frozen threshold.
