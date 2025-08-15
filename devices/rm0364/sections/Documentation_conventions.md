**RM0364** **Documentation conventions**

# **1 Documentation conventions**

## **1.1 General information**


The STM32F334xx devices have an Arm [®][(a)] Cortex [®] -M4 core.

## **1.2 List of abbreviations for registers**


The following abbreviations [(b)] are used in register descriptions:


read/write (rw) Software can read and write to this bit.


read-only (r) Software can only read this bit.


write-only (w) Software can only write to this bit. Reading this bit returns the reset value.


read/clear write0 (rc_w0) Software can read as well as clear this bit by writing 0. Writing 1 has no
effect on the bit value.


read/clear write1 (rc_w1) Software can read as well as clear this bit by writing 1. Writing 0 has no
effect on the bit value.


read/clear write (rc_w) Software can read as well as clear this bit by writing to the register. The
value written to this bit is not important.


read/clear by read (rc_r) Software can read this bit. Reading this bit automatically clears it to 0.
Writing this bit has no effect on the bit value.


read/set by read (rs_r) Software can read this bit. Reading this bit automatically sets it to 1.
Writing this bit has no effect on the bit value.


read/set (rs) Software can read as well as set this bit. Writing 0 has no effect on the bit
value.


read/write once (rwo) Software can only write once to this bit and can also read it at any time.
Only a reset can return the bit to its reset value.


toggle (t) The software can toggle this bit by writing 1. Writing 0 has no effect.


read-only write trigger (rt_w1) Software can read this bit. Writing 1 triggers an event but has no effect on
the bit value.


Reserved (Res.) Reserved bit, must be kept at reset value.


a. Arm is a registered trademark of Arm Limited (or its subsidiaries) in the US and/or elsewhere.


b. This is an exhaustive list of all abbreviations applicable to STM microcontrollers, some of them may not be
used in the current document.


RM0364 Rev 4 43/1124



44


**Documentation conventions** **RM0364**

## **1.3 Glossary**


This section gives a brief definition of acronyms and abbreviations used in this document:

      - The Arm [®] Cortex [®] -M4 core integrates one debug port: **SWD debug port (SWD-DP)**
provides a 2-pin (clock and data) interface based on the Serial Wire Debug (SWD)
protocol. Refer to the Cortex [®] -M4 technical reference manual.


      - **Word** : data of 32-bit length.


      - **Half-word** : data of 16-bit length.


      - **Byte** : data of 8-bit length.


      - **IAP (in-application programming)** : IAP is the ability to re-program the Flash memory
of a microcontroller while the user program is running.


      - **ICP (in-circuit programming)** : ICP is the ability to program the Flash memory of a
microcontroller using the JTAG protocol, the SWD protocol or the bootloader while the
device is mounted on the user application board.


      - **Option bytes** : product configuration bits stored in the Flash memory.


      - **OBL** : option byte loader.


      - **AHB** : advanced high-performance bus.

## **1.4 Availability of peripherals**


For availability of peripherals and their number across all sales types, refer to the particular
device datasheet.


44/1124 RM0364 Rev 4


