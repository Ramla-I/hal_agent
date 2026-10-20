# Archived canonical run — `r006.zip`

A frozen snapshot of the **raw extraction results behind the paper's numbers**.
The live `register_info/`, `constraints/`, and `hal_out/` directories are
gitignored scratch (generation is non-deterministic — it calls an LLM), so this
archive is the durable provenance record.

**This is for archival/verification, not for re-running.** To re-run the
experiment from scratch, follow the recipe in `../../README.md` (needs the API
keys, the datasheet chunks, and the vendored retriever). An LLM re-run will not
be bit-identical; this zip is the exact `r006` the committed results came from.

## Contents

- `register_info/r006/` — the **complete final snapshot**: all 75 driver-scoped
  register JSONs + `run_manifest.jsonl` (content hashes, model, args) + `info/`.
  `r006` is the end of the completion chain (base run r003 → completion passes
  r004, r005 → gpt-5.2 escalation r006); each pass carries the full set forward
  and overwrites only the registers it regenerates, so r006 alone is everything
  the downstream tools need.
- `constraints/r006_constraints.json` — the grammar-valid collection
  (`build_constraints_list.py` reads this; also regenerable from the snapshot
  via `s3_collect_constraints.py r006`).
- `register_info/r003,r004,r005/{run_manifest.jsonl, info/usage.csv}` — the
  chain's provenance + token usage, so the cost (97 LLM calls, 693k in / 199k
  out) and the retry-cadence numbers in `reports/results.md` are reproducible.

## Unpack (to regenerate the committed artifacts offline, no API needed)

```bash
cd pipeline
python3 -c "import zipfile; zipfile.ZipFile('archive/r006.zip').extractall('.')"
# now the committed reports regenerate byte-identically:
python3 build_constraints_list.py          # reports/constraints_found.{json,md}
python3 audit_structure.py r006             # reports/audit_structure.json
python3 s4_emit_hal.py r006 --gated --extra-constraints config/recovered_constraints.json
```
