"""Offline tests for the Validator cross-validation building blocks.

No network / no LLM. Run in the project container:
    scripts/docker_run.sh run -m optimization_validator.tests.test_offline
"""

from __future__ import annotations

import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd

from optimization_validator.corruption import (
    ACCESS_VALUES, COMMON_SIZES, build_register_contexts, corrupt_row, corrupt_value, corrupt_field_name,
)
from optimization_validator.kfold import load_verified, build_corrupted_benchmark, assign_folds
from optimization_validator.calibration import ConfusionMatrix, calibrate
from optimization_validator.cross_validate import (
    confusion_at, tune_threshold, tune_threshold_precision, make_tuner,
    build_review_queue, precision_at_k_table, reliability_table,
)

VERIFIED = "verified_datasheet/stm/rm0041_stm32f100.csv"
_HEX_RE = re.compile(r"^0x[0-9a-fA-F]+$")

_failures = []


def check(cond, msg):
    if not cond:
        _failures.append(msg)
        print(f"  FAIL: {msg}")
    else:
        print(f"  ok:   {msg}")


def test_corruption_realism():
    print("\n== corruption realism ==")
    df = load_verified(VERIFIED)
    contexts = build_register_contexts(df)
    rng = random.Random(7)

    # Corrupt every row's VALUE and check per-key constraints.
    n = len(df)
    bad_diff = bad_range = 0
    sizes_ok = access_ok = hex_ok = 0
    sizes_tot = access_tot = hex_tot = 0
    for row in df.to_dict("records"):
        ctx = contexts[(row["peripheral"], row["register"])]
        key = row["key"]
        field_name = "" if row["field_name"] is None else str(row["field_name"])
        new = corrupt_value(key, row["correct_value"], ctx, field_name, rng)
        if str(new).strip() == str(row["correct_value"]).strip():
            bad_diff += 1
        if key == "bit_offset" and new.lstrip("-").isdigit():
            size = ctx.size or 32
            if not (0 <= int(new) < size):
                bad_range += 1
        if key == "bit_width" and new.lstrip("-").isdigit():
            size = ctx.size or 32
            if not (1 <= int(new) <= size):
                bad_range += 1
        if key == "size":
            sizes_tot += 1
            if int(new) in COMMON_SIZES and new != row["correct_value"]:
                sizes_ok += 1
        if key == "access":
            access_tot += 1
            if new in ACCESS_VALUES and new != str(row["correct_value"]).strip().lower():
                access_ok += 1
        if key in ("address_offset", "reset_value") and _HEX_RE.match(str(row["correct_value"]).strip()):
            hex_tot += 1
            if _HEX_RE.match(new):
                hex_ok += 1

    check(bad_diff == 0, f"all {n} value corruptions differ from original (violations={bad_diff})")
    check(bad_range == 0, f"bit_offset/width corruptions stay in range (violations={bad_range})")
    check(sizes_ok == sizes_tot, f"size corruptions in {{8,16,32,64}} & changed ({sizes_ok}/{sizes_tot})")
    check(access_ok == access_tot, f"access corruptions valid & changed ({access_ok}/{access_tot})")
    check(hex_ok == hex_tot, f"hex corruptions keep 0x format ({hex_ok}/{hex_tot})")


def test_field_name_corruption():
    print("\n== field-name corruption ==")
    df = load_verified(VERIFIED)
    contexts = build_register_contexts(df)
    rng = random.Random(11)
    field_rows = [r for r in df.to_dict("records") if str(r["field_name"]).strip()]
    changed = sibling = 0
    for r in field_rows[:500]:
        ctx = contexts[(r["peripheral"], r["register"])]
        new = corrupt_field_name(str(r["field_name"]), ctx, rng)
        if new != r["field_name"]:
            changed += 1
        if new in ctx.fields:
            sibling += 1
    check(changed == len(field_rows[:500]), f"every field-name corruption changes the name ({changed}/{len(field_rows[:500])})")
    check(sibling > 0, f"some field-name corruptions reuse a real sibling name ({sibling} of 500)")


def test_folds():
    print("\n== group k-fold ==")
    df = load_verified(VERIFIED)
    bench = build_corrupted_benchmark(df, corruption_fraction=0.30, seed=3)
    frac = (~bench["is_correct"]).mean()
    check(abs(frac - 0.30) < 0.02, f"corruption fraction ~0.30 (got {frac:.3f})")

    k = 5
    folded = assign_folds(bench, k=k, seed=3)
    # Each (peripheral, register) in exactly one fold.
    grp_folds = folded.groupby(["peripheral", "register"])["fold"].nunique()
    check((grp_folds == 1).all(), "each (peripheral, register) maps to exactly one fold")
    # Every fold has both classes.
    both = all(
        (folded[folded["fold"] == f]["is_correct"].sum() > 0)
        and ((~folded[folded["fold"] == f]["is_correct"]).sum() > 0)
        for f in range(k)
    )
    check(both, "every fold contains both positive and negative cases")
    # No corrupted/original pair leakage: replacement means one row per (per,reg,field,key)
    # within a fold partition is structurally guaranteed by grouping registers.
    check(folded["fold"].nunique() == k, f"exactly {k} folds populated")


