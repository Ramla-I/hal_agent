**Power control (PWR)** **RM0360**

# **6 Power control (PWR)**

## **6.1 Power supplies**


The STM32F030/STM32F070 subfamily embeds a voltage regulator in order to supply the
internal 1.8 V digital power domain.


      - The STM32F030/STM32F070 devices require a 2.4 V - 3.6 V operating supply voltage
(V DD ) and a 2.4 V - 3.6 V analog supply voltage (V DDA ).


**Figure 7. Power supply overview**













**6.1.1** **Independent A/D converter supply and reference voltage**


To improve conversion accuracy and to extend the supply flexibility, the ADC has an
independent power supply that can be separately filtered and shielded from noise on the
PCB.


      - The ADC voltage supply input is available on a separate V DDA pin.


      - An isolated supply ground connection is provided on pin V SSA .


The V DDA supply/reference voltage must be equal or higher than V DD .


When a single supply is used, V DDA can be externally connected to V DD, through the
external filtering circuit in order to ensure a noise free V DDA reference voltage.


When V DDA is different from V DD, V DDA must always be higher or equal to V DD . To keep
safe potential difference in between V DDA and V DD during power-up/power-down, an
external Shottky diode may be used between V DD and V DDA . Refer to the datasheet for the
maximum allowed difference.


76/775 RM0360 Rev 5


**RM0360** **Power control (PWR)**


**6.1.2** **Voltage regulator**


The voltage regulator is always enabled after Reset. It works in three different modes
depending on the application modes.


      - In Run mode, the regulator supplies full power to the 1.8 V domain (core, memories
and digital peripherals).


      - In Stop mode the regulator supplies low-power to the 1.8 V domain, preserving
contents of registers and SRAM


      - In Standby Mode, the regulator is powered off. The contents of the registers and SRAM
are lost except for the Standby circuitry.

## **6.2 Power supply supervisor**


**6.2.1** **Power on reset (POR) / power down reset (PDR)**


STM32F0x1xx and STM32F0x2xx devices feature integrated power-on reset (POR) and
power-down reset (PDR) circuits, which are always active and ensure proper operation
above a threshold of 2 V.


The device remains in Reset mode when the monitored supply voltage is below a specified
threshold, V POR/PDR, without the need for an external reset circuit.


      - The POR monitors only the V DD supply voltage. During the startup phase V DDA must
arrive first and be greater than or equal to V DD.

      - The PDR monitors both the V DD and V DDA supply voltages. However, the V DDA power
supply supervisor can be disabled (by programming a dedicated option bit
V DDA_MONITOR ) to reduce the power consumption if the application is designed to
make sure that V DDA is higher than or equal to V DD .


For more details on the power on / power down reset threshold, refer to the electrical
characteristics section in the datasheet.


**Figure 8. Power on reset/power down reset waveform**











RM0360 Rev 5 77/775



87


**Power control (PWR)** **RM0360**

## **6.3 Low-power modes**


By default, the microcontroller is in Run mode after a system or a power Reset. Several lowpower modes are available to save power when the CPU does not need to be kept running,
for example when waiting for an external event. It is up to the user to select the mode that
gives the best compromise between low-power consumption, short startup time and
available wake-up sources.


The device features three low-power modes:

      - Sleep mode (CPU clock off, all peripherals including Arm [®] Cortex [®] -M0 core
peripherals like NVIC, SysTick, etc. are kept running)


      - Stop mode (all clocks are stopped)


      - Standby mode (1.8V domain powered-off)


In addition, the power consumption in Run mode can be reduce by one of the following

means:


      - Slowing down the system clocks


      - Gating the clocks to the APB and AHB peripherals when they are unused.


78/775 RM0360 Rev 5


**RM0360** **Power control (PWR)**


**Table 15. Low-power mode summary**
























