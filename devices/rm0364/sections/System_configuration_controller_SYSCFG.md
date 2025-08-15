**RM0364** **System configuration controller (SYSCFG)**

# **10 System configuration controller (SYSCFG)**


The STM32F334xx devices feature a set of configuration registers. The main purposes of
the system configuration controller are the following:

      - Enabling/disabling I [2] C Fm+ on some I/O ports


      - Remapping some DMA trigger sources from TIM16, TIM17, TIM6, SPI1, I2C1,
DAC1_CH1,TIM7 and to different DMA channels


      - Remapping the memory located at the beginning of the code area


      - Managing the external interrupt line connection to the GPIOs


      - Remapping TIM1 ITR3 source


      - Remapping DAC1 and DAC2 triggers


      - Managing robustness feature


      - Configuring encoder mode


      - CCM SRAM pages protection

## **10.1 SYSCFG registers**


**10.1.1** **SYSCFG configuration register 1 (SYSCFG_CFGR1)**


This register is used for specific configurations on memory remap.


Two bits are used to configure the type of memory accessible at address 0x0000 0000.
These bits are used to select the physical remap by software and so, bypass the BOOT pin
and the option bit setting.


After reset these bits take the value selected by the BOOT pin (BOOT0) and by the option
bit (BOOT1).


Address offset: 0x00


Reset value: 0x7C00 000X (X is the memory mode selected by the BOOT0 pin and BOOT1
option bit)














|31 30 29 28 27 26|Col2|Col3|Col4|Col5|Col6|25|24|23 22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|FPU_IE[5..0]|FPU_IE[5..0]|FPU_IE[5..0]|FPU_IE[5..0]|FPU_IE[5..0]|FPU_IE[5..0]|Res|Res|ENCODER_<br>MODE|Res|I2C1_<br>FMP|I2C_<br>PB9_<br>FMP|I2C_<br>PB8_<br>FMP|I2C_<br>PB7_<br>FMP|I2C_<br>PB6_<br>FMP|
|rw|rw|rw|rw|rw|rw|||rw||rw|rw|rw|rw|rw|





















|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DAC2_<br>CH1_D<br>MA_R<br>MP|TIM7_<br>DAC2_<br>DMA_<br>RMP|TIM6_<br>DAC1_<br>DMA_<br>RMP|TIM17_<br>DMA_<br>RMP|TIM16_<br>DMA_<br>RMP|Res|Res|Res|DAC_<br>TRIG_<br>RMP|TIM1_<br>ITR3_<br>RMP|Res|Res|Res|Res|MEM_MODE|MEM_MODE|
|rw|rw|rw|rw|rw||||rw|rw|||||rw|rw|


RM0364 Rev 4 157/1124



169


**System configuration controller (SYSCFG)** **RM0364**


Bits 31:26 **FPU_IE[5..0]** : Floating Point Unit interrupts enable bits

FPU_IE[5]: Inexact interrupt enable

FPU_IE[4]: Input normal interrupt enable

FPU_IE[3]: Overflow interrupt enable

FPU_IE[2]: underflow interrupt enable

FPU_IE[1]: Divide-by-zero interrupt enable

FPU_IE[0]: Invalid operation interrupt enable


Bits 25:24 Reserved, must be kept at reset value.


Bits 23:22 **ENCODER_MODE:** Encoder mode

This bit is set and cleared by software.

00: No redirection.

01: TIM2 IC1 and TIM2 IC2 are connected to TIM15 IC1 and TIM15 IC2 respectively.

10: TIM3 IC1 and TIM3 IC2 are connected to TIM15 IC1 and TIM15 IC2

respectively .

11: Reserved.


Bit 21 Reserved, must be kept at reset value.


Bit 20 **I2C1_FMP:** I2C1 Fm+ driving capability activation

This bit is set and cleared by software. It enables the Fm+ on I2C1 pins selected through AF
selection bits.

