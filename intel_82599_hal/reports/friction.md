# Friction ledger — what it took to make the generated HAL work with Theseus

Every manual or contract-level adaptation needed so that remaining compiler
errors mean *bugs and genuine divergences*, not trivia. Each entry names its
category, the artifact that records it, and whether it recurs per-device or is
one-time experiment scaffolding.

## A. Naming (datasheet name ↔ driver name)

| # | Item | Artifact | Notes |
|---|------|----------|-------|
| A1 | `FCTTVn` → `fcttv` | `pipeline/name_map.json` (1 entry) | The ONLY register-name mismatch out of 75: the datasheet abbreviation carries a literal index letter (`FCTTVn`, no brackets); the mechanical rule lowercase(abbrev base) gives `fcttvn`. Found as 1 of the 3 first-compile errors. |
| A2 | Driver constant names ↔ datasheet field names | `pipeline/constants_map.json` (71 entries, 54 field-derived) | The driver invents constant names (`RECEIVE_ENABLE` is RXCTRL.RXEN, `TE` is DMATXCTL.TE, `BROADCAST_ACCEPT_MODE` is FCTRL.BAM). The map records name + derivation kind; bit positions still come from extraction. Writing it took datasheet knowledge for ~10 entries (e.g. `BROADCAST_ACCEPT_MODE` = FCTRL.BAM); `alt` spellings were needed for 0 entries in the final run (fuzzy matcher sufficed). |

All 75 register field names otherwise joined mechanically (case-insensitive
base-name match) — zero further register-name friction.

## B. Packaging / API shape (driver contract, not datasheet fact)

| # | Item | Artifact |
|---|------|----------|
| B1 | 7-struct split of the 128 KiB BAR0 space, region boundaries, queue container fields (`rx_regs1/tx_regs/rx_regs2`), struct/doc names | `pipeline/packaging.json` |
| B2 | Queue element structs (`RegistersRx`/`RegistersTx`, 64 B) derived by rule: a 0x40-stride register bank starting inside a queue region becomes an element-struct field at `offset − region_start` | emitter rule (s4_emit_hal.py) |
| B3 | `queue_registers.rs` untouched: it is driver glue (trait impls, MappedPages plumbing), not register data | — |
| B4 | Array representation rules: R1 contiguous stride-4 → `[Volatile<u32>; N]`; R2 non-contiguous stride (RAL/RAH interleaved 8-byte pairs) → element-0 scalar, as the driver models it; R3 second banks outside queue regions (EITR's 0x12300 bank) → skipped, as the driver does | emitter rules, logged per-register in `emit_report.json` |

## C. Adjudicated access divergences (datasheet vs. driver reality)

| # | Item | Resolution |
|---|------|------------|
| C1 | `RDH[n]` datasheet-typed RO ("controlled by hardware") but the driver must zero the head at queue init (as ixgbe/DPDK do) | `config/access_overrides.json` → `Volatile`, adjudication recorded |
| C2 | `TDH[n]` heading says RO, but its own description authorizes exactly one software write ("after a reset and before enabling the transmit function") | Structural config: override to `Volatile`. Constraint config: **witness-gated write** — the datasheet's authorization rule becomes the type (`GatedTdh::write(v, &TxdctlEnableCleared)`), superseding the override. |

These two were 2 of the 3 first-compile errors — the compile metric surfaced
them, and they are *findings about the datasheet/driver relationship*, not
extraction misses.

## D. Driver policy constants (no datasheet derivation possible)

17 of 71 constants are driver-chosen values (`TXDCTL_PTHRESH = 36` "taken from
DPDK", `DISABLE_INTERRUPTS`, RETA byte-lane offsets, composite semaphore
masks, one silicon-workaround reserved bit). Kept verbatim, each with a
recorded reason in `config/constants_map.json`.

## E. Driver diff required by the constraint layer (by design)

`pipeline/driver_diff_gated.patch`: **2 files, +27/−15 lines** for 9 encoded
constraints — the measured cost of adopting the field-level gates:
- `enable_rx_function`: mint `RxctrlRxenCleared`, pass its token to the `fctrl`
  write, `release` re-enables (replaces two manual RXEN writes).
- `set_tdh`: mint `TxdctlEnableCleared` before the head write.
- CRC strip: the two independent OR-writes (one of them the RDRXCTL bug)
  collapse into one coupled `set_rxcrcstrp_crcstrip(..., true)` call.
- 5 mechanical renames `write` → `write_preserving` (hlreg0 tx site, rdrxctl
  RSC clear, both dmatxctl TE toggles, eiac) — loud-by-design: gated registers
  drop raw `write()` so every old site must consciously pick the preserving,
  witnessed, or coupled path; silent clamping would hide driver intent.
The original driver already satisfied the FCTRL/TDH rules implicitly; the
gates make the ordering structural instead of accidental.

## F. Source-document artifacts (md conversion of the datasheet)

Not code friction, but they shaped the pipeline and belong in any honest
account of "datasheet → HAL":
- Register bit tables split across page markers; continuations sometimes land
  under the NEXT section heading (AUTOC's bits 25–31 sit under the LINKS
  heading). Handled by the completion pass (full-page context expansion) +
  a merge-continuation prompt rule + model escalation for 3 stubborn cases.
- Table 8-2 omits second register banks (the 0xD000 Rx queue bank); the
  detailed headings carry them → both sources parsed, cross-checked.
- Datasheet-internal inconsistencies found by the cross-checks: GPRC/GPTC
  access codes swapped between summary (RC/RO) and detail (RO/RC); EITR's
  second range printed "n=24...128" (129 entries would overrun; actual 24–127).

## G. Environment scaffolding (one-time)

- This worktree has no `.venv`; the sibling `hal_agent-retrieval` venv is used.
- Theseus needs its submodules and pinned nightly-2023-10-27; full `make iso`
  additionally needs `nasm` (absent on this host), so the eval gate is
  `cargo check`/`cargo build -p ixgbe` for the whole crate graph under
  Theseus's target JSON — regs.rs is fully within that graph.
