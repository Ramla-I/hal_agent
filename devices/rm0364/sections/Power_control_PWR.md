**Power control (PWR)** **RM0364**

# **6 Power control (PWR)**

## **6.1 Power supplies**


The STM32F334xx devices require a 2.0 V - 3.6 V operating supply voltage (V DD ) and a 2.0
V - 3.6 V analog supply voltage (V DDA ). The embedded regulator is used to supply the
internal 1.8 V digital power.


The real-time clock (RTC) and backup registers can be powered from the V BAT voltage
when the main V DD supply is powered off.


**Figure 6. Power supply overview**













The following supply voltages are available:


      - V DD and V SS : external power supply for I/Os and core.
These supply voltages are provided externally through V DD and V SS pins. V DD = 2.0 to
3.6 V .
V DD must always be kept lower than or equal to V DDA .


      - VDD18 = 1.65 to 1.95 V (VDD18 domain): power supply for digital core, SRAM and
Flash memory.
VDD18 is internally generated through an internal voltage regulator .


82/1124 RM0364 Rev 4


**RM0364** **Power control (PWR)**


      - V DDA, V SSA = 2.0 to 3.6 V : external power supply for ADC, DAC, comparators,
operational amplifiers, temperature sensor, PLL, HSI 8 MHz oscillator, LSI 40 kHz
oscillator, and reset block.
V DDA must be in the 2.4 to 3.6 V range when the OPAMP and DAC are used.
It is forbidden to have V DDA < V DD          - 0.4 V. An external Schottky diode must be placed
between V DD and V DDA to guarantee that this condition is met.


      - V BAT = 1.65 to 3.6 V: Backup power supply for RTC, LSE oscillator, PC13 to PC15 and
backup registers when V DD is not present. When V DD supply is present, the internal
power switch switches the backup power to V DD . If V BAT is not used, it must be
connected to V DD .


**6.1.1** **Independent A/D and D/A converter supply and reference voltage**


To improve conversion accuracy, the ADC and the DAC have an independent power supply
which can be separately filtered and shielded from noise on the PCB.


The ADC and DAC voltage supply input is available on a separate VDDA pin. An isolated
supply ground connection is provided on the VSSA pin.


**64-pin, 48-pin and 32-pin package connections**


On these packages, the VREF+ and VREF- pins are not available. They are internally
connected to the ADC voltage supply (V DDA ) and ground (V SSA ) respectively.


The V DDA supply/reference voltage can be equal to or higher than V DD . When a single
supply is used, V DDA can be externally connected to V DD, through the external filtering
circuit in order to ensure a noise free V DDA /reference voltage.


When V DDA is different from V DD, V DDA must always be higher or equal to V DD . To maintain
a safe potential difference between V DDA and V DD during power-up/power-down, an
external Schottky diode can be used between V DD and V DDA . Refer to the datasheet for the
maximum allowed difference.


**6.1.2** **Battery Backup domain**


To retain the content of the backup registers and supply the RTC function when V DD is
turned off, V BAT pin can be connected to an optional standby voltage supplied by a battery
or by another source.


The V BAT pin powers the RTC unit, the LSE oscillator and the PC13 to PC15 I/Os, allowing
the RTC to operate even when the main power supply is turned off. The switch to the V BAT
supply is controlled by the power-down reset (PDR) embedded in the reset block.


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


RM0364 Rev 4 83/1124



95


**Power control (PWR)** **RM0364**


**connect an external low-drop diode between this power**
**supply and the V** **BAT** **pin.**


If no external battery is used in the application, it is recommended to connect V BAT
externally to V DD with a 100 nF external ceramic decoupling capacitor (for more details refer
to AN4206).


When the RTC domain is supplied by V DD (analog switch connected to V DD ), the following
functions are available:


      - PC13, PC14 and PC15 can be used as GPIO pins


      - PC13, PC14 and PC15 can be configured by RTC or LSE (refer to _Section 26.3: RTC_
_functional description on page 836_ )


