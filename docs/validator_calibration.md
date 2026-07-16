# Validator calibration run — LLM judge vs corruption harness

**Date:** 2026-07-16
**Model:** `openai/gpt-oss-120b` via Groq (temperature 0, no structured-output
mode — free-form completion + JSON-block recovery; plan §6 rationale)
**Tools:** `constraint_validator/judge.py`, `corruption.py`, `calibrate.py`
(plan §7.0 stage 1 + §7.2 corruption harness for β)
**Inputs:** the 3,789 quote-anchored rows (tier `exact`/`fuzzy` of
`constraint_validator/out/anchors.jsonl`, from
`verified_datasheet/constraints/stm.csv`) with their derived contexts —
closed-book: the judge saw only quote + context + structured encoding. No
retrieval anywhere in the judging path (plan §7.1).
**Artifacts:** `constraint_validator/out/calibration/` (git-ignored:
`corruptions.jsonl`, `judgments_originals.jsonl`,
`judgments_corruptions.jsonl`, `scorecard.json`).

> Blindness rule (plan §7.2): no judge verdict appears in or near
> `verified_datasheet/constraints/stm.csv`; `judge.py` structurally refuses
> to write under `verified_datasheet/`. The human annotation, whenever it
> proceeds, must not be anchored by the machine's labels.

## Sample design

- **150 originals** — deterministic stratified sample (seed `20260716`) of
  the anchored rows: round-robin across all 30 reference manuals (exactly 5
  per RM), and within each RM round-robin across constraint *shapes*
  (operation × precondition-count bucket × postcondition bucket × carries an
  `equals` value). Shape stratification deliberately over-represents rare
  and pathological shapes relative to the corpus (see caveats).
- **150 corruptions** — 30 per type over the same anchored pool
  (`corruption.py`, same seed; 5 per RM, all 30 RMs). Corrupted rows keep
  the ORIGINAL quote + context byte-identical; only the encoding changes,
  one corruption per variant. Realism rules (plan §7.2 / Phase-1b lesson):
  sibling fields are real names mined from the same row or the same
  register's other rows, values stay in-range (bit-length ≤ the original
  literal's width), operation swaps stay in vocabulary, retargets come from
  the same RM's rows.
- A **detected corruption** = `verdict != "confirmed"` (an
  `encoding_error` *or* `not_constraint` verdict counts as a catch).

## Scorecard

### Corruption detection (the β leg — known-bad by construction)

| corruption type | detected | rate | verdicts |
| --- | ---: | ---: | --- |
| `flip_polarity` | 30/30 | **100%** | 29 encoding_error, 1 not_constraint |
| `perturb_value` | 30/30 | **100%** | 29 encoding_error, 1 not_constraint |
| `swap_field` | 28/30 | **93.3%** | 27 encoding_error, 1 not_constraint, 2 confirmed |
| `retarget_register` | 27/30 | **90.0%** | 20 encoding_error, 7 not_constraint, 3 confirmed |
| `change_operation` | 23/30 | **76.7%** | 21 encoding_error, 2 not_constraint, 7 confirmed |
| **overall** | **138/150** | **92.0%** | |

`change_operation` splits sharply by direction — the misses are almost all
the semantically adjacent swap:

| direction | detected |
| --- | ---: |
| read → write | 7/7 |
| write → read | 11/12 |
| write → modify | 5/11 |

A `modify` performs a write, so "software may write this bit only when …"
prose genuinely licenses a `modify` encoding; the write→modify corruption is
close to semantically benign (trait-gated codegen would still gate the
modify surface, plan §3). Counting only the semantically substantive
corruptions (excluding write↔modify), overall detection is 133/139
(**95.7%**).

### Flag rate on originals

**This is a flag rate, NOT a false-positive rate.** The originals carry no
human ground truth until the retrospective annotation of
`verified_datasheet/constraints/stm.csv` accumulates (plan §7.2 — annotation
is async and never blocking). A flagged original may be a judge error *or* a
real extraction defect; the corpus is known to contain both (plan §5.1
estimated ~75–80% true positives by manual sample).

| | |
| --- | ---: |
| originals judged | 150 |
| `confirmed` | 59 (39.3%) |
| `encoding_error` | 74 (49.3%) |
| `not_constraint` | 17 (11.3%) |
| **flag rate** | **60.7%** |

The headline number is inflated by the shape stratification, which is a
feature for coverage but makes the sample deliberately unrepresentative:

- The corpus-dominant shape — `write` **with** preconditions, 2,472/3,789
  (65%) of anchored rows — was flagged at **3/12 (25%)** in the sample,
  consistent with the plan's ~75–80% true-positive estimate.
- Rows with **empty** encodings (no pre/postconditions) were flagged at very
  high rates (write: 27/35; read: 25/30): the judge marks an encoding that
  captures none of the quoted requirement as unfaithful. These are exactly
  the §5.1 "expressiveness losses" the grammar-v2 kinds exist to recover —
  the flags are working as intended, not misfiring.
- Off-vocabulary operations (`read/write`, `any`, `access`, `clear`) were
  flagged at 19/19 — stage-0 lint (plan §7.0) will already normalize or
  reject these before the judge ever sees them.

### Confidence, parsing, cost

- **Confidence is not a useful separator at temperature 0:** mean 0.96 on
  detected corruptions vs 0.96 on missed ones; 0.97 on confirmed originals
  vs 0.95 on flagged ones; nearly everything lands in 0.90–0.98. Do not
  threshold on it without recalibration.
