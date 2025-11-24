**Power control (PWR)** **RM0041**

# **4 Power control (PWR)**


**Low-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 16 and 32 Kbytes.


**Medium-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 64 and 128 Kbytes.


**High-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 256 and 512 Kbytes.


This section applies to the whole STM32F100xx family, unless otherwise specified.

## **4.1 Power supplies**


The device requires a 2.0 to 3.6 V operating voltage supply (V DD ). An embedded regulator
is used to supply the internal 1.8 V digital power.


The real-time clock (RTC) and backup registers can be powered from the V BAT voltage
when the main V DD supply is powered off.


**Figure 4. Power supply overview**












|I/O Ring<br>Standby circuitry<br>(Wakeup logic,<br>IWDG)<br>Voltage Regulator|Col2|Core<br>Memories<br>digital<br>peripherals|
|---|---|---|
|I/O Ring<br>Standby circuitry<br>~~(W~~akeup logic,<br>IWDG)<br>Voltage Regulator|||



1. V DDA and V SSA must be connected to V DD and V SS, respectively.


50/709 RM0041 Rev 6


**RM0041** **Power control (PWR)**


**4.1.1** **Independent A/D and D/A converter supply and reference voltage**


To improve conversion accuracy, the ADC and the DAC have an independent power supply
that can be separately filtered and shielded from noise on the PCB.


      - The ADC and DAC voltage supply input is available on a separate V DDA pin.


      - An isolated supply ground connection is provided on pin V SSA .


When available (according to package), V REF- must be tied to V SSA .


**On 100-pin packages**


To ensure a better accuracy on low-voltage inputs and outputs, the user can connect a
separate external reference voltage on V REF+ . V REF+ is the highest voltage, represented by
the full scale value, for an analog input (ADC) or output (DAC) signal. The voltage on V REF+
can range from 2.4 V to V DDA .


**On 64-pin packages and packages with less pins**


The V REF+ and V REF- pins are not available, they are internally connected to the ADC
voltage supply (V DDA ) and ground (V SSA ).


**4.1.2** **Battery backup domain**


To retain the content of the Backup registers and supply the RTC function when V DD is
turned off, V BAT pin can be connected to an optional standby voltage supplied by a battery
or by another source.


The V BAT pin powers the RTC unit, the LSE oscillator and the PC13 to PC15 IOs, allowing
the RTC to operate even when the main digital supply (V DD ) is turned off. The switch to the
V BAT supply is controlled by the Power Down Reset embedded in the Reset block.


**Warning:** **During** **t** **RSTTEMPO** **(temporization at V** **DD** **startup) or after a PDR**
**is detected, the power switch between V** **BAT** **and V** **DD** **remains**
**connected to V** **BAT** **.**
**During the startup phase, if V** **DD** **is established in less than**
**t** **RSTTEMPO** **(Refer to the datasheet for the value of t** **RSTTEMPO** **)**
**and V** **DD** **> V** **BAT** **+ 0.6 V, a current may be injected into V** **BAT**
**through an internal diode connected between V** **DD** **and the**
**power switch (V** **BAT** **).**
**If the power supply/battery connected to the V** **BAT** **pin cannot**
**support this current injection, it is strongly recommended to**
**connect an external low-drop diode between this power**
**supply and the V** **BAT** **pin.**


If no external battery is used in the application, it is recommended to connect V BAT
externally to V DD with a 100 nF external ceramic decoupling capacitor (for more details refer
to AN2586).


RM0041 Rev 6 51/709



63


**Power control (PWR)** **RM0041**


When the backup domain is supplied by V DD (analog switch connected to V DD ), the
following functions are available:


      - PC14 and PC15 can be used as either GPIO or LSE pins


      - PC13 can be used as GPIO, TAMPER pin, RTC Calibration Clock, RTC Alarm or
second output (refer to _Section 5: Backup registers (BKP)_ )


_Note:_ _Because the switch only sinks a limited amount of current (3 mA), the use of GPIOs PC13 to_
_PC15 in output mode is restricted: the speed has to be limited to 2 MHz with a maximum_
_load of 30 pF and these IOs must not be used as a current source (e.g. to drive a LED)._


