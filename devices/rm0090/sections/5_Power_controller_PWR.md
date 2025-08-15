**RM0090** **Power controller (PWR)**

# **5 Power controller (PWR)**



This section applies to the whole STM32F4xx family, unless otherwise specified.

## **5.1 Power supplies**


The device requires a 1.8 to 3.6 V operating voltage supply (V DD ). An embedded linear
voltage regulator is used to supply the internal 1.2 V digital power.


The real-time clock (RTC), the RTC backup registers, and the backup SRAM (BKP SRAM)
can be powered from the V BAT voltage when the main V DD supply is powered off.


_Note:_ _Depending on the operating power supply range, some peripheral may be used with limited_
_functionality and performance. For more details refer to section “General operating_
_conditions” in STM32F4xx datasheets._


**Figure 9. Power supply overview for STM32F405xx/07xx and STM32F415xx/17xx**



































1. V DDA and V SSA must be connected to V DD and V SS, respectively.


RM0090 Rev 21 117/1757



151


**Power controller (PWR)** **RM0090**


**Figure 10. Power supply overview for STM32F42xxx and STM32F43xxx**


























|Voltage<br>regulator|Col2|
|---|---|
|||
|||

















|Col1|Col2|Col3|
|---|---|---|
|VREF+|||
|VREF+|||
|VSSA|||


1. V DDA and V SSA must be connected to V DD and V SS, respectively.


**5.1.1** **Independent A/D converter supply and reference voltage**





To improve conversion accuracy, the ADC has an independent power supply which can be
separately filtered and shielded from noise on the PCB.


      - The ADC voltage supply input is available on a separate VDDA pin.


      - An isolated supply ground connection is provided on VSSA pin.


To ensure a better accuracy of low voltage inputs, the user can connect a separate external
reference voltage ADC input on V REF . The voltage on V REF ranges from 1.8 V to V DDA .


118/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


**5.1.2** **Battery backup domain**


**Backup domain description**


To retain the content of the RTC backup registers, backup SRAM, and supply the RTC when
V DD is turned off, VBAT pin can be connected to an optional standby voltage supplied by a
battery or by another source.


To allow the RTC to operate even when the main digital supply (V DD ) is turned off, the VBAT
pin powers the following blocks:


      - The RTC


      - The LSE oscillator


      - The backup SRAM when the low-power backup regulator is enabled


      - PC13 to PC15 I/Os, plus PI8 I/O (when available)


The switch to the V BAT supply is controlled by the power-down reset embedded in the Reset
block.


**Warning:** **During** **t** **RSTTEMPO** **(temporization at V** **DD** **startup) or after a PDR**
**is detected, the power switch between V** **BAT** **and V** **DD** **remains**
**connected to V** **BAT** **.**
**During the startup phase, if V** **DD** **is established in less than**
**t** **RSTTEMPO** **(Refer to the datasheet for the value of t** **RSTTEMPO** **)**
**and V** **DD** **> V** **BAT** **+ 0.6 V, a current may be injected into V** **BAT**
**through an internal diode connected between V** **DD** **and the**
**power switch (V** **BAT** **).**
**If the power supply/battery connected to the VBAT pin cannot**
**support this current injection, it is strongly recommended to**
**connect an external low-drop diode between this power**
**supply and the VBAT pin.**


If no external battery is used in the application, it is recommended to connect the VBAT pin
to V DD supply, and add a 100 nF external decoupling ceramic capacitor on VBAT pin.


When the backup domain is supplied by V DD (analog switch connected to V DD ), the
following functions are available:


      - PC14 and PC15 can be used as either GPIO or LSE pins


      - PC13 can be used as a GPIOas the RTC_AF1 pin (refer to _Table 38: RTC_AF1 pin_ for
more details about this pin configuration)


_Note:_ _Due to the fact that the switch only sinks a limited amount of current (3 mA), the use of PI8_
_and PC13 to PC15 GPIOs in output mode is restricted: the speed has to be limited to 2 MHz_
_with a maximum load of 30 pF and these I/Os must not be used as a current source (e.g. to_
_drive an LED)._


RM0090 Rev 21 119/1757



151


**Power controller (PWR)** **RM0090**


When the backup domain is supplied by V BAT (analog switch connected to V BAT because
V DD is not present), the following functions are available:


      - PC14 and PC15 can be used as LSE pins only


      - PC13 can be used as the RTC_AF1 pin (refer to _Table 38: RTC_AF1 pin_ for more
details about this pin configuration)


      - PI8 can be used as RTC_AF2


**Backup domain access**


After reset, the backup domain (RTC registers, RTC backup register and backup SRAM) is
protected against possible unwanted write accesses. To enable access to the backup
domain, proceed as follows:


      - Access to the RTC and RTC backup registers


1. Enable the power interface clock by setting the PWREN bits in the RCC_APB1ENR
register (see _Section 7.3.13_ and _Section 6.3.13_ )


2. Set the DBP bit in the _Section 5.4.1_ and _PWR power control register (PWR_CR) for_
_STM32F42xxx and STM32F43xxx_ to enable access to the backup domain


3. Select the RTC clock source: see _Section 7.2.8: RTC/AWU clock_


4. Enable the RTC clock by programming the RTCEN [15] bit in the _Section 7.3.20: RCC_
_Backup domain control register (RCC_BDCR)_


      - Access to the backup SRAM


1. Enable the power interface clock by setting the PWREN bits in the RCC_APB1ENR
register (see _Section 7.3.13_ and _Section 6.3.13_ for STM32F405xx/07xx and
STM32F415xx/17xx and STM32F42xxx and STM32F43xxx, respectively)


2. Set the DBP bit in the _PWR power control register (PWR_CR) for STM32F405xx/07xx_
_and STM32F415xx/17xx_ and _PWR power control register (PWR_CR) for_
_STM32F42xxx and STM32F43xxx_ to enable access to the backup domain


3. Enable the backup SRAM clock by setting BKPSRAMEN bit in the _RCC AHB1_
_peripheral clock enable register (RCC_AHB1ENR)_ .


**RTC and RTC backup registers**


The real-time clock (RTC) is an independent BCD timer/counter. The RTC provides a timeof-day clock/calendar, two programmable alarm interrupts, and a periodic programmable
wake-up flag with interrupt capability. The RTC contains 20 backup data registers (80 bytes)
which are reset when a tamper detection event occurs. For more details refer to _Section 26:_
_Real-time clock (RTC)_ .


**Backup SRAM**


The backup domain includes 4 Kbytes of backup SRAM addressed in 32-bit, 16-bit or 8-bit
mode. Its content is retained even in Standby or V BAT mode when the low-power backup
regulator is enabled. It can be considered as an internal EEPROM when V BAT is always
present.


When the backup domain is supplied by V DD (analog switch connected to V DD ), the backup
SRAM is powered from V DD which replaces the V BAT power supply to save battery life.


When the backup domain is supplied by V BAT (analog switch connected to V BAT because
V DD is not present), the backup SRAM is powered by a dedicated low-power regulator. This
regulator can be ON or OFF depending whether the application needs the backup SRAM
function in Standby and V BAT modes or not. The power-down of this regulator is controlled


120/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


by a dedicated bit, the BRE control bit of the PWR_CSR register (see _Section 5.4.2: PWR_
_power control/status register (PWR_CSR) for STM32F405xx/07xx and_
_STM32F415xx/17xx_ ).


The backup SRAM is not mass erased by an tamper event. When the Flash memory is read
protected, the backup SRAM is also read protected to prevent confidential data, such as
cryptographic private key, from being accessed. When the protection level change from
level 1 to level 0 is requested, the backup SRAM content is erased.


**Figure 11. Backup domain**









**5.1.3** **Voltage regulator for STM32F405xx/07xx and STM32F415xx/17xx**


An embedded linear voltage regulator supplies all the digital circuitries except for the backup
domain and the Standby circuitry. The regulator output voltage is around 1.2 V.


This voltage regulator requires one or two external capacitors to be connected to one or two
dedicated pins, V CAP_1 and V CAP_2 available in all packages. Specific pins must be
connected either to V SS or V DD to activate or deactivate the voltage regulator. These pins
depend on the package.


When activated by software, the voltage regulator is always enabled after Reset. It works in
three different modes depending on the application modes.


      - In **Run mode**, the regulator supplies full power to the 1.2 V domain (core, memories
and digital peripherals). In this mode, the regulator output voltage (around 1.2 V) can
be scaled by software to different voltage values:


Scale 1 or scale 2 can be configured on the fly through VOS (bit 15 of the
PWR_CR register).


The voltage scaling allows optimizing the power consumption when the device is
clocked below the maximum system frequency.


      - In **Stop mode,** the main regulator or the low-power regulator supplies to the 1.2 V
domain, thus preserving the content of registers and internal SRAM. The voltage


RM0090 Rev 21 121/1757



151


**Power controller (PWR)** **RM0090**


regulator can be put either in main regulator mode (MR) or in low-power mode (LPR).
The programmed voltage scale remains the same during Stop mode:


The programmed voltage scale remains the same during Stop mode (see
_Section 5.4.1: PWR power control register (PWR_CR) for STM32F405xx/07xx_
_and STM32F415xx/17xx_ ).


      - In **Standby mode**, the regulator is powered down. The content of the registers and
SRAM are lost except for the Standby circuitry and the backup domain.


_Note:_ _For more details, refer to the voltage regulator section in the STM32F405xx/07xx and_
_STM32F415xx/17xx datasheets._


**5.1.4** **Voltage regulator for STM32F42xxx and STM32F43xxx**


An embedded linear voltage regulator supplies all the digital circuitries except for the backup
domain and the Standby circuitry. The regulator output voltage is around 1.2 V.


This voltage regulator requires two external capacitors to be connected to two dedicated
pins, VCAP_1 and VCAP_2 available in all packages. Specific pins must be connected
either to V SS or V DD to activate or deactivate the voltage regulator. These pins depend on
the package.


When activated by software, the voltage regulator is always enabled after Reset. It works in
three different modes depending on the application modes (Run, Stop, or Standby mode).


      - In **Run mode**, the main regulator supplies full power to the 1.2 V domain (core,
memories and digital peripherals). In this mode, the regulator output voltage (around
1.2 V) can be scaled by software to different voltage values (scale 1, scale 2, and scale
3 can be configured through VOS[1:0] bits of the PWR_CR register). The scale can be
modified only when the PLL is OFF and the HSI or HSE clock source is selected as
system clock source. The new value programmed is active only when the PLL is ON.
When the PLL is OFF, the voltage scale 3 is automatically selected.


The voltage scaling allows optimizing the power consumption when the device is
clocked below the maximum system frequency. After exit from Stop mode, the voltage


122/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


