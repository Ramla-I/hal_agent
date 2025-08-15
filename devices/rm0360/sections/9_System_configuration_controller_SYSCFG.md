**System configuration controller (SYSCFG)** **RM0360**

# **9 System configuration controller (SYSCFG)**


The devices feature a set of configuration registers. The main purposes of the system
configuration controller are the following:

      - Enabling/disabling I [2] C Fast Mode Plus on some IO ports


      - Remapping some DMA trigger sources to different DMA channels


      - Remapping the memory located at the beginning of the code area


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


_Note:_ _For STM32F030xC devices, DMA remapping bits are replaced by more flexible mapping_
_configured through DMA_CSELR register. Refer to Section 10.6.7: DMA channel selection_
_register (DMA_CSELR) for more details._


















|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|USART3<br>_DMA_<br>RMP|Res.|Res.|I2C_<br>PA10_<br>FMP|I2C_<br>PA9_<br>FMP|I2C2_<br>FMP|I2C1_<br>FMP|I2C_<br>PB9_<br>FMP|I2C_<br>PB8_<br>FMP|I2C_<br>PB7_<br>FMP|I2C_<br>PB6_<br>FMP|
||||||rw|||rw|rw|rw|rw|rw|rw|rw|rw|

















|15|14|13|12|11|10|9|8|7 6|5|4|3|2|1 0|Col15|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res|Res|TIM17_<br>DMA_<br>RMP|TIM16_<br>DMA_<br>RMP|USART1<br>_RX_<br>DMA_<br>RMP|USART1<br>_TX_<br>DMA_<br>RMP|ADC_<br>DMA_<br>RMP|Res.|Res.|PA11_<br>PA12_<br>RMP|Res.|Res.|MEM_MODE<br>[1:0]|MEM_MODE<br>[1:0]|
||||rw|rw|rw|rw|rw|||rw|||rw|rw|


Bits 31:27 Reserved, must be kept at reset value.


Bit 26 **USART3_DMA_RMP:** USART3 DMA request remapping bit. Available on STM32F070xB
devices only.

This bit is set and cleared by software. It controls the remapping of USART3 DMA requests.

0: Disabled, need to enable remap before use.
1: Remap (USART3_RX and USART3_TX DMA requests mapped on DMA channel 3 and 2
respectively)


142/775 RM0360 Rev 5


**RM0360** **System configuration controller (SYSCFG)**


Bits 25:24 Reserved, must be kept at reset value.


Bits 23:22 **I2C_PAx_FMP:** Fast Mode Plus (FM+) driving capability activation bits. Available on
STM32F030x4, STM32F030x6, STM32F070x6 and STM32F030xC devices only.
These bits are set and cleared by software. Each bit enables I [2] C FM+ mode for PA10 and PA9
I/Os.

0: PAx pin operates in standard mode.
1: I [2] C FM+ mode enabled on PAx pin and the Speed control is bypassed.


Bit 21 **I2C2_FMP** : FM+ driving capability activation for I2C2. Available on STM32F070xB and
STM32F030xC devices only.

This bit is set and cleared by software. This bit is OR-ed with I2C_Pxx_FM+ bits.

0: FM+ mode is controlled by I2C_Pxx_FM+ bits only.
1: FM+ mode is enabled on all I2C2 pins selected through selection bits in GPIOx_AFR
registers. This is the only way to enable the FM+ mode for pads without a dedicated
I2C_Pxx_FM+ control bit.


Bit 20 **I2C1_FMP** : FM+ driving capability activation for I2C1. Not available on STM32F030x8 devices.

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


Bits 15:13 Reserved, must be kept at reset value.


Bit 12 **TIM17_DMA_RMP** : TIM17 DMA request remapping bit. Available on STM32F030x4,
STM32F030x6, STM32F070x6, STM32F030x8 and STM32F070xB devices only.

This bit is set and cleared by software. It controls the remapping of TIM17 DMA requests.

0: No remap (TIM17_CH1 and TIM17_UP DMA requests mapped on DMA channel 1)
1: Remap (TIM17_CH1 and TIM17_UP DMA requests mapped on DMA channel 2)


Bit 11 **TIM16_DMA_RMP** : TIM16 DMA request remapping bit. Available on STM32F030x4,
STM32F030x6, STM32F070x6, STM32F030x8 and STM32F070xB devices only **.**

This bit is set and cleared by software. It controls the remapping of TIM16 DMA requests.

0: No remap (TIM16_CH1 and TIM16_UP DMA requests mapped on DMA channel 3)
1: Remap (TIM16_CH1 and TIM16_UP DMA requests mapped on DMA channel 4)


Bit 10 **USART1_RX_DMA_RMP** : USART1_RX DMA request remapping bit. Available on
STM32F030x4, STM32F030x6, STM32F070x6, STM32F030x8 and STM32F070xB devices
only.

This bit is set and cleared by software. It controls the remapping of USART1_RX DMA
requests.

0: No remap (USART1_RX DMA request mapped on DMA channel 3)
1: Remap (USART1_RX DMA request mapped on DMA channel 5)


RM0360 Rev 5 143/775



148


**System configuration controller (SYSCFG)** **RM0360**


Bit 9 **USART1_TX_DMA_RMP** : USART1_TX DMA request remapping bit. . Available on
STM32F030x4,STM32F030x6, STM32F070x6, STM32F030x8 and STM32F070xB devices
only.

