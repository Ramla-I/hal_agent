**Serial peripheral interface (SPI)** **RM0041**

# **21 Serial peripheral interface (SPI)**


**Low-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 16 and 32 Kbytes.


**Medium-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 64 and 128 Kbytes.


**High-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 256 and 512 Kbytes.

## **21.1 SPI introduction**


The serial peripheral interface (SPI) allows half/ full-duplex, synchronous, serial
communication with external devices. The interface can be configured as the master and in
this case it provides the communication clock (SCK) to the external slave device. The
interface is also capable of operating in multimaster configuration.


It may be used for a variety of purposes, including simplex synchronous transfers on two
lines with a possible bidirectional data line or reliable communication using CRC checking.


**Warning:** **Since some SPI1 and SPI3 pins may be mapped onto some**
**pins used by the JTAG interface (SPI1/3_NSS onto JTDI,**
**SPI1/3_SCK onto JTDO and SPI1/3_MISO onto NJTRST), you**
**may either:**
**– disable the JTAG and use the SWD interface prior to**
**configuring the pins listed as SPI IOs (when debugging the**
**application), or**
**– disable both JTAG/SWD interfaces (for standalone**
**applications).**
**For more information on the configuration of the JTAG/SWD**
**interface pins, refer to** _**Section 7.3.3: JTAG/SWD alternate**_
_**function remapping**_ **.**


536/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**

## **21.2 SPI main features**


**21.2.1** **SPI features**


      - Full-duplex synchronous transfers on three lines


      - Simplex synchronous transfers on two lines with or without a bidirectional data line


      - 8- or 16-bit transfer frame format selection


      - Master or slave operation


      - Multimaster mode capability


      - 8 master mode baud rate prescalers (f PCLK /2 max.)


      - Slave mode frequency (f PCLK /2 max)


      - Faster communication for both master and slave


      - NSS management by hardware or software for both master and slave: dynamic change
of master/slave operations


      - Programmable clock polarity and phase


      - Programmable data order with MSB-first or LSB-first shifting


      - Dedicated transmission and reception flags with interrupt capability


      - SPI bus busy status flag


      - Hardware CRC feature for reliable communication:


–
CRC value can be transmitted as last byte in Tx mode


–
Automatic CRC error checking for last received byte


      - Master mode fault, overrun and CRC error flags with interrupt capability


      - 1-byte transmission and reception buffer with DMA capability: Tx and Rx requests


RM0041 Rev 6 537/709



565


**Serial peripheral interface (SPI)** **RM0041**

## **21.3 SPI functional description**


**21.3.1** **General description**


The block diagram of the SPI is shown in _Figure 222_ .


**Figure 222. SPI block diagram**









































Usually, the SPI is connected to external devices through four pins:






      - MISO: Master In / Slave Out data. This pin can be used to transmit data in slave mode
and receive data in master mode.


      - MOSI: Master Out / Slave In data. This pin can be used to transmit data in master
mode and receive data in slave mode.


      - SCK: Serial Clock output for SPI masters and input for SPI slaves.


      - NSS: Slave select. This is an optional pin to select a slave device. This pin acts as a
‘chip select’ to let the SPI master communicate with slaves individually and to avoid
contention on the data lines. Slave NSS inputs can be driven by standard IO ports on
the master device. The NSS pin may also be used as an output if enabled (SSOE bit)
and driven low if the SPI is in master configuration. In this manner, all NSS pins from
devices connected to the Master NSS pin see a low level and become slaves when
they are configured in NSS hardware mode. When configured in master mode with
NSS configured as an input (MSTR=1 and SSOE=0) and if NSS is pulled low, the SPI
enters the master mode fault state: the MSTR bit is automatically cleared and the
device is configured in slave mode (refer to _Section 21.3.10_ ).


A basic example of interconnections between a single master and a single slave is
illustrated in _Figure 223_ .


538/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


**Figure 223. Single master/ single slave application**








|Col1|MISO MISO|Col3|
|---|---|---|
||MOSI<br>MOSI|MOSI<br>MOSI|
||SCK<br>SCK||



1. Here, the NSS pin is configured as an input.


The MOSI pins are connected together and the MISO pins are connected together. In this
way data is transferred serially between master and slave (most significant bit first).


The communication is always initiated by the master. When the master device transmits
data to a slave device via the MOSI pin, the slave device responds via the MISO pin. This
implies full-duplex communication with both data out and data in synchronized with the
same clock signal (which is provided by the master device via the SCK pin).


**Slave select (NSS) pin management**


Hardware or software slave select management can be set using the SSM bit in the
SPI_CR1 register.


- Software NSS management (SSM = 1)


The slave select information is driven internally by the value of the SSI bit in the
SPI_CR1 register. The external NSS pin remains free for other application uses.


- Hardware NSS management (SSM = 0)


Two configurations are possible depending on the NSS output configuration (SSOE bit
in register SPI_CR2).


–
NSS output enabled (SSM = 0, SSOE = 1)


This configuration is used only when the device operates in master mode. The
NSS signal is driven low when the master starts the communication and is kept
low until the SPI is disabled.


–
NSS output disabled (SSM = 0, SSOE = 0)


This configuration allows multimaster capability for devices operating in master
mode. For devices set as slave, the NSS pin acts as a classical NSS input: the
slave is selected when NSS is low and deselected when NSS high.


RM0041 Rev 6 539/709



565


**Serial peripheral interface (SPI)** **RM0041**


**Clock phase and clock polarity**


Four possible timing relationships may be chosen by software, using the CPOL and CPHA
bits in the SPI_CR1 register. The CPOL (clock polarity) bit controls the steady state value of
the clock when no data is being transferred. This bit affects both master and slave modes. If
CPOL is reset, the SCK pin has a low-level idle state. If CPOL is set, the SCK pin has a
high-level idle state.


If the CPHA (clock phase) bit is set, the second edge on the SCK pin (falling edge if the
CPOL bit is reset, rising edge if the CPOL bit is set) is the MSBit capture strobe. Data are
latched on the occurrence of the second clock transition. If the CPHA bit is reset, the first
edge on the SCK pin (falling edge if CPOL bit is set, rising edge if CPOL bit is reset) is the
MSBit capture strobe. Data are latched on the occurrence of the first clock transition.


The combination of the CPOL (clock polarity) and CPHA (clock phase) bits selects the data
capture clock edge.


_Figure 224_, shows an SPI transfer with the four combinations of the CPHA and CPOL bits.
The diagram may be interpreted as a master or slave timing diagram where the SCK pin,
the MISO pin, the MOSI pin are directly connected between the master and the slave
device.


_Note:_ _Prior to changing the CPOL/CPHA bits the SPI must be disabled by resetting the SPE bit._


_Master and slave must be programmed with the same timing mode._


_The idle state of SCK must correspond to the polarity selected in the SPI_CR1 register (by_
_pulling up SCK if CPOL=1 or pulling down SCK if CPOL=0)._


