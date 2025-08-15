**RM0490** **Nested vectored interrupt controller (NVIC)**

# **13 Nested vectored interrupt controller (NVIC)**

## **13.1 Main features**


      - 32 maskable interrupt channels (not including the sixteen Cortex [®] -M0+ interrupt lines)


      - 4 programmable priority levels (2 bits of interrupt priority are used)


      - Low-latency exception and interrupt handling


      - Power management control


      - Implementation of system control registers


The NVIC and the processor core interface are closely coupled, which enables low-latency
interrupt processing and efficient processing of late arriving interrupts.


All interrupts including the core exceptions are managed by the NVIC. For more information
on exceptions and NVIC programming, refer to the programming manual PM0223.

## **13.2 SysTick calibration value register**


The SysTick calibration value is set to 1000. SysTick reload value register may be adapted
to the actual HCLK frequency and required time period, see PM0223 for more details.

## **13.3 Interrupt and exception vectors**


_Table 55_ is the vector table. Information pertaining to a peripheral only applies to devices
containing that peripheral.


**Table 55. Vector table** **[(1)]**















|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|-|-|-|-|Reserved|0x0000_0000|
|-|-3|fixed|Reset|Reset|0x0000_0004|
|-|-2|fixed|NMI_Handler|Non maskable interrupt. SRAM<br>parity error, HSE CSS and LSE CSS<br>are linked to the NMI vector.|0x0000_0008|
|-|-1|fixed|HardFault_Handler|All class of fault|0x0000_000C|
|-|-|-|-|Reserved|0x0000_0010<br>0x0000_0014<br>0x0000_0018<br>0x0000_001C<br>0x0000_0020<br>0x0000_0024<br>0x0000_0028|
|-|3|settable|SVCall_Handler|System service call via SWI<br>instruction|0x0000_002C|


RM0490 Rev 5 257/1027



259


**Nested vectored interrupt controller (NVIC)** **RM0490**


**Table 55. Vector table** **[(1)]** **(continued)**







|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|-|-|-|-|Reserved|0x0000_0030<br>0x0000_0034|
|-|5|settable|PendSV_Handler|Pendable request for system service|0x0000_0038|
|-|6|settable|SysTick_Handler|System tick timer|0x0000_003C|
|0|7|settable|WWDG|Window watchdog interrupt|0x0000_0040|
|1|8|settable|PVM|VDDIO2 monitor interrupt (EXTI line<br>34)|0x0000_0044|
|2|9|settable|RTC|RTC interrupts (EXTI line 19)|0x0000_0048|
|3|10|settable|FLASH|Flash global interrupt|0x0000_004C|
|4|11|settable|RCC/CRS|RCC/CRS global interrupt|0x0000_0050|
|5|12|settable|EXTI0_1|EXTI line 0 & 1 interrupt|0x0000_0054|
|6|13|settable|EXTI2_3|EXTI line 2 & 3 interrupt|0x0000_0058|
|7|14|settable|EXTI4_15|EXTI line 4 to 15 interrupt|0x0000_005C|
|8|15|settable|USB|USB global interrupt (combined with<br>EXTI line 36)|0x0000_0060|
|9|16|settable|DMA1_Channel1|DMA1 channel 1 interrupt|0x0000_0064|
|10|17|settable|DMA1_Channel2_3|DMA1 channel 2 & 3 interrupts|0x0000_0068|
|11|18|settable|DMAMUX/<br>DMA1_Channel4_5_6<br>_7|DMAMUX and DMA1 channel 4, 5,<br>6, and 7 interrupts|0x0000_006C|
|12|19|settable|ADC|ADC interrupt|0x0000_0070|
|13|20|settable|TIM1_BRK_UP_TRG<br>_COM|TIM1 break, update, trigger and<br>commutation interrupts|0x0000_0074|
|14|21|settable|TIM1_CC|TIM1 Capture Compare interrupt|0x0000_0078|
|15|22|settable|TIM2|TIM2 global interrupt|0x0000_007C|
|16|23|settable|TIM3|TIM3 global interrupt|0x0000_0080|
|17|-|-|-|Reserved|0x0000_0084|
|18|-|-|-|Reserved|0x0000_0088|
|19|26|settable|TIM14|TIM14 global interrupt|0x0000_008C|
|20|27|settable|TIM15|TIM15 global interrupt|0x0000_0090|
|21|28|settable|TIM16|TIM16 global interrupt|0x0000_0094|
|22|29|settable|TIM17|TIM17 global interrupt|0x0000_0098|
|23|30|settable|I2C1|I2C1 global interrupt (combined with<br>EXTI line 23)|0x0000_009C|
|24|31|settable|I2C2|I2C2 global interrupt|0x0000_00A0|
|25|32|settable|SPI1|SPI1 global interrupt|0x0000_00A4|


258/1027 RM0490 Rev 5


**RM0490** **Nested vectored interrupt controller (NVIC)**


**Table 55. Vector table** **[(1)]** **(continued)**

|Position|Priority|Type of<br>priority|Acronym|Description|Address|
|---|---|---|---|---|---|
|26|33|settable|SPI2|SPI2 global interrupt|0x0000_00A8|
|27|34|settable|USART1|USART1 global interrupt (combined<br>with EXTI line 25)|0x0000_00AC|
|28|35|settable|USART2|USART2 global interrupt|0x0000_00B0|
|29|36|settable|USART3/USART4|USART3/4 global interrupt<br>(combined with EXTI 28)|0x0000_00B4|
|30|37|settable|FDCAN_IT0|FDCAN global interrupt 0|0x0000_00B8|
|31|38|settable|FDCAN_IT1|FDCAN global interrupt 1|0x0000_00BC|



1. The grayed cells correspond to the Cortex [®] -M0+ interrupts.


RM0490 Rev 5 259/1027



259


