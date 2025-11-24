**RM0091** **Touch sensing controller (TSC)**

# **16 Touch sensing controller (TSC)**


This section applies to STM32F05x, STM32F04x, STM32F07x and STM32F09x devices
only.

## **16.1 Introduction**


The touch sensing controller provides a simple solution for adding capacitive sensing
functionality to any application. Capacitive sensing technology is able to detect finger
presence near an electrode that is protected from direct touch by a dielectric (for example
glass, plastic). The capacitive variation introduced by the finger (or any conductive object) is
measured using a proven implementation based on a surface charge transfer acquisition
principle.


The touch sensing controller is fully supported by the STMTouch touch sensing firmware
library, which is free to use and allows touch sensing functionality to be implemented reliably
in the end application.

## **16.2 TSC main features**


The touch sensing controller has the following main features:


      - Proven and robust surface charge transfer acquisition principle


      - Supports up to 24 capacitive sensing channels


      - Up to 8 capacitive sensing channels can be acquired in parallel offering a very good
response time


      - Spread spectrum feature to improve system robustness in noisy environments


      - Full hardware management of the charge transfer acquisition sequence


      - Programmable charge transfer frequency


      - Programmable sampling capacitor I/O pin


      - Programmable channel I/O pin


      - Programmable max count value to avoid long acquisition when a channel is faulty


      - Dedicated end of acquisition and max count error flags with interrupt capability


      - One sampling capacitor for up to 3 capacitive sensing channels to reduce the system
components


      - Compatible with proximity, touchkey, linear and rotary touch sensor implementation


      - Designed to operate with STMTouch touch sensing firmware library


_Note:_ _The number of capacitive sensing channels is dependent on the size of the packages and_
_subject to IO availability._


RM0091 Rev 10 309/1017



327


**Touch sensing controller (TSC)** **RM0091**

## **16.3 TSC functional description**


**16.3.1** **TSC block diagram**


The block diagram of the touch sensing controller is shown in _Figure 58_ .


**Figure 58. TSC block diagram**











**16.3.2** **Surface charge transfer acquisition overview**


The surface charge transfer acquisition is a proven, robust and efficient way to measure a
capacitance. It uses a minimum number of external components to operate with a single
ended electrode type. This acquisition is designed around an analog I/O group composed of
up to four GPIOs (see _Figure 59_ ). Several analog I/O groups are available to allow the
acquisition of several capacitive sensing channels simultaneously and to support a larger
number of capacitive sensing channels. Within a same analog I/O group, the acquisition of
the capacitive sensing channels is sequential.


One of the GPIOs is dedicated to the sampling capacitor C S . Only one sampling capacitor
I/O per analog I/O group must be enabled at a time.


The remaining GPIOs are dedicated to the electrodes and are commonly called channels.
For some specific needs (such as proximity detection), it is possible to simultaneously
enable more than one channel per analog I/O group.


310/1017 RM0091 Rev 10


**RM0091** **Touch sensing controller (TSC)**


**Figure 59. Surface charge transfer analog I/O group structure**



















_Note:_ _Gx_IOy where x is the analog I/O group number and y the GPIO number within the selected_

_group._


The surface charge transfer acquisition principle consists of charging an electrode
capacitance (C X ) and transferring a part of the accumulated charge into a sampling
capacitor (C S ). This sequence is repeated until the voltage across C S reaches a given
threshold (V IH in our case). The number of charge transfers required to reach the threshold
is a direct representation of the size of the electrode capacitance.


_Table 55_ details the charge transfer acquisition sequence of the capacitive sensing channel
1. States 3 to 7 are repeated until the voltage across C S reaches the given threshold. The
same sequence applies to the acquisition of the other channels. The electrode serial
resistor R S improves the ESD immunity of the solution.


RM0091 Rev 10 311/1017



327


**Touch sensing controller (TSC)** **RM0091**


**Table 55. Acquisition sequence summary**









|State|Gx_IO1<br>(channel)|Gx_IO2<br>(sampling)|Gx_IO3<br>(channel)|Gx_IO4<br>(channel)|State description|
|---|---|---|---|---|---|
|#1|Input floating<br>with analog<br>switch closed|Output open-<br>drain low with<br>analog switch<br>closed|Input floating with analog switch<br>closed|Input floating with analog switch<br>closed|Discharge all CX and<br>CS|
|#2|Input floating|Input floating|Input floating|Input floating|Dead time|
|#3|Output push-<br>pull high|Input floating|Input floating|Input floating|Charge CX1|
|#4|Input floating|Input floating|Input floating|Input floating|Dead time|
|#5|Input floating with analog switch<br>closed|Input floating with analog switch<br>closed|Input floating|Input floating|Charge transfer from<br>CX1to CS|
|#6|Input floating|Input floating|Input floating|Input floating|Dead time|
|#7|Input floating|Input floating|Input floating|Input floating|Measure CS voltage|


