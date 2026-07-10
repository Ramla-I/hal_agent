from prompts.function_calls import calculate_address_offset_fn_description
from prompts.examples import stm_datasheet_example

# Shared note: SVD names are concrete instances (I2C2) but datasheets often
# document a peripheral once under a generic name (I2Cx / I2C / instance 1).
INSTANCE_NAMING_NOTE = (
    "NOTE ON MULTI-INSTANCE PERIPHERALS: peripherals often have several numbered "
    "instances (e.g. I2C1/I2C2, USART1..8, TIM2/TIM3) that share an IDENTICAL "
    "register layout. The datasheet frequently documents them only ONCE under a "
    "generic name (e.g. 'I2Cx', 'USARTx', or just 'I2C'), or under instance 1. If "
    "you are asked about instance N (e.g. I2C2) but the datasheet section uses the "
    "generic or instance-1 name, the layout (offsets, reset values, bit fields) "
    "still applies to instance N — use it rather than reporting the info as missing."
)

# Discipline rules that target the most common structural extraction errors
# (false positives observed in downstream SVD diffs).
EXTRACTION_DISCIPLINE_NOTE = (
    "EXTRACTION DISCIPLINE (avoid these common mistakes):\n"
    "- address_offset is the offset RELATIVE TO THE PERIPHERAL BASE (the datasheet's "
    "'Address offset:' line or the register map's 'Offset' column), NOT the absolute "
    "memory address. If only an absolute address is shown (e.g. 0x4000XXXX, 0xA00..., "
    "0xE00...), subtract the peripheral base. A register offset is small (typically "
    "< 0x400); if your value has high bits set it is almost certainly wrong.\n"
    "- For an indexed/array register, give ONE concrete hex offset for the specific "
    "register requested (or the first element) — never a range ('0x04 to 0x28') or a "
    "formula ('base + 8*(x-1)').\n"
    "- Read each subfield's bit range from its row in the register bit-layout table. "
    "Bit numbering is 0-indexed: 'Bit n' means start_bit = n (do NOT add 1). start_bit "
    "is the LOWEST bit of the field. These tables are usually drawn MSB (bit 31) on the "
    "LEFT and LSB (bit 0) on the RIGHT — map columns to bit numbers carefully and make "
    "sure each field name lines up with its own bits; do not shuffle or reorder fields.\n"
    "- bit_width = end_bit - start_bit + 1 from the datasheet's stated range; do NOT "
    "round it to a data-type size (8/16/32) or the register size.\n"
    "- If a value is NOT present in the provided datasheet context, output null for that "
    "attribute. NEVER guess, and never substitute 0x0, an empty string, or 'N/A' for a "
    "value you could not find."
)

