**Reset and clock control (RCC)** **RM0490**

# **6 Reset and clock control (RCC)**

## **6.1 Reset**


There are three types of reset, defined as system reset, power reset and RTC domain reset.


**6.1.1** **Power reset**


A power reset is generated when one of the following events occurs:


      - power-on reset (POR) or brown-out reset (BOR)


      - exit from Standby mode


      - exit from Shutdown mode


Power and brown-out reset set all registers to their reset values.


When exiting Standby mode, all registers in the V CORE domain are set to their reset value.
Registers outside the V CORE domain (WKUP, IWDG, and Standby/Shutdown mode control)
are not impacted.


When exiting Shutdown mode, the brown-out reset is generated, resetting all registers.


**6.1.2** **System reset**


System reset sets all registers to their reset values except the reset flags in the RCC
control/status register 2 (RCC_CSR2) and the registers in the RTC domain.


System reset is generated when one of the following events occurs:


      - low level on NRST (external reset)


      - window watchdog event (WWDG reset)


      - independent watchdog event (IWDG reset)


      - software reset (SW reset) (see _Software reset_ )


      - low-power mode security reset (see _Low-power mode security reset_ )


      - option byte loader reset (see _Option byte loader reset_ )


      - power-on reset


The reset source can be identified by checking the reset flags in the RCC_CSR register
(see _Section 6.4.23: RCC control/status register 2 (RCC_CSR2)_ ).


**NRST (external reset)**


Through specific option bits, the PF2-NRST pin is configurable for operating as:


      - **Reset input/output** (default at device delivery)


Valid reset signal on the pin is propagated to the internal logic, and each internal reset
source is led to a pulse generator the output of which drives this pin. The GPIO
functionality (PF2) is not available. The pulse generator guarantees a minimum reset
pulse duration of 20 µs for each internal reset source to be output on the NRST pin. An
internal reset holder option can be used, if enabled in the _FLASH option register_
_(FLASH_OPTR)_, to ensure that the pin is pulled low until its voltage meets V IL
threshold. This function allows the detection of internal reset sources by external
components when the line faces a significant capacitive load. The BOOT0 pin is


118/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


sampled on NRST rising edge, regardless whether caused by internal or external
resets.


      - **Reset** **input**


In this mode, any valid reset signal on the NRST pin is propagated to device internal
logic, but resets generated internally by the device are not visible on the pin. The GPIO
functionality (PF2) is not available. The BOOT0 pin is sampled on POR and any
subsequent NRST rising edge, caused by external resets. Other internal resets do not
trigger new BOOT0 sampling.


      - **GPIO**


In this mode, the pin can be used as PF2 GPIO. The reset function of the pin is not
available. Reset is only possible from device internal reset sources and it is not
propagated to the pin. Refer to _Section 8.3.15: Reset pin (PF2-NRST) in GPIO mode_
for additional considerations for this mode. The BOOT0 pin is sampled on the POR
NRST rising edge only. Subsequent internal resets or transitions on the PF2 GPIO do
not trigger new BOOT0 sampling.


**Caution:** Upon power reset or wake-up from Standby or Shutdown mode, the NRST pin is configured
as Reset input/output and driven low by the system until it is reconfigured to the expected
mode when the option bytes are loaded, in the fourth clock cycle after the end of t RSTTEMPO
time (see datasheet).


**Figure 8. Simplified diagram of the reset circuit**



















**Software reset**


The SYSRESETREQ bit in Cortex [®] -M0+ Application interrupt and reset control register
must be set to force a software reset on the device (refer to the programming manual
PM0223).


RM0490 Rev 5 119/1027



165


**Reset and clock control (RCC)** **RM0490**


**Low-power mode security reset**


To prevent that critical applications mistakenly enter a low-power mode, low-power mode
security resets are available. If enabled in option bytes, the resets are generated in the
following conditions:


      - **Entering Standby mode**


This type of reset is enabled by resetting nRST_STDBY bit in user option bytes. In this
case, whenever a Standby mode entry sequence is successfully executed, the device
is reset instead of entering Standby mode.


      - **Entering Stop mode**


This type of reset is enabled by resetting nRST_STOP bit in user option bytes. In this
case, whenever a Stop mode entry sequence is successfully executed, the device is
reset instead of entering Stop mode.


      - **Entering Shutdown mode**


This type of reset is enabled by resetting nRST_SHDW bit in user option bytes. In this
case, whenever a Shutdown mode entry sequence is successfully executed, the device
is reset instead of entering Shutdown mode.


For further information on the user option bytes, refer to _Section 4.4.1: FLASH option byte_
_description_ .


**Option byte loader reset**


The option byte loader reset is generated when the OBL_LAUNCH bit is set in the
FLASH_CR register. This bit is used to launch the option byte loading by software.


**6.1.3** **RTC domain reset**


The RTC domain has two specific resets.


A RTC domain reset is generated when one of the following events occurs:


      - **Software reset**, triggered by setting the RTCRST bit of the _RCC control/status register_
_1 (RCC_CSR1)_ .


      - **V** **DD** **power on** .


RTC domain reset only affects the LSE oscillator, the RTC, and the RCC control/status
register 1.


120/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**

## **6.2 Clocks**


The device provides the following clock sources producing primary clocks:


      - **HSI48 RC**       - a high-speed fully-integrated RC oscillator producing **HSI48** clock
(48 MHz)


      - **HSIUSB48 RC**       - - a high-speed fully-integrated RC oscillator producing **HSIUSB48**
clock for USB (about 48 MHz)


      - **HSE OSC**       - a high-speed oscillator with external crystal/ceramic resonator or external
clock source, producing **HSE** clock (4 to 48 MHz)


      - **LSI RC**       - a low-speed fully-integrated RC oscillator producing **LSI** clock (about 32 kHz)


      - **LSE OSC**       - a low-speed oscillator with external crystal/ceramic resonator or external
clock source, producing **LSE** clock (accurate 32.768 kHz or external clock up to
1 MHz)


      - **I2S_CKIN**       - pin for direct clock input for I2S1 peripheral


Each oscillator can be switched on or off independently when it is not used, to optimize
power consumption. Check sub-sections of this section for more functional details. For
electrical characteristics of the internal and external clock sources, refer to the device
datasheet.


The device produces secondary clocks by dividing the primary clocks:


      - **HSISYS**       - a clock derived from HSI48 through division by a factor programmable from 1
to 128


      - **SYSCLK**       - a clock obtained through selecting one of LSE, LSI, HSE, HSIUSB48, and
HSISYS clocks


      - **HSIKER**       - a clock derived from HSI48 through division by a factor programmable from
1 to 8


      - **HCLK**       - a clock derived from SYSCLK through division by a factor programmable from
1 to 512


      - **HCLK8**       - a clock derived from HCLK through division by eight


      - **PCLK**       - a clock derived from HCLK through division by a factor programmable from 1 to
16


      - **TIMPCLK**       - a clock derived from PCLK, running at PCLK frequency if the APB
prescaler division factor is set to 1, or at twice the PCLK frequency otherwise


More secondary clocks are generated by fixed division of HSE, HSI48 and HCLK clocks.


The HSISYS is used as system clock source after startup from reset, with the division by
four (producing 12 MHz frequency).


The HCLK clock and PCLK clock are used for clocking the AHB and the APB domains,
respectively. Their maximum allowed frequency is 48 MHz.


The peripherals are clocked with the clocks from the bus they are attached to (HCLK for
AHB, PCLK for APB) except:


      - **TIMx**


–
TIMPCLK running at PCLK frequency if the APB prescaler division factor is set to
1, or at twice the PCLK frequency otherwise


RM0490 Rev 5 121/1027



165


**Reset and clock control (RCC)** **RM0490**


      - **USART1**, with these clock sources to select from:


–
SYSCLK (system clock)


– HSIKER


– LSE


–
PCLK (APB clock)


The wake-up from Stop mode is supported only when the clock is HSI48 or LSE.


      - **ADC**, with these clock sources to select from:


–
SYSCLK (system clock)


– HSIKER


      - **I2C1**, with these clock sources to select from:


–
SYSCLK (system clock)


– HSIKER


–
PCLK (APB clock)


The wake-up from Stop mode is supported only when the clock is HSI48.


      - **I2S1**, with these clock sources to select from:


–
SYSCLK (system clock)


– HSIKER


–
I2S_CKIN pin


      - **RTC**, with these clock sources to select from:


– LSE


– LSI


–
HSE clock divided by 32


The functionality in Stop mode (including wake-up) is supported only when the clock is
LSI or LSE.


      - **IWDG**, always clocked with LSI clock.


      - **USB**, with these clock sources to select from:


– HSE


– HSIUSB48


      - **FDCAN1**, with these clock sources to select from:


– PCLK


– HSIKER


– HSE

      - **SysTick** (Cortex [®] core system timer), with these clock sources to select from:


–
HCLK (AHB clock)


–
HCLK clock divided by 8


The selection is done through SysTick control and status register.


HCLK is used as Cortex [®] -M0+ free-running clock (FCLK). For more details, refer to the
programming manual PM0223.


122/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


**Figure 9. Clock tree**




































































|Col1|PCLK|
|---|---|
|||
|SYSCLK<br>HSIKER|SYSCLK<br>HSIKER|
|SYSCLK<br>HSIKER||
|SYSCLK<br>HSIKER||


























|HSIKER|Col2|Col3|HSIKER|
|---|---|---|---|
||||HSE|
|||||
||||HSIKER<br>|









1. TIMPCLK runs at PCLK frequency if the APB prescaler division factor is set to 1, or at twice the PCLK frequency otherwise.


2. Only applies to STM32C071xx.


3. Only applies to STM32C051xx, STM32C071xx, and STM32C091xx/92xx.


4. Only applies to STM32C092xx.


5. 128 for STM32C011xx and STM32C031xx, 1024 for STM32C051xx, STM32C071xx, STM32C091xx, and STM32C092xx.


**6.2.1** **HSE clock**


The high speed external clock signal (HSE) can be generated from two possible clock

sources:


      - HSE external crystal/ceramic resonator


      - HSE user external clock


RM0490 Rev 5 123/1027



165


**Reset and clock control (RCC)** **RM0490**


The resonator and the load capacitors have to be placed as close as possible to the
oscillator pins in order to minimize output distortion and startup stabilization time. The
loading capacitance values must be adjusted according to the selected oscillator.


**Figure 10. HSE/ LSE clock sources**










|Clock source|Hardware configuration|
|---|---|
|External clock|<br>OSC_OUT<br>External<br>source<br>GPIO<br>OSC_IN<br>(OSC_EN as AF)|
|Crystal/Ceramic<br>resonators|<br>OSC_IN<br>OSC_OUT<br>Load<br>capacitors<br>CL2<br>CL1|



**External crystal/ceramic resonator (HSE crystal)**


The 4 to 48 MHz external oscillator has the advantage of producing a very accurate rate on
the main clock.


The associated hardware configuration is shown in _Figure 10_ . Refer to the electrical
characteristics section of the _datasheet_ for more details.


The HSERDY flag in the _RCC clock control register (RCC_CR)_ indicates if the HSE
oscillator is stable or not. At startup, the clock is not released until this bit is set by hardware.
An interrupt can be generated if enabled in the _RCC clock interrupt enable register_
_(RCC_CIER)_ .


The HSE Crystal can be switched on and off using the HSEON bit in the _RCC clock control_
_register (RCC_CR)_ .


**External source (HSE bypass)**


