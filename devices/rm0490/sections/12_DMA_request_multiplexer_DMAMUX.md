**DMA request multiplexer (DMAMUX)** **RM0490**

# **12 DMA request multiplexer (DMAMUX)**

## **12.1 Introduction**


A peripheral indicates a request for DMA transfer by setting its DMA request signal. The
DMA request is pending until served by the DMA controller that generates a DMA
acknowledge signal, and the corresponding DMA request signal is deasserted.


In this document, the set of control signals required for the DMA request/acknowledge
protocol is not explicitly shown or described, and it is referred to as DMA request line.


The DMAMUX request multiplexer enables routing a DMA request line between the
peripherals and the DMA controller of the product. The routing function is ensured by a
programmable multi-channel DMA request line multiplexer. Each channel selects a unique
DMA request line, unconditionally or synchronously with events from its DMAMUX
synchronization inputs. The DMAMUX may also be used as a DMA request generator from
programmable events on its input trigger signals.


The number of DMAMUX instances and their main characteristics are specified in
_Section 12.3.1_ .


The assignment of DMAMUX request multiplexer inputs to the DMA request lines from
peripherals and to the DMAMUX request generator outputs, the assignment of DMAMUX
request multiplexer outputs to DMA controller channels, and the assignment of DMAMUX
synchronizations and trigger inputs to internal and external signals depend upon product
implementation. They are detailed in _Section 12.3.2_ .


242/1027 RM0490 Rev 5


**RM0490** **DMA request multiplexer (DMAMUX)**

## **12.2 DMAMUX main features**


      - Up to 5-channel programmable DMA request line multiplexer output


      - 4-channel DMA request generator


      - 23 trigger inputs to DMA request generator


      - 23 synchronization inputs


      - Per DMA request generator channel:


–
DMA request trigger input selector


–
DMA request counter


–
Event overrun flag for selected DMA request trigger input


      - Per DMA request line multiplexer channel output:


–
Up to 57 input DMA request lines from peripherals


–
One DMA request line output


–
Synchronization input selector


–
DMA request counter


–
Event overrun flag for selected synchronization input


–
One event output, for DMA request chaining

## **12.3 DMAMUX implementation**


**12.3.1** **DMAMUX instantiation**


DMAMUX is instantiated with the hardware configuration parameters listed in the following
table.


**Table 48. DMAMUX instantiation**

|Feature|DMAMUX|
|---|---|
|Number of DMAMUX output request channels|3/5/7(1)|
|Number of DMAMUX request generator channels|4|
|Number of DMAMUX request trigger inputs|23|
|Number of DMAMUX synchronization inputs|23|
|Number of DMAMUX peripheral request inputs|Up to 57|



1. Seven instances for STM32C091/92xx devices, five instances for STM32C051/71xx devices, three
instances for STM32C011/31xx devices.


**12.3.2** **DMAMUX mapping**


The mapping of resources to DMAMUX is hardwired.


RM0490 Rev 5 243/1027



256


**DMA request multiplexer (DMAMUX)** **RM0490**


**Table 49. DMAMUX: assignment of multiplexer inputs to resources**

