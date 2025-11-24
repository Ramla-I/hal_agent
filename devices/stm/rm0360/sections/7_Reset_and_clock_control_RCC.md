**Reset and clock control (RCC)** **RM0360**

# **7 Reset and clock control (RCC)**

## **7.1 Reset**


There are three types of reset, defined as system reset, power reset and RTC domain reset.


**7.1.1** **Power reset**


A power reset is generated when one of the following events occurs:


1. Power-on/power-down reset (POR/PDR reset)


2. When exiting Standby mode


A power reset sets all registers to their reset values.


**7.1.2** **System reset**


System reset sets each register to its reset value, unless otherwise specified in the register
description.


A system reset is generated when one of the following events occurs:


1. A low level on the NRST pin (external reset)


2. Window watchdog event (WWDG reset)


3. Independent watchdog event (IWDG reset)


4. A software reset (SW reset) (see _Software reset_ )


5. Low-power management reset (see _Low-power management reset_ )


6. Option byte loader reset (see _Option byte loader reset_ )


7. A power reset


The reset source can be identified by checking the reset flags in the Control/Status register,
RCC_CSR (see _Section 7.4.10: Control/status register (RCC_CSR)_ ).


These sources act on the NRST pin and it is always kept low during the delay phase. The
RESET service routine vector is fixed at address 0x0000_0004 in the memory map.


The system reset signal provided to the device is output on the NRST pin. The pulse
generator guarantees a minimum reset pulse duration of 20 µs for each internal reset
source. In case of an external reset, the reset pulse is generated while the NRST pin is
asserted low.


88/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


**Figure 9. Simplified diagram of the reset circuit**











**Software reset**


The SYSRESETREQ bit in Arm [®] Cortex [®] -M0 Application Interrupt and Reset Control
Register must be set to force a software reset on the device. Refer to the _Cortex™-M0_
_technical reference manual_ for more details.


**Low-power management reset**


There are two ways to generate a low-power management reset:


1. Reset generated when entering Standby mode:


This type of reset is enabled by resetting nRST_STDBY bit in User Option Bytes. In this
case, whenever a Standby mode entry sequence is successfully executed, the device
is reset instead of entering Standby mode.


2. Reset when entering Stop mode:


This type of reset is enabled by resetting nRST_STOP bit in User Option Bytes. In this
case, whenever a Stop mode entry sequence is successfully executed, the device is
reset instead of entering Stop mode.


For further information on the User Option Bytes, refer to _Section 4: Option bytes_ .


**Option byte loader reset**


The option byte loader reset is generated when the OBL_LAUNCH bit (bit 13) is set in the
FLASH_CR register. This bit is used to launch the option byte loading by software.


**7.1.3** **RTC domain reset**


An RTC domain reset only affects the LSE oscillator, the RTC and the RCC _RTC domain_
_control register (RCC_BDCR)_ . It is generated when one of the following events occurs.


1. Software reset, triggered by setting the BDRST bit in the _RTC domain control register_
_(RCC_BDCR)_ .


2. A POR reset.


RM0360 Rev 5 89/775



124


**Reset and clock control (RCC)** **RM0360**

## **7.2 Clocks**


Various clock sources can be used to drive the system clock (SYSCLK):


      - HSI 8 MHz RC oscillator clock


      - HSE oscillator clock


      - PLL clock


The devices have the following additional clock sources:


      - 40 kHz low speed internal RC (LSI RC) which drives the independent watchdog and
optionally the RTC used for Auto-wake-up from Stop/Standby mode.


      - 32.768 kHz low speed external crystal (LSE crystal) which optionally drives the realtime clock (RTCCLK)


      - 14 MHz high speed internal RC (HSI14) dedicated for ADC.


Each clock source can be switched on or off independently when it is not used, to optimize
power consumption.


Several prescalers can be used to configure the frequency of the AHB and the APB
domains. The AHB and the APB domains maximum frequency is 48 MHz.


All the peripheral clocks are derived from their bus clock (HCLK for AHB or PCLK for APB)
except:


      - The Flash memory programming interface clock (FLITFCLK) which is always the HSI
clock.


      - The option byte loader clock which is always the HSI clock


      - The ADC clock which is derived (selected by software) from one of the two following

sources:


–
dedicated HSI14 clock, to run always at the maximum sampling rate


–
APB clock (PCLK) divided by 2 or 4


      - The USART1 clock which is derived (selected by software) from one of the four
following sources:


–
system clock


– HSI clock


– LSE clock


–
APB clock (PCLK)


      - The I2C1 clock which is derived (selected by software) from one of the two following

sources:


–
system clock


– HSI clock


      - The USB clock which is derived (selected by software) from the following source:


– PLL clock


      - The RTC clock which is derived from the LSE, LSI or from the HSE clock divided by 32.


      - The timer clock frequencies are automatically fixed by hardware. There are two cases:


–
if the APB prescaler is 1, the timer clock frequencies are set to the same
frequency as that of the APB domain;


–
otherwise, they are set to twice (x2) the frequency of the APB domain.


      - The IWDG clock which is always the LSI clock.


90/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


The RCC feeds the Cortex System Timer (SysTick) external clock with the AHB clock
(HCLK) divided by 8. The SysTick can work either with this clock or directly with the Cortex
clock (HCLK), configurable in the SysTick Control and Status Register.















































1. Applies to STM32F030x4/x6 devices.


2. Applies to STM32F030x8 devices.


RM0360 Rev 5 91/775



124


**Reset and clock control (RCC)** **RM0360**



























































FCLK acts as Arm [®] Cortex [®] -M0’s free-running clock. For more details refer to the _Arm_
_Cortex-M0 r0p0 technical reference manual (TRM)._


92/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


**7.2.1** **HSE clock**


The high speed external clock signal (HSE) can be generated from two possible clock

sources:


      - HSE external crystal/ceramic resonator


      - HSE user external clock


The resonator and the load capacitors have to be placed as close as possible to the
oscillator pins in order to minimize output distortion and startup stabilization time. The
loading capacitance values must be adjusted according to the selected oscillator.

|Col1|Figure 12. HSE/ LSE clock sources|
|---|---|
|**Clock source**|**Hardware configuration**|
|**External clock**|MSv31915V1<br>OSC_IN<br>OSC_OUT<br>GPIO<br>External<br>source|
|**Crystal/Ceramic**<br>**resonators**|MSv31916V1<br>OSC_IN<br>OSC_OUT<br>CL1<br>CL2<br>Load<br>capacitors|



RM0360 Rev 5 93/775



124


**Reset and clock control (RCC)** **RM0360**


**External crystal/ceramic resonator (HSE crystal)**


The 4 to 32 MHz external oscillator has the advantage of producing a very accurate rate on
the main clock.


The associated hardware configuration is shown in _Figure 12_ . Refer to the electrical
characteristics section of the _datasheet_ for more details.


The HSERDY flag in the _Clock control register (RCC_CR)_ indicates if the HSE oscillator is
stable or not. At startup, the clock is not released until this bit is set by hardware. An
interrupt can be generated if enabled in the _Clock interrupt register (RCC_CIR)_ .


The HSE Crystal can be switched on and off using the HSEON bit in the _Clock control_
_register (RCC_CR)_ .


For code example refer to the Appendix section _A.3.1: HSE start sequence_ .


**Caution:** To switch ON the HSE oscillator, 512 HSE clock pulses need to be seen by an internal
stabilization counter after the HSEON bit is set. Even in the case that no crystal or resonator
is connected to the device, excessive external noise on the OSC_IN pin may still lead the
oscillator to start. Once the oscillator is started, it needs another 6 HSE clock pulses to
complete a switching OFF sequence. If for any reason the oscillations are no more present
on the OSC_IN pin, the oscillator cannot be switched OFF, locking the OSC pins from any
other use and introducing unwanted power consumption. To avoid such situation, it is
strongly recommended to always enable the Clock Security System (CSS) which is able to
switch OFF the oscillator even in this case.


**External source (HSE bypass)**


In this mode, an external clock source must be provided. It can have a frequency of up to
32 MHz. You select this mode by setting the HSEBYP and HSEON bits in the _Clock control_
_register (RCC_CR)_ . The external clock signal (square, sinus or triangle) with ~40-60% duty
cycle depending on the frequency (refer to the datasheet) has to drive the OSC_IN pin while
the OSC_OUT pin can be used a GPIO. See _Figure 12_ .


**7.2.2** **HSI clock**


The HSI clock signal is generated from an internal 8 MHz RC oscillator and can be used
directly as a system clock or for PLL input


The HSI RC oscillator has the advantage of providing a clock source at low cost (no external
components). It also has a faster startup time than the HSE crystal oscillator however, even
with calibration the frequency is less accurate than an external crystal oscillator or ceramic
resonator.


**Calibration**


RC oscillator frequencies can vary from one chip to another due to manufacturing process
variations, this is why each device is factory calibrated by ST for 1% accuracy at T A =25°C.


After reset, the factory calibration value is loaded in the HSICAL[7:0] bits in the _Clock control_
_register (RCC_CR)_ .


If the application is subject to voltage or temperature variations this may affect the RC
oscillator speed. You can trim the HSI frequency in the application using the HSITRIM[4:0]
bits in the _Clock control register (RCC_CR)_ .


