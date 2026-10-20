#!/usr/bin/env python3
"""Step 3 (s3) — collect + grammar-validate the extracted 82599 access
constraints from a generation run.

For every register JSON in register_info/<run>/, take each access_constraints_v2
entry and:
  1. pydantic-parse it against the grammar-v2 discriminated union
     (defs.ConstraintV2), with PER-CONSTRAINT recovery — a malformed entry is
     REJECTED with its validation error and recorded, never aborting the
     register or the run (so one bad constraint can't lose the register's good
     ones);
  2. compute its enforceability class (defs.derive_enforceability —
     action_witnessed / state_witnessed / dynamic_check / doc_only; COMPUTED
     from kind + structure, never emitted by the model);
  3. tag it with in_driver_set (whether the register is one the Theseus driver
     actually touches), joined from targets/registers_join.json.

This is SCHEMA validation only. It does NOT run the LLM Constraint Validator
(quote anchoring + target-location gate + closed-book judge in
core/constraint_validator.py) — that semantic pass was not wired for the Intel
case study (see reports/results.md).

Output: constraints/<run>_constraints.json ({n_accepted, n_rejected, accepted[],
rejected[]}) + a printed table. That file is gitignored scratch and consumed
downstream by:
  - s4_emit_hal.py --gated  (selects which state_gates become witness gates);
  - build_constraints_list.py (promotes the durable committed record
    reports/constraints_found.{json,md}).

Usage: python3 s3_collect_constraints.py r006
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
