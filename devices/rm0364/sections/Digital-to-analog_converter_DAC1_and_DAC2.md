**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**

# **14 Digital-to-analog converter (DAC1 and DAC2)**

## **14.1 Introduction**


The DAC module is a 12-bit, voltage output digital-to-analog converter. The DAC can be
configured in 8- or 12-bit mode and may be used in conjunction with the DMA controller. In
12-bit mode, the data could be left- or right-aligned. An input reference voltage,
V REF+ (shared with ADC), is available. The output can optionally be buffered for higher
current drive.

## **14.2 DAC1/2 main features**


The devices integrate three 12-bit DAC channels:


      - DAC1 integrates two DAC channels:


–
DAC1 channel 1 which output is DAC1_OUT1


–
DAC1 channel 2 which output is DAC1_OUT2


The two channels can be used independently or simultaneously when both channels
are grouped together for synchronous update operations (dual mode).


      - DAC2 integrates only one channel, DAC2 channel 1 which output is DAC2_OUT1 .


The DAC main features are the following:


      - Left or right data alignment in 12-bit mode


      - Synchronized update capability


      - Noise-wave generation (DAC1 only)


      - Triangular-wave generation (DAC1 only)


      - Independent or simultaneous conversions (dual mode only)


      - DMA capability for each channel


      - DMA underrun error detection


      - External triggers for conversion


      - Programmable internal buffer


      - Input voltage reference, V DDA


_Figure 83_ and _Figure 84_ show the block diagram of a DAC1 and DAC2 channel and
_Table 52_ gives the pin description.


RM0364 Rev 4 317/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**


**Figure 83. DAC1 block diagram**





















1. On STM32F334, there is no output buffer on the DAC1 channel 2. There is instead a switch allowing to
connect the DAC1_OUT2 to the corresponding I/O (PA5) (refer to DAC2 block diagram).


318/1124 RM0364 Rev 4


**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**


**Figure 84. DAC2 block diagram**





















**Table 52. DACx pins**

|Name|Signal type|Remarks|
|---|---|---|
|VDDA|Input, analog supply|Analog power supply|
|VSSA|Input, analog supply ground|Ground for analog power supply|
|DAC1_OUT1/2<br>DAC2_OUT1|Analog output signal|DACx channel y analog output|



_Note:_ _Once the DACx channel y is enabled, the corresponding GPIO pin (PA4, PA5 or PA6) is_
_automatically connected to the analog converter output (DACx_OUTy). In order to avoid_
_parasitic consumption, the PA4, PA5 or PA6 pin should first be configured to analog (AIN)._

## **14.3 DAC output buffer enable/DAC output switch**



The DAC1 channel 1 comes with an output buffer that can be used to reduce the output
impedance on DAC1_OUT1 output, and to drive external loads directly without having to
add an external operational amplifier.


In the STM32F334xx, the DAC1 channel 1 comes with an output buffer. The DAC1
channel2 does not have an output buffer, it has instead a switch allowing to connect the
DAC1_OUT2 to the corresponding I/O (PA5). The switch can be enabled and disabled
through the OUTEN2 bit in the DAC_CR register. The DAC2 channel1 does not have an
output buffer, it has instead a switch allowing to connect the DAC2_OUT1 to the



RM0364 Rev 4 319/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**


corresponding I/O (PA6). The switch can be enabled and disabled through the OUTEN1 bit
in the DAC_CR register.


The DAC1 channel output buffer can be enabled and disabled through the BOFF1 bit in the
DAC_CR register.

## **14.4 DAC channel enable**


Each DAC channel can be powered on by setting the corresponding ENx bit in the DAC_CR
register. Each DAC channel is then enabled after a startup time t WAKEUP .


_Note:_ _The ENx bit enables the analog DAC Channelx macrocell only. The DAC Channelx digital_
_interface is enabled even if the ENx bit is reset._

## **14.5 Single mode functional description**


**14.5.1** **DAC data format**


There are three possibilities:


      - 8-bit right alignment: the software has to load data into the DAC_DHR8Rx [7:0] bits
(stored into the DHRx[11:4] bits)


      - 12-bit left alignment: the software has to load data into the DAC_DHR12Lx [15:4] bits
(stored into the DHRx[11:0] bits)


      - 12-bit right alignment: the software has to load data into the DAC_DHR12Rx [11:0] bits
(stored into the DHRx[11:0] bits)


Depending on the loaded DAC_DHRyyyx register, the data written by the user is shifted and
stored into the corresponding DHRx (data holding registerx, which are internal non-memorymapped registers). The DHRx register is then loaded into the DORx register either
automatically, by software trigger or by an external event trigger.


**Figure 85. Data registers in single DAC channel mode**


**14.5.2** **DAC channel conversion**


The DAC_DORx cannot be written directly and any data transfer to the DAC channelx must
be performed by loading the DAC_DHRx register (write to DAC_DHR8Rx, DAC_DHR12Lx,
DAC_DHR12Rx).


Data stored in the DAC_DHRx register are automatically transferred to the DAC_DORx
register after one APB1 clock cycle, if no hardware trigger is selected (TENx bit in DAC_CR
register is reset). However, when a hardware trigger is selected (TENx bit in DAC_CR


320/1124 RM0364 Rev 4


**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**


register is set) and a trigger occurs, the transfer is performed three PCLK1 clock cycles
later.


When DAC_DORx is loaded with the DAC_DHRx contents, the analog output voltage
becomes available after a time t SETTLING that depends on the power supply voltage and the
analog output load.


**Figure 86. Timing diagram for conversion with trigger disabled TEN = 0**











**Independent trigger with single LFSR generation**





To configure the DAC in this conversion mode (see _Section 14.7: Noise generation_ ), the
following sequence is required:


1. Set the DAC channel trigger enable bit TENx.


2. Configure the trigger source by setting TSELx[2:0] bits.


