import re
import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    # Access constraints (grammar v2 — the discriminated union defined below;
    # forward reference resolved by the model_rebuild() at the end of this
    # module). Empty when the datasheet states no access/ordering requirement.
    # Old grammar-v1 generator output is converted first with
    # applications/pac_codegen/convert_v1_to_v2.py.
    access_constraints_v2: list["ConstraintV2"] = []

class RegisterList(BaseModel):
    registers: list[RegisterInfo]

class RegisterName(BaseModel):
    driver_register_name: str
    datasheet_register_name: str
    datasheet_register_abbreviation: str

class RegisterNameList(BaseModel):
    registers: list[RegisterName]


# ---------------------------------------------------------------------------
# Register-constraint grammar v2
# ---------------------------------------------------------------------------
# Normative spec: docs/register_constraints_plan.md Appendix B (summarized in
# docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md). A constraint is a discriminated
# union on `kind`; every vocabulary is a Literal so drift is rejected at
# collection-time pydantic parsing rather than spliced into generated Rust.
#
# Terminology (reserved verbs, plan section 3): the LLM pipeline VALIDATES
# extracted facts; the compiler ENFORCES that a witness is presented before a
# gated operation (both enforceable classes are compile-time witness-gated).
# A witness is minted either by a runtime CHECK of hardware state (state
# witness) or by performing a required software ACTION (action witness, no
# runtime check). Four token roles: state witness, action witness, obligation
# (a duty to discharge -- postcondition cleanup), capability (authority to do
# something at most once -- write_once).
#
# This module is grammar-v2 only. Old grammar-v1 generator output is converted
# to v2 by applications/pac_codegen/convert_v1_to_v2.py, which owns the retired
# v1 models and the mechanical lift.


# Accepted numeric syntax for constraint values, everywhere: hex, binary, or
# decimal. One regex so the vocabulary cannot drift between the model
# validators and the v1 lift (it is also the collection repair rule for the
# OR-string drift like "equals:0b01|0b10|0b11").
_VALUE_TOKEN_RE = re.compile(r"^(0x[0-9A-Fa-f]+|0b[01]+|\d+)$")


def parse_value_token(token) -> int:
    """Parse one numeric value token (int, "0x5555", "0b01", "7") to int.

    This is the single definition of the accepted numeric syntax -- both the
    FieldCondition/Step validators and the v1->v2 lift funnel through it, so
    strings are normalized to int in exactly one place (killing both the
    OR-string drift and the code-injection surface of splicing value strings
    verbatim into Rust).

    Raises ValueError for anything else (including negative ints -- register
    field values are unsigned).
    """
    if isinstance(token, bool):
        raise ValueError(f"boolean is not a register value: {token!r}")
    if isinstance(token, int):
        if token < 0:
            raise ValueError(f"register values are unsigned, got {token}")
        return token
    if isinstance(token, str):
        tok = token.strip()
        if _VALUE_TOKEN_RE.match(tok):
            if tok.startswith("0x"):
                return int(tok, 16)
            if tok.startswith("0b"):
                return int(tok, 2)
            return int(tok, 10)
    raise ValueError(
        f"unparseable value token {token!r} (expected hex 0x..., binary 0b..., or decimal)"
    )


# The spec-mandated field name `register` shadows only ABCMeta.register
# (inherited via pydantic's metaclass), which is never used on these models;
# suppress pydantic's shadowing warning for exactly that name.
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message=r'Field name "register"')

    class FieldRef(BaseModel):
        """A validated reference to a register (and optionally one of its fields).

        `field` must be a real SVD field name -- no ranges ("LCK0-LCK15"),
        wildcards ("AES_KEYR*"), or pseudo-fields ("key", ""). Whole-register
        references set `whole_register` explicitly instead of the v1 corpus's
        silent field_name="" convention, so "refers to the whole register" and
        "the model failed to name a field" are distinguishable.
        """
        register: str                 # SVD-canonical name; resolved at collection
        field: str = ""               # SVD-canonical; "" only with whole_register
        whole_register: bool = False

        @model_validator(mode="after")
        def _field_iff_not_whole_register(self):
            if self.whole_register:
                if self.field:
                    raise ValueError(
                        "whole_register=true must not name a field "
                        f"(got field={self.field!r})"
                    )
            elif not self.field:
                raise ValueError(
                    'field "" is not allowed; whole-register references must '
                    "set whole_register=true"
                )
            return self

    class Step(BaseModel):
        """One step of an ordered protocol (also the trigger operation of delay)."""
        register: str
        operation: Literal["write", "read"]
        value: Optional[int] = None   # required for writes with prescribed values

        @field_validator("value", mode="before")
        @classmethod
        def _parse_value(cls, v):
            if v is None:
                return None
            return parse_value_token(v)