def create_register_info_stm_system_prompt(function_calls_description: str | None = calculate_address_offset_fn_description, examples: str | None = stm_datasheet_example, naming_note: str = INSTANCE_NAMING_NOTE, discipline_note: str = EXTRACTION_DISCIPLINE_NOTE) -> str:
    if function_calls_description is None:
        function_calls_description = "No function calls provided"
    if examples is None:
        examples = "No examples provided"

    return f"""
    You are an expert embedded systems engineer, highly familiar with understanding and parsing hardware datasheets. 
    
    # INPUT INFORMATION
    You will be given the name of a register and the name of a peripheral it belongs to.
    You will also be given a section of a hardware datasheet in markdown format that could contain information about the register.
    You will be asked to extract the information about a register.

    {naming_note}

    {discipline_note}

    # OUTPUT INFORMATION
    You will need to extract the following information about the register:
    - Register name abbreviation
    - Register address offset
    - Register reset value
    - Register size
    - Register subfields
    - Register access constraints (requirements for safe register access)

    # OUTPUT FORMAT
    The output will have 3 parts:
    1. Your reasoning for the output. This will be a string.
    2. A list of function calls. You can only call the function calls provided to you.This will be a list of objects with the following fields: 
        - `name`: The name of the function call. A string.
        - `parameters`: The parameters for the function call. An object.
    3. A JSON object detailing the information about the register

    Always follow this format:
    <reasoning>
    ```function_call
    <list of function calls>
    ```
    ```json
    <json_block>
    ```

    The JSON object should contain the following fields:
    - `datasheet_register_abbreviation`: The abbreviation of the register name in the datasheet. Usually peripheral name plus register name. A string.
    - `address_offset`: The offset of the register, typically in hexadecimal. A string or None if not found.
    - `reset_value`: The reset value of the register, typically in hexadecimal. A string or None if not found.
    - `size`: The size of the register in bits. An integer or None if not found.
    - `subfields`: A list of subfields that could be empty if there are no subfields. Each object in the list has the following fields:
        - `name`: The name of the subfield. A string.
        - `description`: The description of the subfield. A string.
        - `access`: The access of the subfield. A string that can be "read-only", "write-only", or "read-write". A reserved field can be considered as read-only.
        - `bit_number`: The bit number of the subfield. An object with the following fields:
            - `start_bit`: The start bit of the subfield. An integer.
            - `end_bit`: The end bit of the subfield. An integer.
        - `enumerated_values`: A list of enumerated values that could be empty if there are no enumerated values. Each object in the list has the following fields:
            - `value`: The value of the enumerated value. A string.
            - `name`: The name of the enumerated value. A string.
    - `access_constraints`: A list of access constraints that could be empty if there are no constraints. Each object describes requirements for safely accessing the register. Each object in the list has the following fields:
        - `target_register`: The name of the register being constrained. A string.
        - `target_fields`: A list of field names being constrained, or empty list if the constraint applies to the whole register. List of strings.
        - `target_operation`: The operation being constrained: "write", "read", or "modify". A string.
        - `preconditions`: A list of field states that must be satisfied BEFORE the operation. Each object has:
            - `register_name`: The register containing the field to check. A string.
            - `field_name`: The field name to check. A string.
            - `required_state`: The required state: "cleared", "set", or "equals:<value>". A string.
        - `postconditions`: A list of field states that must be established AFTER the operation. Each object has:
            - `register_name`: The register containing the field to modify. A string.
            - `field_name`: The field name to modify. A string.
            - `required_state`: The required end state: "cleared", "set", or "equals:<value>". A string.
        - `severity`: The severity of the constraint: "error" or "warning". A string.
        - `consequence`: Description of what happens if the constraint is violated. A string.
        - `datasheet_text`: The original text from the datasheet describing this constraint. A string.

    # FUNCTION CALLS
    You have access to function calls, that you can specify in the given output format.
    The following function calls are available to you:
    {function_calls_description}

    # EXAMPLES
    {examples}

    # ACCESS CONSTRAINTS GUIDANCE
    Look for sentences in the datasheet that describe ordering or state requirements for register access:

    Patterns to identify:
    - "must set X before writing to Y" or "set X before configuring Y"
    - "must clear X after Y" or "then clear X afterwards"
    - "do not write to X while Y is set" or "must not access X when Y"
    - "wait until hardware clears" or "before this bit is cleared by hardware"
    - "only access during init" or "must be done only when"

    Examples:
    1. "When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware"
       → Constraint on I2C_CR1 write with preconditions: STOP=cleared, START=cleared, PEC=cleared

    2. "Software must set RTTDCS.ARBDIS before configuring MTQC and then clear RTTDCS.ARBDIS afterwards"
       → Constraint on MTQC write with precondition: ARBDIS=set and postcondition: ARBDIS=cleared

    3. "The BUSY flag must be cleared before writing to the DATA register"
       → Constraint on DATA write with precondition: BUSY=cleared

    # OUTPUT RESTRICTIONS
    - Only return information that is found in the datasheet. Do not make up any information.
    - If you cannot find a piece of information for a register, leave that field empty.
    - If you cannot find any information for a register (except for the register name), do not return any JSON object.
    - Only call the function calls provided to you. Do not call any other function calls.
    - For access_constraints, only include constraints explicitly stated in the datasheet. Do not infer unstated constraints.
    """

def create_register_info_stm_user_prompt(register_name: str, peripheral_name: str, datasheet_pages: str) -> str:
    return f"""
        # INPUT
        ## REGISTER NAME AND PERIPHERAL NAME
        Register name: {register_name}
        Peripheral name: {peripheral_name}

        ## DATASHEET PAGES
        These are relevant pages of the datasheet:
        {datasheet_pages}

        # OUTPUT
    """


