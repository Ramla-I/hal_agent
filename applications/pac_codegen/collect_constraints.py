#!/usr/bin/env python3
"""
Dependency-invariant bridge: collect access constraints from a generator run.

This module closes the datasheet -> extraction -> codegen data path. It scans a
single generator-output run directory (the layout produced by the pipeline,
``agent_output/<manufacturer>/<device>/<run>/``, with one file per register named
``{peripheral}_{register}``), reads each register's ``access_constraints`` list,
and writes per-register constraints files in the exact schema that
``applications/pac_codegen/rust_codegen.py`` consumes (a ``RegisterInfo`` JSON,
matching the example fixture ``applications/pac_codegen/constraint_test/stm32f405_i2c1.json``).

GRAMMAR V2 (roadmap step D)
---------------------------
On top of forwarding the v1 constraints untouched, collection now LIFTS each
register's v1 constraints to grammar v2 (``defs.lift_v1_constraint``, table B.6
of docs/register_constraints_plan.md) and applies the B.4 repair-vs-reject
policy:

- deterministic drift is REPAIRED and logged (severity "info" -> "warning",
  "any"/"read/write" expanded to per-operation gates, hex/bin value strings
  normalized to int, enum state names -> values via SVD enumeratedValues,
  empty field_name -> explicit whole_register);
- judgment-requiring drift is REJECTED with a structured error entry
  ``{file, constraint_index, field, value, reason}`` -- per constraint, NEVER
  aborting a peripheral;
- ``%s``-placeholder register names (a run-dir filename plumbing bug, e.g.
  ``tim3_ccr%s``) are flagged in lint_flags and their constraints rejected with
  reason "placeholder_in_name" rather than guessing an expansion.

STAGE-0 LINT (roadmap step E, plan section 7.0)
-----------------------------------------------
On top of the lift, collection now runs the deterministic stage-0 lint:

- **Exact dedup** (within one register file's constraint list): constraints
  identical in (target register, operation, conditions, datasheet_text) --
  the per-bit fan-out and repeated-note pattern -- keep the FIRST occurrence;
  later ones are dropped with lint flag ``exact_duplicate`` and a
  ``duplicate_of`` back-reference. Dedup is deliberately NOT applied across
  peripheral instances' files (usart1_brr and usart2_brr stay separate rows;
  step H emits per-instance paths); instead, identical constraints repeated
  across a family's instances get the lint flag ``duplicate_across_instances``.
- **SVD-metadata lint** (needs ``--svd-dir``): ``equals`` values exceeding the
  SVD field/register bit width -> reject ``value_exceeds_field_width``;
  write/modify gates on an SVD read-only target -> reject
  ``write_constraint_on_read_only`` (FP by construction); postconditions that
  merely restate w1c/rc flag-clear semantics (SVD ``modifiedWriteValues``
  oneToClear/... or a status register with ``readAction``) -> reject
  ``w1c_flag_semantics`` + flag ``w1c_semantics``; read gates whose check
  touches a ``readAction`` register/field -> flag ``read_side_effect``.
- **Structural flags** (no SVD needed): read gates whose hardware-established
  preconditions all live on the target register itself -> reject
  ``self_defeating_read_gate`` (the check would perform the constrained read;
  codegen refuses these, collection stops them earlier); conditions whose
  register resolves to a DIFFERENT peripheral than the target (name-prefix
  heuristics + SVD peripheral attribution) -> flag ``cross_peripheral``
  (NOT a reject; step H emits cross-peripheral paths).

Each per-register output JSON keeps the v1 ``access_constraints`` key untouched
(codegen still consumes v1 until roadmap step B/H) and gains:

- ``access_constraints_v2``: the lifted v2 constraints, each annotated with its
  computed ``enforceability`` (defs.derive_enforceability -- never LLM-emitted);
- ``constraint_reports``: per-v1-constraint repair/reject/lint details.

A ``manifest.json`` is written next to the per-register files with per-register
and per-constraint entries (kind, enforceability, repairs, rejects, lint flags,
duplicates dropped) plus run-level metrics: the ``other``-rate (fraction of v2
constraints that needed the escape-valve kind), the reject-rate (over UNIQUE
post-dedup v1 constraints), dedup stats, a reject-reason histogram, and
lint-flag histograms (per-constraint and per-register).

SVD name resolution is OPTIONAL (``--svd-dir``, a directory of .svd files or
one .svd file): when given, every register/field name in a lifted constraint
is resolved against the SVDs (unresolvable names are rejected per B.4) and the
SVD-metadata lint above runs; when absent, both are skipped and registers
carry the lint flag ``svd_unchecked`` -- SVDs are never a hard requirement, so
corpus runs work without them.

NATIVE GRAMMAR-V2 REGISTERS (roadmap step F)
--------------------------------------------
The v2 prompt makes the generator emit grammar v2 directly: a register file
then carries ``"access_constraints": []`` (v1 key kept, empty),
``"access_constraints_v2": [...]`` and ``"schema_version": 2``. Collection
detects native v2 (schema_version == 2 or a non-empty access_constraints_v2
list), SKIPS the v1 lift, and runs the applicable stage-0 lint directly on
the native objects: per-constraint pydantic validation (a malformed entry is
rejected with reason ``invalid_v2_constraint``; siblings survive), exact
dedup, %s-placeholder rejects, target_register normalization, "any"
expansion, SVD name/width resolution, write-on-read-only, w1c postcondition
reclassification, self-defeating read gates, cross_peripheral/read_side_effect
flags, and the computed ``enforceability`` annotation. The manifest records
the constraint source (``native_v2`` vs ``lifted_v1``) per register plus
run-level counts of each.

NOTE ON SCOPE
-------------
This bridge collects, lifts, and lints; it does NOT judge whether a constraint
is faithful to the datasheet. Semantic validation is the Constraint Validator
(roadmap step G). Published corpus numbers from the stage-0 sweep live in
docs/constraints_corpus_stats.md.

Usage (CLI):
    python applications/pac_codegen/collect_constraints.py agent_output/stm/rm0041/24 \
        --output-dir applications/pac_codegen/constraints/rm0041_24 \
        [--svd-dir devices/stm/rm0041/svd]

    # Then generate Rust for one of the collected registers:
    python applications/pac_codegen/rust_codegen.py \
        applications/pac_codegen/constraints/rm0041_24/i2c1_cr1.json \
        --peripheral i2c1 --output applications/pac_codegen/generated/i2c1/constraints.rs

Programmatic:
    from applications.pac_codegen.collect_constraints import collect_constraints
    results = collect_constraints("agent_output/stm/rm0041/24",
                                  output_dir="applications/pac_codegen/constraints/rm0041_24")
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from pydantic import TypeAdapter, ValidationError

# Add the repo root to sys.path so we can import the shared defs.py.
# This file lives at applications/pac_codegen/collect_constraints.py, so the
# repo root is three levels up.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# This application's own directory (applications/pac_codegen/).
_APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT))

from defs import (  # noqa: E402  (path setup must precede import)
    ConstraintV2,
    RegisterAccessConstraint,
    RegisterInfo,
    derive_enforceability,
    lift_v1_constraint,
    parse_value_token,
)

# Per-constraint validator for NATIVE v2 constraints (plan section 6.1d:
# recovery is per-constraint, not per-response -- a malformed entry becomes a
# structured reject; well-formed siblings survive).
_CONSTRAINT_V2_ADAPTER = TypeAdapter(ConstraintV2)


# Files that may appear inside a run directory but are not register outputs.
_SKIP_NAMES = {".DS_Store"}
_SKIP_DIR_NAMES = {"info", "coverage_improver"}

# SVD <dim> array templates leave placeholders in run-dir file names (e.g.
# ``tim3_ccr%s``) -- root cause and proposed fix documented in
# docs/constraints_corpus_stats.md ("%s root cause"); the correct fix spans
# agent_tools/svd_parsing.py AND the coverage comparator, so stage 0 only
# refuses to guess an expansion.
_PLACEHOLDER = "%s"

# SVD modifiedWriteValues vocabularies that mean "writing this field
# manipulates a hardware-managed flag" (w1c/w0c and friends) rather than
# storing the written value. "modify" (the default behavior) is deliberately
# absent.
_MWV_FLAG_SEMANTICS = {
    "onetoclear", "zerotoclear", "clear",
    "onetoset", "zerotoset", "set",
    "onetotoggle", "zerototoggle",
}

_BIT_RANGE_RE = re.compile(r"^\[(\d+):(\d+)\]$")


def _family(name: str) -> str:
    """Peripheral family: instance name with trailing digits stripped
    (usart1 -> usart). Letter-suffixed instances (gpioa/gpiob) are handled by
    _families_compatible instead."""
    return name.strip().lower().rstrip("0123456789")


def split_peripheral_register(file_name: str) -> tuple[str, str]:
    """Split a ``{peripheral}_{register}`` file name on the first underscore.

    Mirrors the convention used by the validator (see
    ``core/s4_validator.py``: ``peripheral_name, register_name = name.split("_", 1)``).

    If there is no underscore, the whole name is treated as the peripheral and
    the register is left empty.
    """
    if "_" in file_name:
        peripheral, register = file_name.split("_", 1)
        return peripheral, register
    return file_name, ""


def _load_register_info(path: Path) -> Optional[tuple[RegisterInfo, list, bool]]:
    """Load and validate a single register output file.

    Returns ``(register_info, raw_v2_constraints, native_v2)`` or None (with a
    warning) if the file is not a parseable RegisterInfo JSON, so a single
    malformed file does not abort the whole run.

    ``native_v2`` is True when the file carries native grammar-v2 output
    (schema_version == 2 or a non-empty access_constraints_v2 list).
    ``raw_v2_constraints`` is the file's raw (unvalidated) v2 constraint list:
    the native lint validates each entry INDEPENDENTLY so one malformed
    constraint cannot take down its well-formed siblings (per-constraint
    recovery, plan section 6.1d) -- which is why the RegisterInfo parse below
    deliberately excludes the v2 list.
    """
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [skip] {path.name}: not readable JSON ({e})", file=sys.stderr)
        return None

    if not isinstance(data, dict) or "access_constraints" not in data:
        # Not a register output (e.g. a coverage report or other artifact).
        return None

    raw_v2 = data.get("access_constraints_v2")
    if not isinstance(raw_v2, list):
        raw_v2 = []
    native_v2 = data.get("schema_version") == 2 or bool(raw_v2)

    try:
        envelope = {k: v for k, v in data.items() if k != "access_constraints_v2"}
        return RegisterInfo(**envelope), raw_v2, native_v2
    except Exception as e:  # pydantic ValidationError or similar
        print(f"  [skip] {path.name}: does not match RegisterInfo ({e})",
              file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Optional SVD name resolution (B.4 "names unresolvable in the SVD")
# ---------------------------------------------------------------------------
# agent_tools/svd_parsing.py exposes peripheral/register NAMES and field
# COUNTS, but constraint resolution needs field NAMES and enumeratedValues,
# so we do the (minimal) ElementTree parsing here instead of forcing an API
# change on the pipeline's SVD utilities.


def _parse_svd_int(text: Optional[str]) -> Optional[int]:
    """Parse an SVD numeric literal (0x hex, #/0b binary, decimal) or None.

    SVD binary literals may carry don't-care bits ("#01xx"); those are treated
    as 0 -- good enough for enum-name repair, where an exact value is required
    anyway and don't-care enums are practically nonexistent in STM SVDs.
    """
    if text is None:
        return None
    t = text.strip()
    try:
        if t.lower().startswith("0x"):
            return int(t, 16)
        if t.startswith("#"):
            return int(t[1:].lower().replace("x", "0"), 2)
        if t.lower().startswith("0b"):
            return int(t, 2)
        return int(t, 10)
    except ValueError:
        return None


def _expand_dim_names(name: str, elem: ET.Element) -> list[str]:
    """Expand an SVD dim placeholder (%s) in a register name.

    Returns the concrete names ("JOFR1".."JOFR4") plus the bare family form
    ("JOFR") so datasheet-style references resolve too. Names without %s pass
    through unchanged.
    """
    if _PLACEHOLDER not in name:
        return [name]
    indices: list[str] = []
    dim_index = elem.findtext("dimIndex")
    if dim_index:
        s = dim_index.strip()
        if "-" in s and "," not in s:
            lo, hi = s.split("-", 1)
            try:
                indices = [str(i) for i in range(int(lo), int(hi) + 1)]
            except ValueError:
                indices = []
        else:
            indices = [p.strip() for p in s.split(",") if p.strip()]
    else:
        dim = elem.findtext("dim")
        try:
            indices = [str(i) for i in range(int(dim))] if dim else []
        except ValueError:
            indices = []
    base = name.replace("[%s]", "%s")
    names = [base.replace(_PLACEHOLDER, i) for i in indices]
    names.append(base.replace(_PLACEHOLDER, ""))
    return [n for n in names if n]


def _field_bit_width(field: ET.Element) -> Optional[int]:
    """Bit width of an SVD field: <bitWidth>, <msb>/<lsb>, or <bitRange>."""
    bw = _parse_svd_int(field.findtext("bitWidth"))
    if bw is not None:
        return bw
    msb = _parse_svd_int(field.findtext("msb"))
    lsb = _parse_svd_int(field.findtext("lsb"))
    if msb is not None and lsb is not None:
        return msb - lsb + 1
    m = _BIT_RANGE_RE.match((field.findtext("bitRange") or "").strip())
    if m:
        return int(m.group(1)) - int(m.group(2)) + 1
    return None


def _load_svd_index(svd_dir: str) -> dict:
    """Build a name-resolution + metadata index from SVD file(s).

    ``svd_dir`` may be a directory of .svd files or a single .svd file (the
    corpus sweep picks one SVD per reference manual deterministically).

    Returns::

        {"registers": {key: set(field_lower)},
         "enums": {(key, field_lower): {enum_name_lower: int}},
         "field_meta": {(key, field_lower): {"widths", "accesses", "mwv",
                                             "read_actions"}},
         "reg_meta": {key: {"sizes", "read_only", "read_actions"}},
         "peripheral_registers": {instance_or_family_lower: set(reg_lower)},
         "peripheral_names": set(instance_and_family_lower)}

    Each register is indexed under several keys -- bare name ("cr1"),
    instance-prefixed ("usart1_cr1"), and family-prefixed ("usart_cr1",
    trailing digits stripped) -- because datasheet-style constraint references
    use the family form while SVDs name instances.

    Resolution is deliberately LENIENT: keys shared by several peripherals
    (every peripheral has a "cr1") union their field sets, so a field that
    exists on any same-named register resolves. The metadata aggregation
    follows the same never-reject-a-real-name polarity: value-vs-width checks
    use the MAX width across contributors, and the read-only reject requires
    EVERY contributor to be read-only (``reg_meta[key]["read_only"]`` is one
    bool per contributing concrete register). w1c/readAction lint flags are
    informational and use any-contributor semantics.

    Access/modifiedWriteValues/readAction respect SVD inheritance
    (device -> peripheral -> register -> field).
    """
    registers: dict[str, set] = {}
    enums: dict[tuple, dict] = {}
    field_meta: dict[tuple, dict] = {}
    reg_meta: dict[str, dict] = {}
    peripheral_registers: dict[str, set] = {}
    peripheral_names: set = set()

    svd_arg = Path(svd_dir)
    if svd_arg.is_file():
        svd_files = [svd_arg]
    else:
        svd_files = sorted(svd_arg.glob("*.svd"))
    if not svd_files:
        raise FileNotFoundError(f"No .svd files found in {svd_dir}")

    for svd_path in svd_files:
        try:
            root = ET.parse(svd_path).getroot()
        except ET.ParseError as e:
            print(f"  [skip] {svd_path.name}: unparseable SVD ({e})", file=sys.stderr)
            continue
        device_size = _parse_svd_int(root.findtext("size"))
        device_access = (root.findtext("access") or "").strip() or None
        peripherals_elem = root.find("peripherals")
        if peripherals_elem is None:
            continue
        periph_elems = peripherals_elem.findall("peripheral")
        by_name = {
            (p.findtext("name") or "").strip(): p for p in periph_elems
        }
        for periph in periph_elems:
            pname = (periph.findtext("name") or "").strip()
            regs_parent = periph.find("registers")
            if regs_parent is None:
                # derivedFrom peripherals share the base peripheral's registers.
                base = by_name.get(periph.get("derivedFrom", ""))
                if base is not None:
                    regs_parent = base.find("registers")
            if not pname or regs_parent is None:
                continue
            plower = pname.lower()
            family = _family(plower)
            peripheral_names.add(plower)
            if family:
                peripheral_names.add(family)
            periph_size = _parse_svd_int(periph.findtext("size")) or device_size
            periph_access = (periph.findtext("access") or "").strip() or device_access
            # iter() (not findall()) also picks up registers nested in clusters.
            for reg in regs_parent.iter("register"):
                rname = (reg.findtext("name") or "").strip()
                if not rname:
                    continue
                reg_size = _parse_svd_int(reg.findtext("size")) or periph_size
                reg_access = (reg.findtext("access") or "").strip() or periph_access
                reg_mwv = (reg.findtext("modifiedWriteValues") or "").strip() or None
                reg_read_action = (reg.findtext("readAction") or "").strip() or None
                fields: set = set()
                field_enums: dict = {}
                field_infos: list = []
                fields_elem = reg.find("fields")
                if fields_elem is not None:
                    for field in fields_elem.findall("field"):
                        fname = (field.findtext("name") or "").strip()
                        if not fname:
                            continue
                        flower = fname.lower()
                        fields.add(flower)
                        evs = {}
                        for ev in field.iter("enumeratedValue"):
                            en = (ev.findtext("name") or "").strip().lower()
                            val = _parse_svd_int(ev.findtext("value"))
                            if en and val is not None:
                                evs[en] = val
                        if evs:
                            field_enums[flower] = evs
                        field_infos.append({
                            "name": flower,
                            "width": _field_bit_width(field),
                            "access": (field.findtext("access") or "").strip() or reg_access,
                            "mwv": ((field.findtext("modifiedWriteValues") or "").strip()
                                    or reg_mwv),
                            "read_action": ((field.findtext("readAction") or "").strip()
                                            or reg_read_action),
                        })
                # This concrete register's read-only verdict: declared
                # read-only, or every field is (fields inherit the register/
                # peripheral default, so unspecified fields inherit upward).
                read_only = (reg_access == "read-only") or (
                    bool(field_infos)
                    and all(fi["access"] == "read-only" for fi in field_infos)
                )
                for expanded in _expand_dim_names(rname, reg):
                    rlower = expanded.lower()
                    stripped = (rlower[len(plower) + 1:]
                                if rlower.startswith(f"{plower}_") else rlower)
                    for pkey in (plower, family):
                        if pkey:
                            peripheral_registers.setdefault(pkey, set()).update(
                                {rlower, stripped})
                    keys = {rlower, f"{plower}_{rlower}"}
                    if family:
                        keys.add(f"{family}_{rlower}")
                    for key in keys:
                        registers.setdefault(key, set()).update(fields)
                        for flower, evs in field_enums.items():
                            enums.setdefault((key, flower), {}).update(evs)
                        rm = reg_meta.setdefault(
                            key, {"sizes": set(), "read_only": [], "read_actions": set()})
                        if reg_size:
                            rm["sizes"].add(reg_size)
                        rm["read_only"].append(read_only)
                        if reg_read_action:
                            rm["read_actions"].add(reg_read_action)
                        for fi in field_infos:
                            fm = field_meta.setdefault(
                                (key, fi["name"]),
                                {"widths": set(), "accesses": set(), "mwv": set(),
                                 "read_actions": set()})
                            if fi["width"]:
                                fm["widths"].add(fi["width"])
                            if fi["access"]:
                                fm["accesses"].add(fi["access"])
                            if fi["mwv"]:
                                fm["mwv"].add(fi["mwv"].lower())
                            if fi["read_action"]:
                                fm["read_actions"].add(fi["read_action"])

    return {"registers": registers, "enums": enums, "field_meta": field_meta,
            "reg_meta": reg_meta, "peripheral_registers": peripheral_registers,
            "peripheral_names": peripheral_names}


def _resolve_register_key(name: str, svd_index: dict) -> Optional[str]:
    """Resolve a constraint's register name to an SVD index key, or None.

    Tries the name as-is, then with its leading (datasheet peripheral-family)
    prefix stripped -- "USART_CR1" matches the family key "usart_cr1" directly,
    while "RCC_APB1ENR" also matches via bare "apb1enr".
    """
    n = name.strip().lower()
    if not n:
        return None
    candidates = [n]
    if "_" in n:
        candidates.append(n.split("_", 1)[1])
    for key in candidates:
        if key in svd_index["registers"]:
            return key
    return None


def _lookup_enum_value(register: str, field: str, token: str, svd_index: dict) -> Optional[int]:
    """Look up an enumeratedValue NAME for (register, field), or None."""
    key = _resolve_register_key(register, svd_index)
    if key is None or not field:
        return None
    return svd_index["enums"].get((key, field.strip().lower()), {}).get(token.strip().lower())


def _repair_enum_states(
    constraint: RegisterAccessConstraint, svd_index: dict, repairs: list
) -> RegisterAccessConstraint:
    """B.4 repair: enum NAMES used as states -> values via SVD enumeratedValues.

    Handles the "enabled" drift case (bare enum name as required_state) and
    enum names inside "equals:" ("equals:output"). Only applies when every
    non-numeric token resolves to an enumeratedValue of that exact field --
    partial matches are left untouched for the lift to reject, because a
    half-repaired OR-list would silently change meaning.
    """
    c = constraint.model_copy(deep=True)
    for where, conds in (("preconditions", c.preconditions),
                         ("postconditions", c.postconditions)):
        for i, fs in enumerate(conds):
            rs = fs.required_state.strip()
            if rs in ("cleared", "set"):
                continue
            if rs.startswith("equals:"):
                parts = [p.strip() for p in rs[len("equals:"):].split("|")]
            else:
                parts = [rs]
            new_parts = []
            repaired = False
            resolvable = True
            for part in parts:
                try:
                    parse_value_token(part)
                    new_parts.append(part)
                    continue
                except ValueError:
                    pass
                val = _lookup_enum_value(fs.register_name, fs.field_name, part, svd_index)
                if val is None:
                    resolvable = False
                    break
                new_parts.append(str(val))
                repaired = True
            if resolvable and repaired:
                new_rs = "equals:" + "|".join(new_parts)
                repairs.append(
                    f"{where}[{i}].required_state: enum name(s) in "
                    f"{fs.required_state!r} repaired to {new_rs!r} via SVD "
                    "enumeratedValues"
                )
                fs.required_state = new_rs
    return c


def _constraint_name_refs(constraint) -> list[tuple[str, str, str]]:
    """Every (path, register, field) name reference of a v2 constraint.

    ``field == ""`` means only the register name is checked (whole-register
    references, sequence steps, delay triggers).
    """
    refs: list[tuple[str, str, str]] = []

    def _ref(path, field_ref):
        refs.append((path, field_ref.register,
                     "" if field_ref.whole_register else field_ref.field))

    kind = constraint.kind
    if kind in ("state_gate", "write_once"):
        refs.append(("target_register", constraint.target_register, ""))
        for j, f in enumerate(constraint.target_fields):
            refs.append((f"target_fields[{j}]", constraint.target_register, f))
        if kind == "state_gate":
            for name in ("preconditions", "postconditions"):
                for j, cond in enumerate(getattr(constraint, name)):
                    _ref(f"{name}[{j}]", cond)
    elif kind == "sequence":
        for j, step in enumerate(constraint.steps):
            refs.append((f"steps[{j}]", step.register, ""))
        if constraint.enables is not None:
            _ref("enables", constraint.enables)
    elif kind == "delay":
        refs.append(("after", constraint.after.register, ""))
        if constraint.before is not None:
            _ref("before", constraint.before)
    elif kind == "read_effect":
        refs.append(("read_register", constraint.read_register, ""))
        for j, effect in enumerate(constraint.effects):
            refs.append((f"effects[{j}]", constraint.read_register, effect.field))
    elif kind == "clock_gate":
        _ref("clock", constraint.clock)
    elif kind == "value_relation":
        for j, fr in enumerate(constraint.fields):
            _ref(f"fields[{j}]", fr)
    elif kind == "other":
        for j, fr in enumerate(constraint.involved):
            _ref(f"involved[{j}]", fr)
    return refs


def _svd_unresolved(constraint, svd_index: dict) -> list[dict]:
    """Names of a lifted constraint that do not resolve in the SVD (B.4 reject)."""
    out = []
    for path, register, field in _constraint_name_refs(constraint):
        key = _resolve_register_key(register, svd_index)
        if key is None:
            out.append({"field": f"{path}.register", "value": register,
                        "reason": "unresolvable_in_svd"})
        elif field and field.strip().lower() not in svd_index["registers"].get(key, set()):
            out.append({"field": f"{path}.field", "value": f"{register}.{field}",
                        "reason": "unresolvable_in_svd"})
    return out


def _v1_names_with_placeholder(c: RegisterAccessConstraint) -> list[str]:
    """v1 name fields that carry the %s filename-plumbing placeholder."""
    hits = []
    if _PLACEHOLDER in c.target_register:
        hits.append("target_register")
    for j, f in enumerate(c.target_fields):
        if _PLACEHOLDER in f:
            hits.append(f"target_fields[{j}]")
    for name in ("preconditions", "postconditions"):
        for j, fs in enumerate(getattr(c, name)):
            if _PLACEHOLDER in fs.register_name or _PLACEHOLDER in fs.field_name:
                hits.append(f"{name}[{j}]")
    return hits


# ---------------------------------------------------------------------------
# Stage-0 lint (roadmap step E, plan section 7.0)
# ---------------------------------------------------------------------------


def _v1_constraint_key(c: RegisterAccessConstraint) -> tuple:
    """Exact-dedup key: target register + operation + conditions + quote.

    Deliberately EXCLUDES target_fields (per-bit fan-out of one register-level
    note differs only there; enforcement is currently register-granular
    anyway) and severity/consequence (prose paraphrases of the same quote).
    """
    def conds(lst) -> tuple:
        return tuple(
            (fs.register_name.strip().lower(), fs.field_name.strip().lower(),
             fs.required_state.strip(),
             getattr(fs, "evidence_kind", None),
             getattr(fs, "action_operation", None))
            for fs in lst
        )
    return (c.target_register.strip().lower(),
            c.target_operation.strip().lower(),
            conds(c.preconditions), conds(c.postconditions),
            c.datasheet_text.strip())


def _v2_constraint_key(raw) -> tuple:
    """Exact-dedup key for a NATIVE v2 constraint (raw dict, pre-validation).

    Mirrors _v1_constraint_key's polarity: excludes target_fields (per-bit
    fan-out) and severity/consequence (prose paraphrases); everything else --
    kind, targets, conditions, steps, datasheet_text -- participates via a
    canonical JSON dump. Non-dict entries dedup by identity (never merged).
    """
    if not isinstance(raw, dict):
        return ("v2-nondict", id(raw))
    trimmed = {k: v for k, v in raw.items()
               if k not in ("target_fields", "severity", "consequence")}
    return ("v2", json.dumps(trimmed, sort_keys=True, default=str))


def _add_flag(flags: list, flag: str) -> None:
    if flag not in flags:
        flags.append(flag)


def _families_compatible(fa: str, fb: str) -> bool:
    """Whether two peripheral families plausibly denote the same block.

    Substring containment covers i2c/fmpi2c; the one-deletion rule covers
    usart/uart (shared manual chapters use both prefixes); the trailing-
    letter rule covers letter-suffixed instances (gpioa/gpiob are the same
    GPIO family, i.e. cross-INSTANCE, not cross-peripheral).
    """
    if not fa or not fb:
        return True  # can't tell -- err on "same"
    if fa == fb or fa in fb or fb in fa:
        return True
    short, long = sorted((fa, fb), key=len)
    if len(long) - len(short) == 1 and any(
            long[:i] + long[i + 1:] == short for i in range(len(long))):
        return True  # usart <-> uart
    if len(fa) > 3 and len(fb) > 3 and fa[:-1] == fb[:-1]:
        return True
    return False


def _same_register(a: str, b: str, svd_index: Optional[dict]) -> bool:
    """Whether two constraint register names plausibly denote one register."""
    la, lb = a.strip().lower(), b.strip().lower()
    if not la or not lb:
        return False
    if la == lb:
        return True
    # Prefix-qualified vs bare form of the same name ("GPIOA_LCKR" vs "LCKR").
    if la.endswith(f"_{lb}") or lb.endswith(f"_{la}"):
        return True
    if svd_index is not None:
        ka = _resolve_register_key(a, svd_index)
        kb = _resolve_register_key(b, svd_index)
        if ka is not None and ka == kb:
            return True
    return False


def _is_self_defeating_read_gate(gate, svd_index: Optional[dict]) -> bool:
    """Plan section 3: a read gate whose check performs the constrained read.

    op=read, at least one precondition, and EVERY precondition is a
    hardware-established condition on the target register itself -- checking it
    requires reading the target, which is exactly the constrained operation.
    Codegen rejects these; collection stops them earlier.
    """
    if gate.kind != "state_gate" or gate.target_operation != "read":
        return False
    if not gate.preconditions:
        return False
    return all(
        cond.established_by == "hardware"
        and _same_register(cond.register, gate.target_register, svd_index)
        for cond in gate.preconditions
    )


def _references_cross_peripheral(gate, file_peripheral: str,
                                 svd_index: Optional[dict]) -> bool:
    """Whether any condition register lives in a different peripheral.

    Name-prefix heuristic ("PWR_CR" on a usart file), refined by the SVD when
    available: a name that is actually a register of the target peripheral is
    never cross, and a prefix that names no known peripheral is not trusted
    (garbage names are handled by the unresolvable reject instead).
    """
    tfam = _family(file_peripheral)
    if not tfam:
        return False
    conditions = (list(getattr(gate, "preconditions", []) or [])
                  + list(getattr(gate, "postconditions", []) or []))
    for cond in conditions:
        c = cond.register.strip().lower()
        if "_" not in c:
            continue  # bare register name: assume the target's own peripheral
        prefix_fam = _family(c.split("_", 1)[0])
        if _families_compatible(prefix_fam, tfam):
            continue
        if svd_index is not None:
            target_regs = (
                svd_index["peripheral_registers"].get(file_peripheral.strip().lower(), set())
                | svd_index["peripheral_registers"].get(tfam, set()))
            if c in target_regs:
                continue  # literally a register of the target peripheral
            if prefix_fam not in svd_index["peripheral_names"]:
                # Prefix is not a peripheral (e.g. a field name misused as a
                # register); resolution rejects handle it.
                continue
        return True
    return False


def _condition_w1c(register: str, field: str, svd_index: dict) -> bool:
    """w1c-flag semantics: field modifiedWriteValues in the flag vocabularies,
    or the parent register is a status register with a readAction."""
    key = _resolve_register_key(register, svd_index)
    if key is None:
        return False
    if field:
        fm = svd_index["field_meta"].get((key, field.strip().lower()))
        if fm and (fm["mwv"] & _MWV_FLAG_SEMANTICS):
            return True
    rm = svd_index["reg_meta"].get(key)
    return bool(rm and rm["read_actions"])


def _has_read_action(register: str, field: str, svd_index: dict) -> bool:
    """Whether reading this register/field has SVD-declared side effects."""
    key = _resolve_register_key(register, svd_index)
    if key is None:
        return False
    if field:
        fm = svd_index["field_meta"].get((key, field.strip().lower()))
        if fm and fm["read_actions"]:
            return True
    rm = svd_index["reg_meta"].get(key)
    return bool(rm and rm["read_actions"])


def _strip_w1c_postconditions(constraint: RegisterAccessConstraint,
                              svd_index: dict, rejects: list,
                              lint_flags: list) -> RegisterAccessConstraint:
    """Stage-0 w1c reclassification (plan section 5.3, FP class 1).

    A postcondition "field X is cleared" on a w1c flag field merely restates
    the hardware's flag-clear behavior -- it is not a driver obligation.
    Dropped pre-lift with reject reason ``w1c_flag_semantics`` (more precise
    than the generic observed-state drop the lift would emit) and lint flag
    ``w1c_semantics``; the rest of the constraint survives.
    """
    kept, dropped = [], []
    for i, fs in enumerate(constraint.postconditions):
        if (fs.required_state.strip() == "cleared"
                and _condition_w1c(fs.register_name, fs.field_name, svd_index)):
            dropped.append((i, fs))
        else:
            kept.append(fs)
    if not dropped:
        return constraint
    for i, fs in dropped:
        rejects.append({
            "field": f"postconditions[{i}]",
            "value": f"{fs.register_name}.{fs.field_name} cleared",
            "reason": "w1c_flag_semantics",
        })
    _add_flag(lint_flags, "w1c_semantics")
    c = constraint.model_copy(deep=True)
    c.postconditions = kept
    return c


def _value_width_rejects(gate, svd_index: dict) -> list[dict]:
    """B.4 reject: equals values exceeding the SVD field/register bit width.

    Uses the MAX width across same-named contributors (lenient polarity --
    never reject a value some real field can hold); unknown widths are skipped.
    """
    out: list[dict] = []
    for name in ("preconditions", "postconditions"):
        for i, cond in enumerate(getattr(gate, name, []) or []):
            if cond.state != "equals":
                continue
            key = _resolve_register_key(cond.register, svd_index)
            if key is None:
                continue  # unresolvable is its own reject
            if cond.whole_register:
                meta = svd_index["reg_meta"].get(key)
                widths = meta["sizes"] if meta else set()
                what = cond.register
            else:
                meta = svd_index["field_meta"].get((key, cond.field.strip().lower()))
                widths = meta["widths"] if meta else set()
                what = f"{cond.register}.{cond.field}"
            if not widths:
                continue
            width = max(widths)
            too_big = [v for v in cond.values if v >= (1 << width)]
            if too_big:
                out.append({
                    "field": f"{name}[{i}].values",
                    "value": (f"{what}: {', '.join(hex(v) for v in too_big)} "
                              f"exceeds {width}-bit width"),
                    "reason": "value_exceeds_field_width",
                })
    return out


def _write_on_read_only_reject(gate, svd_index: dict) -> Optional[dict]:
    """B.4 reject: a write/modify constraint on an SVD read-only target is an
    FP by construction (the gated operation cannot happen).

    Lenient polarity: rejects only when EVERY SVD contributor is read-only
    (all named target fields read-only, or the whole register read-only).
    """
    if gate.kind != "state_gate" or gate.target_operation != "write":
        return None
    key = _resolve_register_key(gate.target_register, svd_index)
    if key is None:
        return None
    if gate.target_fields:
        metas = [svd_index["field_meta"].get((key, f.strip().lower()))
                 for f in gate.target_fields]
        read_only = bool(metas) and all(
            m is not None and m["accesses"] == {"read-only"} for m in metas)
        what = f"{gate.target_register}.{'/'.join(gate.target_fields)}"
    else:
        rm = svd_index["reg_meta"].get(key)
        read_only = bool(rm and rm["read_only"] and all(rm["read_only"]))
        what = gate.target_register
    if read_only:
        return {"field": "target_register", "value": what,
                "reason": "write_constraint_on_read_only"}
    return None


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def _lift_register_constraints(
    register_info: RegisterInfo,
    file_name: str,
    svd_index: Optional[dict],
    cross_instance_dups: Optional[set] = None,
) -> tuple[list[dict], list[dict], list[str], int]:
    """Lift one register's v1 constraints to v2, applying the stage-0 lint.

    Order per constraint: exact dedup (keep first) -> %s-placeholder reject ->
    SVD enum-name repair -> w1c postcondition reclassification -> B.6 lift ->
    per-gate rejects (SVD resolution, value-vs-width, write-on-read-only,
    self-defeating read gate) -> per-gate lint flags (w1c_semantics,
    read_side_effect, cross_peripheral).

    ``cross_instance_dups`` is the set of v1 indices this run found repeated
    verbatim in another instance of the same peripheral family (computed by
    the caller across the whole run; lint flag only, never dropped).

    Returns (v2_constraints_json, constraint_reports, register_lint_flags,
    duplicates_dropped). v2 constraint dicts carry the computed
    ``enforceability`` annotation. Rejects drop individual constraints only --
    the register (and peripheral) always survives.
    """
    lint_flags: list[str] = []
    if svd_index is None:
        lint_flags.append("svd_unchecked")
    placeholder_in_file = _PLACEHOLDER in file_name
    if placeholder_in_file:
        lint_flags.append("placeholder_in_name")

    file_peripheral, _ = split_peripheral_register(file_name)

    v2_json: list[dict] = []
    reports: list[dict] = []
    seen_keys: dict = {}
    duplicates_dropped = 0

    for idx, v1c in enumerate(register_info.access_constraints):
        repairs: list[str] = []
        rejects: list[dict] = []
        constraint_lint: list[str] = []
        kinds: list[str] = []
        enforceability: list[str] = []

        if cross_instance_dups and idx in cross_instance_dups:
            constraint_lint.append("duplicate_across_instances")

        # Exact dedup within this register's list: per-bit fan-out and
        # repeated notes produce byte-identical constraints; keep the first.
        key = _v1_constraint_key(v1c)
        kept_idx = seen_keys.get(key)
        if kept_idx is not None:
            duplicates_dropped += 1
            constraint_lint.append("exact_duplicate")
            reports.append({
                "v1_index": idx,
                "kinds": [],
                "enforceability": [],
                "repairs": [],
                "rejects": [],
                "lint_flags": constraint_lint,
                "duplicate_of": kept_idx,
            })
            continue
        seen_keys[key] = idx

        placeholder_fields = _v1_names_with_placeholder(v1c)
        if placeholder_in_file or placeholder_fields:
            # Never guess a %s expansion (safe choice): reject, flag, move on.
            constraint_lint.append("placeholder_in_name")
            for field in (["source_file"] if placeholder_in_file else []) + placeholder_fields:
                rejects.append({
                    "field": field,
                    "value": file_name if field == "source_file" else _PLACEHOLDER,
                    "reason": "placeholder_in_name",
                })
        else:
            c = v1c
            if svd_index is not None:
                c = _repair_enum_states(c, svd_index, repairs)
                c = _strip_w1c_postconditions(c, svd_index, rejects, constraint_lint)
            result = lift_v1_constraint(
                c, register_info.datasheet_register_abbreviation)
            repairs.extend(result.repairs)
            rejects.extend(r.model_dump() for r in result.rejects)

            if not v1c.preconditions and not v1c.postconditions:
                # Lifts fine but gates nothing; flag it (v1's 729 empty
                # constraints -- the discovery queue that motivated `other`).
                constraint_lint.append("vacuous_no_conditions")

            for gate in result.constraints:
                gate_rejects: list[dict] = []
                if svd_index is not None:
                    unresolved = _svd_unresolved(gate, svd_index)
                    if unresolved:
                        rejects.extend(unresolved)
                        continue
                    gate_rejects.extend(_value_width_rejects(gate, svd_index))
                    ro = _write_on_read_only_reject(gate, svd_index)
                    if ro is not None:
                        gate_rejects.append(ro)
                if _is_self_defeating_read_gate(gate, svd_index):
                    gate_rejects.append({
                        "field": "target_operation",
                        "value": gate.target_operation,
                        "reason": "self_defeating_read_gate",
                    })
                if gate_rejects:
                    rejects.extend(gate_rejects)
                    continue

                conditions = (list(getattr(gate, "preconditions", []) or [])
                              + list(getattr(gate, "postconditions", []) or []))
                if svd_index is not None:
                    if any(_condition_w1c(cd.register, cd.field, svd_index)
                           for cd in conditions):
                        _add_flag(constraint_lint, "w1c_semantics")
                    if getattr(gate, "target_operation", None) == "read" and (
                            _has_read_action(gate.target_register, "", svd_index)
                            or any(_has_read_action(cd.register, cd.field, svd_index)
                                   for cd in conditions)):
                        _add_flag(constraint_lint, "read_side_effect")
                if _references_cross_peripheral(gate, file_peripheral, svd_index):
                    _add_flag(constraint_lint, "cross_peripheral")

                enforced = derive_enforceability(gate)
                gate_json = gate.model_dump(mode="json")
                gate_json["enforceability"] = enforced
                v2_json.append(gate_json)
                kinds.append(gate.kind)
                enforceability.append(enforced)

        reports.append({
            "v1_index": idx,
            "kinds": kinds,
            "enforceability": enforceability,
            "repairs": repairs,
            "rejects": rejects,
            "lint_flags": constraint_lint,
        })

    return v2_json, reports, lint_flags, duplicates_dropped


def _lint_native_v2_constraints(
    register_info: RegisterInfo,
    raw_v2: list,
    file_name: str,
    svd_index: Optional[dict],
    cross_instance_dups: Optional[set] = None,
) -> tuple[list[dict], list[dict], list[str], int]:
    """Stage-0 lint for NATIVE grammar-v2 constraints (no lift).

    Same contract as _lift_register_constraints -- returns
    (v2_constraints_json, constraint_reports, register_lint_flags,
    duplicates_dropped) -- but the input is the file's raw
    ``access_constraints_v2`` list. Order per constraint: exact dedup (keep
    first) -> per-constraint pydantic validation (reason
    ``invalid_v2_constraint``; siblings survive) -> %s-placeholder reject ->
    target_register normalization -> w1c postcondition reclassification ->
    "any" expansion -> per-gate rejects (SVD resolution, value-vs-width,
    write-on-read-only, self-defeating read gate) -> lint flags
    (w1c_semantics, read_side_effect, cross_peripheral, vacuous_no_conditions)
    -> computed ``enforceability``.
    """
    lint_flags: list[str] = []
    if svd_index is None:
        lint_flags.append("svd_unchecked")
    placeholder_in_file = _PLACEHOLDER in file_name
    if placeholder_in_file:
        lint_flags.append("placeholder_in_name")

    file_peripheral, _ = split_peripheral_register(file_name)
    authoritative = register_info.datasheet_register_abbreviation

    v2_json: list[dict] = []
    reports: list[dict] = []
    seen_keys: dict = {}
    duplicates_dropped = 0

    for idx, raw in enumerate(raw_v2):
        repairs: list[str] = []
        rejects: list[dict] = []
        constraint_lint: list[str] = []
        kinds: list[str] = []
        enforceability: list[str] = []

        if cross_instance_dups and idx in cross_instance_dups:
            constraint_lint.append("duplicate_across_instances")

        key = _v2_constraint_key(raw)
        kept_idx = seen_keys.get(key)
        if kept_idx is not None:
            duplicates_dropped += 1
            constraint_lint.append("exact_duplicate")
            reports.append({
                "v2_index": idx,
                "kinds": [],
                "enforceability": [],
                "repairs": [],
                "rejects": [],
                "lint_flags": constraint_lint,
                "duplicate_of": kept_idx,
            })
            continue
        seen_keys[key] = idx

        constraint = None
        try:
            constraint = _CONSTRAINT_V2_ADAPTER.validate_python(raw)
        except ValidationError as e:
            errors = e.errors()
            first = errors[0] if errors else {}
            loc = ".".join(str(p) for p in first.get("loc", ())) or "constraint"
            rejects.append({
                "field": loc,
                "value": str(first.get("msg", "invalid"))[:200],
                "reason": "invalid_v2_constraint",
            })

        if constraint is not None:
            placeholder_fields = [
                path for path, reg, field in _constraint_name_refs(constraint)
                if _PLACEHOLDER in reg or _PLACEHOLDER in (field or "")
            ]
            if placeholder_in_file or placeholder_fields:
                # Never guess a %s expansion (safe choice): reject, flag, move on.
                constraint_lint.append("placeholder_in_name")
                for field in ((["source_file"] if placeholder_in_file else [])
                              + placeholder_fields):
                    rejects.append({
                        "field": field,
                        "value": file_name if field == "source_file" else _PLACEHOLDER,
                        "reason": "placeholder_in_name",
                    })
                constraint = None

        if constraint is not None:
            # target_register consistency (the deliberately-redundant check):
            # the containing register file is authoritative.
            if (constraint.kind in ("state_gate", "write_once")
                    and constraint.target_register != authoritative):
                repairs.append(
                    f"target_register normalized from "
                    f"{constraint.target_register!r} to {authoritative!r} "
                    "(containing register is authoritative)"
                )
                constraint = constraint.model_copy(
                    update={"target_register": authoritative})

            # w1c reclassification (plan section 5.3, FP class 1): a (software)
            # postcondition "cleared" on a w1c flag field restates hardware
            # flag-acknowledge semantics; drop the element, keep the gate.
            if (svd_index is not None and constraint.kind == "state_gate"
                    and constraint.postconditions):
                kept = []
                for i, pc in enumerate(constraint.postconditions):
                    if (pc.state == "cleared" and not pc.whole_register
                            and _condition_w1c(pc.register, pc.field, svd_index)):
                        rejects.append({
                            "field": f"postconditions[{i}]",
                            "value": f"{pc.register}.{pc.field} cleared",
                            "reason": "w1c_flag_semantics",
                        })
                        _add_flag(constraint_lint, "w1c_semantics")
                    else:
                        kept.append(pc)
                if len(kept) != len(constraint.postconditions):
                    constraint = constraint.model_copy(
                        update={"postconditions": kept})

            if (constraint.kind == "state_gate"
                    and not constraint.preconditions
                    and not constraint.postconditions):
                constraint_lint.append("vacuous_no_conditions")

            # "any" legal at extraction; EXPANDED to the two bus operations here
            # (B.2.1), matching the lifted path's deterministic repair. modify()
            # is NOT a gate here: it is derived as read+write in the emitter.
            if (constraint.kind == "state_gate"
                    and constraint.target_operation == "any"):
                repairs.append(
                    "target_operation 'any' expanded to per-operation gates: "
                    "read, write"
                )
                gates = [
                    constraint.model_copy(deep=True,
                                          update={"target_operation": op})
                    for op in ("read", "write")
                ]
            else:
                gates = [constraint]

            for gate in gates:
                gate_rejects: list[dict] = []
                if svd_index is not None:
                    unresolved = _svd_unresolved(gate, svd_index)
                    if unresolved:
                        rejects.extend(unresolved)
                        continue
                    gate_rejects.extend(_value_width_rejects(gate, svd_index))
                    ro = _write_on_read_only_reject(gate, svd_index)
                    if ro is not None:
                        gate_rejects.append(ro)
                if _is_self_defeating_read_gate(gate, svd_index):
                    gate_rejects.append({
                        "field": "target_operation",
                        "value": gate.target_operation,
                        "reason": "self_defeating_read_gate",
                    })
                if gate_rejects:
                    rejects.extend(gate_rejects)
                    continue

                conditions = (list(getattr(gate, "preconditions", []) or [])
                              + list(getattr(gate, "postconditions", []) or []))
                if svd_index is not None:
                    if any(_condition_w1c(cd.register, cd.field, svd_index)
                           for cd in conditions):
                        _add_flag(constraint_lint, "w1c_semantics")
                    if getattr(gate, "target_operation", None) == "read" and (
                            _has_read_action(gate.target_register, "", svd_index)
                            or any(_has_read_action(cd.register, cd.field, svd_index)
                                   for cd in conditions)):
                        _add_flag(constraint_lint, "read_side_effect")
                if _references_cross_peripheral(gate, file_peripheral, svd_index):
                    _add_flag(constraint_lint, "cross_peripheral")

                enforced = derive_enforceability(gate)
                gate_json = gate.model_dump(mode="json")
                gate_json["enforceability"] = enforced
                v2_json.append(gate_json)
                kinds.append(gate.kind)
                enforceability.append(enforced)

        reports.append({
            "v2_index": idx,
            "kinds": kinds,
            "enforceability": enforceability,
            "repairs": repairs,
            "rejects": rejects,
            "lint_flags": constraint_lint,
        })

    return v2_json, reports, lint_flags, duplicates_dropped


def collect_constraints(
    run_dir: str,
    output_dir: Optional[str] = None,
    include_empty: bool = False,
    svd_dir: Optional[str] = None,
) -> list[dict]:
    """Collect access constraints from a generator-output run directory.

    Scans ``run_dir`` for register files named ``{peripheral}_{register}``,
    reads each register's ``access_constraints``, and -- for every register that
    carries at least one constraint (unless ``include_empty`` is set) -- writes a
    constraints file in the ``RegisterInfo`` schema consumed by
    ``rust_codegen.py``, augmented with the lifted grammar-v2 constraints
    (``access_constraints_v2``) and per-constraint ``constraint_reports``.
    Also writes a ``manifest.json`` with per-constraint kind/enforceability/
    repair/reject details and run-level other-rate and reject-rate metrics.

    Args:
        run_dir: Path to a run directory, e.g. ``agent_output/stm/rm0041/24``.
        output_dir: Where to write the per-register constraints JSON files.
            Defaults to ``applications/pac_codegen/constraints/collected/<device>_<run>``
            derived from the run directory.
        include_empty: If True, also forward registers whose
            ``access_constraints`` list is empty. Default False (constrained
            registers only).
        svd_dir: Optional directory of .svd files (or one .svd file). When
            given, register/field names in lifted constraints are resolved
            against the SVDs (unresolvable -> per-constraint reject),
            enum-name states are repaired to values, and the SVD-metadata
            lint runs (value-vs-width, read-only targets, w1c/readAction).
            When absent, registers get the lint flag ``svd_unchecked``.

    Returns:
        A list of summary dicts, one per collected register, each with keys
        ``peripheral``, ``register``, ``num_constraints``,
        ``num_constraints_v2``, and ``output_path``.
    """
    run_path = Path(run_dir)
    if not run_path.is_dir():
        raise NotADirectoryError(f"Run directory not found: {run_path}")

    svd_index = _load_svd_index(svd_dir) if svd_dir else None

    if output_dir is not None:
        out_path = Path(output_dir)
    else:
        # e.g. agent_output/stm/rm0041/24 -> constraints/collected/rm0041_24
        device = run_path.parent.name
        run = run_path.name
        out_path = (
            _APP_DIR / "constraints" / "collected" / f"{device}_{run}"
        )

    out_path.mkdir(parents=True, exist_ok=True)

    # Phase 1: load every register output. Loading everything first lets the
    # cross-instance duplicate lint see the whole run before per-register
    # processing (a run is a few hundred small JSON files -- cheap).
    loaded: list[tuple[str, RegisterInfo, list, bool]] = []
    for entry in sorted(run_path.iterdir()):
        if entry.name in _SKIP_NAMES:
            continue
        if entry.is_dir():
            # Sub-directories such as info/ or coverage_improver/ are not
            # register outputs; skip them.
            continue
        loaded_entry = _load_register_info(entry)
        if loaded_entry is None:
            continue
        register_info, raw_v2, native_v2 = loaded_entry
        loaded.append((entry.name, register_info, raw_v2, native_v2))

    # Cross-instance duplicate lint: the same constraint repeated verbatim
    # across a peripheral family's instances (usart1_brr vs usart2_brr). The
    # rows stay separate (step H emits per-instance paths); they only get the
    # lint flag ``duplicate_across_instances``. Native-v2 registers
    # participate with their own key shape (never colliding with v1 keys).
    entry_keys: dict[str, list] = {}
    group_files: dict[tuple, set] = {}
    for name, register_info, raw_v2, native_v2 in loaded:
        peripheral, register = split_peripheral_register(name)
        fam = _family(peripheral)
        if native_v2:
            keys = [(fam, register, _v2_constraint_key(c)) for c in raw_v2]
        else:
            keys = [(fam, register, _v1_constraint_key(c))
                    for c in register_info.access_constraints]
        entry_keys[name] = keys
        for k in keys:
            group_files.setdefault(k, set()).add(name)
    cross_instance: dict[str, set] = {}
    for name, keys in entry_keys.items():
        for idx, k in enumerate(keys):
            if len(group_files[k]) > 1:
                cross_instance.setdefault(name, set()).add(idx)

    results: list[dict] = []
    manifest_registers: list[dict] = []
    totals = {
        "constraints_v1": 0,          # raw v1 count of LIFTED registers (incl. duplicates)
        "constraints_deduped": 0,     # exact duplicates dropped (keep-first, both sources)
        "constraints_v1_unique": 0,   # v1 minus duplicates
        "constraints_native_v2": 0,   # raw native-v2 count (incl. duplicates)
        "constraints_native_v2_unique": 0,   # native minus duplicates
        "constraints_v2": 0,
        "constraints_rejected": 0,    # unique source constraints with NO v2 output
        "reject_entries": 0,          # all structured reject entries (incl. dropped conditions)
        "repair_count": 0,
    }
    # Run-level counts of the per-register constraint source (task shape:
    # manifest records "native_v2" vs "lifted_v1" per register + counts).
    source_counts = {"native_v2": 0, "lifted_v1": 0}
    kind_counts: dict = {}
    enforceability_counts: dict = {}
    reject_reasons: dict = {}
    constraint_lint_counts: dict = {}
    register_lint_counts: dict = {}

    # Phase 2: lift (v1) or lint natively (v2) + write each register.
    for entry_name, register_info, raw_v2, native_v2 in loaded:
        num_constraints = (len(raw_v2) if native_v2
                           else len(register_info.access_constraints))
        if num_constraints == 0 and not include_empty:
            continue

        peripheral, register = split_peripheral_register(entry_name)

        if native_v2:
            v2_json, reports, lint_flags, dups_dropped = _lint_native_v2_constraints(
                register_info, raw_v2, entry_name, svd_index,
                cross_instance.get(entry_name))
        else:
            v2_json, reports, lint_flags, dups_dropped = _lift_register_constraints(
                register_info, entry_name, svd_index,
                cross_instance.get(entry_name))
        constraint_source = "native_v2" if native_v2 else "lifted_v1"
        source_counts[constraint_source] += 1

        # Structured reject entries, collected per register (task shape:
        # {file, constraint_index, field, reason}).
        register_rejects = [
            {"file": entry_name,
             "constraint_index": rep.get("v1_index", rep.get("v2_index")),
             **rej}
            for rep in reports for rej in rep["rejects"]
        ]

        # Write out in the RegisterInfo schema rust_codegen.py consumes (v1
        # key untouched -- extra keys are ignored by the pydantic parse), plus
        # the v2 constraints and their repair/reject reports. For native-v2
        # registers this REPLACES the raw generator constraints with their
        # linted, enforceability-annotated forms.
        data = register_info.model_dump(mode="json")
        data["access_constraints_v2"] = v2_json
        data["constraint_reports"] = reports
        out_file = out_path / f"{entry_name}.json"
        out_file.write_text(json.dumps(data, indent=2))

        if native_v2:
            totals["constraints_native_v2"] += num_constraints
            totals["constraints_native_v2_unique"] += num_constraints - dups_dropped
        else:
            totals["constraints_v1"] += num_constraints
            totals["constraints_v1_unique"] += num_constraints - dups_dropped
        totals["constraints_deduped"] += dups_dropped
        totals["constraints_v2"] += len(v2_json)
        totals["constraints_rejected"] += sum(
            1 for rep in reports
            if not rep["kinds"] and "exact_duplicate" not in rep["lint_flags"])
        totals["reject_entries"] += len(register_rejects)
        totals["repair_count"] += sum(len(rep["repairs"]) for rep in reports)
        for rep in reports:
            for kind in rep["kinds"]:
                kind_counts[kind] = kind_counts.get(kind, 0) + 1
            for enforced in rep["enforceability"]:
                enforceability_counts[enforced] = enforceability_counts.get(enforced, 0) + 1
            for rej in rep["rejects"]:
                reject_reasons[rej["reason"]] = reject_reasons.get(rej["reason"], 0) + 1
            for flag in rep["lint_flags"]:
                constraint_lint_counts[flag] = constraint_lint_counts.get(flag, 0) + 1
        for flag in lint_flags:
            register_lint_counts[flag] = register_lint_counts.get(flag, 0) + 1

        manifest_registers.append({
            "file": entry_name,
            "peripheral": peripheral,
            "register": register,
            "constraint_source": constraint_source,
            "num_constraints_v1": len(register_info.access_constraints),
            "num_source_constraints": num_constraints,
            "num_constraints_v2": len(v2_json),
            "duplicates_dropped": dups_dropped,
            "lint_flags": lint_flags,
            "constraints": reports,
            "rejects": register_rejects,
            "output_path": str(out_file),
        })

        results.append(
            {
                "peripheral": peripheral,
                "register": register,
                "constraint_source": constraint_source,
                "num_constraints": num_constraints,
                "num_constraints_v2": len(v2_json),
                "output_path": str(out_file),
            }
        )

    # Run-level grammar-coverage metrics (plan section 4): the other-rate is
    # the fraction of v2 constraints needing the escape valve (a spike is a
    # prompt regression; the lift emits only state_gate, so lifted runs score
    # 0 -- native-v2 extraction is where the metric is live); the reject-rate
    # is the fraction of UNIQUE (post-dedup) source constraints (lifted v1 +
    # native v2) the grammar/lint could not hold.
    source_total = totals["constraints_v1"] + totals["constraints_native_v2"]
    unique_total = (totals["constraints_v1_unique"]
                    + totals["constraints_native_v2_unique"])
    v2_total = totals["constraints_v2"]
    other_count = kind_counts.get("other", 0)
    manifest = {
        "run_dir": str(run_path),
        "svd_dir": svd_dir,
        "grammar_version": 2,
        "summary": {
            **totals,
            "registers_collected": len(results),
            "constraint_sources": source_counts,
            "dedup_rate": (totals["constraints_deduped"] / source_total) if source_total else 0.0,
            "reject_rate": (totals["constraints_rejected"] / unique_total) if unique_total else 0.0,
            "other_count": other_count,
            "other_rate": (other_count / v2_total) if v2_total else 0.0,
            "kind_counts": kind_counts,
            "enforceability_counts": enforceability_counts,
            "reject_reasons": reject_reasons,
            "constraint_lint_flag_counts": constraint_lint_counts,
            "register_lint_flag_counts": register_lint_counts,
        },
        "registers": manifest_registers,
    }
    (out_path / "manifest.json").write_text(json.dumps(manifest, indent=2))

    return results


def main(argv: list[str] | None = None) -> None:
    """CLI entry point; ``argv`` lets drivers (inject_from_run.py) call this
    in-process instead of shelling out. None = use sys.argv as before."""
    parser = argparse.ArgumentParser(
        description=(
            "Collect access_constraints from a generator-output run directory, "
            "lift them to grammar v2, and forward them as RegisterInfo JSON "
            "files (plus manifest.json) for rust_codegen.py."
        )
    )
    parser.add_argument(
        "run_dir",
        help="Run directory, e.g. agent_output/stm/rm0041/24",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Where to write per-register constraints JSON. "
            "Default: applications/pac_codegen/constraints/collected/<device>_<run>"
        ),
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="Also forward registers with no access_constraints.",
    )
    parser.add_argument(
        "--svd-dir",
        default=None,
        help=(
            "Optional directory of .svd files (or a single .svd file) for "
            "name resolution, enum-name repair, and the SVD-metadata lint "
            "(value-vs-width, read-only targets, w1c/readAction). Without "
            "it, v2 constraints carry the 'svd_unchecked' lint flag."
        ),
    )
    args = parser.parse_args(argv)

    results = collect_constraints(
        args.run_dir,
        output_dir=args.output_dir,
        include_empty=args.include_empty,
        svd_dir=args.svd_dir,
    )

    if not results:
        print(
            f"No constrained registers found in {args.run_dir}. "
            f"(Use --include-empty to forward all registers.)"
        )
        return

    total = sum(r["num_constraints"] for r in results)
    total_v2 = sum(r["num_constraints_v2"] for r in results)
    print(f"Collected {len(results)} register(s), {total} source constraint(s), "
          f"{total_v2} v2 constraint(s):")
    for r in results:
        print(
            f"  {r['peripheral']}_{r['register']}: "
            f"{r['num_constraints']} {r['constraint_source']} / "
            f"{r['num_constraints_v2']} v2 "
            f"-> {r['output_path']}"
        )
    out_dir = Path(results[0]["output_path"]).parent
    manifest = json.loads((out_dir / "manifest.json").read_text())
    summary = manifest["summary"]
    sources = summary["constraint_sources"]
    print(
        f"Constraint sources: {sources['native_v2']} native_v2 register(s), "
        f"{sources['lifted_v1']} lifted_v1 register(s)."
    )
    source_total = summary["constraints_v1"] + summary["constraints_native_v2"]
    unique_total = (summary["constraints_v1_unique"]
                    + summary["constraints_native_v2_unique"])
    print(
        f"Stage-0 lint: {summary['constraints_deduped']} exact duplicate(s) dropped "
        f"({summary['dedup_rate']:.1%} of {source_total} source), "
        f"{unique_total} unique."
    )
    print(
        f"Grammar coverage: reject-rate {summary['reject_rate']:.1%} "
        f"({summary['constraints_rejected']}/{unique_total} unique rejected), "
        f"other-rate {summary['other_rate']:.1%} "
        f"({summary['other_count']}/{summary['constraints_v2']} v2)."
    )
    if summary["reject_reasons"]:
        top = sorted(summary["reject_reasons"].items(), key=lambda kv: -kv[1])
        print("Reject reasons: " + ", ".join(f"{r}={n}" for r, n in top))
    if summary["constraint_lint_flag_counts"]:
        top = sorted(summary["constraint_lint_flag_counts"].items(), key=lambda kv: -kv[1])
        print("Lint flags: " + ", ".join(f"{f}={n}" for f, n in top))
    print(f"Manifest: {out_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
