# constraint_validator

The Constraint Validator's package (roadmap step G, plan §7): the
deterministic quote-anchoring leg (§7.1), the LLM judge (§7.0 stage 1), and
the corruption-calibration harness (§7.2).

Every extracted constraint carries its own cited evidence
(`datasheet_text`), so verification decomposes (§7.1):

1. **Quote authenticity is deterministic** — `quote_anchor.py`. No LLM is
   spent on a quote that cannot be grounded.
2. **Context is derived, never generated** — for anchored quotes the
   surrounding paragraphs are pulled programmatically from the chunked
   markdown. This is the judge's input; it is trusted by construction and
   closes the selective-quoting blind spot.
3. **Encoding fidelity** is then a closed, local task for the judge
   (`judge.py`). **No semantic retrieval in the judging path.**

Terminology (plan §3): the LLM **validates**; runtime Rust **checks**; the
compiler **enforces**.

## quote_anchor.py

```bash
source .venv/bin/activate
python3 constraint_validator/quote_anchor.py \
    --csv verified_datasheet/constraints/stm.csv \
    --chunks /home/ramla/hal_agent-phase-1d/chunked_datasheets/stm \
    --out constraint_validator/out/anchors.jsonl \
    [--rm rm0008]
```

Per reference manual it assembles per-page text from the chunk files
(`{rm}_pNNN_cNN.txt`, merging the chunker's intra-page overlap), plus
adjacent-page joins so quotes spanning a page break still match. Matching is
performed in a normalized space (NFKC, curly quotes/dashes/soft hyphens to
ASCII, markdown emphasis/heading/table markers stripped — intra-word
underscores like `ADC_CR1` are preserved — lowercase, whitespace collapsed)
applied identically to both sides.

Match tiers per row:

- `exact` — normalized quote is a substring of a page (or page pair).
  Occurrences are counted; for multi-page boilerplate the page mentioning
  the row's own register is preferred, and `ambiguous` is flagged when >1
  page matches and none/multiple mention it.
- `fuzzy` — best `difflib.SequenceMatcher` ratio >= 0.85 over candidate
  windows (pages shortlisted via a token 5-gram index, then quote-length
  windows slid over only those pages and their boundary joins).
- `unanchored` — neither. The best ratio and best-guess pages are still
  recorded as deterministic triage hints (plan §7.1 allows aiding *human*
  triage; nothing here ever feeds the judge for unanchored rows).

For anchored rows the **context** is extracted from the ORIGINAL
(un-normalized) page text — the paragraph containing the match plus one
paragraph before and after, capped at 2,000 chars — by re-locating the match
via an offset-tracking normalizer.

### Output (JSONL, one object per attempted row)

| field | meaning |
| --- | --- |
| `id` | constraint row id from the CSV |
| `reference_manual` | rm0008 … rm0505 |
| `tier` | `exact` / `fuzzy` / `unanchored` |
| `ratio` | 1.0 for exact; best SequenceMatcher ratio otherwise (4 decimals) |
| `pages` | matched page number(s); best-guess page(s) for unanchored |
| `occurrences` | number of exact occurrences (0 for fuzzy/unanchored) |
| `ambiguous` | true when >1 page matches exactly and the register-mention heuristic cannot pick one |
| `context` | derived original-text context (only when anchored) |
| `quote_len` | length of the raw `datasheet_text` |

**Determinism:** same inputs produce a byte-identical JSONL (rows in CSV
order, sorted JSON keys, ASCII-escaped strings, fixed float format). Run
artifacts under `constraint_validator/out/` are git-ignored; the committed
summary of the real run lives in `docs/quote_anchoring_stats.md`.

## judge.py — the LLM judge (§7.0 stage 1)

Closed-book validation of every ANCHORED row (tier `exact`/`fuzzy`): the
judge sees only the verbatim quote, its derived context, and the structured
encoding — no retrieval, no file access. Model: `openai/gpt-oss-120b` via
Groq (env `GROQ_API_KEY`; the OpenAI SDK with `base_url` override). No
structured-output mode (Groq OSS models hard-error on `json_schema`) —
free-form completion plus robust JSON-block recovery (fenced or bare) with
one per-item repair retry.

```bash
python3 constraint_validator/judge.py \
    --anchors constraint_validator/out/anchors.jsonl \
    --csv verified_datasheet/constraints/stm.csv \
    --out constraint_validator/out/judgments.jsonl \
    [--limit 150 --sample-seed 7]   # deterministic stratified sample
    [--ids ids.txt]                 # or an explicit id list
    [--rows-jsonl corruptions.jsonl]  # judge pre-built rows instead
```

Per row the judge answers: **is_constraint** (does the quoted text state a
genuine access/ordering requirement, vs. descriptive behavior / flag
semantics / validity notes), **encoding_faithful** (do target register,
operation, fields, polarities, values match the text), and a **verdict**
`confirmed` / `encoding_error` / `not_constraint` with confidence and a
one-sentence reason. Output JSONL (sorted by id, deterministic bytes):
`{id, verdict, is_constraint, encoding_faithful, confidence, reason, model,
usage, parse_recovered}`.

Concurrency is a small thread pool (default 6) with exponential backoff on
429/5xx (Retry-After respected). **Blindness rule (plan §7.2):** the module
refuses to write output anywhere under `verified_datasheet/` — judge
verdicts must never sit near the human annotation file.

## corruption.py — known-bad variants for β (§7.2)

Generates corrupted encodings of anchored constraints; quote+context stay
byte-identical, so a competent judge must return `verdict != "confirmed"`.
Phase-1b realism lesson applied: corruptions stay in-distribution — sibling
fields are real names (same row's conditions or mined from other rows of the
same register in the CSV), values stay in-range (bit-length never exceeds
the original literal's width), retargets come from the same RM's rows.

| type | change |
| --- | --- |
| `flip_polarity` | `cleared` <-> `set` on one precondition |
| `swap_field` | precondition field replaced with a real sibling field |
| `change_operation` | `write` <-> `read` / `write` <-> `modify` |
| `perturb_value` | `equals:` value +/-1, in-range, style preserved |
| `retarget_register` | target register replaced with another from the same RM |

```bash
python3 constraint_validator/corruption.py \
    --anchors constraint_validator/out/anchors.jsonl \
    --csv verified_datasheet/constraints/stm.csv \
    --out constraint_validator/out/corruptions.jsonl \
    --per-type 30 --seed 20260716
```

Deterministic given `--seed` (per-row RNG keyed by seed+type+id); one
corruption type per variant; each record carries
`{id, corruption_type, original_id}` and is directly consumable by
`judge.py --rows-jsonl`.

## calibrate.py — the scorecard (§7.2)

Judges a deterministic stratified sample of originals plus the corruptions
and computes: corruption-detection rate (overall and per type), **flag rate
on originals** (explicitly *not* a false-positive rate — originals have no
human ground truth until the retrospective annotation lands), confidence
distributions, parse-recovery counts, token usage and estimated cost.

```bash
python3 constraint_validator/calibrate.py \
    --originals 150 --per-type 30 --seed 20260716 --concurrency 6
# artifacts -> constraint_validator/out/calibration/ (git-ignored)
```

The committed results of the real run live in
`docs/validator_calibration.md`.

## Tests

```bash
.venv/bin/python -m pytest constraint_validator/tests/ -q
```

Synthetic chunk trees only — the real chunked datasheets
(`/home/ramla/hal_agent-phase-1d/chunked_datasheets/stm`, read-only) are
never touched by tests. Judge tests inject a fake client: **no network in
tests.**
