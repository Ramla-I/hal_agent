**RM0364** **Interrupts and events**

# **12 Interrupts and events**

## **12.1 Nested vectored interrupt controller (NVIC)**


**12.1.1** **NVIC main features**


      - 73 maskable interrupt channels (not including the sixteen Cortex-M4 with FPU interrupt
lines)


      - 16 programmable priority levels (4 bits of interrupt priority are used)


      - Low-latency exception and interrupt handling


      - Power management control


      - Implementation of System Control Registers


The NVIC and the processor core interface are closely coupled, which enables low latency
interrupt processing and efficient processing of late arriving interrupts.


All interrupts including the core exceptions are managed by the NVIC. For more information
on exceptions and NVIC programming, refer to the PM0214 programming manual for
Cortex-M4 products.


**12.1.2** **SysTick calibration value register**


The SysTick calibration value is set to 9000, which gives a reference time base of 1 ms with
the SysTick clock set to 9 MHz (max f HCLK /8).


**12.1.3** **Interrupt and exception vectors**


_Table 35_ is the vector table for STM32F334xx devices.


**Table 35. STM32F334xx vector table**



|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|-|-|-|-|Reserved|0x0000 0000|
|-|-3|fixed|Reset|Reset|0x0000 0004|
|-|-2|fixed|NMI|Non maskable interrupt. The RCC Clock<br>Security System (CSS) is linked to the NMI<br>vector.|0x0000 0008|
|-|-1|fixed|HardFault|All class of fault|0x0000 000C|
|-|0|settable|MemManage|Memory management|0x0000 0010|
|-|1|settable|BusFault|Pre-fetch fault, memory access fault|0x0000 0014|
|-|2|settable|UsageFault|Undefined instruction or illegal state|0x0000 0018|
|-|-|-|-|Reserved|0x0000 001C -<br>0x0000 0028|
|-|3|settable|SVCall|System service call via SWI instruction|0x0000 002C|


RM0364 Rev 4 193/1124



210


**Interrupts and events** **RM0364**


**Table 35. STM32F334xx vector table (continued)**





|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|-|5|settable|PendSV|Pendable request for system service|0x0000 0038|
|-|6|settable|SysTick|System tick timer|0x0000 003C|
|0|7|settable|WWDG|Window Watchdog interrupt|0x0000 0040|
|1|8|settable|PVD|PVD through EXTI line 16 detection interrupt|0x0000 0044|
|2|9|settable|TAMPER_STAMP|Tamper and TimeStamp interrupts<br>through the EXTI line 19|0x0000 0048|
|3|10|settable|RTC_WKUP|RTC wakeup timer interrupts through the<br>EXTI line 20|0x0000 004C|
|4|11|settable|FLASH|Flash global interrupt|0x0000 0050|
|5|12|settable|RCC|RCC global interrupt|0x0000 0054|
|6|13|settable|EXTI0|EXTI Line0 interrupt|0x0000 0058|
|7|14|settable|EXTI1|EXTI Line1 interrupt|0x0000 005C|
|8|15|settable|EXTI2_TS|EXTI Line2 and Touch sensing interrupts|0x0000 0060|
|9|16|settable|EXTI3|EXTI Line3|0x0000 0064|
|10|17|settable|EXTI4|EXTI Line4|0x0000 0068|
|11|18|settable|DMA1_Channel1|DMA1 channel 1 interrupt|0x0000 006C|
|12|19|settable|DMA1_Channel2|DMA1 channel 2 interrupt|0x0000 0070|
|13|20|settable|DMA1_Channel3|DMA1 channel 3 interrupt|0x0000 0074|
|14|21|settable|DMA1_Channel4|DMA1 channel 4 interrupt|0x0000 0078|
|15|22|settable|DMA1_Channel5|DMA1 channel 5 interrupt|0x0000 007C|
|16|23|settable|DMA1_Channel6|DMA1 channel 6 interrupt|0x0000 0080|
|17|24|settable|DMA1_Channel7|DMA1 channel 7 interrupt|0x0000 0084|
|18|25|settable|ADC1_2|ADC1 and ADC2 global interrupt|0x0000 0088|
|19|26|settable|CAN_TX|CAN_TX interrupts|0x0000 008C|
|20|27|settable|CAN_RX0|CAN_RX0 interrupts|0x0000 0090|
|21|28|settable|CAN_RX1|CAN_RX1 interrupt|0x0000 0094|
|22|29|settable|CAN_SCE|CAN_SCE interrupt|0x0000 0098|
|23|30|settable|EXTI9_5|EXTI Line[9:5] interrupts|0x0000 009C|
|24|31|settable|TIM1_BRK/TIM15|TIM1 Break/TIM15 global interrupts|0x0000 00A0|
|25|32|settable|TIM1_UP/TIM16|TIM1 Update/TIM16 global interrupts|0x0000 00A4|
|26|33|settable|TIM1_TRG_COM<br>/TIM17|TIM1 trigger and commutation/TIM17<br>interrupts|0x0000 00A8|
|27|34|settable|TIM1_CC|TIM1 capture compare interrupt|0x0000 00AC|
|28|35|settable|TIM2|TIM2 global interrupt|0x0000 00B0|


