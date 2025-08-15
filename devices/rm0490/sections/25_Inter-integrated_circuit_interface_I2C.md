**RM0490** **Inter-integrated circuit interface (I2C)**

# **25 Inter-integrated circuit interface (I2C)**

## **25.1 Introduction**


The I2C peripheral handles the interface between the device and the serial I²C (interintegrated circuit) bus. It provides multicontroller capability, and controls all I²C-bus-specific
sequencing, protocol, arbitration and timing. It supports Standard-mode (Sm), Fast-mode
(Fm) and Fast-mode Plus (Fm+).


The I2C peripheral is also SMBus (system management bus) and PMBus [®] (power
management bus) compatible.


It can use DMA to reduce the CPU load.

# **25.2 I2C main features**


      - I²C-bus specification rev03 compatibility:


–
Target and controller modes


–
Multicontroller capability


–
Standard-mode (up to 100 kHz)


–
Fast-mode (up to 400 kHz)


–
Fast-mode Plus (up to 1 MHz)


–
7-bit and 10-bit addressing mode


–
Multiple 7-bit target addresses (2 addresses, 1 with configurable mask)


–
All 7-bit-addresses acknowledge mode


– General call


–
Programmable setup and hold times


–
Easy-to-use event management


–
Clock stretching (optional)


      - 1-byte buffer with DMA capability


      - Programmable analog and digital noise filters

      - SMBus specification rev 3.0 compatibility [(a)] :


–
Hardware PEC (packet error checking) generation and verification with ACK
control


–
Command and data acknowledge control


–
Address resolution protocol (ARP) support


–
Host and device support


– SMBus alert


– Timeouts and idle condition detection


      - PMBus rev 1.3 standard compatibility


      - Independent clock


a. To check the compliance of the GPIOs selected for SMBus with the specified logical levels, refer to the
product datasheet.


RM0490 Rev 5 677/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


      - Wake-up from Stop mode on address match


For information on I2C instantiation, refer to _Section 25.3: I2C implementation_ .

# **25.3 I2C implementation**


This section provides an implementation overview with respect to the I2C instantiation.


**Table 105. I2C implementation**







|I2C features(1)|I2C1|I2C2(2)|
|---|---|---|
|7-bit addressing mode|X|X|
|10-bit addressing mode|X|X|
|Standard-mode (up to 100 kbit/s)|X|X|
|Fast-mode (up to 400 kbit/s)|X|X|
|Fast-mode Plus with 20 mA output drive I/Os (up to 1 Mbit/s)|X|X|
|Independent clock|X|-|
|Wake-up from Stop mode|X|-|
|SMBus/PMBus|X|-|


1. X = supported.


2. I2C2 is only available on STM32C051xx/071xx/091xx/092xx devices.

# **25.4 I2C functional description**


In addition to receiving and transmitting data, the peripheral converts them from serial to
parallel format and vice versa. The interrupts are enabled or disabled by software. The
peripheral is connected to the I²C-bus through a data pin (SDA) and a clock pin (SCL). It
supports Standard-mode (up to 100 kHz), Fast-mode (up to 400 kHz), and Fast-mode Plus
(up to 1 MHz) I²C-bus.


The peripheral can also be connected to an SMBus, through the data pin (SDA), the clock
pin (SCL), and an optional SMBus alert pin (SMBA). Refer to _Section 25.3: I2C_
_implementation_ for the relevant I2C instances.


The independent clock function allows the I2C communication speed to be independent of
the PCLK frequency.


For I2C I/Os supporting 20 mA output current drive for Fast-mode Plus operation, the driving
capability is enabled through control bits in the system configuration block(SYSCFG) _._


678/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**25.4.1** **I2C block diagram**


**Figure 222. Block diagram**





















The block diagram shows a functional superset. Refer to _Section 25.3: I2C implementation_
for information relative to different instances of the I2C peripheral. The instances not
supporting features such as SMBus and wake-up from Stop mode do not include the
corresponding blocks. The instances not supporting the independent clock function use
PCLK for clocking both the kernel and the registers.


RM0490 Rev 5 679/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**25.4.2** **I2C pins and internal signals**


**Table 106. I2C input/output pins**

|Pin name|Signal type|Description|
|---|---|---|
|I2C_SDA|Bidirectional|I²C-bus data|
|I2C_SCL|Bidirectional|I²C-bus clock|
|I2C_SMBA|Bidirectional|SMBus alert|



**Table 107. I2C internal input/output signals**

|Internal signal name|Signal type|Description|
|---|---|---|
|i2c_ker_ck|Input|I2C kernel clock, also named I2CCLK in this document|
|i2c_pclk|Input|I2C APB clock|
|i2c_it|Output|I2C interrupts, refer to_Table 121_ for the list of interrupt sources|
|i2c_rx_dma|Output|I2C receive data DMA request (I2C_RX)|
|i2c_tx_dma|Output|I2C transmit data DMA request (I2C_TX)|



**25.4.3** **I2C clock requirements**


The I2C kernel is clocked by I2CCLK.


The I2CCLK period t I2CCLK must respect the following conditions:


_t_ _I2CCLK_ < ( _t_ _LOW_               - _t_ _filters_ ) / 4


_t_ _I2CCLK_ < _t_ _HIGH_


where _t_ _LOW_ is the SCL low time, _t_ _HIGH_ is the SCL high time, and _t_ _filters_ is the sum of the
analog and digital filter delays (when enabled).


The digital filter delay is DNF[3:0] x _t_ _I2CCLK_ .


The PCLK clock period _t_ _PCLK_ must respect the condition _t_ _PCLK_ < 4/3 _t_ _SCL_, where _t_ _SCL_ is the
SCL period.


**Caution:** When the I2C kernel is clocked by PCLK, this clock must respect the conditions for _t_ _I2CCLK_ .


**25.4.4** **I2C mode selection**


The peripheral can operate as:


      - Target transmitter


      - Target receiver


      - Controller transmitter


      - Controller receiver


By default, the peripheral operates in target mode. It automatically switches from target to
controller mode upon generating START condition, and from controller to target mode upon
arbitration loss or upon generating STOP condition. This allows the use of the I2C
peripheral in a multicontroller I²C-bus environment.


680/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Communication flow**


In controller mode, the I2C peripheral initiates a data transfer and generates the clock
signal. Serial data transfers always begin with a START condition and end with a STOP
condition. Both START and STOP conditions are generated in controller mode by software.


In target mode, the peripheral recognizes its own 7-bit or 10-bit address, and the general
call address. The general call address detection can be enabled or disabled by software.
The reserved SMBus addresses can also be enabled by software.


Data and addresses are transferred as 8-bit bytes, MSB first. The address is contained in
the first byte (7-bit addressing) or in the first two bytes (10-bit addressing) following the
START condition. The address is always transmitted in controller mode.


The following figure shows the transmission of a single byte. The controller generates nine
SCL pulses. The transmitter sends the eight data bits to the receiver with the SCL pulses 1
to 8. Then the receiver sends the acknowledge bit to the transmitter with the ninth SCL
pulse.


**Figure 223. I²C-bus protocol**









The acknowledge can be enabled or disabled by software. The own addresses of the I2C
peripheral can be selected by software.


**25.4.5** **I2C initialization**


**Enabling and disabling the peripheral**


Before enabling the I2C peripheral, configure and enable its clock through the RCC, and
initialize its control registers.


The I2C peripheral can then be enabled by setting the PE bit of the I2C_CR1 register.


Disabling the I2C peripheral by clearing the PE bit resets the I2C peripheral. Refer to
_Section 25.4.6_ for more details.


**Noise filters**


Before enabling the I2C peripheral by setting the PE bit of the I2C_CR1 register, the user
must configure the analog and/or digital noise filters, as required.


RM0490 Rev 5 681/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


The analog noise filter on the SDA and SCL inputs complies with the I²C-bus specification
which requires, in Fast-mode and Fast-mode Plus, the suppression of spikes shorter than
50 ns. Enabled by default, it can be disabled by setting the ANFOFF bit.


The digital filter is controlled through the DNF[3:0] bitfield of the I2C_CR1 register. When it is
enabled, the internal SCL and SDA signals only take the level of their corresponding I²C-bus
line when remaining stable for more than DNF[3:0] periods of I2CCLK. This allows
suppressing spikes shorter than the filtering capacity period programmable from one to
fifteen I2CCLK periods.


The following table compares the two filters.


**Table 108. Comparison of analog and digital filters**














|Item|Analog filter|Digital filter|
|---|---|---|
|Filtering capacity(1)|≥ 50 ns|One to fifteen I2CCLK periods|
|Benefits|Available in Stop mode|– Programmable filtering capacity<br>– Extra filtering capability versus I²C-bus<br>specification requirements<br>– Stable filtering capacity|
|Drawbacks|Filtering capacity<br>variation with<br>temperature, voltage, and<br>silicon process|Wake-up from Stop mode on address match not<br>supported when the digital filter is enabled|



1. Maximum duration of spikes that the filter can suppress


**Caution:** The filter configuration cannot be changed when the I2C peripheral is enabled.


**I2C timings**


To ensure correct data hold and setup times, the corresponding timings must be configured
through the PRESC[3:0], SCLDEL[3:0], and SDADEL[3:0] bitfields of the I2C_TIMINGR
register.


The STM32CubeMX tool calculates and provides the I2C_TIMINGR content in the _I2C_
_configuration_ window.


682/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Figure 224. Setup and hold timings**













When the SCL falling edge is internally detected, the delay t SDADEL (impacting the hold time
t HD;DAT ) is inserted before sending SDA output:


t SDADEL = SDADEL x t PRESC + t I2CCLK, where t PRESC = (PRESC + 1) x t I2CCLK .


The total SDA output delay is:


t SYNC1 + {[SDADEL x (PRESC + 1) + 1] x t I2CCLK }


The t SYNC1 duration depends upon:


- SCL falling slope


- input delay t AF(min) < t AF < t AF(max) introduced by the analog filter (if enabled)

- input delay t DNF = DNF x t I2CCLK introduced by the digital filter (if enabled)


- delay due to SCL synchronization to I2CCLK clock (two to three I2CCLK periods)


To bridge the undefined region of the SCL falling edge, the user must set SDADEL[3:0] so
as to fulfill the following condition:


{t f(max) + t HD;DAT(min) - t AF(min) - [(DNF + 3) x t I2CCLK ]} / {(PRESC + 1) x t I2CCLK } ≤SDADEL


SDADEL ≤ {t HD;DAT (max) - t AF(max) - [(DNF + 4) x t I2CCLK ]} / {(PRESC + 1) x t I2CCLK }


RM0490 Rev 5 683/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


_Note:_ _t_ _AF(min)_ _and t_ _AF(max)_ _are only part of the condition when the analog filter is enabled. Refer to_
_the device datasheet for t_ _AF_ _values._


The t HD;DAT time can at maximum be 3.45 µs for Standard-mode, 0.9 µs for Fast-mode, and
0.45 µs for Fast-mode Plus. It must be lower than the maximum of t VD;DAT by a transition
time. This maximum must only be met if the device does not stretch the LOW period (t LOW )
of the SCL signal. When it stretches SCL, the data must be valid by the set-up time before it
releases the clock.


The SDA rising edge is usually the worst case. The previous condition then becomes:


SDADEL ≤ {t VD;DAT (max)       - t r (max)       - t AF (max)       - [(DNF + 4) x t I2CCLK ]} / {(PRESC + 1) x t I2CCLK }


_Note:_ _This condition can be violated when NOSTRETCH = 0, because the device stretches SCL_
_low to guarantee the set-up time, according to the SCLDEL[3:0] value._


After t SDADEL, or after sending SDA output when the target had to stretch the clock because
the data was not yet written in I2C_TXDR register, the SCL line is kept at low level during
the setup time. This setup time is t SCLDEL = (SCLDEL + 1) x t PRESC, where
t PRESC = (PRESC + 1) x t I2CCLK . t SCLDEL impacts the setup time t SU;DAT .


To bridge the undefined region of the SDA transition (rising edge usually worst case), the
user must program SCLDEL[3:0] so as to fulfill the following condition:


{[t r (max) + t SU;DAT (min) ] / [(PRESC + 1) x t I2CCLK ]} - 1 ≤ SCLDEL


Refer to the following table for t f, t r, t HD;DAT, t VD;DAT, and t SU;DAT standard values.


Use the SDA and SCL real transition time values measured in the application to widen the
scope of allowed SDADEL[3:0] and SCLDEL[3:0] values. Use the maximum SDA and SCL
transition time values defined in the standard to make the device work reliably regardless of
the application.


_Note:_ _At every clock pulse, after SCL falling edge detection, I2C operating as controller or target_
_stretches SCL low during at least_ _[(SDADEL + SCLDEL + 1) x (PRESC + 1) + 1] x t_ _I2CCLK_ _, in both_
_transmission and reception modes. In transmission mode, if the data is not yet written in_
_I2C_TXDR when SDA delay elapses, the I2C peripheral keeps stretching SCL low until the_
_next data is written. Then new data MSB is sent on SDA output, and SCLDEL counter starts,_
_continuing stretching SCL low to guarantee the data setup time._


When the NOSTRETCH bit is set in target mode, the SCL is not stretched. The
SDADEL[3:0] must then be programmed so that it ensures a sufficient setup time.


**Table 109. I²C-bus and SMBus specification data setup and hold times**







|Symbol|Parameter|Standard-mode<br>(Sm)|Col4|Fast-mode<br>(Fm)|Col6|Fast-mode Plus<br>(Fm+)|Col8|SMBus|Col10|Unit|
|---|---|---|---|---|---|---|---|---|---|---|
|**Symbol**|**Parameter**|**Min**|**Max**|**Min**|**Max**|**Min**|**Max**|**Min**|**Max**|**Max**|
|tHD;DAT|Data hold time|0|-|0|-|0|-|0.3|-|µs|
|tVD;DAT|Data valid time|-|3.45|-|0.9|-|0.45|-|-|-|
|tSU;DAT|Data setup time|250|-|100|-|50|-|250|-|ns|
|tr|Rise time of both<br>SDA and SCL signals|-|1000|-|300|-|120|-|1000|1000|
|tf|Fall time of both<br>SDA and SCL signals|-|300|-|300|-|120|-|300|300|


