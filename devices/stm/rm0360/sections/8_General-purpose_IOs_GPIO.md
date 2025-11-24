**RM0360** **General-purpose I/Os (GPIO)**

# **8 General-purpose I/Os (GPIO)**

## **8.1 Introduction**


Each general-purpose I/O port has four 32-bit configuration registers (GPIOx_MODER,
GPIOx_OTYPER, GPIOx_OSPEEDR and GPIOx_PUPDR), two 32-bit data registers
(GPIOx_IDR and GPIOx_ODR) and a 32-bit set/reset register (GPIOx_BSRR). Ports A and
B also have a 32-bit locking register (GPIOx_LCKR) and two 32-bit alternate function
selection registers (GPIOx_AFRH and GPIOx_AFRL).


On STM32F030xB and STM32F030xC devices, also ports C and Dhave two 32-bit alternate
function selection registers (GPIOx_AFRH and GPIOx_AFRL).

## **8.2 GPIO main features**


      - Output states: push-pull or open drain + pull-up/down


      - Output data from output data register (GPIOx_ODR) or peripheral (alternate function
output)


      - Speed selection for each I/O


      - Input states: floating, pull-up/down, analog


      - Input data to input data register (GPIOx_IDR) or peripheral (alternate function input)


      - Bit set and reset register (GPIOx_ BSRR) for bitwise write access to GPIOx_ODR


      - Locking mechanism (GPIOx_LCKR) provided to freeze the port A or B I/O port
configuration.


      - Analog function


      - Alternate function selection registers (at most 16 AFs possible per I/O)


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


Each I/O port bit is freely programmable, however the I/O port registers have to be
accessed as 32-bit words, half-words or bytes. The purpose of the GPIOx_BSRR register is


RM0360 Rev 5 125/775



141


**General-purpose I/Os (GPIO)** **RM0360**


to allow atomic read/modify accesses to any of the GPIOx_ODR registers. In this way, there
is no risk of an IRQ occurring between the read and the modify access.


_Figure 14_ shows the basic structures of a standard I/O port bit. _Table 22_ gives the possible
port bit configurations.


**Figure 14. Basic structure of an I/O port bit**























**Table 22. Port bit configuration table** **[(1)]**































|MODER(i)<br>[1:0]|OTYPER(i)|OSPEEDR(i)<br>[1:0]|PUPDR(i)<br>[1:0]|Col5|I/O configuration|Col7|
|---|---|---|---|---|---|---|
|01|0|SPEED<br>[1:0]|0|0|GP output|PP|
|01|0|0|0|1|GP output|PP + PU|
|01|0|0|1|0|GP output|PP + PD|
|01|0|0|1|1|Reserved|Reserved|
|01|1|1|0|0|GP output|OD|
|01|1|1|0|1|GP output|OD + PU|
|01|1|1|1|0|GP output|OD + PD|
|01|1|1|1|1|Reserved (GP output OD)|Reserved (GP output OD)|
|10|0|SPEED<br>[1:0]|0|0|AF|PP|
|10|0|0|0|1|AF|PP + PU|
|10|0|0|1|0|AF|PP + PD|
|10|0|0|1|1|Reserved|Reserved|
|10|1|1|0|0|AF|OD|
|10|1|1|0|1|AF|OD + PU|
|10|1|1|1|0|AF|OD + PD|
|10|1|1|1|1|Reserved|Reserved|


126/775 RM0360 Rev 5


**RM0360** **General-purpose I/Os (GPIO)**


**Table 22. Port bit configuration table** **[(1)]** **(continued)**

|MODER(i)<br>[1:0]|OTYPER(i)|OSPEEDR(i)<br>[1:0]|Col4|PUPDR(i)<br>[1:0]|Col6|I/O configuration|Col8|
|---|---|---|---|---|---|---|---|
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


During and just after reset, the alternate functions are not active and most of the I/O ports
are configured in input floating mode.


The debug pins are in AF pull-up/pull-down after reset:


      - PA14: SWCLK in pull-down


      - PA13: SWDIO in pull-up


When the pin is configured as output, the value written to the output data register
(GPIOx_ODR) is output on the I/O pin. It is possible to use the output driver in push-pull
mode or open-drain mode (only the low level is driven, high level is HI-Z).


The input data register (GPIOx_IDR) captures the data present on the I/O pin at every AHB
clock cycle.


All GPIO pins have weak internal pull-up and pull-down resistors, which can be activated or
not depending on the value in the GPIOx_PUPDR register.


**8.3.2** **I/O pin alternate function multiplexer and mapping**


The device I/O pins are connected to on-board peripherals/modules through a multiplexer
that allows only one peripheral alternate function (AF) connected to an I/O pin at a time. In
this way, there can be no conflict between peripherals available on the same I/O pin.


Each I/O pin has a multiplexer with up to sixteen alternate function inputs (AF0 to AF15) that
can be configured through the GPIOx_AFRL (for pin 0 to 7) and GPIOx_AFRH (for pin 8 to
15) registers:


      - After reset the multiplexer selection is alternate function 0 (AF0). The I/Os are
configured in alternate function mode through GPIOx_MODER register.


      - The specific alternate function assignments for each pin are detailed in the device
