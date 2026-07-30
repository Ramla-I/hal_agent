#!/usr/bin/env python3
"""Preprocess (chunk + enrich + local vector DB) STM datasheets that lack chunks,
so they become constraint-ready (constraint anchoring needs
chunked_datasheets/stm/{rm}/chunks/md) and generator-ready.

Runs inside Docker. Per RM: context_retrieval/preprocessing/pipeline.py on the
device PDF with --backend local. Bounded parallelism (chunking+embedding is
CPU-heavy — keep it low), one log per RM, resume by skipping RMs that already
have md chunks.

    python scripts/preprocess_stm_batch.py --devices rm0041 rm0090 ... --parallel 1
"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_DIR = os.path.join(_REPO, "logs", "stm_preprocess")


def _md_dir(rm: str) -> str:
    return os.path.join(_REPO, "chunked_datasheets", "stm", rm, "chunks", "md")


def _run_rm(rm: str, fmt: str, backend: str, force: bool, timeout_s: int) -> dict:
    if not force and os.path.isdir(_md_dir(rm)) and os.listdir(_md_dir(rm)):
        return {"rm": rm, "status": "skipped_has_chunks"}
    pdf = os.path.join(_REPO, "devices", "stm", rm, f"{rm}.pdf")
    if not os.path.isfile(pdf):
        return {"rm": rm, "status": "fail", "reason": "no_pdf"}
    os.makedirs(_LOG_DIR, exist_ok=True)
    log = os.path.join(_LOG_DIR, f"{rm}.log")
    # --output-dir MUST place chunks under chunked_datasheets/stm/{rm}/chunks (where
    # the constraint step + config.chunk_index_path look); pipeline.py's default is
    # {pdf_dir}/chunks (devices/...), which the constraint anchor step never reads.
    out_dir = os.path.join("chunked_datasheets", "stm", rm, "chunks")
    cmd = [sys.executable, "context_retrieval/preprocessing/pipeline.py",
           pdf, rm, "--output-dir", out_dir,
           "--format", fmt, "--embed-metadata", "--backend", backend]
    with open(log, "w") as lf:
        lf.write(f"==== {' '.join(cmd)}\n")
        lf.flush()
        t0 = time.time()
        try:
            # start_new_session so a timeout kills the whole process group (the
            # pdf->md converter may spawn children); giant datasheets that hang
            # can't stall the rest of the batch.
            rc = subprocess.run(cmd, cwd=_REPO, stdout=lf, stderr=subprocess.STDOUT,
                                timeout=timeout_s, start_new_session=True).returncode
        except subprocess.TimeoutExpired:
            rc = 124
            lf.write(f"---- TIMEOUT after {timeout_s}s — skipped (likely oversized PDF)\n")
        lf.write(f"---- rc={rc} ({time.time() - t0:.0f}s)\n")
    ok = os.path.isdir(_md_dir(rm)) and os.listdir(_md_dir(rm))
    status = "ok" if (rc == 0 and ok) else ("timeout" if rc == 124 else "fail")
    return {"rm": rm, "status": status, "rc": rc}


def _pdf_mb(rm: str) -> float:
    p = os.path.join(_REPO, "devices", "stm", rm, f"{rm}.pdf")
    return os.path.getsize(p) / 1e6 if os.path.isfile(p) else 0.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devices", nargs="+", required=True)
    ap.add_argument("--format", default="markdown")
    ap.add_argument("--backend", default="local", choices=["local", "openai", "none"])
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=3600,
                    help="per-RM timeout seconds (default 3600); giant PDFs that "
                         "exceed it are skipped so they can't stall the batch")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    os.makedirs(_LOG_DIR, exist_ok=True)
    status = os.path.join(_LOG_DIR, "status.json")
    results: list[dict] = []
    # Smallest PDF first: quick wins complete early; the 70-94MB giants (which may
    # hang or take hours in pdf->md conversion) go last and are timeout-bounded.
    devices = sorted(args.devices, key=_pdf_mb)
    n = len(devices)
    t_start = time.time()

    def save():
        with open(status, "w") as f:
            json.dump({"total": n, "done": len(results),
                       "elapsed_s": round(time.time() - t_start),
                       "results": results}, f, indent=1)

    save()
    print(f"preprocess start: {n} RMs, parallel={args.parallel}, "
          f"timeout={args.timeout}s (smallest PDF first)", flush=True)
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(_run_rm, rm, args.format, args.backend, args.force, args.timeout): rm
                for rm in devices}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            save()
            print(f"[{len(results)}/{n}] {r['rm']}: {r['status']}", flush=True)
    save()
    ok = [r for r in results if r["status"].startswith(("ok", "skipped"))]
    print(f"DONE {len(ok)}/{n} ok; fails: "
          f"{[r['rm'] for r in results if r['status'] == 'fail']}", flush=True)


if __name__ == "__main__":
    main()
