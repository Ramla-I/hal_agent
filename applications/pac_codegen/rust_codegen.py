#!/usr/bin/env python3
"""Constraint-aware Rust code generator for svd2rust PAC crates (trait gating).

Reads a RegisterInfo JSON (v1 schema from the repo-root ``defs.py``) and turns
its ``access_constraints`` into compile-time enforcement inside a PAC crate.

ENCODING (see docs/register_constraints_plan.md §3 + Appendix A)
----------------------------------------------------------------
Gating is by TRAIT BOUND, not wrapper types or method shadowing: the stock
``Reg::write``/``modify``/``read``/``reset``/``write_with_zero``/``from_*``
methods gain a ``where REG: UnconstrainedWrite/Modify/Read`` clause in
``generic.rs``. Every unconstrained register receives one-line marker impls;
a constrained register receives NO marker for the gated operation, so the
witness-free method *does not exist* for it — every call site gets E0277 with
a ``#[diagnostic::on_unimplemented]`` message naming the fix. The witness
types ride on separate ``WriteGate``/``ModifyGate``/``ReadGate`` traits that
only constrained registers implement, so the stock ``Writable``/``Readable``
trait definitions (and all ~everything svd2rust emitted) stay untouched.

Per constrained register the injected ``constraints`` module provides:
  - zero-sized witness types (``Cr1WriteWitness`` — private field, non-Copy)
  - a register-scoped error enum
  - ``check_write_ready()`` — ONE fresh volatile read checks every
    precondition conjunctively and mints the witness (a *state witness*)
  - ``write_when_ready(f)`` — check + witnessed write welded into one call
    (the recommended entry point: the witness never escapes user code)

The only escapes are ``unsafe`` (``write_unwitnessed`` etc.); there is no
wrapper, no ``Deref`` hole, and no visibility widening (injected code lives
inside the crate's own modules).

SCOPE (roadmap steps B + H): observed-state preconditions on write/modify/
read, same-register and cross-register. A ``write`` constraint gates BOTH
the write surface (write/reset/write_with_zero/from_write) and the modify
surface (a modify performs a write), each with its own witness type. A
``read`` constraint gates the read surface and its preconditions must all be
cross-register (a same-register read gate is self-defeating: the check would
perform the constrained read). Cross-register checks take the source
register(s) as ``&Reg<SRCrs>`` parameters — same-peripheral sources resolve
to ``super::<reg>::<REG>rs``, cross-peripheral ones (e.g. PWR_CR gating RTC)
to ``super::super::<periph>::<reg>::<REG>rs``. Postconditions / action
witnesses land in step I.

USAGE
-----
Standalone module (golden test input):
    python rust_codegen.py fixture.json --peripheral i2c1 --output out.rs

Inject into a provisioned PAC (see get_pac.py):
    python rust_codegen.py fixture.json --peripheral i2c1 \
        --inject-pac applications/pac_codegen/vendored/pac/stm32f4 \
        --device stm32f405

Injection is ONE-SHOT from a pristine PAC (it refuses to run twice); the
compile tests snapshot and restore the tree around each case.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Repo root (three levels up) for the shared v1 schema.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from defs import FieldState, RegisterInfo  # noqa: E402

GENERIC_SENTINEL = "// ===== LIDAR constraint gating (generated; do not edit) ====="
MARKER_SENTINEL = "// LIDAR-MARKERS (generated; do not edit)"
MODULE_SENTINEL = "// LIDAR-CONSTRAINTS (generated; do not edit)"

# Operations and the generic.rs surface each one gates.
WRITE_SURFACE = "write/reset/write_with_zero/from_write"
MODIFY_SURFACE = "modify/from_modify"


# --------------------------------------------------------------------------- #
# Normalization: v1 RegisterInfo -> per-operation conjunctive precondition sets
# --------------------------------------------------------------------------- #

def _norm_reg_name(name: str) -> str:
    """Uppercase, underscore-free register name for same-register matching
    (datasheets write ``I2C_CR1`` where the SVD register is ``CR1``)."""
    return name.upper().replace("_", "")


def _is_same_register(field_state: FieldState, target: str) -> bool:
    ref = _norm_reg_name(field_state.register_name)
    tgt = _norm_reg_name(target)
    return ref == tgt or ref.endswith(tgt)


class SourceRegister:
    """A cross-register witness source, resolved to a Rust path.

    Datasheet names are ``<PERIPHERAL>_<REGISTER>`` (``SPI_SR``, ``PWR_CR``).
    If the prefix names the target's own peripheral (instance digits
    stripped: spi1 -> spi), the source lives in a sibling module
    (``super::sr::SRrs``); otherwise it is cross-peripheral and resolves via
    the device module (``super::super::pwr::cr::CRrs``). Instance binding is
    the documented limit either way (shared module types).
    """

    def __init__(self, register_name: str, peripheral: str):
        if "_" not in register_name:
            raise ValueError(
                f"cross-register source {register_name!r} lacks a "
                "PERIPHERAL_REGISTER prefix; cannot resolve its module"
            )
        prefix, reg = register_name.split("_", 1)
        self.reg = reg.lower()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.reg):
            raise ValueError(f"unresolvable source register {register_name!r}")
        base = peripheral.lower().rstrip("0123456789")
        self.same_peripheral = prefix.lower() in (base, peripheral.lower())
        self.periph_module = None if self.same_peripheral else prefix.lower()
        self.display = register_name

    def key(self):
        return (self.periph_module, self.reg)

    def var(self) -> str:
        return self.reg if self.same_peripheral else f"{self.periph_module}_{self.reg}"

    def spec_path(self) -> str:
        spec = f"{self.reg.upper()}rs"
        if self.same_peripheral:
            return f"super::{self.reg}::{spec}"
        return f"super::super::{self.periph_module}::{self.reg}::{spec}"


def _parse_equals_value(state: str) -> int:
    """Parse the value of an ``equals:<v>`` state to an int, strictly.

    Raw text must never be spliced into Rust (it is an injection surface and
    ``a|b`` silently changes meaning under Rust operator precedence).
    """
    raw = state.split(":", 1)[1].strip()
    if not re.fullmatch(r"(0[xX][0-9a-fA-F]+|0[bB][01]+|\d+)", raw):
        raise ValueError(
            f"unsupported equals value {raw!r}: must be a single hex/bin/dec "
            "integer literal (OR-values and sequences are a grammar-v2 concern)"
        )
    return int(raw, 0)


class Precondition:
    """A field-state check, validated and value-parsed. ``source`` is None
    for same-register conditions, else the resolved cross-register source."""

    def __init__(self, fs: FieldState, source: "SourceRegister | None" = None):
        self.source = source
        self.field = fs.field_name
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", self.field or ""):
            raise ValueError(
                f"field name {self.field!r} is not an SVD-style identifier "
                "(ranges/wildcards/pseudo-fields are rejected)"
            )
        state = fs.required_state
        if state == "cleared":
            self.kind, self.value = "cleared", None
        elif state == "set":
            self.kind, self.value = "set", None
        elif state.startswith("equals:"):
            self.kind, self.value = "equals", _parse_equals_value(state)
        else:
            raise ValueError(f"unsupported required_state {state!r}")

    def key(self):
        src = self.source.key() if self.source else None
        return (src, self.field.lower(), self.kind, self.value)

    def reader_var(self) -> str:
        return f"r_{self.source.var()}" if self.source else "r"

    def describe(self) -> str:
        where = f"{self.source.display}." if self.source else ""
        if self.kind == "equals":
            return f"{where}{self.field} == {self.value:#x}"
        return f"{where}{self.field} {self.kind}"

    def check_expr(self, reader: str = "r") -> str:
        accessor = self.field.lower()
        if self.kind == "cleared":
            return f"{reader}.{accessor}().bit_is_clear()"
        if self.kind == "set":
            return f"{reader}.{accessor}().bit_is_set()"
        return f"{reader}.{accessor}().bits() == {self.value:#x}"

    def error_variant(self) -> str:
        name = self.field.capitalize()
        if self.source:
            name = self.source.reg.capitalize() + name
        if self.kind == "cleared":
            return f"{name}NotCleared"
        if self.kind == "set":
            return f"{name}NotSet"
        return f"{name}NotEq{self.value}"


class FieldGate:
    """A field-scoped write gate (field-level gating, opt-in): setting one
    field of the register requires a witness that its preconditions held.

    Unlike a whole-register gate, the register's own `write`/`modify` stay
    unconstrained — only the field's writer accessor `w.<field>()` is gated,
    so writes to sibling fields are unaffected. Both write and modify go
    through that accessor, so one gate covers both surfaces."""

    def __init__(self, field: str):
        self.field = field
        self.field_lower = field.lower()
        self.preconditions: list["Precondition"] = []
        self.docs: list[str] = []

    def sources(self) -> list["SourceRegister"]:
        out, seen = [], set()
        for p in self.preconditions:
            if p.source and p.source.key() not in seen:
                out.append(p.source)
                seen.add(p.source.key())
        return out

    def witness_name(self, reg: str) -> str:
        return f"{reg.capitalize()}{self.field.capitalize()}FieldWitness"

    def check_name(self) -> str:
        return f"check_{self.field_lower}_field_ready"


class RegisterPlan:
    """Everything the emitter needs for one constrained register."""

    def __init__(self, register_info: RegisterInfo, peripheral: str,
                 field_level_gating: bool = False):
        # Field-level gating is OPT-IN (default off). When off, the emitter's
        # behavior is exactly as before: field-scoped constraints are skipped
        # with a warning. When on, they are enforced by gating the per-field
        # writer accessor (see FieldGate / patch_field_accessors).
        self.peripheral = peripheral.lower()
        # Corpus abbreviations are often peripheral-prefixed (SPI_TXCRCR);
        # the PAC module is named by the bare register (txcrcr). Strip the
        # prefix when it names this peripheral.
        name = register_info.datasheet_register_abbreviation
        if "_" in name:
            prefix, rest = name.split("_", 1)
            base = self.peripheral.rstrip("0123456789")
            if prefix.lower() in (base, self.peripheral):
                name = rest
        self.reg_name = name  # e.g. CR1, TXCRCR
        self.reg_lower = self.reg_name.lower()
        # op -> ordered unique preconditions; op in {"write", "modify"}
        self.preconditions: dict[str, list[Precondition]] = {}
        # op -> constraint doc lines (datasheet text + consequence)
        self.docs: dict[str, list[str]] = {}
        # field-lowercase -> FieldGate (populated only when field_level_gating)
        self.field_gates: dict[str, FieldGate] = {}

        for c in register_info.access_constraints:
            if getattr(c, "target_fields", None):
                if not field_level_gating:
                    # Default: field-scoped gating disabled. Gating the whole
                    # register would demand this precondition for writes to
                    # UNRELATED fields — sound but over-restrictive, and for a
                    # software-established precondition it can force incorrect
                    # setup of this or another register. So skip rather than
                    # over-gate. Enable with field_level_gating=True.
                    print(
                        f"WARNING: {self.reg_name}: skipping field-scoped "
                        f"constraint on {list(c.target_fields)} "
                        f"({c.target_operation}) — field-level gating is "
                        f"disabled; this constraint is NOT enforced.",
                        file=sys.stderr,
                    )
                    continue
                self._add_field_gate(c, peripheral)
                continue
            if c.postconditions:
                raise NotImplementedError(
                    f"{self.reg_name}: postconditions/action witnesses are "
                    "roadmap step I; not emitted yet"
                )
            pres = []
            for fs in c.preconditions:
                if _is_same_register(fs, c.target_register):
                    pres.append(Precondition(fs))
                else:
                    pres.append(Precondition(
                        fs, SourceRegister(fs.register_name, peripheral)))
            if c.target_operation == "write":
                ops = ["write", "modify"]  # a modify performs a write
            elif c.target_operation == "modify":
                ops = ["modify"]
            elif c.target_operation == "read":
                same = [p for p in pres if p.source is None]
                if same:
                    raise ValueError(
                        f"{self.reg_name}: same-register read gate on "
                        f"{[p.field for p in same]} is self-defeating (the "
                        "check performs the constrained read); rejected"
                    )
                ops = ["read"]
            else:
                raise ValueError(
                    f"{self.reg_name}: unsupported target_operation "
                    f"{c.target_operation!r} (v1 vocabulary is write/read/modify)"
                )
            if not pres:
                raise ValueError(
                    f"{self.reg_name}: constraint has no preconditions — "
                    "nothing to enforce (grammar-v2 `other` material)"
                )
            for op in ops:
                bucket = self.preconditions.setdefault(op, [])
                seen = {p.key() for p in bucket}
                for p in pres:
                    if p.key() not in seen:
                        bucket.append(p)
                        seen.add(p.key())
                doc = self.docs.setdefault(op, [])
                line = c.datasheet_text.strip()
                if line and line not in doc:
                    doc.append(line)

        if not self.preconditions and not self.field_gates:
            raise ValueError(f"{self.reg_name}: no enforceable constraints")

    def _add_field_gate(self, c, peripheral: str) -> None:
        """Record a field-scoped constraint as one FieldGate per named field
        (field-level gating; only reached when field_level_gating is on)."""
        if c.postconditions:
            raise NotImplementedError(
                f"{self.reg_name}: field-scoped postconditions are not "
                "supported (roadmap step I)"
            )
        if c.target_operation not in ("write", "modify"):
            # Field-level gating gates the writer accessor, which serves both
            # write and modify; a field-scoped READ gate has no writer to gate.
            print(
                f"WARNING: {self.reg_name}: field-scoped {c.target_operation} "
                f"gate on {list(c.target_fields)} — field-level gating "
                f"supports only write/modify; NOT enforced.",
                file=sys.stderr,
            )
            return
        pres = []
        for fs in c.preconditions:
            if _is_same_register(fs, c.target_register):
                pres.append(Precondition(fs))
            else:
                pres.append(Precondition(
                    fs, SourceRegister(fs.register_name, peripheral)))
        if not pres:
            raise ValueError(
                f"{self.reg_name}: field-scoped constraint has no "
                "preconditions — nothing to enforce"
            )
        doc = c.datasheet_text.strip()
        for field in c.target_fields:
            fg = self.field_gates.setdefault(field.lower(), FieldGate(field))
            seen = {p.key() for p in fg.preconditions}
            for p in pres:
                if p.key() not in seen:
                    fg.preconditions.append(p)
                    seen.add(p.key())
            if doc and doc not in fg.docs:
                fg.docs.append(doc)

    def sources(self, op: str) -> list["SourceRegister"]:
        """Ordered unique cross-register sources for one operation."""
        out, seen = [], set()
        for p in self.preconditions[op]:
            if p.source and p.source.key() not in seen:
                out.append(p.source)
                seen.add(p.source.key())
        return out

    def has_read_gate(self) -> bool:
        return "read" in self.preconditions

    def prune_for_access(self, readable: bool, writable: bool) -> list[str]:
        """Drop gates the register's access mode cannot express (a write-only
        register has no `modify`/`read` to gate; svd2rust never emits them and
        the gate impls would not compile). Same-register preconditions also
        need `self.read()`, so a non-readable register can only carry
        cross-register checks. Returns the removed operations."""
        removed = []
        for op in list(self.preconditions):
            bad = (
                (op == "write" and not writable)
                or (op == "modify" and not (readable and writable))
                or (op == "read" and not readable)
                or (not readable and any(
                    p.source is None for p in self.preconditions[op]))
            )
            if bad:
                del self.preconditions[op]
                self.docs.pop(op, None)
                removed.append(op)
        # Field gates set a field via the register's writer, and their same-
        # register preconditions read it: they need a writable (and, for such
        # preconditions, readable) register or the patched accessor / check
        # would not compile.
        for fname in list(self.field_gates):
            fg = self.field_gates[fname]
            if not writable or (not readable and any(
                    p.source is None for p in fg.preconditions)):
                del self.field_gates[fname]
                removed.append(f"field:{fg.field}")
        return removed

    # (peripheral module, register-spec type, gated op), for the marker walk
    def gated_ops(self) -> set[tuple[str, str, str]]:
        spec = f"{self.reg_name.upper()}rs"
        return {(self.peripheral, spec, op) for op in self.preconditions}

    def witness_name(self, op: str) -> str:
        return f"{self.reg_name.capitalize()}{op.capitalize()}Witness"

    def error_name(self) -> str:
        return f"{self.reg_name.capitalize()}ConstraintError"


# --------------------------------------------------------------------------- #
# Emitter: the per-peripheral `constraints` module
# --------------------------------------------------------------------------- #

def generate_constraint_module(plan: RegisterPlan) -> str:
    reg = plan.reg_name
    spec = f"super::{plan.reg_lower}::{reg.upper()}rs"
    ux = f"<{spec} as crate::RegisterSpec>::Ux"
    err = plan.error_name()

    lines: list[str] = []
    a = lines.append

    a(f"//! Compile-time access constraints for {plan.peripheral.upper()} {reg}.")
    a("//!")
    a("//! Generated from datasheet constraints. Do not edit manually.")
    a("//!")
    a("//! A witness attests that the preconditions were OBSERVED TRUE in one")
    a("//! fresh volatile read; prefer `*_when_ready` (check + use in one call).")
    a("")

    # --- Witness types (state witnesses: private field, non-Copy, ZST) ---
    a("// === Witnesses ===")
    for op in sorted(plan.preconditions):
        w = plan.witness_name(op)
        a(f"/// State witness authorizing one {op} of {reg}.")
        a(f"pub struct {w} {{ _priv: () }}")
    for fname in sorted(plan.field_gates):
        fg = plan.field_gates[fname]
        a(f"/// State witness authorizing writes to the {fg.field} field of {reg}.")
        a(f"pub struct {fg.witness_name(reg)} {{ _priv: () }}")
    a("")

    # --- Error enum (register-scoped name: peripheral module may gain more) ---
    all_pres: list[Precondition] = []
    seen = set()
    for op in sorted(plan.preconditions):
        for p in plan.preconditions[op]:
            if p.key() not in seen:
                all_pres.append(p)
                seen.add(p.key())
    for fname in sorted(plan.field_gates):
        for p in plan.field_gates[fname].preconditions:
            if p.key() not in seen:
                all_pres.append(p)
                seen.add(p.key())
    a("// === Error Type ===")
    a("/// A precondition that was not satisfied at check time.")
    a("#[derive(Debug, Clone, Copy, PartialEq, Eq)]")
    a(f"pub enum {err} {{")
    for p in all_pres:
        a(f"    /// {p.describe()} was required")
        a(f"    {p.error_variant()},")
    a("}")
    a("")

    # --- Gate impls: the witness types ride on Write/Modify/ReadGate ---
    a("// === Gates ===")
    for op in sorted(plan.preconditions):
        gate = {"write": "WriteGate", "modify": "ModifyGate", "read": "ReadGate"}[op]
        a(f"impl crate::{gate} for {spec} {{")
        a(f"    type Witness = {plan.witness_name(op)};")
        a("}")
    a("")

    def _src_params(srcs) -> str:
        return "".join(
            f", {s.var()}: &crate::Reg<{s.spec_path()}>" for s in srcs)

    def src_params(op: str) -> str:
        return _src_params(plan.sources(op))

    def src_args(op: str) -> str:
        return "".join(f", {s.var()}" for s in plan.sources(op))

    # --- Check methods + welded check+use entry points ---
    a("// === Checks ===")
    a(f"impl crate::Reg<{spec}> {{")
    for op in sorted(plan.preconditions):
        w = plan.witness_name(op)
        pres = plan.preconditions[op]
        needs_self_read = any(p.source is None for p in pres)
        srcs = plan.sources(op)
        what = "and every source register " if srcs else ""
        a(f"    /// Read {'the source register(s)' if not needs_self_read else reg} "
          f"{what}once and check every {op} precondition.")
        a("    ///")
        a("    /// # Constraint")
        for doc in plan.docs.get(op, []):
            a(f"    /// {doc}")
        a("    #[inline(always)]")
        a(f"    pub fn check_{op}_ready(&self{src_params(op)}) -> Result<{w}, {err}> {{")
        if needs_self_read:
            a("        let r = self.read();")
        for s in srcs:
            a(f"        let r_{s.var()} = {s.var()}.read();")
        for p in pres:
            a(f"        if !({p.check_expr(p.reader_var())}) {{")
            a(f"            return Err({err}::{p.error_variant()});")
            a("        }")
        a(f"        Ok({w} {{ _priv: () }})")
        a("    }")
        a("")

    # *_when_ready: check + use welded into one call
    if "write" in plan.preconditions:
        a("    /// Check and write in one call — the witness never escapes,")
        a("    /// so the check-to-write window is fixed by this body.")
        a("    #[inline(always)]")
        a(f"    pub fn write_when_ready<F>(&self, f: F{src_params('write')}) -> Result<{ux}, {err}>")
        a("    where")
        a(f"        F: FnOnce(&mut crate::W<{spec}>) -> &mut crate::W<{spec}>,")
        a("    {")
        a(f"        let witness = self.check_write_ready({src_args('write').lstrip(', ')})?;"
          if plan.sources("write") else
          "        let witness = self.check_write_ready()?;")
        a("        Ok(self.write_witnessed(f, witness))")
        a("    }")
        a("")
    if "modify" in plan.preconditions:
        a("    /// Check and modify in one call — the witness never escapes.")
        a("    #[inline(always)]")
        a(f"    pub fn modify_when_ready<F>(&self, f: F{src_params('modify')}) -> Result<{ux}, {err}>")
        a("    where")
        a(f"        for<'w> F: FnOnce(&crate::R<{spec}>, &'w mut crate::W<{spec}>) -> &'w mut crate::W<{spec}>,")
        a("    {")
        a(f"        let witness = self.check_modify_ready({src_args('modify').lstrip(', ')})?;"
          if plan.sources("modify") else
          "        let witness = self.check_modify_ready()?;")
        a("        Ok(self.modify_witnessed(f, witness))")
        a("    }")
        a("")
    if "read" in plan.preconditions:
        a("    /// Check and read in one call — the witness never escapes.")
        a("    #[inline(always)]")
        a(f"    pub fn read_when_ready(&self{src_params('read')}) -> Result<crate::R<{spec}>, {err}> {{")
        a(f"        let witness = self.check_read_ready({src_args('read').lstrip(', ')})?;")
        a("        Ok(self.read_witnessed(witness))")
        a("    }")
        a("")

    # --- Field-gate checks: mint the per-field witness the patched writer
    # accessor `w.<field>(&witness)` requires. Unlike the whole-register
    # gate there is no welded `_when_ready` — the field is set inside a
    # user-controlled write/modify closure, so the witness is minted here
    # and borrowed into that closure.
    for fname in sorted(plan.field_gates):
        fg = plan.field_gates[fname]
        w = fg.witness_name(reg)
        pres = fg.preconditions
        needs_self_read = any(p.source is None for p in pres)
        srcs = fg.sources()
        a(f"    /// Check every precondition for writing the {fg.field} field "
          f"of {reg}.")
        a("    ///")
        a("    /// # Constraint")
        for doc in fg.docs:
            a(f"    /// {doc}")
        a("    #[inline(always)]")
        a(f"    pub fn {fg.check_name()}(&self{_src_params(srcs)}) "
          f"-> Result<{w}, {err}> {{")
        if needs_self_read:
            a("        let r = self.read();")
        for s in srcs:
            a(f"        let r_{s.var()} = {s.var()}.read();")
        for p in pres:
            a(f"        if !({p.check_expr(p.reader_var())}) {{")
            a(f"            return Err({err}::{p.error_variant()});")
            a("        }")
        a(f"        Ok({w} {{ _priv: () }})")
        a("    }")
        a("")
    a("}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# generic.rs patch: gate stock methods, add witnessed/unwitnessed surface
# --------------------------------------------------------------------------- #

# (method signature to find — must contain a where clause, where-bound to add).
# `read` and `reset` have no stock where clause and are handled separately.
_GATED_METHODS = [
    ("    pub fn write<F>(&self, f: F) -> REG::Ux\n    where\n        F: FnOnce(&mut W<REG>) -> &mut W<REG>,", "UnconstrainedWrite"),
    ("    pub fn from_write<F, T>(&self, f: F) -> T\n    where\n        F: FnOnce(&mut W<REG>) -> T,", "UnconstrainedWrite"),
    ("    pub unsafe fn write_with_zero<F>(&self, f: F) -> REG::Ux\n    where\n        F: FnOnce(&mut W<REG>) -> &mut W<REG>,", "UnconstrainedWrite"),
    ("    pub unsafe fn from_write_with_zero<F, T>(&self, f: F) -> T\n    where\n        F: FnOnce(&mut W<REG>) -> T,", "UnconstrainedWrite"),
    ("    pub fn modify<F>(&self, f: F) -> REG::Ux\n    where\n        for<'w> F: FnOnce(&R<REG>, &'w mut W<REG>) -> &'w mut W<REG>,", "UnconstrainedModify"),
    ("    pub fn from_modify<F, T>(&self, f: F) -> T\n    where\n        for<'w> F: FnOnce(&R<REG>, &'w mut W<REG>) -> T,", "UnconstrainedModify"),
]

_GENERIC_ADDITIONS = GENERIC_SENTINEL + """

