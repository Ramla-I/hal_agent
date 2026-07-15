"""
Test that the JSON schema described in prompts matches the Pydantic models in defs.py

This ensures the prompt description stays in sync with the actual data models.
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from defs import RegisterInfo, BitField, BitNumber, EnumValue, FieldState, RegisterAccessConstraint


def test_complete_register_info_schema():
    """Test that a complete RegisterInfo JSON can be parsed"""
    sample_json = {
        "datasheet_register_abbreviation": "I2C_CR1",
        "address_offset": "0x00",
        "reset_value": "0x0000",
        "size": 32,
        "subfields": [
            {
                "name": "PE",
                "description": "Peripheral enable",
                "access": "read-write",
                "bit_number": {
                    "start_bit": 0,
                    "end_bit": 0
                },
                "enumerated_values": [
                    {
                        "value": "0",
                        "name": "Disabled"
                    },
                    {
                        "value": "1",
                        "name": "Enabled"
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
                    }
                ],
                "postconditions": [],
                "severity": "error",
                "consequence": "Risk of setting second STOP or START request",
                "datasheet_text": "When the STOP or START bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware."
            }
        ]
    }

    # This should parse without errors
    register_info = RegisterInfo(**sample_json)

    # Verify structure
    assert register_info.datasheet_register_abbreviation == "I2C_CR1"
    assert register_info.address_offset == "0x00"
    assert register_info.reset_value == "0x0000"
    assert register_info.size == 32
    assert len(register_info.subfields) == 1
    assert len(register_info.access_constraints) == 1


def test_minimal_register_info_schema():
    """Test that minimal RegisterInfo JSON can be parsed"""
    sample_json = {
        "datasheet_register_abbreviation": "TEST_REG",
        "address_offset": "0x04",
        "reset_value": "0x00",
        "size": 32,
        "subfields": [],
        "access_constraints": []
    }

    register_info = RegisterInfo(**sample_json)
    assert register_info.datasheet_register_abbreviation == "TEST_REG"
    assert len(register_info.subfields) == 0
    assert len(register_info.access_constraints) == 0


def test_access_constraint_with_postconditions():
    """Test access constraint with both pre and post conditions"""
    sample_json = {
        "datasheet_register_abbreviation": "MTQC",
        "address_offset": "0x10",
        "reset_value": "0x0000",
        "size": 32,
        "subfields": [],
        "access_constraints": [
            {
                "target_register": "MTQC",
                "target_fields": [],
                "target_operation": "write",
                "preconditions": [
                    {
                        "register_name": "RTTDCS",
                        "field_name": "ARBDIS",
                        "required_state": "set"
                    }
                ],
                "postconditions": [
                    {
                        "register_name": "RTTDCS",
                        "field_name": "ARBDIS",
                        "required_state": "cleared"
                    }
                ],
                "severity": "error",
                "consequence": "Undefined behavior if ARBDIS not cleared after",
                "datasheet_text": "Software must set RTTDCS.ARBDIS before configuring MTQC and then clear RTTDCS.ARBDIS afterwards"
            }
        ]
    }

    register_info = RegisterInfo(**sample_json)
    constraint = register_info.access_constraints[0]

    assert constraint.target_register == "MTQC"
    assert len(constraint.preconditions) == 1
    assert len(constraint.postconditions) == 1
    assert constraint.preconditions[0].required_state == "set"
    assert constraint.postconditions[0].required_state == "cleared"


def test_field_state_schema():
    """Test FieldState model directly"""
    field_state_json = {
        "register_name": "I2C_CR1",
        "field_name": "STOP",
        "required_state": "cleared"
    }

    field_state = FieldState(**field_state_json)
    assert field_state.register_name == "I2C_CR1"
    assert field_state.field_name == "STOP"
    assert field_state.required_state == "cleared"


def test_field_state_with_value():
    """Test FieldState with equals value"""
    field_state_json = {
        "register_name": "CONFIG",
        "field_name": "MODE",
        "required_state": "equals:0x3"
    }

    field_state = FieldState(**field_state_json)
    assert field_state.required_state == "equals:0x3"


def test_constraint_target_fields():
    """Test constraint targeting specific fields"""
    sample_json = {
        "datasheet_register_abbreviation": "TEST",
        "address_offset": "0x00",
        "reset_value": "0x00",
        "size": 32,
        "subfields": [],
        "access_constraints": [
            {
                "target_register": "TEST",
                "target_fields": ["FIELD1", "FIELD2"],
                "target_operation": "modify",
                "preconditions": [],
                "postconditions": [],
                "severity": "warning",
                "consequence": "Test consequence",
                "datasheet_text": "Test text"
            }
        ]
    }

    register_info = RegisterInfo(**sample_json)
    constraint = register_info.access_constraints[0]

    assert constraint.target_fields == ["FIELD1", "FIELD2"]
    assert constraint.target_operation == "modify"


def test_multiple_constraints():
    """Test register with multiple access constraints"""
    sample_json = {
        "datasheet_register_abbreviation": "TEST",
        "address_offset": "0x00",
        "reset_value": "0x00",
        "size": 32,
        "subfields": [],
        "access_constraints": [
            {
                "target_register": "TEST",
                "target_fields": [],
                "target_operation": "write",
                "preconditions": [
                    {
                        "register_name": "STATUS",
                        "field_name": "BUSY",
                        "required_state": "cleared"
                    }
                ],
                "postconditions": [],
                "severity": "error",
                "consequence": "Data corruption",
                "datasheet_text": "Wait until BUSY is cleared"
            },
            {
                "target_register": "TEST",
                "target_fields": [],
                "target_operation": "read",
                "preconditions": [
                    {
                        "register_name": "STATUS",
                        "field_name": "READY",
                        "required_state": "set"
                    }
                ],
                "postconditions": [],
                "severity": "warning",
                "consequence": "May read stale data",
                "datasheet_text": "Read only when READY is set"
            }
        ]
    }

    register_info = RegisterInfo(**sample_json)
    assert len(register_info.access_constraints) == 2
    assert register_info.access_constraints[0].target_operation == "write"
    assert register_info.access_constraints[1].target_operation == "read"


def test_all_required_fields_present():
    """Test that all required fields are present in the model"""
    # This test ensures we don't accidentally make required fields optional
    required_fields = {
        "datasheet_register_abbreviation",
        "address_offset",
        "reset_value",
        "size",
        "subfields",
        "access_constraints"
    }
    # Optional fields with defaults -- absent from every prompt-emitted JSON,
    # so they must never become required. schema_version tags the constraint
    # grammar version (v1 wire format until roadmap step F; defaults to 1).
    optional_fields = {"schema_version"}

    model_fields = set(RegisterInfo.model_fields.keys())
    assert required_fields | optional_fields == model_fields, \
        f"Field mismatch. Expected: {required_fields | optional_fields}, Got: {model_fields}"
    for name in required_fields:
        assert RegisterInfo.model_fields[name].is_required(), \
            f"{name} must stay required"
    for name in optional_fields:
        assert not RegisterInfo.model_fields[name].is_required(), \
            f"{name} must stay optional (prompts do not emit it)"
    assert RegisterInfo.model_fields["schema_version"].default == 1


def test_constraint_required_fields():
    """Test that RegisterAccessConstraint has all required fields"""
    required_fields = {
        "target_register",
        "target_fields",
        "target_operation",
        "preconditions",
        "postconditions",
        "severity",
        "consequence",
        "datasheet_text"
    }

    model_fields = set(RegisterAccessConstraint.model_fields.keys())
    assert required_fields == model_fields, f"Field mismatch. Expected: {required_fields}, Got: {model_fields}"


def test_field_state_required_fields():
    """Test that FieldState has all required fields"""
    required_fields = {
        "register_name",
        "field_name",
        "required_state"
    }

    model_fields = set(FieldState.model_fields.keys())
    assert required_fields == model_fields, f"Field mismatch. Expected: {required_fields}, Got: {model_fields}"


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
