**RM0090** **DMA controller (DMA)**

# **10 DMA controller (DMA)**


This section applies to the whole STM32F4xx family, unless otherwise specified.

## **10.1 DMA introduction**


Direct memory access (DMA) is used in order to provide high-speed data transfer between
peripherals and memory and between memory and memory. Data can be quickly moved by
DMA without any CPU action. This keeps CPU resources free for other operations.


The DMA controller combines a powerful dual AHB master bus architecture with
independent FIFO to optimize the bandwidth of the system, based on a complex bus matrix
architecture.


The two DMA controllers have 16 streams in total (8 for each controller), each dedicated to
managing memory access requests from one or more peripherals. Each stream can have
up to 8 channels (requests) in total. And each has an arbiter for handling the priority
between DMA requests.

## **10.2 DMA main features**


The main DMA features are:


      - Dual AHB master bus architecture, one dedicated to memory accesses and one
dedicated to peripheral accesses


      - AHB slave programming interface supporting only 32-bit accesses


      - 8 streams for each DMA controller, up to 8 channels (requests) per stream


      - Four-word depth 32 first-in, first-out memory buffers (FIFOs) per stream, that can be
used in FIFO mode or direct mode:


–
FIFO mode: with threshold level software selectable between 1/4, 1/2 or 3/4 of the
FIFO size


– Direct mode


Each DMA request immediately initiates a transfer from/to the memory. When it is
configured in direct mode (FIFO disabled), to transfer data in memory-toperipheral mode, the DMA preloads only one data from the memory to the internal


RM0090 Rev 21 305/1757



341


**DMA controller (DMA)** **RM0090**


FIFO to ensure an immediate data transfer as soon as a DMA request is triggered
by a peripheral.


      - Each stream can be configured by hardware to be:


–
a regular channel that supports peripheral-to-memory, memory-to-peripheral and
memory-to-memory transfers


–
a double buffer channel that also supports double buffering on the memory side


      - Each of the 8 streams are connected to dedicated hardware DMA channels (requests)


      - Priorities between DMA stream requests are software-programmable (4 levels
consisting of very high, high, medium, low) or hardware in case of equality (request 0
has priority over request 1, etc.)


      - Each stream also supports software trigger for memory-to-memory transfers (only
available for the DMA2 controller)


      - Each stream request can be selected among up to 8 possible channel requests. This
selection is software-configurable and allows several peripherals to initiate DMA
requests


      - The number of data items to be transferred can be managed either by the DMA
controller or by the peripheral:


– DMA flow controller: the number of data items to be transferred is softwareprogrammable from 1 to 65535


–
Peripheral flow controller: the number of data items to be transferred is unknown
and controlled by the source or the destination peripheral that signals the end of
the transfer by hardware


      - Independent source and destination transfer width (byte, half-word, word): when the
data widths of the source and destination are not equal, the DMA automatically
packs/unpacks the necessary transfers to optimize the bandwidth. This feature is only
available in FIFO mode


      - Incrementing or non-incrementing addressing for source and destination


      - Supports incremental burst transfers of 4, 8 or 16 beats. The size of the burst is
software-configurable, usually equal to half the FIFO size of the peripheral


      - Each stream supports circular buffer management


      - 5 event flags (DMA Half Transfer, DMA Transfer complete, DMA Transfer Error, DMA
FIFO Error, Direct Mode Error) logically ORed together in a single interrupt request for
each stream


306/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**

## **10.3 DMA functional description**



**10.3.1** **General description**


_Figure 32_ shows the block diagram of a DMA.


**Figure 32. DMA block diagram**

















The DMA controller performs direct memory transfer: as an AHB master, it can take the
control of the AHB bus matrix to initiate AHB transactions.



It can carry out the following transactions:


- peripheral-to-memory


- memory-to-peripheral




- memory-to-memory


The DMA controller provides two AHB master ports: the _AHB memory port_, intended to be
connected to memories and the _AHB peripheral port_, intended to be connected to
peripherals. However, to allow memory-to-memory transfers, the _AHB peripheral port_ must
also have access to the memories.


The AHB slave port is used to program the DMA controller (it supports only 32-bit
accesses).


RM0090 Rev 21 307/1757



341


**DMA controller (DMA)** **RM0090**


See _Figure 33_ and _Figure 34_ for the implementation of the system of two DMA controllers.


**Figure 33. System implementation of the two DMA controllers**
**(STM32F405xx/07xx and STM32F415xx/17xx)**





























1. The DMA1 controller AHB peripheral port is not connected to the bus matrix like DMA2 controller. As a result, only DMA2
streams are able to perform memory-to-memory transfers.


308/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


**Figure 34. System implementation of the two DMA controllers**
**(STM32F42xxx and STM32F43xxx)**





























1. The DMA1 controller AHB peripheral port is not connected to the bus matrix like in the case of the DMA2
controller, thus only DMA2 streams are able to perform memory-to-memory transfers.


**10.3.2** **DMA transactions**


A DMA transaction consists of a sequence of a given number of data transfers. The number
of data items to be transferred and their width (8-bit, 16-bit or 32-bit) are softwareprogrammable.


Each DMA transfer consists of three operations:


      - A loading from the peripheral data register or a location in memory, addressed through
the DMA_SxPAR or DMA_SxM0AR register


      - A storage of the data loaded to the peripheral data register or a location in memory
addressed through the DMA_SxPAR or DMA_SxM0AR register


      - A post-decrement of the DMA_SxNDTR register, which contains the number of
transactions that still have to be performed


RM0090 Rev 21 309/1757



341


**DMA controller (DMA)** **RM0090**


After an event, the peripheral sends a request signal to the DMA controller. The DMA
controller serves the request depending on the channel priorities. As soon as the DMA
controller accesses the peripheral, an Acknowledge signal is sent to the peripheral by the
DMA controller. The peripheral releases its request as soon as it gets the Acknowledge
signal from the DMA controller. Once the request has been deasserted by the peripheral,
the DMA controller releases the Acknowledge signal. If there are more requests, the
peripheral can initiate the next transaction.


**10.3.3** **Channel selection**


Each stream is associated with a DMA request that can be selected out of 8 possible
channel requests. The selection is controlled by the CHSEL[2:0] bits in the DMA_SxCR
register.


**Figure 35. Channel selection**











The 8 requests from the peripherals (TIM, ADC, SPI, I2C, etc.) are independently connected
to each channel and their connection depends on the product implementation.


See the following table(s) for examples of DMA request mappings.


**Table 43. DMA1 request mapping**






























|Peripheral<br>requests|Stream 0|Stream 1|Stream 2|Stream 3|Stream 4|Stream 5|Stream 6|Stream 7|
|---|---|---|---|---|---|---|---|---|
|Channel 0|SPI3_RX|-|SPI3_RX|SPI2_RX|SPI2_TX|SPI3_TX|-|SPI3_TX|
|Channel 1|I2C1_RX|-|TIM7_UP|-|TIM7_UP|I2C1_RX|I2C1_TX|I2C1_TX|
|Channel 2|TIM4_CH1|-|I2S3_EXT_<br>RX|TIM4_CH2|I2S2_EXT_<br>TX|I2S3_EXT_<br>TX|TIM4_UP|TIM4_CH3|
|Channel 3|I2S3_EXT_<br>RX|TIM2_UP<br>TIM2_CH3|I2C3_RX|I2S2_EXT_<br>RX|I2C3_TX|TIM2_CH1|TIM2_CH2<br>TIM2_CH4|TIM2_UP<br>TIM2_CH4|
|Channel 4|UART5_RX|USART3_RX|UART4_RX|USART3_TX|UART4_TX|USART2_RX|USART2_TX|UART5_TX|
|Channel 5|UART8_TX(1)|UART7_TX(1)|TIM3_CH4<br>TIM3_UP|UART7_RX(1)|TIM3_CH1<br>TIM3_TRIG|TIM3_CH2|UART8_RX(1)|TIM3_CH3|



310/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


**Table 43. DMA1 request mapping** **(continued)**











|Peripheral<br>requests|Stream 0|Stream 1|Stream 2|Stream 3|Stream 4|Stream 5|Stream 6|Stream 7|
|---|---|---|---|---|---|---|---|---|
|Channel 6|TIM5_CH3<br>TIM5_UP|TIM5_CH4<br>TIM5_TRIG|TIM5_CH1|TIM5_CH4<br>TIM5_TRIG|TIM5_CH2|-|TIM5_UP|-|
|Channel 7|-|TIM6_UP|I2C2_RX|I2C2_RX|USART3_TX|DAC1|DAC2|I2C2_TX|


1. These requests are available on STM32F42xxx and STM32F43xxx only.


**Table 44. DMA2 request mapping**

|Peripheral<br>requests|Stream 0|Stream 1|Stream 2|Stream 3|Stream 4|Stream 5|Stream 6|Stream 7|
|---|---|---|---|---|---|---|---|---|
|Channel 0|ADC1|-SAI1_A(1)|TIM8_CH1<br>TIM8_CH2<br>TIM8_CH3|-SAI1_A(1)|ADC1|SAI1_B(1)-|TIM1_CH1<br>TIM1_CH2<br>TIM1_CH3|-|
|Channel 1|-|DCMI|ADC2|ADC2|SAI1_B(1)-|-SPI6_TX(1)|SPI6_RX(1)-|DCMI|
|Channel 2|ADC3|ADC3|-|SPI5_RX(1)-|-SPI5_TX(1)|CRYP_OUT|CRYP_IN|HASH_IN|
|Channel 3|SPI1_RX|-|SPI1_RX|SPI1_TX|-|SPI1_TX|-|-|
|Channel 4|SPI4_RX(1)-|-SPI4_TX(1)|USART1_RX|SDIO|-|USART1_RX|SDIO|USART1_TX|
|Channel 5|-|USART6_RX|USART6_RX|SPI4_RX(1)-|-SPI4_TX(1)|-|USART6_TX|USART6_TX|
|Channel 6|TIM1_TRIG|TIM1_CH1|TIM1_CH2|TIM1_CH1|TIM1_CH4<br>TIM1_TRIG<br>TIM1_COM|TIM1_UP|TIM1_CH3|-|
|Channel 7|-|TIM8_UP|TIM8_CH1|TIM8_CH2|TIM8_CH3|SPI5_RX(1)-|SPI5_TX(1)-|TIM8_CH4<br>TIM8_TRIG<br>TIM8_COM|



