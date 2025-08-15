**System configuration controller (SYSCFG)** **RM0091**

# **9 System configuration controller (SYSCFG)**


The devices feature a set of configuration registers. The main purposes of the system
configuration controller are the following:

      - Enabling/disabling I [2] C Fast Mode Plus on some IO ports


      - Remapping some DMA trigger sources to different DMA channels


      - Remapping the memory located at the beginning of the code area


      - Pending interrupt status registers for each interrupt line on STM32F09x devices


      - Managing the external interrupt line connection to the GPIOs


      - Managing robustness feature

## **9.1 SYSCFG registers**


**9.1.1** **SYSCFG configuration register 1 (SYSCFG_CFGR1)**


This register is used for specific configurations of memory and DMA requests remap and to
control special I/O features.


Two bits are used to configure the type of memory accessible at address 0x0000 0000.
These bits are used to select the physical remap by software and so, bypass the hardware
BOOT selection.


After reset these bits take the value selected by the actual boot mode configuration.


Address offset: 0x00


Reset value: 0x0000 000X (X is the memory mode selected by the actual boot mode
configuration


































|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|TIM3_<br>DMA_<br>RMP|TIM2_<br>DMA_<br>RMP|TIM1_<br>DMA_<br>RMP|I2C1_<br>DMA_<br>RMP|USART3<br>_DMA_<br>RMP|USART2<br>_DMA_<br>RMP|SPI2_<br>DMA_<br>RMP|I2C_<br>PA10_<br>FMP|I2C_<br>PA9_<br>FMP|I2C2_<br>FMP|I2C1_<br>FMP|I2C_<br>PB9_<br>FMP|I2C_<br>PB8_<br>FMP|I2C_<br>PB7_<br>FMP|I2C_<br>PB6_<br>FMP|
||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|

























|15|14|13|12|11|10|9|8|7 6|5|4|3|2|1 0|Col15|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|TIM17<br>_DMA<br>_RMP<br>2|TIM16<br>_DMA<br>_RMP<br>2|TIM17_<br>DMA_<br>RMP|TIM16_<br>DMA_<br>RMP|USART1<br>_RX_<br>DMA_<br>RMP|USART1<br>_TX_<br>DMA_<br>RMP|ADC_<br>DMA_<br>RMP|IR_MOD<br>[1:0]|Res.|PA11_<br>PA12_<br>RMP|Res.|Res.|MEM_MODE<br>[1:0]|MEM_MODE<br>[1:0]|
||rw|rw|rw|rw|rw|rw|rw|rw||rw|||rw|rw|


Bit 31 Reserved, must be kept at reset value.


Bit 30 **TIM3_DMA_RMP:** TIM3 DMA request remapping bit. Available on STM32F07x devices only.

This bit is set and cleared by software. It controls the remapping of TIM3 DMA requests.

0: No remap (TIM3_CH1 and TIM3_TRIG DMA requests mapped on DMA channel 4)
1: Remap (TIM3_CH1 and TIM3_TRIG DMA requests mapped on DMA channel 6)


166/1017 RM0091 Rev 10


**RM0091** **System configuration controller (SYSCFG)**


Bit 29 **TIM2_DMA_RMP:** TIM2 DMA request remapping bit. Available on STM32F07x devices only.

This bit is set and cleared by software. It controls the remapping of TIM2 DMA requests.

0: No remap (TIM2_CH2 and TIM2_CH4 DMA requests mapped on DMA channel 3 and 4
respectively)
1: Remap (TIM2_CH2 and TIM2_CH4 DMA requests mapped on DMA channel 7)


Bit 28 **TIM1_DMA_RMP:** TIM1 DMA request remapping bit. Available on STM32F07x devices only.

This bit is set and cleared by software. It controls the remapping of TIM1 DMA requests.

0: No remap (TIM1_CH1, TIM1_CH2 and TIM1_CH3 DMA requests mapped on DMA
channel 2, 3 and 4 respectively)
1: Remap (TIM1_CH1, TIM1_CH2 and TIM1_CH3 DMA requests mapped on DMA channel
6)


Bit 27 **I2C1_DMA_RMP:** I2C1 DMA request remapping bit. Available on STM32F07x devices only.

This bit is set and cleared by software. It controls the remapping of I2C1 DMA requests.

0: No remap (I2C1_RX and I2C1_TX DMA requests mapped on DMA channel 3 and 2
respectively)
1: Remap (I2C1_RX and I2C1_TX DMA requests mapped on DMA channel 7 and 6
respectively)


Bit 26 **USART3_DMA_RMP:** USART3 DMA request remapping bit. Available on STM32F07x
devices only.

This bit is set and cleared by software. It controls the remapping of USART3 DMA requests.

0: (USART3_RX and USART3_TX DMA requests mapped on DMA channel 6 and 7
respectively)
1: Remap (USART3_RX and USART3_TX DMA requests mapped on DMA channel 3 and 2
respectively)


Bit 25 **USART2_DMA_RMP:** USART2 DMA request remapping bit. Available on STM32F07x
devices only.

This bit is set and cleared by software. It controls the remapping of USART2 DMA requests.

0: No remap (USART2_RX and USART2_TX DMA requests mapped on DMA channel 5 and
4 respectively)
1: Remap (USART2_RX and USART2_TX DMA requests mapped on DMA channel 6 and 7
respectively)


Bit 24 **SPI2_DMA_RMP:** SPI2 DMA request remapping bit. Available on STM32F07x devices only.

This bit is set and cleared by software. It controls the remapping of SPI2 DMA requests.

0: No remap (SPI2_RX and SPI2_TX DMA requests mapped on DMA channel 4 and 5
respectively)
1: Remap (SPI2_RX and SPI2_TX DMA requests mapped on DMA channel 6 and 7
respectively)


Bits 23:22 **I2C_PAx_FMP:** Fast Mode Plus (FM+) driving capability activation bits. Available on
STM32F03x, STM32F04x and STM32F09x devices only.
These bits are set and cleared by software. Each bit enables I [2] C FM+ mode for PA10 and PA9
I/Os.

0: PAx pin operates in standard mode.
1: I [2] C FM+ mode enabled on PAx pin and the Speed control is bypassed.


RM0091 Rev 10 167/1017



187


**System configuration controller (SYSCFG)** **RM0091**


Bit 21 **I2C2_FMP** : FM+ driving capability activation for I2C2. Available on STM32F07x and
STM32F09x devices only.

This bit is set and cleared by software. This bit is OR-ed with I2C_Pxx_FM+ bits.

0: FM+ mode is controlled by I2C_Pxx_FM+ bits only.
1: FM+ mode is enabled on all I2C2 pins selected through selection bits in GPIOx_AFR
registers. This is the only way to enable the FM+ mode for pads without a dedicated
I2C_Pxx_FM+ control bit.


Bit 20 **I2C1_FMP** : FM+ driving capability activation for I2C1. Not available on STM32F05x devices.

This bit is set and cleared by software. This bit is OR-ed with I2C_Pxx_FM+ bits.

0: FM+ mode is controlled by I2C_Pxx_FM+ bits only.
1: FM+ mode is enabled on all I2C1 pins selected through selection bits in GPIOx_AFR
registers. This is the only way to enable the FM+ mode for pads without a dedicated
I2C_Pxx_FM+ control bit.


Bits 19:16 **I2C_PBx_FMP** : Fast Mode Plus (FM+) driving capability activation bits.
These bits are set and cleared by software. Each bit enables I [2] C FM+ mode for PB6, PB7,
PB8, and PB9 I/Os.

0: PBx pin operates in standard mode.
1: I [2] C FM+ mode enabled on PBx pin and the Speed control is bypassed.


Bit 15 Reserved, must be kept at reset value.


Bit 14 **TIM17_DMA_RMP2** : TIM17 alternate DMA request remapping bit. Available on STM32F07x
devices only.

This bit is set and cleared by software. It controls the alternate remapping of TIM17 DMA
requests.

0: No alternate remap (TIM17 DMA requests mapped according to TIM17_DMA_RMP bit)
1: Alternate remap (TIM17_CH1 and TIM17_UP DMA requests mapped on DMA channel 7)


Bit 13 **TIM16_DMA_RMP2** : TIM16 alternate DMA request remapping bit. Available on STM32F07x
devices only.

This bit is set and cleared by software. It controls the alternate remapping of TIM16 DMA
requests.

0: No alternate remap (TIM16 DMA requests mapped according to TIM16_DMA_RMP bit)
1: Alternate remap (TIM16_CH1 and TIM16_UP DMA requests mapped on DMA channel 6)


Bit 12 **TIM17_DMA_RMP** : TIM17 DMA request remapping bit. Available on STM32F03x,
STM32F04x, STM32F05x and STM32F07x devices only.

This bit is set and cleared by software. It controls the remapping of TIM17 DMA requests.

0: No remap (TIM17_CH1 and TIM17_UP DMA requests mapped on DMA channel 1)
1: Remap (TIM17_CH1 and TIM17_UP DMA requests mapped on DMA channel 2)


Bit 11 **TIM16_DMA_RMP** : TIM16 DMA request remapping bit. Available on STM32F03x,
STM32F04x, STM32F05x and STM32F07x devices only **.**

This bit is set and cleared by software. It controls the remapping of TIM16 DMA requests.

0: No remap (TIM16_CH1 and TIM16_UP DMA requests mapped on DMA channel 3)
1: Remap (TIM16_CH1 and TIM16_UP DMA requests mapped on DMA channel 4)


Bit 10 **USART1_RX_DMA_RMP** : USART1_RX DMA request remapping bit. Available on
STM32F03x, STM32F04x, STM32F05x and STM32F07x devices only.

This bit is set and cleared by software. It controls the remapping of USART1_RX DMA
requests.

0: No remap (USART1_RX DMA request mapped on DMA channel 3)
1: Remap (USART1_RX DMA request mapped on DMA channel 5)


168/1017 RM0091 Rev 10


**RM0091** **System configuration controller (SYSCFG)**


Bit 9 **USART1_TX_DMA_RMP** : USART1_TX DMA request remapping bit. Available on
STM32F03x, STM32F04x, STM32F05x and STM32F07x devices only.

This bit is set and cleared by software. It bit controls the remapping of USART1_TX DMA
requests.

0: No remap (USART1_TX DMA request mapped on DMA channel 2)
1: Remap (USART1_TX DMA request mapped on DMA channel 4)


Bit 8 **ADC_DMA_RMP** : ADC DMA request remapping bit. Available on STM32F03x, STM32F04x,
STM32F05x and STM32F07x devices only.

This bit is set and cleared by software. It controls the remapping of ADC DMA requests.

0: No remap (ADC DMA request mapped on DMA channel 1)
1: Remap (ADC DMA request mapped on DMA channel 2)


Bits 7:6 **IR_MOD[1:0]:** IR Modulation Envelope signal selection. Available on STM32F09x devices
only.

Those bits allow to select the modulation envelope signal between TIM16, USART1 and
USART4:

00: TIM16 selected

01: USART1 selected

10: USART4 selected

11: Reserved


Bit 5 Reserved, must be kept at reset value.


Bit 4 **PA11_PA12_RMP** : PA11 and PA12 remapping bit for small packages (28 and 20 pins).
Available on STM32F04x devices only.

This bit is set and cleared by software. It controls the mapping of either PA9/10 or PA11/12 pin
pair on small pin-count packages.

0: No remap (pin pair PA9/10 mapped on the pins)
1: Remap (pin pair PA11/12 mapped instead of PA9/10)


Bits 3:2 Reserved, must be kept at reset value.


Bits 1:0 **MEM_MODE[1:0]:** Memory mapping selection bits

These bits are set and cleared by software. They control the memory internal mapping at
address 0x0000 0000. After reset these bits take on the value selected by the actual boot
mode configuration. Refer to _Section 2.5: Boot configuration_ for more details.

x0: Main Flash memory mapped at 0x0000 0000
01: System Flash memory mapped at 0x0000 0000
11: Embedded SRAM mapped at 0x0000 0000


**9.1.2** **SYSCFG external interrupt configuration register 1**
**(SYSCFG_EXTICR1)**


Address offset: 0x08


Reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI3[3:0]|EXTI3[3:0]|EXTI3[3:0]|EXTI3[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI0[3:0]|EXTI0[3:0]|EXTI0[3:0]|EXTI0[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



RM0091 Rev 10 169/1017



187


**System configuration controller (SYSCFG)** **RM0091**


Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **EXTIx[3:0]** : EXTI x configuration bits (x = 0 to 3)

These bits are written by software to select the source input for the EXTIx external interrupt.

x000: PA[x] pin
x001: PB[x] pin
x010: PC[x] pin
x011: PD[x] pin
x100: PE[x] pin
x101: PF[x] pin
other configurations: reserved


_Note:_ _Some of the I/O pins mentioned in the above register may not be available on small_
_packages._


**9.1.3** **SYSCFG external interrupt configuration register 2**
**(SYSCFG_EXTICR2)**


Address offset: 0x0C


Reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI7[3:0]|EXTI7[3:0]|EXTI7[3:0]|EXTI7[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI4[3:0]|EXTI4[3:0]|EXTI4[3:0]|EXTI4[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **EXTIx[3:0]** : EXTI x configuration bits (x = 4 to 7)

These bits are written by software to select the source input for the EXTIx external interrupt.

x000: PA[x] pin
x001: PB[x] pin
x010: PC[x] pin
x011: PD[x] pin
x100: PE[x] pin
x101: PF[x] pin
other configurations: reserved


_Note:_ _Some of the I/O pins mentioned in the above register may not be available on small_
_packages._


**9.1.4** **SYSCFG external interrupt configuration register 3**
**(SYSCFG_EXTICR3)**


Address offset: 0x10


Reset value: 0x0000


170/1017 RM0091 Rev 10


**RM0091** **System configuration controller (SYSCFG)**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI11[3:0]|EXTI11[3:0]|EXTI11[3:0]|EXTI11[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI8[3:0]|EXTI8[3:0]|EXTI8[3:0]|EXTI8[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **EXTIx[3:0]** : EXTI x configuration bits (x = 8 to 11)

These bits are written by software to select the source input for the EXTIx external interrupt.

x000: PA[x] pin
x001: PB[x] pin
x010: PC[x] pin
x011: PD[x] pin
x100: PE[x] pin
x101: PF[x] pin
other configurations: reserved


_Note:_ _Some of the I/O pins mentioned in the above register may not be available on small_
_packages._


**9.1.5** **SYSCFG external interrupt configuration register 4**
**(SYSCFG_EXTICR4)**


Address offset: 0x14


Reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI15[3:0]|EXTI15[3:0]|EXTI15[3:0]|EXTI15[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI12[3:0]|EXTI12[3:0]|EXTI12[3:0]|EXTI12[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **EXTIx[3:0]** : EXTI x configuration bits (x = 12 to 15)

These bits are written by software to select the source input for the EXTIx external interrupt.

x000: PA[x] pin
x001: PB[x] pin
x010: PC[x] pin
x011: PD[x] pin
x100: PE[x] pin
x101: PF[x] pin
other configurations: reserved


_Note:_ _Some of the I/O pins mentioned in the above register may not be available on small_
_packages._


RM0091 Rev 10 171/1017



187


**System configuration controller (SYSCFG)** **RM0091**


**9.1.6** **SYSCFG configuration register 2 (SYSCFG_CFGR2)**


Address offset: 0x18


System reset value: 0x0000


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||









|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SRAM_<br>PEF|Res.|Res.|Res.|Res.|Res.|PVD_<br>LOCK|SRAM_<br>PARITY<br>_LOCK|LOCKUP<br>_LOCK|
||||||||rc_w1||||||rw|rw|rw|


Bits 31:9 Reserved, must be kept at reset value


Bit 8 **SRAM_PEF** : SRAM parity error flag

This bit is set by hardware when an SRAM parity error is detected. It is cleared by software by
writing ‘1’.

0: No SRAM parity error detected
1: SRAM parity error detected


Bits 7:3 Reserved, must be kept at reset value


Bit 2 **PVD_LOCK** : PVD lock enable bit

This bit is set by software and cleared by a system reset. It can be used to enable and lock the
PVD connection to TIM1/15/16/17 Break input, as well as the PVDE and PLS[2:0] in the
PWR_CR register.

0: PVD interrupt disconnected from TIM1/15/16/17 Break input. PVDE and PLS[2:0] bits can
be programmed by the application.
1: PVD interrupt connected to TIM1/15/16/17 Break input, PVDE and PLS[2:0] bits are read
only.


Bit 1 **SRAM_PARITY_LOCK** : SRAM parity lock bit

This bit is set by software and cleared by a system reset. It can be used to enable and lock the
SRAM parity error signal connection to TIM1/15/16/17 Break input.

0: SRAM parity error disconnected from TIM1/15/16/17 Break input
1: SRAM parity error connected to TIM1/15/16/17 Break input


Bit 0 **LOCKUP_LOCK** : Cortex-M0 LOCKUP bit enable bit

This bit is set by software and cleared by a system reset. It can be use to enable and lock the
connection of Cortex-M0 LOCKUP (Hardfault) output to TIM1/15/16/17 Break input.

0: Cortex-M0 LOCKUP output disconnected from TIM1/15/16/17 Break input
1: Cortex-M0 LOCKUP output connected to TIM1/15/16/17 Break input


**9.1.7** **SYSCFG interrupt line 0 status register (SYSCFG_ITLINE0)**


A dedicated set of registers is implemented on STM32F09x to collect all pending interrupt
sources associated with each interrupt line into a single register. This allows users to check
by single read which peripheral requires service in case more than one source is associated
to the interrupt line.


All bits in those registers are read only, set by hardware when there is corresponding
interrupt request pending and cleared by resetting the interrupt source flags in the
peripheral registers.


172/1017 RM0091 Rev 10


**RM0091** **System configuration controller (SYSCFG)**


Address offset: 80h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|WWDG|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **WWDG** : Window watchdog interrupt pending flag


**9.1.8** **SYSCFG interrupt line 1 status register (SYSCFG_ITLINE1)**


Address offset: 84h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|VDDIO2|PVDOUT|
|||||||||||||||r|r|



Bits 31:2 Reserved (read as ‘0’)


Bit 1 **VDDIO2** : VDDIO2 supply monitoring interrupt request pending (EXTI line 31)


Bit 0 **PVDOUT** : PVD supply monitoring interrupt request pending (EXTI line 16). This bit is not
available on STM32F0x8 devices.


**9.1.9** **SYSCFG interrupt line 2 status register (SYSCFG_ITLINE2)**


Address offset: 88h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RTC_<br>ALRA|RTC_<br>TSTAMP|RTC_<br>WAKEUP|
||||||||||||||r|r|r|



Bits 31:3 Reserved (read as ‘0’)


Bit 2 **RTC_ALRA:** RTC Alarm interrupt request pending (EXTI line 17)


Bit 1 **RTC_TSTAMP** : RTC Tamper and TimeStamp interrupt request pending (EXTI line 19)


RM0091 Rev 10 173/1017



187


**System configuration controller (SYSCFG)** **RM0091**


Bit 0 **RTC_WAKEUP** : RTC Wake Up interrupt request pending (EXTI line 20)


**9.1.10** **SYSCFG interrupt line 3 status register (SYSCFG_ITLINE3)**


Address offset: 8Ch


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FLASH_<br>ITF|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **FLASH_ITF** : Flash interface interrupt request pending


**9.1.11** **SYSCFG interrupt line 4 status register (SYSCFG_ITLINE4)**


Address offset: 90h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CRS|RCC|
|||||||||||||||r|r|



Bits 31:2 Reserved (read as ‘0’)


Bit 1 **CRS** : Clock recovery system interrupt request pending


Bit 0 **RCC** : Reset and clock control interrupt request pending


**9.1.12** **SYSCFG interrupt line 5 status register (SYSCFG_ITLINE5)**


Address offset: 94h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI1|EXTI0|
|||||||||||||||r|r|



Bits 31:2 Reserved (read as ‘0’)


174/1017 RM0091 Rev 10


**RM0091** **System configuration controller (SYSCFG)**


Bit 1 **EXTI1** : EXTI line 1 interrupt request pending


Bit 0 **EXTI0** : EXTI line 0 interrupt request pending


**9.1.13** **SYSCFG interrupt line 6 status register (SYSCFG_ITLINE6)**


Address offset: 98h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI3|EXTI2|
|||||||||||||||r|r|



Bits 31:2 Reserved (read as ‘0’)


Bit 1 **EXTI3** : EXTI line 3 interrupt request pending


Bit 0 **EXTI2** : EXTI line 2 interrupt request pending


**9.1.14** **SYSCFG interrupt line 7 status register (SYSCFG_ITLINE7)**


Address offset: 9Ch


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|EXTI15|EXTI14|EXTI13|EXTI12|EXTI11|EXTI10|EXTI9|EXTI8|EXTI7|EXTI6|EXTI5|EXTI4|
|||||r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:10 Reserved (read as ‘0’)


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


RM0091 Rev 10 175/1017



187


**System configuration controller (SYSCFG)** **RM0091**


Bit 0 **EXTI4** : EXTI line 4 interrupt request pending


**9.1.15** **SYSCFG interrupt line 8 status register (SYSCFG_ITLINE8)**


Address offset: A0h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TCS_<br>EOA|TCS_<br>MCE|
|||||||||||||||r|r|



Bits 31:2 Reserved (read as ‘0’)


Bit 1 **TCS_EOA** : Touch sensing controller end of acquisition interrupt request pending


Bit 0 **TCS_MCE** : Touch sensing controller max count error interrupt request pending


**9.1.16** **SYSCFG interrupt line 9 status register (SYSCFG_ITLINE9)**


Address offset: A4h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1_<br>CH1|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **DMA1_CH1** : DMA1 channel 1 interrupt request pending


**9.1.17** **SYSCFG interrupt line 10 status register (SYSCFG_ITLINE10)**


Address offset: A8h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA2<br>_CH2|DMA2<br>_CH1|DMA1<br>_CH3|DMA1<br>_CH2|
|||||||||||||r|r|r|r|



176/1017 RM0091 Rev 10


**RM0091** **System configuration controller (SYSCFG)**


Bits 31:4 Reserved (read as ‘0’)


Bit 3 **DMA2_CH2** : DMA2 channel 2 interrupt request pending


Bit 2 **DMA2_CH1** : DMA2 channel 1 interrupt request pending


Bit 1 **DMA1_CH3** : DMA1 channel 3 interrupt request pending


Bit 0 **DMA1_CH2** : DMA1 channel 2 interrupt request pending


**9.1.18** **SYSCFG interrupt line 11 status register (SYSCFG_ITLINE11)**


Address offset: ACh


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA2<br>_CH5|DMA2<br>_CH4|DMA2<br>_CH3|DMA1<br>_CH7|DMA1<br>_CH6|DMA1<br>_CH5|DMA1<br>_CH4|
||||||||||r|r|r|r|r|r|r|



Bits 31:7 Reserved (read as ‘0’)


Bit 6 **DMA2_CH5** : DMA2 channel 5 interrupt request pending


Bit 5 **DMA2_CH4** : DMA2 channel 4 interrupt request pending


Bit 4 **DMA2_CH3** : DMA2 channel 3 interrupt request pending


Bit 3 **DMA1_CH7** : DMA1 channel 7 interrupt request pending


Bit 2 **DMA1_CH6** : DMA1 channel 6 interrupt request pending


Bit 1 **DMA1_CH5** : DMA1 channel 5 interrupt request pending


Bit 0 **DMA1_CH4** : DMA1 channel 4 interrupt request pending


**9.1.19** **SYSCFG interrupt line 12 status register (SYSCFG_ITLINE12)**


Address offset: B0h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|COMP2|COMP1|ADC|
||||||||||||||r|r|r|



Bits 31:3 Reserved (read as ‘0’)


Bit 2 **COMP2** : Comparator 2 interrupt request pending (EXTI line 22)


Bit 1 **COMP1** : Comparator 1 interrupt request pending (EXTI line 21)


RM0091 Rev 10 177/1017



187


**System configuration controller (SYSCFG)** **RM0091**


Bit 0 **ADC** : ADC interrupt request pending


**9.1.20** **SYSCFG interrupt line 13 status register (SYSCFG_ITLINE13)**


Address offset: B4h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM1_<br>BRK|TIM1_<br>UPD|TIM1_<br>TRG|TIM1_<br>CCU|
|||||||||||||r|r|r|r|



Bits 31:4 Reserved (read as ‘0’)


Bit 3 **TIM1_BRK** : Timer 1 break interrupt request pending


Bit 2 **TIM1_UPD** : Timer 1 update interrupt request pending


Bit 1 **TIM1_TRG** : Timer 1 trigger interrupt request pending


Bit 0 **TIM1_CCU** : Timer 1 commutation interrupt request pending


**9.1.21** **SYSCFG interrupt line 14 status register (SYSCFG_ITLINE14)**


Address offset: B8h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM1_<br>CC|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **TIM1_CC** : Timer 1 capture compare interrupt request pending


**9.1.22** **SYSCFG interrupt line 15 status register (SYSCFG_ITLINE15)**


Address offset: BCh


System reset value: 0x0000


178/1017 RM0091 Rev 10


**RM0091** **System configuration controller (SYSCFG)**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM2|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **TIM2** : Timer 2 interrupt request pending


**9.1.23** **SYSCFG interrupt line 16 status register (SYSCFG_ITLINE16)**


Address offset: C0h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM3|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **TIM3** : Timer 3 interrupt request pending


**9.1.24** **SYSCFG interrupt line 17 status register (SYSCFG_ITLINE17)**


Address offset: C4h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DAC|TIM6|
|||||||||||||||r|r|



Bits 31:1 Reserved (read as ‘0’)


Bit 1 **DAC** : DAC underrun interrupt request pending


Bit 0 **TIM6** : Timer 6 interrupt request pending


**9.1.25** **SYSCFG interrupt line 18 status register (SYSCFG_ITLINE18)**


Address offset: C8h


System reset value: 0x0000


RM0091 Rev 10 179/1017



187


**System configuration controller (SYSCFG)** **RM0091**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM7|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **TIM7** : Timer 7 interrupt request pending


**9.1.26** **SYSCFG interrupt line 19 status register (SYSCFG_ITLINE19)**


Address offset: CCh


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM14|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **TIM14** : Timer 14 interrupt request pending


**9.1.27** **SYSCFG interrupt line 20 status register (SYSCFG_ITLINE20)**


Address offset: D0h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM15|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **TIM15** : Timer 15 interrupt request pending


**9.1.28** **SYSCFG interrupt line 21 status register (SYSCFG_ITLINE21)**


Address offset: D4h


System reset value: 0x0000


180/1017 RM0091 Rev 10


**RM0091** **System configuration controller (SYSCFG)**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM16|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **TIM16** : Timer 16 interrupt request pending


**9.1.29** **SYSCFG interrupt line 22 status register (SYSCFG_ITLINE22)**


Address offset: D8h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM17|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **TIM17** : Timer 17 interrupt request pending


**9.1.30** **SYSCFG interrupt line 23 status register (SYSCFG_ITLINE23)**


Address offset: DCh


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|I2C1|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **I2C1** : I2C1 interrupt request pending, combined with EXTI line 23


**9.1.31** **SYSCFG interrupt line 24 status register (SYSCFG_ITLINE24)**


Address offset: E0h


System reset value: 0x0000


RM0091 Rev 10 181/1017



187


**System configuration controller (SYSCFG)** **RM0091**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|I2C2|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **I2C2** : I2C2 interrupt request pending


**9.1.32** **SYSCFG interrupt line 25 status register (SYSCFG_ITLINE25)**


Address offset: E4h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SPI1|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **SPI1** : SPI1 interrupt request pending


**9.1.33** **SYSCFG interrupt line 26 status register (SYSCFG_ITLINE26)**


Address offset: E8h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SPI2|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **SPI2** : SPI2 interrupt request pending


**9.1.34** **SYSCFG interrupt line 27 status register (SYSCFG_ITLINE27)**


Address offset: ECh


System reset value: 0x0000


182/1017 RM0091 Rev 10


**RM0091** **System configuration controller (SYSCFG)**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USART1|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **USART1** : USART1 interrupt request pending, combined with EXTI line 25


**9.1.35** **SYSCFG interrupt line 28 status register (SYSCFG_ITLINE28)**


Address offset: F0h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USART2|
||||||||||||||||r|



Bits 31:1 Reserved (read as ‘0’)


Bit 0 **USART2** : USART2 interrupt request pending, combined with EXTI line 26


**9.1.36** **SYSCFG interrupt line 29 status register (SYSCFG_ITLINE29)**


Address offset: F4h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USART8|USART7|USART6|USART5|USART4|USART3|
|||||||||||r|r|r|r|r|r|



Bits 31:6 Reserved (read as ‘0’)


Bit 5 **USART8** : USART8 interrupt request pending


Bit 4 **USART7** : USART7 interrupt request pending


Bit 3 **USART6** : USART6 interrupt request pending


Bit 2 **USART5** : USART5 interrupt request pending


Bit 1 **USART4** : USART4 interrupt request pending


Bit 0 **USART3** : USART3 interrupt request pending, combined with EXTI line 28.


RM0091 Rev 10 183/1017



187


**System configuration controller (SYSCFG)** **RM0091**


**9.1.37** **SYSCFG interrupt line 30 status register (SYSCFG_ITLINE30)**


Address offset: F8h


System reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CAN|CEC|
|||||||||||||||r|r|



Bits 31:2 Reserved (read as ‘0’)


Bit 1 **CAN** : CAN interrupt request pending


Bit 0 **CEC** : CEC interrupt request pending, combined with EXTI line 27


184/1017 RM0091 Rev 10


**RM0091** **System configuration controller (SYSCFG)**


**9.1.38** **SYSCFG register maps**


The following table gives the SYSCFG register map and the reset values.


**Table 26. SYSCFG register map and reset values**

























|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**SYSCFG_CFGR1**|Res.|TIM3_DMA_RMP|TIM2_DMA_RMP|TIM1_DMA_RMP|I2C1_DMA_RMP|USART3_DMA_RMP|USART2_DMA_RMP|SPI2_DMA_RMP|I2C_PA10_FMP|I2C_PA9_FMP|I2C2_FMP|I2C1_FMP|I2C_PB9_FMP|I2C_PB8_FMP|I2C_PB7_FMP|I2C_PB6_FMP|Res.|TIM17_DMA_RMP2|TIM16_DMA_RMP2|TIM17_DMA_RMP|TIM16_DMA_RMP|USART1_RX_DMA_RMP|USART1_TX_DMA_RMP|ADC_DMA_RMP|IR_MOD|IR_MOD|Res.|PA11_PA12_RMP|Res.|Res.|MEM_MODE[1:0]|MEM_MODE[1:0]|
|0x00|Reset value||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0||0|0|0|0|0|0|0|0|0||0|||X|X|
|0x08|**SYSCFG_EXTICR1**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI3[3:0]|EXTI3[3:0]|EXTI3[3:0]|EXTI3[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI0[3:0]|EXTI0[3:0]|EXTI0[3:0]|EXTI0[3:0]|
|0x08|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0C|**SYSCFG_EXTICR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI7[3:0]|EXTI7[3:0]|EXTI7[3:0]|EXTI7[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI4[3:0]|EXTI4[3:0]|EXTI4[3:0]|EXTI4[3:0]|
|0x0C|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**SYSCFG_EXTICR3**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI11[3:0]|EXTI11[3:0]|EXTI11[3:0]|EXTI11[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI8[3:0]|EXTI8[3:0]|EXTI8[3:0]|EXTI8[3:0]|
|0x10|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x14|**SYSCFG_EXTICR4**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI15[3:0]|EXTI15[3:0]|EXTI15[3:0]|EXTI15[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI12[3:0]|EXTI12[3:0]|EXTI12[3:0]|EXTI12[3:0]|
|0x14|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x18|**SYSCFG_CFGR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SRAM_PEF|Res.|Res.|Res.|Res.|Res.|PVD_LOCK|SRAM_PARITY_LOCK|LOCUP_LOCK|
|0x18|Reset value||||||||||||||||||||||||0||||||0|0|0|


**Table 27. SYSCFG register map and reset values for STM32F09x devices**



|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x1D to<br>0x7F|**Reserved**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x1D to<br>0x7F|Reset value|||||||||||||||||||||||||||||||||
|0x80|**SYSCFG_ITLINE0**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|WWDG|
|0x80|Reset value|||||||||||||||||||||||||||||||||
|0x84|**SYSCFG_ITLINE1**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|VDDIO2<br>|PVDOU|
|0x84|Reset value|||||||||||||||||||||||||||||||||
|0x88|**SYSCFG_ITLINE2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RTC_ALRA|RTC_TSTAMP|RTC_WAKEUP|
|0x88|Reset value|||||||||||||||||||||||||||||||||


RM0091 Rev 10 185/1017



187


**System configuration controller (SYSCFG)** **RM0091**


**Table 27. SYSCFG register map and reset values for STM32F09x devices (continued)**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x8C|**SYSCFG_ITLINE3**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FLASH_ITF|
|0x8C|Reset value|||||||||||||||||||||||||||||||||
|0x90|**SYSCFG_ITLINE4**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CRS|RCC|
|0x90|Reset value|||||||||||||||||||||||||||||||||
|0x94|**SYSCFG_ITLINE5**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI1|EXTI0|
|0x94|Reset value|||||||||||||||||||||||||||||||||
|0x98|**SYSCFG_ITLINE6**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI3|EXTI2|
|0x98|Reset value|||||||||||||||||||||||||||||||||
|0x9C|**SYSCFG_ITLINE7**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI15|EXTI14|EXTI13|EXTI12|EXTI11|EXTI10|EXTI9|EXTI8|EXTI7|EXTI6|EXTI5|EXTI4|
|0x9C|Reset value|||||||||||||||||||||||||||||||||
|0xA0|**SYSCFG_ITLINE8**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TCS_EOA|TCS_MCE|
|0xA0|Reset value|||||||||||||||||||||||||||||||||
|0xA4|**SYSCFG_ITLINE9**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA1_CH1|
|0xA4|Reset value|||||||||||||||||||||||||||||||||
|0xA8|**SYSCFG_ITLINE10**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA2_CH2|DMA2_CH1|DMA1_CH3|DMA1_CH2|
|0xA8|Reset value|||||||||||||||||||||||||||||||||
|0xAC|**SYSCFG_ITLINE11**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMA2_CH5|DMA2_CH4|DMA2_CH3|DMA1_CH7|DMA1_CH6|DMA1_CH5|DMA1_CH4|
|0xAC|Reset value|||||||||||||||||||||||||||||||||
|0xB0|**SYSCFG_ITLINE12**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|COMP2|COMP1|ADC|
|0xB0|Reset value|||||||||||||||||||||||||||||||||
|0xB4|**SYSCFG_ITLINE13**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM1_BRK|TIM1_UPD|TIM1_TRG|TIM1_CCU|
|0xB4|Reset value|||||||||||||||||||||||||||||||||
|0xB8|**SYSCFG_ITLINE14**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM1_CC|
|0xB8|Reset value|||||||||||||||||||||||||||||||||
|0xBC|**SYSCFG_ITLINE15**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM2|
|0xBC|Reset value|||||||||||||||||||||||||||||||||
|0xC0|**SYSCFG_ITLINE16**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM3|
|0xC0|Reset value|||||||||||||||||||||||||||||||||



186/1017 RM0091 Rev 10


**RM0091** **System configuration controller (SYSCFG)**


**Table 27. SYSCFG register map and reset values for STM32F09x devices (continued)**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0xC4|**SYSCFG_ITLINE17**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DAC|TIM6|
|0xC4|Reset value|||||||||||||||||||||||||||||||||
|0xC8|**SYSCFG_ITLINE18**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM7|
|0xC8|Reset value|||||||||||||||||||||||||||||||||
|0xCC|**SYSCFG_ITLINE19**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM14|
|0xCC|Reset value|||||||||||||||||||||||||||||||||
|0xD0|**SYSCFG_ITLINE20**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM15|
|0xD0|Reset value|||||||||||||||||||||||||||||||||
|0xD4|**SYSCFG_ITLINE21**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM16|
|0xD4|Reset value|||||||||||||||||||||||||||||||||
|0xD8|**SYSCFG_ITLINE22**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIM17|
|0xD8|Reset value|||||||||||||||||||||||||||||||||
|0xDC|**SYSCFG_ITLINE23**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|I2C1|
|0xDC|Reset value|||||||||||||||||||||||||||||||||
|0xE0|**SYSCFG_ITLINE24**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|I2C2|
|0xE0|Reset value|||||||||||||||||||||||||||||||||
|0xE4|**SYSCFG_ITLINE25**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SPI1|
|0xE4|Reset value|||||||||||||||||||||||||||||||||
|0xE8|**SYSCFG_ITLINE26**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SPI2|
|0xE8|Reset value|||||||||||||||||||||||||||||||||
|0xEC|**SYSCFG_ITLINE27**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USART1|
|0xEC|Reset value|||||||||||||||||||||||||||||||||
|0xF0|**SYSCFG_ITLINE28**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USART2|
|0xF0|Reset value|||||||||||||||||||||||||||||||||
|0xF4|**SYSCFG_ITLINE29**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|USART3|
|0xF4|Reset value|||||||||||||||||||||||||||||||||
|0xF8|**SYSCFG_ITLINE30**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CAN|CEC|
|0xF8|Reset value|||||||||||||||||||||||||||||||||



Refer to _Section 2.2 on page 46_ for the register boundary addresses.


RM0091 Rev 10 187/1017



187