|DMA<br>request<br>MUX input|Resource|DMA<br>request<br>MUX input|Resource|DMA<br>request<br>MUX input|Resource|
|---|---|---|---|---|---|
|1|dmamux_gen0_dma|20|tim1_ch1_dma|39|Reserved|
|2|dmamux_gen1_dma|21|tim1_ch2_dma|40|tim15_ch1_dma|
|3|dmamux_gen2_dma|22|tim1_ch3_dma|41|tim15_ch2_dma|
|4|dmamux_gen3_dma|23|tim1_ch4_dma|42|tim15_trgi_com_dma|
|5|adc1_dma|24|tim1_trgi_com_dma|43|tim15_up_dma|
|6|Reserved|25|tim1_up_dma|44|tim16_ch1_dma|
|7|Reserved|26|tim2_ch1_dma|45|tim16_trgi_com_dma|
|8|Reserved|27|tim2_ch2_dma|46|tim16_up_dma|
|9|Reserved|28|tim2_ch3_dma|47|tim17_ch1_dma|
|10|i2c1_rx_dma|29|tim2_ch4_dma|48|tim17_trgi_com_dma|
|11|i2c1_tx_dma|30|tim2_trgi_dma|49|tim17_up_dma|
|12|i2c2_rx_dma|31|tim2_up_dma|50|usart1_rx_dma|
|13|i2c2_tx_dma|32|tim3_ch1_dma|51|usart1_tx_dma|
|14|Reserved|33|tim3_ch2_dma|52|usart2_rx_dma|
|15|Reserved|34|tim3_ch3_dma|53|usart2_tx_dma|
|16|spi2s1_rx_dma|35|tim3_ch4_dma|54|usart3_rx_dma|
|17|spi2s1_tx_dma|36|tim3_trgi_dma|55|usart3_tx_dma|
|18|spi2_rx_dma|37|tim3_up_dma|56|usart4_rx_dma|
|19|spi2_tx_dma|38|Reserved|57|usart4_tx_dma|



**Table 50. DMAMUX: assignment of trigger inputs to resources**

|Trigger input|Resource|Trigger input|Resource|
|---|---|---|---|
|0|EXTI0|12|EXTI12|
|1|EXTI1|13|EXTI13|
|2|EXTI2|14|EXTI14|
|3|EXTI3|15|EXTI15|
|4|EXTI4|16|dmamux_evt0|
|5|EXTI5|17|dmamux_evt1|
|6|EXTI6|18|dmamux_evt2|
|7|EXTI7|19|dmamux_evt3|
|8|EXTI8|20|Reserved|
|9|EXTI9|21|Reserved|
|10|EXTI10|22|tim14_trgo|
|11|EXTI11|23|Reserved|



244/1027 RM0490 Rev 5


**RM0490** **DMA request multiplexer (DMAMUX)**


**Table 51. DMAMUX: assignment of synchronization inputs to resources**

|Trigger input|Resource|Trigger input|Resource|
|---|---|---|---|
|0|EXTI0|12|EXTI12|
|1|EXTI1|13|EXTI13|
|2|EXTI2|14|EXTI14|
|3|EXTI3|15|EXTI15|
|4|EXTI4|16|dmamux_evt0|
|5|EXTI5|17|dmamux_evt1|
|6|EXTI6|18|dmamux_evt2|
|7|EXTI7|19|dmamux_evt3|
|8|EXTI8|20|Reserved|
|9|EXTI9|21|tim14_trgo|
|10|EXTI10|22|Reserved|
|11|EXTI11|23|Reserved|



RM0490 Rev 5 245/1027



256


**DMA request multiplexer (DMAMUX)** **RM0490**

## **12.4 DMAMUX functional description**



**12.4.1** **DMAMUX block diagram**


_Figure 22_ shows the DMAMUX block diagram.



**Figure 22. DMAMUX block diagram**