0: Fm+ mode is not enabled on I2C1 pins selected through AF selection bits
1: Fm+ mode is enabled on I2C1 pins selected through AF selection bits.


Bits 19:16 **I2C_PBx_FMP** : Fm+ driving capability activation on the pad
These bits are set and cleared by software. Each bit enables I [2] C Fm+ mode for PB6, PB7,
PB8, and PB9 I/Os.

0: PBx pin operates in standard mode (Sm), x = 6..9
1: I [2] C Fm+ mode enabled on PBx pin, and the Speed control is bypassed.


Bit 15 **DAC2_CH1_DMA_RMP:** DAC2 channel1 DMA remap

This bit is set and cleared by software. It controls the remapping of DAC2 channel1 DMA
request.

0: No remap
1: Remap (DAC2_CH1 DMA requests mapped on DMA1 channel 5)


_Note: In STM32F334xx, this bit must be set._


Bit 14 **TIM7_DAC1_CH2_DMA_RMP:** TIM7 and DAC channel2 DMA remap

This bit is set and cleared by software. It controls the remapping of TIM7(UP) and DAC
channel2 DMA request.

0: No remap
1: Remap (TIM7_UP and DAC_CH2 DMA requests mapped on DMA1 channel 4)


_Note: In STM32F334xx, this bit must be set as there is no DMA2 in these products._


Bit 13 **TIM6_DAC1_CH1_DMA_RMP:** TIM6 and DAC channel1 DMA remap

This bit is set and cleared by software. It controls the remapping of TIM6 (UP) and DAC
channel1 DMA request.

0: No remap (TIM6_UP and DAC_CH1 DMA requests mapped on DMA2 channel 3)
1: Remap (TIM6_UP and DAC_CH1 DMA requests mapped on DMA1 channel 3)


_Note: In STM32F334xx, this bit must be set as there is no DMA2 in these products._


158/1124 RM0364 Rev 4


**RM0364** **System configuration controller (SYSCFG)**


Bit 12 **TIM17_DMA_RMP:** TIM17 DMA request remapping bit

This bit is set and cleared by software. It controls the remapping of TIM17 DMA request.

0: No remap (TIM17_CH1 and TIM17_UP DMA requests mapped on DMA1 channel 1)
1: Remap (TIM17_CH1 and TIM17_UP DMA requests mapped on DMA1 channel 7)


Bit 11 **TIM16_DMA_RMP:** TIM16 DMA request remapping bit

This bit is set and cleared by software. It controls the remapping of TIM16 DMA request.

0: No remap (TIM16_CH1 and TIM16_UP DMA requests mapped on DMA1 channel 3)
1: Remap (TIM16_CH1 and TIM16_UP DMA requests mapped on DMA1 channel 6)


Bits 10:8 Reserved, must be kept at reset value.


Bit 7 **DAC1_TRIG_RMP:** DAC trigger remap (when TSEL = 001) This bit is set and cleared by
software. It controls the mapping of the DAC trigger source.

0: No remap
1: Remap (DAC trigger is TIM3_TRGO)


Bit 6 **TIM1_ITR3_RMP:** Timer 1 ITR3 selection

This bit is set and cleared by software. It controls the mapping of TIM1 ITR3.

0: No remap
1: Remap (TIM1_ITR3 = TIM17_OC)


Bits 5:2 Reserved, must be kept at reset value.


Bits 1:0 **MEM_MODE:** Memory mapping selection bits

This bit is set and cleared by software. It controls the memory internal mapping at address
0x0000 0000. After reset these bits take on the memory mapping selected by BOOT0 pin and
BOOT1 option bit.

x0: Main Flash memory mapped at 0x0000 0000
01: System Flash memory mapped at 0x0000 0000
11: Embedded SRAM (on the D-Code bus) mapped at 0x0000 0000


**10.1.2** **SYSCFG CCM SRAM protection register (SYSCFG_RCR)**


