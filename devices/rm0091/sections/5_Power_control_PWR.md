**RM0091** **Power control (PWR)**

# **5 Power control (PWR)**

## **5.1 Power supplies**


The STM32F0x1/F0x2 subfamily embeds a voltage regulator in order to supply the internal
1.8 V digital power domain, unlike the STM32F0x8 subfamily where the stable 1.8 V must
be delivered by the application.


      - The STM32F0x1/F0x2 devices require a 2.0 V - 3.6 V operating supply voltage (V DD )
and a 2.0 V - 3.6 V analog supply voltage (V DDA ).


      - The STM32F0x8 devices require a 1.8 V ± 8% operating supply voltage (V DD ), and a
1.65 V - 3.6 V analog supply voltage (V DDA ).


The real-time clock (RTC) and backup registers can be powered from the V BAT voltage
when the main V DD supply is powered off.


**Figure 6. Power supply overview**


































|Col1|VDDIO2 domain (1)|
|---|---|
||I/O ring<br><br>VDDIO2|
|||


|Col1|VDDIO2 domain (1)|
|---|---|
||I/O ring<br><br>VDDIO2|
|||

























1. Available only on STM32F04x, STM32F07x and STM32F09x devices.


RM0091 Rev 10 81/1017



94


**Power control (PWR)** **RM0091**


**5.1.1** **Independent A/D and D/A converter supply and reference voltage**


To improve conversion accuracy and to extend the supply flexibility, the ADC and the DAC
have an independent power supply that can be separately filtered and shielded from noise
on the PCB.


      - The ADC and DAC voltage supply input is available on a separate V DDA pin.


      - An isolated supply ground connection is provided on pin V SSA .


The V DDA supply/reference voltage must be equal or higher than V DD .


When a single supply is used, V DDA can be externally connected to V DD, through the
external filtering circuit in order to ensure a noise free V DDA reference voltage.


When V DDA is different from V DD, V DDA must always be higher or equal to V DD . To keep
safe potential difference in between V DDA and V DD during power-up/power-down, an
external Shottky diode may be used between V DD and V DDA . Refer to the datasheet for the
maximum allowed difference.


**5.1.2** **Independent I/O supply rail**


For better supply flexibility on STM32F04x, STM32F07x and STM32F09x devices, portions
of the I/Os are supplied from a separate supply rail. Power supply for this rail can range from
1.65 to 3.6 V and is provided externally through the VDDIO2 pin. The V DDIO2 voltage level is
completely independent from V DD or V DDA, but it must not be provided without a valid
operating supply on the V DD pin. Refer to the pinout diagrams or tables in related device
datasheets for concerned I/Os list.


The V DDIO2 supply is monitored and compared with the internal reference voltage (V REFINT ).
When the V DDIO2 is below this threshold, all the I/Os supplied from this rail are disabled by
hardware. The output of this comparator is connected to EXTI line 31 and it can be used to
generate an interrupt.


**5.1.3** **Battery backup domain**


To retain the content of the Backup registers and supply the whole RTC domain when V DD is
turned off, V BAT pin can be connected to an optional standby voltage supplied by a battery
or by another source.


The V BAT pin powers the RTC unit, the LSE oscillator and the PC13 to PC15 IOs, allowing
the RTC to operate even when the main power supply is turned off. The switch to the V BAT
supply is controlled by the Power Down Reset embedded in the Reset block or (on
STM32F0x8 devices) by the external NPOR signal.


**Warning: During** **t** **RSTTEMPO** **(temporization at V** **DD** **startup) or after a PDR is**
**detected, the power switch between V** **BAT** **and V** **DD** **remains connected**
**to V** **BAT** **.**
**During the startup phase, if V** **DD** **is established in less than t** **RSTTEMPO**
**(Refer to the datasheet for the value of t** **RSTTEMPO** **) and V** **DD** **> V** **BAT** **+**
**0.6 V, a current may be injected into V** **BAT** **through an internal diode**
**connected between V** **DD** **and the power switch (V** **BAT** **).**
**If the power supply/battery connected to the V** **BAT** **pin cannot support**


82/1017 RM0091 Rev 10


**RM0091** **Power control (PWR)**


**this current injection, it is strongly recommended to connect an**
**external low-drop diode between this power supply and the V** **BAT** **pin.**


If no external battery is used in the application, it is recommended to connect V BAT
externally to V DD with a 100 nF external ceramic decoupling capacitor (for more details refer
to AN4080).


