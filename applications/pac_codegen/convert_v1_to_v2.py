#!/usr/bin/env python3
"""Convert OLD (grammar-v1) generator output to grammar-v2, in bulk.

The pipeline is grammar-v2 only. This is the ONE tool that understands the
retired v1 access-constraint grammar: point it at an old generator run
directory (one JSON file per ``{peripheral}_{register}`` whose constraints live
in the v1 ``access_constraints`` list) and it writes a parallel directory whose
register files carry ``access_constraints_v2`` instead (``access_constraints``
dropped, ``schema_version: 2``). Everything else (``info/`` subdir, non-register
files) is copied through unchanged.

The transformation is the mechanical B.6 lift (``defs.lift_v1_constraint``):
every v1 constraint becomes one or more v2 ``state_gate``s; unliftable drift
(unparseable states, unknown vocabulary) is reported per file, never silently
dropped.

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

# Repo root (three levels up: applications/pac_codegen/ -> repo).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from defs import RegisterInfo, lift_v1_constraint  # noqa: E402


def _is_v1_register_file(data: object) -> bool:
    """A v1 register file is a dict with a non-empty v1 ``access_constraints``
    list and NOT already native v2."""
    if not isinstance(data, dict) or "access_constraints" not in data:
        return False
    if data.get("schema_version") == 2 or data.get("access_constraints_v2"):
        return False  # already v2
    return bool(data.get("access_constraints"))


def convert_register(data: dict) -> tuple[dict, list[str]]:
    """Lift one register's v1 constraints to v2. Returns (new_data, reports).

    ``new_data`` has ``access_constraints: []``, ``access_constraints_v2``
    populated, ``schema_version: 2``. ``reports`` lists any per-constraint
    rejects/repairs (empty when the lift was clean).
    """
    ri = RegisterInfo(**data)
    gates: list[dict] = []
    reports: list[str] = []
    for i, c in enumerate(ri.access_constraints):
        res = lift_v1_constraint(c, ri.datasheet_register_abbreviation)
        gates.extend(g.model_dump() for g in res.constraints)
        for r in res.rejects:
            reports.append(f"constraint[{i}] REJECT {r.reason}: {r.field}={r.value!r}")
        for rep in res.repairs:
            reports.append(f"constraint[{i}] repair: {rep}")
    out = dict(data)
    out["access_constraints"] = []
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