1. These requests are available on STM32F42xxx and STM32F43xxx.


**10.3.4** **Arbiter**


An arbiter manages the 8 DMA stream requests based on their priority for each of the two
AHB master ports (memory and peripheral ports) and launches the peripheral/memory

access sequences.


Priorities are managed in two stages:


       - Software: each stream priority can be configured in the DMA_SxCR register. There are
four levels:


–
Very high priority


–
High priority


–
Medium priority


–
Low priority


       - Hardware: If two requests have the same software priority level, the stream with the
lower number takes priority over the stream with the higher number. For example,
Stream 2 takes priority over Stream 4.


RM0090 Rev 21 311/1757



341


**DMA controller (DMA)** **RM0090**


**10.3.5** **DMA streams**


Each of the 8 DMA controller streams provides a unidirectional transfer link between a
source and a destination.


Each stream can be configured to perform:


      - Regular type transactions: memory-to-peripherals, peripherals-to-memory or memoryto-memory transfers


      - Double-buffer type transactions: double buffer transfers using two memory pointers for
the memory (while the DMA is reading/writing from/to a buffer, the application can
write/read to/from the other buffer).


The amount of data to be transferred (up to 65535) is programmable and related to the
source width of the peripheral that requests the DMA transfer connected to the peripheral
AHB port. The register that contains the amount of data items to be transferred is
decremented after each transaction.


**10.3.6** **Source, destination and transfer modes**


Both source and destination transfers can address peripherals and memories in the entire
4 GB area, at addresses comprised between 0x0000 0000 and 0xFFFF FFFF.


The direction is configured using the DIR[1:0] bits in the DMA_SxCR register and offers
three possibilities: memory-to-peripheral, peripheral-to-memory or memory-to-memory
transfers. _Table 45_ describes the corresponding source and destination addresses.


**Table 45. Source and destination address**

|Bits DIR[1:0] of the<br>DMA_SxCR register|Direction|Source address|Destination address|
|---|---|---|---|
|00|Peripheral-to-memory|DMA_SxPAR|DMA_SxM0AR|
|01|Memory-to-peripheral|DMA_SxM0AR|DMA_SxPAR|
|10|Memory-to-memory|DMA_SxPAR|DMA_SxM0AR|
|11|reserved|-|-|



When the data width (programmed in the PSIZE or MSIZE bits in the DMA_SxCR register)
is a half-word or a word, respectively, the peripheral or memory address written into the
DMA_SxPAR or DMA_SxM0AR/M1AR registers has to be aligned on a word or half-word
address boundary, respectively.


**Peripheral-to-memory mode**


_Figure 36_ describes this mode.


When this mode is enabled (by setting the bit EN in the DMA_SxCR register), each time a
peripheral request occurs, the stream initiates a transfer from the source to fill the FIFO.


When the threshold level of the FIFO is reached, the contents of the FIFO are drained and
stored into the destination.


The transfer stops once the DMA_SxNDTR register reaches zero, when the peripheral
requests the end of transfers (in case of a peripheral flow controller) or when the EN bit in
the DMA_SxCR register is cleared by software.


312/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


In direct mode (when the DMDIS value in the DMA_SxFCR register is ‘0’), the threshold
level of the FIFO is not used: after each single data transfer from the peripheral to the FIFO,
the corresponding data are immediately drained and stored into the destination.


The stream has access to the AHB source or destination port only if the arbitration of the
corresponding stream is won. This arbitration is performed using the priority defined for
each stream using the PL[1:0] bits in the DMA_SxCR register.


**Figure 36. Peripheral-to-memory mode**














|FIFO<br>level|Col2|
|---|---|
|FIFO<br>level||
|FIFO<br>level||
|FIFO<br>level||
|FIFO<br>level||
|FIFO<br>level||
|FIFO<br>level||
|FIFO<br>level||









1. For double-buffer mode.


**Memory-to-peripheral mode**


_Figure 37_ describes this mode.


When this mode is enabled (by setting the EN bit in the DMA_SxCR register), the stream
immediately initiates transfers from the source to entirely fill the FIFO.


Each time a peripheral request occurs, the contents of the FIFO are drained and stored into
the destination. When the level of the FIFO is lower than or equal to the predefined
threshold level, the FIFO is fully reloaded with data from the memory.


The transfer stops once the DMA_SxNDTR register reaches zero, when the peripheral
requests the end of transfers (in case of a peripheral flow controller) or when the EN bit in
the DMA_SxCR register is cleared by software.


In direct mode (when the DMDIS value in the DMA_SxFCR register is '0'), the threshold
level of the FIFO is not used. Once the stream is enabled, the DMA preloads the first data to
transfer into an internal FIFO. As soon as the peripheral requests a data transfer, the DMA
transfers the preloaded value into the configured destination. It then reloads again the


RM0090 Rev 21 313/1757



341


**DMA controller (DMA)** **RM0090**


empty internal FIFO with the next data to be transfer. The preloaded data size corresponds
to the value of the PSIZE bitfield in the DMA_SxCR register.


The stream has access to the AHB source or destination port only if the arbitration of the
corresponding stream is won. This arbitration is performed using the priority defined for
each stream using the PL[1:0] bits in the DMA_SxCR register.


**Figure 37. Memory-to-peripheral mode**














|FIFO<br>level|Col2|
|---|---|
|FIFO<br>level||
|FIFO<br>level||
|FIFO<br>level||
|FIFO<br>level||
|FIFO<br>level||
|FIFO<br>level||
|FIFO<br>level||











1. For double-buffer mode.


**Memory-to-memory mode**


The DMA channels can also work without being triggered by a request from a peripheral.
This is the memory-to-memory mode, described in _Figure 38_ .


When the stream is enabled by setting the Enable bit (EN) in the DMA_SxCR register, the
stream immediately starts to fill the FIFO up to the threshold level. When the threshold level
is reached, the FIFO contents are drained and stored into the destination.


The transfer stops once the DMA_SxNDTR register reaches zero or when the EN bit in the
DMA_SxCR register is cleared by software.


The stream has access to the AHB source or destination port only if the arbitration of the
corresponding stream is won. This arbitration is performed using the priority defined for
each stream using the PL[1:0] bits in the DMA_SxCR register.


_Note:_ _When memory-to-memory mode is used, the Circular and direct modes are not allowed._


_Only the DMA2 controller is able to perform memory-to-memory transfers._


314/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


**Figure 38. Memory-to-memory mode**














|FIFO<br>level|Col2|
|---|---|
|**FIFO**<br>level||
|**FIFO**<br>level||
|**FIFO**<br>level||
|**FIFO**<br>level||
|**FIFO**<br>level||
|**FIFO**<br>level||
|**FIFO**<br>level||









1. For double-buffer mode.


**10.3.7** **Pointer incrementation**


Peripheral and memory pointers can optionally be automatically post-incremented or kept
constant after each transfer depending on the PINC and MINC bits in the DMA_SxCR
register.


Disabling the Increment mode is useful when the peripheral source or destination data are
accessed through a single register.


If the Increment mode is enabled, the address of the next transfer is the address of the
previous one incremented by 1 (for bytes), 2 (for half-words) or 4 (for words) depending on
the data width programmed in the PSIZE or MSIZE bits in the DMA_SxCR register.


In order to optimize the packing operation, it is possible to fix the increment offset size for
the peripheral address whatever the size of the data transferred on the AHB peripheral port.
The PINCOS bit in the DMA_SxCR register is used to align the increment offset size with
the data size on the peripheral AHB port, or on a 32-bit address (the address is then
incremented by 4). The PINCOS bit has an impact on the AHB peripheral port only.


If PINCOS bit is set, the address of the next transfer is the address of the previous one
incremented by 4 (automatically aligned on a 32-bit address) whatever the PSIZE value.
The AHB memory port, however, is not impacted by this operation.


RM0090 Rev 21 315/1757



341


**DMA controller (DMA)** **RM0090**


**10.3.8** **Circular mode**


The Circular mode is available to handle circular buffers and continuous data flows (e.g.
ADC scan mode). This feature can be enabled using the CIRC bit in the DMA_SxCR
register.


When the circular mode is activated, the number of data items to be transferred is
automatically reloaded with the initial value programmed during the stream configuration
phase, and the DMA requests continue to be served.


_Note:_ _In the circular mode, it is mandatory to respect the following rule in case of a burst mode_
_configured for memory:_


_DMA_SxNDTR = Multiple of ((Mburst beat) × (Msize)/(Psize)), where:_


–
_(Mburst beat) = 4, 8 or 16 (depending on the MBURST bits in the DMA_SxCR_
_register)_


–
_((Msize)/(Psize)) = 1, 2, 4, 1/2 or 1/4 (Msize and Psize represent the MSIZE and_
_PSIZE bits in the DMA_SxCR register. They are byte dependent)_


–
_DMA_SxNDTR = Number of data items to transfer on the AHB peripheral port_


_For example: Mburst beat = 8 (INCR8), MSIZE = ‘00’ (byte) and PSIZE = ‘01’ (half-word), in_
_this case: DMA_SxNDTR must be a multiple of (8 × 1/2 = 4)._


_If this formula is not respected, the DMA behavior and data integrity are not guaranteed._


_NDTR must also be a multiple of the Peripheral burst size multiplied by the peripheral data_
_size, otherwise this could result in a bad DMA behavior._


**10.3.9** **Double buffer mode**


This mode is available for all the DMA1 and DMA2 streams.


The Double buffer mode is enabled by setting the DBM bit in the DMA_SxCR register.


A double-buffer stream works as a regular (single buffer) stream with the difference that it
has two memory pointers. When the Double buffer mode is enabled, the Circular mode is
automatically enabled (CIRC bit in DMA_SxCR is don’t care) and at each end of transaction,
the memory pointers are swapped.


In this mode, the DMA controller swaps from one memory target to another at each end of
transaction. This allows the software to process one memory area while the second memory
area is being filled/used by the DMA transfer. The double-buffer stream can work in both
directions (the memory can be either the source or the destination) as described in
_Table 46: Source and destination address registers in Double buffer mode (DBM=1)_ .


_Note:_ _In Double buffer mode, it is possible to update the base address for the AHB memory port_
_on-the-fly (_ DMA_SxM0AR or DMA_SxM1AR _) when the stream is enabled, by respecting the_
_following conditions:_


      - _When the CT bit is ‘0’ in the DMA_SxCR register, the DMA_SxM1AR register can be_
