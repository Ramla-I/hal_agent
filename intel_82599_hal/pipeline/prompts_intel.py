"""Intel 82599 generator prompts.

Variant of prompts/register_info_stm.py for the 82599 NIC datasheet. The
access-constraint schema + guidance are imported VERBATIM from the STM module
(single authoritative constraint text; see that module's header). What differs
is everything peripheral-shaped: the 82599 has no peripherals — registers live
at absolute BAR0 byte offsets (up to 0x1FFFF) and arrays are documented once
in [n] notation — and the detailed sections use a fixed heading + table format:

    # <Full Name> — ABBREV[n] (0x01000 + 0x40*n, n=0...63 ...; RW)
    | Field | Bit(s) | Init Val | Description |

Divergences from the STM prompt (each is a recorded tuning knob):
- no function calls (single-shot; the evolved retriever supplies context)
- extra output field `register_access` (the heading's access code) — regs.rs
  needs register-level RO/WO/RW typing, which MCU SVDs carry per field
- discipline note rewritten: absolute offsets are CORRECT here (the STM note
  calls high-bit offsets "almost certainly wrong")
- reset value assembled from the per-field Init Val column ('X' = undefined)
"""
import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from prompts.register_info_stm import (  # noqa: E402
    ACCESS_CONSTRAINTS_V2_SCHEMA,
    ACCESS_CONSTRAINTS_V2_GUIDANCE,
)

INTEL_FORMAT_NOTE = (
    "NOTE ON THE 82599 DATASHEET FORMAT: this is a memory-mapped NIC, not a "
    "microcontroller — there are no peripherals and no peripheral base addresses. "
    "Every register lives at an absolute byte offset inside the device's BAR0 "
    "register space (0x00000 to 0x1FFFF). A register's authoritative definition is "
    "a section headed like '# Receive Descriptor Length — RDLEN[n] (0x01008 + "
    "0x40*n, n=0...63 and 0x0D008 + 0x40*(n-64), n=64...127; RW)': full name, "
    "abbreviation, offset expression, then the access code after the semicolon. "
    "Array registers ([n]) are documented ONCE; when asked about the base name "
    "(e.g. RDLEN), extract the shared per-element definition. The bit layout is a "
    "markdown table with columns Field | Bit(s) | Init Val | Description."
)

INTEL_DISCIPLINE_NOTE = (
    "EXTRACTION DISCIPLINE (avoid these common mistakes):\n"
    "- address_offset is the ABSOLUTE BAR0 byte offset from the register's section "
    "heading (or the register summary), as hex. Large offsets like 0x10140 or "
    "0x0EC80 are normal and correct. For an [n] array register, give the concrete "
    "offset of element n=0 of the FIRST range (e.g. '0x01008 + 0x40*n, n=0...63' "
    "-> \"0x01008\") — never a formula or a range.\n"
    "- All 82599 registers are 32 bits unless the datasheet explicitly says "
    "otherwise; when the section shows a bit table covering 31:0, size is 32.\n"
    "- Read each subfield's bits from the Bit(s) column. 'm:l' means end_bit = m "
    "(the high bit) and start_bit = l (the low bit); a single number n means "
    "start_bit = end_bit = n. Bit numbering is 0-indexed. Copy every row of the "
    "bit table, including Reserved rows (name them as printed).\n"
    "- register_access is the access code the heading gives after the offset "
    "expression: RW, RO, WO, RC, RW1C, RO/RW, etc. Copy it verbatim.\n"
    "- Subfield access derives from the register access code unless the field's "
    "description explicitly overrides it: RW -> \"read-write\", RO -> "
    "\"read-only\", WO -> \"write-only\", RC (read-to-clear counter) -> "
    "\"read-only\", RW1C -> \"read-write\". Overrides: 'Ignored on writes' / "
    "'hardware controlled' / 'read as 0x0' style text makes that field "
    "\"read-only\"; 'self-clearing' write-trigger bits stay \"read-write\".\n"
    "- reset_value: assemble the 32-bit value from the Init Val column when every "
    "field's init value is defined; if any field is 'X' (undefined), use null.\n"
    "- The 82599 documents PF (physical function) and VF (virtual function) "
    "registers; extract from the PF section unless the register name starts with "
    "VF.\n"
    "- NIC-datasheet constraint cues: a Note that firmware and software may access "
    "the register in parallel and 'a synchronization between them is needed' (the "
    "SW/FW semaphore protocol) IS an access constraint — emit it (kind "
    "\"state_gate\" when the excerpt names the semaphore register/fields, "
    "otherwise kind \"other\" quoting the note and naming the involved "
    "registers). Likewise 'this register/field should only be written/changed "
    "while X is disabled (Y.Z = 0b)' is a state_gate, and 'poll bit X until it "
    "reads 1b before doing Y' is a state_gate with established_by hardware."
)

