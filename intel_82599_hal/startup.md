# startup — Intel 82599 intralingual-HAL case study

Read `README.md` first for the goals and design. This file is the execution handoff for
a fresh session working in this worktree (`hal_agent-intel-82599`).

## Goal (one line)
Generate an intralingual HAL for the Intel 82599 from the datasheet and plug it into the
**current** Theseus `ixgbe` driver; measure recall via the driver's compile (`make`), and
add access-constraint enforcement the hand-written HAL lacks.

## What's already here
- `reference/` — current Theseus `kernel/ixgbe` (commit in `reference/COMMIT.txt`): the
  driver (`lib.rs`, `virtual_function.rs`) + the HAL to replace (`regs.rs`,
  `queue_registers.rs`) + `Cargo.toml`. This is the API our generated HAL must satisfy.
- `pipeline/retriever/best_program.py` (evolved 82599 retriever, `sha256` below) +
  `_shared_cache.py`. Only external dep is `context_retrieval.vector_db.embeddings`
  (in this repo). Vendored from `hal_agent-retrieval` `v6_82599_seed42`.
  - `sha256(best_program.py) = 76079e0386750719331094601404ece71a9bc48baf6886fe576e8f20c83ad655`

## Environment
```bash
source .venv/bin/activate                 # pipeline deps (openai, fastembed, chromadb, tiktoken, pandas)
export GROQ_API_KEY=...                    # generator = gpt-oss-120b via Groq (or try a stronger model)
export OPENAI_API_KEY=...                  # fallbacks
```
- **Datasheet:** `devices/intel/82599/82599.md` (~827 KB markdown).
- **Chunks:** live in `hal_agent-retrieval/chunked_datasheets/intel/82599/chunks` — copy
  them in (or re-chunk `82599.md` with the preprocessing pipeline) so retrieval runs here.
- Rust toolchain + `make` + qemu for the Theseus build (eval step).

## Plan / scripts to write (keep everything under this folder; gitignore outputs)

1. **Enumerate registers (no SVD → two sources).**
   - Recall denominator: parse the datasheet's **register-summary / memory-map** section
     from `82599.md`.
   - End-to-end target: the register set the **current driver** uses (extract the field
     names + offsets from `reference/src/regs.rs` + `queue_registers.rs`).
   Start with the **driver-needed set** (cheaper, makes the compile metric concrete), then
   layer the datasheet-summary coverage estimate.

2. **Generate** (`pipeline/generate.py`): per register, run the vendored retriever →
   generator (gpt-oss-120b), same prompt module as the MCU pipeline. Config for **recall,
   not precision**: do NOT drop low-confidence specs. Extract structure **and**
   `access_constraints_v2`. Smoke-test on a handful of registers before the full run.

3. **Constraint extraction:** run the grammar-v2 constraint pass on the 82599 registers the
   driver touches (queue enable/disable ordering, link-setup sequences, etc.).

4. **HAL emitter** (`pipeline/emit_hal.py`) — NEW codegen, target format = the current
   `regs.rs`: `#[repr(C)]` region structs, `Volatile/ReadOnly/WriteOnly<u32>` from extracted
   access, `[T; N]` arrays from extracted dims/strides, explicit `_paddingN` from offsets,
   `const _: assert!(size_of == …)` per region. Then layer **witness / type-state gating**
   from `access_constraints_v2` (reuse the enforcement concept from
   `applications/pac_codegen`, retargeted to MMIO). Match the driver's field names/API for a
   drop-in structural layer; gated registers change the API and require driver edits.

5. **Evaluate = clone Theseus and `make`.**
   ```bash
   git clone https://github.com/theseus-os/Theseus theseus_clone   # gitignored
   # swap our generated HAL into theseus_clone/kernel/ixgbe/src/{regs,queue_registers}.rs
   cd theseus_clone && make    # compiler errors reveal missing/wrong specs (the recall signal)
   ```
   Record the compile-error taxonomy (missing register / wrong offset → size-assert fail /
   missing field / missing constraint witness). For the constraint layer, record the
   driver-side diff needed to satisfy the gates.

## Ground rules
- Numbers must be reproducible from committed scripts; record model, retriever sha, commit.
- Self-contained folder; `.gitignore` the generated HAL, `register_info/`, metrics, and
  `theseus_clone/`. Don't touch other worktrees. Smoke-test big runs on small inputs first.
