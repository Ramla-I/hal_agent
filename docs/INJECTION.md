# Constraint Injection — Plan & File Locations

Injecting **validated register access constraints** into Rust PAC crates as
compile-time, witness-gated guarantees. This worktree (`pac-injection`) holds the
enforcement code; the **data** (bug reports + constraint files) is produced by the
STM pipeline run in the sibling `hal_agent-phase-1d` worktree.

---

## Where the data lives (produced in `hal_agent-phase-1d`)

Base: **`/home/ramla/hal_agent-phase-1d`**. These outputs are gitignored, so this
worktree references them by **absolute path**. Per RM (run `1`):

| Artifact | Path (under the base above) | What it is |
|---|---|---|
| **Constraint file (machine)** | `agent_output/stm/{rm}/1/constraint_validation/validated.jsonl` | one record/constraint: full v2 constraint + `verdict` + `enforcement` |
| **Constraint file (reviewable)** | `evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl` | same + `devices` + blank **`tp_fp`** to label |
| **SVD-bug report** | `evaluation/stm/{rm}/1/{rm}_structure_review.csv` | potential SVD/generator disagreements (`validator_verdict` = TP/FP, blank `tp_fp` to label) |
| **Generator run dir** | `agent_output/stm/{rm}/1` | one file per register (input to `inject_from_run`) |
| **SVD dir** | `devices/stm/{rm}/svd` | for collection's name/width lint |
| **Chunked datasheet** | `chunked_datasheets/stm` | for `--chunks` quote verification |

---

## The two constraint views (same constraints, keyed by the same `id`)

- **`validated.jsonl`** — machine output. `enforcement ∈ {enforce, doc_only, drop}`:
  - `enforce`  — judge-`confirmed` AND witness-enforceable → compile-time gated.
  - `doc_only` — genuine but not witness-enforceable, or `encoding_error`/unanchored → documented, not gated.
  - `drop`     — judge said `not_constraint`.
- **`{rm}_constraints_review.jsonl`** — the one to *go through*. Set **`tp_fp`**:
  - `"FP"` → force drop (overrides `enforce`).
  - `"TP"` → rescue a non-`enforce` row to at least doc_only.

`inject_from_run --validated` accepts **either** file and gates codegen to
`enforce`-only, honoring `tp_fp`. So: review `_constraints_review.jsonl`, then point
`--validated` at it.

---

## Injection workflow

1. **Review** `evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl` — set `tp_fp`
   on any you want to drop/rescue. (Optional — defaults gate on the judge alone.)
2. **Dry-run** to see the fate of every constraint without touching a crate.
3. **Inject** (drop `--dry-run`) into the target PAC crate.

`inject_from_run` internally: generator run → `collect_constraints` (lint) →
`--validated` gate (enforce-only + `tp_fp`) → `--chunks` quote re-verification →
inject via `rust_codegen`. Fates in the report: `planned`, `gated_out_by_validator`,
`kind_not_emitted`, `rejected_at_collection`, `peripheral_not_in_device`, etc.

### Sample command (dry-run first)

```bash
cd /home/ramla/hal_agent-pac-injection
python applications/pac_codegen/inject_from_run.py \
  /home/ramla/hal_agent-phase-1d/agent_output/stm/rm0316/1 \
  --device stm32f303 \
  --pac <path/to/pac-crate> \
  --svd-dir /home/ramla/hal_agent-phase-1d/devices/stm/rm0316/svd \
  --validated /home/ramla/hal_agent-phase-1d/evaluation/stm/rm0316/1/rm0316_constraints_review.jsonl \
  --chunks /home/ramla/hal_agent-phase-1d/chunked_datasheets/stm \
  --report /home/ramla/hal_agent-pac-injection/reports/rm0316.json \
  --dry-run
```

- `--device` is the PAC device module; STM RM→device names come from
  `devices/stm/rm_device_mapping.xml` (e.g. rm0316→`stm32f303`; rm0008→
  `stm32f101/f102/f103/f107`).
- `--pac` is **your input**: the PAC crate to inject into.
- Whole-register gating is default; field-level is opt-in via `--field-level-gating`.

---

## Ready to inject now (grows as the pipeline completes; from `hal_agent-phase-1d`)

| RM | device(s) | SVD-bug rows | constraints |
|---|---|---|---|
| rm0091 | stm32f0x1/x2/x8 | 472 | 112 |
| rm0316 | stm32f303 | 424 | 73 |
| rm0360 | — | 182 | 80 |
| rm0313 | — | 330 | 62 |
| rm0008 | stm32f101/2/3/107 | 303 | 62 |
| rm0365 | — | 274 | 56 |
| rm0038 | — | 286 | 53 |
| rm0368 | — | 233 | 54 |
| rm0033 | — | 330 | 51 |
| rm0366 | — | 179 | 36 |

