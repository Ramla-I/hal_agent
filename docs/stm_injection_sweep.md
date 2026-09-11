# STM injection sweep — every manual with validated constraints, into its PAC

**What was asked:** map the SVDs to their Rust chip crates, fetch those crates,
inject the extracted access constraints, and compile real driver libraries
against the result to see what breaks.

**Run:** 2026-07-30, 13 reference manuals — every RM the phase-1d pipeline had
finished validating at the time (rm0383 and rm0385 were still in flight).
Driver: `applications/pac_codegen/experiments/stm_sweep.py`.
Reports: `applications/pac_codegen/experiments/out/` (gitignored).

---

## 1. The map

`applications/pac_codegen/rm_pac_mappings/stm.toml` is the manual → PAC → consumer
configuration. Re-verified against the live crates.io sparse index on the run
date (`experiments/build_map.py`); every field held. The 13 RMs land on **7
chip crates**, all at the 0.16.0 release (svd2rust 0.36.1 — the template the
injector targets), and each RM's device module exists in its crate:

| RM | constraints | judge-enforce | PAC crate | device module | consumer measurable on PAC 0.16 |
|---|---|---|---|---|---|
| rm0091 | 112 | 91 | stm32f0 | stm32f0x1 | — none |
| rm0367 | 104 | 79 | stm32l0 | stm32l0x3 | — none |
| rm0316 | 73 | 59 | stm32f3 | stm32f303 | **stm32-hal2 2.1.10** |
| rm0376 | 82 | 56 | stm32l0 | stm32l0x2 | — none |
| rm0360 | 80 | 41 | stm32f0 | stm32f0x0 | — none |
| rm0365 | 56 | 39 | stm32f3 | stm32f302 | **stm32-hal2 2.1.10** |
| rm0377 | 69 | 39 | stm32l0 | stm32l0x1 | — none |
| rm0008 | 62 | 33 | stm32f1 | stm32f103 | **stm32f1xx-hal 0.11.0** |
| rm0038 | 53 | 31 | stm32l1 | stm32l151 | — none |
| rm0366 | 36 | 31 | stm32f3 | stm32f301 | **stm32-hal2 2.1.10** |
| rm0033 | 51 | 30 | stm32f2 | stm32f215 | — none (no HAL at any version) |
| rm0313 | 62 | 26 | stm32f3 | stm32f373 | **stm32-hal2 2.1.10** |
| rm0368 | 54 | 26 | stm32f4 | stm32f401 | **stm32f4xx-hal 0.23.0 + stm32-hal2 2.1.10** |

An RM projects onto several chips; one device module is injected at a time
(`generic.rs` is patched crate-wide and injection is one-shot), and four RMs
share the stm32f3 crate, so every target snapshots and restores its tree.

### Which consumers can be measured — and why the rest cannot

Injection needs nothing from a consumer, but the *adoption* question does.

**The first pass of this analysis got the answer wrong by asking too narrow a
question.** `stm.toml` names one HAL per family — the community `*xx-hal` crate
— and only two of those (**stm32f1xx-hal 0.11.0**, **stm32f4xx-hal 0.23.0**)
have a release on PAC 0.16. But a PAC can have any number of downstream
consumers, and the question that matters is whether *anything* real depends on
the 0.16 generation. A reverse-dependency sweep of crates.io over every PAC in
`stm.toml` answers it properly:

| PAC | corpus manuals | consumers already on PAC 0.16 |
|---|---|---|
| stm32f1 | 1 | stm32f1xx-hal 0.11.0, stm32f1-hal 0.14.1 |
| stm32f3 | 4 | **stm32-hal2 2.1.10**, stm32-hrtim 0.2.0 |
| stm32f4 | 7 | stm32f4xx-hal 0.23.0, **stm32-hal2 2.1.10** |
| stm32c0 / g0 / g4 / h5 / h7 / l4 / l5 / wb | 6 (+ future) | **stm32-hal2 2.1.10** (g4 also stm32g4xx-hal 0.1.0) |
| stm32f0, stm32f2, stm32f7, stm32l0, stm32l1 | 11 | **— none, at any version —** |