|Col1|Col2|Col3|Request multiplexer|Col5|Col6|Col7|Col8|Col9|Col10|Col11|
|---|---|---|---|---|---|---|---|---|---|---|
||||**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>**Channel m**<br>3<br>2<br>2<br>1<br>**DMAMUX_CmCR**<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>**Channel m**<br>3<br>2<br>2<br>1<br>**DMAMUX_CmCR**<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>**Channel m**<br>3<br>2<br>2<br>1<br>**DMAMUX_CmCR**<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>**Channel m**<br>3<br>2<br>2<br>1<br>**DMAMUX_CmCR**<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>**Channel m**<br>3<br>2<br>2<br>1<br>**DMAMUX_CmCR**<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>**Channel m**<br>3<br>2<br>2<br>1<br>**DMAMUX_CmCR**<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>**Channel m**<br>3<br>2<br>2<br>1<br>**DMAMUX_CmCR**<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>**Channel m**<br>3<br>2<br>2<br>1<br>**DMAMUX_CmCR**<br>**Sync**<br><br><br>|
||||**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>**Channel 1**<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|
|qx|qx|qx|qx|qx|qx|qx|qx|qx|qx|qx|
|qx||**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>n+3<br>n+2<br>n+p+2<br>2<br>1<br>n+1<br>**Sync**<br>0<br>1<br>s|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|
|qx||**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>n+3<br>n+2<br>n+p+2<br>2<br>1<br>n+1<br>**Sync**<br>0<br>1<br>s|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>||1|
|qx||**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>n+3<br>n+2<br>n+p+2<br>2<br>1<br>n+1<br>**Sync**<br>0<br>1<br>s|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|||0<br>|
|qx||**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>n+3<br>n+2<br>n+p+2<br>2<br>1<br>n+1<br>**Sync**<br>0<br>1<br>s|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|||||m<br>|
|qx||**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>n+3<br>n+2<br>n+p+2<br>2<br>1<br>n+1<br>**Sync**<br>0<br>1<br>s|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|||||1<br>|
|qx||**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>n+3<br>n+2<br>n+p+2<br>2<br>1<br>n+1<br>**Sync**<br>0<br>1<br>s|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|||||0<br>|
|qx||**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>n+3<br>n+2<br>n+p+2<br>2<br>1<br>n+1<br>**Sync**<br>0<br>1<br>s|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>||||||
|qx||**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>n+3<br>n+2<br>n+p+2<br>2<br>1<br>n+1<br>**Sync**<br>0<br>1<br>s|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>||0<br>1<br>s|0<br>1<br>s|||||
|qx||**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>n+3<br>n+2<br>n+p+2<br>2<br>1<br>n+1<br>**Sync**<br>0<br>1<br>s|**DMAMUX_C0CR**<br>**Channel 0**<br>Channel<br>select<br>Ctrl<br>3<br>2<br>2<br>1<br>**Sync**<br><br><br>||0<br>1<br>s||||||























DMAMUX features two main sub-blocks: the request line multiplexer and the request line
generator.


The implementation assigns:


- DMAMUX request multiplexer sub-block inputs (dmamux_reqx) from peripherals
(dmamux_req_inx) and from channels of the DMAMUX request generator sub-block
(dmamux_req_genx)


- DMAMUX request outputs to channels of DMA controllers (dmamux_req_outx)


- Internal or external signals to DMA request trigger inputs (dmamux_trgx)




      - Internal or external signals to synchronization inputs (dmamux_syncx)


246/1027 RM0490 Rev 5


**RM0490** **DMA request multiplexer (DMAMUX)**


**12.4.2** **DMAMUX signals**


_Table 52_ lists the DMAMUX signals.


**Table 52. DMAMUX signals**

|Signal name|Description|
|---|---|
|dmamux_hclk|DMAMUX AHB clock|
|dmamux_req_inx|DMAMUX DMA request line inputs from peripherals|
|dmamux_trgx|DMAMUX DMA request triggers inputs (to request generator sub-block)|
|dmamux_req_genx|DMAMUX request generator sub-block channels outputs|
|dmamux_reqx|DMAMUX request multiplexer sub-block inputs (from peripheral<br>requests and request generator channels)|
|dmamux_syncx|DMAMUX synchronization inputs (to request multiplexer sub-block)|
|dmamux_req_outx|DMAMUX requests outputs (to DMA controller)|
|dmamux_evtx|DMAMUX events outputs|



**12.4.3** **DMAMUX channels**


A DMAMUX channel is a request multiplexer channel that can include, depending upon the
selected input of the request multiplexer, an additional DMAMUX request generator
channel.


A DMAMUX request multiplexer channel is connected and dedicated to a single channel of
DMA controller.


**Channel configuration procedure**


Follow the sequence below to configure a DMAMUX x channel and the related DMA
channel y:


1. Set and configure completely the DMA channel y, except enabling the channel y.


2. Set and configure completely the related DMAMUX y channel.


3. Last, activate the DMA channel y by setting the EN bit in the DMA y channel register.


**12.4.4** **DMAMUX request line multiplexer**


