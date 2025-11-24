**Direct memory access controller (DMA)** **RM0041**

# **9 Direct memory access controller (DMA)**


**Low-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 16 and 32 Kbytes.


**Medium-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 64 and 128 Kbytes.


**High-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 256 and 512 Kbytes.


_This_ section _applies to the whole STM32F100xx family, unless otherwise specified._

## **9.1 DMA introduction**


Direct memory access (DMA) is used in order to provide high-speed data transfer between
peripherals and memory as well as memory to memory. Data can be quickly moved by DMA
without any CPU actions. This keeps CPU resources free for other operations.


The two DMA controllers have 12 channels in total (7 for DMA1 and 5 for DMA2), each
dedicated to managing memory access requests from one or more peripherals. It has an
arbiter for handling the priority between DMA requests.

## **9.2 DMA main features**


      - 12 independently configurable channels (requests): 7 for DMA1 and 5 for DMA2


      - Each of the 12 channels is connected to dedicated hardware DMA requests, software
trigger is also supported on each channel. This configuration is done by software.


      - Priorities between requests from channels of one DMA are software programmable (4
levels consisting of _very high_, _high_, _medium_, _low_ ) or hardware in case of equality
(request 1 has priority over request 2, etc.)


      - Independent source and destination transfer size (byte, half word, word), emulating
packing and unpacking. Source/destination addresses must be aligned on the data
size.


      - Support for circular buffer management


      - 3 event flags (DMA Half Transfer, DMA Transfer complete and DMA Transfer Error)
logically ORed together in a single interrupt request for each channel


      - Memory-to-memory transfer


      - Peripheral-to-memory and memory-to-peripheral, and peripheral-to-peripheral
transfers


      - Access to flash, SRAM, APB1, APB2 and AHB peripherals as source and destination


      - Programmable number of data to be transferred: up to 65536


The block diagram is shown in _Figure 20_ and _Figure 21_ .


144/709 RM0041 Rev 6


**RM0041** **Direct memory access controller (DMA)**


**Figure 20. DMA block diagram in low and medium- density**
**Cat.1 and Cat.2 STM32F100xx devices**



































RM0041 Rev 6 145/709



161


**Direct memory access controller (DMA)** **RM0041**


**Figure 21. DMA block diagram in high-density**
**Cat.4 and Cat.5 STM32F100xx devices**






































|Col1|Col2|Col3|Col4|Col5|
|---|---|---|---|---|
|||||DMA request<br><br>DMA request|
|||||DMA request|
||||||







_Note:_ _The DMA2 controller and its related requests are available only in High density value line_
_devices._


_SPI3, UART4, UART5and TIM5 DMA requests are available only in High density value line_
_devices._

## **9.3 DMA functional description**


The DMA controller performs direct memory transfer by sharing the system bus with the
Cortex [®] -M3 core. The DMA request may stop the CPU access to the system bus for some
bus cycles, when the CPU and DMA are targeting the same destination (memory or
peripheral). The bus matrix implements round-robin scheduling, thus ensuring at least half
of the system bus bandwidth (both to memory and peripheral) for the CPU.


**9.3.1** **DMA transactions**


After an event, the peripheral sends a request signal to the DMA controller. The DMA
controller serves the request depending on the channel priorities. As soon as the DMA
controller accesses the peripheral, an Acknowledge is sent to the peripheral by the DMA
controller. The peripheral releases its request as soon as it gets the Acknowledge from the


146/709 RM0041 Rev 6


**RM0041** **Direct memory access controller (DMA)**


DMA controller. Once the request is deasserted by the peripheral, the DMA controller
releases the Acknowledge. If there are more requests, the peripheral can initiate the next
transaction.


In summary, each DMA transfer consists of three operations:


      - The loading of data from the peripheral data register or a location in memory addressed
through an internal current peripheral/memory address register. The start address used
for the first transfer is the base peripheral/memory address programmed in the
DMA_CPARx or DMA_CMARx register


      - The storage of the data loaded to the peripheral data register or a location in memory
addressed through an internal current peripheral/memory address register. The start
address used for the first transfer is the base peripheral/memory address programmed
in the DMA_CPARx or DMA_CMARx register


      - The post-decrementing of the DMA_CNDTRx register, which contains the number of
transactions that have still to be performed.


**9.3.2** **Arbiter**


The arbiter manages the channel requests based on their priority and launches the
peripheral/memory access sequences.


The priorities are managed in two stages:


      - Software: each channel priority can be configured in the DMA_CCRx register. There
are four levels:


–
Very high priority


–
High priority


–
Medium priority


–
Low priority


      - Hardware: if two requests have the same software priority level, the channel with the
lowest number gets priority versus the channel with the highest number. For example,
channel 2 gets priority over channel 4.


_Note:_ _In high-density value line devices, the DMA1 controller has priority over the DMA2_
_controller._


