# Constraint Chain Refactor — Plan (task #46)

**Status:** proposed, not started. Slot *before* the full STM run.

## Motivation

Today the constraint arm has **two parallel readers** of the generator output,
not a pipeline:

```
Generator run dir ──┬─→ Constraint Validator (s0 Step 6)  → anchors.jsonl / judgments.jsonl
                    └─→ collect_constraints (lint)        → collected per-register files + manifest
constraints_review.py joins the two by a shared sha1 id → review JSONL
inject_from_run.py: generator → collect → quote-anchor static drop → inject PAC
```

Consequences we want to fix:

1. **Wasted judgments.** The validator judges *all* raw `access_constraints_v2`
   (190 in rm0091). `collect` deterministically rejects ~29 as provably wrong
   (write-gate on read-only, value-exceeds-width, self-defeating read gate).
   Those never should reach an LLM, and the judge can even "confirm" a
   structurally-invalid constraint.
2. **Two sources of truth.** codegen and the validator read the generator
   independently and can silently diverge.
3. **Untrustworthy enforcement.** `inject_from_run`'s only validator-ish gate is
   the *static* quote-anchor drop; the **judge verdict never gates codegen**. A
   PAC crate can compile-time-enforce a constraint the judge would reject.

## Target architecture

A single chained constraint stage; codegen and review both read one artifact.

```
Generator run
  → collect_constraints   (lint + repair + enforceability; in-memory; persist manifest as audit)
  → Constraint Validator   (anchor + judge, on the LINTED set only)
  → validated store         (linted constraint ∧ enforceability ∧ anchor_tier ∧ verdict ∧ confidence)
        ├→ constraints_review.jsonl   (+ devices, + human tp_fp)
        └→ PAC codegen                (emit iff confirmed ∧ enforceable ∧ not human-FP)
```

## Calibration note (IMPORTANT — do not conflate the two validators)

- The `deployment_threshold` (STM 0.98) lives in `validator_cards/` and belongs
  to the **structure validator** (register TP/FP). It is **irrelevant here** and
  must not be reused for constraints.
- The **constraint validator is uncalibrated.** `run_judge` returns a categorical
  verdict `confirmed | encoding_error | not_constraint` + a confidence that is
  currently recorded but never thresholded. So the codegen gate is the
  **categorical `verdict == "confirmed"`**, full stop.
- Leave a `--min-confidence` hook (default `0.0`, i.e. off) on the codegen gate so
  that when constraint calibration lands (branch `constraint_validator_tuning`,
  verified-constraints datasheet) a tuned threshold can be applied without
  re-plumbing. Do **not** block this refactor on that calibration.

## The one real correctness bug this surfaces: the id scheme

Constraint id today = `sha1(rm | register | kind | datasheet_text)[:12]`. It
omits BOTH `peripheral` and `target_operation`. Measured on rm0091: 94 linted
constraints collapse to only **74 distinct old-ids** — 20 rows share an id, so
they share a single verdict and would clobber each other's human `tp_fp` label.
The dominant cause is the **omitted peripheral**: the same-named register across
peripheral instances (usart1_brr … usart8_brr — 7 rows on one id, cr1 ×6,
rtor ×5) collapses. The secondary cause is the omitted operation: collect's B.4
repair can split an `"any"` gate into read+write children that share
rm/register/kind/datasheet_text. Both were survivable in the *sibling* design
(the validator saw the raw pre-split constraint); chaining forces the fix.

**Status: DONE.** New id = `sha1(rm|peripheral|register|kind|operation|fields|text)`
→ 94 distinct ids over the 94 rm0091 constraints. Implemented in
`core/constraint_pipeline.new_constraint_id`.

Chaining also *removes the reason the id had to be reproducible across two
processes* — there is no longer a cross-process join. So:

- Mint the id **once, on the linted object**, as a content hash of the full
  normalized constraint (include `target_operation` and `target_fields`), e.g.
  `sha1(rm|register|kind|target_operation|sorted(target_fields)|datasheet_text)`.
- This is a breaking change to any stored review file keyed on the old id (only
  the rm0091 test artifact — regenerate it).

## Module boundaries / concrete changes