|Mode name|Entry|Wake-up|Effect on 1.8 V<br>domain clocks|Effect on<br>V<br>DD<br>domain<br>clocks|Voltage<br>regulator|
|---|---|---|---|---|---|
|Sleep<br>(Sleep now or<br>Sleep-on -<br>exit)|WFI|Any interrupt|CPU clock OFF<br>no effect on other<br>clocks or analog<br>clock sources|None|ON|
|Sleep<br>(Sleep now or<br>Sleep-on -<br>exit)|WFE|Wake-up event|Wake-up event|Wake-up event|Wake-up event|
|Stop|PDDS and LPDS<br>bits +<br>SLEEPDEEP bit<br>+ WFI or WFE|Any EXTI line<br>(configured in the<br>EXTI registers)|All 1.8V domain<br>clocks OFF|HSI and<br>HSE<br>oscillators<br>OFF|ON or in low-<br>power mode<br>(depends on<br>_Power control_<br>_register_<br>_(PWR_CR)_)|
|Standby|PDDS bit +<br>SLEEPDEEP bit<br>+ WFI or WFE|WKUP pin rising<br>edge, RTC alarm,<br>external reset in<br>NRST pin, <br>IWDG reset|WKUP pin rising<br>edge, RTC alarm,<br>external reset in<br>NRST pin, <br>IWDG reset|WKUP pin rising<br>edge, RTC alarm,<br>external reset in<br>NRST pin, <br>IWDG reset|OFF|



**6.3.1** **Slowing down system clocks**


In Run mode the speed of the system clocks (SYSCLK, HCLK, PCLK) can be reduced by
programming the prescaler registers. These prescalers can also be used to slow down
peripherals before entering Sleep mode.


For more details refer to _Section 7.4.2: Clock configuration register (RCC_CFGR)_ .


RM0360 Rev 5 79/775



87


**Power control (PWR)** **RM0360**


**6.3.2** **Peripheral clock gating**


In Run mode, the AHB clock (HCLK) and the APB clock (PCLK) for individual peripherals
and memories can be stopped at any time to reduce power consumption.


To further reduce power consumption in Sleep mode the peripheral clocks can be disabled
prior to executing the WFI or WFE instructions.


Peripheral clock gating is controlled by the _AHB peripheral clock enable register_
_(RCC_AHBENR)_, the _APB peripheral clock enable register 2 (RCC_APB2ENR)_ and the
_APB peripheral clock enable register 1 (RCC_APB1ENR)_ .


**6.3.3** **Sleep mode**


**Entering Sleep mode**


The Sleep mode is entered by executing the WFI (Wait For Interrupt) or WFE (Wait for
Event) instructions. Two options are available to select the Sleep mode entry mechanism,
depending on the SLEEPONEXIT bit in the Arm [®] Cortex [®] -M0 System Control register:


      - Sleep-now: if the SLEEPONEXIT bit is cleared, the MCU enters Sleep mode as soon
as WFI or WFE instruction is executed.


      - Sleep-on-exit: if the SLEEPONEXIT bit is set, the MCU enters Sleep mode as soon as
it exits the lowest priority ISR.


In the Sleep mode, all I/O pins keep the same state as in the Run mode.


Refer to _Table 16_ and _Table 17_ for details on how to enter Sleep mode.


**Exiting Sleep mode**


If the WFI instruction is used to enter Sleep mode, any peripheral interrupt acknowledged by
the nested vectored interrupt controller (NVIC) can wake up the device from Sleep mode.


If the WFE instruction is used to enter Sleep mode, the MCU exits Sleep mode as soon as
an event occurs. The wake-up event can be generated either by:


      - enabling an interrupt in the peripheral control register but not in the NVIC, and enabling
the SEVONPEND bit in the Arm [®] Cortex [®] -M0 System Control register. When the MCU
resumes from WFE, the peripheral interrupt pending bit and the peripheral NVIC IRQ
channel pending bit (in the NVIC interrupt clear pending register) must be cleared.


      - or configuring an external or internal EXTI line in event mode. When the CPU resumes
from WFE, it is not necessary to clear the peripheral interrupt pending bit or the NVIC
IRQ channel pending bit as the pending bit corresponding to the event line is not set.


This mode offers the lowest wake-up time as no time is wasted in interrupt entry/exit.


Refer to _Table 16_ and _Table 17_ for more details on how to exit Sleep mode.


80/775 RM0360 Rev 5


**RM0360** **Power control (PWR)**








|Col1|Table 16. Sleep-now|
|---|---|
|**Sleep-now mode**|**Description**|
|**Mode entry**|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– SLEEPDEEP = 0 and<br>– SLEEPONEXIT = 0<br>Refer to the Arm® Cortex®-M0 System Control register.|
|**Mode exit**|If WFI was used for entry:<br>Interrupt: Refer to_Table 31: Vector table_<br>If WFE was used for entry<br>Wake-up event: Refer to_Section 11.2.3: Event management_|
|**Wake-up latency**|None|