INTEL_EXAMPLE = """\
Input register: LEDCTL — datasheet section:

# LED Control — LEDCTL (0x00200; RW)

| Field     | Bit(s) | Init Val | Description                                        |
| --------- | ------ | -------- | -------------------------------------------------- |
| LED0_MODE | 3:0    | 0x0      | LED0 Mode. This field specifies the mode of LED0.  |
| Reserved  | 4      | 0b       | Reserved.                                          |
| GLOBAL_BLINK_MODE | 5 | 0b   | Global Blink Mode.                                 |
| LED0_IVRT | 6      | 0b       | LED0 Invert.                                       |
| LED0_BLINK| 7      | 0b       | LED0 Blink.                                        |
| Reserved  | 31:8   | 0x0      | Reserved.                                          |

Output entry (one element of the JSON array):
{
  "register_name": "LEDCTL",
  "datasheet_register_abbreviation": "LEDCTL",
  "register_access": "RW",
  "address_offset": "0x00200",
  "reset_value": "0x0",
  "size": 32,
  "subfields": [
    {"name": "LED0_MODE", "description": "LED0 Mode. This field specifies the mode of LED0.", "access": "read-write", "bit_number": {"start_bit": 0, "end_bit": 3}, "enumerated_values": []},
    {"name": "Reserved", "description": "Reserved.", "access": "read-only", "bit_number": {"start_bit": 4, "end_bit": 4}, "enumerated_values": []},
    {"name": "GLOBAL_BLINK_MODE", "description": "Global Blink Mode.", "access": "read-write", "bit_number": {"start_bit": 5, "end_bit": 5}, "enumerated_values": []},
    {"name": "LED0_IVRT", "description": "LED0 Invert.", "access": "read-write", "bit_number": {"start_bit": 6, "end_bit": 6}, "enumerated_values": []},
    {"name": "LED0_BLINK", "description": "LED0 Blink.", "access": "read-write", "bit_number": {"start_bit": 7, "end_bit": 7}, "enumerated_values": []},
    {"name": "Reserved", "description": "Reserved.", "access": "read-only", "bit_number": {"start_bit": 8, "end_bit": 31}, "enumerated_values": []}
  ],
  "access_constraints_v2": []
}"""


def create_register_info_intel_system_prompt() -> str:
    return f"""
    You are an expert systems engineer, highly familiar with understanding and parsing hardware datasheets for network controllers.

    # INPUT INFORMATION
    You will be given a list of register abbreviations of the Intel 82599 10 GbE controller.
    You will also be given excerpts of the 82599 datasheet in markdown format that could contain information about these registers.
    You will be asked to extract the information about each register.

    {INTEL_FORMAT_NOTE}

    {INTEL_DISCIPLINE_NOTE}

    # OUTPUT INFORMATION
    For each register, you will need to extract the following information:
    - Register name abbreviation
    - Register-level access code
    - Register address offset
    - Register reset value
    - Register size
    - Register subfields
    - Register access constraints (requirements for safe register access)

    # OUTPUT FORMAT
    The output will have 2 parts:
    1. Your reasoning for the output. This will be a string.
    2. A JSON **array** of objects, one per register.

    Always follow this format:
    <reasoning>
    ```json
    <json_array>
    ```

    Each object in the JSON array should contain the following fields:
    - `register_name`: The register abbreviation exactly as given in the input list. A string.
    - `datasheet_register_abbreviation`: The abbreviation the datasheet section heading uses (without the [n] suffix). A string.
    - `register_access`: The access code from the section heading (RW, RO, WO, RC, ...). A string.
    - `address_offset`: The absolute BAR0 offset of the register (element n=0 for arrays), in hexadecimal. A string or null if not found.
    - `reset_value`: The reset value of the register, in hexadecimal. A string or null if not found or undefined.
    - `size`: The size of the register in bits. An integer or null if not found.
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

    # EXAMPLE
    {INTEL_EXAMPLE}

    # ACCESS CONSTRAINTS GUIDANCE
{ACCESS_CONSTRAINTS_V2_GUIDANCE}

    # COMPLETENESS
    - You MUST include ALL subfields for every register. Do not skip, abbreviate, or summarize any subfields, even if a register has many similar or repetitive fields. Every individual bit field found in the datasheet must appear as a separate entry in the subfields array.
    - You MUST output a complete JSON entry for every register in the input list. Do not stop early or omit registers.
    - If the datasheet contains information about a register, include ALL of it: offset, access code, reset value, size, and every subfield.

    # OUTPUT RESTRICTIONS
    - Only return information that is found in the datasheet excerpts. Do not make up any information.
    - If you cannot find a piece of information for a register, leave that field null.
    - For registers where no information is found in the excerpts, include an entry in the array with only `register_name` and all other fields set to null.
    - For access_constraints_v2, only include constraints explicitly stated in the datasheet. Do not infer unstated constraints.
    - The output JSON must be an array, even if there is only one register.
    """


def create_register_info_intel_user_prompt(registers, contexts) -> str:
    """registers: list of dicts {abbrev_base, abbrev, name}; contexts: same-order
    list of retrieved context strings (deduped upstream for batches)."""
    reg_lines = "\n".join(
        f"    - {r['abbrev_base']}  ({r['abbrev']}: {r['name']})" for r in registers
    )
    ctx_parts = []
    seen = set()
    for r, ctx in zip(registers, contexts):
        blocks = [b for b in ctx.split("\n\n---\n\n")]
        fresh = [b for b in blocks if b not in seen]
        seen.update(fresh)
        if fresh:
            ctx_parts.append(
                f"### Context retrieved for {r['abbrev_base']}\n" + "\n\n---\n\n".join(fresh)
            )
    ctx_text = "\n\n".join(ctx_parts)
    return f"""
        # INPUT
        ## REGISTERS TO EXTRACT
{reg_lines}

        ## DATASHEET EXCERPTS
        These are relevant excerpts of the Intel 82599 datasheet:
        {ctx_text}

        # OUTPUT
    """
