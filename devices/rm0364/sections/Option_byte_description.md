**RM0364** **Option byte description**

# **4 Option byte description**


There are six option bytes. They are configured by the end user depending on the
application requirements. As a configuration example, the watchdog may be selected in
hardware or software mode.


A 32-bit word is split up as follows in the option bytes.


**Table 9. Option byte format**

|31-24|23-16|15 -8|7-0|
|---|---|---|---|
|Complemented option<br>byte1|Option byte 1|Complemented option<br>byte0|Option byte 0|



The organization of these bytes inside the information block is as shown in _Table 10_ .


The option bytes can be read from the memory locations listed in _Table 10_ or from the
Option byte register (FLASH_OBR).


_Note:_ _The new programmed option bytes (user, read/write protection) are loaded after a system_
_reset._


**Table 10. Option byte organization**

|Address|[31:24]|[23:16]|[15:8]|[7:0]|
|---|---|---|---|---|
|0x1FFF F800|nUSER|USER|nRDP|RDP|
|0x1FFF F804|nData1|Data1|nData0|Data0|
|0x1FFF F808|nWRP1|WRP1|nWRP0|WRP0|



RM0364 Rev 4 73/1124



75


**Option byte description** **RM0364**






|Col1|Table 11. Description of the option bytes|
|---|---|
|**Flash memory**<br>**address**|**Option bytes**|
|0x1FFF F800|Bits [31:24]:**nUSER**<br>Bits [23:16]:**USER:**User option byte (stored in FLASH_OBR[15:8])<br>This byte is used to configure the following features:<br>- Select the watchdog event: Hardware or software<br>- Reset event when entering Stop mode<br>- Reset event when entering Standby mode<br>Bit 23: Reserved<br>Bit 22:**SRAM_PE**<br>The SRAM hardware parity check is disabled by default. This bit allows the user to<br>enable the SRAM hardware parity check.<br>0: Parity check enabled.<br>1: Parity check disabled.<br>Bit 21:**VDDA_MONITOR**<br>This bit selects the analog monitoring on the VDDA power source:<br>0: VDDA power supply supervisor disabled.<br>1: VDDA power supply supervisor enabled.<br>Bit 20:**nBOOT1** <br>Together with the BOOT0 pin, this bit selects Boot mode from the main Flash<br>memory, SRAM or System memory. Refer to_Section 2.5 on page 52_.<br>Bit 19: Reserved, must be kept at reset.<br>Bit 18:**nRST_STDBY**<br>0: Reset generated when entering Standby mode.<br>1: No reset generated.<br>Bit 17:** nRST_STOP**<br>0: Reset generated when entering Stop mode<br>1: No reset generated<br>Bit 16:**WDG_SW**<br>0: Hardware watchdog<br>1: Software watchdog<br>Bits [15:8]:**nRDP**<br>Bits [7:0]:**RDP:** Read protection option byte<br>The value of this byte defines the Flash memory protection level<br>0xAA: Level 0<br>0xXX (except 0xAA and 0xCC): Level 1<br>0xCC: Level 2<br>The protection levels are stored in the Flash_OBR Flash option bytes register<br>(RDPRT bits).|



74/1124 RM0364 Rev 4


**RM0364** **Option byte description**






|Col1|Table 11. Description of the option bytes (continued)|
|---|---|
|**Flash memory**<br>**address**|**Option bytes**|
|0x1FFF F804|**Datax**: Two bytes for user data storage.<br>These addresses can be programmed using the option byte programming<br>procedure.<br>Bits [31:24]:**nData1**<br>Bits [23:16]:**Data1** (stored in FLASH_OBR[31:24])<br>Bits [15:8]:**nData0**<br>Bits [7:0]:**Data0** (stored in FLASH_OBR[23:16])|
|0x1FFF F808|**WRPx**: Flash memory write protection option bytes<br>Bits [31:24]:**nWRP1**<br>Bits [23:16]:**WRP1** (stored in FLASH_WRPR[15:8])<br>Bits [15:8]:**nWRP0**<br>Bits [7:0]:**WRP0** (stored in FLASH_WRPR[7:0])<br>0: Write protection active<br>1: Write protection not active<br>Refer to_Section 3.3.2: Write protection_ for more details.<br>In total, 2 user option bytes are used to protect the whole main Flash memory.<br>WRP0: Write-protects pages 0 to 15<br>WRP1: Write-protects pages 16 to 31<br>_Note: Even if WRP2 and WRP3 are not available, they must be kept at reset_<br>_value._|



On every system reset, the option byte loader (OBL) reads the information block and stores
the data into the Option byte register (FLASH_OBR) and the Write protection register
(FLASH_WRPR). Each option byte also has its complement in the information block. During
option loading, by verifying the option bit and its complement, it is possible to check that the
loading has correctly taken place. If this is not the case, an option byte error (OPTERR) is
generated. When a comparison error occurs, the corresponding option byte is forced to
0xFF. The comparator is disabled when the option byte and its complement are both equal
to 0xFF (Electrical Erase state).


RM0364 Rev 4 75/1124



75


