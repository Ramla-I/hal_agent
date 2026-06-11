# Phase 2: Deprecation Warnings on Unconstrained `write()`/`modify()`

## Overview

Phase 2 extends the Phase 1 witness-token constraint system to emit **compiler deprecation warnings** when HAL code calls `write()` or `modify()` on registers that have hardware constraints. The safe alternative `write_constrained()` compiles without warnings.

The key technical challenge: `write()` and `modify()` are defined generically in `generic.rs` on `Reg<REG>`. We needed to make them emit warnings **only** for constrained register types (e.g., `CR1rs`) without affecting any other register.

## Solution: Trait-Based Method Shadowing

Rust resolves method calls by checking **inherent methods first**, then trait methods. By moving the generic `write()`/`modify()` implementations from inherent methods to traits (`RegWrite`/`RegModify`), we create a lower-priority fallback. The constraint module then defines deprecated **inherent** `write()`/`modify()` on the specific `Reg<CR1rs>` type, which shadow the trait methods for that type only.

```
                         ┌─────────────────────────────┐
                         │   Unconstrained register     │
                         │   e.g. i2c1.cr2().write()    │
                         │                              │
                         │   No inherent write() found  │
                         │   → Falls through to trait    │
                         │   → RegWrite::write()        │
                         │   → No warning               │
                         └─────────────────────────────┘

                         ┌─────────────────────────────┐
                         │   Constrained register       │
                         │   e.g. i2c1.cr1().write()    │
                         │                              │
                         │   Inherent write() found     │
                         │   → #[deprecated] method     │
                         │   → Compiler warning         │
                         └─────────────────────────────┘

                         ┌─────────────────────────────┐
                         │   Safe path                  │
                         │   i2c1.cr1()                 │
                         │     .write_constrained(...)  │
                         │                              │
                         │   Not deprecated             │
                         │   → No warning               │
                         └─────────────────────────────┘
```

## PAC Crate Changes (`stm32-rs/stm32f4/`)

### 1. `src/generic.rs` — Trait Extraction + Visibility

**Field visibility widened** (needed so the constraint module can construct `R`/`W` and access `Reg.register`):

| Field | Before | After |
|-------|--------|-------|
| `Reg.register` | private | `pub(crate)` |
| `raw::R._reg` | `pub(super)` | `pub(crate)` |
| `raw::W._reg` | `pub(super)` | `pub(crate)` |

**`write()` extracted to `RegWrite` trait** (lines 705-727):

```rust
pub trait RegWrite<REG: Resettable + Writable> {
    fn write<F>(&self, f: F) -> REG::Ux
    where
        F: FnOnce(&mut W<REG>) -> &mut W<REG>;
}

impl<REG: Resettable + Writable> RegWrite<REG> for Reg<REG> {
    #[inline(always)]
    fn write<F>(&self, f: F) -> REG::Ux
    where
        F: FnOnce(&mut W<REG>) -> &mut W<REG>,
    {
        // ... same body as before
    }
}
```

**`modify()` extracted to `RegModify` trait** (lines 834-862):

```rust
pub trait RegModify<REG: Readable + Writable> {
    fn modify<F>(&self, f: F) -> REG::Ux
    where
        for<'w> F: FnOnce(&R<REG>, &'w mut W<REG>) -> &'w mut W<REG>;
}

impl<REG: Readable + Writable> RegModify<REG> for Reg<REG> {
    #[inline(always)]
    fn modify<F>(&self, f: F) -> REG::Ux
    where
        for<'w> F: FnOnce(&R<REG>, &'w mut W<REG>) -> &'w mut W<REG>,
    {
        // ... same body as before
    }
}
```

All other methods (`reset()`, `from_write()`, `from_modify()`, `read()`, `write_with_zero()`, etc.) remain as inherent methods — unchanged.

### 2. `src/stm32f405/mod.rs` — Injected Constraint Module

Inside `pub mod i2c1 { ... }`, after `pub mod cr1 { ... }` closes, a `pub mod constraints` block is injected (lines 42470-42639). It contains:

**Phase 1 elements** (unchanged):
- Witness token types: `StopClearedToken`, `StartClearedToken`, `PecClearedToken`
- `ConstraintError` enum with `StopNotCleared`, `StartNotCleared`, `PecNotCleared`
- Verify methods on `super::cr1::R`: `verify_stop_cleared()`, `verify_start_cleared()`, `verify_pec_cleared()`

**Phase 2 additions** (all in a single `impl crate::Reg<super::cr1::CR1rs>` block):

- **`write_constrained()`** — safe write consuming tokens, no warning. Has its own body (does not delegate to `self.write()` to avoid triggering the deprecation).

- **`write()` (deprecated)** — inherent method marked with `#[deprecated]`. Shadows the `RegWrite` trait method for `CR1rs` only. The deprecation message reads:
  > I2C1_CR1 has hardware constraints: STOP must be cleared, START must be cleared, PEC must be cleared before writing. Use `i2c1::constraints::write_constrained()` instead.

- **`modify()` (deprecated)** — inherent method marked with `#[deprecated]`. Shadows the `RegModify` trait method for `CR1rs` only. Same deprecation message.

### 3. `src/lib.rs` — Re-exports

The traits are automatically public via `generic.rs`. Downstream crates access them as `stm32f4::RegWrite` and `stm32f4::RegModify`.

## HAL Crate Changes (`stm32f4xx-hal/`)

Since `write()` and `modify()` are now trait methods, every HAL source file that calls them must bring the trait into scope. Added imports to 24 files:

| File | Import |
|------|--------|
| `src/i2c.rs` | `use stm32f4::RegWrite;` |
| `src/i2c/dma.rs` | `use stm32f4::{RegModify, RegWrite};` |
| `src/adc.rs` | `use stm32f4::RegModify;` |
| `src/crc32.rs` | `use stm32f4::RegWrite;` |
| `src/dac.rs` | `use stm32f4::{RegModify, RegWrite};` |
| `src/dma/mod.rs` | `use stm32f4::{RegModify, RegWrite};` |
| `src/flash.rs` | `use stm32f4::{RegModify, RegWrite};` |
| `src/gpio.rs` | `use stm32f4::{RegModify, RegWrite};` |
| `src/gpio/convert.rs` | `use stm32f4::RegModify;` |
| `src/gpio/erased.rs` | `use stm32f4::RegWrite;` |
| `src/gpio/exti.rs` | `use stm32f4::{RegModify, RegWrite};` |
| `src/gpio/outport.rs` | `use stm32f4::RegWrite;` |
| `src/gpio/partially_erased.rs` | `use stm32f4::RegWrite;` |
| `src/qei.rs` | `use stm32f4::RegWrite;` |
| `src/rcc/f4/mod.rs` | `use stm32f4::RegModify;` |
| `src/rcc/f4/pll.rs` | `use stm32f4::{RegModify, RegWrite};` |
| `src/rng.rs` | `use stm32f4::RegModify;` |
| `src/rtc.rs` | `use stm32f4::{RegModify, RegWrite};` |
| `src/serial.rs` | `use stm32f4::RegWrite;` |
| `src/serial/uart_impls.rs` | `use stm32f4::{RegModify, RegWrite};` |
| `src/spi.rs` | `use stm32f4::{RegModify, RegWrite};` |
| `src/timer.rs` | `use stm32f4::{RegModify, RegWrite};` |
| `src/timer/pwm_input.rs` | `use stm32f4::RegModify;` |
| `src/watchdog.rs` | `use stm32f4::{RegModify, RegWrite};` |

Each file imports only the trait(s) it actually uses to avoid unused-import warnings.

## Code Generator Changes (`rust_codegen.py`)

- `generate_constraint_module()`: `write_constrained()` now has its own body (doesn't call `self.write()`). Also generates deprecated `write()` and `modify()` inherent methods in the same `impl` block.
- Added `patch_generic_rs()`: Patches field visibility and extracts `write()`/`modify()` to `RegWrite`/`RegModify` traits. Idempotent — checks for `pub trait RegWrite`/`RegModify` before patching.
- `inject_into_pac()`: Now calls `patch_generic_rs()` before injecting the constraint module.

## Expected Compiler Output

### PAC crate — clean

```
$ cargo check --features stm32f405
    Checking stm32f4 v0.16.0
    Finished `dev` profile [unoptimized + debuginfo] target(s)
```

No warnings in the PAC itself (no call sites for the deprecated methods within the PAC).

### HAL crate — 14 deprecation warnings

```
$ cargo check --features stm32f405 --target thumbv7em-none-eabihf
```

Produces 14 deprecation warnings, all on `cr1().modify(...)` calls:

**`src/i2c.rs`** (8 warnings):
- Line 149: `i2c.cr1().modify(|_, w| w.pe().clear_bit())`
- Line 206: `i2c.cr1().modify(|_, w| w.pe().set_bit())`
- Line 261: `i2c.cr1().modify(|_, w| w.start().set_bit())`
- Lines 326-327: `i2c.cr1().modify(|_, w| w.start().set_bit().ack().set_bit())`
- Line 352: `i2c.cr1().modify(|_, w| w.start().set_bit())`
- Line 460: `i2c.cr1().modify(|_, w| w.ack().clear_bit().stop().set_bit())`
- Line 490: `i2c.cr1().modify(|_, w| w.stop().set_bit())`
- Line 512: `i2c.cr1().modify(|_, w| w.stop().set_bit())`

**`src/i2c/dma.rs`** (6 warnings):
- Lines using `cr1().modify(...)` for START, STOP, PE operations

Each warning message reads:
```
warning: use of deprecated method `stm32f405::i2c1::constraints::<impl Reg<CR1rs>>::modify`:
I2C1_CR1 has hardware constraints: STOP must be cleared, START must be cleared,
PEC must be cleared before writing. Use `i2c1::constraints::write_constrained()` instead.
```

### constraint_test crate — clean (with `#[allow(deprecated)]`)

```
$ cargo check --target thumbv7em-none-eabihf
    Checking constraint_test v0.1.0
    Finished `dev` profile [unoptimized + debuginfo] target(s)
```

The test demonstrates all three paths:
1. `write_constrained()` with tokens — no warning
2. `write()` / `modify()` on CR1 — deprecated (suppressed with `#[allow(deprecated)]`)
3. `write()` / `modify()` on CR2 (unconstrained) — no warning, resolves via `RegWrite`/`RegModify` traits

## Why Not Inherent-vs-Inherent Shadowing?

The original plan proposed defining deprecated `write()`/`modify()` as inherent methods on `impl Reg<CR1rs>` that would shadow the generic `impl<REG> Reg<REG>` inherent methods. This fails with **E0592: duplicate definitions for `write`** — Rust does not allow two inherent impl blocks to define the same method on the same type, even when one is more specific.

The trait-based approach works because Rust's method resolution has a strict priority: **inherent methods always win over trait methods**. By making the generic versions trait methods, the constraint module's inherent deprecated methods shadow them for CR1rs without conflicting.
