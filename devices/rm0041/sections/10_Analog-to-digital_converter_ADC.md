**Analog-to-digital converter (ADC)** **RM0041**

# **10 Analog-to-digital converter (ADC)**


**Low-density** **value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 16 and 32 Kbytes.


**Medium-density** **value line** **devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 64 and 128 Kbytes.


**High-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 256 and 512 Kbytes.


This section applies to the whole STM32F100xx family, unless otherwise specified.

## **10.1 ADC introduction**


The 12-bit ADC is a successive approximation analog-to-digital converter. It has up to 18
multiplexed channels allowing it measure signals from sixteen external and two internal
sources. A/D conversion of the various channels can be performed in single, continuous,
scan or discontinuous mode. The result of the ADC is stored in a left-aligned or right-aligned
16-bit data register.


The analog watchdog feature allows the application to detect if the input voltage goes
outside the user-defined high or low thresholds.


The ADC input clock is generated from the PCLK2 clock divided by a prescaler, refer to
_Figure 8: STM32F100xx clock tree (low and medium-density devices)_ and _Figure 9:_
_STM32F100xx clock tree (high-density devices)_ .

## **10.2 ADC main features**


      - 12-bit resolution


      - Interrupt generation at End of Conversion, End of Injected conversion and Analog
watchdog event


      - Single and continuous conversion modes


      - Scan mode for automatic conversion of channel 0 to channel ‘n’


      - Self-calibration


      - Data alignment with in-built data coherency


      - Channel by channel programmable sampling time


      - External trigger option for both regular and injected conversion


      - Discontinuous mode


      - ADC conversion time:


–
STM32F100xx value line devices: 1.17 µs at 24 MHz


      - ADC supply requirement: 2.4 V to 3.6 V


      - ADC input range: V REF- ≤ V IN ≤ V REF+

      - DMA request generation during regular channel conversion


The block diagram of the ADC is shown in _Figure 24_ .


_Note:_ _V_ _REF-_ _, if available (depending on package), must be tied to V_ _SSA_ _._


162/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**

## **10.3 ADC functional description**


_Figure 24_ shows a single ADC block diagramand _Table 57_ gives the ADC pin description.


**Figure 24. Single ADC block diagram**












|Flags|Col2|enable bits Interrupt|
|---|---|---|
|EOC<br>AWD<br><br>JEOC|EOC<br>AWD<br><br>JEOC||
|EOC<br>AWD<br><br>JEOC||~~EOCIE~~<br>|
|EOC<br>AWD<br><br>JEOC||~~AWDIE~~<br>~~JEOCIE~~|


























|Col1|Col2|
|---|---|
|||
||GPIO<br>Ports|
|||

















RM0041 Rev 6 163/709



189


**Analog-to-digital converter (ADC)** **RM0041**


**Table 57. ADC pins**







|Name|Signal type|Remarks|
|---|---|---|
|VREF+|Input, analog reference<br>positive|The higher/positive reference voltage for the ADC,<br>2.4 V≤ VREF+ ≤ VDDA|
|VDDA<br>(1)|Input, analog supply|Analog power supply equal to VDD and<br>2.4 V≤ VDDA≤ 3.6 V|
|VREF-|Input, analog reference<br>negative|The lower/negative reference voltage for the ADC,<br>VREF-= VSSA|
|VSSA<br>(1)|Input, analog supply<br>ground|Ground for analog power supply equal to VSS|
|ADCx_IN[15:0]|Analog signals|Up to 21 analog channels(2)|


1. V DDA and V SSA have to be connected to V DD and V SS, respectively.


2. For full details about the ADC I/O pins, refer to the “Pinouts and pin descriptions” section of the
corresponding device datasheet.


**10.3.1** **ADC on-off control**


The ADC can be powered-on by setting the ADON bit in the ADC_CR2 register. When the
ADON bit is set for the first time, it wakes up the ADC from Power Down mode.


Conversion starts when ADON bit is set for a second time by software after ADC power-up
time (t STAB ).


The conversion can be stopped, and the ADC put in power down mode by resetting the
ADON bit. In this mode the ADC consumes almost no power (only a few µA).


**10.3.2** **ADC clock**


The ADCCLK clock provided by the Clock Controller is synchronous with the PCLK2 (APB2
clock). The RCC controller has a dedicated programmable prescaler for the ADC clock,
refer to _Section 6: Reset and clock control (RCC)_ for more details.


**10.3.3** **Channel selection**


There are 16 multiplexed channels. It is possible to organize the conversions in two groups:
regular and injected. A group consists of a sequence of conversions which can be done on
any channel and in any order. For instance, it is possible to do the conversion in the
following order: Ch3, Ch8, Ch2, Ch2, Ch0, Ch2, Ch2, Ch15.


      - The **regular group** is composed of up to 16 conversions. The regular channels and
their order in the conversion sequence must be selected in the ADC_SQRx registers.
The total number of conversions in the regular group must be written in the L[3:0] bits in
the ADC_SQR1 register.


      - The **injected group** is composed of up to 4 conversions. The injected channels and
their order in the conversion sequence must be selected in the ADC_JSQR register.
The total number of conversions in the injected group must be written in the L[1:0] bits
in the ADC_JSQR register.


If the ADC_SQRx or ADC_JSQR registers are modified during a conversion, the current
conversion is reset and a new start pulse is sent to the ADC to convert the new chosen

group.


164/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**


**Temperature sensor/V** **REFINT** **internal channels**


The temperature sensor is connected to channel ADCx_IN16 and the internal reference
voltage V REFINT is connected to ADCx_IN17. These two internal channels can be selected
and converted as injected or regular channels.


_Note:_ _The sensor and V_ _REFINT_ _are only available on the master ADC1 peripheral._


**10.3.4** **Single conversion mode**


In Single conversion mode the ADC does one conversion. This mode is started either by
setting the ADON bit in the ADC_CR2 register (for a regular channel only) or by external
trigger (for a regular or injected channel), while the CONT bit is 0.


Once the conversion of the selected channel is complete:


      - If a regular channel was converted:


–
The converted data is stored in the 16-bit ADC_DR register


–
The EOC (End Of Conversion) flag is set


–
and an interrupt is generated if the EOCIE is set.


      - If an injected channel was converted:


–
The converted data is stored in the 16-bit ADC_DRJ1 register


–
The JEOC (End Of Conversion Injected) flag is set


–
and an interrupt is generated if the JEOCIE bit is set.


The ADC is then stopped.


**10.3.5** **Continuous conversion mode**


In continuous conversion mode ADC starts another conversion as soon as it finishes one.
This mode is started either by external trigger or by setting the ADON bit in the ADC_CR2
register, while the CONT bit is 1.


After each conversion:


      - If a regular channel was converted:


–
The converted data is stored in the 16-bit ADC_DR register


