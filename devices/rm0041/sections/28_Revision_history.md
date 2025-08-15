**RM0041** **Revision history**

## **28 Revision history**


**Table 161. Document revision history**





|Date|Revision|Changes|
|---|---|---|
|26-Feb-2010|1|Initial release.|
|04-Jun-2010|2|Corrected description of TIMx_CCER register in_Section 12.4.9 on page_<br>_272_ and_Section 13.4.9 on page 334_<br>Updated_Section 14.3.5: Input capture mode on page 353_<br>Added method 1 and 2 in_Section 22.3.3: I2C master mode_<br>Updated note in POS bit description_Section 22.6: I2C registers_|
|12-Oct-2010|3|Updated for high density value line devices<br>Updated_Section 20.5.2: Supported memories and transactions_<br>Added_Section 14: General-purpose timers (TIM12/13/14)_<br>Added_Section 20: Flexible static memory controller (FSMC)_|
|21-Jul-2011|4|Corrected_Figure 2: High density value line system architecture on_<br>_page 35_<br>Updated SPI table in_Section 7.1.11: GPIO configurations for device_<br>_peripherals on page 109_<br>Updated bit descriptions in_Section 7.3.1: Clock control register (RCC_CR)_<br>_on page 99_ and_Section 8.3.1: Clock control register (RCC_CR) on_<br>_page 132_<br>EXTI:<br>Updated_Figure 18: External interrupt/event controller block diagram_<br>**ADC**:<br>Corrected_Table 59: External trigger for regular channels for ADC1_ and<br>_Table 60: External trigger for injected channels for ADC1 on page 171_<br>**TIMERS:**<br>Removed wrong references to 32-bit counter in _Section 13.4: TIMx2 to_<br>_TIM5 registers on page 321_<br>TIM1&TIM8: Updated example and definition of DBL bits in<br>_Section 12.4.19: TIM1 DMA control register (TIMx_DCR)_. Added example<br>related to DMA burst feature and description of DMAB bits in<br>_Section 12.4.20: TIM1 DMA address for full transfer (TIMx_DMAR)_. <br>TIM2 to TIM5 and TIM15 to 17: added example and updated definition of<br>DBL bits in_Section 13.4.17: TIMx DMA control register (TIMx_DCR)_. <br>Added example related to DMA burst feature and description of DMAB bits<br>in_Section 13.4.18: TIMx DMA address for full transfer (TIMx_DMAR)_. <br>Updated definition of DBL bits in_Section 13.4.17: TIMx DMA control_<br>_register (TIMx_DCR)_.<br>In_Section 12.3.3: Repetition counter_ Added paragraph “In Center aligned<br>mode, for odd values of RCR, ....”<br>Modified_Figure 167: Update rate examples depending on mode and_<br>_TIMx_RCR register settings on page 398_.<br>**WWDG**<br>Updated_Section 19.2: WWDG main features_.<br>Updated_Section 19.3: WWDG functional description_ to remove paragraph<br>related to counter reload using EWI interrupt.|


RM0041 Rev 6 703/709



706


**Revision history** **RM0041**


**Table 161. Document revision history** **(continued)**






