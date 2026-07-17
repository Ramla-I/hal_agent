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
    vs_id_text: str
    vs_id_md: str
    
class FieldState(BaseModel):
    """Represents a field state requirement (pre or post condition).

    This is the GRAMMAR V1 wire format, still emitted by the generator prompts
    until roadmap step F. extra="allow" (instead of pydantic's default
    "ignore") retains PR-15-style optional keys (``evidence_kind``,
    ``action_operation``) when present in a run file, so the v1->v2 lift
    (``lift_v1_constraint`` below) can read them; parsing acceptance and
    serialization of the existing corpus (which has no extra keys) are
    unchanged.
    """
    model_config = ConfigDict(extra="allow")

    register_name: str  # Can be different register (e.g., "RTTDCS" when constraining "MTQC")
    field_name: str
    required_state: str  # "cleared", "set", "equals:<value>"

class RegisterAccessConstraint(BaseModel):
    """
    GRAMMAR V1 constraint on register/field access, enforced with witness tokens.

    Preconditions are enforced by consuming witness tokens.
    Postconditions are enforced by producing witness tokens (obligations) that
    must be consumed elsewhere.

    This remains the generator wire format until roadmap step F; the v2
    discriminated-union grammar below supersedes it for downstream consumers
    (see docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md). extra="allow" for the
    same lift-compatibility reason as FieldState.
    """
    model_config = ConfigDict(extra="allow")
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
    # Grammar v1 constraints. The v2-native generator (roadmap step F) keeps
    # this key present but ALWAYS EMPTY; v1-era run files still populate it
    # and are lifted at collection time (see
    # applications/pac_codegen/collect_constraints.py).
    access_constraints: list[RegisterAccessConstraint]
    # Grammar v2 constraints (the discriminated union defined below; forward
    # reference resolved by the model_rebuild() at the end of this module).
    # Default empty so every existing v1 run file parses unchanged. A register
    # is native-v2 when schema_version == 2 or this list is non-empty;
    # collection then skips the v1 lift and lints these objects directly.
    access_constraints_v2: list["ConstraintV2"] = []
    # Grammar version of the constraint wire format. Absent in every v1 run
    # file, so it defaults to 1; the v2-native generator stamps 2.
    schema_version: int = 1

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


# ---------------------------------------------------------------------------
# Register-constraint grammar v2
# ---------------------------------------------------------------------------
# Normative spec: docs/register_constraints_plan.md Appendix B (summarized in
# docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md). A constraint is a discriminated
# union on `kind`; every vocabulary is a Literal so drift is rejected at
# collection-time pydantic parsing rather than spliced into generated Rust.
#
# Terminology (reserved verbs, plan section 3): the LLM pipeline VALIDATES
# extracted facts; generated code CHECKS hardware state at runtime, minting
# WITNESS tokens; the compiler ENFORCES that witnesses are presented. Four
# token roles: state witness (minted by a runtime check of hardware state),
# action witness (minted by performing a required software action), obligation
# (a duty to discharge -- postcondition cleanup), capability (authority to do
# something at most once -- write_once).
#
# The v1 models above stay intact: the generator emits v1 until roadmap step F,
# and lift_v1_constraint() below lifts the existing corpus mechanically.


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
    target_operation: Literal["read", "write", "modify", "any"]
                                      # "any" legal at extraction; EXPANDED to
                                      # per-operation gates at collection
    preconditions: list[FieldCondition]    # conjunctive
    postconditions: list[FieldCondition]   # software-established ONLY (validated below)

    @model_validator(mode="after")
    def _postconditions_software_only(self):
        # An observed-state (hardware-established) postcondition is unenforceable
        # -- it was PR 15's silently-dropped class. v2 rejects it loudly at
        # parse time; the lift converts such v1 postconditions into structured
        # rejects instead (see lift_v1_constraint).
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
    "compile_gate", "witnessed_runtime_check", "dynamic_check", "doc_only"
]


def derive_enforceability(constraint) -> Enforceability:
    """Derive the enforceability class of a v2 constraint.

    Computed, never LLM-emitted -- models would guess it. Deterministic from
    (kind, established_by, target refs):
      - state_gate: any hardware-established precondition needs a runtime check
        minting a state witness -> "witnessed_runtime_check"; all-software
        preconditions are pure action-witness ordering -> "compile_gate".
      - sequence / write_once / clock_gate: pure token ordering/capability ->
        "compile_gate".
      - delay: ordering is compile-gated only if the text names the dependent
        access (`before`); otherwise only the duration remains ->
        "dynamic_check".
      - read_effect / value_relation / other: "doc_only" by construction.
    """
    kind = constraint.kind
    if kind == "state_gate":
        if not constraint.preconditions and not constraint.postconditions:
            # Vacuous gate (v1 corpus has 593): nothing to check, nothing to
            # gate — counting it as compile-enforceable would inflate the
            # paper metric. It is documentation until re-extraction gives it
            # structure.
            return "doc_only"
        if any(p.established_by == "hardware" for p in constraint.preconditions):
            return "witnessed_runtime_check"
        return "compile_gate"
    if kind in ("sequence", "write_once", "clock_gate"):
        return "compile_gate"
    if kind == "delay":
        return "witnessed_runtime_check" if constraint.before is not None else "dynamic_check"
    # read_effect, value_relation, other
    return "doc_only"


