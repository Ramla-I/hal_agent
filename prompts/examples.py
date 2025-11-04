stm_datasheet_example = """
--- EXAMPLE 1 ---
# INPUT

## REGISTER NAME AND PERIPHERAL NAME
    Register name: GPIOA_OTYPER
    Peripheral name: GPIOA

## DATASHEET INPUT
    **8.4.2** **GPIO port output type register (GPIOx_OTYPER)**
    **(x = A..I/J/K)**

    Address offset: 0x04

    Reset value: 0x0000 0000

    31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16
    Reserved
    |15 14 13 12 11 10 9 8 7 6 5 4 3 2|1|0|
    |---|---|---|
    |reserved|OT1|OT0|
    |reserved|rw|rw|

    Bits 31:2 Reserved, must be kept at reset value.

    Bits 1:0 **OTy** : Port x configuration bits (y = 0..1)

    These bits are written by software to configure the output type of the I/O port.
    0: Output push-pull (reset state)
    1: Output open-drain

# OUTPUT
    I can see that the register name is GPIOx_OTYPER where x can equal A.
    So this is the GPIOA_OTYPER register.
    I can see that the GPIOx_OTYPER has a size of 32 bits.
    It's offset it 0x04 and its reset value is 0x00000000.
    Bits 31:2 are reserved so read-only.
    Bits 1:0 are read-write.
    There are no write-only fields.
    There are 2 subfields with the name OTy where y is 0 to 1.
    Each of these subfields can be written with one of two enumerated values:
        Name = OutputPushPull, Value = 0 
        Name = OutputOpenDrain, Value = 1
    
    ```json
    {
        "datasheet_register_abbreviation": "GPIOA_OTYPER",
        "address_offset": "0x04",
        "reset_value": "0x00000000",
        "size": 32,
        "readonly_bits": [
            {
            "start_bit": 2,
            "end_bit": 31
            }
        ],
        "write_only_bits": [],
        "read_write_bits": [
            {
            "start_bit": 0,
            "end_bit": 1
            }
        ],
        "subfields": [
            {
                "name": "OT0",
                "description": "Port 0 configuration bits",
                "bit_number": {
                    "start_bit": 0,
                    "end_bit": 0
                },
                "enumerated_values": [
                    {
                        "value": "0",
                        "name": "OutputPushPull"
                    },
                    {
                        "value": "1",
                        "name": "OutputOpenDrain"
                    }
                ]
            },
            { 
                "name": "OT1",
                "description": "Port 1 configuration bits",
                "bit_number": {
                    "start_bit": 1,
                    "end_bit": 1
                },
                "enumerated_values": [
                    {
                        "value": "0",
                        "name": "OutputPushPull"
                    },
                    {
                        "value": "1",
                        "name": "OutputOpenDrain"
                    }
                ]
            },
        ]
    }
    ```

--- EXAMPLE 2 ---
# INPUT
## REGISTER NAME AND PERIPHERAL NAME
    Register name: TIM12_CR2
    Peripheral name: TIM12

## DATASHEET INPUT
    **17.4.2** **TIM1 and TIM8 control register 2 (TIMx_CR2)**

    Address offset: 0x04

    Reset value: 0x0000

    |15|14|13|12|11|10|9|8|7|6 5 4|Col11|Col12|3|2|1|0|
    |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
    |Res.|OIS4|OIS3N|OIS3|OIS2N|OIS2|OIS1N|OIS1|TI1S|MMS[2:0]|MMS[2:0]|MMS[2:0]|CCDS|CCUS|Res.|CCPC|
    |Res.|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|

# OUTPUT
    I can see that the register name is TIMx_CR2 where x can equal 1 or 8.
    So this information is not relevant to the TIM12 peripheral.
    Datasheet does not contain information about the TIM12_CR2 register.
    I will return no JSONoutput for this register.
"""