|Date|Revision|Changes|
|---|---|---|
|21-Jul-2011|4<br>continued|**I2C:**<br>Updated BERR bit description in_Section 22.6.6: I2C Status register 1_<br>_(I2C_SR1)_.<br>Updated_Note:_ in_Section 22.6.8: I2C Clock control register (I2C_CCR)_.<br>Added note 3 below_Figure 235: Transfer sequence diagram for slave_<br>_transmitter on page 570_. Added note below_Figure 236: Transfer sequence_<br>_diagram for slave receiver on page 571_. Modified_Section : Closing slave_<br>_communication on page 571_. Modified STOPF, ADDR, bit description in<br>_Section 22.6.6: I2C Status register 1 (I2C_SR1) on page 591_. Modified<br>_Section 22.6.7: I2C Status register 2 (I2C_SR2)_. <br>**USART:**<br>Updated_Figure 251: Mute mode using address mark detection_ for<br>Address =1.**SPI:**<br>Modified_Slave select (NSS) pin management on page 539_ and note on<br>NSS in_Section 21.3.3: Configuring the SPI in master mode_<br>**FSMC:**<br>Updated description of DATLAT, DATAST, and ADDSET bits in<br>_SRAM/NOR-Flash chip-select timing registers 1..4 (FSMC_BTR1..4)_.<br>Updated byte select description in_Section 20.5.2: Supported memories_<br>_and transactions on page 501_|
|10-Jun-2016|5|Added_SCL master clock generation_ and_Note:_ to_Entering Stop mode_.<br>Added_Table 88: Minimum and maximum timeout values @24 MHz_<br>_(fPCLK1)_.<br>Updated_Table 74: TIMx Internal trigger connection_, _Table 79: TIMx_<br>_Internal trigger connection_, _Table 92: Programmable NOR/PSRAM access_<br>_parameters_, _Table 97: NOR flash/PSRAM controller: example of_<br>_supported memories and transactions_ and_Table 114: FSMC_BCRx bit_<br>_fields_.<br>Updated_Figure 5: Power on reset/power down reset waveform_, _Figure 6:_<br>_PVD thresholds_, _Figure 7: Simplified diagram of the reset circuit_, <br>_Figure 40: Advanced-control timer block diagram_, _Figure 68: Output stage_<br>_of capture/compare channel (channel 1 to 3)_, _Figure 78: Clearing TIMx_<br>_OCxREF_, _Figure 121: Clearing TIMx OCxREF_, _Figure 128: Master/Slave_<br>_timer example_, _Figure 158: TIM16 and TIM17 block diagram_, _Figure 173:_<br>_Output stage of capture/compare channel (channel 1)_, _Figure 200:_<br>_Watchdog block diagram_, _Figure 201: Window watchdog timing diagram_, <br>_Figure 202: FSMC block diagram_, _Figure 217: Asynchronous wait during a_<br>_read access_, _Figure 218: Asynchronous wait during a write access_ and<br>_Figure 220: Synchronous multiplexed read mode - NOR, PSRAM (CRAM)_.<br>Updated caption of_Figure 101: Counter timing diagram, Update event_ and<br>of_Figure 208: Mode2 and mode B read accesses_.|



704/709 RM0041 Rev 6


**RM0041** **Revision history**


**Table 161. Document revision history** **(continued)**





