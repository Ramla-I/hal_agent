from prompts.function_calls import calculate_address_offset_fn_description
from prompts.examples import stm_datasheet_example, stm_access_constraints_v2_examples

# ---------------------------------------------------------------------------
# Access-constraint grammar v2: the SINGLE authoritative prompt text.
#
# ACCESS_CONSTRAINTS_V2_SCHEMA and ACCESS_CONSTRAINTS_V2_GUIDANCE are shared
# VERBATIM by all three generator system-prompt builders below and by the
# constraints-only prompt used by the extraction eval
# (optimization/generator/extraction_eval_v2.py), so the eval always tests
# exactly the text that ships. The normative schema is defs.py (ConstraintV2)
# / docs/register_constraints_plan.md Appendix B;
# tests/test_prompt_schema_consistency.py checks prompt<->schema alignment.
#
# Deliberately provider-agnostic: schema enforcement is TIERED (plan section
# 6.1) -- this text always carries the compact schema and exemplars; token-
# level structured-output (json_schema) mode is a per-provider option that is
# NOT assumed here (Groq OSS models hard-error on it); the guarantee layer is
# collection-time pydantic parsing with per-constraint recovery.
# ---------------------------------------------------------------------------

ACCESS_CONSTRAINTS_V2_SCHEMA = """\
    - `schema_version`: The constraint grammar version. Always the integer 2.
    - `access_constraints_v2`: A list of access-constraint objects; empty if the datasheet states no access or ordering requirement for the register. Every object carries this shared envelope:
        - `kind`: Which constraint schema the object uses: "state_gate", "sequence", "write_once", "delay", "read_effect", "clock_gate", "value_relation", or "other". A string.
        - `severity`: "error" (a violation corrupts state or the operation is ignored) or "warning" (degraded or unreliable behavior). A string.
        - `consequence`: What happens if the constraint is violated. A string.
        - `datasheet_text`: The VERBATIM datasheet text stating the requirement, COMPLETE: if the requirement spans several sentences, quote every one of them, unmodified. A string.

      Kind "state_gate" -- an operation on this register is only permitted while named field conditions hold (the most common kind). Additional fields:
        - `target_register`: The register being constrained; must be the register being extracted. A string.
        - `target_fields`: The constrained field names, or [] when the whole register is constrained. A list of strings.
        - `target_operation`: The bus operation the datasheet constrains: "read", "write", or "any" ("any" = both read and write). A string. Note: datasheets say "modify / modified / change a register" to mean WRITING it, so encode those as "write" -- there is no "modify" target here. A read-modify-write is just a read plus a write and needs no special value.
        - `preconditions`: Conditions that must ALL hold before the operation. A list of condition objects.
        - `postconditions`: Actions software must perform after the operation (every entry must have "established_by": "software"). A list of condition objects.
        Each condition object has:
        - `register`: The register holding the condition, SVD-canonical name. A string.
        - `field`: The field checked, SVD-canonical name. A string. When the condition is about a whole register's value (e.g. a key register), omit `field` and set `whole_register` to true instead; never use "".
        - `whole_register`: true only for whole-register conditions. A boolean, default false.
        - `state`: "cleared", "set", or "equals". A string.
        - `values`: Only with state "equals": one or more required numeric values; several values mean any one of them satisfies the condition. Numeric literals only, as hex ("0x5555"), binary ("0b01"), or decimal ("3") strings. A list.
        - `established_by`: "hardware" or "software" -- who brings the state about (see the guidance). A string.
        - `action_operation`: How the driver PERFORMS the establishing action -- "modify" (read-modify-write: change only the needed bits and keep the register's other bits) or "write" (compose a fresh value from the reset value, overwriting the register's other bits). Choose "modify" to set or clear a bit while preserving the register's other configured state (the usual case, e.g. clearing UE to disable a peripheral); choose "write" only when the datasheet prescribes writing a specific whole-register value (e.g. a key). Required exactly when established_by is "software"; omitted otherwise. Unlike `target_operation`, "modify" IS meaningful here: it names the method used to set up the precondition, not a constrained surface.

      The other kinds add these fields to the envelope:
        - Kind "sequence" (ordered multi-step protocol): `steps` -- at least 2 step objects, in order, each {"register": str, "operation": "write" or "read", "value": number or null}; optional `enables` -- what the completed sequence unlocks, as a plain reference: {"register": str, "field": str} or {"register": str, "whole_register": true} (a reference, never a step -- no "operation" or "value" keys).
        - Kind "write_once" (writable only once until reset): `target_register` (string), `target_fields` (list of strings), `reset_scope` -- "system_reset" or "power_cycle".
        - Kind "delay" (a required wait): `after` -- the step object that starts the wait; `duration` -- {"value": int, "unit": "cycles_ahb" | "cycles_apb" | "us" | "ms"}; optional `before` -- the dependent access, {"register": str, "field": str} or {"register": str, "whole_register": true}.
        - Kind "read_effect" (reading has side effects): `read_register` (string), `effects` -- a list of {"field": str, "becomes": "cleared" or "set"}.
        - Kind "clock_gate" (peripheral clock must be enabled before any register access): `clock` -- one condition object naming the clock-enable bit (normally state "set", established_by "software").
        - Kind "value_relation" (required value relationship between fields, no ordering or state): `fields` -- a list of {"register": str, "field": str}; the relation itself stays in datasheet_text.
        - Kind "other" (a genuine access/ordering requirement fitting no kind above): `description` -- the requirement in your own words (string); `involved` -- a list of {"register": str, "field": str} references."""


