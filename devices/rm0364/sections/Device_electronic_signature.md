**RM0364** **Device electronic signature**

# **32 Device electronic signature**


The device electronic signature is stored in the System memory area of the Flash memory
module, and can be read using the debug interface or by the CPU. It contains factoryprogrammed identification and calibration data that allow the user firmware or other external
devices to automatically match to the characteristics of the STM32F334xx microcontroller.

## **32.1 Unique device ID register (96 bits)**


The unique device identifier is ideally suited:


      - for use as serial numbers (for example USB string serial numbers or other end
applications)


      - for use as part of the security keys in order to increase the security of code in Flash
memory while using and combining this unique ID with software cryptographic
primitives and protocols before programming the internal Flash memory


      - to activate secure boot processes, etc.


The 96-bit unique device identifier provides a reference number which is unique for any
device and in any context. These bits cannot be altered by the user.


Base address: 0x1FFF F7AC


Address offset: 0x00


Read only = 0xXXXX XXXX where X is factory-programmed

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


Read only = 0xXXXX XXXX where X is factory-programmed

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|UID[63:48]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|UID[47:32]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



RM0364 Rev 4 1117/1124



1118


**Device electronic signature** **RM0364**


Bits 31:8 **UID[63:40]:** LOT_NUM[23:0]

Lot number (ASCII encoded)


Bits 7:0 **UID[39:32]:** WAF_NUM[7:0]

Wafer number (8-bit unsigned number)


Address offset: 0x08


Read only = 0xXXXX XXXX where X is factory-programmed

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

## **32.2 Flash memory size data register**


Base address: 0x1FFF F7CC


Address offset: 0x00


Read only = 0xXXXX where X is factory-programmed

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 15:0 **FLASH_SIZE[15:0]** : Flash memory size

This bitfield indicates the size of the device Flash memory expressed in Kbytes.

As an example, 0x040 corresponds to 64 Kbytes.


1118/1124 RM0364 Rev 4


