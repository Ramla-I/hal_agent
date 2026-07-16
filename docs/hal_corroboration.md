# Corroboration analysis — are the HAL enforcement hits already handled?

**Date:** 2026-07-16
**Tool:** `applications/pac_codegen/experiments/corroboration.py`
**Question:** for every place the witness gate breaks an unmodified HAL crate,
does that HAL *already* perform the datasheet-prescribed check some other way?
The answer decides what each enforcement hit means: *corroboration* (the HAL
author knew the rule — independent confirmation, and a mechanical migration
site) versus *unchecked* (a candidate latent bug, and a potential upstream
report). Overlap is not redundancy — a hand-rolled runtime check protects one
HAL path; the type gate protects every consumer of the PAC crate — so this
classification changes the *claim*, never the decision to gate.

## Method

Three passes over all 34 enforcement hits (14 in stm32f4xx-hal 0.23.0, 20 in
stm32f1xx-hal 0.11.0; constraint = the I2C CR1 STOP/START/PEC rule):

1. **Deterministic scan** — does the enclosing function reference any
   precondition-field accessor before the flagged line?
2. **LLM judge** — the calibrated gpt-oss validator, closed-book: the
   constraint + quote + the enclosing function, verdict
   corroborated / unchecked / unclear.
3. **Human adjudication** of every disagreement (10 of 34).

## Results

| | f4 (14 hits) | f1 (20 hits) | total |
| --- | --- | --- | --- |
| scan and judge agree "unchecked" | 9 | 15 | 24 |
| disagreements (human-adjudicated) | 5 | 5 | 10 |

Adjudicated classification of all 34:

| final class | count | meaning |
| --- | --- | --- |
| **fully corroborated** (all three preconditions checked) | **0** | *no site in either HAL implements the complete rule* |
| **partially corroborated** (waits on STOP only; never START or PEC) | 10 | the rule was known — one third of it was implemented |
| **unchecked** | 24 | the constrained operation runs with no nearby precondition check |

The partial sites are unambiguous about author intent — stm32f4xx-hal even
carries the manual's reasoning as a comment directly above its STOP wait:

```rust
// Wait until a previous STOP condition finishes. ... It is possible that
// the STOP condition is still being generated when we reach here, so we
// wait until it finishes before proceeding to start a new transaction.
while self.i2c.cr1().read().stop().bit_is_set() {}
...
self.i2c.cr1().modify(|_, w| w.start().set_bit());
```

— a hand-written, STOP-only implementation of the sentence our pipeline
extracted. START and PEC are never checked anywhere in either HAL.

## The headline

**Zero of 34 real-world call sites implement the complete datasheet rule.**
Ten implement a third of it (the STOP wait); twenty-four implement none of
it. This is the strongest possible framing for the witnessed API: where HAL
authors knew the rule they encoded it partially and by hand; the generated
`check_write_ready()` performs the *complete, datasheet-derived* check, and
migrating a partial site actually deletes code (the hand-rolled wait loop is
subsumed by `write_when_ready`/`modify_when_ready`). The 24 unchecked sites
are candidate upstream reports once a human confirms each (the manual's own
"risk of a second STOP/START/PEC request" is the consequence text).

## Tool findings (why both methods run, and disagreements go to a human)

The two automated passes fail in **complementary** ways, both observed:

- the **scan over-credits**: writer proxies match field patterns
  (`w.start().set_bit()` *sets* START — it doesn't check it), and a
  function-level match can't distinguish full from partial checking;
- the **judge under-credits**: prompted for "the preconditions" (plural), it
  marked STOP-only waits as unchecked — defensible, but it buries the
  partial class; it was also the only method to see checks hidden behind
  helpers (`busy_wait_cycles!(self.wait_for_stop(), …)`), which the scan is
  blind to.

Refinement queued for the next iteration: give the judge a three-way
full / partial / none verdict with per-field attribution, which would have
matched the human adjudication on all 10 disagreements.

Run artifacts (per-hit JSONL incl. judge evidence lines):
`applications/pac_codegen/experiments/out/` (git-ignored; regenerate with the
tool — deterministic hits, judge at temperature 0).
