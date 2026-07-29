"""Unit tests for validate_candidates (stdlib only — no LLM/Docker).

Run: python3 applications/bug_finding/tests/test_validate_candidates.py
"""
import csv
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from applications.bug_finding.validate_candidates import (
    candidate_invariants, decide_verdict, apply_verdicts, load_card, card_threshold,
)

TMP = os.environ.get("TMPDIR", "/tmp")

_REVIEW_HEADER = ["RM", "peripheral", "register", "field", "key", "svd_value",
                  "generator_value", "status", "svd_count", "svd_files", "tp_fp", "correct_value"]


def _write_review(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_REVIEW_HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({**{k: "" for k in _REVIEW_HEADER}, **r})


def _write_classification(path, rows):
    hdr = ["peripheral_name", "register_name", "field_name", "key", "value",
           "agent_judgement", "confidence_score"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def test_candidate_invariants():
    p = os.path.join(TMP, "rev_cand.csv")
    _write_review(p, [
        {"peripheral": "flash", "register": "acr", "key": "reset_value", "svd_value": "0x30",
         "generator_value": "0x0", "status": ""},                         # candidate
        {"peripheral": "spi1", "register": "cr2", "key": "reset_value", "svd_value": "0x700",
         "generator_value": "0x0", "status": "false_positive"},           # auto-FP -> excluded
        {"peripheral": "tim1", "register": "smcr", "field": "sms", "key": "bit_offset",
         "svd_value": "0", "generator_value": "3", "status": ""},         # field candidate
    ])
    invs = candidate_invariants(p)
    assert len(invs) == 2, invs
    assert invs[0] == {"peripheral_name": "flash", "register_name": "acr", "field_name": "",
                       "key": "reset_value", "value": "0x0"}
    assert invs[1]["field_name"] == "sms" and invs[1]["value"] == "3"
    print("  candidate_invariants OK")


def test_decide_verdict():
    assert decide_verdict(True, 0.99, 0.98) == "TP"      # confident true
    assert decide_verdict(True, 0.90, 0.98) == ""        # leans true, under threshold -> abstain
    assert decide_verdict(False, 0.99, 0.98) == "FP"     # confident false
    assert decide_verdict(None, 0.0, 0.98) == ""         # no judgement
    print("  decide_verdict OK")


def test_apply_verdicts():
    rev = os.path.join(TMP, "rev_apply.csv")
    cls = os.path.join(TMP, "cls_apply.csv")
    _write_review(rev, [
        {"peripheral": "flash", "register": "acr", "key": "reset_value", "svd_value": "0x30",
         "generator_value": "0x0", "status": "", "tp_fp": "TP"},          # human already labeled -> preserve
        {"peripheral": "tim1", "register": "smcr", "field": "sms", "key": "bit_offset",
         "svd_value": "0", "generator_value": "3", "status": ""},
        {"peripheral": "spi1", "register": "cr2", "key": "reset_value", "svd_value": "0x700",
         "generator_value": "0x0", "status": "false_positive"},           # auto-FP -> blank verdict
        {"peripheral": "rcc", "register": "cr", "key": "reset_value", "svd_value": "0x1",
         "generator_value": "0x2", "status": ""},                         # no classification -> unmatched
    ])
    _write_classification(cls, [
        {"peripheral_name": "flash", "register_name": "acr", "field_name": "", "key": "reset_value",
         "value": "0x0", "agent_judgement": "True", "confidence_score": "0.99"},   # -> TP
        {"peripheral_name": "tim1", "register_name": "smcr", "field_name": "sms", "key": "bit_offset",
         "value": "3", "agent_judgement": "False", "confidence_score": "0.95"},    # -> FP
    ])
    counts = apply_verdicts(rev, cls, threshold=0.98)
    assert counts == {"TP": 1, "FP": 1, "abstain": 0, "unmatched": 1, "candidates": 3, "fallback": 0}, counts

    rows = {(_r["peripheral"], _r["register"]): _r for _r in csv.DictReader(open(rev, newline=""))}
    assert rows[("flash", "acr")]["structure_verdict"] == "TP"
    assert rows[("flash", "acr")]["structure_confidence"] == "0.99"
    assert rows[("flash", "acr")]["tp_fp"] == "TP"                          # human label preserved
    assert rows[("tim1", "smcr")]["structure_verdict"] == "FP"
    assert rows[("spi1", "cr2")]["structure_verdict"] == ""                 # auto-FP untouched
    assert rows[("rcc", "cr")]["structure_verdict"] == ""                   # unmatched -> blank
    print("  apply_verdicts OK")


def test_load_card_and_threshold():
    d = os.path.join(TMP, "cards_test")
    os.makedirs(d, exist_ok=True)
    import json
    json.dump({"device": "rm0041", "deployment_threshold": 0.98},
              open(os.path.join(d, "stm_rm0041_gpt-oss-120b.json"), "w"))
    # exact miss for rm0360 -> vendor-default falls back to the rm0041 card
    card, why = load_card("stm", "rm0360", "gpt-oss-120b", d)
    assert card is not None and why.startswith("vendor-default") and card_threshold(card) == 0.98
    # exact hit
    card2, why2 = load_card("stm", "rm0041", "gpt-oss-120b", d)
    assert why2 == "exact"
    # no card -> uncalibrated default
    card3, why3 = load_card("stm", "rm0041", "no-such-model", d)
    assert card3 is None and why3 == "uncalibrated" and card_threshold(card3) == 0.9
    print("  load_card + threshold OK")


if __name__ == "__main__":
    test_candidate_invariants()
    test_decide_verdict()
    test_apply_verdicts()
    test_load_card_and_threshold()
    print("validate_candidates tests OK")