_The Data Frame Format (8- or 16-bit) is selected through the DFF bit in SPI_CR1 register,_
_and determines the data length during transmission/reception._


540/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


**Figure 224. Data clock timing diagram**













1. These timings are shown with the LSBFIRST bit reset in the SPI_CR1 register.


**Data frame format**


Data can be shifted out either MSB-first or LSB-first depending on the value of the
LSBFIRST bit in the SPI_CR1 register.





Each data frame is 8 or 16 bits long depending on the size of the data programmed using
the DFF bit in the SPI_CR1 register. The selected data frame format is applicable for
transmission and/or reception.


RM0041 Rev 6 541/709



565


**Serial peripheral interface (SPI)** **RM0041**


**21.3.2** **Configuring the SPI in slave mode**


In the slave configuration, the serial clock is received on the SCK pin from the master
device. The value set in the BR[2:0] bits in the SPI_CR1 register, does not affect the data
transfer rate.


_Note:_ _It is recommended to enable the SPI slave before the master sends the clock. If not,_
_undesired data transmission might occur. The data register of the slave needs to be ready_
_before the first edge of the communication clock or before the end of the ongoing_
_communication. It is mandatory to have the polarity of the communication clock set to the_
_steady state value before the slave and the master are enabled._


Follow the procedure below to configure the SPI in slave mode:


**Procedure**


1. Set the DFF bit to define 8- or 16-bit data frame format


2. Select the CPOL and CPHA bits to define one of the four relationships between the
data transfer and the serial clock (see _Figure 224_ ). For correct data transfer, the CPOL
and CPHA bits must be configured in the same way in the slave device and the master
device.


3. The frame format (MSB-first or LSB-first depending on the value of the LSBFIRST bit in
the SPI_CR1 register) must be the same as the master device.


4. In Hardware mode (refer to _Slave select (NSS) pin management_ ), the NSS pin must be
connected to a low level signal during the complete byte transmit sequence. In NSS
software mode, set the SSM bit and clear the SSI bit in the SPI_CR1 register.


5. Clear the MSTR bit and set the SPE bit (both in the SPI_CR1 register) to assign the
pins to alternate functions.


In this configuration the MOSI pin is a data input and the MISO pin is a data output.


**Transmit sequence**


The data byte is parallel-loaded into the Tx buffer during a write cycle.


The transmit sequence begins when the slave device receives the clock signal and the most
significant bit of the data on its MOSI pin. The remaining bits (the 7 bits in 8-bit data frame
format, and the 15 bits in 16-bit data frame format) are loaded into the shift-register. The
TXE flag in the SPI_SR register is set on the transfer of data from the Tx Buffer to the shift
register and an interrupt is generated if the TXEIE bit in the SPI_CR2 register is set.


**Receive sequence**


For the receiver, when data transfer is complete:


      - The Data in shift register is transferred to Rx Buffer and the RXNE flag (SPI_SR
register) is set


      - An Interrupt is generated if the RXNEIE bit is set in the SPI_CR2 register.


After the last sampling clock edge the RXNE bit is set, a copy of the data byte received in
the shift register is moved to the Rx buffer. When the SPI_DR register is read, the SPI
peripheral returns this buffered value.


Clearing of the RXNE bit is performed by reading the SPI_DR register.


542/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


**21.3.3** **Configuring the SPI in master mode**


In the master configuration, the serial clock is generated on the SCK pin.


**Procedure**


1. Select the BR[2:0] bits to define the serial clock baud rate (see SPI_CR1 register).


2. Select the CPOL and CPHA bits to define one of the four relationships between the
data transfer and the serial clock (see _Figure 224_ ).


3. Set the DFF bit to define 8- or 16-bit data frame format


4. Configure the LSBFIRST bit in the SPI_CR1 register to define the frame format.


5. If the NSS pin is required in input mode, in hardware mode, connect the NSS pin to a
high-level signal during the complete byte transmit sequence. In NSS software mode,
set the SSM and SSI bits in the SPI_CR1 register. If the NSS pin is required in output
mode, the SSOE bit only should be set.


6. The MSTR and SPE bits must be set (they remain set only if the NSS pin is connected
to a high-level signal).


In this configuration the MOSI pin is a data output and the MISO pin is a data input.


**Transmit sequence**


The transmit sequence begins when a byte is written in the Tx Buffer.


The data byte is parallel-loaded into the shift register (from the internal bus) during the first
bit transmission and then shifted out serially to the MOSI pin MSB first or LSB first
depending on the LSBFIRST bit in the SPI_CR1 register. The TXE flag is set on the transfer
of data from the Tx Buffer to the shift register and an interrupt is generated if the TXEIE bit in
the SPI_CR2 register is set.


**Receive sequence**


For the receiver, when data transfer is complete:


      - The data in the shift register is transferred to the RX Buffer and the RXNE flag is set


      - An interrupt is generated if the RXNEIE bit is set in the SPI_CR2 register


At the last sampling clock edge the RXNE bit is set, a copy of the data byte received in the
shift register is moved to the Rx buffer. When the SPI_DR register is read, the SPI
peripheral returns this buffered value.


Clearing the RXNE bit is performed by reading the SPI_DR register.


A continuous transmit stream can be maintained if the next data to be transmitted is put in
the Tx buffer once the transmission is started. Note that TXE flag should be ‘1 before any
attempt to write the Tx buffer is made.


_Note:_ _When a master is communicating with SPI slaves which need to be de-selected between_
_transmissions, the NSS pin must be configured as GPIO or another GPIO must be used and_
_toggled by software._


**21.3.4** **Configuring the SPI for half-duplex communication**


The SPI is capable of operating in half-duplex mode in 2 configurations.


      - 1 clock and 1 bidirectional data wire


      - 1 clock and 1 data wire (receive-only or transmit-only)


RM0041 Rev 6 543/709



565


**Serial peripheral interface (SPI)** **RM0041**


**1 clock and 1 bidirectional data wire (BIDIMODE = 1)**


This mode is enabled by setting the BIDIMODE bit in the SPI_CR1 register. In this mode
SCK is used for the clock and MOSI in master or MISO in slave mode is used for data
communication. The transfer direction (Input/Output) is selected by the BIDIOE bit in the
SPI_CR1 register. When this bit is 1, the data line is output otherwise it is input.


**1 clock and 1 unidirectional data wire (BIDIMODE = 0)**


In this mode, the application can use the SPI either in transmit-only mode or in receive-only
mode.


      - Transmit-only mode is similar to full-duplex mode (BIDIMODE=0, RXONLY=0): the
data are transmitted on the transmit pin (MOSI in master mode or MISO in slave mode)
and the receive pin (MISO in master mode or MOSI in slave mode) can be used as a
general-purpose IO. In this case, the application just needs to ignore the Rx buffer (if
the data register is read, it does not contain the received value).


      - In receive-only mode, the application can disable the SPI output function by setting the
RXONLY bit in the SPI_CR1 register. In this case, it frees the transmit IO pin (MOSI in
master mode or MISO in slave mode), so it can be used for other purposes.


