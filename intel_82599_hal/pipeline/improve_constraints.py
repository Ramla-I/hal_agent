#!/usr/bin/env python3
"""Validate two constraint-extraction improvements on the registers whose
constraints were missed (RXCSUM, RDLEN, TDLEN, DAQF, SDPQF, RTTDCS):

  (1) prompt cues for the missed classes (alignment, init-by-software,
      RXEN-style mode gate, arbitration/ordering) — already in prompts_intel;
  (2) constraint-recall-driven context expansion (the RXCSUM note sits just
      past the base chunk boundary, so a plain re-gen wouldn't see it).

Re-generates each into a THROWAWAY dir (never the canonical runs), with +4-page
expanded context and the improved prompt, and reports which missed constraints
are now emitted + grammar-valid. --model to escalate.
"""
import json, os, sys, time, argparse
sys.path.insert(0, ".")
import s2_generate as g
from pydantic import TypeAdapter
sys.path.insert(0, g.REPO_ROOT)
import defs

MISSED = {  # register -> (cue substring to confirm recovery, expected kind)
    "RXCSUM":  ("RXEN", "state_gate"),
    "RDLEN":   ("align", "value_relation"),
    "TDLEN":   ("align", "value_relation"),
    "DAQF":    ("initialized by software", "other"),
    "SDPQF":   ("initialized by software", "other"),
    "RTTDCS":  ("ARBDIS", None),  # any ordering/state constraint beyond the read_effect
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-oss-120b")
    ap.add_argument("--extra-pages", type=int, default=4)
    args = ap.parse_args()

    regs = [r for r in g.load_targets("regs_rs")
            if r["abbrev_base"].upper() in MISSED]
    import best_program as ev
    col, proc = ev.setup_database(g.CHUNKS_DIR, g.CHUNKS_INDEX)
    full_page_ctx = g.build_page_index()
    from prompts_intel import (create_register_info_intel_system_prompt,
                               create_register_info_intel_user_prompt)
    from utils.parse_output import get_reasoning_from_response, get_json_array_from_response
    from utils.llm import call_llm
    sysprompt = create_register_info_intel_system_prompt()
    adapter = TypeAdapter(defs.ConstraintV2)

    out = {}
    for r in regs:
        base = r["abbrev_base"]
        ctx = ev.run_retrieval("82599", base, col, proc)
        ctx = g.expand_context(ctx, full_page_ctx, args.extra_pages)
        up = create_register_info_intel_user_prompt([r], [ctx])
        resp, used = call_llm(models=[args.model],
                              input=[{"role": "developer", "content": sysprompt},
                                     {"role": "user", "content": up}],
                              max_output_tokens=12000)
        _, rest = get_reasoning_from_response(resp.output_text or "")
        items = get_json_array_from_response(rest) or get_json_array_from_response(resp.output_text or "")
        cons = []
        for it in (items or []):
            if isinstance(it, dict):
                cons = it.get("access_constraints_v2") or cons
        valid = []
        for c in cons:
            try:
                adapter.validate_python(c); valid.append(c)
            except Exception:
                pass
        out[base] = valid
        time.sleep(0.5)

    print(f"\n=== recovery (model={args.model}, +{args.extra_pages} pages, improved prompt) ===")
    recovered = 0
    for base, (cue, kind) in MISSED.items():
        cons = out.get(base, [])
        hit = [c for c in cons
               if (kind is None or c.get("kind") == kind)
               and (base != "RTTDCS" or c.get("kind") != "read_effect")]
        got = bool(hit)
        if base in ("RDLEN", "TDLEN"):
            got = any(c.get("kind") == "value_relation" for c in cons)
        recovered += got
        mark = "RECOVERED" if got else "still missing"
        kinds = [c.get("kind") for c in cons]
        print(f"  {base:8s} [{mark}]  emitted kinds={kinds}")
        for c in cons:
            print(f"        {c.get('kind')}: {str(c.get('datasheet_text'))[:95]}")
    print(f"\nrecovered {recovered}/{len(MISSED)} previously-missed registers")


if __name__ == "__main__":
    main()
