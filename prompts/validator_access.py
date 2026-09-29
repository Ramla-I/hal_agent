"""Access-aware batched validator system prompt.

`prompts/validator.py` is edit-protected, so rather than modify it in place this
layers the access-case improvements on top of its batched system prompt:
  1. the `value` field doc names the access vocabulary (read-only/write-only/read-write);
  2. a dedicated ACCESS validation rule (read the specific field, translate the
     datasheet notation via the legend BEFORE comparing, and — like every other
     invariant — mark it false when the access can't be found in the datasheet text,
     no default assumed);
  3. two access few-shot examples (a status flag that is read-only, and an `rc_w0`
     field that translates to read-write) — the model has zero access examples otherwise.

Value invariants are unchanged (the base text is reused verbatim); only access-scoped
guidance is added. `validator_core` uses this instead of the base system prompt.
"""
from __future__ import annotations

from prompts.validator import create_batched_validator_system_prompt as _base

# --- access-scoped additions (plain strings; operate on the RESOLVED base output) ---
_ACCESS_RULE = (
    "\n    * ACCESS (key=`access`): judge the SPECIFIC field, reading its access from "
    "that field's row in the register's bit-description table (an access column such as "
    "r / rw / w / rc_w0). Translate the datasheet's notation to its canonical type using "
    "the notation key above BEFORE comparing — e.g. rc_w0 / rc_w1 / rt_w are read-write, "
    "a status flag shown as `r` is read-only, `w` is write-only. If the field's access is "
    "not explicitly stated in the retrieved datasheet text, treat it like any other "
    "unfound fact — set is_true=false with confidence 1.0; do NOT assume a default."
)

_EX_INV_4 = ('      4. peripheral="FTM0", register="FTM0_C7SC", field_name="Xyfka", '
             'key="bit_offset", value="7"')
_EX_INV_56 = (
    '\n      5. peripheral="SPI1", register="SR", field_name="OVR", key="access", value="read-write"'
    '\n      6. peripheral="TIM2", register="SR", field_name="UIF", key="access", value="read-write"'
)
_EX_RSN_4 = '      4. FTM0_C7SC exists, but it has no field named "Xyfka". False.'
_EX_RSN_56 = (
    "\n      5. SPI1_SR.OVR is an overrun status flag; the datasheet marks it read-only "
    "(r), so a read-write claim is wrong. False, confident."
    "\n      6. TIM2_SR.UIF is printed as `rc_w0` (read, cleared by writing 0), which the "
    "notation key maps to read-write, so read-write is correct. True."
)
# NB: braces are single here — the base f-string has already been rendered.
_EX_JSON_4 = '        {"invariant_index": 4, "is_true": false, "confidence_score": 1.0}\n    ]'
_EX_JSON_456 = (
    '        {"invariant_index": 4, "is_true": false, "confidence_score": 1.0},\n'
    '        {"invariant_index": 5, "is_true": false, "confidence_score": 1.0},\n'
    '        {"invariant_index": 6, "is_true": true, "confidence_score": 0.95}\n    ]'
)


def _apply(s: str, old: str, new: str, what: str) -> str:
    if old not in s:
        raise RuntimeError(f"access prompt layering: anchor missing ({what}) — base prompt changed")
    return s.replace(old, new, 1)


def create_batched_validator_system_prompt(access_legend: str = "", name_aliasing: bool = False) -> str:
    """The base batched system prompt with access-case guidance layered on."""
    s = _base(access_legend, name_aliasing)
    s = _apply(s, "The value to validate",
               "The value to validate (for `access`, one of: read-only, write-only, read-write)",
               "value vocabulary")
    s = _apply(s, "set is_true=false and confidence_score=1.0",
               "set is_true=false and confidence_score=1.0" + _ACCESS_RULE, "access rule")
    s = _apply(s, _EX_INV_4, _EX_INV_4 + _EX_INV_56, "example invariants")
    s = _apply(s, _EX_RSN_4, _EX_RSN_4 + _EX_RSN_56, "example reasoning")
    s = _apply(s, _EX_JSON_4, _EX_JSON_456, "example json")
    return s
