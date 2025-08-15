**Interrupts and events** **RM0090**

# **12 Interrupts and events**


This Section applies to the whole STM32F4xx family, unless otherwise specified.

## **12.1 Nested vectored interrupt controller (NVIC)**


**12.1.1** **NVIC features**


The nested vector interrupt controller NVIC includes the following features:


      - 82 maskable interrupt channels for STM32F405xx/07xx and STM32F415xx/17xx, and
up to 91 maskable interrupt channels for STM32F42xxx and STM32F43xxx (not
including the 16 interrupt lines of Cortex [®] -M4 with FPU)


      - 16 programmable priority levels (4 bits of interrupt priority are used)


      - low-latency exception and interrupt handling


      - power management control


      - implementation of system control registers


The NVIC and the processor core interface are closely coupled, which enables low latency
interrupt processing and efficient processing of late arriving interrupts.


All interrupts including the core exceptions are managed by the NVIC. For more information
on exceptions and NVIC programming, refer to programming manual PM0214.


**12.1.2** **SysTick calibration value register**


The SysTick calibration value is fixed to 18750, which gives a reference time base of 1 ms
with the SysTick clock set to 18.75 MHz (HCLK/8, with HCLK set to 150 MHz).


**12.1.3** **Interrupt and exception vectors**


See _Table 62_ and _Table 63_, for the vector table for the STM32F405xx/07xx and
STM32F415xx/17xx and STM32F42xxx and STM32F43xxx devices.

## **12.2 External interrupt/event controller (EXTI)**


The external interrupt/event controller consists of up to 23 edge detectors for generating
event/interrupt requests. Each input line can be independently configured to select the type
(interrupt or event) and the corresponding trigger event (rising or falling or both). Each line
can also masked independently. A pending register maintains the status line of the interrupt
requests.


The grey rows in the following tables describe the vectors without specific position.


374/1757 RM0090 Rev 21


**RM0090** **Interrupts and events**


**Table 62. Vector table for STM32F405xx/07xx and STM32F415xx/17xx**











|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|-|-|-|-|Reserved|0x0000 0000|
|-|-3|fixed|Reset|Reset|0x0000 0004|
|-|-2|fixed|NMI|Non maskable interrupt. The RCC<br>Clock Security System (CSS) is linked<br>to the NMI vector.|0x0000 0008|
|-|-1|fixed|HardFault|All class of fault|0x0000 000C|
|-|0|settable|MemManage|Memory management|0x0000 0010|
|-|1|settable|BusFault|Pre-fetch fault, memory access fault|0x0000 0014|
|-|2|settable|UsageFault|Undefined instruction or illegal state|0x0000 0018|
|-|-|-|-|Reserved|0x0000 001C - 0x0000<br>002B|
|-|3|settable|SVCall|System service call via SWI<br>instruction|0x0000 002C|
|-|4|settable|Debug Monitor|Debug Monitor|0x0000 0030|
|-|-|-|-|Reserved|0x0000 0034|
|-|5|settable|PendSV|Pendable request for system service|0x0000 0038|
|-|6|settable|SysTick|System tick timer|0x0000 003C|
|0|7|settable|WWDG|Window Watchdog interrupt|0x0000 0040|
|1|8|settable|PVD|PVD through EXTI line detection<br>interrupt|0x0000 0044|
|2|9|settable|TAMP_STAMP|Tamper and TimeStamp interrupts<br>through the EXTI line|0x0000 0048|
|3|10|settable|RTC_WKUP|RTC Wake-up interrupt through the<br>EXTI line|0x0000 004C|
|4|11|settable|FLASH|Flash global interrupt|0x0000 0050|
|5|12|settable|RCC|RCC global interrupt|0x0000 0054|
|6|13|settable|EXTI0|EXTI Line0 interrupt|0x0000 0058|
|7|14|settable|EXTI1|EXTI Line1 interrupt|0x0000 005C|
|8|15|settable|EXTI2|EXTI Line2 interrupt|0x0000 0060|
|9|16|settable|EXTI3|EXTI Line3 interrupt|0x0000 0064|
|10|17|settable|EXTI4|EXTI Line4 interrupt|0x0000 0068|
|11|18|settable|DMA1_Stream0|DMA1 Stream0 global interrupt|0x0000 006C|


