# Quote-anchoring run — verified-constraints datasheet vs chunked markdown

**Date:** 2026-07-16
**Tool:** `constraint_validator/quote_anchor.py` (deterministic; plan §7.1)
**Inputs:** `verified_datasheet/constraints/stm.csv` (4,160 rows, 30 reference
manuals) matched against the chunked markdown at
`/home/ramla/hal_agent-phase-1d/chunked_datasheets/stm/{rm}/chunks/md/`.
**Output:** `constraint_validator/out/anchors.jsonl` (git-ignored run
artifact; byte-reproducible from the inputs above).

> These results are **machine-derived** (string matching only). They may
> inform annotation triage — e.g. `unanchored` rows are natural
> `quote_missing` candidates — but **no LLM verdicts are involved anywhere
> in this file or the JSONL** (blindness rule, plan §7.2: the human label
> must not be anchored by the machine's).

## Coverage

| | |
| --- | --- |
| RMs in CSV | 30 |
| RMs with chunked markdown | **30 / 30** (no gaps) |
| Rows attempted | **4,160 / 4,160** |
| Runtime | 283.6 s single-threaded (~4 m 44 s wall) |

## Tier breakdown

| tier | rows | % | meaning |
| --- | ---: | ---: | --- |
| `exact` | 3,253 | 78.2% | normalized quote is a substring of a page (or adjacent-page join) |
| `fuzzy` | 536 | 12.9% | best SequenceMatcher ratio >= 0.85 over candidate windows |
| `unanchored` | 371 | 8.9% | no match — quote cannot be grounded in the manual |

- **Anchored (exact + fuzzy): 3,789 rows (91.1%)**, every one carrying a
  derived original-text context (paragraph containing the match ± one
  paragraph, capped at 2,000 chars; median 381 chars, max 1,990).
- **Boilerplate:** 1,378 exact rows match more than once, 1,115 of them on
  more than one page. The register-mention heuristic resolved 496 of the
  multi-page rows to the page naming the row's own register (context is
  taken from that page); the remaining **619 are flagged `ambiguous`**
  (none or several matched pages mention the register).
- Exact matches spanning a page break via the adjacent-page join: 0 — page
  header lines interrupt cross-page text in the markdown, so genuine spans
  surface in the `fuzzy` tier instead (working as designed).
- Normalizer disagreements (fast vs offset-tracking path): 0.

## Per reference manual

| rm | rows | exact | fuzzy | unanchored | ambiguous |
| --- | ---: | ---: | ---: | ---: | ---: |
| rm0008 | 80 | 58 | 14 | 8 | 10 |
| rm0033 | 90 | 72 | 9 | 9 | 17 |
| rm0038 | 101 | 72 | 19 | 10 | 8 |
| rm0091 | 234 | 177 | 36 | 21 | 34 |
| rm0313 | 76 | 61 | 9 | 6 | 7 |
| rm0316 | 78 | 59 | 10 | 9 | 10 |
| rm0360 | 63 | 50 | 10 | 3 | 6 |
| rm0365 | 103 | 91 | 4 | 8 | 11 |
| rm0366 | 75 | 62 | 7 | 6 | 10 |
| rm0367 | 140 | 107 | 16 | 17 | 32 |
| rm0368 | 70 | 58 | 4 | 8 | 9 |
| rm0376 | 140 | 107 | 20 | 13 | 32 |
| rm0377 | 119 | 90 | 21 | 8 | 11 |
| rm0383 | 76 | 57 | 9 | 10 | 9 |
| rm0385 | 151 | 121 | 19 | 11 | 21 |
| rm0386 | 278 | 192 | 54 | 32 | 46 |
| rm0390 | 110 | 87 | 13 | 10 | 18 |
| rm0394 | 131 | 105 | 13 | 13 | 19 |
| rm0401 | 79 | 53 | 17 | 9 | 6 |
| rm0402 | 106 | 73 | 17 | 16 | 15 |
| rm0410 | 313 | 258 | 31 | 24 | 43 |
| rm0430 | 224 | 169 | 34 | 21 | 48 |
| rm0431 | 142 | 121 | 11 | 10 | 17 |
| rm0434 | 269 | 232 | 21 | 16 | 47 |
| rm0444 | 153 | 120 | 21 | 12 | 19 |
| rm0451 | 84 | 60 | 14 | 10 | 8 |
| rm0454 | 103 | 81 | 16 | 6 | 12 |
| rm0490 | 133 | 105 | 14 | 14 | 30 |
| rm0493 | 372 | 300 | 44 | 28 | 56 |
| rm0505 | 67 | 55 | 9 | 3 | 8 |
| **total** | **4,160** | **3,253** | **536** | **371** | **619** |

## Example unanchored rows (annotation-triage seeds)

First 80 chars of `datasheet_text`; best fuzzy ratio and best-guess page are
recorded in the JSONL as deterministic near-miss hints for *human* triage
(never fed to the judge).

| id | rm | best ratio | quote (first 80 chars) |
| --- | --- | ---: | --- |
| `606441e95df0` | rm0008 | 0.72 | `This bit should read a logic 0 before writing to ETH_MACMIIAR and ETH_MACMIIDR. ` |
| `fb709bb3234a` | rm0033 | 0.73 | `This bit should read a logic 0 before writing to ETH_MACMIIAR and ETH_MACMIIDR. ` |
| `9b49dbf2981d` | rm0038 | 0.70 | `The Option key register is write accessible only after the good write sequence h` |
| `b13c583652d6` | rm0091 | 0.67 | `This register can only be accessed by the software when the CAN hardware is in i` |
| `8ae94234e8d3` | rm0313 | 0.72 | `TXEOM must be set before writing transmission data to TXDR. TXSOM must be set wh` |

Spot-checks show the unanchored population is dominated by quotes the
generator stitched or paraphrased rather than copied verbatim — ellipsis
joins (`RTC_CNT registers ... are write-protected`), inserted parentheticals
(`while this bit (TEF) is set`), and reworded clauses — i.e. exactly the
evidence-fidelity failures the deterministic anchor exists to catch
(plan §7.1: no match → the constraint dies, no LLM spent).

## Reproduce

```bash
source .venv/bin/activate
python3 constraint_validator/quote_anchor.py \
    --csv verified_datasheet/constraints/stm.csv \
    --chunks /home/ramla/hal_agent-phase-1d/chunked_datasheets/stm \
    --out constraint_validator/out/anchors.jsonl
```

Same inputs → byte-identical JSONL (rows in CSV order, sorted keys, fixed
float format).