_Note:_ _Due to the fact that the switch only sinks a limited amount of current (3 mA), the use of_
_GPIOs PC13 to PC15 in output mode is restricted: the speed has to be limited to 2 MHz with_
_a maximum load of 30 pF and these I/Os must not be used as a current source (e.g. to drive_
_an LED)._


When the RTC domain is supplied by V BAT (analog switch connected to V BAT because V DD
is not present), the following functions are available:


      - PC13, PC14 and PC15 can be controlled only by RTC or LSE (refer to _Section 26.3:_
_RTC functional description on page 836_ )


**6.1.3** **Voltage regulator**


The voltage regulator is always enabled after Reset. It works in three different modes
depending on the application modes.


      - In Run mode, the regulator supplies full power to the 1.8 V domain (core, memories
and digital peripherals).


      - In Stop mode the regulator supplies low-power to the 1.8 V domain, preserving
contents of registers and SRAM.


      - In Standby Mode, the regulator is powered off. The contents of the registers and SRAM
are lost except for the Standby circuitry and the RTC Domain.

## **6.2 Power supply supervisor**


**6.2.1** **Power on reset (POR)/power down reset (PDR)**


The device has an integrated power-on reset (POR) and power-down reset (PDR) circuits
which are always active and ensure proper operation above a threshold of 2 V.


The device remains in Reset mode when the monitored supply voltage is below a specified
threshold, V POR/PDR, without the need for an external reset circuit.


      - The POR monitors only the V DD supply voltage. During the startup phase V DDA must
arrive first and be greater than or equal to V DD .


      - The PDR monitors both the V DD and V DDA supply voltages. However, if the application
is designed with V DDA higher than or equal to V DD, the V DDA power supply supervisor
can be disabled (by programming a dedicated VDDA_MONITOR option bit) to reduce
the power consumption.


84/1124 RM0364 Rev 4


**RM0364** **Power control (PWR)**


For more details on the power on /power down reset threshold, refer to the electrical
characteristics section in the datasheet.


**Figure 7. Power on reset/power down reset waveform**





|POR|Col2|Col3|
|---|---|---|
||||
|||Temporization<br>tRSTTEMPO|
||||
||||


**6.2.2** **Programmable voltage detector (PVD)**





User can use the PVD to monitor the V DD power supply by comparing it to a threshold
selected by the PLS[2:0] bits in the _Power control register (PWR_CR)_ .


The PVD is enabled by setting the PVDE bit.


A PVDO flag is available, in the _Power control/status register (PWR_CSR)_, to indicate if V DD
is higher or lower than the PVD threshold. This event is internally connected to the EXTI
line16 and can generate an interrupt if enabled through the EXTI registers. The rising/falling
edge sensitivity of the EXTI Line16 should be configured according to PVD output behavior
i.e. if the EXTI line 16 is configured to rising edge sensitivity, the interrupt is generated when
V DD drops below the PVD threshold. As an example the service routine could perform
emergency shutdown tasks.


RM0364 Rev 4 85/1124



95


**Power control (PWR)** **RM0364**


**Figure 8. PVD thresholds**


VDD





100 mV

hysteresis


MS19670V1



PVD output

|Col1|PVD threshold|
|---|---|
|||
|||
|||


## **6.3 Low-power modes**



By default, the microcontroller is in Run mode after a system or a power Reset. Several lowpower modes are available to save power when the CPU does not need to be kept running,
for example when waiting for an external event. It is up to the user to select the mode that
gives the best compromise between low-power consumption, short startup time and
available wakeup sources.


The device features three low-power modes:

- Sleep mode (CPU clock off, all peripherals including Arm [®] Cortex [®] -M4 core
peripherals like NVIC, SysTick, etc. are kept running)


- Stop mode (all clocks are stopped)


- Standby mode (1.8V domain powered-off)