RM0090 Rev 21 375/1757



390


**Interrupts and events** **RM0090**


**Table 62. Vector table for STM32F405xx/07xx and STM32F415xx/17xx (continued)**




|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|12|19|settable|DMA1_Stream1|DMA1 Stream1 global interrupt|0x0000 0070|
|13|20|settable|DMA1_Stream2|DMA1 Stream2 global interrupt|0x0000 0074|
|14|21|settable|DMA1_Stream3|DMA1 Stream3 global interrupt|0x0000 0078|
|15|22|settable|DMA1_Stream4|DMA1 Stream4 global interrupt|0x0000 007C|
|16|23|settable|DMA1_Stream5|DMA1 Stream5 global interrupt|0x0000 0080|
|17|24|settable|DMA1_Stream6|DMA1 Stream6 global interrupt|0x0000 0084|
|18|25|settable|ADC|ADC1, ADC2 and ADC3 global<br>interrupts|0x0000 0088|
|19|26|settable|CAN1_TX|CAN1 TX interrupts|0x0000 008C|
|20|27|settable|CAN1_RX0|CAN1 RX0 interrupts|0x0000 0090|
|21|28|settable|CAN1_RX1|CAN1 RX1 interrupt|0x0000 0094|
|22|29|settable|CAN1_SCE|CAN1 SCE interrupt|0x0000 0098|
|23|30|settable|EXTI9_5|EXTI Line[9:5] interrupts|0x0000 009C|
|24|31|settable|TIM1_BRK_TIM9|TIM1 Break interrupt and TIM9 global<br>interrupt|0x0000 00A0|
|25|32|settable|TIM1_UP_TIM10|TIM1 Update interrupt and TIM10<br>global interrupt|0x0000 00A4|
|26|33|settable|TIM1_TRG_COM_TIM11|TIM1 Trigger and Commutation<br>interrupts and TIM11 global interrupt|0x0000 00A8|
|27|34|settable|TIM1_CC|TIM1 Capture Compare interrupt|0x0000 00AC|
|28|35|settable|TIM2|TIM2 global interrupt|0x0000 00B0|
|29|36|settable|TIM3|TIM3 global interrupt|0x0000 00B4|
|30|37|settable|TIM4|TIM4 global interrupt|0x0000 00B8|
|31|38|settable|I2C1_EV|I2C1 event interrupt|0x0000 00BC|
|32|39|settable|I2C1_ER|I2C1 error interrupt|0x0000 00C0|
|33|40|settable|I2C2_EV|I2C2 event interrupt|0x0000 00C4|
|34|41|settable|I2C2_ER|I2C2 error interrupt|0x0000 00C8|
|35|42|settable|SPI1|SPI1 global interrupt|0x0000 00CC|
|36|43|settable|SPI2|SPI2 global interrupt|0x0000 00D0|
|37|44|settable|USART1|USART1 global interrupt|0x0000 00D4|
|38|45|settable|USART2|USART2 global interrupt|0x0000 00D8|
|39|46|settable|USART3|USART3 global interrupt|0x0000 00DC|



376/1757 RM0090 Rev 21


**RM0090** **Interrupts and events**


**Table 62. Vector table for STM32F405xx/07xx and STM32F415xx/17xx (continued)**



