# Draft: Compile-Time Enforcement of Register Access Constraints

> Paper-section draft (Ramla to adapt/condense). Four subsections thread one
> running example end to end, plus a fifth on field-level gating (its own SPI
> example). Kept in sync with `paper_enforcement_section_draft.tex`. All numbers are
> reproducible: grammar/corpus figures from `docs/constraints_corpus_stats.md`
> and `docs/quote_anchoring_stats.md`; enforcement and HAL figures pinned by
> the test suite (`applications/pac_codegen/test_codegen.py`,
> `test_hal_demo`). Terminology follows the settled scheme: the LLM
> *validates*, generated Rust *checks* at runtime, the compiler *enforces*.

## The running example

STMicroelectronics' reference manuals for the STM32 family state, in the
description of the I2C peripheral's first control register:

> *"When the STOP, START or PEC bit is set, the software must not perform any
> write access to I2C_CR1 before this bit is cleared by hardware. This is to
> avoid setting a second STOP, START or PEC request."*

This is an *access-ordering constraint*: a rule about **when** a register may
be touched, not about **what** the register contains. SVD files — the
machine-readable register descriptions that PAC crates are generated from —
have no vocabulary for such rules, so today they live only in prose and in
driver authors' heads. Our extraction pipeline recovers this sentence and its
meaning from the manual; the four subsections below follow it from structured
form to a compile error in an unmodified, widely-used driver library.

## 1. The register access constraint grammar

The grammar is the contract between the extraction LLM and everything
downstream: a small, closed target language that is easy for a model to emit,
mechanically validatable without any AI in the loop, and compilable into
enforcement. Three design rules shape it.

**Closed vocabularies, structured values.** Every enumerable field is a fixed
choice set (operation ∈ {read, write, modify, any}; severity ∈ {error,
warning}), and numeric values are lists of integers validated against the
SVD's field widths — never free text. An earlier iteration allowed strings
like `equals:0b01|0b10|0b11`; free text of this kind both invites drift and,
when spliced into generated code, silently changes meaning under the host
language's operator precedence. In the current grammar such a value is the
list `[1, 2, 3]`.

**A quote anchor.** Every constraint carries the verbatim sentence it was
extracted from (`datasheet_text`). Because the quote travels with the
constraint, its authenticity is checkable by plain string search against the
manual — no retrieval, no judgment — and the surrounding paragraph can be
recovered as trusted context for later validation.

**Who establishes the state.** Each condition's `established_by` key declares exactly that:
`hardware` (software may only observe it — the running example, where
hardware clears STOP) or `software` (the driver itself must establish it,
e.g. "this register may be written only while the peripheral is disabled").
The distinction cannot be inferred from the SVD; it exists only in prose, so
it must be captured at extraction time. As §2 shows, it decides the *shape*
of the generated enforcement.

Constraints are a tagged union of eight kinds — state gates (the workhorse),
multi-step sequences (unlock keys), write-once locks, delays, read
side-effects, peripheral clock gates, value relations, and an explicit
`other` escape valve so a real requirement that fits no kind is preserved
verbatim rather than force-fitted or dropped. Enforceability is *computed*
from the kind and `established_by`, never emitted by the model.

The running example in grammar form:

```json
{ "kind": "state_gate",
  "target_register": "CR1", "target_operation": "write",
  "preconditions": [
    {"register": "I2C_CR1", "field": "STOP",  "state": "cleared", "established_by": "hardware"},
    {"register": "I2C_CR1", "field": "START", "state": "cleared", "established_by": "hardware"},
    {"register": "I2C_CR1", "field": "PEC",   "state": "cleared", "established_by": "hardware"}],
  "postconditions": [],
  "severity": "error",
  "datasheet_text": "When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware. ..." }
```

**Results.** Applied to 30 STM reference manuals, the pipeline extracted
4,927 raw constraints (4,362 after removing exact duplicates). Deterministic
validation — vocabulary, SVD name and width resolution, duplicate and
flag-semantics filters — accepts **2,857 enforceable state gates** and
rejects the remainder with machine-readable reasons (35.6% under a
one-device-per-manual projection; 28.5% when resolving against all of a
manual's devices — the dominant reject is a constraint naming a peripheral
the projected device does not have). Independently, **91.1% of all extracted
constraints carry a quote genuinely present in the manual** (78.2% verbatim,
12.9% near-verbatim); the unanchored 8.9% are stitched or paraphrased quotes
and are routed to human review.

