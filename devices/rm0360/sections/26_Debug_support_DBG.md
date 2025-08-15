**RM0360** **Debug support (DBG)**

# **26 Debug support (DBG)**

## **26.1 Overview**


The STM32F0x0 devices are built around a Arm [®] Cortex [®] -M0 core, which contains
hardware extensions for advanced debugging features. The debug extensions allow the
core to be stopped either on a given instruction fetch (breakpoint) or data access
(watchpoint). When stopped, the core’s internal state and the system’s external state may
be examined. Once examination is complete, the core and the system may be restored and
program execution resumed.


The debug features are used by the debugger host when connecting to and debugging the
STM32F0x0 MCUs.


One interface for debug is available:


      - Serial wire


**Figure 267. Block diagram of STM32F0x0 MCU and Arm** **[®]** **Cortex** **[®]** **-M0-level debug**
**support**
















|Col1|System interface|
|---|---|
|Bridge|Debug AP|
|NVIC|NVIC|



1. The debug features embedded in the Arm [®] Cortex [®] -M0 core are a subset of the Arm CoreSight Design Kit.


RM0360 Rev 5 705/775



719


**Debug support (DBG)** **RM0360**


The Arm Arm [®] Cortex [®] -M0 core provides integrated on-chip debug support. It is comprised
of:


      - SW-DP: Serial wire


      - BPU: Break point unit


      - DWT: Data watchpoint trigger


It also includes debug features dedicated to the STM32F0x0:


      - Flexible debug pinout assignment


      - MCU debug box (support for low-power modes, control over peripheral clocks, etc.)


_Note:_ _For further information on debug functionality supported by the Arm Arm_ _[®]_ _Cortex_ _[®]_ _-M0 core,_
_refer to the Arm_ _[®]_ _Cortex_ _[®]_ _-M0 Technical Reference Manual (see Section 26.2: Reference_
_Arm documentation)._

## **26.2 Reference Arm documentation**


      - Arm [®] Cortex [®] -M0 Technical Reference Manual (TRM)
It is available from:

_http://infocenter.arm.com_


      - Arm Debug Interface V5


      - Arm CoreSight Design Kit revision r1p1 Technical Reference Manual

## **26.3 Pinout and debug port pins**


The STM32F0x0 MCUs are available in various packages with different numbers of
available pins.


706/775 RM0360 Rev 5


**RM0360** **Debug support (DBG)**


**26.3.1** **SWD port pins**


Two pins are used as outputs for the SW-DP as alternate functions of general purpose I/Os.
These pins are available on all packages.

|Col1|Table 109. SW debug port pins|Col3|Col4|
|---|---|---|---|
|**SW-DP pin name**|**SW debug port**|**SW debug port**|**Pin**<br>**assignment**|
|**SW-DP pin name**|**Type**|**Debug assignment**|**Debug assignment**|
|SWDIO|IO|Serial Wire Data Input/Output|PA13|
|SWCLK|I|Serial Wire Clock|PA14|



**26.3.2** **SW-DP pin assignment**


After reset (SYSRESETn or PORESETn), the pins used for the SW-DP are assigned as
dedicated pins, immediately usable by the debugger host.


However, the MCU offers the possibility to disable the SWD port and can then release the
associated pins for general-purpose I/O (GPIO) usage. For more details on how to disable
SW-DP port pins, refer to _Section 8.3.2: I/O pin alternate function multiplexer and mapping_
_on page 127_ .


**26.3.3** **Internal pull-up and pull-down on SWD pins**


Once the SW I/O is released by the user software, the GPIO controller takes control of these
pins. The reset states of the GPIO control registers put the I/Os in the equivalent states:


      - SWDIO: input pull-up


      - SWCLK: input pull-down


_Having embedded pull-up and pull-down resistors removes the need to add external_
_resistors._

## **26.4 ID codes and locking mechanism**


There are several ID codes inside the MCU. ST strongly recommends the tool
manufacturers (for example Keil, IAR, Raisonance) to lock their debugger using the MCU
device ID located at address 0x40015800.


Only the DEV_ID[15:0] should be used for identification by the debugger/programmer tools
(the revision ID must not be taken into account).


