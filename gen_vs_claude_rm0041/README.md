# Experiment: evolved extraction pipeline vs. a headless Claude agent (rm0041)

**Question.** For extracting register structure from a datasheet, is a purpose-built
retrieval+LLM **pipeline** better or worse than just pointing a general **headless
coding agent** (Claude Code) at the PDF? Compared on **cost** and **accuracy** on one
full device.

This folder holds **only what's needed to reproduce the experiment** plus this README.
The bulk per-register outputs, scored CSVs, and raw metrics/usage JSON are **generated,
not committed** (they're `.gitignore`d) — the results are recorded below and regenerable
from the scripts here.

---

## What was compared

Both systems extract the same thing — per-register structure (`address_offset`,
`reset_value`, `size`, and per-field `bit_offset`/`bit_width`/`access`) with
**enumerated values excluded** — and both are scored by the **same** tool against the
**same** verified datasheet.

- **Device:** rm0041 / STM32F100. Full device = **589 SVD registers**; the verified
  ground truth covers **245 registers / 3,356 facts**.
- **Ground truth / scorer:** `verified_datasheet/stm/rm0041_stm32f100.csv` +
  `pipeline/compare_generator_with_verified.py` (verbatim copy of the repo's
  `optimization/common/` scorer). `pipeline/rescore_bitpos.py` adds bit-position +
  representation credit (see Scoring below).

### Arm A — evolved pipeline (`pipeline/run_noenum_rm0041.py`)
- **Retriever:** the evolved OpenEvolve program
  `hal_agent-retrieval/openevolve_retrieval/v6_rm0041_seed42_labelfix/best/best_program.py`
  — local **FastEmbed** embeddings, ephemeral in-memory Chroma → **$0**, no API.
- **Generator:** `gpt-oss-120b` via Groq, **one focused call per register**.
- **Parameters (all in `run_noenum_rm0041.py`):**
  - `enumerated_values` **dropped** from the prompt (to match the Claude baseline).
  - **retry + exponential backoff:** `MAX_RETRIES=5`, `BASE_BACKOFF=2.0s`.
  - `max_completion_tokens=8000` (eliminates mid-JSON truncation).
  - **query-name reconciliation:** strip `_input`/`_output` from the *retrieval query*
    only (the manual titles the section `CCMR1`, not `CCMR1_Input`); the full name is
    kept for the output file + scoring.
  - Groq pricing used for cost: input **$0.15/M**, cached-input **$0.075/M**, output **$0.60/M**.

### Arm B — Claude headless baseline (`claude_baseline/prompt.md`)
- **Agent:** headless Claude Code — `claude-fable-5-1` orchestrator with `opus-5` and
  `haiku-4.5` sub-agents (the agent chooses its own model mix; not restricted).
- **Input:** only the rm0041 PDF + its SVDs; instructed to write one file per register.
- **Isolation:** Docker, work dir mounted only; network egress allow-listed to
  `api.anthropic.com`. Budget cap **$100**.
- **Prompt:** the exact task text is in `claude_baseline/prompt.md` (enums excluded,
  one JSON file per `{peripheral}_{register}`, grammar-v2 access constraints).
- (The Claude run harness — Dockerfile / run-docker.sh / settings — lived outside the
  repo at `~/rm0041_headless_baseline/`; only the prompt, a parameter, is kept here.)

---

## Results

### Cost & tokens
| | Pipeline (gpt-oss-120b) | Claude (opus+fable+haiku) |
|---|---|---|
| **Cost** | **$0.86** | **$31.23** |
| Wall-clock (generation) | ~45 min | ~21 min |
| Input tokens (uncached) | 1,401,659 | 4,418 |
| Cached input (read) | 2,323,200 | 14,252,545 |
| Cache-creation input | — | 1,547,176 |
| Output tokens | 793,654 | 485,208 |

Per-model Claude cost: **opus-5 $23.58 · fable-5-1 $7.65 · haiku-4.5 $0.003**. The
cost gap is driven by Claude's agentic context (~16M cache-read/-creation tokens from
re-reading the manual across turns/sub-agents) vs the pipeline's 589 targeted calls.
**Pipeline is ~36× cheaper.**

