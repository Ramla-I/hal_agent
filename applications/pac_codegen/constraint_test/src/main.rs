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
    let r = i2c1.cr1().read();
    let stop_tok = r.verify_stop_cleared().unwrap();
    let start_tok = r.verify_start_cleared().unwrap();
    let pec_tok = r.verify_pec_cleared().unwrap();
    i2c1.cr1()
        .write_constrained(|w| w.pe().enabled(), stop_tok, start_tok, pec_tok);

    // === Safe path: modify_constrained() — no errors ===
    let r = i2c1.cr1().read();
    let stop_tok = r.verify_stop_cleared().unwrap();
    let start_tok = r.verify_start_cleared().unwrap();
    let pec_tok = r.verify_pec_cleared().unwrap();
    i2c1.cr1()
        .modify_constrained(|_, w| w.pe().enabled(), stop_tok, start_tok, pec_tok);

    // === Token-requiring write()/modify() shadows also work with tokens ===
    let r = i2c1.cr1().read();
    let stop_tok = r.verify_stop_cleared().unwrap();
    let start_tok = r.verify_start_cleared().unwrap();
    let pec_tok = r.verify_pec_cleared().unwrap();
    i2c1.cr1()
        .write(|w| w.pe().enabled(), stop_tok, start_tok, pec_tok);

    let r = i2c1.cr1().read();
    let stop_tok = r.verify_stop_cleared().unwrap();
    let start_tok = r.verify_start_cleared().unwrap();
    let pec_tok = r.verify_pec_cleared().unwrap();
    i2c1.cr1()
        .modify(|_, w| w.pe().enabled(), stop_tok, start_tok, pec_tok);

    // === Unconstrained register: write()/modify() work without tokens ===
    // CR2 has no constraints, so Deref to Reg provides the original methods.
    i2c1.cr2().write(|w| unsafe { w.freq().bits(8) });
    i2c1.cr2().modify(|_, w| unsafe { w.freq().bits(8) });

    // === Calling cr1().write(|w| ...) or cr1().modify(|_, w| ...) without tokens ===
    // would produce a compilation error: "expected 4 arguments but 1 was supplied"
    // because the inherent methods shadow the Deref target.

    loop {}
}
