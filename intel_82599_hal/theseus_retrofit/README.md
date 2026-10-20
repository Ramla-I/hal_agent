# Theseus retrofit — the compile-based recall eval + gate adoption

The case study's end-to-end evaluation: plug the generated HAL into the real
Theseus `ixgbe` driver and build it.

- **`driver_diff_gated.patch`** (committed) — the driver-side edits that make
  Theseus compile against the **constraint-gated** HAL (`pipeline/s4_emit_hal.py
  --gated`): 2 files, +40/−18 lines. Each hunk adopts one extracted access
  constraint (FCTRL/TDH/RXCSUM witness gates, the CRC-strip coupled setter, the
  DMATXCTL/EIAC `write_preserving` guards). This is the measured cost of the
  enforcement arm. With the plain structural HAL the driver builds unchanged.
- **`driver_diff_gated_minted.patch`** (committed) — the same adoption for the
  **provenance-hardened** HAL (`pipeline/s4b_emit_hal_minted.py`, output
  `hal_out/<run>-gated-minted/`). Identical to `driver_diff_gated.patch` except
  the witness-minting lines route through the prerequisite register's newtype
  (`RxctrlRxenCleared::establish(&mut regs.rxctrl)` → `regs.rxctrl.clear_rxen()`,
  the two RXEN windows + the TXDCTL mint + the releases). Same +40/−18; verified
  green with the pinned toolchain.
- **`theseus_clone/`** (gitignored, ~900 MB) — a checkout of
  `theseus-os/Theseus` @ `1fbfe567` (see `../reference/COMMIT.txt`), not
  committed; recreate it with the recipe below.

## Recreate + run

```bash
cd theseus_retrofit
git clone https://github.com/theseus-os/Theseus theseus_clone
cd theseus_clone && git checkout 1fbfe567 && git submodule update --init --recursive

# structural recall: swap in the plain HAL, build the unmodified driver
cp ../../pipeline/hal_out/<run>/regs.rs kernel/ixgbe/src/regs.rs
RUST_TARGET_PATH=$PWD/cfg cargo check -p ixgbe \
  -Z unstable-options -Z build-std=core,alloc \
  -Z build-std-features=compiler-builtins-mem --target x86_64-unknown-theseus

# enforcement: swap in the gated HAL and apply the driver diff
cp ../../pipeline/hal_out/<run>-gated/regs.rs kernel/ixgbe/src/regs.rs
git apply ../driver_diff_gated.patch
# cargo check again -> green

# provenance-hardened variant: minted HAL + minted driver diff
cp ../../pipeline/hal_out/<run>-gated-minted/regs.rs kernel/ixgbe/src/regs.rs
git apply ../driver_diff_gated_minted.patch
# cargo check again -> green
```