**9.3.3** **DMA channels**


Each channel can handle DMA transfer between a peripheral register located at a fixed
address and a memory address. The amount of data to be transferred (up to 65535) is
programmable. The register which contains the amount of data items to be transferred is
decremented after each transaction.


**Programmable data sizes**


Transfer data sizes of the peripheral and memory are fully programmable through the
PSIZE and MSIZE bits in the DMA_CCRx register.


**Pointer incrementation**


Peripheral and memory pointers can optionally be automatically post-incremented after
each transaction depending on the PINC and MINC bits in the DMA_CCRx register.
If incremented mode is enabled, the address of the next transfer is the address of the
previous one incremented by 1, 2 or 4 depending on the chosen data size. The first transfer


RM0041 Rev 6 147/709



161


**Direct memory access controller (DMA)** **RM0041**


address is the one programmed in the DMA_CPARx/DMA_CMARx registers. During
transfer operations, these registers keep the initially programmed value. The current
transfer addresses (in the current internal peripheral/memory address register) are not
accessible by software.


If the channel is configured in non-circular mode, no DMA request is served after the last
transfer (that is once the number of data items to be transferred has reached zero). In order
to reload a new number of data items to be transferred into the DMA_CNDTRx register, the
DMA channel must be disabled.


_Note:_ _If a DMA channel is disabled, the DMA registers are not reset. The DMA channel registers_
_(DMA_CCRx, DMA_CPARx and DMA_CMARx) retain the initial values programmed during_
_the channel configuration phase._


In circular mode, after the last transfer, the DMA_CNDTRx register is automatically reloaded
with the initially programmed value. The current internal address registers are reloaded with
the base address values from the DMA_CPARx/DMA_CMARx registers.


**Channel configuration procedure**


The following sequence should be followed to configure a DMA channel x (where x is the
channel number).


1. Set the peripheral register address in the DMA_CPARx register. The data are moved
from/ to this address to/ from the memory after the peripheral event.


2. Set the memory address in the DMA_CMARx register. The data are written to or read
from this memory after the peripheral event.


3. Configure the total number of data to be transferred in the DMA_CNDTRx register.
After each peripheral event, this value is decremented.


4. Configure the channel priority using the PL[1:0] bits in the DMA_CCRx register


5. Configure data transfer direction, circular mode, peripheral & memory incremented
mode, peripheral & memory data size, and interrupt after half and/or full transfer in the
DMA_CCRx register


6. Activate the channel by setting the ENABLE bit in the DMA_CCRx register.


As soon as the channel is enabled, it can serve any DMA request from the peripheral
connected on the channel.


Once half of the bytes are transferred, the half-transfer flag (HTIF) is set and an interrupt is
generated if the Half-Transfer Interrupt Enable bit (HTIE) is set. At the end of the transfer,
the Transfer Complete Flag (TCIF) is set and an interrupt is generated if the Transfer
Complete Interrupt Enable bit (TCIE) is set.


**Circular mode**


Circular mode is available to handle circular buffers and continuous data flows (e.g. ADC
scan mode). This feature can be enabled using the CIRC bit in the DMA_CCRx register.
When circular mode is activated, the number of data to be transferred is automatically
reloaded with the initial value programmed during the channel configuration phase, and the
DMA requests continue to be served.


**Memory-to-memory mode**


The DMA channels can also work without being triggered by a request from a peripheral.
This mode is called Memory to Memory mode.


148/709 RM0041 Rev 6


**RM0041** **Direct memory access controller (DMA)**


If the MEM2MEM bit in the DMA_CCRx register is set, then the channel initiates transfers
as soon as it is enabled by software by setting the Enable bit (EN) in the DMA_CCRx
register. The transfer stops once the DMA_CNDTRx register reaches zero. Memory to
Memory mode may not be used at the same time as Circular mode.


**9.3.4** **Programmable data width, data alignment and endians**


When PSIZE and MSIZE are not equal, the DMA performs some data alignments as
described in _Table 52_ .


**Table 52. Programmable data width and endian behavior (when bits PINC = MINC = 1)**


















