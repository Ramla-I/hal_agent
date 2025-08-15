**RM0364** **Operational amplifier (OPAMP)**

#### **16 Operational amplifier (OPAMP)**

##### **16.1 OPAMP introduction**


STM32F334xx devices embed 1 operational amplifier OPAMP2. It can either be used as a
standalone amplifier or as a follower / programmable gain amplifier.


The operational amplifier output is internally connected to an ADC channel for measurement

purposes.

##### **16.2 OPAMP main features**


      - Rail-to-rail input/output


      - Low offset voltage


      - Capability of being configured as a standalone operational amplifier or as a
programmable gain amplifier (PGA)


      - Access to all terminals


      - Input multiplexer on inverting and non-inverting input


      - Input multiplexer can be triggered by a timer and synchronized with a PWM signal.

##### **16.3 OPAMP functional description**


**16.3.1** **General description**


On every OPAMP, there is one 4:1 multiplexer on the non-inverting input and one 2:1
multiplexer on the inverting input.


The inverting and non inverting inputs selection is made using the VM_SEL and VP_SEL
bits respectively in the OPAMPx_CSR register.


The I/Os used as OPAMP input/outputs must be configured in analog mode in the GPIOs
registers.


The connections with dedicated I/O are summarized in the table below and in _Figure 94_ .


**Table 58. Connections with dedicated I/O**

|OPAMP2 inverting input|OPAMP2 non inverting input|
|---|---|
|PA5 (VM1)|PA7 (VP0)|
|PC5 (VM0)|PD14 (VP1)|
|-|PB0 (VP2)|



**16.3.2** **Clock**


The OPAMP clock provided by the clock controller is synchronized with the PCLK2 (APB2
clock). There is no clock enable control bit provided in the RCC controller. To use a clock
source for the OPAMP, the SYSCFG clock enable control bit must be set in the RCC
controller.


RM0364 Rev 4 353/1124



363


**Operational amplifier (OPAMP)** **RM0364**


**16.3.3** **Operational amplifiers and comparators interconnections**


Internal connections between the operational amplifiers and the comparators are useful in
motor control applications. These connections are summarized in the following figures.





























**16.3.4** **Using the OPAMP outputs as ADC inputs**


In order to use OPAMP outputs as ADC inputs, the operational amplifiers must be enabled
and the ADC must use the OPAMP output channel number:


      - For OPAMP2, ADC2 channel 3 is used.


**16.3.5** **Calibration**


The OPAMP interface continuously sends trimmed offset values to the 4 operational
amplifiers. At startup, these values are initialized with the preset ‘factory’ trimming value.


Furthermore each operational amplifier offset can be trimmed by the user.


The user can switch from the ‘factory’ values to the ‘user’ trimmed values using the
USER_TRIM bit in the OPAMP control register. This bit is reset at startup (‘factory’ values
are sent to the operational amplifiers).


The rail-to-rail input stage of the OPAMP is composed of two differential pairs:


      - One pair composed of NMOS transistors


      - One pair composed of PMOS transistors.


As these two pairs are independent, the trimming procedure calibrates each one separately.
The TRIMOFFSETN bits calibrate the NMOS differential pair offset and the TRIMOFFSETP
bits calibrate the PMOS differential pair offset.


To calibrate the NMOS differential pair, the following conditions must be met: CALON=1 and
CALSEL=11. In this case, an internal high voltage reference (0.9 x V DDA ) is generated and
applied on the inverting and non inverting OPAMP inputs connected together. The voltage


354/1124 RM0364 Rev 4


**RM0364** **Operational amplifier (OPAMP)**


applied to both inputs of the OPAMP can be measured (the OPAMP reference voltage can
be output through the TSTREF bit and connected internally to an ADC channel; refer to
_Section 13: Analog-to-digital converters (ADC) on page 211_ ). The software should
increment the TRIMOFFSETN bits in the OPAMP control register from 0x00 to the first value
that causes the OUTCAL bit to change from 1 to 0 in the OPAMP register. If the OUTCAL bit
is reset, the offset is calibrated correctly and the corresponding trimming value must be
stored.


The calibration of the PMOS differential pair is performed in the same way, with two
differences: the TRIMOFFSETP bits-fields are used and the CALSEL bits must be
programmed to ‘01’ (an internal low voltage reference (0.1 x V DDA ) is generated and applied
on the inverting and non inverting OPAMP inputs connected together).