194/1124 RM0364 Rev 4


**RM0364** **Interrupts and events**


**Table 35. STM32F334xx vector table (continued)**



|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|29|36|settable|TIM3|TIM3 global interrupt|0x0000 00B4|
|30|37|-|Reserved|Reserved|0x0000 00B8|
|31|38|settable|I2C1_EV|I2C1 event interrupt & EXTI Line23 interrupt|0x0000 00BC|
|32|39|settable|I2C1_ER|I2C1 error interrupt|0x0000 00C0|
|33|40|-|Reserved|Reserved|0x0000 00C4|
|34|41|-|Reserved|Reserved|0x0000 00C8|
|35|42|-|SPI1|SPI1 global interrupt|0x0000 00CC|
|36|43|-|Reserved|Reserved|0x0000 00D0|
|37|44|settable|USART1|USART1 global interrupt & EXTI Line 25|0x0000 00D4|
|38|45|settable|USART2|USART2 global interrupt & EXTI Line 26|0x0000 00D8|
|39|46|settable|USART3|USART3 global interrupt & EXTI Line 28|0x0000 00DC|
|40|47|settable|EXTI15_10|EXTI Line[15:10] interrupts|0x0000 00E0|
|41|48|settable|RTC_Alarm|RTC alarm interrupt|0x0000 00E4|
|42|49|-|Reserved|Reserved|0x0000 00E8|
|43|50|-|Reserved|Reserved|0x0000 00EC|
|44|51|-|Reserved|Reserved|0x0000 00F0|
|45|52|-|Reserved|Reserved|0x0000 00F4|
|46|53|-|Reserved|Reserved|0x0000 00F8|
|47|54|-|Reserved|Reserved|0x0000 00FC|
|48|55|-|Reserved|Reserved|0x0000 0100|
|49|56|-|Reserved|Reserved|0x0000 0104|
|50|57|-|Reserved|Reserved|0x0000 0108|
|51|58|-|Reserved|Reserved|0x0000 010C|
|52|59|-|Reserved|Reserved|0x0000 0110|
|53|60|-|Reserved|Reserved|0x0000 0114|
|54|61|settable|TIM6_DAC1|TIM6 global and DAC1 underrun interrupts|0x0000 0118|
|55|62|settable|TIM7_DAC2|TIM7 global and DAC2 underrun interrupt|0x0000 011C|
|56|63|-|Reserved|Reserved|0x0000 0120|
|57|64|-|Reserved|Reserved|0x0000 0124|
|58|65|-|Reserved|Reserved|0x0000 0128|
|59|66|-|Reserved|Reserved|0x0000 012C|
|60|67|-|Reserved|Reserved|0x0000 0130|
|61|68|-|Reserved|Reserved|0x0000 0134|


RM0364 Rev 4 195/1124



210


**Interrupts and events** **RM0364**


**Table 35. STM32F334xx vector table (continued)**





