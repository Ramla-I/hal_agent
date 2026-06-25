"""Top-level, human-reviewable summary of register ACCESS CONSTRAINTS.

The generator extracts access_constraints (ordering/precondition invariants like
"write to X only when Y is cleared") per register. SVDs cannot express these, so
they are NOT part of the layout bug-finding / diff pipeline. This builds a
per-RM constraints review CSV — one row per DISTINCT constraint, deduped across
the registers/instances that share it — with a tp_fp column for the reviewer.

Run (regenerates the review file for every run that has generator output):
    python applications/pac_codegen/constraints_review.py
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re

CONSTRAINTS_REVIEW_FIELDS = [
    "RM",
    "peripheral",
    "target_register",
    "target_operation",
    "target_fields",
    "preconditions",
    "postconditions",
    "severity",
    "occurrences",        # how many register files carried this exact constraint
    "example_registers",
    "datasheet_text",     # the evidence the reviewer checks
    "tp_fp",              # reviewer label: TP / FP
]

# Columns that identify a constraint row (so tp_fp labels survive regeneration).
_KEY_FIELDS = ("peripheral", "target_register", "target_operation",
               "target_fields", "preconditions", "postconditions")

_SKIP_SUFFIXES = (".json", ".jsonl", ".csv", ".txt")

# Rows are grouped/sorted by peripheral → target_register → target_operation (then
# target_fields / pre / post for determinism) in *natural* order so numeric
# suffixes read like a human (tim2 before tim10, adc1 before adc10).
_NAT_RE = re.compile(r"(\d+)")


def _nat_chunks(s: str) -> tuple:
    return tuple((1, int(t)) if t.isdigit() else (0, t.lower())
                 for t in _NAT_RE.split(s or "") if t)


def _constraint_sort_key(key: tuple) -> tuple:
    """Natural grouping order for a constraint key (= _KEY_FIELDS order)."""
    peripheral, target_register, operation, target_fields, pre, post = key
    return (_nat_chunks(peripheral), _nat_chunks(target_register), _nat_chunks(operation),
            _nat_chunks(target_fields), pre or "", post or "")


def resort_constraints_review_csv(path: str) -> int:
    """Re-sort an existing constraints review CSV in place by the canonical
    grouping, preserving the header and every cell (incl. reviewer tp_fp). A pure
    reorder — safe to re-run and idempotent."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    if not fields:
        return 0
    rows.sort(key=lambda r: _constraint_sort_key(
        tuple(r.get(c, "") for c in _KEY_FIELDS)))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _split_peripheral_register(filename: str):
    peripheral, sep, register = filename.partition("_")
    if not sep:
        return None, None
    return peripheral.lower(), register.lower()


def _flatten_states(states) -> str:
    """FieldState list -> 'REG.FIELD=state; ...'."""
    parts = []
    for s in states or []:
        reg = s.get("register_name", "")
        fld = s.get("field_name", "")
        st = s.get("required_state", "")
        parts.append(f"{reg}.{fld}={st}")
    return "; ".join(parts)


def load_constraints(agent_output_dir: str):
    """Yield (peripheral, register, constraint_dict) for every access constraint
    in the generator output of a run."""
    for path in sorted(glob.glob(os.path.join(agent_output_dir, "*"))):
        base = os.path.basename(path)
        if not os.path.isfile(path) or base == "run_manifest.json" or base.endswith(_SKIP_SUFFIXES):
            continue
        peripheral, register = _split_peripheral_register(base)
        if peripheral is None:
            continue
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        for c in data.get("access_constraints") or []:
            if isinstance(c, dict):
                yield peripheral, register, c


def _load_existing_tp_fp(output_path: str) -> dict[tuple, str]:
    if not os.path.exists(output_path):
        return {}
    preserved: dict[tuple, str] = {}
    try:
        for row in csv.DictReader(open(output_path, newline="", encoding="utf-8")):
            val = (row.get("tp_fp") or "").strip()
            if val:
                preserved[tuple(row.get(c, "") for c in _KEY_FIELDS)] = val
    except Exception:
        return {}
    return preserved


def write_constraints_review_csv(agent_output_dir: str, output_path: str, rm: str) -> int:
    """Write the per-RM constraints review CSV; returns the number of rows.

    Dedups identical constraints (key = peripheral + target + operation + fields +
    pre/postconditions) across registers; preserves reviewer tp_fp labels.
    """
    groups: dict[tuple, dict] = {}
    for peripheral, register, c in load_constraints(agent_output_dir):
        target_fields = ";".join(c.get("target_fields") or []) or "(whole register)"
        pre = _flatten_states(c.get("preconditions"))
        post = _flatten_states(c.get("postconditions"))
        key = (peripheral, c.get("target_register", "") or "", c.get("target_operation", "") or "",
               target_fields, pre, post)
        if key not in groups:
            groups[key] = {"registers": set(), "severity": c.get("severity", "") or "", "text": ""}
        g = groups[key]
        g["registers"].add(f"{peripheral}_{register}")
        if not g["text"] and c.get("datasheet_text"):
            g["text"] = " ".join(str(c["datasheet_text"]).split())

    preserved = _load_existing_tp_fp(output_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CONSTRAINTS_REVIEW_FIELDS)
        writer.writeheader()
        for key in sorted(groups, key=_constraint_sort_key):
            peripheral, target_register, operation, target_fields, pre, post = key
            g = groups[key]
            registers = sorted(g["registers"])
            writer.writerow({
                "RM": rm,
                "peripheral": peripheral,
                "target_register": target_register,
                "target_operation": operation,
                "target_fields": target_fields,
                "preconditions": pre,
                "postconditions": post,
                "severity": g["severity"],
                "occurrences": len(registers),
                "example_registers": ";".join(registers[:8]),
                "datasheet_text": g["text"][:500],
                "tp_fp": preserved.get(key, ""),
            })
    return len(groups)


def main() -> None:
    """Regenerate the constraints review for every run with generator output."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    os.chdir(repo_root)
    total = 0
    # run dirs that contain generator output (have a run_manifest or register files)
    for run_dir in sorted(glob.glob("agent_output/stm/*/*")):
        if not os.path.isdir(run_dir):
            continue
        parts = run_dir.split(os.sep)
        mfr, rm, run = parts[-3], parts[-2], parts[-1]
        if not run.isdigit():
            continue
        n_constraints = sum(1 for _ in load_constraints(run_dir))
        if n_constraints == 0:
            continue
        output_path = os.path.join("evaluation", mfr, rm, run, f"{rm}_constraints_review.csv")
        n = write_constraints_review_csv(run_dir, output_path, rm)
        print(f"{rm}/{run}: {n} distinct constraints -> {output_path}")
        total += 1
    print(f"\nwrote constraints review for {total} run(s)")


if __name__ == "__main__":
    main()