When the RTC domain is supplied by V DD (analog switch connected to V DD ), the following
functions are available:


      - PC13, PC14 and PC15 can be used as GPIO pins


      - PC13, PC14 and PC15 can be configured by RTC or LSE (refer to _Section 25.4: RTC_
_functional description on page 591_ )


_Note:_ _Due to the fact that the analog switch can transfer only a limited amount of current (3 mA),_
_the use of GPIOs PC13 to PC15 in output mode is restricted: the speed has to be limited to_
_2 MHz with a maximum load of 30 pF and these IOs must not be used as a current source_
_(e.g. to drive an LED)._


When the RTC domain is supplied by V BAT (analog switch connected to V BAT because V DD
is not present), the following functions are available:


      - PC13, PC14 and PC15 can be controlled only by RTC or LSE (refer to _Section 25.4:_
_RTC functional description on page 591_ )


**5.1.4** **Voltage regulator**


The voltage regulator is always enabled after Reset. It works in three different modes
depending on the application modes.


      - In Run mode, the regulator supplies full power to the 1.8 V domain (core, memories
and digital peripherals).


      - In Stop mode the regulator supplies low-power to the 1.8 V domain, preserving
contents of registers and SRAM


      - In Standby Mode, the regulator is powered off. The contents of the registers and SRAM
are lost except for the Standby circuitry and the RTC domain.


_Note:_ _In STM32F0x8 devices, the voltage regulator is bypassed and the microcontroller must be_
_powered from a nominal V_ _DD_ _= 1.8 V ±8% supply._

## **5.2 Power supply supervisor**


**5.2.1** **Power on reset (POR) / power down reset (PDR)**


STM32F0x1xx and STM32F0x2xx devices feature integrated power-on reset (POR) and
power-down reset (PDR) circuits, which are always active and ensure proper operation
above a threshold of 2 V.


RM0091 Rev 10 83/1017



94


**Power control (PWR)** **RM0091**


The devices remain in Reset mode when the monitored supply voltage is below a specified
threshold, V POR/PDR, without the need for an external reset circuit.


      - The POR monitors only the V DD supply voltage. During the startup phase V DDA must
arrive first and be greater than or equal to V DD.

      - The PDR monitors both the V DD and V DDA supply voltages. However, the V DDA power
supply supervisor can be disabled (by programming a dedicated option bit
V DDA_MONITOR ) to reduce the power consumption if the application is designed to
make sure that V DDA is higher than or equal to V DD .


For more details on the power on / power down reset threshold, refer to the electrical
characteristics section in the datasheet.


**Figure 7. Power on reset/power down reset waveform**









**External NPOR signal**





In STM32F0x8 devices, the PB2 I/O (or PB1 on small packages) is not available and is
replaced by the NPOR functionality used for power on reset.


To guarantee a proper power on and power down reset to the device, the NPOR pin must be
held low until V DD is stable or before turning off the supply. When V DD is stable, the reset
state can be exited by putting the NPOR pin in high impedance. The NPOR pin has an
internal pull-up connected to V DDA .


**5.2.2** **Programmable voltage detector (PVD)**


STM32F0x1xx and STM32F0x2xx can use the PVD to monitor the V DD power supply by
comparing it to a threshold selected by the PLS[2:0] bits in the _Power control register_
_(PWR_CR)_ .


The PVD is enabled by setting the PVDE bit.


A PVDO flag is available, in the _Power control/status register (PWR_CSR)_, to indicate if V DD
is higher or lower than the PVD threshold. This event is internally connected to the EXTI
line16 and can generate an interrupt if enabled through the EXTI registers. The PVD output
interrupt can be generated when V DD drops below the PVD threshold and/or when V DD


84/1017 RM0091 Rev 10


**RM0091** **Power control (PWR)**


rises above the PVD threshold depending on EXTI line16 rising/falling edge configuration.
As an example the service routine could perform emergency shutdown tasks.


**Figure 8. PVD thresholds**






## **5.3 Low-power modes**



By default, the microcontroller is in Run mode after a system or a power Reset. Several lowpower modes are available to save power when the CPU does not need to be kept running,
for example when waiting for an external event. It is up to the user to select the mode that
gives the best compromise between low-power consumption, short startup time and
available wake-up sources.


The device features three low-power modes:

- Sleep mode (CPU clock off, all peripherals including Cortex [®] -M0 core peripherals like
NVIC, SysTick, etc. are kept running)


