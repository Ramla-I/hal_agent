# Claude triage — HAL witness-gate true-bug list

**Scope:** every witness gate that fired when the injected-constraint PACs were
compiled against the HAL crates, across **both** verdict piles — the *unchecked*
candidates and the *corroborated* gates (the static scan's value-blind auto-clear).
~450 distinct HAL gate-sites triaged. Generated 2026-09-22.

These are **candidate** verdicts from source+datasheet analysis, for you to
confirm. Nothing here is written into the ledger's `tp_fp` column — mark those
yourself (e.g. via `review.py`).

- **Confirmed true bugs: 12** (7 from the unchecked pile, 5 from the corroborated pile)
- **Unsure (unguarded API / conditional): 8**
- **Bonus (off our precondition axis): 2** — one wrong injected constraint, one copy-paste code bug

**Links:** each bug points to the `bug_review/` CSV(s) its site appears in.
Corroborated gates are now included in the ledger too, tagged
`static_verdict=corroborated` (a site fires on several devices, so it can appear
in several family CSVs).

---

## Summary table

| # | HAL | Site | Bug | Pass | Present in |
|---|-----|------|-----|------|-----------|
| 1 | stm32g4xx-hal | `rcc/mod.rs:459` | LSE enabled without DBP unlock (MCO path) | unchecked | [stm32g4/rm0440.csv](stm32g4/rm0440.csv) |
| 2 | stm32l0xx-hal | `adc.rs:259` | ADC_CFGR1 written while ADEN=1 | unchecked | [stm32l0/rm0376.csv](stm32l0/rm0376.csv), [stm32l0/rm0377.csv](stm32l0/rm0377.csv) |
| 3 | stm32f4xx-hal | `rcc/f4/mod.rs:641` | DCKCFGR I2S-mux written while PLLs on (f412) | unchecked | [stm32f4/rm0402.csv](stm32f4/rm0402.csv) |
| 4 | stm32-hal2 | `clocks/baseline.rs:880` | DCRST=1 while D-cache enabled | unchecked | [stm32g4/rm0440.csv](stm32g4/rm0440.csv), [stm32l4/rm0351.csv](stm32l4/rm0351.csv), [stm32l4/rm0394.csv](stm32l4/rm0394.csv), [stm32wl/rm0461.csv](stm32wl/rm0461.csv) |
| 5 | stm32-hal2 | `clocks/baseline.rs:881` | ICRST=1 while I-cache enabled | unchecked | [stm32c0/rm0490.csv](stm32c0/rm0490.csv), [stm32g0/rm0454.csv](stm32g0/rm0454.csv), [stm32l4/rm0351.csv](stm32l4/rm0351.csv), [stm32l4/rm0394.csv](stm32l4/rm0394.csv), [stm32wb/rm0434.csv](stm32wb/rm0434.csv), [stm32wl/rm0461.csv](stm32wl/rm0461.csv) |
| 6 | stm32-hal2 | `clocks/baseline.rs:1016` | LSE enabled without DBP unlock (G0 setup) | unchecked | [stm32g0/rm0444.csv](stm32g0/rm0444.csv) |
| 7 | stm32-hal2 | `clocks/baseline.rs:1452` | LSE enabled without DBP unlock (G0 reselect) | unchecked | [stm32g0/rm0444.csv](stm32g0/rm0444.csv) |
| 8 | stm32-hal2 | `clocks/baseline.rs:1053` | HSEBYPPWR written after HSEON=1 | corroborated | [stm32wl/rm0461.csv](stm32wl/rm0461.csv) |
| 9 | stm32-hal2 | `clocks/baseline.rs:1055` | HSEBYP written after HSEON=1 | corroborated | [stm32g0/rm0454.csv](stm32g0/rm0454.csv), [stm32g4/rm0440.csv](stm32g4/rm0440.csv) |
| 10 | stm32-hal2 | `clocks/f.rs:494` | HSEBYP written after HSEON=1 | corroborated | [stm32f3/rm0313.csv](stm32f3/rm0313.csv), [stm32f3/rm0316.csv](stm32f3/rm0316.csv), [stm32f4/rm0401.csv](stm32f4/rm0401.csv) |
| 11 | stm32-hal2 | `usart.rs:265` | IREN=1 while UE=1 (IrDA config after enable) | corroborated | [stm32f4/rm0090.csv](stm32f4/rm0090.csv), [stm32f4/rm0390.csv](stm32f4/rm0390.csv), [stm32f4/rm0430.csv](stm32f4/rm0430.csv) |
| 12 | stm32-hal2 | `usart.rs:263` | HDSEL written while UE=1 (same block) | corroborated | [stm32f4/rm0386.csv](stm32f4/rm0386.csv) |

Per-HAL: **stm32-hal2 = 9**, stm32f4xx-hal = 1, stm32l0xx-hal = 1, stm32g4xx-hal = 1.
Clean (0 bugs): stm32f1xx-hal, stm32f0xx-hal, stm32f1-hal, stm32l0x1-hal.

To find a corroborated row in `review.py`, its `static_verdict` field reads
`corroborated` (unchecked candidates read `unchecked`).

---

## Theme 1 — writes `RCC_BDCR` (LSE) without unlocking the backup domain

`PWR_CR1.DBP` must be 1 before any `RCC_BDCR` bit can change; otherwise the write
is **silently rejected by hardware and LSE never starts**.

### Bug 1 — stm32g4xx-hal `rcc/mod.rs:459` `enable_lse`
- **Rule (RM0440):** BDCR bits are backup-domain write-protected until `DBP=1`.
- **Code:** `DBP` is set in exactly one place, `unlock_rtc()`. `enable_lse` has two
  callers: `lsco()` calls `unlock_rtc()` first (safe), but **`mco(MCOSrc::LSE)`
  calls `enable_lse` directly with no unlock on the path** → `LSEON`/`LSEBYP`
  written with `DBP=0`.
- **Reachable:** `pin.mco(MCOSrc::LSE, …)`. **Impact:** LSE never starts; MCO outputs nothing.
- **Present in:** [stm32g4/rm0440.csv](stm32g4/rm0440.csv)

### Bug 6 — stm32-hal2 `clocks/baseline.rs:1016` `setup`
- **Rule (RM0444, G0):** same DBP requirement for `RCC_BDCR.LSEON`.
- **Code:** on the G0 `InputSrc::Lse` path `bdcr().modify(lseon=1)` runs; a grep shows
  `dbp` is set only in `rtc.rs`, never in the clocks path or a predecessor of `setup`.
- **Impact:** LSE never enables unless the app independently set DBP (undocumented).
- **Present in:** [stm32g0/rm0444.csv](stm32g0/rm0444.csv)

### Bug 7 — stm32-hal2 `clocks/baseline.rs:1452` `reselect_input`
- Same G0 LSE-without-DBP write on the input-reselect path.
- **Present in:** [stm32g0/rm0444.csv](stm32g0/rm0444.csv)

---

## Theme 2 — configures / resets a block while it is enabled

The datasheet requires the block disabled for these writes; the HAL does them
after enabling → the write is ignored or takes effect at an illegal time.

### Bug 11 — stm32-hal2 `usart.rs:265` `new` — **the strong one (hubris shape)**
- **Rule (RM0091 CR3 bit1):** *"IREN … can only be written when the USART is disabled (UE=0)."*
- **Code:** `Usart::new()` calls `enable()` (UE=1, polled) at line 233, then — when
  `config.irda_mode != None` — writes the IrDA config into CR3 (`IREN=1`) at 247–266,
  i.e. **UE=0-gated bits written with UE=1**.
- **Slipped corroboration because** the injected quote here was the half-duplex
  *value-relation* (keep IREN/SCEN cleared), which the code satisfies — value-blind
  to IREN itself being written post-enable.
- **Reachable:** any `IrdaMode::Normal`/`LowPower`. **Impact:** IrDA mode misconfigured.
- **Present in:** [stm32f4/rm0090.csv](stm32f4/rm0090.csv), [stm32f4/rm0390.csv](stm32f4/rm0390.csv), [stm32f4/rm0430.csv](stm32f4/rm0430.csv) (corroborated)

### Bug 12 — stm32-hal2 `usart.rs:263` `new`
- Same IrDA `cr3().modify()` after `enable()`, writing `HDSEL` (also UE=0-gated) with UE=1.
  The written value is 0 (=reset) so the effect is benign; the harmful payload is IREN at :265.
- **Present in:** [stm32f4/rm0386.csv](stm32f4/rm0386.csv) (corroborated)

### Bug 2 — stm32l0xx-hal `adc.rs:259` `configure`
- **Rule (RM0376/RM0377):** *"software is allowed to program ADC_CFGR1 only when ADEN is cleared."*
- **Code:** `configure()` (RES/CONT/ALIGN/DMACFG/DMAEN/EXTSEL/EXTEN) is called only from
  `read()`/`start()`, and **both call `power_up()` immediately before** (ADEN=1, waits ADRDY)
  → CFGR1 configured after the ADC is enabled, on every reachable path.
- **Present in:** [stm32l0/rm0376.csv](stm32l0/rm0376.csv), [stm32l0/rm0377.csv](stm32l0/rm0377.csv)

### Bug 4 — stm32-hal2 `clocks/baseline.rs:880` `setup`
- **Rule:** `DCRST` (data-cache reset) writable only when D-cache disabled (DCEN=0).
- **Code:** the first `flash.acr().modify(...)` in `setup()` sets `DCRST=1` while the cache
  is enabled out of reset (ACR reset has DCEN=1; the HAL's own comment confirms "enabled by
  default"). → cache reset silently ignored.
- **Present in:** [stm32g4/rm0440.csv](stm32g4/rm0440.csv), [stm32l4/rm0351.csv](stm32l4/rm0351.csv), [stm32l4/rm0394.csv](stm32l4/rm0394.csv), [stm32wl/rm0461.csv](stm32wl/rm0461.csv)

### Bug 5 — stm32-hal2 `clocks/baseline.rs:881` `setup`
- Same, `ICRST=1` while I-cache enabled (ICEN=1 at reset).
- **Present in:** [stm32c0/rm0490.csv](stm32c0/rm0490.csv), [stm32g0/rm0454.csv](stm32g0/rm0454.csv), [stm32l4/rm0351.csv](stm32l4/rm0351.csv), [stm32l4/rm0394.csv](stm32l4/rm0394.csv), [stm32wb/rm0434.csv](stm32wb/rm0434.csv), [stm32wl/rm0461.csv](stm32wl/rm0461.csv)

### Bug 8 — stm32-hal2 `clocks/baseline.rs:1053` `setup`
- **Rule:** `HSEBYPPWR` writable only while HSE disabled (HSEON=HSERDY=0).
- **Code:** on the HSE / PLL-from-HSE path, `hseon=1`+HSERDY-wait run at 953/987, then
  HSEBYPPWR is written at 1047–1056 → written with HSE running.
- **Impact (honest):** limited — writing the bypass value while HSE runs is a no-op, and a
  genuine `hse_bypass=true` config would fail HSERDY earlier. But it's a real ordering violation.
- **Present in:** [stm32wl/rm0461.csv](stm32wl/rm0461.csv) (corroborated; also fires on other devices)

### Bug 9 — stm32-hal2 `clocks/baseline.rs:1055` `setup`
- Same block, `HSEBYP` written after `HSEON=1`.
- **Present in:** [stm32g0/rm0454.csv](stm32g0/rm0454.csv), [stm32g4/rm0440.csv](stm32g4/rm0440.csv) (corroborated)

### Bug 10 — stm32-hal2 `clocks/f.rs:494` `setup`
- Same root cause in the F-series clock path: `hseon=1`+HSERDY-wait at 457/475, then
  unconditional `w.hsebyp(self.hse_bypass)` at 492–495.
- **Present in:** [stm32f3/rm0313.csv](stm32f3/rm0313.csv), [stm32f3/rm0316.csv](stm32f3/rm0316.csv), [stm32f4/rm0401.csv](stm32f4/rm0401.csv) (corroborated)

### Bug 3 — stm32f4xx-hal `rcc/f4/mod.rs:641` `config_clocksel` (f412)
- **Rule (RM0402):** `DCKCFGR.I2S1SRC/I2S2SRC` (bits 26:25 / 28:27) writable only while
  PLL and PLLI2S disabled.
- **Code:** `freeze_internal` sets `PLLON` (:442) and `PLLI2SON` (:467), both ready-polled,
  then calls `config_clocksel` (:484) which writes the I2S mux → both PLLs live.
- **Impact (honest):** softest of the 12 — datasheet says "should", and it runs at init before
  any I2S consumer, so likely benign. Still a clear deviation. Runs on every `freeze()`.
- **Present in:** [stm32f4/rm0402.csv](stm32f4/rm0402.csv)

---

## Unsure (8) — unguarded public API / config-dependent; real only on specific call orderings

| # | HAL | Site | Concern | Present in |
|---|-----|------|---------|-----------|
| U1 | stm32-hal2 | `usart.rs:284` `set_baud` | clears UE without waiting TC=1 (can truncate last TX frame) | [stm32f4/rm0401.csv](stm32f4/rm0401.csv) |
| U2 | stm32-hal2 | `usart.rs:345` `disable` | clears UE without waiting TC=1; `write()` also doesn't wait TC | [stm32f4/rm0401.csv](stm32f4/rm0401.csv) |
| U3 | stm32-hal2 | `lpuart.rs:248` `write_one` | TDR write with no TXE guard (non-blocking path) | [stm32h7/rm0433.csv](stm32h7/rm0433.csv) |
| U4 | stm32-hal2 | `timer.rs:1372` `set_alignment` | writes CR1.CMS with no CEN=0 guard (post-`enable()` misuse) | [stm32f3/rm0365.csv](stm32f3/rm0365.csv), [stm32f4/rm0430.csv](stm32f4/rm0430.csv), [stm32g4/rm0440.csv](stm32g4/rm0440.csv), [stm32h7/rm0399.csv](stm32h7/rm0399.csv), [stm32h7/rm0433.csv](stm32h7/rm0433.csv), [stm32l4/rm0394.csv](stm32l4/rm0394.csv) |
| U5 | stm32-hal2 | `adc.rs:1079` `read_result` | clears PCSEL; in continuous mode ADSTART stays set → hits active conversion | [stm32h7/rm0399.csv](stm32h7/rm0399.csv), [stm32h7/rm0433.csv](stm32h7/rm0433.csv) |
| U6 | stm32-hal2 | `adc.rs:1139` `set_trigger` | writes CFGR EXTEN/EXTSEL with no stop guard (sibling `set_sample_time` stops first) | [stm32f3/rm0316.csv](stm32f3/rm0316.csv), [stm32g4/rm0440.csv](stm32g4/rm0440.csv), [stm32h7/rm0433.csv](stm32h7/rm0433.csv), [stm32h7/rm0468.csv](stm32h7/rm0468.csv), [stm32l4/rm0351.csv](stm32l4/rm0351.csv), [stm32l4/rm0394.csv](stm32l4/rm0394.csv), [stm32l5/rm0438.csv](stm32l5/rm0438.csv) |
| U7 | stm32-hal2 | `adc.rs:1299` `enable_interrupt` | writes IER.JQOVFIE with no JADSTART=0 guard | [stm32h7/rm0433.csv](stm32h7/rm0433.csv), [stm32h7/rm0468.csv](stm32h7/rm0468.csv) |
| U8 | stm32l0x1-hal | `adc.rs:424` `start` | sets ADSTART while ADEN=0 (HAL never enables ADC); needs RM0377 AUTOFF-semantics check | [stm32l0/rm0377.csv](stm32l0/rm0377.csv) |

---

## Bonus findings (surfaced during triage, off the precondition axis)

- **Wrong injected constraint** — stm32-hal2 `adc.rs:766/771` `inject_calibration`: the injected
  quote says CALFACT needs ADEN=0, but RM0490 actually requires **ADEN=1 and ADSTART=0**; the
  code is correct — **the ground-truth constraint is wrong**. (corroborated; a concrete
  "constraints not human-checked" case.)
- **Copy-paste code bug** — stm32-hal2 `flash/trustzone.rs:229`: Secure `erase_page` clears
  `NSPER` on `nscr()` instead of `SECPER` on `seccr()`. Real bug, but not a precondition violation
  (BSY is correctly clear); our gate happened to point at the line. (corroborated)

---

## Method note

The 5 corroborated TPs (8–12) were **auto-cleared by the pipeline** because the precondition
field is *referenced* nearby — but value-blind corroboration missed that it is set in the
**wrong order** (the hubris UE/BRR shape). The ledger now carries the corroborated gates too
(tagged `static_verdict=corroborated`) so they can be reviewed; before this change they lived
only in the raw triage JSONLs. Any headline "bug" count resting only on the unchecked pile
undercounts by these 5 (a ~2.5% false-negative rate for the static auto-clear on these HALs).
