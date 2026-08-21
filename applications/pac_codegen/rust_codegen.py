#!/usr/bin/env python3
"""Constraint-aware Rust code generator for svd2rust PAC crates (trait gating).

Reads a RegisterInfo JSON (grammar-v2 schema from the repo-root ``defs.py``)
and turns its ``access_constraints_v2`` state gates into compile-time
enforcement inside a PAC crate. (Old v1 generator output is converted first
with ``convert_v1_to_v2.py``.)

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

# Repo root (three levels up) for the shared grammar schema (defs.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from defs import RegisterInfo  # noqa: E402

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


def _is_same_register(register_name: str, target: str) -> bool:
    ref = _norm_reg_name(register_name)
    tgt = _norm_reg_name(target)
    return ref == tgt or ref.endswith(tgt)


def _extend_unique(bucket: list, items) -> None:
    """Append each item whose ``.key()`` is not already present, preserving
    order — the emitter's de-dup for preconditions across constraints."""
    seen = {p.key() for p in bucket}
    for p in items:
        if p.key() not in seen:
            bucket.append(p)
            seen.add(p.key())


def _unique_sources(preconditions) -> list["SourceRegister"]:
    """Ordered, de-duplicated cross-register witness sources in a precondition
    list (a same-register precondition has no source)."""
    out, seen = [], set()
    for p in preconditions:
        if p.source and p.source.key() not in seen:
            out.append(p.source)
            seen.add(p.source.key())
    return out


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


# Rust's reserved words, including the 2018/2021 additions and the words
# reserved-for-future-use. svd2rust cannot name a method after one of these,
# so when a datasheet field collides it appends an underscore:
#
#     pub type PRIV_R = crate::BitReader;
#     pub fn priv_(&self) -> PRIV_R { ... }
#
# Emitting `r.priv()` -- the field name lowercased, which is what a precondition
# naively spells -- is a PARSE error, so the whole chip crate dies, not just the
# constrained register. The security-enabled families (L5, H5, H7-S) all carry a
# PRIV bit, and all three failed exactly here.
_RUST_KEYWORDS = frozenset("""
as break const continue crate dyn else enum extern false fn for if impl in let
loop match mod move mut pub ref return self Self static struct super trait true
type unsafe use where while async await box do final macro override priv try
typeof unsized virtual yield abstract become
""".split())


def field_accessor(field: str) -> str:
    """The generated accessor method name for a datasheet field."""
    f = field.lower()
    return f + "_" if f in _RUST_KEYWORDS else f


class Precondition:
    """A field-state check, validated and value-parsed. ``source`` is None
    for same-register conditions, else the resolved cross-register source.

    ``cond`` is a grammar-v2 ``FieldCondition`` (``register``/``field``/
    ``state``/``values``); its values are already parsed to ``int`` by the
    grammar, so no raw text is ever spliced into Rust."""

    def __init__(self, cond, source: "SourceRegister | None" = None):
        self.source = source
        self.field = cond.field
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", self.field or ""):
            raise ValueError(
                f"field name {self.field!r} is not an SVD-style identifier "
                "(ranges/wildcards/pseudo-fields are rejected)"
            )
        if cond.state == "cleared":
            self.kind, self.value = "cleared", None
        elif cond.state == "set":
            self.kind, self.value = "set", None
        elif cond.state == "equals":
            if len(cond.values) != 1:
                raise ValueError(
                    f"equals condition on {self.field!r} has {len(cond.values)} "
                    "values; the emitter supports a single value only "
                    "(OR-values are not enforceable as one check)"
                )
            self.kind, self.value = "equals", cond.values[0]
        else:
            raise ValueError(f"unsupported condition state {cond.state!r}")

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
        accessor = field_accessor(self.field)
        if self.kind == "cleared":
            return f"{reader}.{accessor}().bit_is_clear()"
        if self.kind == "set":
            return f"{reader}.{accessor}().bit_is_set()"
        return f"{reader}.{accessor}().bits() == {self.value:#x}"

    def reader_shape(self) -> str:
        """The svd2rust reader shape ``check_expr`` needs: ``equals`` calls
        ``bits()`` (FieldReader only), set/cleared call ``bit_is_*``
        (BitReader only)."""
        return "field" if self.kind == "equals" else "bit"

    def narrow_to_bit(self) -> bool:
        """Respell an ``equals`` check on a 1-bit field as set/cleared — the
        same condition, in the API BitReader actually has. False when the
        value cannot be one bit (the condition is unsatisfiable as written)."""
        if self.kind != "equals":
            return True
        if self.value in (0, 1):
            self.kind, self.value = ("set" if self.value else "cleared"), None
            return True
        return False

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
        self.field_lower = field_accessor(field)
        self.preconditions: list["Precondition"] = []
        self.docs: list[str] = []

    def sources(self) -> list["SourceRegister"]:
        return _unique_sources(self.preconditions)

    def witness_name(self, reg: str) -> str:
        return f"{reg.capitalize()}{self.field.capitalize()}FieldWitness"

    def check_name(self) -> str:
        return f"check_{self.field_lower}_field_ready"


def _build_preconditions(constraint, peripheral: str) -> list["Precondition"]:
    """Resolve a state_gate's conditions to Preconditions — same-register, or a
    cross-register ``SourceRegister``. Shared by whole-register and field
    gates (the resolution rule is identical)."""
    pres = []
    for cond in constraint.preconditions:
        if _is_same_register(cond.register, constraint.target_register):
            pres.append(Precondition(cond))
        else:
            pres.append(Precondition(
                cond, SourceRegister(cond.register, peripheral)))
    return pres