|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|40|47|settable|EXTI15_10|EXTI Line[15:10] interrupts|0x0000 00E0|
|41|48|settable|RTC_Alarm|RTC Alarms (A and B) through EXTI<br>line interrupt|0x0000 00E4|
|42|49|settable|OTG_FS_WKUP|USB On-The-Go FS Wake-up through<br>EXTI line interrupt|0x0000 00E8|
|43|50|settable|TIM8_BRK_TIM12|TIM8 Break interrupt and TIM12<br>global interrupt|0x0000 00EC|
|44|51|settable|TIM8_UP_TIM13|TIM8 Update interrupt and TIM13<br>global interrupt|0x0000 00F0|
|45|52|settable|TIM8_TRG_COM_TIM14|TIM8 Trigger and Commutation<br>interrupts and TIM14 global interrupt|0x0000 00F4|
|46|53|settable|TIM8_CC|TIM8 Capture Compare interrupt|0x0000 00F8|
|47|54|settable|DMA1_Stream7|DMA1 Stream7 global interrupt|0x0000 00FC|
|48|55|settable|FSMC|FSMC global interrupt|0x0000 0100|
|49|56|settable|SDIO|SDIO global interrupt|0x0000 0104|
|50|57|settable|TIM5|TIM5 global interrupt|0x0000 0108|
|51|58|settable|SPI3|SPI3 global interrupt|0x0000 010C|
|52|59|settable|UART4|UART4 global interrupt|0x0000 0110|
|53|60|settable|UART5|UART5 global interrupt|0x0000 0114|
|54|61|settable|TIM6_DAC|TIM6 global interrupt,<br>DAC1 and DAC2 underrun error<br>interrupts|0x0000 0118|
|55|62|settable|TIM7|TIM7 global interrupt|0x0000 011C|
|56|63|settable|DMA2_Stream0|DMA2 Stream0 global interrupt|0x0000 0120|
|57|64|settable|DMA2_Stream1|DMA2 Stream1 global interrupt|0x0000 0124|
|58|65|settable|DMA2_Stream2|DMA2 Stream2 global interrupt|0x0000 0128|
|59|66|settable|DMA2_Stream3|DMA2 Stream3 global interrupt|0x0000 012C|
|60|67|settable|DMA2_Stream4|DMA2 Stream4 global interrupt|0x0000 0130|
|61|68|settable|ETH|Ethernet global interrupt|0x0000 0134|
|62|69|settable|ETH_WKUP|Ethernet Wake-up through EXTI line<br>interrupt|0x0000 0138|
|63|70|settable|CAN2_TX|CAN2 TX interrupts|0x0000 013C|
|64|71|settable|CAN2_RX0|CAN2 RX0 interrupts|0x0000 0140|


RM0090 Rev 21 377/1757



390


**Interrupts and events** **RM0090**


**Table 62. Vector table for STM32F405xx/07xx and STM32F415xx/17xx (continued)**

|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|65|72|settable|CAN2_RX1|CAN2 RX1 interrupt|0x0000 0144|
|66|73|settable|CAN2_SCE|CAN2 SCE interrupt|0x0000 0148|
|67|74|settable|OTG_FS|USB On The Go FS global interrupt|0x0000 014C|
|68|75|settable|DMA2_Stream5|DMA2 Stream5 global interrupt|0x0000 0150|
|69|76|settable|DMA2_Stream6|DMA2 Stream6 global interrupt|0x0000 0154|
|70|77|settable|DMA2_Stream7|DMA2 Stream7 global interrupt|0x0000 0158|
|71|78|settable|USART6|USART6 global interrupt|0x0000 015C|
|72|79|settable|I2C3_EV|I2C3 event interrupt|0x0000 0160|
|73|80|settable|I2C3_ER|I2C3 error interrupt|0x0000 0164|
|74|81|settable|OTG_HS_EP1_OUT|USB On The Go HS End Point 1 Out<br>global interrupt|0x0000 0168|
|75|82|settable|OTG_HS_EP1_IN|USB On The Go HS End Point 1 In<br>global interrupt|0x0000 016C|
|76|83|settable|OTG_HS_WKUP|USB On The Go HS Wake-up through<br>EXTI interrupt|0x0000 0170|
|77|84|settable|OTG_HS|USB On The Go HS global interrupt|0x0000 0174|
|78|85|settable|DCMI|DCMI global interrupt|0x0000 0178|
|79|86|settable|CRYP|CRYP crypto global interrupt|0x0000 017C|
|80|87|settable|HASH_RNG|Hash and Rng global interrupt|0x0000 0180|
|81|88|settable|FPU|FPU global interrupt|0x0000 0184|



**Table 63. Vector table for STM32F42xxx and STM32F43xxx**

|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|-|-|-|-|Reserved|0x0000 0000|
|-|-3|fixed|Reset|Reset|0x0000 0004|
|-|-2|fixed|NMI|Non maskable interrupt, Clock Security<br>System|0x0000 0008|



378/1757 RM0090 Rev 21


**RM0090** **Interrupts and events**


**Table 63. Vector table for STM32F42xxx and STM32F43xxx (continued)**