_Note:_ _Gx_IOy where x is the analog I/O group number and y the GPIO number within the selected_

_group._


The voltage variation over the time on the sampling capacitor C S is detailed below:


**Figure 60. Sampling capacitor voltage variation**


**16.3.3** **Reset and clocks**


The TSC clock source is the AHB clock (HCLK). Two programmable prescalers are used to
generate the pulse generator and the spread spectrum internal clocks:


      - The pulse generator clock (PGCLK) is defined using the PGPSC[2:0] bits of the
TSC_CR register


      - The spread spectrum clock (SSCLK) is defined using the SSPSC bit of the TSC_CR
register


312/1017 RM0091 Rev 10


**RM0091** **Touch sensing controller (TSC)**


The Reset and Clock Controller (RCC) provides dedicated bits to enable the touch sensing
controller clock and to reset this peripheral. For more information, refer to _Section 6: Reset_
_and clock control (RCC)_ .


**16.3.4** **Charge transfer acquisition sequence**


An example of a charge transfer acquisition sequence is detailed in _Figure 61_ .


**Figure 61. Charge transfer acquisition sequence**



























For higher flexibility, the charge transfer frequency is fully configurable. Both the pulse high
state (charge of C X ) and the pulse low state (transfer of charge from C X to C S ) duration can
be defined using the CTPH[3:0] and CTPL[3:0] bits in the TSC_CR register. The standard
range for the pulse high and low states duration is 500 ns to 2 µs. To ensure a correct
measurement of the electrode capacitance, the pulse high state duration must be set to
ensure that C X is always fully charged.


A dead time where both the sampling capacitor I/O and the channel I/O are in input floating
state is inserted between the pulse high and low states to ensure an optimum charge
transfer acquisition sequence. This state duration is 2 periods of HCLK.


At the end of the pulse high state and if the spread spectrum feature is enabled, a variable
number of periods of the SSCLK clock are added.


The reading of the sampling capacitor I/O, to determine if the voltage across C S has
reached the given threshold, is performed at the end of the pulse low state.


_Note:_ _The following TSC control register configurations are forbidden:_


     - _bits PGPSC are set to ‘000’ and bits CTPL are set to ‘0000’_


     - _bits PGPSC are set to ‘000’ and bits CTPL are set to ‘0001’_


     - _bits PGPSC are set to ‘001’ and bits CTPL are set to ‘0000’_


RM0091 Rev 10 313/1017



327


**Touch sensing controller (TSC)** **RM0091**


**16.3.5** **Spread spectrum feature**


The spread spectrum feature generates a variation of the charge transfer frequency. This is
done to improve the robustness of the charge transfer acquisition in noisy environments and
also to reduce the induced emission. The maximum frequency variation is in the range of
10% to 50% of the nominal charge transfer period. For instance, for a nominal charge
transfer frequency of 250 kHz (4 µs), the typical spread spectrum deviation is 10% (400 ns)
which leads to a minimum charge transfer frequency of ~227 kHz.


In practice, the spread spectrum consists of adding a variable number of SSCLK periods to
the pulse high state using the principle shown below:


**Figure 62. Spread spectrum variation principle**









The table below details the maximum frequency deviation with different HCLK settings:


**Table 56. Spread spectrum deviation versus AHB clock frequency**

|f<br>HCLK|Spread spectrum step|Maximum spread spectrum deviation|
|---|---|---|
|24 MHz|41.6 ns|10666.6 ns|
|48 MHz|20.8 ns|5333.3 ns|



The spread spectrum feature can be disabled/enabled using the SSE bit in the TSC_CR
register. The frequency deviation is also configurable to accommodate the device HCLK
clock frequency and the selected charge transfer frequency through the SSPSC and
SSD[6:0] bits in the TSC_CR register.


**16.3.6** **Max count error**


