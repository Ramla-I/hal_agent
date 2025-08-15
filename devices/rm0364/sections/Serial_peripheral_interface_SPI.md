**RM0364** **Serial peripheral interface (SPI)**

# **29 Serial peripheral interface (SPI)**

## **29.1 Introduction**


The SPI interface can be used to communicate with external devices using the SPI protocol.
SPI mode is selectable by software. SPI Motorola mode is selected by default after a device
reset.


The serial peripheral interface (SPI) protocol supports half-duplex, full-duplex and simplex
synchronous, serial communication with external devices. The interface can be configured
as master and in this case it provides the communication clock (SCK) to the external slave
device. The interface is also capable of operating in multimaster configuration.

## **29.2 SPI main features**


      - Master or slave operation


      - Full-duplex synchronous transfers on three lines


      - Half-duplex synchronous transfer on two lines (with bidirectional data line)


      - Simplex synchronous transfers on two lines (with unidirectional data line)


      - 4 to 16-bit data size selection


      - Multimaster mode capability


      - 8 master mode baud rate prescalers up to f PCLK /2


      - Slave mode frequency up to f PCLK /2.


      - NSS management by hardware or software for both master and slave: dynamic change
of master/slave operations


      - Programmable clock polarity and phase


      - Programmable data order with MSB-first or LSB-first shifting


      - Dedicated transmission and reception flags with interrupt capability


      - SPI bus busy status flag


      - SPI Motorola support


      - Hardware CRC feature for reliable communication:


–
CRC value can be transmitted as last byte in Tx mode


–
Automatic CRC error checking for last received byte


      - Master mode fault, overrun flags with interrupt capability


      - CRC Error flag


      - Two 32-bit embedded Rx and Tx FIFOs with DMA capability


      - Enhanced TI and NSS pulse modes support

## **29.3 SPI implementation**


The following table describes all the SPI instances and their features embedded in the
devices.


RM0364 Rev 4 1015/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


**Table 144. STM32F334xx SPI implementation**

|SPI Features|SPI1|
|---|---|
|Enhanced NSSP & TI modes|Yes|
|Hardware CRC calculation|Yes|
|Data size configurable|from 4 to 16-bit|
|Rx/Tx FIFO size|32-bit|
|Wakeup capability from Low-power Sleep|Yes|


## **29.4 SPI functional description**


**29.4.1** **General description**


The SPI allows synchronous, serial communication between the MCU and external devices.
Application software can manage the communication by polling the status flag or using
dedicated SPI interrupt. The main elements of SPI and their interactions are shown in the
following block diagram _Figure 379_ .


**Figure 379. SPI block diagram**










|Col1|Col2|CRC controller|
|---|---|---|
||||

























1016/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


Four I/O pins are dedicated to SPI communication with external devices.


      - **MISO:** Master In / Slave Out data. In the general case, this pin is used to transmit data
in slave mode and receive data in master mode.


      - **MOSI:** Master Out / Slave In data. In the general case, this pin is used to transmit data
in master mode and receive data in slave mode.


      - **SCK:** Serial Clock output pin for SPI masters and input pin for SPI slaves.


      - **NSS:** Slave select pin. Depending on the SPI and NSS settings, this pin can be used to
either:


– select an individual slave device for communication


–
synchronize the data frame or


–
detect a conflict between multiple masters


See _Section 29.4.5: Slave select (NSS) pin management_ for details.


The SPI bus allows the communication between one master device and one or more slave
devices. The bus consists of at least two wires - one for the clock signal and the other for
synchronous data transfer. Other signals can be added depending on the data exchange
between SPI nodes and their slave select signal management.


**29.4.2** **Communications between one master and one slave**


The SPI allows the MCU to communicate using different configurations, depending on the
device targeted and the application requirements. These configurations use 2 or 3 wires
(with software NSS management) or 3 or 4 wires (with hardware NSS management).
Communication is always initiated by the master.


**Full-duplex communication**


By default, the SPI is configured for full-duplex communication. In this configuration, the
shift registers of the master and slave are linked using two unidirectional lines between the
MOSI and the MISO pins. During SPI communication, data is shifted synchronously on the
SCK clock edges provided by the master. The master transmits the data to be sent to the
slave via the MOSI line and receives data from the slave via the MISO line. When the data
frame transfer is complete (all the bits are shifted) the information between the master and
slave is exchanged.


**Figure 380. Full-duplex single master/ single slave application**






















|Col1|Tx shift register|Col3|
|---|---|---|
|||SPI clock<br>generator|



1. The NSS pins can be used to provide a hardware control flow between master and slave. Optionally, the
pins can be left unused by the peripheral. Then the flow has to be handled internally for both master and
slave. For more details see _Section 29.4.5: Slave select (NSS) pin management_ .


RM0364 Rev 4 1017/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


**Half-duplex communication**


The SPI can communicate in half-duplex mode by setting the BIDIMODE bit in the
SPIx_CR1 register. In this configuration, one single cross connection line is used to link the
shift registers of the master and slave together. During this communication, the data is
synchronously shifted between the shift registers on the SCK clock edge in the transfer
direction selected reciprocally by both master and slave with the BDIOE bit in their
SPIx_CR1 registers. In this configuration, the master’s MISO pin and the slave’s MOSI pin
are free for other application uses and act as GPIOs.


**Figure 381. Half-duplex single master/ single slave application**
























|Col1|Tx shift register|Col3|
|---|---|---|
|||SPI clock<br>generator|



1. The NSS pins can be used to provide a hardware control flow between master and slave. Optionally, the
pins can be left unused by the peripheral. Then the flow has to be handled internally for both master and
slave. For more details see _Section 29.4.5: Slave select (NSS) pin management_ .


2. In this configuration, the master’s MISO pin and the slave’s MOSI pin can be used as GPIOs.


3. A critical situation can happen when communication direction is changed not synchronously between two
nodes working at bidirectionnal mode and new transmitter accesses the common data line while former
transmitter still keeps an opposite value on the line (the value depends on SPI configuration and
communication data). Both nodes then fight while providing opposite output levels on the common line
temporary till next node changes its direction settings correspondingly, too. It is suggested to insert a serial
resistance between MISO and MOSI pins at this mode to protect the outputs and limit the current blowing
between them at this situation.


**Simplex communications**


The SPI can communicate in simplex mode by setting the SPI in transmit-only or in receiveonly using the RXONLY bit in the SPIx_CR2 register. In this configuration, only one line is
used for the transfer between the shift registers of the master and slave. The remaining
MISO and MOSI pins pair is not used for communication and can be used as standard
GPIOs.


      - **Transmit-only mode (RXONLY=0):** The configuration settings are the same as for fullduplex. The application has to ignore the information captured on the unused input pin.
This pin can be used as a standard GPIO.


      - **Receive-only mode (RXONLY=1)** : The application can disable the SPI output function
by setting the RXONLY bit. In slave configuration, the MISO output is disabled and the
pin can be used as a GPIO. The slave continues to receive data from the MOSI pin
while its slave select signal is active (see _29.4.5: Slave select (NSS) pin management_ ).
Received data events appear depending on the data buffer configuration. In the master
configuration, the MOSI output is disabled and the pin can be used as a GPIO. The
clock signal is generated continuously as long as the SPI is enabled. The only way to
stop the clock is to clear the RXONLY bit or the SPE bit and wait until the incoming
pattern from the MISO pin is finished and fills the data buffer structure, depending on its
configuration.


1018/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