|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|-|-1|fixed|HardFault|All class of fault|0x0000 000C|
|-|0|settable|MemManage|Memory management|0x0000 0010|
|-|1|settable|BusFault|Pre-fetch fault, memory access fault|0x0000 0014|
|-|2|settable|UsageFault|Undefined instruction or illegal state|0x0000 0018|
|-|-|-|-|Reserved|0x0000 001C -<br>0x0000 002B|
|-|3|settable|SVCall|System Service call via SWI instruction|0x0000 002C|
|-|4|settable|Debug Monitor|Debug Monitor|0x0000 0030|
|-||-|-|Reserved|0x0000 0034|
|-|5|settable|PendSV|Pendable request for system service|0x0000 0038|
|-|6|settable|Systick|System tick timer|0x0000 003C|
|0|7|settable|WWDG|Window Watchdog interrupt|0x0000 0040|
|1|8|settable|PVD|PVD through EXTI line detection interrupt|0x0000 0044|
|2|9|settable|TAMP_STAMP|Tamper and TimeStamp interrupts through<br>the EXTI line|0x0000 0048|
|3|10|settable|RTC_WKUP|RTC Wake-up interrupt through the EXTI<br>line|0x0000 004C|
|4|11|settable|FLASH|Flash global interrupt|0x0000 0050|
|5|12|settable|RCC|RCC global interrupt|0x0000 0054|
|6|13|settable|EXTI0|EXTI Line0 interrupt|0x0000 0058|
|7|14|settable|EXTI1|EXTI Line1 interrupt|0x0000 005C|
|8|15|settable|EXTI2|EXTI Line2 interrupt|0x0000 0060|
|9|16|settable|EXTI3|EXTI Line3 interrupt|0x0000 0064|
|10|17|settable|EXTI4|EXTI Line4 interrupt|0x0000 0068|
|11|18|settable|DMA1_Stream0|DMA1 Stream0 global interrupt|0x0000 006C|
|12|19|settable|DMA1_Stream1|DMA1 Stream1 global interrupt|0x0000 0070|
|13|20|settable|DMA1_Stream2|DMA1 Stream2 global interrupt|0x0000 0074|
|14|21|settable|DMA1_Stream3|DMA1 Stream3 global interrupt|0x0000 0078|
|15|22|settable|DMA1_Stream4|DMA1 Stream4 global interrupt|0x0000 007C|
|16|23|settable|DMA1_Stream5|DMA1 Stream5 global interrupt|0x0000 0080|
|17|24|settable|DMA1_Stream6|DMA1 Stream6 global interrupt|0x0000 0084|


RM0090 Rev 21 379/1757



390


**Interrupts and events** **RM0090**


**Table 63. Vector table for STM32F42xxx and STM32F43xxx (continued)**




|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|18|25|settable|ADC|ADC1, ADC2 and ADC3 global interrupts|0x0000 0088|
|19|26|settable|CAN1_TX|CAN1 TX interrupts|0x0000 008C|
|20|27|settable|CAN1_RX0|CAN1 RX0 interrupts|0x0000 0090|
|21|28|settable|CAN1_RX1|CAN1 RX1 interrupt|0x0000 0094|
|22|29|settable|CAN1_SCE|CAN1 SCE interrupt|0x0000 0098|
|23|30|settable|EXTI9_5|EXTI Line[9:5] interrupts|0x0000 009C|
|24|31|settable|TIM1_BRK_TIM9|TIM1 Break interrupt and TIM9 global<br>interrupt|0x0000 00A0|
|25|32|settable|TIM1_UP_TIM10|TIM1 Update interrupt and TIM10 global<br>interrupt|0x0000 00A4|
|26|33|settable|TIM1_TRG_COM_TIM11|TIM1 Trigger and Commutation interrupts<br>and TIM11 global interrupt|0x0000 00A8|
|27|34|settable|TIM1_CC|TIM1 Capture Compare interrupt|0x0000 00AC|
|28|35|settable|TIM2|TIM2 global interrupt|0x0000 00B0|
|29|36|settable|TIM3|TIM3 global interrupt|0x0000 00B4|
|30|37|settable|TIM4|TIM4 global interrupt|0x0000 00B8|
|31|38|settable|I2C1_EV|I2C1 event interrupt|0x0000 00BC|
|32|39|settable|I2C1_ER|I2C1 error interrupt|0x0000 00C0|
|33|40|settable|I2C2_EV|I2C2 event interrupt|0x0000 00C4|
|34|41|settable|I2C2_ER|I2C2 error interrupt|0x0000 00C8|
|35|42|settable|SPI1|SPI1 global interrupt|0x0000 00CC|
|36|43|settable|SPI2|SPI2 global interrupt|0x0000 00D0|
|37|44|settable|USART1|USART1 global interrupt|0x0000 00D4|
|38|45|settable|USART2|USART2 global interrupt|0x0000 00D8|
|39|46|settable|USART3|USART3 global interrupt|0x0000 00DC|
|40|47|settable|EXTI15_10|EXTI Line[15:10] interrupts|0x0000 00E0|
|41|48|settable|RTC_Alarm|RTC Alarms (A and B) through EXTI line<br>interrupt|0x0000 00E4|
|42|49|settable|OTG_FS_WKUP|USB On-The-Go FS Wake-up through EXTI<br>line interrupt|0x0000 00E8|
|43|50|settable|TIM8_BRK_TIM12|TIM8 Break interrupt and TIM12 global<br>interrupt|0x0000 00EC|



