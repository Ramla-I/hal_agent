**RM0490** **Memory and bus architecture**

# **2 Memory and bus architecture**

## **2.1 System architecture**


The main system consists of:


      - Two masters:


– Cortex [®] -M0+ core


–
General-purpose DMA


      - Three slaves:


– Internal SRAM


–
Internal flash memory


–
AHB with AHB-to-APB bridge that connects all the APB peripherals


These are interconnected using a multilayer AHB bus architecture as shown in _Figure 1_ .


**Figure 1. System architecture**
















|S|R|AM|
|---|---|---|
|S|||
|AHB<br>br|-t<br>id|o-APB<br>ge|













**System bus (S-bus)**


This bus connects the system bus of the Cortex [®] -M0+ core (peripheral bus) to a bus matrix
that manages the arbitration between the core and the DMA.


**DMA bus**


This bus connects the AHB master interface of the DMA to the bus matrix that manages the
access of CPU and DMA to SRAM, flash memory and AHB/APB peripherals.


RM0490 Rev 5 43/1027



44


**Memory and bus architecture** **RM0490**


**Bus matrix**


The bus matrix arbitrates the access between the core system bus and the DMA master
bus. The arbitration uses a Round Robin algorithm. The bus matrix is composed of masters
(CPU, DMA) and slaves (flash memory interface, SRAM and AHB-to-APB bridge).


AHB peripherals are connected to the system bus through the bus matrix to allow DMA

access.


**AHB-to-APB bridge (APB)**


The AHB-to-APB bridge provides full synchronous connections between the AHB and the
APB bus.


Refer to _Section 2.2: Memory organization_ for the address mapping of the peripherals
connected to this bridge.


After each device reset, all peripheral clocks are disabled (except for the SRAM and flash
memory). Before using a peripheral, its clock must first be enabled through the
RCC_AHBENR, RCC_APBENRx, or RCC_IOPENR register.


_Note:_ _Unless otherwise specified, when a 16- or 8-bit access is performed on an APB register, the_
_access is transformed into a 32-bit access: the bridge duplicates the 16- or 8-bit data to feed_
_the 32-bit vector._


44/1027 RM0490 Rev 5


**RM0490**

## **2.2 Memory organization**


**2.2.1** **Introduction**


Program memory, data memory, registers and I/O ports are organized within the same linear
address space.


The bytes are coded in memory in Little Endian format. The lowest numbered byte in a word
is considered the word’s least significant byte and the highest numbered byte the most
significant.


RM0490 Rev 5 45/1027



45


**RM0490**



**2.2.2** **Memory map and register boundary addresses**


**Figure 2. Memory map**





































1. 0x0000 7FFF for STM32C011xx and STM32C031xx; 0x0800 FFFF for STM32C051xx; 0x0001 FFFF for STM32C071xx;
0x0003 FFFF for STM32C091xx/92xx


2. 0x0800 7FFF for STM32C011xx and STM32C031xx; 0x0000 FFFF for STM32C051xx; 0x0801 FFFF for STM32C071xx;
0x0803 FFFF for STM32C091xx/92xx


3. Depends on boot configuration


All the memory map areas that are not allocated to on-chip memories and peripherals are
considered as reserved. For the detailed mapping of available memory and register areas,
refer to the following tables.


46/1027 RM0490 Rev 5


**RM0490**


**Table 2. STM32C011xx and STM32C031xx boundary addresses**












|Type|Boundary address|Size|Memory Area|Register description|
|---|---|---|---|---|
|SRAM|0x2000 3000 - 0x3FFF FFFF|~512 MB|Reserved|-|
|SRAM|0x2000 0000 - 0x2000 2FFF|12 KB|SRAM|-|
|FLASH|0x1FFF 7880- 0x1FFF FFFF|~34 KB|Reserved|-|
|FLASH|0x1FFF 7800 - 0x1FFF 787F|128 B|Option bytes|_Section 4.4 on page 66_|
|FLASH|0x1FFF 7500 - 0x1FFF 77FF|768 B|Engineering bytes|-|
|FLASH|0x1FFF 7400- 0x1FFF 74FF|256 B|Reserved|-|
|FLASH|0x1FFF 7000 - 0x1FFF 73FF|1 KB|OTP|-|
|FLASH|0x1FFF 1800- 0x1FFF 6FFF|~22 KB|Reserved|-|
|FLASH|0x1FFF 0000 - 0x1FFF 17FF|6 KB|System memory|-|
|FLASH|0x0800 8000 - 0x1FFE FFFF|~384 MB|Reserved|-|
|FLASH|0x0800 0000 - 0x0800 7FFF|32 KB|Main flash memory|_Section 4.3.1 on page 56_|
|FLASH or<br>SRAM|0x0000 8000 - 0x07FF FFFF|~127 MB|Reserved|-|
|FLASH or<br>SRAM|0x0000 0000 - 0x000 7FFF|32 KB|Main flash memory, system<br>memory, or SRAM,<br>depending on boot<br>configuration|-|



