// Golden output for applications/pac_codegen/rust_codegen.py (trait gating).
// Refresh after an intentional emitter change with:
//   .venv/bin/python applications/pac_codegen/rust_codegen.py \
//     applications/pac_codegen/constraint_test/stm32f405_crc_idr.json \
//     --peripheral crc --output /tmp/c.rs   # then paste below the marker
//@@LIDAR-GOLDEN-GENERATED@@
//! Compile-time access constraints for CRC IDR.
//!
//! Generated from datasheet constraints. Do not edit manually.
//!
//! A witness attests that the preconditions were OBSERVED TRUE in one
//! fresh volatile read; prefer `*_when_ready` (check + use in one call).

// === Witnesses ===
/// Write-once capability for IDR: minted at most once per reset by `take_write_cap()`, consumed by `write_witnessed`.
pub struct IdrWriteWitness { _priv: () }

// === Gates ===
impl crate::WriteGate for super::idr::IDRrs {
    type Witness = IdrWriteWitness;
}

// === Checks ===
impl crate::Reg<super::idr::IDRrs> {
    /// Take the one-shot IDR write capability (at most once per reset);
    /// pass it to `write_witnessed`. Returns `None` if already taken.
    ///
    /// # Constraint
    /// IDR may be programmed only once after a system reset.
    #[inline(always)]
    pub fn take_write_cap(&self) -> Option<IdrWriteWitness> {
        static TAKEN: core::sync::atomic::AtomicBool =
            core::sync::atomic::AtomicBool::new(false);
        if TAKEN.swap(true, core::sync::atomic::Ordering::Relaxed) {
            None
        } else {
            Some(IdrWriteWitness { _priv: () })
        }
    }

}