–
The EOC (End Of Conversion) flag is set


–
An interrupt is generated if the EOCIE is set.


      - If an injected channel was converted:


–
The converted data is stored in the 16-bit ADC_DRJ1 register


–
The JEOC (End Of Conversion Injected) flag is set


–
An interrupt is generated if the JEOCIE bit is set.


**10.3.6** **Timing diagram**


As shown in _Figure 25_, the ADC needs a stabilization time of t STAB before it starts
converting accurately. After the start of ADC conversion and after 14 clock cycles, the EOC
flag is set and the 16-bit ADC Data register contains the result of the conversion.


RM0041 Rev 6 165/709



189


**Analog-to-digital converter (ADC)** **RM0041**


**Figure 25. Timing diagram**



|Col1|Start 1st c|Col3|Start next|
|---|---|---|---|
|||onversion|onversion|
|||ADC conversion|ADC conversion|
||tSTAB|Conversion time<br>(total conv. time)|Conversion time<br>(total conv. time)|
|||||


**10.3.7** **Analog watchdog**







The AWD analog watchdog status bit is set if the analog voltage converted by the ADC is
below a low threshold or above a high threshold. These thresholds are programmed in the
12 least significant bits of the ADC_HTR and ADC_LTR 16-bit registers. An interrupt can be
enabled by using the AWDIE bit in the ADC_CR1 register.


The threshold value is independent of the alignment selected by the ALIGN bit in the
ADC_CR2 register. The comparison is done before the alignment (see _Section 10.5_ ).


The analog watchdog can be enabled on one or more channels by configuring the
ADC_CR1 register as shown in _Table 58._


**Figure 26. Analog watchdog** **guarded area**









**Table 58. Analog watchdog channel selection**







|Channels to be guarded by analog<br>watchdog|ADC_CR1 register control bits (x = don’t care)|Col3|Col4|
|---|---|---|---|
|**Channels to be guarded by analog**<br>**watchdog**|**AWDSGL bit**|**AWDEN bit**|**JAWDEN bit**|
|None|x|0|0|
|All injected channels|0|0|1|
|All regular channels|0|1|0|


166/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**


**Table 58. Analog watchdog channel selection (continued)**







|Channels to be guarded by analog<br>watchdog|ADC_CR1 register control bits (x = don’t care)|Col3|Col4|
|---|---|---|---|
|**Channels to be guarded by analog**<br>**watchdog**|**AWDSGL bit**|**AWDEN bit**|**JAWDEN bit**|
|All regular and injected channels|0|1|1|
|Single(1) injected channel|1|0|1|
|Single(1) regular channel|1|1|0|
|Single(1) regular or injected channel|1|1|1|


1. Selected by AWDCH[4:0] bits


**10.3.8** **Scan mode**


This mode is used to scan a group of analog channels.


Scan mode can be selected by setting the SCAN bit in the ADC_CR1 register. Once this bit
is set, ADC scans all the channels selected in the ADC_SQRx registers (for regular
channels) or in the ADC_JSQR (for injected channels). A single conversion is performed for
each channel of the group. After each end of conversion the next channel of the group is
converted automatically. If the CONT bit is set, conversion does not stop at the last selected
group channel but continues again from the first selected group channel.


When using scan mode, DMA bit must be set and the direct memory access controller is
used to transfer the converted data of regular group channels to SRAM after each update of
the ADC_DR register.


The injected channel converted data is always stored in the ADC_JDRx registers.


**10.3.9** **Injected channel management**


**Triggered injection**


To use triggered injection, the JAUTO bit must be cleared and SCAN bit must be set in the
ADC_CR1 register.


1. Start conversion of a group of regular channels either by external trigger or by setting
the ADON bit in the ADC_CR2 register.


2. If an external injected trigger occurs during the regular group channel conversion, the
current conversion is reset and the injected channel sequence is converted in Scan
once mode.


3. Then, the regular group channel conversion is resumed from the last interrupted
regular conversion. If a regular event occurs during an injected conversion, it doesn’t
interrupt it but the regular sequence is executed at the end of the injected sequence.
_Figure 27_ shows the timing diagram.


_Note:_ _When using triggered injection, the interval between trigger events must be longer than the_
_injection sequence. For instance, if the sequence length is 28 ADC clock cycles (that is two_
_conversions with a 1.5 clock-period sampling time), the minimum interval between triggers_
_must be 29 ADC clock cycles._


RM0041 Rev 6 167/709



189


**Analog-to-digital converter (ADC)** **RM0041**


**Auto-injection**


If the JAUTO bit is set, then the injected group channels are automatically converted after
the regular group channels. This can be used to convert a sequence of up to 20 conversions
programmed in the ADC_SQRx and ADC_JSQR registers.


In this mode, external trigger on injected channels must be disabled.


If the CONT bit is also set in addition to the JAUTO bit, regular channels followed by injected
channels are continuously converted.


For ADC clock prescalers ranging from 4 to 8, a delay of 1 ADC clock period is automatically
inserted when switching from regular to injected sequence (respectively injected to regular).
When the ADC clock prescaler is set to 2, the delay is 2 ADC clock periods.


_Note:_ _It is not possible to use both auto-injected and discontinuous modes simultaneously._


**Figure 27. Injected conversion latency**


1. The maximum latency value can be found in the electrical characteristics of the STM32F101xx and
STM32F103xx datasheets.


**10.3.10** **Discontinuous mode**


**Regular group**


This mode is enabled by setting the DISCEN bit in the ADC_CR1 register. It can be used to
convert a short sequence of n conversions (n <=8) which is a part of the sequence of
conversions selected in the ADC_SQRx registers. The value of n is specified by writing to
the DISCNUM[2:0] bits in the ADC_CR1 register.


When an external trigger occurs, it starts the next n conversions selected in the ADC_SQRx
registers until all the conversions in the sequence are done. The total sequence length is
defined by the L[3:0] bits in the ADC_SQR1 register.


Example:


n = 3, channels to be converted = 0, 1, 2, 3, 6, 7, 9, 10
first trigger: sequence converted 0, 1, 2. An EOC event is generated at each


168/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**


conversion
second trigger: sequence converted 3, 6, 7. An EOC event is generated at each
conversion
third trigger: sequence converted 9, 10. An EOC event is generated at each conversion
fourth trigger: sequence converted 0, 1, 2. An EOC event is generated at each
conversion


_Note:_ _When a regular group is converted in discontinuous mode, no rollover will occur. When all_
_sub groups are converted, the next trigger starts conversion of the first sub-group._


_In the example above, the fourth trigger reconverts the first sub-group channels 0, 1 and 2._


**Injected group**


This mode is enabled by setting the JDISCEN bit in the ADC_CR1 register. It can be used to
convert the sequence selected in the ADC_JSQR register, channel by channel, after an
external trigger event.