datasheet.


In addition to this flexible I/O multiplexing architecture, each peripheral has alternate
functions mapped onto different I/O pins to optimize the number of peripherals available in
smaller packages.


RM0360 Rev 5 127/775



141


**General-purpose I/Os (GPIO)** **RM0360**


To use an I/O in a given configuration, the user has to proceed as follows:


      - **Debug function:** after each device reset these pins are assigned as alternate function
pins immediately usable by the debugger host


      - **GPIO:** configure the desired I/O as output, input or analog in the GPIOx_MODER
register.


      - **Peripheral alternate function:**


–
Connect the I/O to the desired AFx in one of the GPIOx_AFRL or GPIOx_AFRH
register.


–
Select the type, pull-up/pull-down and output speed via the GPIOx_OTYPER,
GPIOx_PUPDR and GPIOx_OSPEEDER registers, respectively.


–
Configure the desired I/O as an alternate function in the GPIOx_MODER register.


      - **Additional functions:**


–
ADC connection can be enabled in ADC registers regardless the configured GPIO
mode. When ADC uses a GPIO, it is recommended to configure the GPIO in
analog mode, through the GPIOx_MODER register.


–
For the additional functions like RTC, WKUPx and oscillators, configure the
required function in the related RTC, PWR and RCC registers. These functions
have priority over the configuration in the standard GPIO registers.


Refer to the “Alternate function mapping” table in the device datasheet for the detailed
mapping of the alternate function I/O pins.


**8.3.3** **I/O port control registers**


Each of the GPIO ports has four 32-bit memory-mapped control registers (GPIOx_MODER,
GPIOx_OTYPER, GPIOx_OSPEEDR, GPIOx_PUPDR) to configure up to 16 I/Os. The
GPIOx_MODER register is used to select the I/O mode (input, output, AF, analog). The
GPIOx_OTYPER and GPIOx_OSPEEDR registers are used to select the output type (pushpull or open-drain) and speed. The GPIOx_PUPDR register is used to select the pullup/pull-down whatever the I/O direction.


**8.3.4** **I/O port data registers**


Each GPIO has two 16-bit memory-mapped data registers: input and output data registers
(GPIOx_IDR and GPIOx_ODR). GPIOx_ODR stores the data to be output, it is read/write
accessible. The data input through the I/O are stored into the input data register
(GPIOx_IDR), a read-only register.


See _Section 8.4.5: GPIO port input data register (GPIOx_IDR) (x = A to D, F)_ and
_Section 8.4.6: GPIO port output data register (GPIOx_ODR) (x = A to D, F)_ for the register
descriptions.


**8.3.5** **I/O data bitwise handling**


The bit set reset register (GPIOx_BSRR) is a 32-bit register which allows the application to
set and reset each individual bit in the output data register (GPIOx_ODR). The bit set reset
register has twice the size of GPIOx_ODR.


To each bit in GPIOx_ODR, correspond two control bits in GPIOx_BSRR: BS(i) and BR(i).
When written to 1, bit BS(i) **sets** the corresponding ODR(i) bit. When written to 1, bit BR(i)
**resets** the ODR(i) corresponding bit.


128/775 RM0360 Rev 5


**RM0360** **General-purpose I/Os (GPIO)**


Writing any bit to 0 in GPIOx_BSRR does not have any effect on the corresponding bit in
GPIOx_ODR. If there is an attempt to both set and reset a bit in GPIOx_BSRR, the set
action takes priority.


Using the GPIOx_BSRR register to change the values of individual bits in GPIOx_ODR is a
“one-shot” effect that does not lock the GPIOx_ODR bits. The GPIOx_ODR bits can always
be accessed directly. The GPIOx_BSRR register provides a way of performing atomic
bitwise handling.


There is no need for the software to disable interrupts when programming the GPIOx_ODR
at bit level: it is possible to modify one or more bits in a single atomic AHB write access.


**8.3.6** **GPIO locking mechanism**


It is possible to freeze the port A and B GPIO control registers by applying a specific write
sequence to the GPIOx_LCKR register. The frozen registers are GPIOx_MODER,
GPIOx_OTYPER, GPIOx_OSPEEDR, GPIOx_PUPDR, GPIOx_AFRL and GPIOx_AFRH.


