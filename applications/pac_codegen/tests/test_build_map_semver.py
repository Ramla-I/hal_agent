#!/usr/bin/env python3
"""test_build_map_semver.py -- cargo version-requirement matching.

build_map.caret_matches_0_16 answers "does this req admit exactly 0.16.0?" and
feeds the HAL-on-0.16 adoption map. The old version substring-matched "0.16"
and so wrongly accepted `=0.16.1`, `^0.16.1`, and `<0.16` — none of which admit
0.16.0 — inflating the adoption count.

Run directly or under pytest.
"""

import sys
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent / "experiments"
sys.path.insert(0, str(EXP))

from build_map import caret_matches_0_16 as m  # noqa: E402


class CaretMatches(unittest.TestCase):
    def test_admits_0_16_0(self):
        for req in ("0.16", "0.16.0", "^0.16", "^0.16.0", "=0.16.0",
                    ">=0.16", ">=0.16.0", "<0.17", "<=0.16.0",
                    ">=0.14, <0.17"):
            self.assertTrue(m(req), f"{req!r} should admit 0.16.0")

    def test_does_not_admit_0_16_0(self):
        for req in ("=0.16.1", "^0.16.1", "<0.16", "^0.15.1",
                    ">=0.16.1", ">0.16.0", "0.15", "^0.17",
                    ">=0.14, <0.16"):
            self.assertFalse(m(req), f"{req!r} must NOT admit 0.16.0")


if __name__ == "__main__":
    unittest.main()