1. **`core/collect_constraints.py`** — expose an **in-memory API** alongside the
   CLI: `collect(run_dir, svd_dir=None) -> (linted_items, manifest)` where
   `linted_items` are the accepted, repaired, enforceability-annotated
   constraints and `manifest` is the accept/reject/flag record. Keep `main()`
   (still writes the manifest for audit; per-register payload files become
   optional, behind `--write-payload`, since the chained stage no longer needs
   them on disk). *Note:* collect's full lint needs the SVD dir — the chained
   stage must pass it (s0 Step 6 does not today).

2. **New `core/constraint_pipeline.py`** — `run_constraint_stage(run_dir,
   chunks_root, svd_dir, judge_model, batch_size, ...) -> summary`. Body:
   collect → mint ids on linted items → `anchor_row` per item → `run_judge` on
   anchored items → write the **unified artifact** `validated.jsonl` under
   `<run_dir>/constraint_validation/` (also keep `anchors.jsonl` /
   `judgments.jsonl` / `summary.json` for parity). This replaces the inline
   Step-6 body in `s0_run_full_analysis.py` (Step 6 becomes a thin call).

3. **Unified artifact schema** — `validated.jsonl`, one record per linted
   constraint:
   `{ id, rm, peripheral, register, source_file, constraint (linted RegisterInfo-
   shaped, with enforceability), lint_flags, anchor_tier, verdict, confidence,
   reason }`. Keep the constraint payload in the RegisterInfo shape so
   `rust_codegen.py` stays unchanged.

4. **`core/constraints_review.py`** — becomes a thin **formatter** over
   `validated.jsonl` (drop the two-dir join-by-id). Adds `devices` (prefilled
   from `rm_device_mapping.xml`, preserved on re-run) and the human `tp_fp`
   (preserved on re-run). Output path unchanged:
   `evaluation/{mfr}/{rm}/{run}/{rm}_constraints_review.jsonl`.

5. **`applications/pac_codegen/inject_from_run.py`** — read `validated.jsonl`
   (run the stage if absent) and apply the **codegen gate**:
   emit iff `lint=accepted ∧ enforceability ∈ {action_witnessed, state_witnessed}
   ∧ verdict == "confirmed" ∧ confidence ≥ --min-confidence ∧ human tp_fp ≠ "FP"`.
   Non-confirmed (`encoding_error` / `not_constraint` / unanchored): **drop by
   default**, or emit as `doc_only` behind `--emit-doc-only`. A human `tp_fp == "TP"`
   overrides a non-confirmed verdict (belt-and-suspenders review win).

## Testing (hermetic, stdlib)

- **id uniqueness under split-repair**: an `"any"` gate that splits into read+write
  yields two distinct ids.
- **chain end-to-end** on a fixture: a lint-rejected constraint never reaches the
  judge (assert it's absent from `judgments.jsonl` and from `validated.jsonl`).
- **codegen gate**: `encoding_error` / unanchored dropped; `confirmed ∧ enforceable`
  kept; `tp_fp == "FP"` on a confirmed row drops it; `tp_fp == "TP"` on a
  non-confirmed row keeps it.
- **review formatter**: `validated.jsonl` → review JSONL preserves `devices` /
  `tp_fp` across re-runs.
- **manifest persisted** even when payload files are not written.

## Sequencing

1. id scheme change + collect in-memory API (+ tests).
2. `constraint_pipeline.run_constraint_stage` + unified artifact; wire s0 Step 6 to it.
3. `constraints_review.py` → formatter over the artifact.
4. `inject_from_run.py` codegen gate (+ `--min-confidence`, `--emit-doc-only`).
5. Regenerate the rm0091 artifacts under the new id scheme; sanity-check counts.
6. (Later, separate) constraint-validator calibration on `constraint_validator_tuning`
   turns on a real `--min-confidence`.

## Risks / notes

- Old-id review artifacts (only rm0091 test) must be regenerated — acceptable.
- No threshold exists today, so there is nothing to recalibrate now; the gate is
  categorical. The `--min-confidence` hook is inert until calibration lands.
- collect needs the SVD dir for full lint; the chained stage must thread it
  through (a new input for the Step-6 path).
