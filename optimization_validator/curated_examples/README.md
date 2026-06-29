# Curated examples (per manufacturer)

Human-curated, **datasheet-grounded** few-shot examples for the Validator's second pass —
created **once per vendor** and reused across that vendor's devices.

## Workflow
1. Run the validator baseline (pass 1) on a device of the vendor. It writes
   `curation_candidates_<model>.json` to the run folder — the Validator's false
   positives/negatives, each with the invariant, its **correct** label (`is_true`), and
   the ground-truth value.
2. Copy the instructive candidates into `<vendor>.json` here (schema below). For each,
   paste the **supporting datasheet excerpt** and a one-line **reasoning**. Drop the rest.
3. Re-run with `--curated-examples optimization_validator/curated_examples/<vendor>.json`.
   The examples (with their datasheet evidence) are injected into the prompt and the
   `summary_*` reports the baseline-vs-curated lift.

## Schema (`<vendor>.json`)
```json
{
  "examples": [
    {
      "peripheral": "usart1", "register": "sr", "field_name": "ne", "key": "access",
      "value": "read-write", "is_true": true,
      "datasheet_excerpt": "NE: noise error flag — rc_w0 (read, cleared by writing 0)",
      "reasoning": "rc_w0 is both readable and writable, i.e. access read-write"
    }
  ]
}
```
- `is_true` is the **correct** label the example teaches.
- Entries with an empty `datasheet_excerpt` are ignored (still un-curated).
- Keep the set small — each example is ~60–120 tokens on **every** call.
