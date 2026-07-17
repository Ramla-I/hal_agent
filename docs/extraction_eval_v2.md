# Extraction eval — grammar-v2 prompt (roadmap step F)

**Date:** 2026-07-17
**Model:** `openai/gpt-oss-120b` via Groq (temperature 0, free-form JSON — no `json_schema` mode, per the tiered schema-enforcement decision, plan §6.1)
**Harness:** `optimization/generator/extraction_eval_v2.py` over the committed golden sample `optimization/generator/eval_expectations_v2.json`; run outputs under `optimization/test_outputs/extraction_eval_v2/` (git-ignored).
**Final run:** `2026-07-17-r2` (the shipped prompt text). An earlier run `2026-07-17` drove three prompt fixes — both are reported below.

This is the plan's "do not land prompt changes blind" gate: the eval proves the model populates the new v2 fields (kinds, `established_by`, `whole_register`, numeric `values`, verbatim quotes) correctly, and that the native-v2 wire format flows through collection end-to-end.

## Method

- **Prompt identity.** The eval uses `create_register_constraints_v2_system_prompt()`, which embeds `ACCESS_CONSTRAINTS_V2_SCHEMA` and `ACCESS_CONSTRAINTS_V2_GUIDANCE` **verbatim** — the same two constants every shipping generator prompt (full, batched, batched-minimal) embeds. `tests/test_prompt_schema_consistency.py::test_all_prompts_share_v2_constraint_text` pins this, so the eval always tests exactly the text that ships.
- **Retrieval isolation.** Context per register is assembled **deterministically** from the chunked markdown (`hal_agent-phase-1d/chunked_datasheets/stm/<rm>/chunks/md/`): pages mentioning the register (the quote-anchor `RMMatcher` mention heuristic), the register's own section first (identified by the STM "… register (REG_NAME)" header + "Reset value" marker), its continuation pages, then other mentioning pages, capped at ~12k chars. None of the pipeline's retrieval infrastructure is used, so **a scoring miss is a prompt/model failure, never a retrieval miss**. (The plan's ~8k cap was raised to ~12k after the dry run showed the RTC_WPR unlock-procedure page falling just outside the budget for `rm0383/rtc_dr`; a dry-run marker check confirmed every case's constraint sentence is present in its context.)
- **One call per register**, one JSON-repair retry allowed (none was needed in either run). Each output is written as a **run-dir-style native-v2 file** (`access_constraints: []`, `access_constraints_v2: […]`, `schema_version: 2`, raw — including any malformed entries) and `collect_constraints.py` is run over it per RM with that RM's alphabetically-first SVD, exercising the native-v2 collection path end-to-end.

## Sample design (11 registers)

| case | why it is in the sample |
|---|---|
| rm0008 `i2c1_cr1` | canonical hardware `state_gate`, 3 conditions (STOP/START/PEC cleared by hardware) |
| rm0091 `usart1_cr1` | software mode-gate (UE=0 → `established_by: software`) repeated across many bits → dedup guidance |
| rm0008 `rtc_cnth` | RTC-CNF **pre+post software action** (the MTQC replacement) + hardware RTOFF |
| rm0008 `iwdg_pr` | **dual establishment**: whole-register KR==0x5555 (software) + hardware PVU |
| rm0383 `rtc_dr` | RTC_WPR 0xCA→0x53 → `sequence` (v1 mangled this into `equals:0xCA then 0x53`) |
| rm0008 `spi1_txcrcr` | cross-register **read gate** (BSY, hardware) — sound, not self-defeating |
| rm0360 `adc_chselr` | ADSTART=0 gate (golden label: software; see the honest note below) |
| rm0313 `rcc_csr` | **negative** — w1c flag-acknowledge pathology (v1 emitted 9 postconditions here) |
| rm0008 `wwdg_cfr` | **negative** — access-width note (v1 emitted a vacuous read/write constraint) |
| rm0008 `gpioa_odr` | **negative control** — plain register, no constraint prose |
| rm0008 `crc_dr` | **negative control** — plain data register |

## Iteration 1 → prompt fixes

Run `2026-07-17` (the first version of the v2 prompt): parse 10/11, kind accuracy 6/7, negatives 4/4, quote-anchor 6/8. Three concrete weaknesses, each fixed with one sentence in the shared prompt text and re-run:

