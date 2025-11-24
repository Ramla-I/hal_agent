**RM0091** **Analog-to-digital converter (ADC)**

# **13 Analog-to-digital converter (ADC)**

## **13.1 Introduction**


The 12-bit ADC is a successive approximation analog-to-digital converter. It has up to 19
multiplexed channels allowing it to measure signals from 16 external and 3 internal sources.
A/D conversion of the various channels can be performed in single, continuous, scan or
discontinuous mode. The result of the ADC is stored in a left-aligned or right-aligned 16-bit
data register.


The analog watchdog feature allows the application to detect if the input voltage goes
outside the user-defined higher or lower thresholds.


An efficient low-power mode is implemented to allow very low consumption at low
frequency.


RM0091 Rev 10 233/1017



275


**Analog-to-digital converter (ADC)** **RM0091**

## **13.2 ADC main features**


      - High performance


–
12-bit, 10-bit, 8-bit or 6-bit configurable resolution


–
ADC conversion time: 1.0 µs for 12-bit resolution (1 MHz), 0.93 µs conversion
time for 10-bit resolution, faster conversion times can be obtained by lowering
resolution.


– Self-calibration


–
Programmable sampling time


–
Data alignment with built-in data coherency


–
DMA support


      - Low-power


–
The application can reduce PCLK frequency for low-power operation while still
keeping optimum ADC performance. For example, 1.0 µs conversion time is kept,
whatever the PCLK frequency


–
Wait mode: prevents ADC overrun in applications with low PCLK frequency


–
Auto off mode: ADC is automatically powered off except during the active
conversion phase. This dramatically reduces the power consumption of the ADC.


      - Analog input channels


–
16 external analog inputs


–
1 channel for internal temperature sensor (V SENSE )


–
1 channel for internal reference voltage (V REFINT )


–
1 channel for monitoring external V BAT power supply pin


      - Start-of-conversion can be initiated:


–
By software


–
By hardware triggers with configurable polarity (timer events)


      - Conversion modes


–
Can convert a single channel or can scan a sequence of channels.


–
Single mode converts selected inputs once per trigger


–
Continuous mode converts selected inputs continuously


– Discontinuous mode


      - Interrupt generation at the end of sampling, end of conversion, end of sequence
conversion, and in case of analog watchdog or overrun events


      - Analog watchdog


      - ADC input range: V SSA ≤ V IN ≤ V DDA


234/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**

## **13.3 ADC functional description**



_Figure 26_ shows the ADC block diagram and _Table 41_ gives the ADC pin description.


**Figure 26. ADC block diagram**





































**13.3.1** **ADC pins and internal signals**


**Table 41. ADC input/output pins**







|Name|Signal type|Remarks|
|---|---|---|
|VDDA|Input, analog power<br>supply|Analog power supply and positive reference voltage<br>for the ADC|
|VSSA|Input, analog supply<br>ground|Ground for analog power supply|
|ADC_INx|Analog input signals|16 external analog input channels|


RM0091 Rev 10 235/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


**Table 42. ADC internal input/output signals**

|Internal signal<br>name|Signal type|Description|
|---|---|---|
|VIN[x]|Analog Input<br>channels|Connected either to internal channels or to ADC_IN_i _<br>external channels|
|TRGx|Input|ADC conversion triggers|
|VSENSE|Input|Internal temperature sensor output voltage|
|VREFINT|Input|Internal voltage reference output voltage|
|VBAT/2|Input|VBAT pin input voltage divided by 2|
|ADC_AWDx_OUT|Output|Internal analog watchdog output signal connected to on-<br>chip timers (x = Analog watchdog number = 1)|



**Table 43. External triggers**

|Name|Source|EXTSEL[2:0]|
|---|---|---|
|TRG0|TIM1_TRGO|000|
|TRG1|TIM1_CC4|001|
|TRG2|TIM2_TRGO|010|
|TRG3|TIM3_TRGO|011|
|TRG4|TIM15_TRGO|100|
|TRG5|Reserved|101|
|TRG6|Reserved|110|
|TRG7|Reserved|111|



**13.3.2** **Calibration (ADCAL)**


The ADC has a calibration feature. During the calibration phase, the ADC calculates a
calibration factor which is internally applied to the ADC until the next ADC power-off. The
application must not use the ADC during calibration and must wait until it is complete.


Calibration should be performed before starting A/D conversion. It removes the offset error
which may vary from chip to chip due to process variation.


The calibration is initiated by software by setting ADCAL bit to 1. It can only be initiated
when the ADC is disabled (when ADEN = 0). ADCAL bit stays at 1 during the whole
calibration sequence. It is then cleared by hardware as soon the calibration completes. After
this, the calibration factor can be read from the ADC_DR register (from bits 6 to 0).


The internal analog calibration is kept if the ADC is disabled (ADEN = 0). When the ADC
operating conditions change (V DDA changes are the main contributor to ADC offset
variations and temperature change to a lesser extend), it is recommended to re-run a
calibration cycle.


The calibration factor is lost each time power is removed from the ADC (for example when
the product enters Standby mode).


236/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


**Calibration software procedure**


1. Ensure that ADEN = 0 and DMAEN = 0.


2. Set ADCAL = 1.


3. Wait until ADCAL = 0.


4. The calibration factor can be read from bits 6:0 of ADC_DR.


For code example refer to the Appendix section _A.7.1: ADC calibration code example_ .


**Figure 27. ADC calibration**











**13.3.3** **ADC on-off control (ADEN, ADDIS, ADRDY)**


At power-up, the ADC is disabled and put in power-down mode (ADEN = 0).


As shown in _Figure 28_, the ADC needs a stabilization time of t STAB before it starts
converting accurately.


Two control bits are used to enable or disable the ADC:


      - Set ADEN = 1 to enable the ADC. The ADRDY flag is set as soon as the ADC is ready
for operation.


      - Set ADDIS = 1 to disable the ADC and put the ADC in power down mode. The ADEN
and ADDIS bits are then automatically cleared by hardware as soon as the ADC is fully
disabled.


Conversion can then start either by setting ADSTART to 1 (refer to _Section 13.4: Conversion_
_on external trigger and trigger polarity (EXTSEL, EXTEN) on page 244_ ) or when an external
trigger event occurs if triggers are enabled.


Follow this procedure to enable the ADC:


1. Clear the ADRDY bit in ADC_ISR register by programming this bit to 1.


2. Set ADEN = 1 in the ADC_CR register.


3. Wait until ADRDY = 1 in the ADC_ISR register and continue to write ADEN = 1
(ADRDY is set after the ADC startup time). This can be handled by interrupt if the
interrupt is enabled by setting the ADRDYIE bit in the ADC_IER register.


For code example refer to the Appendix section _A.7.2: ADC enable sequence code_
_example_ .


RM0091 Rev 10 237/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


Follow this procedure to disable the ADC:


1. Check that ADSTART = 0 in the ADC_CR register to ensure that no conversion is
ongoing. If required, stop any ongoing conversion by writing 1 to the ADSTP bit in the
ADC_CR register and waiting until this bit is read at 0.


2. Set ADDIS = 1 in the ADC_CR register.


3. If required by the application, wait until ADEN = 0 in the ADC_CR register, indicating
that the ADC is fully disabled (ADDIS is automatically reset once ADEN = 0).


4. Clear the ADRDY bit in ADC_ISR register by programming this bit to 1 (optional).


For code example refer to the Appendix section _A.7.3: ADC disable sequence code_
_example_ .


**Caution:** ADEN bit cannot be set when ADCAL = 1 and during four ADC clock cycles after the
ADCAL bit is cleared by hardware (end of calibration).


**Figure 28. Enabling/disabling the ADC**


_Note:_ _In Auto-off mode (AUTOFF = 1) the power-on/off phases are performed automatically, by_
_hardware and the ADRDY flag is not set._


238/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


**13.3.4** **ADC clock (CKMODE)**


The ADC has a dual clock-domain architecture, so that the ADC can be fed with a clock
(ADC asynchronous clock) independent from the APB clock (PCLK).


**Figure 29. ADC clock scheme**



















1. Refer to _Section Reset and clock control (RCC_ ) for how the PCLK clock and ADC asynchronous clock are
enabled.


The input clock of the analog ADC can be selected between two different clock sources (see
_Figure 29: ADC clock scheme_ to see how the PCLK clock and the ADC asynchronous clock
are enabled):


a) The ADC clock can be a specific clock source, named “ADC asynchronous clock“
which is independent and asynchronous with the APB clock.


Refer to RCC Section for more information on generating this clock source.


To select this scheme, bits CKMODE[1:0] of the ADC_CFGR2 register must be
reset.


For code example refer to the Appendix section _A.7.4: ADC clock selection code_
_example_ .


b) The ADC clock can be derived from the APB clock of the ADC bus interface,
divided by a programmable factor (1, 2 or 4) according to bits CKMODE[1:0].


