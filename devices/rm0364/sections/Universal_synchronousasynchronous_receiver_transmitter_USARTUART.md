**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**

# **28 Universal synchronous/asynchronous receiver** **transmitter (USART/UART)**

## **28.1 Introduction**


The universal synchronous asynchronous receiver transmitter (USART) offers a flexible
means of Full-duplex data exchange with external equipment requiring an industry standard
NRZ asynchronous serial data format. The USART offers a very wide range of baud rates
using a programmable baud rate generator.


It supports synchronous one-way communication and Half-duplex Single-wire
communication, as well as multiprocessor communications. It also supports the LIN (Local
Interconnect Network), Smartcard protocol and IrDA (Infrared Data Association) SIR
ENDEC specifications and Modem operations (CTS/RTS).


High speed data communication is possible by using the DMA (direct memory access) for
multibuffer configuration.

## **28.2 USART main features**


      - Full-duplex asynchronous communications


      - NRZ standard format (mark/space)


      - Configurable oversampling method by 16 or 8 to give flexibility between speed and
clock tolerance


      - A common programmable transmit and receive baud rate of up to 9 Mbit/s when the
clock frequency is 72 MHz and oversampling is by 8


      - Dual clock domain allowing:


–
USART functionality and wakeup from Stop mode


–
Convenient baud rate programming independent from the PCLK reprogramming


      - Auto baud rate detection


      - Programmable data word length (7, 8 or 9 bits)


      - Programmable data order with MSB-first or LSB-first shifting


      - Configurable stop bits (1 or 2 stop bits)


      - Synchronous mode and clock output for synchronous communications


      - Single-wire Half-duplex communications


      - Continuous communications using DMA


      - Received/transmitted bytes are buffered in reserved SRAM using centralized DMA


      - Separate enable bits for transmitter and receiver


      - Separate signal polarity control for transmission and reception


      - Swappable Tx/Rx pin configuration


      - Hardware flow control for modem and RS-485 transceiver


948/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


      - Communication control/error detection flags


      - Parity control:


–
Transmits parity bit


–
Checks parity of received data byte


      - Fourteen interrupt sources with flags


      - Multiprocessor communications


The USART enters mute mode if the address does not match.


      - Wakeup from mute mode (by idle line detection or address mark detection)

## **28.3 USART extended features**


      - LIN master synchronous break send capability and LIN slave break detection capability


–
13-bit break generation and 10/11-bit break detection when USART is hardware
configured for LIN


      - IrDA SIR encoder decoder supporting 3/16 bit duration for normal mode


      - Smartcard mode


–
Supports the T=0 and T=1 asynchronous protocols for smartcards as defined in
the ISO/IEC 7816-3 standard


–
0.5 and 1.5 stop bits for smartcard operation


      - Support for ModBus communication


– Timeout feature


–
CR/LF character recognition


RM0364 Rev 4 949/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**

## **28.4 USART implementation**


**Table 135. STM32F334xx USART features**







|USART modes/features(1)|USART1|USART2/<br>USART3|
|---|---|---|
|Hardware flow control for modem|X|X|
|Continuous communication using DMA|X|X|
|Multiprocessor communication|X|X|
|Synchronous mode|X|X|
|Smartcard mode|X|-|
|Single-wire Half-duplex communication|X|X|
|IrDA SIR ENDEC block|X|-|
|LIN mode|X|-|
|Dual clock domain and wakeup from Stop mode|X|-|
|Receiver timeout interrupt|X|-|
|Modbus communication|X|-|
|Auto baud rate detection|X|-|
|Driver Enable|X|X|
|USART data length|7(2), 8 and 9 bits|7(2), 8 and 9 bits|


1. X = supported.


2. In 7-bit data length mode, Smartcard mode, LIN master mode and Auto baud rate (0x7F and 0x55 frame
detection) are not supported.

## **28.5 USART functional description**


Any USART bidirectional communication requires a minimum of two pins: Receive data In
(RX) and Transmit data Out (TX):


      - **RX** : Receive data Input.


This is the serial data input. Oversampling techniques are used for data recovery by
discriminating between valid incoming data and noise.


      - **TX:** Transmit data Output.


When the transmitter is disabled, the output pin returns to its I/O port configuration.
When the transmitter is enabled and nothing is to be transmitted, the TX pin is at high
level. In Single-wire and Smartcard modes, this I/O is used to transmit and receive the
data.


950/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


Serial data are transmitted and received through these pins in normal USART mode. The
frames are comprised of:


      - An Idle Line prior to transmission or reception


      - A start bit


      - A data word (7, 8 or 9 bits) least significant bit first


      - 0.5, 1, 1.5, 2 stop bits indicating that the frame is complete


      - The USART interface uses a baud rate generator


      - A status register (USART_ISR)


      - Receive and transmit data registers (USART_RDR, USART_TDR)


      - A baud rate register (USART_BRR)


      - A guard-time register (USART_GTPR) in case of Smartcard mode.


Refer to _Section 28.8: USART registers on page 992_ for the definitions of each bit.


The following pin is required to interface in synchronous mode and Smartcard mode:


      - **CK:** Clock output. This pin outputs the transmitter data clock for synchronous
transmission corresponding to SPI master mode (no clock pulses on start bit and stop
bit, and a software option to send a clock pulse on the last data bit). In parallel, data
can be received synchronously on RX. This can be used to control peripherals that
have shift registers. The clock phase and polarity are software programmable. In
Smartcard mode, CK output can provide the clock to the smartcard.


The following pins are required in RS232 Hardware flow control mode:


      - **CTS:** Clear To Send blocks the data transmission at the end of the current transfer

when high


      - **RTS:** Request to send indicates that the USART is ready to receive data (when low).


The following pin is required in RS485 Hardware control mode:


      - **DE** : Driver Enable activates the transmission mode of the external transceiver.


_Note:_ _DE and RTS share the same pin._


RM0364 Rev 4 951/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Figure 354. USART block diagram**












|Transmit data register<br>(TDR)|Col2|
|---|---|
|||
|||














|USART_CR3 register|Col2|Col3|Col4|
|---|---|---|---|
|USART_CR2 register|USART_CR2 register|USART_CR2 register|USART_CR2 register|
|USART_CR2 register|USART_CR2 register|USART_CR2 register||
|USART_CR2 register|USART_CR2 register|||
|USART_CR2 register||||





























1. For details on coding USARTDIV in the USART_BRR register, refer to _Section 28.5.4: USART baud rate_
_generation_ .


2. f CK can be f LSE, f HSI, f PCLK, f SYS .


952/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


**28.5.1** **USART character description**


The word length can be selected as being either 7 or 8 or 9 bits by programming the M[1:0]
bits in the USART_CR1 register (see _Figure 355_ ).


      - 7-bit character length: M[1:0] = 10


      - 8-bit character length: M[1:0] = 00


      - 9-bit character length: M[1:0] = 01


_Note:_ _The 7-bit mode is supported only on some USARTs. In addition, not all modes are_
_supported in 7-bit data length mode. Refer to Section 28.4: USART implementation for_
_additional information._


By default, the signal (TX or RX) is in low state during the start bit. It is in high state during
the stop bit.


These values can be inverted, separately for each signal, through polarity configuration
control.


An _**Idle character**_ is interpreted as an entire frame of “1”s (the number of “1”s includes the
number of stop bits).


A _**Break character**_ is interpreted on receiving “0”s for a frame period. At the end of the
break frame, the transmitter inserts 2 stop bits.


Transmission and reception are driven by a common baud rate generator, the clock for each
is generated when the enable bit is set respectively for the transmitter and receiver.


The details of each block is given below.


RM0364 Rev 4 953/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Figure 355. Word length programming**










|Idle frame<br>Break frame|Col2|Col3|
|---|---|---|
|Idle frame<br>Break frame|Stop<br>bit|Stop<br>bit|










|Idle frame<br>Break frame|Col2|Col3|
|---|---|---|
|Idle frame<br>Break frame|Stop<br>bit|Stop<br>bit|

























954/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


**28.5.2** **USART transmitter**


The transmitter can send data words of either 7, 8 or 9 bits depending on the M bits status.
The Transmit Enable bit (TE) must be set in order to activate the transmitter function. The
data in the transmit shift register is output on the TX pin and the corresponding clock pulses
are output on the CK pin.


**Character transmission**


During an USART transmission, data shifts out least significant bit first (default
configuration) on the TX pin. In this mode, the USART_TDR register consists of a buffer
(TDR) between the internal bus and the transmit shift register (see _Figure 354_ ).


Every character is preceded by a start bit which is a logic level low for one bit period. The
character is terminated by a configurable number of stop bits.


The following stop bits are supported by USART: 0.5, 1, 1.5 and 2 stop bits.


_Note:_ _The TE bit must be set before writing the data to be transmitted to the USART_TDR._


_The TE bit should not be reset during transmission of data. Resetting the TE bit during the_
_transmission will corrupt the data on the TX pin as the baud rate counters will get frozen._
_The current data being transmitted will be lost._


_An idle frame will be sent after the TE bit is enabled._


**Configurable stop bits**


The number of stop bits to be transmitted with every character can be programmed in
Control register 2, bits 13,12.


      - _**1 stop bit**_ **:** This is the default value of number of stop bits.


      - _**2 stop bits**_ **:** This will be supported by normal USART, Single-wire and Modem modes.


      - _**1.5 stop bits**_ **:** To be used in Smartcard mode.


      - _**0.5 stop bit**_ : To be used when receiving data in Smartcard mode.


An idle frame transmission will include the stop bits.


A break transmission will be 10 low bits (when M[1:0] = 00) or 11 low bits (when M[1:0] = 01)
or 9 low bits (when M[1:0] = 10) followed by 2 stop bits (see _Figure 356_ ). It is not possible to
transmit long breaks (break of length greater than 9/10/11 low bits).


RM0364 Rev 4 955/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Figure 356. Configurable stop bits**














|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|parity b|s bit|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Start bit||Bit0||Bit1||Bit2||Bit3||Bit4||Bit5||Bit6|Bit7|1.5<br><br>|
|Start bit||Bit0||Bit1||Bit2||Bit3||Bit4||Bit5||Bit6|Bit7|Stop|









**Character transmission procedure**


1. Program the M bits in USART_CR1 to define the word length.


2. Select the desired baud rate using the USART_BRR register.


3. Program the number of stop bits in USART_CR2.





4. Enable the USART by writing the UE bit in USART_CR1 register to 1.


5. Select DMA enable (DMAT) in USART_CR3 if multibuffer communication is to take
place. Configure the DMA register as explained in multibuffer communication.


6. Set the TE bit in USART_CR1 to send an idle frame as first transmission.


7. Write the data to send in the USART_TDR register (this clears the TXE bit). Repeat this
for each data to be transmitted in case of single buffer.


8. After writing the last data into the USART_TDR register, wait until TC=1. This indicates
that the transmission of the last frame is complete. This is required for instance when
the USART is disabled or enters the Halt mode to avoid corrupting the last
transmission.


**Single byte communication**


Clearing the TXE bit is always performed by a write to the transmit data register.


The TXE bit is set by hardware and it indicates:


      - The data has been moved from the USART_TDR register to the shift register and the
data transmission has started.


      - The USART_TDR register is empty.


      - The next data can be written in the USART_TDR register without overwriting the
previous data.


This flag generates an interrupt if the TXEIE bit is set.


When a transmission is taking place, a write instruction to the USART_TDR register stores
the data in the TDR register; next, the data is copied in the shift register at the end of the
currently ongoing transmission.


956/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


When no transmission is taking place, a write instruction to the USART_TDR register places
the data in the shift register, the data transmission starts, and the TXE bit is set.


If a frame is transmitted (after the stop bit) and the TXE bit is set, the TC bit goes high. An
interrupt is generated if the TCIE bit is set in the USART_CR1 register.


After writing the last data in the USART_TDR register, it is mandatory to wait for TC=1
before disabling the USART or causing the microcontroller to enter the low-power mode
(see _Figure 357: TC/TXE behavior when transmitting_ ).


**Figure 357. TC/TXE behavior when transmitting**


**Break characters**


Setting the SBKRQ bit transmits a break character. The break frame length depends on the
M bits (see _Figure 355_ ).


If a ‘1’ is written to the SBKRQ bit, a break character is sent on the TX line after completing
the current character transmission. The SBKF bit is set by the write operation and it is reset
by hardware when the break character is completed (during the stop bits after the break
character). The USART inserts a logic 1 signal (STOP) for the duration of 2 bits at the end of
the break frame to guarantee the recognition of the start bit of the next frame.


In the case the application needs to send the break character following all previously
inserted data, including the ones not yet transmitted, the software should wait for the TXE
flag assertion before setting the SBKRQ bit.


**Idle characters**


Setting the TE bit drives the USART to send an idle frame before the first data frame.


**28.5.3** **USART receiver**


The USART can receive data words of either 7, 8 or 9 bits depending on the M bits in the
USART_CR1 register.


**Start bit detection**


The start bit detection sequence is the same when oversampling by 16 or by 8.


RM0364 Rev 4 957/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


In the USART, the start bit is detected when a specific sequence of samples is recognized.
This sequence is: 1 1 1 0 X 0 X 0X 0X 0 X 0X 0.


**Figure 358. Start bit detection when oversampling by 16 or 8**


_Note:_ _If the sequence is not complete, the start bit detection aborts and the receiver returns to the_
_idle state (no flag is set), where it waits for a falling edge._


The start bit is confirmed (RXNE flag set, interrupt generated if RXNEIE=1) if the 3 sampled
bits are at 0 (first sampling on the 3rd, 5th and 7th bits finds the 3 bits at 0 and second
sampling on the 8th, 9th and 10th bits also finds the 3 bits at 0).


The start bit is validated (RXNE flag set, interrupt generated if RXNEIE=1) but the NF noise
flag is set if,


a) for both samplings, 2 out of the 3 sampled bits are at 0 (sampling on the 3rd, 5th
and 7th bits and sampling on the 8th, 9th and 10th bits)


or


b) for one of the samplings (sampling on the 3rd, 5th and 7th bits or sampling on the
8th, 9th and 10th bits), 2 out of the 3 bits are found at 0.


If neither conditions a. or b. are met, the start detection aborts and the receiver returns to the
idle state (no flag is set).


958/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


**Character reception**


During an USART reception, data shifts in least significant bit first (default configuration)
through the RX pin. In this mode, the USART_RDR register consists of a buffer (RDR)
between the internal bus and the receive shift register.


**Character reception procedure**


1. Program the M bits in USART_CR1 to define the word length.


2. Select the desired baud rate using the baud rate register USART_BRR


3. Program the number of stop bits in USART_CR2.


4. Enable the USART by writing the UE bit in USART_CR1 register to 1.


5. Select DMA enable (DMAR) in USART_CR3 if multibuffer communication is to take
place. Configure the DMA register as explained in multibuffer communication.


6. Set the RE bit USART_CR1. This enables the receiver which begins searching for a
start bit.


When a character is received:


      - The RXNE bit is set to indicate that the content of the shift register is transferred to the
RDR. In other words, data has been received and can be read (as well as its
associated error flags).


      - An interrupt is generated if the RXNEIE bit is set.


      - The error flags can be set if a frame error, noise or an overrun error has been detected
during reception. PE flag can also be set with RXNE.


      - In multibuffer, RXNE is set after every byte received and is cleared by the DMA read of
the Receive data Register.


      - In single buffer mode, clearing the RXNE bit is performed by a software read to the
USART_RDR register. The RXNE flag can also be cleared by writing 1 to the RXFRQ
in the USART_RQR register. The RXNE bit must be cleared before the end of the
reception of the next character to avoid an overrun error.


**Break character**


When a break character is received, the USART handles it as a framing error.


**Idle character**


When an idle frame is detected, there is the same procedure as for a received data
character plus an interrupt if the IDLEIE bit is set.


