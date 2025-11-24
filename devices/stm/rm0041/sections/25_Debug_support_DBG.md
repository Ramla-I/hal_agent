**RM0041** **Debug support (DBG)**

# **25 Debug support (DBG)**


**Low-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 16 and 32 Kbytes.


**Medium-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 64 and 128 Kbytes.


**High-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 256 and 512 Kbytes.


This section applies to the whole STM32F100xx family, unless otherwise specified.

## **25.1 Overview**


The STM32F100xx are built around a Cortex [®] -M3 core which contains hardware extensions
for advanced debugging features. The debug extensions allow the core to be stopped either
on a given instruction fetch (breakpoint) or data access (watchpoint). When stopped, the
core’s internal state and the system’s external state may be examined. Once examination is
complete, the core and the system may be restored and program execution resumed.


The debug features are used by the debugger host when connecting to and debugging the
STM32F100xx MCUs.


Two interfaces for debug are available:


      - Serial wire


      - JTAG debug port


RM0041 Rev 6 669/709



698


**Debug support (DBG)** **RM0041**


**Figure 284. Block diagram of STM32 MCU and Cortex** **[®]** **-M3-level debug support**





















_Note:_ _The debug features embedded in the Cortex_ _[®]_ _-M3 core are a subset of the Arm_ _[®]_ _CoreSight_
_Design Kit._


The Arm [®] Cortex [®] -M3 core provides integrated on-chip debug support. It is comprised of:


      - SWJ-DP: Serial wire / JTAG debug port


      - AHP-AP: AHB access p ort


      - ITM: Instrumentation trace macrocell


      - FPB: Flash patch breakpoint


      - DWT: Data watchpoint trigger


      - TPUI: Trace port unit interface (available on larger packages, where the corresponding
pins are mapped)


It also includes debug features dedicated to the STM32F100xx:


      - Flexible debug pinout assignment


      - MCU debug box (support for low-power modes, control over peripheral clocks, etc.)


_Note:_ _For further information on debug functionality supported by the Arm_ _[®]_ Cortex [®] _-M3_ _core, refer_
_to the_ Cortex [®] _-M3_ _-_ r1p1 _Technical Reference Manual and to the CoreSight Design Kit-r1p0_
_TRM (see Section 25.2)._


670/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**

## **25.2 Reference Arm [®] documentation**


      - Cortex [®] -M3 r1p1 Technical Reference Manual (TRM)


It is available from:


_http://infocenter.arm.com/_

      - Arm [®] Debug Interface V5

      - Arm [®] CoreSight Design Kit revision r1p1 Technical Reference Manual

## **25.3 SWJ debug port (serial wire and JTAG)**


The core of the STM32F100xx integrates the Serial Wire / JTAG Debug Port (SWJ-DP). It is
an Arm [®] standard CoreSight debug port that combines a JTAG-DP (5-pin) interface and a
SW-DP (2-pin) interface.


      - The JTAG Debug Port (JTAG-DP) provides a 5-pin standard JTAG interface to the
AHP-AP port.


      - The Serial Wire Debug Port (SW-DP) provides a 2-pin (clock + data) interface to the
AHP-AP port.


In the SWJ-DP, the two JTAG pins of the SW-DP are multiplexed with some of the five JTAG
pins of the JTAG-DP.


**Figure 285. SWJ debug** **port**


_Figure 285_ shows that the asynchronous TRACE output (TRACESWO) is multiplexed with
TDO. This means that the asynchronous trace can only be used with SW-DP, not JTAG-DP.


RM0041 Rev 6 671/709



698


**Debug support (DBG)** **RM0041**


**25.3.1** **Mechanism to select the JTAG-DP or the SW-DP**


By default, the JTAG-Debug Port is active.


If the debugger host wants to switch to the SW-DP, it must provide a dedicated JTAG
sequence on TMS/TCK (respectively mapped to SWDIO and SWCLK) which disables the
JTAG-DP and enables the SW-DP. This way it is possible to activate the SWDP using only
the SWCLK and SWDIO pins.


This sequence is:


1. Send more than 50 TCK cycles with TMS (SWDIO) =1


2. Send the 16-bit sequence on TMS (SWDIO) = 0111100111100111 (MSB transmitted
first)


3. Send more than 50 TCK cycles with TMS (SWDIO) =1

## **25.4 Pinout and debug port pins**


The STM32F100xx MCUs are available in various packages with different numbers of
available pins. As a result, some functionality (ETM) related to pin availability may differ
between packages.


**25.4.1** **SWJ debug port pins**


Five pins are used as outputs from the STM32F100xx for the SWJ-DP as _alternate functions_
of general-purpose I/Os. These pins are available on all packages.


**Table 145. SWJ debug** **port pins**

|SWJ-DP pin name|JTAG debug port|Col3|SW debug port|Col5|Pin<br>assignment|
|---|---|---|---|---|---|
|**SWJ-DP pin name**|**Type**|**Description**|**Type**|**Debug assignment**|**Debug assignment**|
|JTMS/SWDIO|I|JTAG Test Mode Selection|IO|Serial Wire Data Input/Output|PA13|
|JTCK/SWCLK|I|JTAG Test Clock|I|Serial Wire Clock|PA14|
|JTDI|I|JTAG Test Data Input|-|-|PA15|
|JTDO/TRACESWO|O|JTAG Test Data Output|-|TRACESWO if async trace is<br>enabled|PB3|
|NJTRST|I|JTAG Test nReset|-|-|PB4|



**25.4.2** **Flexible SWJ-DP pin assignment**


After RESET (SYSRESETn or PORESETn), all five pins used for the SWJ-DP are assigned
as dedicated pins immediately usable by the debugger host (note that the trace outputs are
not assigned except if explicitly programmed by the debugger host).


However, the STM32F100xx MCU implements the _AF remap and debug I/O configuration_
_register (AFIO_MAPR)_ register to disable some part or all of the SWJ-DP port and so
releases the associated pins for General Purpose IOs usage. This register is mapped on an
APB bridge connected to the Cortex [®] -M3 System Bus. Programming of this register is done
by the user software program and not the debugger host.


672/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**


Three control bits allow the configuration of the SWJ-DP pin assignments. These bits are
reset by the System Reset.


      - AFIO_MAPR (@ 0x40010004 in the STM32F100xx MCU)


– READ: APB - No Wait State


–
WRITE: APB - 1 Wait State if the write buffer of the AHB-APB bridge is full.


Bit 26:24= **SWJ_CFG[2:0]**


Set and cleared by software.


These bits are used to configure the number of pins assigned to the SWJ debug port.
The goal is to release as much as possible the number of pins to be used as General
Purpose IOs if using a small size for the debug port.


The default state after reset is “000” (whole pins assigned for a full JTAG-DP
connection). Only one of the 3 bits can be set (it is forbidden to set more than one bit).


**Table 146. Flexible SWJ-DP pin assignment**











