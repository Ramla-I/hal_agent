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
7 devices, `--backend local`, 3 concurrent. All rc=0. Per-device wall time:
rm0451 949s · rm0368 956s · rm0313 1140s · rm0505 1304s · rm0008 1352s · rm0316 1555s · rm0033 1638s.
Total wall ~60 min (06:23→07:23 UTC). Fully offline (FastEmbed local; enrichment
use_llm=False; no OpenAI upload on --backend local). Chunk counts 1036–1951.
Observation: preprocessing dominated by PDF→markdown chunking + local embedding;
this is the slow step, but it's embarrassingly parallel and API-free.

Host: 192 CPU, 376 GB RAM — local resources are NOT the bottleneck.

## Run topology decision (consequence of the OE-cache bug below)
`--max-workers >1` is unsafe with `--retrieval openevolve`, and even sequential
multi-device in one process is wrong, because the OE ephemeral DB is cached by
program path only (all 10 devices share program output_rm0041). So this run uses
**one device per Docker container, 10 containers in parallel** (process isolation
→ correct per-device OE DB; 10 concurrent Groq request streams = the stress).

## Generation + analyzer (Groq — rate-limit surface)
_(filled in during the run)_

### HIGH — OpenEvolve DB cache ignores chunks_dir (correctness, multi-device)
`context_retrieval/openevolve_search.py:_oe_cache` is keyed by resolved program
path only; `_ensure_database` returns the cached collection whenever it exists,
ignoring `chunks_dir`. Running multiple devices in one process with the same OE
program (the rm0041 default for all STM) makes devices 2..N retrieve against the
FIRST device's datasheet. Breaks s0 `--max-workers >1` AND sequential multi-device.
Fix: key the cache by `(program_path, chunks_index_csv)` (or chunks_dir).
Workaround used now: one device per process (separate containers).

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