To start the communication in receive-only mode, configure and enable the SPI:


      - In master mode, the communication starts immediately and stops when the SPE bit is
cleared and the current reception stops. There is no need to read the BSY flag in this
mode. It is always set when an SPI communication is ongoing.


      - In slave mode, the SPI continues to receive as long as the NSS is pulled down (or the
SSI bit is cleared in NSS software mode) and the SCK is running.


**21.3.5** **Data transmission and reception procedures**


**Rx and Tx buffers**


In reception, data are received and then stored into an internal Rx buffer while In
transmission, data are first stored into an internal Tx buffer before being transmitted.


A read access of the SPI_DR register returns the Rx buffered value whereas a write access
to the SPI_DR stores the written data into the Tx buffer.


544/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


**Start sequence in master mode**


      - In full-duplex (BIDIMODE=0 and RXONLY=0)


–
The sequence begins when data are written into the SPI_DR register (Tx buffer).


–
The data are then parallel loaded from the Tx buffer into the 8-bit shift register
during the first bit transmission and then shifted out serially to the MOSI pin.


–
At the same time, the received data on the MISO pin is shifted in serially to the 8bit shift register and then parallel loaded into the SPI_DR register (Rx buffer).


      - In unidirectional receive-only mode (BIDIMODE=0 and RXONLY=1)


–
The sequence begins as soon as SPE=1


–
Only the receiver is activated and the received data on the MISO pin are shifted in
serially to the 8-bit shift register and then parallel loaded into the SPI_DR register
(Rx buffer).


      - In bidirectional mode, when transmitting (BIDIMODE=1 and BIDIOE=1)


–
The sequence begins when data are written into the SPI_DR register (Tx buffer).


–
The data are then parallel loaded from the Tx buffer into the 8-bit shift register
during the first bit transmission and then shifted out serially to the MOSI pin.


– No data are received.


      - In bidirectional mode, when receiving (BIDIMODE=1 and BIDIOE=0)


–
The sequence begins as soon as SPE=1 and BIDIOE=0.


–
The received data on the MOSI pin are shifted in serially to the 8-bit shift register
and then parallel loaded into the SPI_DR register (Rx buffer).


–
The transmitter is not activated and no data are shifted out serially to the MOSI
pin.


**Start sequence in slave mode**


      - In full-duplex mode (BIDIMODE=0 and RXONLY=0)


–
The sequence begins when the slave device receives the clock signal and the first
bit of the data on its MOSI pin. The 7 remaining bits are loaded into the shift
register.


–
At the same time, the data are parallel loaded from the Tx buffer into the 8-bit shift
register during the first bit transmission, and then shifted out serially to the MISO
pin. The software must have written the data to be sent before the SPI master
device initiates the transfer.


      - In unidirectional receive-only mode (BIDIMODE=0 and RXONLY=1)


–
The sequence begins when the slave device receives the clock signal and the first
bit of the data on its MOSI pin. The 7 remaining bits are loaded into the shift
register.


–
The transmitter is not activated and no data are shifted out serially to the MISO
pin.


      - In bidirectional mode, when transmitting (BIDIMODE=1 and BIDIOE=1)


–
The sequence begins when the slave device receives the clock signal and the first
bit in the Tx buffer is transmitted on the MISO pin.


–
The data are then parallel loaded from the Tx buffer into the 8-bit shift register
during the first bit transmission and then shifted out serially to the MISO pin. The


RM0041 Rev 6 545/709



565


**Serial peripheral interface (SPI)** **RM0041**


software must have written the data to be sent before the SPI master device

initiates the transfer.


– No data are received.


      - In bidirectional mode, when receiving (BIDIMODE=1 and BIDIOE=0)


–
The sequence begins when the slave device receives the clock signal and the first
bit of the data on its MISO pin.


–
The received data on the MISO pin are shifted in serially to the 8-bit shift register
and then parallel loaded into the SPI_DR register (Rx buffer).


–
The transmitter is not activated and no data are shifted out serially to the MISO
pin.


**Handling data transmission and reception**


The TXE flag (Tx buffer empty) is set when the data are transferred from the Tx buffer to the
shift register. It indicates that the internal Tx buffer is ready to be loaded with the next data.
An interrupt can be generated if the TXEIE bit in the SPI_CR2 register is set. Clearing the
TXE bit is performed by writing to the SPI_DR register.


_Note:_ _The software must ensure that the TXE flag is set to 1 before attempting to write to the Tx_
_buffer. Otherwise, it overwrites the data previously written to the Tx buffer._


The RXNE flag (Rx buffer not empty) is set on the last sampling clock edge, when the data
are transferred from the shift register to the Rx buffer. It indicates that data are ready to be
read from the SPI_DR register. An interrupt can be generated if the RXNEIE bit in the
SPI_CR2 register is set. Clearing the RXNE bit is performed by reading the SPI_DR
register.


For some configurations, the BSY flag can be used during the last data transfer to wait until
the completion of the transfer.


Full-duplex transmit and receive procedure in master or slave mode (BIDIMODE=0 and
RXONLY=0)


The software has to follow this procedure to transmit and receive data (see _Figure 225_ and
_Figure 226_ ):


1. Enable the SPI by setting the SPE bit to 1.


2. Write the first data item to be transmitted into the SPI_DR register (this clears the TXE
flag).


3. Wait until TXE=1 and write the second data item to be transmitted. Then wait until
RXNE=1 and read the SPI_DR to get the first received data item (this clears the RXNE
bit). Repeat this operation for each data item to be transmitted/received until the n–1
received data.


4. Wait until RXNE=1 and read the last received data.


5. Wait until TXE=1 and then wait until BSY=0 before disabling the SPI.


This procedure can also be implemented using dedicated interrupt subroutines launched at
each rising edges of the RXNE or TXE flag.


546/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


**Figure 225. TXE/RXNE/BSY behavior in Master / full-duplex mode (BIDIMODE=0 and**
**RXONLY=0) in case of continuous transfers**






















|b0|Col2|b1|b2|b3|b4|b5|b6|b7|Col10|b0|b1|b2|b3|b4|b5|b6|b7|Col19|b0|b1|b2|b3|b4|b5|b6|b7|Col28|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|||set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software||set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software||||||||||
|||||||||||||||||||||||||||||
|0|xF1|0xF2<br>|0xF2<br>|0xF2<br>|0xF2<br>|0xF2<br>|0xF2<br>|0xF2<br>|0xF2<br>|0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|0xF3||||||||||
||||||||||||||||||||DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|
||||||||||||DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|
||||||||||||DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 2 = 0xA2|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3|DATA 3 = 0xA3||
|b0|b0|b1|b2|b3|b4|b5|b6|b7|b7|b0|b1|b2|b3|b4|b5|b6|b7|b7|b0|b1|b2|b3|b4|b5|b6|b|7|
|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware||cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|||||||||||
|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware||cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|||||||||||
|||||||||||||||||||||||||||||

















