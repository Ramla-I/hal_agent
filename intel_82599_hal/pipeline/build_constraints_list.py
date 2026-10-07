#!/usr/bin/env python3
"""Build the durable, committed final constraints list for the 82599 case study:
the grammar-valid constraints from the canonical run PLUS the constraints
recovered by the constraint-recall improvement, with verbatim datasheet quotes
and computed enforceability. Writes reports/constraints_found.{json,md}.

The per-run collection (constraints/<run>_constraints.json) and register_info
runs are gitignored scratch and non-deterministic to regenerate; this snapshot
is the committed record.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, REPO)
import defs
from pydantic import TypeAdapter

REPORTS = os.path.join(HERE, "..", "reports")
adapter = TypeAdapter(defs.ConstraintV2)

# --- canonical run r006: the 29 grammar-valid constraints ---
r006 = json.load(open(os.path.join(HERE, "constraints", "r006_constraints.json")))
found = []
for a in r006["accepted"]:
    c = a["constraint"]
    found.append({"register": a["register"], "kind": c["kind"],
                  "enforceability": a["enforceability"],
                  "datasheet_text": c.get("datasheet_text", ""),
                  "source": "run r006 (gpt-oss-120b / gpt-5.2), grammar-valid"})

# --- the 5 recovered by the constraint-recall improvement (verbatim quotes) ---
recovered = [
 {"register": "RXCSUM", "kind": "state_gate",
  "datasheet_text": "This register should only be initialized (written) when the receiver is not enabled (for example, only write this register when RXCTRL.RXEN = 0b).",
  "model": "gpt-oss-120b"},
 {"register": "RDLEN", "kind": "value_relation",
  "datasheet_text": "It must be 128-byte aligned (7 LS bit must be set to zero).",
  "model": "gpt-oss-120b"},
 {"register": "TDLEN", "kind": "value_relation",
  "datasheet_text": "It must be 128-byte-aligned (7 LS bit must be set to zero).",
  "model": "gpt-oss-120b"},
 {"register": "DAQF", "kind": "other",
  "datasheet_text": "This register must be initialized by software.",
  "model": "gpt-5.2"},
 {"register": "SDPQF", "kind": "other",
  "datasheet_text": "This register must be initialized by software.",
  "model": "gpt-5.2"},
]
# compute enforceability for the recovered ones from a minimal valid object
def enf(reg, kind, text):
    if kind == "state_gate":
        obj = {"kind": "state_gate", "severity": "error", "consequence": "",
               "datasheet_text": text, "target_register": reg, "target_fields": [],
               "target_operation": "write",
               "preconditions": [{"register": "RXCTRL", "field": "RXEN",
                                  "state": "cleared", "established_by": "software",
                                  "action_operation": "modify"}], "postconditions": []}
    elif kind == "value_relation":
        obj = {"kind": "value_relation", "severity": "warning", "consequence": "",
               "datasheet_text": text,
               "fields": [{"register": reg, "field": "LEN"}]}
    else:
        obj = {"kind": "other", "severity": "warning", "consequence": "",
               "datasheet_text": text, "description": text,
               "involved": [{"register": reg, "field": "0"}]}
    return defs.derive_enforceability(adapter.validate_python(obj))

for r in recovered:
    r["enforceability"] = enf(r["register"], r["kind"], r["datasheet_text"])
    r["source"] = f"recovered via --constraint-recall pass ({r.pop('model')}), schema-valid"
    found.append(r)

# --- accounting: everything the extraction FOUND vs. what was kept ---
#   found   = r006 raw (accepted + schema-rejected) + recovered in the later run
#   dropped = r006 constraints that failed grammar-v2 schema validation
#   kept    = r006 grammar-valid + recovered (= the list below)
dropped_regs = [r["register"] for r in r006.get("rejected", [])]
n_dropped = r006["n_rejected"]
n_kept = len(found)
n_found = len(r006["accepted"]) + n_dropped + len(recovered)   # 29 + 5 + 5 = 39

GENERATED_BY = "pipeline/build_constraints_list.py"
out = {"_generated_by": GENERATED_BY,
       "note": f"Final 82599 constraints list (committed snapshot). {n_found} "
               f"constraints were FOUND across both runs ({len(r006['accepted'])} "
               f"grammar-valid + {n_dropped} schema-rejected in canonical run r006, "
               f"plus {len(recovered)} recovered in the later constraint-recall "
               f"run). {n_dropped} were DROPPED for grammar-v2 schema "
               f"inconsistency ({', '.join(dropped_regs)}). The {n_kept} KEPT "
               f"(listed here) are schema-valid with computed enforceability; they "
               f"were NOT run through the LLM constraint validator. "
               f"Regenerate with: python3 " + GENERATED_BY,
       "n_found": n_found, "n_dropped": n_dropped, "dropped_registers": dropped_regs,
       "n_total": n_kept, "n_kept": n_kept, "n_canonical": len(r006["accepted"]),
       "n_recovered": len(recovered), "constraints": found}
os.makedirs(REPORTS, exist_ok=True)
json.dump(out, open(os.path.join(REPORTS, "constraints_found.json"), "w"), indent=2)

# --- also render the committed .md (same generator, so both stay in sync) ---
md = []
md.append("# Intel 82599 — final constraints list\n")
md.append(f"*Generated by `{GENERATED_BY}` — do not edit by hand; "
          f"regenerate with `python3 {GENERATED_BY}`.*\n")
md.append(f"**{n_found} access constraints were found** across the 75 driver-scoped "
          f"registers — **{len(r006['accepted'])} grammar-valid + {n_dropped} "
          f"schema-rejected** in the canonical run r006, plus **{len(recovered)} "
          f"recovered** in the later constraint-recall run. **{n_dropped} were "
          f"dropped** for grammar-v2 schema inconsistency "
          f"({', '.join(dropped_regs)}), leaving the **{n_kept} kept** below "
          f"({len(r006['accepted'])} canonical + {len(recovered)} recovered). Each "
          f"is schema-valid (grammar-v2) with computed enforceability. They were "
          f"**not** run through the LLM constraint validator (quote-anchor + "
          f"closed-book judge) — see results.md. The per-run collection files are "
          f"gitignored scratch; this is the durable record.\n")
md.append("| # | Register | Kind | Enforceability | Datasheet text | Source |")
md.append("|---|---|---|---|---|---|")
for i, c in enumerate(found, 1):
    q = c["datasheet_text"].replace("|", "\\|")
    q = (q[:120] + "…") if len(q) > 120 else q
    src = "recovered" if c["source"].startswith("recovered") else "r006"
    md.append(f"| {i} | {c['register']} | {c['kind']} | {c['enforceability']} | {q} | {src} |")
open(os.path.join(REPORTS, "constraints_found.md"), "w").write("\n".join(md) + "\n")

print(f"{n_found} found -> {n_dropped} dropped (schema: {', '.join(dropped_regs)}) "
      f"-> {n_kept} kept ({len(r006['accepted'])} canonical + {len(recovered)} recovered)")
print("wrote reports/constraints_found.json + .md")