## 2. Translating constraints to witness tokens

How strong a guarantee the type system can give depends on who establishes
the condition, which the grammar's `established_by` field records. The easy
case is *software*: when the driver itself must bring the condition about — it
must disable the USART (`UE=0`) before writing the baud-rate register — the
compiler enforces the requirement outright. The generated `disable()` returns
a witness token that the write consumes, so code that writes the baud rate
without first disabling the USART does not compile; and because software alone
controls `UE`, that witness is a *standing* guarantee rather than a snapshot.
The harder case, and our running example, is *hardware*: the compiler cannot
observe hardware, so it cannot enforce "STOP is clear" directly. What it *can*
enforce is an ordering — **the datasheet-prescribed check must happen before
the constrained operation** — so that holding the witness attests the check
was performed on a fresh read. Both cases use the same device, *witness
tokens*: zero-sized values creatable only by performing the prescribed action
or check, and consumed by the constrained operation. We develop the harder
case in full; the generator emits, into the PAC's I2C module:

```rust
/// State witness authorizing one write of CR1.
pub struct Cr1WriteWitness { _priv: () }        // cannot be forged: private field

impl Reg<CR1rs> {
    /// Read CR1 once and check every write precondition.
    pub fn check_write_ready(&self) -> Result<Cr1WriteWitness, Cr1ConstraintError> {
        let r = self.read();                     // ONE fresh hardware read
        if !r.stop().bit_is_clear()  { return Err(StopNotCleared); }
        if !r.start().bit_is_clear() { return Err(StartNotCleared); }
        if !r.pec().bit_is_clear()   { return Err(PecNotCleared); }
        Ok(Cr1WriteWitness { _priv: () })
    }
    /// Check and write in one call — the witness never escapes user code.
    pub fn write_when_ready<F>(&self, f: F) -> Result<u16, Cr1ConstraintError> { ... }
}
```

Four properties carry the guarantees. The witness is **unforgeable** (its
only constructor is the check). It is **affine** — consumed by the write, so
one check authorizes one operation; reusing it is a compile error. It is
**operation-specific**: a write witness does not authorize a read-modify-write,
which has its own witness type. And the recommended entry point
(`write_when_ready`) mints and spends the witness inside one call, so the
check-to-use window is fixed by the library, not by caller discipline.

Honesty about semantics: a witness is a *witness*, not a proof — it attests
that the preconditions were observed true in one fresh read. Time-of-check to
time-of-use is inherited from the hardware contract itself: memory-mapped I/O
has no atomic check-and-act, so the manual's own prescribed procedure carries
the identical window, and for hardware-cleared flags like STOP the race is
benign in the safe direction (hardware only clears it). In the terms of the
opening, this is the *hardware* case, and its fresh check mints what we call a
*state witness*; the *software* case mints an *action witness* — the setup
action itself, with no runtime check. Naming aside, `established_by` selects
only *how* the witness is minted, not *whether* enforcement is compile-time:
in both cases the gated operation will not type-check without the witness, and
in both the condition is established at runtime. The sole difference is the
presence of a fallible runtime check.

**Results.** Of the 2,857 accepted gates, 2,243 translate to compile-gated
state witnesses (each minted by one runtime check) and 614 remain
documentation-only (they carry no checkable condition in the legacy corpus
encoding); action witnesses appear once re-extraction emits the
`established_by` field, making that split a direct measure of the
re-extraction step's value.

## 3. Applying the changes to PAC crates

**How a PAC crate works today.** A peripheral access crate is machine-generated
(by the community tool svd2rust) from the vendor's SVD file, one crate per
family with a build feature per device. Its safety model rests on two ideas.
First, *ownership*: the crate exposes each peripheral as a singleton object
(`Peripherals::take()` yields it exactly once), so two parts of a program
cannot race on the same hardware by accident. Second, *typed registers*: every
register is a value of type `Reg<REG>`, where `REG` is a zero-sized marker
type identifying that specific register, and a small set of **capability
traits** on the marker declares what the hardware allows — `RegisterSpec`
(its raw width), `Readable`, `Writable`, and `Resettable` (its documented
reset value). The register methods are defined once, generically, but each is
available only where the matching capability holds: `read()` returns a reader
with typed per-field accessors (`r.stop().bit_is_clear()`); `write(|w| …)`
composes a full register value starting from the reset value through field
proxies (`w.pe().enabled()`) that make invalid bit patterns unrepresentable —
or `unsafe` where the SVD cannot vouch for them; `modify(|r, w| …)` performs
a read-modify-write; `reset()` restores the documented reset value; and
`write_with_zero` (already `unsafe`) starts from all-zeroes instead. A
read-only register simply *has no* `write` method — its marker never
implements `Writable`, and the compiler rejects the call. This is the load-
bearing observation for what follows: **conditional method availability is
already the PAC's own safety mechanism**; our change extends the same ladder
by one rung.