380/1757 RM0090 Rev 21


**RM0090** **Interrupts and events**


**Table 63. Vector table for STM32F42xxx and STM32F43xxx (continued)**



|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|44|51|settable|TIM8_UP_TIM13|TIM8 Update interrupt and TIM13 global<br>interrupt|0x0000 00F0|
|45|52|settable|TIM8_TRG_COM_TIM1<br>4|TIM8 Trigger and Commutation interrupts<br>and TIM14 global interrupt|0x0000 00F4|
|46|53|settable|TIM8_CC|TIM8 Capture Compare interrupt|0x0000 00F8|
|47|54|settable|DMA1_Stream7|DMA1 Stream7 global interrupt|0x0000 00FC|
|48|55|settable|FSMC|FSMC global interrupt|0x0000 0100|
|49|56|settable|SDIO|SDIO global interrupt|0x0000 0104|
|50|57|settable|TIM5|TIM5 global interrupt|0x0000 0108|
|51|58|settable|SPI3|SPI3 global interrupt|0x0000 010C|
|52|59|settable|UART4|UART4 global interrupt|0x0000 0110|
|53|60|settable|UART5|UART5 global interrupt|0x0000 0114|
|54|61|settable|TIM6_DAC|TIM6 global interrupt,<br>DAC1 and DAC2 underrun error interrupts|0x0000 0118|
|55|62|settable|TIM7|TIM7 global interrupt|0x0000 011C|
|56|63|settable|DMA2_Stream0|DMA2 Stream0 global interrupt|0x0000 0120|
|57|64|settable|DMA2_Stream1|DMA2 Stream1 global interrupt|0x0000 0124|
|58|65|settable|DMA2_Stream2|DMA2 Stream2 global interrupt|0x0000 0128|
|59|66|settable|DMA2_Stream3|DMA2 Stream3 global interrupt|0x0000 012C|
|60|67|settable|DMA2_Stream4|DMA2 Stream4 global interrupt|0x0000 0130|
|61|68|settable|ETH|Ethernet global interrupt|0x0000 0134|
|62|69|settable|ETH_WKUP|Ethernet Wake-up through EXTI line<br>interrupt|0x0000 0138|
|63|70|settable|CAN2_TX|CAN2 TX interrupts|0x0000 013C|
|64|71|settable|CAN2_RX0|CAN2 RX0 interrupts|0x0000 0140|
|65|72|settable|CAN2_RX1|CAN2 RX1 interrupt|0x0000 0144|
|66|73|settable|CAN2_SCE|CAN2 SCE interrupt|0x0000 0148|
|67|74|settable|OTG_FS|USB On The Go FS global interrupt|0x0000 014C|
|68|75|settable|DMA2_Stream5|DMA2 Stream5 global interrupt|0x0000 0150|
|69|76|settable|DMA2_Stream6|DMA2 Stream6 global interrupt|0x0000 0154|
|70|77|settable|DMA2_Stream7|DMA2 Stream7 global interrupt|0x0000 0158|
|71|78|settable|USART6|USART6 global interrupt|0x0000 015C|


