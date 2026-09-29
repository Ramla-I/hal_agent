# Discussion: Why not just run a headless agent?

*Draft discussion section for the paper. Numbers are sourced from
`pipeline/metrics.json`, `claude_baseline/run.json`, and the scored `analysis/`
(see `README.md` and `pipeline/comparison.md`).*

A natural objection to a purpose-built extraction pipeline is that a general
headless coding agent, given the datasheet and the target register list, could do
the same job with far less engineering. To test this directly we ran both systems on
the same device (RM0041 / STM32F100), extracting the same targets (register structure
and grammar-v2 access constraints, enumerated values excluded from both), and scored
both with the same tool against the same verified datasheet. The pipeline paired the
evolved retriever (local embeddings, no API cost) with `gpt-oss-120b`, issuing one
focused call per register. The agent was Claude Code (an `opus`/`fable`/`haiku`
ensemble) given only the PDF and SVDs and instructed to write one file per register,
free to orchestrate sub-agents and iterate.

**The agent achieves higher coverage, and the mechanism is iteration over cached
context.** It produced a file for every register in the SVD (100%, versus 82.9% —
203/245 — for the single-shot pipeline). This is not because it extracts individual
registers more accurately, but because it can loop: it re-reads the datasheet across
many turns and sub-agents, cross-checks its output against the SVD register list, and
returns to fill gaps before terminating. The pipeline, by contrast, makes one
retrieval-and-extraction attempt per register and permanently misses those where
retrieval surfaces the wrong section. In effect the agent trades tokens for
coverage — and the token bill is exactly where the cost appears.

**That coverage costs roughly 36×.** The agent cost \$31.23 against the pipeline's
\$0.86. The gap is almost entirely agentic context overhead: the agent consumed ~16M
cache-read and cache-creation input tokens (an orchestrator repeatedly re-reading the
manual across turns and sub-agents) plus 485K output tokens, whereas the pipeline used
3.7M input tokens (2.3M served from cache) and 794K output tokens across 589 targeted
calls. The same iteration that buys the agent its last ~17 points of coverage is what
makes each run an order of magnitude more expensive.

**On the registers it does produce, per-register quality is essentially equal.** After
correcting a scoring artifact — the model expresses wide repetitive registers
compactly (e.g. EXTI `MRx[17:0]`) where the SVD-derived ground truth enumerates every
line (`mr0…mr17`), which naive field-name matching miscounts as missing — the
pipeline's accuracy on the registers it generated is 96.9%, against the agent's 97.3%.
The two systems therefore differ in *coverage*, not in *correctness*: when the pipeline
retrieves the right context, its extraction is as good as the agent's. This also flags
a methodological point for anyone benchmarking extraction against SVD-derived
references: strict field-name scoring systematically understates compact-but-correct
output, and bit-position reconciliation is needed for a fair comparison.

**Crucially, neither approach removes the need for a verified datasheet.** The agent
returns a complete, confident-looking set of register files, but nothing in that
output indicates *which* entries are correct — establishing that still required scoring
against human-verified ground truth. The verified datasheet was in fact load-bearing
twice over: it is what we used to tune and evolve the retriever, and it is the only
instrument by which either system's accuracy can be known. A headless agent thus shifts
the trade-off but does not escape it: it can buy higher coverage at ~36× the cost, yet
the correctness of its output remains exactly as unknowable, a priori, as the
pipeline's — verification is unavoidable in either case. (It is worth noting even the
"100%" coverage is relative to what the manual documents: registers for ARM-core
peripherals such as NVIC and SCB are specified in a separate programming manual, not
RM0041, and are correctly excluded from the scored set.)

**Takeaway.** The answer to "why not just run a headless agent" is: you can, and it
will give you better coverage because it iterates over cached input — but at roughly
an order-of-magnitude-plus higher cost, with no better per-register accuracy, and with
the same hard dependency on a verified datasheet to know whether the output is right.
The pipeline is preferable when cost scales with the number of devices and a
verification set exists to bound accuracy; the agent is attractive as a high-coverage,
higher-cost baseline or for one-off extraction where its price is acceptable.

## Threats to validity

- **Two variables move together.** This compares two *systems* (evolved retriever +
  `gpt-oss-120b` vs the Claude agent), so the retriever and the base model vary
  jointly, not in isolation; it is a system-vs-system operating point, not an ablation.
- **Single device, single run.** Results are for one device and one (stochastic) run.
  The ~36× cost ratio is robust, but the exact coverage and accuracy points carry
  per-run noise (e.g. `gpt-oss` occasionally returns no parseable JSON for a register
  that succeeds on a retry).

## Summary table

| | Pipeline (gpt-oss-120b) | Claude agent (opus+fable+haiku) |
|---|---|---|
| Cost | **\$0.86** | **\$31.23** (~36×) |
| Register coverage | 82.9% (203/245) | 100% (245/245) |
| Accuracy on produced registers (artifacts credited) | 96.9% | 97.3% |
| Total tokens (input / output) | 3.7M / 794K | ~15.8M cached-in + 4.4K in / 485K |
| Needs a verified datasheet to know accuracy? | Yes | Yes |