|Col1|Table 17. Sleep-on-exit|
|---|---|
|**Sleep-on-exit**|**Description**|
|**Mode entry**|WFI (wait for interrupt) while:<br>– SLEEPDEEP = 0 and<br>– SLEEPONEXIT = 1<br>Refer to the Arm® Cortex®-M0 System Control register.|
|**Mode exit**|Interrupt: Refer to_Table 31: Vector table_.|
|**Wake-up latency**|None|


**6.3.4** **Stop mode**


The Stop mode is based on the Arm [®] Cortex [®] -M0 deep sleep mode combined with
peripheral clock gating. The voltage regulator can be configured either in normal or lowpower mode. In Stop mode, all clocks in the 1.8 V domain are stopped, the PLL, the HSI and
the HSE oscillators are disabled. SRAM and register contents are preserved.


In the Stop mode, all I/O pins keep the same state as in the Run mode.


**Entering Stop mode**


Refer to _Table 18_ for details on how to enter the Stop mode.


To further reduce power consumption in Stop mode, the internal voltage regulator can be put
in low-power mode. This is configured by the LPDS bit of the _Power control register_
_(PWR_CR)_ .


If Flash memory programming is ongoing, the Stop mode entry is delayed until the memory
access is finished.


If an access to the APB domain is ongoing, The Stop mode entry is delayed until the APB
access is finished.


In Stop mode, the following features can be selected by programming individual control bits:


      - Independent watchdog (IWDG): the IWDG is started by writing to its Key register or by
hardware option. Once started it cannot be stopped except by a Reset. See
_Section 19.3: IWDG functional description_ .


RM0360 Rev 5 81/775



87


**Power control (PWR)** **RM0360**


      - real-time clock (RTC): this is configured by the RTCEN bit in the _RTC domain control_
_register (RCC_BDCR)_


      - Internal RC oscillator (LSI): this is configured by the LSION bit in the _Control/status_
_register (RCC_CSR)_ .


      - External 32.768 kHz oscillator (LSE): this is configured by the LSEON bit in the _RTC_
_domain control register (RCC_BDCR)_ .


The ADC can also consume power during Stop mode, unless it is disabled before entering
this mode. Refer to _ADC control register (ADC_CR)_ for details on how to disable it.


**Exiting Stop mode**


Refer to _Table 18_ for more details on how to exit Stop mode.


When exiting Stop mode by issuing an interrupt or a wake-up event, the HSI oscillator is
selected as system clock.


When the voltage regulator operates in low-power mode, an additional startup delay is
incurred when waking up from Stop mode. By keeping the internal regulator ON during Stop
mode, the consumption is higher although the startup time is reduced.







|Col1|Table 18. Stop mode|
|---|---|
|**Stop mode**|**Description**|
|**Mode entry**|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– Set SLEEPDEEP bit in Arm® Cortex®-M0 System Control register<br>– Clear PDDS bit in Power Control register (PWR_CR)<br>– Select the voltage regulator mode by configuring LPDS bit in PWR_CR<br>**Note:** To enter Stop mode, all EXTI line pending bits (in_Pending register_<br>_(EXTI_PR)_), all peripherals interrupt pending bits and RTC Alarm flag must<br>be reset. Otherwise, the Stop mode entry procedure is ignored and<br>program execution continues.<br>If the application needs to disable the external oscillator (external clock)<br>before entering Stop mode, the system clock source must be first switched<br>to HSI and then clear the HSEON bit.<br>Otherwise, if before entering Stop mode the HSEON bit is kept at 1, the<br>security system (CSS) feature must be enabled to detect any external<br>oscillator (external clock) failure and avoid a malfunction when entering<br>Stop mode.|
|**Mode exit**|If WFI was used for entry:<br>– Any EXTI line configured in Interrupt mode (the corresponding EXTI<br>Interrupt vector must be enabled in the NVIC).<br>Refer to_Table 31: Vector table_.<br>If WFE was used for entry:<br>Any EXTI line configured in event mode. Refer to_Section 11.2.3: Event_<br>_management on page 174_|
|**Wake-up latency**|HSI wake-up time + regulator wake-up time from Low-power mode|


82/775 RM0360 Rev 5


**RM0360** **Power control (PWR)**


**6.3.5** **Standby mode**


The Standby mode allows to achieve the lowest power consumption. It is based on the
Arm [®] Cortex [®] -M0 deepsleep mode, with the voltage regulator disabled. The 1.8 V domain
is consequently powered off. The PLL, the HSI oscillator and the HSE oscillator are also
switched off. SRAM and register contents are lost except for registers in the Standby
circuitry (see _Figure 7_ ).


