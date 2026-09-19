# PAC Codegen — injecting datasheet constraints into a chip crate

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
| **Chunked datasheet** | `chunked_datasheets/stm` | for `--attribution-check` (quote anchoring + target attribution) |

---

## The two constraint views (same constraints, keyed by the same `id`)

- **`validated.jsonl`** — machine output. `enforcement ∈ {enforce, doc_only, drop}`:
  - `enforce`  — judge-`confirmed` AND witness-enforceable → compile-time gated.
  - `doc_only` — genuine but not witness-enforceable, or `encoding_error`/unanchored → documented, not gated.
  - `drop`     — judge said `not_constraint`.
- **`{rm}_constraints_review.jsonl`** — the one to *go through*. Set **`tp_fp`**:
  - `"FP"` → force drop (overrides `enforce`).
  - `"TP"` → rescue a non-`enforce` row to at least doc_only.

`inject_from_run --constraints` accepts **either** file and gates codegen to
`enforce`-only, honoring `tp_fp`. So: review `_constraints_review.jsonl`, then point
`--constraints` at it.

---

## Injection workflow

1. **Review** `evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl` — set `tp_fp`
   on any you want to drop/rescue. (Optional — defaults gate on the judge alone.)
2. **Dry-run** to see the fate of every constraint without touching a crate.
3. **Inject** (drop `--dry-run`) into the target PAC crate.

`inject_from_run` internally: generator run → `collect_constraints` (lint) →
`--constraints` gate (enforce-only + `tp_fp`) → `--attribution-check` →
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
  --constraints /home/ramla/hal_agent-phase-1d/evaluation/stm/rm0316/1/rm0316_constraints_review.jsonl \
  --attribution-check /home/ramla/hal_agent-phase-1d/chunked_datasheets/stm \
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
  --constraints <eval>/stm/rm0008/1/rm0008_constraints_review.jsonl
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

---

# When one register has several rules

A register rarely arrives with exactly one rule. A manual may state two
different conditions for it; the same sentence may be extracted twice at
different precision; and every *copy* of a peripheral (I2C1, I2C2, I2C3) is
scanned separately, so one rule can arrive three times.

In Rust those copies share one piece of code — `i2c2`'s `TIMEOUTR` **is**
`i2c1::timeoutr::TIMEOUTRrs`, the same type — so gating is all-or-nothing per
register. We must settle on one answer. This section is the normative account
of how; the grammar itself is specified in
[`REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`](REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md).
The implementation is `RegisterPlan._emit_state_gate` and
`resolve_instance_collisions` in `applications/pac_codegen/rust_codegen.py`.

## The one rule

> **Rules add up. When two readings of one rule compete, the narrower one wins.**

Everything below follows from that, plus one asymmetry in why:

- **Over-gating invents a finding.** A gate the datasheet never asked for makes
  correct downstream code fail to compile, and every user pays.
- **Under-gating loses one.** A missing gate is a violation we do not catch.

They are not symmetric costs, which is why precision beats coverage at every
branch, and why genuinely contradictory evidence buys no gate at all.

## The tree

