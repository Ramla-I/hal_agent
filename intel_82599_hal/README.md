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

See `startup.md` for the step-by-step execution plan, environment, and the scripts to
write. Reproduction inputs are vendored; generated outputs are `.gitignore`d.
