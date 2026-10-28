# NXP svd2rust — downstream triage

Each injected PAC (whole-register hard gates, `--register-only`) was patched into
its real downstream HALs/firmware via `[patch.crates-io]` and built. A gate
**firing** is an `E0277` where the consumer writes a constrained register without
the witness. Method (`run_downstream.py`): build PRISTINE first; if that fails
the target is *unevaluable* (not our gate); else patch and rebuild, and every new
`E0277` is a firing. Every firing is adjudicated against the datasheet
precondition and the driver source: **BUG** (reachable with the precondition
false on a realistic/public path) vs **FP/friction** (the driver already
establishes the precondition imperatively — polls the pending/status bit,
disables the peripheral, or relies on a reset-state invariant).

## Summary

| consumer | device / PAC | firings | bugs | result |
|---|---|--:|--:|---|
| lpc55-hal 0.7.1 | lpc55s69 / lpc55-pac 0.5.0 | 10 | 0 | all FP |
| mk20dx-hal (mk20d7) | mk20d7 / mk20d7-pac | 11 | 0 | all FP |
| mk20dx-hal (mk20d5) | mk20d5 / mk20d5-pac | 2 | 0 | all FP |
| lpc8xx-hal 0.10.0 | lpc845 / lpc845-pac 0.4.1 | 9 | **1** | **1 real bug** + 8 FP |
| embassy-imxrt | mimxrt685s / mimxrt685s-pac | 49 | 0 | all FP |
| bootleby (Oxide RoT loader) | lpc55 / lpc55-pac 0.5.0 | 0 | 0 | compiles clean, no gated access |
| **total evaluated** | | **81** | **1** | |
| nitrokey-3-firmware | lpc55 | — | — | unevaluable: pristine needs `arm-none-eabi-gcc` (p256-cortex-m4-sys) |
| solo2 | lpc55 | — | — | out of scope: lpc55-hal 0.6 → lpc55-pac ^0.4 + `-Dwarnings` |
| hubris + bootleby-apps | lpc55 | — | — | out of scope: lpc55-pac ^0.4 + `xtask` build |

## The one real bug — lpc8xx-hal `I2cMaster::read_all`

**File:** `src/i2c/master.rs:98` · **public API:** `read_all(address, buffer, channel)`

Datasheet (LPC845 I2C): *MSTCTL should only be written when `STAT.MSTPENDING` is
set (the last bus operation has completed).* The gate withholds the witness, so a
witness-free `MSTCTL` write fires.

The DMA-read entry point enables master DMA on `MSTCTL` **without** first waiting
for the master to become pending, whereas its DMA-write twin does:

```rust
pub fn write_all(..) -> .. {
    self.start_operation(address, Rw::Write)?;   // ends by writing MSTSTART → MSTPENDING clears
    self.wait_for_state(State::TxReady)?;        // ← waits until MSTPENDING set
    self.mstctl.modify(|_, w| w.mstdma().enabled());
    ..
}
pub fn read_all(..) -> .. {
    self.start_operation(address, Rw::Read)?;    // ends by writing MSTSTART → MSTPENDING clears
    self.mstctl.modify(|_, w| w.mstdma().enabled());   // ← line 98: NO wait; MSTPENDING = 0 here
    ..
}
```

`start_operation` finishes with `mstctl.write(|w| w.mststart().start())`, which
starts the transfer and drops `MSTPENDING` to 0 (in progress). `read_all` then
modifies `MSTCTL` to arm DMA while the master is not pending — exactly the access
the datasheet forbids — so the DMA-enable may be dropped/misapplied during the
address phase. The write path gets this right (`wait_for_state(TxReady)` first);
the read path omits the wait. Reachable on the normal path through the public
`read_all`; asymmetric with every other `MSTCTL` access in the file, which is
either preceded by a `wait_for_state` or guarded. Classic configure-without-wait
bug — the gate caught it by flagging the one site that skips the handshake.

## Why everything else is a false positive

The firing registers land exactly where they should — the I2C master/slave
command protocol, the PUF key path, the TRNG entropy-config path, the LPTMR/RTC
timers — but the drivers are disciplined and uphold each precondition in code:

- **lpc55-hal (10):** every `MSTCTL` write sits next to `while stat.mstpending().is_in_progress()`; PUF `CODEINPUT`/`KEYOUTPUT` guarded by `if stat.codeinreq()`/`if stat.keyoutavail()`; ADC `SWTRIG` only after `ctrl.adcen` set. (details in `lpc55s69/downstream_lpc55_hal.md`)
- **mk20dx-hal (13):** LPTMR `PSR`/`CMR` always written after `csr().write(ten=0)` (disable-first); RTC `IER`/`TAR` rely on the `WAR` access bits being set at reset (the HAL never writes the Lock register).
- **embassy-imxrt (49):** every MSTSTART/STOP/CONTINUE and SLVCONTINUE/SLVNACK command write is pending-gated (busy-wait or an explicit `if …pending()` on the line above; drop-guards defer to the pending-gated IRQ handler). All five TRNG config writes (`FRQMAX`/`PKRRNG`/`SCR1L`/`SCR5L`/`SCMISC`) are bracketed by `MCTL[PRGM]=1` inside `init()` — the entropy source is never configured outside programming mode. The only non-gated writes are DMA-arm *config-bit* toggles in teardown/recovery (value-blind whole-register friction, no bus command).
- **bootleby:** compiles clean against the gated PAC — it touches none of lpc55's gated registers in a witness-free way.

