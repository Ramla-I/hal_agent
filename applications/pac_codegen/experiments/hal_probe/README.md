# hal_probe — compile any driver against any injected PAC

A four-line crate whose **build is the experiment**. It depends on a driver
normally and swaps the chip crate underneath with `[patch.crates-io]` — exactly
how a downstream user would consume a constrained PAC. The driver is never
modified, so every error is the gate firing rather than an edit of ours.

`stm_sweep.py` does this for all 49 targets at once. Reach for this when you
want **one** pairing, in your hands, to poke at.

## Three things to change

**1. `Cargo.toml` — the driver.** Pin with `=`; use the crate's *own* feature
names (`stm32f4xx-hal` wants `stm32f401`, `stm32-hal2` wants `f401`).

```toml
[dependencies]
stm32f1xx-hal = { version = "=0.11.0", features = ["stm32f103", "medium"] }
```

**2. `Cargo.toml` — the injected PAC.** The name must be what the driver
depends on (`stm32f1`, `stm32f4`, …), and the path must point at a crate that
**has been injected**:

```toml
[patch.crates-io]
stm32f1 = { path = "/tmp/kept/rm0008_stm32f103_stm32f1" }
```

Get one with:

```sh
python applications/pac_codegen/experiments/stm_sweep.py --only rm0008 --keep-pac /tmp/kept
```

Pointing at `vendored/pac/<crate>` measures the **pristine** crate and finds
nothing — the sweep restores it when it finishes.

**3. `src/lib.rs` — the `pub use`.** Crate name with dashes as underscores.

## Run it

```sh
python applications/pac_codegen/experiments/hal_probe/check.py
python applications/pac_codegen/experiments/hal_probe/check.py --errors
```

Use `check.py` rather than bare `cargo check`, for one reason:

> Cargo does **not** fail when a `[patch.crates-io]` cannot be applied. It
> prints a warning and resolves the registry crate — so a probe with a wrong
> crate name or an unsatisfiable version requirement compiles cleanly against
> the PRISTINE PAC and looks like *"zero violations"*.

`check.py` reads `Cargo.lock` and refuses to report anything until the local
path has actually won.

## Reading the result

```
patch applied: stm32f1 <- local path   OK
errors 18   violations 5   generic friction 13   other 0

  VIOLATIONS -- the driver touches a gated register here:
      4x stm32f1::stm32f103::rtc::crh::CRHrs
      1x PRLHrs
      rtc.rs: lines [285, 334, 342, 357, 364]

  GENERIC FRICTION -- 13 error(s) ...
      adc.rs: lines [301, 311, ...]
```

The split is the whole point, and it is not cosmetic:

- **violations** — our diagnostic naming a **concrete** register type. The
  driver touches something the datasheet says is conditional.
- **generic friction** — our diagnostic naming an **associated-type
  projection** (`<<ADC as Ptr>::RB as AdcRB>::CR2rs`). A driver written
  generically over register blocks needs the marker bounds even where nothing
  on this device is gated. That is the encoding's adoption cost, fixed by
  mechanical `where` clauses — counting it as a finding would inflate the
  result. (Above: every ADC hit is friction; stm32f1xx-hal's ADC layer is
  generic, and no ADC register is gated on rm0008.)
- **bound cascade** — `E0276 impl has stricter requirements than trait`. Not
  one of our diagnostics, but an *expected* residue after `--apply-fix`: a
  bound we added landed on a method implementing a trait, and Rust rejects a
  requirement the trait itself does not declare. Neither a finding nor
  collateral — see below.
- **other** — neither ours nor an expected residue. This IS collateral, and
  worth reading.

A violation is a **candidate**, not a proven bug: the driver may establish the
precondition a few lines above. `experiments/corroboration.py` does that triage.

## Removing the friction: `--apply-fix`

```sh
python applications/pac_codegen/experiments/hal_probe/check.py --apply-fix
```

Copies the driver out of the registry cache into `vendored/`, repoints
`Cargo.toml` at the copy, and applies **rustc's own MachineApplicable `where`
bounds** until the friction is gone. The registry cache is never touched — it
is shared by every project on the machine and cargo overwrites it.

Only `MachineApplicable` suggestions are taken. A `MaybeIncorrect` one is rustc
guessing at intent; applying it would make this a rewrite of the driver rather
than the mechanical step it claims to be.

Three repairs are needed on top of what rustc hands you, and all three were
found by running it:

- **same-span merge.** Two errors on one generic item each suggest
  ` where A: Trait` at the *same* byte span. Applied verbatim that is two where
  clauses and `cannot define duplicate where clauses on an item`.
- **name qualification.** rustc emits trait names as they were in scope where
  it *diagnosed*, not where the clause gets written. It suggests bare
  `UnconstrainedModify` (it lives in the PAC) and bare `Ptr` (stm32f1xx-hal
  spells its own trait `crate::Ptr`). Unrepaired, 12 of 13 sites become E0405
  and the run gets *worse* — 18 errors to 25.
- **lift to the impl block.** A bound on a method that implements a trait is
  illegal (`E0276: impl has stricter requirements than trait`). The fix is not
  to widen the trait — that changes the driver's public API. A bound on the
  **impl block** is legal and says the right thing: *this impl applies where
  the register is unconstrained*. So the clause moves up one level, into the
  impl's own `where`, where the impl's generic params are already in scope.

```rust
impl<ADC: Instance, WORD, PIN> OneShot<ADC, WORD, PIN> for Adc<ADC>
where
    WORD: From<u16>,
    PIN: Channel<ADC, ID = u8>,
    <<ADC as crate::Ptr>::RB as AdcRB>::CR2rs: stm32f1::UnconstrainedModify,
{
    fn read(&mut self, _pin: &mut PIN) -> nb::Result<WORD, Self::Error> { … }
```

### What it found, on stm32f1xx-hal 0.11.0 vs rm0008-injected stm32f1

```
18 errors  =  5 violations + 13 generic friction
    ↓  17 bounds added, 4 lifted to an impl block,
       17 names qualified, over 8 rounds
 5 errors  =  5 violations
```

**Converged.** The driver compiles against the injected PAC except exactly
where it genuinely touches a gated register — RTC `CRH` modified four times and
`PRLH` written once, without checking `RTOFF`.

**Every edit is verified to be a bound and nothing else.** After the loop, each
touched file is compared against the pristine copy in the registry cache with
all marker predicates stripped and whitespace collapsed; anything that differs
beyond its bounds fails the run. Without that, *"we only added where clauses"*
is an assurance rather than a checked claim — and a driver we silently reshaped
is a driver whose violations mean nothing. Same discipline as
`port_hal.py --verify`.

### The honest scope of "mechanical"

All 13 friction errors were removable without touching a line of logic, so the
adoption cost for this pairing is 17 one-line annotations a tool can write. But
note where the difficulty sat: not in the bounds themselves, which rustc hands
you, but in the three repairs above. A naive application of rustc's own
machine-applicable suggestions makes the build *worse*. The cost is mechanical;
mechanising it is not free.
