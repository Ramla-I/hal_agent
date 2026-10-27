#!/usr/bin/env python3
"""test_gate_contradiction_redundancy.py -- three emitter correctness fixes.

WHAT THIS GUARDS
----------------
Three decisions RegisterPlan.__init__ makes while pooling constraints, each of
which was wrong in a way that silently weakened or mis-merged a gate:

  1. SIGNATURE COMPLETENESS (`_plan_signature`)
     Sibling instances (I2C1/I2C2/...) share one Rust module, so their plans
     are reconciled by signature. The signature fingerprinted field gates by
     NAME only, so two instances that name the same field but gate it on
     DIFFERENT conditions looked identical and were merged silently, dropping
     one reading. The condition is now part of the fingerprint.

  2. CONTRADICTORY GATES ARE DROPPED, NOT FORBIDDEN
     Two preconditions on one field in opposite states (set vs cleared) can
     never both hold -- a bad reading, usually from the derived modify bucket
     (read wants EN set, write wants it cleared). The op is now dropped
     explicitly and reported, and left UNGATED, instead of being forbidden
     (kept in the gated set with no gate, so only `unsafe` reached it). A
     register we forbid all safe access to as the product of a contradiction
     makes no sense. If dropping empties the register, UnsatisfiableGate.

  3. REDUNDANCY IS PER SURFACE, NOT THE UNION
     A field gate is suppressed as redundant only when EVERY surface that can
     write the field (write AND modify) already demands its condition. The old
     test compared against the UNION of write+modify conditions, so a field
     required on modify but not on plain write was wrongly dropped -- a bare
     write would then reach the field with its condition unchecked.

No toolchain needed -- these are pure plan-construction assertions.

Run directly (`python test_gate_contradiction_redundancy.py`) or under pytest.
"""

import contextlib
import io
import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR.parent.parent))

import rust_codegen  # noqa: E402
from defs import FieldCondition, RegisterInfo, StateGate  # noqa: E402


def _sg(target_register, operation, conds, fields=None, text="x"):
    """A state_gate. `conds` is a list of (source_register, field, state)."""
    return StateGate(
        target_register=target_register,
        target_operation=operation,
        target_fields=list(fields or []),
        preconditions=[FieldCondition(register=r, field=f, state=s)
                       for (r, f, s) in conds],
        postconditions=[],
        consequence="undefined behavior",
        datasheet_text=text,
    )


def _ri(abbr, constraints):
    return RegisterInfo(
        datasheet_register_abbreviation=abbr,
        address_offset="0x00", reset_value="0x0", size=32,
        subfields=[], access_constraints_v2=constraints,
    )


def _plan(abbr, constraints, peripheral="adc1"):
    return rust_codegen.RegisterPlan(
        _ri(abbr, constraints), peripheral, field_level_gating=True)


class PlanSignature(unittest.TestCase):
    """Fix 1: the sibling-reconciliation fingerprint must see field conditions."""

    def _field_plan(self, state):
        return _plan("ADC_CR2", [
            _sg("ADC_CR2", "write", [("RCC_APB2ENR", "ADCEN", state)],
                fields=["JQOVFIE"])])

    def test_same_field_different_condition_differs(self):
        """THE REGRESSION. Same field name, opposite conditions: a name-only
        fingerprint tied these and merged them, dropping one reading."""
        sig = rust_codegen._plan_signature
        p_set = self._field_plan("set")
        p_clr = self._field_plan("cleared")
        # Both genuinely name the same field -- a name-only test would tie them.
        self.assertEqual(set(p_set.field_gates), set(p_clr.field_gates))
        self.assertNotEqual(sig(p_set), sig(p_clr))

    def test_same_field_same_condition_matches(self):
        """And it must not over-split: identical field + condition is one rule."""
        sig = rust_codegen._plan_signature
        self.assertEqual(sig(self._field_plan("set")),
                         sig(self._field_plan("set")))


class ContradictoryGate(unittest.TestCase):
    """Fix 2: contradictory ops are dropped + reported + left ungated."""

    def test_all_dropped_raises_unsatisfiable(self):
        """Register whose only gate is self-contradictory: nothing left."""
        with self.assertRaises(rust_codegen.UnsatisfiableGate):
            _plan("AES_IVR0", [
                _sg("AES_IVR0", "write",
                    [("AES_CR", "EN", "set"), ("AES_CR", "EN", "cleared")])],
                 peripheral="aes")

    def test_partial_drop_leaves_register_ungated_not_forbidden(self):
        """write (and its derived modify) are contradictory and drop; the
        surviving read keeps the register. The dropped ops are UNGATED -- their
        markers are not withheld. forbidden_ops exists (write_once / sequence /
        delay withhold ops through it), but the contradiction path must NOT use
        it: a contradictory reading leaves the op ungated, it does not forbid."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            plan = _plan("AES_IVR0", [
                _sg("AES_IVR0", "write",
                    [("AES_CR", "EN", "set"), ("AES_CR", "EN", "cleared")]),
                _sg("AES_IVR0", "read", [("AES_CR", "EN", "set")])],
                peripheral="aes")

        self.assertNotIn("write", plan.preconditions)
        self.assertNotIn("modify", plan.preconditions)   # derived bucket, also contradictory
        self.assertIn("read", plan.preconditions)

        # Dropped, not forbidden: the contradictory ops must not land in
        # forbidden_ops (which exists for the feature kinds).
        self.assertNotIn("write", plan.forbidden_ops)
        self.assertNotIn("modify", plan.forbidden_ops)
        ops = {op for _, _, op in plan.gated_ops()}
        self.assertNotIn("write", ops)   # no marker withheld -> freely callable
        self.assertNotIn("modify", ops)
        self.assertIn("read", ops)

        # Reported both ways: recorded on the plan and warned on stderr.
        self.assertTrue(any("contradicts" in u for u in plan._unsatisfiable))
        self.assertIn("left ungated", err.getvalue())


class FieldGateRedundancy(unittest.TestCase):
    """Fix 3: redundancy is decided per write surface, not against the union."""

    def test_kept_when_only_modify_covers_it(self):
        """THE REGRESSION. A read gate feeds read+modify; plain write is
        unconstrained. A field gate matching that condition is NOT redundant:
        a bare write would set the field without the check. The old union test
        (write ∪ modify) saw the condition on modify and wrongly dropped it."""
        plan = _plan("ADC_CR2", [
            _sg("ADC_CR2", "read", [("RCC_APB2ENR", "ADCEN", "set")]),
            _sg("ADC_CR2", "write", [("RCC_APB2ENR", "ADCEN", "set")],
                fields=["JQOVFIE"])])
        self.assertNotIn("write", plan.preconditions)   # write truly uncovered
        self.assertIn("modify", plan.preconditions)
        self.assertIn("jqovfie", plan.field_gates)      # lock kept

    def test_pruned_when_every_surface_covers_it(self):
        """Genuinely redundant: a whole-register write gate forces the same
        condition on write AND the derived modify, so the field lock adds
        nothing and is suppressed."""
        plan = _plan("ADC_CR2", [
            _sg("ADC_CR2", "write", [("RCC_APB2ENR", "ADCEN", "set")]),
            _sg("ADC_CR2", "write", [("RCC_APB2ENR", "ADCEN", "set")],
                fields=["JQOVFIE"])])
        self.assertIn("write", plan.preconditions)
        self.assertIn("modify", plan.preconditions)
        self.assertNotIn("jqovfie", plan.field_gates)
        self.assertTrue(any("JQOVFIE" in r for r in plan._redundant_fields))


if __name__ == "__main__":
    unittest.main()