To select this scheme, bits CKMODE[1:0] of the ADC_CFGR2 register must be
different from “00”.


Option a) has the advantage of reaching the maximum ADC clock frequency whatever the
APB clock scheme selected.


Option b) has the advantage of bypassing the clock domain resynchronizations. This can be
useful when the ADC is triggered by a timer and if the application requires that the ADC is
precisely triggered without any uncertainty (otherwise, an uncertainty of the trigger instant is
added by the resynchronizations between the two clock domains).


RM0091 Rev 10 239/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


**Table 44. Latency between trigger and start of conversion** **[(1)]**

|ADC clock source|CKMODE[1:0]|Latency between the trigger event<br>and the start of conversion|
|---|---|---|
|Dedicated 14MHz clock|00|Latency is not deterministic (jitter)|
|PCLK divided by 2|01|Latency is deterministic (no jitter) and equal to<br>2.75 ADC clock cycles|
|PCLK divided by 4|10|Latency is deterministic (no jitter) and equal to<br>2.625 ADC clock cycles|



1. Refer to the device datasheet for the maximum ADC_CLK frequency.


**13.3.5** **Configuring the ADC**


The software must write the ADCAL and ADEN bits in the ADC_CR register only when the
ADC is disabled (ADEN cleared).


The software must only write to the ADSTART and ADDIS bits in the ADC_CR register only
if the ADC is enabled and there is no pending request to disable the ADC (ADEN = 1 and
ADDIS = 0).


For all the other control bits in the ADC_IER, ADC_CFGRi, ADC_SMPR, ADC_TR,
ADC_CHSELR and ADC_CCR registers, refer to the description of the corresponding
control bit in _Section 13.11: ADC registers_ .


The software must only write to the ADSTP bit in the ADC_CR register if the ADC is enabled
(and possibly converting) and there is no pending request to disable the ADC (ADSTART =
1 and ADDIS = 0).


_Note:_ _There is no hardware protection preventing software from making write operations forbidden_
_by the above rules. If such a forbidden write access occurs, the ADC may enter an_
_undefined state. To recover correct operation in this case, the ADC must be disabled (clear_
_ADEN = 0 and all the bits in the ADC_CR register)._


**13.3.6** **Channel selection (CHSEL, SCANDIR)**


There are up to 19 multiplexed channels:


      - 16 analog inputs from GPIO pins (ADC_INx)


      - 3 internal analog inputs (temperature sensor, internal reference voltage, V BAT channel)


It is possible to convert a single channel or a sequence of channels.


The sequence of the channels to be converted can be programmed in the ADC_CHSELR
channel selection register: each analog input channel has a dedicated selection bit
(CHSELx).


The order in which the channels is scanned can be configured by programming the bit
SCANDIR bit in the ADC_CFGR1 register:


      - SCANDIR = 0: forward scan Channel 0 to Channel 18


      - SCANDIR = 1: backward scan Channel 18 to Channel 0


**Temperature sensor, V** **REFINT** **and V** **BAT** **internal channels**


The temperature sensor is connected to channel ADC V IN [16].


240/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


The internal voltage reference V REFINT is connected to channel ADC V IN [17].


V BAT channel is connected to ADC V IN [18] channel.


**13.3.7** **Programmable sampling time (SMP)**


Before starting a conversion, the ADC needs to establish a direct connection between the
voltage source to be measured and the embedded sampling capacitor of the ADC. This
sampling time must be enough for the input voltage source to charge the sample and hold
capacitor to the input voltage level.


Having a programmable sampling time allows the conversion speed to be trimmed
according to the input resistance of the input voltage source.


The ADC samples the input voltage for a number of ADC clock cycles that can be modified
using the SMP[2:0] bits in the ADC_SMPR register.


This programmable sampling time is common to all channels. If required by the application,
the software can change and adapt this sampling time between each conversions.


The total conversion time is calculated as follows:


t CONV = Sampling time + 12.5 x ADC clock cycles


Example:


With ADC_CLK = 14 MHz and a sampling time of 1.5 ADC clock cycles:


t CONV = 1.5 + 12.5 = 14 ADC clock cycles = 1 µs


The ADC indicates the end of the sampling phase by setting the EOSMP flag.


**13.3.8** **Single conversion mode (CONT** _=_ **0)**


In Single conversion mode, the ADC performs a single sequence of conversions, converting
all the channels once. This mode is selected when CONT _=_ 0 in the ADC_CFGR1 register.
Conversion is started by either:


      - Setting the ADSTART bit in the ADC_CR register


      - Hardware trigger event


Inside the sequence, after each conversion is complete:


      - The converted data are stored in the 16-bit ADC_DR register


      - The EOC (end of conversion) flag is set


      - An interrupt is generated if the EOCIE bit is set


After the sequence of conversions is complete:


      - The EOS (end of sequence) flag is set


      - An interrupt is generated if the EOSIE bit is set


Then the ADC stops until a new external trigger event occurs or the ADSTART bit is set
again.


_Note:_ _To convert a single channel, program a sequence with a length of 1._


RM0091 Rev 10 241/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


**13.3.9** **Continuous conversion mode (CONT** _=_ **1)**


In continuous conversion mode, when a software or hardware trigger event occurs, the ADC
performs a sequence of conversions, converting all the channels once and then
automatically re-starts and continuously performs the same sequence of conversions. This
mode is selected when CONT _=_ 1 in the ADC_CFGR1 register. Conversion is started by
either:


      - Setting the ADSTART bit in the ADC_CR register


      - Hardware trigger event


Inside the sequence, after each conversion is complete:


      - The converted data are stored in the 16-bit ADC_DR register


      - The EOC (end of conversion) flag is set


      - An interrupt is generated if the EOCIE bit is set


After the sequence of conversions is complete:


      - The EOS (end of sequence) flag is set


      - An interrupt is generated if the EOSIE bit is set


Then, a new sequence restarts immediately and the ADC continuously repeats the
conversion sequence.


_Note:_ _To convert a single channel, program a sequence with a length of 1._


_It is not possible to have both discontinuous mode and continuous mode enabled: it is_
_forbidden to set both bits DISCEN = 1 and CONT = 1._


**13.3.10** **Starting conversions (ADSTART)**


Software starts ADC conversions by setting ADSTART _=_ 1.


When ADSTART is set, the conversion:


      - Starts immediately if EXTEN _=_ 00 (software trigger)


      - At the next active edge of the selected hardware trigger if EXTEN ≠ 00


The ADSTART bit is also used to indicate whether an ADC operation is currently ongoing. It
is possible to re-configure the ADC while ADSTART _=_ 0, indicating that the ADC is idle.


The ADSTART bit is cleared by hardware:


      - In single mode with software trigger (CONT _=_ 0, EXTEN _=_ 00)


– At any end of conversion sequence (EOS _=_ 1)


      - In discontinuous mode with software trigger (CONT _=_ 0, DISCEN _=_ 1, EXTEN _=_ 00)


– At end of conversion (EOC _=_ 1)


      - In all cases (CONT _=_ x, EXTEN _=_ XX)


–
After execution of the ADSTP procedure invoked by software (see
_Section 13.3.12: Stopping an ongoing conversion (ADSTP) on page 244_ )


_Note:_ _In continuous mode (CONT = 1), the ADSTART bit is not cleared by hardware when the_
_EOS flag is set because the sequence is automatically relaunched._


_When hardware trigger is selected in single mode (CONT = 0 and EXTEN =_ 01 _), ADSTART_
_is not cleared by hardware when the EOS flag is set (except if DMAEN = 1 and_
_DMACFG = 0 in which case ADSTART is cleared at end of the DMA transfer). This avoids_


242/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


_the need for software having to set the ADSTART bit again and ensures the next trigger_
_event is not missed._


**13.3.11** **Timings**


The elapsed time between the start of a conversion and the end of conversion is the sum of
the configured sampling time plus the successive approximation time depending on data
resolution:


t CONV = t SMPL + t SAR = [1.5 |min + 12.5 |12bit ] x t ADC_CLK


t CONV = t SMPL + t SAR = 107.1 ns |min + 892.8 ns |12bit = 1 µs |min (for f ADC_CLK = 14 MHz)


**Figure 30. Analog to digital conversion time**



































**Figure 31. ADC conversion timings**










|Rea|dy|S0|Conversion 0 S1 Conversion 1|S2 Conversion 2 S3|Col6|Conversion 3|
|---|---|---|---|---|---|---|
|Rea|||||||
|Rea|||||||



1. EXTEN _=_ 00 or EXTEN ≠ 00


2. Trigger latency (refer to datasheet for more details)


3. ADC_DR register write latency (refer to datasheet for more details)


RM0091 Rev 10 243/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


**13.3.12** **Stopping an ongoing conversion (ADSTP)**


