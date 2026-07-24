# Register Access Constraint Grammar (v2)

This document specifies how datasheet access/ordering constraints — which SVDs
cannot express — are encoded for generating constraint-enforcing Rust PAC
(Peripheral Access Crate) code. It is the working copy of the normative spec in
`docs/register_constraints_plan.md` Appendix B; the Pydantic implementation
lives in `defs.py` (grammar v2 section), and collection lives in
`applications/pac_codegen/collect_constraints.py`.

All examples below are real, from the 30-reference-manual STM corpus.

## Purpose

Turn extracted datasheet constraints into compile-time enforcement inside PAC
crates: drivers that violate a hardware requirement fail to compile, with a
domain-specific diagnostic; the only bypass is `unsafe`.

## Terminology: witness tokens (reserved vocabulary)

The umbrella term is **witness tokens** — a token attests a *past observation
or action*, not a present guarantee (never "proof"). Four distinct roles,
never conflated:

| role | meaning | example |
| --- | --- | --- |
| **state witness** | minted by a runtime check of hardware-controlled state | `check_write_ready() -> Cr1WriteWitness` |
| **action witness** | minted by performing a required software action | `set_cnf() -> CnfSetWitness` |
| **obligation** | a duty to discharge (postcondition cleanup), `#[must_use]` | `-> CnfMustClearObligation` |
| **capability** | authority to do something at most once, consumed by value | `LckrWriteCap` (write_once) |

Reserved verbs, used consistently in this doc, `defs.py`, generated Rust, and
the paper:

- **validate** — the LLM pipeline judging extracted facts (s4 Validator,
  Constraint Validator). Never used for runtime code.
- **check** — the runtime inspection in generated code (`check_write_ready()`),
  which mints a witness. Not "verify", which reads as static/formal and
  collides with the Validator.
- **enforce** — what the compiler does at compile time (a missing witness is a
  compile error).

## Overall shape

A constraint is a **discriminated union on `kind`**: one tag from eight, then a
small kind-specific field set. Two shared objects are reused everywhere; there
are no free-text micro-grammars. Every vocabulary is a `Literal`, guaranteed at
collection-time Pydantic parsing (with per-constraint recovery); every
register/field name and numeric value is validated against the SVD at
collection when SVDs are available.

```python
# ── shared across all kinds (defs.py) ───────────────────────────
class ConstraintBase(BaseModel):
    kind: Literal["state_gate", "sequence", "write_once", "delay",
                  "read_effect", "clock_gate", "value_relation", "other"]
    severity: Literal["error", "warning"] = "error"
    consequence: str                  # what happens on violation (prose)
    datasheet_text: str               # VERBATIM, COMPLETE quote — the anchor for
                                      # deterministic PDF verification

class FieldRef(BaseModel):
    register: str                     # SVD-canonical name; resolved at collection
    field: str = ""                   # SVD-canonical; no ranges, wildcards, or
                                      # pseudo-fields; "" only with whole_register
    whole_register: bool = False      # explicit flag — never field=""

class FieldCondition(FieldRef):
    state: Literal["cleared", "set", "equals"]
    values: list[int] = []            # non-empty iff state == "equals";
                                      # >1 entry = OR-of-values; parsed from
                                      # hex/bin/dec strings, normalized to int
    established_by: Literal["hardware", "software"] = "hardware"
    action_operation: Optional[Literal["write", "modify"]] = None
                                      # required iff established_by == "software"
```

`values` accepts hex (`0x5555`), binary (`0b01`), or decimal strings, validated
by the regex `^(0x[0-9A-Fa-f]+|0b[01]+|\d+)$` and normalized to `int` — this
kills both the v1 OR-string drift (`equals:0b01|0b10|0b11`) and the
code-injection surface of splicing value strings verbatim into Rust.

`established_by` is the load-bearing semantic distinction (only the prose says who
establishes a state — codegen cannot infer it):

- `"hardware"` — hardware establishes the state; software can only *observe*
  it → codegen emits a runtime **check** minting a **state witness**.
