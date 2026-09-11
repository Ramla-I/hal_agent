#!/usr/bin/env python3
"""The --save-constraints artifact must describe every gate it counts.

`applications/pac_codegen/constraints/<rm>_<device>.json` is the durable,
reviewable record of what a device's crate enforces. A field-scoped gate lives
in ``RegisterPlan.field_gates``, NOT ``.preconditions``, and ``gated_ops()``
reads only the latter -- so a register whose gates are all field-scoped once
serialised as ``"gated_operations": []`` with empty preconditions and empty
datasheet text. Present in the record, unexplained: 21 of one manual's 83 rows
looked like that.

No toolchain, no PAC and no run directory needed -- that is the point of
``device_constraints_file`` being its own function.
"""

import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR.parent.parent))
sys.path.insert(0, str(APP_DIR))

import rust_codegen  # noqa: E402
from inject_from_run import device_constraints_file  # noqa: E402
from defs import RegisterInfo  # noqa: E402

FIELD_FIXTURE = APP_DIR / "constraint_test" / "stm32f405_i2c1_start_field.json"
WHOLE_FIXTURE = APP_DIR / "constraint_test" / "stm32f405_i2c1.json"


def _plan(fixture: Path, field_gating: bool):
    info = RegisterInfo(**json.loads(fixture.read_text()))
    return rust_codegen.RegisterPlan(info, "i2c1",
                                     field_level_gating=field_gating)


def _file(plan, field_gating: bool) -> dict:
    return device_constraints_file("stm32f405", "run", "svd", None,
                                   field_gating, [plan], {})


def test_field_gate_is_described_not_merely_counted():
    plan = _plan(FIELD_FIXTURE, field_gating=True)
    assert plan.field_gates, "fixture no longer produces a field gate"
    (row,) = _file(plan, True)["registers"]

    assert row["gated_fields"], "a field-gated register serialised with none"
    for field, g in row["gated_fields"].items():
        assert g["preconditions"], f"{field}: gate with no precondition"
        assert g["datasheet_text"], f"{field}: gate with no datasheet sentence"
        # One writer accessor serves both surfaces.
        assert g["operations"] == ["write", "modify"]

    # No row may be gate-less in BOTH structures: that is the shape that made
    # the omission invisible.
    assert row["gated_operations"] or row["gated_fields"]


def test_field_gating_leaves_the_whole_register_surface_free():
    """The mode's whole point: siblings stay writable. If this ever gains
    register-level preconditions, the field gate has been widened."""
    row, = _file(_plan(FIELD_FIXTURE, field_gating=True), True)["registers"]
    assert row["gated_operations"] == []
    assert row["preconditions"] == {}


def test_whole_register_file_carries_no_field_section():
    """The default mode skips field-scoped constraints rather than widening
    them, so its files must never claim a field gate."""
    row, = _file(_plan(WHOLE_FIXTURE, field_gating=False), False)["registers"]
    assert row["gated_operations"], "fixture no longer gates the register"
    assert row["gated_fields"] == {}


def test_mode_is_recorded():
    """Two modes plan different gate sets; a file that does not say which it
    is cannot be read safely."""
    for gating, fixture in ((True, FIELD_FIXTURE), (False, WHOLE_FIXTURE)):
        doc = _file(_plan(fixture, gating), gating)
        assert doc["field_level_gating"] is gating


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
