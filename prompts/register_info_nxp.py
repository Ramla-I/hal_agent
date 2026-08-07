"""NXP / Kinetis register-extraction prompts.

Reuses the STM prompt body (parameterized) but swaps the vendor-specific notes
and examples: NXP naming conventions (short register names, UARTx/FTMx/ADCx
instances) and a stronger value-discipline rule that forbids the garbage values
observed when the STM prompt ran on NXP data (e.g. emitting the string
"Undefined" for a device-unique reset instead of null).
"""
from prompts.function_calls import calculate_address_offset_fn_description
from prompts.register_info_stm import (
    EXTRACTION_DISCIPLINE_NOTE,
    create_register_info_stm_system_prompt,
    create_register_info_stm_system_prompt_batched,
    create_register_info_stm_user_prompt,
    create_register_info_stm_user_prompt_batched,
)
from prompts.examples import nxp_datasheet_batched_example

# NXP peripherals are also multi-instance, documented once under a generic name.
NXP_INSTANCE_NAMING_NOTE = (
    "NOTE ON NXP/KINETIS NAMING: registers use SHORT names (e.g. C1, C2, S1, SC1, "
    "BDH, BDL) and are prefixed with the peripheral (UART0_C1). Peripherals often "
    "have several numbered instances (UART0/UART1/UART2, FTM0/FTM1/FTM2, "
    "ADC0/ADC1) that share an IDENTICAL register layout; the datasheet frequently "
    "documents them ONCE under a generic name (e.g. 'UARTx_C1', 'FTMx') or under "
    "instance 0. If asked about instance N but the section uses the generic or "
    "instance-0 name, the layout still applies — use it rather than reporting the "
    "info as missing. Many Kinetis registers are 8-bit (size = 8), not 32-bit."
)

# STM discipline + NXP-specific reinforcement of the null rule (the concrete
# failure mode: 'Undefined'/'device-specific' reset values emitted as strings).
NXP_EXTRACTION_DISCIPLINE_NOTE = EXTRACTION_DISCIPLINE_NOTE + (
    "\n- A register whose reset value is device-unique or explicitly 'undefined' / "
    "'unaffected' / 'not reset' (e.g. UID/UUID, factory-trim, or read-only ID "
    "registers) has NO fixed reset value: output reset_value = null. NEVER emit the "
    "literal string 'Undefined', 'unknown', 'device-specific', 'N/A', or 'x' for any "
    "attribute — null is the only allowed not-found value."
)


def create_register_info_nxp_system_prompt(
    function_calls_description=calculate_address_offset_fn_description,
    examples=None,
) -> str:
    return create_register_info_stm_system_prompt(
        function_calls_description,
        examples=examples,
        naming_note=NXP_INSTANCE_NAMING_NOTE,
        discipline_note=NXP_EXTRACTION_DISCIPLINE_NOTE,
    )


def create_register_info_nxp_user_prompt(register_name, peripheral_name, datasheet_pages):
    return create_register_info_stm_user_prompt(register_name, peripheral_name, datasheet_pages)


def create_register_info_nxp_system_prompt_batched(
    function_calls_description=calculate_address_offset_fn_description,
    examples=None,
    include_reasoning: bool = True,
) -> str:
    return create_register_info_stm_system_prompt_batched(
        function_calls_description,
        examples=examples if examples is not None else nxp_datasheet_batched_example,
        include_reasoning=include_reasoning,
        naming_note=NXP_INSTANCE_NAMING_NOTE,
        discipline_note=NXP_EXTRACTION_DISCIPLINE_NOTE,
    )


def create_register_info_nxp_user_prompt_batched(peripheral_name, register_names, datasheet_pages):
    return create_register_info_stm_user_prompt_batched(peripheral_name, register_names, datasheet_pages)
