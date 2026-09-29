#!/usr/bin/env python3
"""Step 3 — collect + lint the extracted 82599 access constraints.

Per register JSON of a run: pydantic-parse each access_constraints_v2 entry
against the grammar (defs.ConstraintV2) with PER-CONSTRAINT recovery (a bad
constraint is rejected with its error, never aborting the register), then
compute enforceability (defs.derive_enforceability — computed, never
LLM-emitted). Output: constraints/<run>_constraints.json + a printed table.

Usage: python3 collect_constraints_intel.py r006
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, REPO_ROOT)

from pydantic import TypeAdapter  # noqa: E402
import defs  # noqa: E402


def main():
    run = sys.argv[1]
    run_dir = os.path.join(HERE, "register_info", run)
    out_dir = os.path.join(HERE, "constraints")
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(HERE, "targets", "registers_join.json")) as f:
        join = {r["abbrev_base"].upper(): r for r in json.load(f)["registers"]}

    adapter = TypeAdapter(defs.ConstraintV2)
    accepted, rejected = [], []
    for fn in sorted(os.listdir(run_dir)):
        if not fn.endswith(".json") or fn.startswith("run_manifest"):
            continue
        reg = fn[:-5]
        with open(os.path.join(run_dir, fn)) as f:
            data = json.load(f)
        for i, raw in enumerate(data.get("access_constraints_v2") or []):
            try:
                c = adapter.validate_python(raw)
            except Exception as e:
                rejected.append({"register": reg, "index": i,
                                 "error": str(e).split("\n")[0][:200], "raw": raw})
                continue
            j = join.get(reg, {})
            accepted.append({
                "register": reg,
                "in_driver_set": j.get("in_driver_set", False),
                "enforceability": defs.derive_enforceability(c),
                "constraint": c.model_dump(),
            })

    out = {"run": run, "n_accepted": len(accepted), "n_rejected": len(rejected),
           "accepted": accepted, "rejected": rejected}
    out_path = os.path.join(out_dir, f"{run}_constraints.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"{run}: {len(accepted)} accepted, {len(rejected)} rejected -> {out_path}")
    from collections import Counter
    print("enforceability:", dict(Counter(a["enforceability"] for a in accepted)))
    print()
    for a in accepted:
        c = a["constraint"]
        mark = "*" if a["in_driver_set"] else " "
        print(f" {mark} {a['register']:10s} {c['kind']:14s} {a['enforceability']:16s} "
              f"{str(c.get('datasheet_text'))[:90]}")
    for r in rejected:
        print(f" REJECTED {r['register']}[{r['index']}]: {r['error'][:120]}")


if __name__ == "__main__":
    main()