RM0090 Rev 21 381/1757



390


**Interrupts and events** **RM0090**


**Table 63. Vector table for STM32F42xxx and STM32F43xxx (continued)**




|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|72|79|settable|I2C3_EV|I2C3 event interrupt|0x0000 0160|
|73|80|settable|I2C3_ER|I2C3 error interrupt|0x0000 0164|
|74|81|settable|OTG_HS_EP1_OUT|USB On The Go HS End Point 1 Out global<br>interrupt|0x0000 0168|
|75|82|settable|OTG_HS_EP1_IN|USB On The Go HS End Point 1 In global<br>interrupt|0x0000 016C|
|76|83|settable|OTG_HS_WKUP|USB On The Go HS Wake-up through EXTI<br>interrupt|0x0000 0170|
|77|84|settable|OTG_HS|USB On The Go HS global interrupt|0x0000 0174|
|78|85|settable|DCMI|DCMI global interrupt|0x0000 0178|
|79|86|settable|CRYP|CRYP crypto global interrupt|0x0000 017C|
|80|87|settable|HASH_RNG|Hash and Rng global interrupt|0x0000 0180|
|81|88|Settable|FPU|FPU global interrupt|0x0000 0184|
|82|89|settable|UART7|UART 7 global interrupt|0x0000 0188|
|83|90|settable|UART8|UART 8 global interrupt|0x0000 018C|
|84|91|settable|SPI4|SPI 4 global interrupt|0x0000 0190|
|85|92|settable|SPI5|SPI 5 global interrupt|0x0000 0194|
|86|93|settable|SPI6|SPI 6 global interrupt|0x0000 0198|
|87|94|settable|SAI1|SAI1 global interrupt|0x0000 019C|
|88|95|settable|LCD-TFT|LTDC global interrupt|0x0000 01A0|
|89|96|settable|LCD-TFT|LTDC global Error interrupt|0x0000 01A4|
|90|97|settable|DMA2D|DMA2D global interrupt|0x0000 01A8|



**12.2.1** **EXTI main features**


The main features of the EXTI controller are the following:


      - independent trigger and mask on each interrupt/event line


      - dedicated status bit for each interrupt line


      - generation of up to 23 software event/interrupt requests


      - detection of external signals with a pulse width lower than the APB2 clock period. Refer
to the electrical characteristics section of the STM32F4xx datasheets for details on this

parameter.


382/1757 RM0090 Rev 21


**RM0090** **Interrupts and events**


**12.2.2** **EXTI block diagram**


_Figure 41_ shows the block diagram.


**Figure 41. External interrupt/event controller block diagram**



























**12.2.3** **Wake-up event management**



The STM32F4xx are able to handle external or internal events in order to wake up the core
(WFE). The wake-up event can be generated either by:


      - enabling an interrupt in the peripheral control register but not in the NVIC, and enabling
the SEVONPEND bit in the Cortex [®] -M4 with FPU System Control register. When the
MCU resumes from WFE, the peripheral interrupt pending bit and the peripheral NVIC
IRQ channel pending bit (in the NVIC interrupt clear pending register) have to be
cleared.


      - or configuring an external or internal EXTI line in event mode. When the CPU resumes
from WFE, it is not necessary to clear the peripheral interrupt pending bit or the NVIC
IRQ channel pending bit as the pending bit corresponding to the event line is not set.


To use an external line as a wake-up event, refer to _Section 12.2.4: Functional description_ .


**12.2.4** **Functional description**


To generate the interrupt, the interrupt line should be configured and enabled. This is done
by programming the two trigger registers with the desired edge detection and by enabling
the interrupt request by writing a ‘1’ to the corresponding bit in the interrupt mask register.
When the selected edge occurs on the external interrupt line, an interrupt request is


RM0090 Rev 21 383/1757



390


**Interrupts and events** **RM0090**


generated. The pending bit corresponding to the interrupt line is also set. This request is
reset by writing a ‘1’ in the pending register.


To generate the event, the event line should be configured and enabled. This is done by
programming the two trigger registers with the desired edge detection and by enabling the
event request by writing a ‘1’ to the corresponding bit in the event mask register. When the
selected edge occurs on the event line, an event pulse is generated. The pending bit
corresponding to the event line is not set.


