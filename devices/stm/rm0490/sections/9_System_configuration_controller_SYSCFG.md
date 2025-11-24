**RM0490** **System configuration controller (SYSCFG)**

# **9 System configuration controller (SYSCFG)**


The devices feature a set of configuration registers. The main purposes of the system
configuration controller are the following:

      - Enabling/disabling I [2] C-bus Fast-mode Plus mode on some I/O ports


      - Configuring the IR modulation signal and its output polarity


      - Remapping of some I/O ports


      - Remapping the memory located at the beginning of the code area


      - Flag pending interrupts from each interrupt line


      - Managing robustness feature

## **9.1 SYSCFG registers**


**9.1.1** **SYSCFG configuration register 1 (SYSCFG_CFGR1)**


This register is used for specific configurations of memory remap and to control special I/O
features.
Two bits are used to configure the type of memory accessible at address 0x0000 0000.
These bits are used to select the physical remap by software and so, bypass the hardware
BOOT selection. After reset these bits take the value selected by the actual boot mode
configuration.
If the Fm+ mode is desired on the I2C pins, first assign GPIOs to I2Cx through the
GPIOx_AFRH or GPIOx_AFRL alternate function registers and then only activate the Fm+
mode.


The Fm+ mode on a GPIO _y_ used as I2Cx can individually be activated by setting its
corresponding I2C_ _y_ _FMP bit. It can also collectively be activated for GPIOs used as I2C _x_,
by setting the I2C _x_ _FMP bit. If the Fm+ mode is not desired on a GPIO _y_ used as I2C _x_, both
I2C_ _y_ _FMP and I2C _x_ _FMP bits must be cleared.


When the Fm+ mode is activated, the speed configuration of the I/O (GPIOx OSPEEDR) is
ignored.


Address offset: 0x00


Reset value: 0x0000 000X (X is the memory mode selected by the actual boot mode
configuration)





















|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|I2C_<br>PC14_<br>FMP|I2C_<br>PA10_<br>FMP|I2C_<br>PA9_<br>FMP|I2C2_<br>FMP|I2C1_<br>FMP|I2C_<br>PB9_<br>FMP|I2C_<br>PB8_<br>FMP|I2C_<br>PB7_<br>FMP|I2C_<br>PB6_<br>FMP|
||||||||rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7 6|Col10|5|4|3|2|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|IR_MOD<br>[1:0]|IR_MOD<br>[1:0]|IR_<br>POL|PA12_<br>RMP|PA11_<br>RMP|Res.|MEM_MODE<br>[1:0]|MEM_MODE<br>[1:0]|
|||||||||rw|rw|rw|rw|rw||rw|rw|


RM0490 Rev 5 195/1027



216


**System configuration controller (SYSCFG)** **RM0490**


Bits 31:25 Reserved, must be kept at reset value.


Bit 24 **I2C_PC14_FMP** : Fast-mode Plus (Fm+) enable for PC14

This bit is set and cleared by software. It enables I2C Fm+ driving capability on PC14 I/O
port.
0: Disable if not enabled through I2Cx_FMP

1: Enable

_Note: Not available on STM32C011xx._


Bit 23 **I2C_PA10_FMP:** Fast-mode Plus (Fm+) enable for PA10

This bit is set and cleared by software. It enables I2C Fm+ driving capability on PA10 I/O
port.
0: Disable disabled if not enabled through I2Cx_FMP

1: Enable


Bit 22 **I2C_PA9_FMP:** Fast-mode Plus (Fm+) enable for PA9

This bit is set and cleared by software. It enables I2C Fm+ driving capability on PA9 I/O port.
0: Disable disabled if not enabled through I2Cx_FMP

1: Enable


Bit 21 **I2C2_FMP** : Fast-mode Plus (Fm+) enable for I2C2

This bit is set and cleared by software. It enables I2C Fm+ driving capability on I/O ports
configured as I2C2 through GPIOx_AFR registers.
0: Disable disabled if not enabled through I2C_y_FMP

1: Enable

_Note: Only applicable to STM32C051xx, STM32C071xx, and STM32C091xx/92xx. Reserved_
_on the other products._


Bit 20 **I2C1_FMP** : Fast-mode Plus (Fm+) enable for I2C1

This bit is set and cleared by software. It enables I2C Fm+ driving capability on I/O ports
configured as I2C1 through GPIOx_AFR registers.
0: Disable disabled if not enabled through I2C_y_FMP

1: Enable