94/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


For more details on how to measure the HSI frequency variation refer to _Section 7.2.12:_
_Internal/external clock measurement with TIM14 on page 98_ .


The HSIRDY flag in the _Clock control register (RCC_CR)_ indicates if the HSI RC is stable or
not. At startup, the HSI RC output clock is not released until this bit is set by hardware.


The HSI RC can be switched on and off using the HSION bit in the _Clock control register_
_(RCC_CR)_ .


The HSI signal can also be used as a backup source (Auxiliary clock) if the HSE crystal
oscillator fails. Refer to _Section 7.2.7: Clock security system (CSS) on page 96_ .


Furthermore it is possible to drive the HSI clock to the MCO multiplexer. Then the clock
could be driven to the Timer 14 giving the ability to the user to calibrate the oscillator.


**7.2.3** **PLL**


The internal PLL can be used to multiply the HSI and the HSE output clock frequency. Refer
to _Figure 9: Simplified diagram of the reset circuit_, _Figure 12: HSE/ LSE clock sources_ and
_Clock control register (RCC_CR)_ .


The PLL configuration (selection of the input clock, predivider and multiplication factor) must
be done before enabling the PLL. Once the PLL is enabled, these parameters cannot be
changed.


To modify the PLL configuration, proceed as follows:


1. Disable the PLL by setting PLLON to 0.


2. Wait until PLLRDY is cleared. The PLL is now fully stopped.


3. Change the desired parameter.


4. Enable the PLL again by setting PLLON to 1.


5. Wait until PLLRDY is set.


An interrupt can be generated when the PLL is ready, if enabled in the _Clock interrupt_
_register (RCC_CIR)_ .


The PLL output frequency must be set in the range 16-48 MHz.


For code example refer to the Appendix section _A.3.2: PLL configuration modification_ .


**7.2.4** **LSE clock**


The LSE crystal is a 32.768 kHz Low Speed External crystal or ceramic resonator. It has the
advantage of providing a low-power but highly accurate clock source to the real-time clock
peripheral (RTC) for clock/calendar or other timing functions.


The LSE crystal is switched on and off using the LSEON bit in _RTC domain control register_
_(RCC_BDCR)_ . The crystal oscillator driving strength can be changed at runtime using the
LSEDRV[1:0] bits in the _RTC domain control register (RCC_BDCR)_ to obtain the best
compromise between robustness and short start-up time on one side and low-power
consumption on the other.


The LSERDY flag in the _RTC domain control register (RCC_BDCR)_ indicates whether the
LSE crystal is stable or not. At startup, the LSE crystal output clock signal is not released
until this bit is set by hardware. An interrupt can be generated if enabled in the _Clock_
_interrupt register (RCC_CIR)_ .


RM0360 Rev 5 95/775



124


**Reset and clock control (RCC)** **RM0360**


**Caution:** To switch ON the LSE oscillator, 4096 LSE clock pulses need to be seen by an internal
stabilization counter after the LSEON bit is set. Even in the case that no crystal or resonator
is connected to the device, excessive external noise on the OSC32_IN pin may still lead the
oscillator to start. Once the oscillator is started, it needs another 6 LSE clock pulses to
complete a switching OFF sequence. If for any reason the oscillations are no more present
on the OSC_IN pin, the oscillator cannot be switched OFF, locking the OSC32 pins from any
other use and introducing unwanted power consumption. The only way to recover such
situation is to perform the RTC domain reset by software.


**External source (LSE bypass)**


In this mode, an external clock source must be provided. It can have a frequency of up to
1 MHz. You select this mode by setting the LSEBYP and LSEON bits in the _RTC domain_
_control register (RCC_BDCR)_ . The external clock signal (square, sinus or triangle) with
~50% duty cycle has to drive the OSC32_IN pin while the OSC32_OUT pin can be used as
GPIO. See _Figure 12_ .


**7.2.5** **LSI clock**


The LSI RC acts as a low-power clock source that can be kept running in Stop and Standby
mode for the independent watchdog (IWDG) and RTC. The clock frequency is around 40
kHz. For more details, refer to the electrical characteristics section of the datasheets.


The LSI RC can be switched on and off using the LSION bit in the _Control/status register_
_(RCC_CSR)_ .


The LSIRDY flag in the _Control/status register (RCC_CSR)_ indicates if the LSI oscillator is
stable or not. At startup, the clock is not released until this bit is set by hardware. An
interrupt can be generated if enabled in the _Clock interrupt register (RCC_CIR)_ .


**7.2.6** **System clock (SYSCLK) selection**


Various clock sources can be used to drive the system clock (SYSCLK):


      - HSI oscillator


      - HSE oscillator


      - PLL


After a system reset, the HSI oscillator is selected as system clock. When a clock source is
used directly or through the PLL as a system clock, it is not possible to stop it.


A switch from one clock source to another occurs only if the target clock source is ready
(clock stable after startup delay or PLL locked). If a clock source which is not yet ready is
selected, the switch will occur when the clock source becomes ready. Status bits in the
_Clock control register (RCC_CR)_ indicate which clock(s) is (are) ready and which clock is
currently used as a system clock.


**7.2.7** **Clock security system (CSS)**


Clock security system can be activated by software. In this case, the clock detector is
enabled after the HSE oscillator startup delay, and disabled when this oscillator is stopped.


If a failure is detected on the HSE clock, the HSE oscillator is automatically disabled, a clock
failure event is sent to the break input of the advanced-control timers (TIM1) and generalpurpose timers (TIM15, TIM16 and TIM17) and an interrupt is generated to inform the
software about the failure (clock security system interrupt, or CSSI), allowing the MCU to


96/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


perform rescue operations. The CSSI is linked to the Arm [®] Cortex [®] -M0 NMI (Non-Maskable
Interrupt) exception vector.


_Note:_ _Once the CSS is enabled and if the HSE clock fails, the CSS interrupt occurs and an NMI is_
_automatically generated. The NMI is executed indefinitely unless the CSS interrupt pending_
_bit is cleared. As a consequence, in the NMI ISR user must clear the CSS interrupt by_
_setting the CSSC bit in the Clock interrupt register (RCC_CIR)._


If the HSE oscillator is used directly or indirectly as the system clock (indirectly means: it is
used as PLL input clock, and the PLL clock is used as system clock), a detected failure
causes a switch of the system clock to the HSI oscillator and the disabling of the HSE
oscillator. If the HSE clock (divided or not) is the clock entry of the PLL used as system clock
when the failure occurs, the PLL is disabled too.


**7.2.8** **ADC clock**


The ADC clock selection is done inside the ADC_CFGR2 (refer to _Section 12.10.5: ADC_
_configuration register 2 (ADC_CFGR2) on page 220_ ). It can be either the dedicated 14 MHz
RC oscillator (HSI14) connected on the ADC asynchronous clock input or PCLK divided by
2 or 4. The 14 MHz RC oscillator can be configured by software either to be turned on/off
(“auto-off mode”) by the ADC interface or to be always enabled. The HSI 14 MHz RC
oscillator cannot be turned on by ADC interface when the APB clock is selected as an ADC
kernel clock.


**7.2.9** **RTC clock**


The RTCCLK clock source can be either the HSE/32, LSE or LSI clocks. This is selected by
programming the RTCSEL[1:0] bits in the _RTC domain control register (RCC_BDCR)_ . This
selection cannot be modified without resetting the RTC domain. The system must be always
configured in a way that the PCLK frequency is greater then or equal to the RTCCLK
frequency for proper operation of the RTC.


**7.2.10** **Independent watchdog clock**


If the Independent watchdog (IWDG) is started by either hardware option or software
access, the LSI oscillator is forced ON and cannot be disabled. After the LSI oscillator
temporization, the clock is provided to the IWDG.


**7.2.11** **Clock-out capability**


The microcontroller clock output (MCO) capability allows the clock to be output onto the
external MCO pin. The configuration registers of the corresponding GPIO port must be
programmed in alternate function mode. One of the following clock signals can be selected
as the MCO clock:


      - HSI14


      - SYSCLK


      - HSI


      - HSE


      - PLL clock divided by 2 or direct (direct connection is not available on STM32F030x8
devices)


      - LSE


      - LSI


RM0360 Rev 5 97/775



124


**Reset and clock control (RCC)** **RM0360**


The selection is controlled by the MCO[3:0] bits of the _Clock configuration register_
_(RCC_CFGR)_ .


For code example refer to the Appendix section _A.3.3: MCO selection_ .


On STM32F030x4, STM32F030x6, STM32F070x6, STM32F070xB and STM32F030xC
devices, the additional bit PLLNODIV of this register controls the divider bypass for a PLL
clock input to MCO. The MCO frequency can be reduced by a configurable binary divider,
controlled by the MCOPRE[2..0] bits of the _Clock configuration register (RCC_CFGR)_ .


**7.2.12** **Internal/external clock measurement with TIM14**


It is possible to indirectly measure the frequency of all on-board clock sources by mean of
the TIM14 channel 1 input capture. As represented on _Figure 13_ .


**Figure 13. Frequency measurement with TIM14 in capture mode**