The software can decide to stop any ongoing conversions by setting ADSTP _=_ 1 in the
ADC_CR register.


This resets the ADC operation and the ADC is idle, ready for a new operation.


When the ADSTP bit is set by software, any ongoing conversion is aborted and the result is
discarded (ADC_DR register is not updated with the current conversion).


The scan sequence is also aborted and reset (meaning that restarting the ADC would restart a new sequence).


Once this procedure is complete, the ADSTP and ADSTART bits are both cleared by
hardware and the software must wait until ADSTART=0 before starting new conversions.


**Figure 32. Stopping an ongoing conversion**


















## **13.4 Conversion on external trigger and trigger polarity (EXTSEL,** **EXTEN)**

A conversion or a sequence of conversion can be triggered either by software or by an
external event (for example timer capture). If the EXTEN[1:0] control bits are not equal to
“0b00”, then external events are able to trigger a conversion with the selected polarity. The
trigger selection is effective once software has set bit ADSTART _=_ 1.


Any hardware triggers which occur while a conversion is ongoing are ignored.


If bit ADSTART _=_ 0, any hardware triggers which occur are ignored.


_Table 45_ provides the correspondence between the EXTEN[1:0] values and the trigger
polarity.


**Table 45. Configuring the trigger polarity**

|Source|EXTEN[1:0]|
|---|---|
|Trigger detection disabled|00|
|Detection on rising edge|01|
|Detection on falling edge|10|
|Detection on both rising and falling edges|11|



_Note:_ _The polarity of the external trigger can be changed only when the ADC is not converting_
_(ADSTART = 0)._


The EXTSEL[2:0] control bits are used to select which of 8 possible events can trigger
conversions.


244/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


Refer to _Table 43: External triggers_ in _Section 13.3.1: ADC pins and internal signals_ for the
list of all the external triggers that can be used for regular conversion.


The software source trigger events can be generated by setting the ADSTART bit in the
ADC_CR register.


_Note:_ _The trigger selection can be changed only when the ADC is not converting (ADSTART = 0)._


**13.4.1** **Discontinuous mode (DISCEN)**


This mode is enabled by setting the DISCEN bit in the ADC_CFGR1 register.


In this mode (DISCEN _=_ 1), a hardware or software trigger event is required to start each
conversion defined in the sequence. On the contrary, if DISCEN _=_ 0, a single hardware or
software trigger event successively starts all the conversions defined in the sequence.


Example:


      - DISCEN _=_ 1, channels to be converted = 0, 3, 7, 10


–
1st trigger: channel 0 is converted and an EOC event is generated


–
2nd trigger: channel 3 is converted and an EOC event is generated


–
3rd trigger: channel 7 is converted and an EOC event is generated


–
4th trigger: channel 10 is converted and both EOC and EOS events are
generated.


–
5th trigger: channel 0 is converted an EOC event is generated


–
6th trigger: channel 3 is converted and an EOC event is generated


– ...


      - DISCEN _=_ 0, channels to be converted = 0, 3, 7, 10


–
1st trigger: the complete sequence is converted: channel 0, then 3, 7 and 10. Each
conversion generates an EOC event and the last one also generates an EOS
event.


–
Any subsequent trigger events restarts the complete sequence.


_Note:_ _It is not possible to have both discontinuous mode and continuous mode enabled: it is_
_forbidden to set both bits DISCEN = 1 and CONT = 1._


**13.4.2** **Programmable resolution (RES) - Fast conversion mode**


It is possible to obtain faster conversion times (t SAR ) by reducing the ADC resolution.


The resolution can be configured to be either 12, 10, 8, or 6 bits by programming the
RES[1:0] bits in the ADC_CFGR1 register. Lower resolution allows faster conversion times
for applications where high data precision is not required.


_Note:_ _The RES[1:0] bit must only be changed when the ADEN bit is reset._


The result of the conversion is always 12 bits wide and any unused LSB bits are read as

zeros.


Lower resolution reduces the conversion time needed for the successive approximation
steps as shown in _Table 46_ .


RM0091 Rev 10 245/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


**Table 46. t** **SAR** **timings depending on resolution**















|RES[1:0]<br>bits|t<br>SAR<br>(ADC clock<br>cycles)|t (ns) at<br>SAR<br>f = 14 MHz<br>ADC|t<br>SMPL (min)<br>(ADC clock<br>cycles)|t<br>CONV<br>(ADC clock cycles)<br>(with min. t<br>SMPL)|t (ns) at<br>CONV<br>f = 14 MHz<br>ADC|
|---|---|---|---|---|---|
|12|12.5|893|1.5|14|1000|
|10|11.5|821|1.5|13|928|
|8|9.5|678|1.5|11|785|
|6|7.5|535|1.5|9|643|


**13.4.3** **End of conversion, end of sampling phase (EOC, EOSMP flags)**


The ADC indicates each end of conversion (EOC) event.


The ADC sets the EOC flag in the ADC_ISR register as soon as a new conversion data
result is available in the ADC_DR register. An interrupt can be generated if the EOCIE bit is
set in the ADC_IER register. The EOC flag is cleared by software either by writing 1 to it, or
by reading the ADC_DR register.


The ADC also indicates the end of sampling phase by setting the EOSMP flag in the
ADC_ISR register. The EOSMP flag is cleared by software by writing1 to it. An interrupt can
be generated if the EOSMPIE bit is set in the ADC_IER register.


The aim of this interrupt is to allow the processing to be synchronized with the conversions.
Typically, an analog multiplexer can be accessed in hidden time during the conversion
phase, so that the multiplexer is positioned when the next sampling starts.


_Note:_ _As there is only a very short time left between the end of the sampling and the end of the_
_conversion, it is recommenced to use polling or a WFE instruction rather than an interrupt_
_and a WFI instruction._


**13.4.4** **End of conversion sequence (EOS flag)**


The ADC notifies the application of each end of sequence (EOS) event.


The ADC sets the EOS flag in the ADC_ISR register as soon as the last data result of a
conversion sequence is available in the ADC_DR register. An interrupt can be generated if
the EOSIE bit is set in the ADC_IER register. The EOS flag is cleared by software by writing
1 to it.


246/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


**13.4.5** **Example timing diagrams (single/continuous modes**
**hardware/software triggers)**


**Figure 33. Single conversions of a sequence, software trigger**













1. EXTEN = 00, CONT = 0


2. CHSEL = 0x20601, WAIT = 0, AUTOFF = 0


For code example refer to the Appendix section _A.7.5: Single conversion sequence code_
_example - Software trigger_ .


**Figure 34. Continuous conversion of a sequence, software trigger**























1. EXTEN = 00, CONT = 1,


2. CHSEL = 0x20601, WAIT = 0, AUTOFF = 0


For code example refer to the Appendix section _A.7.6: Continuous conversion sequence_
_code example - Software trigger_ .


RM0091 Rev 10 247/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


**Figure 35. Single conversions of a sequence, hardware trigger**

















1. EXTSEL = TRGx (over-frequency), EXTEN = 01 (rising edge), CONT = 0


2. CHSEL = 0xF, SCANDIR = 0, WAIT = 0, AUTOFF = 0


For code example refer to the Appendix section _A.7.7: Single conversion sequence code_
_example - Hardware trigger_ .


**Figure 36. Continuous conversions of a sequence, hardware trigger**























1. EXTSEL = TRGx, EXTEN = 10 (falling edge), CONT = 1


2. CHSEL = 0xF, SCANDIR = 0, WAIT = 0, AUTOFF = 0


For code example refer to the Appendix section _A.7.8: Continuous conversion sequence_
_code example - Hardware trigger_ .


248/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**

## **13.5 Data management**


**13.5.1** **Data register and data alignment (ADC_DR, ALIGN)**


At the end of each conversion (when an EOC event occurs), the result of the converted data
is stored in the ADC_DR data register which is 16-bit wide.


The format of the ADC_DR depends on the configured data alignment and resolution.


The ALIGN bit in the ADC_CFGR1 register selects the alignment of the data stored after
conversion. Data can be right-aligned (ALIGN = 0) or left-aligned (ALIGN = 1) as shown in
_Figure 37_ .


**Figure 37. Data alignment and resolution**




















|ALIGN|RES|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|Col17|Col18|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ALIGN|RES|||||||||||||||||
|0|0x0||~~0~~|x0|||||||DR|[11:0|]|||||
|0|0x1|||0|x00|||||||D|R[9:0|]||||
|0|0x2||||0|x00|||||||D|R[7:0]||||
|0|0x3|||||0|x00|||||||D|R[5:0|]||
|1|0x0||||||D|R[11:|0]|||||||0x0||
|1|0x1|||||DR|[9:0]||||||||0x00|||
|1|0x2||||DR|[7:0]||||||||0x00||||
|1|0x3||||0x0|0|||||DR|[5:0]||||0x|0|



**13.5.2** **ADC overrun (OVR, OVRMOD)**


