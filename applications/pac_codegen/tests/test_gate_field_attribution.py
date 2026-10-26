#!/usr/bin/env python3
"""test_gate_field_attribution.py -- two peripherals, one register NAME.

WHAT THIS GUARDS
----------------
Triage decides whether a compile-confirmed violation is a real candidate bug or
an access the driver already guards, by scanning the surrounding function for
the PRECONDITION FIELD the gate waits on. Which field that is has to come from
the constraint that built the gate.

The map from register to field was keyed by the bare register name, and
assigned rather than merged. RM0090 constrains two different CR2s::

    adc1   CR2.SWSTART   requires  ADON set
    usart1 CR2.CPOL/..   requires  USART_CR1.TE cleared

so `cr2` ended up meaning `te` -- whichever peripheral the loop happened to
parse last. Triage then looked for a USART field at `src/adc.rs:353`, where
stm32f4xx-hal's `start_conversion` writes ADC1_CR2 two lines after calling
`self.enable()`. It found no `te`, and reported an ADC access the driver
guards as a candidate bug.

Across the 49 targets, 351 register names are shared by two or more
peripherals and 252 of those disagree on the precondition fields.

The register name alone cannot always be disambiguated: a whole-register gate
fires as E0277 naming the full Rust path, but a FIELD gate fires as an arity
error whose witness type carries the register and field and no module. So the
fix is two-part -- resolve exactly when the peripheral is known, fall back to
the UNION when it is not, and mark which happened.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent / "experiments"
sys.path.insert(0, str(EXP))
import stm_sweep  # noqa: E402

RM0090 = {"registers": [
    {"peripheral": "adc1", "register": "CR2",
     "gated_fields": {"SWSTART": {"operations": ["write", "modify"],
                                  "preconditions": ["ADON set"]}}},
    {"peripheral": "usart1", "register": "CR2",
     "gated_fields": {"CPOL": {"operations": ["write", "modify"],
                               "preconditions": ["USART_CR1.TE cleared"]}}},
    {"peripheral": "i2c1", "register": "CCR",
     "preconditions": {"write": ["I2C_CR1.PE cleared"]}},
]}


class GateFields(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        p = Path(self.td.name) / "c.json"
        p.write_text(json.dumps(RM0090))
        self.gf = stm_sweep._gate_fields(p)

    def tearDown(self):
        self.td.cleanup()

    def test_neither_peripheral_is_lost(self):
        """The bug: `out[reg] = per_op` kept only the last one."""
        self.assertEqual(set(self.gf["cr2"]["by_peripheral"]), {"adc1", "usart1"})

    def test_adc_keeps_adon(self):
        self.assertEqual(self.gf["cr2"]["by_peripheral"]["adc1"]["modify"],
                         ["adon"])

    def test_usart_keeps_te(self):
        self.assertEqual(self.gf["cr2"]["by_peripheral"]["usart1"]["modify"],
                         ["te"])

    def test_collision_is_flagged(self):
        self.assertTrue(self.gf["cr2"]["ambiguous"])

    def test_uncontested_register_is_not_flagged(self):
        self.assertFalse(self.gf["ccr"]["ambiguous"])


class FieldsFor(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        p = Path(self.td.name) / "c.json"
        p.write_text(json.dumps(RM0090))
        self.gf = stm_sweep._gate_fields(p)

    def tearDown(self):
        self.td.cleanup()

    def test_full_path_resolves_the_peripheral(self):
        """THE REGRESSION. A whole-register gate names the module, so the ADC
        site must be told to look for ADON, not USART's TE."""
        fields, how, periph, ident = stm_sweep._fields_for(
            self.gf, "stm32f4::stm32f429::adc1::cr2::CR2rs", "cr2", "modify")
        self.assertEqual(fields, ["adon"])
        self.assertEqual(how, "exact")
        self.assertEqual(periph, "adc1")
        self.assertEqual(ident.get("peripheral"), "adc1")

    def test_the_other_peripheral_too(self):
        fields, how, periph, _ = stm_sweep._fields_for(
            self.gf, "stm32f4::stm32f429::usart1::cr2::CR2rs", "cr2", "modify")
        self.assertEqual(fields, ["te"])
        self.assertEqual(how, "exact")
        self.assertEqual(periph, "usart1")

    def test_bare_spec_falls_back_to_the_union_and_says_so(self):
        """A field gate fires as an arity error carrying `CR2rs` and no module.
        Looking for either field can over-credit a site as guarded, which
        declines to invent a bug; the row has to record that it happened."""
        fields, how, periph, ident = stm_sweep._fields_for(
            self.gf, "CR2rs", "cr2", "modify")
        self.assertEqual(fields, ["adon", "te"])
        self.assertEqual(how, "union")
        self.assertEqual(periph, "", "a union names no single peripheral")
        self.assertEqual(
            [c["peripheral"] for c in ident["candidates"]],
            ["adc1", "usart1"],
            "under a union the constraint identity is the CANDIDATE LIST, "
            "never a silent pick")

    def test_bare_spec_on_an_uncontested_register_is_not_a_union(self):
        fields, how, periph, ident = stm_sweep._fields_for(
            self.gf, "CCRrs", "ccr", "write")
        self.assertEqual(fields, ["pe"])
        self.assertEqual(how, "only")
        self.assertEqual(periph, "i2c1",
                         "an uncontested name resolves to its one peripheral")

    def test_unknown_register_yields_nothing(self):
        self.assertEqual(stm_sweep._fields_for(self.gf, "X", "nope", "write"),
                         ([], "none", "", {}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
