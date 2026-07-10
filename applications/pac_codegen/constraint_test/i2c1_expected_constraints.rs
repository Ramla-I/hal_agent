// Golden output for applications/pac_codegen/rust_codegen.py.
// Regenerate the generated section with the command documented in README.md.
//@@LIDAR-GOLDEN-GENERATED@@
//! Compile-time access constraints for I2C1 CR1.
//!
//! Generated from datasheet constraints. Do not edit manually.
//!
//! This module provides composite-proof safe write methods that enforce
//! hardware preconditions at the type level.

// === Composite Proof ===
// A zero-sized, non-Copy proof that all preconditions were checked.

/// Proof that CR1 is ready for a constrained write operation.
/// The private constructor ensures this can only be obtained by verification.
pub struct Cr1WriteReady(());

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

// === Constrained Write ===

/// Safe write to CR1 that enforces datasheet constraints.
///
/// # Constraint
/// When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware. This is to avoid setting a second STOP, START or PEC request.
///
/// # Usage
/// ```no_run
/// let proof = i2c1.cr1().verify_write_ready().unwrap();
/// i2c1.cr1().write_constrained(|w| w, proof);
/// ```
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

    #[inline(always)]
    pub fn write_constrained<F>(&self, f: F, _proof: Cr1WriteReady) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
    where
        F: FnOnce(&mut crate::W<super::cr1::CR1rs>) -> &mut crate::W<super::cr1::CR1rs>,
    {
        self.reg.write(f)
    }

    /// Safe read-modify-write to CR1 that enforces datasheet constraints.
    ///
    /// # Constraint
    /// When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware. This is to avoid setting a second STOP, START or PEC request.
    #[inline(always)]
    pub fn modify_constrained<F>(&self, f: F, _proof: Cr1WriteReady) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
    where
        for<'w> F: FnOnce(&crate::R<super::cr1::CR1rs>, &'w mut crate::W<super::cr1::CR1rs>) -> &'w mut crate::W<super::cr1::CR1rs>,
    {
        self.reg.modify(f)
    }

    /// Writes to CR1 with constraint verification.
    ///
    /// This method shadows `Reg::write()` and requires a composite proof,
    /// enforcing hardware constraints at compile time.
    #[inline(always)]
    pub fn write<F>(&self, f: F, proof: Cr1WriteReady) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
    where
        F: FnOnce(&mut crate::W<super::cr1::CR1rs>) -> &mut crate::W<super::cr1::CR1rs>,
    {
        self.write_constrained(f, proof)
    }

    /// Reset CR1 after constraint verification.
    #[inline(always)]
    pub fn reset_constrained(&self, _proof: Cr1WriteReady) {
        self.reg.reset()
    }

    #[inline(always)]
    pub fn reset(&self, proof: Cr1WriteReady) {
        self.reset_constrained(proof)
    }

    /// Write from zero after constraint verification.
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

    /// Write and return a closure-produced value after verification.
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

    /// Modifies CR1 via read-modify-write with constraint verification.
    ///
    /// This method shadows `Reg::modify()` and requires a composite proof,
    /// enforcing hardware constraints at compile time.
    #[inline(always)]
    pub fn modify<F>(&self, f: F, proof: Cr1WriteReady) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
    where
        for<'w> F: FnOnce(&crate::R<super::cr1::CR1rs>, &'w mut crate::W<super::cr1::CR1rs>) -> &'w mut crate::W<super::cr1::CR1rs>,
    {
        self.modify_constrained(f, proof)
    }

    /// Read-modify-write and return a closure-produced value.
    #[inline(always)]
    pub fn from_modify_constrained<F, T>(&self, f: F, _proof: Cr1WriteReady) -> T
    where
        for<'w> F: FnOnce(&crate::R<super::cr1::CR1rs>, &'w mut crate::W<super::cr1::CR1rs>) -> T,
    {
        self.reg.from_modify(f)
    }

    #[inline(always)]
    pub fn from_modify<F, T>(&self, f: F, proof: Cr1WriteReady) -> T
    where
        for<'w> F: FnOnce(&crate::R<super::cr1::CR1rs>, &'w mut crate::W<super::cr1::CR1rs>) -> T,
    {
        self.from_modify_constrained(f, proof)
    }
}
