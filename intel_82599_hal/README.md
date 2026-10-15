# Case study: generate an intralingual HAL for the Intel 82599 10 GbE NIC

A self-contained experiment (like `gen_vs_claude_rm0041/`) that takes our extraction
pipeline **outside the microcontroller domain** and drives it end-to-end into a real
driver.

## Two purposes (from the paper)
1. **Cross-domain applicability.** Show the pipeline can generate a **HAL** for hardware
   outside the MCU ecosystem, i.e. the HAL abstraction applies across domains and can
   take **different implementations** (here: a memory-mapped NIC register model, not a
   per-register svd2rust PAC).
2. **Incomplete specification recovery.** Our other evaluations prioritize *precision*
   (keep only specs highly likely correct). Bug-finding/constraint-injection can confirm
   true positives via SVD diffs and compiler errors, but those signals never reveal what
   the pipeline **misses entirely**. Building a *complete software interface* does: a
   missing register/field/constraint breaks the end-to-end HAL. This case study measures
   that via a real driver's compile.

## The target: current Theseus `ixgbe`
- Reference vendored under `reference/` — the **current** `theseus-os/Theseus`
  `kernel/ixgbe` at commit `1fbfe567…` (see `reference/COMMIT.txt`). The older
  `devices/intel/82599/ixgbe_4a124f4.rs` snapshot is **not** used.
- Its HAL (`reference/src/regs.rs` + `queue_registers.rs`) is **7 `#[repr(C)]` structs**
  covering the memory-mapped region (general 1/2/3, Rx 1/2, Tx, MAC), split to isolate
  per-queue registers for virtualization. Each field is a `Volatile<u32>` /
  `ReadOnly<u32>` / `WriteOnly<u32>` at an exact offset, with explicit `_paddingN: [u8; N]`
  between them, array registers as `[Volatile<u32>; N]`, and `const _: assert!(size_of ==
  4096)` guards per region.
- So **access *direction* is already intralingual** (the `Volatile`/`ReadOnly`/`WriteOnly`
  type encodes RW/RO/WO), but there is **no ordering/state-constraint encoding**. That gap
  is our contribution.

## What we build
Auto-generate an **intralingual HAL** for the 82599 from the datasheet and **plug it into
the current driver**, in two respects:
- **Structural HAL** — regenerate the `regs.rs`/`queue_registers.rs` register model
  (offsets, widths, RO/WO/RW, arrays, region split, size asserts) from our extraction.
  This is what the recall metric tests.
- **Constraint encoding** — layer our grammar-v2 `access_constraints_v2` into the types
  (witness / type-state gating) so illegal access orderings fail to compile — the safety
  the hand-written HAL does **not** have. This is "the HAL takes a different, safer
  implementation."

## No ground truth
Intel ships no SVD/verified datasheet for the 82599. Therefore:
- **The current Theseus driver is the reference + consumer.** The register set the driver
  needs = the end-to-end target; the datasheet register-summary = the recall denominator.
- **Recall metric = clone Theseus and `make`.** Plug our generated HAL into the ixgbe
  crate and build Theseus; **compiler errors surface exactly the missing/wrong specs**
  (a missing register shifts the `#[repr(C)]` layout and trips the size asserts — recall
  failures are loud, not silent).

## Deliverables
1. A generated intralingual 82599 HAL (structural + constraint-encoded).
2. **Recall result:** what the driver needs that we recovered vs. missed, and the
   compile-error taxonomy showing how misses break the end-to-end HAL.
3. **Enforcement result:** the access constraints we encoded that the hand-written HAL
   lacks, and the driver-side diff required to satisfy them.

Reproduction inputs are vendored; generated outputs are `.gitignore`d.

## Reproduction

```bash
# This worktree has no .venv of its own — use the sibling retrieval worktree's
# (openai, fastembed, chromadb, tiktoken, pandas):
VENV=/home/ramla/hal_agent-retrieval/.venv/bin/python
export GROQ_API_KEY=...     # generator = gpt-oss-120b via Groq
export OPENAI_API_KEY=...   # the gpt-5.2 escalation / fallback

cd pipeline
$VENV s1_enumerate_targets.py                       # targets/ (committed)
$VENV s2_generate.py --registers ctrl               # one-register smoke test — CALLS the LLM (gpt-oss-120b)
$VENV s2_generate.py --registers ctrl --dry-run     # retrieval only, NO LLM (just saves the context)
$VENV s2_generate.py                                # all 75; then --auto-complete rNNN for the retry loop
$VENV s3_collect_constraints.py rNNN          # grammar-valid constraints + enforceability
$VENV s4_emit_hal.py rNNN       [--gated] [--plain] # generated regs.rs (structural / constraint-gated)
# gated over the COMBINED 34 (folds in the recovered constraints) and the provenance variant:
$VENV s4_emit_hal.py rNNN --gated --extra-constraints config/recovered_constraints.json
$VENV s4b_emit_hal_minted.py rNNN --extra-constraints config/recovered_constraints.json
$VENV build_constraints_list.py               # regenerate reports/constraints_found.{json,md} (needs constraints/r006_*.json)
```

