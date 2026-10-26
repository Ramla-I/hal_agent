#!/usr/bin/env python3
"""test_gate_surface_complete.py -- no ungated way to touch a gated register.

WHAT THIS GUARDS
----------------
Enforcement is a trait bound on `Reg<REG>`'s methods. That argument only holds
if EVERY method reaching the register carries one. `_GATED_METHODS` is a table
of exact signatures, so a method svd2rust emits and nobody adds to the table is
silently ungated -- and the crate still compiles, still injects, still reports
hits. Nothing fails.

That is not hypothetical. svd2rust emits an atomic write surface behind the
`atomics` feature::

    pub unsafe fn set_bits<F>(&self, f: F)
    where
        F: FnOnce(&mut W<REG>) -> &mut W<REG>,
    { .. REG::Ux::atomic_or(self.register.as_ptr(), bits) }

`set_bits`, `clear_bits` and `toggle_bits` are FULLY TYPED -- they take
`&mut W<REG>` and the caller names the field, `w.lseon().set_bit()` -- and all
three were missing from the table, so they wrote gated registers with no bound
at all. `unsafe` is not a gate: it says the resulting bit pattern may be
invalid, not that the datasheet precondition holds.

So this test does not check a list of names. It reads a PRISTINE `generic.rs`,
finds every public method that can write the register, and requires each to be
either gated or on an explicitly justified allowlist. A new svd2rust release
that adds a write path fails here instead of quietly widening the hole.
"""

import re
import sys
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))
import rust_codegen  # noqa: E402

VENDORED = APP / "vendored" / "pac"

# Methods that reach the register and are deliberately NOT gated. Each needs a
# reason, because "it was already like that" is how the atomic surface stayed
# ungated.
ALLOWED_UNGATED = {
    # Our own escape hatches. `*_witnessed` demand a witness value instead of a
    # marker -- that IS the gate, expressed the other way. `*_unwitnessed` are
    # the documented opt-out and are `unsafe`.
    "read_witnessed", "write_witnessed", "modify_witnessed", "reset_witnessed",
    "from_write_witnessed", "from_modify_witnessed",
    "write_with_zero_witnessed",
    "read_unwitnessed", "write_unwitnessed", "modify_unwitnessed",
    # Hands out a raw pointer. Gating this would break DMA and every
    # legitimate address-taking use, and a pointer cannot carry the bound --
    # this is the door bit banding walks through, tracked in LOST_FINDINGS §4.
    "as_ptr",
}

# A method touches the register if it takes a writer or reader proxy, or is one
# of the two stock methods with no closure at all.
_WRITES = re.compile(r"&mut W<REG>")
_READS = re.compile(r"&R<REG>|-> R<REG>")


def public_methods(generic_src: str) -> dict:
    """method name -> its signature text, for every `pub fn .. (&self, ..)`."""
    out = {}
    for m in re.finditer(
            r"pub (unsafe )?fn (?P<name>\w+)(<[^>]*>)?\(&self[^)]*\)[^{]*\{",
            generic_src):
        out.setdefault(m.group("name"), m.group(0))
    return out


class GateSurface(unittest.TestCase):
    def pristine(self):
        for fam in sorted(VENDORED.iterdir()):
            g = fam / "src" / "generic.rs"
            if g.is_file() and rust_codegen.GENERIC_SENTINEL not in g.read_text():
                return fam.name, g.read_text()
        self.skipTest("no pristine vendored generic.rs available")

    def test_every_write_path_is_gated_or_justified(self):
        """THE REGRESSION TEST. set_bits/clear_bits/toggle_bits failed this."""
        fam, src = self.pristine()
        table = " ".join(sig for sig, _ in rust_codegen._GATED_METHODS)
        missing = []
        for name, sig in public_methods(src).items():
            if name in ALLOWED_UNGATED:
                continue
            body_start = src.index(sig) + len(sig)
            window = sig + src[body_start:body_start + 400]
            if not _WRITES.search(window):
                continue
            if f"fn {name}" not in table and name not in ("read", "reset"):
                missing.append(name)
        self.assertEqual(missing, [],
                         f"{fam}: write paths reaching the register with no "
                         f"bound and no justification: {missing}")

    def test_the_atomic_surface_is_in_the_table(self):
        """Named explicitly, so deleting them from the table is loud."""
        table = " ".join(sig for sig, _ in rust_codegen._GATED_METHODS)
        for name in ("set_bits", "clear_bits", "toggle_bits"):
            self.assertIn(f"fn {name}", table, f"{name} is not gated")

    def test_atomic_surface_is_gated_as_a_write(self):
        for sig, bound in rust_codegen._GATED_METHODS:
            if "fn set_bits" in sig or "fn clear_bits" in sig \
                    or "fn toggle_bits" in sig:
                self.assertEqual(bound, "UnconstrainedWrite")

    def test_every_table_entry_matches_a_pristine_crate(self):
        """The table is exact text. An entry that matches nothing is a gate
        that silently never gets applied."""
        fam, src = self.pristine()
        for sig, _ in rust_codegen._GATED_METHODS:
            self.assertIn(sig, src, f"{fam}: table entry matches nothing:\n{sig}")

    def test_every_table_entry_has_a_where_clause_at_its_own_indent(self):
        """The patcher splits on the where clause. It used to assume four
        spaces, which silently failed for the atomic methods -- they live in
        `mod atomic`, one level deeper."""
        for sig, _ in rust_codegen._GATED_METHODS:
            indent = " " * (len(sig) - len(sig.lstrip(" ")))
            self.assertIn(f"\n{indent}where\n", sig, sig)

    def test_allowlist_entries_actually_exist(self):
        """A stale allowlist hides a method that was renamed, not removed."""
        fam, src = self.pristine()
        ours = {n for n in ALLOWED_UNGATED
                if "witness" in n or n.endswith("_unwitnessed")}
        for name in ALLOWED_UNGATED - ours:
            self.assertIn(f"fn {name}", src, f"{fam}: allowlisted {name} is gone")


if __name__ == "__main__":
    unittest.main(verbosity=2)