_Note:_ _During calibration mode, to get the correct OUTCAL value, please make sure the_
_OFFTRIMmax delay (specified in the datasheet electrical characteristics section) has_
_elapsed between the write of a trimming value (TRIMOFFSETP or TRIMOFFSETN) and the_
_read of the OUTCAL value,_


To calibrate the NMOS differential pair, use the following software procedure:


1. Enable OPAMP by setting the OPAMPxEN bit


2. Enable the user offset trimming by setting the USERTRIM bit


3. Connect VM and VP to the internal reference voltage by setting the CALON bit


4. Set CALSEL to 11 (OPAMP internal reference =0.9 x V DDA )


5. In a loop, increment the TRIMOFFSETN value. To exit from the loop, the OUTCAL bit
must be reset. In this case, the TRIMOFFSETN value must be stored.


The same software procedure must be applied for PMOS differential pair calibration with
CALSEL = 01 (OPAMP internal reference = 0.1 V DDA ).


**16.3.6** **Timer controlled Multiplexer mode**


The selection of the OPAMP inverting and non inverting inputs can be done automatically. In
this case, the switch from one input to another is done automatically. This automatic switch
is triggered by the TIM1 CC6 output arriving on the OPAMP input multiplexers.


This is useful for dual motor control with a need to measure the currents on the 3 phases
instantaneously on a first motor and then on the second motor.


The automatic switch is enabled by setting the TCM_EN bit in the OPAMP control register.
The inverting and non inverting inputs selection is performed using the VPS_SEL and
VMS_SEL bit fields in the OPAMP control register. If the TCM_EN bit is cleared, the
selection is done using the VP_SEL and VM_SEL bit fields in the OPAMP control register.


RM0364 Rev 4 355/1124



363


**Operational amplifier (OPAMP)** **RM0364**


**Figure 95. Timer controlled Multiplexer mode**


|s|Col2|Col3|
|---|---|---|
|s|||
||||



**16.3.7** **OPAMP modes**







The operational amplifier inputs and outputs are all accessible on terminals. The amplifiers
can be used in multiple configuration environments:


      - Standalone mode (external gain setting mode)


      - Follower configuration mode


      - PGA modes


**Important note** : the amplifier output pin is directly connected to the output pad to minimize
the output impedance. It cannot be used as a general purpose I/O, even if the amplifier is
configured as a PGA and only connected to the ADC channel.


_Note:_ _The impedance of the signal must be maintained below a level which avoids the input_
_leakage to create significant artefacts (due to a resistive drop in the source). Please refer to_
_the electrical characteristics section in the datasheet for further details._


**Standalone mode (external gain setting mode)**


The external gain setting mode gives full flexibility to choose the amplifier configuration and
feedback networks. This mode is enabled by writing the VM_SEL bits in the OPAMPx_CR
register to 00 or 01, to connect the inverting inputs to one of the two possible I/Os.


356/1124 RM0364 Rev 4


**RM0364** **Operational amplifier (OPAMP)**


**Figure 96. Standalone mode: external gain setting mode**









1. This figure gives an example in an inverting configuration. Any other option is possible, including
comparator mode.


**Follower configuration mode**


The amplifier can be configured as a follower, by setting the VM_SEL bits to 11 in the
OPAMPx_CR register. This allows you for instance to buffer signals with a relatively high
impedance. In this case, the inverting inputs are free and the corresponding ports can be
used as regular I/Os.


RM0364 Rev 4 357/1124



363


**Operational amplifier (OPAMP)** **RM0364**


**Figure 97. Follower configuration**













1. This figure gives an example in an inverting configuration. Any other option is possible, including
comparator mode.


**Programmable Gain Amplifier mode**


The Programmable Gain Amplifier (PGA) mode is enabled by writing the VM_SEL bits to 10
in the OPAMPx_CR register. The gain is set using the PGA_GAIN bits which must be set to
0x00..0x11 for gains ranging from 2 to 16.


In this case, the inverting inputs are internally connected to the central point of a built-in gain
setting resistive network. _Figure 98: PGA mode, internal gain setting (x2/x4/x8/x16),_
_inverting input not used_ shows the internal connection in this mode.