When the backup domain is supplied by V BAT (analog switch connected to V BAT because
V DD is not present), the following functions are available:


      - PC14 and PC15 can be used as LSE pins only


      - PC13 can be used as TAMPER pin, RTC Alarm or Second output (refer to
_Section 5.4.2: RTC clock calibration register (BKP_RTCCR)_ ).


**4.1.3** **Voltage regulator**


The voltage regulator is always enabled after Reset. It works in three different modes
depending on the application modes.


      - In Run mode, the regulator supplies full power to the 1.8 V domain (core, memories
and digital peripherals).


      - In Stop mode the regulator supplies low-power to the 1.8 V domain, preserving
contents of registers and SRAM


      - In Standby mode, the regulator is powered off. The contents of the registers and SRAM
are lost except for the Standby circuitry and the Backup Domain.

## **4.2 Power supply supervisor**


**4.2.1** **Power on reset (POR)/power down reset (PDR)**


The device has an integrated POR/PDR circuitry that allows proper operation starting
from/down to 2 V.


The device remains in Reset mode when V DD /V DDA is below a specified threshold,
V POR/PDR, without the need for an external reset circuit. For more details concerning the
power on/power down reset threshold, refer to the electrical characteristics of the datasheet.


52/709 RM0041 Rev 6


**RM0041** **Power control (PWR)**













The PVD can be used to monitor the V DD /V DDA power supply by comparing it to a threshold
selected by the PLS[2:0] bits in the _Power control register (PWR_CR)_ .


The PVD is enabled by setting the PVDE bit.


A PVDO flag is available, in the _Power control/status register (PWR_CSR)_, to indicate if
V DD /V DDA is higher or lower than the PVD threshold. This event is internally connected to
the EXTI line16 and can generate an interrupt if enabled through the EXTI registers. The
PVD output interrupt can be generated when V DD /V DDA drops below the PVD threshold
and/or when V DD /V DDA rises above the PVD threshold depending on EXTI line16
rising/falling edge configuration. As an example the service routine could perform
emergency shutdown tasks.


RM0041 Rev 6 53/709



63


**Power control (PWR)** **RM0041**







54/709 RM0041 Rev 6




**RM0041** **Power control (PWR)**

## **4.3 Low-power modes**


By default, the microcontroller is in Run mode after a system or a power Reset. Several lowpower modes are available to save power when the CPU does not need to be kept running,
for example when waiting for an external event. It is up to the user to select the mode that
gives the best compromise between low-power consumption, short startup time and
available wakeup sources.


The STM32F100xx devices feature three low-power modes:

      - Sleep mode (CPU clock off, all peripherals including Cortex [®] -M3 core peripherals like
NVIC, SysTick, are kept running)


      - Stop mode (all clocks are stopped)


      - Standby mode (1.8V domain powered-off)


In addition, the power consumption in Run mode can be reduced by one of the following

means:


      - Slowing down the system clocks


      - Gating the clocks to the APB and AHB peripherals when they are unused.


**Table 8. Low-power mode summary**














|Mode name|Entry|Wakeup|Effect on 1.8V<br>domain clocks|Effect on V<br>DD<br>domain clocks|Voltage regulator|
|---|---|---|---|---|---|
|Sleep<br>(Sleep now or<br>Sleep-on -exit)|WFI|Any interrupt|CPU clock OFF<br>no effect on other<br>clocks or analog<br>clock sources|None|ON|
|Sleep<br>(Sleep now or<br>Sleep-on -exit)|WFE|Wakeup event|Wakeup event|Wakeup event|Wakeup event|
|Stop|PDDS and LPDS<br>bits + SLEEPDEEP<br>bit + WFI or WFE|Any EXTI line<br>(configured in the<br>EXTI registers)|All 1.8V domain<br>clocks OFF|HSI and HSE<br>oscillators OFF|ON or in<br>low-power mode<br>(depends on_Power_<br>_control register_<br>_(PWR_CR)_)|
|Standby|PDDS bit +<br>SLEEPDEEP bit +<br>WFI or WFE|WKUP pin rising<br>edge, RTC alarm,<br>external reset in<br>NRST pin,<br>IWDG reset|WKUP pin rising<br>edge, RTC alarm,<br>external reset in<br>NRST pin,<br>IWDG reset|WKUP pin rising<br>edge, RTC alarm,<br>external reset in<br>NRST pin,<br>IWDG reset|OFF|



**4.3.1** **Slowing down system clocks**


