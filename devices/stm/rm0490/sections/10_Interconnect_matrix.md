**RM0490** **Interconnect matrix**

# **10 Interconnect matrix**

## **10.1 Introduction**


Several peripherals have direct connections between them.


This allows autonomous communication and/or synchronization between peripherals,
saving CPU resources thus power consumption.


In addition, these hardware connections remove software latency and allow design of
predictable systems.


Depending on peripherals, these interconnections can operate in Run, Sleep, and Stop
mode.


For availability of peripherals on different STM32C0 series products, refer to _Section 1.5:_
_Availability of peripherals_ .

## **10.2 Connection summary**


The numbers in the following table are links to corresponding sub-sections in _Section 10.3:_
_Interconnection details_ .The “-” symbol in grayed cells means “no interconnection”.


**Table 42. Interconnect matrix**





|Destination ►<br>Source ▼|TIM1|TIM2|TIM3|TIM14|TIM15|TIM16|TIM17|ADC1|DMAMUX|IRTIM|
|---|---|---|---|---|---|---|---|---|---|---|
|TIM1|-|_10.3.1_|_10.3.1_|-|-|-|-|_10.3.2_|-|-|
|TIM2|_10.3.1_|-|_10.3.1_|-|_10.3.1_|-|-|_10.3.2_|-|-|
|TIM3|_10.3.1_|_10.3.1_|-|-|_10.3.1_|-|-|_10.3.2_|-|-|
|TIM14|-||_10.3.1_|-|-|-|-|-|_10.3.8_|-|
|TIM15|_10.3.1_|_10.3.1_|_10.3.1_|-|-|-|-|_10.3.2_|_10.3.8_|-|
|TIM16|-|-|-|-|_10.3.1_|-|-|-|-|_10.3.7_|
|TIM17|_10.3.1_|-|-|-|_10.3.1_|-|-|-|-|_10.3.7_|
|USART1|-|-|-|-|-|-|-|-|-|_10.3.7_|
|USART2|-|-|-|-|-|-|-|-|-|_10.3.7_|
|ADC|_10.3.3_|-|-|-|-|-|-|-|-|-|
|Temp. sensor|-|-|-|-|-|-|-|_10.3.5_|-|-|
|VREFINT|-|-|-|-|-|-|-|_10.3.5_|-|-|
|HSE|-|-|-|_10.3.4_|-|-|_10.3.4_|-|-|-|
|LSE|-|-|-|-|-|_10.3.4_|-|-|-|-|
|LSI|-|-|-|-|-|_10.3.4_|-|-|-|-|
|MCO|-|-|-|_10.3.4_|-|-|_10.3.4_|-|-|-|


RM0490 Rev 5 217/1027



221


**Interconnect matrix** **RM0490**


**Table 42. Interconnect matrix (continued)**





|Destination ►<br>Source ▼|TIM1|TIM2|TIM3|TIM14|TIM15|TIM16|TIM17|ADC1|DMAMUX|IRTIM|
|---|---|---|---|---|---|---|---|---|---|---|
|MCO2|-|-|-|_10.3.4_|-|_10.3.4_|_10.3.4_|-|-|-|
|EXTI|-|-|-|-|-|-|-|_10.3.2_|_10.3.2_|-|
|RTC|-|-|-|_10.3.4_|-|-|-|-|-|-|
|SYST ERR|_10.3.6_|-|-|-|_10.3.6_|_10.3.6_|_10.3.6_|-|-|-|

## **10.3 Interconnection details**

**10.3.1** **From TIM1, TIM2, TIM3, TIM14, TIM15, and TIM17, to TIM1, TIM2,**
**and TIM3**


**Purpose**


Some of the TIMx timers are linked together internally for timer synchronization or chaining.


When one timer is configured in master mode, it can reset, start, stop or clock the counter of
another timer configured in slave mode.


A description of the feature is provided in: _Section 18.3.19: Timer synchronization_ .


The modes of synchronization are detailed in:


      - _Section 17.3.26: Timer synchronization_ for advanced-control timer TIM1


      - _Section 18.3.18: Timers and external trigger synchronization_ for general-purpose
timers TIM2/TIM3


      - _Section 20.4.20: External trigger synchronization (TIM15 only)_ for general-purpose
timer TIM15


**Triggering signals**


The output (from master) is on signal TIMx_TRGO (and TIMx_TRGOx), following a
configurable timer event.


With TIM14, TIM16 and TIM17 timers that do not have a trigger output, the output
compare 1 is used instead.


The input (to slave) is on signals TIMx_ITR0/ITR1/ITR2/ITR3.