3. Configure the DAC channel WAVEx[1:0] bits as “01” and the same LFSR mask value in
the MAMPx[3:0] bits


4. Load the DAC channel data into the desired DAC_DHRx register (DHR12RD,
DHR12LD or DHR8RD).


When a DAC channelx trigger arrives, the LFSRx counter, with the same mask, is added to
the DHRx register and the sum is transferred into DAC_DORx (three APB clock cycles
later). Then the LFSRx counter is updated.


**Independent trigger with single triangle generation**


To configure the DAC in this conversion mode (see _Section 14.8: Triangle-wave generation_ ),
the following sequence is required:


1. Set the DAC channelx trigger enable TENx bits.


2. Configure the trigger source by setting TSELx[2:0] bits.


3. Configure the DAC channelx WAVEx[1:0] bits as “1x” and the same maximum
amplitude value in the MAMPx[3:0] bits


4. Load the DAC channelx data into the desired DAC_DHRx register. (DHR12RD,
DHR12LD or DHR8RD).


When a DAC channelx trigger arrives, the DAC channelx triangle counter, with the same
triangle amplitude, is added to the DHRx register and the sum is transferred into
DAC_DORx (three APB clock cycles later). The DAC channelx triangle counter is then
updated.


RM0364 Rev 4 321/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**


**14.5.3** **DAC output voltage**


Digital inputs are converted to output voltages on a linear conversion between 0 and V DDA .


The analog output voltages on each DAC channel pin are determined by the following
equation:

DACoutput = V DDA × DOR ------------ 4096 **-**


**14.5.4** **DAC trigger selection**


If the TENx control bit is set, conversion can then be triggered by an external event (timer
counter, external interrupt line). The TSELx[2:0] control bits determine which possible
events will trigger conversion as shown in _Table 53_ .


**Table 53. External triggers (DAC1)**





















|Source|Type|TSEL[2:0]|
|---|---|---|
|TIM6_TRGO event|Internal signal from on-chip<br>timers|000|
|TIM3_TRGO event(1)|TIM3_TRGO event(1)|001|
|TIM7_TRGO event|TIM7_TRGO event|010|
|TIM15_TRGO eventor<br>HRTIM1_DACTRG1 event(2)|TIM15_TRGO eventor<br>HRTIM1_DACTRG1 event(2)|011(2)|
|TIM2_TRGO event|TIM2_TRGO event|100|
|HRTIM1_DACTRG2 event(3)|HRTIM1_DACTRG2 event(3)|101(3)|
|EXTI line9|External pin|110|
|SWTRIG|Software control bit|111|


1. To select TIM3_TRGO event as DAC1 trigger source, the DAC_ TRIG_RMP bit must be set in
SYSCFG_CFGR1 register.


2. When TSEL=011, the DAC trigger is selected using the DAC1_TRIG3_RMP bit in SYSCFG_CFGR3
register.


3. When TSEL=101, the DAC trigger is selected using the DAC1_TRIG5_RMP bit in SYSCFG_CFGR3
register.


**Table 54. External triggers (DAC2)**











|Source|Type|TSEL[2:0]|
|---|---|---|
|TIM6_TRGO event|Internal signal from on-chip<br>timers|000|
|TIM3_TRGO event(1)|TIM3_TRGO event(1)|001|
|TIM7_TRGO event|TIM7_TRGO event|010|
|TIM15_TRGO event|TIM15_TRGO event|011|
|TIM2_TRGO event|TIM2_TRGO event|100|
|HRTIM1_DACTRG3 event|HRTIM1_DACTRG3 event|101|
|EXTI line9|External pin|110|
|SWTRIG|Software control bit|111|


322/1124 RM0364 Rev 4


**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**


1. To select TIM3_TRGO event as DAC1 trigger source, the DAC_ TRIG_RMP bit must be set in
SYSCFG_CFGR1 register.


Each time a DAC interface detects a rising edge on the selected timer TRGO output, or on
the selected external interrupt line 9, the last data stored into the DAC_DHRx register are
transferred into the DAC_DORx register. The DAC_DORx register is updated three APB1
cycles after the trigger occurs.


If the software trigger is selected, the conversion starts once the SWTRIG bit is set.
SWTRIG is reset by hardware once the DAC_DORx register has been loaded with the
DAC_DHRx register contents.


_Note:_ _TSELx[2:0] bit cannot be changed when the ENx bit is set. When software trigger is_
_selected, the transfer from the DAC_DHRx register to the DAC_DORx register takes only_
_one APB1 clock cycle._

## **14.6 Dual-mode functional description**


**14.6.1** **DAC data format**


In Dual DAC channel mode, there are three possibilities:


      - 8-bit right alignment: data for DAC channel1 to be loaded in the DAC_DHR8RD [7:0]
bits (stored in the DHR1[11:4] bits) and data for DAC channel2 to be loaded in the
DAC_DHR8RD [15:8] bits (stored in the DHR2[11:4] bits)


      - 12-bit left alignment: data for DAC channel1 to be loaded into the DAC_DHR12LD

[15:4] bits (stored into the DHR1[11:0] bits) and data for DAC channel2 to be loaded
into the DAC_DHR12LD [31:20] bits (stored in the DHR2[11:0] bits)


      - 12-bit right alignment: data for DAC channel1 to be loaded into the DAC_DHR12RD

[11:0] bits (stored in the DHR1[11:0] bits) and data for DAC channel2 to be loaded into
the DAC_DHR12LD [27:16] bits (stored in the DHR2[11:0] bits)


Depending on the loaded DAC_DHRyyyD register, the data written by the user is shifted
and stored in DHR1 and DHR2 (data holding registers, which are internal non-memorymapped registers). The DHR1 and DHR2 registers are then loaded into the DOR1 and
DOR2 registers, respectively, either automatically, by software trigger or by an external
event trigger.


**Figure 87. Data registers in dual DAC channel mode**


RM0364 Rev 4 323/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**


**14.6.2** **DAC channel conversion in dual mode**