- **Datasheet chunks** (pre-chunked, external): `INTEL_CHUNKS_DIR`, default
  `/home/ramla/hal_agent-retrieval/chunked_datasheets/intel/82599/chunks/md`.
- **Retriever**: `pipeline/retriever/best_program.py`, vendored from
  `hal_agent-retrieval` `v6_82599_seed42`,
  `sha256 = 76079e0386750719331094601404ece71a9bc48baf6886fe576e8f20c83ad655`.
- Eval: clone `theseus-os/Theseus` @ `1fbfe567` (see `reference/COMMIT.txt`),
  swap the generated `regs.rs` into `kernel/ixgbe/src/`, `cargo check -p ixgbe`.
- The canonical generation runs are r003–r006 (gitignored); `reports/` holds
  the committed results.

## Status: done — see the reports

- **`reports/results.md`** — the numbers. Structural recall is near-perfect:
  3 first-compile errors on the full drop-in (1 rename + 2 adjudicated
  RO-vs-init-write divergences), then green; **75/75 offsets** correct;
  **75/75 register access codes** match the datasheet; reset values extracted
  for the 55 registers the datasheet defines (20 correctly null); and a full
  **census of all 406 extracted bit fields vs the datasheet's own field tables
  = 404/406 (99.5%)** correct (the 2 errors are spurious fields the full-page
  completion pass bled in from adjacent registers, inert in this whole-register
  HAL). **8 real bugs** found across the four drivers (none by testing) — e.g.
  Theseus `RDRXCTL_CRC_STRIP` sets a reserved bit, and (via the recovered RXCSUM
  constraint) Theseus writes RXCSUM/RSS config while the receiver is enabled.
  (An earlier count of 9 included an ixy/Redox FCTRL "live write" that turned
  out to be a false positive — both write FCTRL inside `init_rx`'s
  RXEN-disabled window; see `reports/results.md` finding 6.)
- **`reports/constraints_found.md` / `.json`** — the durable final constraints
  list: **39 found → 5 dropped (grammar schema) → 34 kept** = 29 grammar-valid
  from the canonical run + **5 recovered** by the constraint-recall improvement
  (RXCSUM, RDLEN, TDLEN, DAQF, SDPQF, committed as
  `config/recovered_constraints.json`). Over the combined 34, **9 become
  compile-time gates** (field-level default: witnesses, never-set clamps, a
  coupled CRC-strip setter that makes the RDRXCTL bug unwritable, and the
  recovered RXCSUM witness gate), at a driver-diff cost of +40/−18 lines.
  (Schema-valid + computed enforceability; not run through the LLM constraint
  validator — noted in the report.)
- **`reports/friction.md`** — the friction ledger: every manual/contract-level
  adaptation, categorized (naming / packaging / adjudicated access divergence /
  policy constants / gate-required driver diff / source-document artifacts),
  kept separate from the genuine findings.
- **`reports/retrofit.md`** — extension: ixy.rs / Redox ixgbed / RedLeaf vs
  the generated HAL — **all three compile against it**: full ports of ixy
  (85 replacements) and Redox (67), RedLeaf via a zero-call-site layer
  retarget (its domain crate also compile-verified against the gated HAL);
  coverage complete (41/37/17 registers); leads exposed include the DMATXCTL.VT
  clobber in **three** codebases (ixy, Redox, and RedLeaf's domain driver —
  all ixy descendants, see the lineage note), RedLeaf's RDLEN stride typo
  (0x60 for 0x40), 64-bit reads of 32-bit registers, and the legacy 0x5400
  RAL/RAH alias reliance. The ixy/Redox FCTRL promiscuous writes are **not**
  bugs — they sit inside `init_rx`'s RXEN-disabled window; the whole-register
  gate fires there as a false positive (write-site-local), documented as such.
- `pipeline/` — s1_enumerate_targets.py, s2_generate.py (batched generation + s2a_prompts_intel + s2b_scan_constraints helpers,
  bounded completion passes, the self-escalating `--auto-complete` loop, and
  the optional `--constraint-recall` trigger), s3_collect_constraints.py,
  s4_emit_hal.py (structural + `--gated` + `--extra-constraints` to fold in the
  recovered set), s4b_emit_hal_minted.py (the provenance-hardened variant), the
  audit/scan tools (audit_full_subfields.py, audit_structure.py,
  audit_score_subfields.py, audit_selection_subfields.py, s2b_scan_constraints.py,
  build_constraints_list.py), the
  committed contracts (config/packaging.json, config/name_map.json, config/access_overrides.json,
  config/constants_map.json). Theseus integration (clone recipe + the gated driver diff) is in `theseus_retrofit/`.