**`stm32-hal2` is a second, independent HAL family** covering c0/f3/f4/g0/g4/
h5/h7/l4/l5/wb, already on PAC 0.16, and it compiles clean against every
pristine PAC we tested. It takes the measurable set from 2 manuals to **6 of
13** today (the whole f3 family joins, and rm0368 gains a second independent
consumer), and to **19 of the 30-manual corpus** as the pipeline completes.

### The 11 that stay unmeasurable, and why

For f0 / f2 / f7 / l0 / l1 there is **no crates.io consumer on PAC 0.16 at
all** — checked across every published version of every reverse dependency.
Three separate things stand in the way, each measured rather than assumed:

**(a) The community HALs are a port away, not a version bump.**
`experiments/hal_gap.py` forces each one onto the pristine PAC 0.16 (spoofing
only the local copy's version string so `[patch.crates-io]` applies; the source
compiled is the real 0.16.0) and counts:

| consumer | errors vs PAC 0.16 | dominant class |
|---|---|---|
| stm32f3xx-hal 0.10.0 | 846 | 652 × E0616 *field is private* |
| stm32l0xx-hal 0.10.0 | 703 | 595 × E0616 |
| stm32l1xx-hal 0.1.0 | 666 | 569 × E0616 |
| stm32f0xx-hal 0.18.0 | 446 | 408 × E0616 |
| *stm32f1xx-hal 0.11.0* (control) | *0* | — |
| *stm32f4xx-hal 0.23.0* (control) | *0* | — |

svd2rust made register-block fields private behind accessors and renamed every
generated enum (`CKMODE_A` → `CKMODE`) between the generation these HALs target
and 0.36.1. Hundreds of call sites each.

**(b) Most of them are dormant.** Last commit: stm32f3xx-hal 2023-11-30,
stm32l0xx-hal 2024-01-27, stm32l1xx-hal 2020-09-11. No open PR in any of the
four mentions 0.16. Only stm32f0xx-hal is active (2026-05-31), and its master
has moved 0.14 → 0.15 — still one generation short. "Wait for upstream" is a
real strategy for f0; for l0 and l1 it means waiting on dormant projects. For
f3 it is moot, since stm32-hal2 already covers it.

**(c) Going backwards is worse.** Injecting into the older PAC each HAL *does*
pair with was measured too (`experiments/old_pac_probe.py`):

| HAL crate | PAC it needs | svd2rust that generated it | injector anchors matched |
|---|---|---|---|
| stm32f3xx-hal | stm32f3 0.15.1 | 0.24.1 | 1 / 9 |
| stm32l0xx-hal | stm32l0 0.15.1 | 0.24.1 | 1 / 9 |
| stm32f0xx-hal | stm32f0 0.14.0 | 0.19.0 | 1 / 9 |
| stm32l1xx-hal | stm32l1 0.5.0 | — (package ships no `src/generic.rs`) | — |

Eight of nine `generic.rs` anchors the injector patches are absent from the
0.19–0.24 templates. Back-porting the injector is itself a port — which is the
evidence behind `stm.toml`'s standing policy. **stm32f2 has no HAL at all, on
any PAC version.**

> **Harness note.** An early version of `hal_gap.py` reported 0 errors for
> stm32f0xx-hal. It was measuring nothing: the spoofed version did not satisfy
> the HAL's requirement, so cargo *warned* and resolved the registry PAC
> instead — exit code 0, empty error list, indistinguishable from success.
> `patch_applied()` now reads the resolved `Cargo.lock` (a path dependency has
> no `source` key) and discards any run where the swap did not take. Both
> `hal_gap.py` and `stm_sweep.py` check it.

---

## 2. Injection: 13 / 13

Every RM injected, and for every one the injected chip crate still compiles
(`probe crate: PASS` — a downstream crate that merely depends on the device
module) and the tree restored byte-identical afterward.