The input capture channel of the Timer 14 can be a GPIO line or an internal clock of the
MCU. This selection is performed through the TI1_RMP [1:0] bits in the TIM14_OR register.
The possibilities available are the following ones.


      - TIM14 Channel1 is connected to the GPIO. Refer to the alternate function mapping in
the device datasheets.


      - TIM14 Channel1 is connected to the RTCCLK.


      - TIM14 Channel1 is connected to the HSE/32 Clock.


      - TIM14 Channel1 is connected to the microcontroller clock output (MCO). Refer to
_Section 7.2.11: Clock-out capability_ for MCO clock configuration.


For code example refer to the Appendix section _A.3.4: Clock measurement configuration_
_with TIM14_ .


**Calibration of the HSI**


The primary purpose of connecting the LSE, through the MCO multiplexer, to the channel 1
input capture is to be able to precisely measure the HSI system clocks (for this, the HSI
should be used as the system clock source). The number of HSI clock counts between
consecutive edges of the LSE signal provides a measure of the internal clock period. Taking
advantage of the high precision of LSE crystals (typically a few tens of ppm), it is possible to
determine the internal clock frequency with the same resolution, and trim the source to
compensate for manufacturing-process- and/or temperature- and voltage-related frequency
deviations.


The HSI oscillator has dedicated user-accessible calibration bits for this purpose.


98/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


The basic concept consists in providing a relative measurement (e.g. the HSI/LSE ratio): the
precision is therefore closely related to the ratio between the two clock sources. The higher
the ratio is, the better the measurement is.


If LSE is not available, HSE/32 is the better option in order to reach the most precise
calibration possible.


**Calibration of the LSI**


The calibration of the LSI will follow the same pattern that for the HSI, but changing the
reference clock. It is necessary to connect LSI clock to the channel 1 input capture of the
TIM14. Then define the HSE as system clock source, the number of its clock counts
between consecutive edges of the LSI signal provides a measure of the internal low speed
clock period.


The basic concept consists in providing a relative measurement (e.g. the HSE/LSI ratio): the
precision is therefore closely related to the ratio between the two clock sources. The higher
the ratio is, the better the measurement is.


**Calibration of the HSI14**


For the HSI14, because of its high frequency, it is not possible to have a precise resolution.
However a solution could be to clock Timer 14 with HSE through PLL to reach 48 MHz, and
to use the input capture line with the HSI14 and the capture prescaler defined to the higher
value. In that configuration, we got a ratio of 27 events. It is still a bit low to have an accurate
calibration. In order to increase the measure accuracy, it is advised to count the HSI periods
after multiple cycles of Timer 14. Using polling to treat the capture event is necessary in this

case.

## **7.3 Low-power modes**


APB peripheral clocks and DMA clock can be disabled by software.


Sleep mode stops the CPU clock. The memory interface clocks (Flash and RAM interfaces)
can be stopped by software during sleep mode. The AHB to APB bridge clocks are disabled
by hardware during Sleep mode when all the clocks of the peripherals connected to them
are disabled.


Stop mode stops all the clocks in the core supply domain and disables the PLL and the HSI,
HSI14 and HSE oscillators.


Standby mode stops all the clocks in the core supply domain and disables the PLL and the
HSI, HSI14 and HSE oscillators.


The CPU’s deepsleep mode can be overridden for debugging by setting the DBG_STOP or
DBG_STANDBY bits in the DBGMCU_CR register.


When waking up from deepsleep after an interrupt (Stop mode) or reset (Standby mode),
the HSI oscillator is selected as system clock.


If a Flash programming operation is on going, deepsleep mode entry is delayed until the
Flash interface access is finished. If an access to the APB domain is ongoing, deepsleep
mode entry is delayed until the APB access is finished.


RM0360 Rev 5 99/775



124


**Reset and clock control (RCC)** **RM0360**

## **7.4 RCC registers**


Refer to _Section 1.2 on page 33_ for a list of abbreviations used in register descriptions.


**7.4.1** **Clock control register (RCC_CR)**


Address offset: 0x00


Reset value: 0x0000 XX83 where X is undefined.


Access: no wait state, word, half-word and byte access

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|PLL<br>RDY|PLLON|Res.|Res.|Res.|Res.|CSS<br>ON|HSE<br>BYP|HSE<br>RDY|HSE<br>ON|
|||||||r|rw|||||rw|rw|r|rw|


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3|Col10|Col11|Col12|Col13|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSITRIM[4:0]|HSITRIM[4:0]|HSITRIM[4:0]|HSITRIM[4:0]|HSITRIM[4:0]|Res.|HSI<br>RDY|HSION|
|r|r|r|r|r|r|r|r|rw|rw|rw|rw|rw||r|rw|



Bits 31:26 Reserved, must be kept at reset value.


Bit 25 **PLLRDY:** PLL clock ready flag

Set by hardware to indicate that the PLL is locked.

0: PLL unlocked

1: PLL locked


Bit 24 **PLLON:** PLL enable

Set and cleared by software to enable PLL.

Cleared by hardware when entering Stop or Standby mode. This bit can not be reset if the PLL
clock is used as system clock or is selected to become the system clock.

0: PLL OFF

1: PLL ON


Bits 23:20 Reserved, must be kept at reset value.


Bit 19 **CSSON:** Clock security system enable

Set and cleared by software to enable the clock security system. When CSSON is set, the
clock detector is enabled by hardware when the HSE oscillator is ready, and disabled by
hardware if a HSE clock failure is detected.

0: Clock security system disabled (clock detector OFF).
1: Clock security system enabled (clock detector ON if the HSE is ready, OFF if not).


Bit 18 **HSEBYP:** HSE crystal oscillator bypass

Set and cleared by software to bypass the oscillator with an external clock. The external clock
must be enabled with the HSEON bit set, to be used by the device. The HSEBYP bit can be
written only if the HSE oscillator is disabled.

0: HSE crystal oscillator not bypassed
1: HSE crystal oscillator bypassed with external clock


100/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


Bit 17 **HSERDY:** HSE clock ready flag

Set by hardware to indicate that the HSE oscillator is stable. This bit needs 6 cycles of the HSE
oscillator clock to fall down after HSEON reset.

0: HSE oscillator not ready
1: HSE oscillator ready


Bit 16 **HSEON:** HSE clock enable

Set and cleared by software.

Cleared by hardware to stop the HSE oscillator when entering Stop or Standby mode. This bit
cannot be reset if the HSE oscillator is used directly or indirectly as the system clock.

0: HSE oscillator OFF

1: HSE oscillator ON


Bits 15:8 **HSICAL[7:0]:** HSI clock calibration

These bits are initialized automatically at startup. They are adjusted by SW through the
HSITRIM setting.


Bits 7:3 **HSITRIM[4:0]:** HSI clock trimming

These bits provide an additional user-programmable trimming value that is added to the
HSICAL[7:0] bits. It can be programmed to adjust to variations in voltage and temperature that
influence the frequency of the HSI.

The default value is 16, which, when added to the HSICAL value, should trim the HSI to 8 MHz
± 1%. The trimming step is around 40 kHz between two consecutive HSICAL steps.

_Note: Increased value in the register results to higher clock frequency._


Bit 2 Reserved, must be kept at reset value.


Bit 1 **HSIRDY:** HSI clock ready flag

Set by hardware to indicate that HSI oscillator is stable. After the HSION bit is cleared,
HSIRDY goes low after 6 HSI oscillator clock cycles.

0: HSI oscillator not ready
1: HSI oscillator ready


Bit 0 **HSION:** HSI clock enable

Set and cleared by software.

Set by hardware to force the HSI oscillator ON when leaving Stop or Standby mode or in case
of failure of the HSE crystal oscillator used directly or indirectly as system clock. This bit
cannot be reset if the HSI is used directly or indirectly as system clock or is selected to become
the system clock.

0: HSI oscillator OFF

1: HSI oscillator ON


**7.4.2** **Clock configuration register (RCC_CFGR)**


Address offset: 0x04


Reset value: 0x0000 0000


Access: 0 ≤ wait state ≤ 2, word, half-word and byte access


1 or 2 wait states inserted only if the access occurs during clock source switch.


RM0360 Rev 5 101/775



124


**Reset and clock control (RCC)** **RM0360**

|31|30 29 28|Col3|Col4|27 26 25 24|Col6|Col7|Col8|23|22|21 20 19 18|Col12|Col13|Col14|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PLL<br>NODIV|MCOPRE[2:0]|MCOPRE[2:0]|MCOPRE[2:0]|MCO[3:0]|MCO[3:0]|MCO[3:0]|MCO[3:0]|Res.|Res.|PLLMUL[3:0]|PLLMUL[3:0]|PLLMUL[3:0]|PLLMUL[3:0]|PLL<br>XTPRE|PLL<br>SRC[1]|
|rw|rw|rw|rw|rw|rw|rw|rw|||rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10 9 8|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2|Col14|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PLL<br>SRC[0]|ADC<br>PRE|Res.|Res.|Res.|PPRE[2:0]|PPRE[2:0]|PPRE[2:0]|HPRE[3:0]|HPRE[3:0]|HPRE[3:0]|HPRE[3:0]|SWS[1:0]|SWS[1:0]|SW[1:0]|SW[1:0]|
|rw|rw||||rw|rw|rw|rw|rw|rw|rw|r|r|rw|rw|