- Stop mode (all clocks are stopped)


- Standby mode (1.8V domain powered-off)


In addition, the power consumption in Run mode can be reduce by one of the following

means:


- Slowing down the system clocks


- Gating the clocks to the APB and AHB peripherals when they are unused.


RM0091 Rev 10 85/1017



94


**Power control (PWR)** **RM0091**


**Table 13. Low-power mode summary**
























|Mode name|Entry|Wake-up|Effect on 1.8 V<br>domain clocks|Effect on<br>V<br>DD<br>domain<br>clocks|Voltage<br>regulator|
|---|---|---|---|---|---|
|Sleep<br>(Sleep now or<br>Sleep-on -<br>exit)|WFI|Any interrupt|CPU clock OFF<br>no effect on other<br>clocks or analog<br>clock sources|None|ON|
|Sleep<br>(Sleep now or<br>Sleep-on -<br>exit)|WFE|Wake-up event|Wake-up event|Wake-up event|Wake-up event|
|Stop|PDDS and LPDS<br>bits +<br>SLEEPDEEP bit<br>+ WFI or WFE|Any EXTI line<br>(configured in the<br>EXTI registers)<br>Specific<br>communication<br>peripherals on<br>reception events<br>(CEC, USART,<br>I2C)|All 1.8V domain<br>clocks OFF|HSI and<br>HSE<br>oscillators<br>OFF|ON or in low-<br>power mode<br>(depends on<br>_Power control_<br>_register_<br>_(PWR_CR)_)|
|Standby|PDDS bit +<br>SLEEPDEEP bit<br>+ WFI or WFE|WKUP pin rising<br>edge, RTC alarm,<br>external reset in<br>NRST pin, <br>IWDG reset|WKUP pin rising<br>edge, RTC alarm,<br>external reset in<br>NRST pin, <br>IWDG reset|WKUP pin rising<br>edge, RTC alarm,<br>external reset in<br>NRST pin, <br>IWDG reset|OFF|



**Caution:** On STM32F0x8 devices, the Stop mode is available, but it is meaningless to distinguish
between voltage regulator in low-power mode and voltage regulator in Run mode because
the regulator is not used and the core is supplied directly from an external source.
Consequently, the Standby mode is not available on those devices.


**5.3.1** **Slowing down system clocks**


In Run mode the speed of the system clocks (SYSCLK, HCLK, PCLK) can be reduced by
programming the prescaler registers. These prescalers can also be used to slow down
peripherals before entering Sleep mode.


For more details refer to _Section 6.4.2: Clock configuration register (RCC_CFGR)_ .


86/1017 RM0091 Rev 10


**RM0091** **Power control (PWR)**


**5.3.2** **Peripheral clock gating**


In Run mode, the AHB clock (HCLK) and the APB clock (PCLK) for individual peripherals
and memories can be stopped at any time to reduce power consumption.


To further reduce power consumption in Sleep mode the peripheral clocks can be disabled
prior to executing the WFI or WFE instructions.


Peripheral clock gating is controlled by the _AHB peripheral clock enable register_
_(RCC_AHBENR)_, the _APB peripheral clock enable register 2 (RCC_APB2ENR)_ and the
_APB peripheral clock enable register 1 (RCC_APB1ENR)_ .


**5.3.3** **Sleep mode**


**Entering Sleep mode**


The Sleep mode is entered by executing the WFI (Wait For Interrupt) or WFE (Wait for
Event) instructions. Two options are available to select the Sleep mode entry mechanism,
depending on the SLEEPONEXIT bit in the Cortex [®] -M0 System Control register:


      - Sleep-now: if the SLEEPONEXIT bit is cleared, the MCU enters Sleep mode as soon
as WFI or WFE instruction is executed.


      - Sleep-on-exit: if the SLEEPONEXIT bit is set, the MCU enters Sleep mode as soon as
it exits the lowest priority ISR.


In the Sleep mode, all I/O pins keep the same state as in the Run mode.


Refer to _Table 14_ and _Table 15_ for details on how to enter Sleep mode.


**Exiting Sleep mode**


If the WFI instruction is used to enter Sleep mode, any peripheral interrupt acknowledged by
the nested vectored interrupt controller (NVIC) can wake up the device from Sleep mode.


If the WFE instruction is used to enter Sleep mode, the MCU exits Sleep mode as soon as
an event occurs. The wake-up event can be generated either by:


      - enabling an interrupt in the peripheral control register but not in the NVIC, and enabling
