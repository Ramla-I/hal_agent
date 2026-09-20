#!/usr/bin/env python3
"""test_bug_review.py -- the reviewer's marks survive every re-run.

WHAT THIS GUARDS
----------------
bug_review.csv is where a HUMAN records tp/fp judgements over the sweep's
possible-bug sites. The one property that must never break: re-running
`--init` after a fresh sweep cannot lose a mark. Everything here follows from
that.

  - a marked row whose site reappears keeps its tp_fp and note verbatim
  - a marked row whose site VANISHES from the new sweep is kept, flagged
    `stale` -- a judgement is evidence even after the site moves (the
    LOST_FINDINGS rule); an UNMARKED vanished row is dropped, because an
    empty row for a gone site is noise
  - the key deliberately excludes the driver VERSION, so a driver bump keeps
    marks wherever the site survived
  - a union-resolved row's constraint identity is the candidate LIST with the
    quotes labelled per peripheral, never a silent pick
"""

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent / "experiments"
sys.path.insert(0, str(EXP))


def make_row(**kw):
    base = {"rm": "rm0399", "device": "stm32h747cm7", "crate": "stm32-hal2",
            "version": "2.1.10", "file": "src/adc.rs", "line": 100,
            "peripheral": "adc3", "register": "cr", "operation": "modify",
            "fields": ["aden"], "field_source": "exact",
            "verdict": "unchecked", "helpers": [],
            "constraint_ids": ["abc123"], "quote": "only when ADEN=0"}
    base.update(kw)
    return base


class Review(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        root = Path(self.td.name)
        (root / "out" / "triage").mkdir(parents=True)
        import bug_review
        importlib.reload(bug_review)
        bug_review.OUT = root / "out"
        (root / "out" / "constraints").mkdir()
        bug_review.REVIEW = root / "bug_review.csv"
        bug_review.TABLE = root / "out" / "bug_review_table.md"
        self.br = bug_review
        self.tri = root / "out" / "triage" / "rm0399_stm32h747cm7_stm32-hal2.jsonl"

    def tearDown(self):
        self.td.cleanup()

    def write_sites(self, rows):
        self.tri.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def read(self):
        import csv
        with open(self.br.REVIEW, newline="") as fh:
            return {self.br.key(r): r for r in csv.DictReader(fh)}

    def test_init_builds_rows_with_empty_marks(self):
        self.write_sites([make_row(), make_row(line=200, verdict="corroborated")])
        self.br.init()
        rows = self.read()
        self.assertEqual(len(rows), 1, "only possible bugs enter the ledger")
        r = next(iter(rows.values()))
        self.assertEqual(r["tp_fp"], "")
        self.assertEqual(r["constraint_ids"], "abc123")
        self.assertIn("ADEN", r["quote"])

    def test_marks_survive_a_rerun(self):
        """THE PROPERTY. Everything else is decoration."""
        self.write_sites([make_row()])
        self.br.init()
        rows = list(self.read().values())
        rows[0]["tp_fp"] = "tp"
        rows[0]["note"] = "no ADEN check anywhere in the file"
        self.br.write_review(rows)
        self.br.init()                              # fresh sweep, same site
        r = next(iter(self.read().values()))
        self.assertEqual(r["tp_fp"], "tp")
        self.assertEqual(r["note"], "no ADEN check anywhere in the file")

    def test_version_bump_keeps_the_mark(self):
        self.write_sites([make_row()])
        self.br.init()
        rows = list(self.read().values())
        rows[0]["tp_fp"] = "fp"
        self.br.write_review(rows)
        self.write_sites([make_row(version="2.2.0")])
        self.br.init()
        r = next(iter(self.read().values()))
        self.assertEqual(r["tp_fp"], "fp")
        self.assertEqual(r["version"], "2.2.0", "machine columns refresh")

    def test_marked_vanished_site_goes_stale_not_away(self):
        self.write_sites([make_row()])
        self.br.init()
        rows = list(self.read().values())
        rows[0]["tp_fp"] = "tp"
        self.br.write_review(rows)
        self.write_sites([make_row(line=999)])      # old site gone
        self.br.init()
        rows = self.read()
        self.assertEqual(len(rows), 2)
        stale = [r for r in rows.values() if r["status"] == "stale"]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["tp_fp"], "tp")

    def test_unmarked_vanished_site_is_dropped(self):
        self.write_sites([make_row()])
        self.br.init()
        self.write_sites([make_row(line=999)])
        self.br.init()
        rows = self.read()
        self.assertEqual(len(rows), 1, "an empty row for a gone site is noise")

    def test_union_identity_is_a_labelled_list(self):
        self.write_sites([make_row(
            peripheral="", field_source="union",
            candidates=[{"peripheral": "adc1", "constraint_ids": ["a1"],
                         "quote": "rule one"},
                        {"peripheral": "usart1", "constraint_ids": ["u1"],
                         "quote": "rule two"}],
            constraint_ids=None, quote=None)])
        self.br.init()
        r = next(iter(self.read().values()))
        self.assertEqual(sorted(r["constraint_ids"].split()), ["a1", "u1"])
        self.assertIn("[adc1] rule one", r["quote"])
        self.assertIn("[usart1] rule two", r["quote"])

    def test_table_renders_marks(self):
        self.write_sites([make_row()])
        self.br.init()
        rows = list(self.read().values())
        rows[0]["tp_fp"] = "tp"; rows[0]["note"] = "real"
        self.br.write_review(rows)
        self.br.table()
        md = self.br.TABLE.read_text()
        self.assertIn("| tp |", md)
        self.assertIn("real", md)
        self.assertIn("**1** tp", md)


