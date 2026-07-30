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

`applications/pac_codegen/targets/stm.toml` is the manual → PAC → consumer
configuration. Re-verified against the live crates.io sparse index on the run
date (`experiments/build_map.py`); every field held. The 13 RMs land on **7
chip crates**, all at the 0.16.0 release (svd2rust 0.36.1 — the template the
injector targets), and each RM's device module exists in its crate:

| RM | constraints | judge-enforce | PAC crate | device module | HAL consumer | released pairing on PAC 0.16 |
|---|---|---|---|---|---|---|
| rm0091 | 112 | 91 | stm32f0 | stm32f0x1 | stm32f0xx-hal | none |
| rm0367 | 104 | 79 | stm32l0 | stm32l0x3 | stm32l0xx-hal | none |
| rm0316 | 73 | 59 | stm32f3 | stm32f303 | stm32f3xx-hal | none |
| rm0376 | 82 | 56 | stm32l0 | stm32l0x2 | stm32l0xx-hal | none |
| rm0360 | 80 | 41 | stm32f0 | stm32f0x0 | stm32f0xx-hal | none |
| rm0365 | 56 | 39 | stm32f3 | stm32f302 | stm32f3xx-hal | none |
| rm0377 | 69 | 39 | stm32l0 | stm32l0x1 | stm32l0xx-hal | none |
| rm0008 | 62 | 33 | stm32f1 | stm32f103 | stm32f1xx-hal | **0.11.0** |
| rm0038 | 53 | 31 | stm32l1 | stm32l151 | stm32l1xx-hal | none |
| rm0366 | 36 | 31 | stm32f3 | stm32f301 | stm32f3xx-hal | none |
| rm0033 | 51 | 30 | stm32f2 | stm32f215 | — (no HAL exists) | — |
| rm0313 | 62 | 26 | stm32f3 | stm32f373 | stm32f3xx-hal | none |
| rm0368 | 54 | 26 | stm32f4 | stm32f401 | stm32f4xx-hal | **0.23.0** |

An RM projects onto several chips; one device module is injected at a time
(`generic.rs` is patched crate-wide and injection is one-shot), and four RMs
share the stm32f3 crate, so every target snapshots and restores its tree.

### Why only two HAL crates can be measured

Injection needs nothing from a HAL, but the *adoption* question does. Only
**stm32f1xx-hal 0.11.0** and **stm32f4xx-hal 0.23.0** have a released version
that depends on PAC 0.16. Checked two ways on the run date:

- crates.io index: the newest release of stm32f3xx-hal / stm32l0xx-hal /
  stm32f0xx-hal / stm32l1xx-hal requires stm32f3 ^0.15.1, stm32l0 ^0.15.1,
  stm32f0 ^0.15, stm32l1 ^0.5.0 respectively;
- their **git master** branches (raw `Cargo.toml`): same requirements. Upstream
  has not moved.

Going the other way — injecting into the older PAC each HAL *does* pair with —
was measured, not assumed (`experiments/old_pac_probe.py`):

| HAL crate | PAC it needs | svd2rust that generated it | injector anchors matched |
|---|---|---|---|
| stm32f3xx-hal | stm32f3 0.15.1 | 0.24.1 | 1 / 9 |
| stm32l0xx-hal | stm32l0 0.15.1 | 0.24.1 | 1 / 9 |
| stm32f0xx-hal | stm32f0 0.14.0 | 0.19.0 | 1 / 9 |
| stm32l1xx-hal | stm32l1 0.5.0 | — (package ships no `src/generic.rs`) | — |

Eight of the nine `generic.rs` anchors the injector patches are absent from the
0.19–0.24 templates. Back-porting is a port, not a tweak — which is the
evidence behind `stm.toml`'s standing policy of waiting for the HAL dev
branches rather than back-porting. **stm32f2 has no maintained HAL at all.**

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
| | **total** | **170** | 13/13 | 13/13 |

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

The two measurable families. Each compiles the **unmodified** HAL from
crates.io, swapped onto the local injected PAC with one `[patch.crates-io]`
line — exactly how a downstream user would consume it. Both **baselines pass
against the pristine PAC**, so the injected result means something.

| | rm0008 → stm32f1xx-hal 0.11.0 | rm0368 → stm32f4xx-hal 0.23.0 |
|---|---|---|
| baseline (pristine PAC) | PASS | PASS |
| true enforcement | **5 errors** | **7 errors** |
| generic friction | 27 errors | 14 errors |
| **other (collateral damage)** | **0** | **0** |

**Zero other errors in both.** Every single compile error the injection causes
in ~30k lines of third-party driver code is one of our own datasheet
diagnostics — nothing else in either library breaks.

**True enforcement** — our diagnostic naming a register we actually gated, at a
concrete call site:

```
error[E0277]: `stm32f1::stm32f103::rtc::crh::CRHrs` is modify-constrained by its datasheet   @ src/rtc.rs
error[E0277]: `PRLHrs` is write-constrained by its datasheet                                 @ src/rtc.rs
error[E0277]: `stm32f4::stm32f401::i2c1::ccr::CCRrs` is write-constrained by its datasheet   @ src/i2c.rs
error[E0277]: `TRISErs` is write-constrained by its datasheet                                @ src/i2c.rs
```

RM0008's RTC gates land in the HAL's RTC driver; RM0368's I2C timing gates land
in its I2C driver. No gate hits a module unrelated to its peripheral.

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
those modules. The plain-code majority of both libraries needs nothing.

This is the same split `applications/pac_codegen/eval_hal/README.md` reports
for the stm32f4/I2C reference case, reproduced on real corpus constraints for
two chip families.

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
```

`stm_sweep.py` reads the pipeline outputs from the sibling `hal_agent-phase-1d`
worktree (`DATA` at the top of the file) and provisions PACs via `get_pac.py`.
