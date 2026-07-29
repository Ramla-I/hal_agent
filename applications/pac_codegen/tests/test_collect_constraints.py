"""
Native grammar-v2 collection tests (roadmap step F).

The generator emits grammar v2 directly; a register file carries an
``"access_constraints_v2"`` list. Collection runs the stage-0 lint directly on
the native objects. Covers:

- per-constraint pydantic validation: a malformed entry is rejected with
  reason ``invalid_v2_constraint`` while well-formed siblings survive
  (plan section 6.1d per-constraint recovery);
- exact dedup on native objects (keep-first, duplicate_of back-reference);
- target_register normalization and "any" expansion (deterministic repairs);
- stage-0 lint on native objects: SVD name resolution, value-vs-width,
  write-on-read-only, w1c postcondition reclassification, self-defeating
  read gates, cross_peripheral flag;
- computed ``enforceability`` annotation on every emitted constraint;
- manifest bookkeeping: ``constraint_source`` per register plus run-level
  ``constraint_sources`` counts, in mixed native/lifted runs.

Run: .venv/bin/python -m pytest applications/pac_codegen/tests/test_collect_constraints.py
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from applications.pac_codegen.collect_constraints import collect_constraints


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _register_json_v2(abbrev, constraints_v2, subfields=()):
    return {
        "datasheet_register_abbreviation": abbrev,
        "address_offset": "0x00",
        "reset_value": "0x0000",
        "size": 32,
        "subfields": list(subfields),
        "access_constraints_v2": list(constraints_v2),
    }


def _state_gate(target, op="write", pre=(), post=(), fields=(),
                severity="error", text="quote", consequence="c"):
    return {
        "kind": "state_gate",
        "target_register": target,
        "target_fields": list(fields),
        "target_operation": op,
        "preconditions": list(pre),
        "postconditions": list(post),
        "severity": severity,
        "consequence": consequence,
        "datasheet_text": text,
    }


def _cond(register, field, state="cleared", established_by="hardware", **extra):
    cond = {"register": register, "field": field, "state": state,
            "established_by": established_by, **extra}
    if established_by == "software" and "action_operation" not in cond:
        cond["action_operation"] = "modify"
    return cond


SW_UE_CLEARED = _cond("USART_CR1", "UE", "cleared", "software")


def _load_manifest(out_dir):
    return json.loads((out_dir / "manifest.json").read_text())


def _reg_entry(manifest, file_name):
    return {r["file"]: r for r in manifest["registers"]}[file_name]


NATIVE_SVD = """<?xml version="1.0" encoding="utf-8"?>
<device>
  <name>NATIVEDEV</name>
  <size>0x20</size>
  <peripherals>
    <peripheral>
      <name>USART1</name>
      <registers>
        <register><name>BRR</name>
          <fields><field><name>DIV_Mantissa</name><bitWidth>12</bitWidth></field></fields>
        </register>
        <register><name>CR1</name>
          <fields><field><name>UE</name><bitWidth>1</bitWidth></field></fields>
        </register>
        <register><name>SR</name>
          <fields>
            <field><name>TC</name><bitWidth>1</bitWidth>
              <modifiedWriteValues>oneToClear</modifiedWriteValues>
            </field>
          </fields>
        </register>
      </registers>
    </peripheral>
    <peripheral>
      <name>IWDG</name>
      <registers>
        <register><name>PR</name>
          <fields><field><name>PR</name><bitWidth>3</bitWidth></field></fields>
        </register>
        <register><name>KR</name>
          <fields><field><name>KEY</name><bitWidth>16</bitWidth></field></fields>
        </register>
        <register><name>SR</name>
          <access>read-only</access>
          <fields><field><name>PVU</name><bitWidth>1</bitWidth></field></fields>
        </register>
      </registers>
    </peripheral>
    <peripheral>
      <name>RTC</name>
      <registers>
        <register><name>WPR</name>
          <fields><field><name>KEY</name><bitWidth>8</bitWidth></field></fields>
        </register>
        <register><name>DR</name>
          <fields><field><name>DU</name><bitWidth>4</bitWidth></field></fields>
        </register>
      </registers>
    </peripheral>
    <peripheral>
      <name>PWR</name>
      <registers>
        <register><name>CR</name>
          <fields><field><name>DBP</name><bitWidth>1</bitWidth></field></fields>
        </register>
      </registers>
    </peripheral>
  </peripherals>
