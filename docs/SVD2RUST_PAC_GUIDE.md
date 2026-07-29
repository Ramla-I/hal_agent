# How svd2rust Generates PAC Crates

## What Is a PAC?

A **Peripheral Access Crate** (PAC) is a low-level Rust library that provides type-safe access to a microcontroller's memory-mapped hardware registers. It is auto-generated from an SVD (System View Description) file — an XML document that describes every peripheral, register, field, and enumerated value on the chip.

The tool that performs this generation is **svd2rust** (v0.37.1 as of this writing). It reads the SVD and produces a complete Rust crate with zero-cost abstractions over raw volatile register access.

## The svd2rust Code Generation Pipeline

```
                                    ┌──────────────────┐
                                    │  STM32F405.svd   │
                                    │  (XML input)     │
                                    └────────┬─────────┘
                                             │
                                    svd_parser::parse()
                                             │
                                    ┌────────▼─────────┐
                                    │  svd::Device      │
                                    │  (in-memory AST)  │
                                    └────────┬─────────┘
                                             │
                              svd_parser::expand::Index::create()
                                             │
                          ┌──────────────────┼──────────────────┐
                          │                  │                  │
              generate::device::render()     │                  │
                          │                  │                  │
            ┌─────────────┼──────────┐       │                  │
            │             │          │       │                  │
   Crate attributes   Generic    Peripherals loop          Peripherals
   (#![no_std], etc)  module     (for each peripheral)     struct + take()
            │             │          │
            │    include_str!()      │
            │    generic.rs +        │
            │    generic_reg_vcell.rs │
            │             │          │
            │             │    peripheral::render()
            │             │          │
            │             │    ┌─────┼──────────────┐
            │             │    │     │              │
            │             │  Periph  RegisterBlock  Register modules
            │             │  type    struct +       (for each register)
            │             │  alias   accessors
            │             │                         │
            │             │                  register::render()
            │             │                         │
            │             │                  ┌──────┼──────────┐
            │             │                  │      │          │
            │             │             Type alias  Register   Field readers
            │             │             CR1 = Reg   module     & writers
            │             │             <cr1::      pub mod    (per field)
            │             │              CR1rs>     cr1 { }
            │             │
            └─────────────┴──────── → TokenStream → rustfmt → lib.rs / mod.rs
```

### Step-by-step

1. **Parse SVD**: `svd_parser` reads the XML into a `svd::Device` tree of peripherals, registers, fields, and enumerated values.

2. **Expand and index**: `svd_parser::expand::Index` resolves `derivedFrom` references (e.g., I2C2 derived from I2C1), expands register arrays, and builds lookup tables.

3. **Render device** (`generate/device.rs`):
   - Emits crate-level attributes (`#![no_std]`, `#![allow(...)]`)
   - Includes the generic register infrastructure as a `pub mod generic` by embedding two static Rust source files via `include_str!()`:
     - `generic.rs` — trait hierarchy, R/W types, field readers/writers
     - `generic_reg_vcell.rs` — `Reg<REG>` struct with `read`/`write`/`modify`/`reset` methods
   - Optionally includes `generic_atomic.rs` for atomic register operations
   - Iterates all peripherals, calling `peripheral::render()` for each
   - Generates the `Peripherals` struct with `take()` and `steal()`

4. **Render peripheral** (`generate/peripheral.rs`):
   - Emits `pub type I2C1 = crate::Periph<i2c1::RegisterBlock, 0x4000_5400>`
   - Generates `pub mod i2c1 { ... }` containing the `RegisterBlock` struct and accessor methods
   - For derived peripherals (e.g., I2C2), emits a type alias with a different base address and a `pub use` re-export of the base module
   - Calls `register::render()` for each register in the peripheral

