# Hopter OS against a constraint-injected chip crate

**Question:** does anything in [Hopter](https://github.com/hopter-project/hopter)
— a Rust embedded OS for STM32 — stop compiling once the chip crate underneath
carries our datasheet gates?

**Answer:** nothing in Hopter's own code. Every error comes from the driver
library it sits on, and we had already measured those.

Reproduce with `python applications/pac_codegen/experiments/hopter.py`; the
report lands in `experiments/out/hopter.json`.

---

## Three facts that shape the experiment

**1. Hopter's kernel does not link a chip crate at all.** Its only hardware
dependency is `cortex-m`. The `stm32f4`/`stm32f0` names in `src/` are a vector
table *copied* from the stm32f4 crate plus interrupt names in doc comments —
the `[dependencies]` table contains no PAC. Our injection therefore cannot
reach Hopter's kernel by construction; it can only reach Hopter through the
HAL its examples use (9 of 52 examples).

**2. Hopter needs a forked compiler.** `rust-toolchain` pins `segstk-rust`, a
Rust fork with segmented-stack support. On a stock nightly the build dies with
**28 × E0787** (`asm!` in naked functions) inside Hopter's own allocator and
unwinder — entirely in its kernel, long before any chip crate is involved. We
do not have that fork, so a full Hopter build is out of reach here.

**3. Its HAL pin does not pair with our chip crate anyway.** The examples use
stm32f4xx-hal **0.21**, which requires stm32f4 `^0.15.1`. The injector targets
0.16.0, and only stm32f4xx-hal **0.23** pairs with it (0.22 wants `^0.16.1`,
and no stm32f4 0.16.1 exists). Bumping is not a one-line change either — 0.23
moved `Config` into `serial`, and `GPIOA.split()` / `USART1.serial()` now take
`&mut rcc`, so Hopter's example code needs updating for reasons that have
nothing to do with us.

---

## What was measured instead

A **surface probe**: Hopter's exact call sequence from `examples/uart_echo.rs`
— steal the peripherals, constrain RCC, split GPIOA, put PA9/PA10 into
alternate function 7, open USART1 at 115200, then blocking `read()`/`write()`
— expressed in the 0.23 API and compiled against the pristine and the injected
chip crate. Same driver paths, paired HAL version, no forked compiler needed.
It is a proxy for Hopter, and reported as one.

Target: RM0368 → stm32f401, a chip Hopter lists as a supported board.

| | result |
|---|---|
| baseline, pristine chip crate | **compiles** |
| injected chip crate | 17 true enforcement, 8 generic friction, **0 other** |
| **errors in Hopter's own call sequence** | **0** |

Every single error is attributed to a file inside stm32f4xx-hal —
`src/i2c.rs`, `src/rtc.rs`, `src/spi.rs` for the enforcement hits,
`src/serial.rs` and `src/serial/uart_impls.rs` for the friction. The counts
match RM0368's HAL row in the [tracking table](injection_tracking.md) exactly,
because they *are* that measurement: compiling the probe compiles the HAL.

---

## Where the developer actually sees the error

The counts above hide something the numbers alone do not tell you, and it
matters more for adoption than the totals: **the application is never
compiled at all.**

Cargo builds dependencies first. `stm32f4xx-hal` fails, so the build stops:

```
   Checking enumflags2 v0.7.12
error: could not compile `stm32f4xx-hal` (lib) due to 25 previous errors
```

`hopter`, and the example on top of it, are never type-checked. Measured on
the probe: **0 error locations in the application's own file**, and the first
(and every) error points into someone else's crate:

```
error[E0277]: `TRISErs` is write-constrained by its datasheet
   --> ~/.cargo/registry/src/…/stm32f4xx-hal-0.23.0/src/i2c.rs:167:26
    |
167 |         self.i2c.trise().write(|w| w.trise().set(trise as u8));
```

Note what that register is: **I2C timing**, in an application that only opens
a UART. The developer's first contact with our work is a compile error in a
dependency they did not write, about a peripheral they are not using.

The intended experience does exist — it just requires the HAL to compile
first. An application talking to the chip crate **directly** gets exactly what
the design promises:

```
error[E0277]: `TRISErs` is write-constrained by its datasheet
   --> src/lib.rs:5:21
    |
  5 |     dp.I2C1.trise().write(|w| unsafe { w.bits(9) });
    |                     ^^^^^ this register requires a witness: call
    |                           `write_when_ready(f)` …
```

So there are two regimes, and today's HAL-mediated corpus is entirely in the
first:

| | what the developer sees |
|---|---|
| the HAL itself touches a gated register | build fails inside the HAL; **no line of theirs is implicated** |
| the HAL does not, but the application does | error at the application's own line, naming the datasheet rule |

This is the strongest practical argument for landing one of the two fixes in
[`generic_friction.md`](generic_friction.md) upstream — not because friction
is large (8 errors), but because **until the HAL compiles, enforcement is
invisible to the person it is meant to protect.**

## What this does and does not show

**Shows:** an OS-level consumer driving the constrained crate through a HAL
adds no errors of its own. Hopter's application-facing code — clock setup,
GPIO configuration, opening a UART, byte I/O — compiles unchanged against the
injected crate. The adoption cost for a downstream OS is exactly the cost its
driver library already pays, not a new one.

**Does not show:** that Hopter itself builds. It cannot be built here without
`segstk-rust`. A complete result needs that toolchain plus a bump of Hopter's
HAL dev-dependency to 0.23 (with the API updates that entails) — at which
point `cargo check --examples --target thumbv7em-none-eabihf` would give the
real answer for all 9 HAL-using examples.

**Also worth noting:** because Hopter's kernel links no chip crate, the parts
of it that would benefit most from register constraints — the vector table it
hand-copied from the stm32f4 crate, its interrupt plumbing — are outside the
reach of this technique as currently scoped.
