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
        "access_constraints_v2": []
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
    This is a state condition on a write operation, so the kind is "state_gate".
    The bits are cleared by hardware, so each condition is established_by "hardware".

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
        "access_constraints_v2": [
            {
                "kind": "state_gate",
                "target_register": "I2C_CR1",
                "target_fields": [],
                "target_operation": "write",
                "preconditions": [
                    {
                        "register": "I2C_CR1",
                        "field": "STOP",
                        "state": "cleared",
                        "established_by": "hardware"
                    },
                    {
                        "register": "I2C_CR1",
                        "field": "START",
                        "state": "cleared",
                        "established_by": "hardware"
                    },
                    {
                        "register": "I2C_CR1",
                        "field": "PEC",
                        "state": "cleared",
                        "established_by": "hardware"
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


# ---------------------------------------------------------------------------
# Worked access-constraint few-shots (grammar v2). Real STM examples per plan
# section 5.2 / decision 11.6 -- these REPLACE the synthetic Intel
# MTQC/RTTDCS example everywhere. Embedded verbatim in every generator system
# prompt (via ACCESS_CONSTRAINTS_V2_GUIDANCE in prompts/register_info_stm.py)
# and in the constraints-only extraction-eval prompt.
# ---------------------------------------------------------------------------

stm_access_constraints_v2_examples = """\
    Worked constraint examples (datasheet text -> access_constraints_v2 entries):

    CONSTRAINT EXAMPLE 1 -- software mode-gate (state_gate, established_by "software"):
    Datasheet text about USART_BRR: "This register can only be written when the USART is disabled (UE=0)."
    The driver itself must clear UE first, so the condition is established_by "software" with action_operation "modify".
    Emits:
    ```json
    [
        {
            "kind": "state_gate",
            "target_register": "USART_BRR",
            "target_fields": [],
            "target_operation": "write",
            "preconditions": [
                {"register": "USART_CR1", "field": "UE", "state": "cleared", "established_by": "software", "action_operation": "modify"}
            ],
            "postconditions": [],
            "severity": "error",
            "consequence": "Writing BRR while the USART is enabled is not allowed and can corrupt the baud rate",
            "datasheet_text": "This register can only be written when the USART is disabled (UE=0)."
        }
    ]
    ```

    CONSTRAINT EXAMPLE 2 -- pre + post software action (state_gate with a software postcondition):
    Datasheet text about RTC_CNTH: "To write to this register it is necessary to enter configuration mode (set CNF). The write operation is only executed when the CNF bit is reset by software after has been set."
    Software must SET RTC_CRL.CNF before the write and CLEAR it afterwards -- a software-established precondition plus a software postcondition, both performed by modifying RTC_CRL.
    Emits:
    ```json
    [
        {
            "kind": "state_gate",
            "target_register": "RTC_CNTH",
            "target_fields": [],
            "target_operation": "write",
            "preconditions": [
                {"register": "RTC_CRL", "field": "CNF", "state": "set", "established_by": "software", "action_operation": "modify"}
            ],
            "postconditions": [
                {"register": "RTC_CRL", "field": "CNF", "state": "cleared", "established_by": "software", "action_operation": "modify"}
            ],
            "severity": "error",
            "consequence": "The write is not executed until CNF is set before and cleared after the write",
            "datasheet_text": "To write to this register it is necessary to enter configuration mode (set CNF). The write operation is only executed when the CNF bit is reset by software after has been set."
        }
    ]
    ```

    CONSTRAINT EXAMPLE 3 -- dual establishment + whole-register condition (state_gate):
    Datasheet text about IWDG_PR: "Write access to the IWDG_PR and IWDG_RLR registers is protected. To modify them, first write the code 0x5555 in the IWDG_KR register. PVU bit of IWDG_SR must be reset in order to be able to change the prescaler divider."
    Two conditions: software must write the key value into the whole IWDG_KR register (whole_register, "equals", established_by "software"), and the hardware-managed PVU flag must be cleared (established_by "hardware"). Values are numeric literals.
    Emits:
    ```json
    [
        {
            "kind": "state_gate",
            "target_register": "IWDG_PR",
            "target_fields": [],
            "target_operation": "write",
            "preconditions": [
                {"register": "IWDG_KR", "whole_register": true, "state": "equals", "values": ["0x5555"], "established_by": "software", "action_operation": "write"},
                {"register": "IWDG_SR", "field": "PVU", "state": "cleared", "established_by": "hardware"}
            ],
            "postconditions": [],
            "severity": "error",
            "consequence": "The write to IWDG_PR is ignored while the register is protected or a prescaler update is ongoing",
            "datasheet_text": "Write access to the IWDG_PR and IWDG_RLR registers is protected. To modify them, first write the code 0x5555 in the IWDG_KR register. PVU bit of IWDG_SR must be reset in order to be able to change the prescaler divider."
        }
    ]
    ```

    CONSTRAINT EXAMPLE 4 -- NEGATIVE: flag-acknowledge semantics emit nothing:
    Datasheet text about WWDG_SR bit EWIF: "This bit is set by hardware when the counter has reached the value 0x40. It must be cleared by software by writing '0'. A write of '1' has no effect."
    This describes HOW a status flag is set by hardware and acknowledged by software (write-to-clear semantics). It is not an access or ordering requirement on the register.
    Emits: nothing -- access_constraints_v2 stays [].
"""


stm_datasheet_batched_example = """
--- BATCHED EXAMPLE ---
# INPUT

## PERIPHERAL NAME
    Peripheral name: BKP

## REGISTERS TO EXTRACT
    - BKP_DR1
    - BKP_DR2
    - BKP_CR
    - BKP_CSR
    - BKP_DR35

## DATASHEET INPUT
    **6.4.1** **Backup data registers (BKP_DRx)**
    **(x = 1..10)**

    Address offset: 0x04 + (x - 1) * 0x04, x = 1..10

    Reset value: 0x0000 0000

    |15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|
    |---|
    |D[15:0]|
    |rw|

    Bits 15:0 **D[15:0]**: Backup data
    These bits can be written by the application and are only cleared by a tamper event or a Backup domain reset.

    **6.4.4** **Backup control register (BKP_CR)**

    Address offset: 0x30

    Reset value: 0x0000 0000

    |15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|
    |---|---|
    |Reserved|TPE|
    |Reserved|rw|

    Bit 0 **TPE**: TAMPER pin enable
    0: The TAMPER pin is free for GPIO alternate function
    1: Enables the tamper detection on the TAMPER pin

    **6.4.5** **Backup control/status register (BKP_CSR)**

    Address offset: 0x34

    Reset value: 0x0000 0000

    |15 14 13 12 11 10|9|8|7 6 5 4 3|2|1|0|
    |---|---|---|---|---|---|---|
    |Reserved|TIF|TEF|Reserved|TPIE|CTI|CTE|
    |Reserved|r|r|Reserved|rw|w|w|

    Bit 9 **TIF**: Tamper interrupt flag
    This bit is set by hardware when a tamper event is detected and the TPIE bit is set.
    It is cleared by writing 1 to the CTI bit.
    1: A tamper interrupt occurred

    Bit 8 **TEF**: Tamper event flag
    This bit is set by hardware when a tamper event is detected.
    It is cleared by writing 1 to the CTE bit.
    1: A tamper event has been detected

    Bit 2 **TPIE**: TAMPER pin interrupt enable
    0: Tamper interrupt disabled
    1: Tamper interrupt enabled (the TIF bit will set an interrupt)

    Bit 1 **CTI**: Clear tamper interrupt
    0: No effect
    1: Clear the tamper interrupt and the TIF tamper interrupt flag

    Bit 0 **CTE**: Clear tamper event
    0: No effect
    1: Reset the TEF tamper event flag (and the tamper detector)

# OUTPUT
    I need to extract information for 5 registers: BKP_DR1, BKP_DR2, BKP_CR, BKP_CSR, and BKP_DR35.

    **BKP_DR1**: The datasheet shows BKP_DRx where x = 1..10. Since x=1 is within the range, BKP_DR1 is valid.
    The address offset is a formula: 0x04 + (x-1)*0x04. I need to use calculate_address_offset for x=1.
    Reset value is 0x00000000. Size is 16 bits. It has one subfield D[15:0] that is read-write.

    **BKP_DR2**: Same register family BKP_DRx, x=2 is within range. I need calculate_address_offset for x=2.
    Reset value is 0x00000000. Size is 16 bits. Same subfield D[15:0] that is read-write.

    **BKP_CR**: The datasheet shows BKP_CR at offset 0x30. Reset value is 0x00000000. Size is 16 bits.
    It has one subfield TPE at bit 0 that is read-write.

    **BKP_CSR**: The datasheet shows BKP_CSR at offset 0x34. Reset value is 0x00000000. Size is 16 bits.
    It has 5 subfields: TIF (bit 9, read-only), TEF (bit 8, read-only), TPIE (bit 2, read-write),
    CTI (bit 1, write-only), CTE (bit 0, write-only). I must include all 5 subfields.

    **BKP_DR35**: The datasheet shows BKP_DRx only for x = 1..10, and even with the extended range
    (DR11..DR42), there is no DR35 in the range visible here. No information found.

    ```function_call
    { "function_calls": [
        {
            "name": "calculate_address_offset",
            "parameters": {
                "base_address_in_hex": "0x04",
                "start_register_number": 1,
                "register_number": 1,
                "register_size_in_bytes": 4
            }
        },
        {
            "name": "calculate_address_offset",
            "parameters": {
                "base_address_in_hex": "0x04",
                "start_register_number": 1,
                "register_number": 2,
                "register_size_in_bytes": 4
            }
        }
    ]}
    ```

    ```json
    [
        {
            "register_name": "BKP_DR1",
            "datasheet_register_abbreviation": "BKP_DR1",
            "address_offset": "0x04",
            "reset_value": "0x00000000",
            "size": 16,
            "subfields": [
                {
                    "name": "D",
                    "description": "Backup data",
                    "access": "read-write",
                    "bit_number": {
                        "start_bit": 0,
                        "end_bit": 15
                    }
                }
            ],
            "access_constraints_v2": []
        },
        {
            "register_name": "BKP_DR2",
            "datasheet_register_abbreviation": "BKP_DR2",
            "address_offset": "0x08",
            "reset_value": "0x00000000",
            "size": 16,
            "subfields": [
                {
                    "name": "D",
                    "description": "Backup data",
                    "access": "read-write",
                    "bit_number": {
                        "start_bit": 0,
                        "end_bit": 15
                    }
                }
            ],
            "access_constraints_v2": []
        },
        {
            "register_name": "BKP_CR",
            "datasheet_register_abbreviation": "BKP_CR",
            "address_offset": "0x30",
            "reset_value": "0x00000000",
            "size": 16,
            "subfields": [
                {
                    "name": "TPE",
                    "description": "TAMPER pin enable",
                    "access": "read-write",
                    "bit_number": {
                        "start_bit": 0,
                        "end_bit": 0
                    }
                }
            ],
            "access_constraints_v2": []
        },
        {
            "register_name": "BKP_CSR",
            "datasheet_register_abbreviation": "BKP_CSR",
            "address_offset": "0x34",
            "reset_value": "0x00000000",
            "size": 16,
            "subfields": [
                {
                    "name": "CTE",
                    "description": "Clear tamper event",
                    "access": "write-only",
                    "bit_number": {
                        "start_bit": 0,
                        "end_bit": 0
                    }
                },
                {
                    "name": "CTI",
                    "description": "Clear tamper interrupt",
                    "access": "write-only",
                    "bit_number": {
                        "start_bit": 1,
                        "end_bit": 1
                    }
                },
                {
                    "name": "TPIE",
                    "description": "TAMPER pin interrupt enable",
                    "access": "read-write",
                    "bit_number": {
                        "start_bit": 2,
                        "end_bit": 2
                    }
                },
                {
                    "name": "TEF",
                    "description": "Tamper event flag",
                    "access": "read-only",
                    "bit_number": {
                        "start_bit": 8,
                        "end_bit": 8
                    }
                },
                {
                    "name": "TIF",
                    "description": "Tamper interrupt flag",
                    "access": "read-only",
                    "bit_number": {
                        "start_bit": 9,
                        "end_bit": 9
                    }
                }
            ],
            "access_constraints_v2": []
        },
        {
            "register_name": "BKP_DR35",
            "datasheet_register_abbreviation": null,
            "address_offset": null,
            "reset_value": null,
            "size": null,
            "subfields": null,
            "access_constraints_v2": null
        }
    ]
    ```
"""

stm_datasheet_batched_example_no_reasoning = """
--- BATCHED EXAMPLE ---
# INPUT

## PERIPHERAL NAME
    Peripheral name: BKP

## REGISTERS TO EXTRACT
    - BKP_DR1
    - BKP_DR2
    - BKP_CR
    - BKP_CSR
    - BKP_DR35

## DATASHEET INPUT
    **6.4.1** **Backup data registers (BKP_DRx)**
    **(x = 1..10)**

    Address offset: 0x04 + (x - 1) * 0x04, x = 1..10

    Reset value: 0x0000 0000

    |15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|
    |---|
    |D[15:0]|
    |rw|

    Bits 15:0 **D[15:0]**: Backup data
    These bits can be written by the application and are only cleared by a tamper event or a Backup domain reset.

    **6.4.4** **Backup control register (BKP_CR)**

    Address offset: 0x30

    Reset value: 0x0000 0000

    |15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0|
    |---|---|
    |Reserved|TPE|
    |Reserved|rw|

    Bit 0 **TPE**: TAMPER pin enable
    0: The TAMPER pin is free for GPIO alternate function
    1: Enables the tamper detection on the TAMPER pin

    **6.4.5** **Backup control/status register (BKP_CSR)**

    Address offset: 0x34

    Reset value: 0x0000 0000

    |15 14 13 12 11 10|9|8|7 6 5 4 3|2|1|0|
    |---|---|---|---|---|---|---|
    |Reserved|TIF|TEF|Reserved|TPIE|CTI|CTE|
    |Reserved|r|r|Reserved|rw|w|w|

    Bit 9 **TIF**: Tamper interrupt flag
    This bit is set by hardware when a tamper event is detected and the TPIE bit is set.
    It is cleared by writing 1 to the CTI bit.
    1: A tamper interrupt occurred

    Bit 8 **TEF**: Tamper event flag
    This bit is set by hardware when a tamper event is detected.
    It is cleared by writing 1 to the CTE bit.
    1: A tamper event has been detected

    Bit 2 **TPIE**: TAMPER pin interrupt enable
    0: Tamper interrupt disabled
    1: Tamper interrupt enabled (the TIF bit will set an interrupt)

    Bit 1 **CTI**: Clear tamper interrupt
    0: No effect
    1: Clear the tamper interrupt and the TIF tamper interrupt flag

    Bit 0 **CTE**: Clear tamper event
    0: No effect
    1: Reset the TEF tamper event flag (and the tamper detector)

# OUTPUT
    ```function_call
    { "function_calls": [
        {
            "name": "calculate_address_offset",
            "parameters": {
                "base_address_in_hex": "0x04",
                "start_register_number": 1,
                "register_number": 1,
                "register_size_in_bytes": 4
            }
        },
        {
            "name": "calculate_address_offset",
            "parameters": {
                "base_address_in_hex": "0x04",
                "start_register_number": 1,
                "register_number": 2,
                "register_size_in_bytes": 4
            }
        }
    ]}
    ```

    ```json
    [
        {
            "register_name": "BKP_DR1",
            "datasheet_register_abbreviation": "BKP_DR1",
            "address_offset": "0x04",
            "reset_value": "0x00000000",
            "size": 16,
            "subfields": [
                {
                    "name": "D",
                    "description": "Backup data",
                    "access": "read-write",
                    "bit_number": {
                        "start_bit": 0,
                        "end_bit": 15
                    }
                }
            ],
            "access_constraints_v2": []
        },
        {
            "register_name": "BKP_DR2",
            "datasheet_register_abbreviation": "BKP_DR2",
            "address_offset": "0x08",
            "reset_value": "0x00000000",
            "size": 16,
            "subfields": [
                {
                    "name": "D",
                    "description": "Backup data",
                    "access": "read-write",
                    "bit_number": {
                        "start_bit": 0,
                        "end_bit": 15
                    }
                }
            ],
            "access_constraints_v2": []
        },
        {
            "register_name": "BKP_CR",
            "datasheet_register_abbreviation": "BKP_CR",
            "address_offset": "0x30",
            "reset_value": "0x00000000",
            "size": 16,
            "subfields": [
                {
                    "name": "TPE",
                    "description": "TAMPER pin enable",
                    "access": "read-write",
                    "bit_number": {
                        "start_bit": 0,
                        "end_bit": 0
                    }
                }
            ],
            "access_constraints_v2": []
        },
        {
            "register_name": "BKP_CSR",
            "datasheet_register_abbreviation": "BKP_CSR",
            "address_offset": "0x34",
            "reset_value": "0x00000000",
            "size": 16,
            "subfields": [
                {
                    "name": "CTE",
                    "description": "Clear tamper event",
                    "access": "write-only",
                    "bit_number": {
                        "start_bit": 0,
                        "end_bit": 0
                    }
                },
                {
                    "name": "CTI",
                    "description": "Clear tamper interrupt",
                    "access": "write-only",
                    "bit_number": {
                        "start_bit": 1,
                        "end_bit": 1
                    }
                },
                {
                    "name": "TPIE",
                    "description": "TAMPER pin interrupt enable",
                    "access": "read-write",
                    "bit_number": {
                        "start_bit": 2,
                        "end_bit": 2
                    }
                },
                {
                    "name": "TEF",
                    "description": "Tamper event flag",
                    "access": "read-only",
                    "bit_number": {
                        "start_bit": 8,
                        "end_bit": 8
                    }
                },
                {
                    "name": "TIF",
                    "description": "Tamper interrupt flag",
                    "access": "read-only",
                    "bit_number": {
                        "start_bit": 9,
                        "end_bit": 9
                    }
                }
            ],
            "access_constraints_v2": []
        },
        {
            "register_name": "BKP_DR35",
            "datasheet_register_abbreviation": null,
            "address_offset": null,
            "reset_value": null,
            "size": null,
            "subfields": null,
            "access_constraints_v2": null
        }
    ]
    ```
"""