# ---------------------------------------------------------------------------
# v1 -> v2 lift (mechanical, per the B.6 table)
# ---------------------------------------------------------------------------

class LiftReject(BaseModel):
    """Structured rejection produced by the lift (never an exception).

    `field` names the offending v1 field (e.g. "preconditions[0].required_state"),
    `value` is its verbatim value, `reason` is a stable machine-readable tag.
    These feed the collection manifest and the one automated re-prompt round.
    """
    field: str
    value: str
    reason: str


class LiftResult(BaseModel):
    """Outcome of lifting ONE v1 constraint.

    constraints: zero or more v2 constraints ("any"/"read/write" operations
        expand to one per operation; a rejected constraint yields zero).
    rejects: structured errors. If `constraints` is empty and `rejects` is
        non-empty the whole constraint was rejected; if both are non-empty,
        individual conditions were dropped (observed-state postconditions)
        while the remaining gate survived.
    repairs: human-readable log of deterministic, lossless repairs applied.
    """
    constraints: list[ConstraintV2] = []
    rejects: list[LiftReject] = []
    repairs: list[str] = []


# v1 target_operation -> v2 per-operation expansion (B.6). Missing keys are
# unknown vocabulary -> reject ("clear", "access", ...).
_V1_OPERATION_LIFT = {
    "write": ["write"],
    "read": ["read"],
    "modify": ["modify"],
    "any": ["read", "write", "modify"],
    "read/write": ["read", "write"],
    "read-write": ["read", "write"],
}

# v1 evidence_kind -> v2 established_by (B.6). v1 corpus files lack evidence_kind
# entirely (it was a PR-15 addition) -> default "hardware", matching the v1
# reading that a bare condition is observed state.
_V1_EVIDENCE_LIFT = {
    None: "hardware",
    "observed_state": "hardware",
    "software_action": "software",
}


def _lift_required_state(required_state: str):
    """Parse a v1 required_state string into (state, values).

    "cleared"/"set" pass through; "equals:<v>" and the OR drift
    "equals:A|B|C" parse each |-separated part with parse_value_token.
    Raises ValueError on anything else ("unlocked", "written",
    "equals:0xCA then 0x53", "equals:output", ...) -- the caller converts
    that into a structured reject, since repairing these needs judgment
    (most are sequence/other in v2, reachable only via re-prompt).
    """
    rs = required_state.strip()
    if rs == "cleared" or rs == "set":
        return rs, []
    if rs.startswith("equals:"):
        parts = [p.strip() for p in rs[len("equals:"):].split("|")]
        return "equals", [parse_value_token(p) for p in parts]
    raise ValueError(f"unparseable required_state {required_state!r}")


def _lift_field_state(fs: FieldState, where: str, rejects: list, repairs: list):
    """Lift one v1 FieldState to a FieldCondition.

    Returns the FieldCondition, or None after appending a LiftReject. `where`
    is the v1 path prefix for reject entries (e.g. "preconditions[0]").
    """
    try:
        state, values = _lift_required_state(fs.required_state)
    except ValueError:
        rejects.append(LiftReject(
            field=f"{where}.required_state",
            value=fs.required_state,
            reason="unparseable_required_state",
        ))
        return None

    evidence_kind = getattr(fs, "evidence_kind", None)
    if evidence_kind not in _V1_EVIDENCE_LIFT:
        rejects.append(LiftReject(
            field=f"{where}.evidence_kind",
            value=str(evidence_kind),
            reason="unknown_evidence_kind",
        ))
        return None
    established_by = _V1_EVIDENCE_LIFT[evidence_kind]

    action_operation = getattr(fs, "action_operation", None)
    if established_by == "software":
        if action_operation not in ("write", "modify"):
            # B.4 reject: established_by "software" without a usable action_operation.
            rejects.append(LiftReject(
                field=f"{where}.action_operation",
                value=str(action_operation),
                reason="software_evidence_without_action_operation",
            ))
            return None
    elif action_operation is not None:
        # Only meaningful with software established_by; dropping it is lossless.
        repairs.append(
            f"{where}: dropped action_operation={action_operation!r} "
            "(only meaningful with software established_by)"
        )
        action_operation = None

    # The v1 corpus encodes whole-register conditions as field_name="" (e.g.
    # the IWDG_KR==0x5555 unlock). v2 makes that explicit.
    whole_register = fs.field_name == ""
    if whole_register:
        repairs.append(f"{where}: empty field_name lifted to whole_register=true")

    return FieldCondition(
        register=fs.register_name,
        field=fs.field_name,
        whole_register=whole_register,
        state=state,
        values=values,
        established_by=established_by,
        action_operation=action_operation if established_by == "software" else None,
    )


