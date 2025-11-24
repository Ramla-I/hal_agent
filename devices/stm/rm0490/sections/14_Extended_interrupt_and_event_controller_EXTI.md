**Extended interrupt and event controller (EXTI)** **RM0490**

# **14 Extended interrupt and event controller (EXTI)**


The Extended interrupt and event controller (EXTI) manages the CPU and system wake-up
through configurable and direct event inputs (lines). It provides wake-up requests to the
power control, and generates an interrupt request to the CPU NVIC and events to the CPU
event input. For the CPU an additional event generation block (EVG) is needed to generate
the CPU event signal.


The EXTI wake-up requests allow the system to be woken up from Stop modes.


The interrupt request and event request generation can also be used in Run mode.


The EXTI also includes the EXTI I/O port multiplexer.

## **14.1 EXTI main features**


The EXTI main features are the following:


      - System wake-up upon event on any input


      - Wake-up flag and CPU interrupt generation for events not having a wake-up flag in
their source peripheral


      - Configurable events (from I/Os, peripherals not having an associated interrupt pending
status bit, or peripherals generating a pulse)


–
Selectable active trigger edge


–
Independent rising and falling edge interrupt pending status bits


–
Individual interrupt and event generation mask, used for conditioning the CPU
wake-up, interrupt and event generation


–
SW trigger possibility


      - Direct events (from peripherals having an associated flag and interrupt pending status
bit)


–
Fixed rising edge active trigger


–
No interrupt pending status bit in the EXTI


–
Individual interrupt and event generation mask for conditioning the CPU wake-up
and event generation


–
No SW trigger possibility


      - I/O port selector

## **14.2 EXTI block diagram**


The EXTI consists of a register block accessed via an AHB interface, the event input trigger
block, the masking block, and EXTI multiplexer as shown in _Figure 25_ .


The register block contains all the EXTI registers.


The event input trigger block provides an event input edge trigger logic.


The masking block provides the event input distribution to the different wake-up, interrupt
and event outputs, and the masking of these.


The EXTI multiplexer provides the I/O port selection on to the EXTI event signal.


260/1027 RM0490 Rev 5


**RM0490** **Extended interrupt and event controller (EXTI)**


**Figure 25. EXTI block diagram**


























|Col1|Col2|
|---|---|
|||
|||
||c_evt_rst|









**Table 56. EXTI signal overview**

|Signal name|I/O|Description|
|---|---|---|
|AHB interface|I/O|EXTI register bus interface. When one event is configured to allow<br>security, the AHB interface support secure accesses|
|hclk|I|AHB bus clock and EXTI system clock|
|Configurable<br>event(y)|I|Asynchronous wake-up events from peripherals that do not have an<br>associated interrupt and flag in the peripheral|
|Direct event(x)|I|Synchronous and asynchronous wake-up events from peripherals having<br>an associated interrupt and flag in the peripheral|
|IOPort(n)|I|GPIO ports[15:0]|
|exti[15:0]|O|EXTI output port to trigger other IPs|
|it_exti_per (y)|O|Interrupts to the CPU associated with configurable event (y)|
|c_evt_exti|O|High-level sensitive event output for CPU synchronous to hclk|
|c_evt_rst|I|Asynchronous reset input to clear c_evt_exti|
|sys_wakeup|O|Asynchronous system wake-up request to PWR for ck_sys and hclk|
|c_wakeup|O|Wake-up request to PWR for CPU, synchronous to hclk|



**Table 57. EVG pin overview**

|Pin name|I/O|Description|
|---|---|---|
|c_fclk|I|CPU free-running clock|
|c_evt_in|I|High-level sensitive event input from EXTI, asynchronous to CPU clock|
|c_event|O|Event pulse, synchronous to CPU clock|
|c_evt_rst|O|Event reset signal, synchronous to CPU clock|



RM0490 Rev 5 261/1027



277


**Extended interrupt and event controller (EXTI)** **RM0490**


**14.2.1** **EXTI connections between peripherals and CPU**


The peripherals able to generate wake-up or interrupt events when the system is in Stop
mode are connected to the EXTI.


      - Peripheral wake-up signals that generate a pulse or that do not have an interrupt status
bits in the peripheral, are connect to an EXTI configurable line. For these events the
EXTI provides a status pending bit which requires to be cleared. It is the EXTI interrupt
associated with the status bit that interrupts the CPU.


      - Peripheral interrupt and wake-up signals that have a status bit in the peripheral which
requires to be cleared in the peripheral, are connected to an EXTI direct line. There is
no status pending bit within the EXTI. The interrupt or wake-up is cleared by the CPU in
the peripheral. It is the peripheral interrupt that interrupts the CPU directly.


      - All GPIO ports input to the EXTI multiplexer, allowing to select a port to wake up the
system via a configurable event.


The EXTI configurable event interrupts are connected to the NVIC(a) of the CPU.


The dedicated EXTI/EVG CPU event is connected to the CPU rxev input.


The EXTI CPU wake-up signals are connected to the PWR block, and are used to wake up
the system and CPU sub-system bus clocks.

## **14.3 EXTI functional description**


Depending on the EXTI line type and wake-up target(s), different logic implementations are
used. The applicable features and control or status registers are:


      - rising and falling edge event enable through


–
_EXTI rising trigger selection register 1 (EXTI_RTSR1)_


–
_EXTI falling trigger selection register 1 (EXTI_FTSR1)_


      - software trigger through _EXTI software interrupt event register 1 (EXTI_SWIER1)_


      - pending interrupt flagging through


–
_EXTI rising edge pending register 1 (EXTI_RPR1)_


–
_EXTI falling edge pending register 1 (EXTI_FPR1)_


–
_EXTI external interrupt selection register (EXTI_EXTICRx)_


      - CPU wake-up and interrupt enable through


–
_EXTI CPU wake-up with interrupt mask register 1 (EXTI_IMR1)_


      - CPU wake-up and event enable through


–
_EXTI CPU wake-up with event mask register (EXTI_EMR1)_


