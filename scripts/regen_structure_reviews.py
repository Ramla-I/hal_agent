#!/usr/bin/env python3
"""Regenerate {rm}_structure_review.csv from the on-disk generator output + the
(fixed) SVD parser — no generator/s6 re-run. Re-runs the bug-finding pipeline
(diff -> analyzer -> report) per RM and re-consolidates. Reviewer tp_fp /
correct_value and s6 validator_verdict / validator_confidence are preserved by
row identity (report.py). Analyzer is gpt-5-nano (OpenAI). Runs inside Docker.

    python scripts/regen_structure_reviews.py --devices rm0008
    python scripts/regen_structure_reviews.py --parallel 4          # all RMs under evaluation/stm

NOTE: do not regen an RM whose s6 is being (re)written concurrently — the
consolidated CSV is a shared output.
"""
import argparse
import glob
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)


def _regen(rm: str, run: str, mfr: str) -> dict:
    from applications.bug_finding.pipeline import run_bug_finding
    from applications.bug_finding.report import write_consolidated_from_dir
    svd_dir = os.path.join(_REPO, "devices", mfr, rm, "svd")
    agent = os.path.join(_REPO, "agent_output", mfr, rm, run)
    res = os.path.join(_REPO, "evaluation", mfr, rm, run)
    if not os.path.isdir(agent):
        return {"rm": rm, "status": "skip_no_generator_output"}
    t0 = time.time()
    run_bug_finding(svd_dir, agent, res, run_analyzer_enabled=True)
    n = write_consolidated_from_dir(res)
    return {"rm": rm, "status": "ok", "rows": n, "secs": round(time.time() - t0)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devices", nargs="*", help="RMs (default: all under evaluation/{mfr})")
    ap.add_argument("--run", default="1")
    ap.add_argument("--manufacturer", default="stm")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--exclude", nargs="*", default=[], help="RMs to skip (e.g. giants mid-backfill)")
    ap.add_argument("--no-dim-expand", action="store_true",
                    help="parse SVD with <dim> arrays collapsed (%%s) — required when the "
                         "on-disk generator output predates dim-expansion")
    args = ap.parse_args()

    if args.no_dim_expand:
        os.environ["SVD_DIM_EXPAND"] = "0"

    rms = args.devices or sorted(
        os.path.basename(os.path.dirname(os.path.dirname(p)))
        for p in glob.glob(os.path.join(_REPO, "evaluation", args.manufacturer, "*", args.run, "")))
    rms = [r for r in rms if r not in set(args.exclude)]
    print(f"regen {len(rms)} RM(s), parallel={args.parallel}"
          + (f" (excluding {args.exclude})" if args.exclude else ""), flush=True)

    results = []
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(_regen, rm, args.run, args.manufacturer): rm for rm in rms}
        for fut in as_completed(futs):
            rm = futs[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"rm": rm, "status": "FAIL", "err": str(e)[:120]}
            results.append(r)
            tag = r["status"] + (f" {r.get('rows')}rows {r.get('secs')}s" if r["status"] == "ok"
                                 else f" {r.get('err', '')}")
            print(f"  [{len(results)}/{len(rms)}] {rm}: {tag}", flush=True)
    ok = [r for r in results if r["status"] == "ok"]
    print(f"DONE {len(ok)}/{len(rms)} regenerated; fails: "
          f"{[r['rm'] for r in results if r['status'] == 'FAIL']}", flush=True)


if __name__ == "__main__":
    main()
