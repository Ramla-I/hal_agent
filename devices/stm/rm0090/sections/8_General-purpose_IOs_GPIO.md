**General-purpose I/Os (GPIO)** **RM0090**

# **8 General-purpose I/Os (GPIO)**


This section applies to the whole STM32F4xx family, unless otherwise specified.

## **8.1 GPIO introduction**


Each general-purpose I/O port has four 32-bit configuration registers (GPIOx_MODER,
GPIOx_OTYPER, GPIOx_OSPEEDR and GPIOx_PUPDR), two 32-bit data registers
(GPIOx_IDR and GPIOx_ODR), a 32-bit set/reset register (GPIOx_BSRR), a 32-bit locking
register (GPIOx_LCKR) and two 32-bit alternate function selection register (GPIOx_AFRH
and GPIOx_AFRL).

## **8.2 GPIO main features**


      - Up to 16 I/Os under control


      - Output states: push-pull or open drain + pull-up/down


      - Output data from output data register (GPIOx_ODR) or peripheral (alternate function
output)


      - Speed selection for each I/O


      - Input states: floating, pull-up/down, analog


      - Input data to input data register (GPIOx_IDR) or peripheral (alternate function input)


      - Bit set and reset register (GPIOx_BSRR) for bitwise write access to GPIOx_ODR


      - Locking mechanism (GPIOx_LCKR) provided to freeze the I/O configuration


      - Analog function


      - Alternate function input/output selection registers (at most 16 AFs per I/O)


      - Fast toggle capable of changing every two clock cycles


      - Highly flexible pin multiplexing allows the use of I/O pins as GPIOs or as one of several
peripheral functions

## **8.3 GPIO functional description**


Subject to the specific hardware characteristics of each I/O port listed in the datasheet, each
port bit of the general-purpose I/O (GPIO) ports can be individually configured by software in
several modes:


      - Input floating


      - Input pull-up


      - Input-pull-down


      - Analog


      - Output open-drain with pull-up or pull-down capability


      - Output push-pull with pull-up or pull-down capability


      - Alternate function push-pull with pull-up or pull-down capability


      - Alternate function open-drain with pull-up or pull-down capability


270/1757 RM0090 Rev 21


**RM0090** **General-purpose I/Os (GPIO)**


Each I/O port bit is freely programmable, however the I/O port registers have to be
accessed as 32-bit words, half-words or bytes. The purpose of the GPIOx_BSRR register is
to allow atomic read/modify accesses to any of the GPIO registers. In this way, there is no
risk of an IRQ occurring between the read and the modify access.


_Figure 25_ shows the basic structure of a 5 V tolerant I/O port bit. _Table 40_ gives the possible
port bit configurations.


**Figure 25. Basic structure of a five-volt tolerant I/O port bit**







































1. V DD_FT is a potential specific to five-volt tolerant I/Os and different from V DD .


**Table 36. Port bit configuration table** **[(1)]**

















|MODER(i)<br>[1:0]|OTYPER(i)|OSPEEDR(i)<br>[B:A]|PUPDR(i)<br>[1:0]|Col5|I/O configuration|Col7|
|---|---|---|---|---|---|---|
|01|0|SPEED<br>[B:A]|0|0|GP output|PP|
|01|0|0|0|1|GP output|PP + PU|
|01|0|0|1|0|GP output|PP + PD|
|01|0|0|1|1|Reserved|Reserved|
|01|1|1|0|0|GP output|OD|
|01|1|1|0|1|GP output|OD + PU|
|01|1|1|1|0|GP output|OD + PD|
|01|1|1|1|1|Reserved (GP output OD)|Reserved (GP output OD)|


RM0090 Rev 21 271/1757



291


**General-purpose I/Os (GPIO)** **RM0090**


**Table 36. Port bit configuration table** **[(1)]** **(continued)**


















|MODER(i)<br>[1:0]|OTYPER(i)|OSPEEDR(i)<br>[B:A]|Col4|PUPDR(i)<br>[1:0]|Col6|I/O configuration|Col8|
|---|---|---|---|---|---|---|---|
|10|0|SPEED<br>[B:A]|SPEED<br>[B:A]|0|0|AF|PP|
|10|0|0|0|0|1|AF|PP + PU|
|10|0|0|0|1|0|AF|PP + PD|
|10|0|0|0|1|1|Reserved|Reserved|
|10|1|1|1|0|0|AF|OD|
|10|1|1|1|0|1|AF|OD + PU|
|10|1|1|1|1|0|AF|OD + PD|
|10|1|1|1|1|1|Reserved|Reserved|
|00|x|x|x|0|0|Input|Floating|
|00|x|x|x|0|1|Input|PU|
|00|x|x|x|1|0|Input|PD|
|00|x|x|x|1|1|Reserved (input floating)|Reserved (input floating)|
|11|x|x|x|0|0|Input/output|Analog|
|11|x|x|x|0|1|Reserved|Reserved|
|11|x|x|x|1|0|0|0|
|11|x|x|x|1|1|1|1|



1. GP = general-purpose, PP = push-pull, PU = pull-up, PD = pull-down, OD = open-drain, AF = alternate
function.


**8.3.1** **General-purpose I/O (GPIO)**


During and just after reset, the alternate functions are not active and the I/O ports are
configured in input floating mode.


The debug pins are in AF pull-up/pull-down after reset:


      - PA15: JTDI in pull-up


      - PA14: JTCK/SWCLK in pull-down


      - PA13: JTMS/SWDAT in pull-up


      - PB4: NJTRST in pull-up


      - PB3: JTDO in floating state


When the pin is configured as output, the value written to the output data register
(GPIOx_ODR) is output on the I/O pin. It is possible to use the output driver in push-pull
mode or open-drain mode (only the N-MOS is activated when 0 is output).


The input data register (GPIOx_IDR) captures the data present on the I/O pin at every AHB1
clock cycle.


All GPIO pins have weak internal pull-up and pull-down resistors, which can be activated or
not depending on the value in the GPIOx_PUPDR register.


272/1757 RM0090 Rev 21


**RM0090** **General-purpose I/Os (GPIO)**


**8.3.2** **I/O pin multiplexer and mapping**


The microcontroller I/O pins are connected to onboard peripherals/modules through a
multiplexer that allows only one peripheral’s alternate function (AF) connected to an I/O pin
at a time. In this way, there can be no conflict between peripherals sharing the same I/O pin.