RM0360 Rev 5 707/775



719


**Debug support (DBG)** **RM0360**


**26.4.1** **MCU device ID code**


The STM32F0xx products integrate an MCU ID code. This ID identifies the ST MCU part

number and the die revision.


This code is accessible by the software debug port (two pins) or by the user software.


For code example refer to the Appendix section _A.10.1: DBG read device ID_ .


**DBGMCU_IDCODE**


Address: 0x40015800


Only 32-bit access supported. Read-only

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15|14|13|12|11 10 9 8 7 6 5 4 3 2 1 0|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|
|||||r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:16 **REV_ID[15:0]** Revision identifier

This field indicates the revision of the device. Refer to _Table 115_ .


Bits 15:12 Reserved: read 0b0110.


Bits 11:0 **DEV_ID[11:0]** : Device identifier

This field indicates the device ID. Refer to _Table 115_ .


**Table 110. DEV_ID and REV_ID field values**

|Device|DEV_ID|Revision code|Revision number|REV_ID|
|---|---|---|---|---|
|STM32F030x4<br>STM32F030x6|0x444|A or 1|1.0|0x1000|
|STM32F070x6|0x445|A|1.0|0x1000|
|STM32F030x8|0x440|B or 1|1.1|0x1001|
|STM32F030x8|0x440|Z|1.2|0x1003|
|STM32F070xB|0x448|Y or 1|2.1|0x2001|
|STM32F070xB|0x448|W|2.2|0x2003|
|STM32F030xC|0x442|A|1.0|0x1000|


## **26.5 SWD port**


**26.5.1** **SWD protocol introduction**


This synchronous serial protocol uses two pins:


      - SWCLK: clock from host to target


      - SWDIO: bidirectional


708/775 RM0360 Rev 5


**RM0360** **Debug support (DBG)**


The protocol allows two banks of registers (DPACC registers and APACC registers) to be
read and written to.


Bits are transferred LSB-first on the wire.


For SWDIO bidirectional management, the line must be pulled-up on the board (100 kΩ
recommended by Arm).


Each time the direction of SWDIO changes in the protocol, a turnaround time is inserted
where the line is not driven by the host nor the target. By default, this turnaround time is one
bit time, however this can be adjusted by configuring the SWCLK frequency.


**26.5.2** **SWD protocol sequence**


Each sequence consist of three phases:


1. Packet request (8 bits) transmitted by the host


2. Acknowledge response (3 bits) transmitted by the target


3. Data transfer phase (33 bits) transmitted by the host or the target


**Table 111. Packet request (8-bits)**

|Bit|Name|Description|
|---|---|---|
|0|Start|Must be “1”|
|1|APnDP|0: DP Access<br>1: AP Access|
|2|RnW|0: Write Request<br>1: Read Request|
|4:3|A[3:2]|Address field of the DP or AP registers (refer to_Table 115 on_<br>_page 712_)|
|5|Parity|Single bit parity of preceding bits|
|6|Stop|0|
|7|Park|Not driven by the host. Must be read as “1” by the target<br>because of the pull-up|



Refer to the Arm [®] Cortex [®] -M0 _TRM_ for a detailed description of DPACC and APACC
registers.


The packet request is always followed by the turnaround time (default 1 bit) where neither
the host nor target drive the line.


**Table 112. ACK response (3 bits)**

|Bit|Name|Description|
|---|---|---|
|0..2|ACK|001: FAULT<br>010: WAIT<br>100: OK|



The ACK Response must be followed by a turnaround time only if it is a READ transaction
or if a WAIT or FAULT acknowledge has been received.


RM0360 Rev 5 709/775



719


**Debug support (DBG)** **RM0360**


**Table 113. DATA transfer (33 bits)**

|Bit|Name|Description|
|---|---|---|
|0..31|WDATA or<br>RDATA|Write or Read data|
|32|Parity|Single parity of the 32 data bits|



The DATA transfer must be followed by a turnaround time only if it is a READ transaction.


**26.5.3** **SW-DP state machine (reset, idle states, ID code)**


