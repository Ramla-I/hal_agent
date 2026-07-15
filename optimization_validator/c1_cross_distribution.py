"""C1 — cross-distribution pi test (Rogan-Gladen instrument transfer).

WHY THIS EXISTS. Within a single run, the Rogan-Gladen prevalence estimate pi is an
algebraic IDENTITY: calibrate() reads alpha, beta and the acceptance rate r_hat off the
*same* confusion matrix, so it recovers that run's own prevalence by construction and
proves nothing. The real scientific claim is that alpha (sensitivity) and beta
(specificity) are properties of the VALIDATOR — the noisy labeler — and do NOT depend on
the prevalence pi. If that holds, we can measure the instrument (alpha, beta) at one
corruption rate and use it to correct a benchmark at a DIFFERENT rate.

WHAT C1 DOES. Freeze (alpha, beta) from a "calibration" run (e.g. 30% corruption) and
apply them to the acceptance rate r_hat of an "apply" run at a different rate (e.g. 50%):

    pi_hat = (r_hat_apply - (1 - beta_calib)) / (alpha_calib + beta_calib - 1)

then check pi_hat recovers the apply run's TRUE prevalence (1 - corruption_fraction).
It also reports alpha/beta measured on each run so you can see directly whether the
instrument is prevalence-stable (alpha_30 ~= alpha_50, beta_30 ~= beta_50).

OPERATING POINT. alpha/beta/r_hat are all threshold-dependent, and Rogan-Gladen needs
them at ONE consistent operating point. We use the RAW labeler — V=1 iff `is_true`, the
Validator's own accept/reject decision — which is threshold-independent (no gate tuning),
i.e. the pure noisy-labeler. Read straight from judgments_<model>.csv (columns is_true,
is_correct). Both runs must use the SAME Validator config (model + curated examples);
only the corruption fraction differs.

CONVENTIONS. C=1 is a genuinely-correct invariant (is_correct=True); V=1 is Validator
accept (is_true=True). So prevalence pi = P(C=1) = 1 - corruption_fraction (at 30%
corruption pi=0.70; at 50%, pi=0.50).

Usage (host python; no APIs, no pandas):
    python3 optimization_validator/c1_cross_distribution.py \
        --calib-judgments <30pct_run>/judgments_gpt-oss-120b.csv \
        --apply-judgments <50pct_run>/judgments_gpt-oss-120b.csv \
        [--out c1_result.json]
The true prevalence of each run is read from its is_correct column (no need to pass the
corruption fraction).
"""
from __future__ import annotations

import argparse
import csv
import json
from typing import Optional


def _as_bool(v) -> bool:
    return str(v).strip().lower() == "true"


def instrument_from_labels(is_true, is_correct) -> dict:
    """Raw (V=1 iff is_true) confusion + noisy-labeler stats from paired label lists.

    Returns alpha (sensitivity P(V=1|C=1)), beta (specificity P(V=0|C=0)), the observed
    acceptance rate r_hat = P(V=1), and the true prevalence pi_true = P(C=1), plus counts.
    alpha/beta are None when their class is empty.
    """
    tp = fp = tn = fn = 0
    for v, c in zip(is_true, is_correct):
        if c and v:
            tp += 1
        elif (not c) and v:
            fp += 1
        elif (not c) and (not v):
            tn += 1
        else:
            fn += 1
    n = tp + fp + tn + fn
    pos = tp + fn        # C=1
    neg = tn + fp        # C=0
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn, "n": n,
        "alpha": (tp / pos) if pos else None,      # sensitivity  P(V=1|C=1)
        "beta": (tn / neg) if neg else None,       # specificity  P(V=0|C=0)
        "r_hat": ((tp + fp) / n) if n else 0.0,    # acceptance rate P(V=1)
        "pi_true": (pos / n) if n else 0.0,        # true prevalence P(C=1)
    }


def rogan_gladen(r_hat: float, alpha: Optional[float], beta: Optional[float],
                 margin: float = 1e-6) -> dict:
    """Invert r_hat = alpha*pi + (1-beta)*(1-pi) for pi, using a FOREIGN (alpha, beta).

    Returns pi_raw (unclamped), pi (clamped to [0,1]), and identifiable
    (alpha+beta-1 > margin — the labeler must beat random for the inversion to be stable).
    """
    if alpha is None or beta is None:
        return {"pi_raw": None, "pi": None, "identifiable": False,
                "note": "alpha or beta undefined (empty class in calibration run)"}
    denom = alpha + beta - 1.0
    if denom <= margin:
        return {"pi_raw": None, "pi": None, "identifiable": False,
                "note": f"alpha+beta-1={denom:.4f} <= {margin}: not identifiable (labeler ~ random)"}
    pi_raw = (r_hat - (1.0 - beta)) / denom
    return {"pi_raw": pi_raw, "pi": max(0.0, min(1.0, pi_raw)), "identifiable": True, "note": ""}


