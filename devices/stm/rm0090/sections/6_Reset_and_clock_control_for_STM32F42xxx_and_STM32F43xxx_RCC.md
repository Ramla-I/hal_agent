**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**

# **6 Reset and clock control for** **STM32F42xxx and STM32F43xxx (RCC)**

## **6.1 Reset**


There are three types of reset, defined as system Reset, power Reset and backup domain
Reset.


**6.1.1** **System reset**


A system reset sets all registers to their reset values unless specified otherwise in the
register description (see _Figure 10_ ).


A system reset is generated when one of the following events occurs:


1. A low level on the NRST pin (external reset)


2. Window watchdog end of count condition (WWDG reset)


3. Independent watchdog end of count condition (IWDG reset)


4. A software reset (SW reset) (see _Software reset_ )


5. Low-power management reset (see _Low-power management reset_ )


**Software reset**


The reset source can be identified by checking the reset flags in the _RCC clock control &_
_status register (RCC_CSR)_ .


The SYSRESETREQ bit in Cortex [®] -M4 with FPU Application Interrupt and Reset Control
Register must be set to force a software reset on the device. Refer to the Cortex [®] -M4 with
FPU technical reference manual for more details.


**Low-power management reset**


There are two ways of generating a low-power management reset:


1. Reset generated when entering the Standby mode:


This type of reset is enabled by resetting the nRST_STDBY bit in the user option bytes.
In this case, whenever a Standby mode entry sequence is successfully executed, the
device is reset instead of entering the Standby mode.


2. Reset when entering the Stop mode:


This type of reset is enabled by resetting the nRST_STOP bit in the user option bytes.
In this case, whenever a Stop mode entry sequence is successfully executed, the
device is reset instead of entering the Stop mode.


**6.1.2** **Power reset**


A power reset is generated when one of the following events occurs:


1. Power-on/power-down reset (POR/PDR reset) or brownout (BOR) reset


2. When exiting the Standby mode


A power reset sets all registers to their reset values except the Backup domain (see
_Figure 10_ )


152/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


These sources act on the NRST pin and it is always kept low during the delay phase. The
RESET service routine vector is fixed at address 0x0000_0004 in the memory map.


The system reset signal provided to the device is output on the NRST pin. The pulse
generator guarantees a minimum reset pulse duration of 20 µs for each internal reset
source. In case of an external reset, the reset pulse is generated while the NRST pin is
asserted low.


**Figure 15. Simplified diagram of the reset circuit**















The Backup domain has two specific resets that affect only the Backup domain (see
_Figure 10_ ).


**6.1.3** **Backup domain reset**


The backup domain reset sets all RTC registers, the RCC_BDCR register, and the BRE bit
of the PWR_CSR register to their reset values. The BKPSRAM is not affected by this reset.
The only way of resetting the BKPSRAM is through the Flash interface by requesting a
protection level change from 1 to 0.


A backup domain reset is generated when one of the following events occurs:


1. Software reset, triggered by setting the BDRST bit in the _RCC Backup domain control_
_register (RCC_BDCR)_ .


2. V DD or V BAT power on, if both supplies have previously been powered off.


_Note:_ _The DBP bit of the PWR_CR register must be set to generate a backup domain reset._

## **6.2 Clocks**


Three different clock sources can be used to drive the system clock (SYSCLK):


      - HSI oscillator clock


      - HSE oscillator clock


      - Main PLL (PLL) clock


The devices have the two following secondary clock sources:


      - 32 kHz low-speed internal RC (LSI RC) which drives the independent watchdog and,
optionally, the RTC used for Auto-wakeup from the Stop/Standby mode.


      - 32.768 kHz low-speed external crystal (LSE crystal) which optionally drives the RTC
clock (RTCCLK)


RM0090 Rev 21 153/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Each clock source can be switched on or off independently when it is not used, to optimize
power consumption.






































|Col1|C en|
|---|---|
|||
||/8|






























|Col1|Col2|Col3|L|
|---|---|---|---|
|||||
|||||
|||||
|||||
|PLL<br>VC~~O~~<br>xN<br>/P<br>/Q<br>/R|PLL<br>VC~~O~~<br>xN<br>/P<br>/Q<br>/R|PLL<br>VC~~O~~<br>xN<br>/P<br>/Q<br>/R||
|PLL<br>VC~~O~~<br>xN<br>/P<br>/Q<br>/R|/P|/P|/P|
|PLL<br>VC~~O~~<br>xN<br>/P<br>/Q<br>/R|/P|||
|PLL<br>VC~~O~~<br>xN<br>/P<br>/Q<br>/R|/Q|/Q||
|PLL<br>VC~~O~~<br>xN<br>/P<br>/Q<br>/R|/R|/R|/R|
|||||
|||||
|VC~~O~~<br>xN|/P|/P|/P|
|VC~~O~~<br>xN|/Q<br>|||










|VCO|/P|
|---|---|
|xN|/Q<br>/R|
|PLLSAI|PLLSAI|










|PHY Ethernet<br>25 to 50 MHz|Col2|
|---|---|
|PHY Ethernet<br>25 to 50 MHz||





1. For full details about the internal and external clock source characteristics, refer to the Electrical characteristics section in
the device datasheet.


2. When TIMPRE bit of the RCC_DCKCFGR register is reset, if APBx prescaler is 1, then TIMxCLK = PCLKx, otherwise
TIMxCLK = 2x PCLKx.


3. When TIMPRE bit in the RCC_DCKCFGR register is set, if APBx prescaler is 1,2 or 4, then TIMxCLK = HCLK, otherwise
TIMxCLK = 4x PCLKx.


154/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


The clock controller provides a high degree of flexibility to the application in the choice of the
external crystal or the oscillator to run the core and peripherals at the highest frequency
and, guarantee the appropriate frequency for peripherals that need a specific clock like
Ethernet, USB OTG FS and HS, I2S, SAI, LTDC, and SDIO.


Several prescalers are used to configure the AHB frequency, the high-speed APB (APB2)
and the low-speed APB (APB1) domains. The maximum frequency of the AHB domain is
180 MHz. The maximum allowed frequency of the high-speed APB2 domain is 90 MHz. The
maximum allowed frequency of the low-speed APB1 domain is 45 MHz


All peripheral clocks are derived from the system clock (SYSCLK) except for:


      - The USB OTG FS clock (48 MHz), the random analog generator (RNG) clock
( ≤ 48 MHz) and the SDIO clock ( ≤ 48 MHz) which are coming from a specific output of
PLL (PLL48CLK)


      - I2S clock


To achieve high-quality audio performance, the I2S clock can be derived either from a
specific PLL (PLLI2S) or from an external clock mapped on the I2S_CKIN pin. For
more information about I2S clock frequency and precision, refer to _Section 28.4.4:_
_Clock generator_ .


      - SAI1 clock


The SAI1 clock is generated from a specific PLL (PLLSAI or PLLI2S) or from an
external clock mapped on the I2S_CKIN pin.


The PLLSAI can be used as clock source for SAI1 peripheral in case the PLLI2S is
programmed to achieve another audio sampling frequency (49.152 MHz or
11.2896 MHz), and the application requires both frequencies at the same time.


      - LTDC clock


The LTDC clock is generated from a specific PLL (PLLSAI).


      - The USB OTG HS (60 MHz) clock which is provided from the external PHY


      - The Ethernet MAC clocks (TX, RX and RMII) which are provided from the external
PHY. For further information on the Ethernet configuration, please refer to
_Section 33.4.4: MII/RMII selection_ in the Ethernet peripheral description. When the
Ethernet is used, the AHB clock frequency must be at least 25 MHz.


The RCC feeds the external clock of the Cortex System Timer (SysTick) with the AHB clock
(HCLK) divided by 8. The SysTick can work either with this clock or with the Cortex clock
(HCLK), configurable in the SysTick control and status register.


The timer clock frequencies for STM32F42xxx and STM32F43xxx are automatically set by
hardware. There are two cases depending on the value of TIMPRE bit in RCC_CFGR
register:


      - If TIMPRE bit in RCC_DKCFGR register is reset:


If the APB prescaler is configured to a division factor of 1, the timer clock frequencies
(TIMxCLK) are set to PCLKx. Otherwise, the timer clock frequencies are twice the
frequency of the APB domain to which the timers are connected: TIMxCLK = 2xPCLKx.


      - If TIMPRE bit in RCC_DKCFGR register is set:


If the APB prescaler is configured to a division factor of 1, 2 or 4, the timer clock
frequencies (TIMxCLK) are set to HCLK. Otherwise, the timer clock frequencies is four
times the frequency of the APB domain to which the timers are connected: TIMxCLK =
4xPCLKx.


RM0090 Rev 21 155/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


FCLK acts as Cortex [®] -M4 with FPU free-running clock. For more details, refer to the
Cortex [®] -M4 with FPU technical reference manual.


**6.2.1** **HSE clock**


The high speed external clock signal (HSE) can be generated from two possible clock

sources:


      - HSE external crystal/ceramic resonator


      - HSE external user clock


The resonator and the load capacitors have to be placed as close as possible to the
oscillator pins in order to minimize output distortion and startup stabilization time. The
loading capacitance values must be adjusted according to the selected oscillator.


**Figure 17. HSE/ LSE clock sources**

|Col1|Hardware configuration|
|---|---|
|External clock|OSC_OUT<br>External<br>source<br>(HI-Z)|
|Crystal/ceramic<br>resonators|OSC_IN<br>OSC_OUT<br>Load<br>capacitors<br>CL2<br>CL1|



**External source (HSE bypass)**


In this mode, an external clock source must be provided. You select this mode by setting the
HSEBYP and HSEON bits in the _RCC clock control register (RCC_CR)_ . The external clock
signal (square, sinus or triangle) with ~50% duty cycle has to drive the OSC_IN pin while the
OSC_OUT pin should be left HI-Z. See _Figure 17_ .


**External crystal/ceramic resonator (HSE crystal)**


The HSE has the advantage of producing a very accurate rate on the main clock.


The associated hardware configuration is shown in _Figure 17_ . Refer to the electrical
characteristics section of the _datasheet_ for more details.


The HSERDY flag in the _RCC clock control register (RCC_CR)_ indicates if the high-speed
external oscillator is stable or not. At startup, the clock is not released until this bit is set by
hardware. An interrupt can be generated if enabled in the _RCC clock interrupt register_
_(RCC_CIR)_ .


156/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


The HSE Crystal can be switched on and off using the HSEON bit in the _RCC clock control_
_register (RCC_CR)_ .


**6.2.2** **HSI clock**


The HSI clock signal is generated from an internal 16 MHz RC oscillator and can be used
directly as a system clock, or used as PLL input.


The HSI RC oscillator has the advantage of providing a clock source at low cost (no external
components). It also has a faster startup time than the HSE crystal oscillator however, even
with calibration the frequency is less accurate than an external crystal oscillator or ceramic
resonator.


**Calibration**


RC oscillator frequencies can vary from one chip to another due to manufacturing process
variations, this is why each device is factory calibrated by ST for 1% accuracy at T A = 25 °C.


After reset, the factory calibration value is loaded in the HSICAL[7:0] bits in the _RCC clock_
_control register (RCC_CR)_ .


If the application is subject to voltage or temperature variations this may affect the RC
oscillator speed. You can trim the HSI frequency in the application using the HSITRIM[4:0]
bits in the _RCC clock control register (RCC_CR)_ .


The HSIRDY flag in the _RCC clock control register (RCC_CR)_ indicates if the HSI RC is
stable or not. At startup, the HSI RC output clock is not released until this bit is set by
hardware.


The HSI RC can be switched on and off using the HSION bit in the _RCC clock control_
_register (RCC_CR)_ .


The HSI signal can also be used as a backup source (Auxiliary clock) if the HSE crystal
oscillator fails. Refer to _Section 6.2.7: Clock security system (CSS) on page 159_ .


**6.2.3** **PLL configuration**


The STM32F4xx devices feature three PLLs:


      - A main PLL (PLL) clocked by the HSE or HSI oscillator and featuring two different
output clocks:


–
The first output is used to generate the high speed system clock (up to 180 MHz)


–
The second output is used to generate the clock for the USB OTG FS (48 MHz),
the random analog generator ( ≤ 48 MHz) and the SDIO ( ≤ 48 MHz).


      - Two dedicated PLLs (PLLI2S and PLLSAI) used to generate an accurate clock to
achieve high-quality audio performance on the I2S and SAI1 interfaces. PLLSAI is also
used for the LCD-TFT clock.


Since the main-PLL configuration parameters cannot be changed once PLL is enabled, it is
recommended to configure PLL before enabling it (selection of the HSI or HSE oscillator as
PLL clock source, and configuration of division factors M, N, P, and Q).


The PLLI2S and PLLSAI use the same input clock as PLL (PLLM[5:0] and PLLSRC bits are
common to both PLLs). However, the PLLI2S and PLLSAI have dedicated enable/disable
and division factors (N and R) configuration bits. Once the PLLI2S and PLLSAI are enabled,
the configuration parameters cannot be changed.


RM0090 Rev 21 157/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


The three PLLs are disabled by hardware when entering Stop and Standby modes, or when
an HSE failure occurs when HSE or PLL (clocked by HSE) are used as system clock. _RCC_
_PLL configuration register (RCC_PLLCFGR)_, _RCC clock configuration register_
_(RCC_CFGR)_, and _RCC Dedicated Clock Configuration Register (RCC_DCKCFGR)_ can be
used to configure PLL, PLLI2S, and PLLSAI.


**6.2.4** **LSE clock**


The LSE clock is generated from a 32.768 kHz low-speed external crystal or ceramic
resonator. It has the advantage providing a low-power but highly accurate clock source to
the real-time clock peripheral (RTC) for clock/calendar or other timing functions.


The LSE oscillator is switched on and off using the LSEON bit in _RCC Backup domain_
_control register (RCC_BDCR)_ .


The LSERDY flag in the _RCC Backup domain control register (RCC_BDCR)_ indicates if the
LSE crystal is stable or not. At startup, the LSE crystal output clock signal is not released
until this bit is set by hardware. An interrupt can be generated if enabled in the _RCC clock_
_interrupt register (RCC_CIR)_ .


**External source (LSE bypass)**


In this mode, an external clock source must be provided. It must have a frequency up to
1 MHz. You select this mode by setting the LSEBYP and LSEON bits in the _RCC Backup_
_domain control register (RCC_BDCR)_ . The external clock signal (square, sinus or triangle)
with ~50% duty cycle has to drive the OSC32_IN pin while the OSC32_OUT pin should be
left HI-Z. See _Figure 17_ .


**6.2.5** **LSI clock**


The LSI RC acts as an low-power clock source that can be kept running in Stop and
Standby mode for the independent watchdog (IWDG) and Auto-wakeup unit (AWU). The
clock frequency is around 32 kHz. For more details, refer to the electrical characteristics
section of the datasheets.


The LSI RC can be switched on and off using the LSION bit in the _RCC clock control &_
_status register (RCC_CSR)_ .


The LSIRDY flag in the _RCC clock control & status register (RCC_CSR)_ indicates if the lowspeed internal oscillator is stable or not. At startup, the clock is not released until this bit is
set by hardware. An interrupt can be generated if enabled in the _RCC clock interrupt register_
_(RCC_CIR)_ .


**6.2.6** **System clock (SYSCLK) selection**


After a system reset, the HSI oscillator is selected as the system clock. When a clock source
is used directly or through PLL as the system clock, it is not possible to stop it.


A switch from one clock source to another occurs only if the target clock source is ready
(clock stable after startup delay or PLL locked). If a clock source that is not yet ready is
selected, the switch occurs when the clock source is ready. Status bits in the _RCC clock_
_control register (RCC_CR)_ indicate which clock(s) is (are) ready and which clock is currently
used as the system clock.


158/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


**6.2.7** **Clock security system (CSS)**


The clock security system can be activated by software. In this case, the clock detector is
enabled after the HSE oscillator startup delay, and disabled when this oscillator is stopped.


If a failure is detected on the HSE clock, this oscillator is automatically disabled, a clock
failure event is sent to the break inputs of advanced-control timers TIM1 and TIM8, and an
interrupt is generated to inform the software about the failure (clock security system
interrupt CSSI), allowing the MCU to perform rescue operations. The CSSI is linked to the
Cortex [®] -M4 with FPU NMI (non-maskable interrupt) exception vector.


_Note:_ _When the CSS is enabled, if the HSE clock happens to fail, the CSS generates an interrupt,_
_which causes the automatic generation of an NMI. The NMI is executed indefinitely unless_
_the CSS interrupt pending bit is cleared. As a consequence, the application has to clear the_
_CSS interrupt in the NMI ISR by setting the CSSC bit in the Clock interrupt register_
_(RCC_CIR)._


