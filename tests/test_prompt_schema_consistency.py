"""
Test that the JSON schema described in prompts matches the Pydantic models in defs.py

This ensures the prompt description stays in sync with the actual data models.
Covers both the v1 layout/constraint wire format (still parsed from the
corpus) and the grammar-v2 constraint text (ACCESS_CONSTRAINTS_V2_SCHEMA /
ACCESS_CONSTRAINTS_V2_GUIDANCE), which every generator system prompt and the
constraints-only eval prompt must share verbatim.
"""

import re
import sys
import os
import json

from pydantic import TypeAdapter

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from defs import (
    ConstraintBase,
    ConstraintV2,
    FieldCondition,
    RegisterInfo,
    StateGate,
)
from prompts.register_info_stm import (
    ACCESS_CONSTRAINTS_V2_GUIDANCE,
    ACCESS_CONSTRAINTS_V2_SCHEMA,
    create_register_constraints_v2_system_prompt,
    create_register_info_stm_system_prompt,
    create_register_info_stm_system_prompt_batched,
    create_register_info_stm_system_prompt_batched_minimal,
)
from prompts.examples import (
    stm_access_constraints_v2_examples,
    stm_datasheet_batched_example,
    stm_datasheet_batched_example_no_reasoning,
    stm_datasheet_example,
)

CONSTRAINT_V2_ADAPTER = TypeAdapter(ConstraintV2)

ALL_SYSTEM_PROMPTS = {
    "full": create_register_info_stm_system_prompt(),
    "batched": create_register_info_stm_system_prompt_batched(),
    "batched_no_reasoning": create_register_info_stm_system_prompt_batched(
        include_reasoning=False),
    "batched_minimal": create_register_info_stm_system_prompt_batched_minimal(),
    "constraints_only": create_register_constraints_v2_system_prompt(),
}

_JSON_FENCE_RE = re.compile(r"```json\s*(.*?)```", re.DOTALL)


def test_all_required_fields_present():
    """Test that all required fields are present in the model"""
    # This test ensures we don't accidentally make required fields optional
    required_fields = {
        "datasheet_register_abbreviation",
        "address_offset",
        "reset_value",
        "size",
        "subfields",
    }
    # Optional fields with defaults. access_constraints_v2 defaults empty (a
    # register with no access rule); schema_version tags the grammar version.
    optional_fields = {"schema_version", "access_constraints_v2"}

    model_fields = set(RegisterInfo.model_fields.keys())
    assert required_fields | optional_fields == model_fields, \
        f"Field mismatch. Expected: {required_fields | optional_fields}, Got: {model_fields}"
    for name in required_fields:
        assert RegisterInfo.model_fields[name].is_required(), \
            f"{name} must stay required"
    for name in optional_fields:
        assert not RegisterInfo.model_fields[name].is_required(), \
            f"{name} must stay optional"
    assert RegisterInfo.model_fields["schema_version"].default == 2


# ---------------------------------------------------------------------------
# Grammar v2: prompt <-> schema alignment
# ---------------------------------------------------------------------------


def test_native_v2_register_info_parses():
    """The v2-native wire format (step F): access_constraints kept empty,
    access_constraints_v2 populated, schema_version 2."""
    sample_json = {
        "datasheet_register_abbreviation": "USART_BRR",
        "address_offset": "0x08",
        "reset_value": "0x0000",
        "size": 32,
        "subfields": [],
        "access_constraints_v2": [
            {
                "kind": "state_gate",
                "target_register": "USART_BRR",
                "target_fields": [],
                "target_operation": "write",
                "preconditions": [
                    {"register": "USART_CR1", "field": "UE", "state": "cleared",
                     "established_by": "software", "action_operation": "modify"}
                ],
                "postconditions": [],
                "severity": "error",
                "consequence": "baud rate corrupted",
                "datasheet_text": "This register can only be written when the USART is disabled (UE=0).",
            }
        ],
        "schema_version": 2,
    }
    register_info = RegisterInfo(**sample_json)
    assert register_info.schema_version == 2
    (gate,) = register_info.access_constraints_v2
    assert isinstance(gate, StateGate)
    assert gate.preconditions[0].established_by == "software"


def test_all_prompts_share_v2_constraint_text():
    """Every generator system prompt AND the constraints-only eval prompt
    embed the two authoritative constraint-text constants verbatim -- the
    factoring that lets the extraction eval test exactly what ships."""
    for name, prompt in ALL_SYSTEM_PROMPTS.items():
        assert ACCESS_CONSTRAINTS_V2_SCHEMA in prompt, \
            f"{name} prompt does not embed ACCESS_CONSTRAINTS_V2_SCHEMA verbatim"
        assert ACCESS_CONSTRAINTS_V2_GUIDANCE in prompt, \
            f"{name} prompt does not embed ACCESS_CONSTRAINTS_V2_GUIDANCE verbatim"
        assert stm_access_constraints_v2_examples in prompt, \
            f"{name} prompt does not embed the worked constraint examples"


