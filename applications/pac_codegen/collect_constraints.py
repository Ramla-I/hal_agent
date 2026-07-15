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

Each per-register output JSON keeps the v1 ``access_constraints`` key untouched
(codegen still consumes v1 until roadmap step B/H) and gains:

- ``access_constraints_v2``: the lifted v2 constraints, each annotated with its
  computed ``enforceability`` (defs.derive_enforceability -- never LLM-emitted);
- ``constraint_reports``: per-v1-constraint repair/reject/lint details.

A ``manifest.json`` is written next to the per-register files with per-register
and per-constraint entries (kind, enforceability, repairs, rejects, lint flags)
plus run-level grammar-coverage metrics: the ``other``-rate (fraction of v2
constraints that needed the escape-valve kind) and the reject-rate.

SVD name resolution is OPTIONAL (``--svd-dir``): when given, every
register/field name in a lifted constraint is resolved against the SVDs
(unresolvable names are rejected per B.4); when absent, resolution is skipped
and registers carry the lint flag ``svd_unchecked`` -- SVDs are never a hard
requirement, so corpus runs work without them.

NOTE ON SCOPE
-------------
This bridge collects, lifts, and lints; it does NOT judge whether a constraint
is faithful to the datasheet. Semantic validation is the Constraint Validator
(roadmap step G); the full stage-0 lint over the 30-RM corpus is step E.

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
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

# Add the repo root to sys.path so we can import the shared defs.py.
# This file lives at applications/pac_codegen/collect_constraints.py, so the
# repo root is three levels up.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# This application's own directory (applications/pac_codegen/).
_APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT))

from defs import (  # noqa: E402  (path setup must precede import)
    RegisterAccessConstraint,
    RegisterInfo,
    derive_enforceability,
    lift_v1_constraint,
    parse_value_token,
)


# Files that may appear inside a run directory but are not register outputs.
_SKIP_NAMES = {".DS_Store"}
_SKIP_DIR_NAMES = {"info", "coverage_improver"}

# The derivedFrom plumbing bug in the run-dir writer leaves svd2rust dim
# placeholders in file names (e.g. ``tim3_ccr%s``). The bug's FIX belongs in
# core/ (roadmap step E); here we only refuse to guess an expansion.
_PLACEHOLDER = "%s"


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