684/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


Additionally, in controller mode, the SCL clock high and low levels must be configured by
programming the PRESC[3:0], SCLH[7:0], and SCLL[7:0] bitfields of the I2C_TIMINGR
register.


When the SCL falling edge is internally detected, the I2C peripheral releasing the SCL
output after the delay t SCLL = (SCLL + 1) x t PRESC, where t PRESC = (PRESC + 1) x t I2CCLK . The
t SCLL delay impacts the SCL low time t LOW .


When the SCL rising edge is internally detected, the I2C peripheral forces the SCL output to
low level after the delay t SCLH = (SCLH + 1) x t PRESC, where t PRESC = (PRESC + 1) x t I2CCLK . The
t SCLH impacts the SCL high time t HIGH .


Refer to _I2C controller initialization_ for more details.


**Caution:** Changing the timing configuration and the NOSTRETCH configuration is not allowed when
the I2C peripheral is enabled. Like the timing settings, the target NOSTRETCH settings
must also be done before enabling the peripheral. Refer to _I2C target initialization_ for more
details.


**Figure 225. I2C initialization flow**

















**25.4.6** **I2C reset**


The reset of the I2C peripheral is performed by clearing the PE bit of the I2C_CR1 register.
It has the effect of releasing the SCL and SDA lines. Internal state machines are reset and
the communication control bits and the status bits revert to their reset values. This reset
does not impact the configuration registers.


The impacted register bits are:


1. I2C_CR2 register: START, STOP, PECBYTE, and NACK


2. I2C_ISR register: BUSY, TXE, TXIS, RXNE, ADDR, NACKF, TCR, TC, STOPF, BERR,
ARLO, PECERR, TIMEOUT, ALERT, and OVR


RM0490 Rev 5 685/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


_Note:_ _The PECBYTE, PECERR, TIMOUT, and ALERT bits only apply to I2C instances supporting_
_SMBus._


PE must be kept low during at least three APB clock cycles to perform the I2C reset. To
ensure this, perform the following software sequence:


1. Write PE = 0


2. Check PE = 0


3. Write PE = 1


**25.4.7** **I2C data transfer**


The data transfer is managed through transmit and receive data registers and a shift
register.


**Reception**


The SDA input fills the shift register. After the eighth SCL pulse (when the complete data
byte is received), the shift register is copied into the I2C_RXDR register if it is empty
(RXNE = 0). If RXNE = 1, which means that the previous received data byte has not yet
been read, the SCL line is stretched low until I2C_RXDR is read. The stretch occurs
between the eighth and the ninth SCL pulse (before the acknowledge pulse).


**Figure 226. Data reception**























686/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Transmission**


If the I2C_TXDR register is not empty (TXE = 0), its content is copied into the shift register
after the ninth SCL pulse (the acknowledge pulse). Then the shift register content is shifted
out on the SDA line. If TXE = 1, which means that no data is written yet in I2C_TXDR, the
SCL line is stretched low until I2C_TXDR is written. The stretch starts after the ninth SCL
pulse.


**Figure 227. Data transmission**














|Col1|Col2|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
|xx|xx|data|xx|data2|xx|







**Hardware transfer management**


The I2C features an embedded byte counter to manage byte transfer and to close the
communication in various modes, such as:


–
NACK, STOP and ReSTART generation in controller mode


–
ACK control in target receiver mode


–
PEC generation/checking, on I2C instances supporting SMBus


In controller mode, the byte counter is always used. By default, it is disabled in target mode.
It can be enabled by software, by setting the SBC (target byte control) bit of the I2C_CR1
register.


The number of bytes to transfer is programmed in the NBYTES[7:0] bitfield of the I2C_CR2
register. If this number is greater than 255, or if a receiver wants to control the acknowledge
value of a received data byte, the reload mode must be selected, by setting the RELOAD bit
of the I2C_CR2 register. In this mode, the TCR flag is set when the number of bytes
programmed in NBYTES[7:0] is transferred (when the associated counter reaches zero),
and an interrupt is generated if TCIE is set. SCL is stretched as long as the TCR flag is set.
TCR is cleared by software when NBYTES[7:0] is written to a non-zero value.


When NBYTES[7:0] is reloaded with the last number of bytes to transfer, the RELOAD bit
must be cleared.


RM0490 Rev 5 687/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


When RELOAD = 0 in controller mode, the counter can be used in two modes:


      - **Automatic end** (AUTOEND = 1 in the I2C_CR2 register). In this mode, the controller
automatically sends a STOP condition once the number of bytes programmed in the
NBYTES[7:0] bitfield is transferred.


      - **Software end** (AUTOEND = 0 in the I2C_CR2 register). In this mode, a software action
is expected once the number of bytes programmed in the NBYTES[7:0] bitfield is
transferred; the TC flag is set and an interrupt is generated if the TCIE bit is set. The
SCL signal is stretched as long as the TC flag is set. The TC flag is cleared by software
when the START or STOP bit of the I2C_CR2 register is set. This mode must be used
when the controller wants to send a RESTART condition.


**Caution:** The AUTOEND bit has no effect when the RELOAD bit is set.


**Table 110. I2C configuration**

|Function|SBC bit|RELOAD bit|AUTOEND bit|
|---|---|---|---|
|Controller Tx/Rx NBYTES + STOP|X|0|1|
|Controller Tx/Rx + NBYTES + RESTART|X|0|0|
|Target Tx/Rx, all received bytes ACKed|0|X|X|
|Target Rx with ACK control|1|1|X|



**25.4.8** **I2C target mode**


**I2C target initialization**


To work in target mode, the user must enable at least one target address. The I2C_OAR1
and I2C_OAR2 registers are available to program the target own addresses OA1 and OA2,
respectively.


OA1 can be configured either in 7-bit (default) or in 10-bit addressing mode, by setting the
OA1MODE bit of the I2C_OAR1 register.


OA1 is enabled by setting the OA1EN bit of the I2C_OAR1 register.


If an additional target addresses are required, the second target address OA2 can be
configured. Up to seven OA2 LSBs can be masked, by configuring the OA2MSK[2:0] bitfield
of the I2C_OAR2 register. Therefore, for OA2MSK[2:0] configured from 1 to 6, only
OA2[7:2], OA2[7:3], OA2[7:4], OA2[7:5], OA2[7:6], or OA2[7] are compared with the
received address. When OA2MSK[2:0] is other than 0, the address comparator for OA2
excludes the I2C reserved addresses (0000 XXX and 1111 XXX) and they are not
acknowledged. If OA2MSK[2:0] = 7, all received 7-bit addresses are acknowledged (except
reserved addresses). OA2 is always a 7-bit address.


When enabled through the specific bit, the reserved addresses can be acknowledged if they
are programmed in the I2C_OAR1 or I2C_OAR2 register with OA2MSK[2:0] = 0.


OA2 is enabled by setting the OA2EN bit of the I2C_OAR2 register.


The general call address is enabled by setting the GCEN bit of the I2C_CR1 register.


When the I2C peripheral is selected by one of its enabled addresses, the ADDR interrupt
status flag is set, and an interrupt is generated if the ADDRIE bit is set.


By default, the target uses its clock stretching capability, which means that it stretches the
SCL signal at low level when required, to perform software actions. If the controller does not


688/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


support clock stretching, I2C must be configured with NOSTRETCH = 1 in the I2C_CR1
register.


After receiving an ADDR interrupt, if several addresses are enabled, the user must read the
ADDCODE[6:0] bitfield of the I2C_ISR register to check which address matched. The DIR
flag must also be checked to know the transfer direction.


**Target with clock stretching**


As long as the NOSTRETCH bit of the I2C_CR1 register is zero (default), the I2C peripheral
operating as an I²C-bus target stretches the SCL signal in the following situations:


      - The ADDR flag is set and the received address matches with one of the enabled target
addresses.
The stretch is released when the software clears the ADDR flag by setting the
ADDRCF bit.


      - In transmission, the previous data transmission is completed and no new data is written
in I2C_TXDR register, or the first data byte is not written when the ADDR flag is cleared
(TXE = 1).
The stretch is released when the data is written to the I2C_TXDR register.


      - In reception, the I2C_RXDR register is not read yet and a new data reception is
completed.
The stretch is released when I2C_RXDR is read.


      - In target byte control mode (SBC bit set) with reload (RELOAD bit set), the last data
byte transfer is finished (TCR bit set).
The stretch is released when then TCR is cleared by writing a non-zero value in the
NBYTES[7:0] bitfield.


      - After SCL falling edge detection.
The stretch is released after [(SDADEL + SCLDEL + 1) x (PRESC+ 1) + 1] x t I2CCLK
period.


**Target without clock stretching**


As long as the NOSTRETCH bit of the I2C_CR1 register is set, the I2C peripheral operating
as an I²C-bus target does not stretch the SCL signal.


The SCL clock is not stretched while the ADDR flag is set.


In transmission, the data must be written in the I2C_TXDR register before the first SCL
pulse corresponding to its transfer occurs. If not, an underrun occurs, the OVR flag is set in
the I2C_ISR register and an interrupt is generated if the ERRIE bit of the I2C_CR1 register
is set. The OVR flag is also set when the first data transmission starts and the STOPF bit is
still set (has not been cleared). Therefore, if the user clears the STOPF flag of the previous
transfer only after writing the first data to be transmitted in the next transfer, it ensures that
the OVR status is provided, even for the first data to be transmitted.


In reception, the data must be read from the I2C_RXDR register before the ninth SCL pulse
(ACK pulse) of the next data byte occurs. If not, an overrun occurs, the OVR flag is set in the
I2C_ISR register, and an interrupt is generated if the ERRIE bit of the I2C_CR1 register is
set.


RM0490 Rev 5 689/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**Target byte control mode**


To allow byte ACK control in target reception mode, the target byte control mode must be
enabled, by setting the SBC bit of the I2C_CR1 register. This is required to comply with
SMBus standards.


The reload mode must be selected to allow byte ACK control in target reception mode
(RELOAD = 1). To get control of each byte, NBYTES[7:0] must be initialized to 0x1 in the
ADDR interrupt subroutine, and reloaded to 0x1 after each received byte. When the byte is
received, the TCR bit is set, stretching the SCL signal low between the eighth and the ninth
SCL pulse. The user can read the data from the I2C_RXDR register, and then decide to
acknowledge it or not by configuring the ACK bit of the I2C_CR2 register. The SCL stretch is
released by programming NBYTES to a non-zero value: the acknowledge or
not-acknowledge is sent and the next byte can be received.


NBYTES[7:0] can be loaded with a value greater than 0x1. Receiving then continues until
the corresponding number of bytes are received.


_Note:_ _The SBC bit must be configured when the I2C peripheral is disabled, when the target is not_
_addressed, or when ADDR = 1._


_The RELOAD bit value can be changed when ADDR = 1, or when TCR = 1._


**Caution:** The target byte control mode is not compatible with NOSTRETCH mode. Setting SBC when
NOSTRETCH = 1 is not allowed.


**Figure 228. Target initialization flow**



1. SBC must be set to support SMBus features.


690/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Target transmitter**


A transmit interrupt status (TXIS) flag is generated when the I2C_TXDR register becomes
empty. An interrupt is generated if the TXIE bit of the I2C_CR1 register is set.


The TXIS flag is cleared when the I2C_TXDR register is written with the next data byte to
transmit.


When NACK is received, the NACKF flag is set in the I2C_ISR register and an interrupt is
generated if the NACKIE bit of the I2C_CR1 register is set. The target automatically
releases the SCL and SDA lines to let the controller perform a STOP or a RESTART
condition. The TXIS bit is not set when a NACK is received.


When STOP is received and the STOPIE bit of the I2C_CR1 register is set, the STOPF flag
of the I2C_ISR register is set and an interrupt is generated. In most applications, the SBC bit
is usually programmed to 0. In this case, if TXE = 0 when the target address is received
(ADDR = 1), the user can choose either to send the content of the I2C_TXDR register as the
first data byte, or to flush the I2C_TXDR register, by setting the TXE bit in order to program
a new data byte.


In target byte control mode (SBC = 1), the number of bytes to transmit must be programmed
in NBYTES[7:0] in the address match interrupt subroutine (ADDR = 1). In this case, the
number of TXIS events during the transfer corresponds to the value programmed in
NBYTES[7:0].


**Caution:** When NOSTRETCH = 1, the SCL clock is not stretched while the ADDR flag is set, so the
user cannot flush the I2C_TXDR register content in the ADDR subroutine to program the
first data byte. The first data byte to send must be previously programmed in the I2C_TXDR
register:


      - This data can be the one written in the last TXIS event of the previous transmission

message.


      - If this data byte is not the one to send, the I2C_TXDR register can be flushed, by
setting the TXE bit, to program a new data byte. The STOPF bit must be cleared only
after these actions. This guarantees that they are executed before the first data
transmission starts, following the address acknowledge.


If STOPF is still set when the first data transmission starts, an underrun error is
generated (the OVR flag is set).


If a TXIS event (transmit interrupt or transmit DMA request) is required, the user must
set the TXIS bit in addition to the TXE bit, to generate the event.


RM0490 Rev 5 691/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**Figure 229. Transfer sequence flow for I2C target transmitter, NOSTRETCH = 0**













692/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Figure 230. Transfer sequence flow for I2C target transmitter, NOSTRETCH = 1**











RM0490 Rev 5 693/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**Figure 231. Transfer bus diagrams for I2C target transmitter (mandatory events only)**









































694/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Target receiver**


The RXNE bit of the I2C_ISR register is set when the I2C_RXDR is full, which generates an
interrupt if the RXIE bit of the I2C_CR1 register is set. RXNE is cleared when I2C_RXDR is
read.


When STOP condition is received and the STOPIE bit of the I2C_CR1 register is set, the
STOPF flag in the I2C_ISR register is set and an interrupt is generated.


**Figure 232. Transfer sequence flow for I2C target receiver, NOSTRETCH = 0**









RM0490 Rev 5 695/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**











**Figure 234. Transfer bus diagrams for I2C target receiver**
**(mandatory events only)**

























696/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**25.4.9** **I2C controller mode**


