"""
Grammar v2 tests: models, validators, v1->v2 lift, enforceability, collection.

Covers the normative spec in docs/register_constraints_plan.md Appendix B
(mirrored in docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md):

- FieldCondition validators (evidence/action_operation iff, equals/values iff,
  hex/bin/dec value normalization, whole_register flag);
- the discriminated union round-trip for all eight kinds;
- every drift-disposition row of the B.6 v1->v2 lift table, using the REAL
  drift values observed in the 30-RM STM corpus;
- deterministic enforceability derivation (B.3) for each kind;
- an end-to-end collect_constraints run over a synthetic run directory,
  including per-constraint drops (peripheral survives), %s-placeholder
  filenames, and optional SVD name resolution + enum-name repair.

Run: .venv/bin/python -m pytest tests/test_constraints_v2.py
"""

import json
import os
import sys

import pytest
from pydantic import TypeAdapter, ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from defs import (
    ClockGate,
    ConstraintV2,
    Delay,
    FieldCondition,
    FieldRef,
    FieldState,
    LiftResult,
    Other,
    ReadEffect,
    RegisterAccessConstraint,
    RegisterInfo,
    Sequence,
    StateGate,
    ValueRelation,
    WriteOnce,
    derive_enforceability,
    lift_v1_constraint,
    parse_value_token,
)
from applications.pac_codegen.collect_constraints import collect_constraints

CONSTRAINT_ADAPTER = TypeAdapter(ConstraintV2)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def make_v1(**overrides) -> RegisterAccessConstraint:
    """A well-formed v1 constraint (the USART_BRR UE=0 mode gate)."""
    base = {
        "target_register": "USART_BRR",
        "target_fields": [],
        "target_operation": "write",
        "preconditions": [
            {"register_name": "USART_CR1", "field_name": "UE",
             "required_state": "cleared"},
        ],
        "postconditions": [],
        "severity": "error",
        "consequence": "BRR writes while the USART is enabled are ignored",
        "datasheet_text": "This register can only be written when the USART is disabled (UE=0).",
    }
    base.update(overrides)
    return RegisterAccessConstraint(**base)


def make_condition(**overrides) -> dict:
    base = {"register": "USART_CR1", "field": "UE", "state": "cleared"}
    base.update(overrides)
    return base


def reject_reasons(result: LiftResult) -> list:
    return [r.reason for r in result.rejects]


# ---------------------------------------------------------------------------
# parse_value_token
# ---------------------------------------------------------------------------

def test_parse_value_token_hex_bin_dec():
    assert parse_value_token("0x5555") == 0x5555
    assert parse_value_token("0b01") == 1
    assert parse_value_token("7") == 7
    assert parse_value_token(3) == 3
    assert parse_value_token(" 0xCA ") == 0xCA  # whitespace tolerated


@pytest.mark.parametrize("bad", ["output", "0xCA then 0x53", "", "-1", "0x", -1, True, None])
def test_parse_value_token_rejects_drift(bad):
    with pytest.raises((ValueError, TypeError)):
        parse_value_token(bad)


# ---------------------------------------------------------------------------
# FieldRef / FieldCondition validators
# ---------------------------------------------------------------------------

def test_field_condition_software_requires_action_operation():
    with pytest.raises(ValidationError, match="action_operation"):
        FieldCondition(**make_condition(evidence="software"))
    # And with it, parses fine.
    cond = FieldCondition(**make_condition(evidence="software", action_operation="modify"))
    assert cond.action_operation == "modify"


def test_field_condition_hardware_forbids_action_operation():
    with pytest.raises(ValidationError, match="action_operation"):
        FieldCondition(**make_condition(evidence="hardware", action_operation="write"))


def test_field_condition_equals_requires_values():
    with pytest.raises(ValidationError, match="values"):
        FieldCondition(**make_condition(state="equals", values=[]))
    with pytest.raises(ValidationError, match="values"):
        FieldCondition(**make_condition(state="cleared", values=[1]))


def test_field_condition_value_normalization():
    cond = FieldCondition(**make_condition(state="equals", values=["0x5555", "0b10", "3", 4]))
    assert cond.values == [0x5555, 2, 3, 4]
    # NOTE: no width check here -- value-vs-field-width needs the SVD and is
    # collection/stage-0-lint territory, not a model validator.
    big = FieldCondition(**make_condition(state="equals", values=["0xFFFFFFFFFF"]))
    assert big.values == [0xFFFFFFFFFF]