The State Machine of the SW-DP has an internal ID code which identifies the SW-DP. It

follows the JEP-106 standard. This ID code is the default Arm one and is set to
**0x0BB11477** (corresponding to Arm [®] Cortex [®] -M0).


_Note:_ _Note that the SW-DP state machine is inactive until the target reads this ID code._


      - The SW-DP state machine is in RESET STATE either after power-on reset, or after the
line is high for more than 50 cycles


      - The SW-DP state machine is in IDLE STATE if the line is low for at least two cycles
after RESET state.


      - After RESET state, it is **mandatory** to first enter into an IDLE state AND to perform a
READ access of the DP-SW ID CODE register. Otherwise, the target will issue a
FAULT acknowledge response on another transactions.


Further details of the SW-DP state machine can be found in the _Arm_ _[®]_ Cortex [®] -M0 _TRM_ and
the _CoreSight Design Kit r1p0 TRM_ .


**26.5.4** **DP and AP read/write accesses**


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
IDCODE read or CTRL/STAT read or ABORT write which are accepted even if the write
buffer is full.


      - Because of the asynchronous clock domains SWCLK and HCLK, two extra SWCLK
cycles are needed after a write transaction (after the parity bit) to make the write
effective internally. These cycles should be applied while driving the line low (IDLE
state)
This is particularly important when writing the CTRL/STAT for a power-up request. If the
next transaction (requiring a power-up) occurs immediately, it will fail.


710/775 RM0360 Rev 5


**RM0360** **Debug support (DBG)**


**26.5.5** **SW-DP registers**


Access to these registers are initiated when APnDP=0


**Table 114. SW-DP registers**












|A[3:2]|R/W|CTRLSEL bit<br>of SELECT<br>register|Register|Notes|
|---|---|---|---|---|
|00|Read||IDCODE|The manufacturer code is set to the default<br>Arm code for Cortex-M0: <br>**0x0BB11477**(identifies the SW-DP)|
|00|Write||ABORT||
|01|Read/Write|0|DP-CTRL/STAT|Purpose is to:<br>– request a system or debug power-up<br>– configure the transfer operation for AP<br>accesses<br>– control the pushed compare and pushed<br>verify operations.<br>– read some status flags (overrun, power-up<br>acknowledges)|
|01|Read/Write|1|WIRE<br>CONTROL|Purpose is to configure the physical serial<br>port protocol (like the duration of the<br>turnaround time)|
|10|Read||READ<br>RESEND|Enables recovery of the read data from a<br>corrupted debugger transfer, without<br>repeating the original AP transfer.|
|10|Write||SELECT|The purpose is to select the current access<br>port and the active 4-words register window|
|11|Read/Write||READ BUFFER|This read buffer is useful because AP<br>accesses are posted (the result of a read AP<br>request is available on the next AP<br>transaction).<br>This read buffer captures data from the AP,<br>presented as the result of a previous read,<br>without initiating a new transaction|



RM0360 Rev 5 711/775



719


**Debug support (DBG)** **RM0360**


**26.5.6** **SW-AP registers**


Access to these registers are initiated when APnDP=1


There are many AP Registers addressed as the combination of:


      - The shifted value A[3:2]


      - The current value of the DP SELECT register.


**Table 115. 32-bit debug** **port registers addressed through the shifted value A[3:2]**







|Address|A[3:2] value|Description|
|---|---|---|
|0x0|00|Reserved, must be kept at reset value.|
|0x4|01|DP CTRL/STAT register. Used to:<br>– Request a system or debug power-up<br>– Configure the transfer operation for AP accesses<br>– Control the pushed compare and pushed verify operations.<br>– Read some status flags (overrun, power-up acknowledges)|
|0x8|10|DP SELECT register: Used to select the current access port and the<br>active 4-words register window.<br>– Bits 31:24: APSEL: select the current AP<br>– Bits 23:8: reserved<br>– Bits 7:4: APBANKSEL: select the active 4-words register window on the<br>current AP<br>– Bits 3:0: reserved|
|0xC|11|DP RDBUFF register: Used to allow the debugger to get the final result<br>after a sequence of operations (without requesting new JTAG-DP<br>operation)|