5. **Render register** (`generate/register.rs`):
   - Emits the register type alias: `pub type CR1 = crate::Reg<cr1::CR1rs>`
   - Generates `pub mod cr1 { ... }` containing:
     - `R` and `W` type aliases
     - Field reader and writer types
     - Enumerated value types
     - `impl R { ... }` with field reader accessors
     - `impl W { ... }` with field writer accessors
     - `impl Debug for R`
     - Register spec struct + trait impls (`RegisterSpec`, `Readable`, `Writable`, `Resettable`)

6. **Output**: All `TokenStream`s are collected into a single stream, written to `lib.rs` (or `mod.rs` per device when using `--generic_mod`), and formatted with `rustfmt`.

### Static Templates vs. Generated Code

svd2rust uses **two strategies** for code generation:

| Component | Strategy | File |
|-----------|----------|------|
| Generic infrastructure (Reg, R, W, traits, field proxies) | **Static template** — Rust source files embedded via `include_str!()` | `generate/generic.rs`, `generate/generic_reg_vcell.rs` |
| Device-specific code (peripherals, registers, fields) | **Programmatic** — built with `proc_macro2`/`quote` macros | `generate/peripheral.rs`, `generate/register.rs` |

The generic module is identical across all devices. Only the device-specific peripheral/register/field code varies.

## Generated PAC Crate Structure

### Directory Layout

```
stm32f4/
├── Cargo.toml
├── build.rs
└── src/
    ├── lib.rs                    # Crate root — re-exports generic, feature-gates devices
    ├── generic.rs                # Generic register infrastructure (Reg, R, W, traits, etc.)
    └── stm32f405/
        ├── mod.rs                # ALL peripherals for this device (single monolithic file)
        └── device.x              # Linker script for interrupt vector table
```

All device-specific code lives in a single `mod.rs` file — for STM32F405 this is ~101,000 lines. Each peripheral is a nested module within that file.

### Cargo.toml — Dependencies

```toml
[dependencies]
vcell = "0.1.3"                                    # Volatile cell for register access
cortex-m = "0.7.7"                                 # ARM Cortex-M core support
cortex-m-rt = { version = "0.7.5", optional = true } # Runtime + interrupt vectors
critical-section = { version = "1.0", optional = true } # Safe Peripherals::take()
defmt = { version = "1", optional = true }          # Embedded logging
portable-atomic = { version = "1", optional = true } # Atomic register operations

[features]
default = ["critical-section", "rt"]
rt = ["cortex-m-rt/device"]
stm32f405 = []            # One empty feature per device variant
# ... stm32f401, stm32f407, etc.
```

Only one device feature should be enabled at a time.

### lib.rs — Crate Entry Point

```rust
#![no_std]
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]

mod generic;
pub use self::generic::*;       // Re-export all generic types at crate root

#[cfg(feature = "stm32f405")]
pub mod stm32f405;
// ... other device modules
```

The `pub use self::generic::*` line is what makes types like `Reg`, `R`, `W`, `Readable`, `Writable`, `BitReader`, `FieldWriter`, etc. accessible as `crate::Reg`, `crate::R`, etc. throughout the PAC.

## The Generic Module (`generic.rs`)

This is the heart of the PAC's type system. It provides the infrastructure that all device-specific code builds on.

### Trait Hierarchy

```
                    RegisterSpec                   FieldSpec
                    (type Ux)                      (type Ux)
                   /    |     \                        |
              Readable  Writable  Resettable       IsEnum (marker)
                        (type Safety;
                         ZERO_TO_MODIFY_FIELDS_BITMAP;
                         ONE_TO_MODIFY_FIELDS_BITMAP)

    RawReg: Copy + BitOr + BitAnd + Shl<u8> + ...
    (implemented for u8, u16, u32, u64)
```

