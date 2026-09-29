# rm0041: evolved-pipeline vs. Claude whole-datasheet baseline

A one-off, full-device (rm0041 / STM32F100) comparison of two ways to extract
register structure + grammar-v2 access constraints from a datasheet:

- **Pipeline** — the evolved OpenEvolve retriever (local FastEmbed embeddings, $0)
  feeding `gpt-oss-120b` (Groq), one register at a time.
- **Claude baseline** — a headless Claude Code agent (`fable-5-1` orchestrating
  `opus`/`haiku`) given only the PDF + SVDs and told to write one file per register.

Both extract the same thing (**no enumerated values**), and both are scored by the
same tool (`optimization/common/compare_generator_with_verified.py`) against the
same verified datasheet (`verified_datasheet/stm/rm0041_stm32f100.csv`).

## Headline

| | Pipeline (gpt-oss-120b) | Claude baseline |
|---|---|---|
| **Cost** | **$0.86** | **$31.23** |
| Wall-clock (generation) | ~45 min | ~21 min |
| Register coverage | 203 / 245 = **82.9%** | 245 / 245 = **100%** |
| Complete accuracy (strict) | 74.7% (2506/3356) | 97.3% (3267/3356) |
| **Complete accuracy (artifacts credited)** | **82.6%** (2773/3356) | 97.3% |
| **Accuracy on registers it produced (artifacts credited)** | **96.9%** (2773/2862) | 97.3% |

**The pipeline is ~36× cheaper.** Once two scoring artifacts are removed (below),
its accuracy *on the registers it produces* is **96.9% ≈ Claude's 97.3%** — i.e.
extraction quality is on par; the remaining gap is almost entirely **coverage**.

## Token usage & cost

| | Pipeline (gpt-oss-120b) | Claude baseline (opus + fable + haiku) |
|---|---|---|
| Input tokens (uncached) | 1,401,659 | 4,418 |
| Cached input (read) | 2,323,200 | 14,252,545 |
| Cache-creation input | — | 1,547,176 |
| Output tokens | 793,654 | 485,208 |
| **Total cost** | **$0.86** | **$31.23** |

Per-model cost (Claude): **opus-5 $23.58** (412k output, 10.2M cache-read) +
**fable-5-1 $7.65** (73k output, 4.1M cache-read) + **haiku-4.5 $0.003**. Sources:
`pipeline/metrics.json` and `claude_baseline/run.json` (`modelUsage`).

The cost gap is driven by Claude's agentic context: ~16M cache-read/-creation input
tokens (an orchestrator re-reading the datasheet across many turns and sub-agents)
vs the pipeline's one focused call per register (589 calls, system prompt cached).
Token accounting differs by provider (Groq vs Anthropic cache semantics), so compare
the totals and cost, not line-by-line.

## Why strict scoring understates the pipeline (two artifacts)

1. **Array-granularity.** The model writes wide repetitive registers compactly —
   e.g. EXTI `MRx[17:0]` as ONE field — where the SVD-derived ground truth
   enumerates `mr0..mr17` as 18 fields. Strict field-name matching counts the
   un-enumerated lines as missing though the bits are covered. `rescore_bitpos.py`
   credits a verified subfield when a generator field's bit range covers it (access
   must still match): **+249 facts** (EXTI alone +216).
2. **Representation.** `size 0x20` vs `32` etc. show up as "wrong": **+18 facts**.

## What actually limits the pipeline (decomposition of the 3356 facts)

| | facts | share |
|---|---|---|
| Correct (artifacts credited) | 2773 | **82.6%** |
| Lost to **coverage** — 42 of 245 scored registers never produced | 494 | 14.7% |
| Genuinely missing subfields (in produced registers) | ~50 | 1.5% |
| Genuinely wrong | 39 | 1.2% |

The 42 un-produced scored registers (the `no_json` / wrong-chunk gap) are the real
lever. The 160 total un-produced files (of 589 SVD registers) break down as: **48**
ARM-core registers absent from RM0041 (nvic/scb/mpu/stk — documented in PM0056, not
this manual; unextractable by any retriever), **19** BKP `DRx` array registers
(in-scope; array-naming, reconcilable), and **93** genuine retrieval misses.

## How the experiment evolved