scale 3 is automatically selected.(see _Section 5.4.1: PWR power control register_
_(PWR_CR) for STM32F405xx/07xx and STM32F415xx/17xx_ .


2 operating modes are available:


– **Normal mode** : The CPU and core logic operate at maximum frequency at a given
voltage scaling (scale 1, scale 2 or scale 3)


– **Over-drive mode** : This mode allows the CPU and the core logic to operate at a
higher frequency than the normal mode for the voltage scaling scale 1 and scale
2.


      - In **Stop mode** : the main regulator or low-power regulator supplies a low-power voltage
to the 1.2V domain, thus preserving the content of registers and internal SRAM.


The voltage regulator can be put either in main regulator mode (MR) or in low-power
mode (LPR). Both modes can be configured by software as follows:


– **Normal mode** : the 1.2 V domain is preserved in nominal leakage mode. It is the
default mode when the main regulator (MR) or the low-power regulator (LPR) is
enabled.

– **Under-drive mode** : the 1.2 V domain is preserved in reduced leakage mode. This
mode is only available with the main regulator or in low-power regulator mode
(see _Table 23_ ).


      - In **Standby mode** : the regulator is powered down. The content of the registers and
SRAM are lost except for the Standby circuitry and the backup domain.


_Note:_ _Over-drive and under-drive mode are not available when the regulator is bypassed._


_For more details, refer to the voltage regulator section in the STM32F42xxx and_
_STM32F43xxx datasheets._


**Table 23. Voltage regulator configuration mode versus device operating mode** **(1)**







|Voltage regulator<br>configuration|Run mode|Sleep mode|Stop mode|Standby mode|
|---|---|---|---|---|
|Normal mode|MR|MR|MR or LPR|-|
|Over-drive<br>mode(2)|MR|MR|-|-|
|Under-drive mode|-|-|MR or LPR|-|
|Power-down<br>mode|-|-|-|Yes|


1. ‘-’ means that the corresponding configuration is not available.


2. The over-drive mode is not available when V DD = 1.8 to 2.1 V.


RM0090 Rev 21 123/1757



151


**Power controller (PWR)** **RM0090**


**Entering Over-drive mode**


It is recommended to enter Over-drive mode when the application is not running critical
tasks and when the system clock source is either HSI or HSE. To optimize the configuration
time, enable the Over-drive mode during the PLL lock phase.


To enter Over-drive mode, follow the sequence below:


1. Select HSI or HSE as system clock.


2. Configure RCC_PLLCFGR register and set PLLON bit of RCC_CR register.


3. Set ODEN bit of PWR_CR register to enable the Over-drive mode and wait for the
ODRDY flag to be set in the PWR_CSR register.


4. Set the ODSW bit in the PWR_CR register to switch the voltage regulator from Normal
mode to Over-drive mode. The System is stalled during the switch but the PLL clock
system is still running during locking phase.


5. Wait for the ODSWRDY flag in the PWR_CSR to be set.


6. Select the required Flash latency as well as AHB and APB prescalers.


7. Wait for PLL lock.


8. Switch the system clock to the PLL.


9. Enable the peripherals that are not generated by the System PLL (I2S clock, LCD-TFT
clock, SAI1 clock, USB_48MHz clock....).


_Note:_ _The PLLI2S and PLLSAI can be configured at the same time as the system PLL._


_During the Over-drive switch activation, no peripheral clocks should be enabled. The_
_peripheral clocks must be enabled once the Over-drive mode is activated._


_Entering Stop mode disables the Over-drive mode, as well as the PLL. The application_
_software has to configure again the Over-drive mode and the PLL after exiting from Stop_
_mode._


**Exiting from Over-drive mode**


It is recommended to exit from Over-drive mode when the application is not running critical
tasks and when the system clock source is either HSI or HSE.There are two sequences that
allow exiting from over-drive mode:


      - By resetting simultaneously the ODEN and ODSW bits bit in the PWR_CR register
(sequence 1)


      - By resetting first the ODSW bit to switch the voltage regulator to Normal mode and then
resetting the ODEN bit to disable the Over-drive mode (sequence 2).


Example of sequence 1:


1. Select HSI or HSE as system clock source.


2. Disable the peripheral clocks that are not generated by the System PLL (I2S clock,
LCD-TFT clock, SAI1 clock, USB_48MHz clock,....)


3. Reset simultaneously the ODEN and the ODSW bits in the PWR_CR register to switch
back the voltage regulator to Normal mode and disable the Over-drive mode.


4. Wait for the ODWRDY flag of PWR_CSR to be reset.


124/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


Example of sequence 2:


1. Select HSI or HSE as system clock source.


2. Disable the peripheral clocks that are not generated by the System PLL (I2S clock,
LCD-TFT clock, SAI1 clock, USB_48MHz clock,....).


3. Reset the ODSW bit in the PWR_CR register to switch back the voltage regulator to
Normal mode. The system clock is stalled during voltage switching.


4. Wait for the ODWRDY flag of PWR_CSR to be reset.


5. Reset the ODEN bit in the PWR_CR register to disable the Over-drive mode.


_Note:_ _During step 3, the ODEN bit remains set and the Over-drive mode is still enabled but not_
_active (ODSW bit is reset). If the ODEN bit is reset instead, the Over-drive mode is disabled_
_and the voltage regulator is switched back to the initial voltage._

## **5.2 Power supply supervisor**


**5.2.1** **Power-on reset (POR)/power-down reset (PDR)**


The device has an integrated POR/PDR circuitry that allows proper operation starting
from 1.8 V.


The device remains in Reset mode when V DD /V DDA is below a specified threshold,
V POR/PDR, without the need for an external reset circuit. For more details concerning the
power on/power-down reset threshold, refer to the electrical characteristics of the
datasheet.


**Figure 12. Power-on reset/power-down reset waveform**













RM0090 Rev 21 125/1757



151


**Power controller (PWR)** **RM0090**


**5.2.2** **Brownout reset (BOR)**


During power on, the Brownout reset (BOR) keeps the device under reset until the supply
voltage reaches the specified V BOR threshold.


V BOR is configured through device option bytes. By default, BOR is off. 3 programmable
V BOR threshold levels can be selected:


      - BOR Level 3 (VBOR3). Brownout threshold level 3.


      - BOR Level 2 (VBOR2). Brownout threshold level 2.


      - BOR Level 1 (VBOR1). Brownout threshold level 1.


_Note:_ _For full details about BOR characteristics, refer to the "Electrical characteristics" section in_
_the device datasheet._


When the supply voltage (V DD ) drops below the selected V BOR threshold, a device reset is
generated.


The BOR can be disabled by programming the device option bytes. In this case, the
power-on and power-down is then monitored by the POR/ PDR (see _Section 5.2.1: Power-_
_on reset (POR)/power-down reset (PDR)_ ).


The BOR threshold hysteresis is ~100 mV (between the rising and the falling edge of the







**5.2.3** **Programmable voltage detector (PVD)**





You can use the PVD to monitor the V DD power supply by comparing it to a threshold
selected by the PLS[2:0] bits in the _PWR power control register (PWR_CR) for_


126/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


_STM32F405xx/07xx and STM32F415xx/17xx_ and _PWR power control register (PWR_CR)_
_for STM32F42xxx and STM32F43xxx_ .


The PVD is enabled by setting the PVDE bit.


A PVDO flag is available, in the _PWR power control/status register (PWR_CSR) for_
_STM32F405xx/07xx and STM32F415xx/17xx_, to indicate if V DD is higher or lower than the
PVD threshold. This event is internally connected to the EXTI line16 and can generate an
interrupt if enabled through the EXTI registers. The PVD output interrupt can be generated
when V DD drops below the PVD threshold and/or when V DD rises above the PVD threshold
depending on EXTI line16 rising/falling edge configuration. As an example the service
routine could perform emergency shutdown tasks.


**Figure 14. PVD thresholds**











By default, the microcontroller is in Run mode after a system or a power-on reset. In Run
mode the CPU is clocked by HCLK and the program code is executed. Several low-power
modes are available to save power when the CPU does not need to be kept running, for
example when waiting for an external event. It is up to the user to select the mode that gives
the best compromise between low-power consumption, short startup time and available
wake-up sources.


The devices feature three low-power modes:

- Sleep mode (Cortex [®] -M4 with FPU core stopped, peripherals kept running)


- Stop mode (all clocks are stopped)


- Standby mode (1.2 V domain powered off)


RM0090 Rev 21 127/1757



151


**Power controller (PWR)** **RM0090**


In addition, the power consumption in Run mode can be reduce by one of the following

means:


      - Slowing down the system clocks


      - Gating the clocks to the APBx and AHBx peripherals when they are unused.


**Entering low-power mode**


Low-power modes are entered by the MCU by executing the WFI (Wait For Interrupt), or
WFE (Wait for Event) instructions, or when the SLEEPONEXIT bit in the Cortex [®] -M4 with
FPU System Control register is set on Return from ISR.


Entering Low-power mode through WFI or WFE is executed only if no interrupt is pending or
no event is pending.


**Exiting low-power mode**


The MCU exits from Sleep and Stop modes low-power mode depending on the way the lowpower mode was entered:

      - If the WFI instruction or Return from ISR was used to enter the low-power mode, any
peripheral interrupt acknowledged by the NVIC can wake up the device.


      - If the WFE instruction is used to enter the low-power mode, the MCU exits the lowpower mode as soon as an event occurs. The wake-up event can be generated either
by:


–
NVIC IRQ interrupt:

When SEVONPEND = 0 in the Cortex [®] -M4 with FPU System Control register: by
enabling an interrupt in the peripheral control register and in the NVIC. When the
MCU resumes from WFE, the peripheral interrupt pending bit and the NVIC
peripheral IRQ channel pending bit (in the NVIC interrupt clear pending register)
have to be cleared. Only NVIC interrupts with sufficient priority wakes up and
interrupts the MCU.

When SEVONPEND = 1 in the Cortex [®] -M4 with FPU System Control register: by
enabling an interrupt in the peripheral control register and optionally in the NVIC.
When the MCU resumes from WFE, the peripheral interrupt pending bit and when
enabled the NVIC peripheral IRQ channel pending bit (in the NVIC interrupt clear
pending register) have to be cleared. All NVIC interrupts wakes up the MCU, even
the disabled ones. Only enabled NVIC interrupts with sufficient priority wakes up
and interrupts the MCU.


– Event


This is done by configuring a EXTI line in event mode. When the CPU resumes
from WFE, it is not necessary to clear the EXTI peripheral interrupt pending bit or
the NVIC IRQ channel pending bit as the pending bits corresponding to the event
line is not set. It may be necessary to clear the interrupt flag in the peripheral.


The MCU exits from Standby low-power mode through an external reset (NRST pin), an
IWDG reset, a rising edge on one of the enabled WKUPx pins or a RTC event occurs (see
_Figure 237: RTC block diagram_ ).


After waking up from Standby mode, program execution restarts in the same way as after a
Reset (boot pin sampling, option bytes loading, reset vector is fetched, etc.).


128/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


Only enabled NVIC interrupts with sufficient priority wakes up and interrupts the MCU.


**Table 24. Low-power mode summary**
























|Mode name|Entry|Wake-up|Effect on 1.2 V<br>domain clocks|Effect on<br>V<br>DD<br>domain<br>clocks|Voltage regulator|
|---|---|---|---|---|---|
|**Sleep**<br>**(Sleep now or**<br>**Sleep-on-**<br>**exit)**|WFI or Return<br>from ISR|Any interrupt|CPU CLK OFF<br>no effect on other<br>clocks or analog<br>clock sources|None|ON|
|**Sleep**<br>**(Sleep now or**<br>**Sleep-on-**<br>**exit)**|WFE|Wake-up event|Wake-up event|Wake-up event|Wake-up event|
|**Stop**|PDDS and LPDS<br>bits +<br>SLEEPDEEP bit<br>+ WFI, Return<br>from ISR or WFE|Any EXTI line (configured<br>in the EXTI registers,<br>internal and external lines)|All 1.2 V domain<br>clocks OFF|HSI and<br>HSE<br>oscillator<br>s OFF|ON or in low- power<br>mode (depends on<br>_PWR power control_<br>_register (PWR_CR)_<br>_for_<br>_STM32F405xx/07x_<br>_x and_<br>_STM32F415xx/17x_<br>_x_ and_PWR power_<br>_control register_<br>_(PWR_CR) for_<br>_STM32F405xx/07x_<br>_x and_<br>_STM32F415xx/17x_<br>_xPWR power_<br>_control register_<br>_(PWR_CR) for_<br>_STM32F42xxx and_<br>_STM32F43xxx_|
|**Standby**|PDDS bit +<br>SLEEPDEEP bit<br>+ WFI, Return<br>from ISR or WFE|WKUP pin rising edge,<br>RTC alarm (Alarm A or<br>Alarm B), RTC Wake-up<br>event, RTC tamper<br>events, RTC time stamp<br>event, external reset in<br>NRST pin, IWDG reset|WKUP pin rising edge,<br>RTC alarm (Alarm A or<br>Alarm B), RTC Wake-up<br>event, RTC tamper<br>events, RTC time stamp<br>event, external reset in<br>NRST pin, IWDG reset|WKUP pin rising edge,<br>RTC alarm (Alarm A or<br>Alarm B), RTC Wake-up<br>event, RTC tamper<br>events, RTC time stamp<br>event, external reset in<br>NRST pin, IWDG reset|OFF|



**5.3.1** **Slowing down system clocks**


In Run mode the speed of the system clocks (SYSCLK, HCLK, PCLK1, PCLK2) can be
reduced by programming the prescaler registers. These prescalers can also be used to slow
down peripherals before entering Sleep mode.


For more details refer to _Section 7.3.3: RCC clock configuration register (RCC_CFGR)_ .


**5.3.2** **Peripheral clock gating**


In Run mode, the HCLKx and PCLKx for individual peripherals and memories can be
stopped at any time to reduce power consumption.


To further reduce power consumption in Sleep mode the peripheral clocks can be disabled
prior to executing the WFI or WFE instructions.


RM0090 Rev 21 129/1757



151


**Power controller (PWR)** **RM0090**


Peripheral clock gating is controlled by the AHB1 peripheral clock enable register
(RCC_AHB1ENR), AHB2 peripheral clock enable register (RCC_AHB2ENR), AHB3
peripheral clock enable register (RCC_AHB3ENR) (see _Section 7.3.10: RCC AHB1_
_peripheral clock enable register (RCC_AHB1ENR)_, _Section 7.3.11: RCC AHB2 peripheral_
_clock enable register (RCC_AHB2ENR)_, _Section 7.3.12: RCC AHB3 peripheral clock_
_enable register (RCC_AHB3ENR)_ for STM32F405xx/07xx and STM32F415xx/17xx, and
_Section 6.3.10: RCC AHB1 peripheral clock register (RCC_AHB1ENR)_, _Section 6.3.11:_
_RCC AHB2 peripheral clock enable register (RCC_AHB2ENR)_, and _Section 6.3.12: RCC_
_AHB3 peripheral clock enable register (RCC_AHB3ENR)_ for STM32F42xxx and
STM32F43xxx).


Disabling the peripherals clocks in Sleep mode can be performed automatically by resetting
the corresponding bit in RCC_AHBxLPENR and RCC_APBxLPENR registers.


**5.3.3** **Sleep mode**


**Entering Sleep mode**


The Sleep mode is entered according to _Section : Entering low-power mode_, when the
SLEEPDEEP bit in the Cortex [®] -M4 with FPU System Control register is cleared.


Refer to _Table 25_ and _Table 26_ for details on how to enter Sleep mode.


_Note:_ _All interrupt pending bits must be cleared before the sleep mode entry._


**Exiting Sleep mode**


The Sleep mode is exited according to _Section : Exiting low-power mode_ .


Refer to _Table 25_ and _Table 26_ for more details on how to exit Sleep mode.






|Col1|Table 25. Sleep-now entry and exit|
|---|---|
|**Sleep-now mode**|**Description**|
|**Mode entry**|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– SLEEPDEEP = 0, and<br>– No interrupt (for WFI) or event (for WFE) is pending.<br>Refer to the Cortex®-M4 with FPU System Control register.|
|**Mode entry**|On Return from ISR while:<br>– SLEEPDEEP = 0 and<br>– SLEEPONEXIT = 1,<br>– No interrupt is pending.<br>Refer to the Cortex®-M4 with FPU System Control register.|



130/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


**Table 25. Sleep-now entry and exit (continued)**








|Sleep-now mode|Description|
|---|---|
|**Mode exit**|If WFI or Return from ISR was used for entry:<br>Interrupt: Refer to_Table 62: Vector table for STM32F405xx/07xx and_<br>_STM32F415xx/17xx_ and_Table 63: Vector table for STM32F42xxx and_<br>_STM32F43xxx_<br>If WFE was used for entry and SEVONPEND = 0<br>Wake-up event: Refer to_Section 12.2.3: Wake-up event management_<br>f WFE was used for entry and SEVONPEND = 1<br>Interrupt even when disabled in NVIC: refer to_Table 62: Vector table for_<br>_STM32F405xx/07xx and STM32F415xx/17xx_ and_Table 63: Vector table_<br>_for STM32F42xxx and STM32F43xxx_or Wake-up event (see<br>_Section 12.2.3: Wake-up event management_).|
|**Wake-up latency**|None|







|Col1|Table 26. Sleep-on-exit entry and exit|
|---|---|
|**Sleep-on-exit**|**Description**|
|**Mode entry**|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– SLEEPDEEP = 0, and<br>– No interrupt (for WFI) or event (for WFE) is pending.<br>Refer to the Cortex®-M4 with FPU System Control register.|
|**Mode entry**|On Return from ISR while:<br>– SLEEPDEEP = 0, and<br>– SLEEPONEXIT = 1, and<br>– No interrupt is pending.<br>Refer to the Cortex®-M4 with FPU System Control register.|
|**Mode exit**|Interrupt: refer to_Table 62: Vector table for STM32F405xx/07xx and_<br>_STM32F415xx/17xx_ and_Table 63: Vector table for STM32F42xxx and_<br>_STM32F43xxx_|
|**Wake-up latency**|None|


**5.3.4** **Stop mode (STM32F405xx/07xx and STM32F415xx/17xx)**


The Stop mode is based on the Cortex [®] -M4 with FPU deepsleep mode combined with
peripheral clock gating. The voltage regulator can be configured either in normal or lowpower mode. In Stop mode, all clocks in the 1.2 V domain are stopped, the PLLs, the HSI
and the HSE RC oscillators are disabled. Internal SRAM and register contents are
preserved.


By setting the FPDS bit in the PWR_CR register, the Flash memory also enters power-down
mode when the device enters Stop mode. When the Flash memory is in power-down mode,
an additional startup delay is incurred when waking up from Stop mode (see _Table 27: Stop_
_operating modes (STM32F405xx/07xx and STM32F415xx/17xx)_ and _Section 5.4.1: PWR_
_power control register (PWR_CR) for STM32F405xx/07xx and STM32F415xx/17xx_ ).


RM0090 Rev 21 131/1757



151


**Power controller (PWR)** **RM0090**


**Table 27. Stop operating modes**
**(STM32F405xx/07xx and STM32F415xx/17xx)**






|Stop mode|LPDS bit|FPDS bit|Wake-up latency|
|---|---|---|---|
|STOP MR<br>(Main regulator)|0|0|HSI RC startup time|
|STOP MR-FPD|0|1|HSI RC startup time +<br>Flash wake-up time from Power<br>Down mode|
|STOP LP|1|0|HSI RC startup time +<br>regulator wake-up time from LP<br>mode|
|STOP LP-FPD|1|1|HSI RC startup time +<br>Flash wake-up time from Power<br>Down mode +<br>regulator wake-up time from LP<br>mode|



**Entering Stop mode (for STM32F405xx/07xx and STM32F415xx/17xx)**


The Stop mode is entered according to _Section : Entering low-power mode_, when the
SLEEPDEEP bit in the Cortex [®] -M4 with FPU System Control register is set.


Refer to _Table 28_ for details on how to enter the Stop mode.


To further reduce power consumption in Stop mode, the internal voltage regulator can be put
in low-power mode. This is configured by the LPDS bit of the _PWR power control register_
_(PWR_CR) for STM32F405xx/07xx and STM32F415xx/17xx_ and _PWR power control_
_register (PWR_CR) for STM32F42xxx and STM32F43xxx_ .


If Flash memory programming is ongoing, the Stop mode entry is delayed until the memory
access is finished.


If an access to the APB domain is ongoing, The Stop mode entry is delayed until the APB
access is finished.


In Stop mode, the following features can be selected by programming individual control bits:


      - Independent watchdog (IWDG): the IWDG is started by writing to its Key register or by
hardware option. Once started it cannot be stopped except by a Reset. See
_Section 21.3_ in _Section 21: Independent watchdog (IWDG)_ .


      - Real-time clock (RTC): this is configured by the RTCEN bit in the _Section 7.3.20: RCC_
_Backup domain control register (RCC_BDCR)_


      - Internal RC oscillator (LSI RC): this is configured by the LSION bit in the
_Section 7.3.21: RCC clock control & status register (RCC_CSR)_ .


      - External 32.768 kHz oscillator (LSE OSC): this is configured by the LSEON bit in the
_Section 7.3.20: RCC Backup domain control register (RCC_BDCR)_ .


The ADC or DAC can also consume power during the Stop mode, unless they are disabled
before entering it. To disable them, the ADON bit in the ADC_CR2 register and the ENx bit
in the DAC_CR register must both be written to 0.


132/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


_Note:_ _If the application needs to disable the external clock before entering Stop mode, the HSEON_
_bit must first be disabled and the system clock switched to HSI._


_Otherwise, if the HSEON bit is kept enabled while the external clock (external oscillator) can_
_be removed before entering stop mode, the clock security system (CSS) feature must be_
_enabled to detect any external oscillator failure and avoid a malfunction behavior when_
_entering stop mode._


**Exiting Stop mode (for STM32F405xx/07xx and STM32F415xx/17xx)**


The Stop mode is exited according to _Section : Exiting low-power mode_ .


Refer to _Table 28_ for more details on how to exit Stop mode.


When exiting Stop mode by issuing an interrupt or a wake-up event, the HSI RC oscillator is
selected as system clock.


When the voltage regulator operates in low-power mode, an additional startup delay is
incurred when waking up from Stop mode. By keeping the internal regulator ON during Stop
mode, the consumption is higher although the startup time is reduced.





|Table 28. Stop mode|entry and exit (for STM32F405xx/07xx and STM32F415xx/17xx)|
|---|---|
|**Stop mode**|**Description**|
|**Mode entry**|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– No interrupt (for WFI) or event (for WFE) is pending,<br>– SLEEPDEEP bit is set in Cortex®-M4 with FPU System Control register,<br>– PDDS bit is cleared in Power Control register (PWR_CR),<br>– Select the voltage regulator mode by configuring LPDS bit in PWR_CR.|
|**Mode entry**|On Return from ISR:<br>– No interrupt is pending,<br>– SLEEPDEEP bit is set in Cortex®-M4 with FPU System Control register,<br>– SLEEPONEXIT = 1,<br>– PDDS bit is cleared in Power Control register (PWR_CR).|
|**Mode entry**|_Note: To enter Stop mode, all EXTI Line pending bits (inPending register_<br>_(EXTI_PR)), all peripheral interrupts pending bits, the RTC Alarm_<br>_(Alarm A and Alarm B), RTC wake-up, RTC tamper, and RTC time_<br>_stamp flags, must be reset. Otherwise, the Stop mode entry_<br>_procedure is ignored and program execution continues._|


RM0090 Rev 21 133/1757



151


**Power controller (PWR)** **RM0090**







|Table 28. Stop mode|entry and exit (for STM32F405xx/07xx and STM32F415xx/17xx)|
|---|---|
|**Stop mode**|**Description**|
|**Mode exit**|If WFI or Return from ISR was used for entry:<br>Any EXTI lines configured in Interrupt mode (the corresponding EXTI<br>Interrupt vector must be enabled in the NVIC). The interrupt source can<br>be external interrupts or peripherals with wake-up capability. Refer to<br>_Table 62: Vector table for STM32F405xx/07xx and STM32F415xx/17xx_<br>_on page 375_ and_Table 63: Vector table for STM32F42xxx and_<br>_STM32F43xxx_.<br>If WFE was used for entry and SEVONPEND = 0<br>Any EXTI lines configured in event mode. Refer to_Section 12.2.3: Wake-_<br>_up event management on page 383_.<br>If WFE was used for entry and SEVONPEND = 1:<br>– Any EXTI lines configured in Interrupt mode (even if the corresponding<br>EXTI Interrupt vector is disabled in the NVIC). The interrupt source can<br>be an external interrupt or a peripheral with wake-up capability. Refer to<br>_Table 62: Vector table for STM32F405xx/07xx and STM32F415xx/17xx_<br>_on page 375_ and_Table 63: Vector table for STM32F42xxx and_<br>_STM32F43xxx_.<br>– Wake-up event: refer to_Section 12.2.3: Wake-up event management on_<br>_page 383_.|
|**Wake-up latency**|_Table 27: Stop operating modes (STM32F405xx/07xx and_<br>_STM32F415xx/17xx)_|


**5.3.5** **Stop mode (STM32F42xxx and STM32F43xxx)**


The Stop mode is based on the Cortex [®] -M4 with FPU deepsleep mode combined with
peripheral clock gating. The voltage regulator can be configured either in normal or lowpower mode. In Stop mode, all clocks in the 1.2 V domain are stopped, the PLLs, the HSI
and the HSE RC oscillators are disabled. Internal SRAM and register contents are
preserved.


In Stop mode, the power consumption can be further reduced by using additional settings in
the PWR_CR register. However this induces an additional startup delay when waking up
from Stop mode (see _Table 29_ ).


134/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


**Table 29. Stop operating modes (STM32F42xxx and STM32F43xxx)**










|Voltage Regulator Mode|Col2|UDEN[1:0]<br>bits|MRUDS<br>bit|LPUDS<br>bit|LPDS<br>bit|FPDS<br>bit|Wake-up latency|
|---|---|---|---|---|---|---|---|
|Normal<br>mode|STOP MR<br>(Main Regulator)|-|0|-|0|0|HSI RC startup time|
|Normal<br>mode|STOP MR- FPD|-|0|-|0|1|HSI RC startup time +<br>Flash wake-up time from power-<br>down mode|
|Normal<br>mode|STOP LP|-|0|0|1|0|HSI RC startup time +<br>regulator wake-up time from LP<br>mode|
|Normal<br>mode|STOP LP-FPD|-|-|0|1|1|HSI RC startup time +<br>Flash wake-up time from power-<br>down mode +<br>regulator wake-up time from LP<br>mode|
|Under-<br>drive<br>Mode|STOP UMR-<br>FPD|3|1|-|0|-|HSI RC startup time +<br>Flash wake-up time from power-<br>down mode +<br>Main regulator wake-up time from<br>under-drive mode + Core logic to<br>nominal mode|
|Under-<br>drive<br>Mode|STOP ULP-FPD|3|-|1|1|-|HSI RC startup time +<br>Flash wake-up time from power-<br>down mode +<br>regulator wake-up time from LP<br>under-drive mode + Core logic to<br>nominal mode|



**Entering Stop mode (STM32F42xxx and STM32F43xxx)**


The Stop mode is entered according to _Section : Entering low-power mode_, when the
SLEEPDEEP bit in the Cortex [®] -M4 with FPU System Control register is set.


Refer to _Table 30_ for details on how to enter the Stop mode.


When the microcontroller enters in Stop mode, the voltage scale 3 is automatically selected.
To further reduce power consumption in Stop mode, the internal voltage regulator can be put
in low voltage mode. This is configured by the LPDS, MRUDS, LPUDS and UDEN bits of
the _PWR power control register (PWR_CR) for STM32F405xx/07xx and_
_STM32F415xx/17xx_ .


If Flash memory programming is ongoing, the Stop mode entry is delayed until the memory
access is finished.


If an access to the APB domain is ongoing, The Stop mode entry is delayed until the APB
access is finished.


If the Over-drive mode was enabled before entering Stop mode, it is automatically disabled
during when the Stop mode is activated.


RM0090 Rev 21 135/1757



151


**Power controller (PWR)** **RM0090**


In Stop mode, the following features can be selected by programming individual control bits:


      - Independent watchdog (IWDG): the IWDG is started by writing to its Key register or by
hardware option. Once started it cannot be stopped except by a Reset. See
_Section 21.3_ in _Section 21: Independent watchdog (IWDG)_ .


      - Real-time clock (RTC): this is configured by the RTCEN bit in the _Section 7.3.20: RCC_
_Backup domain control register (RCC_BDCR)_


      - Internal RC oscillator (LSI RC): this is configured by the LSION bit in the
_Section 7.3.21: RCC clock control & status register (RCC_CSR)_ .


      - External 32.768 kHz oscillator (LSE OSC): this is configured by the LSEON bit in the
_RCC Backup domain control register (RCC_BDCR)_ .


The ADC or DAC can also consume power during the Stop mode, unless they are disabled
before entering it. To disable them, the ADON bit in the ADC_CR2 register and the ENx bit
in the DAC_CR register must both be written to 0.


_Note:_ _Before entering Stop mode, it is recommended to enable the clock security system (CSS)_
_feature to prevent external oscillator (HSE) failure from impacting the internal MCU_
_behavior._


**Exiting Stop mode (STM32F42xxx and STM32F43xxx)**


The Stop mode is exited according to _Section : Exiting low-power mode_ .


Refer to _Table 30_ for more details on how to exit Stop mode.


When exiting Stop mode by issuing an interrupt or a wake-up event, the HSI RC oscillator is
selected as system clock.


If the Under-drive mode was enabled, it is automatically disabled after exiting Stop mode.


When the voltage regulator operates in low voltage mode, an additional startup delay is
incurred when waking up from Stop mode. By keeping the internal regulator ON during Stop
mode, the consumption is higher although the startup time is reduced.


When the voltage regulator operates in Under-drive mode, an additional startup delay is
induced when waking up from Stop mode.


136/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


**Table 30. Stop mode entry and exit (STM32F42xxx and STM32F43xxx)**







|Stop mode|Description|
|---|---|
|**Mode entry**|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– No interrupt or event is pending,<br>– SLEEPDEEP bit is set in Cortex®-M4 with FPU System Control register,<br>– PDDS bit is cleared in Power Control register (PWR_CR),<br>– Select the voltage regulator mode by configuring LPDS,MRUDS, LPUDS<br>and UDEN bitsin PWR_CR (see_Table 29: Stop operating modes_<br>_(STM32F42xxx and STM32F43xxx)_).|
|**Mode entry**|On Return from ISR while:<br>– No interrupt is pending,<br>– SLEEPDEEP bit is set in Cortex®-M4 with FPU System Control register,<br>and<br>– SLEEPONEXIT = 1, and<br>– PDDS is cleared in PWR_CR1.|
|**Mode entry**|_Note: To enter Stop mode, all EXTI Line pending bits (inPending register_<br>_(EXTI_PR)), all peripheral interrupts pending bits, the RTC Alarm_<br>_(Alarm A and Alarm B), RTC wake-up, RTC tamper, and RTC time_<br>_stamp flags, must be reset. Otherwise, the Stop mode entry_<br>_procedure is ignored and program execution continues._|
|**Mode exit**|If WFI or Return from ISR was used for entry:<br>All EXTI lines configured in Interrupt mode (the corresponding EXTI<br>Interrupt vector must be enabled in the NVIC). The interrupt source can<br>be external interrupts or peripherals with wake-up capability. Refer to<br>_Table 62: Vector table for STM32F405xx/07xx and STM32F415xx/17xx_<br>_on page 375_.<br>If WFE was used for entry and SEVONPEND = 0:<br>All EXTI Lines configured in event mode. Refer to_Section 12.2.3: Wake-_<br>_up event management on page 383_<br>If WFE was used for entry and SEVONPEND = 1:<br>– Any EXTI lines configured in Interrupt mode (even if the corresponding<br>EXTI Interrupt vector is disabled in the NVIC). The interrupt source can<br>be external interrupts or peripherals with wake-up capability. Refer to<br>_Table 62: Vector table for STM32F405xx/07xx and STM32F415xx/17xx_<br>_on page 375_ and_Table 63: Vector table for STM32F42xxx and_<br>_STM32F43xxx_.<br>– Wake-up event: refer to_Section 12.2.3: Wake-up event management on_<br>_page 383_.|
|**Wake-up latency**|Refer to_Table 29: Stop operating modes (STM32F42xxx and_<br>_STM32F43xxx)_|


**5.3.6** **Standby mode**


The Standby mode allows to achieve the lowest power consumption. It is based on the
Cortex [®] -M4 with FPU deepsleep mode, with the voltage regulator disabled. The 1.2 V
domain is consequently powered off. The PLLs, the HSI oscillator and the HSE oscillator are
also switched off. SRAM and register contents are lost except for registers in the backup
domain (RTC registers, RTC backup register and backup SRAM), and Standby circuitry (see
_Figure 9_ ).


RM0090 Rev 21 137/1757



151


**Power controller (PWR)** **RM0090**


**Entering Standby mode**


The Standby mode is entered according to _Section : Entering low-power mode_, when the
SLEEPDEEP bit in the Cortex [®] -M4 with FPU System Control register is set.

Refer to _Table 31_ for more details on how to enter Standby mode.


In Standby mode, the following features can be selected by programming individual control
bits:


      - Independent watchdog (IWDG): the IWDG is started by writing to its Key register or by
hardware option. Once started it cannot be stopped except by a reset. See
_Section 21.3_ in _Section 21: Independent watchdog (IWDG)_ .


      - Real-time clock (RTC): this is configured by the RTCEN bit in the backup domain
control register (RCC_BDCR)


      - Internal RC oscillator (LSI RC): this is configured by the LSION bit in the Control/status
register (RCC_CSR).


      - External 32.768 kHz oscillator (LSE OSC): this is configured by the LSEON bit in the
backup domain control register (RCC_BDCR)


**Exiting Standby mode**


The Standby mode is exited according to _Section : Exiting low-power mode_ . The SBF status
flag in PWR_CR (see _Section 5.4.2: PWR power control/status register (PWR_CSR) for_
_STM32F405xx/07xx and STM32F415xx/17xx_ ) indicates that the MCU was in Standby
mode. All registers are reset after wake-up from Standby except for PWR_CR.


Refer to _Table 31_ for more details on how to exit Standby mode.







|Col1|Table 31. Standby mode entry and exit|
|---|---|
|**Standby mode**|**Description**|
|**Mode entry**|WFI (Wait for Interrupt) or WFE (Wait for Event) while:<br>– SLEEPDEEP is set in Cortex®-M4 with FPU System Control register,<br>– PDDS bit is set in Power Control register (PWR_CR),<br>– No interrupt (for WFI) or event (for WFE) is pending,<br>– WUF bit is cleared in Power Control register (PWR_CR),<br>– the RTC flag corresponding to the chosen wake-up source (RTC Alarm<br>A, RTC Alarm B, RTC wake-up, Tamper or Timestamp flags) is cleared|
|**Mode entry**|On return from ISR while:<br>– SLEEPDEEP bit is set in Cortex®-M4 with FPU System Control register,<br>and<br>– SLEEPONEXIT = 1, and<br>– PDDS bit is set in Power Control register (PWR_CR), and<br>– No interrupt is pending,<br>– WUF bit is cleared in Power Control/Status register (PWR_SR),<br>– The RTC flag corresponding to the chosen wake-up source (RTC Alarm<br>A, RTC Alarm B, RTC wake-up, Tamper or Timestamp flags) is cleared.|
|**Mode exit**|WKUP pin rising edge, RTC alarm (Alarm A and Alarm B), RTC wake-up,<br>tamper event, time stamp event, external reset in NRST pin, IWDG reset.|
|**Wake-up latency**|Reset phase.|


138/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


**I/O states in Standby mode**


In Standby mode, all I/O pins are high impedance except for:


      - Reset pad (still available)


      - RTC_AF1 pin (PC13) if configured for tamper, time stamp, RTC Alarm out, or RTC
clock calibration out


      - WKUP pin (PA0), if enabled


**Debug mode**


By default, the debug connection is lost if the application puts the MCU in Stop or Standby
mode while the debug features are used. This is due to the fact that the Cortex [®] -M4 with
FPU core is no longer clocked.


However, by setting some configuration bits in the DBGMCU_CR register, the software can
be debugged even when using the low-power modes extensively. For more details, refer to
_Section 38.16.1: Debug support for low-power modes_ .


**5.3.7** **Programming the RTC alternate functions to wake up the device from**
**the Stop and Standby modes**


The MCU can be woken up from a low-power mode by an RTC alternate function.


The RTC alternate functions are the RTC alarms (Alarm A and Alarm B), RTC wake-up,
RTC tamper event detection and RTC time stamp event detection.


These RTC alternate functions can wake up the system from the Stop and Standby lowpower modes.


The system can also wake up from low-power modes without depending on an external
interrupt (Auto-wake-up mode), by using the RTC alarm or the RTC wake-up events.


The RTC provides a programmable time base for waking up from the Stop or Standby mode
at regular intervals.


For this purpose, two of the three alternate RTC clock sources can be selected by
programming the RTCSEL[1:0] bits in the _Section 7.3.20: RCC Backup domain control_
_register (RCC_BDCR)_ :


      - Low-power 32.768 kHz external crystal oscillator (LSE OSC)
This clock source provides a precise time base with a very low-power consumption
(additional consumption of less than 1 µA under typical conditions)


      - Low-power internal RC oscillator (LSI RC)
This clock source has the advantage of saving the cost of the 32.768 kHz crystal. This
internal RC oscillator is designed to use minimum power.


RM0090 Rev 21 139/1757



151


**Power controller (PWR)** **RM0090**


**RTC alternate functions to wake up the device from the Stop mode**


      - To wake up the device from the Stop mode with an RTC alarm event, it is necessary to:


a) Configure the EXTI Line 17 to be sensitive to rising edges (Interrupt or Event
modes)


b) Enable the RTC Alarm Interrupt in the RTC_CR register


c) Configure the RTC to generate the RTC alarm


      - To wake up the device from the Stop mode with an RTC tamper or time stamp event, it