|Date|Revision|Changes|
|---|---|---|
|10-Jun-2016|5<br>continued|Updated:<br>–_ Introduction_<br>–_ Section 2.1: System architecture_, _Section 2.3: Memory map_<br>–_ Section 25.6.1: MCU device ID code_.<br>–_ Section 4.4.2: Power control/status register (PWR_CSR)_, <br>–_ Section 6.1.2: Power reset_, _Section 6.2.8: RTC clock_<br>–_ Section 7.2.3: Port input data register (GPIOx_IDR) (x=A..G)_ and<br>_Section 7.2.4: Port output data register (GPIOx_ODR) (x=A..G)_<br>–_ Section 8.2: External interrupt/event controller (EXTI)_, _Section 8.3.5:_<br>_Software interrupt event register (EXTI_SWIER)_ and_Section 8.3.6:_<br>_Pending register (EXTI_PR)_.<br>–_ Section 10.11.7: ADC watchdog high threshold register (ADC_HTR)_ and<br>_Section 10.11.8: ADC watchdog low threshold register (ADC_LTR)_.<br>Renumbered former_Section 14.3_ into_Section 14.2.2_.<br>Updated:<br>–_ Section 12.3.1: Time-base unit_, _Section 12.3.2: Counter modes_, <br>_Section 12.3.6: Input capture mode_, _Section 12.3.11: Complementary_<br>_outputs and dead-time insertion_, _Section 12.3.13: Clearing the OCxREF_<br>_signal on an external event_, _Section 12.3.16: Encoder interface mode_, <br>_Section 12.3.18: Interfacing with Hall sensors_, _Section 12.4.3: TIM1_<br>_slave mode control register (TIMx_SMCR)_, _Section 12.4.2: TIM1 control_<br>_register 2 (TIMx_CR2)_, _Section 12.4.7: TIM1 capture/compare mode_<br>_register 1 (TIMx_CCMR1)_, _Section 12.4.12: TIM1 auto-reload register_<br>_(TIMx_ARR)_, _Section 13.3.5: Input capture mode_, _Section 13.3.9: PWM_<br>_mode_, _Section 13.3.11: Clearing the OCxREF signal on an external_<br>_event_, _Section 13.3.12: Encoder interface mode_, _Section 13.3.15: Timer_<br>_synchronization_, _Section 13.4.2: TIMx control register 2 (TIMx_CR2)_, <br>_Section 13.4.3: TIMx slave mode control register (TIMx_SMCR)_, <br>_Section 13.4.7: TIMx capture/compare mode register 1 (TIMx_CCMR1)_, <br>_Section 14.3.1: Time-base unit_, _Section 14.3.5: Input capture mode_, <br>_Section 14.3.9: PWM mode_, _Section 14.4.7: TIM capture/compare mode_<br>_register 1 (TIMx_CCMR1)_, _Section 14.5.5: TIM13/14 capture/compare_<br>_mode register 1 (TIMx_CCMR1)_, _Section 15.2: TIM15 main features_, <br>_Section 15.3: TIM16 and TIM17 main features_, _Section 15.4.1: Time-_<br>_base unit_, _Section 15.4.2: Counter modes_, _Section 15.4.3: Repetition_<br>_counter_, _Section 15.4.6: Input capture mode_, _Section 15.4.10: PWM_<br>_mode_, _Section 15.4.11: Complementary outputs and dead-time_<br>_insertion_, _Section 15.5.3: TIM15 slave mode control register_<br>_(TIM15_SMCR)_, _Section 15.5.7: TIM15 capture/compare mode register_<br>_1 (TIM15_CCMR1)_, _Section 15.5.11: TIM15 auto-reload register_<br>_(TIM15_ARR)_, _Section 15.5.15: TIM15 break and dead-time register_<br>_(TIM15_BDTR)_, _Section 15.6.6: TIM16&TIM17 capture/compare mode_<br>_register 1 (TIMx_CCMR1)_, _Section 15.6.10: TIM16&TIM17 auto-reload_<br>_register (TIMx_ARR)_ and_Section 15.6.13: TIM16&TIM17 break and_<br>_dead-time register (TIMx_BDTR)_.<br>Updated:<br>–_ Section 19.4: How to program the watchdog timeout_.|


RM0041 Rev 6 705/709



706


**Revision history** **RM0041**


**Table 161. Document revision history** **(continued)**






|Date|Revision|Changes|
|---|---|---|
|10-Jun-2016|5<br>continued|Updated:<br>–_ Mode 1 - SRAM/PSRAM (CRAM)_, _Asynchronous static memories (NOR_<br>_flash memory, PSRAM, SRAM)_,,_Mode 2/B - NOR flash_, _SRAM/NOR-_<br>_Flash chip-select timing registers 1..4 (FSMC_BTR1..4)_, _SRAM/NOR-_<br>_Flash write timing registers 1..4 (FSMC_BWTR1..4)_, _SRAM/NOR-flash_<br>_chip-select control registers 1..4 (FSMC_BCR1..4)_, _Section 20.5.4: NOR_<br>_flash/PSRAM controller asynchronous transactions_ and_Section 20.5.6:_<br>_NOR/PSRAM control registers_.<br>Replaced M/SL with MSL throughout_Section 22: Inter-integrated circuit_<br>_(I2C) interface_, and updated_Section 22.6.1: I2C Control register 1_<br>_(I2C_CR1)_, _Section 22.6.2: I2C Control register 2 (I2C_CR2)_ and<br>_Section 22.6.9: I2C TRISE register (I2C_TRISE)_.<br>Replaced nCTS with CTS, nRTS with RTS and SCLK with CK throughout<br>_Section 27: Universal synchronous asynchronous receiver transmitter_<br>_(USART)_.<br>Updated:<br>–_ Section 27.3.8: LIN (local interconnection network) mode_, _Selecting the_<br>_proper oversampling method_, _How to derive USARTDIV from_<br>_USART_BRR register values when OVER8=0_ and_How to derive_<br>_USARTDIV from USART_BRR register values when OVER8=1_ and<br>_Section 27.6.6: Control register 3 (USART_CR3)_.|
|12-Dec-2022|6|Updated_Introduction_, _Section 4.4.1: Power control register (PWR_CR)_, <br>_Section 5.2: BKP main features_, _Section 5.4: BKP registers_, <br>_Section 12.3.21: Debug mode_, _Section 12.4.7: TIM1 capture/compare_<br>_mode register 1 (TIMx_CCMR1)_, _Section 12.4.14: TIM1 capture/compare_<br>_register 1 (TIMx_CCR1)_, _Section 12.4.17: TIM1 capture/compare register_<br>_4 (TIMx_CCR4)_, _Section 12.4.20: TIM1 DMA address for full transfer_<br>_(TIMx_DMAR)_, _Section 13.4.7: TIMx capture/compare mode register 1_<br>_(TIMx_CCMR1)_, sections_13.4.13_ to_13.4.16_, _Section 14.4.7: TIM_<br>_capture/compare mode register 1 (TIMx_CCMR1)_, sections_14.4.11_ to<br>_14.4.13_, _Section 14.5.9: TIM13/14 auto-reload register (TIMx_ARR)_, <br>_Section 14.5.10: TIM13/14 capture/compare register 1 (TIMx_CCR1)_, <br>_Section 15.5.5: TIM15 status register (TIM15_SR)_, _Section 15.6.12:_<br>_TIM16&TIM17 capture/compare register 1 (TIMx_CCR1)_, and<br>_Section 19.4: How to program the watchdog timeout_.<br>Added_Section 1.4: General information_ and_Section 27: Important security_<br>_notice_.<br>Updated_Table 14: BKP register map and reset values_ and_Table 69: TIM1_<br>_register map and reset values_.<br>Updated_Figure 6: PVD thresholds_, _Figure 40: Advanced-control timer_<br>_block diagram_, _Figure 134: General-purpose timer block diagram (TIM12)_, <br>and_Figure 259: Parity error detection using the 1.5 stop bits_.<br>Minor text edits across the whole document.|



