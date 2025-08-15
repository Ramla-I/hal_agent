**RM0490** **FD controller area network (FDCAN)**

# **28 FD controller area network (FDCAN)**


This section applies to STM32C092xx devices only.

## **28.1 Introduction**


The controller area network (CAN) subsystem (see _Figure 316_ ) consists of one CAN
module, a shared message RAM, and a configuration block. Refer to the memory map for
the base address of each of these parts.


The modules (FDCAN) are compliant with ISO 11898-1: 2015 (CAN protocol specification
version 2.0 part A, B) and CAN FD protocol specification version 1.0.


A 0.8-Kbyte message RAM per FDCAN instance is used for filtering, transmitting event
FIFOs, and receiving and transmitting FIFOs.


RM0490 Rev 5 887/1027



952


**FD controller area network (FDCAN)** **RM0490**


**Figure 316. CAN subsystem.**






|Configuration<br>PDIV[3:0]<br>/ 1..30<br>Subsystem CKDIV<br>Configuration<br>fdcan_tq_ck<br>register|Col2|
|---|---|
|**/ 1..30**<br>CKDIV<br>**Subsystem**<br>**Configuration**<br>**register**<br>fdcan_tq_ck<br>**Configuration**<br>PDIV[3:0]|**Subsystem**<br>**Configuration**<br>**register**|
|||








|Col1|Col2|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
||||Sync|Sync||
||||Tx State|Tx State|Tx State|
|**TX Handler**<br>TX prioritizati<br>Frame synchroni|**TX Handler**<br>TX prioritizati<br>Frame synchroni|**TX Handler**<br>TX prioritizati<br>Frame synchroni|**TX Handler**<br>TX prioritizati<br>Frame synchroni|**TX Handler**<br>TX prioritizati<br>Frame synchroni|on<br>zation|
|**TX Handler**<br>TX prioritizati<br>Frame synchroni|**TX Handler**<br>TX prioritizati<br>Frame synchroni|**TX Handler**<br>TX prioritizati<br>Frame synchroni|**TX Handler**<br>TX prioritizati<br>Frame synchroni|||
|**RX Ha**<br>Accepta|**RX Ha**<br>Accepta|**RX Ha**<br>Accepta|**RX Ha**<br>Accepta|**ndler**<br>nce filter|**ndler**<br>nce filter|


|Col1|Interrupts<br>interface<br>CAN core<br>Sync<br>Sync<br>Control and<br>Configuration Tx Req Tx State Rx State<br>registers<br>TX Handler<br>TX prioritization<br>Frame synchronization<br>RX Handler<br>Message RAM<br>interface<br>Acceptance filter<br>CANFDL|
|---|---|
|||
|||
|||
|||
|||









888/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**

## **28.2 FDCAN main features**


      - Conform with CAN protocol version 2.0 part A, B, and ISO 11898-1: 2015


      - CAN FD with maximum 64 data bytes supported


      - CAN error logging


      - AUTOSAR and J1939 support


      - Improved acceptance filtering


      - Two receive FIFOs of three payloads each (up to 64 bytes per payload)


      - Separate signaling on reception of high priority messages


      - Configurable transmit FIFO/queue of three payloads (up to 64 bytes per payload)


      - Transmit event FIFO


      - Programmable loop-back test mode


      - Maskable module interrupts


      - Two clock domains: APB bus interface and CAN core kernel clock


      - Power-down support


RM0490 Rev 5 889/1027



952


**FD controller area network (FDCAN)** **RM0490**

## **28.3 FDCAN functional description**



**28.3.1** **FDCAN block diagram**


**Figure 317. FDCAN block diagram**












|Col1|Col2|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
||||Sync|Sync||
||||Tx State|Tx State|Tx State|
|**TX Handler**<br>TX prioritizati<br>Frame Synch|**TX Handler**<br>TX prioritizati<br>Frame Synch|**TX Handler**<br>TX prioritizati<br>Frame Synch|**TX Handler**<br>TX prioritizati<br>Frame Synch|**TX Handler**<br>TX prioritizati<br>Frame Synch|on<br>ro|
|**TX Handler**<br>TX prioritizati<br>Frame Synch|**TX Handler**<br>TX prioritizati<br>Frame Synch|**TX Handler**<br>TX prioritizati<br>Frame Synch|**TX Handler**<br>TX prioritizati<br>Frame Synch|||
|**RX Ha**<br>Accepta|**RX Ha**<br>Accepta|**RX Ha**<br>Accepta|**RX Ha**<br>Accepta|**ndler**<br>nce filter|**ndler**<br>nce filter|







**Dual interrupt lines**


The FDCAN peripheral provides two interrupt lines, fdcan_intr0_it and fdcan_intr1_it.


By programming the EINT0 and EINT1 bits of the FDCAN_ILE register, the interrupt lines
can be independently enabled or disabled.


**CAN core**


The CAN core contains the protocol controller and receive/transmit shift registers. It handles
all ISO 11898-1: 2015 protocol functions and supports both 11-bit and 29-bit identifiers.


**Sync**



This block synchronizes signals from the APB clock domain to the CAN kernel clock domain
and vice versa.


890/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**Tx handler**


The Tx handler controls the message transfer from the message RAM to the CAN core. A
maximum of three Tx buffers is available for transmission. The Tx buffer can be used as Tx
FIFO or as a Tx queue. Tx event FIFO stores Tx timestamps together with the
corresponding message ID. Transmit cancellation is also supported.


**Rx handler**


The Rx handler controls the transfer of received messages from the CAN core to the
external message RAM. The Rx handler supports two receive FIFOs, for storage of all
messages that have passed acceptance filtering. An Rx timestamp is stored together with
each message. Up to 28 filters can be defined for 11-bit IDs; up to eight filters for 29-bit IDs.


**APB interface**


The APB interface connects the FDCAN to the APB bus for configuration registers,
controller configuration, and RAM access.


**Message RAM interface**


The message RAM interface connects the FDCAN access to an external 1-Kbyte message
RAM through a RAM controller/arbiter.


**28.3.2** **FDCAN pins and internal signals**


The CAN subsystem I/O signals and pins are detailed, respectively, in _Table 139_, _Table 140_,
and _Figure 316_ .


**Table 139. CAN subsystem I/O signals**

|Name|Type|Description|
|---|---|---|
|fdcan_ker_ck|Digital input|CAN subsystem kernel clock input|
|fdcan_pclk|fdcan_pclk|CAN subsystem APB interface clock input|
|fdcan_intr0_it|Digital output|FDCAN interrupt0|
|fdcan_intr1_it|fdcan_intr1_it|FDCAN interrupt1|
|fdcan_ts[0:15]|-|External timestamp vector|
|APB interface|Digital input/output|Single APP with multiple psel for configuration, control<br>and RAM access|



**Table 140. CAN subsystem I/O pins**

|Name|Type|Description|
|---|---|---|
|FDCAN_RX|Digital input|FDCAN receive pin|
|FDCAN_TX|Digital output|FDCAN transmit pin|



RM0490 Rev 5 891/1027



952


**FD controller area network (FDCAN)** **RM0490**


**28.3.3** **Bit timing**


The bit timing logic monitors the serial bus-line and performs sampling and adjustment of
the sample point by synchronizing on the start-bit edge and resynchronizing on the following
edges.


As shown in _Figure 318_, this operation can be explained simply by splitting the bit time in
three segments, as follows:


      - Synchronization segment (SYNC_SEG): a bit change is expected to occur within this
time segment, having a fixed length of one time quantum (1 × t q ).

      - Bit segment 1 (BS1): defines the location of the sample point. It includes the
PROP_SEG and PHASE_SEG1 of the CAN standard. Its duration is programmable
from 1 to 16 time quanta, but can be automatically lengthened to compensate for
positive phase drifts due to differences in the frequency of various nodes of the
network.


      - Bit segment 2 (BS2): defines the location of the transmit point. It represents the
PHASE_SEG2 of the CAN standard, its duration is programmable between one and
eight time quanta, but can also be automatically shortened to compensate for negative
phase drifts.


**Figure 318. Bit timing**

|SyncSeg|Bit segment 1 (BS1)|Bit segment 2 (BS2)|
|---|---|---|
||||



The baud rate is the inverse of the bit time (baud rate = 1 / bit time), which, in turn, is the
sum of three components (see _Figure 318_ ):


bit time = t SyncSeg + t BS1 + t BS2

Where:


– For the nominal bit time


t q = (NBRP[8:0] + 1) × t fdcan_tq_clk
t SyncSeg = 1 × t q
t BS1 = t q × (NTSEG1[7:0] + 1)

t BS2 = t q × (NTSEG2[6:0] + 1)

Where NBRP[8:0], NTSEG1[7:0], and NTSEG2[6:0] bitfields belong to the
FDCAN_NBTP register.


– For the data bit time


t q = (DBRP[4:0] + 1) × t fdcan_tq_clk
t SyncSeg = 1 × t q
t BS1 = t q × (DTSEG1[4:0] + 1)

t BS2 = t q × (DTSEG2[3:0] + 1)


892/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


Where DBRP[4:0], DTSEG1[4:0], and DTSEG2[3:0] belong to the FDCAN_DBTP
register.


The (re)synchronization jump width (SJW) defines an upper bound for the amount of
lengthening or shortening of the bit segments. It is programmable between one and four
time quanta.


A valid edge is defined as the first transition in a bit time from dominant to recessive bus
level, provided the controller itself does not send a recessive bit.


If a valid edge is detected in BS1 instead of SYNC_SEG, BS1 is extended by up to SJW, so
that the sample point is delayed.


Conversely, if a valid edge is detected in BS2 instead of SYNC_SEG, BS2 is shortened by
up to SJW, so that the transmit point is moved earlier.


As a safeguard against programming errors, the configuration of the bit timing register is
only possible while the device is in Standby mode. The FDCAN_DBTP and FDCAN_NBTP
registers (dedicated, respectively, to data and nominal bit timing) are only accessible when
the CCE and INIT of the FDCA_CCCR register are set.


The FDCAN requires that the CAN time quanta clock is always below or equal to the APB
clock (f dcan_tq_ck < f dcan_pclk ).


_Note:_ _For a detailed description of the CAN bit timing and resynchronization mechanism, refer to_
_the ISO 11898-1 standard._


**28.3.4** **Operating modes**


**Configuration**


Access to peripheral version, hardware, and input clock divider configuration. When the
clock divider is set to 0, the primary input clock is used as it is.


**Software initialization**


Software initialization is started by setting the INIT bit of the FDCAN_CCCR register, by
software, by a hardware reset, or by entering bus-off state. While the INIT bit is set,
message transfers from and to the CAN bus are stopped, and the status of the CAN bus
output FDCAN_TX is recessive (high). The EML (error management logic) counters are
unchanged. Setting the INIT bit does not change any configuration register. Clearing INIT bit
of FDCAN_CCCR finishes the software initialization. Afterwards the bit stream processor
(BSP) synchronizes itself to the data transfer on the CAN bus by waiting for the occurrence
of a sequence of 11 consecutive recessive bits (bus-idle) before it can take part in bus
activities and start the message transfer.


Access to the FDCAN configuration registers is only enabled when the INIT bit and the CCE
bit of the FDCAN_CCCR register are both set.


The CCE bit of the FDCAN_CCCR register can only be set/cleared while the INIT bit of
FDCAN_CCCR is set. The CCE bit is automatically cleared when the INIT bit is cleared.


RM0490 Rev 5 893/1027



952


**FD controller area network (FDCAN)** **RM0490**


The following registers are reset when the CCE bit of the FDCAN_CCCR register is set:


      - FDCAN_HPMS: High priority message status


      - FDCAN_RXF0S: Rx FIFO 0 status


      - FDCAN_RXF1S: Rx FIFO 1 status


      - FDCAN_TXFQS: Tx FIFO/queue status


      - FDCAN_TXBRP: Tx buffer request pending


      - FDCAN_TXBTO: Tx buffer transmission occurred


      - FDCAN_TXBCF: Tx buffer cancellation finished


      - FDCAN_TXEFS: Tx event FIFO status


The timeout counter value (TOC[15:0] bit of the FDCAN_TOCV register) is preset to the
value configured by the TOP[15:0] of the FDCAN_TOCC register when the CCE bit of the
FDCAN_CCCR is set.


In addition, the state machines of the Tx handler and Rx handler are held in idle state while
the CCE bit is set.


The following registers can be written only when the CCE bit is cleared:


      - FDCAN_TXBAR: Tx buffer add request


      - FDCAN_TXBCR: Tx buffer cancellation request


The TEST and the MON bits of the FDCAN_CCCR register can be set only by software
while the INIT and the CCE bits of the FDCAN_CCCR register are both set. Both bits can be
reset at any time. The DAR bit of FDCAN_CCCR can only be set/cleared while the INIT and
CCE bits are both set.


**Normal operation**


The FDCAN default operating mode after hardware reset is event-driven CAN
communication. TT operation mode is not supported.


Once the FDCAN is initialized and the INIT bit of the FDCAN_CCCR register is cleared, the
FDCAN synchronizes itself to the CAN bus and is ready for communication.


After passing the acceptance filtering, received messages including message ID and DLC
are stored into the Rx FIFO 0 or Rx FIFO 1.


For messages to be transmitted, the Tx FIFO or the Tx queue can be initialized or updated.
Automated transmission on reception of remote frames is not supported.


**CAN FD operation**


There are two variants in the FDCAN protocol:


      - Long frame mode (LFM), where the data field of a CAN frame may be longer than eight
bytes.


      - Fast frame mode (FFM), where the control field, data field, and CRC field of a CAN
frame are transmitted with a higher bit rate compared to the beginning and to the end of
the frame.


The fast frame mode can be used in combination with the long frame mode.


The previously reserved bit in CAN frames with 11-bit identifiers and the first previously
reserved bit in CAN frames with 29-bit identifiers are decoded as FDF bit: FDF recessive
signifies a CAN FD frame, while FDF dominant signifies a classic CAN frame.


894/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


In a CAN FD frame, the two bits following FDF (res and BRS) decide whether the bit rate
inside this CAN FD frame is switched. A CAN FD bit rate switch is signified by res dominant
and BRS recessive. The coding of res recessive is reserved for future expansion of the
protocol. In case the FDCAN receives a frame with FDF recessive and res recessive, it
signals a protocol exception event by setting the PXE bit of the FDCAN_PSR register. When
protocol exception handling is enabled (PXHD = 0 in FDCAN_CCCR), this causes the
operation state to change from receiver (ACT[1:0] = 10 in FDCAN_PSR) to integrating
(ACT[1:0] = 00 in FDCAN_PSR) at the next sample point. If protocol exception handling is
disabled (PXHD = 1 in FDCAN_CCCR), the FDCAN treats a recessive res bit as a form
error and responds with an error frame.


CAN FD operation is enabled by programming the FDOE bit of the FDCAN_CCCR register.
In case FDOE = 1, transmission and reception of CAN FD frames are enabled.
Transmission and reception of classic CAN frames are always possible. Whether a CAN FD
frame or a classic CAN frame is transmitted can be configured via the FDF bit in the
respective Tx buffer element. With FDOE = 0, received frames are interpreted as classic
CAN frames, which leads to the transmission of an error frame when receiving a CAN FD
frame. When CAN FD operation is disabled, no CAN FD frames are transmitted even if the
FDF bit of a Tx buffer element is set. The FDOE and BRSE bits of the FDCAN_CCCR
register can only be changed while the INIT and CCE bits are both set.


With FDOE = 0, the setting of the FDF and BRS bits is ignored, and frames are transmitted
in classic CAN format. With FDOE = 1 and BRSE = 0, only the FDF bit of a Tx buffer
element is evaluated. With FDOE = 1 and BRSE = 1, transmission of CAN FD frames with
bit rate switching is enabled. All Tx buffer elements with FDF and BRS bits set are
transmitted in CAN FD format with bit rate switching.


A mode change during CAN operation is recommended only under the following conditions:


      - The failure rate in the CAN FD data phase is significant higher than in the CAN FD
arbitration phase. In this case, disable the CAN FD bit rate switching option for
transmissions.


      - During system startup, all nodes transmit classic CAN messages until it is verified that
they are able to communicate in CAN FD format. If this is true, all nodes switch to CAN
FD operation.


      - Wake-up messages in CAN partial networking have to be transmitted in classic CAN
format.


      - End-of-line programming in case not all nodes are CAN FD capable. Non-CAN FD
nodes are held in silent mode until programming is complete. Then all nodes switch
back to classic CAN communication.


In the FDCAN format, the coding of the DLC differs from that of the standard CAN format.
The DLC codes 0 to 8 have the same coding as in standard CAN, the codes 9 to 15 (that in
standard CAN all code a data field of 8 bytes) are coded according to _Table 141_ .


: **Table 141. DLC coding in FDCAN**

|DLC|9|10|11|12|13|14|15|
|---|---|---|---|---|---|---|---|
|Number of data bytes|12|16|20|24|32|48|64|



In CAN FD fast frames, the bit timing is switched inside the frame, after the BRS (bit rate
switch) bit, if this bit is recessive. Before the BRS bit, in the FDCAN arbitration phase, the
standard CAN bit timing is used as defined by the FDCAN_DBTP register. In the following


RM0490 Rev 5 895/1027



952


**FD controller area network (FDCAN)** **RM0490**


FDCAN data phase, the fast CAN bit timing is used as defined by the FDCAN_DBTP
register. The bit timing is switched back from the fast timing at the CRC delimiter or when an
error is detected, whichever occurs first.


The maximum configurable bit rate in the CAN FD data phase depends on the FDCAN
kernel clock frequency. For example, with an FDCAN kernel clock frequency of 20 MHz and
the shortest configurable bit time of four time quanta (t q ), the bit rate in the data phase is
5 Mbit/s.


In both data frame formats (CAN FD long frames and CAN FD fast frames), the value of bit
ESI (error status indicator) is determined by the transmitter error state at the start of the
transmission. If the transmitter is error passive, ESI is transmitted recessive, else it is
transmitted dominant. In CAN FD remote frames, the ESI bit is always transmitted
dominant, independent of the transmitter error state. The data length code of CAN FD
remote frames is transmitted as 0.


