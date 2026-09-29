#!/usr/bin/env python3
"""Step 2 — generate 82599 register specs from the datasheet.

Per register: vendored evolved retriever (best_program.py, the v6_82599_seed42
program) -> gpt-oss-120b (Groq) with the Intel prompt variant -> one JSON spec
per register (structure + access_constraints_v2) under register_info/<run>/.

Calling convention matches the retriever's evolution labels: peripheral_name is
the literal "82599", register_name is the Table 8-2 abbreviation base.

Config for RECALL, not precision: low-confidence specs are kept; nothing is
dropped here. Tunable knobs (recorded in the run manifest): --model,
--batch-size (registers per LLM call; contexts are deduped within a batch),
--max-output-per-reg.

Usage:
  python3 generate.py --registers rdlen,ctrl,swsm            # smoke test
  python3 generate.py                                        # all 75 regs.rs targets
  python3 generate.py --scope driver                         # only the 63 driver-needed
  python3 generate.py --resume r001                          # fill gaps in a run
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RETRIEVER_DIR = os.path.join(HERE, "retriever")
for p in (REPO_ROOT, RETRIEVER_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

DEFAULT_CHUNKS_DIR = "/home/ramla/hal_agent-retrieval/chunked_datasheets/intel/82599/chunks/md"
CHUNKS_DIR = os.environ.get("INTEL_CHUNKS_DIR", DEFAULT_CHUNKS_DIR)
CHUNKS_INDEX = os.path.join(CHUNKS_DIR, "chunks_index.csv")
TARGETS = os.path.join(HERE, "targets")
OUT_BASE = os.path.join(HERE, "register_info")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def load_targets(scope):
    with open(os.path.join(TARGETS, "registers_join.json")) as f:
        join = json.load(f)["registers"]
    with open(os.path.join(TARGETS, "datasheet_register_summary.csv")) as f:
        names = {}
        for row in csv.DictReader(f):
            base = re.sub(r"\[[^\]]*\]$", "", row["abbrev"]).strip()
            names.setdefault(base.lower(), row["name"])
    regs = []
    seen = set()
    for j in join:
        if scope == "driver" and not j["in_driver_set"]:
            continue
        base = j["abbrev_base"]
        if base.lower() in seen:
            continue          # ral/rah style duplicates cannot occur, but be safe
        seen.add(base.lower())
        regs.append({
            "field": j["field"],
            "abbrev": j["abbrev"],
            "abbrev_base": base,
            "name": names.get(base.lower(), ""),
            "section": j["section"],
        })
    return regs


def next_run_tag():
    os.makedirs(OUT_BASE, exist_ok=True)
    existing = [d for d in os.listdir(OUT_BASE) if re.fullmatch(r"r\d{3}", d)]
    n = max((int(d[1:]) for d in existing), default=0) + 1
    return f"r{n:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registers", help="comma-separated abbrev bases (smoke test)")
    ap.add_argument("--scope", choices=["regs_rs", "driver"], default="regs_rs")
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--model", default="gpt-oss-120b")
    ap.add_argument("--max-output-per-reg", type=int, default=4000)
    ap.add_argument("--resume", help="existing run tag (e.g. r001): only missing registers")
    ap.add_argument("--dry-run", action="store_true", help="retrieval only, no LLM")
    args = ap.parse_args()

    regs = load_targets(args.scope)
    if args.registers:
        want = {r.strip().lower() for r in args.registers.split(",")}
        regs = [r for r in regs if r["abbrev_base"].lower() in want]
        missing = want - {r["abbrev_base"].lower() for r in regs}
        assert not missing, f"unknown registers: {missing}"

    run_tag = args.resume or next_run_tag()
    out_dir = os.path.join(OUT_BASE, run_tag)
    info_dir = os.path.join(out_dir, "info")
    os.makedirs(info_dir, exist_ok=True)

    if args.resume:
        regs = [r for r in regs
                if not os.path.exists(os.path.join(out_dir, r["abbrev_base"].upper() + ".json"))]
        print(f"resume {run_tag}: {len(regs)} registers still missing")

    print(f"run {run_tag}: {len(regs)} registers, batch_size={args.batch_size}, "
          f"model={args.model}")

    # --- retriever setup (vendored evolved program) ---
    import best_program as ev
    assert os.path.exists(CHUNKS_INDEX), (
        f"chunks not found at {CHUNKS_DIR} — set INTEL_CHUNKS_DIR or re-chunk "
        "devices/intel/82599/82599.md with the preprocessing pipeline")
    col, proc = ev.setup_database(CHUNKS_DIR, CHUNKS_INDEX)

    from prompts_intel import (
        create_register_info_intel_system_prompt,
        create_register_info_intel_user_prompt,
    )
    from utils.parse_output import (
        get_reasoning_from_response,
        get_json_array_from_response,
    )
    from utils.llm import call_llm

    system_prompt = create_register_info_intel_system_prompt()

    # batches: keep Table 8-2 section neighbours together so contexts overlap
    regs_sorted = sorted(regs, key=lambda r: (r["section"], r["abbrev_base"]))
    batches = [regs_sorted[i:i + args.batch_size]
               for i in range(0, len(regs_sorted), args.batch_size)]

    usage_path = os.path.join(info_dir, "usage.csv")
    new_usage = not os.path.exists(usage_path)
    usage_f = open(usage_path, "a", newline="")
    usage_w = csv.writer(usage_f)
    if new_usage:
        usage_w.writerow(["registers", "model", "input_tokens", "output_tokens",
                          "total_tokens", "seconds"])

    n_ok = n_empty = n_fail = 0
    for bi, batch in enumerate(batches):
        labels = [r["abbrev_base"] for r in batch]
        contexts = [ev.run_retrieval("82599", r["abbrev_base"], col, proc)
                    for r in batch]
        for r, ctx in zip(batch, contexts):
            with open(os.path.join(info_dir, f"context_{r['abbrev_base'].upper()}.txt"),
                      "w") as f:
                f.write(ctx)
        if args.dry_run:
            print(f"[{bi+1}/{len(batches)}] {','.join(labels)}: "
                  f"{[len(c) for c in contexts]} context chars")
            continue

        user_prompt = create_register_info_intel_user_prompt(batch, contexts)
        t0 = time.time()
        try:
            response, used_model = call_llm(
                models=[args.model],
                input=[{"role": "developer", "content": system_prompt},
                       {"role": "user", "content": user_prompt}],
                max_output_tokens=args.max_output_per_reg * len(batch) + 2000,
            )
        except Exception as e:
            print(f"[{bi+1}/{len(batches)}] {','.join(labels)}: LLM FAILED: {e}")
            n_fail += len(batch)
            continue
        dt = time.time() - t0

        text = response.output_text or ""
        reasoning, rest = get_reasoning_from_response(text)
        with open(os.path.join(info_dir, "responses.jsonl"), "a") as f:
            f.write(json.dumps({"registers": labels, "model": used_model,
                                "response": text}) + "\n")
        u = getattr(response, "usage", None)
        usage_w.writerow([";".join(labels), used_model,
                          getattr(u, "input_tokens", None),
                          getattr(u, "output_tokens", None),
                          getattr(u, "total_tokens", None), f"{dt:.1f}"])
        usage_f.flush()

        items = get_json_array_from_response(rest) or get_json_array_from_response(text)
        if items is None:
            print(f"[{bi+1}/{len(batches)}] {','.join(labels)}: NO JSON ARRAY parsed")
            n_fail += len(batch)
            continue
        by_name = {}
        for item in items:
            if isinstance(item, dict) and item.get("register_name"):
                by_name[str(item["register_name"]).strip().upper()] = item
        for r in batch:
            key = r["abbrev_base"].upper()
            item = by_name.get(key)
            if item is None:
                # tolerate the datasheet abbreviation spelling
                item = by_name.get(r["abbrev"].upper())
            if item is None:
                print(f"    {key}: missing from response")
                n_fail += 1
                continue
            has_data = any(item.get(k) is not None
                           for k in ("address_offset", "reset_value", "size")) \
                       or item.get("subfields")
            item["_meta"] = {"driver_field": r["field"], "model": used_model,
                             "run": run_tag}
            with open(os.path.join(out_dir, key + ".json"), "w") as f:
                json.dump(item, f, indent=2)
            if has_data:
                n_ok += 1
            else:
                n_empty += 1
                print(f"    {key}: empty (no info found)")
        print(f"[{bi+1}/{len(batches)}] {','.join(labels)}: ok "
              f"({dt:.0f}s, out={getattr(u, 'output_tokens', '?')} tok)")

    usage_f.close()

    manifest = {
        "written_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "run": run_tag,
        "args": vars(args),
        "model": args.model,
        "retriever_sha256": sha256_file(os.path.join(RETRIEVER_DIR, "best_program.py")),
        "prompt_sha256": sha256_file(os.path.join(HERE, "prompts_intel.py")),
        "chunks_dir": CHUNKS_DIR,
        "chunks_index_sha256": sha256_file(CHUNKS_INDEX),
        "git_sha": os.popen(f"git -C {REPO_ROOT} rev-parse HEAD").read().strip(),
        "counts": {"ok": n_ok, "empty": n_empty, "failed": n_fail},
    }
    mode = "a" if args.resume else "w"
    with open(os.path.join(out_dir, "run_manifest.jsonl"), mode) as f:
        f.write(json.dumps(manifest) + "\n")
    print(f"done: ok={n_ok} empty={n_empty} failed={n_fail} -> {out_dir}")


if __name__ == "__main__":
    main()
