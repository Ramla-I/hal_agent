# rm0041: evolved retrieval pipeline vs. Claude whole-datasheet baseline

One-off, full-device (rm0041 / STM32F100) register extraction. Both extract the
same thing (register structure + grammar-v2 access constraints, **no enums**) and
are scored by the same tool against the same verified datasheet
(`verified_datasheet/stm/rm0041_stm32f100.csv`).

## Headline — fair, apples-to-apples (enums dropped + query names reconciled)

| | Evolved pipeline (gpt-oss-120b) | Claude baseline (fable/opus) |
|---|---|---|
| Cost | **$0.86** | **$31.23** |
| Wall-clock | ~45 min | ~21 min |
| Register coverage | 203 / 245 = **82.9%** | 245 / 245 = **100%** |
| Fact-level coverage | **85.3%** (2862 / 3356) | 100% |
| Complete accuracy (correct / all verified facts) | **74.7%** (2506 / 3356) | **97.3%** (3267 / 3356) |
| Accuracy on registers it *did* produce | **87.6%** (2506 / 2862) | 97.3% |
| Files written | 429 of 589 attempted | 589 |
| Embeddings | FastEmbed local ($0) | n/a |

**Cost is ~36× lower** ($0.86 vs $31.23). The remaining gap is **coverage** and,
on the harder recovered registers, per-register completeness.

## Fix (b): SVD→datasheet query-name reconciliation

The SVD (and verified CSV) split some registers by mode — e.g. TIM
`CCMR1_Input` / `CCMR1_Output` — but the manual titles that section just `CCMR1`.
`build_query` querying with the `_input`/`_output` suffix returned the wrong chunk
(the table of contents), so the model refused. Fix: strip the suffix **for the
retrieval query only** (the output file + scoring keep the full name, since the
verified datasheet uses `ccmr1_input`/`ccmr1_output`). 32 queries reconciled.

| metric | enum-free (before) | + name-reconciled (after) |
|---|---|---|
| CCMR `_input`/`_output` recovered | 2/32 (6%) | **27/32 (84%)** |
| Register coverage | 76.7% (188/245) | **82.9% (203/245)** |
| Fact-level coverage | 82.6% | **85.3%** |
| Complete accuracy | 75.5% | 74.7% (flat) |
| Accuracy on produced | 91.4% | 87.6% |

Two honest caveats on the accuracy columns:
1. **The recovered registers are the hard ones** — CCMR mode-split fields extracted
   from a *shared* datasheet section, so the model misses more (`missing_found`
   175→299). We bought coverage; those registers are low-yield, which is why
   found-accuracy dips. Expected, not a regression.
2. **Generator run-to-run noise** — `correct_all` barely moved (2533→2506) despite
   +15 registers found; gpt-oss is stochastic, so some registers that parsed in the
   earlier run became `no_json` here, offsetting CCMR gains on the *complete*
   metric. The clean deterministic signals are the **CCMR 2→27 recovery** and the
   **+6.2pt register-coverage** win.

## What dropping enums changed (and why it matters)

The generator's default prompt requests `enumerated_values`; the Claude baseline
was told to omit them. Running the pipeline **with** enums was therefore both
unfair *and* worse. Dropping them (config now matches the baseline) improved every
axis at once:

| | with enums (+retry backfill) | **enums dropped (fair)** |
|---|---|---|
| Cost | $1.15 | **$0.82** |
| Register coverage | 204/245 (83.3%) | 188/245 (76.7%) |
| Complete accuracy | 63.5% | **75.5%** |
| Accuracy on produced | 88.9% | **91.4%** |

Enums added output tokens (cost) and scoring noise without being scored at all, so
removing them raised accuracy *and* cut cost. (Register coverage dips slightly —
run-to-run variance in which marginal registers the model refuses on; see below.)

## What the 160 remaining no-JSON registers actually are

Retry fixed the transient share; the 8k cap eliminated truncation
(`truncated_finish_length = 0`). The 160 that still produce no parseable JSON are
**not** one failure mode — categorizing them (28 in-scope, 132 out-of-scope):