/// Marker: this register's WRITE surface needs no witness. Emitted for every
/// unconstrained register; ABSENT on write-constrained ones, so the stock
/// methods do not exist for them and E0277 points at the offending call.
#[diagnostic::on_unimplemented(
    message = "`{Self}` is write-constrained by its datasheet",
    label = "this register requires a witness: call `write_witnessed(f, witness)` or `write_when_ready(f)`; obtain the witness via `check_write_ready()`; bypass only with `unsafe write_unwitnessed`",
)]
pub trait UnconstrainedWrite: Writable {}

/// Marker: this register's MODIFY surface needs no witness.
#[diagnostic::on_unimplemented(
    message = "`{Self}` is modify-constrained by its datasheet",
    label = "call `modify_witnessed(f, witness)` or `modify_when_ready(f)`; obtain the witness via `check_modify_ready()`; bypass only with `unsafe modify_unwitnessed`",
)]
pub trait UnconstrainedModify: Readable + Writable {}

/// Marker: this register's READ surface needs no witness.
#[diagnostic::on_unimplemented(
    message = "`{Self}` is read-constrained by its datasheet",
    label = "call `read_witnessed(witness)`; bypass only with `unsafe read_unwitnessed`",
)]
pub trait UnconstrainedRead: Readable {}

/// Implemented ONLY by write-constrained registers; carries the witness type
/// their gated write surface consumes.
pub trait WriteGate: Writable {
    /// The witness consumed by `write_witnessed`/`reset_witnessed`/....
    type Witness;
}

