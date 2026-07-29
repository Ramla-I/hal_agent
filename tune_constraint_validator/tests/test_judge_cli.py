"""Tests for the calibration-CLI helpers lifted out of the judge
(tune_constraint_validator/judge_cli.py): deterministic stratified sampling and
the §7.2 blindness-rule output guard. No network. The judging core itself is
tested in tests/test_constraint_validator.py.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core import constraint_validator as judge  # noqa: E402
from tune_constraint_validator import judge_cli  # noqa: E402


def _write_inputs(tmp_path, n_per_rm=4, rms=("rm0001", "rm0002")):
    import csv as csv_mod
    csv_path = tmp_path / "stm.csv"
    anchors_path = tmp_path / "anchors.jsonl"
    fields = ["id", "reference_manual", "run", "source_file", "peripheral",
              "register", "target_operation", "target_fields",
              "preconditions", "postconditions", "severity", "consequence",
              "datasheet_text", "dup_count", "lint_flags", "status", "note"]
    rows, anchors = [], []
    for rm in rms:
        for i in range(n_per_rm):
            rid = f"{rm}x{i:02d}"
            rows.append({
                "id": rid, "reference_manual": rm, "run": "1",
                "source_file": f"{rm}/1/per_reg", "peripheral": "per",
                "register": f"reg{i}", "target_operation": "write",
                "target_fields": "[]",
                "preconditions": ('[{"register_name":"PER_CR","field_name":'
                                  '"EN","required_state":"cleared"}]'),
                "postconditions": "[]", "severity": "error",
                "consequence": "c", "datasheet_text": f"quote {rid}",
                "dup_count": "1", "lint_flags": "", "status": "", "note": "",
            })
            tier = "unanchored" if i == n_per_rm - 1 else "exact"
            anc = {"id": rid, "tier": tier, "reference_manual": rm}
            if tier != "unanchored":
                anc["context"] = f"context for {rid}"
            anchors.append(anc)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv_mod.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(anchors_path, "w", encoding="utf-8") as f:
        for a in anchors:
            f.write(json.dumps(a) + "\n")
    return str(csv_path), str(anchors_path)


def test_stratified_sample_deterministic_and_covers_rms(tmp_path):
    csv_path, anchors_path = _write_inputs(tmp_path, n_per_rm=6,
                                           rms=("rm1", "rm2", "rm3"))
    items = judge.load_items(csv_path, anchors_path)
    s1 = judge_cli.stratified_sample(items, 6, seed="s")
    s2 = judge_cli.stratified_sample(items, 6, seed="s")
    assert [i["id"] for i in s1] == [i["id"] for i in s2]
    assert len(s1) == 6
    assert {i["reference_manual"] for i in s1} == {"rm1", "rm2", "rm3"}
    s3 = judge_cli.stratified_sample(items, 6, seed="other")
    assert isinstance(s3, list) and len(s3) == 6  # valid under any seed
    # n >= population returns everything
    assert len(judge_cli.stratified_sample(items, 999, seed="s")) == len(items)


def test_refuses_output_under_verified_datasheet(tmp_path):
    bad = tmp_path / "verified_datasheet" / "constraints" / "j.jsonl"
    with pytest.raises(SystemExit, match="blindness"):
        judge_cli.write_judgments([], str(bad))
    ok = tmp_path / "out" / "j.jsonl"
    judge_cli.write_judgments([], str(ok))           # must not raise
    assert ok.exists()
