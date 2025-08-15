**Peripheral interconnect matrix** **RM0364**

# **7 Peripheral interconnect matrix**

## **7.1 Introduction**


Several STM32F3 peripherals have internal interconnections. Knowing these
interconnections allows the following benefits:


      - Autonomous communication between peripherals,


      - Efficient synchronization between peripherals,


      - Discard the software latency and minimize GPIOs configuration,


      - Optimum number of available pins even with small packages,


      - Avoid the use of connectors and design an optimized PCB with less dissipated energy.

## **7.2 Connection summary**


The following table presents the matrix for the peripheral interconnect.


**Table 20. STM32F334 peripherals interconnect matrix** **[(1)]**





|Source /<br>Destination|DMA1|ADC1|ADC2|COMP2|COMP4|COMP6|OPAMP|TIM1|TIM15|TIM16|TIM17|TIM2|TIM3|DAC1|DAC2|IRTIM|HRTIM1|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ADC1|x|-|x|-|-|-|-|x|-|-|-|-|-|-|-|-|x|
|ADC2|x|-|-|-|-|-|-|x|-|-|-|-|-|-|-|-|x|
|COMP2|-|-|-|-|-|-|-|x|-|-|-|x|x|-|-|-|x|
|COMP4|-|-|-|-|-|-|-|-|x|-|-|-|x|-|-|-|x|
|COMP6|-|-|-|-|-|-|-|-|-|x|x|x|x|-|-|-|x|
|OPAMP2|-|-|x|-|-|-|-|-|-|-|-|-|-|-|-|-|x|
|TIM1|x|x|x|x|-|-|x|-|-|-|-|x|x|-|-|-|x|
|SPI1|x|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|
|USART1|x|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|
|TIM15|x|x|x|-|x|x|-|x|-|-|-|-|x|x|x|-|x|
|TIM16|x|-|-|-|-|-|-|-|x|-|-|-|-|-|-|x|x|
|TIM17|x|-|-|-|-|-|-|x|x|-|-|-|-|-|-|x|x|
|TIM2|x|x|x|x|-|x|-|x|x|-|-|-|x|x|x|-|x|
|TIM3|x|x|x|x|x|-|-|x|x|-|-|x|-|x|x|-|x|
|TIM6|x|x|x|-|-|-|-|-|-|-|-|-|-|x|x|-|x|
|TIM7|x|-|-|-|-|-|-|-|-|-|-|-|-|x|x|-|x|
|USART2|x|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|
|USART3|x|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|
|I2C1|x|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|
|DAC1|x|-|-|x|x|x|-|-|-|-|-|-|-|-|-|-|-|


96/1124 RM0364 Rev 4


**RM0364** **Peripheral interconnect matrix**


**Table 20. STM32F334 peripherals interconnect matrix** **[(1)]** **(continued)**





|Source /<br>Destination|DMA1|ADC1|ADC2|COMP2|COMP4|COMP6|OPAMP|TIM1|TIM15|TIM16|TIM17|TIM2|TIM3|DAC1|DAC2|IRTIM|HRTIM1|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DAC2|x|-|-|x|x|x|-|-|-|-|-|-|-|-|-|-|-|
|TS|-|x|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|
|VBAT|-|x|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|
|Vrefint|-|x|x|x|x|-|-|-|-|-|-|-|-|-|-|-|-|
|CSS|-|-|-|-|-|-|-|x|x|-|-|-|-|-|-|-|x|
|PVD|-|-|-|-|-|-|-|x|x|-|-|-|-|-|-|-|x|
|SRAM Parity<br>error|-|-|-|-|-|-|-|x|x|-|-|-|-|-|-|-|x|
|CPU Hardfault|-|-|-|-|-|-|-|x|x|-|-|-|-|-|-|-|x|
|HSE|-|-|-|-|-|-|-|-|-|x|-|-|-|-|-|-|-|
|HSI|-|-|-|-|-|-|-|-|-|x|-|-|-|-|-|-|-|
|LSE|-|-|-|-|-|-|-|-|-|x|-|-|-|-|-|-|-|
|LSI|-|-|-|-|-|-|-|-|-|x|-|-|-|-|-|-|-|
|MCO|-|-|-|-|-|-|-|-|-|x|-|-|-|-|-|-|-|
|RTC|-|-|-|-|-|-|-|-|-|x|-|-|-|-|-|-|-|
|HRTIM1|x|x|x|-|-|-|-|-|-|-|-|-|-|x|x|-|-|


1. The cells with gray shading indicate that there is no interconnection.

## **7.3 Interconnection details**


**7.3.1** **DMA interconnections**


