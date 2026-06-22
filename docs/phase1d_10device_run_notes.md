# Phase 1d — 10-device stress run notes

Goal: run the bug-finding pipeline over 10 STM PDFs with max parallelism, recording
issues (rate limits, 503s, failures, timings) to drive code improvements afterward.

## Devices (10)
rm0091, rm0360, rm0490 (chunks pre-built) · rm0008, rm0033, rm0313, rm0316, rm0368, rm0451, rm0505 (preprocessed for this run).
Excluded rm0041/rm0090 (reserved for 1b/eval).

## Run config
- Retrieval: OpenEvolve (rm0041 program, default fallback).
- `--coverage-improver-iterations 0 --skip-validator --run-analyzer`.
- Generation model: gpt-oss-120b (Groq). Device-level parallelism via `--max-workers`.
- Retry/backoff (`responses_create_with_retry`) active on generator + analyzer.

## Preprocessing (offline / CPU-bound, no API)
_(filled in during the run)_

## Generation + analyzer (Groq — rate-limit surface)
_(filled in during the run)_

## Issues log
| Time (UTC) | Stage | Device | Issue | Notes |
|------------|-------|--------|-------|-------|

## Candidate code improvements

### HIGH — `derivedFrom` SVD instances silently dropped (recall)
STM SVDs define instance 1 with full `<registers>` and other instances as
`<peripheral derivedFrom="...">` (registers inherited, not repeated). Neither
`agent_tools/svd_parsing.get_register_names_for_peripheral` (generator input) nor
`applications/bug_finding/diff.parse_svd_registers` resolves `derivedFrom`, so all
derived instances get **0 registers** on both sides → never generated, never diffed.
Grounded on rm0091/stm32f0x1: i2c2=0, spi2=0, usart2..8=0 each, tim3/tim7/tim17=0
(only i2c1/spi1/usart1/tim1.. are checked). Precision-safe but big recall loss on
multi-instance (numbered-suffix) peripherals.
Fix: resolve `derivedFrom` — derived peripheral inherits the base's registers
(keep the derived name/baseAddress). Apply in BOTH parse paths (fold into the
shared register-IO helper per Issue #2).

### MEDIUM — generic vs. instance naming in retrieval (I2C vs I2C1)
Datasheets often title a section generically (`I2Cx_CR1` / `I2C_CR1`) while
retrieval queries the concrete instance (`I2C1_CR1`). The OpenEvolve program builds
`reg_key = "{peripheral}_{register}".upper()` and exact-match-boosts on it; the
generic heading misses the boost (only fuzzy embeddings help). No suffix
normalization in the OE path, keyword search, or metadata filter. The generator
prompt handles register-number templates with explicit ranges (BKP_DRx) but not
peripheral-instance generic naming; the analyzer only sees same-name value
mismatches so it's unaffected.
Fix: add a generic-alias fallback to retrieval queries + exact-match boost (strip
trailing digits from the peripheral → also try `I2C_`/`I2Cx_`), and add a prompt
note that instance N shares instance 1's layout.

