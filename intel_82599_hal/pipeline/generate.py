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


def incomplete_registers(base_dir, regs):
    """Registers to re-generate: (a) subfield bit coverage does not span 0..31
    or no subfields at all; (b) a driver-needed field (constants_map.json) is
    absent from the spec — the interface contract names the field, the bits
    still come from extraction."""
    sys.path.insert(0, HERE)
    from emit_hal import find_field
    retry = set()
    specs = {}
    regs_keys = {r["abbrev_base"].upper() for r in regs}
    for r in regs:
        key = r["abbrev_base"].upper()
        p = os.path.join(base_dir, key + ".json")
        if not os.path.exists(p):
            retry.add(key)
            continue
        with open(p) as f:
            specs[key] = json.load(f)
        sf = specs[key].get("subfields") or []
        bits = [s["bit_number"] for s in sf if s.get("bit_number")]
        hi = max((b.get("end_bit", -1) for b in bits), default=-1)
        lo = min((b.get("start_bit", 99) for b in bits), default=99)
        if not sf or hi < 31 or lo > 1:
            retry.add(key)
    cmap_p = os.path.join(HERE, "constants_map.json")
    if os.path.exists(cmap_p):
        with open(cmap_p) as f:
            cmap = json.load(f)
        for c in cmap["constants"]:
            if c["kind"] == "policy":
                continue
            key = c["register"].upper()
            # only registers in scope (regs); a key absent from `specs` because
            # it is out of scope must NOT be flagged as a driver-field miss.
            if key not in regs_keys:
                continue
            sfound, _ = find_field(specs.get(key), [c.get("field")] + c.get("alt", []))
            if sfound is None:
                retry.add(key)
    return retry


def build_page_index():
    """page_number -> ordered full text of that page's chunks."""
    pages = {}
    with open(CHUNKS_INDEX) as f:
        for row in csv.DictReader(f):
            path = os.path.join(CHUNKS_DIR, os.path.basename(row["file_path"]))
            with open(path) as cf:
                text = cf.read()
            pages.setdefault(int(row["page_number"]), []).append(
                (int(row["chunk_index"]), text))
    return {p: "\n".join(t for _, t in sorted(v)) for p, v in pages.items()}


def expand_context(ctx, full_page_ctx, extra_pages=2, cap_chars=40000):
    """Replace a retrieved context by the FULL pages it touched plus the next
    extra_pages pages — the deterministic neighbour expansion used by the
    completion pass (long register tables run past chunk boundaries)."""
    pages = sorted({int(m) for m in re.findall(r"\[Page (\d+)\]", ctx)})
    if not pages:
        return ctx
    want = sorted(set(pages) | {pages[-1] + i for i in range(1, extra_pages + 1)})
    parts = []
    total = 0
    for p in want:
        if p not in full_page_ctx:
            continue
        block = f"[Page {p}]\n{full_page_ctx[p]}"
        total += len(block)
        if total > cap_chars:
            break
        parts.append(block)
    return "\n\n---\n\n".join(parts) if parts else ctx


def next_run_tag():
    os.makedirs(OUT_BASE, exist_ok=True)
    existing = [d for d in os.listdir(OUT_BASE) if re.fullmatch(r"r\d{3}", d)]
    n = max((int(d[1:]) for d in existing), default=0) + 1
    return f"r{n:03d}"


# ---------------------------------------------------------------------------
# Completion-pass helpers (shared by --complete-from and --auto-complete)
# ---------------------------------------------------------------------------
def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def completion_targets(base_dir, regs):
    """Like incomplete_registers, but also say WHY each register is flagged.

    Returns {REG: missing_driver_field | None} — the driver-needed field name
    when that is the trigger (used for the in-context presence check), else
    None for a bit-coverage-only trigger (no single field to probe)."""
    sys.path.insert(0, HERE)
    from emit_hal import find_field
    flagged = incomplete_registers(base_dir, regs)
    out = {r: None for r in flagged}
    cmap_p = os.path.join(HERE, "constants_map.json")
    if os.path.exists(cmap_p):
        cmap = json.load(open(cmap_p))["constants"]
        for c in cmap:
            if c["kind"] == "policy":
                continue
            key = c["register"].upper()
            if key not in flagged:
                continue
            p = os.path.join(base_dir, key + ".json")
            spec = json.load(open(p)) if os.path.exists(p) else None
            sfound, _ = find_field(spec, [c.get("field")] + c.get("alt", []))
            if sfound is None and out.get(key) is None:
                out[key] = c.get("field")
    return out