An interrupt/event request can also be generated by software by writing a ‘1’ in the software
interrupt/event register.


**Hardware interrupt selection**


To configure the 23 lines as interrupt sources, use the following procedure:


      - Configure the mask bits of the 23 interrupt lines (EXTI_IMR)


      - Configure the Trigger selection bits of the interrupt lines (EXTI_RTSR and EXTI_FTSR)


      - Configure the enable and mask bits that control the NVIC IRQ channel mapped to the
external interrupt controller (EXTI) so that an interrupt coming from one of the 23 lines
can be correctly acknowledged.


**Hardware event selection**


To configure the 23 lines as event sources, use the following procedure:


      - Configure the mask bits of the 23 event lines (EXTI_EMR)


      - Configure the Trigger selection bits of the event lines (EXTI_RTSR and EXTI_FTSR)


**Software interrupt/event selection**


The 23 lines can be configured as software interrupt/event lines. The following is the
procedure to generate a software interrupt.


      - Configure the mask bits of the 23 interrupt/event lines (EXTI_IMR, EXTI_EMR)


      - Set the required bit in the software interrupt register (EXTI_SWIER)


384/1757 RM0090 Rev 21


**RM0090** **Interrupts and events**


**12.2.5** **External interrupt/event line mapping**


Up to 140 GPIOs (STM32F405xx/07xx and STM32F415xx/17xx), 168 GPIOs
(STM32F42xxx and STM32F43xxx) are connected to the 16 external interrupt/event lines in
the following manner:


**Figure 42. External interrupt/event GPIO mapping**
**(STM32F405xx/07xx and STM32F415xx/17xx)**



















RM0090 Rev 21 385/1757



390


**Interrupts and events** **RM0090**


**Figure 43. External interrupt/event GPIO mapping** **(STM32F42xxx and STM32F43xxx)**



















The seven other EXTI lines are connected as follows:


      - EXTI line 16 is connected to the PVD output


      - EXTI line 17 is connected to the RTC Alarm event


      - EXTI line 18 is connected to the USB OTG FS Wake-up event


      - EXTI line 19 is connected to the Ethernet Wake-up event


      - EXTI line 20 is connected to the USB OTG HS (configured in FS) Wake-up event


      - EXTI line 21 is connected to the RTC Tamper and TimeStamp events


      - EXTI line 22 is connected to the RTC Wake-up event


386/1757 RM0090 Rev 21


**RM0090** **Interrupts and events**

## **12.3 EXTI registers**


Refer to _Section 1.1: List of abbreviations for registers_ for a list of abbreviations used in
register descriptions.


**12.3.1** **Interrupt mask register (EXTI_IMR)**


Address offset: 0x00


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|
|Reserved|MR22|MR21|MR20|MR19|MR18|MR17|MR16|
|Reserved|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MR15|MR14|MR13|MR12|MR11|MR10|MR9|MR8|MR7|MR6|MR5|MR4|MR3|MR2|MR1|MR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:23 Reserved, must be kept at reset value.


Bits 22:0 **MRx:** Interrupt mask on line x

0: Interrupt request from line x is masked
1: Interrupt request from line x is not masked


**12.3.2** **Event mask register (EXTI_EMR)**


Address offset: 0x04

Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|
|Reserved|MR22|MR21|MR20|MR19|MR18|MR17|MR16|
|Reserved|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MR15|MR14|MR13|MR12|MR11|MR10|MR9|MR8|MR7|MR6|MR5|MR4|MR3|MR2|MR1|MR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:23 Reserved, must be kept at reset value.


Bits 22:0 **MRx:** Event mask on line x

0: Event request from line x is masked
1: Event request from line x is not masked


RM0090 Rev 21 387/1757



390


**Interrupts and events** **RM0090**


**12.3.3** **Rising trigger selection register (EXTI_RTSR)**


Address offset: 0x08

Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|
|Reserved|TR22|TR21|TR20|TR19|TR18|TR17|TR16|
|Reserved|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:23 Reserved, must be kept at reset value.


Bits 22:0 **TRx:** Rising trigger event configuration bit of line x

0: Rising trigger disabled (for Event and Interrupt) for input line
1: Rising trigger enabled (for Event and Interrupt) for input line