ACCESS_CONSTRAINTS_V2_GUIDANCE = f"""\
    Emit constraints ONLY for access or ordering requirements the datasheet states explicitly. Choose the kind with this decision tree, in order:
    1. The text prescribes an ordered multi-step protocol (write key A then key B; read X then read Y) -> "sequence". Never encode a sequence as an "equals" value such as "0xCA then 0x53".
    2. The text requires waiting a time or a number of clock cycles -> "delay".
    3. The peripheral clock must be enabled before any register access -> "clock_gate".
    4. A field or register may be written only once until the next reset -> "write_once".
    5. Reading the register clears or otherwise changes a flag -> "read_effect".
    6. An operation is only permitted while a field or register state holds -> "state_gate".
    7. Field values must relate in a required way, with no ordering or state involved -> "value_relation".
    8. A genuine access/ordering requirement that fits none of the kinds above -> "other".
    9. Not an access/ordering requirement at all -> emit NOTHING (see the DO-NOT-EMIT rules).

    `established_by` states who brings a condition's state about:
    - "hardware": hardware establishes the state and software can only observe it -- e.g. "before this bit is cleared by hardware", a busy or update flag the peripheral clears on its own.
    - "software": the driver itself must establish the state first -- e.g. disabling a peripheral (UE=0) or writing a key value; `action_operation` is then required and names HOW: "modify" (read-modify-write, changing the needed bits while preserving the register's other bits -- the usual choice, e.g. clearing one enable bit) or "write" (compose the whole register from its reset value, overwriting the other bits -- only when the datasheet prescribes a specific whole-register value such as a key).

    Operations: `target_operation` is "read", "write", or "any" only. A datasheet sentence about "modifying" or "changing" a register is a WRITE constraint -- encode it as "write". Never emit "modify" as a `target_operation`; a read-modify-write needs no special target (it is a read plus a write, and the enforcement handles it automatically).

    DO-NOT-EMIT rules -- the following are NOT access constraints; emit nothing for them:
    - Flag-acknowledge write semantics (w1c / rc_w): "This bit is set by hardware and cleared by software writing 1." -> nothing.
    - Read-to-clear behavior standing alone: "This flag is cleared by a read to this register." -> "read_effect" if the side effect matters to other software, otherwise nothing; never a read constraint.
    - Access-width notes: "The peripheral registers have to be accessed by half-words (16 bits) or words (32 bits)." -> nothing.
    - Secure or privileged access notes: "This register can only be accessed by privileged software." -> nothing.
    - Validity / don't-care notes: "This bit is valid only when EXTSEL is 0b111, otherwise it is don't care." -> nothing.
    - Reset behavior: "This bit is set and cleared by hardware after a system reset." -> nothing.

    Naming rules:
    - Use SVD-canonical register and field names, exactly as the datasheet's register description spells them (e.g. register "RTC_CRL", field "CNF").
    - Never use bit ranges ("LCK0-LCK15"), wildcards ("AES_KEYR*"), or invented pseudo-fields ("key", "mailbox_state"). For a condition on a whole register's value, set whole_register to true and omit the field.

    Values:
    - `values` entries are numeric literals only: hex "0x5555", binary "0b01", or decimal "3". Never words ("enabled"), never prose, never "X then Y" strings -- a multi-step protocol is a `sequence` with one step per operation.

    `datasheet_text` must be VERBATIM AND COMPLETE: quote every sentence the requirement spans, character for character. Do not paraphrase, abbreviate, or stitch fragments together. Quote CONTIGUOUS text only -- never join separated passages with ellipses ("..."); when separate passages state parts of the requirement, quote the contiguous sentence(s) stating the operative requirement.

    De-duplication: when one note constrains several bits of the same register in the same way, emit ONE constraint for that (register, operation) pair and list the bits in `target_fields` -- never one constraint per bit. Quote the recurring sentence ONCE in `datasheet_text`; never concatenate its per-bit repetitions.

{stm_access_constraints_v2_examples}"""