_written. Attempting to write to this register while CT = '1' sets an error flag (TEIF) and_
_the stream is automatically disabled._


      - _When the CT bit is ‘1’ in the DMA_SxCR register, the DMA_SxM0AR register can be_
_written. Attempting to write to this register while CT = '0', sets an error flag (TEIF) and_
_the stream is automatically disabled._


_To avoid any error condition, it is advised to change the base address as soon as the TCIF_
_flag is asserted because, at this point, the targeted memory must have changed from_


316/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


_memory 0 to 1 (or from 1 to 0) depending on the value of CT in the DMA_SxCR register in_
_accordance with one of the two above conditions._


_For all the other modes (except the Double buffer mode), the memory address registers are_
_write-protected as soon as the stream is enabled._


**Table 46. Source and destination address registers in Double buffer mode (DBM=1)**

|Bits DIR[1:0] of the<br>DMA_SxCR register|Direction|Source address|Destination address|
|---|---|---|---|
|00|Peripheral-to-memory|DMA_SxPAR|DMA_SxM0AR /<br>DMA_SxM1AR|
|01|Memory-to-peripheral|DMA_SxM0AR /<br>DMA_SxM1AR|DMA_SxPAR|
|10|Not allowed(1)|Not allowed(1)|Not allowed(1)|
|11|Reserved|-|-|



1. When the Double buffer mode is enabled, the Circular mode is automatically enabled. Since the memoryto-memory mode is not compatible with the Circular mode, when the Double buffer mode is enabled, it is
not allowed to configure the memory-to-memory mode.


**10.3.10** **Programmable data width, packing/unpacking, endianess**


The number of data items to be transferred has to be programmed into DMA_SxNDTR
(number of data items to transfer bit, NDT) before enabling the stream (except when the
flow controller is the peripheral, PFCTRL bit in DMA_SxCR is set).


When using the internal FIFO, the data widths of the source and destination data are
programmable through the PSIZE and MSIZE bits in the DMA_SxCR register (can be 8-,
16- or 32-bit).


When PSIZE and MSIZE are not equal:


      - The data width of the number of data items to transfer, configured in the DMA_SxNDTR
register is equal to the width of the peripheral bus (configured by the PSIZE bits in the
DMA_SxCR register). For instance, in case of peripheral-to-memory, memory-toperipheral or memory-to-memory transfers and if the PSIZE[1:0] bits are configured for
half-word, the number of bytes to be transferred is equal to 2 × NDT.


      - The DMA controller only copes with little-endian addressing for both source and
destination. This is described in _Table 47: Packing/unpacking & endian behavior (bit_
_PINC = MINC = 1)_ .


This packing/unpacking procedure may present a risk of data corruption when the operation
is interrupted before the data are completely packed/unpacked. So, to ensure data
coherence, the stream may be configured to generate burst transfers: in this case, each
group of transfers belonging to a burst are indivisible (refer to _Section 10.3.11: Single and_
_burst transfers_ ).


In direct mode (DMDIS = 0 in the DMA_SxFCR register), the packing/unpacking of data is
not possible. In this case, it is not allowed to have different source and destination transfer
data widths: both are equal and defined by the PSIZE bits in the DMA_SxCR MSIZE bits are
don’t care).


RM0090 Rev 21 317/1757



341


**DMA controller (DMA)** **RM0090**


**Table 47. Packing/unpacking & endian behavior (bit PINC = MINC = 1)**





















































|AHB<br>memory<br>port<br>width|AHB<br>peripheral<br>port width|Number<br>of data<br>items to<br>transfer<br>(NDT)|-<br>Memory<br>transfer<br>-number|Memory port<br>address / byte<br>lane|Peripher<br>al<br>transfer<br>number|Peripheral port address / byte lane|Col8|
|---|---|---|---|---|---|---|---|
|**AHB**<br>**memory**<br>**port**<br>**width**|**AHB**<br>**peripheral**<br>**port width**|**Number**<br>**of data**<br>**items to**<br>**transfer**<br>**(NDT)**<br><br>|-<br>**Memory**<br>**transfer**<br>**number**<br>-|**Memory port**<br>**address / byte**<br>**lane**|**Peripher**<br>**al**<br>**transfer**<br>**number**|**PINCOS = 1**|**PINCOS = 0**|
|8|8|4<br>|-<br>1<br>2<br>3<br>4|0x0 / B0[7:0]<br>0x1 / B1[7:0]<br>0x2 / B2[7:0]<br>0x3 / B3[7:0]|1<br>2<br>3<br>4|0x0 / B0[7:0]<br>0x4 / B1[7:0]<br>0x8 / B2[7:0]<br>0xC / B3[7:0]|0x0 / B0[7:0]<br>0x1 / B1[7:0]<br>0x2 / B2[7:0]<br>0x3 / B3[7:0]|
|8|16|2<br>|-<br>1<br>2<br>3<br>4|0x0 / B0[7:0]<br>0x1 / B1[7:0]<br>0x2 / B2[7:0]<br>0x3 / B3[7:0]|1<br>2|0x0 / B1|B0[15:0]<br>0x4 / B3|B2[15:0]|0x0 / B1|B0[15:0]<br>0x2 / B3|B2[15:0]|
|8|32|1<br>|-<br>1<br>2<br>3<br>4|0x0 / B0[7:0]<br>0x1 / B1[7:0]<br>0x2 / B2[7:0]<br>0x3 / B3[7:0]|1|0x0 / B3|B2|B1|B0[31:0]|0x0 / B3|B2|B1|B0[31:0]|
|16|8|4<br>|-<br>1<br>2|0x0 / B1|B0[15:0]<br>0x2 / B3|B2[15:0]|1<br>2<br>3<br>4|0x0 / B0[7:0]<br>0x4 / B1[7:0]<br>0x8 / B2[7:0]<br>0xC / B3[7:0]|0x0 / B0[7:0]<br>0x1 / B1[7:0]<br>0x2 / B2[7:0]<br>0x3 / B3[7:0]|
|16|16|2<br>|-<br>1<br>2|0x0 / B1|B0[15:0]<br>0x2 / B1|B0[15:0]|1<br>2|0x0 / B1|B0[15:0]<br>0x4 / B3|B2[15:0]|0x0 / B1|B0[15:0]<br>0x2 / B3|B2[15:0]|
|16|32|1<br>|-<br>1<br>2|0x0 / B1|B0[15:0]<br>0x2 / B3|B2[15:0]|1|0x0 / B3|B2|B1|B0[31:0]|0x0 / B3|B2|B1|B0[31:0]|
|32|8|4<br>|-<br>1|0x0 / B3|B2|B1|B0[31:0]|1<br>2<br>3<br>4|0x0 / B0[7:0]<br>0x4 / B1[7:0]<br>0x8 / B2[7:0]<br>0xC / B3[7:0]|0x0 / B0[7:0]<br>0x1 / B1[7:0]<br>0x2 / B2[7:0]<br>0x3 / B3[7:0]|
|32|16|2<br>|-<br>1|0x0 /B3|B2|B1|B0[31:0]|1<br>2|0x0 / B1|B0[15:0]<br>0x4 / B3|B2[15:0]|0x0 / B1|B0[15:0]<br>0x2 / B3|B2[15:0]|
|32|32|1<br>|- 1|0x0 /B3|B2|B1|B0 [31:0]|1|0x0 /B3|B2|B1|B0 [31:0]|0x0 / B3|B2|B1|B0[31:0]|


_Note:_ _Peripheral port may be the source or the destination (it could also be the memory source in_
_the case of memory-to-memory transfer)._


PSIZE, MSIZE and NDT[15:0] have to be configured so as to ensure that the last transfer is
not incomplete. This can occur when the data width of the peripheral port (PSIZE bits) is
lower than the data width of the memory port (MSIZE bits). This constraint is summarized in
_Table 48_ .


318/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


**Table 48. Restriction on NDT versus PSIZE and MSIZE**

|PSIZE[1:0] of DMA_SxCR|MSIZE[1:0] of DMA_SxCR|NDT[15:0] of DMA_SxNDTR|
|---|---|---|
|00 (8-bit)|01 (16-bit)|must be a multiple of 2|
|00 (8-bit)|10 (32-bit)|must be a multiple of 4|
|01 (16-bit)|10 (32-bit)|must be a multiple of 2|



**10.3.11** **Single and burst transfers**


The DMA controller can generate single transfers or incremental burst transfers of 4, 8 or 16
beats.


The size of the burst is configured by software independently for the two AHB ports by using
the MBURST[1:0] and PBURST[1:0] bits in the DMA_SxCR register.


The burst size indicates the number of beats in the burst, not the number of bytes
transferred.


To ensure data coherence, each group of transfers that form a burst are indivisible: AHB
transfers are locked and the arbiter of the AHB bus matrix does not degrant the DMA master
during the sequence of the burst transfer.


Depending on the single or burst configuration, each DMA request initiates a different
number of transfers on the AHB peripheral port:


      - When the AHB peripheral port is configured for single transfers, each DMA request
generates a data transfer of a byte, half-word or word depending on the PSIZE[1:0] bits
in the DMA_SxCR register


      - When the AHB peripheral port is configured for burst transfers, each DMA request
generates 4,8 or 16 beats of byte, half word or word transfers depending on the
PBURST[1:0] and PSIZE[1:0] bits in the DMA_SxCR register.


The same as above has to be considered for the AHB memory port considering the
MBURST and MSIZE bits.


In direct mode, the stream can only generate single transfers and the MBURST[1:0] and
PBURST[1:0] bits are forced by hardware.


The address pointers (DMA_SxPAR or DMA_SxM0AR registers) must be chosen so as to
ensure that all transfers within a burst block are aligned on the address boundary equal to
the size of the transfer.


The burst configuration has to be selected in order to respect the AHB protocol, where
bursts must _not_ cross the 1 KB address boundary because the minimum address space that
can be allocated to a single slave is 1 KB. This means that the 1 KB address boundary
should not be crossed by a burst block transfer, otherwise an AHB error would be
generated, that is not reported by the DMA registers.


RM0090 Rev 21 319/1757



341


**DMA controller (DMA)** **RM0090**


**10.3.12** **FIFO**


**FIFO structure**


The FIFO is used to temporarily store data coming from the source before transmitting them
to the destination.