The DAC channel conversion in dual mode is performed in the same way as in single mode
(refer to _Section 14.5.2_ ) except that the data have to be loaded by writing to DAC_DHR8Rx,
DAC_DHR12Lx, DAC_DHR12Rx, DAC_DHR8RD, DAC_DHR12LD or DAC_DHR12RD.


**14.6.3** **Description of dual conversion modes**


To efficiently use the bus bandwidth in applications that require the two DAC channels at the
same time, three dual registers are implemented: DHR8RD, DHR12RD and DHR12LD. A
unique register access is then required to drive both DAC channels at the same time.


Eleven conversion modes are possible using the two DAC channels and these dual
registers. All the conversion modes can nevertheless be obtained using separate DHRx
registers if needed.


All modes are described in the paragraphs below.


Refer to _Section 14.5.2: DAC channel conversion_ for details on the APB bus (APB or APB1)
that clocks the DAC conversions.


**Independent trigger without wave generation**


To configure the DAC in this conversion mode, the following sequence is required:


1. Set the two DAC channel trigger enable bits TEN1 and TEN2


2. Configure different trigger sources by setting different values in the TSEL1[2:0] and
TSEL2[2:0] bits


3. Load the dual DAC channel data into the desired DHR register (DAC_DHR12RD,
DAC_DHR12LD or DAC_DHR8RD)


When a DAC channel1 trigger arrives, the DHR1 register is transferred into DAC_DOR1
(three APB clock cycles later).


When a DAC channel2 trigger arrives, the DHR2 register is transferred into DAC_DOR2
(three APB clock cycles later).


**Independent trigger with single LFSR generation**


To configure the DAC in this conversion mode (refer to _Section 14.7: Noise generation_ ), the
following sequence is required:


1. Set the two DAC channel trigger enable bits TEN1 and TEN2


2. Configure different trigger sources by setting different values in the TSEL1[2:0] and
TSEL2[2:0] bits


3. Configure the two DAC channel WAVEx[1:0] bits as “01” and the same LFSR mask
value in the MAMPx[3:0] bits


4. Load the dual DAC channel data into the desired DHR register (DHR12RD, DHR12LD
or DHR8RD)


When a DAC channel1 trigger arrives, the LFSR1 counter, with the same mask, is added to
the DHR1 register and the sum is transferred into DAC_DOR1 (three APB clock cycles
later). Then the LFSR1 counter is updated.


When a DAC channel2 trigger arrives, the LFSR2 counter, with the same mask, is added to
the DHR2 register and the sum is transferred into DAC_DOR2 (three APB clock cycles
later). Then the LFSR2 counter is updated.


324/1124 RM0364 Rev 4


**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**


**Independent trigger with different LFSR generation**


To configure the DAC in this conversion mode (refer to _Section 14.7: Noise generation_ ), the
following sequence is required:


1. Set the two DAC channel trigger enable bits TEN1 and TEN2


2. Configure different trigger sources by setting different values in the TSEL1[2:0] and
TSEL2[2:0] bits


3. Configure the two DAC channel WAVEx[1:0] bits as “01” and set different LFSR masks
values in the MAMP1[3:0] and MAMP2[3:0] bits


4. Load the dual DAC channel data into the desired DHR register (DAC_DHR12RD,
DAC_DHR12LD or DAC_DHR8RD)


When a DAC channel1 trigger arrives, the LFSR1 counter, with the mask configured by
MAMP1[3:0], is added to the DHR1 register and the sum is transferred into DAC_DOR1
(three APB clock cycles later). Then the LFSR1 counter is updated.


When a DAC channel2 trigger arrives, the LFSR2 counter, with the mask configured by
MAMP2[3:0], is added to the DHR2 register and the sum is transferred into DAC_DOR2
(three APB clock cycles later). Then the LFSR2 counter is updated.


**Independent trigger with single triangle generation**


To configure the DAC in this conversion mode (refer to _Section 14.8: Triangle-wave_
_generation_ ), the following sequence is required:


1. Set the DAC channelx trigger enable TENx bits.


2. Configure different trigger sources by setting different values in the TSELx[2:0] bits


3. Configure the DAC channelx WAVEx[1:0] bits as “1x” and the same maximum
amplitude value in the MAMPx[3:0] bits


4. Load the DAC channelx data into the desired DAC_DHRx register.


Refer to _Section 14.5.2: DAC channel conversion_ for details on the APB bus (APB or APB1)
that clocks the DAC conversions.


When a DAC channelx trigger arrives, the DAC channelx triangle counter, with the same
triangle amplitude, is added to the DHRx register and the sum is transferred into
DAC_DORx (three APB clock cycles later). The DAC channelx triangle counter is then
updated.


**Independent trigger with different triangle generation**


To configure the DAC in this conversion mode (refer to _Section 14.8: Triangle-wave_
_generation_ ), the following sequence is required:


1. Set the DAC channelx trigger enable TENx bits.


2. Configure different trigger sources by setting different values in the TSELx[2:0] bits


3. Configure the DAC channelx WAVEx[1:0] bits as “1x” and set different maximum
amplitude values in the MAMPx[3:0] bits


4. Load the DAC channelx data into the desired DAC_DHRx register.


When a DAC channelx trigger arrives, the DAC channelx triangle counter, with a triangle
amplitude configured by MAMPx[3:0], is added to the DHRx register and the sum is
transferred into DAC_DORx (three APB clock cycles later). The DAC channelx triangle
counter is then updated.


RM0364 Rev 4 325/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**


**Simultaneous software start**


To configure the DAC in this conversion mode, the following sequence is required:


1. Load the dual DAC channel data to the desired DHR register (DAC_DHR12RD,
DAC_DHR12LD or DAC_DHR8RD)


In this configuration, one APB clock cycles).


**Simultaneous trigger without wave generation**


To configure the DAC in this conversion mode, the following sequence is required:


1. Set the two DAC channel trigger enable bits TEN1 and TEN2


