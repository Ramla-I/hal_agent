# Register Constraints — Full Plan (grammar v2, encoding, PR 15, extraction quality, validator)

**Status:** DRAFT for Ramla's review — nothing here is implemented yet.
**Date:** 2026-07-15
**Scope:** the enforcement arm (Phase 4): constraint grammar, PAC codegen encoding, PR 15 disposition, extraction quality on the STM corpus, and constraint validation without a verified-constraint datasheet.
**Inputs:**

- PR #15 (`cursor/stabilize-pac-codegen`, 7 commits `c44dd07..b1cfa6f`) — reviewed via multi-agent deep-read + two adversarial judges; load-bearing claims **compiler-verified** against a real svd2rust-generated `stm32f4` 0.16.0 PAC.
- Extracted-constraints corpus: `hal_agent-phase-1d/agent_output/stm/<rm>/<run>/` — 4,927 constraints across 30 STM reference manuals (note: `evaluation/` holds layout diffs, not constraints).
- Curated example set: 33 constraints across 14 categories (scratchpad `curated_stm_constraint_examples.json`; all re-derivable from the sources cited in §5.2).

---



## 0. Goal and the hard design condition

Turn datasheet access/ordering constraints (which SVDs cannot express) into compile-time enforcement inside PAC crates.

**Hard condition:** constrained PAC crates must be usable **as-is** by any upper-level crate (HAL, driver, app) — a normal cargo dependency, no consumer build steps — and violations must surface as **compile-time errors in the upper-level crate**. An explicit `unsafe` escape hatch is acceptable. Runtime cost only where a witness about hardware-controlled state genuinely requires a check.

---



## 1. Where we are



### 1.1 Baseline (main)

`rust_codegen.py` swaps a constrained register's type alias to `ConstrainedReg<REG>` (Deref → `Reg`) and adds inherent `write`/`modify` shadows that demand per-field witness tokens, so a token-less `cr1().write(f)` fails with E0061. It handles only same-register preconditions on `target_operation="write"`; it silently drops postconditions, cross-register references, `target_fields`, and `severity`.

### 1.2 What PR 15 adds

- **Composite per-(register, operation) tokens** minted from a **single fresh read** (`verify_write_ready() -> Cr1WriteReady`; the PR calls these "proofs" — we rename to **witnesses**, see §3) — replaces per-field tokens; prevents cross-read staleness and cross-operation authorization. *Keep.*
- **Full write-surface gating**: `write`/`reset`/`write_with_zero`/`from_write` on the write witness; `modify`/`from_modify` on a modify witness; `read` on a read witness. *Keep — closes real holes.*
- **Schema:** `FieldState.evidence_kind: Literal["observed_state","software_action"]` + `action_operation`, with backward-compatible defaults. *Keep the fields; the dichotomy is correct and not inferable by codegen (only prose says whether hardware or software establishes a state).*
- **Action-derived witnesses** (`set_x() -> Token`) and `#[must_use]` cleanup obligations carrying the operation's return value; cross-register checks as free functions; grouped peripheral generation + `manifest.json` in `collect_constraints.py`; honest doc retreat from "linear" to "affine". *Mixed — see §2.*
- Prompt + consistency-test updates for the new fields. *Decouple — see §2/§6.*

---



## 2. PR 15 verdict: right direction, not mergeable as-is

All findings below were verified by generating against the real PAC and running `cargo check` on adversarial programs (branch file:line refs).

1. **The emitted Rust does not compile.** The safe `write_with_zero_constrained` calls `Reg::write_with_zero`, which is `unsafe fn` in svd2rust 0.36.1 and 0.37.1 → E0133 inside the PAC (`rust_codegen.py:682-694`; the committed golden contains the same defect). Nothing the PR generates can currently build.
2. **Safe, silent bypass via** `Deref`**.** `let r: &Reg<CR1rs> = i2c1.cr1(); r.write(f)` compiles clean — no `unsafe`, no warning. The gate is method-resolution shadowing only; type ascription, `&`**, UFCS, or any function generic over `Reg<REG>` reaches the stock API. This violates the hard condition and makes `unsafe bypass_constraints()` ceremonial.
3. **Enforcement has never been proven.** All four cargo tests silently `SKIP` (no CI; submodule ships SVDs, not generated source), so the cross-register and action-chain Rust has never been through rustc. Golden-file diffs are change detectors, not correctness guards — which is exactly how defect 1 shipped.
4. **Witnesses are not instance-bound.** stm32f405 shares the `i2c1` module across I2C1/2/3, so a witness from I2C1 authorizes a write to I2C2 (compiles). Fixing needs per-instance types — document as a known limit, don't fix now.
5. **Silent semantic drops.** Observed-state postconditions are discarded with no diagnostic; `severity` is never read ("warning" hard-gates like "error"); a register whose only constraint is an observed postcondition gets its alias flipped with zero enforcement.
6. `equals:` **values spliced verbatim into Rust** — an injection surface, and `equals:0b01|0b10|0b11` silently becomes `bits() == 0b11` (Rust `|` binds tighter than `==`).
7. **Generator robustness:** nested-action guard false-rejects whole peripherals on vacuous constraints; injector only handles single-file `mod.rs` (real crates.io PACs are multi-file); no Rust-keyword escaping (a field named `TYPE` emits `r.type()`); ~40% of the 1,358 lines is duplication an IR would remove.

**Disposition (settled 2026-07-15): PR 15 is not used at all — closed unmerged, zero code cherry-picked.** Everything is written fresh by Claude via the §10 series. The branch survives only as a *reviewed reference*: the ideas judged good above (composite per-operation witnesses, full write-surface gating, the established_by dichotomy, grouped manifest, honest affine framing) are **re-implemented from scratch** — under the settled terminology and the trait-bound encoding, neither of which the branch has — and the ideas judged bad (Deref-based gating, action chains ahead of extraction evidence, blind prompt changes) are simply not carried. This also removes all rebase/attribution complexity: no commit from `cursor/stabilize-pac-codegen` enters main's history.

---



## 3. Target encoding: trait-level gating in `generic.rs`

**Terminology (settled 2026-07-15):** the umbrella term is **witness tokens**, restoring the original grammar-doc/README language — PR 15's "proof" overclaims (a token attests a *past observation*, not a present guarantee; see §3.1 TOCTOU). Four distinct roles, never conflated: **state witness** (minted by a runtime check of hardware state), **action witness** (minted by performing the required software action), **obligation** (a duty to discharge — postcondition cleanup), **capability** (authority to do X at most once — write_once). Verbs are reserved too: **validate** = the LLM pipeline judging extracted facts (s4 Validator, Constraint Validator); **check** = the runtime inspection in generated code (`check_write_ready()`, matching the grammar doc's "runtime check" and the `witnessed_runtime_check` enforceability class — not "verify", which reads as static/formal and collides with the Validator); **enforce** = what the compiler does at compile time. Use these words everywhere: grammar doc, `defs.py` docstrings, generated Rust identifiers, paper ("witness-gated", not "proof-gated").

Replace `ConstrainedReg` + shadowing with gating **by trait bound**, so the witness-free method *does not exist* on constrained registers (mechanism validated in a scratch crate during review):

```rust
// generic.rs (patched now; emitted natively by svd2rust in the endgame)
pub trait Writable: RegisterSpec { type WriteWitness; type ModifyWitness; /* existing items */ }
pub trait Readable: RegisterSpec { type ReadWitness; /* existing items */ }

#[diagnostic::on_unimplemented(message = "`{Self}` is write-constrained by its datasheet; \
    call `write_witnessed(f, witness)` — obtain the witness via `check_write_ready()`")]
pub trait UnconstrainedWrite: Writable {}   // likewise UnconstrainedModify, UnconstrainedRead

impl<REG: Resettable + Writable> Reg<REG> {
    pub fn write<F>(&self, f: F) -> REG::Ux where REG: UnconstrainedWrite { /* stock body */ }
    pub fn write_witnessed<F>(&self, f: F, witness: REG::WriteWitness) -> REG::Ux { /* same body */ }
    pub unsafe fn write_unwitnessed<F>(&self, f: F) -> REG::Ux { /* the one greppable escape */ }
}
```

Per register, codegen emits either `type WriteWitness = (); impl UnconstrainedWrite for CR2rs {}` (unconstrained — **byte-identical API**, checked with `cargo public-api`) or a real witness type (`Cr1WriteWitness` — role-named, not `...Ready`) and *no* marker impl (constrained — every bypass, including `as_ptr()`+`write_volatile`, requires explicit `unsafe`).

Why this beats the wrapper:

- **No Deref hole** — nothing to deref to; the ungated method is absent from the type.
- **Domain-specific diagnostics** — `#[diagnostic::on_unimplemented]` (stable since Rust 1.78) yields *"*`CR1rs` *is write-constrained by its datasheet…"* instead of E0061 "wrong number of arguments".
- **Robust injection** — anchors on the deterministic `impl crate::Writable for {REG}rs` blocks, not 5,000-char regex lookbehinds; no alias rewriting.
- **Upstreamable** — associated types in svd2rust's `generic_reg` template + per-register emission is the natural sidecar-file feature shape (§8).

Churn edge: downstream code *generic* over registers (`fn f<R: Writable>(r: &Reg<R>)` that calls `write`) needs an `UnconstrainedWrite` bound. Rare — HAL register code is macro-generated and monomorphic.

*Appendix A gives the full mechanics: stock svd2rust code, the exact patch shapes both approaches apply, and why the resolution behavior differs.*

