# Phase 3: ConstrainedReg Wrapper + Compilation Errors

## Overview

Phase 3 replaces the Phase 2 trait-based method shadowing approach with a **`ConstrainedReg<REG>` newtype wrapper** and escalates constraint enforcement from deprecation warnings to **hard compilation errors**. The result is zero HAL source changes and stronger compile-time safety.

This was implemented in two steps:
1. **Phase 3a**: Replace `RegWrite`/`RegModify` traits with `ConstrainedReg<REG>` + Deref-based shadowing (deprecation warnings preserved)
2. **Phase 3b**: Replace deprecated `write()`/`modify()` shadows with token-requiring versions that cause argument-count compilation errors

## Why Replace Phase 2?

Phase 2 moved `write()`/`modify()` from inherent methods to `RegWrite`/`RegModify` traits, then shadowed them with deprecated inherent methods on specific register types. This worked but had a significant cost:

- **24 HAL files needed `use stm32f4::{RegWrite, RegModify}` imports** — because `write()` and `modify()` became trait methods, every call site needed the trait in scope
- **Downstream breakage** — any crate calling `write()`/`modify()` would fail until imports were added
- **Fragile** — new HAL files must remember to add the imports

Phase 3 eliminates all of this: `write()` and `modify()` stay as inherent methods on `Reg<REG>` (untouched), and `ConstrainedReg<REG>` interposes only for constrained registers via `Deref`.

## Phase 3a: ConstrainedReg Wrapper

### Approach: Deref-Based Method Shadowing

```
                         ┌─────────────────────────────┐
                         │   Unconstrained register     │
                         │   e.g. i2c1.cr2().write()    │
                         │                              │
                         │   Type: Reg<CR2rs>            │
                         │   → Inherent Reg::write()    │
                         │   → No change                │
                         └─────────────────────────────┘

                         ┌─────────────────────────────┐
                         │   Constrained register       │
                         │   e.g. i2c1.cr1().write(f)   │
                         │                              │
                         │   Type: ConstrainedReg<CR1rs> │
                         │   → Inherent write(f, tokens) │
                         │     found (wrong arg count)  │
                         │   → Compilation error        │
                         └─────────────────────────────┘

                         ┌─────────────────────────────┐
                         │   Safe path                  │
                         │   i2c1.cr1()                 │
                         │     .write_constrained(...)  │
                         │                              │
                         │   Inherent on ConstrainedReg │
                         │   → Compiles cleanly         │
                         └─────────────────────────────┘
```

`ConstrainedReg<REG>` is a `#[repr(transparent)]` newtype wrapping `Reg<REG>`. It implements `Deref<Target = Reg<REG>>`, so all existing methods (`read()`, `reset()`, `write_with_zero()`, etc.) forward transparently. The constraint module adds inherent `write()`/`modify()` methods on `ConstrainedReg<CR1rs>` that shadow the `Deref` target's methods — inherent methods always win over deref'd methods in Rust's method resolution.

### PAC Crate Changes (`stm32-rs/stm32f4/`)

#### 1. `src/generic.rs` — ConstrainedReg Definition

**Field visibility** (same as Phase 2, unchanged):

| Field | Before | After |
|-------|--------|-------|
| `Reg.register` | private | `pub(crate)` |
| `raw::R._reg` | `pub(super)` | `pub(crate)` |
| `raw::W._reg` | `pub(super)` | `pub(crate)` |

**Removed** from Phase 2:
- `pub trait RegWrite<REG>` — deleted entirely
- `pub trait RegModify<REG>` — deleted entirely
- `write()` and `modify()` restored to inherent methods on `Reg<REG>` (svd2rust default)

**Added** after `unsafe impl Send for Reg<REG>`:

```rust
/// A register wrapper indicating hardware write constraints exist.
/// Forwards all operations via Deref to Reg; constraint modules add
/// write()/modify() shadows as inherent methods.
#[repr(transparent)]
pub struct ConstrainedReg<REG: RegisterSpec> {
    pub(crate) reg: Reg<REG>,
}

unsafe impl<REG: RegisterSpec> Send for ConstrainedReg<REG> where REG::Ux: Send {}

impl<REG: RegisterSpec> core::ops::Deref for ConstrainedReg<REG> {
    type Target = Reg<REG>;
    #[inline(always)]
    fn deref(&self) -> &Reg<REG> {
        &self.reg
    }
}

impl<REG: Readable> core::fmt::Debug for ConstrainedReg<REG>
where
    R<REG>: core::fmt::Debug,
{
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        core::fmt::Debug::fmt(&**self, f)
    }
}
```

