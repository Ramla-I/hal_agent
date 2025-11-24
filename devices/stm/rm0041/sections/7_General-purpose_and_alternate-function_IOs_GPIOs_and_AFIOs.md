**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**

# **7 General-purpose and alternate-function I/Os** **(GPIOs and AFIOs)**


**Low-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 16 and 32 Kbytes.


**Medium-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 64 and 128 Kbytes.


**High-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 256 and 512 Kbytes.


This section applies to the whole STM32F100xx family, unless otherwise specified.

## **7.1 GPIO functional description**


Each of the general-purpose I/O ports has two 32-bit configuration registers (GPIOx_CRL,
GPIOx_CRH), two 32-bit data registers (GPIOx_IDR, GPIOx_ODR), a 32-bit set/reset
register (GPIOx_BSRR), a 16-bit reset register (GPIOx_BRR) and a 32-bit locking register
(GPIOx_LCKR).


Subject to the specific hardware characteristics of each I/O port listed in the _datasheet_, each
port bit of the General Purpose IO (GPIO) Ports, can be individually configured by software
in several modes:


      - Input floating


      - Input pull-up


      - Input-pull-down


      - Analog


      - Output open-drain


      - Output push-pull


      - Alternate function push-pull


      - Alternate function open-drain


Each I/O port bit is freely programmable, however the I/O port registers have to be
accessed as 32-bit words (half-word or byte accesses are not allowed). The purpose of the
GPIOx_BSRR and GPIOx_BRR registers is to allow atomic read/modify accesses to any of
the GPIO registers. This way, there is no risk that an IRQ occurs between the read and the
modify access.


_Figure 11_ shows the basic structure of an I/O Port bit.


102/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


**Figure 11. Basic structure of a standard I/O port bit**























**Figure 12. Basic structure of a 5-Volt tolerant I/O port bit**





















1. V DD_FT is a potential specific to 5-Volt tolerant I/Os, and different from V DD .


RM0041 Rev 6 103/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


**Table 16. Port bit configuration table**







|Configuration mode|Col2|CNF1|CNF0|MODE1|MODE0|PxODR<br>register|
|---|---|---|---|---|---|---|
|General purpose<br>output|Push-pull|0|0|01<br>10<br>11<br>see_Table 17_|01<br>10<br>11<br>see_Table 17_|0 or 1|
|General purpose<br>output|Open-drain|Open-drain|1|1|1|0 or 1|
|Alternate Function<br>output|Push-pull|1|0|0|0|Don’t care|
|Alternate Function<br>output|Open-drain|Open-drain|1|1|1|Don’t care|
|Input|Analog|0|0|00|00|Don’t care|
|Input|Input floating|Input floating|1|1|1|Don’t care|
|Input|Input pull-down|1|0|0|0|0|
|Input|Input pull-up|Input pull-up|Input pull-up|Input pull-up|Input pull-up|1|


**Table 17. Output MODE bits**













|MODE[1:0]|Meaning|
|---|---|
|00|Reserved|
|01|Maximum output speed 10 MHz|
|10|Maximum output speed 2 MHz|
|11|Maximum output speed 50 MHz|


**7.1.1** **General-purpose I/O (GPIO)**


During and just after reset, the alternate functions are not active and the I/O ports are
configured in Input Floating mode (CNFx[1:0]=01b, MODEx[1:0]=00b).


The JTAG pins are in input PU/PD after reset:


PA15: JTDI in PU


PA14: JTCK in PD


PA13: JTMS in PU


PB4: NJTRST in PU


When configured as output, the value written to the Output Data register (GPIOx_ODR) is
output on the I/O pin. It is possible to use the output driver in Push-Pull mode or Open-Drain
mode (only the N-MOS is activated when outputting 0).


The Input Data register (GPIOx_IDR) captures the data present on the I/O pin at every
APB2 clock cycle.


All GPIO pins have an internal weak pull-up and weak pull-down that can be activated or not
when configured as input.


**7.1.2** **Atomic bit set or reset**


There is no need for the software to disable interrupts when programming the GPIOx_ODR
at bit level: it is possible to modify only one or several bits in a single atomic APB2 write
access. This is achieved by programming to ‘1’ the Bit Set/Reset register (GPIOx_BSRR, or


104/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


for reset only GPIOx_BRR) to select the bits to modify. The unselected bits will not be
modified.


**7.1.3** **External interrupt/wakeup lines**


All ports have external interrupt capability. To use external interrupt lines, the port must be
configured in input mode. For more information on external interrupts, refer to _Section 8.2:_
_External interrupt/event controller (EXTI)_ and _Section 8.2.3: Wakeup event management_ .


**7.1.4** **Alternate functions (AF)**


It is necessary to program the Port Bit Configuration register before using a default alternate
function.


      - For alternate function inputs, the port must be configured in Input mode (floating, pullup or pull-down) and the input pin must be driven externally.


_Note:_ _It is also possible to emulate the AFI input pin by software by programming the GPIO_
_controller. In this case, the port should be configured in Alternate Function Output mode._
_And obviously, the corresponding port should not be driven externally as it will be driven by_
_the software using the GPIO controller._


      - For alternate function outputs, the port must be configured in Alternate Function Output
mode (Push-Pull or Open-Drain).


      - For bidirectional Alternate Functions, the port bit must be configured in Alternate
Function Output mode (Push-Pull or Open-Drain). In this case the input driver is
configured in input floating mode


If a port bit is configured as Alternate Function Output, this disconnects the output register
and connects the pin to the output signal of an on-chip peripheral.


If software configures a GPIO pin as Alternate Function Output, but peripheral is not
activated, its output is not specified.


**7.1.5** **Software remapping of I/O alternate functions**