/// Implemented ONLY by modify-constrained registers.
pub trait ModifyGate: Readable + Writable {
    /// The witness consumed by `modify_witnessed`/`from_modify_witnessed`.
    type Witness;
}

/// Implemented ONLY by read-constrained registers.
pub trait ReadGate: Readable {
    /// The witness consumed by `read_witnessed`.
    type Witness;
}

impl<REG: Resettable + Writable> Reg<REG> {
    /// Witnessed `write`: consumes the witness minted by the register's
    /// `check_write_ready()`. The witness attests a past observation; prefer
    /// `write_when_ready` which welds check and write into one call.
    #[inline(always)]
    pub fn write_witnessed<F>(&self, f: F, _witness: <REG as WriteGate>::Witness) -> REG::Ux
    where
        REG: WriteGate,
        F: FnOnce(&mut W<REG>) -> &mut W<REG>,
    {
        let value = f(&mut W {
            bits: REG::RESET_VALUE & !REG::ONE_TO_MODIFY_FIELDS_BITMAP
                | REG::ZERO_TO_MODIFY_FIELDS_BITMAP,
            _reg: marker::PhantomData,
        })
        .bits;
        self.register.set(value);
        value
    }

    /// Witnessed `reset`.
    #[inline(always)]
    pub fn reset_witnessed(&self, _witness: <REG as WriteGate>::Witness)
    where
        REG: WriteGate,
    {
        self.register.set(REG::RESET_VALUE)
    }

