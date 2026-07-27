# The Register Structure Grammar

This document describes the **register structure grammar** — the small, closed
JSON schema the generator emits to describe *what a hardware register looks
like*: its address, its reset value, its width, and the named bit-fields
inside it. It is the extraction target of the project's first arm (recovering
register facts from a datasheet and checking them against the vendor's SVD
ground truth).

It is **not** the access-constraint grammar. Structure answers *"what does this
register contain?"*; the access-constraint grammar (grammar v2) answers *"when
may this register be read, written, or modified?"*. The two travel together in
the same JSON object — a register's constraints hang off the structure object
in the `access_constraints_v2` field — but the constraint grammar is specified
separately in
[`REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`](REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md)
and [`register_constraints_plan.md`](register_constraints_plan.md) (Appendix B).
This doc covers only the structure fields; it treats the constraint list as an
opaque payload and points you there.

- **Authoritative definition:** the Pydantic models in
  [`defs.py`](../defs.py) (`RegisterInfo`, `BitField`, `BitNumber`,
  `EnumValue`).
- **Prompt that instructs the LLM to emit it:**
  [`prompts/register_info_stm.py`](../prompts/register_info_stm.py).
- **On the wire:** one JSON object per register, saved as a file named
  `{PERIPHERAL}_{register}` under
  `agent_output/{mfr}/{device}/{run}/` (e.g. `I2C1_cr1`).

---

## The shape at a glance

One register is one `RegisterInfo` object:

```jsonc
{
  "datasheet_register_abbreviation": "I2C1_CR1",   // register name in the datasheet
  "address_offset": "0x00",                        // offset from the peripheral base, hex string
  "reset_value":    "0x0000",                      // value after reset, hex string
  "size":           16,                            // register width in bits
  "subfields": [                                   // the named bit-fields, in any order
    {
      "name":        "PE",                         // field name
      "description": "Peripheral enable",          // field description from the datasheet
      "access":      "read-write",                 // "read-only" | "write-only" | "read-write"
      "bit_number":  { "start_bit": 0, "end_bit": 0 },   // inclusive bit range, LSB = 0
      "enumerated_values": []                      // named values, or [] if none
    },
    {
      "name":        "START",
      "description": "Start generation",
      "access":      "read-write",
      "bit_number":  { "start_bit": 8, "end_bit": 8 },
      "enumerated_values": [
        { "value": "0", "name": "NoStart" },       // value (string) -> symbolic name
        { "value": "1", "name": "Start" }
      ]
    }
  ],

  // --- constraint payload (grammar v2; specified elsewhere) ---
  "access_constraints_v2": [ /* grammar-v2 objects */ ]
}
```

---

## Field reference

### `RegisterInfo` — one register

| Field | Type | Meaning |
|-------|------|---------|
| `datasheet_register_abbreviation` | string | The register's abbreviated name **as written in the datasheet**, usually peripheral + register (e.g. `I2C1_CR1`). This is the datasheet-side identity; SVD-side names are reconciled separately (see *Related models*). |
| `address_offset` | string | Offset of the register from its peripheral's base address, typically a hex string (`"0x00"`, `"0x24"`). |
| `reset_value` | string | The register's value immediately after reset, typically a hex string (`"0x0000"`). |
| `size` | integer | Register width in **bits** (commonly `8`, `16`, or `32`). |
| `subfields` | list of `BitField` | The named bit-fields inside the register. May be empty for a register the datasheet does not decompose. |
| `access_constraints_v2` | list of constraint objects | The access/ordering constraints (grammar v2) — an opaque payload here; see [`REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`](REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md). Empty (the default) when the datasheet states no access requirement. |

> The prompt instructs the model to emit `null` for `address_offset`,
> `reset_value`, or `size` when the datasheet does not state them, so consumers
> should tolerate a missing/`null` scalar even though the happy-path type is a
> string or integer.

### `BitField` — one bit-field (an entry in `subfields`)

| Field | Type | Meaning |
|-------|------|---------|
| `name` | string | Field name (e.g. `PE`, `START`). |
| `description` | string | Human-readable description from the datasheet (e.g. `"Peripheral enable"`). |
| `access` | string | One of `"read-only"`, `"write-only"`, `"read-write"`. A **reserved** field is treated as `"read-only"`. |
| `bit_number` | `BitNumber` | The bit range the field occupies (see below). |
| `enumerated_values` | list of `EnumValue` | Named/symbolic values for the field; `[]` when the field has none (e.g. a plain numeric or single-purpose bit). |

### `BitNumber` — a bit range