class Duplicates(unittest.TestCase):
    """Identity is per gated FIELD; what is still identical aggregates.

    Four field gates on one `cfgr.modify(..)` line are four different bits
    -- with `gated_field` in the key they are four distinguishable rows. A
    macro body reported once per expansion is ONE site for a reviewer; those
    byte-identical repeats collapse to a single row with `count`."""

    def setUp(self):
        Review.setUp(self)

    def tearDown(self):
        Review.tearDown(self)

    write_sites = Review.write_sites
    read = Review.read

    def test_identical_repeats_collapse_with_count(self):
        self.write_sites([make_row(gated_field="txdata")] * 5)
        self.br.init()
        rows = list(self.read().values())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["count"], "5")

    def test_distinct_gated_fields_stay_separate_rows(self):
        self.write_sites([make_row(gated_field="dcen"),
                          make_row(gated_field="icen")])
        self.br.init()
        rows = self.read()
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["gated_field"] for r in rows.values()},
                         {"dcen", "icen"})

    def test_mark_on_aggregated_row_survives(self):
        self.write_sites([make_row(gated_field="txdata")] * 3)
        self.br.init()
        import csv
        with open(self.br.REVIEW, newline="") as fh:
            rows = list(csv.DictReader(fh))
        rows[0]["tp_fp"] = "fp"
        self.br.write_review(rows)
        self.write_sites([make_row(gated_field="txdata")] * 3)
        self.br.init()
        row = next(iter(self.read().values()))
        self.assertEqual(row["tp_fp"], "fp")
        self.assertEqual(row["count"], "3")


class PortSites(unittest.TestCase):
    """The compiled PROJECTS' hits enter the ledger too -- the first version
    covered only the sweep's HALs while the handover advice pointed the
    reviewer at project rows that did not exist. Identity is JOINED from the
    per-device constraints file: one register match is exact, several share
    the name -> the labelled candidate list, the sweep's union rule."""

    def setUp(self):
        import tempfile
        self.td = tempfile.TemporaryDirectory()
        root = Path(self.td.name)
        (root / "out" / "triage").mkdir(parents=True)
        (root / "out" / "constraints").mkdir()
        import importlib, bug_review
        importlib.reload(bug_review)
        bug_review.OUT = root / "out"
        bug_review.REVIEW = root / "bug_review.csv"
        bug_review.TABLE = root / "out" / "t.md"
        bug_review.PORT_RECORDS = ["port_x.json"]
        self.br = bug_review
        self.root = root

    def tearDown(self):
        self.td.cleanup()

    def write(self, hits, constraints):
        (self.root / "out" / "port_x.json").write_text(json.dumps(
            {"project": "proj-x", "rm": "rm0399", "device": "stm32h747cm7",
             "baseline": "PASS", "hal": "some-hal 1.0", "hits": hits}))
        (self.root / "out" / "constraints" / "rm0399_stm32h747cm7.json"
         ).write_text(json.dumps({"registers": constraints}))

    def test_unchecked_project_hit_joined_exactly(self):
        self.write(
            [{"file": "src/sdmmc.rs", "line": 196, "register": "clkcr",
              "operation": "write", "fields": ["dpsmact"],
              "verdict": "unchecked"}],
            [{"peripheral": "sdmmc1", "register": "CLKCR",
              "constraint_ids": ["c1"],
              "gated_fields": {"CLKDIV": {
                  "preconditions": ["DPSMACT cleared"],
                  "datasheet_text": ["written when DPSM not active"]}}}])
        rows = self.br.load_port_sites()
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["crate"], "proj-x")
        self.assertEqual(r["peripheral"], "sdmmc1")
        self.assertEqual(r["constraint_ids"], "c1")
        self.assertIn("DPSM not active", r["quote"])
        self.assertEqual(r["field_source"], "exact")

    def test_shared_register_name_yields_labelled_union(self):
        self.write(
            [{"file": "src/a.rs", "line": 1, "register": "CR2rs",
              "operation": "write", "fields": [], "verdict": "unchecked"}],
            [{"peripheral": "adc1", "register": "CR2",
              "constraint_ids": ["a"], "datasheet_text": {"w": ["rule A"]}},
             {"peripheral": "usart1", "register": "CR2",
              "constraint_ids": ["u"], "datasheet_text": {"w": ["rule U"]}}])
        r = self.br.load_port_sites()[0]
        self.assertEqual(r["field_source"], "union")
        self.assertIn("[adc1] rule A", r["quote"])
        self.assertIn("[usart1] rule U", r["quote"])

    def test_guarded_hits_stay_out(self):
        self.write([{"file": "f", "line": 1, "register": "clkcr",
                     "operation": "write", "verdict": "corroborated"}], [])
        self.assertEqual(self.br.load_port_sites(), [])

    def test_failed_baseline_record_contributes_nothing(self):
        (self.root / "out" / "port_x.json").write_text(json.dumps(
            {"project": "p", "rm": "r", "device": "d", "baseline": "FAIL",
             "hits": [{"register": "x", "verdict": "unchecked"}]}))
        self.assertEqual(self.br.load_port_sites(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
