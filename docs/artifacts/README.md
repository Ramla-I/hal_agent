# `docs/artifacts/` — generated, git-ignored

Rendered pages produced by the enforcement arm's `gen_*_artifact.py` scripts.
They are derived from the current runs/measurements and drift when those change,
so they are **git-ignored** — only this README and `.gitignore` are tracked.
Regenerate on demand:

| artifact | regenerate with |
|---|---|
| `injection_tracking.{md,html}` — what each PAC enforces | `python applications/pac_codegen/experiments/gen_injection_tracking_artifact.py` |
| `constraint_validity.html` — per-manual constraint validity | `python scripts/gen_constraint_validity_artifact.py` |
| `pac_injection_cost.{html,svg}` — injection cost (source LOC vs binary) | `python applications/pac_codegen/experiments/binary_size/gen_injection_cost_artifact.py` |

The hand-authored `docs/constraint_grammar_encodings.html` is **not** here — it
has no generator and is a committed source document.