The DMAMUX request multiplexer with its multiple channels ensures the actual routing of
DMA request/acknowledge control signals, named DMA request lines.


Each DMA request line is connected in parallel to all the channels of the DMAMUX request
line multiplexer.


A DMA request is sourced either from the peripherals, or from the DMAMUX request
generator.


The DMAMUX request line multiplexer channel x selects the DMA request line number as
configured by the DMAREQ_ID field in the DMAMUX_CxCR register.


_Note:_ _The null value in the field DMAREQ_ID corresponds to no DMA request line selected._


RM0490 Rev 5 247/1027



256


**DMA request multiplexer (DMAMUX)** **RM0490**


**Caution:** A same non-null DMAREQ_ID cannot be programmed to different x and y DMAMUX
request multiplexer channels (via DMAMUX_CxCR and DMAMUX_CyCR), except when the
application guarantees that the two connected DMA channels are not simultaneously active.


On top of the DMA request selection, the synchronization mode and/or the event generation
may be configured and enabled, if required.


**Synchronization mode and channel event generation**


Each DMAMUX request line multiplexer channel x can be individually synchronized by
setting the synchronization enable (SE) bit in the DMAMUX_CxCR register.


DMAMUX has multiple synchronization inputs. The synchronization inputs are connected in
parallel to all the channels of the request multiplexer.


The synchronization input is selected via the SYNC_ID field in the DMAMUX_CxCR register
of a given channel x.


When a channel is in this synchronization mode, the selected input DMA request line is
propagated to the multiplexer channel output, once a programmable rising/falling edge is
detected on the selected input synchronization signal, via the SPOL[1:0] field of the
DMAMUX_CxCR register.


Additionally, internally to the DMAMUX request multiplexer, there is a programmable DMA
request counter, which can be used for the channel request output generation, and for an
event generation. An event generation on the channel x output is enabled through the EGE
bit (event generation enable) of the DMAMUX_CxCR register.


As shown in _Figure 24_, upon the detected edge of the synchronization input, the pending
selected input DMA request line is connected to the DMAMUX multiplexer channel x output.


_Note:_ _If a synchronization event occurs while there is no pending selected input DMA request line,_
_it is discarded. The following asserted input request lines is not connected to the DMAMUX_
_multiplexer channel output until a synchronization event occurs again._


From this point on, each time the connected DMAMUX request is served by the DMA
controller (a served request is deasserted), the DMAMUX request counter is decremented.
At its underrun, the DMA request counter is automatically loaded with the value in the
NBREQ field of the DMAMUX_CxCR register and the input DMA request line is
disconnected from the multiplexer channel x output.


Thus, the number of DMA requests transferred to the multiplexer channel x output following
a detected synchronization event, is equal to the value in the NBREQ field, plus one.


_Note:_ _The NBREQ field value can be written by software only when both synchronization enable_
_bit (SE) and event generation enable bit (EGE) of the corresponding multiplexer channel x_
_are disabled._


248/1027 RM0490 Rev 5


**RM0490** **DMA request multiplexer (DMAMUX)**








|Col1|Col2|Col3|Col4|Col5|Col6|Col7|
|---|---|---|---|---|---|---|
||||||||
||||||||
|4||3|2|1|0|4|
|4|||||||



























If EGE is enabled, the multiplexer channel generates a channel event, as a pulse of one
AHB clock cycle, when its DMA request counter is automatically reloaded with the value of
the programmed NBREQ field, as shown in _Figure 23_ and _Figure 24_ .


RM0490 Rev 5 249/1027



256


**DMA request multiplexer (DMAMUX)** **RM0490**


_Note:_ _If EGE is enabled and NBREQ = 0, an event is generated after each served DMA request._


_Note:_ _A synchronization event (edge) is detected if the state following the edge remains stable for_
_more than two AHB clock cycles._


_Upon writing into DMAMUX_CxCR register, the synchronization events are masked during_
_three AHB clock cycles._


**Synchronization overrun and interrupt**


