**RM0090** **LCD-TFT controller (LTDC)**

# **16 LCD-TFT controller (LTDC)**


This section applies only to STM32F429xx/439xx devices.

## **16.1 Introduction**


The LCD-TFT (Liquid Crystal Display - Thin Film Transistor) display controller provides a
parallel digital RGB (Red, Green, Blue) and signals for horizontal, vertical synchronisation,
Pixel Clock and Data Enable as output to interface directly to a variety of LCD and TFT
panels.

## **16.2 LTDC main features**


      - 24-bit RGB Parallel Pixel Output; 8 bits-per-pixel (RGB888)


      - 2 display layers with dedicated FIFO (64x32-bit)


      - Color Look-Up Table (CLUT) up to 256 color (256x24-bit) per layer


      - Supports up to XGA (1024x768) resolution


      - Programmable timings for different display panels


      - Programmable Background color


      - Programmable polarity for HSync, VSync and Data Enable


      - Up to 8 Input color formats selectable per layer


– ARGB8888


– RGB888


– RGB565


– ARGB1555


– ARGB4444


–
L8 (8-bit Luminance or CLUT)


–
AL44 (4-bit alpha + 4-bit luminance)


–
AL88 (8-bit alpha + 8-bit luminance)


      - Pseudo-random dithering output for low bits per channel


–
Dither width 2-bits for Red, Green, Blue


      - Flexible blending between two layers using alpha value (per pixel or constant)


      - Color Keying (transparency color)


      - Programmable Window position and size


      - Supports thin film transistor (TFT) color displays


      - AHB master interface with burst of 16 words


      - Up to 4 programmable interrupt events


RM0090 Rev 21 483/1757



517


**LCD-TFT controller (LTDC)** **RM0090**

## **16.3 LTDC functional description**


**16.3.1** **LTDC block diagram**


The block diagram of the LTDC is shown in _Figure 81: LTDC block diagram_ .


**Figure 81. LTDC block diagram**




















|AHB<br>interface|Col2|Col3|Layer1<br>PFC<br>FIFO<br>Blending Dithering<br>unit unit<br>Layer1<br>PFC<br>FIFO<br>Timing<br>generator|
|---|---|---|---|
|Configuration<br>and status<br>registers|Configuration<br>and status<br>registers|||







Layer FIFO: One FIFO 64x32 bit per layer.


PFC: Pixel Format Convertor performing the pixel format conversion from the selected input
pixel format of a layer to words.


AHB interface: For data transfer from memories to the FIFO.


Blending, Dithering unit and Timings Generator: Refer to _Section 16.4.1_ and _Section 16.4.2_ .


**16.3.2** **LTDC reset and clocks**


The LCD-TFT controller peripheral uses 3 clock domains:


      - The AHB clock domain (HCLK) is used for data transfer from the memories to the
Layer FIFO and frame buffer configuration register


      - The APB2 clock domain (PCLK2) is used for global configuration register and interrupt
registers


      - The Pixel Clock domain (LCD_CLK) is used to generate LCD-TFT interface signals,
pixel data generation and layer configuration. The LCD_CLK output should be
configured following the panel requirements. The LCD_CLK is configured through the
PLLSAI (refer to RCC section).


_Table 89_ summarizes the clock domain for each register.


484/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


**Table 89. LTDC registers versus clock domain**






|LTDC registers|Clock domain|
|---|---|
|LTDC_LxCR|HCLK|
|LTDC_LxCFBAR|LTDC_LxCFBAR|
|LTDC_LxCFBLR|LTDC_LxCFBLR|
|LTDC_LxCFBLNR|LTDC_LxCFBLNR|
|LTDC_SRCR|PCLK2|
|LTDC_IER|LTDC_IER|
|LTDC_ISR|LTDC_ISR|
|LTDC_ICR|LTDC_ICR|
|LTDC_SSCR|Pixel Clock (LCD_CLK)|
|LTDC_BPCR|LTDC_BPCR|
|LTDC_AWCR|LTDC_AWCR|
|LTDC_TWCR|LTDC_TWCR|
|LTDC_GCR|LTDC_GCR|
|LTDC_BCCR|LTDC_BCCR|
|LTDC_LIPCR|LTDC_LIPCR|
|LTDC_CPSR|LTDC_CPSR|
|LTDC_CDSR|LTDC_CDSR|
|LTDC_LxWHPCR|LTDC_LxWHPCR|
|LTDC_LxWVPCR|LTDC_LxWVPCR|
|LTDC_LxCKCR|LTDC_LxCKCR|
|LTDC_LxPFCR|LTDC_LxPFCR|
|LTDC_LxCACR|LTDC_LxCACR|
|LTDC_LxDCCR|LTDC_LxDCCR|
|LTDC_LxBFCR|LTDC_LxBFCR|
|LTDC_LxCLUTWR|LTDC_LxCLUTWR|



Care must be taken when accessing the LTDC registers since the APB2 bus is stalling when
the following operations are ongoing:


- Register write access and update for 6 xPCKL2 period + 5x LCD_CLK period (5x
HCLK period for register on AHB clock domain)


- Register read access for 7xPCKL2 period + 5x LCD_CLK period (5x HCLK period for
register on AHB clock domain).


For registers on PCLK2 clock domain, APB2 bus is stalling during the register write access
for 6 xPCKL2 period and 7xPCKL2 period for read access.


The LCD controller can be reset by setting the corresponding bit in the RCC_APB2RSTR
register. It resets the three clock domains.


RM0090 Rev 21 485/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


**16.3.3** **LCD-TFT pins and signal interface**


The Table below summarizes the LTDC signal interface:


**Table 90. LCD-TFT pins and signal interface**

|LCD-TFT<br>signals|I/O|Description|
|---|---|---|
|LCD_CLK|O|Clock Output|
|LCD_HSYNC|O|Horizontal Synchronization|
|LCD_VSYNC|O|Vertical Synchronization|
|LCD_DE|O|Not Data Enable|
|LCD_R[7:0]|O|Data: 8-bit Red data|
|LCD_G[7:0]|O|Data: 8-bit Green data|
|LCD_B[7:0]|O|Data: 8-bit Blue data|



The LCD-TFT controller pins must be configured by the user application. The unused pins
can be used for other purposes.


For LTDC outputs up to 24-bit (RGB888), if less than 8bpp are used to output for example
RGB565 or RGB666 to interface on 16b-bit or 18-bit displays, the RGB display data lines
must be connected to the MSB of the LCD-TFT controller RGB data lines. As an example, in
the case of an LCD-TFT controller interfacing with a RGB565 16-bit display, the LCD display
R[4:0], G[5:0] and B[4:0] data lines pins must be connected to LCD-TFT controller
LCD_R[7:3], LCD_G[7:2] and LCD_B[7:3].

## **16.4 LTDC programmable parameters**


The LCD-TFT controller provides flexible configurable parameters. It can be enabled or
disabled through the **LTDC_GCR** register.


**16.4.1** **LTDC Global configuration parameters**


**Synchronous Timings:**


_Figure 82_ presents the configurable timing parameters generated by the Synchronous
Timings Generator block presented in the block diagram _Figure 81_ . It generates the
Horizontal and Vertical Synchronization timings panel signals, the Pixel Clock and the Data
Enable signals.


486/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


**Figure 82. LCD-TFT Synchronous timings**





|Col1|Col2|Col3|Col4|Col5|
|---|---|---|---|---|
||||||
||||||
||||Data1, Line1|Data1, Line1|
||||||


_Note:_ _The HBP and HFP are respectively the Horizontal back porch and front porch period._


_The VBP and the VFP are respectively the Vertical back porch and front porch period._


The LCD-TFT programmable synchronous timings are:


–
HSYNC and VSYNC Width: Horizontal and Vertical Synchronization width
configured by programming a value of _**HSYNC Width - 1**_ and _**VSYNC Width - 1**_ in
the **LTDC_SSCR** register.


–
HBP and VBP: Horizontal and Vertical Synchronization back porch width
configured by programming the accumulated value _**HSYNC Width + HBP - 1**_ and
the accumulated value _**VSYNC Width + VBP - 1**_ in the **LTDC_BPCR** register.