In this mode, an external clock source must be provided. It can have a frequency of up to
48 MHz. This mode is selected by setting the HSEBYP and HSEON bits in the _RCC clock_
_control register (RCC_CR)_ . The external clock signal (square, sinus or triangle - refer to the
datatsheet) must drive the OSC_IN pin, on devices where OSC_IN and OSC_OUT pins are
available (see _Figure 10_ ). The OSC_OUT pin can be used as a GPIO.


124/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


The OSC_OUT pin can be used as a GPIO or it can be configured as OSC_EN alternate
function, to provide an enable signal to external clock synthesizer. The OSC_EN output is
high when the external HSE clock is required and low when the external HSE clock can be
switched off. It allows stopping the external clock source when the device enters low power
modes.


_Note:_ _For details on pin availability, refer to the pinout section in the corresponding device_
_datasheet._


To minimize the consumption, it is recommended to use the square signal.


**6.2.2** **HSI48 clock**


The HSI48 clock signal is generated from an internal 48 MHz RC oscillator.


The HSI48 RC oscillator has the advantage of providing a clock source at low cost (no
external components). It also has a faster startup time than the HSE crystal oscillator.
However, even after calibration, it is less accurate than an oscillator using a frequency
reference such as quartz crystal or ceramic resonator.


The HSISYS clock derived from HSI48 can be selected as system clock after wake-up from
Stop mode. Refer to _Section 6.3: Low-power modes_ . It can also be used as a backup clock
source (auxiliary clock) if the HSE crystal oscillator fails. Refer to _Section 6.2.7: Clock_
_security system (CSS)_ .


**Calibration**


RC oscillator frequencies can vary from one chip to another due to manufacturing process
variations. To compensate for this variation, each device is factory calibrated to 1 %
accuracy at T A =25°C.


After reset, the factory calibration value is loaded in the HSICAL[7:0] bits in the _RCC internal_
_clock source calibration register (RCC_ICSCR)_ .


Voltage or temperature variations in the application may affect the HSI48 frequency of the
RC oscillator. It can be trimmed using the HSITRIM[6:0] bits in the _RCC internal clock_
_source calibration register (RCC_ICSCR)_ .


For more details on how to measure the HSI48 frequency variation, refer to _Section 6.2.14:_
_Internal/external clock measurement with TIM14/TIM16/TIM17_ .


The HSIRDY flag in the _RCC clock control register (RCC_CR)_ indicates if the HSI48 RC is
stable or not. At startup, the HSI48 RC output clock is not released until this bit is set by
hardware.


The HSI48 RC can be switched on and off using the HSION bit in the _RCC clock control_
_register (RCC_CR)_ .


The HSI48 signal can also be used as a backup source (auxiliary clock) if the HSE crystal
oscillator fails. Refer to _Section 6.2.7: Clock security system (CSS) on page 127_ .


**6.2.3** **HSIUSB48 clock**


Available on the STM32C071xx devices only, the HSIUSB48 clock signal is generated from
an internal 48 MHz RC oscillator. It can be used as clock source for the USB peripheral or
system clock.


RM0490 Rev 5 125/1027



165


**Reset and clock control (RCC)** **RM0490**


The HSIUSB48 clock is of high-precision thanks to the clock recovery system (CRS). The
CRS uses the USB SOF signal, the LSE clock or an external signal as timing reference, to
precisely adjust the HSIUSB48 RC oscillator frequency.


The HSIUSB48 RC oscillator is disabled as soon as the system enters Stop or Standby
mode.


When the CRS is not used, the HSIUSB48 RC oscillator runs on its free-run frequency that
is subject to manufacturing process variations. The devices are factory-calibrated for about
3 % accuracy at T A = 25°C.


Refer to the CRS section for more details on how to configure and use it.


The HSIUSB48RDY flag in the RCC_CR register indicates if HSIUSB48 is stable or not. At
startup, the HSIUSB48 clock is not released until the hardware sets this flag.


The HSIUSB48 RC oscillator is enabled/disabled through the HSIUSB48ON bit of the
RCC_CR register. It is automatically enabled (by hardware setting the HSIUSB48ON bit)
when selected as clock source for the USB peripheral, as long as the USB peripheral is
enabled.


Furthermore, it is possible to output the HSIUSB48 clock through the MCO and MCO2
outputs and use it as a clock source for other application components.


**6.2.4** **LSE clock**


The LSE crystal is a 32.768 kHz crystal or ceramic resonator. It has the advantage of
providing a low-power but highly accurate clock source to the real-time clock peripheral
(RTC) for clock/calendar or other timing functions.


The LSE crystal is switched on and off using the LSEON bit of _RCC control/status register 1_
_(RCC_CSR1)_ . The crystal oscillator driving strength can be changed at runtime using the
LSEDRV bit of the _RCC control/status register 1 (RCC_CSR1)_ to obtain the best
compromise between robustness and short start-up time on one side and low-powerconsumption on the other side. The LSE drive can be decreased to the lower drive
capability (LSEDRV cleared) when the LSE is ON. However, once LSEDRV is selected, the
drive capability can not be increased if LSEON is set.


The LSERDY flag in the _RCC control/status register 1 (RCC_CSR1)_ indicates whether the
LSE crystal is stable or not. At startup, the LSE crystal output clock signal is not released
until this bit is set by hardware. An interrupt can be generated if enabled in the _RCC clock_
_recovery RC register (RCC_CRRCR)_ .


**External source (LSE bypass)**


In this mode, an external clock source must be provided. It can have a frequency of up to
1 MHz. This mode is selected by setting the LSEBYP and LSEON bits in the _RCC AHB_
_peripheral clock enable in Sleep/Stop mode register (RCC_AHBSMENR)_ . The external
clock signal (square, sinus or triangle - refer to the datasheet) has to drive the OSCX_IN pin
while the OSCX_OUT pin can be used as GPIO. See _Figure 10_ .


**6.2.5** **LSI clock**


The LSI RC acts as a low-power clock source that can be kept running in Stop and Standby
mode for the independent watchdog (IWDG) and RTC. The clock frequency is 32 kHz. For
more details, refer to the electrical characteristics section of the datasheets.


126/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


The LSI RC can be switched on and off using the LSION bit in the _RCC control/status_
_register 2 (RCC_CSR2)_ .


The LSIRDY flag in the _RCC control/status register 2 (RCC_CSR2)_ indicates if the LSI
oscillator is stable or not. At startup, the clock is not released until this bit is set by hardware.
An interrupt can be generated if enabled in the _RCC clock recovery RC register_
_(RCC_CRRCR)_ .


**6.2.6** **System clock (SYSCLK) selection**


One of the following clocks can be selected as system clock (SYSCLK):


      - LSI


      - LSE


      - HSISYS


      - HSE


      - HSIUSB48


The system clock maximum frequency is 48 MHz. Upon system reset, the HSISYS clock
derived from HSI48 oscillator is selected as system clock. When a clock source is used as a
system clock, it is not possible to stop it.


A switch from one clock source to another occurs only if the target clock source is ready
(clock stable after startup delay). If a clock source which is not yet ready is selected, the
switch occurs when the clock source becomes ready. Status bits in the _RCC clock control_
_register (RCC_CR)_ indicate which clock(s) is (are) ready and the _RCC clock configuration_
_register (RCC_CFGR)_ indicates which clock is currently used as a system clock.


**6.2.7** **Clock security system (CSS)**


Clock security system can be activated by software. In this case, the clock detector is
enabled after the HSE oscillator startup delay, and disabled when this oscillator is stopped.


If a failure is detected on the HSE clock:


      - the HSE oscillator is automatically disabled


      - a clock failure event is sent to the break input of TIM1, TIM15, TIM16, and TIM17
timers


      - CSSI (clock security system interrupt) is generated


The CSSI is linked to the Cortex [®] -M0+ NMI (non-maskable interrupt) exception vector. It
makes the software aware of a HSE clock failure to allow it to perform rescue operations.


_Note:_ _If the CSS is enabled and the HSE clock fails, the CSSI occurs and an NMI is automatically_
_generated. The NMI is executed infinitely unless the CSS interrupt pending bit is cleared. It_
_is therefore necessary that the NMI ISR clears the CSSI by setting the CSSC bit in the RCC_
_clock interrupt clear register (RCC_CICR)._


If HSE is selected directly or indirectly as system clock, and a failure of HSE clock is
detected, the system clock switches automatically to HSISYS and the HSE oscillator is
disabled.


**6.2.8** **Clock security system for LSE clock (LSECSS)**


A clock security system on LSE can be activated by setting the LSECSSON bit in _RCC_
_control/status register 1 (RCC_CSR1)_ . This bit can be cleared only by a hardware reset or


RM0490 Rev 5 127/1027



165


**Reset and clock control (RCC)** **RM0490**


RTC software reset, or after LSE clock failure detection. LSECSSON must be written after
LSE and LSI are enabled (LSEON and LSION enabled) and ready (LSERDY and LSIRDY
flags set by hardware), and after selecting the RTC clock by RTCSEL.


The LSECSS works in all modes except Standby and Shutdown. It keeps working also
under system reset (excluding power-on reset). If a failure is detected on the LSE oscillator,
the LSE clock is no longer supplied to the RTC but its registers are not impacted.


_Note:_ _If the LSECSS is enabled and the LSE clock fails, the LSECSSI occurs and an NMI is_
_automatically generated. The NMI is executed infinitely unless the LSECSS interrupt_
_pending bit is cleared. It is therefore necessary that the NMI ISR clears the LSECSSI by_
_setting the LSECSSC bit in the RCC clock interrupt clear register (RCC_CICR)._


If LSE is used as system clock, and a failure of LSE clock is detected, the system clock
switches automatically to LSI. In low-power modes, an LSE clock failure generates a wakeup. The interrupt flag must then be cleared within the RCC registers.


The software **must** then disable the LSECSSON bit, stop the defective 32 kHz oscillator (by
clearing LSEON), and change the RTC clock source (no clock, LSI or HSE, with RTCSEL),
or take any appropriate action to secure the application.


The frequency of the LSE oscillator must exceed 30 kHz to avoid false positive detections.


**6.2.9** **ADC clock**


The ADC clock (refer to the device datasheet for maximum frequency) is derived from the
system clock SYSCLK or from the kernel clock output HSIKER (see ADCSEL[1:0] bitfield of
the _RCC peripherals independent clock configuration register 1 (RCC_CCIPR)_ ). It can be
prescaled by 1, 2, 4, 6, 8, 10, 12, 16, 32, 64, 128 or 256, by configuring the PRESC[3:0]
bitfield of the ADC_CCR register. It is asynchronous to the APB clock. Alternatively, the
ADC clock can be derived from the APB clock of the ADC bus interface (synchronous
clock), divided by a programmable factor (1, 2 or 4) set through the CKMODE[1:0] bitfield of
the ADC_CFGR2 register.


**6.2.10** **RTC clock**


The RTCCLK clock source can be either the HSE/32, LSE or LSI clock. It is selected by
programming the RTCSEL[1:0] bits in the _RCC control/status register 1 (RCC_CSR1)_ . This
selection cannot be modified without resetting the RTC domain. The system must always be
configured so as to get a PCLK frequency greater then or equal to the RTCCLK frequency
for a proper operation of the RTC.


RTC does not operate if the V DD supply is powered off or if the internal voltage regulator is
powered off (removing power from the V CORE domain).


When the RTC clock is LSE or LSI, the RTC remains clocked and functional under system
reset.


**6.2.11** **Timer clock**


The timer clock TIMPCLK is derived from PCLK (used for APB) as follows:


1. If the APB prescaler is set to 1, TIMPCLK frequency is equal to PCLK frequency.


2. Otherwise, the TIMPCLK frequency is set to twice the PCLK frequency.


128/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


**6.2.12** **Watchdog clock**


If the Independent watchdog (IWDG) is started by either hardware option or software
access, the LSI oscillator is forced ON and cannot be disabled. After the LSI oscillator
temporization, the clock is provided to the IWDG.


**6.2.13** **Clock-out capability**


**MCO and MCO2**


The MCO and MCO2 pins output, independently of each other, the clock selected from:


      - LSI


      - LSE


      - SYSCLK


      - HSI48


      - HSE


      - HSIUSB48


The multiplexers for MCO and MCO2, respectively, are controlled by the MCOSEL[3:0] and
MCO2SEL[3:0] bitfields of the _RCC clock configuration register (RCC_CFGR)_ . Their outputs
are further divided by a factor set through the MCOPRE[3:0] and MCO2PRE[3:0] bitfields of
the _RCC clock configuration register (RCC_CFGR)_ .


**LSCO**


The LSCO pin allows outputting on of low-speed clocks:


      - LSI


      - LSE


The selection is controlled by the LSCOSEL bit and enabled with the LSCOEN bit of the
_RCC control/status register 1 (RCC_CSR1)_ . The configuration registers of the
corresponding GPIO port must be programmed in alternate function mode.


This function remains available in Stop mode.


**6.2.14** **Internal/external clock measurement with TIM14/TIM16/TIM17**


It is possible to indirectly measure the frequency of all on-board clock sources with the
TIM14, TIM16 and TIM17 channel 1 input capture, as represented in _Figure 11_, _Figure 12_
and _Figure 13_ .


**TIM14**


By setting the TI1SEL[3:0] field of the TIM14_TISEL register, the clock selected for the input
capture channel1 of TIM14 can be one of:


      - GPIO (refer to the alternate function mapping in the device datasheets)


      - RTC clock (RTCCLK)


      - HSE clock divided by 32


      - MCO (MCU clock output)


      - MCO2 (MCU clock output)


RM0490 Rev 5 129/1027



165


**Reset and clock control (RCC)** **RM0490**


MCO and MCO2 are controlled by the MCOSEL[3:0] and MCO2SEL[3:0] bitfields,
respectively, of the clock configuration register (RCC_CFGR). All clock sources can be
selected for the MCO and MCO2 pins.


**Figure 11. Frequency measurement with TIM14 in capture mode**















**TIM16**


By setting the TI1SEL[3:0] field of the TIM16_TISEL register, the clock selected for the input
capture channel1 of TIM16 can be one of:


- GPIO (refer to the alternate function mapping in the device datasheets).


- LSI clock


- LSE clock


- MCO2


MCO2 is controlled by the MCO2SEL[3:0] bitfield of the clock configuration register


(RCC_CFGR). All clock sources can be selected for the MCO2 pin.


**Figure 12. Frequency measurement with TIM16 in capture mode**





130/1027 RM0490 Rev 5






**RM0490** **Reset and clock control (RCC)**


**TIM17**


By setting the TI1SEL[3:0] field of the TIM17_TISEL register, the clock selected for the input
capture channel1 of TIM17 can be one of:


      - GPIO Refer to the alternate function mapping in the device datasheets.


      - HSIUSB48 / 256 (only available on STM32C071xx device)


      - HSE clock divided by 32


      - MCO (MCU clock output)


      - MCO2 (MCU clock output)


MCO and MCO2 are controlled by the MCOSEL[3:0] and MCO2SEL[3:0] bitfields,
respectively, of the clock configuration register (RCC_CFGR). All clock sources can be
selected for the MCO and MCO2 pins.


**Figure 13. Frequency measurement with TIM17 in capture mode**





**Calibration of the HSI48 oscillator**







For TIM14, TIM16, and TIM17, the primary purpose of connecting the LSE to the channel 1
input capture is to precisely measure HSISYS (derived from HSI48) selected as system
clock. Counting HSISYS clock pulses between consecutive edges of the LSE clock (the
time reference) allows measuring the HSISYS (and HSI48) clock period. Such
measurement can determine the HSI48 oscillator frequency with nearly the same accuracy
as the accuracy of the 32.768 kHz quartz crystal used with the LSE oscillator (typically a few
tens of ppm). The HSI48 oscillator can then be trimmed to compensate for deviations from
target frequency, due to manufacturing, process, temperature and/or voltage variation.


The HSI48 oscillator has dedicated user-accessible calibration bits for this purpose.


The basic concept consists in providing a relative measurement (for example, the
HSISYS/LSE ratio): the measurement accuracy is therefore closely related to the ratio
between the two clock sources. Increasing the ratio allows improving the measurement

accuracy.


Generated by the HSE oscillator, the HSE clock (divided by 32) used as time reference is
the second best method for reaching a good HSI48 frequency measurement accuracy. It is
recommended in absence of the LSE clock.


RM0490 Rev 5 131/1027



165


**Reset and clock control (RCC)** **RM0490**


In order to further improve the precision of the HSI48 oscillator calibration, it is advised to
employ one or a combination of the following measures to increase the frequency
measurement accuracy:


      - set the HSISYS divider to 1 for HSISYS frequency to be equal to HSI48 frequency


      - average the results of multiple consecutive measurements


      - use the input capture prescaler of the timer (one capture every up to eight periods)


**Measurement of the LSI oscillator frequency**


The measurement of the LSI oscillator frequency uses the same principle as that for
calibrating the HSI48 oscillator. TIM16 channel1 input capture must be used for LSI clock,
and HSE selected as system clock source. The number of HSE clock pulses between
consecutive edges of the LSI signal, counted by TIM16, is then representative of the LSI
clock period.


**6.2.15** **Peripheral clock enable registers**


The clock to each peripheral can individually be enabled by the corresponding enable bit of
the RCC_AHBENR register or one of the RCC_APBENRx registers. The clocks to I/O ports
can individually be enabled through the RCC_IOPENR register.


When the clock to a peripheral or I/O port is not active, the read and write accesses to its
registers are not effective.


**Caution:** The enable bits have a synchronization mechanism to create a glitch-free clock for the the
corresponding peripheral or I/O port. After an enable bit is set, there is a 2-clock-cycle delay
before the clock becomes active, which the software must take into account.

## **6.3 Low-power modes**


      - AHB and APB peripheral clocks, including DMA clock, can be disabled by software.


      - Sleep mode stops the CPU clock. The memory interface clocks (flash memory and
SRAM interfaces) can be stopped by software during sleep mode. The AHB to APB
bridge clocks are disabled by hardware during Sleep mode when all the clocks of the
peripherals connected to them are disabled.


      - Stop mode stops all the clocks in the V CORE domain and disable the HSI48,
HSIUSB48, and HSE oscillators.


The USART1 and I2C1 peripherals can enable the HSI48 oscillator even when the
MCU is in Stop mode (if HSI48 is selected as clock source for one of those
peripherals).


The USART1 peripheral can also operate with the clock from the LSE oscillator when
the system is in Stop mode, if LSE is selected as clock source for that peripheral and
the LSE oscillator is enabled (LSEON set). In that case, the LSE oscillator remains
active when the device enters Stop mode (these peripherals do not have the capability
to turn on the LSE oscillator).


      - Standby and Shutdown modes stop all clocks in the V CORE domain and disable the
HSI48, HSIUSB48, and HSE oscillators.


The CPU deepsleep mode can be overridden for debugging, by setting the DBG_STOP or
DBG_STANDBY bits in the DBGMCU_CR register.


When leaving the Stop mode, HSISYS becomes automatically the system clock.


132/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


When leaving the Standby and Shutdown modes, HSISYS (with frequency equal to
HSI48/4) becomes automatically the system clock. At wake-up from Standby and Shutdown
mode, the user trim is lost.


If a flash memory programming operation is ongoing, Stop, Standby, and Shutdown entry is
delayed until the flash memory interface access is finished. If an access to the APB domain
is ongoing, the Stop, Standby, and Shutdown entry is delayed until the APB access is
finished.

## **6.4 RCC registers**


Unless otherwise specified, the RCC registers support word, half-word, and byte access,
without any wait state.


**6.4.1** **RCC clock control register (RCC_CR)**


Address offset: 0x00


Power-on reset value: 0x0000 1540


Other types of reset: same as power-on reset, except the HSEBYP bit that keeps its
previous value.


This register only supports word and half-word access.






|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|HSIUSB48RDY|HSIUSB48ON|Res.|Res.|CSS<br>ON|HSE<br>BYP|HSE<br>RDY|HSE<br>ON|
|||||||||rw|rw|||rs|rw|r|rw|



|15|14|13 12 11|Col4|Col5|10|9|8|7 6 5|Col10|Col11|4 3 2|Col13|Col14|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|HSIDIV[2:0]|HSIDIV[2:0]|HSIDIV[2:0]|HSI<br>RDY|HSI<br>KERON|HSION|HSIKERDIV[2:0]|HSIKERDIV[2:0]|HSIKERDIV[2:0]|SYSDIV[2:0]|SYSDIV[2:0]|SYSDIV[2:0]|Res.|Res.|
|||rw|rw|rw|r|rw|rw|rw|rw|rw|rw|rw|rw|||


Bits 31:24 Reserved, must be kept at reset value.


Bit 23 **HSIUSB48RDY** : HSIUSB48 clock ready flag

Set by hardware when the HSIUSB48 oscillator is enabled through HSIUSB48ON and ready
to use (stable).
0: Not ready
1: Ready

_Note: Only applicable to STM32C071xx, reserved on the other products._


Bit 22 **HSIUSB48ON** : HSIUSB48 clock enable

Set and cleared by software and hardware, with hardware taking priority. Kept low by
hardware as long as the device is in a low-power mode. Kept high by hardware as long as
the system is clocked from HSIUSB48.

0: Disable

1: Enable

_Note: Only applicable to STM32C071xx, reserved on the other products._


Bits 21:20 Reserved, must be kept at reset value.


RM0490 Rev 5 133/1027



165


**Reset and clock control (RCC)** **RM0490**


Bit 19 **CSSON** : Clock security system enable

Set by software to enable the clock security system. When the bit is set, the clock detector is
enabled by hardware when the HSE oscillator is ready, and disabled by hardware if a HSE
clock failure is detected. The bit is cleared by hardware upon reset.

0: Disable

1: Enable


Bit 18 **HSEBYP** : HSE crystal oscillator bypass

Set and cleared by software.
When the bit is set, the internal HSE oscillator is bypassed for use of an external clock. The
external clock must then be enabled with the HSEON bit set. Write access to the bit is only
effective when the HSE oscillator is disabled.

0: No bypass
1: Bypass


Bit 17 **HSERDY** : HSE clock ready flag

Set by hardware to indicate that the HSE oscillator is stable and ready for use.
0: Not ready
1: Ready

_Note: Upon clearing HSEON, HSERDY goes low after six HSE clock cycles._


Bit 16 **HSEON** : HSE clock enable

Set and cleared by software.
Cleared by hardware to stop the HSE oscillator when entering Stop, or Standby, or Shutdown
mode. This bit cannot be cleared if the HSE oscillator is used directly or indirectly as the
system clock.

0: Disable

1: Enable


Bits 15:14 Reserved, must be kept at reset value.


Bits 13:11 **HSIDIV[2:0]** : HSI48 clock division factor

This bitfield controlled by software sets the division factor of the HSI48 clock divider to
produce HSISYS clock:

000: 1

001: 2

010: 4 (reset value)

011: 8

100: 16

101: 32

110: 64

111: 128


Bit 10 **HSIRDY** : HSI48 clock ready flag

Set by hardware when the HSI48 oscillator is enabled through HSION and ready to use
(stable).
0: Not ready
1: Ready

_Note: Upon clearing HSION, HSIRDY goes low after six HSI48 clock cycles._


134/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


Bit 9 **HSIKERON** : HSI48 always-enable for peripheral kernels.

Set and cleared by software.
Setting the bit activates the HSI48 oscillator in Run and Stop modes, regardless of the
HSION bit state. The HSI48 clock can only feed USART1, USART2, and I2C1 peripherals
configured with HSI48 as kernel clock.
0: HSI48 oscillator enable depends on the HSION bit
1: HSI48 oscillator is active in Run and Stop modes

_Note: Keeping the HSI48 active in Stop mode allows speeding up the serial interface_
_communication as the HSI48 clock is ready immediately upon exiting Stop mode._


Bit 8 **HSION** : HSI48 clock enable

Set and cleared by software and hardware, with hardware taking priority.
Kept low by hardware as long as the device is in a low-power mode.
Kept high by hardware as long as the system is clocked with a clock derived from HSI48.
This includes the exit from low-power modes and the system clock fall-back to HSI48 upon
failing HSE oscillator clock selected as system clock source.

0: Disable

1: Enable


Bits 7:5 **HSIKERDIV[2:0]** : HSI48 kernel clock division factor

This bitfield controlled by software sets the division factor of the kernel clock divider to
produce HSIKER clock:

000: 1

001: 2

010: 3 (reset value)

011: 4

100: 5

101: 6

110: 7

111: 8


Bits 4:2 **SYSDIV[2:0]** : Clock division factor for system clock
S et and cleared by software. SYSCLK is result of the division by:

000: 1 (no division, reset value)

001: 2

010: 3

011: 4

100: 5

101: 6

110: 7

111: 8

_Note: This bitfield is only available on STM32C051xx, STM32C071xx, and_
_STM32C091xx/92xx._


Bits 1:0 Reserved, must be kept at reset value.


**6.4.2** **RCC internal clock source calibration register (RCC_ICSCR)**


Address offset: 0x04


Reset value: 0x0000 40XX


The X nibbles of the reset can vary from part to part as they depend on the part calibration in
the factory.


RM0490 Rev 5 135/1027



165