_Note:_ _The external wake-up lines are edge triggered, no glitch must be generated on these lines._
_If a rising edge occurs on the external interrupt line while writing to the EXTI_RTSR register,_
_the pending bit is be set._


_Rising and falling edge triggers can be set for the same interrupt line. In this configuration,_
_both generate a trigger condition._


**12.3.4** **Falling trigger selection register (EXTI_FTSR)**


Address offset: 0x0C

Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|
|Reserved|TR22|TR21|TR20|TR19|TR18|TR17|TR16|
|Reserved|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|TR15<br>TR14<br>TR13<br>TR12<br>TR11<br>TR10<br>TR9<br>TR8<br>TR7<br>TR6<br>TR5<br>TR4<br>TR3<br>TR2<br>TR1<br>TR0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:23 Reserved, must be kept at reset value.


Bits 22:0 **TRx:** Falling trigger event configuration bit of line x

0: Falling trigger disabled (for Event and Interrupt) for input line
1: Falling trigger enabled (for Event and Interrupt) for input line.


_Note:_ _The external wake-up lines are edge triggered, no glitch must be generated on these lines._
_If a falling edge occurs on the external interrupt line while writing to the EXTI_FTSR register,_
_the pending bit is not set._


_Rising and falling edge triggers can be set for the same interrupt line. In this configuration,_
_both generate a trigger condition._


388/1757 RM0090 Rev 21


**RM0090** **Interrupts and events**


**12.3.5** **Software interrupt event register (EXTI_SWIER)**


Address offset: 0x10

Reset value: 0x0000 0000






|31 30 29 28 27 26 25 24 23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|
|Reserved|SWIER<br>22|SWIER<br>21|SWIER<br>20|SWIER<br>19|SWIER<br>18|SWIER<br>17|SWIER<br>16|
|Reserved|rw|rw|rw|rw|rw|rw|rw|



|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SWIER<br>15|SWIER<br>14|SWIER<br>13|SWIER<br>12|SWIER<br>11|SWIER<br>10|SWIER<br>9|SWIER<br>8|SWIER<br>7|SWIER<br>6|SWIER<br>5|SWIER<br>4|SWIER<br>3|SWIER<br>2|SWIER<br>1|SWIER<br>0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:23 Reserved, must be kept at reset value.


Bits 22:0 **SWIERx:** Software Interrupt on line x

If interrupt are enabled on line x in the EXTI_IMR register, writing '1' to SWIERx bit when it is
set at '0' sets the corresponding pending bit in the EXTI_PR register, thus resulting in an
interrupt request generation.
This bit is cleared by clearing the corresponding bit in EXTI_PR (by writing a 1 to the bit).


**12.3.6** **Pending register (EXTI_PR)**


Address offset: 0x14


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|
|Reserved|PR22|PR21|PR20|PR19|PR18|PR17|PR16|
|Reserved|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|PR15<br>PR14<br>PR13<br>PR12<br>PR11<br>PR10<br>PR9<br>PR8<br>PR7<br>PR6<br>PR5<br>PR4<br>PR3<br>PR2<br>PR1<br>PR0|
|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|



Bits 31:23 Reserved, must be kept at reset value.


Bits 22:0 **PRx:** Pending bit

0: No trigger request occurred
1: selected trigger request occurred
This bit is set when the selected edge event arrives on the external interrupt line.
This bit is cleared by programming it to ‘1’.


RM0090 Rev 21 389/1757



390


**Interrupts and events** **RM0090**


**12.3.7** **EXTI register map**


_Table 65_ gives the EXTI register map and the reset values.



**Table 64. External interrupt/event controller register map and reset values**





































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**EXTI_IMR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|
|0x00|**EXTI_IMR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x04|**EXTI_EMR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|MR[22:0]|
|0x04|**EXTI_EMR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x08|**EXTI_RTSR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|
|0x08|**EXTI_RTSR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0C|**EXTI_FTSR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|TR[22:0]|
|0x0C|**EXTI_FTSR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**EXTI_SWIER**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|SWIER[22:0]|
|0x10|**EXTI_SWIER**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x14|**EXTI_PR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|PR[22:0]|
|0x14|**EXTI_PR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


Refer to _Section 2.3: Memory map_ for the register boundary addresses.


390/1757 RM0090 Rev 21