**Entering Standby mode**


Refer to _Table 19_ for more details on how to enter Standby mode.


In Standby mode, the following features can be selected by programming individual control
bits:


      - Independent watchdog (IWDG): the IWDG is started by writing to its Key register or by
hardware option. Once started it cannot be stopped except by a reset. See
_Section 19.3: IWDG functional description_ .


      - Real-time clock (RTC): this is configured by the RTCEN bit in the _RTC domain control_
_register (RCC_BDCR)_ .


      - Internal RC oscillator (LSI): this is configured by the LSION bit in the _Control/status_
_register (RCC_CSR)_ .


      - External 32.768 kHz oscillator (LSE): this is configured by the LSEON bit in the _RTC_
_domain control register (RCC_BDCR)_ .


**Exiting Standby mode**


The microcontroller exits the Standby mode when an external reset (NRST pin), an IWDG
reset, a rising edge on one of the enabled WKUPx pins or an RTC event occurs. All
registers are reset after wake-up from Standby except for _Power control/status register_
_(PWR_CSR)_ .


After waking up from Standby mode, program execution restarts in the same way as after a
Reset (boot pin sampling, option bytes loading, reset vector is fetched, etc.). The SBF status
flag in the _Power control/status register (PWR_CSR)_ indicates that the MCU was in Standby
mode.


Refer to _Table 19_ for more details on how to exit Standby mode.







|Col1|Table 19. Standby mode|
|---|---|
|**Standby mode**|**Description**|
|**Mode entry**|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– Set SLEEPDEEP in Arm® Cortex®-M0 System Control register<br>– Set PDDS bit in Power Control register (PWR_CR)<br>– Clear WUF bit in Power Control/Status register (PWR_CSR)|
|**Mode exit**|WKUP pin rising edge, RTC alarm event’s rising edge, external Reset in<br>NRST pin, IWDG Reset.|
|**Wake-up latency**|Reset phase|


RM0360 Rev 5 83/775



87


**Power control (PWR)** **RM0360**


**I/O states in Standby mode**


In Standby mode, all I/O pins are high impedance except:


      - Reset pad (still available)


      - PC13, PC14 and PC15 if configured by RTC or LSE


      - WKUPx pins


**Debug mode**


By default, the debug connection is lost if the application puts the MCU in Stop or Standby
mode while the debug features are used. This is due to the fact that the Arm [®] Cortex [®] -M0
core is no longer clocked.


However, by setting some configuration bits in the DBGMCU_CR register, the software can
be debugged even when using the low-power modes extensively.


**6.3.6** **RTC wakeup from low-power mode**


The RTC can be used to wake-up the MCU from low-power mode by means of the RTC
alarm. For this purpose, two of the three alternative RTC clock sources can be selected by
programming the RTCSEL[1:0] bits in the _RTC domain control register (RCC_BDCR)_ :


      - Low-power 32.768 kHz external crystal oscillator (LSE OSC)
This clock source provides a precise time base with very low-power consumption (less
than 1 µA added consumption in typical conditions)


      - Low-power internal RC oscillator (LSI)
This clock source has the advantage of saving the cost of the 32.768 kHz crystal. This
internal RC oscillator is designed to add minimum power consumption.


To wake-up from Stop mode with an RTC alarm event, it is necessary to:


      - Configure the EXTI Line 17 to be sensitive to rising edge


      - Configure the RTC to generate the RTC alarm


To wake-up from Standby mode, there is no need to configure the EXTI Line 17.


84/775 RM0360 Rev 5


**RM0360** **Power control (PWR)**

## **6.4 Power control registers**


The peripheral registers can be accessed by half-words (16-bit) or words (32-bit).


**6.4.1** **Power control register (PWR_CR)**


Address offset: 0x00


Reset value: 0x0000 0000 (reset by wake-up from Standby mode)

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res|Res|Res|Res|Res|Res|Res|DBP|Res|Res|Res|Res|CSBF|CWUF|PDDS|LPDS|
||||||||rw|||||rc_w1|rc_w1|rw|rw|



Bits 31:9 Reserved, must be kept at reset value.


Bit 8 **DBP** : Disable RTC domain write protection.

In reset state, the RTC registers are protected against parasitic write access. This bit must be
set to enable write access to these registers.

0: Access to RTC disabled

1: Access to RTC enabled


Bits 7:4 Reserved, must be kept at reset value


Bit 3 **CSBF** : Clear standby flag.

This bit is always read as 0.

0: No effect

