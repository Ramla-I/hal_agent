**Backup registers (BKP)** **RM0041**

# **5 Backup registers (BKP)**


**Low-density** **value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 16 and 32 Kbytes.


**Medium-density** **value line** **devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 64 and 128 Kbytes.


**High-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 256 and 512 Kbytes.


This section applies to the whole STM32F100xx family, unless otherwise specified.

## **5.1 BKP introduction**


The backup registers are ten 16-bit registers in low and medium density devices, 42
registers in high-density devices for storing 20 or 84 bytes of user application data.


They are implemented in the backup domain that remains powered on by V BAT when the
V DD power is switched off. They are not reset when the device wakes up from Standby
mode or by a system reset or power reset.


In addition, the BKP control registers are used to manage the Tamper detection feature and
RTC calibration.


After reset, access to the Backup registers and RTC is disabled and the Backup domain
(BKP) is protected against possible parasitic write access. To enable access to the Backup
registers and the RTC, proceed as follows:


      - enable the power and backup interface clocks by setting the PWREN and BKPEN bits
in the RCC_APB1ENR register


      - set the DBP bit in the Power control register (PWR_CR) to enable access to the
Backup registers and RTC.

## **5.2 BKP main features**


      - 20-byte data registers (in low and medium-density devices) or 40-byte data registers (in
high-density devices)


      - Status/control register for managing tamper detection with interrupt capability


      - Calibration register for storing the RTC calibration value


      - Possibility to output the RTC Calibration Clock, RTC Alarm pulse or Second pulse on
TAMPER pin PC13 (when this pin is not used for tamper detection)


64/709 RM0041 Rev 6


**RM0041** **Backup registers (BKP)**

## **5.3 BKP functional description**


**5.3.1** **Tamper detection**


The TAMPER pin generates a Tamper detection event when the pin changes from 0 to 1 or
from 1 to 0 depending on the TPAL bit in the _Backup control register (BKP_CR)_ . A tamper
detection event resets all data backup registers.


However to avoid losing Tamper events, the signal used for edge detection is logically
ANDed with the Tamper enable in order to detect a Tamper event in case it occurs before
the TAMPER pin is enabled.


      - **When TPAL=0:** If the TAMPER pin is already high before it is enabled (by setting TPE
bit), an extra Tamper event is detected as soon as the TAMPER pin is enabled (while
there was no rising edge on the TAMPER pin after TPE was set)


      - **When TPAL=1:** If the TAMPER pin is already low before it is enabled (by setting the
TPE bit), an extra Tamper event is detected as soon as the TAMPER pin is enabled
(while there was no falling edge on the TAMPER pin after TPE was set)


By setting the TPIE bit in the BKP_CSR register, an interrupt is generated when a Tamper
detection event occurs.


After a Tamper event has been detected and cleared, the TAMPER pin should be disabled
and then re-enabled with TPE before writing to the backup data registers (BKP_DRx) again.
This prevents software from writing to the backup data registers (BKP_DRx), while the
TAMPER pin value still indicates a Tamper detection. This is equivalent to a level detection
on the TAMPER pin.


_Note:_ _Tamper detection is still active when V_ _DD_ _power is switched off. To avoid unwanted resetting_
_of the data backup registers, the TAMPER pin should be externally tied to the correct level._


**5.3.2** **RTC calibration**


For measurement purposes, the RTC clock with a frequency divided by 64 can be output on
the TAMPER pin. This is enabled by setting the CCO bit in the _RTC clock calibration register_
_(BKP_RTCCR)_ .


The clock can be slowed down by up to 121 ppm by configuring CAL[6:0] bits.


For more details about RTC calibration and how to use it to improve timekeeping accuracy,
refer to AN2604 " _STM32F101xx and STM32F103xx RTC calibration_ ”.


RM0041 Rev 6 65/709



70


**Backup registers (BKP)** **RM0041**

## **5.4 BKP registers**


Refer to _Section 1.1 on page 32_ for a list of abbreviations used in register descriptions.