| RM | device module | registers compile-gated | probe compiles | tree pristine after |
|---|---|---|---|---|
| rm0008 | stm32f103 | 6 | PASS | yes |
| rm0033 | stm32f215 | 6 | PASS | yes |
| rm0038 | stm32l151 | 12 | PASS | yes |
| rm0091 | stm32f0x1 | 18 | PASS | yes |
| rm0313 | stm32f373 | 9 | PASS | yes |
| rm0316 | stm32f303 | 19 | PASS | yes |
| rm0360 | stm32f0x0 | 9 | PASS | yes |
| rm0365 | stm32f302 | 11 | PASS | yes |
| rm0366 | stm32f301 | 12 | PASS | yes |
| rm0367 | stm32l0x3 | 26 | PASS | yes |
| rm0368 | stm32f401 | 5 | PASS | yes |
| rm0376 | stm32l0x2 | 18 | PASS | yes |
| rm0377 | stm32l0x1 | 19 | PASS | yes |
| | **total** | **184** | 13/13 | 13/13 |

### Peripheral instances share one register-block module

svd2rust emits ONE module per register block and gives each instance a type
alias over it, generated from the SVD's `derivedFrom`:

```rust
pub type I2C2 = crate::Periph<i2c1::RegisterBlock, 0x4000_5800>;
```

So `i2c2.rs` does not exist and never will — I2C2's TIMEOUTR *is*
`i2c1::timeoutr::TIMEOUTRrs`. The injector originally required
`<peripheral>.rs` to exist and discarded everything else as
`peripheral_not_in_device`, which was wrong for every non-first instance:

| | before | after |
|---|---|---|
| enforced state gates | 179 | **295** (+117 via alias, −1 to a conflict) |
| dropped as "peripheral not in device" | 200 | **20** (the genuinely absent) |
| registers gated | 170 | **184** |

The 20 that remain are real: Ethernet on an F103, CAN2 on a single-CAN part,
and one naming mismatch (`can1` where the crate calls the sole instance `CAN`).

**A constraint found for one instance necessarily gates them all**, because
they share the Rust type. That is forced by the encoding, and the corpus says
it is also correct: instances are `derivedFrom` the same block, and when
several instances do carry the same rule they quote the *same sentence* of the
manual — the manual states it once and our per-instance iteration replicates
it. Measured over the corpus: **92 register groups where instances agree
exactly, 32 where they disagree, 536 where only one instance carried anything.**

The 32 disagreements are extraction noise on an identical quote, not
per-instance rules. RM0008's USART_CR2 is typical — both instances quote
*"These 3 bits (CPOL, CPHA, LBCL) should not be written while the transmitter
is enabled"*, but one extracted the precondition as `CR1.TE cleared` (correct)
and the other as `CR1.UE cleared` (wrong).

**A disagreement drops the gate entirely** — the whole group, not "keep one".
Both alternatives are worse: unioning demands a precondition the datasheet does
not, turning correct code into a compile error; and picking one arbitrarily
gates every downstream user on a reading we have equal reason to think is the
wrong one. Being the module owner is a tie-break for *agreeing* plans, not
evidence that a reading is correct. A gate is a compile-time obligation, so
contradictory evidence should buy no gate at all; the drop is recorded as
`instance_conflict` with the disagreeing instances so it stays reviewable.

Agreeing plans still collapse to one — that is a single rule the manual states
once, and dropping it because two instances carry it would be perverse.

Corpus cost of the strict policy: **1 constraint and 1 register** (295 enforced
state gates instead of 296, 184 registers instead of 185). Only one conflict
survives that far — RM0360's `usart1/tdr` across five instances — because the
collection lint and the validator have already removed most disagreeing pairs.

### Where the other constraints went

1151 constraint outcomes across the 13 manuals. Nothing is dropped silently;
every row carries its fate and reason in the per-RM report.