1: Clear the SBF standby flag (write).


Bit 2 **CWUF:** Clear wake-up flag.

This bit is always read as 0.

0: No effect

1: Clear the WUF wake-up Flag **after 2 System clock cycles** . (write)


Bit 1 **PDDS** : Power down deepsleep.

This bit is set and cleared by software. It works together with the LPDS bit.

0: Enter Stop mode when the CPU enters Deepsleep. The regulator status depends on the
LPDS bit.

1: Enter Standby mode when the CPU enters Deepsleep.


Bit 0 **LPDS:** Low-power deepsleep.

This bit is set and cleared by software. It works together with the PDDS bit.

0: Voltage regulator on during Stop mode
1: Voltage regulator in low-power mode during Stop mode

_Note: When a peripheral that can work in STOP mode requires a clock, the Power controller_
_automatically switch the voltage regulator from Low-power mode to Normal mode and_
_remains in this mode until the request disappears._


RM0360 Rev 5 85/775



87


**Power control (PWR)** **RM0360**


**6.4.2** **Power control/status register (PWR_CSR)**


Address offset: 0x04


Reset value: 0x0000 000X (not reset by wake-up from Standby mode)


Additional APB cycles are needed to read this register versus a standard APB read.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|EWUP<br>7|EWUP<br>6|EWUP<br>5|EWUP<br>4|Res.|EWUP<br>2|EWUP<br>1|Res|Res|Res|Res|Res|Res|SBF|WUF|
||rw|rw|rw|rw||rw|rw|||||||r|r|



Bits 31:15 Reserved, must be kept at reset value.


Bits 14:11 **EWUPx:** Enable WKUPx pin (available only on STM32F070xB and STM32F030xC devices)

These bits are set and cleared by software.

0: WKUPx pin is used for general purpose I/O. An event on the WKUPx pin does not wakeup the device from Standby mode.
1: WKUPx pin is used for wake-up from Standby mode and forced in input pull down
configuration (rising edge on WKUPx pin wakes-up the system from Standby mode).

_Note: These bits are reset by a system Reset._


Bit 10 Reserved, must be kept at reset value.


Bits 9:8 **EWUPx:** Enable WKUPx pin

These bits are set and cleared by software.

0: WKUPx pin is used for general purpose I/O. An event on the WKUPx pin does not wakeup
the device from Standby mode.
1: WKUPx pin is used for wakeup from Standby mode and forced in input pull down
configuration (rising edge on WKUPx pin wakes-up the system from Standby mode).

_Note: These bits are reset by a system Reset._


Bits 7:2 Reserved, must be kept at reset value.


Bit 1 **SBF:** Standby flag

This bit is set by hardware when the device enters Standby mode and it is cleared only by a
POR/PDR (power on reset/power down reset) or by setting the CSBF bit in the _Power control_
_register (PWR_CR)_


0: Device has not been in Standby mode
1: Device has been in Standby mode


Bit 0 **WUF:** Wake-up flag

This bit is set by hardware to indicate that the device received a wake-up event. It is cleared by
a system reset or by setting the CWUF bit in the _Power control register (PWR_CR)_


0: No wake-up event occurred
1: A wake-up event was received from one of the enabled WKUPx pins or from the RTC
alarm.

_Note: An additional wake-up event is detected if one WKUPx pin is enabled (by setting the_
_EWUPx bit) when its pin level is already high._


86/775 RM0360 Rev 5


**RM0360** **Power control (PWR)**


**6.4.3** **PWR register map**


The following table summarizes the PWR register map and reset values.


**Table 20. PWR register map and reset values**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x000|**PWR_CR**<br><br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.|CSBF<br>|CWUF<br>|PDDS<br>|LPDS<br>|
|0x000|~~Reset value~~|||||||||||||||||||||||||||||~~0~~|~~0~~|~~0~~|~~0~~|
|0x004|**PWR_CSR**<br><br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.|EWUP7(1)<br>|EWUP6(1)<br>|EWUP5(1)<br>|EWUP4(1)<br><br>|Res.|EWUP2<br>|EWUP1<br><br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.|SBF<br>|WUF<br>|
|0x004|~~Reset value~~||||||||||||||||||~~0~~|~~0~~|~~0~~|~~0~~||~~0~~|~~0~~|||||||~~0~~|~~0~~|



1. Available on STM32F070xB and STM32F030xC devices only.


Refer to _Section 2.2 on page 37_ for the register boundary addresses.


RM0360 Rev 5 87/775



87