def lift_v1_constraint(c: RegisterAccessConstraint, target_register: str) -> LiftResult:
    """Lift one v1 RegisterAccessConstraint to grammar-v2 StateGate(s).

    Implements the B.6 table exactly. Every v1 constraint is a state gate by
    construction (v1 could express nothing else); richer kinds (sequence,
    write_once, ...) only arrive via re-extraction with the v2 prompt.
    Never raises for bad constraint content -- judgment-requiring drift becomes
    structured LiftReject entries; deterministic drift is repaired and logged.

    `target_register` is the authoritative register name from the containing
    RegisterInfo (datasheet_register_abbreviation); it is stamped into the
    lifted gates so the deliberately-redundant target_register consistency
    check has a trusted side.
    """
    rejects: list = []
    repairs: list = []

    # severity: "info" -> "warning" (B.6); anything off-vocabulary is judgment.
    severity = c.severity
    if severity == "info":
        repairs.append('severity "info" repaired to "warning"')
        severity = "warning"
    elif severity not in ("error", "warning"):
        rejects.append(LiftReject(
            field="severity", value=str(c.severity), reason="unknown_severity"))
        return LiftResult(rejects=rejects, repairs=repairs)

    # target_operation: expand "any"/"read/write"/"read-write"; reject unknowns.
    operations = _V1_OPERATION_LIFT.get(c.target_operation)
    if operations is None:
        rejects.append(LiftReject(
            field="target_operation", value=str(c.target_operation),
            reason="unknown_target_operation"))
        return LiftResult(rejects=rejects, repairs=repairs)
    if len(operations) > 1:
        repairs.append(
            f"target_operation {c.target_operation!r} expanded to "
            f"per-operation gates: {', '.join(operations)}"
        )

    if c.target_register != target_register:
        repairs.append(
            f"target_register normalized from {c.target_register!r} to "
            f"{target_register!r} (containing register is authoritative)"
        )

    # Preconditions: all-or-nothing. Dropping one would silently WEAKEN the
    # gate (enforce less than the datasheet requires), so any unliftable
    # precondition rejects the whole constraint.
    preconditions = []
    for i, fs in enumerate(c.preconditions):
        cond = _lift_field_state(fs, f"preconditions[{i}]", rejects, repairs)
        if cond is None:
            return LiftResult(rejects=rejects, repairs=repairs)
        preconditions.append(cond)

    # Postconditions: software-established only survive (B.2.1). Observed-state
    # postconditions are unenforceable -- PR 15 dropped them silently; the lift
    # drops them LOUDLY (structured reject) while keeping the still-sound
    # precondition gate. An unparseable postcondition state rejects the whole
    # constraint, same as preconditions.
    postconditions = []
    for i, fs in enumerate(c.postconditions):
        n_rejects_before = len(rejects)
        cond = _lift_field_state(fs, f"postconditions[{i}]", rejects, repairs)
        if cond is None:
            reason = rejects[-1].reason if len(rejects) > n_rejects_before else ""
            if reason == "unparseable_required_state":
                return LiftResult(rejects=rejects, repairs=repairs)
            continue  # element-level drop (e.g. software without action_operation)
        if cond.established_by != "software":
            rejects.append(LiftReject(
                field=f"postconditions[{i}]",
                value=f"{fs.register_name}.{fs.field_name} {fs.required_state}",
                reason="observed_state_postcondition_unenforceable",
            ))
            continue
        postconditions.append(cond)

    constraints = [
        StateGate(
            target_register=target_register,
            target_fields=list(c.target_fields),
            target_operation=op,
            preconditions=[p.model_copy(deep=True) for p in preconditions],
            postconditions=[p.model_copy(deep=True) for p in postconditions],
            severity=severity,
            consequence=c.consequence,
            datasheet_text=c.datasheet_text,
        )
        for op in operations
    ]
    return LiftResult(constraints=constraints, rejects=rejects, repairs=repairs)