2. Configure the same trigger source for both DAC channels by setting the same value in
the TSEL1[2:0] and TSEL2[2:0] bits


3. Load the dual DAC channel data to the desired DHR register (DAC_DHR12RD,
DAC_DHR12LD or DAC_DHR8RD)


When a trigger arrives, the DHR1 and DHR2 registers are transferred into DAC_DOR1 and
DAC_DOR2, respectively (after three APB clock cycles).


**Simultaneous trigger with single LFSR generation**


To configure the DAC in this conversion mode (refer to _Section 14.7: Noise generation_ ), the
following sequence is required:


1. Set the two DAC channel trigger enable bits TEN1 and TEN2


2. Configure the same trigger source for both DAC channels by setting the same value in
the TSEL1[2:0] and TSEL2[2:0] bits


3. Configure the two DAC channel WAVEx[1:0] bits as “01” and the same LFSR mask
value in the MAMPx[3:0] bits


4. Load the dual DAC channel data to the desired DHR register (DHR12RD, DHR12LD or
DHR8RD)


When a trigger arrives, the LFSR1 counter, with the same mask, is added to the DHR1
register and the sum is transferred into DAC_DOR1 (three APB clock cycles later). The
LFSR1 counter is then updated. At the same time, the LFSR2 counter, with the same mask,
is added to the DHR2 register and the sum is transferred into DAC_DOR2 (three APB clock
cycles later). The LFSR2 counter is then updated.


**Simultaneous trigger with different LFSR generation**


To configure the DAC in this conversion mode (refer to _Section 14.7: Noise generation_ ), the
following sequence is required:


1. Set the two DAC channel trigger enable bits TEN1 and TEN2


2. Configure the same trigger source for both DAC channels by setting the same value in
the TSEL1[2:0] and TSEL2[2:0] bits


3. Configure the two DAC channel WAVEx[1:0] bits as “01” and set different LFSR mask
values using the MAMP1[3:0] and MAMP2[3:0] bits


4. Load the dual DAC channel data into the desired DHR register (DAC_DHR12RD,
DAC_DHR12LD or DAC_DHR8RD)


When a trigger arrives, the LFSR1 counter, with the mask configured by MAMP1[3:0], is
added to the DHR1 register and the sum is transferred into DAC_DOR1 (three APB clock
cycles later). The LFSR1 counter is then updated.


326/1124 RM0364 Rev 4


**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**


At the same time, the LFSR2 counter, with the mask configured by MAMP2[3:0], is added to
the DHR2 register and the sum is transferred into DAC_DOR2 (three APB clock cycles
later). The LFSR2 counter is then updated.


**Simultaneous trigger with single triangle generation**


To configure the DAC in this conversion mode (refer to _Section 14.8: Triangle-wave_
_generation_ ), the following sequence is required:


1. Set the DAC channelx trigger enable TEN1x bits.


2. Configure the same trigger source for both DAC channels by setting the same value in
the TSELx[2:0] bits.


3. Configure the DAC channelx WAVEx[1:0] bits as “1x” and the same maximum
amplitude value using the MAMPx[3:0] bits


4. Load the DAC channelx data into the desired DAC_DHRx registers.


When a trigger arrives, the DAC channelx triangle counter, with the same triangle amplitude,
is added to the DHRx register and the sum is transferred into DAC_DORx (three APB clock
cycles later). The DAC channelx triangle counter is then updated.


**Simultaneous trigger with different triangle generation**


To configure the DAC in this conversion mode ‘refer to _Section 14.8: Triangle-wave_
_generation_ ), the following sequence is required:


1. Set the DAC channelx trigger enable TENx bits.


2. Configure the same trigger source for DAC channelx by setting the same value in the
TSELx[2:0] bits


3. Configure the DAC channelx WAVEx[1:0] bits as “1x” and set different maximum
amplitude values in the MAMPx[3:0] bits.


4. Load the DAC channelx data into the desired DAC_DHRx registers.


When a trigger arrives, the DAC channelx triangle counter, with a triangle amplitude
configured by MAMPx[3:0], is added to the DHRx register and the sum is transferred into
DAC_DORx (three APB clock cycles later). Then the DAC channelx triangle counter is
updated.


**14.6.4** **DAC output voltage**


Refer to _Section 14.5.3: DAC output voltage_ .


RM0364 Rev 4 327/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**


**14.6.5** **DAC trigger selection**


Refer to _Section 14.5.4: DAC trigger selection_

## **14.7 Noise generation**


In order to generate a variable-amplitude pseudonoise, an LFSR (linear feedback shift
register) is available. DAC noise generation is selected by setting WAVEx[1:0] to “01”. The
preloaded value in LFSR is 0xAAA. This register is updated three APB clock cycles after
each trigger event, following a specific calculation algorithm.


**Figure 88. DAC LFSR register calculation algorithm**







The LFSR value, that may be masked partially or totally by means of the MAMPx[3:0] bits in
the DAC_CR register, is added up to the DAC_DHRx contents without overflow and this
value is then stored into the DAC_DORx register.


If LFSR is 0x0000, a ‘1 is injected into it (antilock-up mechanism).


It is possible to reset LFSR wave generation by resetting the WAVEx[1:0] bits.


**Figure 89. DAC conversion (SW trigger enabled) with LFSR wave generation**










|0x00|Col2|Col3|Col4|
|---|---|---|---|
|0x00||||
|0x00||0xAAA|0xAAA|
|0x00||||



_Note:_ _The DAC trigger must be enabled for noise generation by setting the TENx bit in the_
_DAC_CR register._


328/1124 RM0364 Rev 4


**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**

## **14.8 Triangle-wave generation**