The max count error prevents long acquisition times resulting from a faulty capacitive
sensing channel. It consists of specifying a maximum count value for the analog I/O group
counters. This maximum count value is specified using the MCV[2:0] bits in the TSC_CR
register. As soon as an acquisition group counter reaches this maximum value, the ongoing
acquisition is stopped and the end of acquisition (EOAF bit) and max count error (MCEF bit)
flags are both set. An interrupt can also be generated if the corresponding end of acquisition
(EOAIE bit) or/and max count error (MCEIE bit) interrupt enable bits are set.


314/1017 RM0091 Rev 10


**RM0091** **Touch sensing controller (TSC)**


**16.3.7** **Sampling capacitor I/O and channel I/O mode selection**


To allow the GPIOs to be controlled by the touch sensing controller, the corresponding
alternate function must be enabled through the standard GPIO registers and the GPIOxAFR
registers.


The GPIOs modes controlled by the TSC are defined using the TSC_IOSCR and
TSC_IOCCR register.


When there is no ongoing acquisition, all the I/Os controlled by the touch sensing controller
are in default state. While an acquisition is ongoing, only unused I/Os (neither defined as
sampling capacitor I/O nor as channel I/O) are in default state. The IODEF bit in the
TSC_CR register defines the configuration of the I/Os which are in default state. The table
below summarizes the configuration of the I/O depending on its mode.


**Table 57. I/O state depending on its mode and IODEF bit value**







|IODEF bit|Acquisition<br>status|Unused I/O<br>mode|Channel I/O<br>mode|Sampling<br>capacitor I/O<br>mode|
|---|---|---|---|---|
|0<br>(output push-pull low)|No|Output push-pull<br>low|Output push-pull<br>low|Output push-pull<br>low|
|0<br>(output push-pull low)|Ongoing|Output push-pull<br>low|-|-|
|1<br>(input floating)|No|Input floating|Input floating|Input floating|
|1<br>(input floating)|Ongoing|Input floating|-|-|


Unused I/O mode


An unused I/O corresponds to a GPIO controlled by the TSC peripheral but not defined as
an electrode I/O nor as a sampling capacitor I/O.


Sampling capacitor I/O mode


To allow the control of the sampling capacitor I/O by the TSC peripheral, the corresponding
GPIO must be first set to alternate output open drain mode and then the corresponding
Gx_IOy bit in the TSC_IOSCR register must be set.


Only one sampling capacitor per analog I/O group must be enabled at a time.


Channel I/O mode


To allow the control of the channel I/O by the TSC peripheral, the corresponding GPIO must
be first set to alternate output push-pull mode and the corresponding Gx_IOy bit in the
TSC_IOCCR register must be set.


For proximity detection where a higher equivalent electrode surface is required or to speedup the acquisition process, it is possible to enable and simultaneously acquire several
channels belonging to the same analog I/O group.


_Note:_ _During the acquisition phase and even if the TSC peripheral alternate function is not_
_enabled, as soon as the TSC_IOSCR or TSC_IOCCR bit is set, the corresponding GPIO_
_analog switch is automatically controlled by the touch sensing controller._


RM0091 Rev 10 315/1017



327


**Touch sensing controller (TSC)** **RM0091**


**16.3.8** **Acquisition mode**


The touch sensing controller offers two acquisition modes:


      - Normal acquisition mode: the acquisition starts as soon as the START bit in the
TSC_CR register is set.


      - Synchronized acquisition mode: the acquisition is enabled by setting the START bit in
the TSC_CR register but only starts upon the detection of a falling edge or a rising
edge and high level on the SYNC input pin. This mode is useful for synchronizing the
capacitive sensing channels acquisition with an external signal without additional CPU
load.


The GxE bits in the TSC_IOGCSR registers specify which analog I/O groups are enabled
(corresponding counter is counting). The C S voltage of a disabled analog I/O group is not
monitored and this group does not participate in the triggering of the end of acquisition flag.
However, if the disabled analog I/O group contains some channels, they are pulsed.


When the C S voltage of an enabled analog I/O group reaches the given threshold, the
corresponding GxS bit of the TSC_IOGCSR register is set. When the acquisition of all
enabled analog I/O groups is complete (all GxS bits of all enabled analog I/O groups are
set), the EOAF flag in the TSC_ISR register is set. An interrupt request is generated if the
EOAIE bit in the TSC_IER register is set.


In the case that a max count error is detected, the ongoing acquisition is stopped and both
the EOAF and MCEF flags in the TSC_ISR register are set. Interrupt requests can be
generated for both events if the corresponding bits (EOAIE and MCEIE bits of the TSCIER
register) are set. Note that when the max count error is detected the remaining GxS bits in
the enabled analog I/O groups are not set.


