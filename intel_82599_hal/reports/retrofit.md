# Retrofit study — can other ixgbe drivers use the generated HAL?

**Question** (Ramla): can ixy.rs, RedLeaf's ixgbe, and Redox's ixgbed be
retrofitted to use the intralingual HAL we generated for Theseus?

**Answer: yes — all three now compile against it.** ixy.rs and Redox ixgbed
via full call-site ports; RedLeaf via a layer retarget with zero call-site
changes. Compile-testing needed no OS build environment for any of them.

## Register coverage (analyze_drivers.py — address-based join over the PRISTINE sources)

| driver | registers used | matched in Table 8-2 | covered by the generated 75 | gated regs touched (write sites) |
|---|---|---|---|---|
| ixy.rs | 41 | 39* | 39* | **7 (14)** |
| Redox ixgbed | 37 | 35* | 35* | **7 (9)** |
| RedLeaf ixgbe | 17 | 17 | 17 | 1 (5) |

\* the only unmatched addresses are RAL/RAH read through the legacy 82598
`0x5400` alias (observation 3) — the registers themselves are modeled at their
documented `0xA200` home, so effective coverage is 41/41 and 37/37.

Coverage is complete because the Theseus-derived 75-register target is a
superset of what these minimal drivers touch; any register outside it would be
one more entry in the generation list. All three drivers write TDH — every
retrofit exercises the gates. (Two analyzer defects were found and fixed while
finalizing: Redox's `write_flag`/`clear_flag` helpers were missing from the
write-helper list — its first-pass numbers under-counted — and `wait_write_reg`
polls had matched their embedded `write_reg` and been misread as writes.)

## Compile-test recipes (no OS build env, no booting)

- **ixy.rs**: plain `cargo check`/`cargo build` on Linux.
- **Redox**: `cargo check -p ixgbed` in the `base` workspace on Linux — its
  pinned nightly auto-installs and every dep compiles on the host.
- **RedLeaf**: pinned `nightly-2021-12-15` (rustup auto-installs) + two setup
  steps: generate its IDL interface crate (`git submodule update --init
  tools/redIDL`, install `cargo-expand`, `make -C interface`) and pin
  era-appropriate dep versions (`cargo update -p quote --precise 1.0.10`,
  `syn 1.0.82`, `proc-macro2 1.0.34`, `byteorder 1.4.3`, `log 0.4.14`);
  then `cargo check` in `lib/devices/ixgbe`.

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

1. **FCTRL gate false positive (not a bug).** The FCTRL write-while-`RXEN=0`
   gate fires at ixy's `set_promisc` FCTRL write, but it is **not** a bug:
   `init_rx` clears RXCTRL.RXEN just before the write and re-enables it just
   after (`set_promisc` is private and only called there). The whole-register
   witness is local to the write site and can't see the precondition established
   in the enclosing function, so it flags a compliant write; the port threads
   the witness anyway (redundant but valid). Same story in Redox.
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

## Demonstrated: the Redox ixgbed port (`port_redox.py`, 67 asserted replacements)

Same shape as ixy: the four offset helpers deleted, seven typed casts, all 52+
sites ported, witnesses threaded (RXEN window over rx-init — Redox's FCTRL
writes sit inside that disabled window too, so the gate firing there is the
same false positive as ixy, not a bug; TDH
witness; CRC-strip coupling; EIAC clamp; **DMATXCTL hold — Redox has ixy's
exact absolute `DMATXCTL = TE` write, so the VT-clobber bug exists in a second
driver and is auto-repaired the same way**; RedLeaf's domain driver carries the
identical write at `device.rs:294`, making it a **third** codebase with the
bug). `cargo check -p ixgbed` green;
violation demo: removing the establish line → E0425 at both dependent sites.
Semantic note: Redox's `write_reg` did a volatile read-back after every write
(posted-write flush); the typed writes do not — matching the Theseus
reference semantics.

## Demonstrated: the RedLeaf retarget (`port_redleaf.py`, layer-internal, zero call-site changes)