|Source<br>port<br>width|Desti-<br>nation<br>port<br>width|Number<br>of data<br>items to<br>transfer<br>(NDT)|Source content:<br>address / data|Transfer operations|Destination<br>content:<br>address / data|
|---|---|---|---|---|---|
|8|8|4|@0x0 / B0<br>@0x1 / B1<br>@0x2 / B2<br>@0x3 / B3|1: READ B0[7:0] @0x0 then WRITE B0[7:0] @0x0<br>2: READ B1[7:0] @0x1 then WRITE B1[7:0] @0x1<br>3: READ B2[7:0] @0x2 then WRITE B2[7:0] @0x2<br>4: READ B3[7:0] @0x3 then WRITE B3[7:0] @0x3|@0x0 / B0<br>@0x1 / B1<br>@0x2 / B2<br>@0x3 / B3|
|8|16|4|@0x0 / B0<br>@0x1 / B1<br>@0x2 / B2<br>@0x3 / B3|1: READ B0[7:0] @0x0 then WRITE 00B0[15:0] @0x0<br>2: READ B1[7:0] @0x1 then WRITE 00B1[15:0] @0x2<br>3: READ B3[7:0] @0x2 then WRITE 00B2[15:0] @0x4<br>4: READ B4[7:0] @0x3 then WRITE 00B3[15:0] @0x6|@0x0 / 00B0<br>@0x2 / 00B1<br>@0x4 / 00B2<br>@0x6 / 00B3|
|8|32|4|@0x0 / B0<br>@0x1 / B1<br>@0x2 / B2<br>@0x3 / B3|1: READ B0[7:0] @0x0 then WRITE 000000B0[31:0] @0x0<br>2: READ B1[7:0] @0x1 then WRITE 000000B1[31:0] @0x4<br>3: READ B3[7:0] @0x2 then WRITE 000000B2[31:0] @0x8<br>4: READ B4[7:0] @0x3 then WRITE 000000B3[31:0] @0xC|@0x0 / 000000B0<br>@0x4 / 000000B1<br>@0x8 / 000000B2<br>@0xC / 000000B3|
|16|8|4|@0x0 / B1B0<br>@0x2 / B3B2<br>@0x4 / B5B4<br>@0x6 / B7B6|1: READ B1B0[15:0] @0x0 then WRITE B0[7:0] @0x0<br>2: READ B3B2[15:0] @0x2 then WRITE B2[7:0] @0x1<br>3: READ B5B4[15:0] @0x4 then WRITE B4[7:0] @0x2<br>4: READ B7B6[15:0] @0x6 then WRITE B6[7:0] @0x3|@0x0 / B0<br>@0x1 / B2<br>@0x2 / B4<br>@0x3 / B6|
|16|16|4|@0x0 / B1B0<br>@0x2 / B3B2<br>@0x4 / B5B4<br>@0x6 / B7B6|1: READ B1B0[15:0] @0x0 then WRITE B1B0[15:0] @0x0<br>2: READ B3B2[15:0] @0x2 then WRITE B3B2[15:0] @0x2<br>3: READ B5B4[15:0] @0x4 then WRITE B5B4[15:0] @0x4<br>4: READ B7B6[15:0] @0x6 then WRITE B7B6[15:0] @0x6|@0x0 / B1B0<br>@0x2 / B3B2<br>@0x4 / B5B4<br>@0x6 / B7B6|
|16|32|4|@0x0 / B1B0<br>@0x2 / B3B2<br>@0x4 / B5B4<br>@0x6 / B7B6|1: READ B1B0[15:0] @0x0 then WRITE 0000B1B0[31:0] @0x0<br>2: READ B3B2[15:0] @0x2 then WRITE 0000B3B2[31:0] @0x4<br>3: READ B5B4[15:0] @0x4 then WRITE 0000B5B4[31:0] @0x8<br>4: READ B7B6[15:0] @0x6 then WRITE 0000B7B6[31:0] @0xC|@0x0 / 0000B1B0<br>@0x4 / 0000B3B2<br>@0x8 / 0000B5B4<br>@0xC / 0000B7B6|
|32|8|4|@0x0 / B3B2B1B0<br>@0x4 / B7B6B5B4<br>@0x8 / BBBAB9B8<br>@0xC / BFBEBDBC|1: READ B3B2B1B0[31:0] @0x0 then WRITE B0[7:0] @0x0<br>2: READ B7B6B5B4[31:0] @0x4 then WRITE B4[7:0] @0x1<br>3: READ BBBAB9B8[31:0] @0x8 then WRITE B8[7:0] @0x2<br>4: READ BFBEBDBC[31:0] @0xC then WRITE BC[7:0] @0x3|@0x0 / B0<br>@0x1 / B4<br>@0x2 / B8<br>@0x3 / BC|
|32|16|4|@0x0 / B3B2B1B0<br>@0x4 / B7B6B5B4<br>@0x8 / BBBAB9B8<br>@0xC / BFBEBDBC|1: READ B3B2B1B0[31:0] @0x0 then WRITE B1B0[7:0] @0x0<br>2: READ B7B6B5B4[31:0] @0x4 then WRITE B5B4[7:0] @0x1<br>3: READ BBBAB9B8[31:0] @0x8 then WRITE B9B8[7:0] @0x2<br>4: READ BFBEBDBC[31:0] @0xC then WRITE BDBC[7:0] @0x3|@0x0 / B1B0<br>@0x2 / B5B4<br>@0x4 / B9B8<br>@0x6 / BDBC|
|32|32|4|@0x0 / B3B2B1B0<br>@0x4 / B7B6B5B4<br>@0x8 / BBBAB9B8<br>@0xC / BFBEBDBC|1: READ B3B2B1B0[31:0] @0x0 then WRITE B3B2B1B0[31:0] @0x0<br>2: READ B7B6B5B4[31:0] @0x4 then WRITE B7B6B5B4[31:0] @0x4<br>3: READ BBBAB9B8[31:0] @0x8 then WRITE BBBAB9B8[31:0] @0x8<br>4: READ BFBEBDBC[31:0] @0xC then WRITE BFBEBDBC[31:0] @0xC|@0x0 / B3B2B1B0<br>@0x4 / B7B6B5B4<br>@0x8 / BBBAB9B8<br>@0xC / BFBEBDBC|



