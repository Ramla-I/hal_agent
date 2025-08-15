**System and memory overview** **RM0091**

# **2 System and memory overview**

## **2.1 System architecture**


The main system consists of:


      - Up to three masters:

– Cortex [®] -M0 core


–
General-purpose DMA1


–
General purpose DMA2 (available on STM32F09x devices only)


      - Four slaves:


– Internal SRAM


–
Internal flash memory


–
AHB1 with AHB to APB bridge, which connects all the APB peripherals


–
AHB2 dedicated to GPIO ports


These are interconnected using a multilayer AHB bus architecture, as shown in _Figure 1_ :


**Figure 1. System architecture**






















|SR|Col2|AM|
|---|---|---|
|SR|||
|SR|O<br>,<br>|O<br>,<br>|
|AHB<br>br|t<br>id|o APB<br>ge|









**System bus**


This bus connects the system bus of the Cortex [®] -M0 core (peripherals bus) to a BusMatrix
which manages the arbitration between the core and the DMA.


44/1017 RM0091 Rev 10


**RM0091** **System and memory overview**


**DMA bus**


This bus connects the AHB master interface of the DMA to the BusMatrix which manages
the access of CPU and DMA to SRAM, flash memory and peripherals.


**BusMatrix**


The BusMatrix manages the access arbitration between the core system bus and the DMA
master bus. The arbitration uses a Round Robin algorithm. The BusMatrix is composed of
up to three masters (CPU, DMA1, DMA2) and four slaves (FLITF, SRAM, AHB1 with AHB to
APB bridge and AHB2).


AHB peripherals are connected on system bus through a BusMatrix to allow DMA access.


**AHB to APB bridge (APB)**


The AHB to APB bridge provides full synchronous connections between the AHB and the
APB bus.


Refer to _Section 2.2.2: Memory map and register boundary addresses_ for the address
mapping of the peripherals connected to this bridge.


After each device reset, all peripheral clocks are disabled (except for the SRAM and flash).
Before using a peripheral you have to enable its clock in the RCC_AHBENR,
RCC_APB2ENR or RCC_APB1ENR register.


_Note:_ _When a 16- or 8-bit access is performed on an APB register, the access is transformed into_
_a 32-bit access: the bridge duplicates the 16- or 8-bit data to feed the 32-bit vector._


RM0091 Rev 10 45/1017



45


**RM0091**

## **2.2 Memory organization**


**2.2.1** **Introduction**


Program memory, data memory, registers and I/O ports are organized within the same linear
4-Gbyte address space.


The bytes are coded in memory in Little Endian format. The lowest numbered byte in a word
is considered the word’s least significant byte and the highest numbered byte the most
significant.


The addressable memory space is divided into eight main blocks, of 512 Mbytes each.


46/1017 RM0091 Rev 10


**RM0091**


**2.2.2** **Memory map and register boundary addresses**


**Figure 2. Memory map**

































All the memory map areas not allocated to on-chip memories and peripherals are
considered “Reserved”. For the detailed mapping of available memory and register areas,
refer to the following table, which gives the boundary addresses of the available peripherals.


**Table 1. STM32F0xx peripheral register boundary addresses**

|Bus|Boundary address|Size|Peripheral|Peripheral register map|
|---|---|---|---|---|
|-|0xE000 0000 - 0xE00F FFFF|1MB|Cortex®-M0 internal<br>peripherals|-|
|-|0x4800 1800 - 0x5FFF FFFF|~384 MB|Reserved|-|



RM0091 Rev 10 47/1017



55


**RM0091**


**Table 1. STM32F0xx peripheral register boundary addresses (continued)**

