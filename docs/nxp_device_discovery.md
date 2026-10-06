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

## k32l3a — Group A (modern Kinetis) — PARTIAL (timed out)

**Run:** s0 **timed out at 3 h** (rc=124) mid-generation — dual-core (2 SVDs, 3,898 registers). Generated 2,952 register files but never reached summary-fill (Step 2b) or the constraint pipeline, so no funnel/review. Structure numbers below are **raw generator, pre-fill**.

**Structure coverage (partial, vs SVD 2202; 2074 matched):** address 65% · reset 46% · size 66%. Raw constraints in partial output: **244** (state_gate 164, other 39, value_relation 16, write_once 14, sequence 6, clock_gate 3, read_effect 2).

**Observations (throughput):** (1) log shows per-peripheral "batches" of **1 register** for several peripherals — batching degraded to per-register. (2) repeated function-call errors `register_size_in_bytes cannot be converted to int` / `Missing required parameter: base_address_in_hex` → retries → slow. Both inflate wall-clock on large devices. **Not a format-group issue — a generator throughput bug.**

**Blocked:** needs a throughput fix or a much larger timeout to complete. s32k1xx (13,815 regs) is worse. See campaign decision below.

### k32l3a — COMPLETE (after throughput + DB-lock fixes)

**Run:** s0 end-to-end, `--generator-concurrency 6`, rc=0 (~93 min; was >3h timeout). SVD-union correction: k32l3a is 2,392 unique regs (not 3,898); s32k1xx ~3,093 (not 13,815).

**Structure coverage (vs SVD 2202; 2138 matched, 64 absent):** address **60%** · reset **42%** · size **61%**.
- **Group A summary-fill = no-op** (Step 2b filled 0 of 1,748 gaps): the Group A generator extracts offsets itself; the cross-chunk fill adds nothing. So Group A needs no fill — contrary to the earlier "mostly works" guess.
- 835 missing offsets, **577 array-indexed** (`FTFE_FCCOB%s`, `DMAMUX1_CHCFG[%s]`, TCD arrays) → array/dim reconciliation is the dominant structural gap.
- ⚠️ **Retry-overwrite regression:** address was ~80% right after generation but **dropped to 60%** after the empty-field retry re-generated field-less registers (`force=True`) and some lost an `address_offset` they'd had. Pre-existing behavior (not caused by the concurrency change). **Recommended fix: the retry should MERGE recovered subfields into the existing file, not overwrite structural fields it already had.** *medium, cross-vendor — would also help STM.*

**Constraints:** collected native_v2 **307** → survived lint **245** → anchored 236 → **confirmed 176** (enforceable 158). Rich (envelope-gate fix active). Below-gate rejects: 53 `invalid_v2_constraint`, 31 `unresolvable_in_svd`, 2 write-on-read-only, 1 w1c.

**Shipped & confirmed here:** generator concurrency (3.6× on the 65-reg test; k32l3a completes vs timeout), DB-build lock, smart retry, envelope-gate salvage (307→245).

