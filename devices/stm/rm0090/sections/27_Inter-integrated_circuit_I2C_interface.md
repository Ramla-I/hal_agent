**Inter-integrated circuit (I2C) interface** **RM0090**

# **27 Inter-integrated circuit (I2C) interface**


This section applies to the whole STM32F4xx family, unless otherwise specified.

## **27.1 I [2] C introduction**


I [2] C (inter-integrated circuit) bus Interface serves as an interface between the microcontroller
and the serial I [2] C bus. It provides multimaster capability, and controls all I [2] C bus-specific
sequencing, protocol, arbitration and timing. It supports the standard mode (Sm, up to
100 kHz) and Fm mode (Fm, up to 400 kHz).


It may be used for a variety of purposes, including CRC generation and verification, SMBus
(system management bus) and PMBus (power management bus).


Depending on specific device implementation DMA capability can be available for reduced
CPU overload.

## **27.2 I [2] C main features**


      - Parallel-bus/I [2] C protocol converter


      - Multimaster capability: the same interface can act as Master or Slave

      - I [2] C Master features:


–
Clock generation


–
Start and Stop generation

      - I [2] C Slave features:

– Programmable I [2] C Address detection


–
Dual Addressing Capability to acknowledge 2 slave addresses


–
Stop bit detection


      - Generation and detection of 7-bit/10-bit addressing and General Call


      - Supports different communication speeds:


–
Standard Speed (up to 100 kHz)


–
Fast Speed (up to 400 kHz)


      - Analog noise filter


      - Programmable digital noise filter for STM32F42xxx and STM32F43xxx


      - Status flags:


–
Transmitter/Receiver mode flag


–
End-of-Byte transmission flag

– I [2] C busy flag


      - Error flags:


– Arbitration lost condition for master mode


–
Acknowledgment failure after address/ data transmission


–
Detection of misplaced start or stop condition


–
Overrun/Underrun if clock stretching is disabled


      - 2 Interrupt vectors:


842/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


–
1 Interrupt for successful address/ data communication


–
1 Interrupt for error condition


      - Optional clock stretching


      - 1-byte buffer with DMA capability


      - Configurable PEC (packet error checking) generation or verification:


–
PEC value can be transmitted as last byte in Tx mode


–
PEC error checking for last received byte


      - SMBus 2.0 Compatibility:


–
25 ms clock low timeout delay


– 10 ms master cumulative clock low extend time


– 25 ms slave cumulative clock low extend time


–
Hardware PEC generation/verification with ACK control


–
Address Resolution Protocol (ARP) supported


      - PMBus Compatibility


_Note:_ _Some of the above features may not be available in certain products. The user should refer_
_to the product data sheet, to identify the specific features supported by the I_ _[2]_ _C interface_
_implementation._

## **27.3 I [2] C functional description**


In addition to receiving and transmitting data, this interface converts it from serial to parallel
format and vice versa. The interrupts are enabled or disabled by software. The interface is
connected to the I [2] C bus by a data pin (SDA) and by a clock pin (SCL). It can be connected
with a standard (up to 100 kHz) or fast (up to 400 kHz) I [2] C bus.


**27.3.1** **Mode selection**


The interface can operate in one of the four following modes:


      - Slave transmitter


      - Slave receiver


      - Master transmitter


      - Master receiver


By default, it operates in slave mode. The interface automatically switches from slave to
master, after it generates a START condition and from master to slave, if an arbitration loss
or a Stop generation occurs, allowing multimaster capability.


**Communication flow**


In Master mode, the I [2] C interface initiates a data transfer and generates the clock signal. A
serial data transfer always begins with a start condition and ends with a stop condition. Both
start and stop conditions are generated in master mode by software.


In Slave mode, the interface is capable of recognizing its own addresses (7 or 10-bit), and
the General Call address. The General Call address detection may be enabled or disabled
by software.


RM0090 Rev 21 843/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


Data and addresses are transferred as 8-bit bytes, MSB first. The first byte(s) following the
start condition contain the address (one in 7-bit mode, two in 10-bit mode). The address is
always transmitted in Master mode.


A 9th clock pulse follows the 8 clock cycles of a byte transfer, during which the receiver must
send an acknowledge bit to the transmitter. Refer to _Figure 238_ .


**Figure 238. I** **[2]** **C bus protocol**









Acknowledge may be enabled or disabled by software. The I [2] C interface addresses (dual
addressing 7-bit/ 10-bit and/or general call address) can be selected by software.


The block diagram of the I [2] C interface is shown in _Figure 239_ .


844/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


**Figure 239. I** **[2]** **C block diagram for STM32F40x/41x**





















RM0090 Rev 21 845/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


**Figure 240. I** **[2]** **C block diagram for STM32F42x/43x**





















1. SMBA is an optional signal in SMBus mode. This signal is not applicable if SMBus is disabled.


**27.3.2** **I** **[2]** **C slave mode**


By default the I [2] C interface operates in Slave mode. To switch from default Slave mode to
Master mode a Start condition generation is needed.


The peripheral input clock must be programmed in the I2C_CR2 register in order to
generate correct timings. The peripheral input clock frequency must be at least:


      - 2 MHz in Sm mode


      - 4 MHz in Fm mode


As soon as a start condition is detected, the address is received from the SDA line and sent
to the shift register. Then it is compared with the address of the interface (OAR1) and with
OAR2 (if ENDUAL=1) or the General Call address (if ENGC = 1).


_Note:_ _In 10-bit addressing mode, the comparison includes the header sequence (11110xx0),_
_where xx denotes the two most significant bits of the address._


846/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


**Header or address not matched** : the interface ignores it and waits for another Start
condition.


**Header matched** (10-bit mode only): the interface generates an acknowledge pulse if the
ACK bit is set and waits for the 8-bit slave address.


**Address matched** : the interface generates in sequence:


      - An acknowledge pulse if the ACK bit is set


      - The ADDR bit is set by hardware and an interrupt is generated if the ITEVFEN bit is
set.


      - If ENDUAL=1, the software has to read the DUALF bit to check which slave address
has been acknowledged.


In 10-bit mode, after receiving the address sequence the slave is always in Receiver mode.
It enters Transmitter mode on receiving a repeated Start condition followed by the header
sequence with matching address bits and the least significant bit set (11110xx1).


The TRA bit indicates whether the slave is in Receiver or Transmitter mode.


**Slave transmitter**


Following the address reception and after clearing ADDR, the slave sends bytes from the
DR register to the SDA line via the internal shift register.


The slave stretches SCL low until ADDR is cleared and DR filled with the data to be sent
(see _Figure 241_ Transfer sequencing EV1 EV3).


When the acknowledge pulse is received:


      - The TxE bit is set by hardware with an interrupt if the ITEVFEN and the ITBUFEN bits
are set.


If TxE is set and some data were not written in the I2C_DR register before the end of the
next data transmission, the BTF bit is set and the interface waits until BTF is cleared by a
read to I2C_SR1 followed by a write to the I2C_DR register, stretching SCL low.


RM0090 Rev 21 847/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


**Figure 241. Transfer sequence diagram for slave transmitter**

|S|Address|A|Col4|Col5|Data1|A|Data2|A|Col10|
|---|---|---|---|---|---|---|---|---|---|
|S|Address|A|EV1|EV3-1|EV3|EV3|EV3|EV3|EV3|


|S|Header|A|Address|A|Col6|
|---|---|---|---|---|---|
|S|Header|A|Address|A|EV1|


|Sr|Header|A|Col4|Col5|Data1|A|Col8|
|---|---|---|---|---|---|---|---|
|Sr|Header|A|EV1|EV3_1|EV3|EV3|EV3|


|DataN|NA|P|
|---|---|---|
|DataN|NA|EV3-2|


|DataN|NA|P|
|---|---|---|
|DataN|NA|EV3-2|



1. The EV1 and EV3_1 events stretch SCL low until the end of the corresponding software sequence.


2. The EV3 event stretches SCL low if the software sequence is not completed before the end of the next byte
transmission.


**Slave receiver**


Following the address reception and after clearing ADDR, the slave receives bytes from the
SDA line into the DR register via the internal shift register. After each byte the interface
generates in sequence:


      - An acknowledge pulse if the ACK bit is set


      - The RxNE bit is set by hardware and an interrupt is generated if the ITEVFEN and
ITBUFEN bit is set.