Bit 31 **PLLNODIV:** PLL clock not divided for MCO (not available on STM32F030x8 devices)

This bit is set and cleared by software. It switches off divider by 2 for PLL connection to MCO.

0: PLL is divided by 2 for MCO

1: PLL is not divided for MCO


Bits 30:28 **MCOPRE[2:0]:** Microcontroller clock output prescaler (not available on STM32F030x8
devices)

These bits are set and cleared by software to select the MCO prescaler division factor. To
avoid glitches, it is highly recommended to change this prescaler only when the MCO output is
disabled.

000: MCO is divided by 1
001: MCO is divided by 2
010: MCO is divided by 4

.....

111: MCO is divided by 128


Bits 27:24 **MCO[3:0]:** Microcontroller clock output

Set and cleared by software.

0000: MCO output disabled, no clock on MCO
0001: Internal RC 14 MHz (HSI14) oscillator clock selected
0010: Internal low speed (LSI) oscillator clock selected
0011: External low speed (LSE) oscillator clock selected
0100: System clock selected
0101: Internal RC 8 MHz (HSI) oscillator clock selected
0110: External 4-32 MHz (HSE) oscillator clock selected
0111: PLL clock selected (divided by 1 or 2, depending on PLLNODIV)
1xxx: Reserved, must be kept at reset value.

_Note: This clock output may have some truncated cycles at startup or during MCO clock_
_source switching._


Bits 23:22 Reserved, must be kept at reset value.


102/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


Bits 21:18 **PLLMUL[3:0]:** PLL multiplication factor

These bits are written by software to define the PLL multiplication factor. These bits can be
written only when PLL is disabled.

Caution: The PLL output frequency must not exceed 48 MHz.

0000: PLL input clock x 2
0001: PLL input clock x 3
0010: PLL input clock x 4
0011: PLL input clock x 5
0100: PLL input clock x 6
0101: PLL input clock x 7
0110: PLL input clock x 8
0111: PLL input clock x 9
1000: PLL input clock x 10
1001: PLL input clock x 11
1010: PLL input clock x 12
1011: PLL input clock x 13
1100: PLL input clock x 14
1101: PLL input clock x 15
1110: PLL input clock x 16
1111: PLL input clock x 16


Bit 17 **PLLXTPRE** : HSE divider for PLL input clock

This bit is the same bit as bit PREDIV[0] from RCC_CFGR2. Refer to RCC_CFGR2 PREDIV
bits description for its meaning.


Bits 16:15 **PLLSRC[1:0]:** PLL input clock source

Set and cleared by software to select PLL or PREDIV clock source. These bits can be written
only when PLL is disabled.

00: HSI/2 selected as PLL input clock (PREDIV forced to divide by 2 on STM32F070xx and
STM32F030xC devices)
01: HSI/PREDIV selected as PLL input clock
10: HSE/PREDIV selected as PLL input clock

11: Reserved

Bit PLLSRC[0] is available only on STM32F070xx and STM32F030xC devices, otherwise it is
reserved (with value zero).


Bit 14 **ADCPRE:** ADC prescaler

Obsolete setting. Proper ADC clock selection is done inside the ADC_CFGR2 (refer to
_Section 12.10.5: ADC configuration register 2 (ADC_CFGR2) on page 220_ ).


Bits 13:11 Reserved, must be kept at reset value.


Bits 10:8 **PPRE[2:0]:** PCLK prescaler

Set and cleared by software to control the division factor of the APB clock (PCLK).

0xx: HCLK not divided

100: HCLK divided by 2
101: HCLK divided by 4
110: HCLK divided by 8
111: HCLK divided by 16


RM0360 Rev 5 103/775



124


**Reset and clock control (RCC)** **RM0360**


Bits 7:4 **HPRE[3:0]:** HCLK prescaler

Set and cleared by software to control the division factor of the AHB clock.

0xxx: SYSCLK not divided

1000: SYSCLK divided by 2
1001: SYSCLK divided by 4
1010: SYSCLK divided by 8
1011: SYSCLK divided by 16
1100: SYSCLK divided by 64
1101: SYSCLK divided by 128
1110: SYSCLK divided by 256
1111: SYSCLK divided by 512


Bits 3:2 **SWS[1:0]:** System clock switch status

Set and cleared by hardware to indicate which clock source is used as system clock.

00: HSI oscillator used as system clock
01: HSE oscillator used as system clock
10: PLL used as system clock
11: Reserved, must be kept at reset value.


Bits 1:0 **SW[1:0]:** System clock switch

Set and cleared by software to select SYSCLK source.

Cleared by hardware to force HSI selection when leaving Stop and Standby mode or in case
of failure of the HSE oscillator used directly or indirectly as system clock (if the Clock Security
System is enabled).

00: HSI selected as system clock
01: HSE selected as system clock
10: PLL selected as system clock
11: Reserved, must be kept at reset value.


**7.4.3** **Clock interrupt register (RCC_CIR)**


Address offset: 0x08


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CSSC|Res.|HSI14<br>RDYC|PLL<br>RDYC|HSE<br>RDYC|HSI<br>RDYC|LSE<br>RDYC|LSI<br>RDYC|
|||||||||w||w|w|w|w|w|w|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|HSI14<br>RDYIE|PLL<br>RDYIE|HSE<br>RDYIE|HSI<br>RDYIE|LSE<br>RDYIE|LSI<br>RDYIE|CSSF|Res.|HSI14<br>RDYF|PLL<br>RDYF|HSE<br>RDYF|HSI<br>RDYF|LSE<br>RDYF|LSI<br>RDYF|
|||rw|rw|rw|rw|rw|rw|r||r|r|r|r|r|r|



Bits 31:24 Reserved, must be kept at reset value.


Bit 23 **CSSC:** Clock security system interrupt clear

This bit is set by software to clear the CSSF flag.

0: No effect

1: Clear CSSF flag


104/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


Bit 22

Reserved, must be kept at reset value.


Bit 21 **HSI14RDYC:** HSI14 ready interrupt clear

This bit is set by software to clear the HSI14RDYF flag.

0: No effect

1: Clear HSI14RDYF flag


Bit 20 **PLLRDYC:** PLL ready interrupt clear

This bit is set by software to clear the PLLRDYF flag.

0: No effect

1: Clear PLLRDYF flag


Bit 19 **HSERDYC:** HSE ready interrupt clear

This bit is set by software to clear the HSERDYF flag.

0: No effect

1: Clear HSERDYF flag


Bit 18 **HSIRDYC:** HSI ready interrupt clear

This bit is set software to clear the HSIRDYF flag.

0: No effect

1: Clear HSIRDYF flag


Bit 17 **LSERDYC:** LSE ready interrupt clear

This bit is set by software to clear the LSERDYF flag.

0: No effect

1: LSERDYF cleared


Bit 16 **LSIRDYC:** LSI ready interrupt clear

This bit is set by software to clear the LSIRDYF flag.

0: No effect

1: LSIRDYF cleared


Bits 15:14 Reserved, must be kept at reset value.


Bit 13 **HSI14RDYIE** : HSI14 ready interrupt enable

Set and cleared by software to enable/disable interrupt caused by the HSI14 oscillator
stabilization.

0: HSI14 ready interrupt disabled
1: HSI14 ready interrupt enabled


Bit 12 **PLLRDYIE:** PLL ready interrupt enable

Set and cleared by software to enable/disable interrupt caused by PLL lock.

0: PLL lock interrupt disabled
1: PLL lock interrupt enabled


Bit 11 **HSERDYIE:** HSE ready interrupt enable

Set and cleared by software to enable/disable interrupt caused by the HSE oscillator
stabilization.

0: HSE ready interrupt disabled
1: HSE ready interrupt enabled


Bit 10 **HSIRDYIE:** HSI ready interrupt enable

Set and cleared by software to enable/disable interrupt caused by the HSI oscillator
stabilization.

0: HSI ready interrupt disabled
1: HSI ready interrupt enabled


RM0360 Rev 5 105/775



124


**Reset and clock control (RCC)** **RM0360**


Bit 9 **LSERDYIE:** LSE ready interrupt enable

Set and cleared by software to enable/disable interrupt caused by the LSE oscillator
stabilization.

0: LSE ready interrupt disabled
1: LSE ready interrupt enabled


Bit 8 **LSIRDYIE:** LSI ready interrupt enable

Set and cleared by software to enable/disable interrupt caused by the LSI oscillator
stabilization.

0: LSI ready interrupt disabled
1: LSI ready interrupt enabled


Bit 7 **CSSF:** Clock security system interrupt flag

Set by hardware when a failure is detected in the HSE oscillator.

Cleared by software setting the CSSC bit.

0: No clock security interrupt caused by HSE clock failure
1: Clock security interrupt caused by HSE clock failure


Bit 6

Reserved, must be kept at reset value.


Bit 5 **HSI14RDYF:** HSI14 ready interrupt flag

