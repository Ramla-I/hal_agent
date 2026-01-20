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
    Bits 31:2 are reserved and so do not have to be listed as a subfield.
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
        "subfields": [
            {
                "name": "OT0",
                "description": "Port 0 configuration bits",
                "access": "read-write",
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
                "access": "read-write",
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
            }
        ],
        "access_constraints": []
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
    I will return no JSON output for this register.

--- EXAMPLE 3 ---
# INPUT
## REGISTER NAME AND PERIPHERAL NAME
    Register name: FSMC_BCR2
    Peripheral name: FSMC

## DATASHEET INPUT
    ** SRAM/NOR-flash chip-select control registers 1..4 (FSMC_BCR1..4) **
    Address offset: 0xA000 0000 + 8 * (x - 1), x = 1...4

# OUTPUT
    I can see that the register name is FSMC_BCRx where x can equal 2.
    So this is the FSMC_BCR2 register.
    The address offset is given as 0xA000 0000 + 8 * (x - 1), x = 1...4.
    I will return a function call to calculate the address offset for the FSMC_BCR2 register.

    ```function_call
    { "function_calls": [
        {
            "name": "calculate_address_offset",
            "parameters": {
                "base_address_in_hex": "0xA000 0000",
                "start_register_number": 1,
                "register_number": 2,
                "register_size_in_bytes": 8
            }
        }
    ]}
    ```

--- EXAMPLE 4 ---
# INPUT
## REGISTER NAME AND PERIPHERAL NAME
    Register name: I2C_CR1
    Peripheral name: I2C

## DATASHEET INPUT
    **26.6.1 I2C Control register 1 (I2C_CR1)**

    Address offset: 0x00
    Reset value: 0x0000

    |15|14|13|12|11|10|9|8|7|6|5|4|3|2|1|0|
    |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
    |SWRST|Res.|ALERT|PEC|POS|ACK|STOP|START|NOSTRETCH|ENGC|ENPEC|ENARP|SMBTYPE|Res.|SMBUS|PE|
    |rw|Res.|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|rw|Res.|rw|rw|

    Bit 9 **STOP**: Stop generation
    This bit is set and cleared by software, cleared by hardware when a Stop condition is detected, set by hardware when a timeout error is detected.
    0: No Stop generation.
    1: Stop generation after the current byte transfer or after the current Start condition is sent.

    Bit 8 **START**: Start generation
    This bit is set and cleared by software and cleared by hardware when start is sent or PE=0.
    0: No Start generation
    1: Repeated start generation

    Note: When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware. Otherwise there is a risk of setting a second STOP, START or PEC request.

# OUTPUT
    I can see that the register name is I2C_CR1.
    The address offset is 0x00 and reset value is 0x0000.
    The register is 16 bits (based on the bit field table).
    I can see STOP and START bits which have special constraints mentioned in the Note.
    The Note states that software must not write to I2C_CR1 while STOP, START, or PEC bits are set (before they are cleared by hardware).
    This is an access constraint that needs to be captured.

    ```json
    {
        "datasheet_register_abbreviation": "I2C_CR1",
        "address_offset": "0x00",
        "reset_value": "0x0000",
        "size": 16,
        "subfields": [
            {
                "name": "PE",
                "description": "Peripheral enable",
                "access": "read-write",
                "bit_number": {
                    "start_bit": 0,
                    "end_bit": 0
                },
                "enumerated_values": []
            },
            {
                "name": "START",
                "description": "Start generation",
                "access": "read-write",
                "bit_number": {
                    "start_bit": 8,
                    "end_bit": 8
                },
                "enumerated_values": [
                    {
                        "value": "0",
                        "name": "NoStart"
                    },
                    {
                        "value": "1",
                        "name": "Start"
                    }
                ]
            },
            {
                "name": "STOP",
                "description": "Stop generation",
                "access": "read-write",
                "bit_number": {
                    "start_bit": 9,
                    "end_bit": 9
                },
                "enumerated_values": [
                    {
                        "value": "0",
                        "name": "NoStop"
                    },
                    {
                        "value": "1",
                        "name": "Stop"
                    }
                ]
            }
        ],
        "access_constraints": [
            {
                "target_register": "I2C_CR1",
                "target_fields": [],
                "target_operation": "write",
                "preconditions": [
                    {
                        "register_name": "I2C_CR1",
                        "field_name": "STOP",
                        "required_state": "cleared"
                    },
                    {
                        "register_name": "I2C_CR1",
                        "field_name": "START",
                        "required_state": "cleared"
                    },
                    {
                        "register_name": "I2C_CR1",
                        "field_name": "PEC",
                        "required_state": "cleared"
                    }
                ],
                "postconditions": [],
                "severity": "error",
                "consequence": "Risk of setting a second STOP, START or PEC request",
                "datasheet_text": "When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware. Otherwise there is a risk of setting a second STOP, START or PEC request."
            }
        ]
    }
    ```
"""