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

Each register file in a run directory is already a ``RegisterInfo`` JSON
(``datasheet_register_abbreviation``, ``address_offset``, ``reset_value``,
``size``, ``subfields``, ``access_constraints``) -- the same schema as
``applications/pac_codegen/constraint_test/stm32f405_i2c1.json``. This bridge simply selects the
registers that carry one or more ``access_constraints`` and forwards them, one
output file per register, ready to feed into the Rust code generator.

NOTE ON SCOPE
-------------
This bridge only *collects and forwards* the dependency invariants
(access_constraints) that were already extracted upstream. It does NOT *validate*
them -- i.e. it does not check that the preconditions/postconditions are
internally consistent, satisfiable, or faithful to the datasheet. Full constraint
validation (and enforcement of dependency invariants end-to-end) is later work,
tracked under Phase 2/4 (see ``docs/pac/PHASE4_PLAN.md`` and
``docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md``). The validator layout logic in
``core/s4_validator.py`` is intentionally left untouched.

Usage (CLI):
    python applications/pac_codegen/collect_constraints.py agent_output/stm/rm0041/24 \
        --output-dir applications/pac_codegen/constraints/rm0041_24

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
from pathlib import Path
from typing import Optional

# Add the repo root to sys.path so we can import the shared defs.py.
# This file lives at applications/pac_codegen/collect_constraints.py, so the
# repo root is three levels up.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# This application's own directory (applications/pac_codegen/).
_APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT))

from defs import RegisterInfo  # noqa: E402  (path setup must precede import)


# Files that may appear inside a run directory but are not register outputs.
_SKIP_NAMES = {".DS_Store"}
_SKIP_DIR_NAMES = {"info", "coverage_improver"}


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


def collect_constraints(
    run_dir: str,
    output_dir: Optional[str] = None,
    include_empty: bool = False,
) -> list[dict]:
    """Collect access constraints from a generator-output run directory.

    Scans ``run_dir`` for register files named ``{peripheral}_{register}``,
    reads each register's ``access_constraints``, and -- for every register that
    carries at least one constraint (unless ``include_empty`` is set) -- writes a
    constraints file in the ``RegisterInfo`` schema consumed by
    ``rust_codegen.py``.

    Args:
        run_dir: Path to a run directory, e.g. ``agent_output/stm/rm0041/24``.
        output_dir: Where to write the per-register constraints JSON files.
            Defaults to ``applications/pac_codegen/constraints/collected/<device>_<run>``
            derived from the run directory.
        include_empty: If True, also forward registers whose
            ``access_constraints`` list is empty. Default False (constrained
            registers only).

    Returns:
        A list of summary dicts, one per collected register, each with keys
        ``peripheral``, ``register``, ``num_constraints``, and ``output_path``.
    """
    run_path = Path(run_dir)
    if not run_path.is_dir():
        raise NotADirectoryError(f"Run directory not found: {run_path}")

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

        # Write out in the RegisterInfo schema rust_codegen.py consumes. Use the
        # original file name (lower-cased, .json suffix) so the peripheral is
        # recoverable for the --peripheral flag.
        out_file = out_path / f"{entry.name}.json"
        out_file.write_text(register_info.model_dump_json(indent=2))

        results.append(
            {
                "peripheral": peripheral,
                "register": register,
                "num_constraints": num_constraints,
                "output_path": str(out_file),
            }
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Collect access_constraints from a generator-output run directory "
            "and forward them as RegisterInfo JSON files for rust_codegen.py."
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
    args = parser.parse_args()

    results = collect_constraints(
        args.run_dir,
        output_dir=args.output_dir,
        include_empty=args.include_empty,
    )

    if not results:
        print(
            f"No constrained registers found in {args.run_dir}. "
            f"(Use --include-empty to forward all registers.)"
        )
        return

    total = sum(r["num_constraints"] for r in results)
    print(f"Collected {len(results)} register(s), {total} constraint(s) total:")
    for r in results:
        print(
            f"  {r['peripheral']}_{r['register']}: "
            f"{r['num_constraints']} constraint(s) -> {r['output_path']}"
        )


if __name__ == "__main__":
    main()