In addition, the power consumption in Run mode can be reduce by one of the following

means:


- Slowing down the system clocks


- Gating the clocks to the APB and AHB peripherals when they are unused.


**Table 14. Low-power mode summary**












|Mode name|Entry|wakeup|Effect on 1.8V<br>domain clocks|Effect on<br>V<br>DD<br>domain<br>clocks|Voltage<br>regulator|
|---|---|---|---|---|---|
|Sleep<br>(Sleep now or<br>Sleep-on -<br>exit)|WFI|Any interrupt|CPU clock OFF<br>no effect on other<br>clocks or analog<br>clock sources|None|ON|
|Sleep<br>(Sleep now or<br>Sleep-on -<br>exit)|WFE|Wakeup event|Wakeup event|Wakeup event|Wakeup event|



86/1124 RM0364 Rev 4


**RM0364** **Power control (PWR)**


**Table 14. Low-power mode summary**


















|Mode name|Entry|wakeup|Effect on 1.8V<br>domain clocks|Effect on<br>V<br>DD<br>domain<br>clocks|Voltage<br>regulator|
|---|---|---|---|---|---|
|Stop|PDDS and LPDS<br>bits +<br>SLEEPDEEP bit<br>+ WFI or WFE|Any EXTI line<br>(configured in the<br>EXTI registers)<br>Specific<br>communication<br>peripherals on<br>reception events<br>(USART, I2C)|All 1.8V domain<br>clocks OFF|HSI and<br>HSE<br>oscillators<br>OFF|ON or in low-<br>power mode<br>(depends on<br>_Power control_<br>_register_<br>_(PWR_CR)_)|
|Standby|PDDS bit +<br>SLEEPDEEP bit<br>+ WFI or WFE|WKUP pin rising<br>edge, RTC alarm,<br>external reset in<br>NRST pin,<br>IWDG reset|WKUP pin rising<br>edge, RTC alarm,<br>external reset in<br>NRST pin,<br>IWDG reset|WKUP pin rising<br>edge, RTC alarm,<br>external reset in<br>NRST pin,<br>IWDG reset|OFF|



**6.3.1** **Slowing down system clocks**


In Run mode the speed of the system clocks (SYSCLK, HCLK, PCLK) can be reduced by
programming the prescaler registers. These prescalers can also be used to slow down
peripherals before entering Sleep mode.


For more details refer to _Section 8.4.2: Clock configuration register (RCC_CFGR)_ .


**6.3.2** **Peripheral clock gating**


In Run mode, the HCLK and PCLK for individual peripherals and memories can be stopped
at any time to reduce power consumption.


To further reduce power consumption in Sleep mode the peripheral clocks can be disabled
prior to executing the WFI or WFE instructions.


Peripheral clock gating is controlled by the AHB peripheral clock enable register
(RCC_AHBENR), APB1 peripheral clock enable register (RCC_APB1ENR) and APB2
peripheral clock enable register (RCC_APB2ENR).


**6.3.3** **Sleep mode**


**Entering Sleep mode**


The Sleep mode is entered by executing the WFI (Wait For Interrupt) or WFE (Wait for
Event) instructions. Two options are available to select the Sleep mode entry mechanism,
depending on the SLEEPONEXIT bit in the Arm [®] Cortex [®] -M4 System Control register:


      - Sleep-now: if the SLEEPONEXIT bit is cleared, the MCU enters Sleep mode as soon
as WFI or WFE instruction is executed.


      - Sleep-on-exit: if the SLEEPONEXIT bit is set, the MCU enters Sleep mode as soon as
it exits the lowest priority ISR.


In the Sleep mode, all I/O pins keep the same state as in the Run mode.


Refer to _Table 15_ and _Table 16_ for details on how to enter Sleep mode.


RM0364 Rev 4 87/1124



95


**Power control (PWR)** **RM0364**


**Exiting Sleep mode**