</device>
"""


@pytest.fixture
def svd_dir(tmp_path):
    svd = tmp_path / "svd"
    svd.mkdir()
    (svd / "native.svd").write_text(NATIVE_SVD)
    return svd


@pytest.fixture
def run_dir(tmp_path):
    run = tmp_path / "agent_output" / "stm" / "rmnative" / "1"
    run.mkdir(parents=True)
    return run


# ---------------------------------------------------------------------------
# native detection + basic flow
# ---------------------------------------------------------------------------

def test_native_v2_basic(run_dir, tmp_path):
    (run_dir / "usart1_brr").write_text(json.dumps(_register_json_v2(
        "USART_BRR",
        [_state_gate("USART_BRR", pre=[SW_UE_CLEARED],
                     text="This register can only be written when the USART is disabled (UE=0).")],
    )))
    out_dir = tmp_path / "out"
    results = collect_constraints(str(run_dir), output_dir=str(out_dir))
    (r,) = results
    assert r["constraint_source"] == "native_v2"
    assert r["num_constraints"] == 1 and r["num_constraints_v2"] == 1

    data = json.loads((out_dir / "usart1_brr.json").read_text())
    assert "access_constraints" not in data              # v1 key retired
    (v2,) = data["access_constraints_v2"]
    assert v2["kind"] == "state_gate"
    # All-software preconditions -> pure action-witness ordering.
    assert v2["enforceability"] == "action_witnessed"
    assert v2["preconditions"][0]["established_by"] == "software"

    manifest = _load_manifest(out_dir)
    entry = _reg_entry(manifest, "usart1_brr")
    assert entry["constraint_source"] == "native_v2"
    assert entry["num_source_constraints"] == 1
    (report,) = entry["constraints"]
    assert report["v2_index"] == 0 and report["kinds"] == ["state_gate"]
    summary = manifest["summary"]
    assert summary["constraint_sources"] == {"native_v2": 1}
    assert summary["constraints_native_v2"] == 1
    assert summary["kind_counts"] == {"state_gate": 1}


# ---------------------------------------------------------------------------
# per-constraint recovery, dedup, repairs
# ---------------------------------------------------------------------------

def test_malformed_native_entry_rejected_siblings_survive(run_dir, tmp_path):
    good = _state_gate("USART_BRR", pre=[SW_UE_CLEARED])
    bad_kind = {"kind": "mystery", "consequence": "c", "datasheet_text": "t"}
    bad_condition = _state_gate(
        "USART_BRR",
        pre=[{"register": "USART_CR1", "field": "UE", "state": "cleared",
              "established_by": "software"}],  # missing action_operation
    )
    (run_dir / "usart1_brr").write_text(json.dumps(_register_json_v2(
        "USART_BRR", [bad_kind, good, bad_condition])))
    out_dir = tmp_path / "out"
    (r,) = collect_constraints(str(run_dir), output_dir=str(out_dir))
    assert r["num_constraints"] == 3 and r["num_constraints_v2"] == 1

    manifest = _load_manifest(out_dir)
    entry = _reg_entry(manifest, "usart1_brr")
    bad_rep, good_rep, bad2_rep = entry["constraints"]
    assert bad_rep["kinds"] == []
    assert bad_rep["rejects"][0]["reason"] == "invalid_v2_constraint"
    assert good_rep["kinds"] == ["state_gate"] and good_rep["rejects"] == []
    assert bad2_rep["kinds"] == []
    assert bad2_rep["rejects"][0]["reason"] == "invalid_v2_constraint"
    assert "action_operation" in bad2_rep["rejects"][0]["field"] or \
        "action_operation" in bad2_rep["rejects"][0]["value"]
    assert manifest["summary"]["reject_reasons"]["invalid_v2_constraint"] == 2


def test_native_exact_dedup_keeps_first(run_dir, tmp_path):
    gate = _state_gate("USART_BRR", pre=[SW_UE_CLEARED], text="same quote")
    # Same constraint with different target_fields still dedups (per-bit
    # fan-out polarity, mirroring the v1 key).
    fanout = _state_gate("USART_BRR", pre=[SW_UE_CLEARED], text="same quote",
                         fields=["DIV_Mantissa"])
    (run_dir / "usart1_brr").write_text(json.dumps(_register_json_v2(
        "USART_BRR", [gate, dict(gate), fanout])))
    out_dir = tmp_path / "out"
    (r,) = collect_constraints(str(run_dir), output_dir=str(out_dir))
    assert r["num_constraints_v2"] == 1

    manifest = _load_manifest(out_dir)
    entry = _reg_entry(manifest, "usart1_brr")
    assert entry["duplicates_dropped"] == 2
    first, dup1, dup2 = entry["constraints"]
    assert first["kinds"] == ["state_gate"]
    for dup in (dup1, dup2):
        assert "exact_duplicate" in dup["lint_flags"]
        assert dup["duplicate_of"] == 0
    assert manifest["summary"]["constraints_deduped"] == 2
    assert manifest["summary"]["constraints_native_v2_unique"] == 1


def test_native_any_expansion_and_target_register_normalization(run_dir, tmp_path):
    gate = _state_gate("BRR", op="any", pre=[SW_UE_CLEARED])
    (run_dir / "usart1_brr").write_text(json.dumps(_register_json_v2(
        "USART_BRR", [gate])))
    out_dir = tmp_path / "out"
    (r,) = collect_constraints(str(run_dir), output_dir=str(out_dir))
    assert r["num_constraints_v2"] == 2

    data = json.loads((out_dir / "usart1_brr.json").read_text())
    ops = [c["target_operation"] for c in data["access_constraints_v2"]]
    assert ops == ["read", "write"]
    assert all(c["target_register"] == "USART_BRR"
               for c in data["access_constraints_v2"])
    entry = _reg_entry(_load_manifest(out_dir), "usart1_brr")
    (report,) = entry["constraints"]
    assert any("normalized" in rep for rep in report["repairs"])
    assert any("expanded" in rep for rep in report["repairs"])


def test_native_non_state_gate_kinds_flow_through(run_dir, tmp_path):
    sequence = {
        "kind": "sequence",
        "steps": [
            {"register": "RTC_WPR", "operation": "write", "value": "0xCA"},
            {"register": "RTC_WPR", "operation": "write", "value": "0x53"},
        ],
        "enables": {"register": "RTC_DR", "whole_register": True},
        "severity": "error",
        "consequence": "RTC registers stay write-protected",
        "datasheet_text": "Write 0xCA then 0x53 into the RTC_WPR register.",
    }
    other = {
        "kind": "other",
        "description": "do not change after initial programming",
        "involved": [{"register": "RTC_DR", "field": "DU"}],
        "severity": "warning",
        "consequence": "c",
        "datasheet_text": "t",
    }
    (run_dir / "rtc_dr").write_text(json.dumps(_register_json_v2(
        "RTC_DR", [sequence, other])))
    out_dir = tmp_path / "out"
    (r,) = collect_constraints(str(run_dir), output_dir=str(out_dir))
    assert r["num_constraints_v2"] == 2

    data = json.loads((out_dir / "rtc_dr.json").read_text())
    seq_json, other_json = data["access_constraints_v2"]
    assert seq_json["kind"] == "sequence"
    assert seq_json["enforceability"] == "action_witnessed"
    assert seq_json["steps"][0]["value"] == 0xCA   # numeric normalization
    assert other_json["kind"] == "other"
    assert other_json["enforceability"] == "doc_only"
    summary = _load_manifest(out_dir)["summary"]
    assert summary["kind_counts"] == {"sequence": 1, "other": 1}
    assert summary["other_rate"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# stage-0 lint on native objects
# ---------------------------------------------------------------------------

def test_native_self_defeating_read_gate_rejected(run_dir, tmp_path):
    gate = _state_gate("USART_BRR", op="read",
                       pre=[_cond("USART_BRR", "DIV_Mantissa", "set")])
    (run_dir / "usart1_brr").write_text(json.dumps(_register_json_v2(
        "USART_BRR", [gate])))
    out_dir = tmp_path / "out"
    (r,) = collect_constraints(str(run_dir), output_dir=str(out_dir))
    assert r["num_constraints_v2"] == 0
    entry = _reg_entry(_load_manifest(out_dir), "usart1_brr")
    assert entry["rejects"][0]["reason"] == "self_defeating_read_gate"


def test_native_svd_unresolvable_rejected(run_dir, svd_dir, tmp_path):
    good = _state_gate("USART_BRR", pre=[SW_UE_CLEARED])
    bad = _state_gate("USART_BRR",
                      pre=[_cond("USART_CR1", "NOSUCH", "cleared")])
    (run_dir / "usart1_brr").write_text(json.dumps(_register_json_v2(
        "USART_BRR", [good, bad])))
    out_dir = tmp_path / "out"
    (r,) = collect_constraints(str(run_dir), output_dir=str(out_dir),
                               svd_dir=str(svd_dir))
    assert r["num_constraints_v2"] == 1
    manifest = _load_manifest(out_dir)
    entry = _reg_entry(manifest, "usart1_brr")
    assert "svd_unchecked" not in entry["lint_flags"]
    good_rep, bad_rep = entry["constraints"]
    assert good_rep["rejects"] == []
    assert bad_rep["rejects"][0]["reason"] == "unresolvable_in_svd"
    assert bad_rep["rejects"][0]["field"] == "preconditions[0].field"


def test_native_value_width_and_read_only_rejects(run_dir, svd_dir, tmp_path):
    too_wide = _state_gate(
        "IWDG_PR",
        pre=[_cond("IWDG_KR", "KEY", "equals", "software",
                   action_operation="write", values=["0x15555"])])  # 17 bits > 16
    on_read_only = _state_gate(
        "IWDG_SR", op="write",
        pre=[_cond("IWDG_KR", "KEY", "equals", "software",
                   action_operation="write", values=["0x5555"])])
    (run_dir / "iwdg_pr").write_text(json.dumps(_register_json_v2(
        "IWDG_PR", [too_wide])))
    (run_dir / "iwdg_sr").write_text(json.dumps(_register_json_v2(
        "IWDG_SR", [on_read_only])))
    out_dir = tmp_path / "out"
    collect_constraints(str(run_dir), output_dir=str(out_dir),
                        svd_dir=str(svd_dir))
    manifest = _load_manifest(out_dir)
    pr = _reg_entry(manifest, "iwdg_pr")
    assert pr["num_constraints_v2"] == 0
    assert pr["rejects"][0]["reason"] == "value_exceeds_field_width"
    sr = _reg_entry(manifest, "iwdg_sr")
    assert sr["num_constraints_v2"] == 0
    assert sr["rejects"][0]["reason"] == "write_constraint_on_read_only"


def test_native_w1c_postcondition_stripped_gate_survives(run_dir, svd_dir, tmp_path):
    gate = _state_gate(
        "USART_BRR",
        pre=[SW_UE_CLEARED],
        post=[_cond("USART_SR", "TC", "cleared", "software",
                    action_operation="write")])
    (run_dir / "usart1_brr").write_text(json.dumps(_register_json_v2(
        "USART_BRR", [gate])))
    out_dir = tmp_path / "out"
    (r,) = collect_constraints(str(run_dir), output_dir=str(out_dir),
                               svd_dir=str(svd_dir))
    assert r["num_constraints_v2"] == 1
    data = json.loads((out_dir / "usart1_brr.json").read_text())
    (v2,) = data["access_constraints_v2"]
    assert v2["postconditions"] == []          # w1c restatement dropped
    assert len(v2["preconditions"]) == 1       # the gate itself survives
    entry = _reg_entry(_load_manifest(out_dir), "usart1_brr")
    (report,) = entry["constraints"]
    assert report["rejects"][0]["reason"] == "w1c_flag_semantics"
    assert "w1c_semantics" in report["lint_flags"]


def test_native_cross_peripheral_flag(run_dir, tmp_path):
    gate = _state_gate("RTC_DR", pre=[_cond("PWR_CR", "DBP", "set", "software",
                                            action_operation="modify")])
    (run_dir / "rtc_dr").write_text(json.dumps(_register_json_v2(
        "RTC_DR", [gate])))
    out_dir = tmp_path / "out"
    (r,) = collect_constraints(str(run_dir), output_dir=str(out_dir))
    assert r["num_constraints_v2"] == 1
    entry = _reg_entry(_load_manifest(out_dir), "rtc_dr")
    (report,) = entry["constraints"]
    assert "cross_peripheral" in report["lint_flags"]


def test_native_placeholder_filename_rejected(run_dir, tmp_path):
    gate = _state_gate("TIM3_CCR%s", pre=[SW_UE_CLEARED])
    (run_dir / "tim3_ccr%s").write_text(json.dumps(_register_json_v2(
        "TIM3_CCR%s", [gate])))
    out_dir = tmp_path / "out"
    (r,) = collect_constraints(str(run_dir), output_dir=str(out_dir))
    assert r["num_constraints_v2"] == 0
    entry = _reg_entry(_load_manifest(out_dir), "tim3_ccr%s")
    assert "placeholder_in_name" in entry["lint_flags"]
    assert any(rej["reason"] == "placeholder_in_name" for rej in entry["rejects"])


def test_native_hardware_gate_is_witnessed(run_dir, tmp_path):
    gate = _state_gate("IWDG_PR", pre=[
        # whole_register conditions omit `field` (never field "")
        {"register": "IWDG_KR", "whole_register": True, "state": "equals",
         "values": ["0x5555"], "established_by": "software",
         "action_operation": "write"},
        _cond("IWDG_SR", "PVU", "cleared", "hardware"),
    ])
    (run_dir / "iwdg_pr").write_text(json.dumps(_register_json_v2(
        "IWDG_PR", [gate])))
    out_dir = tmp_path / "out"
    (r,) = collect_constraints(str(run_dir), output_dir=str(out_dir))
    assert r["num_constraints_v2"] == 1
    data = json.loads((out_dir / "iwdg_pr.json").read_text())
    (v2,) = data["access_constraints_v2"]
    assert v2["enforceability"] == "state_witnessed"
    assert v2["preconditions"][0]["whole_register"] is True
    assert v2["preconditions"][0]["values"] == [0x5555]