|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|62|69|-|Reserved|Reserved|0x0000 0138|
|63|70|-|Reserved|Reserved|0x0000 013C|
|64|71|settable|COMP2|COMP2 interrupt combined with EXTI Lines<br>22 interrupt.|0x0000 0140|
|65|72|settable|COMP4_6|COMP4 & COMP6 interrupts combined with<br>EXTI Lines 30 and 32 interrupts respectively.|0x0000 0144|
|66|73|-|Reserved|Reserved|0x0000 0148|
|67|74|-|HRTIM_Master_IRQn|HRTIM master timer interrupt|0x0000 014C|
|68|75|-|HRTIM_TIMA_IRQn|HRTIM timer A interrupt|0x0000 0150|
|69|76|-|HRTIM_TIMB_IRQn|HRTIM timer B interrupt|0x0000 0154|
|70|77|-|HRTIM_TIMC_IRQn|HRTIM timer C interrupt|0x0000 0158|
|71|78|-|HRTIM_TIMD_IRQn|HRTIM timer D interrupt|0x0000 015C|
|72|79|-|HRTIM_TIME_IRQn|HRTIM timer E interrupt|0x0000 0160|
|73|80|-|HRTIM_TIM_FLT_IRQn|HRTIM fault interrupt|0x0000 0164|
|74|81|-|Reserved|Reserved|0x0000 0168|
|75|82|-|Reserved|Reserved|0x0000 016C|
|76|83|-|Reserved|Reserved|0x0000 0170|
|77|84|-|Reserved|Reserved|0x0000 0174|
|78|85|-|Reserved|Reserved|0x0000 0178|
|79|86|-|Reserved|Reserved|0x0000 017C|
|80|87|-|Reserved|Reserved|0x0000 0180|
|81|88|settable|FPU|Floating point interrupt|0x0000 0184|

## **12.2 Extended interrupts and events controller (EXTI)**

The extended interrupts and events controller (EXTI) manages the external and internal
asynchronous events/interrupts and generates the event request to the CPU/Interrupt
Controller and a wake-up request to the Power Manager.


The EXTI allows the management of up to 36 external/internal event line (28 external event
lines and 8 internal event lines).


The active edge of each external interrupt line can be chosen independently, whilst for
internal interrupt the active edge is always the rising one. An interrupt could be left pending:
in case of an external one, a status register is instantiated and indicates the source of the
interrupt; an event is always a simple pulse and it’s used for triggering the core wake-up. For
internal interrupts, the pending status is assured by the generating peripheral, so no need


196/1124 RM0364 Rev 4


**RM0364** **Interrupts and events**


for a specific flag. Each input line can be masked independently for interrupt or event
generation, in addition the internal lines are sampled only in STOP mode. This controller
allows also to emulate the (only) external events by software, multiplexed with the
corresponding hardware event line, by writing to a dedicated register.


**12.2.1** **Main features**


The EXTI main features are the following:


      - support generation of up to 36 event/interrupt requests


      - Independent configuration of each line as an external or an internal event requests


      - Independent mask on each event/interrupt line


      - Automatic disable of internal lines when system is not in STOP mode


      - Independent trigger for external event/interrupt line


      - Dedicated status bit for external interrupt line


      - Emulation for all the external event requests.


**12.2.2** **Block diagram**


The extended interrupt/event block diagram is shown in the following figure.


**Figure 21. External interrupt/event block diagram**







































RM0364 Rev 4 197/1124



210


**Interrupts and events** **RM0364**


**12.2.3** **Wakeup event management**


STM32F334xx devices are able to handle external or internal events in order to wake up the
core (WFE). The wakeup event can be generated either by:


      - enabling an interrupt in the peripheral control register but not in the NVIC, and enabling
the SEVONPEND bit in the Cortex-M4 System Control register. When the MCU
resumes from WFE, the EXTI peripheral interrupt pending bit and the peripheral NVIC
IRQ channel pending bit (in the NVIC interrupt clear pending register) have to be
cleared.


      - or by configuring an external or internal EXTI line in event mode. When the CPU
resumes from WFE, it is not necessary to clear the peripheral interrupt pending bit or
the NVIC IRQ channel pending bit as the pending bit corresponding to the event line is
not set.


**12.2.4** **Asynchronous Internal Interrupts**