RM0041 Rev 6 547/709



565


**Serial peripheral interface (SPI)** **RM0041**


**Figure 226. TXE/RXNE/BSY behavior in Slave / full-duplex mode (BIDIMODE=0,**
**RXONLY=0) in case of continuous transfers**






















|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|Col17|Col18|Col19|Col20|Col21|Col22|Col23|Col24|Col25|Col26|Col27|Col28|Col29|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
||||||||||||||||||||||||||||||
|b0|b0|b1|b2|b3|b4|b5|b6|b7|b0|b0|b1|b2|b3|b4|b5|b6|b7|b7|b|0|b1|b2|b3|b4|b5|b6||b7|
|||set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|||set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|||set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware||
|||set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|||set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|||set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware||
||||||||||||||||||||||||||||||
|0|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|||0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|0xF3||||||||||||
||||||||||||||||||||||||||||||
||||||||||||||||||||||||||||||
|b0|b0|b1|b2|b3|b4|b5|b6|b7|b|0|b1|b2|b3|b4|b5|b6|b7|b7|b0|b0|b1|b2|b3|b4|b5|b6||b7|
|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software||||||||||||

















**Transmit-only procedure (BIDIMODE=0 RXONLY=0)**


In this mode, the procedure can be reduced as described below and the BSY bit can be
used to wait until the completion of the transmission (see _Figure 227_ and _Figure 228_ ).


1. Enable the SPI by setting the SPE bit to 1.


2. Write the first data item to send into the SPI_DR register (this clears the TXE bit).


3. Wait until TXE=1 and write the next data item to be transmitted. Repeat this step for
each data item to be transmitted.


4. After writing the last data item into the SPI_DR register, wait until TXE=1, then wait until
BSY=0, this indicates that the transmission of the last data is complete.


This procedure can be also implemented using dedicated interrupt subroutines launched at
each rising edge of the TXE flag.


_Note:_ _During discontinuous communications, there is a 2 APB clock period delay between the_
_write operation to SPI_DR and the BSY bit setting. As a consequence, in transmit-only_
_mode, it is mandatory to wait first until TXE is set and then until BSY is cleared after writing_
_the last data._


_After transmitting two data items in transmit-only mode, the OVR flag is set in the SPI_SR_
_register since the received data are never read._


548/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


**Figure 227. TXE/BSY behavior in Master transmit-only mode (BIDIMODE=0 and RXONLY=0)**
**in case of continuous transfers**










|b0 b1|b2|b3|b4|b5|b6|b7|b0|b1|b2|b3|b4|b5|b6|b7|b0|b1|b2|b3|b4|b5|b6|b7|Col24|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software||set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software||||||||||
|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software||set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software||||||||||
|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software||||||||||||||||||
|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|0xF3||||||||||
|||||||||||||||||||||||||













**Figure 228. TXE/BSY in Slave transmit-only mode (BIDIMODE=0 and RXONLY=0) in case of**
**continuous transfers**














|0 b1|b2|b3|b4|b5|b6|b7|Col8|b0|Col10|b1|b2|b3|b4|b5|b6|b7|Col18|b0|b1|b2|b3|b4|b5|b6|b7|Col27|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software||||set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|||set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware||
|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software||||set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|||set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware||
|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|set by hardware<br>cleared by software|||||||||||||||||||||
|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|xF1<br>0xF2|||0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|||||||||||
||||||||||||||||||||||||||||







**Bidirectional transmit procedure (BIDIMODE=1 and BIDIOE=1)**


In this mode, the procedure is similar to the procedure in Transmit-only mode except that
the BIDIMODE and BIDIOE bits both have to be set in the SPI_CR2 register before enabling
the SPI.


**Unidirectional receive-only procedure (BIDIMODE=0 and RXONLY=1)**


In this mode, the procedure can be reduced as described below (see _Figure 229_ ):


RM0041 Rev 6 549/709



565


**Serial peripheral interface (SPI)** **RM0041**


1. Set the RXONLY bit in the SPI_CR1 register.


2. Enable the SPI by setting the SPE bit to 1:


a) In master mode, this immediately activates the generation of the SCK clock, and
data are serially received until the SPI is disabled (SPE=0).


b) In slave mode, data are received when the SPI master device drives NSS low and
generates the SCK clock.


3. Wait until RXNE=1 and read the SPI_DR register to get the received data (this clears
the RXNE bit). Repeat this operation for each data item to be received.


This procedure can also be implemented using dedicated interrupt subroutines launched at
each rising edge of the RXNE flag.


_Note:_ _If it is required to disable the SPI after the last transfer, follow the recommendation_
_described in Section 21.3.8._


**Figure 229. RXNE behavior in receive-only mode (BIDIRMODE=0 and RXONLY=1)**
**in case of continuous transfers**
















|b0|b1|b2|b3|b4|b5|b6|b7|Col9|b0|b1|b2|b3|b4|b5|b6|b7|Col18|b0|b1|b2|b3|b4|b5|b6|b7|Col27|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware||cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|cleared by software|||||||||||
|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware||||||||||||||||||||
||||||||||||||||||||||||||||
||||||||||0xA1|0xA1|0xA1|0xA1|0xA1|0xA1|0xA1|0xA1|0xA1|0xA2|0xA2|0xA2|0xA2|0xA2|0xA2|0xA2|0xA2|0xA2|









**Bidirectional receive procedure (BIDIMODE=1 and BIDIOE=0)**


In this mode, the procedure is similar to the Receive-only mode procedure except that the
BIDIMODE bit has to be set and the BIDIOE bit cleared in the SPI_CR2 register before
enabling the SPI.


**Continuous and discontinuous transfers**


When transmitting data in master mode, if the software is fast enough to detect each rising
edge of TXE (or TXE interrupt) and to immediately write to the SPI_DR register before the
ongoing data transfer is complete, the communication is said to be continuous. In this case,
there is no discontinuity in the generation of the SPI clock between each data item and the
BSY bit is never cleared between each data transfer.


On the contrary, if the software is not fast enough, this can lead to some discontinuities in
the communication. In this case, the BSY bit is cleared between each data transmission
(see _Figure 230_ ).


In Master receive-only mode (RXONLY=1), the communication is always continuous and
the BSY flag is always read at 1.


550/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


In slave mode, the continuity of the communication is decided by the SPI master device. In
any case, even if the communication is continuous, the BSY flag goes low between each
transfer for a minimum duration of one SPI clock cycle (see _Figure 228_ ).


**Figure 230. TXE/BSY behavior when transmitting (BIDIRMODE=0 and RXONLY=0)**
**in case of discontinuous transfers**