def test_field_condition_rejects_unparseable_value_strings():
    with pytest.raises(ValidationError):
        FieldCondition(**make_condition(state="equals", values=["output"]))


def test_field_ref_whole_register_flag():
    # field "" is only legal with the explicit flag.
    with pytest.raises(ValidationError, match="whole_register"):
        FieldRef(register="IWDG_KR", field="")
    ref = FieldRef(register="IWDG_KR", whole_register=True)
    assert ref.field == ""
    with pytest.raises(ValidationError, match="whole_register"):
        FieldRef(register="IWDG_KR", field="KEY", whole_register=True)


def test_state_gate_rejects_observed_state_postconditions():
    # B.2.1: postconditions are software-evidence ONLY (PR 15's silently
    # dropped class is a loud parse error in v2).
    with pytest.raises(ValidationError, match="postcondition"):
        StateGate(
            target_register="RTC_CNTH", target_operation="write",
            preconditions=[],
            postconditions=[FieldCondition(register="RTC_CRL", field="CNF",
                                           state="cleared", evidence="hardware")],
            consequence="c", datasheet_text="t",
        )


# ---------------------------------------------------------------------------
# discriminated union: round-trip all eight kinds
# ---------------------------------------------------------------------------

ALL_KIND_SAMPLES = {
    "state_gate": {
        "kind": "state_gate", "target_register": "USART_BRR",
        "target_operation": "write",
        "preconditions": [{"register": "USART_CR1", "field": "UE",
                           "state": "cleared", "evidence": "software",
                           "action_operation": "modify"}],
        "postconditions": [],
        "severity": "error",
        "consequence": "BRR writes while enabled are ignored",
        "datasheet_text": "This register can only be written when the USART is disabled (UE=0).",
    },
    "sequence": {
        "kind": "sequence",
        "steps": [
            {"register": "RTC_WPR", "operation": "write", "value": "0xCA"},
            {"register": "RTC_WPR", "operation": "write", "value": "0x53"},
        ],
        "enables": {"register": "RTC_WUTR", "whole_register": True},
        "consequence": "protected RTC registers stay locked",
        "datasheet_text": "Write 0xCA then 0x53 into the RTC_WPR register.",
    },
    "write_once": {
        "kind": "write_once", "target_register": "EXTI_LOCKR",
        "target_fields": ["LOCK"], "reset_scope": "system_reset",
        "consequence": "subsequent writes are ignored",
        "datasheet_text": "This bit is written once after reset.",
    },
    "delay": {
        "kind": "delay",
        "after": {"register": "RCC_APB1ENR", "operation": "write"},
        "duration": {"value": 2, "unit": "cycles_apb"},
        "before": {"register": "I2C_CR1", "whole_register": True},
        "consequence": "register accesses may be lost",
        "datasheet_text": "Wait at least two APB clock cycles after enabling the clock.",
    },
    "read_effect": {
        "kind": "read_effect", "read_register": "USART_DR",
        "effects": [{"field": "RXNE", "becomes": "cleared"}],
        "consequence": "flag lost on read",
        "datasheet_text": "A read to the USART_DR register clears the RXNE bit.",
    },
    "clock_gate": {
        "kind": "clock_gate",
        "clock": {"register": "RCC_APB1ENR", "field": "I2C1EN", "state": "set",
                  "evidence": "software", "action_operation": "modify"},
        "consequence": "peripheral registers read 0x0",
        "datasheet_text": "When the peripheral clock is not active, the returned value is always 0x0.",
    },
    "value_relation": {
        "kind": "value_relation",
        "fields": [{"register": "I2C_CR2", "field": "FREQ"}],
        "consequence": "wrong timings",
        "datasheet_text": "FREQ must be configured with the APB clock frequency value.",
    },
    "other": {
        "kind": "other",
        "description": "channel selection bits must remain unchanged during sample cycles",
        "involved": [{"register": "ADC_SMPR1", "field": "SMP10"}],
        "consequence": "corrupted conversion",
        "datasheet_text": "The channel selection bits must remain unchanged during the sampling cycles.",
    },
}

EXPECTED_TYPES = {
    "state_gate": StateGate, "sequence": Sequence, "write_once": WriteOnce,
    "delay": Delay, "read_effect": ReadEffect, "clock_gate": ClockGate,
    "value_relation": ValueRelation, "other": Other,
}


