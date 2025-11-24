**Documentation conventions** **RM0041**

# **1 Documentation conventions**

## **1.1 List of abbreviations for registers**


The following abbreviations are used in register descriptions:


read/write (rw) Software can read and write to these bits.


read-only (r) Software can only read these bits.


write-only (w) Software can only write to this bit. Reading the bit returns the reset
value.


read/clear (rc_w1) Software can read as well as clear this bit by writing 1. Writing ‘0’ has no
effect on the bit value.


read/clear (rc_w0) Software can read as well as clear this bit by writing 0. Writing ‘1’ has no
effect on the bit value.


read/clear by read Software can read this bit. Reading this bit automatically clears it to ‘0’.
(rc_r) Writing ‘0’ has no effect on the bit value.


read/set (rs) Software can read as well as set this bit. Writing ‘0’ has no effect on the
bit value.


read-only write Software can read this bit. Writing ‘0’ or ‘1’ triggers an event but has no
trigger (rt_w) effect on the bit value.


toggle (t) Software can only toggle this bit by writing ‘1’. Writing ‘0’ has no effect.


Reserved (Res.) Reserved bit, must be kept at reset value.

## **1.2 Glossary**


      - **Low-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 16 and 32 Kbytes.

      - **Medium-density** **value line devices** are STM32F100xx microcontrollers where the
flash memory density ranges between 64 and 128 Kbytes.

      - **High-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 256 and 512 Kbytes.

      - **Word:** data of 32-bit length.

      - **Half-word:** data of 16-bit length.

      - **Byte:** data of 8-bit length.

## **1.3 Peripheral availability**


For the availability and number of peripherals across sales types, refer to the STM32F100xx
datasheets.


32/709 RM0041 Rev 6


**RM0041** **Documentation conventions**

## **1.4 General information**


The STM32F100xx MCUs are based on an Arm [®] Cortex [®] core.


_Note:_ _Arm is a registered trademark of Arm Limited (or its subsidiaries) in the US and/or_
_elsewhere._


RM0041 Rev 6 33/709



46


