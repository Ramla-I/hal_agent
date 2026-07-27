"""
Tests for the v1 -> v2 conversion tool (applications/pac_codegen/convert_v1_to_v2.py).

The pipeline is grammar-v2 only; this tool is the ONE place the retired v1
access-constraint wire format is still parsed (FieldState /
RegisterAccessConstraint / V1RegisterInfo) before being lifted to v2. These
tests pin that the legacy wire format keeps parsing, so old generator output
can always be converted. (The v1->v2 lift transformation itself is covered by
tests/test_constraints_v2.py; end-to-end convert-then-collect by
tests/test_constraints_v2.py::test_collect_end_to_end_*.)

Run: .venv/bin/python -m pytest tests/test_convert_v1_to_v2.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from applications.pac_codegen.convert_v1_to_v2 import (
    FieldState,
    RegisterAccessConstraint,
    V1RegisterInfo,
)


def test_v1_field_state_parses():
    """A v1 FieldState carries exactly (register_name, field_name,
    required_state), including the "equals:<value>" form."""
    assert set(FieldState.model_fields) == {
        "register_name", "field_name", "required_state"}
    fs = FieldState(register_name="I2C_CR1", field_name="STOP",
                    required_state="cleared")
    assert (fs.register_name, fs.field_name, fs.required_state) == (
        "I2C_CR1", "STOP", "cleared")
    assert FieldState(register_name="CONFIG", field_name="MODE",
                      required_state="equals:0x3").required_state == "equals:0x3"


def test_v1_register_access_constraint_parses():
    """A full v1 constraint (pre + post + target_fields) parses, with the fixed
    field set (the pre+post software-action shape from rm0008 rtc_cnth)."""
    assert set(RegisterAccessConstraint.model_fields) == {
        "target_register", "target_fields", "target_operation",
        "preconditions", "postconditions", "severity", "consequence",
        "datasheet_text"}
    c = RegisterAccessConstraint(
        target_register="RTC_CNTH", target_fields=["CNTH"],
        target_operation="write",
        preconditions=[{"register_name": "RTC_CRL", "field_name": "CNF",
                        "required_state": "set"}],
        postconditions=[{"register_name": "RTC_CRL", "field_name": "CNF",
                         "required_state": "cleared"}],
        severity="error", consequence="c", datasheet_text="t")
    assert c.target_fields == ["CNTH"]
    assert c.preconditions[0].required_state == "set"
    assert c.postconditions[0].required_state == "cleared"


def test_v1_register_info_parses():
    """A complete legacy v1 register file (subfields + constraints) and a
    minimal empty one both parse via V1RegisterInfo."""
    complete = V1RegisterInfo(
        datasheet_register_abbreviation="I2C_CR1", address_offset="0x00",
        reset_value="0x0000", size=32,
        subfields=[{"name": "PE", "description": "Peripheral enable",
                    "access": "read-write",
                    "bit_number": {"start_bit": 0, "end_bit": 0},
                    "enumerated_values": []}],
        access_constraints=[{
            "target_register": "I2C_CR1", "target_fields": [],
            "target_operation": "write",
            "preconditions": [
                {"register_name": "I2C_CR1", "field_name": "STOP",
                 "required_state": "cleared"},
                {"register_name": "I2C_CR1", "field_name": "START",
                 "required_state": "cleared"}],
            "postconditions": [], "severity": "error", "consequence": "c",
            "datasheet_text": "When the STOP or START bit is set, ..."}])
    assert complete.datasheet_register_abbreviation == "I2C_CR1"
    assert len(complete.access_constraints) == 1
    assert len(complete.access_constraints[0].preconditions) == 2

    minimal = V1RegisterInfo(
        datasheet_register_abbreviation="TEST_REG", address_offset="0x04",
        reset_value="0x00", size=32, subfields=[], access_constraints=[])
    assert minimal.access_constraints == []
