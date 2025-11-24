**RM0490** **Independent watchdog (IWDG)**

# **22 Independent watchdog (IWDG)**

## **22.1 Introduction**


The devices feature an embedded watchdog peripheral (IWDG) that offers a combination of
high safety level, timing accuracy, and flexibility of use. This peripheral detects and solves
malfunctions due to software failure, and triggers a system reset when the counter reaches
a given timeout value.


The independent watchdog is clocked by its own dedicated low-speed clock (LSI), and stays
active even if the main clock fails.


The IWDG is best suited for applications that require the watchdog to run as a totally
independent process outside the main application, but have lower timing accuracy
constraints. For further information on the window watchdog, refer to _Section 23: System_
_window watchdog (WWDG)_ .

## **22.2 IWDG main features**


      - Free-running downcounter


      - Clocked from an independent RC oscillator (can operate in Standby and Stop modes)


      - Conditional reset


–
Reset (if watchdog is activated) when the downcounter value becomes lower than
0x000


–
Reset (if watchdog is activated) if the downcounter is reloaded outside the window

## **22.3 IWDG functional description**


**22.3.1** **IWDG block diagram**


_Figure 218_ shows the functional blocks of the independent watchdog module.


**Figure 218. Independent watchdog block diagram**





















1. The register interface is located in the V DD voltage domain. The watchdog function is located in the V DD
voltage domain, still functional in Stop and Standby modes.


RM0490 Rev 5 631/1027



639


**Independent watchdog (IWDG)** **RM0490**


When the independent watchdog is started by writing the value 0x0000 CCCC in the _IWDG_
_key register (IWDG_KR)_, the counter starts counting down from the reset value of 0xFFF.
When it reaches the end of count value (0x000), a reset signal is generated (IWDG reset).


Whenever the key value 0x0000 AAAA is written in the _IWDG key register (IWDG_KR)_, the
IWDG_RLR value is reloaded in the counter, and the watchdog reset is prevented.


Once running, the IWDG cannot be stopped.


**22.3.2** **Window option**


The IWDG can also work as a window watchdog by setting the appropriate window in the
_IWDG window register (IWDG_WINR)_ .


If the reload operation is performed while the counter is greater than the value stored in the
_IWDG window register (IWDG_WINR)_, a reset is provided.


The default value of the _IWDG window register (IWDG_WINR)_ is 0x0000 0FFF, so if it is not
updated, the window option is disabled.


As soon as the window value is changed, a reload operation is performed to reset the
downcounter to the _IWDG reload register (IWDG_RLR)_ value, and to ease the cycle number
calculation to generate the next reload.


**Configuring the IWDG when the window option is enabled**


1. Enable the IWDG by writing 0x0000 CCCC in the _IWDG key register (IWDG_KR)_ .


2. Enable register access by writing 0x0000 5555 in the _IWDG key register (IWDG_KR)_ .


3. Write the IWDG prescaler by programming _IWDG prescaler register (IWDG_PR)_ from
0 to 7.


4. Write the _IWDG reload register (IWDG_RLR)_ .


5. Wait for the registers to be updated (IWDG_SR = 0x0000 0000).


6. Write to the _IWDG window register (IWDG_WINR)_ . This automatically refreshes the
counter value in the _IWDG reload register (IWDG_RLR)_ .


_Note:_ _Writing the window value allows the counter value to be refreshed by the RLR when the_
_IWDG status register (IWDG_SR) is set to 0x0000 0000._


**Configuring the IWDG when the window option is disabled**


When the window option is not used, the IWDG can be configured as follows:


1. Enable the IWDG by writing 0x0000 CCCC in the _IWDG key register (IWDG_KR)_ .


2. Enable register access by writing 0x0000 5555 in the _IWDG key register (IWDG_KR)_ .


3. Write the prescaler by programming the _IWDG prescaler register (IWDG_PR)_ from 0 to
7.


4. Write the _IWDG reload register (IWDG_RLR)_ .


5. Wait for the registers to be updated (IWDG_SR = 0x0000 0000).


6. Refresh the counter value with IWDG_RLR (IWDG_KR = 0x0000 AAAA).