def create_register_info_stm_system_prompt(function_calls_description: str | None = calculate_address_offset_fn_description, examples: str | None = stm_datasheet_example) -> str:
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
{ACCESS_CONSTRAINTS_V2_SCHEMA}

    # FUNCTION CALLS
    You have access to function calls, that you can specify in the given output format.
    The following function calls are available to you:
    {function_calls_description}

    # EXAMPLES
    {examples}

    # ACCESS CONSTRAINTS GUIDANCE
{ACCESS_CONSTRAINTS_V2_GUIDANCE}

    # OUTPUT RESTRICTIONS
    - Only return information that is found in the datasheet. Do not make up any information.
    - If you cannot find a piece of information for a register, leave that field empty.
    - If you cannot find any information for a register (except for the register name), do not return any JSON object.
    - Only call the function calls provided to you. Do not call any other function calls.
    - For access_constraints_v2, only include constraints explicitly stated in the datasheet. Do not infer unstated constraints.
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
{ACCESS_CONSTRAINTS_V2_SCHEMA}

    # FUNCTION CALLS
    You have access to function calls, that you can specify in the given output format.
    The following function calls are available to you:
    {function_calls_description}

    # EXAMPLES
    {examples}

    # ACCESS CONSTRAINTS GUIDANCE
{ACCESS_CONSTRAINTS_V2_GUIDANCE}

    # COMPLETENESS
    - You MUST include ALL subfields for every register. Do not skip, abbreviate, or summarize any subfields, even if a register has many similar or repetitive fields. Every individual bit field found in the datasheet must appear as a separate entry in the subfields array.
    - You MUST output a complete JSON entry for every register in the input list. Do not stop early or omit registers.
    - If the datasheet contains information about a register, include ALL of it: offset, reset value, size, and every subfield.

    # OUTPUT RESTRICTIONS
    - Only return information that is found in the datasheet. Do not make up any information.
    - If you cannot find a piece of information for a register, leave that field empty.
    - For registers where no information is found in the datasheet, include an entry in the array with only `register_name` and all other fields set to null.
    - Only call the function calls provided to you. Do not call any other function calls.
    - For access_constraints_v2, only include constraints explicitly stated in the datasheet. Do not infer unstated constraints.
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
{ACCESS_CONSTRAINTS_V2_SCHEMA}

    # FUNCTION CALLS
    {function_calls_description}

    # ACCESS CONSTRAINTS GUIDANCE
{ACCESS_CONSTRAINTS_V2_GUIDANCE}

    # RULES
    - Include ALL subfields for every register — never skip or abbreviate.
    - Output a JSON entry for every register in the input list.
    - If no info is found for a register, include it with all fields set to null (except register_name).
    - Only return information found in the datasheet. Do not fabricate data.
    - Only include access_constraints_v2 explicitly stated in the datasheet.

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
        "access_constraints_v2": [], "schema_version": 2}},
      {{"register_name": "BKP_CR", "datasheet_register_abbreviation": "BKP_CR", "address_offset": "0x30", "reset_value": "0x00000000", "size": 16,
        "subfields": [{{"name": "TPE", "description": "TAMPER pin enable", "access": "read-write", "bit_number": {{"start_bit": 0, "end_bit": 0}},
          "enumerated_values": [{{"value": "0", "name": "FreeForGPIO"}}, {{"value": "1", "name": "TamperEnabled"}}]}}],
        "access_constraints_v2": [], "schema_version": 2}},
      {{"register_name": "BKP_DR35", "datasheet_register_abbreviation": null, "address_offset": null, "reset_value": null, "size": null, "subfields": null, "access_constraints_v2": null, "schema_version": 2}}
    ]
    ```
    """


def create_register_constraints_v2_system_prompt() -> str:
    """Constraints-only extraction prompt (grammar v2).

    Used by the extraction eval (optimization/generator/extraction_eval_v2.py)
    to isolate PROMPT quality from retrieval quality: it shares
    ACCESS_CONSTRAINTS_V2_SCHEMA and ACCESS_CONSTRAINTS_V2_GUIDANCE verbatim
    with the three generator system prompts above, so the eval exercises
    exactly the constraint text that ships, without the layout-extraction
    surface.
    """
    return f"""
    You are an expert embedded systems engineer, highly familiar with understanding and parsing hardware datasheets.

    # INPUT INFORMATION
    You will be given the name of a register, the name of the peripheral it belongs to, and pages of a hardware datasheet in markdown format that could contain information about the register.
    Extract ONLY the register's access constraints (requirements for safe register access). Ignore layout details (address offset, reset value, subfields).

    # OUTPUT FORMAT
    The output will have 2 parts:
    1. Your reasoning for the output. This will be a string.
    2. A single JSON object with the register name and its access constraints.

    Always follow this format:
    <reasoning>
    ```json
    {{"register_name": "<PERIPHERAL_REGISTER>", "schema_version": 2, "access_constraints_v2": [...]}}
    ```

    The JSON object should contain the following fields:
    - `register_name`: The register being extracted, as given in the input. A string.
{ACCESS_CONSTRAINTS_V2_SCHEMA}

    # ACCESS CONSTRAINTS GUIDANCE
{ACCESS_CONSTRAINTS_V2_GUIDANCE}

    # OUTPUT RESTRICTIONS
    - Only report constraints explicitly stated in the given datasheet pages. Do not infer unstated constraints and do not use outside knowledge of the device.
    - Only report constraints that apply to the register being extracted (its own section, or a note that names it).
    - If the pages state no access or ordering requirement for this register, output "access_constraints_v2": [].
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