- `"software"` — the driver itself must establish the state → codegen emits a
  setup method minting an **action witness**, performed via `action_operation`:
  `"modify"` (a read-modify-write that changes the needed bits and preserves the
  register's other bits — the usual choice, e.g. clearing one enable bit) or
  `"write"` (compose the whole register from its reset value, overwriting the
  other bits — only when the datasheet prescribes a specific whole-register
  value such as a key). This is a *method* choice for establishing a
  precondition and is distinct from `target_operation` (the constrained
  surface), where `"modify"` is not a value.

The `RegisterInfo` envelope carries `schema_version` (defaults to 1; existing
run files have no version field and are grammar v1).

## The eight kinds

### `state_gate` — the workhorse (~all of today's true positives)

An operation on a register/fields is permitted only while named field
conditions hold; optionally, conditions must be re-established afterward.

```python
class StateGate(ConstraintBase):
    kind: Literal["state_gate"]
    target_register: str              # must equal the containing RegisterInfo —
                                      # deliberately redundant: a free consistency check
    target_fields: list[str] = []     # empty = whole register
    target_operation: Literal["read", "write", "any"]
                                      # the two bus operations a datasheet
                                      # constrains, plus "any" (EXPANDED to
                                      # read+write at collection). Datasheet
                                      # prose "modify/change a register" means
                                      # WRITING it → encode as "write"; a legacy
                                      # "modify" is coerced to "write". svd2rust's
                                      # modify() is DERIVED (gated as read ∪
                                      # write) in the emitter, never a target.
    preconditions: list[FieldCondition]    # conjunctive
    postconditions: list[FieldCondition]   # software-established ONLY: an observed-state
                                           # postcondition is unenforceable → parse error
```

Mode-gate, software established_by (`rm0091/2/usart1_brr`, ×37): *"This register can
only be written when the USART is disabled (UE=0)."*

```json
{ "kind": "state_gate", "target_register": "USART_BRR", "target_fields": [],
  "target_operation": "write",
  "preconditions": [{ "register": "USART_CR1", "field": "UE", "state": "cleared",
                      "established_by": "software", "action_operation": "modify" }],
  "postconditions": [], "severity": "error",
  "consequence": "BRR writes while the USART is enabled are ignored or corrupt the baud rate",
  "datasheet_text": "This register can only be written when the USART is disabled (UE=0)." }
```

More real shapes:

- **Hardware-flag gate** (`rm0430/1/rtc_wutr`): *"This register can be written
  only when WUTWF is set to 1 in RTC_ISR"* — same shape with
  `established_by: "hardware"` (a check is emitted, not a setup method).
- **Dual-established_by unlock** (`rm0008/1/iwdg_pr`): `IWDG_PR` write requires
  `IWDG_KR == 0x5555` (software, whole-register value) **and** `IWDG_SR.PVU`
  cleared (hardware). The whole-register condition uses
  `"whole_register": true` — never `field: ""`.
- **Pre+post software action** (`rm0008/1/rtc_cnth` — the canonical fixture):
  F1 RTC config mode — set `RTC_CRL.CNF` before writing `CNTH/ALRH/…`, clear it
  after. Software-established_by precondition `CNF state="set"` plus
  software-established postcondition `CNF state="cleared"`, both
  `action_operation: "modify"`.
- **OR-valued equals** (legalized v1 drift): `required_state:
  "equals:0b01|0b10|0b11"` → `"state": "equals", "values": [1, 2, 3]`.

**Enforcement:** hardware preconditions → `state_witnessed` (composite
state witness from one fresh runtime check); software preconditions →
`action_witnessed` (action witness, no runtime check); postconditions →
obligation + closure-scoped wrapper, and
reframed as a precondition of the hazardous next operation where the text names
one. Gated via the trait bound (plan §3 / Appendix A).

### `sequence` — ordered multi-step protocols

```python
class Step(BaseModel):
    register: str
    operation: Literal["write", "read"]
    value: Optional[int] = None       # required for writes with prescribed values

class Sequence(ConstraintBase):
    kind: Literal["sequence"]
    steps: list[Step]                 # ≥ 2, in order (fewer fails parsing)
    enables: Optional[FieldRef] = None  # what the completed sequence unlocks
```

Examples: RTC write protection (`rm0383/1/rtc_dr`) — write `0xCA` then `0x53`
to `RTC_WPR`, enabling protected RTC registers (mangled in v1 into
`equals:0xCA then 0x53`); I2C ADDR clearing (`rm0033`) — read `SR1` then `SR2`
(two read steps); AES key order (`rm0493/1/aes_keyr7`); GPIO LCKR lock
(`rm0033/1/gpioi_lckr`); the two-word DBGMCU auth key.

**Enforcement:** `action_witnessed` — the strongest linear-types fit in the
grammar: each generated step method consumes the previous step's token
(`write_key1() -> Key1Written`, `write_key2(Key1Written) -> FlashUnlocked`), so
ordering is a pure type-level property; only the writes themselves run at
runtime, and there is no runtime check.
The terminal token is the witness required by the unlocked operation.

### `write_once` — lock bits

```python
class WriteOnce(ConstraintBase):
    kind: Literal["write_once"]
    target_register: str
    target_fields: list[str] = []
    reset_scope: Literal["system_reset", "power_cycle"]
```

Examples: `rm0493/1/exti_lockr` (*"This bit is written once after reset"*);
TIM `BDTR.LOCK` levels.

**Enforcement:** `action_witnessed` via a **capability**: a non-`Copy`
`LckrWriteCap` minted once in the peripheral singleton; the gated write
consumes it by value; a second write is E0382. Honest affinity — the datasheet
property *is* "at most once."

### `delay` — time/cycle waits

```python
class Duration(BaseModel):
    value: int
    unit: Literal["cycles_ahb", "cycles_apb", "us", "ms"]

class Delay(ConstraintBase):
    kind: Literal["delay"]
    after: Step                        # the operation that starts the clock
    duration: Duration
    before: Optional[FieldRef] = None  # the dependent access, if the text names one
```

Example: *"wait at least two APB clock cycles after enabling the peripheral
clock before accessing its registers."*

**Enforcement:** hybrid — codegen emits `wait_after_x() -> DelayElapsed` (dummy
reads / nop loop); the *ordering* is witness-gated at compile time via the
token (with a named successor, `state_witnessed`), the *duration* is a runtime
wait. With no named dependent access it degrades to `dynamic_check` (a bare
runtime wait, no compile-time gate).

### `read_effect` — read side-effects (documentation-only)

```python
class Effect(BaseModel):
    field: str
    becomes: Literal["cleared", "set"]

class ReadEffect(ConstraintBase):
    kind: Literal["read_effect"]
    read_register: str
    effects: list[Effect]
```

Examples: `rm0386/1/dsi_isr1` (*"always cleared after a read"* — misextracted
in v1 as 14 postconditions); USART_DR read clears RXNE.

**Enforcement:** `doc_only` — reads cannot usefully be forbidden, but this
metadata (a) feeds the Constraint Validator, (b) tells codegen when a checking
read would itself perturb state (the self-defeating same-register read-gate
case, rejected at codegen), and (c) where a real ordering obligation exists,
the decision tree routes the model to `sequence` instead.

### `clock_gate` — peripheral clock enable (the most common formerly-inexpressible constraint)

```python
class ClockGate(ConstraintBase):
    kind: Literal["clock_gate"]
    clock: FieldCondition              # e.g. RCC_APB1ENR.I2C1EN, state="set",
                                       # established_by="software", action_operation="modify"
```

Peripheral-scoped: the LLM may emit it on any register file of the peripheral;
collection deduplicates and hoists it to the peripheral entry in
`manifest.json`. Corpus established_by: `rm0008/1/rcc_ahbenr` (*"When the peripheral
clock is not active, the peripheral register values may not be readable … the
returned value is always 0x0"*).

**Enforcement:** `action_witnessed` at the **handle**, not per register (gating
every method is an unacceptable API tax): `rcc.enable_i2c1() ->
I2c1ClockEnabled`, and the I2C1 block accessor requires the token once —
mirroring the HAL `.constrain()` idiom while staying inside the PAC.

### `value_relation` — inter-field value relationships (documentation-only)

```python
class ValueRelation(ConstraintBase):
    kind: Literal["value_relation"]
    fields: list[FieldRef]             # the related fields; the relation itself stays
                                       # in datasheet_text — an expression language would
                                       # be unreliable for the LLM and unenforceable in the PAC
```

Examples: *"CR2.FREQ must equal the APB1 frequency in MHz"*; *"keep RXONLY
clear while BIDIMODE is set"* (`rm0454/1/spi1_cr1`). Always `doc_only`.

### `other` — escape valve and discovery queue

```python
class Other(ConstraintBase):
    kind: Literal["other"]
    description: str                   # the requirement in the model's own words (clustering)
    involved: list[FieldRef] = []      # SVD-validated like all refs
```

For *genuine access/ordering requirements that fit no kind* — corpus examples:
*"channel selection bits must remain unchanged during sample cycles"*
(`rm0008/1/adc2_smpr1`), *"do not make changes to this register after initial
programming"* (`rm0008/1/otg_fs_device_dcfg`). **Not** the destination for
routed-out non-constraints (w1c, access-width, privilege, validity notes —
those emit nothing). `doc_only` **by construction** — can never gate an
operation or break a build. Collection reports the **`other`-rate per
device/run**: a spike is a visible prompt regression, and the steady-state rate
is the grammar-coverage paper metric. This institutionalizes how
`sequence`/`clock_gate`/`write_once` were discovered (mining v1's 729
empty-pre/post constraints, ~347 of them real but inexpressible).

## Computed enforceability (never LLM-emitted)

At collection, each constraint gains an enforceability class — derived
deterministically by `defs.derive_enforceability` (models would guess it):

```python
enforceability: Literal["action_witnessed", "state_witnessed", "dynamic_check", "doc_only"]
```

`action_witnessed` and `state_witnessed` are **both compile-time
witness-gated** (the operation will not compile without the witness); they
differ only in what mints the witness — the program's own action/ordering/
capability (`action_witnessed`, no runtime check) vs a fallible runtime check
of hardware state (`state_witnessed`). This is not a compile-time-vs-runtime
distinction: both establish the condition at runtime.

| kind | derivation |
| --- | --- |
| `state_gate` | any hardware-established precondition → `state_witnessed`; all-software → `action_witnessed` |
| `sequence`, `write_once`, `clock_gate` | `action_witnessed` |
| `delay` | `state_witnessed` if `before` names the dependent access, else `dynamic_check` |
| `read_effect`, `value_relation`, `other` | `doc_only` |

Codegen records `enforced_as` (same enum) per constraint in `manifest.json`,
making downgrades visible. Paper metrics — fraction *classifiable* as
compile-enforceable and fraction *actually enforced* — are computed from
manifests, not hand counts.

## Collection rules (repair vs reject)

Implemented in `applications/pac_codegen/collect_constraints.py`.

**Repair deterministically (lossless, logged in `constraint_reports` and the
manifest):**

- hex/bin value strings → `int`;
- `target_operation: "any"` / `"read/write"` / `"read-write"` → the two
  bus-operation gates (read + write); legacy `"modify"` → `"write"`;
- `severity: "info"` → `"warning"`;
- v1 → v2 lift (table below);
- SVD-canonical name casing; enum *names* → values via SVD `enumeratedValues`
  (the `"enabled"` drift case; requires `--svd-dir`);
- v1 `field_name: ""` → explicit `whole_register: true`.

**Reject (judgment required; structured error `{file, constraint_index, field,
value, reason}`, enabling one automated re-prompt round, then per-constraint
drop with a manifest entry — NEVER aborting a peripheral):**

- unknown `kind` / `state` / `target_operation` / `severity`;
- `established_by: "software"` without `action_operation`;
- names unresolvable in the SVD (only checked when `--svd-dir` is given;
  otherwise registers carry the lint flag `svd_unchecked`);
- values exceeding field width (stage-0 lint, roadmap step E);
- `sequence` with < 2 steps;
- observed-state postconditions (unenforceable — PR 15's silently-dropped
  class, loud in v2);
- write constraints on SVD read-only fields (FP by construction; step E);
- `%s`-placeholder register names from run-dir filenames (`tim3_ccr%s`):
  flagged `placeholder_in_name` and rejected rather than guessing an expansion
  (the filename plumbing fix is roadmap step E, in `core/`).

**Routed out at the prompt (not constraints; emit nothing):** w1c/rc_w flag
semantics (SVD `modifiedWriteValues`), read-to-clear behavior standing alone
(→ `read_effect` if worth recording), access-width requirements,
secure/privileged-access notes, "value is don't-care" validity notes, reset
behavior.

## The decision tree (prompt)

> order of operations mentioned → `sequence` · wait/time → `delay` · "before
> any access"/clock enable → `clock_gate` · "once until reset" → `write_once` ·
> "reading clears/affects" → `read_effect` · a state condition on an operation
> → `state_gate` · pure value relationship → `value_relation` · a genuine
> requirement fitting none → `other` · not a requirement at all (w1c, width,
> privilege, validity note) → emit nothing.

## v1 → v2 lift (mechanical)

`defs.lift_v1_constraint(constraint, target_register) -> LiftResult` lifts one
v1 `RegisterAccessConstraint`; every v1 constraint is a `state_gate` by
construction (v1 could express nothing else — richer kinds only arrive via
re-extraction with the v2 prompt). It never raises on bad constraint content:
judgment-requiring drift becomes structured `LiftResult.rejects` entries
(`{field, value, reason}`), deterministic drift is repaired and logged in
`LiftResult.repairs`.

| v1 | v2 |
| --- | --- |
| `RegisterAccessConstraint` | `StateGate` |
| `FieldState.register_name` / `field_name` | `FieldCondition.register` / `field` |
| `field_name: ""` | `whole_register: true` (repair, logged) |
| `required_state: "cleared"` / `"set"` | `state: "cleared"` / `"set"` |
| `required_state: "equals:<v>"` | `state: "equals", values: [parse(v)]` |
| `required_state: "equals:A\|B\|C"` | `state: "equals", values: [A, B, C]` |
| `evidence_kind: "observed_state"` / `"software_action"` (absent → observed) | `established_by: "hardware"` / `"software"` |
| `target_operation: "any"` / `"read/write"` / `"read-write"` | expanded to read + write `state_gate`s |
| `target_operation: "modify"` | normalized to `"write"` (datasheet "modify" = write; `modify()` gating is derived as read ∪ write in the emitter) |
| `severity: "info"` | `"warning"` |
| observed-state postcondition | dropped with structured reject (gate survives) |
| unparseable `required_state` (`"unlocked"`, `"written"`, `"equals:X then Y"` …) | reject with reason → re-prompt round (most are `sequence`/`other` in v2) |

Value parsing applies the regex `^(0x[0-9A-Fa-f]+|0b[01]+|\d+)$` to each
`|`-separated part.

## v1 compatibility

**Grammar v1 remains the generator wire format until roadmap step F.** The v1
models (`FieldState`, `RegisterAccessConstraint`,
`RegisterInfo.access_constraints`) stay intact in `defs.py` and parse the
existing 30-RM corpus unchanged; the prompts keep emitting v1 until the prompt
v2 + extraction eval lands. Collection
(`applications/pac_codegen/collect_constraints.py`) bridges the two worlds: the
per-register output JSON keeps `access_constraints` (v1, consumed by today's
codegen) untouched and adds `access_constraints_v2` (lifted, with computed
`enforceability`) plus `constraint_reports` (repairs/rejects), and writes a
`manifest.json` with per-constraint kind/enforceability entries and run-level
`other`-rate / reject-rate metrics.

**Codegen support for v2 is phased** (plan §10): `state_gate` first (step B,
trait-bound gating), `sequence` + cross-register paths in step H,
`clock_gate`/`write_once`/`delay` later. `read_effect`, `value_relation`, and
`other` are documentation-only by construction and never gate an operation.
