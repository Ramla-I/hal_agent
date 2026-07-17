# I2C CR1 call sites — what each HAL does at every witness-gated access

**Date:** 2026-07-17
**Scope:** every place the I2C control-register (CR1) witness gate breaks an
unmodified HAL crate, with the actual driver code at that line.
**Constraint enforced:** a write or modify of `I2C_CR1` requires the `STOP`,
`START`, and `PEC` bits to be settled (cleared / not mid-operation) first —
the datasheet's rule that you must not reconfigure CR1 while a previous
START/STOP/PEC condition is still pending. (Exact sentence and encoding:
`applications/pac_codegen/constraints/stm32f103.json`.)
**Sources inspected:** `stm32f4xx-hal` 0.23.0 and `stm32f1xx-hal` 0.11.0,
built against the injected PAC; run artifacts in
`applications/pac_codegen/experiments/out/corroboration_{f4,f1}.jsonl`.

## How to read the table

Each row is one call site the compiler rejected once the gate was injected.
Columns:

- **site / function** — file, line, and the enclosing HAL function.
- **op** — the register surface the gate flagged (`modify` = read-modify-write;
  `write` = full write). A modify is gated because it performs a write.
- **CR1 action on flagged line** — what that line actually does to CR1
  (which bits it sets or clears).
- **scan / judge** — the two independent corroboration passes: did the
  enclosing function establish the STOP/START/PEC preconditions *before* this
  line? (`corroborated` = yes, `unchecked` = no.)
- **final** — the adjudicated class: **unchecked** (no guard — a candidate
  latent bug), **partial** (waits on `STOP` only, never `START`/`PEC`), or
  **fully corroborated** (all three — none exist).

## stm32f4xx-hal 0.23.0

| # | site | function | op | CR1 action on flagged line | scan | judge | final |
|---|------|----------|----|----------------------------|------|-------|-------|
| 1 | `i2c.rs:149` | `i2c_init` | modify | clear PE | unchecked | unchecked | **unchecked** |
| 2 | `i2c.rs:205` | `i2c_init` | modify | set PE | unchecked | unchecked | **unchecked** |
| 3 | `i2c.rs:261` | `prepare_write` | modify | set START | corroborated | unchecked | **partial** |
| 4 | `i2c.rs:326` | `prepare_read` | modify | set START, set ACK | corroborated | unchecked | **partial** |
| 5 | `i2c.rs:352` | `prepare_read` | modify | set START | corroborated | unchecked | **partial** |
| 6 | `i2c.rs:461` | `read_wo_prepare` | modify | clear ACK, set STOP | unchecked | unchecked | **unchecked** |
| 7 | `i2c.rs:490` | `write_wo_prepare` | modify | set STOP | unchecked | unchecked | **unchecked** |
| 8 | `i2c.rs:511` | `write_iter` | modify | set STOP | unchecked | unchecked | **unchecked** |
| 9 | `i2c/dma.rs:432` | `send_start` | modify | set ACK, set START | unchecked | unchecked | **unchecked** |
| 10 | `i2c/dma.rs:434` | `send_start` | modify | set START | corroborated | unchecked | **unchecked** \* |
| 11 | `i2c/dma.rs:459` | `send_stop` | modify | set STOP | unchecked | unchecked | **unchecked** |
| 12 | `i2c/dma.rs:529` | `prepare_read` | modify | clear ACK | unchecked | unchecked | **unchecked** |
| 13 | `i2c/dma.rs:701` | `handle_dma_interrupt` | modify | clear ACK | unchecked | unchecked | **unchecked** |
| 14 | `i2c/dma.rs:788` | `handle_dma_interrupt` | modify | clear ACK | corroborated | unchecked | **unchecked** \* |

## stm32f1xx-hal 0.11.0

