#!/usr/bin/env python3
"""test_gate_surface_complete.py -- no ungated way to touch a gated register.

WHAT THIS GUARDS
----------------
Enforcement is a trait bound on `Reg<REG>`'s methods. That argument only holds
if EVERY method reaching the register carries one. The dialect gated-method
tables (`_GATED_METHODS_MODERN` / `_GATED_METHODS_EARLY`) are exact signatures,
so a method svd2rust emits and nobody adds to the table is silently ungated --
the crate still compiles, still injects, still reports hits. Nothing fails.

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

So this test does not check a list of names. For EVERY pristine vendored
`generic.rs` -- across both svd2rust dialects -- it finds every public method
that can write the register and requires each to be either gated (present in
that crate's dialect table) or on an explicitly justified allowlist. A new
svd2rust release that adds a write path fails here instead of quietly widening
the hole.
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

# A method WRITES the register if its closure takes a writer proxy. Modern
# svd2rust spells that `&mut W<REG>`; the early dialect (0.19-0.21) spells it
# `&mut REG::Writer` (the per-register newtype).
_WRITES = re.compile(r"&mut W<REG>|&mut REG::Writer")


def public_methods(generic_src: str) -> dict:
    """method name -> its signature text, for every `pub fn .. (&self, ..)`."""
    out = {}
    for m in re.finditer(
            r"pub (unsafe )?fn (?P<name>\w+)(<[^>]*>)?\(&self[^)]*\)[^{]*\{",
            generic_src):
        out.setdefault(m.group("name"), m.group(0))
    return out


def pristine_crates():
    """(name, src, dialect) for every vendored pristine (un-injected) crate."""
    for fam in sorted(VENDORED.iterdir()):
        g = fam / "src" / "generic.rs"
        if g.is_file():
            src = g.read_text()
            if rust_codegen.GENERIC_SENTINEL in src:
                continue
            try:
                dialect = rust_codegen.detect_dialect(src)
            except RuntimeError:
                continue  # a layout we do not inject into
            yield fam.name, src, dialect


class GateSurface(unittest.TestCase):
    def crates(self):
        crates = list(pristine_crates())
        if not crates:
            self.skipTest("no pristine vendored generic.rs available")
        return crates

    def test_every_write_path_is_gated_or_justified(self):
        """THE REGRESSION TEST. set_bits/clear_bits/toggle_bits failed this.

        Runs for every vendored crate against ITS OWN dialect table, so a write
        path that exists in one svd2rust dialect but is absent from that
        dialect's table is caught."""
        for fam, src, dialect in self.crates():
            table_entries = rust_codegen._DIALECTS[dialect][0]
            table = " ".join(sig for sig, _bound, _req in table_entries)
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
                             f"{fam} ({dialect}): write paths reaching the "
                             f"register with no bound and no justification: "
                             f"{missing}")

    def test_the_atomic_surface_is_in_the_modern_table(self):
        """Named explicitly, so deleting them from the table is loud. Atomics
        are a modern-dialect surface (the early NXP PACs have none)."""
        table = " ".join(sig for sig, _b, _r
                         in rust_codegen._GATED_METHODS_MODERN)
        for name in ("set_bits", "clear_bits", "toggle_bits"):
            self.assertIn(f"fn {name}", table, f"{name} is not gated")

    def test_atomic_surface_is_gated_as_a_write(self):
        for sig, bound, _req in rust_codegen._GATED_METHODS_MODERN:
            if "fn set_bits" in sig or "fn clear_bits" in sig \
                    or "fn toggle_bits" in sig:
                self.assertEqual(bound, "UnconstrainedWrite")

    def test_required_table_entries_match_a_pristine_crate_of_their_dialect(self):
        """The table is exact text. A REQUIRED entry that matches nothing is a
        gate that silently never gets applied; an OPTIONAL entry (atomics, some
        from_*) must match verbatim WHEN a method of that name is present."""
        by_dialect = {}
        for fam, src, dialect in self.crates():
            by_dialect.setdefault(dialect, (fam, src))
        for dialect, (fam, src) in by_dialect.items():
            for sig, _bound, required in rust_codegen._DIALECTS[dialect][0]:
                name = re.search(r"fn (\w+)", sig).group(1)
                if required:
                    self.assertIn(sig, src,
                                  f"{fam} ({dialect}): required table entry "
                                  f"matches nothing:\n{sig}")
                elif f"fn {name}" in src:
                    self.assertIn(sig, src,
                                  f"{fam} ({dialect}): optional entry {name} is "
                                  f"present but its signature drifted:\n{sig}")

    def test_read_signature_present_for_each_dialect(self):
        """The dialect's stock `read` sig must exist in a crate of that dialect
        (the patcher gives it a where clause from this exact text)."""
        by_dialect = {}
        for fam, src, dialect in self.crates():
            by_dialect.setdefault(dialect, (fam, src))
        for dialect, (fam, src) in by_dialect.items():
            read_sig = rust_codegen._DIALECTS[dialect][1]
            self.assertIn(read_sig, src,
                          f"{fam} ({dialect}): stock read sig not found: {read_sig}")

    def test_every_table_entry_has_a_where_clause_at_its_own_indent(self):
        """The patcher splits on the where clause. It used to assume four
        spaces, which silently failed for the atomic methods -- they live in
        `mod atomic`, one level deeper."""
        for table in (rust_codegen._GATED_METHODS_MODERN,
                      rust_codegen._GATED_METHODS_EARLY):
            for sig, _b, _r in table:
                indent = " " * (len(sig) - len(sig.lstrip(" ")))
                self.assertIn(f"\n{indent}where\n", sig, sig)

    def test_allowlist_entries_actually_exist(self):
        """A stale allowlist hides a method that was renamed, not removed.
        Checked against a modern crate (it has the full stock surface)."""
        modern = [(fam, src) for fam, src, d in self.crates() if d == "modern"]
        if not modern:
            self.skipTest("no modern pristine crate vendored")
        fam, src = modern[0]
        ours = {n for n in ALLOWED_UNGATED
                if "witness" in n or n.endswith("_unwitnessed")}
        for name in ALLOWED_UNGATED - ours:
            self.assertIn(f"fn {name}", src, f"{fam}: allowlisted {name} is gone")


if __name__ == "__main__":
    unittest.main(verbosity=2)
