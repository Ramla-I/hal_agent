# Devices

All datasheets, drivers and SVD files that are used as input are stored in this directory.
It is expected that the folder name is the device number for Intel devices and the Reference Manual number for STM devices. 
That is because one STM reference manual can be used for multiple devices.
Within the individual device folder, the datasheet should be present in both pdf and md format, with the name the same as the folder name.
All SVD files are also place in the individual device folder as well as the driver.
If the datasheet has been split into chapters, the pdfs for the chapters are placed in the sections/ subdirectory.


For example, for reference manual RM0041, the directory structure is:

devices
    |
    rm0041
        |
        rm0041.pdf
        rm0041.md
        stm32f100.svd
        sections/