Some communication peripherals (UART, I2C) are able to generate events when the system
is in run mode and also when the system is in stop mode allowing to wake up the system
from stop mode.


To accomplish this, the peripheral is asked to generate both a synchronized (to the system
clock, e.g. APB clock) and an asynchronous version of the event.


**12.2.5** **Functional description**


For the external interrupt lines, to generate the interrupt, the interrupt line should be
configured and enabled. This is done by programming the two trigger registers with the
desired edge detection and by enabling the interrupt request by writing a ‘1’ to the
corresponding bit in the interrupt mask register. When the selected edge occurs on the
external interrupt line, an interrupt request is generated. The pending bit corresponding to
the interrupt line is also set. This request is reset by writing a 1 in the pending register.


For the internal interrupt lines, the active edge is always the rising edge, the interrupt is
enabled by default in the interrupt mask register and there is no corresponding pending bit
in the pending register.


To generate the event, the event line should be configured and enabled. This is done by
programming the two trigger registers with the desired edge detection and by enabling the
event request by writing a ‘1’ to the corresponding bit in the event mask register. When the
selected edge occurs on the event line, an event pulse is generated. The pending bit
corresponding to the event line is not set.


For the external lines, an interrupt/event request can also be generated by software by
writing a 1 in the software interrupt/event register.


_Note:_ _The interrupts or events associated to the internal lines can be triggered only when the_
_system is in STOP mode. If the system is still running, no interrupt/event is generated._


198/1124 RM0364 Rev 4


**RM0364** **Interrupts and events**


**Hardware interrupt selection**


To configure a line as interrupt source, use the following procedure:


      - Configure the corresponding mask bit in the EXTI_IMR register.


      - Configure the Trigger Selection bits of the Interrupt line (EXTI_RTSR and EXTI_FTSR)


      - Configure the enable and mask bits that control the NVIC IRQ channel mapped to the
EXTI so that an interrupt coming from one of the EXTI line can be correctly
acknowledged.


**Hardware event selection**


To configure a line as event source, use the following procedure:


      - Configure the corresponding mask bit in the EXTI_EMR register.


      - Configure the Trigger Selection bits of the Event line (EXTI_RTSR and EXTI_FTSR)


**Software interrupt/event selection**


Any of the external lines can be configured as software interrupt/event lines. The following is
the procedure to generate a software interrupt.


      - Configure the corresponding mask bit (EXTI_IMR, EXTI_EMR)


      - Set the required bit of the software interrupt register (EXTI_SWIER)


RM0364 Rev 4 199/1124



210


**Interrupts and events** **RM0364**


**12.2.6** **External and internal interrupt/event line mapping**


36 interrupt/event lines are available: 8 lines are internal (including the reserved ones); the
remaining 28 lines are external.


The GPIOs are connected to the 16 external interrupt/event lines in the following manner:


**Figure 22. External interrupt/event GPIO mapping**















200/1124 RM0364 Rev 4






**RM0364** **Interrupts and events**


The remaining lines are connected as follows:


      - EXTI line 16 is connected to the PVD output


      - EXTI line 17 is connected to the RTC Alarm event


      - EXTI line 18 is reserved


      - EXTI line 19 is connected to RTC tamper and Timestamps


      - EXTI line 20 is connected to RTC wakeup timer


      - EXTI line 21 is reserved


      - EXTI line 22 is connected to Comparator 2 output


      - EXTI line 23 is connected to I2C1 wakeup


      - EXTI line 24 is reserved


      - EXTI line 25 is connected to USART1 wakeup


      - EXTI line 26 is reserved


      - EXTI line 27 is reserved


      - EXTI line 28 is reserved


      - EXTI line 29 is reserved


      - EXTI line 30 is connected to Comparator 4 output


      - EXTI line 31 is reserved


      - EXTI line 32 is connected to Comparator 6 output


_Note:_ _EXTI lines 23 and 25 are internal._

## **12.3 EXTI registers**


Refer to _Section 1.2_ for a list of abbreviations used in register descriptions.


The peripheral registers have to be accessed by words (32-bit).