def test_calibration():
    print("\n== calibration math ==")
    # Construct from pi=0.7, alpha=0.9, beta=0.8, N=1000.
    cm = ConfusionMatrix(tp=630, fp=60, tn=240, fn=70)
    check(abs(cm.alpha - 0.9) < 1e-9, f"alpha=0.9 (got {cm.alpha})")
    check(abs(cm.beta - 0.8) < 1e-9, f"beta=0.8 (got {cm.beta})")
    res = calibrate(cm)
    check(abs(res.r_hat - 0.69) < 1e-9, f"r_hat=0.69 (got {res.r_hat})")
    check(abs(res.pi - 0.7) < 1e-6, f"pi recovered = 0.7 (got {res.pi})")
    check(abs(res.validated_precision - (630 / 690)) < 1e-6,
          f"validated precision = tp/(tp+fp) (got {res.validated_precision})")
    check(res.identifiable and not res.clamped, "identifiable, not clamped")

    # Non-identifiable: alpha+beta = 1 (random labeler).
    bad = calibrate(ConfusionMatrix(tp=50, fp=50, tn=50, fn=50))
    check(not bad.identifiable, "alpha+beta<=1 flagged non-identifiable")

    # Clamping: high acceptance with imperfect labeler pushes pi_raw > 1.
    clamp = calibrate(ConfusionMatrix(tp=98, fp=2, tn=0, fn=0))  # beta undefined -> guard
    # beta undefined here (no negatives); ensure it doesn't crash and reports a note.
    check(clamp.pi is None and not clamp.identifiable, "empty negative class handled gracefully")

    # Proper clamp case: alpha=0.9, beta=0.9, but observed r_hat very high.
    clamp2 = calibrate(ConfusionMatrix(tp=95, fp=4, tn=1, fn=0))
    check(clamp2.pi is not None and 0.0 <= clamp2.pi <= 1.0, f"pi clamped into [0,1] (got {clamp2.pi}, raw {clamp2.pi_raw})")


def test_operational_gate():
    print("\n== operational gate / queue ==")
    # Synthetic scored set: score increasing, with a couple of corrupted (False) rows
    # mixed into the high-score region so precision < 1 unless the gate is raised.
    # scores:   0.1 0.2 0.3 0.4 0.55 0.6 0.7 0.8 0.9 0.95
    # gold(C=1): F   F   F   F    T    F   T   T   T   T     (a False at 0.6 to push tau up)
    scores = [0.1, 0.2, 0.3, 0.4, 0.55, 0.6, 0.7, 0.8, 0.9, 0.95]
    golds  = [False, False, False, False, True, False, True, True, True, True]

    # F1 tuner vs precision tuner should generally differ here.
    tau_f1 = tune_threshold(scores, golds)
    tau_p = tune_threshold_precision(scores, golds, target_precision=1.0)
    cm_p = confusion_at(scores, golds, tau_p)
    check(cm_p.precision >= 1.0 - 1e-9, f"precision-gate hits target=1.0 (got {cm_p.precision:.3f}, tau={tau_p})")
    # At target 1.0 the gate must exclude the False@0.6 -> tau > 0.6, keeping the 4 top Trues.
    check(cm_p.tp == 4 and cm_p.fp == 0, f"precision-gate keeps the 4 clean trues (tp={cm_p.tp}, fp={cm_p.fp})")

    # Yield-maximisation: a looser target should keep at least as many true positives.
    tau_loose = tune_threshold_precision(scores, golds, target_precision=0.8)
    cm_loose = confusion_at(scores, golds, tau_loose)
    check(cm_loose.tp >= cm_p.tp, f"looser target yields >= recall ({cm_loose.tp} >= {cm_p.tp})")
    check(make_tuner("f1")(scores, golds) == tau_f1, "make_tuner('f1') matches tune_threshold")

    # Build a tuned_eval-like frame (one held-out pass): needs score, tau, is_correct,
    # confidence_score + identity cols. Survivors = score >= tau.
    tau = tau_p
    df = pd.DataFrame({
        "score": scores,
        "confidence_score": scores,  # for V=1 survivors score==confidence
        "is_true": [s >= 0.5 for s in scores],
        "is_correct": golds,
        "tau": [tau] * len(scores),
        "fold": [0] * len(scores),
        "peripheral": ["p"] * len(scores),
        "register": [f"r{i}" for i in range(len(scores))],
        "field_name": [""] * len(scores),
        "key": ["address_offset"] * len(scores),
        "correct_value": ["0x0"] * len(scores),
        "corruption_type": ["" if g else "value" for g in golds],
        "reasoning": [""] * len(scores),
    })
    queue = build_review_queue(df)
    check((queue["score"] >= tau).all(), "review queue contains only gate survivors")
    check(list(queue["score"]) == sorted(queue["score"], reverse=True),
          "review queue ranked by score descending")
    check(int(queue["is_correct"].sum()) == cm_p.tp, "queue true-bug count matches gate tp")

    pk = precision_at_k_table(queue)
    check(abs(float(pk.iloc[-1]["precision_at_k"]) - queue["is_correct"].mean()) < 1e-9,
          "precision@100% equals overall queue precision")
    check((pk["precision_at_k"] <= 1.0 + 1e-9).all() and (pk["precision_at_k"] >= -1e-9).all(),
          "precision@k within [0,1]")

    rel = reliability_table(queue, n_bins=10)
    check(int(rel["n"].sum()) == len(queue), "reliability bins cover every survivor")


if __name__ == "__main__":
    test_corruption_realism()
    test_field_name_corruption()
    test_folds()
    test_calibration()
    test_operational_gate()
    print("\n" + ("=" * 50))
    if _failures:
        print(f"{len(_failures)} FAILURE(S):")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL OFFLINE TESTS PASSED")