Hardware DMA requests are managed by peripherals. The DMA channels dedicated to
each peripheral are summarized in _Section 11.3.2: DMA request mapping_ .


**7.3.2** **From ADC to ADC**


ADC1 can be used as a "master" to trigger ADC2 "slave" start of conversion.


In dual ADC mode, the converted data of the master and slave ADCs can be read in
parallel.


A description of dual ADC mode is provided in _Section 13.3.29: Dual ADC modes_ .


**7.3.3** **From ADC to TIM**


ADCx (x=1, 2) can provide trigger event through watchdog signals to advanced-control
timer TIM1.


A description of the ADC analog watchdog settings is provided in _Section 13.3.28: Analog_
_window watchdog (AWD1EN, JAWD1EN, AWD1SGL, AWD1CH, AWD2CH, AWD3CH,_
_AWD_HTx, AWD_LTx, AWDx)._


RM0364 Rev 4 97/1124



103


**Peripheral interconnect matrix** **RM0364**


The output (from ADC) is on signals ADCx_AWDy_OUT (x = 1, 2 and y = 1..3 as there are 3
analog watchdogs per ADC) and the input (to timer) on signal TIM1_ETR (external trigger).


TIM1_ETR is connected to ADCx_AWDy_OUT through bits in TIM1_OR registers; refer to
_Section 18.4.23: TIM1 option registers (TIM1_OR)._


**7.3.4** **From TIM and EXTI to ADC**


General-purpose timers (TIM2/TIM3), basic timers (TIM6/TIM7), advanced-control timer
(TIM1), general-purpose timer (TIM15/TIM16/TIM17) and EXTI can be used to generate an
ADC triggering event.


The output (from timer) is on signal TIMx_TRGO, TIMx_TRGO2 or TIMx_CCx event.


The input (to ADC) is on signal EXT[15:0], JEXT[15:0].


The connection between timers and ADCs or also EXTI & ADCs is provided in:


      - _Table 40: ADC1 (master) & 2 (slave) - External triggers for regular channels_


      - _Table 41: ADC1 & ADC2 - External trigger for injected channels_


**7.3.5** **From OPAMP to ADC**


There are two interconnection types:


1. Connect OPAMP output reference voltage to an internal ADC channel. This connection
can be used for OPAMP calibration. For more details, please refer to the
_Section 16.3.5: Calibration_ .


_ADC2_IN17 is the channel connected internally to the reference voltage for OPAMP2._


2. OPAMP2 can be connected to ADC2_IN3. Refer to _Section 16.3.4: Using the OPAMP_
_outputs as ADC inputs._


**7.3.6** **From TS to ADC**


Internal temperature sensor (VTS) is connected internally to ADC1_IN16. Refer to
_Section 13.3.30: Temperature sensor_ .


**7.3.7** **From VBAT to ADC**


VBAT/2 output voltage can be converted using ADC1_IN17. This interconnection is
explained in _Section 13.3.31: VBAT supply monitoring_ .


**7.3.8** **From VREFINT to ADC**


VREFINT is internally connected to channel 18 of the two ADCs. This allows the monitoring
of its value as described in _Section 13.3.32: Monitoring the internal voltage reference_ .


**7.3.9** **From COMP to TIM**


The comparators outputs can be redirected internally to different timer inputs:


      - break input 1/2 for fast PWM shutdowns,


      - OCREF_CLR input,


      - Input capture.


98/1124 RM0364 Rev 4


**RM0364** **Peripheral interconnect matrix**


To select which timer input must be connected to the comparator output, the bits field
COMPxOUTSEL in the COMPx_CSR register are used.


The following table gives an overview of all possible comparator outputs redirection to the
timer inputs.









|Table 21. Comparator outputs to timer inputs|Col2|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
|**COMP output selection**|**COMP output selection**|**COMP output selection**|**COMP output selection**|**COMP output selection**|**COMP output selection**|
|-|**TIM1**|**TIM2**|**TIM3**|**TIM15**|**TIM16**|
|COMP2|TIM1_BRK_ACTH<br>TIM1_BRK2<br>TIM1_OCrefClear<br>TIM1_IC1|TIM2_IC4<br>TIM2_OCrefClear|TIM3_IC1<br>TIM3_OCrefClear|-|-|
|COMP4|TIM1_BRK<br>TIM1_BRK2|-|TIM3_IC3<br>TIM3_OCrefClear|TIM15_OCrefCle<br>arTIM15_IC2|-|
|COMP6|TIM1_BRK_ACTH<br>TIM1_BRK2|TIM2_IC2<br>TIM2_OCrefClear|-|-|TIM16_OCrefClear<br>TIM16_IC1|


