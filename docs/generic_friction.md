# Generic friction: what it is, why it happens, and the two ways out

When we inject datasheet constraints into a chip crate, some driver code stops
compiling for a reason that has nothing to do with any constraint. This is the
one real adoption cost of the encoding, and it is worth stating precisely,
because the error message we emit actively misleads about it.

Everything below is measured. The experiments live in
`applications/pac_codegen/experiments/friction.py` (`--only A|B|C`); the
per-manual numbers are in [`injection_tracking.md`](injection_tracking.md).

---

## 1. What the error looks like

```
error[E0277]: `<Self as UartRB>::SRrs` is read-constrained by its datasheet
   --> stm32f4xx-hal-0.23.0/src/serial/uart_impls.rs:11
```

Two things are wrong with reading that at face value:

- **No UART register is constrained** in that run. `SRrs` is not in the
  device's gated set.
- **`<Self as UartRB>::SRrs` is not a register.** It is a *placeholder* — "the
  status register of whichever UART this turns out to be".

The message is our `#[diagnostic::on_unimplemented]` text firing in a context
it was not written for. The true statement is *"I cannot prove this register is
**un**constrained"*, which is a different claim from *"this register is
constrained"*. Rewording it to cover both cases is a small, worthwhile fix.

---

## 2. Why it happens

### The encoding, in one paragraph

`generic.rs` gains a bound on the stock methods:

```rust
pub fn read(&self) -> R<REG> where REG: UnconstrainedRead { … }
```

Every **unconstrained** register gets a one-line `impl UnconstrainedRead for
CRrs {}`. A **constrained** register gets no such impl, so `read()` does not
exist for it and every call site is a compile error naming the datasheet rule.
That is the whole mechanism, and it is why violations are caught at compile
time rather than reviewed by a human.

### Two kinds of call site

**Concrete code — unaffected.** When a driver writes

```rust
dp.RCC.cr().write(|w| …)
```

the compiler knows the type is `stm32f401::rcc::cr::CRrs`, looks for the impl,
and either finds it (compiles exactly as before) or does not (our error, doing
its job). This is the large majority of every driver.

**Generic code — this is the friction.** stm32f4xx-hal abstracts over "any
UART-ish register block":

```rust
pub trait UartRB {
    type SRrs: SrR + SrW;              // "the status register, whatever it is"
    fn sr(&self) -> &Reg<Self::SRrs>;
}

fn read_u16(&self) -> nb::Result<u16, Error> {
    let sr = self.sr().read();          // ← fails here
    …
}
```

`read_u16` is compiled **once** and must be valid for *every* type that could
ever fill `Self::SRrs`. To check `.read()`, the compiler needs
`Self::SRrs: UnconstrainedRead` — and the only facts it may use are the ones
the signature declares, namely `SrR + SrW`. Our marker is not among them, so
it refuses.

The concrete chips *do* carry the marker (`type SRrs = usart1::sr::SRrs;` and
that type is marked). Rust simply will not look: **a generic function is
type-checked once against its declared bounds, never against its
instantiations.** C++ templates check at instantiation and would have accepted
this code unchanged; Rust's choice is deliberate, and this is the price.

### Isolating it to one line

Experiment C compiles the *same body* twice against the *same* injected chip
crate:

| written as | result |
|---|---|
| generic over an associated register type (`Self::SRrs`) | **fails** |
| against the concrete register type (`usart1::sr::SRrs`) | **compiles** |

So friction is a property of the **abstraction**, not of the register, the
datasheet, or the encoding.

---

## 3. Three things it is *not*

**Not proportional to the constraints.** Experiment A installs the encoding
while gating *nothing* — `generic.rs` patched, every register given every
marker, the crate semantically identical to pristine. The friction is
unchanged:

| driver | friction with 0 constraints gated | with the full manual injected |
|---|---|---|
| stm32f4xx-hal 0.23.0 | 14 | 14 |
| stm32f1xx-hal 0.11.0 | 27 | 27 |

It is a **fixed cost of installing the encoding**. The hundredth constraint
costs nothing more than the first — which is good news for scaling, and means
"inject fewer constraints" is not a mitigation.

**Not universal across drivers.** `stm32-hal2` is written as concrete per-chip
code and takes **zero** friction on all five targets it was measured against.
RM0368 gives a controlled comparison — same chip, same manual, same five gated
registers, two drivers:

| rm0368 / stm32f401 | true enforcement | generic friction |
|---|---|---|
| stm32f4xx-hal 0.23.0 | 17 | 8 |
| stm32-hal2 2.1.10 | 9 | **0** |