The CCM SRAM has a size of 4 Kbytes, organized in 4 pages (1 Kbyte each). .


Each page can be write protected.


Address offset: 0x04


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res|Res|Res|Res|Res|Res|Res|Res|Res|PAGE<br>3_WP|PAGE<br>2_WP|PAGE<br>1_WP|PAGE<br>0_WP|
|||||||||||||rw|rw|rw|rw|



RM0364 Rev 4 159/1124



169


**System configuration controller (SYSCFG)** **RM0364**


Bits 31:4 Reserved, must be kept at reset value.


Bits 3:0 **PAGEx_WP** (x= 0 to 3): CCM SRAM page write protection bit)

These bits are set by software. They can be cleared only by system reset.

0: Write protection of pagex is disabled.
1: Write protection of pagex is enabled.


**10.1.3** **SYSCFG external interrupt configuration register 1**
**(SYSCFG_EXTICR1)**


Address offset: 0x08


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI3[3:0]|EXTI3[3:0]|EXTI3[3:0]|EXTI3[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI0[3:0]|EXTI0[3:0]|EXTI0[3:0]|EXTI0[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:12 **EXTI3[3:0]** : EXTI 3 configuration bits

These bits are written by software to select the source input for the EXTI3 external
interrupt.

x000: PA[3] pin
x001: PB[3] pin
x010: PC[3] pin
x011: PD[3] pin
x100: PE[3] pin
other configurations: reserved


160/1124 RM0364 Rev 4


**RM0364** **System configuration controller (SYSCFG)**


Bits 11:8 **EXTI2[3:0]** : EXTI 2 configuration bits

These bits are written by software to select the source input for the EXTI2 external
interrupt.

x000: PA[2] pin
x001: PB[2] pin
x010: PC[2] pin
x011: PD[2] pin
x100: PE[2] pin
x101: PF[2] pin
other configurations: reserved


Bits 7:4 **EXTI1[3:0]** : EXTI 1 configuration bits

These bits are written by software to select the source input for the EXTI1 external
interrupt.

x000: PA[1] pin
x001: PB[1] pin
x010: PC[1] pin
x011: PD[1] pin
x100: PE[1] pin
x101: PF[1] pin
other configurations: reserved


Bits 3:0 **EXTI0[3:0]** : EXTI 0 configuration bits

These bits are written by software to select the source input for the EXTI0 external
interrupt.

_Note:_ x000: PA[0] pin
x001: PB[0] pin
x010: PC[0] pin
x011: PD[0] pin
x100: PE[0] pin
x101: PF[0] pin
other configurations: reserved


**10.1.4** **SYSCFG external interrupt configuration register 2**
**(SYSCFG_EXTICR2)**


Address offset: 0x0C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI7[3:0]|EXTI7[3:0]|EXTI7[3:0]|EXTI7[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI4[3:0]|EXTI4[3:0]|EXTI4[3:0]|EXTI4[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



RM0364 Rev 4 161/1124



169


**System configuration controller (SYSCFG)** **RM0364**


Bits 31:16 Reserved, must be kept at reset value.


Bits 15:12 **EXTI7[3:0]** : EXTI 7 configuration bits

These bits are written by software to select the source input for the EXTI7 external
interrupt.

x000: PA[7] pin
x001: PB[7] pin
x010: PC[7] pin
x011: PD[7] pin
x100: PE[7] pin
Other configurations: reserved


Bits 11:8 **EXTI6[3:0]** : EXTI 6 configuration bits

These bits are written by software to select the source input for the EXTI6 external
interrupt.

x000: PA[6] pin
x001: PB[6] pin
x010: PC[6] pin
x011: PD[6] pin
x100: PE[6] pin
x101: PF[6] pin
Other configurations: reserved


Bits 7:4 **EXTI5[3:0]** : EXTI 5 configuration bits

These bits are written by software to select the source input for the EXTI5 external
interrupt.

x000: PA[5] pin
x001: PB[5] pin
x010: PC[5] pin
x011: PD[5] pin
x100: PE[5] pin
x101: PF[5] pin
Other configurations: reserved


Bits 3:0 **EXTI4[3:0]** : EXTI 4 configuration bits

These bits are written by software to select the source input for the EXTI4 external
interrupt.

x000: PA[4] pin
x001: PB[4] pin
x010: PC[4] pin
x011: PD[4] pin
x100: PE[4] pin
x101: PF[4] pin
Other configurations: reserved


_Note:_ _Some of the I/O pins mentioned in the above register may not be available on small_
_packages._


162/1124 RM0364 Rev 4


**RM0364** **System configuration controller (SYSCFG)**


**10.1.5** **SYSCFG external interrupt configuration register 3**
**(SYSCFG_EXTICR3)**


Address offset: 0x10


Reset value: 0x0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI11[3:0]|EXTI11[3:0]|EXTI11[3:0]|EXTI11[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI8[3:0]|EXTI8[3:0]|EXTI8[3:0]|EXTI8[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:12 **EXTI11[3:0]** : EXTI 11 configuration bits

These bits are written by software to select the source input for the EXTI11 external
interrupt.

x000: PA[11] pin
x001: PB[11] pin
x010: PC[11] pin
x011: PD[11] pin
x100: PE[11] pin
other configurations: reserved


Bits 11:8 **EXTI10[3:0]** : EXTI 10 configuration bits

These bits are written by software to select the source input for the EXTI10
external interrupt.

x000: PA[10] pin
x001: PB[10] pin
x010: PC[10] pin
x011:PD[10] pin
x100:PE[10] pin
x101:PF[10] pin
other configurations: reserved


Bits 7:4 **EXTI9[3:0]** : EXTI 9 configuration bits

These bits are written by software to select the source input for the EXTI9 external
interrupt.

x000: PA[9] pin
x001: PB[9] pin
x010: PC[9] pin
x011: PD[9] pin
x100: PE[9] pin
x101: PF[9] pin
other configurations: reserved


RM0364 Rev 4 163/1124



169


**System configuration controller (SYSCFG)** **RM0364**


Bits 3:0 **EXTI8[3:0]** : EXTI 8 configuration bits

These bits are written by software to select the source input for the EXTI8 external
interrupt.

x000: PA[8] pin
x001: PB[8] pin
x010: PC[8] pin
x011: PD[8] pin
x100: PE[8] pin
other configurations: reserved


_Note:_ _Some of the I/O pins mentioned in the above register may not be available on small_
_packages._


**10.1.6** **SYSCFG external interrupt configuration register 4**
**(SYSCFG_EXTICR4)**


Address offset: 0x14


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12|Col2|Col3|Col4|11 10 9 8|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI15[3:0]|EXTI15[3:0]|EXTI15[3:0]|EXTI15[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI12[3:0]|EXTI12[3:0]|EXTI12[3:0]|EXTI12[3:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:12 **EXTI15[3:0]** : EXTI15 configuration bits

These bits are written by software to select the source input for the EXTI15 external
interrupt.

x000: PA[15] pin
x001: PB[15] pin
x010: PC[15] pin
x011: PD[15] pin
x100: PE[15] pin
Other configurations: reserved


164/1124 RM0364 Rev 4


**RM0364** **System configuration controller (SYSCFG)**


Bits 11:8 **EXTI14[3:0]** : EXTI14 configuration bits

These bits are written by software to select the source input for the EXTI14 external
interrupt.

x000: PA[14] pin
x001: PB[14] pin
x010: PC[14] pin
x011: PD[14] pin
x100: PE[14] pin
Other configurations: reserved


Bits 7:4 **EXTI13[3:0]** : EXTI13 configuration bits

These bits are written by software to select the source input for the EXTI13 external
interrupt.

x000: PA[13] pin
x001: PB[13] pin
x010: PC[13] pin
x011: PD[13] pin
x100: PE[13] pin
Other configurations: reserved


Bits 3:0 **EXTI12[3:0]** : EXTI12 configuration bits

These bits are written by software to select the source input for the EXTI12 external
interrupt.

x000: PA[12] pin
x001: PB[12] pin
x010: PC[12] pin
x011: PD[12] pin
x100: PE[12] pin
Other configurations: reserved


_Note:_ _Some of the I/O pins mentioned in the above register may not be available on small_
_packages._


**10.1.7** **SYSCFG configuration register 2 (SYSCFG_CFGR2)**


Address offset: 0x18


System reset value: 0x0000


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||









|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res|Res|Res|Res|Res|Res|Res|SRAM_<br>PEF|Res|Res|Res|BYP_ADDR<br>_PAR|Res|PVD_<br>LOCK|SRAM_<br>PARITY<br>_LOCK|LOCKUP<br>_LOCK|
||||||||rc_w1||||rw||rw|rw|rw|


RM0364 Rev 4 165/1124



169


**System configuration controller (SYSCFG)** **RM0364**


Bits 31:9 Reserved, must be kept at reset value


Bit 8 **SRAM_PEF** : SRAM parity error flag

This bit is set by hardware when an SRAM parity error is detected. It is cleared by
software by writing ‘1’.

0: No SRAM parity error detected
1: SRAM parity error detected


Bits 7:5 Reserved, must be kept at reset value


Bit 4 **BYP_ADDR_PAR** : Bypass address bit 29 in parity calculation

This bit is set by software and cleared by a system reset. It is used to prevent an
unwanted parity error when the user writes a code in the RAM at address
0x2XXXXXXX (address in the address range 0x20000000-0x20002000) and then
executes the code from RAM at boot (RAM is remapped at address 0x00). In this
case, a read operation is performed from the range 0x00000000-0x00002000
resulting in a parity error (the parity on the address is different).

0: The ramload operation is performed taking into consideration bit 29 of the
address when the parity is calculated.
1: The ramload operation is performed without taking into consideration bit 29 of
the address when the parity is calculated.


Bit 3 Reserved, must be kept at reset value


Bit 2 **PVD_LOCK** : PVD lock enable bit

This bit is set by software and cleared by a system reset. It can be used to
enable and lock the PVD connection to TIM1/15/16/17 Break input and HRTIM1
SYSFLT, as well as the PVDE and PLS[2:0] in the PWR_CR register.
0: PVD interrupt disconnected from TIM1/15/16/17 and HRTIM1 SYSFLT Break
input. PVDE and PLS[2:0] bits can be programmed by the application.
1: PVD interrupt connected to TIM1/15/16/17 and HRTIM1 SYSFLT Break input,
PVDE and PLS[2:0] bits are read only.


Bit 1 **SRAM_PARITY_LOCK** : SRAM parity lock bit

This bit is set by software and cleared by a system reset. It can be used to
enable and lock the SRAM parity error signal connection to TIM1/15/16/17 Break
inputs and HRTIM1 SYSFLT.
0: SRAM parity error signal disconnected from TIM1/15/16/17 and HRTIM1
SYSFLT Break inputs
1: SRAM parity error signal connected to TIM1/15/16/17 and HRTIM1 SYSFLT
Break inputs


Bit 0 **LOCKUP_LOCK:** Cortex [®] -M4 LOCKUP (Hardfault) output enable bit

This bit is set by software and cleared by a system reset. It can be use to enable
and lock the connection of Cortex [®] -M4 LOCKUP (Hardfault) output to
TIM1/15/16/17 Break input.
0: Cortex [®] -M4 LOCKUP output disconnected from TIM1/15/16/17 Break inputs
and HRTIM1 SYSFLT.
1: Cortex [®] -M4 LOCKUP output connected to TIM1/15/16/17 and HRTIM1
SYSFLT Break inputs


166/1124 RM0364 Rev 4


**RM0364** **System configuration controller (SYSCFG)**


**10.1.8** **SYSCFG configuration register 3 (SYSCFG_CFGR3)**


Address offset: 0x50


System reset value: 0x0000 0200









|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|DAC1_<br>TRIG5_<br>RMP|DAC1_<br>TRIG3_<br>RMP|
|||||||||||||||rw|rw|


|15|14|13|12|11|10|9 8|Col8|7 6|Col10|5 4|Col12|3 2|Col14|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res|Res|Res|Res|Res|Res|ADC2_DMA_<br>RMP|ADC2_DMA_<br>RMP|I2C1_TX_DMA_<br>RMP|I2C1_TX_DMA_<br>RMP|I2C1_RX_DMA_<br>RMP|I2C1_RX_DMA_<br>RMP|SPI1_TX_DMA_<br>RMP|SPI1_TX_DMA_<br>RMP|SPI1_RX_DMA_<br>RMP|SPI1_RX_DMA_<br>RMP|
|||||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:18 Reserved, must be kept at reset value


Bit 17 **DAC1_TRIG5_RMP:** DAC1_CH1 / DAC1_CH2 Trigger remap

Set and cleared by software. This bit controls the mapping of DAC1 trigger

0: No remap

1: Remap (DAC trigger is HRTIM1_DAC1_TRIG2)


Bit 16 **DAC1_TRIG3_RMP** DAC1_CH1 / DAC1_CH2 Trigger remap

Set and cleared by software. This bit controls the mapping of DAC1 trigger

0: Remap (DAC trigger is TIM15_TRGO)

1: Remap (DAC trigger is HRTIM1_DAC1_TRIG1)


Bits 15:10 Reserved, must be kept at reset value


Bit 9 **ADC2_DMA_RMP[1]** : ADC2 DMA controller remapping bit

0: Reserved

1: ADC2 mapped on DMA1


Bit 8 **ADC2_DMA_RMP[0]** : ADC2 DMA channel remapping bit

0: ADC2 mapped on DMA1 channel 2
1: ADC2 mapped on DMA1 channel 4


Bits 7:6 **I2C1_TX_DMA_RMP:** I2C1_TX DMA remapping bit

This bit is set and cleared by software. It defines on which DMA1 channel I2C1_TX
is mapped.

00: I2C1_TX mapped on DMA1 CH6
01: I2C1_TX mapped on DMA1 CH2
10: I2C1_TX mapped on DMA1 CH4
11: I2C1_TX mapped on DMA1 CH6


RM0364 Rev 4 167/1124



169


**System configuration controller (SYSCFG)** **RM0364**


Bits 5:4 **I2C1_RX_DMA_RMP:** I2C1_RX DMA remapping bit

This bit is set and cleared by software. It defines on which DMA1 channel I2C1_RX
is mapped.

00: I2C1_RX mapped on DMA1 CH7
01: I2C1_RX mapped on DMA1 CH3
10: I2C1_RX mapped on DMA1 CH5
11: I2C1_RX mapped on DMA1 CH7


Bits 3:2 **SPI1_TX_DMA_RMP:** SPI1_TX DMA remapping bit

This bit is set and cleared by software. It defines on which DMA1 channel SPI1_TX
is mapped.

00: SPI1_TX mapped on DMA1 CH3
01: SPI1_TX mapped on DMA1 CH5
10: SPI1_TX mapped on DMA1 CH7
11: SPI1_TX mapped on DMA1 CH3


Bits 1:0 **SPI1_RX_DMA_RMP:** SPI1_RX DMA remapping bit

This bit is set and cleared by software. It defines on which DMA1 channel
SPI1_RXis mapped.

00: SPI1_RX mapped on DMA1 CH2
01: SPI1_RX mapped on DMA1 CH4
10: SPI1_RX mapped on DMA1 CH6
11: SPI1_RX mapped on DMA1 CH2


**10.1.9** **SYSCFG register map**


**Table 29. SYSCFG register map and reset values**































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**SYSCFG_CFGR1**|FPU_IE[5..0]|FPU_IE[5..0]|FPU_IE[5..0]|FPU_IE[5..0]|FPU_IE[5..0]|FPU_IE[5..0]|Res|Res|ENCODER_MODE [1:0]|ENCODER_MODE [1:0]|Res|I2C1_FMP|I2C_PB9_FMP|I2C_PB8_FMP|I2C_PB7_FMP|I2C_PB6_FMP|DAC2_CH1_DMA_RMP|TIM7_DAC2_DMA_RMP|TIM6_DAC1_DMA_RMP|TIM17_DMA_RMP|TIM16_DMA_RMP|Res|Res|Res|DAC_TRIG_RMP|TIM1_ITR3_RMP|Res|Res|Res|Res|MEM_MODE|MEM_MODE|
|0x00|Reset value|1|1|1|1|1|0|||0|0||0|0|0|0|0|0|0|0|0|0||||0|0|||||X|X|
|0x04|**SYSCFG_RCR**|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|PAGE[3:0]_<br>WP|PAGE[3:0]_<br>WP|PAGE[3:0]_<br>WP|PAGE[3:0]_<br>WP|
|0x04|Reset value|||||||||||||||||||||||||||||0|0|0|0|
|0x08|**SYSCFG_EXTICR1**|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|EXTI3[3:0]|EXTI3[3:0]|EXTI3[3:0]|EXTI3[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI2[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI1[3:0]|EXTI0[3:0]|EXTI0[3:0]|EXTI0[3:0]|EXTI0[3:0]|
|0x08|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0C|**SYSCFG_EXTICR2**|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|EXTI7[3:0]|EXTI7[3:0]|EXTI7[3:0]|EXTI7[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI6[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI5[3:0]|EXTI4[3:0]|EXTI4[3:0]|EXTI4[3:0]|EXTI4[3:0]|
|0x0C|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**SYSCFG_EXTICR3**|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|EXTI11[3:0]|EXTI11[3:0]|EXTI11[3:0]|EXTI11[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI10[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI9[3:0]|EXTI8[3:0]|EXTI8[3:0]|EXTI8[3:0]|EXTI8[3:0]|
|0x10|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x14|**SYSCFG_EXTICR4**|Res.|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|EXTI15[3:0]|EXTI15[3:0]|EXTI15[3:0]|EXTI15[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI14[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI13[3:0]|EXTI12[3:0]|EXTI12[3:0]|EXTI12[3:0]|EXTI12[3:0]|
|0x14|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


168/1124 RM0364 Rev 4


**RM0364** **System configuration controller (SYSCFG)**


**Table 29. SYSCFG register map and reset values (continued)**









|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x18|**SYSCFG_CFGR2**|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|SRAM_PEF|Res|Res|Res|BYP_ADDR_PAR|Res|PVD_LOCK|SRAM_PARITY_LOCK|LOCKUP_LOCK|
|0x18|Reset value||||||||||||||||||||||||0||||0||0|0|0|
|.<br>.<br>.|.<br>.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|.<br>.|
|0x50|**SYSCFG_CFGR3**|Res.|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|Res|DAC1_TRIG5_RMP|DAC1_TRIG3_RMP|Res.|Res|Res|Res|Res|Res|ADC2_DMA_RMP|ADC2_DMA_RMP|I2C1_TX_DMA_RMP|I2C1_TX_DMA_RMP|I2C1_RX_DMA_RMP|I2C1_RX_DMA_RMP|SPI1_TX_DMA_RMP|SPI1_TX_DMA_RMP|SPI1_RX_DMA_RMP|SPI1_RX_DMA_RMP|
|0x50|Reset value|||||||||||||||0|0|||||||1|0|0|0|0|0|0|0|0|0|


Refer to _Section 2.2 on page 47_ for the register boundary addresses.


RM0364 Rev 4 169/1124



169


