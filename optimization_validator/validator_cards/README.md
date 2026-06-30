# Validator cards

One JSON per `(vendor, device, model)` — the **frozen calibration** of the Validator
measured on a *development* device, and the single **deployment threshold** to apply on
that vendor's *unverified* devices. Built by `optimization_validator/validator_card.py`
from a cross-validation run.

## What each field is for

| field | meaning / use |
|---|---|
| **`deployment_threshold`** | The one τ to freeze and apply. On any device, a candidate enters the human review queue iff its pseudo-score `s = conf if is_true else 1−conf` is `≥ τ`. **This is what decides how many rows get reviewed** on an unverified device. Picked as the lowest cutoff hitting the precision target on the *full* dev-device benchmark. |
| `threshold_stability` | The per-fold τ spread. Tight (small std) ⇒ the operating point is well determined; scattered ⇒ shaky. |
| `instrument.alpha/beta` | Sensitivity / specificity — the noisy-labeler properties **assumed to transfer** across the vendor's devices. Use them in Rogan–Gladen to estimate true defect prevalence on an unverified device. |
| `measured_on_dev_device` | Held-out gate precision / yield / F1 — what you **expect to roughly hold** after transfer (precision is the design target; yield is what you get). |
| `config_to_freeze` | The rest of the deployable config (curated examples file, alt_name, objective, target). Freeze together with the threshold. |

## How to use it on an unverified device

1. Run the Validator on the new device with **the same `config_to_freeze`** (model +
   `curated_examples/<vendor>.json` + retrieval + alias) — **all** curated examples, no
   fold exclusion (that was measurement-only).
2. Compute each candidate's pseudo-score and **gate at `deployment_threshold`**: survivors
   (`s ≥ τ`) form the human review queue, ranked by confidence.
3. The queue size *is* "how many rows to review." Expect ≈ the dev-device gate precision
   among them; review top-down to your labour budget.
4. (Optional) Apply `alpha`/`beta` to the raw acceptance rate to estimate how many true
   defects the device has (Rogan–Gladen) — a count, not a selector.

## Caveats

- **Transfer is an assumption** until the C2 device-to-device test confirms it
  (calibrate on device 1 → freeze → check on device 2 of the same vendor).
- Cards are **single-seed** unless a seed-variance (E2) range is recorded in `provenance`.
- One card per model; pick the operating point you'll deploy (e.g. `gpt-5.4` had a lower
  threshold / higher yield than `gpt-oss-120b` at the same precision on rm0041).
