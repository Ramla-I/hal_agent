**RM0041** **Device electronic signature**

# **26 Device electronic signature**


**Low-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 16 and 32 Kbytes.


**Medium-density** **value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 64 and 128 Kbytes.


**High-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 256 and 512 Kbytes.


This section applies to all STM32F100xx devices, unless otherwise specified.


The electronic signature is stored in the System memory area in the flash memory module,
and can be read using the JTAG/SWD or the CPU. It contains factory-programmed
identification data that allow the user firmware or other external devices to automatically
match its interface to the characteristics of the STM32F100xx microcontroller.

## **26.1 Memory size registers**


**26.1.1** **Flash size register**


Base address: 0x1FFF F7E0


Read only = 0xXXXX where X is factory-programmed

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 15:0 **F_SIZE:** Flash memory size

This field value indicates the flash memory size of the device in Kbytes.
Example: 0x0080 = 128 Kbytes.


RM0041 Rev 6 699/709



701


**Device electronic signature** **RM0041**

## **26.2 Unique device ID register (96 bits)**


The unique device identifier is ideally suited:


      - for use as serial numbers


      - for use as security keys, to increase the security of code in flash memory while using
and combining this unique ID with software cryptographic primitives and protocols,
before programming the internal flash memory


      - to activate secure boot processes


The 96-bit unique device identifier provides a reference number, unique for any device and
in any context. These bits cannot be altered by the user.


The 96-bit unique device identifier can also be read in single bytes/half-words/words in
different ways and then be concatenated using a custom algorithm.


**Base address: 0x1FFF F7E8**


Address offset: 0x00


Read only = 0xXXXX where X is factory-programmed

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|U_ID(15:0)|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 15:0 **U_ID(15:0):** 15:0 unique ID bits


Address offset: 0x02


Read only = 0xXXXX where X is factory-programmed

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|U_ID(31:16)|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 15:0 **U_ID(31:16):** 31:16 unique ID bits

This field value is also reserved for a future feature.


Address offset: 0x04


Read only = 0xXXXX XXXX where X is factory-programmed

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|U_ID(63:48)|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|U_ID(47:32)|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:0 **U_ID(63:32):** 63:32 unique ID bits


700/709 RM0041 Rev 6


**RM0041** **Device electronic signature**


Address offset: 0x08


Read only = 0xXXXX XXXX where X is factory-programmed

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|U_ID(95:80)|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|U_ID(79:64)|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:0 **U_ID(95:64):** 95:64 unique ID bits.


RM0041 Rev 6 701/709



701


