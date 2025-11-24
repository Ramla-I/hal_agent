**Infrared interface (IRTIM)** **RM0490**

# **21 Infrared interface (IRTIM)**


An infrared interface (IRTIM) for remote control is available on the device. It can be used
with an infrared LED to perform remote control functions.


It uses internal connections with USART1, USART2, TIM16, and TIM17 as shown in
_Figure 217_ .


To generate the infrared remote control signals, the IR interface must be enabled and TIM16
channel 1 (TIM16_OC1) and TIM17 channel 1 (TIM17_OC1) must be properly configured to
generate correct waveforms.


The infrared receiver can be implemented easily through a basic input capture mode.


**Figure 217. IRTIM internal hardware connections with TIM16 and TIM17  .**









All standard IR pulse modulation modes can be obtained by programming the two timer
output compare channels.


TIM17 is used to generate the high frequency carrier signal, while TIM16 or alternatively
USART1 or USART42 generates the modulation envelope according to the setting of the
IR_MOD[1:0] bits in the SYSCFG_CFGR1 register.


The polarity of the output signal from IRTIM is controlled by the IR_POL bit in the
SYSCFG_CFGR1 register and can be inverted by setting of this bit.


The infrared function is output on the IR_OUT pin. The activation of this function is done
through the GPIOx_AFRx register by enabling the related alternate function bit.


The high sink LED driver capability (only available on the PB9 and PC14 pins) can be
activated through the I2C_PB9_FMP bit and/or I2C_PC14_FMP bit in the SYSCFG_CFGR1
register and used to sink the high current needed to directly control an infrared LED.


630/1027 RM0490 Rev 5


