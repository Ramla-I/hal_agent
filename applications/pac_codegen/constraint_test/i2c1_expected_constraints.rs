// =============================================================================
// i2c1_expected_constraints.rs
//
// GOLDEN reference output for the PAC constraint code generator.
//
// This is the exact Rust module that `rust_codegen.py` must emit for the I2C1
// CR1 access constraints described in `stm32f405_i2c1.json` (same folder).
// `test_codegen.py` regenerates that module and diffs it, line for line, against
// the generated section below the marker line — so an unintended change to the
// code generator (or to the shared schema in `defs.py`) is caught immediately,
// before it can reach the PAC.
//
// This file is test data only: the `constraint_test` crate does NOT compile it
// (cargo only builds `src/`).
//
// Everything ABOVE the marker line is an ignored, human-readable header.
// Everything BELOW it is compared verbatim. If you change `rust_codegen.py` on
// purpose, refresh the generated section by running, from
// `applications/pac_codegen/`:
//
//     python rust_codegen.py constraint_test/stm32f405_i2c1.json \
//         --peripheral i2c1 --output /tmp/new.rs
//
// then replacing everything below the marker line with the contents of
// /tmp/new.rs.
// =============================================================================
//@@LIDAR-GOLDEN-GENERATED@@
//! Compile-time access constraints for I2C1 CR1.
//!
//! Generated from datasheet constraints. Do not edit manually.
//!
//! This module provides witness-token-based safe write methods that enforce
//! hardware preconditions at the type level.

// === Witness Tokens ===
// Zero-sized types that prove a precondition has been verified.

/// Proof that STOP is cleared in CR1.
/// This token is consumed by `write_constrained()` to enforce the
/// precondition at compile time.
pub struct StopClearedToken(());

/// Proof that START is cleared in CR1.
/// This token is consumed by `write_constrained()` to enforce the
/// precondition at compile time.
pub struct StartClearedToken(());

/// Proof that PEC is cleared in CR1.
/// This token is consumed by `write_constrained()` to enforce the
/// precondition at compile time.
pub struct PecClearedToken(());

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

// === Verification Methods ===
// Methods on cr1::R to verify preconditions and obtain tokens.

impl super::cr1::R {
    /// Verify that STOP is cleared and obtain a proof token.
    ///
    /// Returns `Ok(StopClearedToken)` if the precondition holds,
    /// `Err(ConstraintError::StopNotCleared)` otherwise.
    #[inline(always)]
    pub fn verify_stop_cleared(&self) -> Result<StopClearedToken, ConstraintError> {
        let r = self;
        if r.stop().bit_is_clear() {
            Ok(StopClearedToken(()))
        } else {
            Err(ConstraintError::StopNotCleared)
        }
    }

    /// Verify that START is cleared and obtain a proof token.
    ///
    /// Returns `Ok(StartClearedToken)` if the precondition holds,
    /// `Err(ConstraintError::StartNotCleared)` otherwise.
    #[inline(always)]
    pub fn verify_start_cleared(&self) -> Result<StartClearedToken, ConstraintError> {
        let r = self;
        if r.start().bit_is_clear() {
            Ok(StartClearedToken(()))
        } else {
            Err(ConstraintError::StartNotCleared)
        }
    }

    /// Verify that PEC is cleared and obtain a proof token.
    ///
    /// Returns `Ok(PecClearedToken)` if the precondition holds,
    /// `Err(ConstraintError::PecNotCleared)` otherwise.
    #[inline(always)]
    pub fn verify_pec_cleared(&self) -> Result<PecClearedToken, ConstraintError> {
        let r = self;
        if r.pec().bit_is_clear() {
            Ok(PecClearedToken(()))
        } else {
            Err(ConstraintError::PecNotCleared)
        }
    }

}

// === Constrained Write ===

/// Safe write to CR1 that enforces datasheet constraints.
///
/// # Constraint
/// When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware. This is to avoid setting a second STOP, START or PEC request.
///
/// # Usage
/// ```no_run
/// let r = i2c1.cr1().read();
/// let stop_token = r.verify_stop_cleared().unwrap();
/// let start_token = r.verify_start_cleared().unwrap();
/// let pec_token = r.verify_pec_cleared().unwrap();
/// i2c1.cr1().write_constrained(|w| w, stop_token, start_token, pec_token);
/// ```
impl crate::ConstrainedReg<super::cr1::CR1rs> {
    #[inline(always)]
    pub fn write_constrained<F>(&self, f: F, _stop_token: StopClearedToken, _start_token: StartClearedToken, _pec_token: PecClearedToken) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
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
    pub fn modify_constrained<F>(&self, f: F, _stop_token: StopClearedToken, _start_token: StartClearedToken, _pec_token: PecClearedToken) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
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
    /// This method shadows `Reg::write()` and requires witness tokens,
    /// enforcing hardware constraints at compile time.
    #[inline(always)]
    pub fn write<F>(&self, f: F, _stop_token: StopClearedToken, _start_token: StartClearedToken, _pec_token: PecClearedToken) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
    where
        F: FnOnce(&mut crate::W<super::cr1::CR1rs>) -> &mut crate::W<super::cr1::CR1rs>,
    {
        self.write_constrained(f, _stop_token, _start_token, _pec_token)
    }

    /// Modifies CR1 via read-modify-write with constraint verification.
    ///
    /// This method shadows `Reg::modify()` and requires witness tokens,
    /// enforcing hardware constraints at compile time.
    #[inline(always)]
    pub fn modify<F>(&self, f: F, _stop_token: StopClearedToken, _start_token: StartClearedToken, _pec_token: PecClearedToken) -> <super::cr1::CR1rs as crate::RegisterSpec>::Ux
    where
        for<'w> F: FnOnce(&crate::R<super::cr1::CR1rs>, &'w mut crate::W<super::cr1::CR1rs>) -> &'w mut crate::W<super::cr1::CR1rs>,
    {
        self.modify_constrained(f, _stop_token, _start_token, _pec_token)
    }
}