- **Parsing:** 0 parse failures; 7/300 items needed the one-shot repair
  retry (`parse_recovered`), all succeeded. No `json_schema` mode was used
  (Groq OSS models hard-error on it).
- **Usage:** 479,927 tokens (358,178 in / 121,749 out), 307 API calls,
  estimated **$0.145** at Groq list prices ($0.15/M in, $0.75/M out —
  adjust in `calibrate.py` if pricing changes).
- **Wall time:** 69.6 s total at concurrency 6 (~35 s per 150-item batch);
  no rate-limit stalls (wall time shows no backoff waits).

## Example judgments (verbatim)

**1. Confirmed original** — `031eca5f4b74` (rm0402 `spi4.txcrcr`, read gate
on `SPI_SR.BSY` cleared; quote: *"A read to this register when the BSY Flag
is set could return an incorrect value."*):

```json
{"verdict": "confirmed", "is_constraint": true, "encoding_faithful": true,
 "confidence": 0.96, "parse_recovered": false,
 "reason": "The text requires the BSY flag to be cleared before reading the register, which matches the encoded precondition."}
```

**2. Caught corruption** — `02acd9da096d-flip_polarity` (rm0410
`gpioi.lckr`; original precondition `LCKK cleared` flipped to `LCKK set`;
quote: *"These bits are read/write but can only be written when the LCKK bit
is 0."*):

```json
{"verdict": "encoding_error", "is_constraint": true, "encoding_faithful": false,
 "confidence": 0.98, "parse_recovered": false,
 "reason": "The text requires LCKK to be cleared (0) before writing LCK bits, but the encoding incorrectly requires it to be set."}
```

**3. Missed corruption** — `fd8259378953-retarget_register` (rm0383: target
retargeted from `rtc.wutr` to `rtc.alrm%sr`; quote kept: *"This register can
be written only when WUTWF is set to 1 in RTC_ISR."*):

```json
{"verdict": "confirmed", "is_constraint": true, "encoding_faithful": true,
 "confidence": 0.98, "parse_recovered": false,
 "reason": "The quoted note explicitly requires WUTWF to be set before writing the register, which matches the encoded precondition."}
```

The miss is structural, not sloppy: the quote is self-referential ("This
register…") and never names its register, so nothing in the closed-book
input contradicts the retarget. Retarget detection depends on the quote or
derived context naming the target — the two other retarget misses have the
same shape ("The registers are not accessible in write mode when…").

## Honest caveats

1. **No human ground truth on originals yet.** The 60.7% flag rate cannot be
   read as a false-positive rate (either direction) until annotated rows
   from `annotate_constraints.py` accumulate and α is measured
   retrospectively (plan §7.2). β from corruptions is the only calibrated
   number here.
2. **Corruption detection is a lower-bound proxy for β, on *synthetic*
   errors.** Real extraction errors (selective quoting, invented conditions)
   may be easier or harder than these five types. Two structural blind spots
   surfaced: self-referential quotes hide `retarget_register`, and
   write↔modify is semantically adjacent. One realism artifact cuts the
   other way: a sibling swap occasionally lands on a *text-consistent*
   field (`I2SMOD`→`I2SE` under "configured when the I2S is disabled";
   `BSY`→`BUSY` is a near-alias mined from another row's extraction) — such
   "misses" are not clearly judge errors.
3. **Single model, single prompt, bounded sample** (150+150; ±~5% at 95%
   confidence on the overall detection rate). No cross-model comparison was
   run (the OpenAI-platform comparison is Ramla's, later).
4. **Confidence values are unusable as-is** (see scorecard) — filter on
   verdicts, not confidence.
5. The shape-stratified originals sample intentionally over-weights rare
   shapes; corpus-level flag rate must be measured on the full run or a
   proportional sample.

## Reproduce

```bash
source .venv/bin/activate

# prerequisite (if constraint_validator/out/anchors.jsonl is absent; ~5 min):
python3 constraint_validator/quote_anchor.py \
    --csv verified_datasheet/constraints/stm.csv \
    --chunks /home/ramla/hal_agent-phase-1d/chunked_datasheets/stm \
    --out constraint_validator/out/anchors.jsonl

# the calibration run reported above (GROQ_API_KEY required):
python3 constraint_validator/calibrate.py \
    --anchors constraint_validator/out/anchors.jsonl \
    --csv verified_datasheet/constraints/stm.csv \
    --out-dir constraint_validator/out/calibration \
    --originals 150 --per-type 30 --seed 20260716 --concurrency 6
```

Sampling and corruption generation are deterministic given the seed; judge
verdicts are near-deterministic (temperature 0) but not guaranteed
byte-stable across provider updates.

### Scaling to the full corpus

```bash
# all 3,789 anchored rows (~25x this run: ~$1.9, ~15 min at concurrency 6):
python3 constraint_validator/judge.py \
    --anchors constraint_validator/out/anchors.jsonl \
    --csv verified_datasheet/constraints/stm.csv \
    --out constraint_validator/out/judgments.jsonl

# larger corruption set (e.g. 100 per type):
python3 constraint_validator/corruption.py --per-type 100 --seed 20260716 \
    --out constraint_validator/out/corruptions_100.jsonl
python3 constraint_validator/judge.py \
    --rows-jsonl constraint_validator/out/corruptions_100.jsonl \
    --out constraint_validator/out/judgments_corruptions_100.jsonl
```

If Groq rate limits bite at scale, lower `--concurrency` (the built-in
backoff honors `Retry-After`); keep the sample size.