If the HSE oscillator is used directly or indirectly as the system clock (indirectly meaning that
it is directly used as PLL input clock, and that PLL clock is the system clock) and a failure is
detected, then the system clock switches to the HSI oscillator and the HSE oscillator is
disabled.


If the HSE oscillator clock was the clock source of PLL used as the system clock when the
failure occurred, PLL is also disabled. In this case, if the PLLI2S was enabled, it is also
disabled when the HSE fails.


**6.2.8** **RTC/AWU clock**


Once the RTCCLK clock source has been selected, the only possible way of modifying the
selection is to reset the power domain.


The RTCCLK clock source can be either the HSE 1 MHz (HSE divided by a programmable
prescaler), the LSE or the LSI clock. This is selected by programming the RTCSEL[1:0] bits
in the _RCC Backup domain control register (RCC_BDCR)_ and the RTCPRE[4:0] bits in _RCC_
_clock configuration register (RCC_CFGR)_ . This selection cannot be modified without
resetting the Backup domain.


If the LSE is selected as the RTC clock, the RTC operates normally if the backup or the
system supply disappears. If the LSI is selected as the AWU clock, the AWU state is not
guaranteed if the system supply disappears. If the HSE oscillator divided by a value
between 2 and 31 is used as the RTC clock, the RTC state is not guaranteed if the backup
or the system supply disappears.


The LSE clock is in the Backup domain, whereas the HSE and LSI clocks are not. As a

consequence:


      - If LSE is selected as the RTC clock:


– The RTC continues to work even if the V DD supply is switched off, provided the
V BAT supply is maintained.


      - If LSI is selected as the Auto-wakeup unit (AWU) clock:


–
The AWU state is not guaranteed if the V DD supply is powered off. Refer to
_Section 6.2.5: LSI clock on page 158_ for more details on LSI calibration.


      - If the HSE clock is used as the RTC clock:


–
The RTC state is not guaranteed if the V DD supply is powered off or if the internal
voltage regulator is powered off (removing power from the 1.2 V domain).


RM0090 Rev 21 159/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


_Note:_ _To read the RTC calendar register when the APB1 clock frequency is less than seven times_
_the RTC clock frequency (f_ _APB1_ _< 7xf_ _RTCLCK_ _), the software must read the calendar time and_
_date registers twice. The data are correct if the second read access to RTC_TR gives the_
_same result than the first one. Otherwise a third read access must be performed._


**6.2.9** **Watchdog clock**


If the independent watchdog (IWDG) is started by either hardware option or software
access, the LSI oscillator is forced ON and cannot be disabled. After the LSI oscillator
temporization, the clock is provided to the IWDG.


**6.2.10** **Clock-out capability**


Two microcontroller clock output (MCO) pins are available:


      - MCO1


You can output four different clock sources onto the MCO1 pin (PA8) using the
configurable prescaler (from 1 to 5):


– HSI clock


– LSE clock


– HSE clock


– PLL clock


The desired clock source is selected using the MCO1PRE[2:0] and MCO1[1:0] bits in
the _RCC clock configuration register (RCC_CFGR)_ .


      - MCO2


You can output four different clock sources onto the MCO2 pin (PC9) using the
configurable prescaler (from 1 to 5):


– HSE clock


– PLL clock


–
System clock (SYSCLK)


– PLLI2S clock


The desired clock source is selected using the MCO2PRE[2:0] and MCO2 bits in the
_RCC clock configuration register (RCC_CFGR)_ .


For the different MCO pins, the corresponding GPIO port has to be programmed in alternate
function mode.


The selected clock to output onto MCO must not exceed 100 MHz (the maximum I/O
speed).


**6.2.11** **Internal/external clock measurement using TIM5/TIM11**


It is possible to indirectly measure the frequencies of all on-board clock source generators
by means of the input capture of TIM5 channel4 and TIM11 channel1 as shown in _Figure 18_
and _Figure 19_ .


**Internal/external clock measurement using TIM5 channel4**


TIM5 has an input multiplexer which allows choosing whether the input capture is triggered
by the I/O or by an internal clock. This selection is performed through the TI4_RMP [1:0] bits
in the TIM5_OR register.


160/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


The primary purpose of having the LSE connected to the channel4 input capture is to be
able to precisely measure the HSI (this requires to have the HSI used as the system clock
source). The number of HSI clock counts between consecutive edges of the LSE signal
provides a measurement of the internal clock period. Taking advantage of the high precision
of LSE crystals (typically a few tens of ppm) we can determine the internal clock frequency
with the same resolution, and trim the source to compensate for manufacturing-process
and/or temperature- and voltage-related frequency deviations.


The HSI oscillator has dedicated, user-accessible calibration bits for this purpose.


The basic concept consists in providing a relative measurement (e.g. HSI/LSE ratio): the
precision is therefore tightly linked to the ratio between the two clock sources. The greater
the ratio, the better the measurement.


It is also possible to measure the LSI frequency: this is useful for applications that do not
have a crystal. The ultralow-power LSI oscillator has a large manufacturing process
deviation: by measuring it versus the HSI clock source, it is possible to determine its
frequency with the precision of the HSI. The measured value can be used to have more
accurate RTC time base timeouts (when LSI is used as the RTC clock source) and/or an
IWDG timeout with an acceptable accuracy.


Use the following procedure to measure the LSI frequency:


1. Enable the TIM5 timer and configure channel4 in Input capture mode.


2. This bit is set the TI4_RMP bits in the TIM5_OR register to 0x01 to connect the LSI
clock internally to TIM5 channel4 input capture for calibration purposes.


3. Measure the LSI clock frequency using the TIM5 capture/compare 4 event or interrupt.


4. Use the measured LSI frequency to update the prescaler of the RTC depending on the
desired time base and/or to compute the IWDG timeout.


**Figure 18. Frequency measurement with TIM5 in Input capture mode**











**Internal/external clock measurement using TIM11 channel1**


TIM11 has an input multiplexer which allows choosing whether the input capture is triggered
by the I/O or by an internal clock. This selection is performed through TI1_RMP [1:0] bits in
the TIM11_OR register. The HSE_RTC clock (HSE divided by a programmable prescaler) is
connected to channel 1 input capture to have a rough indication of the external crystal
frequency. This requires that the HSI is the system clock source. This can be useful for
instance to ensure compliance with the IEC 60730/IEC 61335 standards which require to be
able to determine harmonic or subharmonic frequencies (–50/+100% deviations).


RM0090 Rev 21 161/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


**Figure 19. Frequency measurement with TIM11 in Input capture mode**





162/1757 RM0090 Rev 21






**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**

## **6.3 RCC registers**


Refer to _Section 1.1: List of abbreviations for registers_ for a list of abbreviations used in
register descriptions.


**6.3.1** **RCC clock control register (RCC_CR)**


Address offset: 0x00


Reset value: 0x0000 XX83 where X is undefined.


Access: no wait state, word, half-word and byte access










|31 30|29|28|27|26|25|24|23 22 21 20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|PLLSAI<br>RDY|PLLSAI<br>ON|PLLI2S<br>RDY|PLLI2S<br>ON|PLLRD<br>Y|PLLON|Reserved|CSS<br>ON|HSE<br>BYP|HSE<br>RDY|HSE<br>ON|
|Reserved|r|rw|r|rw|r|rw|rw|rw|rw|r|rw|







|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3|Col10|Col11|Col12|Col13|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSITRIM[4:0]|HSITRIM[4:0]|HSITRIM[4:0]|HSITRIM[4:0]|HSITRIM[4:0]|Res.|HSI<br>RDY|HSION|
|r|r|r|r|r|r|r|r|rw|rw|rw|rw|rw|rw|r|rw|


Bits 31:28 Reserved, must be kept at reset value.


Bit 29 **PLLSAIRDY** : PLLSAI clock ready flag

Set by hardware to indicate that the PLLSAI is locked.

0: PLLSAI unlocked

1: PLLSAI locked


Bit 28 **PLLSAION** : PLLSAI enable

Set and cleared by software to enable PLLSAI.
Cleared by hardware when entering Stop or Standby mode.

0: PLLSAI OFF

1: PLLSAI ON


Bit 27 **PLLI2SRDY** : PLLI2S clock ready flag

Set by hardware to indicate that the PLLI2S is locked.

0: PLLI2S unlocked

1: PLLI2S locked


Bit 26 **PLLI2SON** : PLLI2S enable

Set and cleared by software to enable PLLI2S.
Cleared by hardware when entering Stop or Standby mode.

0: PLLI2S OFF

1: PLLI2S ON


Bit 25 **PLLRDY** : Main PLL (PLL) clock ready flag

Set by hardware to indicate that PLL is locked.

0: PLL unlocked

1: PLL locked


Bit 24 **PLLON** : Main PLL (PLL) enable

Set and cleared by software to enable PLL.
Cleared by hardware when entering Stop or Standby mode. This bit cannot be reset if PLL
clock is used as the system clock.

0: PLL OFF

1: PLL ON


RM0090 Rev 21 163/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bits 23:20 Reserved, must be kept at reset value.


Bit 19 **CSSON** : Clock security system enable

Set and cleared by software to enable the clock security system. When CSSON is set, the
clock detector is enabled by hardware when the HSE oscillator is ready, and disabled by
hardware if an oscillator failure is detected.

0: Clock security system OFF (Clock detector OFF)
1: Clock security system ON (Clock detector ON if HSE oscillator is stable, OFF if not)


Bit 18 **HSEBYP** : HSE clock bypass

Set and cleared by software to bypass the oscillator with an external clock. The external
clock must be enabled with the HSEON bit, to be used by the device.
The HSEBYP bit can be written only if the HSE oscillator is disabled.
0: HSE oscillator not bypassed
1: HSE oscillator bypassed with an external clock


Bit 17 **HSERDY** : HSE clock ready flag

Set by hardware to indicate that the HSE oscillator is stable. After the HSEON bit is cleared,
HSERDY goes low after 6 HSE oscillator clock cycles.
0: HSE oscillator not ready
1: HSE oscillator ready


Bit 16 **HSEON** : HSE clock enable

Set and cleared by software.
Cleared by hardware to stop the HSE oscillator when entering Stop or Standby mode. This
bit cannot be reset if the HSE oscillator is used directly or indirectly as the system clock.

0: HSE oscillator OFF

1: HSE oscillator ON


Bits 15:8 **HSICAL[7:0]** : Internal high-speed clock calibration

These bits are initialized automatically at startup.


Bits 7:3 **HSITRIM[4:0]** : Internal high-speed clock trimming

These bits provide an additional user-programmable trimming value that is added to the
HSICAL[7:0] bits. It can be programmed to adjust to variations in voltage and temperature
that influence the frequency of the internal HSI RC.


Bit 2 Reserved, must be kept at reset value.


Bit 1 **HSIRDY** : Internal high-speed clock ready flag

Set by hardware to indicate that the HSI oscillator is stable. After the HSION bit is cleared,
HSIRDY goes low after 6 HSI clock cycles.
0: HSI oscillator not ready
1: HSI oscillator ready


Bit 0 **HSION** : Internal high-speed clock enable

Set and cleared by software.
Set by hardware to force the HSI oscillator ON when leaving the Stop or Standby mode or in
case of a failure of the HSE oscillator used directly or indirectly as the system clock. This bit
cannot be cleared if the HSI is used directly or indirectly as the system clock.

0: HSI oscillator OFF

1: HSI oscillator ON


164/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


**6.3.2** **RCC PLL configuration register (RCC_PLLCFGR)**


Address offset: 0x04


Reset value: 0x2400 3010


Access: no wait state, word, half-word and byte access.


This register is used to configure the PLL clock outputs according to the formulas:

      - f (VCO clock) = f (PLL clock input) × (PLLN / PLLM)

      - f = f / PLLP
(PLL general clock output) (VCO clock)

      - f = f / PLLQ
(USB OTG FS, SDIO, RNG clock output) (VCO clock)








|31 30 29 28|27|26|25|24|23|22|21 20 19 18|17|16|
|---|---|---|---|---|---|---|---|---|---|
|Reserved|PLLQ3|PLLQ2|PLLQ1|PLLQ0|Reserv<br>ed|PLLSR<br>C|Reserved|PLLP1|PLLP0|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|





|15|14 13 12 11 10 9 8 7 6|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserv<br>ed|PLLN|PLLN|PLLN|PLLN|PLLN|PLLN|PLLN|PLLN|PLLN|PLLM5|PLLM4|PLLM3|PLLM2|PLLM1|PLLM0|
|Reserv<br>ed|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:28 Reserved, must be kept at reset value.


Bits 27:24 **PLLQ:** Main PLL (PLL) division factor for USB OTG FS, SDIO and random number generator
clocks

Set and cleared by software to control the frequency of USB OTG FS clock, the random
number generator clock and the SDIO clock. These bits should be written only if PLL is
disabled.


**Caution:** The USB OTG FS requires a 48 MHz clock to work correctly. The SDIO and the
random number generator need a frequency lower than or equal to 48 MHz to work
correctly.
USB OTG FS clock frequency = VCO frequency / PLLQ with 2 ≤ PLLQ ≤ 15
0000: PLLQ = 0, wrong configuration
0001: PLLQ = 1, wrong configuration

0010: PLLQ = 2

0011: PLLQ = 3

0100: PLLQ = 4

...

1111: PLLQ = 15


Bit 23 Reserved, must be kept at reset value.


Bit 22 **PLLSRC:** Main PLL(PLL) and audio PLL (PLLI2S) entry clock source

Set and cleared by software to select PLL and PLLI2S clock source. This bit can be written
only when PLL and PLLI2S are disabled.
0: HSI clock selected as PLL and PLLI2S clock entry
1: HSE oscillator clock selected as PLL and PLLI2S clock entry


Bits 21:18 Reserved, must be kept at reset value.


RM0090 Rev 21 165/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bits 17:16 **PLLP:** Main PLL (PLL) division factor for main system clock

Set and cleared by software to control the frequency of the general PLL output clock. These
bits can be written only if PLL is disabled.


**Caution:** The software has to set these bits correctly not to exceed 180 MHz on this domain.
PLL output clock frequency = VCO frequency / PLLP with PLLP = 2, 4, 6, or 8

00: PLLP = 2

01: PLLP = 4

10: PLLP = 6

11: PLLP = 8


Bits 14:6 **PLLN:** Main PLL (PLL) multiplication factor for VCO

Set and cleared by software to control the multiplication factor of the VCO. These bits can
be written only when PLL is disabled. Only half-word and word accesses are allowed to
write these bits.


**Caution:** The software has to set these bits correctly to ensure that the VCO output
frequency is between 100 and 432 MHz.
VCO output frequency = VCO input frequency × PLLN with 50 ≤ PLLN ≤ 432
000000000: PLLN = 0, wrong configuration
000000001: PLLN = 1, wrong configuration

...

000110010: PLLN = 50

...

001100011: PLLN = 99

001100100: PLLN = 100

...

110110000: PLLN = 432

110110001: PLLN = 433, wrong configuration

...

111111111: PLLN = 511, wrong configuration

_Note: Multiplication factors ranging from 50 and 99 are possible for VCO input frequency_
_higher than 1 MHz. However care must be taken that the minimum VCO output_
_frequency respects the value specified above._


Bits 5:0 **PLLM:** Division factor for the main PLL (PLL) and audio PLL (PLLI2S) input clock

Set and cleared by software to divide the PLL and PLLI2S input clock before the VCO.
These bits can be written only when the PLL and PLLI2S are disabled.


**Caution:** The software has to set these bits correctly to ensure that the VCO input frequency
ranges from 1 to 2 MHz. It is recommended to select a frequency of 2 MHz to limit
PLL jitter.
VCO input frequency = PLL input clock frequency / PLLM with 2 ≤ PLLM ≤ 63
000000: PLLM = 0, wrong configuration
000001: PLLM = 1, wrong configuration
000010: PLLM = 2

000011: PLLM = 3

000100: PLLM = 4

...

111110: PLLM = 62

111111: PLLM = 63


166/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


**6.3.3** **RCC clock configuration register (RCC_CFGR)**


Address offset: 0x08


Reset value: 0x0000 0000


Access: 0 ≤ wait state ≤ 2, word, half-word and byte access


1 or 2 wait states inserted only if the access occurs during a clock source switch.

|31 30|Col2|29 28 27|Col4|Col5|26 25 24|Col7|Col8|23|22 21|Col11|20 19 18 17 16|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MCO2|MCO2|MCO2 PRE[2:0]|MCO2 PRE[2:0]|MCO2 PRE[2:0]|MCO1 PRE[2:0]|MCO1 PRE[2:0]|MCO1 PRE[2:0]|I2SSC<br>R|MCO1|MCO1|RTCPRE[4:0]|RTCPRE[4:0]|RTCPRE[4:0]|RTCPRE[4:0]|RTCPRE[4:0]|
|rw||rw|rw|rw|rw|rw|rw|rw|rw||rw|rw|rw|rw|rw|