Only the **final** run's artifacts are committed, but here is the progression that
led to it (each row adds one change; register coverage = of 245 scored registers):

| stage | change | cost | reg. coverage | complete acc. |
|---|---|---|---|---|
| 1 | initial: enums on, single-shot (no retry) | $0.87 | 70.2% | 49.0% |
| 2 | + retry / backoff (no register dropped on a transient error) | $1.15 | 83.3% | 63.5% |
| 3 | + drop enums (apples-to-apples with Claude) + 8k token cap | $0.82 | 76.7% | 75.5% |
| 4 | **+ query-name reconciliation (FINAL)** | **$0.86** | **82.9%** | **74.7%** |
| — | *(scoring)* + bit-position + representation credit on stage 4 | — | — | **82.6%** |

Stage 3 dropped enums (cheaper *and* more accurate — enums cost tokens and add
scoring noise without being scored). Stage 4 fixed the retrieval query for mode-split
registers (`CCMR1_Input` → query `CCMR1`), recovering CCMR files 2/32 → 27/32. The
final scoring line removes the two artifacts (see below). `comparison.md` has the
full write-up with every caveat.

## Layout

```
gen_vs_claude_rm0041/
├── README.md                      ← this file (with the evolution above)
├── claude_baseline/               ← Claude results
│   ├── register_info_rm0041/      589 register JSON files
│   ├── run.json                   cost + model usage ($31.23; opus/fable/haiku split)
│   ├── summary.txt
│   └── prompt.md                  exactly what Claude was asked
└── pipeline/                      ← FINAL run only (enum-free + name-reconciled)
    ├── register_info/  metrics.json  analysis/     the final run's output + score
    ├── comparison.md              full write-up (progression + all caveats)
    ├── run_noenum_rm0041.py       ← the pipeline run driver, final config
    ├── compare_generator_with_verified.py  ← the scoring tool (verbatim repo copy)
    └── rescore_bitpos.py          ← the bit-position re-scorer (offline, reproducible)
```

The **measurement chain** is two scripts: `compare_generator_with_verified.py` scores
either output against the verified datasheet (produces `analysis/`), and
`rescore_bitpos.py` applies the bit-position + representation credit on top. The
comparison tool is a verbatim copy of `optimization/common/compare_generator_with_verified.py`;
it imports one repo helper (`utils.generator_facts`) and `pandas`, so run it with
`PYTHONPATH=<repo>`.

## The measurement script — all the updates we made

`pipeline/run_noenum_rm0041.py` is the final run driver and folds in every change
from this experiment:
- **enums dropped** from the generator prompt (matches the Claude baseline);
- **retry + exponential backoff** on the Groq call (transient errors no longer drop
  a register permanently);
- **8k completion-token cap** (eliminates mid-JSON truncation);
- **query-name reconciliation** — strip `_input`/`_output` for the *retrieval query*
  only (the manual titles the section `CCMR1`, not `CCMR1_Input`), while keeping the
  full name for the output file + scoring. Recovered CCMR files 2/32 → 27/32.

`pipeline/rescore_bitpos.py` applies the bit-position subfield credit + representation
credit and prints the 74.7% → 82.1% → 82.6% progression.

## Reproduce

```bash
# 1. Score the output against the verified datasheet (writes ./analysis/):
cd gen_vs_claude_rm0041/pipeline && \
  PYTHONPATH=<repo> python compare_generator_with_verified.py \
    -v <repo>/verified_datasheet/stm/rm0041_stm32f100.csv register_info
# (needs pandas + the repo's utils.generator_facts on PYTHONPATH)

# 2. Apply the bit-position + representation credit (offline, no API, no cost):
python gen_vs_claude_rm0041/pipeline/rescore_bitpos.py
```

**Reproducibility boundary.** `rescore_bitpos.py` and the comparison tool re-derive
every number here from the committed data (offline). Re-running the *pipeline itself*
(`run_noenum_rm0041.py`) additionally needs a `GROQ_API_KEY` and the evolved retrieval
program, which lives in a separate worktree
(`hal_agent-retrieval/openevolve_retrieval/v6_rm0041_seed42_labelfix/`) — its path is
hard-coded in `run_noenum_rm0041.py` and noted here so the run harness is documented
even though the retriever is not vendored into this folder.