In case an FDCAN Tx buffer is configured for FDCAN transmission with DLC > 8, the first
eight bytes are transmitted as configured in the Tx buffer while the remaining part of the
data field is padded with 0xCC. When the FDCAN receives a FDCAN frame with DLC > 8,
the first eight bytes of that frame are stored into the matching Rx FIFO. The remaining bytes
are discarded.


**Transceiver delay compensation**


During the data phase of an FDCAN transmission, only one node is transmitting, all others
are receivers. The length of the bus line has no impact. When transmitting via pin
FDCAN_TX, the protocol controller receives the transmitted data from its local CAN
transceiver via pin FDCAN_RX. The received data is delayed by the CAN transceiver loop
delay. If this delay is greater than TSEG1 (time segment before sample point), and a bit
error is detected. Without transceiver delay compensation, the bit rate in the data phase of
an FDCAN frame is limited by the transceiver loop delay.


The FDCAN implements a delay compensation mechanism to compensate the CAN
transceiver loop delay, thereby enabling transmission with higher bit rates during the
FDCAN data phase independent of the delay of a specific CAN transceiver.


To check for bit errors during the data phase of transmitting nodes, the delayed transmit
data is compared against the received data at the secondary sample point (SSP). If a bit
error is detected, the transmitter reacts on this bit error at the next following regular sample
point. During the arbitration phase, the delay compensation is always disabled.


The transmitter delay compensation enables configurations where the data bit time is
shorter than the transmitter delay. This is enabled by setting the TDC bit of the
FDCAN_DBTP register, and described in detail in the ISO11898-1 specification.


The received bit is compared against the transmitted bit at the SSP. The SSP position is
defined as the sum of the measured delay from the FDCAN transmit output pin FDCAN_TX
through the transceiver to the receive input pin FDCAN_RX plus the transmitter delay
compensation offset as configured by TDCO[6:0] of FDCAN_TDCR. The transmitter delay
compensation offset is used to adjust the position of the SSP inside the received bit (for
example, half of the bit time in the data phase). The position of the secondary sample point
is rounded down to the next integer number of mt q (minimum time quantum, one period of
fdcan_tq_ck clock).


The TDCV[6:0] bitfield of the FDCAN_PSR register shows the actual transmitter delay
compensation value. TDCV[6:0] is cleared when the INIT is set in the FDCAN_CCCR. It is


896/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


updated at each transmission of an FD frame while the TDC bit of the FDCAN_DBTP
register is set.



The following boundary conditions have to be considered for the transmitter delay
compensation implemented in the FDCAN:


- The sum of the measured delay from FDCAN_Tx to FDCAN_Rx and the configured
transmitter delay compensation offset TDCO[6:0] has to be lower than 6-bit times in the
data phase.


- The sum of the measured delay from FDCAN_TX to FDCAN_RX and the configured
transmitter delay compensation offset TDCO[6:0] has to be lower than or equal to
127 × mt q . If the sum exceeds this value, the maximum value (127 × mt q ) is used for
transmitter delay compensation.


- The data phase ends at the sample point of the CRC delimiter, which stops checking
received bits at the SSPs.



If transmitter delay compensation is enabled by setting the TDC bit of the FDCAN_DBTP;
the measurement is started within each transmitted CAN FD frame at the falling edge of bit
FDF to bit res. The measurement is stopped when this edge is seen at the receive input pin
FDCAN_TX of the transmitter. The resolution of this measurement is one mt q .


**Figure 319. Transceiver delay measurement**



























To avoid that a dominant glitch inside the received FDF bit ends the delay compensation
measurement before the falling edge of the received res bit (resulting in a too early SSP
position), the use of a transmitter delay compensation filter window can be enabled by
programming the TDCF[6:0] bitfield of the FDCAN_TDCR register. This defines a minimum
value for the SSP position. Dominant edges on FDCAN_RX that would result in an earlier
SSP position are ignored for transmitter delay measurement. The measurement is stopped
when the SSP position is at least TDCF[6:0] and FDCAN_RX is low.


RM0490 Rev 5 897/1027



952


**FD controller area network (FDCAN)** **RM0490**


**Restricted operation mode**


In restricted operation mode, the node is able to receive data and remote frames, and to
give acknowledge to valid frames, but it does not send data frames, remote frames, active
error frames, or overload frames. In case of an error condition or overload condition, it does
not send dominant bits. Instead, it waits for the occurrence of a bus-idle condition to
resynchronize itself to the CAN communication. The error counters (REC[6:0] and TEC[7:0]
in FDCAN_ECR) are frozen while the error logging (CEL[7:0]) is active. The software can
set the FDCAN into restricted operation mode by setting the ASM bit of FDCAN_CCCR. The
bit can only be set by software when both CCE and INIT bits are set in FDCAN_CCCR. The
bit can be cleared by software at any time.


Restricted operation mode is automatically entered when the Tx handler is not able to read
data from the message RAM in time. To leave restricted operation mode, the software has to
clear the ASM bit of FDCAN_CCCR.


The restricted operation mode can be used in applications that adapt themselves to different
CAN bit rates. In this case, the application tests different bit rates and leaves the restricted
operation mode after it has received a valid frame.


_Note:_ _The restricted operation mode must not be combined with the loop-back mode (internal or_
_external)._


**Bus monitoring mode**


The FDCAN is set in bus monitoring mode by setting the MON bit of the FDCAN_CCCR
register. In bus monitoring mode (for more details refer to ISO11898-1, 10.12 bus
monitoring), the FDCAN is able to receive valid data frames and valid remote frames, but
cannot start a transmission. In this mode, it sends only recessive bits on the CAN bus. If the
FDCAN is required to send a dominant bit (ACK bit, overload flag, active error flag), the bit is
rerouted internally so that the FDCAN can monitor it, even if the CAN bus remains in
recessive state. In bus monitoring mode, the FDCAN_TXBRP register is held in reset state.


The bus monitoring mode can be used to analyze the traffic on a CAN bus without affecting
it by the transmission of dominant bits. _Figure 320_ shows the connection of FDCAN_TX and
FDCAN_RX signals to the FDCAN in bus monitoring mode.


**Figure 320. Pin control in bus monitoring mode**


898/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**Disabled automatic retransmission mode (DAR)**


According to the CAN specification (see ISO11898-1, 6.3.3 Recovery Management), the
FDCAN provides means for automatic retransmission of frames that have lost arbitration or
have been disturbed by errors during transmission. By default, automatic retransmission is
enabled. The DAR mode can be disabled through the DAR bit of the FDCAN_CCCR
register.


**Frame transmission in DAR mode**


In DAR mode, all transmissions are automatically canceled after they have been started on
the CAN bus. A Tx buffer Tx request pending bit (TRPx in FDCAN_TXBRP) is reset after
successful transmission, when a transmission has not yet been started at the point of
cancellation, when it has been aborted due to lost arbitration, or when an error has occurred
during frame transmission.


      - Successful transmission


–
The corresponding Tx buffer transmission occurred bit TOx is set in
FDCAN_TXBTO register.


–
The corresponding Tx buffer cancellation finished bit CFx is cleared in the
FDCAN_TXBCF register.


      - Successful transmission in spite of cancellation


–
The corresponding Tx buffer transmission occurred bit TOx is set in the
FDCAN_TXBTO register.


–
The corresponding Tx buffer cancellation finished bit CFx is set in the
FDCAN_TXBCF register.


      - Arbitration loss or frame transmission disturbed


–
The corresponding Tx buffer transmission occurred bit TOx is cleared in the
FDCAN_TXBTO register.


–
The corresponding Tx buffer cancellation finished bit CFx is set in the
FDCAN_TXBCF register.


In case of a successful frame transmission, and if the storage of Tx events is enabled, a Tx
event FIFO element is written with event type ET = 10 (transmission in spite of cancellation).


**Power-down (Sleep mode)**


**Power-down entry**


The FDCAN can be set into power-down mode controlled by setting the CSR bit of the
FDCAN_CCCR register. As long as the clock stop request is active, CSR is read as 1.


When all pending transmission requests have completed, the FDCAN waits until the busidle state is detected. The FDCAN then sets the INIT bit of the FDCAN_CCCR register to
prevent any further CAN transfers. Now, the FDCAN acknowledges that it is ready for
power-down by setting the CSA bit of the FDCAN_CCCR register. In this state, before the
clocks are switched off, further register accesses can be made. A write access to the INIT
bit has no effect. Now, the module clock inputs can be switched off.


**Power-down exit**


To leave power-down mode, the application has to turn on the module clocks before clearing
the CSR bit. The FDCAN acknowledges this by clearing the CSA bit. Afterwards, the
application can restart CAN communication by clearing the INIT bit.


RM0490 Rev 5 899/1027



952


**FD controller area network (FDCAN)** **RM0490**


**Test modes**


To enable write access to _FDCAN test register (FDCAN_TEST)_, the TEST bit of the
FDCAN_CCCR register must be set, thus enabling the configuration of test modes and
functions.


Four output functions are available for the CAN transmit pin FDCAN_TX by programming
the TX[1:0] bitfield of the FDCAN_TEST register. In addition to its default function (the serial
data output), it can drive the CAN sample point signal to monitor the FDCAN bit timing as
well as drive constant dominant or recessive values. The actual value at pin FDCAN_RX
can be read from the RX bit of FDCAN_TEST. Both functions can be used to check the CAN
bus physical layer.


Due to the synchronization mechanism between CAN kernel clock and APB clock domain,
there can be a delay of several APB clock periods between writing to TX[1:0] until the new
configuration is visible at FDCAN_TX output pin. This applies also when reading
FDCAN_RX input pin via RX.


_Note:_ _Test modes must be used for production tests or self-test only. The software control for_
_FDCAN_TX pin interferes with all CAN protocol functions. It is not recommended to use test_
_modes for application._


**External loop-back mode**


The FDCAN can be set in external loop-back mode by setting the LBCK bit of the
FDCAN_TEST register. In loop-back mode, the FDCAN treats its own transmitted
messages as received messages and stores them (if they pass acceptance filtering) into Rx
FIFOs. _Figure 321_ shows the connection of transmit and receive signals FDCAN_TX and
FDCAN_RX to the FDCAN in external loop-back mode.


This mode is provided for hardware self-test. To be independent from external stimulation,
the FDCAN ignores acknowledge errors (recessive bit sampled in the acknowledge slot of a
data/remote frame) in loop-back mode. In this mode, the FDCAN performs an internal
feedback from its transmit output to its receive input. The actual value of the FDCAN_RX
input pin is disregarded by the FDCAN. The transmitted messages can be monitored at the
FDCAN_TX transmit pin.


**Internal loop-back mode**


Internal loop-back mode is entered by setting both the LBCK bit of FDCAN_TEST and the
MON bit of FDCAN_CCR. This mode can be used for a “hot self-test”, meaning the FDCAN
can be tested without affecting a running CAN system connected to the FDCAN_TX and
FDCAN_RX pins. In this mode, FDCAN_RX pin is disconnected from the FDCAN and
FDCAN_TX pin is held recessive. _Figure 321_ shows the connection of FDCAN_TX and
FDCAN_RX pins to the FDCAN in case of internal loop-back mode.


900/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**Figure 321. Pin control in loop-back mode**



**Timestamp generation**









For timestamp generation, the FDCAN supplies a 16-bit wrap-around counter. A prescaler
(TCP[3:0] of FDCAN_TSCC) can be configured to clock the counter in multiples of CAN bit
times (1 to 16). The counter is readable via the TCV[15:0] bitfield of the FDCAN_TSCV
register. A write access to TSCV15:0] resets the counter to 0. When the timestamp counter
wraps around, the interrupt flag (TSW bit of FDCAN_ISR) is set.


On start of frame reception/transmission, the counter value is captured and stored into the
timestamp section of an Rx FIFO (RXTS[15:0]) or Tx event FIFO (TXTS[15:0]) element.


By programming TSS[1:0] of FDCAN_TSCC, a 16-bit timestamp can be used.


**Debug mode behavior**


In debug mode, the set/reset on read feature is automatically disabled during the debugger
register access, and enabled during normal MCU operation


**Timeout counter**


To signal timeout conditions for Rx FIFO 0, Rx FIFO 1, and the Tx event FIFO the FDCAN
supplies a 16-bit timeout counter. It operates as a down-counter and uses the same
prescaler controlled by TCP[3:0] of FDCAN_TSCC as the timestamp counter. The timeout
counter is configured via the FDCAN_TOCC register. The actual counter value can be read
from the TOC[15:0] bitfield of FDCAN_TOCV. The timeout counter can only be started while
the INIT bit of FDCAN_CCCR is cleared. It is stopped when INIT is set, for example, when
the FDCAN enters bus-off state.


The operation mode is selected by TOS[1:0] of FDCAN_TOCC. When operating in
continuous mode, the counter starts when INIT is cleared. A write to FDCAN_TOCV presets
the counter to the value configured by TOP[15:0] in FDCAN_TOCC and continues downcounting.


When the timeout counter is controlled by one of the FIFOs, an empty FIFO presets the
counter to the value configured by TOP[15:0]. Down-counting is started when the first FIFO
element is stored. Writing to FDCAN_TOCV has no effect.


RM0490 Rev 5 901/1027



952


**FD controller area network (FDCAN)** **RM0490**


When the counter reaches 0, the TOO interrupt flag is set in the FDCAN_IR register. In
continuous mode, the counter is immediately restarted at TOP[15:0].


_Note:_ _The clock signal for the timeout counter is derived from the CAN core sample point signal._
_Therefore, the point in time where the timeout counter is decremented may vary due to the_
_synchronization/resynchronization mechanism of the CAN core. If the baud rate switch_
_feature in FDCAN is used, the timeout counter is clocked differently in the arbitration and_
_data fields._


**28.3.5** **Error management**


As described in the CAN protocol, the error management is handled entirely by hardware
using the transmit error counter (the TEC[7:0] bitfield of the _FDCAN error counter register_
_(FDCAN_ECR)_ ) and the receive error counter (the REC[6:0] bitfield of the _FDCAN error_
_counter register (FDCAN_ECR)_ ). These values are incremented or decremented according
to the error condition. For detailed information on TEC[7:0] and REC[6:0] management,
refer to the CAN standard. Both values can be read by software to determine the stability of
the network.


The bus-off state is reached when TEC[7:0] is greater than 255. This state is also indicated
by the BO flag of the _FDCAN protocol status register (FDCAN_PSR)_ . In bus-off state, the
CAN is no longer able to transmit and receive messages. It has to wait at least for the
duration of the recovery sequence specified in the CAN standard (128 occurrences of 11
consecutive recessive bits monitored on FDCAN_RX input).







_Note:_ _In initialization mode, the CAN does not monitor the_ FDCAN_RX _signal, and therefore_
_cannot complete the recovery sequence. To recover from an error state, the CAN must_
_operate in normal mode._


902/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**28.3.6** **Message RAM**


The message RAM is 32-bit wide, and the FDCAN module is configured to allocate up to
212 words in it. It is not necessary to configure each of the sections shown in _Figure 323_ .


**Figure 323. Message RAM configuration**































When the FDCAN addresses the message RAM, it addresses 32-bit words (aligned), not a
single byte. The RAM addresses are 32-bit words, that is, only bits 15 to 2 are evaluated,
the two least significant bits are ignored.


In case of multiple instances, the RAM start address for the FDCANn is computed by end
address + 4 of FDCANn - 1, and the FDCANn end address is computed by FDCANn start
address + 0x0350 - 4.


As an example, for two instances:


- FDCAN1:


– Start address 0x0000


–
End address 0x034C (as in _Figure 323_ )


- FDCAN2:


–
Start address = 0x034C (FDCAN1 end address) + 4 = 0x0350


–
End address = 0x0350 (FDCAN2 start address) + 0x0350 - 4 = 0x069C.


**Rx handling**


The Rx handler controls the acceptance filtering, the transfer of received messages to one
of the two Rx FIFOs, as well as the Rx FIFO put and get indices.


**Acceptance filter**


The FDCAN offers the possibility to configure two sets of acceptance filters, one for
standard identifiers and another for extended identifiers. These filters can be assigned to Rx
FIFO 0 or Rx FIFO 1. For acceptance filtering, each list of filters is executed from element
#0 until the first matching element. Acceptance filtering stops at the first matching element,
and the following filter elements are not evaluated for this message.


RM0490 Rev 5 903/1027



952


**FD controller area network (FDCAN)** **RM0490**


The main features are:


      - Each filter element can be configured as


–
Range filter (from - to)


– Filter for one or two dedicated IDs


– Classic bit mask filter


      - Each filter element is configurable for acceptance or rejection filtering.


      - Each filter element can be enabled/disabled individually.


      - Filters are checked sequentially, execution stops with the first matching filter element


Related configuration registers are:


      - Global filter configuration (RXGFC)


      - Extended ID AND mask (XIDAM)


Depending on the configuration of the filter element (SFEC[2:0]/EFEC[2:0]), a match
triggers one of the following actions:


      - Store received frame in FIFO 0 or FIFO 1


      - Reject received frame


      - Set the high priority message interrupt flag HPM in FDCAN_IR


      - Set the high priority message interrupt flag HPM in FDCAN_IR, and store the received
frame in FIFO 0 or FIFO 1.


Acceptance filtering is started after the complete identifier has been received. After
acceptance filtering has completed, and if a matching Rx FIFO has been found, the
message handler starts writing the received message data in 32-bit portions to the matching
Rx FIFO. If the CAN protocol controller has detected an error condition (for example, CRC
error), this message is discarded with the following impact:


      - **Rx FIFO**


The put index of the matching Rx FIFO is not updated, but the related Rx FIFO element
is partly overwritten with the received data. For error type, see LEC[2:0] and DLEC[2:0]
bitfields of the FDCAN_PSR register. In case the matching Rx FIFO is operated in
overwrite mode, the boundary conditions described in _Rx FIFO overwrite mode_ have to
be considered.


_Note:_ _When an accepted message is written to one of the two Rx FIFOs, the unmodified received_
_identifier is stored independently from the used filters. The result of the acceptance filter_
_process strongly depends on the sequence of configured filter elements._


