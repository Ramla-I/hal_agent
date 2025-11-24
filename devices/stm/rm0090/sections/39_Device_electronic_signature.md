**RM0090** **Device electronic signature**

# **39 Device electronic signature**


The electronic signature is stored in the Flash memory area. It can be read using the
JTAG/SWD or the CPU. It contains factory-programmed identification data that allow the
user firmware or other external devices to automatically match its interface to the
characteristics of the STM32F4xx microcontrollers.

## **39.1 Unique device ID register (96 bits)**


The unique device identifier is ideally suited:


      - for use as serial numbers (for example USB string serial numbers or other end
applications)


      - for use as security keys in order to increase the security of code in Flash memory while
using and combining this unique ID with software cryptographic primitives and
protocols before programming the internal Flash memory


      - to activate secure boot processes, etc.


The 96-bit unique device identifier provides a reference number which is unique for any
device and in any context. These bits can never be altered by the user.


The 96-bit unique device identifier can also be read in single bytes/half-words/words in
different ways and then be concatenated using a custom algorithm.


**Base address: 0x1FFF 7A10**


Address offset: 0x00


Read only = 0xXXXX XXXX where X is factory-programmed

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|Col17|Col18|Col19|Col20|Col21|Col22|Col23|Col24|Col25|Col26|Col27|Col28|Col29|Col30|Col31|Col32|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|UID(31:0)|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:0 **UID** **(31:0):** X and Y coordinates on the wafer


Address offset: 0x04


Read only = 0xXXXX XXXX where X is factory-programmed

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|UID(63:48)|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|UID(47:32)|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



RM0090 Rev 21 1717/1757



1718


**Device electronic signature** **RM0090**


Bits 31:8 **UID(63:40):** LOT_NUM[23:0]

Lot number (ASCII encoded).


Bits 7:0 **UID(39:32):** WAF_NUM[7:0]

Wafer number (ASCII encoded).


Address offset: 0x08


Read only = 0xXXXX XXXX where X is factory-programmed

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|UID(95:80)|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|UID(79:64)|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:0 **UID(95:64):** LOT_NUM[55:24]

Lot number (ASCII encoded).

## **39.2 Flash size**


Base address: 0x1FFF 7A22


Address offset: 0x00


Read only = 0xXXXX where X is factory-programmed

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|F_SIZE|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 15:0 F_ID(15:0): Flash memory size

This bitfield indicates the size of the device Flash memory expressed in Kbytes.
As an example, 0x0400 corresponds to 1024 Kbytes.


1718/1757 RM0090 Rev 21


