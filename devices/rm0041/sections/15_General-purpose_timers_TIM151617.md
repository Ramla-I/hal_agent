**General-purpose timers (TIM15/16/17)** **RM0041**

# **15 General-purpose timers (TIM15/16/17)**


**Low-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 16 and 32 Kbytes.


**Medium-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 64 and 128 Kbytes.


**High-density value line devices** are STM32F100xx microcontrollers where the flash
memory density ranges between 256 and 512 Kbytes.


_This_ section _applies to the whole STM32F100xx family, unless otherwise specified._

## **15.1 TIM15/16/17 introduction**


The TIM15/16/17 timers consist of a 16-bit auto-reload counter driven by a programmable
prescaler.


They may be used for a variety of purposes, including measuring the pulse lengths of input
signals (input capture) or generating output waveforms (output compare, PWM,
complementary PWM with dead-time insertion).


Pulse lengths and waveform periods can be modulated from a few microseconds to several
milliseconds using the timer prescaler and the RCC clock controller prescalers.


The TIM15/16/17 timers are completely independent, and do not share any resources. They
can be synchronized together as described in _Section 14.3.12_ .


388/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**

## **15.2 TIM15 main features**


TIM15 includes the following features:


      - 16-bit auto-reload upcounter


      - 16-bit programmable prescaler used to divid (also “on the fly”) the counter clock
frequency by any factor between 1 and 65536


      - Up to 2 independent channels for:


–
Input capture


–
Output compare


–
PWM generation (edge mode)


–
One-pulse mode output


      - Complementary outputs with programmable dead-time (for channel 1 only)


      - Synchronization circuit to control the timer with external signals and to interconnect
several timers together


      - Repetition counter to update the timer registers only after a given number of cycles of
the counter


      - Break input to put the timer’s output signals in the reset state or a known state


      - Interrupt/DMA generation on the following events:


–
Update: counter overflow, counter initialization (by software or internal/external
trigger)


–
Trigger event (counter start, stop, initialization or count by internal/external trigger)


–
Input capture


–
Output compare


–
Break input (interrupt request)


RM0041 Rev 6 389/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**

## **15.3 TIM16 and TIM17 main features**


The TIM16 and TIM17 timers include the following features:


      - 16-bit auto-reload upcounter


      - 16-bit programmable prescaler used to divide (also “on the fly”) the counter clock
frequency by any factor between 1 and 65536


      - One channel for:


–
Input capture


–
Output compare


–
PWM generation (edge-aligned mode)


–
One-pulse mode output


      - Complementary outputs with programmable dead-time


      - Repetition counter to update the timer registers only after a given number of cycles of
the counter


      - Break input to put the timer’s output signals in the reset state or a known state


      - Interrupt/DMA generation on the following events:


–
Update: counter overflow


–
Trigger event (counter start, stop, initialization or count by internal/external trigger)


–
Input capture


–
Output compare


–
Break input


390/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**Figure 157. TIM15 block diagram**































































































RM0041 Rev 6 391/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**Figure 158. TIM16 and TIM17 block diagram**













































392/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**

## **15.4 TIM15/16/17 functional description**


**15.4.1** **Time-base unit**


The main block of the programmable timer is a 16-bit counter with its related auto-reload
register. The counter can count up, down or both up and down. The counter clock can be
divided by a prescaler.


The counter, the auto-reload register and the prescaler register can be written or read by
software. This is true even when the counter is running.


The time-base unit includes:


      - Counter register (TIMx_CNT)


      - Prescaler register (TIMx_PSC)


      - Auto-reload register (TIMx_ARR)


      - Repetition counter register (TIMx_RCR)


The auto-reload register is preloaded. Writing to or reading from the auto-reload register
accesses the preload register. The content of the preload register are transferred into the
shadow register permanently or at each update event (UEV), depending on the auto-reload
preload enable bit (ARPE) in TIMx_CR1 register. The update event is sent when the counter
reaches the overflow (or underflow when downcounting) and if the UDIS bit equals 0 in the
TIMx_CR1 register. It can also be generated by software. The generation of the update
event is described in detailed for each configuration.


The counter is clocked by the prescaler output CK_CNT, which is enabled only when the
counter enable bit (CEN) in TIMx_CR1 register is set (refer also to the slave mode controller
description to get more details on counter enabling).


Note that the counter starts counting 1 clock cycle after setting the CEN bit in the TIMx_CR1
register.


**Prescaler description**


The prescaler can divide the counter clock frequency by any factor between 1 and 65536. It
is based on a 16-bit counter controlled through a 16-bit register (in the TIMx_PSC register).
It can be changed on the fly as this control register is buffered. The new prescaler ratio is
taken into account at the next update event.


_Figure 159_ and _Figure 160_ give some examples of the counter behavior when the prescaler
ratio is changed on the fly:


RM0041 Rev 6 393/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**Figure 159. Counter timing diagram with prescaler division change from 1 to 2**











|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|F8|F9<br>|FA|FB|FC|00<br>|00<br>|01|01|02|02|03|03|
|F8|F9<br>|FA|FB|FC|||||||||
|F8|F9<br>|FA|FB|FC|||||||||
|F8|F9<br>|FA|FB|FC|||||||||
|F8|F9<br>|FA|FB|FC|||||||||
|F8|F9<br>|FA|FB|FC|0|1|0|1|0|1|0|1|


**Figure 160. Counter timing diagram with prescaler division change from 1 to 4**











**15.4.2** **Counter modes**


**Upcounting mode**

|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|F8|F9<br>|FA|FB|FC|00<br>|00<br>|00<br>|00<br>|00<br>|00<br>|00<br>|00<br>|
|F8|F9<br>|FA|FB|FC|||||||||
|F8|F9<br>|FA|FB|FC|||||||||
|F8|F9<br>|FA|FB|FC|||||||||
|F8|F9<br>|FA|FB|FC|||||||||
|F8|F9<br>|FA|FB|FC|0|1|2|3|0|1|2|3|



In upcounting mode, the counter counts from 0 to the auto-reload value (content of the
TIMx_ARR register), then restarts from 0 and generates a counter overflow event.


If the repetition counter is used, the update event (UEV) is generated after upcounting is
repeated for the number of times programmed in the repetition counter register plus one
(TIMx_RCR + 1). Else the update event is generated at each counter overflow.


Setting the UG bit in the TIMx_EGR register (by software or by using the slave mode
controller) also generates an update event.


The UEV event can be disabled by software by setting the UDIS bit in the TIMx_CR1
register. This is to avoid updating the shadow registers while writing new values in the


394/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


preload registers. Then no update event occurs until the UDIS bit has been written to 0.
However, the counter restarts from 0, as well as the counter of the prescaler (but the
prescale rate does not change). In addition, if the URS bit (update request selection) in
TIMx_CR1 register is set, setting the UG bit generates an update event UEV but without
setting the UIF flag (thus no interrupt or DMA request is sent). This is to avoid generating
both update and capture interrupts when clearing the counter on the capture event.


When an update event occurs, all the registers are updated and the update flag (UIF bit in
TIMx_SR register) is set (depending on the URS bit):


      - The repetition counter is reloaded with the content of TIMx_RCR register,


      - The auto-reload shadow register is updated with the preload value (TIMx_ARR),


      - The buffer of the prescaler is reloaded with the preload value (content of the TIMx_PSC
register).


The following figures show some examples of the counter behavior for different clock
frequencies when TIMx_ARR=0x36.


**Figure 161. Counter timing diagram, internal clock divided by 1**






|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|32|33|34|35|36|00<br>|01|02|03|04|05|06|07|



**Figure 162. Counter timing diagram, internal clock divided by 2**







RM0041 Rev 6 395/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**Figure 163. Counter timing diagram, internal clock divided by 4**









**Figure 164. Counter timing diagram, internal clock divided by N**


**Figure 165. Counter timing diagram, update event when ARPE=0 (TIMx_ARR not**
**preloaded)**






|2 33 34 35 36|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|2 33|34|35|36|00|01|0|2 03|04|05|06|07|



396/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**Figure 166. Counter timing diagram, update event when ARPE=1 (TIMx_ARR**
**preloaded)**






|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|F|1 F2|F3|F4|F5|00|01|02|03|04|05|06|07|



**15.4.3** **Repetition counter**


_Section 14.3.1: Time-base unit_ describes how the update event (UEV) is generated with
respect to the counter overflows/underflows. It is actually generated only when the repetition
counter has reached zero. This can be useful when generating PWM signals.


This means that data are transferred from the preload registers to the shadow registers
(TIMx_ARR auto-reload register, TIMx_PSC prescaler register, but also TIMx_CCRx
capture/compare registers in compare mode) every N+1 counter overflows or underflows,
where N is the value in the TIMx_RCR repetition counter register.


The repetition counter is decremented at each counter overflow in upcounting mode.


The repetition counter is an auto-reload type; the repetition rate is maintained as defined by
the TIMx_RCR register value (refer to _Figure 167_ ). When the update event is generated by
software (by setting the UG bit in TIMx_EGR register) or by hardware through the slave
mode controller, it occurs immediately whatever the value of the repetition counter is and the
repetition counter is reloaded with the content of the TIMx_RCR register.


RM0041 Rev 6 397/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**Figure 167. Update rate examples depending on mode and TIMx_RCR register**
**settings**







**15.4.4** **Clock selection**


The counter clock can be provided by the following clock sources:


      - Internal clock (CK_INT)


      - External clock mode1: external input pin






      - Internal trigger inputs (ITRx) (only for TIM15): using one timer as the prescaler for
another timer, for example, TIM1 can be configured to act as a prescaler for TIM15.
Refer to _Using one timer as prescaler for another timer_ for more details.


**Internal clock source (CK_INT)**


If the slave mode controller is disabled (SMS=000), then the CEN, DIR (in the TIMx_CR1
register) and UG bits (in the TIMx_EGR register) are actual control bits and can be changed
only by software (except UG which remains cleared automatically). As soon as the CEN bit
is written to 1, the prescaler is clocked by the internal clock CK_INT.


_Figure 144_ shows the behavior of the control circuit and the upcounter in normal mode,
without prescaler.


398/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**Figure 168. Control circuit in normal mode, internal clock divided by 1**


**External clock source mode 1**


This mode is selected when SMS=111 in the TIMx_SMCR register. The counter can count at
each rising or falling edge on a selected input.


**Figure 169. TI2 external clock connection example**































For example, to configure the upcounter to count in response to a rising edge on the TI2
input, use the following procedure:


1. Configure channel 2 to detect rising edges on the TI2 input by writing CC2S = ‘01’ in
the TIMx_CCMR1 register.


2. Configure the input filter duration by writing the IC2F[3:0] bits in the TIMx_CCMR1
register (if no filter is needed, keep IC2F=0000).


3. Select rising edge polarity by writing CC2P=0 in the TIMx_CCER register.


4. Configure the timer in external clock mode 1 by writing SMS=111 in the TIMx_SMCR
register.


5. Select TI2 as the trigger input source by writing TS=110 in the TIMx_SMCR register.


6. Enable the counter by writing CEN=1 in the TIMx_CR1 register.


_Note:_ _The capture prescaler is not used for triggering, so there’s no need to configure it._


When a rising edge occurs on TI2, the counter counts once and the TIF flag is set.


The delay between the rising edge on TI2 and the actual clock of the counter is due to the
resynchronization circuit on TI2 input.


RM0041 Rev 6 399/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**Figure 170. Control circuit in external clock mode 1**


**15.4.5** **Capture/compare channels**


Each Capture/Compare channel is built around a capture/compare register (including a
shadow register), a input stage for capture (with digital filter, multiplexing and prescaler) and
an output stage (with comparator and output control).


_Figure 147_ to _Figure 174_ give an overview of one Capture/Compare channel.


The input stage samples the corresponding TIx input to generate a filtered signal TIxF.
Then, an edge detector with polarity selection generates a signal (TIxFPx) which can be
used as trigger input by the slave mode controller or as the capture command. It is
prescaled before the capture register (ICxPS).


**Figure 171. Capture/compare channel (example: channel 1 input stage)**

















































The output stage generates an intermediate waveform which is then used for reference:
OCxRef (active high). The polarity acts at the end of the chain.


400/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**Figure 172. Capture/compare channel 1 main circuit**



































**Figure 173. Output stage of capture/compare channel (channel 1)**




















|Col1|Dead-time<br>generator|OC1_DT|
|---|---|---|
||Dead-time<br>generator|OC1N_DT|














|Col1|CC1NE|Col3|CC1E|
|---|---|---|---|
|MOE|MOE|OSSI<br><br>|OSSR|













**Figure 174. Output stage of capture/compare channel (channel 2 for TIM15)**















RM0041 Rev 6 401/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


The capture/compare block is made of one preload register and one shadow register. Write
and read always access the preload register.


In capture mode, captures are actually done in the shadow register, which is copied into the
preload register.


In compare mode, the content of the preload register is copied into the shadow register
which is compared to the counter.


**15.4.6** **Input capture mode**


In Input capture mode, the Capture/Compare Registers (TIMx_CCRx) are used to latch the
value of the counter after a transition detected by the corresponding ICx signal. When a
capture occurs, the corresponding CCXIF flag (TIMx_SR register) is set and an interrupt or
a DMA request can be sent if they are enabled. If a capture occurs while the CCxIF flag was
already high, then the over-capture flag CCxOF (TIMx_SR register) is set. CCxIF can be
cleared by software by writing it to ‘0’ or by reading the captured data stored in the
TIMx_CCRx register. CCxOF is cleared when written it to ‘0’.


The following example shows how to capture the counter value in TIMx_CCR1 when TI1
input rises. To do this, use the following procedure:


      - Select the active input: TIMx_CCR1 must be linked to the TI1 input, so write the CC1S
bits to 01 in the TIMx_CCMR1 register. As soon as CC1S becomes different from 00,
the channel is configured in input and the TIMx_CCR1 register becomes read-only.


      - Program the needed input filter duration with respect to the signal connected to the
