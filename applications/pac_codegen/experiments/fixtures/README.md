# Cross-PAC experiment fixtures

Inputs for `../cross_pac.py` (the cross-PAC generality experiment; see
`docs/cross_pac_generality.md` for results).

The three STM fixtures are **verbatim copies** of real generator output from
the phase-1d corpus — byte-identical to their sources (verified with `cmp` at
copy time). That is the point of the experiment: the constraints injected into
each family's PAC are real extracted constraints, not hand-tuned examples.

| Fixture | Corpus source (read-only checkout) | Family / reference manual |
|---|---|---|
| `rm0008_i2c1_cr1.json` | `/home/ramla/hal_agent-phase-1d/agent_output/stm/rm0008/1/i2c1_cr1` | STM32F1 / RM0008 |
| `rm0091_i2c1_timeoutr.json` | `/home/ramla/hal_agent-phase-1d/agent_output/stm/rm0091/3/i2c1_timeoutr` | STM32F0 / RM0091 |
| `rm0394_spi1_cr1.json` | `/home/ramla/hal_agent-phase-1d/agent_output/stm/rm0394/1/spi1_cr1` | STM32L4 / RM0394 |

`rp2040_i2c0_ic_enable.json` is **SYNTHETIC** (clearly marked inside the
file): a minimal constraint targeting the real `I2C0.IC_ENABLE` register and
its real `ENABLE`/`ABORT` fields in `rp2040-pac`. It exists only to probe
whether the injector's generic.rs template survives a non-stm32-rs,
different-svd2rust-version crate — the constraint text is not a corpus
extraction and licenses no extraction claim.
