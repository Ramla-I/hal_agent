**RM0090** **Analog-to-digital converter (ADC)**

# **13 Analog-to-digital converter (ADC)**


This section applies to the whole STM32F4xx family, unless otherwise specified.

## **13.1 ADC introduction**


The 12-bit ADC is a successive approximation analog-to-digital converter. It has up to 19
multiplexed channels allowing it to measure signals from 16 external sources, two internal
sources, and the V BAT channel. The A/D conversion of the channels can be performed in
single, continuous, scan or discontinuous mode. The result of the ADC is stored into a leftor right-aligned 16-bit data register.


The analog watchdog feature allows the application to detect if the input voltage goes
beyond the user-defined, higher or lower thresholds.

## **13.2 ADC main features**


      - 12-bit, 10-bit, 8-bit or 6-bit configurable resolution


      - Interrupt generation at the end of conversion, end of injected conversion, and in case of
analog watchdog or overrun events


      - Single and continuous conversion modes


      - Scan mode for automatic conversion of channel 0 to channel ‘n’


      - Data alignment with in-built data coherency


      - Channel-wise programmable sampling time


      - External trigger option with configurable polarity for both regular and injected
conversions


      - Discontinuous mode


      - Dual/Triple mode (on devices with 2 ADCs or more)


      - Configurable DMA data storage in Dual/Triple ADC mode


      - Configurable delay between conversions in Dual/Triple interleaved mode


      - ADC conversion type (refer to the datasheets)


      - ADC supply requirements: 2.4 V to 3.6 V at full speed and down to 1.8 V at slower
speed


      - ADC input range: V REF _–_ ≤ V IN ≤ V REF+

      - DMA request generation during regular channel conversion


_Figure 44_ shows the block diagram of the ADC.


_Note:_ _V_ _REF–_ _, if available (depending on package), must be tied to V_ _SSA_ _._


RM0090 Rev 21 391/1757



435


**Analog-to-digital converter (ADC)** **RM0090**

## **13.3 ADC functional description**


_Figure 44_ shows a single ADC block diagram and _Table 66_ gives the ADC pin description.


**Figure 44. Single ADC block diagram**


















|Flags|Col2|enable bit Interrupt|
|---|---|---|
||||
|EOC<br>~~OVR~~||EOCIE<br>~~OVRIE~~|
||||
|JEOC||JEOCIE|
|AWD|AWD|AWDIE|
































|Col1|Col2|Col3|
|---|---|---|
||||
|||GPIO<br>ports|
||||

























392/1757 RM0090 Rev 21






**RM0090** **Analog-to-digital converter (ADC)**


**Table 66. ADC pins**

|Name|Signal type|Remarks|
|---|---|---|
|VREF+|Input, analog reference<br>positive|The higher/positive reference voltage for the ADC,<br>1.8 V≤ VREF+ ≤ VDDA|
|VDDA|Input, analog supply|Analog power supply equal to VDD and<br>2.4 V≤ VDDA≤ VDD (3.6 V) for full speed<br>1.8 V≤ VDDA≤ VDD (3.6 V) for reduced speed|
|VREF–|Input, analog reference<br>negative|The lower/negative reference voltage for the ADC,<br>VREF–= VSSA|
|VSSA|Input, analog supply<br>ground|Ground for analog power supply equal to VSS|
|ADCx_IN[15:0]|Analog input signals|16 analog input channels|



**13.3.1** **ADC on-off control**


The ADC is powered on by setting the ADON bit in the ADC_CR2 register. When the ADON
bit is set for the first time, it wakes up the ADC from the Power-down mode.


Conversion starts when either the SWSTART or the JSWSTART bit is set.


You can stop conversion and put the ADC in power down mode by clearing the ADON bit. In
this mode the ADC consumes almost no power (only a few µA).


**13.3.2** **ADC clock**


The ADC features two clock schemes:


      - Clock for the analog circuitry: ADCCLK, common to all ADCs


This clock is generated from the APB2 clock divided by a programmable prescaler that
allows the ADC to work at f PCLK2 /2, /4, /6 or /8. Refer to the datasheets for the
maximum value of ADCCLK.


      - Clock for the digital interface (used for registers read/write access)


This clock is equal to the APB2 clock. The digital interface clock can be
enabled/disabled individually for each ADC through the RCC APB2 peripheral clock
enable register (RCC_APB2ENR).


**13.3.3** **Channel selection**


There are 16 multiplexed channels. It is possible to organize the conversions in two groups:
regular and injected. A group consists of a sequence of conversions that can be done on
any channel and in any order. For instance, it is possible to implement the conversion
sequence in the following order: ADC_IN3, ADC_IN8, ADC_IN2, ADC_IN2, ADC_IN0,
ADC_IN2, ADC_IN2, ADC_IN15.


      - A **regular group** is composed of up to 16 conversions. The regular channels and their
order in the conversion sequence must be selected in the ADC_SQRx registers. The
total number of conversions in the regular group must be written in the L[3:0] bits in the
ADC_SQR1 register.


      - An **injected group** is composed of up to 4 conversions. The injected channels and
their order in the conversion sequence must be selected in the ADC_JSQR register.


RM0090 Rev 21 393/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


The total number of conversions in the injected group must be written in the L[1:0] bits
in the ADC_JSQR register.


If the ADC_SQRx or ADC_JSQR registers are modified during a conversion, the current
conversion is reset and a new start pulse is sent to the ADC to convert the newly chosen

group.


**Temperature sensor, V** **REFINT** **and V** **BAT** **internal channels**


      - For the STM32F40x and STM32F41x devices, the temperature sensor is internally
connected to channel ADC1_IN16.


The internal reference voltage VREFINT is connected to ADC1_IN17.


      - For the STM32F42x and STM32F43x devices, the temperature sensor is internally
connected to ADC1_IN18 channel which is shared with VBAT. Only one conversion,
temperature sensor or VBAT, must be selected at a time. When the temperature sensor
and VBAT conversion are set simultaneously, only the VBAT conversion is performed.


The internal reference voltage VREFINT is connected to ADC1_IN17.


The V BAT channel (connected to channel ADC1_IN18) can also be converted as an injected
or regular channel.


_Note:_ _The temperature sensor, V_ _REFINT_ _and the V_ _BAT_ _channel are available only on the master_
_ADC1 peripheral._


**13.3.4** **Single conversion mode**


In Single conversion mode the ADC does one conversion. This mode is started with the
CONT bit at 0 by either:


      - setting the SWSTART bit in the ADC_CR2 register (for a regular channel only)


      - setting the JSWSTART bit (for an injected channel)


      - external trigger (for a regular or injected channel)


Once the conversion of the selected channel is complete:


      - If a regular channel was converted:


–
The converted data are stored into the 16-bit ADC_DR register


–
The EOC (end of conversion) flag is set


–
An interrupt is generated if the EOCIE bit is set


      - If an injected channel was converted:


–
The converted data are stored into the 16-bit ADC_JDR1 register


–
The JEOC (end of conversion injected) flag is set


–
An interrupt is generated if the JEOCIE bit is set


Then the ADC stops.


394/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


**13.3.5** **Continuous conversion mode**


In continuous conversion mode, the ADC starts a new conversion as soon as it finishes one.
This mode is started with the CONT bit at 1 either by external trigger or by setting the
SWSTART bit in the ADC_CR2 register (for regular channels only).


After each conversion:


      - If a regular group of channels was converted:


–
The last converted data are stored into the 16-bit ADC_DR register


–
The EOC (end of conversion) flag is set


–
An interrupt is generated if the EOCIE bit is set


_Note:_ _Injected channels cannot be converted continuously. The only exception is when an injected_
_channel is configured to be converted automatically after regular channels in continuous_
_mode (using JAUTO bit), refer to Auto-injection section)_ **.**


**13.3.6** **Timing diagram**


As shown in _Figure 45_, the ADC needs a stabilization time of t STAB before it starts
converting accurately. After the start of the ADC conversion and after 15 clock cycles, the
EOC flag is set and the 16-bit ADC data register contains the result of the conversion.


**Figure 45. Timing diagram**



|Col1|Start 1st c|Col3|Start next|
|---|---|---|---|
|||onversion|onversion|
|||ADC conversion|ADC conversion|
||tSTAB|Conversion time<br>(total conv. time)|Conversion time<br>(total conv. time)|
|||||


**13.3.7** **Analog watchdog**







The AWD analog watchdog status bit is set if the analog voltage converted by the ADC is
below a lower threshold or above a higher threshold. These thresholds are programmed in
the 12 least significant bits of the ADC_HTR and ADC_LTR 16-bit registers. An interrupt can
be enabled by using the AWDIE bit in the ADC_CR1 register.


The threshold value is independent of the alignment selected by the ALIGN bit in the
ADC_CR2 register. The analog voltage is compared to the lower and higher thresholds
before alignment.


_Table 67_ shows how the ADC_CR1 register should be configured to enable the analog
watchdog on one or more channels.


RM0090 Rev 21 395/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


**Figure 46. Analog watchdog’s guarded area**









**Table 67. Analog watchdog channel selection**













|Channels guarded by the analog<br>watchdog|ADC_CR1 register control bits (x = don’t care)|Col3|Col4|
|---|---|---|---|
|**Channels guarded by the analog**<br>**watchdog**|**AWDSGL bit**|**AWDEN bit**|**JAWDEN bit**|
|None|x|0|0|
|All injected channels|0|0|1|
|All regular channels|0|1|0|
|All regular and injected channels|0|1|1|
|Single(1) injected channel|1|0|1|
|Single(1) regular channel|1|1|0|
|Single(1) regular or injected channel|1|1|1|


1. Selected by the AWDCH[4:0] bits


**13.3.8** **Scan mode**


This mode is used to scan a group of analog channels.


The Scan mode is selected by setting the SCAN bit in the ADC_CR1 register. Once this bit
has been set, the ADC scans all the channels selected in the ADC_SQRx registers (for
regular channels) or in the ADC_JSQR register (for injected channels). A single conversion
is performed for each channel of the group. After each end of conversion, the next channel
in the group is converted automatically. If the CONT bit is set, regular channel conversion
does not stop at the last selected channel in the group but continues again from the first
selected channel.


If the DMA bit is set, the direct memory access (DMA) controller is used to transfer the data
converted from the regular group of channels (stored in the ADC_DR register) to SRAM
after each regular channel conversion.


The EOC bit is set in the ADC_SR register:


      - At the end of each regular group sequence if the EOCS bit is cleared to 0


      - At the end of each regular channel conversion if the EOCS bit is set to 1


The data converted from an injected channel are always stored into the ADC_JDRx
registers.


396/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


**13.3.9** **Injected channel management**


**Triggered injection**


To use triggered injection, the JAUTO bit must be cleared in the ADC_CR1 register.


1. Start the conversion of a group of regular channels either by external trigger or by
setting the SWSTART bit in the ADC_CR2 register.


2. If an external injected trigger occurs or if the JSWSTART bit is set during the
conversion of a regular group of channels, the current conversion is reset and the
injected channel sequence switches to Scan-once mode.