## **26.6 Core debug**

Core debug is accessed through the core debug registers. Debug access to these registers
is by means of the debug access port. It consists of four registers:


**Table 116. Core debug registers**

|Register|Description|
|---|---|
|DHCSR|_The 32-bit Debug Halting Control and Status Register_<br>This provides status information about the state of the processor enable core debug<br>halt and step the processor|
|DCRSR|_The 17-bit Debug Core Register Selector Register:_<br>This selects the processor register to transfer data to or from.|
|DCRDR|_The 32-bit Debug Core Register Data Register:_<br>This holds data for reading and writing registers to and from the processor selected<br>by the DCRSR (Selector) register.|
|DEMCR|_The 32-bit Debug Exception and Monitor Control Register:_<br>This provides Vector Catching and Debug Monitor Control.|



712/775 RM0360 Rev 5


**RM0360** **Debug support (DBG)**


These registers are not reset by a system reset. They are only reset by a power-on reset.
Refer to the Arm [®] Cortex [®] -M0 TRM for further details.


To Halt on reset, it is necessary to:


      - enable the bit0 (VC_CORRESET) of the Debug and Exception Monitor Control
Register


      - enable the bit0 (C_DEBUGEN) of the Debug Halting Control and Status Register

## **26.7 BPU (Break Point Unit)**


The Cortex-M0 BPU implementation provides four breakpoint registers. The BPU is a
subset of the Flash Patch and Breakpoint (FPB) block available in Armv7-M (Cortex-M3 &
Cortex-M4).


**26.7.1** **BPU functionality**


The processor breakpoints implement PC based breakpoint functionality.


Refer to the Armv6-M Arm and the Arm CoreSight Components Technical Reference
Manual for more information about the BPU CoreSight identification registers, and their
addresses and access types.

## **26.8 DWT (Data Watchpoint)**


The Cortex-M0 DWT implementation provides two watchpoint register sets.


**26.8.1** **DWT functionality**


The processor watchpoints implement both data address and PC based watchpoint
functionality, a PC sampling register, and support comparator address masking, as
described in the Armv6-M Arm.


**26.8.2** **DWT Program Counter Sample Register**


A processor that implements the data watchpoint unit also implements the Armv6-M
optional _DWT Program Counter Sample Register_ (DWT_PCSR). This register permits a
debugger to periodically sample the PC without halting the processor. This provides coarse
grained profiling. See the _ARMv6-M Arm_ for more information.


The Cortex-M0 DWT_PCSR records both instructions that pass their condition codes and
those that fail.

## **26.9 MCU debug component (DBGMCU)**


The MCU debug component helps the debugger provide support for:


      - Low-power modes


      - Clock control for timers, watchdog and I2C during a breakpoint


RM0360 Rev 5 713/775



719


**Debug support (DBG)** **RM0360**


**26.9.1** **Debug support for low-power modes**


To enter low-power mode, the instruction WFI or WFE must be executed.


The MCU implements several low-power modes which can either deactivate the CPU clock
or reduce the power of the CPU.


The core does not allow FCLK or HCLK to be turned off during a debug session. As these
are required for the debugger connection, during a debug, they must remain active. The
MCU integrates special means to allow the user to debug software in low-power modes.


For this, the debugger host must first set some debug configuration registers to change the
low-power mode behavior:


      - In Sleep mode: FCLK and HCLK are still active. Consequently, this mode does not
impose any restrictions on the standard debug features.


      - In Stop/Standby mode, the DBG_STOP bit must be previously set by the debugger.


This enables the internal RC oscillator clock to feed FCLK and HCLK in Stop mode.


For code example refer to the Appendix section _A.10.2: DBG debug in Low-power mode_ .


**26.9.2** **Debug support for timers, watchdog and I** **[2]** **C**


During a breakpoint, it is necessary to choose how the counter of timers and watchdog
should behave:


      - They can continue to count inside a breakpoint. This is usually required when a PWM is
controlling a motor, for example.


      - They can stop to count inside a breakpoint. This is required for watchdog purposes.