def test_prompt_schema_covers_v2_vocabulary():
    """Every Literal vocabulary of the v2 union appears in the schema text;
    every FieldCondition wire key is described."""
    kinds = ConstraintBase.model_fields["kind"].annotation.__args__
    assert set(kinds) == {"state_gate", "sequence", "write_once", "delay",
                          "read_effect", "clock_gate", "value_relation", "other"}
    for kind in kinds:
        assert f'"{kind}"' in ACCESS_CONSTRAINTS_V2_SCHEMA, \
            f"kind {kind} missing from the prompt schema"
    for field_name in FieldCondition.model_fields:
        assert f"`{field_name}`" in ACCESS_CONSTRAINTS_V2_SCHEMA, \
            f"condition field {field_name} missing from the prompt schema"
    for value in ("hardware", "software"):
        assert f'"{value}"' in ACCESS_CONSTRAINTS_V2_SCHEMA
    for state in ("cleared", "set", "equals"):
        assert f'"{state}"' in ACCESS_CONSTRAINTS_V2_SCHEMA
    # The wire-format keys themselves.
    for key in ("schema_version", "access_constraints_v2"):
        assert f"`{key}`" in ACCESS_CONSTRAINTS_V2_SCHEMA
    # established_by is explained (one sentence each) in the guidance.
    assert "established_by" in ACCESS_CONSTRAINTS_V2_GUIDANCE
    assert "action_operation" in ACCESS_CONSTRAINTS_V2_GUIDANCE


def test_guidance_has_decision_tree_and_negative_rules():
    """Plan section 6: decision tree ends in the two-way fork; the negative
    routing rules cover every FP class of section 5.3."""
    g = ACCESS_CONSTRAINTS_V2_GUIDANCE
    # Two-way fork: genuine-but-fits-no-kind -> other; not-a-requirement -> nothing.
    assert '"other"' in g
    assert "emit NOTHING" in g
    for negative in ("w1c", "Read-to-clear", "Access-width", "privileged",
                     "don't-care", "Reset behavior"):
        assert negative in g, f"negative routing rule for {negative!r} missing"
    # Naming, values, verbatim-quote and dedup rules.
    assert "whole_register" in g
    assert "wildcards" in g
    assert "VERBATIM AND COMPLETE" in g
    assert "target_fields" in g  # dedup guidance


def test_prompt_example_json_validates_against_models():
    """Every ```json block in the example sets parses, and every
    access_constraints_v2 entry validates against the v2 union -- so the
    few-shots can never drift from defs.py."""
    # strict=True: every fenced block must be valid JSON (pure example sets).
    # strict=False: format-placeholder snippets like ```json\n[...]``` are
    # allowed to skip (full built prompts).
    sources = {
        "stm_datasheet_example": (stm_datasheet_example, True),
        "stm_access_constraints_v2_examples":
            (stm_access_constraints_v2_examples, True),
        "stm_datasheet_batched_example": (stm_datasheet_batched_example, True),
        "stm_datasheet_batched_example_no_reasoning":
            (stm_datasheet_batched_example_no_reasoning, True),
        "batched_minimal_prompt":
            (ALL_SYSTEM_PROMPTS["batched_minimal"], False),
    }
    v2_entries = 0
    for name, (text, strict) in sources.items():
        blocks = _JSON_FENCE_RE.findall(text)
        assert blocks, f"{name} has no ```json blocks"
        parsed = 0
        for block in blocks:
            try:
                data = json.loads(block)
            except ValueError:
                if strict:
                    raise AssertionError(
                        f"{name} has an invalid ```json block: {block[:120]!r}")
                continue
            parsed += 1
            objs = data if isinstance(data, list) else [data]
            for obj in objs:
                if not isinstance(obj, dict):
                    continue
                v2 = obj.get("access_constraints_v2")
                if isinstance(obj.get("kind"), str):
                    # a bare constraint example
                    CONSTRAINT_V2_ADAPTER.validate_python(obj)
                    v2_entries += 1
                if v2 is None:
                    continue
                # The wire format is grammar-v2 only: no legacy access_constraints
                # key, schema_version stamped 2.
                assert "access_constraints" not in obj, \
                    f"{name}: the retired v1 access_constraints key must be gone"
                assert obj.get("schema_version") == 2, \
                    f"{name}: schema_version 2 missing"
                for entry in v2:
                    CONSTRAINT_V2_ADAPTER.validate_python(entry)
                    v2_entries += 1
        assert parsed, f"{name}: no ```json block parsed"
    assert v2_entries >= 4, "expected the worked few-shots to carry v2 constraints"


def test_synthetic_intel_example_gone():
    """Decision 11.6: the synthetic Intel MTQC/RTTDCS example is replaced by
    real STM few-shots everywhere."""
    for name, prompt in ALL_SYSTEM_PROMPTS.items():
        assert "MTQC" not in prompt and "RTTDCS" not in prompt, \
            f"{name} prompt still carries the synthetic Intel example"
    # And the real replacements are present in the shared examples.
    for marker in ("RTC_CRL", "IWDG_KR", "USART_CR1", "EWIF"):
        assert marker in stm_access_constraints_v2_examples, \
            f"real STM few-shot {marker} missing"


if __name__ == "__main__":
    # Run all test functions
    test_functions = [
        test_complete_register_info_schema,
        test_minimal_register_info_schema,
        test_access_constraint_with_postconditions,
        test_field_state_schema,
        test_field_state_with_value,
        test_constraint_target_fields,
        test_multiple_constraints,
        test_all_required_fields_present,
        test_constraint_required_fields,
        test_field_state_required_fields,
        test_native_v2_register_info_parses,
        test_all_prompts_share_v2_constraint_text,
        test_prompt_schema_covers_v2_vocabulary,
        test_guidance_has_decision_tree_and_negative_rules,
        test_prompt_example_json_validates_against_models,
        test_synthetic_intel_example_gone,
    ]

    print("Running prompt schema consistency tests...\n")
    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")

    if failed > 0:
        exit(1)