@pytest.mark.parametrize("kind", sorted(ALL_KIND_SAMPLES))
def test_union_round_trip(kind):
    obj = CONSTRAINT_ADAPTER.validate_python(ALL_KIND_SAMPLES[kind])
    assert type(obj) is EXPECTED_TYPES[kind]
    assert obj.kind == kind
    # JSON round-trip preserves the discriminant and content.
    dumped = CONSTRAINT_ADAPTER.dump_python(obj, mode="json")
    again = CONSTRAINT_ADAPTER.validate_json(json.dumps(dumped))
    assert again == obj


def test_union_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        CONSTRAINT_ADAPTER.validate_python(
            {"kind": "mystery", "consequence": "c", "datasheet_text": "t"})


def test_sequence_requires_two_steps():
    sample = dict(ALL_KIND_SAMPLES["sequence"])
    sample["steps"] = sample["steps"][:1]
    with pytest.raises(ValidationError):
        CONSTRAINT_ADAPTER.validate_python(sample)


# ---------------------------------------------------------------------------
# v1 -> v2 lift: every B.6 disposition row, with real corpus drift values
# ---------------------------------------------------------------------------

def test_lift_basic_state_gate():
    result = lift_v1_constraint(make_v1(), "USART_BRR")
    assert not result.rejects
    (gate,) = result.constraints
    assert isinstance(gate, StateGate)
    assert gate.target_operation == "write"
    assert gate.severity == "error"
    cond = gate.preconditions[0]
    # register_name/field_name -> register/field; "cleared" passes through.
    assert (cond.register, cond.field, cond.state) == ("USART_CR1", "UE", "cleared")
    # v1 corpus files LACK evidence_kind entirely -> default hardware.
    assert cond.evidence == "hardware"
    assert cond.action_operation is None


def test_lift_required_state_set():
    v1 = make_v1(preconditions=[{"register_name": "RTC_ISR", "field_name": "WUTWF",
                                 "required_state": "set"}])
    (gate,) = lift_v1_constraint(v1, "USART_BRR").constraints
    assert gate.preconditions[0].state == "set"


def test_lift_equals_single_value():
    v1 = make_v1(preconditions=[{"register_name": "IWDG_KR", "field_name": "KEY",
                                 "required_state": "equals:0x5555"}])
    (gate,) = lift_v1_constraint(v1, "USART_BRR").constraints
    assert gate.preconditions[0].state == "equals"
    assert gate.preconditions[0].values == [0x5555]


def test_lift_equals_or_list():
    # Real corpus drift: "equals:0b01|0b10|0b11" (the Rust-injection case).
    v1 = make_v1(preconditions=[{"register_name": "TIM1_CR1", "field_name": "CMS",
                                 "required_state": "equals:0b01|0b10|0b11"}])
    (gate,) = lift_v1_constraint(v1, "USART_BRR").constraints
    assert gate.preconditions[0].values == [1, 2, 3]


def test_lift_evidence_kind_mapping():
    # PR-15-style v1 files carry evidence_kind; the v1 models keep the extra
    # keys (extra="allow") so the lift can read them.
    v1 = make_v1(preconditions=[
        {"register_name": "RTC_ISR", "field_name": "WUTWF",
         "required_state": "set", "evidence_kind": "observed_state"},
        {"register_name": "USART_CR1", "field_name": "UE",
         "required_state": "cleared", "evidence_kind": "software_action",
         "action_operation": "modify"},
    ])
    (gate,) = lift_v1_constraint(v1, "USART_BRR").constraints
    assert gate.preconditions[0].evidence == "hardware"
    assert gate.preconditions[1].evidence == "software"
    assert gate.preconditions[1].action_operation == "modify"


def test_lift_software_action_without_operation_rejected():
    v1 = make_v1(preconditions=[
        {"register_name": "USART_CR1", "field_name": "UE",
         "required_state": "cleared", "evidence_kind": "software_action"},
    ])
    result = lift_v1_constraint(v1, "USART_BRR")
    assert result.constraints == []
    assert reject_reasons(result) == ["software_evidence_without_action_operation"]