To optimize the number of peripheral I/O functions for different device packages, it is
possible to remap some alternate functions to some other pins. This is achieved by
software, by programming the corresponding registers (refer to _AFIO registers_ . In that case,
the alternate functions are no longer mapped to their original assignations.


**7.1.6** **GPIO locking mechanism**


The locking mechanism allows the IO configuration to be frozen. When the LOCK sequence
has been applied on a port bit, it is no longer possible to modify the value of the port bit until
the next reset.


RM0041 Rev 6 105/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


**7.1.7** **Input configuration**


When the I/O Port is programmed as Input:


      - The Output Buffer is disabled


      - The Schmitt Trigger Input is activated


      - The weak pull-up and pull-down resistors are activated or not depending on input
configuration (pull-up, pull-down or floating):


      - The data present on the I/O pin is sampled into the Input Data register every APB2
clock cycle


      - A read access to the Input Data register obtains the I/O State.


_Figure 13_ shows the Input Configuration of the I/O Port bit.


**Figure 13. Input floating/pull up/pull down configurations**













1. V DD_FT is a potential specific to 5-Volt tolerant I/Os, and different from V DD .


**7.1.8** **Output configuration**


When the I/O Port is programmed as Output:


      - The Output Buffer is enabled:





–
Open Drain mode: A “0” in the Output register activates the N-MOS while a “1” in
the Output register leaves the port in Hi-Z (the P-MOS is never activated)


–
Push-Pull mode: A “0” in the Output register activates the N-MOS while a “1” in the
Output register activates the P-MOS


      - The Schmitt Trigger Input is activated.


      - The weak pull-up and pull-down resistors are disabled.


      - The data present on the I/O pin is sampled into the Input Data register every APB2
clock cycle


      - A read access to the Input Data register gets the I/O state in open drain mode


      - A read access to the Output Data register gets the last written value in Push-Pull mode


_Figure 14_ shows the Output configuration of the I/O Port bit.


106/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


**Figure 14. Output configuration**

















1. V DD_FT is a potential specific to 5-Volt tolerant I/Os, and different from V DD .


**7.1.9** **Alternate function configuration**


When the I/O Port is programmed as Alternate Function:


      - The Output Buffer is turned on in Open Drain or Push-Pull configuration


      - The Output Buffer is driven by the signal coming from the peripheral (alternate function
out)


      - The Schmitt Trigger Input is activated


      - The weak pull-up and pull-down resistors are disabled.


      - The data present on the I/O pin is sampled into the Input Data register every APB2
clock cycle


      - A read access to the Input Data register gets the I/O state in open drain mode


      - A read access to the Output Data register gets the last written value in Push-Pull mode


_Figure 15_ shows the Alternate Function Configuration of the I/O Port bit. Also, refer to
_Section 7.4: AFIO registers_ for further information.


A set of Alternate Function I/O registers allows the user to remap some alternate functions
to different pins. Refer to _Section 7.3: Alternate function I/O and debug configuration (AFIO)_ .


RM0041 Rev 6 107/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


**Figure 15. Alternate function configuration**



















1. V DD_FT is a potential specific to 5-Volt tolerant I/Os, and different from V DD .


**7.1.10** **Analog configuration**


When the I/O Port is programmed as Analog configuration:


      - The Output Buffer is disabled.


      - The Schmitt Trigger Input is de-activated providing zero consumption for every analog
value of the I/O pin. The output of the Schmitt Trigger is forced to a constant value (0).


      - The weak pull-up and pull-down resistors are disabled.


      - Read access to the Input Data register gets the value “0”.


_Figure 16_ shows the high impedance-analog configuration of the I/O Port bit.


108/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


**Figure 16. High impedance-analog configuration**









**7.1.11** **GPIO configurations for device peripherals**


_Table 18_ to _Table 27_ give the GPIO configurations of the device peripherals.


**Table 18. Advanced timer TIM1**





|TIM1 pinout|Configuration|GPIO configuration|
|---|---|---|
|TIM1_CHx|Input capture channel x|Input floating|
|TIM1_CHx|Output compare channel x|Alternate function push-pull|
|TIM1_CHxN|Complementary output channel x|Alternate function push-pull|
|TIM1_BKIN|Break input|Input floating|
|TIM1_ETR|External trigger timer input|Input floating|


**Table 19. General-purpose timers TIM2/3/4/5**

|TIM2/3/4/5 pinout|Configuration|GPIO configuration|
|---|---|---|
|TIM2/3/4/5_CHx|Input capture channel x|Input floating|
|TIM2/3/4/5_CHx|Output compare channel x|Alternate function push-pull|
|TIM2/3/4/5_ETR|External trigger timer input|Input floating|



**Table 20. General-purpose timers TIM15/16/17**

|TIM15/16/17 pinout|Configuration|GPIO configuration|
|---|---|---|
|TIM15/16/17_CHx|Input capture channel x|Input floating|
|TIM15/16/17_CHx|Output compare channel x|Alternate function push-pull|
|TIM15/16/17_CHxN|Complementary output channel x|Alternate function push-pull|



RM0041 Rev 6 109/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


**Table 20. General-purpose timers TIM15/16/17**

|TIM15/16/17 pinout|Configuration|GPIO configuration|
|---|---|---|
|TIM15/16/17_BKIN|Break input|Input floating|
|TIM15/16/17_ETR|External trigger timer input|Input floating|



**Table 21. General-purpose timers TIM12/13/14**

|TIM12/13/14 pinout|Configuration|GPIO configuration|
|---|---|---|
|TIM12/13/14_CHx|Input capture channel x|Input floating|
|TIM12/13/14_CHx|Output compare channel x|Alternate function push-pull|



**Table 22. USARTs**







|USART pinout|Configuration|GPIO configuration|
|---|---|---|
|USARTx_TX(1)|Full duplex|Alternate function push-pull|
|USARTx_TX(1)|Half duplex synchronous mode|Alternate function push-pull|
|USARTx_RX|Full duplex|Input floating / Input pull-up|
|USARTx_RX|Half duplex synchronous mode|Not used. Can be used as a general IO|
|USARTx_CK|Synchronous mode|Alternate function push-pull|
|USARTx_RTS|Hardware flow control|Alternate function push-pull|
|USARTx_CTS|Hardware flow control|Input floating/ Input pull-up|


1. The USART_TX pin can also be configured as alternate function open drain.


**Table 23. SPI**






|SPI pinout|Configuration|GPIO configuration|
|---|---|---|
|SPIx_SCK|Master|Alternate function push-pull|
|SPIx_SCK|Slave|Input floating|
|SPIx_MOSI|Full duplex / master|Alternate function push-pull|
|SPIx_MOSI|Full duplex /  slave|Input floating / Input pull-up|
|SPIx_MOSI|Simplex bidirectional data wire / master|Alternate function push-pull|
|SPIx_MOSI|Simplex bidirectional data wire/ slave|Not used. Can be used as a GPIO|
|SPIx_MISO|Full duplex / master|Input floating / Input pull-up|
|SPIx_MISO|Full duplex /  slave (point to point)|Alternate function push-pull|
|SPIx_MISO|Full duplex /  slave (multi-slave)|Alternate function open drain|
|SPIx_MISO|Simplex bidirectional data wire / master|Not used. Can be used as a GPIO|
|SPIx_MISO|Simplex bidirectional data wire/ slave<br>(point to point)|Alternate function push-pull|
|SPIx_MISO|Simplex bidirectional data wire/ slave<br>(multi-slave)|Alternate function open drain|



110/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


**Table 23. SPI (continued)**





|SPI pinout|Configuration|GPIO configuration|
|---|---|---|
|SPIx_NSS|Hardware master /slave|Input floating/ Input pull-up / Input pull-down|
|SPIx_NSS|Hardware master/ NSS output enabled|Alternate function push-pull|
|SPIx_NSS|Software|Not used. Can be used as a GPIO|


**Table 24. CEC**



|CEC pinout|Configuration|GPIO configuration|
|---|---|---|
|CEC|CEC line|Alternate function open drain|


**Table 25. I2C**

|I2C pinout|Configuration|GPIO configuration|
|---|---|---|
|I2Cx_SCL|I2C clock|Alternate function open drain|
|I2Cx_SDA|I2C Data I/O|Alternate function open drain|



The GPIO configuration of the ADC inputs should be analog.


**Figure 17. ADC / DAC**

|ADC/DAC pin|GPIO configuration|
|---|---|
|ADC/DAC|Analog|



**Table 26. FSMC**

|FSMC pinout|GPIO configuration|
|---|---|
|FSMC_A[25:0]<br>FSMC_D[15:0]|Alternate function push-pull|
|FSMC_CK|Alternate function push-pull|
|FSMC_NOE<br>FSMC_NWE|Alternate function push-pull|
|FSMC_NE[4:1]|Alternate function push-pull|
|FSMC_NWAIT|Input floating/ Input pull-up|
|FSMC_NL<br>FSMC_NBL[1:0]|Alternate function push-pull|



RM0041 Rev 6 111/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


**Table 27. Other IOs**

|Pins|Alternate function|GPIO configuration|
|---|---|---|
|TAMPER-RTC pin|RTC output|Forced by hardware when configuring the<br>BKP_CR and BKP_RTCCR registers|
|TAMPER-RTC pin|Tamper event input|Tamper event input|
|MCO|Clock output|Alternate function push-pull|
|EXTI input lines|External input interrupts|Input floating / input pull-up / input pull-down|



112/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**

## **7.2 GPIO registers**


Refer to _Section 1.1 on page 32_ for a list of abbreviations used in register descriptions.


The peripheral registers have to be accessed by words (32-bit).


**7.2.1** **Port configuration register low (GPIOx_CRL) (x=A..G)**


Address offset: 0x00


Reset value: 0x4444 4444


|31 30|Col2|29 28|Col4|27 26|Col6|25 24|Col8|23 22|Col10|21 20|Col12|19 18|Col14|17 16|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CNF7[1:0]|CNF7[1:0]|MODE7[1:0]|MODE7[1:0]|CNF6[1:0]|CNF6[1:0]|MODE6[1:0]|MODE6[1:0]|CNF5[1:0]|CNF5[1:0]|MODE5[1:0]|MODE5[1:0]|CNF4[1:0]|CNF4[1:0]|MODE4[1:0]|MODE4[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14|Col2|13 12|Col4|11 10|Col6|9 8|Col8|7 6|Col10|5 4|Col12|3 2|Col14|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CNF3[1:0]|CNF3[1:0]|MODE3[1:0]|MODE3[1:0]|CNF2[1:0]|CNF2[1:0]|MODE2[1:0]|MODE2[1:0]|CNF1[1:0]|CNF1[1:0]|MODE1[1:0]|MODE1[1:0]|CNF0[1:0]|CNF0[1:0]|MODE0[1:0]|MODE0[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:30, 27:26,
23:22, 19:18, 15:14,
11:10, 7:6, 3:2


Bits 29:28, 25:24,
21:20, 17:16, 13:12,
9:8, 5:4, 1:0



**CNFy[1:0]:** Port x configuration bits (y= 0 .. 7)

These bits are written by software to configure the corresponding I/O port.
Refer to _Table 16: Port bit configuration table_ .
**In input mode (MODE[1:0]=00)** :
00: Analog mode
01: Floating input (reset state)
10: Input with pull-up / pull-down

11: Reserved

**In output mode (MODE[1:0]**  - **00)** :
00: General purpose output push-pull
01: General purpose output Open-drain
10: Alternate function output Push-pull
11: Alternate function output Open-drain


**MODEy[1:0]:** Port x mode bits (y= 0 .. 7)

These bits are written by software to configure the corresponding I/O port.
Refer to _Table 16: Port bit configuration table_ .
00: Input mode (reset state)
01: Output mode, max speed 10 MHz.
10: Output mode, max speed 2 MHz.
11: Output mode, max speed 50 MHz.


RM0041 Rev 6 113/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


**7.2.2** **Port configuration register high (GPIOx_CRH) (x=A..G)**


Address offset: 0x04


Reset value: 0x4444 4444


|31 30|Col2|29 28|Col4|27 26|Col6|25 24|Col8|23 22|Col10|21 20|Col12|19 18|Col14|17 16|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CNF15[1:0]|CNF15[1:0]|MODE15[1:0]|MODE15[1:0]|CNF14[1:0]|CNF14[1:0]|MODE14[1:0]|MODE14[1:0]|CNF13[1:0]|CNF13[1:0]|MODE13[1:0]|MODE13[1:0]|CNF12[1:0]|CNF12[1:0]|MODE12[1:0]|MODE12[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14|Col2|13 12|Col4|11 10|Col6|9 8|Col8|7 6|Col10|5 4|Col12|3 2|Col14|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CNF11[1:0]|CNF11[1:0]|MODE11[1:0]|MODE11[1:0]|CNF10[1:0]|CNF10[1:0]|MODE10[1:0]|MODE10[1:0]|CNF9[1:0]|CNF9[1:0]|MODE9[1:0]|MODE9[1:0]|CNF8[1:0]|CNF8[1:0]|MODE8[1:0]|MODE8[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:30, 27:26,
23:22, 19:18, 15:14,
11:10, 7:6, 3:2


Bits 29:28, 25:24,
21:20, 17:16, 13:12,
9:8, 5:4, 1:0



**CNFy[1:0]:** Port x configuration bits (y= 8 .. 15)

These bits are written by software to configure the corresponding I/O port.
Refer to _Table 16: Port bit configuration table_ .
**In input mode (MODE[1:0]=00)** :
00: Analog mode
01: Floating input (reset state)
10: Input with pull-up / pull-down

11: Reserved

**In output mode (MODE[1:0]**  - **00)** :
00: General purpose output push-pull
01: General purpose output Open-drain
10: Alternate function output Push-pull
11: Alternate function output Open-drain


**MODEy[1:0]:** Port x mode bits (y= 8 .. 15)

These bits are written by software to configure the corresponding I/O port.
Refer to _Table 16: Port bit configuration table_ .
00: Input mode (reset state)
01: Output mode, max speed 10 MHz.
10: Output mode, max speed 2 MHz.
11: Output mode, max speed 50 MHz.



**7.2.3** **Port input data register (GPIOx_IDR) (x=A..G)**


Address offset: 0x08h


Reset value: 0x0000 XXXX


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|IDR15|IDR14|IDR13|IDR12|IDR11|IDR10|IDR9|IDR8|IDR7|IDR6|IDR5|IDR4|IDR3|IDR2|IDR1|IDR0|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **IDRy:** Port input data (y= 0 .. 15)

These bits are read only and can be accessed in Word mode only. They contain the input
value of the corresponding I/O port.


114/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


**7.2.4** **Port output data register (GPIOx_ODR) (x=A..G)**


Address offset: 0x0C


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ODR15|ODR14|ODR13|ODR12|ODR11|ODR10|ODR9|ODR8|ODR7|ODR6|ODR5|ODR4|ODR3|ODR2|ODR1|ODR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **ODRy:** Port output data (y= 0 .. 15)

These bits can be read and written by software and can be accessed in Word mode only.

_Note: For atomic bit set/reset, the ODR bits can be individually set and cleared by writing to_
_the GPIOx_BSRR register (x = A .. E)._


**7.2.5** **Port bit set/reset register (GPIOx_BSRR) (x=A..G)**


Address offset: 0x10


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|BR15|BR14|BR13|BR12|BR11|BR10|BR9|BR8|BR7|BR6|BR5|BR4|BR3|BR2|BR1|BR0|
|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|BS15|BS14|BS13|BS12|BS11|BS10|BS9|BS8|BS7|BS6|BS5|BS4|BS3|BS2|BS1|BS0|
|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|



Bits 31:16 **BRy:** Port x Reset _bit y (y= 0 .. 15)_

These bits are write-only and can be accessed in Word mode only.
0: No action on the corresponding ODRx bit
1: Reset the corresponding ODRx bit

_Note: If both BSx and BRx are set, BSx has priority._


Bits 15:0 **BSy:** Port x _Set bit y (y= 0 .. 15)_

These bits are write-only and can be accessed in Word mode only.
0: No action on the corresponding ODRx bit
1: Set the corresponding ODRx bit


RM0041 Rev 6 115/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


**7.2.6** **Port bit reset register (GPIOx_BRR) (x=A..G)**


Address offset: 0x14


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|BR15|BR14|BR13|BR12|BR11|BR10|BR9|BR8|BR7|BR6|BR5|BR4|BR3|BR2|BR1|BR0|
|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|



Bits 31:16 Reserved


Bits 15:0 **BRy:** Port x Reset bit y (y= 0 .. 15)

These bits are write-only and can be accessed in Word mode only.
0: No action on the corresponding ODRx bit
1: Reset the corresponding ODRx bit


**7.2.7** **Port configuration lock register (GPIOx_LCKR) (x=A..G)**


This register is used to lock the configuration of the port bits when a correct write sequence
is applied to bit 16 (LCKK). The value of bits [15:0] is used to lock the configuration of the
GPIO. During the write sequence, the value of LCKR[15:0] must not change. When the
LOCK sequence has been applied on a port bit it is no longer possible to modify the value of
the port bit until the next reset.


Each lock bit freezes the corresponding 4 bits of the control register (CRL, CRH).


Address offset: 0x18


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17|16|
|---|---|
|Reserved|LCKK|
|Reserved|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|LCK15|LCK14|LCK13|LCK12|LCK11|LCK10|LCK9|LCK8|LCK7|LCK6|LCK5|LCK4|LCK3|LCK2|LCK1|LCK0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



116/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


Bits 31:17 Reserved


Bit 16 **LCKK[16]:** Lock key

This bit can be read anytime. It can only be modified using the Lock Key Writing Sequence.
0: Port configuration lock key not active
1: Port configuration lock key active. GPIOx_LCKR register is locked until the next reset.


LOCK key writing sequence:

Write 1

Write 0

Write 1

Read 0

Read 1 (this read is optional but confirms that the lock is active)

_Note: During the LOCK Key Writing sequence, the value of LCK[15:0] must not change._

Any error in the lock sequence will abort the lock.


Bits 15:0 **LCKy:** Port x Lock bit y (y= 0 .. 15)

These bits are read write but can only be written when the LCKK bit is 0.
0: Port configuration not locked
1: Port configuration locked.

## **7.3 Alternate function I/O and debug configuration (AFIO)**


To optimize the number of peripherals available for the 64-pin or the 100-pin or the 144-pin
package, it is possible to remap some alternate functions to some other pins. This is
achieved by software, by programming the _AF remap and debug I/O configuration register_
_(AFIO_MAPR)_ . In this case, the alternate functions are no longer mapped to their original
assignations.


**7.3.1** **Using OSC32_IN/OSC32_OUT pins as GPIO ports PC14/PC15**


The LSE oscillator pins OSC32_IN and OSC32_OUT can be used as general-purpose I/O
PC14 and PC15, respectively, when the LSE oscillator is off. The LSE has priority over the
GP IOs function.


_Note:_ _The PC14/PC15 GPIO functionality is lost when the 1.8 V domain is powered off (by_
_entering standby mode) or when the backup domain is supplied by V_ _BAT_ _(V_ _DD_ _no more_
_supplied). In this case the IOs are set in analog mode._


_Refer to the note on IO usage restrictions in Section 4.1.2: Battery backup domain._


**7.3.2** **Using OSC_IN/OSC_OUT pins as GPIO ports PD0/PD1**


The HSE oscillator pins OSC_IN/OSC_OUT can be used as general-purpose I/O PD0/PD1
by programming the PD01_REMAP bit in the _AF remap and debug I/O configuration register_
_(AFIO_MAPR)_ .


This remap is available only on 48- and 64-pin packages (PD0 and PD1 are available on
100-pin and 144-pin packages, no need for remapping).


_Note:_ _The external interrupt/event function is not remapped. PD0 and PD1 cannot be used for_
_external interrupt/event generation on 48- and 64-pin packages._


RM0041 Rev 6 117/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


**7.3.3** **JTAG/SWD alternate function remapping**


The debug interface signals are mapped on the GPIO ports as shown in _Table 28_ .


**Table 28. Debug interface signals**

|Alternate function|GPIO port|
|---|---|
|JTMS / SWDIO|PA13|
|JTCK / SWCLK|PA14|
|JTDI|PA15|
|JTDO / TRACESWO|PB3|
|NJTRST|PB4|
|TRACECK|PE2|
|TRACED0|PE3|
|TRACED1|PE4|
|TRACED2|PE5|
|TRACED3|PE6|



To optimize the number of free GPIOs during debugging, this mapping can be configured in
different ways by programming the SWJ_CFG[1:0] bits in the _AF remap and debug I/O_
_configuration register (AFIO_MAPR)_ . Refer to _Table 29_ .


**Table 29. Debug** **port mapping**















|SWJ _CFG<br>[2:0]|Available debug ports|SWJ I/O pin assigned|Col4|Col5|Col6|Col7|
|---|---|---|---|---|---|---|
|**SWJ _CFG**<br>**[2:0]**|**Available debug ports**|**PA13 /**<br>**JTMS/**<br>**SWDIO**|**PA14 /**<br>**JTCK/S**<br>**WCLK**|**PA15 /**<br>**JTDI**|**PB3 / JTDO/**<br>**TRACE**<br>**SWO**|**PB4/**<br>**NJTRST**|
|000|Full SWJ (JTAG-DP + SW-DP)<br>(Reset state)|X|X|X|X|X|
|001|Full SWJ (JTAG-DP + SW-DP)<br>but without NJTRST|X|X|X|x|Free|
|010|JTAG-DP Disabled and<br>SW-DP Enabled|X|X|Free|Free(1)|Free|
|100|JTAG-DP Disabled and<br>SW-DP Disabled|Free|Free|Free|Free|Free|
|Other|Forbidden|-|-|-|-|-|


1. Released only if not using asynchronous trace.


**7.3.4** **Timer alternate function remapping**


Timer 4 channels 1 to 4 can be remapped from Port B to Port D. Other timer remapping
possibilities are listed in _Table 35_ to _Table 37_ . Refer to _AF remap and debug I/O_
_configuration register (AFIO_MAPR)_ .


118/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


**Table 30. TIM5 alternate function remapping** **[(1)]**

|Alternate function|TIM5CH4_IREMAP = 0|TIM5CH4_IREMAP = 1|
|---|---|---|
|TIM5_CH4|TIM5 Channel 4 is<br>connected to PA3|LSI internal clock is connected to TIM5_CH4<br>input for calibration purpose.|



1. Remap available only for high-density value line devices.


**Table 31. TIM12 remapping** **[(1)]**

|Alternate function|TIM12_REMAP = 0|TIM12_REMAP = 1|
|---|---|---|
|TIM12_CH1|PC4|PB12|
|TIM12_CH2|PC5|PB13|



1. Refer to the AF remap and debug I/O configuration register _Section 7.4.7: AF remap and debug I/O_
_configuration register (AFIO_MAPR2)_ . Remap available only for high-density value line devices.


**Table 32. TIM13 remapping** **[(1)]**

|Alternate function|TIM13_REMAP = 0|TIM13_REMAP = 1|
|---|---|---|
|TIM13_CH1|PC8|PB0|



1. Refer to the AF remap and debug I/O configuration register _Section 7.4.7: AF remap and debug I/O_
_configuration register (AFIO_MAPR2)_ . Remap available only for high-density value line devices.


**Table 33. TIM14 remapping** **[(1)]**

|Alternate function|TIM14_REMAP = 0|TIM14_REMAP = 1|
|---|---|---|
|TIM14_CH1|PC9|PB1|



1. Refer to the AF remap and debug I/O configuration register _Section 7.4.7: AF remap and debug I/O_
_configuration register (AFIO_MAPR2)_ . Remap available only for high-density value line devices.


**Table 34. TIM4 alternate function remapping**

|Alternate function|TIM4_REMAP = 0|TIM4_REMAP = 1(1)|
|---|---|---|
|TIM4_CH1|PB6|PD12|
|TIM4_CH2|PB7|PD13|
|TIM4_CH3|PB8|PD14|
|TIM4_CH4|PB9|PD15|



1. Remap available only for 100-pin and for 144-pin package.


**Table 35. TIM3 alternate function remapping**

|Alternate function|TIM3_REMAP[1:0] =<br>“00” (no remap)|TIM3_REMAP[1:0] =<br>“10” (partial remap)|TIM3_REMAP[1:0] =<br>“11” (full remap) (1)|
|---|---|---|---|
|TIM3_CH1|PA6|PB4|PC6|
|TIM3_CH2|PA7|PB5|PC7|
|TIM3_CH3|PB0|PB0|PC8|
|TIM3_CH4|PB1|PB1|PC9|



RM0041 Rev 6 119/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


1. Remap available only for 64-pin, 100-pin and 144-pin packages.


**Table 36. TIM2 alternate function remapping**















|Alternate<br>function|TIM2_REMAP<br>[1:0] = “00”<br>(no remap)|TIM2_REMAP<br>[1:0] = “01”<br>(partial remap)|TIM2_REMAP<br>[1:0] = “10”<br>(partial remap)|TIM2_REMAP<br>[1:0] = “11”<br>(full remap)|
|---|---|---|---|---|
|TIM2_CH1_ETR(1)|PA0|PA15|PA0|PA15|
|TIM2_CH2|PA1|PB3|PA1|PB3|
|TIM2_CH3|PA2|PA2|PB10|PB10|
|TIM2_CH4|PA3|PA3|PB11|PB11|


1. TIM_CH1 and TIM_ETR share the same pin but cannot be used at the same time (which is why we have
this notation: TIM2_CH1_ETR).


**Table 37. TIM1 alternate function remapping**

|Alternate functions<br>mapping|TIM1_REMAP[1:0] =<br>“00” (no remap)|TIM1_REMAP[1:0] =<br>“01” (partial remap)|TIM1_REMAP[1:0] =<br>“11” (full remap)(1)|
|---|---|---|---|
|TIM1_ETR|PA12|PA12|PE7|
|TIM1_CH1|PA8|PA8|PE9|
|TIM1_CH2|PA9|PA9|PE11|
|TIM1_CH3|PA10|PA10|PE13|
|TIM1_CH4|PA11|PA11|PE14|
|TIM1_BKIN|PB12|PA6|PE15|
|TIM1_CH1N|PB13|PA7|PE8|
|TIM1_CH2N|PB142)|PB0|PE10|
|TIM1_CH3N|PB15(2)|PB1|PE12|



1. Remap available only for 100-pin and 144-pin packages.


**Table 38. TIM1 DMA remapping** **[(1)]**

|DMA requests|TIM1_DMA_REMAP = 0|TIM1_DMA_REMAP = 1|
|---|---|---|
|TIM1_CH1 DMA request|Mapped on DMA1 Channel2|Mapped on DMA1 Channel6|
|TIM1_CH2 DMA request|Mapped on DMA1 Channel3|Mapped on DMA1 Channel6|



1. Refer to the AF remap and debug I/O configuration register _Section 7.4.7: AF remap and debug I/O_
_configuration register (AFIO_MAPR2)_ .


**Table 39. TIM15 remapping** **[(1)]**

|Alternate function|TIM15_REMAP = 0|TIM15_REMAP = 1|
|---|---|---|
|TIM15_CH1|PA2|PB14|
|TIM15_CH2|PA3|PB15|



1. Refer to the AF remap and debug I/O configuration register _Section 7.4.7: AF remap and debug I/O_
_configuration register (AFIO_MAPR2)_ .


120/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


**Table 40. TIM16 remapping** **[(1)]**

|Alternate function|TIM16_REMAP = 0|TIM16_REMAP = 1|
|---|---|---|
|TIM16_CH1|PB8|PA6|



1. Refer to the AF remap and debug I/O configuration register _Section 7.4.7: AF remap and debug I/O_
_configuration register (AFIO_MAPR2)_ .


**Table 41. TIM17 remapping** **[(1)]**

|Alternate function|TIM17_REMAP = 0|TIM17_REMAP = 1|
|---|---|---|
|TIM17_CH1|PB9|PA7|



1. Refer to the AF remap and debug I/O configuration register _Section 7.4.7: AF remap and debug I/O_
_configuration register (AFIO_MAPR2)_ .


**7.3.5** **USART alternate function remapping**


Refer to _AF remap and debug I/O configuration register (AFIO_MAPR)_ .


**Table 42. USART3 remapping**







|Alternate function|USART3_REMAP[1:0]<br>= “00” (no remap)|USART3_REMAP[1:0] =<br>“01” (partial remap) (1)|USART3_REMAP[1:0]<br>= “11” (full remap) (2)|
|---|---|---|---|
|USART3_TX|PB10|PC10|PD8|
|USART3_RX|PB11|PC11|PD9|
|USART3_CK|PB12|PC12|PD10|
|USART3_CTS|PB13|PB13|PD11|
|USART3_RTS|PB14|PB14|PD12|


1. Remap available only for 64-pin, 100-pin and 144-pin packages


2. Remap available only for 100-pin and 144-pin packages.


**Table 43. USART2 remapping**

|Alternate functions|USART2_REMAP = 0|USART2_REMAP = 1(1)|
|---|---|---|
|USART2_CTS|PA0|PD3|
|USART2_RTS|PA1|PD4|
|USART2_TX|PA2|PD5|
|USART2_RX|PA3|PD6|
|USART2_CK|PA4|PD7|



1. Remap available only for 100-pin and 144-pin packages.


**Table 44. USART1 remapping**

|Alternate function|USART1_REMAP = 0|USART1_REMAP = 1|
|---|---|---|
|USART1_TX|PA9|PB6|
|USART1_RX|PA10|PB7|



RM0041 Rev 6 121/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


**7.3.6** **I2C1 alternate function remapping**


Refer to _AF remap and debug I/O configuration register (AFIO_MAPR)_


**Table 45. I2C1 remapping**

|Alternate function|I2C1_REMAP = 0|I2C1_REMAP = 1|
|---|---|---|
|I2C1_SCL|PB6|PB8|
|I2C1_SDA|PB7|PB9|



**7.3.7** **SPI1 alternate function remapping**


Refer to _AF remap and debug I/O configuration register (AFIO_MAPR)_


**Table 46. SPI1 remapping**

|Alternate function|SPI1_REMAP = 0|SPI1_REMAP = 1|
|---|---|---|
|SPI1_NSS|PA4|PA15|
|SPI1_SCK|PA5|PB3|
|SPI1_MISO|PA6|PB4|
|SPI1_MOSI|PA7|PB5|



**7.3.8** **CEC remap**


Refer to _Section 7.4.7: AF remap and debug I/O configuration register (AFIO_MAPR2)_ .


**Table 47. CEC remapping**

|Alternate function|CEC_REMAP = 0|CEC_REMAP = 1|
|---|---|---|
|CEC|PB8|PB10|



122/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**

## **7.4 AFIO registers**


Refer to _Section 1.1 on page 32_ for a list of abbreviations used in register descriptions.


_Note:_ _To read/write the AFIO_EVCR, AFIO_MAPR, AFIO_MAPR2 and AFIO_EXTICRX registers,_
_the AFIO clock should first be enabled. Refer to APB2 peripheral clock enable register_
_(RCC_APB2ENR)._


The peripheral registers have to be accessed by words (32-bit).


**7.4.1** **Event control register (AFIO_EVCR)**


Address offset: 0x00


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8|7|6 5 4|Col4|Col5|3 2 1 0|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|EVOE|PORT[2:0]|PORT[2:0]|PORT[2:0]|PIN[3:0]|PIN[3:0]|PIN[3:0]|PIN[3:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:8 Reserved


Bit 7 **EVOE:** Event output enable
Set and cleared by software. When set the EVENTOUT Cortex [®] output is connected to the
I/O selected by the PORT[2:0] and PIN[3:0] bits.


Bits 3:0 **PIN[3:0]:** Pin selection (x = A .. E)
Set and cleared by software. Select the pin used to output the Cortex [®] EVENTOUT signal.

0000: Px0 selected

0001: Px1 selected

0010: Px2 selected

0011: Px3 selected

...

1111: Px15 selected


RM0041 Rev 6 123/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


**7.4.2** **AF remap and debug I/O configuration register (AFIO_MAPR)**


Address offset: 0x04


Reset value: 0x0000 0000








|31 30 29 28 27|26 25 24|Col3|Col4|23 22 21 20 19 18 17|16|
|---|---|---|---|---|---|
|Reserved|SWJ_CFG[2:0]|SWJ_CFG[2:0]|SWJ_CFG[2:0]|Reserved|TIM5CH4<br>_IREMAP|
|Reserved|w|w|w|w|rw|







|15|14 13|12|11 10|Col5|9 8|Col7|7 6|Col9|5 4|Col11|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PD01_<br>REMAP|Reserved|TIM4_<br>REMAP|TIM3_REMAP<br>[1:0]|TIM3_REMAP<br>[1:0]|TIM2_REMAP<br>[1:0]|TIM2_REMAP<br>[1:0]|TIM1_REMAP<br>[1:0]|TIM1_REMAP<br>[1:0]|USART3_<br>REMAP[1:0]|USART3_<br>REMAP[1:0]|USART2_<br>REMAP|USART1_<br>REMAP|I2C1_<br>REMAP|SPI1_<br>REMAP|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:27 Reserved


Bits 26:24 **SWJ_CFG[2:0]:** Serial wire JTAG configuration

These bits are write-only (when read, the value is undefined). They are used to configure the
SWJ and trace alternate function I/Os. The SWJ (Serial Wire JTAG) supports JTAG or SWD
access to the Cortex [®] debug port. The default state after reset is SWJ ON without trace.
This allows JTAG or SW mode to be enabled by sending a specific sequence on the JTMS /
JTCK pin.
000: Full SWJ (JTAG-DP + SW-DP): Reset State
001: Full SWJ (JTAG-DP + SW-DP) but without NJTRST
010: JTAG-DP Disabled and SW-DP Enabled

100: JTAG-DP Disabled and SW-DP Disabled

Other combinations: no effect


Bits 23:17 Reserved.


Bit 15 **PD01_REMAP:** Port D0/Port D1 mapping on OSC_IN/OSC_OUT

This bit is set and cleared by software. It controls the mapping of PD0 and PD1 GPIO
functionality. When the HSE oscillator is not used (application running on internal 8 MHz RC)
PD0 and PD1 can be mapped on OSC_IN and OSC_OUT. This is available only on 48- and
64-pin packages (PD0 and PD1 are available on 100-pin packages, no need for remapping).
0: No remapping of PD0 and PD1
1: PD0 remapped on OSC_IN, PD1 remapped on OSC_OUT,


Bits 14:13 Reserved.


Bit 12 **TIM4_REMAP:** TIM4 remapping

This bit is set and cleared by software. It controls the mapping of TIM4 channels 1 to 4 onto
the GPIO ports.
0: No remap (TIM4_CH1/PB6, TIM4_CH2/PB7, TIM4_CH3/PB8, TIM4_CH4/PB9)
1: Full remap (TIM4_CH1/PD12, TIM4_CH2/PD13, TIM4_CH3/PD14, TIM4_CH4/PD15)

_Note: TIM4_ETR on PE0 is not re-mapped._


Bits 11:10 **TIM3_REMAP[1:0]:** TIM3 remapping

These bits are set and cleared by software. They control the mapping of TIM3 channels 1 to
4 on the GPIO ports.
00: No remap (CH1/PA6, CH2/PA7, CH3/PB0, CH4/PB1)
01: Not used

10: Partial remap (CH1/PB4, CH2/PB5, CH3/PB0, CH4/PB1)
11: Full remap (CH1/PC6, CH2/PC7, CH3/PC8, CH4/PC9)

_Note: TIM3_ETR on PE0 is not re-mapped._


124/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


Bits 9:8 **TIM2_REMAP[1:0]:** TIM2 remapping

These bits are set and cleared by software. They control the mapping of TIM2 channels 1 to
4 and external trigger (ETR) on the GPIO ports.
00: No remap (CH1/ETR/PA0, CH2/PA1, CH3/PA2, CH4/PA3)
01: Partial remap (CH1/ETR/PA15, CH2/PB3, CH3/PA2, CH4/PA3)
10: Partial remap (CH1/ETR/PA0, CH2/PA1, CH3/PB10, CH4/PB11)
11: Full remap (CH1/ETR/PA15, CH2/PB3, CH3/PB10, CH4/PB11)


Bits 7:6 **TIM1_REMAP[1:0]:** TIM1 remapping

These bits are set and cleared by software. They control the mapping of TIM1 channels 1 to
4, 1N to 3N, external trigger (ETR) and Break input (BKIN) on the GPIO ports.
00: No remap (ETR/PA12, CH1/PA8, CH2/PA9, CH3/PA10, CH4/PA11, BKIN/PB12,
CH1N/PB13, CH2N/PB14, CH3N/PB15)
01: Partial remap (ETR/PA12, CH1/PA8, CH2/PA9, CH3/PA10, CH4/PA11, BKIN/PA6,
CH1N/PA7, CH2N/PB0, CH3N/PB1)
10: not used

11: Full remap (ETR/PE7, CH1/PE9, CH2/PE11, CH3/PE13, CH4/PE14, BKIN/PE15,
CH1N/PE8, CH2N/PE10, CH3N/PE12)


Bits 5:4 **USART3_REMAP[1:0]:** USART3 remapping

These bits are set and cleared by software. They control the mapping of USART3 CTS,
RTS,CK,TX and RX alternate functions on the GPIO ports.
00: No remap (TX/PB10, RX/PB11, CK/PB12, CTS/PB13, RTS/PB14)
01: Partial remap (TX/PC10, RX/PC11, CK/PC12, CTS/PB13, RTS/PB14)
10: not used

11: Full remap (TX/PD8, RX/PD9, CK/PD10, CTS/PD11, RTS/PD12)


Bit 3 **USART2_REMAP:** USART2 remapping

This bit is set and cleared by software. It controls the mapping of USART2 CTS, RTS,CK,TX
and RX alternate functions on the GPIO ports.
0: No remap (CTS/PA0, RTS/PA1, TX/PA2, RX/PA3, CK/PA4)
1: Remap (CTS/PD3, RTS/PD4, TX/PD5, RX/PD6, CK/PD7)


Bit 2 **USART1_REMAP:** USART1 remapping

This bit is set and cleared by software. It controls the mapping of USART1 TX and RX
alternate functions on the GPIO ports.
0: No remap (TX/PA9, RX/PA10)
1: Remap (TX/PB6, RX/PB7)


Bit 1 **I2C1_REMAP:** I2C1 remapping

This bit is set and cleared by software. It controls the mapping of I2C1 SCL and SDA
alternate functions on the GPIO ports.
0: No remap (SCL/PB6, SDA/PB7)
1: Remap (SCL/PB8, SDA/PB9)


Bit 0 **SPI1_REMAP:** SPI1 remapping

This bit is set and cleared by software. It controls the mapping of SPI1 NSS, SCK, MISO,
MOSI alternate functions on the GPIO ports.
0: No remap (NSS/PA4, SCK/PA5, MISO/PA6, MOSI/PA7)
1: Remap (NSS/PA15, SCK/PB3, MISO/PB4, MOSI/PB5)


RM0041 Rev 6 125/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


**7.4.3** **External interrupt configuration register 1 (AFIO_EXTICR1)**


Address offset: 0x08


Reset value: 0x0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI3[3:0]|EXTI3[3:0]|EXTI3[3:0]|EXTI3[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI0[3:0]|EXTI0[3:0]|EXTI0[3:0]|EXTI0[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved


Bits 15:0 **EXTIx[3:0]:** EXTI x configuration (x= 0 to 3)

These bits are written by software to select the source input for EXTIx external interrupt.
Refer to _Section 8.2.5: External interrupt/event line mapping_
0000: PA[x] pin
0001: PB[x] pin
0010: PC[x] pin
0011: PD[x] pin
0100: PE[x] pin
0101: PF[x] pin
0110: PG[x] pin


**7.4.4** **External interrupt configuration register 2 (AFIO_EXTICR2)**


Address offset: 0x0C


Reset value: 0x0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI7[3:0]|EXTI7[3:0]|EXTI7[3:0]|EXTI7[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI4[3:0]|EXTI4[3:0]|EXTI4[3:0]|EXTI4[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved


Bits 15:0 **EXTIx[3:0]:** EXTI x configuration (x= 4 to 7)

These bits are written by software to select the source input for EXTIx external interrupt.
0000: PA[x] pin
0001: PB[x] pin
0010: PC[x] pin
0011: PD[x] pin
0100: PE[x] pin
0101: PF[x] pin
0110: PG[x] pin


126/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


**7.4.5** **External interrupt configuration register 3 (AFIO_EXTICR3)**


Address offset: 0x10


Reset value: 0x0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI11[3:0]|EXTI11[3:0]|EXTI11[3:0]|EXTI11[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI8[3:0]|EXTI8[3:0]|EXTI8[3:0]|EXTI8[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved


Bits 15:0 **EXTIx[3:0]** : EXTI x configuration (x= 8 to 11)

These bits are written by software to select the source input for EXTIx external interrupt.
0000: PA[x] pin
0001: PB[x] pin
0010: PC[x] pin
0011: PD[x] pin
0100: PE[x] pin
0101: PF[x] pin
0110: PG[x] pin


**7.4.6** **External interrupt configuration register 4 (AFIO_EXTICR4)**


Address offset: 0x14


Reset value: 0x0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI15[3:0]|EXTI15[3:0]|EXTI15[3:0]|EXTI15[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI12[3:0]|EXTI12[3:0]|EXTI12[3:0]|EXTI12[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved


Bits 15:0 **EXTIx[3:0]** : EXTI x configuration (x= 12 to 15)

These bits are written by software to select the source input for EXTIx external interrupt.
0000: PA[x] pin
0001: PB[x] pin
0010: PC[x] pin
0011: PD[x] pin
0100: PE[x] pin
0101: PF[x] pin
0110: PG[x] pin


RM0041 Rev 6 127/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**


**7.4.7** **AF remap and debug I/O configuration register (AFIO_MAPR2)**


Address offset: 0x1C


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved



























|15 14|13|12|11|10|9|8|7 6 5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|MISC<br>_ <br>REM<br>AP|TIM12_<br>REMA<br>P|TIM67_<br>DAC_<br>DMA_<br>REMA<br>P|FSM<br>C_NA<br>DV|TIM14_<br>REMA<br>P|TIM13_<br>REMA<br>P|Reserved|TIM1_<br>DMA_<br>REMAP|CEC_<br>REMA<br>P|TIM17_<br>REMA<br>P|TIM16_<br>REMA<br>P|TIM15_<br>REMA<br>P|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:14 Reserved.


Bit 13 **MISC_REMAP:** Miscellaneous features remapping.

This bit is set and cleared by software. It controls miscellaneous features
The DMA2 channel 5 interrupt position in the vector table
The timer selection for DAC trigger 3 (TSEL[2:0] = 011, for more details refer to the
DAC_CR register).
0: DMA2 channel 5 interrupt is mapped with DMA2 channel 4 at position 59, TIM5 TRGO
event is selected as DAC Trigger 3, TIM5 triggers TIM1/3.
1: DMA2 channel 5 interrupt is mapped separately at position 60 and TIM15 TRGO event is
selected as DAC Trigger 3, TIM15 triggers TIM1/3.

_Note: This bit is available only in high density value line devices._


Bit 12 **TIM12_REMAP:** TIM12 remapping

This bit is set and cleared by software. It controls the mapping of the TIM12_CH1 and
TIM12_CH2 alternate function onto the GPIO ports.
0: No remap (CH1/PC4, CH2/PC5)
1: Remap (CH1/PB12, CH2/PB13)

_Note: This bit is available only in high density value line devices._


Bit 11 **TIM76_DAC_DMA_REMAP:** TIM67_DAC DMA remapping

This bit is set and cleared by software. It controls the mapping of the TIM6_DAC1 and
TIM7_DAC2 DMA requests onto the DMA1 channels.
0: No remap (TIM6_DAC1 DMA request/DMA2 Channel3, TIM7_DAC2 DMA request/DMA2
Channel4)
1: Remap (TIM6_DAC1 DMA request/DMA1 Channel3, TIM7_DAC2 DMA request/DMA1
Channel4)


Bit 10 **FSMC_NADV:** NADV connect/disconnect

This bit is set and cleared by software. It controls the use of the optional FSMC_NADV
signal.
0: The NADV signal is connected to the output (default)
1: The NADV signal is _not_ connected. The I/O pin can be used by another peripheral.

_Note: This bit is available only in high density value line devices._


Bit 9 **TIM14_REMAP:** TIM14 remapping

This bit is set and cleared by software. It controls the mapping of the TIM14_CH1 alternate
function onto the GPIO ports.
0: No remap (PC9)
1: Remap (PB1)


128/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


Bit 8 **TIM13_REMAP:** TIM13 remapping

This bit is set and cleared by software. It controls the mapping of the TIM13_CH1 alternate
function onto the GPIO ports.
0: No remap (PC8)
1: Remap (PB0)


Bits 7:5 Reserved.


Bit 4 **TIM1_DMA_REMAP:** TIM1 DMA remapping

This bit is set and cleared by software. It controls the mapping of the TIM1 channel 1 and
channel 2 DMA requests onto the DMA1 channels.
0: No remap (TIM1_CH1 DMA request/DMA1 Channel2, TIM1_CH2 DMA request/DMA1
Channel3)
1: Remap (TIM1_CH1 DMA request/DMA1 Channel6, TIM1_CH2 DMA request/DMA1
Channel6)


Bit 3 **CEC_REMAP:** CEC remapping

This bit is set and cleared by software. It controls the mapping of the alternate functions of
the CEC line onto the GPIO ports.
0: No remap (CEC/PB8)
1: Remap (CEC/PB10)


Bit 2 **TIM17_REMAP:** TIM17 remapping

This bit is set and cleared by software. It controls the mapping of the alternate functions of
TIM17 channel 1 onto the GPIO ports.
0: No remap (CH1/PB9)
1: Remap (CH1/PA7)


Bit 1 **TIM16_REMAP:** TIM16 remapping

This bit is set and cleared by software. It controls the mapping of the alternate functions of
TIM16 channel 1 onto the GPIO ports.
0: No remap (CH1/PB8)
1: Remap (CH1/PA6)


Bit 0 **TIM15_REMAP:** TIM15 remapping

This bit is set and cleared by software. It controls the mapping of the alternate functions of
TIM15 channels 1 and 2 onto the GPIO ports.
0: No remap (CH1/PA2, CH2/PA3)
1: Remap (CH1/PB14, CH2/PB15)


RM0041 Rev 6 129/709



131


**General-purpose and alternate-function I/Os (GPIOs and AFIOs)** **RM0041**

## **7.5 GPIO and AFIO register maps**


The following tables give the GPIO and AFIO register map and the reset values.


Refer to _Table 1 on page 37_ and _Table 2 on page 38_ for the register boundary addresses.


**Table 48. GPIO register map and reset values**
















































































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|GPIOx<br>_CRL<br>Reset value|CNF<br>7<br>[1:0]<br><br>|CNF<br>7<br>[1:0]<br><br>|MODE<br>7<br>[1:0]<br><br>|MODE<br>7<br>[1:0]<br><br>|CNF<br>6<br>[1:0]<br><br>|CNF<br>6<br>[1:0]<br><br>|MODE<br>6<br>[1:0]<br><br>|MODE<br>6<br>[1:0]<br><br>|CNF<br>5<br>[1:0]<br><br>|CNF<br>5<br>[1:0]<br><br>|MODE<br>5<br>[1:0]<br><br>|MODE<br>5<br>[1:0]<br><br>|CNF<br>4<br>[1:0]<br><br>|CNF<br>4<br>[1:0]<br><br>|MODE<br>4<br>[1:0]<br><br>|MODE<br>4<br>[1:0]<br><br>|CNF<br>3<br>[1:0]<br><br>|CNF<br>3<br>[1:0]<br><br>|MOD<br>E3<br>[1:0]<br><br>|MOD<br>E3<br>[1:0]<br><br>|CNF<br>2<br>[1:0]<br><br>|CNF<br>2<br>[1:0]<br><br>|MODE<br>2<br>[1:0]<br><br>|MODE<br>2<br>[1:0]<br><br>|CNF<br>1<br>[1:0]<br><br>|CNF<br>1<br>[1:0]<br><br>|MOD<br>E1<br>[1:0]<br><br>|MOD<br>E1<br>[1:0]<br><br>|CNF<br>0<br>[1:0]<br><br>|CNF<br>0<br>[1:0]<br><br>|MODE<br>0<br>[1:0]<br><br>|MODE<br>0<br>[1:0]<br><br>|
|0x00|GPIOx<br>_CRL<br>Reset value|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|
|0x04|GPIOx<br>_CRH<br>Reset value|CNF<br>15<br>[1:0]<br><br>|CNF<br>15<br>[1:0]<br><br>|MODE<br>15<br>[1:0]<br><br>|MODE<br>15<br>[1:0]<br><br>|CNF<br>14<br>[1:0]<br><br>|CNF<br>14<br>[1:0]<br><br>|MODE<br>14<br>[1:0]<br><br>|MODE<br>14<br>[1:0]<br><br>|CNF<br>13<br>[1:0]<br><br>|CNF<br>13<br>[1:0]<br><br>|MODE<br>13<br>[1:0]<br><br>|MODE<br>13<br>[1:0]<br><br>|CNF<br>12<br>[1:0]<br><br>|CNF<br>12<br>[1:0]<br><br>|MODE<br>12<br>[1:0]<br><br>|MODE<br>12<br>[1:0]<br><br>|CNF<br>11<br>[1:0]<br><br>|CNF<br>11<br>[1:0]<br><br>|MOD<br>E11<br>[1:0]<br><br>|MOD<br>E11<br>[1:0]<br><br>|CNF<br>10<br>[1:0]<br><br>|CNF<br>10<br>[1:0]<br><br>|MODE<br>10<br>[1:0]<br><br>|MODE<br>10<br>[1:0]<br><br>|CNF<br>9<br>[1:0]<br><br>|CNF<br>9<br>[1:0]<br><br>|MOD<br>E9<br>[1:0]<br><br>|MOD<br>E9<br>[1:0]<br><br>|CNF<br>8<br>[1:0]<br><br>|CNF<br>8<br>[1:0]<br><br>|MODE<br>8<br>[1:0]<br><br>|MODE<br>8<br>[1:0]<br><br>|
|0x04|GPIOx<br>_CRH<br>Reset value|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|~~0~~|~~1~~|~~0~~|~~0~~|
|0x08|GPIOx<br>_IDR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|IDRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x08|GPIOx<br>_IDR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x0C|GPIOx<br>_ODR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|ODRy<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x0C|GPIOx<br>_ODR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x10|GPIOx<br>_BSRR<br>Reset value|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BSR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x10|GPIOx<br>_BSRR<br>Reset value|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x14|GPIOx<br>_BRR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|BR[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x14|GPIOx<br>_BRR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x18|GPIOx<br>_LCKR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|LCKK<br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|LCK[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x18|GPIOx<br>_LCKR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|



**Table 49. AFIO register map and reset values**





|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|AFIO_EVCR<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|EVOE<br>|PORT[2:<br>0]<br><br><br>|PORT[2:<br>0]<br><br><br>|PORT[2:<br>0]<br><br><br>|PIN[3:0]<br><br><br>|PIN[3:0]<br><br><br>|PIN[3:0]<br><br><br>|
|0x00|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x04|AFIO_MAPR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|SWJ_<br>CFG[2:0]<br><br><br>|SWJ_<br>CFG[2:0]<br><br><br>|SWJ_<br>CFG[2:0]<br><br><br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|TIM5CH4_IREMAP<br><br>|PD01_REMAP<br>|Reserved<br>|Reserved<br>|TIM4_REMAP<br>|TIM3_REMAP[1:0]<br><br>|TIM3_REMAP[1:0]<br><br>|TIM2_REMAP[1:0]<br><br>|TIM2_REMAP[1:0]<br><br>|TIM1_REMAP[1:0]<br><br>|TIM1_REMAP[1:0]<br><br>|USART3_REMAP[1:0]<br><br><br>|USART3_REMAP[1:0]<br><br><br>|USART2_REMAP<br><br>|USART1_REMAP<br><br>|I2C1_REMAP<br><br>|SPI1_REMAP<br>|
|0x04|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|


130/709 RM0041 Rev 6


**RM0041** **General-purpose and alternate-function I/Os (GPIOs and AFIOs)**


**Table 49. AFIO register map and reset values (continued)**







|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x08|AFIO_EXTICR1<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|EXTI3[3:0]<br><br><br><br>|EXTI3[3:0]<br><br><br><br>|EXTI3[3:0]<br><br><br><br>|EXTI3[3:0]<br><br><br><br>|EXTI2[3:0]<br><br><br><br>|EXTI2[3:0]<br><br><br><br>|EXTI2[3:0]<br><br><br><br>|EXTI2[3:0]<br><br><br><br>|EXTI1[3:0]<br><br><br><br>|EXTI1[3:0]<br><br><br><br>|EXTI1[3:0]<br><br><br><br>|EXTI1[3:0]<br><br><br><br>|EXTI0[3:0]<br><br><br><br>|EXTI0[3:0]<br><br><br><br>|EXTI0[3:0]<br><br><br><br>|EXTI0[3:0]<br><br><br><br>|
|0x08|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x0C|AFIO_EXTICR2<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|EXTI7[3:0]<br><br><br><br>|EXTI7[3:0]<br><br><br><br>|EXTI7[3:0]<br><br><br><br>|EXTI7[3:0]<br><br><br><br>|EXTI6[3:0]<br><br><br><br>|EXTI6[3:0]<br><br><br><br>|EXTI6[3:0]<br><br><br><br>|EXTI6[3:0]<br><br><br><br>|EXTI5[3:0]<br><br><br><br>|EXTI5[3:0]<br><br><br><br>|EXTI5[3:0]<br><br><br><br>|EXTI5[3:0]<br><br><br><br>|EXTI4[3:0]<br><br><br><br>|EXTI4[3:0]<br><br><br><br>|EXTI4[3:0]<br><br><br><br>|EXTI4[3:0]<br><br><br><br>|
|0x0C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x10|AFIO_EXTICR3<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|EXTI11[3:0]<br><br><br><br>|EXTI11[3:0]<br><br><br><br>|EXTI11[3:0]<br><br><br><br>|EXTI11[3:0]<br><br><br><br>|EXTI10[3:0]<br><br><br><br>|EXTI10[3:0]<br><br><br><br>|EXTI10[3:0]<br><br><br><br>|EXTI10[3:0]<br><br><br><br>|EXTI9[3:0]<br><br><br><br>|EXTI9[3:0]<br><br><br><br>|EXTI9[3:0]<br><br><br><br>|EXTI9[3:0]<br><br><br><br>|EXTI8[3:0]<br><br><br><br>|EXTI8[3:0]<br><br><br><br>|EXTI8[3:0]<br><br><br><br>|EXTI8[3:0]<br><br><br><br>|
|0x10|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x14|AFIO_EXTICR4<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|EXTI15[3:0]<br><br><br><br>|EXTI15[3:0]<br><br><br><br>|EXTI15[3:0]<br><br><br><br>|EXTI15[3:0]<br><br><br><br>|EXTI14[3:0]<br><br><br><br>|EXTI14[3:0]<br><br><br><br>|EXTI14[3:0]<br><br><br><br>|EXTI14[3:0]<br><br><br><br>|EXTI13[3:0]<br><br><br><br>|EXTI13[3:0]<br><br><br><br>|EXTI13[3:0]<br><br><br><br>|EXTI13[3:0]<br><br><br><br>|EXTI12[3:0]<br><br><br><br>|EXTI12[3:0]<br><br><br><br>|EXTI12[3:0]<br><br><br><br>|EXTI12[3:0]<br><br><br><br>|
|0x14|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x1C|AFIO_MAPR2<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|MISC_ REMAP<br><br>|TIM12_REMAP<br><br>|TIM67_DAC_ DMA_ REMAP<br><br>|FSMC_NADV<br><br>|TIM14_REMAP<br><br>|TIM13_REMAP<br>|Res.<br>|Res.<br>|Res.<br>|TIM1_DMA_REMAP<br><br>|CEC_REMAP<br><br>|TIM17_REMAP<br><br>|TIM16_REMAP<br><br>|TIM15_REMAP<br>|
|0x1C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|


RM0041 Rev 6 131/709



131