|15 14 13|Col2|Col3|12 11 10|Col5|Col6|9 8|7 6 5 4|Col9|Col10|Col11|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PPRE2[2:0]|PPRE2[2:0]|PPRE2[2:0]|PPRE1[2:0]|PPRE1[2:0]|PPRE1[2:0]|Reserved|HPRE[3:0]|HPRE[3:0]|HPRE[3:0]|HPRE[3:0]|SWS1|SWS0|SW1|SW0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|r|r|rw|rw|



Bits 31:30 **MCO2[1:0]:** Microcontroller clock output 2

Set and cleared by software. Clock source selection may generate glitches on MCO2. It is
highly recommended to configure these bits only after reset before enabling the external
oscillators and the PLLs.

00: System clock (SYSCLK) selected

01: PLLI2S clock selected

10: HSE oscillator clock selected

11: PLL clock selected


Bits 27:29 **MCO2PRE:** MCO2 prescaler

Set and cleared by software to configure the prescaler of the MCO2. Modification of this
prescaler may generate glitches on MCO2. It is highly recommended to change this
prescaler only after reset before enabling the external oscillators and the PLLs.

0xx: no division

100: division by 2
101: division by 3
110: division by 4
111: division by 5


Bits 24:26 **MCO1PRE:** MCO1 prescaler

Set and cleared by software to configure the prescaler of the MCO1. Modification of this
prescaler may generate glitches on MCO1. It is highly recommended to change this
prescaler only after reset before enabling the external oscillators and the PLL.

0xx: no division

100: division by 2
101: division by 3
110: division by 4
111: division by 5


Bit 23 **I2SSRC** : I2S clock selection

Set and cleared by software. This bit allows to select the I2S clock source between the
PLLI2S clock and the external clock. It is highly recommended to change this bit only after
reset and before enabling the I2S module.

0: PLLI2S clock used as I2S clock source

1: External clock mapped on the I2S_CKIN pin used as I2S clock source


RM0090 Rev 21 167/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bits 22:21 **MCO1:** Microcontroller clock output 1

Set and cleared by software. Clock source selection may generate glitches on MCO1. It is
highly recommended to configure these bits only after reset before enabling the external
oscillators and PLL.

00: HSI clock selected

01: LSE oscillator selected

10: HSE oscillator clock selected

11: PLL clock selected


Bits 20:16 **RTCPRE:** HSE division factor for RTC clock

Set and cleared by software to divide the HSE clock input clock to generate a 1 MHz clock
for RTC.


**Caution:** The software has to set these bits correctly to ensure that the clock supplied to the
RTC is 1 MHz. These bits must be configured if needed before selecting the RTC
clock source.

00000: no clock

00001: no clock

00010: HSE/2

00011: HSE/3

00100: HSE/4

...

11110: HSE/30

11111: HSE/31


Bits 15:13 **PPRE2:** APB high-speed prescaler (APB2)

Set and cleared by software to control APB high-speed clock division factor.


**Caution:** The software has to set these bits correctly not to exceed 90 MHz on this domain.
The clocks are divided with the new prescaler factor from 1 to 16 AHB cycles after
PPRE2 write.

0xx: AHB clock not divided

100: AHB clock divided by 2
101: AHB clock divided by 4
110: AHB clock divided by 8
111: AHB clock divided by 16


Bits 12:10 **PPRE1:** APB Low speed prescaler (APB1)

Set and cleared by software to control APB low-speed clock division factor.


**Caution:** The software has to set these bits correctly not to exceed 45 MHz on this domain.
The clocks are divided with the new prescaler factor from 1 to 16 AHB cycles after
PPRE1 write.

0xx: AHB clock not divided

100: AHB clock divided by 2
101: AHB clock divided by 4
110: AHB clock divided by 8
111: AHB clock divided by 16


Bits 9:8 Reserved, must be kept at reset value.


168/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bits 7:4 **HPRE:** AHB prescaler

Set and cleared by software to control AHB clock division factor.


**Caution:** The clocks are divided with the new prescaler factor from 1 to 16 AHB cycles after
HPRE write.


**Caution:** The AHB clock frequency must be at least 25 MHz when the Ethernet is used.
0xxx: system clock not divided
1000: system clock divided by 2
1001: system clock divided by 4
1010: system clock divided by 8
1011: system clock divided by 16
1100: system clock divided by 64
1101: system clock divided by 128
1110: system clock divided by 256
1111: system clock divided by 512


Bits 3:2 **SWS:** System clock switch status

Set and cleared by hardware to indicate which clock source is used as the system clock.
00: HSI oscillator used as the system clock
01: HSE oscillator used as the system clock
10: PLL used as the system clock
11: not applicable


Bits 1:0 **SW:** System clock switch

Set and cleared by software to select the system clock source.
Set by hardware to force the HSI selection when leaving the Stop or Standby mode or in
case of failure of the HSE oscillator used directly or indirectly as the system clock.
00: HSI oscillator selected as system clock
01: HSE oscillator selected as system clock
10: PLL selected as system clock
11: not allowed


**6.3.4** **RCC clock interrupt register (RCC_CIR)**


Address offset: 0x0C


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access


|31 30 29 28 27 26 25 24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|
|Reserved|CSSC|PLLSAI<br>RDYC|PLLI2S<br>RDYC|PLL<br>RDYC|HSE<br>RDYC|HSI<br>RDYC|LSE<br>RDYC|LSI<br>RDYC|
|Reserved|w|w|w|w|w|w|w|w|





|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserv<br>ed|PLLSAI<br>RDYIE|PLLI2S<br>RDYIE|PLL<br>RDYIE|HSE<br>RDYIE|HSI<br>RDYIE|LSE<br>RDYIE|LSI<br>RDYIE|CSSF|PLLSAI<br>RDYF|PLLI2S<br>RDYF|PLL<br>RDYF|HSE<br>RDYF|HSI<br>RDYF|LSE<br>RDYF|LSI<br>RDYF|
|Reserv<br>ed|rw|rw|rw|rw|rw|rw|rw|r|r|r|r|r|r|r|r|


RM0090 Rev 21 169/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bits 31:24 Reserved, must be kept at reset value.


Bit 23 **CSSC:** Clock security system interrupt clear

This bit is set by software to clear the CSSF flag.

0: No effect

1: Clear CSSF flag


Bit 22 **PLLSAIRDYC** : PLLSAI Ready Interrupt Clear

This bit is set by software to clear PLLSAIRDYF flag. It is reset by hardware when the
PLLSAIRDYF is cleared.

0: PLLSAIRDYF not cleared

1: PLLSAIRDYF cleared


Bit 21 **PLLI2SRDYC:** PLLI2S ready interrupt clear

This bit is set by software to clear the PLLI2SRDYF flag.

0: No effect

1: PLLI2SRDYF cleared


Bit 20 **PLLRDYC:** Main PLL(PLL) ready interrupt clear

This bit is set by software to clear the PLLRDYF flag.

0: No effect

1: PLLRDYF cleared


Bit 19 **HSERDYC:** HSE ready interrupt clear

This bit is set by software to clear the HSERDYF flag.

0: No effect

1: HSERDYF cleared


Bit 18 **HSIRDYC:** HSI ready interrupt clear

This bit is set software to clear the HSIRDYF flag.

0: No effect

1: HSIRDYF cleared


Bit 17 **LSERDYC:** LSE ready interrupt clear

This bit is set by software to clear the LSERDYF flag.

0: No effect

1: LSERDYF cleared


Bit 16 **LSIRDYC:** LSI ready interrupt clear

This bit is set by software to clear the LSIRDYF flag.

0: No effect

1: LSIRDYF cleared


Bit 15 Reserved, must be kept at reset value.


Bit 14 **PLLSAIRDYIE** : PLLSAI Ready Interrupt Enable

This bit is set and reset by software to enable/disable interrupt caused by PLLSAI lock.
0: PLLSAI lock interrupt disabled
1: PLLSAI lock interrupt enabled


Bit 13 **PLLI2SRDYIE:** PLLI2S ready interrupt enable

This bit is set and cleared by software to enable/disable interrupt caused by PLLI2S lock.
0: PLLI2S lock interrupt disabled
1: PLLI2S lock interrupt enabled


170/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bit 12 **PLLRDYIE:** Main PLL (PLL) ready interrupt enable

This bit is set and cleared by software to enable/disable interrupt caused by PLL lock.
0: PLL lock interrupt disabled
1: PLL lock interrupt enabled


Bit 11 **HSERDYIE:** HSE ready interrupt enable

This bit is set and cleared by software to enable/disable interrupt caused by the HSE
oscillator stabilization.

0: HSE ready interrupt disabled
1: HSE ready interrupt enabled


Bit 10 **HSIRDYIE:** HSI ready interrupt enable

This bit is set and cleared by software to enable/disable interrupt caused by the HSI
oscillator stabilization.

0: HSI ready interrupt disabled
1: HSI ready interrupt enabled


Bit 9 **LSERDYIE:** LSE ready interrupt enable

This bit is set and cleared by software to enable/disable interrupt caused by the LSE
oscillator stabilization.

0: LSE ready interrupt disabled
1: LSE ready interrupt enabled


Bit 8 **LSIRDYIE:** LSI ready interrupt enable

This bit is set and cleared by software to enable/disable interrupt caused by LSI oscillator
stabilization.

0: LSI ready interrupt disabled
1: LSI ready interrupt enabled


Bit 7 **CSSF:** Clock security system interrupt flag

This bit is set by hardware when a failure is detected in the HSE oscillator.
It is cleared by software by setting the CSSC bit.
0: No clock security interrupt caused by HSE clock failure
1: Clock security interrupt caused by HSE clock failure


Bit 6 **PLLSAIRDYF** : PLLSAI Ready Interrupt flag

This bit is set by hardware when the PLLSAI is locked and PLLSAIRDYIE is set.
It is cleared by software by setting the PLLSAIRDYC bit.
0: No clock ready interrupt caused by PLLSAI lock
1: Clock ready interrupt caused by PLLSAI lock


Bit 5 **PLLI2SRDYF:** PLLI2S ready interrupt flag

This bit is set by hardware when the PLLI2S is locked and PLLI2SRDYIE is set.
It is cleared by software by setting the PLLRI2SDYC bit.
0: No clock ready interrupt caused by PLLI2S lock
1: Clock ready interrupt caused by PLLI2S lock


Bit 4 **PLLRDYF:** Main PLL (PLL) ready interrupt flag

This bit is set by hardware when PLL is locked and PLLRDYIE is set.
It is cleared by software setting the PLLRDYC bit.
0: No clock ready interrupt caused by PLL lock
1: Clock ready interrupt caused by PLL lock


RM0090 Rev 21 171/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bit 3 **HSERDYF:** HSE ready interrupt flag

This bit is set by hardware when External High Speed clock becomes stable and
HSERDYIE is set.

It is cleared by software by setting the HSERDYC bit.
0: No clock ready interrupt caused by the HSE oscillator
1: Clock ready interrupt caused by the HSE oscillator


Bit 2 **HSIRDYF:** HSI ready interrupt flag

This bit is set by hardware when the Internal High Speed clock becomes stable and
HSIRDYIE is set.

It is cleared by software by setting the HSIRDYC bit.
0: No clock ready interrupt caused by the HSI oscillator
1: Clock ready interrupt caused by the HSI oscillator


Bit 1 **LSERDYF:** LSE ready interrupt flag

This bit is set by hardware when the External Low Speed clock becomes stable and
LSERDYIE is set.

It is cleared by software by setting the LSERDYC bit.
0: No clock ready interrupt caused by the LSE oscillator
1: Clock ready interrupt caused by the LSE oscillator


Bit 0 **LSIRDYF:** LSI ready interrupt flag

This bit is set by hardware when the internal low speed clock becomes stable and
LSIRDYIE is set.

It is cleared by software by setting the LSIRDYC bit.
0: No clock ready interrupt caused by the LSI oscillator
1: Clock ready interrupt caused by the LSI oscillator


**6.3.5** **RCC AHB1 peripheral reset register (RCC_AHB1RSTR)**


Address offset: 0x10


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access.












|31 30|29|28 27 26|25|24|23|22|21|20 19 18 17 16|
|---|---|---|---|---|---|---|---|---|
|Reserved|OTGH<br>S<br>RST|Reserved|ETHMAC<br>RST|Res.|DMA2D<br>RST|DMA2<br>RST|DMA1<br>RST|Reserved|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|









|15 14 13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|CRCR<br>ST|Res.|GPIOK<br>RST|GPIOJ<br>RST|GPIOI<br>RST|GPIOH<br>RST|GPIOGG<br>RST|GPIOF<br>RST|GPIOE<br>RST|GPIOD<br>RST|GPIOC<br>RST|GPIOB<br>RST|GPIOA<br>RST|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:30 Reserved, must be kept at reset value.


Bit 29 **OTGHSRST:** USB OTG HS module reset

This bit is set and cleared by software.

0: does not reset the USB OTG HS module

1: resets the USB OTG HS module


Bits 28:26 Reserved, must be kept at reset value.


172/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bit 25 **ETHMACRST:** Ethernet MAC reset

This bit is set and cleared by software.

0: does not reset Ethernet MAC

1: resets Ethernet MAC


Bit 24 Reserved, must be kept at reset value.


Bit 23 **DMA2DRST** : DMA2D reset

This bit is set and reset by software.

0: does not reset DMA2D

1: resets DMA2D


Bit 22 **DMA2RST:** DMA2 reset

This bit is set and cleared by software.

0: does not reset DMA2

1: resets DMA2


Bit 21 **DMA1RST:** DMA2 reset

This bit is set and cleared by software.

0: does not reset DMA2

1: resets DMA2


Bits 20:13 Reserved, must be kept at reset value.


Bit 12 **CRCRST:** CRC reset

This bit is set and cleared by software.

0: does not reset CRC

1: resets CRC


Bit 11 Reserved, must be kept at reset value.


Bit 10 **GPIOKRST** : IO port K reset

This bit is set and cleared by software.
0: does not reset IO port K
1: resets IO port K


Bit 9 **GPIOJRST** : IO port J reset

This bit is set and cleared by software.
0: does not reset IO port J
1: resets IO port J


Bit 8 **GPIOIRST:** IO port I reset

This bit is set and cleared by software.
0: does not reset IO port I
1: resets IO port I


Bit 7 **GPIOHRST:** IO port H reset

This bit is set and cleared by software.
0: does not reset IO port H
1: resets IO port H


Bit 6 **GPIOGRST:** IO port G reset

This bit is set and cleared by software.
0: does not reset IO port G
1: resets IO port G


RM0090 Rev 21 173/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bit 5 **GPIOFRST:** IO port F reset

This bit is set and cleared by software.
0: does not reset IO port F
1: resets IO port F


Bit 4 **GPIOERST:** IO port E reset

This bit is set and cleared by software.
0: does not reset IO port E
1: resets IO port E


Bit 3 **GPIODRST:** IO port D reset

This bit is set and cleared by software.
0: does not reset IO port D
1: resets IO port D


Bit 2 **GPIOCRST:** IO port C reset

This bit is set and cleared by software.
0: does not reset IO port C
1: resets IO port C


Bit 1 **GPIOBRST:** IO port B reset

This bit is set and cleared by software.
0: does not reset IO port B
1:resets IO port B


Bit 0 **GPIOARST:** IO port A reset

This bit is set and cleared by software.
0: does not reset IO port A
1: resets IO port A


174/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


**6.3.6** **RCC AHB2 peripheral reset register (RCC_AHB2RSTR)**


Address offset: 0x14


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved









|15 14 13 12 11 10 9 8|7|6|5|4|3 2 1|0|
|---|---|---|---|---|---|---|
|Reserved|OTGFS<br>RST|RNG<br>RST|HASH<br>RST|CRYP<br>RST|Reserved|DCMI<br>RST|
|Reserved|rw|rw|rw|rw|rw|rw|


Bits 31:8 Reserved, must be kept at reset value.


Bit 7 **OTGFSRST:** USB OTG FS module reset

Set and cleared by software.

0: does not reset the USB OTG FS module

1: resets the USB OTG FS module


Bit 6 **RNGRST:** Random number generator module reset

Set and cleared by software.
0: does not reset the random number generator module
1: resets the random number generator module


Bit 5 **HASHRST:** Hash module reset

Set and cleared by software.

0: does not reset the HASH module

1: resets the HASH module


Bit 4 **CRYPRST:** Cryptographic module reset