The overrun flag (OVR) indicates a data overrun event, when the converted data was not
read in time by the CPU or the DMA, before the data from a new conversion is available.


The OVR flag is set in the ADC_ISR register if the EOC flag is still at ‘1’ at the time when a
new conversion completes. An interrupt can be generated if the OVRIE bit is set in the
ADC_IER register.


When an overrun condition occurs, the ADC keeps operating and can continue to convert
unless the software decides to stop and reset the sequence by setting the ADSTP bit in the
ADC_CR register.


The OVR flag is cleared by software by writing 1 to it.


It is possible to configure if the data is preserved or overwritten when an overrun event
occurs by programming the OVRMOD bit in the ADC_CFGR1 register:


      - OVRMOD = 0


–
An overrun event preserves the data register from being overwritten: the old data
is maintained and the new conversion is discarded. If OVR remains at 1, further
conversions can be performed but the resulting data is discarded.


      - OVRMOD = 1


–
The data register is overwritten with the last conversion result and the previous
unread data is lost. If OVR remains at 1, further conversions can be performed
and the ADC_DR register always contains the data from the latest conversion.


RM0091 Rev 10 249/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


**Figure 38. Example of overrun (OVR)**












|OVERRUN|Col2|
|---|---|
|||









**13.5.3** **Managing a sequence of data converted without using the DMA**


If the conversions are slow enough, the conversion sequence can be handled by software.
In this case the software must use the EOC flag and its associated interrupt to handle each
data result. Each time a conversion is complete, the EOC bit is set in the ADC_ISR register
and the ADC_DR register can be read. The OVRMOD bit in the ADC_CFGR1 register
should be configured to 0 to manage overrun events as an error.


**13.5.4** **Managing converted data without using the DMA without overrun**


It may be useful to let the ADC convert one or more channels without reading the data after
each conversion. In this case, the OVRMOD bit must be configured at 1 and the OVR flag
should be ignored by the software. When OVRMOD = 1, an overrun event does not prevent
the ADC from continuing to convert and the ADC_DR register always contains the latest
conversion data.


**13.5.5** **Managing converted data using the DMA**


Since all converted channel values are stored in a single data register, it is efficient to use
DMA when converting more than one channel. This avoids losing the conversion data
results stored in the ADC_DR register.


250/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


When DMA mode is enabled (DMAEN bit set in the ADC_CFGR1 register), a DMA request
is generated after the conversion of each channel. This allows the transfer of the converted
data from the ADC_DR register to the destination location selected by the software.


_Note:_ _The DMAEN bit in the ADC_CFGR1 register must be set after the ADC calibration phase._


Despite this, if an overrun occurs (OVR = 1) because the DMA could not serve the DMA
transfer request in time, the ADC stops generating DMA requests and the data
corresponding to the new conversion is not transferred by the DMA. Which means that all
the data transferred to the RAM can be considered as valid.


Depending on the configuration of OVRMOD bit, the data is either preserved or overwritten
(refer to _Section 13.5.2: ADC overrun (OVR, OVRMOD) on page 249_ ).


The DMA transfer requests are blocked until the software clears the OVR bit.


Two different DMA modes are proposed depending on the application use and are
configured with bit DMACFG in the ADC_CFGR1 register:


      - DMA one shot mode (DMACFG = 0).
This mode should be selected when the DMA is programmed to transfer a fixed
number of data words.


      - DMA circular mode (DMACFG = 1)
This mode should be selected when programming the DMA in circular mode or double
buffer mode.


**DMA one shot mode (DMACFG** = **0)**


In this mode, the ADC generates a DMA transfer request each time a new conversion data
word is available and stops generating DMA requests once the DMA has reached the last
DMA transfer (when a transfer complete interrupt occurs, see _Section 10: Direct memory_
_access controller (DMA) on page 188_ ) even if a conversion has been started again.


For code example refer to the Appendix section _A.7.9: DMA one shot mode sequence code_
_example_ .


When the DMA transfer is complete (all the transfers configured in the DMA controller have
been done):


      - The content of the ADC data register is frozen.


      - Any ongoing conversion is aborted and its partial result discarded


      - No new DMA request is issued to the DMA controller. This avoids generating an
overrun error if there are still conversions which are started.


      - The scan sequence is stopped and reset


      - The DMA is stopped


**DMA circular mode (DMACFG** = **1)**


In this mode, the ADC generates a DMA transfer request each time a new conversion data
word is available in the data register, even if the DMA has reached the last DMA transfer.
This allows the DMA to be configured in circular mode to handle a continuous analog input
data stream.


For code example refer to the Appendix section _A.7.10: DMA circular mode sequence code_
_example_ .


RM0091 Rev 10 251/1017



275


**Analog-to-digital converter (ADC)** **RM0091**

## **13.6 Low-power features**


**13.6.1** **Wait mode conversion**


Wait mode conversion can be used to simplify the software as well as optimizing the
performance of applications clocked at low frequency where there might be a risk of ADC
overrun occurring.


When the WAIT bit is set in the ADC_CFGR1 register, a new conversion can start only if the
previous data has been treated, once the ADC_DR register has been read or if the EOC bit
has been cleared.


This is a way to automatically adapt the speed of the ADC to the speed of the system that
reads the data.


_Note:_ _Any hardware triggers which occur while a conversion is ongoing or during the wait time_
_preceding the read access are ignored._


**Figure 39. Wait mode conversion (continuous mode, software trigger)**













1. EXTEN = 00, CONT = 1


2. CHSEL = 0x3, SCANDIR = 0, WAIT = 1, AUTOFF = 0


For code example refer to the Appendix section _A.7.11: Wait mode sequence code_
_example_ .


252/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


**13.6.2** **Auto-off mode (AUTOFF)**


The ADC has an automatic power management feature which is called auto-off mode, and
is enabled by setting AUTOFF = 1 in the ADC_CFGR1 register.


When AUTOFF = 1, the ADC is always powered off when not converting and automatically
wakes-up when a conversion is started (by software or hardware trigger). A startup-time is
automatically inserted between the trigger event which starts the conversion and the
sampling time of the ADC. The ADC is then automatically disabled once the sequence of
conversions is complete.


Auto-off mode can cause a dramatic reduction in the power consumption of applications
which need relatively few conversions or when conversion requests are timed far enough
apart (for example with a low frequency hardware trigger) to justify the extra power and
extra time used for switching the ADC on and off.


Auto-off mode can be combined with the wait mode conversion (WAIT = 1) for applications
clocked at low frequency. This combination can provide significant power savings if the ADC
is automatically powered-off during the wait phase and restarted as soon as the ADC_DR
register is read by the application (see _Figure 41: Behavior with WAIT = 1, AUTOFF = 1_ ).


**Figure 40. Behavior with WAIT = 0, AUTOFF = 1**











1. EXTSEL = TRGx, EXTEN = 01 (rising edge), CONT = x, ADSTART = 1, CHSEL = 0xF, SCANDIR = 0, WAIT = 1,
AUTOFF = 1


For code example refer to the Appendix section _A.7.12: Auto Off and no wait mode_
_sequence code example_ .


RM0091 Rev 10 253/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


**Figure 41. Behavior with WAIT = 1, AUTOFF = 1**










|Col1|Col2|
|---|---|
|||
||DLY|


|Col1|Col2|Col3|Col4|
|---|---|---|---|
|||||
|||||
|DLY|DLY|DLY|DL|



















1. EXTSEL = TRGx, EXTEN = 01 (rising edge), CONT = x, ADSTART = 1, CHSEL = 0xF, SCANDIR = 0, WAIT = 1,
AUTOFF = 1


For code example refer to the Appendix section _A.7.13: Auto Off and wait mode sequence_
_code example_ .

## **13.7 Analog window watchdog**


**13.7.1** **Description of the analog watchdog**


The AWD analog watchdog is enabled by setting the AWDEN bit in the ADC_CFGR1
register. It is used to monitor that either one selected channel or all enabled channels (see
_Table 48: Analog watchdog channel selection_ ) remain within a configured voltage range
(window) as shown in _Figure 42_ .


The AWD analog watchdog status bit is set if the analog voltage converted by the ADC is
below a lower threshold or above a higher threshold. These thresholds are programmed in
HT[11:0] and LT[11:0] bit of ADC_TR register. An interrupt can be enabled by setting the
AWDIE bit in the ADC_IER register.


The AWD flag is cleared by software by programming it to it.


When converting data with a resolution of less than 12-bit (according to bits RES[1:0]), the
LSB of the programmed thresholds must be kept cleared because the internal comparison
is always performed on the full 12-bit raw converted data (left aligned).


For code example refer to the Appendix section _A.7.14: Analog watchdog code example_ .


_Table 47_ describes how the comparison is performed for all the possible resolutions.


254/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


**Table 47. Analog watchdog comparison**