**Reset and clock control (RCC)** **RM0490**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14 13 12 11 10 9 8|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|HSITRIM[6:0]|HSITRIM[6:0]|HSITRIM[6:0]|HSITRIM[6:0]|HSITRIM[6:0]|HSITRIM[6:0]|HSITRIM[6:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|
||rw|rw|rw|rw|rw|rw|rw|r|r|r|r|r|r|r|r|



Bits 31:15 Reserved, must be kept at reset value.


Bits 14:8 **HSITRIM[6:0]** : HSI48 clock trimming

The value of this bitfield contributes to the HSICAL[7:0] bitfield value.
It allows HSI48 clock frequency user trimming.
The HSI48 frequency accuracy as stated in the device datasheet applies when this bitfield is
left at its reset value.


Bits 7:0 **HSICAL[7:0]** : HSI48 clock calibration

This bitfield directly acts on the HSI48 clock frequency. Its value is a sum of an internal
factory-programmed number and the value of the HSITRIM[6:0] bitfield. In the factory, the
internal number is set to calibrate the HSI48 clock frequency to 48 MHz (with HSITRIM[6:0]
left at its reset value). Refer to the device datasheet for HSI48 calibration accuracy and for
the frequency trimming granularity.

_Note: The trimming effect presents discontinuities at HSICAL[7:0] multiples of 64._


**6.4.3** **RCC clock configuration register (RCC_CFGR)**


One or two wait states are inserted when accessing this register upon a clock source switch,
and between zero and 15 wait states upon updating APB or AHB prescaler values.


Address offset: 0x08


Reset value: 0x0000 0000

|31 30 29 28|Col2|Col3|Col4|27 26 25 24|Col6|Col7|Col8|23 22 21 20|Col10|Col11|Col12|19 18 17 16|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MCOPRE[3:0]|MCOPRE[3:0]|MCOPRE[3:0]|MCOPRE[3:0]|MCOSEL[3:0]|MCOSEL[3:0]|MCOSEL[3:0]|MCOSEL[3:0]|MCO2PRE[3:0]|MCO2PRE[3:0]|MCO2PRE[3:0]|MCO2PRE[3:0]|MCO2SEL[3:0]|MCO2SEL[3:0]|MCO2SEL[3:0]|MCO2SEL[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14 13 12|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7|6|5 4 3|Col12|Col13|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|PPRE[2:0]|PPRE[2:0]|PPRE[2:0]|HPRE[3:0]|HPRE[3:0]|HPRE[3:0]|HPRE[3:0]|Res.|Res.|SWS[2:0]|SWS[2:0]|SWS[2:0]|SW[2:0]|SW[2:0]|SW[2:0]|
||rw|rw|rw|rw|rw|rw|rw|||r|r|r|rw|rw|rw|



136/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


Bits 31:28 **MCOPRE[3:0]** : Microcontroller clock output prescaler

This bitfield is controlled by software. It sets the division factor of the clock sent to the MCO
output as follows:

0000: 1

0001: 2

0010: 4

...

0111: 128

1000: 256

1001: 512

1010: 1024

Other: Reserved

It is highly recommended to set this field before the MCO output is enabled.

_Note: Values above 0111 are only significant for STM32C051xx, STM32C071xx, and_
_STM32C091xx/92xx. On STM32C011xx and STM32C031xx devices, MCOPRE[3] is_
_reserved._


Bits 27:24 **MCOSEL[3:0]** : Microcontroller clock output clock selector

This bitfield is controlled by software. It sets the clock selector for MCO output as follows:

0000: no clock

0001: SYSCLK

0010: Reserved

0011: HSI48

0100: HSE

0101: Reserved

0110: LSI

0111: LSE

1000: HSIUSB48

Other: reserved, must not be used

_Note: This clock output may have some truncated cycles at startup or during MCO clock_
_source switching. On STM32C011xx, STM32C031xx, STM32C051xx, and_
_STM32C091xx/92xx, MCOSEL[3] is reserved._


Bits 23:20 **MCO2PRE[3:0]** : Microcontroller clock output 2 prescaler

This bitfield is controlled by software. It sets the division factor of the clock sent to the MCO2
output as follows:

0000: 1

0001: 2

0010: 4

...

0111: 128

1000: 256

1001: 512

1010: 1024

Other: Reserved

It is highly recommended to set this field before the MCO2 output is enabled.

_Note: Values above 0111 are only significant for STM32C051xx, STM32C071xx, and_
_STM32C091xx/92xx. On STM32C011xx and STM32C031xx devices, MCO2PRE[3] is_
_reserved._


RM0490 Rev 5 137/1027



165


**Reset and clock control (RCC)** **RM0490**


Bits 19:16 **MCO2SEL[3:0]** : Microcontroller clock output 2 clock selector

This bitfield is controlled by software. It sets the clock selector for MCO2 output as follows:

0000: no clock

0001: SYSCLK

0010: Reserved

0011: HSI48

0100: HSE

0101: Reserved

0110: LSI

0111: LSE

1000: HSIUSB48

Other: reserved, must not be used

_Note: This clock output may have some truncated cycles at startup or during MCO2 clock_
_source switching. On STM32C011xx, STM32C031xx, STM32C051xx, and_
_STM32C091xx/92xx, MCO2SEL[3] is reserved._


Bit 15 Reserved, must be kept at reset value.


Bits 14:12 **PPRE[2:0]** : APB prescaler

This bitfield is controlled by software. To produce PCLK clock, it sets the division factor of
HCLK clock as follows:

0xx: 1

100: 2

101: 4

110: 8

111: 16


Bits 11:8 **HPRE[3:0]** : AHB prescaler

This bitfield is controlled by software. To produce HCLK clock, it sets the division factor of
SYSCLK clock as follows:

0xxx: 1

1000: 2

1001: 4

1010: 8

1011: 16

1100: 64

1101: 128

1110: 256

1111: 512


Bits 7:6 Reserved, must be kept at reset value.


138/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


Bits 5:3 **SWS[2:0]** : System clock switch status

This bitfield is controlled by hardware to indicate the clock source used as system clock:

000: HSISYS

001: HSE

010: HSIUSB48 on STM32C071xx, reserved on the other products

011: LSI

100: LSE

Others: Reserved


Bits 2:0 **SW[2:0]** : System clock switch

This bitfield is controlled by software and hardware. The bitfield selects the clock for
SYSCLK as follows:

000: HSISYS

001: HSE

010: HSIUSB48 on STM32C071xx, reserved on the other products

011: LSI

100: LSE

Others: Reserved

The setting is forced by hardware to 000 (HSISYS selected) when the MCU exits Stop, or
Standby, or Shutdown mode, or when the setting is 001 (HSE selected) and HSE oscillator
failure is detected.


**6.4.4** **RCC clock recovery RC register (RCC_CRRCR)**


This register is only available on STM32C071xx. On the other devices, it is reserved.


Address offset: 0x14


Reset value: 0b0000 0000 0000 0000 0000 000X XXXX XXXX


Access: no wait state, word, half-word and byte access

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8 7 6 5 4 3 2 1 0|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|
||||||||r|r|r|r|r|r|r|r|r|



Bits 31:9 Reserved, must be kept at reset value.


Bits 8:0 **HSIUSB48CAL[8:0]** : HSIUSB48 clock calibration

These bits are initialized at startup with the factory-programmed HSIUSB48 calibration trim

value.


**6.4.5** **RCC clock interrupt enable register (RCC_CIER)**


Address offset: 0x18


Reset value: 0x0000 0000


RM0490 Rev 5 139/1027



165


**Reset and clock control (RCC)** **RM0490**


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||









|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|HSE<br>RDYIE|HSI<br>RDYIE|HSI<br>USB48<br>RDYIE|LSE<br>RDYIE|LSI<br>RDYIE|
||||||||||||rw|rw|rw|rw|rw|


Bits 31:5 Reserved, must be kept at reset value.


Bit 4 **HSERDYIE** : HSE ready interrupt enable

Set and cleared by software to enable/disable interrupt caused by the HSE oscillator
stabilization:

0: Disable

1: Enable


Bit 3 **HSIRDYIE** : HSI48 ready interrupt enable

Set and cleared by software to enable/disable interrupt caused by the HSI48 oscillator
stabilization:

0: Disable

1: Enable


Bit 2 **HSIUSB48RDYIE** : HSIUSB48 ready interrupt enable

Set and cleared by software to enable/disable interrupt caused by the HSIUSB48 oscillator
stabilization:

0: Disable

1: Enable

_Note: Only applicable to STM32C071xx, reserved on the other products._


Bit 1 **LSERDYIE** : LSE ready interrupt enable

Set and cleared by software to enable/disable interrupt caused by the LSE oscillator
stabilization:

0: Disable

1: Enable


Bit 0 **LSIRDYIE** : LSI ready interrupt enable

Set and cleared by software to enable/disable interrupt caused by the LSI oscillator
stabilization:

0: Disable

1: Enable


**6.4.6** **RCC clock interrupt flag register (RCC_CIFR)**


Address offset: 0x1C


Reset value: 0x0000 0000


140/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||









|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|LSE<br>CSSF|CSSF|Res.|Res.|Res.|HSE<br>RDYF|HSI<br>RDYF|HSI<br>USB48<br>RDYF|LSE<br>RDYF|LSI<br>RDYF|
|||||||r|r||||r|r|r|r|r|


Bits 31:10 Reserved, must be kept at reset value.


Bit 9 **LSECSSF** : LSE clock security system interrupt flag

This flag indicates a pending interrupt upon LSE clock failure.
Set by hardware when a failure is detected in the LSE oscillator.
Cleared by software by setting the LSECSSC bit.
0: Interrupt not pending
1: Interrupt pending


Bit 8 **CSSF** : HSE clock security system interrupt flag

This flag indicates a pending interrupt upon HSE clock failure.
Set by hardware when a failure is detected in the HSE oscillator.
Cleared by software setting the CSSC bit.
0: Interrupt not pending
1: Interrupt pending


Bits 7:5 Reserved, must be kept at reset value.


Bit 4 **HSERDYF** : HSE ready interrupt flag

This flag indicates a pending interrupt upon HSE clock getting ready.
Set by hardware when the HSE clock becomes stable and HSERDYIE is set.
Cleared by software setting the HSERDYC bit.
0: Interrupt not pending
1: Interrupt pending


Bit 3 **HSIRDYF** : HSI48 ready interrupt flag

This flag indicates a pending interrupt upon HSI48 clock getting ready.
Set by hardware when the HSI48 clock becomes stable and HSIRDYIE is set in response to
setting the HSION (refer to _RCC clock control register (RCC_CR)_ ). When HSION is not
set but the HSI48 oscillator is enabled by the peripheral through a clock request, this bit is
not set and no interrupt is generated.
Cleared by software setting the HSIRDYC bit.
0: Interrupt not pending
1: Interrupt pending


RM0490 Rev 5 141/1027



165


**Reset and clock control (RCC)** **RM0490**


Bit 2 **HSIUSB48RDYF** : HSIUSB48 ready interrupt flag

Set by hardware when the HSIUSB48 clock becomes stable and HSIUSB48RDYIE is set as
a response to setting HSIUSB48ON (refer to _RCC clock control register (RCC_CR)_ ).
When HSIUSB48ON is not set but the HSIUSB48 oscillator is enabled by the peripheral
through a clock request, this bit is not set and no interrupt is generated.
Cleared by software setting the HSIUSB48RDYC bit.
0: Interrupt not pending
1: Interrupt pending

_Note: Only applicable to STM32C071xx, reserved on the other products._


Bit 1 **LSERDYF** : LSE ready interrupt flag

This flag indicates a pending interrupt upon LSE clock getting ready.
Set by hardware when the LSE clock becomes stable and LSERDYIE is set.
Cleared by software setting the LSERDYC bit.
0: Interrupt not pending
1: Interrupt pending


Bit 0 **LSIRDYF** : LSI ready interrupt flag

This flag indicates a pending interrupt upon LSI clock getting ready.
Set by hardware when the LSI clock becomes stable and LSIRDYIE is set.
Cleared by software setting the LSIRDYC bit.
0: Interrupt not pending
1: Interrupt pending


**6.4.7** **RCC clock interrupt clear register (RCC_CICR)**


Address offset: 0x20


Reset value: 0x0000 0000


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||









|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|LSE<br>CSSC|CSSC|Res.|Res.|Res.|HSE<br>RDYC|HSI<br>RDYC|HSI<br>USB48<br>RDYC|LSE<br>RDYC|LSI<br>RDYC|
|||||||w|w||||w|w|w|w|w|


RCC


Bits 31:10 Reserved, must be kept at reset value.


Bit 9 **LSECSSC** : LSE Clock security system interrupt clear

This bit is set by software to clear the LSECSSF flag.

0: No effect

1: Clear LSECSSF flag


Bit 8 **CSSC** : Clock security system interrupt clear

This bit is set by software to clear the HSECSSF flag.

0: No effect

1: Clear CSSF flag


Bits 7:5 Reserved, must be kept at reset value.


142/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


Bit 4 **HSERDYC** : HSE ready interrupt clear

This bit is set by software to clear the HSERDYF flag.

0: No effect

1: Clear HSERDYF flag


Bit 3 **HSIRDYC** : HSI48 ready interrupt clear

This bit is set software to clear the HSIRDYF flag.

0: No effect

1: Clear HSIRDYF flag


Bit 2 **HSIUSB48RDYC** : HSIUSB48 ready interrupt clear

This bit is set software to clear the HSIUSB48RDYF flag.

0: No effect

1: Clear HSIUSB48RDYF flag

_Note: Only applicable to STM32C071xx, reserved on the other products._


Bit 1 **LSERDYC** : LSE ready interrupt clear

This bit is set by software to clear the LSERDYF flag.

0: No effect

1: Clear LSERDYF flag


Bit 0 **LSIRDYC** : LSI ready interrupt clear

This bit is set by software to clear the LSIRDYF flag.

0: No effect

1: Clear LSIRDYF flag


**6.4.8** **RCC I/O port reset register (RCC_IOPRSTR)**


Address offset: 0x24


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GPIOF<br>RST|Res.|GPIOD<br>RST|GPIOC<br>RST|GPIOB<br>RST|GPIOA<br>RST|
|||||||||||rw||rw|rw|rw|rw|



Bits 31:6 Reserved, must be kept at reset value.


Bit 5 **GPIOFRST:** I/O port F reset

This bit is set and cleared by software.

0: no effect

1: Reset I/O port F


Bit 4 Reserved, must be kept at reset value.


Bit 3 **GPIODRST:** I/O port D reset

This bit is set and cleared by software.

0: no effect

1: Reset I/O port D


RM0490 Rev 5 143/1027



165


**Reset and clock control (RCC)** **RM0490**


Bit 2 **GPIOCRST:** I/O port C reset

This bit is set and cleared by software.

0: no effect

1: Reset I/O port C


Bit 1 **GPIOBRST:** I/O port B reset

This bit is set and cleared by software.

0: no effect

1: Reset I/O port B


Bit 0 **GPIOARST:** I/O port A reset

This bit is set and cleared by software.

0: no effect

1: Reset I/O port A


**6.4.9** **RCC AHB peripheral reset register (RCC_AHBRSTR)**


Address offset: 0x28


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|CRC<br>RST|Res.|Res.|Res.|FLASH<br>RST|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1<br>RST|
||||rw||||rw||||||||rw|



Bits 31:13 Reserved, must be kept at reset value.


Bit 12 **CRCRST** : CRC reset

Set and cleared by software.

0: No effect

1: Reset CRC


Bits 11:9 Reserved, must be kept at reset value.


Bit 8 **FLASHRST** : Flash memory interface reset

Set and cleared by software.

0: No effect

1: Reset flash memory interface
This bit can only be set when the flash memory is in power down mode.


Bits 7:1 Reserved, must be kept at reset value.


Bit 0 **DMA1RST** : DMA1 and DMAMUX reset

Set and cleared by software.

0: No effect

1: Reset DMA1 and DMAMUX


**6.4.10** **RCC APB peripheral reset register 1 (RCC_APBRSTR1)**


Address offset: 0x2C


Reset value: 0x0000 0000


144/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|PWR<br>RST|DBG<br>RST|Res.|Res.|Res.|Res.|I2C2<br>RST|I2C1<br>RST|Res.|USART4<br>RST|USART3<br>RST|USART2<br>RST|CRS<br>RST|
||||rw|rw|||||rw|rw||rw|rw|rw|rw|









|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|SPI2<br>RST|USB<br>RST|FD<br>CAN1<br>RST|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM3<br>RST|TIM2<br>RST|
||rw|rw|rw|||||||||||rw|rw|


Bits 31:29 Reserved, must be kept at reset value.


Bit 28 **PWRRST** : Power interface reset

Set and cleared by software.

0: No effect

1: Reset PWR


Bit 27 **DBGRST** : Debug support reset

Set and cleared by software.

0: No effect

1: Reset DBG


Bits 26:23 Reserved, must be kept at reset value.


Bit 22 **I2C2RST** : I2C2 reset

Set and cleared by software.

0: No effect

1: Reset I2C2

_Note: Only applicable to STM32C051xx, STM32C071xx, and STM32C091xx/92xx, reserved_
_on the other products._


Bit 21 **I2C1RST** : I2C1 reset

Set and cleared by software.

0: No effect

1: Reset I2C1


Bit 20 Reserved, must be kept at reset value.


Bit 19 **USART4RST** : USART4 reset

Set and cleared by software.

0: No effect

1: Reset USART4

_Note: Only applicable to STM32C091xx/92xx, reserved on the other products._


Bit 18 **USART3RST** : USART3 reset

Set and cleared by software.

0: No effect

1: Reset USART3

_Note: Only applicable to STM32C091xx/92xx, reserved on the other products._


Bit 17 **USART2RST** : USART2 reset

Set and cleared by software.

0: No effect

1: Reset USART2


RM0490 Rev 5 145/1027



165


**Reset and clock control (RCC)** **RM0490**


Bit 16 **CRSRST** : CRS reset

Set and cleared by software.

0: No effect

1: Reset CRS

_Note: Only applicable to STM32C071xx, reserved on the other products._


Bit 15 Reserved, must be kept at reset value.


Bit 14 **SPI2RST** : SPI2 reset

Set and cleared by software.

0: No effect

1: Reset SPI2

_Note: Only applicable to STM32C051xx, STM32C071xx, and STM32C091xx/92xx, reserved_
_on the other products._


Bit 13 **USBRST** : USB reset

Set and cleared by software.

0: No effect

1: Reset USB

_Note: Only applicable to STM32C071xx, reserved on the other products._


Bit 12 **FDCAN1RST** : FDCAN1 reset

Set and cleared by software.

0: No effect

1: Reset FDCAN1

_Note: Only applicable to STM32C092xx, reserved on the other products._


Bits 11:2 Reserved, must be kept at reset value.


Bit 1 **TIM3RST** : TIM3 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM3


Bit 0 **TIM2RST** : TIM2 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM2

_Note: Only applicable to STM32C051xx, STM32C071xx, and STM32C091xx/92xx, reserved_
_on the other products._


**6.4.11** **RCC APB peripheral reset register 2 (RCC_APBRSTR2)**


Address offset: 0x30


Reset value: 0x0000 0000


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADC<br>RST|Res.|TIM17<br>RST|TIM16<br>RST|TIM15<br>RST|
||||||||||||rw||rw|rw|rw|







|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TIM14<br>RST|USART1<br>RST|Res.|SPI1<br>RST|TIM1<br>RST|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SYS<br>CFG<br>RST|
|rw|rw||rw|rw|||||||||||rw|


146/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


Bits 31:21 Reserved, must be kept at reset value.


Bit 20 **ADCRST** : ADC reset

Set and cleared by software.

0: No effect

1: Reset ADC


Bit 19 Reserved, must be kept at reset value.


Bit 18 **TIM17RST** : TIM16 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM17 timer


Bit 17 **TIM16RST** : TIM16 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM16 timer


Bit 16 **TIM15RST** : TIM15 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM15 timer

_Note: Only applicable to STM32C092xx, reserved on the other products._


Bit 15 **TIM14RST** : TIM14 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM14 timer


Bit 14 **USART1RST** : USART1 reset

Set and cleared by software.

0: No effect

1: Reset USART1


Bit 13 Reserved, must be kept at reset value.


Bit 12 **SPI1RST** : SPI1 reset

Set and cleared by software.

0: No effect

1: Reset SPI1


Bit 11 **TIM1RST** : TIM1 timer reset

Set and cleared by software.

0: No effect

1: Reset TIM1 timer


Bits 10:1 Reserved, must be kept at reset value.


Bit 0 **SYSCFGRST** : SYSCFG reset

Set and cleared by software.

0: No effect

1: Reset SYSCFG


**6.4.12** **RCC I/O port clock enable register (RCC_IOPENR)**


Address offset: 0x34


RM0490 Rev 5 147/1027



165


**Reset and clock control (RCC)** **RM0490**


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GPIOF<br>EN|Res.|GPIOD<br>EN|GPIOC<br>EN|GPIOB<br>EN|GPIOA<br>EN|
|||||||||||rw||rw|rw|rw|rw|



Bits 31:6 Reserved, must be kept at reset value.


Bit 5 **GPIOFEN:** I/O port F clock enable

This bit is set and cleared by software.

0: Disable

1: Enable


Bit 4 Reserved, must be kept at reset value.


Bit 3 **GPIODEN:** I/O port D clock enable

This bit is set and cleared by software.

0: Disable

1: Enable


Bit 2 **GPIOCEN:** I/O port C clock enable

This bit is set and cleared by software.

0: Disable

1: Enable


Bit 1 **GPIOBEN:** I/O port B clock enable

This bit is set and cleared by software.

0: Disable

1: Enable


Bit 0 **GPIOAEN:** I/O port A clock enable

This bit is set and cleared by software.

0: Disable

1: Enable


**6.4.13** **RCC AHB peripheral clock enable register (RCC_AHBENR)**


Address offset: 0x38


Reset value: 0x0000 0100


This register individually enables clocks to AHB peripherals. In Sleep and Stop modes, a
clock enabled through this register is only supplied to the peripheral if the corresponding bit
of the RCC_AHBSMENR register is also set.


148/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|CRC<br>EN|Res.|Res.|Res.|FLASH<br>EN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1<br>EN|
||||rw||||rw||||||||rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:13 Reserved, must be kept at reset value.


Bit 12 **CRCEN** : CRC clock enable

Set and cleared by software.

0: Disable

1: Enable


Bits 11:9 Reserved, must be kept at reset value.


Bit 8 **FLASHEN** : Flash memory interface clock enable

Set and cleared by software.

0: Disable

1: Enable

This bit can only be cleared when the flash memory is in power down mode.


Bits 7:1 Reserved, must be kept at reset value.


Bit 0 **DMA1EN** : DMA1 and DMAMUX clock enable

Set and cleared by software.

0: Disable

1: Enable

DMAMUX is enabled as long as at least one DMA peripheral is enabled.


**6.4.14** **RCC APB peripheral clock enable register 1 (RCC_APBENR1)**


Address offset: 0x3C


Reset value: 0x0000 0000


This register individually enables clocks to APB peripherals. In Sleep and Stop modes, a
clock enabled through this register is only supplied to the peripheral if the corresponding bit
of the RCC_APBSMENR1 register is also set.


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|PWR<br>EN|DBG<br>EN|Res.|Res.|Res.|Res.|I2C2<br>EN|I2C1<br>EN|Res.|USART4<br>EN|USART3<br>EN|USART2<br>EN|CRS<br>EN|
||||rw|rw|||||rw|rw||rw|rw|rw|rw|













|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|SPI2<br>EN|USB<br>EN|FD<br>CAN1<br>EN|WWDG<br>EN|RTC<br>APB<br>EN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM3<br>EN|TIM2<br>EN|
||rw|rw|rw|rw|rw|||||||||rw|rw|


RM0490 Rev 5 149/1027



165


**Reset and clock control (RCC)** **RM0490**


Bits 31:29 Reserved, must be kept at reset value.


Bit 28 **PWREN** : Power interface clock enable

Set and cleared by software.

0: Disable

1: Enable


Bit 27 **DBGEN** : Debug support clock enable

Set and cleared by software.

0: Disable

1: Enable


Bits 26:23 Reserved, must be kept at reset value.


Bit 22 **I2C2EN** : I2C2 clock enable

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C051xx, STM32C071xx, and STM32C091xx/92xx, reserved_
_on the other products._


Bit 21 **I2C1EN** : I2C1 clock enable

Set and cleared by software.

0: Disable

1: Enable


Bit 20 Reserved, must be kept at reset value.


Bit 19 **USART4EN** : USART4 clock enable

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C091xx/92xx, reserved on the other products._


Bit 18 **USART3EN** : USART3 clock enable

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C091xx/92xx, reserved on the other products._


Bit 17 **USART2EN** : USART2 clock enable

Set and cleared by software.

0: Disable

1: Enable


Bit 16 **CRSEN** : CRS clock enable

Set and cleared by software.

0: Disable

1: Enable

_Only applicable to STM32C071xx, reserved on the other products._


Bit 15 Reserved, must be kept at reset value.


150/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


Bit 14 **SPI2EN** : SPI2 clock enable

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C051xx, STM32C071xx, and STM32C091xx/92xx, reserved_
_on the other products._


Bit 13 **USBEN** : USB clock enable

Set and cleared by software.

0: Disable

1: Enable

_Only applicable to STM32C071xx, reserved on the other products._


Bit 12 **FDCAN1EN** : FDCAN1 clock enable

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C092xx, reserved on the other products._


Bit 11 **WWDGEN** : WWDG clock enable

Set by software to enable the window watchdog clock. Cleared by hardware system
reset

0: Disable

1: Enable

This bit can also be set by hardware if the WWDG_SW option bit is 0.


Bit 10 **RTCAPBEN** : RTC APB clock enable

Set and cleared by software.

0: Disable

1: Enable


Bits 9:2 Reserved, must be kept at reset value.


Bit 1 **TIM3EN** : TIM3 timer clock enable

Set and cleared by software.

0: Disable

1: Enable


Bit 0 **TIM2EN** : TIM2 timer clock enable

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C051xx, STM32C071xx, and STM32C091xx/92xx, reserved_
_on the other products._


**6.4.15** **RCC APB peripheral clock enable register 2(RCC_APBENR2)**


Address offset: 0x40


Reset value: 0x0000 0000


This register individually enables clocks to APB peripherals. In Sleep and Stop modes, a
clock enabled through this register is only supplied to the peripheral if the corresponding bit
of the RCC_APBSMENR2 register is also set.


RM0490 Rev 5 151/1027



165


**Reset and clock control (RCC)** **RM0490**


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADC<br>EN|Res.|TIM17<br>EN|TIM16<br>EN|TIM15<br>EN|
||||||||||||rw||rw|rw|rw|







|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TIM14<br>EN|USART1<br>EN|Res.|SPI1<br>EN|TIM1<br>EN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SYS<br>CFG<br>EN|
|rw|rw||rw|rw|||||||||||rw|


Bits 31:21 Reserved, must be kept at reset value.


Bit 20 **ADCEN** : ADC clock enable

Set and cleared by software.

0: Disable

1: Enable


Bit 19 Reserved, must be kept at reset value.


Bit 18 **TIM17EN** : TIM16 timer clock enable

Set and cleared by software.

0: Disable

1: Enable


Bit 17 **TIM16EN** : TIM16 timer clock enable

Set and cleared by software.

0: Disable

1: Enable


Bit 16 **TIM15EN** : TIM15 timer clock enable

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C091xx/92xx, reserved on the other products._


Bit 15 **TIM14EN** : TIM14 timer clock enable

Set and cleared by software.

0: Disable

1: Enable


Bit 14 **USART1EN** : USART1 clock enable

Set and cleared by software.

0: Disable

1: Enable


Bit 13 Reserved, must be kept at reset value.


Bit 12 **SPI1EN** : SPI1 clock enable

Set and cleared by software.

0: Disable

1: Enable


152/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


Bit 11 **TIM1EN** : TIM1 timer clock enable

Set and cleared by software.

0: Disable

1: Enable


Bits 10:1 Reserved, must be kept at reset value.


Bit 0 **SYSCFGEN** : SYSCFG clock enable

Set and cleared by software.

0: Disable

1: Enable


**6.4.16** **RCC I/O port in Sleep mode clock enable register**
**(RCC_IOPSMENR)**


Address offset: 0x44


Reset value: 0x0000 002F

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GPIOF<br>SMEN|Res.|GPIOD<br>SMEN|GPIOC<br>SMEN|GPIOB<br>SMEN|GPIOA<br>SMEN|
|||||||||||rw||rw|rw|rw|rw|



Bits 31:6 Reserved, must be kept at reset value.


Bit 5 **GPIOFSMEN:** I/O port F clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bit 4 Reserved, must be kept at reset value.


Bit 3 **GPIODSMEN:** I/O port D clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bit 2 **GPIOCSMEN:** I/O port C clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bit 1 **GPIOBSMEN:** I/O port B clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bit 0 **GPIOASMEN:** I/O port A clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


RM0490 Rev 5 153/1027



165


**Reset and clock control (RCC)** **RM0490**


**6.4.17** **RCC AHB peripheral clock enable in Sleep/Stop mode register**
**(RCC_AHBSMENR)**


Address offset: 0x48


Reset value: 0x0000 1301


This register can individually program which AHB peripheral clocks are disabled (bit
cleared) upon the device entering Sleep or Stop mode. When a bit of this register is set
(enable), the corresponding peripheral clock is supplied in Sleep or Stop mode according to
the setting of the RCC_AHBENR register.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|CRC<br>SMEN|Res.|Res.|SRAM<br>SMEN|FLASH<br>SMEN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1<br>SMEN|
||||rw|||rw|rw||||||||rw|



Bits 31:13 Reserved, must be kept at reset value.


Bit 12 **CRCSMEN** : CRC clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bits 11:10 Reserved, must be kept at reset value.


Bit 9 **SRAMSMEN** : SRAM clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bit 8 **FLASHSMEN** : Flash memory interface clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable

This bit can be activated only when the flash memory is in power down mode.


Bits 7:1 Reserved, must be kept at reset value.


Bit 0 **DMA1SMEN** : DMA1 and DMAMUX clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable

Clock to DMAMUX during Sleep mode is enabled as long as the clock in Sleep mode is
enabled to at least one DMA peripheral.


**6.4.18** **RCC APB peripheral clock enable in Sleep/Stop mode register 1**
**(RCC_APBSMENR1)**


Address offset: 0x4C


Reset value: 0x186F 7C03


154/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


This register can individually program which APB peripheral clocks are disabled (bit cleared)
upon the device entering Sleep or Stop mode. When a bit of this register is set (enable), the
corresponding peripheral clock is supplied in Sleep or Stop mode according to the setting of
the RCC_APBENR1 register.


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|PWR<br>SMEN|DBG<br>SMEN|Res.|Res.|Res.|Res.|I2C2<br>SMEN|I2C1<br>SMEN|Res.|USART4<br>SMEN|USART3<br>SMEN|USART2<br>SMEN|CRS<br>SMEN|
||||rw|rw|||||rw|rw||rw|rw|rw|rw|













|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|SPI2<br>SMEN|USB<br>SMEN|FD<br>CAN1<br>SMEN|WWDG<br>SMEN|RTC<br>APB<br>SMEN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM3<br>SMEN|TIM2<br>SMEN|
||rw|rw|rw|rw|rw|||||||||rw|rw|


Bits 31:29 Reserved, must be kept at reset value.


Bit 28 **PWRSMEN** : Power interface clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bit 27 **DBGSMEN** : Debug support clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bits 26:23 Reserved, must be kept at reset value.


Bit 22 **I2C2SMEN** : I2C2 clock enable during Sleep and Stop modes

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C051xx, STM32C071xx, and STM32C091xx/92xx, reserved_
_on the other products._


Bit 21 **I2C1SMEN** : I2C1 clock enable during Sleep and Stop modes

Set and cleared by software.

0: Disable

1: Enable


Bit 20 Reserved, must be kept at reset value.


Bit 19 **USART4SMEN** : USART4 clock enable during Sleep and Stop modes

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C091xx/92xx, reserved on the other products._


Bit 18 **USART3SMEN** : USART3 clock enable during Sleep and Stop modes

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C091xx/92xx, reserved on the other products._


RM0490 Rev 5 155/1027



165


**Reset and clock control (RCC)** **RM0490**


Bit 17 **USART2SMEN** : USART2 clock enable during Sleep and Stop modes

Set and cleared by software.

0: Disable

1: Enable


Bit 16 **CRSSMEN** : CRS clock enable during Sleep and Stop modes

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C051xx, STM32C071xx, and STM32C091xx/92xx, reserved_
_on the other products._


Bit 15 Reserved, must be kept at reset value.


Bit 14 **SPI2SMEN** : SPI2 clock enable during Sleep and Stop modes

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C071xx, reserved on the other products._


Bit 13 **USBSMEN** : USB clock enable during Sleep and Stop modes

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C071xx, reserved on the other products._


Bit 12 **FDCAN1SMEN** : FDCAN1 clock enable during Sleep and Stop modes

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C092xx, reserved on the other products._


Bit 11 **WWDGSMEN** : WWDG clock enable during Sleep and Stop modes

Set and cleared by software.

0: Disable

1: Enable


Bit 10 **RTCAPBSMEN** : RTC APB clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bits 9:2 Reserved, must be kept at reset value.


Bit 1 **TIM3SMEN** : TIM3 timer clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bit 0 **TIM2SMEN** : TIM2 timer clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C051xx, STM32C071xx, and STM32C091xx/92xx, reserved_
_on the other products._


156/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


**6.4.19** **RCC APB peripheral clock enable in Sleep/Stop mode register 2**
**(RCC_APBSMENR2)**


Address offset: 0x50


Reset value: 0x0017 D801


This register can individually program which APB peripheral clocks are disabled (bit cleared)
upon the device entering Sleep or Stop mode. When a bit of this register is set (enable), the
corresponding peripheral clock is supplied in Sleep or Stop mode according to the setting of
the RCC_APBENR2 register.


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADC<br>SMEN|Res.|TIM17<br>SMEN|TIM16<br>SMEN|TIM15<br>SMEN|
||||||||||||rw||rw|rw|rw|







|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TIM14<br>SMEN|USART1<br>SMEN|Res.|SPI1<br>SMEN|TIM1<br>SMEN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SYS<br>CFG<br>SMEN|
|rw|rw||rw|rw|||||||||||rw|


Bits 31:21 Reserved, must be kept at reset value.


Bit 20 **ADCSMEN** : ADC clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bit 19 Reserved, must be kept at reset value.


Bit 18 **TIM17SMEN** : TIM16 timer clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bit 17 **TIM16SMEN** : TIM16 timer clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bit 16 **TIM15SMEN** : TIM15 timer clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable

_Note: Only applicable to STM32C091xx/92xx, reserved on the other products._


Bit 15 **TIM14SMEN** : TIM14 timer clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bit 14 **USART1SMEN** : USART1 clock enable during Sleep and Stop modes

Set and cleared by software.

0: Disable

1: Enable


RM0490 Rev 5 157/1027



165


**Reset and clock control (RCC)** **RM0490**


Bit 13 Reserved, must be kept at reset value.


Bit 12 **SPI1SMEN** : SPI1 clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bit 11 **TIM1SMEN** : TIM1 timer clock enable during Sleep mode

Set and cleared by software.

0: Disable

1: Enable


Bits 10:1 Reserved, must be kept at reset value.


Bit 0 **SYSCFGSMEN** : SYSCFG clock enable during Sleep and Stop modes

Set and cleared by software.

0: Disable

1: Enable


**6.4.20** **RCC peripherals independent clock configuration register 1**
**(RCC_CCIPR)**


Address offset: 0x54


Reset value: 0x0000 0000

|31 30|Col2|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ADCSEL[1:0]|ADCSEL[1:0]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|rw|rw|||||||||||||||


|15 14|Col2|13 12|Col4|11|10|9 8|Col8|7|6|5|4|3|2|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|I2S1SEL[1:0]|I2S1SEL[1:0]|I2C1SEL[1:0]|I2C1SEL[1:0]|Res.|Res.|FDCAN1SEL<br>[1:0]|FDCAN1SEL<br>[1:0]|Res.|Res.|Res.|Res.|Res.|Res.|USART1SEL<br>[1:0]|USART1SEL<br>[1:0]|
|rw|rw|rw|rw|||rw|rw|||||||rw|rw|



Bits 31:30 **ADCSEL[1:0]** : ADCs clock source selection

This bitfield is controlled by software to select the asynchronous clock source for ADC:
00: System clock

01: Reserved

10: HSIKER

11: Reserved


Bits 29:16 Reserved, must be kept at reset value.


Bits 15:14 **I2S1SEL[1:0]** : I2S1 clock source selection

This bitfield is controlled by software to select I2S1 clock source as follows:

00: SYSCLK

01: Reserved

10: HSIKER

11: I2S_CKIN


158/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


Bits 13:12 **I2C1SEL[1:0]** : I2C1 clock source selection

This bitfield is controlled by software to select I2C1 clock source as follows:

00: PCLK

01: SYSCLK

10: HSIKER

11: Reserved


Bits 11:10 Reserved, must be kept at reset value.


Bits 9:8 **FDCAN1SEL[1:0]** : FDCAN1 clock source selection

This bitfield is controlled by software to select FDCAN1 clock source as follows:

00: PCLK

01: HSIKER

10: HSE

11: Reserved

_Note: Only applicable to STM32C092xx, reserved on the other products._


Bits 7:2 Reserved, must be kept at reset value.


Bits 1:0 **USART1SEL[1:0]** : USART1 clock source selection

This bitfield is controlled by software to select USART1 clock source as follows:

00: PCLK

01: SYSCLK

10: HSIKER

11: LSE


**6.4.21** **RCC peripherals independent clock configuration register 2**
**(RCC_CCIPR2)**


This register is only available on STM32C071xx. On the other devices, it is reserved.


Address offset: 0x58


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|USBSEL|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
||||rw|||||||||||||



Bits 31:13 Reserved, must be kept at reset value.


Bit 12 **USBSEL** : USB clock source selection

Set and cleared by software.

0: HSIUSB48

1: HSE


Bits 11:0 Reserved, must be kept at reset value.


**6.4.22** **RCC control/status register 1 (RCC_CSR1)**


Up to three wait states are inserted in case of successive accesses to this register.


RM0490 Rev 5 159/1027



165


**Reset and clock control (RCC)** **RM0490**


The register bits are only reset upon RTC domain reset (see _Section 6.1.3: RTC domain_
_reset_ ), except the LSCOSEL, LSCOEN, and RTCRST bits that are only reset upon RTC
domain power-on reset. Any internal or external reset has no effect on these bits.


Address offset: 0x5C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|LSCO<br>SEL|LSCO<br>EN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RTCRS<br>T|
|||||||rw|rw||||||||rw|


|15|14|13|12|11|10|9 8|Col8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|RTC<br>EN|Res.|Res.|Res.|Res.|Res.|RTCSEL[1:0]|RTCSEL[1:0]|Res.|LSE<br>CSSD|LSE<br>CSSON|Res.|LSE<br>DRV|LSE<br>BYP|LSE<br>RDY|LSEON|
|rw||||||rw|rw||r|rw||rw|rw|r|rw|



Bits 31:26 Reserved, must be kept at reset value.


Bit 25 **LSCOSEL** : Low-speed clock output selection

Set and cleared by software to select the low-speed output clock:

0: LSI

1: LSE


Bit 24 **LSCOEN** : Low-speed clock output (LSCO) enable

Set and cleared by software.

0: Disable

1: Enable


Bits 23:17 Reserved, must be kept at reset value.


Bit 16 **RTCRST** : RTC domain software reset

Set and cleared by software to reset the RTC domain:

0: No effect

1: Reset


Bit 15 **RTCEN** : RTC clock enable

Set and cleared by software. The bit enables clock to RTC.

0: Disable

1: Enable


Bits 14:10 Reserved, must be kept at reset value.


Bits 9:8 **RTCSEL[1:0]** : RTC clock source selection

Set by software to select the clock source for the RTC as follows:

00: No clock

01: LSE

10: LSI

11: HSE divided by 32
Once the RTC clock source is selected, it cannot be changed anymore unless the RTC
domain is reset, or unless a failure is detected on LSE (LSECSSD is set). The RTCRST bit
can be used to reset this bitfield to 00.


Bit 7 Reserved, must be kept at reset value.


160/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


Bit 6 **LSECSSD:** CSS on LSE failure Detection

Set by hardware to indicate when a failure is detected by the clock security system
on the external 32 kHz oscillator (LSE):

0: No failure detected

1: Failure detected


Bit 5 **LSECSSON:** CSS on LSE enable

Set by software to enable the clock security system on LSE (32 kHz) oscillator as follows:

0: Disable

1: Enable

LSECSSON must be enabled after the LSE oscillator is enabled (LSEON bit enabled) and
ready (LSERDY flag set by hardware), and after the RTCSEL bit is selected.
Once enabled, this bit cannot be disabled, except after a LSE failure detection (LSECSSD
=1). In that case the software **must** disable the LSECSSON bit.


Bit 4 Reserved, must be kept at reset value.


Bit 3 **LSEDRV** : LSE oscillator drive capability

Set by software to select the LSE oscillator drive capability as follows:
0: medium-high driving capability
1: high driving capability
Applicable when the LSE oscillator is in Xtal mode, as opposed to bypass mode.


Bit 2 **LSEBYP** : LSE oscillator bypass

Set and cleared by software to bypass the LSE oscillator (in debug mode).
0: Not bypassed
1: Bypassed
This bit can be written only when the external 32 kHz oscillator is disabled (LSEON=0 and
LSERDY=0).


Bit 1 **LSERDY** : LSE oscillator ready

Set and cleared by hardware to indicate when the external 32 kHz oscillator is ready (stable):
0: Not ready
1: Ready
After the LSEON bit is cleared, LSERDY goes low after 6 external low-speed oscillator clock
cycles.


Bit 0 **LSEON** : LSE oscillator enable

Set and cleared by software to enable LSE oscillator:

0: Disable

1: Enable


**6.4.23** **RCC control/status register 2 (RCC_CSR2)**


Up to three wait states are inserted in case of successive accesses to this register. The
register is reset upon system reset, except for reset flags that are only reset upon power
reset.


Address offset: 0x60


Reset value: 0xXX00 0000


RM0490 Rev 5 161/1027



165


**Reset and clock control (RCC)** **RM0490**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|LPWR<br>RSTF|WWDG<br>RSTF|IWDG<br>RSTF|SFT<br>RSTF|PWR<br>RSTF|PIN<br>RSTF|OBL<br>RSTF|Res.|RMVF|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|r|r|r|r|r|r|r||rw||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LSI<br>RDY|LSION|
|||||||||||||||r|rw|



Bit 31 **LPWRRSTF** : Low-power reset flag

Set by hardware when a reset occurs due to illegal Stop, or Standby, or Shutdown mode
entry.
Cleared by setting the RMVF bit.
0: No illegal mode reset occurred
1: Illegal mode reset occurred
This operates only if nRST_STOP, or nRST_STDBY or nRST_SHDW option bits are cleared.


Bit 30 **WWDGRSTF** : Window watchdog reset flag

Set by hardware when a window watchdog reset occurs.
Cleared by setting the RMVF bit.
0: No window watchdog reset occurred
1: Window watchdog reset occurred


Bit 29 **IWDGRSTF** : Independent window watchdog reset flag

Set by hardware when an independent watchdog reset domain occurs.
Cleared by setting the RMVF bit.
0: No independent watchdog reset occurred
1: Independent watchdog reset occurred


Bit 28 **SFTRSTF** : Software reset flag

Set by hardware when a software reset occurs.
Cleared by setting the RMVF bit.

0: No software reset occurred

1: Software reset occurred


Bit 27 **PWRRSTF** : BOR or POR/PDR flag

Set by hardware when a BOR or POR/PDR occurs.
Cleared by setting the RMVF bit.

0: No BOR or POR occurred

1: BOR or POR occurred


Bit 26 **PINRSTF** : Pin or other system reset flag

Set by hardware when a system reset from PF2-NRST pin or from any other source occurs.
Cleared by setting the RMVF bit.
0: No system reset occurred
1: System reset occurred


Bit 25 **OBLRSTF** : Option byte loader reset flag

Set by hardware when a reset from the Option byte loading occurs.
Cleared by setting the RMVF bit.
0: No reset from Option byte loading occurred
1: Reset from Option byte loading occurred


Bit 24 Reserved, must be kept at reset value.


162/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


Bit 23 **RMVF** : Remove reset flags

Set by software to clear the reset flags.

0: No effect

1: Clear reset flags


Bits 22:2 Reserved, must be kept at reset value.


Bit 1 **LSIRDY** : LSI oscillator ready

Set and cleared by hardware to indicate when the LSI oscillator is ready (stable):
0: Not ready
1: Ready
After the LSION bit is cleared, LSIRDY goes low after 3 LSI oscillator clock cycles. This bit
can be set even if LSION = 0 if the LSI is requested by the Clock Security System on LSE, by
the Independent Watchdog or by the RTC.


Bit 0 **LSION** : LSI oscillator enable

Set and cleared by software to enable/disable the LSI oscillator:

0: Disable

1: Enable


**6.4.24** **RCC register map**


The following table gives the RCC register map and the reset values.


**Table 31. RCC register map and reset values**













|Off-<br>set|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|RCC_CR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|HSIUSB48RDY|HSIUSB48ON|Res.|Res.|CSSON|HSEBYP|HSERDY|HSEON|Res.|Res.|HSIDIV[2:0]|HSIDIV[2:0]|HSIDIV[2:0]|HSIRDY|HSIKERON|HSION|HSIKERDIV[2:0]|HSIKERDIV[2:0]|HSIKERDIV[2:0]|SYSDIV[2:0]|SYSDIV[2:0]|SYSDIV[2:0]|Res.|Res.|
|0x00|Reset value|||||||||0|0|||0|0|0|0|||0|1|0|1|0|1|0|1|0|0|0|0|||
|0x04|RCC_ICSCR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|HSITRIM[6:0]|HSITRIM[6:0]|HSITRIM[6:0]|HSITRIM[6:0]|HSITRIM[6:0]|HSITRIM[6:0]|HSITRIM[6:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|HSICAL[7:0]|
|0x04|Reset value||||||||||||||||||1|0|0|0|0|0|0|X|X|X|X|X|X|X|X|
|0x08|RCC_CFGR|MCOPRE[3:0]|MCOPRE[3:0]|MCOPRE[3:0]|MCOPRE[3:0]|MCOSEL[3:0]|MCOSEL[3:0]|MCOSEL[3:0]|MCOSEL[3:0]|MCO2PRE[3:0]|MCO2PRE[3:0]|MCO2PRE[3:0]|MCO2PRE[3:0]|MCO2SEL[3:0]|MCO2SEL[3:0]|MCO2SEL[3:0]|MCO2SEL[3:0]|Res.|PPRE[2:0]|PPRE[2:0]|PPRE[2:0]|HPRE[3:0]|HPRE[3:0]|HPRE[3:0]|HPRE[3:0]|Res.|Res.|SWS[2:0]|SWS[2:0]|SWS[2:0]|SW[2:0]|SW[2:0]|SW[2:0]|
|0x08|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0||0|0|0|0|0|0|0|||0|0|0|0|0|0|
|0x0C|Reserved|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x10|Reserved|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x14|RCC_CRRCR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|HSIUSB48CAL[8:0]|
|0x14|Reset value|||||||||||||||||||||||X|X|X|X|X|X|X|X|X|X|
|0x18|RCC_CIER|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|HSERDYIE|HSIRDYIE|HSIUSB48RDYIE|LSERDYIE|LSIRDYIE|
|0x18|Reset value||||||||||||||||||||||||||||0|0|0|0|0|


RM0490 Rev 5 163/1027



165


**Reset and clock control (RCC)** **RM0490**


**Table 31. RCC register map and reset values (continued)**

|Off-<br>set|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x1C|RCC_CIFR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LSECSSF|CSSF|Res.|Res.|Res.|HSERDYF|HSIRDYF|HSIUSB48RDYF|LSERDYF|LSIRDYF|
|0x1C|Reset value|||||||||||||||||||||||0|0||||0|0|0|0|0|
|0x20|RCC_CICR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LSECSSC|CSSC|Res.|Res.|Res.|HSERDYC|HSIRDYC|HSIUSB48RDYC|LSERDYC|LSIRDYC|
|0x20|Reset value|||||||||||||||||||||||0|0||||0|0|0|0|0|
|0x24|RCC_<br>IOPRSTR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GPIOFRST|Res.|GPIODRST|GPIOCRST|GPIOBRST|GPIOARST|
|0x24|Reset value|||||||||||||||||||||||||||0||0|0|0|0|
|0x28|RCC_<br>AHBRSTR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CRCRST.|Res.|Res.|Res.|FLASHRST.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1RST|
|0x28|Reset value||||||||||||||||||||0||||0||||||||0|
|0x2C|RCC_<br>APBRSTR1|Res.|Res.|Res.|PWRRST|DBGRST|Res.|Res.|Res.|Res.|Res.|I2C1RST|Res.|USART4RST|USART3RST|USART2RST|CRSRST|USBRST|SPI2RST|Res.|FDCAN1RST|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM3RST|TIM2RST|
|0x2C|Reset value||||0|0||||||0||0|0|0|0|0|0||0|||||||||||0|0|
|0x30|RCC_<br>APBRSTR2|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADCRST|Res.|TIM17RST|TIM16RST|TIM15RST|TIM14RST|USART1RST|Res.|SPI1RST|TIM1RST|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SYSCFGRST|
|0x30|Reset value||||||||||||0||0|0|0|0|0||0|0|||||||||||0|
|0x34|RCC_<br>IOPENR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GPIOFEN|Res.|GPIODEN|GPIOCEN|GPIOBEN|GPIOAEN|
|0x34|Reset value|||||||||||||||||||||||||||0||0|0|0|0|
|0x38|RCC_<br>AHBENR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CRCEN|Res.|Res.|Res.|FLASHEN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1EN|
|0x38|Reset value||||||||||||||||||||0||||1||||||||0|
|0x3C|RCC_<br>APBENR1|Res.|Res.|Res.|PWREN|DBGEN|Res.|Res.|Res.|Res.|I2C2EN|I2C1EN|Res.|USART4EN|USART3EN|USART2EN|CRSEN|Res.|SPI2EN|USBEN|FDCAN1EN|WWDGEN|RTCAPBEN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM3EN|TIM2EN|
|0x3C|Reset value||||0|0|||||0|0||0|0|0|0||0|0|0|0|0|||||||||0|0|
|0x40|RCC_<br>APBENR2|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADCEN|Res.|TIM17EN|TIM16EN|TIM15EN|TIM14EN|USART1EN|Res.|SPI1EN|TIM1EN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SYSCFGEN|
|0x40|Reset value||||||||||||0||0|0|0|0|0||0|0|||||||||||0|



164/1027 RM0490 Rev 5


**RM0490** **Reset and clock control (RCC)**


**Table 31. RCC register map and reset values (continued)**

|Off-<br>set|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x44|RCC_<br>IOPSMENR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GPIOFSMEN|Res.|GPIODSMEN|GPIOCSMEN|GPIOBSMEN|GPIOASMEN|
|0x44|Reset value|||||||||||||||||||||||||||1||1|1|1|1|
|0x48|RCC_<br>AHBSMENR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CRCSMEN|Res.|Res.|SRAMSMEN|FLASHSMEN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1SMEN|
|0x48|Reset value||||||||||||||||||||1|||1|1||||||||1|
|0x4C|RCC_<br>APBSMENR1|Res.|Res.|Res.|PWRSMEN|DBGSMEN|Res.|Res.|Res.|Res.|I2C2SMEN|I2C1SMEN|Res.|USART4SMEN|USART3SMEN|USART2SMEN|CRSSMEN|Res.|SPI2SMEN|USBSMEN|FDCAN1SMEN|WWDGSMEN|RTCAPBSMEN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM3SMEN|TIM2SMEN|
|0x4C|Reset value||||1|1|||||1|1||1|1|1|1||1|1|1|1|1|||||||||1|1|
|0x50|RCC_<br>APBSMENR2|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADCSMEN|Res.|TIM17SMEN|TIM16SMEN|TIM15SMEN|TIM14SMEN|USART1SMEN|Res.|SPI1SMEN|TIM1SMEN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SYSCFGSMEN|
|0x50|Reset value||||||||||||1||1|1|1|1|1||1|1|||||||||||1|
|0x54|RCC_CCIPR|ADCSEL[1:0]|ADCSEL[1:0]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|I2S1SEL[1:0]|I2S1SEL[1:0]|I2C1SEL[1:0]|I2C1SEL[1:0]|Res.|Res.|FDCAN1SEL[1:0]|FDCAN1SEL[1:0]|Res.|Res.|Res.|Res.|Res.|Res.|USART1SEL[1:0]|USART1SEL[1:0]|
|0x54|Reset value|0|0|||||||||||||||0|0|0|0|||0|0|||||||0|0|
|0x58|RCC_CCIPR2|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USBSEL|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x58|Reset value||||||||||||||||||||0|||||||||||||
|0x5C|RCC_CSR1|Res.|Res.|Res.|Res.|Res.|Res.|LSCOSEL|LSCOEN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RTCRST|RTCEN|Res.|Res.|Res.|Res.|Res.|RTC SEL[1:0]|RTC SEL[1:0]|Res.|LSECSSD|LSECSSON|Res.|LSEDRV|LSEBYP|LSERDY|LSEON|
|0x5C|Reset value|||||||0|0||||||||0|0||||||0|0||0|0||0|0|0|0|
|0x60|RCC_CSR2|LPWRRSTF|WWDGRSTF|IWDGRSTF|SFTRSTF|PWRRSTF|PINRSTF|OBLRSTF|Res.|RMVF|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LSIRDY|LSION|
|0x60|Reset value|0|0|0|0|0|0|0||0||||||||||||||||||||||0|0|



Refer to _Section 2.2 on page 45_ for the register boundary addresses.


RM0490 Rev 5 165/1027



165