is necessary to:


a) Configure the EXTI Line 21 to be sensitive to rising edges (Interrupt or Event
modes)


b) Enable the RTC time stamp Interrupt in the RTC_CR register or the RTC tamper
interrupt in the RTC_TAFCR register


c) Configure the RTC to detect the tamper or time stamp event


      - To wake up the device from the Stop mode with an RTC wake-up event, it is necessary
to:


a) Configure the EXTI Line 22 to be sensitive to rising edges (Interrupt or Event
modes)


b) Enable the RTC wake-up interrupt in the RTC_CR register


c) Configure the RTC to generate the RTC Wake-up event


**RTC alternate functions to wake up the device from the Standby mode**


      - To wake up the device from the Standby mode with an RTC alarm event, it is necessary
to:


a) Enable the RTC alarm interrupt in the RTC_CR register


b) Configure the RTC to generate the RTC alarm


      - To wake up the device from the Standby mode with an RTC tamper or time stamp
event, it is necessary to:


a) Enable the RTC time stamp interrupt in the RTC_CR register or the RTC tamper
interrupt in the RTC_TAFCR register


b) Configure the RTC to detect the tamper or time stamp event


      - To wake up the device from the Standby mode with an RTC wake-up event, it is
necessary to:


a) Enable the RTC wake-up interrupt in the RTC_CR register