Each stream has an independent 4-word FIFO and the threshold level is softwareconfigurable between 1/4, 1/2, 3/4 or full.


To enable the use of the FIFO threshold level, the direct mode must be disabled by setting
the DMDIS bit in the DMA_SxFCR register.


The structure of the FIFO differs depending on the source and destination data widths, and
is described in _Figure 39: FIFO structure_ .


**Figure 39. FIFO structure**






















|B15|B 11|B7|B3|
|---|---|---|---|
|B14|B10|B6|B2|
|B13|B9|B5|B1|
|B12<br>W3|B8<br>W2|B4<br>W1|B0<br>W0|
































|B15|B 11|B7|B3|
|---|---|---|---|
|B14<br>H7|B10<br>H5|B6<br>H3|B2<br>H1|
|B13|B9|B5|B1|
|B12<br>H6|B8<br>H4|B4<br>H2|B0<br>H0|




















|H7|H5|H3|H1|
|---|---|---|---|
|W3<br>H6|W2<br>H4|W1<br>H2|H0<br>W0|








































|B15|B 11|B7|B3|
|---|---|---|---|
|B14<br>H7|B10<br>H5|B6<br>H3|B2<br>H1|
|B13|B9|B5|B1|
|B12<br>H6|B8<br>H4|B4<br>H2|B0<br>H0|





320/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


**FIFO threshold and burst configuration**


Caution is required when choosing the FIFO threshold (bits FTH[1:0] of the DMA_SxFCR
register) and the size of the memory burst (MBURST[1:0] of the DMA_SxCR register): The
content pointed by the FIFO threshold must exactly match to an integer number of memory
burst transfers. If this is not in the case, a FIFO error (flag FEIFx of the DMA_HISR or
DMA_LISR register) is generated when the stream is enabled, then the stream is
automatically disabled. The allowed and forbidden configurations are described in the
_Table 49: FIFO threshold configurations_ .


**Table 49. FIFO threshold configurations**












|MSIZE|FIFO level|MBURST = INCR4|MBURST = INCR8|MBURST = INCR16|
|---|---|---|---|---|
|Byte|1/4|1 burst of 4 beats|forbidden|forbidden|
|Byte|1/2|2 bursts of 4 beats|1 burst of 8 beats|1 burst of 8 beats|
|Byte|3/4|3 bursts of 4 beats|forbidden|forbidden|
|Byte|Full|4 bursts of 4 beats|2 bursts of 8 beats|1 burst of 16 beats|
|Half-word|1/4|forbidden|forbidden|forbidden|
|Half-word|1/2|1 burst of 4 beats|1 burst of 4 beats|1 burst of 4 beats|
|Half-word|3/4|forbidden|forbidden|forbidden|
|Half-word|Full|2 bursts of 4 beats|1 burst of 8 beats|1 burst of 8 beats|
|Word|1/4|forbidden|forbidden|forbidden|
|Word|1/2|1/2|1/2|1/2|
|Word|3/4|3/4|3/4|3/4|
|Word|Full|1 burst of 4 beats|1 burst of 4 beats|1 burst of 4 beats|



In all cases, the burst size multiplied by the data size must not exceed the FIFO size (data
size can be: 1 (byte), 2 (half-word) or 4 (word)).


Incomplete Burst transfer at the end of a DMA transfer may happen if one of the following
conditions occurs:


      - For the AHB peripheral port configuration: the total number of data items (set in the
DMA_SxNDTR register) is not a multiple of the burst size multiplied by the data size


      - For the AHB memory port configuration: the number of remaining data items in the
FIFO to be transferred to the memory is not a multiple of the burst size multiplied by the
data size


In such cases, the remaining data to be transferred is managed in single mode by the DMA,
even if a burst transaction was requested during the DMA stream configuration.


_Note:_ _When burst transfers are requested on the peripheral AHB port and the FIFO is used_
_(DMDIS = 1 in the DMA_SxCR register), it is mandatory to respect the following rule to_
_avoid permanent underrun or overrun conditions, depending on the DMA stream direction:_


_If (PBURST × PSIZE) = FIFO_SIZE (4 words), FIFO_Threshold = 3/4 is forbidden with_
_PSIZE = 1, 2 or 4 and PBURST = 4, 8 or 16._


_This rule ensures that enough FIFO space at a time is free to serve the request from the_
_peripheral._


RM0090 Rev 21 321/1757



341


**DMA controller (DMA)** **RM0090**


**FIFO flush**


The FIFO can be flushed when the stream is disabled by resetting the EN bit in the
DMA_SxCR register and when the stream is configured to manage peripheral-to-memory or
memory-to-memory transfers: If some data are still present in the FIFO when the stream is
disabled, the DMA controller continues transferring the remaining data to the destination
(even though stream is effectively disabled). When this flush is completed, the transfer
complete status bit (TCIFx) in the DMA_LISR or DMA_HISR register is set.


The remaining data counter DMA_SxNDTR keeps the value in this case to indicate how
many data items are currently available in the destination memory.


Note that during the FIFO flush operation, if the number of remaining data items in the FIFO
to be transferred to memory (in bytes) is less than the memory data width (for example 2
bytes in FIFO while MSIZE is configured to word), data is sent with the data width set in the
MSIZE bit in the DMA_SxCR register. This means that memory is written with an undesired
value. The software may read the DMA_SxNDTR register to determine the memory area
that contains the good data (start address and last address).


If the number of remaining data items in the FIFO is lower than a burst size (if the MBURST
bits in DMA_SxCR register are set to configure the stream to manage burst on the AHB
memory port), single transactions are generated to complete the FIFO flush.


**Direct mode**


By default, the FIFO operates in direct mode (DMDIS bit in the DMA_SxFCR is reset) and
the FIFO threshold level is not used. This mode is useful when the system requires an
immediate and single transfer to or from the memory after each DMA request.


When the DMA is configured in direct mode (FIFO disabled), to transfer data in memory-toperipheral mode, the DMA preloads one data from the memory to the internal FIFO to
ensure an immediate data transfer as soon as a DMA request is triggered by a peripheral.


To avoid saturating the FIFO, it is recommended to configure the corresponding stream with
a high priority.


This mode is restricted to transfers where:


      - The source and destination transfer widths are equal and both defined by the
PSIZE[1:0] bits in DMA_SxCR (MSIZE[1:0] bits are don’t care)


      - Burst transfers are not possible (PBURST[1:0] and MBURST[1:0] bits in DMA_SxCR
are don’t care)


Direct mode must not be used when implementing memory-to-memory transfers.


**10.3.13** **DMA transfer completion**


Different events can generate an end of transfer by setting the TCIFx bit in the DMA_LISR
or DMA_HISR status register:


      - In DMA flow controller mode:


–
The DMA_SxNDTR counter has reached zero in the memory-to-peripheral mode


–
The stream is disabled before the end of transfer (by clearing the EN bit in the
DMA_SxCR register) and (when transfers are peripheral-to-memory or memory

322/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


to-memory) all the remaining data have been flushed from the FIFO into the

memory


      - In Peripheral flow controller mode:


–
The last external burst or single request has been generated from the peripheral
and (when the DMA is operating in peripheral-to-memory mode) the remaining
data have been transferred from the FIFO into the memory


–
The stream is disabled by software, and (when the DMA is operating in peripheralto-memory mode) the remaining data have been transferred from the FIFO into
the memory


_Note:_ _The transfer completion is dependent on the remaining data in FIFO to be transferred into_
_memory only in the case of peripheral-to-memory mode. This condition is not applicable in_
_memory-to-peripheral mode._


If the stream is configured in noncircular mode, after the end of the transfer (that is when the
number of data to be transferred reaches zero), the DMA is stopped (EN bit in DMA_SxCR
register is cleared by Hardware) and no DMA request is served unless the software
reprograms the stream and re-enables it (by setting the EN bit in the DMA_SxCR register).


**10.3.14** **DMA transfer suspension**


At any time, a DMA transfer can be suspended to be restarted later on or to be definitively
disabled before the end of the DMA transfer.


There are two cases:


      - The stream disables the transfer with no later-on restart from the point where it was
stopped. There is no particular action to do, except to clear the EN bit in the
DMA_SxCR register to disable the stream. The stream may take time to be disabled
(ongoing transfer is completed first). The transfer complete interrupt flag (TCIF in the
DMA_LISR or DMA_HISR register) is set in order to indicate the end of transfer. The
value of the EN bit in DMA_SxCR is now ‘0’ to confirm the stream interruption. The
DMA_SxNDTR register contains the number of remaining data items at the moment
when the stream was stopped so that the software can determine how many data items
have been transferred before the stream was interrupted.


      - The stream suspends the transfer before the number of remaining data items to be
transferred in the DMA_SxNDTR register reaches 0. The aim is to restart the transfer
later by re-enabling the stream. In order to restart from the point where the transfer was
stopped, the software has to read the DMA_SxNDTR register after disabling the stream
by writing the EN bit in DMA_SxCR register (and then checking that it is at ‘0’) to know
the number of data items already collected. Then:


–
The peripheral and/or memory addresses have to be updated in order to adjust
the address pointers


–
The SxNDTR register has to be updated with the remaining number of data items
to be transferred (the value read when the stream was disabled)


–
The stream may then be re-enabled to restart the transfer from the point it was
stopped


_Note:_ _Note that a Transfer complete interrupt flag (TCIF in DMA_LISR or DMA_HISR) is set to_
_indicate the end of transfer due to the stream interruption._


RM0090 Rev 21 323/1757



341


**DMA controller (DMA)** **RM0090**


**10.3.15** **Flow controller**


The entity that controls the number of data to be transferred is known as the flow controller.
This flow controller is configured independently for each stream using the PFCTRL bit in the
DMA_SxCR register.


The flow controller can be:


      - The DMA controller: in this case, the number of data items to be transferred is
programmed by software into the DMA_SxNDTR register before the DMA stream is
enabled.


      - The peripheral source or destination: this is the case when the number of data items to
be transferred is unknown. The peripheral indicates by hardware to the DMA controller
when the last data are being transferred. This feature is only supported for peripherals
which are able to signal the end of the transfer, that is:


– SDIO


When the peripheral flow controller is used for a given stream, the value written into the
DMA_SxNDTR has no effect on the DMA transfer. Actually, whatever the value written, it is
forced by hardware to 0xFFFF as soon as the stream is enabled, to respect the following
schemes:


      - Anticipated stream interruption: EN bit in DMA_SxCR register is reset to 0 by the
