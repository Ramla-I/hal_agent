# Register Constraints — Full Plan (grammar v2, encoding, PR 15, extraction quality, validator)

**Status:** LARGELY IMPLEMENTED. This began (2026-07-15) as the design plan for the enforcement arm; most of it has since shipped. The **Divergence log** at the end is the authoritative record of what was built and where the implementation departed from this plan; the constraint grammar is specified separately in **[`REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`](REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md)**. The sections below give the design and its rationale (some still in the original planning voice).
**Date:** 2026-07-15 (plan); see the Divergence log for implementation dates
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



## 1. Background: PR 15 and the chosen encoding

The enforcement arm was bootstrapped from a review of PR #15
(`cursor/stabilize-pac-codegen`), which prototyped witness-token gating with
`ConstrainedReg` wrapper types + method shadowing. A multi-agent deep-read plus
adversarial `cargo check` judged it **right direction, not mergeable as-is**:
the emitted Rust did not compile; the wrapper left a safe, silent bypass through
`Deref` (`&Reg<CR1rs>` reaches the stock `write`); enforcement had never been
through rustc (all four tests silently skipped — the origin of the CI gate in
§9); witnesses were not instance-bound; and `equals:` values were spliced
verbatim into Rust (an injection surface, and `0b01|0b10` mis-parses under
operator precedence).

**Disposition (settled 2026-07-15):** PR 15 was closed unmerged with **zero code
cherry-picked**. Everything was re-implemented fresh under (a) **trait-bound
gating** — the witness-free method *does not exist* on a constrained register, so
there is no `Deref` hole (§3, Appendix A) — and (b) the settled **witness-token
terminology** (§3). The good ideas were kept (composite per-operation witnesses
from one fresh read, full write-surface gating, the `established_by` dichotomy,
grouped `manifest.json`); the bad ones dropped (Deref gating, action chains ahead
of extraction evidence, blind prompt changes). No commit from the branch enters
main's history.

---



## 3. Target encoding: trait-level gating in `generic.rs`