```
SEVERAL RULES FOR ONE REGISTER
│
├─ (A) they all came from ONE FILE
│      A file describes one register on one copy of a peripheral. If it lists
│      several rules, none of them are competing. Every rule applies.
│
│      ├─ every rule is about the whole register
│      │     Their conditions are collected into one list. You get a single
│      │     key for the register, and only when every condition on that list
│      │     is true at the same time. Adding a rule makes the gate stricter;
│      │     it can never make it looser.
│      │
│      ├─ every rule names specific fields
│      │     Each named field gets its own key, carrying only the conditions
│      │     of the rules that named it. A rule naming three fields gives all
│      │     three the same conditions. A field named by two separate
│      │     sentences collects the conditions of both. A field never picks up
│      │     a condition from a neighbouring field it was not named
│      │     alongside.
│      │
│      ├─ some rules are about the register and some name fields
│      │     Both kinds apply, so writing a gated field needs two keys: the
│      │     register's and the field's. This is right when the rules really
│      │     are different. On CRS_CR, the register may not be written while
│      │     CEN is set, and separately its TRIM field may not be written
│      │     while AUTOTRIMEN is set.
│      │
│      │     One exception. If a field's conditions are already included in
│      │     the register's conditions, the field's key is dropped. You cannot
│      │     reach the field without first getting the register key, and
│      │     getting it proved strictly more, so the second key would add
│      │     nothing.
│      │
│      └─ two rules ask for opposite things
│            If one rule needs a field set and another needs the same field
│            cleared, no one can ever satisfy both, so that OPERATION is
│            forbidden outright. It gets no marker and no gate, which means
│            neither modify() nor modify_witnessed() exists for the register
│            and only unsafe modify_unwitnessed can reach it. The register's
│            other operations keep their own rules.
│            fate: unsatisfiable_gate
│
└─ (B) they came from SEVERAL FILES for the same register
       In Rust, I2C1 and I2C2 and I2C3 share one piece of code, so we cannot
       gate one of them differently from another. We have to settle on a
       single answer for the register.
       │
       ├─ every file is for the SAME copy of the peripheral
       │    This happens when one register has two files, because the chip
       │    exposes it at a second address (a secure alias) or because of a
       │    naming variant: rng_htcr and rng_s_htcr.
       │    │
       │    ├─ the files quote the same sentence but read it differently
       │    │     One file listed the fields the sentence is about and
       │    │     another listed none. Keep the one with the fields. The file
       │    │     that produced no field list did not make a broader claim,
       │    │     it simply failed to work out what the sentence was about,
       │    │     so its version is discarded rather than merged in.
       │    │
       │    └─ the files quote different sentences
       │          These are different rules, so they apply together exactly
       │          as they would inside one file.
       │          fate: same_instance_rules_unioned
       │
       └─ the files are for DIFFERENT copies of the peripheral
            │
            ├─ the copies say the same thing
            │     One rule that the manual states once, which our scan picked
            │     up separately for each copy. Keep one of them.
            │
            └─ the copies say different things
                 │
                 ├─ one copy listed fields and another listed none
                 │     Keep the fields, for the same reason as above: a
                 │     missing field list is an incomplete reading, not a
                 │     wider claim. Two copies of I2C read "these bits" as
                 │     TXDATA and a third produced nothing, so TXDATA wins.
                 │     This is how most of these cases look — 104 of 127.
                 │
                 ├─ the copies each listed fields, and the lists differ
                 │     Take every field any copy named. One copy of SPI named
                 │     CRCEN and another named CRCEN and CRCL, so both are
                 │     gated. A field name has to exist on the register to get
                 │     this far, because collection checks it against the SVD,
                 │     so a name appearing in one reading and not another is
                 │     far more likely to be a field the other reading missed
                 │     than one it invented. 23 of 127.
                 │     fate: instance_merged_for_review
                 │
                 └─ the copies disagree about the conditions themselves
                       Nothing is gated, for any copy. On rm0008's USART_CR2,
                       one copy read the identical quote as being about
                       CR1.TE and another as CR1.UE. One of them is wrong and
                       nothing tells us which. Making a register harder to
                       use, on a condition we have equal reason to think is
                       the wrong one, would break correct driver code, so we
                       gate nothing instead.
                       fate: instance_conflict_dropped
```

Two rules apply whichever branch you land on.

**A rule whose condition is a field of the register it guards, and which only
software can restore, is refused.** Setting that field would lock the register
for good, because clearing it again means writing the register, and the rule
forbids that. If the *hardware* clears the field instead, there is no problem
and the rule is kept. See *Same-register refusal* below.

**Everything here has already been confirmed by the judge.** The choices above
are always between two readings the validator accepted, never between an
accepted one and a rejected one.

"Narrower" means two things, because two different questions come up:

- A reading that lists the fields a sentence is about beats one that lists
  none. The second did not make a broader claim; it failed to work out what the
  sentence covered.
- When two readings each list fields and the lists differ, only the fields both
  of them named are gated. The rest we have two readings of and no way to
  choose between.

## Worked examples

**I2C_OAR2 — why narrow must win.** *"These bits can be written only when
OA2EN = 0"* scopes to the address fields, not to `OA2EN` itself. 94 of 103
extractions in the corpus resolved it correctly to `['OA2MSK','OA2']`; 9 lost
the field list. Taking a register-wide reading gates `OA2EN` on itself: set it
once and the register can never be written again, because clearing it is a
write the gate forbids. See *Same-register refusal* below.

**RNG_HTCR — narrow wins within one copy.** Three files (`rng_htcr`,
`rng_s_htcr`, `sec_rng_htcr`), one sentence, one condition pair. Only the first
named a field. Result: `HTCFG` alone carries the gate; the two register-wide
readings are dropped.

