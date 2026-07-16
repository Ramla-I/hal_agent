# STM constraints corpus — stage-0 lint statistics (roadmap step E)

**Date:** 2026-07-15
**Produced by:** `applications/pac_codegen/collect_constraints.py` (grammar-v2 lift + stage-0 deterministic lint, plan §7.0), swept over the full 30-RM corpus.
**Status:** citable snapshot for the paper. Numbers regenerate deterministically from the command below; update this file when the corpus or the lint changes.

## Corpus provenance

- **Source:** `hal_agent-phase-1d/agent_output/stm/<rm>/<run>/` — 30 STM reference manuals, **32 run directories** (rm0091 has runs 1–3; every other RM has run 1).
- **Raw corpus:** **4,927 v1 constraints** in **4,107** constraint-carrying files out of **15,388** register-shaped JSON files (plan §5.1 quotes 15,422 register files; the small delta is files that are not parseable JSON dicts with an `access_constraints` key). **424** files carry `%s` placeholder names (see "%s root cause" below).
- **Collected:** 2,991 files do not validate as full `RegisterInfo` (missing/invalid layout keys) and are skipped by collection; they carry 474 constraints. Collection therefore operates on **4,453 v1 constraints** across **3,712 constrained registers** — exactly the step-D sweep number in the plan's divergence log.
- **SVDs:** `hal_agent-phase-1d/devices/stm/<rm>/svd/*.svd`, **one SVD per RM, chosen deterministically (alphabetically first)**. Every RM has at least one SVD. An all-SVDs-per-RM comparison run is reported below to quantify the selection's effect.

Reproduce (per run dir; sweep = loop over all 32):

```bash
.venv/bin/python applications/pac_codegen/collect_constraints.py \
    <phase-1d>/agent_output/stm/<rm>/<run> \
    --output-dir <tmp>/<rm>_<run> \
    --svd-dir <phase-1d>/devices/stm/<rm>/svd/<first-alphabetically>.svd
```

The sweep completed over all 32 run dirs with **zero crashes** in ~8 s.

## Headline numbers

| stage | count | note |
| --- | ---: | --- |
| raw v1 constraints (all JSON) | 4,927 | plan §5.1 baseline, matched exactly |
| v1 in `RegisterInfo`-valid files | 4,453 | collection input |
| exact duplicates dropped (within-register) | 91 (2.0%) | keep-first; see dedup section |
| **post-dedup unique v1** | **4,362** | reject-rate denominator |
| whole-constraint rejects | 1,552 (35.6%) | 28.5% with all SVDs per RM |
| **v2 constraints emitted** | **2,857** | all `state_gate` (lift-only, by construction) |
| `other`-rate | 0.0% | the lift never emits `other`; becomes meaningful at step-F re-extraction |
| repairs logged | 194 | enum-name→value, `any` expansion, whole-register flag, severity `info`→`warning`, … |

Enforceability of the 2,857 v2 gates (computed, never LLM-emitted): **2,243 `witnessed_runtime_check`** (≥1 hardware-evidence precondition), **614 `doc_only`**, **0 `compile_gate`**.

> **Correction (2026-07-16):** an earlier revision reported the 614 as `compile_gate`. That bucket is almost entirely the **vacuous** constraints (empty pre- and postconditions, 593 in corpus) which satisfied "all preconditions are software" vacuously — counting them as compile-enforceable inflated the paper metric. `derive_enforceability` now classifies condition-less gates as `doc_only`. Zero `compile_gate` is the *correct* current number: the v1 corpus carries no `evidence` field, so every lifted condition defaults to hardware evidence; genuine compile-gates (software-action ordering: UE=0, CNF set/clear, FINIT=1) appear only after step-F re-extraction emits `evidence: "software"` — which makes this row a direct measure of what step F is for.

## Exact dedup

Dedup key: (target register, operation, conditions, `datasheet_text`) — deliberately **excluding** `target_fields` (per-bit fan-out of one register-level note differs only there) and severity/consequence. Scope: **within one register file's constraint list only**; the first occurrence is kept, later ones get lint flag `exact_duplicate` + a `duplicate_of` back-reference and emit no v2.