|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|Col17|Col18|Col19|Col20|Col21|Col22|Col23|Col24|Col25|Col26|Col27|Col28|Col29|Col30|Col31|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
||b0|b1|b2|b3|b4|b5|b6|b7|b7|||b0|b1|b2|b3|b4|b5|b6|b7|b7|||b0|b1|b2|b3|b4|b5|b6|b7|
||||||||||||||||||||||||||||||||
||||||||||||||||||||||||||||||||
||||||||||||||||||||||||||||||||
||0xF1|0xF1|0xF1|0xF1|0xF1|0xF1|0xF1|0xF1||||0xF2|0xF2|0xF2|0xF2|0xF2|0xF2|0xF2|0xF2|||||0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|
||0xF1|0xF1|0xF1|0xF1|0xF1|0xF1|0xF1|0xF1|||||||||||||||||||||||







**21.3.6** **CRC calculation**


A CRC calculator has been implemented for communication reliability. Separate CRC
calculators are implemented for transmitted data and received data. The CRC is calculated
using a programmable polynomial serially on each bit. It is calculated on the sampling clock
edge defined by the CPHA and CPOL bits in the SPI_CR1 register.


_Note:_ _This SPI offers two kinds of CRC calculation standard which depend directly on the data_
_frame format selected for the transmission and/or reception: 8-bit data (CR8) and 16-bit data_
_(CRC16)._


CRC calculation is enabled by setting the CRCEN bit in the SPI_CR1 register. This action
resets the CRC registers (SPI_RXCRCR and SPI_TXCRCR). In full duplex or transmitter
only mode, when the transfers are managed by the software (CPU mode), it is necessary to
write the bit CRCNEXT immediately after the last data to be transferred is written to the
SPI_DR. At the end of this last data transfer, the SPI_TXCRCR value is transmitted.


In receive only mode and when the transfers are managed by software (CPU mode), it is
necessary to write the CRCNEXT bit after the second last data has been received. The CRC
is received just after the last data reception and the CRC check is then performed.


At the end of data and CRC transfers, the CRCERR flag in the SPI_SR register is set if
corruption occurs during the transfer.


If data are present in the TX buffer, the CRC value is transmitted only after the transmission
of the data byte. During CRC transmission, the CRC calculator is switched off and the
register value remains unchanged.


SPI communication using the CRC is possible through the following procedure:


RM0041 Rev 6 551/709



565


**Serial peripheral interface (SPI)** **RM0041**


1. Program the CPOL, CPHA, LSBFirst, BR, SSM, SSI and MSTR values.


2. Program the polynomial in the SPI_CRCPR register.


3. Enable the CRC calculation by setting the CRCEN bit in the SPI_CR1 register. This
also clears the SPI_RXCRCR and SPI_TXCRCR registers.


4. Enable the SPI by setting the SPE bit in the SPI_CR1 register.


5. Start the communication and sustain the communication until all but one byte or halfword have been transmitted or received.


–
In full duplex or transmitter-only mode, when the transfers are managed by
software, when writing the last byte or half word to the Tx buffer, set the
CRCNEXT bit in the SPI_CR1 register to indicate that the CRC is transmitted after
the transmission of the last byte.


–
In receiver only mode, set the bit CRCNEXT just after the reception of the second
to last data to prepare the SPI to enter in CRC Phase at the end of the reception of
the last data. CRC calculation is frozen during the CRC transfer.


6. After the transfer of the last byte or half word, the SPI enters the CRC transfer and
check phase. In full duplex mode or receiver-only mode, the received CRC is
compared to the SPI_RXCRCR value. If the value does not match, the CRCERR flag in
SPI_SR is set and an interrupt can be generated when the ERRIE bit in the SPI_CR2
register is set.


_Note:_ _When the SPI is in slave mode, be careful to enable CRC calculation only when the clock is_
_stable, that is, when the clock is in the steady state. If not, a wrong CRC calculation may be_
_done. In fact, the CRC is sensitive to the SCK slave input clock as soon as CRCEN is set,_
_and this, whatever the value of the SPE bit._


_With high bitrate frequencies, be careful when transmitting the CRC. As the number of used_
_CPU cycles has to be as low as possible in the CRC transfer phase, it is forbidden to call_
_software functions in the CRC transmission sequence to avoid errors in the last data and_
_CRC reception. In fact, CRCNEXT bit has to be written before the end of the_
_transmission/reception of the last data._


_For high bit rate frequencies, it is advised to use the DMA mode to avoid the degradation of_
_the SPI speed performance due to CPU accesses impacting the SPI bandwidth._


_When the devices are configured as slaves and the NSS hardware mode is used, the NSS_
_pin needs to be kept low between the data phase and the CRC phase._


When the SPI is configured in slave mode with the CRC feature enabled, CRC calculation
takes place even if a high level is applied on the NSS pin. This may happen for example in
case of a multislave environment where the communication master addresses slaves

alternately.


Between a slave deselection (high level on NSS) and a new slave selection (low level on
NSS), the CRC value should be cleared on both master and slave sides in order to
resynchronize the master and slave for their respective CRC calculation.


To clear the CRC, follow the procedure below:


1. Disable SPI (SPE = 0)


2. Clear the CRCEN bit


3. Set the CRCEN bit


4. Enable the SPI (SPE = 1)


552/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


**21.3.7** **Status flags**


Four status flags are provided for the application to completely monitor the state of the SPI
bus.


**Tx buffer empty flag (TXE)**


When it is set, this flag indicates that the Tx buffer is empty and the next data to be
transmitted can be loaded into the buffer. The TXE flag is cleared when writing to the
SPI_DR register.


**Rx buffer not empty (RXNE)**


When set, this flag indicates that there are valid received data in the Rx buffer. It is cleared
when SPI_DR is read.


**BUSY flag**


This BSY flag is set and cleared by hardware (writing to this flag has no effect). The BSY
flag indicates the state of the communication layer of the SPI.


When BSY is set, it indicates that the SPI is busy communicating. There is one exception in
master mode / bidirectional receive mode (MSTR=1 and BDM=1 and BDOE=0) where the
BSY flag is kept low during reception.


The BSY flag is useful to detect the end of a transfer if the software wants to disable the SPI
and enter Halt mode (or disable the peripheral clock). This avoids corrupting the last
transfer. For this, the procedure described below must be strictly respected.


The BSY flag is also useful to avoid write collisions in a multimaster system.


The BSY flag is set when a transfer starts, with the exception of master mode / bidirectional
receive mode (MSTR=1 and BDM=1 and BDOE=0).


It is cleared:


      - when a transfer is finished (except in master mode if the communication is continuous)


      - when the SPI is disabled


      - when a master mode fault occurs (MODF=1)


When communication is not continuous, the BSY flag is low between each communication.


When communication is continuous:


      - in master mode, the BSY flag is kept high during all the transfers


      - in slave mode, the BSY flag goes low for one SPI clock cycle between each transfer


_Note:_ _Do not use the BSY flag to handle each data transmission or reception. It is better to use the_
_TXE and RXNE flags instead._


RM0041 Rev 6 553/709



565


**Serial peripheral interface (SPI)** **RM0041**


**21.3.8** **Disabling the SPI**