If a new synchronization event occurs before the request counter underrun (the internal
request counter programmed via the NBREQ field of the DMAMUX_CxCR register), the
synchronization overrun flag bit SOFx is set in the DMAMUX_CSR register.


_Note:_ _The request multiplexer channel x synchronization must be disabled_
_(DMAMUX_CxCR.SE = 0) when the use of the related channel of the DMA controller is_
_completed. Else, upon a new detected synchronization event, there is a synchronization_
_overrun due to the absence of a DMA acknowledge (that is, no served request) received_
_from the DMA controller._


The overrun flag SOFx is reset by setting the associated clear synchronization overrun flag
bit CSOFx in the DMAMUX_CFR register.


Setting the synchronization overrun flag generates an interrupt if the synchronization
overrun interrupt enable bit SOIE is set in the DMAMUX_CxCR register.


**12.4.5** **DMAMUX request generator**


The DMAMUX request generator produces DMA requests following trigger events on its
DMA request trigger inputs.


The DMAMUX request generator has multiple channels. DMA request trigger inputs are
connected in parallel to all channels.


The outputs of DMAMUX request generator channels are inputs to the DMAMUX request
line multiplexer.


Each DMAMUX request generator channel x has an enable bit GE (generator enable) in the
corresponding DMAMUX_RGxCR register.


The DMA request trigger input for the DMAMUX request generator channel x is selected
through the SIG_ID (trigger signal ID) field in the corresponding DMAMUX_RGxCR register.


Trigger events on a DMA request trigger input can be rising edge, falling edge or either
edge. The active edge is selected through the GPOL (generator polarity) field in the
corresponding DMAMUX_RGxCR register.


Upon the trigger event, the corresponding generator channel starts generating DMA
requests on its output. Each time the DMAMUX generated request is served by the
connected DMA controller (a served request is deasserted), a built-in (inside the DMAMUX
request generator) DMA request counter is decremented. At its underrun, the request
generator channel stops generating DMA requests and the DMA request counter is
automatically reloaded to its programmed value upon the next trigger event.


Thus, the number of DMA requests generated after the trigger event is GNBREQ + 1.


250/1027 RM0490 Rev 5


**RM0490** **DMA request multiplexer (DMAMUX)**


_Note:_ _The GNBREQ field value can be written by software only when the enable GE bit of the_
_corresponding generator channel x is disabled._


_There is no hardware write protection._


_A trigger event (edge) is detected if the state following the edge remains stable for more_
_than two AHB clock cycles._


_Upon writing into DMAMUX_RGxCR register, the trigger events are masked during three_
_AHB clock cycles._


**Trigger overrun and interrupt**


If a new DMA request trigger event occurs before the DMAMUX request generator counter
underrun (the internal counter programmed via the GNBREQ field of the DMAMUX_RGxCR
register), and if the request generator channel x was enabled via GE, then the request
trigger event overrun flag bit OFx is asserted by the hardware in the DMAMUX_RGSR
register.


_Note:_ _The request generator channel x must be disabled (DMAMUX_RGxCR.GE = 0) when the_
_usage of the related channel of the DMA controller is completed. Else, upon a new detected_
_trigger event, there is a trigger overrun due to the absence of an acknowledge (that is, no_
_served request) received from the DMA._


The overrun flag OFx is reset by setting the associated clear overrun flag bit COFx in the
DMAMUX_RGCFR register.


Setting the DMAMUX request trigger overrun flag generates an interrupt if the DMA request
trigger event overrun interrupt enable bit OIE is set in the DMAMUX_RGxCR register.

## **12.5 DMAMUX interrupts**


An interrupt can be generated upon:


      - a synchronization event overrun in each DMA request line multiplexer channel


      - a trigger event overrun in each DMA request generator channel


For each case, per-channel in.dividual interrupt enable, status, and clear flag register bits
are available.


**Table 53. DMAMUX interrupts**