|Resolution<br>bits<br>RES[1:0]|Analog Watchdog comparison between:|Col3|Comments|
|---|---|---|---|
|**Resolution**<br>**bits**<br>**RES[1:0]**|**Raw converted**<br>**data, left aligned(1) **|**Thresholds**|**Thresholds**|
|00: 12-bit|DATA[11:0]|LT[11:0] and HT[11:0]|-|
|01: 10-bit|DATA[11:2],00|LT[11:0] and HT[11:0]|The user must configure LT1[1:0] and HT1[1:0] to “00”|
|10: 8-bit|DATA[11:4],0000|LT[11:0] and HT[11:0]|The user must configure LT1[3:0] and HT1[3:0] to<br>“0000”|
|11: 6-bit|DATA[11:6],000000|LT[11:0] and HT[11:0]|The user must configure LT1[5:0] and HT1[5:0] to<br>“000000”|


1. The watchdog comparison is performed on the raw converted data before any alignment calculation.


_Table 48_ shows how to configure the AWDSGL and AWDEN bits in the ADC_CFGR1
register to enable the analog watchdog on one or more channels.


**Figure 42. Analog watchdog** **guarded area**







**Table 48. Analog watchdog channel selection**



|Channels guarded by the analog watchdog|AWDSGL bit|AWDEN bit|
|---|---|---|
|None|x|0|
|All channels|0|1|
|Single(1) channel|1|1|


1. Selected by the AWDCH[4:0] bits


**13.7.2** **ADC_AWD1_OUT output signal generation**





The analog watchdog is associated to an internal hardware signal, ADC_AWD1_OUT that is
directly connected to the ETR input (external trigger) of some on-chip timers (refer to the
timers section for details on how to select the ADC_AWD1_OUT signal as ETR).


RM0091 Rev 10 255/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


ADC_AWD1_OUT is activated when the analog watchdog is enabled:


      - ADC_AWD1_OUT is set when a guarded conversion is outside the programmed
thresholds.


      - ADC_AWD1_OUT is reset after the end of the next guarded conversion which is inside
the programmed thresholds. It remains at 1 if the next guarded conversions are still
outside the programmed thresholds.


      - ADC_AWD1_OUT is also reset when disabling the ADC (when setting ADDIS to 1).
Note that stopping conversions (ADSTP set), might clear the ADC_AWD1_OUT state.


      - ADC_AWD1_OUT state does not change when the ADC converts the none-guarded
channel (see _Figure 43_ )


AWD flag is set by hardware and reset by software: AWD flag has no influence on the
generation of ADC_AWD1_OUT (as an example, ADC_AWD1_OUT can toggle while AWD
flag remains at 1 if the software has not cleared the flag).


The ADC_AWD1_OUT signal is generated by the ADC_CLK domain. This signal can be
generated even the APB clock is stopped.


The AWD comparison is performed at the end of each ADC conversion. The
ADC_AWD1_OUT rising edge and falling edge occurs two ADC_CLK clock cycles after the
comparison.


As ADC_AWD1_OUT is generated by the ADC_CLK domain and AWD flag is generated by
the APB clock domain, the rising edges of these signals are not synchronized.


**Figure 43. ADC_AWD1_OUT signal generation**

















256/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


**Figure 44. ADC_AWD1_OUT signal generation (AWD flag not cleared by software)**



















**Figure 45. ADC1_AWD_OUT signal generation (on a single channel)**















**13.7.3** **Analog watchdog threshold control**


LT[11:0] and HT[11:0] can be changed during an analog-to-digital conversion (that is
between the start of the conversion and the end of conversion of the ADC internal state). If
LT and HT bits are programmed during the ADC guarded channel conversion, the watchdog
function is masked for this conversion. This mask is cleared when starting a new
conversion, and the resulting new AWD threshold is applied starting the next ADC
conversion result. AWD comparison is performed at each end of conversion. If the current
ADC data are out of the new threshold interval, this does not generated any interrupt or an
ADC_AWD1_OUT signal. The Interrupt and the ADC_AWD1_OUT generation only occurs
at the end of the ADC conversion that started after the threshold update. If
ADC_AWD1_OUT is already asserted, programming the new threshold does not deassert
the ADC_AWD1_OUT signal.


RM0091 Rev 10 257/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


**Figure 46. Analog watchdog threshold update**


















## **13.8 Temperature sensor and internal reference voltage**

The temperature sensor can be used to measure the junction temperature (T J ) of the
device. The temperature sensor is internally connected to the ADC V IN [16] input channel
which is used to convert the sensor’s output voltage to a digital value. The sampling time for
the temperature sensor analog pin must be greater than the minimum T S_temp value
specified in the datasheet. When not in use, the sensor can be put in power down mode.


The temperature sensor output voltage changes linearly with temperature, however its
characteristics may vary significantly from chip to chip due to the process variations. To
improve the accuracy of the temperature sensor (especially for absolute temperature
measurement), calibration values are individually measured for each part by ST during
production test and stored in the system memory area. Refer to the specific device
datasheet for additional information.


The internal voltage reference (V REFINT ) provides a stable (bandgap) voltage output for the
ADC and comparators. V REFINT is internally connected to the ADC V IN [17] input channel.
The precise voltage of V REFINT is individually measured for each part by ST during
production test and stored in the system memory area.


_Figure 47_ shows the block diagram of connections between the temperature sensor, the
internal voltage reference and the ADC.


The TSEN bit must be set to enable the conversion of ADC V IN [16] (temperature sensor)
and the VREFEN bit must be set to enable the conversion of ADC V IN [17] (V REFINT ).


258/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


**Figure 47. Temperature sensor and V** **REFINT** **channel block diagram**











**Reading the temperature**


1. Select the ADC V IN [16] input channel.

2. Select an appropriate sampling time specified in the device datasheet (T S_temp ).

3. Set the TSEN bit in the ADC_CCR register to wake up the temperature sensor from
power down mode and wait for its stabilization time (t START ).


For code example refer to the Appendix section _A.7.15: Temperature configuration_
_code example_ .


4. Start the ADC conversion by setting the ADSTART bit in the ADC_CR register (or by
external trigger).


5. Read the resulting V SENSE data in the ADC_DR register.


6. Calculate the temperature using the following formula


–
Temperature in °C ( ) = TS_CAL2_TEMP --------------------------------------------------------------------------------------------------– TS_CAL1_TEMP **-** × ( TS_DATA – TS_CAL1 ) + TS_CAL1_TEMP
TS_CAL2 TS_CAL1


Where:


      - TS_CAL2 is the temperature sensor calibration value acquired at TS_CAL2_TEMP
(refer to the datasheet for TS_CAL2 value)


      - TS_CAL1 is the temperature sensor calibration value acquired at TS_CAL1_TEMP
(refer to the datasheet for TS_CAL1 value)


      - TS_DATA is the actual temperature sensor output value converted by ADC


Refer to the specific device datasheet for more information about TS_CAL1 and
TS_CAL2 calibration points.


For code example refer to the _A.7.16: Temperature computation code example_ .


_Note:_ _The sensor has a startup time after waking from power down mode before it can output_
_V_ _SENSE_ _at the correct level. The ADC also has a startup time after power-on, so to minimize_
_the delay, the ADEN and TSEN bits should be set at the same time._


RM0091 Rev 10 259/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


**Calculating the actual V** **DDA** **voltage using the internal reference voltage**


The V DDA power supply voltage applied to the device may be subject to variation or not
precisely known. The embedded internal voltage reference (V REFINT ) and its calibration
data, acquired by the ADC during the manufacturing process at V DDA_Charac, can be used to
evaluate the actual V DDA voltage level.


The following formula gives the actual V DDA voltage supplying the device:

V DDA = V DDA_Charac x VREFINT_CAL / VREFINT_DATA


Where:


      - V DDA_Charac is the value of V DDA voltage characterized at V REFINT during the
manufacturing process. It is specified in the device datasheet.


      - VREFINT_CAL is the VREFINT calibration value


      - VREFINT_DATA is the actual VREFINT output value converted by ADC


**Converting a supply-relative ADC measurement to an absolute voltage value**


The ADC is designed to deliver a digital value corresponding to the ratio between the analog
power supply and the voltage applied on the converted channel. For most application use
cases, it is necessary to convert this ratio into a voltage independent of V DDA . For
applications where V DDA is known and ADC converted values are right-aligned you can use
the following formula to get this absolute value:

V CHANNELx = ------------------------------------- FULL_SCALEV DDA × ADC_DATA x


For applications where V DDA value is not known, you must use the internal voltage
reference and V DDA can be replaced by the expression provided in _Section : Calculating the_
_actual V_ _DDA_ _voltage using the internal reference voltage_, resulting in the following formula:

V CHANNELx = ------------------------------------------------------------------------------------------------------------------------- V DDA_Charac × VREFINT_CAL × ADC_DATA x
VREFINT_DATA × FULL_SCALE


