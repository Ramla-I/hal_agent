#!/usr/bin/env python3
"""One-off backfill of an existing generator output directory, in place, so it
looks like one clean run of the improved (retry-capable) generator:

  1. Full-enumeration non-batched generation. Enumerating the SVD expands dim
     arrays to concrete names (BCR%s -> bcr2/bcr3/bcr4), so the missing concrete
     instances are generated; already-good files are skipped (skip-existing).
  2. The empty-field retry (built into run_generator_batched) force-regenerates,
     one register per call, any register whose subfields came back empty but whose
     SVD register has fields — the batching drop-outs. Failed re-gens keep the
     existing file (register-level facts preserved).
  3. Stale "%s"-placeholder files (now superseded by the concrete instances from
     step 1) are deleted. A "%s" file with no concrete sibling (its expansion
     failed to generate) is kept, so nothing is silently dropped.

Runs inside Docker.

    python scripts/backfill_generator.py --devices rm0451
    python scripts/backfill_generator.py --all
"""
import argparse
import os
import re
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_REPO, os.path.join(_REPO, "core")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config
from s0_run_full_analysis import (
    resolve_device_paths, build_context_retrieval_params, apply_retrieval_override, determine_client,
)
from s1a_generator import run_generator_batched, _find_empty_field_registers
from agent_tools.tools import all_svd_file_paths


def _delete_stale_pct(agent_output_dir: str) -> list:
    """Remove "%s"-placeholder files that now have a concrete sibling (e.g.
    fmc_bcr%s next to the freshly generated fmc_bcr2). Returns deleted names."""
    files = os.listdir(agent_output_dir)
    deleted = []
    for base in files:
        if "%s" not in base:
            continue
        pat = re.escape(base).replace(re.escape("%s"), r"\d+")
        if any(x != base and re.fullmatch(pat, x) for x in files):
            os.remove(os.path.join(agent_output_dir, base))
            deleted.append(base)
    return deleted


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--devices", nargs="+")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--run", type=int, default=1)
    ap.add_argument("--retries", type=int, default=2)
    args = ap.parse_args()

    model = config.GENERATOR_MODEL_NAME
    models = list(config.STAGE_MODELS["generator"])
    client = determine_client(model)
    want = None if args.all else {d.lower() for d in args.devices}

    for ctx in config.user_contexts:
        if want is not None and ctx.device_name.lower() not in want:
            continue
        paths = resolve_device_paths(ctx, _REPO, args.run)
        if not os.path.isdir(paths.agent_output_dir):
            print(f"{ctx.device_name}: no output dir {paths.agent_output_dir}, skip", flush=True)
            continue
        cr = build_context_retrieval_params(paths.device_dir, ctx)
        cr = apply_retrieval_override(cr, "openevolve", ctx.device_name, _REPO, ctx.manufacturer)
        svds = all_svd_file_paths(paths.device_dir)

        empty_before = sum(len(v) for v in _find_empty_field_registers(paths.agent_output_dir, svds).values())
        pct_before = len([f for f in os.listdir(paths.agent_output_dir) if "%s" in f])
        print(f"{ctx.device_name}: {empty_before} empty-field register(s), "
              f"{pct_before} %s-placeholder file(s) before", flush=True)

        # Full enumeration (peripherals_registers_dict=None) so dim arrays expand to
        # concrete names; non-batched (max_registers_per_batch=1) so nothing truncates;
        # empty_field_retries backfills the existing drop-outs.
        run_generator_batched(
            client, model, ctx.device_name, args.run, paths.device_dir,
            paths.agent_output_dir, cr, ctx.manufacturer,
            peripherals_registers_dict=None, max_registers_per_batch=1,
            models=models, empty_field_retries=args.retries,
        )

        deleted = _delete_stale_pct(paths.agent_output_dir)
        empty_after = sum(len(v) for v in _find_empty_field_registers(paths.agent_output_dir, svds).values())
        pct_after = len([f for f in os.listdir(paths.agent_output_dir) if "%s" in f])
        print(f"{ctx.device_name}: empty-field {empty_before} -> {empty_after}; "
              f"deleted {len(deleted)} stale %s file(s); {pct_after} %s file(s) remain "
              f"(no concrete sibling)", flush=True)


if __name__ == "__main__":
    main()
