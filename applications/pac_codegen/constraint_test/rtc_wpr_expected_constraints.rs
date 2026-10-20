// Golden output for applications/pac_codegen/rust_codegen.py (trait gating).
// Refresh after an intentional emitter change with:
//   .venv/bin/python applications/pac_codegen/rust_codegen.py \
//     applications/pac_codegen/constraint_test/stm32f405_rtc_wpr.json \
//     --peripheral rtc --output /tmp/c.rs   # then paste below the marker
//@@LIDAR-GOLDEN-GENERATED@@
//! Compile-time access constraints for RTC WPR.
//!
//! Generated from datasheet constraints. Do not edit manually.
//!
//! A witness attests that the preconditions were OBSERVED TRUE in one
//! fresh volatile read; prefer `*_when_ready` (check + use in one call).

// === Witnesses ===
/// Sequence token: step 1 of 2 of the WPR write sequence (handshake — raw write withheld).
pub struct WprSeq0 { _priv: () }
/// Sequence token: step 2 of 2 of the WPR write sequence (handshake — raw write withheld).
pub struct WprSeq1 { _priv: () }

// === Gates ===

// === Checks ===
impl crate::Reg<super::wpr::WPRrs> {
    /// Sequence step 1 of 2 for WPR (writes 0xca).
    ///
    /// The raw `write` of this register is withheld; this ordered chain is
    /// the only safe path. Each step consumes the previous step's token.
    ///
    /// # Constraint
    /// The RTC registers are write-protected. Writing 0xCA then 0x53 to the WPR key register unlocks them; any other value re-enables the protection.
    #[inline(always)]
    pub fn seq_step_0(&self) -> WprSeq0 {
        // SAFETY: sanctioned sequence step; the token chain enforces order.
        unsafe { self.write_unwitnessed(|w| unsafe { w.bits(0xca) }); }
        WprSeq0 { _priv: () }
    }

    /// Sequence step 2 of 2 for WPR (writes 0x53).
    #[inline(always)]
    pub fn seq_step_1(&self, _prev: WprSeq0) -> WprSeq1 {
        // SAFETY: sanctioned sequence step; the token chain enforces order.
        unsafe { self.write_unwitnessed(|w| unsafe { w.bits(0x53) }); }
        WprSeq1 { _priv: () }
    }

}
