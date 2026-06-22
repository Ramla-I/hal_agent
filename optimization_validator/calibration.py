"""Calibrate downstream measurements from the Validator's confusion matrix.

Implements the paper section "Calibrating Downstream Measurements". The Validator is
a noisy binary labeler with measured sensitivity/specificity; treating its judgments
as ground truth biases estimates of TRIE's extraction quality, so we invert the
noisy-label model (Rogan-Gladen).

Confusion matrix (C = true correctness, V = Validator judgment):

            C = 1     C = 0
    V = 1    TP        FP        (= 1-beta column mass on C=0)
    V = 0    FN        TN

    alpha = P(V=1 | C=1) = TP / (TP + FN)   sensitivity (true-positive rate)
    beta  = P(V=0 | C=0) = TN / (TN + FP)   specificity (true-negative rate)

Given the observed acceptance rate r_hat = P(V=1):

    r_hat = alpha * pi + (1 - beta) * (1 - pi)
    =>  pi = (r_hat - (1 - beta)) / (alpha + beta - 1)          (Rogan-Gladen)

pi = P(C=1) is the *intrinsic* fraction of correct invariants TRIE produces, corrected
for Validator error. The validated-set precision (fraction of accepted invariants that
are truly correct) follows from Bayes' rule:

    P(C=1 | V=1) = alpha * pi / r_hat

Identifiability: the inversion is valid only when alpha + beta > 1 (Validator better
than random); near alpha + beta = 1 it is unstable. Because alpha, beta, r_hat come
from finite data, pi can land slightly outside [0, 1] — we clamp to [0, 1] for
reporting and flag when clamping occurred.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class ConfusionMatrix:
    tp: int  # V=1, C=1
    fp: int  # V=1, C=0
    tn: int  # V=0, C=0
    fn: int  # V=0, C=1

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    def __add__(self, other: "ConfusionMatrix") -> "ConfusionMatrix":
        return ConfusionMatrix(
            tp=self.tp + other.tp,
            fp=self.fp + other.fp,
            tn=self.tn + other.tn,
            fn=self.fn + other.fn,
        )

    # --- labeler error rates ------------------------------------------------ #
    @property
    def alpha(self) -> Optional[float]:
        """Sensitivity P(V=1|C=1) = TP / (TP + FN). None if no positives."""
        denom = self.tp + self.fn
        return self.tp / denom if denom > 0 else None

    @property
    def beta(self) -> Optional[float]:
        """Specificity P(V=0|C=0) = TN / (TN + FP). None if no negatives."""
        denom = self.tn + self.fp
        return self.tn / denom if denom > 0 else None

    # --- standard quality metrics ------------------------------------------ #
    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.total if self.total > 0 else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(
            alpha=self.alpha,
            beta=self.beta,
            precision=self.precision,
            recall=self.recall,
            f1=self.f1,
            accuracy=self.accuracy,
        )
        return d


@dataclass
class CalibrationResult:
    r_hat: float            # observed Validator acceptance rate P(V=1)
    alpha: Optional[float]  # sensitivity
    beta: Optional[float]   # specificity
    pi_raw: Optional[float]      # Rogan-Gladen estimate before clamping
    pi: Optional[float]          # clamped to [0, 1]
    validated_precision: Optional[float]  # P(C=1 | V=1)
    identifiable: bool      # alpha + beta > 1 (with margin)
    clamped: bool           # pi_raw fell outside [0, 1]
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def calibrate(cm: ConfusionMatrix, identifiability_margin: float = 1e-3) -> CalibrationResult:
    """Invert the noisy-label model to recover pi and the validated-set precision.

    `cm` is the (aggregated) Validator confusion matrix measured on the benchmark.
    The acceptance rate r_hat is read off the same matrix: P(V=1) = (TP+FP)/N.
    """
    alpha = cm.alpha
    beta = cm.beta
    total = cm.total
    r_hat = (cm.tp + cm.fp) / total if total > 0 else 0.0

    if alpha is None or beta is None:
        return CalibrationResult(
            r_hat=r_hat, alpha=alpha, beta=beta, pi_raw=None, pi=None,
            validated_precision=None, identifiable=False, clamped=False,
            note="alpha or beta undefined (a class is empty); cannot calibrate",
        )

    denom = alpha + beta - 1
    identifiable = denom > identifiability_margin
    if not identifiable:
        return CalibrationResult(
            r_hat=r_hat, alpha=alpha, beta=beta, pi_raw=None, pi=None,
            validated_precision=None, identifiable=False, clamped=False,
            note=f"alpha+beta={alpha + beta:.4f} <= 1 (+margin); inversion unstable/undefined",
        )

    pi_raw = (r_hat - (1 - beta)) / denom
    pi = min(1.0, max(0.0, pi_raw))
    clamped = pi != pi_raw

    # Validated-set precision via Bayes: P(C=1|V=1) = alpha*pi / r_hat.
    # Use the clamped pi so the reported precision stays in [0,1]; if nothing was
    # accepted (r_hat == 0) precision is undefined.
    if r_hat > 0:
        validated_precision = min(1.0, max(0.0, alpha * pi / r_hat))
    else:
        validated_precision = None

    note = ""
    if clamped:
        note = f"pi_raw={pi_raw:.4f} outside [0,1]; clamped to {pi:.4f}"
    return CalibrationResult(
        r_hat=r_hat, alpha=alpha, beta=beta, pi_raw=pi_raw, pi=pi,
        validated_precision=validated_precision, identifiable=True,
        clamped=clamped, note=note,
    )