- **91 duplicates dropped** (2.0% of 4,453).
- Constraints repeated **verbatim across a peripheral family's instances** (usart1_brr vs usart2_brr) are **not dropped** — step H emits per-instance paths, so the rows must stay separate — but are flagged `duplicate_across_instances`: **589 constraints** (13.5% of unique).

## Reject breakdown

`constraints_rejected` counts unique v1 constraints that produced **no** v2 output (1,552). The reason histogram below counts structured reject **entries** (3,195) — one constraint can have several entries, and element-level drops (postconditions) leave the constraint alive.

| reason | entries (1 SVD/RM) | entries (all SVDs/RM) | note |
| --- | ---: | ---: | --- |
| `unresolvable_in_svd` | 2,698 | 1,875 | 1,230 register-name + 1,468 field-name misses (1-SVD run) |
| `observed_state_postcondition_unenforceable` | 269 | 262 | element-level; PR 15's silently-dropped class, now loud |
| `placeholder_in_name` | 89 | 89 | `%s` files; never guessed, see root cause below |
| `write_constraint_on_read_only` | 46 | 46 | FP by construction (e.g. `FLASH_SR.BSY`, `IWDG_SR`) |
| `unparseable_required_state` | 42 | 42 | `unlocked`, `written`, `equals:X then Y`, … |
| `w1c_flag_semantics` | 34 | 41 | postconditions restating w1c flag-clear (plan §5.3 class 1: `USART_SR.TC`, `SPI_SR.CRCERR`, `WWDG_SR.EWIF`) |
| `self_defeating_read_gate` | 8 | 8 | read gates checked by reading the target (`iwdg_sr`, `sdio_sta`, `rtc_crl`) |
| `value_exceeds_field_width` | 5 | 5 | e.g. `RTC_WPR.KEY = 0xCA53` vs 8-bit field — the 0xCA→0x53 *sequence* mangled into one value; recoverable as `sequence` at step F |
| `unknown_target_operation` | 4 | 4 | `clear`, `access` drift |

**Effect of the one-SVD-per-RM selection:** whole-constraint rejects drop from 1,552 (35.6%) to 1,245 (28.5%) when resolving against *all* of an RM's SVDs — ≈307 constraints reject only because the alphabetically-first SVD lacks their peripheral/register (an RM covers several devices). `unresolvable_in_svd` therefore mixes genuinely-invented names (ranges, wildcards, pseudo-fields — plan §5.3 class 4) with device-coverage misses; the Constraint Validator (step G) sees only survivors, so this polarity is safe (false rejects lose recall, never precision — consistent with the no-recall-claim thesis).

## Lint-flag histogram (constraint-level)