**Addressing an AHB peripheral that does not support byte or halfword write**
**operations**


When the DMA initiates an AHB byte or halfword write operation, the data are duplicated on
the unused lanes of the HWDATA[31:0] bus. So when the used AHB slave peripheral does
not support byte or halfword write operations (when HSIZE is not used by the peripheral)


RM0041 Rev 6 149/709



161


**Direct memory access controller (DMA)** **RM0041**


_and_ does not generate any error, the DMA writes the 32 HWDATA bits as shown in the two
examples below:


      - To write the halfword “0xABCD”, the DMA sets the HWDATA bus to “0xABCDABCD”
with HSIZE = HalfWord


      - To write the byte “0xAB”, the DMA sets the HWDATA bus to “0xABABABAB” with
HSIZE = Byte


Assuming that the AHB/APB bridge is an AHB 32-bit slave peripheral that does not take the
HSIZE data into account, it transforms any AHB byte or halfword operation into a 32-bit APB
operation in the following manner:


      - an AHB byte write operation of the data “0xB0” to 0x0 (or to 0x1, 0x2 or 0x3) is
converted to an APB word write operation of the data “0xB0B0B0B0” to 0x0


      - an AHB halfword write operation of the data “0xB1B0” to 0x0 (or to 0x2) is converted to
an APB word write operation of the data “0xB1B0B1B0” to 0x0


For instance, to write the APB backup registers (16-bit registers aligned to a 32-bit address
boundary), the memory source size (MSIZE) must be configured to “16-bit” and the
peripheral destination size (PSIZE) to “32-bit”.


**9.3.5** **Error management**


A DMA transfer error can be generated by reading from or writing to a reserved address
space. When a DMA transfer error occurs during a DMA read or a write access, the faulty
channel is automatically disabled through a hardware clear of its EN bit in the corresponding
Channel configuration register (DMA_CCRx). The channel's transfer error interrupt flag
(TEIF) in the DMA_IFR register is set and an interrupt is generated if the transfer error
interrupt enable bit (TEIE) in the DMA_CCRx register is set.


**9.3.6** **Interrupts**


An interrupt can be produced on a Half-transfer, Transfer complete or Transfer error for
each DMA channel. Separate interrupt enable bits are available for flexibility.


**Table 53. DMA interrupt requests**

|Interrupt event|Event flag|Enable Control bit|
|---|---|---|
|Half-transfer|HTIF|HTIE|
|Transfer complete|TCIF|TCIE|
|Transfer error|TEIF|TEIE|



_Note:_ _In high-density value line devices, DMA2 Channel4 and DMA2 Channel5 interrupts are_
_mapped onto the same interrupt vector. All other DMA1 and DMA2 Channel interrupts have_
_their own interrupt vector._


**9.3.7** **DMA request mapping**


**DMA1 controller**


The 7 requests from the peripherals (TIMx[1,2,3,4,6,7,15,16,17], ADC1, SPI[1,2], I2Cx[1,2],
USARTx[1,2,3]) and DAC Channelx[1,2] are simply logically ORed before entering the
DMA1, this means that only one request must be enabled at a time. Refer to _Figure 22_ .


150/709 RM0041 Rev 6


**RM0041** **Direct memory access controller (DMA)**


The peripheral DMA requests can be independently activated/de-activated by programming
the DMA control bit in the registers of the corresponding peripheral.


**Figure 22. DMA1 request mapping**



























1. The TIM1_CH1 and TIM1_CH2 DMA requests are mapped on DMA Channel 2 and DMA Channel 3,
respectively, only if the TIM1_DMA_REMAP bit in the AFIO_MAPR2 register is cleared. For more details
refer to the AFIO section.


2. The TIM1_CH1 and TIM1_CH2 DMA requests are mapped on DMA Channel 6 only if the
TIM1_DMA_REMAP bit in the AFIO_MAPR2 register is set. For more details refer to the AFIO section.