**Table 3. STM32C051xx boundary addresses**












|Type|Boundary address|Size|Memory Area|Register description|
|---|---|---|---|---|
|SRAM|0x2000 3000 - 0x3FFF FFFF|~512 MB|Reserved|-|
|SRAM|0x2000 0000 - 0x2000 2FFF|12 KB|SRAM|-|
|FLASH|0x1FFF 8000- 0x1FFF FFFF|32 KB|Reserved|-|
|FLASH|0x1FFF 7800 - 0x1FFF 7FFF|2 KB|Option bytes|_Section 4.4 on page 66_|
|FLASH|0x1FFF 7500 - 0x1FFF 77FF|768 B|Engineering bytes|-|
|FLASH|0x1FFF 7400- 0x1FFF 74FF|256 B|Reserved|-|
|FLASH|0x1FFF 7000 - 0x1FFF 73FF|1 KB|OTP|-|
|FLASH|0x1FFF 3000 - 0x1FFF 6FFF|16 KB|Reserved|-|
|FLASH|0x1FFF 0000 - 0x1FFF 2FFF|12 KB|System memory|-|
|FLASH|0x0801 0000 - 0x1FFE FFFF|~384 MB|Reserved|-|
|FLASH|0x0800 0000 - 0x0800 FFFF|64 KB|Main flash memory|_Section 4.3.1 on page 56_|
|FLASH or<br>SRAM|0x0000 8000 - 0x07FF FFFF|~127 MB|Reserved|-|
|FLASH or<br>SRAM|0x0000 0000 - 0x000 FFFF|64 KB|Main flash memory, system<br>memory, or SRAM,<br>depending on boot<br>configuration|-|



RM0490 Rev 5 47/1027



55


**RM0490**


**Table 4. STM32C071xx boundary addresses**










|Type|Boundary address|Size|Memory Area|Register description|
|---|---|---|---|---|
|SRAM|0x2000 6000 - 0x3FFF FFFF|~512 MB|Reserved|-|
|SRAM|0x2000 0000 - 0x2000 5FFF|24 KB|SRAM|-|
|FLASH|0x1FFF 8000- 0x1FFF FFFF|32 KB|Reserved|-|
|FLASH|0x1FFF 7800 - 0x1FFF 7FFF|2 KB|Option bytes|_Section 4.4 on page 66_|
|FLASH|0x1FFF 7500 - 0x1FFF 77FF|768 B|Engineering bytes|-|
|FLASH|0x1FFF 7400 - 0x1FFF 74FF|256 B|Reserved|-|
|FLASH|0x1FFF 7000 - 0x1FFF 73FF|1 KB|OTP|-|
|FLASH|0x1FFF 0000 - 0x1FFF 6FFF|28 KB|System memory|-|
|FLASH|0x0802 0000 - 0x1FFE FFFF|~384 MB|Reserved|-|
|FLASH|0x0800 0000 - 0x0801 FFFF|128 KB|Main flash memory|_Section 4.3.1 on page 56_|
|FLASH or<br>SRAM|0x0002 0000 - 0x07FF FFFF|~128 MB|Reserved|-|
|FLASH or<br>SRAM|0x0000 0000 - 0x001 FFFF|128 KB|Main flash memory, system<br>memory, or SRAM,<br>depending on boot<br>configuration|-|



**Table 5. STM32C091xx boundary addresses**












|Type|Boundary address|Size|Memory Area|Register description|
|---|---|---|---|---|
|SRAM|0x2000 9000 - 0x3FFF FFFF|~512 MB|Reserved|-|
|SRAM|0x2000 0000 - 0x2000 8FFF|36 KB|SRAM|-|
|FLASH|0x1FFF 8000- 0x1FFF FFFF|32 KB|Reserved|-|
|FLASH|0x1FFF 7800 - 0x1FFF 7FFF|2 KB|Option bytes|_Section 4.4 on page 66_|
|FLASH|0x1FFF 7500 - 0x1FFF 77FF|768 B|Engineering bytes|-|
|FLASH|0x1FFF 7400- 0x1FFF 74FF|256 B|Reserved|-|
|FLASH|0x1FFF 7000 - 0x1FFF 73FF|1 KB|OTP|-|
|FLASH|0x1FFF 4000 - 0x1FFF 6FFF|12 KB|Reserved|-|
|FLASH|0x1FFF 0000 - 0x1FFF 3FFF|16 KB|System memory|-|
|FLASH|0x0804 0000 - 0x1FFE FFFF|~384 MB|Reserved|-|
|FLASH|0x0800 0000 - 0x0803 FFFF|256 KB|Main flash memory|_Section 4.3.1 on page 56_|
|FLASH or<br>SRAM|0x0004 0000 - 0x07FF FFFF|~128 MB|Reserved|-|
|FLASH or<br>SRAM|0x0000 0000 - 0x0003 FFFF|256 KB|Main flash memory, system<br>memory, or SRAM,<br>depending on boot<br>configuration|-|



