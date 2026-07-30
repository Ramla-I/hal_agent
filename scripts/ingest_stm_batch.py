#!/usr/bin/env python3
"""Build local ChromaDB vector stores for STM RMs from their existing
chunked_datasheets md_enriched chunks — making chunk-only RMs generator-ready
(openevolve retrieval reads the local store; s0 Step 1 then skips re-chunking
because databases/{rm}_md_chunks already exists).

Registration in config_devices.json must be done FIRST (ingest_local_vector_db
looks the device up in config.user_contexts). CPU-only (local FastEmbed
embeddings) — no Groq — so it can run alongside the pipeline. Runs inside Docker.
Resumes by skipping RMs whose vector store already exists.

    python scripts/ingest_stm_batch.py --devices rm0351 rm0399 ... --parallel 4
"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_DIR = os.path.join(_REPO, "logs", "stm_ingest")


def _db_exists(rm: str) -> bool:
    return os.path.isdir(os.path.join(_REPO, "databases", f"{rm}_md_chunks"))


def _chunks_dir(rm: str) -> str:
    enr = os.path.join("chunked_datasheets", "stm", rm, "chunks", "md_enriched")
    return enr if os.path.isdir(os.path.join(_REPO, enr)) else \
        os.path.join("chunked_datasheets", "stm", rm, "chunks", "md")


def _ingest(rm: str, force: bool) -> dict:
    if not force and _db_exists(rm):
        return {"rm": rm, "status": "skipped_db_exists"}
    os.makedirs(_LOG_DIR, exist_ok=True)
    log = os.path.join(_LOG_DIR, f"{rm}.log")
    cmd = [sys.executable, "context_retrieval/preprocessing/ingest_local_vector_db.py",
           rm, "--chunks-dir", _chunks_dir(rm), "--embedding-provider", "local"]
    with open(log, "w") as lf:
        lf.write(" ".join(cmd) + "\n")
        lf.flush()
        t0 = time.time()
        rc = subprocess.call(cmd, cwd=_REPO, stdout=lf, stderr=subprocess.STDOUT)
        lf.write(f"\n---- rc={rc} ({time.time() - t0:.0f}s)\n")
    ok = rc == 0 and _db_exists(rm)
    return {"rm": rm, "status": "ok" if ok else "fail", "rc": rc}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devices", nargs="+", required=True)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    os.makedirs(_LOG_DIR, exist_ok=True)
    status = os.path.join(_LOG_DIR, "status.json")
    results: list[dict] = []
    n = len(args.devices)

    def save():
        with open(status, "w") as f:
            json.dump({"total": n, "done": len(results), "results": results}, f, indent=1)

    save()
    print(f"ingest start: {n} RMs, parallel={args.parallel}", flush=True)
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(_ingest, rm, args.force): rm for rm in args.devices}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            save()
            print(f"[{len(results)}/{n}] {r['rm']}: {r['status']}", flush=True)
    save()
    ok = [r for r in results if r["status"].startswith(("ok", "skipped"))]
    print(f"DONE {len(ok)}/{n} vector stores; fails: "
          f"{[r['rm'] for r in results if r['status'] == 'fail']}", flush=True)


if __name__ == "__main__":
    main()