**I2C controller initialization**


Before enabling the peripheral, the I2C controller clock must be configured, by setting the
SCLH and SCLL bits in the I2C_TIMINGR register.


The STM32CubeMX tool calculates and provides the I2C_TIMINGR content in the _I2C_
_Configuration_ window.


A clock synchronization mechanism is implemented in order to support multicontroller
environment and target clock stretching.


In order to allow clock synchronization:


      - The low level of the clock is counted using the SCLL counter, starting from the SCL low
level internal detection.


      - The high level of the clock is counted using the SCLH counter, starting from the SCL
high level internal detection.


I2C detects its own SCL low level after a t SYNC1 delay depending on the SCL falling edge,
SCL input noise filters (analog and digital), and SCL synchronization to the I2CxCLK clock.
I2C releases SCL to high level once the SCLL counter reaches the value programmed in the
SCLL[7:0] bitfield of the I2C_TIMINGR register.


I2C detects its own SCL high level after a t SYNC2 delay depending on the SCL rising edge,
SCL input noise filters (analog and digital), and SCL synchronization to the I2CxCLK clock.
I2C ties SCL to low level once the SCLH counter reaches the value programmed in the
SCLH[7:0] bitfield of the I2C_TIMINGR register.


Consequently the controller clock period is:


t SCL = t SYNC1 + t SYNC2 + {[(SCLH+ 1) + (SCLL+ 1)] x (PRESC+ 1) x t I2CCLK }


The duration of t SYNC1 depends upon:


      - SCL falling slope


      - input delay induced by the analog filter (when enabled)


      - input delay induced by the digital filter (when enabled): DNF[3:0] x t I2CCLK

      - delay due to SCL synchronization with the I2CCLK clock (two to three I2CCLK periods)


The duration of t SYNC2 depends upon:


      - SCL rising slope


      - input delay induced by the analog filter (when enabled)


      - input delay induced by the digital filter (when enabled): DNF[3:0] x t I2CCLK

      - delay due to SCL synchronization with the I2CCLK clock (two to three I2CCLK periods)


RM0490 Rev 5 697/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**





























698/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Caution:** For compliance with the I²C-bus or SMBus specification, the controller clock must respect
the timings in the following table.


**Table 111. I²C-bus and SMBus specification clock timings**







|Symbol|Parameter|Standard-<br>mode (Sm)|Col4|Fast-mode<br>(Fm)|Col6|Fast-mode<br>Plus (Fm+)|Col8|SMBus|Col10|Unit|
|---|---|---|---|---|---|---|---|---|---|---|
|**Symbol**|**Parameter**|**Min**|**Max**|**Min**|**Max**|**Min**|**Max**|**Min**|**Max**|**Max**|
|fSCL|SCL clock frequency|-|100|-|400|-|1000|-|100|kHz|
|tHD:STA|Hold time (repeated) START condition|4.0|-|0.6|-|0.26|-|4.0|-|µs|
|tSU:STA|Set-up time for a repeated START<br>condition|4.7|-|0.6|-|0.26|-|4.7|-|-|
|tSU:STO|Set-up time for STOP condition|4.0|-|0.6|-|0.26|-|4.0|-|-|
|tBUF|Bus free time between a STOP and<br>START condition|4.7|-|1.3|-|0.5|-|4.7|-|-|
|tLOW|Low period of the SCL clock|4.7|-|1.3|-|0.5|-|4.7|-|-|
|tHIGH|High period of the SCL clock|4.0|-|0.6|-|0.26|-|4.0|50|50|
|tr|Rise time of both SDA and SCL signals|-|1000|-|300|-|120|-|1000|ns|
|tf|Fall time of both SDA and SCL signals|-|300|-|300|-|120|-|300|300|


_Note:_ _The SCLL[7:0] bitfield also determines the_ _t_ _BUF_ _and_ _t_ _SU:STA_ _timings and SCLH[7:0] the_
_t_ _HD:STA_ _and_ _t_ _SU:STO_ _timings_ _._


Refer to _Section 25.4.10_ for examples of I2C_TIMINGR settings versus the I2CCLK
frequency.


**Controller communication initialization (address phase)**


To initiate the communication with a target to address, set the following bitfields of the
I2C_CR2 register:


      - ADD10: addressing mode (7-bit or 10-bit)


      - SADD[9:0]: target address to send


      - RD_WRN: transfer direction


      - HEAD10R: in case of 10-bit address read, this bit determines whether the header only
(for direction change) or the complete address sequence is sent.


      - NBYTES[7:0]: the number of bytes to transfer; if equal to or greater than 255 bytes, the
bitfield must initially be set to 0xFF.


_Note:_ _Changing these bitfields is not allowed as long as the START bit is set._


Before launching the communication, make sure that the I²C-bus is idle. This can be
checked using the bus idle detection function or by verifying that the IDR bits of the GPIOs
selected as SDA and SCL are set. Any low-level incident on the I²C-bus lines that coincides
with the START condition asserted by the I2C peripheral may cause its deadlock if not
filtered out by the input filters. If such incidents cannot be prevented, design the software so
that it restores the normal operation of the I2C peripheral in case of a deadlock, by toggling
the PE bit of the I2C_CR1 register.


RM0490 Rev 5 699/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


To launch the communication, set the START bit of the I2C_CR2 register. The controller
then automatically sends a START condition followed by the target address, either
immediately if the BUSY flag is low, or t BUF time after the BUSY flag transits from high to low
state. The BUSY flag is set upon sending the START condition.


In case of an arbitration loss, the controller automatically switches back to target mode and
can acknowledge its own address if it is addressed as a target.


_Note:_ _The START bit is reset by hardware when the target address is sent on the bus, whatever_
_the received acknowledge value. The START bit is also reset by hardware upon arbitration_
_loss._


_In 10-bit addressing mode, the controller automatically keeps resending the target address_
_in a loop until the first address byte (first seven address bits) is acknowledged by the target._
_Setting the ADDRCF bit makes I2C quit that loop._
_If the I2C peripheral is addressed as a target (ADDR = 1) while the START bit is set, the I2C_
_peripheral switches to target mode and the START bit is cleared._


_Note:_ _The same procedure is applied for a repeated START condition. In this case, BUSY = 1._


**Figure 236. Controller initialization flow**





**Initialization of a controller receiver addressing a 10-bit address target**


If the target address is in 10-bit format, the user can choose to send the complete read
sequence, by clearing the HEAD10R bit of the I2C_CR2 register. In this case, the controller
automatically sends the following complete sequence after the START bit is set:


(RE)START + Target address 10-bit header Write + Target address second byte +
(RE)START + Target address 10-bit header Read.











700/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


If the controller addresses a 10-bit address target, transmits data to this target and then
reads data from the same target, a controller transmission flow must be done first. Then a
repeated START is set with the 10-bit target address configured with HEAD10R = 1. In this
case, the controller sends this sequence:


RESTART + Target address 10-bit header Read.


**Figure 238. 10-bit address read access with HEAD10R = 1**























**Controller transmitter**


In the case of a write transfer, the TXIS flag is set after each byte transmission, after the
ninth SCL pulse when an ACK is received.


A TXIS event generates an interrupt if the TXIE bit of the I2C_CR1 register is set. The flag is
cleared when the I2C_TXDR register is written with the next data byte to transmit.


The number of TXIS events during the transfer corresponds to the value programmed in
NBYTES[7:0]. If the total number of data bytes to transmit is greater than 255, the reload
mode must be selected by setting the RELOAD bit in the I2C_CR2 register. In this case,
when the NBYTES[7:0] number of data bytes is transferred, the TCR flag is set and the SCL
line is stretched low until NBYTES[7:0] is written with a non-zero value.


When RELOAD = 0 and the number of data bytes defined in NBYTES[7:0] is transferred:


- In automatic end mode (AUTOEND = 1), a STOP condition is automatically sent.


- In software end mode (AUTOEND = 0), the TC flag is set and the SCL line is stretched
low, to perform software actions:


–
A RESTART condition can be requested by setting the START bit of the I2C_CR2
register with the proper target address configuration and the number of bytes to
transfer. Setting the START bit clears the TC flag and sends the START condition
on the bus.


–
A STOP condition can be requested by setting the STOP bit of the I2C_CR2
register. This clears the TC flag and sends a STOP condition on the bus.


When a NACK is received, the TXIS flag is not set and a STOP condition is automatically
sent. The NACKF flag of the I2C_ISR register is set. An interrupt is generated if the NACKIE
bit is set.


RM0490 Rev 5 701/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**













702/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Figure 240. Transfer sequence flow for I2C controller transmitter, N > 255 bytes**



















RM0490 Rev 5 703/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**Figure 241. Transfer bus diagrams for I2C controller transmitter**
**(mandatory events only)**























704/1027 RM0490 Rev 5




**RM0490** **Inter-integrated circuit interface (I2C)**


**Controller receiver**


In the case of a read transfer, the RXNE flag is set after each byte reception, after the eighth
SCL pulse. An RXNE event generates an interrupt if the RXIE bit of the I2C_CR1 register is
set. The flag is cleared when I2C_RXDR is read.


If the total number of data bytes to receive is greater than 255, select the reload mode, by
setting the RELOAD bit of the I2C_CR2 register. In this case, when the NBYTES[7:0]
number of data bytes is transferred, the TCR flag is set and the SCL line is stretched low
until NBYTES[7:0] is written with a non-zero value.


When RELOAD = 0 and he number of data bytes defined in NBYTES[7:0] is transferred:


      - In automatic end mode (AUTOEND = 1), a NACK and a STOP are automatically sent
after the last received byte.


      - In software end mode (AUTOEND = 0), a NACK is automatically sent after the last
received byte. The TC flag is set and the SCL line is stretched low in order to allow
software actions:


–
A RESTART condition can be requested by setting the START bit of the I2C_CR2
register, with the proper target address configuration and the number of bytes to
transfer. Setting the START bit clears the TC flag and sends the START condition
and the target address on the bus.


–
A STOP condition can be requested by setting the STOP bit of the I2C_CR2
register. This clears the TC flag and sends a STOP condition on the bus.


RM0490 Rev 5 705/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**Figure 242. Transfer sequence flow for I2C controller receiver, N ≤ 255 bytes**











706/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Figure 243. Transfer sequence flow for I2C controller receiver, N > 255 bytes**













RM0490 Rev 5 707/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**Figure 244. Transfer bus diagrams for I2C controller receiver**
**(mandatory events only)**





























**25.4.10** **I2C_TIMINGR register configuration examples**





The following tables provide examples of how to program the I2C_TIMINGR register to
obtain timings compliant with the I²C-bus specification. To get more accurate configuration
values, use the STM32CubeMX tool ( _I2C Configuration_ window).


708/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**

|Col1|Table 112. Timing settings for|Col3|fI2CCLK of 8 MHz|Col5|
|---|---|---|---|---|
|**Parameter**|**Standard-mode (Sm)**|**Standard-mode (Sm)**|**Fast-mode (Fm)**|**Fast-mode Plus**<br>**(Fm+)**|
|**Parameter**|**10 kHz**|**100 kHz**|**400 kHz**|**500 kHz**|
|PRESC[3:0]|0x1|0x1|0x0|0x0|
|SCLL[7:0]|0xC7|0x13|0x9|0x6|
|tSCLL|200 x 250 ns = 50 µs|20 x 250 ns = 5.0 µs|10 x 125 ns = 1250 ns|7 x 125 ns = 875 ns|
|SCLH[7:0]|0xC3|0xF|0x3|0x3|
|tSCLH|196 x 250 ns = 49 µs|16 x 250 ns = 4.0 µs|4 x 125 ns = 500 ns|4 x 125 ns = 500 ns|
|tSCL(1)|~100 µs(2)|~10 µs(2)|~2.5 µs(3)|~2.0 µs(4)|
|SDADEL[3:0]|0x2|0x2|0x1|0x0|
|tSDADEL|2 x 250 ns = 500 ns|2 x 250 ns = 500 ns|1 x 125 ns = 125 ns|0 ns|
|SCLDEL[3:0]|0x4|0x4|0x3|0x1|
|tSCLDEL|5 x 250 ns = 1250 ns|5 x 250 ns = 1250 ns|4 x 125 ns = 500 ns|2 x 125 ns = 250 ns|



1. t SCL is greater than t SCLL + t SCLH due to SCL internal detection delay. Values provided for t SCL are examples only.


2. t SYNC1 + t SYNC2 minimum value is 4 x t I2CCLK = 500 ns. Example with t SYNC1 + t SYNC2 = 1000 ns.


3. t SYNC1 + t SYNC2 minimum value is 4 x t I2CCLK = 500 ns. Example with t SYNC1 + t SYNC2 = 750 ns.


4. t SYNC1 + t SYNC2 minimum value is 4 x t I2CCLK = 500 ns. Example with t SYNC1 + t SYNC2 = 655 ns.

|Col1|Table 113. Timing settings for|Col3|r fI2CCLK of 16 MHz|Col5|
|---|---|---|---|---|
|**Parameter**|**Standard-mode (Sm)**|**Standard-mode (Sm)**|**Fast-mode (Fm)**|**Fast-mode Plus (Fm+)**|
|**Parameter**|**10 kHz**|**100 kHz**|**400 kHz**|**1000 kHz**|
|PRESC[3:0]|0x3|0x3|0x1|0x0|
|SCLL[7:0]|0xC7|0x13|0x9|0x4|
|tSCLL|200 x 250 ns = 50 µs|20 x 250 ns = 5.0 µs|10 x 125 ns = 1250 ns|5 x 62.5 ns = 312.5 ns|
|SCLH[7:0]|0xC3|0xF|0x3|0x2|
|tSCLH|196 x 250 ns = 49 µs|16 x 250 ns = 4.0 µs|4 x 125 ns = 500 ns|3 x 62.5 ns = 187.5 ns|
|tSCL(1)|~100 µs(2)|~10 µs(2)|~2.5 µs(3)|~1.0 µs(4)|
|SDADEL[3:0]|0x2|0x2|0x2|0x0|
|tSDADEL|2 x 250 ns = 500 ns|2 x 250 ns = 500 ns|2 x 125 ns = 250 ns|0 ns|
|SCLDEL[3:0]|0x4|0x4|0x3|0x2|
|tSCLDEL|5 x 250 ns = 1250 ns|5 x 250 ns = 1250 ns|4 x 125 ns = 500 ns|3 x 62.5 ns = 187.5 ns|