Where:


      - V DDA_Charac is the value of V DDA voltage characterized at V REFINT during the
manufacturing process. It is specified in the device datasheet.


      - VREFINT_CAL is the VREFINT calibration value


      - ADC_DATA x is the value measured by the ADC on channelx (right-aligned)


      - VREFINT_DATA is the actual VREFINT output value converted by the ADC


      - full_SCALE is the maximum digital value of the ADC output. For example with 12-bit
resolution, it is 2 [12]           - 1 = 4095 or with 8-bit resolution, 2 [8]           - 1 = 255.


_Note:_ _If ADC measurements are done using an output format other than 12 bit right-aligned, all the_
_parameters must first be converted to a compatible format before the calculation is done._

## **13.9 Battery voltage monitoring**


The VBATEN bit in the ADC_CCR register allows the application to measure the backup
battery voltage on the VBAT pin. As the V BAT voltage could be higher than V DDA, to ensure
the correct operation of the ADC, the VBAT pin is internally connected to a bridge divider.
This bridge is automatically enabled when VBATEN is set, to connect V BAT to the ADC
V IN [18] input channel. As a consequence, the converted digital value is V BAT /2. To prevent


260/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


any unwanted consumption on the battery, it is recommended to enable the bridge divider
only when needed for ADC conversion.

## **13.10 ADC interrupts**


An interrupt can be generated by any of the following events:


      - ADC power-up, when the ADC is ready (ADRDY flag)


      - End of any conversion (EOC flag)


      - End of a sequence of conversions (EOS flag)


      - When an analog watchdog detection occurs (AWD flag)


      - When the end of sampling phase occurs (EOSMP flag)


      - when a data overrun occurs (OVR flag)


Separate interrupt enable bits are available for flexibility.


**Table 49. ADC interrupts**

|Interrupt event|Event flag|Enable control bit|
|---|---|---|
|ADC ready|ADRDY|ADRDYIE|
|End of conversion|EOC|EOCIE|
|End of sequence of conversions|EOS|EOSIE|
|Analog watchdog status bit is set|AWD|AWDIE|
|End of sampling phase|EOSMP|EOSMPIE|
|Overrun|OVR|OVRIE|



RM0091 Rev 10 261/1017



275


**Analog-to-digital converter (ADC)** **RM0091**

## **13.11 ADC registers**


Refer to _Section 1.2_ for a list of abbreviations used in register descriptions.


**13.11.1** **ADC interrupt and status register (ADC_ISR)**


Address offset: 0x00


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|AWD|Res.|Res.|OVR|EOS|EOC|EOSMP|ADRDY|
|||||||||rc_w1|||rc_w1|rc_w1|rc_w1|rc_w1|rc_w1|



Bits 31:13 Reserved, must be kept at reset value.


Bits 12:10 Reserved, must be kept at reset value.


Bits 9:8 Reserved, must be kept at reset value.


Bit 7 **AWD** : Analog watchdog flag

This bit is set by hardware when the converted voltage crosses the values programmed in ADC_TR
register. It is cleared by software by programming it to 1.
0: No analog watchdog event occurred (or the flag event was already acknowledged and cleared by
software)
1: Analog watchdog event occurred


Bits 6:5 Reserved, must be kept at reset value.


Bit 4 **OVR** : ADC overrun

This bit is set by hardware when an overrun occurs, meaning that a new conversion has complete
while the EOC flag was already set. It is cleared by software writing 1 to it.
0: No overrun occurred (or the flag event was already acknowledged and cleared by software)

1: Overrun has occurred


Bit 3 **EOS** : End of sequence flag

This bit is set by hardware at the end of the conversion of a sequence of channels selected by the
CHSEL bits. It is cleared by software writing 1 to it.
0: Conversion sequence not complete (or the flag event was already acknowledged and cleared by
software)
1: Conversion sequence complete


262/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


Bit 2 **EOC** : End of conversion flag

This bit is set by hardware at the end of each conversion of a channel when a new data result is
available in the ADC_DR register. It is cleared by software writing 1 to it or by reading the ADC_DR
register.
0: Channel conversion not complete (or the flag event was already acknowledged and cleared by
software)
1: Channel conversion complete


Bit 1 **EOSMP** : End of sampling flag

This bit is set by hardware during the conversion, at the end of the sampling phase.It is cleared by
software by programming it to ‘1’.
0: Not at the end of the sampling phase (or the flag event was already acknowledged and cleared by
software)
1: End of sampling phase reached


Bit 0 **ADRDY** : ADC ready

This bit is set by hardware after the ADC has been enabled (ADEN = 1) and when the ADC reaches
a state where it is ready to accept conversion requests.

It is cleared by software writing 1 to it.

0: ADC not yet ready to start conversion (or the flag event was already acknowledged and cleared
by software)
1: ADC is ready to start conversion


_Note:_ _In auto-off mode (AUTOFF = 1) the power-on/off phases are performed automatically, by_
_hardware and the ADRDY flag is not set._


**13.11.2** **ADC interrupt enable register (ADC_IER)**


Address offset: 0x04


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|AWDIE|Res.|Res.|OVRIE|EOSIE|EOCIE|EOSMP<br>IE|ADRDY<br>IE|
|||||||||rw|||rw|rw|rw|rw|rw|



Bits 31:13 Reserved, must be kept at reset value.


Bits 12:10 Reserved, must be kept at reset value.


Bits 9:8 Reserved, must be kept at reset value.


Bit 7 **AWDIE** : Analog watchdog interrupt enable

This bit is set and cleared by software to enable/disable the analog watchdog interrupt.
0: Analog watchdog interrupt disabled
1: Analog watchdog interrupt enabled

_Note: The Software is allowed to write this bit only when ADSTART bit is cleared (this ensures that no_
_conversion is ongoing)._


Bits 6:5 Reserved, must be kept at reset value.


RM0091 Rev 10 263/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


Bit 4 **OVRIE** : Overrun interrupt enable

This bit is set and cleared by software to enable/disable the overrun interrupt.
0: Overrun interrupt disabled
1: Overrun interrupt enabled. An interrupt is generated when the OVR bit is set.

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures that no_
_conversion is ongoing)._


Bit 3 **EOSIE** : End of conversion sequence interrupt enable

This bit is set and cleared by software to enable/disable the end of sequence of conversions
interrupt.
0: EOS interrupt disabled
1: EOS interrupt enabled. An interrupt is generated when the EOS bit is set.

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures that no_
_conversion is ongoing)._


Bit 2 **EOCIE** : End of conversion interrupt enable

This bit is set and cleared by software to enable/disable the end of conversion interrupt.

0: EOC interrupt disabled
1: EOC interrupt enabled. An interrupt is generated when the EOC bit is set.

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures that no_
_conversion is ongoing)._


Bit 1 **EOSMPIE** : End of sampling flag interrupt enable

This bit is set and cleared by software to enable/disable the end of the sampling phase interrupt.

0: EOSMP interrupt disabled.
1: EOSMP interrupt enabled. An interrupt is generated when the EOSMP bit is set.

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures that no_
_conversion is ongoing)._


Bit 0 **ADRDYIE** : ADC ready interrupt enable

This bit is set and cleared by software to enable/disable the ADC Ready interrupt.

0: ADRDY interrupt disabled.
1: ADRDY interrupt enabled. An interrupt is generated when the ADRDY bit is set.

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures that no_
_conversion is ongoing)._


264/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


**13.11.3** **ADC control register (ADC_CR)**


Address offset: 0x08


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ADCAL|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|rs||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADSTP|Res.|ADSTA<br>RT|ADDIS|ADEN|
||||||||||||rs||rs|rs|rs|



Bit 31 **ADCAL** : ADC calibration

This bit is set by software to start the calibration of the ADC.
It is cleared by hardware after calibration is complete.
0: Calibration complete
1: Write 1 to calibrate the ADC. Read at 1 means that a calibration is in progress.

_Note: The software is allowed to set ADCAL only when the ADC is disabled (ADCAL_ = _0,_
_ADSTART_ = _0, ADSTP_ = _0, ADDIS_ = _0, AUTOFF = 0, and ADEN_ = _0)._

_is allowed to_


Bits 30:28 Reserved, must be kept at reset value.


Bits 27:5 Reserved, must be kept at reset value.


Bit 4 **ADSTP** : ADC stop conversion command

This bit is set by software to stop and discard an ongoing conversion (ADSTP Command).
It is cleared by hardware when the conversion is effectively discarded and the ADC is ready to
accept a new start conversion command.
0: No ADC stop conversion command ongoing
1: Write 1 to stop the ADC. Read 1 means that an ADSTP command is in progress.

_Note: Setting ADSTP to ‘1’ is only effective when ADSTART_ = _1 and ADDIS_ = _0 (ADC is enabled and_
_may be converting and there is no pending request to disable the ADC)_