If RxNE is set and the data in the DR register is not read before the end of the next data
reception, the BTF bit is set and the interface waits until BTF is cleared by a read from the
I2C_DR register, stretching SCL low (see _Figure 242_ Transfer sequencing).


848/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


**Figure 242. Transfer sequence diagram for slave receiver**

|S|Address|A|Col4|Data1|A|Data2|A|Col9|
|---|---|---|---|---|---|---|---|---|
|S|Address|A|EV1|EV1|EV1|EV2|EV2|EV2|


|S|Header|A|Address|A|Col6|Data1|A|Col9|
|---|---|---|---|---|---|---|---|---|
|S|Header|A|Address|A|EV1|EV1|EV1|EV2|


|DataN|A|P|Col4|
|---|---|---|---|
|DataN|A|EV2|EV4|


|DataN|A|P|Col4|
|---|---|---|---|
|DataN|A|EV2|EV4|



1. The EV1 event stretches SCL low until the end of the corresponding software sequence.


2. The EV2 event stretches SCL low if the software sequence is not completed before the end of the next byte
reception.


3. After checking the SR1 register content, the user should perform the complete clearing sequence for each
flag found set.
Thus, for ADDR and STOPF flags, the following sequence is required inside the I2C interrupt routine:
READ SR1
if (ADDR == 1) {READ SR1; READ SR2}
if (STOPF == 1) {READ SR1; WRITE CR1}
The purpose is to make sure that both ADDR and STOPF flags are cleared if both are found set.


**Closing slave communication**


After the last data byte is transferred a Stop Condition is generated by the master. The
interface detects this condition and sets:


      - The STOPF bit and generates an interrupt if the ITEVFEN bit is set.


The STOPF bit is cleared by a read of the SR1 register followed by a write to the CR1
register (see EV4 in _Figure 242_ ).


**27.3.3** **I** **[2]** **C master mode**


In Master mode, the I [2] C interface initiates a data transfer and generates the clock signal. A
serial data transfer always begins with a Start condition and ends with a Stop condition.
Master mode is selected as soon as the Start condition is generated on the bus with a
START bit.


The following is the required sequence in master mode.


      - Program the peripheral input clock in I2C_CR2 register in order to generate correct
timings


      - Configure the clock control registers


      - Configure the rise time register


      - Program the I2C_CR1 register to enable the peripheral


      - Set the START bit in the I2C_CR1 register to generate a Start condition


The peripheral input clock frequency must be at least:


      - 2 MHz in Sm mode


      - 4 MHz in Fm mode


RM0090 Rev 21 849/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


**SCL master clock generation**


The CCR bits are used to generate the high and low level of the SCL clock, starting from the
generation of the rising and falling edge (respectively). As a slave may stretch the SCL line,
the peripheral checks the SCL input from the bus at the end of the time programmed in
TRISE bits after rising edge generation.


      - If the SCL line is low, it means that a slave is stretching the bus, and the high level
counter stops until the SCL line is detected high. This allows to guarantee the minimum
HIGH period of the SCL clock parameter.


      - If the SCL line is high, the high level counter keeps on counting.


Indeed, the feedback loop from the SCL rising edge generation by the peripheral to the SCL
rising edge detection by the peripheral takes time even if no slave stretches the clock. This
loopback duration is linked to the SCL rising time (impacting SCL VIH input detection), plus
delay due to the noise filter present on the SCL input path, plus delay due to internal SCL
input synchronization with APB clock. The maximum time used by the feedback loop is
programmed in the TRISE bits, so that the SCL frequency remains stable whatever the SCL
rising time.


**Start condition**


Setting the START bit causes the interface to generate a Start condition and to switch to
Master mode (MSL bit set) when the BUSY bit is cleared.


_Note:_ _In master mode, setting the START bit causes the interface to generate a ReStart condition_
_at the end of the current byte transfer._


Once the Start condition is sent:


      - The SB bit is set by hardware and an interrupt is generated if the ITEVFEN bit is set.


Then the master waits for a read of the SR1 register followed by a write in the DR register
with the Slave address (see _Figure 243_ and _Figure 244_ Transfer sequencing EV5).


**Slave address transmission**


Then the slave address is sent to the SDA line via the internal shift register.


      - In 10-bit addressing mode, sending the header sequence causes the following event:


–
The ADD10 bit is set by hardware and an interrupt is generated if the ITEVFEN bit
is set.


Then the master waits for a read of the SR1 register followed by a write in the DR
register with the second address byte (see _Figure 243_ and _Figure 244_ Transfer
sequencing).


–
The ADDR bit is set by hardware and an interrupt is generated if the ITEVFEN bit
is set.


Then the master waits for a read of the SR1 register followed by a read of the SR2
register (see _Figure 243_ and _Figure 244_ Transfer sequencing).


      - In 7-bit addressing mode, one address byte is sent.


As soon as the address byte is sent,


–
The ADDR bit is set by hardware and an interrupt is generated if the ITEVFEN bit
is set.


Then the master waits for a read of the SR1 register followed by a read of the SR2
register (see _Figure 243_ and _Figure 244_ Transfer sequencing).


850/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


The master can decide to enter Transmitter or Receiver mode depending on the LSB of the
slave address sent.


      - In 7-bit addressing mode,


–
To enter Transmitter mode, a master sends the slave address with LSB reset.


–
To enter Receiver mode, a master sends the slave address with LSB set.


      - In 10-bit addressing mode,


–
To enter Transmitter mode, a master sends the header (11110xx0) and then the
slave address, (where xx denotes the two most significant bits of the address).


–
To enter Receiver mode, a master sends the header (11110xx0) and then the
slave address. Then it should send a repeated Start condition followed by the
header (11110xx1), (where xx denotes the two most significant bits of the
address).


The TRA bit indicates whether the master is in Receiver or Transmitter mode.


**Master transmitter**


Following the address transmission and after clearing ADDR, the master sends bytes from
the DR register to the SDA line via the internal shift register.


The master waits until the first data byte is written into I2C_DR (see _Figure 243_ Transfer
sequencing EV8_1).


When the acknowledge pulse is received, the TxE bit is set by hardware and an interrupt is
generated if the ITEVFEN and ITBUFEN bits are set.


If TxE is set and a data byte was not written in the DR register before the end of the last data
transmission, BTF is set and the interface waits until BTF is cleared by a write to I2C_DR,
stretching SCL low.


**Closing the communication**


After the last byte is written to the DR register, the STOP bit is set by software to generate a
Stop condition (see _Figure 243_ Transfer sequencing EV8_2). The interface automatically
goes back to slave mode (MSL bit cleared).


_Note:_ _Stop condition should be programmed during EV8_2 event, when either TxE or BTF is set._


RM0090 Rev 21 851/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


**Figure 243. Transfer sequence diagram for master transmitter**

|S|Col2|Address|A|Col5|Col6|Data1|A|Data2|A|Col11|
|---|---|---|---|---|---|---|---|---|---|---|
|S|EV5|EV5|EV5|EV6|EV8_1|EV8|EV8|EV8|EV8|EV8|


|S|Col2|Header|A|Col5|Address|A|Col8|Col9|Data1|A|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|S|EV5|EV5|EV5|EV9|EV9|EV9|EV6|EV8_1|EV8|EV8|EV8|


|DataN|A|Col3|P|
|---|---|---|---|
|DataN|A|EV8_2|EV8_2|


|DataN|A|Col3|P|
|---|---|---|---|
|DataN|A|EV8_2|EV8_2|



1. The EV5, EV6, EV9, EV8_1 and EV8_2 events stretch SCL low until the end of the corresponding software sequence.


2. The EV8 event stretches SCL low if the software sequence is not complete before the end of the next byte transmission.


**Master receiver**


Following the address transmission and after clearing ADDR, the I [2] C interface enters
Master Receiver mode. In this mode the interface receives bytes from the SDA line into the
DR register via the internal shift register. After each byte the interface generates in

sequence:


1. An acknowledge pulse if the ACK bit is set


2. The RxNE bit is set and an interrupt is generated if the ITEVFEN and ITBUFEN bits are
set (see _Figure 244_ Transfer sequencing EV7).


If the RxNE bit is set and the data in the DR register is not read before the end of the last
data reception, the BTF bit is set by hardware and the interface waits until BTF is cleared by
a read in the DR register, stretching SCL low.


**Closing the communication**


The master sends a NACK for the last byte received from the slave. After receiving this
NACK, the slave releases the control of the SCL and SDA lines. Then the master can send
a Stop/Restart condition.