3. For High-density value line devices, the TIM6_DAC1 and TIM7_DAC2 DMA requests are mapped
respectively on DMA1 Channel 3 and DMA1 Channel 4 only if the TIM67_DAC_DMA_REMAP bit in the
AFIO_MAPR2 register is set and mapped respectively on DMA2 Channel 3 and DMA2 Channel 4 when the
TIM67_DAC_DMA_REMAP bit in the AFIO_MAPR2 register is reset.


RM0041 Rev 6 151/709



161


**Direct memory access controller (DMA)** **RM0041**


On low- and medium -density devices the TIM6_DAC1 and TIM7_DAC2 DMA requests are always
mapped respectively on DMA1 Channel 3 and DMA1 Channel 4. For more details refer to the AFIO
section.


_Table 54_ lists the DMA requests for each channel.


**Table 54. Summary of DMA1 requests for each channel**









|Peripherals|Channel 1|Channel 2|Channel 3|Channel 4|Channel 5|Channel 6|Channel 7|
|---|---|---|---|---|---|---|---|
|ADC1|ADC1|-|-|-|-|-|-|
|SPI|-|SPI1_RX|SPI1_TX|SPI2_RX|SPI2_TX|-|-|
|USART|-|USART3_TX|USART3_RX|USART1_TX|USART1_RX|USART2_RX|USART2_TX|
|I2C|-|-|-|I2C2_TX|I2C2_RX|I2C1_TX|I2C1_RX|
|TIM1|-|TIM1_CH1|-|TIM1_CH4<br>TIM1_TRIG<br>TIM1_COM|TIM1_UP|TIM1_CH3<br>TIM1_CH2<br>TIM1_CH1|-|
|TIM2|TIM2_CH3|TIM2_UP|-|-|TIM2_CH1|-|TIM2_CH2<br>TIM2_CH4|
|TIM3|-|TIM3_CH3|TIM3_CH4<br>TIM3_UP|-|-|TIM3_CH1<br>TIM3_TRIG|-|
|TIM4|TIM4_CH1|-|-|TIM4_CH2|TIM4_CH3|-|TIM4_UP|
|TIM6/DAC_<br>Channel1|-||TIM6_UP/DA<br>C_Channel1|||-||
|TIM7/DAC_<br>Channel2|-|-|-|TIM7_UP/DA<br>C_Channel2|-|-|-|
|TIM15|-|-|-|-|TIM15_CH1<br>TIM15_UP<br>TIM15_TRIG<br>TIM15_COM|-|-|
|TIM16|-|-|-|-|-|TIM16_CH1<br>TIM16_UP|-|
|TIM17|-|-|-|-|-|-|TIM17_CH1<br>TIM17_UP|


**DMA2 controller**


The five requests from the peripherals (TIMx[5,6,7], SPI3, UARTx[4,5], DAC_Channel[1,2])
are simply logically ORed before entering the DMA2, this means that only one request must
be enabled at a time. Refer to _Figure 23_ .


The peripheral DMA requests can be independently activated/de-activated by programming
the DMA control bit in the registers of the corresponding peripheral.


_Note:_ _The DMA2 controller and its relative requests are available only in high-density value line_
_devices._


152/709 RM0041 Rev 6


**RM0041** **Direct memory access controller (DMA)**


**Figure 23. DMA2 request mapping**























1. For high-density value line devices, the TIM6_DAC1 and TIM7_DAC2 DMA requests are mapped
respectively on DMA1 Channel 3 and DMA1 Channel 4 only if the TIM67_DAC_DMA_REMAP bit in the
AFIO_MAPR2 register is set, and mapped respectively on DMA2 Channel 3 and DMA2 Channel 4 when
the TIM67_DAC_DMA_REMAP bit in the AFIO_MAPR2 register is reset. On low- and medium -density
devices the TIM6_DAC1 and TIM7_DAC2 DMA requests are always mapped respectively on DMA1
Channel 3 and DMA1 Channel 4. For more details refer to the AFIO section.


_Table 55_ lists the DMA2 requests for each channel.


**Table 55. Summary of DMA2 requests for each channel**

|Peripherals|Channel 1|Channel 2|Channel 3|Channel 4|Channel 5|
|---|---|---|---|---|---|
|SPI3|SPI3_RX|SPI3_TX|-|-||
|UART4|-|-|UART4_RX|-|UART4_TX|
|UART5|UART5_TX|-|-|UART5_RX|-|
|TIM5|TIM5_CH4<br>TIM5_TRIG|TIM5_CH3<br>TIM5_UP|-|TIM5_CH2|TIM5_CH1|
|TIM6/<br>DAC_Channel1|-|-|TIM6_UP/<br>DAC_Channel1|-|-|
|TIM7/<br>DAC_Channel2|-|-|-|TIM7_UP/<br>DAC_Channel2|-|



RM0041 Rev 6 153/709



161


**Direct memory access controller (DMA)** **RM0041**