| Field | Type | Meaning |
|-------|------|---------|
| `start_bit` | integer | Low bit of the field. Bit numbering is **LSB = 0**. |
| `end_bit` | integer | High bit of the field. The range is **inclusive**. |

A single-bit field has `start_bit == end_bit` (e.g. `PE` occupies `{0, 0}`).
A multi-bit field spans the inclusive range, e.g. bits 15..12 → `{ "start_bit":
12, "end_bit": 15 }`.

### `EnumValue` — one enumerated value (an entry in `enumerated_values`)

| Field | Type | Meaning |
|-------|------|---------|
| `value` | string | The raw value the field takes, as a string (e.g. `"0"`, `"1"`). |
| `name` | string | The symbolic name for that value (e.g. `"NoStart"`, `"Start"`). |

---

## Conventions and rules

- **Numeric scalars are hex strings.** `address_offset` and `reset_value` are
  strings, normally hexadecimal with a `0x` prefix (`"0x00"`, `"0x0000"`), not
  integers.
- **`size` is a bit-width, not a byte count.** A 16-bit register has `"size":
  16`.
- **Bit ranges are LSB-0 and inclusive.** `{start_bit, end_bit}` names both
  endpoints; a single-bit field repeats the same index.
- **`access` is a closed three-value vocabulary** — `read-only`,
  `write-only`, `read-write` — with reserved fields folded into `read-only`.
- **Absent facts are `null`, not guessed.** When the datasheet does not give an
  offset, reset value, or size, the model is told to emit `null` rather than
  invent one.
- **`enumerated_values` is optional** and defaults to `[]`; most fields have
  none.
- **`access_constraints_v2` defaults to `[]`** — a register with no stated
  access/ordering rule.

---

## Worked example: I2C1 `CR1` (structure only)

The control register 1 of the I²C peripheral — a 16-bit register at offset
`0x00`, resetting to `0x0000`, whose bit 0 (`PE`) enables the peripheral and
whose bit 9 (`STOP`) requests a stop condition:

```json
{
  "datasheet_register_abbreviation": "I2C1_CR1",
  "address_offset": "0x00",
  "reset_value": "0x0000",
  "size": 16,
  "subfields": [
    { "name": "PE",   "description": "Peripheral enable",
      "access": "read-write", "bit_number": { "start_bit": 0, "end_bit": 0 },
      "enumerated_values": [] },
    { "name": "STOP", "description": "Stop generation",
      "access": "read-write", "bit_number": { "start_bit": 9, "end_bit": 9 },
      "enumerated_values": [
        { "value": "0", "name": "NoStop" },
        { "value": "1", "name": "Stop" } ] }
  ],
  "access_constraints_v2": [ /* the STOP/START/PEC write gate, grammar v2 */ ]
}
```

---

## How the grammar is produced and checked

1. **Produced.** The generator (`core/s1a_generator.py`) walks each peripheral
   and register named in the vendor SVD, retrieves the relevant datasheet
   context, and emits one `RegisterInfo` object per register.
2. **Compared to SVD ground truth.** Because SVD files are themselves
   structured register descriptions, the extracted structure is diffed against
   them field-by-field — peripheral / register / field coverage, plus the
   individual facts (`address_offset`, `reset_value`, bit ranges, `access`)
   compared as invariants (`evaluation/.../register_diff.csv`,
   `field_diff.csv`).
3. **Classified against the datasheet.** The validator
   (`core/s4_validator.py`) turns each extracted fact into an invariant and has
   an LLM search the datasheet to classify it true/false, so a disagreement
   with the SVD can be attributed to the extractor or to an SVD bug.

This is why the grammar is deliberately small and closed: every field is
either a scalar checkable against the SVD or a bounded list, with no free-text
values to drift.

---

## Related models

The same module defines a few auxiliary structure models used by the pipeline
around `RegisterInfo`:

| Model | Role |
|-------|------|
| `RegisterList` | A `{ "registers": [ RegisterInfo, ... ] }` wrapper for handling many registers at once. |
| `RegisterName` / `RegisterNameList` | Name reconciliation: maps a driver's register name, the datasheet register name, and the datasheet abbreviation to one another (the datasheet and SVD do not always agree on names). |
| `SectionInfo` | Where a peripheral's section lives in the datasheet — `peripheral_name`, `section_name`, `start_page`, `end_page`, and whether it exists — used to scope context retrieval. |

For the constraint half of the same JSON object, see
[`REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`](REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md)
(grammar v2 spec) and [`SVD2RUST_PAC_GUIDE.md`](SVD2RUST_PAC_GUIDE.md) (how
constraints become compile-time enforcement).