When an external trigger occurs, it starts the next channel conversions selected in the
ADC_JSQR registers until all the conversions in the sequence are done. The total sequence
length is defined by the JL[1:0] bits in the ADC_JSQR register.


Example:


n = 1, channels to be converted = 1, 2, 3
first trigger: channel 1 converted
second trigger: channel 2 converted
third trigger: channel 3 converted and EOC and JEOC events generated
fourth trigger: channel 1


_Note:_ _When all injected channels are converted, the next trigger starts the conversion of the first_
_injected channel. In the example above, the fourth trigger reconverts the first injected_
_channel 1._


_It is not possible to use both auto-injected and discontinuous modes simultaneously._


_The user must avoid setting discontinuous mode for both regular and injected groups_
_together. Discontinuous mode must be enabled only for one group conversion._

## **10.4 Calibration**


The ADC has an built-in self calibration mode. Calibration significantly reduces accuracy
errors due to internal capacitor bank variations. During calibration, an error-correction code
(digital word) is calculated for each capacitor, and during all subsequent conversions, the
error contribution of each capacitor is removed using this code.


Calibration is started by setting the CAL bit in the ADC_CR2 register. Once calibration is
over, the CAL bit is reset by hardware and normal conversion can be performed. It is
recommended to calibrate the ADC once at power-on. The calibration codes are stored in
the ADC_DR as soon as the calibration phase ends.


_Note:_ _It is recommended to perform a calibration after each power-up._


_Before starting a calibration, the ADC must have been in power-on state (ADON bit = ‘1’) for_
_at least two ADC clock cycles._


RM0041 Rev 6 169/709



189


**Analog-to-digital converter (ADC)** **RM0041**


**Figure 28. Calibration timing diagram**


## **10.5 Data alignment**





ALIGN bit in the ADC_CR2 register selects the alignment of data stored after conversion.
Data can be left or right aligned as shown in _Figure 29._ and _Figure 30._


The injected group channels converted data value is decreased by the user-defined offset
written in the ADC_JOFRx registers so the result can be a negative value. The SEXT bit is
the extended sign value.


For regular group channels no offset is subtracted so only twelve bits are significant.


**Figure 29. Right alignment of data**













**Figure 30. Left alignment of data**













170/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**

## **10.6 Channel-by-channel programmable sample time**


ADC samples the input voltage for a number of ADC_CLK cycles which can be modified using the SMP[2:0] bits in the ADC_SMPR1 and ADC_SMPR2 registers. Each channel can be
sampled with a different sample time.


The total conversion time is calculated as follows:


Tconv = Sampling time + 12.5 cycles


Example:


With an ADCCLK = 12 MHz and a sampling time of 1.5 cycles:


Tconv = 1.5 + 12.5 = 14 cycles = 1.17 µs

## **10.7 Conversion on external trigger**


Conversion can be triggered by an external event (e.g. timer capture, EXTI line). If the EXTTRIG control bit is set then external events are able to trigger a conversion. The EXTSEL[2:0] and JEXTSEL[2:0] control bits allow the application to select decide which out of 8
possible events can trigger conversion for the regular and injected groups.


_Note:_ _When an external trigger is selected for ADC regular or injected conversion, only the rising_
_edge of the signal can start the conversion._


**Table 59. External trigger for regular channels for ADC1**







|Source|Type|EXTSEL[2:0]|
|---|---|---|
|TIM1_CC1 event|Internal signal from on-chip timers|000|
|TIM1_CC2 event|TIM1_CC2 event|001|
|TIM1_CC3 event|TIM1_CC3 event|010|
|TIM2_CC2 event|TIM2_CC2 event|011|
|TIM3_TRGO event|TIM3_TRGO event|100|
|TIM4_CC4 event|TIM4_CC4 event|101|
|EXTI line 11|External pin|110|
|SWSTART|Software control bit|111|


**Table 60. External trigger for injected channels for ADC1**







|Source|Connection type|JEXTSEL[2:0]|
|---|---|---|
|TIM1_TRGO event|Internal signal from on-chip timers|000|
|TIM1_CC4 event|TIM1_CC4 event|001|
|TIM2_TRGO event|TIM2_TRGO event|010|
|TIM2_CC1 event|TIM2_CC1 event|011|
|TIM3_CC4 event|TIM3_CC4 event|100|
|TIM4_TRGO event|TIM4_TRGO event|101|
|EXTI line 15|External pin|110|
|JSWSTART|Software control bit|111|


RM0041 Rev 6 171/709



189


**Analog-to-digital converter (ADC)** **RM0041**


The software source trigger events can be generated by setting a bit in a register
(SWSTART and JSWSTART in ADC_CR2).


A regular group conversion can be interrupted by an injected trigger.

## **10.8 DMA request**


Since converted regular channels value are stored in a unique data register, it is necessary
to use DMA for conversion of more than one regular channel. This avoids the loss of data
already stored in the ADC_DR register.


Only the end of conversion of a regular channel generates a DMA request, which allows the
transfer of its converted data from the ADC_DR register to the destination location selected
by the user.

## **10.9 Temperature sensor**


The temperature sensor can be used to measure the junction temperature (T J ) of the
device.


The temperature sensor is internally connected to the ADCx_IN16 input channel which is
used to convert the sensor output voltage into a digital value. The recommended sampling
time for the temperature sensor is 17.1 µs.


The block diagram of the temperature sensor is shown in _Figure 31_ .


When not in use, this sensor can be put in power down mode.


_Note:_ _The TSVREFE bit must be set to enable both internal channels: ADCx_IN16 (temperature_
_sensor) and ADCx_IN17 (V_ _REFINT_ _) conversion._


The temperature sensor output voltage changes linearly with temperature. The offset of this
line varies from chip to chip due to process variations (up to 45 °C from one chip to another).


The internal temperature sensor is more suited to applications that detect temperature
variations instead of absolute temperatures. If accurate temperature readings are needed,
an external temperature sensor part should be used.


172/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**


**Figure 31. Temperature sensor and V** **REFINT** **channel block diagram**











RM0041 Rev 6 173/709



189


**Analog-to-digital converter (ADC)** **RM0041**


**Reading the temperature**


To use the sensor:


1. Select the ADCx_IN16 input channel.


2. Select a sample time of 17.1 µs


3. Set the TSVREFE bit in the _ADC control register 2 (ADC_CR2)_ to wake up the
temperature sensor from power down mode.


4. Start the ADC conversion by setting the ADON bit (or by external trigger).


5. Read the resulting V SENSE data in the ADC data register


6. Obtain the temperature using the following formula:


Temperature (in °C) = {(V 25         - V SENSE ) / Avg_Slope} + 25.


Where,


V 25 = V SENSE value for 25° C and