**Not even universal within a driver.** Inside stm32f4xx-hal, the concrete
modules absorb the gates cleanly — every one of its 17 enforcement hits lands
in `i2c.rs` and `rtc.rs` — while only the generic serial module produces
friction. Same crate, same injection, opposite outcomes by module style.

---

## 4. What we already did about it

The stock methods used to carry the bound for **read, write and modify
unconditionally**. But a bound on an operation that no register gates enforces
nothing — every register carries that marker — while still forcing every
generic signature downstream to name it. Neither RM0008 nor RM0368 gates a
single *read*, yet every one of stm32f4xx-hal's 14 friction errors was
`read-constrained`.

`inject_into_pac` now derives the gated operations from the plans and bounds
only those. It cannot weaken enforcement (an operation with no gate has nothing
to enforce), and the template drift checks still run over every signature:

| | true enforcement | friction before | friction after |
|---|---|---|---|
| rm0368 → stm32f4xx-hal | unchanged | 14 | **8** |
| rm0008 → stm32f1xx-hal | unchanged | 27 | **13** |

Roughly half the friction was being paid for operations we never constrain.
The rest is real: generic code that writes or modifies registers, in a crate
that genuinely gates writes and modifies.

---

## 5. The two ways to remove the remainder

Both are changes to the *driver*, not to us. Rust offers no flag and no codegen
trick that would let the chip crate resolve a bound for an unresolved
associated type.

### Option A — declare the bound

Add what the compiler asks for:

```rust
fn read_u16(&self) -> nb::Result<u16, Error>
where <Self as UartRB>::SRrs: UnconstrainedRead { … }
```

Measured by applying rustc's own machine-applicable suggestions and iterating
(experiment B):

| driver | round 1 | round 2 | round 3 | edits |
|---|---|---|---|---|
| stm32f4xx-hal | 14 | 30 | 0 witness errors | 42 |
| stm32f1xx-hal | 27 | 37 | 0 witness errors | 57 |

It reaches zero, but **the bounds cascade**: every generic function that gains
one forces its generic callers to declare it too, which is why round 2 has more
errors than round 1. Forty-two to fifty-seven edits, spreading into public
signatures.

- **For:** smallest diff; preserves the driver's design; purely additive.
- **Against:** viral — it propagates through the public API, so it is a
  semver-relevant change, and it puts our trait name in their signatures,
  coupling them to us.

### Option B — write the code concretely

Move the trait's default methods into per-instance impls (or a macro that
generates them), so `Self` is concrete and the marker resolves. This is what
`stm32-hal2` does throughout, and why it pays nothing.

- **For:** removes the problem at the root rather than annotating around it; no
  API change; no mention of our traits anywhere; already proven at scale by a
  major HAL.
- **Against:** much larger; asks the maintainers to give up an abstraction they
  chose deliberately (one implementation instead of six); grows code size.

### Why this matters more than the error count suggests

Cargo compiles dependencies first, so a HAL that fails to build takes the
application with it — the application is never type-checked. Measured on a
UART-only probe against an injected stm32f401:

- **0** error locations in the application's own file;
- the first error points into `stm32f4xx-hal-0.23.0/src/i2c.rs`, about
  **I2C timing**, in a program that only opens a UART.

An application talking to the chip crate directly gets the intended
experience — `--> src/lib.rs:5`, naming the rule at the line that breaks it.
But behind a HAL that itself touches a gated register, nobody ever gets there.

So the case for fixing friction upstream is not that 8 errors are many. It is
that **until the HAL compiles, the enforcement is invisible to the developer
it is meant to protect**, and their first contact with it is a failure inside
a crate they did not write.

### Which to propose

Neither is ours to land, and the choice belongs to each driver's maintainers.
If we were opening the PR: **Option A for stm32f1xx-hal and stm32f4xx-hal**,
because it is mechanical, reviewable, and the compiler writes most of it —
with the caveat that it is an API change. Option B is the better end state but
is a refactor we would be asking someone else to accept on our behalf.

The honest framing for the paper: friction is a **one-time, fixed cost paid
only by trait-generic driver code**, it is quantified (8 and 13 errors after
the operation-selective fix, in ~30k-line libraries), it never produces a wrong
program — only a compile error demanding an annotation — and there exist two
concrete remedies, one of which a major HAL already demonstrates at zero cost.

---

## Reproducing

```sh
python applications/pac_codegen/experiments/friction.py            # A, B and C
python applications/pac_codegen/experiments/friction.py --only C   # the one-line isolation
```

Neither experiment touches the committed chip crates; everything runs on
copies.
