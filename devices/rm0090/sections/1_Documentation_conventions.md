**RM0090** **Documentation conventions**

# **1 Documentation conventions**


The STM32F405xx/07xx, STM32F415xx/17xx, STM32F42xxx and STM32F43xxx devices
have an Arm [®][(a)] Cortex [®] -M4 with FPU core.

## **1.1 List of abbreviations for registers**


The following abbreviations are used in register descriptions:


read/write (rw) Software can read and write to these bits.


read-only (r) Software can only read these bits.


write-only (w) Software can only write to this bit. Reading the bit returns the reset
value.


read/clear (rc_w1) Software can read as well as clear this bit by writing 1. Writing ‘0’ has
no effect on the bit value.


read/clear (rc_w0) Software can read as well as clear this bit by writing 0. Writing ‘1’ has
no effect on the bit value.


read/clear by read Software can read this bit. Reading this bit automatically clears it to ‘0’.
(rc_r) Writing ‘0’ has no effect on the bit value.


read/set (rs) Software can read as well as set this bit. Writing ‘0’ has no effect on the
bit value.


read-only write Software can read this bit. Writing ‘0’ or ‘1’ triggers an event but has no
trigger (rt_w) effect on the bit value.


toggle (t) Software can only toggle this bit by writing ‘1’. Writing ‘0’ has no effect.


Reserved (Res.) Reserved bit, must be kept at reset value.


a. Arm is a registered trademark of Arm Limited (or its subsidiaries) in the US and/or elsewhere.


RM0090 Rev 21 57/1757



113


**Documentation conventions** **RM0090**

## **1.2 Glossary**


This section gives a brief definition of acronyms and abbreviations used in this document:


      - The CPU core integrates two debug ports:


–
JTAG debug port (JTAG-DP) provides a 5-pin standard interface based on the
Joint Test Action Group (JTAG) protocol.


–
SWD debug port (SWD-DP) provides a 2-pin (clock and data) interface based on
the Serial Wire Debug (SWD) protocol.

For both the JTAG and SWD protocols, please refer to the Cortex [®] -M4 with FPU
Technical Reference Manual


      - Word: data/instruction of 32-bit length.


      - Half word: data/instruction of 16-bit length.


      - Byte: data of 8-bit length.


      - Double word: data of 64-bit length.


      - IAP (in-application programming): IAP is the ability to reprogram the flash memory of a
microcontroller while the user program is running.


      - ICP (in-circuit programming): ICP is the ability to program the flash memory of a
microcontroller using the JTAG protocol, the SWD protocol or the bootloader while the
device is mounted on the user application board.


      - I-Code: this bus connects the Instruction bus of the CPU core to the Flash instruction

interface. Prefetch is performed on this bus.


      - D-Code: this bus connects the D-Code bus (literal load and debug access) of the CPU
to the Flash data interface.


      - Option bytes: product configuration bits stored in the flash memory.


      - OBL: option byte loader.


      - AHB: advanced high-performance bus.

      - CPU: refers to the Cortex [®] -M4 with FPU core.

## **1.3 Peripheral availability**


For peripheral availability and number across all STM32F405xx/07xx and
STM32F415xx/17xx sales types, please refer to the STM32F405xx/07xx and
STM32F415xx/17xx datasheets.


For peripheral availability and number across all STM32F42xxx and STM32F43xxx sales
types, please refer to the STM32F42xxx and STM32F43xxx datasheets.


58/1757 RM0090 Rev 21