It is possible to add a small-amplitude triangular waveform on a DC or slowly varying signal.
DAC triangle-wave generation is selected by setting WAVEx[1:0] to “10”. The amplitude is
configured through the MAMPx[3:0] bits in the DAC_CR register. An internal triangle counter
is incremented three APB clock cycles after each trigger event. The value of this counter is
then added to the DAC_DHRx register without overflow and the sum is stored into the
DAC_DORx register. The triangle counter is incremented as long as it is less than the
maximum amplitude defined by the MAMPx[3:0] bits. Once the configured amplitude is
reached, the counter is decremented down to 0, then incremented again and so on.


It is possible to reset triangle wave generation by resetting the WAVEx[1:0] bits.



**Figure 90. DAC triangle wave generation**



**Figure 91. DAC conversion (SW trigger enabled) with triangle wave generation**













|0xABE|Col2|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
|0xABE||||||
|0xABE||0xABE|0xABE|0xABF|0xABF|
|0xABE||||||


_Note:_ _The DAC trigger must be enabled for triangle generation by setting the TENx bit in the_
_DAC_CR register._


_The MAMPx[3:0] bits must be configured before enabling the DAC, otherwise they cannot_
_be changed._


RM0364 Rev 4 329/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**

## **14.9 DMA request**


Each DAC channel has a DMA capability. Two DMA channels are used to service DAC
channel DMA requests.


A DAC DMA request is generated when an external trigger (but not a software trigger)
occurs while the DMAENx bit is set. The value of the DAC_DHRx register is then transferred
to the DAC_DORx register.


In dual mode, if both DMAENx bits are set, two DMA requests are generated. If only one
DMA request is needed, user should set only the corresponding DMAENx bit. In this way,
the application can manage both DAC channels in dual mode by using one DMA request
and a unique DMA channel.


**DMA underrun**


The DAC DMA request is not queued so that if a second external trigger arrives before the
acknowledgment for the first external trigger is received (first request), then no new request
is issued and the DMA channelx underrun flag DMAUDRx in the DAC_SR register is set,
reporting the error condition. DMA data transfers are then disabled and no further DMA
request is treated. The DAC channelx continues to convert old data.


The software should clear the DMAUDRx flag by writing “1”, clear the DMAEN bit of the
used DMA stream and re-initialize both DMA and DAC channelx to restart the transfer
correctly. The software should modify the DAC trigger conversion frequency or lighten the
DMA workload to avoid a new DMA. Finally, the DAC conversion can be resumed by
enabling both DMA data transfer and conversion trigger.


For each DAC channel, an interrupt is also generated if the corresponding DMAUDRIEx bit
in the DAC_CR register is enabled.


330/1124 RM0364 Rev 4


**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**

## **14.10 DAC registers**


Refer to _Section 1.2 on page 43_ for a list of abbreviations used in register descriptions.


The peripheral registers have to be accessed by words (32-bit).


**14.10.1** **DAC control register (DAC_CR)**


Address offset: 0x00


Reset value: 0x0000 0000

|31|30|29|28|27 26 25 24|Col6|Col7|Col8|23 22|Col10|21 20 19|Col12|Col13|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|DMAU<br>DRIE2|DMA<br>EN2|MAMP2[3:0]|MAMP2[3:0]|MAMP2[3:0]|MAMP2[3:0]|WAVE2[1:0]|WAVE2[1:0]|TSEL2[2:0]|TSEL2[2:0]|TSEL2[2:0]|TEN2|BOFF2 <br>/OUTE<br>N2|EN2|
|||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11 10 9 8|Col6|Col7|Col8|7 6|Col10|5 4 3|Col12|Col13|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|DMAU<br>DRIE1|DMA<br>EN1|MAMP1[3:0]|MAMP1[3:0]|MAMP1[3:0]|MAMP1[3:0]|WAVE1[1:0]|WAVE1[1:0]|TSEL1[2:0]|TSEL1[2:0]|TSEL1[2:0]|TEN1|BOFF1<br>/OUTE<br>N1|EN1|
|||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:30 Reserved, must be kept at reset value.


Bit 29 **DMAUDRIE2** : DAC channel2 DMA underrun interrupt enable

This bit is set and cleared by software.

0: DAC channel2 DMA underrun interrupt disabled
1: DAC channel2 DMA underrun interrupt enabled

_Note: This bit is available in dual mode only. It is reserved in single mode._


Bit 28 **DMAEN2** : DAC channel2 DMA enable

This bit is set and cleared by software.

0: DAC channel2 DMA mode disabled

1: DAC channel2 DMA mode enabled

_Note: This bit is available in dual mode only. It is reserved in single mode._


Bits 27:24 **MAMP2[3:0]** : DAC channel2 mask/amplitude selector

These bits are written by software to select mask in wave generation mode or amplitude in
triangle generation mode.

0000: Unmask bit0 of LFSR/ triangle amplitude equal to 1
0001: Unmask bits[1:0] of LFSR/ triangle amplitude equal to 3
0010: Unmask bits[2:0] of LFSR/ triangle amplitude equal to 7
0011: Unmask bits[3:0] of LFSR/ triangle amplitude equal to 15
0100: Unmask bits[4:0] of LFSR/ triangle amplitude equal to 31
0101: Unmask bits[5:0] of LFSR/ triangle amplitude equal to 63
0110: Unmask bits[6:0] of LFSR/ triangle amplitude equal to 127
0111: Unmask bits[7:0] of LFSR/ triangle amplitude equal to 255
1000: Unmask bits[8:0] of LFSR/ triangle amplitude equal to 511
1001: Unmask bits[9:0] of LFSR/ triangle amplitude equal to 1023
1010: Unmask bits[10:0] of LFSR/ triangle amplitude equal to 2047
≥1011: Unmask bits[11:0] of LFSR/ triangle amplitude equal to 4095

_Note: These bits are available only in dual mode when wave generation is supported._
_Otherwise, they are reserved and must be kept at reset value._


RM0364 Rev 4 331/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**


Bits 23:22 **WAVE2[1:0]** : DAC channel2 noise/triangle wave generation enable

These bits are set/reset by software.