Avg_Slope = Average Slope for curve between Temperature vs. V SENSE (given in
mV/° C or µV/ °C).


Refer to the Electrical characteristics section for the actual values of V 25 and
Avg_Slope.


_Note:_ _The sensor has a startup time after waking from power down mode before it can output_
_V_ _SENSE_ _at the correct level. The ADC also has a startup time after power-on, so to minimize_
_the delay, the ADON and TSVREFE bits should be set at the same time._

## **10.10 ADC interrupts**


An interrupt can be produced on end of conversion for regular and injected groups and
when the analog watchdog status bit is set. Separate interrupt enable bits are available for
flexibility.


Two other flags are present in the ADC_SR register, but there is no interrupt associated with
them:


      - JSTRT (Start of conversion for injected group channels)


      - STRT (Start of conversion for regular group channels)


**Table 61. ADC interrupts**

|Interrupt event|Event flag|Enable Control bit|
|---|---|---|
|End of conversion regular group|EOC|EOCIE|
|End of conversion injected group|JEOC|JEOCIE|
|Analog watchdog status bit is set|AWD|AWDIE|



174/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**

## **10.11 ADC registers**


Refer to _Section 1.1 on page 32_ for a list of abbreviations used in register descriptions.


The peripheral registers have to be accessed by words (32-bit).


**10.11.1** **ADC status register (ADC_SR)**


Address offset: 0x00


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5|4|3|2|1|0|
|---|---|---|---|---|---|
|Reserved|STRT|JSTRT|JEOC|EOC|AWD|
|Reserved|rc_w0|rc_w0|rc_w0|rc_w0|rc_w0|



Bits 31:5 Reserved, must be kept at reset value.


Bit 4 **STRT:** Regular channel Start flag

This bit is set by hardware when regular channel conversion starts. It is cleared by software.
0: No regular channel conversion started
1: Regular channel conversion has started


Bit 3 **JSTRT:** Injected channel Start flag

This bit is set by hardware when injected channel group conversion starts. It is cleared by
software.

0: No injected group conversion started
1: Injected group conversion has started


Bit 2 **JEOC:** Injected channel end of conversion

This bit is set by hardware at the end of all injected group channel conversion. It is cleared
by software.
0: Conversion is not complete
1: Conversion complete


Bit 1 **EOC:** End of conversion

This bit is set by hardware at the end of a group channel conversion (regular or injected). It is
cleared by software or by reading the ADC_DR.
0: Conversion is not complete
1: Conversion complete


Bit 0 **AWD:** Analog watchdog flag

This bit is set by hardware when the converted voltage crosses the values programmed in
the ADC_LTR and ADC_HTR registers. It is cleared by software.
0: No Analog watchdog event occurred
1: Analog watchdog event occurred


RM0041 Rev 6 175/709



189


**Analog-to-digital converter (ADC)** **RM0041**


**10.11.2** **ADC control register 1 (ADC_CR1)**


Address offset: 0x04


Reset value: 0x0000 0000






|31 30 29 28 27 26 25 24|23|22|21 20 19 18 17 16|
|---|---|---|---|
|Reserved|AWDE<br>N|JAWDE<br>N|Reserved|
|Reserved|rw|rw|rw|



|15 14 13|Col2|Col3|12|11|10|9|8|7|6|5|4 3 2 1 0|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DISCNUM[2:0]|DISCNUM[2:0]|DISCNUM[2:0]|JDISCE<br>N|DISC<br>EN|JAUTO|AWD<br>SGL|SCAN|JEOC<br>IE|AWDIE|EOCIE|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


Bits 31:24 Reserved, must be kept at reset value.


Bit 23 **AWDEN:** Analog watchdog enable on regular channels

This bit is set/reset by software.
0: Analog watchdog disabled on regular channels
1: Analog watchdog enabled on regular channels


Bit 22 **JAWDEN:** Analog watchdog enable on injected channels

This bit is set/reset by software.
0: Analog watchdog disabled on injected channels
1: Analog watchdog enabled on injected channels


Bits 21:16 Reserved, must be kept at reset value.


Bits 15:13 **DISCNUM[2:0]** : Discontinuous mode channel count

These bits are written by software to define the number of regular channels to be converted
in discontinuous mode, after receiving an external trigger.

000: 1 channel

001: 2 channels

.......

111: 8 channels


Bit 12 **JDISCEN** : Discontinuous mode on injected channels

This bit set and cleared by software to enable/disable discontinuous mode on injected group
channels

0: Discontinuous mode on injected channels disabled
1: Discontinuous mode on injected channels enabled


Bit 11 **DISCEN** : Discontinuous mode on regular channels

This bit set and cleared by software to enable/disable Discontinuous mode on regular
channels.

0: Discontinuous mode on regular channels disabled
1: Discontinuous mode on regular channels enabled


Bit 10 **JAUTO:** Automatic Injected Group conversion

This bit set and cleared by software to enable/disable automatic injected group conversion
after regular group conversion.
0: Automatic injected group conversion disabled
1: Automatic injected group conversion enabled


176/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**


Bit 9 **AWDSGL:** Enable the watchdog on a single channel in scan mode

This bit set and cleared by software to enable/disable the analog watchdog on the channel
identified by the AWDCH[4:0] bits.
0: Analog watchdog enabled on all channels
1: Analog watchdog enabled on a single channel


Bit 8 **SCAN:** Scan mode

This bit is set and cleared by software to enable/disable Scan mode. In Scan mode, the
inputs selected through the ADC_SQRx or ADC_JSQRx registers are converted.

0: Scan mode disabled

1: Scan mode enabled

_Note: An EOC or JEOC interrupt is generated only on the end of conversion of the last_
_channel if the corresponding EOCIE or JEOCIE bit is set_


Bit 7 **JEOCIE** : Interrupt enable for injected channels

This bit is set and cleared by software to enable/disable the end of conversion interrupt for
injected channels.
0: JEOC interrupt disabled
1: JEOC interrupt enabled. An interrupt is generated when the JEOC bit is set.


Bit 6 **AWDIE** _:_ Analog watchdog interrupt enable

This bit is set and cleared by software to enable/disable the analog watchdog interrupt.
0: Analog watchdog interrupt disabled
1: Analog watchdog interrupt enabled


Bit 5 **EOCIE:** Interrupt enable for EOC

This bit is set and cleared by software to enable/disable the End of Conversion interrupt.
0: EOC interrupt disabled
1: EOC interrupt enabled. An interrupt is generated when the EOC bit is set.


Bits 4:0 **AWDCH[4:0]:** Analog watchdog channel select bits

These bits are set and cleared by software. They select the input channel to be guarded by
the Analog watchdog.
00000: ADC analog Channel0
00001: ADC analog Channel1

....

01111: ADC analog Channel15
10000: ADC analog Channel16
10001: ADC analog Channel17