(Check `hal_agent-phase-1d/logs/stm_batch/status.json` for the live list; the full
STM run adds RMs as they finish.)

---

## What injection actually changes in a PAC crate

Every figure below is from diffing a pristine `stm32f1` 0.16.0 against the
same crate after injecting RM0008 into `stm32f103` (6 registers gated, 1608
files changed). Reproduce with:

```bash
python applications/pac_codegen/get_pac.py --crate stm32f1 --version 0.16.0 --force
cp -r applications/pac_codegen/vendored/pac/stm32f1 /tmp/pristine_f1
python applications/pac_codegen/inject_from_run.py \
  <run_dir>/agent_output/stm/rm0008/1 \
  --pac applications/pac_codegen/vendored/pac/stm32f1 --device stm32f103 \
  --svd-dir <devices>/stm/rm0008/svd/stm32f103.svd \
  --validated <eval>/stm/rm0008/1/rm0008_constraints_review.jsonl
diff -rq /tmp/pristine_f1 applications/pac_codegen/vendored/pac/stm32f1
```

| # | Where | Change | Why |
|---|---|---|---|
| 1 | `src/generic.rs` | Add 3 marker traits — `UnconstrainedRead` / `UnconstrainedWrite` / `UnconstrainedModify` | The **absence** of a marker is the gate |
| 2 | `src/generic.rs` | Add 3 gate traits — `ReadGate` / `WriteGate` / `ModifyGate`, each with `type Witness` | Binds a witness type to a constrained register |
| 3 | `src/generic.rs` | Add `REG: UnconstrainedWrite` (etc.) bounds to the **existing** `read`/`write`/`modify`/`reset` | Makes the ordinary API refuse a gated register — this is what produces the compile error |
| 4 | `src/generic.rs` | Add `*_witnessed` and `*_when_ready` methods | The sanctioned way to perform a constrained operation |
| 5 | `src/generic.rs` | Add `unsafe *_unwitnessed` | Acknowledged bypass, like `unsafe` anywhere else |
| 6 | Every register file in the injected device — **363** | Append `impl crate::Unconstrained{Read,Write,Modify} for <Spec> {}` for each operation *not* constrained | Unconstrained registers keep the ordinary API |
| 7 | The gated register files — **6** | **Omit** the marker for the constrained operation | The gate itself |
| 8 | The gated register's peripheral module — **2** | Append `pub mod constraints`: witness structs, a `ConstraintError` enum, the gate impls, and `check_*_ready()` | The runtime check that reads the source register and mints a witness |
| 9 | Every *other* device module — **1242** | Append all three markers to every register | A sibling chip must not inherit another chip's datasheet |
| 10 | *(opt-in, `--field-level-gating`)* Field writer accessors | `pub fn <field>(&mut self)` gains a `&<Field>Witness` parameter | Field-level gating |

### The gate is a subtraction

```rust
// can/fa1r.rs — gated: write and modify markers withheld
impl crate::UnconstrainedRead for FA1Rrs {}

// tim1/cr1.rs — unconstrained: ordinary API intact
impl crate::UnconstrainedRead for CR1rs {}
impl crate::UnconstrainedWrite for CR1rs {}
impl crate::UnconstrainedModify for CR1rs {}
```

### The check carries the datasheet sentence

```rust
/// This register can be written only when the filter initialization
/// mode is set (FINIT=1) in the CAN_FMR register.
pub fn check_write_ready(&self, fmr: &crate::Reg<super::fmr::FMRrs>)
    -> Result<Fa1rWriteWitness, Fa1rConstraintError> {
    let r_fmr = fmr.read();
    if !(r_fmr.finit().bit_is_set()) {
        return Err(Fa1rConstraintError::FmrFinitNotSet);
    }
    Ok(Fa1rWriteWitness { _priv: () })
}
```

### Two properties worth stating

**Almost every edit is the null change.** 1605 of 1608 files only receive
markers saying *unconstrained*, and 1242 of those are in sibling device
modules the selected cargo feature never compiles. Two files gain real logic;
six have a marker withheld. The technique is subtractive — the interesting
change is what is missing.

**No existing code is rewritten.** Every change is an append, except the trait
bounds added to `generic.rs`'s existing methods. Register layouts, field
accessors, addresses and reset values are untouched, which is what makes "the
driver's behaviour is unchanged" a structural property rather than a claim.

For *why* trait-bound gating rather than shadowing, see
`docs/register_constraints_plan.md` Appendix A.

## Notes

- Constraint-validator verdicts are the judge's categorical call (uncalibrated;
  no confidence threshold yet). `inject_from_run --min-confidence` is available but
  inert until constraint calibration lands (branch `constraint_validator_tuning`).
- The design/mechanics: `docs/register_constraints_plan.md` (§3, Appendix A) and
  `docs/constraint_chain_refactor_plan.md` (the chained validated.jsonl this consumes).
