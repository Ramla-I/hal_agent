#!/usr/bin/env python3
"""Re-generate register files whose `subfields` came back empty (a batching
drop-out) for the given RMs, in place. Reconstructs the generation context
(openevolve retrieval) and calls the batched generator over the existing output:
the already-good registers are skipped, and the empty-field retry re-generates the
rest one register per call (no truncation), overwriting in the same output dir.
Runs inside Docker.

    python scripts/regen_empty_fields.py --devices rm0008
"""
import argparse
import os
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devices", nargs="+", required=True)
    ap.add_argument("--run", type=int, default=1)
    ap.add_argument("--retries", type=int, default=2)
    args = ap.parse_args()

    model = config.GENERATOR_MODEL_NAME
    models = list(config.STAGE_MODELS["generator"])
    client = determine_client(model)
    want = {d.lower() for d in args.devices}

    for ctx in config.user_contexts:
        if ctx.device_name.lower() not in want:
            continue
        paths = resolve_device_paths(ctx, _REPO, args.run)
        if not os.path.isdir(paths.agent_output_dir):
            print(f"{ctx.device_name}: no output dir {paths.agent_output_dir}, skip")
            continue
        cr = build_context_retrieval_params(paths.device_dir, ctx)
        cr = apply_retrieval_override(cr, "openevolve", ctx.device_name, _REPO, ctx.manufacturer)
        svds = all_svd_file_paths(paths.device_dir)

        before = _find_empty_field_registers(paths.agent_output_dir, svds)
        n_before = sum(len(v) for v in before.values())
        print(f"{ctx.device_name}: {n_before} empty-field register(s) before "
              f"-> {dict((p, len(r)) for p, r in before.items())}", flush=True)
        if n_before == 0:
            continue

        # Only the empty ones (force-overwrite, single register per call) — fast.
        run_generator_batched(
            client, model, ctx.device_name, args.run, paths.device_dir,
            paths.agent_output_dir, cr, ctx.manufacturer,
            peripherals_registers_dict=before, max_registers_per_batch=1,
            models=models, empty_field_retries=args.retries, force=True,
        )

        after = _find_empty_field_registers(paths.agent_output_dir, svds)
        n_after = sum(len(v) for v in after.values())
        print(f"{ctx.device_name}: {n_after} empty-field register(s) remain "
              f"(recovered {n_before - n_after})"
              + (f" -> still empty: {dict((p, r) for p, r in after.items())}" if after else ""),
              flush=True)


if __name__ == "__main__":
    main()