1. t SCL is greater than t SCLL + t SCLH due to SCL internal detection delay. Values provided for t SCL are examples only.


2. t SYNC1 + t SYNC2 minimum value is 4 x t I2CCLK = 250 ns. Example with t SYNC1 + t SYNC2 = 1000 ns.


3. t SYNC1 + t SYNC2 minimum value is 4 x t I2CCLK = 250 ns. Example with t SYNC1 + t SYNC2 = 750 ns.


4. t SYNC1 + t SYNC2 minimum value is 4 x t I2CCLK = 250 ns. Example with t SYNC1 + t SYNC2 = 500 ns.


RM0490 Rev 5 709/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**

|Col1|Table 114. Timing settings for|Col3|fI2CCLK of 48 MHz|Col5|
|---|---|---|---|---|
|**Parameter**|**Standard-mode (Sm)**|**Standard-mode (Sm)**|**Fast-mode (Fm)**|**Fast-mode Plus (Fm+)**|
|**Parameter**|**10 kHz**|**100 kHz**|**400 kHz**|**1000 kHz**|
|PRESC[3:0]|0xB|0xB|0x5|0x5|
|SCLL[7:0]|0xC7|0x13|0x9|0x3|
|tSCLL|200 x 250 ns = 50 µs|20 x 250 ns = 5.0 µs|10 x 125 ns = 1250 ns|4 x 125 ns = 500 ns|
|SCLH[7:0]|0xC3|0xF|0x3|0x1|
|tSCLH|196 x 250 ns = 49 µs|16 x 250 ns = 4.0 µs|4 x 125 ns = 500 ns|2 x 125 ns = 250 ns|
|tSCL(1)|~100 µs(2)|~10 µs(2)|~2.5 µs(3)|~875 ns(4)|
|SDADEL[3:0]|0x2|0x2|0x3|0x0|
|tSDADEL|2 x 250 ns = 500 ns|2 x 250 ns = 500 ns|3 x 125 ns = 375 ns|0 ns|
|SCLDEL[3:0]|0x4|0x4|0x3|0x1|
|tSCLDEL|5 x 250 ns = 1250 ns|5 x 250 ns = 1250 ns|4 x 125 ns = 500 ns|2 x 125 ns = 250 ns|



1. t SCL is greater than t SCLL + t SCLH due to the SCL internal detection delay. Values provided for t SCL are only examples.


2. t SYNC1 + t SYNC2 minimum value is 4x t I2CCLK = 83.3 ns. Example with t SYNC1 + t SYNC2 = 1000 ns


3. t SYNC1 + t SYNC2 minimum value is 4x t I2CCLK = 83.3 ns. Example with t SYNC1 + t SYNC2 = 750 ns


4. t SYNC1 + t SYNC2 minimum value is 4x t I2CCLK = 83.3 ns. Example with t SYNC1 + t SYNC2 = 250 ns


**25.4.11** **SMBus specific features**


This section pertains to the instances of the I2C peripheral supporting SMBus. Refer to
_Section 25.3: I2C implementation_ .


**Introduction**


The system management bus (SMBus) is a two-wire interface through which various
devices can communicate with each other and with the rest of the system. It is based on
operation principles of the I²C-bus. The SMBus provides a control bus for system and power
management related tasks.


