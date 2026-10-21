# Survey: bugs from the NON-state_gate constraints (STM + NXP)

`state_gate` was already scanned (the whole-register injection campaigns). This
survey covers the other kinds — **`write_once`, `sequence`, `delay`, `other`,
`value_relation`** — which the compile-gate can't express (so step-2's automated
scan is blind to them) and which the FP analysis said hide their bugs in manual
review. Method: extract every distinct non-state_gate rule (1124 STM + 472 NXP
after dropping pure security-lock/key registers no HAL touches), then read each
against the real driver source and adjudicate (a rule is a bug only if a driver
demonstrably does the forbidden thing on a reachable path; `modify`-preserves,
established-precondition, and untouched-register cases are dismissed).

## Confirmed bugs — non-state_gate (the requested scope): 4

| # | crate | site | register / kind | the rule it breaks | effect |
|---|---|---|---|---|---|
| 1 | **stm32-hal2 2.1.10** | `src/gpio.rs:909` `cfg_lock` | GPIOx_LCKR / **sequence** | the config lock engages only via the LCKK key sequence (write LCKK=1, =0, =1, read, read) | `cfg_lock(Locked)` sets only the per-pin `LCKx` bit and never writes `LCKK` (grep: `lckk` absent from the whole crate) → **the lock silently never engages**; a safety API that does nothing |
| 2 | **stm32-hal2 2.1.10** | `src/usart.rs:299–316` `set_baud` | USART_BRR / **value_relation** | when OVER8=1, BRR[2:0]=USARTDIV[3:0]>>1 and BRR[3] must be kept cleared | with `OverSampling::O8` (public) the OVER16 divisor `2·fclk/baud` is written raw — no shift, BRR[3] not cleared (an in-source `// todo` admits it) → **corrupted baud rate** |
| 3 | **stm32-hal2 2.1.10** | `src/lpuart.rs:145–156` `set_baud` | LPUART_BRR / **value_relation** | it is forbidden to write LPUART_BRR < 0x300 | no lower-bound guard; LSE-clocked LPUART (32.768 kHz, common for stop-mode wake) computes ≈76 ≪ 768 → **forbidden write + wrong baud** (conditional on a low-freq LPUART clock) |
| 4 | **mk20dx-hal 0.2.2** | `src/pwm.rs:1859` `set_filter` | FTM_FILTER / **other** | writing FILTER must be done only when channels 0–3 are NOT in input modes, else a valid signal can be missed | `QuadratureDecoder::new` sets QUADEN=1 (CH0/CH1 live as phase inputs); the only filter API writes FILTER while the decoder is active and never disables it → structurally always in the hazard window |

Three of four are in **stm32-hal2 2.1.10** (a popular multi-family HAL), all surfaced by `sequence`/`value_relation` rules.

## Bonus — real bugs, but state_gate-class (configure-while-enabled); outside the strict scope, distinct sites: 2

| crate | site | what | note |
|---|---|---|---|
| **embassy-stm32** (0.6.0 … HEAD) | `src/lptim/timer/mod.rs:65` via `lptim/pwm.rs init` | LPTIM PWM writes `CFGR.PRESC` *after* `enable()` (CR.ENABLE=1); CFGR is writable only when disabled → prescaler write ignored → **wrong PWM frequency** for any non-DIV1 case | the governing rule is a `state_gate` (write-when-disabled); flagged because it's genuinely harmful and may not have been in the prior scan's crate set |
| **lpc8xx-hal 0.10.0** | `src/usart/tx.rs:273` `enable_cts_throttling` | reconfigures USART `CFG.CTSEN` while the USART is enabled; datasheet requires disabling first → glitch/corrupt an in-flight character | state_gate-class; a DISTINCT site from the prior campaign's lpc8xx CFG finding |

## The clobber / RMW class (the OAxEN shape) — clean this round

The prototypical "whole-word write drops a preserved bit" bug (which found a real
embassy bug in the chiptool arm) came up **clean everywhere reachable** in both
ecosystems: Flexcomm FIFOWR is always a full `.write()`, i.MX PDRUNCFG uses
SET/CLR registers, eDMA writes BITER==CITER, WWDT feed is 0xAA→0x55 in order,
FlexCAN IFLAG is single-bit W1C, and the STM I2C/SPI drivers use `modify` on the
registers whose rules name preserved bits. No pure clobber bug survived.

## Also checked and cleared (representative)
WWDG T6 combined-setter (embassy `t_val=63+ticks` always sets bit 6 — correct);
OTG_DCFG write-once (only the DAD address field is updated post-init, which USB
requires — FP); FMC_SDRTR (written once); ADC voltage-regulator startup delays
(all present); SPI TXDR/RXDR access-width (only ever *wider* than configured);
RTC_PRER two-write (single 32-bit write is a documented spec-deviation but
latches both prescalers on silicon — benign).

## Caveats
- Confidence: #1/#2 high, #3 conditional (needs a low-freq LPUART clock), #4
  medium (the FILTER hazard note's literal scope is input-capture; quadrature
  mode reuses the same CH0/CH1 FILTER fields as inputs, so it applies).
- Coverage is the mature crates.io HALs + the shared driver crates
  (synopsys-usb-otg, stm32-fmc) + embassy HEAD; obscure peripherals on families
  with no HAL (many U5/H5 `other` rules: RIFSC, MDIOS, GPDMA, XSPI) have no
  consumer to violate them and were not reachable.
