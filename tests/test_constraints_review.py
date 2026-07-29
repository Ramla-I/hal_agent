"""Hermetic tests for the constraints-review JSONL join adapter (stdlib only).

Run: python3 tests/test_constraints_review.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.constraints_review import constraint_id, build_constraints_review, rm_devices

TMP = os.environ.get("TMPDIR", "/tmp")

_CONSTRAINT = {
    "kind": "state_gate", "target_register": "CR1", "target_fields": [], "target_operation": "write",
    "preconditions": [{"register": "CR1", "field": "PE", "state": "cleared", "established_by": "software",
                       "action_operation": "modify"}],
    "postconditions": [], "severity": "error", "consequence": "writes ignored",
    "datasheet_text": "This register can only be written when PE=0.", "enforceability": "action_witnessed",
}


def _setup(tmp):
    rm, run = "rm0091", "1"
    collect = os.path.join(tmp, "collect"); val = os.path.join(tmp, "val")
    os.makedirs(collect, exist_ok=True); os.makedirs(val, exist_ok=True)
    # collect output: one register file with the constraint + a manifest to be skipped
    json.dump({"access_constraints_v2": [_CONSTRAINT]}, open(os.path.join(collect, "i2c1_cr1.json"), "w"))
    json.dump({"summary": {}}, open(os.path.join(collect, "manifest.json"), "w"))
    cid = constraint_id(rm, "cr1", "state_gate", _CONSTRAINT["datasheet_text"])
    with open(os.path.join(val, "anchors.jsonl"), "w") as f:
        f.write(json.dumps({"id": cid, "tier": "exact"}) + "\n")
    with open(os.path.join(val, "judgments.jsonl"), "w") as f:
        f.write(json.dumps({"id": cid, "verdict": "confirmed", "confidence": 0.95}) + "\n")
    return rm, run, collect, val, cid


def test_build_join():
    tmp = os.path.join(TMP, "creview"); os.makedirs(tmp, exist_ok=True)
    rm, run, collect, val, cid = _setup(tmp)
    out = os.path.join(tmp, "rm0091_constraints_review.jsonl")
    n = build_constraints_review(rm, run, collect, val, out, repo_root=tmp)
    assert n == 1
    rec = json.loads(open(out).read().strip())
    assert rec["id"] == cid
    assert rec["peripheral"] == "i2c1" and rec["register"] == "cr1"
    assert rec["constraint"]["kind"] == "state_gate"                 # FULL constraint present
    assert rec["constraint"]["datasheet_text"].startswith("This register")
    assert rec["anchor_tier"] == "exact" and rec["verdict"] == "confirmed" and rec["confidence"] == 0.95
    assert rec["tp_fp"] == ""
    # no sibling column duplicates a constraint field
    assert "kind" not in rec and "datasheet_text" not in rec and "enforceability" not in rec
    print("  build join OK")


def test_preserve_tp_fp_and_devices_on_rerun():
    tmp = os.path.join(TMP, "creview2"); os.makedirs(tmp, exist_ok=True)
    rm, run, collect, val, cid = _setup(tmp)
    out = os.path.join(tmp, "rm0091_constraints_review.jsonl")
    build_constraints_review(rm, run, collect, val, out, repo_root=tmp)
    # reviewer edits tp_fp + trims devices
    recs = [json.loads(l) for l in open(out) if l.strip()]
    recs[0]["tp_fp"] = "TP"; recs[0]["devices"] = ["stm32f0x1"]
    with open(out, "w") as f:
        f.write(json.dumps(recs[0]) + "\n")
    # re-run must preserve both
    build_constraints_review(rm, run, collect, val, out, repo_root=tmp)
    rec = json.loads(open(out).read().strip())
    assert rec["tp_fp"] == "TP" and rec["devices"] == ["stm32f0x1"]
    print("  preserve tp_fp + devices OK")


def test_rm_devices_from_mapping():
    tmp = os.path.join(TMP, "creview3", "devices", "stm"); os.makedirs(tmp, exist_ok=True)
    with open(os.path.join(tmp, "rm_device_mapping.xml"), "w") as f:
        f.write('<root><reference_manual rm="rm0091"><svd>'
                '<svd_file>stm32f0x1.svd</svd_file><svd_file>stm32f0x2.svd</svd_file>'
                '</svd></reference_manual></root>')
    repo_root = os.path.join(TMP, "creview3")
    assert rm_devices("rm0091", repo_root=repo_root) == ["stm32f0x1", "stm32f0x2"]
    print("  rm_devices from mapping OK")


if __name__ == "__main__":
    test_build_join()
    test_preserve_tp_fp_and_devices_on_rerun()
    test_rm_devices_from_mapping()
    print("constraints_review tests OK")
