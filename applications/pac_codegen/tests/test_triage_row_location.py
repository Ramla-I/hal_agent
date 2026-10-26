#!/usr/bin/env python3
"""test_triage_row_location.py -- the triage row's file must own its line.

WHAT THIS GUARDS
----------------
A triage row records where a compile-confirmed violation sits in the driver:
`{"file": .., "line": ..}`. Those two values used to come from two DIFFERENT
collections built from the same diagnostic:

    file  <- hal_files[0]   the alphabetically FIRST file the diagnostic
                            touches anywhere (primary span, macro expansions)
    line  <- sites[0][1]    the line of the alphabetically first (path, line)

For a diagnostic confined to one file they agree. For a macro error spanning
two files -- and these HALs generate whole peripheral APIs from macros -- the
row could pair file A's name with a line number that only exists in file B.

The verdict itself was computed at the right place (triage_hit takes the site
tuple), so the COUNTS were right; the recorded location lied. And the location
is not cosmetic: trace_hal joins driver functions on exactly (file, line) via
`enclosing()`, so a mismatched pair attaches the violation to the wrong
function or, more likely, to none -- silently, because a failed join just
means "no entry points reach this site".

The fix carries the relative name inside the site tuple itself: (abs, line,
rel), so file and line can never come from different spans again.
"""

import sys
import tempfile
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent / "experiments"
sys.path.insert(0, str(EXP))
import stm_sweep  # noqa: E402

GATE_FIELDS = {"ccr": {"by_peripheral": {"i2c1": {"write": ["pe"]}},
                       "union": {"write": ["pe"]}, "ambiguous": False}}


def diag(hal_files, sites, message="`CCRrs` is write-constrained by its datasheet"):
    return {"code": "E0277", "message": message, "labels": "",
            "hal_files": hal_files, "sites": sites}


class RowLocation(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        # The file the SITE is in. Establishes the precondition so triage has
        # something to find and the row is actually emitted.
        self.zpath = Path(self.td.name) / "z_late.rs"
        self.zpath.write_text(
            "fn configure() {\n"
            "    x.pe().clear_bit();\n"
            "    x.ccr().write(|w| w);\n"
            "}\n")

    def tearDown(self):
        self.td.cleanup()

    def classify(self, e):
        return stm_sweep.classify([e], {"CCRrs"}, GATE_FIELDS)

    def test_file_comes_from_the_site_not_the_file_set(self):
        """THE REGRESSION. The diagnostic also touches a file that sorts
        earlier; the row must still name the file the line belongs to."""
        e = diag(hal_files=["a_early.rs", "z_late.rs"],
                 sites=[(str(self.zpath), 3, "z_late.rs")])
        res = self.classify(e)
        self.assertEqual(len(res["triage"]), 1)
        row = res["triage"][0]
        self.assertEqual((row["file"], row["line"]), ("z_late.rs", 3),
                         "file and line were taken from different spans")

    def test_single_file_diagnostic_is_unchanged(self):
        e = diag(hal_files=["z_late.rs"],
                 sites=[(str(self.zpath), 3, "z_late.rs")])
        row = self.classify(e)["triage"][0]
        self.assertEqual((row["file"], row["line"]), ("z_late.rs", 3))

    def test_verdict_is_computed_at_that_same_site(self):
        """The precondition (`pe`) is established in z_late.rs, so if triage
        looked anywhere else this would not come back corroborated."""
        e = diag(hal_files=["a_early.rs", "z_late.rs"],
                 sites=[(str(self.zpath), 3, "z_late.rs")])
        row = self.classify(e)["triage"][0]
        self.assertEqual(row["verdict"], "corroborated")

    def test_old_two_tuple_sites_still_work(self):
        """Cached or hand-built diagnostics may carry (abs, line) only; the
        fallback keeps them usable rather than crashing on site[2]."""
        e = diag(hal_files=["z_late.rs"], sites=[(str(self.zpath), 3)])
        row = self.classify(e)["triage"][0]
        self.assertEqual((row["file"], row["line"]), ("z_late.rs", 3))


if __name__ == "__main__":
    unittest.main(verbosity=2)