3. Then, the regular conversion of the regular group of channels is resumed from the last
interrupted regular conversion.
If a regular event occurs during an injected conversion, the injected conversion is not
interrupted but the regular sequence is executed at the end of the injected sequence.
_Figure 47_ shows the corresponding timing diagram.


_Note:_ _When using triggered injection, one must ensure that the interval between trigger events is_
_longer than the injection sequence. For instance, if the sequence length is 30 ADC clock_
_cycles (that is two conversions with a sampling time of 3 clock periods), the minimum_
_interval between triggers must be 31 ADC clock cycles._


**Auto-injection**


If the JAUTO bit is set, then the channels in the injected group are automatically converted
after the regular group of channels. This can be used to convert a sequence of up to 20
conversions programmed in the ADC_SQRx and ADC_JSQR registers.


In this mode, external trigger on injected channels must be disabled.


If the CONT bit is also set in addition to the JAUTO bit, regular channels followed by injected
channels are continuously converted.


_Note:_ _It is not possible to use both the auto-injected and discontinuous modes simultaneously._


**Figure 47. Injected conversion latency**


1. The maximum latency value can be found in the electrical characteristics of the STM32F40x and
STM32F41x datasheets.


RM0090 Rev 21 397/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


**13.3.10** **Discontinuous mode**


**Regular group**


This mode is enabled by setting the DISCEN bit in the ADC_CR1 register. It can be used to
convert a short sequence of n conversions (n ≤ 8) that is part of the sequence of conversions
selected in the ADC_SQRx registers. The value of n is specified by writing to the
DISCNUM[2:0] bits in the ADC_CR1 register.


When an external trigger occurs, it starts the next n conversions selected in the ADC_SQRx
registers until all the conversions in the sequence are done. The total sequence length is
defined by the L[3:0] bits in the ADC_SQR1 register.


Example:


      - n = 3, channels to be converted = 0, 1, 2, 3, 6, 7, 9, 10


      - 1st trigger: sequence converted 0, 1, 2. An EOC event is generated at each
conversion.


      - 2nd trigger: sequence converted 3, 6, 7. An EOC event is generated at each
conversion


      - 3rd trigger: sequence converted 9, 10.An EOC event is generated at each conversion


      - 4th trigger: sequence converted 0, 1, 2. An EOC event is generated at each conversion


_Note:_ _When a regular group is converted in discontinuous mode, no rollover occurs._


_When all subgroups are converted, the next trigger starts the conversion of the first_
_subgroup. In the example above, the 4th trigger reconverts the channels 0, 1 and 2 in the_
_1st subgroup._


**Injected group**


This mode is enabled by setting the JDISCEN bit in the ADC_CR1 register. It can be used to
convert the sequence selected in the ADC_JSQR register, channel by channel, after an
external trigger event.


When an external trigger occurs, it starts the next channel conversions selected in the
ADC_JSQR registers until all the conversions in the sequence are done. The total sequence
length is defined by the JL[1:0] bits in the ADC_JSQR register.


Example:


n = 1, channels to be converted = 1, 2, 3
1st trigger: channel 1 converted
2nd trigger: channel 2 converted
3rd trigger: channel 3 converted and JEOC event generated
4th trigger: channel 1


_Note:_ _When all injected channels are converted, the next trigger starts the conversion of the first_
_injected channel. In the example above, the 4th trigger reconverts the 1st injected channel_
_1._


_It is not possible to use both the auto-injected and discontinuous modes simultaneously._


_Discontinuous mode must not be set for regular and injected groups at the same time._
_Discontinuous mode must be enabled only for the conversion of one group._


398/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**

## **13.4 Data alignment**


The ALIGN bit in the ADC_CR2 register selects the alignment of the data stored after
conversion. Data can be right- or left-aligned as shown in _Figure 48_ and _Figure 49_ .


The converted data value from the injected group of channels is decreased by the userdefined offset written in the ADC_JOFRx registers so the result can be a negative value.
The SEXT bit represents the extended sign value.


For channels in a regular group, no offset is subtracted so only twelve bits are significant.


**Figure 48. Right alignment of 12-bit data**













**Figure 49. Left alignment of 12-bit data**











Special case: when left-aligned, the data are aligned on a half-word basis except when the
resolution is set to 6-bit. in that case, the data are aligned on a byte basis as shown in
_Figure 50_ .


**Figure 50. Left alignment of 6-bit data**











RM0090 Rev 21 399/1757



435


**Analog-to-digital converter (ADC)** **RM0090**

## **13.5 Channel-wise programmable sampling time**


The ADC samples the input voltage for a number of ADCCLK cycles that can be modified
using the SMP[2:0] bits in the ADC_SMPR1 and ADC_SMPR2 registers. Each channel can
be sampled with a different sampling time.


The total conversion time is calculated as follows:


T conv = Sampling time + 12 cycles


Example:


With ADCCLK = 30 MHz and sampling time = 3 cycles:


T conv = 3 + 12 = 15 cycles = 0.5 µs with APB2 at 60 MHz

## **13.6 Conversion on external trigger and trigger polarity**


Conversion can be triggered by an external event (e.g. timer capture, EXTI line). If the
EXTEN[1:0] control bits (for a regular conversion) or JEXTEN[1:0] bits (for an injected
conversion) are different from “0b00”, then external events are able to trigger a conversion
with the selected polarity. _Table 68_ provides the correspondence between the EXTEN[1:0]
and JEXTEN[1:0] values and the trigger polarity.


**Table 68. Configuring the trigger polarity**

|Source|EXTEN[1:0] / JEXTEN[1:0]|
|---|---|
|Trigger detection disabled|00|
|Detection on the rising edge|01|
|Detection on the falling edge|10|
|Detection on both the rising and falling edges|11|



_Note:_ _The polarity of the external trigger can be changed on the fly._


The EXTSEL[3:0] and JEXTSEL[3:0] control bits are used to select which out of 16 possible
events can trigger conversion for the regular and injected groups.


_Table 69_ gives the possible external trigger for regular conversion.


400/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


**Table 69. External trigger for regular channels**







|Source|Type|EXTSEL[3:0]|
|---|---|---|
|TIM1_CH1 event|Internal signal from on-chip<br>timers|0000|
|TIM1_CH2 event|TIM1_CH2 event|0001|
|TIM1_CH3 event|TIM1_CH3 event|0010|
|TIM2_CH2 event|TIM2_CH2 event|0011|
|TIM2_CH3 event|TIM2_CH3 event|0100|
|TIM2_CH4 event|TIM2_CH4 event|0101|
|TIM2_TRGO event|TIM2_TRGO event|0110|
|TIM3_CH1 event|TIM3_CH1 event|0111|
|TIM3_TRGO event|TIM3_TRGO event|1000|
|TIM4_CH4 event|TIM4_CH4 event|1001|
|TIM5_CH1 event|TIM5_CH1 event|1010|
|TIM5_CH2 event|TIM5_CH2 event|1011|
|TIM5_CH3 event|TIM5_CH3 event|1100|
|TIM8_CH1 event|TIM8_CH1 event|1101|
|TIM8_TRGO event|TIM8_TRGO event|1110|
|EXTI line11|External pin|1111|


_Table 70_ gives the possible external trigger for injected conversion.


RM0090 Rev 21 401/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


**Table 70. External trigger for injected channels**







|Source|Connection type|JEXTSEL[3:0]|
|---|---|---|
|TIM1_CH4 event|Internal signal from on-chip<br>timers|0000|
|TIM1_TRGO event|TIM1_TRGO event|0001|
|TIM2_CH1 event|TIM2_CH1 event|0010|
|TIM2_TRGO event|TIM2_TRGO event|0011|
|TIM3_CH2 event|TIM3_CH2 event|0100|
|TIM3_CH4 event|TIM3_CH4 event|0101|
|TIM4_CH1 event|TIM4_CH1 event|0110|
|TIM4_CH2 event|TIM4_CH2 event|0111|
|TIM4_CH3 event|TIM4_CH3 event|1000|
|TIM4_TRGO event|TIM4_TRGO event|1001|
|TIM5_CH4 event|TIM5_CH4 event|1010|
|TIM5_TRGO event|TIM5_TRGO event|1011|
|TIM8_CH2 event|TIM8_CH2 event|1100|
|TIM8_CH3 event|TIM8_CH3 event|1101|
|TIM8_CH4 event|TIM8_CH4 event|1110|
|EXTI line15|External pin|1111|


Software source trigger events can be generated by setting SWSTART (for regular
conversion) or JSWSTART (for injected conversion) in ADC_CR2.


A regular group conversion can be interrupted by an injected trigger.


_Note:_ _The trigger selection can be changed on the fly. However, when the selection changes,_
_there is a time frame of 1 APB clock cycle during which the trigger detection is disabled._
_This is to avoid spurious detection during transitions._

## **13.7 Fast conversion mode**


It is possible to perform faster conversion by reducing the ADC resolution. The RES bits are
used to select the number of bits available in the data register. The minimum conversion
time for each resolution is then as follows:


      - 12 bits: 3 + 12 = 15 ADCCLK cycles


      - 10 bits: 3 + 10 = 13 ADCCLK cycles


      - 8 bits: 3 + 8 = 11 ADCCLK cycles


      - 6 bits: 3 + 6 = 9 ADCCLK cycles


402/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**

## **13.8 Data management**


**13.8.1** **Using the DMA**


Since converted regular channel values are stored into a unique data register, it is useful to
use DMA for conversion of more than one regular channel. This avoids the loss of the data
already stored in the ADC_DR register.


When the DMA mode is enabled (DMA bit set to 1 in the ADC_CR2 register), after each
conversion of a regular channel, a DMA request is generated. This allows the transfer of the
converted data from the ADC_DR register to the destination location selected by the
software.


Despite this, if data are lost (overrun), the OVR bit in the ADC_SR register is set and an
interrupt is generated (if the OVRIE enable bit is set). DMA transfers are then disabled and
DMA requests are no longer accepted. In this case, if a DMA request is made, the regular
conversion in progress is aborted and further regular triggers are ignored. It is then
necessary to clear the OVR flag and the DMAEN bit in the used DMA stream, and to reinitialize both the DMA and the ADC to have the wanted converted channel data transferred
to the right memory location. Only then can the conversion be resumed and the data
transfer, enabled again. Injected channel conversions are not impacted by overrun errors.


When OVR = 1 in DMA mode, the DMA requests are blocked after the last valid data have
been transferred, which means that all the data transferred to the RAM can be considered
as valid.


At the end of the last DMA transfer (number of transfers configured in the DMA controller’s
DMA_SxNDTR register):


      - No new DMA request is issued to the DMA controller if the DDS bit is cleared to 0 in the
ADC_CR2 register (this avoids generating an overrun error). However the DMA bit is
not cleared by hardware. It must be written to 0, then to 1 to start a new transfer.


      - Requests can continue to be generated if the DDS bit is set to 1. This allows
configuring the DMA in double-buffer circular mode.


To recover the ADC from OVR state when the DMA is used, follow the steps below:


1. Reinitialize the DMA (adjust destination address and NDTR counter)


