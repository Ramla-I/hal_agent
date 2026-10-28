# Claude triage — HAL witness-gate bug review

**Everything here is a _candidate verdict_, not an adjudication.** The ledger's
`tp_fp` column is yours to fill (e.g. via `review.py`); the **`claude`** column
below is only my confidence hint so you know where to spend effort — `tp` = my
analysis found a concrete violation, `unsure` = I couldn't decide without
runtime/config. **You review every row in §1.** Each links the `bug_review/`
CSV(s) the site appears in (a site can fire on several devices → several family
CSVs). False positives are in §3 — **not** in the review table.

**Scope:** every witness gate that fired when the injected-constraint PACs were
compiled (or statically scanned) against real HAL/firmware — across all three
injection arms (**svd2rust**, **chiptool**, **raltool**) and both ecosystems
(**STM**, **NXP**). ~450 HAL gate-sites triaged, across the *unchecked* and
*corroborated* piles.

## Totals

| pile | count | where |
|---|---|---|
| **Review — likely a bug** (`claude=tp`) | **18** | §1 A–G |
| **Review — unsure** (`claude=unsure`) | **10** | §1 A–G |
| **Review — downstream own-code candidates** (from the port experiments) | **4 crates / 22 sites** — 2 confirmed (hubris), rest unsure/fp | §1 Class H |
| Not a bug (`claude=fp`) | 3 notable (+ the rest) | §3 |

- **By tool** (the 28 HAL-sweep bugs, A–G): svd2rust **26**, chiptool **2** (B1, C1), raltool **0** (arm has no findings yet).
- **By ecosystem** (A–G): STM **25**, NXP **3** (X1, B2 on lpc8xx-hal; N4 on mk20dx-hal).
- Class H (hubris / rustuino / elodin / anne-key) is a separate population — the app's/driver's own code, from the port experiments, not the HAL-sweep CSVs. Source-analysis confirmed 2 real own-code bugs in hubris (H1, H2); the rest are unsure/fp.

---

## 1. Bugs to review

Grouped by failure class; the `claude` column is my confidence. Mark `tp_fp`
yourself on all of them. "caught" = whether compiling a HAL on the injected PAC
fires this as an `E0277` (vs found by manual review).

### Class A — `RCC_BDCR` (LSE) written without unlocking the backup domain
`PWR_CR1.DBP` must be 1 before any `RCC_BDCR` bit changes, or the write is
**silently dropped and LSE never starts**.

| ID | claude | HAL | site | bug (detail §5) | pac | device | tool | caught | CSV |
|---|---|---|---|---|---|---|---|---|---|
| 1 | tp | stm32g4xx-hal | `rcc/mod.rs:459` `enable_lse` | LSE enabled with DBP=0 (MCO path) | stm32g4 | stm32g4a1 | svd2rust | yes | [stm32g4/rm0440.csv](stm32g4/rm0440.csv) |
| 6 | tp | stm32-hal2 | `clocks/baseline.rs:1016` `setup` | LSE enabled with DBP=0 (G0 setup) | stm32g0 | stm32g071 | svd2rust | yes | [stm32g0/rm0444.csv](stm32g0/rm0444.csv) |
| 7 | tp | stm32-hal2 | `clocks/baseline.rs:1452` `reselect_input` | LSE enabled with DBP=0 (G0 reselect) | stm32g0 | stm32g071 | svd2rust | yes | [stm32g0/rm0444.csv](stm32g0/rm0444.csv) |

### Class B — a clock/flash block is reset or bypass-switched while it is live
Datasheet requires the block disabled; the HAL writes after enabling → ignored or illegal-time.

