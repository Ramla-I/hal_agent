# Adopting the constrained crate: what it actually costs a HAL

Until the HAL compiles, nothing downstream of it is type-checked, so the
enforcement never reaches the application developer
([`hopter.md`](hopter.md)). This is the experiment that performs the adoption
a HAL maintainer would eventually perform — mechanically, on
**stm32f4xx-hal 0.23.0** against **RM0383 / stm32f411** (14 registers gated) —
and records what it took.

Run it with `applications/pac_codegen/experiments/hal_probe/check.py
--apply-fix`; `patch_hal.py` did this first and was retired, because its
results carried no triage — every site it rewrote was recorded as a
`hal_constraint_violation`, and on stm32f4xx-hal all seven of those were sites
the driver already guarded.

---

## Headline: 31 places where a widely-used driver writes a constrained
## register without establishing the precondition

These are the *payoff*, not the cost. Each is a concrete register the manual
says has a precondition, written by the HAL with nothing establishing it:

| count | file | register | operation |
|---|---|---|---|
| 8 | `src/spi.rs` | `CR1` | modify |
| 2 | `src/spi.rs` | `CR1` | write |
| 4 | `src/flash.rs` | `CR` | modify |
| 4 | `src/rtc.rs` | `DR` | modify |
| 2 | `src/rtc.rs` | `DR` | write |
| 3 | `src/rtc.rs` | `TR` | modify |
| 1 | `src/rtc.rs` | `TR` | write |
| 3 | `src/rtc.rs` | `WUTR` | write |
| 3 | `src/i2c.rs` | `CCR` | write |
| 1 | `src/i2c.rs` | `TRISE` | write |

Whether each is a live bug needs a human reading the datasheet clause against
the surrounding code — some will be preceded by a check the type system cannot
see. But this is the list a maintainer would triage, produced automatically
from the manual, in a driver used by a large fraction of the STM32 Rust
ecosystem. **That is the value proposition.**

The SPI `CR1` cluster is the most interesting: the manual's rule is *"this bit
should be written only when SPI is disabled (SPE = 0)"*, and ten separate call
sites modify or write that register.

---

## The cost side: mechanical adoption does NOT converge

The patcher fixes each error class the way a maintainer would — declare the
bound where rustc suggests it, add the imports rustc names, widen the trait
declaration when an impl may not be stricter than its trait — and iterates:

| round | true enforcement | generic friction | other |
|---|---|---|---|
| 1 | 32 | 8 | 0 |
| 2 | 1 | 9 | 0 |
| 3 | 1 | 6 | 3 |
| 4 | 1 | 3 | 9 |
| 5 | 1 | 11 | 12 |
| 6 | **0** | **0** | **20** |

Friction and enforcement both reach zero. **The build still fails**, with a
tail of 11 × `E0276` and 9 × `E0425` that the machine cannot clear.

### Why it stalls, and why that matters

`E0276: impl has stricter requirements than trait`. An impl may not demand
more than the trait it implements, so a bound added at an impl must also be
added to the **trait declaration** — which changes that trait's public
contract and obliges *every other implementor*. rustc offers no
machine-applicable fix for that step; it only points at the trait method.

The patcher does widen traits (9 widenings across the run), but each widening
ripples: methods like `handle_dma_interrupt(&mut self)` — declared with no
bounds at all, implemented for concrete DMA/serial combinations — acquire a
requirement that then has to be threaded through their own callers.

**Superseded — see [`generic_friction.md`](generic_friction.md) §5.** Putting
the bound on the trait's *associated type* rather than on each method clears
all friction in **4 one-line edits with no cascade at all**. The costs below
are what happens when rustc's per-method suggestions are applied verbatim,
which is the wrong place for the bound. The 31 constraint violations above are
unaffected — they are true enforcement, not friction.

**This corrected an earlier estimate.** Applying rustc's suggestions to a leaf
crate converged in 42–57 edits, which made "declare the bound" look purely
mechanical. On the full HAL it is not: the bounds reach trait definitions, and
from there the change is **semver-breaking and requires human judgement about
what each trait should promise**. The honest cost of Option A is *"a
maintainer-led API revision"*, not *"a compiler-assisted patch"*.

That strengthens the case for Option B (write the register access concretely,
as `stm32-hal2` does) — it needs no trait contract changes at all, because
there are no placeholder types to bound.

---

## What this unblocks, and what it does not

**Unblocked and verified:** Hopter itself builds. Its custom compiler
(`segstk-rust`, a Rust 1.81 fork) is published as a prebuilt release, and with
the dependency graph walked back to versions cargo 1.81 can parse
(`time` 0.3.41 — newer releases require edition 2024), a Hopter example
compiles cleanly on its own toolchain. That baseline is now reproducible.

**Still blocked:** running Hopter *on* the injected crate, because that needs a
HAL that compiles, which the section above shows is a maintainer-led change
rather than an automated one.

**Worth noting about the target anyway:** none of the four F4-family manuals in
the corpus (RM0368, RM0383, RM0386, RM0390) gates a TIM register, and Hopter's
own direct register access is TIM5 (`psc`, `cr1`, `cnt`, `sr`) plus RCC clock
setup. So on today's corpus Hopter's own code has no constraint to violate —
the findings are all in the driver beneath it. A manual that constrains TIM
would change that: RM0008 gates `TIM1/TIM2 CR1` on exactly the pattern Hopter
uses (`cr1.modify(|_, w| w.cen().clear_bit())`).