    /// Witnessed `from_write`.
    #[inline(always)]
    pub fn from_write_witnessed<F, T>(&self, f: F, _witness: <REG as WriteGate>::Witness) -> T
    where
        REG: WriteGate,
        F: FnOnce(&mut W<REG>) -> T,
    {
        let mut writer = W {
            bits: REG::RESET_VALUE & !REG::ONE_TO_MODIFY_FIELDS_BITMAP
                | REG::ZERO_TO_MODIFY_FIELDS_BITMAP,
            _reg: marker::PhantomData,
        };
        let result = f(&mut writer);
        self.register.set(writer.bits);
        result
    }

    /// The sanctioned escape hatch: write WITHOUT the datasheet-required
    /// witness. Greppable; the caller accepts responsibility for violating
    /// the documented hardware procedure (errata, bring-up, etc.).
    ///
    /// # Safety
    ///
    /// The datasheet forbids this write unless its preconditions hold; the
    /// caller must establish them by other means.
    #[inline(always)]
    pub unsafe fn write_unwitnessed<F>(&self, f: F) -> REG::Ux
    where
        F: FnOnce(&mut W<REG>) -> &mut W<REG>,
    {
        let value = f(&mut W {
            bits: REG::RESET_VALUE & !REG::ONE_TO_MODIFY_FIELDS_BITMAP
                | REG::ZERO_TO_MODIFY_FIELDS_BITMAP,
            _reg: marker::PhantomData,
        })
        .bits;
        self.register.set(value);
        value
    }
}