@pytest.mark.parametrize("op,expected", [
    ("any", ["read", "write", "modify"]),
    ("read/write", ["read", "write"]),
    ("read-write", ["read", "write"]),
])
def test_lift_operation_expansion(op, expected):
    result = lift_v1_constraint(make_v1(target_operation=op), "USART_BRR")
    assert [g.target_operation for g in result.constraints] == expected
    assert not result.rejects
    assert any("expanded" in r for r in result.repairs)


@pytest.mark.parametrize("op", ["clear", "access"])
def test_lift_unknown_operation_rejected(op):
    result = lift_v1_constraint(make_v1(target_operation=op), "USART_BRR")
    assert result.constraints == []
    (rej,) = result.rejects
    assert (rej.field, rej.value, rej.reason) == (
        "target_operation", op, "unknown_target_operation")


def test_lift_severity_info_repaired_to_warning():
    result = lift_v1_constraint(make_v1(severity="info"), "USART_BRR")
    (gate,) = result.constraints
    assert gate.severity == "warning"
    assert any("info" in r for r in result.repairs)


@pytest.mark.parametrize("state", [
    "unlocked",                 # real corpus drift
    "written",                  # real corpus drift
    "equals:0xCA then 0x53",    # real corpus drift -> must become a sequence
    "unchanged",                # real corpus drift
    "enabled",                  # enum-name drift; repairable only with an SVD
])
def test_lift_unparseable_required_state_rejected(state):
    v1 = make_v1(preconditions=[{"register_name": "GPIOA_LCKR", "field_name": "LCKK",
                                 "required_state": state}])
    result = lift_v1_constraint(v1, "USART_BRR")
    # Structured rejection {field, value, reason} -- never an exception.
    assert result.constraints == []
    (rej,) = result.rejects
    assert rej.field == "preconditions[0].required_state"
    assert rej.value == state
    assert rej.reason == "unparseable_required_state"


def test_lift_empty_field_name_becomes_whole_register():
    # The real IWDG dual-evidence example encodes the whole-register
    # KR==0x5555 condition as field_name="".
    v1 = make_v1(preconditions=[
        {"register_name": "IWDG_KR", "field_name": "", "required_state": "equals:0x5555"},
        {"register_name": "IWDG_SR", "field_name": "PVU", "required_state": "cleared"},
    ])
    result = lift_v1_constraint(v1, "IWDG_PR")
    (gate,) = result.constraints
    assert gate.preconditions[0].whole_register is True
    assert gate.preconditions[0].values == [0x5555]
    assert gate.preconditions[1].whole_register is False
    assert any("whole_register" in r for r in result.repairs)


def test_lift_observed_state_postcondition_dropped_loudly():
    # v1 postcondition without evidence_kind -> hardware -> unenforceable:
    # dropped with a structured reject, the precondition gate SURVIVES.
    v1 = make_v1(postconditions=[{"register_name": "RTC_CRL", "field_name": "CNF",
                                  "required_state": "cleared"}])
    result = lift_v1_constraint(v1, "USART_BRR")
    (gate,) = result.constraints
    assert gate.postconditions == []
    assert len(gate.preconditions) == 1
    (rej,) = result.rejects
    assert rej.reason == "observed_state_postcondition_unenforceable"


def test_lift_software_postcondition_kept():
    # The RTC-CNF pre+post software action (rm0008/1/rtc_cnth): with
    # PR-15-style evidence the postcondition is representable and kept.
    v1 = make_v1(
        preconditions=[{"register_name": "RTC_CRL", "field_name": "CNF",
                        "required_state": "set",
                        "evidence_kind": "software_action",
                        "action_operation": "modify"}],
        postconditions=[{"register_name": "RTC_CRL", "field_name": "CNF",
                         "required_state": "cleared",
                         "evidence_kind": "software_action",
                         "action_operation": "modify"}],
    )
    result = lift_v1_constraint(v1, "RTC_CNTH")
    (gate,) = result.constraints
    assert not result.rejects
    assert len(gate.postconditions) == 1
    assert gate.postconditions[0].evidence == "software"


def test_lift_target_register_stamped_from_container():
    result = lift_v1_constraint(make_v1(target_register="BRR"), "USART_BRR")
    (gate,) = result.constraints
    assert gate.target_register == "USART_BRR"
    assert any("normalized" in r for r in result.repairs)


# ---------------------------------------------------------------------------
# enforceability derivation (B.3)
# ---------------------------------------------------------------------------