### Coverage & accuracy (of 245 verified registers / 3,356 facts)
| | Pipeline | Claude |
|---|---|---|
| Register coverage | 203 / 245 = **82.9%** | 245 / 245 = **100%** |
| Fact-level coverage | 85.3% (2,862 / 3,356) | 100% |
| Complete accuracy (strict) | 74.7% (2,506 / 3,356) | 97.3% (3,267 / 3,356) |
| **Complete accuracy (artifacts credited)** | **82.6%** (2,773 / 3,356) | 97.3% |
| **Accuracy on produced registers (credited)** | **96.9%** (2,773 / 2,862) | 97.3% |

### Scoring: strict → credited
Strict field-name matching **understates** the pipeline because it writes wide
repetitive registers compactly (EXTI `MRx[17:0]`) where the SVD-derived ground truth
enumerates every line (`mr0..mr17`). `rescore_bitpos.py` credits a subfield fact when
a generator field's bit range covers it (access must still match), and also credits
representation-only "wrong" (`size 0x20` vs `32`):

| scoring | complete accuracy |
|---|---|
| strict | 74.7% (2,506/3,356) |
| + bit-position credit (+249; EXTI +216) | 82.1% (2,755/3,356) |
| + representation credit (+18) | **82.6%** (2,773/3,356) |

**Takeaway.** The agent gives better *coverage* because it iterates over cached
context, but at ~36× the cost; **per-register extraction quality is on par** (96.9% vs
97.3% once the scoring artifact is removed). And a verified datasheet is required
either way to know accuracy. Full write-up: **`DISCUSSION.md`**.

---

## Files in this folder

```
gen_vs_claude_rm0041/
├── README.md                       # this file
├── DISCUSSION.md                   # paper-style write-up of the finding
├── claude_baseline/
│   └── prompt.md                   # the exact prompt the Claude agent was given
└── pipeline/
    ├── run_noenum_rm0041.py        # Arm A run driver (all parameters above)
    ├── compare_generator_with_verified.py  # the scorer (verbatim repo copy)
    └── rescore_bitpos.py           # bit-position + representation credit
```
Generated (`.gitignore`d, regenerate to reproduce): `pipeline/register_info/`,
`pipeline/analysis/`, `pipeline/metrics.json`, `claude_baseline/register_info_rm0041/`,
`claude_baseline/run.json`, `claude_baseline/summary.txt`.

## Reproduce

```bash
source .venv/bin/activate   # needs pandas etc.

# 1. Pipeline arm — regenerate register_info/ (needs GROQ_API_KEY + the evolved
#    retriever in the hal_agent-retrieval worktree, path hard-coded in the script):
python gen_vs_claude_rm0041/pipeline/run_noenum_rm0041.py     # writes register_info/ + metrics.json

# 2. Score it against the verified datasheet (writes ./analysis/):
cd gen_vs_claude_rm0041/pipeline && \
  PYTHONPATH=<repo> python compare_generator_with_verified.py \
    -v <repo>/verified_datasheet/stm/rm0041_stm32f100.csv register_info

# 3. Apply the bit-position + representation credit:
python gen_vs_claude_rm0041/pipeline/rescore_bitpos.py
```

The **Claude arm** is reproduced by running headless Claude Code on the rm0041 PDF+SVDs
with `claude_baseline/prompt.md` (model `claude-fable-5-1`, Docker-isolated, budget $100).

**Reproducibility boundary.** The numbers above are the recorded reference. Regenerating
the pipeline arm needs a `GROQ_API_KEY` and the evolved retrieval program (separate
worktree); regenerating the Claude arm needs an Anthropic key and the headless harness.