impl<REG: Writable> Reg<REG> {
    /// Witnessed `write_with_zero`. Still `unsafe`: the zero-base bit
    /// pattern may be invalid for the register (svd2rust's own contract).
    ///
    /// # Safety
    ///
    /// Unsafe to use with registers which don't allow to write 0.
    #[inline(always)]
    pub unsafe fn write_with_zero_witnessed<F>(&self, f: F, _witness: <REG as WriteGate>::Witness) -> REG::Ux
    where
        REG: WriteGate,
        F: FnOnce(&mut W<REG>) -> &mut W<REG>,
    {
        let value = f(&mut W {
            bits: REG::Ux::ZERO,
            _reg: marker::PhantomData,
        })
        .bits;
        self.register.set(value);
        value
    }
}

impl<REG: Readable + Writable> Reg<REG> {
    /// Witnessed `modify`: consumes the witness minted by the register's
    /// `check_modify_ready()`. Prefer `modify_when_ready`.
    #[inline(always)]
    pub fn modify_witnessed<F>(&self, f: F, _witness: <REG as ModifyGate>::Witness) -> REG::Ux
    where
        REG: ModifyGate,
        for<'w> F: FnOnce(&R<REG>, &'w mut W<REG>) -> &'w mut W<REG>,
    {
        let bits = self.register.get();
        let value = f(
            &R {
                bits,
                _reg: marker::PhantomData,
            },
            &mut W {
                bits: bits & !REG::ONE_TO_MODIFY_FIELDS_BITMAP | REG::ZERO_TO_MODIFY_FIELDS_BITMAP,
                _reg: marker::PhantomData,
            },
        )
        .bits;
        self.register.set(value);
        value
    }

    /// Witnessed `from_modify`.
    #[inline(always)]
    pub fn from_modify_witnessed<F, T>(&self, f: F, _witness: <REG as ModifyGate>::Witness) -> T
    where
        REG: ModifyGate,
        for<'w> F: FnOnce(&R<REG>, &'w mut W<REG>) -> T,
    {
        let bits = self.register.get();
        let mut writer = W {
            bits: bits & !REG::ONE_TO_MODIFY_FIELDS_BITMAP | REG::ZERO_TO_MODIFY_FIELDS_BITMAP,
            _reg: marker::PhantomData,
        };
        let result = f(
            &R {
                bits,
                _reg: marker::PhantomData,
            },
            &mut writer,
        );
        self.register.set(writer.bits);
        result
    }

    /// Escape hatch for the modify surface.
    ///
    /// # Safety
    ///
    /// The datasheet forbids this read-modify-write unless its preconditions
    /// hold; the caller must establish them by other means.
    #[inline(always)]
    pub unsafe fn modify_unwitnessed<F>(&self, f: F) -> REG::Ux
    where
        for<'w> F: FnOnce(&R<REG>, &'w mut W<REG>) -> &'w mut W<REG>,
    {
        let bits = self.register.get();
        let value = f(
            &R {
                bits,
                _reg: marker::PhantomData,
            },
            &mut W {
                bits: bits & !REG::ONE_TO_MODIFY_FIELDS_BITMAP | REG::ZERO_TO_MODIFY_FIELDS_BITMAP,
                _reg: marker::PhantomData,
            },
        )
        .bits;
        self.register.set(value);
        value
    }
}