# --------------------------------------------------------------------------- #
# Per-kind codegen enablement                                                  #
# --------------------------------------------------------------------------- #

# Grammar-v2 kinds the emitter can translate to Rust. Every kind listed here is
# ENABLED by default; to stop emitting one that misbehaves, disable it (CLI
# ``--disable-kind KIND`` or ``disabled_kinds=``). A constraint of a disabled
# kind — or of a kind with no emitter yet — is SKIPPED with a warning, never
# emitted. This is the single source of truth shared by the emitter
# (``RegisterPlan``) and the driver (``inject_from_run.select_and_plan``).
SUPPORTED_KINDS = frozenset({"state_gate"})


def enabled_kinds(disabled=None) -> frozenset:
    """Kinds the emitter will translate, given an optional set to disable."""
    return SUPPORTED_KINDS - frozenset(disabled or ())


class FieldGatingDisabled(ValueError):
    """Every constraint on this register was field-scoped and field-level
    gating is off, so nothing was emitted.

    NOT an emitter limitation, which is why it is distinguishable: the
    emitter builds these gates perfectly well with ``field_level_gating=True``
    (CLI ``--field-level-gating``). It is switched off by DEFAULT because
    gating a whole register for a rule about one of its fields would demand
    the precondition for writes to unrelated fields. Reporting it as
    "emitter_rejected" made a policy default read as a codegen gap -- and it
    is the single largest such bucket in the corpus.
    """


class RegisterPlan:
    """Everything the emitter needs for one constrained register."""

    def __init__(self, register_info: RegisterInfo, peripheral: str,
                 field_level_gating: bool = False, disabled_kinds=None):
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
        # svd2rust-operation -> ordered unique preconditions; op in
        # {"write", "read", "modify"}. "modify" is the DERIVED union bucket: a
        # write target feeds {write, modify}, a read target feeds {read, modify}.
        self.preconditions: dict[str, list[Precondition]] = {}
        # op -> constraint doc lines (datasheet text + consequence)
        self.docs: dict[str, list[str]] = {}
        # field-lowercase -> FieldGate (populated only when field_level_gating)
        self.field_gates: dict[str, FieldGate] = {}
        # Kinds this plan will emit (all supported kinds minus any disabled).
        self._enabled_kinds = enabled_kinds(disabled_kinds)
        # Constraints skipped ONLY because field-level gating is off; they
        # would have produced field gates with it on.
        self._skipped_field_scoped = 0

        for c in register_info.access_constraints_v2:
            if c.kind not in self._enabled_kinds:
                why = ("no codegen emitter yet"
                       if c.kind not in SUPPORTED_KINDS
                       else "codegen disabled for this kind")
                print(
                    f"WARNING: {self.reg_name}: skipping {c.kind} constraint "
                    f"({why}); this constraint is NOT enforced.",
                    file=sys.stderr,
                )
                continue
            getattr(self, f"_emit_{c.kind}")(c, peripheral, field_level_gating)

        if not self.preconditions and not self.field_gates:
            if self._skipped_field_scoped:
                raise FieldGatingDisabled(
                    f"{self.reg_name}: {self._skipped_field_scoped} "
                    "field-scoped constraint(s) skipped because field-level "
                    "gating is disabled; nothing left to gate "
                    "(enable with --field-level-gating)")
            raise ValueError(f"{self.reg_name}: no enforceable constraints")

    def _emit_state_gate(self, c, peripheral: str,
                         field_level_gating: bool) -> None:
        """Emit one state_gate: a whole-register precondition gate, or (opt-in,
        default off) a per-field gate for a field-scoped constraint."""
        if c.target_fields:
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
                self._skipped_field_scoped += 1
                return
            self._add_field_gate(c, peripheral)
            return
        if c.postconditions:
            raise NotImplementedError(
                f"{self.reg_name}: postconditions/action witnesses are "
                "roadmap step I; not emitted yet"
            )
        pres = _build_preconditions(c, peripheral)
        op_raw = c.target_operation.strip().lower()
        # svd2rust modify() = one read + one write, so its obligations are
        # the UNION of the register's read and write constraints. modify is
        # DERIVED here (a "modify" bucket fed by both surfaces), never a
        # first-class target. Datasheet prose "modify/change a register"
        # means writing it, so a legacy "modify" gates the write surface.
        if op_raw in ("write", "modify"):
            ops = ["write", "modify"]        # a modify performs a write
        elif op_raw in ("read", "any", "read/write", "read-write"):
            same = [p for p in pres if p.source is None]
            if same:
                # A read (and a modify's RMW read) reads the target; gating
                # it on a condition read FROM the target is self-defeating.
                raise ValueError(
                    f"{self.reg_name}: same-register read gate on "
                    f"{[p.field for p in same]} is self-defeating (the "
                    "check performs the constrained read); rejected"
                )
            # read gates modify() too (a modify performs a read); "any"/
            # "read/write" gate every surface.
            ops = (["read", "modify"] if op_raw == "read"
                   else ["read", "write", "modify"])
        else:
            raise ValueError(
                f"{self.reg_name}: unsupported target_operation "
                f"{c.target_operation!r} (expected read/write/any; "
                "modify is derived from read+write, not a target)"
            )
        if not pres:
            raise ValueError(
                f"{self.reg_name}: constraint has no preconditions — "
                "nothing to enforce (grammar-v2 `other` material)"
            )
        for op in ops:
            _extend_unique(self.preconditions.setdefault(op, []), pres)
            doc = self.docs.setdefault(op, [])
            line = c.datasheet_text.strip()
            if line and line not in doc:
                doc.append(line)

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
        pres = _build_preconditions(c, peripheral)
        if not pres:
            raise ValueError(
                f"{self.reg_name}: field-scoped constraint has no "
                "preconditions — nothing to enforce"
            )
        doc = c.datasheet_text.strip()
        for field in c.target_fields:
            fg = self.field_gates.setdefault(field.lower(), FieldGate(field))
            _extend_unique(fg.preconditions, pres)
            if doc and doc not in fg.docs:
                fg.docs.append(doc)

    def sources(self, op: str) -> list["SourceRegister"]:
        """Ordered unique cross-register sources for one operation."""
        return _unique_sources(self.preconditions[op])

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