class FieldCondition(FieldRef):
    """A single field-state condition (pre- or postcondition of a state_gate).

    `established_by` is the load-bearing semantic distinction (only prose says who
    establishes a state -- codegen cannot infer it):
      - "hardware": hardware establishes the state; software can only observe
        it -> codegen emits a runtime check minting a STATE WITNESS.
      - "software": the driver itself must establish the state -> codegen
        emits a setup method minting an ACTION WITNESS, performed via
        `action_operation`.
    """
    state: Literal["cleared", "set", "equals"]
    values: list[int] = []            # non-empty iff state == "equals";
                                      # >1 entry = OR-of-values
    established_by: Literal["hardware", "software"] = "hardware"
    action_operation: Optional[Literal["write", "modify"]] = None
                                      # required iff established_by == "software"

    @field_validator("values", mode="before")
    @classmethod
    def _parse_values(cls, v):
        # Accept ints or hex/bin/dec strings; normalize to int here so no
        # value string ever survives into downstream consumers.
        if v is None:
            return []
        if isinstance(v, list):
            return [parse_value_token(item) for item in v]
        return v

    @model_validator(mode="after")
    def _consistent(self):
        if self.state == "equals" and not self.values:
            raise ValueError('state "equals" requires at least one entry in values')
        if self.state != "equals" and self.values:
            raise ValueError(f'values are only allowed with state "equals" (state={self.state!r})')
        if self.established_by == "software" and self.action_operation is None:
            raise ValueError('action_operation is required when established_by == "software"')
        if self.established_by == "hardware" and self.action_operation is not None:
            raise ValueError('action_operation is only meaningful when established_by == "software"')
        return self


class ConstraintBase(BaseModel):
    """Shared envelope of every v2 constraint kind."""
    kind: Literal["state_gate", "sequence", "write_once", "delay",
                  "read_effect", "clock_gate", "value_relation", "other"]
    severity: Literal["error", "warning"] = "error"
    consequence: str                  # what happens on violation (prose)
    datasheet_text: str               # VERBATIM, COMPLETE quote -- the anchor for
                                      # deterministic PDF verification


class StateGate(ConstraintBase):
    """An operation is permitted only while named field conditions hold.

    The workhorse kind (~all of today's true positives): UE=0 mode gates,
    hardware-flag gates (WUTWF=1), dual-established_by unlocks (IWDG), and the
    RTC-CNF pre+post software action.
    """
    kind: Literal["state_gate"] = "state_gate"
    target_register: str              # must equal the containing RegisterInfo --
                                      # deliberately redundant: a free consistency check
    target_fields: list[str] = []     # empty = whole register
    target_operation: Literal["read", "write", "any"]
                                      # Only the two bus operations a datasheet
                                      # actually constrains, plus "any" (sugar,
                                      # EXPANDED to read+write at collection).
                                      # svd2rust's modify() is NEVER a target: it
                                      # performs a read AND a write, so its
                                      # obligations are DERIVED as read + write
                                      # in the emitter. Datasheet prose "modify/
                                      # change a register" means writing it, so a
                                      # legacy "modify" is coerced to "write"
                                      # below.
    preconditions: list[FieldCondition]    # conjunctive
    postconditions: list[FieldCondition]   # software-established ONLY (validated below)

    @field_validator("target_operation", mode="before")
    @classmethod
    def _coerce_modify_to_write(cls, v):
        # Datasheets say "modify/modified/change" to mean "write the register",
        # not svd2rust's read-modify-write. Legacy data (and drift) used
        # target_operation="modify"; normalize it to "write" so the grammar
        # exposes only the read/write hazard axis. modify() gating is derived
        # (read + write) in rust_codegen, never declared here.
        if isinstance(v, str) and v.strip().lower() == "modify":
            return "write"
        return v

    @model_validator(mode="after")
    def _postconditions_software_only(self):
        # An observed-state (hardware-established) postcondition is unenforceable
        # -- it was PR 15's silently-dropped class. v2 rejects it loudly at
        # parse time; the v1->v2 conversion tool (convert_v1_to_v2.py) turns
        # such legacy postconditions into structured rejects instead.
        for i, pc in enumerate(self.postconditions):
            if pc.established_by != "software":
                raise ValueError(
                    f"postconditions[{i}]: observed-state (hardware-established) "
                    "postconditions are unenforceable and not representable; "
                    "reframe as a precondition of the hazardous next operation"
                )
        return self


class Sequence(ConstraintBase):
    """Ordered multi-step protocol (RTC_WPR 0xCA -> 0x53, GPIO LCKR lock, ...).

    The strongest linear-types fit: each generated step method consumes the
    previous step's token, so ordering is a pure type-level property.
    """
    kind: Literal["sequence"] = "sequence"
    steps: list[Step] = Field(min_length=2)   # collection rejects fewer
    enables: Optional[FieldRef] = None        # what the completed sequence unlocks


class WriteOnce(ConstraintBase):
    """Lock bits: "written once after reset" (EXTI_LOCKR.LOCK, TIM BDTR.LOCK).

    Enforced as a CAPABILITY: a non-Copy token minted once in the peripheral
    singleton, consumed by value; a second write is E0382.
    """
    kind: Literal["write_once"] = "write_once"
    target_register: str
    target_fields: list[str] = []
    reset_scope: Literal["system_reset", "power_cycle"]


