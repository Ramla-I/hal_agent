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
_(filled in after the run)_