| fate | n | what it means |
|---|---|---|
| `rejected_at_collection` | 316 | stage-0 lint: 237 name a register/field not resolvable in the SVD, 68 fail grammar-v2 validation, 11 carry a placeholder name |
| `gated_out_by_validator` | 220 | the closed-book judge: 215 `doc_only` (genuine but not witness-enforceable, or `encoding_error`), 5 `drop` (not a constraint) |
| `peripheral_not_in_device` | 195 | the manual covers a chip family; this peripheral is not on the chip injected |
| `planned` | 178 | reached the emitter |
| `kind_not_emitted` | 129 | no emitter yet: 84 `sequence`, 16 `delay`, 15 `write_once`, 8 `read_effect`, 5 `value_relation`, 1 `other` |
| `emitter_rejected` | 85 | 78 "no enforceable constraints" left after kind filtering, 7 a non-identifier field name |
| `pruned_for_device` | 22 | survived planning but not expressible against the generated PAC (access mode or field-reader shape) |
| `target_unverified_by_location` | 6 | `--chunks` quote check: self-referential quote anchored outside the target's section |

The single largest enforcement gap is `sequence` (84) — ordering constraints,
roadmap step I — followed by the lint's `unresolvable_in_svd` (237), which is
a generator-precision issue, not an enforcement one.

---

## 3. Real drivers compiled against the injected crates

Six manuals, three independent consumer crates, seven measured builds. Each
compiles the **unmodified** consumer from crates.io, swapped onto the local
injected PAC with one `[patch.crates-io]` line — exactly how a downstream user
would consume it. **Every baseline passes against the pristine PAC**, and every
run's patch is verified to have actually applied, so each result means
something.

| RM | device | consumer | baseline | true enforcement | generic friction | **other** |
|---|---|---|---|---|---|---|
| rm0008 | stm32f103 | stm32f1xx-hal 0.11.0 | PASS | 5 | 13 | **0** |
| rm0313 | stm32f373 | stm32-hal2 2.1.10 | PASS | 11 | 0 | **0** |
| rm0316 | stm32f303 | stm32-hal2 2.1.10 | PASS | **93** | 0 | **0** |
| rm0365 | stm32f302 | stm32-hal2 2.1.10 | PASS | 3 | 0 | **0** |
| rm0366 | stm32f301 | stm32-hal2 2.1.10 | PASS | 20 | 0 | **0** |
| rm0368 | stm32f401 | stm32f4xx-hal 0.23.0 | PASS | 7 | 8 | **0** |
| rm0368 | stm32f401 | stm32-hal2 2.1.10 | PASS | 5 | 0 | **0** |

**Zero other errors anywhere.** Across seven builds of three separate driver
libraries, every compile error the injection causes is one of our own datasheet
diagnostics — nothing else in any of them breaks.

### Generic friction is the driver's property, not the encoding's

The two stm32-hal2 columns settle a question the single-family result could
not. **rm0368 is a controlled comparison**: same chip, same manual, same five
gated registers, two different drivers.

| rm0368 / stm32f401 | true enforcement | generic friction |
|---|---|---|
| stm32f4xx-hal 0.23.0 | 7 | 8 |
| stm32-hal2 2.1.10 | 5 | **0** |

stm32-hal2 takes **zero friction on all five targets**. It is written as
concrete per-chip code; the `*xx-hal` crates abstract over "any UART-ish
register block" with traits. Friction is a cost that generic driver code pays,
not one the witness encoding imposes on adopters generally — a driver in the
common style pays nothing.

**True enforcement** — our diagnostic naming a register we actually gated, at a
concrete call site:

```
error[E0277]: `stm32f1::stm32f103::rtc::crh::CRHrs` is modify-constrained by its datasheet   @ src/rtc.rs
error[E0277]: `PRLHrs` is write-constrained by its datasheet                                 @ src/rtc.rs
error[E0277]: `stm32f4::stm32f401::i2c1::ccr::CCRrs` is write-constrained by its datasheet   @ src/i2c.rs
error[E0277]: `stm32f3::stm32f303::adc1::cfgr::CFGRrs` is modify-constrained by its datasheet @ src/adc.rs
error[E0277]: `stm32f3::stm32f373::flash::cr::CRrs` is modify-constrained by its datasheet   @ src/flash/non_trustzone.rs
```