To clear the interrupt flags, the corresponding EOAIC and MCEIC bits in the TSC_ICR
register must be set.


The analog I/O group counters are cleared when a new acquisition is started. They are
updated with the number of charge transfer cycles generated on the corresponding
channel(s) upon the completion of the acquisition.


For code example refer to the Appendix section _A.18.1: TSC configuration code example_ .


**16.3.9** **I/O hysteresis and analog switch control**


In order to offer a higher flexibility, the touch sensing controller is able to take the control of
the Schmitt trigger hysteresis and analog switch of each Gx_IOy. This control is available
whatever the I/O control mode is (controlled by standard GPIO registers or other
peripherals) assuming that the touch sensing controller is enabled. This may be useful to
perform a different acquisition sequence or for other purposes.


In order to improve the system immunity, the Schmitt trigger hysteresis of the GPIOs
controlled by the TSC must be disabled by resetting the corresponding Gx_IOy bit in the
TSC_IOHCR register.


316/1017 RM0091 Rev 10


**RM0091** **Touch sensing controller (TSC)**

## **16.4 TSC low-power modes**


**Table 58. Effect of low-power modes on TSC**

|Mode|Description|
|---|---|
|Sleep|No effect <br>TSC interrupts cause the device to exit Sleep mode.|
|Stop|TSC registers are frozen <br>The TSC stops its operation until the Stop or Standby mode is exited.|
|Standby|Standby|


## **16.5 TSC interrupts**


**Table 59. Interrupt control bits**

|Interrupt event|Enable<br>control bit|Event flag|Clear flag<br>bit|Exit the<br>Sleep mode|Exit the<br>Stop mode|Exit the<br>Standby mode|
|---|---|---|---|---|---|---|
|End of acquisition|EOAIE|EOAIF|EOAIC|Yes|No|No|
|Max count error|MCEIE|MCEIF|MCEIC|Yes|No|No|



For code example refer to the Appendix section _A.18.2: TSC interrupt code example_ .


RM0091 Rev 10 317/1017



327


**Touch sensing controller (TSC)** **RM0091**

## **16.6 TSC registers**


Refer to _Section 1.2 on page 42_ of the reference manual for a list of abbreviations used in
register descriptions.


The peripheral registers can be accessed by words (32-bit).


**16.6.1** **TSC control register (TSC_CR)**


Address offset: 0x00


Reset value: 0x0000 0000

|31 30 29 28|Col2|Col3|Col4|27 26 25 24|Col6|Col7|Col8|23 22 21 20 19 18 17|Col10|Col11|Col12|Col13|Col14|Col15|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CTPH[3:0]|CTPH[3:0]|CTPH[3:0]|CTPH[3:0]|CTPL[3:0]|CTPL[3:0]|CTPL[3:0]|CTPL[3:0]|SSD[6:0]|SSD[6:0]|SSD[6:0]|SSD[6:0]|SSD[6:0]|SSD[6:0]|SSD[6:0]|SSE|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14 13 12|Col3|Col4|11|10|9|8|7 6 5|Col10|Col11|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SSPSC|PGPSC[2:0]|PGPSC[2:0]|PGPSC[2:0]|Res.|Res.|Res.|Res.|MCV[2:0]|MCV[2:0]|MCV[2:0]|IODEF|SYNC<br>POL|AM|START|TSCE|
|rw|rw|rw|rw|||||rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:28 **CTPH[3:0]** : Charge transfer pulse high

These bits are set and cleared by software. They define the duration of the high state of the
charge transfer pulse (charge of C X ).
0000: 1x t PGCLK
0001: 2x t PGCLK

...

1111: 16x t PGCLK
_Note: These bits must not be modified when an acquisition is ongoing._


Bits 27:24 **CTPL[3:0]** : Charge transfer pulse low

These bits are set and cleared by software. They define the duration of the low state of the
charge transfer pulse (transfer of charge from C X to C S ).
0000: 1x t PGCLK
0001: 2x t PGCLK

...

1111: 16x t PGCLK
_Note: These bits must not be modified when an acquisition is ongoing._

_Note: Some configurations are forbidden. Refer to the Section 16.3.4: Charge transfer_
_acquisition sequence for details._


Bits 23:17 **SSD[6:0]** : Spread spectrum deviation

