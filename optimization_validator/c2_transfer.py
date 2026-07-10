"""C2 — per-vendor / cross-family transfer of the frozen Validator calibration.

HYPOTHESIS. The Validator's operating point amortizes across a vendor's devices: the
evolved OpenEvolve retrieval program, the deployment threshold tau, and the noisy-labeler
instrument (alpha, beta) measured on device 1 transfer to device 2 of the SAME vendor
without re-tuning. So on device 2 you should be able to FREEZE device 1's tau and still
hit the precision target, at a yield close to device 1's.

WHAT C2 CHECKS. Given device 2's per-row judgments (score, is_correct) and device 1's
FROZEN tau, apply the gate on device 2 (accept iff score >= tau_frozen) and measure the
resulting precision and yield/recall. Compare against:
  * the target precision (did the frozen tau still clear it on device 2?), and
  * device 2's OWN re-tuned operating point (the ceiling you'd get by recalibrating) — so
    you can see how much, if anything, transfer costs vs. per-device tuning.

CONVENTIONS (identical to the harness). C=1 is a genuinely-correct invariant
(is_correct=True); V=1 is Validator accept (score >= tau). precision = P(C=1 | V=1) over
the accepted pile; yield/recall = fraction of the real positives kept.

Both devices must use the SAME frozen config (model, curated examples, and here the SAME
evolved OpenEvolve program) — only the device (and its datasheet) differs. Read device 2's
judgments_<model>.csv (columns score, is_correct).

Usage (host python; no APIs, no pandas):
    python3 optimization_validator/c2_transfer.py \
        --judgments <rm0394_run>/judgments_gpt-oss-120b.csv \
        --frozen-card optimization_validator/validator_cards/stm_rm0041_gpt-oss-120b.json \
        [--target-precision 0.95] [--out c2_result.json]
Or pass the threshold directly with --frozen-threshold 0.98 instead of --frozen-card.
"""
from __future__ import annotations

import argparse
import csv
import json
from typing import Optional


def _as_bool(v) -> bool:
    return str(v).strip().lower() == "true"


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


def metrics_at(scores, golds, tau) -> dict:
    """Gate metrics when accepting iff score >= tau."""
    tp, fp, tn, fn = _confusion(scores, golds, tau)
    n = tp + fp + tn + fn
    reviewed = tp + fp
    pos = tp + fn
    return {
        "tau": tau,
        "precision": (tp / reviewed) if reviewed else None,   # P(C=1 | V=1)
        "yield_recall": (tp / pos) if pos else None,          # fraction of real positives kept
        "n_reviewed": reviewed, "n_total": n,
        "true_positives": tp, "false_positives": fp, "false_negatives": fn, "true_negatives": tn,
    }


def best_tau_at_precision(scores, golds, target_precision) -> float:
    """Device's OWN operating point: lowest tau whose precision >= target, max recall
    (ties -> lower tau); fall back to the highest-precision tau if unreachable.
    Mirrors tune_threshold_precision / validator_card, dependency-free."""
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


def read_judgments(path: str):
    """Read (score, is_correct) from a judgments_<model>.csv."""
    scores, golds = [], []
    with open(path, newline="") as fh:
        r = csv.DictReader(fh)
        if r.fieldnames is None or "score" not in r.fieldnames or "is_correct" not in r.fieldnames:
            raise ValueError(f"{path}: expected columns score, is_correct (got {r.fieldnames})")
        for row in r:
            try:
                scores.append(float(row["score"]))
            except (KeyError, ValueError):
                continue
            golds.append(_as_bool(row["is_correct"]))
    return scores, golds