Other values: reserved.

_ADC1 analog Channel16 and Channel17 are internally connected to the temperature_
_sensor and to V_ _REFINT_ _, respectively._


**10.11.3** **ADC control register 2 (ADC_CR2)**


Address offset: 0x08


Reset value: 0x0000 0000





|31 30 29 28 27 26 25 24|23|22|21|20|19 18 17|Col7|Col8|16|
|---|---|---|---|---|---|---|---|---|
|Reserved|TSVRE<br>FE|SWSTA<br>RT|JSWST<br>ART|EXTTR<br>IG|EXTSEL[2:0]|EXTSEL[2:0]|EXTSEL[2:0]|Res.|
|Reserved|rw|rw|rw|rw|rw|rw|rw||


RM0041 Rev 6 177/709



189


**Analog-to-digital converter (ADC)** **RM0041**







|15|14 13 12|Col3|Col4|11|10 9|8|7 6 5 4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|
|JEXTT<br>RIG|JEXTSEL[2:0]|JEXTSEL[2:0]|JEXTSEL[2:0]|ALIGN|Reserved|DMA|Reserved|RST<br>CAL|CAL|CONT|ADON|
|rw|rw|rw|rw|rw|Res.|rw|rw|rw|rw|rw|rw|


Bits 31:24 Reserved, must be kept at reset value.


Bit 23 **TSVREFE** : Temperature sensor and V REFINT enable
This bit is set and cleared by software to enable/disable the temperature sensor and V REFINT
channel.

0: Temperature sensor and V REFINT channel disabled
1: Temperature sensor and V REFINT channel enabled


Bit 22 **SWSTART** : Start conversion of regular channels

This bit is set by software to start conversion and cleared by hardware as soon as
conversion starts. It starts a conversion of a group of regular channels if SWSTART is
selected as trigger event by the EXTSEL[2:0] bits.

0: Reset state

1: Starts conversion of regular channels


Bit 21 **JSWSTART** : Start conversion of injected channels