def doc_lines(text: str, indent: str = "    ") -> list:
    """A datasheet quote as legal Rust doc-comment lines.

    Quotes are lifted verbatim from the manual and a good number of them span
    several lines -- RM0440's FDCAN rule is "The following registers can be
    written only when the CCE bit is cleared:" followed by a bulleted list.
    Interpolating that into a single `/// {doc}` prefixes only the FIRST line;
    the rest land as bare text inside an `impl` block and the crate stops
    parsing:

        error: expected item after doc comment
           --> src/stm32g4a1/fdcan.rs:813:9

    which takes down the whole chip crate, not just one register. Seven of the
    48 sweep targets failed this way. Every line gets its own `///`, and blank
    lines are kept as `///` so paragraphs survive.
    """
    out = []
    for raw in text.splitlines():
        line = raw.rstrip()
        out.append(f"{indent}///{' ' + line.strip() if line.strip() else ''}")
    return out or [f"{indent}///"]


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
    for op in sorted(plan.preconditions):
        _extend_unique(all_pres, plan.preconditions[op])
    for fname in sorted(plan.field_gates):
        _extend_unique(all_pres, plan.field_gates[fname].preconditions)
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

    def emit_check_body(w, pres, srcs) -> None:
        # Body shared by the whole-register and field-gate check methods: one
        # fresh read of self (only if a same-register precondition needs it) and
        # of each source register, a guard per precondition, then mint the ZST
        # witness.
        if any(p.source is None for p in pres):
            a("        let r = self.read();")
        for s in srcs:
            a(f"        let r_{s.var()} = {s.var()}.read();")
        for p in pres:
            a(f"        if !({p.check_expr(p.reader_var())}) {{")
            a(f"            return Err({err}::{p.error_variant()});")
            a("        }")
        a(f"        Ok({w} {{ _priv: () }})")

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
            for line in doc_lines(doc):
                a(line)
        a("    #[inline(always)]")
        a(f"    pub fn check_{op}_ready(&self{src_params(op)}) -> Result<{w}, {err}> {{")
        emit_check_body(w, pres, srcs)
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
        srcs = fg.sources()
        a(f"    /// Check every precondition for writing the {fg.field} field "
          f"of {reg}.")
        a("    ///")
        a("    /// # Constraint")
        for doc in fg.docs:
            for line in doc_lines(doc):
                a(line)
        a("    #[inline(always)]")
        a(f"    pub fn {fg.check_name()}(&self{_src_params(srcs)}) "
          f"-> Result<{w}, {err}> {{")
        emit_check_body(w, pres, srcs)
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


# marker trait -> the operation it gates, so a bound can be skipped when this
# crate gates nothing of that operation.
_BOUND_OP = {"UnconstrainedRead": "read", "UnconstrainedWrite": "write",
             "UnconstrainedModify": "modify"}
ALL_OPS = frozenset(_BOUND_OP.values())


def patch_generic_rs(generic_path: Path, gated_ops=None) -> None:
    """Gate the stock methods and append the witnessed/unwitnessed surface.

    ``gated_ops`` (default: all three) is the set of operations this crate
    ACTUALLY gates. A bound is emitted only for those.

    Why it matters: a bound on an operation that no register gates enforces
    nothing — every register carries the marker — yet every *generic*
    downstream signature must still name it, because generic code cannot
    prove a bound for an unresolved associated type. That is precisely the
    "generic friction" error class. Bounding only what is gated makes the
    friction proportional to the operations really constrained instead of a
    flat cost of installing the encoding, and cannot weaken enforcement: an
    operation with no gate has nothing to enforce.

    The drift checks still run for every signature, gated or not — a template
    that moved must fail loudly regardless of what this crate happens to gate.
    """
    ops = ALL_OPS if gated_ops is None else frozenset(gated_ops)
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
    if "read" in ops:
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
    if "write" in ops:
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
        if _BOUND_OP[bound] not in ops:
            continue
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
    if "read" in ops:
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
    # Resolve through DeviceLayout: stm32h7 keeps its register files in a
    # shared src/common/<periph>/<hash>/ tree, so the flat
    # device_dir/<periph>/<reg>.rs guess is a FileNotFoundError there. The
    # whole-register path was converted when that layout was first supported;
    # this one is reached only under --field-level-gating and was missed.
    layout = DeviceLayout(device_dir)
    for plan in plans:
        if not plan.field_gates:
            continue
        reg_file = layout.register_file(plan.peripheral, plan.reg_lower)
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