RM0364 Rev 4 959/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Overrun error**


An overrun error occurs when a character is received when RXNE has not been reset. Data
can not be transferred from the shift register to the RDR register until the RXNE bit is
cleared.


The RXNE flag is set after every byte received. An overrun error occurs if RXNE flag is set
when the next data is received or the previous DMA request has not been serviced. When

an overrun error occurs:


      - The ORE bit is set.


      - The RDR content will not be lost. The previous data is available when a read to
USART_RDR is performed.


      - The shift register will be overwritten. After that point, any data received during overrun
is lost.


      - An interrupt is generated if either the RXNEIE bit is set or EIE bit is set.


      - The ORE bit is reset by setting the ORECF bit in the ICR register.


_Note:_ _The ORE bit, when set, indicates that at least 1 data has been lost. There are two_
_possibilities:_


_- if RXNE=1, then the last valid data is stored in the receive register RDR and can be read,_


_- if RXNE=0, then it means that the last valid data has already been read and thus there is_
_nothing to be read in the RDR. This case can occur when the last valid data is read in the_
_RDR at the same time as the new (and lost) data is received._


**Selecting the clock source and the proper oversampling method**


The choice of the clock source is done through the Clock Control system (see Section Reset
and clock control (RCC))). The clock source must be chosen before enabling the USART
(by setting the UE bit).


The choice of the clock source must be done according to two criteria:


      - Possible use of the USART in low-power mode


      - Communication speed.


The clock source frequency is f CK .


When the dual clock domain with the wakeup from Stop mode is supported, the clock
source can be one of the following sources: PCLK (default), LSE, HSI or SYSCLK.
Otherwise, the USART clock source is PCLK.


Choosing LSE or HSI as clock source may allow the USART to receive data while the MCU
is in low-power mode. Depending on the received data and wakeup mode selection, the
USART wakes up the MCU, when needed, in order to transfer the received data by software
reading the USART_RDR register or by DMA.


For the other clock sources, the system must be active in order to allow USART
communication.


The communication speed range (specially the maximum communication speed) is also
determined by the clock source.


The receiver implements different user-configurable oversampling techniques for data
recovery by discriminating between valid incoming data and noise. This allows a trade-off
between the maximum communication speed and noise/clock inaccuracy immunity.


960/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


The oversampling method can be selected by programming the OVER8 bit in the
USART_CR1 register and can be either 16 or 8 times the baud rate clock ( _Figure 359_ and
_Figure 360_ ).


Depending on the application:


      - Select oversampling by 8 (OVER8=1) to achieve higher speed (up to f CK /8). In this
case the maximum receiver tolerance to clock deviation is reduced (refer to
_Section 28.5.5: Tolerance of the USART receiver to clock deviation on page 966_ )


      - Select oversampling by 16 (OVER8=0) to increase the tolerance of the receiver to
clock deviations. In this case, the maximum speed is limited to maximum f CK /16 where
f CK is the clock source frequency.


Programming the ONEBIT bit in the USART_CR3 register selects the method used to
evaluate the logic level. There are two options:


      - The majority vote of the three samples in the center of the received bit. In this case,
when the 3 samples used for the majority vote are not equal, the NF bit is set


      - A single sample in the center of the received bit


Depending on the application:


–
select the three samples’ majority vote method (ONEBIT=0) when operating in a
noisy environment and reject the data when a noise is detected (refer to
_Figure 136_ ) because this indicates that a glitch occurred during the sampling.


–
select the single sample method (ONEBIT=1) when the line is noise-free to
increase the receiver’s tolerance to clock deviations (see _Section 28.5.5:_
_Tolerance of the USART receiver to clock deviation on page 966_ ). In this case the
NF bit will never be set.


When noise is detected in a frame:


      - The NF bit is set at the rising edge of the RXNE bit.


      - The invalid data is transferred from the Shift register to the USART_RDR register.


      - No interrupt is generated in case of single byte communication. However this bit rises
at the same time as the RXNE bit which itself generates an interrupt. In case of
multibuffer communication an interrupt will be issued if the EIE bit is set in the
USART_CR3 register.


The NF bit is reset by setting NFCF bit in ICR register.


_Note:_ _Oversampling by 8 is not available in LIN, Smartcard and IrDA modes. In those modes, the_
_OVER8 bit is forced to ‘0’ by hardware._


RM0364 Rev 4 961/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Figure 359. Data sampling when oversampling by 16**





**Table 136. Noise detection from sampled data**



**Figure 360. Data sampling when oversampling by 8**







|Sampled value|NE status|Received bit value|
|---|---|---|
|000|0|0|
|001|1|0|
|010|1|0|
|011|1|1|
|100|1|0|
|101|1|1|
|110|1|1|
|111|0|1|


962/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


**Framing error**


A framing error is detected when the stop bit is not recognized on reception at the expected
time, following either a de-synchronization or excessive noise.


When the framing error is detected:


      - The FE bit is set by hardware


      - The invalid data is transferred from the Shift register to the USART_RDR register.


      - No interrupt is generated in case of single byte communication. However this bit rises
at the same time as the RXNE bit which itself generates an interrupt. In case of
multibuffer communication an interrupt will be issued if the EIE bit is set in the
USART_CR3 register.


The FE bit is reset by writing 1 to the FECF in the USART_ICR register.


**Configurable stop bits during reception**


The number of stop bits to be received can be configured through the control bits of Control
Register 2 - it can be either 1 or 2 in normal mode and 0.5 or 1.5 in Smartcard mode.


     - _**0.5 stop bit (reception in Smartcard mode)**_ _: No sampling is done for 0.5 stop bit. As_
_a consequence, no framing error and no break frame can be detected when 0.5 stop bit_
_is selected._


      - _**1 stop bit**_ : Sampling for 1 stop Bit is done on the 8th, 9th and 10th samples.


      - _**1.5 stop bits (Smartcard mode)**_ : When transmitting in Smartcard mode, the device
must check that the data is correctly sent. Thus the receiver block must be enabled (RE
=1 in the USART_CR1 register) and the stop bit is checked to test if the smartcard has
detected a parity error. In the event of a parity error, the smartcard forces the data
signal low during the sampling - NACK signal-, which is flagged as a framing error.
Then, the FE flag is set with the RXNE at the end of the 1.5 stop bits. Sampling for 1.5
stop bits is done on the 16th, 17th and 18th samples (1 baud clock period after the
beginning of the stop bit). The 1.5 stop bits can be decomposed into 2 parts: one 0.5
baud clock period during which nothing happens, followed by 1 normal stop bit period
during which sampling occurs halfway through. Refer to _Section 28.5.13: USART_
_Smartcard mode on page 977_ for more details.


      - _**2 stop bits**_ : Sampling for 2 stop bits is done on the 8th, 9th and 10th samples of the
first stop bit. If a framing error is detected during the first stop bit the framing error flag
will be set. The second stop bit is not checked for framing error. The RXNE flag will be
set at the end of the first stop bit.


RM0364 Rev 4 963/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**28.5.4** **USART baud rate generation**


The baud rate for the receiver and transmitter (Rx and Tx) are both set to the same value as
programmed in the USART_BRR register.


**Equation 1: Baud rate for standard USART (SPI mode included) (OVER8 = 0 or 1)**


In case of oversampling by 16, the equation is:


f
Tx/Rx baud = -------------------------------- CK
USARTDIV


In case of oversampling by 8, the equation is:

Tx/Rx baud = -------------------------------- 2 × f CK
USARTDIV


**Equation 2: Baud rate in Smartcard, LIN and IrDA modes (OVER8 = 0)**


In Smartcard, LIN and IrDA modes, only Oversampling by 16 is supported:

Tx/Rx baud = -------------------------------- f CK
USARTDIV


USARTDIV is an unsigned fixed point number that is coded on the USART_BRR register.


      - When OVER8 = 0, BRR = USARTDIV.


      - When OVER8 = 1


–
BRR[2:0] = USARTDIV[3:0] shifted 1 bit to the right.


–
BRR[3] must be kept cleared.


–
BRR[15:4] = USARTDIV[15:4]


_Note:_ _The baud counters are updated to the new value in the baud registers after a write operation_
_to USART_BRR. Hence the baud rate register value should not be changed during_
_communication._


_In case of oversampling by 16 or 8, USARTDIV must be greater than or equal to 16d._


**How to derive USARTDIV from USART_BRR register values**


**Example 1**


To obtain 9600 baud with f CK = 8 MHz.


      - In case of oversampling by 16:


USARTDIV = 8 000 000/9600


BRR = USARTDIV = 833d = 0341h


      - In case of oversampling by 8:


USARTDIV = 2 * 8 000 000/9600


USARTDIV = 1666,66 (1667d = 683h)


BRR[3:0] = 3h << 1 = 1h


BRR = 0x681


964/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


**Example 2**


To obtain 921.6 Kbaud with f CK = 48 MHz.


      - In case of oversampling by 16:


USARTDIV = 48 000 000/921 600


BRR = USARTDIV = 52d = 34h


      - In case of oversampling by 8:


USARTDIV = 2 * 48 000 000/921 600


USARTDIV = 104 (104d = 68h)


BRR[3:0] = USARTDIV[3:0] >> 1 = 8h >> 1 = 4h


BRR = 0x64


**Table 137. Error calculation for programmed baud rates at f** **CK** **= 72MHz in both cases of**









