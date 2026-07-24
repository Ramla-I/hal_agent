#!/usr/bin/env python3
"""Convert OLD (grammar-v1) generator output to grammar-v2, in bulk.

The pipeline is grammar-v2 only. This is the ONE tool that understands the
retired v1 access-constraint grammar: point it at an old generator run
directory (one JSON file per ``{peripheral}_{register}`` whose constraints live
in the v1 ``access_constraints`` list) and it writes a parallel directory whose
register files carry ``access_constraints_v2`` instead (``access_constraints``
dropped, ``schema_version: 2``). Everything else (``info/`` subdir, non-register
files) is copied through unchanged.

The v1 models (``FieldState``/``RegisterAccessConstraint``) and the mechanical
B.6 lift live HERE, nowhere else -- ``defs.py`` and the rest of the pipeline are
grammar-v2 only. Every v1 constraint becomes one or more v2 ``state_gate``s;
unliftable drift (unparseable states, unknown vocabulary) is reported per file,
never silently dropped.

Usage:
    python applications/pac_codegen/convert_v1_to_v2.py OLD_RUN_DIR OUT_DIR
    python applications/pac_codegen/convert_v1_to_v2.py OLD_RUN_DIR --in-place

A file already in v2 form (``schema_version == 2`` or a non-empty
``access_constraints_v2``) is copied through untouched, so re-running is safe.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict

# Repo root (three levels up: applications/pac_codegen/ -> repo).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# The v2 grammar the lift PRODUCES lives in defs.py; only v1 lives here.
from defs import (  # noqa: E402
    ConstraintV2,
    FieldCondition,
    StateGate,
    parse_value_token,
)


# ---------------------------------------------------------------------------
# Grammar v1 wire format (RETIRED — parsed only here, to lift to v2)
# ---------------------------------------------------------------------------

class FieldState(BaseModel):
    """A v1 field-state requirement (pre/post condition). extra="allow" retains
    PR-15 optional keys (``evidence_kind``, ``action_operation``) for the lift."""
    model_config = ConfigDict(extra="allow")

    register_name: str
    field_name: str
    required_state: str  # "cleared", "set", "equals:<value>"


class RegisterAccessConstraint(BaseModel):
    """A v1 register/field access constraint (the retired generator wire
    format). extra="allow" for the same lift-compatibility reason."""
    model_config = ConfigDict(extra="allow")

    target_register: str
    target_fields: list[str]           # empty = whole register
    target_operation: str              # "write", "read", "modify", "any", ...
    preconditions: list[FieldState]
    postconditions: list[FieldState]
    severity: str                      # "error", "warning"
    consequence: str
    datasheet_text: str


class V1RegisterInfo(BaseModel):
    """Just enough of a v1 register file to lift its constraints (extra keys —
    subfields, address, etc. — are preserved separately as the raw dict)."""
    model_config = ConfigDict(extra="allow")

    datasheet_register_abbreviation: str
    access_constraints: list[RegisterAccessConstraint] = []


# ---------------------------------------------------------------------------
# v1 -> v2 lift (mechanical, per the B.6 table)
# ---------------------------------------------------------------------------

class LiftReject(BaseModel):
    """Structured rejection produced by the lift (never an exception)."""
    field: str
    value: str
    reason: str


class LiftResult(BaseModel):
    """Outcome of lifting ONE v1 constraint (zero+ v2 constraints, structured
    rejects, and a repair log)."""
    constraints: list[ConstraintV2] = []
    rejects: list[LiftReject] = []
    repairs: list[str] = []


# v1 target_operation -> v2 per-operation expansion (B.6). The v2 target
# vocabulary is the two bus operations only: read and write. Datasheet
# "modify/change" means "write", so legacy "modify" lifts to "write";
# "any"/"read/write" expand to both bus operations.
_V1_OPERATION_LIFT = {
    "write": ["write"],
    "read": ["read"],
    "modify": ["write"],
    "any": ["read", "write"],
    "read/write": ["read", "write"],
    "read-write": ["read", "write"],
}

# v1 evidence_kind -> v2 established_by (B.6). v1 corpus files lack evidence_kind
# entirely -> default "hardware" (a bare condition is observed state).
_V1_EVIDENCE_LIFT = {
    None: "hardware",
    "observed_state": "hardware",
    "software_action": "software",
}


def _lift_required_state(required_state: str):
    """Parse a v1 required_state string into (state, values).

    "cleared"/"set" pass through; "equals:<v>" and "equals:A|B|C" parse each
    |-separated part. Raises ValueError on anything else (the caller turns that
    into a structured reject).
    """
    rs = required_state.strip()
    if rs == "cleared" or rs == "set":
        return rs, []
    if rs.startswith("equals:"):
        parts = [p.strip() for p in rs[len("equals:"):].split("|")]
        return "equals", [parse_value_token(p) for p in parts]
    raise ValueError(f"unparseable required_state {required_state!r}")


def _lift_field_state(fs: FieldState, where: str, rejects: list, repairs: list):
    """Lift one v1 FieldState to a v2 FieldCondition, or None (+ a LiftReject)."""
    try:
        state, values = _lift_required_state(fs.required_state)
    except ValueError:
        rejects.append(LiftReject(
            field=f"{where}.required_state",
            value=fs.required_state,
            reason="unparseable_required_state",
        ))
        return None

    evidence_kind = getattr(fs, "evidence_kind", None)
    if evidence_kind not in _V1_EVIDENCE_LIFT:
        rejects.append(LiftReject(
            field=f"{where}.evidence_kind",
            value=str(evidence_kind),
            reason="unknown_evidence_kind",
        ))
        return None
    established_by = _V1_EVIDENCE_LIFT[evidence_kind]

    action_operation = getattr(fs, "action_operation", None)
    if established_by == "software":
        if action_operation not in ("write", "modify"):
            rejects.append(LiftReject(
                field=f"{where}.action_operation",
                value=str(action_operation),
                reason="software_evidence_without_action_operation",
            ))
            return None
    elif action_operation is not None:
        repairs.append(
            f"{where}: dropped action_operation={action_operation!r} "
            "(only meaningful with software established_by)"
        )
        action_operation = None

    # v1 encodes whole-register conditions as field_name="" (the IWDG_KR unlock).
    whole_register = fs.field_name == ""
    if whole_register:
        repairs.append(f"{where}: empty field_name lifted to whole_register=true")

    return FieldCondition(
        register=fs.register_name,
        field=fs.field_name,
        whole_register=whole_register,
        state=state,
        values=values,
        established_by=established_by,
        action_operation=action_operation if established_by == "software" else None,
    )


def lift_v1_constraint(c: RegisterAccessConstraint, target_register: str) -> LiftResult:
    """Lift one v1 RegisterAccessConstraint to grammar-v2 StateGate(s) (B.6).

    Never raises for bad content -- judgment-requiring drift becomes structured
    LiftReject entries; deterministic drift is repaired and logged.
    """
    rejects: list = []
    repairs: list = []

    severity = c.severity
    if severity == "info":
        repairs.append('severity "info" repaired to "warning"')
        severity = "warning"
    elif severity not in ("error", "warning"):
        rejects.append(LiftReject(
            field="severity", value=str(c.severity), reason="unknown_severity"))
        return LiftResult(rejects=rejects, repairs=repairs)

    operations = _V1_OPERATION_LIFT.get(c.target_operation)
    if operations is None:
        rejects.append(LiftReject(
            field="target_operation", value=str(c.target_operation),
            reason="unknown_target_operation"))
        return LiftResult(rejects=rejects, repairs=repairs)
    if len(operations) > 1:
        repairs.append(
            f"target_operation {c.target_operation!r} expanded to "
            f"per-operation gates: {', '.join(operations)}"
        )

    if c.target_register != target_register:
        repairs.append(
            f"target_register normalized from {c.target_register!r} to "
            f"{target_register!r} (containing register is authoritative)"
        )

    # Preconditions: all-or-nothing (dropping one would silently weaken the gate).
    preconditions = []
    for i, fs in enumerate(c.preconditions):
        cond = _lift_field_state(fs, f"preconditions[{i}]", rejects, repairs)
        if cond is None:
            return LiftResult(rejects=rejects, repairs=repairs)
        preconditions.append(cond)

    # Postconditions: software-established only survive (observed-state ones are
    # unenforceable; dropped LOUDLY as a structured reject, gate survives).
    postconditions = []
    for i, fs in enumerate(c.postconditions):
        n_rejects_before = len(rejects)
        cond = _lift_field_state(fs, f"postconditions[{i}]", rejects, repairs)
        if cond is None:
            reason = rejects[-1].reason if len(rejects) > n_rejects_before else ""
            if reason == "unparseable_required_state":
                return LiftResult(rejects=rejects, repairs=repairs)
            continue
        if cond.established_by != "software":
            rejects.append(LiftReject(
                field=f"postconditions[{i}]",
                value=f"{fs.register_name}.{fs.field_name} {fs.required_state}",
                reason="observed_state_postcondition_unenforceable",
            ))
            continue
        postconditions.append(cond)

    constraints = [
        StateGate(
            target_register=target_register,
            target_fields=list(c.target_fields),
            target_operation=op,
            preconditions=[p.model_copy(deep=True) for p in preconditions],
            postconditions=[p.model_copy(deep=True) for p in postconditions],
            severity=severity,
            consequence=c.consequence,
            datasheet_text=c.datasheet_text,
        )
        for op in operations
    ]
    return LiftResult(constraints=constraints, rejects=rejects, repairs=repairs)


# ---------------------------------------------------------------------------
# Bulk conversion
# ---------------------------------------------------------------------------

def _is_v1_register_file(data: object) -> bool:
    """A v1 register file has the register abbreviation and a v1
    ``access_constraints`` list (possibly empty — empty registers are converted
    too, so the whole run dir ends up uniformly v2), and is NOT already v2."""
    if not isinstance(data, dict):
        return False
    if data.get("schema_version") == 2 or data.get("access_constraints_v2"):
        return False  # already v2
    return ("access_constraints" in data
            and "datasheet_register_abbreviation" in data)


def convert_register(data: dict) -> tuple[dict, list[str]]:
    """Lift one register's v1 constraints to v2. Returns (new_data, reports).

    ``new_data`` has ``access_constraints`` dropped, ``access_constraints_v2``
    populated, ``schema_version: 2``. ``reports`` lists any per-constraint
    rejects/repairs (empty when the lift was clean).
    """
    ri = V1RegisterInfo(**data)
    gates: list[dict] = []
    reports: list[str] = []
    for i, c in enumerate(ri.access_constraints):
        res = lift_v1_constraint(c, ri.datasheet_register_abbreviation)
        gates.extend(g.model_dump() for g in res.constraints)
        for r in res.rejects:
            reports.append(f"constraint[{i}] REJECT {r.reason}: {r.field}={r.value!r}")
        for rep in res.repairs:
            reports.append(f"constraint[{i}] repair: {rep}")
    out = {k: v for k, v in data.items() if k != "access_constraints"}
    out["access_constraints_v2"] = gates
    out["schema_version"] = 2
    return out, reports


def convert_dir(in_dir: Path, out_dir: Path) -> dict:
    """Convert every v1 register file under ``in_dir`` into ``out_dir`` (mirror
    layout). Non-register files are copied verbatim. Returns a summary dict."""
    summary = {"converted": 0, "copied": 0, "already_v2": 0,
               "unreadable": 0, "constraints_lifted": 0, "reports": []}
    for src in sorted(in_dir.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(in_dir)
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(src.read_text())
        except (ValueError, UnicodeDecodeError):
            shutil.copy2(src, dst)               # not JSON -> copy through
            summary["copied"] += 1
            continue
        if not _is_v1_register_file(data):
            shutil.copy2(src, dst)
            if isinstance(data, dict) and (
                    data.get("schema_version") == 2 or data.get("access_constraints_v2")):
                summary["already_v2"] += 1
            else:
                summary["copied"] += 1
            continue
        try:
            new_data, reports = convert_register(data)
        except Exception as e:                    # malformed v1 -> copy + note
            shutil.copy2(src, dst)
            summary["unreadable"] += 1
            summary["reports"].append(f"{rel}: NOT CONVERTED ({e})")
            continue
        dst.write_text(json.dumps(new_data, indent=2) + "\n")
        summary["converted"] += 1
        summary["constraints_lifted"] += len(new_data["access_constraints_v2"])
        for r in reports:
            summary["reports"].append(f"{rel}: {r}")
    return summary


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="old grammar-v1 generator run directory")
    ap.add_argument("out_dir", nargs="?",
                    help="output directory (omit with --in-place)")
    ap.add_argument("--in-place", action="store_true",
                    help="convert the run_dir in place (overwrite v1 files)")
    args = ap.parse_args(argv)

    in_dir = Path(args.run_dir)
    if not in_dir.is_dir():
        sys.exit(f"not a directory: {in_dir}")
    if args.in_place:
        if args.out_dir:
            sys.exit("--in-place takes no OUT_DIR")
        out_dir = in_dir
    elif args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        sys.exit("provide OUT_DIR or --in-place")

    summary = convert_dir(in_dir, out_dir)
    print(f"converted {summary['converted']} register file(s), "
          f"{summary['constraints_lifted']} constraint(s) lifted; "
          f"{summary['already_v2']} already v2, {summary['copied']} copied, "
          f"{summary['unreadable']} unreadable")
    for r in summary["reports"]:
        print("  " + r, file=sys.stderr)


if __name__ == "__main__":
    main()