|Bus|Boundary address|Size|Peripheral|Peripheral register map|
|---|---|---|---|---|
|AHB2|0x4800 1400 - 0x4800 17FF|1KB|GPIOF|_Section 8.4.12 on page 164_|
|AHB2|0x4800 1000 - 0x4800 13FF|1KB|GPIOE|_Section 8.4.12 on page 164_|
|AHB2|0x4800 0C00 - 0x4800 0FFF|1KB|GPIOD|_Section 8.4.12 on page 164_|
|AHB2|0x4800 0800 - 0x4800 0BFF|1KB|GPIOC|_Section 8.4.12 on page 164_|
|AHB2|0x4800 0400 - 0x4800 07FF|1KB|GPIOB|_Section 8.4.12 on page 164_|
|AHB2|0x4800 0000 - 0x4800 03FF|1KB|GPIOA|_Section 8.4.12 on page 164_|
|-|0x4002 4400 - 0x47FF FFFF|~128 MB|Reserved|-|
|AHB1|0x4002 4000 - 0x4002 43FF|1 KB|TSC|_Section 16.6.11 on page 326_|
|AHB1|0x4002 3400 - 0x4002 3FFF|3 KB|Reserved|-|
|AHB1|0x4002 3000 - 0x4002 33FF|1 KB|CRC|_Section 12.5.6 on page 232_|
|AHB1|0x4002 2400 - 0x4002 2FFF|3 KB|Reserved|-|
|AHB1|0x4002 2000 - 0x4002 23FF|1 KB|FLASH interface|_Section 3.5.9 on page 75_|
|AHB1|0x4002 1400 - 0x4002 1FFF|3 KB|Reserved|-|
|AHB1|0x4002 1000 - 0x4002 13FF|1 KB|RCC|_Section 6.4.15 on page 136_|
|AHB1|0x4002 0800 - 0x4002 0FFF|2 KB|Reserved|-|
|AHB1|0x4002 0400 - 0x4002 07FF|1 KB|DMA2|_Section 10.6.8 on page 212_|
|AHB1|0x4002 0000 - 0x4002 03FF|1 KB|DMA|_Section 10.6.8 on page 212_|
|-|0x4001 8000 - 0x4001 FFFF|32 KB|Reserved|-|



48/1017 RM0091 Rev 10


**RM0091**


**Table 1. STM32F0xx peripheral register boundary addresses (continued)**











|Bus|Boundary address|Size|Peripheral|Peripheral register map|
|---|---|---|---|---|
|APB|0x4001 5C00 - 0x4001 7FFF|9 KB|Reserved|-|
|APB|0x4001 5800 - 0x4001 5BFF|1 KB|DBGMCU|_Section 32.9.6 on page 934_|
|APB|0x4001 4C00 - 0x4001 57FF|3 KB|Reserved|-|
|APB|0x4001 4800 - 0x4001 4BFF|1 KB|TIM17|_Section 20.6.17 on page 558_|
|APB|0x4001 4400 - 0x4001 47FF|1 KB|TIM16|_Section 20.6.17 on page 558_|
|APB|0x4001 4000 - 0x4001 43FF|1 KB|TIM15|_Section 20.5.19 on page 541_|
|APB|0x4001 3C00 - 0x4001 3FFF|1 KB|Reserved|-|
|APB|0x4001 3800 - 0x4001 3BFF|1 KB|USART1|_Section 27.8.12 on page 765_|
|APB|0x4001 3400 - 0x4001 37FF|1 KB|Reserved|-|
|APB|0x4001 3000 - 0x4001 33FF|1 KB|SPI1/I2S1|_Section 28.9.10 on page 824_|
|APB|0x4001 2C00 - 0x4001 2FFF|1 KB|TIM1|_Section 17.4.21 on page 402_|
|APB|0x4001 2800 - 0x4001 2BFF|1 KB|Reserved|-|
|APB|0x4001 2400 - 0x4001 27FF|1 KB|ADC|_Section 13.12 on page 274_|
|APB|0x4001 2000 - 0x4001 23FF|1 KB|Reserved|-|
|APB|0x4001 1C00 -0x4001 1FFF|1 KB|USART8|_Section 27.8.12 on page 765_|
|APB|0x4001 1800 - 0x4001 1BFF|1 KB|USART7|_Section 27.8.12 on page 765_|
|APB|0x4001 1400 - 0x4001 17FF|1 KB|USART6|_Section 27.8.12 on page 765_|
|APB|0x4001 0800 - 0x4001 13FF|3 KB|Reserved|-|
|APB|0x4001 0400 - 0x4001 07FF|1 KB|EXTI|_Section 11.3.7 on page 225_|
|APB|0x4001 0000 - 0x4001 03FF|1 KB|SYSCFG<br>COMP|_Section 9.1.38 on page 185_|
|APB|0x4001 0000 - 0x4001 03FF|1 KB|SYSCFG<br>COMP|_Section 15.5.2 on page 308_|
|-|0x4000 8000 - 0x4000 FFFF|32 KB|Reserved|-|