00: wave generation disabled
01: Noise wave generation enabled
1x: Triangle wave generation enabled

_Note: Only used if bit TEN2 = 1 (DAC channel2 trigger enabled)_

_These bits are available only in dual mode when wave generation is supported._
_Otherwise, they are reserved and must be kept at reset value._


Bits 21:19 **TSEL2[2:0]** : DAC channel2 trigger selection

These bits select the external event used to trigger DAC channel2

000: Timer 6 TRGO event

001: Timer 3 TRGO event

010: Timer 7 TRGO event

011: Timer 15 TRGO or HRTM1_DACTRG1 event

100: Timer 2 TRGO event

101: HRTIM1_DACTRG2 event

110: EXTI line9

111: Software trigger

_Note: Only used if bit TEN2 = 1 (DAC channel2 trigger enabled)._

_These bits are available in dual mode only. They are reserved in single mode._


Bit 18 **TEN2** : DAC channel2 trigger enable

This bit is set and cleared by software to enable/disable DAC channel2 trigger

0: DAC channel2 trigger disabled and data written into the DAC_DHRx register are
transferred one APB1clock cycle later to the DAC_DOR2 register
1: DAC channel2 trigger enabled and data from the DAC_DHRx register are transferred
three APB1 clock cycles later to the DAC_DOR2 register

_Note:_ When software trigger is selected, the transfer from the DAC_DHRx reg _ister to the_
_DAC_DOR2 register takes only one APB1 clock cycle._

_Note: This bit is available in dual mode only. It is reserved in single mode._


Bit 17 **OUTEN2:** DAC channel2 output switch enable

This bit is set and cleared by software to enable/disable DAC channel2 output switch.

0: DAC channel2 output switch disabled
1: DAC channel2 output switch enabled


Bit 16 **EN2** : DAC channel2 enable

This bit is set and cleared by software to enable/disable DAC channel2.

0: DAC channel2 disabled

1: DAC channel2 enabled

_Note: This bit is available in dual mode only. It is reserved in single mode._


Bits 15:14 Reserved, must be kept at reset value.


Bit 13 **DMAUDRIE1** : DAC channel1 DMA Underrun Interrupt enable

This bit is set and cleared by software.

0: DAC channel1 DMA Underrun Interrupt disabled
1: DAC channel1 DMA Underrun Interrupt enabled


Bit 12 **DMAEN1** : DAC channel1 DMA enable

This bit is set and cleared by software.

0: DAC channel1 DMA mode disabled

1: DAC channel1 DMA mode enabled


332/1124 RM0364 Rev 4


**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**


Bits 11:8 **MAMP1[3:0]** : DAC channel1 mask/amplitude selector

These bits are written by software to select mask in wave generation mode or amplitude in
triangle generation mode.

0000: Unmask bit0 of LFSR/ triangle amplitude equal to 1
0001: Unmask bits[1:0] of LFSR/ triangle amplitude equal to 3
0010: Unmask bits[2:0] of LFSR/ triangle amplitude equal to 7
0011: Unmask bits[3:0] of LFSR/ triangle amplitude equal to 15
0100: Unmask bits[4:0] of LFSR/ triangle amplitude equal to 31
0101: Unmask bits[5:0] of LFSR/ triangle amplitude equal to 63
0110: Unmask bits[6:0] of LFSR/ triangle amplitude equal to 127
0111: Unmask bits[7:0] of LFSR/ triangle amplitude equal to 255
1000: Unmask bits[8:0] of LFSR/ triangle amplitude equal to 511
1001: Unmask bits[9:0] of LFSR/ triangle amplitude equal to 1023
1010: Unmask bits[10:0] of LFSR/ triangle amplitude equal to 2047
≥ 1011: Unmask bits[11:0] of LFSR/ triangle amplitude equal to 4095


Bits 7:6 **WAVE1[1:0]** : DAC channel1 noise/triangle wave generation enable

These bits are set and cleared by software.

00: Wave generation disabled
01: Noise wave generation enabled
1x: Triangle wave generation enabled

_Note: Only used if bit TEN1 = 1 (DAC channel1 trigger enabled)._


Bits 5:3 **TSEL1[2:0]** : DAC channel1 trigger selection

These bits select the external event used to trigger DAC channel1.

000: Timer 6 TRGO event

001: Timer 3 TRGO event

010: Timer 7 TRGO event

011: Timer15 TRGO or HRTM1_DACTRG1 event (DAC1 only)

100: Timer 2 TRGO event

101: HRTIM1_DACTRG2 (DAC1) or HRTM1_DACTRG3 (DAC2) event

110: EXTI line9

111: Software trigger

_Note: When TSEL=011, the DAC trigger is selected using the DAC1_TRIG3_RMP bit in_
_SYSCFG_CFGR3register._

_Note: When TSEL=101, the DAC trigger is selected using the DAC1_TRIG5_RMP bit in_
_SYSCFG_CFGR3register._

_Note: Only used if bit TEN1 = 1 (DAC channel1 trigger enabled)._


RM0364 Rev 4 333/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**


Bit 2 **TEN1** : DAC channel1 trigger enable

This bit is set and cleared by software to enable/disable DAC channel1 trigger.

0: DAC channel1 trigger disabled and data written into the DAC_DHRx register are
transferred one APB1 clock cycle later to the DAC_DOR1 register
1: DAC channel1 trigger enabled and data from the DAC_DHRx register are transferred
three APB1 clock cycles later to the DAC_DOR1 register

_Note: When software trigger is selected, the transfer from the DAC_DHRx register to the_
_DAC_DOR1 register takes only one APB1 clock cycle._


Bit 1 **In DAC1:**

**BOFF1** : DAC channel1 output buffer disable

This bit is set and cleared by software to enable/disable DAC channel1 output buffer.

0: DAC channel1 output buffer enabled
1: DAC channel1 output buffer disabled

**In DAC2: (STM32F334xx only)**

**OUTEN1** : DAC channel1 output switch enable

