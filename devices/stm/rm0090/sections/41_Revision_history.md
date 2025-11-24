**Revision history** **RM0090**

## **41 Revision history**


**Table 316. Document revision history**






|Date|Version|Changes|
|---|---|---|
|15-Sep-2011|1|Initial release.|
|19-Oct-2012|2|Updated reference documents and added Table 1: Applicable products on cover<br>page.<br>**MEMORY**:<br>Updated Section 2: Memory and bus architecture.<br>**PWR**:<br>Updated VDDA and VREF+ decoupling capacitor in Figure 7: Power supply<br>overview.<br>VOSRDY bit changed to read-only in Section 5.4.3: PWR power control/status<br>register (PWR_CSR).<br>Removed VDDA in Section 5.2.3: Programmable voltage detector (PVD) and<br>remove VDDA in PVDO bit description (Section 5.4.3: PWR power control/status<br>register (PWR_CSR)).<br>**RCC**:<br>Updated Figure 20: Simplified diagram of the reset circuit and minimum reset pulse<br>duration guaranteed by pulse generator restricted to internal reset sources.<br>**GPIOs**:<br>Updated Section 8.3.1: General-purpose I/O (GPIO).|
|19-Oct-2012|2|**DMA**:<br>Updated direct mode description in Section 10.2: DMA main features.<br>Updated direct mode description in Section : Memory-to-peripheral mode, and<br>Section 10.3.12: FIFO/: Direct mode.<br>Updated register access in Section 10.5: DMA registers.<br>Modified Stream2 /Channel 2 in Table 42: DMA1 request mapping.<br>Added note related to EN bit in Section 10.5.5: DMA stream x configuration register<br>(DMA_SxCR) (x = 0..7). Updated definition of NDT[15:0] bits in Section 10.5.6:<br>DMA stream x number of data register (DMA_SxNDTR) (x = 0..7).<br>**Interrupts**:<br>Updated number of maskable interrupts to 82 in Section 12.1.1: NVIC featuress.<br>Updated Section 12.2: External interrupt/event controller (EXTI).|



1720/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|19-Oct-2012|2 <br>(continued)|**ADC**:<br>Changed ADCCLK frequency to 30 MHz in Section 13.5: Channel-wise<br>programmable sampling timee.<br>Added recovery from ADC sequence in Section 13.8.1: Using the DMA and Section<br>13.8.2: Managing a sequence of conversions without using the DMA.<br>Updated AWDIE in Section 13.13.2: ADC control register 1 (ADC_CR1). Added<br>read and write access in Section 13.13: ADC registers.<br>**Advanced control timers (TIM1 and TIM8):**<br>Updated 16-bit prescaler range in Section 17.2: TIM1 and TIM8 main features.<br>Updated OC1 block diagram in Figure 114: Output stage of capture/compare<br>channel (channel 1 to 3).<br>Updated update event generation in Upcounting mode and Downcounting mode in<br>Section 17.3.2: Counter modes and Section 17.3.3: Repetition counter.<br>Updated bits that control the dead-time generation in Section 17.3.11:<br>Complementary outputs and dead-time insertion.<br>Updated ways to generate a break in Section 17.3.12: Using the break function.<br>Changed OCxREF to ETR in the example given in Section 17.3.13: Clearing the<br>OCxREF signal on an external event and changed<br>OCREF_CLR to ETRF in Figure 124: Clearing TIMx OCxREF.<br>Updated configuration for example of counter operation in encoder<br>interface mode in Section 17.3.16: Encoder interface mode.<br>Added register access in Section 17.4: TIM1 and TIM8 registers.<br>Changed definition of ARR[15:0] bits in Section 17.4.12: TIM1 and TIM8 auto-<br>reload register (TIMx_ARR).<br>Updated BKE definition in Section 17.4.18: TIM1 and TIM8 break and dead-time<br>register (TIMx_BDTR).|


RM0090 Rev 21 1721/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|19-Oct-2012|2 <br>(continued)|**General purpose timers (TIM2 to TIM5):**<br>Removed all references to “repetition counter”.<br>Added Figure 134: General-purpose timer block diagram.<br>Updated 16-bit prescaler range in Section 18.2: TIM2 to TIM5 main features.<br>External clock mode 2 ETR restricted to TIM2 to TIM4 in<br>Section 18.3.3: Clock selection and Section 18.3.6: PWM input mode.<br>Updated Section 18.3.9: PWM mode and Section 18.3.11: Clearing the OCxREF<br>signal on an external event.<br>Updated Figure 174: Master/Slave timer example to change ITR1 to<br>ITR0.<br>Updated read and write access to registers in Section 18.4: TIM2 to TIM5<br>registerss.<br>Restored bits 15 to 8 of TIMx_SMCR as well as Table 98: TIMx internal trigger<br>connection in Section 14.4.3.<br>Removed note 1 related to OC1M bits in Section 18.4.13: TIMx capture/compare<br>register 1 (TIMx_CCR1).<br>Updated TIMx_CCER bit description for TIM2 to TIM5 in<br>Section 18.4.9: TIMx capture/compare enable register (TIMx_CCER).<br>**General purpose timers (TIM9 to TIM14):**<br>Updated 16-bit prescaler range in Section 19.2.1: TIM9/TIM12 main features and<br>Section 19.2.2: TIM10/TIM11 and TIM13/TIM14 main features.<br>Updated Figure 181: General-purpose timer block diagram (TIM10/11/13/14)) to<br>remove TRGO trigger controller output.<br>Added register access in Section 19.4: TIM9 and TIM12 registers<br>and Section 19.5: TIM10/11/13/14 registers.<br>**Basic timers (TIM6 and TIM7):**<br>Removed all references to “repetition counter”.<br>Updated 16-bit prescaler range in Section 20.2: TIM6 and TIM7 main features.<br>**HASH**:<br>Updated Section 25.3.1: Duration of the processing.<br>**RNG**:<br>Updated Section 24.1: RNG introduction.|



1722/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|19-Oct-2012|2 <br>(continued)|**RTC**:<br>Updated Figure 237: RTC block diagram.<br>Added formula to compute fck_apre in Figure 26.3.1: Clock and prescalers.<br>Updated Section 26.3.9: RTC reference clock detection.<br>Updated Section : RTC register write protection.<br>Added RTC_SSR shadow register in Section 26.3.6: Reading the calendar.<br>Updated description of DC[4:0] bits in Section 26.6.7: RTC calibration register<br>(RTC_CALIBR).<br>Renamed RTC_BKxR into RTC_BKPxR in Table 121: RTC register map and reset<br>values.<br>Added power-on reset value and changed reset value to system<br>reset value in Section 26.6.11: RTC sub second register (RTC_SSR).<br>Updated definition of ALARMOUTTYPE in Section 26.6.17: RTC tamper and<br>alternate function configuration register (RTC_TAFCR).<br>**I2C**:<br>Modified Section 27.3.8: DMA requests.<br>Updated bit 14 description in Section 27.6.3: I2C Own address register 1<br>(I2C_OAR1)).<br>Updated definition of PE bit and note related to SWRST bit; moved<br>note related to STOP bit to the whole register in Section 27.6.1: I2C Control register<br>1 (I2C_CR1).<br>**USART**:<br>Section 30.6.6: Control register 3 (USART_CR3)): removed notes<br>related to UART5 in DMAT and DMAR description.<br>Updated TTable 142: Error calculation for programmed baud rates at fPCLK = 42<br>MHz or fPCLK = 84 Hz, oversampling by 16 and<br>Table 143: Error calculation for programmed baud rates at fPCLK = 42 MHz or<br>fPCLK = 84 MHz, oversampling by 8.<br>**SPI/I2S:**<br>Updated Section 28.1: SPI introduction.<br>Changed I2S simplex communication/mode to half-duplex communication/mode.<br>Updated flags in reception/transmission modes in Section 28.2.2: I2S features.<br>Added Frame error flag in Table 128: I2S interrupt requests.<br>Added register access in Section 28.5: SPI and I2S registers.<br>Updated ERRIE definition in Section 28.5.2: SPI control register 2 (SPI_CR2).<br>Renamed TIFRFE to FRE and definition updated in Section 28.5.3: SPI status<br>register (SPI_SR).|


RM0090 Rev 21 1723/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|19-Oct-2012|2 <br>(continued)|**SDIO**:<br>Updated value and description for bits [45:40] and [7:1] in Table 176: R4 response.<br>Updated value at bits [45:40] in Table 178: R5 response.<br>**CAN**:<br>Updated Figure 335: Dual CAN block diagram.<br>Modified definition of CAN2SB bits in Section : CAN filter master register<br>(CAN_FMR).<br>Added register access in Section 32.9: CAN registers<br>**ETHERNET**:<br>Updated standard for precision networked clock synchronization in Section 33.1:<br>Ethernet introduction and Section 33.2.1: MAC core features.<br>Updated CR bit definition in Section : Ethernet MAC MII address register<br>(ETH_MACMIIAR).<br>Replace RTPR by PM bit in Table 192: Source address filtering.<br>**USB OTG FS**<br>Updated remote wake-up signaling bit and the resume<br>interrupt in Section : Suspended state.<br>Added peripheral register access in Section 34.16: OTG_FS control and status<br>registerss.<br>Updated INEPTXSA description in OTG_FS_DIEPTXFx.<br>Changed PHYSEL from bit 7 to bit 6 of the OTG_FS_GUSBCFG<br>register.<br>**USB OTG HS**<br>Updated remote wake-up signaling bit and the resume<br>interrupt in Section : Suspended state.<br>Added peripheral register access in Section 35.12: OTG_HS control and status<br>registers.<br>Updated OTG_HS_CID reset value.<br>Updated INEPTXSA description in OTG_HS_DIEPTXFx.<br>Updated FSLSPCS for LS host mode, added PHYSEL in Section : OTG_HS host<br>configuration register (OTG_HS_HCFG).<br>Renamed PHYSEL into PHSEL and changed from bit 7 to bit 6 of<br>the OTG_HS_GUSBCFG register.<br>Updated OTG_HS_DIEPEACHMSK1 and OTG_HS_DOEPEACHMSK1 reset<br>values.|



1724/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|19-Oct-2012|2 <br>(continued)|**FSMC**:<br>Updated step b) in Section 36.3.1: Supported memories and transactions.<br>Updated Table 196: FSMC_BTRx bit fields.<br>Changed Clock divide ration min in Table 246: Programmable NAND/PC Card<br>access parameters.<br>Updated case of synchronous accesses in Section 36.5: NOR Flash/PSRAM<br>controller.<br>Changed minimum value for ADDSET to 0 in Table 203, Table 206, Table 207,<br>Table 209, and Table 210.<br>Move note from Figure 437: Mode1 write accesses and Figure 436: Mode1 read<br>accesses. Move note from Figure 439: ModeA write accesses to Figure 438:<br>ModeA read accesses.<br>Updated Section : WAIT management in asynchronous accesses.<br>Added register access in Section 36.5.6: NOR/PSRAM control registers and<br>Section 36.6.2: NAND Flash / PC Card supported memories and transactions.<br>Removed caution note in Section 36.6.1: External memory interface signalss.<br>Updated Table 249: 16-bit PC Card.<br>Updated step 3 in Section 36.6.4: NAND Flash operations.<br>Updated Figure 455: Access to non ‘CE don’t care’ NAND-Flash and note below in<br>Section 36.6.5: NAND Flash prewait functionality.<br>Updated access to I/O Space in Section 36.6.7: PC Card/CompactFlash<br>operationss. Updated Table 251: 16-bit PC-Card signals and access type. Updated<br>BUSTURN bit definition in Section : SRAM/NOR-Flash chip-select timing registers<br>1..4 (FSMC_BTR1..4)). Changed bits 16 to 19 to BUSTURN in Section :<br>SRAM/NOR-Flash write timing registers 1..4 (FSMC_BWTR1..4)<br>**DEBUG**: <br>Updated Section 38.4.3: Internal pull-up and pull-down on JTAG pins.<br>**Electronic signature**<br>Updated Section 24: Device electronic signature introduction.<br>Updated REV_ID[15:0] to add revision Z in Section 24.1: Unique device ID register<br>(96 bits).<br>Updated address and example in Section 24.2: Flash size.|