RedLeaf funnels all access through one enum-keyed layer, so Tier A replaces
only that layer's internals (~3 function bodies + typed accessors) under the
unchanged enum API. `cargo check` green on the pinned 2021 nightly. What the
retarget fixed by construction:
1. **`RDLEN` was declared with stride `0x60` instead of `0x40`** — for any
   queue > 0 the raw math would have accessed RXDCTL of that queue instead of
   RDLEN (dormant only because RedLeaf uses queue 0). A new finding, spotted
   by laying the declaration against the typed model.
2. The 64-bit volatile reads of 32-bit registers are gone (typed u32 access);
   the raw-fallback arms for the few unmodeled stats registers now use
   correct 32-bit reads too.
3. The dormant `STATUS = 0x00004` entry (CTRL's alias offset) is bypassed —
   the typed arm reads the real STATUS at 0x8.
4. SRRCTL/DCA_TXCTRL normalize from legacy 82598-compat banks to the
   documented primary banks.
Gates apply force-the-action style inside the layer (as in Theseus's
`set_tdh`): `write_reg_idx(Tdh, ...)` mints the queue-disabled witness;
scalar FCTRL writes establish/release the RXEN window. Registers outside the
75-register model (19 stats scalars, TxpbThresh, Qptc, Rxmpc, RAL/RAH beyond
entry 0) keep a documented raw path. Tier B (call-site port, ~65 sites) stays
available if call-site gate visibility is wanted for RedLeaf too.

**Two RedLeaf crates — library vs. domain.** The retarget above covers
`lib/devices/ixgbe` (crate `ixgbe_device`): the register map + raw
`read_reg`/`write_reg` + per-queue init primitives + datapath — where the three
structure findings above live. RedLeaf's *actual* driver is a separate crate,
`domains/sys/driver/ixgbe` (crate `ixgbe`), a fault-isolated RedLeaf **domain**
that `path`-depends on `ixgbe_device` and adds the init *sequence* plus the
RPC/`RRef` network interface. That domain carries one constraint bug the library
layer does not: **`device.rs:294`, after `init_tx()`, does
`write_reg(IxgbeRegs::DMATXCTL, IXGBE_DMATXCTL_TE)`** — an absolute write of `0x1`
that zeroes DMATXCTL.VT, the same VT-clobber as ixy/Redox (the library layer
never writes DMATXCTL).

**Compile-verified (the domain crate too).** We built the domain crate against
the gated HAL — `cargo rcheck -p ixgbe` from `domains/` on the pinned
nightly-2021-12-15 (custom `x86_64-unknown-redleaf` target, build-std; needs the
`smoltcp`/`hashes` submodules initialized) — and both `ixgbe_device` (library)
and `ixgbe` (domain) check **green**. The DMATXCTL VT-clobber is then a
compile-time guarantee: the gated `GatedDmatxctl` type exposes only `read()` and
`write_preserving()` — **no raw `write()`** — so the enum-keyed access layer
*must* preserve VT. Pointing the `DMATXCTL` arm of `write_reg` at a raw
`.write(v)` (i.e. re-introducing the clobber) fails to compile with
`error[E0599]: no method named 'write' found for struct GatedDmatxctl`. Unlike
ixy/Redox the error surfaces inside the access layer rather than at the
`device.rs:294` call site, because RedLeaf routes every scalar write through the
uniform `write_reg` (which the retarget fixes once, for all callers).

## Caveats

- The 7-struct packaging is Theseus-shaped (split for virtualization); it is
  `config/packaging.json` config, not architecture — a flat packaging would serve
  the others equally.
- The model covers the first register banks (as the Theseus driver does):
  queue ids ≥ 64 and EITR indices ≥ 24 would need the second banks added
  (one geometry entry each). Typed indexing makes an out-of-range access a
  loud panic instead of a silent write into a neighbouring register's space.
- Witnesses remain type-level, not instance-bound (same as the MCU arm).