Set by hardware when the HSI14 becomes stable and HSI14RDYDIE is set in a response to
setting the HSI14ON bit in _Clock control register 2 (RCC_CR2)_ . When HSI14ON is not set
but the HSI14 oscillator is enabled by the peripheral through a clock request, this bit is not set
and no interrupt is generated.

Cleared by software setting the HSI14RDYC bit.

0: No clock ready interrupt caused by the HSI14 oscillator
1: Clock ready interrupt caused by the HSI14 oscillator


Bit 4 **PLLRDYF:** PLL ready interrupt flag

Set by hardware when the PLL locks and PLLRDYDIE is set.

Cleared by software setting the PLLRDYC bit.

0: No clock ready interrupt caused by PLL lock
1: Clock ready interrupt caused by PLL lock


Bit 3 **HSERDYF:** HSE ready interrupt flag

Set by hardware when the HSE clock becomes stable and HSERDYDIE is set.

Cleared by software setting the HSERDYC bit.

0: No clock ready interrupt caused by the HSE oscillator
1: Clock ready interrupt caused by the HSE oscillator


Bit 2 **HSIRDYF:** HSI ready interrupt flag

Set by hardware when the HSI clock becomes stable and HSIRDYDIE is set in a response to
setting the HSION (refer to _Clock control register (RCC_CR)_ ). When HSION is not set but the
HSI oscillator is enabled by the peripheral through a clock request, this bit is not set and no
interrupt is generated.

Cleared by software setting the HSIRDYC bit.

0: No clock ready interrupt caused by the HSI oscillator
1: Clock ready interrupt caused by the HSI oscillator


106/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


Bit 1 **LSERDYF:** LSE ready interrupt flag

Set by hardware when the LSE clock becomes stable and LSERDYDIE is set.

Cleared by software setting the LSERDYC bit.

0: No clock ready interrupt caused by the LSE oscillator
1: Clock ready interrupt caused by the LSE oscillator


Bit 0 **LSIRDYF:** LSI ready interrupt flag

Set by hardware when the LSI clock becomes stable and LSIRDYDIE is set.

Cleared by software setting the LSIRDYC bit.

0: No clock ready interrupt caused by the LSI oscillator
1: Clock ready interrupt caused by the LSI oscillator


**7.4.4** **APB peripheral reset register 2 (RCC_APB2RSTR)**


Address offset: 0x0C


Reset value: 0x00000 0000


Access: no wait state, word, half-word and byte access

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBGMCU<br>RST|Res.|Res.|Res.|TIM17<br>RST|TIM16<br>RST|TIM15<br>RST|
||||||||||rw||||rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|USART1<br>RST|Res.|SPI1<br>RST|TIM1<br>RST|Res.|ADC<br>RST|Res.|Res.|Res.|USART6<br>RST|Res.|Res.|Res.|Res.|SYSCFG<br>RST|
||rw||rw|rw||rw||||rw|||||rw|



Bits 31:23 Reserved, must be kept at reset value.


Bit 22 **DBGMCURST:** Debug MCU reset

Set and cleared by software.

0: No effect

1: Reset Debug MCU


Bits 21:19 Reserved, must be kept at reset value.


Bit 18 **TIM17RST:** TIM17 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM17 timer


Bit 17 **TIM16RST:** TIM16 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM16 timer


Bit 16 **TIM15RST:** TIM15 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM15 timer


Bit 15 Reserved, must be kept at reset value.


RM0360 Rev 5 107/775



124


**Reset and clock control (RCC)** **RM0360**


Bit 14 **USART1RST:** USART1 reset

Set and cleared by software.

0: No effect

1: Reset USART1


Bit 13 Reserved, must be kept at reset value.


Bit 12 **SPI1RST:** SPI1 reset

Set and cleared by software.

0: No effect

1: Reset SPI1


Bit 11 **TIM1RST:** TIM1 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM1 timer


Bit 10 Reserved, must be kept at reset value.


Bit 9 **ADCRST:** ADC interface reset

Set and cleared by software.

0: No effect

1: Reset ADC interface


Bits 8:6 Reserved, must be kept at reset value.


Bit 5 **USART6RST:** USART6 reset

Set and cleared by software

0: No effect

1: Reset USART6


Bits 4:1 Reserved, must be kept at reset value.


Bit 0 **SYSCFGRST:** SYSCFG reset

Set and cleared by software.

0: No effect

1: Reset SYSCFG


**7.4.5** **APB peripheral reset register 1 (RCC_APB1RSTR)**


Address offset: 0x10


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|PWR<br>RST|Res.|Res.|Res.|Res.|USB<br>RST|I2C2<br>RST|I2C1<br>RST|USART5<br>RST|USART4<br>RST|USART3<br>RST|USART2<br>RST|Res.|
||||rw|||||rw|rw|rw|rw|rw|rw|rw||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|SPI2<br>RST|Res.|Res.|WWDG<br>RST|Res.|Res.|TIM14<br>RST|Res.|Res.|TIM7<br>RST|TIM6<br>RST|Res.|Res.|TIM3<br>RST|Res.|
||rw|||rw|||rw|||rw|rw|||rw||



108/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


Bits 31:29 Reserved, must be kept at reset value.


Bit 28 **PWRRST:** Power interface reset

Set and cleared by software.

0: No effect

1: Reset power interface


Bits 27:24 Reserved, must be kept at reset value.


Bit 23 **USBRST:** USB interface reset

Set and cleared by software.

0: No effect

1: Reset USB interface


Bit 22 **I2C2RST:** I2C2 reset

Set and cleared by software.

0: No effect

1: Reset I2C2


Bit 21 **I2C1RST:** I2C1 reset

Set and cleared by software.

0: No effect

1: Reset I2C1


Bit 20 **USART5RST:** USART5 reset

Set and cleared by software.

0: No effect

1: Reset USART4


Bit 19 **USART4RST:** USART4 reset

Set and cleared by software.

0: No effect

1: Reset USART4


Bit 18 **USART3RST:** USART3 reset

Set and cleared by software.

0: No effect

1: Reset USART3


Bit 17 **USART2RST:** USART2 reset

Set and cleared by software.

0: No effect

1: Reset USART2


Bits 16:15 Reserved, must be kept at reset value.


Bit 14 **SPI2RST:** SPI2 reset

Set and cleared by software.

0: No effect

1: Reset SPI2


Bits 13:12 Reserved, must be kept at reset value.


Bit 11 **WWDGRST:** Window watchdog reset

Set and cleared by software.

0: No effect

1: Reset window watchdog


RM0360 Rev 5 109/775



124


**Reset and clock control (RCC)** **RM0360**


Bits 10:9 Reserved, must be kept at reset value.


Bit 8 **TIM14RST:** TIM14 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM14


Bits 7:6 Reserved, must be kept at reset value.


Bit 5 **TIM7RST:** TIM7 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM7


Bit 4 **TIM6RST:** TIM6 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM6


Bits 3:2 Reserved, must be kept at reset value.


Bit 1 **TIM3RST:** TIM3 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM3


Bit 0 Reserved, must be kept at reset value.


**7.4.6** **AHB peripheral clock enable register (RCC_AHBENR)**


Address offset: 0x14


Reset value: 0x0000 0014


Access: no wait state, word, half-word and byte access


_Note:_ _When the peripheral clock is not active, the peripheral register values may not be readable_
_by software and the returned value is always 0x0._

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GPIOF<br>EN|Res.|GPIOD<br>EN|GPIOC<br>EN|GPIOB<br>EN|GPIOA<br>EN|Res.|
||||||||||rw||rw|rw|rw|rw||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CRC<br>EN|Res.|FLITF<br>EN|Res.|SRAM<br>EN|Res.|DMA<br>EN|
||||||||||rw||rw||rw||rw|



Bits 31:23 Reserved, must be kept at reset value.


Bit 22 **GPIOFEN:** I/O port F clock enable

Set and cleared by software.

0: I/O port F clock disabled
1: I/O port F clock enabled


Bit 21 Reserved, must be kept at reset value.


110/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


Bit 20 **GPIODEN:** I/O port D clock enable

Set and cleared by software.

0: I/O port D clock disabled
1: I/O port D clock enabled


Bit 19 **GPIOCEN:** I/O port C clock enable

Set and cleared by software.

0: I/O port C clock disabled
1: I/O port C clock enabled


Bit 18 **GPIOBEN:** I/O port B clock enable

Set and cleared by software.

0: I/O port B clock disabled
1: I/O port B clock enabled


Bit 17 **GPIOAEN:** I/O port A clock enable

Set and cleared by software.

0: I/O port A clock disabled
1: I/O port A clock enabled


Bits 16:7 Reserved, must be kept at reset value.


Bit 6 **CRCEN:** CRC clock enable

Set and cleared by software.

0: CRC clock disabled

1: CRC clock enabled


Bit 5 Reserved, must be kept at reset value.


Bit 4 **FLITFEN:** FLITF clock enable

Set and cleared by software to disable/enable FLITF clock during Sleep mode.

0: FLITF clock disabled during Sleep mode
1: FLITF clock enabled during Sleep mode


Bit 3 Reserved, must be kept at reset value.


Bit 2 **SRAMEN:** SRAM interface clock enable

Set and cleared by software to disable/enable SRAM interface clock during Sleep mode.

