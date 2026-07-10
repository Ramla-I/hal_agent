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

    // === Safe path: write_constrained() — no errors ===
    let proof = i2c1.cr1().verify_write_ready().unwrap();
    i2c1.cr1()
        .write_constrained(|w| w.pe().enabled(), proof);

    // === Safe path: modify_constrained() — no errors ===
    let proof = i2c1.cr1().verify_write_ready().unwrap();
    i2c1.cr1()
        .modify_constrained(|_, w| w.pe().enabled(), proof);

    // === Proof-requiring write()/modify() shadows also work with proof ===
    let proof = i2c1.cr1().verify_write_ready().unwrap();
    i2c1.cr1()
        .write(|w| w.pe().enabled(), proof);

    let proof = i2c1.cr1().verify_write_ready().unwrap();
    i2c1.cr1()
        .modify(|_, w| w.pe().enabled(), proof);

    // === Unconstrained register: write()/modify() work without proof ===
    // CR2 has no constraints, so Deref to Reg provides the original methods.
    i2c1.cr2().write(|w| unsafe { w.freq().bits(8) });
    i2c1.cr2().modify(|_, w| unsafe { w.freq().bits(8) });

    // === Calling cr1().write(|w| ...) or cr1().modify(|_, w| ...) without proof ===
    // would produce a compilation error: "expected 2 arguments but 1 was supplied"
    // because the inherent methods shadow the Deref target.

    loop {}
}