These bits are set and cleared by software. They define the spread spectrum deviation which
consists in adding a variable number of periods of the SSCLK clock to the charge transfer
pulse high state.
0000000: 1x t SSCLK
0000001: 2x t SSCLK

...

1111111: 128x t SSCLK
_Note: These bits must not be modified when an acquisition is ongoing._


318/1017 RM0091 Rev 10


**RM0091** **Touch sensing controller (TSC)**


Bit 16 **SSE** : Spread spectrum enable

This bit is set and cleared by software to enable/disable the spread spectrum feature.
0: Spread spectrum disabled
1: Spread spectrum enabled

_Note: This bit must not be modified when an acquisition is ongoing._


Bit 15 **SSPSC** : Spread spectrum prescaler

This bit is set and cleared by software. It selects the AHB clock divider used to generate the
spread spectrum clock (SSCLK).
0: f HCLK
1: f HCLK /2
_Note: This bit must not be modified when an acquisition is ongoing._


Bits 14:12 **PGPSC[2:0]** : Pulse generator prescaler

These bits are set and cleared by software.They select the AHB clock divider used to
generate the pulse generator clock (PGCLK).
000: f HCLK
001: f HCLK /2
010: f HCLK /4
011: f HCLK /8
100: f HCLK /16
101: f HCLK /32
110: f HCLK /64
111: f HCLK /128
_Note: These bits must not be modified when an acquisition is ongoing._

_Note: Some configurations are forbidden. Refer to the Section 16.3.4: Charge transfer_
_acquisition sequence for details._


Bits 11:8 Reserved, must be kept at reset value.


Bits 7:5 **MCV[2:0]** : Max count value

These bits are set and cleared by software. They define the maximum number of charge
transfer pulses that can be generated before a max count error is generated.

000: 255

001: 511

010: 1023

011: 2047

100: 4095

101: 8191

110: 16383

111: reserved

_Note: These bits must not be modified when an acquisition is ongoing._


Bit 4 **IODEF** : I/O Default mode

This bit is set and cleared by software. It defines the configuration of all the TSC I/Os when
there is no ongoing acquisition. When there is an ongoing acquisition, it defines the
configuration of all unused I/Os (not defined as sampling capacitor I/O or as channel I/O).
0: I/Os are forced to output push-pull low
1: I/Os are in input floating

_Note: This bit must not be modified when an acquisition is ongoing._


Bit 3 **SYNCPOL** : Synchronization pin polarity

This bit is set and cleared by software to select the polarity of the synchronization input pin.
0: Falling edge only
1: Rising edge and high level


RM0091 Rev 10 319/1017



327


**Touch sensing controller (TSC)** **RM0091**


Bit 2 **AM** : Acquisition mode

This bit is set and cleared by software to select the acquisition mode.
0: Normal acquisition mode (acquisition starts as soon as START bit is set)
1: Synchronized acquisition mode (acquisition starts if START bit is set and when the
selected signal is detected on the SYNC input pin)

_Note: This bit must not be modified when an acquisition is ongoing._


Bit 1 **START** : Start a new acquisition

This bit is set by software to start a new acquisition. It is cleared by hardware as soon as the
acquisition is complete or by software to cancel the ongoing acquisition.
0: Acquisition not started
1: Start a new acquisition


Bit 0 **TSCE** : Touch sensing controller enable

This bit is set and cleared by software to enable/disable the touch sensing controller.
0: Touch sensing controller disabled
1: Touch sensing controller enabled

_Note: When the touch sensing controller is disabled, TSC registers settings have no effect._


**16.6.2** **TSC interrupt enable register (TSC_IER)**


Address offset: 0x04


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|MCEIE|EOAIE|
|||||||||||||||rw|rw|



Bits 31:2 Reserved, must be kept at reset value.


Bit 1 **MCEIE** : Max count error interrupt enable

This bit is set and cleared by software to enable/disable the max count error interrupt.
0: Max count error interrupt disabled
1: Max count error interrupt enabled


Bit 0 **EOAIE** : End of acquisition interrupt enable

This bit is set and cleared by software to enable/disable the end of acquisition interrupt.
0: End of acquisition interrupt disabled
1: End of acquisition interrupt enabled


320/1017 RM0091 Rev 10


**RM0091** **Touch sensing controller (TSC)**


**16.6.3** **TSC interrupt clear register (TSC_ICR)**


Address offset: 0x08


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|MCEIC|EOAIC|
|||||||||||||||rw|rw|



Bits 31:2 Reserved, must be kept at reset value.