b) Configure the RTC to generate the RTC wake-up event


**Safe RTC alternate function wake-up flag clearing sequence**


If the selected RTC alternate function is set before the PWR wake-up flag (WUTF) is
cleared, it is not detected on the next event as detection is made once on the rising edge.


To avoid bouncing on the pins onto which the RTC alternate functions are mapped, and exit
correctly from the Stop and Standby modes, it is recommended to follow the sequence
below before entering the Standby mode:


      - When using RTC alarm to wake up the device from the low-power modes:


a) Disable the RTC alarm interrupt (ALRAIE or ALRBIE bits in the RTC_CR register)


b) Clear the RTC alarm (ALRAF/ALRBF) flag


140/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


c) Clear the PWR Wake-up (WUF) flag


d) Enable the RTC alarm interrupt


e) Re-enter the low-power mode


      - When using RTC wake-up to wake up the device from the low-power modes:


a) Disable the RTC Wake-up interrupt (WUTIE bit in the RTC_CR register)


b) Clear the RTC Wake-up (WUTF) flag


c) Clear the PWR Wake-up (WUF) flag


d) Enable the RTC Wake-up interrupt


e) Re-enter the low-power mode


      - When using RTC tamper to wake up the device from the low-power modes:


a) Disable the RTC tamper interrupt (TAMPIE bit in the RTC_TAFCR register)