A PAC generated by svd2rust defines every register method once, generically:
`write` exists for any register type implementing the `Writable` trait. One
cannot delete a method from a single register — but one can make a method's
*availability conditional*, which is an idiomatic Rust pattern (a slice's
`sort` exists only for orderable elements; indeed svd2rust itself already
rejects writes to read-only registers by exactly this mechanism).

The generator therefore patches the crate in three small, mechanical ways:

1. **The shared core** (`generic.rs`, one file): the stock `write`, `modify`,
   `read`, `reset`, … methods gain a requirement — the register must carry an
   "unconstrained" marker for that operation. Alongside them appear the
   witnessed variants (`write_witnessed`, `write_when_ready`) and a single,
   deliberately `unsafe`, greppable escape hatch (`write_unwitnessed`).
2. **Every unconstrained register** — the overwhelming majority — receives
   one-line marker implementations. Its public API is unchanged.
3. **Each constrained register** receives *no* marker for the gated
   operation — the absence *is* the gate — plus the generated module of §2.

Because the missing-marker error is a standard trait-bound failure, Rust's
diagnostic attribute turns it into a domain-specific message at the offending
line:

```
error[E0277]: `...i2c1::cr1::CR1rs` is write-constrained by its datasheet
  --> src/i2c.rs:149
   = this register requires a witness: call `write_witnessed(f, witness)` or
     `write_when_ready(f)`; obtain the witness via `check_write_ready()`;
     bypass only with `unsafe write_unwitnessed`
```

There is no wrapper type and no method shadowing — an earlier wrapper-based
design left the stock method reachable through an ordinary reference
coercion, a silent, safe bypass; under trait gating the method *does not
exist* for the constrained register, so that bypass is itself a compile
error, permanently pinned in our test suite. The patched crate is consumed
exactly like the original: it is the published, generated source plus these
additions, so a downstream project adopts it with a one-line dependency swap
and no build steps.

**Results.** For the running example's device, the patch touches the one
shared core file, adds one-line markers to 445 register files, and injects
one constraints module; the patched crate type-checks in ~14 s. Enforcement
is pinned by an eleven-program compile-fail suite: every witness-less access
fails with the message above, witness reuse and cross-operation reuse fail
with the expected ownership and type errors, and the legal witnessed paths
compile.

## 4. Effect on higher-level crates

The adoption question is whether real driver code — written by others, before
these constraints existed — can use the modified PAC *as is*. We answer it
experimentally: compile the unmodified stm32f4xx-hal (the community's
standard hardware-abstraction layer for these chips, ~30k lines) against the
patched PAC, consumed exactly as a downstream user would consume it.

**Results.** Against the *unpatched* baseline crate the HAL compiles clean —
adoption costs nothing where nothing is constrained. Against the patched
crate there are exactly two classes of outcome and nothing else:

| class | count | where | meaning |
| --- | --- | --- | --- |
| true enforcement | **14 / 14** | the HAL's I2C driver (`i2c.rs`, `i2c/dma.rs`) | every site that writes CR1 fails with the datasheet diagnostic; **zero false hits** elsewhere |
| generic-code friction | 14 | one module (`serial/`) | trait-generic code must re-state its requirements; ~10 one-line bounds fix the module |

The first class is the running example completing its journey: the sentence
from the manual is now a compile error at the fourteen real call sites that
could violate it. Fixing such a site is a local, guided edit — the diagnostic
names the replacement:

```rust
// before (no longer compiles):
self.i2c.cr1().modify(|_, w| w.stop().set_bit());
// after (checked):
self.i2c.cr1().modify_when_ready(|_, w| w.stop().set_bit())?;
```