|Col1|Col2|oversampling by 16 or by 8(|Col4|Col5|CK (1)|Col7|Col8|
|---|---|---|---|---|---|---|---|
|**Baud rate**|**Baud rate**|**Oversampling by 16 (OVER8 = 0)**|**Oversampling by 16 (OVER8 = 0)**|**Oversampling by 16 (OVER8 = 0)**|**Oversampling by 8 (OVER8 = 1)**|**Oversampling by 8 (OVER8 = 1)**|**Oversampling by 8 (OVER8 = 1)**|
|**S.No**|**Desired**|**Actual**|**BRR**|**% Error =**<br>**(Calculated -**<br>**Desired)B.Rate /**<br>**Desired B.Rate**|**Actual**|**BRR**|**% Error**|
|1|2.4 KBps|2.4 KBps|0x7530|0|2.4 KBps|0xEA60|0|
|2|9.6 KBps|9.6 KBps|0x1D4C|0|9.6 KBps|0x3A94|0|
|3|19.2 KBps|19.2 KBps|0xEA6|0|19.2 KBps|0x1D46|0|
|4|38.4 KBps|38.4 KBps|0x753|0|38.4 KBps|0xEA3|0|
|5|57.6 KBps|57.6 KBps|0x4E2|0|57.6 KBps|0x9C2|0|
|6|115.2 KBps|115.2 KBps|0x271|0|115.2 KBps|0x4E1|0|
|7|230.4 KBps|230.03KBps|0x139|0.16|230.4 KBps|0x270|0|
|8|460.8 KBps|461.54KBps|0x9C|0.16|460.06KBps|0x134|0.16|
|9|921.6 KBps|923.08KBps|0x4E|0.16|923.07KBps|0x96|0.16|
|10|2 MBps|2 MBps|0x24|0|2 MBps|0x44|0|
|11|3 MBps|3 MBps|0x18|0|3 MBps|0x30|0|
|12|4MBps|4MBps|0x12|0|4MBps|0x22|0|
|13|5MBps|N.A|N.A|N.A|4965.51KBps|0x16|0.69|
|14|6MBps|N.A|N.A|N.A|6MBps|0x14|0|
|15|7MBps|N.A|N.A|N.A|6857.14KBps|0x12|2|
|16|9MBps|N.A|N.A|N.A|9MBps|0x10|0|


1. The lower the CPU clock the lower the accuracy for a particular baud rate. The upper limit of the achievable baud rate can
be fixed with these data.


RM0364 Rev 4 965/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**28.5.5** **Tolerance of the USART receiver to clock deviation**


The asynchronous receiver of the USART works correctly only if the total clock system
deviation is less than the tolerance of the USART receiver. The causes which contribute to

the total deviation are:


      - DTRA: Deviation due to the transmitter error (which also includes the deviation of the
transmitter’s local oscillator)


      - DQUANT: Error due to the baud rate quantization of the receiver


      - DREC: Deviation of the receiver’s local oscillator


      - DTCL: Deviation due to the transmission line (generally due to the transceivers which
can introduce an asymmetry between the low-to-high transition timing and the high-tolow transition timing)


DTRA + DQUANT + DREC + DTCL + DWU < USART receiver ′ s tolerance


where


DWU is the error due to sampling point deviation when the wakeup from Stop mode is
used.


when M[1:0] = 01:


DWU = --------------------------- t WUUSART
11 × Tbit


when M[1:0] = 00:


DWU = --------------------------- t WUUSART
10 × Tbit


when M[1:0] = 10:


DWU = --------------------------- t WUUSART
9 × Tbit


t WUUSART is the time between:


1. The detection of start bit falling edge


2. The instant when clock (requested by the peripheral) is ready and reaching the
peripheral and regulator is ready.


The USART receiver can receive data correctly at up to the maximum tolerated
deviation specified in _Table 138_ and _Table 138_ depending on the following choices:


      - 9-, 10- or 11-bit character length defined by the M bits in the USART_CR1 register


      - Oversampling by 8 or 16 defined by the OVER8 bit in the USART_CR1 register


      - Bits BRR[3:0] of USART_BRR register are equal to or different from 0000.


      - Use of 1 bit or 3 bits to sample the data, depending on the value of the ONEBIT bit in
the USART_CR3 register.


966/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


**Table 138. Tolerance of the USART receiver when BRR [3:0] = 0000**

|M bits|OVER8 bit = 0|Col3|OVER8 bit = 1|Col5|
|---|---|---|---|---|
|**M bits**|**ONEBIT=0**|**ONEBIT=1**|**ONEBIT=0**|**ONEBIT=1**|
|00|3.75%|4.375%|2.50%|3.75%|
|01|3.41%|3.97%|2.27%|3.41%|
|10|4.16%|4.86%|2.77%|4.16%|



**Table 139. Tolerance of the USART receiver when BRR [3:0] is different from 0000**

|M bits|OVER8 bit = 0|Col3|OVER8 bit = 1|Col5|
|---|---|---|---|---|
|**M bits**|**ONEBIT=0**|**ONEBIT=1**|**ONEBIT=0**|**ONEBIT=1**|
|00|3.33%|3.88%|2%|3%|
|01|3.03%|3.53%|1.82%|2.73%|
|10|3.7%|4.31%|2.22%|3.33%|



_Note:_ _The data specified in Table 138_ _and Table 139 may slightly differ in the special case when_
_the received frames contain some Idle frames of exactly 10-bit durations when M bits = 00_
_(11-bit durations when M bits =01 or 9- bit durations when M bits = 10)._


**28.5.6** **USART auto baud rate detection**


The USART is able to detect and automatically set the USART_BRR register value based
on the reception of one character. Automatic baud rate detection is useful under two
circumstances:


      - The communication speed of the system is not known in advance


      - The system is using a relatively low accuracy clock source and this mechanism allows
the correct baud rate to be obtained without measuring the clock deviation.


The clock source frequency must be compatible with the expected communication speed
(when oversampling by 16, the baud rate is between f CK /65535 and f CK /16. when
oversampling by 8, the baud rate is between f CK /65535 and f CK /8).


Before activating the auto baud rate detection, the auto baud rate detection mode must be
chosen. There are various modes based on different character patterns.


They can be chosen through the ABRMOD[1:0] field in the USART_CR2 register. In these
auto baud rate modes, the baud rate is measured several times during the synchronization
data reception and each measurement is compared to the previous one.


These modes are:


      - **Mode 0** : Any character starting with a bit at 1. In this case the USART measures the
duration of the Start bit (falling edge to rising edge).


      - **Mode 1:** Any character starting with a 10xx bit pattern. In this case, the USART
measures the duration of the Start and of the 1st data bit. The measurement is done
falling edge to falling edge, ensuring better accuracy in the case of slow signal slopes.


      - **Mode 2** : A 0x7F character frame (it may be a 0x7F character in LSB first mode or a
0xFE in MSB first mode). In this case, the baud rate is updated first at the end of the


RM0364 Rev 4 967/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


start bit (BRs), then at the end of bit 6 (based on the measurement done from falling
edge to falling edge: BR6). Bit 0 to bit 6 are sampled at BRs while further bits of the
character are sampled at BR6.


      - **Mode 3** : A 0x55 character frame. In this case, the baud rate is updated first at the end
of the start bit (BRs), then at the end of bit 0 (based on the measurement done from
falling edge to falling edge: BR0), and finally at the end of bit 6 (BR6). Bit 0 is sampled
at BRs, bit 1 to bit 6 are sampled at BR0, and further bits of the character are sampled
at BR6.


In parallel, another check is performed for each intermediate transition of RX line. An
error is generated if the transitions on RX are not sufficiently synchronized with the
receiver (the receiver being based on the baud rate calculated on bit 0).


Prior to activating auto baud rate detection, the USART_BRR register must be initialized by
writing a non-zero baud rate value.


The automatic baud rate detection is activated by setting the ABREN bit in the USART_CR2
register. The USART will then wait for the first character on the RX line. The auto baud rate
operation completion is indicated by the setting of the ABRF flag in the USART_ISR
register. If the line is noisy, the correct baud rate detection cannot be guaranteed. In this
case the BRR value may be corrupted and the ABRE error flag will be set. This also
happens if the communication speed is not compatible with the automatic baud rate
detection range (bit duration not between 16 and 65536 clock periods (oversampling by 16)
and not between 8 and 65536 clock periods (oversampling by 8)).


The RXNE interrupt will signal the end of the operation.


At any later time, the auto baud rate detection may be relaunched by resetting the ABRF
flag (by writing a 0).


_Note:_ _If the USART is disabled (UE=0) during an auto baud rate operation, the BRR value may be_
_corrupted._


**28.5.7** **Multiprocessor communication using USART**


In multiprocessor communication, the following bits are to be kept cleared:


      - LINEN bit in the USART_CR2 register,


      - HDSEL, IREN and SCEN bits in the USART_CR3 register.


It is possible to perform multiprocessor communication with the USART (with several
USARTs connected in a network). For instance one of the USARTs can be the master, its TX
output connected to the RX inputs of the other USARTs. The others are slaves, their
respective TX outputs are logically ANDed together and connected to the RX input of the
master.


In multiprocessor configurations it is often desirable that only the intended message
recipient should actively receive the full message contents, thus reducing redundant USART
service overhead for all non addressed receivers.


The non addressed devices may be placed in mute mode by means of the muting function.
In order to use the mute mode feature, the MME bit must be set in the USART_CR1
register.


968/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


In mute mode:


      - None of the reception status bits can be set.


      - All the receive interrupts are inhibited.


      - The RWU bit in USART_ISR register is set to 1. RWU can be controlled automatically
by hardware or by software, through the MMRQ bit in the USART_RQR register, under
certain conditions.


The USART can enter or exit from mute mode using one of two methods, depending on the
WAKE bit in the USART_CR1 register:


      - Idle Line detection if the WAKE bit is reset,


      - Address Mark detection if the WAKE bit is set.


**Idle line detection (WAKE=0)**


The USART enters mute mode when the MMRQ bit is written to 1 and the RWU is
automatically set.


It wakes up when an Idle frame is detected. Then the RWU bit is cleared by hardware but
the IDLE bit is not set in the USART_ISR register. An example of mute mode behavior using
Idle line detection is given in _Figure 361_ .


**Figure 361. Mute mode using Idle line detection**











_Note:_ _If the MMRQ is set while the IDLE character has already elapsed, mute mode will not be_
_entered (RWU is not set)._


_If the USART is activated while the line is IDLE, the idle state is detected after the duration_
_of one IDLE frame (not only after the reception of one character frame)._


**4-bit/7-bit address mark detection (WAKE=1)**


In this mode, bytes are recognized as addresses if their MSB is a ‘1’ otherwise they are
considered as data. In an address byte, the address of the targeted receiver is put in the 4
or 7 LSBs. The choice of 7 or 4-bit address detection is done using the ADDM7 bit. This 4bit/7-bit word is compared by the receiver with its own address which is programmed in the
ADD bits in the USART_CR2 register.


_Note:_ _In 7-bit and 9-bit data modes, address detection is done on 6-bit and 8-bit addresses_
_(ADD[5:0] and ADD[7:0]) respectively._


RM0364 Rev 4 969/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


The USART enters mute mode when an address character is received which does not

match its programmed address. In this case, the RWU bit is set by hardware. The RXNE
flag is not set for this address byte and no interrupt or DMA request is issued when the
USART enters mute mode.


The USART also enters mute mode when the MMRQ bit is written to 1. The RWU bit is also
automatically set in this case.


The USART exits from mute mode when an address character is received which matches

the programmed address. Then the RWU bit is cleared and subsequent bytes are received
normally. The RXNE bit is set for the address character since the RWU bit has been
cleared.


An example of mute mode behavior using address mark detection is given in _Figure 362_ .


**Figure 362. Mute mode using address mark detection**















**28.5.8** **Modbus communication using USART**


The USART offers basic support for the implementation of Modbus/RTU and Modbus/ASCII
protocols. Modbus/RTU is a half duplex, block transfer protocol. The control part of the
protocol (address recognition, block integrity control and command interpretation) must be
implemented in software.


The USART offers basic support for the end of the block detection, without software
overhead or other resources.


**Modbus/RTU**


In this mode, the end of one block is recognized by a “silence” (idle line) for more than 2
character times. This function is implemented through the programmable timeout function.


The timeout function and interrupt must be activated, through the RTOEN bit in the
USART_CR2 register and the RTOIE in the USART_CR1 register. The value corresponding
to a timeout of 2 character times (for example 22 x bit duration) must be programmed in the
RTO register. when the receive line is idle for this duration, after the last stop bit is received,
an interrupt is generated, informing the software that the current block reception is
completed.


970/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


**Modbus/ASCII**


In this mode, the end of a block is recognized by a specific (CR/LF) character sequence.
The USART manages this mechanism using the character match function.


By programming the LF ASCII code in the ADD[7:0] field and by activating the character
match interrupt (CMIE=1), the software is informed when a LF has been received and can
check the CR/LF in the DMA buffer.


**28.5.9** **USART parity control**


Parity control (generation of parity bit in transmission and parity checking in reception) can
be enabled by setting the PCE bit in the USART_CR1 register. Depending on the frame
length defined by the M bits, the possible USART frame formats are as listed in _Table 140_ .


**Table 140. Frame formats**

|M bits|PCE bit|USART frame(1)|
|---|---|---|
|00|0|| SB | 8-bit data | STB ||
|00|1|| SB | 7-bit data | PB | STB ||
|01|0|| SB | 9-bit data | STB ||
|01|1|| SB | 8-bit data | PB | STB ||
|10|0|| SB | 7-bit data | STB ||
|10|1|| SB | 6-bit data | PB | STB ||



1. Legends: SB: start bit, STB: stop bit, PB: parity bit. In the data register, the PB is always taking the MSB
position (9th, 8th or 7th, depending on the M bits value).


**Even parity**


The parity bit is calculated to obtain an even number of “1s” inside the frame of the 6, 7 or 8
LSB bits (depending on M bits values) and the parity bit.


As an example, if data=00110101, and 4 bits are set, then the parity bit will be 0 if even
parity is selected (PS bit in USART_CR1 = 0).


**Odd parity**


The parity bit is calculated to obtain an odd number of “1s” inside the frame made of the 6, 7
or 8 LSB bits (depending on M bits values) and the parity bit.


As an example, if data=00110101 and 4 bits set, then the parity bit will be 1 if odd parity is
selected (PS bit in USART_CR1 = 1).


**Parity checking in reception**


If the parity check fails, the PE flag is set in the USART_ISR register and an interrupt is
generated if PEIE is set in the USART_CR1 register. The PE flag is cleared by software
writing 1 to the PECF in the USART_ICR register.


RM0364 Rev 4 971/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Parity generation in transmission**


If the PCE bit is set in USART_CR1, then the MSB bit of the data written in the data register
is transmitted but is changed by the parity bit (even number of “1s” if even parity is selected
(PS=0) or an odd number of “1s” if odd parity is selected (PS=1)).


**28.5.10** **USART LIN (local interconnection network) mode**


This section is relevant only when LIN mode is supported. Please refer to _Section 28.4:_
_USART implementation on page 950_ .


The LIN mode is selected by setting the LINEN bit in the USART_CR2 register. In LIN
mode, the following bits must be kept cleared:


      - STOP[1:0] and CLKEN in the USART_CR2 register,


      - SCEN, HDSEL and IREN in the USART_CR3 register.


**LIN transmission**


The procedure explained in _Section 28.5.2: USART transmitter_ has to be applied for LIN
Master transmission. It must be the same as for normal USART transmission with the
following differences:


      - Clear the M bits to configure 8-bit word length.


      - Set the LINEN bit to enter LIN mode. In this case, setting the SBKRQ bit sends 13 ‘0’
bits as a break character. Then 2 bits of value ‘1’ are sent to allow the next start

detection.


**LIN reception**


When LIN mode is enabled, the break detection circuit is activated. The detection is totally
independent from the normal USART receiver. A break can be detected whenever it occurs,
during Idle state or during a frame.


When the receiver is enabled (RE=1 in USART_CR1), the circuit looks at the RX input for a
start signal. The method for detecting start bits is the same when searching break
characters or data. After a start bit has been detected, the circuit samples the next bits
exactly like for the data (on the 8th, 9th and 10th samples). If 10 (when the LBDL = 0 in
USART_CR2) or 11 (when LBDL=1 in USART_CR2) consecutive bits are detected as ‘0,
and are followed by a delimiter character, the LBDF flag is set in USART_ISR. If the LBDIE
bit=1, an interrupt is generated. Before validating the break, the delimiter is checked for as it
signifies that the RX line has returned to a high level.


If a ‘1’ is sampled before the 10 or 11 have occurred, the break detection circuit cancels the
current detection and searches for a start bit again.


If the LIN mode is disabled (LINEN=0), the receiver continues working as normal USART,
without taking into account the break detection.


If the LIN mode is enabled (LINEN=1), as soon as a framing error occurs (i.e. stop bit
detected at ‘0’, which will be the case for any break frame), the receiver stops until the break
detection circuit receives either a ‘1’, if the break word was not complete, or a delimiter
character if a break has been detected.


The behavior of the break detector state machine and the break flag is shown on the
_Figure 363: Break detection in LIN mode (11-bit break length - LBDL bit is set) on page 973_ .


972/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


Examples of break frames are given on _Figure 364: Break detection in LIN mode vs._
_Framing error detection on page 974_ .


**Figure 363. Break detection in LIN mode (11-bit break length - LBDL bit is set)**





























RM0364 Rev 4 973/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Figure 364. Break detection in LIN mode vs. Framing error detection**















**28.5.11** **USART synchronous mode**


The synchronous mode is selected by writing the CLKEN bit in the USART_CR2 register to
1. In synchronous mode, the following bits must be kept cleared:


      - LINEN bit in the USART_CR2 register,


      - SCEN, HDSEL and IREN bits in the USART_CR3 register.


In this mode, the USART can be used to control bidirectional synchronous serial
communications in master mode. The CK pin is the output of the USART transmitter clock.
No clock pulses are sent to the CK pin during start bit and stop bit. Depending on the state
of the LBCL bit in the USART_CR2 register, clock pulses are, or are not, generated during
the last valid data bit (address mark). The CPOL bit in the USART_CR2 register is used to
select the clock polarity, and the CPHA bit in the USART_CR2 register is used to select the
phase of the external clock (see _Figure 365_, _Figure 366_ and _Figure 367_ ).


During the Idle state, preamble and send break, the external CK clock is not activated.


In synchronous mode the USART transmitter works exactly like in asynchronous mode. But
as CK is synchronized with TX (according to CPOL and CPHA), the data on TX is
synchronous.


In this mode the USART receiver works in a different manner compared to the
asynchronous mode. If RE=1, the data is sampled on CK (rising or falling edge, depending
on CPOL and CPHA), without any oversampling. A setup and a hold time must be
respected (which depends on the baud rate: 1/16 bit duration).


974/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


_Note:_ _The CK pin works in conjunction with the TX pin. Thus, the clock is provided only if the_
_transmitter is enabled (TE=1) and data is being transmitted (the data register USART_TDR_
_written). This means that it is not possible to receive synchronous data without transmitting_
_data._


_The LBCL, CPOL and CPHA bits have to be selected when the USART is disabled (UE=0)_
_to ensure that the clock pulses function correctly._


**Figure 365. USART example of synchronous transmission**


**Figure 366. USART data clock timing diagram (** M bits = 00 **)**








|Start|Col2|Col3|Col4|Col5|M|M bi|its =|= 00|(8 d|data|bits)|)|Col14|Col15|Col16|Col17|Col18|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|A=0)||||||||||||||||||
|A=0)||||||||||||||||*|*|
|A=1)||||||||||||||||||
|A=1)|||||||||||||||*|*|*|
|||||||||||||||||*||
|A=0)|||||||||||||||*|*||
|A=0)||||||||||||||||||
|A=0)||||||||||||||||||

















RM0364 Rev 4 975/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Figure 367. USART data clock timing diagram (** M bits = 01 **)**








|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|Col17|Col18|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|||||||||||||||||||
|||||||||||||||||||
||||||||||||||||||*|
|||||||||||||||||||
||||||||||||||||||*|
|||||||||||||||||||
|||||||||||||||||||


|*|Col2|
|---|---|
|*||
|*||
|*||
|||
|||



**Figure 368. RX data setup/hold time**


















|Col1|Col2|
|---|---|
|||
|Valid D|ATA bit|



_Note:_ _The function of CK is different in Smartcard mode. Refer to Section 28.5.13: USART_

_Smartcard mode for more details._


976/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


**28.5.12** **USART Single-wire Half-duplex communication**


Single-wire Half-duplex mode is selected by setting the HDSEL bit in the USART_CR3
register. In this mode, the following bits must be kept cleared:


      - LINEN and CLKEN bits in the USART_CR2 register,


      - SCEN and IREN bits in the USART_CR3 register.


The USART can be configured to follow a Single-wire Half-duplex protocol where the TX
and RX lines are internally connected. The selection between half- and Full-duplex
communication is made with a control bit HDSEL in USART_CR3.


As soon as HDSEL is written to 1:


      - The TX and RX lines are internally connected


      - The RX pin is no longer used


      - The TX pin is always released when no data is transmitted. Thus, it acts as a standard
I/O in idle or in reception. It means that the I/O must be configured so that TX is
configured as alternate function open-drain with an external pull-up.


Apart from this, the communication protocol is similar to normal USART mode. Any conflicts
on the line must be managed by software (by the use of a centralized arbiter, for instance).
In particular, the transmission is never blocked by hardware and continues as soon as data
is written in the data register while the TE bit is set.


**28.5.13** **USART Smartcard mode**


This section is relevant only when Smartcard mode is supported. Please refer to
_Section 28.4: USART implementation on page 950_ .


Smartcard mode is selected by setting the SCEN bit in the USART_CR3 register. In
Smartcard mode, the following bits must be kept cleared:


      - LINEN bit in the USART_CR2 register,


      - HDSEL and IREN bits in the USART_CR3 register.


Moreover, the CLKEN bit may be set in order to provide a clock to the smartcard.


The smartcard interface is designed to support asynchronous protocol for smartcards as
defined in the ISO 7816-3 standard. Both T=0 (character mode) and T=1 (block mode) are
supported.


The USART should be configured as:


      - 8 bits plus parity: where word length is set to 8 bits and PCE=1 in the USART_CR1
register


      - 1.5 stop bits: where STOP=11 in the USART_CR2 register. It is also possible to choose
0.5 stop bit for receiving.


In T=0 (character) mode, the parity error is indicated at the end of each character during the
guard time period.


_Figure 369_ shows examples of what can be seen on the data line with and without parity

error.


RM0364 Rev 4 977/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Figure 369. ISO 7816-3 asynchronous protocol**

















When connected to a smartcard, the TX output of the USART drives a bidirectional line that
is also driven by the smartcard. The TX pin must be configured as open drain.


Smartcard mode implements a single wire half duplex communication protocol.


      - Transmission of data from the transmit shift register is guaranteed to be delayed by a
minimum of 1/2 baud clock. In normal operation a full transmit shift register starts
shifting on the next baud clock edge. In Smartcard mode this transmission is further
delayed by a guaranteed 1/2 baud clock.


      - In transmission, if the smartcard detects a parity error, it signals this condition to the
USART by driving the line low (NACK). This NACK signal (pulling transmit line low for 1
baud clock) causes a framing error on the transmitter side (configured with 1.5 stop
bits). The USART can handle automatic re-sending of data according to the protocol.
The number of retries is programmed in the SCARCNT bit field. If the USART
continues receiving the NACK after the programmed number of retries, it stops
transmitting and signals the error as a framing error. The TXE bit can be set using the
TXFRQ bit in the USART_RQR register.


      - Smartcard auto-retry in transmission: a delay of 2.5 baud periods is inserted between
the NACK detection by the USART and the start bit of the repeated character. The TC
bit is set immediately at the end of reception of the last repeated character (no guardtime). If the software wants to repeat it again, it must insure the minimum 2 baud
periods required by the standard.


      - If a parity error is detected during reception of a frame programmed with a 1.5 stop bits
period, the transmit line is pulled low for a baud clock period after the completion of the
receive frame. This is to indicate to the smartcard that the data transmitted to the
USART has not been correctly received. A parity error is NACKed by the receiver if the
NACK control bit is set, otherwise a NACK is not transmitted (to be used in T=1 mode).
If the received character is erroneous, the RXNE/receive DMA request is not activated.
According to the protocol specification, the smartcard must resend the same character.
If the received character is still erroneous after the maximum number of retries
specified in the SCARCNT bit field, the USART stops transmitting the NACK and
signals the error as a parity error.


      - Smartcard auto-retry in reception: the BUSY flag remains set if the USART NACKs the
card but the card doesn’t repeat the character.


978/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


      - In transmission, the USART inserts the Guard Time (as programmed in the Guard Time
register) between two successive characters. As the Guard Time is measured after the
stop bit of the previous character, the GT[7:0] register must be programmed to the
desired CGT (Character Guard Time, as defined by the 7816-3 specification) minus 12
(the duration of one character).


      - The assertion of the TC flag can be delayed by programming the Guard Time register.
In normal operation, TC is asserted when the transmit shift register is empty and no
further transmit requests are outstanding. In Smartcard mode an empty transmit shift
register triggers the Guard Time counter to count up to the programmed value in the
Guard Time register. TC is forced low during this time. When the Guard Time counter
reaches the programmed value TC is asserted high.


      - The de-assertion of TC flag is unaffected by Smartcard mode.


      - If a framing error is detected on the transmitter end (due to a NACK from the receiver),
the NACK is not detected as a start bit by the receive block of the transmitter.
According to the ISO protocol, the duration of the received NACK can be 1 or 2 baud
clock periods.


      - On the receiver side, if a parity error is detected and a NACK is transmitted the receiver
does not detect the NACK as a start bit.


_Note:_ _A break character is not significant in Smartcard mode. A 0x00 data with a framing error is_
_treated as data and not as a break._


_No Idle frame is transmitted when toggling the TE bit. The Idle frame (as defined for the_
_other configurations) is not defined by the ISO protocol._


_Figure 370_ details how the NACK signal is sampled by the USART. In this example the
USART is transmitting data and is configured with 1.5 stop bits. The receiver part of the
USART is enabled in order to check the integrity of the data and the NACK signal.


**Figure 370. Parity error detection using the 1.5 stop bits**









The USART can provide a clock to the smartcard through the CK output. In Smartcard
mode, CK is not associated to the communication but is simply derived from the internal
peripheral input clock through a 5-bit prescaler. The division ratio is configured in the
prescaler register USART_GTPR. CK frequency can be programmed from f CK /2 to f CK /62,
where f CK is the peripheral input clock.


RM0364 Rev 4 979/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Block mode (T=1)**


In T=1 (block) mode, the parity error transmission is deactivated, by clearing the NACK bit in
the UART_CR3 register.


When requesting a read from the smartcard, in block mode, the software must enable the
receiver Timeout feature by setting the RTOEN bit in the USART_CR2 register and program
the RTO bits field in the RTOR register to the BWT (block wait time) - 11 value. If no answer
is received from the card before the expiration of this period, the RTOF flag will be set and a
timeout interrupt will be generated (if RTOIE bit in the USART_CR1 register is set). If the
first character is received before the expiration of the period, it is signaled by the RXNE
interrupt.


_Note:_ _The RXNE interrupt must be enabled even when using the USART in DMA mode to read_
_from the smartcard in block mode. In parallel, the DMA must be enabled only after the first_
_received byte._


After the reception of the first character (RXNE interrupt), the RTO bit fields in the RTOR
register must be programmed to the CWT (character wait time) - 11 value, in order to allow
the automatic check of the maximum wait time between two consecutive characters. This

time is expressed in baudtime units. If the smartcard does not send a new character in less
than the CWT period after the end of the previous character, the USART signals this to the
software through the RTOF flag and interrupt (when RTOIE bit is set).


_Note:_ _The RTO counter starts counting:_


_- From the end of the stop bit in case STOP = 00._


_- From the end of the second stop bit in case of STOP = 10._


_- 1 bit duration after the beginning of the STOP bit in case STOP = 11._


_- From the beginning of the STOP bit in case STOP = 01._


_As in the Smartcard protocol definition, the BWT/CWT values are defined from the_
_beginning (start bit) of the last character. The RTO register must be programmed to BWT -_
_11 or CWT -11, respectively, taking into account the length of the last character itself._


A block length counter is used to count all the characters received by the USART. This
counter is reset when the USART is transmitting (TXE=0). The length of the block is
communicated by the smartcard in the third byte of the block (prologue field). This value
must be programmed to the BLEN field in the USART_RTOR register. when using DMA
mode, before the start of the block, this register field must be programmed to the minimum
value (0x0). with this value, an interrupt is generated after the 4th received character. The
software must read the LEN field (third byte), its value must be read from the receive buffer.


In interrupt driven receive mode, the length of the block may be checked by software or by
programming the BLEN value. However, before the start of the block, the maximum value of
BLEN (0xFF) may be programmed. The real value will be programmed after the reception of
the third character.


If the block is using the LRC longitudinal redundancy check (1 epilogue byte), the
BLEN=LEN. If the block is using the CRC mechanism (2 epilogue bytes), BLEN=LEN+1
must be programmed. The total block length (including prologue, epilogue and information
fields) equals BLEN+4. The end of the block is signaled to the software through the EOBF
flag and interrupt (when EOBIE bit is set).


In case of an error in the block length, the end of the block is signaled by the RTO interrupt
(Character wait Time overflow).


980/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


_Note:_ _The error checking code (LRC/CRC) must be computed/verified by software._


**Direct and inverse convention**


The Smartcard protocol defines two conventions: direct and inverse.


The direct convention is defined as: LSB first, logical bit value of 1 corresponds to a H state
of the line and parity is even. In order to use this convention, the following control bits must
be programmed: MSBFIRST=0, DATAINV=0 (default values).


The inverse convention is defined as: MSB first, logical bit value 1 corresponds to an L state
on the signal line and parity is even. In order to use this convention, the following control bits
must be programmed: MSBFIRST=1, DATAINV=1.


_Note:_ _When logical data values are inverted (0=H, 1=L), the parity bit is also inverted in the same_

_way._


In order to recognize the card convention, the card sends the initial character, TS, as the
first character of the ATR (Answer To Reset) frame. The two possible patterns for the TS
are: LHHL LLL LLH and LHHL HHH LLH.


      - (H) LHHL LLL LLH sets up the inverse convention: state L encodes value 1 and
moment 2 conveys the most significant bit (MSB first). when decoded by inverse
convention, the conveyed byte is equal to '3F'.


      - (H) LHHL HHH LLH sets up the direct convention: state H encodes value 1 and
moment 2 conveys the least significant bit (LSB first). when decoded by direct
convention, the conveyed byte is equal to '3B'.


Character parity is correct when there is an even number of bits set to 1 in the nine
moments 2 to 10.


As the USART does not know which convention is used by the card, it needs to be able to
recognize either pattern and act accordingly. The pattern recognition is not done in
hardware, but through a software sequence. Moreover, supposing that the USART is
configured in direct convention (default) and the card answers with the inverse convention,
TS = LHHL LLL LLH => the USART received character will be ‘03’ and the parity will be odd.


Therefore, two methods are available for TS pattern recognition:


**Method 1**


The USART is programmed in standard Smartcard mode/direct convention. In this case, the
TS pattern reception generates a parity error interrupt and error signal to the card.


      - The parity error interrupt informs the software that the card didn’t answer correctly in
direct convention. Software then reprograms the USART for inverse convention


      - In response to the error signal, the card retries the same TS character, and it will be
correctly received this time, by the reprogrammed USART


Alternatively, in answer to the parity error interrupt, the software may decide to reprogram
the USART and to also generate a new reset command to the card, then wait again for the
TS.


RM0364 Rev 4 981/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Method 2**


The USART is programmed in 9-bit/no-parity mode, no bit inversion. In this mode it receives
any of the two TS patterns as:


(H) LHHL LLL LLH = 0x103 -> inverse convention to be chosen


(H) LHHL HHH LLH = 0x13B -> direct convention to be chosen


The software checks the received character against these two patterns and, if any of them
match, then programs the USART accordingly for the next character reception.


If none of the two is recognized, a card reset may be generated in order to restart the
negotiation.


**28.5.14** **USART IrDA SIR ENDEC block**


This section is relevant only when IrDA mode is supported. Please refer to _Section 28.4:_
_USART implementation on page 950_ .


IrDA mode is selected by setting the IREN bit in the USART_CR3 register. In IrDA mode,
the following bits must be kept cleared:


      - LINEN, STOP and CLKEN bits in the USART_CR2 register,


      - SCEN and HDSEL bits in the USART_CR3 register.


The IrDA SIR physical layer specifies use of a Return to Zero, Inverted (RZI) modulation
scheme that represents logic 0 as an infrared light pulse (see _Figure 371_ ).


The SIR Transmit encoder modulates the Non Return to Zero (NRZ) transmit bit stream
output from USART. The output pulse stream is transmitted to an external output driver and
infrared LED. USART supports only bit rates up to 115.2 Kbps for the SIR ENDEC. In
normal mode the transmitted pulse width is specified as 3/16 of a bit period.


The SIR receive decoder demodulates the return-to-zero bit stream from the infrared

detector and outputs the received NRZ serial bit stream to the USART. The decoder input is
normally high (marking state) in the Idle state. The transmit encoder output has the opposite
polarity to the decoder input. A start bit is detected when the decoder input is low.


      - IrDA is a half duplex communication protocol. If the Transmitter is busy (when the
USART is sending data to the IrDA encoder), any data on the IrDA receive line is
ignored by the IrDA decoder and if the Receiver is busy (when the USART is receiving
decoded data from the IrDA decoder), data on the TX from the USART to IrDA is not
encoded. while receiving data, transmission should be avoided as the data to be
transmitted could be corrupted.


      - A 0 is transmitted as a high pulse and a 1 is transmitted as a 0. The width of the pulse
is specified as 3/16th of the selected bit period in normal mode (see _Figure 372_ ).


      - The SIR decoder converts the IrDA compliant receive signal into a bit stream for
USART.


      - The SIR receive logic interprets a high state as a logic one and low pulses as logic

zeros.


      - The transmit encoder output has the opposite polarity to the decoder input. The SIR
output is in low state when Idle.


982/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


      - The IrDA specification requires the acceptance of pulses greater than 1.41 µs. The
acceptable pulse width is programmable. Glitch detection logic on the receiver end
filters out pulses of width less than 2 PSC periods (PSC is the prescaler value
programmed in the USART_GTPR). Pulses of width less than 1 PSC period are always
rejected, but those of width greater than one and less than two periods may be
accepted or rejected, those greater than 2 periods will be accepted as a pulse. The
IrDA encoder/decoder doesn’t work when PSC=0.


      - The receiver can communicate with a low-power transmitter.


      - In IrDA mode, the STOP bits in the USART_CR2 register must be configured to “1 stop
bit”.


**IrDA low-power mode**


**Transmitter**


In low-power mode the pulse width is not maintained at 3/16 of the bit period. Instead, the
width of the pulse is 3 times the low-power baud rate which can be a minimum of 1.42 MHz.


Generally, this value is 1.8432 MHz (1.42 MHz < PSC< 2.12 MHz). A low-power mode
programmable divisor divides the system clock to achieve this value.


**Receiver**


Receiving in low-power mode is similar to receiving in normal mode. For glitch detection the
USART should discard pulses of duration shorter than 1 PSC period. A valid low is accepted
only if its duration is greater than 2 periods of the IrDA low-power Baud clock (PSC value in
the USART_GTPR).


_Note:_ _A pulse of width less than two and greater than one PSC period(s) may or may not be_
_rejected._


_The receiver set up time should be managed by software. The IrDA physical layer_
_specification specifies a minimum of 10 ms delay between transmission and reception (IrDA_
_is a half duplex protocol)._


**Figure 371. IrDA SIR ENDEC- block diagram**














|TX|Col2|
|---|---|
|||
|||



RM0364 Rev 4 983/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Figure 372. IrDA data modulation (3/16) -Normal Mode**















**28.5.15** **USART continuous communication in DMA mode**


The USART is capable of performing continuous communication using the DMA. The DMA
requests for Rx buffer and Tx buffer are generated independently.


_Note:_ _Please refer to Section 28.4: USART implementation on page 950 to determine if the DMA_
_mode is supported. If DMA is not supported, use the USART as explained in Section 28.5.2:_
_USART transmitter or Section 28.5.3: USART receiver. To perform continuous_
_communication, the user can clear the TXE/ RXNE flags In the USART_ISR register._


**Transmission using DMA**


DMA mode can be enabled for transmission by setting DMAT bit in the USART_CR3
register. Data is loaded from a SRAM area configured using the DMA peripheral (refer to
_Section 11: Direct memory access controller (DMA) on page 170_ ) to the USART_TDR
register whenever the TXE bit is set. To map a DMA channel for USART transmission, use
the following procedure (x denotes the channel number):


1. Write the USART_TDR register address in the DMA control register to configure it as
the destination of the transfer. The data is moved to this address from memory after
each TXE event.


2. Write the memory address in the DMA control register to configure it as the source of
the transfer. The data is loaded into the USART_TDR register from this memory area
after each TXE event.


3. Configure the total number of bytes to be transferred to the DMA control register.


4. Configure the channel priority in the DMA register


5. Configure DMA interrupt generation after half/ full transfer as required by the
application.


6. Clear the TC flag in the USART_ISR register by setting the TCCF bit in the
USART_ICR register.


7. Activate the channel in the DMA register.


When the number of data transfers programmed in the DMA Controller is reached, the DMA
controller generates an interrupt on the DMA channel interrupt vector.


In transmission mode, once the DMA has written all the data to be transmitted (the TCIF flag
is set in the DMA_ISR register), the TC flag can be monitored to make sure that the USART


984/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


communication is complete. This is required to avoid corrupting the last transmission before
disabling the USART or entering Stop mode. Software must wait until TC=1. The TC flag
remains cleared during all data transfers and it is set by hardware at the end of transmission
of the last frame.


**Figure 373. Transmission using DMA**






|dle preamble|Col2|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
|||||||
|||||||
|||||||
|F1||F2||F3||
|||||||
|||||||





















**Reception using DMA**


DMA mode can be enabled for reception by setting the DMAR bit in USART_CR3 register.
Data is loaded from the USART_RDR register to a SRAM area configured using the DMA
peripheral (refer to _Section 11: Direct memory access controller (DMA) on page 170_ )
whenever a data byte is received. To map a DMA channel for USART reception, use the
following procedure:


1. Write the USART_RDR register address in the DMA control register to configure it as
the source of the transfer. The data is moved from this address to the memory after
each RXNE event.


2. Write the memory address in the DMA control register to configure it as the destination
of the transfer. The data is loaded from USART_RDR to this memory area after each
RXNE event.


3. Configure the total number of bytes to be transferred to the DMA control register.


4. Configure the channel priority in the DMA control register


5. Configure interrupt generation after half/ full transfer as required by the application.


6. Activate the channel in the DMA control register.


When the number of data transfers programmed in the DMA Controller is reached, the DMA
controller generates an interrupt on the DMA channel interrupt vector.


RM0364 Rev 4 985/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Figure 374. Reception using DMA**














|Col1|Col2|Col3|
|---|---|---|
||||
||F1|F2|
|||Set by hardware|
||||











**Error flagging and interrupt generation in multibuffer communication**


In multibuffer communication if any error occurs during the transaction the error flag is
asserted after the current byte. An interrupt is generated if the interrupt enable flag is set.
For framing error, overrun error and noise flag which are asserted with RXNE in single byte
reception, there is a separate error flag interrupt enable bit (EIE bit in the USART_CR3
register), which, if set, enables an interrupt after the current byte if any of these errors occur.


**28.5.16** **RS232 hardware flow control and RS485 driver enable**
**using USART**


It is possible to control the serial data flow between 2 devices by using the CTS input and
the RTS output. The _Figure 375_ shows how to connect 2 devices in this mode:


**Figure 375. Hardware flow control between 2 USARTs**















986/1124 RM0364 Rev 4




**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


RS232 RTS and CTS flow control can be enabled independently by writing the RTSE and
CTSE bits respectively to 1 (in the USART_CR3 register).


**RS232 RTS flow control**


If the RTS flow control is enabled (RTSE=1), then RTS is asserted (tied low) as long as the
USART receiver is ready to receive a new data. When the receive register is full, RTS is deasserted, indicating that the transmission is expected to stop at the end of the current frame.
_Figure 376_ shows an example of communication with RTS flow control enabled.


**Figure 376. RS232 RTS flow control**









**RS232 CTS flow control**







If the CTS flow control is enabled (CTSE=1), then the transmitter checks the CTS input
before transmitting the next frame. If CTS is asserted (tied low), then the next data is
transmitted (assuming that data is to be transmitted, in other words, if TXE=0), else the
transmission does not occur. when CTS is de-asserted during a transmission, the current
transmission is completed before the transmitter stops.


When CTSE=1, the CTSIF status bit is automatically set by hardware as soon as the CTS
input toggles. It indicates when the receiver becomes ready or not ready for communication.
An interrupt is generated if the CTSIE bit in the USART_CR3 register is set. _Figure 377_
shows an example of communication with CTS flow control enabled.


RM0364 Rev 4 987/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Figure 377. RS232 CTS flow control**












|Col1|Col2|Col3|
|---|---|---|
|empty|Data 3||
|empty|Data 3||













_Note:_ _For correct behavior, CTS must be asserted at least 3 USART clock source periods before_
_the end of the current character. In addition it should be noted that the CTSCF flag may not_
_be set for pulses shorter than 2 x PCLK periods._


**RS485 Driver Enable**


The driver enable feature is enabled by setting bit DEM in the USART_CR3 control register.
This allows the user to activate the external transceiver control, through the DE (Driver
Enable) signal. The assertion time is the time between the activation of the DE signal and
the beginning of the START bit. It is programmed using the DEAT [4:0] bit fields in the
USART_CR1 control register. The de-assertion time is the time between the end of the last
stop bit, in a transmitted message, and the de-activation of the DE signal. It is programmed
using the DEDT [4:0] bit fields in the USART_CR1 control register. The polarity of the DE
signal can be configured using the DEP bit in the USART_CR3 control register.


In USART, the DEAT and DEDT are expressed in sample time units (1/8 or 1/16 bit duration,
depending on the oversampling rate).


**28.5.17** **Wakeup from Stop mode using USART**


The USART is able to wake up the MCU from Stopmode when the UESM bit is set and the
USART clock is set to HSI or LSE (refer to Section Reset and clock control (RCC)).


      - USART source clock is HSI


If during stop mode the HSI clock is switched OFF, when a falling edge on the USART
receive line is detected, the USART interface requests the HSI clock to be switched
ON. The HSI clock is then used for the frame reception.


–
If the wakeup event is verified, the MCU wakes up from low-power mode and data
reception goes on normally.


–
If the wakeup event is not verified, the HSI clock is switched OFF again, the MCU
is not waken up and stays in low-power mode and the clock request is released.


      - USART source clock is LSE


Same principle as described in case of USART source clock is HSI with the difference
that the LSE is ON in stop mode, but the LSE clock is not propagated to USART if the


988/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


USART is not requesting it. The LSE clock is not OFF but there is a clock gating to
avoid useless consumption.


The MCU wakeup from Stop mode can be done using the standard RXNE interrupt. In this
case, the RXNEIE bit must be set before entering Stop mode.


Alternatively, a specific interrupt may be selected through the WUS bit fields.


In order to be able to wake up the MCU from Stop mode, the UESM bit in the USART_CR1
control register must be set prior to entering Stop mode.


When the wakeup event is detected, the WUF flag is set by hardware and a wakeup
interrupt is generated if the WUFIE bit is set.


_Note:_ _Before entering Stop mode, the user must ensure that the USART is not performing a_
_transfer. BUSY flag cannot ensure that Stop mode is never entered during a running_
_reception._


_The WUF flag is set when a wakeup event is detected, independently of whether the MCU is_
_in Stop or in an active mode._


_When entering Stop mode just after having initialized and enabled the receiver, the REACK_
_bit must be checked to ensure the USART is actually enabled._


_When DMA is used for reception, it must be disabled before entering Stop mode and re-_
_enabled upon exit from Stop mode._


_The wakeup from Stop mode feature is not available for all modes. For example it doesn’t_
_work in SPI mode because the SPI operates in master mode only._


**Using Mute mode with Stop mode**


If the USART is put into Mute mode before entering Stop mode:


      - Wakeup from Mute mode on idle detection must not be used, because idle detection
cannot work in Stop mode.


      - If the wakeup from Mute mode on address match is used, then the source of wake-up
from Stop mode must also be the address match. If the RXNE flag is set when entering
the Stop mode, the interface will remain in mute mode upon address match and wake
up from Stop.


      - If the USART is configured to wake up the MCU from Stop mode on START bit
detection, the WUF flag is set, but the RXNE flag is not set.


**Determining the maximum USART baud rate allowing to wakeup correctly**
**from Stop mode when the USART clock source is the HSI clock**


The maximum baud rate allowing to wakeup correctly from stop mode depends on:


      - the parameter t WUUSART provided in the device datasheet


      - the USART receiver tolerance provided in the _Section 28.5.5: Tolerance of the USART_
_receiver to clock deviation_ .


Let us take this example: OVER8 = 0, M bits = 10, ONEBIT = 1, BRR [3:0] = 0000.


In these conditions, according to _Table 138: Tolerance of the USART receiver when BRR_

_[3:0] = 0000_, the USART receiver tolerance is 4.86 %.


DTRA + DQUANT + DREC + DTCL + DWU < USART receiver's tolerance


DWU max = t WUUSART / (9 x Tbit Min)


Tbit Min = t WUUSART / (9 x DWU max)


RM0364 Rev 4 989/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


If we consider an ideal case where the parameters DTRA, DQUANT, DREC and DTCL are
at 0%, the DWU max is 4.86 %. In reality, we need to consider at least the HSI inaccuracy.


Let us consider HSI inaccuracy = 1 %, t WUUSART = 3.125 μs (in case of wakeup from stop
mode, with the main regulator in Run mode).


DWU max = 4.86 % - 1 % = 3.86 %


Tbit min = 3.125 μs / (9 ₓ 3.86 %) = 9 μs


In these conditions, the maximum baud rate allowing to wakeup correctly from Stop mode is
1/9 μs = 111 Kbaud.

## **28.6 USART low-power modes**


**Table 141. Effect of low-power modes on the USART**







|Mode|Description|
|---|---|
|Sleep|No effect. USART interrupt causes the device to exit Sleep mode.|
|Stop|The USART is able to wake up the MCU from Stop mode when the UESM<br>bit is set and the USART clock is set to HSI or LSE.<br>The MCU wakeup from Stop mode can be done using either a standard<br>RXNE or a WUF interrupt.|
|Standby|The USART is powered down and must be reinitialized when the device<br>has exited from Standby mode.|

## **28.7 USART interrupts**

**Table 142. USART interrupt requests**

|Interrupt event|Event flag|Enable Control<br>bit|
|---|---|---|
|Transmit data register empty|TXE|TXEIE|
|CTS interrupt|CTSIF|CTSIE|
|Transmission Complete|TC|TCIE|
|Receive data register not empty (data ready to be read)|RXNE|RXNEIE|
|Overrun error detected|ORE|ORE|
|Idle line detected|IDLE|IDLEIE|
|Parity error|PE|PEIE|
|LIN break|LBDF|LBDIE|
|Noise Flag, Overrun error and Framing Error in multibuffer<br>communication.|NF or ORE or FE|EIE|
|Character match|CMF|CMIE|
|Receiver timeout|RTOF|RTOIE|
|End of Block|EOBF|EOBIE|
|Wakeup from Stop mode|WUF(1)|WUFIE|



990/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


1. The WUF interrupt is active only in Stop mode.


The USART interrupt events are connected to the same interrupt vector (see _Figure 378_ ).


      - During transmission: Transmission Complete, Clear to Send, Transmit data Register
empty or Framing error (in Smartcard mode) interrupt.


      - During reception: Idle Line detection, Overrun error, Receive data register not empty,
Parity error, LIN break detection, Noise Flag, Framing Error, Character match, etc.


These events generate an interrupt if the corresponding Enable Control Bit is set.


**Figure 378. USART interrupt mapping diagram**







RM0364 Rev 4 991/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**

## **28.8 USART registers**


Refer to _Section 1.2 on page 43_ for a list of abbreviations used in register descriptions.


The peripheral registers have to be accessed by words (32 bits).


**28.8.1** **USART control register 1 (USART_CR1)**


Address offset: 0x00


Reset value: 0x0000 0000

|31|30|29|28|27|26|25 24 23 22 21|Col8|Col9|Col10|Col11|20 19 18 17 16|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|M1|EOBIE|RTOIE|DEAT[4:0]|DEAT[4:0]|DEAT[4:0]|DEAT[4:0]|DEAT[4:0]|DEDT[4:0]|DEDT[4:0]|DEDT[4:0]|DEDT[4:0]|DEDT[4:0]|
||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|OVER8|CMIE|MME|M0|WAKE|PCE|PS|PEIE|TXEIE|TCIE|RXNEIE|IDLEIE|TE|RE|UESM|UE|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:29 Reserved, must be kept at reset value.


Bit 28 **M1** : Word length

This bit, with bit 12 (M0), determines the word length. It is set or cleared by software.
M[1:0] = 00: 1 Start bit, 8 data bits, n stop bits
M[1:0] = 01: 1 Start bit, 9 data bits, n stop bits
M[1:0] = 10: 1 Start bit, 7 data bits, n stop bits
This bit can only be written when the USART is disabled (UE=0).


_Note: Not all modes are supported In 7-bit data length mode. Refer to Section 28.4: USART_
_implementation for details._


Bit 27 **EOBIE** : End of Block interrupt enable

This bit is set and cleared by software.
0: Interrupt is inhibited
1: A USART interrupt is generated when the EOBF flag is set in the USART_ISR register.

_Note: If the USART does not support Smartcard mode, this bit is reserved and must be kept_
_at reset value. Please refer to Section 28.4: USART implementation on page 950._


Bit 26 **RTOIE** : Receiver timeout interrupt enable

This bit is set and cleared by software.
0: Interrupt is inhibited
1: An USART interrupt is generated when the RTOF bit is set in the USART_ISR register.

_Note: If the USART does not support the Receiver timeout feature, this bit is reserved and_
_must be kept at reset value. Section 28.4: USART implementation on page 950._


Bits 25:21 **DEAT[4:0]** : Driver Enable assertion time

This 5-bit value defines the time between the activation of the DE (Driver Enable) signal and
the beginning of the start bit. It is expressed in sample time units (1/8 or 1/16 bit duration,
depending on the oversampling rate).
This bit field can only be written when the USART is disabled (UE=0).

_Note: If the Driver Enable feature is not supported, this bit is reserved and must be kept at_
_reset value. Please refer to Section 28.4: USART implementation on page 950._


992/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


Bits 20:16 **DEDT[4:0]** : Driver Enable de-assertion time

This 5-bit value defines the time between the end of the last stop bit, in a transmitted
message, and the de-activation of the DE (Driver Enable) signal. It is expressed in sample
time units (1/8 or 1/16 bit duration, depending on the oversampling rate).
If the USART_TDR register is written during the DEDT time, the new data is transmitted only
when the DEDT and DEAT times have both elapsed.
This bit field can only be written when the USART is disabled (UE=0).

_Note: If the Driver Enable feature is not supported, this bit is reserved and must be kept at_
_reset value. Please refer to Section 28.4: USART implementation on page 950._


Bit 15 **OVER8** : Oversampling mode

0: Oversampling by 16
1: Oversampling by 8
This bit can only be written when the USART is disabled (UE=0).

_Note: In LIN, IrDA and modes, this bit must be kept at reset value._


Bit 14 **CMIE** : Character match interrupt enable

This bit is set and cleared by software.
0: Interrupt is inhibited
1: A USART interrupt is generated when the CMF bit is set in the USART_ISR register.


Bit 13 **MME** : Mute mode enable

This bit activates the mute mode function of the USART. when set, the USART can switch
between the active and mute modes, as defined by the WAKE bit. It is set and cleared by
software.

0: Receiver in active mode permanently

1: Receiver can switch between mute mode and active mode.


Bit 12 **M0** : Word length

This bit, with bit 28 (M1), determines the word length. It is set or cleared by software. See Bit
28 (M1) description.
This bit can only be written when the USART is disabled (UE=0).


Bit 11 **WAKE** : Receiver wakeup method

This bit determines the USART wakeup method from Mute mode. It is set or cleared by
software.

0: Idle line

1: Address mark

This bit field can only be written when the USART is disabled (UE=0).


Bit 10 **PCE** : Parity control enable

This bit selects the hardware parity control (generation and detection). When the parity
control is enabled, the computed parity is inserted at the MSB position (9th bit if M=1; 8th bit
if M=0) and parity is checked on the received data. This bit is set and cleared by software.
Once it is set, PCE is active after the current byte (in reception and in transmission).
0: Parity control disabled
1: Parity control enabled
This bit field can only be written when the USART is disabled (UE=0).


Bit 9 **PS** : Parity selection

This bit selects the odd or even parity when the parity generation/detection is enabled (PCE
bit set). It is set and cleared by software. The parity will be selected after the current byte.
0: Even parity
1: Odd parity
This bit field can only be written when the USART is disabled (UE=0).


RM0364 Rev 4 993/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


Bit 8 **PEIE** : PE interrupt enable

This bit is set and cleared by software.
0: Interrupt is inhibited
1: A USART interrupt is generated whenever PE=1 in the USART_ISR register


Bit 7 **TXEIE** : interrupt enable

This bit is set and cleared by software.
0: Interrupt is inhibited
1: A USART interrupt is generated whenever TXE=1 in the USART_ISR register


Bit 6 **TCIE** : Transmission complete interrupt enable

This bit is set and cleared by software.
0: Interrupt is inhibited
1: A USART interrupt is generated whenever TC=1 in the USART_ISR register


Bit 5 **RXNEIE** : RXNE interrupt enable

This bit is set and cleared by software.
0: Interrupt is inhibited
1: A USART interrupt is generated whenever ORE=1 or RXNE=1 in the USART_ISR
register


Bit 4 **IDLEIE** : IDLE interrupt enable

This bit is set and cleared by software.
0: Interrupt is inhibited
1: A USART interrupt is generated whenever IDLE=1 in the USART_ISR register


Bit 3 **TE** : Transmitter enable

This bit enables the transmitter. It is set and cleared by software.

0: Transmitter is disabled

1: Transmitter is enabled

_Note: During transmission, a “0” pulse on the TE bit (“0” followed by “1”) sends a preamble_
_(idle line) after the current word, except in Smartcard mode. In order to generate an idle_
_character, the TE must not be immediately written to 1. In order to ensure the required_
_duration, the software can poll the TEACK bit in the USART_ISR register._

_In Smartcard mode, when TE is set there is a 1 bit-time delay before the transmission_
_starts._


994/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


Bit 2 **RE** : Receiver enable

This bit enables the receiver. It is set and cleared by software.

0: Receiver is disabled

1: Receiver is enabled and begins searching for a start bit


Bit 1 **UESM** : USART enable in Stop mode

When this bit is cleared, the USART is not able to wake up the MCU from Stop mode.
When this bit is set, the USART is able to wake up the MCU from Stop mode, provided that
the USART clock selection is HSI or LSE in the RCC.

This bit is set and cleared by software.
0: USART not able to wake up the MCU from Stop mode.
1: USART able to wake up the MCU from Stop mode. When this function is active, the clock
source for the USART must be HSI or LSE (see Section Reset and clock control (RCC) .

_Note: It is recommended to set the UESM bit just before entering Stop mode and clear it on_
_exit from Stop mode._

_If the USART does not support the wakeup from Stop feature, this bit is reserved and_
_must be kept at reset value. Please refer to Section 28.4: USART implementation on_
_page 950._


Bit 0 **UE** : USART enable

When this bit is cleared, the USART prescalers and outputs are stopped immediately, and
current operations are discarded. The configuration of the USART is kept, but all the status
flags, in the USART_ISR are set to their default values. This bit is set and cleared by
software.

0: USART prescaler and outputs disabled, low-power mode

1: USART enabled

_Note: In order to go into low-power mode without generating errors on the line, the TE bit_
_must be reset before and the software must wait for the TC bit in the USART_ISR to be_
_set before resetting the UE bit._

_The DMA requests are also reset when UE = 0 so the DMA channel must be disabled_
_before resetting the UE bit._


**28.8.2** **USART control register 2 (USART_CR2)**


Address offset: 0x04


Reset value: 0x0000 0000

|31 30 29 28|Col2|Col3|Col4|27 26 25 24|Col6|Col7|Col8|23|22 21|Col11|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ADD[7:4]|ADD[7:4]|ADD[7:4]|ADD[7:4]|ADD[3:0]|ADD[3:0]|ADD[3:0]|ADD[3:0]|RTOEN|ABRMOD[1:0]|ABRMOD[1:0]|ABREN|MSBFI<br>RST|DATAINV|TXINV|RXINV|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13 12|Col4|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SWAP|LINEN|STOP[1:0]|STOP[1:0]|CLKEN|CPOL|CPHA|LBCL|Res.|LBDIE|LBDL|ADDM7|Res.|Res.|Res.|Res.|
|rw|rw|rw|rw|rw|rw|rw|rw||rw|rw|rw|||||



RM0364 Rev 4 995/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


Bits 31:28 **ADD[7:4]** : Address of the USART node

This bit-field gives the address of the USART node or a character code to be recognized.
This is used in multiprocessor communication during Mute mode or Stop mode, for wakeup with 7bit address mark detection. The MSB of the character sent by the transmitter should be equal to 1.
It may also be used for character detection during normal reception, Mute mode inactive (for
example, end of block detection in ModBus protocol). In this case, the whole received character (8bit) is compared to the ADD[7:0] value and CMF flag is set on match.
This bit field can only be written when reception is disabled (RE = 0) or the USART is disabled
(UE=0)


Bits 27:24 **ADD[3:0]** : Address of the USART node

This bit-field gives the address of the USART node or a character code to be recognized.
This is used in multiprocessor communication during Mute mode or Stop mode, for wakeup with
address mark detection.

This bit field can only be written when reception is disabled (RE = 0) or the USART is disabled
(UE=0)


Bit 23 **RTOEN** : Receiver timeout enable

This bit is set and cleared by software.

0: Receiver timeout feature disabled.

1: Receiver timeout feature enabled.

When this feature is enabled, the RTOF flag in the USART_ISR register is set if the RX line is idle
(no reception) for the duration programmed in the RTOR (receiver timeout register).

_Note: If the USART does not support the Receiver timeout feature, this bit is reserved and must be_
_kept at reset value. Please refer to Section 28.4: USART implementation on page 950._


Bits 22:21 **ABRMOD[1:0]** : Auto baud rate mode

These bits are set and cleared by software.

00: Measurement of the start bit is used to detect the baud rate.

01: Falling edge to falling edge measurement. (the received frame must start with a single bit = 1 ->
Frame = Start10xxxxxx)

10: 0x7F frame detection.

11: 0x55 frame detection

This bit field can only be written when ABREN = 0 or the USART is disabled (UE=0).

_Note: If DATAINV=1 and/or MSBFIRST=1 the patterns must be the same on the line, for example_
_0xAA for MSBFIRST)_

_If the USART does not support the auto baud rate feature, this bit is reserved and must be kept_
_at reset value. Please refer to Section 28.4: USART implementation on page 950._


Bit 20 **ABREN** : Auto baud rate enable

This bit is set and cleared by software.

0: Auto baud rate detection is disabled.

1: Auto baud rate detection is enabled.

_Note: If the USART does not support the auto baud rate feature, this bit is reserved and must be kept_
_at reset value. Please refer to Section 28.4: USART implementation on page 950._


Bit 19 **MSBFIRST** : Most significant bit first

This bit is set and cleared by software.
0: data is transmitted/received with data bit 0 first, following the start bit.
1: data is transmitted/received with the MSB (bit 7/8/9) first, following the start bit.
This bit field can only be written when the USART is disabled (UE=0).


996/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


Bit 18 **DATAINV:** Binary data inversion

This bit is set and cleared by software.
0: Logical data from the data register are send/received in positive/direct logic. (1=H, 0=L)
1: Logical data from the data register are send/received in negative/inverse logic. (1=L, 0=H). The
parity bit is also inverted.
This bit field can only be written when the USART is disabled (UE=0).


Bit 17 **TXINV:** TX pin active level inversion

This bit is set and cleared by software.
0: TX pin signal works using the standard logic levels (V DD =1/idle, Gnd=0/mark)
1: TX pin signal values are inverted. (V DD =0/mark, Gnd=1/idle).
This allows the use of an external inverter on the TX line.

This bit field can only be written when the USART is disabled (UE=0).


Bit 16 **RXINV:** RX pin active level inversion

This bit is set and cleared by software.
0: RX pin signal works using the standard logic levels (V DD =1/idle, Gnd=0/mark)
1: RX pin signal values are inverted. (V DD =0/mark, Gnd=1/idle).
This allows the use of an external inverter on the RX line.

This bit field can only be written when the USART is disabled (UE=0).


Bit 15 **SWAP:** Swap TX/RX pins

This bit is set and cleared by software.
0: TX/RX pins are used as defined in standard pinout
1: The TX and RX pins functions are swapped. This allows to work in the case of a cross-wired
connection to another USART.

This bit field can only be written when the USART is disabled (UE=0).


Bit 14 **LINEN** : LIN mode enable

This bit is set and cleared by software.

0: LIN mode disabled

1: LIN mode enabled

The LIN mode enables the capability to send LIN synchronous breaks (13 low bits) using the
SBKRQ bit in the USART_RQR register, and to detect LIN Sync breaks.
This bit field can only be written when the USART is disabled (UE=0).

_Note: If the USART does not support LIN mode, this bit is reserved and must be kept at reset value._
_Please refer to Section 28.4: USART implementation on page 950._


Bits 13:12 **STOP[1:0]** : STOP bits

These bits are used for programming the stop bits.
00: 1 stop bit
01: 0.5 stop bit
10: 2 stop bits
11: 1.5 stop bits
This bit field can only be written when the USART is disabled (UE=0).


RM0364 Rev 4 997/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


Bit 11 **CLKEN** : Clock enable

This bit allows the user to enable the CK pin.
0: CK pin disabled
1: CK pin enabled
This bit can only be written when the USART is disabled (UE=0).

_Note: If neither synchronous mode nor Smartcard mode is supported, this bit is reserved and must_
_be kept at reset value. Please refer to Section 28.4: USART implementation on page 950._

_In order to provide correctly the CK clock to the Smartcard when CK is always available When_
_CLKEN = 1, regardless of the UE bit value, the steps below must be respected:_

_- UE = 0_

_- SCEN = 1_

_- GTPR configuration (If PSC needs to be configured, it is recommended to configure PSC and_
_GT in a single access to USART_ GTPR register)._

_- CLKEN= 1_

_- UE = 1_


Bit 10 **CPOL** : Clock polarity

This bit allows the user to select the polarity of the clock output on the CK pin in synchronous mode.
It works in conjunction with the CPHA bit to produce the desired clock/data relationship
0: Steady low value on CK pin outside transmission window
1: Steady high value on CK pin outside transmission window
This bit can only be written when the USART is disabled (UE=0).

_Note: If synchronous mode is not supported, this bit is reserved and must be kept at reset value._
_Please refer to Section 28.4: USART implementation on page 950._


Bit 9 **CPHA** : Clock phase

This bit is used to select the phase of the clock output on the CK pin in synchronous mode. It works
in conjunction with the CPOL bit to produce the desired clock/data relationship (see _Figure 366_ and
_Figure 367_ )
0: The first clock transition is the first data capture edge
1: The second clock transition is the first data capture edge
This bit can only be written when the USART is disabled (UE=0).

_Note: If synchronous mode is not supported, this bit is reserved and must be kept at reset value._
_Please refer to Section 28.4: USART implementation on page 950._


Bit 8 **LBCL** : Last bit clock pulse

This bit is used to select whether the clock pulse associated with the last data bit transmitted (MSB)
has to be output on the CK pin in synchronous mode.
0: The clock pulse of the last data bit is not output to the CK pin
1: The clock pulse of the last data bit is output to the CK pin


**Caution:** The last bit is the 7th or 8th or 9th data bit transmitted depending on the 7 or 8 or 9 bit
format selected by the M bits in the USART_CR1 register.
This bit can only be written when the USART is disabled (UE=0).

_Note: If synchronous mode is not supported, this bit is reserved and must be kept at reset value._
_Please refer to Section 28.4: USART implementation on page 950._


Bit 7 Reserved, must be kept at reset value.


Bit 6 **LBDIE** : LIN break detection interrupt enable

Break interrupt mask (break detection using break delimiter).
0: Interrupt is inhibited
1: An interrupt is generated whenever LBDF=1 in the USART_ISR register

_Note: If LIN mode is not supported, this bit is reserved and must be kept at reset value. Please refer_
_to Section 28.4: USART implementation on page 950._


998/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


Bit 5 **LBDL** : LIN break detection length

This bit is for selection between 11 bit or 10 bit break detection.

0: 10-bit break detection

1: 11-bit break detection

This bit can only be written when the USART is disabled (UE=0).

_Note: If LIN mode is not supported, this bit is reserved and must be kept at reset value. Please refer_
_to Section 28.4: USART implementation on page 950._


Bit 4 **ADDM7** :7-bit Address Detection/4-bit Address Detection

This bit is for selection between 4-bit address detection or 7-bit address detection.

0: 4-bit address detection

1: 7-bit address detection (in 8-bit data mode)
This bit can only be written when the USART is disabled (UE=0)

_Note: In 7-bit and 9-bit data modes, the address detection is done on 6-bit and 8-bit address_
_(ADD[5:0] and ADD[7:0]) respectively._


Bits 3:0 Reserved, must be kept at reset value.


_Note:_ _The 3 bits (CPOL, CPHA, LBCL) should not be written while the transmitter is enabled._


**28.8.3** **USART control register 3 (USART_CR3)**


Address offset: 0x08


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|WUFIE|WUS1|WUS0|SCARC<br>NT2|SCARC<br>NT1|SCARC<br>NT0|Res.|
||||||||||rw|rw|rw|rw|rw|rw||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DEP|DEM|DDRE|OVRDI<br>S|ONEBI<br>T|CTSIE|CTSE|RTSE|DMAT|DMAR|SCEN|NACK|HDSEL|IRLP|IREN|EIE|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:25 Reserved, must be kept at reset value.


Bit 24 Reserved, must be kept at reset value.


Bit 23 Reserved, must be kept at reset value.


Bit 22 **WUFIE** : Wakeup from Stop mode interrupt enable

This bit is set and cleared by software.
0: Interrupt is inhibited
1: An USART interrupt is generated whenever WUF=1 in the USART_ISR register

_Note: WUFIE must be set before entering in Stop mode._

_The WUF interrupt is active only in Stop mode._

_If the USART does not support the wakeup from Stop feature, this bit is reserved and_
_must be kept at reset value._


RM0364 Rev 4 999/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


Bits 21:20 **WUS[1:0]** : Wakeup from Stop mode interrupt flag selection

This bit-field specify the event which activates the WUF (wakeup from Stop mode flag).
00: WUF active on address match (as defined by ADD[7:0] and ADDM7)

01:Reserved.

10: WuF active on Start bit detection

11: WUF active on RXNE.

This bit field can only be written when the USART is disabled (UE=0).

_Note: If the USART does not support the wakeup from Stop feature, this bit is reserved and_
_must be kept at reset value._


Bits 19:17 **SCARCNT[2:0]** : Smartcard auto-retry count

This bit-field specifies the number of retries in transmit and receive, in Smartcard mode.
In transmission mode, it specifies the number of automatic retransmission retries, before
generating a transmission error (FE bit set).
In reception mode, it specifies the number or erroneous reception trials, before generating a
reception error (RXNE and PE bits set).
This bit field must be programmed only when the USART is disabled (UE=0).
When the USART is enabled (UE=1), this bit field may only be written to 0x0, in order to stop
retransmission.

0x0: retransmission disabled - No automatic retransmission in transmit mode.

0x1 to 0x7: number of automatic retransmission attempts (before signaling error)

_Note: If Smartcard mode is not supported, this bit is reserved and must be kept at reset_
_value. Please refer to Section 28.4: USART implementation on page 950._


Bit 16 Reserved, must be kept at reset value.


Bit 15 **DEP** : Driver enable polarity selection

0: DE signal is active high.
1: DE signal is active low.
This bit can only be written when the USART is disabled (UE=0).

_Note: If the Driver Enable feature is not supported, this bit is reserved and must be kept at_
_reset value. Please refer to Section 28.4: USART implementation on page 950._


Bit 14 **DEM** : Driver enable mode

This bit allows the user to activate the external transceiver control, through the DE signal.

0: DE function is disabled.

1: DE function is enabled. The DE signal is output on the RTS pin.
This bit can only be written when the USART is disabled (UE=0).

_Note: If the Driver Enable feature is not supported, this bit is reserved and must be kept at_
_reset value. Section 28.4: USART implementation on page 950._


Bit 13 **DDRE** : DMA Disable on Reception Error

0: DMA is not disabled in case of reception error. The corresponding error flag is set but
RXNE is kept 0 preventing from overrun. As a consequence, the DMA request is not
asserted, so the erroneous data is not transferred (no DMA request), but next correct
received data will be transferred (used for Smartcard mode).
1: DMA is disabled following a reception error. The corresponding error flag is set, as well as
RXNE. The DMA request is masked until the error flag is cleared. This means that the
software must first disable the DMA request (DMAR = 0) or clear RXNE before clearing the
error flag.
This bit can only be written when the USART is disabled (UE=0).

_Note: The reception errors are: parity error, framing error or noise error._


1000/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


Bit 12 **OVRDIS** : Overrun Disable

This bit is used to disable the receive overrun detection.

0: Overrun Error Flag, ORE, is set when received data is not read before receiving new data.
1: Overrun functionality is disabled. If new data is received while the RXNE flag is still set
the ORE flag is not set and the new received data overwrites the previous content of the
USART_RDR register.
This bit can only be written when the USART is disabled (UE=0).

_Note: This control bit allows checking the communication flow without reading the data._


Bit 11 **ONEBIT** : One sample bit method enable

This bit allows the user to select the sample method. When the one sample bit method is
selected the noise detection flag (NF) is disabled.
0: Three sample bit method
1: One sample bit method
This bit can only be written when the USART is disabled (UE=0).

_Note: ONEBIT feature applies only to data bits, It does not apply to Start bit._


Bit 10 **CTSIE** : CTS interrupt enable

0: Interrupt is inhibited
1: An interrupt is generated whenever CTSIF=1 in the USART_ISR register

_Note: If the hardware flow control feature is not supported, this bit is reserved and must be_
_kept at reset value. Please refer to Section 28.4: USART implementation on page 950._


Bit 9 **CTSE** : CTS enable

0: CTS hardware flow control disabled

1: CTS mode enabled, data is only transmitted when the CTS input is asserted (tied to 0). If
the CTS input is de-asserted while data is being transmitted, then the transmission is
completed before stopping. If data is written into the data register while CTS is de-asserted,
the transmission is postponed until CTS is asserted.
This bit can only be written when the USART is disabled (UE=0)

_Note: If the hardware flow control feature is not supported, this bit is reserved and must be_
_kept at reset value. Please refer to Section 28.4: USART implementation on page 950._


Bit 8 **RTSE** : RTS enable

0: RTS hardware flow control disabled

1: RTS output enabled, data is only requested when there is space in the receive buffer. The
transmission of data is expected to cease after the current character has been transmitted.
The RTS output is asserted (pulled to 0) when data can be received.
This bit can only be written when the USART is disabled (UE=0).

_Note: If the hardware flow control feature is not supported, this bit is reserved and must be_
_kept at reset value. Please refer to Section 28.4: USART implementation on page 950._


Bit 7 **DMAT** : DMA enable transmitter

This bit is set/reset by software

1: DMA mode is enabled for transmission

0: DMA mode is disabled for transmission


Bit 6 **DMAR** : DMA enable receiver

This bit is set/reset by software
1: DMA mode is enabled for reception
0: DMA mode is disabled for reception


RM0364 Rev 4 1001/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


Bit 5 **SCEN** : Smartcard mode enable

This bit is used for enabling Smartcard mode.

0: Smartcard Mode disabled

1: Smartcard Mode enabled

This bit field can only be written when the USART is disabled (UE=0).

_Note: If the USART does not support Smartcard mode, this bit is reserved and must be kept_
_at reset value. Please refer to Section 28.4: USART implementation on page 950._


Bit 4 **NACK** : Smartcard NACK enable

0: NACK transmission in case of parity error is disabled
1: NACK transmission during parity error is enabled
This bit field can only be written when the USART is disabled (UE=0).

_Note: If the USART does not support Smartcard mode, this bit is reserved and must be kept_
_at reset value. Please refer to Section 28.4: USART implementation on page 950._


Bit 3 **HDSEL** : Half-duplex selection

Selection of Single-wire Half-duplex mode
0: Half duplex mode is not selected
1: Half duplex mode is selected
This bit can only be written when the USART is disabled (UE=0).


Bit 2 **IRLP** : IrDA low-power

This bit is used for selecting between normal and low-power IrDA modes

0: Normal mode

1: Low-power mode
This bit can only be written when the USART is disabled (UE=0).

_Note: If IrDA mode is not supported, this bit is reserved and must be kept at reset value._
_Please refer to Section 28.4: USART implementation on page 950._


Bit 1 **IREN** : IrDA mode enable

This bit is set and cleared by software.

0: IrDA disabled

1: IrDA enabled

This bit can only be written when the USART is disabled (UE=0).

_Note: If IrDA mode is not supported, this bit is reserved and must be kept at reset value._
_Please refer to Section 28.4: USART implementation on page 950._


Bit 0 **EIE** : Error interrupt enable

Error Interrupt Enable Bit is required to enable interrupt generation in case of a framing
error, overrun error or noise flag (FE=1 or ORE=1 or NF=1 in the USART_ISR register).
0: Interrupt is inhibited
1: An interrupt is generated when FE=1 or ORE=1 or NF=1 in the USART_ISR register.


1002/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


**28.8.4** **USART baud rate register (USART_BRR)**


This register can only be written when the USART is disabled (UE=0). It may be
automatically updated by hardware in auto baud rate detection mode.


Address offset: 0x0C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:4 **BRR[15:4]**

BRR[15:4] = USARTDIV[15:4]


Bits 3:0 **BRR[3:0]**

When OVER8 = 0, BRR[3:0] = USARTDIV[3:0].

When OVER8 = 1:

BRR[2:0] = USARTDIV[3:0] shifted 1 bit to the right.
BRR[3] must be kept cleared.


**28.8.5** **USART guard time and prescaler register (USART_GTPR)**


Address offset: 0x10


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|GT[7:0]|GT[7:0]|GT[7:0]|GT[7:0]|GT[7:0]|GT[7:0]|GT[7:0]|GT[7:0]|PSC[7:0]|PSC[7:0]|PSC[7:0]|PSC[7:0]|PSC[7:0]|PSC[7:0]|PSC[7:0]|PSC[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



RM0364 Rev 4 1003/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


Bits 31:16 Reserved, must be kept at reset value.


Bits 15:8 **GT[7:0]** : Guard time value

This bit-field is used to program the Guard time value in terms of number of baud clock
periods.
This is used in Smartcard mode. The Transmission Complete flag is set after this guard time
value.

This bit field can only be written when the USART is disabled (UE=0).

_Note: If Smartcard mode is not supported, this bit is reserved and must be kept at reset value._
_Please refer to Section 28.4: USART implementation on page 950._


Bits 7:0 **PSC[7:0]** : Prescaler value

**In IrDA Low-power and normal IrDA mode:**
PSC[7:0] = IrDA Normal and Low-Power Baud Rate
Used for programming the prescaler for dividing the USART source clock to achieve the lowpower frequency:
The source clock is divided by the value given in the register (8 significant bits):
00000000: Reserved - do not program this value
00000001: divides the source clock by 1
00000010: divides the source clock by 2

...

**In Smartcard mode:**

PSC[4:0]: Prescaler value
Used for programming the prescaler for dividing the USART source clock to provide the
Smartcard clock.

The value given in the register (5 significant bits) is multiplied by 2 to give the division factor
of the source clock frequency:
00000: Reserved - do not program this value
00001: divides the source clock by 2
00010: divides the source clock by 4
00011: divides the source clock by 6

...

This bit field can only be written when the USART is disabled (UE=0).

_Note: Bits [7:5] must be kept at reset value if Smartcard mode is used._

_This bit field is reserved and must be kept at reset value when the Smartcard and IrDA_
_modes are not supported. Please refer to Section 28.4: USART implementation on_
_page 950._


**28.8.6** **USART receiver timeout register (USART_RTOR)**


Address offset: 0x14


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24|Col2|Col3|Col4|Col5|Col6|Col7|Col8|23 22 21 20 19 18 17 16|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|BLEN[7:0]|BLEN[7:0]|BLEN[7:0]|BLEN[7:0]|BLEN[7:0]|BLEN[7:0]|BLEN[7:0]|BLEN[7:0]|RTO[23:16]|RTO[23:16]|RTO[23:16]|RTO[23:16]|RTO[23:16]|RTO[23:16]|RTO[23:16]|RTO[23:16]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|RTO[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



1004/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


Bits 31:24 **BLEN[7:0]** : Block Length

This bit-field gives the Block length in Smartcard T=1 Reception. Its value equals the number
of information characters + the length of the Epilogue Field (1-LEC/2-CRC) - 1.
Examples:

BLEN = 0 -> 0 information characters + LEC

BLEN = 1 -> 0 information characters + CRC

BLEN = 255 -> 254 information characters + CRC (total 256 characters))
In Smartcard mode, the Block length counter is reset when TXE=0.
This bit-field can be used also in other modes. In this case, the Block length counter is reset
when RE=0 (receiver disabled) and/or when the EOBCF bit is written to 1.

_Note: This value can be programmed after the start of the block reception (using the data_
_from the LEN character in the Prologue Field). It must be programmed only once per_
_received block._


Bits 23:0 **RTO[23:0]** : Receiver timeout value

This bit-field gives the Receiver timeout value in terms of number of bit duration.
In standard mode, the RTOF flag is set if, after the last received character, no new start bit is
detected for more than the RTO value.

In Smartcard mode, this value is used to implement the CWT and BWT. See Smartcard
section for more details.

In this case, the timeout measurement is done starting from the Start Bit of the last received
character.

_Note: This value must only be programmed once per received character._


_Note:_ _RTOR can be written on the fly. If the new value is lower than or equal to the counter, the_
_RTOF flag is set._


_This register is reserved and forced by hardware to “0x00000000” when the Receiver_
_timeout feature is not supported. Please refer to_ _Section 28.4: USART implementation on_
_page 950_ _._


**28.8.7** **USART request register (USART_RQR)**


Address offset: 0x18


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TXFRQ|RXFRQ|MMRQ|SBKRQ|ABRRQ|
||||||||||||w|w|w|w|w|



RM0364 Rev 4 1005/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


Bits 31:5 Reserved, must be kept at reset value.


Bit 4 **TXFRQ** : Transmit data flush request

Writing 1 to this bit sets the TXE flag.
This allows to discard the transmit data. This bit must be used only in Smartcard mode,
when data has not been sent due to errors (NACK) and the FE flag is active in the
USART_ISR register.
If the USART does not support Smartcard mode, this bit is reserved and must be kept at
reset value. Please refer to _Section 28.4: USART implementation on page 950_ .


Bit 3 **RXFRQ** : Receive data flush request

Writing 1 to this bit clears the RXNE flag.
This allows to discard the received data without reading it, and avoid an overrun condition.


Bit 2 **MMRQ** : Mute mode request

Writing 1 to this bit puts the USART in mute mode and sets the RWU flag.


Bit 1 **SBKRQ** : Send break request

Writing 1 to this bit sets the SBKF flag and request to send a BREAK on the line, as soon as
the transmit machine is available.

_Note: In the case the application needs to send the break character following all previously_
_inserted data, including the ones not yet transmitted, the software should wait for the_
_TXE flag assertion before setting the SBKRQ bit._


Bit 0 **ABRRQ** : Auto baud rate request

Writing 1 to this bit resets the ABRF flag in the USART_ISR and request an automatic baud
rate measurement on the next received data frame.

_Note: If the USART does not support the auto baud rate feature, this bit is reserved and must_
_be kept at reset value. Please refer to Section 28.4: USART implementation on_
_page 950._


**28.8.8** **USART interrupt and status register (USART_ISR)**


Address offset: 0x1C


Reset value: 0x0200 00C0

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|REACK|TEACK|WUF|RWU|SBKF|CMF|BUSY|
||||||||||r|r|r|r|r|r|r|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ABRF|ABRE|Res.|EOBF|RTOF|CTS|CTSIF|LBDF|TXE|TC|RXNE|IDLE|ORE|NF|FE|PE|
|r|r||r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:25 Reserved, must be kept at reset value.


Bits 24:23 Reserved, must be kept at reset value.


1006/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


Bit 22 **REACK** : Receive enable acknowledge flag

This bit is set/reset by hardware, when the Receive Enable value is taken into account by
the USART.

When the wakeup from Stop mode is supported, the REACK flag can be used to verify that
the USART is ready for reception before entering Stop mode.


Bit 21 **TEACK** : Transmit enable acknowledge flag

This bit is set/reset by hardware, when the Transmit Enable value is taken into account by
the USART.

It can be used when an idle frame request is generated by writing TE=0, followed by TE=1
in the USART_CR1 register, in order to respect the TE=0 minimum period.


Bit 20 **WUF** : Wakeup from Stop mode flag

This bit is set by hardware, when a wakeup event is detected. The event is defined by the
WUS bit field. It is cleared by software, writing a 1 to the WUCF in the USART_ICR register.

An interrupt is generated if WUFIE=1 in the USART_CR3 register.

_Note: When UESM is cleared, WUF flag is also cleared._

_The WUF interrupt is active only in Stop mode._

_If the USART does not support the wakeup from Stop feature, this bit is reserved and_
_kept at reset value._


Bit 19 **RWU** : _Receiver wakeup from Mute mode_

This bit indicates if the USART is in mute mode. It is cleared/set by hardware when a
wakeup/mute sequence is recognized. The mute mode control sequence (address or IDLE)
is selected by the WAKE bit in the USART_CR1 register.
When wakeup on IDLE mode is selected, this bit can only be set by software, writing 1 to the
MMRQ bit in the USART_RQR register.

0: Receiver in active mode

1: Receiver in mute mode


Bit 18 **SBKF** : Send break flag

This bit indicates that a send break character was requested. It is set by software, by writing
1 to the SBKRQ bit in the USART_RQR register. It is automatically reset by hardware during
the stop bit of break transmission.

0: No break character is transmitted

1: Break character will be transmitted


Bit 17 **CMF** : Character match flag

This bit is set by hardware, when the character defined by ADD[7:0] is received. It is cleared
by software, writing 1 to the CMCF in the USART_ICR register.
An interrupt is generated if CMIE=1in the USART_CR1 register.

0: No Character match detected

1: Character Match detected


Bit 16 **BUSY** : Busy flag

This bit is set and reset by hardware. It is active when a communication is ongoing on the
RX line (successful start bit detected). It is reset at the end of the reception (successful or
not).
0: USART is idle (no reception)
1: Reception on going


RM0364 Rev 4 1007/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


Bit 15 **ABRF:** Auto baud rate flag

This bit is set by hardware when the automatic baud rate has been set (RXNE will also be
set, generating an interrupt if RXNEIE = 1) or when the auto baud rate operation was
completed without success (ABRE=1) (ABRE, RXNE and FE are also set in this case)
It is cleared by software, in order to request a new auto baud rate detection, by writing 1 to
the ABRRQ in the USART_RQR register.

_Note: If the USART does not support the auto baud rate feature, this bit is reserved and kept_
_at reset value._


Bit 14 **ABRE** : Auto baud rate error

This bit is set by hardware if the baud rate measurement failed (baud rate out of range or
character comparison failed)
It is cleared by software, by writing 1 to the ABRRQ bit in the USART_CR3 register.

_Note: If the USART does not support the auto baud rate feature, this bit is reserved and kept_
_at reset value._


Bit 13 Reserved, must be kept at reset value.


Bit 12 **EOBF** : End of block flag

This bit is set by hardware when a complete block has been received (for example T=1
Smartcard mode). The detection is done when the number of received bytes (from the start
of the block, including the prologue) is equal or greater than BLEN + 4.
An interrupt is generated if the EOBIE=1 in the USART_CR2 register.
It is cleared by software, writing 1 to the EOBCF in the USART_ICR register.

0: End of Block not reached

1: End of Block (number of characters) reached

_Note: If Smartcard mode is not supported, this bit is reserved and kept at reset value. Please_
_refer to Section 28.4: USART implementation on page 950._


Bit 11 **RTOF** : Receiver timeout

This bit is set by hardware when the timeout value, programmed in the RTOR register has
lapsed, without any communication. It is cleared by software, writing 1 to the RTOCF bit in
the USART_ICR register.
An interrupt is generated if RTOIE=1 in the USART_CR1 register.
In Smartcard mode, the timeout corresponds to the CWT or BWT timings.

0: Timeout value not reached

1: Timeout value reached without any data reception

_Note: If a time equal to the value programmed in RTOR register separates 2 characters,_
_RTOF is not set. If this time exceeds this value + 2 sample times (2/16 or 2/8,_
_depending on the oversampling method), RTOF flag is set._

_The counter counts even if RE = 0 but RTOF is set only when RE = 1. If the timeout has_
_already elapsed when RE is set, then RTOF will be set._

_If the USART does not support the Receiver timeout feature, this bit is reserved and_
_kept at reset value._


Bit 10 **CTS** : CTS flag

This bit is set/reset by hardware. It is an inverted copy of the status of the CTS input pin.

0: CTS line set

1: CTS line reset

_Note: If the hardware flow control feature is not supported, this bit is reserved and kept at_
_reset value._


1008/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


Bit 9 **CTSIF** : CTS interrupt flag

This bit is set by hardware when the CTS input toggles, if the CTSE bit is set. It is cleared by
software, by writing 1 to the CTSCF bit in the USART_ICR register.
An interrupt is generated if CTSIE=1 in the USART_CR3 register.
0: No change occurred on the CTS status line
1: A change occurred on the CTS status line

_Note: If the hardware flow control feature is not supported, this bit is reserved and kept at_
_reset value._


Bit 8 **LBDF** : LIN break detection flag

This bit is set by hardware when the LIN break is detected. It is cleared by software, by
writing 1 to the LBDCF in the USART_ICR.
An interrupt is generated if LBDIE = 1 in the USART_CR2 register.

0: LIN Break not detected

1: LIN break detected

_Note: If the USART does not support LIN mode, this bit is reserved and kept at reset value._
_Please refer to Section 28.4: USART implementation on page 950._


Bit 7 **TXE** : Transmit data register empty

This bit is set by hardware when the content of the USART_TDR register has been
transferred into the shift register. It is cleared by a write to the USART_TDR register.
The TXE flag can also be cleared by writing 1 to the TXFRQ in the USART_RQR register, in
order to discard the data (only in Smartcard T=0 mode, in case of transmission failure).
An interrupt is generated if the TXEIE bit =1 in the USART_CR1 register.
0: data is not transferred to the shift register
1: data is transferred to the shift register)

_Note: This bit is used during single buffer transmission._


Bit 6 **TC** : Transmission complete

This bit is set by hardware if the transmission of a frame containing data is complete and if
TXE is set. An interrupt is generated if TCIE=1 in the USART_CR1 register. It is cleared by
software, writing 1 to the TCCF in the USART_ICR register or by a write to the USART_TDR
register.
An interrupt is generated if TCIE=1 in the USART_CR1 register.
0: Transmission is not complete
1: Transmission is complete

_Note: If TE bit is reset and no transmission is on going, the TC bit will be set immediately._


Bit 5 **RXNE** : Read data register not empty

This bit is set by hardware when the content of the RDR shift register has been transferred
to the USART_RDR register. It is cleared by a read to the USART_RDR register. The RXNE
flag can also be cleared by writing 1 to the RXFRQ in the USART_RQR register.
An interrupt is generated if RXNEIE=1 in the USART_CR1 register.

0: data is not received

1: Received data is ready to be read.


RM0364 Rev 4 1009/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


Bit 4 **IDLE** : Idle line detected

This bit is set by hardware when an Idle Line is detected. An interrupt is generated if
IDLEIE=1 in the USART_CR1 register. It is cleared by software, writing 1 to the IDLECF in
the USART_ICR register.

0: No Idle line is detected

1: Idle line is detected

_Note: The IDLE bit will not be set again until the RXNE bit has been set (i.e. a new idle line_
_occurs)._

_If mute mode is enabled (MME=1), IDLE is set if the USART is not mute (RWU=0),_
_whatever the mute mode selected by the WAKE bit. If RWU=1, IDLE is not set._


Bit 3 **ORE** : Overrun error

This bit is set by hardware when the data currently being received in the shift register is
ready to be transferred into the RDR register while RXNE=1. It is cleared by a software,
writing 1 to the ORECF, in the USART_ICR register.
An interrupt is generated if RXNEIE=1 or EIE = 1 in the USART_CR1 register.

0: No overrun error

1: Overrun error is detected

_Note: When this bit is set, the RDR register content is not lost but the shift register is_
_overwritten. An interrupt is generated if the ORE flag is set during multibuffer_
_communication if the EIE bit is set._

_This bit is permanently forced to 0 (no overrun detection) when the OVRDIS bit is set in_
_the USART_CR3 register._


Bit 2 **NF** : START bit Noise detection flag

This bit is set by hardware when noise is detected on a received frame. It is cleared by
software, writing 1 to the NFCF bit in the USART_ICR register.

0: No noise is detected

1: Noise is detected

_Note: This bit does not generate an interrupt as it appears at the same time as the RXNE bit_
_which itself generates an interrupt. An interrupt is generated when the NF flag is set_
_during multibuffer communication if the EIE bit is set._

_Note: When the line is noise-free, the NF flag can be disabled by programming the ONEBIT_
_bit to 1 to increase the USART tolerance to deviations (Refer to Section 28.5.5:_
_Tolerance of the USART receiver to clock deviation on page 966)._


Bit 1 **FE** : Framing error

This bit is set by hardware when a de-synchronization, excessive noise or a break character
is detected. It is cleared by software, writing 1 to the FECF bit in the USART_ICR register.
In Smartcard mode, in transmission, this bit is set when the maximum number of transmit
attempts is reached without success (the card NACKs the data frame).
An interrupt is generated if EIE = 1 in the USART_CR1 register.
0: No Framing error is detected
1: Framing error or break character is detected


Bit 0 **PE** : Parity error

This bit is set by hardware when a parity error occurs in receiver mode. It is cleared by
software, writing 1 to the PECF in the USART_ICR register.
An interrupt is generated if PEIE = 1 in the USART_CR1 register.
0: No parity error
1: Parity error


1010/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


**28.8.9** **USART interrupt flag clear register (USART_ICR)**


Address offset: 0x20


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|WUCF|Res.|Res.|CMCF|Res.|
||||||||||||rc_w1|||rc_w1||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|EOBCF|RTOCF|Res.|CTSCF|LBDCF|Res.|TCCF|Res.|IDLECF|ORECF|NCF|FECF|PECF|
||||rc_w1|rc_w1||rc_w1|rc_w1||rc_w1||rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|



Bits 31:21 Reserved, must be kept at reset value.


Bit 20 **WUCF** : Wakeup from Stop mode clear flag

Writing 1 to this bit clears the WUF flag in the USART_ISR register.

_Note: If the USART does not support the wakeup from Stop feature, this bit is reserved and_
_must be kept at reset value._


Bits 19:18 Reserved, must be kept at reset value.


Bit 17 **CMCF** : Character match clear flag

Writing 1 to this bit clears the CMF flag in the USART_ISR register.


Bits 16:13 Reserved, must be kept at reset value.


Bit 12 **EOBCF** : End of block clear flag

Writing 1 to this bit clears the EOBF flag in the USART_ISR register.

_Note: If the USART does not support Smartcard mode, this bit is reserved and must be kept_
_at reset value. Please refer to Section 28.4: USART implementation on page 950._


Bit 11 **RTOCF** : Receiver timeout clear flag

Writing 1 to this bit clears the RTOF flag in the USART_ISR register.

_Note: If the USART does not support the Receiver timeout feature, this bit is reserved and_
_must be kept at reset value. Please refer to Section 28.4: USART implementation on_
_page 950._


Bit 10 Reserved, must be kept at reset value.


Bit 9 **CTSCF** : CTS clear flag

Writing 1 to this bit clears the CTSIF flag in the USART_ISR register.

_Note: If the hardware flow control feature is not supported, this bit is reserved and must be_
_kept at reset value. Please refer to Section 28.4: USART implementation on page 950._


Bit 8 **LBDCF** : LIN break detection clear flag

Writing 1 to this bit clears the LBDF flag in the USART_ISR register.

_Note: If LIN mode is not supported, this bit is reserved and must be kept at reset value._
_Please refer to Section 28.4: USART implementation on page 950._


Bit 7 Reserved, must be kept at reset value.


Bit 6 **TCCF** : Transmission complete clear flag

Writing 1 to this bit clears the TC flag in the USART_ISR register.


Bit 5 Reserved, must be kept at reset value.


Bit 4 **IDLECF** : Idle line detected clear flag

Writing 1 to this bit clears the IDLE flag in the USART_ISR register.


RM0364 Rev 4 1011/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


Bit 3 **ORECF** : Overrun error clear flag

Writing 1 to this bit clears the ORE flag in the USART_ISR register.


Bit 2 **NCF** : Noise detected clear flag

Writing 1 to this bit clears the NF flag in the USART_ISR register.


Bit 1 **FECF** : Framing error clear flag

Writing 1 to this bit clears the FE flag in the USART_ISR register.


Bit 0 **PECF** : Parity error clear flag

Writing 1 to this bit clears the PE flag in the USART_ISR register.


**28.8.10** **USART receive data register (USART_RDR)**


Address offset: 0x24


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8 7 6 5 4 3 2 1 0|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RDR[8:0]|RDR[8:0]|RDR[8:0]|RDR[8:0]|RDR[8:0]|RDR[8:0]|RDR[8:0]|RDR[8:0]|RDR[8:0]|
||||||||r|r|r|r|r|r|r|r|r|



Bits 31:9 Reserved, must be kept at reset value.


Bits 8:0 **RDR[8:0]** : Receive data value

Contains the received data character.

The RDR register provides the parallel interface between the input shift register and the
internal bus (see _Figure 354_ ).
When receiving with the parity enabled, the value read in the MSB bit is the received parity
bit.


**28.8.11** **USART transmit data register (USART_TDR)**


Address offset: 0x28


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8 7 6 5 4 3 2 1 0|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TDR[8:0]|TDR[8:0]|TDR[8:0]|TDR[8:0]|TDR[8:0]|TDR[8:0]|TDR[8:0]|TDR[8:0]|TDR[8:0]|
||||||||rw|rw|rw|rw|rw|rw|rw|rw|rw|



1012/1124 RM0364 Rev 4


**RM0364** **Universal synchronous/asynchronous receiver transmitter (USART/UART)**


Bits 31:9 Reserved, must be kept at reset value.


Bits 8:0 **TDR[8:0]** : Transmit data value

Contains the data character to be transmitted.

The TDR register provides the parallel interface between the internal bus and the output
shift register (see _Figure 354_ ).
When transmitting with the parity enabled (PCE bit set to 1 in the USART_CR1 register),
the value written in the MSB (bit 7 or bit 8 depending on the data length) has no effect
because it is replaced by the parity.

_Note: This register must be written only when TXE=1._


**28.8.12** **USART register map**


The table below gives the USART register map and reset values.


**Table 143. USART register map and reset values**



















|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**USART_CR1**|Res.|Res.|Res.|M1|EOBIE|RTOIE|DEAT4|DEAT3|DEAT2|DEAT1|DEAT0|DEDT4|DEDT3|DEDT2|DEDT1|DEDT0|OVER8|CMIE|MME|M0|WAKE|PCE|PS|PEIE|TXEIE|TCIE|RXNEIE|IDLEIE|TE|RE|UESM|UE|
|0x00|Reset value||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x04|**USART_CR2**|ADD[7:4]|ADD[7:4]|ADD[7:4]|ADD[7:4]|ADD[3:0]|ADD[3:0]|ADD[3:0]|ADD[3:0]|RTOEN|ABRMOD1|ABRMOD0|ABREN|MSBFIRST|DATAINV|TXINV|RXINV|SWAP|LINEN|STOP<br>[1:0]|STOP<br>[1:0]|CLKEN|CPOL|CPHA|LBCL|Res.|LBDIE|LBDL|ADDM7|Res.|Res.|Res.|Res.|
|0x04|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0||0|0|0|||||
|0x08|**USART_CR3**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|WUFIE|WUS|WUS|SCARCNT2:0]|SCARCNT2:0]|SCARCNT2:0]|Res.|DEP|DEM|DDRE|OVRDIS|ONEBIT|CTSIE|CTSE|RTSE|DMAT|DMAR|SCEN|NACK|HDSEL|IRLP|IREN|EIE|
|0x08|Reset value||||||||||0|0|0|0|0|0||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0C|**USART_BRR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|BRR[15:0]|
|0x0C|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**USART_GTPR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GT[7:0]|GT[7:0]|GT[7:0]|GT[7:0]|GT[7:0]|GT[7:0]|GT[7:0]|GT[7:0]|PSC[7:0]|PSC[7:0]|PSC[7:0]|PSC[7:0]|PSC[7:0]|PSC[7:0]|PSC[7:0]|PSC[7:0]|
|0x10|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x14|**USART_RTOR**|BLEN[7:0]|BLEN[7:0]|BLEN[7:0]|BLEN[7:0]|BLEN[7:0]|BLEN[7:0]|BLEN[7:0]|BLEN[7:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|RTO[23:0]|
|0x14|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x18|**USART_RQR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TXFRQ|RXFRQ|MMRQ|SBKRQ|ABRRQ|
|0x18|Reset value||||||||||||||||||||||||||||0|0|0|0|0|


RM0364 Rev 4 1013/1124



1014


**Universal synchronous/asynchronous receiver transmitter (USART/UART)** **RM0364**


**Table 143. USART register map and reset values (continued)**













|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x1C|**USART_ISR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|REACK|TEACK|WUF|RWU|SBKF|CMF|BUSY|ABRF|ABRE|Res.|EOBF|RTOF|CTS|CTSIF|LBDF|TXE|TC|RXNE|IDLE|ORE|NF|FE|PE|
|0x1C|Reset value||||||||||0|0|0|0|0|0|0|0|0||0|0|0|0|0|1|1|0|0|0|0|0|0|
|0x20|**USART_ICR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|WUCF|Res.|Res.|CMCF|Res.|Res.|Res.|Res.|EOBCF|RTOCF|Res.|CTSCF|LBDCF|Res.|TCCF|Res.|IDLECF|ORECF|NCF|FECF|PECF|
|0x20|Reset value||||||||||||0|||0|||||0|0||0|0||0||0|0|0|0|0|
|0x24|**USART_RDR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RDR[8:0]|RDR[8:0]|RDR[8:0]|RDR[8:0]|RDR[8:0]|RDR[8:0]|RDR[8:0]|RDR[8:0]|RDR[8:0]|
|0x24|Reset value||||||||||||||||||||||||X|X|X|X|X|X|X|X|X|
|0x28|**USART_TDR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TDR[8:0]|TDR[8:0]|TDR[8:0]|TDR[8:0]|TDR[8:0]|TDR[8:0]|TDR[8:0]|TDR[8:0]|TDR[8:0]|
|0x28|Reset value||||||||||||||||||||||||X|X|X|X|X|X|X|X|X|


Refer to _Section 2.2 on page 47_ for the register boundary addresses.


1014/1124 RM0364 Rev 4