RM0091 Rev 10 49/1017



55


**RM0091**


**Table 1. STM32F0xx peripheral register boundary addresses (continued)**






|Bus|Boundary address|Size|Peripheral|Peripheral register map|
|---|---|---|---|---|
|APB|0x4000 7C00 - 0x4000 7FFF|1 KB|Reserved|-|
|APB|0x4000 7800 - 0x4000 7BFF|1 KB|CEC|_Section 31.7.7 on page 919_|
|APB|0x4000 7400 - 0x4000 77FF|1 KB|DAC|_Section 14.10.15 on page 299_|
|APB|0x4000 7000 - 0x4000 73FF|1 KB|PWR|_Section 5.4.3 on page 94_|
|APB|0x4000 6C00 - 0x4000 6FFF|1 KB|CRS|_Section 7.7.5 on page 147_|
|APB|0x4000 6800 - 0x4000 6BFF|1 KB|Reserved|-|
|APB|0x4000 6400 - 0x4000 67FF|1 KB|CAN|_Section 29.9.5 on page 864_|
|APB|0x4000 6000 - 0x4000 63FF|1 KB|USB/CAN SRAM|_Section 30.6.3 on page 900_|
|APB|0x4000 5C00 - 0x4000 5FFF|1 KB|USB|_Section 30.6.3 on page 900_|
|APB|0x4000 5800 - 0x4000 5BFF|1 KB|I2C2|_Section 26.7.12 on page 698_|
|APB|0x4000 5400 - 0x4000 57FF|1 KB|I2C1|_Section 26.7.12 on page 698_|
|APB|0x4000 5000 - 0x4000 53FF|1 KB|USART5|_Section 27.8.12 on page 765_|
|APB|0x4000 4C00 - 0x4000 4FFF|1 KB|USART4|_Section 27.8.12 on page 765_|
|APB|0x4000 4800 - 0x4000 4BFF|1 KB|USART3|_Section 27.8.12 on page 765_|
|APB|0x4000 4400 - 0x4000 47FF|1 KB|USART2|_Section 27.8.12 on page 765_|
|APB|0x4000 3C00 - 0x4000 43FF|2 KB|Reserved|-|
|APB|0x4000 3800 - 0x4000 3BFF|1 KB|SPI2|_Section 28.9.10 on page 824_|
|APB|0x4000 3400 - 0x4000 37FF|1 KB|Reserved|-|
|APB|0x4000 3000 - 0x4000 33FF|1 KB|IWDG|_Section 23.4.6 on page 582_|
|APB|0x4000 2C00 - 0x4000 2FFF|1 KB|WWDG|_Section 24.5.4 on page 588_|
|APB|0x4000 2800 - 0x4000 2BFF|1 KB|RTC|_Section 25.7.18 on page 628_|
|APB|0x4000 2400 - 0x4000 27FF|1 KB|Reserved|-|
|APB|0x4000 2000 - 0x4000 23FF|1 KB|TIM14|_Section 19.4.13 on page 490_|
|APB|0x4000 1800 - 0x4000 1FFF|2 KB|Reserved|-|
|APB|0x4000 1400 - 0x4000 17FF|1 KB|TIM7|_Section 21.4.9 on page 572_|
|APB|0x4000 1000 - 0x4000 13FF|1 KB|TIM6|_Section 21.4.9 on page 572_|
|APB|0x4000 0800 - 0x4000 0FFF|2 KB|Reserved|-|
|APB|0x4000 0400 - 0x4000 07FF|1 KB|TIM3|_Section 18.4.19 on page 469_|
|APB|0x4000 0000 - 0x4000 03FF|1 KB|TIM2|_Section 18.4.19 on page 469_|



50/1017 RM0091 Rev 10


**RM0091**


**Table 2. STM32F0xx memory boundary addresses**




