48/1027 RM0490 Rev 5


**RM0490**


**Table 6. STM32C092xx boundary addresses**












|Type|Boundary address|Size|Memory Area|Register description|
|---|---|---|---|---|
|SRAM|0x2000 7800 - 0x3FFF FFFF|~512 MB|Reserved|-|
|SRAM|0x2000 0000 - 0x2000 77FF|30 KB|SRAM|-|
|FLASH|0x1FFF 8000- 0x1FFF FFFF|32 KB|Reserved|-|
|FLASH|0x1FFF 7800 - 0x1FFF 7FFF|2 KB|Option bytes|_Section 4.4 on page 66_|
|FLASH|0x1FFF 7500 - 0x1FFF 77FF|768 B|Engineering bytes|-|
|FLASH|0x1FFF 7400- 0x1FFF 74FF|256 B|Reserved|-|
|FLASH|0x1FFF 7000 - 0x1FFF 73FF|1 KB|OTP|-|
|FLASH|0x1FFF 4000 - 0x1FFF 6FFF|12 KB|Reserved|-|
|FLASH|0x1FFF 0000 - 0x1FFF 3FFF|16 KB|System memory|-|
|FLASH|0x0804 0000 - 0x1FFE FFFF|~384 MB|Reserved|-|
|FLASH|0x0800 0000 - 0x0803 FFFF|256 KB|Main flash memory|_Section 4.3.1 on page 56_|
|FLASH or<br>SRAM|0x0004 0000 - 0x07FF FFFF|~128 MB|Reserved|-|
|FLASH or<br>SRAM|0x0000 0000 - 0x0003 FFFF|256 KB|Main flash memory, system<br>memory, or SRAM,<br>depending on boot<br>configuration|-|



**Table 7. STM32C0 series peripheral register boundary addresses**





|Bus|Boundary address|Size|Peripheral|Peripheral register map|
|---|---|---|---|---|
|-|0xE000 0000 - 0xE00F FFFF|1MB|Cortex®-M0+ internal<br>peripherals|-|
|IOPORT|0x5000 1800 - 0x5FFF 17FF|~256 MB|Reserved|-|
|IOPORT|0x5000 1400 - 0x5000 17FF|1 KB|GPIOF|_Section 8.5.12 on page 194_|
|IOPORT|0x5000 1000 - 0x5000 13FF|1 KB|Reserved|-|
|IOPORT|0x5000 0C00 - 0x5000 0FFF|1 KB|GPIOD|_Section 8.5.12 on page 194_|
|IOPORT|0x5000 0800 - 0x5000 0BFF|1 KB|GPIOC|_Section 8.5.12 on page 194_|
|IOPORT|0x5000 0400 - 0x5000 07FF|1 KB|GPIOB|_Section 8.5.12 on page 194_|
|IOPORT|0x5000 0000 - 0x5000 03FF|1 KB|GPIOA|_Section 8.5.12 on page 194_|


RM0490 Rev 5 49/1027



55


**RM0490**


**Table 7. STM32C0 series peripheral register boundary addresses (continued)**













