#!/usr/bin/env python3
"""test_spec_match_determinism.py -- one register name containing another.

WHAT THIS GUARDS
----------------
`classify` decides which gated register a diagnostic is about by matching each
gated spec against the message. Register names nest::

    CRrs   is inside   ACRrs, AWD2CRrs, AWD3CRrs, BDCRrs, CCRrs, TDCRrs,
                       and hrtim's CPT1CRrs and ICRrs
    DRrs   is inside   TXDRrs
    IERrs  is inside   DIERrs

Substring-in-message matching failed on that twice, in two different ways:

1. BOTH names gated. A diagnostic naming `BDCRrs` matched two specs and
   `named[0]` decided which; `gated_specs` is a SET with per-process hash
   randomisation, so the winner changed between runs. Re-running rm0440 with
   no code change moved stm32-hal2's split from 135 guarded / 86 candidate to
   132 / 89. Longest-match-wins fixed this.

2. Only the SHORT name gated. Longest-match cannot help when the containing
   name is not a candidate at all: hrtim's generic accessor API fails
   definition-side on `<<TIM as Instance>::RB as TimExt>::CPT1CRrs` --
   `cpt1cr` is UNGATED, its markers are present, every instantiation
   compiles; the failure is pure adoption friction. But the embedded `CRrs`
   matched, so 14 friction errors across three manuals were recorded as
   candidate bugs, wearing ADC precondition fields on G4 and a JPEG codec
   quote on H7.

The rule now: a bare spec matches only a whole identifier TOKEN of the
message; a qualified spec (containing `::`) is not a single token and keeps
substring matching, because the path itself is the specificity. Among the
matches, longest (and most-qualified) wins, deterministically.
"""

import re
import unittest

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def resolve(gated_specs, message):
    """The matching `stm_sweep.classify` applies. Kept in step with it by
    `test_matches_the_implementation` below."""
    tokens = set(_IDENT_RE.findall(message))
    return sorted((s for s in gated_specs
                   if (s in tokens if "::" not in s else s in message)),
                  key=lambda s: (-s.count("::"), -len(s), s))


SPECS = {"CRrs", "BDCRrs", "CCRrs", "ACRrs", "DRrs", "TXDRrs", "CR1rs"}


class LongestMatchWins(unittest.TestCase):
    def test_nested_name_resolves_to_the_longer(self):
        """Both names gated: the diagnostic is about `BDCRrs`, and the
        embedded `CRrs` no longer matches at all -- `BDCRrs` is one token."""
        named = resolve(SPECS, "`BDCRrs` is write-constrained by its datasheet")
        self.assertEqual(named, ["BDCRrs"])

    def test_second_nesting(self):
        named = resolve(SPECS, "`TXDRrs` is write-constrained by its datasheet")
        self.assertEqual(named, ["TXDRrs"])

    def test_unnested_name_is_unaffected(self):
        named = resolve(SPECS, "`CR1rs` is read-constrained by its datasheet")
        self.assertEqual(named[0], "CR1rs")

    def test_fully_qualified_path_beats_a_bare_name(self):
        """A whole-register gate names the full path, which also identifies
        the PERIPHERAL -- worth more than length alone. The path's leaf is a
        token, so the bare spec matches too; the qualified one outranks it."""
        specs = {"CCRrs", "stm32f4::stm32f429::i2c1::ccr::CCRrs"}
        named = resolve(specs, "`stm32f4::stm32f429::i2c1::ccr::CCRrs` is "
                               "write-constrained by its datasheet")
        self.assertEqual(named[0], "stm32f4::stm32f429::i2c1::ccr::CCRrs")
        self.assertIn("CCRrs", named)

    def test_no_match_is_empty(self):
        self.assertEqual(resolve(SPECS, "unrelated error"), [])


class UngatedContainerName(unittest.TestCase):
    """THE hrtim REGRESSION: the container name is NOT gated, so nothing may
    match -- classify must fall through to generic friction."""

    HRTIM_SPECS = {"CRrs", "IERrs", "CR1rs", "SQR1rs"}  # rm0440-shaped: no CPT1CRrs

    def test_ungated_container_matches_nothing(self):
        named = resolve(self.HRTIM_SPECS,
                        "`<<TIM as Instance>::RB as TimExt>::CPT1CRrs` is "
                        "modify-constrained by its datasheet")
        self.assertEqual(named, [], "gated CRrs claimed ungated CPT1CRrs -- "
                         "this is how 14 friction errors became candidate bugs")

    def test_second_container_pair(self):
        named = resolve(self.HRTIM_SPECS,
                        "`<<TIM as Instance>::RB as MasterExt>::DIERrs` is "
                        "modify-constrained by its datasheet")
        self.assertEqual(named, [], "gated IERrs claimed ungated DIERrs")

    def test_gated_assoc_leaf_still_matches(self):
        """The mirror image must keep working: f4xx-hal's `UartRB` paths fail
        on registers that genuinely ARE gated. Those are real enforcement at
        the generic site, and the leaf is an exact token."""
        named = resolve({"SRrs", "CR3rs"},
                        "`<Self as UartRB>::SRrs` is read-constrained by its "
                        "datasheet")
        self.assertEqual(named, ["SRrs"])


class Deterministic(unittest.TestCase):
    def test_order_does_not_depend_on_set_iteration(self):
        """The original bug was `[s for s in gated_specs if ..]` over a set:
        correct contents, arbitrary order. Feeding the same specs in many
        different orders must give one answer."""
        import itertools
        msg = "`BDCRrs` is write-constrained by its datasheet"
        answers = {resolve(set(p), msg)[0]
                   for p in itertools.permutations(sorted(SPECS))}
        self.assertEqual(answers, {"BDCRrs"})

    def test_full_order_is_stable_not_just_the_head(self):
        import itertools
        specs = {"CCRrs", "stm32f4::stm32f429::i2c1::ccr::CCRrs"}
        msg = ("`stm32f4::stm32f429::i2c1::ccr::CCRrs` is "
               "write-constrained by its datasheet")
        orders = {tuple(resolve(set(p), msg))
                  for p in itertools.permutations(sorted(specs))}
        self.assertEqual(len(orders), 1, f"unstable orderings: {orders}")


class MatchesTheImplementation(unittest.TestCase):
    def test_matches_the_implementation(self):
        """The helper above duplicates one expression in stm_sweep (and its
        mirror in dependent_compile). If those change and this does not, the
        test is guarding nothing."""
        from pathlib import Path
        exp = Path(__file__).resolve().parent.parent / "experiments"
        for name in ("stm_sweep.py", "dependent_compile.py"):
            src = (exp / name).read_text()
            self.assertIn('if (s in tokens if "::" not in s', src,
                          f"{name} no longer token-matches bare specs the way "
                          "this test assumes; update both together")
            self.assertNotIn('if s in e["message"])', src,
                             f"the substring-anywhere form is back in {name}")
        src = (exp / "stm_sweep.py").read_text()
        self.assertIn("key=lambda s: (-s.count(\"::\"), -len(s), s)", src,
                      "stm_sweep no longer sorts matches the way this test "
                      "assumes; update both together")


if __name__ == "__main__":
    unittest.main(verbosity=2)