The input and output signals for TIM1 are shown in _Figure 57: Advanced-control timer block_
_diagram_ .


The possible master/slave connections are given in _Table 80: TIM1 internal trigger_
_connection_ .


**Relevant power modes**


These interconnections operate in Run and Sleep modes.


218/1027 RM0490 Rev 5


**RM0490** **Interconnect matrix**


**10.3.2** **From TIM1, TIM2, TIM3, TIM15, and EXTI, to ADC**


**Purpose**


The general-purpose timer TIM3, TIM15, advanced-control timer TIM1, and EXTI can be
used to generate an ADC triggering event.


TIMx synchronization is described in: _Section 17.3.27: ADC synchronization_ .


ADC synchronization is described in: _Section 16.5: Conversion on external trigger and_
_trigger polarity (EXTSEL, EXTEN)_ .


**Triggering signals**


The output (from timer) is on signal TIMx_TRGO, TIMx_TRGO2 or TIMx_CCx event.


The input (to ADC) is on signal TRG[7:0].


The connection between timers and ADC is provided in _Table 68: External triggers_ .


**Relevant power modes**


These interconnections operate in Run and Sleep modes.


**10.3.3** **From ADC to TIM1**


**Purpose**


ADC can provide trigger event through watchdog signals to the advanced-control timer
TIM1.


A description of the ADC analog watchdog setting is provided in: _Section 16.8: Analog_
_window watchdogs_ .


Trigger settings on the timer are provided in: _Section 17.3.4: External trigger input_ .


**Triggering signals**


The output (from ADC) is on signals ADC_AWDx_OUT x = 1, 2, 3 (three watchdogs per
ADC) and the input (to timer) on signal TIMx_ETR (external trigger).


**Relevant power modes**


This interconnection operates in Run and Sleep modes.


**10.3.4** **From HSE, LSE, LSI, MCO, MCO2, and RTC, to TIM14,**
**TIM16, and TIM17**


**Purpose**


External clocks (HSE, LSE), internal clock (LSI), microcontroller output clock (MCO and
MCO2), RTC clock, and GPIO can be selected as inputs to capture channel 1 of some of
TIM14/16/TIM17 timers.


The timers allow calibrating or precisely measuring internal clocks such as HSI48 or LSI,
using accurate clocks such as LSE or HSE/32 for timing reference. See details in
_Section 6.2.14: Internal/external clock measurement with TIM14/TIM16/TIM17_ .


RM0490 Rev 5 219/1027



221


**Interconnect matrix** **RM0490**


When low-speed external (LSE) oscillator is used, no additional hardware connections are
required.


**Relevant power modes**


These interconnections operate in Run and Sleep modes.


**10.3.5** **From internal analog sources to ADC**


**Purpose**


The internal temperature sensor output voltage V TS and the internal reference voltage
V REFINT channel are connected to ADC input channels.


More information is in:


      - _Section 16.2: ADC main features_


      - _Section 16.4.8: Channel selection (CHSEL, SCANDIR, CHSELRMOD)_


      - _Figure 16.10: Temperature sensor and internal reference voltage_


**Relevant power modes**


These interconnections operate in Run and Sleep modes.


**10.3.6** **From system errors to TIM1, TIM15, TIM16, and TIM17**


**Purpose**


CSS, CPU HardFault, and RAM parity error can generate system errors in the form of timer
break toward TIM1, TIM16, and TIM17.


The purpose of the break function is to protect power switches driven by PWM signals from
the timers.


The relevant information is in:


      - _Section 17.3.16: Using the break function_ (TIM1)


      - _Section 20.4.13: Using the break function_ (TIM15/TIM16/TIM17)


      - _Figure 182: TIM15 block diagram_


      - _Figure 183: TIM16/TIM17 block diagram_


**Relevant power modes**


These interconnections operate in Run and Sleep modes.


**10.3.7** **From TIM16, TIM17, USART1, and USART2, to IRTIM**


**Purpose**


TIMx_OC1 output channel of TIM17 timer, associated with USART1 or USART2
transmission signal, can generate the infrared output waveform.


The functionality is described in _Section 21: Infrared interface (IRTIM)_ .


**Relevant power modes**


These interconnections operate in Run and Sleep modes.


220/1027 RM0490 Rev 5


**RM0490** **Interconnect matrix**


**10.3.8** **From TIM14 and EXTI to DMAMUX**


**Purpose**


TIM14 general-purpose timer and EXTI can be used as triggering event to DMAMUX.


**Relevant power modes**


These interconnections operate in Run and Sleep modes.


RM0490 Rev 5 221/1027



221