the SEVONPEND bit in the Cortex [®] -M0 System Control register. When the MCU
resumes from WFE, the peripheral interrupt pending bit and the peripheral NVIC IRQ
channel pending bit (in the NVIC interrupt clear pending register) must be cleared.


      - or configuring an external or internal EXTI line in event mode. When the CPU resumes
from WFE, it is not necessary to clear the peripheral interrupt pending bit or the NVIC
IRQ channel pending bit as the pending bit corresponding to the event line is not set.


This mode offers the lowest wake-up time as no time is wasted in interrupt entry/exit.


Refer to _Table 14_ and _Table 15_ for more details on how to exit Sleep mode.


RM0091 Rev 10 87/1017



94


**Power control (PWR)** **RM0091**








|Col1|Table 14. Sleep-now|
|---|---|
|**Sleep-now mode**|**Description**|
|**Mode entry**|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– SLEEPDEEP = 0 and<br>– SLEEPONEXIT = 0<br>Refer to the Cortex®-M0 System Control register.|
|**Mode exit**|If WFI was used for entry:<br>Interrupt: Refer to_Table 36: Vector table_<br>If WFE was used for entry<br>Wake-up event: Refer to_Section 11.2.3: Event management_|
|**Wake-up latency**|None|







|Col1|Table 15. Sleep-on-exit|
|---|---|
|**Sleep-on-exit**|**Description**|
|**Mode entry**|WFI (wait for interrupt) while:<br>– SLEEPDEEP = 0 and<br>– SLEEPONEXIT = 1<br>Refer to the Cortex®-M0 System Control register.|
|**Mode exit**|Interrupt: Refer to_Table 36: Vector table_.|
|**Wake-up latency**|None|


**5.3.4** **Stop mode**


The Stop mode is based on the Cortex [®] -M0 deep sleep mode combined with peripheral
clock gating. The voltage regulator can be configured either in normal or low-power mode.
In Stop mode, all clocks in the 1.8 V domain are stopped, the PLL, the HSI and the HSE
oscillators are disabled. SRAM and register contents are preserved.


In the Stop mode, all I/O pins keep the same state as in the Run mode.


**Entering Stop mode**


Refer to _Table 16_ for details on how to enter the Stop mode.


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
_Section 23.3: IWDG functional description_ .


88/1017 RM0091 Rev 10


**RM0091** **Power control (PWR)**


      - real-time clock (RTC): this is configured by the RTCEN bit in the _RTC domain control_
_register (RCC_BDCR)_


      - Internal RC oscillator (LSI): this is configured by the LSION bit in the _Control/status_
_register (RCC_CSR)_ .


      - External 32.768 kHz oscillator (LSE): this is configured by the LSEON bit in the _RTC_
_domain control register (RCC_BDCR)_ .


The ADC or DAC can also consume power during Stop mode, unless they are disabled
before entering this mode. Refer to _ADC control register (ADC_CR)_ and _DAC control_
_register (DAC_CR)_ for details on how to disable them.


**Exiting Stop mode**


Refer to _Table 16_ for more details on how to exit Stop mode.


When exiting Stop mode by issuing an interrupt or a wake-up event, the HSI oscillator is
selected as system clock.


When the voltage regulator operates in low-power mode, an additional startup delay is
incurred when waking up from Stop mode. By keeping the internal regulator ON during Stop
mode, the consumption is higher although the startup time is reduced.







|Col1|Table 16. Stop mode|
|---|---|
|**Stop mode**|**Description**|
|**Mode entry**|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– Set SLEEPDEEP bit in Cortex®-M0 System Control register<br>– Clear PDDS bit in Power Control register (PWR_CR)<br>– Select the voltage regulator mode by configuring LPDS bit in PWR_CR<br>**Note:** To enter Stop mode, all EXTI line pending bits (in_Pending register_<br>_(EXTI_PR)_), all peripherals interrupt pending bits and RTC Alarm flag must<br>be reset. Otherwise, the Stop mode entry procedure is ignored and<br>program execution continues.<br>If the application needs to disable the external oscillator (external clock)<br>before entering Stop mode, the system clock source must be first switched<br>to HSI and then clear the HSEON bit.<br>Otherwise, if before entering Stop mode the HSEON bit is kept at 1, the<br>security system (CSS) feature must be enabled to detect any external<br>oscillator (external clock) failure and avoid a malfunction when entering<br>Stop mode.|
|**Mode exit**|If WFI was used for entry:<br>– Any EXTI line configured in Interrupt mode (the corresponding EXTI<br>Interrupt vector must be enabled in the NVIC).<br>– Some specific communication peripherals (CEC, USART, I2C) interrupts,<br>when programmed in wake-up mode (the peripheral must be<br>programmed in wake-up mode and the corresponding interrupt vector<br>must be enabled in the NVIC).<br>Refer to_Table 36: Vector table_.<br>If WFE was used for entry:<br>Any EXTI line configured in event mode. Refer to_Section 11.2.3: Event_<br>_management on page 218_|
|**Wake-up latency**|HSI wake-up time + regulator wake-up time from Low-power mode|