This bit is set and cleared by software to enable/disable DAC channel1 output switch.

0: DAC channel1 output switch disabled
1: DAC channel1 output switch enabled


Bit 0 **EN1** : DAC channel1 enable

This bit is set and cleared by software to enable/disable DAC channel1.

0: DAC channel1 disabled

1: DAC channel1 enabled


334/1124 RM0364 Rev 4


**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**


**14.10.2** **DAC software trigger register (DAC_SWTRIGR)**


Address offset: 0x04


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SWTRIG2|SWTRIG1|
|||||||||||||||w|w|



Bits 31:2 Reserved, must be kept at reset value.


Bit 1 **SWTRIG2** : DAC channel2 software trigger

This bit is set and cleared by software to enable/disable the software trigger.

0: Software trigger disabled
1: Software trigger enabled

_Note: This bit is cleared by hardware (one APB1 clock cycle later) once the DAC_DHR2_
_register value has been loaded into the DAC_DOR2 register._

_This bit is available in dual mode only. It is reserved in single mode._


Bit 0 **SWTRIG1** : DAC channel1 software trigger

This bit is set and cleared by software to enable/disable the software trigger.

0: Software trigger disabled
1: Software trigger enabled

_Note: This bit is cleared by hardware (one APB1 clock cycle later) once the DAC_DHR1_
_register value has been loaded into the DAC_DOR1 register._


**14.10.3** **DAC channel1 12-bit right-aligned data holding register**
**(DAC_DHR12R1)**


Address offset: 0x08


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11 10 9 8 7 6 5 4 3 2 1 0|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|
|||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:12 Reserved, must be kept at reset value.


Bits 11:0 **DACC1DHR[11:0]** : DAC channel1 12-bit right-aligned data

These bits are written by software which specifies 12-bit data for DAC channel1.


RM0364 Rev 4 335/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**


**14.10.4** **DAC channel1 12-bit left-aligned data holding register**
**(DAC_DHR12L1)**


Address offset: 0x0C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12 11 10 9 8 7 6 5 4|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|v|Res.|Res.|Res.|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|||||



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:4 **DACC1DHR[11:0]** : DAC channel1 12-bit left-aligned data

These bits are written by software which specifies 12-bit data for DAC channel1.


Bits 3:0 Reserved, must be kept at reset value.


**14.10.5** **DAC channel1 8-bit right-aligned data holding register**
**(DAC_DHR8R1)**


Address offset: 0x10


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|
|||||||||rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:8 Reserved, must be kept at reset value.


Bits 7:0 **DACC1DHR[7:0]** : DAC channel1 8-bit right-aligned data

These bits are written by software which specifies 8-bit data for DAC channel1.


**14.10.6** **DAC channel2 12-bit right-aligned data holding register**
**(DAC_DHR12R2)**


Address offset: 0x14


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11 10 9 8 7 6 5 4 3 2 1 0|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|
|||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



336/1124 RM0364 Rev 4


**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**


Bits 31:12 Reserved, must be kept at reset value.


Bits 11:0 **DACC2DHR[11:0]** : DAC channel2 12-bit right-aligned data

These bits are written by software which specifies 12-bit data for DAC channel2.


**14.10.7** **DAC channel2 12-bit left-aligned data holding register**
**(DAC_DHR12L2)**


Address offset: 0x18


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15 14 13 12 11 10 9 8 7 6 5 4|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|Res.|Res.|Res.|Res.|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|||||



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:4 **DACC2DHR[11:0]** : DAC channel2 12-bit left-aligned data

These bits are written by software which specify 12-bit data for DAC channel2.


Bits 3:0 Reserved, must be kept at reset value.


**14.10.8** **DAC channel2 8-bit right-aligned data holding register**
**(DAC_DHR8R2)**


Address offset: 0x1C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|
|||||||||rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:8 Reserved, must be kept at reset value.


Bits 7:0 **DACC2DHR[7:0]** : DAC channel2 8-bit right-aligned data

These bits are written by software which specifies 8-bit data for DAC channel2.


RM0364 Rev 4 337/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**


**14.10.9** **Dual DAC 12-bit right-aligned data holding register**
**(DAC_DHR12RD)**


Address offset: 0x20


Reset value: 0x0000 0000

|31|30|29|28|27 26 25 24 23 22 21 20 19 18 17 16|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|
|||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11 10 9 8 7 6 5 4 3 2 1 0|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|
|||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:28 Reserved, must be kept at reset value.


Bits 27:16 **DACC2DHR[11:0]** : DAC channel2 12-bit right-aligned data

These bits are written by software which specifies 12-bit data for DAC channel2.


Bits 15:12 Reserved, must be kept at reset value.


Bits 11:0 **DACC1DHR[11:0]** : DAC channel1 12-bit right-aligned data

These bits are written by software which specifies 12-bit data for DAC channel1.


**14.10.10 Dual DAC 12-bit left-aligned data holding register**
**(DAC_DHR12LD)**


Address offset: 0x24


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22 21 20|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|Res.|Res.|Res.|Res.|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|||||


|15 14 13 12 11 10 9 8 7 6 5 4|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|Res.|Res.|Res.|Res.|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|||||



Bits 31:20 **DACC2DHR[11:0]** : DAC channel2 12-bit left-aligned data

These bits are written by software which specifies 12-bit data for DAC channel2.


Bits 19:16 Reserved, must be kept at reset value.


Bits 15:4 **DACC1DHR[11:0]** : DAC channel1 12-bit left-aligned data

These bits are written by software which specifies 12-bit data for DAC channel1.


Bits 3:0 Reserved, must be kept at reset value.


**14.10.11 Dual DAC 8-bit right-aligned data holding register**
**(DAC_DHR8RD)**


Address offset: 0x28


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||



338/1124 RM0364 Rev 4


**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**

|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:16 Reserved, must be kept at reset value.