In Run mode the speed of the system clocks (SYSCLK, HCLK, PCLK1, PCLK2) can be
reduced by programming the prescaler registers. These prescalers can also be used to slow
down peripherals before entering Sleep mode.


For more details refer to _Section 7.3.2: Clock configuration register (RCC_CFGR)_ .


RM0041 Rev 6 55/709



63


**Power control (PWR)** **RM0041**


**4.3.2** **Peripheral clock gating**


In Run mode, the HCLK and PCLKx for individual peripherals and memories can be stopped
at any time to reduce power consumption.


To further reduce power consumption in Sleep mode the peripheral clocks can be disabled
prior to executing the WFI or WFE instructions.


Peripheral clock gating is controlled by the, _APB1 peripheral clock enable register_
_(RCC_APB1ENR)_ and _APB2 peripheral clock enable register (RCC_APB2ENR)_ .


**4.3.3** **Sleep mode**


**Entering Sleep mode**


The Sleep mode is entered by executing the WFI (Wait For Interrupt) or WFE (Wait for
Event) instructions. Two options are available to select the Sleep mode entry mechanism,
depending on the SLEEPONEXIT bit in the Cortex [®] -M3 System Control register:


      - Sleep-now: if the SLEEPONEXIT bit is cleared, the MCU enters Sleep mode as soon
as WFI or WFE instruction is executed.


      - Sleep-on-exit: if the SLEEPONEXIT bit is set, the MCU enters Sleep mode as soon as
it exits the lowest priority ISR.


In the Sleep mode, all I/O pins keep the same state as in the Run mode.


Refer to _Table 9_ and _Table 10_ for details on how to enter Sleep mode.


**Exiting Sleep mode**


If the WFI instruction is used to enter Sleep mode, any peripheral interrupt acknowledged by
the nested vectored interrupt controller (NVIC) can wake up the device from Sleep mode.


If the WFE instruction is used to enter Sleep mode, the MCU exits Sleep mode as soon as
an event occurs. The wakeup event can be generated either by:


      - enabling an interrupt in the peripheral control register but not in the NVIC, and enabling
the SEVONPEND bit in the Cortex [®] -M3 System Control register. When the MCU
resumes from WFE, the peripheral interrupt pending bit and the peripheral NVIC IRQ
channel pending bit (in the NVIC interrupt clear pending register) have to be cleared.


      - or configuring an external or internal EXTI line in event mode. When the CPU resumes
from WFE, it is not necessary to clear the peripheral interrupt pending bit or the NVIC
IRQ channel pending bit as the pending bit corresponding to the event line is not set.


This mode offers the lowest wakeup time as no time is wasted in interrupt entry/exit.


Refer to _Table 9_ and _Table 10_ for more details on how to exit Sleep mode.


56/709 RM0041 Rev 6


**RM0041** **Power control (PWR)**


**Table 9. Sleep-now**







|Sleep-now mode|Description|
|---|---|
|Mode entry|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– SLEEPDEEP = 0 and<br>– SLEEPONEXIT = 0<br>Refer to the Cortex®-M3 System Control register.|
|Mode exit|If WFI was used for entry:<br>Interrupt: Refer to_Table 50: Vector table for STM32F100xx devices_<br>If WFE was used for entry<br>Wakeup event: Refer to_Section 8.2.3: Wakeup event management_|
|Wakeup latency|None|


**Table 10. Sleep-on-exit**







|Sleep-on-exit|Description|
|---|---|
|Mode entry|WFI (wait for interrupt) while:<br>– SLEEPDEEP = 0 and<br>– SLEEPONEXIT = 1<br>Refer to the Cortex®-M3 System Control register.|
|Mode exit|Interrupt: refer to_Table 50: Vector table for STM32F100xx devices_.|
|Wakeup latency|None|


**4.3.4** **Stop mode**


The Stop mode is based on the Cortex [®] -M3 deepsleep mode combined with peripheral
clock gating. The voltage regulator can be configured either in normal or low-power mode.
In Stop mode, all clocks in the 1.8 V domain are stopped, the PLL, the HSI and the HSE RC
oscillators are disabled. SRAM and register contents are preserved.


In the Stop mode, all I/O pins keep the same state as in the Run mode.


**Entering Stop mode**


Refer to _Table 11_ for details on how to enter the Stop mode.