timer (when the input is one of the TIx (ICxF bits in the TIMx_CCMRx register). Let’s
imagine that, when toggling, the input signal is not stable during at must five internal
clock cycles. We must program a filter duration longer than these five clock cycles. We
can validate a transition on TI1 when 8 consecutive samples with the new level have
been detected (sampled at f DTS frequency). Then write IC1F bits to 0011 in the
TIMx_CCMR1 register.


      - Select the edge of the active transition on the TI1 channel by writing CC1P bit to 0 in
the TIMx_CCER register (rising edge in this case).


      - Program the input prescaler. In our example, we wish the capture to be performed at
each valid transition, so the prescaler is disabled (write IC1PS bits to ‘00’ in the
TIMx_CCMR1 register).


      - Enable capture from the counter into the capture register by setting the CC1E bit in the
TIMx_CCER register.


      - If needed, enable the related interrupt request by setting the CC1IE bit in the
TIMx_DIER register, and/or the DMA request by setting the CC1DE bit in the
TIMx_DIER register.


When an input capture occurs:


      - The TIMx_CCR1 register gets the value of the counter on the active transition.


      - CC1IF flag is set (interrupt flag). CC1OF is also set if at least two consecutive captures
occurred whereas the flag was not cleared.


      - An interrupt is generated depending on the CC1IE bit.


      - A DMA request is generated depending on the CC1DE bit.


In order to handle the overcapture, it is recommended to read the data before the
overcapture flag. This is to avoid missing an overcapture which could happen after reading
the flag and before reading the data.


402/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


_Note:_ _IC interrupt and/or DMA requests can be generated by software by setting the_
_corresponding CCxG bit in the TIMx_EGR register._


**15.4.7** **PWM input mode (only for TIM15)**


This mode is a particular case of input capture mode. The procedure is the same except:


      - Two ICx signals are mapped on the same TIx input.


      - These 2 ICx signals are active on edges with opposite polarity.


      - One of the two TIxFP signals is selected as trigger input and the slave mode controller
is configured in reset mode.


For example, user can measure the period (in TIMx_CCR1 register) and the duty cycle (in
TIMx_CCR2 register) of the PWM applied on TI1 using the following procedure (depending
on CK_INT frequency and prescaler value):


      - Select the active input for TIMx_CCR1: write the CC1S bits to 01 in the TIMx_CCMR1
register (TI1 selected).


      - Select the active polarity for TI1FP1 (used both for capture in TIMx_CCR1 and counter
clear): write the CC1P bit to ‘0’ (active on rising edge).


      - Select the active input for TIMx_CCR2: write the CC2S bits to 10 in the TIMx_CCMR1
register (TI1 selected).


      - Select the active polarity for TI1FP2 (used for capture in TIMx_CCR2): write the CC2P
bit to ‘1’ (active on falling edge).


      - Select the valid trigger input: write the TS bits to 101 in the TIMx_SMCR register
(TI1FP1 selected).


      - Configure the slave mode controller in reset mode: write the SMS bits to 100 in the
TIMx_SMCR register.


      - Enable the captures: write the CC1E and CC2E bits to ‘1’ in the TIMx_CCER register.


**Figure 175. PWM input mode timing**











1. The PWM input mode can be used only with the TIMx_CH1/TIMx_CH2 signals due to the fact that only
TI1FP1 and TI2FP2 are connected to the slave mode controller.


RM0041 Rev 6 403/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**15.4.8** **Forced output mode**


In output mode (CCxS bits = 00 in the TIMx_CCMRx register), each output compare signal
(OCxREF and then OCx/OCxN) can be forced to active or inactive level directly by software,
independently of any comparison between the output compare register and the counter.


To force an output compare signal (OCXREF/OCx) to its active level, user just needs to
write 101 in the OCxM bits in the corresponding TIMx_CCMRx register. Thus OCXREF is
forced high (OCxREF is always active high) and OCx get opposite value to CCxP polarity
bit.


For example: CCxP=0 (OCx active high) => OCx is forced to high level.


The OCxREF signal can be forced low by writing the OCxM bits to 100 in the TIMx_CCMRx
register.


Anyway, the comparison between the TIMx_CCRx shadow register and the counter is still
performed and allows the flag to be set. Interrupt and DMA requests can be sent
accordingly. This is described in the output compare mode section below.


**15.4.9** **Output compare mode**


This function is used to control an output waveform or indicating when a period of time has
elapsed.


When a match is found between the capture/compare register and the counter, the output
compare function:


      - Assigns the corresponding output pin to a programmable value defined by the output
compare mode (OCxM bits in the TIMx_CCMRx register) and the output polarity (CCxP
bit in the TIMx_CCER register). The output pin can keep its level (OCXM=000), be set
active (OCxM=001), be set inactive (OCxM=010) or can toggle (OCxM=011) on match.


      - Sets a flag in the interrupt status register (CCxIF bit in the TIMx_SR register).


      - Generates an interrupt if the corresponding interrupt mask is set (CCXIE bit in the
TIMx_DIER register).


      - Sends a DMA request if the corresponding enable bit is set (CCxDE bit in the
TIMx_DIER register, CCDS bit in the TIMx_CR2 register for the DMA request
selection).


The TIMx_CCRx registers can be programmed with or without preload registers using the
OCxPE bit in the TIMx_CCMRx register.


In output compare mode, the update event UEV has no effect on OCxREF and OCx output.
The timing resolution is one count of the counter. Output compare mode can also be used to
output a single pulse (in One-pulse mode).


Procedure:


404/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


1. Select the counter clock (internal, external, prescaler).


2. Write the desired data in the TIMx_ARR and TIMx_CCRx registers.


3. Set the CCxIE bit if an interrupt request is to be generated.


4. Select the output mode. For example:


–
Write OCxM = 011 to toggle OCx output pin when CNT matches CCRx


–
Write OCxPE = 0 to disable preload register


–
Write CCxP = 0 to select active high polarity


–
Write CCxE = 1 to enable the output


5. Enable the counter by setting the CEN bit in the TIMx_CR1 register.


The TIMx_CCRx register can be updated at any time by software to control the output
waveform, provided that the preload register is not enabled (OCxPE=’0’, else TIMx_CCRx
shadow register is updated only at the next update event UEV). An example is given in
_Figure 151_ .


**Figure 176. Output compare mode, toggle on OC1.**









**15.4.10** **PWM mode**







Pulse Width Modulation mode allows the user to generate a signal with a frequency
determined by the value of the TIMx_ARR register and a duty cycle determined by the value
of the TIMx_CCRx register.


The PWM mode can be selected independently on each channel (one PWM per OCx
output) by writing ‘110’ (PWM mode 1) or ‘111’ (PWM mode 2) in the OCxM bits in the
TIMx_CCMRx register. Enable the corresponding preload register by setting the OCxPE bit
in the TIMx_CCMRx register, and eventually the auto-reload preload register by setting the
ARPE bit in the TIMx_CR1 register.


As the preload registers are transferred to the shadow registers only when an update event
occurs, before starting the counter, initialize all the registers by setting the UG bit in the
TIMx_EGR register.


RM0041 Rev 6 405/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


OCx polarity is software programmable using the CCxP bit in the TIMx_CCER register. It
can be programmed as active high or active low. OCx output is enabled by a combination of
the CCxE, CCxNE, MOE, OSSI and OSSR bits (TIMx_CCER and TIMx_BDTR registers).
Refer to the TIMx_CCER register description for more details.


In PWM mode (1 or 2), TIMx_CNT and TIMx_CCRx are always compared to determine
whether TIMx_CCRx ≤TIMx_CNT or TIMx_CNT ≤TIMx_CCRx (depending on the direction
of the counter).


The timer is able to generate PWM in edge-aligned mode or center-aligned mode
depending on the CMS bits in the TIMx_CR1 register.


**PWM edge-aligned mode**


      - Upcounting configuration


Upcounting is active when the DIR bit in the TIMx_CR1 register is low. Refer to the
_Upcounting mode on page 347_ .


In the following example, we consider PWM mode 1. The reference PWM signal
OCxREF is high as long as TIMx_CNT < TIMx_CCRx else it becomes low. If the
compare value in TIMx_CCRx is greater than the auto-reload value (in TIMx_ARR)
then OCxREF is held at ‘1’. If the compare value is 0 then OCxRef is held at ‘0’.
_Figure 152_ shows some edge-aligned PWM waveforms in an example where
TIMx_ARR=8.


**Figure 177. Edge-aligned PWM waveforms (ARR=8)**






|0|1|2|3|4|5|6|7|8|0|1|
|---|---|---|---|---|---|---|---|---|---|---|
|0|1|2|3||||||||
|0|1|2|3||||||||
|0|1|2|3||||||||
|0|1|2|3||||||||










      - Downcounting configuration


Downcounting is active when DIR bit in TIMx_CR1 register is high. Refer to the
_Repetition counter on page 397_


In PWM mode 1, the reference signal OCxRef is low as long as
TIMx_CNT > TIMx_CCRx else it becomes high. If the compare value in TIMx_CCRx is
greater than the auto-reload value in TIMx_ARR, then OCxREF is held at ‘1’. 0% PWM
is not possible in this mode.


406/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**15.4.11** **Complementary outputs and dead-time insertion**


The TIM15/16/17 general-purpose timers can output one complementary signal and
manage the switching-off and switching-on of the outputs.


This time is generally known as dead-time and must be adjusted depending on the devices
connected to the outputs and their characteristics (intrinsic delays of level-shifters, delays
due to power switches...)


The polarity of the outputs (main output OCx or complementary OCxN) can be selected
independently for each output. This is done by writing to the CCxP and CCxNP bits in the
TIMx_CCER register.


The complementary signals OCx and OCxN are activated by a combination of several
control bits: the CCxE and CCxNE bits in the TIMx_CCER register and the MOE, OISx,
OISxN, OSSI and OSSR bits in the TIMx_BDTR and TIMx_CR2 registers. Refer to _Table 80_
_on page 428_ for more details. In particular, the dead-time is activated when switching to the
IDLE state (MOE falling down to 0).


Dead-time insertion is enabled by setting both CCxE and CCxNE bits, and the MOE bit if the
break circuit is present. There is one 8-bit field named DTG[7:0] in the TIMx_BDTR register
used to control the dead-time generation for all channels. From a reference waveform
OCxREF, it generates 2 outputs OCx and OCxN. If OCx and OCxN are active high:


      - the OCx output signal is the same as the reference signal except for the rising edge,
which is delayed relative to the reference rising edge


      - the OCxN output signal is the opposite of the reference signal except for the rising
edge, which is delayed relative to the reference falling edge.


If the delay is greater than the width of the active output (OCx or OCxN) then the
corresponding pulse is not generated.


The following figures show the relationships between the output signals of the dead-time
generator and the reference signal OCxREF. (we suppose CCxP=0, CCxNP=0, MOE=1,
CCxE=1 and CCxNE=1 in these examples).


**Figure 178. Complementary output with dead-time insertion.**


**Figure 179. Dead-time waveforms with delay** **greater than the negative pulse.**


RM0041 Rev 6 407/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**Figure 180. Dead-time waveforms with delay** **greater than the positive pulse.**


The dead-time delay is the same for each of the channels and is programmable with the
DTG bits in the TIMx_BDTR register. Refer to _Section 15.5.15: TIM15 break and dead-time_
_register (TIM15_BDTR) on page 431_ for delay calculation.


**Re-directing OCxREF to OCx or OCxN**


In output mode (forced, output compare or PWM), OCxREF can be re-directed to the OCx
output or to OCxN output by configuring the CCxE and CCxNE bits in the TIMx_CCER
register.


This allows the user to send a specific waveform (such as PWM or static active level) on
one output while the complementary remains at its inactive level. Other alternative
possibilities are to have both outputs at inactive level or both outputs active and
complementary with dead-time.


_Note:_ _When only OCxN is enabled (CCxE=0, CCxNE=1), it is not complemented and becomes_
_active as soon as OCxREF is high. For example, if CCxNP=0 then OCxN=OCxRef. On the_
_other hand, when both OCx and OCxN are enabled (CCxE=CCxNE=1) OCx becomes_
_active when OCxREF is high whereas OCxN is complemented and becomes active when_
_OCxREF is low._


**15.4.12** **Using the break function**


When using the break function, the output enable signals and inactive levels are modified
according to additional control bits (MOE, OSSI and OSSR bits in the TIMx_BDTR register,
OISx and OISxN bits in the TIMx_CR2 register). In any case, the OCx and OCxN outputs
cannot be set both to active level at a given time. Refer to _Table 80: Output control bits for_
_complementary OCx and OCxN channels with break feature on page 428_ for more details.


The break source can be either the break input pin or a clock failure event, generated by the
Clock Security System (CSS), from the Reset Clock Controller. For further information on
the Clock Security System, refer to _Section 6.2.7: Clock security system (CSS)_ .


When exiting from reset, the break circuit is disabled and the MOE bit is low. Enable the
break function by setting the BKE bit in the TIMx_BDTR register. The break input polarity
can be selected by configuring the BKP bit in the same register. BKE and BKP can be
modified at the same time. When the BKE and BKP bits are written, a delay of 1 APB clock
cycle is applied before the writing is effective. Consequently, it is necessary to wait one APB
clock period to correctly read back the bit after the write operation.


Because MOE falling edge can be asynchronous, a resynchronization circuit has been
inserted between the actual signal (acting on the outputs) and the synchronous control bit
(accessed in the TIMx_BDTR register). It results in some delays between the asynchronous
and the synchronous signals. In particular, if user writes MOE to 1 whereas it was low, a


408/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


delay (dummy instruction) must be inserted before reading it correctly. This is because user
writes the asynchronous signal and reads the synchronous signal.


When a break occurs (selected level on the break input):


      - The MOE bit is cleared asynchronously, putting the outputs in inactive state, idle state
or in reset state (selected by the OSSI bit). This feature functions even if the MCU
oscillator is off.


      - Each output channel is driven with the level programmed in the OISx bit in the
TIMx_CR2 register as soon as MOE=0. If OSSI=0 then the timer releases the enable
output else the enable output remains high.


      - When complementary outputs are used:


–
The outputs are first put in reset state inactive state (depending on the polarity).
This is done asynchronously so that it works even if no clock is provided to the
timer.


–
If the timer clock is still present, then the dead-time generator is reactivated in
order to drive the outputs with the level programmed in the OISx and OISxN bits
after a dead-time. Even in this case, OCx and OCxN cannot be driven to their
active level together. Note that because of the resynchronization on MOE, the
dead-time duration is a bit longer than usual (around 2 ck_tim clock cycles).


–
If OSSI=0 then the timer releases the enable outputs else the enable outputs
remain or become high as soon as one of the CCxE or CCxNE bits is high.


      - The break status flag (BIF bit in the TIMx_SR register) is set. An interrupt can be
generated if the BIE bit in the TIMx_DIER register is set. A DMA request can be sent if
the BDE bit in the TIMx_DIER register is set.


      - If the AOE bit in the TIMx_BDTR register is set, the MOE bit is automatically set again
at the next update event UEV. This can be used to perform a regulation, for instance.
Else, MOE remains low until user writes it to ‘1’ again. In this case, it can be used for
security and user can connect the break input to an alarm from power drivers, thermal
sensors or any security components.


_Note:_ _The break inputs is acting on level. Thus, the MOE cannot be set while the break input is_
_active (neither automatically nor by software). In the meantime, the status flag BIF cannot_
_be cleared._


The break can be generated by the BRK input which has a programmable polarity and an
enable bit BKE in the TIMx_BDTR Register.


In addition to the break input and the output management, a write protection has been
implemented inside the break circuit to safeguard the application. It allows the user to freeze
the configuration of several parameters (dead-time duration, OCx/OCxN polarities and state
when disabled, OCxM configurations, break enable and polarity). User can choose from
three levels of protection selected by the LOCK bits in the TIMx_BDTR register. Refer to
_Section 15.5.15: TIM15 break and dead-time register (TIM15_BDTR) on page 431_ . The
LOCK bits can be written only once after an MCU reset.


The _Figure 181_ shows an example of behavior of the outputs in response to a break.


RM0041 Rev 6 409/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**Figure 181. Output behavior in response to a break.**











|Col1|Col2|Col3|Col4|Col5|
|---|---|---|---|---|
||||||
||||||
|OISx=|1)|1)|1)|1)|
|OISx=|1)||||
|OISx=|0)|0)|0)||
|OISx=|1)|1)|1)||
|OISx=|1)||||
|OISx=|0)|0)|0)|0)|
|OISx=|0)||||
|OISx=|0)||||
|delay||delay|delay|delay|
|delay|CxNP=|CxNP=|CxNP=|CxNP=|
|=1, C|=1, C|0, OI|SxN=1)||
|=1, C|=1, C|0, OI|||
||||||
|=1, C<br>~~delay~~|=1, C<br>~~delay~~|1, OI<br>~~delay~~|SxN=1)<br>|~~delay~~|
|=1, C<br>~~delay~~|CxNP=|CxNP=|CxNP=|CxNP=|
|=1, C<br>~~delay~~|CxNP=||||
|||||delay|
|=0, C|CxNP=|0, OI|SxN=1)||
|=0, C|CxNP=||||
|||||delay|
|=0, C|CxNP=|0, OI|SxN=0)||
|=0, C|CxNP=||||
||||||


410/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**15.4.13** **One-pulse mode**


One-pulse mode (OPM) is a particular case of the previous modes. It allows the counter to
be started in response to a stimulus and to generate a pulse with a programmable length
after a programmable delay.


Starting the counter can be controlled through the slave mode controller. Generating the
waveform can be done in output compare mode or PWM mode. Select One-pulse mode by
setting the OPM bit in the TIMx_CR1 register. This makes the counter stop automatically at
the next update event UEV.


