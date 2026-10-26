#!/usr/bin/env python3
"""test_sweep_isolation.py -- the sweep never writes the shared crate.

WHAT THIS GUARDS
----------------
The sweep used to inject into the shared vendored PAC in place, snapshot
first, and promise a byte-for-byte restore. Every failure mode of that promise
happened in practice: a kill mid-restore left stm32g4 with no generic.rs (the
next run failed with an unrelated-looking pydantic error at collection); a
restored tree kept its old mtimes, so cargo silently reused the INJECTED
build against a pristine-on-disk crate; and two sweeps could not run
concurrently, which is why comparing the two gating modes cost two hours
instead of one.

The replacement is not a hardened restore -- it is no restore. `pac_workdir`
copies the pristine crate to a run-private temp dir; injection and every
build point there; the copy is deleted. These tests pin the properties that
make that safe.
"""

import sys
import tempfile
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent / "experiments"
sys.path.insert(0, str(EXP))
import stm_sweep  # noqa: E402


def make_pristine(root: Path) -> Path:
    pac = root / "stm32xx"
    (pac / "src").mkdir(parents=True)
    (pac / "src" / "generic.rs").write_text("pub struct Reg;\n")
    (pac / "src" / "device" ).mkdir()
    (pac / "src" / "device" / "mod.rs").write_text("pub mod x;\n")
    (pac / "Cargo.toml").write_text("[package]\nname='stm32xx'\n")
    # cargo build cache for SOME OTHER path; copying it along would only
    # mislead the copy's builds
    (pac / "target").mkdir()
    (pac / "target" / "junk.rmeta").write_text("stale")
    return pac


class Workdir(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.pristine = make_pristine(Path(self.td.name))

    def tearDown(self):
        self.td.cleanup()

    def test_copy_is_elsewhere_and_complete(self):
        work, parent = stm_sweep.pac_workdir(self.pristine, "t")
        try:
            self.assertNotEqual(work.resolve(), self.pristine.resolve())
            self.assertTrue((work / "src" / "generic.rs").is_file())
            self.assertTrue((work / "src" / "device" / "mod.rs").is_file())
        finally:
            import shutil
            shutil.rmtree(parent)

    def test_build_cache_is_not_copied(self):
        """target/ belongs to the source path's builds, not the copy's."""
        work, parent = stm_sweep.pac_workdir(self.pristine, "t")
        try:
            self.assertFalse((work / "target").exists())
        finally:
            import shutil
            shutil.rmtree(parent)

    def test_writing_the_copy_leaves_the_shared_tree_alone(self):
        """THE POINT. Injection mutates the copy; the pristine crate must be
        byte-identical afterwards -- by construction, not by restore."""
        before = {f: f.read_bytes()
                  for f in self.pristine.rglob("*") if f.is_file()}
        work, parent = stm_sweep.pac_workdir(self.pristine, "t")
        try:
            (work / "src" / "generic.rs").write_text(
                "pub struct Reg; pub trait UnconstrainedWrite {}\n")
            (work / "src" / "device" / "extra.rs").write_text("// injected\n")
        finally:
            import shutil
            shutil.rmtree(parent)
        after = {f: f.read_bytes()
                 for f in self.pristine.rglob("*") if f.is_file()}
        self.assertEqual(before, after)

    def test_two_workdirs_are_independent(self):
        """The property that lets two sweeps run at once."""
        import shutil
        w1, p1 = stm_sweep.pac_workdir(self.pristine, "a")
        w2, p2 = stm_sweep.pac_workdir(self.pristine, "b")
        try:
            (w1 / "src" / "generic.rs").write_text("mode A\n")
            self.assertEqual((w2 / "src" / "generic.rs").read_text(),
                             "pub struct Reg;\n")
        finally:
            shutil.rmtree(p1)
            shutil.rmtree(p2)


class SweepDoesNotRestore(unittest.TestCase):
    def test_the_sweep_no_longer_calls_restore(self):
        """PacSnapshot stays importable for port_hopter.py, but the sweep itself
        must not have a restore step -- reintroducing one reintroduces every
        failure mode above."""
        src = (EXP / "stm_sweep.py").read_text()
        self.assertNotIn("snap.restore_and_verify", src)
        self.assertIn("pac_workdir(", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