Every gate lands in the driver module for its own peripheral, never anywhere
else: RM0008's RTC gates in the RTC driver, RM0368's I2C timing gates in the
I2C driver, RM0316's 93 hits spread across `adc.rs`, `i2c.rs`, `rtc.rs`,
`spi/baseline.rs` and `usart.rs` — the ADC sampling/sequence registers
(`SMPR2rs` 32, `SQR3rs` 20, `CFGRrs` 16) doing most of the work. Not one hit is
an associated-type projection; all name a concrete gated register.

**Generic friction** — the known, documented cost. Every one of these names an
*associated-type projection*, not a register:

```
error[E0277]: `<<ADC as Ptr>::RB as AdcRB>::CR2rs` is modify-constrained by its datasheet  @ src/adc.rs
error[E0277]: `<Self as UartRB>::SRrs` is read-constrained by its datasheet                @ src/serial/uart_impls.rs
```

Code written generically over "any UART-ish register block" must declare its
requirements in its signature, and "this register needs no witness" is now one
of them. These modules predate the markers, so they fail to type-check *even
though no register they touch is constrained* — `CR2rs` and `SRrs` are not in
either device's gated set. The fix is a handful of one-line bound additions in
those modules. The plain-code majority of both libraries needs nothing, and
stm32-hal2 needs nothing at all.

### Can friction be reduced? Three candidates, measured

`experiments/friction.py`.

**1. Inject fewer constraints — ruled out.** Install the encoding but gate
NOTHING (patch `generic.rs`, then give *every* register *every* marker, so the
PAC is semantically identical to pristine) and recompile: stm32f4xx-hal still
produces 14 friction errors and stm32f1xx-hal still produces 27 — the exact
counts the fully injected runs produced. Friction is a **fixed cost of
installing the encoding**, not a function of how much is gated. Adding the
101st constraint costs nothing more than the first.

**2. Patch the HAL — real, but not small.** Applying rustc's own
machine-applicable `consider further restricting …` suggestions and iterating:

| HAL | round 1 | round 2 | round 3 | edits |
|---|---|---|---|---|
| stm32f4xx-hal | 14 | 30 | 0 witness / 32 other | 42 |
| stm32f1xx-hal | 27 | 37 | 0 witness / 37 other | 57 |

The bounds **cascade to callers**: each generic method that gains
`where <Self as UartRB>::SRrs: UnconstrainedRead` forces every caller to
declare it too, so round 2 surfaces more errors than round 1. It reaches zero
witness errors, but at 42–57 edits spreading into public signatures — an
upstream API change, not a drive-by patch. (The residual "other" errors are
artifacts of applying suggestions verbatim — unimported trait names, two
`where` clauses that should be comma-joined — not new design problems.)

**3. Bound only the operations actually gated — free, and it roughly halves
friction.** `patch_generic_rs` used to add `where REG: Unconstrained*` to
read *and* write *and* modify unconditionally. But a bound on an operation no
register gates enforces nothing — every register carries that marker — while
still forcing every generic downstream signature to name it. Neither RM0008
nor RM0368 gates a single **read**, yet every one of stm32f4xx-hal's 14
friction errors was `read-constrained`.

`inject_into_pac` now derives the gated operations from the plans and bounds
only those. It cannot weaken enforcement (an operation with no gate has
nothing to enforce), and the drift checks still run over every signature:

| | true enforcement | friction before | friction after |
|---|---|---|---|
| rm0368 → stm32f4xx-hal | 7 (unchanged) | 14 | **8** |
| rm0008 → stm32f1xx-hal | 5 (unchanged) | 27 | **13** |

**4. Write the code concretely instead of generically — resolves it fully, but
it is not our change to make.** The same body, compiled twice against the same
injected PAC:

| written as | result |
|---|---|
| generic over an associated register type (`Self::SRrs`) | **fails** |
| against the concrete register type (`usart1::sr::SRrs`) | **compiles** |

So friction is a property of the *abstraction*, not of the register or the
encoding. Three independent confirmations: stm32-hal2 is concrete per-chip
code and takes zero friction on all five targets; within stm32f4xx-hal itself
the concrete modules absorb the gates cleanly (every one of its 17 enforcement
hits lands in `i2c.rs`/`rtc.rs`) while only the generic serial module produces
friction; and the probe above isolates the mechanism to a single line.

