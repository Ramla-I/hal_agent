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
| **Summary-table fill, cross-chunk** (`core/nxp_summary_fill.py`) | 🟡 | ➖* | ✅ | ➖ | ➖ | Shipped `5583c22` for **C** (lpc845 offset 85→93%). **A**: format close (relative offset + `Register` col) — mostly works, **needs per-device validation** (no verified CSV). **B**: safe **no-op** (`*`verified 0 filled/0 wrong) — needs the adapter below. **D/STM**: no summary table. |
| **Group B adapter** (absolute→offset + unwrap `Label (NAME)`) | ➖ | ❌ | ➖ | ➖ | ➖ | **Not started.** Highest ROI: one change covers ke04, k64, mk20d7, mk20d5, ke04_old. |
| **Group D caption parser** (`(NAME: offset=0x..)`) | ➖ | ➖ | ➖ | ❌ | ➖ | Not started; only if Group D recall proves weak (generator may read captions inline already). |
| **NXP generator recall rules** (`prompts/register_info_nxp.py`) | ✅ | ✅ | ✅ | ✅ | ➖ | Shipped `5583c22`. Reset assembly / size-address / write-sequences. NXP-wide. |
| **Per-bit reset assembler** (deferred (a)) | ❌ | ❌ | ❌ | ❌ | ➖ | Not started. Needed where summary tables lack a reset column (esp. C). Blind zero-default rejected (+82 wrong). |
| **`read_effect` `consequence`** (generator/prompt) | ❌ | ❌ | ❌ | ❌ | ❌ | Not started. Generator emits `read_effect` without required `consequence` → `invalid_v2_constraint`. Cross-vendor. |
| **Array/name reconciliation** (`MATCH4`→`base+n×stride`; SVD-name↔manual-name) | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | Not started. Affects residual offsets + `unresolvable_in_svd` constraint rejects on every group. |

## Per-device run status (end-to-end s0)

| Device | Group | Last full run | Notes |
|---|---|---|---|
| lpc845 | C | yes (re-running w/ gate fix) | reference device for the C fixes |
| k32l3a | A | no | chunked; Group A validation pending |
| s32k1xx | A | no | chunked |
| ke04, k64 | B | no | chunked; verified CSVs exist (ground truth) |
| mk20d7, mk20d5, ke04_old | B | no | PDFs only (mk20d5 group inferred) |
| lpc55s69 | D | no | chunked |
| mimxrt685s/633s | D | no | same PDF; chunked (685s) |

## Rule of thumb
Before claiming a fix "works for NXP," check the **group**: a summary-table fix is
meaningless for Group D, and wrong (absolute addresses) for Group B without the
adapter. Universal fixes (anchoring, envelope-gate, `.xml` globs) are the only
ones safe to assume cross-group.