software to stop the stream before the last data hardware signal (single or burst) is sent
by the peripheral. In such a case, the stream is switched off and the FIFO flush is
triggered in the case of a peripheral-to-memory DMA transfer. The TCIFx flag of the
corresponding stream is set in the status register to indicate the DMA completion. To
know the number of data items transferred during the DMA transfer, read the
DMA_SxNDTR register and apply the following formula:


–
Number_of_data_transferred = 0xFFFF – DMA_SxNDTR


      - Normal stream interruption due to the reception of a last data hardware signal: the
stream is automatically interrupted when the peripheral requests the last transfer
(single or burst) and when this transfer is complete. the TCIFx flag of the corresponding
stream is set in the status register to indicate the DMA transfer completion. To know the
number of data items transferred, read the DMA_SxNDTR register and apply the same
formula as above.


      - The DMA_SxNDTR register reaches 0: the TCIFx flag of the corresponding stream is
set in the status register to indicate the forced DMA transfer completion. The stream is
automatically switched off even though the last data hardware signal (single or burst)
has not been yet asserted. The already transferred data are not lost. This means that a
maximum of 65535 data items can be managed by the DMA in a single transaction,
even in peripheral flow control mode.


_Note:_ _When configured in memory-to-memory mode, the DMA is always the flow controller and_
_the PFCTRL bit is forced to 0 by hardware._


_The Circular mode is forbidden in the peripheral flow controller mode._


324/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


**10.3.16** **Summary of the possible DMA configurations**


_Table 50_ summarizes the different possible DMA configurations.


**Table 50. Possible DMA configurations**








|DMA transfer<br>mode|Source|Destination|Flow<br>controller|Circular<br>mode|Transfer<br>type|Direct<br>mode|Double<br>buffer mode|
|---|---|---|---|---|---|---|---|
|Peripheral-to-<br>memory|AHB<br>peripheral port|AHB<br>memory port|DMA|possible|single|possible|possible|
|Peripheral-to-<br>memory|AHB<br>peripheral port|AHB<br>memory port|DMA|possible|burst|forbidden|forbidden|
|Peripheral-to-<br>memory|AHB<br>peripheral port|AHB<br>memory port|Peripheral|forbidden|single|possible|forbidden|
|Peripheral-to-<br>memory|AHB<br>peripheral port|AHB<br>memory port|Peripheral|forbidden|burst|forbidden|forbidden|
|Memory-to-<br>peripheral|AHB<br>memory port|AHB<br>peripheral port|DMA|possible|single|possible|possible|
|Memory-to-<br>peripheral|AHB<br>memory port|AHB<br>peripheral port|DMA|possible|burst|forbidden|forbidden|
|Memory-to-<br>peripheral|AHB<br>memory port|AHB<br>peripheral port|Peripheral|forbidden|single|possible|forbidden|
|Memory-to-<br>peripheral|AHB<br>memory port|AHB<br>peripheral port|Peripheral|forbidden|burst|forbidden|forbidden|
|Memory-to-<br>memory|AHB<br>peripheral port|AHB<br>memory port|DMA only|forbidden|single|forbidden|forbidden|
|Memory-to-<br>memory|AHB<br>peripheral port|AHB<br>memory port|DMA only|forbidden|burst|burst|burst|



**10.3.17** **Stream configuration procedure**


The following sequence should be followed to configure a DMA stream x (where x is the
stream number):


1. If the stream is enabled, disable it by resetting the EN bit in the DMA_SxCR register,
then read this bit in order to confirm that there is no ongoing stream operation. Writing
this bit to 0 is not immediately effective since it is actually written to 0 once all the
current transfers have finished. When the EN bit is read as 0, this means that the
stream is ready to be configured. It is therefore necessary to wait for the EN bit to be
cleared before starting any stream configuration. All the stream dedicated bits set in the
status register (DMA_LISR and DMA_HISR) from the previous data block DMA
transfer should be cleared before the stream can be re-enabled.


2. Set the peripheral port register address in the DMA_SxPAR register. The data are
moved from/ to this address to/ from the peripheral port after the peripheral event.


3. Set the memory address in the DMA_SxMA0R register (and in the DMA_SxMA1R
register in the case of a double buffer mode). The data are written to or read from this
memory after the peripheral event.


4. Configure the total number of data items to be transferred in the DMA_SxNDTR
register. After each peripheral event or each beat of the burst, this value is
decremented.


5. Select the DMA channel (request) using CHSEL[2:0] in the DMA_SxCR register.


6. If the peripheral is intended to be the flow controller and if it supports this feature, set
the PFCTRL bit in the DMA_SxCR register.


7. Configure the stream priority using the PL[1:0] bits in the DMA_SxCR register.


8. Configure the FIFO usage (enable or disable, threshold in transmission and reception)


9. Configure the data transfer direction, peripheral and memory incremented/fixed mode,
single or burst transactions, peripheral and memory data widths, Circular mode,


RM0090 Rev 21 325/1757



341


**DMA controller (DMA)** **RM0090**


Double buffer mode and interrupts after half and/or full transfer, and/or errors in the
DMA_SxCR register.


10. Activate the stream by setting the EN bit in the DMA_SxCR register.


As soon as the stream is enabled, it can serve any DMA request from the peripheral
connected to the stream.


Once half the data have been transferred on the AHB destination port, the half-transfer flag
(HTIF) is set and an interrupt is generated if the half-transfer interrupt enable bit (HTIE) is
set. At the end of the transfer, the transfer complete flag (TCIF) is set and an interrupt is
generated if the transfer complete interrupt enable bit (TCIE) is set.


**Warning:** **To switch off a peripheral connected to a DMA stream**
**request, it is mandatory to, first, switch off the DMA stream to**
**which the peripheral is connected, then to wait for EN bit = 0.**
**Only then can the peripheral be safely disabled.**


**10.3.18** **Error management**


The DMA controller can detect the following errors:


      - **Transfer error** : the transfer error interrupt flag (TEIFx) is set when:


–
A bus error occurs during a DMA read or a write access


–
A write access is requested by software on a memory address register in Double
buffer mode whereas the stream is enabled and the current target memory is the
one impacted by the write into the memory address register (refer to
_Section 10.3.9: Double buffer mode_ )


      - **FIFO error** : the FIFO error interrupt flag (FEIFx) is set if:


– A FIFO underrun condition is detected


–
A FIFO overrun condition is detected (no detection in memory-to-memory mode
because requests and transfers are internally managed by the DMA)


–
The stream is enabled while the FIFO threshold level is not compatible with the
size of the memory burst (refer to _Table 49: FIFO threshold configurations_ )


      - **Direct mode error** : the direct mode error interrupt flag (DMEIFx) can only be set in the
peripheral-to-memory mode while operating in direct mode and when the MINC bit in
the DMA_SxCR register is cleared. This flag is set when a DMA request occurs while
the previous data have not yet been fully transferred into the memory (because the
memory bus was not granted). In this case, the flag indicates that 2 data items were be
transferred successively to the same destination address, which could be an issue if
the destination is not able to manage this situation


In direct mode, the FIFO error flag can also be set under the following conditions:


      - In the peripheral-to-memory mode, the FIFO can be saturated (overrun) if the memory
bus is not granted for several peripheral requests


      - In the memory-to-peripheral mode, an underrun condition may occur if the memory bus
has not been granted before a peripheral request occurs


If the TEIFx or the FEIFx flag is set due to incompatibility between burst size and FIFO
threshold level, the faulty stream is automatically disabled through a hardware clear of its
EN bit in the corresponding stream configuration register (DMA_SxCR).


326/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


If the DMEIFx or the FEIFx flag is set due to an overrun or underrun condition, the faulty
stream is not automatically disabled and it is up to the software to disable or not the stream
by resetting the EN bit in the DMA_SxCR register. This is because there is no data loss
when this kind of errors occur.


When the stream's error interrupt flag (TEIF, FEIF, DMEIF) in the DMA_LISR or DMA_HISR
register is set, an interrupt is generated if the corresponding interrupt enable bit (TEIE,
FEIE, DMIE) in the DMA_SxCR or DMA_SxFCR register is set.


_Note:_ _When a FIFO overrun or underrun condition occurs, the data are not lost because the_
_peripheral request is not acknowledged by the stream until the overrun or underrun_
_condition is cleared. If this acknowledge takes too much time, the peripheral itself may_
_detect an overrun or underrun condition of its internal buffer and data might be lost._

## **10.4 DMA interrupts**


For each DMA stream, an interrupt can be produced on the following events:


      - Half-transfer reached


      - Transfer complete


      - Transfer error


      - Fifo error (overrun, underrun or FIFO level error)


      - Direct mode error


Separate interrupt enable control bits are available for flexibility as shown in _Table 51_ .


**Table 51. DMA interrupt requests**

|Interrupt event|Event flag|Enable control bit|
|---|---|---|
|Half-transfer|HTIF|HTIE|
|Transfer complete|TCIF|TCIE|
|Transfer error|TEIF|TEIE|
|FIFO overrun/underrun|FEIF|FEIE|
|Direct mode error|DMEIF|DMEIE|



_Note:_ _Before setting an Enable control bit to ‘1’, the corresponding event flag should be cleared,_
_otherwise an interrupt is immediately generated._


RM0090 Rev 21 327/1757



341


**DMA controller (DMA)** **RM0090**

## **10.5 DMA registers**


The DMA registers have to be accessed by words (32 bits).


**10.5.1** **DMA low interrupt status register (DMA_LISR)**


Address offset: 0x00


Reset value: 0x0000 0000










|31 30 29 28|Col2|Col3|Col4|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|Reserved|Reserved|Reserved|TCIF3|HTIF3|TEIF3|DMEIF3|Reserv<br>ed|FEIF3|TCIF2|HTIF2|TEIF2|DMEIF2|Reserv<br>ed|FEIF2|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|










|15 14 13 12|Col2|Col3|Col4|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|Reserved|Reserved|Reserved|TCIF1|HTIF1|TEIF1|DMEIF1|Reserv<br>ed|FEIF1|TCIF0|HTIF0|TEIF0|DMEIF0|Reserv<br>ed|FEIF0|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:28, 15:12 Reserved, must be kept at reset value.


Bits 27, 21, 11, 5 **TCIFx** : Stream x transfer complete interrupt flag (x = 3..0)