**I2C_TXDR — narrow wins across copies.** `I2C2` and `I2C3` resolved *"these
bits"* to `TXDATA`; `I2C1` said "the whole register". Result: `TXDATA`.

**CRS_CR — both kinds, correctly.** The register may not be written while `CEN`
is set; its `TRIM` field may not be written while `AUTOTRIMEN` is set. Two
different sentences, two different conditions, so both apply and writing `TRIM`
needs both witnesses.

**USART_CR2 (rm0008) — irreconcilable.** One copy reads the identical quote as
`CR1.TE cleared`, another as `CR1.UE cleared`. One is wrong and nothing
distinguishes them. Unioning would demand a precondition the manual does not;
picking one gates on a condition we have equal reason to think is wrong. Both
are dropped.

## When rules in one file contradict each other

Case (A) pools conditions with no consistency test, so two rules that demand
opposite states of one field produce a gate that **can never be satisfied**.
`check_*_ready()` compiles, is callable, and always returns `Err` -- the
register becomes unreachable through the safe API, the same end state as the
one-way door but arrived at differently.

Eight registers in the corpus are in this state, and every one is the same
shape. `AES_IVRx` carries two correct datasheet rules:

| operation | condition | sentence |
|---|---|---|
| write | `AES_CR.EN` **cleared** | "Write operations to the AES_IVRx registers when the AES peripheral is enabled have no effect" |
| read  | `AES_CR.EN` **set**     | "These registers can be read only when AES is enabled" |

Neither is wrong. But `modify` is **derived** as the union of a register's read
and write obligations -- a modify performs both -- so it inherits `EN cleared`
and `EN set` together:

```json
"modify": ["AES_CR.EN cleared", "AES_CR.EN set"]
```

**The contradiction is manufactured by that derivation, not present in the
manual.** And the conclusion it encodes is *correct*: a read-modify-write of
`AES_IVRx` genuinely cannot be performed safely, because the read needs AES
enabled and the write needs it disabled. The register should not be
modifiable.

What was wrong is the mechanism, and it is now fixed. The operation is marked
**forbidden**: it keeps its place in the gated set so no `Unconstrained*`
marker is emitted, and the constraints module emits nothing for it, so there is
no `ModifyGate` impl either. Neither `modify()` nor `modify_witnessed()`
exists; only `unsafe modify_unwitnessed` remains. The register's read and write
keep their own correct conditions.

Detection is one pass after pooling: preconditions carry
`(source, field, kind, value)`, so two entries differing only in `kind` are
mutually exclusive by construction.

**Forbidding is not the same as freeing.** The first attempt dropped the gate
by deleting the precondition, which took the operation out of the gated set --
and a marker is added to every operation *not* in that set, so `modify` came
back as freely callable. That is strictly worse than the always-failing check
it replaced, which at least made the operation unreachable. Absence of a marker
is the gate; removing a gate must not also grant one.

### Could case (A) hold one sentence at two precisions?

Structurally yes, and there is no precision test in (A) -- the rules would
stack and the broader reading would survive. Measured across the corpus it does
not occur: **zero** files carry a register-scoped and a field-scoped rule citing
the same sentence. Within one file the generator makes a single pass over one
register and emits one constraint per sentence; duplication at differing
precision comes from *repetition* across files (a secure alias, another copy of
the peripheral), which always lands in case (B), where the test does run.

What (A) does hold, twice, is a field gate whose conditions are a **subset** of
the register gate's: `adc2/IER` (register needs `ADSTART` and `JADSTART` clear,
`JQOVFIE` needs only `JADSTART`) and `adc1/CR` (register needs seven busy flags
clear, `ADCAL` needs only `ADEN`). The field gate is then redundant -- the
accessor is unreachable without first satisfying the stricter register
condition -- and costs the caller a second witness for nothing. Suppressing a
field gate whose preconditions are a subset of its register's is not yet
implemented.

## Deduplication

Two layers, at different scopes:

| where | what | key |
|---|---|---|
| collect (`core/collect_constraints.py`) | whole constraints, before the emitter | the linted-constraint id |
| the emitter, case (A) | conditions across constraints | `(source register, field, kind, value)` |

The emitter's key is *semantic*, so the same condition phrased differently or
listed in a different order is stored once. Datasheet quotes, by contrast, are
deduplicated by **exact string**, so two extractions of one sentence differing
by a word both survive into the generated doc comment. Cosmetic — it does not
affect what is enforced — but inconsistent with `_norm_quote`, which normalises
markdown, curly quotes and articles before comparing.