0: SRAM interface clock disabled during Sleep mode.
1: SRAM interface clock enabled during Sleep mode


Bit 1 Reserved, must be kept at reset value.


Bit 0 **DMAEN:** DMA clock enable

Set and cleared by software.

0: DMA clock disabled

1: DMA clock enabled


**7.4.7** **APB peripheral clock enable register 2 (RCC_APB2ENR)**


Address: 0x18


Reset value: 0x0000 0000


Access: word, half-word and byte access


No wait states, except if the access occurs while an access to a peripheral in the APB
domain is on going. In this case, wait states are inserted until the access to APB peripheral
is finished.


RM0360 Rev 5 111/775



124


**Reset and clock control (RCC)** **RM0360**


_Note:_ _When the peripheral clock is not active, the peripheral register values may not be readable_
_by software and the returned value is always 0x0._

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBG<br>MCUEN|Res.|Res.|Res.|TIM17<br>EN|TIM16<br>EN|TIM15<br>EN|
||||||||||rw||||rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|USART1<br>EN|Res.|SPI1<br>EN|TIM1<br>EN|Res.|ADC<br>EN|Res.|Res.|Res.|USART6<br>EN|Res.|Res.|Res.|Res.|SYSCFG<br>COMPEN|
||rw||rw|rw||rw||||rw|||||rw|



Bits 31:23 Reserved, must be kept at reset value.


Bit 22 **DBGMCUEN** MCU debug module clock enable

Set and reset by software.

0: MCU debug module clock disabled
1: MCU debug module enabled


Bits 21:19 Reserved, must be kept at reset value.


Bit 18 **TIM17EN:** TIM17 timer clock enable

Set and cleared by software.

0: TIM17 timer clock disabled

1: TIM17 timer clock enabled


Bit 17 **TIM16EN:** TIM16 timer clock enable

Set and cleared by software.

0: TIM16 timer clock disabled

1: TIM16 timer clock enabled


Bit 16 **TIM15EN:** TIM15 timer clock enable

Set and cleared by software.

0: TIM15 timer clock disabled

1: TIM15 timer clock enabled


Bit 15 Reserved, must be kept at reset value.


Bit 14 **USART1EN:** USART1 clock enable

Set and cleared by software.

0: USART1clock disabled

1: USART1clock enabled


Bit 13 Reserved, must be kept at reset value.


Bit 12 **SPI1EN:** SPI1 clock enable

Set and cleared by software.

0: SPI1 clock disabled

1: SPI1 clock enabled


Bit 11 **TIM1EN:** TIM1 timer clock enable

Set and cleared by software.

0: TIM1 timer clock disabled

1: TIM1P timer clock enabled


112/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


Bit 10 Reserved, must be kept at reset value.


Bit 9 **ADCEN:** ADC interface clock enable

Set and cleared by software.

0: ADC interface disabled

1: ADC interface clock enabled


Bits 8:6 Reserved, must be kept at reset value.


Bit 5 **USART6EN:** USART6 clock enable

Set and cleared by software.

0: USART6clock disabled

1: USART6clock enabled


Bits 4:1 Reserved, must be kept at reset value.


Bit 0 **SYSCFGEN:** SYSCFG clock enable

Set and cleared by software.

0: SYSCFG clock disabled

1: SYSCFG clock enabled


**7.4.8** **APB peripheral clock enable register 1 (RCC_APB1ENR)**


Address: 0x1C


Reset value: 0x0000 0000


Access: word, half-word and byte access


No wait state, except if the access occurs while an access to a peripheral on APB domain is
on going. In this case, wait states are inserted until this access to APB peripheral is finished.


_Note:_ _When the peripheral clock is not active, the peripheral register values may not be readable_
_by software and the returned value is always 0x0._

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|PWR<br>EN|Res.|Res.|Res.|Res.|USB<br>EN|I2C2<br>EN|I2C1<br>EN|USART5<br>EN|USART4<br>EN|USART3<br>EN|USART2<br>EN|Res.|
||||rw|||||rw|rw|rw|rw|rw|rw|rw||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|SPI2<br>EN|Res.|Res.|WWDG<br>EN|Res.|Res.|TIM14<br>EN|Res.|Res.|TIM7<br>EN|TIM6<br>EN|Res.|Res.|TIM3<br>EN|Res.|
||rw|||rw|||rw|||rw|rw|||rw||



Bits 31:29 Reserved, must be kept at reset value.


Bit 28 **PWREN:** Power interface clock enable

Set and cleared by software.

0: Power interface clock disabled

1: Power interface clock enabled


Bits 27:24 Reserved, must be kept at reset value.


RM0360 Rev 5 113/775



124


**Reset and clock control (RCC)** **RM0360**


Bit 23 **USBEN:** USB interface clock enable

Set and cleared by software.

0: USB interface clock disabled

1: USB interface clock enabled


Bit 22 **I2C2EN:** I2C2 clock enable

Set and cleared by software.

0: I2C2 clock disabled

1: I2C2 clock enabled


Bit 21 **I2C1EN:** I2C1 clock enable

Set and cleared by software.

0: I2C1 clock disabled

1: I2C1 clock enabled


Bit 20 **USART5EN:** USART5 clock enable

Set and cleared by software.

0: USART5 clock disabled

1: USART5 clock enabled


Bit 19 **USART4EN:** USART4 clock enable

Set and cleared by software.

0: USART4 clock disabled

1: USART4 clock enabled


Bit 18 **USART3EN:** USART3 clock enable

Set and cleared by software.

0: USART3 clock disabled

1: USART3 clock enabled


Bit 17 **USART2EN:** USART2 clock enable

Set and cleared by software.

0: USART2 clock disabled

1: USART2 clock enabled


Bits 16:15 Reserved, must be kept at reset value.


Bit 14 **SPI2EN:** SPI2 clock enable

Set and cleared by software.

0: SPI2 clock disabled

1: SPI2 clock enabled


Bits 13:12 Reserved, must be kept at reset value.


Bit 11 **WWDGEN:** Window watchdog clock enable

Set and cleared by software.

0: Window watchdog clock disabled
1: Window watchdog clock enabled


Bits 10:9 Reserved, must be kept at reset value.


Bit 8 **TIM14EN:** TIM14 timer clock enable

Set and cleared by software.

0: TIM14 clock disabled

1: TIM14 clock enabled


Bits 7:6 Reserved, must be kept at reset value.


114/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


Bit 5 **TIM7EN:** TIM7 timer clock enable (not available on STM32F070x6, nor STM32F030x4/6/8/C
devices).

Set and cleared by software.

0: TIM7 clock disabled

1: TIM7 clock enabled


Bit 4 **TIM6EN:** TIM6 timer clock enable

Set and cleared by software.

0: TIM6 clock disabled

1: TIM6 clock enabled


Bits 3:2 Reserved, must be kept at reset value.


Bit 1 **TIM3EN:** TIM3 timer clock enable

Set and cleared by software.

0: TIM3 clock disabled

1: TIM3 clock enabled


Bit 0

Reserved, must be kept at reset value.


**7.4.9** **RTC domain control register (RCC_BDCR)**


Address offset: 0x20


Reset value: 0x0000 0018, reset by RTC domain reset.


Access: 0 ≤ wait state ≤ 3, word, half-word and byte access


Wait states are inserted in case of successive accesses to this register.


_Note:_ _The LSEON, LSEBYP, RTCSEL and RTCEN bits of the RTC domain control register_
_(RCC_BDCR) are in the RTC domain. As a result, after reset, these bits are write-protected_
_and the DBP bit in the Power control register (PWR_CR) has to be set before they can be_
_modified. Refer to Section 6.1.2: Voltage regulator_ _for further information. These bits are_
_only reset after a RTC domain reset (see Section 7.1.3: RTC domain reset). Any internal or_
_external reset does not have any effect on these bits._

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|BDRST|
||||||||||||||||rw|


|15|14|13|12|11|10|9 8|Col8|7|6|5|4 3|Col13|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|RTC<br>EN|Res.|Res.|Res.|Res.|Res.|RTCSEL[1:0]|RTCSEL[1:0]|Res.|Res.|Res.|LSEDRV[1:0]|LSEDRV[1:0]|LSE<br>BYP|LSE<br>RDY|LSEON|
|rw||||||rw|rw||||rw|rw|rw|r|rw|



Bits 31:17 Reserved, must be kept at reset value.


Bit 16 **BDRST:** RTC domain software reset

Set and cleared by software.

0: Reset not activated

1: Resets the entire RTC domain


RM0360 Rev 5 115/775



124


**Reset and clock control (RCC)** **RM0360**


Bit 15 **RTCEN:** RTC clock enable

Set and cleared by software.

0: RTC clock disabled

1: RTC clock enabled


Bits 14:10 Reserved, must be kept at reset value.


Bits 9:8 **RTCSEL[1:0]:** RTC clock source selection

Set by software to select the clock source for the RTC. Once the RTC clock source has been
selected, it cannot be changed anymore unless the RTC domain is reset. The BDRST bit can
be used to reset them.

00: No clock

01: LSE oscillator clock used as RTC clock

10: LSI oscillator clock used as RTC clock

11: HSE oscillator clock divided by 32 used as RTC clock


