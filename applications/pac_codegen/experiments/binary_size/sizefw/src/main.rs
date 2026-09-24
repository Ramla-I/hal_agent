#![no_std]
#![no_main]
use cortex_m_rt::entry;
#[panic_handler] fn panic(_: &core::panic::PanicInfo) -> ! { loop {} }
use stm32g4::stm32g474 as pac;
#[entry] fn main() -> ! {
    let dp = unsafe { pac::Peripherals::steal() };
    dp.GPIOA.moder().write(|w| unsafe { w.bits(0x5555_5555) });
    dp.GPIOA.odr().write(|w| unsafe { w.bits(0xABCD) });
    dp.GPIOA.bsrr().write(|w| unsafe { w.bits(0xFFFF_0000) });
    dp.GPIOB.moder().write(|w| unsafe { w.bits(0x0000_AAAA) });
    let mut acc: u32 = 0;
    for _ in 0..8 {
        acc = acc.wrapping_add(dp.GPIOA.idr().read().bits());
        dp.GPIOB.odr().write(|w| unsafe { w.bits(acc) });
        dp.GPIOA.bsrr().write(|w| unsafe { w.bits(acc ^ 0x1234) });
    }
    loop {}
}