**12.3.1** **Interrupt mask register (EXTI_IMR1)**


Address offset: 0x00


Reset value: 0xBFA4 0000 (See note below)

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|MR30|Res.|Res.|Res.|Res.|MR25|Res.|MR23|MR22|Res.|MR20|MR19|Res.|MR17|MR16|
||rw|||||rw||rw|rw||rw|rw||rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MR15|MR14|MR13|MR12|MR11|MR10|MR9|MR8|MR7|MR6|MR5|MR4|MR3|MR2|MR1|MR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 31 Reserved, must be kept at reset value.


Bit 30 **MRx:** Interrupt Mask on external/internal line x (x = 30)

0: Interrupt request from Line x is masked
1: Interrupt request from Line x is not masked


Bits 29:26 Reserved, must be kept at reset value.


RM0364 Rev 4 201/1124



210


**Interrupts and events** **RM0364**


Bit 24 Reserved, must be kept at reset value.


Bit 21 Reserved, must be kept at reset value.


Bit 18 Reserved, must be kept at reset value.


_Note:_ _The reset value for the internal lines (23 and 25) and reserved lines is set to '1'._


**12.3.2** **Event mask register (EXTI_EMR1)**


Address offset: 0x04


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|MR30|Res.|Res.|Res.|Res.|MR25|Res.|MR23|MR22|Res.|MR20|MR19|Res.|MR17|MR16|
||rw|||||rw||rw|rw||rw|rw||rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MR15|MR14|MR13|MR12|MR11|MR10|MR9|MR8|MR7|MR6|MR5|MR4|MR3|MR2|MR1|MR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 31 Reserved, must be kept at reset value.


Bits 29:28 Reserved, must be kept at reset value.


Bit 27 Reserved, must be kept at reset value.


Bit 26 Reserved, must be kept at reset value.


Bit 24 Reserved, must be kept at reset value.


Bit 21 Reserved, must be kept at reset value.


Bit 18 Reserved, must be kept at reset value.


**12.3.3** **Rising trigger selection register (EXTI_RTSR1)**


Address offset: 0x08


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|TR30|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TR22|Res.|TR20|TR19|Res.|TR17|TR16|
||rw||||||||rw||rw|rw||rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TR15|TR14|TR13|TR12|TR11|TR10|TR9|TR8|TR7|TR6|TR5|TR4|TR3|TR2|TR1|TR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 31 Reserved, must be kept at reset value.


Bit 30 **TRx:** Rising trigger event configuration bit of line x (x = 31 to 29)

0: Rising trigger disabled (for Event and Interrupt) for input line
1: Rising trigger enabled (for Event and Interrupt) for input line.


Bits 29:23 Reserved, must be kept at reset value.


202/1124 RM0364 Rev 4


**RM0364** **Interrupts and events**


Bit 22 **TRx:** Rising trigger event configuration bit of line x (x = 22)

0: Rising trigger disabled (for Event and Interrupt) for input line
1: Rising trigger enabled (for Event and Interrupt) for input line.


Bit 21 Reserved, must be kept at reset value.


Bits 20:19 **TRx:** Rising trigger event configuration bit of line x (x = 20 to 19)

0: Rising trigger disabled (for Event and Interrupt) for input line
1: Rising trigger enabled (for Event and Interrupt) for input line.


Bit 18 Reserved, must be kept at reset value.


Bits 17:0 **TRx:** Rising trigger event configuration bit of line x (x = 17 to 0)

0: Rising trigger disabled (for Event and Interrupt) for input line
1: Rising trigger enabled (for Event and Interrupt) for input line.


_Note:_ _The external wakeup lines are edge-triggered. No glitches must be generated on these_
_lines. If a rising edge on an external interrupt line occurs during a write operation in the_
_EXTI_RTSR register, the pending bit is not set._


_Rising and falling edge triggers can be set for the same interrupt line. In this case, both_
_generate a trigger condition._


**12.3.4** **Falling trigger selection register (EXTI_FTSR1)**


