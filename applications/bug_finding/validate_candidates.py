"""Loop the datasheet validator over bug candidates and record its verdict.

The validator judges whether the GENERATOR's value for an invariant is true
against the datasheet. For a bug candidate (svd_value != generator_value):

    validator says generator value TRUE  -> the SVD is wrong        -> TP (real bug)
    validator says generator value FALSE -> the generator hallucinated -> FP

We validate only the candidates (review rows with blank ``status``) using the
generator's value, apply the model's calibrated card threshold, and write two
columns back into the consolidated ``{rm}_review.csv``:
  * ``validator_verdict``    — TP / FP / "" (abstain: leans-true but below threshold, or unclassified)
  * ``validator_confidence`` — the validator's raw confidence (so borderline rows are visible)

``tp_fp`` is NEVER touched — the verdict is advisory; the human still labels.

Stdlib only (csv/glob/json/os): host-testable without the LLM/Docker toolchain.
"""
from __future__ import annotations

import csv
import glob
import json
import os
from typing import Optional

# Fallback threshold when no validator_card exists for a run's model (flagged
# uncalibrated). Conservative: only very-high-confidence trues become TP.
DEFAULT_THRESHOLD = 0.9

# The two columns this stage adds to the consolidated review CSV.
VALIDATOR_COLS = ("validator_verdict", "validator_confidence")


def candidate_invariants(review_csv_path: str) -> list[dict]:
    """Invariant dicts for just the bug candidates (blank status) in a
    consolidated review CSV. value = the generator's value (what we validate)."""
    out: list[dict] = []
    with open(review_csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("status") or "").strip():        # skip auto-FP (status=false_positive)
                continue
            out.append({
                "peripheral_name": (row.get("peripheral") or "").strip(),
                "register_name": (row.get("register") or "").strip(),
                "field_name": (row.get("field") or "").strip(),
                "key": (row.get("key") or "").strip(),
                "value": (row.get("generator_value") or "").strip(),
            })
    return out


def load_card(vendor: str, device: str, model: str,
              cards_dir: str) -> tuple[Optional[dict], str]:
    """Return (card, calibrated_for). Prefer an exact {vendor}_{device}_{model}
    card; else fall back to any {vendor}_*_{model} card (same vendor+model
    operating point) flagged with the device it was measured on; else None."""
    exact = os.path.join(cards_dir, f"{vendor}_{device}_{model}.json")
    if os.path.isfile(exact):
        return json.load(open(exact, encoding="utf-8")), "exact"
    for path in sorted(glob.glob(os.path.join(cards_dir, f"{vendor}_*_{model}.json"))):
        card = json.load(open(path, encoding="utf-8"))
        return card, f"vendor-default:{card.get('device', os.path.basename(path))}"
    return None, "uncalibrated"


def card_threshold(card: Optional[dict]) -> float:
    if card and card.get("deployment_threshold") is not None:
        return float(card["deployment_threshold"])
    return DEFAULT_THRESHOLD


def decide_verdict(is_true: Optional[bool], confidence: float, threshold: float) -> str:
    """TP if the validator is confidently sure the generator value is true; FP if
    it says false; "" (abstain) if it leans true but under the calibrated
    threshold, or there is no judgement."""
    if is_true is None:
        return ""
    if is_true:
        return "TP" if confidence >= threshold else ""
    return "FP"


def _parse_bool(v) -> Optional[bool]:
    s = str(v).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


def _load_classification(classification_csv_path: str) -> dict[tuple, tuple]:
    """(peripheral,register,field,key,value) -> (is_true, confidence)."""
    out: dict[tuple, tuple] = {}
    if not os.path.isfile(classification_csv_path):
        return out
    with open(classification_csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (
                (r.get("peripheral_name") or "").strip(),
                (r.get("register_name") or "").strip(),
                (r.get("field_name") or "").strip(),
                (r.get("key") or "").strip(),
                (r.get("value") or "").strip(),
            )
            try:
                conf = float(r.get("confidence_score") or 0.0)
            except ValueError:
                conf = 0.0
            out[key] = (_parse_bool(r.get("agent_judgement")), conf)
    return out


def apply_verdicts(review_csv_path: str, classification_csv_path: str,
                   threshold: float) -> dict:
    """Write validator_verdict + validator_confidence into the review CSV for
    each candidate, preserving tp_fp and every other cell. Returns counts."""
    classifications = _load_classification(classification_csv_path)

    with open(review_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    new_cols = [c for c in VALIDATOR_COLS if c not in fields]
    if new_cols:                                       # place them right before tp_fp (canonical order)
        if "tp_fp" in fields:
            fields[fields.index("tp_fp"):fields.index("tp_fp")] = new_cols
        else:
            fields.extend(new_cols)

    counts = {"TP": 0, "FP": 0, "abstain": 0, "unmatched": 0, "candidates": 0}
    for row in rows:
        if (row.get("status") or "").strip():            # auto-FP: leave validator cols blank
            row.setdefault("validator_verdict", "")
            row.setdefault("validator_confidence", "")
            continue
        counts["candidates"] += 1
        ck = ((row.get("peripheral") or "").strip(), (row.get("register") or "").strip(),
              (row.get("field") or "").strip(), (row.get("key") or "").strip(),
              (row.get("generator_value") or "").strip())
        if ck not in classifications:
            row["validator_verdict"] = ""
            row["validator_confidence"] = ""
            counts["unmatched"] += 1
            continue
        is_true, conf = classifications[ck]
        verdict = decide_verdict(is_true, conf, threshold)
        row["validator_verdict"] = verdict
        row["validator_confidence"] = f"{conf:.2f}"
        counts["TP" if verdict == "TP" else "FP" if verdict == "FP" else "abstain"] += 1

    tmp = review_csv_path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    os.replace(tmp, review_csv_path)
    return counts