2. Clear the ADC OVR bit in ADC_SR register


3. Trigger the ADC to start the conversion.


**13.8.2** **Managing a sequence of conversions without using the DMA**


If the conversions are slow enough, the conversion sequence can be handled by the
software. In this case the EOCS bit must be set in the ADC_CR2 register for the EOC status
bit to be set at the end of each conversion, and not only at the end of the sequence. When
EOCS = 1, overrun detection is automatically enabled. Thus, each time a conversion is
complete, EOC is set and the ADC_DR register can be read. The overrun management is
the same as when the DMA is used.


To recover the ADC from OVR state when the EOCS is set, follow the steps below:


1. Clear the ADC OVR bit in ADC_SR register


2. Trigger the ADC to start the conversion.


RM0090 Rev 21 403/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


**13.8.3** **Conversions without DMA and without overrun detection**


It may be useful to let the ADC convert one or more channels without reading the data each
time (if there is an analog watchdog for instance). For that, the DMA must be disabled
(DMA = 0) and the EOC bit must be set at the end of a sequence only (EOCS = 0). In this
configuration, overrun detection is disabled.

## **13.9 Multi ADC mode**


In devices with two ADCs or more, the Dual (with two ADCs) and Triple (with three ADCs)
ADC modes can be used (see _Figure 51_ ).


In multi ADC mode, the start of conversion is triggered alternately or simultaneously by the
ADC1 master to the ADC2 and ADC3 slaves, depending on the mode selected by the
MULTI[4:0] bits in the ADC_CCR register.


_Note:_ _In multi ADC mode, when configuring conversion trigger by an external event, the_
_application must set trigger by the master only and disable trigger by slaves to prevent_
_spurious triggers that would start unwanted slave conversions._


The four possible modes below are implemented:


      - Injected simultaneous mode


      - Regular simultaneous mode


      - Interleaved mode


      - Alternate trigger mode


It is also possible to use the previous modes combined in the following ways:


      - Injected simultaneous mode + Regular simultaneous mode


      - Regular simultaneous mode + Alternate trigger mode


_Note:_ _In multi ADC mode, the converted data can be read on the multi-mode data register_
_(ADC_CDR). The status bits can be read in the multi-mode status register (ADC_CSR)._


404/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


**Figure 51. Multi ADC block diagram** **[(1)]**










|Injected data registers<br>(4 x 16 bits)|Col2|
|---|---|
|Injected data registers<br> (4 x 16 bits)||












|Injected data registers<br>(4 x 16 bits)|Col2|
|---|---|
|Injected data registers<br> (4 x 16 bits)||










|Col1|Col2|Col3|Col4|Col5|
|---|---|---|---|---|
||||||
||||||
||GPIO<br>Ports||||
||||||



|Regular data register<br>( 1(162 b bitists))<br>Injected data registers<br>Regular (4 x 16 bits)<br>channels<br>Injected ADC3(2) (Slave)<br>channels|Col2|
|---|---|
|||
||ADC2 (Slave)<br> (12 bits)<br>Injected data registers<br> (4 x 16 bits)<br>Regular<br> channels<br>Injected<br> channels<br>Regular data register<br> (16 bits)|
|||
|Dual/Triple<br> control<br>Common regular data register<br> (32 bits)(3)<br>Common part<br> mode|Dual/Triple<br> control<br>Common regular data register<br> (32 bits)(3)<br>Common part<br> mode|
|||
|||
|Injected data registers<br> (4 x 16 bits)<br>Regular<br> channels<br>Injected<br> channels<br>ADC1 (Master)<br>Regular data register<br> (16 bits)|Injected data registers<br> (4 x 16 bits)<br>Regular<br> channels<br>Injected<br> channels<br>ADC1 (Master)<br>Regular data register<br> (16 bits)|


1. Although external triggers are present on ADC2 and ADC3 they are not shown in this diagram.


2. In the Dual ADC mode, the ADC3 slave part is not present.





3. In Triple ADC mode, the ADC common data register (ADC_CDR) contains the ADC1, ADC2 and ADC3’s
regular converted data. All 32 register bits are used according to a selected storage order.
In Dual ADC mode, the ADC common data register (ADC_CDR) contains both the ADC1 and ADC2’s
regular converted data. All 32 register bits are used.


RM0090 Rev 21 405/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


      - DMA requests in Multi ADC mode:


In Multi ADC mode the DMA may be configured to transfer converted data in three
different modes. In all cases, the DMA streams to use are those connected to the ADC:


– **DMA mode 1:** On each DMA request (one data item is available), a half-word
representing an ADC-converted data item is transferred.


In Triple ADC mode, ADC1 data are transferred on the first request, ADC2 data
are transferred on the second request and ADC3 data are transferred on the third
request; the sequence is repeated. So the DMA first transfers ADC1 data followed
by ADC2 data followed by ADC3 data and so on.


DMA mode 1 is used in regular simultaneous triple mode only.


**Example:**


Regular simultaneous triple mode: 3 consecutive DMA requests are generated
(one for each converted data item)


1st request: ADC_CDR[31:0] = ADC1_DR[15:0]


2nd request: ADC_CDR[31:0] = ADC2_DR[15:0]


3rd request: ADC_CDR[31:0] = ADC3_DR[15:0]


4th request: ADC_CDR[31:0] = ADC1_DR[15:0]


– **DMA mode 2** : On each DMA request (two data items are available) two halfwords representing two ADC-converted data items are transferred as a word.


In Dual ADC mode, both ADC2 and ADC1 data are transferred on the first request
(ADC2 data take the upper half-word and ADC1 data take the lower half-word) and

so on.


In Triple ADC mode, three DMA requests are generated. On the first request, both
ADC2 and ADC1 data are transferred (ADC2 data take the upper half-word and
ADC1 data take the lower half-word). On the second request, both ADC1 and
ADC3 data are transferred (ADC1 data take the upper half-word and ADC3 data
take the lower half-word).On the third request, both ADC3 and ADC2 data are
transferred (ADC3 data take the upper half-word and ADC2 data take the lower
half-word) and so on.


DMA mode 2 is used in interleaved mode and in regular simultaneous mode (for
Dual ADC mode only).


**Example:**


a) Interleaved dual mode: a DMA request is generated each time 2 data items are
available:


1st request: ADC_CDR[31:0] = ADC2_DR[15:0] | ADC1_DR[15:0]


2nd request: ADC_CDR[31:0] = ADC2_DR[15:0] | ADC1_DR[15:0]


b) Interleaved triple mode: a DMA request is generated each time 2 data items are
available


1st request: ADC_CDR[31:0] = ADC2_DR[15:0] | ADC1_DR[15:0]


2nd request: ADC_CDR[31:0] = ADC1_DR[15:0] | ADC3_DR[15:0]


3rd request: ADC_CDR[31:0] = ADC3_DR[15:0] | ADC2_DR[15:0]


4th request: ADC_CDR[31:0] = ADC2_DR[15:0] | ADC1_DR[15:0]


– **DMA mode 3** : This mode is similar to the DMA mode 2. The only differences are
that the on each DMA request (two data items are available) two bytes


406/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


representing two ADC converted data items are transferred as a half-word. The
data transfer order is similar to that of the DMA mode 2.


DMA mode 3 is used in interleaved mode in 6-bit and 8-bit resolutions (dual and
triple mode).


**Example:**


a) Interleaved dual mode: a DMA request is generated each time 2 data items are
available


1st request: ADC_CDR[15:0] = ADC2_DR[7:0] | ADC1_DR[7:0]


2nd request: ADC_CDR[15:0] = ADC2_DR[7:0] | ADC1_DR[7:0]


b) Interleaved triple mode: a DMA request is generated each time 2 data items are
available


1st request: ADC_CDR[15:0] = ADC2_DR[7:0] | ADC1_DR[7:0]


2nd request: ADC_CDR[15:0] = ADC1_DR[7:0] | ADC3_DR[7:0]


3rd request: ADC_CDR[15:0] = ADC3_DR[7:0] | ADC2_DR[7:0]


4th request: ADC_CDR[15:0] = ADC2_DR[7:0] | ADC1_DR[7:0]


**Overrun detection:** If an overrun is detected on one of the concerned ADCs (ADC1 and
ADC2 in dual and triple modes, ADC3 in triple mode only), the DMA requests are no longer
issued to ensure that all the data transferred to the RAM are valid. It may happen that the
EOC bit corresponding to one ADC remains set because the data register of this ADC
contains valid data.


**13.9.1** **Injected simultaneous mode**


This mode converts an injected group of channels. The external trigger source comes from
the injected group multiplexer of ADC1 (selected by the JEXTSEL[3:0] bits in the ADC1_CR2
register). A simultaneous trigger is provided to ADC2 and ADC3.


_Note:_ _Do not convert the same channel on the two/three ADCs (no overlapping sampling times for_
_the two/three ADCs when converting the same channel)._


_In simultaneous mode, one must convert sequences with the same length or ensure that the_
_interval between triggers is longer than the longer of the 2 sequences (Dual ADC mode) /3_
_sequences (Triple ADC mode). Otherwise, the ADC with the shortest sequence may restart_
_while the ADC with the longest sequence is completing the previous conversions._


_Regular conversions can be performed on one or all ADCs. In that case, they are_
_independent of each other and are interrupted when an injected event occurs. They are_
_resumed at the end of the injected conversion group._


RM0090 Rev 21 407/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


**Dual ADC mode**


At the end of conversion event on ADC1 or ADC2:


      - The converted data are stored into the ADC_JDRx registers of each ADC interface.


      - A JEOC interrupt is generated (if enabled on one of the two ADC interfaces) when the
ADC1/ADC2’s injected channels have all been converted.


**Figure 52. Injected simultaneous mode on 4 channels: dual ADC mode**










|Col1|CH0|Col3|CH1|Col5|CH2|Col7|CH3|
|---|---|---|---|---|---|---|---|
||CH15||CH14||CH13||CH12|


|Col1|CH15|
|---|---|
||CH0|









**Triple ADC mode**


At the end of conversion event on ADC1, ADC2 or ADC3:


- The converted data are stored into the ADC_JDRx registers of each ADC interface.


- A JEOC interrupt is generated (if enabled on one of the three ADC interfaces) when the
ADC1/ADC2/ADC3’s injected channels have all been converted.


**Figure 53. Injected simultaneous mode on 4 channels: triple ADC mode**












|Col1|CH0|Col3|CH1|Col5|CH2|Col7|CH3|
|---|---|---|---|---|---|---|---|
||CH15||CH14||CH13||CH12|
||CH10||CH12||CH8||CH5|



**13.9.2** **Regular simultaneous mode**





This mode is performed on a regular group of channels. The external trigger source comes
from the regular group multiplexer of ADC1 (selected by the EXTSEL[3:0] bits in the
ADC1_CR2 register). A simultaneous trigger is provided to ADC2 and ADC3.


_Note:_ _Do not convert the same channel on the two/three ADCs (no overlapping sampling times for_
_the two/three ADCs when converting the same channel)._


