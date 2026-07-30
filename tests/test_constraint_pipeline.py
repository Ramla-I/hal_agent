"""Hermetic tests for the chained constraint stage (stdlib only).

Run: python3 tests/test_constraint_pipeline.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.constraint_pipeline import (
    new_constraint_id, enforcement_decision, build_validated, old_constraint_id,
)

TMP = os.environ.get("TMPDIR", "/tmp")


def test_new_id_disambiguates_peripheral_and_operation():
    c = {"kind": "state_gate", "target_operation": "write", "target_fields": [],
         "datasheet_text": "write only when X=0"}
    # same register name across peripheral instances -> DIFFERENT ids (the old bug)
    assert new_constraint_id("rm0091", "usart1", "brr", c) != new_constraint_id("rm0091", "usart2", "brr", c)
    # same constraint, different operation (an "any"-split) -> DIFFERENT ids
    c_read = dict(c, target_operation="read")
    assert new_constraint_id("rm0091", "usart1", "brr", c) != new_constraint_id("rm0091", "usart1", "brr", c_read)
    # the retired id collapsed both -> identical (documents why we changed it)
    assert old_constraint_id("rm0091", "brr", "state_gate", c["datasheet_text"]) == \
           old_constraint_id("rm0091", "brr", "state_gate", c["datasheet_text"])
    print("  new id disambiguates peripheral + operation OK")


def test_enforcement_decision():
    assert enforcement_decision("confirmed", "state_witnessed", 0.9) == "enforce"
    assert enforcement_decision("confirmed", "action_witnessed", 0.9) == "enforce"
    assert enforcement_decision("confirmed", "doc_only", 0.9) == "doc_only"       # genuine, not witnessed
    assert enforcement_decision("encoding_error", "state_witnessed", 0.9) == "doc_only"
    assert enforcement_decision("", "state_witnessed", None) == "doc_only"        # unanchored/unjudged
    assert enforcement_decision("not_constraint", "state_witnessed", 0.9) == "drop"
    # min_confidence knob (inert at 0.0) demotes a low-confidence confirm to doc_only
    assert enforcement_decision("confirmed", "state_witnessed", 0.5, min_confidence=0.8) == "doc_only"
    print("  enforcement decision mapping OK")


def test_build_validated_reuses_cached_verdicts():
    tmp = os.path.join(TMP, "cpipe"); os.makedirs(tmp, exist_ok=True)
    collect = os.path.join(tmp, "collect"); val = os.path.join(tmp, "val")
    os.makedirs(collect, exist_ok=True); os.makedirs(val, exist_ok=True)
    c = {"kind": "state_gate", "target_operation": "write", "target_fields": [],
         "datasheet_text": "write only when PE=0", "enforceability": "state_witnessed"}
    # SAME constraint text in two peripheral instances -> two linted rows, one old id
    json.dump({"access_constraints_v2": [c]}, open(os.path.join(collect, "usart1_brr.json"), "w"))
    json.dump({"access_constraints_v2": [c]}, open(os.path.join(collect, "usart2_brr.json"), "w"))
    oid = old_constraint_id("rm0091", "brr", "state_gate", c["datasheet_text"])
    open(os.path.join(val, "anchors.jsonl"), "w").write(json.dumps({"id": oid, "tier": "exact"}) + "\n")
    open(os.path.join(val, "judgments.jsonl"), "w").write(
        json.dumps({"id": oid, "verdict": "confirmed", "confidence": 0.95}) + "\n")

    out = os.path.join(tmp, "validated.jsonl")
    counts = build_validated("rm0091", "1", collect, val, out)
    assert counts["constraints"] == 2 and counts["distinct_ids"] == 2   # collision fixed
    recs = [json.loads(l) for l in open(out) if l.strip()]
    # both instances reuse the shared cached verdict, each enforce-gated, distinct ids
    assert all(r["verdict"] == "confirmed" and r["enforcement"] == "enforce" for r in recs)
    assert {r["peripheral"] for r in recs} == {"usart1", "usart2"}
    print("  build_validated reuses cached verdicts + distinct ids OK")


if __name__ == "__main__":
    test_new_id_disambiguates_peripheral_and_operation()
    test_enforcement_decision()
    test_build_validated_reuses_cached_verdicts()
    print("constraint_pipeline tests OK")
