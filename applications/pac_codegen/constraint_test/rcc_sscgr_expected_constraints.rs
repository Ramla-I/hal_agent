// Golden output for applications/pac_codegen/rust_codegen.py (trait gating).
// Refresh after an intentional emitter change with:
//   .venv/bin/python applications/pac_codegen/rust_codegen.py \
//     applications/pac_codegen/constraint_test/stm32f405_rcc_sscgr.json \
//     --peripheral rcc --output /tmp/c.rs   # then paste below the marker
//@@LIDAR-GOLDEN-GENERATED@@
//! Compile-time access constraints for RCC SSCGR.
//!
//! Generated from datasheet constraints. Do not edit manually.
//!
//! A witness attests that the preconditions were OBSERVED TRUE in one
//! fresh volatile read; prefer `*_when_ready` (check + use in one call).

// === Witnesses ===
/// State witness authorizing one modify of SSCGR.
pub struct SscgrModifyWitness { _priv: () }
/// State witness authorizing one write of SSCGR.
pub struct SscgrWriteWitness { _priv: () }

// === Error Type ===
/// A precondition that was not satisfied at check time.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SscgrConstraintError {
    /// RCC_CR.PLLON cleared was required
    CrPllonNotCleared,
}

// === Gates ===
impl crate::ModifyGate for super::sscgr::SSCGRrs {
    type Witness = SscgrModifyWitness;
}
impl crate::WriteGate for super::sscgr::SSCGRrs {
    type Witness = SscgrWriteWitness;
}

// === Checks ===
impl crate::Reg<super::sscgr::SSCGRrs> {
    /// Read the source register(s) and every source register once and check every modify precondition.
    ///
    /// # Constraint
    /// The RCC_SSCGR register must be written either before the main PLL is enabled or after the main PLL disabled. To write before setting CR[24]=PLLON bit.
    #[inline(always)]
    pub fn check_modify_ready(&self, cr: &crate::Reg<super::cr::CRrs>) -> Result<SscgrModifyWitness, SscgrConstraintError> {
        let r_cr = cr.read();
        if !(r_cr.pllon().bit_is_clear()) {
            return Err(SscgrConstraintError::CrPllonNotCleared);
        }
        Ok(SscgrModifyWitness { _priv: () })
    }

    /// Read the source register(s) and every source register once and check every write precondition.
    ///
    /// # Constraint
    /// The RCC_SSCGR register must be written either before the main PLL is enabled or after the main PLL disabled. To write before setting CR[24]=PLLON bit.
    #[inline(always)]
    pub fn check_write_ready(&self, cr: &crate::Reg<super::cr::CRrs>) -> Result<SscgrWriteWitness, SscgrConstraintError> {
        let r_cr = cr.read();
        if !(r_cr.pllon().bit_is_clear()) {
            return Err(SscgrConstraintError::CrPllonNotCleared);
        }
        Ok(SscgrWriteWitness { _priv: () })
    }

    /// Check and write in one call — the witness never escapes,
    /// so the check-to-write window is fixed by this body.
    #[inline(always)]
    pub fn write_when_ready<F>(&self, f: F, cr: &crate::Reg<super::cr::CRrs>) -> Result<<super::sscgr::SSCGRrs as crate::RegisterSpec>::Ux, SscgrConstraintError>
    where
        F: FnOnce(&mut crate::W<super::sscgr::SSCGRrs>) -> &mut crate::W<super::sscgr::SSCGRrs>,
    {
        let witness = self.check_write_ready(cr)?;
        Ok(self.write_witnessed(f, witness))
    }

    /// Check and modify in one call — the witness never escapes.
    #[inline(always)]
    pub fn modify_when_ready<F>(&self, f: F, cr: &crate::Reg<super::cr::CRrs>) -> Result<<super::sscgr::SSCGRrs as crate::RegisterSpec>::Ux, SscgrConstraintError>
    where
        for<'w> F: FnOnce(&crate::R<super::sscgr::SSCGRrs>, &'w mut crate::W<super::sscgr::SSCGRrs>) -> &'w mut crate::W<super::sscgr::SSCGRrs>,
    {
        let witness = self.check_modify_ready(cr)?;
        Ok(self.modify_witnessed(f, witness))
    }

}