1. To generate the nonacknowledge pulse after the last received data byte, the ACK bit
must be cleared just after reading the second last data byte (after second last RxNE
event).


2. In order to generate the Stop/Restart condition, software must set the STOP/START bit
after reading the second last data byte (after the second last RxNE event).


3. In case a single byte has to be received, the Acknowledge disable is made during EV6
(before ADDR flag is cleared) and the STOP condition generation is made after EV6.


After the Stop condition generation, the interface goes automatically back to slave mode
(MSL bit cleared).


852/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


**Figure 244. Transfer sequence diagram for master receiver**


|S|Col2|Address|A|Col5|Data1|A(1)|Data2|A|Col10|
|---|---|---|---|---|---|---|---|---|---|
|S|EV5|EV5|EV5|EV6|EV6|EV6|EV7|EV7|EV7|


|DataN|NA|P|
|---|---|---|
|EV7_1|EV7_1|EV7|


|S|Col2|Header|A|Col5|Address|A|Col8|
|---|---|---|---|---|---|---|---|
|S|EV5|EV5|EV5|EV9|EV9|EV9|EV6|










|Sr|Col2|Header|A|Col5|Data1|A(1)|Data2|A|Col10|
|---|---|---|---|---|---|---|---|---|---|
|Sr|EV5|EV5|EV5|EV6|EV6|EV6|EV7|EV7|EV7|


|DataN|NA|P|
|---|---|---|
|EV7_1|EV7_1|EV7|



1. If a single byte is received, it is NA.


2. The EV5, EV6 and EV9 events stretch SCL low until the end of the corresponding software sequence.


3. The EV7 event stretches SCL low if the software sequence is not completed before the end of the next byte
reception.


4. The EV7_1 software sequence must be completed before the ACK pulse of the current byte transfer.

The procedures described below are recommended if the EV7-1 software sequence is not
completed before the ACK pulse of the current byte transfer.


These procedures must be followed to make sure:


   - The ACK bit is set low on time before the end of the last data reception


   - The STOP bit is set high after the last data reception without reception of
supplementary data.


**For 2-byte reception:**


   - Wait until ADDR = 1 (SCL stretched low until the ADDR flag is cleared)


   - Set ACK low, set POS high


   - Clear ADDR flag


   - Wait until BTF = 1 (Data 1 in DR, Data2 in shift register, SCL stretched low until a data
1 is read)


   - Set STOP high


   - Read data 1 and 2


RM0090 Rev 21 853/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


**For N >2 -byte reception, from N-2 data reception**


      - Wait until BTF = 1 (data N-2 in DR, data N-1 in shift register, SCL stretched low until
data N-2 is read)


      - Set ACK low


      - Read data N-2


      - Wait until BTF = 1 (data N-1 in DR, data N in shift register, SCL stretched low until a
data N-1 is read)


      - Set STOP high


      - Read data N-1 and N


**27.3.4** **Error conditions**


The following are the error conditions which may cause communication to fail.


**Bus error (BERR)**


This error occurs when the I [2] C interface detects an external Stop or Start condition during
an address or a data transfer. In this case:


      - the BERR bit is set and an interrupt is generated if the ITERREN bit is set


      - in Slave mode: data are discarded and the lines are released by hardware:


–
in case of a misplaced Start, the slave considers it is a restart and waits for an
address, or a Stop condition


–
in case of a misplaced Stop, the slave behaves like for a Stop condition and the
lines are released by hardware


      - In Master mode: the lines are not released and the state of the current transmission is

not affected. It is up to the software to abort or not the current transmission


**Acknowledge failure (AF)**


This error occurs when the interface detects a nonacknowledge bit. In this case:


      - the AF bit is set and an interrupt is generated if the ITERREN bit is set


      - a transmitter which receives a NACK must reset the communication:


–
If Slave: lines are released by hardware


–
If Master: a Stop or repeated Start condition must be generated by software


**Arbitration lost (ARLO)**


This error occurs when the I [2] C interface detects an arbitration lost condition. In this case


      - the ARLO bit is set by hardware (and an interrupt is generated if the ITERREN bit is
set)

      - the I [2] C Interface goes automatically back to slave mode (the MSL bit is cleared). When
the I [2] C loses the arbitration, it is not able to acknowledge its slave address in the same
transfer, but it can acknowledge it after a repeated Start from the winning master.


      - lines are released by hardware


854/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


**Overrun/underrun error (OVR)**


An overrun error can occur in slave mode when clock stretching is disabled and the I [2] C
interface is receiving data. The interface has received a byte (RxNE=1) and the data in DR
has not been read, before the next byte is received by the interface. In this case,


      - The last received byte is lost.


      - In case of Overrun error, software should clear the RxNE bit and the transmitter should
re-transmit the last received byte.


Underrun error can occur in slave mode when clock stretching is disabled and the I [2] C
interface is transmitting data. The interface has not updated the DR with the next byte
(TxE=1), before the clock comes for the next byte. In this case,


      - The same byte in the DR register is sent again.


      - The user should make sure that data received on the receiver side during an underrun
error are discarded and that the next bytes are written within the clock low time
specified in the I [2] C bus standard.


For the first byte to be transmitted, the DR must be written after ADDR is cleared and before
the first SCL rising edge. If not possible, the receiver must discard the first data.


**27.3.5** **Programmable noise filter**


The programmable noise filter is available on STM32F42xxx and STM32F43xxx devices
only.


In Fm mode, the I [2] C standard requires that spikes are suppressed to a length of 50 ns on
SDA and SCL lines.


An analog noise filter is implemented in the SDA and SCL I/Os. This filter is enabled by
default and can be disabled by setting the ANOFF bit in the I2C_FLTR register.


A digital noise filter can be enabled by configuring the DNF[3:0] bits to a non-zero value.
This suppresses the spikes on SDA and SCL inputs with a length of up to DNF[3:0] *
T PCLK1 .


Enabling the digital noise filter increases the SDA hold time by (DNF[3:0] +1)* T PCLK .

To be compliant with the maximum hold time of the I [2] C-bus specification version 2.1
(Thd:dat), the DNF bits must be programmed using the constraints shown in _Table 123_, and
assuming that the analog filter is disabled.


_Note:_ _DNF[3:0] must only be configured when the I_ _[2]_ _C is disabled (PE = 0). If the analog filter is_
_also enabled, the digital filter is added to the analog filter._


**Table 123. Maximum DNF[3:0] value to be compliant with Thd:dat(max)**

|PCLK1 frequency|Maximum DNF value|Col3|
|---|---|---|
|**PCLK1 frequency**|**Sm mode**|**Fm mode**|
|2 <= FPCLK1 <= 5|2|0|
|5 < FPCLK1 <= 10|12|0|
|10 < FPCLK1 <= 20|15|1|
|20 < FPCLK1 <= 30|15|7|



RM0090 Rev 21 855/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


**Table 123. Maximum DNF[3:0] value to be compliant with Thd:dat(max)** **(continued)**

|PCLK1 frequency|Maximum DNF value|Col3|
|---|---|---|
|**PCLK1 frequency**|**Sm mode**|**Fm mode**|
|30 < FPCLK1 <= 40|15|13|
|40 < FPCLK1 <= 50|15|15|



_Note:_ _For each frequency range, the constraint is given based on the worst case which is the_
_minimum frequency of the range. Greater DNF values can be used if the system can_
_support maximum hold time violation._


**27.3.6** **SDA/SCL line control**


      - If clock stretching is enabled:


– Transmitter mode: If TxE=1 and BTF=1: the interface holds the clock line low
before transmission to wait for the microcontroller to write the byte in the Data
register (both buffer and shift register are empty).


– Receiver mode: If RxNE=1 and BTF=1: the interface holds the clock line low after
reception to wait for the microcontroller to read the byte in the Data register (both
buffer and shift register are full).


      - If clock stretching is disabled in Slave mode:


– Overrun Error in case of RxNE=1 and no read of DR has been done before the

next byte is received. The last received byte is lost.


– Underrun Error in case TxE=1 and no write into DR has been done before the next

byte must be transmitted. The same byte is sent again.


–
Write Collision not managed.


**27.3.7** **SMBus**


**Introduction**


The System Management Bus (SMBus) is a two-wire interface through which various
devices can communicate with each other and with the rest of the system. It is based on I [2] C
principles of operation. SMBus provides a control bus for system and power management
related tasks. A system may use SMBus to pass messages to and from devices instead of
toggling individual control lines.