A pulse can be correctly generated only if the compare value is different from the counter
initial value. Before starting (when the timer is waiting for the trigger), the configuration must
be:


      - In upcounting: CNT < CCRx ≤ ARR (in particular, 0 < CCRx)


      - In downcounting: CNT > CCRx


**Figure 182. Example of one pulse mode.**


|Col1|Col2|Col3|
|---|---|---|
||||
||||
||||
||||







For example user may want to generate a positive pulse on OC1 with a length of t PULSE and
after a delay of t DELAY as soon as a positive edge is detected on the TI2 input pin.


Let’s use TI2FP2 as trigger 1:


- Map TI2FP2 to TI2 by writing CC2S=’01’ in the TIMx_CCMR1 register.


- TI2FP2 must detect a rising edge, write CC2P=’0’ in the TIMx_CCER register.


- Configure TI2FP2 as trigger for the slave mode controller (TRGI) by writing TS=’110’ in
the TIMx_SMCR register.


- TI2FP2 is used to start the counter by writing SMS to ‘110’ in the TIMx_SMCR register
(trigger mode).


RM0041 Rev 6 411/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


The OPM waveform is defined by writing the compare registers (taking into account the
clock frequency and the counter prescaler).


      - The t DELAY is defined by the value written in the TIMx_CCR1 register.


      - The t PULSE is defined by the difference between the auto-reload value and the compare
value (TIMx_ARR - TIMx_CCR1).


      - Let’s say user wants to build a waveform with a transition from ‘0’ to ‘1’ when a
compare match occurs and a transition from ‘1’ to ‘0’ when the counter reaches the
auto-reload value. To do this enable PWM mode 2 by writing OC1M=111 in the
TIMx_CCMR1 register. User can optionally enable the preload registers by writing
OC1PE=’1’ in the TIMx_CCMR1 register and ARPE in the TIMx_CR1 register. In this
case user has to write the compare value in the TIMx_CCR1 register, the auto-reload
value in the TIMx_ARR register, generate an update by setting the UG bit and wait for
external trigger event on TI2. CC1P is written to ‘0’ in this example.


In our example, the DIR and CMS bits in the TIMx_CR1 register should be low.


User only wants one pulse, so write ‘1’ in the OPM bit in the TIMx_CR1 register to stop the
counter at the next update event (when the counter rolls over from the auto-reload value
back to 0).


Particular case: OCx fast enable


In One-pulse mode, the edge detection on TIx input set the CEN bit which enables the
counter. Then the comparison between the counter and the compare value makes the
output toggle. But several clock cycles are needed for these operations and it limits the
minimum delay t DELAY min we can get.


If user wants to output a waveform with the minimum delay, set the OCxFE bit in the
TIMx_CCMRx register. Then OCxRef (and OCx) are forced in response to the stimulus,
without taking in account the comparison. Its new level is the same as if a compare match
had occurred. OCxFE acts only if the channel is configured in PWM1 or PWM2 mode.


412/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**15.4.14** **TIM15 and external trigger synchronization (only for TIM15)**


The TIM15 timer can be synchronized with an external trigger in several modes: Reset
mode, Gated mode and Trigger mode.


**Slave mode: Reset mode**


The counter and its prescaler can be reinitialized in response to an event on a trigger input.
Moreover, if the URS bit from the TIMx_CR1 register is low, an update event UEV is
generated. Then all the preloaded registers (TIMx_ARR, TIMx_CCRx) are updated.


In the following example, the upcounter is cleared in response to a rising edge on TI1 input:


      - Configure the channel 1 to detect rising edges on TI1. Configure the input filter duration
(in this example, we don’t need any filter, so we keep IC1F=0000). The capture
prescaler is not used for triggering, so no need to configure it. The CC1S bits select the
input capture source only, CC1S = 01 in the TIMx_CCMR1 register. Write CC1P=0 in
TIMx_CCER register to validate the polarity (and detect rising edges only).


      - Configure the timer in reset mode by writing SMS=100 in TIMx_SMCR register. Select
TI1 as the input source by writing TS=101 in TIMx_SMCR register.


      - Start the counter by writing CEN=1 in the TIMx_CR1 register.


The counter starts counting on the internal clock, then behaves normally until TI1 rising
edge. When TI1 rises, the counter is cleared and restarts from 0. In the meantime, the
trigger flag is set (TIF bit in the TIMx_SR register) and an interrupt request, or a DMA
request can be sent if enabled (depending on the TIE and TDE bits in TIMx_DIER register).


The following figure shows this behavior when the auto-reload register TIMx_ARR=0x36.
The delay between the rising edge on TI1 and the actual reset of the counter is due to the
resynchronization circuit on TI1 input.


**Figure 183. Control circuit in reset mode**









RM0041 Rev 6 413/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**Slave mode: Gated mode**


The counter can be enabled depending on the level of a selected input.


In the following example, the upcounter counts only when TI1 input is low:


      - Configure the channel 1 to detect low levels on TI1. Configure the input filter duration
(in this example, we don’t need any filter, so we keep IC1F=0000). The capture
prescaler is not used for triggering, so no need to configure it. The CC1S bits select the
input capture source only, CC1S=01 in TIMx_CCMR1 register. Write CC1P=1 in
TIMx_CCER register to validate the polarity (and detect low level only).


      - Configure the timer in gated mode by writing SMS=101 in TIMx_SMCR register. Select
TI1 as the input source by writing TS=101 in TIMx_SMCR register.


      - Enable the counter by writing CEN=1 in the TIMx_CR1 register (in gated mode, the
counter doesn’t start if CEN=0, whatever is the trigger input level).


The counter starts counting on the internal clock as long as TI1 is low and stops as soon as
TI1 becomes high. The TIF flag in the TIMx_SR register is set both when the counter starts
or stops.


The delay between the rising edge on TI1 and the actual stop of the counter is due to the
resynchronization circuit on TI1 input.


**Figure 184. Control circuit in gated mode**


414/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**Slave mode: Trigger mode**


The counter can start in response to an event on a selected input.


In the following example, the upcounter starts in response to a rising edge on TI2 input:


      - Configure the channel 2 to detect rising edges on TI2. Configure the input filter duration
(in this example, we don’t need any filter, so we keep IC2F=0000). The capture
prescaler is not used for triggering, so no need to configure it. The CC2S bits are
configured to select the input capture source only, CC2S=01 in TIMx_CCMR1 register.
Write CC2P=1 in TIMx_CCER register to validate the polarity (and detect low level
only).


      - Configure the timer in trigger mode by writing SMS=110 in TIMx_SMCR register. Select
TI2 as the input source by writing TS=110 in TIMx_SMCR register.


When a rising edge occurs on TI2, the counter starts counting on the internal clock and the
TIF flag is set.


The delay between the rising edge on TI2 and the actual start of the counter is due to the
resynchronization circuit on TI2 input.


**Figure 185. Control circuit in trigger mode**


**15.4.15** **Timer synchronization**


The TIM timers are linked together internally for timer synchronization or chaining. Refer to
_Section 13.3.15: Timer synchronization on page 316_ for details.


_Note:_ _The clock of the slave timer must be enabled prior to receiving events from the master timer,_
_and must not be changed on-the-fly while triggers are received from the master timer._


**15.4.16** **Debug mode**


When the microcontroller enters debug mode (Cortex [®] -M3 core halted), the TIMx counter
either continues to work normally or stops, depending on DBG_TIMx_STOP configuration
bit in DBG module. For more details, refer to _Section 25.15.2: Debug support for timers,_
_watchdog and I_ _[2]_ _C_ .

## **15.5 TIM15 registers**


Refer to _Section 1.1: List of abbreviations for registers_ for a list of abbreviations used in
register descriptions.


The peripheral registers have to be written by half-words (16 bits) or words (32 bits). Read
accesses can be done by bytes (8 bits), half-words (16 bits) or words (32 bits).


RM0041 Rev 6 415/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**15.5.1** **TIM15 control register 1 (TIM15_CR1)**


Address offset: 0x00


Reset value: 0x0000

|15 14 13 12 11 10|9 8|Col3|7|6 5 4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|
|Reserved|CKD[1:0]|CKD[1:0]|ARPE|Reserved|OPM|URS|UDIS|CEN|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:10 Reserved, must be kept at reset value.


Bits 9:8 **CKD[1:0]** : Clock division

This bitfield indicates the division ratio between the timer clock (CK_INT) frequency and the
dead-time and sampling clock (t DTS ) used by the dead-time generators and the digital filters
(TIx)
00: t DTS = t CK_INT
01: t DTS = 2*t CK_INT
10: t DTS = 4*t CK_INT
11: Reserved, do not program this value


Bit 7 **ARPE** : Auto-reload preload enable

0: TIMx_ARR register is not buffered
1: TIMx_ARR register is buffered


Bits 6:4 Reserved, must be kept at reset value.


Bit 3 **OPM** : One-pulse mode

0: Counter is not stopped at update event
1: Counter stops counting at the next update event (clearing the bit CEN)


Bit 2 **URS** : Update request source

This bit is set and cleared by software to select the UEV event sources.
0: Any of the following events generate an update interrupt if enabled. These events can be:

– Counter overflow/underflow

–
Setting the UG bit

–
Update generation through the slave mode controller
1: Only counter overflow/underflow generates an update interrupt if enabled


Bit 1 **UDIS** : Update disable

This bit is set and cleared by software to enable/disable UEV event generation.
0: UEV enabled. The Update (UEV) event is generated by one of the following events:

– Counter overflow/underflow

–
Setting the UG bit

–
Update generation through the slave mode controller
Buffered registers are then loaded with their preload values.
1: UEV disabled. The Update event is not generated, shadow registers keep their value
(ARR, PSC, CCRx). However the counter and the prescaler are reinitialized if the UG bit is
set or if a hardware reset is received from the slave mode controller.


Bit 0 **CEN** : Counter enable

0: Counter disabled

1: Counter enabled

_Note: External clock and gated mode can work only if the CEN bit has been previously set by_
_software. However trigger mode can set the CEN bit automatically by hardware._


416/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**15.5.2** **TIM15 control register 2 (TIM15_CR2)**


Address offset: 0x04


Reset value: 0x0000

|15 14 13 12 11|10|9|8|7|6 5 4|Col7|Col8|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|OIS2|OIS1N|OIS1|Res.|MMS[2:0]|MMS[2:0]|MMS[2:0]|CCDS|CCUS|Res.|CCPC|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 15:11 Reserved, must be kept at reset value.


Bit 10 **OIS2:** Output idle state 2 (OC2 output)

0: OC2=0 when MOE=0

1: OC2=1 when MOE=0

_Note: This bit cannot be modified as long as LOCK level 1, 2 or 3 has been programmed_
_(LOCK bits in the TIMx_BKR register)._


Bit 9 **OIS1N** : Output Idle state 1 (OC1N output)

0: OC1N=0 after a dead-time when MOE=0

1: OC1N=1 after a dead-time when MOE=0

_Note: This bit can not be modified as long as LOCK level 1, 2 or 3 has been programmed_
_(LOCK bits in TIMx_BKR register)._


Bit 8 **OIS1** : Output Idle state 1 (OC1 output)

0: OC1=0 (after a dead-time if OC1N is implemented) when MOE=0
1: OC1=1 (after a dead-time if OC1N is implemented) when MOE=0

_Note: This bit can not be modified as long as LOCK level 1, 2 or 3 has been programmed_
_(LOCK bits in TIMx_BKR register)._


Bit 7 Reserved, must be kept at reset value.


Bits 6:4 **MMS[1:0]** : Master mode selection

These bits allow to select the information to be sent in master mode to slave timers for

synchronization (TRGO). The combination is as follows:
000: **Reset**             - the UG bit from the TIMx_EGR register is used as trigger output (TRGO). If the
reset is generated by the trigger input (slave mode controller configured in reset mode) then
the signal on TRGO is delayed compared to the actual reset.
001: **Enable**             - the Counter Enable signal CNT_EN is used as trigger output (TRGO). It is
useful to start several timers at the same time or to control a window in which a slave timer is

enable. The Counter Enable signal is generated by a logic OR between CEN control bit and
the trigger input when configured in gated mode. When the Counter Enable signal is
controlled by the trigger input, there is a delay on TRGO, except if the master/slave mode is
selected (see the MSM bit description in TIMx_SMCR register).
010: **Update**             - The update event is selected as trigger output (TRGO). For instance a master
timer can then be used as a prescaler for a slave timer.
011: **Compare Pulse**             - The trigger output send a positive pulse when the CC1IF flag is to be
set (even if it was already high), as soon as a capture or a compare match occurred.
(TRGO).
100: **Compare**             - OC1REF signal is used as trigger output (TRGO).
101: **Compare**             - OC2REF signal is used as trigger output (TRGO).


Bit 3 **CCDS** : Capture/compare DMA selection

0: CCx DMA request sent when CCx event occurs
1: CCx DMA requests sent when update event occurs


RM0041 Rev 6 417/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


Bit 2 **CCUS** : Capture/compare control update selection

0: When capture/compare control bits are preloaded (CCPC=1), they are updated by setting
the COMG bit only.
1: When capture/compare control bits are preloaded (CCPC=1), they are updated by setting
the COMG bit or when an rising edge occurs on TRGI.

_Note: This bit acts only on channels that have a complementary output._


Bit 1 Reserved, must be kept at reset value.


Bit 0 **CCPC** : Capture/compare preloaded control

0: CCxE, CCxNE and OCxM bits are not preloaded
1: CCxE, CCxNE and OCxM bits are preloaded, after having been written, they are updated
only when COM bit is set.

_Note: This bit acts only on channels that have a complementary output._


**15.5.3** **TIM15 slave mode control register (TIM15_SMCR)**


Address offset: 0x08


Reset value: 0x0000