Set and cleared by software.
0: does not reset the cryptographic module
1: resets the cryptographic module


Bits 3:1 Reserved, must be kept at reset value.


Bit 0 **DCMIRST:** Camera interface reset

Set and cleared by software.

0: does not reset the Camera interface

1: resets the Camera interface


RM0090 Rev 21 175/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


**6.3.7** **RCC AHB3 peripheral reset register (RCC_AHB3RSTR)**


Address offset: 0x18


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access.


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1|0|
|---|---|
|Reserved|FMCRST|
|Reserved|rw|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **FMCRST:** Flexible memory controller module reset

Set and cleared by software.

0: does not reset the FMC module

1: resets the FMC module


**6.3.8** **RCC APB1 peripheral reset register (RCC_APB1RSTR)**


Address offset: 0x20


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access.








|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UART8R<br>ST|UART7R<br>ST|DACRST|PWR<br>RST|Reser-<br>ved|CAN2<br>RST|CAN1<br>RST|Reser-<br>ved|I2C3<br>RST|I2C2<br>RST|I2C1<br>RST|UART5<br>RST|UART4<br>RST|UART3<br>RST|UART2<br>RST|Reser-<br>ved|
|rw|rw|rw|rw|rw||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|











|15|14|13 12|11|10 9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SPI3<br>RST|SPI2<br>RST|Reserved|WWDG<br>RST|Reserved|TIM14<br>RST|TIM13<br>RST|TIM12<br>RST|TIM7<br>RST|TIM6<br>RST|TIM5<br>RST|TIM4<br>RST|TIM3<br>RST|TIM2<br>RST|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


176/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bit 31 **UART8RST** : UART8 reset

Set and cleared by software.

0: does not reset UART8

1: resets UART8


Bit 30 **UART7RST** : UART7 reset

Set and cleared by software.

0: does not reset UART7

1: resets UART7


Bit 29 **DACRST:** DAC reset

Set and cleared by software.

0: does not reset the DAC interface

1: resets the DAC interface


Bit 28 **PWRRST:** Power interface reset

Set and cleared by software.
0: does not reset the power interface
1: resets the power interface


Bit 27 Reserved, must be kept at reset value.


Bit 26 **CAN2RST:** CAN2 reset

Set and cleared by software.

0: does not reset CAN2

1: resets CAN2


Bit 25 **CAN1RST:** CAN1 reset

Set and cleared by software.

0: does not reset CAN1

1: resets CAN1


Bit 24 Reserved, must be kept at reset value.


Bit 23 **I2C3RST:** I2C3 reset

Set and cleared by software.

0: does not reset I2C3

1: resets I2C3


Bit 22 **I2C2RST:** I2C2 reset

Set and cleared by software.

0: does not reset I2C2

1: resets I2C2


Bit 21 **I2C1RST:** I2C1 reset

Set and cleared by software.

0: does not reset I2C1

1: resets I2C1


Bit 20 **UART5RST:** UART5 reset

Set and cleared by software.

0: does not reset UART5

1: resets UART5


Bit 19 **UART4RST:** USART4 reset

Set and cleared by software.

0: does not reset UART4

1: resets UART4


RM0090 Rev 21 177/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bit 18 **USART3RST:** USART3 reset

Set and cleared by software.

0: does not reset USART3

1: resets USART3


Bit 17 **USART2RST:** USART2 reset

Set and cleared by software.

0: does not reset USART2

1: resets USART2


Bit 16 Reserved, must be kept at reset value.


Bit 15 **SPI3RST:** SPI3 reset

Set and cleared by software.

0: does not reset SPI3

1: resets SPI3


Bit 14 **SPI2RST:** SPI2 reset

Set and cleared by software.

0: does not reset SPI2

1: resets SPI2


Bits 13:12 Reserved, must be kept at reset value.


Bit 11 **WWDGRST:** Window watchdog reset

Set and cleared by software.
0: does not reset the window watchdog
1: resets the window watchdog


Bits 10:9 Reserved, must be kept at reset value.


Bit 8 **TIM14RST:** TIM14 reset

Set and cleared by software.

0: does not reset TIM14

1: resets TIM14


Bit 7 **TIM13RST:** TIM13 reset

Set and cleared by software.

0: does not reset TIM13

1: resets TIM13


Bit 6 **TIM12RST:** TIM12 reset

Set and cleared by software.

0: does not reset TIM12

1: resets TIM12


Bit 5 **TIM7RST:** TIM7 reset

Set and cleared by software.

0: does not reset TIM7

1: resets TIM7


Bit 4 **TIM6RST:** TIM6 reset

Set and cleared by software.

0: does not reset TIM6

1: resets TIM6


178/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bit 3 **TIM5RST:** TIM5 reset

Set and cleared by software.

0: does not reset TIM5

1: resets TIM5


Bit 2 **TIM4RST:** TIM4 reset

Set and cleared by software.

0: does not reset TIM4

1: resets TIM4


Bit 1 **TIM3RST:** TIM3 reset

Set and cleared by software.

0: does not reset TIM3

1: resets TIM3


Bit 0 **TIM2RST:** TIM2 reset

Set and cleared by software.

0: does not reset TIM2

1: resets TIM2


RM0090 Rev 21 179/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


**6.3.9** **RCC APB2 peripheral reset register (RCC_APB2RSTR)**


Address offset: 0x24


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access.












|31 30 29 28 27|26|25 24 23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|
|Reserved|LTD<br>CRST|Reserved|SAI1<br>RST|SPI6<br>RST|SPI5<br>RST|Res.|TIM11<br>RST|TIM10<br>RST|TIM9<br>RST|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|















|15|14|13|12|11|10 9|8|7 6|5|4|3 2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reser-<br>ved|SYSCF<br>G RST|SPI4<br>RST|SPI1<br>RST|SDIO<br>RST|Reserved|ADC<br>RST|Reserved|USART<br>6<br>RST|USART<br>1<br>RST|Reserved|TIM8<br>RST|TIM1<br>RST|
|Reser-<br>ved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:27 Reserved, must be kept at reset value.


Bit 26 **LTDCRST** : LTDC reset

This bit is set and reset by software.

0: does not reset LCD-TFT

1: resets LCD-TFT


Bits 27:23 Reserved, must be kept at reset value.


Bit 22 **SAI1RST** : SAI1 reset

This bit is set and reset by software.

0: does not reset SAI1

1: resets SAI1


Bit 21 **SPI6RST** : SPI6 reset

This bit is set and cleared by software.

0: does not reset SPI6

1: resets SPI6


Bit 20 **SPI5RST** : SPI5 reset

This bit is set and cleared by software.

0: does not reset SPI5

1: resets SPI5


Bit 19 Reserved, must be kept at reset value.


Bit 18 **TIM11RST:** TIM11 reset

This bit is set and cleared by software.

0: does not reset TIM11

1: resets TIM14


Bit 17 **TIM10RST:** TIM10 reset

This bit is set and cleared by software.

0: does not reset TIM10

1: resets TIM10


Bit 16 **TIM9RST:** TIM9 reset

This bit is set and cleared by software.

0: does not reset TIM9

1: resets TIM9


180/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bit 15 Reserved, must be kept at reset value.


Bit 14 **SYSCFGRST:** System configuration controller reset

This bit is set and cleared by software.
0: does not reset the System configuration controller
1: resets the System configuration controller


Bit 13 **SPI4RST** : SPI4 reset

This bit is set and cleared by software.

0: does not reset SPI4

1: resets SPI4


Bit 12 **SPI1RST:** SPI1 reset

This bit is set and cleared by software.

0: does not reset SPI1

1: resets SPI1


Bit 11 **SDIORST:** SDIO reset

This bit is set and cleared by software.

0: does not reset the SDIO module

1: resets the SDIO module


Bits 10:9 Reserved, must be kept at reset value.


Bit 8 **ADCRST:** ADC interface reset (common to all ADCs)

This bit is set and cleared by software.

0: does not reset the ADC interface

1: resets the ADC interface


Bits 7:6 Reserved, must be kept at reset value.


Bit 5 **USART6RST:** USART6 reset

This bit is set and cleared by software.

0: does not reset USART6

1: resets USART6


Bit 4 **USART1RST:** USART1 reset

This bit is set and cleared by software.

0: does not reset USART1

1: resets USART1


Bits 3:2 Reserved, must be kept at reset value.


Bit 1 **TIM8RST:** TIM8 reset

This bit is set and cleared by software.

0: does not reset TIM8

1: resets TIM8


Bit 0 **TIM1RST:** TIM1 reset

This bit is set and cleared by software.

0: does not reset TIM1

1: resets TIM1


RM0090 Rev 21 181/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


**6.3.10** **RCC AHB1 peripheral clock register (RCC_AHB1ENR)**


Address offset: 0x30


Reset value: 0x0010 0000


Access: no wait state, word, half-word and byte access.


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16




















|Reser-<br>ved|OTGH<br>S<br>ULPIE<br>N|OTGH<br>SEN|ETHM<br>ACPTP<br>EN|ETHM<br>ACRXE<br>N|ETHM<br>ACTXE<br>N|ETHMA<br>CEN|Res.|DMA2D<br>EN|DMA2E<br>N|DMA1E<br>N|CCMDAT<br>ARAMEN|Res.|BKPSR<br>AMEN|Reserved|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reser-<br>ved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|||rw|rw|









|15 14 13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|CRCE<br>N|Res.|GPIOK<br>EN|GPIOJ<br>EN|GPIOIE<br>N|GPIOH<br>EN|GPIOG<br>EN|GPIOFE<br>N|GPIOEEN|GPIOD<br>EN|GPIOC<br>EN|GPIO<br>BEN|GPIO<br>AEN|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bit 31 Reserved, must be kept at reset value.


Bit 30 **OTGHSULPIEN:** USB OTG HSULPI clock enable

This bit is set and cleared by software. It must be cleared when the OTG_HS is used in FS
mode.

0: USB OTG HS ULPI clock disabled

1: USB OTG HS ULPI clock enabled


Bit 29 **OTGHSEN:** USB OTG HS clock enable

This bit is set and cleared by software.

0: USB OTG HS clock disabled

1: USB OTG HS clock enabled


Bit 28 **ETHMACPTPEN:** Ethernet PTP clock enable

This bit is set and cleared by software.

0: Ethernet PTP clock disabled

1: Ethernet PTP clock enabled


Bit 27 **ETHMACRXEN:** Ethernet Reception clock enable

This bit is set and cleared by software.
0: Ethernet Reception clock disabled
1: Ethernet Reception clock enabled


Bit 26 **ETHMACTXEN:** Ethernet Transmission clock enable

This bit is set and cleared by software.

0: Ethernet Transmission clock disabled

1: Ethernet Transmission clock enabled


Bit 25 **ETHMACEN:** Ethernet MAC clock enable

This bit is set and cleared by software.

0: Ethernet MAC clock disabled

1: Ethernet MAC clock enabled


Bit 24 Reserved, must be kept at reset value.


Bit 23 **DMA2DEN:** DMA2D clock enable

This bit is set and cleared by software.

0: DMA2D clock disabled

1: DMA2D clock enabled


182/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bit 22 **DMA2EN:** DMA2 clock enable

This bit is set and cleared by software.

0: DMA2 clock disabled

1: DMA2 clock enabled


Bit 21 **DMA1EN:** DMA1 clock enable

This bit is set and cleared by software.

0: DMA1 clock disabled

1: DMA1 clock enabled


Bit 20 **CCMDATARAMEN** : CCM data RAM clock enable

This bit is set and cleared by software.

0: CCM data RAM clock disabled

1: CCM data RAM clock enabled


Bit 19 Reserved, must be kept at reset value.


Bit 18 **BKPSRAMEN:** Backup SRAM interface clock enable

This bit is set and cleared by software.
0: Backup SRAM interface clock disabled
1: Backup SRAM interface clock enabled


Bits 17:13 Reserved, must be kept at reset value.


Bit 12 **CRCEN:** CRC clock enable

This bit is set and cleared by software.

0: CRC clock disabled

1: CRC clock enabled


Bit 11 Reserved, must be kept at reset value.


Bit 10 **GPIOKEN:** IO port K clock enable

This bit is set and cleared by software.
0: IO port K clock disabled
1: IO port K clock enabled


Bit 9 **GPIOJEN:** IO port J clock enable

This bit is set and cleared by software.
0: IO port J clock disabled
1: IO port J clock enabled


Bit 8 **GPIOIEN:** IO port I clock enable

This bit is set and cleared by software.
0: IO port I clock disabled
1: IO port I clock enabled


Bit 7 **GPIOHEN:** IO port H clock enable

This bit is set and cleared by software.
0: IO port H clock disabled
1: IO port H clock enabled


Bit 6 **GPIOGEN:** IO port G clock enable

This bit is set and cleared by software.
0: IO port G clock disabled
1: IO port G clock enabled


RM0090 Rev 21 183/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bit 5 **GPIOFEN:** IO port F clock enable

This bit is set and cleared by software.
0: IO port F clock disabled
1: IO port F clock enabled


Bit 4 **GPIOEEN:** IO port E clock enable

This bit is set and cleared by software.
0: IO port E clock disabled
1: IO port E clock enabled


Bit 3 **GPIODEN:** IO port D clock enable

This bit is set and cleared by software.

0: IO port D clock disabled
1: IO port D clock enabled


Bit 2 **GPIOCEN:** IO port C clock enable

This bit is set and cleared by software.
0: IO port C clock disabled
1: IO port C clock enabled


Bit 1 **GPIOBEN:** IO port B clock enable

This bit is set and cleared by software.
0: IO port B clock disabled
1: IO port B clock enabled


Bit 0 **GPIOAEN:** IO port A clock enable

This bit is set and cleared by software.
0: IO port A clock disabled
1: IO port A clock enabled


**6.3.11** **RCC AHB2 peripheral clock enable register (RCC_AHB2ENR)**


Address offset: 0x34


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access.


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved









|15 14 13 12 11 10 9 8|7|6|5|4|3 2 1|0|
|---|---|---|---|---|---|---|
|Reserved|OTGFS<br>EN|RNG<br>EN|HASH<br>EN|CRYP<br>EN|Reserved|DCMI<br>EN|
|Reserved|rw|rw|rw|rw|rw|rw|


Bits 31:8 Reserved, must be kept at reset value.


Bit 7 **OTGFSEN:** USB OTG FS clock enable

This bit is set and cleared by software.

0: USB OTG FS clock disabled

1: USB OTG FS clock enabled


Bit 6 **RNGEN:** Random number generator clock enable

This bit is set and cleared by software.
0: Random number generator clock disabled
1: Random number generator clock enabled


184/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bit 5 **HASHEN:** Hash modules clock enable

This bit is set and cleared by software.

0: Hash modules clock disabled

1: Hash modules clock enabled


Bit 4 **CRYPEN:** Cryptographic modules clock enable

This bit is set and cleared by software.
0: cryptographic module clock disabled
1: cryptographic module clock enabled


Bits 3:1 Reserved, must be kept at reset value.


Bit 0 **DCMIEN:** Camera interface enable

This bit is set and cleared by software.

0: Camera interface clock disabled

1: Camera interface clock enabled


**6.3.12** **RCC AHB3 peripheral clock enable register (RCC_AHB3ENR)**


Address offset: 0x38


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access.


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1|0|
|---|---|
|Reserved|FMCEN|
|Reserved|rw|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **FMCEN:** Flexible memory controller module clock enable

This bit is set and cleared by software.

0: FMC module clock disabled

1: FMC module clock enabled


**6.3.13** **RCC APB1 peripheral clock enable register (RCC_APB1ENR)**


Address offset: 0x40


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access.














|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UART8<br>EN|UART7<br>EN|DAC<br>EN|PWR<br>EN|Reser-<br>ved|CAN2<br>EN|CAN1<br>EN|Reser-<br>ved|I2C3<br>EN|I2C2<br>EN|I2C1<br>EN|UART5<br>EN|UART4<br>EN|USART<br>3<br>EN|USART<br>2<br>EN|Reser-<br>ved|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|









|15|14|13 12|11|10 9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SPI3<br>EN|SPI2<br>EN|Reserved|WWDG<br>EN|Reserved|TIM14<br>EN|TIM13<br>EN|TIM12<br>EN|TIM7<br>EN|TIM6<br>EN|TIM5<br>EN|TIM4<br>EN|TIM3<br>EN|TIM2<br>EN|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


RM0090 Rev 21 185/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bit 31 **UART8EN** : UART8 clock enable

This bit is set and cleared by software.

0: UART8 clock disabled

1: UART8 clock enabled


Bit 30 **UART7EN** : UART7 clock enable

This bit is set and cleared by software.

0: UART7 clock disabled

1: UART7 clock enabled