def _gate(preconditions):
    return StateGate(target_register="R", target_operation="write",
                     preconditions=preconditions, postconditions=[],
                     consequence="c", datasheet_text="t")


def test_enforceability_state_gate():
    hw = FieldCondition(register="RTC_ISR", field="WUTWF", state="set")
    sw = FieldCondition(register="USART_CR1", field="UE", state="cleared",
                        evidence="software", action_operation="modify")
    # Any hardware-evidence precondition needs a runtime check.
    assert derive_enforceability(_gate([hw])) == "witnessed_runtime_check"
    assert derive_enforceability(_gate([hw, sw])) == "witnessed_runtime_check"
    # All-software is pure action-witness ordering.
    assert derive_enforceability(_gate([sw])) == "compile_gate"
    assert derive_enforceability(_gate([])) == "compile_gate"


def test_enforceability_other_kinds():
    objs = {k: CONSTRAINT_ADAPTER.validate_python(v) for k, v in ALL_KIND_SAMPLES.items()}
    assert derive_enforceability(objs["sequence"]) == "compile_gate"
    assert derive_enforceability(objs["write_once"]) == "compile_gate"
    assert derive_enforceability(objs["clock_gate"]) == "compile_gate"
    # delay: witnessed iff the text names the dependent access.
    assert derive_enforceability(objs["delay"]) == "witnessed_runtime_check"
    no_before = objs["delay"].model_copy(update={"before": None})
    assert derive_enforceability(no_before) == "dynamic_check"
    assert derive_enforceability(objs["read_effect"]) == "doc_only"
    assert derive_enforceability(objs["value_relation"]) == "doc_only"
    assert derive_enforceability(objs["other"]) == "doc_only"


# ---------------------------------------------------------------------------
# end-to-end collection over a synthetic run directory
# ---------------------------------------------------------------------------

def _register_json(abbrev, constraints, subfields=()):
    return {
        "datasheet_register_abbreviation": abbrev,
        "address_offset": "0x00",
        "reset_value": "0x0000",
        "size": 32,
        "subfields": list(subfields),
        "access_constraints": constraints,
    }


@pytest.fixture
def run_dir(tmp_path):
    """A miniature generator run dir with real-STM-shaped content."""
    run = tmp_path / "agent_output" / "stm" / "rmtest" / "1"
    run.mkdir(parents=True)
    (run / "info").mkdir()  # non-register subdir: must be skipped

    # 1. The IWDG dual-evidence gate (whole-register + hardware flag).
    (run / "iwdg_pr").write_text(json.dumps(_register_json("IWDG_PR", [{
        "target_register": "IWDG_PR", "target_fields": [],
        "target_operation": "write",
        "preconditions": [
            {"register_name": "IWDG_KR", "field_name": "", "required_state": "equals:0x5555"},
            {"register_name": "IWDG_SR", "field_name": "PVU", "required_state": "cleared"},
        ],
        "postconditions": [], "severity": "error",
        "consequence": "write ignored",
        "datasheet_text": "To modify them, first write the code 0x5555 in the IWDG_KR register.",
    }])))

    # 2. One malformed constraint next to one good constraint: the bad one is
    #    dropped per-constraint, the register (and peripheral) survives.
    (run / "gpioa_lckr").write_text(json.dumps(_register_json("GPIOA_LCKR", [
        {
            "target_register": "GPIOA_LCKR", "target_fields": [],
            "target_operation": "write",
            "preconditions": [{"register_name": "GPIOA_LCKR", "field_name": "LCKK",
                               "required_state": "unlocked"}],
            "postconditions": [], "severity": "error",
            "consequence": "lock sequence aborted",
            "datasheet_text": "A specific write sequence must be applied.",
        },
        {
            "target_register": "GPIOA_LCKR", "target_fields": [],
            "target_operation": "read",
            "preconditions": [{"register_name": "GPIOA_LCKR", "field_name": "LCKK",
                               "required_state": "set"}],
            "postconditions": [], "severity": "warning",
            "consequence": "stale lock status",
            "datasheet_text": "Read the LCKK bit.",
        },
    ])))

    # 3. %s placeholder filename: rejected without guessing an expansion.
    (run / "tim3_ccr%s").write_text(json.dumps(_register_json("TIM3_CCR%s", [{
        "target_register": "TIM3_CCR%s", "target_fields": [],
        "target_operation": "write",
        "preconditions": [], "postconditions": [], "severity": "error",
        "consequence": "c", "datasheet_text": "t",
    }])))

    # 4. Enum-name drift, repairable only via SVD enumeratedValues.
    (run / "usart1_brr").write_text(json.dumps(_register_json("USART_BRR", [{
        "target_register": "USART_BRR", "target_fields": [],
        "target_operation": "write",
        "preconditions": [{"register_name": "USART_CR1", "field_name": "UE",
                           "required_state": "disabled"}],
        "postconditions": [], "severity": "error",
        "consequence": "baud rate corrupted",
        "datasheet_text": "This register can only be written when the USART is disabled (UE=0).",
    }])))

    # 5. No constraints: skipped unless include_empty.
    (run / "usart1_dr").write_text(json.dumps(_register_json("USART_DR", [])))

    # 6. Not a register output at all: silently ignored.
    (run / "notes.txt").write_text("not json")
    return run


