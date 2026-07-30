#!/usr/bin/env python3
"""Batch-run the STM pipeline (structure + constraint chains) over many RMs.

Runs inside Docker (/app layout, deps present). Per RM, in order:
  1. s0_run_full_analysis  — generator -> structure validator -> SVD diff ->
     bug-finding (-> {rm}_structure_review.csv) -> chained constraint validation
     (-> constraint_validation/validated.jsonl). Retrieval: openevolve.
  2. constraints_review    — format validated.jsonl -> {rm}_constraints_review.jsonl
  3. s6_validate_candidates — write validator_verdict/confidence into the
     structure review CSV.

Bounded parallelism across RMs, one log file per RM, resume via a per-RM
done-marker (delete it or pass --force to re-run). Run numbers auto-resolve
(fresh device -> run 1; an interrupted RM resumes the same run).

    python scripts/run_stm_batch.py --devices rm0091 rm0008 ... --parallel 2
"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_DIR = os.path.join(_REPO, "logs", "stm_batch")


def _marker(rm: str, run: int) -> str:
    return os.path.join(_REPO, "evaluation", "stm", rm, str(run), ".batch_done")


def _steps(rm: str, run: int, chunks: str):
    py = sys.executable
    return [
        ("s0", [py, "core/s0_run_full_analysis.py", "--devices", rm,
                "--retrieval", "openevolve", "--constraint-validation",
                "--constraint-chunks-root", chunks, "--constraint-batch-size", "8"]),
        ("review", [py, "core/constraints_review.py", "--rm", rm, "--run", str(run)]),
        ("s6", [py, "core/s6_validate_candidates.py", "--devices", rm, "--run", str(run)]),
    ]


def _run_rm(rm: str, run: int, chunks: str, force: bool) -> dict:
    if not force and os.path.exists(_marker(rm, run)):
        return {"rm": rm, "status": "skipped_done"}
    os.makedirs(_LOG_DIR, exist_ok=True)
    log = os.path.join(_LOG_DIR, f"{rm}.log")
    with open(log, "w") as lf:
        for name, cmd in _steps(rm, run, chunks):
            lf.write(f"\n==== {name} :: {' '.join(cmd)}\n")
            lf.flush()
            t0 = time.time()
            rc = subprocess.call(cmd, cwd=_REPO, stdout=lf, stderr=subprocess.STDOUT)
            lf.write(f"---- {name} rc={rc} ({time.time() - t0:.0f}s)\n")
            lf.flush()
            if rc != 0:
                return {"rm": rm, "status": "fail", "step": name, "rc": rc}
    os.makedirs(os.path.dirname(_marker(rm, run)), exist_ok=True)
    with open(_marker(rm, run), "w") as f:
        f.write("ok\n")
    return {"rm": rm, "status": "ok"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devices", nargs="+", required=True)
    ap.add_argument("--run", type=int, default=1, help="run number for review/s6 (default 1)")
    ap.add_argument("--chunks", default="chunked_datasheets/stm")
    ap.add_argument("--parallel", type=int, default=2)
    ap.add_argument("--force", action="store_true", help="ignore done-markers, re-run all")
    args = ap.parse_args()

    os.makedirs(_LOG_DIR, exist_ok=True)
    status = os.path.join(_LOG_DIR, "status.json")
    results: list[dict] = []
    n = len(args.devices)
    t_start = time.time()

    def save():
        with open(status, "w") as f:
            json.dump({"total": n, "done": len(results),
                       "elapsed_s": round(time.time() - t_start),
                       "results": results}, f, indent=1)

    save()
    print(f"batch start: {n} RMs, parallel={args.parallel}", flush=True)
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(_run_rm, rm, args.run, args.chunks, args.force): rm
                for rm in args.devices}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            save()
            tag = r["status"] + (f"@{r.get('step')}" if r["status"] == "fail" else "")
            print(f"[{len(results)}/{n}] {r['rm']}: {tag}", flush=True)
    save()
    ok = [r for r in results if r["status"] in ("ok", "skipped_done")]
    fails = [r["rm"] for r in results if r["status"] == "fail"]
    print(f"DONE {len(ok)}/{n} ok; fails: {fails}", flush=True)


if __name__ == "__main__":
    main()