**Terminology (settled 2026-07-15):** the umbrella term is **witness tokens**, restoring the original grammar-doc/README language — PR 15's "proof" overclaims (a token attests a *past observation*, not a present guarantee; see §3.1 TOCTOU). Four distinct roles, never conflated: **state witness** (minted by a runtime check of hardware state), **action witness** (minted by performing the required software action), **obligation** (a duty to discharge — postcondition cleanup), **capability** (authority to do X at most once — write_once). Verbs are reserved too: **validate** = the LLM pipeline judging extracted facts (s4 Validator, Constraint Validator); **check** = the runtime inspection in generated code (`check_write_ready()`, matching the grammar doc's "runtime check" and the `state_witnessed` enforceability class — not "verify", which reads as static/formal and collides with the Validator); **enforce** = what the compiler does at compile time. Use these words everywhere: grammar doc, `defs.py` docstrings, generated Rust identifiers, paper ("witness-gated", not "proof-gated"). **Both enforceable classes are compile-time witness-gated** — the operation will not compile without the witness; they differ only in what mints the witness (a fallible runtime check of hardware state → `state_witnessed`, vs the program's own action/ordering/capability → `action_witnessed`), NOT in whether enforcement is compile-time. Do not frame these as "compile-time vs runtime enforcement": both establish the condition at runtime, and both gate the use at compile time (Ramla, 2026-07-22).

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

The constraint grammar (grammar v2) is specified in full in its own document,
**[`REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`](REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md)**
— the normative spec (the discriminated union of eight kinds, the shared
envelope, the `FieldCondition` model, computed enforceability, collection /
repair-vs-reject rules, the decision tree, and the v1→v2 lift). This plan does
not restate the grammar.

The one plan-level point: **enforceability is computed, never LLM-emitted** —
collection derives it from `(kind, established_by, target_fields)` and records
`enforced_as` per constraint in the manifest. That feeds the paper's coverage
metric: the fraction of extracted constraints that are compile-time
witness-gated, times the fraction actually enforced.

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

**Status:** steps A, B, D, E, F, G shipped; H shipped for cross-register/cross-peripheral gating (`sequence` emission partial); C reduced to "extract a naming module if needed" (not done, not needed yet); I (action chains / closure-scoped wrappers) and J (external fork + distribution) partial. Field-level gating (§12) is built and opt-in. The Divergence log has the specifics and dates.

| step | content | depends on | folders touched / created |
| --- | --- | --- | --- |
| **A. CI/compile harness** | §9. No generator changes. | — | **create** `.github/workflows/`; edit `applications/pac_codegen/test_codegen.py` (SKIP→FAIL); `applications/pac_codegen/` (PAC-generation helper, cached under `vendored/`); `applications/pac_codegen/constraint_test/` (stub-PAC fixture) |
| **B. Soundness re-cut** | trait-level gating (§3): composite witnesses, full write-surface gating, `unsafe`-only escape, `write_when_ready`, severity=warning→deprecated, loud failures on dropped semantics. Golden + must-fail tests. | A | `applications/pac_codegen/` (`rust_codegen.py` rewrite: generic.rs patch + per-register emission); `applications/pac_codegen/constraint_test/` (new golden, must-fail cases, `main.rs`); `test_codegen.py` (E0061→E0277 assertions) |
| **C. Generator IR refactor** | `PeripheralPlan` IR + single naming/escaping module + dumb renderer; behavior-preserving; kills ~40% duplication, keyword bugs, repeated normalization. | B | `applications/pac_codegen/` (split `rust_codegen.py` → **new** `ir.py`, `naming.py`, `render.py`); `constraint_test/` goldens regenerate byte-identical |
| **D. Grammar v2 schema + collection** | the grammar (`REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`): kinds, Literals, structured values, v1→v2 lift, repair/reject policy, computed enforceability, per-constraint drops. No prompt changes yet. | — (parallel to A–C) | `defs.py` (repo root); `docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`; `applications/pac_codegen/collect_constraints.py`; `tests/` (schema-consistency test) |
| **E. Stage-0 lint + corpus cleanup** | §7.0 stage 0 on the 30-RM corpus; fix `%s` plumbing; dedup; publish cleaned corpus stats. | D | `applications/pac_codegen/` (lint in/next to `collect_constraints.py`, reusing `agent_tools/svd_parsing.py`); `core/` + `utils/result_saver.py` (`%s` run-dir naming fix); stats → `optimization/test_outputs/` |
| **F. Prompt v2 + extraction eval** | §6, with a fixed-sample eval proving the model populates new fields; real-STM few-shots. | D | `prompts/` (`register_info_stm.py`, `examples.py`); `tests/`; eval harness under `optimization/generator/` with runs in `optimization/test_outputs/` |
| **G. Constraint Validator + verified-constraints datasheet** | §7 stage 1 + quote anchoring + derived context; corruption calibration → β/F1 shipped human-free. Alongside: `build_constraints_datasheet.py` → `verified_datasheet/constraints/stm.csv` (30 RMs, `reference_manual` column) + `annotate_constraints.py`; Ramla annotates **asynchronously, never blocking**; α on real data measured retrospectively as annotations accumulate. | E | **create** the constraint validator — `core/quote_anchor.py` + `core/constraint_validator.py` (judge, quote anchor); the corruption/calibration tuning harness (`tune_constraint_validator/`) and the `verified_datasheet/` additions (**new** `constraints/stm.csv`, `build_constraints_datasheet.py`, `annotate_constraints.py`; README note) ship in a follow-up PR (branch `constraint_validator_tuning`, see the 2026-07-28 divergence entry); `prompts/` (judge prompt); reuses only the **artifacts** of `context_retrieval/preprocessing/` (chunked markdown) + `agent_tools/md_ops.py` — context is static quote-anchored extraction, **no semantic retrieval in the judging path** (see §7.1) |
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

## 12. Field-level gating (built, opt-in — 2026-07-22)

**Status: implemented behind a default-off flag.** F-1–F-4 below are done and compile-verified. Field-level gating is enabled with `--field-level-gating` on `rust_codegen.py` / `inject_from_run.py` (or `RegisterPlan(..., field_level_gating=True)`). **Default off: with the flag absent the emitter behaves exactly as before — field-scoped constraints are skipped with a warning** — so the risky per-field accessor patching is never applied unless explicitly requested (Ramla's requirement: retain current codegen if the option is disabled). Design choice: **(a) witness parameter on the field accessor** was implemented rather than the (b) separate-accessor sketch below — it is the most direct and the unwitnessed field write fails with **E0061** (wrong arg count) rather than a custom E0277 message; the trade-off (less-pretty diagnostic, and existing `w.field()` callers break — which *is* the enforcement) was accepted for simplicity. Everything from here down is the original design writeup, kept for context.


**The problem.** A `state_gate` carries `target_fields` (§B.2.1): empty means the whole register, non-empty means the datasheet gated only specific fields (e.g. *"CC2S bits are writable only when the channel is OFF"* → `target_fields: ["CC2S"]`). The current emitter gates the whole register regardless — it never branches on `target_fields`. For a field-scoped constraint that is an **unsound-free but over-restrictive** downgrade: it demands the precondition for writes to *unrelated* fields of the same register. For a hardware-established precondition that is merely an extra check (a false block when the flag happens not to hold); for a **software-established** precondition it can be actively wrong — it forces the developer to *perform* setup (disable the peripheral, clear a bit — possibly in *another* register named by the precondition) that the field they wanted to write never required, which can corrupt the intended operation or push them to `unsafe`. (Discussion with Ramla, 2026-07-22.)

**Default behavior (gating off).** With the flag absent the emitter **skips** any constraint with non-empty `target_fields` and prints a warning (`RegisterPlan.__init__`); whole-register constraints on the same register are unaffected, and a register whose constraints are *all* field-scoped ends up with no gate (`emitter_rejected` in the injection report). The field scope is preserved in the grammar and enforced only when the flag is set. **This matters at scale: 46.4% of the corpus (1,929 of 4,160 constraints) is field-scoped** — mostly single-field (1,564), so field-level gating covers roughly half of the enforceable corpus; it is the highest-value codegen item after the whole-register `state_gate`.

**The mechanism.** A svd2rust PAC exposes per-field *writer accessors* on the register writer — e.g. `impl W<CR1rs> { pub fn stop(&mut self) -> STOP_W<CR1rs> { … } }` — the `w.stop()` you call inside a `write`/`modify` closure. So the gate can attach to the **field-writer accessor** of exactly the constrained field instead of to the register's `write`/`modify` method: only a closure that touches that field demands the witness; writing sibling fields compiles freely. There is no isolated single-field *hardware* write to hang a gate on (the write is always whole-register), but there is a single-field *setter within* the whole-register write, and that is the correct gate point.

**Design choices (weighed; (a) was chosen — see the status note above).**
1. **API shape of the gated field setter.** (a) add a witness parameter to the accessor — `w.stop(witness).set_bit()` — most direct but breaks the fluent `w.stop().set_bit()` idiom every HAL uses; (b) emit a *separate* gated accessor — `w.stop_when_ready(witness)` — leaving the stock `w.stop()` gated off via a marker; (c) a trait bound on the field-writer type. (b) is the least disruptive to existing HAL code, but **(a) was implemented** for directness (the unwitnessed write fails with E0061); (c) remains the route to a custom E0277 message.
2. **read/modify interaction.** A `modify` reads all fields then writes back; the constraint is about *setting* the field, so the gate lives on the field setter inside the closure, not on `modify` itself.
3. **Codegen surface.** Whole-register gating patches one generic `write`/`modify` path; field-level gating patches the per-field writer accessors in each constrained register's module — more files, generated per register. The marker-trait machinery (§3) generalizes: a `FieldWriteGate<REG, FIELD>` marker keyed by (register, field).

**Steps (all done, 2026-07-22).**
- **F-1 ✓** — `FieldGate` on `RegisterPlan`; `generate_constraint_module` emits a per-field witness + `check_<field>_field_ready()`; `patch_field_accessors` rewrites `pub fn <field>(&mut self)` → `pub fn <field>(&mut self, _witness: &super::constraints::<W>)` in the register module. Only the constrained field's accessor changes; the register's own `write`/`modify` keep their Unconstrained markers (siblings unaffected).
- **F-2 ✓** — compile test `test_field_level_gating_compiles_and_enforces` (fixture `constraint_test/stm32f405_i2c1_start_field.json`): the witnessed path and a sibling-field write (`w.pe()`) compile; the unwitnessed `w.start()` fails with **E0061**. Restores the PAC byte-for-byte.
- **F-3 ✓** — `inject_from_run`'s report `planned` row records `field_gates: [...]` alongside the whole-register `gates:`, so field-granularity enforcement is visible in the run report.
- **F-4 ✓ (via the flag)** — with `--field-level-gating` the previously-skipped field-scoped constraints are enforced through the new path; the corpus re-measurement of the forgone 46.4% is a follow-up run.
- Default remains skip-and-warn, so no incorrect over-gating ever ships unless the flag is set.

**Known soundness gap: the whole-register write bypass (Ramla, 2026-07-23).** The field gate rides on the field's *writer accessor* (`w.crcen()`), so it soundly gates `modify` — a `modify` reads the current register and writes it back, retaining fields the closure does not touch, so the gated field cannot change without `w.crcen(&witness)`. But `write` / `reset` / `write_with_zero` compose the whole register from a *base* value (reset or zero) and store all of it, so they write the gated field too (to its reset value), and those surfaces are **not** gated. A whole-register `write` is therefore an unchecked path that can reset the gated field while its precondition is false. We chose to leave it open rather than gate it, because gating `write` would force every whole-register write to carry a witness — the over-restriction field-level gating exists to avoid (Ramla's call: warn, don't hard-gate). A per-call *compile warning* there is **not expressible in Rust**: withholding the generic `write` and adding a concrete `#[deprecated] write` collides with the generic method (E0592 "duplicate definitions" — inherent-method coherence does not use the `UnconstrainedWrite` where-clause to disqualify the overlap), and Rust has no other per-call warning mechanism; the only per-call signal is a hard error. So the bypass is treated like `unsafe`: legal but acknowledged, and **flagged two ways**. (1) At generation time — `patch_field_accessors` prints a per-register warning that the whole-register write stays ungated. (2) In the crate itself — `inject_constraints_module` appends a `///` caveat to each field-gated register's type-alias doc (the generic `write` cannot be annotated per-register, but the register's own doc is ours to extend), so a developer looking up how to write the register sees the caveat in rustdoc / IDE hover, right next to the `write` link. Pinned by `test_field_level_gating_compiles_and_enforces` (asserts the warning fires, the caveat is in the register doc, and that the whole-register write compiles, so any future change to the write surface is deliberate). Closing it would require design (c) (a trait bound on the field-writer that also bounds `write` on the field witness) or accepting the hard gate.

**Deferred within field-level gating:** field-scoped *read* constraints (no writer to gate — a field read still goes through the whole-register read); a custom E0277 diagnostic (would need design (c), the trait-bound-on-field-writer route); field-scoped postconditions (roadmap step I).

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



## Appendix B — Register Constraint Grammar v2

The complete normative grammar specification now lives in its own document:
**[`REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`](REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md)**
(the eight kinds with per-kind examples, the shared envelope, computed
enforceability, the collection repair-vs-reject rules, the decision tree, and
the v1→v2 lift). It was formerly inlined here; it was moved out so the grammar
has a single source of truth.

---

## Divergence log

*(Record departures from this plan here as they happen, per project convention.)*

- 2026-07-28 (constraint validator split; tuning + verified-constraints datasheet moved to a follow-up PR — Ramla's call): to keep this PR focused on the enforcement mechanism, step G was split. **Stays in this PR:** the constraint validator itself — `core/quote_anchor.py` (deterministic anchoring, §7.1) and `core/constraint_validator.py` (the judge, §7.0), wired into `core/s0` (`--constraint-validation`) and `inject_from_run.py` (`--chunks`). It was pulled out of the original one-folder `constraint_validator/` package into `core/` to match the `core/s4_validator.py` ↔ `optimization_validator/` convention (product in a real location; a leaf tuning folder imports it, never the reverse). **Moved to the `constraint_validator_tuning` branch (follow-up PR):** the calibration harness (`tune_constraint_validator/` — corruption + calibrate) and the verified-constraints datasheet additions (`verified_datasheet/build_constraints_datasheet.py`, `annotate_constraints.py`, `constraints/stm.csv` + README, its test). Product tests (`tests/test_quote_anchor.py`, `tests/test_constraint_validator.py`) stay; the tuning tests travel with the harness. Pure relocation — no behavior change; the moved/split suites are green and every consumer imports cleanly.
- 2026-07-27 (grammar v1 fully removed; codegen migrated to v2; `schema_version` dropped — Ramla): the pipeline is now grammar-v2 only, end to end. The retired v1 access-constraint grammar (the `FieldState`/`RegisterAccessConstraint` models + the B.6 lift) lives ONLY in `applications/pac_codegen/convert_v1_to_v2.py`, the single migration tool that converts old v1 generator runs to v2 (verified to reproduce the v2 fixtures byte-for-byte). The **emitter (`rust_codegen.py`) now consumes `access_constraints_v2`** — it previously consumed v1 while v2 was only the analysis/validation layer; the migration was verified **byte-identical** (the golden test regenerates the same Rust from the converted fixtures) and completes native-v2 injection (`inject_from_run` selects v2 gates directly). Removed two vestigial `RegisterInfo` fields: **`access_constraints`** (always `[]` under v2) and **`schema_version`** (always `2` once v1 is gone — the "already v2" checks now key off the presence of `access_constraints_v2`). Swept the generator + validator prompts, the extraction eval, `verified_datasheet/build_constraints_datasheet.py` (reads v2, maps to the unchanged CSV triple shape), collection, and all tests (v1-wire-format tests condensed and moved to `tests/test_convert_v1_to_v2.py`). Full suite green (209 Python + 6 PAC, golden byte-identical). The constraint grammar spec was also pulled out of this plan (former §4 body + Appendix B) into `REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md` as the single source of truth.

- 2026-07-24 (target_operation restricted to {read, write, any}, `modify` dropped — Ramla's call): a datasheet constrains the two bus operations (read, write); svd2rust's `modify()` is a software read-modify-write, and offering "modify" as a *target* invited a category error — datasheet prose "modify/modified/change a register" means *writing* it, so nearly all corpus `modify` rows were mislabeled writes (the 2026-07-17 corruption entry already saw this: LPTIM_CMP "restored the manual's word 'modified'"). Now: `StateGate.target_operation: Literal["read","write","any"]` with a before-validator coercing legacy `"modify"`→`"write"`; the v1 lift maps `"modify"`→write and `"any"`→read+write; collection expands `"any"` to read+write. In the emitter, `modify()` gating is **derived** as the read ∪ write union — a write target feeds {write, modify}, a read target feeds {read, modify}. This also **closes a soundness gap**: a read-constrained register's `modify()` (whose RMW performs the constrained read) was previously ungated. It grounds the separate modify witness on real semantics (a modify's obligations are a superset of a write's exactly when a read constraint exists) rather than the extraction artifact it was. Swept `defs.py`, `collect_constraints.py`, `rust_codegen.py`, the generator + validator-judge prompts, the grammar doc (`REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`), the paper draft (read/write table + caption), and the affected tests; refreshed the `spi1_txcrcr` read-gate golden (now carries the derived modify gate). 198 Python + 6 PAC compile/golden tests green (`LIDAR_REQUIRE_PAC_TESTS=1`). `action_operation ∈ {write, modify}` is unchanged — a different axis (the method used to *establish* a software precondition), where "modify" stays meaningful.
- 2026-07-23 (field-level gating: whole-register write bypass — Ramla's catch + call): the field gate covers `modify` and the field accessor but NOT the whole-register `write`/`reset`, which compose the register from a base value and so write the gated field unchecked. Ramla's call: warn, don't hard-gate (gating `write` would reintroduce the over-restriction). Attempted a per-call compile warning (withhold `UnconstrainedWrite` + concrete `#[deprecated] write`); it fails with **E0592** — Rust's inherent-method coherence treats the concrete `write` as a duplicate of the generic one despite the unsatisfiable `UnconstrainedWrite` bound, and there is no other per-call warning mechanism. Landed Option 2: leave `write` open, flag the gap two ways — a **generation-time** warning (`patch_field_accessors`) and a **caveat in the register's own type-alias doc** (`inject_constraints_module`, so it surfaces in rustdoc/IDE where the generic `write` can't be annotated per-register) — document it as an acknowledged bypass in §12, and pin it with a compile test (warning fires; register-doc caveat present; whole-register write compiles). No change to the default (whole-register) path, which gates write+modify together and has no such gap.
- 2026-07-22 (field-level gating built, opt-in — Ramla): F-1–F-4 implemented behind a **default-off** flag (`--field-level-gating` on `rust_codegen.py`/`inject_from_run.py`, `RegisterPlan(field_level_gating=...)`), so the current codegen is retained exactly when disabled (Ramla's requirement, in case per-field accessor patching breaks a PAC). Design (a) chosen over the plan's recommended (b): the field writer accessor gains a witness parameter (`w.start(&wit)`), so an unwitnessed field write fails with **E0061** (not a custom E0277). Compile-verified end-to-end on stm32f4: witnessed path + sibling-field write compile, unwitnessed `w.start()` rejected, PAC restored byte-for-byte (`test_field_level_gating_compiles_and_enforces`, fixture `stm32f405_i2c1_start_field.json`). §12 rewritten to "built, opt-in"; 112 codegen+core tests green. Deferred: field-scoped reads, custom diagnostic, field-scoped postconditions.
- 2026-07-22 (field-scoped constraints skipped, Ramla's rule): the emitter now **skips** any constraint with non-empty `target_fields` and prints a warning (`RegisterPlan.__init__`), rather than enforcing it at whole-register granularity. Reason: whole-register gating of a field-scoped constraint is sound but over-restrictive — it demands the precondition for writes to unrelated fields of the register, and for a software-established precondition can force incorrect setup of this or another register (Ramla's catch). New §12 "Field-level gating (planned)" documents the mechanism (per-field writer accessors — the PAC *does* expose them, correcting an earlier claim), the API choices, and the steps. Corpus impact measured: **46.4% (1,929/4,160) of constraints are field-scoped** and now forgone until field-level gating lands — the highest-value remaining codegen item. Golden fixtures are all whole-register (unaffected); the two `experiments/fixtures` cross-PAC fixtures are purely field-scoped and now emit nothing (their prior cross-PAC "enforcement" was the over-gating this removes). Pinned by `test_field_scoped_constraint_skipped_with_warning`.
- 2026-07-22 (enforceability naming, Ramla's rule): the enforceability enum's two enforceable classes are renamed `compile_gate` → **`action_witnessed`** and `witnessed_runtime_check` → **`state_witnessed`** (`dynamic_check`/`doc_only` unchanged). Reason: a witnessed runtime check is *also* compile-time gated — the operation will not compile without the state witness — so the old names implied a compile-vs-runtime distinction that does not exist. Both classes are **compile-time witness-gated**; both establish the condition at runtime (the software action and the hardware check both run at runtime). The real difference is only what mints the witness: the program's own action/ordering/capability (`action_witnessed`, no runtime check, standing guarantee) vs a fallible runtime check of hardware-controlled state (`state_witnessed`, a point-in-time observation, welded to the use). Swept through `defs.py` (enum + `derive_enforceability` + token-role comment), the grammar doc, the corpus-stats doc (numbers unchanged: 2,243 `state_witnessed` / 614 `doc_only` / 0 `action_witnessed`), the paper draft's translation subsection, and the two enforceability test files. Historical divergence-log entries keep the old names as dated records.
- 2026-07-17 (corruption directions, Ramla's rule): `change_operation` may never corrupt **toward** `modify` — a modify performs both a read and a write, so a rule over all writes (or reads) *entails* the modify claim, and `write→modify` / `read→modify` manufacture TRUE statements a correct judge must confirm. 6 of the first calibration's 7 op-swap "escapes" were exactly this (one, LPTIM_CMP, literally restored the manual's word "modified"). Away-from-modify stays falsifying (a rule about the RMW cycle says nothing about standalone ops). The 11 affected rows regenerated deterministically as `write→read`; the judge caught all 11. Corruption catch rate corrected **92.0% → 96.0%** (144/150); `change_operation` 76.7% → 96.7%; the remaining 6 escapes: 3 retargets (now caught upstream by the target-location gate), 2 undisambiguated sibling fields, 1 write→read (IWDG). Amendment recorded in `docs/validator_calibration.md`.
- 2026-07-17 (target location, Ramla's second rule): the location-unverified triage queue is resolved by two search refinements Ramla specified — SVD dim-template names carry a literal `%s` the manual never prints (`alrm%sr` stands for ALRMAR/ALRMBR), so the placeholder is **deleted before searching**; and the search allows **one edit** of difference, which absorbs whatever character the manual printed in the slot AND the manual's own family placeholders (`cpar4` under `DMA_CPARx`, gpioa's `idr` under `GPIOx_IDR`). Guard rails: tolerance only for names ≥ 5 chars (no drifting into prose: `calr` ≠ "call"); exact match stays primary. Measured on the 4,160-row corpus: location-unverified 17.8% → **5.1%** (673 → 194 rows, 479 recovered, zero lost); gate purpose intact — 96% of 468 deliberate retargets still rejected vs 97% with tolerance off (3 escapes bought 479 recoveries). F1 e2e stable at 19 registers, artifact byte-identical. Residue: quotes anchored in functional-description prose, CAN `f0r1`-vs-`CAN_FiRx` (two edits), doubled prefixes (`cec_cec_cr`).
- 2026-07-17 (target verification, Ramla's rule): a self-referential quote ("This register …") cannot verify its target textually, so the anchor LOCATION vouches — matched page (or ±2 neighbors: section headers precede continuation notes, register maps follow) must mention the target, with two measured refinements: family-placeholder names count as naming (AFIO_EXTICRX names EXTICR1–4) and manual-prose name forms are searched (run-file `dma_dmardlar` = manual `ETH_DMARDLAR` — the tail-segment candidates cut corpus location-unverified from 27.9% to 15.1% of anchored rows; widening the page window alone recovered <1%). The injection gate rejects self-referential+unlocated (`target_unverified_by_location`); the calibration's three retarget misses are pinned regressions; residual 15.1% = %s-placeholder names + USART/UART-style family aliases (triage queue).
- 2026-07-17 (step F): prompt v2 landed with an eval-driven loop — the 11-register golden eval exposed three prompt weaknesses in run 1 (enables emitted as a step; per-bit quote concatenation; ellipsis-stitched quotes), each fixed with one sentence and re-run. Final: parse 11/11, kinds 7/7 (incl. a correctly recognized RTC_WPR `sequence`), negatives 4/4 (w1c and access-width emit nothing), quote-anchor 9/10, `established_by` 7/10 (all three misses footnoted: RM0008's own RTC_CR-vs-SVD-CRL naming ×2, one ambiguous golden label — no systematic hardware/software confusion). Native-v2 wire format: `access_constraints` stays empty + `access_constraints_v2` + `schema_version: 2`; collection gains a native path (per-constraint pydantic recovery, dedup, full SVD lint, `constraint_source` in the manifest). Context cap for the eval raised 8k→12k chars (the RTC_WPR unlock page fell outside 8k). Cost: ~$0.017/run. **GO for full re-extraction** — pending Ramla's spend decision; follow-ups queued: B.4 one-round re-prompt for unresolvable_in_svd, field-level repair for unresolvable target_fields.
- 2026-07-16 (grammar naming): the v2 condition key `evidence` is renamed **`established_by`** (Ramla) — it states the extracted world-fact (who brings the state about) instead of the enforcement mechanism it feeds; values unchanged. v1's `evidence_kind` wire-format key is historical and stays; the lift maps it. Swept through defs.py, collection, tests, the grammar doc, and the paper draft.
- 2026-07-16 (step J, first half — the HAL demo): `eval_hal/` compiles the UNMODIFIED stm32f4xx-hal 0.23.0 (the crates.io release built against stm32f4 0.16.0) under `[patch.crates-io]` against the injected PAC; pinned as `test_hal_demo`. Result: (1) **true enforcement — 14/14**: every place the HAL touches I2C CR1 (8 in `i2c.rs`, 6 in `i2c/dma.rs`) fails with the datasheet diagnostic, zero false hits anywhere else in ~30k lines; baseline (pristine PAC) compiles clean, so adoption costs nothing where nothing is constrained. (2) **§3's "churn edge" is bigger than predicted**: the plan called generic-over-registers driver code "rare — HAL register code is macro-generated and monomorphic," but stm32f4xx-hal 0.23 moved its serial layer to trait generics (`UartRB` associated register types), and generic definitions calling read/write/modify fail to type-check without the marker bounds — 14 errors across `serial.rs`/`serial/uart_impls.rs` even though no UART register is constrained. Quantified adoption cost: ~10 mechanical one-line where-clause additions in one module. This is inherent to conditional method availability (no post-monomorphization errors in Rust); the honest paper claim splits the two numbers: monomorphic driver code = perfect precision, trait-generic driver code = small quantified patch. Second half of J (the fork + regenerate.sh + publishing) remains.
- 2026-07-15 (step E): stage-0 lint complete; published stats live in `docs/constraints_corpus_stats.md` (not `optimization/test_outputs/` — a citable, committed snapshot beats a git-ignored one). Key dispositions: within-register exact dedup drops 91 (2.0%); cross-INSTANCE duplication (589) is flagged, not dropped — per-instance rows are what codegen injects, so the plan's "−36% dedup" mass is deliberately retained; post-dedup 4,362 unique → 2,857 v2 state_gates (2,243 witnessed_runtime_check / 614 compile_gate) + 35.6% whole-constraint rejects, dominated by SVD-unresolvable names under the one-SVD-per-RM projection (~307 of those are single-device coverage misses, 28.5% reject rate with all SVDs; per-device projection is arguably correct — a constraint is enforceable only for registers the device has). New reject classes verified genuine by spot-check: RTC_WPR 0xCA53 vs 8-bit field (width), FLASH_SR.BSY writes (read-only target), USART_SR.TC (w1c postconditions), 8 self-defeating read gates. **`%s` root cause documented, NOT fixed** (stats doc §"%s root cause"): SVD `<dim>` templates — not derivedFrom as §5.1 guessed — flow through `agent_tools/svd_parsing.py:70-77` → `core/s1a_generator.py` worklist → filenames; the coverage comparator keys the SVD side by the SAME templates, so a worklist-only fix would desync the live coverage loop and is unverifiable offline — three-call-site fix proposal recorded for a live-run session. Step C note: the IR refactor's motivation (PR-15's 40% duplication) was discarded with PR 15; the fresh emitter is ~700 lines with a Plan/emit split — C reduced to "extract a naming module if step I bloats it."
- 2026-07-15 (step H): cross-register witnesses landed as inherent check methods taking the SOURCE register(s) as `&Reg<SRCrs>` parameters (`check_write_ready(&self, cr: &Reg<CRrs>)`), same-peripheral (`super::<reg>::`) and cross-peripheral (`super::super::<periph>::<reg>::`) resolved from the datasheet's `<PERIPHERAL>_<REGISTER>` prefix vs the target peripheral's instance-stripped base. Fixtures are verbatim generator corpus output: SPI_TXCRCR read-gate ⇐ SPI_SR.BSY (rm0008) and RCC_SSCGR ⇐ RCC_CR.PLLON (rm0368); cross-peripheral verified by a synthetic RTC_DR ⇐ PWR_CR.DBP compile probe (real corpus RTC constraints bundle the WPR key sequence, which is step I/sequence material). Read gating consequence handled: the peripheral RegisterBlock's `#[derive(Debug)]` is stripped when a read gate is present (debug-printing performs a read) — documented API divergence. Marker walk now keys (peripheral, spec, op) so same-named specs elsewhere keep their markers; injection accepts multiple constraint inputs in one shot. Compile-fail table grew to 11 rows (witness-less read of read-gated register; witness-less cross-register write).
- 2026-07-15 (step D): grammar v2 landed ALONGSIDE intact v1 in `defs.py` (v1 stays the generator wire format until step F; codegen consumes v1). Appendix-B gaps resolved during implementation: `FieldRef` gains an explicit `whole_register: bool` flag (B.1 referenced but never defined it; the corpus encodes IWDG_KR==0x5555 with `field_name: ""` — repaired to the flag at lift, ×25); observed-state postconditions drop ELEMENT-level with a structured reject while the precondition gate survives (whole-constraint rejection would discard the sound dominant part — consequence: all v1 postconditions default to hardware evidence and drop loudly until step-F re-extraction adds `evidence`); unparseable `required_state` anywhere rejects the WHOLE constraint (dropping a precondition would silently weaken a gate); `action_operation` on hardware evidence is dropped as a logged repair; enum-name repair ("enabled") happens at collection with `--svd-dir` (the lift itself has no SVD access; `agent_tools/svd_parsing.py` exposes counts, not names — collection carries its own minimal SVD index w/ derivedFrom + dim expansion); v1 models now `extra="allow"` so PR-15-style `evidence_kind` keys survive for the B.6 lift row; vacuous v1 constraints (729 in corpus) lift losslessly with a `vacuous_no_conditions` lint flag rather than rejecting. Corpus sweep: 4,453 v1 → 4,379 v2 state_gates, 3.0% whole-constraint rejects, zero crashes across all 30 RMs.
- 2026-07-15 (step B): two refinements over Appendix A while implementing. (1) Witness associated types live on NEW `WriteGate`/`ModifyGate`/`ReadGate` traits implemented ONLY by constrained registers — not on `Writable`/`Readable` as sketched — so the stock trait definitions and every existing register impl stay untouched; unconstrained registers need only the one-line `Unconstrained*` marker impls (appended at end-of-file, 445 files, mechanical). (2) No visibility widening at all: injected code lives inside `mod generic` and the peripheral modules, so private-field access is legal — the old `pub(crate)` patch class disappears. Also settled in code: a `write` constraint gates BOTH the write surface and the modify surface (a modify performs a write), each with its own witness; same-register read gates are rejected as self-defeating; `severity=warning` currently hard-gates like `error` (the `#[deprecated]` shadow is deferred, TODO in emitter). Enforcement is pinned by a nine-row compile-fail table incl. the PR-15 bypass (ascribed `&Reg` ref and UFCS → E0277).
- 2026-07-15 (step A): the plan's "stub mini-PAC fixture" is replaced by provisioning the **published crates.io package** (`stm32f4` 0.16.0, checksum-verified, cached, `get_pac.py`) — svd2rust PACs publish their generated source, so one 4 MB download yields a byte-authentic `generic.rs` + device modules; a hand-maintained stub could drift from real svd2rust output, and fidelity was the whole point of §2 defect 1. Consequence: the canonical test PAC lives at `vendored/pac/stm32f4/` (git-ignored), not in the `stm32-rs` submodule; `constraint_test/Cargo.toml` repointed. CI's enforcement-test step is `continue-on-error` until step B lands (the pre-B injector cannot handle the multi-file crates.io layout — expected, documented); step B removes that line.
- 2026-07-15: initial draft (from the PR-15 multi-agent review + STM corpus audit; session artifacts: nine agent reports + `curated_stm_constraint_examples.json` in the session scratchpad).