|Device|Boundary address|Size|Memory Area|Register description|
|---|---|---|---|---|
|STM32F03x|0x2000 1000 - 0x3FFF FFFF|~512 MB|Reserved|-|
|STM32F03x|0x2000 0000 - 0x2000 0FFF|4 KB|SRAM|_Section 2.3 on page 52_|
|STM32F03x|0x1FFF FC00 - 0x1FFF FFFF|1 KB|Reserved|-|
|STM32F03x|0x1FFF F800 - 0x1FFF FBFF|1 KB|Option bytes|_Section 4 on page 76_|
|STM32F03x|0x1FFF EC00 - 0x1FFF F7FF|3 KB|System memory|-|
|STM32F03x|0x0800 8000 - 0x1FFF EBFF|~384 MB|Reserved|-|
|STM32F03x|0x0800 0000 - 0x0800 7FFF|32 KB|Main flash memory|_Section 3 on page 56_|
|STM32F03x|0x0000 8000 - 0x07FF FFFF|~128 MB|Reserved|-|
|STM32F03x|0x0000 0000 - 0x0000 7FFF|32 KB|Main flash memory,<br>system memory or SRAM<br>depending on BOOT<br>configuration|-|
|STM32F04x|0x2000 1800 - 0x3FFF FFFF|~512 MB|Reserved|-|
|STM32F04x|0x2000 0000 - 0x2000 17FF|6 KB|SRAM|_Section 2.3 on page 52_|
|STM32F04x|0x1FFF FC00 - 0x1FFF FFFF|1 KB|Reserved|-|
|STM32F04x|0x1FFF F800 - 0x1FFF FBFF|1 KB|Option bytes|_Section 4 on page 76_|
|STM32F04x|0x1FFF C400 - 0x1FFF F7FF|13 KB|System memory|-|
|STM32F04x|0x0801 8000- 0x1FFF C7FF|~384 MB|Reserved|-|
|STM32F04x|0x0800 0000 - 0x0801 7FFF|32 KB|Main flash memory|_Section 3 on page 56_|
|STM32F04x|0x0001 8000 - 0x07FF FFFF|~128 MB|Reserved|-|
|STM32F04x|0x0000 0000 - 0x0000 7FFF|32 KB|Main flash memory,<br>system memory or SRAM<br>depending on BOOT<br>configuration|-|
|STM32F05x|0x2000 2000 - 0x3FFF FFFF|~512 MB|Reserved|-|
|STM32F05x|0x2000 0000 - 0x2000 1FFF|8 KB|SRAM|_Section 2.3 on page 52_|
|STM32F05x|0x1FFF FC00 - 0x1FFF FFFF|1 KB|Reserved|-|
|STM32F05x|0x1FFF F800 - 0x1FFF FBFF|1 KB|Option bytes|_Section 4 on page 76_|
|STM32F05x|0x1FFF EC00 - 0x1FFF F7FF|3 KB|System memory|-|
|STM32F05x|0x0801 0000 - 0x1FFF EBFF|~384 MB|Reserved|-|
|STM32F05x|0x0800 0000 - 0x0800 FFFF|64 KB|Main flash memory|_Section 3 on page 56_|
|STM32F05x|0x0001 0000 - 0x07FF FFFF|~128 MB|Reserved|-|
|STM32F05x|0x0000 0000 - 0x0000 FFFF|64 KB|Main flash memory,<br>system memory or SRAM<br>depending on BOOT<br>configuration|-|



RM0091 Rev 10 51/1017



55


**RM0091**


**Table 2. STM32F0xx memory boundary addresses (continued)**