Key design decisions:
- **`#[repr(transparent)]`** — same layout as `Reg<REG>`, zero overhead
- **`Debug` impl** — required because `RegisterBlock` derives `Debug`; delegates through `Deref` to `Reg`'s `Debug` impl
- **`Send` impl** — mirrors the `Send` impl on `Reg<REG>`

#### 2. `src/stm32f405/mod.rs` — Type Alias Patch

The register type alias is patched from:
```rust
pub type CR1 = crate::Reg<cr1::CR1rs>;
```
to:
```rust
pub type CR1 = crate::ConstrainedReg<cr1::CR1rs>;
```

This is scoped to the correct peripheral module (`pub mod i2c1`). The `RegisterBlock` struct, accessor methods, and all downstream code use the alias transparently — `ConstrainedReg` derefs to `Reg`, so `read()`, `reset()`, and all other operations work unchanged.

#### 3. `src/stm32f405/mod.rs` — Constraint Module

The injected `pub mod constraints` block changes from Phase 2:

- **Impl block target**: `impl crate::ConstrainedReg<super::cr1::CR1rs>` (was `impl crate::Reg<...>`)
- **Field access path**: `self.reg.register.set(value)` / `self.reg.register.get()` (was `self.register.set/get`)

### HAL Crate Changes

**Zero HAL source changes.** The 24 `use stm32f4::{RegWrite, RegModify}` import lines added in Phase 2 were **removed**. Since `write()` and `modify()` are back to inherent methods on `Reg<REG>`, no trait imports are needed anywhere.

The HAL submodule was updated from commit `e077fbd` (Phase 2, with trait imports) to `eca3bd5` (Phase 3, imports removed).

### Code Generator Changes (`rust_codegen.py`)

- `generate_constraint_module()`: `impl` block target changed from `crate::Reg<...>` to `crate::ConstrainedReg<...>`; field access changed to `self.reg.register.set/get`
- `patch_generic_rs()`: Removed all `RegWrite`/`RegModify` trait extraction logic (~80 lines of regex). Replaced with `ConstrainedReg` struct injection (~25 lines), inserted after the `Send for Reg<REG>` impl. Idempotent — checks for `pub struct ConstrainedReg` before patching.
- `inject_into_pac()`: Added type alias patching — finds `pub type CR1 = crate::Reg<...>` within the correct peripheral module and replaces with `crate::ConstrainedReg<...>`

## Phase 3b: Compilation Errors (Replacing Deprecation Warnings)

### Motivation

Phase 3a preserved the Phase 2 behavior of `#[deprecated]` `write()`/`modify()` shadows — calling them without tokens triggered deprecation warnings. Phase 3b strengthens this to **hard compilation errors** by changing the shadowing methods to require witness tokens as arguments.

### Mechanism: Argument Count Mismatch

Instead of:
```rust
// Phase 3a: deprecated, takes same args as Reg::write()
#[deprecated(note = "...")]
pub fn write<F>(&self, f: F) -> ... { ... }
```

Phase 3b generates:
```rust
// Phase 3b: requires tokens, different signature from Reg::write()
pub fn write<F>(&self, f: F, _stop: StopClearedToken, _start: StartClearedToken, _pec: PecClearedToken) -> ... {
    self.write_constrained(f, _stop, _start, _pec)
}
```