1. **`enables` emitted as a step** (`{"register": "RTC_DR", "operation": "write"}`) → the sequence failed validation. Fix: "`enables` … a reference, never a step — no `operation`/`value` keys."
2. **Per-bit quote concatenation** (usart1_cr1: the same sentence pasted 8×) → unanchored. Fix: "Quote the recurring sentence ONCE; never concatenate its per-bit repetitions."
3. **Ellipsis-stitched quotes** (rtc_cnth joined three passages with "…", reordered) → unanchored. Fix: "Quote CONTIGUOUS text only — never join separated passages with ellipses."

## Final results (run `2026-07-17-r2`)

Per register:

| case | kinds emitted | kind match | established_by | quotes anchored |
|---|---|---|---|---|
| rm0008 i2c1_cr1 | state_gate | full | STOP ✓ START ✓ PEC ✓ (hardware) | 1/1 exact |
| rm0091 usart1_cr1 | state_gate (1 gate, 8 target_fields) | full | UE ✓ (software) | 1/1 exact |
| rm0008 rtc_cnth | state_gate (RTOFF only) | full | CNF **missing**, RTOFF **missing**¹ | 1/1 exact |
| rm0008 iwdg_pr | 3× state_gate | full | KR ✓ (software, whole_register, 0x5555) · PVU ✓ (hardware) | 3/3 exact |
| rm0383 rtc_dr | **sequence** (0xCA→0x53, `enables` whole_register) + state_gate (INIT) | full | — | 1 fuzzy, 1 unanchored² |
| rm0008 spi1_txcrcr | state_gate (read) | full | BSY ✓ (hardware) | 1/1 exact |
| rm0360 adc_chselr | state_gate | full | ADSTART **wrong** (hardware)³ | 1/1 exact |
| rm0313 rcc_csr | — | zero ✓ | — | — |
| rm0008 wwdg_cfr | — | zero ✓ | — | — |
| rm0008 gpioa_odr | — | zero ✓ | — | — |
| rm0008 crc_dr | — | zero ✓ | — | — |

¹ The model quoted the manual's RTOFF sentence verbatim — but RM0008's own prose names "the RTC_CR register" while the SVD register is `RTC_CRL`, so the suffix-matched golden key misses and collection rejects it (`unresolvable_in_svd`). The stricter contiguous-quote rule also made the model pick the RTOFF passage alone and drop the CNF pre+post encoding it produced in run 1 (where CNF scored ✓). This is the one real regression of fix 3; the B.4 re-prompt round is the designed recovery for exactly this shape.
² The INIT-gate quote's second sentence ("Set INIT bit to 1 in the RTC_ISR register…") paraphrases the init procedure — correctly caught by the deterministic anchor. The sequence itself is quote-anchored (fuzzy: list-numbering stripped).
³ The golden label says software (the driver decides whether a conversion is started); the model said hardware — defensible, since RM0360's text says ADSTART "is cleared by hardware". The label is kept per the sample spec, and the miss is counted, but this is an ambiguous gold, not a clear model error.

Aggregates (11 cases, 10 emitted constraints):

| metric | run 1 | **run 2 (final)** |
|---|---|---|
| parse rate (response JSON + all entries validate) | 10/11 (91%) | **11/11 (100%)** |
| constraint-level validity | 8/9 | **10/10** |
| kind accuracy (positives, required kinds present) | 6/7 (86%) | **7/7 (100%)** |
| established_by accuracy (named conditions) | 7/10 (70%) | **7/10 (70%)** |
| negative compliance (emit nothing) | 4/4 (100%) | **4/4 (100%)** |
| quote-anchor rate (exact+fuzzy) | 6/8 (75%) | **9/10 (90%)** |
| wire-format compliance (`schema_version: 2`, `access_constraints: []`) | 11/11 | **11/11** |

All three established_by misses in run 2 are footnoted above: two are the manual's own `RTC_CR`-naming artifact plus the contiguous-quote trade-off on one register, one is an ambiguous golden label. Every `established_by` value the model actually emitted on resolvable conditions was correct, including both dual-establishment cases (IWDG, and RTC_DR's INIT=software next to hardware flags in run 1).

## Collection over the eval outputs (native-v2 path, end to end)