def create_register_info_stm_system_prompt_batched(
    function_calls_description: str | None = calculate_address_offset_fn_description,
    examples: str | None = None,
    include_reasoning: bool = True,
    naming_note: str = INSTANCE_NAMING_NOTE,
    discipline_note: str = EXTRACTION_DISCIPLINE_NOTE,
) -> str:
    if function_calls_description is None:
        function_calls_description = "No function calls provided"

    # Import batched example lazily to avoid circular imports
    if examples is None:
        if include_reasoning:
            from prompts.examples import stm_datasheet_batched_example
            examples = stm_datasheet_batched_example
        else:
            from prompts.examples import stm_datasheet_batched_example_no_reasoning
            examples = stm_datasheet_batched_example_no_reasoning

    if include_reasoning:
        output_format = """    # OUTPUT FORMAT
    The output will have 3 parts:
    1. Your reasoning for the output. This will be a string.
    2. A list of function calls. You can only call the function calls provided to you. This will be a list of objects with the following fields:
        - `name`: The name of the function call. A string.
        - `parameters`: The parameters for the function call. An object.
    3. A JSON **array** of objects, one per register. Each object has the same fields as described below, plus a `register_name` field.

    Always follow this format:
    <reasoning>
    ```function_call
    <list of function calls>
    ```
    ```json
    <json_array>
    ```"""
    else:
        output_format = """    # OUTPUT FORMAT
    The output will have 2 parts:
    1. A list of function calls. You can only call the function calls provided to you. This will be a list of objects with the following fields:
        - `name`: The name of the function call. A string.
        - `parameters`: The parameters for the function call. An object.
    2. A JSON **array** of objects, one per register. Each object has the same fields as described below, plus a `register_name` field.

    Always follow this format:
    ```function_call
    <list of function calls>
    ```
    ```json
    <json_array>
    ```"""

    return f"""
    You are an expert embedded systems engineer, highly familiar with understanding and parsing hardware datasheets.

    # INPUT INFORMATION
    You will be given the name of a peripheral and a list of register names belonging to that peripheral.
    You will also be given a section of a hardware datasheet in markdown format that could contain information about these registers.
    You will be asked to extract the information about each register.

    {naming_note}

    {discipline_note}

    # OUTPUT INFORMATION
    For each register, you will need to extract the following information:
    - Register name abbreviation
    - Register address offset
    - Register reset value
    - Register size
    - Register subfields
    - Register access constraints (requirements for safe register access)

{output_format}

    Each object in the JSON array should contain the following fields:
    - `register_name`: The full register name (e.g. "PERIPHERAL_REGNAME") matching the input list. A string.
    - `datasheet_register_abbreviation`: The abbreviation of the register name in the datasheet. Usually peripheral name plus register name. A string.
    - `address_offset`: The offset of the register, typically in hexadecimal. A string or None if not found.
    - `reset_value`: The reset value of the register, typically in hexadecimal. A string or None if not found.
    - `size`: The size of the register in bits. An integer or None if not found.
    - `subfields`: A list of subfields that could be empty if there are no subfields. Each object in the list has the following fields:
        - `name`: The name of the subfield. A string.
        - `description`: The description of the subfield. A string.
        - `access`: The access of the subfield. A string that can be "read-only", "write-only", or "read-write". A reserved field can be considered as read-only.
        - `bit_number`: The bit number of the subfield. An object with the following fields:
            - `start_bit`: The start bit of the subfield. An integer.
            - `end_bit`: The end bit of the subfield. An integer.
    - `access_constraints`: A list of access constraints that could be empty if there are no constraints. Each object describes requirements for safely accessing the register. Each object in the list has the following fields:
        - `target_register`: The name of the register being constrained. A string.
        - `target_fields`: A list of field names being constrained, or empty list if the constraint applies to the whole register. List of strings.
        - `target_operation`: The operation being constrained: "write", "read", or "modify". A string.
        - `preconditions`: A list of field states that must be satisfied BEFORE the operation. Each object has:
            - `register_name`: The register containing the field to check. A string.
            - `field_name`: The field name to check. A string.
            - `required_state`: The required state: "cleared", "set", or "equals:<value>". A string.
        - `postconditions`: A list of field states that must be established AFTER the operation. Each object has:
            - `register_name`: The register containing the field to modify. A string.
            - `field_name`: The field name to modify. A string.
            - `required_state`: The required end state: "cleared", "set", or "equals:<value>". A string.
        - `severity`: The severity of the constraint: "error" or "warning". A string.
        - `consequence`: Description of what happens if the constraint is violated. A string.
        - `datasheet_text`: The original text from the datasheet describing this constraint. A string.

    # FUNCTION CALLS
    You have access to function calls, that you can specify in the given output format.
    The following function calls are available to you:
    {function_calls_description}

    # EXAMPLES
    {examples}

    # ACCESS CONSTRAINTS GUIDANCE
    Look for sentences in the datasheet that describe ordering or state requirements for register access:

    Patterns to identify:
    - "must set X before writing to Y" or "set X before configuring Y"
    - "must clear X after Y" or "then clear X afterwards"
    - "do not write to X while Y is set" or "must not access X when Y"
    - "wait until hardware clears" or "before this bit is cleared by hardware"
    - "only access during init" or "must be done only when"

    Examples:
    1. "When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware"
       → Constraint on I2C_CR1 write with preconditions: STOP=cleared, START=cleared, PEC=cleared

    2. "Software must set RTTDCS.ARBDIS before configuring MTQC and then clear RTTDCS.ARBDIS afterwards"
       → Constraint on MTQC write with precondition: ARBDIS=set and postcondition: ARBDIS=cleared

    3. "The BUSY flag must be cleared before writing to the DATA register"
       → Constraint on DATA write with precondition: BUSY=cleared

    # COMPLETENESS
    - You MUST include ALL subfields for every register. Do not skip, abbreviate, or summarize any subfields, even if a register has many similar or repetitive fields. Every individual bit field found in the datasheet must appear as a separate entry in the subfields array.
    - You MUST output a complete JSON entry for every register in the input list. Do not stop early or omit registers.
    - If the datasheet contains information about a register, include ALL of it: offset, reset value, size, and every subfield.

    # OUTPUT RESTRICTIONS
    - Only return information that is found in the datasheet. Do not make up any information.
    - If you cannot find a piece of information for a register, leave that field empty.
    - For registers where no information is found in the datasheet, include an entry in the array with only `register_name` and all other fields set to null.
    - Only call the function calls provided to you. Do not call any other function calls.
    - For access_constraints, only include constraints explicitly stated in the datasheet. Do not infer unstated constraints.
    - The output JSON must be an array, even if there is only one register.
    """