## **9.4 DMA registers**


Refer to for a list of abbreviations used in register descriptions.


_Note:_ _In the following registers, all bits related to channel6 and channel7 are not relevant for_
_DMA2 since it has only 5 channels._


The peripheral registers can be accessed by bytes (8-bit), half-words (16-bit) or words (32bit).


**9.4.1** **DMA interrupt status register (DMA_ISR)**


Address offset: 0x00


Reset value: 0x0000 0000

|31 30 29 28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|TEIF7|HTIF7|TCIF7|GIF7|TEIF6|HTIF6|TCIF6|GIF6|TEIF5|HTIF5|TCIF5|GIF5|
|Reserved|r|r|r|r|r|r|r|r|r|r|r|r|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TEIF4|HTIF4|TCIF4|GIF4|TEIF3|HTIF3|TCIF3|GIF3|TEIF2|HTIF2|TCIF2|GIF2|TEIF1|HTIF1|TCIF1|GIF1|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:28 Reserved, must be kept at reset value.


Bits 27, 23, 19, 15, **TEIFx:** Channel x transfer error flag (x = 1 ..7)
11, 7, 3 This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_IFCR register.
0: No transfer error (TE) on channel x
1: A transfer error (TE) occurred on channel x


Bits 26, 22, 18, 14, **HTIFx:** Channel x half transfer flag (x = 1 ..7)
10, 6, 2 This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_IFCR register.
0: No half transfer (HT) event on channel x
1: A half transfer (HT) event occurred on channel x


Bits 25, 21, 17, 13, **TCIFx:** Channel x transfer complete flag (x = 1 ..7)
9, 5, 1 This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_IFCR register.
0: No transfer complete (TC) event on channel x
1: A transfer complete (TC) event occurred on channel x


Bits 24, 20, 16, 12, **GIFx:** Channel x global interrupt flag (x = 1 ..7)
8, 4, 0 This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_IFCR register.
0: No TE, HT or TC event on channel x

1: A TE, HT or TC event occurred on channel x


154/709 RM0041 Rev 6


**RM0041** **Direct memory access controller (DMA)**


**9.4.2** **DMA interrupt flag clear register (DMA_IFCR)**


Address offset: 0x04


Reset value: 0x0000 0000






|31 30 29 28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|CTEIF<br>7|CHTIF<br>7|CTCIF7|CGIF7|CTEIF6|_CHTIF6_|CTCIF6|CGIF6|CTEIF5|CHTIF5|CTCIF5|CGIF5|
|Reserved|w|w|w|w|w|w|w|w|w|w|w|w|



|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CTEIF<br>4|CHTIF<br>4|CTCIF<br>4|CGIF4|CTEIF<br>3|CHTIF<br>3|CTCIF3|CGIF3|CTEIF2|CHTIF2|CTCIF2|CGIF2|CTEIF1|CHTIF1|CTCIF1|CGIF1|
|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|


Bits 31:28 Reserved, must be kept at reset value.


Bits 27, 23, 19, 15, **CTEIFx:** Channel x transfer error clear (x = 1 ..7)
11, 7, 3 This bit is set and cleared by software.

0: No effect

1: Clears the corresponding TEIF flag in the DMA_ISR register


Bits 26, 22, 18, 14, **CHTIFx:** Channel x half transfer clear (x = 1 ..7)
10, 6, 2 This bit is set and cleared by software.

0: No effect

1: Clears the corresponding HTIF flag in the DMA_ISR register


Bits 25, 21, 17, 13, **CTCIFx:** Channel x transfer complete clear (x = 1 ..7)
9, 5, 1 This bit is set and cleared by software.

0: No effect

1: Clears the corresponding TCIF flag in the DMA_ISR register


Bits 24, 20, 16, 12, **CGIFx:** Channel x global interrupt clear (x = 1 ..7)
8, 4, 0 This bit is set and cleared by software.

0: No effect

1: Clears the GIF, TEIF, HTIF and TCIF flags in the DMA_ISR register


RM0041 Rev 6 155/709



161


**Direct memory access controller (DMA)** **RM0041**


**9.4.3** **DMA channel x configuration register (DMA_CCRx) (x = 1..7,**
**where x = channel number)**


Address offset: 0x08 + 0d20 × (channel number – 1)


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved





|15|14|13 12|Col4|11 10|Col6|9 8|Col8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|MEM2<br>MEM|PL[1:0]|PL[1:0]|MSIZE[1:0]|MSIZE[1:0]|PSIZE[1:0]|PSIZE[1:0]|MINC|PINC|CIRC|DIR|TEIE|HTIE|TCIE|EN|
|Res.|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:15 Reserved, must be kept at reset value.


Bit 14 **MEM2MEM:** Memory to memory mode

This bit is set and cleared by software.
0: Memory to memory mode disabled
1: Memory to memory mode enabled


