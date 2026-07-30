#!/usr/bin/env python3
"""test_instance_alias.py -- peripheral INSTANCES share one register-block module.

WHAT THIS GUARDS
----------------
svd2rust does not emit ``i2c2.rs``. It emits ONE module per register block and
gives each instance a type alias over it, generated from the SVD's
``derivedFrom``::

    pub type I2C1 = crate::Periph<i2c1::RegisterBlock, 0x4000_5400>;
    pub type I2C2 = crate::Periph<i2c1::RegisterBlock, 0x4000_5800>;
    pub type I2C3 = crate::Periph<i2c1::RegisterBlock, 0x4000_7800>;

So I2C2's TIMEOUTR *is* ``i2c1::timeoutr::TIMEOUTRrs`` -- the same Rust type.
Before this map existed, every constraint extracted for a non-first instance
was thrown away as "peripheral not in device" even though the peripheral is on
the chip: 180 of 200 such drops across the STM sweep, and resolving them took
enforced state gates from 179 to 296.

Two consequences the tests below pin:

  1. Resolution must come from the GENERATED alias lines, not from name
     munging. Stripping digits gives ``usart2 -> usart``, a module that does
     not exist; and it cannot know ``dma2 -> dma1`` while ``tim2`` owns its own
     module.

  2. Because instances share the type, gating is ALL-OR-NOTHING per module,
     so two plans can now target one Rust type. Emitting both would define the
     same witness types twice. When colliding plans agree, that is one rule the
     manual states once and our per-instance iteration replicated. When they
     disagree, the difference is extraction noise on the same quote (measured:
     92 agreeing groups vs 32 disagreeing; the disagreements cite identical
     datasheet sentences), so we keep ONE and never union -- a unioned gate
     would demand a precondition the datasheet may not.

No toolchain needed.

Run directly (``python test_instance_alias.py``) or under pytest.
"""

import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR.parent.parent))

import rust_codegen  # noqa: E402
from defs import RegisterInfo  # noqa: E402

_MOD_RS = """\
pub type USART1 = crate::Periph<usart1::RegisterBlock, 0x4001_3800>;
pub type USART2 = crate::Periph<usart1::RegisterBlock, 0x4000_4400>;
pub type I2C1 = crate::Periph<i2c1::RegisterBlock, 0x4000_5400>;
pub type I2C2 = crate::Periph<i2c1::RegisterBlock, 0x4000_5800>;
pub type I2C3 = crate::Periph<i2c1::RegisterBlock, 0x4000_7800>;
pub type TIM2 = crate::Periph<tim2::RegisterBlock, 0x4000_0000>;
"""


def _device(tmp: Path) -> Path:
    dev = tmp / "stm32fake"
    dev.mkdir(parents=True)
    (dev / "mod.rs").write_text(_MOD_RS)
    return dev


def test_alias_map_is_read_from_the_generated_lines():
    with tempfile.TemporaryDirectory() as td:
        m = rust_codegen.peripheral_instance_map(_device(Path(td)))
        assert m["i2c2"] == "i2c1"
        assert m["i2c3"] == "i2c1"
        assert m["usart2"] == "usart1"
        # identity entries too: this is a complete instance->module map
        assert m["i2c1"] == "i2c1"
        # a peripheral that owns its own block maps to itself, NOT to "tim1"
        assert m["tim2"] == "tim2"