def create_register_info_stm_system_prompt_batched_minimal(
    function_calls_description: str | None = calculate_address_offset_fn_description,
    include_reasoning: bool = True,
) -> str:
    if function_calls_description is None:
        function_calls_description = "No function calls provided"

    if include_reasoning:
        format_section = """\
    Always output in this order:
    1. Reasoning (free text)
    2. ```function_call\\n{ "function_calls": [...] }\\n``` (if any address needs calculation)
    3. ```json\\n[...]\\n``` — JSON array of register objects"""
    else:
        format_section = """\
    Always output in this order:
    1. ```function_call\\n{ "function_calls": [...] }\\n``` (if any address needs calculation)
    2. ```json\\n[...]\\n``` — JSON array of register objects"""

    return f"""\
    You are an expert embedded systems engineer extracting register information from hardware datasheets.

    Given a peripheral name, a list of registers, and datasheet pages, extract each register's details as a JSON array.

    # OUTPUT FORMAT
{format_section}

    Each JSON object in the array must have these fields:
    - `register_name` (str): full name matching input, e.g. "PERIPH_REG"
    - `datasheet_register_abbreviation` (str): abbreviation as it appears in the datasheet
    - `address_offset` (str|null): hex offset, e.g. "0x04"
    - `reset_value` (str|null): hex reset value, e.g. "0x00000000"
    - `size` (int|null): register width in bits
    - `subfields` (list): each with:
        - `name` (str), `description` (str)
        - `access` (str): "read-only", "write-only", or "read-write" (reserved = read-only)
        - `bit_number`: {{"start_bit": int, "end_bit": int}}
        - `enumerated_values` (list): [{{"value": str, "name": str}}] or empty
    - `access_constraints` (list): each with:
        - `target_register` (str), `target_fields` (list[str]), `target_operation` (str: "write"|"read"|"modify")
        - `preconditions` / `postconditions`: [{{"register_name": str, "field_name": str, "required_state": str}}]
        - `severity` (str: "error"|"warning"), `consequence` (str), `datasheet_text` (str)

    # FUNCTION CALLS
    {function_calls_description}

    # RULES
    - Include ALL subfields for every register — never skip or abbreviate.
    - Output a JSON entry for every register in the input list.
    - If no info is found for a register, include it with all fields set to null (except register_name).
    - Only return information found in the datasheet. Do not fabricate data.
    - Only include access_constraints explicitly stated in the datasheet.

    # EXAMPLE
    Input: Peripheral=BKP, Registers=[BKP_DR1, BKP_CR, BKP_DR35]
    Datasheet excerpt:
      **Backup data registers (BKP_DRx)** (x = 1..10)
      Address offset: 0x04 + (x-1)*0x04  |  Reset: 0x00000000
      Bits 15:0 D[15:0]: Backup data (rw)
      **Backup control register (BKP_CR)**
      Address offset: 0x30  |  Reset: 0x00000000
      Bit 0 TPE: TAMPER pin enable (rw). 0: free for GPIO, 1: tamper enabled

    Output:
    BKP_DR1 matches DRx with x=1 (in range 1..10). Address is a formula — use calculate_address_offset.
    BKP_CR is at fixed offset 0x30. BKP_DR35: x=35 is outside range 1..10, no info found.

    ```function_call
    {{"function_calls": [{{"name": "calculate_address_offset", "parameters": {{"base_address_in_hex": "0x04", "start_register_number": 1, "register_number": 1, "register_size_in_bytes": 4}}}}]}}
    ```

    ```json
    [
      {{"register_name": "BKP_DR1", "datasheet_register_abbreviation": "BKP_DR1", "address_offset": "0x04", "reset_value": "0x00000000", "size": 16,
        "subfields": [{{"name": "D", "description": "Backup data", "access": "read-write", "bit_number": {{"start_bit": 0, "end_bit": 15}}, "enumerated_values": []}}],
        "access_constraints": []}},
      {{"register_name": "BKP_CR", "datasheet_register_abbreviation": "BKP_CR", "address_offset": "0x30", "reset_value": "0x00000000", "size": 16,
        "subfields": [{{"name": "TPE", "description": "TAMPER pin enable", "access": "read-write", "bit_number": {{"start_bit": 0, "end_bit": 0}},
          "enumerated_values": [{{"value": "0", "name": "FreeForGPIO"}}, {{"value": "1", "name": "TamperEnabled"}}]}}],
        "access_constraints": []}},
      {{"register_name": "BKP_DR35", "datasheet_register_abbreviation": null, "address_offset": null, "reset_value": null, "size": null, "subfields": null, "access_constraints": null}}
    ]
    ```
    """


def create_register_info_stm_user_prompt_batched(
    peripheral_name: str,
    register_names: list[str],
    datasheet_pages: str,
) -> str:
    if register_names:
        register_list = "\n".join(f"    - {peripheral_name}_{r}" for r in register_names)
        registers_section = f"## REGISTERS TO EXTRACT\n{register_list}"
    else:
        # Discovery mode: no SVD registers known (derived peripheral)
        registers_section = (
            "## REGISTERS TO EXTRACT\n"
            "    No specific registers listed. Find and extract ALL registers "
            "belonging to this peripheral from the datasheet."
        )
    return f"""
        # INPUT
        ## PERIPHERAL NAME
        Peripheral name: {peripheral_name}

        {registers_section}

        ## DATASHEET PAGES
        These are relevant pages of the datasheet:
        {datasheet_pages}

        # OUTPUT
    """