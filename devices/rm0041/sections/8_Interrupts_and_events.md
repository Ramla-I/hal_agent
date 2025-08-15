**Interrupts and events** **RM0041**

# **8 Interrupts and events**


**Low-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 16 and 32 Kbytes.


**Medium-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 64 and 128 Kbytes.


**High-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 256 and 512 Kbytes.


This section applies to the whole STM32F100xx family, unless otherwise specified.

## **8.1 Nested vectored interrupt controller (NVIC)**


**Features**


      - 60 maskable interrupt channels in high-density value line devices and 56 in low and
medium-density value line devices (not including the sixteen Cortex [®] -M3 interrupt
lines)


      - 16 programmable priority levels (4 bits of interrupt priority are used)


      - Low-latency exception and interrupt handling


      - Power management control


      - Implementation of System Control registers


The NVIC and the processor core interface are closely coupled, which enables low latency
interrupt processing and efficient processing of late arriving interrupts.


All interrupts including the core exceptions are managed by the NVIC. For more information
on exceptions and NVIC programming, refer to _STM32F100xx_ _Cortex_ _[®]_ -M3 _programming_
_manual_ (see _Related documents on page 1_ ).


**8.1.1** **SysTick calibration value register**


The SysTick calibration value is set to 9000, which gives a reference time base of 3 ms with
the SysTick clock set to 3 MHz (max HCLK/8).


**8.1.2** **Interrupt and exception vectors**


**Table 50. Vector table for STM32F100xx devices**




|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|-|-|-|-|Reserved|0x0000_0000|
|-|-3|fixed|Reset|Reset|0x0000_0004|



132/709 RM0041 Rev 6


**RM0041** **Interrupts and events**


**Table 50. Vector table for STM32F100xx devices (continued)**









|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|-|-2|fixed|NMI_Handler|Non maskable interrupt. The RCC<br>Clock Security System (CSS) is<br>linked to the NMI vector.|0x0000_0008|
|-|-1|fixed|HardFault_Handler|All class of fault|0x0000_000C|
|-|0|settable|MemManage_Handl<br>er|Memory management|0x0000_0010|
|-|1|settable|BusFault_Handler|Pre-fetch fault, memory access fault|0x0000_0014|
|-|2|settable|UsageFault_Handler|Undefined instruction or illegal state|0x0000_0018|
|-|-|-|-|Reserved|0x0000_001C -<br>0x0000_002B|
|-|3|settable|SVC_Handler|System service call via SWI<br>instruction|0x0000_002C|
|-|4|settable|DebugMon_Handler|Debug Monitor|0x0000_0030|
|-|-|-|-|Reserved|0x0000_0034|
|-|5|settable|PendSV_Handler|Pendable request for system<br>service|0x0000_0038|
|-|6|settable|SysTick_Handler|System tick timer|0x0000_003C|
|0|7|settable|WWDG|Window Watchdog interrupt|0x0000_0040|
|1|8|settable|PVD|PVD through EXTI Line detection<br>interrupt|0x0000_0044|
|2|9|settable|TAMPER_STAMP|Tamper and TimeStamp through<br>EXTI line interrupts|0x0000_0048|
|3|10|settable|RTC_WKUP|RTC Wakeup through EXTI line<br>interrupt|0x0000_004C|
|4|11|settable|FLASH|Flash global interrupt|0x0000_0050|
|5|12|settable|RCC|RCC global interrupt|0x0000_0054|
|6|13|settable|EXTI0|EXTI Line0 interrupt|0x0000_0058|
|7|14|settable|EXTI1|EXTI Line1 interrupt|0x0000_005C|
|8|15|settable|EXTI2|EXTI Line2 interrupt|0x0000_0060|
|9|16|settable|EXTI3|EXTI Line3 interrupt|0x0000_0064|
|10|17|settable|EXTI4|EXTI Line4 interrupt|0x0000_0068|
|11|18|settable|DMA1_Channel1|DMA1 Channel1 global interrupt|0x0000_006C|
|12|19|settable|DMA1_Channel2|DMA1 Channel2 global interrupt|0x0000_0070|


RM0041 Rev 6 133/709



143


**Interrupts and events** **RM0041**


**Table 50. Vector table for STM32F100xx devices (continued)**