Bit 19 **I2C_PB9_FMP:** Fast-mode Plus (Fm+) enable for PB9

This bit is set and cleared by software. It enables I2C Fm+ driving capability on PB9 I/O port.
0: Disable disabled if not enabled through I2Cx_FMP

1: Enable

_Note: Not available on STM32C011xx._


Bit 18 **I2C_PB8_FMP:** Fast-mode Plus (Fm+) enable for PB8

This bit is set and cleared by software. It enables I2C Fm+ driving capability on PB8 I/O port.
0: Disable disabled if not enabled through I2Cx_FMP

1: Enable

_Note: Not available on STM32C011xx._


Bit 17 **I2C_PB7_FMP:** Fast-mode Plus (Fm+) enable for PB7

This bit is set and cleared by software. It enables I2C Fm+ driving capability on PB7 I/O port.
0: Disable disabled if not enabled through I2Cx_FMP

1: Enable


Bit 16 **I2C_PB6_FMP:** Fast-mode Plus (Fm+) enable for PB6

This bit is set and cleared by software. It enables I2C Fm+ driving capability on PB6 I/O port.
0: Disable disabled if not enabled through I2Cx_FMP

1: Enable


Bits 15:8 Reserved, must be kept at reset value.


196/1027 RM0490 Rev 5


**RM0490** **System configuration controller (SYSCFG)**


Bits 7:6 **IR_MOD[1:0]:** IR Modulation Envelope signal selection

This bitfield selects the signal for IR modulation envelope:

00: TIM16

01: USART1

10: USART2

11: Reserved


Bit 5 **IR_POL:** IR output polarity selection

0: Output of IRTIM (IR_OUT) is not inverted
1: Output of IRTIM (IR_OUT) is inverted


Bit 4 **PA12_RMP** : PA12 pin remapping

This bit is set and cleared by software. When set, it remaps the PA12 pin to operate as PA10
GPIO port, instead as PA12 GPIO port. In this case, the original PA10 pin (if available) is
forced to analog mode.
0: No remap (PA12)
1: Remap (PA10)

_Note: If the PINMUX4[1:0] bitfield of the SYSCFG_CFGR3 register is at 00, PA12_RMP must_
_be kept at 0 to prevent conflict due to two GPIO outputs with different output levels_
_connected to the same pin._


Bit 3 **PA11_RMP** : PA11 pin remapping

This bit is set and cleared by software. When set, it remaps the PA11 pin to operate as PA9
GPIO port, instead as PA11 GPIO port. In this case, the original PA9 pin (if available) is
forced to analog mode.
0: No remap (PA11)
1: Remap (PA9)

_Note: If the PINMUX2[1:0] bitfield of the SYSCFG_CFGR3 register is at 00, PA11_RMP must_
_be kept at 0 to prevent conflict due to two GPIO outputs with different output levels_
_connected to the same pin._


Bit 2 Reserved, must be kept at reset value.


Bits 1:0 **MEM_MODE[1:0]:** Memory mapping selection bits

This bitfield controlled by software selects the memory internally mapped at the address
0x0000 0000. Its reset value is determined by the boot mode configuration. Refer to
_Section 3: Boot modes_ for more details.

x0: Main flash memory
01: System flash memory
11: Embedded SRAM


**9.1.2** **SYSCFG configuration register 2 (SYSCFG_CFGR2)**


Address offset: 0x18


Reset value: 0x0000 0000


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||






|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LOCKU<br>P_LOC<br>K|
||||||||||||||||rw|



RM0490 Rev 5 197/1027



216


**System configuration controller (SYSCFG)** **RM0490**


Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **LOCKUP_LOCK** : Cortex [®] -M0+ LOCKUP enable

This bit is set by software and cleared by system reset. When set, it enables the connection
of Cortex [®] -M0+ LOCKUP (HardFault) output to the TIM1/16/17 Break input.

0: Disable

1: Enable


**9.1.3** **SYSCFG configuration register 3 (SYSCFG_CFGR3)**


In some products/packages with low pin count, several GPIOs may be internally connected
to the same pin. This register allows selecting the active GPIO that keeps the setting
specified by its corresponding GPIOx_MODER register. For STM32C011xx, STM32C031xx,
and STM32C071xx, the other GPIOs connected to the same pin are forced into digital input
(passive) mode regardless of their corresponding GPIOx_MODER register settings. For
STM32C051xx and STM32C091xx/92xx, the output buffer of the other GPIOs connected to
the same pin are disabled regardless of their corresponding GPIOx_MODER register
settings.
This is only effective when the SECURE_MUXING_EN bit of the _FLASH option register_
_(FLASH_OPTR)_ is set (default).
When SECURE_MUXING_EN is cleared, SYSCFG_CFGR3 has no effect. All GPIOs
connected to the same pin keep the configuration set in their corresponding
GPIOx_MODER register. The user software must then ensure that there is no conflict
between the GPIOs.