## Same-register refusal

Independent of the tree, a whole-register `write`/`modify` gate whose
precondition is a field **of that same register**, restored by **software**, is
refused outright (`fate: same_register_software_gate`). It is a one-way door:
once the field leaves the required state the register can never be written
again. A hardware-restored precondition is exempt — the peripheral clears it
without our help, so the register comes back.

Two shapes produce this, and both are review outcomes rather than codegen
outcomes: an extraction that lost its field list, or a genuine lock bit, which
belongs in the `write_once` kind rather than `state_gate`.

## Known limitations

- **Ordering.** Reconciliation runs *after* the validator gate — so every
  competing plan is already judge-`enforce`, and the tie-break never chooses
  between a confirmed and an unconfirmed extraction — but *before* the
  attribution check. If the kept plan's quote fails to anchor, its gate is
  dropped and a discarded twin whose quote would have anchored is already gone.
  No case in the corpus hits this today.
- **Field-scoped read gates are not enforced.** Field gating works by adding a
  witness parameter to the *writer* accessor; a read has no writer to gate. The
  emitter warns and skips.
- **Quote-identity is textual.** `_quotes_are_one_sentence` tests containment
  of the shortest normalised quote in every other. It tolerates different
  windows around a sentence, and (since articles are normalised away) small
  function-word differences inside one — but two paraphrases of one rule still
  read as two rules.

---

# Finding violations in real code

Injecting gates into a chip crate proves nothing on its own. The finding comes
from putting real code in front of those gates and seeing what will not
compile. Every compile error is a place the code does something the datasheet
forbids.

There are two ways to get there, and which one applies is decided by a single
practical fact: **will the project build against a crate we can inject into?**

## 1. Compile it — `experiments/stm_sweep.py`

The primary finder. For each of 49 (manual, device) targets it provisions the
chip crate, snapshots it, injects, compiles a probe crate and then every
released driver crate that depends on that PAC, restores the crate, and checks
it is byte-for-byte pristine again.

The evidence is the compiler's, so a hit is a violation by construction.

The current numbers live in the artifacts, never here — this file went stale
the first time a sweep re-ran with a fix in it, and a mechanism doc that
quotes results invites exactly that. Read them from
`docs/injection_tracking.md` (regenerated by `experiments/tracking_table.py`)
or the raw `out/sweep.json` / `out/register_only/sweep.json`.

What the columns mean:

- **Guarded** — the driver already establishes the precondition in the
  enclosing function. **Candidate** — it does not; this is the findings pool.
  The split is computed by a static scan for the constraint's own precondition
  fields, resolved per peripheral (two peripherals often share a register
  *name* with different rules), and each row records whether that resolution
  was exact or fell back to a union of candidates.
- **Generic friction** — the encoding's adoption cost in code written
  generically over register types. Not a finding; measured separately in
  `docs/generic_friction.md`.
- **Collateral ("other")** — an error the encoding caused that is neither.
  This is the number to watch: it should be ~zero, and any residue should be
  explained. There is a measured noise floor here — rustc does not always
  render the witness type in the span label the classifier reads, worth about
  1 hit in 2000 (0.05%) between byte-identical runs — so a single drifting
  collateral count is the compiler, not a regression.

## 2. Read it — `experiments/scan_projects.py`

Every other candidate project pins an older HAL or PAC, so there is nothing to
compile against. This finds the same thing in source: it maps each register
access to `(peripheral, register, field, operation)`, cross-references the
constraints, and runs the **same** triage pass, so the verdicts mean the same
thing.

Per-project site counts live on the landscape artifact
(`docs/project_landscape.html`, regenerated by `experiments/landscape_page.py`)
and in `out/scan_projects.json`.

A static scan sees no runtime guards, so `unchecked` here means *we found no
check*, not *there is no check* — a guard one call frame up reads as unchecked.
Its verdicts are candidates in a stronger sense than the sweep's.

That is also why the scanner's own correctness rests on agreeing with the
compiler on a project where both can run. **That check is currently unwired**:
`stm32f4xx-hal` is not among the scanned projects, so the agreement cannot be
computed, and the landscape page says so rather than quoting the stale figure it
used to.

### How candidates are found

The project list is not a sample; it is the result of a repeatable search,
last swept 2026-09. Three passes, in decreasing order of yield:

1. **crates.io reverse dependencies** of every family PAC we inject
   (`stm32f4`, `stm32h7`, `stm32g4`, …) and of both swept drivers
   (`stm32f4xx-hal`, `stm32-hal2`). This finds published libraries. Almost
   all PAC dependents at the injectable generation are already in the sweep;
   the HAL dependents are mostly `embedded-hal` trait drivers with no
   register access at all, which is the common reason a candidate yields
   nothing.
2. **GitHub code search over `Cargo.toml`** for the pairing versions
   (`stm32f4xx-hal 0.23`, `stm32-hal2`) — this finds applications and
   firmware that never publish to crates.io, which is where the interesting
   candidates live (elodin's flight software and the blackpill application
   both came from this pass, not from crates.io).
3. Curated lists (awesome-embedded-rust and its neighbours) as a cross-check.

The inclusion bar: the project must either access registers a constraint
could reach — directly (`pac_direct`), or through a HAL we measure — or be
recorded in `EXCLUDED` with the reason it was rejected, because a project
absent from the report is indistinguishable from one that scanned clean.
Manifest facts (which PAC or HAL, which version, which features) are **read
from the project's manifests at scan time, never hand-entered** — every
hand-entered field this table ever had was eventually found wrong, including
two pinned versions and a renamed `package = "stm32-hal2"` dependency that
made a HAL invisible.

### Downstream dependents — `experiments/dependent_compile.py`