This bit is set and cleared by software. It bit controls the remapping of USART1_TX DMA
requests.

0: No remap (USART1_TX DMA request mapped on DMA channel 2)
1: Remap (USART1_TX DMA request mapped on DMA channel 4)


Bit 8 **ADC_DMA_RMP** : ADC DMA request remapping bit. Available on
STM32F030x4,STM32F030x6, STM32F070x6, STM32F030x8 and STM32F070xB devices
only.

This bit is set and cleared by software. It controls the remapping of ADC DMA requests.

0: No remap (ADC DMA request mapped on DMA channel 1)
1: Remap (ADC DMA request mapped on DMA channel 2)


Bits 7:5 Reserved, must be kept at reset value.


Bit 4 **PA11_PA12_RMP** : PA11 and PA12 remapping bit for small packages (28 and 20 pins).
Available on STM32F070x6 devices only.

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



144/775 RM0360 Rev 5


**RM0360** **System configuration controller (SYSCFG)**


Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **EXTIx[3:0]** : EXTI x configuration bits (x = 0 to 3)

These bits are written by software to select the source input for the EXTIx external interrupt.

x000: PA[x] pin
x001: PB[x] pin
x010: PC[x] pin
x011: PD[x] pin
x100: Reserved

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
x100: Reserved

x101: PF[x] pin
other configurations: reserved


_Note:_ _Some of the I/O pins mentioned in the above register may not be available on small_
_packages._


**9.1.4** **SYSCFG external interrupt configuration register 3**
**(SYSCFG_EXTICR3)**


Address offset: 0x10


Reset value: 0x0000


RM0360 Rev 5 145/775



148


**System configuration controller (SYSCFG)** **RM0360**

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

x100: Reserved

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

x100: Reserved

x101: PF[x] pin
other configurations: reserved


_Note:_ _Some of the I/O pins mentioned in the above register may not be available on small_
_packages._


146/775 RM0360 Rev 5


**RM0360** **System configuration controller (SYSCFG)**


**9.1.6** **SYSCFG configuration register 2 (SYSCFG_CFGR2)**


Address offset: 0x18


System reset value: 0x0000


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||







|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SRAM_<br>PEF|Res.|Res.|Res.|Res.|Res.|Res.|SRAM_<br>PARITY<br>_LOCK|LOCKUP<br>_LOCK|
||||||||rc_w1|||||||rw|rw|


Bits 31:9 Reserved, must be kept at reset value


Bit 8 **SRAM_PEF** : SRAM parity error flag

This bit is set by hardware when an SRAM parity error is detected. It is cleared by software by
writing ‘1’.

0: No SRAM parity error detected
1: SRAM parity error detected


Bits 7:2 Reserved, must be kept at reset value


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


RM0360 Rev 5 147/775



148


**System configuration controller (SYSCFG)** **RM0360**


**9.1.7** **SYSCFG register maps**


The following table gives the SYSCFG register map and the reset values.


**Table 24. SYSCFG register map and reset values**

























|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**SYSCFG_CFGR1**|Res.|Res.|Res.|Res.|Res.|USART3_DMA_RMP|Res.|Res.|I2C_PA10_FMP|I2C_PA9_FMP|I2C2_FMP|I2C1_FMP|I2C_PB9_FMP|I2C_PB8_FMP|I2C_PB7_FMP|I2C_PB6_FMP|Res.|Res.|Res.|TIM17_DMA_RMP|TIM16_DMA_RMP|USART1_RX_DMA_RMP|USART1_TX_DMA_RMP|ADC_DMA_RMP|Res.|Res.|Res.|PA11_PA12_RMP|Res.|Res.|MEM_MODE[1:0]|MEM_MODE[1:0]|
|0x00|Reset value||||||0|||0|0|0|0|0|0|0|0||||0|0|0|0|0||||0|||X|X|
|0x08|**SYSCFG_EXTICR1**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI3[3:0]|EXTI3[3:0]|EXTI3[3:0]|EXTI3[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI0[3:0]|EXTI0[3:0]|EXTI0[3:0]|EXTI0[3:0]|
|0x08|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0C|**SYSCFG_EXTICR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI7[3:0]|EXTI7[3:0]|EXTI7[3:0]|EXTI7[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI4[3:0]|EXTI4[3:0]|EXTI4[3:0]|EXTI4[3:0]|
|0x0C|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**SYSCFG_EXTICR3**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI11[3:0]|EXTI11[3:0]|EXTI11[3:0]|EXTI11[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI8[3:0]|EXTI8[3:0]|EXTI8[3:0]|EXTI8[3:0]|
|0x10|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x14|**SYSCFG_EXTICR4**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EXTI15[3:0]|EXTI15[3:0]|EXTI15[3:0]|EXTI15[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI12[3:0]|EXTI12[3:0]|EXTI12[3:0]|EXTI12[3:0]|
|0x14|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x18|**SYSCFG_CFGR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SRAM_PEF|Res.|Res.|Res.|Res.|Res.|Res.|SRAM_PARITY_LOCK|LOCUP_LOCK|
|0x18|Reset value||||||||||||||||||||||||0|||||||0|0|


Refer to _Section 2.2 on page 37_ for the register boundary addresses.


148/775 RM0360 Rev 5


