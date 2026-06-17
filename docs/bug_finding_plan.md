# Phase 1d — Bug-Finding Driver Plan

**Status:** authoritative spec for Phase 1d (continuous end-to-end STM bug runs). Defined collaboratively with Ramla 2026-06-15 (no paper section — this doc IS the spec).
**Worktree:** `/home/ramla/hal_agent-phase-1d` (branch `phase-1d-stm-e2e-runs`).
**Rule:** implement to this spec; if implementation diverges, log it in the "Divergence log" at the bottom. At phase end this file is the record of what we built and why it differs from the plan.

## Goal
Keep shipping merge-validated SVD bugs on STM while the rest of the infra improves. Per STM device: run the Generator → diff generated register info against the ground-truth SVD → filter to real SVD bugs → **group bugs into classes** → emit a **CSV per SVD file** for human review. Nothing is submitted upstream automatically; the human reviews the CSV and (later) a separate step turns approved classes into PRs.

## Locked decisions (Ramla, 2026-06-15)
1. **Devices:** start with STM devices that have **no verified slice** — `rm0091`, `rm0360`, `rm0490`. (rm0041/rm0090 are the verified dev slices, reserved for 1b/eval.)
2. **Retrieval:** use the **OpenEvolve-evolved STM retrieval** for these devices — `ContextRetrievalMethod.OPENEVOLVE` with `oe_program_path` → the evolved STM best program (`openevolve_retrieval/output_<stm-device>/best/best_program.py`; default rm0041 if device-specific evolution absent).
3. **PR granularity:** by **bug class**, optimized for reviewer ease.
4. **Output:** one **CSV per SVD file** (review queue). No git/`gh` automation in this cut.
5. **Validator vs Analyzer:** the **s4 Validator is out of scope** (not invoked). The **s5 Analyzer IS used** as the SVD-bug filter (confirmed Ramla 2026-06-15) — it separates real SVD bugs from generator errors; its output is the valid-bug set we group.
6. **Engineering latitude:** free to rewrite/improve anywhere (core stages, bug-finding app, interfaces, data structures). Reduce CSV sprawl; code must be clean, readable, maintainable.

