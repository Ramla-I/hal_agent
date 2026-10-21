// Golden output for applications/pac_codegen/rust_codegen.py (trait gating).
// Refresh after an intentional emitter change with:
//   .venv/bin/python applications/pac_codegen/rust_codegen.py \
//     applications/pac_codegen/constraint_test/stm32f405_gpioa_lckr.json \
//     --peripheral gpioa --output /tmp/c.rs   # then paste below the marker
//@@LIDAR-GOLDEN-GENERATED@@
//! Compile-time access constraints for GPIOA LCKR.
//!
//! Generated from datasheet constraints. Do not edit manually.
//!
//! A witness attests that the preconditions were OBSERVED TRUE in one
//! fresh volatile read; prefer `*_when_ready` (check + use in one call).

// === Witnesses ===
/// Sequence token: step 1 of 3 of the LCKR write sequence (handshake — raw write withheld).
pub struct LckrSeq0 { _priv: () }
/// Sequence token: step 2 of 3 of the LCKR write sequence (handshake — raw write withheld).
pub struct LckrSeq1 { _priv: () }
/// Sequence token: step 3 of 3 of the LCKR write sequence (handshake — raw write withheld).
pub struct LckrSeq2 { _priv: () }

// === Gates ===

// === Checks ===
impl crate::Reg<super::lckr::LCKRrs> {
    /// Sequence step 1 of 3 for LCKR (caller supplies the value).
    ///
    /// The raw `write` of this register is withheld; this ordered chain is
    /// the only safe path. Each step consumes the previous step's token.
    ///
    /// # Constraint
    /// LOCK key write sequence: write LCKK=1 with the port bits, then LCKK=0 with the same bits, then LCKK=1 again; the value of LCKR[15:0] must not change during the sequence.
    #[inline(always)]
    pub fn seq_step_0(&self, value: <super::lckr::LCKRrs as crate::RegisterSpec>::Ux) -> LckrSeq0 {
        // SAFETY: sanctioned sequence step; the token chain enforces order.
        unsafe { self.write_unwitnessed(|w| unsafe { w.bits(value) }); }
        LckrSeq0 { _priv: () }
    }

    /// Sequence step 2 of 3 for LCKR (caller supplies the value).
    #[inline(always)]
    pub fn seq_step_1(&self, _prev: LckrSeq0, value: <super::lckr::LCKRrs as crate::RegisterSpec>::Ux) -> LckrSeq1 {
        // SAFETY: sanctioned sequence step; the token chain enforces order.
        unsafe { self.write_unwitnessed(|w| unsafe { w.bits(value) }); }
        LckrSeq1 { _priv: () }
    }

    /// Sequence step 3 of 3 for LCKR (caller supplies the value).
    #[inline(always)]
    pub fn seq_step_2(&self, _prev: LckrSeq1, value: <super::lckr::LCKRrs as crate::RegisterSpec>::Ux) -> LckrSeq2 {
        // SAFETY: sanctioned sequence step; the token chain enforces order.
        unsafe { self.write_unwitnessed(|w| unsafe { w.bits(value) }); }
        LckrSeq2 { _priv: () }
    }

}