For the I [2] C, the user can choose to block the SMBUS timeout during a breakpoint.


714/775 RM0360 Rev 5


**RM0360** **Debug support (DBG)**


**26.9.3** **Debug MCU configuration register (DBGMCU_CR** **)**


This register allows the configuration of the MCU under DEBUG. This concerns:


      - Low-power mode support


This DBGMCU_CR is mapped at address 0x4001 5804.


It is asynchronously reset by the PORESET (and not the system reset). It can be written by
the debugger under system reset.


If the debugger host does not support these features, it is still possible for the user software
to write to these registers.


Address: 0x40015804


Only 32-bit access supported


POR Reset: 0x0000 0000 (not reset by system reset)


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||



|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBG_<br>STAND<br>BY|DBG_<br>STOP|Res.|
||||||||||||||rw|rw||


Bits 31:3 Reserved, must be kept at reset value.









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
one after RESET (CPU clocked by the 8 MHz internal RC oscillator (HSI)). Consequently,
the software must reprogram the clock controller to enable the PLL, the Xtal, etc.
1: (FCLK=On, HCLK=On) In this case, when entering STOP mode, FCLK and HCLK are
provided by the internal RC oscillator which remains active in STOP mode. When exiting
STOP mode, the software must reprogram the clock controller to enable the PLL, the Xtal,
etc. (in the same way it would do in case of DBG_STOP=0)


RM0360 Rev 5 715/775



719


**Debug support (DBG)** **RM0360**


**26.9.4** **Debug MCU APB1 freeze register (DBGMCU_APB1_FZ)**


The DBGMCU_APB1_FZ register is used to configure the MCU under DEBUG. It concerns
some APB peripherals:


      - Timer clock counter freeze


      - I2C SMBUS timeout freeze


      - System window watchdog and independent watchdog counter freeze support


This DBGMCU_APB1_FZ is mapped at address 0x4001 5808.


The register is asynchronously reset by the POR (and not the system reset). It can be
written by the debugger under system reset.


Address offset: 0x08


Only 32-bit access are supported.


Power on reset (POR): 0x0000 0000 (not reset by system reset)








|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBG_I2C1_SMBUS_TIMEOUT|Res.|Res.|Res.|Res.|Res.|
|||||||||||rw||||||













|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|DBG_IWDG_STOP|DBG_WWDG_STOP|DBG_RTC_STOP|Res.|DBG_TIM14_STOP|Res.|Res.|DBG_TIM7_STOP|DBG_TIM6_STOP|Res.|Res.|DBG_TIM3_STOP|Res.|
||||rw|rw|rw||rw|||rw|rw|||rw||


Bits 31:22 Reserved, must be kept at reset value.


Bit 21 **DBG_I2C1_SMBUS_TIMEOUT:** SMBUS timeout mode stopped when core is halted

0: Same behavior as in normal mode

1: The SMBUS timeout is frozen


Bits 20:13 Reserved, must be kept at reset value.


Bit 12 **DBG_IWDG_STOP:** Debug independent watchdog stopped when core is halted

0: The independent watchdog counter clock continues even if the core is halted
1: The independent watchdog counter clock is stopped when the core is halted


Bit 11 **DBG_WWDG_STOP:** Debug window watchdog stopped when core is halted

0: The window watchdog counter clock continues even if the core is halted
1: The window watchdog counter clock is stopped when the core is halted


716/775 RM0360 Rev 5


**RM0360** **Debug support (DBG)**


Bit 10 **DBG_RTC_STOP** : Debug RTC stopped when core is halted

0: The clock of the RTC counter is fed even if the core is halted

1: The clock of the RTC counter is stopped when the core is halted


Bit 9 Reserved, must be kept at reset value.


Bit 8 **DBG_TIM14_STOP** : TIM14 counter stopped when core is halted

0: The counter clock of TIM14 is fed even if the core is halted

1: The counter clock of TIM14 is stopped when the core is halted


Bits 7:6 Reserved, must be kept at reset value.


Bit 5 **DBG_TIM7_STOP:** TIM7 counter stopped when core is halted.

0: The counter clock of TIM7 is fed even if the core is halted