_Note:_ _When the comparator output is configured to be connected internally to timers break input,_
_the following must be considered:_


_1/ COMP2/6 can be used to control TIM1_BRK_ACTH (this break is always active high with_
_no digital filter) and to control also TIM1_BRK2 input._


_2/ COMP4 can be used to control TIM1_BRK and TIM1_BRK2 input (same as the other_
_comparators)._


**7.3.10** **From TIM to COMP**


The timers output can be selected as comparators outputs blanking signals using the
“COMPx_BLANKING” bits in “COMPx_CSR” register. More details on the blanking function
can be found in _Section 15.3.5: Comparator output blanking function_ .

|Table 22. Timer output selection as comparator blanking source|Col2|Col3|Col4|
|---|---|---|---|
|**COMP blanking source**|**COMP blanking source**|**COMP blanking source**|**COMP blanking source**|
|-|**COMP2**|**COMP4**|**COMP6**|
|TIM1|TIM1 OC5|-|-|
|TIM15|-|TIM15 OC1|TIM15 OC2|
|TIM2|TIM2 OC3|-|TIM2 OC4|
|TIM3|TIM3 OC3|TIM3 OC4|-|



RM0364 Rev 4 99/1124



103


**Peripheral interconnect matrix** **RM0364**


**7.3.11** **From DAC to COMP**


The comparators inverting input may be a DAC channel output (DAC1_CH1, DAC1_CH2 or
DAC2_CH1).


The selection is made based on “COMPxINMSEL” bits value in “COMPx_CSR” register.


The following table summarizes these interconnections.

|Table 23. DAC output selection as comparator inverting input|Col2|Col3|Col4|
|---|---|---|---|
|**COMP inverting inputs**|**COMP inverting inputs**|**COMP inverting inputs**|**COMP inverting inputs**|
|-|**COMP2**|**COMP4**|**COMP6**|
|DAC1_CH1|X|X|X|
|DAC1_CH2|X|X|X|
|DAC2_CH1|X|X|X|



**7.3.12** **From VREFINT to COMP**


Besides to the DAC channel output, Vrefint (x1, x3/4, x1/2, x1/4) can be selected as
comparator inverting input using “COMPxINMSEL” bits in “COMPx_CSR” register.


**7.3.13** **From TIM to OPAMP**


The switch between OPAMP inverting and non-inverting inputs can be done automatically.
This automatic switch is triggered by the TIM1 CC6 output arriving on the OPAMP input
multiplexers. More details on this feature are available in _Section 16.3.6: Timer controlled_
_Multiplexer mode_ .


**7.3.14** **From TIM to TIM**


Some STM32F3 timers are linked together internally for timer synchronization or chaining.


When one timer is configured in Master Mode, it can reset, start, stop or clock the counter of
another timer configured in Slave Mode.


A description of the feature with the various synchronization modes is available in:


      - _Section 18.3.25: Timer synchronization_ f _or the advanced-control timer TIM1_


      - _Section 18.3.25: Timer synchronization_ _for the general-purpose timers (TIM2/TIM3)_


The slave mode selection is made using “SMS” bits, as described in:


      - _Section 18.4.3: TIM1 slave mode control register (TIM1_SMCR),_


      - _Section 19.4.3: TIMx slave mode control register (TIMx_SMCR)(x = 2 to 3)_ _for the_
_general-purpose timers (TIM2/TIM3),_


      - _Section 20.5.3: TIM15 slave mode control register (TIM15_SMCR)_ .


100/1124 RM0364 Rev 4


**RM0364** **Peripheral interconnect matrix**


The possible master/slave connections are summarized in the following table providing the
internal trigger connection:

|Col1|Col2|Table 24. Timer synchronization|Col4|Col5|Col6|
|---|---|---|---|---|---|
|-|-|**SLAVE**|**SLAVE**|**SLAVE**|**SLAVE**|
|-|-|**TIM1**|**TIM2**|**TIM3**|**TIM15**|
|MASTER|TIM1|-|TIM2_ITR0|TIM3_ITR0|-|
|MASTER|TIM2|TIM1_ITR1|-|TIM3_ITR1|TIM15_ITR0|
|MASTER|TIM3|TIM1_ITR2|TIM2_ITR2|-|TIM15_ITR1|
|MASTER|TIM15|TIM1_ITR0||TIM3_ITR2|-|
|MASTER|TIM16|-||-|TIM15_ITR2|
|MASTER|TIM17|TIM1_ITR3||-|TIM15_ITR3|



**7.3.15** **From system errors to TIM**


In addition to comparators outputs, other sources can be used as trigger for the internal
break events of some timers (TIM1/TIM15/TIM16/TIM17). For example:


      - the clock failure event generated by CSS, refer to _Section 8.2.6: System clock_
