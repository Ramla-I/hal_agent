#!/usr/bin/env python3
"""Build the field-ACCESS review for devices: diff (generator vs SVD) + validator.

Per device: write ``{rm}_access_review.csv`` (access mismatches, structure-review
layout), then run the SAME s6 candidate validator on it (OpenEvolve retrieval +
the calibrated validator card + vendor access legend) so validator_verdict /
validator_confidence match the structure review exactly. No analyzer, no
generator re-run. Runs inside Docker (needs the LLM/retrieval toolchain).

  python scripts/build_access_reviews.py --devices rm0041
  python scripts/build_access_reviews.py --all --parallel 4
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_REPO, os.path.join(_REPO, "core")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config
from applications.bug_finding.access import write_access_review
from s6_validate_candidates import validate_run
from s0_run_full_analysis import resolve_run_number


def build_for(ctx, run: int, models: list, cards_dir: str | None) -> dict:
    mfr = getattr(ctx.manufacturer, "value", str(ctx.manufacturer)).lower()
    _, n = write_access_review(ctx.device_name, mfr, run, _REPO)
    if n == 0:
        return {"device": ctx.device_name, "run": run, "access_diffs": 0, "skipped": "no access diffs"}
    kw = {"review_suffix": "access_review", "validator_subdir": "access_validator"}
    if cards_dir:
        kw["cards_dir"] = cards_dir
    res = validate_run(ctx, _REPO, run, models, **kw)
    res["access_diffs"] = n
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devices", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--run", type=int, default=None)
    ap.add_argument("--validator-model", default=None)
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--diff-only", action="store_true", help="write the CSV, skip the validator")
    args = ap.parse_args()

    contexts = config.user_contexts
    if args.devices:
        want = {d.lower() for d in args.devices}
        contexts = [c for c in contexts if c.device_name.lower() in want]
    if not contexts:
        print("no matching devices"); return

    models = [args.validator_model] if args.validator_model else list(config.STAGE_MODELS["validator"])
    jobs = [(ctx, args.run if args.run is not None else resolve_run_number(_REPO, ctx)) for ctx in contexts]

    def run_one(ctx, rn):
        mfr = getattr(ctx.manufacturer, "value", str(ctx.manufacturer)).lower()
        if args.diff_only:
            _, n = write_access_review(ctx.device_name, mfr, rn, _REPO)
            return {"device": ctx.device_name, "run": rn, "access_diffs": n, "diff_only": True}
        return build_for(ctx, rn, models, None)

    results = []
    if args.parallel > 1:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futs = {ex.submit(run_one, ctx, rn): ctx.device_name for ctx, rn in jobs}
            for fut in as_completed(futs):
                try:
                    results.append(fut.result())
                except Exception as e:
                    results.append({"device": futs[fut], "error": str(e)})
    else:
        for ctx, rn in jobs:
            try:
                results.append(run_one(ctx, rn))
            except Exception as e:
                results.append({"device": ctx.device_name, "error": str(e)})

    print("\n=== access review summary ===")
    for r in sorted(results, key=lambda r: r.get("device", "")):
        print(" ", json.dumps(r))


if __name__ == "__main__":
    main()