- **`RegisterSpec`**: Every register has a spec struct (e.g., `CR1rs`) that implements this trait. `type Ux` specifies the register width (`u8`/`u16`/`u32`/`u64`).
- **`Readable`**: Marker — register can be read. Enables `Reg::read()`.
- **`Writable`**: Register can be written. `type Safety` controls whether raw bit writes need `unsafe`. `ZERO_TO_MODIFY_FIELDS_BITMAP` and `ONE_TO_MODIFY_FIELDS_BITMAP` handle write-1-to-clear / write-0-to-set semantics.
- **`Resettable`**: Register has a known reset value. `RESET_VALUE` defaults to 0. Enables `Reg::reset()` and `Reg::write()` (which starts from the reset value).
- **`FieldSpec`**: Individual fields have spec types. `IsEnum` marks fields with enumerated values.

### `Reg<REG>` — The Register Accessor

```rust
#[repr(transparent)]
pub struct Reg<REG: RegisterSpec> {
    register: vcell::VolatileCell<REG::Ux>,
    _marker: marker::PhantomData<REG>,
}
```

`Reg` is a transparent wrapper around a `VolatileCell` — it exists at the exact memory address of the hardware register. The `REG` type parameter carries all the register's metadata (width, readable/writable, reset value) at the type level.

The `read()`/`write()`/`modify()` methods and the reader/writer value types together form the layered API described in the next section.

### The API levels: access path, register methods, value methods

Reaching a hardware register goes through three levels, which are easy to conflate:

- **Level 0 — the access path.** The singleton `Peripherals` and the zero-sized `Periph<RB, A>` handles, whose `const fn` accessors (`dp.i2c1()`, `i2c1.cr1()`) compute addresses and hand back a `&Reg<REG>`. No volatile access happens here; this level enforces single-ownership of each peripheral.
- **Level 1 — methods on `Reg<REG>` (the register handle itself).** These are the *only* operations that touch hardware: each performs a volatile read and/or write, and each exists only when the register's marker type carries the matching capability trait. This is where the enforcement gating in this project lives.
- **Level 2 — methods on the `R<REG>` / `W<REG>` *value* that a Level-1 call hands you.** These are the field getters/setters and the raw whole-word accessors. They never touch hardware — they only inspect or compose an in-memory word.

| Level | Operates on | Example calls | Touches hardware? | Governed by |
|-------|-------------|---------------|-------------------|-------------|
| **0 — access path** | `Peripherals`, `Periph<RB, A>` | `Peripherals::take()`, `dp.i2c1()`, `i2c1.cr1()` | No — computes addresses, enforces single ownership | Singleton `take()` / `unsafe steal()`; `Deref` to the register block |
| **1 — register methods** | `Reg<REG>` | `.read()`, `.write(f)`, `.modify(f)`, `.reset()` | **Yes** — volatile read and/or write | Capability traits `Readable` / `Writable` / `Resettable` |
| **2 — value methods** | `R<REG>`, `W<REG>` | `r.pe().bit_is_set()`, `w.pe().set_bit()`, `w.bits(x)` | No — an in-memory word | Field proxy types + `Writable::Safety` |

The levels only compose downward: you reach a `Reg<REG>` (Level 1) only through a Level-0 accessor, and you obtain an `R` or `W` (Level 2) only *through* a Level-1 call — `read()` returns an `R`; `write`/`modify` build a `W` and pass `&mut W` into your closure. So each hardware interaction is a Level-1 call, reached via the Level-0 path, that brackets some Level-2 field manipulation. Level 0 is detailed below under *`Periph`* and *Device-Specific Code Format*; Levels 1 and 2 follow here.

#### Level 1 — every method on `Reg<REG>`

Each row is a volatile access, present only under the listed trait bound (a read-only register has no `write`; a write-only register has no `read`; and so on).