When HAL code calls `i2c1.cr1().modify(|_, w| w.stop().set_bit())`, the inherent `modify()` on `ConstrainedReg<CR1rs>` wins method resolution (over the deref'd `Reg::modify()`). But the inherent method takes 4 arguments, and the call site provides 1 — producing **E0061: this method takes 4 arguments but 1 argument was supplied**.

### Added: `modify_constrained()`

Phase 3b also adds `modify_constrained()` — the read-modify-write counterpart to `write_constrained()`:

```rust
pub fn modify_constrained<F>(&self, f: F,
    _stop_token: StopClearedToken,
    _start_token: StartClearedToken,
    _pec_token: PecClearedToken,
) -> <CR1rs as RegisterSpec>::Ux
where
    for<'w> F: FnOnce(&R<CR1rs>, &'w mut W<CR1rs>) -> &'w mut W<CR1rs>,
{
    let bits = self.reg.register.get();
    let value = f(
        &R { bits, _reg: PhantomData },
        &mut W { bits: bits & !ONE_TO_MODIFY | ZERO_TO_MODIFY, _reg: PhantomData },
    ).bits;
    self.reg.register.set(value);
    value
}
```

### Generated Constraint Module (Final)

Inside `pub mod i2c1 { pub mod constraints { ... } }`:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `write_constrained(f, tokens...)` | Inherent on `ConstrainedReg<CR1rs>` | Safe write from reset value with tokens |
| `modify_constrained(f, tokens...)` | Inherent on `ConstrainedReg<CR1rs>` | Safe read-modify-write with tokens |
| `write(f, tokens...)` | Inherent on `ConstrainedReg<CR1rs>` | Shadows `Reg::write(f)` — causes E0061 without tokens |
| `modify(f, tokens...)` | Inherent on `ConstrainedReg<CR1rs>` | Shadows `Reg::modify(f)` — causes E0061 without tokens |
| `verify_stop_cleared()` | On `cr1::R` | Returns `Result<StopClearedToken, ConstraintError>` |
| `verify_start_cleared()` | On `cr1::R` | Returns `Result<StartClearedToken, ConstraintError>` |
| `verify_pec_cleared()` | On `cr1::R` | Returns `Result<PecClearedToken, ConstraintError>` |

### constraint_test Changes

The test crate demonstrates all paths:

1. **`write_constrained()` with tokens** — compiles cleanly
2. **`modify_constrained()` with tokens** — compiles cleanly (new in Phase 3b)
3. **`write(f, tokens...)` with tokens** — compiles cleanly (shadow method accepts tokens)
4. **`modify(f, tokens...)` with tokens** — compiles cleanly (shadow method accepts tokens)
5. **`cr2().write(f)` / `cr2().modify(f)`** — unconstrained register, `Deref` to `Reg` provides originals
6. **`cr1().write(f)` without tokens** — would produce E0061 (commented out, documented)

Removed from Phase 2: `use stm32f4::{RegModify, RegWrite}` import and `#[allow(deprecated)]` blocks.

## Expected Compiler Output

### PAC crate — clean

```
$ cargo check --features stm32f405
    Checking stm32f4 v0.16.0
    Finished `dev` profile [unoptimized + debuginfo] target(s)
```

### HAL crate — 14 compilation errors

```
$ cargo check --features stm32f405 --target thumbv7em-none-eabihf
```

Produces 14 errors, all **E0061** on `cr1().modify(...)` calls:

**`src/i2c.rs`** (8 errors):
- Line 149: `self.i2c.cr1().modify(|_, w| w.pe().clear_bit())`
- Line 205: `self.i2c.cr1().modify(|_, w| w.pe().set_bit())`
- Line 261: `self.i2c.cr1().modify(|_, w| w.start().set_bit())`
- Line 326: `.modify(|_, w| w.start().set_bit().ack().set_bit())`
- Line 352: `self.i2c.cr1().modify(|_, w| w.start().set_bit())`
- Line 461: `.modify(|_, w| w.ack().clear_bit().stop().set_bit())`
- Line 490: `self.i2c.cr1().modify(|_, w| w.stop().set_bit())`
- Line 511: `self.i2c.cr1().modify(|_, w| w.stop().set_bit())`

**`src/i2c/dma.rs`** (6 errors):
- Line 432: `i2c.cr1().modify(|_, w| w.ack().set_bit().start().set_bit())`
- Line 434: `i2c.cr1().modify(|_, w| w.start().set_bit())`
- Line 459: `self.hal_i2c.i2c.cr1().modify(|_, w| w.stop().set_bit())`
- Line 529: `self.hal_i2c.i2c.cr1().modify(|_, w| w.ack().clear_bit())`
- Line 701: `self.hal_i2c.i2c.cr1().modify(|_, w| w.ack().clear_bit())`
- Line 788: `self.hal_i2c.i2c.cr1().modify(|_, w| w.ack().clear_bit())`

Each error message reads:
```
error[E0061]: this method takes 4 arguments but 1 argument was supplied
     --> src/i2c.rs:149:24
      |
149   |         self.i2c.cr1().modify(|_, w| w.pe().clear_bit());
      |                        ^^^^^^--------------------------- three arguments of type
      |     `StopClearedToken`, `StartClearedToken`, and `PecClearedToken` are missing
```

### constraint_test crate — clean

```
$ cargo check --target thumbv7em-none-eabihf
    Checking constraint_test v0.1.0
    Finished `dev` profile [unoptimized + debuginfo] target(s)
```

## Summary of Changes from Phase 2

| Aspect | Phase 2 | Phase 3 |
|--------|---------|---------|
| `generic.rs` mechanism | `RegWrite`/`RegModify` traits | `ConstrainedReg<REG>` newtype + `Deref` |
| HAL source changes | 24 files need trait imports | **Zero** |
| Enforcement level | Deprecation warnings | **Compilation errors (E0061)** |
| `modify()` safe path | N/A (only `write_constrained`) | `modify_constrained()` added |
| Shadow method body | Duplicated write/modify logic | Delegates to `write_constrained`/`modify_constrained` |
| `write()`/`modify()` on `Reg` | Trait methods (`RegWrite`/`RegModify`) | **Inherent methods (unchanged from svd2rust)** |
| Downstream crate impact | Must add `use stm32f4::{RegWrite, RegModify}` | **None** |