To write the GPIOx_LCKR register, a specific write / read sequence has to be applied. When
the right LOCK sequence is applied to bit 16 in this register, the value of LCKR[15:0] is used
to lock the configuration of the I/Os (during the write sequence the LCKR[15:0] value must
be the same). When the LOCK sequence has been applied to a port bit, the value of the port
bit can no longer be modified until the next MCU reset or peripheral reset. Each
GPIOx_LCKR bit freezes the corresponding bit in the control registers (GPIOx_MODER,
GPIOx_OTYPER, GPIOx_OSPEEDR, GPIOx_PUPDR, GPIOx_AFRL and GPIOx_AFRH.


The LOCK sequence (refer to _Section 8.4.8: GPIO port configuration lock register_
_(GPIOx_LCKR) (x = A to B)_ ) can only be performed using a word (32-bit long) access to the
GPIOx_LCKR register due to the fact that GPIOx_LCKR bit 16 has to be set at the same
time as the [15:0] bits.


For more details refer to LCKR register description in _Section 8.4.8: GPIO port configuration_
_lock register (GPIOx_LCKR) (x = A to B)_ .


**8.3.7** **I/O alternate function input/output**


Two registers are provided to select one of the alternate function inputs/outputs available for
each I/O. With these registers, the user can connect an alternate function to some other pin
as required by the application.


This means that a number of possible peripheral functions are multiplexed on each GPIO
using the GPIOx_AFRL and GPIOx_AFRH alternate function registers. The application can
thus select any one of the possible functions for each I/O. The AF selection signal being
common to the alternate function input and alternate function output, a single channel is
selected for the alternate function input/output of a given I/O.


For code example refer to _Section A.4.2: Alternate function selection sequence on_
_page 728_ .


To know which functions are multiplexed on each GPIO pin refer to the device datasheet.


**8.3.8** **External interrupt/wake-up lines**


All ports have external interrupt capability. To use external interrupt lines, the given pin must
not be configured in analog mode or being used as oscillator pin, so the input trigger is kept
enabled.


RM0360 Rev 5 129/775



141


**General-purpose I/Os (GPIO)** **RM0360**


Refer to _Section 11.2: Extended interrupts and events controller (EXTI)_ and to
_Section 11.2.3: Event management_ .


**8.3.9** **Input configuration**


When the I/O port is programmed as input:


      - The output buffer is disabled


      - The Schmitt trigger input is activated


      - The pull-up and pull-down resistors are activated depending on the value in the
GPIOx_PUPDR register


      - The data present on the I/O pin are sampled into the input data register every AHB
clock cycle


      - A read access to the input data register provides the I/O state


_Figure 15_ shows the input configuration of the I/O port bit.


**Figure 15. Input floating / pull up / pull down configurations**



















**8.3.10** **Output configuration**


When the I/O port is programmed as output:


      - The output buffer is enabled:


–
Open drain mode: a “0” in the output register activates the N-MOS whereas a “1”
in the output register leaves the port in Hi-Z (the P-MOS is never activated)


–
Push-pull mode: a “0” in the output register activates the N-MOS whereas a “1” in
the output register activates the P-MOS


      - The Schmitt trigger input is activated


      - The pull-up and pull-down resistors are activated depending on the value in the
GPIOx_PUPDR register


      - The data present on the I/O pin are sampled into the input data register every AHB
clock cycle


      - A read access to the input data register gets the I/O state


      - A read access to the output data register gets the last written value


130/775 RM0360 Rev 5


**RM0360** **General-purpose I/Os (GPIO)**


_Figure 16_ shows the output configuration of the I/O port bit.


**Figure 16. Output configuration**





























**8.3.11** **Alternate function configuration**


When the I/O port is programmed as alternate function:


      - The output buffer can be configured in open-drain or push-pull mode


      - The output buffer is driven by the signals coming from the peripheral (transmitter
enable and data)


      - The Schmitt trigger input is activated


      - The weak pull-up and pull-down resistors are activated or not depending on the value
in the GPIOx_PUPDR register


      - The data present on the I/O pin are sampled into the input data register every AHB
clock cycle


      - A read access to the input data register gets the I/O state


RM0360 Rev 5 131/775



141


**General-purpose I/Os (GPIO)** **RM0360**


_Figure 17_ shows the alternate function configuration of the I/O port bit.


**Figure 17. Alternate function configuration**





















































**8.3.12** **Analog configuration**


When the I/O port is programmed as analog configuration:


      - The output buffer is disabled


      - The Schmitt trigger input is deactivated, providing zero consumption for every analog
value of the I/O pin. The output of the Schmitt trigger is forced to a constant value (0).


      - The weak pull-up and pull-down resistors are disabled by hardware


      - Read access to the input data register gets the value “0”


For code example refer to _Section A.4.3: Analog GPIO configuration on page 729_ .


132/775 RM0360 Rev 5


**RM0360** **General-purpose I/Os (GPIO)**


_Figure 18_ shows the high-impedance, analog-input configuration of the I/O port bits.


**Figure 18. High impedance-analog configuration**













**8.3.13** **Using the HSE or LSE oscillator pins as GPIOs**


When the HSE or LSE oscillator is switched OFF (default state after reset), the related
oscillator pins can be used as normal GPIOs.


When the HSE or LSE oscillator is switched ON (by setting the HSEON or LSEON bit in the
RCC_CSR register) the oscillator takes control of its associated pins and the GPIO
configuration of these pins has no effect.


When the oscillator is configured in a user external clock mode, only the pin is reserved for
clock input and the OSC_OUT or OSC32_OUT pin can still be used as normal GPIO.


**8.3.14** **Using the GPIO pins in the RTC supply domain**


The PC13/PC14/PC15 GPIO functionality is lost when the core supply domain is powered
off (when the device enters Standby mode). In this case, if their GPIO configuration is not
bypassed by the RTC configuration, these pins are set in an analog input mode.


For details about I/O control by the RTC, refer to _Section 21.4: RTC functional description_ .


RM0360 Rev 5 133/775



141


**General-purpose I/Os (GPIO)** **RM0360**

## **8.4 GPIO registers**


For a summary of register bits, register address offsets and reset values, refer to _Table 23_ .


The peripheral registers can be written in word, half word or byte mode.


**8.4.1** **GPIO port mode register (GPIOx_MODER)**
**(x =A to D, F)**


Address offset:0x00


Reset value: 0x2800 0000 for port A


Reset value: 0x0000 0000 for other ports

|31 30|Col2|29 28|Col4|27 26|Col6|25 24|Col8|23 22|Col10|21 20|Col12|19 18|Col14|17 16|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MODER15[1:0]|MODER15[1:0]|MODER14[1:0]|MODER14[1:0]|MODER13[1:0]|MODER13[1:0]|MODER12[1:0]|MODER12[1:0]|MODER11[1:0]|MODER11[1:0]|MODER10[1:0]|MODER10[1:0]|MODER9[1:0]|MODER9[1:0]|MODER8[1:0]|MODER8[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14|Col2|13 12|Col4|11 10|Col6|9 8|Col8|7 6|Col10|5 4|Col12|3 2|Col14|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MODER7[1:0]|MODER7[1:0]|MODER6[1:0]|MODER6[1:0]|MODER5[1:0]|MODER5[1:0]|MODER4[1:0]|MODER4[1:0]|MODER3[1:0]|MODER3[1:0]|MODER2[1:0]|MODER2[1:0]|MODER1[1:0]|MODER1[1:0]|MODER0[1:0]|MODER0[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **MODER[15:0][1:0]:** Port x configuration I/O pin y (y = 15 to 0)

These bits are written by software to configure the I/O mode.

00: Input mode (reset state)
01: General purpose output mode

10: Alternate function mode

11: Analog mode


**8.4.2** **GPIO port output type register (GPIOx_OTYPER)**
**(x = A to D, F)**


Address offset: 0x04


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|OT15|OT14|OT13|OT12|OT11|OT10|OT9|OT8|OT7|OT6|OT5|OT4|OT3|OT2|OT1|OT0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **OT[15:0]:** Port x configuration I/O pin y (y = 15 to 0)

These bits are written by software to configure the I/O output type.

0: Output push-pull (reset state)
1: Output open-drain


134/775 RM0360 Rev 5


**RM0360** **General-purpose I/Os (GPIO)**


**8.4.3** **GPIO port output speed register (GPIOx_OSPEEDR)**
**(x = A to D, F)**


Address offset: 0x08


Reset value: 0x0C00 0000 (for port A)


Reset value: 0x0000 0000 (for other ports)

|31 30|Col2|29 28|Col4|27 26|Col6|25 24|Col8|23 22|Col10|21 20|Col12|19 18|Col14|17 16|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|OSPEEDR15<br>[1:0]|OSPEEDR15<br>[1:0]|OSPEEDR14<br>[1:0]|OSPEEDR14<br>[1:0]|OSPEEDR13<br>[1:0]|OSPEEDR13<br>[1:0]|OSPEEDR12<br>[1:0]|OSPEEDR12<br>[1:0]|OSPEEDR11<br>[1:0]|OSPEEDR11<br>[1:0]|OSPEEDR10<br>[1:0]|OSPEEDR10<br>[1:0]|OSPEEDR9<br>[1:0]|OSPEEDR9<br>[1:0]|OSPEEDR8<br>[1:0]|OSPEEDR8<br>[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14|Col2|13 12|Col4|11 10|Col6|9 8|Col8|7 6|Col10|5 4|Col12|3 2|Col14|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|OSPEEDR7<br>[1:0]|OSPEEDR7<br>[1:0]|OSPEEDR6<br>[1:0]|OSPEEDR6<br>[1:0]|OSPEEDR5<br>[1:0]|OSPEEDR5<br>[1:0]|OSPEEDR4<br>[1:0]|OSPEEDR4<br>[1:0]|OSPEEDR3<br>[1:0]|OSPEEDR3<br>[1:0]|OSPEEDR2<br>[1:0]|OSPEEDR2<br>[1:0]|OSPEEDR1<br>[1:0]|OSPEEDR1<br>[1:0]|OSPEEDR0<br>[1:0]|OSPEEDR0<br>[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **OSPEEDR[15:0][1:0]** : Port x configuration I/O pin y (y = 15 to 0)

These bits are written by software to configure the I/O output speed.

x0: Low speed
01: Medium speed
11: High speed

_Note: Refer to the device datasheet for the frequency specifications and the power supply_
_and load conditions for each speed.._


**8.4.4** **GPIO port pull-up/pull-down register (GPIOx_PUPDR)**
**(x = A to,D, F)**


Address offset: 0x0C


Reset value: 0x2400 0000 (for port A)


Reset value: 0x0000 0000 (for other ports)

|31 30|Col2|29 28|Col4|27 26|Col6|25 24|Col8|23 22|Col10|21 20|Col12|19 18|Col14|17 16|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PUPDR15[1:0]|PUPDR15[1:0]|PUPDR14[1:0]|PUPDR14[1:0]|PUPDR13[1:0]|PUPDR13[1:0]|PUPDR12[1:0]|PUPDR12[1:0]|PUPDR11[1:0]|PUPDR11[1:0]|PUPDR10[1:0]|PUPDR10[1:0]|PUPDR9[1:0]|PUPDR9[1:0]|PUPDR8[1:0]|PUPDR8[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14|Col2|13 12|Col4|11 10|Col6|9 8|Col8|7 6|Col10|5 4|Col12|3 2|Col14|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PUPDR7[1:0]|PUPDR7[1:0]|PUPDR6[1:0]|PUPDR6[1:0]|PUPDR5[1:0]|PUPDR5[1:0]|PUPDR4[1:0]|PUPDR4[1:0]|PUPDR3[1:0]|PUPDR3[1:0]|PUPDR2[1:0]|PUPDR2[1:0]|PUPDR1[1:0]|PUPDR1[1:0]|PUPDR0[1:0]|PUPDR0[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **PUPDR[15:0][1:0]:** Port x configuration I/O pin y (y = 15 to 0)

These bits are written by software to configure the I/O pull-up or pull-down

00: No pull-up, pull-down
01: Pull-up
10: Pull-down

11: Reserved


RM0360 Rev 5 135/775



141


**General-purpose I/Os (GPIO)** **RM0360**


**8.4.5** **GPIO port input data register (GPIOx_IDR)**
**(x = A to D, F)**


Address offset: 0x10


Reset value: 0x0000 XXXX

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|IDR15|IDR14|IDR13|IDR12|IDR11|IDR10|IDR9|IDR8|IDR7|IDR6|IDR5|IDR4|IDR3|IDR2|IDR1|IDR0|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **IDR[15:0]:** Port x input data I/O pin y (y = 15 to 0)

These bits are read-only. They contain the input value of the corresponding I/O port.


**8.4.6** **GPIO port output data register (GPIOx_ODR)**
**(x = A to D, F)**


Address offset: 0x14


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ODR15|ODR14|ODR13|ODR12|ODR11|ODR10|ODR9|ODR8|ODR7|ODR6|ODR5|ODR4|ODR3|ODR2|ODR1|ODR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **ODR[15:0]:** Port output data I/O pin y (y = 15 to 0)

These bits can be read and written by software.

_Note: For atomic bit set/reset, the ODR bits can be individually set and/or reset by writing to_
_the GPIOx_BSRR register (x = A..D, F)._


136/775 RM0360 Rev 5


**RM0360** **General-purpose I/Os (GPIO)**


**8.4.7** **GPIO port bit set/reset register (GPIOx_BSRR)**
**(x = A to D, F)**


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



Bits 31:16 **BR[15:0]:** Port x reset I/O pin y (y = 15 to 0)

These bits are write-only. A read to these bits returns the value 0x0000.

0: No action on the corresponding ODRx bit
1: Resets the corresponding ODRx bit

_Note: If both BSx and BRx are set, BSx has priority._


Bits 15:0 **BS[15:0]:** Port x set I/O pin y (y = 15 to 0)

These bits are write-only. A read to these bits returns the value 0x0000.

0: No action on the corresponding ODRx bit
1: Sets the corresponding ODRx bit


**8.4.8** **GPIO port configuration lock register (GPIOx_LCKR)**
**(x = A to B)**


This register is used to lock the configuration of the port bits when a correct write sequence
is applied to bit 16 (LCKK). The value of bits [15:0] is used to lock the configuration of the
GPIO. During the write sequence, the value of LCKR[15:0] must not change. When the
LOCK sequence has been applied on a port bit, the value of this port bit can no longer be
modified until the next MCU reset or peripheral reset.


_Note:_ _A specific write sequence is used to write to the GPIOx_LCKR register. Only word access_
_(32-bit long) is allowed during this locking sequence._


Each lock bit freezes a specific configuration register (control and alternate function
registers).


Address offset: 0x1C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LCKK|
||||||||||||||||rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|LCK15|LCK14|LCK13|LCK12|LCK11|LCK10|LCK9|LCK8|LCK7|LCK6|LCK5|LCK4|LCK3|LCK2|LCK1|LCK0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



RM0360 Rev 5 137/775



141


**General-purpose I/Os (GPIO)** **RM0360**


Bits 31:17 Reserved, must be kept at reset value.


Bit 16 **LCKK:** Lock key

This bit can be read any time. It can only be modified using the lock key write sequence.

0: Port configuration lock key not active
1: Port configuration lock key active. The GPIOx_LCKR register is locked until the next MCU
reset or peripheral reset.
LOCK key write sequence:
WR LCKR[16] = 1 + LCKR[15:0]
WR LCKR[16] = 0 + LCKR[15:0]
WR LCKR[16] = 1 + LCKR[15:0]

RD LCKR

RD LCKR[16] = 1 (this read operation is optional but it confirms that the lock is active)

_Note: During the LOCK key write sequence, the value of LCK[15:0] must not change._

_Any error in the lock sequence aborts the lock._

_After the first lock sequence on any bit of the port, any read access on the LCKK bit_
_returns 1 until the next MCU reset or peripheral reset._ For code example refer to
_Section A.4.1: Lock sequence on page 728_ .


Bits 15:0 **LCK[15:0]:** Port x lock I/O pin y (y = 15 to 0)

These bits are read/write but can only be written when the LCKK bit is 0.

0: Port configuration not locked
1: Port configuration locked


**8.4.9** **GPIO alternate function low register (GPIOx_AFRL)**
**(x = A to D, )**


Address offset: 0x20


Reset value: 0x0000 0000

|31 30 29 28|Col2|Col3|Col4|27 26 25 24|Col6|Col7|Col8|23 22 21 20|Col10|Col11|Col12|19 18 17 16|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|AFSEL7[3:0]|AFSEL7[3:0]|AFSEL7[3:0]|AFSEL7[3:0]|AFSEL6[3:0]|AFSEL6[3:0]|AFSEL6[3:0]|AFSEL6[3:0]|AFSEL5[3:0]|AFSEL5[3:0]|AFSEL5[3:0]|AFSEL5[3:0]|AFSEL4[3:0]|AFSEL4[3:0]|AFSEL4[3:0]|AFSEL4[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|AFSEL3[3:0]|AFSEL3[3:0]|AFSEL3[3:0]|AFSEL3[3:0]|AFSEL2[3:0]|AFSEL2[3:0]|AFSEL2[3:0]|AFSEL2[3:0]|AFSEL1[3:0]|AFSEL1[3:0]|AFSEL1[3:0]|AFSEL1[3:0]|AFSEL0[3:0]|AFSEL0[3:0]|AFSEL0[3:0]|AFSEL0[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **AFSELy[3:0]:** Alternate function selection for port x pin y (y = 0..7)

These bits are written by software to configure alternate function I/Os



AFSELy selection:

0000: AF0

0001: AF1

0010: AF2

0011: AF3

0100: AF4

0101: AF5

0110: AF6

0111: AF7



1000: Reserved

1001: Reserved

1010: Reserved

1011: Reserved

1100: Reserved

1101: Reserved

1110: Reserved

1111: Reserved



138/775 RM0360 Rev 5


**RM0360** **General-purpose I/Os (GPIO)**


**8.4.10** **GPIO alternate function high register (GPIOx_AFRH)**
**(x = A to D, F)**


Address offset: 0x24


Reset value: 0x0000 0000

|31 30 29 28|Col2|Col3|Col4|27 26 25 24|Col6|Col7|Col8|23 22 21 20|Col10|Col11|Col12|19 18 17 16|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|AFSEL15[3:0]|AFSEL15[3:0]|AFSEL15[3:0]|AFSEL15[3:0]|AFSEL14[3:0]|AFSEL14[3:0]|AFSEL14[3:0]|AFSEL14[3:0]|AFSEL13[3:0]|AFSEL13[3:0]|AFSEL13[3:0]|AFSEL13[3:0]|AFSEL12[3:0]|AFSEL12[3:0]|AFSEL12[3:0]|AFSEL12[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|AFSEL11[3:0]|AFSEL11[3:0]|AFSEL11[3:0]|AFSEL11[3:0]|AFSEL10[3:0]|AFSEL10[3:0]|AFSEL10[3:0]|AFSEL10[3:0]|AFSEL9[3:0]|AFSEL9[3:0]|AFSEL9[3:0]|AFSEL9[3:0]|AFSEL8[3:0]|AFSEL8[3:0]|AFSEL8[3:0]|AFSEL8[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **AFSELy[3:0]:** Alternate function selection for port x pin y (y = 8..15)

These bits are written by software to configure alternate function I/Os



AFSELy selection:

0000: AF0

0001: AF1

0010: AF2

0011: AF3

0100: AF4

0101: AF5

0110: AF6

0111: AF7



1000: Reserved

1001: Reserved

1010: Reserved

1011: Reserved

1100: Reserved

1101: Reserved

1110: Reserved

1111: Reserved



**8.4.11** **GPIO port bit reset register (GPIOx_BRR) (x = A to D, F)**


Address offset: 0x28


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|BR15|BR14|BR13|BR12|BR11|BR10|BR9|BR8|BR7|BR6|BR5|BR4|BR3|BR2|BR1|BR0|
|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **BR[15:0]:** Port x reset IO pin y (y = 15 to 0)

These bits are write-only. A read to these bits returns the value 0x0000.
0: No action on the corresponding ODx bit
1: Reset the corresponding ODx bit


RM0360 Rev 5 139/775



141


**General-purpose I/Os (GPIO)** **RM0360**


**8.4.12** **GPIO register map**


The following table gives the GPIO register map and reset values.


**Table 23. GPIO register map and reset values**













|Offset|Register name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**GPIOA_MODER**|MODER15[1:0]|MODER15[1:0]|MODER14[1:0]|MODER14[1:0]|MODER13[1:0]|MODER13[1:0]|MODER12[1:0]|MODER12[1:0]|MODER11[1:0]|MODER11[1:0]|MODER10[1:0]|MODER10[1:0]|MODER9[1:0]|MODER9[1:0]|MODER8[1:0]|MODER8[1:0]|MODER7[1:0]|MODER7[1:0]|MODER6[1:0]|MODER6[1:0]|MODER5[1:0]|MODER5[1:0]|MODER4[1:0]|MODER4[1:0]|MODER3[1:0]|MODER3[1:0]|MODER2[1:0]|MODER2[1:0]|MODER1[1:0]|MODER1[1:0]|MODER0[1:0]|MODER0[1:0]|
|0x00|Reset value|0|0|1|0|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00|**GPIOx_MODER** <br>(where x = **B..D,F**)|MODER15[1:0]|MODER15[1:0]|MODER14[1:0]|MODER14[1:0]|MODER13[1:0]|MODER13[1:0]|MODER12[1:0]|MODER12[1:0]|MODER11[1:0]|MODER11[1:0]|MODER10[1:0]|MODER10[1:0]|MODER9[1:0]|MODER9[1:0]|MODER8[1:0]|MODER8[1:0]|MODER7[1:0]|MODER7[1:0]|MODER6[1:0]|MODER6[1:0]|MODER5[1:0]|MODER5[1:0]|MODER4[1:0]|MODER4[1:0]|MODER3[1:0]|MODER3[1:0]|MODER2[1:0]|MODER2[1:0]|MODER1[1:0]|MODER1[1:0]|MODER0[1:0]|MODER0[1:0]|
|0x00|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x04|**GPIOx_OTYPER**<br>(where x =**A..D, F**)|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|OT15|OT14|OT13|OT12|OT11|OT10|OT9|OT8|OT7|OT6|OT5|OT4|OT3|OT2|OT1|OT0|
|0x04|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x08|**GPIOA_OSPEEDR**|OSPEEDR15[1:0]|OSPEEDR15[1:0]|OSPEEDR14[1:0]|OSPEEDR14[1:0]|OSPEEDR13[1:0]|OSPEEDR13[1:0]|OSPEEDR12[1:0]|OSPEEDR12[1:0]|OSPEEDR11[1:0]|OSPEEDR11[1:0]|OSPEEDR10[1:0]|OSPEEDR10[1:0]|OSPEEDR9[1:0]|OSPEEDR9[1:0]|OSPEEDR8[1:0]|OSPEEDR8[1:0]|OSPEEDR7[1:0]|OSPEEDR7[1:0]|OSPEEDR6[1:0]|OSPEEDR6[1:0]|OSPEEDR5[1:0]|OSPEEDR5[1:0]|OSPEEDR4[1:0]|OSPEEDR4[1:0]|OSPEEDR3[1:0]|OSPEEDR3[1:0]|OSPEEDR2[1:0]|OSPEEDR2[1:0]|OSPEEDR1[1:0]|OSPEEDR1[1:0]|OSPEEDR0[1:0]|OSPEEDR0[1:0]|
|0x08|Reset value|0|0|0|0|1|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x08|**GPIOx_OSPEEDR** <br>(where x =** B..D, F**)|OSPEEDR15[1:0]|OSPEEDR15[1:0]|OSPEEDR14[1:0]|OSPEEDR14[1:0]|OSPEEDR13[1:0]|OSPEEDR13[1:0]|OSPEEDR12[1:0]|OSPEEDR12[1:0]|OSPEEDR11[1:0]|OSPEEDR11[1:0]|OSPEEDR10[1:0]|OSPEEDR10[1:0]|OSPEEDR9[1:0]|OSPEEDR9[1:0]|OSPEEDR8[1:0]|OSPEEDR8[1:0]|OSPEEDR7[1:0]|OSPEEDR7[1:0]|OSPEEDR6[1:0]|OSPEEDR6[1:0]|OSPEEDR5[1:0]|OSPEEDR5[1:0]|OSPEEDR4[1:0]|OSPEEDR4[1:0]|OSPEEDR3[1:0]|OSPEEDR3[1:0]|OSPEEDR2[1:0]|OSPEEDR2[1:0]|OSPEEDR1[1:0]|OSPEEDR1[1:0]|OSPEEDR0[1:0]|OSPEEDR0[1:0]|
|0x08|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0C|**GPIOA_PUPDR**|PUPDR15[1:0]|PUPDR15[1:0]|PUPDR14[1:0]|PUPDR14[1:0]|PUPDR13[1:0]|PUPDR13[1:0]|PUPDR12[1:0]|PUPDR12[1:0]|PUPDR11[1:0]|PUPDR11[1:0]|PUPDR10[1:0]|PUPDR10[1:0]|PUPDR9[1:0]|PUPDR9[1:0]|PUPDR8[1:0]|PUPDR8[1:0]|PUPDR7[1:0]|PUPDR7[1:0]|PUPDR6[1:0]|PUPDR6[1:0]|PUPDR5[1:0]|PUPDR5[1:0]|PUPDR4[1:0]|PUPDR4[1:0]|PUPDR3[1:0]|PUPDR3[1:0]|PUPDR2[1:0]|PUPDR2[1:0]|PUPDR1[1:0]|PUPDR1[1:0]|PUPDR0[1:0]|PUPDR0[1:0]|
|0x0C|Reset value|0|0|1|0|0|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0C|**GPIOx_PUPDR** <br>(where x =**B..D, F**)|PUPDR15[1:0]|PUPDR15[1:0]|PUPDR14[1:0]|PUPDR14[1:0]|PUPDR13[1:0]|PUPDR13[1:0]|PUPDR12[1:0]|PUPDR12[1:0]|PUPDR11[1:0]|PUPDR11[1:0]|PUPDR10[1:0]|PUPDR10[1:0]|PUPDR9[1:0]|PUPDR9[1:0]|PUPDR8[1:0]|PUPDR8[1:0]|PUPDR7[1:0]|PUPDR7[1:0]|PUPDR6[1:0]|PUPDR6[1:0]|PUPDR5[1:0]|PUPDR5[1:0]|PUPDR4[1:0]|PUPDR4[1:0]|PUPDR3[1:0]|PUPDR3[1:0]|PUPDR2[1:0]|PUPDR2[1:0]|PUPDR1[1:0]|PUPDR1[1:0]|PUPDR0[1:0]|PUPDR0[1:0]|
|0x0C|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**GPIOx_IDR**<br>(where x =**A..D, F**)|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|IDR15|IDR14|IDR13|IDR12|IDR11|IDR10|IDR9|IDR8|IDR7|IDR6|IDR5|IDR4|IDR3|IDR2|IDR1|IDR0|
|0x10|Reset value|||||||||||||||||x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x14|**GPIOx_ODR**<br>(where x =**A..D, F**)|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ODR15|ODR14|ODR13|ODR12|ODR11|ODR10|ODR9|ODR8|ODR7|ODR6|ODR5|ODR4|ODR3|ODR2|ODR1|ODR0|
|0x14|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x18|**GPIOx_BSRR**<br>(where x =**A..D, F**)|BR15|BR14|BR13|BR12|BR11|BR10|BR9|BR8|BR7|BR6|BR5|BR4|BR3|BR2|BR1|BR0|BS15|BS14|BS13|BS12|BS11|BS10|BS9|BS8|BS7|BS6|BS5|BS4|BS3|BS2|BS1|BS0|
|0x18|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


140/775 RM0360 Rev 5


**RM0360** **General-purpose I/Os (GPIO)**


**Table 23. GPIO register map and reset values (continued)**











|Offset|Register name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x1C|**GPIOx_LCKR**<br>(where x =**A..B**)|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LCKK|LCK15|LCK14|LCK13|LCK12|LCK11|LCK10|LCK9|LCK8|LCK7|LCK6|LCK5|LCK4|LCK3|LCK2|LCK1|LCK0|
|0x1C|Reset value||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x20|**GPIOx_AFRL** <br>(where x =**A.., B**)|AFSEL7<br>[3:0]|AFSEL7<br>[3:0]|AFSEL7<br>[3:0]|AFSEL7<br>[3:0]|AFSEL6<br>[3:0]|AFSEL6<br>[3:0]|AFSEL6<br>[3:0]|AFSEL6<br>[3:0]|AFSEL5<br>[3:0]|AFSEL5<br>[3:0]|AFSEL5<br>[3:0]|AFSEL5<br>[3:0]|AFSEL4<br>[3:0]|AFSEL4<br>[3:0]|AFSEL4<br>[3:0]|AFSEL4<br>[3:0]|AFSEL3<br>[3:0]|AFSEL3<br>[3:0]|AFSEL3<br>[3:0]|AFSEL3<br>[3:0]|AFSEL2<br>[3:0]|AFSEL2<br>[3:0]|AFSEL2<br>[3:0]|AFSEL2<br>[3:0]|AFSEL1<br>[3:0]|AFSEL1<br>[3:0]|AFSEL1<br>[3:0]|AFSEL1<br>[3:0]|AFSEL0<br>[3:0]|AFSEL0<br>[3:0]|AFSEL0<br>[3:0]|AFSEL0<br>[3:0]|
|0x20|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x24|**GPIOx_AFRH** <br>(where x =**A..B**)|AFSEL15<br>[3:0]|AFSEL15<br>[3:0]|AFSEL15<br>[3:0]|AFSEL15<br>[3:0]|AFSEL14<br>[3:0]|AFSEL14<br>[3:0]|AFSEL14<br>[3:0]|AFSEL14<br>[3:0]|AFSEL13<br>[3:0]|AFSEL13<br>[3:0]|AFSEL13<br>[3:0]|AFSEL13<br>[3:0]|AFSEL12<br>[3:0]|AFSEL12<br>[3:0]|AFSEL12<br>[3:0]|AFSEL12<br>[3:0]|AFSEL11<br>[3:0]|AFSEL11<br>[3:0]|AFSEL11<br>[3:0]|AFSEL11<br>[3:0]|AFSEL10<br>[3:0]|AFSEL10<br>[3:0]|AFSEL10<br>[3:0]|AFSEL10<br>[3:0]|AFSEL9<br>[3:0]|AFSEL9<br>[3:0]|AFSEL9<br>[3:0]|AFSEL9<br>[3:0]|AFSEL8<br>[3:0]|AFSEL8<br>[3:0]|AFSEL8<br>[3:0]|AFSEL8<br>[3:0]|
|0x24|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x28|**GPIOx_BRR** <br>(where x =**A..D, F**)|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|BR15|BR14|BR13|BR12|BR11|BR10|BR9|BR8|BR7|BR6|BR5|BR4|BR3|BR2|BR1|BR0|
|0x28|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


Refer to _Section 2.2 on page 37_ for the register boundary addresses.


RM0360 Rev 5 141/775



141