If the WFI instruction is used to enter Sleep mode, any peripheral interrupt acknowledged by
the nested vectored interrupt controller (NVIC) can wake up the device from Sleep mode.


If the WFE instruction is used to enter Sleep mode, the MCU exits Sleep mode as soon as
an event occurs. The wakeup event can be generated either by:


      - enabling an interrupt in the peripheral control register but not in the NVIC, and enabling
the SEVONPEND bit in the Cortex-M4 System Control register. When the MCU
resumes from WFE, the peripheral interrupt pending bit and the peripheral NVIC IRQ
channel pending bit (in the NVIC interrupt clear pending register) have to be cleared.


      - or configuring an external or internal EXTI line in event mode. When the CPU resumes
from WFE, it is not necessary to clear the peripheral interrupt pending bit or the NVIC
IRQ channel pending bit as the pending bit corresponding to the event line is not set.


This mode offers the lowest wakeup time as no time is wasted in interrupt entry/exit.


Refer to _Table 15_ and _Table 16_ for more details on how to exit Sleep mode.


**Table 15. Sleep-now**







|Sleep-now mode|Description|
|---|---|
|Mode entry|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– SLEEPDEEP = 0 and<br>– SLEEPONEXIT = 0<br>Refer to the Cortex-M4 System Control register.|
|Mode exit|If WFI was used for entry:<br>Interrupt: Refer to_Table 35: STM32F334xx vector table_<br>If WFE was used for entry<br>Wakeup event: Refer to_Section 12.2.3: Wakeup event management_|
|Wakeup latency|None|


**Table 16. Sleep-on-exit**







|Sleep-on-exit|Description|
|---|---|
|Mode entry|WFI (wait for interrupt) while:<br>– SLEEPDEEP = 0 and<br>– SLEEPONEXIT = 1<br>Refer to the Cortex-M4 System Control register.|
|Mode exit|Interrupt: refer to_Table 35: STM32F334xx vector table_.|
|Wakeup latency|None|


**6.3.4** **Stop mode**


The Stop mode is based on the Cortex-M4 deepsleep mode combined with peripheral clock
gating. The voltage regulator can be configured either in normal or low-power mode in the
STM32F334xx devices. In the Stop mode, all I/O pins keep the same state as in the Run
mode.


88/1124 RM0364 Rev 4


**RM0364** **Power control (PWR)**


**Entering Stop mode**


Refer to _Table 17_ for details on how to enter the Stop mode.


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
_Section 24.3: IWDG functional description_ in _Section 24: Independent watchdog_
_(IWDG)_ .


      - real-time clock (RTC): this is configured by the RTCEN bit in the _RTC domain control_
_register (RCC_BDCR)_


      - Internal RC oscillator (LSI RC): this is configured by the LSION bit in the _Control/status_
_register (RCC_CSR)_ .


      - External 32.768 kHz oscillator (LSE OSC): this is configured by the LSEON bit in the
_RTC domain control register (RCC_BDCR)_ .


The ADC or DAC can also consume power during the Stop mode, unless they are disabled
before entering it. To disable the ADC, the ADDIS bit must be set in the ADCx_CR register.
To disable the DAC, the ENx bit in the DAC_CR register must be written to 0.


Exiting Stop mode


Refer to _Table 17_ for more details on how to exit Stop mode.


When exiting Stop mode by issuing an interrupt or a wakeup event, the HSI RC oscillator is
selected as system clock.


When the voltage regulator operates in low-power mode, an additional startup delay is
incurred when waking up from Stop mode. By keeping the internal regulator ON during Stop
mode, the consumption is higher although the startup time is reduced.


RM0364 Rev 4 89/1124



95


**Power control (PWR)** **RM0364**







