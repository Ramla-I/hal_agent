# eval_hal — the "real driver" demonstration

## What this is

This tiny crate compiles **stm32f4xx-hal** — the standard, widely-used driver
library for these chips, which we did not write and do not modify — against
our constraint-injected chip crate. It answers the adoption question directly:
*what actually happens when real third-party code meets the witness-gated PAC?*

The swap uses Cargo's `[patch.crates-io]` mechanism: "wherever anything asks
for the `stm32f4` package from the registry, hand it our local copy instead."
That is exactly how a downstream user would consume the constrained crate —
one line in their workspace manifest, no build steps, no forked driver.

## The result (pinned as a regression test, `test_hal_demo`)

Compiling the unmodified driver library (~30k lines) against the injected
crate produces exactly two kinds of outcome, and nothing else:

**1. True enforcement — 14 errors, all in the I2C driver.**
The datasheet says I2C control register 1 must not be written while a
STOP/START/PEC request is pending. The driver library touches that register
at 14 places (`src/i2c.rs`, `src/i2c/dma.rs`), and every one of them now
fails to compile with the message *"…is modify-constrained by its datasheet"*
plus instructions for the witnessed alternative. No other part of the
library is affected by the constraint: zero false hits.

**2. Known friction — 14 errors, all in the serial module.**
The serial (UART) part of this driver library is written *generically*: one
piece of code that works over "any UART-ish register block" through a trait.
Generic code has to declare, in its signature, everything it relies on — and
"this register needs no witness" is now one of those things. The serial
module predates our change, doesn't declare it, and therefore fails to
type-check **even though no UART register is actually constrained**. The fix
would be ~10 mechanical one-line additions in one module of the driver — but
that is a (small, quantified) modification, which is why we count it
separately and honestly.

The plain-code parts of the library (I2C, SPI, GPIO, timers — the large
majority) need nothing.

## Why the friction exists, in one paragraph

Our whole approach is to make the dangerous method *not exist* for a
constrained register, so the compiler can refuse it. Code that names a
concrete register gets this for free: either its register has the "no
witness needed" marker or it doesn't. But code that is generic over registers
must promise the compiler its requirements up front, and a promise written
before our markers existed can't mention them. Any design that removes
methods conditionally has this property; the alternative (the old wrapper
design) kept every method callable and had a silent bypass instead — a far
worse trade.

## Running it

```sh
python applications/pac_codegen/get_pac.py       # provision the chip crate
cd applications/pac_codegen/eval_hal
cargo check                                       # baseline: must pass
# inject constraints (see ../README.md), re-run: the two error classes above
```

The pytest version (`test_codegen.py::test_hal_demo`) does all of this,
asserts the exact error inventory, and restores the chip crate afterward.