|Bus|Boundary address|Size|Peripheral|Peripheral register map|
|---|---|---|---|---|
|AHB|0x4002 3400 - 0x4FFF FFFF|~256 MB|Reserved|-|
|AHB|0x4002 3000 - 0x4002 33FF|1 KB|CRC|_Section 15.4.6 on page 284_|
|AHB|0x4002 2400 - 0x4002 2FFF|3 KB|Reserved|-|
|AHB|0x4002 2000 - 0x4002 23FF|1 KB|FLASH|_Section 4.7.14 on page 90_|
|AHB|0x4002 1C00 - 0x4002 1FFF|3 KB|Reserved|-|
|AHB|0x4002 1800 - 0x4002 1BFF|1 KB|EXTI|_Section 14.5.16 on page 276_|
|AHB|0x4002 1400 - 0x4002 17FF|1 KB|Reserved|-|
|AHB|0x4002 1000 - 0x4002 13FF|1 KB|RCC|_Section 6.4.24 on page 163_|
|AHB|0x4002 0C00 - 0x4002 0FFF|1 KB|Reserved|-|
|AHB|0x4002 0800 - 0x4002 0BFF|1 KB|DMAMUX|_Section 12.6.7 on page 256_|
|AHB|0x4002 0400 - 0x4002 07FF|1 KB|Reserved|-|
|AHB|0x4002 0000 - 0x4002 03FF|1 KB|DMA1|_Section 11.6.7 on page 239_|
|APB|0x4001 5C00 - 0x4001 FFFF|32 KB|Reserved|-|
|APB|0x4001 5800 - 0x4001 5BFF|1 KB|DBG|_Section 30.10.5 on page 1014_|
|APB|0x4001 4C00 - 0x4001 57FF|3 KB|Reserved|-|
|APB|0x4001 4800 - 0x4001 4BFF|1 KB|TIM17|_Section 20.6.21 on page 628_|
|APB|0x4001 4400 - 0x4001 47FF|1 KB|TIM16|_Section 20.6.21 on page 628_|
|APB|0x4001 4000 - 0x4001 43FF|1 KB|TIM15|_Section 20.6.21 on page 628_|
|APB|0x4001 3C00 - 0x4001 3FFF|1 KB|Reserved|-|
|APB|0x4001 3800 - 0x4001 3BFF|1 KB|USART1|_Section 26.8.15 on page 827_|
|APB|0x4001 3400 - 0x4001 37FF|1 KB|Reserved|-|
|APB|0x4001 3000 - 0x4001 33FF|1 KB|SPI1|_Section 27.9.10 on page 886_|
|APB|0x4001 2C00 - 0x4001 2FFF|1 KB|TIM1|_Section 17.4.29 on page 440_|
|APB|0x4001 2800 - 0x4001 2BFF|1 KB|Reserved|-|
|APB|0x4001 2400 - 0x4001 27FF|1 KB|ADC|_Section 16.13 on page 342_|
|APB|0x4001 0400 - 0x4001 23FF|8 KB|Reserved|-|
|APB|0x4001 0080 - 0x4001 03FF|1 KB|SYSCFG(ITLINE)(1)|_Section 9.1.34 on page 213_|
|APB|0x4001 001D - 0x4001 007F|0x4001 001D - 0x4001 007F|Reserved|-|
|APB|0x4001 0000 - 0x4001 001C|0x4001 0000 - 0x4001 001C|SYSCFG|_Section 9.1.34 on page 213_|
|APB|0x4000 CC00- 0x4000 FFFF|19 KB|Reserved|-|
|APB|0x4000 B800- 0x4000 CBFF|5 KB|FDCAN scratch RAM|-|
|APB|0x4000 B400- 0x4000 B7FF|1 KB|FDCAN message RAM|-|
|APB|0x4000 A000 - 0x4000 B3FF|5 KB|Reserved|-|
|APB|0x4000 9800 - 0x4000 9FFF|2 KB|USBRAM|-|
|APB|0x4000 8800 - 0x4000 97FF|4 KB|Reserved|-|
|APB|0x4000 7400 - 0x4000 87FF|5 KB|Reserved|-|
|APB|0x4000 7000 - 0x4000 73FF|1 KB|PWR|_Section 5.4.19 on page 115_|
|APB|0x4000 6C00 - 0x4000 6FFF|1 KB|CRS|_Section 7.7.5 on page 176_|


50/1027 RM0490 Rev 5


**RM0490**


**Table 7. STM32C0 series peripheral register boundary addresses (continued)**