632/1027 RM0490 Rev 5


**RM0490** **Independent watchdog (IWDG)**


**22.3.3** **Hardware watchdog**


If this feature is enabled through the device option bits, the watchdog is automatically
enabled at power-on, and generates a reset unless the _IWDG key register (IWDG_KR)_ is
written by the software before the counter reaches the end of count, and if the downcounter
is lower than the window value (WIN[11:0]).


**22.3.4** **Register access protection**


Write access to _IWDG prescaler register (IWDG_PR)_, _IWDG reload register (IWDG_RLR)_,
and _IWDG window register (IWDG_WINR)_ is protected. To modify them, first write the code
0x0000 5555 in the _IWDG key register (IWDG_KR)_ . A write access to this register with a
different value breaks the sequence, and register access is protected again. This is the case
of the reload operation (writing 0x0000 AAAA).


A status register is available to indicate that an update of the prescaler, or of the
downcounter reload value, or of the window value, is ongoing.


**22.3.5** **Debug mode**


When the device enters Debug mode (core halted), the IWDG counter either continues to
work normally or stops, depending on the configuration of the corresponding bit in
DBGMCU freeze register.


RM0490 Rev 5 633/1027



639


**Independent watchdog (IWDG)** **RM0490**

## **22.4 IWDG registers**


Refer to _Section 1.2 on page 41_ for a list of abbreviations used in register descriptions.


The peripheral registers can be accessed by half-words (16-bit) or words (32-bit).


**22.4.1** **IWDG key register (IWDG_KR)**


Address offset: 0x00


Reset value: 0x0000 0000 (reset by Standby mode)

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|
|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **KEY[15:0]:** Key value (write only, read 0x0000)

These bits must be written by software at regular intervals with the key value 0xAAAA,
otherwise the watchdog generates a reset when the counter reaches 0.
Writing the key value 0x5555 to enable access to the IWDG_PR, IWDG_RLR and
IWDG_WINR registers (see _Section 22.3.4: Register access protection_ )
Writing the key value 0xCCCC starts the watchdog (except if the hardware watchdog option
is selected)


634/1027 RM0490 Rev 5


**RM0490** **Independent watchdog (IWDG)**


**22.4.2** **IWDG prescaler register (IWDG_PR)**


Address offset: 0x04


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PR[2:0]|PR[2:0]|PR[2:0]|
||||||||||||||rw|rw|rw|



Bits 31:3 Reserved, must be kept at reset value.


Bits 2:0 **PR[2:0]:** Prescaler divider

These bits are write access protected see _Section 22.3.4: Register access protection_ . They
are written by software to select the prescaler divider feeding the counter clock. PVU bit of
the _IWDG status register (IWDG_SR)_ must be reset in order to be able to change the
prescaler divider.

000: divider /4

001: divider /8

010: divider /16

011: divider /32

100: divider /64

101: divider /128

110: divider /256

111: divider /256

_Note: Reading this register returns the prescaler value from the V_ _DD_ _voltage domain. This_
_value may not be up to date/valid if a write operation to this register is ongoing. For this_
_reason the value read from this register is valid only when the PVU bit in the IWDG_
_status register (IWDG_SR) is reset._


RM0490 Rev 5 635/1027



639


**Independent watchdog (IWDG)** **RM0490**


**22.4.3** **IWDG reload register (IWDG_RLR)**


Address offset: 0x08


Reset value: 0x0000 0FFF (reset by Standby mode)

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11 10 9 8 7 6 5 4 3 2 1 0|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|
|||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:12 Reserved, must be kept at reset value.


Bits 11:0 **RL[11:0]:** Watchdog counter reload value

These bits are write access protected see _Register access protection_ . They are written by
software to define the value to be loaded in the watchdog counter each time the value
0xAAAA is written in the _IWDG key register (IWDG_KR)_ . The watchdog counter counts
down from this value. The timeout period is a function of this value and the clock prescaler.
Refer to the datasheet for the timeout information.

The RVU bit in the _IWDG status register (IWDG_SR)_ must be reset to be able to change the
reload value.

