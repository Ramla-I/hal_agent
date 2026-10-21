# NXP (and cross-vendor) fix tracking

Fixes in the extraction pipeline are **format-group specific** — the NXP manuals
split into four documentation families (see
[`datasheet_format_families.html`](datasheet_format_families.html)), and a fix
that helps one group can be a no-op (or wrong) for another. This file tracks
which fix applies to which group/device, what's shipped, and what's left.

**Split across two PRs:** **#35** (`nxp_devices`) — the NXP-specific extraction
fills + fixes; **#39** (`generator-concurrency`) — vendor-agnostic
concurrency/thread-safety infra (affects all vendors, so kept separate).

## Format groups (recap)

| Group | Devices | Address form | Name cell | Size col |
|---|---|---|---|---|
| **A** modern Kinetis | k32l3a, s32k1xx | relative offset (summary table) | plain | yes |
| **B** classic Kinetis | ke04, ke04_old, k64, mk20d7, mk20d5 | **absolute** (summary table) | `Label (NAME)` | yes |
| **C** classic LPC | lpc845 | relative offset (summary table) | plain | no |
| **D** modern NXP | lpc55s69, mimxrt685s, mimxrt633s | **caption** `(NAME: offset=0x..)`, no table | — | — |
| **STM** | all 53 rmXXXX | inline `Address offset:` / `Reset value:` | plain | n/a |

## Fix status matrix

Legend: ✅ applies & shipped · 🟡 applies, needs work · ➖ N/A for this group · ❌ not done.

| Fix | A | B | C | D | STM | Where | Status / notes |
|---|:--:|:--:|:--:|:--:|:--:|---|---|
| **Quote-anchor device-prefix** (`core/quote_anchor.py`) | ✅ | ✅ | ✅ | ✅ | ✅ | #35 | Was STM-only (`rm` prefix); now any device id. Universal. |
| **`.xml` SVD globs** (`collect_constraints.py`, `bug_finding/access.py`) | ✅ | ✅ | ✅ | ✅ | ➖ | #35 | NXP SVDs are `.xml`; STM already `.svd`. |
| **Envelope-gate salvage** (`collect_constraints.py`) | ✅ | ✅ | ✅ | ✅ | ✅ | #35 | **Universal** — a null structural field no longer drops a register's constraints. lpc845 3→10 kept; also STM rm0481 +100, rm0394 +21, rm0008 +7. |
| **Summary-table fill, cross-chunk** (`core/nxp_summary_fill.py`) | ➖ | ➖ | ✅ | ➖ | ➖ | #35 | Helps **C only** (lpc845 offset 85→93%). A & B: no-op (generator already extracts offsets). D: no summary table (see caption fill). |
| **Group D caption-offset fill** (`core/nxp_caption_fill.py`) | ➖ | ➖ | ➖ | ✅ | ➖ | #35 | Parses `(NAME[,:] offset=0x..)` table captions, peripheral-scoped. lpc55s69 48→50%, mimxrt685s 46→48%, 0 wrong. |
| **Array/dim reconciliation** (`core/nxp_array_fill.py`) | ✅ | ✅ | ✅ | ✅ | ➖ | #35 | Clone absent array instances from a produced sibling + stride-shift offset. +243 regs, 0 wrong; reg coverage → 94–100%. (Instance-cloning only — name-variant matching is still open, below.) |
| **NXP generator recall rules** (`prompts/register_info_nxp.py`) | ✅ | ✅ | ✅ | ✅ | ➖ | #35 | Reset-assembly / size-address / write-sequence prompt rules. NXP-wide. |
| **Discovery-tool join fix** (`scripts/device_discovery.py`) | ✅ | ✅ | ✅ | ✅ | ➖ | #35 | Measure coverage against the generator's own enumeration (was inflating "absent" ~3×). |
| **Generator concurrency** (`s1a_generator.py`, `result_saver.py`) | ✅ | ✅ | ✅ | ✅ | ✅ | **#39** | `--generator-concurrency` thread-pools batches (3.6× on test); giants that timed out now finish. Default 1 = unchanged. |
| **OE store-build lock** (`openevolve_search.py`) | ✅ | ✅ | ✅ | ✅ | ✅ | **#39** | Serializes the ChromaDB store build so concurrent batches don't race. |
| **Smart empty-field retry** (`s1a_generator.py`) | ✅ | ✅ | ✅ | ✅ | ✅ | **#39** | Stops retry rounds that recover no new fields. |

## Remaining (not done)

| Item | Scope | Note |
|---|---|---|
| **Per-bit reset assembler** | all groups | Reset coverage is the weak axis (23–58%). Attempted + **reverted** — per-bit reset data isn't reliably extractable (LLM emits per-field reset for ~7% of fields; safe deterministic parse ~0). Needs a dedicated per-format extractor. |
| **Array/name reconciliation** (name half) | all groups | Instance-cloning shipped (#35); the SVD **name-variant** matching that would also clear the `unresolvable_in_svd` constraint rejects is not done. |
| **Group D offsets + size** | D | Caption fill got +2pp; the rest is a **retrieval-coverage** problem (fetch the chunk that holds a register's offset) + size extraction. |
| **Scatter recovery** | all groups | ~311 sibling-less absent registers (batch-failure resume, not array cloning). |
| **`read_effect` `consequence`** | cross-vendor | Generator omits the required `consequence` field → `invalid_v2_constraint` rejects. Small prompt fix. |
| **Retry-overwrite merge** | cross-vendor (#39 code) | The empty-field retry re-gens field-less registers and can drop an `address_offset` it already had (k32l3a ~80→60%). Retry should MERGE recovered fields, not overwrite structure. |

## Decided against
- **Group B absolute→offset adapter — retracted.** The Group B generator already gets 76–90% address with no adapter (ke04, k64, mk20d7), so it was unnecessary.

## Per-device run status (end-to-end s0)

All 11 devices run end-to-end. Coverage measured against the generator's own
enumeration, after the fill steps (summary / caption / array). reg% = register coverage.

| Device | Group | reg% | address / reset / size | confirmed constraints |
|---|---|:--:|---|---|
| lpc845 | C | 100 | 91 / 54 / 50 | 17 |
| k32l3a | A | 99 | 60 / 42 / 61 | 176 |
| s32k1xx | A | 97 | 51 / 30 / 52 | 200 |
| ke04 | B | 97 | 91 / 54 / 91 | 43 |
| k64 | B | 98 | 76 / 23 / 79 | 210 |
| mk20d7 | B | 98 | 79 / 28 / 80 | 211 |
| lpc55s69 | D | 94 | 50 / 41 / 24 | 17 |
| mimxrt685s | D | 98 | 48 / 34 / 47 | 82 |
| mk20d5 (sib) | B | 95 | 91 / 33 / 93 | 188 |
| ke04_old (sib) | B | 97 | 94 / 46 / 95 | 61 |
| mimxrt633s (sib) | D | 99 | 46 / 34 / 48 | 74 |

## Rule of thumb
The empirical finding: the **generator extracts offsets itself across all groups**
(A 51–60%, B 76–94%, C 91%, D 46–50%) and finds 94–100% of registers — so no
per-family adapter/parser was needed. The real remaining gaps are cross-group:
**reset** (hard — attempted + reverted) and **Group D offsets/size** (retrieval).
