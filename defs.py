from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel

class Manufacturer(Enum):
    INTEL = "Intel"
    STM = "STM"
    NXP = "NXP"
    TI = "TI"

class ContextRetrievalMethod(Enum):
    KEYWORD_SEARCH = "keyword_search"
    SEMANTIC_SEARCH = "semantic_search"
    REGEX = "regex"

class CoverageInfo(BaseModel):
    peripheral_coverage: float
    register_coverage: float
    field_coverage: float
    peripherals_only_in_svd: list[str]
    peripherals_only_in_agent_output: list[str]
    peripherals_present_in_both: list[str]
    registers_only_in_svd: dict[str, list[str]]
    registers_only_in_agent_output: dict[str, list[str]]
    registers_present_in_both: dict[str, list[str]]
    fields_only_in_svd: dict[str, dict[str, list[str]]]
    fields_only_in_agent_output: dict[str, dict[str, list[str]]]
    fields_present_in_both: dict[str, dict[str, list[str]]]


class ContextRetrievalParameters(BaseModel):
    context_retrieval_method: ContextRetrievalMethod
    pages_after_keyword: int
    remove_tables: bool
    number_embeddings: int
    re_ranking: bool
    score_threshold: float
    query_rewrite: bool
    vs_id: str
    regex: str
    other: str

class CoverageImproverOutput(BaseModel):
    context_retrieval_parameters: ContextRetrievalParameters
    stop_improving: bool
    
@dataclass
class UserContext:
    device_name: str
    peripheral_name: str
    manufacturer: Manufacturer
    driver_path: str
    run: int
    file_id: str
    vs_id: str

class FieldState(BaseModel):
    """Represents a field state requirement (pre or post condition)"""
    register_name: str  # Can be different register (e.g., "RTTDCS" when constraining "MTQC")
    field_name: str
    required_state: str  # "cleared", "set", "equals:<value>"

class RegisterAccessConstraint(BaseModel):
    """
    Constraint on register/field access using linear types.

    Preconditions are enforced by consuming linear type tokens.
    Postconditions are enforced by producing linear type tokens that must be consumed elsewhere.

    See REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md for detailed explanation and examples.
    """
    # What's being constrained
    target_register: str
    target_fields: list[str]  # Empty = whole register
    target_operation: str  # "write", "read", "modify"

    # Pre-conditions: linear types that must be CONSUMED
    # e.g., to write, you must consume StopClearedToken
    preconditions: list[FieldState]

    # Post-conditions: linear types that are PRODUCED and must be used elsewhere
    # e.g., writing produces ArbdisMustClearToken that must be consumed
    postconditions: list[FieldState]

    # Metadata
    severity: str  # "error", "warning"
    consequence: str
    datasheet_text: str

class BitNumber(BaseModel):
    start_bit: int
    end_bit: int

class EnumValue(BaseModel):
    value: str
    name: str

class BitField(BaseModel):
    name: str
    description: str
    access: str
    bit_number: BitNumber
    enumerated_values: list[EnumValue]

class RegisterInfo(BaseModel):
    datasheet_register_abbreviation: str
    address_offset: str
    reset_value: str
    size: int
    subfields: list[BitField]
    access_constraints: list[RegisterAccessConstraint]

class RegisterList(BaseModel):
    registers: list[RegisterInfo]

class RegisterName(BaseModel):
    driver_register_name: str
    datasheet_register_name: str
    datasheet_register_abbreviation: str

class RegisterNameList(BaseModel):
    registers: list[RegisterName]

class SectionInfo(BaseModel):
    section_exists: bool
    peripheral_name: str
    section_name: str
    start_page: int
    end_page: int