Bits 13:12 **PL[1:0]:** Channel priority level

These bits are set and cleared by software.

00: Low

01: Medium

10: High
11: Very high


Bits 11:10 **MSIZE[1:0]:** Memory size

These bits are set and cleared by software.

00: 8-bits

01: 16-bits

10: 32-bits

11: Reserved


Bits 9:8 **PSIZE[1:0]:** Peripheral size

These bits are set and cleared by software.

00: 8-bits

01: 16-bits

10: 32-bits

11: Reserved


Bit 7 **MINC:** Memory increment mode

This bit is set and cleared by software.
0: Memory increment mode disabled
1: Memory increment mode enabled


Bit 6 **PINC:** Peripheral increment mode

This bit is set and cleared by software.
0: Peripheral increment mode disabled
1: Peripheral increment mode enabled


Bit 5 **CIRC:** Circular mode

This bit is set and cleared by software.

0: Circular mode disabled

1: Circular mode enabled



156/709 RM0041 Rev 6


**RM0041** **Direct memory access controller (DMA)**


Bit 4 **DIR:** Data transfer direction

This bit is set and cleared by software.
0: Read from peripheral
1: Read from memory


Bit 3 **TEIE:** Transfer error interrupt enable

This bit is set and cleared by software.
0: TE interrupt disabled
1: TE interrupt enabled


Bit 2 **HTIE:** Half transfer interrupt enable

This bit is set and cleared by software.
0: HT interrupt disabled
1: HT interrupt enabled


Bit 1 **TCIE:** Transfer complete interrupt enable

This bit is set and cleared by software.
0: TC interrupt disabled
1: TC interrupt enabled


Bit 0 **EN:** Channel enable

This bit is set and cleared by software.

0: Channel disabled

1: Channel enabled


**9.4.4** **DMA channel x number of data register (DMA_CNDTRx) (x = 1..7,**
**where x = channel number)**


Address offset: 0x0C + 0d20 × (channel number – 1)


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|NDT|NDT|NDT|NDT|NDT|NDT|NDT|NDT|NDT|NDT|NDT|NDT|NDT|NDT|NDT|NDT|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **NDT[15:0]:** Number of data to transfer

Number of data to be transferred (0 up to 65535). This register can only be written when the
channel is disabled. Once the channel is enabled, this register is read-only, indicating the
remaining bytes to be transmitted. This register decrements after each DMA transfer.
Once the transfer is completed, this register can either stay at zero or be reloaded
automatically by the value previously programmed if the channel is configured in autoreload mode.

If this register is zero, no transaction can be served whether the channel is enabled or not.


RM0041 Rev 6 157/709



161


**Direct memory access controller (DMA)** **RM0041**


**9.4.5** **DMA channel x peripheral address register (DMA_CPARx) (x = 1..7,**
**where x = channel number)**


Address offset: 0x10 + 0d20 × (channel number – 1)


Reset value: 0x0000 0000


This register must _not_ be written when the channel is enabled.

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|Col17|Col18|Col19|Col20|Col21|Col22|Col23|Col24|Col25|Col26|Col27|Col28|Col29|Col30|Col31|Col32|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|PA|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **PA[31:0]:** Peripheral address

Base address of the peripheral data register from/to which the data are read/written.
When PSIZE is 01 (16-bit), the PA[0] bit is ignored. Access is automatically aligned to a halfword address.

When PSIZE is 10 (32-bit), PA[1:0] are ignored. Access is automatically aligned to a word
address.


**9.4.6** **DMA channel x memory address register (DMA_CMARx) (x = 1..7,**
**where x = channel number)**


Address offset: 0x14 + 0d20 × (channel number – 1)


Reset value: 0x0000 0000


This register must _not_ be written when the channel is enabled.

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|Col17|Col18|Col19|Col20|Col21|Col22|Col23|Col24|Col25|Col26|Col27|Col28|Col29|Col30|Col31|Col32|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|MA|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **MA[31:0]:** Memory address

Base address of the memory area from/to which the data are read/written.
When MSIZE is 01 (16-bit), the MA[0] bit is ignored. Access is automatically aligned to a
half-word address.

When MSIZE is 10 (32-bit), MA[1:0] are ignored. Access is automatically aligned to a word
address.


158/709 RM0041 Rev 6


**RM0041** **Direct memory access controller (DMA)**


**9.4.7** **DMA register map**


The following table gives the DMA register map and the reset values.


