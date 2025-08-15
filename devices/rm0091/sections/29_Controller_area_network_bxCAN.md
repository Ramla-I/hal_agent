**RM0091** **Controller area network (bxCAN)**

# **29 Controller area network (bxCAN)**

## **29.1 Introduction**


The **Basic Extended CAN** peripheral, named **bxCAN**, interfaces the CAN network. It
supports the CAN protocols version 2.0A and B. It has been designed to manage a high
number of incoming messages efficiently with a minimum CPU load. It also meets the
priority requirements for transmit messages.


For safety-critical applications, the CAN controller provides all hardware functions for
supporting the CAN Time Triggered Communication option.

## **29.2 bxCAN main features**


      - Supports CAN protocol version 2.0 A, B Active


      - Bit rates up to 1 Mbit/s


      - Supports the Time Triggered Communication option


Transmission


      - Three transmit mailboxes


      - Configurable transmit priority


      - Time stamp on SOF transmission


Reception


      - Two receive FIFOs with three stages


      - Scalable filter banks:


–
14 filter banks for single CAN


      - Identifier list feature


      - Configurable FIFO overrun


      - Time stamp on SOF reception


Time-triggered communication option


      - Disable automatic retransmission mode


      - 16-bit free running timer


      - Time stamp sent in last two data bytes


Management


      - Maskable interrupts


      - Software-efficient mailbox mapping at a unique address space

## **29.3 bxCAN general description**


In today CAN applications, the number of nodes in a network is increasing and often several
networks are linked together via gateways. Typically the number of messages in the system
(to be handled by each node) has significantly increased. In addition to the application
messages, network management and diagnostic messages have been introduced.


      - An enhanced filtering mechanism is required to handle each type of message.


RM0091 Rev 10 825/1017



867


**Controller area network (bxCAN)** **RM0091**


Furthermore, application tasks require more CPU time, therefore real-time constraints
caused by message reception have to be reduced.


      - A receive FIFO scheme allows the CPU to be dedicated to application tasks for a long
time period without losing messages.


The standard HLP (Higher Layer Protocol) based on standard CAN drivers requires an
efficient interface to the CAN controller.


**Figure 311. CAN network topology**


**29.3.1** **CAN 2.0B active core**


The bxCAN module handles the transmission and the reception of CAN messages fully
autonomously. Standard identifiers (11-bit) and extended identifiers (29-bit) are fully
supported by hardware.


**29.3.2** **Control, status and configuration registers**


The application uses these registers to:


      - Configure CAN parameters, e.g. baud rate


      - Request transmissions


      - Handle receptions


      - Manage interrupts


      - Get diagnostic information


**29.3.3** **Tx mailboxes**


Three transmit mailboxes are provided to the software for setting up messages. The
transmission scheduler decides which mailbox has to be transmitted first.


**29.3.4** **Acceptance filters**


The bxCAN provides up to 14 scalable/configurable identifier filter banks in single CAN
configuration, for selecting the incoming messages, that the software needs and discarding
the others.


826/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


**Receive FIFO**



Two receive FIFOs are used by hardware to store the incoming messages. Three complete
messages can be stored in each FIFO. The FIFOs are managed completely by hardware.


**Figure 312. Single-CAN block diagram**












|Col1|Col2|Col3|Col4|2|
|---|---|---|---|---|
|||ailbo x 0<br>1|ailbo x 0<br>1|2|
|Mailbo x 0|Mailbo x 0|ailbo x 0|ailbo x 0|ailbo x 0|
|Mailbo x 0|Mailbo x 0|ailbo x 0|||


|Col1|Col2|Col3|Col4|2|
|---|---|---|---|---|
|||ailbox 0<br>1|ailbox 0<br>1|2|
|Mailbox 0|Mailbox 0|ailbox 0|ailbox 0|ailbox 0|
|Mailbox 0|Mailbox 0|ailbox 0|||














## **29.4 bxCAN operating modes**

bxCAN has three main operating modes: **initialization**, **normal** and **Sleep** . After a
hardware reset, bxCAN is in Sleep mode to reduce power consumption and an internal pullup is active on CANTX. The software requests bxCAN to enter **initialization** or **Sleep** mode
by setting the INRQ or SLEEP bits in the CAN_MCR register. Once the mode has been
entered, bxCAN confirms it by setting the INAK or SLAK bits in the CAN_MSR register and
the internal pull-up is disabled. When neither INAK nor SLAK are set, bxCAN is in **normal**
mode. Before entering **normal** mode bxCAN always has to **synchronize** on the CAN bus.
To synchronize, bxCAN waits until the CAN bus is idle, this means 11 consecutive recessive
bits have been monitored on CANRX.



**29.4.1** **Initialization mode**


The software initialization can be done while the hardware is in Initialization mode. To enter
this mode the software sets the INRQ bit in the CAN_MCR register and waits until the
hardware has confirmed the request by setting the INAK bit in the CAN_MSR register.



To leave Initialization mode, the software clears the INQR bit. bxCAN has left Initialization
mode once the INAK bit has been cleared by hardware.


While in Initialization Mode, all message transfers to and from the CAN bus are stopped and
the status of the CAN bus output CANTX is recessive (high).



Entering Initialization Mode does not change any of the configuration registers.


To initialize the CAN Controller, software has to set up the Bit Timing (CAN_BTR) and CAN
options (CAN_MCR) registers.



RM0091 Rev 10 827/1017



867


**Controller area network (bxCAN)** **RM0091**


To initialize the registers associated with the CAN filter banks (mode, scale, FIFO
assignment, activation and filter values), software has to set the FINIT bit (CAN_FMR). Filter
initialization also can be done outside the initialization mode.


_Note:_ _When FINIT=1, CAN reception is deactivated._


_The filter values also can be modified by deactivating the associated filter activation bits (in_
_the CAN_FA1R register)._


_If a filter bank is not used, it is recommended to leave it non active (leave the corresponding_
_FACT bit cleared)._


For code example refer to the Appendix section _A.11.1: bxCAN initialization mode code_
_example_ .


**29.4.2** **Normal mode**


Once the initialization is complete, the software must request the hardware to enter Normal
mode to be able to synchronize on the CAN bus and start reception and transmission.


The request to enter Normal mode is issued by clearing the INRQ bit in the CAN_MCR
register. The bxCAN enters Normal mode and is ready to take part in bus activities when it
has synchronized with the data transfer on the CAN bus. This is done by waiting for the
occurrence of a sequence of 11 consecutive recessive bits (Bus Idle state). The switch to
Normal mode is confirmed by the hardware by clearing the INAK bit in the CAN_MSR
register.


The initialization of the filter values is independent from Initialization Mode but must be done
while the filter is not active (corresponding FACTx bit cleared). The filter scale and mode
configuration must be configured before entering Normal Mode.


**29.4.3** **Sleep mode (low-power)**


To reduce power consumption, bxCAN has a low-power mode called Sleep mode. This
mode is entered on software request by setting the SLEEP bit in the CAN_MCR register. In
this mode, the bxCAN clock is stopped, however software can still access the bxCAN
mailboxes.


If software requests entry to **initialization** mode by setting the INRQ bit while bxCAN is in
**Sleep** mode, it must also clear the SLEEP bit.


bxCAN can be woken up (exit Sleep mode) either by software clearing the SLEEP bit or on
detection of CAN bus activity.


On CAN bus activity detection, hardware automatically performs the wake-up sequence by
clearing the SLEEP bit if the AWUM bit in the CAN_MCR register is set. If the AWUM bit is
cleared, software has to clear the SLEEP bit when a wake-up interrupt occurs, in order to
exit from Sleep mode.


_Note:_ _If the wake-up interrupt is enabled (WKUIE bit set in CAN_IER register) a wake-up interrupt_
_is generated on detection of CAN bus activity, even if the bxCAN automatically performs the_
_wake-up sequence._


After the SLEEP bit has been cleared, Sleep mode is exited once bxCAN has synchronized
with the CAN bus, refer to _Figure 313_ . The Sleep mode is exited once the SLAK bit has
been cleared by hardware.


828/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


**Figure 313. bxCAN operating modes**













1. ACK = The wait state during which hardware confirms a request by setting the INAK or SLAK bits in the
CAN_MSR register.


2. SYNC = The state during which bxCAN waits until the CAN bus is idle, meaning 11 consecutive recessive
bits have been monitored on CANRX.


## **29.5 Test mode**

Test mode can be selected by the SILM and LBKM bits in the CAN_BTR register. These bits
must be configured while bxCAN is in Initialization mode. Once test mode has been
selected, the INRQ bit in the CAN_MCR register must be reset to enter Normal mode.



**29.5.1** **Silent mode**


The bxCAN can be put in Silent mode by setting the SILM bit in the CAN_BTR register.


In Silent mode, the bxCAN is able to receive valid data frames and valid remote frames, but
sends only recessive bits on the CAN bus and cannot start a transmission. If the bxCAN has
to send a dominant bit (ACK bit, overload flag, active error flag), the bit is rerouted internally
so that the CAN Core monitors this dominant bit, although the CAN bus may remain in
recessive state. Silent mode can be used to analyze the traffic on a CAN bus without
affecting it by the transmission of dominant bits (Acknowledge bits, Error frames).


RM0091 Rev 10 829/1017



867


**Controller area network (bxCAN)** **RM0091**


**Figure 314. bxCAN in silent mode**


**29.5.2** **Loop back mode**


The bxCAN can be set in Loop Back Mode by setting the LBKM bit in the CAN_BTR
register. In Loop Back Mode, the bxCAN treats its own transmitted messages as received
messages and stores them (if they pass acceptance filtering) in a Receive mailbox.


**Figure 315. bxCAN in loop back mode**


This mode is provided for self-test functions. To be independent of external events, the CAN
Core ignores acknowledge errors (no dominant bit sampled in the acknowledge slot of a
data / remote frame) in Loop Back Mode. In this mode, the bxCAN performs an internal
feedback from its Tx output to its Rx input. The actual value of the CANRX input pin is
disregarded by the bxCAN. The transmitted messages can be monitored on the CANTX pin.


