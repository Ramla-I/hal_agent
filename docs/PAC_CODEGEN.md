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
