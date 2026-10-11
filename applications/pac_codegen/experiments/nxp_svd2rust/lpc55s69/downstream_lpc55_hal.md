# Downstream: lpc55-hal against the injected lpc55-pac

Built **lpc55-hal 0.7.1** (`thumbv8m.main-none-eabihf`) with
`[patch.crates-io] lpc55-pac = { path = <injected> }`. The gate fires at **every**
site the HAL touches a constrained register — **10 whole-register firings** (plus
field-gate `E0061`s from the default field-level advisory). All 10 adjudicated
against the HAL source.

| # | site | register / op | datasheet precondition | verdict |
|---|---|---|---|---|
| 1 | drivers/i2c.rs:164 | MSTCTL write (mststart) | MSTPENDING=1 (master idle) | FP — idle after enable / prior `stop()` waited for pending |
| 2 | drivers/i2c.rs:184 | MSTCTL write (mstcontinue) | MSTPENDING=1 | FP — preceding `while stat.mstpending().is_in_progress()` |
| 3 | drivers/i2c.rs:204 | MSTCTL write (mststart, read path) | MSTPENDING=1 | FP — same as #1 |
| 4 | drivers/i2c.rs:250 | MSTCTL write (mstcontinue) | MSTPENDING=1 | FP — same as #2 |
| 5 | drivers/i2c.rs:264 | MSTCTL write (last-byte) | MSTPENDING=1 | FP — same as #2 |
| 6 | peripherals/puf.rs:191 | CODEINPUT write (`do_start`) | STAT.CODEINREQ=1 | FP — guarded by `if stat.codeinreq().bit_is_set()` |
| 7 | peripherals/puf.rs:258 | CODEINPUT write (`get_key`) | STAT.CODEINREQ=1 | FP — same guard |
| 8 | peripherals/puf.rs:263 | KEYOUTPUT read (`get_key`) | STAT.KEYOUTAVAIL=1 | FP — guarded by `if stat.keyoutavail().bit_is_set()` |
| 9 | peripherals/adc.rs:136 | SWTRIG write (`cancel_compare`) | CTRL.ADCEN=1 | FP — ADC enabled in config (ctrl.adcen set) |
| 10 | peripherals/adc.rs:299 | SWTRIG write (`read`) | CTRL.ADCEN=1 | FP — same; see note |

**No confirmed bug.** lpc55-hal is a well-written HAL: it upholds every datasheet
precondition imperatively (polls MSTPENDING, the PUF CODEINREQ/KEYOUTAVAIL
handshake, enables the ADC before triggering). The witness API would formalize
exactly these waits/checks. This is the expected "disciplined driver" outcome,
and it confirms the gate fires at precisely the right places — including the
security-critical PUF key-input/output path.

**One latent note (not a bug):** `Adc::read` and `cancel_compare` are on
`impl<State> Adc<State>` (no enabled-typestate), and a `disable()` path clears
ADCEN (adc.rs:271). Calling `read()` after disable would write SWTRIG with
ADCEN=0 (silently ignored) and hang at `while fctrl[0].fcount()==0 {}`. No caller
does this; the gate would have surfaced the missing typestate.

Reproduce: clone lpc55-hal, add the `[patch.crates-io]` to the injected PAC, and
`cargo build --target thumbv8m.main-none-eabihf`.