The second class delimits "as is" honestly. Code that names concrete
registers — the vast majority of a HAL — needs no change unless it genuinely
violates a constraint. Code that is *generic over register types* must
declare the new markers in its trait bounds, because generic code promises
its requirements up front; this HAL's serial layer is written that way and
fails to type-check even though no serial register is constrained. The cost
is small and mechanical (about ten one-line bounds in one module), but it is
a modification, and any design that makes methods conditionally available
shares it — the alternative, keeping every method callable, is precisely the
silent bypass we rejected. We therefore report adoption as two measured
numbers rather than one claim: perfect precision on concrete driver code,
and a small, quantified patch for trait-generic driver code.

## 5. Field-level gating

The running example gates a whole register: any write to `I2C_CR1` is
constrained. But many datasheet rules name only *specific fields*. A
constraint records this in its `target_fields` list — empty for a
whole-register rule, otherwise the fields the rule scopes to. For the SPI
control register, for instance, the CRC-enable bit may be changed only while
the peripheral is disabled, and nothing is said about the register's other
bits:

```json
{ "kind": "state_gate",
  "target_register": "SPI_CR1",
  "target_fields": ["CRCEN"],
  "target_operation": "write",
  "preconditions": [
    {"register": "SPI_CR1", "field": "SPE", "state": "cleared"}],
  "datasheet_text":
    "CRCEN is written only when the SPI is disabled (SPE = 0)." }
```

Gating the whole `CR1` register here would be sound but *over-restrictive*: it
would demand "`SPE` cleared" before writing *any* field of `CR1`, including the
many the datasheet never mentions. That is not merely inconvenient — forcing a
program to disable the SPI in order to touch an unrelated bit can be wrong. And
it is not a corner case: **46% of the extracted constraints name specific
fields rather than the whole register**, so treating them all at register
granularity would over-constrain nearly half the corpus.

The finer gate is possible because the PAC already exposes a per-field writer
accessor — the `w.crcen()` one calls inside a `write`/`modify` closure. We
attach the witness requirement to *that accessor* rather than to the
register's `write`/`modify` methods, so the register's own methods stay
unconstrained and sibling fields are untouched. Two changes realize it. First,
the generated constraints module gains a per-field witness and its check,
exactly as before but scoped to the field:

```rust
pub struct Cr1CrcenFieldWitness { _priv: () }

impl Reg<CR1rs> {
    /// CRCEN is written only when the SPI is disabled (SPE = 0).
    pub fn check_crcen_field_ready(&self)
        -> Result<Cr1CrcenFieldWitness, Cr1ConstraintError>
    {
        let r = self.read();                 // one fresh read
        if !r.spe().bit_is_clear() { return Err(SpeNotCleared); }
        Ok(Cr1CrcenFieldWitness { _priv: () })
    }
}
```

Second, the field's writer accessor in the register module is given the
witness as a parameter — the one place the whole-register gate never touches:

```rust
// svd2rust original:
pub fn crcen(&mut self) -> CRCEN_W<CR1rs> { CRCEN_W::new(self, 13) }
// patched:
pub fn crcen(&mut self, _witness: &constraints::Cr1CrcenFieldWitness)
    -> CRCEN_W<CR1rs> { CRCEN_W::new(self, 13) }
```

*The field's writer accessor, before and after the patch. `CR1rs` is
svd2rust's zero-sized register-spec marker type for the `CR1` register — the
register handle is `Reg<CR1rs>`, and the `rs` suffix is the tool's naming
convention. It is distinct from our generated witness type
`Cr1CrcenFieldWitness`, whose `Cr1` is a capitalized register name we chose.*

The effect is field-precise. A write to a sibling field compiles unchanged;
the gated field compiles only with a witness; the gated field without one does
not compile:

```rust
spi.cr1().modify(|_, w| w.mstr().set_bit());          // sibling: OK
let wit = spi.cr1().check_crcen_field_ready()?;
spi.cr1().modify(|_, w| w.crcen(&wit).enabled());     // witnessed: OK
spi.cr1().modify(|_, w| w.crcen().enabled());         // error[E0061]
```

Two properties distinguish this from the whole-register gate. The failure is
an arity error (`E0061`, "this method takes one argument") rather than the
tailored trait-bound message, because the gate now rides on the accessor's
signature; a trait-bound variant could recover the custom text at the cost of
more generated code. And because the patch edits each constrained register's
own field accessor — rather than the single shared core file the
whole-register gate touches — it is more invasive, so it is *opt-in*: enabled
per run, and absent it the emitter falls back to whole-register gating,
leaving field-scoped constraints unenforced rather than over-enforced. The
witnessed path and both compile outcomes above are pinned by a compile test
against the generated PAC.