def test_missing_mod_rs_yields_empty_map():
    """Other PAC layouts have no mod.rs; callers must fall back, not crash."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "nodev"
        d.mkdir()
        assert rust_codegen.peripheral_instance_map(d) == {}


def _plan(module: str, instance: str, field: str, state: str = "cleared"):
    info = RegisterInfo(**{
        "datasheet_register_abbreviation": "TIMEOUTR",
        "address_offset": "0x0", "reset_value": "0x0", "size": 32,
        "subfields": [],
        "access_constraints_v2": [{
            "kind": "state_gate", "severity": "error", "consequence": "x",
            "datasheet_text": "These bits can be written only when TEXTEN = 0.",
            "target_register": "TIMEOUTR", "target_fields": [],
            "target_operation": "write",
            "preconditions": [{
                "register": "TIMEOUTR", "field": field, "whole_register": False,
                "state": state, "values": [], "established_by": "hardware",
                "action_operation": None,
            }],
            "postconditions": [],
        }],
    })
    p = rust_codegen.RegisterPlan(info, module)
    p.source_instance = instance
    return p


def test_agreeing_instances_collapse_to_one_plan():
    """I2C1/I2C2/I2C3 all carrying the same rule is ONE rule the manual states
    once — it must emit one gate, not three colliding ones."""
    plans = [_plan("i2c1", i, "TEXTEN") for i in ("i2c1", "i2c2", "i2c3")]
    kept, conflicts = rust_codegen.resolve_instance_collisions(plans)
    assert len(kept) == 1
    assert conflicts == []
    assert kept[0].source_instance == "i2c1"      # the module owner


def test_disagreeing_instances_drop_the_whole_gate():
    """Two readings of one datasheet sentence, and no way to tell which is
    right. Neither survives: a gate is a compile-time obligation on every
    downstream user, so contradictory evidence buys no gate at all."""
    plans = [_plan("i2c1", "i2c2", "UE"), _plan("i2c1", "i2c1", "TEXTEN")]
    kept, conflicts = rust_codegen.resolve_instance_collisions(plans)
    assert kept == [], "a disagreeing group must not be enforced"
    assert len(conflicts) == 1
    assert conflicts[0]["instances"] == ["i2c1", "i2c2"]
    assert "disagree" in conflicts[0]["detail"]


def test_owner_does_not_win_a_disagreement():
    """Being the module owner is a tie-break for AGREEING plans only — it is
    not evidence that its reading is the correct one."""
    plans = [_plan("i2c1", "i2c1", "TEXTEN"), _plan("i2c1", "i2c3", "UE")]
    kept, conflicts = rust_codegen.resolve_instance_collisions(plans)
    assert kept == [] and len(conflicts) == 1


def test_disagreement_is_never_unioned():
    """The rejected alternative: a unioned gate would demand BOTH
    preconditions — stricter than the datasheet, and a false compile error
    for correct code."""
    plans = [_plan("i2c1", "i2c2", "UE"), _plan("i2c1", "i2c3", "TEXTEN")]
    kept, _ = rust_codegen.resolve_instance_collisions(plans)
    assert kept == []


def test_tie_break_is_numeric_not_lexicographic():
    """The tie-break only runs on AGREEING groups, but it still has to be
    numeric: a plain string sort puts usart10 before usart2. No collision
    group in today's corpus has a 2+-digit instance, so this guards a latent
    bug rather than a live one."""
    plans = [_plan("usart1", "usart10", "TE"), _plan("usart1", "usart2", "TE")]
    kept, conflicts = rust_codegen.resolve_instance_collisions(plans)
    assert conflicts == []                       # they agree
    assert kept[0].source_instance == "usart2", "picked usart10 over usart2"


def test_collision_input_is_already_validator_gated():
    """Plans reach this function only after the --validated gate, so both
    sides of a conflict are judge-`enforce`. This pins the ordering
    assumption the tie-break rests on (see inject_from_run.main)."""
    src = (APP_DIR / "inject_from_run.py").read_text()
    gate = src.index("gate_map=gate_map")
    collide = src.index("resolve_instance_collisions")
    chunks = src.index("if args.chunks:")
    assert gate < collide < chunks, (
        "pipeline order changed: collisions must be resolved after the "
        "validator gate and before quote re-verification")


def test_distinct_registers_do_not_collide():
    a = _plan("i2c1", "i2c2", "TEXTEN")
    b = _plan("i2c1", "i2c3", "TEXTEN")
    b.reg_name, b.reg_lower = "OAR1", "oar1"
    kept, conflicts = rust_codegen.resolve_instance_collisions([a, b])
    assert len(kept) == 2 and conflicts == []


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    print("Running instance-alias tests...\n")
    for t in tests:
        try:
            t()
            print(f"✓ {t.__name__}")
            passed += 1
        except Exception as e:                                # noqa: BLE001
            print(f"✗ {t.__name__}: {e}")
            failed += 1
    print(f"\n{'=' * 60}\nResults: {passed} passed, {failed} failed\n{'=' * 60}")
    if failed:
        sys.exit(1)