Bit 29 **DACEN:** DAC interface clock enable

This bit is set and cleared by software.

0: DAC interface clock disabled

1: DAC interface clock enable


Bit 28 **PWREN:** Power interface clock enable

This bit is set and cleared by software.

0: Power interface clock disabled

1: Power interface clock enable


Bit 27 Reserved, must be kept at reset value.


Bit 26 **CAN2EN:** CAN 2 clock enable

This bit is set and cleared by software.

0: CAN 2 clock disabled

1: CAN 2 clock enabled


Bit 25 **CAN1EN:** CAN 1 clock enable

This bit is set and cleared by software.

0: CAN 1 clock disabled

1: CAN 1 clock enabled


Bit 24 Reserved, must be kept at reset value.


Bit 23 **I2C3EN:** I2C3 clock enable

This bit is set and cleared by software.

0: I2C3 clock disabled

1: I2C3 clock enabled


Bit 22 **I2C2EN:** I2C2 clock enable

This bit is set and cleared by software.

0: I2C2 clock disabled

1: I2C2 clock enabled


Bit 21 **I2C1EN:** I2C1 clock enable

This bit is set and cleared by software.

0: I2C1 clock disabled

1: I2C1 clock enabled


Bit 20 **UART5EN:** UART5 clock enable

This bit is set and cleared by software.

0: UART5 clock disabled

1: UART5 clock enabled


Bit 19 **UART4EN:** UART4 clock enable

This bit is set and cleared by software.

0: UART4 clock disabled

1: UART4 clock enabled


186/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bit 18 **USART3EN:** USART3 clock enable

This bit is set and cleared by software.

0: USART3 clock disabled

1: USART3 clock enabled


Bit 17 **USART2EN:** USART2 clock enable

This bit is set and cleared by software.

0: USART2 clock disabled

1: USART2 clock enabled


Bit 16 Reserved, must be kept at reset value.


Bit 15 **SPI3EN:** SPI3 clock enable

This bit is set and cleared by software.

0: SPI3 clock disabled

1: SPI3 clock enabled


Bit 14 **SPI2EN:** SPI2 clock enable

This bit is set and cleared by software.

0: SPI2 clock disabled

1: SPI2 clock enabled


Bits 13:12 Reserved, must be kept at reset value.


Bit 11 **WWDGEN:** Window watchdog clock enable

This bit is set and cleared by software.
0: Window watchdog clock disabled
1: Window watchdog clock enabled


Bit 10:9 Reserved, must be kept at reset value.


Bit 8 **TIM14EN:** TIM14 clock enable

This bit is set and cleared by software.

0: TIM14 clock disabled

1: TIM14 clock enabled


Bit 7 **TIM13EN:** TIM13 clock enable

This bit is set and cleared by software.

0: TIM13 clock disabled

1: TIM13 clock enabled


Bit 6 **TIM12EN:** TIM12 clock enable

This bit is set and cleared by software.

0: TIM12 clock disabled

1: TIM12 clock enabled


Bit 5 **TIM7EN:** TIM7 clock enable

This bit is set and cleared by software.

0: TIM7 clock disabled

1: TIM7 clock enabled


Bit 4 **TIM6EN:** TIM6 clock enable

This bit is set and cleared by software.

0: TIM6 clock disabled

1: TIM6 clock enabled


RM0090 Rev 21 187/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bit 3 **TIM5EN:** TIM5 clock enable

This bit is set and cleared by software.

0: TIM5 clock disabled

1: TIM5 clock enabled


Bit 2 **TIM4EN:** TIM4 clock enable

This bit is set and cleared by software.

0: TIM4 clock disabled

1: TIM4 clock enabled


Bit 1 **TIM3EN:** TIM3 clock enable

This bit is set and cleared by software.

0: TIM3 clock disabled

1: TIM3 clock enabled


Bit 0 **TIM2EN:** TIM2 clock enable

This bit is set and cleared by software.

0: TIM2 clock disabled

1: TIM2 clock enabled


188/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


**6.3.14** **RCC APB2 peripheral clock enable register (RCC_APB2ENR)**


Address offset: 0x44


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access.










|31 30 29 28 27|26|25 24 23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|
|Reserved|LTDC<br>EN|Reserved|SAI1EN|SPI6EN|SPI5EN|Res.|TIM11<br>EN|TIM10<br>EN|TIM9<br>EN|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|













|15|14|13|12|11|10|9|8|7 6|5|4|3 2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reser-<br>ved|SYSCF<br>G EN|SPI4E<br>N|SPI1<br>EN|SDIO<br>EN|ADC3<br>EN|ADC2<br>EN|ADC1<br>EN|Reserved|USART<br>6<br>EN|USART<br>1<br>EN|Reserved|TIM8<br>EN|TIM1<br>EN|
|Reser-<br>ved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:27 Reserved, must be kept at reset value.


Bit 26 **LTDCEN:** LTDC clock enable

This bit is set and cleared by software.

0: LTDC clock disabled

1: LTDC clock enabled


Bits 27: 23 Reserved, must be kept at reset value.


Bit 22 **SAI1EN:** SAI1 clock enable

This bit is set and cleared by software.

0: SAI1 clock disabled

1: SAI1 clock enabled


Bit 21 **SPI6EN:** SPI6 clock enable

This bit is set and cleared by software.

0: SPI6 clock disabled

1: SPI6 clock enabled


Bit 20 **SPI5EN:** SPI5 clock enable

This bit is set and cleared by software.

0: SPI5 clock disabled

1: SPI5 clock enabled


Bit 18 **TIM11EN:** TIM11 clock enable

This bit is set and cleared by software.

0: TIM11 clock disabled

1: TIM11 clock enabled


Bit 17 **TIM10EN:** TIM10 clock enable

This bit is set and cleared by software.

0: TIM10 clock disabled

1: TIM10 clock enabled


Bit 16 **TIM9EN:** TIM9 clock enable

This bit is set and cleared by software.

0: TIM9 clock disabled

1: TIM9 clock enabled


Bit 15 Reserved, must be kept at reset value.


RM0090 Rev 21 189/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bit 14 **SYSCFGEN:** System configuration controller clock enable

This bit is set and cleared by software.
0: System configuration controller clock disabled
1: System configuration controller clock enabled


Bit 13 **SPI4EN:** SPI4 clock enable

This bit is set and cleared by software.

0: SPI4 clock disabled

1: SPI4 clock enabled


Bit 12 **SPI1EN:** SPI1 clock enable

This bit is set and cleared by software.

0: SPI1 clock disabled

1: SPI1 clock enabled


Bit 11 **SDIOEN:** SDIO clock enable

This bit is set and cleared by software.

0: SDIO module clock disabled

1: SDIO module clock enabled


Bit 10 **ADC3EN:** ADC3 clock enable

This bit is set and cleared by software.

0: ADC3 clock disabled

1: ADC3 clock enabled


Bit 9 **ADC2EN:** ADC2 clock enable

This bit is set and cleared by software.

0: ADC2 clock disabled

1: ADC2 clock enabled


Bit 8 **ADC1EN:** ADC1 clock enable

This bit is set and cleared by software.

0: ADC1 clock disabled

1: ADC1 clock enabled


Bits 7:6 Reserved, must be kept at reset value.


Bit 5 **USART6EN:** USART6 clock enable

This bit is set and cleared by software.

0: USART6 clock disabled

1: USART6 clock enabled


Bit 4 **USART1EN:** USART1 clock enable

This bit is set and cleared by software.

0: USART1 clock disabled

1: USART1 clock enabled


Bits 3:2 Reserved, must be kept at reset value.


Bit 1 **TIM8EN:** TIM8 clock enable

This bit is set and cleared by software.

0: TIM8 clock disabled

1: TIM8 clock enabled


Bit 0 **TIM1EN:** TIM1 clock enable

This bit is set and cleared by software.

0: TIM1 clock disabled

1: TIM1 clock enabled


190/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


**6.3.15** **RCC AHB1 peripheral clock enable in low power mode register**
**(RCC_AHB1LPENR)**


Address offset: 0x50


Reset value: 0x7EEF 97FF


Access: no wait state, word, half-word and byte access.


























|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|OTGHS<br>ULPILPE<br>N|OTGH<br>S<br>LPEN|ETHPT<br>P<br>LPEN|ETHRX<br>LPEN|ETHTX<br>LPEN|ETHMA<br>C<br>LPEN|Res.|DMA2D<br>LPEN|DMA2<br>LPEN|DMA1<br>LPEN|Res.|SRAM3<br>LPEN|BKPSRA<br>M<br>LPEN|SRAM<br>2<br>LPEN|SRAM<br>1<br>LPEN|
|Res.|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|















|15|14 13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|FLITF<br>LPEN|Reserved|CRC<br>LPEN|Res.|GPIOK<br>LPEN|GPIOIJ<br>LPEN|GPIOI<br>LPEN|GPIOH<br>LPEN|GPIOG<br>G<br>LPEN|GPIO<br>F<br>LPEN|GPIOE<br>LPEN|GPIOD<br>LPEN|GPIOC<br>LPEN|GPIOB<br>LPEN|GPIOA<br>LPEN|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bit 31 Reserved, must be kept at reset value.


Bit 30 **OTGHSULPILPEN:** USB OTG HS ULPI clock enable during Sleep mode

This bit is set and cleared by software. It must be cleared when the OTG_HS is used in FS
mode.

0: USB OTG HS ULPI clock disabled during Sleep mode
1: USB OTG HS ULPI clock enabled during Sleep mode


Bit 29 **OTGHSLPEN:** USB OTG HS clock enable during Sleep mode

This bit is set and cleared by software.
0: USB OTG HS clock disabled during Sleep mode
1: USB OTG HS clock enabled during Sleep mode


Bit 28 **ETHMACPTPLPEN:** Ethernet PTP clock enable during Sleep mode

This bit is set and cleared by software.
0: Ethernet PTP clock disabled during Sleep mode
1: Ethernet PTP clock enabled during Sleep mode


Bit 27 **ETHMACRXLPEN:** Ethernet reception clock enable during Sleep mode

This bit is set and cleared by software.
0: Ethernet reception clock disabled during Sleep mode
1: Ethernet reception clock enabled during Sleep mode


Bit 26 **ETHMACTXLPEN:** Ethernet transmission clock enable during Sleep mode

This bit is set and cleared by software.
0: Ethernet transmission clock disabled during sleep mode
1: Ethernet transmission clock enabled during sleep mode


Bit 25 **ETHMACLPEN:** Ethernet MAC clock enable during Sleep mode

This bit is set and cleared by software.
0: Ethernet MAC clock disabled during Sleep mode
1: Ethernet MAC clock enabled during Sleep mode


Bit 24 Reserved, must be kept at reset value.


RM0090 Rev 21 191/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bit 23 **DMA2DLPEN:** DMA2D clock enable during Sleep mode

This bit is set and cleared by software.
0: DMA2D clock disabled during Sleep mode
1: DMA2D clock enabled during Sleep mode


Bit 22 **DMA2LPEN:** DMA2 clock enable during Sleep mode

This bit is set and cleared by software.
0: DMA2 clock disabled during Sleep mode
1: DMA2 clock enabled during Sleep mode


Bit 21 **DMA1LPEN:** DMA1 clock enable during Sleep mode

This bit is set and cleared by software.
0: DMA1 clock disabled during Sleep mode
1: DMA1 clock enabled during Sleep mode


Bit 20 Reserved, must be kept at reset value.


Bit 19 **SRAM3LPEN:** SRAM3 interface clock enable during Sleep mode

This bit is set and cleared by software.
0: SRAM3 interface clock disabled during Sleep mode
1: SRAM3 interface clock enabled during Sleep mode


Bit 18 **BKPSRAMLPEN:** Backup SRAM interface clock enable during Sleep mode

This bit is set and cleared by software.
0: Backup SRAM interface clock disabled during Sleep mode
1: Backup SRAM interface clock enabled during Sleep mode


Bit 17 **SRAM2LPEN:** SRAM2 interface clock enable during Sleep mode

This bit is set and cleared by software.
0: SRAM2 interface clock disabled during Sleep mode
1: SRAM2 interface clock enabled during Sleep mode


Bit 16 **SRAM1LPEN:** SRAM1 interface clock enable during Sleep mode

This bit is set and cleared by software.
0: SRAM1 interface clock disabled during Sleep mode
1: SRAM1 interface clock enabled during Sleep mode


Bit 15 **FLITFLPEN:** Flash interface clock enable during Sleep mode

This bit is set and cleared by software.
0: Flash interface clock disabled during Sleep mode
1: Flash interface clock enabled during Sleep mode


Bits 14:13 Reserved, must be kept at reset value.


Bit 12 **CRCLPEN:** CRC clock enable during Sleep mode

This bit is set and cleared by software.
0: CRC clock disabled during Sleep mode
1: CRC clock enabled during Sleep mode


Bit 11 Reserved, must be kept at reset value.


Bit 10 **GPIOKLPEN:** IO port K clock enable during Sleep mode

This bit is set and cleared by software.
0: IO port K clock disabled during Sleep mode
1: IO port K clock enabled during Sleep mode


192/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bit 9 **GPIOJLPEN:** IO port J clock enable during Sleep mode

This bit is set and cleared by software.
0: IO port J clock disabled during Sleep mode
1: IO port J clock enabled during Sleep mode


Bit 8 **GPIOILPEN:** IO port I clock enable during Sleep mode

This bit is set and cleared by software.
0: IO port I clock disabled during Sleep mode
1: IO port I clock enabled during Sleep mode


Bit 7 **GPIOHLPEN:** IO port H clock enable during Sleep mode
This bit is set and cleared by software.
0: IO port H clock disabled during Sleep mode
1: IO port H clock enabled during Sleep mode


Bits 6 **GPIOGLPEN:** IO port G clock enable during Sleep mode

This bit is set and cleared by software.
0: IO port G clock disabled during Sleep mode
1: IO port G clock enabled during Sleep mode


Bit 5 **GPIOFLPEN:** IO port F clock enable during Sleep mode

This bit is set and cleared by software.
0: IO port F clock disabled during Sleep mode
1: IO port F clock enabled during Sleep mode


Bit 4 **GPIOELPEN:** IO port E clock enable during Sleep mode

Set and cleared by software.
0: IO port E clock disabled during Sleep mode
1: IO port E clock enabled during Sleep mode


Bit 3 **GPIODLPEN:** IO port D clock enable during Sleep mode

This bit is set and cleared by software.
0: IO port D clock disabled during Sleep mode
1: IO port D clock enabled during Sleep mode


Bit 2 **GPIOCLPEN:** IO port C clock enable during Sleep mode

This bit is set and cleared by software.
0: IO port C clock disabled during Sleep mode
1: IO port C clock enabled during Sleep mode


Bit 1 **GPIOBLPEN:** IO port B clock enable during Sleep mode

This bit is set and cleared by software.
0: IO port B clock disabled during Sleep mode
1: IO port B clock enabled during Sleep mode


Bit 0 **GPIOALPEN:** IO port A clock enable during sleep mode

This bit is set and cleared by software.
0: IO port A clock disabled during Sleep mode
1: IO port A clock enabled during Sleep mode


RM0090 Rev 21 193/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


**6.3.16** **RCC AHB2 peripheral clock enable in low power mode register**
**(RCC_AHB2LPENR)**


Address offset: 0x54


Reset value: 0x0000 00F1


Access: no wait state, word, half-word and byte access.


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved









|15 14 13 12 11 10 9 8|7|6|5|4|3 2 1|0|
|---|---|---|---|---|---|---|
|Reserved|OTGFS<br>LPEN|RNG<br>LPEN|HASH<br>LPEN|CRYP<br>LPEN|Reserved|DCMI<br>LPEN|
|Reserved|rw|rw|rw|rw|rw|rw|


Bits 31:8 Reserved, must be kept at reset value.


Bit 7 **OTGFSLPEN:** USB OTG FS clock enable during Sleep mode

This bit is set and cleared by software.
0: USB OTG FS clock disabled during Sleep mode
1: USB OTG FS clock enabled during Sleep mode


Bit 6 **RNGLPEN:** Random number generator clock enable during Sleep mode

This bit is set and cleared by software.
0: Random number generator clock disabled during Sleep mode
1: Random number generator clock enabled during Sleep mode


Bit 5 **HASHLPEN:** Hash modules clock enable during Sleep mode

This bit is set and cleared by software.
0: Hash modules clock disabled during Sleep mode
1: Hash modules clock enabled during Sleep mode


Bit 4 **CRYPLPEN:** Cryptography modules clock enable during Sleep mode

This bit is set and cleared by software.
0: cryptography modules clock disabled during Sleep mode
1: cryptography modules clock enabled during Sleep mode