**Range filter**


The filter matches for all received frames with message IDs in the range defined by
SF1ID/SF2ID and EF1ID/EF2ID.


There are two possibilities when range filtering is used together with extended frames:


      - EFT[1:0] = 00: the message ID of received frames is AND-ed with the extended ID
AND mask (XIDAM) before the range filter is applied.


      - EFT[1:0] = 11: the extended ID AND mask (XIDAM) is not used for range filtering.


904/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**Filter for dedicated IDs**


A filter element can be configured to filter for one or two specific message IDs. To filter for
one specific message ID, the filter element has to be configured with SF1ID = SF2ID and
EF1ID = EF2ID.


**Classic bit mask filter**


The classic bit mask filtering is intended to filter groups of message IDs by masking single
bits of a received message ID. With classic bit mask filtering SF1ID/EF1ID is used as
message ID filter, while SF2ID/EF2ID is used as filter mask.


0 bit at the filter mask masks out the corresponding bit position of the configured ID filter. For
example, the value of the received message ID at that bit position is not relevant for
acceptance filtering. Only the bits of the received message ID where the corresponding
mask bits are 1 are relevant for acceptance filtering.


In case all mask bits are 1, a match occurs only when the received message ID and the
message ID filter are identical. If all mask bits are 0, all message IDs match.


**Standard message ID filtering**


_Figure 324_ shows the flow for standard message ID (11-bit identifier) filtering. The standard
message ID filter element is described in _Section 28.3.11_ .


The standard message filtering is controlled by the FDCAN_RXGFC register. The standard
message ID, the remote transmission request bit (RTR), and the identifier extension bit
(IDE) of the received frames are compared against the list of configured filter elements.


RM0490 Rev 5 905/1027



952


**FD controller area network (FDCAN)** **RM0490**


**Figure 324. Standard message ID filter path**





















































906/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**Extended message ID filtering**


_Figure 325_ shows the flow for extended message ID (29-bit identifier) filtering. The extended
message ID filter element is described in _Section 28.3.12_ .


The extended message filtering is controlled by the FDCAN_RXGFC register. The extended
message ID, the remote transmission request bit (RTR), and the identifier extension bit
(IDE) of the received frames are compared against the list of configured filter elements.


**Figure 325. Extended message ID filter path**



















































The extended ID AND mask (XIDAM) is AND-ed with the received identifier before the filter
list is executed.


RM0490 Rev 5 907/1027



952


**FD controller area network (FDCAN)** **RM0490**


**Rx FIFOs**


Rx FIFO 0 and Rx FIFO 1 can hold up to three elements each.


Received messages that passed acceptance filtering are transferred to the Rx FIFO as
configured by the matching filter element. For a description of the filter mechanisms
available for Rx FIFO 0 and Rx FIFO 1, see _Acceptance filter_ . The Rx FIFO element is
described in _Section 28.3.8_ .


When an Rx FIFO full condition is signaled by RFnF in FDCAN_IR (where n is the FIFO
number), no further messages are written to the corresponding Rx FIFO until at least one
message has been read out, and the Rx FIFO get index has been incremented. In case a
message is received while the corresponding Rx FIFO is full, this message is discarded,
and the interrupt flag RFnL is set in the FDCAN_IR register.


When reading from an Rx FIFO, the Rx FIFO get index (FnGI of FDCAN_RXFnS) + FIFO
element size has to be added to the corresponding Rx FIFO start address (FnSA).


**Rx FIFO blocking mode**


The Rx FIFO blocking mode is configured by clearing the FnOM bit in the FDCAN_RXGFC
register. This is the default operation mode for the Rx FIFOs.


When an Rx FIFO full condition is reached (FnPI = FnGI in FDCAN_RXFnS), no further
messages are written to the corresponding Rx FIFO until at least one message has been
read out and the Rx FIFO get index has been incremented. An Rx FIFO full condition is
signaled by FnF = 1 in FDCAN_RXFnS. In addition, the RFnF interrupt flag is set in
FDCAN_IR.


In case a message is received while the corresponding Rx FIFO is full, this message is
discarded, and the message lost condition is signaled by setting RFnL bit in
FDCAN_RXFnS. In addition, the RFnL interrupt flag is set in FDCAN_IR.


**Rx FIFO overwrite mode**


The Rx FIFO overwrite mode is configured by setting the FnOM bit of the FDCAN_RXGFC
register.


When an Rx FIFO full condition (FnPI = FnGI of FDCAN_RXFnS) is signaled by FnF = 1 in
FDCAN_RXFnS, the next message accepted for the FIFO overwrites the oldest FIFO
message. Put and get indices are both incremented by one.


When an Rx FIFO is operated in overwrite mode and an Rx FIFO full condition is signaled,
reading from the Rx FIFO elements must start at least at get index + 1. This is because it
may happen that a received message is written to the message RAM (put index) while the
CPU is reading from the message RAM (get index). In this case, inconsistent data can be
read from the respective Rx FIFO element. Adding an offset to the get index when reading
from the Rx FIFO avoids this problem. The offset depends on how fast the CPU accesses
the Rx FIFO.


After reading from the Rx FIFO, the number of the last element read has to be written to the
Rx FIFO acknowledge index (FnA of FDCAN_RXFnA). This increments the get index to that
element number. In case the put index has not been incremented to this Rx FIFO element,
the Rx FIFO full condition is reset (FnF = 0 in FDCAN_RXFnS).


908/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**Tx handling**


The Tx handler handles transmission requests for the Tx FIFO and the Tx queue. It controls
the transfer of transmit messages to the CAN core, the put and get indices, and the Tx event
FIFO. Up to three Tx buffers can be set up for message transmission. The CAN message
data field is configured to 64 bytes. the Tx FIFO allocates eighteen 32-bit words for storage
of a Tx element.


**Table 142. Possible configurations for frame transmission**

|CCCR|Col2|Tx buffer element|Col4|Frame transmission|
|---|---|---|---|---|
|**BRSE**|**FDOE**|**FDF**|**BRS**|**BRS**|
|Ignored|0|Ignored|Ignored|Classic CAN|
|0|1|0|Ignored|Classic CAN|
|0|1|1|Ignored|FD without bit rate switching|
|1|1|0|Ignored|Classic CAN|
|1|1|1|0|FD without bit rate switching|
|1|1|1|1|FD with bit rate switching|



_Note:_ _AUTOSAR requires at least three Tx queue buffers and support of transmit cancellation._


The Tx handler starts a Tx scan to check for the highest priority pending Tx request (Tx
buffer with lowest message ID) when the Tx buffer request pending register
(FDCAN_TXBRP) is updated, or when a transmission has been started.


**Transmit pause**


The transmit pause feature is intended for use in CAN systems where the CAN message
identifiers are permanently specified to specific values and cannot easily be changed.
These message identifiers can have a higher CAN arbitration priority than other defined
messages, while in a specific application their relative arbitration priority must be inverse.
This may lead to a case where one ECU sends a burst of CAN messages that cause
another ECU CAN messages to be delayed because that other messages have a lower
CAN arbitration priority.


As an example, if CAN ECU-1 has the feature enabled and is requested by its application
software to transmit four messages, it waits, after the first successful message transmission,
for two CAN bit times of bus-idle before it is allowed to start the next requested message. If
there are other ECUs with pending messages, these messages are started in the idle time,
and they would not need to arbitrate with the next message of ECU-1. After having received
a message, ECU-1 is allowed to start its next transmission as soon as the received
message releases the CAN bus.


The feature is controlled by the TXP bit of the CCCR register. If the bit is set, the FDCAN,
each time it has successfully transmitted a message, pauses for two CAN bit times before
starting the next transmission. This enables other CAN nodes in the network to transmit
messages even if their messages have lower prior identifiers. By default, this feature is
disabled (TXP = 0 in FDCAN_CCCR).


RM0490 Rev 5 909/1027



952


**FD controller area network (FDCAN)** **RM0490**


This feature looses up burst transmissions coming from a single node and it protects against
"babbling idiot" scenarios where the application program erroneously requests too many
transmissions.


**Tx FIFO**


Tx FIFO operation is configured by clearing the TFQM bit of the FDCAN_TXBC register.
Messages stored in the Tx FIFO are transmitted starting with the message referenced by
the get index (TFGI[1:0] bitfield of FDCAN_TXFQS). After each transmission, the get index
is incremented cyclically until the Tx FIFO is empty. The Tx FIFO enables transmission of
messages with the same message ID from different Tx buffers in the order that these
messages have been written to the Tx FIFO. The FDCAN calculates the Tx FIFO free level
(TFFL[2:0] bitfield of FDCAN_TXFQS) as the difference between the get and put index. It
indicates the number of available (free) Tx FIFO elements.


New transmit messages have to be written to the Tx FIFO starting with the Tx buffer
referenced by the put index (TFQPI[1:0] bitfield of FDCAN_TXFQS). An add request
increments the put index to the next free Tx FIFO element. When the put index reaches the
get index, Tx FIFO full (TFQF = 1 in FDCAN_TXFQS) is signaled. In this case, no further
messages must be written to the Tx FIFO until the next message has been transmitted and
the get index has been incremented.


When a single message is added to the Tx FIFO, the transmission is requested by setting
the FDCAN_TXBAR bit related to the Tx buffer referenced by the Tx FIFO put index.


When multiple (n) messages are added to the Tx FIFO, they are written to n consecutive Tx
buffers starting with the put index. The transmissions are then requested via the
FDCA_TXBAR register. The put index is then cyclically incremented by n. The number of
requested Tx buffers must not exceed the number of free Tx buffers as indicated by the Tx
FIFO free level.


When a transmission request for the Tx buffer referenced by the get index is canceled, the
get index is incremented to the next Tx buffer with a transmission request is pending and the
Tx FIFO free level is recalculated. When transmission cancellation is applied to any other Tx
buffer, the get index and the FIFO Free Level remain unchanged.


A Tx FIFO element allocates eighteen 32-bit words in the message RAM. The Therefore,
the start address of the next available (free) Tx FIFO buffer, is calculated by adding 18 times
the put index TFQPI[1:0] (0 … 2) to the Tx buffer start address TBSA.


**Tx queue**


Tx queue operation is configured by setting the TFQM of the FDCAN_TXBC register.
Messages stored in the Tx queue are transmitted starting with the message with the lowest
message ID (highest priority).


In case of mixing of standard and extended message IDs, the standard message IDs are
compared to bits [28:18] of extended message IDs.


In case multiple queue buffers are configured with the same message ID, the queue buffer
with the lowest buffer number is transmitted first.


New messages have to be written to the Tx buffer referenced by the put index (TFQPI[1:0]
in FDCAN_TXFQS). An add request cyclically increments the put index to the next free Tx
buffer. In case the Tx queue is full (TFQF = 1 in FDCAN_TXFQS), the put index is not valid
and no further message must be written to the Tx queue until at least one of the requested
messages has been sent out or a pending transmission request has been canceled.


910/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


The application can use the FDCAN_TXBRP register instead of the put index and can place
messages to any Tx buffer without pending transmission request.


A Tx queue buffer allocates eighteen 32-bit words in the message RAM. The start address
of Therefore, the next available (free) Tx queue buffer is calculated by adding 18 times the
Tx queue put index TFQPI[1:0] (0 ... 2) to the Tx buffer start address TBSA.


**Transmit cancellation**


The FDCAN supports transmit cancellation. To cancel a requested transmission from a Tx
queue buffer, the host has to write 1 to the corresponding bit position (= number of Tx buffer)
of the FDCAN_TXBCR register. Transmit cancellation is not intended for Tx FIFO operation.


Successful cancellation is signaled by setting the corresponding bit of the FDCAN_TXBCF
register.


In case a transmit cancellation is requested while a transmission from a Tx buffer is already
ongoing, the corresponding FDCAN _TXBRP bit remains set as long as the transmission is
in progress. If the transmission is successful, the corresponding FDCAN_TXBTO and
FDCAN_TXBCF bits are set. If the transmission is not successful, it is not repeated and only
the corresponding FDCAN_TXBCF bit is set.


_Note:_ _In case a pending transmission is canceled immediately before it has been started, there is_
_a short time window where no transmission is started even if another message is pending in_
_the node. This can enable another node to transmit a message that can have a priority lower_
_than that of the second message in the node._


**Tx event handling**


To support Tx event handling the FDCAN has implemented a Tx event FIFO. After the
FDCAN has transmitted a message on the CAN bus, message ID and timestamp are stored
in a Tx event FIFO element. To link a Tx event to a Tx event FIFO element, the message
marker from the transmitted Tx buffer is copied into the Tx event FIFO element.


The Tx event FIFO is configured to three elements. The Tx event FIFO element is described
in _Tx FIFO_ .


The purpose of the Tx event FIFO is to decouple handling transmit status information from
transmit message handling that is, a Tx buffer holds only the message to be transmitted,
while the transmit status is stored separately in the Tx event FIFO. This has the advantage,
especially when operating a dynamically managed transmit queue, that a Tx buffer can be
used for a new message immediately after successful transmission. There is no need to
save transmit status information from a Tx buffer before overwriting that Tx buffer.


When a Tx event FIFO full condition is signaled by the TEFF bit of the FDCAN_IR, no
further elements are written to the Tx event FIFO until at least one element has been read
out and the Tx event FIFO get index has been incremented. In case a Tx event occurs while
the Tx event FIFO is full, this event is discarded and the TEFL interrupt flag is set in the
FDCAN_IR register.


When reading from the Tx event FIFO, the Tx event FIFO get index (EFGI[1:0] of
FDCAN_TXEFS) has to be added twice to the Tx event FIFO start address EFSA.


RM0490 Rev 5 911/1027



952


**FD controller area network (FDCAN)** **RM0490**


**28.3.7** **FIFO acknowledge handling**


The get indices of Rx FIFO 0, Rx FIFO 1, and the Tx event FIFO are controlled by writing to
the corresponding FIFO acknowledge index (see _Section 28.4.23_ and _Section 28.4.25_ ).
Writing to the FIFO acknowledge index sets the FIFO get index to the FIFO acknowledge
index plus one and thereby updates the FIFO fill level. There are two use cases:


      - When only a single element has been read from the FIFO (the one being pointed to by
the get index), this get index value is written to the FIFO acknowledge index.


      - When a sequence of elements has been read from the FIFO, it is sufficient to write the
FIFO acknowledge index only once at the end of that read sequence (value = index of
the last element read), to update the FIFO get index.


Because the CPU has free access to the FDCAN message RAM, special care has to be
taken when reading FIFO elements in an arbitrary order (get index not considered). This
might be useful when reading a high priority message from one of the two Rx FIFOs. In this
case, the FIFO acknowledge index must not be written because this would set the get index
to a wrong position and alter the FIFO fill level. In this case, some of the older FIFO
elements would be lost.


_Note:_ _The application has to ensure that a valid value is written to the FIFO acknowledge index._
_The FDCAN does not check for erroneous values._


**28.3.8** **FDCAN Rx FIFO element**


Two Rx FIFOs are configured in the message RAM. Each Rx FIFO section can be
configured to store up to three received messages. The structure of an Rx FIFO element is
described in _Table 143_ . The description is provided in _Table 144_ .


**Table 143. Rx FIFO element**




|Bit|31 24|Col3|Col4|Col5|23 16|Col7|Col8|Col9|15 8|7 0|
|---|---|---|---|---|---|---|---|---|---|---|
|R0|ESI|XTD|RTR|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|
|R1|ANMF|FIDX[6:0]|FIDX[6:0]|FIDX[6:0]|Res.|FDF|BRS|DLC[3:0]|RXTS[15:0]|RXTS[15:0]|
|R2|DB3[7:0]|DB3[7:0]|DB3[7:0]|DB3[7:0]|DB2[7:0]|DB2[7:0]|DB2[7:0]|DB2[7:0]|DB1[7:0]|D[7:0]|
|R3|DB7[7:0]|DB7[7:0]|DB7[7:0]|DB7[7:0]|DB6[7:0]|DB6[7:0]|DB6[7:0]|DB6[7:0]|DB5[7:0]|DB4[7:0]|
|...|...|...|...|...|...|...|...|...|...|...|
|Rn|DBm[7:0]|DBm[7:0]|DBm[7:0]|DBm[7:0]|DBm-1[7:0]|DBm-1[7:0]|DBm-1[7:0]|DBm-1[7:0]|DBm-2[7:0]|DBm-3[7:0]|



The element size configured for storage of CAN FD messages is set to 64-byte data field.


**Table 144. Rx FIFO element description**






|Field|Description|
|---|---|
|R0 Bit 31<br>ESI|Error state indicator<br>– 0: Transmitting node is error active<br>– 1: Transmitting node is error passive|
|R0 Bit 30<br>XTD|Extended identifier<br>Signals to the host whether the received frame has a standard or extended identifier.<br>– 0: 11-bit standard identifier<br>– 1: 29-bit extended identifier|



912/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**Table 144. Rx FIFO element description (continued)**








|Field|Description|
|---|---|
|R0 Bit 29<br>RTR|Remote transmission request<br>Signals to the host whether the received frame is a data frame or a remote frame.<br>– 0: Received frame is a data frame<br>– 1: Received frame is a remote frame|
|R0 Bits 28:0<br>ID[28:0]|Identifier<br>Standard or extended identifier depending on bit XTD. A standard identifier is stored<br>into ID[28:18].|
|R1 Bit 31<br>ANMF|Accepted non-matching frame<br>Acceptance of non-matching frames can be enabled via ANFS[1:0] and ANFE[1:0]<br>bitfield of FDCAN_RXGFC.<br>– 0: Received frame matching filter index FIDX<br>– 1: Received frame did not match any Rx filter element|
|R1 Bits 30:24<br>FIDX[6:0]|Filter index<br>0-27=Index of matching Rx acceptance filter element (invalid if ANMF = 1).<br>Range: 0 to LSS[4:0] - 1 or LSE[3:0] - 1 in FDCAN_RXGFC.|
|R1 Bit 21<br>FDF|FD format<br>– 0: Standard frame format<br>– 1: FDCAN frame format (new DLC-coding and CRC)|
|R1 Bit 20<br>BRS|Bit rate switch<br>– 0: Frame received without bit rate switching<br>– 1: Frame received with bit rate switching|
|R1 Bits 19:16<br>DLC[3:0]|Data length code<br>– 0-8: Classic CAN + CAN FD: received frame has 0-8 data bytes<br>– 9-15: Classic CAN: received frame has 8 data bytes<br>– 9-15: CAN FD: received frame has 12/16/20/24/32/48/64 data bytes|
|R1 Bits 15:0<br>RXTS[15:0]|Rx timestamp<br>Timestamp Counter value captured on start of frame reception. Resolution depending<br>on configuration of the timestamp counter prescaler TCP[3:0] of FDCAN_TSCC.|
|R2 Bits 31:24<br>DB3[7:0]|Data byte 3|
|R2 Bits 23:16<br>DB2[7:0]|Data byte 2|
|R2 Bits 15:8<br>DB1[7:0]|Data byte 1|
|R2 Bits 7:0<br>D[7:0]|Data byte 0|
|R3 Bits 31:24<br>DB7[7:0]|Data byte 7|
|R3 Bits 23:16<br>DB6[7:0]|Data byte 6|