Each I/O pin has a multiplexer with sixteen alternate function inputs (AF0 to AF15) that can
be configured through the GPIOx_AFRL (for pin 0 to 7) and GPIOx_AFRH (for pin 8 to 15)
registers:


      - After reset all I/Os are connected to the system’s alternate function 0 (AF0)


      - The peripherals’ alternate functions are mapped from AF1 to AF13

      - Cortex [®] -M4 with FPU EVENTOUT is mapped on AF15


This structure is shown in _Figure 26_ below.


In addition to this flexible I/O multiplexing architecture, each peripheral has alternate
functions mapped onto different I/O pins to optimize the number of peripherals available in
smaller packages.


To use an I/O in a given configuration, proceed as follows:


      - **System function**


Connect the I/O to AF0 and configure it depending on the function used:


–
JTAG/SWD, after each device reset these pins are assigned as dedicated pins
immediately usable by the debugger host (not controlled by the GPIO controller)


–
RTC_REFIN: this pin should be configured in Input floating mode


–
MCO1 and MCO2: these pins have to be configured in alternate function mode.


_Note:_ _The user can disable some or all of the JTAG/SWD pins and so release the associated pins_
_for GPIO usage (released pins highlighted in gray in the table)._


For more details refer to _Section 7.2.10: Clock-out capability_ and _Section 6.2.10: Clock-out_
_capability_ .


RM0090 Rev 21 273/1757



291


**General-purpose I/Os (GPIO)** **RM0090**


**Table 37. Flexible SWJ-DP pin assignment**