Bit 3 Reserved, must be kept at reset value.


RM0091 Rev 10 265/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


Bit 2 **ADSTART** : ADC start conversion command

This bit is set by software to start ADC conversion. Depending on the EXTEN [1:0] configuration bits,
a conversion either starts immediately (software trigger configuration) or once a hardware trigger
event occurs (hardware trigger configuration).
It is cleared by hardware:

– In single conversion mode (CONT = 0, DISCEN = 0), when software trigger is selected
(EXTEN = 00): at the assertion of the end of Conversion Sequence (EOS) flag.

– In discontinuous conversion mode(CONT = 0, DISCEN = 1), when the software trigger is selected
(EXTEN = 00): at the assertion of the end of Conversion (EOC) flag.

– In all other cases: after the execution of the ADSTP command, at the same time as the ADSTP bit is
cleared by hardware.

0: No ADC conversion is ongoing.
1: Write 1 to start the ADC. Read 1 means that the ADC is operating and may be converting.

_Note: The software is allowed to set ADSTART only when ADEN_ = _1 and ADDIS_ = _0 (ADC is enabled_
_and there is no pending request to disable the ADC)._


Bit 1 **ADDIS** : ADC disable command

This bit is set by software to disable the ADC (ADDIS command) and put it into power-down state
(OFF state).
It is cleared by hardware once the ADC is effectively disabled (ADEN is also cleared by hardware at
this time).
0: No ADDIS command ongoing
1: Write 1 to disable the ADC. Read 1 means that an ADDIS command is in progress.

_Note: Setting ADDIS to ‘1’ is only effective when ADEN_ = _1 and ADSTART_ = _0 (which ensures that no_
_conversion is ongoing)_


Bit 0 **ADEN** : ADC enable command

This bit is set by software to enable the ADC. The ADC is effectively ready to operate once the
ADRDY flag has been set.
It is cleared by hardware when the ADC is disabled, after the execution of the ADDIS command.
0: ADC is disabled (OFF state)

1: Write 1 to enable the ADC.

_Note: The software is allowed to set ADEN only when all bits of ADC_CR registers are 0 (ADCAL_ = _0,_
_ADSTP_ = _0, ADSTART_ = _0, ADDIS_ = _0 and ADEN_ = _0)_


266/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


**13.11.4** **ADC configuration register 1 (ADC_CFGR1)**


Address offset: 0x0C


Reset value: 0x0000 0000

|31|30 29 28 27 26|Col3|Col4|Col5|Col6|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|Res.|Res.|AWDEN|AWDSGL|Res.|Res.|Res.|Res.|Res.|DISCEN|
||rw|rw|rw|rw|rw|||rw|rw||||||rw|


|15|14|13|12|11 10|Col6|9|8 7 6|Col9|Col10|5|4 3|Col13|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|AUTOFF|WAIT|CONT|OVRMOD|EXTEN[1:0]|EXTEN[1:0]|Res.|EXTSEL[2:0]|EXTSEL[2:0]|EXTSEL[2:0]|ALIGN|RES[1:0]|RES[1:0]|SCAND<br>IR|DMAC<br>FG|DMAEN|
|rw|rw|rw|rw|rw|rw||rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 31 Reserved, must be kept at reset value.


Bits 30:26 **AWDCH[4:0]** : Analog watchdog channel selection

These bits are set and cleared by software. They select the input channel to be guarded by
the analog watchdog.
00000: ADC analog input Channel 0 monitored by AWD
00001: ADC analog input Channel 1 monitored by AWD

.....

10001: ADC analog input Channel 17 monitored by AWD
10010: ADC analog input Channel 18 monitored by AWD

Others: Reserved

_Note: The channel selected by the AWDCH[4:0] bits must be also set into the CHSELR_
_register._

_The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bits 25:24 Reserved, must be kept at reset value.


Bit 23 **AWDEN** : Analog watchdog enable

This bit is set and cleared by software.
0: Analog watchdog disabled
1: Analog watchdog enabled

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bit 22 **AWDSGL** : Enable the watchdog on a single channel or on all channels

This bit is set and cleared by software to enable the analog watchdog on the channel
identified by the AWDCH[4:0] bits or on all the channels
0: Analog watchdog enabled on all channels
1: Analog watchdog enabled on a single channel

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bits 21:17 Reserved, must be kept at reset value.


RM0091 Rev 10 267/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


Bit 16 **DISCEN** : Discontinuous mode

This bit is set and cleared by software to enable/disable discontinuous mode.

0: Discontinuous mode disabled

1: Discontinuous mode enabled

_Note: It is not possible to have both discontinuous mode and continuous mode enabled: it is_
_forbidden to set both bits DISCEN_ = _1 and CONT_ = _1._

_The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bit 15 **AUTOFF** : Auto-off mode

This bit is set and cleared by software to enable/disable auto-off mode. _[.]_


0: Auto-off mode disabled

1: Auto-off mode enabled

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bit 14 **WAIT** : Wait conversion mode

This bit is set and cleared by software to enable/disable wait conversion mode. _[.]_


0: Wait conversion mode off

1: Wait conversion mode on

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bit 13 **CONT** : Single / continuous conversion mode

This bit is set and cleared by software. If it is set, conversion takes place continuously until it
is cleared.

0: Single conversion mode

1: Continuous conversion mode

_Note: It is not possible to have both discontinuous mode and continuous mode enabled: it is_
_forbidden to set both bits DISCEN_ = _1 and CONT_ = _1._

_The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bit 12 **OVRMOD** : Overrun management mode

This bit is set and cleared by software and configure the way data overruns are managed.
0: ADC_DR register is preserved with the old data when an overrun is detected.
1: ADC_DR register is overwritten with the last conversion result when an overrun is
detected.

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bits 11:10 **EXTEN[1:0]** : External trigger enable and polarity selection

These bits are set and cleared by software to select the external trigger polarity and enable
the trigger.
00: Hardware trigger detection disabled (conversions can be started by software)
01: Hardware trigger detection on the rising edge
10: Hardware trigger detection on the falling edge
11: Hardware trigger detection on both the rising and falling edges

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bit 9 Reserved, must be kept at reset value.


268/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


Bits 8:6 **EXTSEL[2:0]** : External trigger selection

These bits select the external event used to trigger the start of conversion (refer to _Table 43:_
_External triggers_ for details):

000: TRG0

001: TRG1

010: TRG2

011: TRG3

100: TRG4

101: TRG5

110: TRG6

111: TRG7

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bit 5 **ALIGN** : Data alignment

This bit is set and cleared by software to select right or left alignment. Refer to _Figure 37:_
_Data alignment and resolution on page 249_
0: Right alignment
1: Left alignment

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bits 4:3 **RES[1:0]** : Data resolution

These bits are written by software to select the resolution of the conversion.

00: 12 bits

01: 10 bits

10: 8 bits

11: 6 bits

_Note: The software is allowed to write these bits only when ADEN is cleared._


RM0091 Rev 10 269/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


Bit 2 **SCANDIR** : Scan sequence direction

This bit is set and cleared by software to select the direction in which the channels is scanned
in the sequence.
0: Upward scan (from CHSEL0 to CHSEL18)
1: Backward scan (from CHSEL18 to CHSEL0)

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bit 1 **DMACFG** : Direct memory access configuration

This bit is set and cleared by software to select between two DMA modes of operation and is
effective only when DMAEN = 1.

0: DMA one shot mode selected

1: DMA circular mode selected

For more details, refer to _Section 13.5.5: Managing converted data using the DMA on_
_page 250_

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


Bit 0 **DMAEN** : Direct memory access enable

This bit is set and cleared by software to enable the generation of DMA requests. This allows
the DMA controller to be used to manage automatically the converted data. For more details,
refer to _Section 13.5.5: Managing converted data using the DMA on page 250_ .

0: DMA disabled

1: DMA enabled

_Note: The software is allowed to write this bit only when ADSTART bit is cleared (this ensures_
_that no conversion is ongoing)._


270/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


**13.11.5** **ADC configuration register 2 (ADC_CFGR2)**


Address offset: 0x10


Reset value: 0x0000 0000

|31 30|Col2|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CKMODE[1:0]|CKMODE[1:0]|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|rw|rw|||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||



Bits 31:30 **CKMODE[1:0]:** ADC clock mode

These bits are set and cleared by software to define how the analog ADC is clocked:
00: ADCCLK (Asynchronous clock mode), generated at product level (refer to RCC section)
01: PCLK/2 (Synchronous clock mode)
10: PCLK/4 (Synchronous clock mode)

11: Reserved

In all synchronous clock modes, there is no jitter in the delay from a timer trigger to the start of a
conversion.

_Note: The software is allowed to write these bits only when the ADC is disabled (ADCAL_ = _0,_
_ADSTART_ = _0, ADSTP_ = _0, ADDIS_ = _0 and ADEN_ = _0)._


