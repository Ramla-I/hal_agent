//! Compiling this crate compiles the unmodified stm32f4xx-hal against the
//! locally patched stm32f4 PAC. The crate body is intentionally empty:
//! the HAL build itself is the experiment.
#![no_std]
pub use stm32f4xx_hal as hal;
