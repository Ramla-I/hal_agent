#!/usr/bin/env python3
"""One-command end-to-end STM pipeline driver.

RUNS ON THE HOST (not inside Docker): device registration writes the host-owned
`config_devices.json`, which the container (running as `nobody`) cannot. Per RM:

  0. (host, with --auto-register) register the device in config_devices.json if
     it is missing — the one step that must be host-side.
  1. launch s0 in the container via scripts/docker_run.sh. s0 now does EVERYTHING
     per device: preprocess (chunk -> ingest, into chunked_datasheets) -> generator
     -> constraint validation + constraints_review.jsonl -> SVD diff + bug-finding
     (structure_review.csv) -> in-process s6 (fills validator_verdict). Retrieval:
     openevolve. s0's own Step 4 (before-diff full validator) stays skipped; s6
     (in-process Step 5b) is the after-diff candidate validator that writes verdicts.

Before each RM it prints a full input/output PATH MANIFEST (every file read and
written). Bounded parallelism across RMs, one log file per RM, resume via a per-RM
done-marker (delete it or pass --force to re-run).

    python scripts/run_stm_batch.py --devices rm0530 --auto-register
    python scripts/run_stm_batch.py --devices rm0091 rm0008 --parallel 2
"""
import argparse
import glob
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_DIR = os.path.join(_REPO, "logs", "stm_batch")
_REGISTRY = os.path.join(_REPO, "config_devices.json")
_DOCKER_RUN = os.path.join(_REPO, "scripts", "docker_run.sh")


def _marker(rm: str, run: int) -> str:
    # Host-owned location: this driver runs on the HOST, but evaluation/ dirs are
    # created by the container as `nobody`, so a marker there would be un-writable.
    return os.path.join(_LOG_DIR, f"{rm}_run{run}.done")


# ---- host-side registration (R6: the container can't write config_devices.json) ----

def _registered(rm: str) -> bool:
    try:
        reg = json.load(open(_REGISTRY, encoding="utf-8"))
    except Exception:
        return False
    return any((d.get("device_name") or "").lower() == rm.lower() for d in reg.get("devices", []))


def _register(rm: str, mfr: str) -> None:
    """Append a minimal registry entry (same shape as update_config.update_device)."""
    reg = json.load(open(_REGISTRY, encoding="utf-8"))
    reg.setdefault("devices", []).append({
        "device_name": rm, "manufacturer": mfr.upper(), "peripheral_name": "",
        "driver_path": "", "run": 0, "file_id": "", "vs_id": "",
    })
    tmp = _REGISTRY + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2)
    os.replace(tmp, _REGISTRY)


# ---- path manifest: every file this process reads and writes ----

def path_manifest(rm: str, run: int, mfr: str) -> str:
    dev = f"devices/{mfr}/{rm}"
    ao = f"agent_output/{mfr}/{rm}/{run}"
    ev = f"evaluation/{mfr}/{rm}/{run}"
    ch = f"chunked_datasheets/{mfr}/{rm}/chunks"
    svds = [os.path.basename(s) for s in sorted(glob.glob(os.path.join(_REPO, dev, "svd", "*.svd")))]
    _sh = [s.replace("stm32", "").replace(".svd", "") for s in svds]
    svd_desc = (f"{len(svds)} SVD(s): " + ", ".join(_sh[:3])
                + (f" +{len(svds) - 3} more" if len(svds) > 3 else "")) if svds else "no SVDs found"

    # Group by base directory: print each prefix once, with short leaves indented
    # underneath and their descriptions aligned in a column (keeps lines short).
    def _fmt(indent, name, desc):
        base = " " * indent + name
        if not desc:
            return base
        return (f"{base:<50}{desc}" if len(base) < 49 else f"{base}   {desc}").rstrip()
    def row(name, desc=""):          # a base dir or a standalone file (indent 2)
        return _fmt(2, name, desc)
    def leaf(name, desc=""):         # a file/dir under the base above (indent 6)
        return _fmt(6, name, desc)

    return "\n".join([
        f"===== PATH MANIFEST: {rm} (run {run}) =====",
        "",
        "INPUTS (read):",
        row(f"{dev}/"),
        leaf(f"{rm}.pdf", "datasheet"),
        leaf("svd/", svd_desc),
        row("config_devices.json", "device registry"),
        row(f"devices/{mfr}/rm_device_mapping.xml", "RM -> device stems"),
        row(f"openevolve_retrieval/output_{rm}/best/best_program.py"),
        leaf("", "evolved retrieval program (or vendor default)"),
        "",
        "OUTPUTS (written):",
        row(f"{ch}/"),
        leaf("md/*.txt, md_enriched/*.txt", "datasheet chunks"),
        leaf("md/metadata.json, md/chunks_index.csv"),
        row("databases/"),
        leaf(f"{rm}_md_chunks/", "local ChromaDB (embeddings)"),
        leaf("oe_embed_cache.sqlite", "shared embedding cache"),
        row(f"{dev}/vector_stores.json", "retrieval config"),
        row(f"{ao}/"),
        leaf("<peripheral>_<register>", "per-register JSON (generator)"),
        leaf("info/", "summary.txt, usage.csv, reasoning.txt/.jsonl, embedding_ids"),
        leaf("constraint_validation/", "validated/anchors/judgments.jsonl, manifest, summary"),
        leaf("validator/", "classification.csv, usage.csv, output.txt"),
        leaf("run_manifest.json"),
        row(f"{ev}/"),
        leaf("<svd>/<svd>_structure_review.csv", "per-SVD review + analyzer_cache.json"),
        leaf(f"{rm}_structure_review.csv", "consolidated review, with verdicts"),
        leaf(f"{rm}_constraints_review.jsonl", "constraint review"),
        row("logs/stm_batch/"),
        leaf(f"{rm}.log", "run log"),
        leaf(f"{rm}_run{run}.done", "resume marker"),
        "=" * 62,
    ])