706/709 RM0041 Rev 6


**Index** **RM0041**

# **Index**



**A**


ADC_CR1 . . . . . . . . . . . . . . . . . . . . . . . . . . .176
ADC_CR2 . . . . . . . . . . . . . . . . . . . . . . . . . . .177
ADC_DR . . . . . . . . . . . . . . . . . . . . . . . . . . . .187
ADC_HTR . . . . . . . . . . . . . . . . . . . . . . . . . . .182
ADC_JDRx . . . . . . . . . . . . . . . . . . . . . . . . . . .187
ADC_JOFRx . . . . . . . . . . . . . . . . . . . . . . . . .181
ADC_JSQR . . . . . . . . . . . . . . . . . . . . . . . . . .186
ADC_LTR . . . . . . . . . . . . . . . . . . . . . . . . . . . .182
ADC_SMPR1 . . . . . . . . . . . . . . . . . . . . . . . . .180
ADC_SMPR2 . . . . . . . . . . . . . . . . . . . . . . . . .181
ADC_SQR1 . . . . . . . . . . . . . . . . . . . . . . . . . .183
ADC_SQR2 . . . . . . . . . . . . . . . . . . . . . . . . . .184
ADC_SQR3 . . . . . . . . . . . . . . . . . . . . . . . . . .185
ADC_SR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .175
AFIO_EVCR . . . . . . . . . . . . . . . . . . . . . . . . . .123
AFIO_EXTICR1 . . . . . . . . . . . . . . . . . . . . . . .126
AFIO_EXTICR2 . . . . . . . . . . . . . . . . . . . . . . .126
AFIO_EXTICR3 . . . . . . . . . . . . . . . . . . . . . . .127
AFIO_EXTICR4 . . . . . . . . . . . . . . . . . . . . . . .127
AFIO_MAPR . . . . . . . . . . . . . . . . . . . . . . . . .124
AFIO_MAPR2 . . . . . . . . . . . . . . . . . . . . . . . .128


**B**


BKP_CR . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .67
BKP_CSR . . . . . . . . . . . . . . . . . . . . . . . . . . . .67
BKP_DRx . . . . . . . . . . . . . . . . . . . . . . . . . . . . .66
BKP_RTCCR . . . . . . . . . . . . . . . . . . . . . . . . . .66


**C**


