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
| **Summary-table fill, cross-chunk** (`core/nxp_summary_fill.py`) | ➖ | ➖ | ✅ | ➖ | ➖ | Shipped `5583c22`. Helps **C only** (lpc845 offset 85→93%). **A & B: confirmed no-op** — the generator already extracts offsets (A: k32l3a/s32k1xx; B: ke04 90%, k64 73%), so the fill fills 0 and isn't needed. **D/STM**: no summary table. |
| **~~Group B adapter~~** (absolute→offset + unwrap `Label (NAME)`) | ➖ | ➖ | ➖ | ➖ | ➖ | **RETRACTED — not needed.** Empirically the Group B generator already gets 73–90% address + 74–89% size with no adapter (ke04, k64). Was wrongly flagged "highest ROI" a priori. |
| **Array/dim reconciliation** (`MATCH4`→`base+n×stride`; SVD-name↔manual-name) | ❌ | ❌ | ❌ | ❌ | 🟡 | **Not started — now the TOP lever.** Dominant gap on every group: s32k1xx 637 absent, k64 233, k32l3a 64, + hundreds of array-indexed missing offsets + the `unresolvable_in_svd` constraint rejects. |
| **Per-bit reset assembler** (deferred (a)) | ❌ | ❌ | ❌ | ❌ | ➖ | Not started. Reset is the weak axis everywhere (21–58%), worst on Group B (ke04 58, k64 21). Blind zero-default rejected (+82 wrong). |
| **Retry-overwrite merge** (`s1a_generator.py`) | ❌ | ❌ | ❌ | ❌ | ❌ | **Not started.** Empty-field retry re-gens field-less regs with `force=True` and can drop a `address_offset` it already had (k32l3a ~80%→60%). Retry should MERGE recovered fields, not overwrite structure. Cross-vendor. |
| **`read_effect` `consequence`** (generator/prompt) | ❌ | ❌ | ❌ | ❌ | ❌ | Not started. Generator emits `read_effect` without required `consequence` → `invalid_v2_constraint`. Cross-vendor. |
| **NXP generator recall rules** (`prompts/register_info_nxp.py`) | ✅ | ✅ | ✅ | ✅ | ➖ | Shipped `5583c22`. Reset assembly / size-address / write-sequences. NXP-wide. |

## Per-device run status (end-to-end s0)

| Device | Group | Full run | address / reset / size | confirmed constraints |
|---|---|---|---|---|
| lpc845 | C | ✅ | 92 / 45 / 54 | 10 |
| k32l3a | A | ✅ | 60 / 42 / 61 | 176 |
| s32k1xx | A | ✅ | 70 / 34 / 72 | 200 |
| ke04 | B | ✅ | 90 / 58 / 89 | 43 |
| k64 | B | ✅ | 73 / 21 / 74 | 210 |
| mk20d7 | B | pending (needs chunk) | — | — |
| lpc55s69 | D | pending (needs chunk) | — | — |
| mimxrt685s | D | pending (needs chunk) | — | — |
| mk20d5, ke04_old, mimxrt633s | B/B/D | skipped (sibling dup) | — | — |

## Rule of thumb
Before claiming a fix "works for NXP," check the **group** — but the empirical
surprise from the full sweep is that the **generator handles offsets/size across
all groups on its own** (60–92% address, no fill/adapter), so the structural fixes
that matter are cross-group (array reconciliation, reset). Universal fixes
(anchoring, envelope-gate, `.xml` globs, concurrency) are the only
ones safe to assume cross-group.