The sweep says a driver *contains* candidate sites; it says nothing about
who *compiles* them. The dependents probe answers that for the crates.io
reverse-dependents of the swept drivers. The population rule is strict:
the driver must be a **normal, non-example dependency** (a dev-dependency
pulls the driver only into the dependent's examples), and the requirement
must resolve to **the generation the sweep measured** — an older pin
contains none of the code the sites live in, so "impact" there would be a
version join. The census behind the filter is snapshotted with its
provenance in `experiments/hal_dependents_census.json`; exclusions carry
their reason in its `_meta` (the inclusion bar above, applied to a second
population).

Method is `port_blackpill`'s, generalized: a bare probe crate depends on
the dependent from crates.io, the chip crate is `[patch]`ed to a private
injected copy, the baseline must PASS against the pristine copy and the
patch is proven applied in `Cargo.lock`. Two semantics to keep straight
when reading the records (`out/dependent_*.json`):

- A bare probe instantiates no generics, so fired sites are code the
  dependent compiles **unconditionally** — a floor, not a ceiling.
- A definition-side failure on an associated-type path
  (`<<TIM as Instance>::RB as TimExt>::CPT1CRrs`) whose underlying
  register is *ungated* is **generic friction** — the driver's generic API
  needs witness bounds — not a finding. Substring spec-matching once
  recorded fourteen of these as candidate bugs, wearing ADC fields on G4
  and a JPEG quote on H7; spec matching is token-exact now
  (`tests/test_spec_match_determinism.py` pins both failure modes). The
  same path shape over a register that genuinely **is** gated (f4xx-hal's
  `UartRB` uart registers) stays enforcement, at the generic site.

One census surprise is worth naming because it reverses a ceiling claim:
embassy's own register blocks can never be gated, but its G474/G484/F334
chip features auto-enable `stm32-hrtim` on the stm32-rs PAC backend — so
an embassy build for those chips compiles a swept pairing after all, and
what injection surfaces there is the adoption cost in hrtim's generic API.

## 3. Make more of it compilable — `experiments/port_*.py`

A project that only *reads* can sometimes be made to *build*. `port_hal.py`
upgrades a community HAL to the PAC generation the injector targets, applying
only the compiler's own suggestions and failing if any edit changed a byte
beyond inserting `()`. `port_hubris.py` does the same for Hubris, whose drivers
talk to the chip crate with no HAL in between — so its errors land on Hubris's
own lines rather than inside somebody else's abstraction.

Each port writes a record the landscape renders (`out/port_hubris.json`,
`out/port_anne_key.json`, `out/port_stm32_eth.json`,
`out/port_stm32f7_discovery.json`); numbers live there.

Hubris's one confirmed hit is instructive, and the artifact records the caveat
next to the number: the site reads *corroborated* because the driver references
`UE` just before the access — but it sets it the **wrong way**, which is the
bug. A static corroboration pass checks that a precondition field is
*consulted*, never that it *holds*.

### The ports done since, and what each one established

Current per-project status lives on the landscape artifact; what belongs here
is what each port was *for*, because each answered a different question about
the pipeline itself. All of them follow the same protocol as Hubris: edits
dictated by the compiler, a **baseline that must pass against the pristine
0.16 crate before anything is injected** (otherwise a gate hit cannot be told
from a port defect), and a JSON record the landscape renders.

**`port_anne_key.py` — does the scanner agree with the compiler where it
claims hits?** anne-key drives an STM32L151 through the PAC directly, and the
scanner claimed three constrained sites, all writes to `FLASH_ACR` in one
function. The prediction, written down before building: the scanner works at
*register* granularity so it flags all three lines, but one of them writes
`ACC64` — the *precondition* — not a constrained field, so field gating should
fire on two. It fired on exactly those two, both guarded, matching the
scanner's verdict; whole-register mode fired on none, because RM0038
constrains two *fields* of ACR and says nothing about the register as a whole.
So the scanner's verdicts held and its count over-reads in precisely the
direction its granularity predicts. The port also surfaced two API findings:
PAC 0.16 collapses `EP0R`/`EP1R` into one `EPR` type, destroying a type
distinction anne-key used to give endpoint 1 different behaviour; and RTFM 0.4
cannot name any interrupt from a modern PAC (`bare_metal::Nr` vs
`InterruptNumber`), which is shimmed in a private copy of the crate.

**`port_stm32_eth.py` — does a scanner *zero* survive the compiler?** A zero
from a text matcher is the easiest number to be wrong about. stm32-eth
programs ~100 registers directly and the scan found none constrained; after
the port (really a HAL bump — the blocker was a missing `resolver = "2"`, not
the PAC), injection gates two dozen registers and the compiler confirms zero
hits in stm32-eth's own source with zero collateral. The zero is explained,
not just observed: RM0386 constrains ADC/CAN/CRYP/I2C/QUADSPI/USART-class
peripherals and stm32-eth touches ETH_MAC/ETH_DMA/ETH_PTP — no overlap.
Reading its source to port it is also what surfaced the **bit-banding
bypass** (next section).

**`port_stm32f7_discovery.py`'s record — when the gap is not the PAC.** The
scan called it `pac-gap`; a timeboxed build attempt says otherwise. The PAC
generation we inject requires Rust 1.65 / edition 2021; the project pins a
2019 nightly, and on a modern toolchain its *dependency stack* (cortex-m
0.1.8, a local crate named `core`, …) fails with dozens of errors — none of
them in the project's own source, whose register code is never compiled at
all. No toolchain builds both, so a PAC port would change nothing; the record
is kept as a blocked *attempt*, which is a more useful answer than the scan's
guess. Chasing this also exposed that the scan's pinned-version fields were
hand-entered and wrong twice; they are now read from each project's manifest.

**`port_blackpill.py` — the first whole application.** Everything above is a
library. blackpill-usb-pwdstore is a *binary* — an encrypted USB password
store on an F411 — that pins stm32f4xx-hal 0.23, the release built against
the PAC generation we inject, on stable Rust. The entire application compiles
against the injected crate with **zero mechanical edits**: the whole
experiment is one `[patch.crates-io]` line. What a hit means changes with
that: the app's own source has no direct register access, so every gate that
fires is HAL code that *this application's feature selection actually
monomorphises* — driver code its binary would contain, not driver code that
merely exists. The sweep asks "does the driver violate the rule anywhere?";
this asks "does the part of the driver this app uses violate it?" — the
question `trace_hal` approximates statically, answered by the compiler.

**No project with findings is `ready`.** Everything with findings either pins
an older PAC, needs its HAL bumped, or has no PAC at all.

That last category is the important one, and it is larger than it looks: **tock,
embassy, bxcan and fdcan together hold 86 of the scan's sites and none of them
can ever be compiled against an injected crate.** They reach real constrained
registers — bxcan's `fa1r`/`fm1r`/`ffa1r` are exactly the filter registers the
`FINIT` rule governs — but through their own register blocks, so no gate we
emit is in their path. This is the clearest statement of why the source scanner
exists, and of the ceiling on the compile-based method.

> The readiness column previously answered a different question. It inferred
> the PAC from which family's registers a project *touched*, so any crate using
> names we recognise came out injectable, and `bxcan`, `fdcan`, `stm32-fmc` and
> `lilos` were all marked `ready` with no PAC dependency at all. It now reads
> the library manifests, skipping `testsuite/`, `examples/` and
> `[dev-dependencies]` — bxcan's testsuite pins `stm32f1` 0.14 to drive
> hardware tests while the library it tests depends on `vcell` and nothing
> else.

## 4. One pairing, by hand — `experiments/hal_probe/`

A four-line crate that depends on a driver normally and swaps the chip crate
underneath with `[patch.crates-io]`. Reach for it to hold a single result: it
reports violations, generic friction and the bound cascade separately, and
`--apply-fix` discharges the friction using the compiler's own suggestions.

## 5. What the gate cannot see — `experiments/bitband_scan.py`

Everything above rests on one mechanism: enforcement is a trait bound on
`Reg<REG>`'s access methods, so the compiler checks exactly the accesses that
go *through* those methods. Two facts follow, one reassuring and one not, and
both are now tested rather than assumed.

**The reassuring one: inside the typed API, every write path is gated.** It
was not always — svd2rust also emits an *atomic* write surface behind the
`atomics` feature (`set_bits`/`clear_bits`/`toggle_bits`, a single
`atomic_or`/`and`/`xor` instead of a read-modify-write), fully typed, caller
names the field — and none of the three was in the gated-method table, so they
wrote gated registers with no bound at all. Being `unsafe` is not a gate: it
says the bit pattern may be invalid, not that the datasheet precondition
holds. That hole is closed, and `tests/test_gate_surface_complete.py` keeps it
closed structurally: it reads a *pristine* `generic.rs`, finds every public
method that can reach the register, and requires each to be gated or on an
allowlist with a stated reason — so a future svd2rust that adds a write path
fails a test instead of quietly widening the hole.

**The unclosable one: `as_ptr`.** It hands out a raw pointer; a pointer cannot
carry a trait bound, and gating it would break DMA and every legitimate
address-taking use. This is the door **bit banding** walks through. ARM maps
each peripheral bit to its own word address, and the helper drivers use takes
the register as `*const T`:

```rust
bb::set(rcc.bdcr(), 0);     // RCC_BDCR bit 0 = LSEON — never calls Reg::write
```

`rcc.bdcr()` yields `&BDCR`, which coerces to the pointer; taking a reference
is not gated, only read/write/modify are. So a write to a constrained field
can compile whatever markers the register carries — and it is not
hypothetical: stm32f4xx-hal's RTC code writes `RCC_BDCR`'s `LSEON`, `LSEBYP`
and `RTCEN` this way, fields that several F4 manuals gate on `PWR_CR.DBP set`.
Recorded as `LOST_FINDINGS.md` entry 4 — a distinct category there, since
nothing dropped these constraints; they are injected and correct, and the
driver goes around them.

`bitband_scan.py` measures the escape instead of ignoring it. It finds
`bb::set/clear/write` calls, resolves the bit number to a field through the
PAC's *own generated reader accessors* (so the bit-to-field map is the
chip's, not a guess), and cross-references the constraints. It reports three
shapes separately, because collapsing them would repeat the join-on-names
mistake: **resolved** (receiver names the peripheral, literal bit — the field
is known exactly), **bit-dynamic** (register known, bit computed — the
register's constrained fields are *listed*, never guessed), and **opaque**
(macro-generated, nothing survives — counted, never dropped, since that is
how every peripheral enable in stm32f4xx-hal's RCC is written). Current
counts live in `out/bitband_scan.json`.

**Consequence for every number above:** sweep and scan hit counts are a
**lower bound**. Every reported hit is a real compiler error; "zero hits"
means "nothing went through the gated API", not "nothing touched the
register". The scanner exists so the size of that gap is measured, not
assumed. And the drivers' own comments make the case for staying inside the
typed API — `// Set BDCR - Bit 0 (LSEON)` is a comment doing a type's job,
one register-layout change away from being silently wrong, when the typed
atomic path (`set_bits`, now gated) offers the same single-instruction write
with the field named by the compiler.

## What each of these is NOT

`patch_hal.py` was retired. It measured the adoption cost before `hal_probe`
did it better, and its `hal_constraint_violations` field read like a findings
list while containing none: it recorded every site it managed to rewrite, with
no triage, so on `stm32f4xx-hal` all seven entries were sites the driver already
guarded and none of the four real candidates appeared. `trace_hal.py` and
`scan_projects.py` now take their sites from the sweep, which carries the
verdict.