|Device|Boundary address|Size|Memory Area|Register description|
|---|---|---|---|---|
|STM32F07x|0x2000 4000 - 0x3FFF FFFF|~512 MB|Reserved|-|
|STM32F07x|0x2000 0000 - 0x2000 3FFF|16 KB|SRAM|_Section 2.3 on page 52_|
|STM32F07x|0x1FFF F800 - 0x1FFF FFFF|2 KB|Option bytes|_Section 4 on page 76_|
|STM32F07x|0x1FFF C800 - 0x1FFF F7FF|12 KB|System memory|-|
|STM32F07x|0x0802 0000 - 0x1FFF C7FF|~384 MB|Reserved|-|
|STM32F07x|0x0800 0000 - 0x0801 FFFF|128 KB|Main flash memory|_Section 3 on page 56_|
|STM32F07x|0x0002 0000 - 0x07FF FFFF|~128 MB|Reserved|-|
|STM32F07x|0x0000 0000 - 0x0001 FFFF|128 KB|Main flash memory,<br>system memory or SRAM<br>depending on BOOT<br>configuration|-|
|STM32F09x|0x2000 8000 - 0x3FFF FFFF|~512 MB|Reserved|-|
|STM32F09x|0x2000 0000 - 0x2000 7FFF|32 KB|SRAM|_Section 2.3 on page 52_|
|STM32F09x|0x1FFF F800 - 0x1FFF FFFF|2 KB|Option bytes|_Section 4 on page 76_|
|STM32F09x|0x1FFF D800 - 0x1FFF F7FF|8 KB|System memory|-|
|STM32F09x|0x0804 0000 - 0x1FFF D7FF|~384 MB|Reserved|-|
|STM32F09x|0x0800 0000 - 0x0803 FFFF|256 KB|Main flash memory|_Section 3 on page 56_|
|STM32F09x|0x0004 0000 - 0x07FF FFFF|~128 MB|Reserved|-|
|STM32F09x|0x0000 0000 - 0x0003 FFFF|256 KB|Main flash memory,<br>system memory or SRAM<br>depending on BOOT<br>configuration|-|

## **2.3 Embedded SRAM**







STM32F03x devices feature 4 Kbytes of static SRAM. STM32F04x devices feature
6 Kbytes of static SRAM. STM32F05x devices feature 8 Kbytes of static SRAM.
STM32F07xS devices feature 16 Kbytes of static SRAM. STM32F09x devices feature
32 Kbytes of static SRAM.


This RAM can be accessed as bytes, half-words (16 bits) or full words (32 bits). This
memory can be addressed at maximum system clock frequency without wait state and thus
by both CPU and DMA.


**Parity check**


The user can enable the parity check using the option bit RAM_PARITY_CHECK in the user
option byte (refer to _Section 4: Option bytes_ ).


The data bus width is 36 bits because 4 bits are available for parity check (1 bit per byte) in
order to increase memory robustness, as required for instance by Class B or SIL norms.


The parity bits are computed and stored when writing into the SRAM. Then, they are
automatically checked when reading. If one bit fails, an NMI is generated. The same error
can also be linked to the BRK_IN Break input of TIM1/15/16/17, with the


52/1017 RM0091 Rev 10


**RM0091**


SRAM_PARITY_LOCK control bit in the _SYSCFG configuration register 2_
_(SYSCFG_CFGR2)_ . The SRAM Parity Error flag (SRAM_PEF) is available in the _SYSCFG_
_configuration register 2 (SYSCFG_CFGR2)_ .


_Note:_ _When enabling the RAM parity check, it is advised to initialize by software the whole RAM_
_memory at the beginning of the code, to avoid getting parity errors when reading non-_
_initialized locations._

## **2.4 Flash memory overview**


The flash memory is composed of two distinct physical areas:


      - The main flash memory block. It contains the application program and user data if

necessary.


      - The information block. It is composed of two parts:


–
option bytes for hardware and memory protection user configuration


–
system memory which contains the proprietary boot loader code
(refer to _Section 3: Embedded flash memory_ for more details.)


The flash interface implements instruction access and data access based on the AHB
protocol. It implements the prefetch buffer that speeds up CPU code execution. It also
implements the logic necessary to carry out the flash memory operations (Program/Erase)
controlled through the flash registers.


RM0091 Rev 10 53/1017



55


**RM0091**

## **2.5 Boot configuration**


In the STM32F0xx, three different boot modes can be selected through the BOOT0 pin and
boot configuration bits nBOOT1, BOOT_SEL and nBOOT0 in the User option byte, as
shown in the following table.


**Table 3. Boot modes** **[(1)]**









|Boot mode configuration|Col2|Col3|Col4|Mode|
|---|---|---|---|---|
|**nBOOT1**<br>**bit**|**BOOT0**<br>**pin**|**BOOT_SEL**<br>**bit**|**nBOOT0**<br>**bit**|**nBOOT0**<br>**bit**|
|x|0|1|x|**Main flash memory** is selected as boot area(2)|
|1|1|1|x|**System memory** is selected as boot area|
|0|1|1|x|**Embedded SRAM** is selected as boot area|
|x|x|0|1|**Main flash memory** is selected as boot area|
|1|x|0|0|**System memory** is selected as boot area|
|0|x|0|0|**Embedded SRAM** is selected as boot area|