RM0490 Rev 5 913/1027



952


**FD controller area network (FDCAN)** **RM0490**


**Table 144. Rx FIFO element description (continued)**

|Field|Description|
|---|---|
|R3 Bits 15:8<br>DB5[7:0]|Data byte 5|
|R3 Bits 7:0<br>DB4[7:0]|Data byte 4|
|...|...|
|Rn Bits 31:24<br>DBm[7:0]|Data byte m|
|Rn Bits 23:16<br>DBm-1[7:0]|Data byte m-1|
|Rn Bits 15:8<br>DBm-2[7:0]|Data byte m-2|
|Rn Bits 7:0<br>DBm-3[7:0]|Data byte m-3|



**28.3.9** **FDCAN Tx buffer element**


The Tx buffers section (three elements) can be configured to hold Tx FIFO or Tx queue. The
Tx handler distinguishes between Tx FIFO and Tx queue using the Tx buffer configuration
TFQM bit of the FDCAN_TXBC register. The element size is configured for storage of CAN
FD messages with up to 64-byte data.


**Table 145. Tx buffer and FIFO element**

|Bit|31 24|Col3|Col4|Col5|23 16|Col7|Col8|Col9|Col10|15 8|7 0|
|---|---|---|---|---|---|---|---|---|---|---|---|
|T0|ESI|XTD|RTR|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|
|T1|MM[7:0]|MM[7:0]|MM[7:0]|MM[7:0]|EFC|Res.|FDF|BRS|DLC[3:0]|Res.|Res.|
|T2|DB3[7:0]|DB3[7:0]|DB3[7:0]|DB3[7:0]|DB2[7:0]|DB2[7:0]|DB2[7:0]|DB2[7:0]|DB2[7:0]|DB1[7:0]|D[7:0]|
|T3|DB7[7:0]|DB7[7:0]|DB7[7:0]|DB7[7:0]|DB6[7:0]|DB6[7:0]|DB6[7:0]|DB6[7:0]|DB6[7:0]|DB5[7:0]|DB4[7:0]|
|...|...|...|...|...|...|...|...|...|...|...|...|
|Tn|DBm[7:0]|DBm[7:0]|DBm[7:0]|DBm[7:0]|DBm-1[7:0]|DBm-1[7:0]|DBm-1[7:0]|DBm-1[7:0]|DBm-1[7:0]|DBm-2[7:0]|DBm-3[7:0]|



**Table 146. Tx buffer element description**






|Field|Description|
|---|---|
|T0 Bit 31<br>ESI(1)|Error state indicator<br>– 0: ESI bit in CAN FD format depends only on error passive flag<br>– 1: ESI bit in CAN FD format transmitted recessive|
|T0 Bit 30<br>XTD|Extended identifier<br>– 0: 11-bit standard identifier<br>– 1: 29-bit extended identifier|



914/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**Table 146. Tx buffer element description (continued)**








|Field|Description|
|---|---|
|T0 Bit 29<br>RTR(2)|Remote transmission request<br>– 0: Transmit data frame<br>– 1: Transmit remote frame|
|T0 Bits 28:0<br>ID[28:0]|Identifier<br>Standard or extended identifier depending on bit XTD. A standard identifier has to be<br>written to ID[28:18].|
|T1 Bits 31:24<br>MM[7:0]|Message marker<br>Written by CPU during Tx buffer configuration. Copied into Tx event FIFO element for<br>identification of Tx message status.|
|T1 Bit 23<br>EFC|Event FIFO control<br>– 0: Do not store Tx events<br>– 1: Store Tx events|
|T1 Bit 21<br>FDF|FD format<br>– 0: Frame transmitted in classic CAN format<br>– 1: Frame transmitted in CAN FD format|
|T1 Bit 20<br>BRS(3)|Bit rate switching<br>– 0: CAN FD frames transmitted without bit rate switching<br>– 1: CAN FD frames transmitted with bit rate switching|
|T1 Bits 19:16<br>DLC[3:0]|Data length code<br>– 0 - 8: Classic CAN + CAN FD: received frame has 0-8 data bytes<br>– 9 - 15: Classic CAN: received frame has 8 data bytes<br>– 9 - 15: CAN FD: received frame has 12/16/20/24/32/48/64 data bytes|
|T2 Bits 31:24<br>DB3[7:0]|Data byte 3|
|T2 Bits 23:16<br>DB2[7:0]|Data byte 2|
|T2 Bits 15:8<br>DB1[7:0]|Data byte 1|
|T2 Bits 7:0<br>D[7:0]|Data byte 0|
|T3 Bits 31:24<br>DB7[7:0]|Data byte 7|
|T3 Bits 23:16<br>DB6[7:0]|Data byte 6|
|T3 Bits 15:8<br>DB5[7:0]|Data byte 5|
|T3 Bits 7:0<br>DB4[7:0]|Data byte 4|
|...|...|



RM0490 Rev 5 915/1027



952


**FD controller area network (FDCAN)** **RM0490**


**Table 146. Tx buffer element description (continued)**

|Field|Description|
|---|---|
|Tn Bits 31:24<br>DBm[7:0]|Data byte m|
|Tn Bits 23:16<br>DBm-1[7:0]|Data byte m-1|
|Tn Bits 15:8<br>DBm-2[7:0]|Data byte m-2|
|Tn Bits 7:0<br>DBm-3[7:0]|Data byte m-3|



1. The ESI bit of the transmit buffer is OR-ed with the error passive flag to decide the value of the ESI bit in
the transmitted FD frame. As required by the CAN FD protocol specification, an error active node can
optionally transmit the ESI bit recessive, but an error passive node always transmits the ESI bit recessive.


2. When RTR = 1, the FDCAN transmits a remote frame according to ISO11898-1, even if the transmission in
CAN FD format is enabled by the FDOE bit of the FDCAN_CCCR.


3. Bits ESI, FDF, and BRS are only evaluated when CAN FD operation is enabled by setting the FDOE bit of
the FDCAN_CCCR. Bit BRS is only evaluated when in addition BRSE bit is set in FDCAN_CCCR.


**28.3.10** **FDCAN Tx event FIFO element**


Each element stores information about transmitted messages. By reading the Tx event,
FIFO the host CPU gets this information in the order that the messages were transmitted.
Status information about the Tx event FIFO can be obtained from FDCAN_TXEFS register.


**Table 147. Tx event FIFO element**

|Bit|31 24|Col3|Col4|Col5|23 16|Col7|Col8|Col9|15 8|7 0|
|---|---|---|---|---|---|---|---|---|---|---|
|E0|ESI|XTD|RTR|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|ID[28:0]|
|E1|MM[7:0]|MM[7:0]|MM[7:0]|MM[7:0]|ET[1:0]|EDL|BRS|DLC[3:0]|TXTS[15:0]|TXTS[15:0]|



**Table 148. Tx event FIFO element description**






|Field|Description|
|---|---|
|E0 Bit 31<br>ESI|Error state indicator<br>– 0: Transmitting node is error active<br>– 1: Transmitting node is error passive|
|E0 Bit 30<br>XTD|Extended identifier<br>– 0: 11-bit standard identifier<br>– 1: 29-bit extended identifier|
|E0 Bit 29<br>RTR|Remote transmission request<br>– 0: Transmit data frame<br>– 1: Transmit remote frame|
|E0 Bits 28:0<br>ID[28:0]|Identifier<br>Standard or extended identifier depending on bit XTD. A standard identifier has to be<br>written to ID[28:18].|



916/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**Table 148. Tx event FIFO element description (continued)**






|Field|Description|
|---|---|
|E1 Bits 31:24<br>MM[7:0]|Message marker<br>Copied from Tx buffer into Tx event FIFO element for identification of Tx message<br>status.|
|E1 Bits 23:22<br>EFC|Event type<br>– 00: Reserved<br>– 01: Tx event<br>– 10: Transmission in spite of cancellation (always set for transmissions in DAR<br>mode)<br>– 11: Reserved|
|E1 Bit 21<br>EDL|Extended data length<br>– 0: Standard frame format<br>– 1: FDCAN frame format (new DLC-coding and CRC)|
|E1 Bit 20<br>BRS|Bit rate switching<br>– 0: Frame transmitted without bit rate switching<br>– 1: Frame transmitted with bit rate switching|
|T1 Bits 19:16<br>DLC[3:0]|Data length code<br>0 - 8: Frame with 0-8 data bytes transmitted<br>9 - 15: Frame with 8 data bytes transmitted|
|E1 Bits 15:0<br>TXTS[15:0]|Tx Timestamp<br>Timestamp counter value captured on start of frame transmission. Resolution<br>depending on configuration of the timestamp counter prescaler TCP[3:0] of<br>FDCAN_TSCC.|



**28.3.11** **FDCAN standard message ID filter element**


Up to 28 filter elements can be configured for 11-bit standard IDs. When accessing a
standard message ID filter element, its address is the filter list standard start address
FLSSA plus the index of the filter element (0 … 27).


**Table 149. Standard message ID filter element**

|Bit|31 24|Col3|Col4|23 16|15 8|Col7|7 0|
|---|---|---|---|---|---|---|---|
|S0|SFT[1:0]|SFEC[2:0]|SFID1[10:0]|SFID1[10:0]|Res.|SFID2[10:0]|SFID2[10:0]|



RM0490 Rev 5 917/1027



952


**FD controller area network (FDCAN)** **RM0490**


**Table 150. Standard message ID filter element field description**







|Field|Description|
|---|---|
|Bit 31:30<br>SFT[1:0](1)|Standard filter type<br>– 00: Range filter from SFID1 to SFID2<br>– 01: Dual ID filter for SFID1 or SFID2<br>– 10: Classic filter: SFID1 = filter, SFID2 = mask<br>– 11: Filter element disabled|
|Bit 29:27<br>SFEC[2:0]|Standard filter element configuration<br>All enabled filter elements are used for acceptance filtering of standard frames.<br>Acceptance filtering stops at the first matching enabled filter element or when the end<br>of the filter list is reached. If SFEC[2:0] = 100, 101 or 110 a match sets interrupt flag<br>IR.HPM and, if enabled, an interrupt is generated. In this case register HPMS is<br>updated with the status of the priority match.<br>– 000: Disable filter element<br>– 001: Store in Rx FIFO 0 if filter matches<br>– 010: Store in Rx FIFO 1 if filter matches<br>– 011: Reject ID if filter matches<br>– 100: Set priority if filter matches<br>– 101: Set priority and store in FIFO 0 if filter matches<br>– 110: Set priority and store in FIFO 1 if filter matches<br>– 111: Not used|
|Bits 26:16<br>SFID1[10:0]|Standard filter ID 1<br>First ID of standard ID filter element.|
|Bits 10:0<br>SFID2[10:0]|Standard filter ID 2<br>Second ID of standard ID filter element.|


1. With SFT[1:0] = 11 the filter element is disabled and the acceptance filtering continues (same behavior as
with SFEC[2:0] = 000).


_Note:_ _In case a reserved value is configured, the filter element is considered disabled._


**28.3.12** **FDCAN extended message ID filter element**


Up to eight filter elements can be configured for 29-bit extended IDs. When accessing an
extended message ID filter element, its address is the filter list extended start address
FLESA plus twice the index of the filter element (0 … 7).


**Table 151. Extended message ID filter element**

|Bit|31|Col3|24|23 16|15 8|7 0|
|---|---|---|---|---|---|---|
|F0|EFEC[2:0]|EFEC[2:0]|EFID1[28:0]|EFID1[28:0]|EFID1[28:0]|EFID1[28:0]|
|F1|EFT[1:0]|Res.|EFID2[28:0]|EFID2[28:0]|EFID2[28:0]|EFID2[28:0]|



918/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**Table 152. Extended message ID filter element field description**







|Field|Description|
|---|---|
|F0 Bits 31:29<br>EFEC[2:0]|Extended filter element configuration<br>All enabled filter elements are used for acceptance filtering of extended frames.<br>Acceptance filtering stops at the first matching enabled filter element or when the end<br>of the filter list is reached. If EFEC[2:0] = 100, 101 or 110 a match sets interrupt flag<br>IR[HPM] and, if enabled, an interrupt is generated. In this case register HPMS is<br>updated with the status of the priority match.<br>– 000: Disable filter element<br>– 001: Store in Rx FIFO 0 if filter matches<br>– 010: Store in Rx FIFO 1 if filter matches<br>– 011: Reject ID if filter matches<br>– 100: Set priority if filter matches<br>– 101: Set priority and store in FIFO 0 if filter matches<br>– 110: Set priority and store in FIFO 1 if filter matches<br>– 111: Not used|
|F0 Bits 28:0<br>EFID1[28:0]|Extended filter ID 1<br>First ID of extended ID filter element.<br>When filtering for Rx FIFO, this field defines the ID of an extended message to be<br>stored. The received identifiers must match exactly, only XIDAM masking<br>mechanism.|
|F1 Bits 31:30<br>EFT[1:0]|Extended filter type<br>– 00: Range filter from EF1ID to EF2ID (EF2ID ≥EF1ID)<br>– 01: Dual ID filter for EF1ID or EF2ID<br>– 10: Classic filter: EF1ID = filter, EF2ID = mask<br>– 11: Range filter from EF1ID to EF2ID (EF2ID ≥EF1ID), XIDAM mask not applied|
|F1 Bit 29|Not used|
|F1 Bits 28:0<br>EFID2[28:0]|Extended filter ID 2<br>Second ID of extended ID filter element.|


RM0490 Rev 5 919/1027



952


**FD controller area network (FDCAN)** **RM0490**

## **28.4 FDCAN registers**


**28.4.1** **FDCAN core release register (FDCAN_CREL)**


Address offset: 0x0000


Reset value: 0x3214 1218

