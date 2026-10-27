#!/usr/bin/env python3
"""test_triage_scan_fixes.py -- three triage/attribution correctness fixes.

These guard the parts of the experiment harness that decide, for a
compile-confirmed illegal access, whether the driver already guards it
(`corroborated`) or it is a real candidate bug (`unchecked`), and which
precondition fields belong to which access. All three bugs biased the
committed bug-review ledger.

  FINDING 5 -- the guard scan must not count the flagged access itself as
    its own preceding evidence. `stm_sweep`/`scan_projects` passed
    `line - start + 1` (1-based), so the strictly-before slice `[:rel]`
    included the flagged line; a one-line `cr.modify(|_,w| w.FIELD())` that
    writes the precondition field corroborated itself. Fixed by passing the
    0-based index (`line - start`), matching the seven other callers.

  FINDING 6 -- same-register precondition fields are spelled bare
    (`STOP cleared`), not dotted (`CAN_FMR.FINIT set`). The whole-register
    extractor required a dot and dropped them, leaving hits untriaged / absent
    from the ledger. Now it falls back to the first token, like the field-gate
    branch.

  FINDING 7 -- field extraction must be bounded to the access's own argument
    list, not a fixed 400/300-char window that spills into the next statements
    and misattributes their fields.

Run directly (`python test_triage_scan_fixes.py`) or under pytest.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent / "experiments"
sys.path.insert(0, str(EXP))

import stm_sweep  # noqa: E402
from scan_projects import scan_pac_direct, scan_tock  # noqa: E402


def _write(tmp: Path, name: str, text: str) -> Path:
    p = tmp / name
    p.write_text(text)
    return p


class Finding5OffByOne(unittest.TestCase):
    """The flagged access is not its own guard."""

    def test_self_reference_on_flagged_line_is_unchecked(self):
        src = (
            "pub fn configure(&self) {\n"
            "    self.rcc.cr().modify(|_, w| w.pllon().clear_bit());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            p = _write(Path(td), "rcc.rs", src)
            # The precondition field `pllon` appears ONLY on the flagged line.
            v = stm_sweep.triage_hit(str(p), 2, ["pllon"])
        self.assertEqual(v["verdict"], "unchecked",
                         "a field written on the flagged access must not "
                         "corroborate that same access")

    def test_genuine_preceding_guard_still_corroborates(self):
        src = (
            "pub fn configure(&self) {\n"
            "    if self.rcc.cr().read().pllon().bit_is_clear() {\n"
            "        self.rcc.cfgr().modify(|_, w| unsafe { w.bits(0) });\n"
            "    }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            p = _write(Path(td), "rcc.rs", src)
            # pllon is checked on line 2, strictly before the flagged line 3.
            v = stm_sweep.triage_hit(str(p), 3, ["pllon"])
        self.assertEqual(v["verdict"], "corroborated")


class Finding6SameRegisterFields(unittest.TestCase):
    """Bare (dot-less) same-register precondition fields survive triage."""

    def _gate_fields(self, data: dict) -> dict:
        with tempfile.TemporaryDirectory() as td:
            p = _write(Path(td), "c.json", json.dumps(data))
            return stm_sweep._gate_fields(p)

    def test_bare_and_dotted_both_extracted(self):
        gf = self._gate_fields({"registers": [
            {"peripheral": "i2c1", "register": "CR1",
             "preconditions": {"write": ["STOP cleared", "I2C_SR.PEC set"]}}]})
        self.assertIn("cr1", gf)
        self.assertIn("stop", gf["cr1"]["union"]["write"])   # bare — the regression
        self.assertIn("pec", gf["cr1"]["union"]["write"])    # dotted still works

    def test_register_with_only_bare_precondition_is_present(self):
        # Before the fix this register vanished entirely (no field extracted ->
        # per_op empty -> never added), so its hits had no ledger row at all.
        gf = self._gate_fields({"registers": [
            {"peripheral": "gpioa", "register": "LCKR",
             "preconditions": {"write": ["LCKK cleared"]}}]})
        self.assertIn("lckr", gf)
        self.assertEqual(gf["lckr"]["union"]["write"], ["lckk"])


class Finding7TailOverreach(unittest.TestCase):
    """Field extraction is bounded to the access's own argument list."""

    def test_svd2rust_fields_not_bled_from_next_statements(self):
        src = (
            "impl Flash {\n"
            "    pub fn setup(&self) {\n"
            "        self.flash.acr().modify(|_, w| w.acc64().set_bit());\n"
            "        self.flash.acr().modify(|_, w| w.prften().set_bit());\n"
            "        self.flash.acr().modify(|_, w| w.latency().bits(3));\n"
            "    }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            p = _write(Path(td), "flash.rs", src)
            hits = scan_pac_direct(p, Path(td))
        got = {(h["line"], tuple(h["fields"])) for h in hits}
        # Each write owns exactly its own field — not the two that follow it.
        self.assertEqual(got, {(3, ("acc64",)), (4, ("prften",)), (5, ("latency",))})

    def test_tock_fields_not_bled_from_next_statements(self):
        src = (
            "register_structs! {\n"
            "    pub Registers {\n"
            "        (0x00 => acr: ReadWrite<u32>),\n"
            "        (0x04 => @END),\n"
            "    }\n"
            "}\n"
            "impl Flash {\n"
            "    fn setup(&self) {\n"
            "        self.registers.acr.modify(ACR::ACC64::SET);\n"
            "        self.registers.acr.modify(ACR::PRFTEN::SET);\n"
            "    }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            p = _write(Path(td), "flash.rs", src)
            hits = scan_tock(p, Path(td))
        got = {(h["line"], tuple(h["fields"])) for h in hits}
        self.assertEqual(got, {(9, ("acc64",)), (10, ("prften",))})


if __name__ == "__main__":
    unittest.main()