Bits 15:8 **DACC2DHR[7:0]** : DAC channel2 8-bit right-aligned data

These bits are written by software which specifies 8-bit data for DAC channel2.


Bits 7:0 **DACC1DHR[7:0]** : DAC channel1 8-bit right-aligned data

These bits are written by software which specifies 8-bit data for DAC channel1.


**14.10.12 DAC channel1 data output register (DAC_DOR1)**


Address offset: 0x2C


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11 10 9 8 7 6 5 4 3 2 1 0|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|
|||||r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:12 Reserved, must be kept at reset value.


Bits 11:0 **DACC1DOR[11:0]** : DAC channel1 data output

These bits are read-only, they contain data output for DAC channel1.


**14.10.13 DAC channel2 data output register (DAC_DOR2)**


Address offset: 0x30

Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11 10 9 8 7 6 5 4 3 2 1 0|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|
|||||r|r|r|r|r|r|r|r|r|r|r|r|



Bits 31:12 Reserved, must be kept at reset value.


Bits 11:0 **DACC2DOR[11:0]** : DAC channel2 data output

These bits are read-only, they contain data output for DAC channel2.


**14.10.14 DAC status register (DAC_SR)**


Address offset: 0x34


Reset value: 0x0000 0000


RM0364 Rev 4 339/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|DMAUDR2|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||rc_w1||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|DMAUDR1|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||rc_w1||||||||||||||



Bits 31:30 Reserved, must be kept at reset value.


Bit 29 **DMAUDR2** : DAC channel2 DMA underrun flag

This bit is set by hardware and cleared by software (by writing it to 1).

0: No DMA underrun error condition occurred for DAC channel2

1: DMA underrun error condition occurred for DAC channel2 (the currently selected trigger is
driving DAC channel2 conversion at a frequency higher than the DMA service capability rate)

_Note: This bit is available in dual mode only. It is reserved in single mode._


Bits 28:14 Reserved, must be kept at reset value.


Bit 13 **DMAUDR1** : DAC channel1 DMA underrun flag

This bit is set by hardware and cleared by software (by writing it to 1).

0: No DMA underrun error condition occurred for DAC channel1

1: DMA underrun error condition occurred for DAC channel1 (the currently selected trigger is
driving DAC channel1 conversion at a frequency higher than the DMA service capability rate)


Bits 12:0 Reserved, must be kept at reset value.


340/1124 RM0364 Rev 4


**RM0364** **Digital-to-analog converter (DAC1 and DAC2)**


**14.10.15 DAC register map**


_Table 55_ summarizes the DAC registers.


**Table 55. DAC register map and reset values**









































































|Offset|Register<br>name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**DAC_CR**|Res.|Res.|DMAUDRIE2|DMAEN2|MAMP2[3:0]|MAMP2[3:0]|MAMP2[3:0]|MAMP2[3:0]|WAVE2[1:0]|WAVE2[1:0]|TSEL2[2:0]|TSEL2[2:0]|TSEL2[2:0]|TEN2|BOFF2|EN2|Res.|Res.|DMAUDRIE1|DMAEN1|MAMP1[3:0].|MAMP1[3:0].|MAMP1[3:0].|MAMP1[3:0].|WAVE1[1:0]|WAVE1[1:0]|TSEL1[2:0]|TSEL1[2:0]|TSEL1[2:0]|TEN1|BOFF1|EN1|
|0x00|Reset value|||0|0|0|0|0|0|0|0|0|0|0|0|0|0|||0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x04|**DAC_**<br>**SWTRIGR**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SWTRIG2|SWTRIG1|
|0x04|Reset value|||||||||||||||||||||||||||||||0|0|
|0x08|**DAC_**<br>**DHR12R1**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|
|0x08|Reset value|||||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|
|0x0C|**DAC_**<br>**DHR12L1**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|Res.|Res.|Res.|Res.|
|0x0C|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|||||
|0x10|**DAC_**<br>**DHR8R1**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|
|0x10|Reset value|||||||||||||||||||||||||0|0|0|0|0|0|0|0|
|0x14|**DAC_**<br>**DHR12R2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|
|0x14|Reset value|||||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|
|0x18|**DAC_**<br>**DHR12L2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|Res.|Res.|Res.|Res.|
|0x18|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|||||
|0x1C|**DAC_**<br>**DHR8R2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|
|0x1C|Reset value|||||||||||||||||||||||||0|0|0|0|0|0|0|0|
|0x20|**DAC_**<br>**DHR12RD**|Res.|Res.|Res.|Res.|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|Res.|Res.|Res.|Res.|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|
|0x20|Reset value|||||0|0|0|0|0|0|0|0|0|0|0|0|||||0|0|0|0|0|0|0|0|0|0|0|0|
|0x24|**DAC_**<br>**DHR12LD**|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|DACC2DHR[11:0]|Res.|Res.|Res.|Res.|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|DACC1DHR[11:0]|Res.|Res.|Res.|Res.|
|0x24|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|||||0|0|0|0|0|0|0|0|0|0|0|0|||||
|0x28|**DAC_**<br>**DHR8RD**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC2DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|DACC1DHR[7:0]|
|0x28|Reset value|||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x2C|**DAC_DOR1**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|DACC1DOR[11:0]|
|0x2C|Reset value|||||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|
|0x30|**DAC_DOR2**|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|DACC2DOR[11:0]|
|0x30|Reset value|||||||||||||||||||||0|0|0|0|0|0|0|0|0|0|0|0|


RM0364 Rev 4 341/1124



342


**Digital-to-analog converter (DAC1 and DAC2)** **RM0364**


**Table 55. DAC register map** **(continued)and reset values (continued)**

|Offset|Register<br>name|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x34|**DAC_SR**|Res.|Res.|DMAUDR2|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|DMAUDR1|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x34|Reset value|||0||||||||||||||||0||||||||||||||



Refer to _Section 2.2 on page 47_ for the register boundary addresses.


342/1124 RM0364 Rev 4


