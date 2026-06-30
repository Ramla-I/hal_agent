"""Build a per-device **validator card** — the frozen, transferable calibration of the
Validator measured on a development device, and the single DEPLOYMENT THRESHOLD to apply
on the vendor's *unverified* devices.

Why this file exists: the cross-validation run reports per-fold thresholds and held-out
metrics for *measurement*. Deployment needs one frozen number and a few summary stats.
The card captures exactly what describes the Validator and amortizes per vendor:

  * `deployment_threshold` — the lowest pseudo-score cutoff that hits the precision target
    on the FULL labeled benchmark of the dev device. Freeze it and apply on other devices:
    on an unverified device, a candidate enters the human review queue iff its pseudo-score
    >= this threshold, so it directly sets HOW MANY rows get reviewed.
  * `instrument` — alpha (sensitivity) / beta (specificity): the noisy-labeler properties
    assumed to transfer across the vendor's devices (used for Rogan-Gladen on new devices).
  * `threshold_stability` — the per-fold tau spread; tight => the operating point is well
    determined, scattered => shaky.
  * `config_to_freeze` — model + curated-examples file + retrieval + target, i.e. the rest
    of the deployable validator config.
  * `measured_on_dev_device` — the held-out estimate you expect to roughly hold on transfer.

Run (host python, no Docker):
    python3 optimization_validator/validator_card.py \
        optimization_validator/stmrm0041_run/curated/gpt-5.4 \
        --vendor stm --device rm0041 --target-precision 0.95
-> writes optimization_validator/validator_cards/<vendor>_<device>_<model>.json
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import statistics


def _confusion(scores, golds, tau):
    tp = fp = tn = fn = 0
    for s, g in zip(scores, golds):
        v1 = s >= tau
        if g and v1:
            tp += 1
        elif (not g) and v1:
            fp += 1
        elif (not g) and (not v1):
            tn += 1
        else:
            fn += 1
    return tp, fp, tn, fn


def deployment_threshold(scores, golds, target_precision):
    """Lowest pseudo-score cutoff whose precision >= target on the FULL data, maximising
    recall (ties -> lower tau). Falls back to the highest-precision cutoff if unreachable.
    Mirrors cross_validate.tune_threshold_precision, but dependency-free."""
    grid = [0.0] + sorted(set(scores)) + [1.0001]
    best = None       # (recall, -tau)
    fallback = None   # (precision, recall)
    for tau in grid:
        tp, fp, tn, fn = _confusion(scores, golds, tau)
        if tp + fp == 0:
            continue
        prec = tp / (tp + fp)
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        if fallback is None or (prec, rec) > fallback[0]:
            fallback = ((prec, rec), tau)
        if prec >= target_precision:
            key = (rec, -tau)
            if best is None or key > best[0]:
                best = (key, tau)
    return best[1] if best else (fallback[1] if fallback else 1.0001)


def _read_judgments(run_dir, model):
    scores, golds = [], []
    with open(os.path.join(run_dir, f"judgments_{model}.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                scores.append(float(r["score"]))
            except (KeyError, ValueError):
                continue
            golds.append(str(r.get("is_correct", "")).strip().lower() == "true")
    return scores, golds


def _read_fold_taus(run_dir, model):
    path = os.path.join(run_dir, f"per_fold_{model}.csv")
    if not os.path.exists(path):
        return []
    out = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                out.append(float(r["tau"]))
            except (KeyError, ValueError):
                pass
    return out


def build_card(run_dir, vendor, device, target_precision=0.95, model=None):
    if model is None:
        sm = glob.glob(os.path.join(run_dir, "summary_*.json"))
        if not sm:
            raise FileNotFoundError(f"no summary_*.json in {run_dir}")
        model = os.path.basename(sm[0])[len("summary_"):-len(".json")]
    summary = json.load(open(os.path.join(run_dir, f"summary_{model}.json")))
    # the deployed config is the curated pass when it ran, else baseline
    block = "curated" if summary.get("operational", {}).get("curated_examples_used") else "baseline"
    conf = summary[block]["aggregated_confusion"]
    calib = summary[block]["calibration"]
    op = summary.get("operational", {})
    usage = summary.get("usage", {})

    scores, golds = _read_judgments(run_dir, model)
    tau = deployment_threshold(scores, golds, target_precision)
    fold_taus = _read_fold_taus(run_dir, model)

    card = {
        "vendor": vendor,
        "device": device,
        "model": model,
        "config_to_freeze": {
            "curated_examples": op.get("curated_examples_used") and f"curated_examples/{vendor}.json" or None,
            "use_alt_name": op.get("use_alt_name"),
            "objective": op.get("objective"),
            "target_precision": op.get("target_precision", target_precision),
        },
        # THE number to apply on unverified devices (sets the review-queue size):
        "deployment_threshold": round(tau, 4),
        "threshold_stability": {
            "per_fold_tau": [round(t, 4) for t in fold_taus],
            "min": round(min(fold_taus), 4) if fold_taus else None,
            "max": round(max(fold_taus), 4) if fold_taus else None,
            "std": round(statistics.pstdev(fold_taus), 4) if len(fold_taus) > 1 else 0.0,
        },
        # transferable noisy-labeler properties (assumed ~constant across the vendor):
        "instrument": {
            "alpha_sensitivity": conf.get("alpha"),
            "beta_specificity": conf.get("beta"),
        },
        # held-out estimate you expect to roughly hold on transfer:
        "measured_on_dev_device": {
            "gate_precision": conf.get("precision"),
            "yield_recall": conf.get("recall"),
            "f1": conf.get("f1"),
            "validated_precision": calib.get("validated_precision"),
            "n_invariants": conf.get("tp", 0) + conf.get("fp", 0) + conf.get("tn", 0) + conf.get("fn", 0),
            "config": block,
        },
        "provenance": {
            "source_run": run_dir,
            "seed": op.get("seed"),
            "corruption_fraction": op.get("corruption_fraction"),
            "est_cost_usd": usage.get("est_cost_usd"),
            "note": "Single-seed estimate unless a seed-variance (E2) range is recorded.",
        },
    }
    return card, model


def main():
    ap = argparse.ArgumentParser(description="Build a per-device validator card")
    ap.add_argument("run_dir", help="a model run dir, e.g. stmrm0041_run/curated/gpt-5.4")
    ap.add_argument("--vendor", required=True)
    ap.add_argument("--device", required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--target-precision", type=float, default=0.95)
    ap.add_argument("--out-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                      "validator_cards"))
    args = ap.parse_args()
    card, model = build_card(args.run_dir, args.vendor, args.device, args.target_precision, args.model)
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, f"{args.vendor}_{args.device}_{model}.json")
    with open(out, "w") as fh:
        json.dump(card, fh, indent=2)
    print(f"wrote {out}")
    print(f"  deployment_threshold = {card['deployment_threshold']}  "
          f"(per-fold tau spread {card['threshold_stability']['min']}–{card['threshold_stability']['max']}, "
          f"std {card['threshold_stability']['std']})")
    print(f"  alpha={card['instrument']['alpha_sensitivity']}  beta={card['instrument']['beta_specificity']}  "
          f"gate_precision={card['measured_on_dev_device']['gate_precision']}  "
          f"yield={card['measured_on_dev_device']['yield_recall']}")


if __name__ == "__main__":
    main()