def _s0_cmd(rm: str, chunks: str) -> list:
    """Launch s0 in the container. s0 does preprocessing + generator + constraints
    (+ constraints_review) + bug-finding + in-process s6. Step 4 (before-diff full
    validator) stays skipped; s6 in-process writes the verdicts."""
    return [_DOCKER_RUN, "run", "core/s0_run_full_analysis.py", "--devices", rm,
            "--retrieval", "openevolve", "--skip-validator", "--constraint-validation",
            "--constraint-chunks-root", chunks, "--constraint-batch-size", "8"]


def _run_rm(rm: str, run: int, chunks: str, force: bool, timeout: int | None) -> dict:
    if not force and os.path.exists(_marker(rm, run)):
        return {"rm": rm, "status": "skipped_done"}
    os.makedirs(_LOG_DIR, exist_ok=True)
    log = os.path.join(_LOG_DIR, f"{rm}.log")
    cmd = _s0_cmd(rm, chunks)
    with open(log, "w") as lf:
        lf.write(path_manifest(rm, run, "stm") + "\n\n")
        lf.write(f"==== s0 :: {' '.join(cmd)}\n")
        lf.flush()
        t0 = time.time()
        try:
            rc = subprocess.run(cmd, cwd=_REPO, stdout=lf, stderr=subprocess.STDOUT,
                                timeout=timeout, start_new_session=True).returncode
        except subprocess.TimeoutExpired:
            rc = 124
            lf.write(f"---- s0 TIMEOUT after {timeout}s\n")
        lf.write(f"---- s0 rc={rc} ({time.time() - t0:.0f}s)\n")
    if rc != 0:
        return {"rm": rm, "status": "fail", "rc": rc}
    os.makedirs(os.path.dirname(_marker(rm, run)), exist_ok=True)
    with open(_marker(rm, run), "w") as f:
        f.write("ok\n")
    return {"rm": rm, "status": "ok"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devices", nargs="+", required=True)
    ap.add_argument("--run", type=int, default=1, help="run number (default 1)")
    ap.add_argument("--manufacturer", default="stm")
    ap.add_argument("--chunks", default="chunked_datasheets/stm",
                    help="constraint chunks root passed to s0")
    ap.add_argument("--parallel", type=int, default=2)
    ap.add_argument("--force", action="store_true", help="ignore done-markers, re-run all")
    ap.add_argument("--auto-register", action="store_true",
                    help="register any unregistered device in config_devices.json (host-side)")
    ap.add_argument("--timeout", type=int, default=None, help="per-RM s0 timeout in seconds")
    args = ap.parse_args()

    # Print the manifests up front (also written to each RM's log).
    for rm in args.devices:
        print(path_manifest(rm, args.run, args.manufacturer), flush=True)

    # Host-side registration, SERIAL (concurrent config_devices.json writes would race).
    for rm in args.devices:
        if _registered(rm):
            continue
        if args.auto_register:
            _register(rm, args.manufacturer)
            print(f"[register] {rm} -> config_devices.json", flush=True)
        else:
            print(f"[warn] {rm} not registered — pass --auto-register (or register manually)", flush=True)

    os.makedirs(_LOG_DIR, exist_ok=True)
    status = os.path.join(_LOG_DIR, "status.json")
    results: list[dict] = []
    n = len(args.devices)
    t_start = time.time()

    def save():
        with open(status, "w") as f:
            json.dump({"total": n, "done": len(results),
                       "elapsed_s": round(time.time() - t_start), "results": results}, f, indent=1)

    save()
    print(f"batch start: {n} RMs, parallel={args.parallel}", flush=True)
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(_run_rm, rm, args.run, args.chunks, args.force, args.timeout): rm
                for rm in args.devices}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            save()
            print(f"[{len(results)}/{n}] {r['rm']}: {r['status']}"
                  + (f" rc={r.get('rc')}" if r["status"] == "fail" else ""), flush=True)
    save()
    ok = [r for r in results if r["status"] in ("ok", "skipped_done")]
    fails = [r["rm"] for r in results if r["status"] == "fail"]
    print(f"DONE {len(ok)}/{n} ok; fails: {fails}", flush=True)


if __name__ == "__main__":
    main()
