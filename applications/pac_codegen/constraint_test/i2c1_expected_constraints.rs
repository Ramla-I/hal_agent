// Golden output for applications/pac_codegen/rust_codegen.py.
// Regenerate the generated section with the command documented in README.md.
//@@LIDAR-GOLDEN-GENERATED@@
//! Compile-time access constraints for I2C1 CR1.
//!
//! Generated from datasheet constraints. Do not edit manually.
//!
//! Each constrained operation requires its own affine composite proof.

// === Composite Proofs ===
// Private constructors ensure proofs only come from fresh verification.

/// Proof that CR1 is ready for a constrained write.
pub struct Cr1WriteReady(());

/// Proof that CR1 is ready for a constrained modify.
pub struct Cr1ModifyReady(());

// === Error Type ===

/// Errors returned when a precondition is not satisfied.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConstraintError {
    /// STOP is not cleared
    StopNotCleared,
    /// START is not cleared
    StartNotCleared,
    /// PEC is not cleared
    PecNotCleared,
}

impl crate::ConstrainedReg<super::cr1::CR1rs> {
    /// Read CR1 once and verify every write precondition.
    #[inline(always)]
    pub fn verify_write_ready(&self) -> Result<Cr1WriteReady, ConstraintError> {
        let r = self.reg.read();
        if !(r.stop().bit_is_clear()) {
            return Err(ConstraintError::StopNotCleared);
        }
        if !(r.start().bit_is_clear()) {
            return Err(ConstraintError::StartNotCleared);
        }
        if !(r.pec().bit_is_clear()) {
            return Err(ConstraintError::PecNotCleared);
        }
        Ok(Cr1WriteReady(()))
    }

    /// Read CR1 once and verify every modify precondition.
    #[inline(always)]
    pub fn verify_modify_ready(&self) -> Result<Cr1ModifyReady, ConstraintError> {
        let r = self.reg.read();
        if !(r.stop().bit_is_clear()) {
            return Err(ConstraintError::StopNotCleared);
        }
        if !(r.start().bit_is_clear()) {
            return Err(ConstraintError::StartNotCleared);
        }
        if !(r.pec().bit_is_clear()) {
            return Err(ConstraintError::PecNotCleared);
        }
        Ok(Cr1ModifyReady(()))
    }

    /// Explicitly bypass generated datasheet constraint enforcement.
    ///
    /// # Safety
    /// The caller accepts responsibility for intentionally overriding
    /// the hardware procedure documented by the datasheet.
    #[inline(always)]
    pub unsafe fn bypass_constraints(&self) -> &crate::Reg<super::cr1::CR1rs> {
        &self.reg
    }

    /// Datasheet constraints:
    /// - When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware. This is to avoid setting a second STOP, START or PEC request.
    #[inline(always)]
    pub fn write_constrained<F>(&self, f: F, _proof: Cr1WriteReady) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
    where
        F: FnOnce(&mut crate::W<super::cr1::CR1rs>) -> &mut crate::W<super::cr1::CR1rs>,
    {
        self.reg.write(f)
    }

    #[inline(always)]
    pub fn write<F>(&self, f: F, proof: Cr1WriteReady) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
    where
        F: FnOnce(&mut crate::W<super::cr1::CR1rs>) -> &mut crate::W<super::cr1::CR1rs>,
    {
        self.write_constrained(f, proof)
    }

    #[inline(always)]
    pub fn reset_constrained(&self, _proof: Cr1WriteReady) {
        self.reg.reset()
    }

    #[inline(always)]
    pub fn reset(&self, proof: Cr1WriteReady) {
        self.reset_constrained(proof)
    }

    #[inline(always)]
    pub fn write_with_zero_constrained<F>(&self, f: F, _proof: Cr1WriteReady) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
    where
        F: FnOnce(&mut crate::W<super::cr1::CR1rs>) -> &mut crate::W<super::cr1::CR1rs>,
    {
        self.reg.write_with_zero(f)
    }

    #[inline(always)]
    pub fn write_with_zero<F>(&self, f: F, proof: Cr1WriteReady) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
    where
        F: FnOnce(&mut crate::W<super::cr1::CR1rs>) -> &mut crate::W<super::cr1::CR1rs>,
    {
        self.write_with_zero_constrained(f, proof)
    }

    #[inline(always)]
    pub fn from_write_constrained<F, T>(&self, f: F, _proof: Cr1WriteReady) -> T
    where
        F: FnOnce(&mut crate::W<super::cr1::CR1rs>) -> T,
    {
        self.reg.from_write(f)
    }

    #[inline(always)]
    pub fn from_write<F, T>(&self, f: F, proof: Cr1WriteReady) -> T
    where
        F: FnOnce(&mut crate::W<super::cr1::CR1rs>) -> T,
    {
        self.from_write_constrained(f, proof)
    }

    /// Datasheet constraints:
    /// - When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware. This is to avoid setting a second STOP, START or PEC request.
    #[inline(always)]
    pub fn modify_constrained<F>(&self, f: F, _proof: Cr1ModifyReady) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
    where
        for<'w> F: FnOnce(&crate::R<super::cr1::CR1rs>, &'w mut crate::W<super::cr1::CR1rs>) -> &'w mut crate::W<super::cr1::CR1rs>,
    {
        self.reg.modify(f)
    }

    #[inline(always)]
    pub fn modify<F>(&self, f: F, proof: Cr1ModifyReady) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
    where
        for<'w> F: FnOnce(&crate::R<super::cr1::CR1rs>, &'w mut crate::W<super::cr1::CR1rs>) -> &'w mut crate::W<super::cr1::CR1rs>,
    {
        self.modify_constrained(f, proof)
    }

    #[inline(always)]
    pub fn from_modify_constrained<F, T>(&self, f: F, _proof: Cr1ModifyReady) -> T
    where
        for<'w> F: FnOnce(&crate::R<super::cr1::CR1rs>, &'w mut crate::W<super::cr1::CR1rs>) -> T,
    {
        self.reg.from_modify(f)
    }

    #[inline(always)]
    pub fn from_modify<F, T>(&self, f: F, proof: Cr1ModifyReady) -> T
    where
        for<'w> F: FnOnce(&crate::R<super::cr1::CR1rs>, &'w mut crate::W<super::cr1::CR1rs>) -> T,
    {
        self.from_modify_constrained(f, proof)
    }

}