Bit 1 **MCEIC** : Max count error interrupt clear

This bit is set by software to clear the max count error flag and it is cleared by hardware
when the flag is reset. Writing a ‘0’ has no effect.

0: No effect

1: Clears the corresponding MCEF of the TSC_ISR register


Bit 0 **EOAIC** : End of acquisition interrupt clear

This bit is set by software to clear the end of acquisition flag and it is cleared by hardware
when the flag is reset. Writing a ‘0’ has no effect.

0: No effect

1: Clears the corresponding EOAF of the TSC_ISR register


RM0091 Rev 10 321/1017



327


**Touch sensing controller (TSC)** **RM0091**


**16.6.4** **TSC interrupt status register (TSC_ISR)**


Address offset: 0x0C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|MCEF|EOAF|
|||||||||||||||r|r|



Bits 31:2 Reserved, must be kept at reset value.


Bit 1 **MCEF** : Max count error flag

This bit is set by hardware as soon as an analog I/O group counter reaches the max count
value specified. It is cleared by software writing 1 to the bit MCEIC of the TSC_ICR register.
0: No max count error (MCE) detected
1: Max count error (MCE) detected


Bit 0 **EOAF** : End of acquisition flag

This bit is set by hardware when the acquisition of all enabled group is complete (all GxS bits
of all enabled analog I/O groups are set or when a max count error is detected). It is cleared
by software writing 1 to the bit EOAIC of the TSC_ICR register.
0: Acquisition is ongoing or not started
1: Acquisition is complete


**16.6.5** **TSC I/O hysteresis control register (TSC_IOHCR)**


Address offset: 0x10


Reset value: 0xFFFF FFFF

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|G8_IO4|G8_IO3|G8_IO2|G8_IO1|G7_IO4|G7_IO3|G7_IO2|G7_IO1|G6_IO4|G6_IO3|G6_IO2|G6_IO1|G5_IO4|G5_IO3|G5_IO2|G5_IO1|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|G4_IO4|G4_IO3|G4_IO2|G4_IO1|G3_IO4|G3_IO3|G3_IO2|G3_IO1|G2_IO4|G2_IO3|G2_IO2|G2_IO1|G1_IO4|G1_IO3|G1_IO2|G1_IO1|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **Gx_IOy** : Gx_IOy Schmitt trigger hysteresis mode, x = 8 to 1, y = 4 to 1.

These bits are set and cleared by software to enable/disable the Gx_IOy Schmitt trigger
hysteresis.
0: Gx_IOy Schmitt trigger hysteresis disabled
1: Gx_IOy Schmitt trigger hysteresis enabled

_Note: These bits control the I/O Schmitt trigger hysteresis whatever the I/O control mode is_
_(even if controlled by standard GPIO registers)._


322/1017 RM0091 Rev 10


**RM0091** **Touch sensing controller (TSC)**


**16.6.6** **TSC I/O analog switch control register**
**(TSC_IOASCR)**


Address offset: 0x18


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|G8_IO4|G8_IO3|G8_IO2|G8_IO1|G7_IO4|G7_IO3|G7_IO2|G7_IO1|G6_IO4|G6_IO3|G6_IO2|G6_IO1|G5_IO4|G5_IO3|G5_IO2|G5_IO1|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|G4_IO4|G4_IO3|G4_IO2|G4_IO1|G3_IO4|G3_IO3|G3_IO2|G3_IO1|G2_IO4|G2_IO3|G2_IO2|G2_IO1|G1_IO4|G1_IO3|G1_IO2|G1_IO1|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **Gx_IOy** : Gx_IOy analog switch enable

These bits are set and cleared by software to enable/disable the Gx_IOy analog switch.
0: Gx_IOy analog switch disabled (opened)
1: Gx_IOy analog switch enabled (closed)

_Note: These bits control the I/O analog switch whatever the I/O control mode is (even if_
_controlled by standard GPIO registers)._


**16.6.7** **TSC I/O sampling control register (TSC_IOSCR)**


Address offset: 0x20


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|G8_IO4|G8_IO3|G8_IO2|G8_IO1|G7_IO4|G7_IO3|G7_IO2|G7_IO1|G6_IO4|G6_IO3|G6_IO2|G6_IO1|G5_IO4|G5_IO3|G5_IO2|G5_IO1|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|G4_IO4|G4_IO3|G4_IO2|G4_IO1|G3_IO4|G3_IO3|G3_IO2|G3_IO1|G2_IO4|G2_IO3|G2_IO2|G2_IO1|G1_IO4|G1_IO3|G1_IO2|G1_IO1|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **Gx_IOy** : Gx_IOy sampling mode