`collect_constraints.py` ran per RM over the raw eval outputs (including run 1's malformed entry) with real SVDs:

| rm | registers | source | native constraints → v2 accepted | rejects | kinds | enforceability |
|---|---|---|---|---|---|---|
| rm0008 | 7 | all native_v2 | 6 → 5 | 1 `unresolvable_in_svd` (RTC_CR) | state_gate ×5 | witnessed ×4, compile ×1 |
| rm0091 | 1 | native_v2 | 1 → 0 | 1 `unresolvable_in_svd` (target field `M0` not in stm32f0x1.svd) | — | — |
| rm0313 | 1 | native_v2 | 0 → 0 | — | — | — |
| rm0360 | 1 | native_v2 | 1 → 1 | — | state_gate | witnessed ×1 |
| rm0383 | 1 | native_v2 | 2 → 2 | — | sequence + state_gate | compile ×2 |

Native-path behaviors exercised live: per-register `constraint_source: native_v2` + run-level source counts; **per-constraint recovery** (run 1's invalid sequence became a structured `invalid_v2_constraint` reject, its valid sibling survived); `"any"` expansion (run 1's IWDG gate → 3 per-operation gates, logged repair); SVD name resolution; computed enforceability; `other`-rate 0.0 everywhere (no escape-valve leakage). One polarity to revisit: a single unresolvable `target_fields` entry (usart1_cr1's `M0`, a datasheet-vs-SVD spelling gap) currently rejects the whole gate even though enforcement is register-granular — a candidate B.4 repair (drop the unresolvable field, keep the gate).

## Cost / time

Per full run: 11 calls, ~66k prompt + ~12k completion tokens, 41–49 s wall clock, ≈ $0.017 at Groq's listed gpt-oss-120b pricing ($0.15/M input, $0.60/M output at the time of writing). Both runs together ≈ $0.035. A full 30-RM re-extraction at corpus scale (~15k registers, batched) extrapolates to the same order as previous generator runs; the constraint text adds ~2.5k prompt tokens per call.

## Verbatim model outputs

**Good (rm0008 iwdg_pr — dual establishment, whole-register key, numeric value, exact quotes; excerpt of the 3-gate output):**

```json
{
  "kind": "state_gate",
  "target_register": "IWDG_PR",
  "target_fields": [],
  "target_operation": "write",
  "preconditions": [
    {
      "register": "IWDG_KR",
      "whole_register": true,
      "state": "equals",
      "values": ["0x5555"],
      "established_by": "software",
      "action_operation": "write"
    }
  ],
  "postconditions": [],
  "severity": "error",
  "consequence": "Write to IWDG_PR is ignored if the required key 0x5555 has not been written to IWDG_KR",
  "datasheet_text": "Write access to the IWDG_PR and IWDG_RLR registers is protected. To modify them, first write the code 0x5555 in the IWDG_KR register."
}
```

**Worst (rm0008 rtc_cnth — verbatim-faithful to the manual's own wrong register name, and the CNF pre+post encoding from run 1 was dropped under the contiguous-quote rule):**

```json
{
  "register_name": "RTC_CNTH",
  "schema_version": 2,
  "access_constraints": [],
  "access_constraints_v2": [
    {
      "kind": "state_gate",
      "target_register": "RTC_CNTH",
      "target_fields": [],
      "target_operation": "write",
      "preconditions": [
        {
          "register": "RTC_CR",
          "field": "RTOFF",
          "state": "set",
          "established_by": "hardware"
        }
      ],
      "postconditions": [],
      "severity": "error",
      "consequence": "Write to RTC_CNTH is ignored or prohibited when RTOFF is not set",
      "datasheet_text": "They are write-protected by bit RTOFF in the RTC_CR register, and a write operation is allowed if the RTOFF value is ‘1’."
    }
  ]
}
```

## Go / no-go

**Go, with two follow-ups.** The prompt reliably produces the load-bearing v2 structure: 100% parse and wire-format compliance, every required kind found (including a correct first-try `sequence` after one schema-sentence fix), 100% negative compliance across all four FP classes tested (the v1 corpus's worst pathologies — the rcc_csr 9-postcondition w1c case and the wwdg_cfr access-width case — both now emit nothing), and 90% of quotes deterministically anchored. `established_by` is correct on every condition the model emitted against a resolvable name; the three scored misses decompose into a manual-prose naming artifact (RTC_CR vs RTC_CRL), a quote-rule trade-off on the same register, and one ambiguous golden label — none is a systematic misunderstanding of the hardware/software distinction. Collection accepts the well-formed output natively and degrades per-constraint, exactly as designed. Follow-ups before/during full re-extraction: (1) implement the B.4 one-round re-prompt for `unresolvable_in_svd` rejects (both eval rejects are recoverable naming gaps, not hallucinations); (2) consider the field-level repair for unresolvable `target_fields` entries. The rtc_cnth CNF drop suggests the contiguous-quote rule may cost some multi-passage constraints; the corpus-scale run should watch the per-register constraint count against the v1 baseline for that signature.
