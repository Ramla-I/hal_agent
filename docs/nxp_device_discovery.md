# NXP device discovery log

Per-device discovery from the full-sweep campaign: run each NXP device through s0,
then analyze structure coverage, the constraint funnel, residual gaps, and how the
device's format group ([[datasheet_format_families.html]]) fits the current fixes.
Recommended changes are recorded per device; shipped fixes are tracked in
[`nxp_fix_tracking.md`](nxp_fix_tracking.md).

Generated with `scripts/device_discovery.py <device>`.

**Scope note:** `ke04_old` (old duplicate of ke04), `mk20d5` (same K20 template as
mk20d7), and `mimxrt633s` (identical PDF to mimxrt685s) are covered by their
siblings and not run separately unless a difference is suspected.

---

<!-- per-device entries appended below -->

## lpc845 — Group C (classic LPC) — reference device

**Run:** s0 end-to-end with summary-fill + envelope-gate fix. `DONE ok`.

**Structure coverage (vs SVD, 668 regs; 658 matched, 10 absent):**
- address_offset **92%** · reset_value **45%** · size **54%**

**Constraint funnel:** raw 19–23 → survived lint **10** → anchored 10 → **confirmed 10** (was **3** before the envelope-gate fix `bb08c11` — the fix flowed through end-to-end). Rejected below the gate: 13 (8 `invalid_v2_constraint` incl. `read_effect` missing `consequence`; 7 `unresolvable_in_svd`).

**Residual gaps:**
- 10 absent registers: `FLASH_CTRL_*`, `MTB_SFR_*` — **multi-underscore peripheral names** (file split on first `_` mis-segments `flash_ctrl`/`mtb_sfr`).
- 49 matched but missing offset; 22 are **array-indexed** (`MATCH4`, `PINASSIGN10` → need `base+n×stride`).
- reset (45%) + size (54%) low: Group C summary tables have **no Width column** and often no reset column → both need the per-bit assembler.

**What would improve lpc845 (recommended, not yet shipped):**
1. Multi-underscore peripheral name handling (recovers ~10 absent). *small*
2. Array/dim reconciliation `base+n×stride` (recovers ~22 offsets + some `unresolvable_in_svd` constraints). *medium*
3. Per-bit reset/size assembler (lifts reset 45%→, size 54%→). *medium, deferred (a)*
4. `read_effect` `consequence` emission (recovers ~3 constraints). *small, cross-vendor*

**Shipped & confirmed here:** cross-chunk summary-fill (C), envelope-gate salvage (universal), quote-anchor prefix (universal).

