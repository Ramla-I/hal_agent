#!/usr/bin/env python3
"""test_classify_attribution.py -- rows must wear their own peripheral and op.

WHAT THIS GUARDS
----------------
Three ways a ledger row lied about identity, all found by reading the ledger:

1. OP. classify re-derived the operation from the E0277 message phrases, and a
   field gate (E0061) matches neither, so every field-gate row fell through to
   `read`. i2c.rs:53 -- a txdr WRITE inside busy_wait! -- was `write` on the
   two manuals whose constraint became a whole-register gate and `read` on the
   ten whose constraint became a field gate. The op now comes from the Hit;
   `classify_diagnostic` already knew it ("a field gate's operation is always
   a write").

2. PERIPHERAL, from the path. A concrete E0277 names the full path
   (`stm32f4::stm32f469::flash::cr::CRrs`); classify matched bare specs and
   never looked, so every contested register name fell to a union that opened
   with another peripheral's quote -- FLASH cr rows led with "[adc]".

3. PERIPHERAL, from the field. An E0061 witness type names the gated FIELD
   (`Cr2AdonFieldWitness` -> adon), and a field only one candidate gates
   identifies the peripheral. Discarding it let rm0090-shaped manuals put a
   USART quote on an ADC write.

Plus the honesty label: a PROJECTION (`<ADC as Instance>::CR2rs`) names the
trait's register, not the code's. rm0041 gates cr2 only for usart1, so the
lookup dressed ADC's power_up() in usart's TE quote with `only` confidence.
Such rows are labelled `projection`, never `only`/`exact`.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experiments"))
import enforcement                                              # noqa: E402
from stm_sweep import _fields_for                               # noqa: E402


def e0277(path, op="modify"):
    return {"code": {"code": "E0277"},
            "message": f"`{path}` is {op}-constrained by its datasheet",
            "spans": []}


def e0061(register="Cr2", field="Adon"):
    return {"code": {"code": "E0061"},
            "message": "this function takes 3 arguments but 2 were supplied",
            "spans": [{"label": f"argument #1 of type "
                                f"`&{register}{field}FieldWitness` is missing",
                       "is_primary": True}]}


GATE_FIELDS = {
    # The GATED field (_gated, off the witness type) is deliberately distinct
    # from the PRECONDITION fields here: txdr gates `txdata` while requiring
    # `txe`, and a fixture where the two coincide (adon gates adon) passed a
    # hint-matcher that compared against the wrong set.
    "cr2": {
        "by_peripheral": {
            "adc1": {"_ident": {"constraint_ids": ["a1"],
                                "quote": "ADON = 1"},
                     "_gated": ["swstart"],
                     "write": ["adon"], "modify": ["adon"]},
            "usart1": {"_ident": {"constraint_ids": ["u1"],
                                  "quote": "while TE is set"},
                       "_gated": ["cpol", "cpha", "lbcl"],
                       "write": ["te"], "modify": ["te"]},
        },
        "union": {"write": ["adon", "te"], "modify": ["adon", "te"]},
        "ambiguous": True,
    },
    "cr": {
        "by_peripheral": {
            "usart1": {"_ident": {"constraint_ids": ["u2"],
                                  "quote": "usart only"},
                       "modify": ["ue"]},
        },
        "union": {"modify": ["ue"]},
        "ambiguous": False,
    },
}


class OpComesFromTheHit(unittest.TestCase):
    def test_field_gate_operation_is_write_not_read(self):
        """THE REGRESSION: E0061 says neither "write-constrained" nor
        "modify-constrained"; the message-sniffing fallback stamped `read`."""
        hit = enforcement.classify_diagnostic(e0061())
        self.assertEqual(hit.kind, "field")
        self.assertEqual(hit.operation, "write")

    def test_register_gate_operation_parsed(self):
        hit = enforcement.classify_diagnostic(
            e0277("stm32f1::stm32f100::adc1::cr2::CR2rs", "modify"))
        self.assertEqual(hit.operation, "modify")


class PathIdentifiesThePeripheral(unittest.TestCase):
    def test_concrete_e0277_carries_its_path(self):
        hit = enforcement.classify_diagnostic(
            e0277("stm32f1::stm32f100::adc1::cr2::CR2rs"))
        self.assertEqual(hit.path, "stm32f1::stm32f100::adc1::cr2::CR2rs")
        self.assertFalse(hit.projection)

    def test_full_path_resolves_exact_with_the_right_quote(self):
        fields, how, periph, ident = _fields_for(
            GATE_FIELDS, "stm32f1::stm32f100::adc1::cr2::CR2rs",
            "cr2", "modify")
        self.assertEqual((how, periph), ("exact", "adc1"))
        self.assertIn("ADON", ident["quote"])

    def test_bare_spec_still_falls_to_union(self):
        _, how, periph, ident = _fields_for(GATE_FIELDS, "CR2rs",
                                            "cr2", "modify")
        self.assertEqual(how, "union")
        self.assertEqual(len(ident["candidates"]), 2)


class FieldIdentifiesThePeripheral(unittest.TestCase):
    def test_unique_gated_field_resolves_the_candidate(self):
        """`cpol` is GATED only by the USART: the E0061 witness carries it,
        and that is as identifying as a module path. The row's fields are
        still the PRECONDITIONS (te), not the gated field."""
        fields, how, periph, ident = _fields_for(
            GATE_FIELDS, "CR2rs", "cr2", "write", field_hint="cpol")
        self.assertEqual((how, periph), ("field", "usart1"))
        self.assertEqual(fields, ["te"])
        self.assertIn("TE", ident["quote"])

    def test_hint_matches_gated_names_not_precondition_names(self):
        """THE REGRESSION: txdr gates `txdata` but requires `txe`. A matcher
        comparing the hint against precondition fields resolves nothing --
        and in the first shipped version, resolved nothing corpus-wide while
        its test passed on the adon coincidence."""
        _, how, periph, _ = _fields_for(
            GATE_FIELDS, "CR2rs", "cr2", "write", field_hint="swstart")
        self.assertEqual((how, periph), ("field", "adc1"))
        _, how2, _, _ = _fields_for(
            GATE_FIELDS, "CR2rs", "cr2", "write", field_hint="te")
        self.assertEqual(how2, "union",
                         "a precondition name must NOT resolve a candidate")

    def test_shared_gated_field_still_unions(self):
        shared = {"cr2": {
            "by_peripheral": {
                "adc1": {"_ident": {}, "_gated": ["en"], "write": ["x"]},
                "usart1": {"_ident": {}, "_gated": ["en"], "write": ["y"]}},
            "union": {"write": ["x", "y"]}, "ambiguous": True}}
        _, how, _, _ = _fields_for(shared, "CR2rs", "cr2", "write",
                                   field_hint="en")
        self.assertEqual(how, "union")


class ProjectionIsLabelled(unittest.TestCase):
    def test_projection_never_wears_only_confidence(self):
        """rm0041's shape: cr2 gated for usart alone, and a generic ADC path
        fails definition-side. The single candidate is the WRONG peripheral
        for the code; the row must say `projection`, not `only`."""
        hit = enforcement.classify_diagnostic(
            e0277("<ADC as Instance>::CR2rs"))
        self.assertTrue(hit.projection)
        _, how, periph, _ = _fields_for(
            GATE_FIELDS, "CR2rs", "cr", "modify", projection=hit.projection)
        self.assertEqual(how, "projection")

    def test_projection_union_is_also_labelled(self):
        _, how, _, ident = _fields_for(GATE_FIELDS, "CR2rs", "cr2", "modify",
                                       projection=True)
        self.assertEqual(how, "projection")
        self.assertEqual(len(ident["candidates"]), 2,
                         "the candidate list survives the relabel")


if __name__ == "__main__":
    unittest.main(verbosity=2)