**Table 58. EXTI event input configurations and register control**





|Event input<br>type|Logic implementation|EXTI_RTSR1|EXTI_FTSR1|EXTI_SWIER1|EXTI_R/FPR1|EXTI_IMR1|EXTI_EMR1|
|---|---|---|---|---|---|---|---|
|Configurable|Configurable event input wake-up logic|x|x|x|x|x|x|
|Direct|Direct event input wake-up logic|-|-|-|-|x|x|


262/1027 RM0490 Rev 5


**RM0490** **Extended interrupt and event controller (EXTI)**


**14.3.1** **EXTI configurable event input wake-up**


_Figure 26_ is a detailed representation of the logic associated with configurable event inputs
which wake up the CPU sub-system bus clocks and generated an EXTI pending flag and
interrupt to the CPU and or a CPU wake-up event.


**Figure 26. Configurable event trigger logic CPU wake-up**



















































The software interrupt event register allows triggering configurable events by software,
writing the corresponding register bit, irrespective of the edge selection setting.


The rising edge and falling edge selection registers allow to enable and select the
configurable event active trigger edge or both edges.


The CPU has its dedicated interrupt mask register and a dedicated event mask registers.
The enabled event allows generating an event on the CPU. All events for a CPU are OR-ed
together into a single CPU event signal. The event pending registers (EXTI_RPR1 and
EXTI_FPR1) is not set for an unmasked CPU event.


The configurable events have unique interrupt pending request registers, shared by the
CPU. The pending register is only set for an unmasked interrupt. Each configurable event
provides a common interrupt to the CPU. The configurable event interrupts need to be
acknowledged by software in the EXTI_RPR1 and/or EXTI_FPR1 registers.


When a CPU interrupt or CPU event is enabled, the asynchronous edge detection circuit is
reset by the clocked delay and rising edge detect pulse generator. This guarantees the
wake-up of the EXTI hclk clock before the asynchronous edge detection circuit is reset.


_Note:_ _A detected configurable event interrupt pending request can be cleared by the CPU. The_
_system cannot enter low-power modes as long as an interrupt pending request is active._


**14.3.2** **EXTI direct event input wake-up**


_Figure 27_ is a detailed representation of the logic associated with direct event inputs waking
up the system.


The direct events do not have an associated EXTI interrupt. The EXTI only wakes up the
system and CPU sub-system clocks and may generate a CPU wake-up event. The
peripheral synchronous interrupt, associated with the direct wake-up event wakes up the
CPU.


RM0490 Rev 5 263/1027



277


**Extended interrupt and event controller (EXTI)** **RM0490**


The EXTI direct event is able to generate a CPU event. This CPU event wakes up the CPU.
The CPU event may occur before the interrupt flag of the associated peripheral is set.


**Figure 27. Direct event trigger logic CPU wake-up**







































**14.3.3** **EXTI multiplexer**


The EXTI multiplexer allows selecting GPIOs as interrupts and wake-up. The GPIOs are
connected via 16 EXTI multiplexer lines to the first 16 EXTI events as configurable event.
The selection of GPIO port as EXTI multiplexer output is controlled through the _EXTI_
_external interrupt selection register (EXTI_EXTICRx)_ register.


**Figure 28. EXTI GPIO multiplexer**



_



_



_



















The EXTIs multiplexer outputs are available as output signals from the EXTI, to trigger other
functional blocks. The EXTI multiplexer outputs are available independently of mask setting
through the EXTI_IMR and EXTI_EMR registers.


The EXTI lines (event inputs) are connected as shown in the following table.


264/1027 RM0490 Rev 5


**RM0490** **Extended interrupt and event controller (EXTI)**


**Table 59. EXTI line connections**

|EXTI line|Line source|Line type|
|---|---|---|
|0-15|GPIO|Configurable|
|16|Reserved|-|
|17|Reserved|-|
|18|Reserved|-|
|19|RTC|Direct|
|20|Reserved|-|
|21|Reserved|-|
|22|Reserved|-|
|23|I2C1 wake-up|Direct|
|24|Reserved|-|
|25|USART1 wake-up|Direct|
|26|Reserved|-|
|27|Reserved|-|
|28|Reserved|-|
|29|Reserved|-|
|30|Reserved|-|
|31|LSE_CSS|Direct|
|32|Reserved|-|
|33|Reserved|-|
|34|VDDIO2 monitoring|Configurable|
|35|Reserved|-|
|36|USB wake-up|Direct|


## **14.4 EXTI functional behavior**


The direct event inputs are enabled in the respective peripheral generating the wake-up
event. The configurable events are enabled by enabling at least one of the trigger edges.


Once an event input is enabled, the generation of a CPU wake-up is conditioned by the
CPU interrupt mask and CPU event mask.


**Table 60. Masking functionality**











|CPU interrupt<br>enable<br>EXTI_IMR.IMn|CPU event enable<br>EXTI_EMR.EMn|Configurable<br>event inputs<br>EXTI_RPR.RPIFn<br>EXTI_FPR.FPIFn|exti(n)<br>interrupt(1)|CPU<br>event|CPU wake-up|
|---|---|---|---|---|---|
|0|0|No|Masked|Masked|Masked|
|0|1|No|Masked|Yes|Yes|


RM0490 Rev 5 265/1027



277


**Extended interrupt and event controller (EXTI)** **RM0490**


**Table 60. Masking functionality** **(continued)**











|CPU interrupt<br>enable<br>EXTI_IMR.IMn|CPU event enable<br>EXTI_EMR.EMn|Configurable<br>event inputs<br>EXTI_RPR.RPIFn<br>EXTI_FPR.FPIFn|exti(n)<br>interrupt(1)|CPU<br>event|CPU wake-up|
|---|---|---|---|---|---|
|1|0|Status latched|Yes|Masked|Yes(2)|
|1|1|Status latched|Yes|Yes|Yes|


1. The single exti(n) interrupt goes to the CPU. If no interrupt is required for CPU, the exti(n) interrupt must be masked in the
CPU NVIC.


