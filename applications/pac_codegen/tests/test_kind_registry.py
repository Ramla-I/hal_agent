"""Per-kind codegen enablement (roadmap step H framework): a grammar-v2 kind
with no emitter yet — or one explicitly disabled — is SKIPPED with a warning,
never a crash, and the register keeps its other (supported) constraints.
`rust_codegen.enabled_kinds` is the single source of truth, shared with
`inject_from_run.select_and_plan`.

Run: .venv/bin/python -m pytest applications/pac_codegen/tests/test_kind_registry.py
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from defs import RegisterInfo  # noqa: E402
from applications.pac_codegen import rust_codegen as rc  # noqa: E402


def _state_gate():
    return {"kind": "state_gate", "severity": "error", "consequence": "x",
            "datasheet_text": "write CR1 only when PE is cleared",
            "target_register": "I2C1_CR1", "target_fields": [],
            "target_operation": "write",
            "preconditions": [{"register": "I2C1_CR1", "field": "PE",
                               "state": "cleared"}],
            "postconditions": []}


def _other():
    # `other` is documentation-only by design — it never gets a codegen emitter,
    # so it is a stable stand-in for "a kind the emitter skips with a warning".
    return {"kind": "other", "severity": "error", "consequence": "x",
            "description": "a free-form access requirement the grammar can't type",
            "datasheet_text": "some free-form access note the grammar can't type"}


def _reg(constraints):
    return RegisterInfo(**{
        "datasheet_register_abbreviation": "I2C1_CR1", "address_offset": "0x0",
        "reset_value": "0x0", "size": 16, "subfields": [],
        "access_constraints_v2": constraints,
    })


def test_enabled_kinds_default_and_disable():
    assert rc.enabled_kinds() == rc.SUPPORTED_KINDS            # all supported ON
    assert "state_gate" in rc.SUPPORTED_KINDS
    assert "write_once" in rc.SUPPORTED_KINDS
    # disabling one supported kind removes exactly that one
    assert rc.enabled_kinds({"state_gate"}) == rc.SUPPORTED_KINDS - {"state_gate"}
    # disabling the whole supported set leaves nothing enabled
    assert rc.enabled_kinds(rc.SUPPORTED_KINDS) == frozenset()


def test_enabled_kinds_only_allowlist():
    # `only` restricts to the named supported kinds
    assert rc.enabled_kinds(only={"sequence"}) == frozenset({"sequence"})
    assert rc.enabled_kinds(only={"sequence", "delay"}) == frozenset({"sequence", "delay"})
    # only + disabled compose: disabled subtracts from the allowlist
    assert rc.enabled_kinds(only={"sequence", "delay"}, disabled={"delay"}) \
        == frozenset({"sequence"})
    # an unsupported / doc-only kind in `only` contributes nothing (no emitter)
    assert rc.enabled_kinds(only={"clock_gate"}) == frozenset()
    assert rc.enabled_kinds(only={"sequence", "clock_gate"}) == frozenset({"sequence"})
    # empty allowlist => nothing (explicit "none")
    assert rc.enabled_kinds(only=set()) == frozenset()


def test_unsupported_kind_warns_and_keeps_supported(capsys):
    # a register carrying a state_gate AND a not-yet-emitted `other`
    plan = rc.RegisterPlan(_reg([_state_gate(), _other()]), "i2c1")
    # the `other` is skipped, but the state_gate is still enforced (no coarse
    # whole-register loss)
    assert "write" in plan.preconditions and "modify" in plan.preconditions
    err = capsys.readouterr().err
    assert "skipping other constraint (no codegen emitter yet)" in err
    assert "state_gate" not in err          # the supported kind wasn't skipped


def test_disable_kind_skips_with_warning(capsys):
    # disabling the only kind leaves nothing enforceable -> the emitter's
    # existing "no enforceable constraints" guard fires (after a warning)
    with pytest.raises(ValueError, match="no enforceable constraints"):
        rc.RegisterPlan(_reg([_state_gate()]), "i2c1",
                        disabled_kinds={"state_gate"})
    assert "codegen disabled for this kind" in capsys.readouterr().err