|Interrupt signal|Interrupt event|Event flag|Clear bit|Enable bit|
|---|---|---|---|---|
|dmamuxovr_it|Synchronization event overrun<br>on channel x of the<br>DMAMUX request line multiplexer|SOFx|CSOFx|SOIE|
|dmamuxovr_it|Trigger event overrun<br>on channel x of the<br>DMAMUX request generator|OFx|COFx|OIE|



RM0490 Rev 5 251/1027



256


**DMA request multiplexer (DMAMUX)** **RM0490**

## **12.6 DMAMUX registers**


Refer to the table containing register boundary addresses for the DMAMUX base address.


DMAMUX registers may be accessed per byte (8-bit), half-word (16-bit), or word (32-bit).
The address must be aligned with the data size.


**12.6.1** **DMAMUX request line multiplexer channel x configuration register**
**(DMAMUX_CxCR)**


Address offset: 0x000 + 0x04 * x (x = 0 to 4)


Reset value: 0x0000 0000

|31|30|29|28 27 26 25 24|Col5|Col6|Col7|Col8|23 22 21 20 19|Col10|Col11|Col12|Col13|18 17|Col15|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|SPOL[1:0]|SPOL[1:0]|SE|
||||rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5 4 3 2 1 0|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|EGE|SOIE|Res.|Res.|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|
|||||||rw|rw|||rw|rw|rw|rw|rw|rw|



Bits 31:29 Reserved, must be kept at reset value.


Bits 28:24 **SYNC_ID[4:0]** : Synchronization identification

Selects the synchronization input (see _Table 51: DMAMUX: assignment of synchronization_
_inputs to resources_ ).


Bits 23:19 **NBREQ[4:0]** : Number of DMA requests minus 1 to forward

Defines the number of DMA requests to forward to the DMA controller after a synchronization
event, and/or the number of DMA requests before an output event is generated.
This field must only be written when both SE and EGE bits are low.


Bits 18:17 **SPOL[1:0]** : Synchronization polarity

Defines the edge polarity of the selected synchronization input:
00: No event (no synchronization, no detection).
01: Rising edge
10: Falling edge
11: Rising and falling edges


Bit 16 **SE** : Synchronization enable

0: Synchronization disabled
1: Synchronization enabled


Bits 15:10 Reserved, must be kept at reset value.


Bit 9 **EGE** : Event generation enable

0: Event generation disabled
1: Event generation enabled


Bit 8 **SOIE** : Synchronization overrun interrupt enable

0: Interrupt disabled
1: Interrupt enabled


252/1027 RM0490 Rev 5


**RM0490** **DMA request multiplexer (DMAMUX)**


Bits 7:6 Reserved, must be kept at reset value.


Bits 5:0 **DMAREQ_ID[5:0]** : DMA request identification

Selects the input DMA request. See the DMAMUX table about assignments of multiplexer
inputs to resources.


**12.6.2** **DMAMUX request line multiplexer interrupt channel status register**
**(DMAMUX_CSR)**


Address offset: 0x080


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SOF4|SOF3|SOF2|SOF1|SOF0|
||||||||||||r|r|r|r|r|



Bits 31:5 Reserved, must be kept at reset value.


Bits 4:0 **SOF[4:0]** : Synchronization overrun event flag

The flag is set when a synchronization event occurs on a DMA request line multiplexer
channel x, while the DMA request counter value is lower than NBREQ.
The flag is cleared by writing 1 to the corresponding CSOFx bit in DMAMUX_CFR register.


**12.6.3** **DMAMUX request line multiplexer interrupt clear flag register**
**(DMAMUX_CFR)**


Address offset: 0x084


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CSOF<br>4|CSOF<br>3|CSOF<br>2|CSOF<br>1|CSOF<br>0|
||||||||||||w|w|w|w|w|



Bits 31:5 Reserved, must be kept at reset value.


Bits 4:0 **CSOF[4:0]** : Clear synchronization overrun event flag

Writing 1 in each bit clears the corresponding overrun flag SOFx in the DMAMUX_CSR
register.


RM0490 Rev 5 253/1027



256


**DMA request multiplexer (DMAMUX)** **RM0490**