2. Only if CPU interrupt is enabled in EXTI_IMR.IMn.


For configurable event inputs, upon an edge on the event input, an event request is
generated if that edge (rising or/and falling) is enabled. When the associated CPU interrupt
is unmasked, the corresponding RPIFn and/or FPIFn bit is/are set in the EXTI_RPR or/and
EXTI_FPR register, waking up the CPU subsystem and activating CPU interrupt signal. The
RPIFn and/or FPIFn pending bit is cleared by writing 1 to it, which clears the CPU interrupt
request.


For direct event inputs, when enabled in the associated peripheral, an event request is
generated on the rising edge only. There is no corresponding CPU pending bit in the EXTI.
When the associated CPU interrupt is unmasked, the corresponding CPU subsystem is
woken up. The CPU is woken up (interrupted) by the peripheral synchronous interrupt.


The CPU event must be unmasked to generate an event. Upon an enabled edge occurring
on an event input, a CPU event pulse is generated. There is no event pending bit.


For the configurable event inputs, the software can generate an event request by setting the
corresponding bit of the software interrupt/event register EXTI_SWIER1, which has the
effect of a rising edge on the event input. The pending rising edge event flag is set in the
EXTI_RPR1 register, irrespective of the EXTI_RTSR1 register setting.

## **14.5 EXTI registers**


The EXTI register map is divided in the following sections:


**Table 61. EXTI register map sections**

|Address|Description|
|---|---|
|0x000 - 0x01C|General configurable event [31:0] configuration|
|0x060 - 0x06C|EXTI I/O port multiplexer|
|0x080 - 0x0BC|CPU input event configuration|



All the registers can be accessed with word (32-bit), half-word (16-bit) and byte (8-bit)

access.


**14.5.1** **EXTI rising trigger selection register 1 (EXTI_RTSR1)**


Address offset: 0x000


Reset value: 0x0000 0000


266/1027 RM0490 Rev 5


**RM0490** **Extended interrupt and event controller (EXTI)**


Contains only register bits for configurable events.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|RT15|RT14|RT13|RT12|RT11|RT10|RT9|RT8|RT7|RT6|RT5|RT4|RT3|RT2|RT1|RT0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **RTx:** Rising trigger event configuration bit of configurable line x (x = 15 to 0)

Each bit enables/disables the rising edge trigger for the event and interrupt on the
corresponding line.

0: Disable

1: Enable

_Note: The configurable lines are edge triggered; no glitch must be generated on these inputs._
_If a rising edge on the configurable line occurs during writing of the register, the_
_associated pending bit is not set. Rising edge trigger can be set for a line with falling_
_edge trigger enabled. In this case, both edges generate a trigger._


**14.5.2** **EXTI falling trigger selection register 1 (EXTI_FTSR1)**


Address offset: 0x004


Reset value: 0x0000 0000


Contains only register bits for configurable events.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|FT15|FT14|FT13|FT12|FT11|FT10|FT9|FT8|FT7|FT6|FT5|FT4|FT3|FT2|FT1|FT0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **FTx:** Falling trigger event configuration bit of configurable line x (x = 15 to 0).

Each bit enables/disables the falling edge trigger for the event and interrupt on the
corresponding line.

0: Disable

1: Enable

_Note: The configurable lines are edge triggered; no glitch must be generated on these inputs._
_If a falling edge on the configurable line occurs during writing of the register, the_
_associated pending bit is not set. Falling edge trigger can be set for a line with rising_
_edge trigger enabled. In this case, both edges generate a trigger._


**14.5.3** **EXTI software interrupt event register 1 (EXTI_SWIER1)**


Address offset: 0x008


RM0490 Rev 5 267/1027



277


**Extended interrupt and event controller (EXTI)** **RM0490**


Reset value: 0x0000 0000


Contains only register bits for configurable events.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SWI<br>15|SWI<br>14|SWI<br>13|SWI<br>12|SWI<br>11|SWI<br>10|SWI9|SWI8|SWI7|SWI6|SWI5|SWI4|SWI3|SWI2|SWI1|SWI0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **SWIx:** Software rising edge event trigger on line x (x = 15 to 0)

Setting of any bit by software triggers a rising edge event on the corresponding line x,
resulting in an interrupt, independently of EXTI_RTSR1 and EXTI_FTSR1 settings. The bits
are automatically cleared by HW. Reading of any bit always returns 0.

0: No effect

1: Rising edge event generated on the corresponding line, followed by an interrupt


**14.5.4** **EXTI rising edge pending register 1 (EXTI_RPR1)**


Address offset: 0x00C


Reset value: 0x0000 0000


Contains only register bits for configurable events.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|RPIF15|RPIF14|RPIF13|RPIF12|RPIF11|RPIF10|RPIF9|RPIF8|RPIF7|RPIF6|RPIF5|RPIF4|RPIF3|RPIF2|RPIF1|RPIF0|
|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **RPIFx:** Rising edge event pending for configurable line x (x = 15 to 0)

Each bit is set upon a rising edge event generated by hardware or by software (through the
EXTI_SWIER1 register) on the corresponding line. Each bit is cleared by writing 1 into it.
0: No rising edge trigger request occurred
1: Rising edge trigger request occurred


**14.5.5** **EXTI falling edge pending register 1 (EXTI_FPR1)**


Address offset: 0x010


Reset value: 0x0000 0000


Contains only register bits for configurable events.


268/1027 RM0490 Rev 5


**RM0490** **Extended interrupt and event controller (EXTI)**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|FPIF15|FPIF14|FPIF13|FPIF12|FPIF11|FPIF10|FPIF9|FPIF8|FPIF7|FPIF6|FPIF5|FPIF4|FPIF3|FPIF2|FPIF1|FPIF0|
|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **FPIFx:** Falling edge event pending for configurable line x (x = 15 to 0)

Each bit is set upon a falling edge event generated by hardware or by software (through the
EXTI_SWIER1 register) on the corresponding line. Each bit is cleared by writing 1 into it.
0: No falling edge trigger request occurred
1: Falling edge trigger request occurred


