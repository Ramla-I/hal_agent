**RM0490** **Boot modes**

# **3 Boot modes**

## **3.1 Boot configuration**


The user can select the boot area through the boot configuration pin BOOT0 and bits
nBOOT1, nBOOT_SEL, and nBOOT0 of the User option byte, as shown in the following
table.

|Table 9. Boot modes|Col2|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
|**Boot mode configuration**|**Boot mode configuration**|**Boot mode configuration**|**Boot mode configuration**|**Boot mode configuration**|**Selected boot area**|
|**BOOT_**<br>**LOCK**|**nBOOT1 bit**|**BOOT0 pin**|**nBOOT_SEL**<br>**bit**|**nBOOT0 bit**|**nBOOT0 bit**|
|0|x|0|0|x|Main flash memory(1)|
|0|1|1|0|x|System memory|
|0|0|1|0|x|Embedded SRAM|
|0|x|x|1|1|Main flash memory(1)|
|0|1|x|1|0|System memory|
|0|0|x|1|0|Embedded SRAM|
|1|x|x|x|x|Main flash memory|



1. Boot forced to system memory when EMPTY flag in the FLASH access control register (FLASH_ACR) is
set. See _Section 3.1.4: Empty check_ .


The boot mode configuration is latched after a reset. It is up to the user to set boot mode
configuration related to the required boot mode. The boot mode configuration is also resampled when exiting Standby mode. Consequently, they must be kept in the required boot
mode configuration in Standby mode. After this startup delay has elapsed, the CPU fetches
the top-of-stack value from the address 0x0000 0000, then starts executing code from the
address stored in the boot memory at 0x0000 0004.


Depending on the selected boot mode, main flash memory, system memory, or SRAM is
accessible as follows:


      - Boot from main flash memory: the main flash memory is aliased in the boot memory
space (0x0000 0000), but still accessible from its original memory space
(0x0800 0000). In other words, the flash memory contents can be accessed starting
from address 0x0000 0000 or 0x0800 0000.


      - Boot from system memory: the system memory is aliased in the boot memory space
(0x0000 0000), but still accessible from its original memory space 0x1FFF0000.


      - Boot from the embedded SRAM: the SRAM is aliased in the boot memory space
(0x0000 0000), but it is still accessible from its original memory space (0x2000 0000).


**Caution:** BOOT0 pin shares the same GPIO with serial wire clock (SWCLK) that is used by the
debugger to connect with the device, based on the fact that these functionalities can be
considered almost completely disjoint. Nevertheless, to ensure system robustness, the
STM32C0 series devices provide a hardware mechanism to force BOOT0 low (boot from
user flash memory) if a debugger access is detected (and BOOT0 information is taken from
the pin), in order to use SWCLK clock for debugger serial communications and at the same


RM0490 Rev 5 53/1027



55


**Boot modes** **RM0490**


time have a safe boot configuration for the device itself. This configuration is kept until the
earliest power-on following the debugger access.


**Caution:** BOOT0 pin sampling is done on NRST (external reset) rising edge. Refer to NRST (external
reset) description in _Section 6.1.2: System reset_ for further details on how the PF2-NRST
pin mode impacts the BOOT0 sampling.


**3.1.1** **Physical remap**


Once the boot mode is selected, the application software can modify the memory accessible
in the code area. This modification is performed by programming the MEM_MODE bits in
the _SYSCFG configuration register 1 (SYSCFG_CFGR1)_ .


**3.1.2** **Embedded boot loader**


The embedded bootloader is located in the system memory, programmed by ST during
production. It is used to reprogram the flash memory using one of the following serial
interfaces:


      - USART


      - I2C


      - SPI (only on STM32C051xx, STM32C071xx, and STM32C091xx/92xx devices)


      - USB DFU (only on STM32C071xx)


      - FDCAN (only on STM32C092xx devices)


For further details, refer to the device data sheets and the application note AN2606.


_Note:_ _Some of the GPIOs are reconfigured from their high-Z state._


_On STM32C092xx, the FDCAN_BL_CK[1:0] bitfield of the FLASH_OPTR register allows_
_selecting FDCAN clock source._


**3.1.3** **Forcing boot from main flash memory**


Setting the BOOT_LOCK bit forces the boot from a unique entry point in the main flash
memory, regardless of the boot mode configuration pin, bits, and the EMPTY flag. See
_Section 4.5.6: Forcing boot from main flash memory_ .


**3.1.4** **Empty check**


Internal empty check flag (the EMPTY bit of the FLASH access control register
FLASH_ACR) is implemented to allow easy programming of virgin devices by the boot
loader. This flag is checked when the boot configuration defines the main flash memory as
the target boot area and the BOOT_LOCK bit is not set. When the EMPTY flag is set, the
device is considered empty and the system memory (bootloader) is selected instead of the
main flash memory as a boot area, to allow the user to program the device. Refer to
AN2606 for more details concerning the bootloader and GPIO configuration in the system
memory boot mode (some of the GPIOs are reconfigured from the High-Z state).


The EMPTY flag is updated by hardware only during the loading of option bytes: it is set
when the 64-bit content of the address 0x0800 0000 is read as 0xFFFF FFFF FFFF FFFF,
otherwise it is cleared. It means that, after programming of a virgin device, a power-on reset
or setting of the OBL_LAUNCH bit of the FLASH_CR register is required to clear the
EMPTY flag (the system reset has no impact on this flag). The software can also modify the
EMPTY flag directly in the FLASH_ACR register.


54/1027 RM0490 Rev 5


**RM0490** **Boot modes**


_Note:_ _If the device is programmed for the first time but the EMPTY flag is not updated, the device_
_still selects system memory as a boot area after a system reset._


RM0490 Rev 5 55/1027



55