CEC_CFGR . . . . . . . . . . . . . . . . . . . . . . . . . .663
CEC_CSR . . . . . . . . . . . . . . . . . . . . . . . . . . .666
CEC_ESR . . . . . . . . . . . . . . . . . . . . . . . . . . .665
CEC_OAR . . . . . . . . . . . . . . . . . . . . . . . . . . .664
CEC_PRES . . . . . . . . . . . . . . . . . . . . . . . . . .664
CEC_RXD . . . . . . . . . . . . . . . . . . . . . . . . . . .667
CEC_TXD . . . . . . . . . . . . . . . . . . . . . . . . . . .667
CRC_DR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .48
CRC_IDR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .48


**D**


DAC_CR . . . . . . . . . . . . . . . . . . . . . . . . . . . .202
DAC_DHR12L1 . . . . . . . . . . . . . . . . . . . . . . .206
DAC_DHR12L2 . . . . . . . . . . . . . . . . . . . . . . .207
DAC_DHR12LD . . . . . . . . . . . . . . . . . . . . . . .208



DAC_DHR12R1 . . . . . . . . . . . . . . . . . . . . . . 205
DAC_DHR12R2 . . . . . . . . . . . . . . . . . . . . . . 207
DAC_DHR12RD . . . . . . . . . . . . . . . . . . . . . . 208
DAC_DHR8R1 . . . . . . . . . . . . . . . . . . . . . . . 206
DAC_DHR8R2 . . . . . . . . . . . . . . . . . . . . . . . 207
DAC_DHR8RD . . . . . . . . . . . . . . . . . . . . . . . 209
DAC_DOR1 . . . . . . . . . . . . . . . . . . . . . . . . . . 209
DAC_DOR2 . . . . . . . . . . . . . . . . . . . . . . . . . . 209
DAC_SR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 210
DAC_SWTRIGR . . . . . . . . . . . . . . . . . . . . . . 205
DBGMCU_CR . . . . . . . . . . . . . . . . . . . . . . . . 689
DBGMCU_IDCODE . . . . . . . . . . . . . . . . . . . 677
DMA_CCRx . . . . . . . . . . . . . . . . . . . . . . . . . . 156
DMA_CMARx . . . . . . . . . . . . . . . . . . . . . . . . 158
DMA_CNDTRx . . . . . . . . . . . . . . . . . . . . . . . 157
DMA_CPARx . . . . . . . . . . . . . . . . . . . . . . . . . 158
DMA_IFCR . . . . . . . . . . . . . . . . . . . . . . . . . . 155
DMA_ISR . . . . . . . . . . . . . . . . . . . . . . . . . . . 154


**E**


EXTI_EMR . . . . . . . . . . . . . . . . . . . . . . . . . . 140
EXTI_FTSR . . . . . . . . . . . . . . . . . . . . . . . . . . 141
EXTI_IMR . . . . . . . . . . . . . . . . . . . . . . . . . . . 140
EXTI_PR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 142
EXTI_RTSR . . . . . . . . . . . . . . . . . . . . . . . . . . 141
EXTI_SWIER . . . . . . . . . . . . . . . . . . . . . . . . . 142


**F**


FSMC_BCR1..4 . . . . . . . . . . . . . . . . . . . . . . . 526
FSMC_BTR1..4 . . . . . . . . . . . . . . . . . . . . . . . 529
FSMC_BWTR1..4 . . . . . . . . . . . . . . . . . . . . . 532


**G**


GPIOx_BRR . . . . . . . . . . . . . . . . . . . . . . . . . 116
GPIOx_BSRR . . . . . . . . . . . . . . . . . . . . . . . . 115
GPIOx_CRH . . . . . . . . . . . . . . . . . . . . . . . . . 114
GPIOx_CRL . . . . . . . . . . . . . . . . . . . . . . . . . 113
GPIOx_IDR . . . . . . . . . . . . . . . . . . . . . . . . . . 114
GPIOx_LCKR . . . . . . . . . . . . . . . . . . . . . . . . 116
GPIOx_ODR . . . . . . . . . . . . . . . . . . . . . . . . . 115


**I**


I2C_CCR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 595
I2C_CR1 . . . . . . . . . . . . . . . . . . . . . . . . . . . . 586
I2C_CR2 . . . . . . . . . . . . . . . . . . . . . . . . . . . . 588



707/709 RM0041 Rev 6


**RM0041** **Index**