Address offset: 0x0C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|TR30|Res|Res.|Res.|Res.|Res.|Res.|Res.|TR22|Res.|TR20|TR19|Res.|TR17|TR16|
||rw||||||||rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TR15|TR14|TR13|TR12|TR11|TR10|TR9|TR8|TR7|TR6|TR5|TR4|TR3|TR2|TR1|TR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 31 Reserved, must be kept at reset value.


Bit 30 **TRx:** Falling trigger event configuration bit of line x (x = 30)

0: Falling trigger disabled (for Event and Interrupt) for input line
1: Falling trigger enabled (for Event and Interrupt) for input line.


Bits 29:23 Reserved, must be kept at reset value.


Bit 22 **TRx:** Falling trigger event configuration bit of line x (x = 22)

0: Falling trigger disabled (for Event and Interrupt) for input line
1: Falling trigger enabled (for Event and Interrupt) for input line.


Bit 21 Reserved, must be kept at reset value.


RM0364 Rev 4 203/1124



210


**Interrupts and events** **RM0364**


Bits 20:19 **TRx:** Falling trigger event configuration bit of line x (x = 20 to 19)

0: Falling trigger disabled (for Event and Interrupt) for input line
1: Falling trigger enabled (for Event and Interrupt) for input line.


Bit 18 Reserved, must be kept at reset value.


Bits 17:0 **TRx:** Falling trigger event configuration bit of line x (x = 17 to 0)

0: Falling trigger disabled (for Event and Interrupt) for input line
1: Falling trigger enabled (for Event and Interrupt) for input line.


_Note:_ _The external wakeup lines are edge-triggered. No glitches must be generated on these_
_lines. If a falling edge on an external interrupt line occurs during a write operation to the_
_EXTI_FTSR register, the pending bit is not set._


_Rising and falling edge triggers can be set for the same interrupt line. In this case, both_
_generate a trigger condition._


**12.3.5** **Software interrupt event register (EXTI_SWIER1)**


Address offset: 0x10


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|SWIER<br>30|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SWIER<br>22|Res.|SWIER<br>20|SWIER<br>19|Res.|SWIER<br>17|SWIER<br>16|
|rw|rw||||||||rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SWIER<br>15|SWIER<br>14|SWIER<br>13|SWIER<br>12|SWIER<br>11|SWIER<br>10|SWIER<br>9|SWIER<br>8|SWIER<br>7|SWIER<br>6|SWIER<br>5|SWIER<br>4|SWIER<br>3|SWIER<br>2|SWIER<br>1|SWIER<br>0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 31 Reserved, must be kept at reset value.


Bit 30 **SWIERx:** Software interrupt on line x (x = 30)

If the interrupt is enabled on this line in the EXTI_IMR, writing a '1' to this bit when
it is at '0' sets the corresponding pending bit in EXTI_PR resulting in an interrupt
request generation.

This bit is cleared by clearing the corresponding bit in the EXTI_PR register (by
writing a ‘1’ into the bit).


Bits 29:23 Reserved, must be kept at reset value.


Bit 22 **SWIERx:** Software interrupt on line x (x = 22)

If the interrupt is enabled on this line in the EXTI_IMR, writing a '1' to this bit when
it is at '0' sets the corresponding pending bit in EXTI_PR resulting in an interrupt
request generation.

This bit is cleared by clearing the corresponding bit of EXTI_PR (by writing a ‘1’
into the bit).


204/1124 RM0364 Rev 4


**RM0364** **Interrupts and events**


Bit 21 Reserved, must be kept at reset value.


Bits 20:19 **SWIERx:** Software interrupt on line x (x = 20 to 19)

If the interrupt is enabled on this line in the EXTI_IMR, writing a '1' to this bit when
it is at '0' sets the corresponding pending bit in EXTI_PR resulting in an interrupt
request generation.

This bit is cleared by clearing the corresponding bit of EXTI_PR (by writing a ‘1’
into the bit).


Bit 18 Reserved, must be kept at reset value.


**12.3.6** **Pending register (EXTI_PR1)**


Address offset: 0x14


Reset value: undefined

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|PR30|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PR22|Res.|PR20|PR19|Res.|PR17|PR16|
||rc_w1||||||||rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PR15|PR14|PR13|PR12|PR11|PR10|PR9|PR8|PR7|PR6|PR5|PR4|PR3|PR2|PR1|PR0|
|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|