| ID | claude | HAL | site | bug (detail §5) | pac | device | tool | caught | CSV |
|---|---|---|---|---|---|---|---|---|---|
| 4 | tp | stm32-hal2 | `clocks/baseline.rs:880` `setup` | DCRST=1 while D-cache on | stm32g4, stm32l4, stm32wl | stm32g474, stm32g4a1, stm32l412, stm32l4x6, stm32wle5 | svd2rust | yes | [stm32g4/rm0440.csv](stm32g4/rm0440.csv), [stm32l4/rm0351.csv](stm32l4/rm0351.csv), [stm32l4/rm0394.csv](stm32l4/rm0394.csv), [stm32wl/rm0461.csv](stm32wl/rm0461.csv) |
| 5 | tp | stm32-hal2 | `clocks/baseline.rs:881` `setup` | ICRST=1 while I-cache on | stm32c0, stm32g0, stm32l4, stm32wb, stm32wl | stm32c031, stm32g070, stm32l412, stm32l4x6, stm32wb55, stm32wle5 | svd2rust | yes | [stm32c0/rm0490.csv](stm32c0/rm0490.csv), [stm32g0/rm0454.csv](stm32g0/rm0454.csv), [stm32l4/rm0351.csv](stm32l4/rm0351.csv), [stm32l4/rm0394.csv](stm32l4/rm0394.csv), [stm32wb/rm0434.csv](stm32wb/rm0434.csv), [stm32wl/rm0461.csv](stm32wl/rm0461.csv) |
| 8 | tp | stm32-hal2 | `clocks/baseline.rs:1053` `setup` | HSEBYPPWR after HSEON=1 (impact limited) | stm32wl | stm32wle5 | svd2rust | yes (corrob.) | [stm32wl/rm0461.csv](stm32wl/rm0461.csv) |
| 9 | tp | stm32-hal2 | `clocks/baseline.rs:1055` `setup` | HSEBYP after HSEON=1 | stm32g0, stm32g4 | stm32g070, stm32g474, stm32g4a1 | svd2rust | yes (corrob.) | [stm32g0/rm0454.csv](stm32g0/rm0454.csv), [stm32g4/rm0440.csv](stm32g4/rm0440.csv) |
| 10 | tp | stm32-hal2 | `clocks/f.rs:494` `setup` | HSEBYP after HSEON=1 (F-series) | stm32f3, stm32f4 | stm32f303, stm32f373, stm32f410 | svd2rust | yes (corrob.) | [stm32f3/rm0313.csv](stm32f3/rm0313.csv), [stm32f3/rm0316.csv](stm32f3/rm0316.csv), [stm32f4/rm0401.csv](stm32f4/rm0401.csv) |

### Class C — a peripheral is configured/reconfigured after it was enabled
The config bits are `*EN=0`-gated; the HAL writes them with the peripheral already enabled.