@pytest.fixture
def svd_dir(tmp_path):
    svd = tmp_path / "svd"
    svd.mkdir()
    (svd / "test.svd").write_text("""<?xml version="1.0" encoding="utf-8"?>
<device>
  <name>TESTDEV</name>
  <peripherals>
    <peripheral>
      <name>IWDG</name>
      <registers>
        <register><name>PR</name>
          <fields><field><name>PR</name></field></fields>
        </register>
        <register><name>KR</name></register>
        <register><name>SR</name>
          <fields><field><name>PVU</name></field></fields>
        </register>
      </registers>
    </peripheral>
    <peripheral>
      <name>USART1</name>
      <registers>
        <register><name>BRR</name>
          <fields><field><name>DIV_Mantissa</name></field></fields>
        </register>
        <register><name>CR2</name>
          <fields><field><name>STOP</name></field></fields>
        </register>
        <register><name>CR1</name>
          <fields>
            <field><name>UE</name>
              <enumeratedValues>
                <enumeratedValue><name>Disabled</name><value>0</value></enumeratedValue>
                <enumeratedValue><name>Enabled</name><value>1</value></enumeratedValue>
              </enumeratedValues>
            </field>
          </fields>
        </register>
      </registers>
    </peripheral>
    <peripheral derivedFrom="USART1">
      <name>USART2</name>
    </peripheral>
    <peripheral>
      <name>GPIOA</name>
      <registers>
        <register><name>LCKR</name>
          <fields><field><name>LCKK</name></field></fields>
        </register>
      </registers>
    </peripheral>
    <peripheral>
      <name>TIM3</name>
      <registers>
        <register>
          <dim>4</dim><dimIndex>1-4</dimIndex>
          <name>CCR%s</name>
        </register>
      </registers>
    </peripheral>
  </peripherals>
</device>
""")
    return svd


def _load_manifest(out_dir):
    return json.loads((out_dir / "manifest.json").read_text())


