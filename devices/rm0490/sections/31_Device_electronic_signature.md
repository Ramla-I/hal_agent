**RM0490** **Device electronic signature**

# **31 Device electronic signature**


The device electronic signature is stored in the system memory area of the flash memory
module, and can be read using the debug inter face or by the CPU. It contains factoryprogrammed identification and calibration data that allow the user firmware or other external
devices to automatically match to the characteristics of the STM32C0 series microcontroller.

## **31.1 Unique device ID register (96 bits) (UID)**


Base address: 0x1FFF 7550


Address offset: 0x00


Reset value: 0xXXXX XXXX (where X is factory-programmed)


The unique device identifier is ideally suited:


      - for use as serial numbers (for example USB string serial numbers or other end
applications)


      - for use as part of the security keys in order to increase the security of code in flash
memory while using and combining this unique ID with software cryptographic
primitives and protocols before programming the internal flash memory


      - to activate secure boot processes, and so on.


The 96-bit unique device identifier provides a reference number which is unique for any
device and in any context. These bits cannot be altered by the user.

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|UID[31:16]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|UID[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:0 **UID[31:0]:** X and Y coordinates on the wafer expressed in BCD format


Address offset: 0x04


Reset value: 0xXXXX XXXX where X is factory-programmed

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



RM0490 Rev 5 1015/1027



1017


**Device electronic signature** **RM0490**


Bits 31:8 **UID[63:40]:** LOT_NUM[23:0]

Lot number (ASCII encoded)


Bits 7:0 **UID[39:32]:** WAF_NUM[7:0]

Wafer number (8-bit unsigned number)


Address offset: 0x08


Reset value: 0xXXXX XXXX where X is factory-programmed

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|UID[95:80]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|UID[79:64]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:0 **UID[95:64]:** LOT_NUM[55:24]

Lot number (ASCII encoded)

## **31.2 Flash memory size data register (FSIZER)**


Base address: 0x1FFF 75A0


Address offset: 0x00


Reset value: 0xXXXX where X is factory-programmed

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 15:0 **FLASH_SIZE[15:0]** : Flash memory size

This bitfield indicates the size of the device flash memory expressed in Kbytes.

As an example, 0x040 corresponds to 64 Kbytes.

## **31.3 Package data register (PCKR)**


Base address: 0x1FFF 7500


Address offset: 0x00


Reset value: 0xXXXX where X is factory-programmed

|15|14|13|12|11|10|9|8|7|6|5|4|3 2 1 0|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|PKG[3:0]|PKG[3:0]|PKG[3:0]|PKG[3:0]|
|||||||||||||r|r|r|r|



1016/1027 RM0490 Rev 5


**RM0490** **Device electronic signature**


Bits 15:4 Reserved


Bits 3:0 **PKG[3:0]:** Package type

**Condition: STM32C011xx**

0001: SO8

0010: WLCSP12

0011: UFQFPN20

0100: TSSOP20

Other: Reserved

**Condition: STM32C031xx**

0010: TSSOP20

0011: UFQFPN28

0100: UFQFPN32 / LQFP32

0101: UFQFPN48 / LQFP48

Other: Reserved

**Condition: STM32C051xx**

0001: WLCSP15

0010: TSSOP20

0011: UFQFPN28

0100: UFQFPN32 / LQFP32

0101: UFQFPN48 / LQFP48

Other: Reserved

**Condition: STM32C071xx**

0001: WLCSP19_GP
0010: WLCSP19_N
0011: TSSOP20_GP
0100: TSSOP20_N
0101: UFQFPN28_GP
0110: UFQFPN28_N
0111: UFQFPN32_GP / LQFP32_GP
1000: UFQFPN32_N / LQFP32_N
1001: UFQFPN48_GP / LQFP48_GP
1010: UFQFPN48_N / LQFP48_N
1011: LQFP64_GP
1000: LQFP64_N
1101: UFBGA64_GP
1110: UFBGA64_N

Other: Reserved

**Condition: STM32C091xx/92xx**

0001: TSSOP20

0010: WLCSP24

0011: UFQFPN28

0100: UFQFPN32 / LQFP32

0101: UFQFPN48 / LQFP48

0110: UFBGA64 / LQFP64

Other: Reserved


RM0490 Rev 5 1017/1027



1017