|Col1|Table 17. Stop mode|
|---|---|
|**Stop mode**|**Description**|
|Mode entry|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– Set SLEEPDEEP bit in Arm® Cortex®-M4 System Control register<br>– Clear PDDS bit in Power Control register (PWR_CR)<br>– Select the voltage regulator mode by configuring LPDS bit in PWR_CR<br>**Note:** To enter Stop mode, all EXTI Line pending bits (in_Pending register_<br>_(EXTI_PR1)_), all peripherals interrupt pending bits and RTC Alarm flag<br>must be reset. Otherwise, the Stop mode entry procedure is ignored and<br>program execution continues.<br>If the application needs to disable the external oscillator (external clock)<br>before entering Stop mode, the system clock source must be first switched<br>to HSI and then clear the HSEON bit.<br>Otherwise, if before entering Stop mode the HSEON bit is kept at 1, the<br>security system (CSS) feature must be enabled to detect any external<br>oscillator (external clock) failure and avoid a malfunction when entering<br>Stop mode.|
|Mode exit|If WFI was used for entry:<br>– Any EXTI Line configured in Interrupt mode (the corresponding EXTI<br>Interrupt vector must be enabled in the NVIC).<br>– Some specific communication peripherals (USART, I2C) interrupts, when<br>programmed in wakeup mode (the peripheral must be programmed in<br>wakeup mode and the corresponding interrupt vector must be enabled in<br>the NVIC).<br>Refer to_Table 35: STM32F334xx vector table_.<br>If WFE was used for entry:<br>Any EXTI Line configured in event mode. Refer to_Section 12.2.3:_<br>_Wakeup event management_|
|Wakeup latency|HSI RC wakeup time + regulator wakeup time from Low-power mode|


**6.3.5** **Standby mode**


The Standby mode allows to achieve the lowest power consumption. It is based on the
Cortex-M4 deepsleep mode, with the voltage regulator disabled. The 1.8 V domain is
consequently powered off. The PLL, the HSI oscillator and the HSE oscillator are also
switched off. SRAM and register contents are lost except for registers in the RTC domain
and Standby circuitry (see _Figure 6_ ).


**Entering Standby mode**


Refer to _Table 18_ for more details on how to enter Standby mode.


In Standby mode, the following features can be selected by programming individual control
bits:


      - Independent watchdog (IWDG): the IWDG is started by writing to its Key register or by
hardware option. Once started it cannot be stopped except by a reset. See


90/1124 RM0364 Rev 4


**RM0364** **Power control (PWR)**


_Section 24.3: IWDG functional description_ in _Section 24: Independent watchdog_
_(IWDG)_ .


      - real-time clock (RTC): this is configured by the RTCEN bit in the RTC domain control
register (RCC_BDCR)


      - Internal RC oscillator (LSI RC): this is configured by the LSION bit in the Control/status
register (RCC_CSR).


      - External 32.768 kHz oscillator (LSE OSC): this is configured by the LSEON bit in the
RTC domain control register (RCC_BDCR)


**Exiting Standby mode**


The microcontroller exits the Standby mode when an external reset (NRST pin), an IWDG
reset, a rising edge on the WKUP pin or the rising edge of an RTC alarm occurs (see
_Figure 323: RTC block diagram_ ). All registers are reset after wakeup from Standby except
for _Power control/status register (PWR_CSR)_ .


After waking up from Standby mode, program execution restarts in the same way as after a
Reset (boot pins sampling, vector reset is fetched, etc.). The SBF status flag in the _Power_
_control/status register (PWR_CSR)_ indicates that the MCU was in Standby mode.


Refer to _Table 18_ for more details on how to exit Standby mode.


**Table 18. Standby mode**







|Standby mode|Description|
|---|---|
|Mode entry|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– Set SLEEPDEEP in Cortex-M4 System Control register<br>– Set PDDS bit in Power Control register (PWR_CR)<br>– Clear WUF bit in Power Control/Status register (PWR_CSR)|
|Mode exit|WKUP pin rising edge, RTC alarm event’s rising edge, external Reset in<br>NRST pin, IWDG Reset.|
|Wakeup latency|Reset phase|