Bits 3:1 Reserved, must be kept at reset value.


Bit 0 **DCMILPEN:** Camera interface enable during Sleep mode

This bit is set and cleared by software.
0: Camera interface clock disabled during Sleep mode
1: Camera interface clock enabled during Sleep mode


194/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


**6.3.17** **RCC AHB3 peripheral clock enable in low power mode register**
**(RCC_AHB3LPENR)**


Address offset: 0x58


Reset value: 0x0000 0001


Access: no wait state, word, half-word and byte access.


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved



|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1|0|
|---|---|
|Reserved|FMC<br>LPEN|
|Reserved|rw|


Bits 31:1Reserved, must be kept at reset value.





Bit 0



**FMCLPEN:** Flexible memory controller module clock enable during Sleep mode

This bit is set and cleared by software.
0: FMC module clock disabled during Sleep mode
1: FMC module clock enabled during Sleep mode



**6.3.18** **RCC APB1 peripheral clock enable in low power mode register**
**(RCC_APB1LPENR)**


Address offset: 0x60


Reset value: 0xF6FE C9FF


Access: no wait state, word, half-word and byte access.












|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UART8<br>LPEN|UART7<br>LPEN|DAC<br>LPEN|PWR<br>LPEN|RESER<br>VED|CAN2<br>LPEN|CAN1<br>LPEN|Reser-<br>ved|I2C3<br>LPEN|I2C2<br>LPEN|I2C1<br>LPEN|UART5<br>LPEN|UART4<br>LPEN|USART<br>3<br>LPEN|USART<br>2<br>LPEN|Reser-<br>ved|
|rw|rw|rw|rw||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|









|15|14|13 12|11|10 9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SPI3<br>LPEN|SPI2<br>LPEN|Reserved|WWDG<br>LPEN|Reserved|TIM14<br>LPEN|TIM13<br>LPEN|TIM12<br>LPEN|TIM7<br>LPEN|TIM6<br>LPEN|TIM5<br>LPEN|TIM4<br>LPEN|TIM3<br>LPEN|TIM2<br>LPEN|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


RM0090 Rev 21 195/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bit 31 **UART8LPEN:** UART8 clock enable during Sleep mode

This bit is set and cleared by software.
0: UART8 clock disabled during Sleep mode
1: UART8 clock enabled during Sleep mode


Bit 30 **UART7LPEN:** UART7 clock enable during Sleep mode

This bit is set and cleared by software.
0: UART7 clock disabled during Sleep mode
1: UART7 clock enabled during Sleep mode


Bit 29 **DACLPEN:** DAC interface clock enable during Sleep mode

This bit is set and cleared by software.
0: DAC interface clock disabled during Sleep mode
1: DAC interface clock enabled during Sleep mode


Bit 28 **PWRLPEN:** Power interface clock enable during Sleep mode

This bit is set and cleared by software.
0: Power interface clock disabled during Sleep mode
1: Power interface clock enabled during Sleep mode


Bit 27 Reserved, must be kept at reset value.


Bit 26 **CAN2LPEN:** CAN 2 clock enable during Sleep mode

This bit is set and cleared by software.
0: CAN 2 clock disabled during sleep mode
1: CAN 2 clock enabled during sleep mode


Bit 25 **CAN1LPEN:** CAN 1 clock enable during Sleep mode

This bit is set and cleared by software.
0: CAN 1 clock disabled during Sleep mode
1: CAN 1 clock enabled during Sleep mode


Bit 24 Reserved, must be kept at reset value.


Bit 23 **I2C3LPEN:** I2C3 clock enable during Sleep mode

This bit is set and cleared by software.
0: I2C3 clock disabled during Sleep mode
1: I2C3 clock enabled during Sleep mode


Bit 22 **I2C2LPEN:** I2C2 clock enable during Sleep mode

This bit is set and cleared by software.
0: I2C2 clock disabled during Sleep mode
1: I2C2 clock enabled during Sleep mode


Bit 21 **I2C1LPEN:** I2C1 clock enable during Sleep mode

This bit is set and cleared by software.
0: I2C1 clock disabled during Sleep mode
1: I2C1 clock enabled during Sleep mode


Bit 20 **UART5LPEN:** UART5 clock enable during Sleep mode

This bit is set and cleared by software.
0: UART5 clock disabled during Sleep mode
1: UART5 clock enabled during Sleep mode


Bit 19 **UART4LPEN:** UART4 clock enable during Sleep mode

This bit is set and cleared by software.
0: UART4 clock disabled during Sleep mode
1: UART4 clock enabled during Sleep mode


196/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bit 18 **USART3LPEN:** USART3 clock enable during Sleep mode
This bit is set and cleared by software.
0: USART3 clock disabled during Sleep mode
1: USART3 clock enabled during Sleep mode


Bit 17 **USART2LPEN:** USART2 clock enable during Sleep mode

This bit is set and cleared by software.
0: USART2 clock disabled during Sleep mode
1: USART2 clock enabled during Sleep mode


Bit 16 Reserved, must be kept at reset value.


Bit 15 **SPI3LPEN:** SPI3 clock enable during Sleep mode

This bit is set and cleared by software.
0: SPI3 clock disabled during Sleep mode
1: SPI3 clock enabled during Sleep mode


Bit 14 **SPI2LPEN:** SPI2 clock enable during Sleep mode

This bit is set and cleared by software.
0: SPI2 clock disabled during Sleep mode
1: SPI2 clock enabled during Sleep mode


Bits 13:12 Reserved, must be kept at reset value.


Bit 11 **WWDGLPEN:** Window watchdog clock enable during Sleep mode

This bit is set and cleared by software.
0: Window watchdog clock disabled during sleep mode
1: Window watchdog clock enabled during sleep mode


Bits 10:9 Reserved, must be kept at reset value.


Bit 8 **TIM14LPEN:** TIM14 clock enable during Sleep mode

This bit is set and cleared by software.
0: TIM14 clock disabled during Sleep mode
1: TIM14 clock enabled during Sleep mode


Bit 7 **TIM13LPEN:** TIM13 clock enable during Sleep mode

This bit is set and cleared by software.
0: TIM13 clock disabled during Sleep mode
1: TIM13 clock enabled during Sleep mode


Bit 6 **TIM12LPEN:** TIM12 clock enable during Sleep mode

This bit is set and cleared by software.
0: TIM12 clock disabled during Sleep mode
1: TIM12 clock enabled during Sleep mode


Bit 5 **TIM7LPEN:** TIM7 clock enable during Sleep mode

This bit is set and cleared by software.
0: TIM7 clock disabled during Sleep mode
1: TIM7 clock enabled during Sleep mode


Bit 4 **TIM6LPEN:** TIM6 clock enable during Sleep mode

This bit is set and cleared by software.
0: TIM6 clock disabled during Sleep mode
1: TIM6 clock enabled during Sleep mode


RM0090 Rev 21 197/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bit 3 **TIM5LPEN:** TIM5 clock enable during Sleep mode

This bit is set and cleared by software.
0: TIM5 clock disabled during Sleep mode
1: TIM5 clock enabled during Sleep mode


Bit 2 **TIM4LPEN:** TIM4 clock enable during Sleep mode

This bit is set and cleared by software.
0: TIM4 clock disabled during Sleep mode
1: TIM4 clock enabled during Sleep mode


Bit 1 **TIM3LPEN:** TIM3 clock enable during Sleep mode

This bit is set and cleared by software.
0: TIM3 clock disabled during Sleep mode
1: TIM3 clock enabled during Sleep mode


Bit 0 **TIM2LPEN:** TIM2 clock enable during Sleep mode
This bit is set and cleared by software.
0: TIM2 clock disabled during Sleep mode
1: TIM2 clock enabled during Sleep mode


198/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


**6.3.19** **RCC APB2 peripheral clock enabled in low power mode register**
**(RCC_APB2LPENR)**


Address offset: 0x64


Reset value: 0x0x0477 7F33


Access: no wait state, word, half-word and byte access.












|31 30 29 28 27|26|25 24 23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|
|Reserved|LTDC<br>LPEN|Reserved|SAI1<br>LPEN|SPI6<br>LPEN|SPI5<br>LPEN|Reser-<br>ved|TIM11<br>LPEN|TIM10<br>LPEN|TIM9<br>LPEN|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|















|15|14|13|12|11|10|9|8|7 6|5|4|3 2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reser-<br>ved|SYSC<br>FG<br>LPEN|SPI4<br>LPEN|SPI1<br>LPEN|SDIO<br>LPEN|ADC3<br>LPEN|ADC2<br>LPEN|ADC1<br>LPEN|Reserved|USART<br>6<br>LPEN|USART<br>1<br>LPEN|Reserved|TIM8<br>LPEN|TIM1<br>LPEN|
|Reser-<br>ved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:27 Reserved, must be kept at reset value.


Bit 26 **LTDCLPEN:** LTDC clock enable during Sleep mode

This bit is set and cleared by software.
0: LTDC clock disabled during Sleep mode
1: LTDC clock enabled during Sleep mode


Bits 25:23 Reserved, must be kept at reset value.


Bit 22 **SAI1LPEN:** SAI1 clock enable during Sleep mode

This bit is set and cleared by software.
0: SAI1 clock disabled during Sleep mode
1: SAI1 clock enabled during Sleep mode


Bit 21 **SPI6LPEN:** SPI6 clock enable during Sleep mode

This bit is set and cleared by software.
0: SPI6 clock disabled during Sleep mode
1: SPI6 clock enabled during Sleep mode


Bit 20 **SPI5LPEN:** SPI5 clock enable during Sleep mode

This bit is set and cleared by software.
0: SPI5 clock disabled during Sleep mode
1: SPI5 clock enabled during Sleep mode


Bit 19 Reserved, must be kept at reset value.


Bit 18 **TIM11LPEN:** TIM11 clock enable during Sleep mode

This bit is set and cleared by software.
0: TIM11 clock disabled during Sleep mode
1: TIM11 clock enabled during Sleep mode


Bit 17 **TIM10LPEN:** TIM10 clock enable during Sleep mode

This bit is set and cleared by software.
0: TIM10 clock disabled during Sleep mode
1: TIM10 clock enabled during Sleep mode


RM0090 Rev 21 199/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bit 16 **TIM9LPEN:** TIM9 clock enable during sleep mode

This bit is set and cleared by software.
0: TIM9 clock disabled during Sleep mode
1: TIM9 clock enabled during Sleep mode


Bit 15 Reserved, must be kept at reset value.


Bit 14 **SYSCFGLPEN:** System configuration controller clock enable during Sleep mode

This bit is set and cleared by software.
0: System configuration controller clock disabled during Sleep mode
1: System configuration controller clock enabled during Sleep mode


Bit 13 **SPI4LPEN:** SPI4 clock enable during Sleep mode

This bit is set and cleared by software.
0: SPI4 clock disabled during Sleep mode
1: SPI4 clock enabled during Sleep mode


Bit 12 **SPI1LPEN:** SPI1 clock enable during Sleep mode

This bit is set and cleared by software.
0: SPI1 clock disabled during Sleep mode
1: SPI1 clock enabled during Sleep mode


Bit 11 **SDIOLPEN:** SDIO clock enable during Sleep mode

This bit is set and cleared by software.
0: SDIO module clock disabled during Sleep mode
1: SDIO module clock enabled during Sleep mode


Bit 10 **ADC3LPEN:** ADC 3 clock enable during Sleep mode

This bit is set and cleared by software.
0: ADC 3 clock disabled during Sleep mode
1: ADC 3 clock enabled during Sleep mode


Bit 9 **ADC2LPEN:** ADC2 clock enable during Sleep mode

This bit is set and cleared by software.
0: ADC2 clock disabled during Sleep mode
1: ADC2 clock enabled during Sleep mode


Bit 8 **ADC1LPEN:** ADC1 clock enable during Sleep mode

This bit is set and cleared by software.
0: ADC1 clock disabled during Sleep mode
1: ADC1 clock enabled during Sleep mode


Bits 7:6 Reserved, must be kept at reset value.


Bit 5 **USART6LPEN:** USART6 clock enable during Sleep mode

This bit is set and cleared by software.
0: USART6 clock disabled during Sleep mode
1: USART6 clock enabled during Sleep mode


Bit 4 **USART1LPEN:** USART1 clock enable during Sleep mode

This bit is set and cleared by software.
0: USART1 clock disabled during Sleep mode
1: USART1 clock enabled during Sleep mode


200/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bits 3:2 Reserved, must be kept at reset value.


Bit 1 **TIM8LPEN:** TIM8 clock enable during Sleep mode

This bit is set and cleared by software.
0: TIM8 clock disabled during Sleep mode
1: TIM8 clock enabled during Sleep mode


Bit 0 **TIM1LPEN:** TIM1 clock enable during Sleep mode

This bit is set and cleared by software.
0: TIM1 clock disabled during Sleep mode
1: TIM1 clock enabled during Sleep mode


**6.3.20** **RCC Backup domain control register (RCC_BDCR)**


Address offset: 0x70


Reset value: 0x0000 0000, reset by Backup domain reset.
Access: 0 ≤ wait state ≤ 3, word, half-word and byte access
Wait states are inserted in case of successive accesses to this register.


The LSEON, LSEBYP, RTCSEL and RTCEN bits in the _RCC Backup domain control_
_register (RCC_BDCR)_ are in the Backup domain. As a result, after Reset, these bits are
write-protected and the DBP bit in the _PWR power control register (PWR_CR) for_
_STM32F42xxx and STM32F43xxx_ has to be set before these can be modified. Refer to
_Section 6.1.1: System reset on page 152_ for further information. These bits are only reset
after a Backup domain Reset (see _Section 6.1.3: Backup domain reset_ ). Any internal or
external Reset has no effect on these bits.


|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17|16|
|---|---|
|Reserved|BDRST|
|Reserved|rw|







|15|14 13 12 11 10|9 8|Col4|7 6 5 4 3|2|1|0|
|---|---|---|---|---|---|---|---|
|RTCEN|Reserved|RTCSEL[1:0]|RTCSEL[1:0]|Reserved|LSEBY<br>P|LSERD<br>Y|LSEON|
|rw|rw|rw|rw|rw|rw|r|rw|


Bits 31:17 Reserved, must be kept at reset value.


Bit 16 **BDRST:** Backup domain software reset

This bit is set and cleared by software.

0: Reset not activated

1: Resets the entire Backup domain

_Note: The BKPSRAM is not affected by this reset, the only way of resetting the BKPSRAM is_
_through the Flash interface when a protection level change from level 1 to level 0 is_
_requested._

_The backup domain software reset does not take effect until the DBP bit of the_
_PWR_CR register is set._


Bit 15 **RTCEN:** RTC clock enable

This bit is set and cleared by software.

0: RTC clock disabled

1: RTC clock enabled


Bits 14:10 Reserved, must be kept at reset value.


RM0090 Rev 21 201/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bits 9:8 **RTCSEL[1:0]:** RTC clock source selection

These bits are set by software to select the clock source for the RTC. Once the RTC clock
source has been selected, it cannot be changed anymore unless the Backup domain is
reset. The BDRST bit can be used to reset them.

00: No clock

01: LSE oscillator clock used as the RTC clock

10: LSI oscillator clock used as the RTC clock

11: HSE oscillator clock divided by a programmable prescaler (selection through the
RTCPRE[4:0] bits in the RCC clock configuration register (RCC_CFGR)) used as the RTC
clock


Bits 7:3 Reserved, must be kept at reset value.


Bit 2 **LSEBYP:** External low-speed oscillator bypass

This bit is set and cleared by software to bypass the oscillator. This bit can be written only
when the LSE clock is disabled.

0: LSE oscillator not bypassed
1: LSE oscillator bypassed


Bit 1 **LSERDY:** External low-speed oscillator ready

This bit is set and cleared by hardware to indicate when the external 32 kHz oscillator is
stable. After the LSEON bit is cleared, LSERDY goes low after 6 external low-speed
oscillator clock cycles.
0: LSE clock not ready
1: LSE clock ready


Bit 0 **LSEON:** External low-speed oscillator enable

This bit is set and cleared by software.

0: LSE clock OFF

1: LSE clock ON


**6.3.21** **RCC clock control & status register (RCC_CSR)**


Address offset: 0x74


Reset value: 0x0E00 0000, reset by system reset, except reset flags by power reset only.


Access: 0 ≤ wait state ≤ 3, word, half-word and byte access


Wait states are inserted in case of successive accesses to this register.

|31|30|29|28|27|26|25|24|23 22 21 20 19 18 17 16|
|---|---|---|---|---|---|---|---|---|
|LPWR<br>RSTF|WWDG<br>RSTF|IWDG<br>RSTF|SFT<br>RSTF|POR<br>RSTF|PIN<br>RSTF|BORRS<br>TF|RMVF|Reserved|
|r|r|r|r|r|r|r|rt_w|rt_w|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2|1|0|
|---|---|---|
|Reserved|LSIRDY|LSION|
|Reserved|r|rw|