These bits are set and cleared by software to configure the Gx_IOy as a sampling capacitor
I/O. Only one I/O per analog I/O group must be defined as sampling capacitor.
0: Gx_IOy unused
1: Gx_IOy used as sampling capacitor

_Note: These bits must not be modified when an acquisition is ongoing._

_During the acquisition phase and even if the TSC peripheral alternate function is not_
_enabled, as soon as the TSC_IOSCR bit is set, the corresponding GPIO analog switch_
_is automatically controlled by the touch sensing controller._


RM0091 Rev 10 323/1017



327


**Touch sensing controller (TSC)** **RM0091**


**16.6.8** **TSC I/O channel control register (TSC_IOCCR)**


Address offset: 0x28


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|G8_IO4|G8_IO3|G8_IO2|G8_IO1|G7_IO4|G7_IO3|G7_IO2|G7_IO1|G6_IO4|G6_IO3|G6_IO2|G6_IO1|G5_IO4|G5_IO3|G5_IO2|G5_IO1|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|G4_IO4|G4_IO3|G4_IO2|G4_IO1|G3_IO4|G3_IO3|G3_IO2|G3_IO1|G2_IO4|G2_IO3|G2_IO2|G2_IO1|G1_IO4|G1_IO3|G1_IO2|G1_IO1|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **Gx_IOy** : Gx_IOy channel mode

These bits are set and cleared by software to configure the Gx_IOy as a channel I/O.
0: Gx_IOy unused
1: Gx_IOy used as channel

_Note: These bits must not be modified when an acquisition is ongoing._

_During the acquisition phase and even if the TSC peripheral alternate function is not_
_enabled, as soon as the TSC_IOCCR bit is set, the corresponding GPIO analog switch_
_is automatically controlled by the touch sensing controller._


**16.6.9** **TSC I/O group control status register (TSC_IOGCSR)**


Address offset: 0x30


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|G8S|G7S|G6S|G5S|G4S|G3S|G2S|G1S|
|||||||||r|r|r|r|r|r|r|r|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|G8E|G7E|G6E|G5E|G4E|G3E|G2E|G1E|
|||||||||rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:24 Reserved, must be kept at reset value.


Bits 23:16 **GxS** : Analog I/O group x status

These bits are set by hardware when the acquisition on the corresponding enabled analog
I/O group x is complete. They are cleared by hardware when a new acquisition is started.
0: Acquisition on analog I/O group x is ongoing or not started
1: Acquisition on analog I/O group x is complete

_Note: When a max count error is detected the remaining GxS bits of the enabled analog I/O_
_groups are not set._


Bits 15:8 Reserved, must be kept at reset value.


Bits 7:0 **GxE** : Analog I/O group x enable

These bits are set and cleared by software to enable/disable the acquisition (counter is
counting) on the corresponding analog I/O group x.
0: Acquisition on analog I/O group x disabled
1: Acquisition on analog I/O group x enabled


324/1017 RM0091 Rev 10


**RM0091** **Touch sensing controller (TSC)**


**16.6.10** **TSC I/O group x counter register (TSC_IOGxCR)**


x represents the analog I/O group number.


Address offset: 0x30 + 0x04 * x, (x = 1 to 8)


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|
|||r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:14 Reserved, must be kept at reset value.


Bits 13:0 **CNT[13:0]** : Counter value

These bits represent the number of charge transfer cycles generated on the analog I/O
group x to complete its acquisition (voltage across C S has reached the threshold).


RM0091 Rev 10 325/1017



327


**Touch sensing controller (TSC)** **RM0091**


**16.6.11** **TSC register map**


**Table 60. TSC register map and reset values**



















