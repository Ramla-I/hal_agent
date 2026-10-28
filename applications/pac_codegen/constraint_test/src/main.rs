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

    // === Write-once register: one-shot capability spent on a witnessed write ===
    // `take_write_cap` returns the cap at most once per reset (None thereafter);
    // the cap IS the WriteGate::Witness, so it is spent by `write_witnessed`.
    let crc = &dp.CRC;
    if let Some(cap) = crc.idr().take_write_cap() {
        crc.idr().write_witnessed(|w| unsafe { w.bits(0) }, cap);
    }
    // Reading a write-once register is unconstrained.
    let _ = crc.idr().read().bits();

    // === Gated sequence (RTC_WPR handshake): raw write withheld, chain only ===
    // Each step hands the next its token; the ordered chain is the sole path.
    let wpr = dp.RTC.wpr();
    let t0 = wpr.seq_step_0();
    let _t1 = wpr.seq_step_1(t0);

    // === Gated sequence (GPIO LCKR handshake): raw write+modify withheld, chain only ===
    // LCKR is not a data port, so the lock-key sequence gates it (B3); each step
    // writes via write_unwitnessed internally. Raw write/modify no longer compile.
    let lckr = dp.GPIOA.lckr();
    let a0 = lckr.seq_step_0(0x1_0000);
    let a1 = lckr.seq_step_1(a0, 0x0);
    let _a2 = lckr.seq_step_2(a1, 0x1_0000);

    // === Delay ordering gate (CRC_CR): dependent write withheld, obligation only ===
    // `await_delay()` mints the #[must_use] obligation; the caller owns the wait.
    let cr = crc.cr();
    let dw = cr.await_delay();
    cr.write_witnessed(|w| w.reset().set_bit(), dw);

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

    // === Cross-register write gate (RCC_SSCGR <= RCC_CR.PLLON cleared) ===
    let _ = dp.RCC.sscgr().write_when_ready(|w| unsafe { w.bits(0) }, dp.RCC.cr());
    if let Ok(witness) = dp.RCC.sscgr().check_write_ready(dp.RCC.cr()) {
        dp.RCC.sscgr().write_witnessed(|w| unsafe { w.bits(0) }, witness);
    }

    // === Cross-register READ gate (SPI_TXCRCR <= SPI_SR.BSY cleared) ===
    let spi1 = &dp.SPI1;
    if let Ok(r) = spi1.txcrcr().read_when_ready(spi1.sr()) {
        let _ = r.bits();
    }
    if let Ok(witness) = spi1.txcrcr().check_read_ready(spi1.sr()) {
        let _ = spi1.txcrcr().read_witnessed(witness).bits();
    }
    // SAFETY: escape hatch for the read surface, compilation test only.
    let _ = unsafe { spi1.txcrcr().read_unwitnessed() }.bits();

    loop {}
}
