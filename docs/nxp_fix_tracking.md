# NXP (and cross-vendor) fix tracking

Fixes in the extraction pipeline are **format-group specific** — the NXP manuals
split into four documentation families (see
[`datasheet_format_families.html`](datasheet_format_families.html)), and a fix
that helps one group can be a no-op (or wrong) for another. This file tracks
which fix applies to which group/device, so we don't assume a fix generalizes
when it doesn't.

## Format groups (recap)

| Group | Devices | Address form | Name cell | Size col |
|---|---|---|---|---|
| **A** modern Kinetis | k32l3a, s32k1xx | relative offset (summary table) | plain | yes |
| **B** classic Kinetis | ke04, ke04_old, k64, mk20d7, mk20d5 | **absolute** (summary table) | `Label (NAME)` | yes |
| **C** classic LPC | lpc845 | relative offset (summary table) | plain | no |
| **D** modern NXP | lpc55s69, mimxrt685s, mimxrt633s | **caption** `(NAME: offset=0x..)`, no table | — | — |
| **STM** | all 53 rmXXXX | inline `Address offset:` / `Reset value:` | plain | n/a |

## Fix status matrix

Legend: ✅ applies & shipped · 🟡 applies, needs work/validation · ➖ N/A for this group · ❌ not yet.

| Fix | A | B | C | D | STM | Status / notes |
|---|:--:|:--:|:--:|:--:|:--:|---|
| **Quote-anchor device-prefix** (`core/quote_anchor.py`) | ✅ | ✅ | ✅ | ✅ | ✅ | Shipped `5583c22`. Was STM-only (`rm` prefix); now any device id. Universal. |
| **`.xml` SVD globs** (`collect_constraints.py`, `bug_finding/access.py`) | ✅ | ✅ | ✅ | ✅ | ➖ | Shipped `5583c22`. NXP SVDs are `.xml`; STM already `.svd`. |
| **Envelope-gate salvage** (`collect_constraints.py`) | ✅ | ✅ | ✅ | ✅ | ✅ | Shipped `bb08c11`. **Universal** — null structural field no longer drops constraints. lpc845 3→10 lint-survivors; also STM rm0481 +100, rm0394 +21, rm0008 +7. |
| **Generator concurrency** (`s1a_generator.py`, `result_saver.py`) | ✅ | ✅ | ✅ | ✅ | ✅ | Shipped `bf7955b`. **Universal.** `--generator-concurrency` thread-pools batches (3.6× on 65-reg test); makes giants feasible (k32l3a >3h timeout → ~93 min; s32k1xx ~2.6 h). Default 1 = unchanged. |
| **OE store-build lock** (`openevolve_search.py`) | ✅ | ✅ | ✅ | ✅ | ✅ | Shipped `7e5d8ee`. **Universal.** Required by concurrency — serializes the ChromaDB store build (was racing "tenant default_tenant"). |
| **Smart empty-field retry** (`s1a_generator.py`) | ✅ | ✅ | ✅ | ✅ | ✅ | Shipped `bf7955b`. Stops retry rounds that recover no new fields (futile on NXP where empty = extraction-failed). |
| **Summary-table fill, cross-chunk** (`core/nxp_summary_fill.py`) | ➖ | ➖ | ✅ | ➖ | ➖ | Shipped `5583c22`. Helps **C only** (lpc845 offset 85→93%). A & B: no-op (generator already extracts offsets). D: no summary table (see caption fill). |
| **Group D caption-offset fill** (`core/nxp_caption_fill.py`) | ➖ | ➖ | ➖ | ✅ | ➖ | Shipped `490fb7c` (Step 2b2). Parses `(NAME[,:] offset=0x..)` table captions, peripheral-scoped. lpc55s69 48→50%, mimxrt685s 46→48%, 0 wrong. Modest: most null-offset Group D regs have no caption in the retrieved chunks (retrieval-coverage, separate). |
| **Array/dim reconciliation** (`core/nxp_array_fill.py`) | ✅ | ✅ | ✅ | ✅ | ➖ | Shipped `8cf8364` (Step 2c). Clone absent array instances from a produced sibling + stride-shift offset. Recovered **243 regs**, 0 wrong offsets; reg coverage → 94–100%. Minor (~1.5%), NOT the top lever — that framing was the join-bug era. |
| **~~Group B adapter~~** (absolute→offset) | ➖ | ➖ | ➖ | ➖ | ➖ | **RETRACTED — not needed.** Group B generator already gets 76–90% address with no adapter (ke04, k64, mk20d7). |
| **~~Per-bit reset assembler~~** | ❌ | ❌ | ❌ | ❌ | ❌ | **ATTEMPTED + REVERTED.** Mechanism (schema + assembler) was correct, but per-bit data isn't reliably available: LLM emits per-field reset for ~7% of fields; safe deterministic chunk-parse ~0. Reset stays at the generator's native ~23–58%. Needs a dedicated per-format extractor. |
| **Retry-overwrite merge** (`s1a_generator.py`) | ❌ | ❌ | ❌ | ❌ | ❌ | **Not started.** Empty-field retry re-gens field-less regs with `force=True` and can drop a `address_offset` it already had (k32l3a ~80%→60%). Retry should MERGE recovered fields, not overwrite structure. Cross-vendor. |
| **`read_effect` `consequence`** (generator/prompt) | ❌ | ❌ | ❌ | ❌ | ❌ | Not started. Generator emits `read_effect` without required `consequence` → `invalid_v2_constraint`. Cross-vendor. |
| **NXP generator recall rules** (`prompts/register_info_nxp.py`) | ✅ | ✅ | ✅ | ✅ | ➖ | Shipped `5583c22`. Reset assembly / size-address / write-sequences. NXP-wide. |

## Per-device run status (end-to-end s0)

All 11 run end-to-end. Coverage = corrected (generator's own enumeration), after
all fill steps (2b summary, 2b2 caption, 2c array). reg% = register coverage.

| Device | Group | reg% | address / reset / size | confirmed constraints |
|---|---|:--:|---|---|
| lpc845 | C | 100 | 91 / 54 / — | 17 |
| k32l3a | A | 99 | 60 / 42 / 61 | 176 |
| s32k1xx | A | 97 | 51 / 30 / 52 | 200 |
| ke04 | B | 97 | 91 / 54 / 91 | 43 |
| k64 | B | 98 | 76 / 23 / 79 | 210 |
| mk20d7 | B | 98 | 79 / 28 / 80 | 211 |
| lpc55s69 | D | 94 | **50** / 41 / 24 | 17 |
| mimxrt685s | D | 98 | **48** / 34 / 47 | 82 |
| mk20d5 (sib) | B | 95 | 91 / 33 / 93 | 188 |
| ke04_old (sib) | B | 97 | 94 / 46 / 95 | 61 |
| mimxrt633s (sib) | D | 99 | 46 / 34 / 48 | 74 |

## Rule of thumb
Check the **group**, but the empirical finding (corrected measurement) is that the
**generator extracts offsets itself across all groups** (A 51–60%, B 76–94%, C 91%,
D 46–50%) and finds 94–100% of registers — so no per-family adapter/parser was
needed. The real structural gaps are cross-group: **reset** (23–58%, attempted +
reverted — hard) and **Group D offsets/size** (~47% — caption fill helps a little;
rest is retrieval). Universal fixes (anchoring, envelope-gate, `.xml` globs,
concurrency) are the only
ones safe to assume cross-group.