|Available debug ports|SWJ IO pin assigned|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
|**Available debug ports**|**PA13 /**<br>**JTMS /**<br>**SWDIO**|**PA14 /**<br>**JTCK /**<br>**SWCLK**|**PA15 /**<br>**JTDI**|**PB3 /**<br>**JTDO**|**PB4 /**<br>**NJTRST**|
|Full SWJ (JTAG-DP + SW-DP) - Reset State|X|X|X|X|X|
|Full SWJ (JTAG-DP + SW-DP) but without NJTRST|X|X|X|X|X|
|JTAG-DP Disabled and SW-DP Enabled|X|X|X|X|X|
|JTAG-DP Disabled and SW-DP Disabled|JTAG-DP Disabled and SW-DP Disabled|JTAG-DP Disabled and SW-DP Disabled|JTAG-DP Disabled and SW-DP Disabled|JTAG-DP Disabled and SW-DP Disabled|JTAG-DP Disabled and SW-DP Disabled|


_Note:_ _When the APB bridge write buffer is full, it takes one extra APB cycle when writing the_
_AFIO_MAPR register. This is because the deactivation of the JTAGSW pins is done in two_
_cycles to guarantee a clean level on the nTRST and TCK input signals of the core._


      - Cycle 1: the JTAGSW input signals to the core are tied to 1 or 0 (to 1 for nTRST, TDI
and TMS, to 0 for TCK)


      - Cycle 2: the GPIO controller takes the control signals of the SWJTAG IO pins (like
controls of direction, pull-up/down, Schmitt trigger activation, etc.).


**25.4.3** **Internal pull-up and pull-down on JTAG pins**


It is necessary to ensure that the JTAG input pins are not floating since they are directly
connected to flip-flops to control the debug mode features. Special care must be taken with
the SWCLK/TCK pin which is directly connected to the clock of some of these flip-flops.


To avoid any uncontrolled IO levels, the device embeds internal pull-ups and pull-downs on
the JTAG input pins:


      - NJTRST: Internal pull-up


      - JTDI: Internal pull-up


      - JTMS/SWDIO: Internal pull-up


      - TCK/SWCLK: Internal pull-down


RM0041 Rev 6 673/709



698


**Debug support (DBG)** **RM0041**


Once a JTAG IO is released by the user software, the GPIO controller takes control again.
The reset states of the GPIO control registers put the I/Os in the equivalent state:


      - NJTRST: Input pull-up


      - JTDI: Input pull-up


      - JTMS/SWDIO: Input pull-up


      - JTCK/SWCLK: Input pull-down


      - JTDO: AF output floatingInput floating


The software can then use these I/Os as standard GPIOs.


_Note:_ _The JTAG IEEE standard recommends to add pull-ups on TDI, TMS and nTRST but there is_
_no special recommendation for TCK. However, for JTCK, the device needs an integrated_
_pull-down._


_Having embedded pull-ups and pull-downs removes the need to add external resistors._


674/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**


**25.4.4** **Using serial wire and releasing the unused debug pins as GPIOs**


To use the serial wire DP to release some GPIOs, the user software must set
SWJ_CFG=010 just after reset. This releases PA15, PB3 and PB4 which now become
available as GPIOs.


When debugging, the host performs the following actions:


      - Under system reset, all SWJ pins are assigned (JTAG-DP + SW-DP).


      - Under system reset, the debugger host sends the JTAG sequence to switch from the
JTAG-DP to the SW-DP.


      - Still under system reset, the debugger sets a breakpoint on vector reset.


      - The system reset is released and the Core halts.


      - All the debug communications from this point are done using the SW-DP. The other
JTAG pins can then be reassigned as GPIOs by the user software.


_Note:_ _For user software designs, note that:_


_To release the debug pins, remember that they are first configured either in input-pull-up_
_(nTRST, TMS, TDI) or pull-down (TCK) or output tristate (TDO) for a certain duration after_
_reset until the instant when the user software releases the pins._


_When debug pins (JTAG or SW or TRACE) are mapped, changing the corresponding IO pin_
_configuration in the IOPORT controller has no effect._

## **25.5 STM32F100xx JTAG TAP connection**


The STM32F100xx MCUs integrate two serially connected JTAG TAPs, the boundary scan
TAP (IR is 5-bit wide) and the Cortex [®] -M3 TAP (IR is 4-bit wide).


To access the TAP of the Cortex [®] -M3 for debug purposes:


1. First, it is necessary to shift the BYPASS instruction of the boundary scan TAP.


2. Then, for each IR shift, the scan chain contains 9 bits (=5+4) and the unused TAP
instruction must be shifted in using the BYPASS instruction.


3. For each data shift, the unused TAP, which is in BYPASS mode, adds 1 extra data bit in
the data scan chain.


_Note:_ _**Important**_ _: Once Serial-Wire is selected using the dedicated Arm_ [®] _JTAG sequence, the_
_boundary scan TAP is automatically disabled (JTMS forced high)._


RM0041 Rev 6 675/709



698


**Debug support (DBG)** **RM0041**


**Figure 286. JTAG TAP connections**

















676/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**

## **25.6 ID codes and locking mechanism**


There are several ID codes inside the STM32F100xx MCUs. ST strongly recommends tools
designers to lock their debuggers using the MCU DEVICE ID code located in the external
PPB memory map at address 0xE0042000.


**25.6.1** **MCU device ID code**


The STM32F100xx MCUs integrate an MCU ID code. This ID identifies the ST MCU partnumber and the die revision. It is part of the DBG_MCU component and is mapped on the
external PPB bus (see _Section 25.15_ ). This code is accessible using the JTAG debug port
(four to five pins) or the SW debug port (two pins) or by the user software. It is even
accessible while the MCU is under system reset.


Only the DEV_ID[11:0] must be used for identification by the debugger/programmer tools.


**DBGMCU_IDCODE**


Address: 0xE004 2000


Only 32-bits access supported. Read-only.

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|REV_ID[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12|11 10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|DEV_ID[11:0]|DEV_ID[11:0]|DEV_ID[11:0]|DEV_ID[11:0]|DEV_ID[11:0]|DEV_ID[11:0]|DEV_ID[11:0]|DEV_ID[11:0]|DEV_ID[11:0]|DEV_ID[11:0]|DEV_ID[11:0]|DEV_ID[11:0]|
|Reserved|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:16 **REV_ID[15:0]** Revision identifier

This field indicates the revision of the device:

In low and medium density value line devices:

– 0x1000 = Revision A

– 0x1001 = Revision Z

In high density value line devices:

– 0x1000 = Revision A


Bits 15:12 Reserved, must be kept at reset value.


Bits 11:0 **DEV_ID[11:0]** : Device identifier

This field indicates the device ID.

For low- and medium-density value line devices, the device ID is 0x420
For high-density value line devices, the device ID is 0x428


RM0041 Rev 6 677/709



698


**Debug support (DBG)** **RM0041**


**25.6.2** **Boundary scan TAP**


**JTAG ID code**


The TAP of the STM32F100xx BSC (boundary scan) integrates a JTAG ID code equal to


      - In low and medium-density value line devices:


– 0x06420041 = Revision A and Revision Z


      - In high-density value line devices:


– 0x06428041 = Revision A


**25.6.3** **Cortex** **[®]** **-M3 TAP**


The TAP of the Arm [®] Cortex [®] -M3 integrates a JTAG ID code. This ID code is the Arm [®]
default one and has not been modified. This code is only accessible by the JTAG Debug
Port, it is 0x3BA00477 (corresponds to Cortex [®] -M3 r1p1-01rel0, see _Section 25.2_ ).


**25.6.4** **Cortex** **[®]** **-M3 JEDEC-106 ID code**


The Arm [®] Cortex [®] -M3 integrates a JEDEC-106 ID code. It is located in the 4 KB ROM table
mapped on the internal PPB bus at address 0xE00FF000_0xE00FFFFF.


This code is accessible by the JTAG Debug Port (4 to 5 pins) or by the SW Debug Port (two
pins) or by the user software.

## **25.7 JTAG debug port**


A standard JTAG state machine is implemented with a 4-bit instruction register (IR) and five
data registers (for full details, refer to the Cortex [®] -M3 r1p1 _Technical Reference Manual_
_(TRM)_, for references, see _Section 25.2)_ .


**Table 147. JTAG debug** **port data registers**






|IR(3:0)|Data register|Details|
|---|---|---|
|1111|BYPASS<br>[1 bit]|-|
|1110|IDCODE<br>[32 bits]|ID CODE<br>0x3BA00477 (Arm® Cortex®-M3 r1p1-01rel0 ID Code)|
|1010|DPACC<br>[35 bits]|Debug port access register<br>This initiates a debug port and allows access to a debug port register.<br>– When transferring data IN:<br>Bits 34:3 = DATA[31:0] = 32-bit data to transfer for a write request<br>Bits 2:1 = A[3:2] = 2-bit address of a debug port register.<br>Bit 0 = RnW = Read request (1) or write request (0).<br>– When transferring data OUT:<br>Bits 34:3 = DATA[31:0] = 32-bit data which is read following a read<br>request<br>Bits 2:0 = ACK[2:0] = 3-bit Acknowledge:<br>010 = OK/FAULT<br>001 = WAIT<br>OTHER = reserved<br>Refer to_Table 148_ for a description of the A[3:2] bits|



678/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**


**Table 147. JTAG debug** **port data registers (continued)**






|IR(3:0)|Data register|Details|
|---|---|---|
|1011|APACC<br>[35 bits]|Access port access register<br>Initiates an access port and allows access to an access port register.<br>– When transferring data IN:<br>Bits 34:3 = DATA[31:0] = 32-bit data to shift in for a write request<br>Bits 2:1 = A[3:2] = 2-bit address (sub-address AP registers).<br>Bit 0 = RnW= Read request (1) or write request (0).<br>– When transferring data OUT:<br>Bits 34:3 = DATA[31:0] = 32-bit data which is read following a read<br>request<br>Bits 2:0 = ACK[2:0] = 3-bit Acknowledge:<br>010 = OK/FAULT<br>001 = WAIT<br>OTHER = reserved<br>There are many AP registers (see AHB-AP) addressed as the<br>combination of:<br>– The shifted value A[3:2]<br>– The current value of the DP SELECT register|
|1000|ABORT<br>[35 bits]|Abort register<br>– Bits 31:1 = Reserved<br>– Bit 0 = DAPABORT: write 1 to generate a DAP abort.|



**Table 148. 32-bit debug** **port registers addressed through the shifted value A[3:2]**







|Address|A[3:2] value|Description|
|---|---|---|
|0x0|00|Reserved, must be kept at reset value.|
|0x4|01|DP CTRL/STAT register. Used to:<br>– Request a system or debug power-up<br>– Configure the transfer operation for AP accesses<br>– Control the pushed compare and pushed verify operations.<br>– Read some status flags (overrun, power-up acknowledges)|
|0x8|10|DP SELECT register: Used to select the current access port and the<br>active 4-words register window.<br>– Bits 31:24: APSEL: select the current AP<br>– Bits 23:8: reserved<br>– Bits 7:4: APBANKSEL: select the active 4-words register window on the<br>current AP<br>– Bits 3:0: reserved|
|0xC|11|DP RDBUFF register: Used to allow the debugger to get the final result<br>after a sequence of operations (without requesting new JTAG-DP<br>operation)|


RM0041 Rev 6 679/709



698


**Debug support (DBG)** **RM0041**

## **25.8 SW debug port**


**25.8.1** **SW protocol introduction**


This synchronous serial protocol uses two pins:


      - SWCLK: clock from host to target


      - SWDIO: bidirectional


The protocol allows two banks of registers (DPACC registers and APACC registers) to be
read and written to.


Bits are transferred LSB-first on the wire.


For SWDIO bidirectional management, the line must be pulled-up on the board (100 KΩ
recommended by Arm [®] ).


Each time the direction of SWDIO changes in the protocol, a turnaround time is inserted
where the line is not driven by the host nor the target. By default, this turnaround time is one
bit time, however this can be adjusted by configuring the SWCLK frequency.


**25.8.2** **SW protocol sequence**


Each sequence consist of three phases:


1. Packet request (8 bits) transmitted by the host


2. Acknowledge response (3 bits) transmitted by the target


3. Data transfer phase (33 bits) transmitted by the host or the target


**Table 149. Packet request (8-bits)**

|Bit|Name|Description|
|---|---|---|
|0|Start|Must be “1”|
|1|APnDP|0: DP Access<br>1: AP Access|
|2|RnW|0: Write Request<br>1: Read Request|
|4:3|A[3:2]|Address field of the DP or AP registers (refer to_Table 148_)|
|5|Parity|Single bit parity of preceding bits|
|6|Stop|0|
|7|Park|Not driven by the host. Must be read as “1” by the target because of<br>the pull-up|



Refer to the Cortex [®] -M3 r1p1 _TRM_ for a detailed description of DPACC and APACC
registers.


The packet request is always followed by the turnaround time (default 1 bit) where neither
the host nor target drive the line.


680/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**


**Table 150. ACK response (3 bits)**

|Bit|Name|Description|
|---|---|---|
|0..2|ACK|001: FAULT<br>010: WAIT<br>100: OK|



The ACK Response must be followed by a turnaround time only if it is a READ transaction
or if a WAIT or FAULT acknowledge has been received.


**Table 151. DATA transfer (33 bits)**

|Bit|Name|Description|
|---|---|---|
|0..31|WDATA or RDATA|Write or Read data|
|32|Parity|Single parity of the 32 data bits|



The DATA transfer must be followed by a turnaround time only if it is a READ transaction.


**25.8.3** **SW-DP state machine (reset, idle states, ID code)**


The State Machine of the SW-DP has an internal ID code which identifies the SW-DP. It
follows the JEP-106 standard. This ID code is the default Arm [®] one and is set to
0x1BA01477 (corresponding to Cortex [®] -M3 r1p1).


_Note:_ _Note that the SW-DP state machine is inactive until the target reads this ID code._


      - The SW-DP state machine is in RESET STATE either after power-on reset, or after the
DP has switched from JTAG to SWD or after the line is high for more than 50 cycles


      - The SW-DP state machine is in IDLE STATE if the line is low for at least two cycles
after RESET state.


      - After RESET state, it is **mandatory** to first enter into an IDLE state AND to perform a
READ access of the DP-SW ID CODE register. Otherwise, the target issues a FAULT
acknowledge response on another transactions.


Further details of the SW-DP state machine can be found in the Cortex [®] -M3 _r1p1 TRM_ and
the _CoreSight Design Kit r1p0 TRM_ .


**25.8.4** **DP and AP read/write accesses**


      - Read accesses to the DP are not posted: the target response can be immediate (if
ACK=OK) or can be delayed (if ACK=WAIT).


      - Read accesses to the AP are posted. This means that the result of the access is
returned on the next transfer. If the next access to be done is NOT an AP access, then
the DP-RDBUFF register must be read to obtain the result.
The READOK flag of the DP-CTRL/STAT register is updated on every AP read access
or RDBUFF read request to know if the AP read access was successful.


      - The SW-DP implements a write buffer (for both DP or AP writes), that enables it to
accept a write operation even when other transactions are still outstanding. If the write
buffer is full, the target acknowledge response is “WAIT”. With the exception of


RM0041 Rev 6 681/709



698


**Debug support (DBG)** **RM0041**


IDCODE read or CTRL/STAT read or ABORT write which are accepted even if the write
buffer is full.


      - Because of the asynchronous clock domains SWCLK and HCLK, two extra SWCLK
cycles are needed after a write transaction (after the parity bit) to make the write
effective internally. These cycles must be applied while driving the line low (IDLE state)
This is particularly important when writing the CTRL/STAT for a power-up request. If the
next transaction (requiring a power-up) occurs immediately, it fails.


**25.8.5** **SW-DP registers**


Access to these registers are initiated when APnDP=0


**Table 152. SW-DP registers**









|A[3:2]|R/W|CTRLSEL bit<br>of SELECT<br>register|Register|Notes|
|---|---|---|---|---|
|00|Read|-|IDCODE|The manufacturer code is not set to ST code.<br>0x1BA01477 (identifies the SW-DP)|
|00|Write|-|ABORT|-|
|01|Read/Write|0|DP-<br>CTRL/STAT|Purpose is to:<br>– request a system or debug power-up<br>– configure the transfer operation for AP<br>accesses<br>– control the pushed compare and pushed verify<br>operations.<br>– read some status flags (overrun, power-up<br>acknowledges)|
|01|Read/Write|1|WIRE<br>CONTROL|Purpose is to configure the physical serial port<br>protocol (like the duration of the turnaround<br>time)|
|10|Read|-|READ<br>RESEND|Enables recovery of the read data from a<br>corrupted debugger transfer, without repeating<br>the original AP transfer.|
|10|Write|-|SELECT|The purpose is to select the current access port<br>and the active 4-words register window|
|11|Read/Write|-|READ<br>BUFFER|This read buffer is useful because AP accesses<br>are posted (the result of a read AP request is<br>available on the next AP transaction).<br>This read buffer captures data from the AP,<br>presented as the result of a previous read,<br>without initiating a new transaction|


**25.8.6** **SW-AP registers**





Access to these registers are initiated when APnDP=1


There are many AP registers (see AHB-AP) addressed as the combination of:


      - The shifted value A[3:2]


      - The current value of the DP SELECT register


682/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**

## **25.9 AHB-AP (AHB access port) - valid for both JTAG-DP** **and SW-DP**


**Features:**


      - System access is independent of the processor status.


      - Either SW-DP or JTAG-DP accesses AHB-AP.


      - The AHB-AP is an AHB master into the Bus Matrix. Consequently, it can access all the
data buses (Dcode Bus, System Bus, internal and external PPB bus) but the ICode
bus.


      - Bitband transactions are supported.


      - AHB-AP transactions bypass the FPB.


The address of the 32-bits AHP-AP resisters are 6-bits wide (up to 64 words or 256 bytes)
and consists of:


d) Bits [7:4] = the bits [7:4] APBANKSEL of the DP SELECT register


e) Bits [3:2] = the 2 address bits of A[3:2] of the 35-bit packet request for SW-DP.


The AHB-AP of the Cortex [®] -M3 includes 9 x 32-bits registers:


**Table 153.** **Cortex** **[®]** **-M3 AHB-AP registers**













|Address<br>offset|Register name|Notes|
|---|---|---|
|0x00|AHB-AP Control and Status<br>Word|Configures and controls transfers through the AHB<br>interface (size, hprot, status on current transfer, address<br>increment type|
|0x04|AHB-AP Transfer Address|-|
|0x0C|AHB-AP Data Read/Write|-|
|0x10|AHB-AP Banked Data 0|Directly maps the 4 aligned data words without rewriting<br>the Transfer Address register.|
|0x14|AHB-AP Banked Data 1|AHB-AP Banked Data 1|
|0x18|AHB-AP Banked Data 2|AHB-AP Banked Data 2|
|0x1C|AHB-AP Banked Data 3|AHB-AP Banked Data 3|
|0xF8|AHB-AP Debug ROM Address|Base Address of the debug interface|
|0xFC|AHB-AP ID register|-|


Refer to the Cortex [®] -M3 r1p1 _TRM_ for further details.


RM0041 Rev 6 683/709



698


**Debug support (DBG)** **RM0041**

## **25.10 Core debug**


Core debug is accessed through the core debug registers. Debug access to these registers
is by means of the _Advanced High-performance Bus_ (AHB-AP) port. The processor can
access these registers directly over the internal _Private Peripheral Bus_ (PPB).


It consists of 4 registers:


**Table 154. Core debug registers**

|Register|Description|
|---|---|
|DHCSR|The 32-bit Debug Halting Control and Status register<br>This provides status information about the state of the processor enable core debug<br>halt and step the processor|
|DCRSR|The 17-bit Debug Core register Selector register:<br>This selects the processor register to transfer data to or from.|
|DCRDR|The 32-bit Debug Core register Data register:<br>This holds data for reading and writing registers to and from the processor selected<br>by the DCRSR (Selector) register.|
|DEMCR|The 32-bit Debug Exception and Monitor Control register:<br>This provides Vector Catching and Debug Monitor Control. This register contains a<br>bit named**_TRCENA_** which enable the use of a TRACE.|



_Note:_ _**Important**_ _: these registers are not reset by a system reset. They are only reset by a power-_
_on reset._


Refer to the Cortex [®] _-M3_ r1p _1 TRM_ for further details.


To Halt on reset, it is necessary to:


      - enable the bit0 (VC_CORRESET) of the Debug and Exception Monitor Control register


      - enable the bit0 (C_DEBUGEN) of the Debug Halting Control and Status register.


684/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**

## **25.11 Capability of the debugger host to connect under system** **reset**


The reset system of the STM32F100xx MCU comprises the following reset sources:


      - POR (power-on reset) which asserts a RESET at each power-up.


      - Internal watchdog reset


      - Software reset


      - External reset


The Cortex [®] -M3 differentiates the reset of the debug part (generally PORRESETn) and the
other one (SYSRESETn)


This way, it is possible for the debugger to connect under System Reset, programming the
Core Debug registers to halt the core when fetching the reset vector. Then the host can
release the system reset and the core immediately halts without having executed any
instructions. In addition, it is possible to program any debug features under System Reset.


_Note:_ _It is highly recommended for the debugger host to connect (set a breakpoint in the reset_
_vector) under system reset._

## **25.12 FPB (Flash patch breakpoint)**


The FPB unit:


      - implements hardware breakpoints


      - patches code and data from code space to system space. This feature gives the
possibility to correct software bugs located in the Code Memory Space.


The use of a Software Patch or a Hardware Breakpoint is exclusive.


The FPB consists of:


      - 2 literal comparators for matching against literal loads from Code Space and remapping
to a corresponding area in the System Space.


      - 6 instruction comparators for matching against instruction fetches from Code Space.
They can be used either to remap to a corresponding area in the System Space or to
generate a Breakpoint Instruction to the core.


RM0041 Rev 6 685/709



698


**Debug support (DBG)** **RM0041**

## **25.13 DWT (data watchpoint trigger)**


The DWT unit consists of four comparators. They are configurable as:


      - a hardware watchpoint or


      - a PC sampler or


      - a data address sampler


The DWT also provides some means to give some profiling informations. For this, some
counters are accessible to give the number of:


      - Clock cycle


      - Folded instructions


      - Load store unit (LSU) operations


      - Sleep cycles


      - CPI (clock per instructions)


      - Interrupt overhead

## **25.14 ITM (instrumentation trace macrocell)**


**25.14.1** **General description**


The ITM is an application-driven trace source that supports _printf_ style debugging to trace
_Operating System_ (OS) and application events, and emits diagnostic system information.
The ITM emits trace information as packets which can be generated as:


      - **Software trace.** Software can write directly to the ITM stimulus registers to emit
packets.


      - **Hardware trace.** The DWT generates these packets, and the ITM emits them.


      - **Time stamping.** Timestamps are emitted relative to packets. The ITM contains a 21-bit
counter to generate the timestamp. The Cortex [®] -M3 clock or the bit clock rate of the
_Serial Wire Viewer_ (SWV) output clocks the counter.


The packets emitted by the ITM are output to the TPIU (Trace Port Interface Unit). The
formatter of the TPIU adds some extra packets (refer to TPIU) and then output the complete
packets sequence to the debugger host.


The bit TRCEN of the Debug Exception and Monitor Control register must be enabled
before programming or using the ITM.


**25.14.2** **Time stamp packets, synchronization and overflow packets**


Time stamp packets encode time stamp information, generic control and synchronization. It
uses a 21-bit timestamp counter (with possible prescalers) which is reset at each time
stamp packet emission. This counter can be either clocked by the CPU clock or the SWV
clock.


A synchronization packet consists of 6 bytes equal to 0x80_00_00_00_00_00 which is
emitted to the TPIU as 00 00 00 00 00 80 (LSB emitted first).


A synchronization packet is a timestamp packet control. It is emitted at each DWT trigger.


686/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**


For this, the DWT must be configured to trigger the ITM: the bit CYCCNTENA (bit0) of the
DWT Control register must be set. In addition, the bit2 (SYNCENA) of the ITM Trace Control
register must be set.


_Note:_ _If the SYNENA bit is not set, the DWT generates Synchronization triggers to the TPIU which_
_sends only TPIU synchronization packets and not ITM synchronization packets._


An overflow packet consists is a special timestamp packets which indicates that data has
been written but the FIFO was full.


**Table 155. Main ITM registers**







|Address|Register|Details|
|---|---|---|
|@E0000FB0|ITM lock access|Write 0xC5ACCE55 to unlock Write Access to the other ITM<br>registers|
|@E0000E80|ITM trace control|Bits 31-24 = Always 0|
|@E0000E80|ITM trace control|Bits 23 = Busy|
|@E0000E80|ITM trace control|Bits 22-16 = 7-bits ATB ID which identifies the source of the<br>trace data.|
|@E0000E80|ITM trace control|Bits 15-10 = Always 0|
|@E0000E80|ITM trace control|Bits 9:8 = TSPrescale = Time Stamp Prescaler|
|@E0000E80|ITM trace control|Bits 7-5 = Reserved|
|@E0000E80|ITM trace control|Bit 4 = SWOENA = Enable SWV behavior (to clock the<br>timestamp counter by the SWV clock).|
|@E0000E80|ITM trace control|Bit 3 = DWTENA: Enable the DWT Stimulus|
|@E0000E80|ITM trace control|Bit 2 = SYNCENA: this bit must be to 1 to enable the DWT to<br>generate synchronization triggers so that the TPIU can then<br>emit the synchronization packets.|
|@E0000E80|ITM trace control|Bit 1 = TSENA (Timestamp Enable)|
|@E0000E80|ITM trace control|Bit 0 = ITMENA: Global Enable Bit of the ITM|
|@E0000E40|ITM trace privilege|Bit 3: mask to enable tracing ports31:24|
|@E0000E40|ITM trace privilege|Bit 2: mask to enable tracing ports23:16|
|@E0000E40|ITM trace privilege|Bit 1: mask to enable tracing ports15:8|
|@E0000E40|ITM trace privilege|Bit 0: mask to enable tracing ports7:0|
|@E0000E00|ITM trace enable|Each bit enables the corresponding Stimulus port to generate<br>trace.|
|@E0000000-<br>E000007C|Stimulus port<br>registers 0-31|Write the 32-bits data on the selected Stimulus Port (32<br>available) to be traced out.|


RM0041 Rev 6 687/709



698


**Debug support (DBG)** **RM0041**


**Example of configuration**


To output a simple value to the TPIU:


      - Configure the TPIU and assign TRACE I/Os by configuring the DBGMCU_CR (refer to
_Section 25.16.2_ and _Section 25.15.3_ )


      - Write 0xC5ACCE55 to the ITM Lock Access register to unlock the write access to the
ITM registers


      - Write 0x00010005 to the ITM Trace Control register to enable the ITM with Sync
enabled and an ATB ID different from 0x00


      - Write 0x1 to the ITM Trace Enable register to enable the Stimulus Port 0


      - Write 0x1 to the ITM Trace Privilege register to unmask stimulus ports 7:0


      - Write the value to output in the Stimulus Port register 0: this can be done by software
(using a printf function)

## **25.15 MCU debug component (DBGMCU)**


The MCU debug component helps the debugger provide support for:


      - Low-power modes


      - Clock control for timers, watchdog, I2C during a breakpoint


      - Control of the trace pins assignment


**25.15.1** **Debug support for low-power modes**


To enter low-power mode, the instruction WFI or WFE must be executed.


The MCU implements several low-power modes which can either deactivate the CPU clock
or reduce the power of the CPU.


The core does not allow FCLK or HCLK to be turned off during a debug session. As these
are required for the debugger connection, during a debug, they must remain active. The
MCU integrates special means to allow the user to debug software in low-power modes.


For this, the debugger host must first set some debug configuration registers to change the
low-power mode behavior:


      - In Sleep mode, DBG_SLEEP bit of DBGMCU_CR register must be previously set by
the debugger. This feeds HCLK with the same clock that is provided to FCLK (system
clock previously configured by the software).


      - In Stop mode, the bit DBG_STOP must be previously set by the debugger. This
enables the internal RC oscillator clock to feed FCLK and HCLK in STOP mode.


**25.15.2** **Debug support for timers, watchdog and I** **[2]** **C**


During a breakpoint, it is necessary to choose how the counter of timers and watchdog must
behave:


      - They can continue to count inside a breakpoint. This is usually required when a PWM is
controlling a motor, for example.


      - They can stop to count inside a breakpoint. This is required for watchdog purposes.


For the I [2] C, the user can choose to block the SMBUS timeout during a breakpoint.


688/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**


For timers having complementary outputs, when the counter is stopped
(DBG_TIMx_STOP = 1), the outputs are disabled (as if the MOE bit was reset) for safety

purposes.


**25.15.3** **Debug MCU configuration register**


This register allows the configuration of the MCU under DEBUG. This concerns:


      - Low-power mode support


      - Timer and watchdog counter support


      - Trace pin assignment


This DBGMCU_CR is mapped on the External PPB bus at address 0xE0042004


It is asynchronously reset by the PORESET (and not the system reset). It can be written by
the debugger under system reset.


If the debugger host does not support these features, it is still possible for the user software
to write to these registers.


**DBGMCU_CR register**


Address: 0xE004 2004


Only 32-bit access supported


POR Reset: 0x0000 0000 (not reset by system reset)


























|31 30 29 28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|DBG_<br>TIM14<br>_STO<br>P|DBG_<br>TIM13<br>_STO<br>P|DBG_<br>TIM12_<br>STOP|DBG_<br>TIM17<br>_STO<br>P|DBG_<br>TIM16<br>_STO<br>P|DBG_<br>TIM15<br>_STO<br>P|Res.|DBG_<br>TIM7_<br>STOP|DBG_<br>TIM6_<br>STOP|DBG_<br>TIM5_<br>STOP|Res.|DBG_I2C2<br>_SMBUS_<br>TIMEOUT|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|

























|15|14|13|12|11|10|9|8|7 6|Col10|5|4 3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DBG_I2C1<br>_SMBUS_<br>TIMEOUT|Res.|DBG_<br>TIM4_<br>STOP|DBG_<br>TIM3_<br>STOP|DBG_<br>TIM2_<br>STOP|DBG_<br>TIM1_<br>STOP|DBG_<br>WWDG<br>_<br>STOP|DBG_<br>IWDG<br>STOP|TRACE_<br>MODE<br>[1:0]|TRACE_<br>MODE<br>[1:0]|TRACE<br>_<br>IOEN|Reserved|DBG_<br>STAND<br>BY|DBG_<br>STOP|DBG_<br>SLEEP|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:28 Reserved, must be kept at reset value.


Bits 27:25 **DBG_TIMx_STOP:** TIMx counter stopped when core is halted (x = 12..14)

0: The clock of the involved timer counter is fed even if the core is halted

1: The clock of the involved timer counter is stopped when the core is halted


Bits 24:22 **DBG_TIMx_STOP:** TIMx counter stopped when core is halted (x = 17..15)

0: The clock of the involved timer counter is fed even if the core is halted

1: The clock of the involved timer counter is stopped when the core is halted


Bit 21 Reserved, must be kept at reset value.


RM0041 Rev 6 689/709



698


**Debug support (DBG)** **RM0041**


Bits 20:18 **DBG_TIMx_STOP:** TIMx counter stopped when core is halted (x=5 .. 7)

0: The clock of the involved timer counter is fed even if the core is halted, and the outputs
behave normally.
1: The clock of the involved timer counter is stopped when the core is halted, and the
outputs are disabled (as if there were an emergency stop in response to a break event).


Bit 17 Reserved, must be kept at reset value.


Bit 16 **DBG_I2C2_SMBUS_TIMEOUT:** SMBUS timeout mode stopped when Core is halted

0: Same behavior as in normal mode

1: The SMBUS timeout is frozen


Bit 15 **DBG_I2C1_SMBUS_TIMEOUT:** SMBUS timeout mode stopped when Core is halted

0: Same behavior as in normal mode

1: The SMBUS timeout is frozen


Bits 13:10 **DBG_TIMx_STOP:** TIMx counter stopped when core is halted (x=4..1)


Bit 9 **DBG_WWDG_STOP:** Debug window watchdog stopped when core is halted

0: The window watchdog counter clock continues even if the core is halted
1: The window watchdog counter clock is stopped when the core is halted


Bit 8 **DBG_IWDG_STOP:** Debug independent watchdog stopped when core is halted

0: The watchdog counter clock continues even if the core is halted
1: The watchdog counter clock is stopped when the core is halted


Bits 7:5 **TRACE_MODE[1:0] and TRACE_IOEN** : Trace pin assignment control

– With TRACE_IOEN=0:

TRACE_MODE=xx: TRACE pins not assigned (default state)

– With TRACE_IOEN=1:

–
TRACE_MODE=00: TRACE pin assignment for Asynchronous mode

–
TRACE_MODE=01: TRACE pin assignment for Synchronous mode with a
TRACEDATA size of 1

–
TRACE_MODE=10: TRACE pin assignment for Synchronous mode with a
TRACEDATA size of 2

–
TRACE_MODE=11: TRACE pin assignment for Synchronous mode with a
TRACEDATA size of 4


Bits 4:3 Reserved, must be kept at reset value.


690/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**


Bit 2 **DBG_STANDBY:** Debug Standby mode

0: (FCLK=Off, HCLK=Off) The whole digital part is unpowered.
From software point of view, exiting from Standby is identical than fetching reset vector
(except a few status bit indicated that the MCU is resuming from Standby)
1: (FCLK=On, HCLK=On) In this case, the digital part is not unpowered and FCLK and
HCLK are provided by the internal RC oscillator which remains active. In addition, the MCU
generate a system reset during Standby mode so that exiting from Standby is identical than
fetching from reset


Bit 1 **DBG_STOP:** Debug Stop mode

0: (FCLK=Off, HCLK=Off) In STOP mode, the clock controller disables all clocks (including
HCLK and FCLK). When exiting from STOP mode, the clock configuration is identical to the
one after RESET (CPU clocked by the MHz internal RC oscillator (HSI)). Consequently, the
software must reprogram the clock controller to enable the PLL, the Xtal, etc.
1: (FCLK=On, HCLK=On) In this case, when entering STOP mode, FCLK and HCLK are
provided by the internal RC oscillator which remains active in STOP mode. When exiting
STOP mode, the software must reprogram the clock controller to enable the PLL, the Xtal,
etc. (in the same way it would do in case of DBG_STOP=0)


Bit 0 **DBG_SLEEP:** Debug Sleep mode

0: (FCLK=On, HCLK=Off) In Sleep mode, FCLK is clocked by the system clock as
previously configured by the software while HCLK is disabled.
In Sleep mode, the clock controller configuration is not reset and remains in the previously
programmed state. Consequently, when exiting from Sleep mode, the software does not
need to reconfigure the clock controller.
1: (FCLK=On, HCLK=On) In this case, when entering Sleep mode, HCLK is fed by the same
clock that is provided to FCLK (system clock as previously configured by the software).

## **25.16 TPIU (trace port interface unit)**


**25.16.1** **Introduction**


The TPIU acts as a bridge between the on-chip trace data from the ITM.


The output data stream encapsulates the trace source ID, that is then captured by a _trace_
_port analyzer_ (TPA).


The core embeds a simple TPIU, especially designed for low-cost debug (consisting of a
special version of the CoreSight TPIU).


RM0041 Rev 6 691/709



698


**Debug support (DBG)** **RM0041**


**Figure 287. TPIU block diagram**















692/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**


**25.16.2** **TRACE pin assignment**


      - Asynchronous mode


The asynchronous mode requires 1 extra pin and is available on all packages. It is only
available if using Serial Wire mode (not in JTAG mode).


**Table 156. Asynchronous TRACE pin assignment**

|TPUI pin name|Trace synchronous mode|Col3|STM32F100xx pin<br>assignment|
|---|---|---|---|
|**TPUI pin name**|**Type**|**Description**|**Description**|
|TRACESWO|O|TRACE Async Data Output|PB3|



      - Synchronous mode


The synchronous mode requires from 2 to 6 extra pins depending on the data trace
size and is only available in the larger packages. In addition it is available in JTAG
mode and in Serial Wire mode and provides better bandwidth output capabilities than
asynchronous trace.


**Table 157. Synchronous TRACE pin assignment**

|TPUI pin name|Trace synchronous mode|Col3|STM32F100xxpin<br>assignment|
|---|---|---|---|
|**TPUI pin name**|**Type**|**Description**|**Description**|
|TRACECK|O|TRACE Clock|PE2|
|TRACED[3:0]|O|TRACE Sync Data Outputs<br>Can be 1, 2 or 4.|PE[6:3]|



**TPUI TRACE pin assignment**


By default, these pins are NOT assigned. They can be assigned by setting the
TRACE_IOEN and TRACE_MODE bits in the _**MCU Debug component configuration**_
_**register**_ . This configuration has to be done by the debugger host.


In addition, the number of pins to assign depends on the trace configuration (asynchronous
or synchronous).


      - **Asynchronous mode** : 1 extra pin is needed


      - **Synchronous mode** : from 2 to 5 extra pins are needed depending on the size of the
data trace port register (1, 2 or 4):


– TRACECK


–
TRACED(0) if port size is configured to 1, 2 or 4


–
TRACED(1) if port size is configured to 2 or 4


–
TRACED(2) if port size is configured to 4


–
TRACED(3) if port size is configured to 4


To assign the TRACE pin, the debugger host must program the bits TRACE_IOEN and
TRACE_MODE[1:0] of the Debug MCU configuration register (DBGMCU_CR). By default
the TRACE pins are not assigned.


This register is mapped on the external PPB and is reset by the PORESET (and not by the
SYSTEM reset). It can be written by the debugger under SYSTEM reset.


RM0041 Rev 6 693/709



698


**Debug support (DBG)** **RM0041**


**Table 158. Flexible TRACE pin assignment**


















|DBGMCU_CR<br>register|Col2|Pins<br>assigned<br>for:|TRACE IO pin assigned|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|**TRACE**<br>**_IOEN**|**TRACE**<br>**_MODE**<br>**[1:0]**|**TRACE**<br>**_MODE**<br>**[1:0]**|**PB3 /JTDO/**<br>**TRACESWO**|**PE2/**<br>**TRACECK**|**PE3 /**<br>**TRACED[0]**|**PE4 /**<br>**TRACED[1]**|**PE5 /**<br>**TRACED[2]**|**PE6 /**<br>**TRACED[3]**|
|0|XX|No Trace<br>(default state)|Released (1)|-|-|-|-|-|
|1|00|Asynchronous<br>Trace|TRACESWO|-|-|Released<br>(usable as GPIO)|Released<br>(usable as GPIO)|Released<br>(usable as GPIO)|
|1|01|Synchronous<br>Trace 1 bit|Released (1)|TRACECK|TRACED[0]|-|-|-|
|1|10|Synchronous<br>Trace 2 bit|Synchronous<br>Trace 2 bit|TRACECK|TRACED[0]|TRACED[1]|-|-|
|1|11|Synchronous<br>Trace 4 bit|Synchronous<br>Trace 4 bit|TRACECK|TRACED[0]|TRACED[1]|TRACED[2]|TRACED[3]|



1. When Serial Wire mode is used, it is released. But when JTAG is used, it is assigned to JTDO.


_Note:_ _By default, the TRACECLKIN input clock of the TPIU is tied to GND. It is assigned to HCLK_
_two clock cycles after the bit TRACE_IOEN has been set._


The debugger must then program the Trace Mode by writing the PROTOCOL[1:0] bits in the
SPP_R (Selected Pin Protocol) register of the TPIU.


       - PROTOCOL=00: Trace Port Mode (synchronous)


       - PROTOCOL=01 or 10: Serial Wire (Manchester or NRZ) Mode (asynchronous mode).
Default state is 01


It then also configures the TRACE port size by writing the bits [3:0] in the CPSPS_R
(Current Sync Port Size register) of the TPIU:


       - 0x1 for 1 pin (default state)


       - 0x2 for 2 pins


       - 0x8 for 4 pins


**25.16.3** **TPUI formatter**


The formatter protocol outputs data in 16-byte frames:


       - seven bytes of data


       - eight bytes of mixed-use bytes consisting of:


–
1 bit (LSB) to indicate it is a DATA byte (‘0) or an ID byte (‘1).


–
7 bits (MSB) which can be data or change of source ID trace.


       - one byte of auxiliary bits where each bit corresponds to one of the eight mixed-use
bytes:


–
if the corresponding byte was a data, this bit gives bit0 of the data.


–
if the corresponding byte was an ID change, this bit indicates when that ID change
takes effect.


694/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**


_Note:_ _Refer to the Arm_ _[®]_ _CoreSight Architecture Specification v1.0 (Arm_ _[®]_ _IHI 0029B) for further_
_information_


**25.16.4** **TPUI frame synchronization packets**


The TPUI can generate two types of synchronization packets:


      - The Frame Synchronization packet (or Full Word Synchronization packet)


It consists of the word: 0x7F_FF_FF_FF (LSB emitted first). This sequence can not
occur at any other time provided that the ID source code 0x7F has not been used.


It is output periodically _**between**_ frames.


In continuous mode, the TPA must discard all these frames once a synchronization
frame has been found.


      - The Half-Word Synchronization packet


It consists of the half word: 0x7F_FF (LSB emitted first).


It is output periodically _**between or within**_ frames.


These packets are only generated in continuous mode and enable the TPA to detect
that the TRACE port is in IDLE mode (no TRACE to be captured). When detected by
the TPA, it must be discarded.


**25.16.5** **Transmission of the synchronization frame packet**


There is no Synchronization Counter register implemented in the TPIU of the core.
Consequently, the synchronization trigger can only be generated by the **DWT** . Refer to the
registers DWT Control register (bits SYNCTAP[11:10]) and the DWT Current PC Sampler
Cycle Count register.


The TPUI Frame synchronization packet (0x7F_FF_FF_FF) is emitted:


      - after each TPIU reset release. This reset is synchronously released with the rising
edge of the TRACECLKIN clock. This means that this packet is transmitted when the
TRACE_IOEN bit in the DBGMCU_CFG register is set. In this case, the word
0x7F_FF_FF_FF is not followed by any formatted packet.


      - at each DWT trigger (assuming DWT has been previously configured). Two cases

occur:


–
If the bit SYNENA of the ITM is reset, only the word 0x7F_FF_FF_FF is emitted
without any formatted stream which follows.


–
If the bit SYNENA of the ITM is set, then the ITM synchronization packets follow
(0x80_00_00_00_00_00), formatted by the TPUI (trace source ID added).


**25.16.6** **Synchronous mode**


The trace data output size can be configured to 4, 2 or 1 pin: TRACED(3:0)


The output clock is output to the debugger (TRACECK)


Here, TRACECLKIN is driven internally and is connected to HCLK only when TRACE is
used.


_Note:_ _In this synchronous mode, it is not required to provide a stable clock frequency._


The TRACE I/Os (including TRACECK) are driven by the rising edge of TRACLKIN (equal
to HCLK). Consequently, the output frequency of TRACECK is equal to HCLK/2.


RM0041 Rev 6 695/709



698


**Debug support (DBG)** **RM0041**


**25.16.7** **Asynchronous mode**


This is a low cost alternative to output the trace using only 1 pin: this is the asynchronous
output pin TRACESWO. Obviously there is a limited bandwidth.


TRACESWO is multiplexed with JTDO when using the SW-DP pin. This way, this
functionality is available in all STM32F100xx packages.


This asynchronous mode requires a constant frequency for TRACECLKIN. For the standard
UART (NRZ) capture mechanism, 5% accuracy is needed. The Manchester encoded
version is tolerant up to 10%.


**25.16.8** **TRACECLKIN connection inside th** e **STM32F100xx**


In the STM32F100xx, this TRACECLKIN input is internally connected to HCLK. This means
that when in asynchronous trace mode, the application is restricted to use to time frames
where the CPU frequency is stable.


_Note:_ _**Important:**_ _when using asynchronous trace: it is important to be aware that:_


_The default clock of the STM32F100xx MCUs is the internal RC oscillator. Its frequency_
_under reset is different from the one after reset release. This is because the RC calibration_
_is the default one under system reset and is updated at each system reset release._


_Consequently, the trace port analyzer (TPA) must not enable the trace (with the_
_TRACE_IOEN bit) under system reset, because a Synchronization Frame Packet is issued_
_with a different bit time than trace packets which are transmitted after reset release._


**25.16.9** **TPIU registers**


The TPIU APB registers can be read and written only if the bit TRCENA of the Debug
Exception and Monitor Control register (DEMCR) is set. Otherwise, the registers are read as
zero (the output of this bit enables the PCLK of the TPIU).


**Table 159. Important TPIU registers**






|Address|Register|Description|
|---|---|---|
|0xE0040004|Current port size|Allows the trace port size to be selected:<br>Bit 0: Port size = 1<br>Bit 1: Port size = 2<br>Bit 2: Port size = 3, not supported<br>Bit 3: Port Size = 4<br>Only 1 bit must be set. By default, the port size is one bit. (0x00000001)|
|0xE00400F0|Selected pin protocol|Allows the Trace Port Protocol to be selected:<br>Bit1:0=<br>00: Sync Trace Port Mode<br>01: Serial Wire Output - manchester (default value)<br>10: Serial Wire Output - NRZ<br>11: reserved|



696/709 RM0041 Rev 6


**RM0041** **Debug support (DBG)**


**Table 159. Important TPIU registers (continued)**







|Address|Register|Description|
|---|---|---|
|0xE0040304|Formatter and flush<br>control|Bits 31-9 = always ‘0<br>Bit 8 = TrigIn = always ‘1 to indicate that triggers are indicated<br>Bits 7-4 = always 0<br>Bits 3-2 = always 0<br>Bit 1 = EnFCont. In Sync Trace mode (Select_Pin_Protocol register<br>bit1:0=00), this bit is forced to ‘1: the formatter is automatically enabled in<br>continuous mode. In asynchronous mode (Select_Pin_Protocol register<br>bit1:0 <> 00), this bit can be written to activate or not the formatter.<br>Bit 0 = always 0<br>The resulting default value is 0x102<br>**Note:**In synchronous mode, because the TRACECTL pin is not mapped<br>outside the chip, the formatter is always enabled in continuous mode -this<br>way the formatter inserts some control packets to identify the source of the<br>trace packets).|
|0xE0040300|Formatter and flush<br>status|Not used in Cortex®-M3, always read as 0x00000008|


**25.16.10 Example of configuration**


      - Set the bit TRCENA in the Debug Exception and Monitor Control register (DEMCR)


      - Write the TPIU Current Port Size register to the desired value (default is 0x1 for a 1-bit
port size)


      - Write TPIU Formatter and Flush Control register to 0x102 (default value)


      - Write the TPIU Select Pin Protocol to select the sync or async mode. Example: 0x2 for
async NRZ mode (UART like)


      - Write the DBGMCU control register to 0x20 (bit IO_TRACEN) to assign TRACE I/Os
for async mode. A TPIU Sync packet is emitted at this time (FF_FF_FF_7F)


      - Configure the ITM and write the ITM Stimulus register to output a value


RM0041 Rev 6 697/709



698


**Debug support (DBG)** **RM0041**

## **25.17 DBG register map**


The following table summarizes the Debug registers.


**Table 160. Value DBG register map and reset values**







|Addr.|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0xE0042000|**DBGMCU_**<br>**IDCODE**|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|Reserved|Reserved|Reserved|Reserved|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|
|0xE0042000|Reset value(1)|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|
|0xE0042004|**DBGMCU_**<br>**CR**|Reserved|Reserved|Reserved|Reserved|DBG_TIM14_STOP|DBG_TIM13_STOP|DBG_TIM12_STOP|DBG_TIM17_STOP|DBG_TIM16_STOP|DBG_TIM15_STOP|Reserved|DBG_TIM7_STOP|DBG_TIM6_STOP|DBG_TIM5_STOP|Reserved|DBG_I2C2_SMBUS_TIMEOUT|DBG_I2C1_SMBUS_TIMEOUT|Reserved|DBG_TIM4_STOP|DBG_TIM3_STOP|DBG_TIM2_STOP|DBG_TIM1_STOP|DBG_WWDG_STOP|DBG_IWDGSTOP|TRACE_MODE[1:0]|TRACE_MODE[1:0]|TRACE_IOEN|Reserved|Reserved|DBG_STANDBY|DBG_STOP|DBG_SLEEP|
|0xE0042004|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


1. The reset value is product dependent. For more information, refer to _Section 25.6.1: MCU device ID code_ .


698/709 RM0041 Rev 6


