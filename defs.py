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
    vs_id: str
    regex: str
    other: str


class CoverageImproverOutput(BaseModel):
    context_retrieval_parameters: ContextRetrievalParameters
    reasoning: str
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

class RegisterDependency(BaseModel):
    dependent_register_name: str
    dependent_subfield_name: str
    dependee_register_name: str
    dependee_subfield_name: str
    dependency_type: str # read-after, write-after, other
    relevant_sentence: str

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
    dependencies: list[RegisterDependency]

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
