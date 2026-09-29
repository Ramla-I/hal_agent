This folder contains the documentation for an STM32F100 microcontroller. Look at what's here and decide how to approach the task.

**Goal: accuracy with efficiency.** Extract the information correctly while spending only as many tokens / as much compute as the task actually requires.

For **every hardware register**, extract two things:

1. **Register structure** — the register's address, reset value, size, and bit fields.
2. **Register access constraints** — every rule the manual states about *when or how* a register or field may be read, written, or modified (ordering, state gating, timing/delays, write-once, read side-effects, clock enable, inter-field value relations, etc.).

Extract only what the manual states — do not infer or invent values.

Write the results as **one JSON file per register** into a folder named `register_info_rm0041/` (create it in your working directory). Name each file `{peripheral}_{register}`, lowercase, with **no file extension** (e.g. `rcc_cr`, `adc1_cr1`, `gpioa_moder`) — exactly one register per file. Each file contains a single register object using the schema below (the peripheral and register are encoded in the filename, so they are not repeated inside the file). Use `[]` for `access_constraints_v2` when the manual states no access/ordering rule for that register.

**Output contract — this is the only thing that counts:**
- The **files on disk** in `register_info_rm0041/` are the sole deliverable. Register data described in a message (yours or a sub-agent's) counts for nothing — if it isn't written to a file, it does not exist.
- **If you delegate to sub-agents, each sub-agent must WRITE its own register files** directly into `register_info_rm0041/` as it goes. Do NOT have sub-agents return register JSON to you to write later — that output gets lost when the turn ends.
- **Do not finish while any register is unwritten.** Before you end, list `register_info_rm0041/`, compare the count and names against the registers in the SVD, and write any that are missing. Only produce your final summary once every register the SVD lists has its file on disk.

---

## Output schema (one file = one register object)

```json
{
  "datasheet_register_abbreviation": "<e.g. RCC_CR>",
  "address_offset": "<hex, e.g. 0x00>",
  "reset_value": "<hex, e.g. 0x00000083>",
  "size": 32,
  "subfields": [
    {
      "name": "<field name>",
      "description": "<short description>",
      "access": "<read-write | read-only | write-only | ...>",
      "bit_number": { "start_bit": <int>, "end_bit": <int> }
    }
  ],
  "access_constraints_v2": [ /* zero or more constraint objects, see below */ ]
}
```

Numeric values anywhere in constraints may be hex (`0x1A`), binary (`0b01`), or decimal (`7`).

### Constraint objects (grammar v2)

Every constraint has this shared envelope:

```json
{
  "kind": "<one of the eight kinds below>",
  "severity": "error",                     // or "warning"
  "consequence": "<what happens if the rule is violated, in prose>",
  "datasheet_text": "<VERBATIM, COMPLETE quote from the manual stating the rule>"
}
```

Plus, per `kind`, these extra fields:

- **`state_gate`** — an operation is allowed only while field conditions hold (the common case: e.g. "USART must be disabled (UE=0) to write this field"):
  `target_register`, `target_fields: []` (empty = whole register), `target_operation: "read" | "write" | "any"`, `preconditions: [FieldCondition]` (all must hold), `postconditions: [FieldCondition]` (software-established only).

- **`sequence`** — an ordered multi-step protocol (e.g. an unlock key sequence):
  `steps: [ Step, Step, ... ]` (≥2, in order), `enables: FieldRef | null` (what completing it unlocks).

- **`write_once`** — bit(s) writable only once after reset (lock bits):
  `target_register`, `target_fields: []`, `reset_scope: "system_reset" | "power_cycle"`.

- **`delay`** — a required wait after an operation:
  `after: Step` (the operation that starts the wait), `duration: { "value": <int>, "unit": "cycles_ahb" | "cycles_apb" | "us" | "ms" }`, `before: FieldRef | null` (the dependent access, if named).

- **`read_effect`** — reading a register changes state (e.g. clear-on-read):
  `read_register`, `effects: [ { "field": "<name>", "becomes": "cleared" | "set" } ]`.

- **`clock_gate`** — the peripheral clock must be enabled before any access:
  `clock: FieldCondition` (the enable bit, e.g. RCC_APB1ENR.I2C1EN).

- **`value_relation`** — a required relationship between fields (keep the relation itself in `datasheet_text`):
  `fields: [ FieldRef, ... ]`.

- **`other`** — a genuine access/ordering rule that fits none of the above:
  `description: "<the rule in your own words>"`, `involved: [ FieldRef ]`.

### Shared shapes referenced above

- **`FieldRef`**: `{ "register": "<name>", "field": "<name>", "whole_register": false }`
  For a whole-register reference, set `"field": ""` and `"whole_register": true`.

- **`FieldCondition`** = a `FieldRef` plus:
  `"state": "cleared" | "set" | "equals"`,
  `"values": [<int>, ...]` (only when `state == "equals"`; more than one entry means OR),
  `"established_by": "hardware" | "software"` (hardware = the driver only observes the state; software = the driver must set it),
  `"action_operation": "write" | "modify"` (required only when `established_by == "software"`).

- **`Step`**: `{ "register": "<name>", "operation": "write" | "read", "value": <int (optional, for writes with a prescribed value)> }`.

---

Keep working until **every** register in the SVD has its file written in `register_info_rm0041/` — do not end the run with registers still unwritten (no "N done, the rest remain" hand-off; finish them). When all files are on disk, your final message should just be a brief summary (e.g. how many registers you wrote). The files are the deliverable.
