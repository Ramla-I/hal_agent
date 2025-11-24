**Device electronic signature** **RM0360**

# **27 Device electronic signature**


The device electronic signature is stored in the System memory area of the Flash memory
module, and can be read using the debug interface or by the CPU. It contains factoryprogrammed identification and calibration data that allow the user firmware or other external
devices to automatically match to the characteristics of the STM32F0x0 microcontroller.

## **27.1 Flash memory size data register**


Base address: 0x1FFF


Address offset: 0x00


Read only = 0xXXXX where X is factory-programmed

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|FLASH_SIZE|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 15:0 **FLASH_SIZE[15:0]** : Flash memory size

This bitfield indicates the size of the device Flash memory expressed in Kbytes.

As an example, 0x040 corresponds to 64 Kbytes.


720/775 RM0360 Rev 5