An alternative option in PGA mode allows you to route the central point of the resistive
network on one of the I/Os connected to the non-inverting input. This is enabled using the
PGA_GAIN bits in OPAMPx_CR register:


      - 10xx values are setting the gain and connect the central point to one of the two
available inputs


      - 11xx values are setting the gain and connect the central point to the second available
input


This feature can be used for instance to add a low-pass filter to PGA, as shown in _Figure 99:_
_PGA mode, internal gain setting (x2/x4/x8/x16), inverting input used for filtering_ . Please note
that the cut-off frequency is changed if the gain is modified (refer to the electrical
characteristics section of the datasheet for details on resistive network elements.


358/1124 RM0364 Rev 4


**RM0364** **Operational amplifier (OPAMP)**


**Figure 98. PGA mode, internal gain setting** **(x2/x4/x8/x16), inverting input not used**









**Figure 99. PGA mode, internal gain setting (x2/x4/x8/x16), inverting input used for**
**filtering**









RM0364 Rev 4 359/1124



363


**Operational amplifier (OPAMP)** **RM0364**

##### **16.4 OPAMP registers**


**16.4.1** **OPAMP2 control register (OPAMP2_CSR)**


Address offset: 0x3C


Reset value: 0xXXXX 0000

|31|30|29|28 27 26 25 24|23 22 21 20 19|18|17 16|
|---|---|---|---|---|---|---|
|LOCK|OUT<br>CAL|TSTR<br>EF|TRIMOFFSETN|TRIMOFFSETP|USER_<br>TRIM|PGA_GAIN|
|rw|r|rw|rw|rw|rw|rw|


|15 14|13 12|11|10 9|8|7|6 5|4|3 2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|
|PGA_GAIN|CALSEL|CAL<br>ON|VPS_SEL|VMS_<br>SEL|TCM_<br>EN|VM_SEL|Res.|VP_SEL|FORCE<br>_VP|OPAMP<br>2EN|
|rw|rw|rw|rw|rw|rw|rw||rw|rw|rw|



Bit 31 **LOCK** : OPAMP 2 lock

This bit is write-once. It is set by software. It can only be cleared by a system reset.
This bit is used to configure the OPAMP2_CSR register as read-only.
0: OPAMP2_CSR is read-write.
1: OPAMP2_CSR is read-only.


Bit 30 **OUTCAL:**

OPAMP output status flag, when the OPAMP is used as comparator during calibration.
0: Non-inverting < inverting
1: Non-inverting > inverting.


Bit 29 **TSTREF:**

This bit is set and cleared by software. It is used to output the internal reference voltage
(V REFOPAMP2 ).
0: V REFOPAMP2 is output.
1: V REFOPAMP2 is not output.


Bits 28:24 **TRIMOFFSETN:** Offset trimming value (NMOS)


Bits 23:19 **TRIMOFFSETP:** Offset trimming value (PMOS)


Bit 18 **USER_TRIM:** User trimming enable.

This bit is used to configure the OPAMP offset.
0: User trimming disabled.
1: User trimming enabled.


Bits 17:14 **PGA_GAIN:** gain in PGA mode

0X00 = Non-inverting gain = 2
0X01 = Non-inverting gain = 4
0X10 = Non-inverting gain = 8
0X11 = Non-inverting gain = 16
1000 = Non-inverting gain = 2 - Internal feedback connected to VM0
1001 = Non-inverting gain = 4 - Internal feedback connected to VM0
1010 = Non-inverting gain = 8 - Internal feedback connected to VM0
1011 = Non-inverting gain = 16 - Internal feedback connected to VM0
1100 = Non-inverting gain = 2 - Internal feedback connected to VM1
1101 = Non-inverting gain = 4 - Internal feedback connected to VM1
1110 = Non-inverting gain = 8 - Internal feedback connected to VM1
1111 = Non-inverting gain = 16 - Internal feedback connected to VM1


360/1124 RM0364 Rev 4


**RM0364** **Operational amplifier (OPAMP)**


Bits 13:12 **CALSEL:** Calibration selection

This bit is set and cleared by software. It is used to select the offset calibration bus used to generate
the internal reference voltage when CALON = 1 or FORCE_VP= 1.
00 = V REFOPAMP = 3.3% V DDA
01 = V REFOPAMP = 10% V DDA
10 = V REFOPAMP = 50% V DDA
11 = V REFOPAMP = 90% V DDA


Bit 11 **CALON:** Calibration mode enable

This bit is set and cleared by software. It is used to enable the calibration mode connecting VM and
VP to the OPAMP internal reference voltage.

0: calibration mode disabled.

1: calibration mode enabled.


Bits 10:9 **VPS_SEL:** OPAMP2 Non inverting input secondary selection.

These bits are set and cleared by software. They are used to select the OPAMP2 non inverting input
when TCM_EN = 1.

00: Reserved

01: PB14 used as OPAMP2 non inverting input
10: PB0 used as OPAMP2 non inverting input
11: PA7 used as OPAMP2 non inverting input


Bit 8 **VMS_SEL:** OPAMP2 inverting input secondary selection

This bit is set and cleared by software. It is used to select the OPAMP2 inverting input when
TCM_EN = 1.
0: PC5 (VM0) used as OPAMP2 inverting input
1: PA5 (VM1) used as OPAMP2 inverting input


Bit 7 **TCM_EN:** Timer controlled Mux mode enable.

This bit is set and cleared by software. It is used to control automatically the switch between the
default selection (VP_SEL and VM_SEL) and the secondary selection (VPS_SEL and VMS_SEL) of
the inverting and non inverting inputs.


Bits 6:5 **VM_SEL:** OPAMP2 inverting input selection.

Theses bits are set and cleared by software. They are used to select the OPAMP2 inverting input.
00: PC5 (VM0) used as OPAMP2 inverting input
01: PA5 (VM1) used as OPAMP2 inverting input
10: Resistor feedback output (PGA mode)

11: follower mode


Bit 4 Reserved, must be kept at reset value.


RM0364 Rev 4 361/1124



363


**Operational amplifier (OPAMP)** **RM0364**


Bits 3:2 **VP_SEL:** OPAMP2 non inverting input selection.

Theses bits are set/reset by software. They are used to select the OPAMP2 non inverting input.

00: Reserved

01: PB14 used as OPAMP2 non inverting input
10: PB0 used as OPAMP2 non inverting input
11: PA7 used as OPAMP2 non inverting input


Bit 1 **FORCE_VP:**

This bit forces a calibration reference voltage on non-inverting input and disables external
connections.

0: Normal operating mode. Non-inverting input connected to inputs.
1: Calibration mode. Non-inverting input connected to calibration reference voltage.


Bit 0 **OPAMP2EN:** OPAMP2 enable.

This bit is set and cleared by software. It is used to select the OPAMP2.

0: OPAMP2 is disabled.

1: OPAMP2 is enabled.


362/1124 RM0364 Rev 4


**RM0364** **Operational amplifier (OPAMP)**


**16.4.2** **OPAMP register map**


The following table summarizes the OPAMP registers.


**Table 59. OPAMP register map and reset values**

|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x3C|**OPAMP2_CSR**<br>|LOCK<br>|OUTCAL<br>|TSTREF<br>|TRIMOFFSETN<br><br><br><br><br>|TRIMOFFSETN<br><br><br><br><br>|TRIMOFFSETN<br><br><br><br><br>|TRIMOFFSETN<br><br><br><br><br>|TRIMOFFSETN<br><br><br><br><br>|TRIMOFFSETP<br><br><br><br><br>|TRIMOFFSETP<br><br><br><br><br>|TRIMOFFSETP<br><br><br><br><br>|TRIMOFFSETP<br><br><br><br><br>|TRIMOFFSETP<br><br><br><br><br>|USER_TRIM<br>|PGA_GAIN<br><br><br><br>|PGA_GAIN<br><br><br><br>|PGA_GAIN<br><br><br><br>|PGA_GAIN<br><br><br><br>|CALSEL<br><br>|CALSEL<br><br>|CALON<br>|VPS_SEL<br><br>|VPS_SEL<br><br>|VMS_SEL<br>|TCM_EN<br>|VM_SEL<br><br>|VM_SEL<br><br>|Res|VP_SEL<br><br>|VP_SEL<br><br>|FORCE_VP<br>|OPAMP2EN<br>|
|0x3C|~~Reset value~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~X~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~|~~0~~||~~0~~|~~0~~|~~0~~|~~0~~|



Refer to _Section 2.2 on page 47_ for the register boundary addresses.


RM0364 Rev 4 363/1124



363