| ID | claude | HAL | site | bug (detail §5) | pac | device | tool | caught | CSV |
|---|---|---|---|---|---|---|---|---|---|
| 11 | tp | stm32-hal2 | `usart.rs:265` `new` | IREN written with UE=1 (IrDA after enable; the strong one) | stm32f4 | stm32f413, stm32f429, stm32f446 | svd2rust | yes (corrob.) | [stm32f4/rm0090.csv](stm32f4/rm0090.csv), [stm32f4/rm0390.csv](stm32f4/rm0390.csv), [stm32f4/rm0430.csv](stm32f4/rm0430.csv) |
| 12 | tp | stm32-hal2 | `usart.rs:263` `new` | HDSEL written with UE=1 (benign; IREN at :265 is the payload) | stm32f4 | stm32f469 | svd2rust | yes (corrob.) | [stm32f4/rm0386.csv](stm32f4/rm0386.csv) |
| 2 | tp | stm32l0xx-hal | `adc.rs:259` `configure` | ADC_CFGR1 written after power_up (ADEN=1) | stm32l0 | stm32l0x1, stm32l0x2 | svd2rust | yes | [stm32l0/rm0376.csv](stm32l0/rm0376.csv), [stm32l0/rm0377.csv](stm32l0/rm0377.csv) |
| 3 | tp | stm32f4xx-hal | `rcc/f4/mod.rs:641` `config_clocksel` | DCKCFGR I2S-mux while PLLs on (f412; likely benign) | stm32f4 | stm32f412 | svd2rust | yes | [stm32f4/rm0402.csv](stm32f4/rm0402.csv) |
| B1 | tp | embassy-stm32 | `lptim/timer/mod.rs:65` | LPTIM PRESC written after ENABLE=1 → wrong PWM freq | stm32-metapac | stm32g474 | chiptool | — | [stm32g4/rm0440.csv](stm32g4/rm0440.csv) |
| B2 | tp | lpc8xx-hal | `usart/tx.rs:273` | CFG.CTSEN reconfigured while USART enabled | lpc845-pac | lpc845 | svd2rust | — | [lpc845-pac/lpc845.csv](lpc845-pac/lpc845.csv) |
| X1 | tp | lpc8xx-hal | `i2c/master.rs:98` `read_all` | MSTCTL written without waiting STAT.MSTPENDING | lpc845-pac | lpc845 | svd2rust | yes | [lpc845-pac/lpc845.csv](lpc845-pac/lpc845.csv) |
| C1 | tp | embassy-stm32 | `i2c/v2.rs:1576` `configure_oa1` | OA1EN toggled false→true in one write (fixed in HEAD) | stm32-metapac | stm32g474 | chiptool | — | [stm32g4/rm0440.csv](stm32g4/rm0440.csv) |
| U4 | unsure | stm32-hal2 | `timer.rs:1372` `set_alignment` | CR1.CMS written with no CEN=0 guard | stm32f3, stm32f4, stm32g4, stm32h7, stm32l4 | stm32f302, stm32f413, stm32g474, stm32g4a1, stm32h747cm7, stm32h753, stm32l412 | svd2rust | — | [stm32f3/rm0365.csv](stm32f3/rm0365.csv), [stm32f4/rm0430.csv](stm32f4/rm0430.csv), [stm32g4/rm0440.csv](stm32g4/rm0440.csv), [stm32h7/rm0399.csv](stm32h7/rm0399.csv), [stm32h7/rm0433.csv](stm32h7/rm0433.csv), [stm32l4/rm0394.csv](stm32l4/rm0394.csv) |
| U5 | unsure | stm32-hal2 | `adc.rs:1079` `read_result` | PCSEL cleared during active conversion (continuous) | stm32h7 | stm32h747cm7, stm32h753 | svd2rust | — | [stm32h7/rm0399.csv](stm32h7/rm0399.csv), [stm32h7/rm0433.csv](stm32h7/rm0433.csv) |
| U6 | unsure | stm32-hal2 | `adc.rs:1139` `set_trigger` | CFGR EXTEN/EXTSEL with no stop guard | stm32f3, stm32g4, stm32h7, stm32l4, stm32l5 | stm32f303, stm32g474, stm32g4a1, stm32h735, stm32h753, stm32l412, stm32l4x6, stm32l562 | svd2rust | — | [stm32f3/rm0316.csv](stm32f3/rm0316.csv), [stm32g4/rm0440.csv](stm32g4/rm0440.csv), [stm32h7/rm0433.csv](stm32h7/rm0433.csv), [stm32h7/rm0468.csv](stm32h7/rm0468.csv), [stm32l4/rm0351.csv](stm32l4/rm0351.csv), [stm32l4/rm0394.csv](stm32l4/rm0394.csv), [stm32l5/rm0438.csv](stm32l5/rm0438.csv) |
| U7 | unsure | stm32-hal2 | `adc.rs:1299` `enable_interrupt` | IER.JQOVFIE with no JADSTART=0 guard | stm32h7 | stm32h735, stm32h753 | svd2rust | — | [stm32h7/rm0433.csv](stm32h7/rm0433.csv), [stm32h7/rm0468.csv](stm32h7/rm0468.csv) |
| U8 | unsure | stm32l0x1-hal | `adc.rs:424` `start` | ADSTART set while ADEN=0 | stm32l0 | stm32l0x1 | svd2rust | — | [stm32l0/rm0377.csv](stm32l0/rm0377.csv) |

### Class D — UART disabled / TDR written without waiting for TX to finish
| ID | claude | HAL | site | bug (detail §5) | pac | device | tool | caught | CSV |
|---|---|---|---|---|---|---|---|---|---|
| U1 | unsure | stm32-hal2 | `usart.rs:284` `set_baud` | UE cleared without waiting TC=1 | stm32f4 | stm32f410 | svd2rust | — | [stm32f4/rm0401.csv](stm32f4/rm0401.csv) |
| U2 | unsure | stm32-hal2 | `usart.rs:345` `disable` | UE cleared without waiting TC=1 | stm32f4 | stm32f410 | svd2rust | — | [stm32f4/rm0401.csv](stm32f4/rm0401.csv) |
| U3 | unsure | stm32-hal2 | `lpuart.rs:248` `write_one` | TDR written with no TXE guard | stm32h7 | stm32h753 | svd2rust | — | [stm32h7/rm0433.csv](stm32h7/rm0433.csv) |