The System Management Bus Specification refers to three types of devices. A _slave_ is a
device that is receiving or responding to a command. A _master_ is a device that issues
commands, generates the clocks, and terminates the transfer. A _host_ is a specialized
master that provides the main interface to the system's CPU. A host must be a master-slave
and must support the SMBus host notify protocol. Only one host is allowed in a system.


**Similarities between SMBus and I** **[2]** **C**


      - 2-wire bus protocol (1 Clk, 1 Data) + SMBus Alert line optional


      - Master-slave communication, Master provides clock


      - Multi master capability

      - SMBus data format similar to I [2] C 7-bit addressing format ( _Figure 238_ ).


856/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


**Differences between SMBus and I** **[2]** **C**


The following table describes the differences between SMBus and I [2] C.


**Table 124. SMBus vs. I** **[2]** **C**

|SMBus|I2C|
|---|---|
|Max. speed 100 kHz|Max. speed 400 kHz|
|Min. clock speed 10 kHz|No minimum clock speed|
|35 ms clock low timeout|No timeout|
|Logic levels are fixed|Logic levels are VDD dependent|
|Different address types (reserved, dynamic etc.)|7-bit, 10-bit and general call slave address types|
|Different bus protocols (quick command, process<br>call etc.)|No bus protocols|



**SMBus application usage**


With System Management Bus, a device can provide manufacturer information, tell the
system what its model/part number is, save its state for a suspend event, report different
types of errors, accept control parameters, and return its status. SMBus provides a control
bus for system and power management related tasks.


**Device identification**