This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_LIFCR register.
0: No transfer complete event on stream x
1: A transfer complete event occurred on stream x


Bits 26, 20, 10, 4 **HTIFx** : Stream x half transfer interrupt flag (x=3..0)

This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_LIFCR register.

0: No half transfer event on stream x

1: A half transfer event occurred on stream x


Bits 25, 19, 9, 3 **TEIFx** : Stream x transfer error interrupt flag (x=3..0)

This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_LIFCR register.

0: No transfer error on stream x

1: A transfer error occurred on stream x


Bits 24, 18, 8, 2 **DMEIFx** : Stream x direct mode error interrupt flag (x=3..0)

This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_LIFCR register.

0: No Direct Mode Error on stream x

1: A Direct Mode Error occurred on stream x


Bits 23, 17, 7, 1 Reserved, must be kept at reset value.


Bits 22, 16, 6, 0 **FEIFx** : Stream x FIFO error interrupt flag (x=3..0)

This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_LIFCR register.

0: No FIFO Error event on stream x

1: A FIFO Error event occurred on stream x


328/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


**10.5.2** **DMA high interrupt status register (DMA_HISR)**


Address offset: 0x04


Reset value: 0x0000 0000










|31 30 29 28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|TCIF7|HTIF7|TEIF7|DMEIF7|Reserv<br>ed|FEIF7|TCIF6|HTIF6|TEIF6|DMEIF6|Reserv<br>ed|FEIF6|
|Reserved|r|r|r|r|r|r|r|r|r|r|r|r|









|15 14 13 12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|TCIF5|HTIF5|TEIF5|DMEIF5|Reserv<br>ed|FEIF5|TCIF4|HTIF4|TEIF4|DMEIF4|Reserv<br>ed|FEIF4|
|Reserved|r|r|r|r|r|r|r|r|r|r|r|r|


Bits 31:28, 15:12 Reserved, must be kept at reset value.


Bits 27, 21, 11, 5 **TCIFx** : Stream x transfer complete interrupt flag (x=7..4)

This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_HIFCR register.
0: No transfer complete event on stream x
1: A transfer complete event occurred on stream x


Bits 26, 20, 10, 4 **HTIFx** : Stream x half transfer interrupt flag (x=7..4)

This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_HIFCR register.

0: No half transfer event on stream x

1: A half transfer event occurred on stream x


Bits 25, 19, 9, 3 **TEIFx** : Stream x transfer error interrupt flag (x=7..4)

This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_HIFCR register.

0: No transfer error on stream x

1: A transfer error occurred on stream x


Bits 24, 18, 8, 2 **DMEIFx** : Stream x direct mode error interrupt flag (x=7..4)

This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_HIFCR register.

0: No Direct mode error on stream x

1: A Direct mode error occurred on stream x


Bits 23, 17, 7, 1 Reserved, must be kept at reset value.


Bits 22, 16, 6, 0 **FEIFx** : Stream x FIFO error interrupt flag (x=7..4)

This bit is set by hardware. It is cleared by software writing 1 to the corresponding bit in the
DMA_HIFCR register.

0: No FIFO error event on stream x

1: A FIFO error event occurred on stream x


RM0090 Rev 21 329/1757



341


**DMA controller (DMA)** **RM0090**


**10.5.3** **DMA low interrupt flag clear register (DMA_LIFCR)**


Address offset: 0x08


Reset value: 0x0000 0000

|31 30 29 28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|CTCIF3|CHTIF3|CTEIF3|CDMEIF3|Reserved|CFEIF3|CTCIF2|CHTIF2|CTEIF2|CDMEIF2|Reserved|CFEIF2|
|Reserved|w|w|w|w|w|w|w|w|w|w|w|w|


|15 14 13 12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|CTCIF1|CHTIF1|CTEIF1|CDMEIF1|Reserved|CFEIF1|CTCIF0|CHTIF0|CTEIF0|CDMEIF0|Reserved|CFEIF0|
|Reserved|w|w|w|w|w|w|w|w|w|w|w|w|



Bits 31:28, 15:12 Reserved, must be kept at reset value.


Bits 27, 21, 11, 5 **CTCIFx** : Stream x clear transfer complete interrupt flag (x = 3..0)

Writing 1 to this bit clears the corresponding TCIFx flag in the DMA_LISR register


Bits 26, 20, 10, 4 **CHTIFx** : Stream x clear half transfer interrupt flag (x = 3..0)

Writing 1 to this bit clears the corresponding HTIFx flag in the DMA_LISR register


Bits 25, 19, 9, 3 **CTEIFx** : Stream x clear transfer error interrupt flag (x = 3..0)

Writing 1 to this bit clears the corresponding TEIFx flag in the DMA_LISR register


Bits 24, 18, 8, 2 **CDMEIFx** : Stream x clear direct mode error interrupt flag (x = 3..0)

Writing 1 to this bit clears the corresponding DMEIFx flag in the DMA_LISR register


Bits 23, 17, 7, 1 Reserved, must be kept at reset value.


Bits 22, 16, 6, 0 **CFEIFx** : Stream x clear FIFO error interrupt flag (x = 3..0)

Writing 1 to this bit clears the corresponding CFEIFx flag in the DMA_LISR register


**10.5.4** **DMA high interrupt flag clear register (DMA_HIFCR)**


Address offset: 0x0C


Reset value: 0x0000 0000

|31 30 29 28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|CTCIF7|CHTIF7|CTEIF7|CDMEIF7|Reserved|CFEIF7|CTCIF6|CHTIF6|CTEIF6|CDMEIF6|Reserved|CFEIF6|
|Reserved|w|w|w|w|w|w|w|w|w|w|w|w|


|15 14 13 12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|CTCIF5|CHTIF5|CTEIF5|CDMEIF5|Reserved|CFEIF5|CTCIF4|CHTIF4|CTEIF4|CDMEIF4|Reserved|CFEIF4|
|Reserved|w|w|w|w|w|w|w|w|w|w|w|w|



Bits 31:28, 15:12 Reserved, must be kept at reset value.


Bits 27, 21, 11, 5 **CTCIFx** : Stream x clear transfer complete interrupt flag (x = 7..4)

Writing 1 to this bit clears the corresponding TCIFx flag in the DMA_HISR register


Bits 26, 20, 10, 4 **CHTIFx** : Stream x clear half transfer interrupt flag (x = 7..4)

Writing 1 to this bit clears the corresponding HTIFx flag in the DMA_HISR register


Bits 25, 19, 9, 3 **CTEIFx** : Stream x clear transfer error interrupt flag (x = 7..4)

Writing 1 to this bit clears the corresponding TEIFx flag in the DMA_HISR register


330/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


Bits 24, 18, 8, 2 **CDMEIFx** : Stream x clear direct mode error interrupt flag (x = 7..4)

Writing 1 to this bit clears the corresponding DMEIFx flag in the DMA_HISR register


Bits 23, 17, 7, 1 Reserved, must be kept at reset value.


Bits 22, 16, 6, 0 **CFEIFx** : Stream x clear FIFO error interrupt flag (x = 7..4)

Writing 1 to this bit clears the corresponding CFEIFx flag in the DMA_HISR register


**10.5.5** **DMA stream x configuration register (DMA_SxCR) (x = 0..7)**


This register is used to configure the concerned stream.


Address offset: 0x10 + 0x18 × _stream number_


Reset value: 0x0000 0000