_In regular simultaneous mode, one must convert sequences with the same length or ensure_
_that the interval between triggers is longer than the long conversion time of the 2 sequences_
_(Dual ADC mode) /3 sequences (Triple ADC mode). Otherwise, the ADC with the shortest_
_sequence may restart while the ADC with the longest sequence is completing the previous_
_conversions._


_Injected conversions must be disabled._


408/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


**Dual ADC mode**


At the end of conversion event on ADC1 or ADC2:


      - A 32-bit DMA transfer request is generated (if DMA[1:0] bits in the ADC_CCR register
are equal to 0b10). This request transfers the ADC2 converted data stored in the upper
half-word of the ADC_CDR 32-bit register to the SRAM and then the ADC1 converted
data stored in the lower half-word of ADC_CDR to the SRAM.


      - An EOC interrupt is generated (if enabled on one of the two ADC interfaces) when the
ADC1/ADC2’s regular channels have all been converted.


**Figure 54. Regular simultaneous mode on 16 channels: dual ADC mode**










|Col1|CH0|Col3|CH1|Col5|CH2|Col7|CH3|
|---|---|---|---|---|---|---|---|
||CH15||CH14||CH13||CH12|


|Col1|CH15|
|---|---|
||CH0|









**Triple ADC mode**


At the end of conversion event on ADC1, ADC2 or ADC3:


- Three 32-bit DMA transfer requests are generated (if DMA[1:0] bits in the ADC_CCR
register are equal to 0b01). Three transfers then take place from the ADC_CDR 32-bit
register to SRAM: first the ADC1 converted data, then the ADC2 converted data and
finally the ADC3 converted data. The process is repeated for each new three
conversions.


- An EOC interrupt is generated (if enabled on one of the three ADC interfaces) when the
ADC1/ADC2/ADC3’s regular channels are have all been converted.


**Figure 55. Regular simultaneous mode on 16 channels: triple ADC mode**












|Col1|CH0|Col3|CH1|Col5|CH2|Col7|CH3|
|---|---|---|---|---|---|---|---|
||CH15||CH14||CH13||CH12|
||CH10||CH12||CH8||CH5|





RM0090 Rev 21 409/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


**13.9.3** **Interleaved mode**


This mode can be started only on a regular group (usually one channel). The external
trigger source comes from the regular channel multiplexer of ADC1.


**Dual ADC mode**


After an external trigger occurs:


      - ADC1 starts immediately


      - ADC2 starts after a delay of severa ~~l A~~ DC clock cycles


The minimum delay which separates 2 conversions in interleaved mode is configured in the
DELAY bits in the ADC_CCR register. However, an ADC cannot start a conversion if the
complementary ADC is still sampling its input (only one ADC can sample the input signal at
a given time). In this case, the delay becomes the sampling time + 2 ADC clock cycles. For
instance, if DELAY = 5 clock cycles and the sampling takes 15 clock cycles on both ADCs,
then 17 clock cycles separate conversions on ADC1 and ADC2).


If the CONT bit is set on both ADC1 and ADC2, the selected regular channels of both ADCs
are continuously converted.


_Note:_ _If the conversion sequence is interrupted (for instance when DMA end of transfer occurs),_
_the multi-ADC sequencer must be reset by configuring it in independent mode first (bits_
_DUAL[4:0] = 00000) before reprogramming the interleaved mode._


After an EOC interrupt is generated by ADC2 (if enabled through the EOCIE bit) a 32-bit
DMA transfer request is generated (if the DMA[1:0] bits in ADC_CCR are equal to 0b10).
This request first transfers the ADC2 converted data stored in the upper half-word of the
ADC_CDR 32-bit register into SRAM, then the ADC1 converted data stored in the register’s
lower half-word into SRAM.


**Figure 56. Interleaved mode on 1 channel in continuous conversion mode: dual ADC**
**mode**



















**Triple ADC mode**


After an external trigger occurs:


- ADC1 starts immediately and


- ADC2 starts after a delay of several ADC clock cycles






      - ADC3 starts after a delay of several ADC clock cycles referred to the ADC2 conversion


The minimum delay which separates 2 conversions in interleaved mode is configured in the
DELAY bits in the ADC_CCR register. However, an ADC cannot start a conversion if the
complementary ADC is still sampling its input (only one ADC can sample the input signal at


410/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


a given time). In this case, the delay becomes the sampling time + 2 ADC clock cycles. For
instance, if DELAY = 5 clock cycles and the sampling takes 15 clock cycles on the three
ADCs, then 17 clock cycles separate the conversions on ADC1, ADC2 and ADC3).


If the CONT bit is set on ADC1, ADC2 and ADC3, the selected regular channels of all ADCs
are continuously converted.


_Note:_ _If the conversion sequence is interrupted (for instance when DMA end of transfer occurs),_
_the multi-ADC sequencer must be reset by configuring it in independent mode first (bits_
_DUAL[4:0] = 00000) before reprogramming the interleaved mode._


In this mode a DMA request is generated each time 2 data items are available, (if the
DMA[1:0] bits in the ADC_CCR register are equal to 0b10). The request first transfers the
first converted data stored in the lower half-word of the ADC_CDR 32-bit register to SRAM,
then it transfers the second converted data stored in ADC_CDR’s upper half-word to SRAM.
The sequence is the following:


      - 1st request: ADC_CDR[31:0] = ADC2_DR[15:0] | ADC1_DR[15:0]


      - 2nd request: ADC_CDR[31:0] = ADC1_DR[15:0] | ADC3_DR[15:0]


      - 3rd request: ADC_CDR[31:0] = ADC3_DR[15:0] | ADC2_DR[15:0]


      - 4th request: ADC_CDR[31:0] = ADC2_DR[15:0] | ADC1_DR[15:0], ...


**Figure 57. Interleaved mode on 1 channel in continuous conversion mode: triple ADC**
**mode**












|Col1|CH0|Col3|
|---|---|---|
|||CH0|












|Col1|CH0|Col3|Col4|Col5|Col6|CH0|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|||CH|CH|CH|0|||CH0|
|||CH|||CH0|CH0|CH0|CH0|



**13.9.4** **Alternate trigger mode**



This mode can be started only on an injected group. The source of external trigger comes
from the injected group multiplexer of ADC1.


_Note:_ _Regular conversions can be enabled on one or all ADCs. In this case the regular_
_conversions are independent of each other. A regular conversion is interrupted when the_


RM0090 Rev 21 411/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


_ADC has to perform an injected conversion. It is resumed when the injected conversion is_
_finished._


_If the conversion sequence is interrupted (for instance when DMA end of transfer occurs),_
_the multi-ADC sequencer must be reset by configuring it in independent mode first (bits_
_DUAL[4:0] = 00000) before reprogramming the interleaved mode._


_The time interval between 2 trigger events must be greater than or equal to 1 ADC clock_
_period. The minimum time interval between 2 trigger events that start conversions on the_
_same ADC is the same as in the single ADC mode._


**Dual ADC mode**


      - When the 1st trigger occurs, all injected ADC1 channels in the group are converted


      - When the 2nd trigger occurs, all injected ADC2 channels in the group are converted


      - and so on


A JEOC interrupt, if enabled, is generated after all injected ADC1 channels in the group
have been converted.


A JEOC interrupt, if enabled, is generated after all injected ADC2 channels in the group
have been converted.


If another external trigger occurs after all injected channels in the group have been
converted then the alternate trigger process restarts by converting the injected ADC1
channels in the group.


**Figure 58. Alternate trigger: injected group of each ADC**

















If the injected discontinuous mode is enabled for both ADC1 and ADC2:


      - When the 1st trigger occurs, the first injected ADC1 channel is converted.


      - When the 2nd trigger occurs, the first injected ADC2 channel are converted


      - and so on


A JEOC interrupt, if enabled, is generated after all injected ADC1 channels in the group
have been converted.


A JEOC interrupt, if enabled, is generated after all injected ADC2 channels in the group
have been converted.


If another external trigger occurs after all injected channels in the group have been
converted then the alternate trigger process restarts.


412/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


**Figure 59. Alternate trigger: 4 injected channels (each ADC) in discontinuous mode**





















**Triple ADC mode**


- When the 1st trigger occurs, all injected ADC1 channels in the group are converted.


- When the 2nd trigger occurs, all injected ADC2 channels in the group are converted.


- When the 3rd trigger occurs, all injected ADC3 channels in the group are converted.


- and so on


A JEOC interrupt, if enabled, is generated after all injected ADC1 channels in the group
have been converted.


A JEOC interrupt, if enabled, is generated after all injected ADC2 channels in the group
have been converted.


A JEOC interrupt, if enabled, is generated after all injected ADC3 channels in the group
have been converted.


If another external trigger occurs after all injected channels in the group have been
converted then the alternate trigger process restarts by converting the injected ADC1
channels in the group.


**Figure 60. Alternate trigger: injected group of each ADC**













**13.9.5** **Combined regular/injected simultaneous mode**


It is possible to interrupt the simultaneous conversion of a regular group to start the
simultaneous conversion of an injected group.


_Note:_ _In combined regular/injected simultaneous mode, one must convert sequences with the_
_same length or ensure that the interval between triggers is longer than the long conversion_
_time of the 2 sequences (Dual ADC mode) /3 sequences (Triple ADC mode). Otherwise, the_


RM0090 Rev 21 413/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


_ADC with the shortest sequence may restart while the ADC with the longest sequence is_
_completing the previous conversions._


**13.9.6** **Combined regular simultaneous + alternate trigger mode**


It is possible to interrupt the simultaneous conversion of a regular group to start the alternate
trigger conversion of an injected group. _Figure 61_ shows the behavior of an alternate trigger
interrupting a simultaneous regular conversion.


The injected alternate conversion is immediately started after the injected event. If regular
conversion is already running, in order to ensure synchronization after the injected
conversion, the regular conversion of all (master/slave) ADCs is stopped and resumed
synchronously at the end of the injected conversion.


_Note:_ _In combined regular simultaneous + alternate trigger mode, one must convert sequences_
_with the same length or ensure that the interval between triggers is longer than the long_
_conversion time of the 2 sequences (Dual ADC mode) /3 sequences (Triple ADC mode)._
_Otherwise, the ADC with the shortest sequence may restart while the ADC with the longest_
_sequence is completing the previous conversions._


_If the conversion sequence is interrupted (for instance when DMA end of transfer occurs),_
_the multi-ADC sequencer must be reset by configuring it in independent mode first (bits_
_DUAL[4:0] = 00000) before reprogramming the interleaved mode._


**Figure 61. Alternate + regular simultaneous**














|Col1|CH0|Col3|CH1|Col5|CH2|Col7|Col8|Col9|Col10|CH2|Col12|CH3|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|||||CH|CH||CH|0|||||
||CH3||CH5||CH6|CH6|CH6|CH6||CH6||CH7|


|Col1|CH3|Col3|CH4|
|---|---|---|---|
|||||
||CH7||CH8|



If a trigger occurs during an injected conversion that has interrupted a regular conversion, it
is ignored. _Figure 62_ shows the behavior in this case (2nd trigger is ignored).


414/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


**Figure 62. Case of trigger occurring during injected conversion**