**Table 56. DMA register map and reset values**























































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x000|**DMA_ISR**|Reserved|Reserved|Reserved|Reserved|TEIF7|HTIF7|TCIF7|GIF7|TEIF6|HTIF6|TCIF6|GIF6|TEIF5|HTIF5|TCIF5|GIF5|TEIF4|HTIF4|TCIF4|GIF4|TEIF3|HTIF3|TCIF3|GIF3|TEIF2|HTIF2|TCIF2|GIF2|TEIF1|HTIF1|TCIF1|GIF1|
|0x000|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x004|**DMA_IFCR**|Reserved|Reserved|Reserved|Reserved|CTEIF7|CHTIF7|CTCIF7|CGIF7|CTEIF6|CHTIF6|CTCIF6|CGIF6|CTEIF5|CHTIF5|CTCIF5|CGIF5|CTEIF4|CHTIF4|CTCIF4|CGIF4|CTEIF3|CHTIF3|CTCIF3|CGIF3|CTEIF2|CHTIF2|CTCIF2|CGIF2|CTEIF1|CHTIF1|CTCIF1|CGIF1|
|0x004|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x008|**DMA_CCR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MEM2MEM|PL<br>[1:0]|PL<br>[1:0]|M SIZE [1:0]|M SIZE [1:0]|PSIZE [1:0]|PSIZE [1:0]|MINC|PINC|CIRC|DIR|TEIE|HTIE|TCIE|EN|
|0x008|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00C|**DMA_CNDTR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|
|0x00C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x010|**DMA_CPAR1**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x010|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x014|**DMA_CMAR1**|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|
|0x014|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x018|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x01C|**DMA_CCR2**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MEM2MEM|PL<br>[1:0]|PL<br>[1:0]|M SIZE [1:0]|M SIZE [1:0]|PSIZE [1:0]|PSIZE [1:0]|MINC|PINC|CIRC|DIR|TEIE|HTIE|TCIE|EN|
|0x01C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x020|**DMA_CNDTR2**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|
|0x020|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x024|**DMA_CPAR2**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x024|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x028|**DMA_CMAR2**|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|
|0x028|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x02C|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x030|**DMA_CCR3**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MEM2MEM|PL<br>[1:0]|PL<br>[1:0]|M SIZE [1:0]|M SIZE [1:0]|PSIZE [1:0]|PSIZE [1:0]|MINC|PINC|CIRC|DIR|TEIE|HTIE|TCIE|EN|
|0x030|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x034|**DMA_CNDTR3**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|
|0x034|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x038|**DMA_CPAR3**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x038|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x03C|**DMA_CMAR3**|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|
|0x03C|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x040|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|


RM0041 Rev 6 159/709



161


**Direct memory access controller (DMA)** **RM0041**


**Table 56. DMA register map and reset values (continued)**

























































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x044|**DMA_CCR4**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MEM2MEM|PL<br>[1:0]|PL<br>[1:0]|M SIZE [1:0]|M SIZE [1:0]|PSIZE [1:0]|PSIZE [1:0]|MINC|PINC|CIRC|DIR|TEIE|HTIE|TCIE|EN|
|0x044|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x048|**DMA_CNDTR4**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|
|0x048|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x04C|**DMA_CPAR4**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x04C|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x050|**DMA_CMAR4**|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|
|0x050|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x054|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x058|**DMA_CCR5**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MEM2MEM|PL<br>[1:0]|PL<br>[1:0]|M SIZE [1:0]|M SIZE [1:0]|PSIZE [1:0]|PSIZE [1:0]|MINC|PINC|CIRC|DIR|TEIE|HTIE|TCIE|EN|
|0x058|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x05C|**DMA_CNDTR5**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|
|0x05C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x060|**DMA_CPAR5**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x060|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x064|**DMA_CMAR5**|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|
|0x064|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x068|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x06C|**DMA_CCR6**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MEM2MEM|PL<br>[1:0]|PL<br>[1:0]|M SIZE [1:0]|M SIZE [1:0]|PSIZE [1:0]|PSIZE [1:0]|MINC|PINC|CIRC|DIR|TEIE|HTIE|TCIE|EN|
|0x06C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x070|**DMA_CNDTR6**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|
|0x070|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x074|**DMA_CPAR6**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x074|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x078|**DMA_CMAR6**|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|
|0x078|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x07C|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x080|**DMA_CCR7**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MEM2MEM|PL<br>[1:0]|PL<br>[1:0]|M SIZE [1:0]|M SIZE [1:0]|PSIZE [1:0]|PSIZE [1:0]|MINC|PINC|CIRC|DIR|TEIE|HTIE|TCIE|EN|
|0x080|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x084|**DMA_CNDTR7**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|
|0x084|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x088|**DMA_CPAR7**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x088|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


160/709 RM0041 Rev 6


**RM0041** **Direct memory access controller (DMA)**


**Table 56. DMA register map and reset values (continued)**



|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x08C|**DMA_CMAR7**|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|MA[31:0]|
|0x08C|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x090|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|


Refer to _Table 1 on page 37_ and _Table 2 on page 38_ for the register boundary addresses.


RM0041 Rev 6 161/709



161