**29.5.3** **Loop back combined with silent mode**


It is also possible to combine Loop back mode and Silent mode by setting the LBKM and
SILM bits in the CAN_BTR register. This mode can be used for a “Hot Selftest”, meaning the
bxCAN can be tested like in Loop back mode but without affecting a running CAN system
connected to the CANTX and CANRX pins. In this mode, the CANRX pin is disconnected
from the bxCAN and the CANTX pin is held recessive.


830/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


**Figure 316. bxCAN in combined mode**

## **29.6 Behavior in debug mode**


When the microcontroller enters the debug mode (Cortex [®] -M0 core halted), the bxCAN
continues to work normally or stops, depending on:


      - the DBG_CAN1_STOP bit in the DBG module for the single mode.


      - the DBF bit in CAN_MCR. For more details, refer to _Section 29.9.2: CAN control and_
_status registers_ .

## **29.7 bxCAN functional description**


**29.7.1** **Transmission handling**


In order to transmit a message, the application must select one **empty** transmit mailbox, set
up the identifier, the data length code (DLC) and the data before requesting the transmission
by setting the corresponding TXRQ bit in the CAN_TIxR register. Once the mailbox has left
**empty** state, the software no longer has write access to the mailbox registers. Immediately
after the TXRQ bit has been set, the mailbox enters **pending** state and waits to become the
highest priority mailbox, see _Transmit Priority_ . As soon as the mailbox has the highest
priority it is **scheduled** for transmission. The transmission of the message of the scheduled
mailbox starts (enter **transmit** state) when the CAN bus becomes idle. Once the mailbox
has been successfully transmitted, it becomes **empty** again. The hardware indicates a
successful transmission by setting the RQCP and TXOK bits in the CAN_TSR register.


If the transmission fails, the cause is indicated by the ALST bit in the CAN_TSR register in
case of an Arbitration Lost, and/or the TERR bit, in case of transmission error detection.


For code example refer to the Appendix section _A.11.2: bxCAN transmit code example_ .


**Transmit priority**


By identifier


When more than one transmit mailbox is pending, the transmission order is given by the
identifier of the message stored in the mailbox. The message with the lowest identifier value
has the highest priority according to the arbitration of the CAN protocol. If the identifier
values are equal, the lower mailbox number is scheduled first.


RM0091 Rev 10 831/1017



867


**Controller area network (bxCAN)** **RM0091**


By transmit request order


The transmit mailboxes can be configured as a transmit FIFO by setting the TXFP bit in the
CAN_MCR register. In this mode the priority order is given by the transmit request order.


This mode is very useful for segmented transmission.


**Abort**


A transmission request can be aborted by the user setting the ABRQ bit in the CAN_TSR
register. In **pending** or **scheduled** state, the mailbox is aborted immediately. An abort
request while the mailbox is in **transmit** state can have two results. If the mailbox is
transmitted successfully the mailbox becomes **empty** with the TXOK bit set in the
CAN_TSR register. If the transmission fails, the mailbox becomes **scheduled,** the
transmission is aborted and becomes **empty** with TXOK cleared. In all cases the mailbox
becomes **empty** again at least at the end of the current transmission.


**Non automatic retransmission mode**


This mode has been implemented in order to fulfill the requirement of the Time Triggered
Communication option of the CAN standard. To configure the hardware in this mode the
NART bit in the CAN_MCR register must be set.


In this mode, each transmission is started only once. If the first attempt fails, due to an
arbitration loss or an error, the hardware does not automatically restart the message
transmission.


At the end of the first transmission attempt, the hardware considers the request as
completed and sets the RQCP bit in the CAN_TSR register. The result of the transmission is
indicated in the CAN_TSR register by the TXOK, ALST and TERR bits.


**Figure 317. Transmit mailbox states**



































832/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


**29.7.2** **Time triggered communication mode**


In this mode, the internal counter of the CAN hardware is activated and used to generate the
time stamp value stored in the CAN_RDTxR/CAN_TDTxR registers, respectively (for Rx
and Tx mailboxes). The internal counter is incremented each CAN bit time (refer to
_Section 29.7.7_ ). The internal counter is captured on the sample point of the Start Of Frame
bit in both reception and transmission.


**29.7.3** **Reception handling**


For the reception of CAN messages, three mailboxes organized as a FIFO are provided. In
order to save CPU load, simplify the software and guarantee data consistency, the FIFO is
managed completely by hardware. The application accesses the messages stored in the
FIFO through the FIFO output mailbox.


**Valid message**


A received message is considered as valid **when** it has been received correctly according to
the CAN protocol (no error until the last but one bit of the EOF field) **and** It passed through
the identifier filtering successfully, see _Section 29.7.4_ .


**Figure 318. Receive FIFO states**













RM0091 Rev 10 833/1017



867


**Controller area network (bxCAN)** **RM0091**


**FIFO management**


Starting from the **empty** state, the first valid message received is stored in the FIFO which
becomes **pending_1** . The hardware signals the event setting the FMP[1:0] bits in the
CAN_RFR register to the value 01b. The message is available in the FIFO output mailbox.
The software reads out the mailbox content and releases it by setting the RFOM bit in the
CAN_RFR register. The FIFO becomes **empty** again. If a new valid message has been
received in the meantime, the FIFO stays in **pending_1** state and the new message is
available in the output mailbox.


For code example refer to the Appendix section _A.11.3: bxCAN receive code example_ .


If the application does not release the mailbox, the next valid message is stored in the FIFO
which enters **pending_2** state (FMP[1:0] = 10b). The storage process is repeated for the
next valid message putting the FIFO into **pending_3** state (FMP[1:0] = 11b). At this point,
the software must release the output mailbox by setting the RFOM bit, so that a mailbox is
free to store the next valid message. Otherwise the next valid message received causes a
loss of message. Refer also to _Section 29.7.5_ .


**Overrun**


Once the FIFO is in **pending_3** state (i.e. the three mailboxes are full) the next valid
message reception leads to an **overrun** and a message is lost. The hardware signals the
overrun condition by setting the FOVR bit in the CAN_RFR register. Which message is lost
depends on the configuration of the FIFO:


      - If the FIFO lock function is disabled (RFLM bit in the CAN_MCR register cleared) the
last message stored in the FIFO is overwritten by the new incoming message. In this
case the latest messages are always available to the application.


      - If the FIFO lock function is enabled (RFLM bit in the CAN_MCR register set) the most
recent message is discarded and the software has the three oldest messages in the
FIFO available.


**Reception related interrupts**


Once a message has been stored in the FIFO, the FMP[1:0] bits are updated and an
interrupt request is generated if the FMPIE bit in the CAN_IER register is set.


When the FIFO becomes full (i.e. a third message is stored) the FULL bit in the CAN_RFR
register is set and an interrupt is generated if the FFIE bit in the CAN_IER register is set.


On overrun condition, the FOVR bit is set and an interrupt is generated if the FOVIE bit in
the CAN_IER register is set.


**29.7.4** **Identifier filtering**


In the CAN protocol the identifier of a message is not associated with the address of a node
but related to the content of the message. Consequently a transmitter broadcasts its
message to all receivers. On message reception a receiver node decides - depending on
the identifier value - whether the software needs the message or not. If the message is
needed, it is copied into the SRAM. If not, the message must be discarded without
intervention by the software.


To fulfill this requirement the bxCAN Controller provides 14 configurable and scalable filter
banks (13-0) to the application, in order to receive only the messages the software needs.


834/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


This hardware filtering saves CPU resources which would be otherwise needed to perform
filtering by software. Each filter bank x consists of two 32-bit registers, CAN_FxR0 and
CAN_FxR1.


**Scalable width**


To optimize and adapt the filters to the application needs, each filter bank can be scaled
independently. Depending on the filter scale a filter bank provides:


      - One 32-bit filter for the STDID[10:0], EXTID[17:0], IDE and RTR bits.


      - Two 16-bit filters for the STDID[10:0], RTR, IDE and EXTID[17:15] bits.


Refer to _Figure 319_ .


Furthermore, the filters can be configured in mask mode or in identifier list mode.


**Mask mode**


In **mask** mode the identifier registers are associated with mask registers specifying which
bits of the identifier are handled as “must match” or as “don’t care”.


**Identifier list mode**


In **identifier list** mode, the mask registers are used as identifier registers. Thus instead of
defining an identifier and a mask, two identifiers are specified, doubling the number of single
identifiers. All bits of the incoming identifier must match the bits specified in the filter
registers.


**Filter bank scale and mode configuration**


The filter banks are configured by means of the corresponding CAN_FMR register. To
configure a filter bank it must be deactivated by clearing the FACT bit in the CAN_FAR
register. The filter scale is configured by means of the corresponding FSCx bit in the
CAN_FS1R register, refer to _Figure 319_ . The **identifier list** or **identifier mask** mode for the
corresponding Mask/Identifier registers is configured by means of the FBMx bits in the
CAN_FMR register.


To filter a group of identifiers, configure the Mask/Identifier registers in mask mode.


To select single identifiers, configure the Mask/Identifier registers in identifier list mode.


Filters not used by the application should be left deactivated.


Each filter within a filter bank is numbered (called the _Filter Number_ ) from 0 to a maximum
dependent on the mode and the scale of each of the filter banks.


Concerning the filter configuration, refer to _Figure 319_ .


RM0091 Rev 10 835/1017



867


**Controller area network (bxCAN)** **RM0091**
























|CAN_FxR1[31:24]|CAN_FxR1[23:16]|CAN_FxR1[15:8]|CAN_FxR1[7:0]|Col5|Col6|Col7|
|---|---|---|---|---|---|---|
|CAN_FxR2[31:24]|CAN_FxR2[23:16]|CAN_FxR2[15:8]|CAN_FxR2[7:0]|CAN_FxR2[7:0]|CAN_FxR2[7:0]|CAN_FxR2[7:0]|
|STID[10:3]|STID[2:0]|STID[2:0]|STID[2:0]|STID[2:0]|STID[2:0]|STID[2:0]|
|EXTID[28:21]|EXID[20:13]|EXID[12:5]|EXID[4:0]|IDE|RTR|0|
