–
Active Width and Active Height: The Active Width and Active Height are
configured by programming the accumulated value _**HSYNC Width + HBP +**_
_**Active Width - 1**_ and the accumulated value _**VSYNC Width + VBP + Active**_
_**Height - 1**_ in the **LTDC_AWCR** register (only up to 1024x768 is supported).


–
Total Width: The Total width is configured by programming the accumulated value
_**HSYNC Width + HBP + Active Width + HFP - 1**_ in the **LTDC_TWCR** register. The
HFP is the Horizontal front porch period.


–
Total Height: The Total Height is configured by programming the accumulated
value _**VSYNC Height + VBP + Active Height + VFP - 1**_ in the **LTDC_TWCR**
register. The VFP is the Vertical front porch period.


_Note:_ _When the LTDC is enabled, the timings generated start with X/Y=0/0 position as the first_
_horizontal synchronization pixel in the vertical synchronization area and following the back_
_porch, active data display area and the front porch._


RM0090 Rev 21 487/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


When the LTDC is disabled, the timing generator block is reset to X= _Total Width - 1_,
Y= _Total Height - 1_ and held the last pixel before the vertical synchronization phase and the
FIFO are flushed. Therefore only blanking data is output continuously.


**Example of Synchronous timings configuration**


TFT-LCD timings (should be extracted from Panel datasheet):


      - Horizontal and Vertical Synchronization width: 0x8 pixels and 0x4 lines


      - Horizontal and Vertical back porch: 0x7 pixels and 0x2 lines


      - Active Width and Active Height: 0x280 pixels, 0x1E0 lines (640x480)


      - Horizontal front porch: 0x6 pixels


      - Vertical front porch: 0x2 lines