**12.6.4** **DMAMUX request generator channel x configuration register**
**(DMAMUX_RGxCR)**


Address offset: 0x100 + 0x04 * x (x = 0 to 3)


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23 22 21 20 19|Col10|Col11|Col12|Col13|18 17|Col15|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GPOL[1:0]|GPOL[1:0]|GE|
|||||||||rw|rw|rw|rw|rw|rw|rw|rw|


|15|14|13|12|11|10|9|8|7|6|5|4 3 2 1 0|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|OIE|Res.|Res.|Res.|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|
||||||||rw||||rw|rw|rw|rw|rw|



Bits 31:24 Reserved, must be kept at reset value.


Bits 23:19 **GNBREQ[4:0]** : Number of DMA requests to be generated (minus 1)

Defines the number of DMA requests to be generated after a trigger event. The actual
number of generated DMA requests is GNBREQ +1.

_Note: This field must be written only when GE bit is disabled._


Bits 18:17 **GPOL[1:0]** : DMA request generator trigger polarity

Defines the edge polarity of the selected trigger input
00: No event, i.e. no trigger detection nor generation.
01: Rising edge
10: Falling edge
11: Rising and falling edges


Bit 16 **GE** : DMA request generator channel x enable

0: DMA request generator channel x disabled
1: DMA request generator channel x enabled


Bits 15:9 Reserved, must be kept at reset value.


Bit 8 **OIE** : Trigger overrun interrupt enable

0: Interrupt on a trigger overrun event occurrence is disabled
1: Interrupt on a trigger overrun event occurrence is enabled


Bits 7:5 Reserved, must be kept at reset value.


Bits 4:0 **SIG_ID[4:0]** : Signal identification

Selects the DMA request trigger input used for the channel x of the DMA request generator


254/1027 RM0490 Rev 5


**RM0490** **DMA request multiplexer (DMAMUX)**


**12.6.5** **DMAMUX request generator interrupt status register**
**(DMAMUX_RGSR)**


Address offset: 0x140


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|OF3|OF2|OF1|OF0|
|||||||||||||r|r|r|r|



Bits 31:4 Reserved, must be kept at reset value.


Bits 3:0 **OF[3:0]** : Trigger overrun event flag

The flag is set when a new trigger event occurs on DMA request generator channel x, before
the request counter underrun (the internal request counter programmed via the GNBREQ
field of the DMAMUX_RGxCR register).
The flag is cleared by writing 1 to the corresponding COFx bit in the DMAMUX_RGCFR
register.


**12.6.6** **DMAMUX request generator interrupt clear flag register**
**(DMAMUX_RGCFR)**


Address offset: 0x144


Reset value: 0x0000 0000

|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|||||||||||||||||


|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|COF3|COF2|COF1|COF0|
|||||||||||||w|w|w|w|



Bits 31:4 Reserved, must be kept at reset value.


Bits 3:0 **COF[3:0]** : Clear trigger overrun event flag

Writing 1 in each bit clears the corresponding overrun flag OFx in the DMAMUX_RGSR
register.


RM0490 Rev 5 255/1027



256


**DMA request multiplexer (DMAMUX)** **RM0490**


**12.6.7** **DMAMUX register map**


The following table summarizes the DMAMUX registers and reset values. Refer to the
register boundary address table for the DMAMUX register base address.