class Duration(BaseModel):
    value: int
    unit: Literal["cycles_ahb", "cycles_apb", "us", "ms"]


class Delay(ConstraintBase):
    """Time/cycle wait after an operation ("wait two APB clock cycles ...").

    Hybrid enforcement: the ordering is compile-gated via a token, the
    duration is runtime. With no named dependent access (`before`) it degrades
    to a dynamic check.
    """
    kind: Literal["delay"] = "delay"
    after: Step                        # the operation that starts the clock
    duration: Duration
    before: Optional[FieldRef] = None  # the dependent access, if the text names one


class Effect(BaseModel):
    field: str
    becomes: Literal["cleared", "set"]


class ReadEffect(ConstraintBase):
    """Read side-effects (DSI_ISR cleared-on-read; USART_DR read clears RXNE).

    Documentation-only, but load-bearing metadata: it tells codegen when a
    checking read would itself perturb state (the self-defeating same-register
    read-gate case) and feeds the Constraint Validator.
    """
    kind: Literal["read_effect"] = "read_effect"
    read_register: str
    effects: list[Effect]


class ClockGate(ConstraintBase):
    """Peripheral clock must be enabled before any register access.

    Peripheral-scoped: collection deduplicates and hoists it to the peripheral
    entry in the manifest; enforcement is at the block accessor (handle), not
    per register.
    """
    kind: Literal["clock_gate"] = "clock_gate"
    clock: FieldCondition              # e.g. RCC_APB1ENR.I2C1EN state="set",
                                       # established_by="software", action_operation="modify"


class ValueRelation(ConstraintBase):
    """Inter-field value relationship ("CR2.FREQ must equal the APB1 frequency").

    The relation itself stays in datasheet_text -- an expression language would
    be unreliable for the LLM and unenforceable in the PAC. Always doc_only.
    """
    kind: Literal["value_relation"] = "value_relation"
    fields: list[FieldRef]             # the related fields


class Other(ConstraintBase):
    """Escape valve for genuine access/ordering requirements fitting no kind.

    NOT the destination for routed-out non-constraints (w1c, access-width,
    privilege, validity notes -- those emit nothing). doc_only BY CONSTRUCTION:
    can never gate an operation or break a build. Collection reports the
    other-rate per run -- a spike is a prompt regression; the steady-state rate
    is the grammar-coverage metric.
    """
    kind: Literal["other"] = "other"
    description: str                   # the requirement in the model's own words
    involved: list[FieldRef] = []      # SVD-validated like all refs


# The v2 constraint: discriminated union on `kind`. Unknown kinds fail parsing
# (collection turns that into a structured per-constraint reject).
ConstraintV2 = Annotated[
    Union[StateGate, Sequence, WriteOnce, Delay, ReadEffect, ClockGate,
          ValueRelation, Other],
    Field(discriminator="kind"),
]

# RegisterInfo.access_constraints_v2 forward-references ConstraintV2 (defined
# just above); resolve it now that the union exists. RegisterList nests
# RegisterInfo, so it must be rebuilt too.
RegisterInfo.model_rebuild()
RegisterList.model_rebuild()


Enforceability = Literal[
    "action_witnessed", "state_witnessed", "dynamic_check", "doc_only"
]


def derive_enforceability(constraint) -> Enforceability:
    """Derive the enforceability class of a v2 constraint.

    Computed, never LLM-emitted -- models would guess it. Deterministic from
    (kind, established_by, target refs). The two enforceable classes are BOTH
    compile-time witness-gated -- the operation will not compile without the
    witness -- and differ only in what produces the witness, NOT in whether
    enforcement is compile-time (both establish the condition at runtime):
      - "action_witnessed": the witness or capability is produced by the
        program's own actions or ordering, with no runtime observation of
        hardware. Software-established state gates (an action witness minted
        by an infallible setup action, no error path), sequences (each step
        mints the next step's token), write_once (a capability consumed by
        value), and clock gates (a one-time handle capability).
      - "state_witnessed": producing the witness requires a fallible runtime
        CHECK that observes hardware-controlled state (a state witness).
        Any hardware-established state-gate precondition; a delay whose
        dependent access is named.
      - "dynamic_check": a bare runtime check with no compile-time gate --
        a delay with no named successor (only the duration remains).
      - "doc_only": not enforceable in code (read_effect, value_relation,
        other, and vacuous gates).
    """
    kind = constraint.kind
    if kind == "state_gate":
        if not constraint.preconditions and not constraint.postconditions:
            # Vacuous gate (v1 corpus has 593): nothing to check, nothing to
            # gate — counting it as enforceable would inflate the paper
            # metric. It is documentation until re-extraction gives it
            # structure.
            return "doc_only"
        if any(p.established_by == "hardware" for p in constraint.preconditions):
            return "state_witnessed"
        return "action_witnessed"
    if kind in ("sequence", "write_once", "clock_gate"):
        return "action_witnessed"
    if kind == "delay":
        return "state_witnessed" if constraint.before is not None else "dynamic_check"
    # read_effect, value_relation, other
    return "doc_only"