The I2C peripheral is compatible with the SMBus specification (http://smbus.org).


The system management bus specification refers to three types of devices:


      - **Target** is a device that receives or responds to a command.


      - **Controller** is a device that issues commands, generates clocks, and terminates the
transfer.


      - **Host** is a specialized controller that provides the main interface to the system CPU. A
host must be a controller-target and must support the SMBus _host notify_ protocol. Only
one host is allowed in a system.


The I2C peripheral can be configured as a controller or a target device, and also as a host.


**Bus protocols**


There are eleven possible command protocols for any given device. The device can use any
or all of them to communicate. These are: _Quick Command_, _Send Byte_, _Receive Byte_, _Write_


710/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


_Byte_, _Write Word_, _Read Byte_, _Read Word_, _Process Call_, _Block Read_, _Block Write_, and _Block_
_Write-Block Read Process Call_ . The protocols must be implemented by the user software.


For more details on these protocols, refer to the SMBus specification (http://smbus.org).


STM32CubeMX implements an SMBus stack thanks to X-CUBE-SMBUS, a downloadable
software pack that allows basic SMBus configuration per I2C instance supporting SMBus.


**Address resolution protocol (ARP)**


SMBus target address conflicts can be resolved by dynamically assigning a new unique
address to each target device. To provide a mechanism to isolate each device for the
purpose of address assignment, each device must implement a unique 128-bit device
identifier (UDID). In the I2C peripheral, it is implemented by software.


The I2C peripheral supports the Address resolution protocol (ARP). The SMBus device
default address (0b1100 001) is enabled by setting the SMBDEN bit of the I2C_CR1
register. The ARP commands must be implemented by the user software.


Arbitration is also performed in target mode for ARP support.


For more details on the SMBus address resolution protocol, refer to the SMBus specification
(http://smbus.org).


**Received command and data acknowledge control**


An SMBus receiver must be able to NACK each received command or data. In order to
allow the ACK control in target mode, the target byte control mode must be enabled, by
setting the SBC bit of the I2C_CR1 register. Refer to _Target byte control mode_ for more
details.


**Host notify protocol**


To enable the host notify protocol, set the SMBHEN bit of the I2C_CR1 register. The I2C
peripheral then acknowledges the SMBus host address (0b0001 000).


When this protocol is used, the device acts as a controller and the host as a target.


**SMBus alert**


The I2C peripheral supports the SMBALERT# optional signal through the SMBA pin. With
the SMBALERT# signal, an SMBus target device can signal to the SMBus host that it wants
to talk. The host processes the interrupt and simultaneously accesses all SMBALERT#
devices through the alert response address (0b0001 100). Only the device/devices which
pulled SMBALERT# low acknowledges/acknowledge the alert response address.


When the I2C peripheral is configured as an SMBus target device (SMBHEN = 0), the
SMBA pin is pulled low by setting the ALERTEN bit of the I2C_CR1 register. The alert
response address is enabled at the same time.


When the I2C peripheral is configured as an SMBus host (SMBHEN = 1), the ALERT flag of
the I2C_ISR register is set when a falling edge is detected on the SMBA pin and ALERTEN
= 1. An interrupt is generated if the ERRIE bit of the I2C_CR1 register is set. When
ALERTEN = 0, the alert line is considered high even if the external SMBA pin is low.


_Note:_ _If the SMBus alert pin is not required, keep the ALERTEN bit cleared. The SMBA pin can_
_then be used as a standard GPIO._


RM0490 Rev 5 711/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**Packet error checking**


A packet error checking mechanism introduced in the SMBus specification improves
reliability and communication robustness. The packet error checking is implemented by
appending a packet error code (PEC) at the end of each message transfer. The PEC is
calculated by using the C(x) = x [8] + x [2] + x + 1 CRC-8 polynomial on all the message bytes
(including addresses and read/write bits).


The I2C peripheral embeds a hardware PEC calculator and allows a not acknowledge to be
sent automatically when the received byte does not match the hardware calculated PEC.


**Timeouts**


To comply with the SMBus timeout specifications, the I2C peripheral embeds hardware
timers.


**Table 115. SMBus timeout specifications**






|Symbol|Parameter|Limits|Col4|Unit|
|---|---|---|---|---|
|**Symbol**|**Parameter**|**Min**|**Max**|**Max**|
|tTIMEOUT|Detect clock low timeout|25|35|ms|
|tLOW:SEXT<br>(1)|Cumulative clock low extend time (target device)|-|25|25|
|tLOW:MEXT<br>(2)|Cumulative clock low extend time (controller<br>device)|-|10|10|



1. t LOW:SEXT is the cumulative time a given target device is allowed to extend the clock cycles in one message
from the initial START to the STOP. It is possible that another target device or the controller also extends
the clock causing the combined clock low extend time to be greater than t LOW:SEXT . The value provided
applies to a single target device connected to a full-target controller.


2. t LOW:MEXT is the cumulative time a controller device is allowed to extend its clock cycles within each byte of
a message as defined from START-to-ACK, ACK-to-ACK, or ACK-to-STOP. It is possible that a target
device or another controller also extends the clock, causing the combined clock low time to be greater than
t LOW:MEXT on a given byte. The value provided applies to a single target device connected to a full-target
controller.


712/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Figure 245. Timeout intervals for t** **LOW:SEXT** **, t** **LOW:MEXT**



**Bus idle detection**





A controller can assume that the bus is free if it detects that the clock and data signals have
been high for t IDLE       - t HIGH (max) (refer to the table in _Section 25.4.9_ ).


This timing parameter covers the condition where a controller is dynamically added to the
bus, and may not have detected a state transition on the SMBCLK or SMBDAT lines. In this
case, the controller must wait long enough to ensure that a transfer is not currently in
progress. The I2C peripheral supports a hardware bus idle detection.


**25.4.12** **SMBus initialization**


This section pertains to the instances of the I2C peripheral supporting SMBus. Refer to
_Section 25.3: I2C implementation_ .


In addition to the I2C initialization for the I²C-bus, the use of the peripheral for the SMBus
communication requires some extra initialization steps.


**Received command and data acknowledge control (target mode)**


An SMBus receiver must be able to NACK each received command or data. To allow ACK
control in target mode, the target byte control mode must be enabled, by setting the SBC bit
of the I2C_CR1 register. Refer to _Target byte control mode_ for more details.


**Specific addresses (target mode)**


The specific SMBus addresses must be enabled if required. Refer to _Bus idle detection_ for
more details.


The SMBus device default address (0b1100 001) is enabled by setting the SMBDEN bit of
the I2C_CR1 register.


The SMBus host address (0b0001 000) is enabled by setting the SMBHEN bit of the
I2C_CR1 register.


RM0490 Rev 5 713/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


The alert response address (0b0001100) is enabled by setting the ALERTEN bit of the
I2C_CR1 register.


**Packet error checking**


PEC calculation is enabled by setting the PECEN bit of the I2C_CR1 register. Then the PEC
transfer is managed with the help of the hardware byte counter associated with the
NBYTES[7:0] bitfield of the I2C_CR2 register. The PECEN bit must be configured before
enabling the I2C.


The PEC transfer is managed with the hardware byte counter, so the SBC bit must be set
when interfacing the SMBus in target mode. The PEC is transferred after transferring
NBYTES[7:0] - 1 data bytes, if the PECBYTE bit is set and the RELOAD bit is cleared. If
RELOAD is set, PECBYTE has no effect.


**Caution:** Changing the PECEN configuration is not allowed when the I2C peripheral is enabled.


**Table 116. SMBus with PEC configuration**

|Mode|SBC bit|RELOAD bit|AUTOEND bit|PECBYTE bit|
|---|---|---|---|---|
|Controller Tx/Rx NBYTES + PEC+ STOP|X|0|1|1|
|Controller Tx/Rx NBYTES + PEC +<br>ReSTART|X|0|0|1|
|Target Tx/Rx with PEC|1|0|X|1|



**Timeout detection**


The timeout detection is enabled by setting the TIMOUTEN and TEXTEN bits of the
I2C_TIMEOUTR register. The timers must be programmed in such a way that they detect a
timeout before the maximum time given in the SMBus specification.


_**t**_ _**TIMEOUT**_ _**check**_


To check the t TIMEOUT parameter, load the 12-bit TIMEOUTA[11:0] bitfield with the timer
reload value. Keep the TIDLE bit at 0 to detect the SCL low level timeout.


Then set the TIMOUTEN bit of the I2C_TIMEOUTR register, to enable the timer.


If SCL is tied low for longer than the (TIMEOUTA + 1) x 2048 x t I2CCLK period, the TIMEOUT
flag of the I2C_ISR register is set.


Refer to _Table 117_ .


**Caution:** Changing the TIMEOUTA[11:0] bitfield and the TIDLE bit values is not allowed when the
TIMEOUTEN bit is set.


_**t**_ _**LOW:SEXT**_ _**and**_ _**t**_ _**LOW:MEXT**_ _**check**_


A 12-bit timer associated with the TIMEOUTB[11:0] bitfield allows checking t LOW:SEXT for the
I2C peripheral operating as a target, or t LOW:MEXT when it operates as a controller. As the
standard only specifies a maximum, the user can choose the same value for both. The timer
is then enabled by setting the TEXTEN bit in the I2C_TIMEOUTR register.


If the SMBus peripheral performs a cumulative SCL stretch for longer than the (TIMEOUTB
+ 1) x 2048 x t I2CCLK period, and within the timeout interval described in _Bus idle detection_
section, the TIMEOUT flag of the I2C_ISR register is set.


Refer to _Table 118_ .


714/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Caution:** Changing the TIMEOUTB[11:0] bitfield value is not allowed when the TEXTEN bit is set.


**Bus idle detection**


To check the t IDLE period, the TIMEOUTA[11:0] bitfield associated with 12-bit timer must be
loaded with the timer reload value. Keep the TIDLE bit at 1 to detect both SCL and SDA high
level timeout. Then set the TIMOUTEN bit of the I2C_TIMEOUTR register to enable the
timer.


If both the SCL and SDA lines remain high for longer than the
(TIMEOUTA + 1) x 4 x t I2CCLK period, the TIMEOUT flag of the I2C_ISR register is set.


Refer to _Table 119_ .


**Caution:** Changing the TIMEOUTA[11:0] bitfield and the TIDLE bit values is not allowed when the
TIMEOUTEN bit is set.


**25.4.13** **SMBus I2C_TIMEOUTR register configuration examples**


This section pertains to the instances of the I2C peripheral supporting SMBus. Refer to
_Section 25.3: I2C implementation_ .

The following tables provide examples of settings to reach desired t TIMEOUT, t LOW:SEXT,
t LOW:MEXT, and t IDLE timings at different f I2CCLK frequencies.


**Table 117. TIMEOUTA[11:0] for maximum t** **TIMEOUT** **of 25 ms**

|f<br>I2CCLK|TIMEOUTA[11:0]|TIDLE|TIMEOUTEN|t<br>TIMEOUT|
|---|---|---|---|---|
|8 MHz|0x61|0|1|98 x 2048 x 125 ns = 25 ms|
|16 MHz|0xC3|0|1|196 x 2048 x 62.5 ns = 25 ms|
|48 MHz|0x249|0|1|586 x 2048 x 20.08 ns = 25 ms|



**Table 118. TIMEOUTB[11:0] for maximum t** **LOW:SEXT** **and t** **LOW:MEXT** **of 8 ms**

|f<br>I2CCLK|TIMEOUTB[11:0]|TEXTEN|t<br>LOW:SEXT<br>t<br>LOW:MEXT|
|---|---|---|---|
|8 MHz|0x1F|1|32 x 2048 x 125 ns = 8 ms|
|16 MHz|0x3F|1|64 x 2048 x 62.5 ns = 8 ms|
|48 MHz|0xBB|1|188 x 2048 x 20.08 ns = 8 ms|



**Table 119. TIMEOUTA[11:0] for maximum t** **IDLE** **of 50 µs**

|f<br>I2CCLK|TIMEOUTA[11:0]|TIDLE|TIMEOUTEN|t<br>IDLE|
|---|---|---|---|---|
|8 MHz|0x63|1|1|100 x 4 x 125 ns = 50 µs|
|16 MHz|0xC7|1|1|200 x 4 x 62.5 ns = 50 µs|
|48 MHz|0x257|1|1|600 x 4 x 20.08 ns = 50 µs|



RM0490 Rev 5 715/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**25.4.14** **SMBus target mode**


This section pertains to the instances of the I2C peripheral supporting SMBus. Refer to
_Section 25.3: I2C implementation_ .


In addition to I2C target transfer management (refer to _Section 25.4.8: I2C target mode_ ), this
section provides extra software flowcharts to support SMBus.


**SMBus target transmitter**


When using the I2C peripheral in SMBus mode, set the SBC bit to enable the PEC
transmission at the end of the programmed number of data bytes. When the PECBYTE bit
is set, the number of bytes programmed in NBYTES[7:0] includes the PEC transmission. In
that case, the total number of TXIS interrupts is NBYTES[7:0] - 1, and the content of the
I2C_PECR register is automatically transmitted if the controller requests an extra byte after
the transfer of the NBYTES[7:0] - 1 data bytes.


**Caution:** The PECBYTE bit has no effect when the RELOAD bit is set.


**Figure 246. Transfer sequence flow for SMBus target transmitter N bytes + PEC**









716/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Figure 247. Transfer bus diagram for SMBus target transmitter (SBC = 1)**















**SMBus target receiver**





When using the I2C peripheral in SMBus mode, set the SBC bit to enable the PEC checking
at the end of the programmed number of data bytes. To allow the ACK control of each byte,
the reload mode must be selected (RELOAD = 1). Refer to _Target byte control mode_ for
more details.


To check the PEC byte, the RELOAD bit must be cleared and the PECBYTE bit must be set.
In this case, after the receipt of NBYTES[7:0] - 1 data bytes, the next received byte is
compared with the internal I2C_PECR register content. A NACK is automatically generated
if the comparison does not match, and an ACK is automatically generated if the comparison
matches, whatever the ACK bit value. Once the PEC byte is received, it is copied into the
I2C_RXDR register like any other data, and the RXNE flag is set.


Upon a PEC mismatch, the PECERR flag is set and an interrupt is generated if the ERRIE
bit of the I2C_CR1 register is set.


If no ACK software control is required, the user can set the PECBYTE bit and, in the same
write operation, load NBYTES[7:0] with the number of bytes to receive in a continuous flow.
After the receipt of NBYTES[7:0] - 1 bytes, the next received byte is checked as being the
PEC.


**Caution:** The PECBYTE bit has no effect when the RELOAD bit is set.


RM0490 Rev 5 717/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**Figure 248. Transfer sequence flow for SMBus target receiver N bytes + PEC**















718/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**Figure 249. Bus transfer diagrams for SMBus target receiver (SBC = 1)**















































**25.4.15** **SMBus controller mode**





This section pertains to the instances of the I2C peripheral supporting SMBus. Refer to
_Section 25.3: I2C implementation_ .


In addition to I2C controller transfer management (refer to _Section 25.4.9: I2C controller_
_mode_ ), this section provides extra software flowcharts to support SMBus.


**SMBus controller transmitter**


When the SMBus controller wants to transmit the PEC, the PECBYTE bit must be set and
the number of bytes must be loaded in the NBYTES[7:0] bitfield, before setting the START
bit. In this case, the total number of TXIS interrupts is NBYTES[7:0] - 1. So if the PECBYTE
bit is set when NBYTES[7:0] = 0x1, the content of the I2C_PECR register is automatically
transmitted.


RM0490 Rev 5 719/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


If the SMBus controller wants to send a STOP condition after the PEC, the automatic end
mode must be selected (AUTOEND = 1). In this case, the STOP condition automatically
follows the PEC transmission.


When the SMBus controller wants to send a RESTART condition after the PEC, the
software mode must be selected (AUTOEND = 0). In this case, once NBYTES[7:0] - 1 are
transmitted, the I2C_PECR register content is transmitted. The TC flag is set after the PEC
transmission, stretching the SCL line low. The RESTART condition must be programmed in
the TC interrupt subroutine.


**Caution:** The PECBYTE bit has no effect when the RELOAD bit is set.


**Figure 250. Bus transfer diagrams for SMBus controller transmitter**













































720/1027 RM0490 Rev 5




**RM0490** **Inter-integrated circuit interface (I2C)**


**SMBus controller receiver**


When the SMBus controller wants to receive, at the end of the transfer, the PEC followed by
a STOP condition, the automatic end mode can be selected (AUTOEND = 1). The
PECBYTE bit must be set and the target address programmed before setting the START bit.
In this case, after the receipt of NBYTES[7:0] - 1 data bytes, the next received byte is
automatically checked versus the I2C_PECR register content. A NACK response is given to
the PEC byte, followed by a STOP condition.


When the SMBus controller receiver wants to receive, at the end of the transfer, the PEC
byte followed by a RESTART condition, the software mode must be selected (AUTOEND =
0). The PECBYTE bit must be set and the target address programmed before setting the
START bit. In this case, after the receipt of NBYTES[7:0] - 1 data bytes, the next received
byte is automatically checked versus the I2C_PECR register content. The TC flag is set
after the PEC byte reception, stretching the SCL line low. The RESTART condition can be
programmed in the TC interrupt subroutine.


**Caution:** The PECBYTE bit has no effect when the RELOAD bit is set.


RM0490 Rev 5 721/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**Figure 251. Bus transfer diagrams for SMBus controller receiver**























































**25.4.16** **Wake-up from Stop mode on address match**





This section pertains to I2C instances supporting the wake-up from Stop mode feature (refer
to _Section 25.3)_ .

The I2C peripheral is able to wake up the device from Stop mode (APB clock is off), when
the device is addressed. All addressing modes are supported.


The wake-up from Stop mode is enabled by setting the WUPEN bit of the I2C_CR1 register.
The HSI48 oscillator must be selected as the clock source for I2CCLK to allow the wake-up
from Stop mode.


In Stop mode, the HSI48 oscillator is stopped. Upon detecting START condition, the I2C
interface starts the HSI48 oscillator and stretches SCL low until the oscillator wakes up.


HSI48 is then used for the address reception.


722/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


If the received address matches the device own address, I2C stretches SCL low until the
device wakes up. The stretch is released when the ADDR flag is cleared by software. Then
the transfer goes on normally.


If the address does not match, the HSI48 oscillator is stopped again and the device does not
wake up.


_Note:_ _When the system clock is used as I2C clock, or when WUPEN = 0,_ _the HSI48 oscillator_
_does not start upon receiving START condition._


_Only an ADDR interrupt can wake the device up. Therefore, do not enter Stop mode when_
_I2C is performing a transfer, either as a controller or as an addressed target after the ADDR_
_flag is set. This can be managed by clearing the SLEEPDEEP bit in the ADDR interrupt_
_routine and setting it again only after the STOPF flag is set._


**Caution:** The digital filter is not compatible with the wake-up from Stop mode feature. Before entering
Stop mode with the WUPEN bit set, deactivate the digital filter, by writing zero to the
DNF[3:0] bitfield.


**Caution:** The feature is only available when the HSI48 oscillator is selected as the I2C clock.


**Caution:** Clock stretching must be enabled (NOSTRETCH = 0) to ensure proper operation of the
wake-up from Stop mode feature.


**Caution:** If the wake-up from Stop mode is disabled (WUPEN = 0), the I2C peripheral must be
disabled before entering Stop mode (PE = 0).


**25.4.17** **Error conditions**


The following errors are the conditions that can cause the communication to fail.


**Bus error (BERR)**


A bus error is detected when a START or a STOP condition is detected and is not located

after a multiple of nine SCL clock pulses. START or STOP condition is detected when an
SDA edge occurs while SCL is high.


The bus error flag is set only if the I2C peripheral is involved in the transfer as controller or
addressed target (that is, not during the address phase in target mode).


In case of a misplaced START or RESTART detection in target mode, the I2C peripheral
enters address recognition state like for a correct START condition.


When a bus error is detected, the BERR flag of the I2C_ISR register is set, and an interrupt
is generated if the ERRIE bit of the I2C_CR1 register is set.


**Arbitration loss (ARLO)**


An arbitration loss is detected when a high level is sent on the SDA line, but a low level is
sampled on the SCL rising edge.


In controller mode, arbitration loss is detected during the address phase, data phase and
data acknowledge phase. In this case, the SDA and SCL lines are released, the START
control bit is cleared by hardware and the controller switches automatically to target mode.


In target mode, arbitration loss is detected during data phase and data acknowledge phase.
In this case, the transfer is stopped and the SCL and SDA lines are released.


When an arbitration loss is detected, the ARLO flag of the I2C_ISR register is set and an
interrupt is generated if the ERRIE bit of the I2C_CR1 register is set.


RM0490 Rev 5 723/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**Overrun/underrun error (OVR)**


An overrun or underrun error is detected in target mode when NOSTRETCH = 1 and:


      - In reception when a new byte is received and the RXDR register has not been read yet.
The new received byte is lost, and a NACK is automatically sent as a response to the
new byte.


      - In transmission:


–
When STOPF = 1 and the first data byte must be sent. The content of the
I2C_TXDR register is sent if TXE = 0, 0xFF if not.


–
When a new byte must be sent and the I2C_TXDR register has not been written
yet, 0xFF is sent.


When an overrun or underrun error is detected, the OVR flag of the I2C_ISR register is set
and an interrupt is generated if the ERRIE bit of the I2C_CR1 register is set.


**Packet error checking error (PECERR)**


This section pertains to the instances of the I2C peripheral supporting SMBus. Refer to
_Section 25.3: I2C implementation_ .


A PEC error is detected when the received PEC byte does not match the I2C_PECR
register content. A NACK is automatically sent after the wrong PEC reception.


When a PEC error is detected, the PECERR flag of the I2C_ISR register is set and an
interrupt is generated if the ERRIE bit of the I2C_CR1 register is set.


**Timeout error (TIMEOUT)**


This section pertains to the instances of the I2C peripheral supporting SMBus. Refer to
_Section 25.3: I2C implementation_ .


A timeout error occurs for any of these conditions:


      - TIDLE = 0 and SCL remains low for the time defined in the TIMEOUTA[11:0] bitfield:
this is used to detect an SMBus timeout.


      - TIDLE = 1 and both SDA and SCL remains high for the time defined in the TIMEOUTA

[11:0] bitfield: this is used to detect a bus idle condition.


      - Controller cumulative clock low extend time reaches the time defined in the
TIMEOUTB[11:0] bitfield (SMBus t LOW:MEXT parameter).


      - Target cumulative clock low extend time reaches the time defined in the
TIMEOUTB[11:0] bitfield (SMBus t LOW:SEXT parameter).


When a timeout violation is detected in controller mode, a STOP condition is automatically
sent.


When a timeout violation is detected in target mode, the SDA and SCL lines are
automatically released.


When a timeout error is detected, the TIMEOUT flag is set in the I2C_ISR register and an
interrupt is generated if the ERRIE bit of the I2C_CR1 register is set.


**Alert (ALERT)**


This section pertains to the instances of the I2C peripheral supporting SMBus. Refer to
_Section 25.3: I2C implementation_ .


724/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


The ALERT flag is set when the I2C peripheral is configured as a host (SMBHEN = 1), the
SMBALERT# signal detection is enabled (ALERTEN = 1), and a falling edge is detected on
the SMBA pin. An interrupt is generated if the ERRIE bit of the I2C_CR1 register is set.

## **25.5 I2C in low-power modes**


**Table 120. Effect of low-power modes to I2C**







|Mode|Description|
|---|---|
|Sleep|No effect. I2C interrupts cause the device to exit the Sleep mode.|
|Stop(1)|The contents of I2C registers are kept.<br>– WUPEN = 1 and I2C is clocked by an internal oscillator (HSI48). The address<br>recognition is functional. The I2C address match condition causes the device to exit the<br>Stop mode.<br>– WUPEN = 0: the I2C must be disabled before entering Stop mode.|
|Standby|The I2C peripheral is powered down. It must be reinitialized after exiting Standby mode.|


1. Refer to _Section 25.3: I2C implementation_ for information about the Stop modes supported by each
instance. If the wake-up from a specific stop mode is not supported, the instance must be disabled before
entering that specific Stop mode.

## **25.6 I2C interrupts**


The following table gives the list of I2C interrupt requests.


**Table 121. I2C interrupt requests**

















|Interrupt<br>acronym|Interrupt<br>event|Event flag|Enable<br>control bit|Interrupt clear<br>method|Exit<br>Sleep<br>mode|Exit<br>Stop<br>modes|Exit<br>Standby<br>modes|
|---|---|---|---|---|---|---|---|
|I2C_EV|Receive buffer not<br>empty|RXNE|RXIE|Read I2C_RXDR<br>register|Yes|No|No|
|I2C_EV|Transmit buffer<br>interrupt status|TXIS|TXIE|Write I2C_TXDR<br>register|Write I2C_TXDR<br>register|Write I2C_TXDR<br>register|Write I2C_TXDR<br>register|
|I2C_EV|STOP detection<br>interrupt flag|STOPF|STOPIE|Write STOPCF = 1|Write STOPCF = 1|Write STOPCF = 1|Write STOPCF = 1|
|I2C_EV|Transfer complete<br>reload|TCR|TCIE|Write I2C_CR2 with<br>NBYTES[7:0] ≠ 0|Write I2C_CR2 with<br>NBYTES[7:0] ≠ 0|Write I2C_CR2 with<br>NBYTES[7:0] ≠ 0|Write I2C_CR2 with<br>NBYTES[7:0] ≠ 0|
|I2C_EV|Transfer complete|TC|TC|Write START = 1 or<br>STOP = 1|Write START = 1 or<br>STOP = 1|Write START = 1 or<br>STOP = 1|Write START = 1 or<br>STOP = 1|
|I2C_EV|Address matched|ADDR|ADDRIE|Write ADDRCF = 1|Write ADDRCF = 1|Yes(1)|Yes(1)|
|I2C_EV|NACK reception|NACKF|NACKIE|Write NACKCF = 1|Write NACKCF = 1|No|No|
|I2C_ERR|Bus error|BERR|ERRIE|Write BERRCF = 1|Yes|No|No|
|I2C_ERR|Arbitration loss|ARLO|ARLO|Write ARLOCF = 1|Write ARLOCF = 1|Write ARLOCF = 1|Write ARLOCF = 1|
|I2C_ERR|Overrun/underrun|OVR|OVR|Write OVRCF = 1|Write OVRCF = 1|Write OVRCF = 1|Write OVRCF = 1|


RM0490 Rev 5 725/1027









741


**Inter-integrated circuit interface (I2C)** **RM0490**


**Table 121. I2C interrupt requests (continued)**


















|Interrupt<br>acronym|Interrupt<br>event|Event flag|Enable<br>control bit|Interrupt clear<br>method|Exit<br>Sleep<br>mode|Exit<br>Stop<br>modes|Exit<br>Standby<br>modes|
|---|---|---|---|---|---|---|---|
|I2C_ERR|PEC error|PECERR|ERRIE|Write PECERRCF = 1|Yes|No|No|
|I2C_ERR|Timeout/<br>tLOW error|TIMEOUT|TIMEOUT|Write<br>TIMEOUTCF = 1|Write<br>TIMEOUTCF = 1|Write<br>TIMEOUTCF = 1|Write<br>TIMEOUTCF = 1|
|I2C_ERR|SMBus alert|ALERT|ALERT|Write ALERTCF = 1|Write ALERTCF = 1|Write ALERTCF = 1|Write ALERTCF = 1|



1. The ADDR match event can wake up the device from Stop mode only if the I2C instance supports the wake-up from Stop
mode feature. Refer to _Section 25.3: I2C implementation_ .

## **25.7 I2C DMA requests**


**25.7.1** **Transmission using DMA**


DMA (direct memory access) can be enabled for transmission by setting the TXDMAEN bit
of the I2C_CR1 register. Data is loaded from an SRAM area configured through the DMA
peripheral (see _Section 11: Direct memory access controller (DMA)_ ) to the I2C_TXDR
register whenever the TXIS bit is set.


Only the data are transferred with DMA.


In controller mode, the initialization, the target address, direction, number of bytes and
START bit are programmed by software (the transmitted target address cannot be
transferred with DMA). When all data are transferred using DMA, DMA must be initialized
before setting the START bit. The end of transfer is managed with the NBYTES counter.
Refer to _Controller transmitter_ .


In target mode:


       - With NOSTRETCH = 0, when all data are transferred using DMA, DMA must be
initialized before the address match event, or in ADDR interrupt subroutine, before
clearing ADDR.


       - With NOSTRETCH = 1, the DMA must be initialized before the address match event.


The PEC transfer is managed with the counter associated to the NBYTES[7:0] bitfield. Refer
to _SMBus target transmitter_ and _SMBus controller transmitter_ . This applies to the instances
of the I2C peripheral supporting SMBus.


_Note:_ _If DMA is used for transmission, it is not required to set the TXIE bit._


**25.7.2** **Reception using DMA**


DMA (direct memory access) can be enabled for reception by setting the RXDMAEN bit of
the I2C_CR1 register. Data is loaded from the I2C_RXDR register to an SRAM area
configured through the DMA peripheral (refer to _Section 11: Direct memory access_
_controller (DMA)_ ) whenever the RXNE bit is set. Only the data (including PEC) are
transferred with DMA.


In controller mode, the initialization, the target address, direction, number of bytes and
START bit are programmed by software. When all data are transferred using DMA, DMA
must be initialized before setting the START bit. The end of transfer is managed with the
NBYTES counter.


726/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


In target mode with NOSTRETCH = 0, when all data are transferred using DMA, DMA must
be initialized before the address match event, or in the ADDR interrupt subroutine, before
clearing the ADDR flag.


The PEC transfer is managed with the counter associated to the NBYTES[7:0] bitfield. Refer
to _SMBus target receiver_ and _SMBus controller receiver_ . This applies to the instances of the
I2C peripheral supporting SMBus.


_Note:_ _If DMA is used for reception, it is not required to set the RXIE bit._

## **25.8 I2C debug modes**


When the device enters debug mode (core halted), the SMBus timeout either continues
working normally or stops, depending on the DBG_I2C1_SMBUS_TIMEOUT bit in the DBG
block.

## **25.9 I2C registers**


Refer to _Section 1.2_ for the list of abbreviations used in register descriptions.


The registers are accessed by words (32-bit).


**25.9.1** **I2C control register 1 (I2C_CR1)**


Address offset: 0x00


Reset value: 0x0000 0000


Access: no wait states, except if a write access occurs while a write access is ongoing. In
this case, wait states are inserted in the second write access, until the previous one is
completed. The latency of the second write access can be up to 2 x PCLK + 6 x I2CCLK.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PECEN|ALERT<br>EN|SMBD<br>EN|SMBH<br>EN|GCEN|WUPE<br>N|NOSTR<br>ETCH|SBC|
|||||||||rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11 10 9 8|Col6|Col7|Col8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|RXDM<br>AEN|TXDMA<br>EN|Res.|ANF<br>OFF|DNF[3:0]|DNF[3:0]|DNF[3:0]|DNF[3:0]|ERRIE|TCIE|STOP<br>IE|NACKI<br>E|ADDRI<br>E|RXIE|TXIE|PE|
|rw|rw||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:24 Reserved, must be kept at reset value.


Bit 23 **PECEN:** PEC enable

0: PEC calculation disabled

1: PEC calculation enabled

On the instances of the I2C peripheral that do not support the SMBus feature, this bit is
reserved and forced by hardware to 0. Refer to _Section 25.3_ .


RM0490 Rev 5 727/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


Bit 22 **ALERTEN** : SMBus alert enable

0: The SMBALERT# signal on SMBA pin is not supported in host mode (SMBHEN = 1). In
device mode (SMBHEN = 0), the SMBA pin is released and the alert response address
header is disabled (0001100x followed by NACK).
1: The SMBALERT# signal on SMBA pin is supported in host mode (SMBHEN = 1). In
device mode (SMBHEN = 0), the SMBA pin is driven low and the alert response address
header is enabled (0001100x followed by ACK).
On the instances of the I2C peripheral that do not support the SMBus feature, this bit is
reserved and forced by hardware to 0. Refer to _Section 25.3_ .

_Note: When ALERTEN = 0, the SMBA pin can be used as a standard GPIO._


Bit 21 **SMBDEN** : SMBus device default address enable

0: Device default address disabled. Address 0b1100001x is NACKed.

1: Device default address enabled. Address 0b1100001x is ACKed.

On the instances of the I2C peripheral that do not support the SMBus feature, this bit is
reserved and forced by hardware to 0. Refer to _Section 25.3_ .


Bit 20 **SMBHEN** : SMBus host address enable

0: Host address disabled. Address 0b0001000x is NACKed.

1: Host address enabled. Address 0b0001000x is ACKed.

On the instances of the I2C peripheral that do not support the SMBus feature, this bit is
reserved and forced by hardware to 0. Refer to _Section 25.3_ .


Bit 19 **GCEN** : General call enable

0: General call disabled. Address 0b00000000 is NACKed.

1: General call enabled. Address 0b00000000 is ACKed.


Bit 18 **WUPEN** : Wake-up from Stop mode enable

0: Wake-up from Stop mode disabled.
1: Wake-up from Stop mode enabled.
On the instances of the I2C peripheral that do not support the wake-up from Stop mode
feature, this bit is reserved and forced by hardware to 0. Refer to _Section 25.3_ .

_Note: WUPEN can be set only when DNF[3:0] = 0000._


Bit 17 **NOSTRETCH** : Clock stretching disable

This bit is used to disable clock stretching in target mode. It must be kept cleared in
controller mode.

0: Clock stretching enabled
1: Clock stretching disabled

_Note: This bit can be programmed only when the I2C peripheral is disabled (PE = 0)._


Bit 16 **SBC** : Target byte control

This bit is used to enable hardware byte control in target mode.
0: Target byte control disabled
1: Target byte control enabled


Bit 15 **RXDMAEN** : DMA reception requests enable

0: DMA mode disabled for reception
1: DMA mode enabled for reception


Bit 14 **TXDMAEN** : DMA transmission requests enable

0: DMA mode disabled for transmission

1: DMA mode enabled for transmission


Bit 13 Reserved, must be kept at reset value.


728/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


Bit 12 **ANFOFF:** Analog noise filter OFF

0: Analog noise filter enabled
1: Analog noise filter disabled

_Note: This bit can be programmed only when the I2C peripheral is disabled (PE = 0)._


Bits 11:8 **DNF[3:0]** : Digital noise filter

These bits are used to configure the digital noise filter on SDA and SCL input. The digital
filter, filters spikes with a length of up to DNF[3:0] ***** t I2CCLK
0000: Digital filter disabled
0001: Digital filter enabled and filtering capability up to one t I2CCLK

...

1111: digital filter enabled and filtering capability up to fifteen t I2CCLK
_Note: If the analog filter is enabled, the digital filter is added to it. This filter can be_
_programmed only when the I2C peripheral is disabled (PE = 0)._


Bit 7 **ERRIE** : Error interrupts enable

0: Error detection interrupts disabled
1: Error detection interrupts enabled

_Note: Any of these errors generates an interrupt:_

_- arbitration loss (ARLO)_

_- bus error detection (BERR)_

_- overrun/underrun (OVR)_

_- timeout detection (TIMEOUT)_

_- PEC error detection (PECERR)_

_- alert pin event detection (ALERT)_


Bit 6 **TCIE** : Transfer complete interrupt enable

0: Transfer complete interrupt disabled
1: Transfer complete interrupt enabled

_Note: Any of these events generates an interrupt:_

_Transfer complete (TC)_

_Transfer complete reload (TCR)_


Bit 5 **STOPIE** : STOP detection interrupt enable

0: STOP detection (STOPF) interrupt disabled
1: STOP detection (STOPF) interrupt enabled


Bit 4 **NACKIE** : Not acknowledge received interrupt enable

0: Not acknowledge (NACKF) received interrupts disabled
1: Not acknowledge (NACKF) received interrupts enabled


Bit 3 **ADDRIE** : Address match interrupt enable (target only)

0: Address match (ADDR) interrupts disabled
1: Address match (ADDR) interrupts enabled


Bit 2 **RXIE** : RX interrupt enable

0: Receive (RXNE) interrupt disabled
1: Receive (RXNE) interrupt enabled


Bit 1 **TXIE** : TX interrupt enable

0: Transmit (TXIS) interrupt disabled
1: Transmit (TXIS) interrupt enabled


RM0490 Rev 5 729/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


Bit 0 **PE** : Peripheral enable

0: Peripheral disabled
1: Peripheral enabled

_Note: When PE = 0, the I2C SCL and SDA lines are released. Internal state machines and_
_status bits are put back to their reset value. When cleared, PE must be kept low for at_
_least three APB clock cycles._


**25.9.2** **I2C control register 2 (I2C_CR2)**


Address offset: 0x04


Reset value: 0x0000 0000


Access: no wait states, except if a write access occurs while a write access is ongoing. In
this case, wait states are inserted in the second write access until the previous one is
completed. The latency of the second write access can be up to 2 x PCLK + 6 x I2CCLK.

|31|30|29|28|27|26|25|24|23 22 21 20 19 18 17 16|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|PECBY<br>TE|AUTOE<br>ND|RELOA<br>D|NBYTES[7:0]|NBYTES[7:0]|NBYTES[7:0]|NBYTES[7:0]|NBYTES[7:0]|NBYTES[7:0]|NBYTES[7:0]|NBYTES[7:0]|
||||||rs|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9 8 7 6 5 4 3 2 1 0|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|NACK|STOP|START|HEAD1<br>0R|ADD10|RD_W<br>RN|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|
|rs|rs|rs|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:27 Reserved, must be kept at reset value.


Bit 26 **PECBYTE** : Packet error checking byte

This bit is set by software, and cleared by hardware when the PEC is transferred, or when a
STOP condition or an Address matched is received, also when PE = 0.

0: No PEC transfer

1: PEC transmission/reception is requested
On the instances of the I2C peripheral that do not support the SMBus feature, this bit is
reserved and forced by hardware to 0. Refer to _Section 25.3_ .

_Note: Writing 0 to this bit has no effect._

_This bit has no effect when RELOAD is set, and in target mode when SBC = 0._


Bit 25 **AUTOEND** : Automatic end mode (controller mode)

This bit is set and cleared by software.
0: software end mode: TC flag is set when NBYTES data are transferred, stretching SCL low.
1: Automatic end mode: a STOP condition is automatically sent when NBYTES data are
transferred.

_Note: This bit has no effect in target mode or when the RELOAD bit is set._


Bit 24 **RELOAD** : NBYTES reload mode

This bit is set and cleared by software.
0: The transfer is completed after the NBYTES data transfer (STOP or RESTART follows).
1: The transfer is not completed after the NBYTES data transfer (NBYTES is reloaded). TCR
flag is set when NBYTES data are transferred, stretching SCL low.


Bits 23:16 **NBYTES[7:0]** : Number of bytes

The number of bytes to be transmitted/received is programmed there. This field is don’t care
in target mode with SBC = 0.

_Note: Changing these bits when the START bit is set is not allowed._


730/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


Bit 15 **NACK** : NACK generation (target mode)

The bit is set by software, cleared by hardware when the NACK is sent, or when a STOP
condition or an Address matched is received, or when PE = 0.
0: an ACK is sent after current received byte.
1: a NACK is sent after current received byte.

_Note: Writing 0 to this bit has no effect._

_This bit is used only in target mode: in controller receiver mode, NACK is automatically_
_generated after last byte preceding STOP or RESTART condition, whatever the NACK_
_bit value._

_When an overrun occurs in target receiver NOSTRETCH mode, a NACK is_
_automatically generated, whatever the NACK bit value._

_When hardware PEC checking is enabled (PECBYTE = 1), the PEC acknowledge value_
_does not depend on the NACK value._


Bit 14 **STOP** : STOP condition generation

This bit only pertains to controller mode. It is set by software and cleared by hardware when
a STOP condition is detected or when PE = 0.

0: No STOP generation
1: STOP generation after current byte transfer

_Note: Writing 0 to this bit has no effect._


Bit 13 **START** : START condition generation

This bit is set by software. It is cleared by hardware after the START condition followed by
the address sequence is sent, by an arbitration loss, by an address matched in target mode,
by a timeout error detection, or when PE = 0.
0: No START generation
1: RESTART/START generation:
If the I2C is already in controller mode with AUTOEND = 0, setting this bit generates a
repeated START condition when RELOAD = 0, after the end of the NBYTES transfer.
Otherwise, setting this bit generates a START condition once the bus is free.

_Note: Writing 0 to this bit has no effect._

_The START bit can be set even if the bus is BUSY or I2C is in target mode._

_This bit has no effect when RELOAD is set._


Bit 12 **HEAD10R** : 10-bit address header only read direction (controller receiver mode)

0: The controller sends the complete 10-bit target address read sequence: START + 2 bytes
10-bit address in write direction + RESTART + first seven bits of the 10-bit address in read

direction.

1: The controller sends only the first seven bits of the 10-bit address, followed by read
direction.

_Note: Changing this bit when the START bit is set is not allowed._


Bit 11 **ADD10** : 10-bit addressing mode (controller mode)

0: The controller operates in 7-bit addressing mode
1: The controller operates in 10-bit addressing mode

_Note: Changing this bit when the START bit is set is not allowed._


Bit 10 **RD_WRN** : Transfer direction (controller mode)

0: Controller requests a write transfer
1: Controller requests a read transfer

_Note: Changing this bit when the START bit is set is not allowed._


RM0490 Rev 5 731/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


Bits 9:0 **SADD[9:0]** : Target address (controller mode)

**Condition: In 7-bit addressing mode (ADD10 = 0)** :
SADD[7:1] must be written with the 7-bit target address to be sent. Bits SADD[9], SADD[8]
and SADD[0] are don't care.
**Condition: In 10-bit addressing mode (ADD10 = 1)** :
SADD[9:0] must be written with the 10-bit target address to be sent.

_Note: Changing these bits when the START bit is set is not allowed._


**25.9.3** **I2C own address 1 register (I2C_OAR1)**


Address offset: 0x08


Reset value: 0x0000 0000


Access: no wait states, except if a write access occurs while a write access is ongoing. In
this case, wait states are inserted in the second write access until the previous one is
completed. The latency of the second write access can be up to 2 x PCLK + 6 x I2CCLK.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9 8 7 6 5 4 3 2 1 0|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|OA1EN|Res.|Res.|Res.|Res.|OA1M<br>ODE|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|
|rw|||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bit 15 **OA1EN** : Own address 1 enable

0: Own address 1 disabled. The received target address OA1 is NACKed.
1: Own address 1 enabled. The received target address OA1 is ACKed.


Bits 14:11 Reserved, must be kept at reset value.


Bit 10 **OA1MODE** : Own address 1 10-bit mode

0: Own address 1 is a 7-bit address.

1: Own address 1 is a 10-bit address.

_Note: This bit can be written only when OA1EN = 0._


Bits 9:0 **OA1[9:0]** : Interface own target address

7-bit addressing mode: OA1[7:1] contains the 7-bit own target address. Bits OA1[9], OA1[8]
and OA1[0] are don't care.
10-bit addressing mode: OA1[9:0] contains the 10-bit own target address.

_Note: These bits can be written only when OA1EN = 0._


732/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**25.9.4** **I2C own address 2 register (I2C_OAR2)**


Address offset: 0x0C


Reset value: 0x0000 0000


Access: no wait states, except if a write access occurs while a write access is ongoing. In
this case, wait states are inserted in the second write access, until the previous one is
completed. The latency of the second write access can be up to 2x PCLK + 6 x I2CCLK.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10 9 8|Col7|Col8|7 6 5 4 3 2 1|Col10|Col11|Col12|Col13|Col14|Col15|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|OA2EN|Res.|Res.|Res.|Res.|OA2MSK[2:0]|OA2MSK[2:0]|OA2MSK[2:0]|OA2[7:1]|OA2[7:1]|OA2[7:1]|OA2[7:1]|OA2[7:1]|OA2[7:1]|OA2[7:1]|Res.|
|rw|||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw||



Bits 31:16 Reserved, must be kept at reset value.


Bit 15 **OA2EN** : Own address 2 enable

0: Own address 2 disabled. The received target address OA2 is NACKed.
1: Own address 2 enabled. The received target address OA2 is ACKed.


Bits 14:11 Reserved, must be kept at reset value.


Bits 10:8 **OA2MSK[2:0]** : Own address 2 masks

000: No mask

001: OA2[1] is masked and don’t care. Only OA2[7:2] are compared.
010: OA2[2:1] are masked and don’t care. Only OA2[7:3] are compared.
011: OA2[3:1] are masked and don’t care. Only OA2[7:4] are compared.
100: OA2[4:1] are masked and don’t care. Only OA2[7:5] are compared.
101: OA2[5:1] are masked and don’t care. Only OA2[7:6] are compared.
110: OA2[6:1] are masked and don’t care. Only OA2[7] is compared.
111: OA2[7:1] are masked and don’t care. No comparison is done, and all (except reserved)
7-bit received addresses are acknowledged.

_Note: These bits can be written only when OA2EN = 0._

_As soon as OA2MSK ≠ 0, the reserved I2C addresses (0b0000xxx and 0b1111xxx) are_
_not acknowledged, even if the comparison matches._


Bits 7:1 **OA2[7:1]** : Interface address

7-bit addressing mode: 7-bit address

_Note: These bits can be written only when OA2EN = 0._


Bit 0 Reserved, must be kept at reset value.


RM0490 Rev 5 733/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**25.9.5** **I2C timing register (I2C_TIMINGR)**


Address offset: 0x10


Reset value: 0x0000 0000


Access: no wait states

|31 30 29 28|Col2|Col3|Col4|27|26|25|24|23 22 21 20|Col10|Col11|Col12|19 18 17 16|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PRESC[3:0]|PRESC[3:0]|PRESC[3:0]|PRESC[3:0]|Res.|Res.|Res.|Res.|SCLDEL[3:0]|SCLDEL[3:0]|SCLDEL[3:0]|SCLDEL[3:0]|SDADEL[3:0]|SDADEL[3:0]|SDADEL[3:0]|SDADEL[3:0]|
|rw|rw|rw|rw|||||rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SCLH[7:0]|SCLH[7:0]|SCLH[7:0]|SCLH[7:0]|SCLH[7:0]|SCLH[7:0]|SCLH[7:0]|SCLH[7:0]|SCLL[7:0]|SCLL[7:0]|SCLL[7:0]|SCLL[7:0]|SCLL[7:0]|SCLL[7:0]|SCLL[7:0]|SCLL[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:28 **PRESC[3:0]** : Timing prescaler

This field is used to prescale I2CCLK to generate the clock period t PRESC used for data setup
and hold counters (refer to section _I2C timings_ ), and for SCL high and low level counters
(refer to section _I2C controller initialization_ ).
t PRESC = (PRESC + 1) x t I2CCLK


Bits 27:24 Reserved, must be kept at reset value.


Bits 23:20 **SCLDEL[3:0]** : Data setup time

This field is used to generate a delay t SCLDEL = (SCLDEL + 1) x t PRESC between SDA edge
and SCL rising edge. In controller and in target modes with NOSTRETCH = 0, the SCL line is
stretched low during t SCLDEL .
_Note: t_ _SCLDEL_ _is used to generate t_ _SU:DAT_ _timing._


Bits 19:16 **SDADEL[3:0]** : Data hold time

This field is used to generate the delay t SDADEL between SCL falling edge and SDA edge. In
controller and in target modes with NOSTRETCH = 0, the SCL line is stretched low during
t SDADEL .
t SDADEL = SDADEL x t PRESC
_Note: SDADEL is used to generate t_ _HD:DAT_ _timing._


Bits 15:8 **SCLH[7:0]** : SCL high period (controller mode)

This field is used to generate the SCL high period in controller mode.
t SCLH = (SCLH + 1) x t PRESC
_Note: SCLH is also used to generate t_ _SU:STO_ _and t_ _HD:STA_ _timing._


Bits 7:0 **SCLL[7:0]** : SCL low period (controller mode)

This field is used to generate the SCL low period in controller mode.
t SCLL = (SCLL + 1) x t PRESC
_Note: SCLL is also used to generate t_ _BUF_ _and t_ _SU:STA_ _timings._


_Note:_ _This register must be configured when the I2C peripheral is disabled (PE = 0)._


_Note:_ _The STM32CubeMX tool calculates and provides the I2C_TIMINGR content in the I2C_
_Configuration window._


734/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**25.9.6** **I2C timeout register (I2C_TIMEOUTR)**


Address offset: 0x14


Reset value: 0x0000 0000


Access: no wait states, except if a write access occurs while a write access is ongoing. In
this case, wait states are inserted in the second write access until the previous one is
completed. The latency of the second write access can be up to 2 x PCLK + 6 x I2CCLK.


On the instances of the I2C peripheral that do not support the SMBus feature, this register is
reserved, and its bits are forced by hardware to 0. Refer to _Section 25.3_ .

|31|30|29|28|27 26 25 24 23 22 21 20 19 18 17 16|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TEXTE<br>N|Res.|Res.|Res.|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|
|rw||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11 10 9 8 7 6 5 4 3 2 1 0|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|TIMOU<br>TEN|Res.|Res.|TIDLE|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|
|rw|||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 31 **TEXTEN** : Extended clock timeout enable

0: Extended clock timeout detection is disabled

1: Extended clock timeout detection is enabled. When a cumulative SCL stretch for more
than t LOW:EXT is done by the I2C interface, a timeout error is detected (TIMEOUT = 1).


Bits 30:28 Reserved, must be kept at reset value.


Bits 27:16 **TIMEOUTB[11:0]** : Bus timeout B

This field is used to configure the cumulative clock extension timeout:

–
Controller mode: the controller cumulative clock low extend time (t LOW:MEXT ) is
detected

–
Target mode: the target cumulative clock low extend time (t LOW:SEXT ) is detected
t LOW:EXT = (TIMEOUTB + TIDLE = 01) x 2048 x t I2CCLK

_Note: These bits can be written only when TEXTEN = 0._


Bit 15 **TIMOUTEN** : Clock timeout enable

0: SCL timeout detection is disabled

1: SCL timeout detection is enabled. When SCL is low for more than t TIMEOUT (TIDLE = 0) or
high for more than t IDLE (TIDLE = 1), a timeout error is detected (TIMEOUT = 1).


Bits 14:13 Reserved, must be kept at reset value.


Bit 12 **TIDLE** : Idle clock timeout detection

0: TIMEOUTA is used to detect SCL low timeout

1: TIMEOUTA is used to detect both SCL and SDA high timeout (bus idle condition)

_Note: This bit can be written only when TIMOUTEN = 0._


Bits 11:0 **TIMEOUTA[11:0]** : Bus timeout A

This field is used to configure:
The SCL low timeout condition t TIMEOUT when TIDLE = 0
t TIMEOUT = (TIMEOUTA + 1) x 2048 x t I2CCLK
The bus idle condition (both SCL and SDA high) when TIDLE = 1
t IDLE = (TIMEOUTA + 1) x 4 x t I2CCLK
_Note: These bits can be written only when TIMOUTEN = 0._


RM0490 Rev 5 735/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**25.9.7** **I2C interrupt and status register (I2C_ISR)**


Address offset: 0x18


Reset value: 0x0000 0001


Access: no wait states

|31|30|29|28|27|26|25|24|23 22 21 20 19 18 17|Col10|Col11|Col12|Col13|Col14|Col15|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADDCODE[6:0]|ADDCODE[6:0]|ADDCODE[6:0]|ADDCODE[6:0]|ADDCODE[6:0]|ADDCODE[6:0]|ADDCODE[6:0]|DIR|
|||||||||r|r|r|r|r|r|r|r|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|BUSY|Res.|ALERT|TIMEO<br>UT|PECER<br>R|OVR|ARLO|BERR|TCR|TC|STOPF|NACKF|ADDR|RXNE|TXIS|TXE|
|r||r|r|r|r|r|r|r|r|r|r|r|r|rs|rs|



Bits 31:24 Reserved, must be kept at reset value.


Bits 23:17 **ADDCODE[6:0]** : Address match code (target mode)

These bits are updated with the received address when an address match event occurs
(ADDR = 1). In the case of a 10-bit address, ADDCODE provides the 10-bit header followed
by the two MSBs of the address.


Bit 16 **DIR** : Transfer direction (target mode)

This flag is updated when an address match event occurs (ADDR = 1).
0: Write transfer, target enters receiver mode.
1: Read transfer, target enters transmitter mode.


Bit 15 **BUSY** : Bus busy

This flag indicates that a communication is in progress on the bus. It is set by hardware
when a START condition is detected, and cleared by hardware when a STOP condition is
detected, or when PE = 0.


Bit 14 Reserved, must be kept at reset value.


Bit 13 **ALERT** : SMBus alert

This flag is set by hardware when SMBHEN = 1 (SMBus host configuration), ALERTEN = 1
and an SMBALERT# event (falling edge) is detected on SMBA pin. It is cleared by software
by setting the ALERTCF bit.
On the instances of the I2C peripheral that do not support the SMBus feature, this bit is
reserved and forced by hardware to 0. Refer to _Section 25.3_ .

_Note: This bit is cleared by hardware when PE = 0._


Bit 12 **TIMEOUT** : Timeout or t LOW detection flag
This flag is set by hardware when a timeout or extended clock timeout occurred. It is cleared
by software by setting the TIMEOUTCF bit.
On the instances of the I2C peripheral that do not support the SMBus feature, this bit is
reserved and forced by hardware to 0. Refer to _Section 25.3_ .

_Note: This bit is cleared by hardware when PE = 0._


Bit 11 **PECERR** : PEC error in reception

This flag is set by hardware when the received PEC does not match with the PEC register
content. A NACK is automatically sent after the wrong PEC reception. It is cleared by
software by setting the PECCF bit.
On the instances of the I2C peripheral that do not support the SMBus feature, this bit is
reserved and forced by hardware to 0. Refer to _Section 25.3_ .

_Note: This bit is cleared by hardware when PE = 0._


736/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


Bit 10 **OVR** : Overrun/underrun (target mode)

This flag is set by hardware in target mode with NOSTRETCH = 1, when an
overrun/underrun error occurs. It is cleared by software by setting the OVRCF bit _._

_Note: This bit is cleared by hardware when PE = 0._


Bit 9 **ARLO** : Arbitration lost

This flag is set by hardware in case of arbitration loss. It is cleared by software by setting the
ARLOCF bit.

_Note: This bit is cleared by hardware when PE = 0._


Bit 8 **BERR** : Bus error

This flag is set by hardware when a misplaced START or STOP condition is detected
whereas the peripheral is involved in the transfer. The flag is not set during the address
phase in target mode. It is cleared by software by setting the BERRCF bit.

_Note: This bit is cleared by hardware when PE = 0._


Bit 7 **TCR** : Transfer complete reload

This flag is set by hardware when RELOAD = 1 and NBYTES data have been transferred. It
is cleared by software when NBYTES is written to a non-zero value _._

_Note: This bit is cleared by hardware when PE = 0._

_This flag is only for controller mode, or for target mode when the SBC bit is set._


Bit 6 **TC** : Transfer complete (controller mode)

This flag is set by hardware when RELOAD = 0, AUTOEND = 0 and NBYTES data have
been transferred. It is cleared by software when START bit or STOP bit is set _._

_Note: This bit is cleared by hardware when PE = 0._


Bit 5 **STOPF** : STOP detection flag

This flag is set by hardware when a STOP condition is detected on the bus and the
peripheral is involved in this transfer:

–
as a controller, provided that the STOP condition is generated by the peripheral.

–
as a target, provided that the peripheral has been addressed previously during this
transfer.

It is cleared by software by setting the STOPCF bit.

_Note: This bit is cleared by hardware when PE = 0._


Bit 4 **NACKF** : Not acknowledge received flag

This flag is set by hardware when a NACK is received after a byte transmission. It is cleared
by software by setting the NACKCF bit.

_Note: This bit is cleared by hardware when PE = 0._


Bit 3 **ADDR** : Address matched (target mode)

This bit is set by hardware as soon as the received target address matched with one of the
enabled target addresses. It is cleared by software by setting _ADDRCF bit._

_Note: This bit is cleared by hardware when PE = 0._


Bit 2 **RXNE** : Receive data register not empty (receivers)

This bit is set by hardware when the received data is copied into the I2C_RXDR register, and
is ready to be read. It is cleared when I2C_RXDR is read.

_Note: This bit is cleared by hardware when PE = 0._


RM0490 Rev 5 737/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


Bit 1 **TXIS** : Transmit interrupt status (transmitters)

This bit is set by hardware when the I2C_TXDR register is empty and the data to be
transmitted must be written in the I2C_TXDR register. It is cleared when the next data to be
sent is written in the I2C_TXDR register.
This bit can be written to 1 by software only when NOSTRETCH = 1, to generate a TXIS
event (interrupt if TXIE = 1 or DMA request if TXDMAEN = 1).

_Note: This bit is cleared by hardware when PE = 0._


Bit 0 **TXE** : Transmit data register empty (transmitters)

This bit is set by hardware when the I2C_TXDR register is empty. It is cleared when the next
data to be sent is written in the I2C_TXDR register.
This bit can be written to 1 by software in order to flush the transmit data register I2C_TXDR.

_Note: This bit is set by hardware when PE = 0._


**25.9.8** **I2C interrupt clear register (I2C_ICR)**


Address offset: 0x1C


Reset value: 0x0000 0000


Access: no wait states

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|ALERT<br>CF|TIMOU<br>TCF|PECCF|OVRCF|ARLOC<br>F|BERRC<br>F|Res.|Res.|STOPC<br>F|NACKC<br>F|ADDR<br>CF|Res.|Res.|Res.|
|||w|w|w|w|w|w|||w|w|w||||



Bits 31:14 Reserved, must be kept at reset value.


Bit 13 **ALERTCF** : Alert flag clear

Writing 1 to this bit clears the ALERT flag in the I2C_ISR register.
On the instances of the I2C peripheral that do not support the SMBus feature, this bit is
reserved and forced by hardware to 0. Refer to _Section 25.3_ .


Bit 12 **TIMOUTCF** : Timeout detection flag clear

Writing 1 to this bit clears the TIMEOUT flag in the I2C_ISR register.
On the instances of the I2C peripheral that do not support the SMBus feature, this bit is
reserved and forced by hardware to 0. Refer to _Section 25.3_ .


Bit 11 **PECCF** : PEC error flag clear

Writing 1 to this bit clears the PECERR flag in the I2C_ISR register.
On the instances of the I2C peripheral that do not support the SMBus feature, this bit is
reserved and forced by hardware to 0. Refer to _Section 25.3_ .


Bit 10 **OVRCF** : Overrun/underrun flag clear

Writing 1 to this bit clears the OVR flag in the I2C_ISR register.


Bit 9 **ARLOCF** : Arbitration lost flag clear

Writing 1 to this bit clears the ARLO flag in the I2C_ISR register.


Bit 8 **BERRCF** : Bus error flag clear

Writing 1 to this bit clears the BERRF flag in the I2C_ISR register.


Bits 7:6 Reserved, must be kept at reset value.


738/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


Bit 5 **STOPCF** : STOP detection flag clear

Writing 1 to this bit clears the STOPF flag in the I2C_ISR register.


Bit 4 **NACKCF** : Not acknowledge flag clear

Writing 1 to this bit clears the NACKF flag in I2C_ISR register.


Bit 3 **ADDRCF** : Address matched flag clear

Writing 1 to this bit clears the ADDR flag in the I2C_ISR register. Writing 1 to this bit also
clears the START bit in the I2C_CR2 register.


Bits 2:0 Reserved, must be kept at reset value.


**25.9.9** **I2C PEC register (I2C_PECR)**


Address offset: 0x20


Reset value: 0x0000 0000


Access: no wait states


On the instances of the I2C peripheral that do not support the SMBus feature, this register is
reserved and its bits are forced by hardware to 0. Refer to _Section 25.3_ .

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|
|||||||||r|r|r|r|r|r|r|r|



Bits 31:8 Reserved, must be kept at reset value.


Bits 7:0 **PEC[7:0]:** Packet error checking register

This field contains the internal PEC when PECEN=1.

The PEC is cleared by hardware when PE = 0.


**25.9.10** **I2C receive data register (I2C_RXDR)**


Address offset: 0x24


Reset value: 0x0000 0000


Access: no wait states

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RXDATA[7:0]|RXDATA[7:0]|RXDATA[7:0]|RXDATA[7:0]|RXDATA[7:0]|RXDATA[7:0]|RXDATA[7:0]|RXDATA[7:0]|
|||||||||r|r|r|r|r|r|r|r|



Bits 31:8 Reserved, must be kept at reset value.


Bits 7:0 **RXDATA[7:0]:** 8-bit receive data

Data byte received from the I²C-bus.


RM0490 Rev 5 739/1027



741


**Inter-integrated circuit interface (I2C)** **RM0490**


**25.9.11** **I2C transmit data register (I2C_TXDR)**


Address offset: 0x28


Reset value: 0x0000 0000


Access: no wait states

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TXDATA[7:0]|TXDATA[7:0]|TXDATA[7:0]|TXDATA[7:0]|TXDATA[7:0]|TXDATA[7:0]|TXDATA[7:0]|TXDATA[7:0]|
|||||||||rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:8 Reserved, must be kept at reset value.


Bits 7:0 **TXDATA[7:0]:** 8-bit transmit data

Data byte to be transmitted to the I²C-bus

_Note: These bits can be written only when TXE = 1._


740/1027 RM0490 Rev 5


**RM0490** **Inter-integrated circuit interface (I2C)**


**25.9.12** **I2C register map**


The table below provides the I2C register map and the reset values.


**Table 122. I2C register map and reset values**



































































|Offset|Register<br>name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|I2C_CR1|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PECEN|ALERTEN|SMBDEN|SMBHEN|GCEN|WUPEN|NOSTRETCH|SBC|RXDMAEN|TXDMAEN|Res.|ANFOFF|DNF[3:0]|DNF[3:0]|DNF[3:0]|DNF[3:0]|ERRIE|TCIE|STOPIE|NACKIE|ADDRIE|RXIE|TXIE|PE|
|0x00|Reset value|||||||||0|0|0|0|0|0|0|0|0|0||0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x04|I2C_CR2|Res.|Res.|Res.|Res.|Res.|PECBYTE|AUTOEND|RELOAD|NBYTES[7:0]|NBYTES[7:0]|NBYTES[7:0]|NBYTES[7:0]|NBYTES[7:0]|NBYTES[7:0]|NBYTES[7:0]|NBYTES[7:0]|NACK|STOP|START|HEAD10R|ADD10|RD_WRN|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|SADD[9:0]|
|0x04|Reset value||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x08|I2C_OAR1|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|OA1EN|Res.|Res.|Res.|Res.|OA1MODE|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|OA1[9:0]|
|0x08|Reset value|||||||||||||||||0|||||0|0|0|0|0|0|0|0|0|0|0|
|0x0C|I2C_OAR2|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|OA2EN|Res.|Res.|Res.|Res.|OA2MS<br>K [2:0]|OA2MS<br>K [2:0]|OA2MS<br>K [2:0]|OA2[7:1]|OA2[7:1]|OA2[7:1]|OA2[7:1]|OA2[7:1]|OA2[7:1]|OA2[7:1]|Res.|
|0x0C|Reset value|||||||||||||||||0|||||0|0|0|0|0|0|0|0|0|0||
|0x10|I2C_<br>TIMINGR|PRESC[3:0]|PRESC[3:0]|PRESC[3:0]|PRESC[3:0]|Res.|Res.|Res.|Res.|SCLDEL<br>[3:0]|SCLDEL<br>[3:0]|SCLDEL<br>[3:0]|SCLDEL<br>[3:0]|SDADEL<br>[3:0]|SDADEL<br>[3:0]|SDADEL<br>[3:0]|SDADEL<br>[3:0]|SCLH[7:0]|SCLH[7:0]|SCLH[7:0]|SCLH[7:0]|SCLH[7:0]|SCLH[7:0]|SCLH[7:0]|SCLH[7:0]|SCLL[7:0]|SCLL[7:0]|SCLL[7:0]|SCLL[7:0]|SCLL[7:0]|SCLL[7:0]|SCLL[7:0]|SCLL[7:0]|
|0x10|Reset value|0|0|0|0|||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x14|I2C_<br>TIMEOUTR|TEXTEN|Res.|Res.|Res.|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMEOUTB[11:0]|TIMOUTEN|Res.|Res.|TIDLE|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|TIMEOUTA[11:0]|
|0x14|Reset value|0||||0|0|0|0|0|0|0|0|0|0|0|0|0|||0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x18|I2C_ISR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADDCODE[6:0]|ADDCODE[6:0]|ADDCODE[6:0]|ADDCODE[6:0]|ADDCODE[6:0]|ADDCODE[6:0]|ADDCODE[6:0]|DIR|BUSY|Res.|ALERT|TIMEOUT|PECERR|OVR|ARLO|BERR|TCR|TC|STOPF|NACKF|ADDR|RXNE|TXIS|TXE|
|0x18|Reset value|||||||||0|0|0|0|0|0|0|0|0||0|0|0|0|0|0|0|0|0|0|0|0|0|1|
|0x1C|I2C_ICR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ALERTCF|TIMOUTCF|PECCF|OVRCF|ARLOCF|BERRCF|Res.|Res.|STOPCF|NACKCF|ADDRCF|Res.|Res.|Res.|
|0x1C|Reset value|||||||||||||||||||0|0|0|0|0|0|||0|0|0||||
|0x20|I2C_PECR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|PEC[7:0]|
|0x20|Reset value|||||||||||||||||||||||||0|0|0|0|0|0|0|0|
|0x24|I2C_RXDR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RXDATA[7:0]|RXDATA[7:0]|RXDATA[7:0]|RXDATA[7:0]|RXDATA[7:0]|RXDATA[7:0]|RXDATA[7:0]|RXDATA[7:0]|
|0x24|Reset value|||||||||||||||||||||||||0|0|0|0|0|0|0|0|
|0x28|I2C_TXDR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|TXDATA[7:0]|TXDATA[7:0]|TXDATA[7:0]|TXDATA[7:0]|TXDATA[7:0]|TXDATA[7:0]|TXDATA[7:0]|TXDATA[7:0]|
|0x28|Reset value|||||||||||||||||||||||||0|0|0|0|0|0|0|0|


Refer to _Section 2.2_ for the register boundary addresses.


RM0490 Rev 5 741/1027



741


