# constraint_validator

The Constraint Validator's package (roadmap step G, plan §7). This directory
holds the validator's **deterministic legs**; the LLM judge and the
corruption-calibration harness (§7.0 stage 1 / §7.2) arrive next and will
live alongside.

Every extracted constraint carries its own cited evidence
(`datasheet_text`), so verification decomposes (§7.1):

1. **Quote authenticity is deterministic** — implemented here
   (`quote_anchor.py`). No LLM is spent on a quote that cannot be grounded.
2. **Context is derived, never generated** — for anchored quotes the
   surrounding paragraphs are pulled programmatically from the chunked
   markdown. This is the judge's future input; it is trusted by
   construction and closes the selective-quoting blind spot.
3. **Encoding fidelity** then becomes a closed, local task for the judge
   (not yet in this package). **No semantic retrieval in the judging path.**

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

## Tests

```bash
.venv/bin/python -m pytest constraint_validator/tests/ -q
```

Synthetic chunk trees only — the real chunked datasheets
(`/home/ramla/hal_agent-phase-1d/chunked_datasheets/stm`, read-only) are
never touched by tests.