b) Clear the Tamper (TAMP1F/TSF) flag


c) Clear the PWR Wake-up (WUF) flag


d) Enable the RTC tamper interrupt


e) Re-enter the low-power mode


      - When using RTC time stamp to wake up the device from the low-power modes:


a) Disable the RTC time stamp interrupt (TSIE bit in RTC_CR)


b) Clear the RTC time stamp (TSF) flag


c) Clear the PWR Wake-up (WUF) flag


d) Enable the RTC TimeStamp interrupt


e) Re-enter the low-power mode


RM0090 Rev 21 141/1757



151


**Power controller (PWR)** **RM0090**

## **5.4 Power control registers (STM32F405xx/07xx and** **STM32F415xx/17xx)**


**5.4.1** **PWR power control register (PWR_CR)**
## **for STM32F405xx/07xx and STM32F415xx/17xx**


Address offset: 0x00


Reset value: 0x0000 4000 (reset by wake-up from Standby mode)


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15|14|13 12 11 10|9|8|7 6 5|Col7|Col8|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|VOS|Reserved|FPDS|DBP|PLS[2:0]|PLS[2:0]|PLS[2:0]|PVDE|CSBF|CWUF|PDDS|LPDS|
|Res.|rw|rw|rw|rw|rw|rw|rw|rw|w|w|rw|rw|



Bits 31:15 Reserved, must be kept at reset value.


Bit 14 **VOS** : Regulator voltage scaling output selection

This bit controls the main internal voltage regulator output voltage to achieve a trade-off
between performance and power consumption when the device does not operate at the
maximum frequency.

0: Scale 2 mode

1: Scale 1 mode (default value at reset)


Bits 13:10 Reserved, must be kept at reset value.


Bit 9 **FPDS** : Flash power-down in Stop mode

When set, the Flash memory enters power-down mode when the device enters Stop mode.
This allows to achieve a lower consumption in stop mode but a longer restart time.
0: Flash memory not in power-down when the device is in Stop mode
1: Flash memory in power-down when the device is in Stop mode


Bit 8 **DBP** : Disable backup domain write protection

