**RM0490** **Documentation conventions**

# **1 Documentation conventions**

## **1.1 General information**


The STM32C0 series devices have an Arm [®(a)] Cortex [®] -M0+ core.

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

## **1.3 Register reset value**


Bits (binary notation) or bits nibbles (hexadecimal notation) of which the reset value is
undefined are marked as X.


a. Arm is a registered trademark of Arm Limited (or its subsidiaries) in the US and/or elsewhere.


b. This is an exhaustive list of all abbreviations applicable to STMicroelectronics microcontrollers, some of
them may not be used in the current document.


RM0490 Rev 5 41/1027



42


**Documentation conventions** **RM0490**


Bits (binary notation) or bits nibbles (hexadecimal notation) of which the reset value is
unmodified are marked as U.

## **1.4 Glossary**


This section gives a brief definition of acronyms and abbreviations used in this document:


      - **Word** : data of 32-bit length.


      - **Half-word** : data of 16-bit length.


      - **Byte** : data of 8-bit length.


      - **AHB** : advanced high-performance bus.

## **1.5 Availability of peripherals**


The following table lists product differentiating peripherals or functions available (X) or
absent (-) on different products.


**Table 1. Peripherals or functions versus products**





|Peripheral or function|STM32C011xx|STM32C031xx|STM32C051xx|STM32C071xx|STM32C091xx|STM32C092xx|
|---|---|---|---|---|---|---|
|CRS|-|-|-|X|-|-|
|USB|-|-|-|X|-|-|
|HSIUSB48 oscillator|-|-|-|X|-|-|
|USART3/4|-|-|-|-|X|X|
|SPI2|-|-|X|X|X|X|
|I2C2|-|-|X|X|X|X|
|FDCAN1|-|-|-|-|-|X|
|TIM2|-|-|X|X|X|X|
|TIM15|-|-|-|-|X|X|
|VDDIO2 pin|-|-|-|X(1)|-|-|


1. Not on all packages. Refer to the product datasheet.


42/1027 RM0490 Rev 5