|Col1|CH0|Col3|CH1|Col5|CH2|Col7|Col8|Col9|Col10|CH2|Col12|CH3|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|||||CH|CH||CH|0|||||
||CH3||CH5||CH6|CH6|CH6|CH6||CH6||CH7|


|Col1|CH3|Col3|CH4|Col5|
|---|---|---|---|---|
|||||CH0|
||CH7||CH8|CH8|












## **13.10 Temperature sensor**

The temperature sensor can be used to measure the junction temperature (T J ) of the
device.


      - On STM32F40x and STM32F41x devices, the temperature sensor is internally
connected to ADC1_IN16 channel which is used to convert the sensor output voltage
to a digital value.


      - On STM32F42x and STM32F43x devices, the temperature sensor is internally
connected to the same input channel, ADC1_IN18, as VBAT: ADC1_IN18 is used to
convert the sensor output voltage or VBAT into a digital value. Only one conversion,
temperature sensor or VBAT, must be selected at a time. When the temperature sensor
and the VBAT conversion are set simultaneously, only the VBAT conversion is
performed.


_Figure 63_ shows the block diagram of the temperature sensor.


When not in use, the sensor can be put in power down mode.


_Note:_ _The TSVREFE bit must be set to enable the conversion of both internal channels: the_
_ADC1_IN16 or ADC1_IN18 (temperature sensor) and the ADC1_IN17 (VREFINT)._


**Main features**


      - Supported temperature range: –40 to 125 °C


      - Precision: ±1.5 °C


RM0090 Rev 21 415/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


**Figure 63. Temperature sensor and V** **REFINT** **channel block diagram**











1. V SENSE is input to ADC1_IN16 for the STM23F40x and STM32F41x devices and to ADC1_IN18 for the
STM32F42x and STM32F43x devices.


**Reading the temperature**


To use the sensor:


3. Select ADC1_IN16 or ADC1_IN18 input channel.


4. Select a sampling time greater than the minimum sampling time specified in the
datasheet.


5. Set the TSVREFE bit in the ADC_CCR register to wake up the temperature sensor
from power down mode


6. Start the ADC conversion by setting the SWSTART bit (or by external trigger)


7. Read the resulting V SENSE data in the ADC data register


8. Calculate the temperature using the following formula:


Temperature (in °C) = {(V SENSE – V 25 ) / Avg_Slope} + 25


Where:


– V 25 = V SENSE value for 25° C


–
Avg_Slope = average slope of the temperature vs. V SENSE curve (given in mV/°C
or µV/°C)


Refer to the datasheet’s electrical characteristics section for the actual values of V 25
and Avg_Slope.


_Note:_ _The sensor has a startup time after waking from power down mode before it can output_
_V_ _SENSE_ _at the correct level. The ADC also has a startup time after power-on, so to minimize_
_the delay, the ADON and TSVREFE bits should be set at the same time._


The temperature sensor output voltage changes linearly with temperature. The offset of this
linear function depends on each chip due to process variation (up to 45 °C from one chip to
another).


416/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


The internal temperature sensor is more suited for applications that detect temperature
variations instead of absolute temperatures. If accurate temperature reading is required, an
external temperature sensor should be used.

## **13.11 Battery charge monitoring**


The VBATE bit in the ADC_CCR register is used to switch to the battery voltage. As the
V BAT voltage could be higher than V DDA, to ensure the correct operation of the ADC, the
V BAT pin is internally connected to a bridge divider.


When the VBATE is set, the bridge is automatically enabled to connect:


      - VBAT/2 to the ADC1_IN18 input channel, on STM32F40xx and STM32F41xx devices


      - VBAT/4 to the ADC1_IN18 input channel, on STM32F42xx and STM32F43xx devices


_Note:_ _On STM32F42xx and STM32F43xx devices, VBAT and temperature sensor are connected_
_to the same ADC internal channel (ADC1_IN18). Only one conversion, either temperature_
_sensor or VBAT, must be selected at a time. When both conversion are enabled_
_simultaneously, only the VBAT conversion is performed._

## **13.12 ADC interrupts**


An interrupt can be produced on the end of conversion for regular and injected groups,
when the analog watchdog status bit is set and when the overrun status bit is set. Separate
interrupt enable bits are available for flexibility.


Two other flags are present in the ADC_SR register, but there is no interrupt associated with
them:


      - JSTRT (Start of conversion for channels of an injected group)


      - STRT (Start of conversion for channels of a regular group)


**Table 71. ADC interrupts**

|Interrupt event|Event flag|Enable control bit|
|---|---|---|
|End of conversion of a regular group|EOC|EOCIE|
|End of conversion of an injected group|JEOC|JEOCIE|
|Analog watchdog status bit is set|AWD|AWDIE|
|Overrun|OVR|OVRIE|



RM0090 Rev 21 417/1757



435


**Analog-to-digital converter (ADC)** **RM0090**

## **13.13 ADC registers**


Refer to _Section 1.1: List of abbreviations for registers for registers_ for a list of abbreviations
used in register descriptions.


The peripheral registers must be written at word level (32 bits). Read accesses can be done
by bytes (8 bits), half-words (16 bits) or words (32 bits).


**13.13.1** **ADC status register (ADC_SR)**


Address offset: 0x00


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|
|Reserved|OVR|STRT|JSTRT|JEOC|EOC|AWD|
|Reserved|rc_w0|rc_w0|rc_w0|rc_w0|rc_w0|rc_w0|



Bits 31:6 Reserved, must be kept at reset value.


Bit 5 **OVR:** Overrun

This bit is set by hardware when data are lost (either in single mode or in dual/triple mode). It
is cleared by software. Overrun detection is enabled only when DMA = 1 or EOCS = 1.

0: No overrun occurred

1: Overrun has occurred


Bit 4 **STRT:** Regular channel start flag

This bit is set by hardware when regular channel conversion starts. It is cleared by software.
0: No regular channel conversion started
1: Regular channel conversion has started


Bit 3 **JSTRT:** Injected channel start flag

This bit is set by hardware when injected group conversion starts. It is cleared by software.
0: No injected group conversion started
1: Injected group conversion has started


Bit 2 **JEOC:** Injected channel end of conversion

This bit is set by hardware at the end of the conversion of all injected channels in the group.
It is cleared by software.
0: Conversion is not complete
1: Conversion complete


Bit 1 **EOC:** Regular channel end of conversion

This bit is set by hardware at the end of the conversion of a regular group of channels. It is
cleared by software or by reading the ADC_DR register.
0: Conversion not complete (EOCS=0), or sequence of conversions not complete (EOCS=1)
1: Conversion complete (EOCS=0), or sequence of conversions complete (EOCS=1)


Bit 0 **AWD:** Analog watchdog flag

This bit is set by hardware when the converted voltage crosses the values programmed in
the ADC_LTR and ADC_HTR registers. It is cleared by software.
0: No analog watchdog event occurred
1: Analog watchdog event occurred


418/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


**13.13.2** **ADC control register 1 (ADC_CR1)**


Address offset: 0x04


Reset value: 0x0000 0000

|31 30 29 28 27|26|25 24|Col4|23|22|21 20 19 18 17 16|
|---|---|---|---|---|---|---|
|Reserved|OVRIE|RES|RES|AWDEN|JAWDEN|Reserved|
|Reserved|rw|rw|rw|rw|rw|rw|


|15 14 13|Col2|Col3|12|11|10|9|8|7|6|5|4 3 2 1 0|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DISCNUM[2:0]|DISCNUM[2:0]|DISCNUM[2:0]|JDISCE<br>N|DISC<br>EN|JAUTO|AWDSG<br>L|SCAN|JEOCIE|AWDIE|EOCIE|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:27 Reserved, must be kept at reset value.


Bit 26 **OVRIE:** Overrun interrupt enable

This bit is set and cleared by software to enable/disable the Overrun interrupt.
0: Overrun interrupt disabled
1: Overrun interrupt enabled. An interrupt is generated when the OVR bit is set.


Bits 25:24 **RES[1:0]:** Resolution

These bits are written by software to select the resolution of the conversion.
00: 12-bit (15 ADCCLK cycles)
01: 10-bit (13 ADCCLK cycles)
10: 8-bit (11 ADCCLK cycles)
11: 6-bit (9 ADCCLK cycles)


Bit 23 **AWDEN:** Analog watchdog enable on regular channels

This bit is set and cleared by software.
0: Analog watchdog disabled on regular channels
1: Analog watchdog enabled on regular channels


Bit 22 **JAWDEN:** Analog watchdog enable on injected channels

This bit is set and cleared by software.
0: Analog watchdog disabled on injected channels
1: Analog watchdog enabled on injected channels


Bits 21:16 Reserved, must be kept at reset value.


Bits 15:13 **DISCNUM[2:0]:** Discontinuous mode channel count

These bits are written by software to define the number of regular channels to be converted
in discontinuous mode, after receiving an external trigger.

000: 1 channel

001: 2 channels

...

111: 8 channels


Bit 12 **JDISCEN:** Discontinuous mode on injected channels

This bit is set and cleared by software to enable/disable discontinuous mode on the injected
channels of a group.
0: Discontinuous mode on injected channels disabled
1: Discontinuous mode on injected channels enabled


RM0090 Rev 21 419/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


Bit 11 **DISCEN:** Discontinuous mode on regular channels

This bit is set and cleared by software to enable/disable Discontinuous mode on regular
channels.

0: Discontinuous mode on regular channels disabled
1: Discontinuous mode on regular channels enabled


Bit 10 **JAUTO:** Automatic injected group conversion

This bit is set and cleared by software to enable/disable automatic injected group conversion
after regular group conversion.
0: Automatic injected group conversion disabled
1: Automatic injected group conversion enabled


Bit 9 **AWDSGL:** Enable the watchdog on a single channel in scan mode

This bit is set and cleared by software to enable/disable the analog watchdog on the channel
identified by the AWDCH[4:0] bits.
0: Analog watchdog enabled on all channels
1: Analog watchdog enabled on a single channel


Bit 8 **SCAN:** Scan mode

This bit is set and cleared by software to enable/disable the Scan mode. In Scan mode, the
inputs selected through the ADC_SQRx or ADC_JSQRx registers are converted.

0: Scan mode disabled

1: Scan mode enabled

_Note: An EOC interrupt is generated if the EOCIE bit is set:_

_–_
_At the end of each regular group sequence if the EOCS bit is cleared to 0_

_–_
_At the end of each regular channel conversion if the EOCS bit is set to 1_

_Note: A JEOC interrupt is generated only on the end of conversion of the last channel if the_
_JEOCIE bit is set._


Bit 7 **JEOCIE:** Interrupt enable for injected channels

This bit is set and cleared by software to enable/disable the end of conversion interrupt for
injected channels.
0: JEOC interrupt disabled
1: JEOC interrupt enabled. An interrupt is generated when the JEOC bit is set.


Bit 6 **AWDIE:** Analog watchdog interrupt enable

This bit is set and cleared by software to enable/disable the analog watchdog interrupt.
0: Analog watchdog interrupt disabled
1: Analog watchdog interrupt enabled