## Prerequisites (fresh clone — must be satisfied before a live run)
- Device assets restored: `scripts/unpack_device_assets.py` (needs `gh auth login`) → `devices/stm/{rm0091,rm0360,rm0490}/*.pdf` + `svd/*.svd`.
- Local vector DB per device: `scripts/docker_run.sh preprocess devices/stm/<dev>/<dev>.pdf <dev>` → `chunked_datasheets/` + `databases/`.
- An evolved STM OpenEvolve program present under `openevolve_retrieval/output_*/best/`.
- `.env` (OPENAI + GROQ) — already present in this worktree. Pipeline runs via `scripts/docker_run.sh` (Docker can't run inside the sandbox → those calls disable the sandbox / prompt; expected).

## Current data flow (as-is, from code map)
- **Generate:** `core/s1a_generator.py` → one `{peripheral}_{register}` JSON per register (serialized `defs.RegisterInfo`) in `agent_output/.../{run}/`.
- **Diff:** `scripts/s2_compare_agent_output_with_svd.py:compare_agent_output_with_svd()` → writes `register_diff.csv` (`id,peripheral,register,key,just_svd,just_output,both`), `field_diff.csv` (+`field_name`), and 3 `*_summary.csv` coverage files into `evaluation/{mfr}/{dev}/{run}/{svd}/`.
- **Analyze:** `core/s5_analyzer.py:run_analyzer()` reads `register_diff.csv`, LLM-classifies rows, emits JSON `{"bugs":[row_ids]}` = the **valid SVD-bug rows** (drops agent errors / acceptable variations). s0 then filters `register_diff.csv` → `register_diff_analyzer.csv`.
- **Report (existing, partial):** `bug_reports/create_bug_report.py` formats `Bug=1` rows into `bug_report.csv` (`SVD File, Crate, RM, Bug Description, PR, Status`), dedup-merging.
- **No existing:** per-device bug-finding driver, bug-class grouping, SVD patch generation.

## Proposed architecture (target)

### New typed models (in `defs.py` or a new `applications/bug_finding/models.py`)
Replace the intermediate `register_diff.csv` / `field_diff.csv` round-trips with in-memory Pydantic types:
- `RegisterDiff` / `FieldDiff` — one structured diff record (peripheral, register, [field], key, svd_value, generator_value, present_in).
- `Bug` — a confirmed SVD-bug diff (the analyzer-kept rows) + datasheet evidence (page/snippet) + confidence + proposed SVD value.
- `BugClass` — a reviewer-facing group of `Bug`s keyed by **(svd_file, key/bug-type, peripheral)** → maps 1:1 to a future PR.

### New package `applications/bug_finding/`
- `diff.py` — in-memory compare: SVD (via `agent_tools/svd_parsing.py`) vs generator JSON (via `utils.generator_facts.convert_generator_register_to_svd_like`), returning `list[RegisterDiff]`/`list[FieldDiff]` (no CSV). Move `scripts/s2_compare_agent_output_with_svd.py`'s core logic here.
- `classify.py` — take analyzer-confirmed bug diffs → group into `BugClass`es. (reset_value bugs cluster & merge well; structural bit_offset/bit_width/address_offset are higher-impact but merge less — see baseline.)
- `report.py` — emit one review CSV per SVD file (schema below).
- `pipeline.py` / `driver.py` — `find_bugs(device) -> list[BugClass]`: orchestrate generate → diff → analyze → classify → report. CLI: `python -m applications.bug_finding.driver --device rm0091`.

### CSV reduction plan
- **Eliminate as files:** `register_diff.csv`, `field_diff.csv` (become in-memory typed diffs); the 3 `*_summary.csv` (compute on demand). Refactor `core/s5_analyzer.py` to accept in-memory diffs, and **update `core/s0_run_full_analysis.py` to use the new typed path directly** — NO parallel/old-CSV compat path to maintain (confirmed Ramla 2026-06-15). Do NOT touch the s4 validator (`core/s4_validator.py`, `prompts/validator.py`).
- **Keep as files (boundaries/outputs):** the per-SVD review CSV; optionally a roll-up `bug_report.csv` (reuse/extend `bug_reports/create_bug_report.py`).

### Review CSV schema (per SVD file) — draft, tune for reviewers
`bug_class_id, svd_file, peripheral, register, field, key, svd_value, generator_value, proposed_svd_fix, datasheet_evidence (page/snippet), confidence, status`
- `proposed_svd_fix` is **pre-filled with the generator's value** so approval is a one-click confirm.
- **False-positive catcher (Ramla 2026-06-15):** the reviewer reads `datasheet_evidence` next to `generator_value`; if the generator's value doesn't actually match the datasheet, the row is a **generator error, not an SVD bug** → mark `status=false_positive`. These are worth recording (a signal on generator quality / FP rate), so the CSV retains them rather than dropping them.
- Rows grouped/sorted by `bug_class_id`; one class → one prospective PR.
- `status` ∈ {blank, `approve`, `reject`, `false_positive`}; blank initially; a later submit step consumes only `approve` classes.

## Boundaries & merge discipline
- All edits inside this worktree. Sandbox hard-denies editing `-1b` and main. The s4 validator is additionally denied here (clean 1b/1d separation) — and is out of scope anyway.
- 1b touches only validator files; 1d touches generator/diff/analyzer/new app → **no overlap with 1b**, so the two branches merge cleanly.
- Keep `s0_run_full_analysis.py` working after any core refactor (thin compat shims).
- **Issue #2** (dedup `split_peripheral_register`/`_load_register_info`): 1d will naturally touch these load sites — fold the dedup into the new `applications/bug_finding/` interfaces where it helps, but leave the main-repo-wide consolidation to a post-merge pass on `main` to avoid churn.

## Resolved decisions (Ramla 2026-06-15)
- **A1 (analyzer):** ✅ Use the s5 Analyzer as the SVD-bug filter; exclude only the s4 Validator.
- **A2 (refactor depth):** ✅ Refactor `scripts/s2_*` + `core/s5_analyzer.py` to typed in-memory interfaces AND update `s0` to use them directly. No parallel/old-CSV path to maintain.
- **A3 (proposed fix):** ✅ Pre-fill `proposed_svd_fix` with the generator value; reviewer confirms. A generator/datasheet mismatch = false positive → `status=false_positive`, kept in the CSV as a noted FP.

## Divergence log
_(empty — append a row whenever implementation departs from this spec.)_

| Date | Plan said | We did instead | Why | Impact |
|------|-----------|----------------|-----|--------|
| 2026-06-17 | Two types `RegisterDiff` / `FieldDiff` | One unified `Diff` with optional `field` (register-level = `field is None`) | Removes near-duplicate handling in classify/report; one code path. Approved by Ramla. | `models.Diff`; field-level diffs carry `field`, register-level leave it None. |
| 2026-06-17 | "Keep diff_table / verified-comparison scripts on disk (revivable)" (verbal #3) | **Deleted** `scripts/s2_compare_agent_output_with_svd.py`, `scripts/s4_generate_diff_table.py`, `scripts/s5_compare_diff_with_verified_output.py` | Discovered they were dead except s0 (the harness imported them but never called them). Deleting fully realizes "kill the CSVs." Approved by Ramla. | Verified-slice eval (diff tables, verified compare) no longer runs in s0; recover from git history if needed. Coverage for the CI loop is unaffected (`calculate_generator_coverage` is in-memory). |
| 2026-06-17 | s5 Analyzer kept as the SVD-bug filter | Analyzer rewritten to (a) consume `list[Diff]` in memory, (b) run via `client.responses.create()` so `model_name` actually selects the model, (c) return per-bug **confidence**. | Old analyzer used the agents SDK without setting a model → silently ran on the SDK default, ignoring the requested model. New path is consistent with generator/validator and grounds the review CSV's `confidence` column. | `classify.run_analyzer(client, model_name, ...)`; analyzer now controllable + synchronous. |
| 2026-06-17 | `datasheet_evidence (page/snippet)` in the review CSV | Evidence sourced from the generator's per-register reasoning (new `info/reasoning.jsonl`), flattened into one cell; no page/snippet extraction and no extra LLM call. | The analyzer has no datasheet access; the generator's reasoning is the cheapest datasheet-grounded evidence. | `generator` writes `reasoning.jsonl`; `classify.attach_evidence` fills the column (peripheral fallback for batched runs). |
| 2026-06-17 | (cross-cutting cleanups, latitude #6 / Ramla request) | Config device registry moved to `config_devices.json` + robust `update_config`; dropped dead `UserContext.vs_id_text/vs_id_md`; logger centralized on the root logger with a console switch; `ResultSaver.aggregate` + single-open CSV; generator dedup + hoisted imports. | Reduce sprawl; make config updatable without regex-on-source; surface logs on console during runs. | Transparent to `config.user_contexts` consumers; `setup_logger` callers unchanged. |