RM0091 Rev 10 89/1017



94


**Power control (PWR)** **RM0091**


**5.3.5** **Standby mode**


The Standby mode allows to achieve the lowest power consumption. It is based on the
Cortex [®] -M0 deepsleep mode, with the voltage regulator disabled. The 1.8 V domain is
consequently powered off. The PLL, the HSI oscillator and the HSE oscillator are also
switched off. SRAM and register contents are lost except for registers in the RTC domain
and Standby circuitry (see _Figure 6_ ).


**Caution:** The Standby mode is not available on STM32F0x8 devices.


**Entering Standby mode**


Refer to _Table 17_ for more details on how to enter Standby mode.


In Standby mode, the following features can be selected by programming individual control
bits:


      - Independent watchdog (IWDG): the IWDG is started by writing to its Key register or by
hardware option. Once started it cannot be stopped except by a reset. See
_Section 23.3: IWDG functional description_ .


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


Refer to _Table 17_ for more details on how to exit Standby mode.







|Col1|Table 17. Standby mode|
|---|---|
|**Standby mode**|**Description**|
|**Mode entry**|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– Set SLEEPDEEP in Cortex®-M0 System Control register<br>– Set PDDS bit in Power Control register (PWR_CR)<br>– Clear WUF bit in Power Control/Status register (PWR_CSR)|
|**Mode exit**|WKUP pin rising edge, RTC alarm event’s rising edge, external Reset in<br>NRST pin, IWDG Reset.|
|**Wake-up latency**|Reset phase|


90/1017 RM0091 Rev 10


**RM0091** **Power control (PWR)**


**I/O states in Standby mode**


In Standby mode, all I/O pins are high impedance except:


      - Reset pad (still available)


      - PC13, PC14 and PC15 if configured by RTC or LSE


      - WKUPx pins


**Debug mode**


By default, the debug connection is lost if the application puts the MCU in Stop or Standby
mode while the debug features are used. This is due to the fact that the Cortex [®] -M0 core is
no longer clocked.


However, by setting some configuration bits in the DBGMCU_CR register, the software can
be debugged even when using the low-power modes extensively.


**5.3.6** **Auto-wake-up from low-power mode**


The RTC can be used to wake-up the MCU from low-power mode by means of the RTC
alarm.from low-power mode without depending on an external interrupt (Auto-wake-up
mode). The RTC provides a programmable time base for waking up from Stop or Standby
mode at regular intervals. For this purpose, two of the three alternative RTC clock sources
can be selected by programming the RTCSEL[1:0] bits in the _RTC domain control register_
_(RCC_BDCR)_ :


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


RM0091 Rev 10 91/1017



94


**Power control (PWR)** **RM0091**

## **5.4 Power control registers**


The peripheral registers can be accessed by half-words (16-bit) or words (32-bit).


**5.4.1** **Power control register (PWR_CR)**


Address offset: 0x00


Reset value: 0x0000 0000 (reset by wake-up from Standby mode)

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7 6 5|Col10|Col11|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res|Res|Res|Res|Res|Res|Res|DBP|PLS[2:0]|PLS[2:0]|PLS[2:0]|PVDE|CSBF|CWUF|PDDS|LPDS|
||||||||rw|rw|rw|rw|rw|rc_w1|rc_w1|rw|rw|



Bits 31:9 Reserved, must be kept at reset value.


Bit 8 **DBP** : Disable RTC domain write protection.

In reset state, the RTC and backup registers are protected against parasitic write access. This
bit must be set to enable write access to these registers.

0: Access to RTC and Backup registers disabled
1: Access to RTC and Backup registers enabled


Bits 7:5 **PLS[2:0]:** PVD level selection.

These bits are written by software to select the voltage threshold detected by the Power
Voltage Detector.