# stm32-rs 0.16 ships TWO device layouts, and the injector has to walk both.
#
#   flat            device/<periph>.rs  +  device/<periph>/<reg>.rs
#                   -- 20 of the 21 crates we provision.
#   deduplicated    device/mod.rs carries
#                       #[path = "../common/<periph>/<hash>/mod.rs"]
#                       pub mod <periph>;
#                   and the register files sit beside that mod.rs, SHARED between
#                   every device whose block is byte-identical. stm32h7 0.16.0 is
#                   the only crate using it today -- and without support for it
#                   all five H7 manuals inject ZERO registers, every peripheral
#                   reported "not in device".
_MOD_PATH_RE = re.compile(
    r'#\[path\s*=\s*"([^"]+)"\]\s*(?:pub\s+)?mod\s+(\w+)\s*;')


class DeviceLayout:
    """Where one device module's peripheral and register files actually live."""

    def __init__(self, device_dir: Path):
        self.device_dir = device_dir
        self.paths: dict = {}
        mod_rs = device_dir / "mod.rs"
        if mod_rs.is_file():
            for m in _MOD_PATH_RE.finditer(mod_rs.read_text()):
                rel, name = m.group(1), m.group(2)
                target = (device_dir / rel).resolve()
                if target.is_file():
                    self.paths[name.lower()] = target

    @property
    def deduplicated(self) -> bool:
        return bool(self.paths)

    def module_file(self, periph: str) -> Path:
        """The peripheral's module file -- where a constraints module is
        appended and where marker impls for its registers are reachable."""
        return self.paths.get(periph.lower(),
                              self.device_dir / f"{periph}.rs")

    def register_file(self, periph: str, reg: str) -> Path:
        p = self.paths.get(periph.lower())
        base = p.parent if p else self.device_dir / periph
        return base / f"{reg}.rs"

    def iter_register_files(self):
        """(peripheral, file) for every .rs holding register definitions."""
        if self.deduplicated:
            for periph, mod_path in sorted(self.paths.items()):
                for f in sorted(mod_path.parent.rglob("*.rs")):
                    yield periph, f
            return
        for f in sorted(self.device_dir.rglob("*.rs")):
            rel = f.relative_to(self.device_dir)
            yield rel.parts[0].removesuffix(".rs"), f


def add_marker_impls(device_dir: Path, gated: set[tuple[str, str, str]],
                     skip_marked: bool = False) -> int:
    """Append Unconstrained* marker impls to every register file. Returns the
    number of files patched. ``gated`` holds (peripheral module, RegisterSpec,
    op) triples to skip — absence of the marker IS the gate. The peripheral is
    keyed by path so equally-named specs in other peripherals (CR1rs exists in
    many) keep their markers."""
    patched = 0
    seen: set = set()
    for periph, rs_file in DeviceLayout(device_dir).iter_register_files():
        if rs_file in seen:
            continue            # a shared block reachable under two names
        seen.add(rs_file)
        text = rs_file.read_text()
        if MARKER_SENTINEL in text:
            if skip_marked:
                continue        # deduplicated layout: block shared with the
            raise RuntimeError( #   injected device, already handled there
                f"{rs_file} already carries LIDAR markers; injection is one-shot"
            )
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
    # Field-gated registers whose whole-register write stays open (a bypass):
    # annotate the register's own doc with the caveat, so a developer looking
    # up how to write it sees it in rustdoc / IDE hover. The generic `write`
    # itself cannot be annotated per-register (E0592), but the register's
    # type-alias doc is ours to extend (the `///` lines concatenate onto the
    # existing `/** */` block doc).
    for p in plans:
        if not p.field_gates or "write" in p.preconditions:
            continue
        reg_up = p.reg_name.upper()
        type_line = f"pub type {reg_up} = crate::Reg<{p.reg_lower}::{reg_up}rs>;"
        if type_line not in text:
            continue
        fields = ", ".join(f"`{f}`" for f in sorted(p.field_gates))
        caveat = (
            "///\n"
            "///# Field-level datasheet constraints (LIDAR)\n"
            f"///Writes to field(s) {fields} are gated (see the `constraints` "
            f"module of [`mod@{p.reg_lower}`]). Prefer "
            "[`modify`](crate::Reg::modify) with the witnessed field accessor "
            "`w.<field>(&witness)`; a whole-register "
            "[`write`](crate::Reg::write) or [`reset`](crate::Reg::reset) "
            "writes those fields **unchecked**.\n"
        )
        text = text.replace(type_line, caveat + type_line, 1)
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


# A generated field reader comes in exactly two shapes, and they share no
# accessor: a 1-bit field reads through `BitReader` (bit/bit_is_set/
# bit_is_clear, NO bits()), a multi-bit field through `FieldReader` (bits(),
# no bit_is_*). A precondition whose state does not match its field's shape
# emits a call to a method that does not exist — E0599 inside the PAC itself,
# which breaks every downstream crate. The generated register file is the
# ground truth, exactly as it is for the access mode above.
_READER_DECL_RE = re.compile(
    r"^pub type (\w+)_R = crate::(BitReader|FieldReader)\b", re.M)