def transfer_report(scores, golds, frozen_tau, target_precision=0.95, tol=0.01) -> dict:
    """Apply the FROZEN tau to this device and compare to its own re-tuned operating point.

    `tol` is the "no meaningful cost" tolerance for the amortization verdict (default 0.01,
    i.e. 1 percentage point) — small measurement-scale gaps don't count as a transfer cost.
    """
    frozen = metrics_at(scores, golds, frozen_tau)
    own_tau = best_tau_at_precision(scores, golds, target_precision)
    own = metrics_at(scores, golds, own_tau)
    reaches_target = frozen["precision"] is not None and frozen["precision"] >= target_precision
    # gap = how much BETTER re-tuning does than freezing (positive => freezing left something
    # on the table; <= 0 => freezing is as good or better).
    p_gap = ((own["precision"] - frozen["precision"])
             if own["precision"] is not None and frozen["precision"] is not None else None)
    y_gap = ((own["yield_recall"] - frozen["yield_recall"])
             if own["yield_recall"] is not None and frozen["yield_recall"] is not None else None)
    # The amortization claim: freezing device-1's tau costs (almost) nothing vs. per-device
    # tuning on device-2. Distinct from whether device-2 can hit the target at all (a
    # device-hardness question) — device-2's ceiling may sit below target regardless.
    amortization_holds = (p_gap is not None and y_gap is not None
                          and p_gap <= tol and y_gap <= tol)
    return {
        "frozen_tau": frozen_tau,
        "target_precision": target_precision,
        "amortization_tol": tol,
        # frozen tau achieves the precision target on device-2 (operational go/no-go):
        "reaches_target": reaches_target,
        # frozen tau is no worse than re-tuning on device-2 (the amortization claim):
        "amortization_holds": amortization_holds,
        "frozen_applied": frozen,                         # metrics at device 1's tau
        "device_own_retuned": own,                        # metrics if you recalibrated on device 2
        "precision_gap_vs_own": p_gap,
        "yield_gap_vs_own": y_gap,
    }


def _fmt(x, nd=3):
    return "None" if x is None else f"{x:.{nd}f}"


def main():
    ap = argparse.ArgumentParser(description="C2 per-vendor transfer check (freeze device-1 tau, apply to device-2)")
    ap.add_argument("--judgments", required=True, help="device-2 judgments_<model>.csv")
    ap.add_argument("--frozen-threshold", type=float, default=None, help="device-1 frozen tau")
    ap.add_argument("--frozen-card", default=None,
                    help="device-1 validator card JSON (reads deployment_threshold)")
    ap.add_argument("--target-precision", type=float, default=0.95)
    ap.add_argument("--amortization-tol", type=float, default=0.01,
                    help="tolerance (default 0.01) below which a precision/yield gap vs "
                         "re-tuning is treated as no transfer cost")
    ap.add_argument("--out", default=None, help="optional path to write the result JSON")
    args = ap.parse_args()

    if args.frozen_threshold is None and args.frozen_card is None:
        ap.error("provide --frozen-threshold or --frozen-card")
    frozen_tau = args.frozen_threshold
    if frozen_tau is None:
        card = json.load(open(args.frozen_card))
        frozen_tau = card["deployment_threshold"]

    scores, golds = read_judgments(args.judgments)
    rep = transfer_report(scores, golds, frozen_tau, args.target_precision, args.amortization_tol)

    fa, ow = rep["frozen_applied"], rep["device_own_retuned"]
    print("C2 — per-vendor transfer (freeze device-1 tau, apply to device-2)")
    print(f"  device-2: n={fa['n_total']}  target_precision={_fmt(args.target_precision)}")
    print(f"  FROZEN tau={_fmt(frozen_tau)}:  precision={_fmt(fa['precision'])}  "
          f"yield={_fmt(fa['yield_recall'])}  reviewed={fa['n_reviewed']}  "
          f"(tp={fa['true_positives']} fp={fa['false_positives']} fn={fa['false_negatives']})")
    print(f"  device-2 OWN re-tuned tau={_fmt(ow['tau'])}:  precision={_fmt(ow['precision'])}  "
          f"yield={_fmt(ow['yield_recall'])}")
    print(f"  AMORTIZATION HOLDS: {rep['amortization_holds']}  "
          f"(freezing costs d_precision={_fmt(rep['precision_gap_vs_own'])}, "
          f"d_yield={_fmt(rep['yield_gap_vs_own'])} vs re-tuning)")
    print(f"  reaches target precision on device-2: {rep['reaches_target']}  "
          f"(frozen precision {_fmt(fa['precision'])} vs target {_fmt(args.target_precision)}; "
          f"device-2 ceiling is its own precision {_fmt(ow['precision'])})")

    if args.out:
        with open(args.out, "w") as fh:
            json.dump(rep, fh, indent=2)
        print(f"  wrote {args.out}")


if __name__ == "__main__":
    main()