In reset state, the RCC_BDCR register, the RTC registers (including the backup registers),
and the BRE bit of the PWR_CSR register, are protected against parasitic write access. This
bit must be set to enable write access to these registers.
0: Access to RTC and RTC Backup registers and backup SRAM disabled
1: Access to RTC and RTC Backup registers and backup SRAM enabled

_Note: Depending on the APB1 prescaler, there is a delay between writing to DBP and the_
_effective disabling/enabling of the backup domain protection. Therefore, a dummy read_
_operation to the PWR_CR register is required just after writing to the DBP bit._


142/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


Bits 7:5 **PLS[2:0]:** PVD level selection

These bits are written by software to select the voltage threshold detected by the
programmable voltage detector

000: 2.0 V

001: 2.1 V

010: 2.3 V

011: 2.5 V

100: 2.6 V

101: 2.7 V

110: 2.8 V

111: 2.9 V

_Note: Refer to the electrical characteristics of the datasheet for more details._


Bit 4 **PVDE:** Programmable voltage detector enable

This bit is set and cleared by software.

0: PVD disabled

1: PVD enabled


Bit 3 **CSBF** : Clear standby flag

This bit is always read as 0.

0: No effect

1: Clear the SBF Standby Flag (write).


Bit 2 **CWUF:** Clear wake-up flag

This bit is always read as 0.

0: No effect

1: Clear the WUF Wake-up Flag **after 2 System clock cycles**


Bit 1 **PDDS** : Power-down deepsleep

This bit is set and cleared by software. It works together with the LPDS bit.
0: Enter Stop mode when the CPU enters deepsleep. The regulator status depends on the
LPDS bit.

1: Enter Standby mode when the CPU enters deepsleep.


Bit 0 **LPDS:** Low-power deepsleep

This bit is set and cleared by software. It works together with the PDDS bit.
0: Voltage regulator on during Stop mode
1: Voltage regulator in low-power mode during Stop mode


**5.4.2** **PWR power control/status register (PWR_CSR)**
**for STM32F405xx/07xx and STM32F415xx/17xx**


Address offset: 0x04


Reset value: 0x0000 0000 (not reset by wake-up from Standby mode)


Additional APB cycles are needed to read this register versus a standard APB read.


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved





|15|14|13 12 11 10|9|8|7 6 5 4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|
|Res|VOS<br>RDY|Reserved|BRE|EWUP|Reserved|BRR|PVDO|SBF|WUF|
|Res|r|r|rw|rw|rw|r|r|r|r|


RM0090 Rev 21 143/1757



151


**Power controller (PWR)** **RM0090**


Bits 31:15 Reserved, must be kept at reset value.


Bit 14 **VOSRDY** : Regulator voltage scaling output selection ready bit

0: Not ready
1: Ready


Bits 13:10 Reserved, must be kept at reset value.


Bit 9 **BRE** : Backup regulator enable

When set, the Backup regulator (used to maintain backup SRAM content in Standby and
V BAT modes) is enabled. If BRE is reset, the backup regulator is switched off. The backup
SRAM can still be used but its content is lost in the Standby and V BAT modes. Once set, the
application must wait that the Backup Regulator Ready flag (BRR) is set to indicate that the
data written into the RAM is maintained in the Standby and V BAT modes.
0: Backup regulator disabled
1: Backup regulator enabled

_Note: This bit is not reset when the device wakes up from Standby mode, by a system reset,_
_or by a power reset._

_The DBP bit of the PWR_CR register must be set before BRE can be written._


Bit 8 **EWUP** : Enable WKUP pin

This bit is set and cleared by software.
0: WKUP pin is used for general purpose I/O. An event on the WKUP pin does not wake up
the device from Standby mode.
1: WKUP pin is used for wake-up from Standby mode and forced in input pull down
configuration (rising edge on WKUP pin wakes-up the system from Standby mode).

_Note: This bit is reset by a system reset._


Bits 7:4 Reserved, must be kept at reset value.


Bit 3 **BRR** : Backup regulator ready

Set by hardware to indicate that the Backup Regulator is ready.
0: Backup Regulator not ready
1: Backup Regulator ready

_Note: This bit is not reset when the device wakes up from Standby mode or by a system reset_
_or power reset._


Bit 2 **PVDO:** PVD output

This bit is set and cleared by hardware. It is valid only if PVD is enabled by the PVDE bit.
0: V DD is higher than the PVD threshold selected with the PLS[2:0] bits.
1: V DD is lower than the PVD threshold selected with the PLS[2:0] bits.
_Note: The PVD is stopped by Standby mode. For this reason, this bit is equal to 0 after_
_Standby or reset until the PVDE bit is set._


Bit 1 **SBF:** Standby flag

This bit is set by hardware and cleared only by a POR/PDR (power-on reset/power-down
reset) or by setting the CSBF bit in the PWR_CR register.
0: Device has not been in Standby mode
1: Device has been in Standby mode


144/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


Bit 0 **WUF:** Wake-up flag

This bit is set by hardware and cleared either by a system reset or by setting the CWUF bit in
the PWR_CR register.
0: No wake-up event occurred
1: A wake-up event was received from the WKUP pin or from the RTC alarm (Alarm A or
Alarm B), RTC Tamper event, RTC TimeStamp event or RTC Wake-up).

_Note: An additional wake-up event is detected if the WKUP pin is enabled (by setting the_
_EWUP bit) when the WKUP pin level is already high._


RM0090 Rev 21 145/1757



151


**Power controller (PWR)** **RM0090**

## **5.5 Power control registers (STM32F42xxx and STM32F43xxx)**


**5.5.1** **PWR power control register (PWR_CR)**
**for STM32F42xxx and STM32F43xxx**


Address offset: 0x00


Reset value: 0x0000 C000 (reset by wake-up from Standby mode)

|31 30 29 28 27 26 25 24 23 22 21 20|19 18|Col3|17|16|
|---|---|---|---|---|
|Reserved|UDEN[1:0]|UDEN[1:0]|ODSWE<br>N|ODEN|
|Reserved|rw|rw|rw|rw|


|15 14|Col2|13|12|11|10|9|8|7 6 5|Col10|Col11|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|VOS[1:0]|VOS[1:0]|ADCDC1|Res.|MRUDS|LPUDS|FPDS|DBP|PLS[2:0]|PLS[2:0]|PLS[2:0]|PVDE|CSBF|CWUF|PDDS|LPDS|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rc_w1|rc_w1|rw|rw|



Bits 31:20 Reserved, must be kept at reset value.


Bits 19:18 **UDEN[1:0]** : Under-drive enable in stop mode

These bits are set by software. They allow to achieve a lower power consumption in Stop
mode but with a longer wake-up time.
When set, the digital area has less leakage consumption when the device enters Stop mode.

00: Under-drive disable

01: Reserved

10: Reserved

11:Under-drive enable


Bit 17 **ODSWEN** : Over-drive switching enabled.

This bit is set by software. It is cleared automatically by hardware after exiting from Stop
mode or when the ODEN bit is reset. When set, It is used to switch to Over-drive mode.
To set or reset the ODSWEN bit, the HSI or HSE must be selected as system clock.
The ODSWEN bit must only be set when the ODRDY flag is set to switch to Over-drive
mode.

0: Over-drive switching disabled
1: Over-drive switching enable d

_Note: On any over-drive switch (enabled or disabled), the system clock is stalled during the_
_internal voltage set up._


Bit 16 **ODEN** : Over-drive enable

This bit is set by software. It is cleared automatically by hardware after exiting from Stop
mode. It is used to enabled the Over-drive mode in order to reach a higher frequency.
To set or reset the ODEN bit, the HSI or HSE must be selected as system clock. When the
ODEN bit is set, the application must first wait for the Over-drive ready flag (ODRDY) to be
set before setting the ODSWEN bit.

0: Over-drive disabled

1: Over-drive enabled


146/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


Bits 15:14 **VOS[1:0]** : Regulator voltage scaling output selection

These bits control the main internal voltage regulator output voltage to achieve a trade-off
between performance and power consumption when the device does not operate at the
maximum frequency (refer to the STM32F42xx and STM32F43xx datasheets for more
details).
These bits can be modified only when the PLL is OFF. The new value programmed is active
only when the PLL is ON. When the PLL is OFF, the voltage scale 3 is automatically
selected.

00: Reserved (Scale 3 mode selected)

01: Scale 3 mode

10: Scale 2 mode

11: Scale 1 mode (reset value)


Bit 13 **ADCDC1** :

0: No effect.

1: Refer to AN4073 for details on how to use this bit.

_Note: This bit can only be set when operating at supply voltage range 2.7 to 3.6V and when_
_the Prefetch is OFF._


Bit 12 Reserved, must be kept at reset value.


Bit 11 **MRUDS** : Main regulator in deepsleep under-drive mode

This bit is set and cleared by software.
0: Main regulator ON when the device is in Stop mode
1: Main Regulator in under-drive mode and Flash memory in power-down when the device is
in Stop under-drive mode.


Bit 10 **LPUDS** : Low-power regulator in deepsleep under-drive mode

This bit is set and cleared by software.
0: Low-power regulator ON if LPDS bit is set when the device is in Stop mode
1: Low-power regulator in under-drive mode if LPDS bit is set and Flash memory in powerdown when the device is in Stop under-drive mode.


