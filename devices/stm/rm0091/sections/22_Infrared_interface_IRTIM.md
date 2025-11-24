**RM0091** **Infrared interface (IRTIM)**

# **22 Infrared interface (IRTIM)**


An infrared interface (IRTIM) for remote control is available on the device. It can be used
with an infrared LED to perform remote control functions.


It uses internal connections withUSART1, USART4 (on STM32F03x and STM32F05x) or
USART2 (STM32F07x), TIM16 and TIM17 as shown in _Figure 211_ .


To generate the infrared remote control signals, the IR interface must be enabled and TIM16
channel 1 (TIM16_OC1) and TIM17 channel 1 (TIM17_OC1) must be properly configured to
generate correct waveforms.


The infrared receiver can be implemented easily through a basic input capture mode.


**Figure 211. IRTIM internal hardware connections with TIM16 and TIM17**











1. USART1 and USART4 can be linked to IRTIM on STM32F09x devices only.


All standard IR pulse modulation modes can be obtained by programming the two timer
output compare channels.


TIM17 is used to generate the high frequency carrier signal, while TIM16 generates the
modulation envelope.


On STM32F09x devices, the modulation envelope can also be created from USART1 or
USART4 transmitter line, upon setting appropriately the IR_MOD[1:0] bits in
SYSCFG_CFGR1 register.


The infrared function is output on the IR_OUT pin. The activation of this function is done
through the GPIOx_AFRx register by enabling the related alternate function bit.


The high sink LED driver capability (only available on the PB9 pin) can be activated through
the I2C_PB9_FMP bit in the SYSCFG_CFGR1 register and used to sink the high current
needed to directly control an infrared LED.


For code example refer to the Appendix section _A.10.1: TIM16 and TIM17 configuration_
_code example_ .


RM0091 Rev 10 573/1017



573


