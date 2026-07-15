// Golden output for applications/pac_codegen/rust_codegen.py (trait gating).
// Refresh after an intentional emitter change with:
//   .venv/bin/python applications/pac_codegen/rust_codegen.py \
//     applications/pac_codegen/constraint_test/stm32f405_i2c1.json \
//     --peripheral i2c1 --output /tmp/c.rs   # then paste below the marker
//@@LIDAR-GOLDEN-GENERATED@@
//! Compile-time access constraints for I2C1 CR1.
//!
//! Generated from datasheet constraints. Do not edit manually.
//!
//! A witness attests that the preconditions were OBSERVED TRUE in one
//! fresh volatile read; prefer `*_when_ready` (check + use in one call).

// === Witnesses ===
/// State witness authorizing one modify of CR1.
pub struct Cr1ModifyWitness { _priv: () }
/// State witness authorizing one write of CR1.
pub struct Cr1WriteWitness { _priv: () }

// === Error Type ===
/// A precondition that was not satisfied at check time.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Cr1ConstraintError {
    /// STOP cleared was required
    StopNotCleared,
    /// START cleared was required
    StartNotCleared,
    /// PEC cleared was required
    PecNotCleared,
}

// === Gates ===
impl crate::ModifyGate for super::cr1::CR1rs {
    type Witness = Cr1ModifyWitness;
}
impl crate::WriteGate for super::cr1::CR1rs {
    type Witness = Cr1WriteWitness;
}

// === Checks ===
impl crate::Reg<super::cr1::CR1rs> {
    /// Read CR1 once and check every modify precondition.
    ///
    /// # Constraint
    /// When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware. This is to avoid setting a second STOP, START or PEC request.
    #[inline(always)]
    pub fn check_modify_ready(&self) -> Result<Cr1ModifyWitness, Cr1ConstraintError> {
        let r = self.read();
        if !(r.stop().bit_is_clear()) {
            return Err(Cr1ConstraintError::StopNotCleared);
        }
        if !(r.start().bit_is_clear()) {
            return Err(Cr1ConstraintError::StartNotCleared);
        }
        if !(r.pec().bit_is_clear()) {
            return Err(Cr1ConstraintError::PecNotCleared);
        }
        Ok(Cr1ModifyWitness { _priv: () })
    }

    /// Read CR1 once and check every write precondition.
    ///
    /// # Constraint
    /// When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware. This is to avoid setting a second STOP, START or PEC request.
    #[inline(always)]
    pub fn check_write_ready(&self) -> Result<Cr1WriteWitness, Cr1ConstraintError> {
        let r = self.read();
        if !(r.stop().bit_is_clear()) {
            return Err(Cr1ConstraintError::StopNotCleared);
        }
        if !(r.start().bit_is_clear()) {
            return Err(Cr1ConstraintError::StartNotCleared);
        }
        if !(r.pec().bit_is_clear()) {
            return Err(Cr1ConstraintError::PecNotCleared);
        }
        Ok(Cr1WriteWitness { _priv: () })
    }

    /// Check and write in one call — the witness
    /// never escapes, so the check-to-write window is fixed by this body.
    #[inline(always)]
    pub fn write_when_ready<F>(&self, f: F) -> Result<<super::cr1::CR1rs as crate::RegisterSpec>::Ux, Cr1ConstraintError>
    where
        F: FnOnce(&mut crate::W<super::cr1::CR1rs>) -> &mut crate::W<super::cr1::CR1rs>,
    {
        let witness = self.check_write_ready()?;
        Ok(self.write_witnessed(f, witness))
    }

    /// Check and modify in one call — the witness never escapes.
    #[inline(always)]
    pub fn modify_when_ready<F>(&self, f: F) -> Result<<super::cr1::CR1rs as crate::RegisterSpec>::Ux, Cr1ConstraintError>
    where
        for<'w> F: FnOnce(&crate::R<super::cr1::CR1rs>, &'w mut crate::W<super::cr1::CR1rs>) -> &'w mut crate::W<super::cr1::CR1rs>,
    {
        let witness = self.check_modify_ready()?;
        Ok(self.modify_witnessed(f, witness))
    }

}
