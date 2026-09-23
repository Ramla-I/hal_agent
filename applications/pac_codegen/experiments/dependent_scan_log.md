# Dependent-scan log — HAL bug blast radius into real crates

**Purpose.** The witness-gate bugs live in the HALs. This log records every
downstream *dependent* we tried to compile against the injected PACs, to measure
**blast radius** — how many gated HAL sites a real crate's build actually
compiles. (No new bugs are expected in dependents: generic `embedded-hal`
consumers add no register access of their own. See
`docs`/memory `dev-dep-census-is-citation`.)

**Two methods.**
- *Bare probe* (`dependent_compile.py`): a crate that depends on the dependent,
  PAC `[patch]`ed to an injected copy. Instantiates no generics → a **floor**.
- *Example/firmware build* (`scratchpad/build_dep_examples.py`, `build_hrtim.py`):
  builds the dependent's own examples/bins → instantiates the HAL → a **ceiling**.

**Two hard gotchas (both cost real time — check them):**
1. **`patch_applied` guard is mandatory.** cargo only *warns* on an unused
   `[patch]` (`"patch … was not used in the crate graph"`), then silently builds
   against the pristine PAC → **a false 0 that looks clean**. Always confirm the
   lock resolves the patched *path* and that no unused-patch warning appears.
2. **stm32f4xx-hal 0.22.x uses `stm32f4-staging` (aliased `stm32f4`); 0.23.x uses
   real `stm32f4`.** A `[patch] stm32f4` applies for 0.23 but is a no-op for 0.22.
   To measure a 0.22 crate: patch `stm32f4-staging`, or bump the dep to 0.23.

---

## Trustworthy measurements (patch confirmed applied, injected PAC)

| Dependent | Downloads | HAL (via) | Device / RM | Dep kind | Method | Blast radius (gates) | Notes |
|---|---|---|---|---|---|---|---|
| semtech_radios | 2,769 | stm32-hal2 2.1 | g474 / RM0440 | normal | bare probe | **221** (122 candidate + 99 corroborated) | runtime dep — ships it |
| stm32f469i-disc | 2,851 | stm32f4xx-hal 0.23 | f469 / RM0386 | normal (BSP) | probe = examples | **42** (34 + 8) | floor==ceiling (BSP) |
| dht11-driver | 95 | stm32f4xx-hal 0.23 | f407 / RM0090 | dev | examples | **16** (11 + 5) | |
| embassy-stm32 | (very high) | stm32-hrtim 0.2 | g474 / RM0440 | normal (opt HRTIM) | bare probe | **0** floor | see hrtim note below |

Trustworthy blast radius total: **279 gate-site firings across 3 real projects**
(221 + 42 + 16), plus embassy as a confirmed floor-0 consumer.

## Attempted but NOT a valid measurement

| Dependent | Downloads | HAL (via) | Disposition |
|---|---|---|---|
| adafruit-seesaw | 33,062 | stm32f4xx-hal **0.22** | ❌ UNMEASURED — 0.22 pulls `stm32f4-staging`; `stm32f4` patch unused → pristine PAC → false 0. Recover by patching staging or bumping to 0.23. |
| f4-w25q | 1,957 | stm32f4xx-hal **0.22** | ❌ same false-0 (device f412 — the one f4xx TP chip, worth recovering) |
| m24c64-driver | 1,880 | stm32f4xx-hal 0.22 | ❌ dependency resolution failure |
| hsm-rs | 29 | stm32f4xx-hal 0.23 (optional) | ⚠️ HAL dep is example-only/optional → library is HAL-free; 0 = "no HAL compiled", not blast radius |
| embedded-battery-pack | 50 | multi-HAL workspace | ❌ auto-detect didn't isolate the f4 crate |
| rlvgl-bsps-stm | 729 | multi-HAL workspace | ❌ same |
| hopter | 7,859 | stm32f4xx/f0xx-hal (dev) | ❌ needs custom `segstk-rust` toolchain (build-from-source). Source-scan only: `cpu_load` TIM5 raw write = FP (writes CEN/URS not CMS, disables counter first); kernel uses `cortex-m` core peripherals = outside any STM32 RM. No bug. |

## HRTIM / embassy — actual firmware fired, but spurious

Building `stm32-hrtim`'s own g474 examples (real HRTIM firmware) against the
injected `stm32g4` fired **11 gates** (`CPT1CR`/`SET1R`/`RST1R`/`ICR`/`DIER`/`RSTR`
in `stm32-hrtim` src) — vs the embassy bare-probe floor of 0. **Triage: all 11 are
FALSE POSITIVES (tooling artifacts):**
- rm0440 extracted **no HRTIM timer constraints** (only `common_adc2r`); the
  injection plan gated **zero** hrtim registers; the concrete specs keep their
  `Unconstrained*` markers (ungated).
- The firings are on **generic associated-type projections**
  (`<<TIM as Instance>::RB as TimExt>::CPT1CRrs`) — the witness bound can't be
  proven for the generic associated type though every concrete instantiation
  satisfies it. This is the known stm32-hrtim "generic-friction" pattern.

So **embassy/hrtim real datasheet-backed blast radius = 0.** Separately this is a
**coverage gap** (HRTIM is essentially unconstrained in our extraction), not a
clean bill of health — measuring HRTIM correctness needs its constraints extracted.

## Census (2026-09)

`scratchpad/census_pins.py` scanned reverse-deps of the injected HALs: **98
reverse-deps, 18 flagged compatible-generation** — but with false matches to
correct for: `stm32g4xx-hal ^0.0.1` ≠ injected 0.1; `stm32f0xx-hal ^0.18` /
`stm32l0xx-hal ^0.10` are the *released* PAC generation (stm32f0/l0 0.15), not our
ported-to-0.16. Genuinely buildable = the **stm32f4xx-hal 0.23** and
**stm32-hal2 2.1** crates above.

## To extend

- Recover the 0.22 crates: patch `stm32f4-staging` (vendor+inject a staging PAC)
  or bump the dep to 0.23; re-run with the `patch_applied` guard.
- More 0.23 f4 dependents build directly. stm32-hal2 dependents beyond semtech:
  only `steami-rs` (pins hal2 1.8 = old gen).
- Reproduce (committed): `dependent_compile.py --work DIR` (bare-probe floor) and
  `dependent_compile.py --work DIR --examples [--only NAME]` (example/firmware
  ceiling). Both bake in the `patch_applied` guard — an unused patch reports
  UNMEASURED, never a false 0. `EXAMPLE_TARGETS` = dht11-driver, stm32f469i-disc,
  stm32-hrtim; `DEPENDENTS` (bare probe) = stm32f469i-disc, semtech_radios,
  embassy-stm32. Verified: `--examples --only dht11-driver` → 16 gates (11+5).
