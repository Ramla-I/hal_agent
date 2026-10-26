#!/usr/bin/env python3
"""test_bitband_scan.py -- the bit-to-field map, and the three shapes.

WHAT THIS GUARDS
----------------
`bitband_scan.py` finds register writes that leave the typed API: bit banding
passes the register as a RAW POINTER, so the trait bound our enforcement rests
on is never checked. To say which FIELD such a write lands on, it reads bit
offsets out of the PAC's own generated reader accessors.

Those accessors come in two shapes, and only one of them has a shift::

    LSEON_R::new((self.bits & 1) != 0)              offset 0, width 1
    LSEBYP_R::new(((self.bits >> 2) & 1) != 0)      offset 2, width 1
    RTCSEL_R::new(((self.bits >> 8) & 3) as u8)     offset 8, width 2

The first version of the pattern did not allow the closing paren that sits
between the shift and the mask, so it matched ONLY fields at offset 0. The
scanner then reported LSEON and silently missed LSEBYP, RTCEN and BDRST --
three of the four sites it exists to find, in the one case already verified by
hand. A scanner that under-reports by 75% looks exactly like a clean result.

The three call shapes are pinned too, because collapsing them is the same
mistake in a different place: a computed bit is not a known field, and a
macro-generated target is not a known register.
"""

import sys
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent / "experiments"
sys.path.insert(0, str(EXP))
import bitband_scan as bb  # noqa: E402

# Shaped exactly like svd2rust's output for RCC_BDCR.
BDCR_RS = """
impl R {
    #[doc = "Bit 0 - LSE oscillator enable"]
    #[inline(always)]
    pub fn lseon(&self) -> LSEON_R {
        LSEON_R::new((self.bits & 1) != 0)
    }
    #[doc = "Bit 2 - LSE oscillator bypass"]
    #[inline(always)]
    pub fn lsebyp(&self) -> LSEBYP_R {
        LSEBYP_R::new(((self.bits >> 2) & 1) != 0)
    }
    #[doc = "Bits 8:9 - RTC clock source selection"]
    #[inline(always)]
    pub fn rtcsel(&self) -> RTCSEL_R {
        RTCSEL_R::new(((self.bits >> 8) & 3) as u8)
    }
    #[doc = "Bit 15 - RTC clock enable"]
    #[inline(always)]
    pub fn rtcen(&self) -> RTCEN_R {
        RTCEN_R::new(((self.bits >> 15) & 1) != 0)
    }
}
"""

CONSTRAINTS = {"registers": [{
    "peripheral": "rcc", "register": "BDCR",
    "gated_fields": {
        "LSEON": {"operations": ["write", "modify"],
                  "preconditions": ["PWR_CR.DBP set"]},
        "LSEBYP": {"operations": ["write", "modify"],
                   "preconditions": ["PWR_CR.DBP set"]},
        "RTCEN": {"operations": ["write", "modify"],
                  "preconditions": ["PWR_CR.DBP set"]},
    }}]}


class FieldMap(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.td = tempfile.TemporaryDirectory()
        dev = Path(self.td.name)
        (dev / "rcc").mkdir(parents=True)
        (dev / "rcc" / "bdcr.rs").write_text(BDCR_RS)
        self.fmap = bb.field_map(dev)

    def tearDown(self):
        self.td.cleanup()

    def test_offset_zero_field(self):
        """`(self.bits & 1)` -- the shape with no shift at all."""
        self.assertEqual(self.fmap[("rcc", "bdcr")]["lseon"], (0, 1))

    def test_shifted_field(self):
        """THE REGRESSION: `((self.bits >> 2) & 1)` has a paren between the
        shift and the mask, and the first pattern rejected it."""
        self.assertEqual(self.fmap[("rcc", "bdcr")]["lsebyp"], (2, 1))

    def test_multi_bit_field(self):
        self.assertEqual(self.fmap[("rcc", "bdcr")]["rtcsel"], (8, 2))

    def test_every_field_is_found(self):
        """Four fields in, four out -- a map missing three of them still
        produces a plausible-looking report."""
        self.assertEqual(set(self.fmap[("rcc", "bdcr")]),
                         {"lseon", "lsebyp", "rtcsel", "rtcen"})

    def test_bit_resolves_to_the_field_containing_it(self):
        f = self.fmap[("rcc", "bdcr")]
        self.assertEqual(bb.field_at(f, 0), "lseon")
        self.assertEqual(bb.field_at(f, 2), "lsebyp")
        self.assertEqual(bb.field_at(f, 9), "rtcsel", "9 is inside RTCSEL 8:9")
        self.assertEqual(bb.field_at(f, 16), "", "BDRST is not in this fixture")


class CallShapes(unittest.TestCase):
    """Three shapes occur in real drivers and mean three different things."""

    def setUp(self):
        import json
        import tempfile
        self.td = tempfile.TemporaryDirectory()
        dev = Path(self.td.name) / "dev"
        (dev / "rcc").mkdir(parents=True)
        (dev / "rcc" / "bdcr.rs").write_text(BDCR_RS)
        self.fmap = bb.field_map(dev)
        c = Path(self.td.name) / "c.json"
        c.write_text(json.dumps(CONSTRAINTS))
        self.cmap = bb.constrained_fields(c)
        self.src = Path(self.td.name) / "src"
        self.src.mkdir()

    def tearDown(self):
        self.td.cleanup()

    def rows(self, text):
        (self.src / "a.rs").write_text(text)
        return bb.scan([self.src], self.fmap, self.cmap, {})

    def test_resolved_literal_bit_on_a_constrained_field(self):
        r = self.rows("unsafe { bb::set(rcc.bdcr(), 2); }\n")[0]
        self.assertEqual(r["state"], "resolved")
        self.assertEqual(r["field"], "lsebyp")
        self.assertTrue(r["constrained"])
        self.assertEqual(r["preconditions"], ["PWR_CR.DBP set"])

    def test_resolved_literal_bit_on_an_unconstrained_field(self):
        """RTCSEL's neighbours are not all constrained; bit 9 is inside
        RTCSEL, which this fixture does not gate."""
        r = self.rows("unsafe { bb::set(rcc.bdcr(), 9); }\n")[0]
        self.assertEqual(r["field"], "rtcsel")
        self.assertFalse(r["constrained"])

    def test_computed_bit_is_not_given_a_field(self):
        """`c*4 + 1` is not a field. Naming one would be a guess."""
        r = self.rows("unsafe { bb::write(rcc.bdcr(), c*4 + 1, b); }\n")[0]
        self.assertEqual(r["state"], "bit-dynamic")
        self.assertEqual(r["field"], "")
        self.assertEqual(r["candidate_fields"], ["lsebyp", "lseon", "rtcen"])

    def test_macro_target_is_opaque_not_absent(self):
        """`Self::Bus::enr(rcc)` names no register. It is counted, because
        silently dropping it is how every peripheral enable in stm32f4xx-hal's
        RCC would vanish from the report."""
        r = self.rows("unsafe { bb::set(Self::Bus::enr(rcc), $bit); }\n")[0]
        self.assertEqual(r["state"], "opaque")
        self.assertFalse(r["constrained"])

    def test_commented_out_call_is_not_a_call(self):
        self.assertEqual(self.rows("// bb::set(rcc.bdcr(), 0);\n"), [])

    def test_clear_counts_as_a_write(self):
        r = self.rows("unsafe { bb::clear(rcc.bdcr(), 15); }\n")[0]
        self.assertEqual(r["op"], "clear")
        self.assertEqual(r["field"], "rtcen")
        self.assertTrue(r["constrained"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
