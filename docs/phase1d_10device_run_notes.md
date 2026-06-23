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
Topology: 10 containers, one device each, all in parallel. Start 19:26, end 20:23 UTC
(~57 min wall). Per-device wall: rm0313 844s, rm0490 950s, rm0505 979s, rm0091 1167s,
rm0316 1213s, rm0368 1285s, rm0451 2152s, rm0008 2297s, rm0360 2299s, rm0033 3440s.

**Outcome: 2/10 fully OK** (rm0360, rm0033). 8 "FAIL".
Review CSVs actually produced: rm0033 (122 bug rows), rm0091 (104; device still marked
FAIL — a later analyzer 429), rm0360 (4). The other 7 failed mid-generation, no CSVs
(gen files at failure: rm0490 3, rm0316 9, rm0313 20, rm0505 28, rm0368 90, rm0008 158,
rm0451 181).

### THE binding constraint: org-wide Groq TPM = 250,000 tokens/min
429 body: "Rate limit reached for model openai/gpt-oss-120b ... tokens per minute (TPM):
Limit 250000, Used 244765, Requested 12288. Please try again in 1.69272s."
- It's **tokens-per-minute, org-wide**, shared across all 10 containers — not RPM, not
  per-request capacity (the earlier rm0091 503 "over capacity" was a different, transient
  server-side issue).
- Each register request ≈ 12k tokens → only ~20 requests/min across the whole org. One
  device doing serial calls already approaches the cap; 10 in parallel saturate it
  continuously.
- The retry wrapper DID engage (traceback shows the 429 raised from
  `responses_create_with_retry` after exhausting 6 attempts). Its retries were invisible
  because they log at WARNING and config.LOG_LEVEL=ERROR.
- Exponential backoff total (~2+4+8+16+32 = 62s) < sustained saturation window, so under
  10× concurrency 8 devices exhausted retries and a single register's terminal 429
  aborted the ENTIRE device.

## Issues log
| Time (UTC) | Stage | Device | Issue | Notes |
|------------|-------|--------|-------|-------|
| ~19:30–20:23 | generate | rm0490, rm0313, rm0316, rm0368, rm0505, rm0008, rm0451 | 429 TPM exhausted retries → device FAIL mid-generation | org TPM 250k shared across 10 containers |
| ~20:xx | analyze | rm0091 | 429 on an analyzer call → device FAIL (CSVs already written) | 104 bugs still emitted before fail |
| n/a | generate | (all) | retry WARNING logs invisible (LOG_LEVEL=ERROR) | can't see throttling in run logs |

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

## Completion re-run (low concurrency) — confirms the TPM analysis
Re-ran the 8 incomplete devices at **-P2** (2 concurrent): **8/8 OK** (vs 8 FAIL at
-P10). Wall ~2h for 8 devices (TPM-bound regardless of worker count, as predicted).
**All 10 devices now complete: 21 review CSVs, 1,497 candidate bug rows**
(rm0490 513 across 6 SVDs, rm0008 285, rm0033 122, rm0316 116, rm0091 116, rm0313 101,
rm0505 89, rm0451 80, rm0368 71, rm0360 4). Takeaway: low concurrency is the reliable
setting today; the improvements below let higher concurrency work via more keys + overflow.

## Implemented improvements (this session)
- I1 config Groq key pool (GROQ_API_KEYS) + editable STAGE_MODELS per stage.
- I2 utils/llm.call_llm: key round-robin + retry honoring 429 retry-after + model
  overflow (Groq→OpenAI gpt-5-nano); analyzer routed to gpt-5-nano (off Groq).
- I3 per-register/batch failure isolation (skip+continue, summary at end).
- I4 OE ephemeral-DB cache keyed by (program, chunks) → s0 --max-workers correct.
- I5 derivedFrom resolution (shared resolve_peripheral_registers) → derived
  instances (i2c2, usart2..8, ...) now visible to generator + diff.
- I6 generic-vs-instance handling: prompt note + generic-stem retrieval fallback.