|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|13|20|settable|DMA1_Channel3|DMA1 Channel3 global interrupt|0x0000_0074|
|14|21|settable|DMA1_Channel4|DMA1 Channel4 global interrupt|0x0000_0078|
|15|22|settable|DMA1_Channel5|DMA1 Channel5 global interrupt|0x0000_007C|
|16|23|settable|DMA1_Channel6|DMA1 Channel6 global interrupt|0x0000_0080|
|17|24|settable|DMA1_Channel7|DMA1 Channel7 global interrupt|0x0000_0084|
|18|25|settable|ADC1|ADC1 global interrupt|0x0000_0088|
|-|-|-|-|Reserved|0x0000_008C -<br>0x0000_0098|
|23|30|settable|EXTI9_5|EXTI Line[9:5] interrupts|0x0000_009C|
|24|31|settable|TIM1_BRK_TIM15|TIM1 Break and TIM15 global<br>interrupt|0x0000_00A0|
|25|32|settable|TIM1_UP_TIM16|TIM1 Update and TIM16 global<br>interrupts|0x0000_00A4|
|26|33|settable|TIM1_TRG_COM_T<br>IM17|TIM1 Trigger and Commutation and<br>TIM17 global interrupts|0x0000_00A8|
|27|34|settable|TIM1_CC|TIM1 Capture Compare interrupt|0x0000_00AC|
|28|35|settable|TIM2|TIM2 global interrupt|0x0000_00B0|
|29|36|settable|TIM3|TIM3 global interrupt|0x0000_00B4|
|30|37|settable|TIM4|TIM4 global interrupt|0x0000_00B8|
|31|38|settable|I2C1_EV|I2C1 event interrupt|0x0000_00BC|
|32|39|settable|I2C1_ER|I2C1 error interrupt|0x0000_00C0|
|33|40|settable|I2C2_EV|I2C2 event interrupt|0x0000_00C4|
|34|41|settable|I2C2_ER|I2C2 error interrupt|0x0000_00C8|
|35|42|settable|SPI1|SPI1 global interrupt|0x0000_00CC|
|36|43|settable|SPI2|SPI2 global interrupt|0x0000_00D0|
|37|44|settable|USART1|USART1 global interrupt|0x0000_00D4|
|38|45|settable|USART2|USART2 global interrupt|0x0000_00D8|
|39|46|settable|USART3|USART3 global interrupt|0x0000_00DC|
|40|47|settable|EXTI15_10|EXTI Line[15:10] interrupts|0x0000_00E0|
|41|48|settable|RTC_Alarm|RTC Alarms (A and B) through EXTI<br>line interrupt|0x0000_00E4|
|42|49|settable|CEC|CEC global interrupt|0x0000_00E8|


134/709 RM0041 Rev 6


**RM0041** **Interrupts and events**


**Table 50. Vector table for STM32F100xx devices (continued)**





|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|43|50|settable|TIM12|TIM12 global interrupt|0x0000_00EC|
|44|51|settable|TIM13|TIM13 global interrupt|0x0000_00F0|
|45|52|settable|TIM14|TIM14 global interrupt|0x0000_00F4|
|-|-|-|-|Reserved|0x0000_00F8 -<br>0x0000_00FC|
|48|55|settable|FSMC|FSMC global interrupt|0x0000_0100|
|-|-|-|-|Reserved|0x0000_0104|
|50|57|settable|TIM5|TIM5 global interrupt|0x0000_0108|
|51|58|settable|SPI3|SPI3 global interrupt|0x0000_010C|
|52|59|settable|UART4|UART4 global interrupt|0x0000_0110|
|53|60|settable|UART5|UART5 global interrupt|0x0000_0114|
|54|61|settable|TIM6_DAC|TIM6 global and DAC underrun<br>interrupts|0x0000_0118|
|55|62|settable|TIM7|TIM7 global interrupt|0x0000_011C|
|56|63|settable|DMA2_Channel1|DMA2 Channel1 global interrupt|0x0000_0120|
|57|64|settable|DMA2_Channel2|DMA2 Channel2 global interrupt|0x0000_0124|
|58|65|settable|DMA2_Channel3|DMA2 Channel3 global interrupt|0x0000_0128|
|59|66|settable|DMA2_Channel4_5|DMA2 Channel4 and DMA2<br>Channel5 global interrupts|0x0000_012C|
|60|67|settable|DMA2_Channel5(1)|DMA2 Channel5 global interrupt|0x0000_0130|


1. For High-density value line devices, the DMA2 Channel 5 is mapped at postion 60 only if the
MISC_REMAP bit in the AFIO_MAPR2 register is set and DMA2 Channel 2 is connected with DMA2
Channel 4 at position 59 when the MISC_REMAP bit in the AFIO_MAPR2 register is reset.


RM0041 Rev 6 135/709



143


**Interrupts and events** **RM0041**

## **8.2 External interrupt/event controller (EXTI)**


The external interrupt/event controller consists of up to 18 edge detectors for generating
event/interrupt requests. Each input line can be independently configured to select the type
(event or interrupt) and the corresponding trigger event (rising or falling or both). Each line
can also masked independently. A pending register maintains the status line of the interrupt
requests


**8.2.1** **Main features**