Bit 31 Reserved, must be kept at reset value.


Bit 30 **PRx:** Pending bit on line x (x = 30)

0: No trigger request occurred
1: Selected trigger request occurred

This bit is set when the selected edge event arrives on the external interrupt line.
This bit is cleared by writing a ‘1’ to the bit.


Bits 29:23 Reserved, must be kept at reset value.


Bit 22 **PRx:** Pending bit on line x (x = 22)

0: No trigger request occurred
1: Selected trigger request occurred

This bit is set when the selected edge event arrives on the external interrupt line.
This bit is cleared by writing a ‘1’ to the bit.


Bit 21 Reserved, must be kept at reset value.


Bits 20:19 **PRx:** Pending bit on line x (x = 20 to 19)

0: No trigger request occurred
1: Selected trigger request occurred
This bit is set when the selected edge event arrives on the external interrupt line.
This bit is cleared by writing a ‘1’ to the bit.


Bit 18 Reserved, must be kept at reset value.


Bits 17:0 **PRx:** Pending bit on line x (x = 17 to 0)

0: No trigger request occurred
1: Selected trigger request occurred
This bit is set when the selected edge event arrives on the external interrupt line.
This bit is cleared by writing a ‘1’ to the bit.


RM0364 Rev 4 205/1124



210


**Interrupts and events** **RM0364**


**12.3.7** **Interrupt mask register (EXTI_IMR2)**


Address offset: 0x20


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|MR32|
||||||||||||||||rw|



Bits 31:1 Reserved, must be kept at reset value


Bit 0 **MRx:** Interrupt mask on EXTI line 32

0: Event request from Line 32 is masked
1: Event request from Line 32 is not masked


**12.3.8** **Event mask register (EXTI_EMR2)**


Address offset: 0x24


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|MR32|
||||||||||||||||rw|



Bits 31:1 Reserved, must be kept at reset value


Bit 0 **MR32:** Event mask on EXTI line 32

0: Event request from Line 32 is masked
1: Event request from Line 32 is not masked


**12.3.9** **Rising trigger selection register (EXTI_RTSR2)**


Address offset: 0x28


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TR32|
||||||||||||||||rw|



206/1124 RM0364 Rev 4


**RM0364** **Interrupts and events**


Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **TRx:** Rising trigger event configuration bit of line x (x = 32)

0: Rising trigger disabled (for Event and Interrupt) for input line
1: Rising trigger enabled (for Event and Interrupt) for input line.


_Note:_ _The external wakeup lines are edge-triggered. No glitches must be generated on these_
_lines. If a rising edge on an external interrupt line occurs during a write operation to the_
_EXTI_RTSR register, the pending bit is not set._


_Rising and falling edge triggers can be set for the same interrupt line. In this case, both_
_generate a trigger condition._


**12.3.10** **Falling trigger selection register (EXTI_FTSR2)**


Address offset: 0x2C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TR32|
||||||||||||||||rw|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **TR32:** Falling trigger event configuration bit of line 32

0: Falling trigger disabled (for Event and Interrupt) for input line
1: Falling trigger enabled (for Event and Interrupt) for input line.


_Note:_ _The external wakeup lines are edge-triggered. No glitches must be generated on these_
_lines. If a falling edge on an external interrupt line occurs during a write operation to the_
_EXTI_FTSR register, the pending bit is not set._


_Rising and falling edge triggers can be set for the same interrupt line. In this case, both_
_generate a trigger condition.r_


**12.3.11** **Software interrupt event register (EXTI_SWIER2)**


Address offset: 0x30


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SWIER<br>32|
||||||||||||||||rw|



RM0364 Rev 4 207/1124



210


**Interrupts and events** **RM0364**


Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **SWIER32:** Software interrupt on line 32

If the interrupt is enabled on this line in the EXTI_IMR, writing a '1' to this bit when
it is at '0' sets the corresponding pending bit in EXTI_PR resulting in an interrupt
request generation.

This bit is cleared by clearing the corresponding bit of EXTI_PR register (by writing
a ‘1’ into the bit).