1: The counter clock of TIM7 is stopped when the core is halted


Bit 4 **DBG_TIM6_STOP** : TIM6 counter stopped when core is halted

0: The counter clock of TIM6 is fed even if the core is halted

1: The counter clock of TIM6 is stopped when the core is halted


Bits 3:2 Reserved, must be kept at reset value.


Bit 1 **DBG_TIM3_STOP** : TIM3 counter stopped when core is halted

0: The counter clock of TIM3 is fed even if the core is halted

1: The counter clock of TIM3 is stopped when the core is halted


Bit 0 Reserved, must be kept at reset value.


RM0360 Rev 5 717/775



719


**Debug support (DBG)** **RM0360**


**26.9.5** **Debug MCU APB2 freeze register (DBGMCU_APB2_FZ)**


The DBGMCU_APB2_FZ register is used to configure the MCU under DEBUG. It concerns
some APB peripherals:


      - Timer clock counter freeze


This register is mapped at address 0x4001580C.


It is asynchronously reset by the POR (and not the system reset). It can be written by the
debugger under system reset.


Address offset: 0x0C


Only 32-bit access is supported.


POR: 0x0000 0000 (not reset by system reset)


|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBG_TIM17_STOP|DBG_TIM16_STOP|DBG_TIM15_STOP|
||||||||||||||rw|rw|rw|







|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|DBG_TIM1_STOP|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||rw||||||||||||


Bits 31:19 Reserved, must be kept at reset value.


Bit 18 **DBG_TIM17_STOP** : TIM17 counter stopped when core is halted

0: The counter clock of TIM17 is fed even if the core is halted

1: The counter clock of TIM17 is stopped when the core is halted


Bit 17 **DBG_TIM16_STOP** : TIM16 counter stopped when core is halted

0: The counter clock of TIM16 is fed even if the core is halted

1: The counter clock of TIM16 is stopped when the core is halted


Bit 16 **DBG_TIM15_STOP** : TIM15 counter stopped when core is halted

0: The counter clock of TIM15 is fed even if the core is halted

1: The counter clock of TIM15 is stopped when the core is halted


Bits 15:12 Reserved, must be kept at reset value.


Bit 11 **DBG_TIM1_STOP:** TIM1 counter stopped when core is halted

0: The counter clock of TIM 1 is fed even if the core is halted

1: The counter clock of TIM 1 is stopped when the core is halted


Bits 0:10 Reserved, must be kept at reset value.


**26.9.6** **DBG register map**


The following table summarizes the Debug registers.


718/775 RM0360 Rev 5


**RM0360** **Debug support (DBG)**


. **Table 117. DBG register map and reset values**







|Addr.|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x40015800|**DBGMCU_**<br>**IDCODE**<br>|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|REV_ID|Res.|Res.|Res.|Res.|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|DEV_ID|
|0x40015800|Reset value~~(1)~~|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|X|||||X|X|X|X|X|X|X|X|X|X|X|X|
|0x40015804|**DBGMCU_CR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBG_STANDBY|DBG_STOP|Res.|
|0x40015804|Reset value||||||||||||||||||||||||||||||0|0||
|0x40015808|**DBGMCU_**<br>**APB1_FZ**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBG_I2C1_SMBUS_TIMEOUT|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBG_IWDG_STOP|DBG_WWDG_STOP|DBG_RTC_STOP|Res.|DBG_TIM14_STOP|Res.|Res.|DBG_TIM7_STOP|DBG_TIM6_STOP|Res.|Res.|DBG_TIM3_STOP|Res.|
|0x40015808|Reset value|||||||||||0|||||||||0|0|0||0|||0|0|||0|0|
|0x4001580C|**DBGMCU_**<br>**APB2_FZ**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DBG_TIM17_STOP|DBG_TIM16_STOP|DBG_TIM15_STOP|Res.|Res.|Res.|Res.|DBG_TIM1_STOP|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x4001580C|Reset value||||||||||||||0|0|0|||||0||||||||||||


1. The reset value is product dependent. For more information, refer to _Section 26.4.1: MCU device ID code_ .


RM0360 Rev 5 719/775



719


