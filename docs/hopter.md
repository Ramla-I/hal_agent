# Hopter OS against a constraint-injected chip crate

**Question.** [Hopter](https://github.com/hopter-project/hopter) is a Rust
embedded OS for STM32. Does anything in it break — or turn out to be a bug —
once the chip crate underneath carries our datasheet gates?

**Answer.** Hopter drives one peripheral directly: TIM5. That timer's control
register **is** constrained — 64 constraints were extracted for it across the
corpus, and reading the manual by hand turns up three further rules we missed
that bear *directly* on the fields Hopter writes. **Hopter obeys every one of
them.** So a fully patched build would report no errors in Hopter's own code,
and that is the correct result rather than an empty one.

Reproduce with `applications/pac_codegen/experiments/hopter.py`; the report
lands in `experiments/out/hopter.json`.

---

## 1. What Hopter is, and what it took to build it

**Its kernel links no chip crate.** The only hardware dependency is
`cortex-m`. The `stm32f4`/`stm32f0` names in `src/` are a vector table
*copied* from the stm32f4 crate plus interrupt names in doc comments. Our
injection can only reach Hopter through the HAL its examples use — 9 of 52
examples.

**It needs a forked compiler.** `rust-toolchain` pins `segstk-rust`, a Rust
fork with segmented-stack support. On a stock nightly the build dies with
**28 × E0787** (`asm!` in naked functions) inside Hopter's own allocator and
unwinder, before any chip crate is involved. The fork ships as a prebuilt
GitHub release (158 MB), linked with `rustup toolchain link`.

**Its dependency graph has drifted past its own compiler.** The fork is Rust
1.81 (April 2025); crates published since use edition 2024, which its cargo
cannot parse. Two pins fix it — `cortex-m-rt =0.7.3` and `time` walked back to
0.3.41. **With those, Hopter builds.**

**Its HAL pin does not pair with our crate.** The examples use stm32f4xx-hal
**0.21**, which needs stm32f4 `^0.15.1`; the injector targets 0.16.0, and only
stm32f4xx-hal **0.23** pairs with it. Bumping is not one line either: 0.23
moved `Config` into `serial`, and `GPIOA.split()` / `USART1.serial()` now take
`&mut rcc`.

**A per-chip trap:** the examples' clock setup only has `#[cfg]` arms for
`stm32f401` and `stm32f407`. Building with `stm32f405` — Hopter's own `qemu`
default — fails with *"cannot find value `clocks`"*, which looks like our
breakage and is not.

---

## 2. Everything Hopter touches

Across **all 52 examples**, only four peripheral handles are ever taken from
the PAC, and only one is driven directly:

| handle | uses | how |
|---|---|---|
| `dp.RCC` | 9 | `.constrain()` → the HAL's clock builder |
| `dp.TIM2` | 7 | `.counter(&clocks)` → the HAL's `CounterUs` |
| `dp.GPIOA` | 1 | `.split()` → the HAL's pin types |
| `dp.TIM5` | 1 | **direct register access — the only one** |

Every register write in every example except
`debug/cpu_load/load_40_percent.rs` happens inside stm32f4xx-hal. That file is
the exception because it needs a free-running microsecond timestamp, which the
HAL's `CounterUs` abstraction does not provide, so it programs TIM5 itself:

| register | fields written |
|---|---|
| `TIM5.CR1` | `CEN` ×4, `URS` ×4 |
| `TIM5.PSC` | `PSC` ×3 |
| `TIM5.EGR` | `UG` ×2 |
| `TIM5.DIER` | `UIE` |
| `TIM5.SR` | `UIF` |
| `TIM5.ARR` | whole-register write |
| `TIM5.CNT` | `reset()` ×2, `read()` ×3 |

### The HAL-mediated path is clean too

Hopter's calls reach four HAL modules — `rcc.rs`, `timer.rs`, `gpio.rs`,
`serial.rs`. The 31 constraint violations we found in stm32f4xx-hal are in
`rtc.rs` (13), `spi.rs` (10), `i2c.rs` (4) and `flash.rs` (4). **Zero
overlap** — Hopter uses no SPI, no RTC, no I2C, and never programs flash.

---

## 3. Those registers *are* constrained

`TIM5.CR1` is not an unconstrained register. Across the 28 manuals, **64
constraints were extracted for it**, every one of them a `state_gate`:

| restricted field | constraints |
|---|---|
| `CMS` | 59 |
| `DIR` | 3 |
| `CMS[1:0]` | 2 |

All express one datasheet sentence — *"It is not allowed to switch from
edge-aligned mode to center-aligned mode as long as the counter is enabled
(CEN=1)"* — a rule about changing the counter's **alignment mode**. Hopter
writes `CEN` and `URS`, so this rule does not reach it.

### Three more rules, which we missed, and which DO reach it

The conclusion is only as good as the corpus's recall, so RM0383's timer
chapter was read directly (67 candidate constraint sentences after de-wrapping
the chunk text). Three rules bear on exactly what Hopter writes, and the
extractor produced **none** of them — their quotes appear in zero register
files:

| page | rule | shape it should have had |
|---|---|---|
| p267 | *"As the preload registers are transferred to the shadow registers only when an update event occurs, before starting the counter, the user must initialize all the registers by setting the UG bit in the TIMx_EGR register."* | `sequence`: EGR.UG **before** CR1.CEN |
| p270 | *"…generate an update by software (setting the UG bit) just before starting the counter and **not to write the counter while it is running**."* | `state_gate`: write CNT requires CEN cleared |
| p258 | *"If the slave mode controller is disabled (SMS=000), then the CEN, DIR and UG bits are actual control bits and can be changed only by software."* | `state_gate`: CEN/UG writes meaningful only while SMS=000 |

That is a real recall gap, on the one peripheral this OS programs. Two of the
three are `sequence`-shaped — the corpus's largest unenforceable kind — so
even once extracted they would land in `kind_not_emitted` today.

---

## 4. Hopter obeys all of them

Its `init_tim5`, with the rules marked:

```rust
tim5.psc.write(|w| w.psc().bits(49));
tim5.cr1.modify(|_, w| w.cen().clear_bit());   // stop the counter FIRST
tim5.cnt.reset();                              //   then write CNT      -> p270 ok
tim5.sr.write(...);                            // clear flags
tim5.arr.write(|w| w.bits(65535));
tim5.dier.modify(|_, w| w.uie().set_bit());
tim5.cr1.modify(|_, w| w.urs().set_bit());     // update from overflow only
tim5.egr.write(|w| w.ug().set_bit());          // UG BEFORE start       -> p267 ok
tim5.cr1.modify(|_, w| w.urs().clear_bit());
tim5.cr1.modify(|_, w| w.cen().set_bit());     // start last
```

- **p267** — `UG` is set before `CEN`. ✔
- **p270** — the only `CNT` *writes* are `cnt.reset()`, both immediately after
  `cen().clear_bit()`; every access while the counter runs is a `read()`. ✔
- **p258** — `SMCR` is never touched anywhere in Hopter, so `SMS` stays `000`
  from reset. ✔
- **the 59 CMS gates** — Hopter never writes `CMS` or `DIR`. Even with
  `--field-level-gating` enabled, those gates patch the `w.cms()` writer
  accessor, which Hopter does not call. ✔

The `URS` set/clear bracketing the `UG` write is the standard idiom for
raising a software update event without firing a spurious interrupt. This is
carefully written code, and the datasheet rules it has to obey, it obeys.

---

## 5. Conclusion

**Hopter uses constrained registers, and uses them correctly.** A build with
the HAL patched and the crate injected would report **zero errors in Hopter's
own code** — a true negative, surviving a recall check aimed squarely at it.

Two things make that worth stating rather than shrugging at:

**It was not free.** The earlier, whole-register extraction of the same CMS
sentence would have gated all of `CR1` and flagged all eight `CEN`/`URS`
writes — a false positive against a correct program. Grammar-v2's
`target_fields` is what converts this into a true negative. The pipeline's
precision is doing real work here.

**The findings are one layer down, and that is honest.** The 31 violations in
stm32f4xx-hal are in `rtc.rs`, `spi.rs`, `i2c.rs` and `flash.rs`, because the
driver is what actually programs the delicate peripherals.

---

## 6. What a Hopter-level finding would need

Not a better pipeline — a wider target. Hopter is a kernel: its examples use
one timer as a heartbeat and one UART for output, a surface of seven registers
on one peripheral. Enforceable constraints cluster where configuration is
delicate — I2C timing, SPI mode changes, RTC write protection, flash
programming — which a scheduler test never touches.

A convincing application-level demonstration needs software that *configures
peripherals*: an I2C sensor driver, an SPI display, an RTC-backed clock — or,
best of all, an OS that talks to the PAC **directly**, with no HAL to absorb
the errors. Oxide's [Hubris](https://github.com/oxidecomputer/hubris) depends
on `stm32f3`/`stm32f4`/`stm32g0`/`stm32h7` with no HAL layer at all, and has to
configure I2C, SPI and flash itself; three of those families are in our corpus.

---

## Appendix: where the developer sees the error

Worth recording separately, because it shaped the whole investigation. Cargo
builds dependencies first, so when a HAL fails to compile the application on
top of it is **never type-checked**:

```
error: could not compile `stm32f4xx-hal` (lib) due to 25 previous errors
```

Measured on a UART-only probe against an injected stm32f401: **0 error
locations in the application's own file**, and the first error pointing into
`~/.cargo/registry/.../stm32f4xx-hal-0.23.0/src/i2c.rs` — about **I2C
timing**, in a program that only opens a UART.

An application talking to the chip crate **directly** gets the intended
experience — `--> src/lib.rs:5`, naming the rule at the line that breaks it.
Two regimes:

| | what the developer sees |
|---|---|
| the HAL itself touches a gated register | build fails inside the HAL; **no line of theirs is implicated** |
| the HAL does not, but the application does | error at their own line, naming the datasheet rule |

This is the practical argument for landing the friction fix upstream — see
[`generic_friction.md`](generic_friction.md), where the fix turns out to be
four one-line changes, not the API revision first estimated.

## Reproducing

```sh
python applications/pac_codegen/experiments/hopter.py            # facts + surface probe
python applications/pac_codegen/experiments/patch_hal.py \       # the HAL adoption step
    --rm rm0383 --device stm32f411 --svd stm32f411.svd
```

Hopter's own build needs the `segstk-rust` toolchain
([prebuilt releases](https://github.com/hopter-project/hopter-compiler-toolchain/releases))
plus the two dependency pins in §1.