Once the PVD_LOCK is enabled in the _SYSCFG configuration register 2 (SYSCFG_CFGR2)_,
the PLS[2:0] bits cannot be programmed anymore.

000: PVD threshold 0

001: PVD threshold 1

010: PVD threshold 2

011: PVD threshold 3

100: PVD threshold 4

101: PVD threshold 5

110: PVD threshold 6

111: PVD threshold 7

Refer to the electrical characteristics of the datasheet for more details.


Bit 4 **PVDE:** Power voltage detector enable.

This bit is set and cleared by software. Once the PVD_LOCK is enabled in the _SYSCFG_
_configuration register 2 (SYSCFG_CFGR2)_ register, the PVDE bit cannot be programmed

anymore.

0: PVD disabled

1: PVD enabled


Bit 3 **CSBF** : Clear standby flag.

This bit is always read as 0.

0: No effect

1: Clear the SBF standby flag (write).


92/1017 RM0091 Rev 10


**RM0091** **Power control (PWR)**


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


**5.4.2** **Power control/status register (PWR_CSR)**


Address offset: 0x04


Reset value: 0x0000 000X (not reset by wake-up from Standby mode)


Additional APB cycles are needed to read this register versus a standard APB read.


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|
|||||||||||||||||







|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EWUP<br>8|EWUP<br>7|EWUP<br>6|EWUP<br>5|EWUP<br>4|EWUP<br>3|EWUP<br>2|EWUP<br>1|Res|Res|Res|Res|VREF<br>INT<br>RDY|PVDO|SBF|WUF|
|rw|rw|rw|rw|rw|rw|rw|rw|||||r|r|r|r|


Bits 31:16 Reserved, must be kept at reset value.


Bits 15:8 **EWUPx:** Enable WKUPx pin

These bits are set and cleared by software.

0: WKUPx pin is used for general purpose I/O. An event on the WKUPx pin does not wakeup the device from Standby mode.
1: WKUPx pin is used for wake-up from Standby mode and forced in input pull down
configuration (rising edge on WKUPx pin wakes-up the system from Standby mode).

_Note: These bits are reset by a system Reset._


Bits 7:4 Reserved, must be kept at reset value.


RM0091 Rev 10 93/1017



94


**Power control (PWR)** **RM0091**


Bit 3 **VREFINTRDY:** VREFINT reference voltage ready

This bit is set and cleared by hardware to indicate the state of the internal voltage reference
VREFINT.

0: VREFINT is not ready
1: VREFINT is ready

_Note: This flag is useful only for STM32F0x8 devices where POR is provided externally_
_(through the NPOR pin). In STM32F0x1/F0x2 devices, the internal POR waits for_
_VREFINT to stabilize before releasing the reset._


Bit 2 **PVDO:** PVD output

This bit is set and cleared by hardware. It is valid only if PVD is enabled by the PVDE bit.

0: V DD is higher than the PVD threshold selected with the PLS[2:0] bits.
1: V DD is lower than the PVD threshold selected with the PLS[2:0] bits.

Notes:

1. The PVD is stopped by Standby mode. For this reason, this bit is equal to 0 after Standby
or reset until the PVDE bit is set.

2. Once the PVD is enabled and configured in the PWR_CR register, PVDO can be used to
generate an interrupt through the external interrupt controller.


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


**5.4.3** **PWR register map**


The following table summarizes the PWR register map and reset values.


**Table 18. PWR register map and reset values**







|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x000|**PWR_CR**<br><br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.|DBP<br>|PLS[2:0]<br><br><br>|PLS[2:0]<br><br><br>|PLS[2:0]<br><br><br>|PVDE<br>|CSBF<br>|CWUF<br>|PDDS<br>|LPDS<br>|
|0x000|~~Reset value~~||||||||||||||||||||||||~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x004|**PWR_CSR**<br><br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.<br>|Res.|EWUP8<br>|EWUP7<br>|EWUP6<br>|EWUP5<br>|EWUP4<br>|EWUP3<br>|EWUP2<br>|EWUP1<br><br>|Res.<br>|Res.<br>|Res.<br>|Res.|VREFINTRDY<br>|PVDO<br>|SBF<br>|WUF<br>|
|0x004|~~Reset value~~|||||||||||||||||~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|||||~~X~~|~~0~~|~~0~~|~~0~~|


Refer to _Section 2.2 on page 46_ for the register boundary addresses.


94/1017 RM0091 Rev 10