The programmed values in the LTDC timings registers are:


      - **LTDC_SSCR** register: to be programmed to 0x00070003. (HSW[11:0] is 0x7 and
VSH[10:0] is 0x3)


      - **LTDC_BPCR** register: to be programmed to 0x000E0005. (AHBP[11:0] is 0xE(0x8 +
0x6) and AVBP[10:0] is 0x5(0x4 + 0x1))


      - **LTDC_AWCR** register: to be programmed to 0x028E01E5. (AAW[11:0] is 0x28E(0x8
+0x7 +0x27F) and AAH[10:0] is 0x1E5(0x4 +0x2 + 0x1DF)


      - **LTDC_TWCR** register: to be programmed to 0x00000294. (TOTALW[11:0] is
0x294(0x8 +0x7 +0x280 + 0x5)


      - **LTDC_THCR** register: to be programmed to 0x000001E7. (TOTALH[10:0] is
0x1E7(0x4 +0x2 + 0x1E0 + 1)


**Programmable polarity**


The Horizontal and Vertical Synchronization, Data Enable and Pixel Clock output signals
polarity can be programmed to active high or active low through the **LTDC_GCR** register.


**Background Color**


A constant background color (RGB888) can programmed through the **LTDC_BCCR**
register. It is used for blending with the bottom layer.


**Dithering**


The Dithering pseudo-random technique using an LFSR is used to add a small random
value (threshold) to each pixel color channel (R, G or B) value, thus rounding up the MSB in
some cases when displaying a 24-bit data on 18-bit display. Thus the Dithering technique is
used to round data which is different from one frame to the other.


The Dither pseudo-random technique is the same as comparing LSBs against a threshold
value and adding a 1 to the MSB part only, if the LSB part is >= the threshold. The LSBs are
typically dropped once dithering was applied.


The width of the added pseudo-random value is 2 bits for each color channel; 2 bits for Red,
2 bits for Green and 2 bits for Blue.


Once the LCD-TFT controller is enabled, the LFSR starts running with the first active pixel
and it is kept running even during blanking periods and when dithering is switched off. If the
LTDC is disabled, the LFSR is reset.


The Dithering can be switched On and Off on the fly through the **LTDC_GCR** register.


488/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


**Reload Shadow registers**


Some configuration registers are shadowed. The shadow registers values can be reloaded
immediately to the active registers when writing to these registers or at the beginning of the
vertical blanking period following the configuration in the **LTDC_SRCR** register. If the
immediate reload configuration is selected, the reload should be only activated when all new
registers have been written.


The shadow registers should not be modified again before the reload has been done.
Reading from the shadow registers returns the actual active value. The new written value
can only be read after the reload has taken place.


A register reload interrupt can be generated if enabled in the **LTDC_IER** register.


The shadowed registers are all the Layer 1 and Layer 2 registers except the
**LTDC_LxCLUTWR** register.


**Interrupt generation event**


Refer to _Section 16.5: LTDC interrupts_ for interrupt configuration.


**16.4.2** **Layer programmable parameters**


Up to two layers can be enabled, disabled and configured separately. The layer display
order is fixed and it is bottom up. If two layers are enabled, the Layer2 is the top displayed
window.


**Windowing**


Every layer can be positioned and resized and it must be inside the Active Display area.


The window position and size are configured through the top-left and bottom-right X/Y
positions and the Internal timing generator which includes the synchronous, back porch size
and the active data area. Refer to **LTDC_LxWHPCR** and **LTDC_WVPCR** registers.


The programmable layer position and size defines the first/last visible pixel of a line and the
first/last visible line in the window. It allows to display either the full image frame or only a
part of the image frame. Refer to _Figure 83_


      - The first and the last visible pixel in the layer are set by configuring the WHSTPOS[11:0]
and WHSPPOS[11:0] in the **LTDC_LxWHPCR** register.


      - The first and the last visible lines in the layer are set by configuring the WVSTPOS[10:0]
and WVSPPOS[10:0] in the **LTDC_LxWVPCR** register.


RM0090 Rev 21 489/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


**Figure 83. Layer window programmable parameters:**











**Pixel input Format**


The programmable pixel format is used for the data stored in the frame buffer of a layer.


Up to 8 input pixel formats can be configured for every layer through the **LTDC_LxPFCR**
register


The pixel data is read from the frame buffer and then transformed to the internal 8888
(ARGB) format as follows:


      - Components which have a width of less than 8 bits get expanded to 8 bits by bit
replication. The selected bit range is concatenated multiple times until it is longer than
8 bits. Of the resulting vector, the 8 MSB bits are chosen. Example: 5 bits of an
RGB565 red channel become (bit positions): 43210432 (the 3 LSBs are filled with the 3
MSBs of the 5 bits)


The figure below describes the pixel data mapping depending on the selected format.


**Table 91. Pixel Data mapping versus Color Format**

|ARGB8888|Col2|Col3|Col4|
|---|---|---|---|
|@+3<br>Ax[7:0]|@+2<br>Rx[7:0]|@+1<br>Gx[7:0]|@<br>Bx[7:0]|
|@+7<br>Ax+1[7:0]|@+6<br>Rx+1[7:0]|@+5<br>Gx+1[7:0]|@+4<br>Bx+1[7:0]|
|**RGB888**|**RGB888**|**RGB888**|**RGB888**|
|@+3<br>Bx+1[7:0]|@+2<br>Rx[7:0]|@+1<br>Gx[7:0]|@<br>Bx[7:0]|
|@+7<br>Gx+2[7:0]|@+6<br>Bx+2[7:0]|@+5<br>Rx+1[7:0]|@+4<br>Gx+1[7:0]|
|**RGB565**|**RGB565**|**RGB565**|**RGB565**|
|@+3<br>Rx+1[4:0] Gx+1[5:3]|@+2<br>Gx+1[2:0] Bx+1[4:0]|@+1<br>Rx[4:0] Gx[5:3]|@<br>Gx[2:0] Bx[4:0]|



490/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


**Table 91. Pixel Data mapping versus Color Format (continued)**













|ARGB8888|Col2|Col3|Col4|
|---|---|---|---|
|@+7<br>Rx+3[4:0] Gx+3[5:3]|@+6<br>Gx+3[2:0] Bx+3[4:0]|@+5<br>Rx+2[4:0] Gx+2[5:3]|@+4<br>Gx+2[2:0] Bx+2[4:0]|
|**ARGB1555**|**ARGB1555**|**ARGB1555**|**ARGB1555**|
|@+3<br>Ax+1[0]Rx+1[4:0]<br>Gx+1[4:3]|@+2<br>Gx+1[2:0] Bx+1[4:0]|@+1<br>Ax[0] Rx[4:0] Gx[4:3]|@<br>Gx[2:0] Bx[4:0]|
|@+7<br>Ax+3[0]Rx+3[4:0]<br>Gx+3[4:3]|@+6<br>Gx+3[2:0] Bx+3[4:0]|@+5<br>Ax+2[0]Rx+2[4:0]Gx+2[4:<br>3]|@+4<br>Gx+2[2:0] Bx+2[4:0]|
|**ARGB4444**|**ARGB4444**|**ARGB4444**|**ARGB4444**|
|@+3<br>Ax+1[3:0]Rx+1[3:0]|@+2<br>Gx+1[3:0] Bx+1[3:0]|@+1<br>Ax[3:0] Rx[3:0]|@<br>Gx[3:0] Bx[3:0]|
|@+7<br>Ax+3[3:0]Rx+3[3:0]|@+6<br>Gx+3[3:0] Bx+3[3:0]|@+5<br>Ax+2[3:0]Rx+2[3:0]|@+4<br>Gx+2[3:0] Bx+2[3:0]|
|**L8**|**L8**|**L8**|**L8**|
|@+3<br>Lx+3[7:0]|@+2<br>Lx+2[7:0]|@+1<br>Lx+1[7:0]|@<br>Lx[7:0]|
|@+7<br>Lx+7[7:0]|@+6<br>Lx+6[7:0]|@+5<br>Lx+5[7:0]|@+4<br>Lx+4[7:0]|
|**AL44**|**AL44**|**AL44**|**AL44**|
|@+3<br>Ax+3[3:0] Lx+3[3:0]|@+2<br>Ax+2[3:0] Lx+2[3:0]|@+1<br>Ax+1[3:0] Lx+1[3:0]|@<br>Ax[3:0] Lx[3:0]|
|@+7<br>Ax+7[3:0] Lx+7[3:0]|@+6<br>Ax+6[3:0] Lx+6[3:0]|@+5<br>Ax+5[3:0] Lx+5[3:0]|@+4<br>Ax+4[3:0] Lx+4[3:0]|
|**AL88**|**AL88**|**AL88**|**AL88**|
|@+3<br>Ax+1[7:0]|@+2<br>Lx+1[7:0]|@+1<br>Ax[7:0]|@<br>Lx[7:0]|
|@+7<br>Ax+3[7:0]|@+6<br>Lx+3[7:0]|@+5<br>Ax+2[7:0]|@+4<br>Lx+2[7:0]|


**Color Look-Up Table (CLUT)**


The CLUT can be enabled at run-time for every layer through the **LTDC_LxCR** register and
it is only useful in case of indexed color when using the L8, AL44 and AL88 input pixel
format.


First, the CLUT has to be loaded with the R, G and B values that replace the original R, G, B
values of that pixel (indexed color). Each color (RGB value) has its own address which is the
position within the CLUT.


RM0090 Rev 21 491/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


The R, G and B values and their own respective address are programmed through the
**LTDC_LxCLUTWR** register.


      - In case of L8 and AL88 input pixel format, the CLUT has to be loaded by 256 colors. The
address of each color is configured in the CLUTADD bits in the **LTDC_LxCLUTWR**
register.


      - In case of AL44 input pixel format, the CLUT has to be only loaded by 16 colors. The
address of each color must be filled by replicating the 4-bit L channel to 8-bit as follows:

–
L0 (indexed color 0), at address 0x00

–
L1, at address 0x11

–
L2, at address 0x22

– .....

–
L15, at address 0xFF


**Color Frame Buffer Address**


Every Layer has a start address for the color frame buffer configured through the
**LTDC_LxCFBAR** register.


When a layer is enabled, the data is fetched from the Color Frame Buffer.


**Color Frame Buffer Length**


Every layer has a total line length setting for the color frame buffer in bytes and a number of
lines in the frame buffer configurable in the **LTDC_LxCFBLR** and **LTDC_LxCFBLNR**
register respectively.


The line length and the number of lines settings are used to stop the prefetching of data to
the layer FIFO at the end of the frame buffer.


      - If it is set to less bytes than required, a FIFO underrun interrupt is generated if it has
been previously enabled.


      - If it is set to more bytes than actually required, the useless data read from the FIFO is
discarded. The useless data is not displayed.


**Color Frame Buffer Pitch**


Every layer has a configurable pitch for the color frame buffer, which is the distance between
the start of one line and the beginning of the next line in bytes. It is configured through the
**LTDC_LxCFBLR** register.


**Layer Blending**


The blending is always active and the two layers can be blended following the blending
factors configured through the **LTDC_LxBFCR** register.


The blending order is fixed and it is bottom up. If two layers are enabled, first the Layer1 is
blended with the Background color, then the Layer2 is blended with the result of blended
color of Layer1 and the background. Refer to _Figure 84_ .


492/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


**Figure 84. Blending two layers with background**













**Default color**


Every layer can have a default color in the format ARGB which is used outside the defined
layer window or when a layer is disabled.


The default color is configured through the **LTDC_LxDCCR** register.


The blending is always performed between the two layers even when a layer is disabled. To
avoid displaying the default color when a layer is disabled, keep the blending factors of this
layer in the LTDC_LxBFCR register to their reset value.


**Color Keying**


A color key (RGB) can be configured to be representative for a transparent pixel.


If the Color Keying is enabled, the current pixels (after format conversion and before
blending) are compared to the color key. If they match for the programmed RGB value, all
channels (ARGB) of that pixel are set to 0.


The Color Key value can be configured and used at run-time to replace the pixel RGB value.


The Color Keying is enabled through the **LTDC_LxCKCR** register.

## **16.5 LTDC interrupts**


The LTDC provides four maskable interrupts logically ORed to two interrupt vectors.


The interrupt sources can be enabled or disabled separately through the **LTDC_IER**
register. Setting the appropriate mask bit to 1 enables the corresponding interrupt.


The two interrupts are generated on the following events:


      - Line interrupt: generated when a programmed line is reached. The line interrupt
position is programmed in the LTDC_LIPCR register


      - Register Reload interrupt: generated when the shadow registers reload was performed
during the vertical blanking period


      - FIFO Underrun interrupt: generated when a pixel is requested from an empty layer
FIFO


      - Transfer Error interrupt: generated when an AHB bus error occurs during data transfer


Those interrupts events are connected to the NVIC controller as described in the figure
below.


RM0090 Rev 21 493/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


**Figure 85. Interrupt events**


**Table 92. LTDC interrupt requests**

|Interrupt event|Event flag|Enable Control bit|
|---|---|---|
|Line|LIF|LIE|
|Register Reload|RRIF|RRIEN|
|FIFO Underrun|FUDERRIF|FUDERRIE|
|Transfer Error|TERRIF|TERRIE|



494/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**

## **16.6 LTDC programming procedure**


      - Enable the LTDC clock in the RCC register


      - Configure the required Pixel clock following the panel datasheet


      - Configure the Synchronous timings: VSYNC, HSYNC, Vertical and Horizontal back
porch, active data area and the front porch timings following the panel datasheet as
described in the _Section 16.4.1: LTDC Global configuration parameters_


      - Configure the synchronous signals and clock polarity in the **LTDC_GCR** register


      - If needed, configure the background color in the **LTDC_BCCR** register


      - Configure the needed interrupts in the **LTDC_IER** and **LTDC_LIPCR** register


      - Configure the Layer1/2 parameters by programming:


– The Layer window horizontal and vertical position in the **LTDC_LxWHPCR** and
**LTDC_WVPCR** registers. The layer window must be in the active data area.


–
The pixel input format in the **LTDC_LxPFCR** register


– The color frame buffer start address in the **LTDC_LxCFBAR** register


–
The line length and pitch of the color frame buffer in the **LTDC_LxCFBLR** register


– The number of lines of the color frame buffer in the **LTDC_LxCFBLNR** register


–
if needed, load the CLUT with the RGB values and its address in the
**LTDC_LxCLUTWR** register


–
If needed, configure the default color and the blending factors respectively in the
**LTDC_LxDCCR** and **LTDC_LxBFCR** registers


      - Enable Layer1/2 and if needed the CLUT in the **LTDC_LxCR** register


      - If needed, dithering and color keying can be enabled respectively in the **LTDC_GCR**
**and LTDC_LxCKCR** registers. It can be also enabled on the fly.


      - Reload the shadow registers to active register through the **LTDC_SRCR** register.


      - Enable the LCD-TFT controller in the **LTDC_GCR** register.


      - All layer parameters can be modified on the fly except the CLUT. The new configuration
has to be either reloaded immediately or during vertical blanking period by configuring
the **LTDC_SRCR** register.


_Note:_ _All layer’s registers are shadowed. Once a register is written, it should not be modified again_
_before the reload has been done. Thus, a new write to the same register overrides the_
_previous configuration if not yet reloaded._


RM0090 Rev 21 495/1757



517


**LCD-TFT controller (LTDC)** **RM0090**

## **16.7 LTDC registers**


**16.7.1** **LTDC Synchronization Size Configuration Register (LTDC_SSCR)**


This register defines the number of Horizontal Synchronization pixels minus 1 and the
number of Vertical Synchronization lines minus 1. Refer to _Figure 82_ and _Section 16.4:_
_LTDC programmable parameters_ for an example of configuration.


Address offset: 0x08


Reset value: 0x0000 0000

|31 30 29 28|27 26 25 24 23 22 21 20 19 18 17 16|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|HSW[11:0]|HSW[11:0]|HSW[11:0]|HSW[11:0]|HSW[11:0]|HSW[11:0]|HSW[11:0]|HSW[11:0]|HSW[11:0]|HSW[11:0]|HSW[11:0]|HSW[11:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11|10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:28 Reserved, must be kept at reset value


Bits 27:16 **HSW[11:0]** : Horizontal Synchronization Width (in units of pixel clock period)

These bits define the number of Horizontal Synchronization pixel minus 1.


Bits 15:11 Reserved, must be kept at reset value


Bits 10:0 **VSH[10:0]** : Vertical Synchronization Height (in units of horizontal scan line)


These bits define the vertical Synchronization height minus 1. It represents the
number

of horizontal synchronization lines.


**16.7.2** **LTDC Back Porch Configuration Register (LTDC_BPCR)**


This register defines the accumulated number of Horizontal Synchronization and back porch
pixels minus 1 ( **HSYNC Width + HBP- 1)** and the accumulated number of Vertical
Synchronization and back porch lines minus 1 ( **VSYNC Height + VBP - 1)** . Refer to
_Figure 82_ and _Section 16.4: LTDC programmable parameters_ for an example of
configuration.


Address offset: 0x0C


Reset value: 0x0000 0000

|31 30 29 28|27 26 25 24 23 22 21 20 19 18 17 16|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11|10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



496/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


Bits 31:28 Reserved, must be kept at reset value


Bits 27:16 **AHBP[11:0]** : Accumulated Horizontal back porch (in units of pixel clock period)

These bits define the Accumulated Horizontal back porch width which includes the
Horizontal Synchronization and Horizontal back porch pixels minus 1.

The Horizontal back porch is the period between Horizontal Synchronization going
inactive and the start of the active display part of the next scan line.


Bits 15:11 Reserved, must be kept at reset value


Bits 10:0 **AVBP[10:0]:** Accumulated Vertical back porch (in units of horizontal scan line)

These bits define the accumulated Vertical back porch width which includes the Vertical
Synchronization and Vertical back porch lines minus 1.

The Vertical back porch is the number of horizontal scan lines at a start of frame to the
start of the first active scan line of the next frame.


**16.7.3** **LTDC Active Width Configuration Register (LTDC_AWCR)**


This register defines the accumulated number of Horizontal Synchronization, back porch
and Active pixels minus 1 ( **HSYNC width + HBP + Active Width - 1)** and the accumulated
number of Vertical Synchronization, back porch lines and Active lines minus 1 ( **VSYNC**
**Height+ BVBP + Active Height - 1)** . Refer to _Figure 82_ and _Section 16.4: LTDC_
_programmable parameters_ for an example of configuration.


Address offset: 0x10


Reset value: 0x0000 0000

|31 30 29 28|27 26 25 24 23 22 21 20 19 18 17 16|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|AAW[11:0]|AAW[11:0]|AAW[11:0]|AAW[11:0]|AAW[11:0]|AAW[11:0]|AAW[11:0]|AAW[11:0]|AAW[11:0]|AAW[11:0]|AAW[11:0]|AAW[11:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11|10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:28 Reserved, must be kept at reset value


Bits 27:16 **AAW[11:0]** : Accumulated Active Width (in units of pixel clock period)

These bits define the Accumulated Active Width which includes the Horizontal

Synchronization, Horizontal back porch and Active pixels minus 1.

The Active Width is the number of pixels in active display area of the panel scan line. The
maximum Active Width supported is 0x400.


Bits 15:11 Reserved, must be kept at reset value


Bits 10:0 **AAH[10:0]** : Accumulated Active Height (in units of horizontal scan line)

These bits define the Accumulated Height which includes the Vertical Synchronization,
Vertical back porch and the Active Height lines minus 1. The Active Height is the number
of active lines in the panel. The maximum Active Height supported is 0x300.


RM0090 Rev 21 497/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


**16.7.4** **LTDC Total Width Configuration Register (LTDC_TWCR)**


This register defines the accumulated number of Horizontal Synchronization, back porch,
Active and front porch pixels minus 1 ( **HSYNC Width + HBP + Active Width + HFP - 1)** and
the accumulated number of Vertical Synchronization, back porch lines, Active and Front
lines minus 1 ( **VSYNC Height+ BVBP + Active Height + VFP - 1)** . Refer to _Figure 82_ and
_Section 16.4: LTDC programmable parameters_ for an example of configuration.


Address offset: 0x14


Reset value: 0x0000 0000

|31 30 29 28|27 26 25 24 23 22 21 20 19 18 17 16|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|16 14 13 12 11|10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:28 Reserved, must be kept at reset value


Bits 27:16 **TOTALW[11:0]:** Total Width (in units of pixel clock period)

These bits defines the accumulated Total Width which includes the Horizontal

Synchronization, Horizontal back porch, Active Width and Horizontal front porch pixels
minus 1.


Bits 15:11 Reserved, must be kept at reset value


Bits 10:0 **TOTALH[10:0]** : Total Height (in units of horizontal scan line)

These bits defines the accumulated Height which includes the Vertical Synchronization,
Vertical back porch, the Active Height and Vertical front porch Height lines minus 1.


**16.7.5** **LTDC Global Control Register (LTDC_GCR)**


This register defines the global configuration of the LCD-TFT controller.


Address offset: 0x18


Reset value: 0x0000 2220


|31|30|29|28|27 26 25 24 23 22 21 20 19 18 17|16|
|---|---|---|---|---|---|
|HSPOL|VSPOL|DEPOL|PCPOL|Reserved|DEN|
|rw|rw|rw|rw|rw|rw|











|15|14 13 12|Col3|Col4|11|10 9 8|Col7|Col8|7|6 5 4|Col11|Col12|3 2 1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserve<br>d|DRW[2:0]|DRW[2:0]|DRW[2:0]|Reser<br>ved|DGW[2:0]|DGW[2:0]|DGW[2:0]|Reser<br>ved|DBW[2:0]|DBW[2:0]|DBW[2:0]|Reserved|LTDCEN|
|Reserve<br>d|r|r|r|r|r|r|r|r|r|r|r|r|rw|


498/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


Bit 31 **HSPOL** : Horizontal Synchronization Polarity

This bit is set and cleared by software.

0: Horizontal Synchronization polarity is active low
1: Horizontal Synchronization polarity is active high


Bit 30 **VSPOL** : Vertical Synchronization Polarity

This bit is set and cleared by software.

0: Vertical Synchronization is active low
1: Vertical Synchronization is active high


Bit 29 **DEPOL** : Data Enable Polarity

This bit is set and cleared by software.

0: Data Enable polarity is active low
1: Data Enable polarity is active high


Bit 28 **PCPOL** : Pixel Clock Polarity

This bit is set and cleared by software.

0: input pixel clock
1: inverted input pixel clock


Bits 27:17 Reserved, must be kept at reset value


Bit 16 **DEN** : Dither Enable

This bit is set and cleared by software.

0: Dither disable

1: Dither enable


Bit 15 Reserved, must be kept at reset value


Bits 14:12 **DRW[2:0]** : Dither Red Width

These bits return the Dither Red Bits


Bit 11 Reserved, must be kept at reset value


Bits 10:8 **DGW[2:0]** : Dither Green Width

These bits return the Dither Green Bits


Bit 7 Reserved, must be kept at reset value


Bits 6:4 **DBW[2:0]** : Dither Blue Width

These bits return the Dither Blue Bits


Bits 3:1 Reserved, must be kept at reset value


Bit 0 **LTDCEN** : LCD-TFT controller enable bit

This bit is set and cleared by software.

0: LTDC disable

1: LTDC enable


RM0090 Rev 21 499/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


**16.7.6** **LTDC Shadow Reload Configuration Register (LTDC_SRCR)**


This register allows to reload either immediately or during the vertical blanking period, the
shadow registers values to the active registers. The shadow registers are all Layer1 and
Layer2 registers except the LTDC_L1CLUTWR and the LTDC_L2CLUTWR.


Address offset: 0x24


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4 3 2|1|0|
|---|---|---|
|Reserved|VBR|IMR|
|Reserved|rw|rw|



Bits 31:2 Reserved, must be kept at reset value


Bit 1 **VBR** : Vertical Blanking Reload

This bit is set by software and cleared only by hardware after reload. (it cannot be cleared
through register write once it is set)

0: No effect

1: The shadow registers are reloaded during the vertical blanking period (at the
beginning of the first line after the Active Display Area)


Bit 0 **IMR** : Immediate Reload

This bit is set by software and cleared only by hardware after reload.

0: No effect

1: The shadow registers are reloaded immediately


_Note:_ _The shadow registers read back the active values. Until the reload has been done, the 'old'_
_value is read._


**16.7.7** **LTDC Background Color Configuration Register (LTDC_BCCR)**


This register defines the background color (RGB888).


Address offset: 0x2C


_Reset value: 0x0000 0000_

|31 30 29 28 27 26 25 24|23 22 21 20 19 18 17 16|Col3|Col4|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|BCRED[7:0]|BCRED[7:0]|BCRED[7:0]|BCRED[7:0]|BCRED[7:0]|BCRED[7:0]|BCRED[7:0]|BCRED[7:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8|7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|BCGREEN[7:0]|BCBLUE[7:0]|BCBLUE[7:0]|BCBLUE[7:0]|BCBLUE[7:0]|BCBLUE[7:0]|BCBLUE[7:0]|BCBLUE[7:0]|BCBLUE[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|



500/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


Bits 31:24 Reserved, must be kept at reset value


Bits 23:16 **BCRED[7:0]** : Background Color Red value

These bits configure the background red value


Bits 15:8 **BCGREEN[7:0]** : Background Color Green value

These bits configure the background green value


Bits 7:0 **BCBLUE[7:0]** : Background Color Blue value

These bits configure the background blue value


**16.7.8** **LTDC Interrupt Enable Register (LTDC_IER)**


This register determines which status flags generate an interrupt request by setting the
corresponding bit to 1.


Address offset: 0x34


_Reset value: 0x0000 0000_


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4|3|2|1|0|
|---|---|---|---|---|
|Reserved|RRIE|TERRIE|FUIE|LIE|
|Reserved|rw|rw|rw|rw|



Bits 31:4 Reserved, must be kept at reset value


Bit 3 **RRIE** : Register Reload interrupt enable

This bit is set and cleared by software

0: Register Reload interrupt disable
1: Register Reload interrupt enable


Bit 2 **TERRIE** : Transfer Error Interrupt Enable

This bit is set and cleared by software

0: Transfer Error interrupt disable
1: Transfer Error interrupt enable


Bit 1 **FUIE** : FIFO Underrun Interrupt Enable

This bit is set and cleared by software

0: FIFO Underrun interrupt disable
1: FIFO Underrun Interrupt enable


Bit 0 **LIE** : Line Interrupt Enable

This bit is set and cleared by software

0: Line interrupt disable
1: Line Interrupt enable


RM0090 Rev 21 501/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


**16.7.9** **LTDC Interrupt Status Register (LTDC_ISR)**


This register returns the interrupt status flag


Address offset: 0x38


_Reset value: 0x0000 0000_


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4|3|2|1|0|
|---|---|---|---|---|
|Reserved|RRIF|TERRIF|FUIF|LIF|
|Reserved|r|r|r|r|



Bits 31:24 Reserved, must be kept at reset value


Bit 3 **RRIF** : Register Reload Interrupt Flag

0: No Register Reload interrupt generated
1: Register Reload interrupt generated when a vertical blanking reload occurs (and the
first line after the active area is reached)


Bit 2 **TERRIF** : Transfer Error interrupt flag

0: No Transfer Error interrupt generated
1: Transfer Error interrupt generated when a Bus error occurs


Bit 1 **FUIF** : FIFO Underrun Interrupt flag

0: NO FIFO Underrun interrupt generated.
1: A FIFO underrun interrupt is generated, if one of the layer FIFOs is empty and pixel
data is read from the FIFO


Bit 0 **LIF** : Line Interrupt flag

0: No Line interrupt generated
1: A Line interrupt is generated, when a programmed line is reached


**16.7.10** **LTDC Interrupt Clear Register (LTDC_ICR)**


Address offset: 0x3C


_Reset value: 0x0000 0000_


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4|3|2|1|0|
|---|---|---|---|---|
|Reserved|CRRIF|CTERRIF|CFUIF|CLIF|
|Reserved|w|w|w|w|



502/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


Bits 31:24 Reserved, must be kept at reset value


Bit 3 **CRRIF** : Clears Register Reload Interrupt Flag

0: No effect

1: Clears the RRIF flag in the LTDC_ISR register


Bit 2 **CTERRIF** : Clears the Transfer Error Interrupt Flag

0: No effect

1: Clears the TERRIF flag in the LTDC_ISR register.


Bit 1 **CFUIF** : Clears the FIFO Underrun Interrupt flag

0: No effect

1: Clears the FUDERRIF flag in the LTDC_ISR register.


Bit 0 **CLIF** : Clears the Line Interrupt Flag

0: No effect

1: Clears the LIF flag in the LTDC_ISR register.


**16.7.11** **LTDC Line Interrupt Position Configuration Register (LTDC_LIPCR)**


This register defines the position of the line interrupt. The line value to be programmed
depends on the timings parameters. Refer to _Figure 82_ .


Address offset: 0x40


_Reset value: 0x0000 0000_


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11|10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:11 Reserved, must be kept at reset value


Bits 10:0 **LIPOS[10:0]** : Line Interrupt Position

These bits configure the line interrupt position


**16.7.12** **LTDC Current Position Status Register (LTDC_CPSR)**


Address offset: 0x44


_Reset value: 0x0000 0000_

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|CYPOS{15;0]|
|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|r|



RM0090 Rev 21 503/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


Bits 31:16: **CXPOS[15:0]** : Current X Position

These bits return the current X position


Bits 15:0 **CYPOS[15:0]** : Current Y Position

These bits return the current Y position


**16.7.13** **LTDC Current Display Status Register (LTDC_CDSR)**


This register returns the status of the current display phase which is controlled by the
HSYNC, VSYNC, and Horizontal/Vertical DE signals.


Example: if the current display phase is the vertical synchronization, the VSYNCS bit is set
(active high). If the current display phase is the horizontal synchronization, the HSYNCS bit
is active high.


Address offset: 0x48


_Reset value: 0x0000 000F_


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved



|15 14 13 12 11 10 9 8 7 6 5 4|3|2|1|0|
|---|---|---|---|---|
|Reserved|HSYNC<br>S|VSYNC<br>S|HDES|VDES|
|Reserved|r|r|r|r|


Bits 31:24 Reserved, must be kept at reset value


Bit 3 **HSYNCS** : Horizontal Synchronization display Status

0: Active low

1: Active high


Bit 2 **VSYNCS** : Vertical Synchronization display Status

0: Active low

1: Active high


Bit 1 **HDES** : Horizontal Data Enable display Status

0: Active low

1: Active high


Bit 0 **VDES** : Vertical Data Enable display Status

0: Active low

1: Active high





_Note:_ _The returned status does not depend on the configured polarity in the_ _**LTDC_GCR**_ _register,_
_instead it returns the current active display phase._


504/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


**16.7.14** **LTDC Layerx Control Register (LTDC_LxCR) (where x=1..2)**


Address offset: 0x84 + 0x80 x ( _Layerx_ -1), _Layerx_ = 1 or 2


_Reset value: 0x0000 0000_


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5|4|3 2|1|0|
|---|---|---|---|---|
|Reserved|CLUTEN|Reserved|COLKEN|LEN|
|Reserved|rw|rw|rw|rw|



Bits 31:5 Reserved, must be kept at reset value


Bit 4 **CLUTEN** : Color Look-Up Table Enable

This bit is set and cleared by software.

0: Color Look-Up Table disable
1: Color Look-Up Table enable

The CLUT is only meaningful for L8, AL44 and AL88 pixel format. Refer to _Color Look-Up_
_Table (CLUT) on page 491_


Bit 3 Reserved, must be kept at reset value


Bit 2 Reserved, must be kept at reset value


Bit 1 **COLKEN** : Color Keying Enable

This bit is set and cleared by software.

0: Color Keying disable
1: Color Keying enable


Bit 0 **LEN** : Layer Enable

This bit is set and cleared by software.

0: Layer disable
1: Layer enable


RM0090 Rev 21 505/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


**16.7.15** **LTDC Layerx Window Horizontal Position Configuration Register**
**(LTDC_LxWHPCR) (where x=1..2)**


This register defines the Horizontal Position (first and last pixel) of the layer 1 or 2 window.


The first visible pixel of a line is the programmed value of _**AHBP[10:0] bits + 1**_ in the
**LTDC_BPCR** register.


The last visible pixel of a line is the programmed value of _**AAW[10:0] bits**_ in the
**LTDC_AWCR** register.


Address offset: 0x88 + 0x80 x ( _Layerx_ -1), _Layerx_ = 1 or 2


_Reset value: 0x0000 0000_

|31 30 29 28|27 26 25 24 23 22 21 20 19 18 17 16|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12|11 10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:28 Reserved, must be kept at reset value


Bits 27:16 **WHSPPOS[11:0]** : Window Horizontal Stop Position

These bits configure the last visible pixel of a line of the layer window.
The following condition must be respected:
WHSPPOS[11:0] ≥ AHBP[10:0] bits + 1 (programmed in LTDC_BPCR register)


Bits 15:12 Reserved, must be kept at reset value


Bits 11:0 **WHSTPOS[11:0]** : Window Horizontal Start Position

These bits configure the first visible pixel of a line of the layer window.
The following condition must be respected:
WHSTPOS[11:0] must be ≤ AAW[10:0] bits (programmed in the LTDC_AWCR
register).


Example:


The LTDC_BPCR register is configured to 0x000E0005(AHBP[11:0] is 0xE) and the
LTDC_AWCR register is configured to 0x028E01E5(AAW[11:0] is 0x28E). To configure the
horizontal position of a window size of 630x460, with horizontal start offset of 5 pixels in the
Active data area.


1. Layer window first pixel: WHSTPOS[11:0] should be programmed to 0x14 (0xE+1+0x5)


2. Layer window last pixel: WHSPPOS[11:0] should be programmed to 0x28A


506/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


**16.7.16** **LTDC Layerx Window Vertical Position Configuration Register**
**(LTDC_LxWVPCR) (where x=1..2)**


This register defines the vertical position (first and last line) of the layer1 or 2 window.


The first visible line of a frame is the programmed value of _**AVBP[10:0] bits + 1**_ in the
register **LTDC_BPCR** register.


The last visible line of a frame is the programmed value of _**AAH[10:0] bits**_ in the
**LTDC_AWCR** register.


Address offset: 0x8C + 0x80 x ( _Layerx_ -1), _Layerx_ = 1 or 2


_Reset value: 0x0000 0000_

|31 30 29 28 27|26 25 24 23 22 21 20 19 18 17 16|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11|10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:27 Reserved, must be kept at reset value


Bits 26:16 **WVSPPOS[10:0]** : Window Vertical Stop Position

These bits configures the last visible line of the layer window.
The following condition must be respected:
WHSPPOS[11:0] must be ≥ AVBP[10:0] bits + 1 (programmed in LTDC_BPCR
register)


Bits 15:11 Reserved, must be kept at reset value


Bits 10:0 **WVSTPOS[10:0]** : Window Vertical Start Position

These bits configure the first visible line of the layer window.
The following condition must be respected:
WHSTPOS[11:0] must be ≤ AAH[10:0] bits (programmed in the LTDC_AWCR register)


Example:


The LTDC_BPCR register is configured to 0x000E0005 (AVBP[10:0] is 0x5) and the
LTDC_AWCR register is configured to 0x028E01E5 (AAH[10:0] is 0x1E5). To configure the
vertical position of a window size of 630x460, with vertical start offset of 8 lines in the Active
data area:


1. Layer window first line: WVSTPOS[10:0] should be programmed to 0xE (0x5 + 1 + 0x8)


2. Layer window last line: WVSPPOS[10:0] should be programmed to 0x1DA


RM0090 Rev 21 507/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


**16.7.17** **LTDC Layerx Color Keying Configuration Register (LTDC_LxCKCR)**
**(where x=1..2)**


This register defines the color key value (RGB), which is used by the Color Keying.


Address offset: 0x90 + 0x80 x ( _Layerx_ -1), _Layerx_ = 1 or 2


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24|23 22 21 20 19 18 17 16|Col3|Col4|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8|7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|CKGREEN[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:24 Reserved, must be kept at reset value


Bits 23:16 **CKRED[7:0]** : Color Key Red value


Bits 15:8 **CKGREEN[7:0]** : Color Key Green value


Bits 7:0 **CKBLUE[7:0]** : Color Key Blue value


**16.7.18** **LTDC Layerx Pixel Format Configuration Register (LTDC_LxPFCR)**
**(where x=1..2)**


This register defines the pixel format which is used for the stored data in the frame buffer of
a layer. The pixel data is read from the frame buffer and then transformed to the internal
format 8888 (ARGB).


Address offset: 0x94 + 0x80 x ( _Layerx_ -1), _Layerx_ = 1 or 2


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8 7 6 5 4 3|2 1 0|Col3|Col4|
|---|---|---|---|
|Reserved|PF[2:0]|PF[2:0]|PF[2:0]|
|Reserved|rw|rw|rw|



508/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


Bits 31:3 Reserved, must be kept at reset value


Bits 2:0 **PF[2:0]** : Pixel Format

These bits configures the Pixel format

000: ARGB8888

001: RGB888

010: RGB565

011: ARGB1555

100: ARGB4444

101: L8 (8-Bit Luminance)

110: AL44 (4-Bit Alpha, 4-Bit Luminance)

111: AL88 (8-Bit Alpha, 8-Bit Luminance)


**16.7.19** **LTDC Layerx Constant Alpha Configuration Register (LTDC_LxCACR)**
**(where x=1..2)**


This register defines the constant alpha value (divided by 255 by Hardware), which is used
in the alpha blending. Refer to LTDC_LxBFCR register.


Address offset: 0x98 + 0x80 x ( _Layerx_ -1), _Layerx_ = 1 or 2


Reset value: (Layerx -1) 0x0000 00FF


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11 10 9 8|7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|Reserved|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:8 Reserved, must be kept at reset value


Bits 7:0 **CONSTA[7:0]** : Constant Alpha

These bits configure the Constant Alpha used for blending. The Constant Alpha is divided
by 255 by hardware.

Example: if the programmed Constant Alpha is 0xFF, the Constant Alpha value is
255/255=1


**16.7.20** **LTDC Layerx Default Color Configuration Register (LTDC_LxDCCR)**
**(where x=1..2)**


This register defines the default color of a layer in the format ARGB. The default color is
used outside the defined layer window or when a layer is disabled. The reset value of
0x00000000 defines a transparent black color.


Address offset: 0x9C + 0x80 x ( _Layerx_ -1), _Layerx_ = 1 or 2


Reset value: 0x0000 0000


RM0090 Rev 21 509/1757



517


**LCD-TFT controller (LTDC)** **RM0090**

|31 30 29 28 27 26 25 24|23 22 21 20 19 18 17 16|Col3|Col4|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|DCALPHA[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8|7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
|DCGREEN[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:24 **DCALPHA[7:0]** : Default Color Alpha

These bits configure the default alpha value


Bits 23:16 **DCRED[7:0]** : Default Color Red

These bits configure the default red value


Bits 15:8 **DCGREEN[7:0]** : Default Color Green

These bits configure the default green value


Bits 7:0 **DCBLUE[7:0]** : Default Color Blue

These bits configure the default blue value


510/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


**16.7.21** **LTDC Layerx Blending Factors Configuration Register (LTDC_LxBFCR)**
**(where x=1..2)**


This register defines the blending factors F1 and F2.


The general blending formula is: BC = BF1 x C + BF2 x Cs


      - BC = Blended color


      - BF1 = Blend Factor 1


      - C = Current layer color


      - BF2 = Blend Factor 2


      - Cs = subjacent layers blended color


Address offset: 0xA0 + 0x80 x ( _Layerx_ -1), _Layerx_ = 1 or 2


Reset value: 0x0000 0607


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11|10 9 8|Col3|Col4|7 6 5 4 3|2 1 0|Col7|Col8|
|---|---|---|---|---|---|---|---|
|Reserved|BF1[2:0]|BF1[2:0]|BF1[2:0]|Reserved|BF2[2:0]|BF2[2:0]|BF2[2:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|



Bits 31:11 Reserved, must be kept at reset value


Bits 10:8 **BF1[2:0]** : Blending Factor 1

These bits select the blending factor F1

000: Reserved

001: Reserved

010: Reserved

011: Reserved

100: Constant Alpha

101: Reserved

110: Pixel Alpha x Constant Alpha

111:Reserved


Bits 7:3 Reserved, must be kept at reset value


Bits 2:0 **BF2[2:0]** : Blending Factor 2

These bits select the blending factor F2

000: Reserved

001: Reserved

010: Reserved

011: Reserved

100: Reserved

101: 1 - Constant Alpha

110: Reserved

111: 1 - (Pixel Alpha x Constant Alpha)


RM0090 Rev 21 511/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


_Note:_ _The Constant Alpha value, is the programmed value in the LxCACR register divided by 255_
_by hardware._


_Example: Only layer1 is enabled, BF1 configured to Constant Alpha_


_BF2 configured to_ 1 - _Constant Alpha_


_Constant Alpha: The Constant Alpha programmed in the LxCACR register is 240 (0xF0)._
_Thus, the Constant Alpha value is 240/255 = 0.94_


_C: Current Layer Color is 128_


_Cs: Background color is 48_


_Layer1 is blended with the background color._


_BC = Constant Alpha_ x C + _(1 - Constant Alpha_ ) x Cs _= 0.94 x 128 + (1- 0.94) x 48 = 123._


**16.7.22** **LTDC Layerx Color Frame Buffer Address Register (LTDC_LxCFBAR)**
**(where x=1..2)**


This register defines the color frame buffer start address which has to point to the address
where the pixel data of the top left pixel of a layer is stored in the frame buffer.


Address offset: 0xAC + 0x80 x ( _Layerx_ -1), _Layerx_ = 1 or 2


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|
|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:0 **CFBADD[31:0]** : Color Frame Buffer Start Address

These bits defines the color frame buffer start address.


**16.7.23** **LTDC Layerx Color Frame Buffer Length Register (LTDC_LxCFBLR)**
**(where x=1..2)**


This register defines the color frame buffer line length and pitch.


Address offset: 0xB0 + 0x80 x ( _Layerx_ -1), _Layerx_ = 1 or 2


Reset value: 0x0000 0000

|31 30 29|28 27 26 25 24 23 22 21 20 19 18 17 16|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|


|15 14 13|12 11 10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|Col13|Col14|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



512/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


Bits 31:29 Reserved, must be kept at reset valuer


Bits 28:16 **CFBP[12:0]** : Color Frame Buffer Pitch in bytes

These bits define the pitch which is the increment from the start of one line of pixels to the
start of the next line in bytes.


Bits 15:13 Reserved, must be kept at reset value


Bits 12:0 **CFBLL[12:0]** : Color Frame Buffer Line Length

These bits define the length of one line of pixels in bytes + 3.

The line length is computed as follows: Active high width x number of bytes per pixel + 3.


Example:


      - A frame buffer having the format RGB565 (2 bytes per pixel) and a width of 256 pixels
(total number of bytes per line is 256x2=512 bytes), where pitch = line length requires a
value of 0x02000203 to be written into this register.


      - A frame buffer having the format RGB888 (3 bytes per pixel) and a width of 320 pixels
(total number of bytes per line is 320x3=960), where pitch = line length requires a value
of 0x03C003C3 to be written into this register.


**16.7.24** **LTDC Layerx ColorFrame Buffer Line Number Register**
**(LTDC_LxCFBLNR) (where x=1..2)**


This register defines the number of lines in the color frame buffer.


Address offset: 0xB4 + 0x80 x ( _Layerx_ -1), _Layerx_ = 1 or 2


Reset value: 0x0000 0000


31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16


Reserved

|15 14 13 12 11|10 9 8 7 6 5 4 3 2 1 0|Col3|Col4|Col5|Col6|Col7|Col8|Col9|Col10|Col11|Col12|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Reserved|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|
|Reserved|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|



Bits 31:11 Reserved, must be kept at reset value


Bits 10:0 **CFBLNBR[10:0]** : Frame Buffer Line Number

These bits define the number of lines in the frame buffer which corresponds to the Active
high width.


_Note:_ _The number of lines and line length settings define how much data is fetched per frame for_
_every layer. If it is configured to less bytes than required, a FIFO underrun interrupt is_
_generated if enabled._


_The start address and pitch settings on the other hand define the correct start of every line in_

_memory._


RM0090 Rev 21 513/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


**16.7.25** **LTDC Layerx CLUT Write Register (LTDC_LxCLUTWR)**
**(where x=1..2)**


This register defines the CLUT address and the RGB value.


Address offset: 0xC4 + 0x80 x ( _Layerx_ -1), _Layerx_ = 1 or 2


Reset value: 0x0000 0000

|31 30 29 28 27 26 25 24|Col2|Col3|Col4|Col5|Col6|Col7|Col8|23 22 21 20 19 18 17 16|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|
|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|


|15 14 13 12 11 10 9 8|Col2|Col3|Col4|Col5|Col6|Col7|Col8|7 6 5 4 3 2 1 0|Col10|Col11|Col12|Col13|Col14|Col15|Col16|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|
|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|w|



Bits 31:24 **CLUTADD[7:0]** : CLUT Address

These bits configure the CLUT address (color position within the CLUT) of each RGB
value


Bits 23:16 **RED[7:0]** : Red value

These bits configure the red value


Bits 15:8 **GREEN[7:0]** : Green value

These bits configure the green value


Bits 7:0 **BLUE[7:0]** : Blue value

These bits configure the blue value


_Note:_ _The CLUT write register should only be configured during blanking period or if the layer is_
_disabled. The CLUT can be enabled or disabled in the_ _**LTDC_LxCR**_ _register._


_The CLUT is only meaningful for L8, AL44 and AL88 pixel format._


514/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**


**16.7.26** **LTDC register map**


The following table summarizes the LTDC registers. Refer to the register boundary
addresses table for the LTDC register base address.


**Table 93. LTDC register map and reset values**































































































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x0008|LTDC_SSCR|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|HSW[9:0]|HSW[9:0]|HSW[9:0]|HSW[9:0]|HSW[9:0]|HSW[9:0]|HSW[9:0]|HSW[9:0]|HSW[9:0]|HSW[9:0]|Reserved|Reserved|Reserved|Reserved|Reserved|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|VSH[10:0]|
|0x0008|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x000C|LTDC_BPCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|AHBP[11:0]|Reserved|Reserved|Reserved|Reserved|Reserved|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|AVBP[10:0]|
|0x000C|LTDC_BPCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0010|LTDC_AWCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|AAV[11:0]|AAV[11:0]|AAV[11:0]|AAV[11:0]|AAV[11:0]|AAV[11:0]|AAV[11:0]|AAV[11:0]|AAV[11:0]|AAV[11:0]|AAV[11:0]|AAV[11:0]|Reserved|Reserved|Reserved|Reserved|Reserved|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|AAH[10:0]|
|0x0010|LTDC_AWCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|0|9|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0014|LTDC_TWCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|TOTALW[11:0]|Reserved|Reserved|Reserved|Reserved|Reserved|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|TOTALH[10:0]|
|0x0014|LTDC_TWCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0018|LTDC_GCR<br>Reset value|HSPOL|VSPOL|DEPOL|PCPOL|Reserve|Reserve|Reserve|Reserve|Reserve|Reserve|Reserve|Reserve|Reserve|Reserve|Reserve|DEN|Reserved|DRW[2:0]|DRW[2:0]|DRW[2:0]|Reserved|DGW[2:0]|DGW[2:0]|DGW[2:0]|Reserved|DBW[2:0]|DBW[2:0]|DBW[2:0]|Reserved|Reserved|Reserved|LTDCEN|
|0x0018|LTDC_GCR<br>Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|1|0|0|0|1|0|0|0|1|0|0|0|0|0|
|0x0024|LTDC_SRCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|VBR|IMR|
|0x0024|LTDC_SRCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|
|0x002C|LTDC_BCCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|BC[23:0]|
|0x002C|LTDC_BCCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0034|LTDC_IER<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|RRIE|TERRIE|FUIE|LIE|
|0x0034|LTDC_IER<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|
|0x0038|LTDC_ISR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|RRIF|TERRIF|FUIF|LIF|
|0x0038|LTDC_ISR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|
|0x003C|LTDC_ICR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CRRIF|CTERRIF|CFUIF|CLIF|
|0x003C|LTDC_ICR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|
|0x0040|LTDC_LIPCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|LIPOS[10:0]|
|0x0040|LTDC_LIPCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|
|0x0044|LTDC_CPSR|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CXPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|CYPOS[15:0]|
|0x0044|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0048|LTDC_CDSR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|HSYNCS|VSYNCS|HDES|VDES|
|0x0048|LTDC_CDSR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|1|1|1|1|
|0x0084|LTDC_L1CR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CLUTEN|Reserved|Reserved|COLKEN|LEN|
|0x0084|LTDC_L1CR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|
|0x0088|LTDC_L1WHPCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|Reserved|Reserved|Reserved|Reserved|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|
|0x0088|LTDC_L1WHPCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


RM0090 Rev 21 515/1757



517


**LCD-TFT controller (LTDC)** **RM0090**


**Table 93. LTDC register map and reset values (continued)**









































































































|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x008C|LTDC_L1WVPCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|Reserved|Reserved|Reserved|Reserved|Reserved|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|
|0x008C|LTDC_L1WVPCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0090|LTDC_L1CKCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|
|0x0090|LTDC_L1CKCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0094|LTDC_L1PFCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|PF[2:0]|PF[2:0]|PF[2:0]|
|0x0094|LTDC_L1PFCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|
|0x0098|LTDC_L1CACR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|
|0x0098|LTDC_L1CACR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|1|1|1|1|1|1|1|1|
|0x009C|LTDC_L1DCCR<br>Reset value|DCALPHA[7:0]|DCALPHA[7:0]|DCALPHA[7:0]|DCALPHA[7:0]|DCALPHA[7:0]|DCALPHA[7:0]|DCALPHA[7:0]|DCALPHA[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|
|0x009C|LTDC_L1DCCR<br>Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00A0|LTDC_L1BFCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|BF1[2:0]|BF1[2:0]|BF1[2:0]|Reserved|Reserved|Reserved|Reserved|Reserved|BF2[2:0]|BF2[2:0]|BF2[2:0]|
|0x00A0|LTDC_L1BFCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|1|1|0|0|0|0|0|0|1|1|1|
|0x00AC|LTDC_L1CFBAR<br>Reset value|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|
|0x00AC|LTDC_L1CFBAR<br>Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00B0|LTDC_L1CFBLR<br>Reset value|Reserved|Reserved|Reserved|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|Reserved|Reserved|Reserved|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|
|0x00B0|LTDC_L1CFBLR<br>Reset value|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x00B4|LTDC_L1CFBLNR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|
|0x00B4|LTDC_L1CFBLNR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|
|0x00C4|LTDC_L1CLUTWR|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|
|0x00C4|Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0104|LTDC_L2CR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CLUTEN|Reserved|Reserved|COLKEN|LEN|
|0x0104|LTDC_L2CR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|
|0x0108|LTDC_L2WHPCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|WHSPPOS[11:0]|Reserved|Reserved|Reserved|Reserved|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|WHSTPOS[11:0]|
|0x0108|LTDC_L2WHPCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x010C|LTDC_L2WVPCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|WVSPPOS[10:0]|Reserved|Reserved|Reserved|Reserved|Reserved|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|WVSTPOS[10:0]|
|0x010C|LTDC_L2WVPCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0110|LTDC_L2CKCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKRED[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKGREEN[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|CKBLUE[7:0]|
|0x0110|LTDC_L2CKCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0114|LTDC_L2PFCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|PF[2:0]|PF[2:0]|PF[2:0]|
|0x0114|LTDC_L2PFCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|0|0|0|
|0x0118|LTDC_L2CACR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|CONSTA[7:0]|
|0x0118|LTDC_L2CACR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|1|1|1|1|1|1|1|1|
|0x011C|LTDC_L2DCCR<br>Reset value|DCALPHA[7:0]|DCALPHA[7:0]|DCALPHA[7:0]|DCALPHA[7:0]|DCALPHA[7:0]|DCALPHA[7:0]|DCALPHA[7:0]|DCALPHA[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCRED[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCGREEN[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|DCBLUE[7:0]|
|0x011C|LTDC_L2DCCR<br>Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0120|LTDC_L2BFCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|BF1[2:0]|BF1[2:0]|BF1[2:0]|Reserved|Reserved|Reserved|Reserved|Reserved|BF2[2:0]|BF2[2:0]|BF2[2:0]|
|0x0120|LTDC_L2BFCR<br>Reset value|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|1|1|0|0|0|0|0|0|1|1|1|
|0x012C|LTDC_L2CFBAR<br>Reset value|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|CFBADD[31:0]|
|0x012C|LTDC_L2CFBAR<br>Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|
|0x0130|LTDC_L2CFBLR<br>Reset value|Reserved|Reserved|Reserved|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|CFBP[12:0]|Reserved|Reserved|Reserved|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|CFBLL[12:0]|
|0x0130|LTDC_L2CFBLR<br>Reset value|Reserved|Reserved|Reserved|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


516/1757 RM0090 Rev 21


**RM0090** **LCD-TFT controller (LTDC)**





**Table 93. LTDC register map and reset values (continued)**



|Offset|Register|31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0x0134|LTDC_L2CFBLNR|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|Reserved|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|CFBLNBR[10:0]|
|0x0134|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|Reset value|0|0|0|0|0|0|0|0|0|0|0|
|0x0144|LTDC_L2CLUTWR<br>Reset value|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|CLUTADD[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|RED[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|GREEN[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|BLUE[7:0]|
|0x0144|LTDC_L2CLUTWR<br>Reset value|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|


RM0090 Rev 21 517/1757



517