The peripheral registers can be accessed by half-words (16-bit) or words (32-bit).


**5.4.1** **Backup data register x (BKP_DRx) (x = 1 ..20)**


Address offset: 0x04 to 0x28, 0x40 to 0x64


Reset value: 0x0000 0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|D[15:0]|D[15:0]|D[15:0]|D[15:0]|D[15:0]|D[15:0]|D[15:0]|D[15:0]|D[15:0]|D[15:0]|D[15:0]|D[15:0]|D[15:0]|D[15:0]|D[15:0]|D[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **D[15:0]** Backup data

These bits can be written with user data.

_Note: The BKP_DRx registers are not reset by a System reset or Power reset or when the_
_device wakes up from Standby mode. They are reset by a Backup Domain reset or by a_
_TAMPER pin event (if the TAMPER pin function is activated)._


**5.4.2** **RTC clock calibration register (BKP_RTCCR)**


Address offset: 0x2C


Reset value: 0x0000 0000

|15 14 13 12 11 10|9|8|7|6 5 4 3 2 1 0|Col6|Col7|Col8|Col9|Col10|Col11|
|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|ASOS|ASOE|CCO|CAL[6:0]|CAL[6:0]|CAL[6:0]|CAL[6:0]|CAL[6:0]|CAL[6:0]|CAL[6:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:10 Reserved, must be kept at reset value.


Bit 9 **ASOS:** Alarm or second output selection

When the ASOE bit is set, the ASOS bit can be used to select whether the signal output on
the TAMPER pin is the RTC Second pulse signal or the Alarm pulse signal:
0: RTC Alarm pulse output selected
1: RTC Second pulse output selected

_Note: This bit is reset only by a Backup domain reset._


66/709 RM0041 Rev 6


**RM0041** **Backup registers (BKP)**


Bit 8 **ASOE:** Alarm or second output enable

Setting this bit outputs either the RTC Alarm pulse signal or the Second pulse signal on the
TAMPER pin depending on the ASOS bit.
The output pulse duration is one RTC clock period. The TAMPER pin must not be enabled
while the ASOE bit is set.

_Note: This bit is reset only by a Backup domain reset._


Bit 7 **CCO:** Calibration clock output

0: No effect

1: Setting this bit outputs the RTC clock with a frequency divided by 64 on the TAMPER pin.
The TAMPER pin must not be enabled while the CCO bit is set in order to avoid unwanted
Tamper detection.

_Note: This bit is reset when the V_ _DD_ _supply is powered off._


Bit 6:0 **CAL[6:0]:** Calibration value

This value indicates the number of clock pulses that will be ignored every 2^20 clock pulses.
This allows the calibration of the RTC, slowing down the clock by steps of 1000000/2^20
PPM.

The clock of the RTC can be slowed down from 0 to 121PPM.


**5.4.3** **Backup control register (BKP_CR)**


Address offset: 0x30


Reset value: 0x0000 0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2|1|0|
|---|---|---|
|Reserved|TPAL|TPE|
|Reserved|rw|rw|



Bits 15:2 Reserved, must be kept at reset value.


Bit 1 **TPAL:** TAMPER pin active level

0: A high level on the TAMPER pin resets all data backup registers (if TPE bit is set).
1: A low level on the TAMPER pin resets all data backup registers (if TPE bit is set).


Bit 0 **TPE:** TAMPER pin enable

0: The TAMPER pin is free for general purpose I/O
1: Tamper alternate I/O function is activated.


_Note:_ _Setting the TPAL and TPE bits at the same time is always safe, however resetting both at_
_the same time can generate a spurious Tamper event. For this reason it is recommended to_
_change the TPAL bit only when the TPE bit is reset._


**5.4.4** **Backup control/status register (BKP_CSR)**


Address offset: 0x34


Reset value: 0x0000 0000

|15 14 13 12 11 10|9|8|7 6 5 4 3|2|1|0|
|---|---|---|---|---|---|---|
|Reserved|TIF|TEF|Reserved|TPIE|CTI|CTE|
|Reserved|r|r|r|rw|w|w|



RM0041 Rev 6 67/709



70


**Backup registers (BKP)** **RM0041**


Bits 15:10 Reserved, must be kept at reset value.


Bit 9 **TIF:** Tamper interrupt flag

This bit is set by hardware when a Tamper event is detected and the TPIE bit is set. It is
cleared by writing 1 to the CTI bit (also clears the interrupt). It is also cleared if the TPIE bit is
reset.

0: No Tamper interrupt
1: A Tamper interrupt occurred

_Note: This bit is reset only by a system reset and wakeup from Standby mode._


Bit 8 **TEF:** Tamper event flag

This bit is set by hardware when a Tamper event is detected. It is cleared by writing 1 to the
CTE bit.

0: No Tamper event
1: A Tamper event occurred

_Note: A_ _Tamper event resets all the BKP_DRx registers. They are held in reset as long as the_
_TEF bit is set. If a write to the BKP_DRx registers is performed while this bit is set, the_
_value will not be stored._


Bits 7:3 Reserved, must be kept at reset value.


Bit 2 **TPIE:** TAMPER pin interrupt enable

0: Tamper interrupt disabled
1: Tamper interrupt enabled (the TPE bit must also be set in the BKP_CR register

_Note: A Tamper interrupt does not wake up the core from low-power modes._

_This bit is reset only by a system reset and wakeup from Standby mode._


Bit 1 **CTI:** Clear tamper interrupt

This bit is write only, and is always read as 0.

0: No effect

1: Clear the Tamper interrupt and the TIF Tamper interrupt flag.


Bit 0 **CTE:** Clear tamper event

This bit is write only, and is always read as 0.

0: No effect

1: Reset the TEF Tamper event flag (and the Tamper detector)


68/709 RM0041 Rev 6


**RM0041** **Backup registers (BKP)**


**5.4.5** **BKP register map**


BKP registers are mapped as 16-bit addressable registers as described in the table below:


**Table 14. BKP register map and reset values**













|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x04|BKP_DR1<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x04|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x08|BKP_DR2<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x08|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x0C|BKP_DR3<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x0C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x10|BKP_DR4<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x10|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x14|BKP_DR5<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x14|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x18|BKP_DR6<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x18|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x1C|BKP_DR7<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x1C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x20|BKP_DR8<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x20|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x24|BKP_DR9<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x24|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x28|BKP_DR10<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x28|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x2C|BKP_RTCCR<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|ASOS<br><br>|ASOE<br><br>|CCO<br>|CAL[6:0]<br><br><br><br><br><br><br>|CAL[6:0]<br><br><br><br><br><br><br>|CAL[6:0]<br><br><br><br><br><br><br>|CAL[6:0]<br><br><br><br><br><br><br>|CAL[6:0]<br><br><br><br><br><br><br>|CAL[6:0]<br><br><br><br><br><br><br>|CAL[6:0]<br><br><br><br><br><br><br>|
|0x2C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x30|BKP_CR<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|TPAL<br><br>|TPE<br>|
|0x30|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|
|0x34|BKP_CSR<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|TIF<br><br>|TEF<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|TPIE<br><br>|CTI<br><br>|CTE<br>|
|0x34|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|


RM0041 Rev 6 69/709



70


**Backup registers (BKP)** **RM0041**


**Table 14. BKP register map and reset values (continued)**





|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x38 to<br>0x3C|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x40|BKP_DR11<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x40|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x44|BKP_DR12<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x44|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x48|BKP_DR13<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x48|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x4C|BKP_DR14<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x4C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x50|BKP_DR15<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x50|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x54|BKP_DR16<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x54|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x58|BKP_DR17<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x58|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x5C|BKP_DR18<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x5C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x60|BKP_DR19<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x60|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x64|BKP_DR20<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|D[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x64|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|


Refer to _Table 1 on page 37_ and _Table 2 on page 38_ for the register boundary addresses.


70/709 RM0041 Rev 6