To further reduce power consumption in Stop mode, the internal voltage regulator can be put
in low-power mode. This is configured by the LPDS bit of the _Power control register_
_(PWR_CR)_ .


If flash memory programming is ongoing, the Stop mode entry is delayed until the memory
access is finished.


If an access to the APB domain is ongoing, The Stop mode entry is delayed until the APB
access is finished.


RM0041 Rev 6 57/709



63


**Power control (PWR)** **RM0041**


In Stop mode, the following features can be selected by programming individual control bits:


      - Independent watchdog (IWDG): the IWDG is started by writing to its Key register or by
hardware option. Once started it cannot be stopped except by a Reset. See
_Section 18.3: IWDG functional description_ .


      - Real-time clock (RTC): this is configured by the RTCEN bit in the _Backup domain_
_control register (RCC_BDCR)_


      - Internal RC oscillator (LSI RC): this is configured by the LSION bit in the _Control/status_
_register (RCC_CSR)_ .


      - External 32.768 kHz oscillator (LSE OSC): this is configured by the LSEON bit in the
_Backup domain control register (RCC_BDCR)_ .


The ADC or DAC can also consume power during the Stop mode, unless they are disabled
before entering it. To disable them, the ADON bit in the ADC_CR2 register and the ENx bit
in the DAC_CR register must both be written to 0.


_Note:_ _If the application needs to disable the external clock before entering Stop mode, the HSEON_
_bit must first be disabled and the system clock switched to HSI. Otherwise, if the HSEON bit_
_remains enabled and the external clock (external oscillator) is removed when entering Stop_
_mode, the clock security system (CSS) feature must be enabled to detect any external_
_oscillator failure and avoid a malfunction behavior when entering stop mode._


Exiting Stop mode


Refer to _Table 11_ for more details on how to exit Stop mode.


When exiting Stop mode by issuing an interrupt or a wakeup event, the HSI RC oscillator is
selected as system clock.


When the voltage regulator operates in low-power mode, an additional startup delay is
incurred when waking up from Stop mode. By keeping the internal regulator ON during Stop
mode, the consumption is higher although the startup time is reduced.







|Col1|Table 11. Stop mode|
|---|---|
|**Stop mode**|**Description**|
|Mode entry|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– Set SLEEPDEEP bit in Cortex®-M3 System Control register<br>– Clear PDDS bit in Power Control register (PWR_CR)<br>– Select the voltage regulator mode by configuring LPDS bit in PWR_CR<br>**Note:** To enter Stop mode, all EXTI Line pending bits (in_Pending register_<br>_(EXTI_PR)_), all peripheral interrupt pending bits, and RTC Alarm flag must<br>be reset. Otherwise, the Stop mode entry procedure is ignored and<br>program execution continues.|
|Mode exit|If WFI was used for entry:<br>Any EXTI Line configured in Interrupt mode (the corresponding EXTI<br>Interrupt vector must be enabled in the NVIC). Refer to_Table 50: Vector_<br>_table for STM32F100xx devices_.<br>If WFE was used for entry:<br>Any EXTI Line configured in event mode. Refer to_Section 8.2.3: Wakeup_<br>_event management_|
|Wakeup latency|HSI RC wakeup time + regulator wakeup time from Low-power mode|


58/709 RM0041 Rev 6


**RM0041** **Power control (PWR)**


**4.3.5** **Standby mode**


The Standby mode allows to achieve the lowest power consumption. It is based on the
Cortex [®] -M3 deepsleep mode, with the voltage regulator disabled. The 1.8 V domain is
consequently powered off. The PLL, the HSI oscillator and the HSE oscillator are also
switched off. SRAM and register contents are lost except for registers in the Backup domain
and Standby circuitry (see _Figure 4_ ).


**Entering Standby mode**


Refer to _Table 12_ for more details on how to enter Standby mode.


In Standby mode, the following features can be selected by programming individual control
bits:


      - Independent watchdog (IWDG): the IWDG is started by writing to its Key register or by
hardware option. Once started it cannot be stopped except by a reset. See
_Section 18.3: IWDG functional description_ .


      - Real-time clock (RTC): this is configured by the RTCEN bit in the Backup domain
control register (RCC_BDCR)


      - Internal RC oscillator (LSI RC): this is configured by the LSION bit in the Control/status