| Method | Trait bound | Safety | What it does |
|--------|-------------|--------|--------------|
| `as_ptr()` | `RegisterSpec` | safe | Returns `*mut REG::Ux` (the register's address). Performs no access. |
| `read()` | `Readable` | safe | One volatile read; returns an `R<REG>` snapshot. |
| `reset()` | `Resettable + Writable` | safe | One volatile write of `REG::RESET_VALUE`. |
| `write(f)` | `Resettable + Writable` | safe | Builds a `W` pre-loaded with the reset value, runs `f(&mut W) -> &mut W`, then one volatile write of the result. |
| `from_write(f)` | `Resettable + Writable` | safe | Like `write`, but `f` also returns a value `T` that `from_write` returns to the caller. |
| `modify(f)` | `Readable + Writable` | safe | One volatile read, runs `f(&R, &mut W)` with `W` pre-loaded from the **current** value, then one volatile write. Read-modify-write. |
| `from_modify(f)` | `Readable + Writable` | safe | Like `modify`, but `f` also returns a value `T` that `from_modify` returns. |
| `write_with_zero(f)` | `Writable` | **unsafe** | Like `write` but `W` starts from `0` instead of the reset value. `unsafe` because `0` may be an invalid content for some fields. |
| `from_write_with_zero(f)` | `Writable` | **unsafe** | The `from_write` variant of `write_with_zero`. |
| `set_bits(f)` / `clear_bits(f)` / `toggle_bits(f)` | `Readable + Writable` where `REG::Ux: AtomicOperations` | **unsafe** | On cores with atomics: set / clear / toggle exactly the bits the closure touched, in a single atomic read-modify-write instruction. `unsafe` because the resulting pattern may not be valid. |

The `write()` body shows how the scratch value is seeded:

```rust
pub fn write<F>(&self, f: F) -> REG::Ux
where F: FnOnce(&mut W<REG>) -> &mut W<REG>,
{
    let value = f(&mut W {
        bits: REG::RESET_VALUE
            & !REG::ONE_TO_MODIFY_FIELDS_BITMAP
            |  REG::ZERO_TO_MODIFY_FIELDS_BITMAP,
        _reg: marker::PhantomData,
    }).bits;
    self.register.set(value);   // volatile write
    value
}
```

The bitmask manipulation makes write-1-to-clear fields start at 0 (so you don't accidentally clear them) and write-0-to-set fields start at 1.

**Mental model — `write()` hands you a scratch buffer and flushes it.** `reg.write(|w| …)` (1) creates a fresh `W<REG>` — call it `w` — pre-loaded with the reset value, (2) runs your closure so you can set fields on `w`, (3) stores whatever `w` ends up holding — the whole word — in one volatile write. `w` is **not** the register; it is a throwaway staging value. Tracing it (I2C_CR1, reset `0x0000`):

```rust
i2c1.cr1().write(|w| {
    // w pre-loaded with RESET_VALUE:  w = 0x0000
    w.pe().set_bit();   // set PE bit:  w = 0x0001
    w.ack().set_bit();  // set ACK bit: w = 0x0401
    w                   // hand w back; write() then stores 0x0401
});
```

`modify(|r, w| …)` is identical except `w` starts from the register's **current** value instead of the reset value, so fields you don't touch keep their live contents. That single difference — reset base vs. live base — *is* the whole distinction between `write` and `modify`. `reset()` is the degenerate case: the reset value written with no closure at all.

#### Level 2 — the value types `R<REG>` and `W<REG>`

Both are transparent wrappers over one raw word:

```rust
pub struct R<REG: RegisterSpec> {   // holds the value just read
    pub(crate) bits: REG::Ux,
    pub(crate) _reg: marker::PhantomData<REG>,
}

pub struct W<REG: RegisterSpec> {   // holds the value being built for writing
    pub(crate) bits: REG::Ux,
    pub(crate) _reg: marker::PhantomData<REG>,
}
```

Every Level-2 method is either a **raw whole-word** accessor or a **named field** accessor. The device-specific `impl R` / `impl W` blocks generate one named accessor per field; none of them touch hardware.

**Reader `R<REG>` — all methods safe.** A read can never yield an invalid value, so there is no safe/unsafe split, and every accessor is a `const fn`:

| Accessor | Returns / proxy | Proxy methods |
|----------|-----------------|---------------|
| raw: `r.bits()` | `REG::Ux` | — the whole word |
| 1-bit field: `r.<field>()` | `BitReader<FI>` | `bit()` → `bool`, `bit_is_set()`, `bit_is_clear()` |
| multi-bit field: `r.<field>()` | `FieldReader<FI>` | `bits()` → the field's value (`FI::Ux`) |
| enumerated field: `r.<field>()` | `BitReader` / `FieldReader` | the above, **plus** `variant()` → the field's enum, and one `is_<value>()` → `bool` per enum variant |

**Writer `W<REG>` — field setters are safe; raw whole-word writes split on `Safety`.**

Raw whole-word writers overwrite the entire buffer:

| Method | Available when | Safety |
|--------|----------------|--------|
| `w.bits(x)` | any `Writable` register | **unsafe** — you assert `x` is a valid content |
| `w.set(x)` | only when `Writable::Safety = Safe` | safe — every bit pattern is valid (typically data registers) |

Named field setters — `w.<field>()` returns a proxy whose type encodes the field's write behavior. Each proxy method **merges** into `w` (touches only that field's bits) and returns `&mut W`, so calls chain:

| Proxy | Used for | Methods |
|-------|----------|---------|
| `BitWriter<'a, REG>` | normal read-write bit | `set_bit()`, `clear_bit()`, `bit(value: bool)` |
| `BitWriter1C<'a, REG>` | write-1-to-clear bit | `clear_bit_by_one()` |
| `BitWriter0S<'a, REG>` | write-0-to-set bit | `set_bit_by_zero()` |
| `BitWriter1T<'a, REG>` | write-1-to-toggle bit | `toggle_bit()` |
| `FieldWriter<'a, REG, WI, FI, Safety>` | multi-bit field | `bits(value)` — safe or `unsafe` per the field's `Safety` — plus `variant(enum)` when the field has enumerated values (always safe) |

**Merge vs. overwrite** is the key contrast. Field setters **merge**: `set_bit()` is `w.bits |= 1 << o`, `clear_bit()` is `w.bits &= !(1 << o)`, and a multi-bit `bits(v)` clears then ors (`w.bits &= !(mask << o); w.bits |= (v & mask) << o`). So composing several field setters accumulates. The raw `bits`/`set` instead **overwrite** the whole buffer (`w.bits = x`). Chaining a few field setters:

```rust
periph.reg().write(|w| w.field1().set_bit().field2().variant(SomeEnum::Value));
```

#### Safety marker types

```rust
pub struct Safe;                                    // any value valid
pub struct Unsafe;                                  // caller must ensure validity
pub struct Range<const MIN: u64, const MAX: u64>;   // runtime range check
pub struct RangeFrom<const MIN: u64>;               // lower-bound check
pub struct RangeTo<const MAX: u64>;                 // upper-bound check
```

These appear in two places: as the `Writable::Safety` associated type (which decides whether the register's raw `w.set()` exists — it does only for `Safety = Safe`) and as the `Safety` parameter on `FieldWriter` (which decides whether that field's `bits(value)` is safe). `Safe` needs no `unsafe`; `Unsafe` requires the caller to reach for `unsafe`; the `Range*` variants keep the setter safe but insert a runtime `assert!` that the value is in range.

### `Periph<RB, const A: usize>` — Peripheral Wrapper

```rust
pub struct Periph<RB, const A: usize> {
    _marker: marker::PhantomData<RB>,
}

impl<RB, const A: usize> core::ops::Deref for Periph<RB, A> {
    type Target = RB;
    fn deref(&self) -> &Self::Target {
        unsafe { &*Self::PTR }      // PTR = A as *const RB
    }
}
```

- `RB`: the `RegisterBlock` type, `A`: the base address as a const generic.
- `Periph` is zero-sized. `Deref` reinterprets the address as a reference to the register block.
- `steal()` creates an instance (unsafe); the safe path is `Peripherals::take()`.

## Device-Specific Code Format

### Peripheral Module Structure

Each peripheral in the SVD becomes a type alias + module:

```rust
// Type alias — zero-sized handle pointing to the base address
pub type I2C1 = crate::Periph<i2c1::RegisterBlock, 0x4000_5400>;

pub mod i2c1 {
    // RegisterBlock — C-layout struct at the peripheral's base address
    #[repr(C)]
    #[derive(Debug)]
    pub struct RegisterBlock {
        cr1: CR1,                       // 0x00
        _reserved1: [u8; 0x02],         // padding
        cr2: CR2,                       // 0x04
        _reserved2: [u8; 0x02],
        oar1: OAR1,                     // 0x08
        // ...
    }

    // Accessor methods — return references to register types
    impl RegisterBlock {
        #[inline(always)]
        pub const fn cr1(&self) -> &CR1 { &self.cr1 }
        pub const fn cr2(&self) -> &CR2 { &self.cr2 }
        // ...
    }

    // Register type aliases
    pub type CR1 = crate::Reg<cr1::CR1rs>;
    pub type CR2 = crate::Reg<cr2::CR2rs>;
    // ...

    // Register modules
    pub mod cr1 { /* ... */ }
    pub mod cr2 { /* ... */ }
    // ...
}
```

- `RegisterBlock` fields are **private** — access is through `const fn` accessor methods only.
- Reserved/padding bytes fill gaps between registers to maintain correct offsets.
- For 16-bit registers on a 32-bit bus, there's typically 2 bytes of padding after each register.

### Derived (Shared) Peripherals

When multiple peripherals share the same register layout (common for I2C, SPI, USART instances), svd2rust avoids code duplication:

```rust
// I2C1 — canonical definition
pub type I2C1 = crate::Periph<i2c1::RegisterBlock, 0x4000_5400>;
pub mod i2c1 { /* full definition */ }

// I2C2 — reuses I2C1's RegisterBlock, different base address
pub type I2C2 = crate::Periph<i2c1::RegisterBlock, 0x4000_5800>;
pub use self::i2c1 as i2c2;

// I2C3 — same pattern
pub type I2C3 = crate::Periph<i2c1::RegisterBlock, 0x4000_5c00>;
pub use self::i2c1 as i2c3;
```

The `pub use self::i2c1 as i2c2` re-export means all register types, modules, and field accessors are shared. Only the base address differs.

### Register Module Structure

Each register produces a type alias and a module:

```rust
pub type CR1 = crate::Reg<cr1::CR1rs>;

pub mod cr1 {
    // --- Reader/Writer type aliases ---
    pub type R = crate::R<CR1rs>;       // Only if Readable
    pub type W = crate::W<CR1rs>;       // Only if Writable

    // --- Enumerated values (per field) ---
    #[derive(Clone, Copy, Debug, PartialEq, Eq)]
    pub enum PE { Disabled = 0, Enabled = 1 }
    impl From<PE> for bool { ... }

    // --- Field reader types ---
    pub type PE_R = crate::BitReader<PE>;           // Single-bit with enum
    pub type FREQ_R = crate::FieldReader;           // Multi-bit, raw u8
    pub type FREQ_R = crate::FieldReader<SomeEnum>; // Multi-bit with enum

    // --- Field reader enum methods ---
    impl PE_R {
        pub const fn variant(&self) -> PE { ... }
        pub fn is_disabled(&self) -> bool { ... }
        pub fn is_enabled(&self) -> bool { ... }
    }

    // --- Field writer types ---
    pub type PE_W<'a, REG> = crate::BitWriter<'a, REG, PE>;
    pub type FREQ_W<'a, REG> = crate::FieldWriter<'a, REG, 6>;  // 6-bit field

    // --- Field writer enum methods ---
    impl<'a, REG> PE_W<'a, REG>
    where REG: crate::Writable + crate::RegisterSpec,
    {
        pub fn disabled(self) -> &'a mut crate::W<REG> { self.variant(PE::Disabled) }
        pub fn enabled(self) -> &'a mut crate::W<REG> { self.variant(PE::Enabled) }
    }

    // --- Register reader impl ---
    impl R {
        pub fn pe(&self) -> PE_R {
            PE_R::new((self.bits & 1) != 0)
        }
        pub fn freq(&self) -> FREQ_R {
            FREQ_R::new((self.bits & 0x3f) as u8)
        }
        // ... one accessor per readable field
    }

    // --- Debug impl for R ---
    impl core::fmt::Debug for R {
        fn fmt(&self, f: &mut core::fmt::Formatter) -> core::fmt::Result {
            f.debug_struct("CR1")
                .field("pe", &self.pe())
                .field("freq", &self.freq())
                // ...
                .finish()
        }
    }

    // --- Register writer impl ---
    impl W {
        pub fn pe(&mut self) -> PE_W<'_, CR1rs> { PE_W::new(self, 0) }
        pub fn freq(&mut self) -> FREQ_W<'_, CR1rs> { FREQ_W::new(self, 0) }
        // ... one accessor per writable field (second arg = bit offset)
    }

    // --- Register spec + trait impls ---
    pub struct CR1rs;

    impl crate::RegisterSpec for CR1rs {
        type Ux = u16;                  // Register width
    }

    impl crate::Readable for CR1rs {}  // Present if register is readable

    impl crate::Writable for CR1rs {   // Present if register is writable
        type Safety = crate::Unsafe;   // Or Safe, Range<MIN,MAX>, etc.
        // Only present if non-zero:
        const ZERO_TO_MODIFY_FIELDS_BITMAP: u16 = 0x...;
        const ONE_TO_MODIFY_FIELDS_BITMAP: u16 = 0x...;
    }

    impl crate::Resettable for CR1rs { // Present if reset value is known
        // Only present if non-zero:
        const RESET_VALUE: u16 = 0x...;
    }
}
```

### Register Variants by Access Type

The traits implemented on the register spec struct determine which operations are available:

| Access | Type Alias | Has R? | Has W? | Traits | Available Methods |
|--------|-----------|--------|--------|--------|-------------------|
| Read-Write | `Reg<XYZrs>` | Yes | Yes | Readable + Writable + Resettable | `read()`, `write()`, `modify()`, `reset()` |
| Read-Only | `Reg<XYZrs>` | Yes | No | Readable + Resettable | `read()` only |
| Write-Only | `Reg<XYZrs>` | No | Yes | Writable + Resettable | `write()`, `write_with_zero()`, `reset()` |

Write-only registers get a special `Debug` impl:

```rust
impl core::fmt::Debug for crate::generic::Reg<KRrs> {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(f, "(not readable)")
    }
}
```

### Field Type Selection

svd2rust selects the field proxy type based on field width and semantics:

| Width | Modified Write Values | Reader Type | Writer Type |
|-------|----------------------|-------------|-------------|
| 1 bit | normal (set/clear) | `BitReader<FI>` | `BitWriter<'a, REG, FI>` |
| 1 bit | write-1-to-clear | `BitReader<FI>` | `BitWriter1C<'a, REG, FI>` |
| 1 bit | write-0-to-set | `BitReader<FI>` | `BitWriter0S<'a, REG, FI>` |
| 1 bit | write-1-to-toggle | `BitReader<FI>` | `BitWriter1T<'a, REG, FI>` |
| N bits | any | `FieldReader<FI>` | `FieldWriter<'a, REG, N, FI, Safety>` |

The `FI` type parameter is `bool` (or `u8`/`u16`) for raw fields, or an enum type for fields with `enumeratedValues` in the SVD.

The `Safety` on `FieldWriter` is determined by:
1. If the field's `writeConstraint` covers the full range → `Safe`
2. If the field is 1 bit wide (no explicit constraint) → `Safe`
3. If enumerated values cover all possible values → `Safe`
4. If `writeConstraint` specifies a range → `Range<MIN, MAX>` (or `RangeFrom`/`RangeTo`)
5. Otherwise → `Unsafe`

### Peripherals Struct — Singleton Access

```rust
static mut DEVICE_PERIPHERALS: bool = false;

pub struct Peripherals {
    pub I2C1: I2C1,
    pub I2C2: I2C2,
    pub SPI1: SPI1,
    // ... all peripherals
}

impl Peripherals {
    /// Returns all peripherals *once*. Returns None on subsequent calls.
    #[cfg(feature = "critical-section")]
    pub fn take() -> Option<Self> {
        critical_section::with(|_| {
            if unsafe { DEVICE_PERIPHERALS } { return None; }
            Some(unsafe { Peripherals::steal() })
        })
    }

    /// Unchecked access. Each peripheral must be used at most once.
    pub unsafe fn steal() -> Self {
        DEVICE_PERIPHERALS = true;
        Peripherals {
            I2C1: I2C1::steal(),
            I2C2: I2C2::steal(),
            SPI1: SPI1::steal(),
            // ...
        }
    }
}
```

`take()` uses `critical-section` to guarantee that peripherals are handed out exactly once. `steal()` is the escape hatch for cases where the singleton pattern doesn't apply (e.g., splitting peripherals across tasks in an RTOS).

## Usage Patterns

### Reading a Register

```rust
let dp = stm32f405::Peripherals::take().unwrap();
let i2c1 = &dp.I2C1;

// Read CR1 and inspect fields
let cr1 = i2c1.cr1().read();
if cr1.pe().is_enabled() {
    // peripheral is enabled
}
let is_stopped = cr1.stop().bit_is_set();
```

### Writing a Register

```rust
// Write from reset value — unmentioned fields get reset defaults
i2c1.cr2().write(|w| unsafe { w.freq().bits(8) });

// Write with enum variants (safe, no unsafe needed)
i2c1.cr1().write(|w| w.pe().enabled().smbus().i2c());
```

### Read-Modify-Write

```rust
// Read current value, modify specific fields, write back
i2c1.cr1().modify(|_, w| w.pe().enabled());

// Use the read value to make decisions
i2c1.cr1().modify(|r, w| {
    if r.pe().is_disabled() {
        w.pe().enabled()
    } else {
        w
    }
});
```

### Chaining Field Writes

```rust
i2c1.cr1().modify(|_, w| {
    w.pe().enabled()
     .ack().set_bit()
     .start().set_bit()
});
```

Each field writer returns `&mut W`, enabling fluent chaining.

## svd2rust Configuration

svd2rust is configured via `svd2rust.toml` (TOML) and/or CLI flags:

```toml
# svd2rust.toml
target = "cortex-m"
atomics = false
impl_debug = true
impl_debug_feature = "debug"
impl_defmt = "defmt"
generic_mod = true              # Write generic.rs as separate file
make_mod = false                # Generate lib.rs (true) or mod.rs (false)
field_names_for_enums = false   # Use field names for enum type names

[ident_formats]                 # Customize identifier formatting
field_reader = { case = "pascal", suffix = "R" }
field_writer = { case = "pascal", suffix = "W" }
```

The `ident_formats_theme` option switches between `"legacy"` (SCREAMING_CASE) and default (PascalCase) naming conventions for generated types.

A separate YAML settings file (`--settings`) can provide:
- `html_url`: Base URL for linking to register documentation
- `crate_path`: Custom crate path prefix
- `riscv_config`: RISC-V-specific interrupt/PLIC/CLINT configuration