# svd2rust de-duplicates identical readers by re-export, in three shapes:
#   pub use HSION_R as PLLON_R;                        (same file)
#   pub use super::exticr1::EXTI0_R as EXTI4_R;        (sibling register)
#   pub use crate::<dev>::<periph>::<reg>::X_R as Y_R; (another peripheral)
_READER_ALIAS_RE = re.compile(
    r"^pub use ((?:\w+::)*)(\w+)_R as (\w+)_R\s*;", re.M)


class ReaderShapes:
    """Resolve a generated field reader to "bit" (1-bit ``BitReader``) or
    "field" (multi-bit ``FieldReader``) for one device module, following
    svd2rust's de-duplicating re-exports across register files."""

    def __init__(self, device_dir: Path):
        self.device_dir = device_dir
        self.layout = DeviceLayout(device_dir)
        self._files: dict = {}

    def _parse(self, periph: str, reg: str):
        key = (periph, reg)
        if key not in self._files:
            f = self.layout.register_file(periph, reg)
            if not f.is_file():
                self._files[key] = None
            else:
                text = f.read_text()
                decls = {m.group(1).lower():
                         ("bit" if m.group(2) == "BitReader" else "field")
                         for m in _READER_DECL_RE.finditer(text)}
                aliases = {}
                for m in _READER_ALIAS_RE.finditer(text):
                    segs = [s for s in m.group(1).split("::") if s]
                    if not segs:
                        target = (periph, reg)
                    elif len(segs) == 2 and segs[0] == "super":
                        target = (periph, segs[1])
                    elif len(segs) == 4 and segs[0] == "crate":
                        target = (segs[2], segs[3])
                    else:
                        continue                # unknown path shape: unresolved
                    aliases[m.group(3).lower()] = (target, m.group(2).lower())
                self._files[key] = (decls, aliases)
        return self._files[key]

    def has_register(self, periph: str, reg: str) -> bool:
        return self._parse(periph, reg) is not None

    def shape(self, periph: str, reg: str, field: str, _depth: int = 0):
        """"bit" | "field", or None when the register file, the field, or the
        re-export chain cannot be resolved."""
        parsed = self._parse(periph, reg)
        if parsed is None or _depth > 8:
            return None
        decls, aliases = parsed
        f = field.lower()
        if f in decls:
            return decls[f]
        if f in aliases:
            (p2, r2), f2 = aliases[f]
            return self.shape(p2, r2, f2, _depth + 1)
        return None


def _prune_plan_for_readers(shapes: ReaderShapes, plan: RegisterPlan) -> list[str]:
    """Reconcile every precondition with the shape of the field it reads.

    ``equals 0``/``equals 1`` on a 1-bit field is RESPELLED as cleared/set (no
    loss — same condition, compilable API). Anything the generated API cannot
    express drops the WHOLE gate, never just the offending condition: a gate
    missing one of its conjuncts would silently demand less than the datasheet
    does, which is worse than no gate at all. Returns what was dropped."""

    def locate(pre: Precondition) -> tuple[str, str]:
        if pre.source is None:
            return plan.peripheral, plan.reg_lower
        if pre.source.same_peripheral:
            return plan.peripheral, pre.source.reg
        return pre.source.periph_module, pre.source.reg

    def unusable(pre: Precondition) -> "str | None":
        periph, reg = locate(pre)
        if not shapes.has_register(periph, reg):
            return f"{pre.describe()}: {periph}/{reg} absent from the device"
        shape = shapes.shape(periph, reg, pre.field)
        if shape is None:
            return f"{pre.describe()}: field has no reader in the generated PAC"
        if shape == "bit" and not pre.narrow_to_bit():
            return f"{pre.describe()}: value does not fit a 1-bit field"
        if shape != pre.reader_shape():
            return (f"{pre.describe()}: {pre.kind} check needs a "
                    f"{pre.reader_shape()} reader, field is {shape}")
        return None

    removed = []
    for op in list(plan.preconditions):
        bad = [why for why in map(unusable, plan.preconditions[op]) if why]
        if bad:
            del plan.preconditions[op]
            plan.docs.pop(op, None)
            removed.append(f"{op} [{'; '.join(bad)}]")
    for fname in list(plan.field_gates):
        fg = plan.field_gates[fname]
        bad = [why for why in map(unusable, fg.preconditions) if why]
        if bad:
            del plan.field_gates[fname]
            removed.append(f"field:{fg.field} [{'; '.join(bad)}]")
    return removed


_PERIPH_ALIAS_RE = re.compile(
    r"^pub type (\w+) = crate::Periph<(\w+)::RegisterBlock", re.M)


def peripheral_instance_map(device_dir: Path) -> dict:
    """instance name (lowercase) -> the module owning its register types.

    svd2rust gives every peripheral INSTANCE a type alias over one shared
    register-block module, generated from the SVD's ``derivedFrom``::

        pub type I2C2 = crate::Periph<i2c1::RegisterBlock, 0x4000_5800>;

    So ``i2c2.rs`` does not exist and never will — I2C2's TIMEOUTR *is*
    ``i2c1::timeoutr::TIMEOUTRrs``, the same Rust type. Without this map a
    constraint extracted for any non-first instance is discarded as
    "peripheral not in device" even though the peripheral is on the chip:
    180 of 200 such drops in the STM sweep.

    Identity entries are included (``i2c1 -> i2c1``), so this is a complete
    instance->module map, not just the aliases. Empty when ``mod.rs`` is
    absent (other PAC layouts); callers then fall back to the file check.
    """
    mod_rs = device_dir / "mod.rs"
    if not mod_rs.is_file():
        return {}
    return {m.group(1).lower(): m.group(2).lower()
            for m in _PERIPH_ALIAS_RE.finditer(mod_rs.read_text())}