The EXTI controller main features are the following:


      - Independent trigger and mask on each interrupt/event line


      - Dedicated status bit for each interrupt line


      - Generation of up to 18 software event/interrupt requests


      - Detection of external signal with pulse width lower than APB2 clock period. Refer to the
electrical characteristics section of the datasheet for details on this parameter.


**8.2.2** **Block diagram**


The block diagram is shown in _Figure 18_ .


**Figure 18. External interrupt/event controller block diagram**





































136/709 RM0041 Rev 6




**RM0041** **Interrupts and events**


**8.2.3** **Wakeup event management**


The STM32F100xx is able to handle external or internal events in order to wake up the core
(WFE). The wakeup event can be generated either by:


      - enabling an interrupt in the peripheral control register but not in the NVIC, and enabling
the SEVONPEND bit in the Cortex [®] -M3 System Control register. When the MCU
resumes from WFE, the peripheral interrupt pending bit and the peripheral NVIC IRQ
channel pending bit (in the NVIC interrupt clear pending register) have to be cleared.


      - or configuring an external or internal EXTI line in event mode. When the CPU resumes
from WFE, it is not necessary to clear the peripheral interrupt pending bit or the NVIC
IRQ channel pending bit as the pending bit corresponding to the event line is not set.


To use an external line as a wakeup event, refer to _Section 8.2.4: Functional description_ .


**8.2.4** **Functional description**


To generate the interrupt, the interrupt line should be configured and enabled. This is done
by programming the two trigger registers with the desired edge detection and by enabling
the interrupt request by writing a ‘1’ to the corresponding bit in the interrupt mask register.
When the selected edge occurs on the external interrupt line, an interrupt request is
generated. The pending bit corresponding to the interrupt line is also set. This request is
reset by writing a ‘1’ in the pending register.


To generate the event, the event line should be configured and enabled. This is done by
programming the two trigger registers with the desired edge detection and by enabling the
event request by writing a ‘1’ to the corresponding bit in the event mask register. When the
selected edge occurs on the event line, an event pulse is generated. The pending bit
corresponding to the event line is not set


An interrupt/event request can also be generated by software by writing a ‘1’ in the software
interrupt/event register.


**Hardware interrupt selection**


To configure the 18 lines as interrupt sources, use the following procedure:


      - Configure the mask bits of the 18 Interrupt lines (EXTI_IMR)


      - Configure the Trigger Selection bits of the Interrupt lines (EXTI_RTSR and
EXTI_FTSR)


      - Configure the enable and mask bits that control the NVIC IRQ channel mapped to the
External Interrupt Controller (EXTI) so that an interrupt coming from one of the 18 lines
can be correctly acknowledged.


**Hardware event selection**


To configure the 18 lines as event sources, use the following procedure:


      - Configure the mask bits of the 18 Event lines (EXTI_EMR)


      - Configure the Trigger Selection bits of the Event lines (EXTI_RTSR and EXTI_FTSR)


RM0041 Rev 6 137/709



143


**Interrupts and events** **RM0041**


**Software interrupt/event selection**


The 18 lines can be configured as software interrupt/event lines. The following is the
procedure to generate a software interrupt.


      - Configure the mask bits of the 18 Interrupt/Event lines (EXTI_IMR, EXTI_EMR)


      - Set the required bit of the software interrupt register (EXTI_SWIER)


**8.2.5** **External interrupt/event line mapping**


The 112 GPIOs are connected to the 16 external interrupt/event lines in the following

manner:


138/709 RM0041 Rev 6


**RM0041** **Interrupts and events**


**Figure 19. External interrupt/event GPIO mapping**


1. To configure the AFIO_EXTICRx for the mapping of external interrupt/event lines onto GPIOs, the AFIO
clock should first be enabled. Refer to _Section 6.3.7: APB2 peripheral clock enable register_
_(RCC_APB2ENR)_ .


The two other EXTI lines are connected as follows:


      - EXTI line 16 is connected to the PVD output


      - EXTI line 17 is connected to the RTC Alarm event


RM0041 Rev 6 139/709



143


**Interrupts and events** **RM0041**

## **8.3 EXTI registers**


Refer to _Section 1.1 on page 32_ for a list of abbreviations used in register descriptions.


The peripheral registers have to be accessed by words (32-bit).


**8.3.1** **Interrupt mask register (EXTI_IMR)**


Address offset: 0x00

Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22 21 20 19 18|17|16|
|---|---|---|
|Reserved|MR17|MR16|
|Reserved|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MR15|MR14|MR13|MR12|MR11|MR10|MR9|MR8|MR7|MR6|MR5|MR4|MR3|MR2|MR1|MR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:18 Reserved, must be kept at reset value (0).


Bits 17:0 **MRx:** Interrupt Mask on line x

0: Interrupt request from Line x is masked
1: Interrupt request from Line x is not masked