|Bus|Boundary address|Size|Peripheral|Peripheral register map|
|---|---|---|---|---|
|APB|0x4000 6800 - 0x4000 6BFF|1 KB|Reserved|-|
|APB|0x4000 6400 - 0x4000 67FF|1 KB|FDCAN1|_Section 28.4.38 on page 949_|
|APB|0x4000 6000 - 0x4000 63FF|1 KB|Reserved|-|
|APB|0x4000 5C00 - 0x4000 5FFF|1 KB|USB|_Section 29.6.8 on page 994_|
|APB|0x4000 5800 - 0x4000 5BFF|1 KB|I2C2|_Section 25.9.12 on page 741_|
|APB|0x4000 5400 - 0x4000 57FF|1 KB|I2C1|_Section 25.9.12 on page 741_|
|APB|0x4000 5000 - 0x4000 53FF|1 KB|Reserved|-|
|APB|0x4000 4C00 - 0x4000 4FFF|1 KB|USART4|_Section 26.8.15 on page 827_|
|APB|0x4000 4800 - 0x4000 4BFF|1 KB|USART3|_Section 26.8.15 on page 827_|
|APB|0x4000 4400 - 0x4000 47FF|1 KB|USART2|_Section 26.8.15 on page 827_|
|APB|0x4000 4000 - 0x4000 43FF|1 KB|Reserved|-|
|APB|0x4000 3C00 - 0x4000 3FFF|1 KB|Reserved|-|
|APB|0x4000 3800 - 0x4000 3BFF|1 KB|SPI2|_Section 27.9.10 on page 886_|
|APB|0x4000 3400 - 0x4000 37FF|1 KB|Reserved|-|
|APB|0x4000 3000 - 0x4000 33FF|1 KB|IWDG|_Section 22.4.6 on page 639_|
|APB|0x4000 2C00 - 0x4000 2FFF|1 KB|WWDG|_Section 23.5.4 on page 645_|
|APB|0x4000 2800 - 0x4000 2BFF|1 KB|RTC|_Section 24.6.18 on page 675_|
|APB|0x4000 2400 - 0x4000 27FF|1 KB|Reserved|-|
|APB|0x4000 2000 - 0x4000 23FF|1 KB|TIM14|_Section 19.4.13 on page 541_|
|APB|0x4000 1800 - 0x4000 1FFF|2 KB|Reserved|-|
|APB|0x4000 1400 - 0x4000 17FF|1 KB|Reserved|-|
|APB|0x4000 1000 - 0x4000 13FF|1 KB|Reserved|-|
|APB|0x4000 0C00 - 0x4000 0FFF|1 KB|Reserved|-|
|APB|0x4000 0800 - 0x4000 0BFF|1 KB|Reserved|-|
|APB|0x4000 0400 - 0x4000 07FF|1 KB|TIM3|_Section 18.4.26 on page 514_|
|APB|0x4000 0000 - 0x4000 03FF|1 KB|TIM2|_Section 18.4.26 on page 514_|



1. SYSCFG (ITLINE) registers use 0x4001 0000 as reference peripheral base address.

## **2.3 Embedded SRAM**


The following table summarizes the SRAM resources on the devices, with parity check
enabled and disabled.


. **Table 8. SRAM size**

|Device|SRAM with parity (Kbyte)|
|---|---|
|STM32C011xx|6|
|STM32C031xx, STM32C051xx|12|
|STM32C071xx|24|



RM0490 Rev 5 51/1027



55


**RM0490**


**Table 8. SRAM size (continued)**

|Device|SRAM with parity (Kbyte)|
|---|---|
|STM32C092xx|30|
|STM32C091xx|36|



The SRAM can be accessed by bytes, half-words (16 bits) or full words (32 bits), at
maximum system clock frequency without wait state and thus by both CPU and DMA.


**Parity check**


The user can enable the parity check using the option bit RAM_PARITY_CHECK in the user
option byte (refer to _Section 4.4: FLASH option bytes_ ).


The data bus width is 36 bits because 4 bits are available for parity check (1 bit per byte) in
order to increase memory robustness, as required for instance by Class B or SIL norms.


The parity bits are computed and stored when writing into the SRAM. Then, they are
automatically checked when reading. If one bit fails, an NMI is generated.


_Note:_ _When enabling the SRAM parity check, it is advised to initialize by software the whole_
_SRAM at the beginning of the code, to avoid getting parity errors when reading non-_
_initialized locations._

## **2.4 FDCAN RAM**


FDCAN RAM is only present on the STM32C092xx devices.


The FDCAN peripheral uses the first 1 KB of FDCAN RAM as a message RAM. The next
5 KB (FDCAN scratch RAM) can be accessed by the user. As the memory is accessible
only from APB bus, it can only be accessed by words. See section _AHB-to-APB bridge_
_(APB)_ .


_Note:_ _Before accessing the FDCAN RAM, enable the FDCAN1 clock._

## **2.5 Flash memory overview**


The flash memory is composed of two distinct physical areas:


      - The main flash memory block. It contains the application program and user data if

necessary.


      - The information block. It is composed of three parts:


–
Option bytes for hardware and memory protection user configuration.


–
System memory which contains the proprietary boot loader code.


–
OTP (one-time programmable) area
Refer to _Section 4: Embedded flash memory (FLASH)_ for more details.


The flash memory interface implements instruction access and data access based on the
AHB protocol. It implements the prefetch buffer that speeds up CPU code execution. It also
implements the logic necessary to carry out the flash memory operations (Program/Erase)
controlled through the flash memory registers.


52/1027 RM0490 Rev 5