def read_judgments(path: str):
    """Read (is_true, is_correct) boolean lists from a judgments_<model>.csv."""
    is_true, is_correct = [], []
    with open(path, newline="") as fh:
        r = csv.DictReader(fh)
        if r.fieldnames is None or "is_true" not in r.fieldnames or "is_correct" not in r.fieldnames:
            raise ValueError(f"{path}: expected columns is_true, is_correct (got {r.fieldnames})")
        for row in r:
            is_true.append(_as_bool(row["is_true"]))
            is_correct.append(_as_bool(row["is_correct"]))
    return is_true, is_correct


def cross_distribution(calib_labels, apply_labels) -> dict:
    """Freeze the instrument from calib, apply it to apply's acceptance rate.

    Each *_labels is (is_true_list, is_correct_list). Returns the two per-run instruments,
    the cross-applied pi_hat and its error vs the apply run's true prevalence, and the
    instrument-stability deltas (|alpha_calib - alpha_apply|, same for beta).
    """
    calib = instrument_from_labels(*calib_labels)
    apply = instrument_from_labels(*apply_labels)
    rg = rogan_gladen(apply["r_hat"], calib["alpha"], calib["beta"])
    pi_hat = rg["pi"]
    return {
        "calibration_run": calib,
        "apply_run": apply,
        "pi_hat_cross": pi_hat,                 # apply's prevalence, via calib's instrument
        "pi_true_apply": apply["pi_true"],
        "pi_error": (abs(pi_hat - apply["pi_true"]) if pi_hat is not None else None),
        "identifiable": rg["identifiable"],
        "note": rg["note"],
        "instrument_stability": {
            "alpha_calib": calib["alpha"], "alpha_apply": apply["alpha"],
            "alpha_abs_delta": (abs(calib["alpha"] - apply["alpha"])
                                if calib["alpha"] is not None and apply["alpha"] is not None else None),
            "beta_calib": calib["beta"], "beta_apply": apply["beta"],
            "beta_abs_delta": (abs(calib["beta"] - apply["beta"])
                               if calib["beta"] is not None and apply["beta"] is not None else None),
        },
    }


def _fmt(x, nd=3):
    return "None" if x is None else f"{x:.{nd}f}"


def main():
    ap = argparse.ArgumentParser(description="C1 cross-distribution pi test (Rogan-Gladen transfer)")
    ap.add_argument("--calib-judgments", required=True,
                    help="judgments_<model>.csv of the run whose (alpha,beta) is frozen (e.g. 30%)")
    ap.add_argument("--apply-judgments", required=True,
                    help="judgments_<model>.csv of the different-rate run to correct (e.g. 50%)")
    ap.add_argument("--out", default=None, help="optional path to write the result JSON")
    args = ap.parse_args()

    calib_labels = read_judgments(args.calib_judgments)
    apply_labels = read_judgments(args.apply_judgments)
    # Forward: freeze calib instrument, recover apply's prevalence. Reverse for symmetry.
    fwd = cross_distribution(calib_labels, apply_labels)
    rev = cross_distribution(apply_labels, calib_labels)

    c, a = fwd["calibration_run"], fwd["apply_run"]
    print("C1 — cross-distribution pi (Rogan-Gladen instrument transfer)")
    print(f"  calibration run: n={c['n']}  pi_true={_fmt(c['pi_true'])}  "
          f"alpha={_fmt(c['alpha'])}  beta={_fmt(c['beta'])}  r_hat={_fmt(c['r_hat'])}")
    print(f"  apply run:       n={a['n']}  pi_true={_fmt(a['pi_true'])}  "
          f"alpha={_fmt(a['alpha'])}  beta={_fmt(a['beta'])}  r_hat={_fmt(a['r_hat'])}")
    st = fwd["instrument_stability"]
    print(f"  instrument stability: d_alpha={_fmt(st['alpha_abs_delta'])}  d_beta={_fmt(st['beta_abs_delta'])}")
    print(f"  FORWARD (calib->apply): pi_hat={_fmt(fwd['pi_hat_cross'])} vs true "
          f"{_fmt(fwd['pi_true_apply'])}  |error|={_fmt(fwd['pi_error'])}  "
          f"identifiable={fwd['identifiable']}{('  ['+fwd['note']+']') if fwd['note'] else ''}")
    print(f"  REVERSE (apply->calib): pi_hat={_fmt(rev['pi_hat_cross'])} vs true "
          f"{_fmt(rev['pi_true_apply'])}  |error|={_fmt(rev['pi_error'])}  "
          f"identifiable={rev['identifiable']}{('  ['+rev['note']+']') if rev['note'] else ''}")

    if args.out:
        with open(args.out, "w") as fh:
            json.dump({"forward": fwd, "reverse": rev}, fh, indent=2)
        print(f"  wrote {args.out}")


if __name__ == "__main__":
    main()