The catch is who can do it. Rust type-checks a generic function ONCE against
its declared bounds and never against its instantiations (unlike C++
templates), so there is no flag and no codegen trick on our side — the
expansion has to happen in the driver. For stm32f4xx-hal that means moving the
default methods of `RegisterBlockImpl: UartRB` into per-instance impls (or a
macro that generates them), which is an architectural change to somebody
else's crate, larger than the 42–57 bound additions of option 2 and asking
them to give up an abstraction they chose deliberately.

What remains is therefore irreducible *for us*: generic code that writes or
modifies registers, in a crate that really does gate writes and modifies.
Reaching zero needs an upstream change — either the bounds (small, but viral
through public signatures) or concrete expansion (large, but local and with no
API impact).

This is the same split `applications/pac_codegen/eval_hal/README.md` reports
for the stm32f4/I2C reference case, reproduced on real corpus constraints
across three driver libraries and three chip families.

---

## 4. Defect found and fixed by this run

The first whole-corpus attempt produced a chip crate that **did not compile**:

```
error[E0599]: no method named `bits` found for struct `BitReader<FI>`
   --> stm32f1/src/stm32f103/can.rs:488:32
        if !(r_fmr.finit().bits() == 0x1) {
```

RM0008's CAN filter gates are written `FINIT == 0x1`. svd2rust gives a 1-bit
field a `BitReader` (`bit_is_set`/`bit_is_clear`, no `bits()`) and a multi-bit
field a `FieldReader` (`bits()`, no `bit_is_*`) — the two share no accessor, so
the `equals` spelling was uncompilable on a 1-bit field. The failure lands
*inside the crate*, breaking every downstream consumer rather than just the
constrained call site.

`prune_plans_for_device` now reconciles each precondition with the generated
register file (the same ground truth it already used for the access mode):
`equals 0`/`equals 1` on a 1-bit field is **respelled** cleared/set — the
identical condition in the API that exists, so the constraint survives — and
anything the generated API genuinely cannot express drops the whole gate, never
just one conjunct. Resolution follows svd2rust's de-duplicating re-exports
(`pub use HSION_R as PLLON_R;`), without which good cross-register gates would
be dropped. Pinned by `tests/test_reader_shapes.py` (9 cases, no toolchain
needed). This is what `pruned_for_device` (22) counts.

---

## 5. Two things worth the pipeline owner's attention

**The rm0008 generator run changed underneath the committed artifact.**
`applications/pac_codegen/constraints/stm32f103.json` records 19 gated
registers (AFIO, BKP, I2C1, IWDG, RCC, RTC, SPI1, TIM1/2, USART1). Re-running
collection over the *same run directory path* today yields a different
constraint set — 9 registers before the validator gate (CAN, RTC, SPI1), 6
after. The run directory was regenerated since. Two separable causes:

- the flagship **I2C1_CR1 STOP/START/PEC gate is gone**: the register file now
  carries `access_constraints_v2: []`;
- constraints that used to be `state_gate` are now emitted as **`clock_gate`**
  (e.g. AFIO_EVCR's "enable the AFIO clock first"). That is arguably a *better*
  classification, but `clock_gate` has no emitter, so those constraints moved
  from enforced to not-enforced.

**The validator gate itself is mild.** For rm0008 it cuts 9 planned registers
to 6; the 19 → 6 drop is mostly the generator run changing, not the judge.

---

## Reproducing

```sh
python applications/pac_codegen/experiments/build_map.py        # map + live index check
python applications/pac_codegen/experiments/stm_sweep.py --dry-run
python applications/pac_codegen/experiments/stm_sweep.py        # inject + compile
python applications/pac_codegen/experiments/old_pac_probe.py    # older-template probe
python applications/pac_codegen/experiments/hal_gap.py          # how far each unpaired HAL is
```

`stm_sweep.py` reads the pipeline outputs from the sibling `hal_agent-phase-1d`
worktree (`DATA` at the top of the file) and provisions PACs via `get_pac.py`.