**Figure 382. Simplex single master/single slave application (master in transmit-only/**
**slave in receive-only mode)**
























|Col1|Tx shift register|Col3|
|---|---|---|
|||SPI clock<br>generator|



1. The NSS pins can be used to provide a hardware control flow between master and slave. Optionally, the
pins can be left unused by the peripheral. Then the flow has to be handled internally for both master and
slave. For more details see _Section 29.4.5: Slave select (NSS) pin management_ .


2. An accidental input information is captured at the input of transmitter Rx shift register. All the events
associated with the transmitter receive flow must be ignored in standard transmit only mode (e.g. OVF
flag).


3. In this configuration, both the MISO pins can be used as GPIOs.


_Note:_ _Any simplex communication can be alternatively replaced by a variant of the half-duplex_
_communication with a constant setting of the transaction direction (bidirectional mode is_
_enabled while BDIO bit is not changed)._


**29.4.3** **Standard multi-slave communication**


In a configuration with two or more independent slaves, the master uses GPIO pins to
manage the chip select lines for each slave (see _Figure 383._ ). The master must select one
of the slaves individually by pulling low the GPIO connected to the slave NSS input. When
this is done, a standard master and dedicated slave communication is established.


RM0364 Rev 4 1019/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


**Figure 383. Master and three independent slaves**


























|Rx shift register|Col2|Col3|
|---|---|---|
|Rx shift register|||


|Col1|Tx shift register|Col3|Col4|
|---|---|---|---|
||||SPI clock<br>generator|












|Rx shift register|Col2|Col3|
|---|---|---|
|Rx shift register|||


|MISO|Col2|Col3|MISO|
|---|---|---|---|
|MOSI|MOSI|MOSI|MOSI|
|MOSI|MOSI||SCK|
|MOSI|||NSS|
|MOSI||||
|MOSI|||MOSI|
|MOSI|||SCK|
|MOSI|||NSS|









|Rx shift register|Col2|Col3|
|---|---|---|
|Rx shift register|||


1. NSS pin is not used on master side at this configuration. It has to be managed internally (SSM=1, SSI=1) to
prevent any MODF error.


2. As MISO pins of the slaves are connected together, all slaves must have the GPIO configuration of their
MISO pin set as alternate function open-drain (see I/O alternate function input/output section (GPIO)).


**29.4.4** **Multi-master communication**


Unless SPI bus is not designed for a multi-master capability primarily, the user can use build
in feature which detects a potential conflict between two nodes trying to master the bus at
the same time. For this detection, NSS pin is used configured at hardware input mode.


The connection of more than two SPI nodes working at this mode is impossible as only one
node can apply its output on a common data line at time.


When nodes are non active, both stay at slave mode by default. Once one node wants to
overtake control on the bus, it switches itself into master mode and applies active level on
the slave select input of the other node via dedicated GPIO pin. After the session is
completed, the active slave select signal is released and the node mastering the bus
temporary returns back to passive slave mode waiting for next session start.


1020/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


If potentially both nodes raised their mastering request at the same time a bus conflict event
appears (see mode fault MODF event). Then the user can apply some simple arbitration
process (e.g. to postpone next attempt by predefined different time-outs applied at both
nodes).


**Figure 384. Multi-master application**


























|Col1|Tx (Rx) shift register|Col3|
|---|---|---|
|||SPI clock<br>generator|


|Tx (Rx) shift register|Col2|Col3|Col4|
|---|---|---|---|
|Tx (Rx) shift register|SPI clock<br>generator|||













1. The NSS pin is configured at hardware input mode at both nodes. Its active level enables the MISO line
output control as the passive node is configured as a slave.


**29.4.5** **Slave select (NSS) pin management**


In slave mode, the NSS works as a standard “chip select” input and lets the slave
communicate with the master. In master mode, NSS can be used either as output or input.
As an input it can prevent multimaster bus collision, and as an output it can drive a slave
select signal of a single slave.


Hardware or software slave select management can be set using the SSM bit in the
SPIx_CR1 register:


      - **Software NSS management (SSM = 1)** : in this configuration, slave select information
is driven internally by the SSI bit value in register SPIx_CR1. The external NSS pin is
free for other application uses.


      - **Hardware NSS management (SSM = 0)** : in this case, there are two possible
configurations. The configuration used depends on the NSS output configuration
(SSOE bit in register SPIx_CR1).


–
**NSS output enable (SSM=0,SSOE = 1)** : this configuration is only used when the
MCU is set as master. The NSS pin is managed by the hardware. The NSS signal
is driven low as soon as the SPI is enabled in master mode (SPE=1), and is kept
low until the SPI is disabled (SPE =0). A pulse can be generated between
continuous communications if NSS pulse mode is activated (NSSP=1). The SPI
cannot work in multimaster configuration with this NSS setting.


–
**NSS output disable (SSM=0, SSOE = 0)** : if the microcontroller is acting as the
master on the bus, this configuration allows multimaster capability. If the NSS pin
is pulled low in this mode, the SPI enters master mode fault state and the device is
automatically reconfigured in slave mode. In slave mode, the NSS pin works as a
standard “chip select” input and the slave is selected while NSS line is at low level.


RM0364 Rev 4 1021/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


**Figure 385. Hardware/software slave select management**










|NSS<br>Inp.|Master<br>mode|Slave mode|
|---|---|---|
|_Vdd_|_OK_|_Non active_|
|_Vss_|_Conflict_|_Active_|













**29.4.6** **Communication formats**





During SPI communication, receive and transmit operations are performed simultaneously.
The serial clock (SCK) synchronizes the shifting and sampling of the information on the data
lines. The communication format depends on the clock phase, the clock polarity and the
data frame format. To be able to communicate together, the master and slaves devices must
follow the same communication format.


**Clock phase and polarity controls**


Four possible timing relationships may be chosen by software, using the CPOL and CPHA
bits in the SPIx_CR1 register. The CPOL (clock polarity) bit controls the idle state value of
the clock when no data is being transferred. This bit affects both master and slave modes. If
CPOL is reset, the SCK pin has a low-level idle state. If CPOL is set, the SCK pin has a
high-level idle state.


If the CPHA bit is set, the second edge on the SCK pin captures the first data bit transacted
(falling edge if the CPOL bit is reset, rising edge if the CPOL bit is set). Data are latched on
each occurrence of this clock transition type. If the CPHA bit is reset, the first edge on the
SCK pin captures the first data bit transacted (falling edge if the CPOL bit is set, rising edge
if the CPOL bit is reset). Data are latched on each occurrence of this clock transition type.


The combination of CPOL (clock polarity) and CPHA (clock phase) bits selects the data
capture clock edge.


1022/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


_Figure 386_, shows an SPI full-duplex transfer with the four combinations of the CPHA and
CPOL bits.


_Note:_ _Prior to changing the CPOL/CPHA bits the SPI must be disabled by resetting the SPE bit._


_The idle state of SCK must correspond to the polarity selected in the SPIx_CR1 register (by_
_pulling up SCK if CPOL=1 or pulling down SCK if CPOL=0)._


**Figure 386. Data clock timing diagram**























1. The order of data bits depends on LSBFIRST bit setting.


**Data frame format**


The SPI shift register can be set up to shift out MSB-first or LSB-first, depending on the
value of the LSBFIRST bit. The data frame size is chosen by using the DS bits. It can be set
from 4-bit up to 16-bit length and the setting applies for both transmission and reception.
Whatever the selected data frame size, read access to the FIFO must be aligned with the
FRXTH level. When the SPIx_DR register is accessed, data frames are always right-aligned
into either a byte (if the data fits into a byte) or a half-word (see _Figure 387_ ). During
communication, only bits within the data frame are clocked and transferred.


RM0364 Rev 4 1023/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


**Figure 387. Data alignment when data length is not equal to 8-bit or 16-bit**



































_Note:_ _The minimum data length is 4 bits. If a data length of less than 4 bits is selected, it is forced_
_to an 8-bit data frame size._


**29.4.7** **Configuration of SPI**


The configuration procedure is almost the same for master and slave. For specific mode
setups, follow the dedicated sections. When a standard communication is to be initialized,
perform these steps:


1. Write proper GPIO registers: Configure GPIO for MOSI, MISO and SCK pins.


2. Write to the SPI_CR1 register:


a) Configure the serial clock baud rate using the BR[2:0] bits (Note: 4).


b) Configure the CPOL and CPHA bits combination to define one of the four
relationships between the data transfer and the serial clock (CPHA must be
cleared in NSSP mode). (Note: 2 - except the case when CRC is enabled at TI
mode).


c) Select simplex or half-duplex mode by configuring RXONLY or BIDIMODE and
BIDIOE (RXONLY and BIDIMODE can't be set at the same time).


d) Configure the LSBFIRST bit to define the frame format (Note: 2).


e) Configure the CRCL and CRCEN bits if CRC is needed (while SCK clock signal is
at idle state).


f) Configure SSM and SSI (Notes: 2 & 3).


g) Configure the MSTR bit (in multimaster NSS configuration, avoid conflict state on
NSS if master is configured to prevent MODF error).


3. Write to SPI_CR2 register:


a) Configure the DS[3:0] bits to select the data length for the transfer.


b) Configure SSOE (Notes: 1 & 2 & 3).


c) Set the FRF bit if the TI protocol is required (keep NSSP bit cleared in TI mode).


d) Set the NSSP bit if the NSS pulse mode between two data units is required (keep
CHPA and TI bits cleared in NSSP mode).


e) Configure the FRXTH bit. The RXFIFO threshold must be aligned to the read
access size for the SPIx_DR register.


f) Initialize LDMA_TX and LDMA_RX bits if DMA is used in packed mode.


4. Write to SPI_CRCPR register: Configure the CRC polynomial if needed.


5. Write proper DMA registers: Configure DMA streams dedicated for SPI Tx and Rx in
DMA registers if the DMA streams are used.


1024/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


_Note:_ _(1) Step is not required in slave mode._


_(2) Step is not required in TI mode._


_(3) Step is not required in NSSP mode._


_(4) The step is not required in slave mode except slave working at TI mode_


**29.4.8** **Procedure for enabling SPI**


It is recommended to enable the SPI slave before the master sends the clock. If not,
undesired data transmission might occur. The data register of the slave must already
contain data to be sent before starting communication with the master (either on the first
edge of the communication clock, or before the end of the ongoing communication if the
clock signal is continuous). The SCK signal must be settled at an idle state level
corresponding to the selected polarity before the SPI slave is enabled.


The master at full-duplex (or in any transmit-only mode) starts to communicate when the
SPI is enabled and TXFIFO is not empty, or with the next write to TXFIFO.


In any master receive only mode (RXONLY=1 or BIDIMODE=1 & BIDIOE=0), master starts
to communicate and the clock starts running immediately after SPI is enabled.


For handling DMA, follow the dedicated section.


**29.4.9** **Data transmission and reception procedures**


**RXFIFO and TXFIFO**


All SPI data transactions pass through the 32-bit embedded FIFOs. This enables the SPI to
work in a continuous flow, and prevents overruns when the data frame size is short. Each
direction has its own FIFO called TXFIFO and RXFIFO. These FIFOs are used in all SPI
modes except for receiver-only mode (slave or master) with CRC calculation enabled (see
_Section 29.4.14: CRC calculation_ ).


The handling of FIFOs depends on the data exchange mode (duplex, simplex), data frame
format (number of bits in the frame), access size performed on the FIFO data registers (8-bit
or 16-bit), and whether or not data packing is used when accessing the FIFOs (see
_Section 29.4.13: TI mode_ ).


A read access to the SPIx_DR register returns the oldest value stored in RXFIFO that has
not been read yet. A write access to the SPIx_DR stores the written data in the TXFIFO at
the end of a send queue. The read access must be always aligned with the RXFIFO
threshold configured by the FRXTH bit in SPIx_CR2 register. FTLVL[1:0] and FRLVL[1:0]
bits indicate the current occupancy level of both FIFOs.


A read access to the SPIx_DR register must be managed by the RXNE event. This event is
triggered when data is stored in RXFIFO and the threshold (defined by FRXTH bit) is
reached. When RXNE is cleared, RXFIFO is considered to be empty. In a similar way, write
access of a data frame to be transmitted is managed by the TXE event. This event is
triggered when the TXFIFO level is less than or equal to half of its capacity. Otherwise TXE
is cleared and the TXFIFO is considered as full. In this way, RXFIFO can store up to four
data frames, whereas TXFIFO can only store up to three when the data frame format is not
greater than 8 bits. This difference prevents possible corruption of 3x 8-bit data frames
already stored in the TXFIFO when software tries to write more data in 16-bit mode into
TXFIFO. Both TXE and RXNE events can be polled or handled by interrupts. See
_Figure 389_ through _Figure 392_ .


RM0364 Rev 4 1025/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


Another way to manage the data exchange is to use DMA (see _Communication using DMA_
_(direct memory addressing)_ ).


If the next data is received when the RXFIFO is full, an overrun event occurs (see
description of OVR flag at _Section 29.4.10: SPI status flags_ ). An overrun event can be
polled or handled by an interrupt.


The BSY bit being set indicates ongoing transaction of a current data frame. When the clock
signal runs continuously, the BSY flag stays set between data frames at master but
becomes low for a minimum duration of one SPI clock at slave between each data frame

transfer.


**Sequence handling**


A few data frames can be passed at single sequence to complete a message. When
transmission is enabled, a sequence begins and continues while any data is present in the
TXFIFO of the master. The clock signal is provided continuously by the master until TXFIFO
becomes empty, then it stops waiting for additional data.


In receive-only modes, half-duplex (BIDIMODE=1, BIDIOE=0) or simplex (BIDIMODE=0,
RXONLY=1) the master starts the sequence immediately when both SPI is enabled and
receive-only mode is activated. The clock signal is provided by the master and it does not
stop until either SPI or receive-only mode is disabled by the master. The master receives
data frames continuously up to this moment.


While the master can provide all the transactions in continuous mode (SCK signal is
continuous) it has to respect slave capability to handle data flow and its content at anytime.
When necessary, the master must slow down the communication and provide either a
slower clock or separate frames or data sessions with sufficient delays. Be aware there is no
underflow error signal for master or slave in SPI mode, and data from the slave is always
transacted and processed by the master even if the slave could not prepare it correctly in
time. It is preferable for the slave to use DMA, especially when data frames are shorter and
bus rate is high.


Each sequence must be encased by the NSS pulse in parallel with the multislave system to
select just one of the slaves for communication. In a single slave system it is not necessary
to control the slave with NSS, but it is often better to provide the pulse here too, to
synchronize the slave with the beginning of each data sequence. NSS can be managed by
both software and hardware (see _Section 29.4.5: Slave select (NSS) pin management_ ).


When the BSY bit is set it signifies an ongoing data frame transaction. When the dedicated
frame transaction is finished, the RXNE flag is raised. The last bit is just sampled and the
complete data frame is stored in the RXFIFO.


**Procedure for disabling the SPI**


When SPI is disabled, it is mandatory to follow the disable procedures described in this
paragraph. It is important to do this before the system enters a low-power mode when the
peripheral clock is stopped. Ongoing transactions can be corrupted in this case. In some
modes the disable procedure is the only way to stop continuous communication running.


Master in full-duplex or transmit only mode can finish any transaction when it stops
providing data for transmission. In this case, the clock stops after the last data transaction.
Special care must be taken in packing mode when an odd number of data frames are
transacted to prevent some dummy byte exchange (refer to _Data packing_ section). Before
the SPI is disabled in these modes, the user must follow standard disable procedure. When


1026/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


the SPI is disabled at the master transmitter while a frame transaction is ongoing or next
data frame is stored in TXFIFO, the SPI behavior is not guaranteed.


When the master is in any receive only mode, the only way to stop the continuous clock is to
disable the peripheral by SPE=0. This must occur in specific time window within last data
frame transaction just between the sampling time of its first bit and before its last bit transfer
starts (in order to receive a complete number of expected data frames and to prevent any
additional “dummy” data reading after the last valid data frame). Specific procedure must be
followed when disabling SPI in this mode.


Data received but not read remains stored in RXFIFO when the SPI is disabled, and must
be processed the next time the SPI is enabled, before starting a new sequence. To prevent
having unread data, ensure that RXFIFO is empty when disabling the SPI, by using the
correct disabling procedure, or by initializing all the SPI registers with a software reset via
the control of a specific register dedicated to peripheral reset (see the SPIiRST bits in the
RCC_APBiRSTR registers).


Standard disable procedure is based on pulling BSY status together with FTLVL[1:0] to
check if a transmission session is fully completed. This check can be done in specific cases,
too, when it is necessary to identify the end of ongoing transactions, for example:


      - When NSS signal is managed by software and master has to provide proper end of
NSS pulse for slave, or


      - When transactions’ streams from DMA or FIFO are completed while the last data frame
or CRC frame transaction is still ongoing in the peripheral bus.


The correct disable procedure is (except when receive only mode is used):


1. Wait until FTLVL[1:0] = 00 (no more data to transmit).


2. Wait until BSY=0 (the last data frame is processed).


3. Disable the SPI (SPE=0).


4. Read data until FRLVL[1:0] = 00 (read all the received data).


The correct disable procedure for certain receive only modes is:


1. Interrupt the receive flow by disabling SPI (SPE=0) in the specific time window while
the last data frame is ongoing.


2. Wait until BSY=0 (the last data frame is processed).


3. Read data until FRLVL[1:0] = 00 (read all the received data).


_Note:_ _If packing mode is used and an odd number of data frames with a format less than or equal_
_to 8 bits (fitting into one byte) has to be received, FRXTH must be set when FRLVL[1:0] =_
_01, in order to generate the RXNE event to read the last odd data frame and to keep good_
_FIFO pointer alignment._


**Data packing**


When the data frame size fits into one byte (less than or equal to 8 bits), data packing is
used automatically when any read or write 16-bit access is performed on the SPIx_DR
register. The double data frame pattern is handled in parallel in this case. At first, the SPI
operates using the pattern stored in the LSB of the accessed word, then with the other half
stored in the MSB. _Figure 388_ provides an example of data packing mode sequence
handling. Two data frames are sent after the single 16-bit access the SPIx_DR register of
the transmitter. This sequence can generate just one RXNE event in the receiver if the
RXFIFO threshold is set to 16 bits (FRXTH=0). The receiver then has to access both data
frames by a single 16-bit read of SPIx_DR as a response to this single RXNE event. The


RM0364 Rev 4 1027/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


RxFIFO threshold setting and the following read access must be always kept aligned at the
receiver side, as data can be lost if it is not in line.


A specific problem appears if an odd number of such “fit into one byte” data frames must be
handled. On the transmitter side, writing the last data frame of any odd sequence with an 8bit access to SPIx_DR is enough. The receiver has to change the Rx_FIFO threshold level
for the last data frame received in the odd sequence of frames in order to generate the
RXNE event.


**Figure 388. Packing data in FIFO for transmission and reception**



















**Communication using DMA (direct memory addressing)**


To operate at its maximum speed and to facilitate the data register read/write process
required to avoid overrun, the SPI features a DMA capability, which implements a simple
request/acknowledge protocol.


A DMA access is requested when the TXE or RXNE enable bit in the SPIx_CR2 register is
set. Separate requests must be issued to the Tx and Rx buffers.


      - In transmission, a DMA request is issued each time TXE is set to 1. The DMA then
writes to the SPIx_DR register.


      - In reception, a DMA request is issued each time RXNE is set to 1. The DMA then reads
the SPIx_DR register.


See _Figure 389_ through _Figure 392_ .


When the SPI is used only to transmit data, it is possible to enable only the SPI Tx DMA
channel. In this case, the OVR flag is set because the data received is not read. When the
SPI is used only to receive data, it is possible to enable only the SPI Rx DMA channel.


In transmission mode, when the DMA has written all the data to be transmitted (the TCIF
flag is set in the DMA_ISR register), the BSY flag can be monitored to ensure that the SPI
communication is complete. This is required to avoid corrupting the last transmission before
disabling the SPI or entering the Stop mode. The software must first wait until
FTLVL[1:0]=00 and then until BSY=0.


1028/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


When starting communication using DMA, to prevent DMA channel management raising
error events, these steps must be followed in order:


1. Enable DMA Rx buffer in the RXDMAEN bit in the SPI_CR2 register, if DMA Rx is
used.


2. Enable DMA streams for Tx and Rx in DMA registers, if the streams are used.


3. Enable DMA Tx buffer in the TXDMAEN bit in the SPI_CR2 register, if DMA Tx is used.


4. Enable the SPI by setting the SPE bit.


To close communication it is mandatory to follow these steps in order:


1. Disable DMA streams for Tx and Rx in the DMA registers, if the streams are used.


2. Disable the SPI by following the SPI disable procedure.


3. Disable DMA Tx and Rx buffers by clearing the TXDMAEN and RXDMAEN bits in the
SPI_CR2 register, if DMA Tx and/or DMA Rx are used.


**Packing with DMA**


If the transfers are managed by DMA (TXDMAEN and RXDMAEN set in the SPIx_CR2
register) packing mode is enabled/disabled automatically depending on the PSIZE value
configured for SPI TX and the SPI RX DMA channel. If the DMA channel PSIZE value is
equal to 16-bit and SPI data size is less than or equal to 8-bit, then packing mode is
enabled. The DMA then automatically manages the write operations to the SPIx_DR
register.


If data packing mode is used and the number of data to transfer is not a multiple of two, the
LDMA_TX/LDMA_RX bits must be set. The SPI then considers only one data for the
transmission or reception to serve the last DMA transfer (for more details refer to _Data_
_packing on page 1027_ .)


RM0364 Rev 4 1029/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


**Communication diagrams**


Some typical timing schemes are explained in this section. These schemes are valid no
matter if the SPI events are handled by polling, interrupts or DMA. For simplicity, the
LSBFIRST=0, CPOL=0 and CPHA=1 setting is used as a common assumption here. No
complete configuration of DMA streams is provided.


The following numbered notes are common for _Figure 389 on page 1031_ through
_Figure 392 on page 1034_ :


1. The slave starts to control MISO line as NSS is active and SPI is enabled, and is
disconnected from the line when one of them is released. Sufficient time must be

provided for the slave to prepare data dedicated to the master in advance before its
transaction starts.
At the master, the SPI peripheral takes control at MOSI and SCK signals (occasionally
at NSS signal as well) only if SPI is enabled. If SPI is disabled the SPI peripheral is
disconnected from GPIO logic, so the levels at these lines depends on GPIO setting
exclusively.


2. At the master, BSY stays active between frames if the communication (clock signal) is
continuous. At the slave, BSY signal always goes down for at least one clock cycle
between data frames.


3. The TXE signal is cleared only if TXFIFO is full.


4. The DMA arbitration process starts just after the TXDMAEN bit is set. The TXE
interrupt is generated just after the TXEIE is set. As the TXE signal is at an active level,
data transfers to TxFIFO start, until TxFIFO becomes full or the DMA transfer
completes.


5. If all the data to be sent can fit into TxFIFO, the DMA Tx TCIF flag can be raised even
before communication on the SPI bus starts. This flag always rises before the SPI
transaction is completed.


6. The CRC value for a package is calculated continuously frame by frame in the
SPIx_TXCRCR and SPIx_RXCRCR registers. The CRC information is processed after
the entire data package has completed, either automatically by DMA (Tx channel must
be set to the number of data frames to be processed) or by SW (the user must handle
CRCNEXT bit during the last data frame processing).
While the CRC value calculated in SPIx_TXCRCR is simply sent out by transmitter,
received CRC information is loaded into RxFIFO and then compared with the
SPIx_RXCRCR register content (CRC error flag can be raised here if any difference).
This is why the user must take care to flush this information from the FIFO, either by
software reading out all the stored content of RxFIFO, or by DMA when the proper
number of data frames is preset for Rx channel (number of data frames + number of
CRC frames) (see the settings at the example assumption).


7. In data packed mode, TxE and RxNE events are paired and each read/write access to
the FIFO is 16 bits wide until the number of data frames are even. If the TxFIFO is ¾
full FTLVL status stays at FIFO full level. That is why the last odd data frame cannot be
stored before the TxFIFO becomes ½ full. This frame is stored into TxFIFO with an 8bit access either by software or automatically by DMA when LDMA_TX control is set.


8. To receive the last odd data frame in packed mode, the Rx threshold must be changed
to 8-bit when the last data frame is processed, either by software setting FRXTH=1 or
automatically by a DMA internal signal when LDMA_RX is set.


1030/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


**Figure 389. Master full-duplex communication**




























|Col1|MSB|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
|||||||
|||3|3|||
|||||||
|11<br>Tx2|11<br>Tx2|11<br>Tx2||||
|11<br>Tx2|||_Enable Tx/Rx D_|_MA or interrupts_||
|11<br>Tx2||||||
|11<br>Tx2||D|D|D|D|
|11<br>Tx2||||||
|11<br>Tx2||10|10|10|10|























Assumptions for master full-duplex communication example:


- Data size > 8 bit


If DMA is used:


- Number of Tx frames transacted by DMA is set to 3


- Number of Rx frames transacted by DMA is set to 3


See also _: Communication diagrams on page 1030_ for details about common assumptions
and notes.


RM0364 Rev 4 1031/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


**Figure 390. Slave full-duplex communication**
































|2<br>MSB DTx1 MSB DTx2 MSB DTx3|Col2|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
|||||||
|||||||
||**MSB**|**MSB**|**MSB**|**MSB**|**MSB**|
|||||||
|||3|3|||
|||||||
|||||||
||||_Enable Tx/Rx D_|_MA or interrupts_||
|||||||
|||D|D|D|D|
|||||||
|||10|10|10|10|

















Assumptions for slave full-duplex communication example:


      - Data size > 8 bit


If DMA is used:


      - Number of Tx frames transacted by DMA is set to 3


      - Number of Rx frames transacted by DMA is set to 3


See also _: Communication diagrams on page 1030_ for details about common assumptions
and notes.


1032/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


**Figure 391. Master full-duplex communication with CRC**












|MSB|Col2|Col3|
|---|---|---|
||||
||||
||||
||_Enable Tx/Rx D_|_MA or interrupts_|





























Assumptions for master full-duplex communication with CRC example:


- Data size = 16 bit


- CRC enabled


If DMA is used:


- Number of Tx frames transacted by DMA is set to 2


- Number of Rx frames transacted by DMA is set to 3


See also _: Communication diagrams on page 1030_ for details about common assumptions
and notes.


RM0364 Rev 4 1033/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


**Figure 392. Master full-duplex communication in packed mode**




















|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|
|---|---|---|---|---|---|---|---|---|---|
|||||||||||
||**5**|**4  3  2  1**|**5**|**4  3  2  1**|**4  3  2  1**|**4  3  2  1**<br>**5**<br>**5**|**5**|**4  3  2  1**|**4  3  2  1**|
|||||||||||
|||||3|3|||||
|||||||||||
|||||||||||
|||||_Ena_|_ble Tx/R_|_x DMA or interrupts_|_x DMA or interrupts_|||
|||||_Ena_||||||
|||||_Ena_|DTx5|DTx5|DTx5|DTx5|DTx5|




























|Col1|Col2|5 4 3 2|1 5 4|3 2 1|5 4 3 2|1 5 4 3 2 1|
|---|---|---|---|---|---|---|
|||**5  4  3  2**<br>|**DRx1-2**|**DRx1-2**|**DRx1-2**|**DRx1-2**|
|||**5  4  3  2**<br>|||||
|_DMA or software control at Rx events_|_DMA or software control at Rx events_|_DMA or software control at Rx events_|||||













Assumptions for master full-duplex communication in packed mode example:


      - Data size = 5 bit


      - Read/write FIFO is performed mostly by 16-bit access


      - FRXTH=0


If DMA is used:


      - Number of Tx frames to be transacted by DMA is set to 3


      - Number of Rx frames to be transacted by DMA is set to 3


      - PSIZE for both Tx and Rx DMA channel is set to 16-bit


      - LDMA_TX=1 and LDMA_RX=1


See also _: Communication diagrams on page 1030_ for details about common assumptions
and notes.


1034/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


**29.4.10** **SPI status flags**


Three status flags are provided for the application to completely monitor the state of the SPI
bus.


**Tx buffer empty flag (TXE)**


The TXE flag is set when transmission TXFIFO has enough space to store data to send.
TXE flag is linked to the TXFIFO level. The flag goes high and stays high until the TXFIFO
level is lower or equal to 1/2 of the FIFO depth. An interrupt can be generated if the TXEIE
bit in the SPIx_CR2 register is set. The bit is cleared automatically when the TXFIFO level
becomes greater than 1/2.


**Rx buffer not empty (RXNE)**


The RXNE flag is set depending on the FRXTH bit value in the SPIx_CR2 register:


      - If FRXTH is set, RXNE goes high and stays high until the RXFIFO level is greater or
equal to 1/4 (8-bit).


      - If FRXTH is cleared, RXNE goes high and stays high until the RXFIFO level is greater
than or equal to 1/2 (16-bit).


An interrupt can be generated if the RXNEIE bit in the SPIx_CR2 register is set.


The RXNE is cleared by hardware automatically when the above conditions are no longer
true.


**Busy flag (BSY)**


The BSY flag is set and cleared by hardware (writing to this flag has no effect).


When BSY is set, it indicates that a data transfer is in progress on the SPI (the SPI bus is
busy).


The BSY flag can be used in certain modes to detect the end of a transfer so that the
software can disable the SPI or its peripheral clock before entering a low-power mode which
does not provide a clock for the peripheral. This avoids corrupting the last transfer.


The BSY flag is also useful for preventing write collisions in a multimaster system.


The BSY flag is cleared under any one of the following conditions:


      - When the SPI is correctly disabled


      - When a fault is detected in Master mode (MODF bit set to 1)


      - In Master mode, when it finishes a data transmission and no new data is ready to be
sent


      - In Slave mode, when the BSY flag is set to '0' for at least one SPI clock cycle between
each data transfer.


_Note:_ _When the next transmission can be handled immediately by the master (e.g. if the master is_
_in Receive-only mode or its Transmit FIFO is not empty), communication is continuous and_
_the BSY flag remains set to '1' between transfers on the master side. Although this is not the_
_case with a slave, it is recommended to use always the TXE and RXNE flags (instead of the_
_BSY flags) to handle data transmission or reception operations._


RM0364 Rev 4 1035/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


**29.4.11** **SPI error flags**


An SPI interrupt is generated if one of the following error flags is set and interrupt is enabled
by setting the ERRIE bit.


**Overrun flag (OVR)**


An overrun condition occurs when data is received by a master or slave and the RXFIFO
has not enough space to store this received data. This can happen if the software or the
DMA did not have enough time to read the previously received data (stored in the RXFIFO)
or when space for data storage is limited e.g. the RXFIFO is not available when CRC is
enabled in receive only mode so in this case the reception buffer is limited into a single data
frame buffer (see _Section 29.4.14: CRC calculation_ ).


When an overrun condition occurs, the newly received value does not overwrite the
previous one in the RXFIFO. The newly received value is discarded and all data transmitted
subsequently is lost. Clearing the OVR bit is done by a read access to the SPI_DR register
followed by a read access to the SPI_SR register.


**Mode fault (MODF)**


Mode fault occurs when the master device has its internal NSS signal (NSS pin in NSS
hardware mode, or SSI bit in NSS software mode) pulled low. This automatically sets the
MODF bit. Master mode fault affects the SPI interface in the following ways:


      - The MODF bit is set and an SPI interrupt is generated if the ERRIE bit is set.


      - The SPE bit is cleared. This blocks all output from the device and disables the SPI
interface.


      - The MSTR bit is cleared, thus forcing the device into slave mode.


Use the following software sequence to clear the MODF bit:


1. Make a read or write access to the SPIx_SR register while the MODF bit is set.


2. Then write to the SPIx_CR1 register.


To avoid any multiple slave conflicts in a system comprising several MCUs, the NSS pin
must be pulled high during the MODF bit clearing sequence. The SPE and MSTR bits can
be restored to their original state after this clearing sequence. As a security, hardware does
not allow the SPE and MSTR bits to be set while the MODF bit is set. In a slave device the

MODF bit cannot be set except as the result of a previous multimaster conflict.


**CRC error (CRCERR)**


This flag is used to verify the validity of the value received when the CRCEN bit in the
SPIx_CR1 register is set. The CRCERR flag in the SPIx_SR register is set if the value
received in the shift register does not match the receiver SPIx_RXCRCR value. The flag is
cleared by the software.


**TI mode frame format error (FRE)**


A TI mode frame format error is detected when an NSS pulse occurs during an ongoing
communication when the SPI is operating in slave mode and configured to conform to the TI
mode protocol. When this error occurs, the FRE flag is set in the SPIx_SR register. The SPI
is not disabled when an error occurs, the NSS pulse is ignored, and the SPI waits for the
next NSS pulse before starting a new transfer. The data may be corrupted since the error
detection may result in the loss of two data bytes.


1036/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


The FRE flag is cleared when SPIx_SR register is read. If the ERRIE bit is set, an interrupt
is generated on the NSS error detection. In this case, the SPI should be disabled because
data consistency is no longer guaranteed and communications should be reinitiated by the
master when the slave SPI is enabled again.


**29.4.12** **NSS pulse mode**


This mode is activated by the NSSP bit in the SPIx_CR2 register and it takes effect only if
the SPI interface is configured as Motorola SPI master (FRF=0) with capture on the first
edge (SPIx_CR1 CPHA = 0, CPOL setting is ignored). When activated, an NSS pulse is
generated between two consecutive data frame transfers when NSS stays at high level for
the duration of one clock period at least. This mode allows the slave to latch data. NSSP
pulse mode is designed for applications with a single master-slave pair.


_Figure 393_ illustrates NSS pin management when NSSP pulse mode is enabled.


**Figure 393. NSSP pulse generation in Motorola SPI master mode**


















|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
||||||||L||
||||||||||
|M|SB|SB|LS|B|M|SB|SB|SB|
||||||M|M|||
|are<br>M|SB|L|L|Do not care|Do not care|SB|L|L|









_Note:_ Similar behavior is encountered when CPOL = 0. In this case the sampling edge is the _rising_
edge of SCK, and NSS assertion and deassertion refer to this sampling edge.


**29.4.13** **TI mode**


**TI protocol in master mode**


The SPI interface is compatible with the TI protocol. The FRF bit of the SPIx_CR2 register
can be used to configure the SPI to be compliant with this protocol.


The clock polarity and phase are forced to conform to the TI protocol requirements whatever
the values set in the SPIx_CR1 register. NSS management is also specific to the TI protocol
which makes the configuration of NSS management through the SPIx_CR1 and SPIx_CR2
registers (SSM, SSI, SSOE) impossible in this case.


In slave mode, the SPI baud rate prescaler is used to control the moment when the MISO
pin state changes to HiZ when the current transaction finishes (see _Figure 394_ ). Any baud
rate can be used, making it possible to determine this moment with optimal flexibility.
However, the baud rate is generally set to the external master clock baud rate. The delay for
the MISO signal to become HiZ (t release ) depends on internal resynchronization and on the


RM0364 Rev 4 1037/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


baud rate value set in through the BR[2:0] bits in the SPIx_CR1 register. It is given by the
formula:


t t
-------------------- baud_rate **-** + 4 × t < t < -------------------- baud_rate **-** + 6 × t
2 pclk release 2 pclk


If the slave detects a misplaced NSS pulse during a data frame transaction the TIFRE flag is
set.


If the data size is equal to 4-bits or 5-bits, the master in full-duplex mode or transmit-only
mode uses a protocol with one more dummy data bit added after LSB. TI NSS pulse is
generated above this dummy bit clock cycle instead of the LSB in each period.


This feature is not available for Motorola SPI communications (FRF bit set to 0).


_Figure 394: TI mode transfer_ shows the SPI communication waveforms when TI mode is
selected.


**Figure 394. TI mode transfer**








|Col1|Col2|
|---|---|
|||
|LSB|LSB|









**29.4.14** **CRC calculation**


Two separate CRC calculators are implemented in order to check the reliability of
transmitted and received data. The SPI offers CRC8 or CRC16 calculation independently of
the frame data length, which can be fixed to 8-bit or 16-bit. For all the other data frame
lengths, no CRC is available.


**CRC principle**


CRC calculation is enabled by setting the CRCEN bit in the SPIx_CR1 register before the
SPI is enabled (SPE = 1). The CRC value is calculated using an odd programmable
polynomial on each bit. The calculation is processed on the sampling clock edge defined by
the CPHA and CPOL bits in the SPIx_CR1 register. The calculated CRC value is checked
automatically at the end of the data block as well as for transfer managed by CPU or by the
DMA. When a mismatch is detected between the CRC calculated internally on the received
data and the CRC sent by the transmitter, a CRCERR flag is set to indicate a data corruption
error. The right procedure for handling the CRC calculation depends on the SPI
configuration and the chosen transfer management.


1038/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


_Note:_ _The polynomial value should only be odd. No even values are supported._


**CRC transfer managed by CPU**


Communication starts and continues normally until the last data frame has to be sent or
received in the SPIx_DR register. Then CRCNEXT bit has to be set in the SPIx_CR1
register to indicate that the CRC frame transaction follows after the transaction of the
currently processed data frame. The CRCNEXT bit must be set before the end of the last
data frame transaction. CRC calculation is frozen during CRC transaction.


The received CRC is stored in the RXFIFO like a data byte or word. That is why in CRC
mode only, the reception buffer has to be considered as a single 16-bit buffer used to
receive only one data frame at a time.


A CRC-format transaction usually takes one more data frame to communicate at the end of
data sequence. However, when setting an 8-bit data frame checked by 16-bit CRC, two
more frames are necessary to send the complete CRC.


When the last CRC data is received, an automatic check is performed comparing the
received value and the value in the SPIx_RXCRC register. Software has to check the
CRCERR flag in the SPIx_SR register to determine if the data transfers were corrupted or
not. Software clears the CRCERR flag by writing '0' to it.


After the CRC reception, the CRC value is stored in the RXFIFO and must be read in the
SPIx_DR register in order to clear the RXNE flag.


**CRC transfer managed by DMA**


When SPI communication is enabled with CRC communication and DMA mode, the
transmission and reception of the CRC at the end of communication is automatic (with the
exception of reading CRC data in receive only mode). The CRCNEXT bit does not have to
be handled by the software. The counter for the SPI transmission DMA channel has to be
set to the number of data frames to transmit excluding the CRC frame. On the receiver side,
the received CRC value is handled automatically by DMA at the end of the transaction but
user must take care to flush out received CRC information from RXFIFO as it is always
loaded into it. In full-duplex mode, the counter of the reception DMA channel can be set to
the number of data frames to receive including the CRC, which means, for example, in the
specific case of an 8-bit data frame checked by 16-bit CRC:


DMA_RX = Numb_of_data + 2


In receive only mode, the DMA reception channel counter should contain only the amount of
data transferred, excluding the CRC calculation. Then based on the complete transfer from
DMA, all the CRC values must be read back by software from FIFO as it works as a single
buffer in this mode.


At the end of the data and CRC transfers, the CRCERR flag in the SPIx_SR register is set if
corruption occurred during the transfer.


If packing mode is used, the LDMA_RX bit needs managing if the number of data is odd.


**Resetting the SPIx_TXCRC and SPIx_RXCRC values**


The SPIx_TXCRC and SPIx_RXCRC values are cleared automatically when new data is
sampled after a CRC phase. This allows the use of DMA circular mode (not available in
receive-only mode) in order to transfer data without any interruption, (several data blocks
covered by intermediate CRC checking phases).


RM0364 Rev 4 1039/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


If the SPI is disabled during a communication the following sequence must be followed:


1. Disable the SPI


2. Clear the CRCEN bit


3. Enable the CRCEN bit


4. Enable the SPI


_Note:_ _When the SPI interface is configured as a slave, the NSS internal signal needs to be kept_
_low during transaction of the CRC phase once the CRCNEXT signal is released. That is why_
_the CRC calculation cannot be used at NSS Pulse mode when NSS hardware mode should_

_be applied at slave normally._


_At TI mode, despite the fact that clock phase and clock polarity setting is fixed and_
_independent on SPIx_CR1 register, the corresponding setting CPOL=0 CPHA=1 has to be_
_kept at the SPIx_CR1 register anyway if CRC is applied. In addition, the CRC calculation_
_has to be reset between sessions by SPI disable sequence with re-enable the CRCEN bit_
_described above at both master and slave side, else CRC calculation can be corrupted at_
_this specific mode._

## **29.5 SPI interrupts**


During SPI communication an interrupt can be generated by the following events:


      - Transmit TXFIFO ready to be loaded


      - Data received in Receive RXFIFO


      - Master mode fault


      - Overrun error


      - TI frame format error


      - CRC protocol error


Interrupts can be enabled and disabled separately.


**Table 145. SPI interrupt requests**

|Interrupt event|Event flag|Enable Control bit|
|---|---|---|
|Transmit TXFIFO ready to be loaded|TXE|TXEIE|
|Data received in RXFIFO|RXNE|RXNEIE|
|Master Mode fault event|MODF|ERRIE|
|Overrun error|OVR|OVR|
|TI frame format error|FRE|FRE|
|CRC protocol error|CRCERR|CRCERR|



1040/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**

## **29.6 SPI registers**


The peripheral registers can be accessed by half-words (16-bit) or words (32-bit). SPI_DR
in addition can be accessed by 8-bit access.


**29.6.1** **SPI control register 1 (SPIx_CR1)**


Address offset: 0x00


Reset value: 0x0000

|15|14|13|12|11|10|9|8|7|6|5 4 3|Col12|Col13|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|BIDIM<br>ODE|BIDIOE|CRCE<br>N|CRCN<br>EXT|CRCL|RXONL<br>Y|SSM|SSI|LSBFIR<br>ST|SPE|BR[2:0]|BR[2:0]|BR[2:0]|MSTR|CPOL|CPHA|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 15 **BIDIMODE:** Bidirectional data mode enable.

This bit enables half-duplex communication using common single bidirectional data line.
Keep RXONLY bit clear when bidirectional mode is active.

_0: 2-line unidirectional data mode selected_

1: 1-line bidirectional data mode selected


Bit 14 **BIDIOE:** Output enable in bidirectional mode

This bit combined with the BIDIMODE bit selects the direction of transfer in bidirectional

mode.

0: Output disabled (receive-only mode)
1: Output enabled (transmit-only mode)

_Note: In master mode, the MOSI pin is used and in slave mode, the MISO pin is used._


Bit 13 **CRCEN:** Hardware CRC calculation enable

0: CRC calculation disabled

1: CRC calculation enabled

_Note: This bit should be written only when SPI is disabled (SPE = ‘0’) for correct operation._


Bit 12 **CRCNEXT:** Transmit CRC next

0: Next transmit value is from Tx buffer.

1: Next transmit value is from Tx CRC register.

_Note: This bit has to be written as soon as the last data is written in the SPIx_DR register._


Bit 11 **CRCL:** CRC length

This bit is set and cleared by software to select the CRC length.
0: 8-bit CRC length
1: 16-bit CRC length

_Note: This bit should be written only when SPI is disabled (SPE = ‘0’) for correct operation._


RM0364 Rev 4 1041/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


Bit 10 **RXONLY:** Receive only mode enabled.

This bit enables simplex communication using a single unidirectional line to receive data
exclusively. Keep BIDIMODE bit clear when receive only mode is active.This bit is also
useful in a multislave system in which this particular slave is not accessed, the output from
the accessed slave is not corrupted.
0: Full-duplex (Transmit and receive)
1: Output disabled (Receive-only mode)


Bit 9 **SSM:** Software slave management

When the SSM bit is set, the NSS pin input is replaced with the value from the SSI bit.
0: Software slave management disabled
1: Software slave management enabled

_Note: This bit is not used in SPI TI mode._


Bit 8 **SSI:** Internal slave select

This bit has an effect only when the SSM bit is set. The value of this bit is forced onto the
NSS pin and the I/O value of the NSS pin is ignored.

_Note: This bit is not used in SPI TI mode._


Bit 7 **LSBFIRST** _**:**_ Frame format

0: data is transmitted / received with the MSB first

1: data is transmitted / received with the LSB first

_Note: 1. This bit should not be changed when communication is ongoing._

_2. This bit is not used in SPI TI mode._


Bit 6 **SPE:** SPI enable

0: Peripheral disabled
1: Peripheral enabled

_Note: When disabling the SPI, follow the procedure described in Procedure for disabling the_
_SPI on page 1026._


Bits 5:3 **BR[2:0]:** Baud rate control

000: f PCLK /2
001: f PCLK /4
010: f PCLK /8
011: f PCLK /16
100: f PCLK /32
101: f PCLK /64
110: f PCLK /128
111: f PCLK /256

_Note: These bits should not be changed when communication is ongoing._


Bit 2 **MSTR:** Master selection

0: Slave configuration
1: Master configuration

_Note: This bit should not be changed when communication is ongoing._


1042/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


Bit 1 **CPOL:** Clock polarity

0: CK to 0 when idle

1: CK to 1 when idle

_Note: This bit should not be changed when communication is ongoing._

_This bit is not used in SPI TI mode except the case when CRC is applied at TI mode._


Bit 0 **CPHA:** Clock phase

0: The first clock transition is the first data capture edge
1: The second clock transition is the first data capture edge

_Note: This bit should not be changed when communication is ongoing._

_This bit is not used in SPI TI mode except the case when CRC is applied at TI mode._


**29.6.2** **SPI control register 2 (SPIx_CR2)**


Address offset: 0x04


Reset value: 0x0700

|15|14|13|12|11 10 9 8|Col6|Col7|Col8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|LDMA<br>_TX|LDMA<br>_RX|FRXT<br>H|DS[3:0]|DS[3:0]|DS[3:0]|DS[3:0]|TXEIE|RXNEIE|ERRIE|FRF|NSSP|SSOE|TXDMAEN|RXDMAEN|
||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 15 Reserved, must be kept at reset value.


Bit 14 **LDMA_TX:** Last DMA transfer for transmission

This bit is used in data packing mode, to define if the total number of data to transmit by DMA
is odd or even. It has significance only if the TXDMAEN bit in the SPIx_CR2 register is set
and if packing mode is used (data length =< 8-bit and write access to SPIx_DR is 16-bit
wide). It has to be written when the SPI is disabled (SPE = 0 in the SPIx_CR1 register).

0: Number of data to transfer is even

1: Number of data to transfer is odd

_Note: Refer to Procedure for disabling the SPI on page 1026 if the CRCEN bit is set._


Bit 13 **LDMA_RX** : Last DMA transfer for reception
Th is bit is used in data packing mode, to define if the total number of data to receive by DMA
is odd or even. It has significance only if the RXDMAEN bit in the SPIx_CR2 register is set
and if packing mode is used (data length =< 8-bit and write access to SPIx_DR is 16-bit
wide). It has to be written when the SPI is disabled (SPE = 0 in the SPIx_CR1 register).

0: Number of data to transfer is even

1: Number of data to transfer is odd

_Note: Refer to Procedure for disabling the SPI on page 1026 if the CRCEN bit is set._


Bit 12 **FRXTH** : FIFO reception threshold

This bit is used to set the threshold of the RXFIFO that triggers an RXNE event
0: RXNE event is generated if the FIFO level is greater than or equal to 1/2 (16-bit)
1: RXNE event is generated if the FIFO level is greater than or equal to 1/4 (8-bit)


RM0364 Rev 4 1043/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


Bits 11:8 **DS[3:0]** : Data size

These bits configure the data length for SPI transfers.

0000: Not used

0001: Not used

0010: Not used

0011: 4-bit

0100: 5-bit

0101: 6-bit

0110: 7-bit

0111: 8-bit

1000: 9-bit

1001: 10-bit

1010: 11-bit

1011: 12-bit

1100: 13-bit

1101: 14-bit

1110: 15-bit

1111: 16-bit

If software attempts to write one of the “Not used” values, they are forced to the value “0111”
(8-bit)


Bit 7 **TXEIE:** Tx buffer empty interrupt enable

0: TXE interrupt masked
1: TXE interrupt not masked. Used to generate an interrupt request when the TXE flag is set.


Bit 6 **RXNEIE:** RX buffer not empty interrupt enable

0: RXNE interrupt masked
1: RXNE interrupt not masked. Used to generate an interrupt request when the RXNE flag is
set.


Bit 5 **ERRIE:** Error interrupt enable

This bit controls the generation of an interrupt when an error condition occurs (CRCERR,
OVR, MODF in SPI mode, FRE at TI mode).
0: Error interrupt is masked
1: Error interrupt is enabled


Bit 4 **FRF** : Frame format

0: SPI Motorola mode

1 SPI TI mode

_Note: This bit must be written only when the SPI is disabled (SPE=0)._


Bit 3 **NSSP** : NSS pulse management

This bit is used in master mode only. it allows the SPI to generate an NSS pulse between two
consecutive data when doing continuous transfers. In the case of a single data transfer, it
forces the NSS pin high level after the transfer.

It has no meaning if CPHA = ’1’, or FRF = ’1’.

0: No NSS pulse
1: NSS pulse generated

_Note: 1. This bit must be written only when the SPI is disabled (SPE=0)._

_2. This bit is not used in SPI TI mode._


1044/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


Bit 2 **SSOE:** SS output enable

0: SS output is disabled in master mode and the SPI interface can work in multimaster
configuration
1: SS output is enabled in master mode and when the SPI interface is enabled. The SPI
interface cannot work in a multimaster environment.

_Note: This bit is not used in SPI TI mode._


Bit 1 **TXDMAEN:** Tx buffer DMA enable

When this bit is set, a DMA request is generated whenever the TXE flag is set.

0: Tx buffer DMA disabled

1: Tx buffer DMA enabled


Bit 0 **RXDMAEN:** Rx buffer DMA enable

When this bit is set, a DMA request is generated whenever the RXNE flag is set.

0: Rx buffer DMA disabled

1: Rx buffer DMA enabled


**29.6.3** **SPI status register (SPIx_SR)**


Address offset: 0x08


Reset value: 0x0002

|15|14|13|12 11|Col5|10 9|Col7|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|FTLVL[1:0]|FTLVL[1:0]|FRLVL[1:0]|FRLVL[1:0]|FRE|BSY|OVR|MODF|CRCE<br>RR|Res.|Res.|TXE|RXNE|
||||r|r|r|r|r|r|r|r|rc_w0|||r|r|



Bits 15:13 Reserved, must be kept at reset value.


Bits 12:11 **FTLVL[1:0]:** FIFO transmission level

These bits are set and cleared by hardware.
00: FIFO empty

01: 1/4 FIFO

10: 1/2 FIFO

11: FIFO full (considered as FULL when the FIFO threshold is greater than 1/2)


Bits 10:9 **FRLVL[1:0]** : FIFO reception level

These bits are set and cleared by hardware.
00: FIFO empty

01: 1/4 FIFO

10: 1/2 FIFO

11: FIFO full

_Note: These bits are not used in SPI receive-only mode while CRC calculation is enabled._


Bit 8 **FRE** : Frame format error

This flag is used for SPI in TI slave mode. Refer to _Section 29.4.11: SPI error flags_ .
This flag is set by hardware and reset when SPIx_SR is read by software.

0: No frame format error

1: A frame format error occurred


RM0364 Rev 4 1045/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


Bit 7 **BSY:** Busy flag

0: SPI not busy
1: SPI is busy in communication or Tx buffer is not empty
This flag is set and cleared by hardware.

_Note: The BSY flag must be used with caution: refer to Section 29.4.10: SPI status flags and_

_Procedure for disabling the SPI on page 1026._


Bit 6 **OVR:** Overrun flag

0: No overrun occurred

1: Overrun occurred

This flag is set by hardware and reset by a software sequence.


Bit 5 **MODF:** Mode fault

0: No mode fault occurred

1: Mode fault occurred

This flag is set by hardware and reset by a software sequence. Refer to _Section : Mode fault_
_(MODF) on page 1036_ for the software sequence.


Bit 4 **CRCERR:** CRC error flag

0: CRC value received matches the SPIx_RXCRCR value
1: CRC value received does not match the SPIx_RXCRCR value

Note: This flag is set by hardware and cleared by software writing 0.


Bits 3:2 Reserved, must be kept at reset value.


Bit 1 **TXE:** Transmit buffer empty

0: Tx buffer not empty
1: Tx buffer empty


Bit 0 **RXNE:** Receive buffer not empty

0: Rx buffer empty
1: Rx buffer not empty


**29.6.4** **SPI data register (SPIx_DR)**


Address offset: 0x0C


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **DR[15:0]:** Data register

Data received or to be transmitted

The data register serves as an interface between the Rx and Tx FIFOs. When the data
register is read, RxFIFO is accessed while the write to data register accesses TxFIFO (See
_Section 29.4.9: Data transmission and reception procedures_ ).

_Note: Data is always right-aligned. Unused bits are ignored when writing to the register, and_
_read as zero when the register is read. The Rx threshold setting must always_
_correspond with the read access currently used._


1046/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


**29.6.5** **SPI CRC polynomial register (SPIx_CRCPR)**


Address offset: 0x10


Reset value: 0x0007

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **CRCPOLY[15:0]:** CRC polynomial register

This register contains the polynomial for the CRC calculation.
The CRC polynomial (0x0007) is the reset value of this register. Another polynomial can be
configured as required.


_Note: The polynomial value should be odd only. No even value is supported._


**29.6.6** **SPI Rx CRC register (SPIx_RXCRCR)**


Address offset: 0x14


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 15:0 **RXCRC[15:0]:** Rx CRC register

When CRC calculation is enabled, the RXCRC[15:0] bits contain the computed CRC value of
the subsequently received bytes. This register is reset when the CRCEN bit in SPIx_CR1
register is written to 1. The CRC is calculated serially using the polynomial programmed in
the SPIx_CRCPR register.
Only the 8 LSB bits are considered when the CRC frame format is set to be 8-bit length
(CRCL bit in the SPIx_CR1 is cleared). CRC calculation is done based on any CRC8
standard.

The entire 16-bits of this register are considered when a 16-bit CRC frame format is selected
(CRCL bit in the SPIx_CR1 register is set). CRC calculation is done based on any CRC16
standard.

_A read to this register when the BSY Flag is set could return an incorrect value._


**29.6.7** **SPI Tx CRC register (SPIx_TXCRCR)**


Address offset: 0x18


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



RM0364 Rev 4 1047/1124



1049


**Serial peripheral interface (SPI)** **RM0364**


Bits 15:0 **TXCRC[15:0]:** Tx CRC register

When CRC calculation is enabled, the TXCRC[7:0] bits contain the computed CRC value of
the subsequently transmitted bytes. This register is reset when the CRCEN bit of SPIx_CR1
is written to 1. The CRC is calculated serially using the polynomial programmed in the
SPIx_CRCPR register.
Only the 8 LSB bits are considered when the CRC frame format is set to be 8-bit length
(CRCL bit in the SPIx_CR1 is cleared). CRC calculation is done based on any CRC8
standard.

The entire 16-bits of this register are considered when a 16-bit CRC frame format is selected
(CRCL bit in the SPIx_CR1 register is set). CRC calculation is done based on any CRC16
standard.

_A read to this register when the BSY flag is set could return an incorrect value._


1048/1124 RM0364 Rev 4


**RM0364** **Serial peripheral interface (SPI)**


**29.6.8** **SPI register map**


_Table 146_ shows the SPI register map and reset values.


**Table 146. SPI register map and reset values**





































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**SPIx_CR1**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|BIDIMODE|BIDIOE|CRCEN|CRCNEXT|CRCL|RXONLY|SSM|SSI|LSBFIRST|SPE|BR [2:0]|BR [2:0]|BR [2:0]|MSTR|CPOL|CPHA|
|0x00|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x04|**SPIx_CR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LDMA_TX|LDMA_RX|FRXTH|DS[3:0]|DS[3:0]|DS[3:0]|DS[3:0]|TXEIE|RXNEIE|ERRIE|FRF|NSSP|_SSOE_|TXDMAEN|RXDMAEN|
|0x04|Reset value||||||||||||||||||0|0|0|0|1|1|1|0|0|0|0|0|0|0|0|
|0x08|**SPIx_SR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FTLVL[1:0]|FTLVL[1:0]|FRLVL[1:0]|FRLVL[1:0]|FRE|BSY|OVR|MODF|CRCERR|Res.|Res.|TXE|RXNE|
|0x08|Reset value||||||||||||||||||||0|0|0|0|0|0|0|0|0|||1|0|
|0x0C|**SPIx_DR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|
|0x0C|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**SPIx_CRCPR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|
|0x10|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|1|1|1|
|0x14|**SPIx_RXCRCR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|
|0x14|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x18|**SPIx_TXCRCR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|
|0x18|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


Refer to _Section 2.2 on page 47_ for the register boundary addresses.


RM0364 Rev 4 1049/1124



1049


