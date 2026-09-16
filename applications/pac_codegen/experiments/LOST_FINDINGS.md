# Findings we used to report and no longer do

Hand-maintained. One entry per constraint that **previously produced a
violation in a driver crate** and stopped doing so because it was removed at an
earlier stage. Not a list of every dropped constraint — only the ones where a
real compile error disappeared, so each is a finding we may have given up.

Add an entry when a change removes a gate that a driver was hitting. Mark it
resolved when you have decided the loss was correct, or when the finding comes
back another way.

---

## 1. Whole-register gates on a bit inside the same register

**Removed by:** `same_register_software_gate` (rule 2, commit `9b207db`).
A gate whose condition is a field of the register it guards, restorable only by
software, is a one-way door: set the field once and the register can never be
written again, because clearing it is itself a write the gate forbids.

**Why the rule was still real.** The datasheet sentence is about *one bit*, and
the extraction lost the field list. rm0041's SPI_CR1 is the clearest:

> Bit 13 **CRCEN:** … This bit should be written only when SPI is disabled
> (SPE = '0) for correct operation.

Two of the three SPI copies extracted this correctly as field-scoped; only the
mis-scoped third produced a gate, and whole-register mode skips field-scoped
constraints, so the wrong reading was the only one that could fire.

**Registers affected**, by how many manuals lost the gate:

| register | manuals | condition |
|---|---:|---|
| `spi1/CR1` | 9 | `SPE cleared` |
| `usart1/CR1` | 8 | `UE cleared` |
| `i2c1/OAR2` | 6 | `OA2EN cleared` |
| `i2c1/OAR1` | 5 | `OA1EN cleared` |
| `fdcan1/CCCR` | 3 | `CCE`, `INIT` |
| `i2c1/TIMEOUTR` | 2 | `TEXTEN cleared` |
| others (26 registers) | 1–2 each | |

**Driver findings lost** — hits before → after, same mode:

| manual | driver | hits | registers it lost |
|---|---|---|---|
| rm0433 | `stm32-hal2` | 206 → 176 | `usart1/CR1`, `tim16/BDTR` |
| rm0399 | `stm32-hal2` | 172 → 146 | `usart1/CR1` |
| rm0468 | `stm32-hal2` | 170 → 144 | `fdcan1/CCCR`, `sdmmc1/CMDR`, `otfdec1/R1CFGR`, `R3CFGR`, `R4CFGR`, `fmc/BCR1`, `usart1/CR1` |
| rm0454 | `stm32-hal2` | 42 → 17 | `usart1/CR1` |
| rm0041 | `stm32f1xx-hal` | 23 → 2 | `spi1/CR1` |
| rm0386 | `stm32f4xx-hal` | 54 → 38 | `spi1/CR1`, `dsi/WCR`, `dsi/WRPCR` |

**Status: VERIFIED — nothing lost.** Every one of the six pairings finds MORE
under field gating, and no driver file went dark:

| manual | driver | reg-only | field | files lost | files gained |
|---|---|---:|---:|---:|---:|
| rm0041 | `stm32f1xx-hal` | 2 | **23** | 0 | 2 |
| rm0386 | `stm32f4xx-hal` | 38 | **42** | 0 | 5 |
| rm0454 | `stm32-hal2` | 17 | **24** | 0 | 1 |
| rm0468 | `stm32-hal2` | 144 | **151** | 0 | 0 |
| rm0399 | `stm32-hal2` | 146 | **154** | 0 | 1 |
| rm0433 | `stm32-hal2` | 176 | **186** | 0 | 1 |

rm0041 lands back on exactly 23, the count it had before rule 2 removed the
unsound `SPI_CR1` gate — the rule returned scoped to `CRCEN` and caught the same
code. Site-level, where the record is complete (rm0041, all 23 sites), nothing
present in register-only is missing from field.

> **A trap when checking this yourself.** `hal_results[].triage` in the sweep
> summary is a SAMPLE capped at 40 rows, not the population; the verdict counts
> beside it are complete. Diffing two capped lists across modes made
> `watchdog.rs:76-77` look lost on rm0386 when the gates are identical in both
> and the file is in the hits set for both. `triage_truncated` now records how
> many rows were dropped.

---

## 2. Quotes that do not attribute to their register

**Removed by:** `target_unverified_by_location`.
The supporting sentence never names the register — "this bit", "these bits" —
and anchored outside the register's own section, so nothing ties it here.

| manual | register | note |
|---|---|---|
| rm0456 | `adc4/CFGR2` | see below — this one is a counting bug, not a real attribution failure |
| rm0486 | `sdmmc1/IDMALAR` | same shape |

Both are the same sentence transcribed twice, once with a `Note:` prefix. The
quote dedup compares exact text while the merge test compares by containment,
so one sentence counted as two and the attribution bar rose with no new
evidence behind it. **Tracked as issue #27**; deferred, not urgent.

**Status: not yet checked** whether either register was producing a driver
finding. rm0456 pairs with `stm32-hal2`; rm0486 with none.

---

## 3. Instances that disagree

**Removed by:** `instance_conflict_dropped`. Two copies of a peripheral read
one sentence incompatibly and nothing distinguishes which is right, so no gate
is emitted for any copy.

8 registers lose enforcement entirely this way, including `adc1/CALFACT` on
rm0394 and `sdmmc1/DLENR` on rm0433.

**Status: unexamined.** One of the two readings is correct in each case, so a
real rule is going unenforced on every instance. These are the best candidates
for recovery by hand, since resolving a single disagreement restores the gate
for the whole peripheral.