**I/O states in Standby mode**


In Standby mode, all I/O pins are high impedance except:


- Reset pad (still available)


- TAMPER pin if configured for tamper or calibration out


- WKUP pin, if enabled


**Debug mode**


By default, the debug connection is lost if the application puts the MCU in Stop or Standby
mode while the debug features are used. This is due to the fact that the Arm [®] Cortex [®] -M4
core is no longer clocked.


However, by setting some configuration bits in the DBGMCU_CR register, the software can
be debugged even when using the low-power modes extensively.


RM0364 Rev 4 91/1124



95


**Power control (PWR)** **RM0364**


**6.3.6** **Auto-wakeup from low-power mode**


The RTC can be used to wakeup the MCU from low-power mode without depending on an
external interrupt (Auto-wakeup mode). The RTC provides a programmable time base for
waking up from Stop or Standby mode at regular intervals. For this purpose, two of the three
alternative RTC clock sources can be selected by programming the RTCSEL[1:0] bits in the
_RTC domain control register (RCC_BDCR)_ :


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


92/1124 RM0364 Rev 4


**RM0364** **Power control (PWR)**

## **6.4 Power control registers**


The peripheral registers can be accessed by half-words (16-bit) or words (32-bit).


**6.4.1** **Power control register (PWR_CR)**


Address offset: 0x00


Reset value: 0x0000 0000 (reset by wakeup from Standby mode)

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7 6 5|Col10|Col11|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBP|PLS[2:0]|PLS[2:0]|PLS[2:0]|PVDE|CSBF|CWUF|PDDS|LPDS|
||||||||rw|rw|rw|rw|rw|rc_w1|rc_w1|rw|rw|



Bits 31:9 Reserved, must be kept at reset value.


Bit 8 **DBP** : Disable RTC domain write protection.

In reset state, the RTC and backup registers are protected against parasitic write
access. This bit must be set to enable write access to these registers.

0: Access to RTC and Backup registers disabled
1: Access to RTC and Backup registers enabled

_Note: If the HSE divided by 128 is used as the RTC clock, this bit must remain set_
_to 1._


Bits 7:5 **PLS[2:0]:** PVD level selection.

These bits are written by software to select the voltage threshold detected by the
Power Voltage Detector.

000: 2.2V

001: 2.3V

010: 2.4V

011: 2.5V

100: 2.6V

101: 2.7V

110: 2.8V

111: 2.9V

Notes:

1. Refer to the electrical characteristics of the datasheet for more details.

2. Once the PVD_LOCK is enabled (for CLASS B protection) the PLS[2:0] bits
cannot be programmed anymore.


Bit 4 **PVDE:** Power voltage detector enable.

This bit is set and cleared by software.

0: PVD disabled

1: PVD enabled


Bit 3 **CSBF** : Clear standby flag.

This bit is always read as 0.

0: No effect

1: Clear the SBF Standby Flag (write).


RM0364 Rev 4 93/1124



95


**Power control (PWR)** **RM0364**


Bit 2 **CWUF:** Clear wakeup flag.

This bit is always read as 0.

0: No effect

1: Clear the WUF Wakeup Flag **after 2 System clock cycles** . (write)


Bit 1 **PDDS** : Power down deepsleep.

This bit is set and cleared by software. It works together with the LPDS bit.

0: Enter Stop mode when the CPU enters Deepsleep. The regulator status
depends on the LPDS bit.
1: Enter Standby mode when the CPU enters Deepsleep.


Bit 0 **LPDS:** Low-power deepsleep.

This bit is set and cleared by software. It works together with the PDDS bit.

0: Voltage regulator on during Stop mode
1: Voltage regulator in low-power mode during Stop mode


**6.4.2** **Power control/status register (PWR_CSR)**


Address offset: 0x04


Reset value: 0x0000 0000 (not reset by wakeup from Standby mode)