def _instance_key(name: str):
    """Order instances NUMERICALLY, not lexicographically: a plain string sort
    puts ``usart10`` before ``usart2``, so the "lowest instance" tie-break
    would silently pick the wrong one on any family with ten or more."""
    m = re.match(r"^(.*?)(\d*)$", name)
    return (m.group(1), int(m.group(2)) if m.group(2) else -1)


# A precondition names its source register the way the manual happened to
# write it, and the manual writes it differently for each instance: TIM4_CR1
# for TIM4, TIM5_CR1 for TIM5, and TIMx_CR1 where it uses its own placeholder.
# All three are the same relative reference -- "this peripheral's CR1" -- but
# compared literally they never match, so every rule whose precondition points
# at its own peripheral looked like a cross-instance disagreement.
_INST_NUM_RE = re.compile(r"(?<=[A-Za-z])\d+(?=_)")
_PLACEHOLDER_RE = re.compile(r"(?<=[A-Za-z])[Xx](?=_)")


def _norm_source_register(name: str) -> str:
    """TIM4_CR1, TIMX_CR1 and TIM_CR1 all collapse to TIM_CR1."""
    s = _PLACEHOLDER_RE.sub("", _INST_NUM_RE.sub("", (name or "").upper()))
    return s


def _norm_condition(text: str) -> str:
    """`FINIT == 0x1` and `FINIT set` are the same condition on a 1-bit field.

    Codegen already respells these when it knows the reader shape; conflict
    detection ran before that and so saw them as different readings."""
    s = _norm_source_register(text)
    s = re.sub(r"\s*==\s*0X1\b", " SET", s)
    s = re.sub(r"\s*==\s*0X0\b", " CLEARED", s)
    return s.strip()


def _plan_signature(plan: "RegisterPlan"):
    """What two plans must agree on to be one rule stated twice.

    Field gates are part of it: with --field-level-gating two instances can
    carry the same precondition but different field lists, and merging those
    silently would gate fields one instance never claimed."""
    pre = tuple(sorted(
        (op, tuple(sorted(_norm_condition(p.describe()) for p in pres)))
        for op, pres in plan.preconditions.items()))
    fields = tuple(sorted(getattr(plan, "field_gates", {}) or {}))
    return (pre, fields)


def _precondition_signature(plan: "RegisterPlan"):
    """The signature ignoring field gates -- "same rule, maybe different
    precision"."""
    return tuple(sorted(
        (op, tuple(sorted(_norm_condition(p.describe()) for p in pres)))
        for op, pres in plan.preconditions.items()))


def _plan_quotes(plan: "RegisterPlan"):
    return frozenset(" ".join(d.split())
                     for docs in (getattr(plan, "docs", {}) or {}).values()
                     for d in docs)


def _rule_quotes(plan: "RegisterPlan"):
    """Every datasheet sentence behind this plan, wherever it is stored.

    A whole-register gate keeps its quotes on the plan; a field gate keeps them
    on the FieldGate. A group can hold both -- one instance whose extraction
    named the bits and one whose did not -- so the comparison has to look in
    both places or the two never appear to be the same rule."""
    qs = set(_plan_quotes(plan))
    for fg in (getattr(plan, "field_gates", {}) or {}).values():
        qs |= {" ".join(d.split()) for d in fg.docs}
    return frozenset(qs)


_SELF_QUAL_RE = re.compile(r"\b([A-Z0-9]+(?:_[A-Z0-9]+)*)\.([A-Z0-9_]+)\b")


def _drop_self_qualifier(cond: str, reg_name: str) -> str:
    """`UART_CR1.UE CLEARED` and `UE CLEARED` are the same condition.

    One instance's extraction spelled the field with its own register in front
    of it and the others did not. A qualifier naming a DIFFERENT register is
    left alone -- that one really is a cross-register condition."""
    reg = (reg_name or "").upper()
    if not reg:
        return cond

    def sub(m):
        qual = m.group(1)
        if qual == reg or qual.rsplit("_", 1)[-1] == reg:
            return m.group(2)
        return m.group(0)

    return _SELF_QUAL_RE.sub(sub, cond)


def _rule_conditions(plan: "RegisterPlan"):
    """Every precondition behind this plan, normalised, from both places."""
    reg = getattr(plan, "reg_name", "")
    conds = set()
    for pres in (getattr(plan, "preconditions", {}) or {}).values():
        conds |= {_norm_condition(pc.describe()) for pc in pres}
    for fg in (getattr(plan, "field_gates", {}) or {}).values():
        conds |= {_norm_condition(pc.describe()) for pc in fg.preconditions}
    return frozenset(_drop_self_qualifier(c, reg) for c in conds)


