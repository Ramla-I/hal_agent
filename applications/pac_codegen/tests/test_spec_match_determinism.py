#!/usr/bin/env python3
"""test_spec_match_determinism.py -- one register name containing another.

WHAT THIS GUARDS
----------------
`classify` decides which gated register a diagnostic is about by testing each
gated spec for membership in the message. That is a SUBSTRING test, and
register names nest::

    CRrs   is a substring of   ACRrs, AWD2CRrs, AWD3CRrs, BDCRrs, CCRrs, TDCRrs
    DRrs   is a substring of   TXDRrs

Seven collisions in rm0440 alone. A diagnostic naming `BDCRrs` therefore
matches two specs, and `named[0]` decided which. `gated_specs` is a SET, and
Python randomises string hashing per process, so which one won changed between
runs of the same code on the same input.

Everything downstream reads `named[0]`: the register name comes from
`_SPEC_REG_RE.search(named[0])`, so triage looked up `bdcr`'s precondition
fields on one run and `cr`'s on the next. Re-running rm0440 with no code change
moved stm32-hal2's split from 135 guarded / 86 candidate to 132 / 89. The hit
count never moved -- only the verdicts -- which is exactly the kind of drift
that reads as a real result.

The rule is longest-match-wins, with fully-qualified paths preferred: `BDCRrs`
is the register that fired; `CRrs` is an artifact of one name containing
another.
"""

import unittest


def resolve(gated_specs, message):
    """The ordering `stm_sweep.classify` applies. Kept in step with it by
    `test_matches_the_implementation` below."""
    return sorted((s for s in gated_specs if s in message),
                  key=lambda s: (-s.count("::"), -len(s), s))


SPECS = {"CRrs", "BDCRrs", "CCRrs", "ACRrs", "DRrs", "TXDRrs", "CR1rs"}


class LongestMatchWins(unittest.TestCase):
    def test_nested_name_resolves_to_the_longer(self):
        """THE REGRESSION: `CRrs` is a substring of `BDCRrs`."""
        named = resolve(SPECS, "`BDCRrs` is write-constrained by its datasheet")
        self.assertEqual(named[0], "BDCRrs")
        self.assertIn("CRrs", named, "the short one still matches, it just loses")

    def test_second_nesting(self):
        named = resolve(SPECS, "`TXDRrs` is write-constrained by its datasheet")
        self.assertEqual(named[0], "TXDRrs")

    def test_unnested_name_is_unaffected(self):
        named = resolve(SPECS, "`CR1rs` is read-constrained by its datasheet")
        self.assertEqual(named[0], "CR1rs")

    def test_fully_qualified_path_beats_a_bare_name(self):
        """A whole-register gate names the full path, which also identifies
        the PERIPHERAL -- worth more than length alone."""
        specs = {"CCRrs", "stm32f4::stm32f429::i2c1::ccr::CCRrs"}
        named = resolve(specs, "`stm32f4::stm32f429::i2c1::ccr::CCRrs` is "
                               "write-constrained by its datasheet")
        self.assertEqual(named[0], "stm32f4::stm32f429::i2c1::ccr::CCRrs")

    def test_no_match_is_empty(self):
        self.assertEqual(resolve(SPECS, "unrelated error"), [])


class Deterministic(unittest.TestCase):
    def test_order_does_not_depend_on_set_iteration(self):
        """The bug was `[s for s in gated_specs if ..]` over a set: correct
        contents, arbitrary order. Feeding the same specs in many different
        orders must give one answer."""
        import itertools
        msg = "`BDCRrs` is write-constrained by its datasheet"
        answers = {resolve(set(p), msg)[0]
                   for p in itertools.permutations(sorted(SPECS))}
        self.assertEqual(answers, {"BDCRrs"})

    def test_full_order_is_stable_not_just_the_head(self):
        import itertools
        msg = "`BDCRrs` is write-constrained by its datasheet"
        orders = {tuple(resolve(set(p), msg))
                  for p in itertools.permutations(sorted(SPECS))}
        self.assertEqual(len(orders), 1, f"unstable orderings: {orders}")


class MatchesTheImplementation(unittest.TestCase):
    def test_matches_the_implementation(self):
        """The helper above duplicates one expression in stm_sweep. If that
        expression changes and this does not, the test is guarding nothing."""
        import re
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experiments"))
        src = (Path(__file__).resolve().parent.parent / "experiments"
               / "stm_sweep.py").read_text()
        self.assertIn("key=lambda s: (-s.count(\"::\"), -len(s), s)", src,
                      "stm_sweep no longer sorts matches the way this test "
                      "assumes; update both together")
        self.assertNotIn('named = [s for s in gated_specs if s in e["message"]]',
                         src, "the set-order-dependent form is back")


if __name__ == "__main__":
    unittest.main(verbosity=2)