| flag | count | meaning |
| --- | ---: | --- |
| `vacuous_no_conditions` | 593 | lifts fine but gates nothing (v1's "empty constraints" class — the `other`/new-kind discovery queue) |
| `duplicate_across_instances` | 589 | verbatim repeat in ≥2 instance files of one peripheral family |
| `w1c_semantics` | 184 | references a `modifiedWriteValues` flag field or a `readAction` status register |
| `cross_peripheral` | 172 | condition register lives in a different peripheral (e.g. `PWR_CR.DBP` gating RTC) — step H's work queue, **not** a reject |
| `exact_duplicate` | 91 | dropped by dedup (see above) |
| `placeholder_in_name` | 89 | `%s` in a constraint's names / source file |

Register-level: 71 collected registers flagged `placeholder_in_name`; `svd_unchecked` is zero (every RM has an SVD).

## Per-RM table (one SVD per RM, alphabetically first)

| RM / run | SVD | regs | v1 | dup | unique | v2 | rejected | reject % | top lint flags |
|---|---|---|---|---|---|---|---|---|---|
| rm0008/1 | stm32f101.svd | 71 | 82 | 1 | 81 | 52 | 30 | 37.0% | vacuous_no_conditions 14, cross_peripheral 9 |
| rm0033/1 | stm32f215.svd | 69 | 86 | 2 | 84 | 47 | 39 | 46.4% | vacuous_no_conditions 20, placeholder_in_name 2 |
| rm0038/1 | stm32l100.svd | 84 | 102 | 3 | 99 | 64 | 35 | 35.4% | vacuous_no_conditions 12, duplicate_across_instances 12 |
| rm0091/1 | stm32f0x1.svd | 6 | 7 | 0 | 7 | 5 | 2 | 28.6% | — |
| rm0091/2 | stm32f0x1.svd | 77 | 95 | 2 | 93 | 72 | 21 | 22.6% | vacuous_no_conditions 9, exact_duplicate 2 |
| rm0091/3 | stm32f0x1.svd | 116 | 133 | 0 | 133 | 98 | 35 | 26.3% | duplicate_across_instances 43, vacuous_no_conditions 8 |
| rm0313/1 | stm32f373.svd | 59 | 73 | 1 | 72 | 50 | 22 | 30.6% | vacuous_no_conditions 10, w1c_semantics 5 |
| rm0316/1 | stm32f303.svd | 61 | 67 | 1 | 66 | 34 | 32 | 48.5% | w1c_semantics 8, placeholder_in_name 6 |
| rm0360/1 | stm32f0x0.svd | 46 | 62 | 1 | 61 | 42 | 19 | 31.1% | w1c_semantics 11, vacuous_no_conditions 3 |
| rm0365/1 | stm32f302.svd | 97 | 119 | 5 | 114 | 74 | 41 | 36.0% | duplicate_across_instances 18, vacuous_no_conditions 12 |
| rm0366/1 | stm32f301.svd | 62 | 78 | 3 | 75 | 45 | 31 | 41.3% | w1c_semantics 10, duplicate_across_instances 10 |
| rm0367/1 | stm32l053.svd | 127 | 147 | 1 | 146 | 90 | 57 | 39.0% | vacuous_no_conditions 25, duplicate_across_instances 15 |
| rm0368/1 | stm32f401.svd | 57 | 71 | 2 | 69 | 37 | 32 | 46.4% | vacuous_no_conditions 12, w1c_semantics 3 |
| rm0376/1 | stm32l052.svd | 122 | 145 | 2 | 143 | 95 | 49 | 34.3% | vacuous_no_conditions 19, duplicate_across_instances 19 |
| rm0377/1 | stm32l0x1.svd | 95 | 122 | 1 | 121 | 87 | 36 | 29.8% | vacuous_no_conditions 18, w1c_semantics 17 |
| rm0383/1 | stm32f411.svd | 74 | 88 | 5 | 83 | 66 | 18 | 21.7% | duplicate_across_instances 21, vacuous_no_conditions 18 |
| rm0385/1 | stm32f745.svd | 132 | 166 | 5 | 161 | 112 | 51 | 31.7% | duplicate_across_instances 25, vacuous_no_conditions 21 |
| rm0386/1 | stm32f469.svd | 247 | 298 | 4 | 294 | 176 | 121 | 41.2% | duplicate_across_instances 51, vacuous_no_conditions 34 |
| rm0390/1 | stm32f446.svd | 87 | 113 | 3 | 110 | 77 | 33 | 30.0% | vacuous_no_conditions 17, duplicate_across_instances 16 |
| rm0394/1 | stm32l412.svd | 115 | 142 | 8 | 134 | 89 | 46 | 34.3% | duplicate_across_instances 30, vacuous_no_conditions 17 |
| rm0401/1 | stm32f410.svd | 66 | 79 | 0 | 79 | 60 | 20 | 25.3% | vacuous_no_conditions 13, duplicate_across_instances 7 |
| rm0402/1 | stm32f412.svd | 100 | 127 | 7 | 120 | 90 | 31 | 25.8% | duplicate_across_instances 25, vacuous_no_conditions 19 |
| rm0410/1 | stm32f765.svd | 287 | 322 | 3 | 319 | 173 | 148 | 46.4% | duplicate_across_instances 38, vacuous_no_conditions 33 |
| rm0430/1 | stm32f413.svd | 212 | 245 | 4 | 241 | 128 | 115 | 47.7% | duplicate_across_instances 57, vacuous_no_conditions 27 |
| rm0431/1 | stm32f722.svd | 141 | 163 | 3 | 160 | 116 | 45 | 28.1% | duplicate_across_instances 31, vacuous_no_conditions 17 |
| rm0434/1 | stm32wb35_cm4.svd | 247 | 290 | 7 | 283 | 224 | 62 | 21.9% | vacuous_no_conditions 60, duplicate_across_instances 52 |
| rm0444/1 | stm32g031.svd | 149 | 171 | 1 | 170 | 82 | 90 | 52.9% | duplicate_across_instances 52, vacuous_no_conditions 20 |
| rm0451/1 | stm32l0x0.svd | 66 | 86 | 4 | 82 | 54 | 29 | 35.4% | vacuous_no_conditions 13, w1c_semantics 11 |
| rm0454/1 | stm32g030.svd | 86 | 116 | 7 | 109 | 75 | 36 | 33.0% | duplicate_across_instances 37, w1c_semantics 14 |
| rm0490/1 | stm32c011.svd | 107 | 122 | 2 | 120 | 56 | 69 | 57.5% | vacuous_no_conditions 16, w1c_semantics 10 |
| rm0493/1 | stm32wba50.svd | 395 | 467 | 1 | 466 | 337 | 140 | 30.0% | cross_peripheral 114, vacuous_no_conditions 75 |
| rm0505/1 | stm32wb09.svd | 52 | 69 | 2 | 67 | 50 | 17 | 25.4% | vacuous_no_conditions 13, exact_duplicate 2 |

Outliers worth knowing: rm0490 (57.5% rejects — smallest SVD of a multi-device RM), rm0444 (52.9% — same cause), rm0493 (cross_peripheral 114 — a security/PWR-heavy WBA manual, step H's richest source).

## Delta vs plan §5.1 estimates

- **Raw counts match exactly:** 4,927 constraints, 4,107 constraint-carrying files (plan: same); 15,388 vs plan's 15,422 register files is a counting-method delta (parseable-JSON-with-constraints-key vs directory entries).
- **Dedup is much smaller than the plan's −36%** — by design, not by miss. The plan's 3,155-in-779-groups figure counts duplicates **across peripheral-instance files** (USART1..8); step E's dedup is scoped to one register file's list (91 dropped, 2.0%) because step H must emit per-instance paths. The cross-instance mass is preserved and *flagged* instead (589 constraints, 13.5%). The plan's ~2,551-unique figure remains the right target for the **verified-constraints datasheet** (step G dedups within RM across runs/instances).
- **`%s` constraints: 89 measured vs 96 estimated** — the plan counted on the raw corpus; collection sees only `RegisterInfo`-valid files, and 2 placeholder constraints fall into within-file dedup first.
- **Empty constraints: 593 flagged `vacuous_no_conditions` (13.6% of unique) vs the plan's 729 (15%)** — same class, smaller denominator (valid files only) plus dedup.
- **Reject rate (35.6% one-SVD / 28.5% all-SVD) vs the plan's "94% of same-register field refs resolve":** different measurements. The plan's figure checked same-register field refs against the runs' own `subfields`; stage 0 checks *every* name (target + cross-register conditions, family-form aliases) against real SVDs and additionally rejects placeholder, drift, w1c, read-only, self-defeating, and width violations. The FP classes of §5.3 that are mechanically identifiable (1, and parts of 3/4/5) are now rejected by construction; the remainder is stage-1 (LLM judge) territory.
- **`other`-rate 0.0% is structural,** not evidence of grammar coverage: the v1→v2 lift can only produce `state_gate`. The metric becomes meaningful when step-F native-v2 extraction lands.

## %s root cause

> **Resolution (Ramla, 2026-07-16): accepted as-is — no pipeline fix.** The
> verified-datasheet annotation tooling already handles `%s` dim templates
> downstream (`annotate.py` expands verified `%s` dim registers/fields on
> session exit, PR #12), and both sides of the coverage loop are consistently
> templated, so the pipeline behavior stays. For the enforcement arm,
> stage-0 lint keeps quarantining placeholder names (`placeholder_in_name`
> rejects, never guessed). The proposed fix below is retained for reference
> only, in case a future need arises to make run dirs concrete-per-instance.

**Symptom:** 424 of 15,388 run-dir register files (and 89–96 constraints) carry svd2rust `<dim>` placeholders in names — `tim3_ccr%s`, `rtc_alrm%sssr`, `dac_dhr12r%s`, `adc1_jdr%s`, `rtc_bkp%sr`. (Plan §5.1 attributes this to "derivedFrom plumbing"; the actual mechanism is SVD `<dim>` array templates — derivedFrom is unrelated.)

**Mechanism (exact path):**

1. `agent_tools/svd_parsing.py:70-77` — `get_register_names_for_peripheral()` returns the raw `<name>` text of every `<register>`. SVD array registers declare `<name>CCR%s</name><dim>4</dim><dimIndex>1-4</dimIndex>`; the function never reads `<dim>`/`<dimIndex>`, so the literal template `ccr%s` enters the returned name list. (`get_field_counts_for_peripheral()`, lines 122-133, has the same behavior.)
2. `core/s1a_generator.py:67-70` (unbatched) and `:353-357` (batched) build the register worklist from that list; `core/s1a_generator.py:84-85` (`output_filename = f"{peripheral_name}_{register_name}"`) and `:368` use the templated name for the output file, the retrieval query, and the prompt.
3. `utils/result_saver.py:86-97` — `ResultSaver.save_json()` writes the given filename verbatim (no sanitization). Sanitizing here would be wrong anyway: the dim indices are unrecoverable at write time, and stripping `%s` collides names (`rtc_alrm%sr` and `rtc_alrm%sssr` families).
4. The LLM, prompted with `ccr%s`, emits `%s` inside constraint content too (`target_register: "TIM3_CCR%s"`), which is why the corpus has placeholder *constraints*, not just placeholder *filenames*.

**Why the fix is not in this change:** the run-dir writer is only half the consumer set. The coverage loop's SVD side — `scripts/s2_compare_agent_output_with_svd.py:40-59` (`parse_svd_registers()`, used by `scripts/calculate_generator_coverage.py`) — keys registers by the **same raw template names**, so today both sides consistently use `ccr%s` and coverage math is internally coherent. Expanding the worklist alone (the only surface inside step E's allowed scope of `core/` + `utils/result_saver.py`) would write `ccr1..ccr4` run files while the comparator still expects `ccr%s`, desyncing the live coverage-improver loop — a live-run-only code path that cannot be validated offline. Per the step-E policy (don't change live-run behavior that offline tests can't prove), the behavior is left unchanged and stage-0 lint quarantines the damage: placeholder names are rejected with the structured reason `placeholder_in_name` and never guessed.

**Proposed fix (one PR, three call sites, shared helper):** implement `<dim>`/`<dimIndex>` expansion once (the semantics already exist in `applications/pac_codegen/collect_constraints.py::_expand_dim_names` — handles `1-4` ranges, comma lists like `A,B`, bare `<dim>` counts, and both `CCR%s`/`CCR[%s]` name forms) and apply it at the SVD-parsing boundary in:

1. `agent_tools/svd_parsing.py::get_register_names_for_peripheral` (+ `get_field_counts_for_peripheral`, replicating each template's field count per expanded instance), and
2. `scripts/s2_compare_agent_output_with_svd.py::parse_svd_registers` (expanding the register dict key, replicating `address_offset` per `<dimIncrement>`),

so the generator worklist, the run-dir filenames, and the coverage comparator move together. Validate with one live generator run on an affected peripheral (TIM/DAC/RTC) plus a coverage diff against a pre-fix run; expect the worklist to grow by ~3 registers per dim family (424 template files → ~1,400 concrete registers corpus-wide), which also raises per-run generator cost proportionally.