|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x0000|**TSC_CR**|CTPH[3:0]|CTPH[3:0]|CTPH[3:0]|CTPH[3:0]|CTPL[3:0]|CTPL[3:0]|CTPL[3:0]|CTPL[3:0]|SSD[6:0]|SSD[6:0]|SSD[6:0]|SSD[6:0]|SSD[6:0]|SSD[6:0]|SSD[6:0]|SSE|SSPSC|PGPSC[2:0]|PGPSC[2:0]|PGPSC[2:0]|Res.|Res.|Res.|Res.|MCV<br>[2:0]|MCV<br>[2:0]|MCV<br>[2:0]|IODEF|SYNCPOL|AM|START|TSCE|
|0x0000|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|||||0|0|0|0|0|0|0|0|
|0x0004|**TSC_IER**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|MCEIE|EOAIE|
|0x0004|Reset value|||||||||||||||||||||||||||||||0|0|
|0x0008|**TSC_ICR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|MCEIC|EOAIC|
|0x0008|Reset value|||||||||||||||||||||||||||||||0|0|
|0x000C|**TSC_ISR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|MCEF|EOAF|
|0x000C|Reset value|||||||||||||||||||||||||||||||0|0|
|0x0010|**TSC_IOHCR**|G8_IO4|G8_IO3|G8_IO2|G8_IO1|G7_IO4|G7_IO3|G7_IO2|G7_IO1|G6_IO4|G6_IO3|G6_IO2|G6_IO1|G5_IO4|G5_IO3|G5_IO2|G5_IO1|G4_IO4|G4_IO3|G4_IO2|G4_IO1|G3_IO4|G3_IO3|G3_IO2|G3_IO1|G2_IO4|G2_IO3|G2_IO2|G2_IO1|G1_IO4|G1_IO3|G1_IO2|G1_IO1|
|0x0010|Reset value|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|
|0x0014|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x0018|**TSC_IOASCR**|G8_IO4|G8_IO3|G8_IO2|G8_IO1|G7_IO4|G7_IO3|G7_IO2|G7_IO1|G6_IO4|G6_IO3|G6_IO2|G6_IO1|G5_IO4|G5_IO3|G5_IO2|G5_IO1|G4_IO4|G4_IO3|G4_IO2|G4_IO1|G3_IO4|G3_IO3|G3_IO2|G3_IO1|G2_IO4|G2_IO3|G2_IO2|G2_IO1|G1_IO4|G1_IO3|G1_IO2|G1_IO1|
|0x0018|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x001C|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x0020|**TSC_IOSCR**|G8_IO4|G8_IO3|G8_IO2|G8_IO1|G7_IO4|G7_IO3|G7_IO2|G7_IO1|G6_IO4|G6_IO3|G6_IO2|G6_IO1|G5_IO4|G5_IO3|G5_IO2|G5_IO1|G4_IO4|G4_IO3|G4_IO2|G4_IO1|G3_IO4|G3_IO3|G3_IO2|G3_IO1|G2_IO4|G2_IO3|G2_IO2|G2_IO1|G1_IO4|G1_IO3|G1_IO2|G1_IO1|
|0x0020|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0024|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x0028|**TSC_IOCCR**|G8_IO4|G8_IO3|G8_IO2|G8_IO1|G7_IO4|G7_IO3|G7_IO2|G7_IO1|G6_IO4|G6_IO3|G6_IO2|G6_IO1|G5_IO4|G5_IO3|G5_IO2|G5_IO1|G4_IO4|G4_IO3|G4_IO2|G4_IO1|G3_IO4|G3_IO3|G3_IO2|G3_IO1|G2_IO4|G2_IO3|G2_IO2|G2_IO1|G1_IO4|G1_IO3|G1_IO2|G1_IO1|
|0x0028|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x002C|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x0030|**TSC_IOGCSR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|G8S|G7S|G6S|G5S|G4S|G3S|G2S|G1S|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|G8E|G7E|G6E|G5E|G4E|G3E|G2E|G1E|
|0x0030|Reset value|||||||||0|0|0|0|0|0|0|0|||||||||0|0|0|0|0|0|0|0|
|0x0034|**TSC_IOG1CR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|
|0x0034|Reset value|||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0038|**TSC_IOG2CR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|
|0x0038|Reset value|||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|


326/1017 RM0091 Rev 10


**RM0091** **Touch sensing controller (TSC)**


**Table 60. TSC register map and reset values (continued)**





































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x003C|**TSC_IOG3CR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|
|0x003C|Reset value|||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0040|**TSC_IOG4CR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|
|0x0040|Reset value|||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0044|**TSC_IOG5CR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|
|0x0044|Reset value|||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0048|**TSC_IOG6CR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|
|0x0048|Reset value|||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x004C|**TSC_IOG7CR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|
|0x004C|Reset value|||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0050|**TSC_IOG8CR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|CNT[13:0]|
|0x0050|Reset value|||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|


Refer to _Section 2.2 on page 46_ for the register boundary addresses.


RM0091 Rev 10 327/1017



327