def resolve_instance_collisions(plans: list) -> tuple[list, list]:
    """Collapse plans that target the SAME register-block module + register.

    Peripheral instances share their register types, so gating is
    all-or-nothing per module: two plans for i2c1/TIMEOUTR (one from I2C2,
    one from I2C3) would emit the same witness types twice and not compile.

    AGREEING plans collapse to one: that is a single rule the manual states
    once, which our per-instance iteration replicated. Dropping those would
    discard I2C1's own constraint merely because I2C2 carries it too.

    DISAGREEING plans are DROPPED ENTIRELY — the whole group, not "keep one".
    They are two readings of the same datasheet sentence and we cannot tell
    which is right: rm0008's USART_CR2 has one instance extracting
    ``CR1.TE cleared`` (correct) and another ``CR1.UE cleared`` (wrong), from
    an identical quote. The alternatives are all worse: unioning demands a
    precondition the datasheet does not, and picking one arbitrarily gates a
    register on a condition we have equal reason to think is the wrong one.
    A gate is a compile-time obligation on every downstream user, so
    contradictory evidence should buy no gate at all. The drop is recorded
    with the disagreeing instances so it stays reviewable.

    WHERE THIS SITS IN THE PIPELINE: after the constraint validator, so every
    colliding plan is already judge-``enforce``; the tie-break chooses between
    two CONFIRMED extractions that disagree, never between a confirmed and an
    unconfirmed one. It runs BEFORE the ``--chunks`` quote re-verification,
    which is a known ordering limitation: if the kept plan's quote turns out
    to be unanchored its gate is dropped, and a discarded twin whose quote
    would have anchored is already gone. No case in the corpus hits this (zero
    quote drops land on a multi-instance register), so the order stands.

    Returns (kept plans, conflict records).
    """
    groups: dict = {}
    for plan in plans:
        groups.setdefault((plan.peripheral, plan.reg_lower), []).append(plan)
    kept, conflicts, reviews = [], [], []
    for (module, reg), group in groups.items():
        if len(group) == 1:
            kept.append(group[0])
            continue
        instances = sorted((getattr(p, "source_instance", module) for p in group),
                           key=_instance_key)
        sigs = {_plan_signature(p) for p in group}
        if len(sigs) == 1:
            owner = next((p for p in group
                          if getattr(p, "source_instance", module) == module), None)
            kept.append(owner or min(
                group,
                key=lambda p: _instance_key(getattr(p, "source_instance", module))))
            continue

        # Same rule, differing precision. Two instances of one peripheral are
        # the same hardware block, described once in the manual, so a rule
        # extracted for one applies to all. When they differ it is almost
        # always precision, not disagreement: one extraction named the bits and
        # another named fewer or none.
        #
        # The test for "same rule" is per FIELD, because under field gating the
        # rule lives on the field gates -- plan.preconditions and plan.docs are
        # both empty there, so a plan-level comparison can never fire. For every
        # field two instances share, they must agree on its preconditions and
        # cite the same datasheet sentence. If they do, the merge is the UNION
        # of the field sets: the widest reading, which cannot miss a site a
        # narrower one would have caught.
        #
        # It is recorded for review rather than merged silently. A field named
        # by one instance and not another may be an incomplete extraction, or a
        # real difference between siblings (a UART is not quite a USART), and
        # only the manual settles which.
        quotes = {_rule_quotes(p) for p in group}
        conds = {_rule_conditions(p) for p in group}
        if len(quotes) == 1 and len(conds) == 1 and quotes != {frozenset()}:
            # The NARROWEST reading wins, not the widest. When one instance
            # named fields and another named none, the two are not a narrow
            # claim and a broad one -- they are one datasheet sentence
            # extracted at two precisions, and the sentence itself ("this
            # bitfield can only be written when...") is field-scoped. Adopting
            # the whole-register reading would gate sibling fields the sentence
            # never mentions, and every one of those is a false report against
            # downstream code. Under-gating loses a finding; over-gating
            # invents one.
            named = [p for p in group if (getattr(p, "field_gates", {}) or {})]
            if named:
                winner = max(named,
                             key=lambda p: len(getattr(p, "field_gates", {}) or {}))
                for pl in named:
                    for name, fg in (getattr(pl, "field_gates", {}) or {}).items():
                        winner.field_gates.setdefault(name, fg)
                how = ("merged to the union of the named fields [%s]"
                       % ", ".join(sorted(winner.field_gates)))
                if len(named) != len(group):
                    how += ("; %d instance(s) named no fields and were narrowed "
                            "to that union" % (len(group) - len(named)))
            else:
                winner = group[0]
                how = "merged as whole-register (no instance named fields)"
            kept.append(winner)
            reviews.append({
                "module": module, "register": reg, "instances": instances,
                "resolution": how,
                "field_sets": sorted(
                    ",".join(sorted(getattr(p, "field_gates", {}) or {}))
                    or "(whole register)" for p in group),
                "detail": "the instances cite the same datasheet sentence and "
                          "the same preconditions, so this is one rule "
                          "extracted at different precision. A person should "
                          "confirm the manual grants it to every instance.",
            })
            continue

        conflicts.append({
            "module": module, "register": reg, "instances": instances,
            "detail": "instances disagree on the gate for the same Rust "
                      "type after normalising instance-qualified register "
                      "names and equals/set conditions; dropped rather than "
                      "unioned (which would demand a precondition the "
                      "datasheet may not) or picked arbitrarily (which would "
                      "gate on a reading we have equal reason to think is "
                      "the wrong one)",
        })
    return kept, conflicts, reviews