def _load_register_info(path: Path) -> Optional[RegisterInfo]:
    """Load and validate a single register output file as RegisterInfo.

    Returns None (with a warning) if the file is not a parseable RegisterInfo
    JSON, so a single malformed file does not abort the whole run.
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

    try:
        return RegisterInfo(**data)
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


def _load_svd_index(svd_dir: str) -> dict:
    """Build a name-resolution index from every .svd file under ``svd_dir``.

    Returns ``{"registers": {key: set(field_lower)}, "enums": {(key, field_lower):
    {enum_name_lower: int}}}``. Each register is indexed under several keys --
    bare name ("cr1"), instance-prefixed ("usart1_cr1"), and family-prefixed
    ("usart_cr1", trailing digits stripped) -- because datasheet-style
    constraint references use the family form while SVDs name instances.

    Resolution is deliberately LENIENT: keys shared by several peripherals
    (every peripheral has a "cr1") union their field sets, so a field that
    exists on any same-named register resolves. That is the right polarity for
    a collection gate -- it must never reject a real name; the precise
    per-peripheral lint is roadmap step E.
    """
    registers: dict[str, set] = {}
    enums: dict[tuple, dict] = {}

    svd_files = sorted(Path(svd_dir).glob("*.svd"))
    if not svd_files:
        raise FileNotFoundError(f"No .svd files found in {svd_dir}")

    for svd_path in svd_files:
        try:
            root = ET.parse(svd_path).getroot()
        except ET.ParseError as e:
            print(f"  [skip] {svd_path.name}: unparseable SVD ({e})", file=sys.stderr)
            continue
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
            family = plower.rstrip("0123456789")
            # iter() (not findall()) also picks up registers nested in clusters.
            for reg in regs_parent.iter("register"):
                rname = (reg.findtext("name") or "").strip()
                if not rname:
                    continue
                fields: set = set()
                field_enums: dict = {}
                fields_elem = reg.find("fields")
                if fields_elem is not None:
                    for field in fields_elem.findall("field"):
                        fname = (field.findtext("name") or "").strip()
                        if not fname:
                            continue
                        fields.add(fname.lower())
                        evs = {}
                        for ev in field.iter("enumeratedValue"):
                            en = (ev.findtext("name") or "").strip().lower()
                            val = _parse_svd_int(ev.findtext("value"))
                            if en and val is not None:
                                evs[en] = val
                        if evs:
                            field_enums[fname.lower()] = evs
                for expanded in _expand_dim_names(rname, reg):
                    rlower = expanded.lower()
                    keys = {rlower, f"{plower}_{rlower}"}
                    if family:
                        keys.add(f"{family}_{rlower}")
                    for key in keys:
                        registers.setdefault(key, set()).update(fields)
                        for flower, evs in field_enums.items():
                            enums.setdefault((key, flower), {}).update(evs)

    return {"registers": registers, "enums": enums}


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
# Collection
# ---------------------------------------------------------------------------


def _lift_register_constraints(
    register_info: RegisterInfo,
    file_name: str,
    svd_index: Optional[dict],
) -> tuple[list[dict], list[dict], list[str]]:
    """Lift one register's v1 constraints to v2, applying repair/reject rules.

    Returns (v2_constraints_json, constraint_reports, register_lint_flags).
    v2 constraint dicts carry the computed ``enforceability`` annotation.
    Rejects drop individual constraints only -- the register (and peripheral)
    always survives.
    """
    lint_flags: list[str] = []
    if svd_index is None:
        lint_flags.append("svd_unchecked")
    placeholder_in_file = _PLACEHOLDER in file_name
    if placeholder_in_file:
        lint_flags.append("placeholder_in_name")

    v2_json: list[dict] = []
    reports: list[dict] = []

    for idx, v1c in enumerate(register_info.access_constraints):
        repairs: list[str] = []
        rejects: list[dict] = []
        constraint_lint: list[str] = []
        kinds: list[str] = []
        enforceability: list[str] = []

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
            result = lift_v1_constraint(
                c, register_info.datasheet_register_abbreviation)
            repairs.extend(result.repairs)
            rejects.extend(r.model_dump() for r in result.rejects)

            if not v1c.preconditions and not v1c.postconditions:
                # Lifts fine but gates nothing; flag it (v1's 729 empty
                # constraints -- the discovery queue that motivated `other`).
                constraint_lint.append("vacuous_no_conditions")

            for gate in result.constraints:
                if svd_index is not None:
                    unresolved = _svd_unresolved(gate, svd_index)
                    if unresolved:
                        rejects.extend(unresolved)
                        continue
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

    return v2_json, reports, lint_flags


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
        svd_dir: Optional directory of .svd files. When given, register/field
            names in lifted constraints are resolved against the SVDs
            (unresolvable -> per-constraint reject) and enum-name states are
            repaired to values. When absent, registers get the lint flag
            ``svd_unchecked``.

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

    results: list[dict] = []
    manifest_registers: list[dict] = []
    totals = {
        "constraints_v1": 0,
        "constraints_v2": 0,
        "constraints_rejected": 0,   # v1 constraints that produced NO v2 output
        "reject_entries": 0,         # all structured reject entries (incl. dropped conditions)
        "repair_count": 0,
    }
    kind_counts: dict = {}
    enforceability_counts: dict = {}

    for entry in sorted(run_path.iterdir()):
        if entry.name in _SKIP_NAMES:
            continue
        if entry.is_dir():
            # Sub-directories such as info/ or coverage_improver/ are not
            # register outputs; skip them.
            continue

        register_info = _load_register_info(entry)
        if register_info is None:
            continue

        num_constraints = len(register_info.access_constraints)
        if num_constraints == 0 and not include_empty:
            continue

        peripheral, register = split_peripheral_register(entry.name)

        v2_json, reports, lint_flags = _lift_register_constraints(
            register_info, entry.name, svd_index)

        # Structured reject entries, collected per register (task shape:
        # {file, constraint_index, field, reason}).
        register_rejects = [
            {"file": entry.name, "constraint_index": rep["v1_index"], **rej}
            for rep in reports for rej in rep["rejects"]
        ]

        # Write out in the RegisterInfo schema rust_codegen.py consumes (v1
        # key untouched -- extra keys are ignored by the pydantic parse), plus
        # the v2 constraints and their repair/reject reports.
        data = register_info.model_dump(mode="json")
        data["access_constraints_v2"] = v2_json
        data["constraint_reports"] = reports
        out_file = out_path / f"{entry.name}.json"
        out_file.write_text(json.dumps(data, indent=2))

        totals["constraints_v1"] += num_constraints
        totals["constraints_v2"] += len(v2_json)
        totals["constraints_rejected"] += sum(1 for rep in reports if not rep["kinds"])
        totals["reject_entries"] += len(register_rejects)
        totals["repair_count"] += sum(len(rep["repairs"]) for rep in reports)
        for rep in reports:
            for kind in rep["kinds"]:
                kind_counts[kind] = kind_counts.get(kind, 0) + 1
            for enforced in rep["enforceability"]:
                enforceability_counts[enforced] = enforceability_counts.get(enforced, 0) + 1

        manifest_registers.append({
            "file": entry.name,
            "peripheral": peripheral,
            "register": register,
            "num_constraints_v1": num_constraints,
            "num_constraints_v2": len(v2_json),
            "lint_flags": lint_flags,
            "constraints": reports,
            "rejects": register_rejects,
            "output_path": str(out_file),
        })

        results.append(
            {
                "peripheral": peripheral,
                "register": register,
                "num_constraints": num_constraints,
                "num_constraints_v2": len(v2_json),
                "output_path": str(out_file),
            }
        )

    # Run-level grammar-coverage metrics (plan section 4): the other-rate is
    # the fraction of v2 constraints needing the escape valve (a spike is a
    # prompt regression; today's lift emits only state_gate, so it is 0 until
    # native-v2 extraction lands); the reject-rate is the fraction of v1
    # constraints the grammar could not hold.
    v1_total = totals["constraints_v1"]
    v2_total = totals["constraints_v2"]
    other_count = kind_counts.get("other", 0)
    manifest = {
        "run_dir": str(run_path),
        "svd_dir": svd_dir,
        "grammar_version": 2,
        "summary": {
            **totals,
            "registers_collected": len(results),
            "reject_rate": (totals["constraints_rejected"] / v1_total) if v1_total else 0.0,
            "other_count": other_count,
            "other_rate": (other_count / v2_total) if v2_total else 0.0,
            "kind_counts": kind_counts,
            "enforceability_counts": enforceability_counts,
        },
        "registers": manifest_registers,
    }
    (out_path / "manifest.json").write_text(json.dumps(manifest, indent=2))

    return results


def main() -> None:
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
            "Optional directory of .svd files for name resolution and "
            "enum-name repair. Without it, v2 constraints carry the "
            "'svd_unchecked' lint flag."
        ),
    )
    args = parser.parse_args()

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
    print(f"Collected {len(results)} register(s), {total} v1 constraint(s), "
          f"{total_v2} v2 constraint(s):")
    for r in results:
        print(
            f"  {r['peripheral']}_{r['register']}: "
            f"{r['num_constraints']} v1 / {r['num_constraints_v2']} v2 "
            f"-> {r['output_path']}"
        )
    out_dir = Path(results[0]["output_path"]).parent
    manifest = json.loads((out_dir / "manifest.json").read_text())
    summary = manifest["summary"]
    print(
        f"Grammar coverage: reject-rate {summary['reject_rate']:.1%} "
        f"({summary['constraints_rejected']}/{summary['constraints_v1']} v1 rejected), "
        f"other-rate {summary['other_rate']:.1%} "
        f"({summary['other_count']}/{summary['constraints_v2']} v2). "
        f"Manifest: {out_dir / 'manifest.json'}"
    )


if __name__ == "__main__":
    main()
