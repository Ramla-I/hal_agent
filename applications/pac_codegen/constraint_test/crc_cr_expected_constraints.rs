// Golden output for applications/pac_codegen/rust_codegen.py (trait gating).
// Refresh after an intentional emitter change with:
//   .venv/bin/python applications/pac_codegen/rust_codegen.py \
//     applications/pac_codegen/constraint_test/stm32f405_crc_cr.json \
//     --peripheral crc --output /tmp/c.rs   # then paste below the marker
//@@LIDAR-GOLDEN-GENERATED@@
//! Compile-time access constraints for CRC CR.
//!
//! Generated from datasheet constraints. Do not edit manually.
//!
//! A witness attests that the preconditions were OBSERVED TRUE in one
//! fresh volatile read; prefer `*_when_ready` (check + use in one call).

// === Witnesses ===
/// Delay OBLIGATION for writing CR — minted by `await_delay()`, consumed by `write_witnessed`.
///
/// Holding it is NOT proof the delay elapsed: after the write of CR the caller
/// MUST wait at least 4 AHB clock cycles before this write; the HAL performs that wait.
#[must_use = "a delay obligation: you must wait at least 4 AHB clock cycles after the write of CR before writing CR — the HAL owns the wait"]
pub struct CrDelayWitness { _priv: () }

// === Gates ===
impl crate::WriteGate for super::cr::CRrs {
    type Witness = CrDelayWitness;
}

// === Checks ===
impl crate::Reg<super::cr::CRrs> {
    /// Acknowledge the post-`write of CR` delay and obtain the obligation
    /// witness required to write CR (its raw `write` is withheld).
    ///
    /// # OBLIGATION (not proof)
    /// This does NOT verify the wait. After the write of CR you MUST wait at
    /// least 4 AHB clock cycles before calling `write_witnessed`; performing that
    /// wait is the HAL's responsibility. The PAC gates only the ORDERING.
    ///
    /// # Constraint
    /// At least four AHB clock cycles are required between two consecutive writes to this register.
    #[inline(always)]
    #[must_use]
    pub fn await_delay(&self) -> CrDelayWitness {
        CrDelayWitness { _priv: () }
    }

}