**14.5.6** **EXTI rising trigger selection register 2 (EXTI_RTSR2)**


This register is only available on STM32C071xx. On the other devices, it is reserved.


Address offset: 0x020


Reset value: 0x0000 0000


Contains only register bits for configurable events.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RT34|Res.|Res.|
||||||||||||||rw|||



Bits 31:3 Reserved, must be kept at reset value.


Bit 2 **RT34:** Rising trigger event configuration bit of configurable line 34

Each bit enables/disables the rising edge trigger for the event and interrupt on the line 34.

0: Disable

1: Enable

_Note: This configurable line is edge triggered; no glitch must be generated on this inputs._
_If a rising edge on the configurable line occurs during writing of the register, the_
_associated pending bit is not set. Rising edge trigger can be set for a line with falling_
_edge trigger enabled. In this case, both edges generate a trigger._


Bits 1:0 Reserved, must be kept at reset value.


**14.5.7** **EXTI falling trigger selection register 2 (EXTI_FTSR2)**


This register is only available on STM32C071xx. On the other devices, it is reserved.


Address offset: 0x024


Reset value: 0x0000 0000


Contains only register bits for configurable events.


RM0490 Rev 5 269/1027



277


**Extended interrupt and event controller (EXTI)** **RM0490**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FT34|Res.|Res.|
||||||||||||||rw|||



Bits 31:3 Reserved, must be kept at reset value.


Bit 2 **FT34:** Falling trigger event configuration bit of configurable line 34.

Each bit enables/disables the falling edge trigger for the event and interrupt on the line 34.

0: Disable

1: Enable

_Note: The configurable lines are edge triggered; no glitch must be generated on these inputs._
_If a falling edge on the configurable line occurs during writing of the register, the_
_associated pending bit is not set. Falling edge trigger can be set for a line with rising_
_edge trigger enabled. In this case, both edges generate a trigger._


Bits 1:0 Reserved, must be kept at reset value.


**14.5.8** **EXTI software interrupt event register 2 (EXTI_SWIER2)**


This register is only available on STM32C071xx. On the other devices, it is reserved.


Address offset: 0x028


Reset value: 0x0000 0000


Contains only register bits for configurable events.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SWI34|Res.|Res.|
||||||||||||||rw|||



Bits 31:3 Reserved, must be kept at reset value.


Bit 2 **SWI34:** Software rising edge event trigger on line 34

Setting of any bit by software triggers a rising edge event on the line 34, resulting in an
interrupt, independently of EXTI_RTSR2 and EXTI_FTSR2 settings. The bits are
automatically cleared by HW. Reading of any bit always returns 0.

0: No effect

1: Rising edge event generated on the corresponding line, followed by an interrupt


Bits 1:0 Reserved, must be kept at reset value.


**14.5.9** **EXTI rising edge pending register 2 (EXTI_RPR2)**


This register is only available on STM32C071xx. On the other devices, it is reserved.


Address offset: 0x02C


Reset value: 0x0000 0000


270/1027 RM0490 Rev 5


**RM0490** **Extended interrupt and event controller (EXTI)**


Contains only register bits for configurable events.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RPIF34|Res.|Res.|
||||||||||||||rc_w1|||



Bits 31:3 Reserved, must be kept at reset value.


Bit 2 **RPIF34:** Rising edge event pending for configurable line 34

Each bit is set upon a rising edge event generated by hardware or by software (through the
EXTI_SWIER2 register) on the line 34. Each bit is cleared by writing 1 into it.
0: No rising edge trigger request occurred
1: Rising edge trigger request occurred


Bits 1:0 Reserved, must be kept at reset value.


**14.5.10** **EXTI falling edge pending register 2 (EXTI_FPR2)**


This register is only available on STM32C071xx. On the other devices, it is reserved.


Address offset: 0x030


Reset value: 0x0000 0000


Contains only register bits for configurable events.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FPIF34|Res.|Res.|
||||||||||||||rc_w1|||



Bits 31:3 Reserved, must be kept at reset value.


Bit 2 **FPIF34:** Falling edge event pending for configurable line 34

Each bit is set upon a falling edge event generated by hardware or by software (through the
EXTI_SWIER2 register) on the line 34. Each bit is cleared by writing 1 into it.
0: No falling edge trigger request occurred
1: Falling edge trigger request occurred


Bits 1:0 Reserved, must be kept at reset value.


**14.5.11** **EXTI external interrupt selection register (EXTI_EXTICRx)**


Address offset: 0x060 + 0x4 * (x - 1), (x = 1 to 4)


Reset value: 0x0000 0000


RM0490 Rev 5 271/1027



277


**Extended interrupt and event controller (EXTI)** **RM0490**

