//! Compile test for the trait-gated constraint PAC: exercises every LEGAL
//! access path. Illegal paths (which must FAIL to compile) live in
//! test_codegen.py's compile-fail cases, not here.
#![no_std]
#![no_main]

use stm32f4::stm32f405;

// Minimal panic handler for no_std
#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {}
}

// Dummy entry point — this is a compilation test, not meant to run
#[no_mangle]
pub extern "C" fn main() -> ! {
    // SAFETY: This is a compilation test only. We take peripherals once.
    let dp = unsafe { stm32f405::Peripherals::steal() };
    let i2c1 = &dp.I2C1;

    // === Recommended path: check + use welded into one call ===
    let _ = i2c1.cr1().write_when_ready(|w| w.pe().enabled());
    let _ = i2c1.cr1().modify_when_ready(|_, w| w.pe().enabled());

    // === Two-step path: mint a witness, spend it once ===
    if let Ok(witness) = i2c1.cr1().check_write_ready() {
        i2c1.cr1().write_witnessed(|w| w.pe().enabled(), witness);
    }
    if let Ok(witness) = i2c1.cr1().check_modify_ready() {
        i2c1.cr1().modify_witnessed(|_, w| w.pe().enabled(), witness);
    }

    // === Every write-capable method has a witnessed form ===
    if let Ok(witness) = i2c1.cr1().check_write_ready() {
        i2c1.cr1().reset_witnessed(witness);
    }
    if let Ok(witness) = i2c1.cr1().check_write_ready() {
        // SAFETY: zero-base bit pattern is valid for CR1 (it is its reset value).
        unsafe { i2c1.cr1().write_with_zero_witnessed(|w| w.pe().enabled(), witness) };
    }
    if let Ok(witness) = i2c1.cr1().check_write_ready() {
        i2c1.cr1().from_write_witnessed(
            |w| {
                w.pe().enabled();
            },
            witness,
        );
    }
    if let Ok(witness) = i2c1.cr1().check_modify_ready() {
        i2c1.cr1().from_modify_witnessed(
            |_, w| {
                w.pe().enabled();
            },
            witness,
        );
    }

    // === Reading CR1 is unconstrained and needs no witness ===
    let _ = i2c1.cr1().read().pe().bit_is_set();

    // === The sanctioned escape hatch is unsafe and greppable ===
    // SAFETY: compilation test; a real caller accepts responsibility for
    // violating the documented procedure (errata, bring-up, ...).
    unsafe {
        i2c1.cr1().write_unwitnessed(|w| w.pe().enabled());
        i2c1.cr1().modify_unwitnessed(|_, w| w.pe().enabled());
    }

    // === Unconstrained register: stock API, byte-identical ===
    i2c1.cr2().write(|w| unsafe { w.freq().bits(8) });
    i2c1.cr2().modify(|_, w| unsafe { w.freq().bits(8) });
    i2c1.cr2().reset();
    let _ = i2c1.cr2().read().bits();

    loop {}
}