The witness API would formalize exactly these imperative waits/checks; the one
place the pattern is broken (lpc8xx-hal `read_all`) is the bug.

## Field-gating pass (every compiler error)

Re-ran with the field-level advisory ON (`GATE_MODE=field`): each constrained
*field*'s writer accessor takes a witness, so a witness-free `w.<field>(…)` fires
`E0061`. This is the more precise (and higher-volume) signal — it pinpoints the
exact field, not the whole register. Every error was adjudicated.

**205 field firings → 13 distinct field-gates → 0 new bugs.** (lpc8xx-hal and
embassy-imxrt produce 0 field firings — lpc845 has no field-scoped constraints,
and embassy-imxrt never writes mimxrt685s's field-gated security/lock registers.)

| consumer | whole-reg (E0277) | field (E0061) | distinct field-gates | field bugs |
|---|--:|--:|--:|--:|
| lpc55-hal | 10 | 26 | 2 | 0 |
| mk20dx-hal (mk20d7) | 11 | 109 | ~11 | 0 |
| mk20dx-hal (mk20d5) | 2 | 70 | (subset) | 0 |
| embassy-imxrt | 49 | 0 | 0 | 0 |
| lpc8xx-hal | 9 | 0 | 0 | 0 |
| bootleby | 0 | 0 | 0 | 0 |

Distinct field-gates, all **FP/friction**:

- **lpc55-hal (2):** `flexcomm/PSELID.PERSEL` (×25 sites — i2c/spi/usart/hs-spi
  `enabled_as_*`) is written right after `syscon.reset()` (so `PSELID.LOCK`=0),
  in a configure-then-lock RMW; `rng/ONLINE_TEST_CFG.DATA_SEL` (×1) is in dead
  `initialize_entropy` (`unimplemented!()`, private, no caller).
- **mk20dx-hal (11):** nine are FTM config fields (`SC.PS/CLKS/CPWMS`,
  `POL.POLn`, `SWOCTRL.*`, `MODE.FTMEN/INIT`, `DEADTIME.*`, `QDCTRL.QUADEN`)
  gated on `MODE.WPDIS` set — **the HAL sets `WPDIS=1` at every FTM entry
  (`split`/`pwm`/`quad`) and never re-enables write-protection**, and the config
  methods are reachable only through typestate handles minted after that; the few
  SC writes that precede their own WPDIS run on a from-reset peripheral (WP off).
  `CMP CR0.FILTER_CNT` (CR1.SE never set); `PDB SC.LDOK` (documented enable-first
  ordering, misuse is a benign hardware no-op, pinned by a test).

**Conclusion:** the field pass confirms the whole-register conclusion with
field-precision — the drivers establish each field's precondition imperatively
(reset-after-reset for the lock bits, WPDIS-before-config for FTM). It surfaces
**no bug beyond** the one whole-register finding (lpc8xx-hal `read_all`). The
value of field mode is diagnostic precision, not additional bugs — and its
volume (205 vs 81) is why the whole-register hard gate is the better default for
a bug-hunt.

### All-errors tally

Across both modes, every injected compiler error was triaged: **81 whole-register
(`E0277`) + 205 field (`E0061`) = 286 firings → 1 real bug** (lpc8xx-hal
`I2cMaster::read_all`), the rest friction on disciplined drivers.

## Low-value-project scan

A pass over the "standalone / stale / dead" crates in the NXP ecosystem doc. Most
are **not scannable**: the device has no constraints in our corpus (lpc82x,
lpc546xx, mkw41z, mcxa, mcxn947 — different families we never extracted), or there
is no consumer to build (ke04, mk66f18, k64, k32l3a60 have no HAL and no
downstream). The one low-value project that pairs a device we have constraints for
with a real consumer is **canadensis** (s32k1xx RM → injected into `s32k146-pac`
0.1.0, 21 whole-register gates; the `s32k146_node` UAVCAN example drives FlexCAN
and the clock tree RAW, no HAL).

| consumer | device / PAC | firings | bugs | result |
|---|---|--:|--:|---|
| canadensis `s32k146_node` | s32k146 / s32k146-pac 0.1.0 | 2 | 0 | all FP |

Both firings are the configure-before-enable pattern, done correctly:
- `SCG.SOSCDIV` write (`src/main.rs:79`) — precondition `SOSCCSR.SOSCEN` cleared.
  The example writes the divider while SOSC is still disabled (enabled later at
  :84). FP.
- `SCG.SPLLCFG` write (`src/main.rs:92`) — precondition `SPLLCSR.SPLLEN` cleared
  ("SPLLCFG cannot be changed when the PLL is enabled; writes are ignored"). The
  example configures the PLL before enabling it at :94. FP.

Well-written clock init (it follows the RM §28.1.4 sequence). **No bug in the
low-value projects.** The gate again fired on exactly the right registers (SCG
clock-source config) and confirmed the ordering was correct.