Keep beneath it, unchanged in shape: composite state witnesses from one fresh read; cross-register check functions; action witnesses; obligations. Add `write_when_ready(f) -> Result<Ux, Cr1ConstraintError>` — sugar that mints and spends the witness inside one method body — as the recommended default for observed-state constraints: the witness never escapes into user code, so the check-to-write window is fixed by the method body (handwritten-driver parity by construction) rather than by user discipline; hoarding is impossible through this path. The two-step `check_write_ready`/`write_witnessed` pair remains the public primitive — it is what the E0277 diagnostic points to, and it is genuinely needed where mint and spend sites differ by nature (action witnesses, cross-register checks); a witness held across other work carries documented freshness responsibility.

### 3.1 Honest enforcement limits (paper language must match)

- **Postconditions are not compile-time enforceable in affine Rust.** Obligations can be dropped or `mem::forget`-ed in safe code (verified: compiles even under `#![deny(unused_must_use)]` via `let _ =`). Three-layer response: (i) **reframe as precondition of the hazardous next operation** wherever extraction names it — the only truly checkable form; (ii) generated closure-scoped wrapper (`with_cnf_set(|scope| …)`) where cleanup happens by construction — the blessed API; (iii) `#[must_use]` obligation as audit trail.
- **Time-of-check to time-of-use (TOCTOU).**
  - *The problem:* a state witness records that the preconditions held **when they were checked**, not that they still hold **when the write executes**. Between the checking read and the gated write there is a window, and in principle the state can change inside it. This is why the term is *witness*, not *proof*.
  - *Why the window is not ours:* MMIO offers no atomic check-and-act — the read that checks a flag and the write that follows are always two separate bus transactions, on any hardware, in any language. So when the reference manual says "write CR1 only after STOP is cleared," the procedure it is prescribing **already is** check-then-act with this exact window in it. The hardware designer accepted the window when writing that sentence; the protocol is designed to be correct under it. The manual's actual requirement is **ordering** — the check must precede the operation — and ordering is precisely what the compiler enforces. A correct handwritten C driver has the same window; no encoding can remove it.
  - *Why the window is usually benign anyway:* in the dominant constraint class, the guarded bits are software-**set** and hardware-**cleared** (STOP/START/PEC, RVU, WUTWF). On its own, hardware only moves such a flag in the *safe* direction — once observed clear, it stays clear until our own software sets it again. For these, the check is not racing hardware at all. The genuinely racy cases are externally-driven flags (slave-mode address match, receive/status flags raised by bus activity from outside), and there the manual's own prescribed procedure carries the identical residual race.
  - *Carve-out 1 — witness hoarding (ours to own):* the manual implies "check *immediately* before use," but a first-class witness can be spent arbitrarily late — or two can be minted up front and one spent stale after the first write invalidates it (the compiler-verified counterexample from the PR-15 review). This extended window is created by our API, not by the hardware contract. Mitigation: `write_when_ready` is the recommended default — it mints and spends the witness inside one method body, so the witness never escapes into user code and the check-to-write distance is fixed by the method, not by user discipline (see §3). The two-step form remains for mint/spend sites that differ by nature (action witnesses, cross-register checks), with documented freshness responsibility.
  - *Carve-out 2 — action-witness self-sabotage (ours to state):* "set X before Y" implicitly means "and do not un-set X in between." An action witness survives its own invalidation (set FREQ, take the token, change FREQ, spend the token). The encoding structures the required ordering but does not police intervening self-inconsistency — a handwritten driver can make the same mistake, so parity holds, but the limit must be stated.
  - *The claim we make (paper language):* TOCTOU is inherited from the hardware contract, not introduced by the encoding; the witness discipline enforces what the manual actually requires — that the prescribed check precede the constrained operation — at parity with a correct handwritten driver, and the default entry point keeps the window as narrow as the handwritten equivalent by construction. Parity is claimed for idiomatic use, not immunity.