When a transfer is terminated, the application can stop the communication by disabling the
SPI peripheral. This is done by clearing the SPE bit.


For some configurations, disabling the SPI and entering the Halt mode while a transfer is
ongoing can cause the current transfer to be corrupted and/or the BSY flag might become
unreliable.


To avoid any of those effects, it is recommended to respect the following procedure when
disabling the SPI:


**In master or slave full-duplex mode (BIDIMODE=0, RXONLY=0)**


1. Wait until RXNE=1 to receive the last data


2. Wait until TXE=1


3. Then wait until BSY=0


4. Disable the SPI (SPE=0) and, eventually, enter the Halt mode (or disable the peripheral
clock)


**In master or slave unidirectional transmit-only mode (BIDIMODE=0,**
**RXONLY=0) or bidirectional transmit mode (BIDIMODE=1, BIDIOE=1)**


After the last data is written into the SPI_DR register:


1. Wait until TXE=1


2. Then wait until BSY=0


3. Disable the SPI (SPE=0) and, eventually, enter the Halt mode (or disable the peripheral
clock)


**In master unidirectional receive-only mode (MSTR=1, BIDIMODE=0,**
**RXONLY=1) or bidirectional receive mode (MSTR=1, BIDIMODE=1, BIDIOE=0)**


This case must be managed in a particular way to ensure that the SPI does not initiate a
new transfer:


1. Wait for the second to last occurrence of RXNE=1 (n–1)


2. Then wait for one SPI clock cycle (using a software loop) before disabling the SPI
(SPE=0)


3. Then wait for the last RXNE=1 before entering the Halt mode (or disabling the
peripheral clock)


_Note:_ _In master bidirectional receive mode (MSTR=1 and BDM=1 and BDOE=0), the BSY flag is_
_kept low during transfers._


**In slave receive-only mode (MSTR=0, BIDIMODE=0, RXONLY=1) or**
**bidirectional receive mode (MSTR=0, BIDIMODE=1, BIDOE=0)**


1. You can disable the SPI (write SPE=1) at any time: the current transfer completes
before the SPI is effectively disabled


2. Then, if you want to enter the Halt mode, you must first wait until BSY = 0 before
entering the Halt mode (or disabling the peripheral clock).


554/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


**21.3.9** **SPI communication using DMA (direct memory addressing)**


To operate at its maximum speed, the SPI needs to be fed with the data for transmission
and the data received on the Rx buffer should be read to avoid overrun. To facilitate the
transfers, the SPI features a DMA capability implementing a simple request/acknowledge
protocol.


A DMA access is requested when the enable bit in the SPI_CR2 register is enabled.
Separate requests must be issued to the Tx and Rx buffers (see _Figure 231_ and
_Figure 232_ ):


      - In transmission, a DMA request is issued each time TXE is set to 1. The DMA then
writes to the SPI_DR register (this clears the TXE flag).


      - In reception, a DMA request is issued each time RXNE is set to 1. The DMA then reads
the SPI_DR register (this clears the RXNE flag).


When the SPI is used only to transmit data, it is possible to enable only the SPI Tx DMA
channel. In this case, the OVR flag is set because the data received are not read.


When the SPI is used only to receive data, it is possible to enable only the SPI Rx DMA
channel.


In transmission mode, when the DMA has written all the data to be transmitted (flag TCIF is
set in the DMA_ISR register), the BSY flag can be monitored to ensure that the SPI
communication is complete. This is required to avoid corrupting the last transmission before
disabling the SPI or entering the Stop mode. The software must first wait until TXE=1 and
then until BSY=0.


_Note:_ _During discontinuous communications, there is a 2 APB clock period delay between the_
_write operation to SPI_DR and the BSY bit setting. As a consequence, it is mandatory to_
_wait first until TXE=1 and then until BSY=0 after writing the last data._


RM0041 Rev 6 555/709



565


**Serial peripheral interface (SPI)** **RM0041**


**Figure 231. Transmission using DMA**


















|Col1|b0|b1|b2|b3|b4|b5|b6|b7|b0 b|1 b2|b3|b4|b5|b6|b7|b0|b1|b2|b3|b4|b5|b6|b7|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|||set<br>set by hardware<br>cleared by DMA write|set<br>set by hardware<br>cleared by DMA write|set<br>set by hardware<br>cleared by DMA write|set<br>set by hardware<br>cleared by DMA write|set<br>set by hardware<br>cleared by DMA write|set<br>set by hardware<br>cleared by DMA write|set<br>set by hardware<br>cleared by DMA write|by hard|ware<br>clear by DMA write|ware<br>clear by DMA write|ware<br>clear by DMA write|ware<br>clear by DMA write|ware<br>clear by DMA write|ware<br>clear by DMA write||set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|
||se|se|se|se|se|se|se|se|se|se|se|se|se|se|se|||||||||
||se|t by hardware|t by hardware|t by hardware|t by hardware|t by hardware|t by hardware|t by hardware|||||||||ignored by the DMA because<br>DMA transfer is complete|ignored by the DMA because<br>DMA transfer is complete|ignored by the DMA because<br>DMA transfer is complete|ignored by the DMA because<br>DMA transfer is complete|ignored by the DMA because<br>DMA transfer is complete|ignored by the DMA because<br>DMA transfer is complete|ignored by the DMA because<br>DMA transfer is complete|
|||||||||||||||||||||||||
||0xF1|0xF2|0xF2|0xF2|0xF2|0xF2|0xF2|0xF2||0xF3|0xF3|0xF3|0xF3|0xF3|0xF3|||||||||
|||||||||||||||||||||||||
||set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|||||||||

















**Figure 232. Reception using DMA**




















|b0|b1|b2|b3|b4|b5|b6|b7|b0|b1 b|2 b3|b4|b5|b6|b7|Col16|b0|Col18|b1|b2|b3|b4|b5|b6|b7|Col26|Col27|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|||||||||||||
|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|||||||||||||
|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|||||||||||||
|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|||||||||||||
|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|clear by DMA read|||||||||||||
|||||||||0xA1|0xA1|0xA1|0xA1|0xA1|0xA1|0xA1|0xA1||0xA2|0xA2|0xA2|0xA2|0xA2|0xA2|0xA2|0xA2|0xA2||
||||||||||||||||||||||||||||
||||||||||||||||||||||||||||
|||||||||||||||||set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|set by hardware|











556/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


**DMA capability with CRC**


When SPI communication is enabled with CRC communication and DMA mode, the
transmission and reception of the CRC at the end of communication are automatic that is
without using the bit CRCNEXT. After the CRC reception, the CRC must be read in the
SPI_DR register to clear the RXNE flag.


At the end of data and CRC transfers, the CRCERR flag in SPI_SR is set if corruption
occurs during the transfer.


**21.3.10** **Error flags**


**Master mode fault (MODF)**