impl<REG: Readable> Reg<REG> {
    /// Witnessed `read` (only exists for read-constrained registers, whose
    /// witnesses come from cross-register checks).
    #[inline(always)]
    pub fn read_witnessed(&self, _witness: <REG as ReadGate>::Witness) -> R<REG>
    where
        REG: ReadGate,
    {
        R {
            bits: self.register.get(),
            _reg: marker::PhantomData,
        }
    }

    /// Escape hatch for the read surface.
    ///
    /// # Safety
    ///
    /// The datasheet constrains reads of this register; the caller must
    /// establish the preconditions by other means.
    #[inline(always)]
    pub unsafe fn read_unwitnessed(&self) -> R<REG> {
        R {
            bits: self.register.get(),
            _reg: marker::PhantomData,
        }
    }
}
"""


def patch_generic_rs(generic_path: Path) -> None:
    """Gate the stock methods and append the witnessed/unwitnessed surface."""
    content = generic_path.read_text()
    if GENERIC_SENTINEL in content:
        raise RuntimeError(
            f"{generic_path} already carries the LIDAR patch; injection is "
            "one-shot from a pristine PAC (restore it, e.g. get_pac.py --force)"
        )

    # `read` has no where clause in stock svd2rust; give it one.
    read_sig = "    pub fn read(&self) -> R<REG> {"
    if read_sig not in content:
        raise RuntimeError("generic.rs drift: stock `read` signature not found")
    content = content.replace(
        read_sig,
        "    pub fn read(&self) -> R<REG>\n"
        "    where\n"
        "        REG: UnconstrainedRead,\n"
        "    {",
        1,
    )

    # `reset` likewise.
    reset_sig = "    pub fn reset(&self) {"
    if reset_sig not in content:
        raise RuntimeError("generic.rs drift: stock `reset` signature not found")
    content = content.replace(
        reset_sig,
        "    pub fn reset(&self)\n"
        "    where\n"
        "        REG: UnconstrainedWrite,\n"
        "    {",
        1,
    )

    # The rest already have a where clause: require the marker first.
    for sig, bound in _GATED_METHODS:
        head, tail = sig.split("\n    where\n", 1)
        if sig not in content:
            raise RuntimeError(f"generic.rs drift: signature not found:\n{sig}")
        content = content.replace(
            sig,
            f"{head}\n    where\n        REG: {bound},\n{tail}",
            1,
        )

    # The generic Debug impl performs a read; it now needs the read marker.
    dbg = ("impl<REG: Readable> core::fmt::Debug for crate::generic::Reg<REG>\n"
           "where\n"
           "    R<REG>: core::fmt::Debug,")
    if dbg not in content:
        raise RuntimeError("generic.rs drift: Debug impl not found")
    content = content.replace(
        dbg,
        "impl<REG: Readable> core::fmt::Debug for crate::generic::Reg<REG>\n"
        "where\n"
        "    R<REG>: core::fmt::Debug,\n"
        "    REG: UnconstrainedRead,",
        1,
    )

    content += "\n" + _GENERIC_ADDITIONS
    generic_path.write_text(content)


# svd2rust field-writer accessor: `pub fn <field>(&mut self) -> <FIELD>_W<...>`.
# The `&mut self` uniquely identifies the WRITER accessor (the reader is
# `&self`, the enum-variant setter takes `self`).
def _field_writer_accessor_re(field_lower: str) -> "re.Pattern":
    return re.compile(rf"(pub fn {re.escape(field_lower)}\(&mut self)(\))")


def patch_field_accessors(device_dir: Path, plans: list[RegisterPlan]) -> int:
    """Field-level gating (opt-in): make each gated field's writer accessor
    require its witness. `w.stop()` becomes `w.stop(&witness)`, so a closure
    that sets the field without a witness fails to compile (E0061) while
    sibling fields and the register's own `write`/`modify` are untouched.
    Returns the number of accessors patched.

    KNOWN GAP (see the plan's "Field-level gating" section): the field gate
    covers the field accessor, so it soundly gates `modify` (which retains
    untouched fields). The whole-register `write`/`reset` compose the register
    from a base value and so write the gated field too, but they are NOT
    gated. A per-call compile warning there is not expressible in Rust (a
    concrete `write` collides with the generic one, E0592), so this stays an
    acknowledged bypass---like `unsafe`---flagged loudly here at generation
    time."""
    patched = 0
    for plan in plans:
        if not plan.field_gates:
            continue
        reg_file = device_dir / plan.peripheral / f"{plan.reg_lower}.rs"
        if not reg_file.is_file():
            raise FileNotFoundError(reg_file)
        text = reg_file.read_text()
        for fg in plan.field_gates.values():
            witness = fg.witness_name(plan.reg_name)
            pat = _field_writer_accessor_re(fg.field_lower)
            new_text, n = pat.subn(
                rf"\1, _witness: &super::constraints::{witness}\2", text)
            if n != 1:
                raise RuntimeError(
                    f"{reg_file}: expected exactly one writer accessor "
                    f"`pub fn {fg.field_lower}(&mut self)`, found {n} — "
                    "field-level gating patch aborted"
                )
            text = new_text
            patched += 1
        reg_file.write_text(text)
        if "write" not in plan.preconditions:
            fields = ", ".join(sorted(plan.field_gates))
            print(
                f"WARNING: {plan.peripheral}/{plan.reg_name}: field-level "
                f"gating enforces field(s) [{fields}] on `modify` and the "
                f"field accessor, but this register's whole-register "
                f"`write`/`reset` stay UNGATED and can write those fields "
                f"unchecked (an acknowledged bypass, like `unsafe`; a per-call "
                f"warning is not expressible in Rust). Use `modify` for "
                f"sibling-field writes.",
                file=sys.stderr,
            )
    return patched


# --------------------------------------------------------------------------- #
# Marker walk: every register in the device gets Unconstrained* impls except
# the (spec, op) pairs the constraints gate.
# --------------------------------------------------------------------------- #

_READABLE_RE = re.compile(r"impl crate::Readable for (\w+) \{")
_WRITABLE_RE = re.compile(r"impl crate::Writable for (\w+) \{")


def add_marker_impls(device_dir: Path, gated: set[tuple[str, str, str]]) -> int:
    """Append Unconstrained* marker impls to every register file. Returns the
    number of files patched. ``gated`` holds (peripheral module, RegisterSpec,
    op) triples to skip — absence of the marker IS the gate. The peripheral is
    keyed by path so equally-named specs in other peripherals (CR1rs exists in
    many) keep their markers."""
    patched = 0
    for rs_file in sorted(device_dir.rglob("*.rs")):
        text = rs_file.read_text()
        if MARKER_SENTINEL in text:
            raise RuntimeError(
                f"{rs_file} already carries LIDAR markers; injection is one-shot"
            )
        rel = rs_file.relative_to(device_dir)
        periph = rel.parts[0].removesuffix(".rs")
        readable = _READABLE_RE.findall(text)
        writable = _WRITABLE_RE.findall(text)
        if not readable and not writable:
            continue
        lines = ["", MARKER_SENTINEL]
        for spec in readable:
            if (periph, spec, "read") not in gated:
                lines.append(f"impl crate::UnconstrainedRead for {spec} {{}}")
        for spec in writable:
            if (periph, spec, "write") not in gated:
                lines.append(f"impl crate::UnconstrainedWrite for {spec} {{}}")
        for spec in writable:
            if spec in readable and (periph, spec, "modify") not in gated:
                lines.append(f"impl crate::UnconstrainedModify for {spec} {{}}")
        if len(lines) > 2:
            rs_file.write_text(text + "\n".join(lines) + "\n")
            patched += 1
    return patched


def inject_constraints_module(peripheral_file: Path,
                              plans: list[RegisterPlan]) -> None:
    """Append ONE `pub mod constraints { ... }` holding every constrained
    register of this peripheral (a peripheral may have several — e.g. F1's
    AFIO gates both EVCR and MAPR; type names are register-scoped so the
    merged module cannot collide).

    A read-gated register makes `Reg<...>` lose its (read-performing) Debug
    impl, so the peripheral RegisterBlock's `#[derive(Debug)]` must go — a
    documented API consequence of read gating (debug-printing reads).
    """
    text = peripheral_file.read_text()
    if MODULE_SENTINEL in text:
        raise RuntimeError(
            f"{peripheral_file} already carries a LIDAR constraints module"
        )
    if any(plan.has_read_gate() for plan in plans):
        derive = "#[derive(Debug)]\n///Register block\npub struct RegisterBlock {"
        if derive in text:
            text = text.replace(
                derive,
                "// LIDAR: Debug derive removed — this block contains a "
                "read-gated register\n///Register block\npub struct RegisterBlock {",
                1,
            )
    parts = []
    for i, p in enumerate(plans):
        code = generate_constraint_module(p)
        if i > 0:
            # `//!` inner docs are only legal at the top of the module; demote
            # subsequent registers' headers to plain comments.
            code = "\n".join(
                ("//" + line[3:]) if line.startswith("//!") else line
                for line in code.splitlines()
            ) + "\n"
        parts.append(code)
    module_code = "\n".join(parts)
    indented = "\n".join(
        ("    " + line) if line.strip() else "" for line in module_code.splitlines()
    )
    text += (
        f"\n{MODULE_SENTINEL}\n"
        "///Datasheet access-constraint witnesses and checks\n"
        f"pub mod constraints {{\n{indented}\n}}\n"
    )
    peripheral_file.write_text(text)


def prune_plans_for_device(device_dir: Path,
                           plans: list[RegisterPlan]) -> list[RegisterPlan]:
    """Drop gates each register's real access mode cannot express (checked
    against the generated register file itself — the ground truth). Mutates
    the plans; returns those with something left to gate. Idempotent, and
    callable by drivers BEFORE saving artifacts so the record matches what is
    actually injected."""
    kept = []
    for plan in plans:
        reg_file = device_dir / plan.peripheral / f"{plan.reg_lower}.rs"
        spec = f"{plan.reg_name.upper()}rs"
        reg_text = reg_file.read_text() if reg_file.is_file() else ""
        removed = plan.prune_for_access(
            readable=f"impl crate::Readable for {spec}" in reg_text,
            writable=f"impl crate::Writable for {spec}" in reg_text,
        )
        if removed:
            print(f"  note: {plan.peripheral}/{plan.reg_name}: dropped "
                  f"{removed} gate(s) — unsupported by the register's "
                  "access mode")
        if plan.preconditions or plan.field_gates:
            kept.append(plan)
        else:
            print(f"  note: {plan.peripheral}/{plan.reg_name}: nothing left "
                  "to gate; skipped")
    return kept


def inject_into_pac(pac_root: Path, device: str, plans: list[RegisterPlan]) -> None:
    src = pac_root / "src"
    generic = src / "generic.rs"
    device_dir = src / device
    if not generic.exists() or not device_dir.is_dir():
        raise FileNotFoundError(f"{generic} / {device_dir}")
    plans = prune_plans_for_device(device_dir, plans)
    by_periph: dict[str, list[RegisterPlan]] = {}
    gated: set[tuple[str, str, str]] = set()
    for plan in plans:
        peripheral_file = device_dir / f"{plan.peripheral}.rs"
        if not peripheral_file.is_file():
            raise FileNotFoundError(peripheral_file)
        by_periph.setdefault(plan.peripheral, []).append(plan)
        gated |= plan.gated_ops()

    patch_generic_rs(generic)
    n = add_marker_impls(device_dir, gated)
    for periph, periph_plans in by_periph.items():
        inject_constraints_module(device_dir / f"{periph}.rs", periph_plans)
    # Field-level gating: patch the per-field writer accessors (no-op when no
    # plan carries field gates, so whole-register-only injection is unchanged).
    fields_patched = patch_field_accessors(device_dir, plans)
    kept = [p for periph_plans in by_periph.values() for p in periph_plans]
    extra = f", {fields_patched} field accessor(s)" if fields_patched else ""
    print(f"Patched generic.rs, added markers to {n} register files{extra}, "
          f"injected constraints for: "
          + ", ".join(f"{p.peripheral}/{p.reg_name}" for p in kept))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _load_plan(json_path: str, peripheral: str,
               field_level_gating: bool = False) -> RegisterPlan:
    data = json.loads(Path(json_path).read_text())
    return RegisterPlan(RegisterInfo(**data), peripheral,
                        field_level_gating=field_level_gating)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate trait-gated constraint Rust from RegisterInfo JSON"
    )
    ap.add_argument("input", nargs="?", help="RegisterInfo JSON (v1 schema)")
    ap.add_argument("--peripheral", help="peripheral name for `input`, e.g. i2c1")
    ap.add_argument("--constraint", action="append", default=[],
                    metavar="PERIPHERAL=FIXTURE.json",
                    help="additional (or sole) constraint inputs; repeatable")
    ap.add_argument("--output", help="write the standalone constraints module here")
    ap.add_argument("--inject-pac",
                    help="PAC crate root (e.g. vendored/pac/stm32f4) to inject into")
    ap.add_argument("--device", default="stm32f405",
                    help="device module inside the PAC (default: stm32f405)")
    ap.add_argument("--field-level-gating", action="store_true",
                    help="OPT-IN: enforce field-scoped constraints by gating "
                         "the per-field writer accessor (default off: "
                         "field-scoped constraints are skipped with a warning)")
    args = ap.parse_args()

    flg = args.field_level_gating
    plans: list[RegisterPlan] = []
    if args.input:
        if not args.peripheral:
            ap.error("--peripheral is required with a positional input")
        plans.append(_load_plan(args.input, args.peripheral, flg))
    for spec in args.constraint:
        peripheral, _, path = spec.partition("=")
        if not path:
            ap.error(f"--constraint needs PERIPHERAL=FIXTURE.json, got {spec!r}")
        plans.append(_load_plan(path, peripheral, flg))
    if not plans:
        ap.error("no constraint inputs given")

    if args.inject_pac:
        inject_into_pac(Path(args.inject_pac), args.device, plans)
    else:
        if len(plans) != 1:
            ap.error("standalone mode takes exactly one constraint input")
        code = generate_constraint_module(plans[0])
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(code)
            print(f"Generated: {out}")
        else:
            sys.stdout.write(code)


if __name__ == "__main__":
    main()