- **No instance binding.**
  - *The problem:* a witness minted from I2C1 also spends on I2C2 — this compiles. svd2rust gives every peripheral instance its own *handle* type (`I2C1`, `I2C2`), but derived instances share one register-block module (`pub use self::i2c1 as i2c2`), so `dp.I2C1.cr1()` and `dp.I2C2.cr1()` return the **same type**, `&Reg<i2c1::cr1::CR1rs>`. Witness types are keyed off that shared register type, and the instance identity is erased the moment the handle derefs into the shared block — so the type system cannot tell the two witnesses apart.
  - *Non-fix — an "instance" type argument on the check method* (`check_write_ready::<I2C1>() -> Cr1WriteWitness<I2C1>`): unsound. The compiler can verify that the mint-side and spend-side annotations *agree with each other*, but nothing ties either annotation to the address actually behind the `&Reg` — the caller picks both, so both can be wrong together (`dp.I2C2.cr1().write_witnessed::<I2C1>(f, w)` compiles). Annotation, not binding.
  - *Fix 1 — per-instance register types:* expand `derivedFrom` (svdtools can) so I2C1 and I2C2 each get their own register module; witnesses then bind for free, fully at compile time. **Drawbacks:** the PAC source multiplies across every derived family (UART/SPI/TIM/I2C), compile times grow, and it breaks the instance-generic pattern HALs are built on — `stm32f4xx-hal`'s `I2c<I2C>` works *because* all instances share one `RegisterBlock` type. A large upstream divergence to close a secondary hole.
  - *Fix 2 — instance-branded methods on the handle types:* mint **and** spend through the handle, which does know its address at the type level (`impl I2C1 { fn check_cr1_write_ready(&self) -> Cr1WriteWitness<I2C1>; fn cr1_write_witnessed(&self, f, w: Cr1WriteWitness<I2C1>) }`). Sound, because the branded value is the thing that touches the hardware. **Drawbacks:** re-introduces per-instance API surface for constrained registers (a scoped version of Fix 1's cost) and moves gated calls off the familiar `periph.reg().op()` shape.
  - *What we propose:* an **address tag in the witness behind** `#[cfg(debug_assertions)]`, checked with `debug_assert_eq!` at spend. **Why:** the check method already holds `&self`, so it captures the register address at mint time with zero API or type changes; the field is compiled out in release, so witnesses remain true ZSTs and the zero-cost claim stands; and every dev/test/CI build turns a silent cross-instance violation into an immediate, located failure. It is not compile-time — we say so in the limits table — but it buys ~all of the practical protection for none of the structural cost. If a specific multi-instance family (I2C/USART/SPI) proves this is a real bug class in the wild, upgrade that family to Fix 2. Note also that the layer above restores instance identity naturally — `stm32f4xx-hal`'s `I2c<I2C1>` owns its handle, so HAL-mediated code cannot cross instances — consistent with our position that ownership/typestate binding belongs in the HAL.
- **Same-register read gates are self-defeating** (the check performs the constrained read) — reject at codegen; only cross-register-witnessed read gates are sound.
- `severity: "warning"` → emit a `#[deprecated]`-annotated witness-free method (compile warning, still callable), not a hard gate.

The honest headline: *"every idiomatic constrained call site is preceded by a fresh conjunctive check, affinely consumed; software-action ordering is structured and auditable; violations are compile errors; the only bypass is* `unsafe`*."*

---



## 4. Grammar v2

A discriminated union on `kind`, sharing an envelope (`severity: Literal["error","warning"]`, `consequence`, `datasheet_text`). Few orthogonal fields; every vocabulary a `Literal`; all names/values SVD-validated at collection. *This section is the summary; the complete normative spec — every model, field, vocabulary, per-kind examples, and collection rules — is Appendix B.*

```python
class FieldCondition(BaseModel):
    register: str                       # SVD-canonical; resolved at collection
    field: str                          # "" not allowed; whole-register via explicit flag
    state: Literal["cleared", "set", "equals"]
    values: list[int] = []              # equals: >=1 entries; >1 == OR-of-values
    established_by: Literal["hardware", "software"] = "hardware"
    action_operation: Optional[Literal["write", "modify"]] = None  # required iff software
```

`values` accepts hex/bin/dec strings, validated by regex and normalized to `int` — kills both the OR-string drift and the code-injection surface in one move.

**Kinds** (each grounded in the corpus, §5):


| kind          | corpus evidence                                                                                   | enforceability class                                                                         |
| ------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `state_gate`  | the dominant class: UE=0, SPE=0, ADSTART=0, FINIT=1, WUTWF=1, LOCK …                              | compile-gate (software evidence → action token; hardware evidence → witnessed runtime check) |
| `sequence`    | RTC_WPR 0xCA→0x53; GPIO LCKR lock; SDIO DCTRL after DTIMER+DLEN; AES key order; DBGMCU 2-word key | compile-gate — strongest linear-types fit: each step consumes the prior step's token         |
| `write_once`  | EXTI_LOCKR.LOCK, TIM BDTR.LOCK ("written once after reset")                                       | compile-gate — affine capability consumed by value (2nd write = E0382)                       |
| `clock_gate`  | RCC ENR before any peripheral access ("registers read 0x0 when clock inactive")                   | compile-gate at the *handle* (block accessor takes a one-time token), not per-register       |
| `delay`       | "wait two APB clock cycles", HSE stabilization                                                    | ordering compile-gated via token; duration runtime                                           |
| `read_effect` | DSI_ISR cleared-on-read; USART_DR clears RXNE                                                     | documentation-only; feeds validator + tells codegen when a verify-read perturbs state        |
| `other`       | escape valve: real access/ordering requirements fitting no kind — corpus: "channel selection bits must remain unchanged during sample cycles", "do not change after initial programming" | documentation-only BY CONSTRUCTION (never gates, never breaks a build); the grammar-evolution discovery queue |


`other` carries `description: str` (the requirement in the model's own words, for clustering) and `involved: list[FieldRef]` (SVD-validated). Two guardrails keep it from becoming a dumping ground: (1) it is for *genuine requirements that fit no kind* — the routed-out non-constraints (w1c, access-width, privilege, validity notes) still emit **nothing**; (2) collection reports the **`other`-rate per device/run** — a spike is a visible prompt regression, and the steady-state number is a paper metric ("the grammar structurally covers X% of extracted constraints; the residual drives evolution"). This institutionalizes how `sequence`/`clock_gate`/`write_once` were found: mining the v1 corpus's 729 empty-pre/post constraints (~347 of them real but inexpressible — structure silently destroyed, which `other` prevents).

Drift dispositions: `target_operation:"any"` → legalized, expanded deterministically to per-op constraints at collection; `"read/write"`/`"read-write"` → normalized likewise; `"access"` (width notes) and privilege/secure notes → **not constraints** (routed out at the prompt, §6); `"enabled"` → repaired via SVD `enumeratedValues` name match, else rejected; `"equals:X then Y"` → must be a `sequence`.

**Enforceability is computed, never LLM-emitted:** collection derives `enforceability ∈ {compile_gate, witnessed_runtime_check, dynamic_check, doc_only}` from `(kind, established_by, target_fields)`; codegen records `enforced_as` per constraint in the manifest. Paper metric = fraction classifiable as compile-enforceable × fraction actually enforced, measured from manifests.

**Evolution:** `schema_version`; mechanical lossless v1→v2 lift for all 30 existing run dirs; repair-vs-reject policy in `collect_constraints` (repair the deterministic: value parsing, `any` expansion, SVD-casing, enum-name→value; reject the judgmental: unknown kinds/states, unresolvable names, out-of-range values), with structured per-constraint errors enabling one automated re-prompt round — never aborting a peripheral.

---



## 5. Extraction quality — what the STM corpus actually says



### 5.1 Headline numbers

- **4,927 constraints, 30 RMs**, 4,107 of 15,422 register files carry constraints (27%).
- **Duplication:** 3,155 sit in 779 exact-duplicate groups (per-instance USART1..8 and per-bit fan-out of register-level notes) → **~2,551 unique**; 1,843 unique (target, op, pre, post) shapes.
- **Vocabulary drift:** 74 off-vocab operations; 13 `severity:"info"`; long tail of free-text states (`unchanged`, `written`, `unlocked`, `privileged`, `empty`, `equals:output`, `equals:0xCA then 0x53`).
- **729 (15%) empty constraints** (no pre, no post) — ~347 of these still read as genuine gating/ordering the grammar couldn't hold (init-mode gating, sequences, write-once): *expressiveness losses, recoverable by v2 kinds*.
- **96 constraints from** `%s`**-placeholder filenames** (`tim3_ccr%s`) — derivedFrom plumbing bug to fix in the run-dir writer.
- **Names are largely real:** 94% of same-register field refs resolve even against the runs' own incomplete `subfields` lists (most misses are fields the generator omitted from `subfields`, not invented names). Resolution must be done against the SVD, not run output.
- **Manual sample estimate: ~75–80% of unique constraints are true positives** (n≈20 random + targeted pathological review; to be measured properly per §7).



### 5.2 Canonical real-STM examples (replace all synthetic fixtures/few-shots)


| pattern                      | example (source)                                                                                                                                                                    |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| mode-gate, software enable   | `USART_BRR` write ⇐ `CR1.UE=0` (`rm0091/2/usart1_brr`, ×37); `SPI_CR1.SPE=0` (×47); `ADC ADSTART=0`; `AES EN=0`                                                                     |
| hardware-flag observed       | `RTC_WUTR` write ⇐ `RTC_ISR.WUTWF=1` (`rm0430/1/rtc_wutr`); I2C_CR1 STOP/START/PEC (`rm0038/1/i2c2_cr1`)                                                                            |
| dual-evidence unlock         | `IWDG_PR` write ⇐ `IWDG_KR==0x5555` (software, value) **and** `IWDG_SR.PVU` cleared (hardware) (`rm0008/1/iwdg_pr`)                                                                 |
| **pre+post software action** | **F1 RTC config mode: set** `RTC_CRL.CNF` **before writing** `CNTH/ALRH/…`**, clear after (**`rm0008/1/rtc_cnth`**) — replaces the synthetic Intel MTQC/RTTDCS example everywhere** |
| set-mode before config       | `CAN_FMxR` write ⇐ `FMR.FINIT=1` (`rm0091/2/can_fm1r`, ×21)                                                                                                                         |
| read gate (warning)          | `SPI_TXCRCR` read while `BSY` set returns garbage (`rm0008/1/spi1_txcrcr`, ×38)                                                                                                     |
| sequence                     | RTC_WPR 0xCA→0x53 (`rm0383/1/rtc_dr`); GPIO LCKR (`rm0033/1/gpioi_lckr`); SDIO_DCTRL (`rm0038/1/sdio_dctrl`); AES key order (`rm0493/1/aes_keyr7`)                                  |
| write-once                   | `EXTI_LOCKR.LOCK` (`rm0493/1/exti_lockr`); TIM `BDTR.LOCK`                                                                                                                          |
| cross-peripheral             | `PWR_CR.DBP` gating RTC/`PWR_CSR` writes (`rm0033/1/pwr_csr`) — common; codegen currently cannot emit cross-peripheral paths                                                        |




### 5.3 False-positive classes (each mechanically identifiable)

1. **w1c flag semantics as postconditions** (9–14-postcondition pathologies: `rm0313/1/rcc_csr` RMVF; `rm0505` radio IRQ) — SVD `modifiedWriteValues` territory.
2. **Read-to-clear as read constraints** (`rm0386/1/dsi_isr1`) — `read_effect` or nothing.
3. **Non-constraint prose:** access-width (`rm0008/1/wwdg_cfr`), validity/don't-care notes (`rm0316/1/fmc_bwtr%s`), TrustZone/privilege (`rm0493/1/pwr_seccfgr`).
4. **Unresolvable references:** ranges `LCK0-LCK15`, wildcards `AES_KEYR`*, pseudo-fields `key`/`mailbox_state`/`order`/`""`.
5. **Encoding slips:** incomplete conditions (TIM DIR: encodes CMS, drops encoder mode); value-invariants misencoded as pre/post (`USART_BRR` OVER8/DIV_Fraction3).

---



## 6. Generator prompt changes

1. **Schema enforcement is tiered, not a hard dependency on structured-output mode.** Groq's open-source models (gpt-oss-120b) frequently fail `json_schema`-constrained decoding with hard API errors — a failed call recovers *nothing*, whereas free-form generation plus post-processing recovers *something*. So: (a) the prompt always carries the compact JSON schema + per-kind exemplars; (b) structured-output mode is enabled **per provider** where it is reliable (OpenAI models), skipped for Groq OSS; (c) the guarantee layer is collection-time pydantic parsing — the same `Literal`s reject drift at parse time, feeding the B.4 repair/reject/re-prompt machinery; (d) recovery is **per-constraint**, not per-response: JSON-block extraction (the existing `utils/parse_output.py` path), then each constraint in the list validates independently — well-formed entries survive a malformed sibling. Net: identical vocabulary guarantees for downstream consumers, no provider lock-in, graceful degradation instead of hard errors.
2. **Negative routing rules** (one example each): do NOT emit constraints for w1c/rc_w semantics, read-to-clear behavior (→ `read_effect`), access-width, secure/privileged access, validity/don't-care notes, reset behavior. These four rules cover every FP class in §5.3.
3. **Naming rules:** SVD-canonical names only; no ranges/wildcards/pseudo-fields; whole-register conditions via the explicit flag.
4. **Values numeric only; sequences →** `sequence` **kind** (never "then"-strings).
5. `datasheet_text` **must be verbatim and complete** — if the requirement spans two sentences, quote both (feeds the deterministic anchor, §7.1).
6. **Few-shots from §5.2:** RTC-CNF pre+post (replacing Intel MTQC), IWDG dual-evidence, UE=0 mode-gate, plus one negative (w1c → no constraint).
7. **Dedup guidance:** one constraint per (register, operation) with fields listed in `target_fields`, rather than per-bit repeats (belt-and-braces: deterministic dedup downstream regardless).
8. **Decision tree** for kinds: order→sequence; wait→delay; "before any access"/clock→clock_gate; "once until reset"→write_once; "reading clears"→read_effect; state condition→state_gate; then the final fork — a genuine access/ordering requirement fitting no kind→`other`; not a requirement at all (w1c, width, privilege, validity note)→emit nothing.

**Do not land prompt changes blind** (PR 15's mistake): each prompt change ships with an extraction eval on a fixed register sample showing the model populates the new fields correctly.

---



## 7. Constraint Validator — and ground truth without a verified-constraint datasheet



### 7.0 Two-stage design

- **Stage 0 — deterministic lint** (in `collect_constraints.py`, free): Literal validation; SVD resolution of every name; value-vs-field-width checks; exact dedup (−36% immediately); `%s` repair; **reclassification of w1c/read-action constraints using SVD** `modifiedWriteValues`**/**`readAction`**/**`access` **metadata** (a write-constraint on a read-only field is an FP by construction); flags for self-defeating same-register read gates and cross-peripheral sources.
- **Stage 1 — LLM judge**, three checks per surviving constraint: (a) quote authenticity (pre-checked deterministically, below); (b) *constraint-ness* — is the quoted text a genuine access/ordering requirement vs descriptive semantics; (c) *encoding fidelity* — target/operation/polarity/fields/evidence match the text. Verdict TP / FP / repair, with confidence. Thesis-consistent role: precision filter before codegen; compiler + PR review adjudicate at the end.



### 7.1 The ground-truth strategy (no verified datasheet needed)

Constraints differ from layout facts in one decisive way: **every constraint carries its own cited evidence** (`datasheet_text`). Verification decomposes:

1. **Quote authenticity is deterministic.** Fuzzy-match the quote against the source document (PyMuPDF / the markdown conversion; same machinery as `annotate.py` page lookup). No match → constraint dies ("unanchored"), no LLM spent. Handles: repeated boilerplate quotes (prefer the occurrence inside the target register's own section; flag surviving ambiguity), table-footnote mangling (match against markdown, not raw PDF text). **The judging path uses no semantic retrieval** — the quote is the pointer, so context extraction is a deterministic string-locate + expand; this isolates validator calibration from retrieval quality (a validator error can never be a retrieval miss, and the corruption harness judges original vs corrupted encodings against byte-identical context). Contrast with the open-book s4 layout Validator, which must hunt for evidence because layout claims carry no citation. Keyword/semantic search may optionally assist *human triage* of `unanchored` rows (suggesting near-miss locations), but never feeds the judge.
2. **Context is derived, never generated.** Do **not** ask the generator for preceding/following lines — generator-emitted context is exactly as unverified as the quote, and the check on generated content can't itself be generated content. Instead: locate the verified quote, then programmatically pull the true enclosing paragraph/±N lines from the chunked markdown. Trusted by construction, window size tunable at validation time, zero generation tokens. This closes the *selective-quoting* blind spot (TIM DIR/CMS case): the omitted condition sits in trusted context the judge can see.
3. **Encoding fidelity becomes a closed, local task**: "given these two sentences (+trusted context), does this JSON encode them faithfully?" — NLI-style, no open-book retrieval.



### 7.2 Measuring the judge — the verified-constraints datasheet (async, never blocking)

**Design principle (Ramla, 2026-07-15): the human annotation must not be the stopping point.** The Constraint Validator is built and calibrated on its two human-free legs (quote anchoring; corruption harness below) and runs immediately; the human-verified data arrives incrementally and is used *retrospectively* to measure the validator's α on real data whenever enough of it exists. Validator development, corpus trimming, and codegen never wait on annotation progress.

- **`verified_datasheet/constraints/stm.csv` — a verified-constraints datasheet seeded from the full 30-RM corpus.** This is the "separate dependency-verified file" that `verified_datasheet/README.md` already reserves as the escape from its layout-only scope. Built by a reproducible `build_constraints_datasheet.py` (corpus run-dirs → CSV; re-runnable when new runs land):
  - one row per **unique constraint per reference manual** (dedup within RM across runs, peripheral instances, and per-bit fan-out; `dup_count` + example source file retained as provenance) — ~2,000–2,500 rows from today's corpus;
  - columns: `id` (stable content hash), **`reference_manual`** (rm0008 … rm0505), `run`, `source_file`, `peripheral`, `register`, `target_operation`, `target_fields`, `preconditions` (JSON), `postconditions` (JSON), `severity`, `consequence`, `datasheet_text`, `dup_count`, `lint_flags` (machine-derived stage-0 findings: off-vocab op/state, unresolvable field, placeholder source — informational, aids stratified annotation), then the annotation columns: `status`, `note`;
  - `status` vocabulary: `confirmed` (genuine constraint, encoding faithful — TP) / `encoding_error` (real constraint, wrong or incomplete encoding) / `not_constraint` (quoted text isn't an access/ordering requirement — FP) / `quote_missing` (quote not found in the manual) / `unsure` / empty (unannotated);
  - blindness rule adapted from Phase 0: the row shows *generator output + its quote* (that pair **is** the object under judgment), but **no LLM-validator verdict ever appears in or near the file** — the human label must not be anchored by the machine's.
- **`verified_datasheet/annotate_constraints.py`** — sibling of `annotate.py`, mirroring its conventions (atomic resumable CSV saves after every answer, `--stats`, strict round-robin across reference manuals so partial effort spreads evenly, colorized keyboard-driven loop). The judgment is the **closed local task** from §7.1 — quote vs encoding — so the tool works without any PDFs present; ~20s/row. When chunked markdown is available it additionally shows the derived surrounding context (§7.1), sharpening `encoding_error` detection for selectively-quoted constraints.
- **How the α measurement then works:** at any point, the annotated subset (stratified by the round-robin) is joined against the validator's verdicts on the same rows → confusion matrix → α on real data. More annotation → tighter confidence interval; zero annotation → the validator still ships, calibrated by the corruption harness alone, with α reported as "pending human audit."
- **Corruption harness for β** — zero human cost; reuse the Phase-1b methodology and its realism lesson: corrupt *encodings* of quote-authentic constraints (flip polarity cleared↔set, swap in a sibling field of the same register, change operation, perturb `equals` values in-range, flip `evidence`) → known-bad by construction → measure detection. Unrealistic corruptions inflate the numbers; use sibling names and in-range values only.
- **Compiler + known-good drivers as the end-of-pipe oracle** (the merge-rate analog for this arm): inject survivors into the PAC; compile unmodified `stm32f4xx-hal` + examples. Every gated call site in mature HAL code is informative — HAL establishes the precondition nearby (corroboration, visible to the reviewer) or a known-good driver broke (strong FP evidence). Constraints gating nothing in real code are inert/low-risk.

**Paper claim this supports:** "constraints are quote-anchored (deterministically verified against the source PDF), validator-filtered with measured α/β, and adjudicated by compilation against production driver code." No recall claim (per thesis). Optional garnish: a *section-scoped* recall probe — Ramla enumerates constraints for 2–3 peripherals' register-description sections (an evening) — positioned as optional, not a dependency.

---



## 8. Integration / distribution

- **Wrapper/companion crate is impossible** (E0116: no external inherent impls; trait methods can't outrank inherent ones; can't remove items from a dependency). Dead end — don't revisit.
- **Winner: fork with committed generated+injected source** (`stm32f4-lidar` or similar). `regenerate.sh`: checkout upstream tag → stm32-rs's own pipeline (svdtools → pinned svd2rust) → batch injection → commit crate source to `constrained/v0.16.0`. Consumers: one-line dependency (new crates) or workspace `[patch.crates-io]` (existing stacks — HALs hardcode `stm32f4`).
- **Guardrails:** `cargo public-api` diff proves the unconstrained API is byte-identical; regeneration is always pristine→inject in one pass (never re-patch a patched tree).
- **Thesis demo:** unmodified `stm32f4xx-hal` under `[patch.crates-io]` fails with exactly the expected constraint errors at its I2C call sites and nothing else — assert the exact error set in CI.
- **Endgame:** propose a generic, human-authorable sidecar (`constraints.toml` + `--constraints` flag) to svd2rust / a `constraints/` step in stm32-rs's Makefile. Pitch the *mechanism* upstream; LIDAR remains one producer of the file. (Standard SVD `<writeConstraint>` etc. cannot carry cross-register/sequence semantics; svdtools rejects unknown YAML keys — checked.)

---



## 9. Testing / CI (precondition for everything else)

The single most important process fix: **make the compiler the test oracle, unskippably.**

- CI job that produces a compilable PAC (pinned svd2rust over vendored SVDs, cached — or a minimal hand-written stub PAC with a real `generic.rs`) and runs all compile tests on every emitted shape (same-register, cross-register, action, sequence): legal paths must pass, violation paths must fail **with the expected diagnostic** (E0277 + message substring under §3; trybuild-style).
- SKIP → FAIL in CI. Golden diffs stay as change detectors only.
- Eval workspace: unmodified stm32f4xx-hal + patch stanza; assert the exact expected error set (the paper's headline table).

---



## 10. Sequenced roadmap


| step | content | depends on | folders touched / created |
| --- | --- | --- | --- |
| **A. CI/compile harness** | §9. No generator changes. | — | **create** `.github/workflows/`; edit `applications/pac_codegen/test_codegen.py` (SKIP→FAIL); `applications/pac_codegen/` (PAC-generation helper, cached under `vendored/`); `applications/pac_codegen/constraint_test/` (stub-PAC fixture) |
| **B. Soundness re-cut** | trait-level gating (§3): composite witnesses, full write-surface gating, `unsafe`-only escape, `write_when_ready`, severity=warning→deprecated, loud failures on dropped semantics. Golden + must-fail tests. | A | `applications/pac_codegen/` (`rust_codegen.py` rewrite: generic.rs patch + per-register emission); `applications/pac_codegen/constraint_test/` (new golden, must-fail cases, `main.rs`); `test_codegen.py` (E0061→E0277 assertions) |
| **C. Generator IR refactor** | `PeripheralPlan` IR + single naming/escaping module + dumb renderer; behavior-preserving; kills ~40% duplication, keyword bugs, repeated normalization. | B | `applications/pac_codegen/` (split `rust_codegen.py` → **new** `ir.py`, `naming.py`, `render.py`); `constraint_test/` goldens regenerate byte-identical |
| **D. Grammar v2 schema + collection** | §4/Appendix B: kinds, Literals, structured values, v1→v2 lift, repair/reject policy, computed enforceability, per-constraint drops. No prompt changes yet. | — (parallel to A–C) | `defs.py` (repo root); `docs/` (rewrite `REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md` from Appendix B); `applications/pac_codegen/collect_constraints.py`; `tests/` (schema-consistency test) |
| **E. Stage-0 lint + corpus cleanup** | §7.0 stage 0 on the 30-RM corpus; fix `%s` plumbing; dedup; publish cleaned corpus stats. | D | `applications/pac_codegen/` (lint in/next to `collect_constraints.py`, reusing `agent_tools/svd_parsing.py`); `core/` + `utils/result_saver.py` (`%s` run-dir naming fix); stats → `optimization/test_outputs/` |
| **F. Prompt v2 + extraction eval** | §6, with a fixed-sample eval proving the model populates new fields; real-STM few-shots. | D | `prompts/` (`register_info_stm.py`, `examples.py`); `tests/`; eval harness under `optimization/generator/` with runs in `optimization/test_outputs/` |
| **G. Constraint Validator + verified-constraints datasheet** | §7 stage 1 + quote anchoring + derived context; corruption calibration → β/F1 shipped human-free. Alongside: `build_constraints_datasheet.py` → `verified_datasheet/constraints/stm.csv` (30 RMs, `reference_manual` column) + `annotate_constraints.py`; Ramla annotates **asynchronously, never blocking**; α on real data measured retrospectively as annotations accumulate. | E | **create** `constraint_validator/` (judge, quote anchor, corruption harness — 1b-style package); `verified_datasheet/` (**new** `constraints/stm.csv`, `build_constraints_datasheet.py`, `annotate_constraints.py`; README note); `prompts/` (judge prompt); reuses only the **artifacts** of `context_retrieval/preprocessing/` (chunked markdown) + `agent_tools/md_ops.py` — context is static quote-anchored extraction, **no semantic retrieval in the judging path** (see §7.1) |
| **H. Cross-register + sequences in codegen** | cross-peripheral paths (PWR.DBP→RTC is real and common), `sequence` kind emission; compile-tested via A. | B, D | `applications/pac_codegen/` (IR + emitters); `constraint_test/` (**new** real-STM fixtures: IWDG, RTC-WPR sequence, PWR.DBP cross-peripheral) |
| **I. Action chains + closure-scoped wrappers** | only after F shows `evidence`/`action_operation` extract reliably; RTC-CNF as the fixture. | B, F | `applications/pac_codegen/` (+ `constraint_test/` RTC-CNF fixture); `prompts/` (the deferred prompt changes land here); `docs/` (grammar-doc examples swap to RTC-CNF) |
| **J. Fork + distribution + HAL demo** | §8: `regenerate.sh`, public-api guard, `[patch.crates-io]` eval workspace. | B (sound encoding first) | **create** external fork repo (`stm32-rs-constrained`, generated source committed); in-repo `applications/pac_codegen/` (`regenerate.sh`, batch injection); **create** `applications/pac_codegen/eval_hal/` (pinned stm32f4xx-hal + patch-stanza workspace) |

PR 15 itself: **closed unmerged — nothing lands from the branch** (settled 2026-07-15). All functionality above is written fresh; the branch is kept only as a reviewed reference and negative example (its verified defects become §9 must-fail test cases).

---



## 11. Decisions — all settled with Ramla, 2026-07-15

1. **Encoding: trait-level gating directly** (§3/Appendix A) — no intermediate ConstrainedReg-minus-Deref step; one rewrite, no throwaway code, the Deref hole never exists, E0277 diagnostics from day one.
2. **Grammar v2 scope: full schema, phased codegen** — all 8 kinds land in `defs.py` + collection in step D (extraction and the corpus lift produce v2 data immediately); codegen support arrives per kind: `state_gate` in B, `sequence` + cross-register in H, `clock_gate`/`write_once`/`delay` later.
3. **PR 15: not used at all** — closed unmerged, zero cherry-picks; everything written fresh per §10. Optional: post the review findings as a closing comment on the PR.
4. **Human α-audit: decoupled** via the verified-constraints datasheet + `annotate_constraints.py` (§7.2) — the validator runs without it; annotation proceeds at Ramla's pace and retrospectively measures α; she is never the stopping point.
5. **Section-scoped recall probe: skipped this round** — the thesis makes no recall claim; annotation time goes to the verified-constraints datasheet instead. (Can be revisited at paper-writing if a coverage-within-sections number proves useful.)
6. **Fixtures: replace the synthetic Intel MTQC/RTTDCS example everywhere** (docs, prompts, codegen fixtures) with the real STM pair — RTC-CNF pre+post (`rm0008/1/rtc_cnth`) and IWDG dual-evidence (`rm0008/1/iwdg_pr`).

**Process rule (Ramla, 2026-07-15):** during implementation, commit after every major change — each completed roadmap step and each coherent milestone within one.

---



## Appendix A — Shadowing vs trait-bound gating: mechanics and patch shapes



### A.1 The underlying problem

svd2rust defines every register method once, generically, in `generic.rs` (`impl<REG: Resettable + Writable> Reg<REG> { pub fn write... }`). Rust has no way to *un*-implement a generic inherent method for one particular `REG` (specialization is unstable; negative bounds don't exist). Both designs are workarounds: **shadowing changes the receiver's type** so a same-named method wins resolution; **the trait bound changes the method's availability condition** so the method doesn't apply to that `REG` at all.

### A.2 Original svd2rust code (simplified but faithful)

```rust
// ---- generic.rs (stock) ----
pub struct Reg<REG: RegisterSpec> {
    register: vcell::VolatileCell<REG::Ux>,
    _marker: marker::PhantomData<REG>,
}

impl<REG: Readable> Reg<REG> {
    pub fn read(&self) -> R<REG> { /* volatile read */ }
}

impl<REG: Resettable + Writable> Reg<REG> {
    pub fn write<F>(&self, f: F) -> REG::Ux
    where F: FnOnce(&mut W<REG>) -> &mut W<REG>
    { /* reset-value base, apply f, volatile write */ }

    pub unsafe fn write_with_zero<F>(&self, f: F) -> REG::Ux { /* … */ }
    pub fn reset(&self) { /* … */ }
}

impl<REG: Readable + Writable> Reg<REG> {
    pub fn modify<F>(&self, f: F) -> REG::Ux { /* read-modify-write */ }
}

// ---- stm32f405 peripheral module (stock) ----
pub type CR1 = crate::Reg<cr1::CR1rs>;
pub mod cr1 {
    pub struct CR1rs;
    impl crate::RegisterSpec for CR1rs { type Ux = u32; }
    impl crate::Readable  for CR1rs {}
    impl crate::Writable  for CR1rs { type Safety = crate::Unsafe; /* bitmaps */ }
    impl crate::Resettable for CR1rs { /* RESET_VALUE */ }
    // R/W field proxies (r.stop(), w.pe(), …)
}
```

Note the shape that matters: `write` already exists *only when* `REG: Writable` — a read-only register has no `write` method because its `REGrs` never implements `Writable`. Both approaches below are judged by how naturally they extend this.

### A.3 Approach 1 — shadowing (main + PR 15)

**Patch to** `generic.rs`**:**

```diff
 pub struct Reg<REG: RegisterSpec> {
-    register: vcell::VolatileCell<REG::Ux>,
+    pub(crate) register: vcell::VolatileCell<REG::Ux>,  // widened for shadow bodies
     _marker: marker::PhantomData<REG>,
 }
+
+/// Wrapper marking a register as constraint-gated.
+#[repr(transparent)]
+pub struct ConstrainedReg<REG: RegisterSpec> {
+    pub(crate) reg: Reg<REG>,
+}
+unsafe impl<REG: RegisterSpec> Send for ConstrainedReg<REG> where REG::Ux: Send {}
+impl<REG: RegisterSpec> core::ops::Deref for ConstrainedReg<REG> {
+    type Target = Reg<REG>;
+    fn deref(&self) -> &Reg<REG> { &self.reg }   // ← the safe bypass lives HERE
+}
+impl<REG: Readable> core::fmt::Debug for ConstrainedReg<REG> /* via deref */ { … }
```

**Patch to the peripheral module — per *constrained* register only:**

```diff
-pub type CR1 = crate::Reg<cr1::CR1rs>;
+pub type CR1 = crate::ConstrainedReg<cr1::CR1rs>;   // alias rewrite (regex, context-sniffed)

+pub mod constraints {
+    pub struct Cr1WriteWitness(());                  // private ctor: unforgeable downstream
+    pub enum Cr1ConstraintError { StopNotCleared, StartNotCleared, PecNotCleared }
+
+    impl crate::ConstrainedReg<super::cr1::CR1rs> {
+        pub fn check_write_ready(&self) -> Result<Cr1WriteWitness, Cr1ConstraintError> {
+            let r = self.reg.read();                 // ONE fresh read, all preconditions
+            /* check stop/start/pec … */
+        }
+        // same-name, different-arity SHADOWS — one per gated op, per register:
+        pub fn write<F>(&self, f: F, _w: Cr1WriteWitness) -> u32 { self.reg.write(f) }
+        pub fn modify<F>(&self, f: F, _w: Cr1ModifyWitness) -> u32 { self.reg.modify(f) }
+        pub fn reset(&self, _w: Cr1WriteWitness) { self.reg.reset() }
+        /* write_with_zero, from_write, from_modify … */
+        pub unsafe fn bypass_constraints(&self) -> &crate::Reg<super::cr1::CR1rs> { &self.reg }
+    }
+}
```

Unconstrained registers: zero changes (the approach's one genuine virtue).

**How it enforces:** for `cr1().write(|w| …)` the compiler walks the autoderef chain (`ConstrainedReg` → `Reg`) selecting methods **by name — arity is not considered during selection**. It finds `ConstrainedReg::write` at step zero, commits, then fails the argument check → **E0061 "this method takes 2 arguments but 1 was supplied."** It never falls through to `Reg::write`.

**The holes** (all compiler-verified): the gate covers only method-call syntax on the wrapper. Any safe way to obtain `&Reg<CR1rs>` restores the stock method — deref coercion (`let r: &Reg<cr1::CR1rs> = i2c1.cr1();`), explicit `&`*, UFCS `Reg::write(&*cr1, f)`, or any `fn f<R: Writable>(r: &Reg<R>)`. No `unsafe` anywhere. The E0061 diagnostic also gives the driver author no hint of *why*.

### A.4 Approach 2 — trait-bound gating (proposed)

**Patch to** `generic.rs`**:**

```diff
+#[diagnostic::on_unimplemented(message = "`{Self}` is write-constrained by its datasheet; \
+    call `write_witnessed(f, witness)` — obtain the witness via `check_write_ready()`")]
+pub trait UnconstrainedWrite: Writable {}
+pub trait UnconstrainedModify: Writable {}
+pub trait UnconstrainedRead: Readable {}

 pub trait Writable: RegisterSpec {
     type Safety;
+    type WriteWitness;
+    type ModifyWitness;
     /* bitmaps … */
 }
 pub trait Readable: RegisterSpec {}
+// Readable gains: type ReadWitness;

 impl<REG: Resettable + Writable> Reg<REG> {
     pub fn write<F>(&self, f: F) -> REG::Ux
     where
+        REG: UnconstrainedWrite,                    // ← the entire mechanism
         F: FnOnce(&mut W<REG>) -> &mut W<REG>,
     { /* body UNCHANGED */ }
+
+    pub fn write_witnessed<F>(&self, f: F, _witness: REG::WriteWitness) -> REG::Ux
+    { /* same body — defined ONCE, generically */ }
+
+    pub unsafe fn write_unwitnessed<F>(&self, f: F) -> REG::Ux
+    { /* same body — the one greppable escape */ }
 }
+// likewise: reset/write_with_zero/from_write gain `REG: UnconstrainedWrite`;
+// modify/from_modify gain `REG: UnconstrainedModify`; read gains `REG: UnconstrainedRead`.
+// Blanket impls that internally call gated methods (e.g. Debug for readable regs)
+// carry the same bound — the PAC build itself verifies this (step A harness).
```

**Patch to the peripheral module — per *constrained* register:**

```diff
 pub type CR1 = crate::Reg<cr1::CR1rs>;             // UNCHANGED — no wrapper, no alias rewrite
 pub mod cr1 {
     impl crate::Writable for CR1rs {
         type Safety = crate::Unsafe;
+        type WriteWitness  = super::constraints::Cr1WriteWitness;
+        type ModifyWitness = super::constraints::Cr1ModifyWitness;
         /* bitmaps … */
     }
+    // NOTE: no `impl crate::UnconstrainedWrite for CR1rs` — the ABSENCE is the gate.
 }
+pub mod constraints {
+    pub struct Cr1WriteWitness(());
+    pub enum Cr1ConstraintError { /* … */ }
+    impl crate::Reg<super::cr1::CR1rs> {           // inherent impl on the STOCK type (same crate)
+        pub fn check_write_ready(&self) -> Result<Cr1WriteWitness, Cr1ConstraintError> { /* … */ }
+        pub fn write_when_ready<F>(&self, f: F) -> Result<u32, Cr1ConstraintError> { /* check+write */ }
+    }
+}
```

**And per *unconstrained* register (the footprint-polarity flip — the majority, mechanical):**

```diff
     impl crate::Writable for CR2rs {
         type Safety = crate::Unsafe;
+        type WriteWitness  = ();
+        type ModifyWitness = ();
         /* bitmaps … */
     }
+    impl crate::UnconstrainedWrite  for CR2rs {}
+    impl crate::UnconstrainedModify for CR2rs {}
+    impl crate::UnconstrainedRead   for CR2rs {}
```

**How it enforces:** `cr1().write(|w| …)` resolves to the one and only `write`, whose where-clause `CR1rs: UnconstrainedWrite` is unsatisfied → **E0277 at the call site with the custom message**. There is nothing to escape to: no wrapper means no Deref target; UFCS hits the same bound; a generic `fn f<R: Writable>(r: &Reg<R>)` that writes doesn't compile *at its own definition* without an `UnconstrainedWrite` bound — and once bounded, `CR1rs` can't be passed to it. The constraint propagates soundly through generic code instead of leaking. Remaining bypasses (`write_unwitnessed`, `as_ptr()`+`write_volatile`) are all `unsafe`.

### A.5 The downstream driver's view

```rust
// unconstrained register — identical under stock, shadowing, and trait-bound:
i2c1.cr2().write(|w| unsafe { w.freq().bits(8) });          // ✓ compiles, all three

// constrained register, token-less write:
i2c1.cr1().write(|w| w.pe().enabled());
// shadowing:   error[E0061]: this method takes 2 arguments but 1 argument was supplied
// trait-bound: error[E0277]: the trait bound `CR1rs: UnconstrainedWrite` is not satisfied
//              note: `CR1rs` is write-constrained by its datasheet; call
//              `write_witnessed(f, witness)` — obtain the witness via `check_write_ready()`

// the witnessed path (both):
let w = i2c1.cr1().check_write_ready()?;
i2c1.cr1().write_witnessed(|w_| w_.pe().enabled(), w);      // ✓

// the safe bypass that distinguishes them:
let r: &stm32f4::Reg<stm32f405::i2c1::cr1::CR1rs> = i2c1.cr1();
r.write(|w| w.start().set_bit());
// shadowing:   ✓ compiles — silent constraint violation, zero unsafe   ← the hole
// trait-bound: ✗ E0277 (same error; the method does not exist for CR1rs anywhere)
```



### A.6 Why the trait bound is idiomatic Rust

Conditional method availability via a where-clause on a generic inherent impl is a std-library staple, and the failure mode downstream developers see (E0277 at the call site) is one they already know how to read: `[T]::sort` exists only `where T: Ord` (calling `.sort()` on `Vec<f64>` is exactly our error shape); `Cell<T>::get` exists only `where T: Copy`; `Result::unwrap` only `where E: Debug`; `Iterator::flatten` only where the item is iterable. The decisive precedent, though, is **svd2rust itself**: a PAC already rejects writes to read-only registers by *precisely this mechanism* — `write` is bounded on `REG: Writable`, and a read-only register's `REGrs` simply never implements it. `UnconstrainedWrite` is not a new pattern grafted onto the PAC; it is one more rung on the capability ladder the PAC is already built on (`Readable` → `Writable` → `Resettable` → `Unconstrained`*). Finally, `#[diagnostic::on_unimplemented]` is the ecosystem-standard way to make such bounds speak the domain's language — std uses it for `Sized`/`Iterator` errors, and axum and diesel use it to turn trait-resolution failures into actionable messages, which is exactly what "this register is write-constrained by its datasheet" does.

### A.7 Summary comparison


|                         | shadowing (main/PR 15)                                          | trait bound (proposed)                                                     |
| ----------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------- |
| mechanism               | same-name inherent method on wrapper wins name-first resolution | stock method's where-clause unsatisfied                                    |
| violation error         | E0061 (arity — no explanation)                                  | E0277 + custom datasheet message                                           |
| safe bypass             | yes: deref coercion / `&*` / UFCS / generic fns                 | none — every bypass is `unsafe`                                            |
| generic downstream code | leaks (gate invisible behind `Reg<R>`)                          | propagates (bound required, constrained REG excluded)                      |
| register type identity  | changes (`ConstrainedReg`) for constrained regs                 | unchanged everywhere                                                       |
| gated-path definition   | re-emitted per register × per operation                         | `write_witnessed` defined once, varies by assoc type                       |
| injection anchors       | alias rewrite + context-sniffing regex                          | deterministic `impl Writable for {REG}rs` blocks                           |
| patch footprint         | constrained registers only                                      | every register (one-line, mechanical) + generic.rs                         |
| trait-definition ripple | none                                                            | `Writable`/`Readable` gain assoc types; internal blanket impls need bounds |
| upstream story          | wrapper + alias rewriting (foreign to svd2rust)                 | assoc types + markers in the template (natural sidecar feature)            |


The one-line summary: **shadowing hides the door behind a curtain (name resolution); the trait bound removes the door from the wall (the method does not exist for that type).**

---



## Appendix B — Register Constraint Grammar v2, complete specification

This is the normative spec that a rewritten `docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md` and `defs.py` implement (roadmap step D). §4 is its summary. All examples below are real, from the STM corpus (§5).

### B.1 Overall shape

A constraint is a **discriminated union on `kind`**: the LLM picks one tag from eight, then fills a small kind-specific field set. Two shared objects are reused everywhere; there are no free-text micro-grammars anywhere. Every `Literal` is **guaranteed at collection-time pydantic parsing** (with per-constraint recovery and the B.4 repair/reject/re-prompt policy); token-level structured-output mode is a per-provider optimization on top — enabled where reliable (OpenAI), skipped for Groq OSS models, which frequently hard-error on `json_schema` mode and would turn recoverable drift into total loss (§6.1). Every register/field name and numeric value is validated against the SVD at collection.

```python
# ── shared across all kinds ─────────────────────────────────────
class ConstraintBase(BaseModel):
    kind: Literal["state_gate", "sequence", "write_once", "delay",
                  "read_effect", "clock_gate", "value_relation", "other"]
    severity: Literal["error", "warning"] = "error"
    consequence: str                  # what happens on violation (prose)
    datasheet_text: str               # VERBATIM, COMPLETE quote — the anchor for
                                      # deterministic PDF verification (§7.1)

class FieldRef(BaseModel):
    register: str                     # SVD-canonical name; resolved at collection
    field: str                        # SVD-canonical; no ranges, wildcards, or pseudo-fields
                                      # (whole-register conditions use an explicit flag,
                                      #  never field="")

class FieldCondition(FieldRef):
    state: Literal["cleared", "set", "equals"]
    values: list[int] = []            # required non-empty iff state == "equals";
                                      # >1 entry = OR-of-values; parsed from hex/bin/dec
                                      # strings, range-checked against SVD field width
    established_by: Literal["hardware", "software"] = "hardware"
    action_operation: Optional[Literal["write", "modify"]] = None
                                      # REQUIRED iff evidence == "software" (model_validator)
```

`established_by` is the load-bearing semantic distinction (kept from PR 15; renamed from `evidence_kind` via an interim `evidence`, final name settled with Ramla 2026-07-16):

- `"hardware"` — hardware establishes the state; software can only *observe* it → codegen emits a runtime **check** minting a **state witness** (`check_write_ready() -> Cr1WriteWitness`).
- `"software"` — the driver itself must establish the state → codegen emits a setup method minting an **action witness** (`set_cnf() -> CnfSetWitness`), performed via `action_operation`.

The envelope carries versioning:

```python
class RegisterInfo(BaseModel):
    ...
    schema_version: int = 1                    # v1 files lift mechanically to v2 (B.6)
    access_constraints: list[Constraint]       # the discriminated union
```

### B.2 The eight kinds

#### B.2.1 `state_gate` — the workhorse (~all of today's true positives)

An operation on a register/fields is permitted only while named field conditions hold; optionally, conditions must be re-established afterward.

```python
class StateGate(ConstraintBase):
    kind: Literal["state_gate"]
    target_register: str              # must equal the containing RegisterInfo —
                                      # deliberately redundant: a free consistency check
    target_fields: list[str] = []     # empty = whole register; currently enforced at
                                      # register granularity, recorded as a downgrade
    target_operation: Literal["read", "write", "modify", "any"]
                                      # "any" legal at extraction; EXPANDED to
                                      # read+write+modify deterministically at collection
    preconditions: list[FieldCondition]    # conjunctive
    postconditions: list[FieldCondition]   # software-evidence ONLY: an observed-state
                                           # postcondition is unenforceable and was PR 15's
                                           # silently-dropped class → v2 rejects with reason
```

Mode-gate, software evidence (`rm0091/2/usart1_brr`, ×37): *"This register can only be written when the USART is disabled (UE=0)."*

```json
{ "kind": "state_gate", "target_register": "USART_BRR", "target_fields": [],
  "target_operation": "write",
  "preconditions": [{ "register": "USART_CR1", "field": "UE", "state": "cleared",
                      "established_by": "software", "action_operation": "modify" }],
  "postconditions": [], "severity": "error",
  "consequence": "BRR writes while the USART is enabled are ignored or corrupt the baud rate",
  "datasheet_text": "This register can only be written when the USART is disabled (UE=0)." }
```

Hardware-flag gate (`rm0430/1/rtc_wutr`): *"This register can be written only when WUTWF is set to 1 in RTC_ISR"* → same shape with `established_by: "hardware"` (a check is emitted, not a setup method). Pre+post software action (`rm0008/1/rtc_cnth`, the MTQC replacement): software-evidence precondition `RTC_CRL.CNF state="set"` plus software-evidence postcondition `CNF state="cleared"`, both `action_operation: "modify"`. OR-valued equals (legalized drift): `required_state: "equals:0b01|0b10|0b11"` → `"state": "equals", "values": [1, 2, 3]`.

**Enforcement:** hardware preconditions → `witnessed_runtime_check` (composite state witness from one fresh read); software preconditions → `compile_gate` (action witness); postconditions → obligation + closure-scoped wrapper + reframe-as-precondition where the hazardous next operation is named (§3.1). Gated via the trait bound (§3, Appendix A).

#### B.2.2 `sequence` — ordered multi-step protocols

```python
class Step(BaseModel):
    register: str
    operation: Literal["write", "read"]
    value: Optional[int] = None       # required for writes with prescribed values

class Sequence(ConstraintBase):
    kind: Literal["sequence"]
    steps: list[Step]                 # ≥ 2, in order (collection rejects fewer)
    enables: Optional[FieldRef] = None  # what the completed sequence unlocks
```

Examples: RTC write protection (`rm0383/1/rtc_dr`) — write `0xCA` then `0x53` to `RTC_WPR`, enabling protected RTC registers (today mangled into `equals:0xCA then 0x53`); I2C ADDR clearing (`rm0033`) — read `SR1` then read `SR2` (two read steps); AES key order (`rm0493/1/aes_keyr7`); GPIO LCKR lock (`rm0033/1/gpioi_lckr`); the two-word DBGMCU auth key.

**Enforcement:** `compile_gate` — the strongest linear-types fit in the grammar: each generated step method consumes the previous step's token (`write_key1() -> Key1Written`, `write_key2(Key1Written) -> FlashUnlocked`), so ordering is a pure type-level property; only the writes themselves are runtime. The terminal token is the witness required by the unlocked operation.

#### B.2.3 `write_once` — lock bits

```python
class WriteOnce(ConstraintBase):
    kind: Literal["write_once"]
    target_register: str
    target_fields: list[str] = []
    reset_scope: Literal["system_reset", "power_cycle"]
```

Examples: `rm0493/1/exti_lockr` (*"This bit is written once after reset"*); TIM `BDTR.LOCK` levels.

**Enforcement:** `compile_gate` via a **capability**: a non-`Copy` `LckrWriteCap` minted once in the peripheral singleton; the gated write consumes it by value; a second write is E0382. Honest affinity — the datasheet property *is* "at most once."

#### B.2.4 `delay` — time/cycle waits

```python
class Duration(BaseModel):
    value: int
    unit: Literal["cycles_ahb", "cycles_apb", "us", "ms"]

class Delay(ConstraintBase):
    kind: Literal["delay"]
    after: Step                        # the operation that starts the clock
    duration: Duration
    before: Optional[FieldRef] = None  # the dependent access, if the text names one
```

Example: *"wait at least two APB clock cycles after enabling the peripheral clock before accessing its registers."*

**Enforcement:** hybrid — codegen emits `wait_after_x() -> DelayElapsed` (dummy reads / nop loop); the *ordering* is compile-gated via the token, the *duration* is runtime. With no named dependent access it degrades to `dynamic_check`.

#### B.2.5 `read_effect` — read side-effects (documentation-only)

```python
class Effect(BaseModel):
    field: str
    becomes: Literal["cleared", "set"]

class ReadEffect(ConstraintBase):
    kind: Literal["read_effect"]
    read_register: str
    effects: list[Effect]
```

Examples: `rm0386/1/dsi_isr1` (*"always cleared after a read"* — today misextracted as 14 postconditions); USART_DR read clears RXNE.

**Enforcement:** `doc_only` — reads cannot usefully be forbidden, but this metadata (a) feeds the Constraint Validator, (b) tells codegen when a checking read would itself perturb state (the self-defeating same-register read-gate case, rejected at codegen), and (c) where a real ordering obligation exists, the decision tree routes the model to `sequence` instead.

#### B.2.6 `clock_gate` — peripheral clock enable (the most common currently-inexpressible constraint)

```python
class ClockGate(ConstraintBase):
    kind: Literal["clock_gate"]
    clock: FieldCondition              # e.g. RCC_APB1ENR.I2C1EN, state="set",
                                       # established_by="software", action_operation="modify"
```

Peripheral-scoped: the LLM may emit it on any register file of the peripheral; collection deduplicates and hoists it to the peripheral entry in `manifest.json`. Corpus evidence: `rm0008/1/rcc_ahbenr` (*"When the peripheral clock is not active, the peripheral register values may not be readable … the returned value is always 0x0"*).

**Enforcement:** `compile_gate` at the **handle**, not per register (gating every method is an unacceptable API tax): `rcc.enable_i2c1() -> I2c1ClockEnabled`, and the I2C1 block accessor requires the token once — mirroring the HAL `.constrain()` idiom while staying inside the PAC.

#### B.2.7 `value_relation` — inter-field value relationships (documentation-only)

```python
class ValueRelation(ConstraintBase):
    kind: Literal["value_relation"]
    fields: list[FieldRef]             # the related fields; the relation itself stays
                                       # in datasheet_text — an expression language would
                                       # be unreliable for the LLM and unenforceable in the PAC
```

Examples: *"CR2.FREQ must equal the APB1 frequency in MHz"*; *"keep RXONLY clear while BIDIMODE is set"* (`rm0454/1/spi1_cr1`). Always `doc_only`.

#### B.2.8 `other` — escape valve and discovery queue

```python
class Other(ConstraintBase):
    kind: Literal["other"]
    description: str                   # the requirement in the model's own words (clustering)
    involved: list[FieldRef] = []      # SVD-validated like all refs
```

For *genuine access/ordering requirements that fit no kind* — corpus examples: *"channel selection bits must remain unchanged during sample cycles"* (`rm0008/1/adc2_smpr1`), *"do not make changes to this register after initial programming"* (`rm0008/1/otg_fs_device_dcfg`). **Not** the destination for routed-out non-constraints (w1c, access-width, privilege, validity notes — those emit nothing). `doc_only` **by construction** — can never gate an operation or break a build. Collection reports the **`other`-rate per device/run**: a spike is a prompt regression; the steady-state rate is the grammar-coverage paper metric. This institutionalizes how `sequence`/`clock_gate`/`write_once` were discovered (mining v1's 729 empty-pre/post constraints, ~347 of them real but inexpressible).

### B.3 Computed annotations (never LLM-emitted)

At collection, each constraint gains:

```python
enforceability: Literal["compile_gate", "witnessed_runtime_check", "dynamic_check", "doc_only"]
# derived deterministically from (kind, established_by, target_fields) — models would guess it
```

Codegen records `enforced_as` (same enum) per constraint in `manifest.json`, making downgrades visible (field-granular gate enforced at register granularity; a `delay` with no gateable successor). Paper metrics — fraction *classifiable* as compile-enforceable and fraction *actually enforced* — are computed from manifests, not hand counts.

### B.4 Collection rules

**Repair deterministically (lossless, logged):** hex/bin value strings → `int`; `"any"` → three per-operation constraints; v1 → v2 lift (B.6); SVD-canonical name casing; enum *names* → values via SVD `enumeratedValues` (the `"enabled"` drift case); `%s`-placeholder filename repair.

**Reject (judgment required; structured error, one automated re-prompt round, then per-constraint drop with manifest entry — never abort a peripheral):** unknown `kind`/`state`; `established_by:"software"` without `action_operation`; names unresolvable in the SVD; values exceeding field width; `sequence` with < 2 steps; observed-state postconditions; write constraints on SVD read-only fields (FP by construction).

**Routed out at the prompt (not constraints; emit nothing):** w1c/rc_w flag semantics (SVD `modifiedWriteValues`), read-to-clear behavior standing alone (→ `read_effect` if worth recording), access-width requirements, secure/privileged-access notes, "value is don't-care" validity notes, reset behavior.

### B.5 The decision tree (prompt)

> order of operations mentioned → `sequence` · wait/time → `delay` · "before any access"/clock enable → `clock_gate` · "once until reset" → `write_once` · "reading clears/affects" → `read_effect` · a state condition on an operation → `state_gate` · pure value relationship → `value_relation` · a genuine requirement fitting none → `other` · not a requirement at all (w1c, width, privilege, validity note) → emit nothing.

### B.6 v1 → v2 lift (mechanical, lossless)

| v1                                                     | v2                                                                         |
| ------------------------------------------------------ | -------------------------------------------------------------------------- |
| `RegisterAccessConstraint`                             | `StateGate`                                                                 |
| `FieldState.register_name` / `field_name`              | `FieldCondition.register` / `field`                                         |
| `required_state: "cleared"` / `"set"`                  | `state: "cleared"` / `"set"`                                                |
| `required_state: "equals:<v>"`                         | `state: "equals", values: [parse(v)]`                                       |
| `required_state: "equals:A\|B\|C"`                     | `state: "equals", values: [A, B, C]`                                        |
| `evidence_kind: "observed_state"` / `"software_action"`| `established_by: "hardware"` / `"software"`                                       |
| `target_operation: "any"` / `"read/write"`             | expanded to per-operation `state_gate`s                                     |
| `severity: "info"`                                     | `"warning"`                                                                 |
| unparseable `required_state` (`"unlocked"`, `"written"`, `"equals:X then Y"` …) | reject with reason → re-prompt round (most are `sequence`/`other` in v2) |

---

## Divergence log

*(Record departures from this plan here as they happen, per project convention.)*

- 2026-07-16 (grammar naming): the v2 condition key `evidence` is renamed **`established_by`** (Ramla) — it states the extracted world-fact (who brings the state about) instead of the enforcement mechanism it feeds; values unchanged. v1's `evidence_kind` wire-format key is historical and stays; the lift maps it. Swept through defs.py, collection, tests, grammar doc, Appendix B, and the paper draft.
- 2026-07-16 (step J, first half — the HAL demo): `eval_hal/` compiles the UNMODIFIED stm32f4xx-hal 0.23.0 (the crates.io release built against stm32f4 0.16.0) under `[patch.crates-io]` against the injected PAC; pinned as `test_hal_demo`. Result: (1) **true enforcement — 14/14**: every place the HAL touches I2C CR1 (8 in `i2c.rs`, 6 in `i2c/dma.rs`) fails with the datasheet diagnostic, zero false hits anywhere else in ~30k lines; baseline (pristine PAC) compiles clean, so adoption costs nothing where nothing is constrained. (2) **§3's "churn edge" is bigger than predicted**: the plan called generic-over-registers driver code "rare — HAL register code is macro-generated and monomorphic," but stm32f4xx-hal 0.23 moved its serial layer to trait generics (`UartRB` associated register types), and generic definitions calling read/write/modify fail to type-check without the marker bounds — 14 errors across `serial.rs`/`serial/uart_impls.rs` even though no UART register is constrained. Quantified adoption cost: ~10 mechanical one-line where-clause additions in one module. This is inherent to conditional method availability (no post-monomorphization errors in Rust); the honest paper claim splits the two numbers: monomorphic driver code = perfect precision, trait-generic driver code = small quantified patch. Second half of J (the fork + regenerate.sh + publishing) remains.
- 2026-07-15 (step E): stage-0 lint complete; published stats live in `docs/constraints_corpus_stats.md` (not `optimization/test_outputs/` — a citable, committed snapshot beats a git-ignored one). Key dispositions: within-register exact dedup drops 91 (2.0%); cross-INSTANCE duplication (589) is flagged, not dropped — per-instance rows are what codegen injects, so the plan's "−36% dedup" mass is deliberately retained; post-dedup 4,362 unique → 2,857 v2 state_gates (2,243 witnessed_runtime_check / 614 compile_gate) + 35.6% whole-constraint rejects, dominated by SVD-unresolvable names under the one-SVD-per-RM projection (~307 of those are single-device coverage misses, 28.5% reject rate with all SVDs; per-device projection is arguably correct — a constraint is enforceable only for registers the device has). New reject classes verified genuine by spot-check: RTC_WPR 0xCA53 vs 8-bit field (width), FLASH_SR.BSY writes (read-only target), USART_SR.TC (w1c postconditions), 8 self-defeating read gates. **`%s` root cause documented, NOT fixed** (stats doc §"%s root cause"): SVD `<dim>` templates — not derivedFrom as §5.1 guessed — flow through `agent_tools/svd_parsing.py:70-77` → `core/s1a_generator.py` worklist → filenames; the coverage comparator keys the SVD side by the SAME templates, so a worklist-only fix would desync the live coverage loop and is unverifiable offline — three-call-site fix proposal recorded for a live-run session. Step C note: the IR refactor's motivation (PR-15's 40% duplication) was discarded with PR 15; the fresh emitter is ~700 lines with a Plan/emit split — C reduced to "extract a naming module if step I bloats it."
- 2026-07-15 (step H): cross-register witnesses landed as inherent check methods taking the SOURCE register(s) as `&Reg<SRCrs>` parameters (`check_write_ready(&self, cr: &Reg<CRrs>)`), same-peripheral (`super::<reg>::`) and cross-peripheral (`super::super::<periph>::<reg>::`) resolved from the datasheet's `<PERIPHERAL>_<REGISTER>` prefix vs the target peripheral's instance-stripped base. Fixtures are verbatim generator corpus output: SPI_TXCRCR read-gate ⇐ SPI_SR.BSY (rm0008) and RCC_SSCGR ⇐ RCC_CR.PLLON (rm0368); cross-peripheral verified by a synthetic RTC_DR ⇐ PWR_CR.DBP compile probe (real corpus RTC constraints bundle the WPR key sequence, which is step I/sequence material). Read gating consequence handled: the peripheral RegisterBlock's `#[derive(Debug)]` is stripped when a read gate is present (debug-printing performs a read) — documented API divergence. Marker walk now keys (peripheral, spec, op) so same-named specs elsewhere keep their markers; injection accepts multiple constraint inputs in one shot. Compile-fail table grew to 11 rows (witness-less read of read-gated register; witness-less cross-register write).
- 2026-07-15 (step D): grammar v2 landed ALONGSIDE intact v1 in `defs.py` (v1 stays the generator wire format until step F; codegen consumes v1). Appendix-B gaps resolved during implementation: `FieldRef` gains an explicit `whole_register: bool` flag (B.1 referenced but never defined it; the corpus encodes IWDG_KR==0x5555 with `field_name: ""` — repaired to the flag at lift, ×25); observed-state postconditions drop ELEMENT-level with a structured reject while the precondition gate survives (whole-constraint rejection would discard the sound dominant part — consequence: all v1 postconditions default to hardware evidence and drop loudly until step-F re-extraction adds `evidence`); unparseable `required_state` anywhere rejects the WHOLE constraint (dropping a precondition would silently weaken a gate); `action_operation` on hardware evidence is dropped as a logged repair; enum-name repair ("enabled") happens at collection with `--svd-dir` (the lift itself has no SVD access; `agent_tools/svd_parsing.py` exposes counts, not names — collection carries its own minimal SVD index w/ derivedFrom + dim expansion); v1 models now `extra="allow"` so PR-15-style `evidence_kind` keys survive for the B.6 lift row; vacuous v1 constraints (729 in corpus) lift losslessly with a `vacuous_no_conditions` lint flag rather than rejecting. Corpus sweep: 4,453 v1 → 4,379 v2 state_gates, 3.0% whole-constraint rejects, zero crashes across all 30 RMs.
- 2026-07-15 (step B): two refinements over Appendix A while implementing. (1) Witness associated types live on NEW `WriteGate`/`ModifyGate`/`ReadGate` traits implemented ONLY by constrained registers — not on `Writable`/`Readable` as sketched — so the stock trait definitions and every existing register impl stay untouched; unconstrained registers need only the one-line `Unconstrained*` marker impls (appended at end-of-file, 445 files, mechanical). (2) No visibility widening at all: injected code lives inside `mod generic` and the peripheral modules, so private-field access is legal — the old `pub(crate)` patch class disappears. Also settled in code: a `write` constraint gates BOTH the write surface and the modify surface (a modify performs a write), each with its own witness; same-register read gates are rejected as self-defeating; `severity=warning` currently hard-gates like `error` (the `#[deprecated]` shadow is deferred, TODO in emitter). Enforcement is pinned by a nine-row compile-fail table incl. the PR-15 bypass (ascribed `&Reg` ref and UFCS → E0277).
- 2026-07-15 (step A): the plan's "stub mini-PAC fixture" is replaced by provisioning the **published crates.io package** (`stm32f4` 0.16.0, checksum-verified, cached, `get_pac.py`) — svd2rust PACs publish their generated source, so one 4 MB download yields a byte-authentic `generic.rs` + device modules; a hand-maintained stub could drift from real svd2rust output, and fidelity was the whole point of §2 defect 1. Consequence: the canonical test PAC lives at `vendored/pac/stm32f4/` (git-ignored), not in the `stm32-rs` submodule; `constraint_test/Cargo.toml` repointed. CI's enforcement-test step is `continue-on-error` until step B lands (the pre-B injector cannot handle the multi-file crates.io layout — expected, documented); step B removes that line.
- 2026-07-15: initial draft (from the PR-15 multi-agent review + STM corpus audit; session artifacts: nine agent reports + `curated_stm_constraint_examples.json` in the session scratchpad).