### Class E — a handshake / lock sequence is never performed
| ID | claude | HAL | site | bug (detail §5) | pac | device | tool | caught | CSV |
|---|---|---|---|---|---|---|---|---|---|
| N1 | tp | stm32-hal2 | `gpio.rs:909` `cfg_lock` | GPIO config lock is a no-op (no LCKK sequence) | stm32g4 | stm32g474 | svd2rust | yes (B2+B3) | [stm32g4/rm0440.csv](stm32g4/rm0440.csv) |

### Class F — value / divisor rule (not access-control; witness-gate can't see it)
| ID | claude | HAL | site | bug (detail §5) | pac | device | tool | caught | CSV |
|---|---|---|---|---|---|---|---|---|---|
| N2 | tp | stm32-hal2 | `usart.rs:299` `set_baud` | OVER8 baud miscomputed (raw divisor, BRR[3] not cleared) | stm32g4 | stm32g474 | svd2rust | no (plan B1) | [stm32g4/rm0440.csv](stm32g4/rm0440.csv) |
| N3 | unsure | stm32-hal2 | `lpuart.rs:145` `set_baud` | LPUART_BRR < 0x300 (no lower-bound guard) | stm32g4 | stm32g474 | svd2rust | no (plan B1) | [stm32g4/rm0440.csv](stm32g4/rm0440.csv) |

### Class G — other (datasheet "do only when disabled", reframed)
| ID | claude | HAL | site | bug (detail §5) | pac | device | tool | caught | CSV |
|---|---|---|---|---|---|---|---|---|---|
| N4 | unsure | mk20dx-hal | `pwm.rs:1859` `set_filter` | FTM FILTER written with quad CH0/CH1 live | mk20d7-pac | mk20d7 | svd2rust | yes (hand-authored, B4) | [mk20d7-pac/mk20d7.csv](mk20d7-pac/mk20d7.csv) |

### Class H — downstream / application OWN-CODE candidates (port experiments)
These fired in the **app's / driver's own source** (not the HAL re-surfacing),
when the project was compiled against an injected PAC. I source-analyzed the
reachable ones (hubris, rustuino); elodin and anne-key I could not reach, so they
stay static claims. Per-site file:line detail and the compiler-agreement column
are in the landscape artifact **"Where datasheet rules would bite"**
(`docs/artifacts/project_landscape.html`).

**Finding: hubris's own USART drivers trip the Class-C rule.** `drv-stm32fx-usart`
(`main.rs:65` then `:74`) and `drv-stm32h7-usart` (`lib.rs:72` then `:76`) both
write `BRR` *after* setting `CR1.UE` — the same configure-after-enable violation
the HAL bugs in Class C have. The `drv-stm32g0-usart` driver does it in the
**correct** order (`BRR` before `UE`), which is the clean control case.

| ID | claude | crate | what fires (own code) | sites | pac | device | tool |
|---|---|---|---|---|---|---|---|
| H1 | tp | hubris `drv-stm32fx-usart` | `BRR` written after `CR1.UE` is enabled (`main.rs:74`, UE at `:65`) — configure-after-enable | 1 | stm32f3 | stm32f303 | svd2rust |
| H2 | tp | hubris `drv-stm32h7-usart` | `BRR` written after `CR1.UE` is enabled (`lib.rs:76`, UE at `:72`) — same shape | 1 | stm32h7 | stm32h753 | svd2rust |
| H3 | fp | hubris `drv-stm32g0-usart` | `BRR` before `UE` (correct order); the `TDR`/`DR` writes and the h7 `CR1` enable-write are the normal data/enable path | 4 | stm32g0, stm32f3, stm32h7 | stm32g031, stm32f303, stm32h753 | svd2rust |
| R | unsure | rustuino | `src/analog.rs` writes ADC `CR2.SWSTART` ×3 — SWSTART is the "go" bit (meant to be written while on); likely a whole-register over-fire, not a config-while-converting write | 3 | stm32f4 | stm32f446 | svd2rust |
| E | unsure | elodin-sensor-fw | its own `src/sdmmc.rs` writes `CLKCR` / `DLENR` / `ARGR` (no gated SDMMC module) — static claim (build halts in the HAL before reaching it) | 11 | stm32h7 | stm32h747cm7 | svd2rust |
| A | unsure | anne-key | FLASH `ACR` latency write at clock init (`src/clock.rs:7-8`); source not reachable to confirm ordering | 2 | stm32l1 | stm32l151 | svd2rust |