register (RCC_CSR).


      - External 32.768 kHz oscillator (LSE OSC): this is configured by the LSEON bit in the
Backup domain control register (RCC_BDCR)


**Exiting Standby mode**


The microcontroller exits the Standby mode when an external reset (NRST pin), an IWDG
reset, a rising edge on the WKUP pin or the rising edge of an RTC alarm occurs (see
_Figure 196: RTC simplified block diagram_ ). All registers are reset after wakeup from
Standby except for _Power control/status register (PWR_CSR)_ .


After waking up from Standby mode, program execution restarts in the same way as after a
Reset (boot pins sampling, vector reset is fetched, etc.). The SBF status flag in the _Power_
_control/status register (PWR_CSR)_ indicates that the MCU was in Standby mode.


Refer to _Table 12_ for more details on how to exit Standby mode.


**Table 12. Standby mode**







|Standby mode|Description|
|---|---|
|Mode entry|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– Set SLEEPDEEP in Cortex®-M3 System Control register<br>– Set PDDS bit in Power Control register (PWR_CR)<br>– Clear WUF bit in Power Control/Status register (PWR_CSR)<br>– No interrupt (for WFI) or event (for WFI) is pending|
|Mode exit|WKUP pin rising edge, RTC alarm event’s rising edge, external Reset in<br>NRST pin, IWDG Reset.|
|Wakeup latency|Reset phase|


RM0041 Rev 6 59/709



63


**Power control (PWR)** **RM0041**


**I/O states in Standby mode**


In Standby mode, all I/O pins are high impedance except:


      - Reset pad (still available)


      - TAMPER pin if configured for tamper or calibration out


      - WKUP pin, if enabled


**Debug mode**


By default, the debug connection is lost if the application puts the MCU in Stop or Standby
mode while the debug features are used. This is due to the fact that the Cortex [®] -M3 core is
no longer clocked.


However, by setting some configuration bits in the DBGMCU_CR register, the software can
be debugged even when using the low-power modes extensively. For more details, refer to
_Section 25.15.1: Debug support for low-power modes_ .


**4.3.6** **Auto-wakeup (AWU) from low-power mode**


The RTC can be used to wakeup the MCU from low-power mode without depending on an
external interrupt (Auto-wakeup mode). The RTC provides a programmable time base for
waking up from Stop or Standby mode at regular intervals. For this purpose, two of the three
alternative RTC clock sources can be selected by programming the RTCSEL[1:0] bits in the
_Backup domain control register (RCC_BDCR)_ :


      - Low-power 32.768 kHz external crystal oscillator (LSE OSC).
This clock source provides a precise time base with very low-power consumption (less
than 1µA added consumption in typical conditions)


      - Low-power internal RC Oscillator (LSI RC)
This clock source has the advantage of saving the cost of the 32.768 kHz crystal. This
internal RC Oscillator is designed to add minimum power consumption.


To wakeup from Stop mode with an RTC alarm event, it is necessary to:


      - Configure the EXTI Line 17 to be sensitive to rising edge


      - Configure the RTC to generate the RTC alarm


To wakeup from Standby mode, there is no need to configure the EXTI Line 17.

## **4.4 Power control registers**


The peripheral registers can be accessed by half-words (16-bit) or words (32-bit).


**4.4.1** **Power control register (PWR_CR)**


Address offset: 0x00


Reset value: 0x0000 0000 (reset by wakeup from Standby mode)


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9|8|7 6 5|Col4|Col5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|
|Reserved|DBP|PLS[2:0]|PLS[2:0]|PLS[2:0]|PVDE|CSBF|CWUF|PDDS|LPDS|
|Reserved|rw|rw|rw|rw|rw|rc_w1|rc_w1|rw|rw|



60/709 RM0041 Rev 6


**RM0041** **Power control (PWR)**


Bits 31:9 Reserved, must be kept at reset value..


Bit 8 **DBP** : Disable backup domain write protection.

In reset state, the RTC and backup registers are protected against parasitic write access.
This bit must be set to enable write access to these registers.
0: Access to RTC and Backup registers disabled
1: Access to RTC and Backup registers enabled

_Note: If the HSE divided by 128 is used as the RTC clock, this bit must remain set to 1._


Bits 7:5 **PLS[2:0]:** PVD level selection.

These bits are written by software to select the voltage threshold detected by the
programmable voltage detector