1. Grey options are available on STM32F04x and STM32F09x devices only.


2. For STM32F04x and STM32F09x devices, see also Empty check description.


The boot mode configuration is latched on the 4th rising edge of SYSCLK after a reset. It is
up to the user to set boot mode configuration related to the required boot mode.


The boot mode configuration is also re-sampled when exiting from Standby mode.
Consequently they must be kept in the required Boot mode configuration in Standby mode.
After this startup delay has elapsed, the CPU fetches the top-of-stack value from address
0x0000 0000, then starts code execution from the boot memory at 0x0000 0004.


Depending on the selected boot mode, main flash memory, system memory or SRAM is
accessible as follows:


      - Boot from main flash memory: the main flash memory is aliased in the boot memory
space (0x0000 0000), but still accessible from its original memory space
(0x0800 0000). In other words, the flash memory contents can be accessed starting
from address 0x0000 0000 or 0x0800 0000.


      - Boot from system memory: the system memory is aliased in the boot memory space
(0x0000 0000), but still accessible from its original memory space(0x1FFF EC00 on
STM32F03x and STM32F05x devices, 0x1FFF C400 on STM32F04x devices, 0x1FFF
C800 on STM32F07x and 0x1FFF D800 on STM32F09x devices).


      - Boot from the embedded SRAM: the SRAM is aliased in the boot memory space
(0x0000 0000), but it is still accessible from its original memory space (0x2000 0000).


**Empty check**


On STM32F04x and STM32F09x devices only, internal empty check flag is implemented to
allow easy programming of virgin devices by the boot loader. This flag is used when BOOT0
pin is defining Main flash memory as the target boot area. When the flag is set, the device is
considered as empty and System memory (boot loader) is selected instead of the main flash
as a boot area to allow user to program the flash memory.


54/1017 RM0091 Rev 10


**RM0091**


This flag is updated only during the loading of option bytes: it is set when the content of the
address 0x08000 0000 is read as 0xFFFF FFFF, otherwise it is cleared. It means a power
reset or setting of OBL_LAUNCH bit in FLASH_CR register is needed to clear this flag after
programming of a virgin device to execute user code after System reset.


_Note:_ _If the device is programmed for a first time but the option bytes are not reloaded, the device_
_still selects System memory as a boot area after a System reset. In the STM32F04x, the_
_boot loader code is able to detect this situation. It then changes the boot memory mapping_
_to main flash and performs a jump to user code programmed there. In the STM32F09x, a_
_POR must be performed or the Option bytes reloaded before applying the system reset._


**Physical remap**


Once the boot mode is selected, the application software can modify the memory accessible
in the code area. This modification is performed by programming the MEM_MODE bits in
the _SYSCFG configuration register 1 (SYSCFG_CFGR1)_ . Unlike Cortex [®] M3 and M4, the
M0 CPU does not support the vector table relocation. For application code which is located
in a different address than 0x0800 0000, some additional code must be added in order to be
able to serve the application interrupts. A solution is to relocate by software the vector table
to the internal SRAM:


      - Copy the vector table from the flash (mapped at the base of the application load
address) to the base address of the SRAM at 0x2000 0000.


      - Remap SRAM at address 0x0000 0000, using SYSCFG configuration register 1.

      - Then once an interrupt occurs, the Cortex [®] -M0 processor fetches the interrupt handler
start address from the relocated vector table in SRAM, then it jumps to execute the
interrupt handler located in the flash.


This operation should be done at the initialization phase of the application. Please refer to
AN4065 and attached IAP code from _www.st.com_ for more details.


**Embedded boot loader**


The embedded boot loader is located in the System memory, programmed by ST during
production. It is used to reprogram the flash memory using one of the following serial
interfaces:


      - USART on pins PA9/PA10, PA14/PA15 or PA2/PA3


      - I2C on pins PB6/PB7 (STM32F04xxx, STM32F07xxx and STM32F09xxx devices only)


      - USB DFU interface (STM32F04xxx and STM32F07xxx devices only)


For further details, refer to the application note AN2606.


RM0091 Rev 10 55/1017



55