Bits 29:10 Reserved, must be kept at reset value.


Bits 9:0 Reserved, must be kept at reset value.


**13.11.6** **ADC sampling time register (ADC_SMPR)**


Address offset: 0x14


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2 1 0|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SMP[2:0]|SMP[2:0]|SMP[2:0]|
||||||||||||||rw|rw|rw|



RM0091 Rev 10 271/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


Bits 31:3 Reserved, must be kept at reset value.


Bits 2:0 **SMP[2:0]:** _Sampling time selection_

These bits are written by software to select the sampling time that applies to all channels.
000: 1.5 ADC clock cycles
001: 7.5 ADC clock cycles
010: 13.5 ADC clock cycles
011: 28.5 ADC clock cycles
100: 41.5 ADC clock cycles
101: 55.5 ADC clock cycles
110: 71.5 ADC clock cycles
111: 239.5 ADC clock cycles

_Note: The software is allowed to write this bit only when ADSTART_ = _0 (which ensures that no_
_conversion is ongoing)._


**13.11.7** **ADC watchdog threshold register (ADC_TR)**


Address offset: 0x20


Reset value: 0x0FFF 0000

|31|30|29|28|27 26 25 24 23 22 21 20 19 18 17 16|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|
|||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11 10 9 8 7 6 5 4 3 2 1 0|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|
|||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:28 Reserved, must be kept at reset value.


Bits 27:16 **HT[11:0]** : _Analog watchdog higher threshold_

These bits are written by software to define the higher threshold for the analog watchdog. Refer to
_Section 13.7: Analog window watchdog on page 254_

_Note: The software is allowed to write this bit only when ADSTART_ = _0 (which ensures that no_
_conversion is ongoing)._


Bits 15:12 Reserved, must be kept at reset value.


Bits 11:0 **LT[11:0]** : Analog watchdog lower threshold

These bits are written by software to define the lower threshold for the analog watchdog.
Refer to _Section 13.7: Analog window watchdog on page 254_ .

_Note: The software is allowed to write this bit only when ADSTART_ = _0 (which ensures that no_
_conversion is ongoing)._


**13.11.8** **ADC channel selection register (ADC_CHSELR)**


Address offset: 0x28


Reset value: 0x0000 0000


272/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CHSEL<br>18|CHSEL<br>17|CHSEL<br>16|
||||||||||||||rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CHSEL<br>15|CHSEL<br>14|CHSEL<br>13|CHSEL<br>12|CHSEL<br>11|CHSEL<br>10|CHSEL<br>9|CHSEL<br>8|CHSEL<br>7|CHSEL<br>6|CHSEL<br>5|CHSEL<br>4|CHSEL<br>3|CHSEL<br>2|CHSEL<br>1|CHSEL<br>0|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:19 Reserved, must be kept at reset value.


Bits 18:0 **CHSELx** : Channel-x selection

These bits are written by software and define which channels are part of the sequence of channels
to be converted.

0: Input Channel-x is not selected for conversion
1: Input Channel-x is selected for conversion

_Note: The software is allowed to write this bit only when ADSTART_ = _0 (which ensures that no_
_conversion is ongoing)._


**13.11.9** **ADC data register (ADC_DR)**


Address offset: 0x40


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:0 **DATA[15:0]** : Converted data

These bits are read-only. They contain the conversion result from the last converted channel. The data
are left- or right-aligned as shown in _Figure 37: Data alignment and resolution on page 249_ .

Just after a calibration is complete, DATA[6:0] contains the calibration factor.


RM0091 Rev 10 273/1017



275


**Analog-to-digital converter (ADC)** **RM0091**


**13.11.10 ADC common configuration register (ADC_CCR)**


Address offset: 0x308


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21 20 19 18|Col12|Col13|Col14|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|VBAT<br>EN|TSEN|VREF<br>EN|Res.|Res.|Res.|Res.|Res.|Res.|
||||||||rw|rw|rw|||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||



Bits 31:25 Reserved, must be kept at reset value.


Bit 24 **VBATEN** : V BAT enable
This bit is set and cleared by software to enable/disable the V BAT channel.
0: V BAT channel disabled
1: V BAT channel enabled
_Note: The software is allowed to write this bit only when ADSTART_ = _0 (which ensures that no_
_conversion is ongoing)_


Bit 23 **TSEN** : Temperature sensor enable

This bit is set and cleared by software to enable/disable the temperature sensor.

0: Temperature sensor disabled
1: Temperature sensor enabled

_Note: Software is allowed to write this bit only when ADSTART_ = _0 (which ensures that no conversion_
_is ongoing)._


Bit 22 **VREFEN** : V REFINT enable
This bit is set and cleared by software to enable/disable the V REFINT .
0: V REFINT disabled
1: V REFINT enabled
_Note: Software is allowed to write this bit only when ADSTART_ = _0 (which ensures that no conversion_
_is ongoing)._


Bits 21:0 Reserved, must be kept at reset value.

## **13.12 ADC register map**


The following table summarizes the ADC registers.


**Table 50. ADC register map and reset values**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**ADC_ISR**|Res.|Res.<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.<br>|Res.|Res.|Res.|Res.<br>|Res|Res.|Res.|Res.|AWD|Res.|Res.|OVR|EOS|EOC|EOSMP|ADRDY|
|0x00|Reset value|||||||||||||||||||||||||0|||0|0|0|0|0|
|0x04|**ADC_IER**|Res.|Res.<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.<br>|Res.|Res.|Res.|Res.<br>|Res|Res.|Res.|Res.|AWDIE|Res.|Res.|OVRIE|EOSIE|EOCIE|EOSMPIE|ADRDYIE|
|0x04|Reset value|||||||||||||||||||||||||0|||0|0|0|0|0|



274/1017 RM0091 Rev 10


**RM0091** **Analog-to-digital converter (ADC)**


**Table 50. ADC register map and reset values (continued)**





























|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x08|**ADC_CR**|ADCAL|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|ADSTP|Res.|ADSTART|ADDIS|ADEN|
|0x08|Reset value|0|||||||||||||||||||||||||||0||0|0|0|
|0x0C|**ADC_CFGR1**|Res.|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|AWDCH[4:0]|Res.|Res.|AWDEN|AWDSGL|Res.|Res.|Res.|Res.|Res.|DISCEN|AUTOFF|WAIT|CONT|OVRMOD|EXTEN[1:0]|EXTEN[1:0]|Res.|EXTSEL<br>[2:0]|EXTSEL<br>[2:0]|EXTSEL<br>[2:0]|ALIGN|RES<br>[1:0]|RES<br>[1:0]|SCANDIR|DMACFG|DMAEN|
|0x0C|Reset value||0|0|0|0|0|||0|0||||||0|0|0|0|0|0|0||0|0|0|0|0|0|0|0|0|
|0x10|**ADC_CFGR2**|CKMODE[1:0]|CKMODE[1:0]|Res|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.<br>|Res.|
|0x10|Reset value|0|0|||||||||||||||||||||||||||||||
|0x14<br>|**ADC_SMPR**<br>|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|~~SMP~~<br>[2:0]<br><br><br>|~~SMP~~<br>[2:0]<br><br><br>|~~SMP~~<br>[2:0]<br><br><br>|
|0x14<br>|~~Reset value~~<br>||||||||||||||||||||||||||||||~~0~~|~~0~~|~~0~~|
|~~0x18~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|
|~~0x1C~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|
|0x20<br>|**ADC_TR**|Res.|Res.|Res.|Res.|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|HT[11:0]|Res.|Res.|Res.|Res.|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|LT[11:0]|
|0x20<br>|Reset value<br>|||||1|1|1|1|1|1|1|1|1|1|1<br>|1<br>|||||0|0|0|0|0|0|0|0|0|0|0|0|
|~~0x24~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|
|0x28<br>|**ADC_CHSELR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CHSEL18|CHSEL17|CHSEL16|CHSEL15|CHSEL14|CHSEL13|CHSEL12|CHSEL11|CHSEL10|CHSEL9|CHSEL8|CHSEL7|CHSEL6|CHSEL5|CHSEL4|CHSEL3|CHSEL2|CHSEL1|CHSEL0|
|0x28<br>|Reset value||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|~~0x2C~~<br>0x30<br>0x34<br>0x38<br>0x3C|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|
|0x40<br>|**ADC_DR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|DATA[15:0]|
|0x40<br>|Reset value<br>|||||||||||||||||0<br>|0<br>|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|~~...~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|
|~~...~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|~~Reserved~~<br>|
|~~...~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|~~Reserved~~|
|0x308|**ADC_CCR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|VBATEN|TSEN|VREFEN|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x308|Reset value||||||||0|0|0|||||||||||||||||||||||


Refer to _Section 2.2 on page 46_ for the register boundary addresses.


RM0091 Rev 10 275/1017



275