def add_sibling_markers(src: Path, device: str) -> int:
    """Give every OTHER device module in the crate FULL markers.

    ``generic.rs`` is patched CRATE-wide, so its bounds apply to every device
    module the crate can build — but the marker walk covers only the injected
    one. Without this, downstream code that selects a SIBLING chip feature gets
    E0277 with our datasheet diagnostic for a register we never constrained:

        error[E0277]: `stm32f1::stm32f101::rcc::cr::CRrs` is write-constrained
                      by its datasheet

    a false positive, and an INVISIBLE one — a generic bound is only checked at
    a call site, so the PAC itself still compiles and no probe crate notices.

    Siblings get every marker and therefore behave exactly as an unpatched PAC.
    They are deliberately NOT gated: a manual's constraints were extracted for
    its own chip, and one crate can serve several manuals (four RMs share
    stm32f3), so propagating a gate sideways would enforce one chip's datasheet
    on another's. Sibling modules are `#[cfg(feature)]`-gated anyway, so the
    added impls are inert unless that chip is selected.

    Returns the number of files patched.

    In the deduplicated layout (stm32h7) sibling devices SHARE register-block
    files with the injected one. Those are skipped here rather than double
    marked: the block is literally the same code, so the injected chip's gate
    already applies to it. That over-applies one chip's rule to a sibling with a
    byte-identical block -- inert in practice, since only one chip feature is
    ever enabled.
    """
    total = 0
    for d in sorted(src.iterdir()):
        if not d.is_dir() or d.name in (device, "common"):
            continue
        if not any(d.rglob("*.rs")):
            continue
        total += add_marker_impls(d, set(), skip_marked=True)
    return total


def prune_plans_for_device(device_dir: Path,
                           plans: list[RegisterPlan]) -> list[RegisterPlan]:
    """Drop gates each register's real access mode cannot express, and gates
    whose preconditions the generated field readers cannot express (both
    checked against the generated register files themselves — the ground
    truth). Mutates the plans; returns those with something left to gate.
    Idempotent, and callable by drivers BEFORE saving artifacts so the record
    matches what is actually injected."""
    kept = []
    shapes = ReaderShapes(device_dir)
    layout = shapes.layout
    for plan in plans:
        reg_file = layout.register_file(plan.peripheral, plan.reg_lower)
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
        for why in _prune_plan_for_readers(shapes, plan):
            print(f"  note: {plan.peripheral}/{plan.reg_name}: dropped "
                  f"{why} — precondition not expressible against the "
                  "generated field reader")
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
    layout = DeviceLayout(device_dir)
    for plan in plans:
        peripheral_file = layout.module_file(plan.peripheral)
        if not peripheral_file.is_file():
            raise FileNotFoundError(peripheral_file)
        by_periph.setdefault(plan.peripheral, []).append(plan)
        gated |= plan.gated_ops()

    # Bound only the operations this crate actually gates (see
    # patch_generic_rs): an ungated operation has nothing to enforce, and
    # bounding it anyway is pure friction for generic downstream code.
    ops = {op for _, _, op in gated}
    patch_generic_rs(generic, ops)
    n = add_marker_impls(device_dir, gated)
    # generic.rs is crate-wide; so must the markers be. A flat single-device
    # crate (device ".") has no siblings — device_dir IS src.
    siblings = 0 if device == "." else add_sibling_markers(src, device)
    n += siblings
    for periph, periph_plans in by_periph.items():
        inject_constraints_module(layout.module_file(periph), periph_plans)
    # Field-level gating: patch the per-field writer accessors (no-op when no
    # plan carries field gates, so whole-register-only injection is unchanged).
    fields_patched = patch_field_accessors(device_dir, plans)
    kept = [p for periph_plans in by_periph.values() for p in periph_plans]
    extra = f", {fields_patched} field accessor(s)" if fields_patched else ""
    sib = f" ({siblings} in sibling device modules)" if siblings else ""
    print(f"Patched generic.rs, added markers to {n} register files{sib}{extra}, "
          f"injected constraints for: "
          + ", ".join(f"{p.peripheral}/{p.reg_name}" for p in kept))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _load_plan(json_path: str, peripheral: str,
               field_level_gating: bool = False,
               disabled_kinds=None) -> RegisterPlan:
    data = json.loads(Path(json_path).read_text())
    return RegisterPlan(RegisterInfo(**data), peripheral,
                        field_level_gating=field_level_gating,
                        disabled_kinds=disabled_kinds)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate trait-gated constraint Rust from RegisterInfo JSON"
    )
    ap.add_argument("input", nargs="?", help="RegisterInfo JSON (grammar-v2 schema)")
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
    ap.add_argument("--disable-kind", action="append", default=[],
                    metavar="KIND",
                    help="disable codegen for a grammar-v2 kind (repeatable); "
                         "its constraints are skipped with a warning. Default: "
                         "all supported kinds enabled.")
    args = ap.parse_args()

    flg = args.field_level_gating
    disabled = set(args.disable_kind)
    plans: list[RegisterPlan] = []
    if args.input:
        if not args.peripheral:
            ap.error("--peripheral is required with a positional input")
        plans.append(_load_plan(args.input, args.peripheral, flg, disabled))
    for spec in args.constraint:
        peripheral, _, path = spec.partition("=")
        if not path:
            ap.error(f"--constraint needs PERIPHERAL=FIXTURE.json, got {spec!r}")
        plans.append(_load_plan(path, peripheral, flg, disabled))
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