|Filters - Identifier List|Col2|Col3|Col4|Col5|Col6|Col7|
|---|---|---|---|---|---|---|
|CAN_FxR1[31:24]|CAN_FxR1[23:16]|CAN_FxR1[15:8]|CAN_FxR1[7:0]|CAN_FxR1[7:0]|CAN_FxR1[7:0]|CAN_FxR1[7:0]|
|CAN_FxR2[31:24]|CAN_FxR2[23:16]|CAN_FxR2[15:8]|CAN_FxR2[7:0]|CAN_FxR2[7:0]|CAN_FxR2[7:0]|CAN_FxR2[7:0]|
|STID[10:3]|STID[2:0]|STID[2:0]|STID[2:0]|STID[2:0]|STID[2:0]|STID[2:0]|
|EXTID[28:21]|EXID[20:13]|EXID[12:5]|EXID[4:0]|IDE|RTR|0|




|Filters - Identifier Mask|Col2|
|---|---|
|CAN_FxR1[15:8]|CAN_FxR1[7:0]|
|CAN_FxR1[31:24]|CAN_FxR1[23:16]|


|CAN_FxR2[15:8]|CAN_FxR2[7:0]|
|---|---|
|CAN_FxR2[31:24]|CAN_FxR2[23:16]|












|Filters - Identifier List|Col2|
|---|---|
|CAN_FxR1[15:8]|CAN_FxR1[7:0]|
|CAN_FxR1[31:24]|CAN_FxR1[23:16]|