_(SYSCLK) selection_ for more details,


      - the PVD output, refer to _Section 6.2.2: Programmable voltage detector (PVD)_ for more
details,


      - the SRAM parity error signal, refer to _Section 2.2.3: Parity check_ for more details,


      - the Cortex-M4 LOCKUP (Hardfault) output.


The sources mentioned above can be connected internally to TIMx_BRK_ACTH input, x =
1,15,16,17.


The purpose of the break function is to protect power switches driven by PWM signals
generated by the timers.


More details on the break feature are provided in:


      - _Section 18.3.16: Using the break function_ for the advanced-control timers (TIM1)


      - _Section 20.4.13: Using the break function_ for the general-purpose timers
(TIM15/TIM16/TIM17)


**7.3.16** **From HSE, HSI, LSE, LSI, MCO, RTC to TIM**


TIM16 can be used for the measurement of internal/external clock sources. TIM16 channel1
input capture is connected to HSE/32, GPIO, RTC clock and MCO to output clocks among
(HSE, HSI, LSE, LSI, SYSCLK, PLLCLK, PLLCLK/2).


The selection is performed through the TI1_RMP [1:0] bits in the TIM16_OR register.


This allows calibrating the HSI/LSI clocks.


More details are provided in _Section 8.2.14: Internal/external clock measurement with_
_TIM16_ .


RM0364 Rev 4 101/1124



103


**Peripheral interconnect matrix** **RM0364**


**7.3.17** **From TIM and EXTI to DAC**


A timer counter may be used as a trigger for DAC conversions.


The TRGO event is the internal signal that will trigger conversion.


The following table provides a summary of DACs interconnections with timers:


This is described in _Section 14.5.4: DAC trigger selection_ .


**Table 25. Timer and EXTI signals triggering DAC conversions**

|-|DAC1|DAC2|
|---|---|---|
|TIM2|X|X|
|TIM3|X|X|
|TIM6|X|X|
|TIM7|X|X|
|TIM15|X|X|
|EXTI line9|X|X|



**7.3.18** **From TIM to IRTIM**


General-purpose timer (TIM16/TIM17) output channels TIMx_OC1 are used to generate the
waveform of infrared signal output. The functionality is described in _Section 22: Infrared_
_interface (IRTIM)_ .


**7.3.19** **From ADC to HRTIM1**


ADCx (x=1, 2) provides the trigger event through watchdog signals to the high resolution


timer HRTIM1.


The exact mapping between HRTIM1 external events and ADC watchdog signals is
provided in _Table 86: External events mapping and associated features_ .


**7.3.20** **From system faults to HRTIM1**


The HRTIM1 system fault input (SYSFLT) gathers MCU internal fault events coming from:


–
the clock failure event generated by the clock security system (CSS),


–
the PVD output,


–
the SRAM parity error signal,


–
the Cortex-M4 LOCKUP (Hardfault) output.


Refer to _Section 21.3.15: Fault protection_ for more details on the HRTIM1 fault protection
feature.


**7.3.21** **From COMP to HRTIM1**


The comparator output can be redirected internally to HRTIM1 inputs.


_Table 56: STM32F334xx comparator input/outputs summary_ provides the exact mapping
between comparators outputs and HRTIM internal signals. It is also explained in _Table 86:_
_External events mapping and associated features_ .


102/1124 RM0364 Rev 4


**RM0364** **Peripheral interconnect matrix**


The comparator outputs are connected directly to HRTIM1 in order to speed-up the
propagation delay.


**7.3.22** **From OPAMP to HRTIM1**


The OPAMP2_VOUT can be used as a HRTIM1 internal event source connected to
HRTIM1_EEV4 or HRTIM1_EEV9 as shown in _Table 86: External events mapping and_
_associated features_


**7.3.23** **From TIM to HRTIM1**


The connections between timers and HRTIM1 are listed in _Table 86: External events_
_mapping and associated features_ .


**7.3.24** **From HRTIM1 to ADC**


The HRTIM1 can be used to generate an ADC trigger event on signal
HRTIM1_ADCTRG1/2/3/4.


More details on ADC triggering using HRTIM1 signals are provided in _Section 21.3.18: ADC_
_triggers_ **.**


**7.3.25** **From HRTIM1 to DAC**


The HRTIM1 DACTRGx events can be selected as internal signals to trigger DAC
conversion depending on the value of TSELx[2:0] control bits in DAC_CR register.


More details on ADC triggering using HRTIM1 signals are provided in _Section 21.3.18: ADC_
_triggers_ **.**


RM0364 Rev 4 103/1124



103