---

## 2. Downstream reach — which of the §1 bugs ship in real dependents

Each downstream crate was compiled against the injected PAC. Its firings are the
**same HAL gates re-surfacing**, not new bugs — so each row below links back to
the exact §1 bug ID. "FP-only" means every gate it fired is a §3 false positive,
not a confirmed bug.

| downstream crate | HAL (pinned) | fired | ships §1 bugs | note |
|---|---|---|---|---|
| **semtech_radios** (`lora-phy`/`sx126x`) | stm32-hal2 2.1.10 | 221 | **#4, #9** (tp) · **U1, U2, U4, U6** (unsure) | only downstream carrying confirmed HAL bugs; same pinned version as the sweep, so lines match exactly |
| **blackpill-usb-pwdstore** | stm32f4xx-hal 0.23 | 32 | — (FP-only) | app source has no direct register access; all 32 are `stm32f4xx-hal` guarded/FP sites (#3 is f412-only, not exercised) |
| **stm32f469i-disc** (dependent) | stm32f4xx-hal 0.23 | 42 | — (FP-only) | same — `stm32f4xx-hal` FP sites (pacext UART CR3 IrDA etc.) |
| **dht11-driver** (example) | stm32f4xx-hal 0.23 | 16 | — (FP-only) | same |
| **embassy-stm32** (via stm32-hrtim) | — | 0 | — | no gate fired |
| **stm32-eth** | stm32f4xx-hal 0.23 | 0 | — | compiler-side zero; ETH_MAC/DMA/PTP don't overlap the constrained peripherals (see `docs/PAC_CODEGEN.md`) |

The **full** landscape — every project, ported-and-run vs scanned-at-its-own-pin,
the per-project firing lists, and the compiler-agreement column — is the published
artifact **"Where datasheet rules would bite"**
(`docs/artifacts/project_landscape.html`, from `gen_project_landscape_artifact.py`).
This table only adds what that page doesn't: the mapping from each confirmed §1
bug to the dependents that ship it.

---

## 3. Fired, but not a bug (false positives)

Not in the review table — recorded so they are not re-triaged (they re-fire on
every injection). The per-device CSVs carry the full FP set (`claude_review=fp`);
these are the notable ones.

| site | why it's a false positive |
|---|---|
| stm32-hal2 `adc.rs:766/771` `inject_calibration` (CALFACT) | **wrong injected constraint** — the quote says CALFACT needs ADEN=0, but RM0490 requires **ADEN=1 and ADSTART=0**; the code is correct, the ground-truth constraint is wrong. (A concrete "constraints not human-checked" case.) |
| synopsys-usb-otg `OTG_DCFG` (`write_once`) | whole-register write_once over-fires; the driver's post-init rewrite touches only the **DAD** (device-address) field, on bus-reset / SET_ADDRESS, which USB requires. The datasheet caveat is about speed/PHY fields (DSPD/PFIVL). Field-scoped write_once would not fire. |
| stm32-fmc `FMC_SDRTR` (`write_once`) | compliant — driver writes SDRTR once at init (`sdram.rs` step 6), reads only afterward. |
| stm32-hal2 `flash/{non_,}trustzone.rs` CR (BSY gate, corroborated) | the BSY precondition is correctly satisfied before the write; the gate fires but the driver complies. *(Aside, off the precondition axis: the Secure `erase_page` at `trustzone.rs:229` clears `NSPER` instead of `SECPER` — a real copy-paste code bug, but not a precondition violation.)* |

**The ~1,400 other FP firings** are the handshake / lock / key / configure-*before*-enable
class: the driver establishes the precondition (polls the pending/status bit,
disables the peripheral, or relies on a reset-state invariant), and the
value-blind corroboration auto-cleared most of them. The NXP campaign's 80+
firings outside X1 are all this class (lpc55-hal, mk20dx-hal, embassy-imxrt,
bootleby, canadensis `s32k146` — 0 bugs), adjudicated in
`experiments/nxp_svd2rust/downstream_triage.md`.

---

## 4. Coverage & method

**Clean HALs / BSPs (0 gates fired):** stm32f1xx-hal, stm32f0xx-hal, stm32f1-hal,
rivet-bsp-stm32f401re, lpc55-hal, embassy-imxrt, bootleby, canadensis `s32k146`.

**The complete scanned population** — every project source-scanned at its own pin
(tock, bxcan, fdcan, stm32-usbd, blethrs, booster, px4flow, lilos, …), with raw
hit counts and the compiler-agreement column — is the landscape artifact **"Where
datasheet rules would bite"** (`docs/artifacts/project_landscape.html`). Those are
static scan hits, not triaged bugs: the drivers reach constrained registers
through their own register blocks and can't be compiled against an injected PAC,
so no witness gate fires in their path. The confirmed/candidate bugs that *did*
survive triage are all in §1 above.

**Compile-caught vs manual.** The witness-gate kinds that reduce to *withholding
a raw operation or minting a consumed token* — `state_gate`, `write_once`,
`sequence`, `delay` — are all compile-enforced: compiling a HAL on the injected
PAC fires the bug as `E0277` (the "caught = yes" rows). Most of those rows are
`state_gate`; **N1 is the one `sequence`/lock** (injection withholds `modify` on
`LCKR` — B2+B3 — so the no-op lock is now an `E0277`), and N4 is a hand-authored
`state_gate` (B4). What stays *manual* is the kinds a witness-gate structurally
cannot express — the **value / divisor** rules (Class F = `value_relation`, the
"no (plan B1)" rows) and the **omission / poll-a-flag** defects (Class D U1–U3 =
`dynamic_check`). Adding `write_once`/`sequence`/`delay` to the emitter did **not**
move any of these into "caught" — they are not ordering/withholding rules; they
need the grammar work in `docs/emitter_improvements_plan.md` (B1 `dynamic_check`)
and issue #41.

**The corroborated auto-clear.** Bugs 8–12 were auto-cleared by the pipeline
because the precondition field is *referenced* nearby — but value-blind
corroboration missed that it is set in the **wrong order** (the hubris UE/BRR
shape). The ledger now carries the corroborated gates too
(`static_verdict=corroborated`); a headline count resting only on the *unchecked*
pile undercounts by these 5 (~2.5% false-negative on the auto-clear for these HALs).

**STM step-2 reinjection (negative result).** Reinjecting the whole STM corpus
with the new kinds surfaced **no new bug**: the hard gates land on handshake /
lock / key / config registers correct drivers write legitimately (245
same-register constant `sequence` handshakes, 49 whole-register `write_once`
incl. 33 security locks, 12 `before`-`delay` ordering gates, across 48 manuals).
The only non-handshake leads that a driver does rewrite are OTG_DCFG and
FMC_SDRTR — both §3 FPs.

**Follow-ups.** The injector doesn't yet parse the 0.14-era svd2rust `generic.rs`
(comma-less early-style where-clauses) of the stm32g0 / stm32f0 PACs, which
blocks those HALs; and the `write_once`-heavy U5/H5 families need the
embassy/chiptool arm to reach a downstream (that arm emits only `state_gate` today).

---

## 5. Per-bug detail (appendix)

Full rule / code / impact for each §1 bug, keyed by ID. Still candidate verdicts —
adjudicate in §1. The unsure rows **U1–U8** carry their complete finding in the
§1 *bug* column; no further detail was recorded for them.

### A — LSE written without DBP unlock

**1 · stm32g4xx-hal `rcc/mod.rs:459` `enable_lse`**
- *Rule (RM0440):* BDCR bits are backup-domain write-protected until `DBP=1`.
- *Code:* `DBP` is set in exactly one place, `unlock_rtc()`. `enable_lse` has two callers — `lsco()` calls `unlock_rtc()` first (safe), but `mco(MCOSrc::LSE)` calls `enable_lse` directly with no unlock → `LSEON`/`LSEBYP` written with `DBP=0`.
- *Reachable / impact:* `pin.mco(MCOSrc::LSE, …)`; LSE never starts, MCO outputs nothing.

**6 · stm32-hal2 `clocks/baseline.rs:1016` `setup`**
- *Rule (RM0444, G0):* same DBP requirement for `RCC_BDCR.LSEON`.
- *Code:* the G0 `InputSrc::Lse` path runs `bdcr().modify(lseon=1)`; `dbp` is set only in `rtc.rs`, never on the clocks path or a predecessor of `setup`.
- *Impact:* LSE never enables unless the app independently set DBP (undocumented).

**7 · stm32-hal2 `clocks/baseline.rs:1452` `reselect_input`** — the same G0 LSE-without-DBP write on the input-reselect path.

### B — a clock/cache block reset or bypass-switched while live

**4 · stm32-hal2 `clocks/baseline.rs:880` `setup`**
- *Rule:* `DCRST` writable only when the D-cache is disabled (`DCEN=0`).
- *Code:* the first `flash.acr().modify(...)` sets `DCRST=1` while the cache is enabled out of reset (ACR reset has `DCEN=1`; the HAL's own comment confirms "enabled by default") → the cache reset is silently ignored.

**5 · stm32-hal2 `clocks/baseline.rs:881` `setup`** — same, `ICRST=1` while the I-cache is enabled (`ICEN=1` at reset).

**8 · stm32-hal2 `clocks/baseline.rs:1053` `setup`**
- *Rule:* `HSEBYPPWR` writable only while HSE is disabled (`HSEON=HSERDY=0`).
- *Code:* on the HSE / PLL-from-HSE path, `hseon=1` + HSERDY-wait run at 953/987, then HSEBYPPWR is written at 1047–1056 — with HSE running.
- *Impact (honest):* limited — writing the bypass value while HSE runs is a no-op, and a genuine `hse_bypass=true` config would fail HSERDY earlier; but a real ordering violation.

**9 · stm32-hal2 `clocks/baseline.rs:1055` `setup`** — same block, `HSEBYP` written after `HSEON=1`.

**10 · stm32-hal2 `clocks/f.rs:494` `setup`** — same root cause on the F-series path: `hseon=1` + HSERDY-wait at 457/475, then an unconditional `w.hsebyp(self.hse_bypass)` at 492–495.

### C — a peripheral configured/reconfigured after it was enabled

**11 · stm32-hal2 `usart.rs:265` `new` — the strong one (hubris shape)**
- *Rule (RM0091 CR3 bit1):* "IREN … can only be written when the USART is disabled (UE=0)."
- *Code:* `Usart::new()` calls `enable()` (UE=1, polled) at 233, then — when `config.irda_mode != None` — writes the IrDA config into CR3 (`IREN=1`) at 247–266: UE=0-gated bits written with UE=1.
- *Why it slipped corroboration:* the injected quote was the half-duplex *value-relation* (keep IREN/SCEN cleared), which the code satisfies — value-blind to IREN being written post-enable.
- *Reachable / impact:* any `IrdaMode::Normal`/`LowPower`; IrDA mode misconfigured.

**12 · stm32-hal2 `usart.rs:263` `new`** — the same IrDA `cr3().modify()` after `enable()`, writing `HDSEL` (also UE=0-gated) with UE=1. The written value is 0 (=reset), so benign; the harmful payload is IREN at :265.

**2 · stm32l0xx-hal `adc.rs:259` `configure`**
- *Rule (RM0376/0377):* "software is allowed to program ADC_CFGR1 only when ADEN is cleared."
- *Code:* `configure()` is called only from `read()`/`start()`, and both call `power_up()` immediately before (ADEN=1, waits ADRDY) → CFGR1 configured after the ADC is enabled, on every reachable path.

**3 · stm32f4xx-hal `rcc/f4/mod.rs:641` `config_clocksel` (f412)**
- *Rule (RM0402):* `DCKCFGR.I2S1SRC/I2S2SRC` writable only while PLL and PLLI2S are disabled.
- *Code:* `freeze_internal` sets `PLLON` (:442) and `PLLI2SON` (:467), both ready-polled, then calls `config_clocksel` (:484), which writes the I2S mux → both PLLs live.
- *Impact (honest):* softest of the set — the datasheet says "should", and it runs at init before any I2S consumer, so likely benign; still a clear deviation, on every `freeze()`.

**B1 · embassy-stm32 `lptim/timer/mod.rs:65`**
- *Rule:* LPTIM `CFGR` writable only when the timer is disabled (`ENABLE=0`).
- *Code:* `Pwm::init()` calls `enable()` (CR.ENABLE=1) then `set_frequency()` → `cfgr().modify(set_presc)` while enabled → the prescaler write is ignored (stays DIV1).
- *Impact:* wrong PWM frequency for any non-unity prescaler. Rides the metapac/chiptool arm, not the svd2rust injection.

**B2 · lpc8xx-hal `usart/tx.rs:273`**
- *Rule (LPC845):* to change USART `CFG`, first ensure the USART is not sending/receiving and disable it (`ENABLE=0`).
- *Code:* `enable_cts_throttling`/`disable_cts_throttling` are on the `Enabled` typestate and do `cfg.modify(|_,w| w.ctsen()..)` with no disable-first.
- *Impact:* glitch / corrupt an in-flight character. A distinct site from X1 in the same crate.

**X1 · lpc8xx-hal `i2c/master.rs:98` `read_all`**
- *Rule (LPC845):* `MSTCTL` (master continue/start) must be written only once `STAT.MSTPENDING=1`.
- *Code:* every other I2C op polls MSTPENDING via `wait_for_state`; `read_all` enables master DMA and writes MSTCTL without that poll → MSTCTL written with MSTPENDING=0. Full downstream triage in `experiments/nxp_svd2rust/downstream_triage.md`.

**C1 · embassy-stm32 `i2c/v2.rs:1576` `configure_oa1` (`reconfigure_addresses`)**
- *Rule (RM0440):* OA1 is modifiable only when `OA1EN=0`.
- *Code:* one `oar1().write()` changes `OA1`/`OA1MODE` while toggling `OA1EN` false→true in the same store, so OA1EN is never committed as 0 before the address changes. `configure_oa2` (:1591) is the same shape.
- *Status:* fixed in current embassy HEAD — split into two writes (OA1EN=0 committed first, then address + OA1EN=1). Row tagged `version 0.6.0`.

### E — an incomplete lock sequence

**N1 · stm32-hal2 `gpio.rs:909` `cfg_lock` — the GPIO config lock is a no-op**
- *Rule (GPIOx_LCKR):* the lock engages only via the LCKK key sequence (write LCKK=1+data, =0+data, =1+data, then read).
- *Code:* `cfg_lock` does `lckr().modify(|_,w| w.lck<N>().bit(..))` — it sets only the per-pin `LCKx`; `LCKK`/`lckk` appears **nowhere** in the crate, and the sequence is never performed.
- *Impact:* `cfg_lock(Locked)` silently does nothing. Recovered by injection — B3 gates LCKR, B2 withholds `modify`, so the line is now an `E0277`.

### F — value / divisor rule (not access-control)

**N2 · stm32-hal2 `usart.rs:299` `set_baud` — OVER8 baud miscomputed**
- *Rule:* when `OVER8=1`, `BRR[2:0]=USARTDIV[3:0]>>1` and `BRR[3]` must be kept cleared.
- *Code:* for `OverSampling::O8` it computes `2*fclk/baud` and writes it raw into BRR — no shift, `BRR[3]` not cleared (a literal `// todo` admits it).
- *Impact:* corrupted baud whenever O8 is selected. Not witness-gateable (value rule); the fix is a `debug_assert` (plan B1).

**N3 · stm32-hal2 `lpuart.rs:145` `set_baud` — LPUART_BRR < 0x300**
- *Rule:* it is forbidden to write `LPUART_BRR < 0x300`.
- *Code:* hardcoded `/10` prescaler, `usart_div=(fclk/baud)*256/10`, written raw with no lower-bound check.
- *Impact:* on an LSE-clocked LPUART (32.768 kHz, stop-mode wake) the divisor is ≈87 ≪ 768 — a forbidden write + wrong baud. Conditional on a low-freq clock.

### G — other (datasheet "do only when disabled", reframed)

**N4 · mk20dx-hal `pwm.rs:1859` `set_filter` — FILTER written with quad inputs live**
- *Rule (K20):* writing FILTER must be done only when channels 0–3 are not in input modes, else a valid signal can be missed.
- *Code:* `QuadratureDecoder::new` sets `QUADEN=1` (CH0/CH1 live phase inputs); the only filter API, `set_filter`, does `filter().modify(..)` while the decoder is active and never disables it first.
- *Impact:* structurally always in the hazard window — a dropped quadrature edge. Really a `state_gate` (precondition QUADEN cleared) filed as `other`; recovered via a hand-authored `state_gate` (B4).