|CAN_FxR2[15:8]|CAN_FxR2[7:0]|Col3|Col4|Col5|
|---|---|---|---|---|
|CAN_FxR2[31:24]|CAN_FxR2[23:16]|CAN_FxR2[23:16]|CAN_FxR2[23:16]|CAN_FxR2[23:16]|
|STID[10:3]|STID[2:0]|RTR|IDE<br>|EXID[17:15|







**Filter match index**


Once a message has been received in the FIFO it is available to the application. Typically,
application data is copied into SRAM locations. To copy the data to the right location the
application has to identify the data by means of the identifier. To avoid this, and to ease the
access to the SRAM locations, the CAN controller provides a filter match index.


This index is stored in the mailbox together with the message according to the filter priority
rules. Thus each received message has its associated filter match index.


|Col1|Col2|
|---|---|
|FSCx = 1<br>FSCx = 0<br>Filter Bank Scale<br>Config. Bits<br>1|FBMx = 0|
|FSCx = 1<br>FSCx = 0<br>Filter Bank Scale<br>Config. Bits<br>1||
|FSCx = 1<br>FSCx = 0<br>Filter Bank Scale<br>Config. Bits<br>1|FBMx = 1|
|FSCx = 1<br>FSCx = 0<br>Filter Bank Scale<br>Config. Bits<br>1||
|FSCx = 1<br>FSCx = 0<br>Filter Bank Scale<br>Config. Bits<br>1|FBMx = 0|
|FSCx = 1<br>FSCx = 0<br>Filter Bank Scale<br>Config. Bits<br>1||
|FSCx = 1<br>FSCx = 0<br>Filter Bank Scale<br>Config. Bits<br>1|FBMx = 1|
|FSCx = 1<br>FSCx = 0<br>Filter Bank Scale<br>Config. Bits<br>1|2<br>Filter Bank Mode|



The filter match index can be used in two ways:


- Compare the filter match index with a list of expected values.




- Use the filter match index as an index on an array to access the data destination
location.


For non masked filters, the software no longer has to compare the identifier.



If the filter is masked the software reduces the comparison to the masked bits only.


The index value of the filter number does not take into account the activation state of the
filter banks. In addition, two independent numbering schemes are used, one for each FIFO.
Refer to _Figure 320_ for an example.


836/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


**Figure 320. Example of filter numbering**



























































**Filter priority rules**


Depending on the filter combination it may occur that an identifier passes successfully
through several filters. In this case the filter match value stored in the receive mailbox is
chosen according to the following priority rules:


- A 32-bit filter takes priority over a 16-bit filter.


- For filters of equal scale, priority is given to the Identifier List mode over the Identifier
Mask mode


- For filters of equal scale and mode, priority is given by the filter number (the lower the
number, the higher the priority).


RM0091 Rev 10 837/1017



867


**Controller area network (bxCAN)** **RM0091**


**Figure 321. Filtering mechanism example**










|Identifier|0|
|---|---|
|Identifier|1|
|Identifier|4|
|||
|Identifier|5|


|Message<br>Stored|Col2|Col3|Col4|
|---|---|---|---|
|~~Message~~<br>St~~ored~~|St~~ored~~|St~~ored~~||
|~~Message~~<br>St~~ored~~|St~~ored~~|||
|~~Message~~<br>St~~ored~~||||














|Identifier|2|
|---|---|
|Mask|Mask|
|||
|Identifier|3|
|Mask|Mask|



The example above shows the filtering principle of the bxCAN. On reception of a message,
the identifier is compared first with the filters configured in identifier list mode. If there is a
match, the message is stored in the associated FIFO and the index of the matching filter is
stored in the filter match index. As shown in the example, the identifier matches with
Identifier #2 thus the message content and FMI 2 is stored in the FIFO.


If there is no match, the incoming identifier is then compared with the filters configured in
mask mode.


If the identifier does not match any of the identifiers configured in the filters, the message is
discarded by hardware without disturbing the software.


**29.7.5** **Message storage**


The interface between the software and the hardware for the CAN messages is
implemented by means of mailboxes. A mailbox contains all information related to a
message; identifier, data, control, status and time stamp information.


**Transmit mailbox**


The software sets up the message to be transmitted in an empty transmit mailbox. The
status of the transmission is indicated by hardware in the CAN_TSR register.


838/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


**Table 118. Transmit mailbox mapping**

|Offset to transmit mailbox base address|Register name|
|---|---|
|0|CAN_TIxR|
|4|CAN_TDTxR|
|8|CAN_TDLxR|
|12|CAN_TDHxR|



**Receive mailbox**


When a message has been received, it is available to the software in the FIFO output
mailbox. Once the software has handled the message (e.g. read it) the software must
release the FIFO output mailbox by means of the RFOM bit in the CAN_RFR register to
make the next incoming message available. The filter match index is stored in the MFMI
field of the CAN_RDTxR register. The 16-bit time stamp value is stored in the TIME[15:0]
field of CAN_RDTxR.


**Table 119. Receive mailbox mapping**

|Offset to receive mailbox base address (bytes)|Register name|
|---|---|
|0|CAN_RIxR|
|4|CAN_RDTxR|
|8|CAN_RDLxR|
|12|CAN_RDHxR|



**Figure 322. CAN error state diagram**











**29.7.6** **Error management**


The error management as described in the CAN protocol is handled entirely by hardware
using a Transmit Error Counter (TEC value, in CAN_ESR register) and a Receive Error
Counter (REC value, in the CAN_ESR register), which get incremented or decremented
according to the error condition. For detailed information about TEC and REC management,
refer to the CAN standard.


RM0091 Rev 10 839/1017



867


**Controller area network (bxCAN)** **RM0091**


Both of them may be read by software to determine the stability of the network.
Furthermore, the CAN hardware provides detailed information on the current error status in
CAN_ESR register. By means of the CAN_IER register (ERRIE bit, etc.), the software can
configure the interrupt generation on error detection in a very flexible way.


**Bus-Off recovery**


The Bus-Off state is reached when TEC is greater than 255, this state is indicated by BOFF
bit in CAN_ESR register. In Bus-Off state, the bxCAN is no longer able to transmit and
receive messages.


Depending on the ABOM bit in the CAN_MCR register, bxCAN recovers from Bus-Off
(become error active again) either automatically or on software request. But in both cases
the bxCAN has to wait at least for the recovery sequence specified in the CAN standard
(128 occurrences of 11 consecutive recessive bits monitored on CANRX).


If ABOM is set, the bxCAN starts the recovering sequence automatically after it has entered
Bus-Off state.


If ABOM is cleared, the software must initiate the recovering sequence by requesting
bxCAN to enter and to leave initialization mode.


_Note:_ _In initialization mode, bxCAN does not monitor the CANRX signal, therefore it cannot_
_complete the recovery sequence._ _**To recover, bxCAN must be in normal mode**_ _._


**29.7.7** **Bit timing**


The bit timing logic monitors the serial bus-line and performs sampling and adjustment of
the sample point by synchronizing on the start-bit edge and resynchronizing on the following
edges.


Its operation may be explained simply by splitting nominal bit time into three segments as
follows:


      - **Synchronization segment (SYNC_SEG)** : a bit change is expected to occur within this
time segment. It has a fixed length of one time quantum (1 x t q ).

      - **Bit segment 1 (BS1)** : defines the location of the sample point. It includes the
PROP_SEG and PHASE_SEG1 of the CAN standard. Its duration is programmable
between 1 and 16 time quanta but may be automatically lengthened to compensate for
positive phase drifts due to differences in the frequency of the various nodes of the
network.


      - **Bit segment 2 (BS2)** : defines the location of the transmit point. It represents the
PHASE_SEG2 of the CAN standard. Its duration is programmable between 1 and 8
time quanta but may also be automatically shortened to compensate for negative
phase drifts.


The resynchronization jump width (SJW) defines an upper bound to the amount of
lengthening or shortening of the bit segments. It is programmable between 1 and 4 time
quanta.


A valid edge is defined as the first transition in a bit time from dominant to recessive bus
level provided the controller itself does not send a recessive bit.


If a valid edge is detected in BS1 instead of SYNC_SEG, BS1 is extended by up to SJW so
that the sample point is delayed.


Conversely, if a valid edge is detected in BS2 instead of SYNC_SEG, BS2 is shortened by
up to SJW so that the transmit point is moved earlier.


840/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


As a safeguard against programming errors, the configuration of the Bit timing register
(CAN_BTR) is only possible while the device is in Standby mode.


_Note:_ _For a detailed description of the CAN bit timing and resynchronization mechanism, refer to_
_the ISO 11898 standard._


**Figure 323. Bit timing**


RM0091 Rev 10 841/1017



867


**Controller area network (bxCAN)** **RM0091**


**Figure 324. CAN frames**



















































842/1017 RM0091 Rev 10




**RM0091** **Controller area network (bxCAN)**

## **29.8 bxCAN interrupts**


Four interrupt vectors are dedicated to bxCAN. Each interrupt source can be independently
enabled or disabled by means of the CAN interrupt enable register (CAN_IER).


**Figure 325. Event flags and interrupt generation**





















































RM0091 Rev 10 843/1017



867


**Controller area network (bxCAN)** **RM0091**


      - The **transmit interrupt** can be generated by the following events:


–
Transmit mailbox 0 becomes empty, RQCP0 bit in the CAN_TSR register set.


–
Transmit mailbox 1 becomes empty, RQCP1 bit in the CAN_TSR register set.


–
Transmit mailbox 2 becomes empty, RQCP2 bit in the CAN_TSR register set.


      - The **FIFO 0 interrupt** can be generated by the following events:


–
Reception of a new message, FMP0 bits in the CAN_RF0R register are not ‘00’.


–
FIFO0 full condition, FULL0 bit in the CAN_RF0R register set.


–
FIFO0 overrun condition, FOVR0 bit in the CAN_RF0R register set.


      - The **FIFO 1 interrupt** can be generated by the following events:


–
Reception of a new message, FMP1 bits in the CAN_RF1R register are not ‘00’.


–
FIFO1 full condition, FULL1 bit in the CAN_RF1R register set.


–
FIFO1 overrun condition, FOVR1 bit in the CAN_RF1R register set.


      - The **error and status change interrupt** can be generated by the following events:


–
Error condition, for more details on error conditions refer to the CAN Error Status
register (CAN_ESR).


–
Wake-up condition, SOF monitored on the CAN Rx signal.


–
Entry into Sleep mode.

## **29.9 CAN registers**


The peripheral registers have to be accessed by words (32 bits).


**29.9.1** **Register access protection**


Erroneous access to certain configuration registers can cause the hardware to temporarily
disturb the whole CAN network. Therefore the CAN_BTR register can be modified by
software only while the CAN hardware is in initialization mode.


Although the transmission of incorrect data does not cause problems at the CAN network
level, it can severely disturb the application. A transmit mailbox can be only modified by
software while it is in empty state, refer to _Figure 317: Transmit mailbox states_ .


The filter values can be modified either deactivating the associated filter banks or by setting
the FINIT bit. Moreover, the modification of the filter configuration (scale, mode and FIFO
assignment) in CAN_FMxR, CAN_FSxR and CAN_FFAR registers can only be done when
the filter initialization mode is set (FINIT=1) in the CAN_FMR register.


**29.9.2** **CAN control and status registers**


Refer to _Section 1.2_ for a list of abbreviations used in register descriptions.


**CAN master control register (CAN_MCR)**


Address offset: 0x00


Reset value: 0x0001 0002


844/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBF|
||||||||||||||||rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|RESET|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TTCM|ABOM|AWUM|NART|RFLM|TXFP|SLEEP|INRQ|
|rs||||||||rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:17 Reserved, must be kept at reset value.


Bit 16 **DBF:** Debug freeze

0: CAN working during debug
1: CAN reception/transmission frozen during debug. Reception FIFOs can still be
accessed/controlled normally.


Bit 15 **RESET:** bxCAN software master reset

0: Normal operation.
1: Force a master reset of the bxCAN -> Sleep mode activated after reset (FMP bits and
CAN_MCR register are initialized to the reset values). This bit is automatically reset to 0.


Bits 14:8 Reserved, must be kept at reset value.


Bit 7 **TTCM** : Time triggered communication mode

0: Time Triggered Communication mode disabled.
1: Time Triggered Communication mode enabled

_Note: For more information on Time Triggered Communication mode, refer to Section 29.7.2:_
_Time triggered communication mode._


Bit 6 **ABOM:** Automatic bus-off management

This bit controls the behavior of the CAN hardware on leaving the Bus-Off state.
0: The Bus-Off state is left on software request, once 128 occurrences of 11 recessive bits
have been monitored and the software has first set and cleared the INRQ bit of the
CAN_MCR register.
1: The Bus-Off state is left automatically by hardware once 128 occurrences of 11 recessive
bits have been monitored.

For detailed information on the Bus-Off state refer to _Section 29.7.6: Error management_ .


Bit 5 **AWUM** : Automatic wake-up mode

This bit controls the behavior of the CAN hardware on message reception during Sleep
mode.

0: The Sleep mode is left on software request by clearing the SLEEP bit of the CAN_MCR
register.
1: The Sleep mode is left automatically by hardware on CAN message detection.
The SLEEP bit of the CAN_MCR register and the SLAK bit of the CAN_MSR register are
cleared by hardware.


Bit 4 **NART** : No automatic retransmission

0: The CAN hardware automatically retransmits the message until it has been successfully
transmitted according to the CAN standard.
1: A message is transmitted only once, independently of the transmission result (successful,
error or arbitration lost).


RM0091 Rev 10 845/1017



867


**Controller area network (bxCAN)** **RM0091**


Bit 3 **RFLM** : Receive FIFO locked mode

0: Receive FIFO not locked on overrun. Once a receive FIFO is full the next incoming
message overwrites the previous one.
1: Receive FIFO locked against overrun. Once a receive FIFO is full the next incoming
message is discarded.


Bit 2 **TXFP** : Transmit FIFO priority

This bit controls the transmission order when several mailboxes are pending at the same
time.

0: Priority driven by the identifier of the message
1: Priority driven by the request order (chronologically)


Bit 1 **SLEEP** : Sleep mode request

This bit is set by software to request the CAN hardware to enter the Sleep mode. Sleep
mode is entered as soon as the current CAN activity (transmission or reception of a CAN
frame) has been completed.
This bit is cleared by software to exit Sleep mode.
This bit is cleared by hardware when the AWUM bit is set and a SOF bit is detected on the
CAN Rx signal.
This bit is set after reset - CAN starts in Sleep mode.


Bit 0 **INRQ** : Initialization request

The software clears this bit to switch the hardware into normal mode. Once 11 consecutive

recessive bits have been monitored on the Rx signal the CAN hardware is synchronized and
ready for transmission and reception. Hardware signals this event by clearing the INAK bit in
the CAN_MSR register.
Software sets this bit to request the CAN hardware to enter initialization mode. Once
software has set the INRQ bit, the CAN hardware waits until the current CAN activity
(transmission or reception) is completed before entering the initialization mode. Hardware
signals this event by setting the INAK bit in the CAN_MSR register.


**CAN master status register (CAN_MSR)**


Address offset: 0x04


Reset value: 0x0000 0C02

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|RX|SAMP|RXM|TXM|Res.|Res.|Res.|SLAKI|WKUI|ERRI|SLAK|INAK|
|||||r|r|r|r||||rc_w1|rc_w1|rc_w1|r|r|



Bits 31:12 Reserved, must be kept at reset value.


Bit 11 **RX** : CAN Rx signal

Monitors the actual value of the **CAN_RX** Pin.


Bit 10 **SAMP** : Last sample point

The value of RX on the last sample point (current received bit value).


846/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


Bit 9 **RXM** : Receive mode

The CAN hardware is currently receiver.


Bit 8 **TXM** : Transmit mode

The CAN hardware is currently transmitter.


Bits 7:5 Reserved, must be kept at reset value.


Bit 4 **SLAKI** : Sleep acknowledge interrupt

When SLKIE=1, this bit is set by hardware to signal that the bxCAN has entered Sleep
Mode. When set, this bit generates a status change interrupt if the SLKIE bit in the
CAN_IER register is set.
This bit is cleared by software or by hardware, when SLAK is cleared.

_Note: When SLKIE=0, no polling on SLAKI is possible. In this case the SLAK bit can be_
_polled._


Bit 3 **WKUI** : Wake-up interrupt

This bit is set by hardware to signal that a SOF bit has been detected while the CAN
hardware was in Sleep mode. Setting this bit generates a status change interrupt if the
WKUIE bit in the CAN_IER register is set.
This bit is cleared by software.


Bit 2 **ERRI** : Error interrupt

This bit is set by hardware when a bit of the CAN_ESR has been set on error detection and
the corresponding interrupt in the CAN_IER is enabled. Setting this bit generates a status
change interrupt if the ERRIE bit in the CAN_IER register is set.
This bit is cleared by software.


Bit 1 **SLAK** : Sleep acknowledge

This bit is set by hardware and indicates to the software that the CAN hardware is now in
Sleep mode. This bit acknowledges the Sleep mode request from the software (set SLEEP
bit in CAN_MCR register).
This bit is cleared by hardware when the CAN hardware has left Sleep mode (to be
synchronized on the CAN bus). To be synchronized the hardware has to monitor a
sequence of 11 consecutive recessive bits on the CAN RX signal.

_Note: The process of leaving Sleep mode is triggered when the SLEEP bit in the CAN_MCR_
_register is cleared. Refer to the AWUM bit of the CAN_MCR register description for_
_detailed information for clearing SLEEP bit_


Bit 0 **INAK** : Initialization acknowledge

This bit is set by hardware and indicates to the software that the CAN hardware is now in
initialization mode. This bit acknowledges the initialization request from the software (set
INRQ bit in CAN_MCR register).
This bit is cleared by hardware when the CAN hardware has left the initialization mode (to
be synchronized on the CAN bus). To be synchronized the hardware has to monitor a
sequence of 11 consecutive recessive bits on the CAN RX signal.


**CAN transmit status register (CAN_TSR)**


Address offset: 0x08


Reset value: 0x1C00 0000


RM0091 Rev 10 847/1017



867


**Controller area network (bxCAN)** **RM0091**

|31|30|29|28|27|26|25 24|Col8|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|LOW2|LOW1|LOW0|TME2|TME1|TME0|CODE[1:0]|CODE[1:0]|ABRQ2|Res.|Res.|Res.|TERR2|ALST2|TXOK2|RQCP2|
|r|r|r|r|r|r|r|r|rs||||rc_w1|rc_w1|rc_w1|rc_w1|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ABRQ1|Res.|Res.|Res.|TERR1|ALST1|TXOK1|RQCP1|ABRQ0|Res.|Res.|Res.|TERR0|ALST0|TXOK0|RQCP0|
|rs||||rc_w1|rc_w1|rc_w1|rc_w1|rs||||rc_w1|rc_w1|rc_w1|rc_w1|



Bit 31 **LOW2** : Lowest priority flag for mailbox 2

This bit is set by hardware when more than one mailbox are pending for transmission and
mailbox 2 has the lowest priority.


Bit 30 **LOW1** : Lowest priority flag for mailbox 1

This bit is set by hardware when more than one mailbox are pending for transmission and
mailbox 1 has the lowest priority.


Bit 29 **LOW0** : Lowest priority flag for mailbox 0

This bit is set by hardware when more than one mailbox are pending for transmission and
mailbox 0 has the lowest priority.

_Note: The LOW[2:0] bits are set to 0 when only one mailbox is pending._


Bit 28 **TME2** : Transmit mailbox 2 empty

This bit is set by hardware when no transmit request is pending for mailbox 2.


Bit 27 **TME1** : Transmit mailbox 1 empty

This bit is set by hardware when no transmit request is pending for mailbox 1.


Bit 26 **TME0** : Transmit mailbox 0 empty

This bit is set by hardware when no transmit request is pending for mailbox 0.


Bits 25:24 **CODE[1:0]** : Mailbox code

In case at least one transmit mailbox is free, the code value is equal to the number of the
next transmit mailbox free.

In case all transmit mailboxes are pending, the code value is equal to the number of the
transmit mailbox with the lowest priority.


Bit 23 **ABRQ2** : Abort request for mailbox 2

Set by software to abort the transmission request for the corresponding mailbox.
Cleared by hardware when the mailbox becomes empty.
Setting this bit has no effect when the mailbox is not pending for transmission.


Bits 22:20 Reserved, must be kept at reset value.


Bit 19 **TERR2** : Transmission error of mailbox 2

This bit is set when the previous TX failed due to an error.


Bit 18 **ALST2** : Arbitration lost for mailbox 2

This bit is set when the previous TX failed due to an arbitration lost.


Bit 17 **TXOK2** : Transmission OK of mailbox 2

The hardware updates this bit after each transmission attempt.
0: The previous transmission failed
1: The previous transmission was successful
This bit is set by hardware when the transmission request on mailbox 2 has been completed
successfully. Refer to _Figure 317_ .


848/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


Bit 16 **RQCP2** : Request completed mailbox2

Set by hardware when the last request (transmit or abort) has been performed.
Cleared by software writing a “1” or by hardware on transmission request (TXRQ2 set in
CAN_TMID2R register).
Clearing this bit clears all the status bits (TXOK2, ALST2 and TERR2) for Mailbox 2.


Bit 15 **ABRQ1** : Abort request for mailbox 1

Set by software to abort the transmission request for the corresponding mailbox.
Cleared by hardware when the mailbox becomes empty.
Setting this bit has no effect when the mailbox is not pending for transmission.


Bits 14:12 Reserved, must be kept at reset value.


Bit 11 **TERR1** : Transmission error of mailbox1

This bit is set when the previous TX failed due to an error.


Bit 10 **ALST1** : Arbitration lost for mailbox1

This bit is set when the previous TX failed due to an arbitration lost.


Bit 9 **TXOK1** : Transmission OK of mailbox1

The hardware updates this bit after each transmission attempt.
0: The previous transmission failed
1: The previous transmission was successful
This bit is set by hardware when the transmission request on mailbox 1 has been completed
successfully. Refer to _Figure 317_ .


Bit 8 **RQCP1** : Request completed mailbox1

Set by hardware when the last request (transmit or abort) has been performed.
Cleared by software writing a “1” or by hardware on transmission request (TXRQ1 set in
CAN_TI1R register).
Clearing this bit clears all the status bits (TXOK1, ALST1 and TERR1) for Mailbox 1.


Bit 7 **ABRQ0** : Abort request for mailbox0

Set by software to abort the transmission request for the corresponding mailbox.
Cleared by hardware when the mailbox becomes empty.
Setting this bit has no effect when the mailbox is not pending for transmission.


Bits 6:4 Reserved, must be kept at reset value.


Bit 3 **TERR0** : Transmission error of mailbox0

This bit is set when the previous TX failed due to an error.


Bit 2 **ALST0** : Arbitration lost for mailbox0

This bit is set when the previous TX failed due to an arbitration lost.


Bit 1 **TXOK0** : Transmission OK of mailbox0

The hardware updates this bit after each transmission attempt.
0: The previous transmission failed
1: The previous transmission was successful
This bit is set by hardware when the transmission request on mailbox 1 has been completed
successfully. Refer to _Figure 317_ .


Bit 0 **RQCP0** : Request completed mailbox0

Set by hardware when the last request (transmit or abort) has been performed.
Cleared by software writing a “1” or by hardware on transmission request (TXRQ0 set in
CAN_TI0R register).
Clearing this bit clears all the status bits (TXOK0, ALST0 and TERR0) for Mailbox 0.


RM0091 Rev 10 849/1017



867


**Controller area network (bxCAN)** **RM0091**


**CAN receive FIFO 0 register (CAN_RF0R)**


Address offset: 0x0C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RFOM0|FOVR0|FULL0|Res.|FMP0[1:0]|FMP0[1:0]|
|||||||||||rs|rc_w1|rc_w1||r|r|



Bits 31:6 Reserved, must be kept at reset value.


Bit 5 **RFOM0** : Release FIFO 0 output mailbox

Set by software to release the output mailbox of the FIFO. The output mailbox can only be
released when at least one message is pending in the FIFO. Setting this bit when the FIFO
is empty has no effect. If at least two messages are pending in the FIFO, the software has to
release the output mailbox to access the next message.
Cleared by hardware when the output mailbox has been released.


Bit 4 **FOVR0** : FIFO 0 overrun

This bit is set by hardware when a new message has been received and passed the filter
while the FIFO was full.

This bit is cleared by software.


Bit 3 **FULL0** : FIFO 0 full

Set by hardware when three messages are stored in the FIFO.
This bit is cleared by software.


Bit 2 Reserved, must be kept at reset value.


Bits 1:0 **FMP0[1:0]** : FIFO 0 message pending

These bits indicate how many messages are pending in the receive FIFO.
FMP is increased each time the hardware stores a new message in to the FIFO. FMP is
decreased each time the software releases the output mailbox by setting the RFOM0 bit.


**CAN receive FIFO 1 register (CAN_RF1R)**


Address offset: 0x10


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RFOM1|FOVR1|FULL1|Res.|FMP1[1:0]|FMP1[1:0]|
|||||||||||rs|rc_w1|rc_w1||r|r|



850/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


Bits 31:6 Reserved, must be kept at reset value.


Bit 5 **RFOM1** : Release FIFO 1 output mailbox

Set by software to release the output mailbox of the FIFO. The output mailbox can only be
released when at least one message is pending in the FIFO. Setting this bit when the FIFO
is empty has no effect. If at least two messages are pending in the FIFO, the software has to
release the output mailbox to access the next message.
Cleared by hardware when the output mailbox has been released.


Bit 4 **FOVR1** : FIFO 1 overrun

This bit is set by hardware when a new message has been received and passed the filter
while the FIFO was full.

This bit is cleared by software.


Bit 3 **FULL1** : FIFO 1 full

Set by hardware when three messages are stored in the FIFO.
This bit is cleared by software.


Bit 2 Reserved, must be kept at reset value.


Bits 1:0 **FMP1[1:0]** : FIFO 1 message pending

These bits indicate how many messages are pending in the receive FIFO1.
FMP1 is increased each time the hardware stores a new message in to the FIFO1. FMP is
decreased each time the software releases the output mailbox by setting the RFOM1 bit.


**CAN interrupt enable register (CAN_IER)**


Address offset: 0x14


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SLKIE|WKUIE|
|||||||||||||||rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ERRIE|Res.|Res.|Res.|LEC<br>IE|BOF<br>IE|EPV<br>IE|EWG<br>IE|Res.|FOV<br>IE1|FF<br>IE1|FMP<br>IE1|FOV<br>IE0|FF<br>IE0|FMP<br>IE0|TME<br>IE|
|rw||||rw|rw|rw|rw||rw|rw|rw|rw|rw|rw|rw|



Bits 31:18 Reserved, must be kept at reset value.


Bit 17 **SLKIE** : Sleep interrupt enable

0: No interrupt when SLAKI bit is set.
1: Interrupt generated when SLAKI bit is set.


Bit 16 **WKUIE** : Wake-up interrupt enable

0: No interrupt when WKUI is set.
1: Interrupt generated when WKUI bit is set.


Bit 15 **ERRIE** : Error interrupt enable

0: No interrupt is generated when an error condition is pending in the CAN_ESR.
1: An interrupt is generation when an error condition is pending in the CAN_ESR.


Bits 14:12 Reserved, must be kept at reset value.


RM0091 Rev 10 851/1017



867


**Controller area network (bxCAN)** **RM0091**


Bit 11 **LECIE** : Last error code interrupt enable

0: ERRI bit is not set when the error code in LEC[2:0] is set by hardware on error detection.
1: ERRI bit is set when the error code in LEC[2:0] is set by hardware on error detection.


Bit 10 **BOFIE** : Bus-off interrupt enable

0: ERRI bit is not set when BOFF is set.

1: ERRI bit is set when BOFF is set.


Bit 9 **EPVIE** : Error passive interrupt enable

0: ERRI bit is not set when EPVF is set.

1: ERRI bit is set when EPVF is set.


Bit 8 **EWGIE** : Error warning interrupt enable

0: ERRI bit is not set when EWGF is set.

1: ERRI bit is set when EWGF is set.


Bit 7 Reserved, must be kept at reset value.


Bit 6 **FOVIE1** : FIFO overrun interrupt enable

0: No interrupt when FOVR is set.
1: Interrupt generation when FOVR is set.


Bit 5 **FFIE1** : FIFO full interrupt enable

0: No interrupt when FULL bit is set.
1: Interrupt generated when FULL bit is set.


Bit 4 **FMPIE1** : FIFO message pending interrupt enable

0: No interrupt generated when state of FMP[1:0] bits are not 00b.
1: Interrupt generated when state of FMP[1:0] bits are not 00b.


Bit 3 **FOVIE0** : FIFO overrun interrupt enable

0: No interrupt when FOVR bit is set.
1: Interrupt generated when FOVR bit is set.


Bit 2 **FFIE0** : FIFO full interrupt enable

0: No interrupt when FULL bit is set.
1: Interrupt generated when FULL bit is set.


Bit 1 **FMPIE0** : FIFO message pending interrupt enable

0: No interrupt generated when state of FMP[1:0] bits are not 00b.
1: Interrupt generated when state of FMP[1:0] bits are not 00b.


Bit 0 **TMEIE** : Transmit mailbox empty interrupt enable

0: No interrupt when RQCPx bit is set.
1: Interrupt generated when RQCPx bit is set.

_Note: Refer to Section 29.8: bxCAN interrupts._


852/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


**CAN error status register (CAN_ESR)**


Address offset: 0x18


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24|Col2|Col3|Col4|Col5|Col6|Col7|Col8|23 22 21 20 19 18 17 16|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|REC[7:0]|REC[7:0]|REC[7:0]|REC[7:0]|REC[7:0]|REC[7:0]|REC[7:0]|REC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15|14|13|12|11|10|9|8|7|6 5 4|Col11|Col12|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LEC[2:0]|LEC[2:0]|LEC[2:0]|Res.|BOFF|EPVF|EWGF|
||||||||||rw|rw|rw||r|r|r|



Bits 31:24 **REC[7:0]** : Receive error counter

The implementing part of the fault confinement mechanism of the CAN protocol. In case of
an error during reception, this counter is incremented by 1 or by 8 depending on the error
condition as defined by the CAN standard. After every successful reception the counter is
decremented by 1 or reset to 120 if its value was higher than 128. When the counter value
exceeds 127, the CAN controller enters the error passive state.


Bits 23:16 **TEC[7:0]** : Least significant byte of the 9-bit transmit error counter

The implementing part of the fault confinement mechanism of the CAN protocol.


Bits 15:7 Reserved, must be kept at reset value.


Bits 6:4 **LEC[2:0]** : Last error code

This field is set by hardware and holds a code which indicates the error condition of the last
error detected on the CAN bus. If a message has been transferred (reception or
transmission) without error, this field is cleared to 0.
The LEC[2:0] bits can be set to value 0b111 by software. They are updated by hardware to
indicate the current communication status.

000: No error

001: Stuff error

010: Form error

011: Acknowledgment error
100: Bit recessive error

101: Bit dominant error

110: CRC error

111: Set by software


Bit 3 Reserved, must be kept at reset value.


Bit 2 **BOFF** : Bus-off flag

This bit is set by hardware when it enters the bus-off state. The bus-off state is entered on
TEC overflow, greater than 255, refer to _Section 29.7.6: Error management_ .


Bit 1 **EPVF** : Error passive flag

This bit is set by hardware when the Error passive limit has been reached (Receive Error
Counter or Transmit Error Counter > 127).


Bit 0 **EWGF** : Error warning flag

This bit is set by hardware when the warning limit has been reached
(Receive Error Counter or Transmit Error Counter ≥ 96).


RM0091 Rev 10 853/1017



867


**Controller area network (bxCAN)** **RM0091**


**CAN bit timing register (CAN_BTR)**


Address offset: 0x1C


Reset value: 0x0123 0000


This register can only be accessed by the software when the CAN hardware is in
initialization mode.

|31|30|29|28|27|26|25 24|Col8|23|22 21 20|Col11|Col12|19 18 17 16|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SILM|LBKM|Res.|Res.|Res.|Res.|SJW[1:0]|SJW[1:0]|Res.|TS2[2:0]|TS2[2:0]|TS2[2:0]|TS1[3:0]|TS1[3:0]|TS1[3:0]|TS1[3:0]|
|rw|rw|||||rw|rw||rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9 8 7 6 5 4 3 2 1 0|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|
|||||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 31 **SILM** : Silent mode (debug)

0: Normal operation
1: Silent Mode


Bit 30 **LBKM** : Loop back mode (debug)

0: Loop Back Mode disabled
1: Loop Back Mode enabled


Bits 29:26 Reserved, must be kept at reset value.


Bits 25:24 **SJW[1:0]** : Resynchronization jump width

These bits define the maximum number of time quanta the CAN hardware is allowed to
lengthen or shorten a bit to perform the resynchronization.
t RJW = t q x (SJW[1:0] + 1)


Bit 23 Reserved, must be kept at reset value.


Bits 22:20 **TS2[2:0]** : Time segment 2

These bits define the number of time quanta in Time Segment 2.
t BS2 = t q x (TS2[2:0] + 1)


Bits 19:16 **TS1[3:0]** : Time segment 1

These bits define the number of time quanta in Time Segment 1
t BS1 = t q x (TS1[3:0] + 1)
For more information on bit timing, refer to _Section 29.7.7: Bit timing_ .


Bits 15:10 Reserved, must be kept at reset value.


Bits 9:0 **BRP[9:0]** : Baud rate prescaler

These bits define the length of a time quanta.
t q = (BRP[9:0]+1) x t PCLK


854/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


**29.9.3** **CAN mailbox registers**


This chapter describes the registers of the transmit and receive mailboxes. Refer to
_Section 29.7.5: Message storage_ for detailed register mapping.


Transmit and receive mailboxes have the same registers except:


      - The FMI field in the CAN_RDTxR register.


      - A receive mailbox is always write protected.


      - A transmit mailbox is write-enabled only while empty, corresponding TME bit in the
CAN_TSR register set.


There are three TX mailboxes and two RX mailboxes. Each RX Mailbox allows access to a
3-level depth FIFO, the access being offered only to the oldest received message in the
FIFO.


Each mailbox consist of four registers.


**Figure 326. CAN mailbox registers**












|Col1|CAN_RI0R|Col3|Col4|Col5|
|---|---|---|---|---|
||~~CAN_RI0R~~|~~AN_RI0R~~|||
||~~C~~||||
||~~C~~|~~AN_RDT0R~~|||
||~~C~~||||
||~~C~~|~~AN_RL0R~~|||
||~~C~~|~~AN_RH0R~~|||


|Col1|CAN_RI1R|Col3|Col4|Col5|
|---|---|---|---|---|
||~~CAN_RI1R~~|~~AN_RI1R~~|||
||~~C~~||||
||~~C~~|~~AN_RDT1R~~|||
||~~C~~||||
||~~C~~|~~AN_RL1R~~|||
||~~C~~|~~AN_RH1R~~|||



**CAN TX mailbox identifier register (CAN_TIxR) (x = 0..2)**


Address offsets: 0x180, 0x190, 0x1A0


Reset value: 0xXXXX XXXX (except bit 0, TXRQ = 0)





All TX registers are write protected when the mailbox is pending transmission (TMEx reset).


This register also implements the TX request control (bit 0) - reset value 0.

|31 30 29 28 27 26 25 24 23 22 21|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|20 19 18 17 16|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|EXID[17:13]|EXID[17:13]|EXID[17:13]|EXID[17:13]|EXID[17:13]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8 7 6 5 4 3|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|IDE|RTR|TXRQ|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:21 **STID[10:0]/EXID[28:18]** : Standard identifier or extended identifier

The standard identifier or the MSBs of the extended identifier (depending on the IDE bit
value).


Bit 20:3 **EXID[17:0]** : Extended identifier

The LSBs of the extended identifier.


RM0091 Rev 10 855/1017



867


**Controller area network (bxCAN)** **RM0091**


Bit 2 **IDE** : Identifier extension

This bit defines the identifier type of message in the mailbox.

0: Standard identifier.

1: Extended identifier.


Bit 1 **RTR** : Remote transmission request

0: Data frame

1: Remote frame


Bit 0 **TXRQ** : Transmit mailbox request

Set by software to request the transmission for the corresponding mailbox.
Cleared by hardware when the mailbox becomes empty.


**CAN mailbox data length control and time stamp register**
**(CAN_TDTxR) (x = 0..2)**


All bits of this register are write protected when the mailbox is not in empty state.


Address offsets: 0x184, 0x194, 0x1A4


Reset value: 0xXXXX XXXX

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DLC[3:0]|DLC[3:0]|DLC[3:0]|DLC[3:0]|
|||||||||||||rw|rw|rw|rw|



Bits 31:16 **TIME[15:0]** : Message time stamp

This field contains the 16-bit timer value captured at the SOF transmission.


Bits 15:9 Reserved, must be kept at reset value.


Bit 8 **TGT** : Transmit global time

This bit is active only when the hardware is in the Time Trigger Communication mode,
TTCM bit of the CAN_MCR register is set.
0: Time stamp TIME[15:0] is not sent.
1: Time stamp TIME[15:0] value is sent in the last two data bytes of the 8-byte message:
TIME[7:0] in data byte 7 and TIME[15:8] in data byte 6, replacing the data written in
CAN_TDHxR[31:16] register (DATA6[7:0] and DATA7[7:0]). DLC must be programmed as 8
in order these two bytes to be sent over the CAN bus.


Bits 7:4 Reserved, must be kept at reset value.


Bits 3:0 **DLC[3:0]** : Data length code

This field defines the number of data bytes a data frame contains or a remote frame request.
A message can contain from 0 to 8 data bytes, depending on the value in the DLC field.


**CAN mailbox data low register (CAN_TDLxR) (x = 0..2)**


All bits of this register are write protected when the mailbox is not in empty state.


Address offsets: 0x188, 0x198, 0x1A8


856/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


Reset value: 0xXXXX XXXX

|31 30 29 28 27 26 25 24|Col2|Col3|Col4|Col5|Col6|Col7|Col8|23 22 21 20 19 18 17 16|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:24 **DATA3[7:0]** : Data byte 3

Data byte 3 of the message.


Bits 23:16 **DATA2[7:0]** : Data byte 2

Data byte 2 of the message.


Bits 15:8 **DATA1[7:0]** : Data byte 1
Data byte 1 of the message.


Bits 7:0 **DATA0[7:0]** : Data byte 0

Data byte 0 of the message.
A message can contain from 0 to 8 data bytes and starts with byte 0.


**CAN mailbox data high register (CAN_TDHxR) (x = 0..2)**


All bits of this register are write protected when the mailbox is not in empty state.


Address offsets: 0x18C, 0x19C, 0x1AC


Reset value: 0xXXXX XXXX

|31 30 29 28 27 26 25 24|Col2|Col3|Col4|Col5|Col6|Col7|Col8|23 22 21 20 19 18 17 16|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:24 **DATA7[7:0]** : Data byte 7

Data byte 7 of the message.

_Note:_ _**I**_ _f TGT of this message and TTCM are active, DATA7 and DATA6 are replaced by the_
_TIME stamp value._


Bits 23:16 **DATA6[7:0]** : Data byte 6

Data byte 6 of the message.


Bits 15:8 **DATA5[7:0]** : Data byte 5

Data byte 5 of the message.


Bits 7:0 **DATA4[7:0]** : Data byte 4

Data byte 4 of the message.


RM0091 Rev 10 857/1017



867


**Controller area network (bxCAN)** **RM0091**


**CAN receive FIFO mailbox identifier register (CAN_RIxR) (x = 0..1)**


Address offsets: 0x1B0, 0x1C0


Reset value: 0xXXXX XXXX


All RX registers are write protected.

|31 30 29 28 27 26 25 24 23 22 21|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|20 19 18 17 16|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|EXID[17:13]|EXID[17:13]|EXID[17:13]|EXID[17:13]|EXID[17:13]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8 7 6 5 4 3|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|EXID[12:0]|IDE|RTR|Res|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r||



Bits 31:21 **STID[10:0]/EXID[28:18]** : Standard identifier or extended identifier

The standard identifier or the MSBs of the extended identifier (depending on the IDE bit
value).


Bits 20:3 **EXID[17:0]** : Extended identifier

The LSBs of the extended identifier.


Bit 2 **IDE** : Identifier extension

This bit defines the identifier type of message in the mailbox.

0: Standard identifier.

1: Extended identifier.


Bit 1 **RTR** : Remote transmission request

0: Data frame

1: Remote frame


Bit 0 Reserved, must be kept at reset value.


**CAN receive FIFO mailbox data length control and time stamp register**
**(CAN_RDTxR) (x = 0..1)**


Address offsets: 0x1B4, 0x1C4


Reset value: 0xXXXX XXXX


All RX registers are write protected.

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7|6|5|4|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|Res.|Res.|Res.|Res.|DLC[3:0]|DLC[3:0]|DLC[3:0]|DLC[3:0]|
|r|r|r|r|r|r|r|r|||||r|r|r|r|



858/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


Bits 31:16 **TIME[15:0]** : Message time stamp

This field contains the 16-bit timer value captured at the SOF detection.


Bits 15:8 **FMI[7:0]** : Filter match index

This register contains the index of the filter the message stored in the mailbox passed
through. For more details on identifier filtering, refer to _Section 29.7.4: Identifier filtering_ .


Bits 7:4 Reserved, must be kept at reset value.


Bits 3:0 **DLC[3:0]** : Data length code

This field defines the number of data bytes a data frame contains (0 to 8). It is 0 in the case
of a remote frame request.


**CAN receive FIFO mailbox data low register (CAN_RDLxR) (x = 0..1)**


All bits of this register are write protected when the mailbox is not in empty state.


Address offsets: 0x1B8, 0x1C8


Reset value: 0xXXXX XXXX


All RX registers are write protected.

|31 30 29 28 27 26 25 24|Col2|Col3|Col4|Col5|Col6|Col7|Col8|23 22 21 20 19 18 17 16|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:24 **DATA3[7:0]** : Data byte 3

Data byte 3 of the message.


Bits 23:16 **DATA2[7:0]** : Data byte 2

Data byte 2 of the message.


Bits 15:8 **DATA1[7:0]** : Data byte 1

Data byte 2 of the message.


Bits 7:0 **DATA0[7:0]** : Data byte 0

Data byte 0 of the message.
A message can contain from 0 to 8 data bytes and starts with byte 0.


**CAN receive FIFO mailbox data high register (CAN_RDHxR) (x = 0..1)**


Address offsets: 0x1BC, 0x1CC


Reset value: 0xXXXX XXXX


All RX registers are write protected.


RM0091 Rev 10 859/1017



867


**Controller area network (bxCAN)** **RM0091**

|31 30 29 28 27 26 25 24|Col2|Col3|Col4|Col5|Col6|Col7|Col8|23 22 21 20 19 18 17 16|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:24 **DATA7[7:0]** : Data byte 7

Data byte 3 of the message.


Bits 23:16 **DATA6[7:0]** : Data byte 6

Data byte 2 of the message.


Bits 15:8 **DATA5[7:0]** : Data byte 5

Data byte 1 of the message.


Bits 7:0 **DATA4[7:0]** : Data byte 4

Data byte 0 of the message.


**29.9.4** **CAN filter registers**


**CAN filter master register (CAN_FMR)**


Address offset: 0x200


Reset value: 0x2A1C 0E01


All bits of this register are set and cleared by software.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FINIT|
||||||||||||||||rw|



Bits 31:1 Reserved, must be kept at reset value.


Bit 0 **FINIT** : Filter initialization mode

Initialization mode for filter banks

0: Active filters mode.

1: Initialization mode for the filters.


**CAN filter mode register (CAN_FM1R)**


Address offset: 0x204


Reset value: 0x0000 0000


This register can be written only when the filter initialization mode is set (FINIT=1) in the
CAN_FMR register.


860/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|FBM13|FBM12|FBM11|FBM10|FBM9|FBM8|FBM7|FBM6|FBM5|FBM4|FBM3|FBM2|FBM1|FBM0|
|||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



_Note:_ _Refer to Figure 319: Filter bank scale configuration - Register organization._


Bits 31:14 Reserved, must be kept at reset value.


Bits 13:0 **FBMx** : Filter mode

Mode of the registers of Filter x.
0: Two 32-bit registers of filter bank x are in Identifier Mask mode.
1: Two 32-bit registers of filter bank x are in Identifier List mode.


**CAN filter scale register (CAN_FS1R)**


Address offset: 0x20C


Reset value: 0x0000 0000


This register can be written only when the filter initialization mode is set (FINIT=1) in the
CAN_FMR register.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|FSC13|FSC12|FSC11|FSC10|FSC9|FSC8|FSC7|FSC6|FSC5|FSC4|FSC3|FSC2|FSC1|FSC0|
|||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:14 Reserved, must be kept at reset value.


Bits 13:0 **FSCx** : Filter scale configuration

These bits define the scale configuration of Filters 13-0.
0: Dual 16-bit scale configuration
1: Single 32-bit scale configuration


_Note:_ _Refer to Figure 319: Filter bank scale configuration - Register organization._


**CAN filter FIFO assignment register (CAN_FFA1R)**


Address offset: 0x214


Reset value: 0x0000 0000


This register can be written only when the filter initialization mode is set (FINIT=1) in the
CAN_FMR register.


RM0091 Rev 10 861/1017



867


**Controller area network (bxCAN)** **RM0091**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|FFA13|FFA12|FFA11|FFA10|FFA9|FFA8|FFA7|FFA6|FFA5|FFA4|FFA3|FFA2|FFA1|FFA0|
|||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:14 Reserved, must be kept at reset value.


Bits 13:0 **FFA** _**x**_ : Filter FIFO assignment for filter x

The message passing through this filter is stored in the specified FIFO.
0: Filter assigned to FIFO 0
1: Filter assigned to FIFO 1


**CAN filter activation register (CAN_FA1R)**


Address offset: 0x21C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|FACT1<br>3|FACT1<br>2|FACT1<br>1|FACT1<br>0|FACT9|FACT8|FACT7|FACT6|FACT5|FACT4|FACT3|FACT2|FACT1|FACT0|
|||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:14 Reserved, must be kept at reset value.


Bits 13:0 **FACTx** : Filter active

The software sets this bit to activate Filter x. To modify the Filter x registers (CAN_FxR[0:7]),
the FACTx bit must be cleared or the FINIT bit of the CAN_FMR register must be set.
0: Filter x is not active

1: Filter x is active


862/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


**Filter bank i register x (CAN_FiRx) (i = 0..13, x = 1, 2)**


Address offsets: 0x240 to 0x2AC


Reset value: 0xXXXX XXXX


There are 14 filter banks, i= 0 to 13. Each filter bank i is composed of two 32-bit registers,
CAN_FiR[2:1].


This register can only be modified when the FACTx bit of the CAN_FAxR register is cleared
or when the FINIT bit of the CAN_FMR register is set.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|FB31|FB30|FB29|FB28|FB27|FB26|FB25|FB24|FB23|FB22|FB21|FB20|FB19|FB18|FB17|FB16|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|FB15|FB14|FB13|FB12|FB11|FB10|FB9|FB8|FB7|FB6|FB5|FB4|FB3|FB2|FB1|FB0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



In all configurations:


Bits 31:0 **FB[31:0]** : Filter bits

**Identifier**

Each bit of the register specifies the level of the corresponding bit of the expected identifier.
0: Dominant bit is expected
1: Recessive bit is expected

**Mask**

Each bit of the register specifies whether the bit of the associated identifier register must
match with the corresponding bit of the expected identifier or not.
0: Do not care, the bit is not used for the comparison
1: Must match, the bit of the incoming identifier must have the same level has specified in
the corresponding identifier register of the filter.


_Note:_ _Depending on the scale and mode configuration of the filter, the function of each register_
_can differ. For the filter mapping, functions description and mask registers association, refer_
_to Section 29.7.4: Identifier filtering._


A Mask/Identifier register in **mask mode** has the same bit mapping as in **identifier list**
mode.


_For the register mapping/addresses of the filter banks refer to Table 120._


RM0091 Rev 10 863/1017



867


**Controller area network (bxCAN)** **RM0091**


**29.9.5** **bxCAN register map**


Refer to _Section 2.2 on page 46_ for the register boundary addresses.


**Table 120. bxCAN register map and reset values**









|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x000|**CAN_MCR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBF|RESET|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TTCM|ABOM|AWUM|NART|RFLM|TXFP|SLEEP|INRQ|
|0x000|Reset value||||||||||||||||1|0||||||||0|0|0|0|0|0|1|0|
|0x004|**CAN_MSR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RX|SAMP|RXM|TXM|Res.|Res.|Res.|SLAKI|WKUI|ERRI|SLAK|INAK|
|0x004|Reset value|||||||||||||||||||||1|1|0|0||||0|0|0|1|0|
|0x008|**CAN_TSR**|LOW[2:0]|LOW[2:0]|LOW[2:0]|TME[2:0]|TME[2:0]|TME[2:0]|CODE[1:0]|CODE[1:0]|ABRQ2|Res.|Res.|Res.|TERR2|ALST2|TXOK2|RQCP2|ABRQ1|Res.|Res.|Res.|TERR1|ALST1|TXOK1|RQCP1|ABRQ0|Res.|Res.|Res.|TERR0|ALST0|TXOK0|RQCP0|
|0x008|Reset value|0|0|0|1|1|1|0|0|0||||0|0|0|0|0||||0|0|0|0|0||||0|0|0|0|
|0x00C|**CAN_RF0R**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RFOM0|FOVR0|FULL0|Res.|FMP0[1:0]|FMP0[1:0]|
|0x00C|Reset value|||||||||||||||||||||||||||0|0|0||0|0|
|0x010|**CAN_RF1R**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RFOM1|FOVR1|FULL1|Res.|FMP1[1:0]|FMP1[1:0]|
|0x010|Reset value|||||||||||||||||||||||||||0|0|0||0|0|
|0x014|**CAN_IER**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SLKIE|WKUIE|ERRIE|Res.|Res.|Res.|LECIE|BOFIE|EPVIE|EWGIE|Res.|FOVIE1|FFIE1|FMPIE1|FOVIE0|FFIE0|FMPIE0|TMEIE|
|0x014|Reset value|||||||||||||||0|0|0||||0|0|0|0||0|0|0|0|0|0|0|
|0x018|**CAN_ESR**|REC[7:0]|REC[7:0]|REC[7:0]|REC[7:0]|REC[7:0]|REC[7:0]|REC[7:0]|REC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|TEC[7:0]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|LEC[2:0]|LEC[2:0]|LEC[2:0]|Res.|BOFF|EPVF|EWGF|
|0x018|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0||||||||||0|0|0||0|0|0|
|0x01C|**CAN_BTR**|SILM|LBKM|Res.|Res.|Res.|Res.|SJW[1:0]|SJW[1:0]|Res.|TS2[2:0]|TS2[2:0]|TS2[2:0]|TS1[3:0]|TS1[3:0]|TS1[3:0]|TS1[3:0]|Res.|Res.|Res.|Res.|Res.|Res.|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|BRP[9:0]|
|0x01C|Reset value|0|0|||||0|0||0|1|0|0|0|1|1|||||||0|0|0|0|0|0|0|0|0|0|
|0x020-<br>0x17F|-|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x180|**CAN_TI0R**|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|IDE|RTR|TXRQ|
|0x180|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|0|


864/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


**Table 120. bxCAN register map and reset values (continued)**



















|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x184|**CAN_TDT0R**|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TGT|Res.|Res.|Res.|Res.|DLC[3:0]|DLC[3:0]|DLC[3:0]|DLC[3:0]|
|0x184|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x||||||||x|||||x|x|x|x|
|0x188|**CAN_TDL0R**|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|
|0x188|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x18C|**CAN_TDH0R**|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|
|0x18C|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x190|**CAN_TI1R**|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|IDE|RTR|TXRQ|
|0x190|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|0|
|0x194|**CAN_TDT1R**|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TGT|Res.|Res.|Res.|Res.|DLC[3:0]|DLC[3:0]|DLC[3:0]|DLC[3:0]|
|0x194|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x||||||||x|||||x|x|x|x|
|0x198|**CAN_TDL1R**|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|
|0x198|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x19C|**CAN_TDH1R**|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|
|0x19C|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x1A0|**CAN_TI2R**|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|IDE|RTR|TXRQ|
|0x1A0|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|0|
|0x1A4|**CAN_TDT2R**|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TGT|Res.|Res.|Res.|Res.|DLC[3:0]|DLC[3:0]|DLC[3:0]|DLC[3:0]|
|0x1A4|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x||||||||x|||||x|x|x|x|
|0x1A8|**CAN_TDL2R**|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|
|0x1A8|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x1AC|**CAN_TDH2R**|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|
|0x1AC|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x1B0|**CAN_RI0R**|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|IDE|RTR|Res.|
|0x1B0|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|-|


RM0091 Rev 10 865/1017



867


**Controller area network (bxCAN)** **RM0091**


**Table 120. bxCAN register map and reset values (continued)**

























|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x1B4|**CAN_RDT0R**|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|Res.|Res.|Res.|Res.|DLC[3:0]|DLC[3:0]|DLC[3:0]|DLC[3:0]|
|0x1B4|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|||||x|x|x|x|
|0x1B8|**CAN_RDL0R**|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|
|0x1B8|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x1BC|**CAN_RDH0R**|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|
|0x1BC|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x1C0|**CAN_RI1R**|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|STID[10:0]/EXID[28:18]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|EXID[17:0]|IDE|RTR|Res.|
|0x1C0|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|-|
|0x1C4|**CAN_RDT1R**|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|TIME[15:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|FMI[7:0]|Res.|Res.|Res.|Res.|DLC[3:0]|DLC[3:0]|DLC[3:0]|DLC[3:0]|
|0x1C4|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|||||x|x|x|x|
|0x1C8|**CAN_RDL1R**|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA3[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA2[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA1[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|DATA0[7:0]|
|0x1C8|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x1CC|**CAN_RDH1R**|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA7[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA6[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA5[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|DATA4[7:0]|
|0x1CC|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x1D0-<br>0x1FF|-|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x200|**CAN_FMR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FINIT|
|0x200|Reset value||||||||||||||||||||||||||||||||1|
|0x204|**CAN_FM1R**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FBM[13:0]|FBM[13:0]|FBM[13:0]|FBM[13:0]|FBM[13:0]|FBM[13:0]|FBM[13:0]|FBM[13:0]|FBM[13:0]|FBM[13:0]|FBM[13:0]|FBM[13:0]|FBM[13:0]|FBM[13:0]|
|0x204|Reset value|||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x208|-|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x208|-|||||||||||||||||||||||||||||||||
|0x20C|**CAN_FS1R**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FSC[13:0]|FSC[13:0]|FSC[13:0]|FSC[13:0]|FSC[13:0]|FSC[13:0]|FSC[13:0]|FSC[13:0]|FSC[13:0]|FSC[13:0]|FSC[13:0]|FSC[13:0]|FSC[13:0]|FSC[13:0]|
|0x20C|Reset value|||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x210|-|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|


866/1017 RM0091 Rev 10


**RM0091** **Controller area network (bxCAN)**


**Table 120. bxCAN register map and reset values (continued)**





















|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x214|**CAN_FFA1R**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FFA[13:0]|FFA[13:0]|FFA[13:0]|FFA[13:0]|FFA[13:0]|FFA[13:0]|FFA[13:0]|FFA[13:0]|FFA[13:0]|FFA[13:0]|FFA[13:0]|FFA[13:0]|FFA[13:0]|FFA[13:0]|
|0x214|Reset value|||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x218|-|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x21C|**CAN_FA1R**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FACT[13:0]|FACT[13:0]|FACT[13:0]|FACT[13:0]|FACT[13:0]|FACT[13:0]|FACT[13:0]|FACT[13:0]|FACT[13:0]|FACT[13:0]|FACT[13:0]|FACT[13:0]|FACT[13:0]|FACT[13:0]|
|0x21C|Reset value|||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x220|-|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x224-<br>0x23F|-|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x240|**CAN_F0R1**|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|
|0x240|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x244|**CAN_F0R2**|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|
|0x244|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x248|**CAN_F1R1**|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|
|0x248|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x24C|**CAN_F1R2**|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|
|0x24C|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|.<br>.<br>.<br>.|
|0x2A8|**CAN_F13R1**|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|
|0x2A8|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|
|0x2AC|**CAN_F13R2**|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|FB[31:0]|
|0x2AC|Reset value|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|x|


Refer to _Section 2.2 on page 46_ for the register boundary addresses.


RM0091 Rev 10 867/1017



867


