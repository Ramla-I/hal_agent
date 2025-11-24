**Infrared interface (IRTIM)** **RM0360**

# **18 Infrared interface (IRTIM)**


An infrared interface (IRTIM) for remote control is available on the device. It can be used
with an infrared LED to perform remote control functions.


It uses internal connections withTIM16 as shown in _Figure 193_ .


To generate the infrared remote control signals, the IR interface must be enabled and TIM16
channel 1 (TIM16_OC1) must be properly configured to generate correct waveforms.


The infrared receiver can be implemented easily through a basic input capture mode.


**Figure 193. IRTIM internal hardware connections**


All standard IR pulse modulation modes can be obtained by programming the two timer
output compare channels.


is used to generate the high frequency carrier signal, while TIM16 generates the modulation
envelope.


The infrared function is output on the IR_OUT pin. The activation of this function is done
through the GPIOx_AFRx register by enabling the related alternate function bit.


The high sink LED driver capability (only available on the PB9 pin) can be activated through
the PB9_FMP bit in the SYSCFG_CFGR1 register and used to sink the high current needed
to directly control an infrared LED.


For code example refer to the Appendix section _A.9.1: TIM16 and TIM17 configuration_ .


468/775 RM0360 Rev 5


