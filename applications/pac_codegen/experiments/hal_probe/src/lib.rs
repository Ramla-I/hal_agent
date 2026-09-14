//! Compiling this crate compiles the driver against the injected PAC.
//! The body is deliberately empty: the BUILD is the experiment, and an empty
//! body keeps every error attributable to the driver rather than to us.
//!
//! Change the `pub use` to match the dependency in Cargo.toml — the crate name
//! with dashes turned into underscores (`stm32f1xx-hal` -> `stm32f1xx_hal`).
#![no_std]

pub use stm32f1xx_hal as hal;