000: 2.2V

001: 2.3V

010: 2.4V

011: 2.5V

100: 2.6V

101: 2.7V

110: 2.8V

111: 2.9V

_Note: Refer to the electrical characteristics of the datasheet for more details._


Bit 4 **PVDE:** programmable voltage detector enable.

This bit is set and cleared by software.

0: PVD disabled

1: PVD enabled


Bit 3 **CSBF** : Clear standby flag.

This bit is always read as 0.

0: No effect

1: Clear the SBF Standby Flag (write).


Bit 2 **CWUF:** Clear wakeup flag.

This bit is always read as 0.

0: No effect

1: Clear the WUF Wakeup Flag **after 2 System clock cycles** . (write)


Bit 1 **PDDS** : Power down deepsleep.

This bit is set and cleared by software. It works together with the LPDS bit.

0: Enter Stop mode when the CPU enters Deepsleep. The regulator status depends on the
LPDS bit.

1: Enter Standby mode when the CPU enters Deepsleep.


Bit 0 **LPDS:** Low-power deepsleep.

This bit is set and cleared by software. It works together with the PDDS bit.

0: Voltage regulator on during Stop mode
1: Voltage regulator in low-power mode during Stop mode


RM0041 Rev 6 61/709



63


**Power control (PWR)** **RM0041**


**4.4.2** **Power control/status register (PWR_CSR)**


Address offset: 0x04


Reset value: 0x0000 0000 (not reset by wakeup from Standby mode)


Additional APB cycles are needed to read this register versus a standard APB read.


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9|8|7 6 5 4 3|2|1|0|
|---|---|---|---|---|---|
|Reserved|EWUP|Reserved|PVDO|SBF|WUF|
|Reserved|rw|rw|r|r|r|



Bits 31:9 Reserved, must be kept at reset value.


Bit 8 **EWUP:** Enable WKUP pin

This bit is set and cleared by software.

0: WKUP pin is used for general purpose I/O. An event on the WKUP pin does not wakeup
the device from Standby mode.
1: WKUP pin is used for wakeup from Standby mode and forced in input pull down
configuration (rising edge on WKUP pin wakes-up the system from Standby mode).

_Note: This bit is reset by a system Reset._


Bits 7:3 Reserved, must be kept at reset value.


Bit 2 **PVDO:** PVD output

This bit is set and cleared by hardware. It is valid only if PVD is enabled by the PVDE bit.

0: V DD /V DDA is higher than the PVD threshold selected with the PLS[2:0] bits.
1: V DD /V DDA is lower than the PVD threshold selected with the PLS[2:0] bits.
_Note: The PVD is stopped by Standby mode. For this reason, this bit is equal to 0 after_
_Standby or reset until the PVDE bit is set._


Bit 1 **SBF:** Standby flag

This bit is set by hardware and cleared only by a POR/PDR (power on reset/power down reset)
or by setting the CSBF bit in the _Power control register (PWR_CR)_


0: Device has not been in Standby mode
1: Device has been in Standby mode


Bit 0 **WUF:** Wakeup flag

This bit is set by hardware and cleared by hardware, by a system reset or by setting the
CWUF bit in the _Power control register (PWR_CR)_
0: No wakeup event occurred
1: A wakeup event was received from the WKUP pin or from the RTC alarm

_Note: An additional wakeup event is detected if the WKUP pin is enabled (by setting the_
_EWUP bit) when the WKUP pin level is already high._


62/709 RM0041 Rev 6


**RM0041** **Power control (PWR)**


**4.4.3** **PWR register map**


The following table summarizes the PWR registers.


**Table 13. PWR register map and reset values**













|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x000<br>0x004|PWR_CR<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|DBP<br>|PLS<br>[2:0]<br><br>|PLS<br>[2:0]<br><br>|PLS<br>[2:0]<br><br>|PVDE<br><br>|CSBF<br><br>|CWUF<br><br>|PDDS<br><br>|LPDS<br>|
|0x000<br>0x004|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x000<br>0x004|PWR_CSR<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|EWUP<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|PVDO<br><br>|SBF<br><br>|WUF<br>|
|0x000<br>0x004|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|


Refer to _Table 1 on page 37_ and _Table 2 on page 38_ for the register boundary addresses.


RM0041 Rev 6 63/709



63