def context_has_field(info_dir, reg, field, alts=()):
    """Did the saved context for `reg` already contain `field`'s row? The
    presence check that separates a generation failure (rows present -> a
    stronger model helps) from a retrieval failure (rows absent -> more pages)."""
    path = os.path.join(info_dir, f"context_{reg.upper()}.txt")
    if not os.path.exists(path):
        return False
    hay = _norm(open(path, errors="replace").read())
    for name in [field, *alts]:
        if name and len(_norm(name)) >= 3 and _norm(name) in hay:
            return True
    return False


def _driver_field_alts(reg, field):
    cmap_p = os.path.join(HERE, "constants_map.json")
    if not (field and os.path.exists(cmap_p)):
        return []
    for c in json.load(open(cmap_p))["constants"]:
        if c.get("register", "").upper() == reg.upper() and c.get("field") == field:
            return c.get("alt", [])
    return []


def prepare_completion(base_tag, regs):
    """Create a fresh run that is a copy of base_tag, and return
    (run_tag, out_dir, info_dir, regs_to_regenerate)."""
    import shutil
    base_dir = os.path.join(OUT_BASE, base_tag)
    run_tag = next_run_tag()
    out_dir = os.path.join(OUT_BASE, run_tag)
    info_dir = os.path.join(out_dir, "info")
    os.makedirs(info_dir, exist_ok=True)
    for f in os.listdir(base_dir):
        srcp = os.path.join(base_dir, f)
        if f.endswith(".json") and os.path.isfile(srcp):
            shutil.copy(srcp, os.path.join(out_dir, f))
    retry = incomplete_registers(base_dir, regs)
    regs_to_gen = [r for r in regs if r["abbrev_base"].upper() in retry]
    return run_tag, out_dir, info_dir, regs_to_gen


# ---------------------------------------------------------------------------
# One generation pass (the body main() used to inline)
# ---------------------------------------------------------------------------
def run_generation(regs, run_tag, out_dir, info_dir, *, model, max_output_per_reg,
                   extra_pages, batch_size, dry_run, append_manifest, full_page_ctx,
                   ev, col, proc, system_prompt, args_record):
    from prompts_intel import create_register_info_intel_user_prompt
    from utils.parse_output import (
        get_reasoning_from_response, get_json_array_from_response,
    )
    from utils.llm import call_llm

    regs_sorted = sorted(regs, key=lambda r: (r["section"], r["abbrev_base"]))
    batches = [regs_sorted[i:i + batch_size]
               for i in range(0, len(regs_sorted), batch_size)]

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
        if full_page_ctx is not None:
            contexts = [expand_context(c, full_page_ctx, extra_pages)
                        for c in contexts]
        for r, ctx in zip(batch, contexts):
            with open(os.path.join(info_dir, f"context_{r['abbrev_base'].upper()}.txt"),
                      "w") as f:
                f.write(ctx)
        if dry_run:
            print(f"[{bi+1}/{len(batches)}] {','.join(labels)}: "
                  f"{[len(c) for c in contexts]} context chars")
            continue

        user_prompt = create_register_info_intel_user_prompt(batch, contexts)
        t0 = time.time()
        try:
            response, used_model = call_llm(
                models=[model],
                input=[{"role": "developer", "content": system_prompt},
                       {"role": "user", "content": user_prompt}],
                max_output_tokens=max_output_per_reg * len(batch) + 2000,
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
            item = by_name.get(key) or by_name.get(r["abbrev"].upper())
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
        "args": args_record,
        "model": model,
        "extra_pages": extra_pages if full_page_ctx is not None else None,
        "retriever_sha256": sha256_file(os.path.join(RETRIEVER_DIR, "best_program.py")),
        "prompt_sha256": sha256_file(os.path.join(HERE, "prompts_intel.py")),
        "chunks_dir": CHUNKS_DIR,
        "chunks_index_sha256": sha256_file(CHUNKS_INDEX),
        "git_sha": os.popen(f"git -C {REPO_ROOT} rev-parse HEAD").read().strip(),
        "counts": {"ok": n_ok, "empty": n_empty, "failed": n_fail},
    }
    with open(os.path.join(out_dir, "run_manifest.jsonl"),
              "a" if append_manifest else "w") as f:
        f.write(json.dumps(manifest) + "\n")
    print(f"done: ok={n_ok} empty={n_empty} failed={n_fail} -> {out_dir}")
    return {"ok": n_ok, "empty": n_empty, "failed": n_fail}


