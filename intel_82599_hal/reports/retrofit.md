# Retrofit study — can other ixgbe drivers use the generated HAL?

**Question** (Ramla): can ixy.rs, RedLeaf's ixgbe, and Redox's ixgbed be
retrofitted to use the intralingual HAL we generated for Theseus?

**Answer: yes.** Register coverage is already complete for all three, and the
retrofit is demonstrated end-to-end for ixy.rs: a full mechanical port that
compiles (`cargo check` + `cargo build`) with the constraint gates active.

## Register coverage (analyze_drivers.py — address-based join, names only cross-checked)

| driver | registers used | matched in Table 8-2 | covered by the generated 75 | gated regs touched (write sites) |
|---|---|---|---|---|
| ixy.rs | 41 | 39* | 39* | **7 (14)** |
| Redox ixgbed | 30 | 28* | 28* | 4 (4) |
| RedLeaf ixgbe | 17 | 17 | 17 | 1 (5) |

\* the only unmatched addresses are RAL/RAH read through the legacy 82598
`0x5400` alias (observation 3) — the registers themselves are modeled at their
documented `0xA200` home, so effective coverage is 41/41 and 30/30.

Coverage is complete because the Theseus-derived 75-register target is a
superset of what these minimal drivers touch; any register outside it would be
one more entry in the generation list (the pipeline is push-button per
register). All three drivers write TDH — every retrofit exercises the gates.

## Demonstrated: the ixy.rs port (`port_ixy.py`, 85 asserted replacements)

- The 7 generated region structs are overlaid on ixy's mapped BAR0; ixy's six
  offset-arithmetic MMIO helpers (`get_reg32`/`set_reg32`/`set_flags32`/…) are
  deleted — the raw-pointer unsafety collapses into seven typed casts, and all
  register access becomes typed (offsets, widths, RO/WO, arrays, gates).
- Uses the `--plain` HAL variant (no zerocopy dependency) + crates.io
  `volatile 0.2` — the Theseus-specific bits are packaging config, not
  architecture.
- **Gates active in a second OS's driver:** the RXEN-cleared witness spans
  ixy's rx-init filter window; all 3 FCTRL writes take the witness token; TDH init
  writes mint the queue-disabled witness; the two independent CRC-strip bit-ORs
  become the coupled `set_rxcrcstrp_crcstrip()`; EIAC writes go through the
  never-set clamp; DMATXCTL through the VT hold.
- **Violation demo:** deleting the single `RxctrlRxenCleared::establish` line
  makes both dependent sites fail to compile (E0425).

## What the retrofit exposed in the foreign drivers (leads)

1. **ixy toggles promiscuous mode by rewriting FCTRL while the receiver is
   live** — the datasheet requires RXEN=0 around filter updates. The gate
   would not compile it; the port adds the disable/re-enable window.
2. **ixy's `set_reg32(IXGBE_DMATXCTL, TE)` is an absolute write that zeroes
   DMATXCTL.VT** (the 802.3ac tag, default 0x8100, documented "must not
   change"; Linux does a read-modify-write here). The hold-encoding
   auto-repairs it: `write_preserving(TE)` keeps VT.
3. **ixy and Redox read the MAC address via the 82598-era `0x5400` RAL/RAH
   alias** (Linux ixgbe.h heritage) — an address the 82599 PF BAR0 register
   summary does not document. The typed port normalizes to the documented
   `0xA200` bank.
4. All three use the 16-entry 82598-compat SRRCTL bank at `0x2100` (alias
   range; the primary bank is `0x1014+0x40*n`). RedLeaf additionally carries a
   dormant `STATUS = 0x00004` enum entry (that offset is CTRL's alias; STATUS
   is 0x8) and performs **64-bit volatile reads of 32-bit registers**
   (`read_reg_idx` reads the neighbouring register too — a hazard next to
   read-to-clear registers).

## Feasibility per driver

- **ixy.rs — done** (compiling; runtime validation needs 82599 hardware).
- **Redox ixgbed** — same Linux-style idiom, ~30 sites, single queue: the
  smallest mechanical port; verifying the compile needs the Redox build env.
- **RedLeaf** — structurally the easiest target: every access already funnels
  through one enum-keyed layer, so the retrofit can replace that layer's
  internals with the typed structs; needs RedLeaf's no_std build env.

## Caveats

- The 7-struct packaging is Theseus-shaped (split for virtualization); it is
  `packaging.json` config, not architecture — a flat packaging would serve
  the others equally.
- The model covers the first register banks (as the Theseus driver does):
  queue ids ≥ 64 and EITR indices ≥ 24 would need the second banks added
  (one geometry entry each). Typed indexing makes an out-of-range access a
  loud panic instead of a silent write into a neighbouring register's space.
- Witnesses remain type-level, not instance-bound (same as the MCU arm).