This bit is set by software and cleared by software or by hardware as soon as the conversion
starts. It starts a conversion of a group of injected channels (if JSWSTART is selected as
trigger event by the JEXTSEL[2:0] bits.

0: Reset state

1: Starts conversion of injected channels


Bit 20 **EXTTRIG** : External trigger conversion mode for regular channels

This bit is set and cleared by software to enable/disable the external trigger used to start
conversion of a regular channel group.

0: Conversion on external event disabled

1: Conversion on external event enabled


Bits 19:17 **EXTSEL[2:0]** : External event select for regular group

These bits select the external event used to trigger the start of conversion of a regular group:

000: Timer 1 CC1 event

001: Timer 1 CC2 event

010: Timer 1 CC3 event

011: Timer 2 CC2 event

100: Timer 3 TRGO event

101: Timer 4 CC4 event

110: EXTI line 11

111: SWSTART


Bit 16 Reserved, must be kept at reset value.


Bit 15 **JEXTTRIG** : External trigger conversion mode for injected channels

This bit is set and cleared by software to enable/disable the external trigger used to start
conversion of an injected channel group.

0: Conversion on external event disabled

1: Conversion on external event enabled


178/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**


Bits 14:12 **JEXTSEL[2:0]** : External event select for injected group

These bits select the external event used to trigger the start of conversion of an injected

group:

000: Timer 1 TRGO event

001: Timer 1 CC4 event

010: Timer 2 TRGO event

011: Timer 2 CC1 event

100: Timer 3 CC4 event

101: Timer 4 TRGO event

110: EXTI line15

111: JSWSTART


Bit 11 **ALIGN** : Data alignment

This bit is set and cleared by software. Refer to _Figure 29._ and _Figure 30._
0: Right Alignment
1: Left Alignment


Bits 10:9 Reserved, must be kept at reset value.


Bit 8 **DMA** : Direct memory access mode

This bit is set and cleared by software. Refer to the DMA controller chapter for more details.

0: DMA mode disabled

1: DMA mode enabled


Bits 7:4 Reserved, must be kept at reset value.


Bit 3 **RSTCAL:** Reset calibration

This bit is set by software and cleared by hardware. It is cleared after the calibration registers
are initialized.

0: Calibration register initialized.
1: Initialize calibration register.

_Note: If RSTCAL is set when conversion is ongoing, additional cycles are required to clear the_
_calibration registers._


Bit 2 **CAL:** A/D Calibration

This bit is set by software to start the calibration. It is reset by hardware after calibration is
complete.
0: Calibration completed

1: Enable calibration


Bit 1 **CONT:** Continuous conversion

This bit is set and cleared by software. If set conversion takes place continuously till this bit is
reset.

0: Single conversion mode

1: Continuous conversion mode


Bit 0 **ADON** : A/D converter ON / OFF

This bit is set and cleared by software. If this bit holds a value of zero and a 1 is written to it
then it wakes up the ADC from Power Down state.
Conversion starts when this bit holds a value of 1 and a 1 is written to it. The application
should allow a delay of t STAB between power up and start of conversion. Refer to _Figure 25._
0: Disable ADC conversion/calibration and go to power down mode.

1: Enable ADC and to start conversion

_Note: If any other bit in this register apart from ADON is changed at the same time, then_
_conversion is not triggered. This is to prevent triggering an erroneous conversion._


RM0041 Rev 6 179/709



189


**Analog-to-digital converter (ADC)** **RM0041**


**10.11.4** **ADC sample time register 1 (ADC_SMPR1)**


Address offset: 0x0C


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24|23 22 21|Col3|Col4|20 19 18|Col6|Col7|17 16|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|SMP17[2:0]|SMP17[2:0]|SMP17[2:0]|SMP16[2:0]|SMP16[2:0]|SMP16[2:0]|SMP15[2:1]|SMP15[2:1]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14 13 12|Col3|Col4|11 10 9|Col6|Col7|8 7 6|Col9|Col10|5 4 3|Col12|Col13|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SMP<br>15_0|SMP14[2:0]|SMP14[2:0]|SMP14[2:0]|SMP13[2:0]|SMP13[2:0]|SMP13[2:0]|SMP12[2:0]|SMP12[2:0]|SMP12[2:0]|SMP11[2:0]|SMP11[2:0]|SMP11[2:0]|SMP10[2:0]|SMP10[2:0]|SMP10[2:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:24 Reserved, must be kept at reset value.


Bits 23:0 **SMPx[2:0]:** Channel x Sample time selection

These bits are written by software to select the sample time individually for each channel.
During sample cycles channel selection bits must remain unchanged.
000: 1.5 cycles
001: 7.5 cycles
010: 13.5 cycles
011: 28.5 cycles
100: 41.5 cycles
101: 55.5 cycles
110: 71.5 cycles
111: 239.5 cycles

_ADC1 analog Channel16 and Channel 17 are internally connected to the temperature_
_sensor and to V_ _REFINT_ _, respectively._


180/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**


**10.11.5** **ADC sample time register 2 (ADC_SMPR2)**


Address offset: 0x10


Reset value: 0x0000 0000

|31 30|29 28 27|Col3|Col4|26 25 24|Col6|Col7|23 22 21|Col9|Col10|20 19 18|Col12|Col13|17 16|Col15|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|SMP9[2:0]|SMP9[2:0]|SMP9[2:0]|SMP8[2:0]|SMP8[2:0]|SMP8[2:0]|SMP7[2:0]|SMP7[2:0]|SMP7[2:0]|SMP6[2:0]|SMP6[2:0]|SMP6[2:0]|SMP5[2:1]|SMP5[2:1]|
|Res.|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14 13 12|Col3|Col4|11 10 9|Col6|Col7|8 7 6|Col9|Col10|5 4 3|Col12|Col13|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SMP<br>5_0|SMP4[2:0]|SMP4[2:0]|SMP4[2:0]|SMP3[2:0]|SMP3[2:0]|SMP3[2:0]|SMP2[2:0]|SMP2[2:0]|SMP2[2:0]|SMP1[2:0]|SMP1[2:0]|SMP1[2:0]|SMP0[2:0]|SMP0[2:0]|SMP0[2:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:30 Reserved, must be kept at reset value.


Bits 29:0 **SMPx[2:0]:** Channel x Sample time selection

These bits are written by software to select the sample time individually for each channel.
During sample cycles channel selection bits must remain unchanged.
000: 1.5 cycles
001: 7.5 cycles
010: 13.5 cycles
011: 28.5 cycles
100: 41.5 cycles
101: 55.5 cycles
110: 71.5 cycles
111: 239.5 cycles


**10.11.6** **ADC injected channel data offset register x (ADC_JOFRx) (x=1..4)**


Address offset: 0x14-0x20


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12|11 10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:12 Reserved, must be kept at reset value.


Bits 11:0 **JOFFSETx[11:0]** : Data offset for injected channel x

These bits are written by software to define the offset to be subtracted from the raw
converted data when converting injected channels. The conversion result can be read from
in the ADC_JDRx registers.


RM0041 Rev 6 181/709



189


**Analog-to-digital converter (ADC)** **RM0041**


**10.11.7** **ADC watchdog high threshold register (ADC_HTR)**


Address offset: 0x24


Reset value: 0x0000 0FFF


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12|11 10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:12 Reserved, must be kept at reset value.


Bits 11:0 **HT[11:0]:** Analog watchdog high threshold

These bits are written by software to define the high threshold for the analog watchdog.


_Note:_ _The software can write to these registers when an ADC conversion is ongoing. The_
_programmed value will be effective when the next conversion is complete. Writing to this_
_register is performed with a write delay that can create uncertainty on the effective time at_
_which the new value is programmed._


**10.11.8** **ADC watchdog low threshold register (ADC_LTR)**


Address offset: 0x28


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12|11 10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:12 Reserved, must be kept at reset value.


Bits 11:0 **LT[11:0]:** Analog watchdog low threshold

These bits are written by software to define the low threshold for the analog watchdog.


_Note:_ _The software can write to these registers when an ADC conversion is ongoing. The_
_programmed value will be effective when the next conversion is complete. Writing to this_
_register is performed with a write delay that can create uncertainty on the effective time at_
_which the new value is programmed._


182/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**


**10.11.9** **ADC regular sequence register 1 (ADC_SQR1)**


Address offset: 0x2C


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24|23 22 21 20|Col3|Col4|Col5|19 18 17 16|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|L[3:0]|L[3:0]|L[3:0]|L[3:0]|SQ16[4:1]|SQ16[4:1]|SQ16[4:1]|SQ16[4:1]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14 13 12 11 10|Col3|Col4|Col5|Col6|9 8 7 6 5|Col8|Col9|Col10|Col11|4 3 2 1 0|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SQ16_0|SQ15[4:0]|SQ15[4:0]|SQ15[4:0]|SQ15[4:0]|SQ15[4:0]|SQ14[4:0]|SQ14[4:0]|SQ14[4:0]|SQ14[4:0]|SQ14[4:0]|SQ13[4:0]|SQ13[4:0]|SQ13[4:0]|SQ13[4:0]|SQ13[4:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:24 Reserved, must be kept at reset value.


Bits 23:20 **L[3:0]** : Regular channel sequence length

These bits are written by software to define the total number of conversions in the regular
channel conversion sequence.

0000: 1 conversion

0001: 2 conversions

.....

1111: 16 conversions


Bits 19:15 **SQ16[4:0]** : 16th conversion in regular sequence

These bits are written by software with the channel number (0..17) assigned as the 16th in
the conversion sequence.


Bits 14:10 **SQ15[4:0]** : 15th conversion in regular sequence


Bits 9:5 **SQ14[4:0]** : 14th conversion in regular sequence


Bits 4:0 **SQ13[4:0]** : 13th conversion in regular sequence


RM0041 Rev 6 183/709



189


**Analog-to-digital converter (ADC)** **RM0041**


**10.11.10 ADC regular sequence register 2 (ADC_SQR2)**


Address offset: 0x30


Reset value: 0x0000 0000

|31 30|29 28 27 26 25|Col3|Col4|Col5|Col6|24 23 22 21 20|Col8|Col9|Col10|Col11|19 18 17 16|Col13|Col14|Col15|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|SQ12[4:0]|SQ12[4:0]|SQ12[4:0]|SQ12[4:0]|SQ12[4:0]|SQ11[4:0]|SQ11[4:0]|SQ11[4:0]|SQ11[4:0]|SQ11[4:0]|SQ10[4:1]|SQ10[4:1]|SQ10[4:1]|SQ10[4:1]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14 13 12 11 10|Col3|Col4|Col5|Col6|9 8 7 6 5|Col8|Col9|Col10|Col11|4 3 2 1 0|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SQ10_<br>0|SQ9[4:0]|SQ9[4:0]|SQ9[4:0]|SQ9[4:0]|SQ9[4:0]|SQ8[4:0]|SQ8[4:0]|SQ8[4:0]|SQ8[4:0]|SQ8[4:0]|SQ7[4:0]|SQ7[4:0]|SQ7[4:0]|SQ7[4:0]|SQ7[4:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:30 Reserved, must be kept at reset value.


Bits 29:26 **SQ12[4:0]** : _1_ 2th conversion in regular sequence

These bits are written by software with the channel number (0..17) assigned as the 12th in the
sequence to be converted.


Bits 24:20 **SQ11[4:0]** : 11th conversion in regular sequence


Bits 19:15 **SQ10[4:0]** : 10th conversion in regular sequence


Bits 14:10 **SQ9[4:0]:** 9th conversion in regular sequence


Bits 9:5 **SQ8[4:0]** : 8th conversion in regular sequence


Bits 4:0 **SQ7[4:0]** : 7th conversion in regular sequence


184/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**


**10.11.11 ADC regular sequence register 3 (ADC_SQR3)**


Address offset: 0x34


Reset value: 0x0000 0000

|31 30|29 28 27 26 25|Col3|Col4|Col5|Col6|24 23 22 21 20|Col8|Col9|Col10|Col11|19 18 17 16|Col13|Col14|Col15|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|SQ6[4:0]|SQ6[4:0]|SQ6[4:0]|SQ6[4:0]|SQ6[4:0]|SQ5[4:0]|SQ5[4:0]|SQ5[4:0]|SQ5[4:0]|SQ5[4:0]|SQ4[4:1]|SQ4[4:1]|SQ4[4:1]|SQ4[4:1]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14 13 12 11 10|Col3|Col4|Col5|Col6|9 8 7 6 5|Col8|Col9|Col10|Col11|4 3 2 1 0|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SQ4_0|SQ3[4:0]|SQ3[4:0]|SQ3[4:0]|SQ3[4:0]|SQ3[4:0]|SQ2[4:0]|SQ2[4:0]|SQ2[4:0]|SQ2[4:0]|SQ2[4:0]|SQ1[4:0]|SQ1[4:0]|SQ1[4:0]|SQ1[4:0]|SQ1[4:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:30 Reserved, must be kept at reset value.


Bits 29:25 **SQ6[4:0]** : 6th conversion in regular sequence

These bits are written by software with the channel number (0..17) assigned as the 6th in the
sequence to be converted.


Bits 24:20 **SQ5[4:0]:** 5th conversion in regular sequence


Bits 19:15 **SQ4[4:0]** : fourth conversion in regular sequence


Bits 14:10 **SQ3[4:0]** : third conversion in regular sequence


Bits 9:5 **SQ2[4:0]:** second conversion in regular sequence


Bits 4:0 **SQ1[4:0]** : first conversion in regular sequence


RM0041 Rev 6 185/709



189


**Analog-to-digital converter (ADC)** **RM0041**


**10.11.12 ADC injected sequence register (ADC_JSQR)**


Address offset: 0x38


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22|21 20|Col3|19 18 17 16|Col5|Col6|Col7|
|---|---|---|---|---|---|---|
|Reserved|JL[1:0]|JL[1:0]|JSQ4[4:1]|JSQ4[4:1]|JSQ4[4:1]|JSQ4[4:1]|
|Reserved|rw|rw|rw|rw|rw|rw|


|15|14 13 12 11 10|Col3|Col4|Col5|Col6|9 8 7 6 5|Col8|Col9|Col10|Col11|4 3 2 1 0|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|JSQ4_0|JSQ3[4:0]|JSQ3[4:0]|JSQ3[4:0]|JSQ3[4:0]|JSQ3[4:0]|JSQ2[4:0]|JSQ2[4:0]|JSQ2[4:0]|JSQ2[4:0]|JSQ2[4:0]|JSQ1[4:0]|JSQ1[4:0]|JSQ1[4:0]|JSQ1[4:0]|JSQ1[4:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:22 Reserved, must be kept at reset value.


Bits 21:20 **JL[1:0]** : Injected sequence length

These bits are written by software to define the total number of conversions in the injected
channel conversion sequence.

00: 1 conversion

01: 2 conversions

10: 3 conversions

11: 4 conversions


Bits 19:15 **JSQ4[4:0]** : fourth conversion in injected sequence (when JL[1:0] = 3) [(1)]


These bits are written by software with the channel number (0..17) assigned as the fourth in
the sequence to be converted.


_Note: Unlike a regular conversion sequence, if JL[1:0] length is less than four, the channels_
_are converted in a sequence starting from (4-JL). Example: ADC_JSQR[21:0] = 10_
_00011 00011 00111 00010 means that a scan conversion will convert the following_
_channel sequence: 7, 3, 3. (not 2, 7, 3)_


Bits 14:10 **JSQ3[4:0]:** third conversion in injected sequence (when JL[1:0] = 3)


Bits 9:5 **JSQ2[4:0]** : second conversion in injected sequence (when JL[1:0] = 3)


Bits 4:0 **JSQ1[4:0]** : first conversion in injected sequence (when JL[1:0] = 3)


1. When JL=3 ( 4 injected conversions in the sequencer), the ADC converts the channels in this order:
JSQ1[4:0] >> JSQ2[4:0] >> JSQ3[4:0] >> JSQ4[4:0]
When JL=2 ( 3 injected conversions in the sequencer), the ADC converts the channels in this order:
JSQ2[4:0] >> JSQ3[4:0] >> JSQ4[4:0]
When JL=1 ( 2 injected conversions in the sequencer), the ADC converts the channels in this order:
JSQ3[4:0] >> JSQ4[4:0]
When JL=0 (1 injected conversion in the sequencer), the ADC converts only JSQ4[4:0] channel


186/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**


**10.11.13 ADC injected data register x (ADC_JDRx) (x= 1..4)**


Address offset: 0x3C - 0x48


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **JDATA[15:0]** : Injected data

These bits are read only. They contain the conversion result from injected channel x. The
data is left or right-aligned as shown in _Figure 29_ and _Figure 30_ .


**10.11.14 ADC regular data register (ADC_DR)**


Address offset: 0x4C


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **DATA[15:0]** : Regular data

These bits are read only. They contain the conversion result from the regular channels. The
data is left or right-aligned as shown in _Figure 29_ and _Figure 30_ .


RM0041 Rev 6 187/709



189


**Analog-to-digital converter (ADC)** **RM0041**


**10.11.15 ADC register map**


The following table summarizes the ADC registers.


**Table 62. ADC register map and reset values**

































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|ADC_SR<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|STRT<br><br>|JSTRT<br><br>|JEOC<br><br>|EOC<br><br>|AWD<br>|
|0x00|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x04|ADC_CR1<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|AWDEN<br><br>|JAWDEN<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|DISC<br>NUM<br>[2:0]<br><br><br><br>|DISC<br>NUM<br>[2:0]<br><br><br><br>|DISC<br>NUM<br>[2:0]<br><br><br><br>|JDISCEN<br><br>|DISCEN<br><br>|JAUTO<br><br>|AWD SGL<br><br>|SCAN<br><br>|JEOC IE<br><br>|AWDIE<br><br>|EOCIE<br>|AWDCH[4:0]<br><br><br><br><br>|AWDCH[4:0]<br><br><br><br><br>|AWDCH[4:0]<br><br><br><br><br>|AWDCH[4:0]<br><br><br><br><br>|AWDCH[4:0]<br><br><br><br><br>|
|0x04|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x08|ADC_CR2<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|TSVREFE<br><br>|SWSTART<br><br>|JSWSTAR<br><br>|EXTTRIG<br>|EXTSEL<br>[2:0]<br><br><br><br>|EXTSEL<br>[2:0]<br><br><br><br>|EXTSEL<br>[2:0]<br><br><br><br>|Reserved<br>|JEXTTRIG<br>|JEXTSE<br>L<br>[2:0]<br><br><br><br>|JEXTSE<br>L<br>[2:0]<br><br><br><br>|JEXTSE<br>L<br>[2:0]<br><br><br><br>|ALIGN<br>|Reserved<br>|Reserved<br>|DMA<br>|Reserved<br>|Reserved<br>|Reserved<br>|Reserved<br>|RSTCAL<br><br>|CAL<br><br>|CONT<br><br>|ADON<br>|
|0x08|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x0C|ADC_SMPR1<br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x0C|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x10|ADC_SMPR2<br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Sample time bits SMPx_x<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x10|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x14|ADC_JOFR1<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JOFFSET1[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET1[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET1[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET1[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET1[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET1[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET1[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET1[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET1[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET1[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET1[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET1[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|
|0x14|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x18|ADC_JOFR2<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JOFFSET2[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET2[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET2[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET2[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET2[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET2[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET2[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET2[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET2[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET2[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET2[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET2[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|
|0x18|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x1C|ADC_JOFR3<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JOFFSET3[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET3[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET3[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET3[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET3[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET3[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET3[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET3[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET3[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET3[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET3[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET3[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|
|0x1C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x20|ADC_JOFR4<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JOFFSET4[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET4[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET4[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET4[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET4[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET4[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET4[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET4[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET4[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET4[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET4[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|JOFFSET4[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|
|0x20|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x24|ADC_HTR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|HT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|HT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|HT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|HT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|HT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|HT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|HT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|HT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|HT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|HT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|HT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|HT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|
|0x24|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x28|ADC_LTR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|LT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|LT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|LT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|LT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|LT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|LT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|LT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|LT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|LT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|LT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|LT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|LT[11:0]<br><br><br><br><br><br><br><br><br><br><br><br>|
|0x28|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x2C|ADC_SQR1<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|L[3:0]<br><br><br><br>|L[3:0]<br><br><br><br>|L[3:0]<br><br><br><br>|L[3:0]<br><br><br><br>|SQ16[4:0] 16th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ16[4:0] 16th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ16[4:0] 16th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ16[4:0] 16th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ16[4:0] 16th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ15[4:0] 15th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ15[4:0] 15th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ15[4:0] 15th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ15[4:0] 15th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ15[4:0] 15th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ14[4:0] 14th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ14[4:0] 14th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ14[4:0] 14th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ14[4:0] 14th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ14[4:0] 14th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ13[4:0] 13th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ13[4:0] 13th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ13[4:0] 13th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ13[4:0] 13th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ13[4:0] 13th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|
|0x2C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|


188/709 RM0041 Rev 6


**RM0041** **Analog-to-digital converter (ADC)**


**Table 62. ADC register map and reset values (continued)**













































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x30|ADC_SQR2<br>|Reserved|Reserved|SQ12[4:0] 12th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ12[4:0] 12th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ12[4:0] 12th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ12[4:0] 12th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ12[4:0] 12th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ11[4:0] 11th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ11[4:0] 11th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ11[4:0] 11th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ11[4:0] 11th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ11[4:0] 11th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ10[4:0] 10th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ10[4:0] 10th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ10[4:0] 10th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ10[4:0] 10th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ10[4:0] 10th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ9[4:0] 9th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ9[4:0] 9th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ9[4:0] 9th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ9[4:0] 9th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ9[4:0] 9th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ8[4:0] 8th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ8[4:0] 8th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ8[4:0] 8th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ8[4:0] 8th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ8[4:0] 8th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ7[4:0] 7th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ7[4:0] 7th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ7[4:0] 7th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ7[4:0] 7th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ7[4:0] 7th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|
|0x30|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x34|ADC_SQR3<br>|Reserved|Reserved|SQ6[4:0] 6th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ6[4:0] 6th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ6[4:0] 6th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ6[4:0] 6th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ6[4:0] 6th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ5[4:0] 5th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ5[4:0] 5th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ5[4:0] 5th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ5[4:0] 5th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ5[4:0] 5th<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ4[4:0] fourth<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ4[4:0] fourth<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ4[4:0] fourth<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ4[4:0] fourth<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ4[4:0] fourth<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ3[4:0] third<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ3[4:0] third<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ3[4:0] third<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ3[4:0] third<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ3[4:0] third<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ2[4:0] second<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ2[4:0] second<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ2[4:0] second<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ2[4:0] second<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ2[4:0] second<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ1[4:0] first<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ1[4:0] first<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ1[4:0] first<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ1[4:0] first<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|SQ1[4:0] first<br>conversion in<br>regular<br>sequence bits<br><br><br><br><br>|
|0x34|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~<br>|~~0~~<br>|~~0~~<br>|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x38|ADC_JSQR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JL[1:<br>0]<br><br>|JL[1:<br>0]<br><br>|JSQ4[4:0]<br>fourthconversion<br>in injected<br>sequence bits<br><br><br><br><br>|JSQ4[4:0]<br>fourthconversion<br>in injected<br>sequence bits<br><br><br><br><br>|JSQ4[4:0]<br>fourthconversion<br>in injected<br>sequence bits<br><br><br><br><br>|JSQ4[4:0]<br>fourthconversion<br>in injected<br>sequence bits<br><br><br><br><br>|JSQ4[4:0]<br>fourthconversion<br>in injected<br>sequence bits<br><br><br><br><br>|JSQ3[4:0] third<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|JSQ3[4:0] third<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|JSQ3[4:0] third<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|JSQ3[4:0] third<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|JSQ3[4:0] third<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|~~JSQ2[4:0]~~<br>second<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|~~JSQ2[4:0]~~<br>second<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|~~JSQ2[4:0]~~<br>second<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|~~JSQ2[4:0]~~<br>second<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|~~JSQ2[4:0]~~<br>second<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|JSQ1[4:0] first<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|JSQ1[4:0] first<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|JSQ1[4:0] first<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|JSQ1[4:0] first<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|JSQ1[4:0] first<br>conversion in<br>injected<br>sequence bits<br><br><br><br><br>|
|0x38|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x3C|ADC_JDR1<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x3C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x40|ADC_JDR2<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x40|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x44|ADC_JDR3<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x44|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x48|ADC_JDR4<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|JDATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x48|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|
|0x4C|ADC_DR<br>|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|Regular DATA[15:0]<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>|
|0x4C|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~Reset value~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|


Refer to _Table 1 on page 37_ and _Table 2 on page 38_ for the register boundary addresses.


RM0041 Rev 6 189/709



189