|31 30 29 28 27 26 25 24|Col2|Col3|Col4|Col5|Col6|Col7|Col8|23 22 21 20 19 18 17 16|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI{4*(x-1)+3}[7:0]|EXTI{4*(x-1)+3}[7:0]|EXTI{4*(x-1)+3}[7:0]|EXTI{4*(x-1)+3}[7:0]|EXTI{4*(x-1)+3}[7:0]|EXTI{4*(x-1)+3}[7:0]|EXTI{4*(x-1)+3}[7:0]|EXTI{4*(x-1)+3}[7:0]|EXTI{4*(x-1)+2}[7:0]|EXTI{4*(x-1)+2}[7:0]|EXTI{4*(x-1)+2}[7:0]|EXTI{4*(x-1)+2}[7:0]|EXTI{4*(x-1)+2}[7:0]|EXTI{4*(x-1)+2}[7:0]|EXTI{4*(x-1)+2}[7:0]|EXTI{4*(x-1)+2}[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EXTI{4*(x-1)+1}[7:0]|EXTI{4*(x-1)+1}[7:0]|EXTI{4*(x-1)+1}[7:0]|EXTI{4*(x-1)+1}[7:0]|EXTI{4*(x-1)+1}[7:0]|EXTI{4*(x-1)+1}[7:0]|EXTI{4*(x-1)+1}[7:0]|EXTI{4*(x-1)+1}[7:0]|EXTI{4*(x-1)}[7:0]|EXTI{4*(x-1)}[7:0]|EXTI{4*(x-1)}[7:0]|EXTI{4*(x-1)}[7:0]|EXTI{4*(x-1)}[7:0]|EXTI{4*(x-1)}[7:0]|EXTI{4*(x-1)}[7:0]|EXTI{4*(x-1)}[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:24 **EXTI{4*(x-1)+3}[7:0]:** EXTI{4*(x-1)+3} GPIO port selection

These bits are written by software to select the source input for EXTI{4*(x-1)+3} external
interrupt.
0x00: PA[{4*(x-1)+3}] pin
0x01: PB[{4*(x-1)+3}] pin
0x02: PC[{4*(x-1)+3}] pin
0x03: PD[{4*(x-1)+3}] pin

0x04: reserved

0x05: PF[{4*(x-1)+3}] pin

Other: reserved


Bits 23:16 **EXTI{4*(x-1)+2}[7:0]:** EXTI{4*(x-1)+2} GPIO port selection

These bits are written by software to select the source input for EXTI{4*(x-1)+2} external
interrupt.
0x00: PA[{4*(x-1)+2}] pin
0x01: PB[{4*(x-1)+2}] pin
0x02: PC[{4*(x-1)+2}] pin
0x03: PD[{4*(x-1)+2}] pin

0x04: reserved

0x05: PF[{4*(x-1)+2}] pin

Other: reserved


Bits 15:8 **EXTI{4*(x-1)+1}[7:0]:** EXTI{4*(x-1)+1} GPIO port selection

These bits are written by software to select the source input for EXTI{4*(x-1)+1} external
interrupt.
0x00: PA[{4*(x-1)+1}] pin
0x01: PB[{4*(x-1)+1}] pin
0x02: PC[{4*(x-1)+1}] pin
0x03: PD[{4*(x-1)+1}] pin

0x04: reserved

0x05: PF[{4*(x-1)+1}] pin

Other: reserved


Bits 7:0 **EXTI{4*(x-1)}[7:0]:** EXTI{4*(x-1)} GPIO port selection

These bits are written by software to select the source input for EXTI{4*(x-1)} external
interrupt.

0x00: PA[{4*(x-1)}] pin
0x01: PB[{4*(x-1)}] pin
0x02: PC[{4*(x-1)}] pin
0x03: PD[{4*(x-1)}] pin

0x04: reserved

0x05: PF[{4*(x-1)}] pin

Other: reserved


272/1027 RM0490 Rev 5


**RM0490** **Extended interrupt and event controller (EXTI)**


**14.5.12** **EXTI CPU wake-up with interrupt mask register 1 (EXTI_IMR1)**


Address offset: 0x080


Reset value: 0xFFF8 0000


Contains register bits for configurable events and direct events.


The reset value is set such as to, by default, enable interrupt from direct lines, and disable
interrupt from configurable lines.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|IM31|Res.|Res.|Res.|Res.|Res.|IM25|Res.|IM23|Res.|Res.|Res.|IM19|Res.|Res.|Res.|
|rw||||||rw||rw||||rw||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|IM15|IM14|IM13|IM12|IM11|IM10|IM9|IM8|IM7|IM6|IM5|IM4|IM3|IM2|IM1|IM0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 31 **IM31:** CPU wake-up with interrupt mask on line 31

Setting/clearing this bit unmasks/masks the CPU wake-up with interrupt, by an event on the
corresponding line.
0: wake-up with interrupt masked
1: wake-up with interrupt unmasked


Bits 30:26 Reserved, must be kept at reset value.


Bit 25 **IM25:** CPU wake-up with interrupt mask on line 25

Setting/clearing each bit unmasks/masks the CPU wake-up with interrupt, by an event on
the corresponding line.
0: wake-up with interrupt masked
1: wake-up with interrupt unmasked


Bit 24 Reserved, must be kept at reset value.


Bit 23 **IM23:** CPU wake-up with interrupt mask on line 23

Setting/clearing each bit unmasks/masks the CPU wake-up with interrupt, by an event on
the corresponding line.
0: wake-up with interrupt masked
1: wake-up with interrupt unmasked


Bits 22:20 Reserved, must be kept at reset value.


Bit 19 **IM19:** CPU wake-up with interrupt mask on line 19

Setting/clearing this bit unmasks/masks the CPU wake-up with interrupt, by an event on the
corresponding line.
0: wake-up with interrupt masked
1: wake-up with interrupt unmasked


Bits 18:16 Reserved, must be kept at reset value.


Bits 15:0 **IMx:** CPU wake-up with interrupt mask on line x (x = 15 to 0)

Setting/clearing each bit unmasks/masks the CPU wake-up with interrupt, by an event on
the corresponding line.
0: wake-up with interrupt masked
1: wake-up with interrupt unmasked


RM0490 Rev 5 273/1027



277


**Extended interrupt and event controller (EXTI)** **RM0490**


**14.5.13** **EXTI CPU wake-up with event mask register (EXTI_EMR1)**


Address offset: 0x084


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EM31|Res.|Res.|Res.|Res.|Res.|EM25|Res.|EM23|Res.|Res.|Res.|EM19|Res.|Res.|Res.|
|rw||||||rw||rw||||rw||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|EM15|EM14|EM13|EM12|EM11|EM10|EM9|EM8|EM7|EM6|EM5|EM4|EM3|EM2|EM1|EM0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 31 **EM31:** CPU wake-up with event generation mask on line 31

Setting/clearing this bit unmasks/masks the CPU wake-up with event generation on the
corresponding line.
0: wake-up with event generation masked
1: wake-up with event generation unmasked


Bits 30:26 Reserved, must be kept at reset value.


Bit 25 **EM25:** CPU wake-up with event generation mask on line 25

Setting/clearing this bit unmasks/masks the CPU wake-up with event generation on the
corresponding line.
0: wake-up with event generation masked
1: wake-up with event generation unmasked


Bit 24 Reserved, must be kept at reset value.


Bit 23 **EM23:** CPU wake-up with event generation mask on line 23

Setting/clearing this bit unmasks/masks the CPU wake-up with event generation on the
corresponding line.
0: wake-up with event generation masked
1: wake-up with event generation unmasked


Bits 22:20 Reserved, must be kept at reset value.


Bit 19 **EM19:** CPU wake-up with event generation mask on line 19

Setting/clearing this bit unmasks/masks the CPU wake-up with event generation on the
corresponding line.
0: wake-up with event generation masked
1: wake-up with event generation unmasked


Bits 18:16 Reserved, must be kept at reset value.


Bits 15:0 **EMx:** CPU wake-up with event generation mask on line x (x = 15 to 0)

Setting/clearing each bit unmasks/masks the CPU wake-up with event generation on the
corresponding line.
0: wake-up with event generation masked
1: wake-up with event generation unmasked


**14.5.14** **EXTI CPU wake-up with interrupt mask register 2 (EXTI_IMR2)**


This register is only available on STM32C071xx. On the other devices, it is reserved.


Address offset: 0x090


274/1027 RM0490 Rev 5


**RM0490** **Extended interrupt and event controller (EXTI)**


Reset value: 0x0000 0000


Contains register bits for configurable events and direct events.


The reset value is set such as to, by default, enable interrupt from direct lines, and disable
interrupt from configurable lines.

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|IM36|Res.|IM34|Res.|Res.|
||||||||||||rw||rw|||



Bits 31:5 Reserved, must be kept at reset value.


Bit 4 **IM36:** CPU wake-up with interrupt mask on line 36

Setting/clearing the bit unmasks/masks the CPU wake-up with interrupt request from the line
36.

0: wake-up with interrupt masked
1: wake-up with interrupt unmasked


Bit 3 Reserved, must be kept at reset value.


Bit 2 **IM34:** CPU wake-up with interrupt mask on line 34

Setting/clearing the bit unmasks/masks the CPU wake-up with interrupt request from the line
34.

0: wake-up with interrupt masked
1: wake-up with interrupt unmasked


Bits 1:0 Reserved, must be kept at reset value.


**14.5.15** **EXTI CPU wake-up with event mask register 2 (EXTI_EMR2)**


This register is only available on STM32C071xx. On the other devices, it is reserved.


Address offset: 0x094


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EM36|Res.|EM34|Res.|Res.|
||||||||||||rw||rw|||



RM0490 Rev 5 275/1027



277


**Extended interrupt and event controller (EXTI)** **RM0490**


Bits 31:5 Reserved, must be kept at reset value.


Bit 4 **EM36:** CPU wake-up with event generation mask on line 36

Setting/clearing this bit unmasks/masks the CPU wake-up with event generation on the line
36.

0: wake-up with event generation masked
1: wake-up with event generation unmasked


Bit 3 Reserved, must be kept at reset value.


Bit 2 **EM34:** CPU wake-up with event generation mask on line 34

Setting/clearing this bit unmasks/masks the CPU wake-up with event generation on the line
34.

0: wake-up with event generation masked
1: wake-up with event generation unmasked


Bits 1:0 Reserved, must be kept at reset value.


**14.5.16** **EXTI register map**


The following table gives the EXTI register map and the reset values.


**Table 62. EXTI controller register map and reset values**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x000|**EXTI_RTSR1**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RT15<br>|RT14<br>|RT13<br>|RT12<br>|RT11<br>|RT10<br>|RT9<br>|RT8<br>|RT7<br>|RT6<br>|RT5<br>|RT4<br>|RT3<br>|RT2<br>|RT1<br>|RT0<br>|
|0x000|~~Reset value~~|||||||||||||||||~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x004|**EXTI_FTSR1**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FT15<br>|FT14<br>|FT13<br>|FT12<br>|FT11<br>|FT10<br>|FT9<br>|FT8<br>|FT7<br>|FT6<br>|FT5<br>|FT4<br>|FT3<br>|FT2<br>|FT1<br>|FT0<br>|
|0x004|~~Reset value~~|||||||||||||||||~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x008|**EXTI_SWIER1**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SWI15<br>|SWI14<br>|SWI13<br>|SWI12<br>|SWI11<br>|SWI10<br>|SWI9<br>|SWI8<br>|SWI7<br>|SWI6<br>|SWI5<br>|SWI4<br>|SWI3<br>|SWI2<br>|SWI1<br>|SWI0<br>|
|0x008|~~Reset value~~|||||||||||||||||~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x00C|**EXTI_RPR1**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RPIF15<br>|RPIF14<br>|RPIF13<br>|RPIF12<br>|RPIF11<br>|RPIF10<br>|RPIF9<br>|RPIF8<br>|RPIF7<br>|RPIF6<br>|RPIF5<br>|RPIF4<br>|RPIF3<br>|RPIF2<br>|RPIF1<br>|RPIF0<br>|
|0x00C|~~Reset value~~|||||||||||||||||~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x010<br>|**EXTI_FPR1**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FPIF15<br>|FPIF14<br>|FPIF13<br>|FPIF12<br>|FPIF11<br>|FPIF10<br>|FPIF9<br>|FPIF8<br>|FPIF7<br>|FPIF6<br>|FPIF5<br>|FPIF4<br>|FPIF3<br>|FPIF2<br>|FPIF1<br>|FPIF0<br>|
|0x010<br>|~~Reset value~~|||||||||||||||||~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|~~0x014-~~<br>0x01C|Reserved|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x020|**EXTI_RTSR2**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RT34<br>|Res.|Res.|
|0x020|~~Reset value~~||||||||||||||||||||||||||||||~~0~~|||
|0x024|**EXTI_FTSR2**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FT34<br>|Res.|Res.|
|0x024|~~Reset value~~||||||||||||||||||||||||||||||~~0~~|||
|0x028|**EXTI_SWIER2**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SWI34<br>|Res.|Res.|
|0x028|~~Reset value~~||||||||||||||||||||||||||||||~~0~~|||



276/1027 RM0490 Rev 5


**RM0490** **Extended interrupt and event controller (EXTI)**


**Table 62. EXTI controller register map and reset values (continued)**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x02C|**EXTI_RPR2**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|RPIF34<br>|Res.|Res.|
|0x02C|~~Reset value~~||||||||||||||||||||||||||||||~~0~~|||
|0x030<br>|**EXTI_FPR2**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|FPIF34<br>|Res.|Res.|
|0x030<br>|~~Reset value~~||||||||||||||||||||||||||||||~~0~~|||
|~~0x034-~~<br>0x05C|Reserved|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x060|**EXTI_EXTICR1**<br>|EXTI3[7:0]<br><br><br><br><br><br><br><br>|EXTI3[7:0]<br><br><br><br><br><br><br><br>|EXTI3[7:0]<br><br><br><br><br><br><br><br>|EXTI3[7:0]<br><br><br><br><br><br><br><br>|EXTI3[7:0]<br><br><br><br><br><br><br><br>|EXTI3[7:0]<br><br><br><br><br><br><br><br>|EXTI3[7:0]<br><br><br><br><br><br><br><br>|EXTI3[7:0]<br><br><br><br><br><br><br><br>|EXTI2[7:0]<br><br><br><br><br><br><br><br>|EXTI2[7:0]<br><br><br><br><br><br><br><br>|EXTI2[7:0]<br><br><br><br><br><br><br><br>|EXTI2[7:0]<br><br><br><br><br><br><br><br>|EXTI2[7:0]<br><br><br><br><br><br><br><br>|EXTI2[7:0]<br><br><br><br><br><br><br><br>|EXTI2[7:0]<br><br><br><br><br><br><br><br>|EXTI2[7:0]<br><br><br><br><br><br><br><br>|EXTI1[7:0]<br><br><br><br><br><br><br><br>|EXTI1[7:0]<br><br><br><br><br><br><br><br>|EXTI1[7:0]<br><br><br><br><br><br><br><br>|EXTI1[7:0]<br><br><br><br><br><br><br><br>|EXTI1[7:0]<br><br><br><br><br><br><br><br>|EXTI1[7:0]<br><br><br><br><br><br><br><br>|EXTI1[7:0]<br><br><br><br><br><br><br><br>|EXTI1[7:0]<br><br><br><br><br><br><br><br>|EXTI0[7:0]<br><br><br><br><br><br><br><br>|EXTI0[7:0]<br><br><br><br><br><br><br><br>|EXTI0[7:0]<br><br><br><br><br><br><br><br>|EXTI0[7:0]<br><br><br><br><br><br><br><br>|EXTI0[7:0]<br><br><br><br><br><br><br><br>|EXTI0[7:0]<br><br><br><br><br><br><br><br>|EXTI0[7:0]<br><br><br><br><br><br><br><br>|EXTI0[7:0]<br><br><br><br><br><br><br><br>|
|0x060|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x064|**EXTI_EXTICR2**<br>|EXTI7[7:0]<br><br><br><br><br><br><br><br>|EXTI7[7:0]<br><br><br><br><br><br><br><br>|EXTI7[7:0]<br><br><br><br><br><br><br><br>|EXTI7[7:0]<br><br><br><br><br><br><br><br>|EXTI7[7:0]<br><br><br><br><br><br><br><br>|EXTI7[7:0]<br><br><br><br><br><br><br><br>|EXTI7[7:0]<br><br><br><br><br><br><br><br>|EXTI7[7:0]<br><br><br><br><br><br><br><br>|EXTI6[7:0]<br><br><br><br><br><br><br><br>|EXTI6[7:0]<br><br><br><br><br><br><br><br>|EXTI6[7:0]<br><br><br><br><br><br><br><br>|EXTI6[7:0]<br><br><br><br><br><br><br><br>|EXTI6[7:0]<br><br><br><br><br><br><br><br>|EXTI6[7:0]<br><br><br><br><br><br><br><br>|EXTI6[7:0]<br><br><br><br><br><br><br><br>|EXTI6[7:0]<br><br><br><br><br><br><br><br>|EXTI5[7:0]<br><br><br><br><br><br><br><br>|EXTI5[7:0]<br><br><br><br><br><br><br><br>|EXTI5[7:0]<br><br><br><br><br><br><br><br>|EXTI5[7:0]<br><br><br><br><br><br><br><br>|EXTI5[7:0]<br><br><br><br><br><br><br><br>|EXTI5[7:0]<br><br><br><br><br><br><br><br>|EXTI5[7:0]<br><br><br><br><br><br><br><br>|EXTI5[7:0]<br><br><br><br><br><br><br><br>|EXTI4[7:0]<br><br><br><br><br><br><br><br>|EXTI4[7:0]<br><br><br><br><br><br><br><br>|EXTI4[7:0]<br><br><br><br><br><br><br><br>|EXTI4[7:0]<br><br><br><br><br><br><br><br>|EXTI4[7:0]<br><br><br><br><br><br><br><br>|EXTI4[7:0]<br><br><br><br><br><br><br><br>|EXTI4[7:0]<br><br><br><br><br><br><br><br>|EXTI4[7:0]<br><br><br><br><br><br><br><br>|
|0x064|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x068|**EXTI_EXTICR3**<br>|EXTI11[7:0]<br><br><br><br><br><br><br><br>|EXTI11[7:0]<br><br><br><br><br><br><br><br>|EXTI11[7:0]<br><br><br><br><br><br><br><br>|EXTI11[7:0]<br><br><br><br><br><br><br><br>|EXTI11[7:0]<br><br><br><br><br><br><br><br>|EXTI11[7:0]<br><br><br><br><br><br><br><br>|EXTI11[7:0]<br><br><br><br><br><br><br><br>|EXTI11[7:0]<br><br><br><br><br><br><br><br>|EXTI10[7:0]<br><br><br><br><br><br><br><br>|EXTI10[7:0]<br><br><br><br><br><br><br><br>|EXTI10[7:0]<br><br><br><br><br><br><br><br>|EXTI10[7:0]<br><br><br><br><br><br><br><br>|EXTI10[7:0]<br><br><br><br><br><br><br><br>|EXTI10[7:0]<br><br><br><br><br><br><br><br>|EXTI10[7:0]<br><br><br><br><br><br><br><br>|EXTI10[7:0]<br><br><br><br><br><br><br><br>|EXTI9[7:0]<br><br><br><br><br><br><br><br>|EXTI9[7:0]<br><br><br><br><br><br><br><br>|EXTI9[7:0]<br><br><br><br><br><br><br><br>|EXTI9[7:0]<br><br><br><br><br><br><br><br>|EXTI9[7:0]<br><br><br><br><br><br><br><br>|EXTI9[7:0]<br><br><br><br><br><br><br><br>|EXTI9[7:0]<br><br><br><br><br><br><br><br>|EXTI9[7:0]<br><br><br><br><br><br><br><br>|EXTI8[7:0]<br><br><br><br><br><br><br><br>|EXTI8[7:0]<br><br><br><br><br><br><br><br>|EXTI8[7:0]<br><br><br><br><br><br><br><br>|EXTI8[7:0]<br><br><br><br><br><br><br><br>|EXTI8[7:0]<br><br><br><br><br><br><br><br>|EXTI8[7:0]<br><br><br><br><br><br><br><br>|EXTI8[7:0]<br><br><br><br><br><br><br><br>|EXTI8[7:0]<br><br><br><br><br><br><br><br>|
|0x068|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x06C<br>|**EXTI_EXTICR4**<br>|EXTI15[7:0]<br><br><br><br><br><br><br><br>|EXTI15[7:0]<br><br><br><br><br><br><br><br>|EXTI15[7:0]<br><br><br><br><br><br><br><br>|EXTI15[7:0]<br><br><br><br><br><br><br><br>|EXTI15[7:0]<br><br><br><br><br><br><br><br>|EXTI15[7:0]<br><br><br><br><br><br><br><br>|EXTI15[7:0]<br><br><br><br><br><br><br><br>|EXTI15[7:0]<br><br><br><br><br><br><br><br>|EXTI14[7:0]<br><br><br><br><br><br><br><br>|EXTI14[7:0]<br><br><br><br><br><br><br><br>|EXTI14[7:0]<br><br><br><br><br><br><br><br>|EXTI14[7:0]<br><br><br><br><br><br><br><br>|EXTI14[7:0]<br><br><br><br><br><br><br><br>|EXTI14[7:0]<br><br><br><br><br><br><br><br>|EXTI14[7:0]<br><br><br><br><br><br><br><br>|EXTI14[7:0]<br><br><br><br><br><br><br><br>|EXTI13[7:0]<br><br><br><br><br><br><br><br>|EXTI13[7:0]<br><br><br><br><br><br><br><br>|EXTI13[7:0]<br><br><br><br><br><br><br><br>|EXTI13[7:0]<br><br><br><br><br><br><br><br>|EXTI13[7:0]<br><br><br><br><br><br><br><br>|EXTI13[7:0]<br><br><br><br><br><br><br><br>|EXTI13[7:0]<br><br><br><br><br><br><br><br>|EXTI13[7:0]<br><br><br><br><br><br><br><br>|EXTI12[7:0]<br><br><br><br><br><br><br><br>|EXTI12[7:0]<br><br><br><br><br><br><br><br>|EXTI12[7:0]<br><br><br><br><br><br><br><br>|EXTI12[7:0]<br><br><br><br><br><br><br><br>|EXTI12[7:0]<br><br><br><br><br><br><br><br>|EXTI12[7:0]<br><br><br><br><br><br><br><br>|EXTI12[7:0]<br><br><br><br><br><br><br><br>|EXTI12[7:0]<br><br><br><br><br><br><br><br>|
|0x06C<br>|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|~~0x070-~~<br>0x07C|Reserved|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x080|**EXTI_IMR1**<br>|IM31<br>|Res.|Res.|Res.|Res.|Res.|IM25<br>|Res.|IM23<br>|Res.|Res.|Res.|IM19<br>|Res.|Res.|Res.|IM15<br>|IM14<br>|IM13<br>|IM12<br>|IM11<br>|IM10<br>|IM9<br>|IM8<br>|IM7<br>|IM6<br>|IM5<br>|IM4<br>|IM3<br>|IM2<br>|IM1<br>|IM0<br>|
|0x080|~~Reset value~~|~~1~~||||||~~1~~||~~1~~||||~~1~~||||~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x084<br>|**EXTI_EMR1**<br>|EM31<br>|Res.|Res.|Res.|Res.|Res.|EM25<br>|Res.|EM23<br>|Res.|Res.|Res.|EM19<br>|Res.|Res.|Res.|EM15<br>|EM14<br>|EM13<br>|EM12<br>|EM11<br>|EM10<br>|EM9<br>|EM8<br>|EM7<br>|EM6<br>|EM5<br>|EM4<br>|EM3<br>|EM2<br>|EM1<br>|EM0<br>|
|0x084<br>|~~Reset value~~|~~0~~||||||~~0~~||~~0~~||||~~0~~||||~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|~~0x088-~~<br>0x08C|Reserved|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x090|**EXTI_IMR2**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|IM36<br>|Res.|IM34<br>|Res.|Res.|
|0x090|~~Reset value~~||||||||||||||||||||||||||||~~0~~||~~0~~|||
|0x094|**EXTI_EMR2**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|EM36<br>|Res.|EM34<br>|Res.|Res.|
|0x094|~~Reset value~~||||||||||||||||||||||||||||~~0~~||~~0~~|||



Refer to _Section 2.2 on page 45_ for the register boundary addresses.


RM0490 Rev 5 277/1027



277