I2C_DR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .591
I2C_OAR1 . . . . . . . . . . . . . . . . . . . . . . . . . . .590
I2C_OAR2 . . . . . . . . . . . . . . . . . . . . . . . . . . .590
I2C_SR1 . . . . . . . . . . . . . . . . . . . . . . . . . . . . .591
I2C_SR2 . . . . . . . . . . . . . . . . . . . . . . . . . . . . .594
I2C_TRISE . . . . . . . . . . . . . . . . . . . . . . . . . . .596
IWDG_KR . . . . . . . . . . . . . . . . . . . . . . . . . . .483
IWDG_PR . . . . . . . . . . . . . . . . . . . . . . . . . . .483
IWDG_RLR . . . . . . . . . . . . . . . . . . . . . . . . . .484
IWDG_SR . . . . . . . . . . . . . . . . . . . . . . . . . . .484


**P**


PWR_CR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .60
PWR_CSR . . . . . . . . . . . . . . . . . . . . . . . . . . . .62


**R**


RCC_AHBENR . . . . . . . . . . . . . . . . . . . . . . . .90
RCC_APB1ENR . . . . . . . . . . . . . . . . . . . . . . . .94
RCC_APB1RSTR . . . . . . . . . . . . . . . . . . . . . .88
RCC_APB2ENR . . . . . . . . . . . . . . . . . . . . . . . .92
RCC_APB2RSTR . . . . . . . . . . . . . . . . . . . . . .86
RCC_BDCR . . . . . . . . . . . . . . . . . . . . . . . . . . .97
RCC_CFGR . . . . . . . . . . . . . . . . . . . . . . . . . . .82
RCC_CFGR2 . . . . . . . . . . . . . . . . . . . . . . . . .100
RCC_CIR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .84
RCC_CR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .80
RCC_CSR . . . . . . . . . . . . . . . . . . . . . . . . . . . .98
RTC_ALRH . . . . . . . . . . . . . . . . . . . . . . . . . .479
RTC_ALRL . . . . . . . . . . . . . . . . . . . . . . . . . . .479
RTC_CNTH . . . . . . . . . . . . . . . . . . . . . . . . . .478
RTC_CNTL . . . . . . . . . . . . . . . . . . . . . . . . . .478
RTC_CRH . . . . . . . . . . . . . . . . . . . . . . . . . . .474
RTC_CRL . . . . . . . . . . . . . . . . . . . . . . . . . . . .475
RTC_DIVH . . . . . . . . . . . . . . . . . . . . . . . . . . .477
RTC_DIVL . . . . . . . . . . . . . . . . . . . . . . . . . . .477
RTC_PRLH . . . . . . . . . . . . . . . . . . . . . . . . . .476
RTC_PRLL . . . . . . . . . . . . . . . . . . . . . . . . . . .477


**S**


SPI_CR1 . . . . . . . . . . . . . . . . . . . . . . . . . . . .559
SPI_CR2 . . . . . . . . . . . . . . . . . . . . . . . . . . . .560
SPI_CRCPR . . . . . . . . . . . . . . . . . . . . . . . . . .563
SPI_DR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .562
SPI_RXCRCR . . . . . . . . . . . . . . . . . . . . . . . .563
SPI_SR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .561
SPI_TXCRCR . . . . . . . . . . . . . . . . . . . . . . . .564


**T**


TIM15_ARR . . . . . . . . . . . . . . . . . . . . . . . . . .429



