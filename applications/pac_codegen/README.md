# applications/pac_codegen/ — witness-gated PAC application

This is the **enforcement arm** of LIDAR: it turns extracted register **access
constraints** (dependency / ordering invariants from datasheets) into
compile-time–safe Rust for STM32 Peripheral Access Crates (PACs). A
constrained register write requires a **witness token** minted by the
datasheet-prescribed check, so an illegal access sequence fails to compile in
any downstream crate.

This is one application under [`../`](../); the layout arm (SVD-diff
bug-finding and reporting) is a separate sibling. See [`../README.md`](../README.md).

## The encoding: trait gating (no wrappers, no shadowing)

Full design: [`../../docs/register_constraints_design.md`](../../docs/register_constraints_design.md)
(§3 + Appendix A). In short:

- The stock `Reg::write` / `modify` / `read` / `reset` / `write_with_zero` /
  `from_*` methods in `generic.rs` gain a
  `where REG: UnconstrainedWrite/Modify/Read` bound.
- Every **unconstrained** register gets one-line marker impls — its API stays
  byte-identical.
- A **constrained** register gets NO marker for the gated operation, so the
  witness-free method *does not exist* for it. Violations surface downstream
  as **E0277 with a custom message** (via `#[diagnostic::on_unimplemented]`):
  *"`CR1rs` is write-constrained by its datasheet — call
  `write_witnessed(f, witness)` or `write_when_ready(f)` …"*.
- Witness types ride on `WriteGate`/`ModifyGate`/`ReadGate` traits implemented
  only by constrained registers; `check_write_ready()` mints a witness from
  ONE fresh volatile read of all preconditions; `write_when_ready(f)` welds
  check + write into one call (the recommended entry point — the witness never
  escapes user code).
- The only bypasses are `unsafe` (`write_unwitnessed`, …) — greppable, and
  there is no `Deref` hole: an ascribed `&Reg<CR1rs>` reference or a UFCS call
  hits the same E0277 (pinned as compile-fail regressions).

Current scope: same-register preconditions on write/modify; a `write`
constraint gates both the write surface and the modify surface. A same-register
**read** gate is rejected as self-defeating (the check performs the read).
Cross-register witnesses = step H; postconditions / action witnesses = step I.

**Field-level gating is the default.** A constraint that names fields is
enforced on the field's writer accessor alone, leaving sibling fields free —
rather than widened to the whole register, which would demand the precondition
for writes to unrelated fields. `--register-only` reverts to whole-register-only
gating, the baseline every previously published number was measured against;
field granularity recovers 602 registers and 1,068 obligations that baseline
discarded. The two modes plan different gate sets and their artifacts are never
mixed. Known bypass, warned about on every
injection: a purely field-gated register's whole-register `write`/`reset` stay
ungated, since `write()` sets unnamed fields to their reset value without
touching the accessor. A register that ALSO carries a register-scoped write
gate has no such hole.

## Layout

```
applications/pac_codegen/
├── rust_codegen.py          The emitter: RegisterInfo JSON -> gated PAC
├── inject_from_run.py       End-to-end driver: generator run dir -> gated PAC
├── get_pac.py               Provision a PAC from crates.io (pinned + checksum-verified)
├── show_injected_constraints.py   Read a device's applied constraints out loud
├── convert_v1_to_v2.py      The ONE tool that still parses the retired v1 grammar
├── constraints/             README + .gitignore; the per-device JSON record is
│                             generated on demand (see constraints/README.md)
├── rm_pac_mappings/stm.toml Manual -> PAC crate -> device -> HAL consumer
├── constraint_test/         no_std crate + 4 fixtures + golden emitter output
├── eval_hal/                The original single-pairing HAL demo (drives test_hal_demo)
├── experiments/             The measurement layer -- see experiments/README.md
├── tests/                   pytest suite, 20 files, ~179 tests
└── vendored/                pac/ (21 released crates), pac_master/ (2 from
                             stm32-rs master), pac_old/ (3 of the 0.14/0.15
                             generation) -- all git-ignored
```

The constraint lift and stage-0 lint live in **`core/collect_constraints.py`**,
not here: they are pipeline stages this application consumes, not part of it.

## Provisioning the test PAC

svd2rust PAC crates publish their **generated source**, so the pinned crates.io
package is a byte-authentic generated PAC:

```sh
python applications/pac_codegen/get_pac.py                        # pinned stm32f4 0.16.0
python applications/pac_codegen/get_pac.py --crate stm32f1 --version 0.16.0
python applications/pac_codegen/get_pac.py --force                # restore after injection
```