RM0090 Rev 21 1725/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|13-Nov-2012|3|Added STM32F42x and STM32F43x devices.<br>Removed reference du Flash programming manual on cover page. Added Section<br>2.3.2: Flash memory overview and Section 3: Embedded Flash memory interface.<br>Change RTC_50Hz into RTC_REFIN in Section 8.3.2: I/O pin multiplexer and<br>mapping. Modified RTC alternate function naming in Section 8: General-purpose<br>I/Os (GPIO) and Section 26: Real-time clock (RTC).<br>Updated max. input frequency in Section 26.3.1: Clock and prescalers.<br>Changed bit access type from ‘rw’ to ‘w’ and bit description updated in Section<br>10.5.3: DMA low interrupt flag clear register (DMA_LIFCR) and Section 10.5.4:<br>DMA high interrupt flag clear register (DMA_HIFCR).<br>Updated Figure 18: Frequency measurement with TIM5 in Input capture mode.<br>Updated Section : Signals synchronization in Section 36: Flexible static memory<br>controller (FSMC)<br>Section 34: USB on-the-go full-speed (OTG_FS): updated Section Figure 389.:<br>USB host-only connection, Section : VBUS valid, and Section : Host detection of a<br>peripheral connection.<br>Section 35: USB on-the-go high-speed (OTG_HS): updated Section : VBUS valid,<br>and Section : Detection of peripheral connection by the host.|
|19-Feb-2013|4|Updated Section 2: Memory and bus architecture.<br>Updated Figure 1: System architecture for STM32F405xx/07xx and<br>STM32F415xx/17xx devices, and Figure 1: System architecture for<br>STM32F405xx/07xx and STM32F415xx/17xx devices. Updated Table 4: Memory<br>mapping vs. Boot mode/physical remap. Updated Figure 5: Sequential 32-bit<br>instruction execution. removed note 1 from Table 13: Maximum program/erase<br>parallelism.<br>**PWR**:<br>Updated Figure 7: Power supply overview.<br>Updated Section 5.1.3: Voltage regulator.<br>Added ADCDC1 bit in Section 5.5.1: PWR power control register (PWR_CR) for<br>STM32F42xxx and STM32F43xxx.<br>**SYSCFG**:<br>Added ADCxDC2 bit in Section 8.2.3: SYSCFG peripheral mode configuration<br>register (SYSCFG_PMC) for STM32F42xxx and STM32F43xxx.<br>**ADC**:<br>Updated Section 13.9.3: Interleaved mode, Section 13.9.4: Alternate trigger mode,<br>and Section 13.9.5: Combined regular/injected simultaneous mode to describe<br>case of interrupted conversion.<br>Updated Section : Temperature sensor, VREFINT and VBAT internal channels,<br>Section 13.10: Temperature sensor, and Section 13.11: Battery charge monitoring.<br>**RTC**:<br>Updated BKP[31:0] bit description in Section 26.6.20: RTC backup registers<br>(RTC_BKPxR).<br>**I2C**:<br>Updated Section 27.3.5: Programmable noise filter.|



1726/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|19-Feb-2013|4 <br>(continued)|**FSMC**: <br>Updated write FIFO size in Section 36.1: FSMC main features.<br>Updated Figure 434: FSMC block diagram.<br>Updated Section 36.5.4: NOR Flash/PSRAM controller asynchronous transactions.<br>Modified differences between Mode B and mode 1 in Section : Mode 2/B - NOR<br>Flash.<br>Modified differences between Mode C and mode 1 in Section : Mode C - NOR<br>Flash - OE toggling.<br>Modified differences between Mode D and mode 1 in Section : Mode D -<br>asynchronous access with extended address.<br>Updated NWAIT signal in Figure 449: Asynchronous wait during a read access,<br>Figure 450: Asynchronous wait during a write access, Figure 451: Wait<br>configurations, Figure 452: Synchronous multiplexed read mode - NOR, PSRAM<br>(CRAM), and Figure 453: Synchronous multiplexed write mode - PSRAM (CRAM).<br>Updated Table 195 to Table 214.<br>Updated Section : SRAM/NOR-Flash chip-select control registers 1..4<br>(FSMC_BCR1..4).<br>**DEBUG**<br>Updated Figure 485: Block diagram of STM32 MCU and Cortex®-M4 with FPU-<br>level debug support.|