def test_collect_end_to_end_without_svd(run_dir, tmp_path):
    out_dir = tmp_path / "collected"
    results = collect_constraints(str(run_dir), output_dir=str(out_dir))

    by_name = {f"{r['peripheral']}_{r['register']}": r for r in results}
    # Empty register skipped; the three constrained + the placeholder collected.
    assert set(by_name) == {"iwdg_pr", "gpioa_lckr", "tim3_ccr%s", "usart1_brr"}

    # IWDG: lifted, whole_register repair, hardware evidence -> witnessed.
    iwdg = json.loads((out_dir / "iwdg_pr.json").read_text())
    assert len(iwdg["access_constraints"]) == 1          # v1 key untouched
    assert iwdg["access_constraints"][0]["preconditions"][0]["field_name"] == ""
    (v2,) = iwdg["access_constraints_v2"]
    assert v2["kind"] == "state_gate"
    assert v2["enforceability"] == "witnessed_runtime_check"
    assert v2["preconditions"][0]["whole_register"] is True
    assert v2["preconditions"][0]["values"] == [0x5555]
    (report,) = iwdg["constraint_reports"]
    assert report["rejects"] == []
    assert any("whole_register" in r for r in report["repairs"])

    # gpioa_lckr: malformed constraint dropped PER-CONSTRAINT; register survives
    # with the good one.
    lckr = json.loads((out_dir / "gpioa_lckr.json").read_text())
    assert len(lckr["access_constraints"]) == 2          # v1 untouched
    assert len(lckr["access_constraints_v2"]) == 1
    assert lckr["access_constraints_v2"][0]["target_operation"] == "read"
    bad, good = lckr["constraint_reports"]
    assert bad["kinds"] == [] and bad["rejects"][0]["reason"] == "unparseable_required_state"
    assert good["kinds"] == ["state_gate"] and good["rejects"] == []

    # placeholder filename: no v2, structured reject, lint flag; no guessing.
    manifest = _load_manifest(out_dir)
    reg = {r["file"]: r for r in manifest["registers"]}
    tim = reg["tim3_ccr%s"]
    assert tim["num_constraints_v2"] == 0
    assert "placeholder_in_name" in tim["lint_flags"]
    assert tim["rejects"][0] == {
        "file": "tim3_ccr%s", "constraint_index": 0, "field": "source_file",
        "value": "tim3_ccr%s", "reason": "placeholder_in_name"}

    # Without --svd-dir every register is svd_unchecked and enum drift rejects.
    assert all("svd_unchecked" in r["lint_flags"] for r in manifest["registers"])
    brr = reg["usart1_brr"]
    assert brr["num_constraints_v2"] == 0
    assert brr["rejects"][0]["reason"] == "unparseable_required_state"

    # Manifest carries per-constraint kind/enforceability and the run-level
    # grammar-coverage metrics.
    summary = manifest["summary"]
    assert summary["constraints_v1"] == 5
    assert summary["constraints_v2"] == 2
    assert summary["constraints_rejected"] == 3
    assert summary["reject_rate"] == pytest.approx(3 / 5)
    assert summary["other_count"] == 0 and summary["other_rate"] == 0.0
    assert summary["kind_counts"] == {"state_gate": 2}
    assert summary["enforceability_counts"] == {"witnessed_runtime_check": 2}


def test_collect_end_to_end_with_svd(run_dir, svd_dir, tmp_path):
    out_dir = tmp_path / "collected_svd"
    collect_constraints(str(run_dir), output_dir=str(out_dir), svd_dir=str(svd_dir))
    manifest = _load_manifest(out_dir)
    reg = {r["file"]: r for r in manifest["registers"]}

    # B.4 repair: enum NAME "disabled" -> value 0 via SVD enumeratedValues.
    brr = reg["usart1_brr"]
    assert brr["num_constraints_v2"] == 1
    assert "svd_unchecked" not in brr["lint_flags"]
    (report,) = brr["constraints"]
    assert any("enumeratedValues" in r for r in report["repairs"])
    brr_json = json.loads((out_dir / "usart1_brr.json").read_text())
    assert brr_json["access_constraints_v2"][0]["preconditions"][0]["values"] == [0]

    # Names that resolve (family-prefixed datasheet style vs SVD instances).
    assert reg["iwdg_pr"]["num_constraints_v2"] == 1
    assert reg["gpioa_lckr"]["num_constraints_v2"] == 1


def test_collect_with_svd_rejects_unresolvable_names(run_dir, svd_dir, tmp_path):
    # Add a register whose precondition names a field the SVD does not have.
    (run_dir / "usart1_cr2").write_text(json.dumps(_register_json("USART_CR2", [{
        "target_register": "USART_CR2", "target_fields": [],
        "target_operation": "write",
        "preconditions": [{"register_name": "USART_CR1", "field_name": "NOSUCH",
                           "required_state": "cleared"}],
        "postconditions": [], "severity": "error",
        "consequence": "c", "datasheet_text": "t",
    }])))
    out_dir = tmp_path / "collected_unres"
    collect_constraints(str(run_dir), output_dir=str(out_dir), svd_dir=str(svd_dir))
    manifest = _load_manifest(out_dir)
    cr2 = {r["file"]: r for r in manifest["registers"]}["usart1_cr2"]
    assert cr2["num_constraints_v2"] == 0
    assert cr2["rejects"][0]["reason"] == "unresolvable_in_svd"
    assert cr2["rejects"][0]["field"] == "preconditions[0].field"


def test_collect_include_empty(run_dir, tmp_path):
    out_dir = tmp_path / "collected_empty"
    results = collect_constraints(str(run_dir), output_dir=str(out_dir),
                                  include_empty=True)
    names = {f"{r['peripheral']}_{r['register']}" for r in results}
    assert "usart1_dr" in names
