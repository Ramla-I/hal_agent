from dataclasses import dataclass
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict

class Manufacturer(Enum):
    INTEL = "Intel"
    STM = "STM"
    NXP = "NXP"
    TI = "TI"

class ContextRetrievalMethod(Enum):
    KEYWORD_SEARCH = "keyword_search"
    OPENAI_FILE_SEARCH = "openai_file_search"
    LOCAL_VECTOR_DB = "local_vector_db"
    OPENEVOLVE = "openevolve"
    REGEX = "regex"

class BatchedRetrievalStrategy(Enum):
    PER_REGISTER = "per_register"                 # Option C: per-register queries, no trim (full union)
    PER_REGISTER_TRIMMED = "per_register_trimmed"  # Option D: per-register queries, trimmed to n_embeddings each (identical to unbatched)
    COMBINED_WITH_FILTER = "combined_with_filter"  # Option A: single combined query + $or metadata filter + reranker
    COMBINED_NO_FILTER = "combined_no_filter"      # Option B: single combined query + reranker only (no metadata filter)

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
    model_config = ConfigDict(extra="ignore")

    context_retrieval_method: ContextRetrievalMethod
    pages_after_keyword: int
    remove_tables: bool
    number_embeddings: int
    re_ranking: bool
    score_threshold: float
    vs_id: str
    regex: str
    # Contiguous chunk expansion parameters
    chunk_expansion_enabled: bool = True  # Enable contiguous chunk expansion after semantic search
    pages_after: int = 2  # Number of pages to expand after each retrieved chunk
    chunk_index_path: str = ""  # Path to chunks_index.csv for chunk index
    expand_table_pages_only: bool = False  # Only expand pages that contain tables
    # Local vector DB parameters (used when context_retrieval_method == LOCAL_VECTOR_DB)
    local_db_name: str = ""  # ChromaDB database name (e.g., "rm0041_md")
    local_db_path: str = ""  # Override path to databases directory
    keyword_boost: bool = True  # Apply keyword boost after search
    reranker_type: str = ""  # "", "local" (FlashRank), "cohere", "bge"
    local_embedding_provider: str = "local"  # "local" (FastEmbed) or "openai"
    metadata_filter_enabled: bool = True  # Filter chunks by register name in metadata before search
    fetch_k_multiplier: int = 5  # Candidate pool multiplier for reranking (fetch_k = n_results * multiplier)
    neighbor_expansion_enabled: bool = False  # Bidirectional same-page chunk neighbor expansion
    batched_retrieval_strategy: BatchedRetrievalStrategy = BatchedRetrievalStrategy.PER_REGISTER
    # OpenEvolve adapter (used when context_retrieval_method == OPENEVOLVE)
    oe_program_path: Optional[str] = None  # Path to an evolved best_program.py; None falls back to the legacy hardcoded rm0041 path

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
    vs_id_text: str
    vs_id_md: str
    
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
    enumerated_values: list[EnumValue] = []

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
