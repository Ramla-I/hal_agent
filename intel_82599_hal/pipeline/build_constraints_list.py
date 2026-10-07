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

out = {"note": "Final 82599 constraints list (committed snapshot). Canonical run "
               "r006 grammar-valid constraints + the 5 recovered by the "
               "constraint-recall improvement. Schema-valid + computed "
               "enforceability; NOT run through the LLM constraint validator.",
       "n_total": len(found), "n_canonical": len(r006["accepted"]),
       "n_recovered": len(recovered), "constraints": found}
os.makedirs(REPORTS, exist_ok=True)
json.dump(out, open(os.path.join(REPORTS, "constraints_found.json"), "w"), indent=2)
print(f"{len(found)} constraints ({len(r006['accepted'])} canonical + {len(recovered)} recovered)")
print("wrote reports/constraints_found.json")