Bits 7:5 Reserved, must be kept at reset value.


Bits 4:3 **LSEDRV** LSE oscillator drive capability

Set and reset by software to modulate the LSE oscillator’s drive capability. A reset of the RTC
domain restores the default value.

00: ‘Xtal mode’ low drive capability
01: ‘Xtal mode’ medium-high drive capability
10: ‘Xtal mode’ medium-low drive capability
11: ‘Xtal mode’ high drive capability (reset value)

_Note: The oscillator is in Xtal mode when it is not in bypass mode._


Bit 2 **LSEBYP:** LSE oscillator bypass

Set and cleared by software to bypass oscillator in debug mode. This bit can be written only
when the external 32 kHz oscillator is disabled.

0: LSE oscillator not bypassed
1: LSE oscillator bypassed


Bit 1 **LSERDY:** LSE oscillator ready

Set and cleared by hardware to indicate when the external 32 kHz oscillator is stable. After the
LSEON bit is cleared, LSERDY goes low after 6 external low-speed oscillator clock cycles.

0: LSE oscillator not ready
1: LSE oscillator ready


Bit 0 **LSEON:** LSE oscillator enable

Set and cleared by software.

0: LSE oscillator OFF

1: LSE oscillator ON


**7.4.10** **Control/status register (RCC_CSR)**


Address: 0x24


Reset value: 0xXXX0 0000, reset by system Reset, except reset flags by power Reset only.


Access: 0 ≤ wait state ≤ 3, word, half-word and byte access


Wait states are inserted in case of successive accesses to this register.


116/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|LPWR<br>RSTF|WWDG<br>RSTF|IWDG<br>RSTF|SFT<br>RSTF|POR<br>RSTF|PIN<br>RSTF|OB<br>LRSTF|RMVF|V18PWR<br>RSTF|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|r|r|r|r|r|r|r|rt_w|r||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LSI<br>RDY|LSION|
|||||||||||||||r|rw|



Bit 31 **LPWRRSTF:** Low-power reset flag

Set by hardware when a Low-power management reset occurs.
Cleared by writing to the RMVF bit.

0: No Low-power management reset occurred
1: Low-power management reset occurred

For further information refer to _Low-power management reset_ .


Bit 30 **WWDGRSTF:** Window watchdog reset flag

Set by hardware when a window watchdog reset occurs.
Cleared by writing to the RMVF bit.

0: No window watchdog reset occurred
1: Window watchdog reset occurred


Bit 29 **IWDGRSTF:** Independent watchdog reset flag

Set by hardware when an independent watchdog reset from V DD domain occurs.
Cleared by writing to the RMVF bit.

0: No watchdog reset occurred
1: Watchdog reset occurred


Bit 28 **SFTRSTF:** Software reset flag

Set by hardware when a software reset occurs.
Cleared by writing to the RMVF bit.

0: No software reset occurred

1: Software reset occurred


Bit 27 **PORRSTF:** POR/PDR reset flag

Set by hardware when a POR/PDR reset occurs.

Cleared by writing to the RMVF bit.

0: No POR/PDR reset occurred

1: POR/PDR reset occurred


Bit 26 **PINRSTF:** PIN reset flag

Set by hardware when a reset from the NRST pin occurs.

Cleared by writing to the RMVF bit.

0: No reset from NRST pin occurred
1: Reset from NRST pin occurred


Bit 25 **OBLRSTF:** Option byte loader reset flag

Set by hardware when a reset from the OBL occurs.

Cleared by writing to the RMVF bit.

0: No reset from OBL occurred

1: Reset from OBL occurred


RM0360 Rev 5 117/775



124


**Reset and clock control (RCC)** **RM0360**


Bit 24 **RMVF:** Remove reset flag

Set by software to clear the reset flags including RMVF.

0: No effect

1: Clear the reset flags


Bit 23 **V18PWRRSTF:** Reset flag of the 1.8 V domain.

Set by hardware when a POR/PDR of the 1.8 V domain occurred.

Cleared by writing to the RMVF bit.

0: No POR/PDR reset of the 1.8 V domain occurred

1: POR/PDR reset of the 1.8 V domain occurred


Bits 22:2 Reserved, must be kept at reset value.


Bit 1 **LSIRDY:** LSI oscillator ready

Set and cleared by hardware to indicate when the LSI oscillator is stable. After the LSION bit is
cleared, LSIRDY goes low after 3 LSI oscillator clock cycles.

0: LSI oscillator not ready
1: LSI oscillator ready


Bit 0 **LSION:** LSI oscillator enable

Set and cleared by software.

0: LSI oscillator OFF

1: LSI oscillator ON


**7.4.11** **AHB peripheral reset register (RCC_AHBRSTR)**


Address: 0x28


Reset value: 0x0000 0000


Access: no wait states, word, half-word and byte access









|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GPIOF<br>RST|Res.|GPIO<br>D<br>RST|GPIO<br>C<br>RST|GPIOB<br>RST|GPIOA<br>RST|Res.|
||||||||||rw||rw|rw|rw|rw||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


Bits 31:23 Reserved, must be kept at reset value.


Bit 22 **GPIOFRST:** I/O port F reset

Set and cleared by software.

0: No effect

1: Reset I/O port F


Bit 21

Reserved, must be kept at reset value.


118/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


Bit 20 **GPIODRST:** I/O port D reset

Set and cleared by software.

0: No effect

1: Reset I/O port D


Bit 19 **GPIOCRST:** I/O port C reset

Set and cleared by software.

0: No effect

1: Reset I/O port C


Bit 18 **GPIOBRST:** I/O port B reset

Set and cleared by software.

0: No effect

1: Reset I/O port B


Bit 17 **GPIOARST:** I/O port A reset

Set and cleared by software.

0: No effect

1: Reset I/O port A


Bits 16:0 Reserved, must be kept at reset value.


**7.4.12** **Clock configuration register 2 (RCC_CFGR2)**


Address: 0x2C


Reset value: 0x0000 0000


Access: no wait states, word, half-word and byte access

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PREDIV[3:0]|PREDIV[3:0]|PREDIV[3:0]|PREDIV[3:0]|
|||||||||||||rw|rw|rw|rw|



Bits 31:4 Reserved, must be kept at reset value.


RM0360 Rev 5 119/775



124


**Reset and clock control (RCC)** **RM0360**


Bits 3:0 **PREDIV[3:0]** PREDIV division factor

These bits are set and cleared by software to select PREDIV division factor. They can be
written only when the PLL is disabled.

_Note: Bit 0 is the same bit as bit 17 in Clock configuration register (RCC_CFGR), so_
_modifying bit 17 in Clock configuration register (RCC_CFGR) also modifies bit 0 in_
_Clock configuration register 2 (RCC_CFGR2) (for compatibility with other STM32_
_products)_

0000: PREDIV input clock not divided
0001: PREDIV input clock divided by 2
0010: PREDIV input clock divided by 3
0011: PREDIV input clock divided by 4
0100: PREDIV input clock divided by 5
0101: PREDIV input clock divided by 6
0110: PREDIV input clock divided by 7
0111: PREDIV input clock divided by 8
1000: PREDIV input clock divided by 9
1001: PREDIV input clock divided by 10
1010: PREDIV input clock divided by 11
1011: PREDIV input clock divided by 12
1100: PREDIV input clock divided by 13
1101: PREDIV input clock divided by 14
1110: PREDIV input clock divided by 15
1111: PREDIV input clock divided by 16


**7.4.13** **Clock configuration register 3 (RCC_CFGR3)**


Address: 0x30


Reset value: 0x0000 0000


Access: no wait states, word, half-word and byte access

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADC<br>SW|USB<br>SW|Res.|Res.|I2C1<br>SW|Res.|Res.|USART1SW[1:0]|USART1SW[1:0]|
||||||||rw|rw|||rw|||rw|rw|



Bits 31:9 Reserved, must be kept at reset value.


Bit 8 **ADCSW:** ADC clock source selection


Obsolete setting. To be kept at reset value, connecting the HSI14 clock to the ADC
asynchronous clock input. Proper ADC clock selection is done inside the ADC_CFGR2 (refer
to _Section 12.10.5: ADC configuration register 2 (ADC_CFGR2) on page 220_ ).


Bit 7 **USBSW:** USB clock source selection

This bit is set and cleared by software to select the USB clock source.

0: USB clock disabled (default)
1: PLL clock (PLLCLK) selected as USB clock


120/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


Bits 6:5 Reserved, must be kept at reset value.


Bit 4 **I2C1SW:** I2C1 clock source selection

This bit is set and cleared by software to select the I2C1 clock source.

0: HSI clock selected as I2C1 clock source (default)
1: System clock (SYSCLK) selected as I2C1 clock


Bits 3:2 Reserved, must be kept at reset value.


Bits 1:0 **USART1SW[1:0]:** USART1 clock source selection

This bit is set and cleared by software to select the USART1 clock source.

00: PCLK selected as USART1 clock source (default)
01: System clock (SYSCLK) selected as USART1 clock

10: LSE clock selected as USART1 clock

11: HSI clock selected as USART1 clock


**7.4.14** **Clock control register 2 (RCC_CR2)**


Address: 0x34


Reset value: 0xXX00 XX80, where X is undefined.


