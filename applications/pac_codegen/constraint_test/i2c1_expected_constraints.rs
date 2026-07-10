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
        let value = f(&mut crate::W {
            bits: <super::cr1::CR1rs as crate::Resettable>::RESET_VALUE
                & !<super::cr1::CR1rs as crate::Writable>::ONE_TO_MODIFY_FIELDS_BITMAP
                | <super::cr1::CR1rs as crate::Writable>::ZERO_TO_MODIFY_FIELDS_BITMAP,
            _reg: core::marker::PhantomData,
        })
        .bits;
        self.reg.register.set(value);
        value
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
        let bits = self.reg.register.get();
        let value = f(
            &crate::R {
                bits,
                _reg: core::marker::PhantomData,
            },
            &mut crate::W {
                bits: bits
                    & !<super::cr1::CR1rs as crate::Writable>::ONE_TO_MODIFY_FIELDS_BITMAP
                    | <super::cr1::CR1rs as crate::Writable>::ZERO_TO_MODIFY_FIELDS_BITMAP,
                _reg: core::marker::PhantomData,
            },
        )
        .bits;
        self.reg.register.set(value);
        value
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
}