|Available debug ports|SWJ I/O pin assigned|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
|**Available debug ports**|**PA13 /**<br>**JTMS/**<br>**SWDIO**|**PA14 /**<br>**JTCK/**<br>**SWCLK**|**PA15 /**<br>**JTDI**|**PB3 /**<br>**JTDO**|**PB4/**<br>**NJTRST**|
|Full SWJ (JTAG-DP + SW-DP) - Reset state|X|X|X|X|X|
|Full SWJ (JTAG-DP + SW-DP) but without<br>NJTRST|X|X|X|X|X|
|JTAG-DP Disabled and SW-DP Enabled|X|X|X|X|X|
|JTAG-DP Disabled and SW-DP Disabled|JTAG-DP Disabled and SW-DP Disabled|JTAG-DP Disabled and SW-DP Disabled|JTAG-DP Disabled and SW-DP Disabled|JTAG-DP Disabled and SW-DP Disabled|JTAG-DP Disabled and SW-DP Disabled|



      - **GPIO**


Configure the desired I/O as output or input in the GPIOx_MODER register.


      - **Peripheral alternate function**


For the ADC and DAC, configure the desired I/O as analog in the GPIOx_MODER
register.


For other peripherals:


–
Configure the desired I/O as an alternate function in the GPIOx_MODER register


–
Select the type, pull-up/pull-down and output speed via the GPIOx_OTYPER,
GPIOx_PUPDR and GPIOx_OSPEEDR registers, respectively


–
Connect the I/O to the desired AFx in the GPIOx_AFRL or GPIOx_AFRH register


      - **EVENTOUT**

Configure the I/O pin used to output the Cortex [®] -M4 with FPU EVENTOUT signal by
connecting it to AF15


_Note:_ _EVENTOUT is not mapped onto the following I/O pins: PC13, PC14, PC15, PH0, PH1 and_
_PI8._


Refer to the “Alternate function mapping” table in the datasheets for the detailed mapping of
the system and peripherals’ alternate function I/O pins.


274/1757 RM0090 Rev 21


**RM0090** **General-purpose I/Os (GPIO)**


**Figure 26. Selecting an alternate function on STM32F405xx/07xx and**
**STM32F415xx/17xx**









1. Configured in FS.







RM0090 Rev 21 275/1757



291


**General-purpose I/Os (GPIO)** **RM0090**


**Figure 27. Selecting an alternate function on STM32F42xxx and STM32F43xxx**









1. Configured in FS.


276/1757 RM0090 Rev 21






**RM0090** **General-purpose I/Os (GPIO)**


**8.3.3** **I/O port control registers**


Each of the GPIOs has four 32-bit memory-mapped control registers (GPIOx_MODER,
GPIOx_OTYPER, GPIOx_OSPEEDR, GPIOx_PUPDR) to configure up to 16 I/Os.


The GPIOx_MODER register is used to select the I/O direction (input, output, AF, analog).
The GPIOx_OTYPER and GPIOx_OSPEEDR registers are used to select the output type
(push-pull or open-drain) and speed (the I/O speed pins are directly connected to the
corresponding GPIOx_OSPEEDR register bits whatever the I/O direction). The
GPIOx_PUPDR register is used to select the pull-up/pull-down whatever the I/O direction.


**8.3.4** **I/O port data registers**


Each GPIO has two 16-bit memory-mapped data registers: input and output data registers
(GPIOx_IDR and GPIOx_ODR). GPIOx_ODR stores the data to be output, it is read/write
accessible. The data input through the I/O are stored into the input data register
(GPIOx_IDR), a read-only register.


See _Section 8.4.5: GPIO port input data register (GPIOx_IDR) (x = A..I/J/K)_ and
_Section 8.4.6: GPIO port output data register (GPIOx_ODR) (x = A..I/J/K)_ for the register
descriptions.


**8.3.5** **I/O data bitwise handling**


The bit set reset register (GPIOx_BSRR) is a 32-bit register which allows the application to
set and reset each individual bit in the output data register (GPIOx_ODR). The bit set reset
register has twice the size of GPIOx_ODR.


To each bit in GPIOx_ODR, correspond two control bits in GPIOx_BSRR: BSRR(i) and
BSRR(i+SIZE). When written to 1, bit BSRR(i) sets the corresponding ODR(i) bit. When
written to 1, bit BSRR(i+SIZE) resets the ODR(i) corresponding bit.


Writing any bit to 0 in GPIOx_BSRR does not have any effect on the corresponding bit in
GPIOx_ODR. If there is an attempt to both set and reset a bit in GPIOx_BSRR, the set
action takes priority.


Using the GPIOx_BSRR register to change the values of individual bits in GPIOx_ODR is a
“one-shot” effect that does not lock the GPIOx_ODR bits. The GPIOx_ODR bits can always
be accessed directly. The GPIOx_BSRR register provides a way of performing atomic
bitwise handling.


There is no need for the software to disable interrupts when programming the GPIOx_ODR
at bit level: it is possible to modify one or more bits in a single atomic AHB1 write access.


**8.3.6** **GPIO locking mechanism**


It is possible to freeze the GPIO control registers by applying a specific write sequence to
the GPIOx_LCKR register. The frozen registers are GPIOx_MODER, GPIOx_OTYPER,
GPIOx_OSPEEDR, GPIOx_PUPDR, GPIOx_AFRL and GPIOx_AFRH.


To write the GPIOx_LCKR register, a specific write / read sequence has to be applied. When
the right LOCK sequence is applied to bit 16 in this register, the value of LCKR[15:0] is used
to lock the configuration of the I/Os (during the write sequence the LCKR[15:0] value must
be the same). When the LOCK sequence has been applied to a port bit, the value of the port
bit can no longer be modified until the next MCU or peripheral reset. Each GPIOx_LCKR bit


RM0090 Rev 21 277/1757



291


**General-purpose I/Os (GPIO)** **RM0090**


freezes the corresponding bit in the control registers (GPIOx_MODER, GPIOx_OTYPER,
GPIOx_OSPEEDR, GPIOx_PUPDR, GPIOx_AFRL and GPIOx_AFRH).


The LOCK sequence (refer to _Section 8.4.8: GPIO port configuration lock register_
_(GPIOx_LCKR) (x = A..I/J/K)_ ) can only be performed using a word (32-bit long) access to
the GPIOx_LCKR register due to the fact that GPIOx_LCKR bit 16 has to be set at the same
time as the [15:0] bits.


For more details refer to LCKR register description in _Section 8.4.8: GPIO port configuration_
_lock register (GPIOx_LCKR) (x = A..I/J/K)_ .


**8.3.7** **I/O alternate function input/output**


Two registers are provided to select one out of the sixteen alternate function inputs/outputs
available for each I/O. With these registers, you can connect an alternate function to some
other pin as required by your application.
This means that a number of possible peripheral functions are multiplexed on each GPIO
using the GPIOx_AFRL and GPIOx_AFRH alternate function registers. The application can
thus select any one of the possible functions for each I/O. The AF selection signal being
common to the alternate function input and alternate function output, a single channel is
selected for the alternate function input/output of one I/O.


To know which functions are multiplexed on each GPIO pin, refer to the datasheets.


_Note:_ _The application is allowed to select one of the possible peripheral functions for each I/O at a_
_time._


**8.3.8** **External interrupt/wake-up lines**


All ports have external interrupt capability. To use external interrupt lines, the port must be
configured in input mode, refer to _Section 12.2: External interrupt/event controller (EXTI)_
and _Section 12.2.3: Wake-up event management_ .


**8.3.9** **Input configuration**


When the I/O port is programmed as Input:


      - the output buffer is disabled


      - the Schmitt trigger input is activated


      - the pull-up and pull-down resistors are activated depending on the value in the
GPIOx_PUPDR register


      - The data present on the I/O pin are sampled into the input data register every AHB1
clock cycle


      - A read access to the input data register provides the I/O State


_Figure 28_ shows the input configuration of the I/O port bit.


278/1757 RM0090 Rev 21


**RM0090** **General-purpose I/Os (GPIO)**


**Figure 28. Input floating/pull up/pull down configurations**









**8.3.10** **Output configuration**

















When the I/O port is programmed as output:


- The output buffer is enabled:


–
Open drain mode: A “0” in the Output register activates the N-MOS whereas a “1”
in the Output register leaves the port in Hi-Z (the P-MOS is never activated)


–
Push-pull mode: A “0” in the Output register activates the N-MOS whereas a “1” in
the Output register activates the P-MOS


- The Schmitt trigger input is activated


- The weak pull-up and pull-down resistors are activated or not depending on the value
in the GPIOx_PUPDR register


- The data present on the I/O pin are sampled into the input data register every AHB1
clock cycle


- A read access to the input data register gets the I/O state


- A read access to the output data register gets the last written value


_Figure 29_ shows the output configuration of the I/O port bit.


RM0090 Rev 21 279/1757



291


**General-purpose I/Os (GPIO)** **RM0090**


**Figure 29. Output configuration**





















**8.3.11** **Alternate function configuration**















When the I/O port is programmed as alternate function:


- The output buffer can be configured as open-drain or push-pull


- The output buffer is driven by the signal coming from the peripheral (transmitter enable
and data)


- The Schmitt trigger input is activated


- The weak pull-up and pull-down resistors are activated or not depending on the value
in the GPIOx_PUPDR register


- The data present on the I/O pin are sampled into the input data register every AHB1
clock cycle


- A read access to the input data register gets the I/O state


_Figure 30_ shows the Alternate function configuration of the I/O port bit.


**Figure 30. Alternate function configuration**



























280/1757 RM0090 Rev 21


**RM0090** **General-purpose I/Os (GPIO)**


**8.3.12** **Analog configuration**


When the I/O port is programmed as analog configuration:


      - The output buffer is disabled


      - The Schmitt trigger input is deactivated, providing zero consumption for every analog
value of the I/O pin. The output of the Schmitt trigger is forced to a constant value (0).


      - The weak pull-up and pull-down resistors are disabled


      - Read access to the input data register gets the value “0”


_Note:_ _In the analog configuration, the I/O pins cannot be 5 Volt tolerant._


_Figure 31_ shows the high-impedance, analog-input configuration of the I/O port bit.


**Figure 31. High impedance-analog configuration**

























**8.3.13** **Using the OSC32_IN/OSC32_OUT pins as GPIO PC14/PC15**
**port pins**


The LSE oscillator pins OSC32_IN and OSC32_OUT can be used as general-purpose
PC14 and PC15 I/Os, respectively, when the LSE oscillator is off. The PC14 and PC15 I/Os
are only configured as LSE oscillator pins OSC32_IN and OSC32_OUT when the LSE
oscillator is ON. This is done by setting the LSEON bit in the RCC_BDCR register. The LSE
has priority over the GPIO function.


_Note:_ _The PC14/PC15 GPIO functionality is lost when the 1.2 V domain is powered off (by the_
_device entering the standby mode) or when the backup domain is supplied by V_ _BAT_ _(V_ _DD_ _no_
_more supplied). In this case the I/Os are set in analog input mode._


**8.3.14** **Using the OSC_IN/OSC_OUT pins as GPIO PH0/PH1 port pins**


The HSE oscillator pins OSC_IN/OSC_OUT can be used as general-purpose PH0/PH1
I/Os, respectively, when the HSE oscillator is OFF. (after reset, the HSE oscillator is off). The
PH0/PH1 I/Os are only configured as OSC_IN/OSC_OUT HSE oscillator pins when the
HSE oscillator is ON. This is done by setting the HSEON bit in the RCC_CR register. The
HSE has priority over the GPIO function.


RM0090 Rev 21 281/1757



291


**General-purpose I/Os (GPIO)** **RM0090**


**8.3.15** **Selection of RTC_AF1 and RTC_AF2 alternate functions**


The STM32F4xx feature two GPIO pins RTC_AF1 and RTC_AF2 that can be used for the
detection of a tamper or time stamp event, or RTC_ALARM, or RTC_CALIB RTC outputs.


       - The RTC_AF1 (PC13) can be used for the following purposes:


RTC_ALARM output: this output can be RTC Alarm A, RTC Alarm B or RTC Wake-up
depending on the OSEL[1:0] bits in the RTC_CR register


       - RTC_CALIB output: this feature is enabled by setting the COE[23] in the RTC_CR
register


       - RTC_TAMP1: tamper event detection


       - RTC_TS: time stamp event detection


The RTC_AF2 (PI8) can be used for the following purposes:


       - RTC_TAMP1: tamper event detection


       - RTC_TAMP2: tamper event detection


       - RTC_TS: time stamp event detection


The selection of the corresponding pin is performed through the RTC_TAFCR register as
follows:


       - TAMP1INSEL is used to select which pin is used as the RTC_TAMP1 tamper input


       - TSINSEL is used to select which pin is used as the RTC_TS time stamp input


       - ALARMOUTTYPE is used to select whether the RTC_ALARM is output in push-pull or
open-drain mode


The output mechanism follows the priority order listed in _Table 38_ and _Table 39_ .


**Table 38. RTC_AF1 pin** **[(1)]**





















|Pin<br>configuration<br>and function|RTC_ALARM<br>enabled|RTC_CALIB<br>enabled|Tamper<br>enabled|Time<br>stamp<br>enabled|TAMP1INSEL<br>TAMPER1<br>pin selection|TSINSEL<br>TIMESTAMP<br>pin<br>selection|ALARMOUTTYPE<br>RTC_ALARM<br>configuration|
|---|---|---|---|---|---|---|---|
|Alarm out<br>output OD|1|Don’t care|Don’t<br>care|Don’t<br>care|Don’t care|Don’t care|0|
|Alarm out<br>output PP|1|Don’t care|Don’t<br>care|Don’t<br>care|Don’t care|Don’t care|1|
|Calibration<br>out output PP|0|1|Don’t<br>care|Don’t<br>care|Don’t care|Don’t care|Don’t care|
|TAMPER1<br>input floating|0|0|1|0|0|Don’t care|Don’t care|
|TIMESTAMP<br>and<br>TAMPER1<br>input floating|0|0|1|1|0|0|Don’t care|
|TIMESTAMP<br>input floating|0|0|0|1|Don’t care|0|Don’t care|
|Standard<br>GPIO|0|0|0|0|Don’t care|Don’t care|Don’t care|


1. OD: open drain; PP: push-pull.


282/1757 RM0090 Rev 21


**RM0090** **General-purpose I/Os (GPIO)**


**Table 39. RTC_AF2 pin**













|Pin configuration and function|Tamper<br>enabled|Time<br>stamp<br>enabled|TAMP1INSEL<br>TAMPER1<br>pin selection|TSINSEL<br>TIMESTAMP<br>pin<br>selection|ALARMOUTTYPE<br>RTC_ALARM<br>configuration|
|---|---|---|---|---|---|
|TAMPER1 input floating|1|0|1|Don’t care|Don’t care|
|TIMESTAMP and TAMPER1 input<br>floating|1|1|1|1|Don’t care|
|TIMESTAMP input floating|0|1|Don’t care|1|Don’t care|
|Standard GPIO|0|0|Don’t care|Don’t care|Don’t care|


RM0090 Rev 21 283/1757



291


**General-purpose I/Os (GPIO)** **RM0090**

## **8.4 GPIO registers**


This section gives a detailed description of the GPIO registers.
For a summary of register bits, register address offsets and reset values, refer to _Table 40_ .


The GPIO registers can be accessed by byte (8 bits), half-words (16 bits) or words (32 bits).


**8.4.1** **GPIO port mode register (GPIOx_MODER) (x = A..I/J/K)**


Address offset: 0x00


Reset values:


      - 0xA800 0000 for port A


      - 0x0000 0280 for port B


      - 0x0000 0000 for other ports

|31 30|Col2|29 28|Col4|27 26|Col6|25 24|Col8|23 22|Col10|21 20|Col12|19 18|Col14|17 16|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MODER15[1:0]|MODER15[1:0]|MODER14[1:0]|MODER14[1:0]|MODER13[1:0]|MODER13[1:0]|MODER12[1:0]|MODER12[1:0]|MODER11[1:0]|MODER11[1:0]|MODER10[1:0]|MODER10[1:0]|MODER9[1:0]|MODER9[1:0]|MODER8[1:0]|MODER8[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14|Col2|13 12|Col4|11 10|Col6|9 8|Col8|7 6|Col10|5 4|Col12|3 2|Col14|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MODER7[1:0]|MODER7[1:0]|MODER6[1:0]|MODER6[1:0]|MODER5[1:0]|MODER5[1:0]|MODER4[1:0]|MODER4[1:0]|MODER3[1:0]|MODER3[1:0]|MODER2[1:0]|MODER2[1:0]|MODER1[1:0]|MODER1[1:0]|MODER0[1:0]|MODER0[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 2y:2y+1 **MODERy[1:0]:** Port x configuration bits (y = 0..15)

These bits are written by software to configure the I/O direction mode.
00: Input (reset state)
01: General purpose output mode
10: Alternate function mode

11: Analog mode


**8.4.2** **GPIO port output type register (GPIOx_OTYPER)**
**(x = A..I/J/K)**


Address offset: 0x04


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|OT15|OT14|OT13|OT12|OT11|OT10|OT9|OT8|OT7|OT6|OT5|OT4|OT3|OT2|OT1|OT0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **OTy** : Port x configuration bits (y = 0..15)

These bits are written by software to configure the output type of the I/O port.
0: Output push-pull (reset state)
1: Output open-drain


284/1757 RM0090 Rev 21


**RM0090** **General-purpose I/Os (GPIO)**


**8.4.3** **GPIO port output speed register (GPIOx_OSPEEDR)**
**(x = A..I/J/K)**


Address offset: 0x08


Reset values:


      - 0x0C00 0000 for port A


      - 0x0000 00C0 for port B


      - 0x0000 0000 for other ports

|31 30|Col2|29 28|Col4|27 26|Col6|25 24|Col8|23 22|Col10|21 20|Col12|19 18|Col14|17 16|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|OSPEEDR15<br>[1:0]|OSPEEDR15<br>[1:0]|OSPEEDR14<br>[1:0]|OSPEEDR14<br>[1:0]|OSPEEDR13<br>[1:0]|OSPEEDR13<br>[1:0]|OSPEEDR12<br>[1:0]|OSPEEDR12<br>[1:0]|OSPEEDR11<br>[1:0]|OSPEEDR11<br>[1:0]|OSPEEDR10<br>[1:0]|OSPEEDR10<br>[1:0]|OSPEEDR9<br>[1:0]|OSPEEDR9<br>[1:0]|OSPEEDR8<br>[1:0]|OSPEEDR8<br>[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14|Col2|13 12|Col4|11 10|Col6|9 8|Col8|7 6|Col10|5 4|Col12|3 2|Col14|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|OSPEEDR7[1:0]|OSPEEDR7[1:0]|OSPEEDR6[1:0]|OSPEEDR6[1:0]|OSPEEDR5[1:0]|OSPEEDR5[1:0]|OSPEEDR4[1:0]|OSPEEDR4[1:0]|OSPEEDR3[1:0]|OSPEEDR3[1:0]|OSPEEDR2[1:0]|OSPEEDR2[1:0]|OSPEEDR1<br>[1:0]|OSPEEDR1<br>[1:0]|OSPEEDR0<br>1:0]|OSPEEDR0<br>1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 2y:2y+1 **OSPEEDRy[1:0]:** Port x configuration bits (y = 0..15)

These bits are written by software to configure the I/O output speed.
00: Low speed
01: Medium speed
10: High speed
11: Very high speed

_Note: Refer to the product datasheets for the values of OSPEEDRy bits versus V_ _DD_
_range and external load._


**8.4.4** **GPIO port pull-up/pull-down register (GPIOx_PUPDR)**
**(x = A..I/J/K)**


Address offset: 0x0C


Reset values:


      - 0x6400 0000 for port A


      - 0x0000 0100 for port B


      - 0x0000 0000 for other ports

|31 30|Col2|29 28|Col4|27 26|Col6|25 24|Col8|23 22|Col10|21 20|Col12|19 18|Col14|17 16|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PUPDR15[1:0]|PUPDR15[1:0]|PUPDR14[1:0]|PUPDR14[1:0]|PUPDR13[1:0]|PUPDR13[1:0]|PUPDR12[1:0]|PUPDR12[1:0]|PUPDR11[1:0]|PUPDR11[1:0]|PUPDR10[1:0]|PUPDR10[1:0]|PUPDR9[1:0]|PUPDR9[1:0]|PUPDR8[1:0]|PUPDR8[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14|Col2|13 12|Col4|11 10|Col6|9 8|Col8|7 6|Col10|5 4|Col12|3 2|Col14|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PUPDR7[1:0]|PUPDR7[1:0]|PUPDR6[1:0]|PUPDR6[1:0]|PUPDR5[1:0]|PUPDR5[1:0]|PUPDR4[1:0]|PUPDR4[1:0]|PUPDR3[1:0]|PUPDR3[1:0]|PUPDR2[1:0]|PUPDR2[1:0]|PUPDR1[1:0]|PUPDR1[1:0]|PUPDR0[1:0]|PUPDR0[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



RM0090 Rev 21 285/1757



291


**General-purpose I/Os (GPIO)** **RM0090**


Bits 2y:2y+1 **PUPDRy[1:0]:** Port x configuration bits (y = 0..15)

These bits are written by software to configure the I/O pull-up or pull-down
00: No pull-up, pull-down
01: Pull-up
10: Pull-down

11: Reserved


**8.4.5** **GPIO port input data register (GPIOx_IDR) (x = A..I/J/K)**


Address offset: 0x10


Reset value: 0x0000 XXXX (where X means undefined)


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|IDR15|IDR14|IDR13|IDR12|IDR11|IDR10|IDR9|IDR8|IDR7|IDR6|IDR5|IDR4|IDR3|IDR2|IDR1|IDR0|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **IDRy** : Port input data (y = 0..15)

These bits are read-only and can be accessed in word mode only. They contain the input
value of the corresponding I/O port.


**8.4.6** **GPIO port output data register (GPIOx_ODR) (x = A..I/J/K)**


Address offset: 0x14


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ODR15|ODR14|ODR13|ODR12|ODR11|ODR10|ODR9|ODR8|ODR7|ODR6|ODR5|ODR4|ODR3|ODR2|ODR1|ODR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **ODRy** : Port output data (y = 0..15)

These bits can be read and written by software.

_Note: For atomic bit set/reset, the ODR bits can be individually set and reset by writing to the_
_GPIOx_BSRR register (x = A..I/J/K)._


286/1757 RM0090 Rev 21


**RM0090** **General-purpose I/Os (GPIO)**


**8.4.7** **GPIO port bit set/reset register (GPIOx_BSRR) (x = A..I/J/K)**


Address offset: 0x18


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|BR15|BR14|BR13|BR12|BR11|BR10|BR9|BR8|BR7|BR6|BR5|BR4|BR3|BR2|BR1|BR0|
|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|BS15|BS14|BS13|BS12|BS11|BS10|BS9|BS8|BS7|BS6|BS5|BS4|BS3|BS2|BS1|BS0|
|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|



Bits 31:16 **BRy:** Port x reset bit y (y = 0..15)

These bits are write-only and can be accessed in word, half-word or byte mode. A read to
these bits returns the value 0x0000.

0: No action on the corresponding ODRx bit
1: Resets the corresponding ODRx bit

_Note: If both BSx and BRx are set, BSx has priority._


Bits 15:0 **BSy:** Port x set bit y (y= 0..15)

These bits are write-only and can be accessed in word, half-word or byte mode. A read to
these bits returns the value 0x0000.

0: No action on the corresponding ODRx bit
1: Sets the corresponding ODRx bit


**8.4.8** **GPIO port configuration lock register (GPIOx_LCKR)**
**(x = A..I/J/K)**


This register is used to lock the configuration of the port bits when a correct write sequence
is applied to bit 16 (LCKK). The value of bits [15:0] is used to lock the configuration of the
GPIO. During the write sequence, the value of LCKR[15:0] must not change. When the
LOCK sequence has been applied on a port bit, the value of this port bit can no longer be
modified until the next MCU or peripheral reset.


_Note:_ _A specific write sequence is used to write to the GPIOx_LCKR register. Only word access_
_(32-bit long) is allowed during this write sequence._


Each lock bit freezes a specific configuration register (control and alternate function
registers).


Address offset: 0x1C


Reset value: 0x0000 0000


Access: 32-bit word only, read/write register

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17|16|
|---|---|
|Reserved|LCKK|
|Reserved|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|LCK15|LCK14|LCK13|LCK12|LCK11|LCK10|LCK9|LCK8|LCK7|LCK6|LCK5|LCK4|LCK3|LCK2|LCK1|LCK0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



RM0090 Rev 21 287/1757



291


**General-purpose I/Os (GPIO)** **RM0090**


Bits 31:17 Reserved, must be kept at reset value.


Bit 16 **LCKK[16]:** Lock key

This bit can be read any time. It can only be modified using the lock key write sequence.
0: Port configuration lock key not active
1: Port configuration lock key active. The GPIOx_LCKR register is locked until an MCU reset
or a peripheral reset occurs.


LOCK key write sequence:
WR LCKR[16] = ‘1’ + LCKR[15:0]
WR LCKR[16] = ‘0’ + LCKR[15:0]
WR LCKR[16] = ‘1’ + LCKR[15:0]

RD LCKR

RD LCKR[16] = ‘1’ (this read operation is optional but it confirms that the lock is active)

_Note: During the LOCK key write sequence, the value of LCK[15:0] must not change._

_Any error in the lock sequence aborts the lock._

_After the first lock sequence on any bit of the port, any read access on the LCKK bit_
_returns ‘1’ until the next CPU reset._


Bits 15:0 **LCKy:** Port x lock bit y (y= 0..15)

These bits are read/write but can only be written when the LCKK bit is ‘0.
0: Port configuration not locked
1: Port configuration locked


**8.4.9** **GPIO alternate function low register (GPIOx_AFRL) (x = A..I/J/K)**


Address offset: 0x20


Reset value: 0x0000 0000

|31 30 29 28|Col2|Col3|Col4|27 26 25 24|Col6|Col7|Col8|23 22 21 20|Col10|Col11|Col12|19 18 17 16|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|AFRL7[3:0]|AFRL7[3:0]|AFRL7[3:0]|AFRL7[3:0]|AFRL6[3:0]|AFRL6[3:0]|AFRL6[3:0]|AFRL6[3:0]|AFRL5[3:0]|AFRL5[3:0]|AFRL5[3:0]|AFRL5[3:0]|AFRL4[3:0]|AFRL4[3:0]|AFRL4[3:0]|AFRL4[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|AFRL3[3:0]|AFRL3[3:0]|AFRL3[3:0]|AFRL3[3:0]|AFRL2[3:0]|AFRL2[3:0]|AFRL2[3:0]|AFRL2[3:0]|AFRL1[3:0]|AFRL1[3:0]|AFRL1[3:0]|AFRL1[3:0]|AFRL0[3:0]|AFRL0[3:0]|AFRL0[3:0]|AFRL0[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **AFRLy:** Alternate function selection for port x bit y (y = 0..7)

These bits are written by software to configure alternate function I/Os



AFRLy selection:

0000: AF0

0001: AF1

0010: AF2

0011: AF3

0100: AF4

0101: AF5

0110: AF6

0111: AF7



1000: AF8

1001: AF9

1010: AF10

1011: AF11

1100: AF12

1101: AF13

1110: AF14

1111: AF15



288/1757 RM0090 Rev 21


**RM0090** **General-purpose I/Os (GPIO)**


**8.4.10** **GPIO alternate function high register (GPIOx_AFRH)**
**(x = A..I/J)**


Address offset: 0x24


Reset value: 0x0000 0000

|31 30 29 28|Col2|Col3|Col4|27 26 25 24|Col6|Col7|Col8|23 22 21 20|Col10|Col11|Col12|19 18 17 16|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|AFRH15[3:0]|AFRH15[3:0]|AFRH15[3:0]|AFRH15[3:0]|AFRH14[3:0]|AFRH14[3:0]|AFRH14[3:0]|AFRH14[3:0]|AFRH13[3:0]|AFRH13[3:0]|AFRH13[3:0]|AFRH13[3:0]|AFRH12[3:0]|AFRH12[3:0]|AFRH12[3:0]|AFRH12[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|AFRH11[3:0]|AFRH11[3:0]|AFRH11[3:0]|AFRH11[3:0]|AFRH10[3:0]|AFRH10[3:0]|AFRH10[3:0]|AFRH10[3:0]|AFRH9[3:0]|AFRH9[3:0]|AFRH9[3:0]|AFRH9[3:0]|AFRH8[3:0]|AFRH8[3:0]|AFRH8[3:0]|AFRH8[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **AFRHy:** Alternate function selection for port x bit y (y = 8..15)

These bits are written by software to configure alternate function I/Os



AFRHy selection:

0000: AF0

0001: AF1

0010: AF2

0011: AF3

0100: AF4

0101: AF5

0110: AF6

0111: AF7



1000: AF8

1001: AF9

1010: AF10

1011: AF11

1100: AF12

1101: AF13

1110: AF14

1111: AF15


RM0090 Rev 21 289/1757



291


**General-purpose I/Os (GPIO)** **RM0090**


**8.4.11** **GPIO register map**


The following table gives the GPIO register map and the reset values.


**Table 40. GPIO register map and reset values**













|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**GPIOA_**<br>**MODER**|MODER15[1:0]|MODER15[1:0]|MODER14[1:0]|MODER14[1:0]|MODER13[1:0]|MODER13[1:0]|MODER12[1:0]|MODER12[1:0]|MODER11[1:0]|MODER11[1:0]|MODER10[1:0]|MODER10[1:0]|MODER9[1:0]|MODER9[1:0]|MODER8[1:0]|MODER8[1:0]|MODER7[1:0]|MODER7[1:0]|MODER6[1:0]|MODER6[1:0]|MODER5[1:0]|MODER5[1:0]|MODER4[1:0]|MODER4[1:0]|MODER3[1:0]|MODER3[1:0]|MODER2[1:0]|MODER2[1:0]|MODER1[1:0]|MODER1[1:0]|MODER0[1:0]|MODER0[1:0]|
|0x00|Reset value|1|0|1|0|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00|**GPIOB_**<br>**MODER**|MODER15[1:0]|MODER15[1:0]|MODER14[1:0]|MODER14[1:0]|MODER13[1:0]|MODER13[1:0]|MODER12[1:0]|MODER12[1:0]|MODER11[1:0]|MODER11[1:0]|MODER10[1:0]|MODER10[1:0]|MODER9[1:0]|MODER9[1:0]|MODER8[1:0]|MODER8[1:0]|MODER7[1:0]|MODER7[1:0]|MODER6[1:0]|MODER6[1:0]|MODER5[1:0]|MODER5[1:0]|MODER4[1:0]|MODER4[1:0]|MODER3[1:0]|MODER3[1:0]|MODER2[1:0]|MODER2[1:0]|MODER1[1:0]|MODER1[1:0]|MODER0[1:0]|MODER0[1:0]|
|0x00|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|1|0|1|0|0|0|0|0|0|0|
|0x00|**GPIOx_MODER** <br>(where x =<br>C..I/J/K)|MODER15[1:0]|MODER15[1:0]|MODER14[1:0]|MODER14[1:0]|MODER13[1:0]|MODER13[1:0]|MODER12[1:0]|MODER12[1:0]|MODER11[1:0]|MODER11[1:0]|MODER10[1:0]|MODER10[1:0]|MODER9[1:0]|MODER9[1:0]|MODER8[1:0]|MODER8[1:0]|MODER7[1:0]|MODER7[1:0]|MODER6[1:0]|MODER6[1:0]|MODER5[1:0]|MODER5[1:0]|MODER4[1:0]|MODER4[1:0]|MODER3[1:0]|MODER3[1:0]|MODER2[1:0]|MODER2[1:0]|MODER1[1:0]|MODER1[1:0]|MODER0[1:0]|MODER0[1:0]|
|0x00|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x04|**GPIOx_**<br>**OTYPER**<br>(where x =<br>A..I/J/K)|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|OT15|OT14|OT13|OT12|OT11|OT10|OT9|OT8|OT7|OT6|OT5|OT4|OT3|OT2|OT1|OT0|
|0x04|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x08|**GPIOx_**<br>**OSPEEDR** <br>(where x =<br>A..I/J/K except<br>B)|OSPEEDR15[1:0]|OSPEEDR15[1:0]|OSPEEDR14[1:0]|OSPEEDR14[1:0]|OSPEEDR13[1:0]|OSPEEDR13[1:0]|OSPEEDR12[1:0]|OSPEEDR12[1:0]|OSPEEDR11[1:0]|OSPEEDR11[1:0]|OSPEEDR10[1:0]|OSPEEDR10[1:0]|OSPEEDR9[1:0]|OSPEEDR9[1:0]|OSPEEDR8[1:0]|OSPEEDR8[1:0]|OSPEEDR7[1:0]|OSPEEDR7[1:0]|OSPEEDR6[1:0]|OSPEEDR6[1:0]|OSPEEDR5[1:0]|OSPEEDR5[1:0]|OSPEEDR4[1:0]|OSPEEDR4[1:0]|OSPEEDR3[1:0]|OSPEEDR3[1:0]|OSPEEDR2[1:0]|OSPEEDR2[1:0]|OSPEEDR1[1:0]|OSPEEDR1[1:0]|OSPEEDR0[1:0]|OSPEEDR0[1:0]|
|0x08|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x08|**GPIOB_**<br>**OSPEEDR**|OSPEEDR15[1:0]|OSPEEDR15[1:0]|OSPEEDR14[1:0]|OSPEEDR14[1:0]|OSPEEDR13[1:0]|OSPEEDR13[1:0]|OSPEEDR12[1:0]|OSPEEDR12[1:0]|OSPEEDR11[1:0]|OSPEEDR11[1:0]|OSPEEDR10[1:0]|OSPEEDR10[1:0]|OSPEEDR9[1:0]|OSPEEDR9[1:0]|OSPEEDR8[1:0]|OSPEEDR8[1:0]|OSPEEDR7[1:0]|OSPEEDR7[1:0]|OSPEEDR6[1:0]|OSPEEDR6[1:0]|OSPEEDR5[1:0]|OSPEEDR5[1:0]|OSPEEDR4[1:0]|OSPEEDR4[1:0]|OSPEEDR3[1:0]|OSPEEDR3[1:0]|OSPEEDR2[1:0]|OSPEEDR2[1:0]|OSPEEDR1[1:0]|OSPEEDR1[1:0]|OSPEEDR0[1:0]|OSPEEDR0[1:0]|
|0x08|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|1|1|0|0|0|0|0|0|
|0x0C|**GPIOA_PUPDR**|PUPDR15[1:0]|PUPDR15[1:0]|PUPDR14[1:0]|PUPDR14[1:0]|PUPDR13[1:0]|PUPDR13[1:0]|PUPDR12[1:0]|PUPDR12[1:0]|PUPDR11[1:0]|PUPDR11[1:0]|PUPDR10[1:0]|PUPDR10[1:0]|PUPDR9[1:0]|PUPDR9[1:0]|PUPDR8[1:0]|PUPDR8[1:0]|PUPDR7[1:0]|PUPDR7[1:0]|PUPDR6[1:0]|PUPDR6[1:0]|PUPDR5[1:0]|PUPDR5[1:0]|PUPDR4[1:0]|PUPDR4[1:0]|PUPDR3[1:0]|PUPDR3[1:0]|PUPDR2[1:0]|PUPDR2[1:0]|PUPDR1[1:0]|PUPDR1[1:0]|PUPDR0[1:0]|PUPDR0[1:0]|
|0x0C|Reset value|0|1|1|0|0|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0C|**GPIOB_PUPDR**|PUPDR15[1:0]|PUPDR15[1:0]|PUPDR14[1:0]|PUPDR14[1:0]|PUPDR13[1:0]|PUPDR13[1:0]|PUPDR12[1:0]|PUPDR12[1:0]|PUPDR11[1:0]|PUPDR11[1:0]|PUPDR10[1:0]|PUPDR10[1:0]|PUPDR9[1:0]|PUPDR9[1:0]|PUPDR8[1:0]|PUPDR8[1:0]|PUPDR7[1:0]|PUPDR7[1:0]|PUPDR6[1:0]|PUPDR6[1:0]|PUPDR5[1:0]|PUPDR5[1:0]|PUPDR4[1:0]|PUPDR4[1:0]|PUPDR3[1:0]|PUPDR3[1:0]|PUPDR2[1:0]|PUPDR2[1:0]|PUPDR1[1:0]|PUPDR1[1:0]|PUPDR0[1:0]|PUPDR0[1:0]|
|0x0C|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|1|0|0|0|0|0|0|0|0|


290/1757 RM0090 Rev 21


**RM0090** **General-purpose I/Os (GPIO)**


**Table 40. GPIO register map and reset values (continued)**





|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x0C|**GPIOx_PUPDR** <br>(where x =<br>C..I/J/K)|PUPDR15[1:0]|PUPDR15[1:0]|PUPDR14[1:0]|PUPDR14[1:0]|PUPDR13[1:0]|PUPDR13[1:0]|PUPDR12[1:0]|PUPDR12[1:0]|PUPDR11[1:0]|PUPDR11[1:0]|PUPDR10[1:0]|PUPDR10[1:0]|PUPDR9[1:0]|PUPDR9[1:0]|PUPDR8[1:0]|PUPDR8[1:0]|PUPDR7[1:0]|PUPDR7[1:0]|PUPDR6[1:0]|PUPDR6[1:0]|PUPDR5[1:0]|PUPDR5[1:0]|PUPDR4[1:0]|PUPDR4[1:0]|PUPDR3[1:0]|PUPDR3[1:0]|PUPDR2[1:0]|PUPDR2[1:0]|PUPDR1[1:0]|PUPDR1[1:0]|PUPDR0[1:0]|PUPDR0[1:0]|
|0x0C|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**GPIOx_IDR** <br>(where x =<br>A..I/J/K)|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|IDR15|IDR14|IDR13|IDR12|IDR11|IDR10|IDR9|IDR8|IDR7|IDR6|IDR5|IDR4|IDR3|IDR2|IDR1|IDR0|
|0x10|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x14|**GPIOx_ODR** <br>(where x =<br>A..I/J/K)|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|ODR15|ODR14|ODR13|ODR12|ODR11|ODR10|ODR9|ODR8|ODR7|ODR6|ODR5|ODR4|ODR3|ODR2|ODR1|ODR0|
|0x14|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x18|**GPIOx_BSRR** <br>(where x =<br>A..I/J/K)|BR15|BR14|BR13|BR12|BR11|BR10|BR9|BR8|BR7|BR6|BR5|BR4|BR3|BR2|BR1|BR0|BS15|BS14|BS13|BS12|BS11|BS10|BS9|BS8|BS7|BS6|BS5|BS4|BS3|BS2|BS1|BS0|
|0x18|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x1C|**GPIOx_LCKR** <br>(where x =<br>A..I/J/K)|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|LCKK|LCK15|LCK14|LCK13|LCK12|LCK11|LCK10|LCK9|LCK8|LCK7|LCK6|LCK5|LCK4|LCK3|LCK2|LCK1|LCK0|
|0x1C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x20|**GPIOx_AFRL** <br>(where x =<br>A..I/J/K)|AFRL7[3:0]|AFRL7[3:0]|AFRL7[3:0]|AFRL7[3:0]|AFRL6[3:0]|AFRL6[3:0]|AFRL6[3:0]|AFRL6[3:0]|AFRL5[3:0]|AFRL5[3:0]|AFRL5[3:0]|AFRL5[3:0]|AFRL4[3:0]|AFRL4[3:0]|AFRL4[3:0]|AFRL4[3:0]|AFRL3[3:0]|AFRL3[3:0]|AFRL3[3:0]|AFRL3[3:0]|AFRL2[3:0]|AFRL2[3:0]|AFRL2[3:0]|AFRL2[3:0]|AFRL1[3:0]|AFRL1[3:0]|AFRL1[3:0]|AFRL1[3:0]|AFRL0[3:0]|AFRL0[3:0]|AFRL0[3:0]|AFRL0[3:0]|
|0x20|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x24|**GPIOx_AFRH** <br>(where x =<br>A..I/J)|AFRH15[3:0]|AFRH15[3:0]|AFRH15[3:0]|AFRH15[3:0]|AFRH14[3:0]|AFRH14[3:0]|AFRH14[3:0]|AFRH14[3:0]|AFRH13[3:0]|AFRH13[3:0]|AFRH13[3:0]|AFRH13[3:0]|AFRH12[3:0]|AFRH12[3:0]|AFRH12[3:0]|AFRH12[3:0]|AFRH11[3:0]|AFRH11[3:0]|AFRH11[3:0]|AFRH11[3:0]|AFRH10[3:0]|AFRH10[3:0]|AFRH10[3:0]|AFRH10[3:0]|AFRH9[3:0]|AFRH9[3:0]|AFRH9[3:0]|AFRH9[3:0]|AFRH8[3:0]|AFRH8[3:0]|AFRH8[3:0]|AFRH8[3:0]|
|0x24|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


Refer to _Section 2.3: Memory map_ for the register boundary addresses.


RM0090 Rev 21 291/1757



291