**12.3.12** **Pending register (EXTI_PR2)**


Address offset: 0x34


Reset value: undefined

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PR32|
||||||||||||||||rc_w1|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **PRx:** Pending bit on line x (x = 32)

0: No trigger request occurred
1: Selected trigger request occurred

This bit is set when the selected edge event arrives on the external interrupt line.
This bit is cleared by writing a ‘1’ into the bit.


**12.3.13** **EXTI register map**


**Table 36. External interrupt/event controller register map and reset values**













|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**EXTI_IMR1**|Res.|MR[31:0]|Res.|Res.|Res.|Res.|MR[31:0]|Res.|MR[31:0]|MR[31:0]|Res.|MR[31:0]|MR[31:0]|Res.|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|MR[31:0]|
|0x00|Reset value|0|0|0|1|1|1|1||1|0||0|0||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x04|**EXTI_EMR1**|Res.|MR[31:0]|Res.|Res.|Res.|Res.|MR[31:0]|Res.|MR[31:0]|MR[31:0]|Res.|MR[31:0]|MR[31:0]|Res.|||||||||||MR[31:0]||||||||
|0x04|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x08|**EXTI_RTSR1**|TR[31:29]|TR[31:29]|TR[31:29]|Res.|Res.|Res.|Res.|Res.|Res.|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|
|0x08|Reset value|0|0|0|||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


208/1124 RM0364 Rev 4


**RM0364** **Interrupts and events**


**Table 36. External interrupt/event controller register map and reset values (continued)**











































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x08|**EXTI_RTSR1**|Res.|TR[31:29]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TR[22:0]|Res.|TR[22:0]|TR[22:0]|Res.|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|
|0x08|Reset value||0||||||||0||0|0||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0C|**EXTI_FTSR1**|TR[31:29]|TR[31:29]|TR[31:29]|Res.|Res.|Res.|Res.|Res.|Res.|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|
|0x0C|Reset value|0|0|0|||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0C|**EXTI_FTSR1**|Res.|TR[31:29]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TR[22:0]|Res.|TR[22:0]|TR[22:0]|Res.|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|
|0x0C|Reset value||0||||||||0||0|0||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**EXTI_SWIER1**|SWIER<br>[31:29]|SWIER<br>[31:29]|SWIER<br>[31:29]|Res.|Res.|Res.|Res.|Res.|Res.|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|
|0x10|Reset value|0|0|0|||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**EXTI_SWIER1**|Res.|SWIER[31:29]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SWIER[31:29]|Res.|SWIER[31:29]|SWIER[31:29]|Res.|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|
|0x10|Reset value||0||||||||0||0|0||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x14|**EXTI_PR1**|PR<br>[31:29]|PR<br>[31:29]|PR<br>[31:29]|Res.|Res.|Res.|Res.|Res.|Res.|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|
|0x14|Reset value|0|0|0|||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x14|**EXTI_PR1**|Res.|PR[31:29]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PR[31:29]|Res.|PR[31:29]|PR[31:29]|Res.|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|
|0x14|Reset value||0||||||||0||0|0||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x20|**EXTI_IMR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|MR32|
|0x20|Reset value||||||||||||||||||||||||||||||||0|
|0x24|**EXTI_EMR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|MR32|
|0x24|Reset value||||||||||||||||||||||||||||||||0|
|0x28|**EXTI_RTSR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TR32|
|0x28|Reset value||||||||||||||||||||||||||||||||0|
|0x2C|**EXTI_FTSR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TR32|
|0x2C|Reset value||||||||||||||||||||||||||||||||0|


RM0364 Rev 4 209/1124



210


**Interrupts and events** **RM0364**


**Table 36. External interrupt/event controller register map and reset values (continued)**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x30|**EXTI_SWIER2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SWIER32|
|0x30|Reset value||||||||||||||||||||||||||||||||0|
|0x34|**EXTI_PR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PR32|
|0x34|Reset value||||||||||||||||||||||||||||||||0|



Refer to _Section 2.2 on page 47_ for the register boundary addresses.


210/1124 RM0364 Rev 4