202/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bit 31 **LPWRRSTF:** Low-power reset flag

This bit is set by hardware when a Low-power management reset occurs.
Cleared by writing to the RMVF bit.
0: No Low-power management reset occurred
1: Low-power management reset occurred
For further information on Low-power management reset, refer to _Low-power management_
_reset_ .


Bit 30 **WWDGRSTF:** Window watchdog reset flag

This bit is set by hardware when a window watchdog reset occurs.
Cleared by writing to the RMVF bit.
0: No window watchdog reset occurred
1: Window watchdog reset occurred


Bit 29 **IWDGRSTF** : Independent watchdog reset flag

This bit is set by hardware when an independent watchdog reset from V DD domain occurs.
Cleared by writing to the RMVF bit.
0: No watchdog reset occurred
1: Watchdog reset occurred


Bit 28 **SFTRSTF:** Software reset flag

This bit is set by hardware when a software reset occurs.
Cleared by writing to the RMVF bit.

0: No software reset occurred

1: Software reset occurred


Bit 27 **PORRSTF:** POR/PDR reset flag

This bit is set by hardware when a POR/PDR reset occurs.
Cleared by writing to the RMVF bit.

0: No POR/PDR reset occurred

1: POR/PDR reset occurred


Bit 26 **PINRSTF:** PIN reset flag

This bit is set by hardware when a reset from the NRST pin occurs.
Cleared by writing to the RMVF bit.
0: No reset from NRST pin occurred
1: Reset from NRST pin occurred


Bit 25 **BORRSTF:** BOR reset flag

Cleared by software by writing the RMVF bit.
This bit is set by hardware when a POR/PDR or BOR reset occurs.

0: No POR/PDR or BOR reset occurred

1: POR/PDR or BOR reset occurred


Bit 24 **RMVF:** Remove reset flag

This bit is set by software to clear the reset flags.

0: No effect

1: Clear the reset flags


RM0090 Rev 21 203/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bits 23:2 Reserved, must be kept at reset value.


Bit 1 **LSIRDY:** Internal low-speed oscillator ready

This bit is set and cleared by hardware to indicate when the internal RC 40 kHz oscillator is
stable. After the LSION bit is cleared, LSIRDY goes low after 3 LSI clock cycles.
0: LSI RC oscillator not ready
1: LSI RC oscillator ready


Bit 0 **LSION:** Internal low-speed oscillator enable

This bit is set and cleared by software.

0: LSI RC oscillator OFF

1: LSI RC oscillator ON


**6.3.22** **RCC spread spectrum clock generation register (RCC_SSCGR)**


Address offset: 0x80


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access.


The spread spectrum clock generation is available only for the main PLL.


The RCC_SSCGR register must be written either before the main PLL is enabled or after
the main PLL disabled.


_Note:_ _For full details about PLL spread spectrum clock generation (SSCG) characteristics, refer to_
_the “Electrical characteristics” section in your device datasheet._







|31|30|29 28|27 26 25 24 23 22 21 20 19 18 17 16|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SSCG<br>EN|SPR<br>EAD<br>SEL|Reserved|INCSTEP|INCSTEP|INCSTEP|INCSTEP|INCSTEP|INCSTEP|INCSTEP|INCSTEP|INCSTEP|INCSTEP|INCSTEP|INCSTEP|
|rw|rw|rw|rw|rw|rw||rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13|Col2|Col3|12 11 10 9 8 7 6 5 4 3 2 1 0|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|INCSTEP|INCSTEP|INCSTEP|MODPER|MODPER|MODPER|MODPER|MODPER|MODPER|MODPER|MODPER|MODPER|MODPER|MODPER|MODPER|MODPER|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bit 31 **SSCGEN:** Spread spectrum modulation enable

This bit is set and cleared by software.
0: Spread spectrum modulation DISABLE. (To write after clearing CR[24]=PLLON bit)
1: Spread spectrum modulation ENABLE. (To write before setting CR[24]=PLLON bit)


Bit 30 **SPREADSEL:** Spread Select

This bit is set and cleared by software.
To write before to set CR[24]=PLLON bit.
0: Center spread
1: Down spread


204/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bits 29:28 Reserved, must be kept at reset value.


Bits 27:13 **INCSTEP:** Incrementation step

These bits are set and cleared by software. To write before setting CR[24]=PLLON bit.
Configuration input for modulation profile amplitude.


Bits 12:0 **MODPER:** Modulation period

These bits are set and cleared by software. To write before setting CR[24]=PLLON bit.
Configuration input for modulation profile period.


**6.3.23** **RCC PLLI2S configuration register (RCC_PLLI2SCFGR)**


Address offset: 0x84


Reset value: 0x2400 3000


Access: no wait state, word, half-word and byte access.


This register is used to configure the PLLI2S clock outputs according to the formulas:

f (VCO clock) = f (PLLI2S clock input) × (PLLI2SN / PLLM)

f = f / PLLI2SR
(PLL I2S clock output) (VCO clock)






|31|30|29|28|27 26 25 24|Col6|Col7|Col8|23 22 21 20 19 18 17 16|
|---|---|---|---|---|---|---|---|---|
|Reserv<br>ed|PLLI2S<br>R2|PLLI2S<br>R1|PLLI2S<br>R0|PLLI2SQ|PLLI2SQ|PLLI2SQ|PLLI2SQ|Reserved|
|Reserv<br>ed|rw|rw|rw|rw|rw|rw|rw|rw|







|15|14|13|12|11|10|9|8|7|6|5 4 3 2 1 0|
|---|---|---|---|---|---|---|---|---|---|---|
|Reserv<br>ed|PLLI2SN<br>8|PLLI2SN<br>7|PLLI2SN<br>6|PLLI2SN<br>5|PLLI2SN<br>4|PLLI2SN<br>3|PLLI2SN<br>2|PLLI2SN<br>1|PLLI2SN<br>0|Reserved|
|Reserv<br>ed|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


RM0090 Rev 21 205/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bit 31 Reserved, must be kept at reset value.


Bits 30:28 **PLLI2SR:** PLLI2S division factor for I2S clocks

These bits are set and cleared by software to control the I2S clock frequency. These bits
should be written only if the PLLI2S is disabled. The factor must be chosen in accordance
with the prescaler values inside the I2S peripherals, to reach 0.3% error when using
standard crystals and 0% error with audio crystals. For more information about I2S clock
frequency and precision, refer to _Section 28.4.4: Clock generator_ in the I2S chapter.


**Caution:** The I2Ss requires a frequency lower than or equal to 192 MHz to work correctly.
I2S clock frequency = VCO frequency / PLLR with 2 ≤ PLLR ≤ 7
000: PLLR = 0, wrong configuration
001: PLLR = 1, wrong configuration
010: PLLR = 2

...

111: PLLR = 7


Bits 27:24 **PLLI2SQ** : PLLI2S division factor for SAI1 clock

These bits are set and cleared by software to control the SAI1 clock frequency.
They should be written when the PLLI2S is disabled.
SAI1 clock frequency = VCO frequency / PLLI2SQ with 2 <= PLLI2SIQ <= 15
0000: PLLI2SQ = 0, wrong configuration
0001: PLLI2SQ = 1, wrong configuration

0010: PLLI2SQ = 2

0011: PLLI2SQ = 3

0100: PLLI2SQ = 4

0101: PLLI2SQ = 5

...

1111: PLLI2SQ = 15


206/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bits 23:15 Reserved, must be kept at reset value.


Bits 14:6 **PLLI2SN:** PLLI2S multiplication factor for VCO

These bits are set and cleared by software to control the multiplication factor of the VCO.
These bits can be written only when PLLI2S is disabled. Only half-word and word accesses
are allowed to write these bits.


**Caution:** The software has to set these bits correctly to ensure that the VCO output
frequency is between 100 and 432 MHz.
VCO output frequency = VCO input frequency × PLLI2SN with 50 ≤ PLLI2SN ≤ 432
000000000: PLLI2SN = 0, wrong configuration
000000001: PLLI2SN = 1, wrong configuration

...

000110010: PLLI2SN = 50

...

001100011: PLLI2SN = 99

001100100: PLLI2SN = 100

001100101: PLLI2SN = 101

001100110: PLLI2SN = 102

...

110110000: PLLI2SN = 432

110110001: PLLI2SN = 433, wrong configuration

...

111111111: PLLI2SN = 511, wrong configuration

_Note: Multiplication factors ranging from 50 and 99 are possible for VCO input frequency_
_higher than 1 MHz. However care must be taken that the minimum VCO output_
_frequency respects the value specified above._


Bits 5:0 Reserved, must be kept at reset value.


RM0090 Rev 21 207/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


**6.3.24** **RCC PLL configuration register (RCC_PLLSAICFGR)**


Address offset: 0x88


Reset value: 0x2400 3000


Access: no wait state, word, half-word and byte access.


This register is used to configure the PLLSAI clock outputs according to the formulas:

      - f (VCO clock) = f (PLLSAI clock input) × (PLLSAIN / PLLM)

      - f = f / PLLSAIQ
(PLLSAI1 clock output) (VCO clock)

      - f = f / PLLSAIR
(PLL LCD clock output) (VCO clock)

|31|30 29 28|Col3|Col4|27 26 25 24|Col6|Col7|Col8|23 22 21 20 19 18 17 16|
|---|---|---|---|---|---|---|---|---|
|Reserved|PLLSAIR|PLLSAIR|PLLSAIR|PLLSAIQ|PLLSAIQ|PLLSAIQ|PLLSAIQ|Reserved|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14 13 12 11 10 9 8 7 6|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|5 4 3 2 1 0|
|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|PLLSAIN|PLLSAIN|PLLSAIN|PLLSAIN|PLLSAIN|PLLSAIN|PLLSAIN|PLLSAIN|PLLSAIN|Reserved|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 31 Reserved, must be kept at reset value.


Bits 30:28 **PLLSAIR:** PLLSAI division factor for LCD clock

Set and reset by software to control the LCD clock frequency.

These bits should be written when the PLLSAI is disabled.

LCD clock frequency = VCO frequency / PLLSAIR with 2 ≤ PLLSAIR ≤ 7
000: PLLSAIR = 0, wrong configuration
001: PLLSAIR = 1, wrong configuration

010: PLLSAIR = 2

...

111: PLLSAIR = 7


Bits 27:24 **PLLSAIQ:** PLLSAI division factor for SAI1 clock

Set and reset by software to control the frequency of SAI1 clock.

These bits should be written when the PLLSAI is disabled.

SAI1 clock frequency = VCO frequency / PLLSAIQ with 2 ≤ PLLSAIQ ≤ 15
0000: PLLSAIQ = 0, wrong configuration
0001: PLLSAIQ = 1, wrong configuration

...

0010: PLLSAIQ = 2

0011: PLLSAIQ = 3

0100: PLLSAIQ = 4

0101: PLLSAIQ = 5

...

1111: PLLSAIQ = 15


208/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bits 23:15 Reserved, must be kept at reset value.


Bits 14:6 **PLLSAIN:** PLLSAI division factor for VCO

These bits are set and cleared by software to control the multiplication factor of the VCO.
These bits can be written only when PLLSAI is disabled. Only half-word and word accesses
are allowed to write these bits.


**Caution:** The software has to set these bits correctly to ensure that the VCO output frequency
is between 100 and 432 MHz.

VCO output frequency = VCO input frequency × PLLISAIN with 50 ≤ PLLISAIN ≤ 432
000000000: PLLISAIN = 0, wrong configuration
000000001: PLLISAIN = 1, wrong configuration

...

000110010: PLLISAIN = 50

...

001100011: PLLISAIN = 99

001100100: PLLISAIN = 100

001100101: PLLISAIN = 101

001100110: PLLISAIN = 102

...

110110000: PLLISAIN = 432

110110001: PLLISAIN = 433, wrong configuration

...

111111111: PLLISAIN = 511, wrong configuration

_Note: Multiplication factors ranging from 50 and 99 are possible for VCO input frequency_
_higher than 1 MHz. However care must be taken that the minimum VCO output_
_frequency respects the value specified above._


Bits 5:0 Reserved, must be kept at reset value


**6.3.25** **RCC Dedicated Clock Configuration Register (RCC_DCKCFGR)**


Address offset: 0x8C


Reset value: 0x0000 0000


Access: no wait state, word, half-word and byte access.


The RCC_DCKCFGR register allows to configure the timer clock prescalers and the PLLSAI
and PLLI2S output clock dividers for SAI1 and LTDC peripherals according to the following
formula:


f = f / PLLSAIDIVQ
(PLLSAIDIVQ clock output) (PLLSAI_Q)

f = f / PLLSAIDIVR
(PLLSAIDIVR clock output) (PLLSAI_R)

f( PLLI2SDIVQ clock output) = f (PLLI2S_Q) / PLLI2SDIVQ

|31 30 29 28 27 26 25|24|23 22|Col4|21 20|Col6|19 18|17 16|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|TIMPRE|SAI1BSRC|SAI1BSRC|SAI1ASRC|SAI1ASRC|Reserved|PLLSAIDIVR|PLLSAIDIVR|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13|12 11 10 9 8|Col3|Col4|Col5|Col6|7 6 5|4 3 2 1 0|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|PLLSAIDIVQ|PLLSAIDIVQ|PLLSAIDIVQ|PLLSAIDIVQ|PLLSAIDIVQ|Reserved|PLLS2DIVQ|PLLS2DIVQ|PLLS2DIVQ|PLLS2DIVQ|PLLS2DIVQ|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



RM0090 Rev 21 209/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


Bits 31:25 Reserved, must be kept at reset value.


Bit 24 **TIMPRE** : Timers clocks prescalers selection

This bit is set and reset by software to control the clock frequency of all the timers connected
to APB1 and APB2 domain.

0: If the APB prescaler (PPRE1, PPRE2 in the RCC_CFGR register) is configured to a
division factor of 1, TIMxCLK = PCLKx. Otherwise, the timer clock frequencies are set to
twice to the frequency of the APB domain to which the timers are connected:

TIMxCLK = 2xPCLKx.

1:If the APB prescaler (PPRE1, PPRE2 in the RCC_CFGR register) is configured to a
division factor of 1, 2 or 4, TIMxCLK = HCLK. Otherwise, the timer clock frequencies are set
to four times to the frequency of the APB domain to which the timers are connected:
TIMxCLK = 4xPCLKx.


Bits 23:22 **SAI1BSRC** : SAI1-B clock source selection

These bits are set and cleared by software to control the SAI1-B clock frequency.
They should be written when the PLLSAI and PLLI2S are disabled.
00: SAI1-B clock frequency = f(PLLSAI_Q) / PLLSAIDIVQ
01: SAI1-B clock frequency = f(PLLI2S_Q) / PLLI2SDIVQ
10: SAI1-B clock frequency = Alternate function input frequency
11: wrong configuration


Bits 21:20 **SAI1ASRC** : SAI1-A clock source selection

These bits are set and cleared by software to control the SAI1-A clock frequency.
They should be written when the PLLSAI and PLLI2S are disabled.
00: SAI1-A clock frequency = f(PLLSAI_Q) / PLLSAIDIVQ
01: SAI1-A clock frequency = f(PLLI2S_Q) / PLLI2SDIVQ
10: SAI1-A clock frequency = Alternate function input frequency
11: wrong configuration


Bits 19: 18 Reserved, must be kept at reset value.


Bits 17:16 **PLLSAIDIVR** : division factor for LCD_CLK

These bits are set and cleared by software to control the frequency of LCD_CLK.
They should be written only if PLLSAI is disabled.
LCD_CLK frequency = f(PLLSAI_R) / PLLSAIDIVR with 2 ≤ PLLSAIDIVR ≤ 16

00: PLLSAIDIVR = /2

01: PLLSAIDIVR = /4

10: PLLSAIDIVR = /8

11: PLLSAIDIVR = /16


Bits 15: 13 Reserved, must be kept at reset value.


210/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


Bits 12:8 **PLLSAIDIVQ** : PLLSAI division factor for SAI1 clock

These bits are set and reset by software to control the SAI1 clock frequency.
They should be written only if PLLSAI is disabled.
SAI1 clock frequency = f(PLLSAI_Q) / PLLSAIDIVQ with 1 ≤ PLLSAIDIVQ ≤ 31

00000: PLLSAIDIVQ = /1

00001: PLLSAIDIVQ = /2

00010: PLLSAIDIVQ = /3

00011: PLLSAIDIVQ = /4

00100: PLLSAIDIVQ = /5

...