TIM15_BDTR . . . . . . . . . . . . . . . . . . . . . . . . 431
TIM15_CCER . . . . . . . . . . . . . . . . . . . . . . . . 426
TIM15_CCMR1 . . . . . . . . . . . . . . . . . . . . . . . 423
TIM15_CCR1 . . . . . . . . . . . . . . . . . . . . . . . . 430
TIM15_CCR2 . . . . . . . . . . . . . . . . . . . . . . . . 431
TIM15_CNT . . . . . . . . . . . . . . . . . . . . . . . . . . 429
TIM15_CR1 . . . . . . . . . . . . . . . . . . . . . . . . . . 416
TIM15_CR2 . . . . . . . . . . . . . . . . . . . . . . . . . . 417
TIM15_DCR . . . . . . . . . . . . . . . . . . . . . . . . . 433
TIM15_DIER . . . . . . . . . . . . . . . . . . . . . . . . . 420
TIM15_DMAR . . . . . . . . . . . . . . . . . . . . . . . . 434
TIM15_EGR . . . . . . . . . . . . . . . . . . . . . . . . . 422
TIM15_PSC . . . . . . . . . . . . . . . . . . . . . . . . . . 429
TIM15_RCR . . . . . . . . . . . . . . . . . . . . . . . . . 430
TIM15_SMCR . . . . . . . . . . . . . . . . . . . . . . . . 418
TIM15_SR . . . . . . . . . . . . . . . . . . . . . . . . . . . 421
TIMx_ARR . . . . . . . . . . . . . . .336, 375, 385, 467
TIMx_BDTR . . . . . . . . . . . . . . . . . . . . . . 278, 450
TIMx_CCER . . . . . . . . .272, 334, 374, 384, 445
TIMx_CCMR1 . . . . . . . .268, 330, 371, 381, 443
TIMx_CCMR2 . . . . . . . . . . . . . . . . . . . . 270, 333
TIMx_CCR1 . . . . . . . . . .276, 336, 376, 386, 449
TIMx_CCR2 . . . . . . . . . . . . . . . . . . 277, 337, 376
TIMx_CCR3 . . . . . . . . . . . . . . . . . . . . . . 277, 337
TIMx_CCR4 . . . . . . . . . . . . . . . . . . . . . . 278, 337
TIMx_CNT . . . . . . .274, 335, 375, 385, 448, 466
TIMx_CR1 . . . . . . .257, 321, 364, 379, 437, 463
TIMx_CR2 . . . . . . . . . . .258, 323, 365, 438, 465
TIMx_DCR . . . . . . . . . . . . . . . . . . . 280, 338, 451
TIMx_DIER . . . . . .263, 326, 367, 380, 440, 465
TIMx_DMAR . . . . . . . . . . . . . . . . . 281, 338, 452
TIMx_EGR . . . . . . .266, 329, 370, 381, 442, 466
TIMx_PSC . . . . . . .274, 335, 375, 385, 448, 467
TIMx_RCR . . . . . . . . . . . . . . . . . . . . . . . 276, 449
TIMx_SMCR . . . . . . . . . . . . . . . . . 261, 324, 366
TIMx_SR . . . . . . . .265, 327, 369, 380, 441, 466


**U**


USART_BRR . . . . . . . . . . . . . . . . . . . . . . . . . 639
USART_CR1 . . . . . . . . . . . . . . . . . . . . . . . . . 639
USART_CR2 . . . . . . . . . . . . . . . . . . . . . . . . . 642
USART_CR3 . . . . . . . . . . . . . . . . . . . . . . . . . 643
USART_DR . . . . . . . . . . . . . . . . . . . . . . . . . . 639
USART_GTPR . . . . . . . . . . . . . . . . . . . . . . . 645
USART_SR . . . . . . . . . . . . . . . . . . . . . . . . . . 636


**W**


WWDG_CFR . . . . . . . . . . . . . . . . . . . . . . . . . 492
WWDG_CR . . . . . . . . . . . . . . . . . . . . . . . . . . 491
WWDG_SR . . . . . . . . . . . . . . . . . . . . . . . . . . 492



RM0041 Rev 6 708/709


**RM0041**


**IMPORTANT NOTICE – PLEASE READ CAREFULLY**


STMicroelectronics NV and its subsidiaries (“ST”) reserve the right to make changes, corrections, enhancements, modifications, and
improvements to ST products and/or to this document at any time without notice. Purchasers should obtain the latest relevant information on
ST products before placing orders. ST products are sold pursuant to ST’s terms and conditions of sale in place at the time of order
acknowledgement.


Purchasers are solely responsible for the choice, selection, and use of ST products and ST assumes no liability for application assistance or
the design of Purchasers’ products.


No license, express or implied, to any intellectual property right is granted by ST herein.


Resale of ST products with provisions different from the information set forth herein shall void any warranty granted by ST for such product.


ST and the ST logo are trademarks of ST. For additional information about ST trademarks, please refer to _www.st.com/trademarks_ . All other
product or service names are the property of their respective owners.


Information in this document supersedes and replaces information previously supplied in any prior versions of this document.


© 2022 STMicroelectronics – All rights reserved


RM0041 Rev 6 709/709



709