|15 14 13 12 11 10 9 8|7|6 5 4|Col4|Col5|3|2 1 0|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|MSM|TS[2:0]|TS[2:0]|TS[2:0]|Res.|SMS[2:0]|SMS[2:0]|SMS[2:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:8 Reserved, must be kept at reset value.


Bit 7 **MSM:** Master/slave mode

0: No action

1: The effect of an event on the trigger input (TRGI) is delayed to allow a perfect
synchronization between the current timer and its slaves (through TRGO). It is useful if we
want to synchronize several timers on a single external event.


418/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


Bits 6:4 **TS[2:0]:** Trigger selection

This bitfield selects the trigger input to be used to synchronize the counter.
000: Internal Trigger 0 (ITR0)
001: Internal Trigger 1 (ITR1)
010: Internal Trigger 2 (ITR2)
011: Internal Trigger 3 (ITR3)
100: TI1 Edge Detector (TI1F_ED)
101: Filtered Timer Input 1 (TI1FP1)
110: Filtered Timer Input 2 (TI2FP2)
See _Table 79: TIMx Internal trigger connection on page 419_ for more details on ITRx
meaning for each Timer.

_Note: These bits must be changed only when they are not used (e.g. when SMS=000) to_
_avoid wrong edge detections at the transition._


Bit 3 Reserved, must be kept at reset value.


Bits 2:0 **SMS:** Slave mode selection

When external signals are selected the active edge of the trigger signal (TRGI) is linked to
the polarity selected on the external input (see Input Control register and Control Register
description.
000: Slave mode disabled - if CEN = ‘1’ then the prescaler is clocked directly by the internal
clock.

001: Encoder mode 1 - Counter counts up/down on TI2FP1 edge depending on TI1FP2
level.

010: Encoder mode 2 - Counter counts up/down on TI1FP2 edge depending on TI2FP1
level.

011: Encoder mode 3 - Counter counts up/down on both TI1FP1 and TI2FP2 edges
depending on the level of the other input.
100: Reset mode - Rising edge of the selected trigger input (TRGI) reinitializes the counter
and generates an update of the registers.
101: Gated mode - The counter clock is enabled when the trigger input (TRGI) is high. The
counter stops (but is not reset) as soon as the trigger becomes low. Both start and stop of
the counter are controlled.

110: Trigger mode - The counter starts at a rising edge of the trigger TRGI (but it is not
reset). Only the start of the counter is controlled.
111: External Clock mode 1 - Rising edges of the selected trigger (TRGI) clock the counter.

_Note: The gated mode must not be used if TI1F_ED is selected as the trigger input_
_(TS=’100’). Indeed, TI1F_ED outputs 1 pulse for each transition on TI1F, whereas the_
_gated mode checks the level of the trigger signal._


**Table 79. TIMx Internal trigger connection**







|Slave TIM|ITR0 (TS = 000)(1)|ITR1 (TS = 001)(1)|ITR2 (TS = 010)|ITR3 (TS = 011)|
|---|---|---|---|---|
|TIM15|TIM2|TIM3|TIM16_OC|TIM17_OC|


1. ITR0 and ITR1 triggers available only in high density value line devices.


RM0041 Rev 6 419/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**15.5.4** **TIM15 DMA/interrupt enable register (TIM15_DIER)**


Address offset: 0x0C


Reset value: 0x0000

|15|14|13 12 11|10|9|8|7|6|5|4 3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|TDE|Reserved|CC2DE|CC1DE|UDE|BIE|TIE|COMIE|Reserved|CC2IE|CC1IE|UIE|
|Res.|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 15 Reserved, must be kept at reset value.


Bit 14 **TDE** : Trigger DMA request enable

0: Trigger DMA request disabled
1: Trigger DMA request enabled


Bits 13:11 Reserved, must be kept at reset value.


Bit 10 **CC2DE** : Capture/Compare 2 DMA request enable

0: CC2 DMA request disabled
1: CC2 DMA request enabled


Bit 9 **CC1DE** : Capture/Compare 1 DMA request enable

0: CC1 DMA request disabled
1: CC1 DMA request enabled


Bit 8 **UDE** : Update DMA request enable

0: Update DMA request disabled
1: Update DMA request enabled


Bit 7 **BIE** : Break interrupt enable

0: Break interrupt disabled
1: Break interrupt enabled


Bit 6 **TIE** : Trigger interrupt enable

0: Trigger interrupt disabled
1: Trigger interrupt enabled


Bit 5 **COMIE:** COM interrupt enable

0: COM interrupt disabled
1: COM interrupt enabled


Bits 4:3 Reserved, must be kept at reset value.


Bit 2 **CC2IE** : Capture/Compare 2 interrupt enable

0: CC2 interrupt disabled
1: CC2 interrupt enabled


Bit 1 **CC1IE** : Capture/Compare 1 interrupt enable

0: CC1 interrupt disabled
1: CC1 interrupt enabled


Bit 0 **UIE** : Update interrupt enable

0: Update interrupt disabled
1: Update interrupt enabled


420/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**15.5.5** **TIM15 status register (TIM15_SR)**


Address offset: 0x10


Reset value: 0x0000

|15 14 13 12 11|10|9|8|7|6|5|4 3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|CC2OF|CC1OF|Res.|BIF|TIF|COMIF|Reserved|CC2IF|CC1IF|UIF|
|Reserved|rc_w0|rc_w0|rc_w0|rc_w0|rc_w0|||rc_w0|rc_w0|rc_w0|



Bits 15:11 Reserved, must be kept at reset value.


Bit 10 **CC2OF** : Capture/Compare 2 overcapture flag

refer to CC1OF description


Bit 9 **CC1OF** : Capture/Compare 1 overcapture flag

This flag is set by hardware only when the corresponding channel is configured in input
capture mode. It is cleared by software by writing it to ‘0’.
0: No overcapture has been detected
1: The counter value has been captured in TIMx_CCR1 register while CC1IF flag was
already set


Bit 8 Reserved, must be kept at reset value.


Bit 7 **BIF** : Break interrupt flag

This flag is set by hardware as soon as the break input goes active. It can be cleared by
software if the break input is not active.
0: No break event occurred

1: An active level has been detected on the break input


Bit 6 **TIF** : Trigger interrupt flag

This flag is set by hardware on trigger event (active edge detected on TRGI input when the
slave mode controller is enabled in all modes but gated mode, both edges in case gated
mode is selected). It is cleared by software.
0: No trigger event occurred
1: Trigger interrupt pending


Bit 5 **COMIF:** COM interrupt flag

This flag is set by hardware on a COM event (once the capture/compare control bits –CCxE,
CCxNE, OCxM– have been updated). It is cleared by software.

0: No COM event occurred

1: COM interrupt pending


Bits 5:3 Reserved, must be kept at reset value.


RM0041 Rev 6 421/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


Bit 2 **CC2IF** : Capture/Compare 2 interrupt flag

refer to CC1IF description


Bit 1 **CC1IF** : Capture/Compare 1 interrupt flag

**If channel CC1 is configured as output:**
This flag is set by hardware when the counter matches the compare value, with some
exception in center-aligned mode (refer to the CMS bits in the TIMx_CR1 register
description). It is cleared by software.
0: No match.

1: The content of the counter TIMx_CNT matches the content of the TIMx_CCR1 register.
When the contents of TIMx_CCR1 are greater than the contents of TIMx_ARR, the CC1IF
bit goes high on the counter overflow (in upcounting and up/down-counting modes) or
underflow (in downcounting mode)
**If channel CC1 is configured as input:**
This bit is set by hardware on a capture. It is cleared by software or by reading the
TIMx_CCR1 register.
0: No input capture occurred
1: The counter value has been captured in TIMx_CCR1 register (An edge has been
detected on IC1 which matches the selected polarity)


Bit 0 **UIF** : Update interrupt flag

This bit is set by hardware on an update event. It is cleared by software.
0: No update occurred.
1: Update interrupt pending. This bit is set by hardware when the registers are updated:

– At overflow regarding the repetition counter value (update if repetition counter = 0) and if the
UDIS=0 in the TIMx_CR1 register.

– When CNT is reinitialized by software using the UG bit in TIMx_EGR register, if URS=0 and
UDIS=0 in the TIMx_CR1 register.

– When CNT is reinitialized by a trigger event (refer to _Section 15.5.3: TIM15 slave mode_
_control register (TIM15_SMCR)_ ), if URS=0 and UDIS=0 in the TIMx_CR1 register.


**15.5.6** **TIM15 event generation register (TIM15_EGR)**


Address offset: 0x14


Reset value: 0x0000

|15 14 13 12 11 10 9 8|7|6|5|4 3|2|1|0|
|---|---|---|---|---|---|---|---|
|Reserved|BG|TG|COMG|Reserved|CC2G|CC1G|UG|
|Reserved|w|w|rw|rw|w|w|w|



Bits 15:8 Reserved, must be kept at reset value.


Bit 7 **BG** : Break generation

This bit is set by software in order to generate an event, it is automatically cleared by
hardware.

0: No action

1: A break event is generated. MOE bit is cleared and BIF flag is set. Related interrupt or
DMA transfer can occur if enabled.


Bit 6 **TG** : Trigger generation

This bit is set by software in order to generate an event, it is automatically cleared by
hardware.

0: No action

1: The TIF flag is set in TIMx_SR register. Related interrupt or DMA transfer can occur if
enabled


422/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


Bit 5 **COMG:** Capture/Compare control update generation

This bit can be set by software, it is automatically cleared by hardware.

0: No action

1: When the CCPC bit is set, it is possible to update the CCxE, CCxNE and OCxM bits

_Note: This bit acts only on channels that have a complementary output._


Bits 4:3 Reserved, must be kept at reset value.


Bit 2 **CC2G** : Capture/Compare 2 generation

refer to CC1G description


Bit 1 **CC1G** : Capture/Compare 1 generation

This bit is set by software in order to generate an event, it is automatically cleared by
hardware.

0: No action

1: A capture/compare event is generated on channel 1:
**If channel CC1 is configured as output:**
CC1IF flag is set, Corresponding interrupt or DMA request is sent if enabled.
**If channel CC1 is configured as input:**
The current value of the counter is captured in TIMx_CCR1 register. The CC1IF flag is set,
the corresponding interrupt or DMA request is sent if enabled. The CC1OF flag is set if the
CC1IF flag was already high.


Bit 0 **UG** : Update generation

This bit can be set by software, it is automatically cleared by hardware.
0: No action.

1: Reinitialize the counter and generates an update of the registers. Note that the prescaler
counter is cleared too (anyway the prescaler ratio is not affected). The counter is cleared if
the center-aligned mode is selected or if DIR=0 (upcounting), else it takes the auto-reload
value (TIMx_ARR) if DIR=1 (downcounting).


**15.5.7** **TIM15 capture/compare mode register 1 (TIM15_CCMR1)**


Address offset: 0x18


Reset value: 0x0000


The channels can be used in input (capture mode) or in output (compare mode). The
direction of a channel is defined by configuring the corresponding CCxS bits. All the other
bits of this register have a different function in input and in output mode. For a given bit,
OCxx describes its function when the channel is configured in output, ICxx describes its
function when the channel is configured in input. Take care that the same bit can have a
different meaning for the input stage and for the output stage.

|15|14 13 12|Col3|Col4|11|10|9 8|Col8|7|6 5 4|Col11|Col12|3|2|1 0|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res|OC2M[2:0]|OC2M[2:0]|OC2M[2:0]|OC2<br>PE|OC2<br>FE|CC2S[1:0]|CC2S[1:0]|Res|OC1M[2:0]|OC1M[2:0]|OC1M[2:0]|OC1<br>PE|OC1<br>FE|CC1S[1:0]|CC1S[1:0]|
|IC2F[3:0]|IC2F[3:0]|IC2F[3:0]|IC2F[3:0]|IC2PSC[1:0]|IC2PSC[1:0]|IC2PSC[1:0]|IC2PSC[1:0]|IC1F[3:0]|IC1F[3:0]|IC1F[3:0]|IC1F[3:0]|IC1PSC[1:0]|IC1PSC[1:0]|IC1PSC[1:0]|IC1PSC[1:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



RM0041 Rev 6 423/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**Output compare mode:**


Bit 15 Reserved, must be kept at reset value.


Bits 14:12 **OC2M[2:0]** : Output Compare 2 mode


Bit 11 **OC2PE** : Output Compare 2 preload enable


Bit 10 **OC2FE** : Output Compare 2 fast enable


Bits 9:8 **CC2S[1:0]** : Capture/Compare 2 selection

This bit-field defines the direction of the channel (input/output) as well as the used input.
00: CC2 channel is configured as output.
01: CC2 channel is configured as input, IC2 is mapped on TI2.
10: CC2 channel is configured as input, IC2 is mapped on TI1.
11: CC2 channel is configured as input, IC2 is mapped on TRC. This mode is working only if
an internal trigger input is selected through the TS bit (TIMx_SMCR register)

_Note: CC2S bits are writable only when the channel is OFF (CC2E = ‘0’ in TIMx_CCER)._


Bit 7 Reserved, must be kept at reset value.


Bits 6:4 **OC1M** : Output Compare 1 mode

These bits define the behavior of the output reference signal OC1REF from which OC1 and
OC1N are derived. OC1REF is active high whereas OC1 and OC1N active level depends
on CC1P and CC1NP bits.

000: Frozen - The comparison between the output compare register TIMx_CCR1 and the
counter TIMx_CNT has no effect on the outputs.
001: Set channel 1 to active level on match. OC1REF signal is forced high when the counter
TIMx_CNT matches the capture/compare register 1 (TIMx_CCR1).
010: Set channel 1 to inactive level on match. OC1REF signal is forced low when the
counter TIMx_CNT matches the capture/compare register 1 (TIMx_CCR1).
011: Toggle - OC1REF toggles when TIMx_CNT=TIMx_CCR1.
100: Force inactive level - OC1REF is forced low.

101: Force active level - OC1REF is forced high.
110: PWM mode 1 - In upcounting, channel 1 is active as long as TIMx_CNT<TIMx_CCR1
else inactive. In downcounting, channel 1 is inactive (OC1REF=‘0’) as long as
TIMx_CNT>TIMx_CCR1 else active (OC1REF=’1’).
111: PWM mode 2 - In upcounting, channel 1 is inactive as long as TIMx_CNT<TIMx_CCR1
else active. In downcounting, channel 1 is active as long as TIMx_CNT>TIMx_CCR1 else
inactive.

_Note:_ _**1:**_ _These bits can not be modified as long as LOCK level 3 has been programmed_
_(LOCK bits in TIMx_BDTR register) and CC1S=’00’ (the channel is configured in_
_output)._

_**2:**_ _In PWM mode 1 or 2, the OCREF level changes only when the result of the_
_comparison changes or when the output compare mode switches from “frozen” mode_
_to “PWM” mode._


424/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


Bit 3 **OC1PE** : Output Compare 1 preload enable

0: Preload register on TIMx_CCR1 disabled. TIMx_CCR1 can be written at anytime, the
new value is taken in account immediately.
1: Preload register on TIMx_CCR1 enabled. Read/Write operations access the preload
register. TIMx_CCR1 preload value is loaded in the active register at each update event.

_Note: These bits can not be modified as long as LOCK level 3 has been programmed (LOCK_
_bits in TIMx_BDTR register) and CC1S=’00’ (the channel is configured in output)._


Bit 2 **OC1FE** : Output Compare 1 fast enable

This bit is used to accelerate the effect of an event on the trigger in input on the CC output.
0: CC1 behaves normally depending on counter and CCR1 values even when the trigger is
ON. The minimum delay to activate CC1 output when an edge occurs on the trigger input is
5 clock cycles.
1: An active edge on the trigger input acts like a compare match on CC1 output. Then, OC is
set to the compare level independently of the result of the comparison. Delay to sample the
trigger input and to activate CC1 output is reduced to 3 clock cycles. OCFE acts only if the
channel is configured in PWM1 or PWM2 mode.


Bits 1:0 **CC1S** : Capture/Compare 1 selection

This bit-field defines the direction of the channel (input/output) as well as the used input.
00: CC1 channel is configured as output.
01: CC1 channel is configured as input, IC1 is mapped on TI1.
10: CC1 channel is configured as input, IC1 is mapped on TI2.
11: CC1 channel is configured as input, IC1 is mapped on TRC. This mode is working only if
an internal trigger input is selected through TS bit (TIMx_SMCR register)

_Note: CC1S bits are writable only when the channel is OFF (CC1E = ‘0’ in TIMx_CCER)._


**Input capture mode**


Bits 15:12 **IC2F** : Input capture 2 filter


Bits 11:10 **IC2PSC[1:0]** : Input capture 2 prescaler


Bits 9:8 **CC2S** : Capture/Compare 2 selection

This bit-field defines the direction of the channel (input/output) as well as the used input.
00: CC2 channel is configured as output
01: CC2 channel is configured as input, IC2 is mapped on TI2
10: CC2 channel is configured as input, IC2 is mapped on TI1
11: CC2 channel is configured as input, IC2 is mapped on TRC. This mode is working only if
an internal trigger input is selected through TS bit (TIMx_SMCR register)

_Note: CC2S bits are writable only when the channel is OFF (CC2E = ‘0’ in TIMx_CCER)._


RM0041 Rev 6 425/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


Bits 7:4 **IC1F[3:0]** : Input capture 1 filter

This bit-field defines the frequency used to sample TI1 input and the length of the digital filter
applied to TI1. The digital filter is made of an event counter in which N consecutive events
are needed to validate a transition on the output:
0000: No filter, sampling is done at f DTS
0001: f SAMPLING =f CK_INT, N=2
0010: f SAMPLING =f CK_INT, N=4
0011: f SAMPLING =f CK_INT, N=8
0100: f SAMPLING =f DTS /2, N=6
0101: f SAMPLING =f DTS /2, N=8
0110: f SAMPLING =f DTS /4, N=6
0111: f SAMPLING =f DTS /4, N=8
1000: f SAMPLING =f DTS /8, N=6
1001: f SAMPLING =f DTS /8, N=8
1010: f SAMPLING =f DTS /16, N=5
1011: f SAMPLING =f DTS /16, N=6
1100: f SAMPLING =f DTS /16, N=8
1101: f SAMPLING =f DTS /32, N=5
1110: f SAMPLING =f DTS /32, N=6
1111: f SAMPLING =f DTS /32, N=8


Bits 3:2 **IC1PSC** : Input capture 1 prescaler

This bit-field defines the ratio of the prescaler acting on CC1 input (IC1).
The prescaler is reset as soon as CC1E=’0’ (TIMx_CCER register).
00: no prescaler, capture is done each time an edge is detected on the capture input
01: capture is done once every 2 events
10: capture is done once every 4 events
11: capture is done once every 8 events


Bits 1:0 **CC1S** : Capture/Compare 1 Selection

This bit-field defines the direction of the channel (input/output) as well as the used input.
00: CC1 channel is configured as output
01: CC1 channel is configured as input, IC1 is mapped on TI1
10: CC1 channel is configured as input, IC1 is mapped on TI2
11: CC1 channel is configured as input, IC1 is mapped on TRC. This mode is working only if
an internal trigger input is selected through TS bit (TIMx_SMCR register)

_Note: CC1S bits are writable only when the channel is OFF (CC1E = ‘0’ in TIMx_CCER)._


**15.5.8** **TIM15 capture/compare enable register (TIM15_CCER)**


Address offset: 0x20


Reset value: 0x0000

|15 14 13 12 11 10 9 8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|
|Reserved|CC1NP|Res;|CC2P|CC2E|CC1NP|CC1NE|CC1P|CC1E|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:8 Reserved, must be kept at reset value.


Bit 7 **CC2NP** : Capture/Compare 2 complementary output polarity

refer to CC1NP description


Bit 6 Reserved, must be kept at reset value.


Bit 5 **CC2P** : Capture/Compare 2 output polarity

refer to CC1P description


426/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


Bit 4 **CC2E** : Capture/Compare 2 output enable

refer to CC1E description


Bit 3 **CC1NP** : Capture/Compare 1 complementary output polarity

0: OC1N active high
1: OC1N active low

_Note: This bit is not writable as soon as LOCK level 2 or 3 has been programmed (LOCK bits_
_in TIMx_BDTR register) and CC1S=”00” (the channel is configured in output)._


Bit 2 **CC1NE** : Capture/Compare 1 complementary output enable

0: Off - OC1N is not active. OC1N level is then function of MOE, OSSI, OSSR, OIS1, OIS1N
and CC1E bits.

1: On - OC1N signal is output on the corresponding output pin depending on MOE, OSSI,
OSSR, OIS1, OIS1N and CC1E bits.


Bit 1 **CC1P** : Capture/Compare 1 output polarity

**CC1 channel configured as output:**
0: OC1 active high
1: OC1 active low

**CC1 channel configured as input:**
The CC1NP/CC1P bits select the polarity of TI1FP1 and TI2FP1 for trigger or capture
operations.
00: noninverted/rising edge: circuit is sensitive to TIxFP1's rising edge (capture, trigger in
reset or trigger mode), TIxFP1 is not inverted (trigger in gated mode).
01: inverted/falling edge: circuit is sensitive to TIxFP1's falling edge (capture, trigger in reset,
or trigger mode), TIxFP1 is inverted (trigger in gated mode).
10: reserved, do not use this configuration.
11: noninverted/both edges: circuit is sensitive to both the rising and falling edges of TIxFP1
(capture, trigger in reset or trigger mode), TIxFP1 is not inverted (trigger in gated mode).

_Note: This bit is not writable as soon as LOCK level 2 or 3 has been programmed (LOCK bits_
_in TIMx_BDTR register).._


Bit 0 **CC1E** : Capture/Compare 1 output enable

**CC1 channel configured as output:**
0: Off - OC1 is not active. OC1 level is then function of MOE, OSSI, OSSR, OIS1, OIS1N
and CC1NE bits.

1: On - OC1 signal is output on the corresponding output pin depending on MOE, OSSI,
OSSR, OIS1, OIS1N and CC1NE bits.
**CC1 channel configured as input:**
This bit determines if a capture of the counter value can actually be done into the input
capture/compare register 1 (TIMx_CCR1) or not.
0: Capture disabled
1: Capture enabled


RM0041 Rev 6 427/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**Table 80. Output control bits for complementary OCx and OCxN channels with break feature**




























|Control bits|Col2|Col3|Col4|Col5|Output states(1)|Col7|
|---|---|---|---|---|---|---|
|MOE bit|OSSI bit|OSSR<br>bit|CCxE bit|CCxNE bit|OCx output state|OCxN output state|
|1|X|0|0|0|Output Disabled (not<br>driven by the timer)<br>OCx=0, OCx_EN=0|Output Disabled (not driven by<br>the timer)<br>OCxN=0, OCxN_EN=0|
|1|X|0|0|1|Output Disabled (not<br>driven by the timer)<br>OCx=0, OCx_EN=0|OCxREF + Polarity<br>OCxN=OCxREF xor CCxNP,<br>OCxN_EN=1|
|1|X|0|1|0|OCxREF + Polarity<br>OCx=OCxREF xor CCxP,<br>OCx_EN=1|Output Disabled (not driven by<br>the timer)<br>OCxN=0, OCxN_EN=0|
|1|X|0|1|1|OCREF + Polarity + dead-<br>time<br>OCx_EN=1|Complementary to OCREF (not<br>OCREF) + Polarity + dead-time<br>OCxN_EN=1|
|1|X|1|0|0|Output Disabled (not<br>driven by the timer)<br>OCx=CCxP, OCx_EN=0|Output Disabled (not driven by<br>the timer)<br>OCxN=CCxNP, OCxN_EN=0|
|1|X|1|0|1|Off-State (output enabled<br>with inactive state)<br>OCx=CCxP, OCx_EN=1|OCxREF + Polarity<br>OCxN=OCxREF xor CCxNP,<br>OCxN_EN=1|
|1|X|1|1|0|OCxREF + Polarity<br>OCx=OCxREF xor CCxP,<br>OCx_EN=1|Off-State (output enabled with<br>inactive state)<br>OCxN=CCxNP, OCxN_EN=1|
|1|X|1|1|1|OCREF + Polarity + dead-<br>time<br>OCx_EN=1|Complementary to OCREF (not<br>OCREF) + Polarity + dead-time<br>OCxN_EN=1|
|0|0|X|0|0|Output Disabled (not driven by the timer)<br>Asynchronously: OCx=CCxP, OCx_EN=0, OCxN=CCxNP,<br>OCxN_EN=0<br>Then if the clock is present: OCx=OISx and OCxN=OISxN<br>after a dead-time, assuming that OISx and OISxN do not<br>correspond to OCX and OCxN both in active state.|Output Disabled (not driven by the timer)<br>Asynchronously: OCx=CCxP, OCx_EN=0, OCxN=CCxNP,<br>OCxN_EN=0<br>Then if the clock is present: OCx=OISx and OCxN=OISxN<br>after a dead-time, assuming that OISx and OISxN do not<br>correspond to OCX and OCxN both in active state.|
|0|0|0|0|1|1|1|
|0|0|0|1|0|0|0|
|0|0|0|1|1|1|1|
|0|1|1|0|0|0|0|
|0|1|1|0|1|Off-State (output enabled with inactive state)<br>Asynchronously: OCx=CCxP, OCx_EN=1, OCxN=CCxNP,<br>OCxN_EN=1<br>Then if the clock is present: OCx=OISx and OCxN=OISxN<br>after a dead-time, assuming that OISx and OISxN do not<br>correspond to OCX and OCxN both in active state|Off-State (output enabled with inactive state)<br>Asynchronously: OCx=CCxP, OCx_EN=1, OCxN=CCxNP,<br>OCxN_EN=1<br>Then if the clock is present: OCx=OISx and OCxN=OISxN<br>after a dead-time, assuming that OISx and OISxN do not<br>correspond to OCX and OCxN both in active state|
|0|1|1|1|0|0|0|
|0|1|1|1|1|1|1|



1. When both outputs of a channel are not used (CCxE = CCxNE = 0), the OISx, OISxN, CCxP and CCxNP bits must be kept
cleared.


_Note:_ _The state of the external I/O pins connected to the complementary OCx and OCxN channels_
_depends on the OCx and OCxN channel state and the GPIO and AFIO registers._


428/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**15.5.9** **TIM15 counter (TIM15_CNT)**


Address offset: 0x24


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **CNT[15:0]** : Counter value


**15.5.10** **TIM15 prescaler (TIM15_PSC)**


Address offset: 0x28


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **PSC[15:0]** : Prescaler value
The counter clock frequency (CK_CNT) is equal to f CK_PSC / (PSC[15:0] + 1).
PSC contains the value to be loaded in the active prescaler register at each update event
(including when the counter is cleared through UG bit of TIMx_EGR register or through trigger
controller when configured in “reset mode”).


**15.5.11** **TIM15 auto-reload register (TIM15_ARR)**


Address offset: 0x2C


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **ARR[15:0]** : Auto-reload value
ARR is the value to be loaded in the actual auto-reload register.

Refer to the _Section 14.3.1: Time-base unit on page 345_ for more details about ARR update
and behavior.

The counter is blocked while the auto-reload value is null.


RM0041 Rev 6 429/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**15.5.12** **TIM15 repetition counter register (TIM15_RCR)**


Address offset: 0x30


Reset value: 0x0000

|15 14 13 12 11 10 9 8|7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:8 Reserved, must be kept at reset value.


Bits 7:0 **REP[7:0]** : Repetition counter value

These bits allow the user to set-up the update rate of the compare registers (i.e. periodic
transfers from preload to active registers) when preload registers are enable, as well as the
update interrupt generation rate, if this interrupt is enable.

Each time the REP_CNT related downcounter reaches zero, an update event is generated
and it restarts counting from REP value. As REP_CNT is reloaded with REP value only at the
repetition update event U_RC, any write to the TIMx_RCR register is not taken in account until
the next repetition update event.

It means in PWM mode (REP+1) corresponds to the number of PWM periods in edge-aligned
mode.


**15.5.13** **TIM15 capture/compare register 1 (TIM15_CCR1)**


Address offset: 0x34


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **CCR1[15:0]** : Capture/Compare 1 value

**If channel CC1 is configured as output** :
CCR1 is the value to be loaded in the actual capture/compare 1 register (preload value).

It is loaded permanently if the preload feature is not selected in the TIMx_CCMR1 register (bit
OC1PE). Else the preload value is copied in the active capture/compare 1 register when an
update event occurs.

The active capture/compare register contains the value to be compared to the counter
TIMx_CNT and signaled on OC1 output.


**If channel CC1 is configured as input** :
CCR1 is the counter value transferred by the last input capture 1 event (IC1).


430/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**15.5.14** **TIM15 capture/compare register 2 (TIM15_CCR2)**


Address offset: 0x38


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **CCR2[15:0]** : Capture/Compare 2 value

**If channel CC2 is configured as output** :
CCR2 is the value to be loaded in the actual capture/compare 2 register (preload value).

It is loaded permanently if the preload feature is not selected in the TIMx_CCMR2 register (bit
OC2PE). Else the preload value is copied in the active capture/compare 2 register when an
update event occurs.

The active capture/compare register contains the value to be compared to the counter
TIMx_CNT and signalled on OC2 output.
**If channel CC2 is configured as input** :
CCR2 is the counter value transferred by the last input capture 2 event (IC2).


**15.5.15** **TIM15 break and dead-time register (TIM15_BDTR)**


Address offset: 0x44


Reset value: 0x0000

|15|14|13|12|11|10|9 8|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MOE|AOE|BKP|BKE|OSSR|OSSI|LOCK[1:0]|LOCK[1:0]|DTG[7:0]|DTG[7:0]|DTG[7:0]|DTG[7:0]|DTG[7:0]|DTG[7:0]|DTG[7:0]|DTG[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



_Note:_ _As the bits AOE, BKP, BKE, OSSI, OSSR and DTG[7:0] can be write-locked depending on_
_the LOCK configuration, it can be necessary to configure all of them during the first write_
_access to the TIMx_BDTR register._


RM0041 Rev 6 431/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


Bit 15 **MOE** : Main output enable

This bit is cleared asynchronously by hardware as soon as the break input is active. It is set
by software or automatically depending on the AOE bit. It is acting only on the channels
which are configured in output.
0: OC and OCN outputs are disabled or forced to idle state
1: OC and OCN outputs are enabled if their respective enable bits are set (CCxE, CCxNE in
TIMx_CCER register)
See OC/OCN enable description for more details ( _Section 15.5.8: TIM15 capture/compare_
_enable register (TIM15_CCER) on page 426_ ).


Bit 14 **AOE** : Automatic output enable

0: MOE can be set only by software
1: MOE can be set by software or automatically at the next update event (if the break input is
not be active)

_Note: This bit can not be modified as long as LOCK level 1 has been programmed (LOCK bits_
_in TIMx_BDTR register)._


Bit 13 **BKP** : Break polarity

0: Break input BRK is active low
1: Break input BRK is active high

_Note: This bit can not be modified as long as LOCK level 1 has been programmed (LOCK bits_
_in TIMx_BDTR register)._

_Note: Any write operation to this bit takes a delay of 1 APB clock cycle to become effective._


Bit 12 **BKE** : Break enable

0: Break inputs (BRK and CSS clock failure event) disabled
1; Break inputs (BRK and CSS clock failure event) enabled

_Note: This bit cannot be modified when LOCK level 1 has been programmed (LOCK bits in_
_TIMx_BDTR register)._

_Note: Any write operation to this bit takes a delay of 1 APB clock cycle to become effective._


Bit 11 **OSSR** : Off-state selection for Run mode

This bit is used when MOE=1 on channels having a complementary output which are
configured as outputs. OSSR is not implemented if no complementary output is implemented
in the timer.

See OC/OCN enable description for more details ( _Section 15.5.8: TIM15 capture/compare_
_enable register (TIM15_CCER) on page 426_ ).
0: When inactive, OC/OCN outputs are disabled (OC/OCN enable output signal=0)
1: When inactive, OC/OCN outputs are enabled with their inactive level as soon as CCxE=1
or CCxNE=1. Then, OC/OCN enable output signal=1

_Note: This bit can not be modified as soon as the LOCK level 2 has been programmed (LOCK_
_bits in TIMx_BDTR register)._


432/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


Bit 10 **OSSI** : Off-state selection for Idle mode

This bit is used when MOE=0 on channels configured as outputs.
See OC/OCN enable description for more details ( _Section 15.5.8: TIM15 capture/compare_
_enable register (TIM15_CCER) on page 426_ ).
0: When inactive, OC/OCN outputs are disabled (OC/OCN enable output signal=0)
1: When inactive, OC/OCN outputs are forced first with their idle level as soon as CCxE=1 or
CCxNE=1. OC/OCN enable output signal=1)

_Note: This bit can not be modified as soon as the LOCK level 2 has been programmed (LOCK_
_bits in TIMx_BDTR register)._


Bits 9:8 **LOCK[1:0]** : Lock configuration

These bits offer a write protection against software errors.
00: LOCK OFF - No bit is write protected
01: LOCK Level 1 = DTG bits in TIMx_BDTR register, OISx and OISxN bits in TIMx_CR2
register and BKE/BKP/AOE bits in TIMx_BDTR register can no longer be written
10: LOCK Level 2 = LOCK Level 1 + CC Polarity bits (CCxP/CCxNP bits in TIMx_CCER
register, as long as the related channel is configured in output through the CCxS bits) as well
as OSSR and OSSI bits can no longer be written.
11: LOCK Level 3 = LOCK Level 2 + CC Control bits (OCxM and OCxPE bits in
TIMx_CCMRx registers, as long as the related channel is configured in output through the
CCxS bits) can no longer be written.

_Note: The LOCK bits can be written only once after the reset. Once the TIMx_BDTR register_
_has been written, their content is frozen until the next reset._


Bits 7:0 **DTG[7:0]** : Dead-time generator setup

This bit-field defines the duration of the dead-time inserted between the complementary
outputs. DT correspond to this duration.
DTG[7:5]=0xx => DT=DTG[7:0]x t dtg with t dtg =t DTS
DTG[7:5]=10x => DT=(64+DTG[5:0])xt dtg with T dtg =2xt DTS
DTG[7:5]=110 => DT=(32+DTG[4:0])xt dtg with T dtg =8xt DTS
DTG[7:5]=111 => DT=(32+DTG[4:0])xt dtg with T dtg =16xt DTS
Example if T DTS =125ns (8MHz), dead-time possible values are:
0 to 15875 ns by 125 ns steps,
16 µs to 31750 ns by 250 ns steps,
32 µs to 63 µs by 1 µs steps,
64 µs to 126 µs by 2 µs steps

_Note: This bit-field can not be modified as long as LOCK level 1, 2 or 3 has been programmed_
_(LOCK bits in TIMx_BDTR register)._


**15.5.16** **TIM15 DMA control register (TIM15_DCR)**


Address offset: 0x48


Reset value: 0x0000

|15 14 13|12 11 10 9 8|Col3|Col4|Col5|Col6|7 6 5|4 3 2 1 0|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|DBL[4:0]|DBL[4:0]|DBL[4:0]|DBL[4:0]|DBL[4:0]|Reserved|DBA[4:0]|DBA[4:0]|DBA[4:0]|DBA[4:0]|DBA[4:0]|
|Res.|rw|rw|rw|rw|rw|Res.|rw|rw|rw|rw|rw|



RM0041 Rev 6 433/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


Bits 15:13 Reserved, must be kept at reset value.


Bits 12:8 **DBL[4:0]** : DMA burst length

This 5-bit vector defines the length of DMA transfers (the timer recognizes a burst transfer
when a read or a write access is done to the TIMx_DMAR address).
00000: 1 transfer,
00001: 2 transfers,
00010: 3 transfers,

...

10001: 18 transfers.


Bits 7:5 Reserved, must be kept at reset value.


Bits 4:0 **DBA[4:0]** : DMA base address

This 5-bits vector defines the base-address for DMA transfers (when read/write access are
done through the TIMx_DMAR address). DBA is defined as an offset starting from the
address of the TIMx_CR1 register.
Example:
00000: TIMx_CR1,
00001: TIMx_CR2,
00010: TIMx_SMCR,

...


**15.5.17** **TIM15 DMA address for full transfer (TIM15_DMAR)**


Address offset: 0x4C


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **DMAB[15:0]** : DMA register for burst accesses

A read or write operation to the DMAR register accesses the register located at the address

(TIMx_CR1 address) + (DBA + DMA index) x 4

where TIMx_CR1 address is the address of the control register 1, DBA is the DMA base
address configured in TIMx_DCR register, DMA index is automatically controlled by the
DMA transfer, and ranges from 0 to DBL (DBL configured in TIMx_DCR).


**15.5.18** **TIM15 register map**


TIM15 registers are mapped as 16-bit addressable registers as described in the table
below:


434/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**Table 81. TIM15 register map and reset values**





























































































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**TIM15_CR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CKD<br>[1:0]|CKD<br>[1:0]|ARPE|Reserved|Reserved|Reserved|OPM|URS|UDIS|CEN|
|0x00|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|
|0x04|**TIM15_CR2**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|OIS2|OIS1N|OIS1|TI1S|MMS[2:0]|MMS[2:0]|MMS[2:0]|CCDS|CCUS|Reserved|CCPC|
|0x04|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|
|0x08|**TIM15_SMCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MSM|TS[2:0]|TS[2:0]|TS[2:0]|Reserved|SMS[2:0]|SMS[2:0]|SMS[2:0]|
|0x08|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|
|0x0C|**TIM15_DIER**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|TDE|Reserved|Reserved|Reserved|CC2DE|CC1DE|UDE|BIE|TIE|COMIE|Reserved|Reserved|CC2IE|CC1IE|UIE|
|0x0C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**TIM15_SR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CC2OF|CC1OF|Reserved|BIF|TIF|COMIF|Reserved|Reserved|CC2IF|CC1IF|UIF|
|0x10|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|
|0x14|**TIM15_EGR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|BG|TG|COMG|Reserved|Reserved|CC2G|CC1G|UG|
|0x14|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|
|0x18|**TIM15_CCMR1**<br>Output<br>Compare mode|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|OC2M<br>[2:0]|OC2M<br>[2:0]|OC2M<br>[2:0]|OC2PE|OC2FE|CC2S<br>[1:0]|CC2S<br>[1:0]|Reserved|OC1M<br>[2:0]|OC1M<br>[2:0]|OC1M<br>[2:0]|OC1PE|OC1FE|CC1<br>S <br>[1:0]|CC1<br>S <br>[1:0]|
|0x18|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x18|**TIM15_CCMR1**<br>Input Capture<br>mode|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|IC2F[3:0]|IC2F[3:0]|IC2F[3:0]|IC2F[3:0]|IC2<br>PSC<br>[1:0]|IC2<br>PSC<br>[1:0]|CC2S<br>[1:0]|CC2S<br>[1:0]|IC1F[3:0]|IC1F[3:0]|IC1F[3:0]|IC1F[3:0]|IC1<br>PSC<br>[1:0]|IC1<br>PSC<br>[1:0]|CC1<br>S <br>[1:0]|CC1<br>S <br>[1:0]|
|0x18|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x20|**TIM15_CCER**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CC2NP|Reserved|CC2P|CC2E|CC1NP|CC1NE|CC1P|CC1E|
|0x20|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|
|0x24|**TIM15_CNT**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|
|0x24|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x28|**TIM15_PSC**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|
|0x28|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x2C|**TIM15_ARR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|
|0x2C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


RM0041 Rev 6 435/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**Table 81. TIM15 register map and reset values (continued)**







































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x30|**TIM15_RCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|
|0x30|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|
|0x34|**TIM15_CCR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|
|0x34|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x38|**TIM15_CCR2**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|CCR2[15:0]|
|0x38|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x44|**TIM15_BDTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MOE|AOE|BKP|BKE|OSSR|OSSI|LOCK<br>[1:0]|LOCK<br>[1:0]|DT[7:0]|DT[7:0]|DT[7:0]|DT[7:0]|DT[7:0]|DT[7:0]|DT[7:0]|DT[7:0]|
|0x44|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x48|**TIM15_DCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|DBL[4:0]|DBL[4:0]|DBL[4:0]|DBL[4:0]|DBL[4:0]|Reserved|Reserved|Reserved|DBA[4:0]|DBA[4:0]|DBA[4:0]|DBA[4:0]|DBA[4:0]|
|0x48|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x4C|**TIM15_DMAR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|
|0x4C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


Refer to _Section 2.3: Memory map_ for the register boundary addresses.


436/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**

## **15.6 TIM16&TIM17 registers**


Refer to _Section 1.1: List of abbreviations for registers_ for a list of abbreviations used in
register descriptions.


The peripheral registers have to be written by half-words (16 bits) or words (32 bits). Read
accesses can be done by bytes (8 bits), half-words (16 bits) or words (32 bits).


**15.6.1** **TIM16&TIM17 control register 1 (TIMx_CR1)**


Address offset: 0x00


Reset value: 0x0000

|15 14 13 12 11 10|9 8|Col3|7|6 5 4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|
|Reserved|CKD[1:0]|CKD[1:0]|ARPE|Reserved|OPM|URS|UDIS|CEN|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:10 Reserved, must be kept at reset value.


Bits 9:8 **CKD[1:0]** : Clock division

This bit-field indicates the division ratio between the timer clock (CK_INT) frequency and the
dead-time and sampling clock (t DTS )used by the dead-time generators and the digital filters
(TIx),
00: t DTS =t CK_INT
01: t DTS =2*t CK_INT
10: t DTS =4*t CK_INT
11: Reserved, do not program this value


Bit 7 **ARPE** : Auto-reload preload enable

0: TIMx_ARR register is not buffered
1: TIMx_ARR register is buffered


Bits 6:4 Reserved, must be kept at reset value.


Bit 3 **OPM** : One pulse mode

0: Counter is not stopped at update event
1: Counter stops counting at the next update event (clearing the bit CEN)


RM0041 Rev 6 437/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


Bit 2 **URS** : Update request source

This bit is set and cleared by software to select the UEV event sources.
0: Any of the following events generate an update interrupt or DMA request if enabled.
These events can be:

– Counter overflow/underflow

–
Setting the UG bit

–
Update generation through the slave mode controller
1: Only counter overflow/underflow generates an update interrupt or DMA request if
enabled.


Bit 1 **UDIS** : Update disable

This bit is set and cleared by software to enable/disable UEV event generation.
0: UEV enabled. The Update (UEV) event is generated by one of the following events:

– Counter overflow/underflow

–
Setting the UG bit

–
Update generation through the slave mode controller
Buffered registers are then loaded with their preload values.
1: UEV disabled. The Update event is not generated, shadow registers keep their value
(ARR, PSC, CCRx). However the counter and the prescaler are reinitialized if the UG bit is
set or if a hardware reset is received from the slave mode controller.


Bit 0 **CEN** : Counter enable

0: Counter disabled

1: Counter enabled

_Note: External clock and gated mode can work only if the CEN bit has been previously set by_
_software. However trigger mode can set the CEN bit automatically by hardware._


**15.6.2** **TIM16&TIM17 control register 2 (TIMx_CR2)**


Address offset: 0x04


Reset value: 0x0000

|15 14 13 12 11 10|9|8|7 6 5 4|3|2|1|0|
|---|---|---|---|---|---|---|---|
|Reserved|OIS1N|OIS1|Reserved|CCDS|CCUS|Res.|CCPC|
|Reserved|rw|rw|rw|rw|rw|rw|rw|



Bits 15:10 Reserved, must be kept at reset value.


Bit 9 **OIS1N** : Output Idle state 1 (OC1N output)

0: OC1N=0 after a dead-time when MOE=0

1: OC1N=1 after a dead-time when MOE=0

_Note: This bit can not be modified as long as LOCK level 1, 2 or 3 has been programmed_
_(LOCK bits in TIMx_BKR register)._


Bit 8 **OIS1** : Output Idle state 1 (OC1 output)

0: OC1=0 (after a dead-time if OC1N is implemented) when MOE=0
1: OC1=1 (after a dead-time if OC1N is implemented) when MOE=0

_Note: This bit can not be modified as long as LOCK level 1, 2 or 3 has been programmed_
_(LOCK bits in TIMx_BKR register)._


Bits 7:4 Reserved, must be kept at reset value.


438/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


Bit 3 **CCDS** : Capture/compare DMA selection

0: CCx DMA request sent when CCx event occurs
1: CCx DMA requests sent when update event occurs


Bit 2 **CCUS** : Capture/compare control update selection

0: When capture/compare control bits are preloaded (CCPC=1), they are updated by setting
the COMG bit only.
1: When capture/compare control bits are preloaded (CCPC=1), they are updated by setting
the COMG bit or when an rising edge occurs on TRGI.

_Note: This bit acts only on channels that have a complementary output._


Bit 1 Reserved, must be kept at reset value.


Bit 0 **CCPC** : Capture/compare preloaded control

0: CCxE, CCxNE and OCxM bits are not preloaded
1: CCxE, CCxNE and OCxM bits are preloaded, after having been written, they are updated
only when COM bit is set.

_Note: This bit acts only on channels that have a complementary output._


RM0041 Rev 6 439/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**15.6.3** **TIM16&TIM17 DMA/interrupt enable register (TIMx_DIER)**


Address offset: 0x0C


Reset value: 0x0000

|15|14|13 12 11 10|9|8|7|6|5|4 3 2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|
|Res.|TDE|Reserved|CC1DE|UDE|BIE|TIE|COMIE|Reserved|CC1IE|UIE|
|Res.|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bit 15 Reserved, must be kept at reset value.


Bit 14 **TDE** : Trigger DMA request enable

0: Trigger DMA request disabled
1: Trigger DMA request enabled


Bist 13:10 Reserved, must be kept at reset value.


Bit 9 **CC1DE** : Capture/Compare 1 DMA request enable

0: CC1 DMA request disabled
1: CC1 DMA request enabled


Bit 8 **UDE** : Update DMA request enable

0: Update DMA request disabled
1: Update DMA request enabled


Bit 7 **BIE** : Break interrupt enable

0: Break interrupt disabled
1: Break interrupt enabled


Bit 6 **TIE** : Trigger interrupt enable

0: Trigger interrupt disabled
1: Trigger interrupt enabled


Bit 5 **COMIE:** COM interrupt enable

0: COM interrupt disabled
1: COM interrupt enabled


Bits 4:2 Reserved, must be kept at reset value.


Bit 1 **CC1IE** : Capture/Compare 1 interrupt enable

0: CC1 interrupt disabled
1: CC1 interrupt enabled


Bit 0 **UIE** : Update interrupt enable

0: Update interrupt disabled
1: Update interrupt enabled


440/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**15.6.4** **TIM16&TIM17 status register (TIMx_SR)**


Address offset: 0x10


Reset value: 0x0000

|15 14 13 12 11 10|9|8|7|6|5|4 3 2|1|0|
|---|---|---|---|---|---|---|---|---|
|Reserved|CC1OF|Res.|BIF|TIF|COMIF|Reserved|CC1IF|UIF|
|Reserved|rc_w0|rc_w0|rc_w0|rc_w0|rc_w0|rc_w0|rc_w0|rc_w0|



Bits 15:10 Reserved, must be kept at reset value.


Bit 9 **CC1OF** : Capture/Compare 1 overcapture flag

This flag is set by hardware only when the corresponding channel is configured in input
capture mode. It is cleared by software by writing it to ‘0’.
0: No overcapture has been detected
1: The counter value has been captured in TIMx_CCR1 register while CC1IF flag was
already set


Bit 8 Reserved, must be kept at reset value.


Bit 7 **BIF** : Break interrupt flag

This flag is set by hardware as soon as the break input goes active. It can be cleared by
software if the break input is not active.
0: No break event occurred

1: An active level has been detected on the break input


Bit 6 **TIF** : Trigger interrupt flag

This flag is set by hardware on trigger event (active edge detected on TRGI input when the
slave mode controller is enabled in all modes but gated mode, both edges in case gated
mode is selected). It is cleared by software.
0: No trigger event occurred
1: Trigger interrupt pending


Bit 5 **COMIF:** COM interrupt flag

This flag is set by hardware on a COM event (once the capture/compare control bits –CCxE,
CCxNE, OCxM– have been updated). It is cleared by software.

0: No COM event occurred

1: COM interrupt pending


RM0041 Rev 6 441/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


Bits 4:2 Reserved, must be kept at reset value.


Bit 1 **CC1IF** : Capture/Compare 1 interrupt flag

**If channel CC1 is configured as output:**
This flag is set by hardware when the counter matches the compare value, with some
exception in center-aligned mode (refer to the CMS bits in the TIMx_CR1 register
description). It is cleared by software.
0: No match.

1: The content of the counter TIMx_CNT matches the content of the TIMx_CCR1 register.
When the contents of TIMx_CCR1 are greater than the contents of TIMx_ARR, the CC1IF
bit goes high on the counter overflow (in upcounting and up/down-counting modes) or
underflow (in downcounting mode)
**If channel CC1 is configured as input:**
This bit is set by hardware on a capture. It is cleared by software or by reading the
TIMx_CCR1 register.
0: No input capture occurred
1: The counter value has been captured in TIMx_CCR1 register (An edge has been
detected on IC1 which matches the selected polarity)


Bit 0 **UIF** : Update interrupt flag

This bit is set by hardware on an update event. It is cleared by software.
0: No update occurred.
1: Update interrupt pending. This bit is set by hardware when the registers are updated:

–
At overflow regarding the repetition counter value (update if repetition counter = 0)
and if the UDIS=0 in the TIMx_CR1 register.

–
When CNT is reinitialized by software using the UG bit in TIMx_EGR register, if
URS=0 and UDIS=0 in the TIMx_CR1 register.

– When CNT is reinitialized by a trigger event (refer to _Section 15.5.3: TIM15 slave_
_mode control register (TIM15_SMCR)_ ), if URS=0 and UDIS=0 in the TIMx_CR1
register.


**15.6.5** **TIM16&TIM17 event generation register (TIMx_EGR)**


Address offset: 0x14


Reset value: 0x0000

|15 14 13 12 11 10 9 8|7|6|5|4 3 2|1|0|
|---|---|---|---|---|---|---|
|Reserved|BG|TG|COMG|Reserved|CC1G|UG|
|Reserved|w|w|w|w|w|w|



Bits 15:8 Reserved, must be kept at reset value.


Bit 7 **BG** : Break generation

This bit is set by software in order to generate an event, it is automatically cleared by
hardware.

0: No action.

1: A break event is generated. MOE bit is cleared and BIF flag is set. Related interrupt or
DMA transfer can occur if enabled.


Bit 6 **TG** : Trigger generation

This bit is set by software in order to generate an event, it is automatically cleared by
hardware.

0: No action.

1: The TIF flag is set in TIMx_SR register. Related interrupt or DMA transfer can occur if
enabled.


442/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


Bit 5 **COMG:** Capture/Compare control update generation

This bit can be set by software, it is automatically cleared by hardware.

0: No action

1: When the CCPC bit is set, it is possible to update the CCxE, CCxNE and OCxM bits

_Note: This bit acts only on channels that have a complementary output._


Bits 4:2 Reserved, must be kept at reset value.


Bit 1 **CC1G** : Capture/Compare 1 generation

This bit is set by software in order to generate an event, it is automatically cleared by
hardware.

0: No action.

1: A capture/compare event is generated on channel 1:
**If channel CC1 is configured as output:**
CC1IF flag is set, Corresponding interrupt or DMA request is sent if enabled.
**If channel CC1 is configured as input:**
The current value of the counter is captured in TIMx_CCR1 register. The CC1IF flag is set,
the corresponding interrupt or DMA request is sent if enabled. The CC1OF flag is set if the
CC1IF flag was already high.


Bit 0 **UG** : Update generation

This bit can be set by software, it is automatically cleared by hardware.
0: No action.

1: Reinitialize the counter and generates an update of the registers. Note that the prescaler
counter is cleared too (anyway the prescaler ratio is not affected). The counter is cleared if
the center-aligned mode is selected or if DIR=0 (upcounting), else it takes the auto-reload
value (TIMx_ARR) if DIR=1 (downcounting).


**15.6.6** **TIM16&TIM17 capture/compare mode register 1 (TIMx_CCMR1)**


Address offset: 0x18


Reset value: 0x0000


The channels can be used in input (capture mode) or in output (compare mode). The
direction of a channel is defined by configuring the corresponding CCxS bits. All the other
bits of this register have a different function in input and in output mode. For a given bit,
OCxx describes its function when the channel is configured in output, ICxx describes its
function when the channel is configured in input. Take care that the same bit can have a
different meaning for the input stage and for the output stage.





|15 14 13 12 11 10 9 8|7|6 5 4|Col4|Col5|3|2|1 0|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|Res|OC1M[2:0]|OC1M[2:0]|OC1M[2:0]|OC1PE|OC1FE|CC1S[1:0]|CC1S[1:0]|
|Reserved|IC1F[3:0]|IC1F[3:0]|IC1F[3:0]|IC1F[3:0]|IC1PSC[1:0]|IC1PSC[1:0]|IC1PSC[1:0]|IC1PSC[1:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|


RM0041 Rev 6 443/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**Output compare mode:**


Bits 15:7 Reserved, must be kept at reset value.


Bits 6:4 **OC1M** : Output Compare 1 mode

These bits define the behavior of the output reference signal OC1REF from which OC1 and
OC1N are derived. OC1REF is active high whereas OC1 and OC1N active level depends
on CC1P and CC1NP bits.

000: Frozen - The comparison between the output compare register TIMx_CCR1 and the
counter TIMx_CNT has no effect on the outputs.
001: Set channel 1 to active level on match. OC1REF signal is forced high when the
counter TIMx_CNT matches the capture/compare register 1 (TIMx_CCR1).
010: Set channel 1 to inactive level on match. OC1REF signal is forced low when the
counter TIMx_CNT matches the capture/compare register 1 (TIMx_CCR1).
011: Toggle - OC1REF toggles when TIMx_CNT=TIMx_CCR1.
100: Force inactive level - OC1REF is forced low.

101: Force active level - OC1REF is forced high.
110: PWM mode 1 - In upcounting, channel 1 is active as long as TIMx_CNT<TIMx_CCR1
else inactive. In downcounting, channel 1 is inactive (OC1REF=‘0’) as long as
TIMx_CNT>TIMx_CCR1 else active (OC1REF=’1’).
111: PWM mode 2 - In upcounting, channel 1 is inactive as long as
TIMx_CNT<TIMx_CCR1 else active. In downcounting, channel 1 is active as long as
TIMx_CNT>TIMx_CCR1 else inactive.

_Note:_ _**1:**_ _These bits can not be modified as long as LOCK level 3 has been programmed_
_(LOCK bits in TIMx_BDTR register) and CC1S=’00’ (the channel is configured in_
_output)._

_**2:**_ _In PWM mode 1 or 2, the OCREF level changes only when the result of the_
_comparison changes or when the output compare mode switches from “frozen” mode_
_to “PWM” mode._


Bit 3 **OC1PE** : Output Compare 1 preload enable

0: Preload register on TIMx_CCR1 disabled. TIMx_CCR1 can be written at anytime, the
new value is taken in account immediately.
1: Preload register on TIMx_CCR1 enabled. Read/Write operations access the preload
register. TIMx_CCR1 preload value is loaded in the active register at each update event.

_Note: These bits can not be modified as long as LOCK level 3 has been programmed (LOCK_
_bits in TIMx_BDTR register) and CC1S=’00’ (the channel is configured in output)._


Bit 2 **OC1FE** : Output Compare 1 fast enable

This bit is used to accelerate the effect of an event on the trigger in input on the CC output.
0: CC1 behaves normally depending on counter and CCR1 values even when the trigger is
ON. The minimum delay to activate CC1 output when an edge occurs on the trigger input is
5 clock cycles.
1: An active edge on the trigger input acts like a compare match on CC1 output. Then, OC
is set to the compare level independently of the result of the comparison. Delay to sample
the trigger input and to activate CC1 output is reduced to 3 clock cycles. OC1FE acts only if
the channel is configured in PWM1 or PWM2 mode.


Bits 1:0 **CC1S** : Capture/Compare 1 selection

This bit-field defines the direction of the channel (input/output) as well as the used input.
00: CC1 channel is configured as output
01: CC1 channel is configured as input, IC1 is mapped on TI1
10: CC1 channel is configured as input, IC1 is mapped on TI2
11: CC1 channel is configured as input, IC1 is mapped on TRC. This mode is working only
if an internal trigger input is selected through TS bit (TIMx_SMCR register)

_Note: CC1S bits are writable only when the channel is OFF (CC1E = ‘0’ in TIMx_CCER)._


444/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**Input capture mode**


Bits 15:8 Reserved, must be kept at reset value.


Bits 7:4 **IC1F[3:0]** : Input capture 1 filter

This bit-field defines the frequency used to sample TI1 input and the length of the digital filter applied
to TI1. The digital filter is made of an event counter in which N consecutive events are needed to
validate a transition on the output:
0000: No filter, sampling is done at f DTS
0001: f SAMPLING =f CK_INT, N=2
0010: f SAMPLING =f CK_INT, N=4
0011: f SAMPLING =f CK_INT, N=8
0100: f SAMPLING =f DTS /2, N=6
0101: f SAMPLING =f DTS /2, N=8
0110: f SAMPLING =f DTS /4, N=6
0111: f SAMPLING =f DTS /4, N=8
1000: f SAMPLING =f DTS /8, N=6
1001: f SAMPLING =f DTS /8, N=8
1010: f SAMPLING =f DTS /16, N=5
1011: f SAMPLING =f DTS /16, N=6
1100: f SAMPLING =f DTS /16, N=8
1101: f SAMPLING =f DTS /32, N=5
1110: f SAMPLING =f DTS /32, N=6
1111: f SAMPLING =f DTS /32, N=8


Bits 3:2 **IC1PSC** : Input capture 1 prescaler

This bit-field defines the ratio of the prescaler acting on CC1 input (IC1).
The prescaler is reset as soon as CC1E=’0’ (TIMx_CCER register).
00: no prescaler, capture is done each time an edge is detected on the capture input.
01: capture is done once every 2 events
10: capture is done once every 4 events
11: capture is done once every 8 events


Bits 1:0 **CC1S** : Capture/Compare 1 Selection

This bit-field defines the direction of the channel (input/output) as well as the used input.
00: CC1 channel is configured as output
01: CC1 channel is configured as input, IC1 is mapped on TI1
10: CC1 channel is configured as input, IC1 is mapped on TI2
11: CC1 channel is configured as input, IC1 is mapped on TRC. This mode is working only if an
internal trigger input is selected through TS bit (TIMx_SMCR register)

_Note: CC1S bits are writable only when the channel is OFF (CC1E = ‘0’ in TIMx_CCER)._


**15.6.7** **TIM16&TIM17 capture/compare enable register (TIMx_CCER)**


Address offset: 0x20


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4|3|2|1|0|
|---|---|---|---|---|
|Reserved|CC1NP|CC1NE|CC1P|CC1E|
|Reserved|rw|rw|rw|rw|



RM0041 Rev 6 445/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


Bits 15:4 Reserved, must be kept at reset value.


Bit 3 **CC1NP** : Capture/Compare 1 complementary output polarity

0: OC1N active high
1: OC1N active low

_Note: This bit is not writable as soon as LOCK level 2 or 3 has been programmed (LOCK bits_
_in TIMx_BDTR register) and CC1S=”00” (the channel is configured in output)._


Bit 2 **CC1NE** : Capture/Compare 1 complementary output enable

0: Off - OC1N is not active. OC1N level is then function of MOE, OSSI, OSSR, OIS1, OIS1N
and CC1E bits.

1: On - OC1N signal is output on the corresponding output pin depending on MOE, OSSI,
OSSR, OIS1, OIS1N and CC1E bits.


Bit 1 **CC1P** : Capture/Compare 1 output polarity

**CC1 channel configured as output:**
0: OC1 active high
1: OC1 active low

**CC1 channel configured as input:**
The CC1NP/CC1P bits select the polarity of TI1FP1 and TI2FP1 for capture operation.
00: Non-inverted/rising edge: circuit is sensitive to TIxFP1's rising edge TIxFP1 is not
inverted.

01: Inverted/falling edge: circuit is sensitive to TIxFP1's falling edge, TIxFP1 is inverted.
10: Reserved, do not use this configuration.
11: Non-inverted/both edges: circuit is sensitive to both the rising and falling edges of
TIxFP1, TIxFP1 is not inverted.

_Note: This bit is not writable as soon as LOCK level 2 or 3 has been programmed (LOCK bits_
_in TIMx_BDTR register)_


Bit 0 **CC1E** : Capture/Compare 1 output enable

**CC1 channel configured as output:**
0: Off - OC1 is not active. OC1 level is then function of MOE, OSSI, OSSR, OIS1, OIS1N
and CC1NE bits.

1: On - OC1 signal is output on the corresponding output pin depending on MOE, OSSI,
OSSR, OIS1, OIS1N and CC1NE bits.
**CC1 channel configured as input:**
This bit determines if a capture of the counter value can actually be done into the input
capture/compare register 1 (TIMx_CCR1) or not.
0: Capture disabled
1: Capture enabled


446/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**Table 82. Output control bits for complementary OCx and OCxN channels with break**




























|Col1|Col2|Col3|Col4|Col5|feature|Col7|
|---|---|---|---|---|---|---|
|Control bits|Control bits|Control bits|Control bits|Control bits|Output states(1)|Output states(1)|
|MOE<br>bit|OSSI<br>bit|OSSR<br>bit|CCxE<br>bit|CCxNE<br>bit|OCx output state|OCxN output state|
|1|X|0|0|0|Output Disabled (not<br>driven by the timer)<br>OCx=0, OCx_EN=0|Output Disabled (not driven by<br>the timer)<br>OCxN=0, OCxN_EN=0|
|1|X|0|0|1|Output Disabled (not<br>driven by the timer)<br>OCx=0, OCx_EN=0|OCxREF + Polarity<br>OCxN=OCxREF xor CCxNP,<br>OCxN_EN=1|
|1|X|0|1|0|OCxREF + Polarity<br>OCx=OCxREF xor CCxP,<br>OCx_EN=1|Output Disabled (not driven by<br>the timer)<br>OCxN=0, OCxN_EN=0|
|1|X|0|1|1|OCREF + Polarity + dead-<br>time<br>OCx_EN=1|Complementary to OCREF (not<br>OCREF) + Polarity + dead-time<br>OCxN_EN=1|
|1|X|1|0|0|Output Disabled (not<br>driven by the timer)<br>OCx=CCxP, OCx_EN=0|Output Disabled (not driven by<br>the timer)<br>OCxN=CCxNP, OCxN_EN=0|
|1|X|1|0|1|Off-State (output enabled<br>with inactive state)<br>OCx=CCxP, OCx_EN=1|OCxREF + Polarity<br>OCxN=OCxREF xor CCxNP,<br>OCxN_EN=1|
|1|X|1|1|0|OCxREF + Polarity<br>OCx=OCxREF xor CCxP,<br>OCx_EN=1|Off-State (output enabled with<br>inactive state)<br>OCxN=CCxNP, OCxN_EN=1|
|1|X|1|1|1|OCREF + Polarity + dead-<br>time<br>OCx_EN=1|Complementary to OCREF (not<br>OCREF) + Polarity + dead-time<br>OCxN_EN=1|
|0|0|X|0|0|Output Disabled (not driven by the timer)<br>Asynchronously: OCx=CCxP, OCx_EN=0, OCxN=CCxNP,<br>OCxN_EN=0<br>Then if the clock is present: OCx=OISx and OCxN=OISxN<br>after a dead-time, assuming that OISx and OISxN do not<br>correspond to OCX and OCxN both in active state.|Output Disabled (not driven by the timer)<br>Asynchronously: OCx=CCxP, OCx_EN=0, OCxN=CCxNP,<br>OCxN_EN=0<br>Then if the clock is present: OCx=OISx and OCxN=OISxN<br>after a dead-time, assuming that OISx and OISxN do not<br>correspond to OCX and OCxN both in active state.|
|0|0|0|0|1|1|1|
|0|0|0|1|0|0|0|
|0|0|0|1|1|1|1|
|0|1|1|0|0|0|0|
|0|1|1|0|1|Off-State (output enabled with inactive state)<br>Asynchronously: OCx=CCxP, OCx_EN=1, OCxN=CCxNP,<br>OCxN_EN=1<br>Then if the clock is present: OCx=OISx and OCxN=OISxN<br>after a dead-time, assuming that OISx and OISxN do not<br>correspond to OCX and OCxN both in active state|Off-State (output enabled with inactive state)<br>Asynchronously: OCx=CCxP, OCx_EN=1, OCxN=CCxNP,<br>OCxN_EN=1<br>Then if the clock is present: OCx=OISx and OCxN=OISxN<br>after a dead-time, assuming that OISx and OISxN do not<br>correspond to OCX and OCxN both in active state|
|0|1|1|1|0|0|0|
|0|1|1|1|1|1|1|



1. When both outputs of a channel are not used (CCxE = CCxNE = 0), the OISx, OISxN, CCxP and CCxNP
bits must be kept cleared.


_Note:_ _The state of the external I/O pins connected to the complementary OCx and OCxN channels_
_depends on the OCx and OCxN channel state and the GPIO and AFIO registers._


RM0041 Rev 6 447/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**15.6.8** **TIM16&TIM17 counter (TIMx_CNT)**


Address offset: 0x24


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **CNT[15:0]** : Counter value


**15.6.9** **TIM16&TIM17 prescaler (TIMx_PSC)**


Address offset: 0x28


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **PSC[15:0]** : Prescaler value
The counter clock frequency (CK_CNT) is equal to f CK_PSC / (PSC[15:0] + 1).
PSC contains the value to be loaded in the active prescaler register at each update event
(including when the counter is cleared through UG bit of TIMx_EGR register or through trigger
controller when configured in “reset mode”).


**15.6.10** **TIM16&TIM17 auto-reload register (TIMx_ARR)**


Address offset: 0x2C


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **ARR[15:0]** : Auto-reload value
ARR is the value to be loaded in the actual auto-reload register.

Refer to the _Section 14.3.1: Time-base unit on page 345_ for more details about ARR update
and behavior.

The counter is blocked while the auto-reload value is null.


448/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**15.6.11** **TIM16&TIM17 repetition counter register (TIMx_RCR)**


Address offset: 0x30


Reset value: 0x0000

|15 14 13 12 11 10 9 8|7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:8 Reserved, must be kept at reset value.


Bits 7:0 **REP[7:0]** : Repetition counter value

These bits allow the user to set-up the update rate of the compare registers (i.e. periodic
transfers from preload to active registers) when preload registers are enable, as well as the
update interrupt generation rate, if this interrupt is enable.

Each time the REP_CNT related downcounter reaches zero, an update event is generated
and it restarts counting from REP value. As REP_CNT is reloaded with REP value only at the
repetition update event U_RC, any write to the TIMx_RCR register is not taken in account until
the next repetition update event.

It means in PWM mode (REP+1) corresponds to the number of PWM periods in edge-aligned
mode.


**15.6.12** **TIM16&TIM17 capture/compare register 1 (TIMx_CCR1)**


Address offset: 0x34


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|
|rw/ro|rw/ro|rw/ro|rw/ro|rw/ro|rw/ro|rw/ro|rw/ro|rw/ro|rw/ro|rw/ro|rw/ro|rw/ro|rw/ro|rw/ro|rw/ro|



Bits 15:0 **CCR1[15:0]** : Capture/Compare 1 value

**If channel CC1 is configured as output** :
CCR1 is the value to be loaded in the actual capture/compare 1 register (preload value).

It is loaded permanently if the preload feature is not selected in the TIMx_CCMR1 register (bit
OC1PE). Else the preload value is copied in the active capture/compare 1 register when an
update event occurs.

The active capture/compare register contains the value to be compared to the counter
TIMx_CNT and signaled on OC1 output.


**If channel CC1 is configured as input** :
CCR1 is the counter value transferred by the last input capture 1 event (IC1). The TIMx_CCR1
register is read-only and cannot be programmed.


RM0041 Rev 6 449/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**15.6.13** **TIM16&TIM17 break and dead-time register (TIMx_BDTR)**


Address offset: 0x44


Reset value: 0x0000

|15|14|13|12|11|10|9 8|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|MOE|AOE|BKP|BKE|OSSR|OSSI|LOCK[1:0]|LOCK[1:0]|DTG[7:0]|DTG[7:0]|DTG[7:0]|DTG[7:0]|DTG[7:0]|DTG[7:0]|DTG[7:0]|DTG[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



_Note:_ _As the bits AOE, BKP, BKE, OSSI, OSSR and DTG[7:0] can be write-locked depending on_
_the LOCK configuration, it can be necessary to configure all of them during the first write_
_access to the TIMx_BDTR register._


Bit 15 **MOE** : Main output enable

This bit is cleared asynchronously by hardware as soon as the break input is active. It is set
by software or automatically depending on the AOE bit. It is acting only on the channels
which are configured in output.
0: OC and OCN outputs are disabled or forced to idle state
1: OC and OCN outputs are enabled if their respective enable bits are set (CCxE, CCxNE in
TIMx_CCER register)
See OC/OCN enable description for more details ( _Section 15.5.8: TIM15 capture/compare_
_enable register (TIM15_CCER) on page 426_ ).


Bit 14 **AOE** : Automatic output enable

0: MOE can be set only by software
1: MOE can be set by software or automatically at the next update event (if the break input is
not be active)

_Note: This bit can not be modified as long as LOCK level 1 has been programmed (LOCK bits_
_in TIMx_BDTR register)._


Bit 13 **BKP** : Break polarity

0: Break input BRK is active low
1: Break input BRK is active high

_Note: This bit can not be modified as long as LOCK level 1 has been programmed (LOCK bits_
_in TIMx_BDTR register)._

_Note: Any write operation to this bit takes a delay of 1 APB clock cycle to become effective._


Bit 12 **BKE** : Break enable

0: Break inputs (BRK and CSS clock failure event) disabled
1; Break inputs (BRK and CSS clock failure event) enabled

_Note: This bit cannot be modified when LOCK level 1 has been programmed (LOCK bits in_
_TIMx_BDTR register)._

_Note: Any write operation to this bit takes a delay of 1 APB clock cycle to become effective._


Bit 11 **OSSR** : Off-state selection for Run mode

This bit is used when MOE=1 on channels having a complementary output which are
configured as outputs. OSSR is not implemented if no complementary output is implemented
in the timer.

See OC/OCN enable description for more details ( _Section 15.5.8: TIM15 capture/compare_
_enable register (TIM15_CCER) on page 426_ ).
0: When inactive, OC/OCN outputs are disabled (OC/OCN enable output signal=0)
1: When inactive, OC/OCN outputs are enabled with their inactive level as soon as CCxE=1
or CCxNE=1. Then, OC/OCN enable output signal=1

_Note: This bit can not be modified as soon as the LOCK level 2 has been programmed (LOCK_
_bits in TIMx_BDTR register)._


450/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


Bit 10 **OSSI** : Off-state selection for Idle mode

This bit is used when MOE=0 on channels configured as outputs.
See OC/OCN enable description for more details ( _Section 15.5.8: TIM15 capture/compare_
_enable register (TIM15_CCER) on page 426_ ).
0: When inactive, OC/OCN outputs are disabled (OC/OCN enable output signal=0)
1: When inactive, OC/OCN outputs are forced first with their idle level as soon as CCxE=1 or
CCxNE=1. OC/OCN enable output signal=1)

_Note: This bit can not be modified as soon as the LOCK level 2 has been programmed (LOCK_
_bits in TIMx_BDTR register)._


Bits 9:8 **LOCK[1:0]** : Lock configuration

These bits offer a write protection against software errors.
00: LOCK OFF - No bit is write protected
01: LOCK Level 1 = DTG bits in TIMx_BDTR register, OISx and OISxN bits in TIMx_CR2
register and BKE/BKP/AOE bits in TIMx_BDTR register can no longer be written.
10: LOCK Level 2 = LOCK Level 1 + CC Polarity bits (CCxP/CCxNP bits in TIMx_CCER
register, as long as the related channel is configured in output through the CCxS bits) as well
as OSSR and OSSI bits can no longer be written.
11: LOCK Level 3 = LOCK Level 2 + CC Control bits (OCxM and OCxPE bits in
TIMx_CCMRx registers, as long as the related channel is configured in output through the
CCxS bits) can no longer be written.

_Note: The LOCK bits can be written only once after the reset. Once the TIMx_BDTR register_
_has been written, their content is frozen until the next reset._


Bits 7:0 **DTG[7:0]** : Dead-time generator setup

This bit-field defines the duration of the dead-time inserted between the complementary
outputs. DT correspond to this duration.
DTG[7:5]=0xx => DT=DTG[7:0]x t dtg with t dtg =t DTS
DTG[7:5]=10x => DT=(64+DTG[5:0])xt dtg with T dtg =2xt DTS
DTG[7:5]=110 => DT=(32+DTG[4:0])xt dtg with T dtg =8xt DTS
DTG[7:5]=111 => DT=(32+DTG[4:0])xt dtg with T dtg =16xt DTS
Example if T DTS =125ns (8MHz), dead-time possible values are:
0 to 15875 ns by 125 ns steps,
16 µs to 31750 ns by 250 ns steps,
32 µs to 63 µs by 1 µs steps,
64 µs to 126 µs by 2 µs steps

_Note: This bit-field can not be modified as long as LOCK level 1, 2 or 3 has been programmed_
_(LOCK bits in TIMx_BDTR register)._


**15.6.14** **TIM16&TIM17 DMA control register (TIMx_DCR)**


Address offset: 0x48


Reset value: 0x0000

|15 14 13|12 11 10 9 8|Col3|Col4|Col5|Col6|7 6 5|4 3 2 1 0|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|DBL[4:0]|DBL[4:0]|DBL[4:0]|DBL[4:0]|DBL[4:0]|Reserved|DBA[4:0]|DBA[4:0]|DBA[4:0]|DBA[4:0]|DBA[4:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



RM0041 Rev 6 451/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


Bits 15:13 Reserved, must be kept at reset value.


Bits 12:8 **DBL[4:0]** : DMA burst length

This 5-bit vector defines the length of DMA transfers (the timer recognizes a burst transfer
when a read or a write access is done to the TIMx_DMAR address), i.e. the number of
transfers. Transfers can be in half-words or in bytes (see example below).
00000: 1 transfer,
00001: 2 transfers,
00010: 3 transfers,

...

10001: 18 transfers.


Bits 7:5 Reserved, must be kept at reset value.


Bits 4:0 **DBA[4:0]** : DMA base address

This 5-bits vector defines the base-address for DMA transfers (when read/write access are
done through the TIMx_DMAR address). DBA is defined as an offset starting from the
address of the TIMx_CR1 register.
Example:
00000: TIMx_CR1,
00001: TIMx_CR2,
00010: TIMx_SMCR,

...

**Example:** Let us consider the following transfer: DBL = 7 transfers and DBA = TIMx_CR1. In
this case the transfer is done to/from 7 registers starting from the TIMx_CR1 address..


**15.6.15** **TIM16&TIM17 DMA address for full transfer (TIMx_DMAR)**


Address offset: 0x4C


Reset value: 0x0000

|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 15:0 **DMAB[15:0]** : DMA register for burst accesses

A read or write access to the DMAR register accesses the register located at the address:

“(TIMx_CR1 address) + DBA + (DMA index)” in which:

TIMx_CR1 address is the address of the control register 1, DBA is the DMA base address
configured in TIMx_DCR register, DMA index is the offset automatically controlled by the
DMA transfer, depending on the length of the transfer DBL in the TIMx_DCR register.


**Example of how to use the DMA burst feature**


In this example the timer DMA burst feature is used to update the contents of the CCRx
registers (x = 2, 3, 4) with the DMA transferring half words into the CCRx registers.


This is done in the following steps:


452/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


1. Configure the corresponding DMA channel as follows:


–
DMA channel peripheral address is the DMAR register address


–
DMA channel memory address is the address of the buffer in the RAM containing
the data to be transferred by DMA into CCRx registers.


–
Number of data to transfer = 3 (See note below).


– Circular mode disabled.


2. Configure the DCR register by configuring the DBA and DBL bit fields as follows:
DBL = 3 transfers, DBA = 0xE.


3. Enable the TIMx update DMA request (set the UDE bit in the DIER register).


4. Enable TIMx


5. Enable the DMA channel


_Note:_ _This example is for the case where every CCRx register to be updated once. If every CCRx_
_register is to be updated twice for example, the number of data to transfer should be 6. Let's_
_take the example of a buffer in the RAM containing data1, data2, data3, data4, data5 and_
_data6. The data is transferred to the CCRx registers as follows: on the first update DMA_
_request, data1 is transferred to CCR2, data2 is transferred to CCR3, data3 is transferred to_
_CCR4 and on the second update DMA request, data4 is transferred to CCR2, data5 is_
_transferred to CCR3 and data6 is transferred to CCR4._


RM0041 Rev 6 453/709



455


**General-purpose timers (TIM15/16/17)** **RM0041**


**15.6.16** **TIM16&TIM17 register map**


TIM16&TIM17 registers are mapped as 16-bit addressable registers as described in the
table below:


**Table 83. TIM16&TIM17 register map and reset values**





















































































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x00|**TIMx_CR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CKD<br>[1:0]|CKD<br>[1:0]|ARPE|Reserved|Reserved|Reserved|OPM|URS|UDIS|CEN|
|0x00|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|
|0x04|**TIMx_CR2**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|OIS1N|OIS1|TI1S|MMS[2:0]|MMS[2:0]|MMS[2:0]|CCDS|CCUS|Reserved|CCPC|
|0x04|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|
|0x0C|**TIMx_DIER**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|TDE|Reserved|Reserved|Reserved|Reserved|CC1DE|UDE|BIE|TIE|Reserved|Reserved|Reserved|Reserved|CC1IE|UIE|
|0x0C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x10|**TIMx_SR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CC1OF|Reserved|BIF|TIF|Reserved|Reserved|Reserved|Reserved|CC1IF|UIF|
|0x10|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|
|0x14|**TIMx_EGR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|BG|TG|COMG|Reserve<br>d|Reserve<br>d|Reserve<br>d|CC1G|UG|
|0x14|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|
|0x18|**TIMx_CCMR1**<br>Output<br>Compare mode|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|OC1M<br>[2:0]|OC1M<br>[2:0]|OC1M<br>[2:0]|OC1PE|OC1FE|CC1<br>S <br>[1:0]|CC1<br>S <br>[1:0]|
|0x18|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|
|0x18|**TIMx_CCMR1**<br>Input Capture<br>mode|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|IC1F[3:0]|IC1F[3:0]|IC1F[3:0]|IC1F[3:0]|IC1<br>PSC<br>[1:0]|IC1<br>PSC<br>[1:0]|CC1<br>S <br>[1:0]|CC1<br>S <br>[1:0]|
|0x18|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|
|0x20|**TIMx_CCER**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CC1NP|CC1NE|CC1P|CC1E|
|0x20|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|
|0x24|**TIMx_CNT**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|CNT[15:0]|
|0x24|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x28|**TIMx_PSC**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|PSC[15:0]|
|0x28|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x2C|**TIMx_ARR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|ARR[15:0]|
|0x2C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|


454/709 RM0041 Rev 6


**RM0041** **General-purpose timers (TIM15/16/17)**


**Table 83. TIM16&TIM17 register map and reset values (continued)**



































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x30|**TIMx_RCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|REP[7:0]|
|0x30|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|
|0x34|**TIMx_CCR1**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|CCR1[15:0]|
|0x34|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x44|**TIMx_BDTR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|MOE|AOE|BKP|BKE|OSSR|OSSI|LOCK<br>[1:0]|LOCK<br>[1:0]|DT[7:0]|DT[7:0]|DT[7:0]|DT[7:0]|DT[7:0]|DT[7:0]|DT[7:0]|DT[7:0]|
|0x44|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x48|**TIMx_DCR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|DBL[4:0]|DBL[4:0]|DBL[4:0]|DBL[4:0]|DBL[4:0]|Reserve<br>d|Reserve<br>d|Reserve<br>d|DBA[4:0]|DBA[4:0]|DBA[4:0]|DBA[4:0]|DBA[4:0]|
|0x48|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x4C|**TIMx_DMAR**|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|DMAB[15:0]|
|0x4C|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


Refer to _Section 3.3: Memory map_ for the register boundary addresses.


RM0041 Rev 6 455/709



455