Master mode fault occurs when the master device has its NSS pin pulled low (in NSS
hardware mode) or SSI bit low (in NSS software mode), this automatically sets the MODF
bit. Master mode fault affects the SPI peripheral in the following ways:


      - The MODF bit is set and an SPI interrupt is generated if the ERRIE bit is set.


      - The SPE bit is cleared. This blocks all output from the device and disables the SPI
interface.


      - The MSTR bit is cleared, thus forcing the device into slave mode.


Use the following software sequence to clear the MODF bit:


1. Make a read or write access to the SPI_SR register while the MODF bit is set.


2. Then write to the SPI_CR1 register.


To avoid any multiple slave conflicts in a system comprising several MCUs, the NSS pin
must be pulled high during the MODF bit clearing sequence. The SPE and MSTR bits can
be restored to their original state after this clearing sequence.


As a security, hardware does not allow the setting of the SPE and MSTR bits while the
MODF bit is set.


In a slave device the MODF bit cannot be set. However, in a multimaster configuration, the
device can be in slave mode with this MODF bit set. In this case, the MODF bit indicates
that there might have been a multimaster conflict for system control. An interrupt routine can
be used to recover cleanly from this state by performing a reset or returning to a default
state.


**Overrun condition**


An overrun condition occurs when the master device has sent data bytes and the slave
device has not cleared the RXNE bit resulting from the previous data byte transmitted.
When an overrun condition occurs:


      - the OVR bit is set and an interrupt is generated if the ERRIE bit is set.


In this case, the receiver buffer contents are not updated with the newly received data from
the master device. A read from the SPI_DR register returns this byte. All other subsequently
transmitted bytes are lost.


Clearing the OVR bit is done by a read from the SPI_DR register followed by a read access
to the SPI_SR register.


RM0041 Rev 6 557/709



565


**Serial peripheral interface (SPI)** **RM0041**


**CRC error**


This flag is used to verify the validity of the value received when the CRCEN bit in the
SPI_CR1 register is set. The CRCERR flag in the SPI_SR register is set if the value
received in the shift register does not match the receiver SPI_RXCRCR value.


**21.3.11** **SPI interrupts**


**Table 119. SPI interrupt requests**

|Interrupt event|Event flag|Enable Control bit|
|---|---|---|
|Transmit buffer empty flag|TXE|TXEIE|
|Receive buffer not empty flag|RXNE|RXNEIE|
|Master mode fault event|MODF|ERRIE|
|Overrun error|OVR|OVR|
|CRC error flag|CRCERR|CRCERR|



558/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**

## **21.4 SPI registers**


The peripheral registers have to be accessed by half-words (16 bits) or words (32 bits).


**21.4.1** **SPI control register 1 (SPI_CR1)**


Address offset: 0x00


Reset value: 0x0000

|15|14|13|12|11|10|9|8|7|6|5 4 3|Col12|Col13|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|BIDI<br>MODE|BIDI<br>OE|CRC<br>EN|CRC<br>NEXT|DFF|RX<br>ONLY|SSM|SSI|_LSB_<br>_FIRST_|SPE|BR [2:0]|BR [2:0]|BR [2:0]|MSTR|CPOL|CPHA|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



_Bit 15_ _**BIDIMODE:**_ Bidirectional data mode enable

_0: 2-line unidirectional data mode selected_

1: 1-line bidirectional data mode selected


_Bit_ 14 **BIDIOE:** Output enable in bidirectional mode

This bit combined with the BIDImode bit selects the direction of transfer in bidirectional mode

0: Output disabled (receive-only mode)
1: Output enabled (transmit-only mode)

_Note: In master mode, the MOSI pin is used and in slave mode, the MISO pin is used._


_Bit_ 13 **CRCEN:** Hardware CRC calculation enable

0: CRC calculation disabled

1: CRC calculation Enabled

_Note: This bit should be written only when SPI is disabled (SPE = ‘0) for correct operation_


_Bit_ 12 **CRCNEXT:** CRC transfer next

0: Data phase (no CRC phase)
1: Next transfer is CRC (CRC phase)

_Note: When the SPI is configured in full duplex or transmitter only modes, CRCNEXT must be_
_written as soon as the last data is written to the SPI_DR register._
_When the SPI is configured in receiver only mode, CRCNEXT must be set after the_
_second last data reception._
_This bit should be kept cleared when the transfers are managed by DMA._


_Bit_ 11 **DFF:** Data frame format

0: 8-bit data frame format is selected for transmission/reception
1: 16-bit data frame format is selected for transmission/reception

_Note: This bit should be written only when SPI is disabled (SPE = ‘0) for correct operation_


_Bit_ 10 **RXONLY:** Receive only

This bit combined with the BIDImode bit selects the direction of transfer in 2-line

unidirectional mode. This bit is also useful in a multislave system in which this particular
slave is not accessed, the output from the accessed slave is not corrupted.
0: Full duplex (Transmit and receive)
1: Output disabled (Receive-only mode)


_Bit_ 9 **SSM:** Software slave management

When the SSM bit is set, the NSS pin input is replaced with the value from the SSI bit.
0: Software slave management disabled
1: Software slave management enabled


RM0041 Rev 6 559/709



565


**Serial peripheral interface (SPI)** **RM0041**


_Bit_ 8 **SSI:** Internal slave select

This bit has an effect only when the SSM bit is set. The value of this bit is forced onto the
NSS pin and the IO value of the NSS pin is ignored.


_Bit 7_ _**LSBFIRST:**_ Frame format

_0: MSB transmitted first_

1: LSB transmitted first

_Note: This bit should not be changed when communication is ongoing._


Bit 6 **SPE:** SPI enable

0: Peripheral disabled
1: Peripheral enabled

_Note: When disabling the SPI, follow the procedure described in_ _Section 21.3.8: Disabling the_

_SPI_ .


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


Bit1 **CPOL:** Clock polarity

0: CK to 0 when idle

1: CK to 1 when idle

_Note: This bit should not be changed when communication is ongoing._


Bit 0 **CPHA:** Clock phase

0: The first clock transition is the first data capture edge
1: The second clock transition is the first data capture edge

_Note: This bit should not be changed when communication is ongoing._


**21.4.2** **SPI control register 2 (SPI_CR2)**


Address offset: 0x04


Reset value: 0x0000

|15 14 13 12 11 10 9 8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|
|Reserved|TXEIE|RXNEIE|ERRIE|Res.|Res.|_SSOE_|TXDMAEN|RXDMAEN|
|Reserved|rw|rw|rw|||rw|rw|rw|



560/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


Bits 15:8 Reserved, must be kept at reset value.


Bit 7 **TXEIE:** Tx buffer empty interrupt enable

0: TXE interrupt masked
1: TXE interrupt not masked. Used to generate an interrupt request when the TXE flag is set.


Bit 6 **RXNEIE:** RX buffer not empty interrupt enable

0: RXNE interrupt masked
1: RXNE interrupt not masked. Used to generate an interrupt request when the RXNE flag is
set.


Bit 5 **ERRIE:** Error interrupt enable

This bit controls the generation of an interrupt when an error condition occurs ).
0: Error interrupt is masked
1: Error interrupt is enabled