| # | site | function | op | CR1 action on flagged line | scan | judge | final |
|---|------|----------|----|----------------------------|------|-------|-------|
| 1 | `i2c.rs:227` | `init` | modify | set PE | unchecked | unchecked | **unchecked** |
| 2 | `i2c.rs:232` | `reset` | write | set PE, set SWRST | unchecked | unchecked | **unchecked** |
| 3 | `i2c.rs:233` | `reset` | write | reset() (all bits → reset) | unchecked | unchecked | **unchecked** |
| 4 | `i2c.rs:242` | `send_start` | modify | set START | unchecked | unchecked | **unchecked** |
| 5 | `i2c.rs:255` | `send_stop` | modify | set STOP | unchecked | unchecked | **unchecked** |
| 6 | `i2c.rs:316` | `prepare_write` | modify | set START | corroborated | unchecked | **partial** |
| 7 | `i2c.rs:381` | `prepare_read` | modify | set START, set ACK | corroborated | unchecked | **partial** |
| 8 | `i2c.rs:407` | `prepare_read` | modify | set START | corroborated | unchecked | **partial** |
| 9 | `i2c.rs:516` | `read_wo_prepare` | modify | clear ACK, set STOP | unchecked | unchecked | **unchecked** |
| 10 | `i2c.rs:545` | `write_wo_prepare` | modify | set STOP | unchecked | unchecked | **unchecked** |
| 11 | `i2c.rs:566` | `write_iter` | modify | set STOP | unchecked | unchecked | **unchecked** |
| 12 | `i2c/blocking.rs:225` | `read` | modify | clear ACK | unchecked | unchecked | **unchecked** |
| 13 | `i2c/blocking.rs:234` | `read` | modify | set ACK | unchecked | corroborated | **partial** \*\* |
| 14 | `i2c/blocking.rs:240` | `read` | modify | set POS, set ACK | unchecked | unchecked | **unchecked** |
| 15 | `i2c/blocking.rs:243` | `read` | modify | clear ACK | unchecked | unchecked | **unchecked** |
| 16 | `i2c/blocking.rs:254` | `read` | modify | clear POS, clear ACK | unchecked | unchecked | **unchecked** |
| 17 | `i2c/blocking.rs:255` | `read` | modify | set ACK | unchecked | corroborated | **partial** \*\* |
| 18 | `i2c/blocking.rs:258` | `read` | modify | set ACK | unchecked | unchecked | **unchecked** |
| 19 | `i2c/blocking.rs:272` | `read` | modify | clear ACK | unchecked | unchecked | **unchecked** |
| 20 | `i2c/blocking.rs:280` | `read` | modify | set ACK | unchecked | unchecked | **unchecked** |

\* **Scan false positive.** The deterministic scan matched a `START`/`STOP`
*writer* earlier in the function (a `w.start().set_bit()` in `send_start`'s
sibling branch; an incidental accessor in `handle_dma_interrupt`) and mistook
it for a guard. Reading the code confirms no precondition wait exists before
the flagged line, so the judge is right and the final class is **unchecked**.
These are the two cases where the aggregate report over-counted (see note).

\*\* **Judge-only catch.** The guard here is a `STOP` wait hidden behind a
helper (`wait_for_stop()`), which the field-pattern scan cannot see; the judge
read the code and found it. Genuine **partial** (STOP only).

## What the functions do (the story behind the rows)

The gated sites fall into four groups:

- **Bring-up** (`i2c_init`, `init`, `reset`) — enable/disable the peripheral
  (`PE`) or software-reset it. No transaction is in flight, so there is
  nothing to wait on; all **unchecked**, and arguably benign.
- **Starting a transaction** (`prepare_write`, `prepare_read`, `send_start`) —
  set `START` (and `ACK`) to open a transfer. **These are the partial sites:**
  the HALs wait for `STOP` to finish first — stm32f4xx-hal even quotes the
  manual's reasoning in a comment above the wait — but never check `START` or
  `PEC`.
- **Ending / streaming** (`send_stop`, `write_iter`, `read_wo_prepare`,
  `write_wo_prepare`) — set `STOP` or push the next byte. All **unchecked**.
- **Byte-level read control** (`blocking.rs::read`, the DMA handlers) — toggle
  `ACK`/`POS` per byte during multi-byte reads and DMA interrupts. All
  **unchecked** except the two helper-hidden `STOP` waits.

## Summary

| final class | count | meaning |
|---|---:|---|
| fully corroborated (STOP + START + PEC) | **0** | no site checks the complete rule |
| partial (STOP wait only) | **8** | the rule was known; one third implemented |
| unchecked | **26** | the CR1 access runs with no precondition guard |
| **total sites** | **34** | 14 in stm32f4xx-hal, 20 in stm32f1xx-hal |

**Zero of 34 real call sites implement the full datasheet rule.** Eight wait
on `STOP` alone; the other twenty-six guard nothing. Every partial site checks
the *same* one of the three conditions (`STOP`) and never `START` or `PEC`, so
the coverage gap is systematic, not scattered.

### Reconciliation with `hal_corroboration.md`

The earlier aggregate reported **10 partial / 24 unchecked**. Re-adjudicating
each site against the HAL source corrects this to **8 partial / 26 unchecked**:
two f4 `dma.rs` disagreements (rows 10 and 14 above) were scan false positives
— writer-proxy matches, not real STOP waits — and belong in *unchecked*. This
is the same "scan over-credits via writer proxies" failure mode that
`hal_corroboration.md` itself documents; the aggregate simply mapped all ten
scan/judge disagreements to *partial* without re-checking those two. The
headline is unchanged and slightly stronger: still 0 fully corroborated, now
26 (not 24) sites with no guard at all.

## Reproduce

```bash
python applications/pac_codegen/experiments/corroboration.py   # regenerates out/*.jsonl
```

The per-site final class is derived from those artifacts plus reading the
enclosing function in each HAL source (function name, flagged-line CR1 action,
and the two scan-false-positive confirmations).