Additional APB cycles are needed to read this register versus a standard APB read.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|EWUP3|EWUP2|EWUP1|Res.|Res.|Res.|Res.|Res.|PVDO|SBF|WUF|
||||||rw|rw|rw||||||r|r|r|



Bits 31:11 Reserved, must be kept at reset value.


Bit 10 **EWUP3:** Enable WKUP3 pin

This bit is set and cleared by software.

0: WKUP3 pin is used for general purpose I/O. An event on the WKUP3 pin does
not wakeup the device from Standby mode.
1: WKUP3 pin is used for wakeup from Standby mode and forced in input pull
down configuration (rising edge on WKUP3 pin wakes-up the system from
Standby mode).

_Note: This bit is reset by a system Reset._


Bit 9 **EWUP2:** Enable WKUP2 pin

This bit is set and cleared by software.

0: WKUP2 pin is used for general purpose I/O. An event on the WKUP2 pin does
not wakeup the device from Standby mode.
1: WKUP2 pin is used for wakeup from Standby mode and forced in input pull
down configuration (rising edge on WKUP2 pin wakes-up the system from
Standby mode).

_Note: This bit is reset by a system Reset._


94/1124 RM0364 Rev 4


**RM0364** **Power control (PWR)**


Bit 8 **EWUP1:** Enable WKUP1 pin

This bit is set and cleared by software.

0: WKUP1 pin is used for general purpose I/O. An event on the WKUP1 pin does
not wakeup the device from Standby mode.
1: WKUP1 pin is used for wakeup from Standby mode and forced in input pull
down configuration (rising edge on WKUP1 pin wakes-up the system from
Standby mode).

_Note: This bit is reset by a system Reset._


Bits 7:3 Reserved, must be kept at reset value.


Bit 2 **PVDO:** PVD output

This bit is set and cleared by hardware. It is valid only if PVD is enabled by the
PVDE bit.

0: V DD /V DDA is higher than the PVD threshold selected with the PLS[2:0] bits.
1: V DD /V DDA is lower than the PVD threshold selected with the PLS[2:0] bits.

Notes:

1. The PVD is stopped by Standby mode. For this reason, this bit is equal to 0
after Standby or reset until the PVDE bit is set.

2. Once the PVD is enabled and configured in the PWR_CR register, PVDO can
be used to generate an interrupt through the External Interrupt controller.

3. Once the PVD_LOCK is enabled (for CLASS B protection) PVDO cannot be
disabled anymore.


Bit 1 **SBF:** Standby flag

This bit is set by hardware and cleared only by a POR/PDR (power on reset/power
down reset) or by setting the CSBF bit in the _Power control register (PWR_CR)_


0: Device has not been in Standby mode
1: Device has been in Standby mode


Bit 0 **WUF:** Wakeup flag

This bit is set by hardware and cleared by a system reset or by setting the CWUF
bit in the _Power control register (PWR_CR)_


0: No wakeup event occurred
1: A wakeup event was received from the WKUP pin or from the RTC alarm

_Note: An additional wakeup event is detected if the WKUP pin is enabled (by_
_setting the EWUP bit) when the WKUP pin level is already high._


**6.4.3** **PWR register map**


**Table 19. PWR register map and reset values**







|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x000|**PWR_CR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBP|PLS[2:0]|PLS[2:0]|PLS[2:0]|PVDE|CSBF|CWUF|PDDS|LPDS|
|0x000|Reset value||||||||||||||||||||||||0|0|0|0|0|0|0|0|0|
|0x004|**PWR_CSR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EWUP3|EWUP2|EWUP1|Res.|Res.|Res.|Res.|Res.|PVDO|SBF|WUF|
|0x004|Reset value||||||||||||||||||||||0|0|0||||||0|0|0|


Refer to _Section 2.2 on page 47_ for the register boundary addresses.


RM0364 Rev 4 95/1124



95