Bit 9 **FPDS** : Flash power-down in Stop mode

When set, the Flash memory enters power-down mode when the device enters Stop mode.
This allows to achieve a lower consumption in stop mode but a longer restart time.
0: Flash memory not in power-down when the device is in Stop mode
1: Flash memory in power-down when the device is in Stop mode


Bit 8 **DBP** : Disable backup domain write protection

In reset state, the RCC_BDCR register, the RTC registers (including the backup registers),
and the BRE bit of the PWR_CSR register, are protected against parasitic write access. This
bit must be set to enable write access to these registers.

0: Access to RTC and RTC Backup registers and backup SRAM disabled
1: Access to RTC and RTC Backup registers and backup SRAM enabled


RM0090 Rev 21 147/1757



151


**Power controller (PWR)** **RM0090**


Bits 7:5 **PLS[2:0]:** PVD level selection

These bits are written by software to select the voltage threshold detected by the

programmable voltage detector

000: 2.0 V

001: 2.1 V

010: 2.3 V

011: 2.5 V

100: 2.6 V

101: 2.7 V

110: 2.8 V

111: 2.9 V

_Note: Refer to the electrical characteristics of the datasheet for more details._


Bit 4 **PVDE:** Programmable voltage detector enable

This bit is set and cleared by software.

0: PVD disabled

1: PVD enabled


Bit 3 **CSBF** : Clear standby flag

This bit is always read as 0.

0: No effect

1: Clear the SBF Standby Flag (write).


Bit 2 **CWUF:** Clear wake-up flag

This bit is always read as 0.

0: No effect

1: Clear the WUF Wake-up Flag **after 2 System clock cycles**


Bit 1 **PDDS** : Power-down deepsleep

This bit is set and cleared by software. It works together with the LPDS bit.

0: Enter Stop mode when the CPU enters deepsleep. The regulator status depends on the
LPDS bit.

1: Enter Standby mode when the CPU enters deepsleep.


Bit 0 **LPDS:** Low-power deepsleep

This bit is set and cleared by software. It works together with the PDDS bit.

0:Main voltage regulator ON during Stop mode
1: Low-power voltage regulator ON during Stop mode


148/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**


**5.5.2** **PWR power control/status register (PWR_CSR)**
**for STM32F42xxx and STM32F43xxx**


Address offset: 0x04


Reset value: 0x0000 0000 (not reset by wake-up from Standby mode)


Additional APB cycles are needed to read this register versus a standard APB read.


|31 30 29 28 27 26 25 24 23 22 21 20|19 18|Col3|17|16|
|---|---|---|---|---|
|Reserved|UDRDY[1:0]|UDRDY[1:0]|ODSWRDY|ODRDY|
|Reserved|rc_w1|rc_w1|r|r|





|15|14|13 12 11 10|9|8|7 6 5 4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|
|Res|VOS<br>RDY|Reserved|BRE|EWUP|Reserved.|BRR|PVDO|SBF|WUF|
|Res|r|r|rw|rw|rw|r|r|r|r|


Bits 31:20 Reserved, must be kept at reset value.


Bits 19:18 **UDRDY[1:0]** : Under-drive ready flag

These bits are set by hardware when MCU entered stop Under-drive mode and exited.
When the under-drive mode is enabled, these bits are not set as long as the MCU has not
entered stop mode yet. They are cleared by programming them to 1.

00: Under-drive is disabled

01: Reserved

10: Reserved

11:Under-drive mode is activated in Stop mode.


Bit 17 **ODSWRDY** : Over-drive mode switching ready

0: Over-drive mode is not active.

1: Over-drive mode is active on digital area on 1.2 V domain


Bit 16 **ODRDY** : Over-drive mode ready

0: Over-drive mode not ready.
1: Over-drive mode ready


Bit 14 **VOSRDY** : Regulator voltage scaling output selection ready bit

0: Not ready
1: Ready


Bits 13:10 Reserved, must be kept at reset value.


Bit 9 **BRE** : Backup regulator enable

When set, the Backup regulator (used to maintain backup SRAM content in Standby and
V BAT modes) is enabled. If BRE is reset, the backup regulator is switched off. The backup
SRAM can still be used but its content is lost in the Standby and V BAT modes. Once set, the
application must wait that the Backup Regulator Ready flag (BRR) is set to indicate that the
data written into the RAM is maintained in the Standby and V BAT modes.
0: Backup regulator disabled
1: Backup regulator enabled

_Note: This bit is not reset when the device wakes up from Standby mode, by a system reset,_
_or by a power reset._

_The DBP bit of the PWR_CR register must be set before BRE can be written._


RM0090 Rev 21 149/1757



151


**Power controller (PWR)** **RM0090**


Bit 8 **EWUP** : Enable WKUP pin

This bit is set and cleared by software.
0: WKUP pin is used for general purpose I/O. An event on the WKUP pin does not wake up
the device from Standby mode.
1: WKUP pin is used for wake-up from Standby mode and forced in input pull down
configuration (rising edge on WKUP pin wakes-up the system from Standby mode).

_Note: This bit is reset by a system reset._


Bits 7:4 Reserved, must be kept at reset value.


Bit 3 **BRR** : Backup regulator ready

Set by hardware to indicate that the Backup Regulator is ready.
0: Backup Regulator not ready
1: Backup Regulator ready

_Note: This bit is not reset when the device wakes up from Standby mode or by a system reset_
_or power reset._


Bit 2 **PVDO:** PVD output

This bit is set and cleared by hardware. It is valid only if PVD is enabled by the PVDE bit.
0: V DD is higher than the PVD threshold selected with the PLS[2:0] bits.
1: V DD is lower than the PVD threshold selected with the PLS[2:0] bits.
_Note: The PVD is stopped by Standby mode. For this reason, this bit is equal to 0 after_
_Standby or reset until the PVDE bit is set._


Bit 1 **SBF:** Standby flag

This bit is set by hardware and cleared only by a POR/PDR (power-on reset/power-down
reset) or by setting the CSBF bit in the _PWR power control register (PWR_CR) for_
_STM32F405xx/07xx and STM32F415xx/17xx_

0: Device has not been in Standby mode
1: Device has been in Standby mode


Bit 0 **WUF:** Wake-up flag

This bit is set by hardware and cleared either by a system reset or by setting the CWUF bit in
the PWR_CR register.
0: No wake-up event occurred
1: A wake-up event was received from the WKUP pin or from the RTC alarm (Alarm A or
Alarm B), RTC Tamper event, RTC TimeStamp event or RTC Wake-up).

_Note: An additional wake-up event is detected if the WKUP pin is enabled (by setting the_
_EWUP bit) when the WKUP pin level is already high._


150/1757 RM0090 Rev 21


**RM0090** **Power controller (PWR)**

## **5.6 PWR register map**


The following table summarizes the PWR registers.


**Table 32. PWR - register map and reset values for**
**STM32F405xx/07xx and STM32F415xx/17xx**

















|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x000|**PWR_CR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|VOS<br>|Reserved|Reserved|Reserved|Reserved|FPDS<br>|DBP<br>|PLS[2:0]<br><br><br>|PLS[2:0]<br><br><br>|PLS[2:0]<br><br><br>|PVDE<br>|CSBF<br>|CWUF<br>|PDDS<br>|LPDS<br>|
|0x000|**PWR_CR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|~~1~~|~~1~~|~~1~~|~~1~~|~~1~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x004|**PWR_CSR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|VOSRDY<br>|Reserved|Reserved|Reserved|Reserved|BRE<br>|EWUP<br>|Reserved|Reserved|Reserved|Reserved|BRR<br>|PVDO<br>|SBF<br>|WUF<br>|
|0x004|**PWR_CSR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|


**Table 33. PWR - register map and reset values for STM32F42xxx and STM32F43xxx**















|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x000|PWR_CR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|UDEN[1:0]<br><br>|UDEN[1:0]<br><br>|ODSWEN<br>|ODEN<br>|VOS[1:0]<br><br>|VOS[1:0]<br><br>|ADCDC1<br>|Reserved|MRUDS<br>|LPUDS<br>|FPDS<br>|DBP<br>|PLS[2:0]<br><br><br>|PLS[2:0]<br><br><br>|PLS[2:0]<br><br><br>|PVDE<br>|CSBF<br>|CWUF<br>|PDDS<br>|LPDS<br>|
|0x000|PWR_CR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|~~0~~|~~0~~|~~0~~|~~0~~|~~1~~|~~1~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x004|PWR_CSR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|UDRDY[1:0]<br><br>|UDRDY[1:0]<br><br>|ODSWRDY<br>|ODRDY<br>|Reserved|VOSRDY<br>|Reserved|Reserved|Reserved|Reserved|BRE<br>0|EWUP<br>0|Reserved|Reserved|Reserved|Reserved|BRR<br>0|PVDO<br>0|SBF<br>0|WUF<br>0|
|0x004|PWR_CSR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|


Refer to _Section 2.3: Memory map_ for the register boundary addresses.


RM0090 Rev 21 151/1757



151