Bit 5 **EOCIE:** Interrupt enable for EOC

This bit is set and cleared by software to enable/disable the end of conversion interrupt.
0: EOC interrupt disabled
1: EOC interrupt enabled. An interrupt is generated when the EOC bit is set.


Bits 4:0 **AWDCH[4:0]:** Analog watchdog channel select bits

These bits are set and cleared by software. They select the input channel to be guarded by
the analog watchdog.

Note: 00000: ADC analog input Channel0
00001: ADC analog input Channel1

...

01111: ADC analog input Channel15
10000: ADC analog input Channel16
10001: ADC analog input Channel17
10010: ADC analog input Channel18
Other values reserved


420/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


**13.13.3** **ADC control register 2 (ADC_CR2)**


Address offset: 0x08


Reset value: 0x0000 0000









|31|30|29 28|Col4|27 26 25 24|Col6|Col7|Col8|23|22|21 20|Col12|19 18 17 16|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|reserved|SWST<br>ART|EXTEN|EXTEN|EXTSEL[3:0]|EXTSEL[3:0]|EXTSEL[3:0]|EXTSEL[3:0]|reserved|JSWST<br>ART|JEXTEN|JEXTEN|JEXTSEL[3:0]|JEXTSEL[3:0]|JEXTSEL[3:0]|JEXTSEL[3:0]|
|reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12|11|10|9|8|7 6 5 4 3 2|1|0|
|---|---|---|---|---|---|---|---|
|reserved|ALIGN|EOCS|DDS|DMA|Reserved|CONT|ADON|
|reserved|rw|rw|rw|rw|rw|rw|rw|


Bit 31 Reserved, must be kept at reset value.


Bit 30 **SWSTART:** Start conversion of regular channels

This bit is set by software to start conversion and cleared by hardware as soon as the
conversion starts.

0: Reset state

1: Starts conversion of regular channels

_Note: This bit can be set only when ADON = 1 otherwise no conversion is launched._


Bits 29:28 **EXTEN:** External trigger enable for regular channels

These bits are set and cleared by software to select the external trigger polarity and enable
the trigger of a regular group.
00: Trigger detection disabled
01: Trigger detection on the rising edge
10: Trigger detection on the falling edge
11: Trigger detection on both the rising and falling edges


Bits 27:24 **EXTSEL[3:0]:** External event select for regular group

These bits select the external event used to trigger the start of conversion of a regular group:

0000: Timer 1 CC1 event

0001: Timer 1 CC2 event

0010: Timer 1 CC3 event

0011: Timer 2 CC2 event

0100: Timer 2 CC3 event

0101: Timer 2 CC4 event

0110: Timer 2 TRGO event

0111: Timer 3 CC1 event

1000: Timer 3 TRGO event

1001: Timer 4 CC4 event

1010: Timer 5 CC1 event

1011: Timer 5 CC2 event

1100: Timer 5 CC3 event

1101: Timer 8 CC1 event

1110: Timer 8 TRGO event

1111: EXTI line11


Bit 23 Reserved, must be kept at reset value.


RM0090 Rev 21 421/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


Bit 22 **JSWSTART:** Start conversion of injected channels

This bit is set by software and cleared by hardware as soon as the conversion starts.

0: Reset state

1: Starts conversion of injected channels

_Note: This bit can be set only when ADON = 1 otherwise no conversion is launched._


Bits 21:20 **JEXTEN:** External trigger enable for injected channels

These bits are set and cleared by software to select the external trigger polarity and enable
the trigger of an injected group.
00: Trigger detection disabled
01: Trigger detection on the rising edge
10: Trigger detection on the falling edge
11: Trigger detection on both the rising and falling edges


Bits 19:16 **JEXTSEL[3:0]:** External event select for injected group

These bits select the external event used to trigger the start of conversion of an injected

group.

0000: Timer 1 CC4 event

0001: Timer 1 TRGO event

0010: Timer 2 CC1 event

0011: Timer 2 TRGO event

0100: Timer 3 CC2 event

0101: Timer 3 CC4 event

0110: Timer 4 CC1 event

0111: Timer 4 CC2 event

1000: Timer 4 CC3 event

1001: Timer 4 TRGO event

1010: Timer 5 CC4 event

1011: Timer 5 TRGO event

1100: Timer 8 CC2 event

1101: Timer 8 CC3 event

1110: Timer 8 CC4 event

1111: EXTI line15


Bits 15:12 Reserved, must be kept at reset value.


Bit 11 **ALIGN:** Data alignment

This bit is set and cleared by software. Refer to _Figure 48_ and _Figure 49_ .
0: Right alignment
1: Left alignment


Bit 10 **EOCS:** End of conversion selection

This bit is set and cleared by software.
0: The EOC bit is set at the end of each sequence of regular conversions. Overrun detection
is enabled only if DMA=1.
1: The EOC bit is set at the end of each regular conversion. Overrun detection is enabled.


Bit 9 **DDS:** DMA disable selection (for single ADC mode)

This bit is set and cleared by software.
0: No new DMA request is issued after the last transfer (as configured in the DMA controller)
1: DMA requests are issued as long as data are converted and DMA=1


Bit 8 **DMA:** Direct memory access mode (for single ADC mode)

This bit is set and cleared by software. Refer to the DMA controller chapter for more details.

0: DMA mode disabled

1: DMA mode enabled


422/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


Bits 7:2 Reserved, must be kept at reset value.


Bit 1 **CONT:** Continuous conversion

This bit is set and cleared by software. If it is set, conversion takes place continuously until it
is cleared.

0: Single conversion mode
1: Continuous conversion mode


Bit 0 **ADON:** A/D Converter ON / OFF

This bit is set and cleared by software.

Note: 0: Disable ADC conversion and go to power down mode
1: Enable ADC


**13.13.4** **ADC sample time register 1 (ADC_SMPR1)**


Address offset: 0x0C


Reset value: 0x0000 0000