_Note: Reading this register returns the reload value from the V_ _DD_ _voltage domain. This value_
_may not be up to date/valid if a write operation to this register is ongoing on it. For this_
_reason the value read from this register is valid only when the RVU bit in the IWDG_
_status register (IWDG_SR) is reset._


636/1027 RM0490 Rev 5


**RM0490** **Independent watchdog (IWDG)**


**22.4.4** **IWDG status register (IWDG_SR)**


Address offset: 0x0C


Reset value: 0x0000 0000 (not reset by Standby mode)

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|WVU|RVU|PVU|
||||||||||||||r|r|r|



Bits 31:3 Reserved, must be kept at reset value.


Bit 2 **WVU:** Watchdog counter window value update

This bit is set by hardware to indicate that an update of the window value is ongoing. It is
reset by hardware when the reload value update operation is completed in the V DD voltage
domain (takes up to five prescaled clock cycles).
Window value can be updated only when WVU bit is reset.


Bit 1 **RVU:** Watchdog counter reload value update

This bit is set by hardware to indicate that an update of the reload value is ongoing. It is reset
by hardware when the reload value update operation is completed in the V DD voltage domain
(takes up to five prescaled clock cycles).
Reload value can be updated only when RVU bit is reset.


Bit 0 **PVU:** Watchdog prescaler value update

This bit is set by hardware to indicate that an update of the prescaler value is ongoing. It is
reset by hardware when the prescaler update operation is completed in the V DD voltage
domain (takes up to five LSI clock cycles).
Prescaler value can be updated only when PVU bit is reset.


_Note:_ _If several reload, prescaler, or window values are used by the application, it is mandatory to_
_wait until RVU bit is reset before changing the reload value, to wait until PVU bit is reset_
_before changing the prescaler value, and to wait until WVU bit is reset before changing the_
_window value. However, after updating the prescaler and/or the reload/window value it is not_
_necessary to wait until RVU or PVU or WVU is reset before continuing code execution_
_except in case of low-power mode entry._


RM0490 Rev 5 637/1027



639


**Independent watchdog (IWDG)** **RM0490**


**22.4.5** **IWDG window register (IWDG_WINR)**


Address offset: 0x10


Reset value: 0x0000 0FFF (reset by Standby mode)

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11 10 9 8 7 6 5 4 3 2 1 0|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|
|||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:12 Reserved, must be kept at reset value.


Bits 11:0 **WIN[11:0]:** Watchdog counter window value

These bits are write access protected, see _Section 22.3.4_, they contain the high limit of the
window value to be compared with the downcounter.
To prevent a reset, the downcounter must be reloaded when its value is lower than the
window register value and greater than 0x0
The WVU bit in the _IWDG status register (IWDG_SR)_ must be reset in order to be able to
change the reload value.

_Note: Reading this register returns the reload value from the V_ _DD_ _voltage domain. This value_
_may not be valid if a write operation to this register is ongoing. For this reason the value_
_read from this register is valid only when the WVU bit in the IWDG status register_
_(IWDG_SR) is reset._


638/1027 RM0490 Rev 5


**RM0490** **Independent watchdog (IWDG)**


**22.4.6** **IWDG register map**


The following table gives the IWDG register map and reset values.


**Table 95. IWDG register map and reset values**

























|Offset|Register<br>name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**IWDG_KR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|KEY[15:0]|
|0x00|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x04|**IWDG_PR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PR[2:0]|PR[2:0]|PR[2:0]|
|0x04|Reset value||||||||||||||||||||||||||||||0|0|0|
|0x08|**IWDG_RLR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|RL[11:0]|
|0x08|Reset value|||||||||||||||||||||1|1|1|1|1|1|1|1|1|1|1|1|
|0x0C|**IWDG_SR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|WVU|RVU|PVU|
|0x0C|Reset value||||||||||||||||||||||||||||||0|0|0|
|0x10|**IWDG_WINR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|WIN[11:0]|
|0x10|Reset value|||||||||||||||||||||1|1|1|1|1|1|1|1|1|1|1|1|


Refer to _Section 2.2 on page 45_ for the register boundary addresses.


RM0490 Rev 5 639/1027



639