## FP-reduction work (J1–J4) + measured re-run (rm0091)
- J1 generator prompt: EXTRACTION_DISCIPLINE_NOTE (offset≠absolute, single-offset-not-range,
  0-indexed/MSB-left bit reading, width=end-start+1, null-not-placeholder).
- J2 deterministic pre-filter (`split_mechanical_fps`): not-found / absolute-address /
  range-formula / whole-register-scramble → routed out of the analyzer, kept in the CSV
  pre-marked `false_positive` with a reason.
- J3 evidence-aware analyzer: feed the generator's per-register datasheet reasoning into the
  analyzer prompt + FP-reject + conservative-on-structural rules.

**Measured re-run** (driver on rm0091 run 2's EXISTING generation, analyzer=gpt-5-nano):
| | BEFORE | AFTER |
|---|---|---|
| structural rows needing human review | 89 (75 bit_offset, 13 addr, 1 width) | **18 (all address_offset)** |
| auto-FP pre-marked (no review) | 0 | 264 (201 not-found, 60 scrambled, 3 absolute) |
| bit_offset/bit_width confirmed | 76 | **0** |

Big precision win: structural review burden −80%; bit-field FPs → 0.

**Limitation found (motivates next step):** of the 18 confirmed address_offset, `crc.init`
(0xC→0x10, ×3 SVDs) looks like a genuine SVD bug, but the **15 DMA `ccr/cndtr` offsets are
generator channel-offset miscalculations (FPs) that the analyzer still confirmed** — because
the evidence it sees is the generator's OWN reasoning, which rationalizes the wrong value.
→ Feeding generator reasoning catches "not-found"/unsupported cases but NOT confident generator
miscalcs. The stronger fix is to give the analyzer INDEPENDENT datasheet retrieval (re-retrieve
the register context) to verify against the raw datasheet, not the generator's narrative.

Caveat: this is new-analysis on OLD generation (pre-J1 prompt, pre-derivedFrom). The 201
not-found are largely derivedFrom instances the old generation never extracted. A clean A/B
needs regenerating rm0091 with the new prompt — recommended next.

## Remaining / optional
- A5 shared token-bucket limiter (sized to per-key TPM) for in-process concurrency
  self-pacing — not yet built; current approach is key pool + overflow + low -P.
- Re-run the 10 with the new path (multi-key + overflow + derivedFrom) to measure
  throughput gain and the now-larger bug set from derived instances.
- Paste 2 more Groq keys into .env GROQ_API_KEYS to realize ~3× TPM.

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

### HIGH — rate-limit handling can't survive org-wide TPM saturation
Root cause of 8/10 failures. Fixes, in priority order:
1. **Honor the server's retry hint.** The 429 body says "try again in 1.69272s" and
   responses carry a `retry-after` header; the wrapper does blind exponential backoff
   instead. Parse the hint/header and sleep that long (+ jitter). Far more efficient and
   would clear most TPM 429s in ~2s instead of failing.
2. **Bound concurrency to the TPM budget.** 250k TPM ÷ ~12k tokens/req ≈ 20 req/min
   org-wide. Total throughput is TPM-bound regardless of worker count, so high
   concurrency only adds 429 churn. Add a shared token-rate limiter, or document that
   safe concurrency is ~1–2 devices (and fix the OE-cache bug so `--max-workers` is
   usable in one process with a single shared limiter).
3. **Per-register failure isolation.** A single register's terminal 429 currently aborts
   the whole device, discarding the bug-finding step even though most registers were
   generated. Catch per-register, log + skip, continue; step 5 then runs on what exists.
4. **Bigger/visible retry budget.** Raise max_retries / total backoff for TPM; log
   rate-limit retries at a visible level (or raise default LOG_LEVEL to INFO for runs) so
   throttling is observable. Currently invisible (WARNING < ERROR).
5. **Resumability is the saving grace** — generation files persist, so failed devices
   resume on re-run. Worked as intended; combine with (1)–(2) to finish reliably.

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