|31 30 29 28 27|26 25 24|Col3|Col4|23 22 21|Col6|Col7|20 19 18|Col9|Col10|17 16|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|SMP18[2:0]|SMP18[2:0]|SMP18[2:0]|SMP17[2:0]|SMP17[2:0]|SMP17[2:0]|SMP16[2:0]|SMP16[2:0]|SMP16[2:0]|SMP15[2:1]|SMP15[2:1]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14 13 12|Col3|Col4|11 10 9|Col6|Col7|8 7 6|Col9|Col10|5 4 3|Col12|Col13|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SMP15_0|SMP14[2:0]|SMP14[2:0]|SMP14[2:0]|SMP13[2:0]|SMP13[2:0]|SMP13[2:0]|SMP12[2:0]|SMP12[2:0]|SMP12[2:0]|SMP11[2:0]|SMP11[2:0]|SMP11[2:0]|SMP10[2:0]|SMP10[2:0]|SMP10[2:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31: 27 Reserved, must be kept at reset value.


Bits 26:0 **SMPx[2:0]:** Channel x sampling time selection

These bits are written by software to select the sampling time individually for each channel.
During sampling cycles, the channel selection bits must remain unchanged.

Note: 000: 3 cycles
001: 15 cycles
010: 28 cycles
011: 56 cycles
100: 84 cycles
101: 112 cycles
110: 144 cycles
111: 480 cycles


**13.13.5** **ADC sample time register 2 (ADC_SMPR2)**


Address offset: 0x10


Reset value: 0x0000 0000

|31 30|29 28 27|Col3|Col4|26 25 24|Col6|Col7|23 22 21|Col9|Col10|20 19 18|Col12|Col13|17 16|Col15|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|SMP9[2:0]|SMP9[2:0]|SMP9[2:0]|SMP8[2:0]|SMP8[2:0]|SMP8[2:0]|SMP7[2:0]|SMP7[2:0]|SMP7[2:0]|SMP6[2:0]|SMP6[2:0]|SMP6[2:0]|SMP5[2:1]|SMP5[2:1]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14 13 12|Col3|Col4|11 10 9|Col6|Col7|8 7 6|Col9|Col10|5 4 3|Col12|Col13|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SMP<br>5_0|SMP4[2:0]|SMP4[2:0]|SMP4[2:0]|SMP3[2:0]|SMP3[2:0]|SMP3[2:0]|SMP2[2:0]|SMP2[2:0]|SMP2[2:0]|SMP1[2:0]|SMP1[2:0]|SMP1[2:0]|SMP0[2:0]|SMP0[2:0]|SMP0[2:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



RM0090 Rev 21 423/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


Bits 31:30 Reserved, must be kept at reset value.


Bits 29:0 **SMPx[2:0]:** Channel x sampling time selection

These bits are written by software to select the sampling time individually for each channel.
During sample cycles, the channel selection bits must remain unchanged.

Note: 000: 3 cycles
001: 15 cycles
010: 28 cycles
011: 56 cycles
100: 84 cycles
101: 112 cycles
110: 144 cycles
111: 480 cycles


**13.13.6** **ADC injected channel data offset register x (ADC_JOFRx) (x=1..4)**


Address offset: 0x14-0x20


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12|11 10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|JOFFSETx[11:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:12 Reserved, must be kept at reset value.


Bits 11:0 **JOFFSETx[11:0]:** Data offset for injected channel x

These bits are written by software to define the offset to be subtracted from the raw
converted data when converting injected channels. The conversion result can be read from
in the ADC_JDRx registers.


**13.13.7** **ADC watchdog higher threshold register (ADC_HTR)**


Address offset: 0x24


Reset value: 0x0000 0FFF


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12|11 10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:12 Reserved, must be kept at reset value.


Bits 11:0 **HT[11:0]:** Analog watchdog higher threshold

These bits are written by software to define the higher threshold for the analog watchdog.


424/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


_Note:_ _The software can write to these registers when an ADC conversion is ongoing. The_
_programmed value is effective when the next conversion is complete. Writing to this register_
_is performed with a write delay that can create uncertainty on the effective time at which the_
_new value is programmed._


**13.13.8** **ADC watchdog lower threshold register (ADC_LTR)**


Address offset: 0x28


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12|11 10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:12 Reserved, must be kept at reset value.


Bits 11:0 **LT[11:0]:** Analog watchdog lower threshold

These bits are written by software to define the lower threshold for the analog watchdog.


_Note:_ _The software can write to these registers when an ADC conversion is ongoing. The_
_programmed value is effective when the next conversion is complete. Writing to this register_
_is performed with a write delay that can create uncertainty on the effective time at which the_
_new value is programmed._


**13.13.9** **ADC regular sequence register 1 (ADC_SQR1)**


Address offset: 0x2C


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24|23 22 21 20|Col3|Col4|Col5|19 18 17 16|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|L[3:0]|L[3:0]|L[3:0]|L[3:0]|SQ16[4:1]|SQ16[4:1]|SQ16[4:1]|SQ16[4:1]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14 13 12 11 10|Col3|Col4|Col5|Col6|9 8 7 6 5|Col8|Col9|Col10|Col11|4 3 2 1 0|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SQ16_0|SQ15[4:0]|SQ15[4:0]|SQ15[4:0]|SQ15[4:0]|SQ15[4:0]|SQ14[4:0]|SQ14[4:0]|SQ14[4:0]|SQ14[4:0]|SQ14[4:0]|SQ13[4:0]|SQ13[4:0]|SQ13[4:0]|SQ13[4:0]|SQ13[4:0]|
|rw|rw|rw|rw|rw|rw|rw|rw||||rw|rw|rw|rw|rw|



Bits 31:24 Reserved, must be kept at reset value.


Bits 23:20 **L[3:0]:** Regular channel sequence length

These bits are written by software to define the total number of conversions in the regular
channel conversion sequence.

0000: 1 conversion

0001: 2 conversions

...

1111: 16 conversions


Bits 19:15 **SQ16[4:0]:** 16th conversion in regular sequence

These bits are written by software with the channel number (0..18) assigned as the 16th in
the conversion sequence.


RM0090 Rev 21 425/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


Bits 14:10 **SQ15[4:0]:** 15th conversion in regular sequence


Bits 9:5 **SQ14[4:0]:** 14th conversion in regular sequence


Bits 4:0 **SQ13[4:0]:** 13th conversion in regular sequence


**13.13.10 ADC regular sequence register 2 (ADC_SQR2)**


Address offset: 0x30


Reset value: 0x0000 0000

|31 30|29 28 27 26 25|Col3|Col4|Col5|Col6|24 23 22 21 20|Col8|Col9|Col10|Col11|19 18 17 16|Col13|Col14|Col15|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|SQ12[4:0]|SQ12[4:0]|SQ12[4:0]|SQ12[4:0]|SQ12[4:0]|SQ11[4:0]|SQ11[4:0]|SQ11[4:0]|SQ11[4:0]|SQ11[4:0]|SQ10[4:1]|SQ10[4:1]|SQ10[4:1]|SQ10[4:1]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14 13 12 11 10|Col3|Col4|Col5|Col6|9 8 7 6 5|Col8|Col9|Col10|Col11|4 3 2 1 0|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|SQ10_0|SQ9[4:0]|SQ9[4:0]|SQ9[4:0]|SQ9[4:0]|SQ9[4:0]|SQ8[4:0]|SQ8[4:0]|SQ8[4:0]|SQ8[4:0]|SQ8[4:0]|SQ7[4:0]|SQ7[4:0]|SQ7[4:0]|SQ7[4:0]|SQ7[4:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:30 Reserved, must be kept at reset value.


Bits 29:26 **SQ12[4:0]:** 12th conversion in regular sequence

These bits are written by software with the channel number (0..18) assigned as the 12th in
the sequence to be converted.


Bits 24:20 **SQ11[4:0]:** 11th conversion in regular sequence


Bits 19:15 **SQ10[4:0]:** 10th conversion in regular sequence


Bits 14:10 **SQ9[4:0]:** 9th conversion in regular sequence


Bits 9:5 **SQ8[4:0]:** 8th conversion in regular sequence


Bits 4:0 **SQ7[4:0]:** 7th conversion in regular sequence


**13.13.11 ADC regular sequence register 3 (ADC_SQR3)**


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


Bits 29:25 **SQ6[4:0]:** 6th conversion in regular sequence

These bits are written by software with the channel number (0..18) assigned as the 6th in the
sequence to be converted.


Bits 24:20 **SQ5[4:0]:** 5th conversion in regular sequence


426/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


Bits 19:15 **SQ4[4:0]:** 4th conversion in regular sequence


Bits 14:10 **SQ3[4:0]:** 3rd conversion in regular sequence


Bits 9:5 **SQ2[4:0]:** 2nd conversion in regular sequence


Bits 4:0 **SQ1[4:0]:** 1st conversion in regular sequence


**13.13.12 ADC injected sequence register (ADC_JSQR)**


Address offset: 0x38


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22|21 20|Col3|19 18 17 16|Col5|Col6|Col7|
|---|---|---|---|---|---|---|
|Reserved|JL[1:0]|JL[1:0]|JSQ4[4:1]|JSQ4[4:1]|JSQ4[4:1]|JSQ4[4:1]|
|Reserved|rw|rw|rw|rw|rw|rw|


|15|14 13 12 11 10|Col3|Col4|Col5|Col6|9 8 7 6 5|Col8|Col9|Col10|Col11|4 3 2 1 0|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|JSQ4[0]|JSQ3[4:0]|JSQ3[4:0]|JSQ3[4:0]|JSQ3[4:0]|JSQ3[4:0]|JSQ2[4:0]|JSQ2[4:0]|JSQ2[4:0]|JSQ2[4:0]|JSQ2[4:0]|JSQ1[4:0]|JSQ1[4:0]|JSQ1[4:0]|JSQ1[4:0]|JSQ1[4:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:22 Reserved, must be kept at reset value.


Bits 21:20 **JL[1:0]:** Injected sequence length

These bits are written by software to define the total number of conversions in the injected
channel conversion sequence.

00: 1 conversion

01: 2 conversions

10: 3 conversions

11: 4 conversions


Bits 19:15 **JSQ4[4:0]:** 4th conversion in injected sequence (when JL[1:0]=3, see note below)

These bits are written by software with the channel number (0..18) assigned as the 4th in the
sequence to be converted.


Bits 14:10 **JSQ3[4:0]:** 3rd conversion in injected sequence (when JL[1:0]=3, see note below)


Bits 9:5 **JSQ2[4:0]:** 2nd conversion in injected sequence (when JL[1:0]=3, see note below)


Bits 4:0 **JSQ1[4:0]:** 1st conversion in injected sequence (when JL[1:0]=3, see note below)


_Note:_ _When JL[1:0]=3 (4 injected conversions in the sequencer), the ADC converts the channels_
_in the following order: JSQ1[4:0], JSQ2[4:0], JSQ3[4:0], and JSQ4[4:0]._


_When JL=2 (3 injected conversions in the sequencer), the ADC converts the channels in the_
_following order: JSQ2[4:0], JSQ3[4:0], and JSQ4[4:0]._


_When JL=1 (2 injected conversions in the sequencer), the ADC converts the channels in_
_starting from JSQ3[4:0], and then JSQ4[4:0]._


_When JL=0 (1 injected conversion in the sequencer), the ADC converts only JSQ4[4:0]_
_channel._


RM0090 Rev 21 427/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


**13.13.13 ADC injected data register x (ADC_JDRx) (x= 1..4)**


Address offset: 0x3C - 0x48


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **JDATA[15:0]:** Injected data

These bits are read-only. They contain the conversion result from injected channel x. The
data are left -or right-aligned as shown in _Figure 48_ and _Figure 49_ .


**13.13.14 ADC regular data register (ADC_DR)**


Address offset: 0x4C


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **DATA[15:0]:** Regular data

These bits are read-only. They contain the conversion result from the regular
channels. The data are left- or right-aligned as shown in _Figure 48_ and
_Figure 49_ .


428/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


**13.13.15 ADC Common status register (ADC_CSR)**


Address offset: 0x00 (this offset address is relative to ADC1 base address + 0x300)


Reset value: 0x0000 0000


This register provides an image of the status bits of the different ADCs. Nevertheless it is
read-only and does not allow to clear the different status bits. Instead each status bit must
be cleared by writing it to 0 in the corresponding ADC_SR register.






|31 30 29 28 27 26 25 24 23 22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|
|Reserved|OVR3|STRT3|JSTRT3|JEOC 3|EOC3|AWD3|
|Reserved|ADC3|ADC3|ADC3|ADC3|ADC3|ADC3|
|Reserved|r|r|r|r|r|r|













|15 14|13|12|11|10|9|8|7 6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|OVR2|STRT2|JSTRT<br>2|JEOC2|EOC2|AWD2|Reserved|OVR1|STRT1|JSTRT1|JEOC 1|EOC1|AWD1|
|Reserved|ADC2|ADC2|ADC2|ADC2|ADC2|ADC2|ADC2|ADC1|ADC1|ADC1|ADC1|ADC1|ADC1|
|Reserved|r|r|r|r|r|r|r|r|r|r|r|r|r|


Bits 31:22 Reserved, must be kept at reset value.


Bit 21 **OVR3:** Overrun flag of ADC3

This bit is a copy of the OVR bit in the ADC3_SR register.


Bit 20 **STRT3:** Regular channel Start flag of ADC3

This bit is a copy of the STRT bit in the ADC3_SR register.


Bit 19 **JSTRT3:** Injected channel Start flag of ADC3

This bit is a copy of the JSTRT bit in the ADC3_SR register.


Bit 18 **JEOC3:** Injected channel end of conversion of ADC3

This bit is a copy of the JEOC bit in the ADC3_SR register.


Bit 17 **EOC3:** End of conversion of ADC3

This bit is a copy of the EOC bit in the ADC3_SR register.


Bit 16 **AWD3:** Analog watchdog flag of ADC3

This bit is a copy of the AWD bit in the ADC3_SR register.


Bits 15:14 Reserved, must be kept at reset value.


Bit 13 **OVR2:** Overrun flag of ADC2

This bit is a copy of the OVR bit in the ADC2_SR register.


Bit 12 **STRT2:** Regular channel Start flag of ADC2

This bit is a copy of the STRT bit in the ADC2_SR register.


Bit 11 **JSTRT2:** Injected channel Start flag of ADC2

This bit is a copy of the JSTRT bit in the ADC2_SR register.


Bit 10 **JEOC2:** Injected channel end of conversion of ADC2

This bit is a copy of the JEOC bit in the ADC2_SR register.


Bit 9 **EOC2:** End of conversion of ADC2

This bit is a copy of the EOC bit in the ADC2_SR register.


Bit 8 **AWD2:** Analog watchdog flag of ADC2

This bit is a copy of the AWD bit in the ADC2_SR register.


RM0090 Rev 21 429/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


Bits 7:6 Reserved, must be kept at reset value.


Bit 5 **OVR1:** Overrun flag of ADC1

This bit is a copy of the OVR bit in the ADC1_SR register.


Bit 4 **STRT1:** Regular channel Start flag of ADC1

This bit is a copy of the STRT bit in the ADC1_SR register.


Bit 3 **JSTRT1:** Injected channel Start flag of ADC1

This bit is a copy of the JSTRT bit in the ADC1_SR register.


Bit 2 **JEOC1:** Injected channel end of conversion of ADC1

This bit is a copy of the JEOC bit in the ADC1_SR register.


Bit 1 **EOC1:** End of conversion of ADC1

This bit is a copy of the EOC bit in the ADC1_SR register.


Bit 0 **AWD1:** Analog watchdog flag of ADC1

This bit is a copy of the AWD bit in the ADC1_SR register.


**13.13.16 ADC common control register (ADC_CCR)**


Address offset: 0x04 (this offset address is relative to ADC1 base address + 0x300)


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24|23|22|21 20 19 18|17 16|Col6|
|---|---|---|---|---|---|
|Reserved|TSVREFE|VBATE|Reserved|ADCPRE|ADCPRE|
|Reserved|rw|rw|rw|rw|rw|


|15 14|Col2|13|12|11 10 9 8|Col6|Col7|Col8|7 6 5|4 3 2 1 0|Col11|Col12|Col13|Col14|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DMA[1:0]|DMA[1:0]|DDS|Res.|DELAY[3:0]|DELAY[3:0]|DELAY[3:0]|DELAY[3:0]|Reserved|MULTI[4:0]|MULTI[4:0]|MULTI[4:0]|MULTI[4:0]|MULTI[4:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:24 Reserved, must be kept at reset value.


Bit 23 **TSVREFE:** Temperature sensor and V REFINT enable
This bit is set and cleared by software to enable/disable the temperature sensor and the
V REFINT channel.
0: Temperature sensor and V REFINT channel disabled
1: Temperature sensor and V REFINT channel enabled

_Note: On STM32F42x and STM32F43x devices, VBATE must be disabled when TSVREFE is_
_set. If both bits are set, only the VBAT conversion is performed._


Bit 22 **VBATE:** V BAT enable
This bit is set and cleared by software to enable/disable the V BAT channel.
0: V BAT channel disabled
1: V BAT channel enabled


Bits 21:18 Reserved, must be kept at reset value.


430/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


Bits 17:16 **ADCPRE:** ADC prescaler

Set and cleared by software to select the frequency of the clock to the ADC. The clock is
common for all the ADCs.

Note: 00: PCLK2 divided by 2
01: PCLK2 divided by 4
10: PCLK2 divided by 6
11: PCLK2 divided by 8


Bits 15:14 **DMA:** Direct memory access mode for multi ADC mode

This bit-field is set and cleared by software. Refer to the DMA controller section for more
details.

00: DMA mode disabled

01: DMA mode 1 enabled (2 / 3 half-words one by one - 1 then 2 then 3)
10: DMA mode 2 enabled (2 / 3 half-words by pairs - 2&1 then 1&3 then 3&2)
11: DMA mode 3 enabled (2 / 3 bytes by pairs - 2&1 then 1&3 then 3&2)


Bit 13 **DDS:** DMA disable selection (for multi-ADC mode)

This bit is set and cleared by software.
0: No new DMA request is issued after the last transfer (as configured in the DMA
controller). DMA bits are not cleared by hardware, however they must have been cleared
and set to the wanted mode by software before new DMA requests can be generated.
1: DMA requests are issued as long as data are converted and DMA = 01, 10 or 11.


Bit 12 Reserved, must be kept at reset value.


RM0090 Rev 21 431/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


Bit 11:8 **DELAY:** Delay between 2 sampling phases

Set and cleared by software. These bits are used in dual or triple interleaved modes.
0000: 5 * T ADCCLK
0001: 6 * T ADCCLK
0010: 7 * T ADCCLK

...

1111: 20 * T ADCCLK


Bits 7:5 Reserved, must be kept at reset value.


Bits 4:0 **MULTI[4:0]:** Multi ADC mode selection

These bits are written by software to select the operating mode.

– All the ADCs independent:
00000: Independent mode

– 00001 to 01001: Dual mode, ADC1 and ADC2 working together, ADC3 is independent
00001: Combined regular simultaneous + injected simultaneous mode
00010: Combined regular simultaneous + alternate trigger mode
00011: Reserved

00101: Injected simultaneous mode only
00110: Regular simultaneous mode only
00111: interleaved mode only
01001: Alternate trigger mode only

– 10001 to 11001: Triple mode: ADC1, 2 and 3 working together
10001: Combined regular simultaneous + injected simultaneous mode
10010: Combined regular simultaneous + alternate trigger mode
10011: Reserved

10101: Injected simultaneous mode only
10110: Regular simultaneous mode only
10111: interleaved mode only
11001: Alternate trigger mode only
All other combinations are reserved and must not be programmed

_Note: In multi mode, a change of channel configuration generates an abort that can cause a_
_loss of synchronization. It is recommended to disable the multi ADC mode before any_
_configuration change._


432/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


**13.13.17 ADC common regular data register for dual and triple modes**
**(ADC_CDR)**


Address offset: 0x08 (this offset address is relative to ADC1 base address + 0x300)


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|DATA2[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|DATA1[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:16 **DATA2[15:0]:** 2nd data item of a pair of regular conversions

– In dual mode, these bits contain the regular data of ADC2. Refer to _Dual ADC mode_ .

– In triple mode, these bits contain alternatively the regular data of ADC2, ADC1 and ADC3.
Refer to _Triple ADC mode_ .


Bits 15:0 **DATA1[15:0]** : 1st data item of a pair of regular conversions

– In dual mode, these bits contain the regular data of ADC1. Refer to _Dual ADC mode_

– In triple mode, these bits contain alternatively the regular data of ADC1, ADC3 and ADC2.
Refer to _Triple ADC mode_ .


**13.13.18 ADC register map**


The following table summarizes the ADC registers.


**Table 72. ADC global register map**

|Offset|Register|
|---|---|
|0x000 - 0x04C|ADC1|
|0x050 - 0x0FC|Reserved|
|0x100 - 0x14C|ADC2|
|0x118 - 0x1FC|Reserved|
|0x200 - 0x24C|ADC3|
|0x250 - 0x2FC|Reserved|
|0x300 - 0x308|Common registers|



RM0090 Rev 21 433/1757



435


**Analog-to-digital converter (ADC)** **RM0090**


**Table 73. ADC register map and reset values for each ADC**





































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**ADC_SR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|OVR|STRT|JSTRT|JEOC|EOC|AWD|
|0x00|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|
|0x04|**ADC_CR1**|Reserved|Reserved|Reserved|Reserved|Reserved|OVRIE|RES[1:0]|RES[1:0]|AWDEN|JAWDEN|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|DISC<br>NUM [2:0]|DISC<br>NUM [2:0]|DISC<br>NUM [2:0]|JDISCEN|DISCEN|JAUTO|AWD SGL|SCAN|JEOCIE|AWDIE|EOCIE|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|
|0x04|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x08|**ADC_CR2**|Re<br>se<br>rv<br>ed|SWSTART|EXTEN[1:0]|EXTEN[1:0]|EXTSEL [3:0]|EXTSEL [3:0]|EXTSEL [3:0]|EXTSEL [3:0]|Re<br>se<br>rv<br>ed|JSWSTART|JEXTEN[1:0]|JEXTEN[1:0]|JEXTSEL<br>[3:0]|JEXTSEL<br>[3:0]|JEXTSEL<br>[3:0]|JEXTSEL<br>[3:0]|Reserved|Reserved|Reserved|Reserved|ALIGN|EOCS|DDS|DMA|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CONT|ADON|
|0x08|Reset value||0|0|0|0|0|0|0||0|0|0|0|0|0|0|0|0|0|0|0|0||0|0|0|0|0|0|0|0|0|
|0x0C|**ADC_SMPR1**|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|
|0x0C|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**ADC_SMPR2**|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|Sample time bits SMPx_x|
|0x10|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x14|**ADC_JOFR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JOFFSET1[11:0]|JOFFSET1[11:0]|JOFFSET1[11:0]|JOFFSET1[11:0]|JOFFSET1[11:0]|JOFFSET1[11:0]|JOFFSET1[11:0]|JOFFSET1[11:0]|JOFFSET1[11:0]|JOFFSET1[11:0]|JOFFSET1[11:0]|JOFFSET1[11:0]|
|0x14|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|
|0x18|**ADC_JOFR2**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JOFFSET2[11:0]|JOFFSET2[11:0]|JOFFSET2[11:0]|JOFFSET2[11:0]|JOFFSET2[11:0]|JOFFSET2[11:0]|JOFFSET2[11:0]|JOFFSET2[11:0]|JOFFSET2[11:0]|JOFFSET2[11:0]|JOFFSET2[11:0]|JOFFSET2[11:0]|
|0x18|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|
|0x1C|**ADC_JOFR3**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JOFFSET3[11:0]|JOFFSET3[11:0]|JOFFSET3[11:0]|JOFFSET3[11:0]|JOFFSET3[11:0]|JOFFSET3[11:0]|JOFFSET3[11:0]|JOFFSET3[11:0]|JOFFSET3[11:0]|JOFFSET3[11:0]|JOFFSET3[11:0]|JOFFSET3[11:0]|
|0x1C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|
|0x20|**ADC_JOFR4**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JOFFSET4[11:0]|JOFFSET4[11:0]|JOFFSET4[11:0]|JOFFSET4[11:0]|JOFFSET4[11:0]|JOFFSET4[11:0]|JOFFSET4[11:0]|JOFFSET4[11:0]|JOFFSET4[11:0]|JOFFSET4[11:0]|JOFFSET4[11:0]|JOFFSET4[11:0]|
|0x20|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|
|0x24|**ADC_HTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|
|0x24|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|1|1|1|1|1|1|1|1|1|1|1|1|
|0x28|**ADC_LTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|
|0x28|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|
|0x2C|**ADC_SQR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|L[3:0]|L[3:0]|L[3:0]|L[3:0]|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|
|0x2C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x30|**ADC_SQR2**|Reserved|Reserved|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|
|0x30|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x34|**ADC_SQR3**|Reserved|Reserved|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|Regular channel sequence SQx_x bits|
|0x34|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x38|**ADC_JSQR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JL[1:0]|JL[1:0]|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|Injected channel sequence JSQx_x bits|
|0x38|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x3C|**ADC_JDR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|
|0x3C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x40|**ADC_JDR2**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|
|0x40|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x44|**ADC_JDR3**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|
|0x44|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x48|**ADC_JDR4**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|JDATA[15:0]|
|0x48|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x4C|**ADC_DR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|Regular DATA[15:0]|
|0x4C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


434/1757 RM0090 Rev 21


**RM0090** **Analog-to-digital converter (ADC)**


**Table 74. ADC register map and reset values (common ADC registers)**













|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**ADC_CSR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|OVR|STRT|JSTRT|JEOC|EOC|AWD|Reserved|Reserved|OVR|STRT|JSTRT|JEOC|EOC|AWD|Reserved|Reserved|OVR|STRT|JSTRT|JEOC|EOC|AWD|
|0x00|**ADC_CSR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00||||||||||||ADC3|ADC3|ADC3|ADC3|ADC3|ADC3|ADC3|ADC3|ADC2|ADC2|ADC2|ADC2|ADC2|ADC2|ADC2|ADC2|ADC1|ADC1|ADC1|ADC1|ADC1|ADC1|
|0x04|**ADC_CCR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|TSVREFE|VBATE|Reserved|Reserved|Reserved|Reserved|ADCPRE[1:0]|ADCPRE[1:0]|DMA[1:0]|DMA[1:0]|DDS|Reserved|DELAY [3:0]|DELAY [3:0]|DELAY [3:0]|DELAY [3:0]|Reserved|Reserved|Reserved|MULTI [4:0]|MULTI [4:0]|MULTI [4:0]|MULTI [4:0]|MULTI [4:0]|
|0x04|**ADC_CCR**<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x08|**ADC_CDR**<br>Reset value|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA2[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|Regular DATA1[15:0]|
|0x08|**ADC_CDR**<br>Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


Refer to _Section 2.3: Memory map_ for the register boundary addresses.


RM0090 Rev 21 435/1757



435