**Table 54. DMAMUX register map and reset values**









































































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x000|DMAMUX_C0CR|Res.|Res.|Res.|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|SPOL<br>[1:0]|SPOL<br>[1:0]|SE|Res.|Res.|Res.|Res.|Res.|Res.|EGE|SOIE|Res.|Res.|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|
|0x000|Reset value||||0|0|0|0|0|0|0|0|0|0|0|0|0|||||||0|0|||0|0|0|0|0|0|
|0x004|DMAMUX_C1CR|Res.|Res.|Res.|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|SPOL<br>[1:0]|SPOL<br>[1:0]|SE|Res.|Res.|Res.|Res.|Res.|Res.|EGE|SOIE|Res.|Res.|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|
|0x004|Reset value||||0|0|0|0|0|0|0|0|0|0|0|0|0|||||||0|0|||0|0|0|0|0|0|
|0x008|DMAMUX_C2CR|Res.|Res.|Res.|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|SPOL<br>[1:0]|SPOL<br>[1:0]|SE|Res.|Res.|Res.|Res.|Res.|Res.|EGE|SOIE|Res.|Res.|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|
|0x008|Reset value||||0|0|0|0|0|0|0|0|0|0|0|0|0|||||||0|0|||0|0|0|0|0|0|
|0x00C|DMAMUX_C3CR|Res.|Res.|Res.|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|SPOL<br>[1:0]|SPOL<br>[1:0]|SE|Res.|Res.|Res.|Res.|Res.|Res.|EGE|SOIE|Res.|Res.|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|
|0x00C|Reset value||||0|0|0|0|0|0|0|0|0|0|0|0|0|||||||0|0|||0|0|0|0|0|0|
|0x010|DMAMUX_C4CR|Res.|Res.|Res.|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|SYNC_ID[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|NBREQ[4:0]|SPOL<br>[1:0]|SPOL<br>[1:0]|SE|Res.|Res.|Res.|Res.|Res.|Res.|EGE|SOIE|Res.|Res.|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|DMAREQ_ID[5:0]|
|0x010|Reset value||||0|0|0|0|0|0|0|0|0|0|0|0|0|||||||0|0|||0|0|0|0|0|0|
|0x014 -<br>0x07C|Reserved|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x080|DMAMUX_CSR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|SOF4|SOF3|SOF2|SOF1|SOF0|
|0x080|Reset value||||||||||||||||||||||||||||0|0|0|0|0|
|0x084|DMAMUX_CFR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|CSOF4|CSOF3|CSOF2|CSOF1|CSOF0|
|0x084|Reset value||||||||||||||||||||||||||||0|0|0|0|0|
|0x088 -<br>0x0FC|Reserved|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x100|DMAMUX_RG0CR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GPOL<br>[1:0]|GPOL<br>[1:0]|GE|Res.|Res.|Res.|Res.|Res.|Res.|Res.|OIE|Res.|Res.|Res.|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|
|0x100|Reset value|||||||||0|0|0|0|0|0|0|0||||||||0||||0|0|0|0|0|
|0x104|DMAMUX_RG1CR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GPOL<br>[1:0]|GPOL<br>[1:0]|GE|Res.|Res.|Res.|Res.|Res.|Res.|Res.|OIE|Res.|Res.|Res.|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|
|0x104|Reset value|||||||||0|0|0|0|0|0|0|0||||||||0||||0|0|0|0|0|
|0x108|DMAMUX_RG2CR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GPOL<br>[1:0]|GPOL<br>[1:0]|GE|Res.|Res.|Res.|Res.|Res.|Res.|Res.|OIE|Res.|Res.|Res.|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|
|0x108|Reset value|||||||||0|0|0|0|0|0|0|0||||||||0||||0|0|0|0|0|
|0x10C|DMAMUX_RG3CR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GNBREQ[4:0]|GPOL<br>[1:0]|GPOL<br>[1:0]|GE|Res.|Res.|Res.|Res.|Res.|Res.|Res.|OIE|Res.|Res.|Res.|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|SIG_ID[4:0]|
|0x10C|Reset value|||||||||0|0|0|0|0|0|0|0||||||||0||||0|0|0|0|0|
|0x110 -<br>0x13C|Reserved|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|
|0x140|DMAMUX_RGSR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|OF3|OF2|OF1|OF0|
|0x140|Reset value|||||||||||||||||||||||||||||0|0|0|0|
|0x144|DMAMUX_RGCFR|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|COF3|COF2|COF1|COF0|
|0x144|Reset value|||||||||||||||||||||||||||||0|0|0|0|
|0x148 -<br>0x3FC|Reserved|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|Res.|


Refer to _Section 2.2 on page 45_ for the register boundary addresses.


256/1027 RM0490 Rev 5