11111: PLLSAIDIVQ = /32


Bits 7:5 Reserved, must be kept at reset value.


Bits 4:0 **PLLI2SDIVQ** : PLLI2S division factor for SAI1 clock

These bits are set and reset by software to control the SAI1 clock frequency.
They should be written only if PLLI2S is disabled.
SAI1 clock frequency = f(PLLI2S_Q) / PLLI2SDIVQ with 1 <= PLLI2SDIVQ <= 31

00000: PLLI2SDIVQ = /1

00001: PLLI2SDIVQ = /2

00010: PLLI2SDIVQ = /3

00011: PLLI2SDIVQ = /4

00100: PLLI2SDIVQ = /5

...

11111: PLLI2SDIVQ = /32


RM0090 Rev 21 211/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


**6.3.26** **RCC register map**


_Table 34_ gives the register map and reset values.


**Table 34. RCC register map and reset values for STM32F42xxx and STM32F43xxx**



















|Addr.<br>offset|Register<br>name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|RCC_CR<br>|Reserved|Reserved|PLL SAIRDY<br>|PLL SAION<br>|PLL I2SRDY<br>|PLL I2SON<br>|PLL RDY<br>|PLL ON<br>|Reserved|Reserved|Reserved|Reserved|CSSON<br>|HSEBYP<br>|HSERDY<br>|HSEON<br>|HSICAL 7<br>|HSICAL 6<br>|HSICAL 5<br>|HSICAL 4<br>|HSICAL 3<br>|HSICAL 2<br>|HSICAL 1<br>|HSICAL 0<br>|HSITRIM 4<br>|HSITRIM 3<br>|HSITRIM 2<br>|HSITRIM 1<br>|HSITRIM 0<br>|Reserved<br>|HSIRDY<br>|HSION<br>|
|0x00|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~1~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~1~~|~~1~~|
|0x04|RCC_<br>PLLCFGR<br>|Reserved|Reserved|Reserved|Reserved|PLLQ 3<br>|PLLQ 2<br>|PLLQ 1<br>|PLLQ 0<br>|Reserved|PLLSRC<br>|Reserved|Reserved|Reserved|Reserved|PLLP 1<br>|PLLP 0<br>|Reserved|PLLN 8<br>|PLLN 7<br>|PLLN 6<br>|PLLN 5<br>|PLLN 4<br>|PLLN 3<br>|PLLN 2<br>|PLLN 1<br>|PLLN 0<br>|PLLM 5<br>|PLLM 4<br>|PLLM 3<br>|PLLM 2<br>|PLLM 1<br>|PLLM 0<br>|
|0x04|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~1~~|~~1~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x08|RCC_CFGR<br>|MCO2 1<br>|MCO2 0<br>|MCO2PRE2<br>|MCO2PRE1<br>|MCO2PRE0<br>|MCO1PRE2<br>|MCO1PRE1<br><br>|MCO1PRE0<br>|I2SSRC<br>|MCO1 1<br>|MCO1 0<br><br>|RTCPRE 4<br>|RTCPRE 3<br>|RTCPRE 2<br>|RTCPRE 1<br>|RTCPRE 0<br>|PPRE2 2<br>|PPRE2 1<br>|PPRE2 0<br>|PPRE1 2<br><br>|PPRE1 1<br><br>|PPRE1 0<br>|Reserved|Reserved|HPRE 3<br>|HPRE 2<br>|HPRE 1<br>|HPRE 0<br>|SWS 1<br>|SWS 0<br>|SW 1<br>|SW 0<br>|
|0x08|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x0C|RCC_CIR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CSSC<br><br>|PLLSAIRDYC<br>|PLLI2SRDYC<br>|PLLRDYC<br>|HSERDYC<br>|HSIRDYC<br>|LSERDYC<br>|LSIRDYC<br>|Reserved|PLLSAIRDYIE<br>|PLLI2SRDYIE<br>|PLLRDYIE<br>|HSERDYIE<br>|HSIRDYIE<br>|LSERDYIE<br>|LSIRDYIE<br>|CSSF<br>|PLLSAIRDYF<br>|PLLI2SRDYF<br>|PLLRDYF<br>|HSERDYF<br>|HSIRDYF<br>|LSERDYF<br>|LSIRDYF<br>|
|0x0C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x10|RCC_<br>AHB1RSTR<br>|Reserved|Reserved|OTGHSRST<br>|Reserved|Reserved|Reserved|ETHMACRST<br>|Reserved|DMA2DRST<br>|DMA2RST<br>|DMA1RST<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CRCRST<br>|Reserved|GPIOKRST<br>|GPIOJRST<br>|GPIOIRST<br>|GPIOHRST<br>|GPIOGRST<br>|GPIOFRST<br>|GPIOERST<br>|GPIODRST<br>|GPIOCRST<br>|GPIOBRST<br>|GPIOARST<br>|
|0x10|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x14|RCC_<br>AHB2RSTR<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|OTGFSRS<br>|RNGRST<br>|HSAHRST<br>|CRYPRST<br>|Reserved|Reserved|Reserved|DCMIRST<br>|
|0x14|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x18<br>|RCC_<br>AHB3RSTR<br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|Reserved<br><br>|FMCRS<br>|
|0x18<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~0~~|
|~~0x1C~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|
|0x20|RCC_<br>APB1RSTR<br>|UART8RST<br>|UART7RST<br>|DACRST<br>|PWRRST<br>|Reserved|CAN2RST<br>|CAN1RST<br>|Reserved|I2C3RST<br>|I2C2RST<br>|I2C1RST<br>|UART5RST<br>|UART4RST<br>|UART3RST<br>|UART2RST<br>|Reserved|SPI3RST<br>|SPI2RST<br>|Reserved|Reserved|WWDGRST<br>|Reserved|Reserved|TIM14RST<br>|TIM13RST<br>|TIM12RST<br>|TIM7RST<br>|TIM6RST<br>|TIM5RST<br>|TIM4RST<br>|TIM3RST<br>|TIM2RST<br>|
|0x20|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x24<br>|RCC_<br>APB2RSTR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|LTDCRST<br>|Reserved<br>|Reserved<br>|Reserved<br>|SAI1RST<br>|SPI6RST<br>|SPI5RST<br>|Reserved|TIM11RST<br>|TIM10RST<br>|TIM9RST<br>|Reserved<br>|SYSCFGRST<br>|SP45RST<br>|SPI1RST<br>|SDIORST<br>|Reserved|Reserved|ADCRST<br>|Reserved|Reserved|USART6RST<br>|USART1RST<br>|Reserved|Reserved|TIM8RST<br>|TIM1RST<br>|
|0x24<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~<br>|~~0~~<br>|~~0~~<br>|~~0~~<br>|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|~~0x28~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|
|~~0x2C~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|
|0x30|RCC_<br>AHB1ENR<br>|Reserved|OTGHSULPIEN<br>|OTGHSEN<br>|ETHMACPTPEN<br>|ETHMACRXEN<br>|ETHMACTXEN<br>|ETHMACEN<br>|Reserved|DMA2DEN<br>|DMA2EN<br>|DMA1EN<br>|CCMDATARAMEN<br>|Reserved|BKPSRAMEN<br>|Reserved|Reserved|Reserved|Reserved|Reserved|CRCEN<br>|Reserved|GPIOKEN<br>|GPIOJEN<br>|GPIOIEN<br>|GPIOHEN<br>|GPIOGEN<br>|GPIOFEN<br>|GPIOEEN<br>|GPIODEN<br>|GPIOCEN<br>|GPIOBEN<br>|GPIOAEN<br>|
|0x30|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~1~~|~~1~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|


212/1757 RM0090 Rev 21


**RM0090** **Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)**


**Table 34. RCC register map and reset values for STM32F42xxx and STM32F43xxx (continued)**









|Addr.<br>offset|Register<br>name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x34|RCC_<br>AHB2ENR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|OTGFSEN<br>|RNGEN<br>|HASHEN<br>|CRYPEN<br>|Reserved|Reserved|Reserved|DCMIEN<br>|
|0x34|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x38<br>|RCC_<br>AHB3ENR<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|FMCEN<br>|
|0x38<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~0~~|
|~~0x3C~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|
|0x40|RCC_<br>APB1ENR<br>|UART8EN<br>|UART7EN<br>|DACEN<br>|PWREN<br>|Reserved|CAN2EN<br>|CAN1EN<br>|Reserved|I2C3EN<br>|I2C2EN<br>|I2C1EN<br>|UART5EN<br>|UART4EN<br>|USART3EN<br>|USART2EN<br>|Reserved|SPI3EN<br>|SPI2EN<br>|Reserved|Reserved|WWDGEN<br>|Reserved|Reserved|TIM14EN<br>|TIM13EN<br>|TIM12EN<br>|TIM7EN<br>|TIM6EN<br>|TIM5EN<br>|TIM4EN<br>|TIM3EN<br>|TIM2EN<br>|
|0x40|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x44<br>|RCC_<br>APB2ENR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|LTDCEN<br>|Reserved|Reserved|Reserved|SAI1EN<br>|SPI6EN<br>|SPI5EN<br>|Reserved|TIM11EN<br>|TIM10EN<br>|TIM9EN<br>|Reserved<br>|SYSCFGEN<br>|SPI4EN<br>|SPI1EN<br>|SDIOEN<br>|ADC3EN<br>|ADC2EN<br>|ADC1EN<br>|Reserved|Reserved|USART6EN<br>|USART1EN<br>|Reserved|Reserved|TIM8EN<br>|TIM1EN<br>|
|0x44<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~<br>|~~0~~<br>|~~0~~<br>|~~0~~<br>|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|~~0x48~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|
|~~0x4C~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|
|0x50|RCC_<br>AHB1LPENR<br>|Reserved|OTGHSULPILPEN<br>|OTGHSLPEN<br>|ETHMACPTPLPEN<br>|ETHMACRXLPEN<br>|ETHMACTXLPEN<br>|ETHMACLPEN<br>|Reserved|DMA2DLPEN<br>|DMA2LPEN<br>|DMA1LPEN<br>|Reserved|SRAM3LPEN<br>|BKPSRAMLPEN<br>|SRAM2LPEN<br>|SRAM1LPEN<br>|FLITFLPEN<br>|Reserved|Reserved|CRCLPEN<br>|Reserved|GPIOKLPEN<br>|GPIOJLPEN<br>|GPIOILPEN<br>|GPIOHLPEN<br>|GPIOGLPEN<br>|GPIOFLPEN<br>|GPIOELPEN<br>|GPIODLPEN<br>|GPIOCLPEN<br>|GPIOBLPEN<br>|GPIOALPEN<br>|
|0x50|~~Reset value~~|~~Reset value~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|
|0x54|RCC_<br>AHB2LPENR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|OTGFSLPEN<br>|RNGLPEN<br>|HASHLPEN<br>|CRYPLPEN<br>|Reserved|Reserved|Reserved|DCMILPEN<br>|
|0x54|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|
|0x58<br>|RCC_<br>AHB3LPENR<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|FMCLPEN<br>|
|0x58<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~1~~|
|~~0x5C~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|
|0x60|RCC_<br>APB1LPENR<br>|UART8LPEN<br>|UART7LPEN<br>|DACLPEN<br>|PWRLPEN<br>|Reserved|CAN2LPEN<br>|CAN1LPEN<br>|Reserved|I2C3LPEN<br>|I2C2LPEN<br>|I2C1LPEN<br>|UART5LPEN<br>|UART4LPEN<br>|USART3LPEN<br>|USART2LPEN<br>|Reserved|SPI3LPEN<br>|SPI2LPEN<br>|Reserved|Reserved|WWDGLPEN<br>|Reserved|Reserved|TIM14LPEN<br>|TIM13LPEN<br>|TIM12LPEN<br>|TIM7LPEN<br>|TIM6LPEN<br>|TIM5LPEN<br>|TIM4LPEN<br>|TIM3LPEN<br>|TIM2LPEN<br>|
|0x60|~~Reset value~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|
|0x64<br>|RCC_<br>APB2LPENR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|LTDCLPEN<br>|Reserved|Reserved|Reserved|SAI1LPEN<br>|SPI6LPEN<br>|SPI5LPEN<br>|Reserved|TIM11LPEN<br>|TIM10LPEN<br>|TIM9LPEN<br>|Reserved<br>|SYSCFGLPEN<br>|SPI4LPEN<br>|SPI1LPEN<br>|SDIOLPEN<br>|ADC3LPEN<br>|ADC2LPEN<br>|ADC1LPEN<br>|Reserved|Reserved|USART6LPEN<br>|USART1LPEN<br>|Reserved|Reserved|TIM8LPEN<br>|TIM1LPEN<br>|
|0x64<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~Reset value~~<br>|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~0~~|~~1~~|~~1~~|~~1~~|~~0~~<br>|~~1~~<br>|~~1~~<br>|~~1~~<br>|~~0~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|
|~~0x68~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|
|~~0x6C~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|
|0x70|RCC_BDCR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|BDRST<br>|RTCEN<br>|Reserved|Reserved|Reserved|Reserved|Reserved|RTCSEL 1<br>|RTCSEL 0<br>|Reserved|Reserved|Reserved|Reserved|Reserved|LSEBYP<br>|LSERDY<br>|LSEON<br>|
|0x70|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|


RM0090 Rev 21 213/1757



214


**Reset and clock control for  STM32F42xxx and STM32F43xxx (RCC)** **RM0090**


**Table 34. RCC register map and reset values for STM32F42xxx and STM32F43xxx (continued)**































|Addr.<br>offset|Register<br>name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x74<br>|RCC_CSR<br>|LPWRRSTF<br>|WWDGRSTF<br>|WDGRSTF<br>|SFTRSTF<br>|PORRSTF<br>|PADRSTF<br>|BORRSTF<br>|RMVF<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|LSIRDY<br>|LSION<br>|
|0x74<br>|~~Reset value~~<br>|~~0~~|~~0~~|~~0~~|~~0~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~0~~|~~0~~|
|~~0x78~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|
|~~0x7C~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|
|0x80|RCC_SSCGR<br>|SSCGEN<br>|SPREADSEL<br>|Reserved|Reserved|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|INCSTEP<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|MODPER<br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x80|~~Reset value~~<br>|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x84|~~RCC_~~<br>PLLI2SCFGR|Reserved|PLLI2SRx|PLLI2SRx|PLLI2SRx|PLLI2SQ|PLLI2SQ|PLLI2SQ|PLLI2SQ|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|PLLI2SNx|PLLI2SNx|PLLI2SNx|PLLI2SNx|PLLI2SNx|PLLI2SNx|PLLI2SNx|PLLI2SNx|PLLI2SNx|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x84|Reset value|Reset value|0|1|0|0|1|0|0|0|0|0|0|0|0|0|0|0|0|1|1|0|0|0|0|0|0|0|0|0|0|0|0|
|0x88|RCC_<br>PLLSAICFGR<br>|Reserved|PLLSAIR<br><br><br>|PLLSAIR<br><br><br>|PLLSAIR<br><br><br>|PLLSAIQ<br><br><br><br>|PLLSAIQ<br><br><br><br>|PLLSAIQ<br><br><br><br>|PLLSAIQ<br><br><br><br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|PLLSAIN<br><br><br><br><br><br><br><br><br>|PLLSAIN<br><br><br><br><br><br><br><br><br>|PLLSAIN<br><br><br><br><br><br><br><br><br>|PLLSAIN<br><br><br><br><br><br><br><br><br>|PLLSAIN<br><br><br><br><br><br><br><br><br>|PLLSAIN<br><br><br><br><br><br><br><br><br>|PLLSAIN<br><br><br><br><br><br><br><br><br>|PLLSAIN<br><br><br><br><br><br><br><br><br>|PLLSAIN<br><br><br><br><br><br><br><br><br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x88|~~Reset value~~|~~Reset value~~|~~0~~|~~1~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~1~~|~~1~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x8C|RCC_<br>DCKCFGR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|TIMPRE<br>|SAI1BSCR<br><br>|SAI1BSCR<br><br>|SAI1ASCR<br><br>|SAI1ASCR<br><br>|Reserved|Reserved|PLLSAIDIVR<br><br>|PLLSAIDIVR<br><br>|Reserved|Reserved|Reserved|0<br>|0<br>|0<br>|0<br>|0<br>|Reserved|Reserved|Reserved|PLLI2SDIVQ<br><br><br><br><br>|PLLI2SDIVQ<br><br><br><br><br>|PLLI2SDIVQ<br><br><br><br><br>|PLLI2SDIVQ<br><br><br><br><br>|PLLI2SDIVQ<br><br><br><br><br>|
|0x8C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|


Refer to _Section 2.3: Memory map_ for the register boundary addresses.


214/1757 RM0090 Rev 21


