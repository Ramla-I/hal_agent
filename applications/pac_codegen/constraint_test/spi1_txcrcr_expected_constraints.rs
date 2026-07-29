// Golden output for applications/pac_codegen/rust_codegen.py (trait gating).
// Refresh after an intentional emitter change with:
//   .venv/bin/python applications/pac_codegen/rust_codegen.py \
//     applications/pac_codegen/constraint_test/stm32f405_spi1_txcrcr.json \
//     --peripheral spi1 --output /tmp/c.rs   # then paste below the marker
//@@LIDAR-GOLDEN-GENERATED@@
//! Compile-time access constraints for SPI1 TXCRCR.
//!
//! Generated from datasheet constraints. Do not edit manually.
//!
//! A witness attests that the preconditions were OBSERVED TRUE in one
//! fresh volatile read; prefer `*_when_ready` (check + use in one call).

// === Witnesses ===
/// State witness authorizing one modify of TXCRCR.
pub struct TxcrcrModifyWitness { _priv: () }
/// State witness authorizing one read of TXCRCR.
pub struct TxcrcrReadWitness { _priv: () }

// === Error Type ===
/// A precondition that was not satisfied at check time.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TxcrcrConstraintError {
    /// SPI_SR.BSY cleared was required
    SrBsyNotCleared,
}

// === Gates ===
impl crate::ModifyGate for super::txcrcr::TXCRCRrs {
    type Witness = TxcrcrModifyWitness;
}
impl crate::ReadGate for super::txcrcr::TXCRCRrs {
    type Witness = TxcrcrReadWitness;
}

// === Checks ===
impl crate::Reg<super::txcrcr::TXCRCRrs> {
    /// Read the source register(s) and every source register once and check every modify precondition.
    ///
    /// # Constraint
    /// A read to this register when the BSY Flag is set could return an incorrect value.
    #[inline(always)]
    pub fn check_modify_ready(&self, sr: &crate::Reg<super::sr::SRrs>) -> Result<TxcrcrModifyWitness, TxcrcrConstraintError> {
        let r_sr = sr.read();
        if !(r_sr.bsy().bit_is_clear()) {
            return Err(TxcrcrConstraintError::SrBsyNotCleared);
        }
        Ok(TxcrcrModifyWitness { _priv: () })
    }

    /// Read the source register(s) and every source register once and check every read precondition.
    ///
    /// # Constraint
    /// A read to this register when the BSY Flag is set could return an incorrect value.
    #[inline(always)]
    pub fn check_read_ready(&self, sr: &crate::Reg<super::sr::SRrs>) -> Result<TxcrcrReadWitness, TxcrcrConstraintError> {
        let r_sr = sr.read();
        if !(r_sr.bsy().bit_is_clear()) {
            return Err(TxcrcrConstraintError::SrBsyNotCleared);
        }
        Ok(TxcrcrReadWitness { _priv: () })
    }

    /// Check and modify in one call — the witness never escapes.
    #[inline(always)]
    pub fn modify_when_ready<F>(&self, f: F, sr: &crate::Reg<super::sr::SRrs>) -> Result<<super::txcrcr::TXCRCRrs as crate::RegisterSpec>::Ux, TxcrcrConstraintError>
    where
        for<'w> F: FnOnce(&crate::R<super::txcrcr::TXCRCRrs>, &'w mut crate::W<super::txcrcr::TXCRCRrs>) -> &'w mut crate::W<super::txcrcr::TXCRCRrs>,
    {
        let witness = self.check_modify_ready(sr)?;
        Ok(self.modify_witnessed(f, witness))
    }

    /// Check and read in one call — the witness never escapes.
    #[inline(always)]
    pub fn read_when_ready(&self, sr: &crate::Reg<super::sr::SRrs>) -> Result<crate::R<super::txcrcr::TXCRCRrs>, TxcrcrConstraintError> {
        let witness = self.check_read_ready(sr)?;
        Ok(self.read_witnessed(witness))
    }

}