|31 30 29 28|Col2|Col3|Col4|27 26 25 24|Col6|Col7|Col8|23 22 21 20|Col10|Col11|Col12|19 18 17 16|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|REL[3:0]|REL[3:0]|REL[3:0]|REL[3:0]|STEP[3:0]|STEP[3:0]|STEP[3:0]|STEP[3:0]|SUBSTEP[3:0]|SUBSTEP[3:0]|SUBSTEP[3:0]|SUBSTEP[3:0]|YEAR[3:0]|YEAR[3:0]|YEAR[3:0]|YEAR[3:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MON[7:0]|MON[7:0]|MON[7:0]|MON[7:0]|MON[7:0]|MON[7:0]|MON[7:0]|MON[7:0]|DAY[7:0]|DAY[7:0]|DAY[7:0]|DAY[7:0]|DAY[7:0]|DAY[7:0]|DAY[7:0]|DAY[7:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:28 **REL[3:0]** : 3


Bits 27:24 **STEP[3:0]** : 2


Bits 23:20 **SUBSTEP[3:0]** : 1


Bits 19:16 **YEAR[3:0]** : 4


Bits 15:8 **MON[7:0]** : 12


Bits 7:0 **DAY[7:0]** : 18


**28.4.2** **FDCAN endian register (FDCAN_ENDN)**


Address offset: 0x0004


Reset value: 0x8765 4321

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|ETV[31:16]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|ETV[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:0 **ETV[31:0]** : Endianness test value

The endianness test value is 0x8765 4321.


_Note:_ _The register read must give the reset value to ensure no endianness issue._


**28.4.3** **FDCAN data bit timing and prescaler register (FDCAN_DBTP)**


Address offset: 0x000C


Reset value: 0x0000 0A33


This register is only writable if the CCE and INIT bits of the FDCAN_CCCR are set. The
CAN time quantum can be programmed in the range of 1 to 32 FDCAN clock periods:
t q = (DBRP[4:0] + 1) FDCAN clock periods.


920/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


DTSEG1[4:0] is the sum of PROP_SEG and PHASE_SEG1. DTSEG2[3:0] is
PHASE_SEG2. Therefore, the length of the bit time is
(programmed values) × [DTSEG1[4:0] + DTSEG2[3:0] + 3] × t q or
(functional values) × [SYNC_SEG + PROP_SEG + PHASE_SEG1 + PHASE_SEG2] × t q .


The information processing time (IPT) is 0, meaning the data for the next bit is available at
the first clock edge after the sample point.

|31|30|29|28|27|26|25|24|23|22|21|20 19 18 17 16|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TDC|Res.|Res.|DBRP[4:0]|DBRP[4:0]|DBRP[4:0]|DBRP[4:0]|DBRP[4:0]|
|||||||||rw|||rw|rw|rw|rw|rw|


|15|14|13|12 11 10 9 8|Col5|Col6|Col7|Col8|7 6 5 4|Col10|Col11|Col12|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|DTSEG1[4:0]|DTSEG1[4:0]|DTSEG1[4:0]|DTSEG1[4:0]|DTSEG1[4:0]|DTSEG2[3:0]|DTSEG2[3:0]|DTSEG2[3:0]|DTSEG2[3:0]|DSJW[3:0]|DSJW[3:0]|DSJW[3:0]|DSJW[3:0]|
||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:24 Reserved, must be kept at reset value.


Bit 23 **TDC** : Transceiver delay compensation

0: Transceiver delay compensation disabled
1: Transceiver delay compensation enabled


Bits 22:21 Reserved, must be kept at reset value.


Bits 20:16 **DBRP[4:0]** : Data bit rate prescaler

The value by which the oscillator frequency is divided to generate the bit time quanta. The bit
time is built up from a multiple of this quantum. Valid values for the baud rate prescaler are 0
to 31. The hardware interpreters this value as the value programmed plus 1.


Bits 15:13 Reserved, must be kept at reset value.


Bits 12:8 **DTSEG1[4:0]** : Data time segment before sample point

Valid values are 0 to 31. The value used by the hardware is the one programmed,
incremented by 1, that is t BS1 = (DTSEG1[4:0] + 1) × t q .


Bits 7:4 **DTSEG2[3:0]** : Data time segment after sample point

Valid values are 0 to 15. The value used by the hardware is the one programmed,
incremented by 1, i.e. t BS2 = (DTSEG2[3:0] + 1) × t q .


Bits 3:0 **DSJW[3:0]** : Synchronization jump width

Valid values are 0 to 15. The value used by the hardware is the one programmed,
incremented by 1: t SJW = (DSJW[3:0] + 1) × t q .


_Note:_ _With an FDCAN clock of 8 MHz, the reset value 0x0000 0A33 configures the FDCAN for a_
_fast bit rate of 500 kbit/s._


_The data phase bit rate must be higher than or equal to the nominal bit rate._


**28.4.4** **FDCAN test register (FDCAN_TEST)**


Write access to this register is enabled by setting the TEST bit of the FDCAN_CCCR
register. All register functions are set to their reset values when this bit is cleared.


Loop-back mode and software control of Tx pin FDCANx_TX are hardware test modes.
Programming TX[1:0] differently from 00 can disturb the message transfer on the CAN bus.


Address offset: 0x0010


Reset value: 0x0000 0000


RM0490 Rev 5 921/1027



952


**FD controller area network (FDCAN)** **RM0490**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6 5|Col11|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RX|TX[1:0]|TX[1:0]|LBCK|Res.|Res.|Res.|Res.|
|||||||||r|rw|rw|rw|||||



Bits 31:8 Reserved, must be kept at reset value.


Bit 7 **RX** : Receive pin

This bit is used to monitor the actual value of FDCANx_RX. It is synchronized with the
FDCANx_RX pin, so it is set after reset if the FDCAN is connected to a network.
0: The CAN bus is dominant (FDCANx_RX = 0)
1: The CAN bus is recessive (FDCANx_RX = 1)


Bits 6:5 **TX[1:0]** : Control of transmit pin

00: Reset value, FDCANx_TX TX is controlled by the CAN core, updated at the end of the
CAN bit time

01: Sample point can be monitored at pin FDCANx_TX
10: Dominant (0) level at pin FDCANx_TX
11: Recessive (1) at pin FDCANx_TX


Bit 4 **LBCK** : Loop-back mode

0: Reset value, loop-back mode is disabled
1: Loop-back mode is enabled (see _Power-down (Sleep mode)_ )


Bits 3:0 Reserved, must be kept at reset value.


**28.4.5** **FDCAN RAM watchdog register (FDCAN_RWD)**


The RAM watchdog monitors the READY output of the message RAM. A message RAM
access starts the message RAM watchdog counter with the value configured through the
WDC[7:0] bitfield of the FDCAN_RWD register.


The counter is reloaded with WDC[7:0] when the message RAM signals successful
completion by activating its READY output. In case there is no response from the message
RAM until the counter has counted down to 0, the counter stops, and the interrupt flag WDI
is set in the FDCAN_IR register. The RAM watchdog counter is clocked by the fdcan_pclk
clock.


Address offset: 0x0014


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|WDV[7:0]|WDV[7:0]|WDV[7:0]|WDV[7:0]|WDV[7:0]|WDV[7:0]|WDV[7:0]|WDV[7:0]|WDC[7:0]|WDC[7:0]|WDC[7:0]|WDC[7:0]|WDC[7:0]|WDC[7:0]|WDC[7:0]|WDC[7:0]|
|r|r|r|r|r|r|r|r|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


922/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


Bits 15:8 **WDV[7:0]** : Watchdog value

Actual message RAM watchdog counter value.


Bits 7:0 **WDC[7:0]** : Watchdog configuration

Start value of the message RAM watchdog counter. With the reset value of 00, the counter is
disabled.

This bitfield is write-protected (P): write access is possible only when the CCE and INIT bits
of the FDCAN_CCCR register are both set.


**28.4.6** **FDCAN CC control register (FDCAN_CCCR)**


Address offset: 0x0018


Reset value: 0x0000 0001


For details about setting and clearing single bits, see _Software initialization_ .

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|NISO|TXP|EFBI|PXHD|Res.|Res.|BRSE|FDOE|TEST|DAR|MON|CSR|CSA|ASM|CCE|INIT|
|rw|rw|rw|rw|||rw|rw|rw|rw|rw|rw|r|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bit 15 **NISO** : Non-ISO operation

If this bit is set, the FDCAN uses the CAN FD frame format as specified by the Bosch CAN
FD Specification V1.0.
0: CAN FD frame format according to ISO11898-1
1: CAN FD frame format according to Bosch CAN FD Specification V1.0


Bit 14 **TXP:** Transmit pause enable

If this bit is set, the FDCAN pauses for two CAN bit times before starting the next
transmission after successfully transmitting a frame.

0: Disabled

1: Enabled


Bit 13 **EFBI** : Edge filtering during bus integration

0: Edge filtering disabled
1: Two consecutive dominant t q required to detect an edge for hard synchronization


Bit 12 **PXHD** : Protocol exception handling disable

0: Protocol exception handling enabled
1: Protocol exception handling disabled


Bits 11:10 Reserved, must be kept at reset value.


Bit 9 **BRSE** : FDCAN bit rate switching

0: Bit rate switching for transmissions disabled
1: Bit rate switching for transmissions enabled


Bit 8 **FDOE** : FD operation enable

0: FD operation disabled
1: FD operation enabled


RM0490 Rev 5 923/1027



952


**FD controller area network (FDCAN)** **RM0490**


Bit 7 **TEST** : Test mode enable

0: Normal operation, FDCAN_TEST holds reset values
1: Test mode, write access to FDCAN_TEST enabled


Bit 6 **DAR** : Disable automatic retransmission

0: Automatic retransmission of messages not transmitted successfully enabled

1: Automatic retransmission disabled


Bit 5 **MON** : Bus monitoring mode

This bit can only be set by software when both CCE and INIT are set. The bit can be cleared
by the host at any time.
0: Bus monitoring mode disabled
1: Bus monitoring mode enabled


Bit 4 **CSR** : Clock stop request

0: No clock stop requested
1: Clock stop requested. When clock stop is requested, first INIT and then CSA is set after all
pending transfer requests have been completed and the CAN bus is idle.


Bit 3 **CSA** : Clock stop acknowledge

0: No clock stop acknowledged
1: FDCAN can be set in power-down by stopping APB clock and kernel clock.


Bit 2 **ASM** : ASM restricted operation mode

The restricted operation mode is intended for applications that adapt themselves to different
CAN bit rates. The application tests different bit rates and leaves the restricted operation
mode after it has received a valid frame. In the optional restricted operation mode the node is
able to transmit and receive data and remote frames and it gives acknowledge to valid
frames, but it does not send active error frames or over.load frames. In case of an error
condition or overload condition, it does not send dominant bits, instead it waits for the
occurrence of bus-idle condition to resynchronize itself to the CAN communication. The error
counters are not incremented. Bit ASM can only be set by software when both CCE and INIT
are set. The bit can be cleared by the software at any time.
0: Normal CAN operation
1: Restricted operation mode active


Bit 1 **CCE** : Configuration change enable

0: The CPU has no write access to the protected configuration registers.
1: The CPU has write access to the protected configuration registers (while INIT set in
FDCAN_CCCR).


Bit 0 **INIT** : Initialization

0: Normal operation

1: Initialization started


_Note:_ _Due to the synchronization mechanism between the two clock domains, there can be a_
_delay until the value written to INIT can be read back. Therefore, the programmer has to_
_assure that the previous value written to INIT has been accepted by reading INIT before_
_setting INIT to a new value._


**28.4.7** **FDCAN nominal bit timing and prescaler register (FDCAN_NBTP)**


Address offset: 0x001C


Reset value: 0x0600 0A03


924/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


This register is only writable if the CCE and INIT bits of the FDCAN_CCCR register are both
set. The CAN bit time can be programed in the range of 4 to 81 × t q . The CAN time quantum
can be programmed in the range of 1 to 1024 FDCAN kernel clock periods:
t q = (BRP + 1) × FDCAN clock period fdcan_ker_ck.


NTSEG1[7:0] is the sum of PROP_SEG and PHASE_SEG1. NTSEG2[6:0] is
PHASE_SEG2. Therefore, the length of the bit time is
(programmed values) × [NTSEG1[7:0] + NTSEG2[6:0] + 3] × t q or
(functional values) × [SYNC_SEG + PROP_SEG + PHASE_SEG1 + PHASE_SEG2] × t q .


The information processing time (IPT) is 0, meaning the data for the next bit is available at
the first clock edge after the sample point.

|31 30 29 28 27 26 25|Col2|Col3|Col4|Col5|Col6|Col7|24 23 22 21 20 19 18 17 16|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|NSJW[6:0]|NSJW[6:0]|NSJW[6:0]|NSJW[6:0]|NSJW[6:0]|NSJW[6:0]|NSJW[6:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7|6 5 4 3 2 1 0|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|NTSEG1[7:0]|NTSEG1[7:0]|NTSEG1[7:0]|NTSEG1[7:0]|NTSEG1[7:0]|NTSEG1[7:0]|NTSEG1[7:0]|NTSEG1[7:0]|Res.|NTSEG2[6:0]|NTSEG2[6:0]|NTSEG2[6:0]|NTSEG2[6:0]|NTSEG2[6:0]|NTSEG2[6:0]|NTSEG2[6:0]|
|rw|rw|rw|rw|rw|rw|rw|rw||rw|rw|rw|rw|rw|rw|rw|



Bits 31:25 **NSJW[6:0]** : Nominal (re)synchronization jump width

Valid values are 0 to 127. The actual interpretation by the hardware of this value is such that
the used value is the one programmed incremented by one.
This bitfield is write-protected (P): write access is possible only when the CCE and INIT bits of
the FDCAN_CCCR register are both set.


Bits 24:16 **NBRP[8:0]** : Bit rate prescaler

Value by which the oscillator frequency is divided for generating the bit time quanta. The bit
time is built up from a multiple of this quantum. Valid values are 0 to 511. The actual
interpretation by the hardware of this value is such that one more than the value programmed
here is used.

This bitfield is write-protected (P): write access is possible only when the CCE and INIT bits of
the FDCAN_CCCR register are both set.


Bits 15:8 **NTSEG1[7:0]** : Nominal time segment before sample point

Valid values are 0 to 255. The actual interpretation by the hardware of this value is such that
one more than the programmed value is used.
This bitfield is write-protected write (P): write access is possible only when the CCE and INIT
bits of the FDCAN_CCCR register are both set.


Bit 7 Reserved, must be kept at reset value.


Bits 6:0 **NTSEG2[6:0]** : Nominal time segment after sample point

Valid values are 0 to 127. The actual interpretation by the hardware of this value is such that
one more than the programmed value is used.


_Note:_ _With a CAN kernel clock of 48 MHz, the reset value of 0x0600 0A03 configures the FDCAN_
_for a bit rate of 3 Mbit/s._


RM0490 Rev 5 925/1027



952


**FD controller area network (FDCAN)** **RM0490**


**28.4.8** **FDCAN timestamp counter configuration register (FDCAN_TSCC)**


Address offset: 0x0020


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19 18 17 16|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TCP[3:0]|TCP[3:0]|TCP[3:0]|TCP[3:0]|
|||||||||||||rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TSS[1:0]|TSS[1:0]|
|||||||||||||||rw|rw|



Bits 31:20 Reserved, must be kept at reset value.


Bits 19:16 **TCP[3:0]** : Timestamp counter prescaler

Configures the timestamp and timeout counters time unit in multiples of CAN bit times

[1…16].
The actual interpretation by the hardware of this value is such that one more than the value
programmed here is used.
In CAN FD mode, the internal timestamp counter TCP does not provide a constant time base
due to the different CAN bit times between arbitration phase and data phase. Thus CAN FD
requires an external counter for timestamp generation (TSS[1:0] = 10).
This bitfield is write-protected (P): write access is possible only when the CCE and INIT bits
of the FDCAN_CCCR register are both set.


Bits 15:2 Reserved, must be kept at reset value.


Bits 1:0 **TSS[1:0]** : Timestamp select

00: Timestamp counter value always 0x0000
01: Timestamp counter value incremented according to TCP
10: External timestamp counter from TIM3 value (tim3_cnt[0:15])

11: Same as 00.

These bits are write-protected write (P): write access is possible only when the CCE and INIT
bits of the FDCAN_CCCR register are both set.


**28.4.9** **FDCAN timestamp counter value register (FDCAN_TSCV)**


Address offset: 0x0024


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|
|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|



Bits 31:16 Reserved, must be kept at reset value.


926/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


Bits 15:0 **TSC[15:0]** : Timestamp counter

The internal/external timestamp counter value is captured on start of frame (both Rx and Tx).
When TSS[1:0] = 01 in FDCAN_TSCC, the timestamp counter is incremented in multiples of
CAN bit times [1 … 16] depending on the configuration of TCP[3:0] in FDCAN_TSCC. A wrap
around sets the TSW interrupt flag in FDCAN_IR. Write access resets the counter to 0.
When TSS[1:0] = 10, TSC[15:0] reflects the external timestamp counter value. A write
access has no impact.


_Note:_ _A “wrap around” is a change of the timestamp counter value from non-0 to 0 that is not_
_caused by write access to FDCAN_TSCV._


**28.4.10** **FDCAN timeout counter configuration register (FDCAN_TOCC)**


Address offset: 0x0028


Reset value: 0xFFFF 0000

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2 1|Col15|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TOS[1:0]|TOS[1:0]|ETOC|
||||||||||||||rw|rw|rw|



Bits 31:16 **TOP[15:0]** : Timeout period

Start value of the timeout counter (down-counter). Configures the timeout period.
This bitfield is write-protected (P), write access is possible only when the CCE and INIT bits of
the FDCAN_CCCR register are both set.


Bits 15:3 Reserved, must be kept at reset value.


Bits 2:1 **TOS[1:0]** : Timeout select

When operating in continuous mode, a write to FDCAN_TOCV presets the counter to the
value configured by TOP[15:0] in FDCAN_TOCC and continues down-counting. When the
timeout counter is controlled by one of the FIFOs, an empty FIFO presets the counter to the
value configured by TOP[15:0]. Down-counting is started when the first FIFO element is
stored.

00: Continuous operation
01: Timeout controlled by Tx event FIFO
10: Timeout controlled by Rx FIFO 0
11: Timeout controlled by Rx FIFO 1
This bitfield is write-protected (P), write access is possible only when the CCE and INIT bits of
the FDCAN_CCCR register are both set.


Bit 0 **ETOC** : Timeout counter enable

0: Timeout counter disabled

1: Timeout counter enabled

This bit is write-protected (P), write access is possible only when the CCE and INIT bits of the
FDCAN_CCCR register are both set.


For more details, see _Timeout counter_ .


RM0490 Rev 5 927/1027



952


**FD controller area network (FDCAN)** **RM0490**


**28.4.11** **FDCAN timeout counter value register (FDCAN_TOCV)**


Address offset: 0x002C


Reset value: 0x0000 FFFF

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|
|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|rc_w|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **TOC[15:0]** : Timeout counter

The timeout counter is decremented in multiples of CAN bit times [1 … 16] depending on the
configuration of the TCP[3:0] bitfield of the FDCAN_TSCC register. When decremented to 0,
the TOO interrupt flag is set in FDCAN_IR and the timeout counter is stopped. Start and
reset/restart conditions are configured via TOS[1:0] in FDCAN_TOCC.


**28.4.12** **FDCAN error counter register (FDCAN_ECR)**


Address offset: 0x0040


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23 22 21 20 19 18 17 16|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CEL[7:0]|CEL[7:0]|CEL[7:0]|CEL[7:0]|CEL[7:0]|CEL[7:0]|CEL[7:0]|CEL[7:0]|
|||||||||rc_r|rc_r|rc_r|rc_r|rc_r|rc_r|rc_r|rc_r|


|15|14 13 12 11 10 9 8|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|RP|REC[6:0]|REC[6:0]|REC[6:0]|REC[6:0]|REC[6:0]|REC[6:0]|REC[6:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:24 Reserved, must be kept at reset value.


Bits 23:16 **CEL[7:0]** : CAN error logging

The counter is incremented each time when a CAN protocol error causes the transmit error
counter or the receive error counter to be incremented. It is reset by read access to CEL[7:0].
The counter stops at 0xFF; the next increment of TEC[7:0] or REC[6:0] sets the ELO
interrupt flag in FDCAN_IR.
Access type is rc_r: cleared on read.


Bit 15 **RP** : Receive error passive

0: The receive error counter is below the error passive level of 128.
1: The receive error counter has reached the error passive level of 128.


Bits 14:8 **REC[6:0]:** Receive error counter

Actual state of the receive error counter, values between 0 and 127.


Bits 7:0 **TEC[7:0]** : Transmit error counter

Actual state of the transmit error counter, values between 0 and 255.

When the ASM bit of the FDCAN_CCCR is set, the CAN protocol controller does not
increment TEC and REC when a CAN protocol error is detected, but CEL[7:0] is still
incremented.


928/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**28.4.13** **FDCAN protocol status register (FDCAN_PSR)**


Address offset: 0x0044


Reset value: 0x0000 0707

|31|30|29|28|27|26|25|24|23|22 21 20 19 18 17 16|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TDCV[6:0]|TDCV[6:0]|TDCV[6:0]|TDCV[6:0]|TDCV[6:0]|TDCV[6:0]|TDCV[6:0]|
||||||||||r|r|r|r|r|r|r|


|15|14|13|12|11|10 9 8|Col7|Col8|7|6|5|4 3|Col13|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|PXE|REDL|RBRS|RESI|DLEC[2:0]|DLEC[2:0]|DLEC[2:0]|BO|EW|EP|ACT[1:0]|ACT[1:0]|LEC[2:0]|LEC[2:0]|LEC[2:0]|
||rc_r|rc_r|rc_r|rc_r|rs|rs|rs|r|r|r|r|r|rs|rs|rs|



Bits 31:23 Reserved, must be kept at reset value.


Bits 22:16 **TDCV[6:0]** : Transmitter delay compensation value

Position of the secondary sample point, defined by the sum of the measured delay from
FDCAN_TX to FDCAN_RX and TDCO[6:0] in FDCAN_TDCR. The SSP position is, in the
data phase, the number of minimum time quanta (m t q ) between the start of the transmitted bit
and the secondary sample point. Valid values are 0 to 127 × m t q .


Bit 15 Reserved, must be kept at reset value.


Bit 14 **PXE** : Protocol exception event

0: No protocol exception event occurred since last read access
1: Protocol exception event occurred


Bit 13 **REDL** : Received FDCAN message

This bit is set independent of acceptance filtering.
0: Since this bit was cleared by the CPU, no FDCAN message has been received.
1: Message in FDCAN format with EDL flag set has been received.
Access type is rc_r: cleared on read.


Bit 12 **RBRS:** BRS flag of last received FDCAN message

This bit is set together with REDL, independent of acceptance filtering.
0: Last received FDCAN message did not have its BRS flag set.
1: Last received FDCAN message had its BRS flag set.
Access type is rc_r: cleared on read.


Bit 11 **RESI** : ESI flag of last received FDCAN message

This bit is set together with REDL, independent of acceptance filtering.
0: Last received FDCAN message did not have its ESI flag set.
1: Last received FDCAN message had its ESI flag set.
Access type is rc_r: cleared on read.


Bits 10:8 **DLEC[2:0]** : Data last error code

Type of last error that occurred in the data phase of a FDCAN format frame with its BRS flag
set. Coding is the same as for LEC[2:0]. This field is cleared when a FDCAN format frame
with its BRS flag set has been transferred (reception or transmission) without error.
Access type is rs: set on read.


Bit 7 **BO** : Bus-off status

0: The FDCAN is not in bus-off state.

1: The FDCAN is in bus-off state.


RM0490 Rev 5 929/1027



952


**FD controller area network (FDCAN)** **RM0490**


Bit 6 **EW** : Warning status

0: Both error counters are below the error-warning limit of 96.
1: At least one of error counter has reached the error-warning limit of 96.


Bit 5 **EP** : Error passive

0: The FDCAN is in the error-active state. It normally takes part in bus communication and
sends an active error flag when an error has been detected.
1: The FDCAN is in the error-passive state.


Bits 4:3 **ACT[1:0]** : Activity

Monitors the module’s CAN communication state.

00: Synchronizing: node is synchronizing on CAN communication.

01: Idle: node is neither receiver nor transmitter.

10: Receiver: node is operating as receiver.
11: Transmitter: node is operating as transmitter.


Bits 2:0 **LEC[2:0]:** Last error code

LEC[2:0] indicates the type of the last error to occur on the CAN bus. This bitfield is cleared
when a message has been transferred (reception or transmission) without error.
000: No error occurred since LEC[2:0] has been cleared by successful reception or
transmission.

001: Stuff error. More than five equal bits in a sequence have occurred in a part of a received
message where this is not allowed.
010: Form error. A fixed format part of a received frame has the wrong format.
011: Ack error. The message transmitted by the FDCAN was not acknowledged by another
node.

100: Bit1 error. During the transmission of a message (with the exception of the arbitration
field), the device wanted to send a recessive level (bit of logical value 1), but the monitored
bus value was dominant.

101: Bit0 error. During the transmission of a message (or acknowledge bit, or active error
flag, or overload flag), the device wanted to send a dominant level (data or identifier bit logical
value 0), but the monitored bus value was recessive. During bus-off recovery this status is set
each time a sequence of 11 recessive bits has been monitored. This enables the CPU to
monitor the proceeding of the bus-off recovery sequence (indicating the bus is not stuck at
dominant or continuously disturbed).
110: CRC error. The CRC check sum of a received message was incorrect. The CRC of an
incoming message does not match with the CRC calculated from the received data.
111: No change. Any read access to the protocol status register reinitializes LEC[2:0] to 7.
When the LEC[2:0] shows the value 7, no CAN bus event was detected since the last CPU
read access to the protocol status register.
Access type is rs: set on read.


_Note:_ _When a frame in FDCAN format has reached the data phase with the BRS flag set, the next_
_CAN event (error or valid frame) is shown in DLEC[2:0] instead of LEC[2:0]. An error in a_
_fixed stuff bit of an FDCAN CRC sequence is shown as a form error, not as a stuff error._


_The bus-off recovery sequence (see CAN Specification Rev. 2.0 or ISO11898-1) cannot be_
_shortened by setting or clearing the INIT bit of the FDCAN_CCCR register. If the device_
_enters bus-off, it sets the INIT bit of its own, stopping all bus activities. Once INIT has been_
_cleared by the CPU, the device waits for 129 occurrences of bus-idle (129 × 11 consecutive_
_recessive bits) before resuming normal operation. At the end of the bus-off recovery_
_sequence, the error management counters are reset. During the waiting time after clearing_
_INIT, each time a sequence of 11 recessive bits has been monitored, a bit0 error code is_
_written to LEC[2:0] of FDCAN_PSR, enabling the CPU to check up whether the CAN bus is_


930/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


_stuck at dominant or continuously disturbed, and to monitor the bus-off recovery sequence._
_The REC[6:0] bitfield of the FDCAN_ECR register is used to count these sequences._


**28.4.14** **FDCAN transmitter delay compensation register (FDCAN_TDCR)**


Address offset: 0x0048


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14 13 12 11 10 9 8|Col3|Col4|Col5|Col6|Col7|Col8|7|6 5 4 3 2 1 0|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|TDCO[6:0]|TDCO[6:0]|TDCO[6:0]|TDCO[6:0]|TDCO[6:0]|TDCO[6:0]|TDCO[6:0]|Res.|TDCF[6:0]|TDCF[6:0]|TDCF[6:0]|TDCF[6:0]|TDCF[6:0]|TDCF[6:0]|TDCF[6:0]|
||rw|rw|rw|rw|rw|rw|rw||rw|rw|rw|rw|rw|rw|rw|



Bits 31:15 Reserved, must be kept at reset value.


Bits 14:8 **TDCO[6:0]** : Transmitter delay compensation offset

Offset value defining the distance between the measured delay from FDCAN_TX to
FDCAN_RX and the secondary sample point. Valid values are 0 to 127 × m t q .
This bitfield is write-protected (P), which means that write access is possible only when the
CCE and INIT bits of the FDCAN_CCCR register are both set.


Bit 7 Reserved, must be kept at reset value.


Bits 6:0 **TDCF[6:0]** : Transmitter delay compensation filter window length

Defines the minimum value for the SSP position, dominant edges on FDCAN_RX that would
result in an earlier SSP position are ignored for transmitter delay measurements.
This bitfield is write-protected (P), which means that write access is possible only when the
CCE and INIT bits of the FDCAN_CCCR register are both set.


**28.4.15** **FDCAN interrupt register (FDCAN_IR)**


The flags are set when one of the listed conditions is detected (edge-sensitive). The flags
remain set until the host clears them. A flag is cleared by writing 1 to the corresponding bit
position.


Writing 0 has no effect. A hard reset clears the register. The configuration of FDCAN_IE
controls whether an interrupt is generated. The configuration of FDCAN_ILS controls on
which interrupt line an interrupt is signaled.


Address offset: 0x0050


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ARA|PED|PEA|WDI|BO|EW|EP|ELO|
|||||||||rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TOO|MRAF|TSW|TEFL|TEFF|TEFN|TFE|TCF|TC|HPM|RF1L|RF1F|RF1N|RF0L|RF0F|RF0N|
|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|



Bits 31:24 Reserved, must be kept at reset value.


RM0490 Rev 5 931/1027



952


**FD controller area network (FDCAN)** **RM0490**


Bit 23 **ARA** : Access to reserved address

0: No access to reserved address occurred

1: Access to reserved address occurred


Bit 22 **PED** : Protocol error in data phase (data bit time is used)

0: No protocol error in data phase
1: Protocol error in data phase detected (DLEC[2:0] different from 0 and 7 in FDCAN_PSR)


Bit 21 **PEA** : Protocol error in arbitration phase (nominal bit time is used)

0: No protocol error in arbitration phase
1: Protocol error in arbitration phase detected (LEC[2:0] different from 0 and 7 in
FDCAN_PSR)


Bit 20 **WDI** : Watchdog interrupt

0: No message RAM watchdog event occurred
1: Message RAM watchdog event due to missing READY


Bit 19 **BO** : Bus-off status

0: Bus-off status unchanged
1: Bus-off status changed


Bit 18 **EW** : Warning status

0: Error-warning status unchanged
1: Error-warning status changed


Bit 17 **EP** : Error passive

0: Error-passive status unchanged
1: Error-passive status changed


Bit 16 **ELO** : Error logging overflow

0: CAN error logging counter did not overflow.
1: Overflow of CAN error logging counter occurred.


Bit 15 **TOO** : Timeout occurred

0: No timeout

1: Timeout reached


Bit 14 **MRAF** : Message RAM access failure

The flag is set when the Rx handler:

                  has not completed acceptance filtering or storage of an accepted message until the
arbitration field of the following message has been received. In this case acceptance
filtering or message storage is aborted and the Rx handler starts processing of the
following message.

                  was unable to write a message to the message RAM. In this case message storage is
aborted.

In both cases the FIFO put index is not updated. The partly stored message is overwritten
when the next message is stored to this location.
The flag is also set when the Tx handler was not able to read a message from the message
RAM in time. In this case message transmission is aborted. In case of a Tx handler access
failure, the FDCAN is switched into restricted operation mode (see _Restricted operation_
_mode_ ). To leave restricted operation mode, the host CPU has to clear the ASM of the
FDCAN_CCCR register.
0: No message RAM access failure occurred
1: Message RAM access failure occurred


932/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


Bit 13 **TSW** : Timestamp wraparound

0: No timestamp counter wrap-around
1: Timestamp counter wrapped around


Bit 12 **TEFL** : Tx event FIFO element lost

0: No Tx event FIFO element lost

1: Tx event FIFO element lost


Bit 11 **TEFF** : Tx event FIFO full

0: Tx event FIFO Not full

1: Tx event FIFO full


Bit 10 **TEFN** : Tx event FIFO new entry

0: Tx event FIFO unchanged

1: Tx handler wrote Tx event FIFO element.


Bit 9 **TFE** : Tx FIFO empty

0: Tx FIFO non-empty
1: Tx FIFO empty


Bit 8 **TCF** : Transmission cancellation finished

0: No transmission cancellation finished

1: Transmission cancellation finished


Bit 7 **TC** : Transmission completed

0: No transmission completed
1: Transmission completed


Bit 6 **HPM** : High-priority message

0: No high-priority message received
1: High-priority message received


Bit 5 **RF1L** : Rx FIFO 1 message lost

0: No Rx FIFO 1 message lost
1: Rx FIFO 1 message lost


Bit 4 **RF1F** : Rx FIFO 1 full

0: Rx FIFO 1 not full

1: Rx FIFO 1 full


Bit 3 **RF1N** : Rx FIFO 1 new message

0: No new message written to Rx FIFO 1
1: New message written to Rx FIFO 1


Bit 2 **RF0L** : Rx FIFO 0 message lost

0: No Rx FIFO 0 message lost
1: Rx FIFO 0 message lost


Bit 1 **RF0F** : Rx FIFO 0 full

0: Rx FIFO 0 not full

1: Rx FIFO 0 full


Bit 0 **RF0N** : Rx FIFO 0 new message

0: No new message written to Rx FIFO 0
1: New message written to Rx FIFO 0


RM0490 Rev 5 933/1027



952


**FD controller area network (FDCAN)** **RM0490**


**28.4.16** **FDCAN interrupt enable register (FDCAN_IE)**


The settings in the interrupt enable register determine which status changes in the interrupt
register are signaled on an interrupt line.


Address offset: 0x0054


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ARAE|PEDE|PEAE|WDIE|BOE|EWE|EPE|ELOE|
|||||||||rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TOOE|MRAFE|TSWE|TEFLE|TEFFE|TEFNE|TFEE|TCFE|TCE|HPME|RF1LE|RF1FE|RF1NE|RF0LE|RF0FE|RF0NE|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:24 Reserved, must be kept at reset value.


Bit 23 **ARAE** : Access to reserved address enable


Bit 22 **PEDE** : Protocol error in data phase enable


Bit 21 **PEAE** : Protocol error in arbitration phase enable


Bit 20 **WDIE** : Watchdog interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 19 **BOE** : Bus-off status

0: Interrupt disabled
1: Interrupt enabled


Bit 18 **EWE** : Warning status interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 17 **EPE** : Error passive interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 16 **ELOE** : Error logging overflow interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 15 **TOOE** : Timeout occurred interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 14 **MRAFE:** Message RAM access failure interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 13 **TSWE** : Timestamp wraparound interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 12 **TEFLE** : Tx event FIFO element lost interrupt enable

0: Interrupt disabled
1: Interrupt enabled


934/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


Bit 11 **TEFFE** : Tx event FIFO full interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 10 **TEFNE** : Tx event FIFO new entry interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 9 **TFEE** : Tx FIFO empty interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 8 **TCFE** : Transmission cancellation finished interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 7 **TCE** : Transmission completed interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 6 **HPME** : High-priority message interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 5 **RF1LE** : Rx FIFO 1 message lost interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 4 **RF1FE** : Rx FIFO 1 full interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 3 **RF1NE** : Rx FIFO 1 new message interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 2 **RF0LE** : Rx FIFO 0 message lost interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 1 **RF0FE** : Rx FIFO 0 full interrupt enable

0: Interrupt disabled
1: Interrupt enabled


Bit 0 **RF0NE** : Rx FIFO 0 new message interrupt enable

0: Interrupt disabled
1: Interrupt enabled


RM0490 Rev 5 935/1027



952


**FD controller area network (FDCAN)** **RM0490**


**28.4.17** **FDCAN interrupt line select register (FDCAN_ILS)**


This register assigns an interrupt generated by a specific group of interrupt flags from the
interrupt register to one of the two module interrupt lines. For interrupt generation, the
respective interrupt line has to be enabled via the EINT0 and EINT1 bit of the FDCAN_ILE
register.


Address offset: 0x0058


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PERR|BERR|MISC|TFERR|SMSG|RXFIF<br>O1|RXFIF<br>O0|
||||||||||rw|rw|rw|rw|rw|rw|rw|



Bits 31:7 Reserved, must be kept at reset value.


Bit 6 **PERR:** Protocol error grouping the following interruption

ARAL: Access to reserved address line

PEDL: Protocol error in data phase line
PEAL: Protocol error in arbitration phase line
WDIL: Watchdog interrupt line

BOL: Bus-off status

EWL: Warning status interrupt line


Bit 5 **BERR:** Bit and line error grouping the following interruption

EPL Error passive interrupt line
ELOL: Error logging overflow interrupt line


Bit 4 **MISC:** Interrupt regrouping the following interruption

TOOL: Timeout occurred interrupt line
MRAFL: Message RAM access failure interrupt line
TSWL: Timestamp wraparound interrupt line


Bit 3 **TFERR:** Tx FIFO ERROR grouping the following interruption

TEFLL: Tx event FIFO element lost interrupt line
TEFFL: Tx event FIFO full interrupt line
TEFNL: Tx event FIFO new entry interrupt line
TFEL: Tx FIFO empty interrupt line


Bit 2 **SMSG:** Status message bit grouping the following interruption

TCFL: Transmission cancellation finished interrupt line
TCL: Transmission completed interrupt line
HPML: High-priority message interrupt line


Bit 1 **RXFIFO1:** RX FIFO bit grouping the following interruption

RF1LL: Rx FIFO 1 message lost interrupt line
RF1FL: Rx FIFO 1 full interrupt line
RF1NL: Rx FIFO 1 new message interrupt line


936/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


Bit 0 **RXFIFO0:** RX FIFO bit grouping the following interruption

RF0LL: Rx FIFO 0 message lost interrupt line
RF0FL: Rx FIFO 0 full interrupt line
RF0NL: Rx FIFO 0 new message interrupt line


**28.4.18** **FDCAN interrupt line enable register (FDCAN_ILE)**


Each of the two interrupt lines to the CPU can be enabled/disabled separately by
programming the EINT0 and EINT1 bits.


Address offset: 0x005C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EINT1|EINT0|
|||||||||||||||rw|rw|



Bits 31:2 Reserved, must be kept at reset value.


Bit 1 **EINT1** : Enable interrupt line 1

0: Interrupt line fdcan_intr0_it disabled
1: Interrupt line fdcan_intr0_it enabled


Bit 0 **EINT0** : Enable interrupt line 0

0: Interrupt line fdcan_intr1_it disabled
1: Interrupt line fdcan_intr1_it enabled


**28.4.19** **FDCAN global filter configuration register (FDCAN_RXGFC)**


Global settings for message ID filtering. The global filter configuration controls the filter path
for standard and extended messages as described in _Figure 324_ and _Figure 325_ .


Address offset: 0x0080


Reset value: 0x0000 0000

|31|30|29|28|27 26 25 24|Col6|Col7|Col8|23|22|21|20 19 18 17 16|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|LSE[3:0]|LSE[3:0]|LSE[3:0]|LSE[3:0]|Res.|Res.|Res.|LSS[4:0]|LSS[4:0]|LSS[4:0]|LSS[4:0]|LSS[4:0]|
|||||rw|rw|rw|rw||||rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5 4|Col12|3 2|Col14|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|F0OM|F1OM|Res.|Res.|ANFS[1:0]|ANFS[1:0]|ANFE[1:0]|ANFE[1:0]|RRFS|RRFE|
|||||||rw|rw|||rw|rw|rw|rw|rw|rw|



Bits 31:28 Reserved, must be kept at reset value.


RM0490 Rev 5 937/1027



952


**FD controller area network (FDCAN)** **RM0490**


Bits 27:24 **LSE[3:0]** : Number of extended filter elements in the list

0: No extended message ID filter
1 to 8: Number of extended message ID filter elements

            - 8: Values greater than 8 are interpreted as 8.
This bitfield is write-protected (P), which means that write access is possible only when the
CCE and INIT bits of the FDCAN_CCCR register are both set.


Bits 23:21 Reserved, must be kept at reset value.


Bits 20:16 **LSS[4:0]** : Number of standard filter elements in the list

0: No standard message ID filter
1 to 28: Number of standard message ID filter elements

            - 28: Values greater than 28 are interpreted as 28.
This bitfield is write protected (P), which means that write access by the bits is possible only
when the CCE and INIT bits of the FDCAN_CCCR register are both set.


Bits 15:10 Reserved, must be kept at reset value.


Bit 9 **F0OM** : FIFO 0 operation mode (overwrite or blocking)

This bit is write-protected (P), which means that write access is possible only when the CCE
and INIT bits of the FDCAN_CCCR register are both set.


Bit 8 **F1OM** : FIFO 1 operation mode (overwrite or blocking)

This bit is write-protected (P), which means that write access is possible only when the CCE
and INIT bits of the FDCAN_CCCR register are both set.


Bits 7:6 Reserved, must be kept at reset value.


Bits 5:4 **ANFS[1:0]** : Accept Non-matching frames standard

Defines how received messages with 11-bit IDs that do not match any element of the filter list
are treated.

00: Accept in Rx FIFO 0
01: Accept in Rx FIFO 1
10: Reject
11: Reject
This bitfield is write-protected (P), which means write access is possible only when the CCE
and INIT bits of the FDCAN_CCCR register are both set.


Bits 3:2 **ANFE[1:0]** : Accept non-matching frames extended

Defines how received messages with 29-bit IDs that do not match any element of the filter list
are treated.

00: Accept in Rx FIFO 0
01: Accept in Rx FIFO 1
10: Reject
11: Reject
This bitfield is write-protected (P), which means that write access is possible only when the
CCE and INIT bits of the FDCAN_CCCR register are both set.


Bit 1 **RRFS** : Reject remote frames standard

0: Filter remote frames with 11-bit standard IDs

1: Reject all remote frames with 11-bit standard IDs
This bit is write-protected (P), which means that write access is possible only when the CCE
and INIT bits of the FDCAN_CCCR register are both set.


938/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


Bit 0 **RRFE** : Reject remote frames extended

0: Filter remote frames with 29-bit standard IDs

1: Reject all remote frames with 29-bit standard IDs
This bit is write-protected (P), which means that write access is possible only when the CCE
and INIT bits of the FDCAN_CCCR register are both set.


**28.4.20** **FDCAN extended ID and mask register (FDCAN_XIDAM)**


Address offset: 0x0084


Reset value: 0x1FFF FFFF

|31|30|29|28 27 26 25 24 23 22 21 20 19 18 17 16|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|EIDM[28:16]|EIDM[28:16]|EIDM[28:16]|EIDM[28:16]|EIDM[28:16]|EIDM[28:16]|EIDM[28:16]|EIDM[28:16]|EIDM[28:16]|EIDM[28:16]|EIDM[28:16]|EIDM[28:16]|EIDM[28:16]|
||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|EIDM[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:29 Reserved, must be kept at reset value.


Bits 28:0 **EIDM[28:0]** : Extended ID mask

For acceptance filtering of extended frames the extended ID AND mask is AND-ed with the
message ID of a received frame. Intended for masking of 29-bit IDs in SAE J1939. With the
reset value of all bits set, the mask is not active.
This bitfield is write-protected (P), which means that write access is possible only when the
CCE and INIT bits of the FDCAN_CCCR register are both set.


**28.4.21** **FDCAN high-priority message status register (FDCAN_HPMS)**


This register is updated every time a message ID filter element configured to generate a
priority event match. This can be used to monitor the status of incoming high priority
messages and to enable fast access to these messages.


Address offset: 0x0088


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12 11 10 9 8|Col5|Col6|Col7|Col8|7 6|Col10|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|FLST|Res.|Res.|FIDX[4:0]|FIDX[4:0]|FIDX[4:0]|FIDX[4:0]|FIDX[4:0]|MSI[1:0]|MSI[1:0]|Res.|Res.|Res.|BIDX[2:0]|BIDX[2:0]|BIDX[2:0]|
|r|||r|r|r|r|r|r|r||||r|r|r|



Bits 31:16 Reserved, must be kept at reset value.


Bit 15 **FLST** : Filter list

Indicates the filter list of the matching filter element:

0: Standard filter list

1: Extended filter list


Bits 14:13 Reserved, must be kept at reset value.


RM0490 Rev 5 939/1027



952


**FD controller area network (FDCAN)** **RM0490**


Bits 12:8 **FIDX[4:0]** : Filter index

Index of matching filter element.
Range: 0 to LSS[4:0] - 1 or LSE[3:0] - 1 in FDCAN_RXGFC.


Bits 7:6 **MSI[1:0]** : Message storage indicator

00: No FIFO selected

01: FIFO overrun

10: Message stored in FIFO 0
11: Message stored in FIFO 1


Bits 5:3 Reserved, must be kept at reset value.


Bits 2:0 **BIDX[2:0]** : Buffer index

Index of Rx FIFO element to which the message was stored. Only valid when MSI[1] = 1.


**28.4.22** **FDCAN Rx FIFO 0 status register (FDCAN_RXF0S)**


Address offset: 0x0090


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17 16|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|RF0L|F0F|Res.|Res.|Res.|Res.|Res.|Res.|F0PI[1:0]|F0PI[1:0]|
|||||||r|r|||||||r|r|


|15|14|13|12|11|10|9 8|Col8|7|6|5|4|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|F0GI[1:0]|F0GI[1:0]|Res.|Res.|Res.|Res.|F0FL[3:0]|F0FL[3:0]|F0FL[3:0]|F0FL[3:0]|
|||||||r|r|||||r|r|r|r|



Bits 31:26 Reserved, must be kept at reset value.


Bit 25 **RF0L** : Rx FIFO 0 message lost

This bit is a copy of the RF0L interrupt flag of the FDCAN_IR register. When RF0L is cleared,
this bit is also cleared.

0: No Rx FIFO 0 message lost
1: Rx FIFO 0 message lost, also set after write attempt to Rx FIFO 0 of size 0


Bit 24 **F0F** : Rx FIFO 0 full

0: Rx FIFO 0 not full

1: Rx FIFO 0 full


Bits 23:18 Reserved, must be kept at reset value.


Bits 17:16 **F0PI[1:0]** : Rx FIFO 0 put index

Rx FIFO 0 write index pointer.
Range: 0 to 2.


Bits 15:10 Reserved, must be kept at reset value.


Bits 9:8 **F0GI[1:0]** : Rx FIFO 0 get index

Rx FIFO 0 read index pointer.
Range: 0 to 2.


Bits 7:4 Reserved, must be kept at reset value.


Bits 3:0 **F0FL[3:0]** : Rx FIFO 0 fill level

Number of elements stored in Rx FIFO 0.

Range: 0 to 3.


940/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**28.4.23** **CAN Rx FIFO 0 acknowledge register (FDCAN_RXF0A)**


Address offset: 0x0094


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|F0AI[2:0]|F0AI[2:0]|F0AI[2:0]|
||||||||||||||rw|rw|rw|



Bits 31:3 Reserved, must be kept at reset value.


Bits 2:0 **F0AI[2:0]** : Rx FIFO 0 acknowledge index

After the host has read a message or a sequence of messages from Rx FIFO 0, it has to
write the buffer index of the last element read from Rx FIFO 0 to F0AI[2:0]. This sets the Rx
FIFO 0 get index (F0GI[1:0] of FDCAN_RXF0S) to F0AI[2:0] + 1 and updates the FIFO 0 fill
level (F0FL[3:0] FDCAN_RXF0S).


**28.4.24** **FDCAN Rx FIFO 1 status register (FDCAN_RXF1S)**


Address offset: 0x0098


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17 16|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|RF1L|F1F|Res.|Res.|Res.|Res.|Res.|Res.|F1PI[1:0]|F1PI[1:0]|
|||||||r|r|||||||r|r|


|15|14|13|12|11|10|9 8|Col8|7|6|5|4|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|F1GI[1:0]|F1GI[1:0]|Res.|Res.|Res.|Res.|F1FL[3:0]|F1FL[3:0]|F1FL[3:0]|F1FL[3:0]|
|||||||r|r|||||r|r|r|r|



Bits 31:26 Reserved, must be kept at reset value.


Bit 25 **RF1L** : Rx FIFO 1 message lost

This bit is a copy of the RF1L interrupt flag of the FDCAN_IR register. When RF1L is cleared,
this bit is also cleared.

0: No Rx FIFO 1 message lost
1: Rx FIFO 1 message lost, also set after write attempt to Rx FIFO 1 of size 0


Bit 24 **F1F** : Rx FIFO 1 full

0: Rx FIFO 1 not full

1: Rx FIFO 1 full


Bits 23:18 Reserved, must be kept at reset value.


Bits 17:16 **F1PI[1:0]** : Rx FIFO 1 put index

Rx FIFO 1 write index pointer.
Range: 0 to 2.


Bits 15:10 Reserved, must be kept at reset value.


RM0490 Rev 5 941/1027



952


**FD controller area network (FDCAN)** **RM0490**


Bits 9:8 **F1GI[1:0]** : Rx FIFO 1 get index

Rx FIFO 1 read index pointer.
Range: 0 to 2.


Bits 7:4 Reserved, must be kept at reset value.


Bits 3:0 **F1FL[3:0]** : Rx FIFO 1 fill level

Number of elements stored in Rx FIFO 1.

Range: 0 to 3.


**28.4.25** **FDCAN Rx FIFO 1 acknowledge register (FDCAN_RXF1A)**


Address offset: 0x009C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|F1AI[2:0]|F1AI[2:0]|F1AI[2:0]|
||||||||||||||rw|rw|rw|



Bits 31:3 Reserved, must be kept at reset value.


Bits 2:0 **F1AI[2:0]** : Rx FIFO 1 acknowledge index

After the host has read a message or a sequence of messages from Rx FIFO 1, it has to
write the buffer index of the last element read from Rx FIFO 1 to F1AI[2:0]. This sets the Rx
FIFO 1 get index (F1GI[1:0] of FDCAN_RXF1S) to F1AI[2:0] + 1 and updates the FIFO 1 fill
level (F1FL[3:0] FDCAN_RXF1S).


**28.4.26** **FDCAN Tx buffer configuration register (FDCAN_TXBC)**


Address offset: 0x00C0


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TFQM|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
||||||||rw|||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||



Bits 31:25 Reserved, must be kept at reset value.


Bit 24 **TFQM** : Tx FIFO/queue mode

0: Tx FIFO operation
1: Tx queue operation.
This bit is write-protected (P), which means that write access is possible only when the CCE
and INIT bits of the FDCAN_CCCR register are both set.


Bits 23:0 Reserved, must be kept at reset value.


942/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**28.4.27** **FDCAN Tx FIFO/queue status register (FDCAN_TXFQS)**


The Tx FIFO/queue status is related to the pending Tx requests listed in the
FDCAN_TXBRP register. Therefore, the effect of add/cancellation requests can be delayed
due to a running Tx scan (FDCAN_TXBRP not yet updated).


Address offset: 0x00C4


Reset value: 0x0000 0003

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17 16|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TFQF|Res.|Res.|Res.|TFQPI[1:0]|TFQPI[1:0]|
|||||||||||r||||r|r|


|15|14|13|12|11|10|9 8|Col8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|TFGI[1:0]|TFGI[1:0]|Res.|Res.|Res.|Res.|Res.|TFFL[2:0]|TFFL[2:0]|TFFL[2:0]|
|||||||r|r||||||r|r|r|



Bits 31:22 Reserved, must be kept at reset value.


Bit 21 **TFQF** : Tx FIFO/queue full

0: Tx FIFO/queue not full
1: Tx FIFO/queue full


Bits 20:18 Reserved, must be kept at reset value.


Bits 17:16 **TFQPI[1:0]** : Tx FIFO/queue put index

Tx FIFO/queue write index pointer, range 0 to 3


Bits 15:10 Reserved, must be kept at reset value.


Bits 9:8 **TFGI[1:0]** : Tx FIFO get index

Tx FIFO read index pointer, range 0 to 3. Read as 0 when Tx queue operation is configured
(TFQM = 1 in FDCAN_TXBC)


Bits 7:3 Reserved, must be kept at reset value.


Bits 2:0 **TFFL[2:0]** : Tx FIFO free level

Number of consecutive free Tx FIFO elements starting from TFGI, range 0 to 3. Read as 0
when Tx queue operation is configured (TFQM = 1 in FDCAN_TXBC).


**28.4.28** **FDCAN Tx buffer request pending register (FDCAN_TXBRP)**


Address offset: 0x00C8


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TRP[2:0]|TRP[2:0]|TRP[2:0]|
||||||||||||||r|r|r|



Bits 31:3 Reserved, must be kept at reset value.


RM0490 Rev 5 943/1027



952


**FD controller area network (FDCAN)** **RM0490**


Bits 2:0 **TRP[2:0]** : Transmission request pending

Each Tx buffer has its own transmission request pending bit. The bits are set via the
FDCAN_TXBAR register. The bits are cleared after a requested transmission has completed
or has been canceled via the FDCAN_TXBCR register.
After the FDCAN_TXBRP bit has been set, a Tx scan is started to check for the pending Tx
request with the highest priority (Tx buffer with lowest message ID).
A cancellation request resets the corresponding transmission request pending bit of the
FDCAN_TXBRP register. In case a transmission has already been started when a
cancellation is requested, this is done at the end of the transmission, regardless whether the
transmission was successful or not. The cancellation request bits are directly cleared after the
corresponding FDCAN_TXBRP bit has been cleared.
After a cancellation has been requested, a finished cancellation is signaled via the
FDCAN_TXBCF in the following cases:

–
after successful transmission together with the corresponding TXBTO bit

–
when the transmission has not yet been started at the point of cancellation

– when the transmission has been aborted due to lost arbitration

–
when an error occurred during frame transmission
In DAR mode, all transmissions are automatically canceled if they are not successful. The
corresponding FDCAN_TXBCF bit is set for all unsuccessful transmissions.
0: No transmission request pending
1: Transmission request pending


_Note:_ _FDCAN_TXBRP bits set while a Tx scan is in progress are not considered during this_
_particular Tx scan. In case a cancellation is requested for such a Tx buffer, this add request_
_is canceled immediately. The corresponding FDCAN_TXBRP bit is cleared._


**28.4.29** **FDCAN Tx buffer add request register (FDCAN_TXBAR)**


Address offset: 0x00CC


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|AR[2:0]|AR[2:0]|AR[2:0]|
||||||||||||||rw|rw|rw|



Bits 31:3 Reserved, must be kept at reset value.


Bits 2:0 **AR[2:0]** : Add request

Each Tx buffer has its own add request bit. Writing a 1 sets the corresponding add request
bit; writing a 0 has no impact. This enables the host to set transmission requests for multiple
Tx buffers with one write to FDCAN_TXBAR. When no Tx scan is running, the bits are
cleared immediately, else the bits remain set until the Tx scan process has completed.
0: No transmission request added
1: Transmission requested added.


_Note:_ _If an add request is applied for a Tx buffer with pending transmission request_
_(corresponding FDCAN_TXBRP bit already set), the request is ignored._


944/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**28.4.30** **FDCAN Tx buffer cancellation request register (FDCAN_TXBCR)**


Address offset: 0x00D0


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CR[2:0]|CR[2:0]|CR[2:0]|
||||||||||||||rw|rw|rw|



Bits 31:3 Reserved, must be kept at reset value.


Bits 2:0 **CR[2:0]** : Cancellation request

Each Tx buffer has its own cancellation request bit. Writing a 1 sets the corresponding CR bit;
writing a 0 has no impact.
This enables the host to set cancellation requests for multiple Tx buffers with one write to
FDCAN_TXBCR. The bits remain set until the corresponding FDCAN_TXBRP bit is cleared.
0: No cancellation pending
1: Cancellation pending


**28.4.31** **FDCAN Tx buffer transmission occurred register (FDCAN_TXBTO)**


Address offset: 0x00D4


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TO[2:0]|TO[2:0]|TO[2:0]|
||||||||||||||r|r|r|



Bits 31:3 Reserved, must be kept at reset value.


Bits 2:0 **TO[2:0]** : Transmission occurred.

Each Tx buffer has its own TO bit. The bits are set when the corresponding FDCAN_TXBRP
bit is cleared after a successful transmission. The bits are cleared when a new transmission

is requested by writing a 1 to the corresponding bit of register FDCAN_TXBAR.

0: No transmission occurred

1: Transmission occurred


RM0490 Rev 5 945/1027



952


**FD controller area network (FDCAN)** **RM0490**


**28.4.32** **FDCAN Tx buffer cancellation finished register (FDCAN_TXBCF)**


Address offset: 0x00D8


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CF[2:0]|CF[2:0]|CF[2:0]|
||||||||||||||r|r|r|



Bits 31:3 Reserved, must be kept at reset value.


Bits 2:0 **CF[2:0]** : Cancellation finished

Each Tx buffer has its own CF bit. The bits are set when the corresponding FDCAN_TXBRP
bit is cleared after a cancellation was requested via FDCAN_TXBCR. In case the
corresponding FDCAN_TXBRP bit was not set at the point of cancellation, CF is set
immediately. The bits are cleared when a new transmission is requested by writing a 1 to the
corresponding bit of the FDCAN_TXBAR register.

0: No transmit buffer cancellation

1: Transmit buffer cancellation finished


**28.4.33** **FDCAN Tx buffer transmission interrupt enable register**
**(FDCAN_TXBTIE)**


Address offset: 0x00DC


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIE[2:0]|TIE[2:0]|TIE[2:0]|
||||||||||||||rw|rw|rw|



Bits 31:3 Reserved, must be kept at reset value.


Bits 2:0 **TIE[2:0]** : Transmission interrupt enable

Each Tx buffer has its own TIE bit.

0: Transmission interrupt disabled
1: Transmission interrupt enable


946/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**28.4.34** **FDCAN Tx buffer cancellation finished interrupt enable register**
**(FDCAN_TXBCIE)**


Address offset: 0x00E0


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CFIE[2:0]|CFIE[2:0]|CFIE[2:0]|
||||||||||||||rw|rw|rw|



Bits 31:3 Reserved, must be kept at reset value.


Bits 2:0 **CFIE[2:0]** : Cancellation finished interrupt enable.

Each Tx buffer has its own CFIE bit.

0: Cancellation finished interrupt disabled
1: Cancellation finished interrupt enabled


**28.4.35** **FDCAN Tx event FIFO status register (FDCAN_TXEFS)**


Address offset: 0x00E4


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17 16|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|TEFL|EFF|Res.|Res.|Res.|Res.|Res.|Res.|EFPI[1:0]|EFPI[1:0]|
|||||||r|r|||||||r|r|


|15|14|13|12|11|10|9 8|Col8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|EFGI[1:0]|EFGI[1:0]|Res.|Res.|Res.|Res.|Res.|EFFL[2:0]|EFFL[2:0]|EFFL[2:0]|
|||||||r|r||||||r|r|r|



Bits 31:26 Reserved, must be kept at reset value.


Bit 25 **TEFL** : Tx event FIFO element lost

This bit is a copy of the TEFL interrupt flag of the FDCAN_IR. When TEFL is cleared, this bit
is also cleared.

0 No Tx event FIFO element lost

1 Tx event FIFO element lost, also set after write attempt to Tx event FIFO of size 0.


Bit 24 **EFF** : Event FIFO full

0: Tx event FIFO not full

1: Tx event FIFO full


Bits 23:18 Reserved, must be kept at reset value.


Bits 17:16 **EFPI[1:0]** : Event FIFO put index

Tx event FIFO write index pointer.
Range: 0 to 3.


Bits 15:10 Reserved, must be kept at reset value.


RM0490 Rev 5 947/1027



952


**FD controller area network (FDCAN)** **RM0490**


Bits 9:8 **EFGI[1:0]** : Event FIFO get index

Tx event FIFO read index pointer.
Range: 0 to 3.


Bits 7:3 Reserved, must be kept at reset value.


Bits 2:0 **EFFL[2:0]** : Event FIFO fill level

Number of elements stored in Tx event FIFO.

Range: 0 to 3.


**28.4.36** **FDCAN Tx event FIFO acknowledge register (FDCAN_TXEFA)**


Address offset: 0x00E8


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EFAI[1:0]|EFAI[1:0]|
|||||||||||||||rw|rw|



Bits 31:2 Reserved, must be kept at reset value.


Bits 1:0 **EFAI[1:0]** : Event FIFO acknowledge index

After the host has read an element or a sequence of elements from the Tx event FIFO, it has
to write the index of the last element read from Tx event FIFO to EFAI[1:0]. This sets the Tx
event FIFO get index (EFGI[1:0] of FDCAN_TXEFS) to EFAI[1:0] + 1 and updates the FIFO 0
fill level (EFFL[2:0] of FDCAN_TXEFS).


**28.4.37** **FDCAN CFG clock divider register (FDCAN_CKDIV)**


Address offset: 0x0100


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PDIV[3:0]|PDIV[3:0]|PDIV[3:0]|PDIV[3:0]|
|||||||||||||rw|rw|rw|rw|



Bits 31:4 Reserved, must be kept at reset value.


948/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


Bits 3:0 **PDIV[3:0]** : input clock divider

The CAN kernel clock can be divided prior to be used by the CAN subsystem. The rate must
be computed using the divider output clock.
0000: Divide by 1
0001: Divide by 2
0010: Divide by 4
0011: Divide by 6
0100: Divide by 8
0101: Divide by 10
0110: Divide by 12
0111: Divide by 14
1000: Divide by 16
1001: Divide by 18
1010: Divide by 20
1011: Divide by 22
1100: Divide by 24
1101: Divide by 26
1110: Divide by 28
1111: Divide by 30
This bitfield is write-protected (P): which means that write access is possible only when the
CCE bit of the FDCAN_CCCR register is set.

_Note: The clock divider is common to all FDCAN instances. Only FDCAN1 instance has_
_FDCAN_CKDIV register, which changes clock divider for all instances._


**28.4.38** **FDCAN register map**


**Table 153. FDCAN register map and reset values**







|Offset|Register name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x0000|FDCAN_CREL|REL[3:0]|REL[3:0]|REL[3:0]|REL[3:0]|STEP[3:0]|STEP[3:0]|STEP[3:0]|STEP[3:0]|SUBSTEP [3:0]|SUBSTEP [3:0]|SUBSTEP [3:0]|SUBSTEP [3:0]|YEAR[3:0]|YEAR[3:0]|YEAR[3:0]|YEAR[3:0]|MON[7:0]|MON[7:0]|MON[7:0]|MON[7:0]|MON[7:0]|MON[7:0]|MON[7:0]|MON[7:0]|DAY[7:0]|DAY[7:0]|DAY[7:0]|DAY[7:0]|DAY[7:0]|DAY[7:0]|DAY[7:0]|DAY[7:0]|
|0x0000|Reset value|0|0|0|0|0|0|0|1|1|1|1|0|1|0|1|0|0|1|1|0|1|1|1|1|1|0|1|0|0|0|1|0|
|0x0004|FDCAN_ENDN|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|ETV[31:0]|
|0x0004|Reset value|1|0|0|0|0|1|1|1|0|1|1|0|0|1|0|1|0|1|0|0|0|0|1|1|0|0|1|0|0|0|0|1|
|0x0008|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x000C|FDCAN_DBTP|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TDC|Res.|Res.|DBRP[4:0]|DBRP[4:0]|DBRP[4:0]|DBRP[4:0]|DBRP[4:0]|Res.|Res|Res.|DTSEG1[4:0]|DTSEG1[4:0]|DTSEG1[4:0]|DTSEG1[4:0]|DTSEG1[4:0]|DTSEG2[3:0]|DTSEG2[3:0]|DTSEG2[3:0]|DTSEG2[3:0]|DSJW[3:0]|DSJW[3:0]|DSJW[3:0]|DSJW[3:0]|
|0x000C|Reset value|||||||||0|0|0|0|0|0|0|0||||0|1|0|1|0|0|0|1|1|0|0|1|1|
|0x0010|FDCAN_TEST|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RX|TX[1:0]|TX[1:0]|LBCK|Res.|Res.|Res.|Res.|
|0x0010|Reset value|||||||||||||||||||||||||0|0|0|0|||||
|0x0014|FDCAN_RWD|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|WDV[7:0]|WDV[7:0]|WDV[7:0]|WDV[7:0]|WDV[7:0]|WDV[7:0]|WDV[7:0]|WDV[7:0]|WDC[7:0]|WDC[7:0]|WDC[7:0]|WDC[7:0]|WDC[7:0]|WDC[7:0]|WDC[7:0]|WDC[7:0]|
|0x0014|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


RM0490 Rev 5 949/1027



952


**FD controller area network (FDCAN)** **RM0490**


**Table 153. FDCAN register map and reset values (continued)**



































|Offset|Register name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x0018|FDCAN_CCCR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|NISO|TXP|EFBI|PXHD|Res.|Res.|BRSE|FDOE|TEST|DAR|MON|CSR|CSA|ASM|CCE|INT|
|0x0018|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|1|
|0x001C|FDCAN_NBTP|NSJW[6:0]|NSJW[6:0]|NSJW[6:0]|NSJW[6:0]|NSJW[6:0]|NSJW[6:0]|NSJW[6:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NBRP[8:0]|NTSEG1[7:0]|NTSEG1[7:0]|NTSEG1[7:0]|NTSEG1[7:0]|NTSEG1[7:0]|NTSEG1[7:0]|NTSEG1[7:0]|NTSEG1[7:0]|Res.|NTSEG2[6:0]|NTSEG2[6:0]|NTSEG2[6:0]|NTSEG2[6:0]|NTSEG2[6:0]|NTSEG2[6:0]|NTSEG2[6:0]|
|0x001C|Reset value|0|0|0|0|0|1|1|0|0|0|0|0|0|0|0|0|0|0|0|0|1|0|1|0|0|0|0|0|0|0|1|1|
|0x0020|FDCAN_TSCC|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TCP[3:0]|TCP[3:0]|TCP[3:0]|TCP[3:0]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TSS[1:0]|TSS[1:0]|
|0x0020|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0024|FDCAN_TSCV|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|TSC[15:0]|
|0x0024|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0028|FDCAN_TOCC|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|TOP[15:0]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TOS[1:0]|TOS[1:0]|ETOC|
|0x0028|Reset value|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x002C|FDCAN_TOCV|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|TOC[15:0]|
|0x002C|Reset value|||||||||||||||||1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|
|0x0030-<br>0x003C|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x0040|FDCAN_ECR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CEL[7:0]|CEL[7:0]|CEL[7:0]|CEL[7:0]|CEL[7:0]|CEL[7:0]|CEL[7:0]|CEL[7:0]|RP|REC[6:0]|REC[6:0]|REC[6:0]|REC[6:0]|REC[6:0]|REC[6:0]|REC[6:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|
|0x0040|Reset value|||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0044|FDCAN_PSR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TDCV[6:0]|TDCV[6:0]|TDCV[6:0]|TDCV[6:0]|TDCV[6:0]|TDCV[6:0]|TDCV[6:0]|Res.|PXE|REDL|RBRSRESI1|RESI|DLEC[2:0]|DLEC[2:0]|DLEC[2:0]|BO|EW|EP|ACT[1:0]|ACT[1:0]|LEC[2;0]|LEC[2;0]|LEC[2;0]|
|0x0044|Reset value||||||||||0|0|0|0|0|0|0||0|0|0|0|0|0|0|0|0|0|0|0|1|1|1|
|0x0048|FDCAN_TDCR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TDCO[6:0]|TDCO[6:0]|TDCO[6:0]|TDCO[6:0]|TDCO[6:0]|TDCO[6:0]|TDCO[6:0]|Res.|TDCF[6:0]|TDCF[6:0]|TDCF[6:0]|TDCF[6:0]|TDCF[6:0]|TDCF[6:0]|TDCF[6:0]|
|0x0048|Reset value||||||||||||||||||0|0|0|0|0|0||0|0|0|0|0|0|0|0|
|0x004C|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x0050|FDCAN_IR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ARA|PED|PEA|WDI|BO|EW|EP|ELO|TOO|MRAF|TSW|TEFL|TEFF|TEFN|TFE|TCF|TC|HPM|RF1L|RF1F|RF1N|RF0L|RF0F|RF0N|
|0x0050|Reset value|||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0054|FDCAN_IE|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ARAE|PEDE|PEAE|WDIE|BOE|EWE|EPE|ELOE|TOOE|MRAFE|TSWE|TEFLE|TEFFE|TEFNE|TFEE|TCFE|TCE|HPME|RF1LE|RF1FE|RF1NE|RF0LE|RF0FE|RF0NE|
|0x0054|Reset value|||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0058|FDCAN_ILS|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PERR|BERR|MISC|TFERR|SMSG|RXFIFO1|RXFIFO0|
|0x0058|Reset value|0|||||||||||||||||||||||||0|0|0|0|0|0|0|


950/1027 RM0490 Rev 5


**RM0490** **FD controller area network (FDCAN)**


**Table 153. FDCAN register map and reset values (continued)**































|Offset|Register name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x005C|FDCAN_ILE|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EINT1|EINT0|
|0x005C|Reset value|||||||||||||||||||||||||||||||0|0|
|0x0060-<br>0x007C|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x0080|FDCAN<br>_RXGFC|Res.|Res.|Res.|Res.|LSE[3:0].|LSE[3:0].|LSE[3:0].|LSE[3:0].|Res.|Res.|Res.|LSS[4:0]|LSS[4:0]|LSS[4:0]|LSS[4:0]|LSS[4:0]|Res.|Res.|Res.|Res.|Res.|Res.|F0OM|F1OM|Res.|Res.|ANFS[1:0]|ANFS[1:0]|ANFE[1:0]|ANFE[1:0]|RRFS|RRFE|
|0x0080|Reset value|||||0|0|0|0||||0|0|0|0|0|||||||0|0|||0|0|0|0|0|0|
|0x0084|FDCAN<br>_XIDAM|Res.|Res.|Res.|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|EIDM[28:0]|
|0x0084|Reset value||||1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|
|0x0088|FDCAN_HPMS|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FLST|Res.|Res.|FIDX[4:0]|FIDX[4:0]|FIDX[4:0]|FIDX[4:0]|FIDX[4:0]|MSI[1:0]|MSI[1:0]|Res.|Res.|Res.|BIDX[2:0]|BIDX[2:0]|BIDX[2:0]|
|0x0088|Reset value|||||||||||||||||0|||0|0|0|0|0|0|0||||0|0|0|
|0x0090|FDCAN<br>_RXF0S|Res.|Res.|Res.|Res.|Res.|Res.|RF0L|F0F|Res.|Res.|Res.|Res.|Res.|Res.|F0PI[1:0]|F0PI[1:0]|Res.|Res.|Res.|Res.|Res.|Res.|F0GI[1:0]|F0GI[1:0]|Res.|Res.|Res.|Res.|F0FL[3:0]|F0FL[3:0]|F0FL[3:0]|F0FL[3:0]|
|0x0090|Reset value|||||||0|0|||||||0|0|||||||0|0|||||0|0|0|0|
|0x0094|FDCAN<br>_RXF0A|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|F0AI[2:0]|F0AI[2:0]|F0AI[2:0]|
|0x0094|Reset value||||||||||||||||||||||||||||||0|0|0|
|0x0098|FDCAN<br>_RXF1S|Res.|Res.|Res.|Res.|Res.|Res.|RF1L|F1F|Res.|Res.|Res.|Res.|Res.|Res.|F1PI[1:0]|F1PI[1:0]|Res.|Res.|Res.|Res.|Res.|Res.|F1GI[1:0]|F1GI[1:0]|Res.|Res.|Res.|Res.|F1FL[3:0]|F1FL[3:0]|F1FL[3:0]|F1FL[3:0]|
|0x0098|Reset value|||||||0|0|||||||0|0|||||||0|0|||||0|0|0|0|
|0x009C|FDCAN<br>_RXF1A|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|F1AI[2:0]|F1AI[2:0]|F1AI[2:0]|
|0x009C|Reset value||||||||||||||||||||||||||||||0|0|0|
|0x00A0-<br>0x00BC|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x00C0|FDCAN<br>_TXBC|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TFQM|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x00C0|Reset value||||||||0|0||||||||||||||||||||||||
|0x00C4|FDCAN<br>_TXFQS|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TFQF|Res.|Res.|Res.|TFQPI[1:0]|TFQPI[1:0]|Res.|Res.|Res.|Res.|Res.|Res.|TFGI[1:0]|TFGI[1:0]|Res.|Res.|Res.|Res.|Res.|TFFL[2:0]|TFFL[2:0]|TFFL[2:0]|
|0x00C4|Reset value|||||||||||0||||0|0|||||||0|0||||||0|1|1|
|0x00C8|FDCAN<br>_TXBRP|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TRP2|TRP1|TRP0|
|0x00C8|Reset value||||||||||||||||||||||||||||||0|0|0|


RM0490 Rev 5 951/1027



952


**FD controller area network (FDCAN)** **RM0490**


**Table 153. FDCAN register map and reset values (continued)**











|Offset|Register name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00CC|FDCAN<br>_TXBAR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|AR2|AR1|AR0|
|0x00CC|Reset value||||||||||||||||||||||||||||||0|0|0|
|0x00D0|FDCAN<br>_TXBCR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CR2|CR1|CR0|
|0x00D0|Reset value||||||||||||||||||||||||||||||0|0|0|
|0x00D4|FDCAN<br>_TXBTO|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TO2|TO1|TO0|
|0x00D4|Reset value||||||||||||||||||||||||||||||0|0|0|
|0x00D8|FDCAN<br>_TXBCF|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CF2|CF1|CF0|
|0x00D8|Reset value||||||||||||||||||||||||||||||0|0|0|
|0x00DC|FDCAN<br>_TXBTIE|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TIE2|TIE1|TIE0|
|0x00DC|Reset value||||||||||||||||||||||||||||||0|0|0|
|0x00E0|FDCAN<br>_TXBCIE|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CFIE2|CFIE1|CFIE0|
|0x00E0|Reset value||||||||||||||||||||||||||||||0|0|0|
|0x00E4|FDCAN<br>_TXEFS|Res.|Res.|Res.|Res.|Res.|Res.|TEFL|EFF|Res.|Res.|Res.|Res.|Res.|Res.|EFPI[1:0]|EFPI[1:0]|Res.|Res.|Res.|Res.|Res.|Res.|EFG[1:0]|EFG[1:0]|Res.|Res.|Res.|Res.|Res.|EFFL[2:0]|EFFL[2:0]|EFFL[2:0]|
|0x00E4|Reset value|||||||0|0|||||||0|0|||||||0|0||||||0|0|0|
|0x00E8|FDCAN<br>_TXEFA|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EFAI[1:0]|EFAI[1:0]|
|0x00E8|Reset value|||||||||||||||||||||||||||||||0|0|
|0x0100|FDCAN<br>_CKDIV|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PDIV[3:0]|PDIV[3:0]|PDIV[3:0]|PDIV[3:0]|
|0x0100|Reset value|||||||||||||||||||||||||||||0|0|0|0|


Refer to _Section 2.2_ for the register boundary addresses.


952/1027 RM0490 Rev 5