**8.3.2** **Event mask register (EXTI_EMR)**


Address offset: 0x04

Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22 21 20 19 18|17|16|
|---|---|---|
|Reserved|MR17|MR16|
|Reserved|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MR15|MR14|MR13|MR12|MR11|MR10|MR9|MR8|MR7|MR6|MR5|MR4|MR3|MR2|MR1|MR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:18 Reserved, must be kept at reset value (0).


Bits 17:0 **MRx:** Event mask on line x

0: Event request from Line x is masked
1: Event request from Line x is not masked


140/709 RM0041 Rev 6


**RM0041** **Interrupts and events**


**8.3.3** **Rising trigger selection register (EXTI_RTSR)**


Address offset: 0x08

Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22 21 20 19 18|17|16|
|---|---|---|
|Reserved|TR17|TR16|
|Reserved|rw|rw|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:18 Reserved, must be kept at reset value (0).


Bits 17:0 **TRx:** Rising trigger event configuration bit of line x

0: Rising trigger disabled (for Event and Interrupt) for input line
1: Rising trigger enabled (for Event and Interrupt) for input line


_Note:_ _The external wakeup lines are edge triggered, no glitches must be generated on these lines._
_If a rising edge on external interrupt line occurs during writing of EXTI_RTSR register, the_
_pending bit will not be set._


_Rising and Falling edge triggers can be set for the same interrupt line. In this configuration,_
_both generate a trigger condition._


**8.3.4** **Falling trigger selection register (EXTI_FTSR)**


Address offset: 0x0C

Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22 21 20 19 18|17|16|
|---|---|---|
|Reserved|TR17|TR16|
|Reserved|rw|rw|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:18 Reserved, must be kept at reset value (0).


Bits 17:0 **TRx:** Falling trigger event configuration bit of line x

0: Falling trigger disabled (for Event and Interrupt) for input line
1: Falling trigger enabled (for Event and Interrupt) for input line


_Note:_ _The external wakeup lines are edge triggered, no glitches must be generated on these lines._
_If a falling edge on external interrupt line occurs during writing of EXTI_FTSR register, the_
_pending bit will not be set._


_Rising and Falling edge triggers can be set for the same interrupt line. In this configuration,_
_both generate a trigger condition._


RM0041 Rev 6 141/709



143


**Interrupts and events** **RM0041**


**8.3.5** **Software interrupt event register (EXTI_SWIER)**


Address offset: 0x10

Reset value: 0x0000 0000






|31 30 29 28 27 26 25 24 23 22 21 20 19 18|17|16|
|---|---|---|
|Reserved|SWIER<br>17|SWIER<br>16|
|Reserved|rw|rw|



|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|SWIER<br>15<br>SWIER<br>14<br>SWIER<br>13<br>SWIER<br>12<br>SWIER<br>11<br>SWIER<br>10<br>SWIER<br>9<br>SWIER<br>8<br>SWIER<br>7<br>SWIER<br>6<br>SWIER<br>5<br>SWIER<br>4<br>SWIER<br>3<br>SWIER<br>2<br>SWIER<br>1<br>SWIER<br>0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:18 Reserved, must be kept at reset value (0).


Bits 17:0 **SWIERx:** Software interrupt on line x

If the interrupt is enabled on this line in the EXTI_IMR, writing a '1' to this bit when it is at '0'
sets the corresponding pending bit in EXTI_PR resulting in an interrupt request generation.
This bit is cleared by clearing the corresponding bit of EXTI_PR (by writing a 1 into the bit)


**8.3.6** **Pending register (EXTI_PR)**


Address offset: 0x14

Reset value: undefined

|31 30 29 28 27 26 25 24 23 22 21 20 19 18|17|16|
|---|---|---|
|Reserved|PR17|PR16|
|Reserved|rc_w1|rc_w1|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|
|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|



Bits 31:18 Reserved, must be kept at reset value (0).


Bits 17:0 **PRx:** Pending bit

0: No trigger request occurred
1: selected trigger request occurred
This bit is set when the selected edge event arrives on the external interrupt line. This bit is
cleared by writing a ‘1’ into the bit.


142/709 RM0041 Rev 6


**RM0041** **Interrupts and events**


**8.3.7** **EXTI register map**


The following table gives the EXTI register map and the reset values.



**Table 51. External interrupt/event controller register map and reset values**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|EXTI_IMR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|MR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|
|0x04|EXTI_EMR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|EMR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|
|0x08|EXTI_RTSR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|RTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|
|0x0C|EXTI_FTSR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|FTSR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|
|0x10|EXTI_SWIER<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|SWIER[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|
|0x14|EXTI_PR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|PR[17:0]<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0<br>0|



Refer to _Table 1 on page 37_ and _Table 2 on page 38_ for the register boundary addresses.


RM0041 Rev 6 143/709



143


