# Register Constraints — Design & Rationale

The *why* behind the enforcement arm: the encoding semantics and witness-token
terminology (§3), the Constraint Validator's design (§7), and the architecture
decision record for the gating mechanism — why trait-bound gating, not shadowing
(Appendix A). For **how to use it** see [`PAC_CODEGEN.md`](PAC_CODEGEN.md); for
the **constraint grammar** see
[`REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`](REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md).
Section numbers are kept from the original plan so internal cross-references
(§3.1, §7.1) still resolve.

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
- **Upstreamable** — associated types in svd2rust's `generic_reg` template + per-register emission is the natural sidecar-file feature shape.

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