RM0090 Rev 21 1727/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|15-Sep-2013|5|Added STM32F429xx and STM32F439xx part numbers.<br>Replaced FSMC by FMC added Chrom-ART Accelerator, LCD-TFT and SAI<br>interface.<br>Updated Figure 2: System architecture for STM32F42xxx and STM32F43xxx<br>devices.<br>**PWR**:<br>Updated Section 5.2.2: Brownout reset (BOR).<br>Added note related to CSS enabling in Entering Stop mode sections in Section<br>5.3.4: Stop mode (STM32F405xx/07xx and STM32F415xx/17xx) and Section 5.3.5:<br>Stop mode (STM32F42xxx and STM32F43xxx). Updated Stop mode entry in Table<br>27 and Table 29.<br>Updated WUF bit defienition in PWR_CSR registers. Changed CWUF and CSBF<br>access type to ‘w’ in PWR_CR register.<br>**RCC**: Updated LSEBYP bit definition in RCC_BDCR register.<br>**GPIOs**:<br>Updated description of OSPEEDR bits. Removed frequency value in description of<br>OSPEEDR bits.Corrected typos: "IDRy[15:0]" replaced with "IDRy" in "GPIOx_IDR"<br>register, "ODRy[15:0]" replaced with "ODRy" in "GPIOx_ODR" register and<br>"OTy[1:0]" replaced with "OTy" in "GPIOx_OTYPER" register.<br>**DCMI**: Updated Section 15.4: DCMI clocks.<br>**IWDG**: Corrected Figure 213: Independent watchdog block diagram.<br>**RTC**: <br>Replaced all occurrences of “power-on reset” with “backup domain reset”. Added<br>caution note under Table 121: RTC register map and reset values. Changed SHPF<br>bit type to ‘r’ in Section 26.6.4: RTC initialization and status register (RTC_ISR)..<br>**SPI**: Updated definition of ERRIE bit in Section 28.5.2: SPI control register 2<br>(SPI_CR2).<br>**UART**: <br>Updated Section 30.3.8: LIN (local interconnection network) mode.<br>Removed note in Section 30.3.13: Continuous communication using DMA.<br>**ETHERNET**:<br>Modified ETH_MACA0HR (and ETH_DMABMR reset values.<br>Updated definitions of TSTS bit in ETH_MACSR, and TSTTR in ETH_PTPTSSR.|



1728/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|15-Sep-2013|5 <br>(continued)|**USB OTG-FS:**<br>Removed note related to VDD range limitation below Figure 387: OTG A-B device<br>connection and Figure 388: USB peripheral-only connection.<br>**FSMC**:<br>Updated Table 229, Table 232, Table 235, Table 239.<br>Replaced all occurences of DATALAT by DATLAT and SRAM/CRAM by<br>SRAM/PSRAM in the whole section.<br>Updated Section 36.1: FSMC main features. Changed bits 27 to 20 of<br>FSMC_BWTR1..4 to reserved.<br>Updated Section 36.6.7: PC Card/CompactFlash operations.<br>Updated WREN bit in Table 231, Table 232, Table 233, Table 236, Table 239, Table<br>242, Table 245, and Table 249.<br>Updated Section 36.5.4: NOR Flash/PSRAM controller asynchronous transactions,<br>Section : SRAM/NOR-Flash chip-select control registers 1..4 (FSMC_BCR1..4),<br>Section : SRAM/NOR-Flash chip-select timing registers 1..4 (FSMC_BTR1..4) and<br>Section : SRAM/NOR-Flash write timing registers 1..4 (FSMC_BWTR1..4).<br>Updated definition of PWID in Section : PC Card/NAND Flash control registers 2..4<br>(FSMC_PCR2..4).<br>**FMC**: <br>Updated TRDC definition in Section : SDRAM Timing registers 1,2<br>(FMC_SDTR1,2).<br>**DEBUG**: updated Figure 487: JTAG TAP connections.|


RM0090 Rev 21 1729/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|03-Feb-2014|6|Added note related to over-drive mode unavailable in 1.8 to 2.1 V VDD range in<br>Section 3.5.1: Relation between CPU clock frequency and Flash memory read<br>time.<br>Updated maximum CPU frequency in Section 3.5.2: Adaptive real-time memory<br>accelerator (ART Accelerator™).<br>**PWR**: <br>Updated Run mode/ over-drive mode in Section 5.1.4: Voltage regulator for<br>STM32F42xxx and STM32F43xxx.<br>**RCC for STM32F42/43xx:**<br>Changed APB1/2 and AHB maximum frequencies.xw<br>**GPIOs**: <br>Updated Figure 27: Selecting an alternate function on STM32F42xxx and<br>STM32F43xxx.<br>**DMA**: <br>Updated Section 10.3.7: Pointer incrementation and Section 10.3.11: Single and<br>burst transfers..<br>**INTERRUPTS AND EVENTS:**<br>Updated Table 62: Vector table for STM32F42xxx and STM32F43xxx.<br>**ADC**: <br>Updated Section 13.3.10: Discontinuous mode/Section : Regular group.<br>**DCMI**: <br>Updated Section 15.5.2: DCMI physical interface.<br>**LTDC**: <br>Updated resolution in note below Figure 82: LCD-TFT Synchronous timings.<br>**TIM1 and 8:**<br>Added note related to IC1F in Section 17.4.7: TIM1 and TIM8 capture/compare<br>mode register 1 (TIMx_CCMR1).<br>**TIM2 to 5:**<br>Updated note related to IC1F in Section 18.4.7: TIMx capture/compare mode<br>register 1 (TIMx_CCMR1).|



1730/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|03-Feb-2014|6 <br>(continued)|**TIM9 to 14:**<br>Updated note related to IC1F in Section 19.5.5: TIM10/11/13/14 capture/compare<br>mode register 1 (TIMx_CCMR1).<br>**RTC**: <br>Updated Section 26.3.11: RTC smooth digital calibration.<br>Changed ALRBIE to ALRBE (bit 9) in Section 26.6.3: RTC control register<br>(RTC_CR).<br>**I2C**: <br>Introduced Sm (standard mode) and Fm (fast mode) acronyms.<br>**FSMC**: <br>Updated BUSTURN definition in Table 245: FSMC_BTRx bit fields.<br>**FMC**:<br>Added Mobile LPSDR SDRAM.<br>Updated Section : SDRAM initialization and Section : SDRAM controller read cycle<br>and Figure 476: NAND Flash/PC Card controller waveforms for common memory<br>access.<br>Updated Section : SRAM/NOR-Flash chip-select control registers 1..4<br>(FMC_BCR1..4), Section : SRAM/NOR-Flash chip-select timing registers 1..4<br>(FMC_BTR1..4), Section : SRAM/NOR-Flash write timing registers 1..4<br>(FMC_BWTR1..4), Section : SDRAM Timing registers 1,2 (FMC_SDTR1,2) and<br>Section : SDRAM Refresh Timer register (FMC_SDRTR).<br>Removed mention “default valeur after reset” in Section : Common memory space<br>timing register 2..4 (FMC_PMEM2..4), Section : Attribute memory space timing<br>registers 2..4 (FMC_PATT2..4), and Section : I/O space timing register 4<br>(FMC_PIO4).<br>Updated BUSTURN definition in Table 288: FMC_BTRx bit fields.<br>Updated REV_ID bits in Section 38.6.1: MCU device ID code.|


RM0090 Rev 21 1731/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|15-May-2014|7|**Embedded Flash memory interface:**<br>Updated Section : Physical remap in STM32F42xxx and STM32F43xxx. Updated<br>bank 2 selection in Section 2.4: Boot configuration. Updated notes related to MERx<br>and SER bits in Section : Mass Erase. Updated Section 3.7.5: Proprietary code<br>readout protection (PCROP). Updated FLASH_OPTCR register reset value for<br>STM32F42/43xx in Section 3.9.10: Flash option control register (FLASH_OPTCR)<br>for STM32F42xxx and STM32F43xxx and Section 3.9.11: Flash option control<br>register (FLASH_OPTCR1) for STM32F42xxx and STM32F43xxx.<br>**RCC (STM32F42/43xx):**<br>Updated PPLN caution note in Section 6.3.2: RCC PLL configuration register<br>(RCC_PLLCFGR)<br>**SYSCFG**<br>Updated MEM_MODE in Section 9.3.1: SYSCFG memory remap register<br>(SYSCFG_MEMRMP)<br>**LTDC**: <br>Changed resolution do XGA (1024x768) in Section 16.2: LTDC main features,<br>Section 16.4.1: LTDC Global configuration parameters, and updated Section<br>16.7.3: LTDC Active Width Configuration Register (LTDC_AWCR).<br>**RTC**<br>Added note in Section 26.3.14: Calibration clock output.<br>**TIMER 1/8:**<br>Removed note related to IC1F bits in Section 17.4.7: TIM1 and TIM8<br>capture/compare mode register 1 (TIMx_CCMR1),<br>**TIM2 to 5:**<br>Replaced IC2S by CC2S.<br>Updated Figure 161: Output stage of capture/compare channel (channel 1).<br>Removed note related to IC1F bits in Section 18.4.7: TIMx capture/compare mode<br>register 1 (TIMx_CCMR1).<br>**TIM9 to 14:**<br>Removed note related to IC1F bits in Section 19.5.5: TIM10/11/13/14<br>capture/compare mode register 1 (TIMx_CCMR1).<br>**USB OTG-HS:**<br>Updated DSPD definition in Section : OTG_HS device configuration register<br>(OTG_HS_DCFG).<br>**FSMC**<br>Updated DATLAT bits definition in Section : SRAM/NOR-Flash chip-select timing<br>registers 1..4 (FSMC_BTR1..4).|



1732/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|15-May-2014|7 <br>(continued)|**FMC**<br>Updated Figure 474: Synchronous multiplexed read mode waveforms - NOR,<br>PSRAM (CRAM). Updated DATLAT bits definition in Section : SRAM/NOR-Flash<br>chip-select timing registers 1..4 (FMC_BTR1..4).<br>Updated FMC_BWTRx register address offsets in Table 297: FMC register map.<br>**DEBUG**<br>Added revision code ‘3’ in Section : DBGMCU_IDCODE.|


RM0090 Rev 21 1733/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|14-Oct-2014|8|**Memory and bus architecture:**<br>Updated Table 3: Memory mapping vs. Boot mode/physical remap  in<br>STM32F405xx/07xx and STM32F415xx/17xx and Table 4: Memory mapping vs.<br>Boot mode/physical remap  in STM32F42xxx and STM32F43xxx.<br>**RCC (STM32F40/41xx) and RCC (STM32F42/43xx):**<br>Removed all references to Flash programming manual. Changed<br>RCC_AHB1LPENR, RCC_APB1LPENR, RCC_APB2LPENR, RCC_PLLI2SCFGR<br>and RCC_APB2LPENR reset values.<br>Updated access type to “r” for bits 24 to 31 in RCC_CSR.<br>**GPIOs**:<br>Updated Figure 27: Selecting an alternate function on STM32F42xxx and<br>STM32F43xxx.<br>**IWDG**<br>Update note in Table 107: Min/max IWDG timeout period (in ms) at 32 kHz (LSI).<br>**CRYPTO and HASH**<br>Removed STM32F405/407xx and STM32F42xx from the whole sections.<br>Removed STM32F405/407xx and STM32F42xx from the whole section.<br>**TIM10/11/13/14**<br>Added TIMx_DIER description in Section 19.5: TIM10/11/13/14 registers.<br>**ETHERNET**:<br>Updated Table 187: Clock range.<br>**USB OTG FS:**<br>Removed TRDT formula in Section 34.17.7: Worst case response time and added<br>Table 203: TRDT values.<br>**USB OTG HS:**<br>Removed TRDT formula in Section 35.13.8: Worst case response time and added<br>Table 213: TRDT values.<br>**FSMC**:<br>Updated EXTMOD definition in Section : SRAM/NOR-Flash chip-select control<br>registers 1..4 (FSMC_BCR1..4).<br>Updated ADDSET definition in Section : SRAM/NOR-Flash chip-select timing<br>registers 1..4 (FSMC_BTR1..4) and Section : SRAM/NOR-Flash write timing<br>registers 1..4 (FSMC_BWTR1..4).|



1734/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|14-Oct-2014|8 <br>(continued)|**FMC**:<br>Modified step 7 in Section : SDRAM initialization.<br>Modified SDRAM refresh rate equations and example in Section : SDRAM Refresh<br>Timer register (FMC_SDRTR) and updated definition of COUNT bits.<br>Updated EXTMOD definition in Section : SRAM/NOR-Flash chip-select control<br>registers 1..4 (FMC_BCR1..4).<br>Updated ADDSET definition in Section : SRAM/NOR-Flash chip-select timing<br>registers 1..4 (FMC_BTR1..4) and Section : SRAM/NOR-Flash write timing<br>registers 1..4 (FMC_BWTR1..4).|


RM0090 Rev 21 1735/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|16-Mar-2015|9|**PWR**: <br>Updated Section 5.1.2: Battery backup domain.<br>Updated Table 23: Low-power mode summary to add Return from ISR as entry<br>condition.<br>Added Section : Entering low-power mode and Section : Exiting low-power mode.<br>Updated Section : Entering Sleep mode, Section : Exiting Sleep mode, Table 24:<br>Sleep-now entry and exit and Table 25: Sleep-on-exit entry and exit.<br>Updated Section : Entering Stop mode (for STM32F405xx/07xx and<br>STM32F415xx/17xx), Section : Exiting Stop mode (for STM32F405xx/07xx and<br>STM32F415xx/17xx) and Table 27: Stop mode entry and exit (for<br>STM32F405xx/07xx and STM32F415xx/17xx). Updated Section : Entering Stop<br>mode (STM32F42xxx and STM32F43xxx), Section : Exiting Stop mode<br>(STM32F42xxx and STM32F43xxx) and Table 29: Stop mode entry and exit<br>(STM32F42xxx and STM32F43xxx).<br>Updated Section : Entering Standby mode, Section : Exiting Standby mode and<br>Table 30: Standby mode entry and exit.<br>**RCC:**<br>Updated bits 24 to 31 access type in Section 7.3.21: RCC clock control & status<br>register (RCC_CSR).<br>**GPIOs**:<br>Added port A reset value in Section 8.4.3: GPIO port output speed register<br>(GPIOx_OSPEEDR)  (x = A..I/J/K).<br>**DMA**:<br>Update FTH[1:0] description in Section 10.5.10: DMA stream x FIFO control<br>register (DMA_SxFCR) (x = 0..7).<br>**TIM2/5:**<br>Register format changed to 32 bits instead of 16 in Section 18.4.10: TIMx counter<br>(TIMx_CNT) and Section 18.4.12: TIMx auto-reload register (TIMx_ARR).<br>**TIM9 to 14:**<br>Updated Table 101: TIMx internal trigger connection<br>**WWDG**:<br>Updated Figure 214: Watchdog block diagram and Section 22.4: How to program<br>the watchdog timeout.<br>Updated Figure 215: Window watchdog timing diagram<br>**RNG**:<br>Replaced PLL48CLK by RNG_CLK in the whole section.|



1736/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|16-Mar-2015|9 <br>(continued)|**I2C2**: <br>Updated FREQ[5:0] description in Section 27.6.2: I2C Control register 2<br>(I2C_CR2).<br>**USART**:<br>Removed note related to RXNEIE in Section : Reception using DMA<br>**FSMC**:<br>Updated Figure 474: Synchronous multiplexed read mode waveforms - NOR,<br>PSRAM (CRAM).<br>**USB OTG FS**<br>Updated Table 203: TRDT values<br>**FMC**<br>Updated FMC_NL in Figure 456: FMC block diagram.<br>Updated ‘Memory wait’ and ‘Memory data bus high-z’ parameters in Table 289:<br>Programmable NAND Flash/PC Card access parameters.<br>Updated Section : Common memory space timing register 2..4 (FMC_PMEM2..4).<br>Updated Figure 476: NAND Flash/PC Card controller waveforms for common<br>memory access.<br>**DEBUG**:<br>Updated REV_ID[15:0) and JTAG ID code in Section 38.6.1: MCU device ID code<br>and Section 38.6.2: Boundary scan TAP, respectively|


RM0090 Rev 21 1737/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|28-Jul-2015|10|**Embedded Flash memory interface**<br>Updated Section 3.7.5: Proprietary code readout protection (PCROP),<br>**Power controller (PWR)**<br>Added the last sentence in Subsection: Entering low-power mode of Section 5.3:<br>Low-power modes,<br>Added the bullet points about the interrupt in mode entry in Table 24: Sleep-now<br>entry and exit, Table 25: Sleep-on-exit entry and exit, Table 27: Stop mode entry<br>and exit (for STM32F405xx/07xx and STM32F415xx/17xx), Table 29: Stop mode<br>entry and exit (STM32F42xxx and STM32F43xxx)<br>Added the last point to Mode entry, on return from ISR in Table 30: Standby mode<br>entry and exit,<br>Added the note in Section: Entering sleep mode in Section 5.3.3: Sleep mode.<br>**General-purpose I/Os (GPIO)**<br>Updated OSPEED[1:0] definition of GPIOx_OSPEEDR register in Section 8.4.3:<br>GPIO port output speed register (GPIOx_OSPEEDR)  (x = A..I/J/K)<br>**LCD-TFT Controller (LTDC)**<br>Corrected the bit field for WHSTPOS in the second bullet point in Section: Window<br>in Section 16.4.2: Layer programmable parameters.<br>**Advanced-control timers (TIM1&TIM8)**<br>Added the note in Section 17.3.20: Timer synchronization,<br>Updated ETF[3:0] description in Section 17.4.3: TIM1 and TIM8 slave mode control<br>register (TIMx_SMCR),<br>Updated IC1F[3:0] description in Section 17.4.7: TIM1 and TIM8 capture/compare<br>mode register 1 (TIMx_CCMR1),<br>Added the note to MMS2 bit description in Section 17.4.8: TIM1 and TIM8<br>capture/compare mode register 2 (TIMx_CCMR2),<br>Added the note to SMS[2:0] bit description in Section 17.4.3: TIM1 and TIM8 slave<br>mode control register (TIMx_SMCR).<br>**General-purpose timers (TIM2 to TIM5)**<br>Added the note in Section 18.3.15: Timer synchronization,<br>Updated SMS[2:0] description in Section 18.4.3: TIMx slave mode control register<br>(TIMx_SMCR),<br>Added the note to MMS2 bit description in Section 18.4.2: TIMx control register 2<br>(TIMx_CR2),<br>Added the note to SMS[2:0] bit description in Section 18.4.3: TIMx slave mode<br>control register (TIMx_SMCR).|



1738/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|28-Jul-2015|10<br>(Continued)|**General-purpose timers (TIM9 to TIM14)**<br>Added the note in Section 19.3.12: Timer synchronization (TIM9/12),<br>Added the note to MMS2 bit description,<br>Added the note to SMS[2:0] bit description in Section 19.4.2: TIM9/12 slave mode<br>control register (TIMx_SMCR).<br>**Window watchdog (WWDG)**<br>Updated.Figure 214: Watchdog block diagram<br>**Controller area network (bxCAN)**<br>Replaced tCAN with tq,<br>**Flexible static memory controller (FSMC)**<br>Added the paragraph about Cross boundary page for Cellular RAM 1.5 in Section<br>36.5.5: Synchronous transactions,<br>Updated MEMHIZx, MEMHOLDx, MEMSETx bit field descriptions for<br>FSMC_PME2..4 register in Section 36.5.5: Synchronous transactions,<br>Updated ATTSET, ATTHOLD, ATTHIZ bit field descriptions for FSMC_PATT2..4<br>register in Section 36.5.5: Synchronous transactions,<br>Updated IRS and IFS bit descriptions for FMC_SR2..4 in Section 36.5.5:<br>Synchronous transactions,<br>Renamed ADDSET as ADDSET[3:0] and MTYP as MTYP[1:0],<br>Addition of CPSIZE in FSMC_BCRx bit fields in Table 226: FSMC_BCRx bit fields,<br>Table 228: FSMC_BCRx bit fields, Table 231: FSMC_BCRx bit fields, Table 234:<br>FSMC_BCRx bit fields, Table 237: FSMC_BCRx bit fields, Table 240: FSMC_BCRx<br>bit fields, Table 242: FSMC_BCRx bit fields,<br>Added CPIZE[2:0] in FMC_BCR1...4 registers in,Section 36.5.6: NOR/PSRAM<br>control registers Section NOR/PSRAM control re<br>Added CPSIZE[2:0] for FMC_BCRx registers in Section 36.6.9: FSMC register<br>map.|


RM0090 Rev 21 1739/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|28-Jul-2015|10<br>(Continued)|**Flexible memory controller (FMC)**<br>Added the paragraph about Cross boundary page for Cellular RAM 1.5 in Section<br>37.5.5: Synchronous transactions,<br>Updated BUSTURN bit field description for FMC_BTR1..4 register in Section<br>37.5.6: NOR/PSRAM controller registers,<br>Updated MEMHIZx, MEMHOLDx, MEMSETx bit field descriptions for<br>FMC_PME2..4 register in Section 37.6.8: NAND Flash/PC Card controller registers,<br>Updated ATTSET, ATTHOLD, ATTHIZ bit field descriptions for FMC_PATT2..4<br>register in Section 37.6.8: NAND Flash/PC Card controller registers,<br>Updated IRS and IFS bit descriptions for FMC_SR2..4 in Section 37.6.8: NAND<br>Flash/PC Card controller registers,<br>Updated the section SDRAM initialization with the last item in the numbered list in<br>Section 37.7.5: SDRAM controller registers,<br>Renamed ADDSET as ADDSET[3:0] and MTYP as MTYP[1:0],<br>Addition of CPSIZE in Table 269: FMC_BCRx bit fields, Table 271: FMC_BCRx bit<br>fields, Table 274: FMC_BCRx bit fields, Table 277: FMC_BCRx bit fields, Table 280:<br>FMC_BCRx bit fields, Table 283: FMC_BCRx bit fields, Table 285: FMC_BCRx bit<br>fields, Table 287: FMC_BCRx bit fields,<br>Added the paragraph about Cross boundary page for Cellular RAM 1.5 in Section<br>37.5.5: Synchronous transactions,<br>Added CPIZE[2:0] in FMC_BCR1...4 registers in Section 37.5.6: NOR/PSRAM<br>controller registers,<br>Added CPSIZE[2:0] for FMC_BCRx registers in Section 37.8: FMC register map.|



1740/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|20-Oct-2015|11|**Reset and clock controller (RCC)**<br>Updated STM32F405/407/415/417xx Figure 21: Clock tree.<br>Updated<br>**General purpose I/O (GPIOs)**<br>Changed definition of OSPEEDR bits in Section 8.4.3: GPIO port output speed<br>register (GPIOx_OSPEEDR) (x = A..I/J/K).<br>**LCD-TFT display controller (LTDC):**<br>Changed LRDC_IER into LTDC_IER in Section 16.5: LTDC interrupts.<br>Updated AHBP[11:0], AAV[11:0 and TOTALW[11:0 in Table 92: LTDC register map<br>and reset values.<br>**Controller area network (bxCAN):**<br>Updated Section 32.3.4: Acceptance filters and Section 32.7.4: Identifier filtering.<br>**Flexible static memory controller (FSMC)**<br>Updated BUSTURN description in Section : SRAM/NOR-Flash write timing<br>registers 1..4 (FSMC_BWTR1..4) and Section : SRAM/NOR-Flash chip-select<br>timing registers 1..4 (FSMC_BTR1..4)<br>Updated note related to IRS and IFS bits in Section : FIFO status and interrupt<br>register 2..4 (FSMC_SR2..4).<br>**Flexible memory controller (FMC)**<br>Updated paragraph related to the cacheable read FIFO in Section : SDRAM<br>controller read cycle.<br>Updated BUSTURN description in Section : SRAM/NOR-Flash write timing<br>registers 1..4 (FMC_BWTR1..4) and Section : SRAM/NOR-Flash chip-select timing<br>registers 1..4 (FMC_BTR1..4).<br>Updated note related to IRS and IFS bits in Section : FIFO status and interrupt<br>register 2..4 (FMC_SR2..4).<br>**Real-time clock (RTC2)**<br>Updated WUCKSEL prescaler input in Figure 237: RTC block diagram.<br>Updated 3rd step in Section : Programming the wakeup timer.<br>Updated WUTWF bit definition in Section 26.6.4: RTC initialization and status<br>register (RTC_ISR).|


RM0090 Rev 21 1741/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|17-May-2016|12|**Flash memory interface**<br>Removed note related to boot from Bank 2 in Section 2.4: Boot configuration.<br>Updated notes in Section 3.7.3: Read protection (RDP).<br>Changed number of LATENCY bits in Section 3.9.2: Flash access control register<br>(FLASH_ACR) for STM32F42xxx and STM32F43xxx<br>In Table 9: 1 Mbyte dual bank Flash memory organization (STM32F42xxx and<br>STM32F43xxx): updated sector 19 size and option bytes (bank 2) address range.<br>**Power control (PWR)**<br>Removed reference to low-power mode in Section 5.1.4: Voltage regulator for<br>STM32F42xxx and STM32F43xxx, Section : Entering Stop mode (STM32F42xxx<br>and STM32F43xxx) and Section : Exiting Stop mode (STM32F42xxx and<br>STM32F43xxx).<br>**Analog-to-digital converter (ADC)**<br>Added note related to ADC_HTR and ADC_LTR register programming in Section<br>13.13.7: ADC watchdog higher threshold register (ADC_HTR) and Section 13.13.8:<br>ADC watchdog lower threshold register (ADC_LTR).<br>**Chrom-Art Accelerator™ controller (DMA2D)**<br>Updated Section 11.3.12: DMA2D transfer control (start, suspend, abort and<br>completion).<br>Section 11.5.8: DMA2D foreground PFC control register (DMA2D_FGPFCCR):<br>updated START bit access type<br>Section 11.5.10: DMA2D background PFC control register (DMA2D_BGPFCCR):<br>updated START bit access and description.<br>**LCD-TFT controller (LTDC)**<br>Updated Section 16.3.2: LTDC reset and clocks.<br>Modified LCD_DE description in Table 89: LCD-TFT pins and signal interface.<br>Modified Section 16.7.15: LTDC Layerx Window Horizontal Position Configuration<br>Register (LTDC_LxWHPCR) (where x=1..2) and Section 16.7.16: LTDC Layerx<br>Window Vertical Position Configuration Register (LTDC_LxWVPCR) (where<br>x=1..2).<br>**General-purpose timers (TIM2 to TIM5)**<br>Updated Section 18.4.11: TIMx prescaler (TIMx_PSC).<br>**General-purpose timers (TIM9 to TIM14)**<br>Added OPM bit in Section 19.5.1: TIM10/11/13/14 control register 1 (TIMx_CR1).<br>Updated Section 19.4.9: TIM9/12 prescaler (TIMx_PSC) and Section 19.5.8:<br>TIM10/11/13/14 prescaler (TIMx_PSC).|



1742/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|17-May-2016|12<br>(continued)|**General-purpose timers (TIM6 and TIM7)**<br>Updated Section 20.4.7: TIM6 and TIM7 prescaler (TIMx_PSC).<br>**Real-time clock (RTC)**<br>Updated conditions for running under System reset in Section 26.3.7: Resetting the<br>RTC.<br>Updated Section 26.3.14: Calibration clock output.<br>Added note related to TSE in Section 26.6.3: RTC control register (RTC_CR).<br>Updated caution note related to TAMP1TRG in Section 26.6.17: RTC tamper and<br>alternate function configuration register (RTC_TAFCR) register.<br>**Universal synchronous asynchronous receiver transmitter (USART)**<br>Replaced all occurrences of nCTS by CTS, nRTS by RTS and SCLK by CK.<br>**Flexible static memory controller (FSMC)**<br>Updated Section 36.3: AHB interface.<br>Added note related to the hold phase delay below Figure 454: NAND/PC Card<br>controller timing for common memory access.<br>Updated Section 36.6.5: NAND Flash prewait functionality.<br>Updated BUSTURN description in Section : SRAM/NOR-Flash chip-select timing<br>registers 1..4 (FSMC_BTR1..4).<br>Updated MEMHOLDx in Section : Common memory space timing register 2..4<br>(FSMC_PMEM2..4) and ATTHOLD in Section : Attribute memory space timing<br>registers 2..4 (FSMC_PATT2..4).<br>**Flexible memory controller (FMC)**<br>Updated Section 37.3: AHB interface.<br>Added note related to the hold phase delay below Figure 476: NAND Flash/PC<br>Card controller waveforms for common memory access.<br>Updated Section 37.6.5: NAND Flash prewait functionality.<br>Updated BUSTURN description in Section : SRAM/NOR-Flash chip-select timing<br>registers 1..4 (FMC_BTR1..4).<br>Updated MEMHOLDx in Section : Common memory space timing register 2..4<br>(FMC_PMEM2..4) and ATTHOLD in Section : Attribute memory space timing<br>registers 2..4 (FMC_PATT2..4).<br>**Debug (DBG)**<br>Updated value to be programmed to the ETM Trace Start/stop register to enable the<br>trace in Section 38.15.4: ETM configuration example.|


RM0090 Rev 21 1743/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|20-Sep-2016|13|**Analog-to-digital converter (ADC)**<br>Updated DMA mode 1 and DMA mode 3 description in Section 13.9: Multi ADC<br>mode.<br>**LCD-TFT controller**<br>Updated values to be programmed to LTDC_SSCR in Section : Example of<br>Synchronous timings configuration<br>Updated Section 16.4.2: Layer programmable parameters/Windowing.<br>**Advanced-control timers (TIM1 and TIM8)**<br>Updated Section 17.3.21: Debug mode.<br>Extended Section 17.4.20: TIM1 and TIM8 DMA address for full transfer<br>(TIMx_DMAR) to 32 bits.<br>Updated Table 95: Output control bits for complementary OCx and OCxN channels<br>with  break feature output state for MOE = 0.<br>Updated TIM1 and TIM8 auto-reload register (TIMx_ARR) reset value.<br>Updated TIMx_CCR1/2/3/4 description when CC1 channel is configured as inputs<br>and changed bit access type to rw/ro.<br>**General-purpose timers (TIM2 to TIM5)**<br>Updated TIMx auto-reload register (TIMx_ARR) reset value.<br>Updated TIMx_CCR1/2/3/4 description when CC1 channel is configured as inputs<br>and changed bit access type to rw/ro.<br>**General-purpose timers (TIM9 to TIM14)**<br>Updated TIM9/12 auto-reload register (TIMx_ARR) and TIM10/11/13/14 auto-<br>reload register (TIMx_ARR) reset value.<br>Updated TIMx_CCR1 description when CC1 channel is configured as inputs and<br>changed bit access type to rw/ro.<br>**Basic timers (TIM6 to TIM7)**<br>Updated TIM6 and TIM7 auto-reload register (TIMx_ARR).<br>**Secure digital input/output interface (SDIO)**<br>Updated Section 31.1: SDIO main features up to 50 MHz.<br>Updated Section 31.3: SDIO functional description SDIO_CK description.<br>Updated note removing 48 MHz in Section 31.9.1: SDIO power control register<br>(SDIO_POWER), Section 31.9.2: SDI clock control register (SDIO_CLKCR),<br>Section 31.9.4: SDIO command register (SDIO_CMD) and Section 31.9.9: SDIO<br>data control register (SDIO_DCTRL).|



1744/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|20-Sep-2016|13<br>(continued)|**FMC**<br>Update BUSTURN bit description in Section : SRAM/NOR-Flash chip-select timing<br>registers 1..4 (FMC_BTR1..4) and Section : SRAM/NOR-Flash write timing<br>registers 1..4 (FMC_BWTR1..4).<br>**Debug support**<br>Specified behavior of timers with complementary outputs in Section 38.16.2: Debug<br>support for timers, watchdog, bxCAN and I2C.<br>Updated DBG_TIMx_STOP bit description in Section 38.16.4: Debug MCU APB1<br>freeze register (DBGMCU_APB1_FZ) and Section 38.16.4: Debug MCU APB1<br>freeze register (DBGMCU_APB1_FZ).<br>**Electronic signature**<br>Updated Section 24.1: Unique device ID register (96 bits).|
|21-Apr-2017|14|Updated:<br>– Section 5.5.2: PWR power control/status register (PWR_CSR) for STM32F42xxx<br>and STM32F43xxx<br>– Section 6.3.14: RCC APB2 peripheral clock enable register (RCC_APB2ENR)<br>– Section 14.3.5: DAC output voltage<br>– Section 38.6.1: MCU device ID code<br>– Figure 237: RTC block diagram<br>Deleted:<br>– Section 7.3.15: RCC APB2 peripheral clock enable register(RCC_APB2ENR)|
|18-Jul-2017|15|Updated:<br>– Section 3.9.10: Flash option control register (FLASH_OPTCR) for STM32F42xxx<br>and STM32F43xxx<br>– OTG_FS USB configuration register (OTG_FS_GUSBCFG)<br>– Table 142: Error calculation for programmed baud rates at fPCLK = 42 MHz or<br>fPCLK = 84 Hz, oversampling by 16 and Table 143: Error calculation for<br>programmed baud rates at fPCLK = 42 MHz or fPCLK = 84 MHz, oversampling<br>by 8.|
|23-Apr-2018|16|Updated:<br>– Section 30.6.1: Status register (USART_SR)<br>– Section 34.16.4: Device-mode registers<br>– Section 34.17.6: Operational model<br>– Section 35.12.4: Device-mode registers<br>– Section 34: USB on-the-go full-speed (OTG_FS)<br>– Table 199: Host-mode control and status registers (CSRs)<br>– Table 205: OTG_FS register map and reset values<br>– Table 210: Device-mode control and status registers<br>– Table 215: OTG_HS register map and reset values<br>Added:<br>– Figure 412: SOF trigger output to TIM2 ITR1 connection<br>– RXOLNY register changed from SPI_CR2 to SPI_CR1 in Section 28.3.4:<br>Configuring the SPI for half-duplex communication and Unidirectional receive-<br>only procedure (BIDIMODE=0 and RXONLY=1)|


RM0090 Rev 21 1745/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|07-Jun-2018|17|Updated:<br>– Figure 16: Clock tree (STM32F42xxx an STM32F43xxx) and Figure 21: Clock<br>tree (STM32F405xx/07xx and STM32F415xx/17xx)<br>– Figure 27: Selecting an alternate function on STM32F42xxx and STM32F43xxx<br>– Table 61: Vector table for STM32F405xx/07xx and STM32F415xx/17xx and Table<br>62: Vector table for STM32F42xxx and STM32F43xxx<br>– Section 29.17.5: SAI xInterrupt mask register (SAI_xIM) where x is A or B<br>– Section 38.6.1: MCU device ID code|



1746/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**

|Date|Version|Changes|
|---|---|---|
|25-Feb-2019|18|**Section 6: Reset and clock control for STM32F42xxx and STM32F43xxx (RCC)**<br>Updated OTGHSULPILPEN bit description in RCC AHB1 peripheral clock enable in<br>low power mode register (RCC_AHB1LPENR) and OTGHSULPIEN bit description<br>in RCC AHB1 peripheral clock register (RCC_AHB1ENR).<br>**Section 7: Reset and clock control for  STM32F405xx/07xx and**<br>**STM32F415xx/17xx(RCC):**<br>Updated RCC APB2 peripheral clock enabled in low power mode register<br>(RCC_APB2LPENR) reset value.<br>Updated OTGHSULPILPEN bit description in RCC AHB1 peripheral clock enable in<br>low power mode register (RCC_AHB1LPENR) and OTGHSULPIEN bit description<br>in RCC AHB1 peripheral clock enable register (RCC_AHB1ENR).<br>**Section 13: Analog-to-digital converter (ADC)**<br>Update Section : Dual ADC mode.<br>**Section 17: Advanced-control timers (TIM1 and TIM8)**<br>Updated Figure 113: Capture/compare channel 1 main circuit.<br>Figure 19: General-purpose timers (TIM9 to TIM14)<br>Updated Figure 194: Capture/compare channel 1 main circuit.<br>**Section 34: USB on-the-go full-speed (OTG_FS)**<br>Updated Section : SETUP and OUT data transfers and Updated Section : IN data<br>transfers. Modified Table 200: Device-mode control and status registers.<br>Section 35: USB on-the-go high-speed (OTG_HS)<br>Updated Table 208: Core global control and status registers (CSRs) and Table 210:<br>Device-mode control and status registers.<br>Updated Section : OTG_HS device IN endpoint transmit FIFO size register<br>(OTG_HS_DIEPTXFx) (x = 1..5, where x is the FIFO_number), Section : OTG<br>device endpoint-x control register (OTG_HS_DIEPCTLx) (x = 0..5, where x =<br>Endpoint_number), Section : OTG_HS device endpoint-x control register<br>(OTG_HS_DOEPCTLx) (x = 1..5, where x = Endpoint_number), Section : OTG_HS<br>device endpoint-x interrupt register (OTG_HS_DIEPINTx) (x = 0..5, where x =<br>Endpoint_number), Section : OTG_HS device endpoint-x interrupt register<br>(OTG_HS_DOEPINTx) (x = 0..5, where x = Endpoint_number), Section : OTG_HS<br>device endpoint-x DMA address register (OTG_HS_DIEPDMAx /<br>OTG_HS_DOEPDMAx) (x = 0..5, where x = Endpoint_number).<br>Updated Section : SETUP and OUT data transfers and Section : IN data transfers.<br>**Section 38: Debug support (DBG)**<br>Updated REV_ID in DBGMCU_CR register.|



RM0090 Rev 21 1747/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|25-Feb-2021|19|Updated:<br>– Section 2: Memory and bus architecture:<br>– Figure 1: System architecture for STM32F405xx/07xx and STM32F415xx/17xx<br>devices<br>– Figure 2: System architecture for STM32F42xxx and STM32F43xxx devices<br>– Section 3: Embedded Flash memory interface:<br>– Table 16: Description of the option bytes (STM32F405xx/07xx and<br>STM32F415xx/17xx)<br>– Table 17: Description of the option bytes  (STM32F42xxx and STM32F43xxx)<br>– Section 12: Interrupts and events:<br>– Table 61: Vector table for STM32F405xx/07xx and STM32F415xx/17xx<br>– Table 62: Vector table for STM32F42xxx and STM32F43xxx<br>– Section 13: Analog-to-digital converter (ADC):<br>– Section 13.3.5: Continuous conversion mode<br>– Section 13.8.1: Using the DMA<br>– Section 13.10: Temperature sensor<br>– Section 17: Advanced-control timers (TIM1 and TIM8):<br>– Figure 86: Advanced-control timer block diagram<br>– Section 17.4.9: TIM1 and TIM8 capture/compare enable register (TIMx_CCER)<br>– Section 27: Inter-integrated circuit (I2C) interface:<br>– Section 27.6.2: I2C Control register 2 (I2C_CR2)<br>– Section 27.6.8: I2C Clock control register (I2C_CCR)<br>– Section 31: Secure digital input/output interface (SDIO):<br>– Section 31.9.2: SDI clock control register (SDIO_CLKCR)<br>– Section 32: Controller area network (bxCAN):<br>– Section 32.4.1: Initialization mode<br>– Section 33: Ethernet (ETH): media access control (MAC) with DMA controller:<br>– Section : TxDMA operation: default (non-OSF) mode<br>– Section : Normal Tx DMA descriptors<br>– Section 35: USB on-the-go high-speed (OTG_HS):<br>– Section : Host port power<br>– Section : OTG_HS core interrupt register (OTG_HS_GINTSTS)<br>– Section : OTG_HS all endpoints interrupt mask register (OTG_HS_DAINTMSK)<br>– Table 215: OTG_HS register map and reset values<br>– Section 35.13.2: Host initialization<br>– Figure 416: Transmit FIFO write task<br>– Figure 417: Receive FIFO read task<br>– Figure 426: Receive FIFO packet read in slave mode<br>– Figure 427: Processing a SETUP packet<br>– Section 38: Debug support (DBG):<br>– Section : DBGMCU_IDCODE|



1748/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**





|Date|Version|Changes|
|---|---|---|
|05-Feb-2024|20|_Section : Introduction_:<br>– Mentioned that the microcontrollers include ST state-of-the-art patented<br>technology<br>– Added errata sheets in the list of reference documents.<br>**_Section 2: Memory and bus architecture_**<br>–_ Section 2.3.1: Embedded SRAM_, updated the SRAM that can be accessed<br>through System or I-Code/D-Code bus.<br>**_Section 3.4: Embedded flash memory in STM32F42xxx and STM32F43xxx_**<br>– Updated Bank 2 section 14 base address in_Table 12: Flash module - 2 Mbyte_<br>_dual bank organization (STM32F42xxx and STM32F43xxx)_.<br>– Specified that dual bank organization is not available on 512 Kbyte devices, and<br>added_Table 16: 512 Kbyte single bank flash memory organization_<br>_(STM32F42xxx and STM32F43xxx)_.<br>– Updated_Section 3.8.2: Program/erase parallelism_**.**<br>– In_Section 3.9.3: Read protection (RDP)_, added note concerning RDP when<br>debugger is connected through JTAG/SWD.<br>**_Section 5: Power controller (PWR)_**<br>– Updated_Figure 12: Power-on reset/power-down reset waveform_.<br>– Updated no external battery use case in_Section 5.1.2: Battery backup domain_.<br>– Updated DBP bit description in_PWR power control register (PWR_CR) for_<br>_STM32F405xx/07xx and STM32F415xx/17xx_ and_PWR power control register_<br>_(PWR_CR) for STM32F42xxx and STM32F43xxx_.<br>– Updated BRE bit description in_PWR power control/status register (PWR_CSR)_<br>_for STM32F405xx/07xx and STM32F415xx/17xx_ and_PWR power control/status_<br>_register (PWR_CSR) for STM32F42xxx and STM32F43xxx_.<br>**_Section 6: Reset and clock control for  STM32F42xxx and STM32F43xxx and_**<br>**_NA(RCC)_**<br>– Updated_Section 6.1.1: System reset_ and_Section 6.1.3: Backup domain reset_.<br>– Updated ethernet PTP clock in_Figure 16: Clock tree_.<br>– Added note regarding backup domain reset in BDRST bit of_RCC Backup domain_<br>_control register (RCC_BDCR)_.<br>– Added register reset values in_Table 38: RCC register map and reset values for_<br>_STM32F42xxx and STM32F43xxx_<br>**_Section 7: Reset and clock control for  STM32F405xx/07xx and_**<br>**_STM32F415xx/17xx(RCC)_**<br>– Updated_Section 7.1.1: System reset_ and_Section 7.1.3: Backup domain reset_.<br>– Updated ethernet PTP clock in_Figure 21: Clock tree_<br>– Added note regarding backup domain reset in BDRST bit of_RCC Backup domain_<br>_control register (RCC_BDCR)_.<br>– Added register reset values in_Table 39: RCC register map and reset values for_<br>_STM32F405xx/07xx and STM32F415xx/17xx_|


RM0090 Rev 21 1749/1757



1751


**Revision history** **RM0090**


**Table 316. Document revision history** **(continued)**






|Date|Version|Changes|
|---|---|---|
|05-Feb-2024|20<br>(continued)|**_Section 10: DMA controller (DMA)_**<br>Updated_DMA stream x FIFO control register (DMA_SxFCR) (x = 0..7)_ address<br>offset.<br>**_Section 12: Interrupts and events_**<br>Changed_Pending register (EXTI_PR)_ reset value to 0x0000 0000.<br>**_Section 17: Advanced-control timers (TIM1 and TIM8)_**<br>Updated_Section 17.3.7: PWM input mode_.<br>Updated SMS in_Section 17.4.3: TIM1 and TIM8 slave mode control register_<br>_(TIMx_SMCR)_.<br>Updated OC1PE in_Section 17.4.7: TIM1 and TIM8 capture/compare mode register_<br>_1 (TIMx_CCMR1)_.<br>**_Section 22: Window watchdog (WWDG)_**<br>Updated tWWDG equation in_Section 22.4: How to program the watchdog timeout_.<br>**_Section 26: Real-time clock (RTC)_**<br>– Updated HSE clock in_Figure 237: RTC block diagram (NA devices)_.<br>– Updated_Section 26.3.6: Reading the calendar_.<br>**_Section 29: Serial audio interface (SAI)_**<br>– In the whole section, replaced TDM by free protocol mode.<br>– In_Section 29.18.4: SAI x frame configuration register (SAI_XFRCR) where x is A_<br>_or B_, specified tha_t FRL[7:0] must be configured when the audio block is_<br>_disabled._<br>**_Section 34: USB on-the-go full-speed (OTG_FS)_**<br>– Updated_Figure 392: Device-mode FIFO address mapping and AHB FIFO_<br>_access mapping_.<br>– Modified_OTG_FS USB configuration register_<br>_(OTG_FS_GUSBCFG)_OTG_FS_GUSBCFG reset value.<br>**_Section 33: Ethernet (ETH): media access control (MAC) with DMA controller_**<br>Updated bits that control the checksum in_Section : Transmit checksum offload_<br>**_Section 38: Debug support (DBG)_**<br>Removed note on APB bridge write buffer after_Table 302: Flexible SWJ-DP pin_<br>_assignment_<br>Updated REV_ID[15:0] in_Section : DBGMCU_IDCODE_<br>**_Section 39: Device electronic signature_**<br>Updated_Section 39.1: Unique device ID register (96 bits)_<br>Added_Section 40: Important security notice_.|



1750/1757 RM0090 Rev 21


**RM0090** **Revision history**


**Table 316. Document revision history** **(continued)**

|Date|Version|Changes|
|---|---|---|
|07-Jun-2024|21|Updated the note in Bit[11:0] description of_Section 27.6.8: I2C Clock control_<br>_register (I2C_CCR)_.<br>Fixed typo in_Section 12.1.3: Interrupt and exception vectors_.|



RM0090 Rev 21 1751/1757



1751


**Index** **RM0090**

# **Index**



**A**


ADC_CCR . . . . . . . . . . . . . . . . . . . . . . . . . . .430
ADC_CDR . . . . . . . . . . . . . . . . . . . . . . . . . . .433
ADC_CR1 . . . . . . . . . . . . . . . . . . . . . . . . . . .419
ADC_CR2 . . . . . . . . . . . . . . . . . . . . . . . . . . .421
ADC_CSR . . . . . . . . . . . . . . . . . . . . . . . . . . .429
ADC_DR . . . . . . . . . . . . . . . . . . . . . . . . . . . .428
ADC_HTR . . . . . . . . . . . . . . . . . . . . . . . . . . .424
ADC_JDRx . . . . . . . . . . . . . . . . . . . . . . . . . . .428
ADC_JOFRx . . . . . . . . . . . . . . . . . . . . . . . . .424
ADC_JSQR . . . . . . . . . . . . . . . . . . . . . . . . . .427
ADC_LTR . . . . . . . . . . . . . . . . . . . . . . . . . . . .425
ADC_SMPR1 . . . . . . . . . . . . . . . . . . . . . . . . .423
ADC_SMPR2 . . . . . . . . . . . . . . . . . . . . . . . . .423
ADC_SQR1 . . . . . . . . . . . . . . . . . . . . . . . . . .425
ADC_SQR2 . . . . . . . . . . . . . . . . . . . . . . . . . .426
ADC_SQR3 . . . . . . . . . . . . . . . . . . . . . . . . . .426
ADC_SR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .418


**C**


CAN_BTR . . . . . . . . . . . . . . . . . . . . . . . . . .1109
CAN_ESR . . . . . . . . . . . . . . . . . . . . . . . . . .1108
CAN_FA1R . . . . . . . . . . . . . . . . . . . . . . . . .1119
CAN_FFA1R . . . . . . . . . . . . . . . . . . . . . . . .1119
CAN_FiRx . . . . . . . . . . . . . . . . . . . . . . . . . .1120
CAN_FM1R . . . . . . . . . . . . . . . . . . . . . . . . .1118
CAN_FMR . . . . . . . . . . . . . . . . . . . . . . . . . .1117
CAN_FS1R . . . . . . . . . . . . . . . . . . . . . . . . .1118
CAN_IER . . . . . . . . . . . . . . . . . . . . . . . . . . .1106
CAN_MCR . . . . . . . . . . . . . . . . . . . . . . . . . .1100
CAN_MSR . . . . . . . . . . . . . . . . . . . . . . . . . .1102
CAN_RDHxR . . . . . . . . . . . . . . . . . . . . . . . .1116
CAN_RDLxR . . . . . . . . . . . . . . . . . . . . . . . .1116
CAN_RDTxR . . . . . . . . . . . . . . . . . . . . . . . .1115
CAN_RF0R . . . . . . . . . . . . . . . . . . . . . . . . .1105
CAN_RF1R . . . . . . . . . . . . . . . . . . . . . . . . .1106
CAN_RIxR . . . . . . . . . . . . . . . . . . . . . . . . . .1114
CAN_TDHxR . . . . . . . . . . . . . . . . . . . . . . . .1113
CAN_TDLxR . . . . . . . . . . . . . . . . . . . . . . . .1113
CAN_TDTxR . . . . . . . . . . . . . . . . . . . . . . . .1112
CAN_TIxR . . . . . . . . . . . . . . . . . . . . . . . . . .1111
CAN_TSR . . . . . . . . . . . . . . . . . . . . . . . . . .1103
CRC_DR . . . . . . . . . . . . . . . . . . . . . . . . . . . .115
CRC_IDR . . . . . . . . . . . . . . . . . . . . . . . . . . . .115
CRYP_CR . . . . . . . . . . . . . . . . . . . . . . .751, 753
CRYP_DIN . . . . . . . . . . . . . . . . . . . . . . . . . . .757
CRYP_DMACR . . . . . . . . . . . . . . . . . . . . . . .759



CRYP_DOUT . . . . . . . . . . . . . . . . . . . . . . . . 758
CRYP_IMSCR . . . . . . . . . . . . . . . . . . . . . . . . 759
CRYP_IV0LR . . . . . . . . . . . . . . . . . . . . . . . . 763
CRYP_IV0RR . . . . . . . . . . . . . . . . . . . . . . . . 763
CRYP_IV1LR . . . . . . . . . . . . . . . . . . . . . . . . 764
CRYP_IV1RR . . . . . . . . . . . . . . . . . . . . . . . . 764
CRYP_K0LR . . . . . . . . . . . . . . . . . . . . . . . . . 761
CRYP_K0RR . . . . . . . . . . . . . . . . . . . . . . . . . 761
CRYP_K1LR . . . . . . . . . . . . . . . . . . . . . . . . . 762
CRYP_K1RR . . . . . . . . . . . . . . . . . . . . . . . . . 762
CRYP_K2LR . . . . . . . . . . . . . . . . . . . . . . . . . 762
CRYP_K2RR . . . . . . . . . . . . . . . . . . . . . . . . . 762
CRYP_K3LR . . . . . . . . . . . . . . . . . . . . . . . . . 762
CRYP_K3RR . . . . . . . . . . . . . . . . . . . . . . . . . 763
CRYP_MISR . . . . . . . . . . . . . . . . . . . . . . . . . 760
CRYP_RISR . . . . . . . . . . . . . . . . . . . . . . . . . 760
CRYP_SR . . . . . . . . . . . . . . . . . . . . . . . . . . . 756


**D**


DAC_CR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 448
DAC_DHR12L1 . . . . . . . . . . . . . . . . . . . . . . . 452
DAC_DHR12L2 . . . . . . . . . . . . . . . . . . . . . . . 453
DAC_DHR12LD . . . . . . . . . . . . . . . . . . . . . . 454
DAC_DHR12R1 . . . . . . . . . . . . . . . . . . . . . . 451
DAC_DHR12R2 . . . . . . . . . . . . . . . . . . . . . . 453
DAC_DHR12RD . . . . . . . . . . . . . . . . . . . . . . 454
DAC_DHR8R1 . . . . . . . . . . . . . . . . . . . . . . . 452
DAC_DHR8R2 . . . . . . . . . . . . . . . . . . . . . . . 453
DAC_DHR8RD . . . . . . . . . . . . . . . . . . . . . . . 455
DAC_DOR1 . . . . . . . . . . . . . . . . . . . . . . . . . . 455
DAC_DOR2 . . . . . . . . . . . . . . . . . . . . . . . . . . 455
DAC_SR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 456
DAC_SWTRIGR . . . . . . . . . . . . . . . . . . . . . . 451
DBGMCU_APB1_FZ . . . . . . . . . . . . . . . . . . 1708
DBGMCU_APB2_FZ . . . . . . . . . . . . . . . . . . 1709
DBGMCU_CR . . . . . . . . . . . . . . . . . . . . . . . 1706
DBGMCU_IDCODE . . . . . . . . . . . . . . . . . . 1693
DCMI_CR . . . . . . . . . . . . . . . . . . . . . . . . . . . 470
DCMI_CWSIZE . . . . . . . . . . . . . . . . . . . . . . . 480
DCMI_CWSTRT . . . . . . . . . . . . . . . . . . . . . . 480
DCMI_DR . . . . . . . . . . . . . . . . . . . . . . . . . . . 481
DCMI_ESCR . . . . . . . . . . . . . . . . . . . . . . . . . 478
DCMI_ESUR . . . . . . . . . . . . . . . . . . . . . . . . . 479
DCMI_ICR . . . . . . . . . . . . . . . . . . . . . . . . . . . 477
DCMI_IER . . . . . . . . . . . . . . . . . . . . . . . . . . . 475
DCMI_MIS . . . . . . . . . . . . . . . . . . . . . . . . . . . 476
DCMI_RIS . . . . . . . . . . . . . . . . . . . . . . . . . . . 474
DCMI_SR . . . . . . . . . . . . . . . . . . . . . . . . . . . 473



1752/1751 RM0090 Rev 21


**RM0090** **Index**



DMA_HIFCR . . . . . . . . . . . . . . . . . . . . . . . . .330
DMA_HISR . . . . . . . . . . . . . . . . . . . . . . . . . . .329
DMA_LIFCR . . . . . . . . . . . . . . . . . . . . . . . . . .330
DMA_LISR . . . . . . . . . . . . . . . . . . . . . . . . . . .328
DMA_SxCR . . . . . . . . . . . . . . . . . . . . . . . . . .331
DMA_SxFCR . . . . . . . . . . . . . . . . . . . . . . . . .336
DMA_SxM0AR . . . . . . . . . . . . . . . . . . . . . . . .335
DMA_SxM1AR . . . . . . . . . . . . . . . . . . . . . . . .335
DMA_SxNDTR . . . . . . . . . . . . . . . . . . . . . . . .334
DMA_SxPAR . . . . . . . . . . . . . . . . . . . . . . . . .335


**E**


ETH_DMABMR . . . . . . . . . . . . . . . . . . . . . .1226
ETH_DMACHRBAR . . . . . . . . . . . . . . . . . . .1239
ETH_DMACHRDR . . . . . . . . . . . . . . . . . . . .1238
ETH_DMACHTBAR . . . . . . . . . . . . . . . . . . .1238
ETH_DMACHTDR . . . . . . . . . . . . . . . . . . . .1238
ETH_DMAIER . . . . . . . . . . . . . . . . . . . . . . .1235
ETH_DMAMFBOCR . . . . . . . . . . . . . . . . . .1237
ETH_DMAOMR . . . . . . . . . . . . . . . . . . . . . .1232
ETH_DMARDLAR . . . . . . . . . . . . . . . . . . . .1228
ETH_DMARPDR . . . . . . . . . . . . . . . . . . . . .1228
ETH_DMARSWTR . . . . . . . . . . . . . . . . . . . .1237
ETH_DMASR . . . . . . . . . . . . . . . . . . . . . . . .1229
ETH_DMATDLAR . . . . . . . . . . . . . . . . . . . .1229
ETH_DMATPDR . . . . . . . . . . . . . . . . . . . . .1227
ETH_MACA0HR . . . . . . . . . . . . . . . . . . . . .1208
ETH_MACA0LR . . . . . . . . . . . . . . . . . . . . . .1209
ETH_MACA1HR . . . . . . . . . . . . . . . . . . . . .1209
ETH_MACA1LR . . . . . . . . . . . . . . . . . . . . . .1210
ETH_MACA2HR . . . . . . . . . . . . . . . . . . . . .1210
ETH_MACA2LR . . . . . . . . . . . . . . . . . . . . . .1211
ETH_MACA3HR . . . . . . . . . . . . . . . . . . . . .1212
ETH_MACA3LR . . . . . . . . . . . . . . . . . . . . . .1212
ETH_MACCR . . . . . . . . . . . . . . . . . . . . . . . .1194
ETH_MACDBGR . . . . . . . . . . . . . . . . . . . . .1205
ETH_MACFCR . . . . . . . . . . . . . . . . . . . . . . .1201
ETH_MACFFR . . . . . . . . . . . . . . . . . . . . . . .1197
ETH_MACHTHR . . . . . . . . . . . . . . . . . . . . .1198
ETH_MACHTLR . . . . . . . . . . . . . . . . . . . . . .1199
ETH_MACIMR . . . . . . . . . . . . . . . . . . . . . . .1208
ETH_MACMIIAR . . . . . . . . . . . . . . . . . . . . .1199
ETH_MACMIIDR . . . . . . . . . . . . . . . . . . . . .1200
ETH_MACPMTCSR . . . . . . . . . . . . . . . . . . .1204
ETH_MACRWUFFR . . . . . . . . . . . . . . . . . .1203
ETH_MACSR . . . . . . . . . . . . . . . . . . . . . . . .1207
ETH_MACVLANTR . . . . . . . . . . . . . . . . . . .1202
ETH_MMCCR . . . . . . . . . . . . . . . . . . . . . . .1213
ETH_MMCRFAECR . . . . . . . . . . . . . . . . . . .1218
ETH_MMCRFCECR . . . . . . . . . . . . . . . . . .1217
ETH_MMCRGUFCR . . . . . . . . . . . . . . . . . .1218



ETH_MMCRIMR . . . . . . . . . . . . . . . . . . . . . 1215
ETH_MMCRIR . . . . . . . . . . . . . . . . . . . . . . 1213
ETH_MMCTGFCR . . . . . . . . . . . . . . . . . . . 1217
ETH_MMCTGFMSCCR . . . . . . . . . . . . . . . 1217
ETH_MMCTGFSCCR . . . . . . . . . . . . . . . . . 1216
ETH_MMCTIMR . . . . . . . . . . . . . . . . . . . . . 1216
ETH_MMCTIR . . . . . . . . . . . . . . . . . . . . . . . 1214
ETH_PTPPPSCR . . . . . . . . . . . . . . . . . . . . 1225
ETH_PTPSSIR . . . . . . . . . . . . . . . . . . . . . . 1221
ETH_PTPTSAR . . . . . . . . . . . . . . . . . . . . . . 1223
ETH_PTPTSCR . . . . . . . . . . . . . . . . . . . . . 1218
ETH_PTPTSHR . . . . . . . . . . . . . . . . . . . . . 1221
ETH_PTPTSHUR . . . . . . . . . . . . . . . . . . . . 1222
ETH_PTPTSLR . . . . . . . . . . . . . . . . . . . . . . 1222
ETH_PTPTSLUR . . . . . . . . . . . . . . . . . . . . 1223
ETH_PTPTSSR . . . . . . . . . . . . . . . . . . . . . . 1224
ETH_PTPTTHR . . . . . . . . . . . . . . . . . . . . . . 1224
ETH_PTPTTLR . . . . . . . . . . . . . . . . . . . . . . 1224
EXTI_EMR . . . . . . . . . . . . . . . . . . . . . . . . . . 387
EXTI_FTSR . . . . . . . . . . . . . . . . . . . . . . . . . . 388
EXTI_IMR . . . . . . . . . . . . . . . . . . . . . . . . . . . 387
EXTI_PR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 389
EXTI_RTSR . . . . . . . . . . . . . . . . . . . . . . . . . . 388
EXTI_SWIER . . . . . . . . . . . . . . . . . . . . . . . . . 389


**F**


FLITF_FCR . . . . . . . . . . . . . . . . . . . . . . 104, 106
FLITF_FKEYR . . . . . . . . . . . . . . . . . . . . . . . . 101
FLITF_FOPTCR . . . . . . . . . . . . . . 107, 109, 111
FLITF_FOPTKEYR . . . . . . . . . . . . . . . . . . . . 101
FLITF_FSR . . . . . . . . . . . . . . . . . . . . . . 102 - 103
FSMC_BCR1..4 . . . . . . . . . . . . . . . . . 1580, 1643
FSMC_BTR1..4 . . . . . . . . . . . . . . . . . 1583, 1645
FSMC_BWTR1..4 . . . . . . . . . . . . . . . 1586, 1649
FSMC_PCR2..4 . . . . . . . . . . . . . . . . . . . . . . 1596
FSMC_PMEM2..4 . . . . . . . . . . . . . . . . . . . . 1598
FSMC_SR2..4 . . . . . . . . . . . . . . . . . . . . . . . 1597


**G**


GPIOx_AFRH . . . . . . . . . . . . . . . . . . . . . . . . 289
GPIOx_AFRL . . . . . . . . . . . . . . . . . . . . . . . . 288
GPIOx_BSRR . . . . . . . . . . . . . . . . . . . . . . . . 287
GPIOx_IDR . . . . . . . . . . . . . . . . . . . . . . . . . . 286
GPIOx_LCKR . . . . . . . . . . . . . . . . . . . . . . . . 287
GPIOx_MODER . . . . . . . . . . . . . . . . . . . . . . 284
GPIOx_ODR . . . . . . . . . . . . . . . . . . . . . . . . . 286
GPIOx_OSPEEDR . . . . . . . . . . . . . . . . . . . . 285
GPIOx_OTYPER . . . . . . . . . . . . . . . . . . . . . . 284
GPIOx_PUPDR . . . . . . . . . . . . . . . . . . . . . . . 285



RM0090 Rev 21 1753/1751


**Index** **RM0090**



**H**


HASH_CR . . . . . . . . . . . . . . . . . . . . . . .785, 788
HASH_CSRx . . . . . . . . . . . . . . . . . . . . . . . . .797
HASH_DIN . . . . . . . . . . . . . . . . . . . . . . . . . . .791
HASH_HR0 . . . . . . . . . . . . . . . . . . . . . . . . . .793
HASH_HR1 . . . . . . . . . . . . . . . . . . . . . . 793 - 794
HASH_HR2 . . . . . . . . . . . . . . . . . . . . . . 793 - 794
HASH_HR3 . . . . . . . . . . . . . . . . . . . . . . . . . .794
HASH_HR4 . . . . . . . . . . . . . . . . . . . . . . . . . .794
HASH_IMR . . . . . . . . . . . . . . . . . . . . . . . . . . .795
HASH_SR . . . . . . . . . . . . . . . . . . . . . . . . . . .796
HASH_STR . . . . . . . . . . . . . . . . . . . . . . . . . .792


**I**


I2C_CCR . . . . . . . . . . . . . . . . . . . . . . . . . . . .873
I2C_CR1 . . . . . . . . . . . . . . . . . . . . . . . . . . . .863
I2C_CR2 . . . . . . . . . . . . . . . . . . . . . . . . . . . .865
I2C_DR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .868
I2C_OAR1 . . . . . . . . . . . . . . . . . . . . . . . . . . .867
I2C_OAR2 . . . . . . . . . . . . . . . . . . . . . . . . . . .867
I2C_SR1 . . . . . . . . . . . . . . . . . . . . . . . . . . . . .868
I2C_SR2 . . . . . . . . . . . . . . . . . . . . . . . . . . . . .871
I2C_TRISE . . . . . . . . . . . . . . . . . . . . . . . . . . .874
IWDG_KR . . . . . . . . . . . . . . . . . . . . . . . . . . .713
IWDG_PR . . . . . . . . . . . . . . . . . . . . . . . . . . .713
IWDG_RLR . . . . . . . . . . . . . . . . . . . . . . . . . .714
IWDG_SR . . . . . . . . . . . . . . . . . . . . . . . . . . .714


**O**


OTG_FS_CID . . . . . . . . . . . . . . . . . . . . . . . .1293
OTG_FS_DAINT . . . . . . . . . . . . . . . . . . . . .1310
OTG_FS_DAINTMSK . . . . . . . . . . . . . . . . .1311
OTG_FS_DCFG . . . . . . . . . . . . . . . . . . . . . .1305
OTG_FS_DCTL . . . . . . . . . . . . . . . . . . . . . .1306
OTG_FS_DIEPCTL0 . . . . . . . . . . . . . . . . . .1312
OTG_FS_DIEPCTLx . . . . . . . . . . . . . . . . . .1314
OTG_FS_DIEPEMPMSK . . . . . . . . . . . . . . .1312
OTG_FS_DIEPINTx . . . . . . . . . . . . . . . . . . .1321
OTG_FS_DIEPMSK . . . . . . . . . . . . . . . . . . .1308
OTG_FS_DIEPTSIZ0 . . . . . . . . . . . . . . . . . .1323
OTG_FS_DIEPTSIZx . . . . . . . . . . . . . . . . . .1326
OTG_FS_DIEPTXF0 . . . . . . . . . . . . . . . . . .1291
OTG_FS_DIEPTXFx . . . . . . . . . . . . . . . . . .1294
OTG_FS_DOEPCTL0 . . . . . . . . . . . . . . . . .1317
OTG_FS_DOEPCTLx . . . . . . . . . . . . . . . . .1318
OTG_FS_DOEPINTx . . . . . . . . . . . . . . . . . .1322
OTG_FS_DOEPMSK . . . . . . . . . . . . . . . . . .1309
OTG_FS_DOEPTSIZ0 . . . . . . . . . . . . . . . . .1325
OTG_FS_DOEPTSIZx . . . . . . . . . . . . . . . . .1327
OTG_FS_DSTS . . . . . . . . . . . . . . . . . . . . . .1307



OTG_FS_DTXFSTSx . . . . . . . . . . . . . . . . . 1327
OTG_FS_DVBUSDIS . . . . . . . . . . . . . . . . . 1311
OTG_FS_DVBUSPULSE . . . . . . . . . . . . . . 1311
OTG_FS_GAHBCFG . . . . . . . . . . . . . . . . . 1277
OTG_FS_GCCFG . . . . . . . . . . . . . . . . . . . . 1292
OTG_FS_GINTMSK . . . . . . . . . . . . . . . . . . 1286
OTG_FS_GINTSTS . . . . . . . . . . . . . . . . . . 1282
OTG_FS_GOTGCTL . . . . . . . . . . . . . . . . . . 1274
OTG_FS_GOTGINT . . . . . . . . . . . . . . . . . . 1275
OTG_FS_GRSTCTL . . . . . . . . . . . . . . . . . . 1280
OTG_FS_GRXFSIZ . . . . . . . . . . . . . . . . . . 1290
OTG_FS_GRXSTSP . . . . . . . . . . . . . . . . . . 1289
OTG_FS_GRXSTSR . . . . . . . . . . . . . . . . . . 1289
OTG_FS_GUSBCFG . . . . . . . . . . . . . . . . . 1278
OTG_FS_HAINT . . . . . . . . . . . . . . . . . . . . . 1297
OTG_FS_HAINTMSK . . . . . . . . . . . . . . . . . 1298
OTG_FS_HCCHARx . . . . . . . . . . . . . . . . . . 1301
OTG_FS_HCFG . . . . . . . . . . . . . . . . . . . . . 1295
OTG_FS_HCINTMSKx . . . . . . . . . . . . . . . . 1303
OTG_FS_HCINTx . . . . . . . . . . . . . . . . . . . . 1302
OTG_FS_HCTSIZx . . . . . . . . . . . . . . . . . . . 1304
OTG_FS_HFIR . . . . . . . . . . . . . . . . . . . . . . 1295
OTG_FS_HFNUM . . . . . . . . . . . . . . . . . . . . 1296
OTG_FS_HNPTXFSIZ . . . . . . . . . . . . . . . . 1291
OTG_FS_HNPTXSTS . . . . . . . . . . . . . . . . . 1291
OTG_FS_HPRT . . . . . . . . . . . . . . . . . . . . . 1298
OTG_FS_HPTXFSIZ . . . . . . . . . . . . . . . . . . 1294
OTG_FS_HPTXSTS . . . . . . . . . . . . . . . . . . 1296
OTG_FS_PCGCCTL . . . . . . . . . . . . . . . . . . 1328
OTG_HS_CID . . . . . . . . . . . . . . . . . . . . . . . 1432
OTG_HS_DAINT . . . . . . . . . . . . . . . . . . . . . 1453
OTG_HS_DAINTMSK . . . . . . . . . . . . . . . . . 1454
OTG_HS_DCFG . . . . . . . . . . . . . . . . . . . . . 1446
OTG_HS_DCTL . . . . . . . . . . . . . . . . . . . . . 1448
OTG_HS_DEACHINT . . . . . . . . . . . . . . . . . 1457
OTG_HS_DEACHINTMSK . . . . . . . . . . . . . 1458
OTG_HS_DIEPCTLx . . . . . . . . . . . . . . . . . . 1460
OTG_HS_DIEPDMAx . . . . . . . . . . . . . . . . . 1474
OTG_HS_DIEPEACHMSK1 . . . . . . . . . . . . 1458
OTG_HS_DIEPEMPMSK . . . . . . . . . . . . . . 1457
OTG_HS_DIEPINTx . . . . . . . . . . . . . . . . . . 1467
OTG_HS_DIEPMSK . . . . . . . . . . . . . . . . . . 1451
OTG_HS_DIEPTSIZ0 . . . . . . . . . . . . . . . . . 1470
OTG_HS_DIEPTSIZx . . . . . . . . . . . . . . . . . 1472
OTG_HS_DIEPTXFx . . . . . . . . . . . . . . . . . . 1433
OTG_HS_DOEPCTL0 . . . . . . . . . . . . . . . . . 1463
OTG_HS_DOEPCTLx . . . . . . . . . . . . . . . . . 1464
OTG_HS_DOEPDMAx . . . . . . . . . . . . . . . . 1474
OTG_HS_DOEPEACHMSK1 . . . . . . . . . . . 1459
OTG_HS_DOEPINTx . . . . . . . . . . . . . . . . . 1469
OTG_HS_DOEPMSK . . . . . . . . . . . . . . . . . 1452
OTG_HS_DOEPTSIZ0 . . . . . . . . . . . . . . . . 1471



1754/1751 RM0090 Rev 21


**RM0090** **Index**



OTG_HS_DOEPTSIZx . . . . . . . . . . . . . . . . .1473
OTG_HS_DSTS . . . . . . . . . . . . . . . . . . . . . .1450
OTG_HS_DTHRCTL . . . . . . . . . . . . . . . . . .1456
OTG_HS_DTXFSTSx . . . . . . . . . . . . . . . . .1473
OTG_HS_DVBUSDIS . . . . . . . . . . . . . . . . .1454
OTG_HS_DVBUSPULSE . . . . . . . . . . . . . .1455
OTG_HS_GAHBCFG . . . . . . . . . . . . . . . . . .1414
OTG_HS_GCCFG . . . . . . . . . . . . . . . . . . . .1431
OTG_HS_GINTMSK . . . . . . . . . . . . . . . . . .1425
OTG_HS_GINTSTS . . . . . . . . . . . . . . . . . . .1421
OTG_HS_GNPTXFSIZ . . . . . . . . . . . . . . . .1430
OTG_HS_GNPTXSTS . . . . . . . . . . . . . . . . .1430
OTG_HS_GOTGCTL . . . . . . . . . . . . . . . . . .1411
OTG_HS_GOTGINT . . . . . . . . . . . . . . . . . .1412
OTG_HS_GRSTCTL . . . . . . . . . . . . . . . . . .1418
OTG_HS_GRXFSIZ . . . . . . . . . . . . . . . . . . .1429
OTG_HS_GRXSTSP . . . . . . . . . . . . . . . . . .1428
OTG_HS_GRXSTSR . . . . . . . . . . . . . . . . . .1428
OTG_HS_GUSBCFG . . . . . . . . . . . . . . . . . .1415
OTG_HS_HAINT . . . . . . . . . . . . . . . . . . . . .1437
OTG_HS_HAINTMSK . . . . . . . . . . . . . . . . .1437
OTG_HS_HCCHARx . . . . . . . . . . . . . . . . . .1440
OTG_HS_HCDMAx . . . . . . . . . . . . . . . . . . .1446
OTG_HS_HCFG . . . . . . . . . . . . . . . . . . . . .1433
OTG_HS_HCINTMSKx . . . . . . . . . . . . . . . .1444
OTG_HS_HCINTx . . . . . . . . . . . . . . . . . . . .1443
OTG_HS_HCSPLTx . . . . . . . . . . . . . . . . . .1442
OTG_HS_HCTSIZx . . . . . . . . . . . . . . . . . . .1445
OTG_HS_HFIR . . . . . . . . . . . . . . . . . . . . . .1435
OTG_HS_HFNUM . . . . . . . . . . . . . . . . . . . .1435
OTG_HS_HPRT . . . . . . . . . . . . . . . . . . . . . .1438
OTG_HS_HPTXFSIZ . . . . . . . . . . . . . . . . . .1432
OTG_HS_HPTXSTS . . . . . . . . . . . . . . . . . .1436
OTG_HS_PCGCCTL . . . . . . . . . . . . . . . . . .1475
OTG_HS_TX0FSIZ . . . . . . . . . . . . . . . . . . .1430


**P**


PWR_CR . . . . . . . . . . . . . . . . . . . . . . . .142, 146
PWR_CSR . . . . . . . . . . . . . . . . . . . . . . .143, 149


**R**


RCC_AHB1ENR . . . . . . . . . . . . . . . . . .182, 244
RCC_AHB1LPENR . . . . . . . . . . . . . . . .191, 252
RCC_AHB1RSTR . . . . . . . . . . . . . . . . .172, 235
RCC_AHB2ENR . . . . . . . . . . . . . . . . . .184, 246
RCC_AHB2LPENR . . . . . . . . . . . . . . . .194, 254
RCC_AHB2RSTR . . . . . . . . . . . . . . . . .175, 238
RCC_AHB3ENR . . . . . . . . . . . . . . . . . .185, 247
RCC_AHB3LPENR . . . . . . . . . . . . . . . .195, 255
RCC_AHB3RSTR . . . . . . . . . . . . . . . . .176, 239
RCC_APB1ENR . . . . . . . . . . . . . . . . . . .185, 247



RCC_APB1LPENR . . . . . . . . . . . . . . . . 195, 256
RCC_APB1RSTR . . . . . . . . . . . . . . . . . 176, 239
RCC_APB2ENR . . . . . . . . . . . . . . . . . . 189, 250
RCC_APB2LPENR . . . . . . . . . . . . . . . . 199, 259
RCC_APB2RSTR . . . . . . . . . . . . . . . . . 180, 242
RCC_BDCR . . . . . . . . . . . . . . . . . . . . . 201, 261
RCC_CFGR . . . . . . . . . . . . . . . . . . . . . 167, 230
RCC_CIR . . . . . . . . . . . . . . . . . . . . . . . 169, 232
RCC_CR . . . . . . . . . . . . . . . . . . . . . . . . 163, 226
RCC_CSR . . . . . . . . . . . . . . . . . . . . . . . 202, 262
RCC_PLLCFGR . . . . . .165, 205, 208, 228, 265
RCC_SSCGR . . . . . . . . . . . . . . . . . . . . 204, 264
RNG_CR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 772
RNG_DR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 773
RNG_SR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 772
RTC_ALRMAR . . . . . . . . . . . . . . . . . . . . . . . 828
RTC_ALRMBR . . . . . . . . . . . . . . . . . . . . . . . 829
RTC_ALRMBSSR . . . . . . . . . . . . . . . . . . . . . 838
RTC_BKxR . . . . . . . . . . . . . . . . . . . . . . . . . . 839
RTC_CALIBR . . . . . . . . . . . . . . . . . . . . . . . . 827
RTC_CALR . . . . . . . . . . . . . . . . . . . . . . . . . . 833
RTC_CR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 821
RTC_DR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 820
RTC_ISR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 823
RTC_PRER . . . . . . . . . . . . . . . . . . . . . . . . . . 826
RTC_SHIFTR . . . . . . . . . . . . . . . . . . . . . . . . 831
RTC_SSR . . . . . . . . . . . . . . . . . . . . . . . . . . . 830
RTC_TR . . . . . . . . . . . . . . . . . . . . . . . . . . . . 819
RTC_TSDR . . . . . . . . . . . . . . . . . . . . . . . . . . 832
RTC_TSSSR . . . . . . . . . . . . . . . . . . . . . . . . . 833
RTC_TSTR . . . . . . . . . . . . . . . . . . . . . . . . . . 831
RTC_WPR . . . . . . . . . . . . . . . . . . . . . . . . . . . 830
RTC_WUTR . . . . . . . . . . . . . . . . . . . . . . . . . 826


**S**


SDIO_CLKCR . . . . . . . . . . . . . . . . . . . . . . . 1064
SDIO_DCOUNT . . . . . . . . . . . . . . . . . . . . . 1070
SDIO_DCTRL . . . . . . . . . . . . . . . . . . . . . . . 1069
SDIO_DLEN . . . . . . . . . . . . . . . . . . . . . . . . 1068
SDIO_DTIMER . . . . . . . . . . . . . . . . . . . . . . 1067
SDIO_FIFO . . . . . . . . . . . . . . . . . . . . . . . . . 1077
SDIO_FIFOCNT . . . . . . . . . . . . . . . . . . . . . 1076
SDIO_ICR . . . . . . . . . . . . . . . . . . . . . . . . . . 1072
SDIO_MASK . . . . . . . . . . . . . . . . . . . . . . . . 1074
SDIO_POWER . . . . . . . . . . . . . . . . . . . . . . 1063
SDIO_RESPCMD . . . . . . . . . . . . . . . . . . . . 1066
SDIO_RESPx . . . . . . . . . . . . . . . . . . . . . . . 1067
SDIO_STA . . . . . . . . . . . . . . . . . . . . . . . . . . 1071
SPI_CR1 . . . . . . . . . . . . . . . . . . . . . . . . . . . . 919
SPI_CR2 . . . . . . . . . . . . . . . . . . . . . . . . . . . . 921
SPI_CRCPR . . . . . . . . . . . . . . . . . . . . . . . . . 924



RM0090 Rev 21 1755/1751


**Index** **RM0090**


SPI_DR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .923
SPI_I2SCFGR . . . . . . . . . . . . . . . . . . . . . . . .925
SPI_I2SPR . . . . . . . . . . . . . . . . . . . . . . . . . . .927
SPI_RXCRCR . . . . . . . . . . . . . . . . . . . . . . . .924
SPI_SR . . . . . . . . . . . . . . . . . . . . . . . . . . . . .922
SPI_TXCRCR . . . . . . . . . . . . . . . . . . . . . . . .925
SYSCFG_EXTICR1 . . . . . . . . . . . . . . . .294, 300
SYSCFG_EXTICR2 . . . . . . . . . . . . . . . .294, 301
SYSCFG_EXTICR3 . . . . . . . . . . . . . . . .295, 301
SYSCFG_EXTICR4 . . . . . . . . . . . . . . . .296, 302
SYSCFG_MEMRMP . . . . . . . . . . . . . . .292, 297


**T**


TIM2_OR . . . . . . . . . . . . . . . . . . . . . . . . . . . .649
TIM5_OR . . . . . . . . . . . . . . . . . . . . . . . . . . . .650
TIMx_ARR . . . . . . . . . . . . . . 645, 685, 695, 709
TIMx_BDTR . . . . . . . . . . . . . . . . . . . . . . . . . .586
TIMx_CCER . . . . . . . . . . . . . 579, 643, 684, 694
TIMx_CCMR1 . . . . . . . . . . . 575, 639, 681, 691
TIMx_CCMR2 . . . . . . . . . . . . . . . . . . . .577, 642
TIMx_CCR1 . . . . . . . . . . . . . 584, 646, 686, 696
TIMx_CCR2 . . . . . . . . . . . . . . . . . 585, 646, 686
TIMx_CCR3 . . . . . . . . . . . . . . . . . . . . . .585, 647
TIMx_CCR4 . . . . . . . . . . . . . . . . . . . . . .586, 647
TIMx_CNT . . . . . . . . . . 583, 645, 685, 695, 708
TIMx_CR1 . . . . . . . . . . 564, 630, 675, 689, 705
TIMx_CR2 . . . . . . . . . . . . . . . . . . 565, 632, 707
TIMx_DCR . . . . . . . . . . . . . . . . . . . . . . .588, 648
TIMx_DIER . . . . . . . . . . 570, 635, 677, 690, 707
TIMx_DMAR . . . . . . . . . . . . . . . . . . . . . .589, 649
TIMx_EGR . . . . . . . . . . 573, 638, 680, 691, 708
TIMx_PSC . . . . . . . . . . 583, 645, 685, 695, 709
TIMx_RCR . . . . . . . . . . . . . . . . . . . . . . . . . . .584
TIMx_SMCR . . . . . . . . . . . . . . . . . 568, 633, 676
TIMx_SR . . . . . . . . . . . 572, 636, 679, 690, 708


**U**


USART_BRR . . . . . . . . . . . . . . . . . . . . . . . .1013
USART_CR1 . . . . . . . . . . . . . . . . . . . . . . . .1013
USART_CR2 . . . . . . . . . . . . . . . . . . . . . . . .1016
USART_CR3 . . . . . . . . . . . . . . . . . . . . . . . .1017
USART_DR . . . . . . . . . . . . . . . . . . . . . . . . .1013
USART_GTPR . . . . . . . . . . . . . . . . . . . . . . .1020
USART_SR . . . . . . . . . . . . . . . . . . . . . . . . .1010


**W**


WWDG_CFR . . . . . . . . . . . . . . . . . . . . . . . . .721
WWDG_CR . . . . . . . . . . . . . . . . . . . . . . . . . .720
WWDG_SR . . . . . . . . . . . . . . . . . . . . . . . . . .721


1756/1751 RM0090 Rev 21


**RM0090**


**IMPORTANT NOTICE – READ CAREFULLY**


STMicroelectronics NV and its subsidiaries (“ST”) reserve the right to make changes, corrections, enhancements, modifications, and
improvements to ST products and/or to this document at any time without notice. Purchasers should obtain the latest relevant information on
ST products before placing orders. ST products are sold pursuant to ST’s terms and conditions of sale in place at the time of order
acknowledgment.


Purchasers are solely responsible for the choice, selection, and use of ST products and ST assumes no liability for application assistance or
the design of purchasers’ products.


No license, express or implied, to any intellectual property right is granted by ST herein.


Resale of ST products with provisions different from the information set forth herein shall void any warranty granted by ST for such product.


ST and the ST logo are trademarks of ST. For additional information about ST trademarks, refer to _www.st.com/trademarks_ . All other
product or service names are the property of their respective owners.


Information in this document supersedes and replaces information previously supplied in any prior versions of this document.


© 2024 STMicroelectronics – All rights reserved


RM0090 Rev 21 1757/1757



1757