|31 30 29 28|27 26 25|Col3|Col4|24 23|Col6|22 21|Col8|20|19|18|17 16|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|CHSEL[2:0]|CHSEL[2:0]|CHSEL[2:0]|MBURST [1:0]|MBURST [1:0]|PBURST[1:0]|PBURST[1:0]|Reser-<br>ved|CT|DBM|PL[1:0]|PL[1:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



|15|14 13|Col3|12 11|Col5|10|9|8|7 6|Col10|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PINCOS|MSIZE[1:0]|MSIZE[1:0]|PSIZE[1:0]|PSIZE[1:0]|MINC|PINC|CIRC|DIR[1:0]|DIR[1:0]|PFCTRL|TCIE|HTIE|TEIE|DMEIE|EN|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:28 Reserved, must be kept at reset value.


Bits 27:25 **CHSEL[2:0]** : Channel selection

These bits are set and cleared by software.

000: channel 0 selected

001: channel 1 selected

010: channel 2 selected

011: channel 3 selected

100: channel 4 selected

101: channel 5 selected

110: channel 6 selected

111: channel 7 selected

These bits are protected and can be written only if EN is ‘0’


Bits 24:23 **MBURST** : Memory burst transfer configuration

These bits are set and cleared by software.
00: single transfer
01: INCR4 (incremental burst of 4 beats)
10: INCR8 (incremental burst of 8 beats)
11: INCR16 (incremental burst of 16 beats)
These bits are protected and can be written only if EN is ‘0’
In direct mode, these bits are forced to 0x0 by hardware as soon as bit EN= '1'.


Bits 22:21 **PBURST[1:0]** : Peripheral burst transfer configuration

These bits are set and cleared by software.
00: single transfer
01: INCR4 (incremental burst of 4 beats)
10: INCR8 (incremental burst of 8 beats)
11: INCR16 (incremental burst of 16 beats)
These bits are protected and can be written only if EN is ‘0’
In direct mode, these bits are forced to 0x0 by hardware.


Bit 20 Reserved, must be kept at reset value.


RM0090 Rev 21 331/1757



341


**DMA controller (DMA)** **RM0090**


Bit 19 **CT** : Current target (only in double buffer mode)

This bits is set and cleared by hardware. It can also be written by software.

0: The current target memory is Memory 0 (addressed by the DMA_SxM0AR pointer)
1: The current target memory is Memory 1 (addressed by the DMA_SxM1AR pointer)
This bit can be written only if EN is ‘0’ to indicate the target memory area of the first transfer.
Once the stream is enabled, this bit operates as a status flag indicating which memory area
is the current target.


Bit 18 **DBM** : Double buffer mode

This bits is set and cleared by software.
0: No buffer switching at the end of transfer
1: Memory target switched at the end of the DMA transfer
This bit is protected and can be written only if EN is ‘0’.


Bits 17:16 **PL[1:0]** : Priority level

These bits are set and cleared by software.

00: Low

01: Medium

10: High
11: Very high
These bits are protected and can be written only if EN is ‘0’.


Bit 15 **PINCOS** : Peripheral increment offset size

This bit is set and cleared by software
0: The offset size for the peripheral address calculation is linked to the PSIZE
1: The offset size for the peripheral address calculation is fixed to 4 (32-bit alignment).
This bit has no meaning if bit PINC = '0'.
This bit is protected and can be written only if EN = '0'.
This bit is forced low by hardware when the stream is enabled (bit EN = '1') if the direct
mode is selected or if PBURST are different from “00”.


Bits 14:13 **MSIZE[1:0]** : Memory data size

These bits are set and cleared by software.
00: byte (8-bit)
01: half-word (16-bit)
10: word (32-bit)
11: reserved

These bits are protected and can be written only if EN is ‘0’.
In direct mode, MSIZE is forced by hardware to the same value as PSIZE as soon as bit EN
= '1'.


Bits 12:11 **PSIZE[1:0]** : Peripheral data size

These bits are set and cleared by software.
00: Byte (8-bit)
01: Half-word (16-bit)
10: Word (32-bit)
11: reserved

These bits are protected and can be written only if EN is ‘0’


Bit 10 **MINC** : Memory increment mode

This bit is set and cleared by software.
0: Memory address pointer is fixed
1: Memory address pointer is incremented after each data transfer (increment is done
according to MSIZE)
This bit is protected and can be written only if EN is ‘0’.


332/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


Bit 9 **PINC** : Peripheral increment mode

This bit is set and cleared by software.
0: Peripheral address pointer is fixed
1: Peripheral address pointer is incremented after each data transfer (increment is done
according to PSIZE)
This bit is protected and can be written only if EN is ‘0’.


Bit 8 **CIRC** : Circular mode

This bit is set and cleared by software and can be cleared by hardware.

0: Circular mode disabled

1: Circular mode enabled

When the peripheral is the flow controller (bit PFCTRL=1) and the stream is enabled (bit
EN=1), then this bit is automatically forced by hardware to 0.
It is automatically forced by hardware to 1 if the DBM bit is set, as soon as the stream is
enabled (bit EN ='1').


Bits 7:6 **DIR[1:0]** : Data transfer direction

These bits are set and cleared by software.
00: Peripheral-to-memory
01: Memory-to-peripheral
10: Memory-to-memory
11: reserved

These bits are protected and can be written only if EN is ‘0’.


Bit 5 **PFCTRL** : Peripheral flow controller

This bit is set and cleared by software.

0: The DMA is the flow controller

1: The peripheral is the flow controller
This bit is protected and can be written only if EN is ‘0’.
When the memory-to-memory mode is selected (bits DIR[1:0]=10), then this bit is
automatically forced to 0 by hardware.


Bit 4 **TCIE** : Transfer complete interrupt enable

This bit is set and cleared by software.
0: TC interrupt disabled
1: TC interrupt enabled


Bit 3 **HTIE** : Half transfer interrupt enable

This bit is set and cleared by software.
0: HT interrupt disabled
1: HT interrupt enabled


Bit 2 **TEIE** : Transfer error interrupt enable

This bit is set and cleared by software.
0: TE interrupt disabled
1: TE interrupt enabled


Bit 1 **DMEIE** : Direct mode error interrupt enable

This bit is set and cleared by software.
0: DME interrupt disabled
1: DME interrupt enabled


RM0090 Rev 21 333/1757



341


**DMA controller (DMA)** **RM0090**


Bit 0 **EN** : Stream enable / flag stream ready when read low

This bit is set and cleared by software.

0: Stream disabled

1: Stream enabled

This bit may be cleared by hardware:

–
on a DMA end of transfer (stream ready to be configured)

– if a transfer error occurs on the AHB master buses

–
when the FIFO threshold on memory AHB port is not compatible with the size of the
burst

When this bit is read as 0, the software is allowed to program the Configuration and FIFO
bits registers. It is forbidden to write these registers when the EN bit is read as 1.

_Note: Before setting EN bit to '1' to start a new transfer, the event flags corresponding to the_
_stream in DMA_LISR or DMA_HISR register must be cleared._


**10.5.6** **DMA stream x number of data register (DMA_SxNDTR) (x = 0..7)**


Address offset: 0x14 + 0x18 × _stream number_


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|NDT[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **NDT[15:0]** : Number of data items to transfer

Number of data items to be transferred (0 up to 65535). This register can be written only
when the stream is disabled. When the stream is enabled, this register is read-only,
indicating the remaining data items to be transmitted. This register decrements after each
DMA transfer.

Once the transfer has completed, this register can either stay at zero (when the stream is in
normal mode) or be reloaded automatically with the previously programmed value in the
following cases:

–
when the stream is configured in Circular mode.

–
when the stream is enabled again by setting EN bit to '1'
If the value of this register is zero, no transaction can be served even if the stream is
enabled.


334/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


**10.5.7** **DMA stream x peripheral address register (DMA_SxPAR) (x = 0..7)**


Address offset: 0x18 + 0x18 × _stream number_


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|PAR[31:16]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|PAR[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **PAR[31:0]** : Peripheral address

Base address of the peripheral data register from/to which the data are read/written.
These bits are write-protected and can be written only when bit EN = '0' in the DMA_SxCR register.


**10.5.8** **DMA stream x memory 0 address register (DMA_SxM0AR) (x = 0..7)**


Address offset: 0x1C + 0x18 × _stream number_


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|M0A[31:16]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|M0A[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **M0A[31:0]** : Memory 0 address

Base address of Memory area 0 from/to which the data are read/written.
These bits are write-protected. They can be written only if:

–
the stream is disabled (bit EN= '0' in the DMA_SxCR register) or

–
the stream is enabled (EN=’1’ in DMA_SxCR register) and bit CT = '1' in the
DMA_SxCR register (in Double buffer mode).


**10.5.9** **DMA stream x memory 1 address register (DMA_SxM1AR) (x = 0..7)**


Address offset: 0x20 + 0x18 × _stream number_


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|M1A[31:16]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|M1A[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



RM0090 Rev 21 335/1757



341


**DMA controller (DMA)** **RM0090**


Bits 31:0 **M1A[31:0]** : Memory 1 address (used in case of Double buffer mode)

Base address of Memory area 1 from/to which the data are read/written.
This register is used only for the Double buffer mode.
These bits are write-protected. They can be written only if:

–
the stream is disabled (bit EN= '0' in the DMA_SxCR register) or

–
the stream is enabled (EN=’1’ in DMA_SxCR register) and bit CT = '0' in the
DMA_SxCR register.


**10.5.10** **DMA stream x FIFO control register (DMA_SxFCR) (x = 0..7)**


Address offset: 0x24 + 0x18 × _stream number_


Reset value: 0x0000 0021


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved








|15 14 13 12 11 10 9 8|7|6|5 4 3|Col5|Col6|2|1 0|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|FEIE|Reser<br>ved|FS[2:0]|FS[2:0]|FS[2:0]|DMDIS|FTH[1:0]|FTH[1:0]|
|Reserved|rw|rw|r|r|r|rw|rw|rw|



Bits 31:8 Reserved, must be kept at reset value.


Bit 7 **FEIE** : FIFO error interrupt enable

This bit is set and cleared by software.
0: FE interrupt disabled
1: FE interrupt enabled


Bit 6 Reserved, must be kept at reset value.


336/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


Bits 5:3 **FS[2:0]** : FIFO status

These bits are read-only.
000: 0 < fifo_level < 1/4
001: 1/4 ≤ fifo_level < 1/2
010: 1/2 ≤ fifo_level < 3/4
011: 3/4 ≤ fifo_level < full
100: FIFO is empty
101: FIFO is full

others: no meaning
These bits are not relevant in the direct mode (DMDIS bit is zero).


Bit 2 **DMDIS** : Direct mode disable

This bit is set and cleared by software. It can be set by hardware.

0: Direct mode enabled

1: Direct mode disabled

This bit is protected and can be written only if EN is ‘0’.
This bit is set by hardware if the memory-to-memory mode is selected (DIR bit in
DMA_SxCR are “10”) and the EN bit in the DMA_SxCR register is ‘1’ because the direct
mode is not allowed in the memory-to-memory configuration.


Bits 1:0 **FTH[1:0]** : FIFO threshold selection

These bits are set and cleared by software.

00: 1/4 full FIFO

01: 1/2 full FIFO

10: 3/4 full FIFO

11: full FIFO

These bits are not used in the direct mode when the DMIS value is zero.

These bits are protected and can be written only if EN is ‘0’.


RM0090 Rev 21 337/1757



341


**DMA controller (DMA)** **RM0090**


**10.5.11** **DMA register map**


_Table 52_ summarizes the DMA registers.


**Table 52. DMA register map and reset values**









































































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x0000|**DMA_LISR**|Reserved|Reserved|Reserved|Reserved|TCIF3|HTIF3|TEIF3|DMEIF3|Reserved|FEIF3|TCIF2|HTIF2|TEIF2|DMEIF2|Reserved|FEIF2|Reserved|Reserved|Reserved|Reserved|TCIF1|HTIF1|TEIF1|DMEIF1|Reserved|FEIF1|TCIF0|HTIF0|TEIF0|DMEIF0|Reserved|FEIF0|
|0x0000|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0004|**DMA_HISR**|Reserved|Reserved|Reserved|Reserved|TCIF7|HTIF7|TEIF7|DMEIF7|Reserved|FEIF7|TCIF6|HTIF6|TEIF6|DMEIF6|Reserved|FEIF6|Reserved|Reserved|Reserved|Reserved|TCIF5|HTIF5|TEIF5|DMEIF5|Reserved|FEIF5|TCIF4|HTIF4|TEIF4|DMEIF4|Reserved|FEIF4|
|0x0004|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0008|**DMA_LIFCR**|Reserved|Reserved|Reserved|Reserved|CTCIF3|CHTIF3|TEIF3|CDMEIF3|Reserved|CFEIF3|CTCIF2|CHTIF2|CTEIF2|CDMEIF2|Reserved|CFEIF2|Reserved|Reserved|Reserved|Reserved|CTCIF1|CHTIF1|CTEIF1|CDMEIF1|Reserved|CFEIF1|CTCIF0|CHTIF0|CTEIF0|CDMEIF0|Reserved|CFEIF0|
|0x0008|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|Reserved|0|0|0|0|0|0|0|0|0|Reserved|0|0|0|0|0|Reserved|0|
|0x000C|**DMA_HIFCR**|Reserved|Reserved|Reserved|Reserved|CTCIF7|CHTIF7|CTEIF7|CDMEIF7|Reserved|CFEIF7|CTCIF6|CHTIF6|CTEIF6|CDMEIF6|-<br>|CFEIF6|Reserved|Reserved|Reserved|Reserved|CTCIF5|CHTIF5|CTEIF5|CDMEIF5|-<br>|CFEIF5|CTCIF4|CHTIF4|CTEIF4|CDMEIF4|-<br>|CFEIF4|
|0x000C|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|~~-~~|0|0|0|0|0|0|0|0|0|~~-~~|0|0|0|0|0|~~-~~|0|
|0x0010|**DMA_S0CR**|Reserved|Reserved|Reserved|Reserved|CHSEL[2:0]|CHSEL[2:0]|CHSEL[2:0]|MBURST[1:0]|MBURST[1:0]|PBURST[1:0]|PBURST[1:0]|Reserved|CT|DBM|PL[1:0]|PL[1:0]|PINCOS|MSIZE[1:0]|MSIZE[1:0]|PSIZE[1:0]|PSIZE[1:0]|MINC|PINC|CIRC|DIR[1:0]|DIR[1:0]|PFCTRL|TCIE|HTIE|TEIE|DMEIE|EN|
|0x0010|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0014|**DMA_S0NDTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|
|0x0014|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0018|**DMA_S0PAR**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x0018|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x001C|**DMA_S0M0AR**|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|
|0x001C|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0020|**DMA_S0M1AR**|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|
|0x0020|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0024|**DMA_S0FCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|FEIE|Reserved|FS[2:0]|FS[2:0]|FS[2:0]|DMDIS|FTH<br>[1:0]|FTH<br>[1:0]|
|0x0024|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|1|0|0|0|0|1|
|0x0028|**DMA_S1CR**|Reserved|Reserved|Reserved|Reserved|CHSEL<br>[2:0]|CHSEL<br>[2:0]|CHSEL<br>[2:0]|MBURST[1:]|MBURST[1:]|PBURST[1:0]|PBURST[1:0]|Reserved|CT|DBM|PL[1:0]|PL[1:0]|PINCOS|MSIZE[1:0]|MSIZE[1:0]|PSIZE[1:0]|PSIZE[1:0]|MINC|PINC|CIRC|DIR[1:0]|DIR[1:0]|PFCTRL|TCIE|HTIE|TEIE|DMEIE|EN|
|0x0028|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x002C|**DMA_S1NDTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|
|0x002C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


338/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


**Table 52. DMA register map and reset values (continued)**













































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x0030|**DMA_S1PAR**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x0030|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0034|**DMA_S1M0A**R|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|
|0x0034|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0038|**DMA_S1M1AR**|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|
|0x0038|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x003C|**DMA_S1FCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|FEIE|Reserved|FS[2:0]|FS[2:0]|FS[2:0]|DMDIS|FTH<br>[1:0]|FTH<br>[1:0]|
|0x003C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|1|0|0|0|0|1|
|0x0040|**DMA_S2CR**|Reserved|Reserved|Reserved|Reserved|CHSEL<br>[2:0]|CHSEL<br>[2:0]|CHSEL<br>[2:0]|MBURST[1:0]|MBURST[1:0]|PBURST[1:0]|PBURST[1:0]|Reserved|CT|DBM|PL[1:0]|PL[1:0]|PINCOS|MSIZE[1:0]|MSIZE[1:0]|PSIZE[1:0]|PSIZE[1:0]|MINC|PINC|CIRC|DIR<br>[1:0]|DIR<br>[1:0]|PFCTRL|TCIE|HTIE|TEIE|DMEIE|EN|
|0x0040|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0044|**DMA_S2NDTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|
|0x0044|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0048|**DMA_S2PAR**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x0048|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x004C|**DMA_S2M0AR**|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|
|0x004C|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0050|**DMA_S2M1AR**|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|
|0x0050|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0054|**DMA_S2FCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|FEIE|Reserved|FS[2:0]|FS[2:0]|FS[2:0]|DMDIS|FTH<br>[1:0]|FTH<br>[1:0]|
|0x0054|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|1|0|0|0|0|1|
|0x0058|**DMA_S3CR**|Reserved|Reserved|Reserved|Reserved|CHSEL[2:0]|CHSEL[2:0]|CHSEL[2:0]|MBURST[1:0]|MBURST[1:0]|PBURST[1:0]|PBURST[1:0]|Reserved|CT|DBM|PL[1:0]|PL[1:0]|PINCOS|MSIZE[1:0]|MSIZE[1:0]|PSIZE[1:0]|PSIZE[1:0]|MINC|PINC|CIRC|DIR[1:0]|DIR[1:0]|PFCTRL|TCIE|HTIE|TEIE|DMEIE|EN|
|0x0058|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x005C|**DMA_S3NDTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|
|0x005C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0060|**DMA_S3PAR**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x0060|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0064|**DMA_S3M0AR**|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|
|0x0064|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


RM0090 Rev 21 339/1757



341


**DMA controller (DMA)** **RM0090**


**Table 52. DMA register map and reset values (continued)**



































































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x0068|**DMA_S3M1AR**|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|
|0x0068|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x006C|**DMA_S3FCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|FEIE|Reserved|FS[2:0]|FS[2:0]|FS[2:0]|DMDIS|FTH<br>[1:0]|FTH<br>[1:0]|
|0x006C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|1|0|0|0|0|1|
|0x0070|**DMA_S4C**R|Reserved|Reserved|Reserved|Reserved|CHSEL[2:0]|CHSEL[2:0]|CHSEL[2:0]|MBURST[1:0]|MBURST[1:0]|PBURST[1:0]|PBURST[1:0]|Reserved|CT|DBM|PL[1:0]|PL[1:0]|PINCOS|MSIZE[1:0]|MSIZE[1:0]|PSIZE[1:0]|PSIZE[1:0]|MINC|PINC|CIRC|DIR<br>[1:0]|DIR<br>[1:0]|PFCTRL|TCIE|HTIE|TEIE|DMEIE|EN|
|0x0070|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0074|**DMA_S4NDTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|
|0x0074|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0078|**DMA_S4PAR**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x0078|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x007C|**DMA_S4M0AR**|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|
|0x007C|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0080|**DMA_S4M1AR**|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|
|0x0080|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0084|**DMA_S4FCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|FEIE|Reserved|FS[2:0]|FS[2:0]|FS[2:0]|DMDIS|FTH<br>[1:0]|FTH<br>[1:0]|
|0x0084|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|1|0|0|0|0|1|
|0x0088|**DMA_S5CR**|Reserved|Reserved|Reserved|Reserved|CHSEL[2:0]|CHSEL[2:0]|CHSEL[2:0]|MBURST[1:0]|MBURST[1:0]|PBURST[1:0]|PBURST[1:0]|Reserved|CT|DBM|PL[1:0]|PL[1:0]|PINCOS|MSIZE[1:0]|MSIZE[1:0]|PSIZE[1:0]|PSIZE[1:0]|MINC|PINC|CIRC|DIR[1:0]|DIR[1:0]|PFCTRL|TCIE|HTIE|TEIE|DMEIE|EN|
|0x0088|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x008C|**DMA_S5NDTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|
|0x008C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0090|**DMA_S5PAR**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x0090|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0094|**DMA_S5M0AR**|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|
|0x0094|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0098|**DMA_S5M1AR**|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|
|0x0098|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x009C|**DMA_S5FCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|FEIE|Reserved|FS[2:0]|FS[2:0]|FS[2:0]|DMDIS|FTH<br>[1:0]|FTH<br>[1:0]|
|0x009C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|1|0|0|0|0|1|
|0x00A0|**DMA_S6CR**|Reserved|Reserved|Reserved|Reserved|CHSEL[2:0]|CHSEL[2:0]|CHSEL[2:0]|MBURST[1:0]|MBURST[1:0]|PBURST[1:0]|PBURST[1:0]|Reserved|CT|DBM|PL[1:0]|PL[1:0]|PINCOS|MSIZE[1:0]|MSIZE[1:0]|PSIZE[1:0]|PSIZE[1:0]|MINC|PINC|CIRC|DIR[1:0]|DIR[1:0]|PFCTRL|TCIE|HTIE|TEIE|DMEIE|EN|
|0x00A0|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00A4|**DMA_S6NDTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|
|0x00A4|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00A8|**DMA_S6PAR**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x00A8|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


340/1757 RM0090 Rev 21


**RM0090** **DMA controller (DMA)**


**Table 52. DMA register map and reset values (continued)**

































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00AC|**DMA_S6M0AR**|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|
|0x00AC|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00B0|**DMA_S6M1AR**|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|
|0x00B0|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00B4|**DMA_S6FCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|FEIE|Reserved|FS[2:0]|FS[2:0]|FS[2:0]|DMDIS|FTH<br>[1:0]|FTH<br>[1:0]|
|0x00B4|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|1|0|0|0|0|1|
|0x00B8|**DMA_S7CR**|Reserved|Reserved|Reserved|Reserved|CHSEL[2:0]|CHSEL[2:0]|CHSEL[2:0]|MBURST[1:0]|MBURST[1:0]|PBURST[1:0]|PBURST[1:0]|Reserved|CT|DBM|PL[1:0]|PL[1:0]|PINCOS<br>|MSIZE[1:0]|MSIZE[1:0]|PSIZE[1:0]|PSIZE[1:0]|MINC|PINC|CIRC|DIR[1:0]|DIR[1:0]|PFCTRL|TCIE|HTIE|TEIE|DMEIE|EN|
|0x00B8|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|~~-~~|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00BC|**DMA_S7NDTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|NDT[15:.]|
|0x00BC|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00C0|**DMA_S7PAR**|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|PA[31:0]|
|0x00C0|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00C4|**DMA_S7M0AR**|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|M0A[31:0]|
|0x00C4|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00C8|**DMA_S7M1AR**|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|M1A[31:0]|
|0x00C8|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00CC|**DMA_S7FCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|FEIE|Reserved|FS[2:0]|FS[2:0]|FS[2:0]|DMDIS|FTH<br>[1:0]|FTH<br>[1:0]|
|0x00CC|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|1|0|0|0|0|1|


Refer to _Section 2.3: Memory map_ for the register boundary addresses.


RM0090 Rev 21 341/1757



341