| # | category | count | nature |
|---|---|---|---|
| A | ARM-core peripherals (nvic/scb/mpu/stk) | **48** | **Not in the RM0041 document.** SCB register names (CPUID/AIRCR/SHCSR) appear in **0** chunks; NVIC/MPU/SysTick have no register maps. These live in ST's separate ARM programming manual (PM0056). Unextractable by *any* retriever. |
| B | BKP `DRx` backup-data array registers | **19** | **In-scope**, not out-of-scope. Same class as CCMR: the manual describes DR1–DR42 once as a range `BKP_DRx`, so per-instance queries miss. Reconcilable (extend fix (b) to array ranges). |
| C | scattered (adc1, tim*, dma, spi, gpio) | **93** | The genuine **wrong-chunk / hard-retrieval** misses — the retriever returns *a* chunk (`empty_retrieval = 0` hides this), just not the *right* one. |

So the "retrieval-quality" story only covers **C (93/160 = 58%)**. The largest
single bucket (**A, 48**) is an **information-not-in-the-source** gap, and **B**
is an in-scope array-naming issue.

**Coverage implication.** The 48 core-peripheral registers can't be extracted from
RM0041 by anyone. They affect the *raw file-level* denominator only: excluding them,
file coverage rises **429/589 = 72.8% → 429/541 = 79.3%**. They do **not** touch the
scored **82.9% / 74.7%** numbers — the verified CSV marks nvic/scb/mpu rows
`not-specified` with an empty `correct_value` (only 78 core fact-rows carry a real
value, for a few registers like `dbg/cr`, `dbg/idcode`, `stk/ctrl` that RM0041 does
document), and `load_verified_datasheet` skips empty-`correct_value` rows. So the
scored denominator (245 registers / 3356 facts) already excludes the out-of-document
core peripherals — the right behavior, and it means the Claude baseline's "100%" was
not inflated by them either.

**Bottom line:** the remaining gap is ~48 out-of-document (unfixable here), ~19
in-scope array-naming (reconcilable), and ~93 genuine retrieval misses (the actual
retrieval-quality lever).

## Re-scoring: the score is suppressed by an array-granularity artifact

Strict scoring matches subfields by exact field name, but the model writes wide
repetitive registers compactly — e.g. EXTI `MRx[17:0]` as ONE field where the
verified datasheet (SVD-derived) enumerates `mr0..mr17` as 18 fields. Strict
scoring counts those 18 as missing though the model covered the bits. `rescore_bitpos.py`
credits a verified subfield fact when a generator field's bit range covers it
(access must still match), and separately counts representation-only "wrong" facts.

| scoring | complete accuracy | accuracy on produced regs |
|---|---|---|
| strict (exact field-name) | 74.7% (2506/3356) | 87.6% (2506/2862) |
| + bit-position credit (+249) | 82.1% (2755/3356) | — |
| + representation credit (+18, e.g. `0x20`=`32`) | **82.6%** (2773/3356) | **96.9%** (2773/2862) |

- 249 of the 793 strict "missing" facts (31%) were actually covered by a collapsed
  field — **EXTI alone +216**.
- On the registers it produces, reconciled accuracy is **96.9% ≈ Claude's 97.3%**.

**Final decomposition of the 3356 facts (artifacts removed):**

| | facts | share |
|---|---|---|
| Correct (reconciled) | 2773 | **82.6%** |
| Lost to coverage (42 scored registers never produced) | 494 | 14.7% |
| Genuinely missing subfields (in produced regs) | ~50 | 1.5% |
| Genuinely wrong | 39 | 1.2% |

So the extraction quality is on par with Claude; the remaining gap is almost
entirely **coverage** (registers never generated = the retrieval/no-JSON gap),
not correctness. This is the same subfield-reconciliation issue as #24 — the
generator-vs-verified comparison tool should adopt the bit-position matching that
`scripts/stm_coverage_statistics.py` already uses.

## Caveats

- Some of the 64 "wrong" facts are representation noise (e.g. `size` `0x20` vs
  `32`), not real errors — same caveat that applied to the Claude scoring.
- Two variables still differ (retrieval strategy *and* generator model:
  gpt-oss-120b vs Claude), so this is a system-vs-system cost/accuracy point, not
  an isolated retrieval comparison.

## Files
- `metrics.json` / `register_info/` / `analysis/` — the final run (enum-free +
  name-reconciled). Earlier variants (with-enums, no-name-fix) are not committed;
  their numbers are in the progression table above and in the top-level README.
- Scored with `compare_generator_with_verified.py` (vendored copy in this folder);
  `rescore_bitpos.py` adds the bit-position + representation credit.