Access: no wait states, word, half-word and byte access

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3|Col10|Col11|Col12|Col13|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14TRIM[4:0]|HSI14TRIM[4:0]|HSI14TRIM[4:0]|HSI14TRIM[4:0]|HSI14TRIM[4:0]|HSI14<br>DIS|HSI14<br>RDY|HSI14<br>ON|
|r|r|r|r|r|r|r|r|rw|rw|rw|rw|rw|rw|r|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:8 **HSI14CAL[7:0]:** HSI14 clock calibration

These bits are initialized automatically at startup.


Bits 7:3 **HSI14TRIM[4:0]:** HSI14 clock trimming

These bits provide an additional user-programmable trimming value that is added to the
HSI14CAL[7:0] bits. It can be programmed to adjust to variations in voltage and temperature
that influence the frequency of the HSI14.

The default value is 16, which, when added to the HSI14CAL value, should trim the HSI14 to
14 MHz ± 1%. The trimming step is around 50 kHz between two consecutive HSI14CAL steps.


Bit 2 **HSI14DIS** HSI14 clock request from ADC disable

Set and cleared by software.

When set this bit prevents the ADC interface from enabling the HSI14 oscillator.

0: ADC interface can turn on the HSI14 oscillator

1: ADC interface can not turn on the HSI14 oscillator


RM0360 Rev 5 121/775



124


**Reset and clock control (RCC)** **RM0360**


Bit 1 **HSI14RDY:** HSI14 clock ready flag

Set by hardware to indicate that HSI14 oscillator is stable. After the HSI14ON bit is cleared,
HSI14RDY goes low after 6 HSI14 oscillator clock cycles. When HSI14ON is not set but the
HSI14 oscillator is enabled by the peripheral through a clock request, this bit is not set.

0: HSI14 oscillator not ready
1: HSI14 oscillator ready


Bit 0 **HSI14ON:** HSI14 clock enable

Set and cleared by software. When the HSI14 oscillator is enabled by the peripheral through a
clock request, this bit is not set and resetting it does not stop the HSI14 oscillator.

0: HSI14 oscillator OFF

1: HSI14 oscillator ON


122/775 RM0360 Rev 5


**RM0360** **Reset and clock control (RCC)**


**7.4.15** **RCC register map**


The following table gives the RCC register map and the reset values.


**Table 21. RCC register map and reset values**

























|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**RCC_CR**|Res.|Res.|Res.|Res.|Res.|Res.|PLL RDY|PLL ON|Res.|Res.|Res.|Res.|CSSON|HSEBYP<br>|HSERD|HSEON|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSITRIM[4:0]|HSITRIM[4:0]|HSITRIM[4:0]|HSITRIM[4:0]|HSITRIM[4:0]|Res.|HSIRDY|HSION|
|0x00|Reset value|||||||0|0|||||0|0|0|0|0|0|0|0|0|0|0|0|1|0|0|0|0||1|1|
|0x04|**RCC_CFGR**|PLL NODIV|MCOPRE<br>[2:0]|MCOPRE<br>[2:0]|MCOPRE<br>[2:0]|MCO [3:0]|MCO [3:0]|MCO [3:0]|MCO [3:0]|Res.|Res.|PLLMUL[3:0]|PLLMUL[3:0]|PLLMUL[3:0]|PLLMUL[3:0]|PLLXTPRE|PLLSRC[1:0]|PLLSRC[1:0]|ADC PRE|Res.|Res.|Res.|PPRE<br>[2:0]|PPRE<br>[2:0]|PPRE<br>[2:0]|HPRE[3:0]|HPRE[3:0]|HPRE[3:0]|HPRE[3:0]|SWS<br>[1:0]|SWS<br>[1:0]|SW<br>[1:0]|SW<br>[1:0]|
|0x04|Reset value|0|0|0|0|0|0|0|0|||0|0|0|0|0|0|0|0||||0|0|0|0|0|0|0|0|0|0|0|
|0x08|**RCC_CIR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CSSC|Res.|HSI14 RDYC|PLLRDYC|HSERDYC|HSIRDYC|LSERDYC|LSIRDYC|Res.|Res.|HSI14 RDYIE|PLLRDYIE|HSERDYIE|HSIRDYIE|LSERDYIE|LSIRDYIE|CSSF|Res.|HSI14 RDYF|PLLRDYF|HSERDYF|HSIRDYF|LSERDYF|LSIRDYF|
|0x08|Reset value|||||||||0||0|0|0|0|0|0|||0|0|0|0|0|0|0||0|0|0|0|0|0|
|0x0C|**RCC_APB2RSTR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.<br>|DBGMCURS|Res.|Res.|Res.|TIM17RST|TIM16RST|TIM15RST|Res.|USART1RST|Res.|SPI1RST|TIM1RST|Res.|ADCRST|Res.|Res.|Res.|USART6RST|Res.|Res.|Res.|Res.|SYSCFGRST|
|0x0C|Reset value||||||||||0||||0|0|0||0||0|0||0|||0|0|||||0|
|0x010|**RCC_APB1RSTR**<br>|Res.|Res.|Res.|PWRRST|CRSRST|Res.|Res.|Res.|USBRST|I2C2RST|I2C1RST|USART5RST|USART4RST|USART3RST|USART2RST|Res.|Res.|SPI2RST|Res.|Res.|WWDGRST|Res.|Res.|TIM14RST|Res.|Res.|TM7RST|TM6RST|Res.|Res.|TIM3RST|Res.|
|0x010|Reset value||||0|0||||0|0|0|0|0|0|0|||0|||0|||0|||0|0|||0||
|0x14|**RCC_AHBENR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GPIOEEN|USART4RST|GPIOCEN|GPIOBEN|GPIOAEN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CRCEN|Res.|FLITFEN|Res.|SRAMEN|Res.|DMAEN|
|0x14|Reset value||||||||||||0|0|0|0|||||||||||0||1||1||0|
|0x18|**RCC_APB2ENR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBGMCUEN|Res.|Res.|Res.|TIM17 EN|TIM16 EN|TIM15 EN|Res.|USART1EN|Res.|SPI1EN|TIM1EN|Res.|ADCEN|Res.|Res.|Res.|USART6EN|Res.|Res.|Res.|Res.|SYSCFGEN|
|0x18|Reset value||||||||||0||||0|0|0||0||0|0||0||||0|||||0|
|0x1C|**RCC_APB1ENR**|Res.|Res.|Res.|PWREN|CRSEN|Res.|Res.|Res.|USBEN|I2C2EN|I2C1EN|USART5EN|USART4EN|USART3EN|USART2EN|Res.|Res.|SPI2EN|Res.|Res.|WWDGEN|Res.|Res.|TIM14EN|Res.|Res.|TIM7EN|TIM6EN|Res.|Res.|TIM3EN|Res.|
|0x1C|Reset value||||0|0||||0|0|0|0|0|0|0|||0|||0|||0|||0|0|||0||
|0x20|**RCC_BDCR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|BDRST|RTCEN|Res.|Res.|Res.|Res.|Res.|RTC<br>SEL<br>[1:0]|RTC<br>SEL<br>[1:0]|Res.|Res.|Res.|LSE<br>DRV<br>[1:0]|LSE<br>DRV<br>[1:0]|LSEBYP|LSERDY|LSEON|
|0x20|Reset value||||||||||||||||0|0||||||0|0||||0|0|0|0|0|
|0x24|**RCC_CSR**|LPWRSTF|WWDGRSTF|IWDGRSTF|SFTRSTF|PORRSTF|PINRSTF|OBLRSTF|RMVF|V18PWR RSTF|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LSIRDY|LSION|
|0x24|Reset value|X|X|X|X|X|X|X|X|X||||||||||||||||||||||0|0|


RM0360 Rev 5 123/775



124


**Reset and clock control (RCC)** **RM0360**


**Table 21. RCC register map and reset values (continued)**













|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x28|**RCC_AHBRSTR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GPIOF RST|Res.|GPIOD RST|GPIOC RST|GPIOB RST|GPIOA RST|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x28|Reset value||||||||||0||0|0|0|0||||||||||||||||||
|0x2C|**RCC_CFGR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PREDIV[3:0]|PREDIV[3:0]|PREDIV[3:0]|PREDIV[3:0]|
|0x2C|Reset value|||||||||||||||||||||||||||||0|0|0|0|
|0x30|**RCC_CFGR3**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.|ADCSW|USBSW<br>|Res.<br>|Res.|I2C1SW<br>|Res.<br>|Res.|USART1SW[1:0]|USART1SW[1:0]|
|0x30|Reset value||||||||||||||||||||||||0|0|||0|||0|0|
|0x34|**RCC_CR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14CAL[7:0]|HSI14TRIM[14:0]|HSI14TRIM[14:0]|HSI14TRIM[14:0]|HSI14TRIM[14:0]|HSI14TRIM[14:0]|HSI14DIS|HSI14RDY|HSI14ON|
|0x34|Reset value|||||||||||||||||X|X|X|X|X|X|X|X|1|0|0|0|0|0|0|0|


Refer to _Section 2.2 on page 37_ for the register boundary addresses.


124/775 RM0360 Rev 5