The no-argument form is the only setup the compile tests need (plus a Rust
toolchain). `--force` is the one to remember: injection is one-shot from a
pristine crate, and a crate left injected by an interrupted run is the most
common way a run here fails for a reason unrelated to what it measures.

## Generating constrained Rust

```sh
# Standalone module (what the golden test diffs):
python applications/pac_codegen/rust_codegen.py \
    applications/pac_codegen/constraint_test/stm32f405_i2c1.json \
    --peripheral i2c1 --output applications/pac_codegen/generated/i2c1/constraints.rs

# Inject into the provisioned PAC (patches generic.rs, adds marker impls to
# every register file, appends the constraints module to the peripheral):
python applications/pac_codegen/rust_codegen.py \
    applications/pac_codegen/constraint_test/stm32f405_i2c1.json \
    --peripheral i2c1 \
    --inject-pac applications/pac_codegen/vendored/pac/stm32f4 \
    --device stm32f405
```

Injection is **one-shot from a pristine PAC** (it refuses to run twice);
restore with `get_pac.py --force`. The tests snapshot and restore the tree
around every case automatically.

## Testing

```sh
python applications/pac_codegen/tests/test_codegen.py     # or under pytest
```

1. **`test_codegen_matches_golden`** (always runs, no toolchain) — emitter
   output vs the committed golden.
2. **`test_constraint_test_compiles`** — inject + `cargo check` the crate of
   legal paths.
3. **`test_illegal_programs_rejected`** — the enforcement table: a set of
   adversarial programs each asserted to fail with a specific error code and
   diagnostic (witness-less calls → E0277 + datasheet message; witness reuse →
   E0382; wrong-operation witness → E0308; the old shadowing design's safe
   `&Reg` bypass → E0277, pinned forever).

Skip policy: without cargo or the provisioned PAC, the compile tests SKIP so a
fresh clone passes — except under `LIDAR_REQUIRE_PAC_TESTS=1` (CI sets it,
`.github/workflows/pac-codegen.yml`), where any would-be skip is a hard
failure. Silently-skipped enforcement tests are how a non-compiling generator
once shipped; the flag makes that impossible in CI.

## The constraint-collection bridge

`core/collect_constraints.py` scans a generator-output run directory
(`agent_output/<mfg>/<device>/<run>/`), reads each register's
**`access_constraints_v2`** (grammar v2, emitted natively; see
[`../../docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`](../../docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md)),
validates/dedups each constraint, applies the stage-0 lint and repair/reject
policy, computes `enforceability`, and writes per-register JSON plus a grouped
`manifest.json`. Old **v1** runs are converted first with `convert_v1_to_v2.py`.
Validating constraints against the datasheet is the Constraint Validator's job
(plan §7).

## End to end: a run directory in, a gated PAC out

`inject_from_run.py` is the driver. It re-runs collection over the run
directory, keeps only what the validator confirmed, plans a gate per register,
resolves instance collisions, checks each quote still attributes to its
register, and injects — reporting every constraint it dropped and why.

```sh
python applications/pac_codegen/inject_from_run.py \
    <phase1d>/agent_output/stm/rm0008/1 \
    --pac applications/pac_codegen/vendored/pac/stm32f1 --device stm32f103 \
    --svd-dir <phase1d>/devices/stm/rm0008/svd/stm32f103.svd \
    --constraints <phase1d>/evaluation/stm/rm0008/1/rm0008_constraints_review.jsonl \
    --attribution-check <phase1d>/chunked_datasheets/stm \
    --report out/rm0008.json --save-constraints constraints/rm0008_stm32f103.json
```

| flag | what it gates on | older name |
|---|---|---|
| `--constraints` | the review ledger; only `enforcement: enforce` compiles | `--validated` |
| `--attribution-check` | the chunked datasheet; drops a gate whose quote does not attribute to its register | `--chunks`, `--verify-evidence` |
| `--save-constraints` | writes the per-device record into `constraints/` (generated; git-ignored) | |
| `--register-only` | whole-register baseline; **field gating is the default** (see above) | `--field-level-gating` (now a no-op) |

Both old flag names still work. `--dry-run` does everything except touch the
PAC, and still writes the report and the constraints file.

To do this for the whole corpus — and compile real drivers against the result —
use `experiments/stm_sweep.py`; see [`experiments/README.md`](experiments/README.md).

## Reading the result

```sh
python applications/pac_codegen/show_injected_constraints.py rm0008 --quotes
python applications/pac_codegen/show_injected_constraints.py --all
```

One block per register: the operations gated, each distinct rule once, and with
`--quotes` the datasheet sentence and the tier it anchored at. The header
states the two facts that decide how a file may be compared to any other —
which gating mode produced it, and whether it was attribution-checked.