Any device that exists on the System Management Bus as a slave has a unique address
called the Slave Address. For the list of reserved slave addresses, refer to the SMBus
specification version. 2.0 ( _http://smbus.org/_ ).


**Bus protocols**


The SMBus specification supports up to nine bus protocols. For more details of these
protocols and SMBus address types, refer to SMBus specification version. 2.0. These
protocols should be implemented by the user software.


**Address resolution protocol (ARP)**


SMBus slave address conflicts can be resolved by dynamically assigning a new unique
address to each slave device. The Address Resolution Protocol (ARP) has the following
attributes:


      - Address assignment uses the standard SMBus physical layer arbitration mechanism


      - Assigned addresses remain constant while device power is applied; address retention
through device power loss is also allowed


      - No additional SMBus packet overhead is incurred after address assignment. (i.e.
subsequent accesses to assigned slave addresses have the same overhead as
accesses to fixed address devices.)


      - Any SMBus master can enumerate the bus


**Unique device identifier (UDID)**


In order to provide a mechanism to isolate each device for the purpose of address
assignment, each device must implement a unique device identifier (UDID).


RM0090 Rev 21 857/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


For the details on 128-bit UDID and more information on ARP, refer to SMBus specification
version 2.0.


**SMBus alert mode**


SMBus Alert is an optional signal with an interrupt line for devices that want to trade their
ability to master for a pin. SMBA is a wired-AND signal just as the SCL and SDA signals are.
SMBA is used in conjunction with the SMBus General Call Address. Messages invoked with
the SMBus are two bytes long.


A slave-only device can signal the host through SMBA that it wants to talk by setting ALERT
bit in I2C_CR1 register. The host processes the interrupt and simultaneously accesses all
SMBA devices through the _Alert Response Address_ (known as ARA having a value 0001
100X). Only the device(s) which pulled SMBA low acknowledge the Alert Response
Address. This status is identified using SMBALERT Status flag in I2C_SR1 register. The
host performs a modified Receive Byte operation. The 7 bit device address provided by the
slave transmit device is placed in the 7 most significant bits of the byte. The eighth bit can
be a zero or one.


If more than one device pulls SMBA low, the highest priority (lowest address) device wins
communication rights via standard arbitration during the slave address transfer. After
acknowledging the slave address the device must disengage its SMBA pull-down. If the
host still sees SMBA low when the message transfer is complete, it knows to read the ARA
again.
A host which does not implement the SMBA signal may periodically access the ARA.


For more details on SMBus Alert mode, refer to SMBus specification version 2.0.


**Timeout error**


There are differences in the timing specifications between I [2] C and SMBus.
SMBus defines a clock low timeout, TIMEOUT of 35 ms. Also SMBus specifies TLOW:
SEXT as the cumulative clock low extend time for a slave device. SMBus specifies TLOW:
MEXT as the cumulative clock low extend time for a master device. For more details on

these timeouts, refer to SMBus specification version 2.0.


The status flag Timeout or Tlow Error in I2C_SR1 shows the status of this feature.


**How to use the interface in SMBus mode**


To switch from I [2] C mode to SMBus mode, the following sequence should be performed.


      - Set the SMBus bit in the I2C_CR1 register


      - Configure the SMBTYPE and ENARP bits in the I2C_CR1 register as required for the
application


If you want to configure the device as a master, follow the Start condition generation
procedure in _Section 27.3.3_ . Otherwise, follow the sequence in _Section 27.3.2_ .


The application has to control the various SMBus protocols by software.


      - SMB Device Default Address acknowledged if ENARP=1 and SMBTYPE=0


      - SMB Host Header acknowledged if ENARP=1 and SMBTYPE=1


      - SMB Alert Response Address acknowledged if SMBALERT=1


858/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


**27.3.8** **DMA requests**


DMA requests (when enabled) are generated only for data transfer. DMA requests are
generated by Data register becoming empty in transmission and Data register becoming full
in reception. The DMA must be initialized and enabled before the I2C data transfer. The
DMAEN bit must be set in the I2C_CR2 register before the ADDR event. In master mode or
in slave mode when clock stretching is enabled, the DMAEN bit can also be set during the
ADDR event, before clearing the ADDR flag. The DMA request must be served before the
end of the current byte transfer. When the number of data transfers which has been
programmed for the corresponding DMA stream is reached, the DMA controller sends an
End of Transfer EOT signal to the I [2] C interface and generates a Transfer Complete interrupt
if enabled:


      - Master transmitter: In the interrupt routine after the EOT interrupt, disable DMA
requests then wait for a BTF event before programming the Stop condition.


      - Master receiver


–
When the number of bytes to be received is equal to or greater than two, the DMA
controller sends a hardware signal, EOT_1, corresponding to the last but one data
byte (number_of_bytes – 1). If, in the I2C_CR2 register, the LAST bit is set, I [2] C
automatically sends a NACK after the next byte following EOT_1. The user can
generate a Stop condition in the DMA Transfer Complete interrupt routine if
enabled.


–
When a single byte must be received: the NACK must be programmed during EV6
event, i.e. program ACK=0 when ADDR=1, before clearing ADDR flag. Then the
user can program the STOP condition either after clearing ADDR flag, or in the
DMA Transfer Complete interrupt routine.


**Transmission using DMA**


DMA mode can be enabled for transmission by setting the DMAEN bit in the I2C_CR2
register. Data are loaded from a Memory area configured using the DMA peripheral (refer to
the DMA specification) to the I2C_DR register whenever the TxE bit is set. To map a DMA
stream x for I [2] C transmission (where x is the stream number), perform the following

sequence:


1. Set the I2C_DR register address in the DMA_SxPAR register. The data are moved to
this address from the memory after each TxE event.


2. Set the memory address in the DMA_SxMA0R register (and in DMA_SxMA1R register
in the case of a bouble buffer mode). The data are loaded into I2C_DR from this
memory after each TxE event.


3. Configure the total number of bytes to be transferred in the DMA_SxNDTR register.
After each TxE event, this value is decremented.


4. Configure the DMA stream priority using the PL[0:1] bits in the DMA_SxCR register


5. Set the DIR bit in the DMA_SxCR register and configure interrupts after half transfer or
full transfer depending on application requirements.


6. Activate the stream by setting the EN bit in the DMA_SxCR register.


When the number of data transfers which has been programmed in the DMA Controller
registers is reached, the DMA controller sends an End of Transfer EOT/ EOT_1 signal to the
I [2] C interface and the DMA generates an interrupt, if enabled, on the DMA stream interrupt
vector.


_Note:_ _Do not enable the ITBUFEN bit in the I2C_CR2 register if DMA is used for transmission._


RM0090 Rev 21 859/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


**Reception using DMA**


DMA mode can be enabled for reception by setting the DMAEN bit in the I2C_CR2 register.
Data are loaded from the I2C_DR register to a Memory area configured using the DMA
peripheral (refer to the DMA specification) whenever a data byte is received. To map a DMA
stream x for I [2] C reception (where x is the stream number), perform the following sequence:


1. Set the I2C_DR register address in DMA_SxPAR register. The data are moved from
this address to the memory after each RxNE event.


2. Set the memory address in the DMA_SxMA0R register (and in DMA_SxMA1R register
in the case of a bouble buffer mode). The data are loaded from the I2C_DR register to
this memory area after each RxNE event.


3. Configure the total number of bytes to be transferred in the DMA_SxNDTR register.
After each RxNE event, this value is decremented.


4. Configure the stream priority using the PL[0:1] bits in the DMA_SxCR register


5. Reset the DIR bit and configure interrupts in the DMA_SxCR register after half transfer
or full transfer depending on application requirements.


6. Activate the stream by setting the EN bit in the DMA_SxCR register.


When the number of data transfers which has been programmed in the DMA Controller
registers is reached, the DMA controller sends an End of Transfer EOT/ EOT_1 signal to the
I [2] C interface and DMA generates an interrupt, if enabled, on the DMA stream interrupt
vector.


_Note:_ _Do not enable the ITBUFEN bit in the I2C_CR2 register if DMA is used for reception._


**27.3.9** **Packet error checking**


A PEC calculator has been implemented to improve the reliability of communication. The
PEC is calculated by using the C(x) = x [8] + x [2] + x + 1 CRC-8 polynomial serially on each bit.


      - PEC calculation is enabled by setting the ENPEC bit in the I2C_CR1 register. PEC is a
CRC-8 calculated on all message bytes including addresses and R/W bits.


–
In transmission: set the PEC transfer bit in the I2C_CR1 register after the TxE
event corresponding to the last byte. The PEC is transferred after the last
transmitted byte.


–
In reception: set the PEC bit in the I2C_CR1 register after the RxNE event
corresponding to the last byte so that the receiver sends a NACK if the next
received byte is not equal to the internally calculated PEC. In case of MasterReceiver, a NACK must follow the PEC whatever the check result. The PEC must


860/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


be set before the ACK of the CRC reception in slave mode. It must be set when
the ACK is set low in master mode.


      - A PECERR error flag/interrupt is also available in the I2C_SR1 register.


      - If DMA and PEC calculation are both enabled:
– In transmission: when the I [2] C interface receives an EOT signal from the DMA
controller, it automatically sends a PEC after the last byte.


–
In reception: when the I [2] C interface receives an EOT_1 signal from the DMA
controller, it automatically considers the next byte as a PEC and checks it. A DMA
request is generated after PEC reception.


      - To allow intermediate PEC transfers, a control bit is available in the I2C_CR2 register
(LAST bit) to determine if it is really the last DMA transfer or not. If it is the last DMA
request for a master receiver, a NACK is automatically sent after the last received byte.


      - PEC calculation is corrupted by an arbitration loss.

## **27.4 I [2] C interrupts**


The table below gives the list of I [2] C interrupt requests.


**Table 125. I** **[2]** **C Interrupt requests**












|Interrupt event|Event flag|Enable control bit|
|---|---|---|
|Start bit sent (Master)|SB|ITEVFEN|
|Address sent (Master) or Address matched (Slave)|ADDR|ADDR|
|10-bit header sent (Master)|ADD10|ADD10|
|Stop received (Slave)|STOPF|STOPF|
|Data byte transfer finished|BTF|BTF|
|Receive buffer not empty|RxNE|ITEVFEN and ITBUFEN|
|Transmit buffer empty|TxE|TxE|
|Bus error|BERR|ITERREN|
|Arbitration loss (Master)|ARLO|ARLO|
|Acknowledge failure|AF|AF|
|Overrun/Underrun|OVR|OVR|
|PEC error|PECERR|PECERR|
|Timeout/Tlow error|TIMEOUT|TIMEOUT|
|SMBus Alert|SMBALERT|SMBALERT|



_Note:_ _SB, ADDR, ADD10, STOPF, BTF, RxNE and TxE are logically OR-ed on the same interrupt_
_channel._


_BERR, ARLO, AF, OVR, PECERR, TIMEOUT and SMBALERT are logically OR-ed on the_
_same interrupt channel._


RM0090 Rev 21 861/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


**Figure 245. I** **[2]** **C interrupt mapping diagram**



|BERR|Col2|
|---|---|
|ARLO|ARLO|
|AF||
|OVR|OVR|
|PECERR|PECERR|
|TIMEOUT|TIMEOUT|
|SMBALERT|SMBALERT|


862/1757 RM0090 Rev 21




**RM0090** **Inter-integrated circuit (I2C) interface**

## **27.5 I [2] C debug mode**


When the microcontroller enters the debug mode (Cortex [®] -M4 with FPU core halted), the
SMBUS timeout either continues to work normally or stops, depending on the
DBG_I2Cx_SMBUS_TIMEOUT configuration bits in the DBG module. For more details,
refer to _Section 38.16.2: Debug support for timers, watchdog, bxCAN and I_ _[2]_ _C_ .

## **27.6 I [2] C registers**


Refer to _Section 1.1_ for a list of abbreviations used in register descriptions.


The peripheral registers have to be accessed by half-words (16 bits) or words (32 bits).


**27.6.1** **I** **[2]** **C Control register 1 (I2C_CR1)**


Address offset: 0x00

Reset value: 0x0000







|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SWRST|Res.|ALERT|PEC|POS|ACK|STOP|START|NO<br>STRETCH|ENGC|ENPEC|ENARP|SMB<br>TYPE|Res.|SMBU<br>S|PE|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bit 15 **SWRST** : Software reset

When set, the I2C is under reset state. Before resetting this bit, make sure the I2C lines are
released and the bus is free.
0: I [2] C Peripheral not under reset
1: I [2] C Peripheral under reset state

_Note: This bit can be used to reinitialize the peripheral after an error or a locked state. As an_
_example, if the BUSY bit is set and remains locked due to a glitch on the bus, the_
_SWRST bit can be used to exit from this state._


Bit 14 Reserved, must be kept at reset value


Bit 13 **ALERT** : SMBus alert

This bit is set and cleared by software, and cleared by hardware when PE=0.
0: Releases SMBA pin high. Alert Response Address Header followed by NACK.
1: Drives SMBA pin low. Alert Response Address Header followed by ACK.


Bit 12 **PEC** : Packet error checking

This bit is set and cleared by software, and cleared by hardware when PEC is transferred or
by a START or Stop condition or when PE=0.
0: No PEC transfer

1: PEC transfer (in Tx or Rx mode)

_Note: PEC calculation is corrupted by an arbitration loss._


Bit 11 **POS** : Acknowledge/PEC Position (for data reception)

This bit is set and cleared by software and cleared by hardware when PE=0.
0: ACK bit controls the (N)ACK of the current byte being received in the shift register. The
PEC bit indicates that current byte in shift register is a PEC.
1: ACK bit controls the (N)ACK of the next byte which is received in the shift register. The
PEC bit indicates that the next byte in the shift register is a PEC

_Note: The POS bit must be used only in 2-byte reception configuration in master mode. It_
_must be configured before data reception starts, as described in the 2-byte reception_
_procedure recommended in Section : Master receiver on page 852._


RM0090 Rev 21 863/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


Bit 10 **ACK** : Acknowledge enable

This bit is set and cleared by software and cleared by hardware when PE=0.
0: No acknowledge returned
1: Acknowledge returned after a byte is received (matched address or data)


Bit 9 **STOP** : Stop generation

The bit is set and cleared by software, cleared by hardware when a Stop condition is
detected, set by hardware when a timeout error is detected.

In Master mode:

0: No Stop generation.
1: Stop generation after the current byte transfer or after the current Start condition is sent.

In Slave mode:

0: No Stop generation.
1: Release the SCL and SDA lines after the current byte transfer.


Bit 8 **START** : Start generation

This bit is set and cleared by software and cleared by hardware when start is sent or PE=0.

In Master mode:

0: No Start generation
1: Repeated start generation

In Slave mode:

0: No Start generation
1: Start generation when the bus is free


Bit 7 **NOSTRETCH** : Clock stretching disable (Slave mode)

This bit is used to disable clock stretching in slave mode when ADDR or BTF flag is set, until
it is reset by software.
0: Clock stretching enabled
1: Clock stretching disabled


Bit 6 **ENGC** : General call enable

0: General call disabled. Address 00h is NACKed.

1: General call enabled. Address 00h is ACKed.


Bit 5 **ENPEC:** PEC enable

0: PEC calculation disabled

1: PEC calculation enabled


Bit 4 **ENARP** : ARP enable

0: ARP disable

1: ARP enable

SMBus Device default address recognized if SMBTYPE=0
SMBus Host address recognized if SMBTYPE=1


Bit 3 **SMBTYPE** : SMBus type

0: SMBus Device

1: SMBus Host


864/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


Bit 2 Reserved, must be kept at reset value


Bit 1 **SMBUS** : SMBus mode
0: I [2] C mode

1: SMBus mode


Bit 0 **PE** : Peripheral enable

0: Peripheral disable
1: Peripheral enable

_Note: If this bit is reset while a communication is on going, the peripheral is disabled at the_
_end of the current communication, when back to IDLE state._
_All bit resets due to PE=0 occur at the end of the communication._

_In master mode, this bit must not be reset before the end of the communication._


_Note:_ _When the STOP, START or PEC bit is set, the software must not perform any write access_
_to I2C_CR1 before this bit is cleared by hardware. Otherwise there is a risk of setting a_
_second STOP, START or PEC request._


**27.6.2** **I** **[2]** **C Control register 2 (I2C_CR2)**


Address offset: 0x04

Reset value: 0x0000

|15 14 13|12|11|10|9|8|7 6|5 4 3 2 1 0|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|LAST|DMAEN|ITBUFEN|ITEVTEN|ITERREN|Reserved|FREQ[5:0]|FREQ[5:0]|FREQ[5:0]|FREQ[5:0]|FREQ[5:0]|FREQ[5:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:13 Reserved, must be kept at reset value


Bit 12 **LAST** : DMA last transfer

0: Next DMA EOT is not the last transfer

1: Next DMA EOT is the last transfer

_Note: This bit is used in master receiver mode to permit the generation of a NACK on the last_
_received data._


Bit 11 **DMAEN** : DMA requests enable

0: DMA requests disabled
1: DMA request enabled when TxE=1 or RxNE =1


Bit 10 **ITBUFEN** : Buffer interrupt enable

0: TxE = 1 or RxNE = 1 does not generate any interrupt.
1: TxE = 1 or RxNE = 1 generates Event Interrupt (whatever the state of DMAEN)


RM0090 Rev 21 865/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


Bit 9 **ITEVTEN** : Event interrupt enable

0: Event interrupt disabled
1: Event interrupt enabled
This interrupt is generated when:

–
SB = 1 (Master)

–
ADDR = 1 (Master/Slave)

–
ADD10= 1 (Master)

–
STOPF = 1 (Slave)

– BTF = 1 with no TxE or RxNE event

– TxE event to 1 if ITBUFEN = 1

– RxNE event to 1if ITBUFEN = 1


Bit 8 **ITERREN** : Error interrupt enable

0: Error interrupt disabled
1: Error interrupt enabled
This interrupt is generated when:

– BERR = 1

– ARLO = 1

– AF = 1

– OVR = 1

– PECERR = 1

– TIMEOUT = 1

– SMBALERT = 1


Bits 7:6 Reserved, must be kept at reset value


Bits 5:0 **FREQ[5:0]** : Peripheral clock frequency

The FREQ bits must be configured with the APB clock frequency value (I2C peripheral
connected to APB). The FREQ field is used by the peripheral to generate data setup and
hold times compliant with the I2C specifications. The minimum allowed frequency is 2 MHz,
the maximum frequency is limited by the maximum APB frequency and cannot exceed
50 MHz (peripheral intrinsic maximum limit).

0b000000: Not allowed

0b000001: Not allowed

0b000010: 2 MHz

...

0b110010: 50 MHz

Higher than 0b101010: Not allowed


866/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


**27.6.3** **I** **[2]** **C Own address register 1 (I2C_OAR1)**


Address offset: 0x08

Reset value: 0x0000

|15|14 13 12 11 10|9 8|Col4|7 6 5 4 3 2 1|Col6|Col7|Col8|Col9|Col10|Col11|0|
|---|---|---|---|---|---|---|---|---|---|---|---|
|ADD<br>MODE|Reserved|ADD[9:8]|ADD[9:8]|ADD[7:1]|ADD[7:1]|ADD[7:1]|ADD[7:1]|ADD[7:1]|ADD[7:1]|ADD[7:1]|ADD0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 15 **ADDMODE** Addressing mode (slave mode)

0: 7-bit slave address (10-bit address not acknowledged)
1: 10-bit slave address (7-bit address not acknowledged)


Bit 14 Should always be kept at 1 by software.


Bits 13:10 Reserved, must be kept at reset value


Bits 9:8 **ADD[9:8]** : Interface address

7-bit addressing mode: don’t care
10-bit addressing mode: bits9:8 of address


Bits 7:1 **ADD[7:1]** : Interface address

bits 7:1 of address


Bit 0 **ADD0** : Interface address

7-bit addressing mode: don’t care
10-bit addressing mode: bit 0 of address


**27.6.4** **I** **[2]** **C Own address register 2 (I2C_OAR2)**


Address offset: 0x0C

Reset value: 0x0000

|15 14 13 12 11 10 9 8|7 6 5 4 3 2 1|Col3|Col4|Col5|Col6|Col7|Col8|0|
|---|---|---|---|---|---|---|---|---|
|Reserved|ADD2[7:1]|ADD2[7:1]|ADD2[7:1]|ADD2[7:1]|ADD2[7:1]|ADD2[7:1]|ADD2[7:1]|ENDUAL|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:8 Reserved, must be kept at reset value


Bits 7:1 **ADD2[7:1]** : Interface address

bits 7:1 of address in dual addressing mode


Bit 0 **ENDUAL** : Dual addressing mode enable

0: Only OAR1 is recognized in 7-bit addressing mode
1: Both OAR1 and OAR2 are recognized in 7-bit addressing mode


RM0090 Rev 21 867/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


**27.6.5** **I** **[2]** **C Data register (I2C_DR)**


Address offset: 0x10

Reset value: 0x0000

|15 14 13 12 11 10 9 8|7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|DR[7:0]|DR[7:0]|DR[7:0]|DR[7:0]|DR[7:0]|DR[7:0]|DR[7:0]|DR[7:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:8 Reserved, must be kept at reset value


Bits 7:0 **DR[7:0]** 8-bit data register

Byte received or to be transmitted to the bus.

– Transmitter mode: Byte transmission starts automatically when a byte is written in the DR
register. A continuous transmit stream can be maintained if the next data to be transmitted is
put in DR once the transmission is started (TxE=1)

– Receiver mode: Received byte is copied into DR (RxNE=1). A continuous transmit stream
can be maintained if DR is read before the next data byte is received (RxNE=1).

_Note: In slave mode, the address is not copied into DR._


_Write collision is not managed (DR can be written if TxE=0)._


_If an ARLO event occurs on ACK pulse, the received byte is not copied into DR and so_
_cannot be read._


**27.6.6** **I** **[2]** **C Status register 1 (I2C_SR1)**


Address offset: 0x14

Reset value: 0x0000







|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SMB<br>ALERT|TIME<br>OUT|Res.|PEC<br>ERR|OVR|AF|ARLO|BERR|TxE|RxNE|Res.|STOPF|ADD10|BTF|ADDR|SB|
|rc_w0|rc_w0|rc_w0|rc_w0|rc_w0|rc_w0|rc_w0|rc_w0|r|r|r|r|r|r|r|r|


Bit 15 **SMBALERT** : SMBus alert

In SMBus host mode:

0: no SMBALERT

1: SMBALERT event occurred on pin

In SMBus slave mode:

0: no SMBALERT response address header
1: SMBALERT response address header to SMBALERT LOW received

– Cleared by software writing 0, or by hardware when PE=0.


868/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


Bit 14 **TIMEOUT** : Timeout or Tlow error

0: No timeout error

1: SCL remained LOW for 25 ms (Timeout)

or

Master cumulative clock low extend time more than 10 ms (Tlow:mext)

or

Slave cumulative clock low extend time more than 25 ms (Tlow:sext)

– When set in slave mode: slave resets the communication and lines are released by
hardware

– When set in master mode: Stop condition sent by hardware

– Cleared by software writing 0, or by hardware when PE=0.

_Note: This functionality is available only in SMBus mode._


Bit 13 Reserved, must be kept at reset value


Bit 12 **PECERR** : PEC Error in reception

0: no PEC error: receiver returns ACK after PEC reception (if ACK=1)
1: PEC error: receiver returns NACK after PEC reception (whatever ACK)

– Cleared by software writing 0, or by hardware when PE=0.

_Note: When the received CRC is wrong, PECERR is not set in slave mode if the PEC control_
_bit is not set before the end of the CRC reception. Nevertheless, reading the PEC value_
_determines whether the received CRC is right or wrong._


Bit 11 **OVR** : Overrun/Underrun

0: No overrun/underrun

1: Overrun or underrun

– Set by hardware in slave mode when NOSTRETCH=1 and:

– In reception when a new byte is received (including ACK pulse) and the DR register has not
been read yet. New received byte is lost.

– In transmission when a new byte should be sent and the DR register has not been written
yet. The same byte is sent twice.

– Cleared by software writing 0, or by hardware when PE=0.

_Note: If the DR write occurs very close to SCL rising edge, the sent data is unspecified and a_
_hold timing error occurs_


Bit 10 **AF** : Acknowledge failure

0: No acknowledge failure
1: Acknowledge failure

– Set by hardware when no acknowledge is returned.

– Cleared by software writing 0, or by hardware when PE=0.


Bit 9 **ARLO** : Arbitration lost (master mode)

0: No Arbitration Lost detected

1: Arbitration Lost detected

Set by hardware when the interface loses the arbitration of the bus to another master

– Cleared by software writing 0, or by hardware when PE=0.

After an ARLO event the interface switches back automatically to Slave mode (MSL=0).

_Note: In SMBUS, the arbitration on the data in slave mode occurs only during the data phase,_
_or the acknowledge transmission (not on the address acknowledge)._


RM0090 Rev 21 869/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


Bit 8 **BERR** : Bus error

0: No misplaced Start or Stop condition
1: Misplaced Start or Stop condition

– Set by hardware when the interface detects an SDA rising or falling edge while SCL is high,
occurring in a non-valid position during a byte transfer.

– Cleared by software writing 0, or by hardware when PE=0.


Bit 7 **TxE** : Data register empty (transmitters)

0: Data register not empty
1: Data register empty

– Set when DR is empty in transmission. TxE is not set during address phase.

– Cleared by software writing to the DR register or by hardware after a start or a stop condition
or when PE=0.

TxE is not set if either a NACK is received, or if next byte to be transmitted is PEC (PEC=1)

_Note: TxE is not cleared by writing the first data being transmitted, or by writing data when_
_BTF is set, as in both cases the data register is still empty._


Bit 6 **RxNE** : Data register not empty (receivers)

0: Data register empty
1: Data register not empty

– Set when data register is not empty in receiver mode. RxNE is not set during address phase.

– Cleared by software reading or writing the DR register or by hardware when PE=0.

RxNE is not set in case of ARLO event.

_Note: RxNE is not cleared by reading data when BTF is set, as the data register is still full._


Bit 5 Reserved, must be kept at reset value


Bit 4 **STOPF** : Stop detection (slave mode)

0: No Stop condition detected
1: Stop condition detected

– Set by hardware when a Stop condition is detected on the bus by the slave after an
acknowledge (if ACK=1).

– Cleared by software reading the SR1 register followed by a write in the CR1 register, or by
hardware when PE=0

_Note: The STOPF bit is not set after a NACK reception._
_It is recommended to perform the complete clearing sequence (READ SR1 then_
_WRITE CR1) after the STOPF is set. Refer to Figure 242._


Bit 3 **ADD10** : 10-bit header sent (Master mode)

0: No ADD10 event occurred.

1: Master has sent first address byte (header).

– Set by hardware when the master has sent the first byte in 10-bit address mode.

– Cleared by software reading the SR1 register followed by a write in the DR register of the
second address byte, or by hardware when PE=0.

_Note: ADD10 bit is not set after a NACK reception_


870/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


Bit 2 **BTF** : Byte transfer finished

0: Data byte transfer not done
1: Data byte transfer succeeded

– Set by hardware when NOSTRETCH=0 and:

– In reception when a new byte is received (including ACK pulse) and DR has not been read
yet (RxNE=1).

– In transmission when a new byte should be sent and DR has not been written yet (TxE=1).

– Cleared by software by either a read or write in the DR register or by hardware after a start or
a stop condition in transmission or when PE=0.

_Note: The BTF bit is not set after a NACK reception_

_The BTF bit is not set if next byte to be transmitted is the PEC (TRA=1 in I2C_SR2_
_register and PEC=1 in I2C_CR1 register)_


Bit 1 **ADDR** : Address sent (master mode)/matched (slave mode)

This bit is cleared by software reading SR1 register followed reading SR2, or by hardware
when PE=0.

Address matched (Slave)

0: Address mismatched or not received.

1: Received address matched.

– Set by hardware as soon as the received slave address matched with the OAR registers
content or a general call or a SMBus Device Default Address or SMBus Host or SMBus Alert
is recognized. (when enabled depending on configuration).

_Note: In slave mode, it is recommended to perform the complete clearing sequence (READ_
_SR1 then READ SR2) after ADDR is set. Refer to Figure 242._

Address sent (Master)

0: No end of address transmission

1: End of address transmission

– For 10-bit addressing, the bit is set after the ACK of the 2nd byte.

– For 7-bit addressing, the bit is set after the ACK of the byte.

_Note: ADDR is not set after a NACK reception_


Bit 0 **SB** : Start bit (Master mode)

0: No Start condition

1: Start condition generated.

– Set when a Start condition generated.

– Cleared by software by reading the SR1 register followed by writing the DR register, or by
hardware when PE=0


**27.6.7** **I** **[2]** **C Status register 2 (I2C_SR2)**


Address offset: 0x18

Reset value: 0x0000


_Note:_ _Reading I2C_SR2 after reading I2C_SR1 clears the ADDR flag, even if the ADDR flag was_
_set after reading I2C_SR1. Consequently, I2C_SR2 must be read only when ADDR is found_
_set in I2C_SR1 or when the STOPF bit is cleared._

|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|DUALF|SMB<br>HOST|SMBDE<br>FAULT|GEN<br>CALL|Res.|TRA|BUSY|MSL|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



RM0090 Rev 21 871/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


Bits 15:8 **PEC[7:0]** Packet error checking register

This register contains the internal PEC when ENPEC=1.


Bit 7 **DUALF** : Dual flag (Slave mode)

0: Received address matched with OAR1

1: Received address matched with OAR2

– Cleared by hardware after a Stop condition or repeated Start condition, or when PE=0.


Bit 6 **SMBHOST** : SMBus host header (Slave mode)

0: No SMBus Host address

1: SMBus Host address received when SMBTYPE=1 and ENARP=1.

– Cleared by hardware after a Stop condition or repeated Start condition, or when PE=0.


Bit 5 **SMBDEFAULT** : SMBus device default address (Slave mode)

0: No SMBus Device Default address

1: SMBus Device Default address received when ENARP=1

– Cleared by hardware after a Stop condition or repeated Start condition, or when PE=0.


Bit 4 **GENCALL** : General call address (Slave mode)

0: No General Call

1: General Call Address received when ENGC=1

– Cleared by hardware after a Stop condition or repeated Start condition, or when PE=0.


Bit 3 Reserved, must be kept at reset value


Bit 2 **TRA** : Transmitter/receiver

0: Data bytes received
1: Data bytes transmitted
This bit is set depending on the R/W bit of the address byte, at the end of total address
phase.
It is also cleared by hardware after detection of Stop condition (STOPF=1), repeated Start
condition, loss of bus arbitration (ARLO=1), or when PE=0.


Bit 1 **BUSY** : Bus busy

0: No communication on the bus

1: Communication ongoing on the bus

– Set by hardware on detection of SDA or SCL low

– cleared by hardware on detection of a Stop condition.

It indicates a communication in progress on the bus. This information is still updated when
the interface is disabled (PE=0).


Bit 0 **MSL** : Master/slave

0: Slave mode

1: Master mode

– Set by hardware as soon as the interface is in Master mode (SB=1).

– Cleared by hardware after detecting a Stop condition on the bus or a loss of arbitration
(ARLO=1), or by hardware when PE=0.


_Note:_ _Reading I2C_SR2 after reading I2C_SR1 clears the ADDR flag, even if the ADDR flag was_
_set after reading I2C_SR1. Consequently, I2C_SR2 must be read only when ADDR is found_
_set in I2C_SR1 or when the STOPF bit is cleared._


872/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


**27.6.8** **I** **[2]** **C Clock control register (I2C_CCR)**


Address offset: 0x1C

Reset value: 0x0000


_Note:_ _f_ _PCLK1_ _must be at least 2 MHz to achieve Sm mode I²C frequencies. It must be at least 4_
_MHz to achieve Fm mode I²C frequencies. It must be a multiple of 10MHz to reach the_
_400 kHz maximum I²C Fm mode clock._


_The CCR register must be configured only when the I2C is disabled (PE = 0)._

|15|14|13 12|11 10 9 8 7 6 5 4 3 2 1 0|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|F/S|DUTY|Reserved|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 15 **F/S:** I2C master mode selection

0: Sm mode I2C

1: Fm mode I2C


Bit 14 **DUTY:** Fm mode duty cycle
0: Fm mode t low /t high = 2
1: Fm mode t low /t high = 16/9 (see CCR)


Bits 13:12 Reserved, must be kept at reset value


Bits 11:0 **CCR[11:0]:** Clock control register in Fm/Sm mode (Master mode)

Controls the SCL clock in master mode.

Sm mode or SMBus:

T high = CCR * T PCLK1
T low = CCR * T PCLK1
Fm mode:

If DUTY = 0:
T high = CCR * T PCLK1
T low = 2 * CCR * T PCLK1
If DUTY = 1:
T high = 9 * CCR * T PCLK1
T low = 16 * CCR * T PCLK1
For instance: in Sm mode, to generate a 100 kHz SCL frequency:
If FREQ = 08, T PCLK1 = 125 ns so CCR must be programmed with 0x28
(0x28 <=> 40d x 125 ns = 5000 ns.)

_Note: The minimum allowed value is 0x04, except in FAST DUTY mode where the minimum_
_allowed value is 0x01_

_t_ _= t_ _+ t_ _._
_high_ _r(SCL)_ _w(SCLH)_
_t_ _low_ _= t_ _f(SCL)_ _+ t_ _w(SCLL)_ _._
_Where the I2C parameters below are part of the I2C standard specification._

_- t_ _= SCL clock rise time from 30% to 70%._
_r(SCL)_

_- t_ _= SCL clock fall time from 70% to 30%._
_f(SCL)_

_- t_ _w(SCLH)_ _= SCL clock high time measure at 70%._

_- t_ _= SCL clock low time measure at 30%._
_w(SCLL)_
_I2C communication speed, fSCL ~ 1/(thigh + tlow). The real frequency may differ due to_
_the analog noise filter input delay._
_The CCR register must be configured only when the I_ _[2]_ _C is disabled (PE = 0)._


RM0090 Rev 21 873/1757



875


**Inter-integrated circuit (I2C) interface** **RM0090**


**27.6.9** **I** **[2]** **C TRISE register (I2C_TRISE)**


Address offset: 0x20

Reset value: 0x0002

|15 14 13 12 11 10 9 8 7 6|5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|
|---|---|---|---|---|---|---|
|Reserved|TRISE[5:0]|TRISE[5:0]|TRISE[5:0]|TRISE[5:0]|TRISE[5:0]|TRISE[5:0]|
|Reserved|rw|rw|rw|rw|rw|rw|



Bits 15:6 Reserved, must be kept at reset value


Bits 5:0 **TRISE[5:0]** : Maximum rise time in Fm/Sm mode (Master mode)

These bits should provide the maximum duration of the SCL feedback loop in master mode.
The purpose is to keep a stable SCL frequency whatever the SCL rising edge duration.
These bits must be programmed with the maximum SCL rise time given in the I [2] C bus
specification, incremented by 1.
For instance: in Sm mode, the maximum allowed SCL rise time is 1000 ns.
If, in the I2C_CR2 register, the value of FREQ[5:0] bits is equal to 0x08 and T PCLK1 = 125 ns
therefore the TRISE[5:0] bits must be programmed with 09h.
(1000 ns / 125 ns = 8 + 1)
The filter value can also be added to TRISE[5:0].
If the result is not an integer, TRISE[5:0] must be programmed with the integer part, in order
to respect the t HIGH parameter.
_Note: TRISE[5:0] must be configured only when the I2C is disabled (PE = 0)._


**27.6.10** **I** **[2]** **C FLTR register (I2C_FLTR)**


Address offset: 0x24


Reset value: 0x0000


The I2C_FLTR is available on STM32F42xxx and STM32F43xxx only.

|15 14 13 12 11 10 9 8 7 6 5|4|3 2 1 0|Col4|Col5|Col6|
|---|---|---|---|---|---|
|Reserved|ANOFF|DNF[3:0]|DNF[3:0]|DNF[3:0]|DNF[3:0]|
|Reserved|rw|rw|rw|rw|rw|



Bits 15:5 Reserved, must be kept at reset value


Bit 4 **ANOFF** : Analog noise filter OFF

0: Analog noise filter enable
1: Analog noise filter disable

_Note: ANOFF must be configured only when the I2C is disabled (PE = 0)._


Bits 3:0 **DNF[3:0]** : Digital noise filter

These bits are used to configure the digital noise filter on SDA and SCL inputs. The digital filter
suppresses the spikes with a length of up to DNF[3:0] * TPCLK1.

0000: Digital noise filter disable
0001: Digital noise filter enabled and filtering capability up to 1* TPCLK1.

...

1111: Digital noise filter enabled and filtering capability up to 15* TPCLK1.

_Note: DNF[3:0] must be configured only when the I2C is disabled (PE = 0). If the analog filter_
_is also enabled, the digital filter is added to the analog filter._


874/1757 RM0090 Rev 21


**RM0090** **Inter-integrated circuit (I2C) interface**


**27.6.11** **I** **[2]** **C register map**


The table below provides the I [2] C register map and reset values.


**Table 126. I** **[2]** **C register map and reset values**





































































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**I2C_CR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|SWRST|Reserved|ALERT|PEC|POS|ACK|STOP|START|NOSTRETCH|ENGC|ENPEC|ENARP|SMBTYPE|Reserved|SMBUS|PE|
|0x00|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x04|**I2C_CR2**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|LAST|DMAEN|ITBUFEN|ITEVTEN|ITERREN|Reserved|Reserved|FREQ[5:0]|FREQ[5:0]|FREQ[5:0]|FREQ[5:0]|FREQ[5:0]|FREQ[5:0]|
|0x04|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x08|**I2C_OAR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|ADDMODE|Reserved|Reserved|Reserved|Reserved|Reserved|ADD[9:8]|ADD[9:8]|ADD[7:1]|ADD[7:1]|ADD[7:1]|ADD[7:1]|ADD[7:1]|ADD[7:1]|ADD[7:1]|ADD0|
|0x08|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0C|**I2C_OAR2**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|ADD2[7:1]|ADD2[7:1]|ADD2[7:1]|ADD2[7:1]|ADD2[7:1]|ADD2[7:1]|ADD2[7:1]|ENDUAL|
|0x0C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|
|0x10|**I2C_DR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|DR[7:0]|DR[7:0]|DR[7:0]|DR[7:0]|DR[7:0]|DR[7:0]|DR[7:0]|DR[7:0]|
|0x10|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|
|0x14|**I2C_SR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|SMBALERT|TIMEOUT|Reserved|PECERR|OVR|AF|ARLO|BERR|TxE|RxNE|Reserved|STOPF|ADD10|BTF|ADDR|SB|
|0x14|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x18|**I2C_SR2**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|DUALF|SMBHOST|SMBDEFAUL|GENCALL|Reserved|TRA|BUSY|MSL|
|0x18|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x1C|**I2C_CCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|F/S|DUTY|Reserved|Reserved|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|CCR[11:0]|
|0x1C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x20|**I2C_TRISE**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|TRISE[5:0]|TRISE[5:0]|TRISE[5:0]|TRISE[5:0]|TRISE[5:0]|TRISE[5:0]|
|0x20|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|1|0|
|0x24|**I2C_FLTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|ANOFF|DNF[3:0]|DNF[3:0]|DNF[3:0]|DNF[3:0]|
|0x24|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|


Refer to _Section 2.3: Memory map_ for the register boundary addresses table.


RM0090 Rev 21 875/1757



875