Bits 4:3 Reserved, must be kept at reset value.


Bit 2 **SSOE:** SS output enable

0: SS output is disabled in master mode and the cell can work in multimaster configuration
1: SS output is enabled in master mode and when the cell is enabled. The cell cannot work
in a multimaster environment.


Bit 1 **TXDMAEN:** Tx buffer DMA enable

When this bit is set, the DMA request is made whenever the TXE flag is set.

0: Tx buffer DMA disabled

1: Tx buffer DMA enabled


Bit 0 **RXDMAEN:** Rx buffer DMA enable

When this bit is set, the DMA request is made whenever the RXNE flag is set.

0: Rx buffer DMA disabled

1: Rx buffer DMA enabled


**21.4.3** **SPI status register (SPI_SR)**


Address offset: 0x08


Reset value: 0x0002

|15 14 13 12 11 10 9 8|7|6|5|4|3 2|1|0|
|---|---|---|---|---|---|---|---|
|Reserved|BSY|OVR|MODF|CRC<br>ERR|Reserved|TXE|RXNE|
|Reserved|r|r|r|rc_w0|rc_w0|r|r|



Bits 15:8 Reserved, must be kept at reset value.


_Bit 7_ _**BSY:**_ Busy flag

0: SPI not busy
1: SPI is busy in communication or Tx buffer is not empty
This flag is set and cleared by hardware.

_Note: BSY flag must be used with caution: refer to Section 21.3.7 and Section 21.3.8._


Bit 6 **OVR:** Overrun flag

0: No overrun occurred

1: Overrun occurred

This flag is set by hardware and reset by a software sequence.


RM0041 Rev 6 561/709



565


**Serial peripheral interface (SPI)** **RM0041**


Bit 5 **MODF:** Mode fault

0: No mode fault occurred

1: Mode fault occurred

This flag is set by hardware and reset by a software sequence. Refer to _Section 21.3.10 on_
_page 557_ for the software sequence.


Bit 4 **CRCERR:** CRC error flag

0: CRC value received matches the SPI_RXCRCR value
1: CRC value received does not match the SPI_RXCRCR value
This flag is set by hardware and cleared by software writing 0.


Bits 3:2 Reserved


Bit 1 **TXE:** Transmit buffer empty

0: Tx buffer not empty
1: Tx buffer empty


Bit 0 **RXNE:** Receive buffer not empty

0: Rx buffer empty
1: Rx buffer not empty


**21.4.4** **SPI data register (SPI_DR)**


Address offset: 0x0C


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **DR[15:0]:** Data register

Data received or to be transmitted.

The data register is split into 2 buffers - one for writing (Transmit Buffer) and another one for
reading (Receive buffer). A write to the data register writes into the Tx buffer and a read
from the data register returns the value held in the Rx buffer.

_Note: These notes apply to SPI mode:_

_Depending on the data frame format selection bit (DFF in SPI_CR1 register), the data_
_sent or received is either 8-bit or 16-bit. This selection has to be made before enabling_
_the SPI to ensure correct operation._

_For an 8-bit data frame, the buffers are 8-bit and only the LSB of the register_
_(SPI_DR[7:0]) is used for transmission/reception. When in reception mode, the MSB of_
_the register (SPI_DR[15:8]) is forced to 0._

_For a 16-bit data frame, the buffers are 16-bit and the entire register, SPI_DR[15:0] is_
_used for transmission/reception._


562/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


**21.4.5** **SPI CRC polynomial register (SPI_CRCPR)**


Address offset: 0x10


Reset value: 0x0007

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **CRCPOLY[15:0]:** CRC polynomial register

This register contains the polynomial for the CRC calculation.
The CRC polynomial (0007h) is the reset value of this register. Another polynomial can be
configured as required.


**21.4.6** **SPI RX CRC register (SPI_RXCRCR)**


Address offset: 0x14


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|RXCRC[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 15:0 **RXCRC[15:0]:** Rx CRC register

When CRC calculation is enabled, the RxCRC[15:0] bits contain the computed CRC value of
the subsequently received bytes. This register is reset when the CRCEN bit in SPI_CR1
register is written to 1. The CRC is calculated serially using the polynomial programmed in
the SPI_CRCPR register.
Only the 8 LSB bits are considered when the data frame format is set to be 8-bit data (DFF
bit of SPI_CR1 is cleared). CRC calculation is done based on any CRC8 standard.
The entire 16-bits of this register are considered when a 16-bit data frame format is selected
(DFF bit of the SPI_CR1 register is set). CRC calculation is done based on any CRC16
standard.

_Note: A read to this register when the BSY Flag is set could return an incorrect value._


RM0041 Rev 6 563/709



565


**Serial peripheral interface (SPI)** **RM0041**


**21.4.7** **SPI TX CRC register (SPI_TXCRCR)**


Address offset: 0x18


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|TXCRC[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 15:0 **TXCRC[15:0]:** Tx CRC register

When CRC calculation is enabled, the TxCRC[7:0] bits contain the computed CRC value of
the subsequently transmitted bytes. This register is reset when the CRCEN bit of SPI_CR1
is written to 1. The CRC is calculated serially using the polynomial programmed in the
SPI_CRCPR register.
Only the 8 LSB bits are considered when the data frame format is set to be 8-bit data (DFF
bit of SPI_CR1 is cleared). CRC calculation is done based on any CRC8 standard.
The entire 16-bits of this register are considered when a 16-bit data frame format is selected
(DFF bit of the SPI_CR1 register is set). CRC calculation is done based on any CRC16
standard.

_Note: A read to this register when the BSY flag is set could return an incorrect value._


564/709 RM0041 Rev 6


**RM0041** **Serial peripheral interface (SPI)**


**21.4.8** **SPI register map**


The table provides shows the SPI register map and reset values.


**Table 120. SPI register map and reset values**













































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**SPI_CR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|BIDIMODE|BIDIOE|CRCEN|CRCNEXT|DFF|RXONLY|SSM|SSI|_LSBFIRST_|SPE|BR [2:0]|BR [2:0]|BR [2:0]|MSTR|CPOL|CPHA|
|0x00|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x04|**SPI_CR2**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|TXEIE|RXNEIE|ERRIE|Reserved|Reserved|_SSOE_|TXDMAEN|RXDMAEN|
|0x04|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|
|0x08|**SPI_SR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|BSY|OVR|MODF|CRCERR|Reserved|Reserved|TXE|RXNE|
|0x08|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|1|0|
|0x0C|**SPI_DR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|DR[15:0]|
|0x0C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**SPI_CRCPR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|CRCPOLY[15:0]|
|0x10|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|1|1|1|
|0x14|**SPI_RXCRCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|RxCRC[15:0]|
|0x14|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x18|**SPI_TXCRCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|TxCRC[15:0]|
|0x18|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


Refer to _Section 3.3: Memory map_ for the register boundary addresses.


RM0041 Rev 6 565/709



565