In the following bitfield descriptions, for products/packages not listed in the “condition”
preceding the bitfield values, consider the bitfield as reserved and keep it at its reset value.


Address offset: 0x3C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14|Col2|13 12|Col4|11 10|Col6|9 8|Col8|7 6|Col10|5 4|Col12|3 2|Col14|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PINMUX7[1:0]|PINMUX7[1:0]|PINMUX6[1:0]|PINMUX6[1:0]|PINMUX5[1:0]|PINMUX5[1:0]|PINMUX4[1:0]|PINMUX4[1:0]|PINMUX3[1:0]|PINMUX3[1:0]|PINMUX2[1:0]|PINMUX2[1:0]|PINMUX1[1:0]|PINMUX1[1:0]|PINMUX0[1:0]|PINMUX0[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:14 **PINMUX7[1:0]** : Pin GPIO multiplexer 7

This bitfield is set and cleared by software. It selects an active GPIO on a pin.

Condition: STM32C051x - GPIO assigned to WLCSP15 ball A2 or TSSOP20 pin 1

00: PB7

01: PB8

Other: Reserved


198/1027 RM0490 Rev 5


**RM0490** **System configuration controller (SYSCFG)**


Bits 13:12 **PINMUX6[1:0]** : Pin GPIO multiplexer 6

This bitfield is set and cleared by software. It selects an active GPIO on a pin.

Condition: STM32C051x - GPIO assigned to WLCSP15 ball B1 or TSSOP20 pin 20

00: PB6

01: PB3

10: PB4

11: PB5


Bits 11:10 **PINMUX5[1:0]** : Pin GPIO multiplexer 5

This bitfield is set and cleared by software. It selects an active GPIO on a pin.

Condition: STM32C011x - GPIO assigned to WLCSP12 ball F1

00: PA3

01: PA4

10: PA5

11: PA6

Condition: STM32C051xx - GPIO assigned to WLCSP15 ball E2 or TSSOP20 pin 19

00: PA14-BOOT0

01: PA15

Other: Reserved


Bits 9:8 **PINMUX4[1:0]** : Pin GPIO multiplexer 4

This bitfield is set and cleared by software. It selects an active GPIO on a pin.

Condition: STM32C011x - GPIO assigned to WLCSP12 ball E2

00: PA7

01: PA12

Other: Reserved

Condition: STM32C051xx - GPIO assigned to WLCSP15 ball H1

00: PA7

01: PA12 [PA10]

Other: Reserved

Condition: STM32C091/92xx - GPIO assigned to TSSOP20 pin 1 or WLCSP24 ball B4

00: PB7

01: PB8

Other: Reserved

_Note: The PA12_RMP bit of the SYSCFG_CFGR1 takes priority over the selection through_
_this bitfield. Refer to the description of the SYSCFG_CFGR1 register for more details._


RM0490 Rev 5 199/1027



216


**System configuration controller (SYSCFG)** **RM0490**


Bits 7:6 **PINMUX3[1:0]** : Pin GPIO multiplexer 3

This bitfield is set and cleared by software. It selects an active GPIO on a pin.

Condition: STM32C011x - GPIO assigned to SO8 pin 8

00: PA14

01: PB6

10: PC15

11: Reserved

Condition: STM32C051xx - GPIO assigned to WLCSP15 ball J2

00: PA5

01: PA6

Other: Reserved

Condition: STM32C071xx - GPIO assigned to WLCSP19 ball B3 or TSSOP20 pin 1

00: PB7

01: PB8

Other: Reserved

Condition: STM32C091/92xx - GPIO assigned WLCSP24 ball A3

00: PB5

01: PB3

Other: Reserved


Bits 5:4 **PINMUX2[1:0]** : Pin GPIO multiplexer 2

This bitfield is set and cleared by software. It selects an active GPIO on a pin.

Condition: STM32C011x - GPIO assigned to SO8 pin 5

00: PA8

01: PA11

Other: Reserved

Condition: STM32C051xx - GPIO assigned to WLCSP15 ball K3

00: PA3

01: PA4

Other: Reserved

Condition: STM32C071xx - GPIO assigned to TSSOP20 pin 20

00: PB6

01: PB3

10: PB4

11: PB5

Condition: STM32C091/92xx - GPIO assigned to TSSOP20 pin 20

00: PB6

01: PB3

10: PB4

11: PB5

Condition: STM32C091/92xx - GPIO assigned to WLCSP24 ball A5

00: PB6

01: PB4

Other: Reserved

_Note: The PA11_RMP bit of the SYSCFG_CFGR1 takes priority over the selection through_
_this bitfield. Refer to the description of the SYSCFG_CFGR1 register for more details._


200/1027 RM0490 Rev 5


**RM0490** **System configuration controller (SYSCFG)**


Bits 3:2 **PINMUX1[1:0]** : Pin GPIO multiplexer 1

This bitfield is set and cleared by software. It selects an active GPIO on a pin.

Condition: STM32C011x - GPIO assigned to SO8 pin 4

00: PF2-NRST

01: PA0

10: PA1

11: PA2

Condition: STM32C051xx - GPIO assigned to WLCSP15 ball G2

00: PA1

01: PA2

Other: Reserved

Condition: STM32C071xx - GPIO assigned to WLCSP19 ball B1 or TSSOP20 pin 19

00: PA14

01: PA15

Other: Reserved

Condition: STM32C091/92xx - GPIO assigned to TSSOP20 pin 15

00: PA8

01: PB0

10: PB1

11: PB2

Condition: STM32C091/92xx - GPIO assigned to WLCSP24 pin G1

00: PA8

01: PB2

Other: Reserved


Bits 1:0 **PINMUX0[1:0]** : Pin GPIO multiplexer 0

This bitfield is set and cleared by software. It selects an active GPIO on a pin.

Condition: STM32C011x - GPIO assigned to SO8 pin 1

00: PB7

01: PC14

Other: Reserved

Condition: STM32C051xx - GPIO assigned to WLCSP15 ball H3

00: PF2-NRST

01: PA0

Other: Reserved

Condition: STM32C071xx - GPIO assigned to WLCSP19 ball H3

00: PF2-NRST

01: PA0

Other: Reserved

Condition: STM32C091/92xx - GPIO assigned to TSSOP20 pin 19

00: PA14

01: PA15

Other: Reserved


**9.1.4** **SYSCFG interrupt line 0 status register (SYSCFG_ITLINE0)**


A dedicated set of registers is implemented on the device to collect all pending interrupt
sources associated with each interrupt line into a single register. This allows users to check
by single read which peripheral requires service in case more than one source is associated
to the interrupt line.
All bits in those registers are read only, set by hardware when there is corresponding


RM0490 Rev 5 201/1027



216


**System configuration controller (SYSCFG)** **RM0490**


interrupt request pending and cleared by resetting the interrupt source flags in the
peripheral registers.


Address offset: 0x80


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|WWDG|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **WWDG** : Window watchdog interrupt pending flag


**9.1.5** **SYSCFG interrupt line 1 status register (SYSCFG_ITLINE1)**


This register is only available on STM32C071xx. On the other devices, it is reserved.


Address offset: 0x84


Reset value: 0x0000 0000


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||



|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PVM_<br>VDDIO2<br>_OUT|Res.|
|||||||||||||||r||


Bits 31:2 Reserved, must be kept at reset value.







Bit 1 **PVM_VDDIO2_OUT** : V DDIO2 supply monitoring interrupt request pending (EXTI line 34)


Bit 0 Reserved, must be kept at reset value.


**9.1.6** **SYSCFG interrupt line 2 status register (SYSCFG_ITLINE2)**


Address offset: 0x88


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RTC|Res.|
|||||||||||||||r||



202/1027 RM0490 Rev 5


**RM0490** **System configuration controller (SYSCFG)**


Bits 31:2 Reserved, must be kept at reset value.


Bit 1 **RTC:** RTC interrupt request pending (EXTI line 19)


Bit 0 Reserved, must be kept at reset value.


**9.1.7** **SYSCFG interrupt line 3 status register (SYSCFG_ITLINE3)**


Address offset: 0x8C


Reset value: 0x0000 0000


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||



|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FLASH<br>_<br>ITF|Res.|
|||||||||||||||r||


Bits 31:2 Reserved, must be kept at reset value.


Bit 1 **FLASH_ITF** : Flash interface interrupt request pending


Bit 0 Reserved, must be kept at reset value.


**9.1.8** **SYSCFG interrupt line 4 status register (SYSCFG_ITLINE4)**


Address offset: 0x90


Reset value: 0x0000 0000







|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CRS|RCC|
|||||||||||||||r|r|


Bits 31:2 Reserved, must be kept at reset value.


Bit 1 **CRS** : CRS interrupt request pending

_Note: Only applicable on STM32C071xx, reserved on other products._


Bit 0 **RCC** : Reset and clock control interrupt request pending


RM0490 Rev 5 203/1027



216


**System configuration controller (SYSCFG)** **RM0490**


**9.1.9** **SYSCFG interrupt line 5 status register (SYSCFG_ITLINE5)**


Address offset: 0x94


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI1|EXTI0|
|||||||||||||||r|r|



Bits 31:2 Reserved, must be kept at reset value.


Bit 1 **EXTI1** : EXTI line 1 interrupt request pending


Bit 0 **EXTI0** : EXTI line 0 interrupt request pending


**9.1.10** **SYSCFG interrupt line 6 status register (SYSCFG_ITLINE6)**


Address offset: 0x98


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI3|EXTI2|
|||||||||||||||r|r|



Bits 31:2 Reserved, must be kept at reset value.


Bit 1 **EXTI3** : EXTI line 3 interrupt request pending


Bit 0 **EXTI2** : EXTI line 2 interrupt request pending


**9.1.11** **SYSCFG interrupt line 7 status register (SYSCFG_ITLINE7)**


Address offset: 0x9C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|EXTI15|EXTI14|EXTI13|EXTI12|EXTI11|EXTI10|EXTI9|EXTI8|EXTI7|EXTI6|EXTI5|EXTI4|
|||||r|r|r|r|r|r|r|r|r|r|r|r|



204/1027 RM0490 Rev 5


**RM0490** **System configuration controller (SYSCFG)**


Bits 31:12 Reserved, must be kept at reset value.


Bit 11 **EXTI15** : EXTI line 15 interrupt request pending


Bit 10 **EXTI14** : EXTI line 14 interrupt request pending


Bit 9 **EXTI13** : EXTI line 13 interrupt request pending


Bit 8 **EXTI12** : EXTI line 12 interrupt request pending


Bit 7 **EXTI11** : EXTI line 11 interrupt request pending


Bit 6 **EXTI10** : EXTI line 10 interrupt request pending


Bit 5 **EXTI9** : EXTI line 9 interrupt request pending


Bit 4 **EXTI8** : EXTI line 8 interrupt request pending


Bit 3 **EXTI7** : EXTI line 7 interrupt request pending


Bit 2 **EXTI6** : EXTI line 6 interrupt request pending


Bit 1 **EXTI5** : EXTI line 5 interrupt request pending


Bit 0 **EXTI4** : EXTI line 4 interrupt request pending


**9.1.12** **SYSCFG interrupt line 8 status register (SYSCFG_ITLINE8)**


This register is only available on STM32C071xx. On the other devices, it is reserved.


Address offset: 0xA0


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USB|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **USB** : USB interrupt request pending


**9.1.13** **SYSCFG interrupt line 9 status register (SYSCFG_ITLINE9)**


Address offset: 0xA4


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1<br>_CH1|
||||||||||||||||r|



RM0490 Rev 5 205/1027



216


**System configuration controller (SYSCFG)** **RM0490**


Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **DMA1_CH1** : DMA1 channel 1interrupt request pending


**9.1.14** **SYSCFG interrupt line 10 status register (SYSCFG_ITLINE10)**


Address offset: 0xA8


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1<br>_CH3|DMA1<br>_CH2|
|||||||||||||||r|r|



Bits 31:2 Reserved, must be kept at reset value.


Bit 1 **DMA1_CH3** : DMA1 channel 3 interrupt request pending


Bit 0 **DMA1_CH2** : DMA1 channel 2 interrupt request pending


**9.1.15** **SYSCFG interrupt line 11 status register (SYSCFG_ITLINE11)**


Address offset: 0xAC


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA_<br>CH7|DMA_<br>CH6|DMA_<br>CH5|DMA_<br>CH4|DMAM<br>UX|
||||||||||||r|r|r|r|r|



Bits 31:5 Reserved, must be kept at reset value.


Bit 4 **DMA_CH7** : DMA channel 7 interrupt request pending

_Note: Only applicable to STM32C091xx/92xx, reserved on the other products._


Bit 3 **DMA_CH6** : DMA channel 6 interrupt request pending

_Note: Only applicable to STM32C091xx/92xx, reserved on the other products._


Bit 2 **DMA_CH5** : DMA channel 5 interrupt request pending

_Note: Only applicable to STM32C051xx, STM32C071xx, and STM32C091xx/92xx, reserved_
_on the other products._


Bit 1 **DMA_CH4** : DMA channel 4 interrupt request pending

_Note: Only applicable to STM32C051xx, STM32C071xx, and STM32C091xx/92xx, reserved_
_on the other products._


Bit 0 **DMAMUX** : DMAMUX interrupt request pending


206/1027 RM0490 Rev 5


**RM0490** **System configuration controller (SYSCFG)**


**9.1.16** **SYSCFG interrupt line 12 status register (SYSCFG_ITLINE12)**


Address offset: 0xB0


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADC|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **ADC** : ADC interrupt request pending


**9.1.17** **SYSCFG interrupt line 13 status register (SYSCFG_ITLINE13)**


Address offset: 0xB4


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM1_B<br>RK|TIM1_<br>UPD|TIM1_<br>TRG|TIM1_<br>CCU|
|||||||||||||r|r|r|r|



Bits 31:4 Reserved, must be kept at reset value.


Bit 3 **TIM1_BRK** : Timer 1 break interrupt request pending


Bit 2 **TIM1_UPD** : Timer 1 update interrupt request pending


Bit 1 **TIM1_TRG** : Timer 1 trigger interrupt request pending


Bit 0 **TIM1_CCU** : Timer 1 commutation interrupt request pending


**9.1.18** **SYSCFG interrupt line 14 status register (SYSCFG_ITLINE14)**


Address offset: 0xB8


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM1_<br>CC|
||||||||||||||||r|



RM0490 Rev 5 207/1027



216


**System configuration controller (SYSCFG)** **RM0490**


Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **TIM1_CC** : Timer 1 capture compare interrupt request pending


**9.1.19** **SYSCFG interrupt line 15 status register (SYSCFG_ITLINE15)**


This register is only available on STM32C051xx, STM32C071xx, and STM32C091xx/92xx.
On the other devices, it is reserved.


Address offset: 0xBC


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM2|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **TIM2** : TIM2 interrupt request pending


**9.1.20** **SYSCFG interrupt line 16 status register (SYSCFG_ITLINE16)**


Address offset: 0xC0


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM3|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **TIM3** : Timer 3 interrupt request pending


**9.1.21** **SYSCFG interrupt line 19 status register (SYSCFG_ITLINE19)**


Address offset: 0xCC


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM14|
||||||||||||||||r|



208/1027 RM0490 Rev 5


**RM0490** **System configuration controller (SYSCFG)**


Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **TIM14** : Timer 14 interrupt request pending


**9.1.22** **SYSCFG interrupt line 20 status register (SYSCFG_ITLINE20)**


This register is only available on STM32C091xx/92xx. On the other devices, it is reserved.


Address offset: 0xD0


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM15|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **TIM15** : Timer 15 interrupt request pending


**9.1.23** **SYSCFG interrupt line 21 status register (SYSCFG_ITLINE21)**


Address offset: 0xD4


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM16|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **TIM16** : Timer 16 interrupt request pending


**9.1.24** **SYSCFG interrupt line 22 status register (SYSCFG_ITLINE22)**


Address offset: 0xD8


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM17|
||||||||||||||||r|



RM0490 Rev 5 209/1027



216


**System configuration controller (SYSCFG)** **RM0490**


Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **TIM17** : Timer 17 interrupt request pending


**9.1.25** **SYSCFG interrupt line 23 status register (SYSCFG_ITLINE23)**


Address offset: 0xDC


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|I2C1|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **I2C1** : I2C1 interrupt request pending, combined with EXTI line 23


**9.1.26** **SYSCFG interrupt line 24 status register (SYSCFG_ITLINE24)**


This register is only available on STM32C051xx, STM32C071xx, and STM32C091xx/92xx.
On the other devices, it is reserved.


Address offset: 0xE0


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|I2C2|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **I2C2** : I2C2 interrupt request pending


**9.1.27** **SYSCFG interrupt line 25 status register (SYSCFG_ITLINE25)**


Address offset: 0xE4


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SPI1|
||||||||||||||||r|



210/1027 RM0490 Rev 5


**RM0490** **System configuration controller (SYSCFG)**


Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **SPI1** : SPI1 interrupt request pending


**9.1.28** **SYSCFG interrupt line 26 status register (SYSCFG_ITLINE26)**


This register is only available on STM32C051xx, STM32C071xx, and STM32C091xx/92xx.
On the other devices, it is reserved.


Address offset: 0xE8


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SPI2|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **SPI2** : SPI2 interrupt request pending


**9.1.29** **SYSCFG interrupt line 27 status register (SYSCFG_ITLINE27)**


Address offset: 0xEC


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USART<br>1|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **USART1** : USART1 interrupt request pending, combined with EXTI line 25


**9.1.30** **SYSCFG interrupt line 28 status register (SYSCFG_ITLINE28)**


Address offset: 0xF0


Reset value: 0x0000 0000


RM0490 Rev 5 211/1027



216


**System configuration controller (SYSCFG)** **RM0490**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USART<br>2|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **USART2** : USART2 interrupt request pending (EXTI line 26)


**9.1.31** **SYSCFG interrupt line 29 status register (SYSCFG_ITLINE29)**


This register is only available on STM32C091xx/92xx. On the other devices, it is reserved.


Address offset: 0xF4


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USART4|USART3|
|||||||||||||||r|r|



Bits 31:2 Reserved, must be kept at reset value.


Bit 1 **USART4** : USART4 interrupt request pending


Bit 0 **USART3** : USART3 interrupt request pending


**9.1.32** **SYSCFG interrupt line 30 status register (SYSCFG_ITLINE30)**


This register is only available on STM32C092xx. On the other devices, it is reserved.


Address offset: 0xF8


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FDCAN_<br>IT0|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **FDCAN_IT0** : FDCAN interrupt request 0 pending


212/1027 RM0490 Rev 5


**RM0490** **System configuration controller (SYSCFG)**


**9.1.33** **SYSCFG interrupt line 31 status register (SYSCFG_ITLINE31)**


This register is only available on STM32C092xx. On the other devices, it is reserved.


Address offset: 0xFC


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FDCAN_<br>IT1|
||||||||||||||||r|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **FDCAN_IT1** : FDCAN interrupt request 1 pending


**9.1.34** **SYSCFG register map**


The following table gives the SYSCFG register map and the reset values.


**Table 41. SYSCFG register map and reset values**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00<br>|**SYSCFG_CFGR1**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|I2C_PC14_FMP|I2C_PA10_FMP|I2C_PA9_FMP|I2C2_FMP|I2C1_FMP|I2C_PB9_FMP|I2C_PB8_FMP|I2C_PB7_FMP|I2C_PB6_FMP|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|IR_MOD|IR_MOD|IR_POL|PA12_RMP|PA11_RMP|Res.|MEM_MODE[1:0]|MEM_MODE[1:0]|
|0x00<br>|Reset value||||||||0|0|0|0|0|0|0|0|0|||||||||0|0|0|0|0||X|X|
|~~0x04 to~~<br>0x17|**Reserved**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x18<br>|**SYSCFG_CFGR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LOCUP_LOCK|
|0x18<br>|Reset value||||||||||||||||||||||||||||||||0|
|~~0x1C to~~<br>0x3B|**Reserved**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x3C<br>|**SYSCFG_CFGR3**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PINMUX7|PINMUX7|PINMUX6|PINMUX6|PINMUX5|PINMUX5|PINMUX4|PINMUX4|PINMUX3|PINMUX3|PINMUX2|PINMUX2|PINMUX1|PINMUX1|PINMUX0|PINMUX0|
|0x3C<br>|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|~~0x40 to~~<br>0x7F|**Reserved**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x80|**SYSCFG_ITLINE0**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|WWDG|
|0x80|Reset value|||||||||||||||||||||||||||||||||



RM0490 Rev 5 213/1027



216


**System configuration controller (SYSCFG)** **RM0490**


**Table 41. SYSCFG register map and reset values (continued)**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x84|**SYSCFG_ITLINE1**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PVM_VDDIO2_OUT|Res.|
|0x84|Reset value|||||||||||||||||||||||||||||||0||
|0x88|**SYSCFG_ITLINE2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RTC|Res.|
|0x88|Reset value|||||||||||||||||||||||||||||||0||
|0x8C|**SYSCFG_ITLINE3**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FLASH_ITF|Res.|
|0x8C|Reset value|||||||||||||||||||||||||||||||0||
|0x90|**SYSCFG_ITLINE4**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CRS|RCC|
|0x90|Reset value|||||||||||||||||||||||||||||||0|0|
|0x94|**SYSCFG_ITLINE5**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI1|EXTI0|
|0x94|Reset value|||||||||||||||||||||||||||||||0|0|
|0x98|**SYSCFG_ITLINE6**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI3|EXTI2|
|0x98|Reset value|||||||||||||||||||||||||||||||0|0|
|0x9C|**SYSCFG_ITLINE7**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI15|EXTI14|EXTI13|EXTI12|EXTI11|EXTI10|EXTI9|EXTI8|EXTI7|EXTI6|EXTI5|EXTI4|
|0x9C|Reset value|||||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|
|0xA0|**SYSCFG_ITLINE8**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USB|
|0xA0|Reset value||||||||||||||||||||||||||||||||0|
|0xA4|**SYSCFG_ITLINE9**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1_CH1|
|0xA4|Reset value||||||||||||||||||||||||||||||||0|
|0xA8|**SYSCFG_ITLINE10**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1_CH3|DMA1_CH2|
|0xA8|Reset value|||||||||||||||||||||||||||||||0|0|
|0xAC|**SYSCFG_ITLINE11**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1_CH7|DMA1_CH6|DMA1_CH5|DMA1_CH4|DMAMUX|
|0xAC|Reset value||||||||||||||||||||||||||||0|0|0|0|0|
|0xB0|**SYSCFG_ITLINE12**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADC|
|0xB0|Reset value||||||||||||||||||||||||||||||||0|
|0xB4|**SYSCFG_ITLINE13**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM1_BRK|TIM1_UPD|TIM1_TRG|TIM1_CCU|
|0xB4|Reset value|||||||||||||||||||||||||||||0|0|0|0|



214/1027 RM0490 Rev 5


**RM0490** **System configuration controller (SYSCFG)**


**Table 41. SYSCFG register map and reset values (continued)**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0xB8|**SYSCFG_ITLINE14**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM1_CC|
|0xB8|Reset value||||||||||||||||||||||||||||||||0|
|0xBC|**SYSCFG_ITLINE15**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM2|
|0xBC|Reset value||||||||||||||||||||||||||||||||0|
|0xC0<br>|**SYSCFG_ITLINE16**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM3|
|0xC0<br>|Reset value||||||||||||||||||||||||||||||||0|
|~~0xC4-~~<br>0xC8|**Reserved**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0xCC|**SYSCFG_ITLINE19**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM14|
|0xCC|Reset value||||||||||||||||||||||||||||||||0|
|0xD0|**SYSCFG_ITLINE20**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM15|
|0xD0|Reset value||||||||||||||||||||||||||||||||0|
|0xD4|**SYSCFG_ITLINE21**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM16|
|0xD4|Reset value||||||||||||||||||||||||||||||||0|
|0xD8|**SYSCFG_ITLINE22**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM17|
|0xD8|Reset value||||||||||||||||||||||||||||||||0|
|0xDC|**SYSCFG_ITLINE23**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|I2C1|
|0xDC|Reset value||||||||||||||||||||||||||||||||0|
|0xE0|**SYSCFG_ITLINE24**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|I2C2|
|0xE0|Reset value||||||||||||||||||||||||||||||||0|
|0xE4|**SYSCFG_ITLINE25**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SPI1|
|0xE4|Reset value||||||||||||||||||||||||||||||||0|
|0xE8|**SYSCFG_ITLINE26**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SPI2|
|0xE8|Reset value||||||||||||||||||||||||||||||||0|
|0xEC|**SYSCFG_ITLINE27**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USART1|
|0xEC|Reset value||||||||||||||||||||||||||||||||0|
|0xF0|**SYSCFG_ITLINE28**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USART2|
|0xF0|Reset value||||||||||||||||||||||||||||||||0|
|0xF4|**SYSCFG_ITLINE29**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USART4|USART3|
|0xF4|Reset value|||||||||||||||||||||||||||||||0|0|
|0xF8|**SYSCFG_ITLINE30**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FDCAN_IT0|
|0xF8|Reset value||||||||||||||||||||||||||||||||0|



RM0490 Rev 5 215/1027



216


**System configuration controller (SYSCFG)** **RM0490**


**Table 41. SYSCFG register map and reset values (continued)**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0xFC|**SYSCFG_ITLINE31**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FDCAN_IT1|
|0xFC|Reset value||||||||||||||||||||||||||||||||0|



Refer to _Section 2.2 on page 45_ for the register boundary addresses.


216/1027 RM0490 Rev 5