# ---------------------------------------------------------------------------
# Self-escalating completion loop (the policy, in code)
# ---------------------------------------------------------------------------
def auto_complete(base_tag, regs, *, base_model, escalate_model, page_schedule,
                  max_output_per_reg, batch_size, ev, col, proc, system_prompt,
                  full_page_ctx):
    """Escalate context while it pays off; switch to a stronger model once more
    pages stop helping AND the missing rows are already in the saved context
    (a generation failure, not retrieval). Deterministic, cost-bounded by the
    page schedule + one model escalation.

      base -> [+p for p in page_schedule, same model, while misses shrink]
           -> if a page bump stops shrinking the miss set (plateau) and the
              stuck registers' rows are in context: one pass at escalate_model.
    """
    base = base_tag
    prev_miss = len(incomplete_registers(os.path.join(OUT_BASE, base), regs))
    print(f"[auto] start from {base}: {prev_miss} register(s) incomplete")
    last_pages = page_schedule[0] if page_schedule else 2

    # Phase 1 — escalate pages while they reduce the miss count.
    for p in page_schedule:
        run_tag, out_dir, info_dir, retry = prepare_completion(base, regs)
        if not retry:
            print(f"[auto] {base}: nothing incomplete — done")
            return base
        print(f"[auto] pass {run_tag}: +{p} pages, model={base_model}, "
              f"{len(retry)} register(s): {sorted(r['abbrev_base'] for r in retry)}")
        run_generation(retry, run_tag, out_dir, info_dir, model=base_model,
                       max_output_per_reg=max_output_per_reg, extra_pages=p,
                       batch_size=batch_size, dry_run=False, append_manifest=False,
                       full_page_ctx=full_page_ctx, ev=ev, col=col, proc=proc,
                       system_prompt=system_prompt,
                       args_record={"auto": True, "phase": "pages", "extra_pages": p,
                                    "from": base})
        miss = len(incomplete_registers(out_dir, regs))
        last_pages = p
        if miss == 0:
            print(f"[auto] complete at {run_tag} (+{p} pages)")
            return run_tag
        if miss < prev_miss:
            base, prev_miss = run_tag, miss           # pages still paying off
        else:
            base = run_tag                            # plateau -> stop adding pages
            print(f"[auto] plateau at {run_tag}: {miss} stuck; more pages not helping")
            break
    else:
        print(f"[auto] page schedule exhausted; {prev_miss} still incomplete")

    # Phase 2 — model escalation, only for the stuck registers whose rows are
    # already in context (otherwise it is a retrieval gap a bigger model can't fix).
    base_dir = os.path.join(OUT_BASE, base)
    base_info = os.path.join(base_dir, "info")
    targets = completion_targets(base_dir, regs)
    if not targets:
        return base
    present, absent = [], []
    for reg, field in targets.items():
        # coverage-only flags (field is None) cannot be presence-probed; give
        # the stronger model the benefit of the doubt (its job is extraction).
        if field is None or context_has_field(base_info, reg, field,
                                               _driver_field_alts(reg, field)):
            present.append(reg)
        else:
            absent.append(reg)
    if absent:
        print(f"[auto] NOT escalating {sorted(absent)} — rows absent from context "
              f"(retrieval gap; needs better chunks, not a bigger model)")
    if not present:
        return base
    regs_present = [r for r in regs if r["abbrev_base"].upper() in present]
    run_tag, out_dir, info_dir, _ = prepare_completion(base, regs)
    print(f"[auto] escalate {run_tag}: model={escalate_model}, +{last_pages} pages, "
          f"{len(regs_present)} register(s): {sorted(present)}")
    run_generation(regs_present, run_tag, out_dir, info_dir, model=escalate_model,
                   max_output_per_reg=max(max_output_per_reg, 12000),
                   extra_pages=last_pages, batch_size=batch_size, dry_run=False,
                   append_manifest=False, full_page_ctx=full_page_ctx, ev=ev,
                   col=col, proc=proc, system_prompt=system_prompt,
                   args_record={"auto": True, "phase": "escalate",
                                "model": escalate_model, "extra_pages": last_pages,
                                "from": base})
    final_miss = len(incomplete_registers(out_dir, regs))
    print(f"[auto] after escalation: {final_miss} still incomplete -> {run_tag}")
    return run_tag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registers", help="comma-separated abbrev bases (smoke test)")
    ap.add_argument("--scope", choices=["regs_rs", "driver"], default="regs_rs")
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--model", default="gpt-oss-120b")
    ap.add_argument("--max-output-per-reg", type=int, default=4000)
    ap.add_argument("--resume", help="existing run tag (e.g. r001): only missing registers")
    ap.add_argument("--complete-from", help="base run tag: ONE completion pass — copy of "
                    "base, re-generating registers with incomplete bit coverage or a "
                    "missing driver-needed field, with full-page expanded context")
    ap.add_argument("--auto-complete", help="base run tag: run the self-escalating "
                    "completion LOOP — escalate --auto-pages while they shrink the miss "
                    "set, then escalate to --escalate-model for the stuck registers whose "
                    "rows are already in context (generation failure, not retrieval)")
    ap.add_argument("--auto-pages", default="2,4",
                    help="comma-separated page schedule for --auto-complete (default 2,4)")
    ap.add_argument("--escalate-model", default="gpt-5.2",
                    help="stronger model used once more pages stop helping (--auto-complete)")
    ap.add_argument("--extra-pages", type=int, default=2,
                    help="single completion pass: pages appended past the last context page")
    ap.add_argument("--dry-run", action="store_true", help="retrieval only, no LLM")
    args = ap.parse_args()

    regs = load_targets(args.scope)
    if args.registers:
        want = {r.strip().lower() for r in args.registers.split(",")}
        regs = [r for r in regs if r["abbrev_base"].lower() in want]
        missing = want - {r["abbrev_base"].lower() for r in regs}
        assert not missing, f"unknown registers: {missing}"

    # --- shared, one-time setup (retriever DB is expensive; build it once) ---
    import best_program as ev
    assert os.path.exists(CHUNKS_INDEX), (
        f"chunks not found at {CHUNKS_DIR} — set INTEL_CHUNKS_DIR or re-chunk "
        "devices/intel/82599/82599.md with the preprocessing pipeline")
    col, proc = ev.setup_database(CHUNKS_DIR, CHUNKS_INDEX)
    from prompts_intel import create_register_info_intel_system_prompt
    system_prompt = create_register_info_intel_system_prompt()

    # ---- auto-complete: the self-escalating loop ----
    if args.auto_complete:
        page_schedule = [int(x) for x in str(args.auto_pages).split(",") if x.strip()]
        full_page_ctx = build_page_index()
        final = auto_complete(args.auto_complete, regs, base_model=args.model,
                              escalate_model=args.escalate_model,
                              page_schedule=page_schedule,
                              max_output_per_reg=args.max_output_per_reg,
                              batch_size=args.batch_size, ev=ev, col=col, proc=proc,
                              system_prompt=system_prompt, full_page_ctx=full_page_ctx)
        print(f"auto-complete finished at {final}")
        return

    # ---- single pass: base / --complete-from / --resume (unchanged behaviour) ----
    full_page_ctx = None
    if args.complete_from:
        run_tag, out_dir, info_dir, regs = prepare_completion(args.complete_from, regs)
        print(f"completion pass from {args.complete_from}: re-generating "
              f"{len(regs)}: {sorted(r['abbrev_base'] for r in regs)}")
        full_page_ctx = build_page_index()
    else:
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
    run_generation(regs, run_tag, out_dir, info_dir, model=args.model,
                   max_output_per_reg=args.max_output_per_reg,
                   extra_pages=args.extra_pages, batch_size=args.batch_size,
                   dry_run=args.dry_run, append_manifest=bool(args.resume),
                   full_page_ctx=full_page_ctx, ev=ev, col=col, proc=proc,
                   system_prompt=system_prompt, args_record=vars(args))


if __name__ == "__main__":
    main()
