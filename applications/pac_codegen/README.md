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

Full design: [`../../docs/register_constraints_plan.md`](../../docs/register_constraints_plan.md)
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

Current scope (roadmap step B): same-register preconditions on write/modify;
a `write` constraint gates both the write surface and the modify surface. A
same-register **read** gate is rejected as self-defeating (the check performs
the read). Cross-register witnesses = step H; postconditions / action
witnesses = step I.

## Layout

```
applications/pac_codegen/
├── rust_codegen.py          Code generator: RegisterInfo JSON -> gated PAC
├── collect_constraints.py   Bridge: generator run dir -> per-register JSON + manifest
├── get_pac.py               Provision the generated stm32f4 PAC (crates.io, pinned+verified)
├── tests/                   pytest suite (golden diff, compile + enforcement, collection/lint, kind registry)
├── constraint_test/         no_std crate compiled against the injected PAC
│   ├── stm32f405_i2c1.json  Constraint fixture (grammar-v2 RegisterInfo JSON)
│   ├── i2c1_expected_constraints.rs   Golden emitter output
│   └── src/main.rs          Every LEGAL access path (illegal ones live in test_codegen.py)
├── vendored/
│   ├── pac/stm32f4/         Provisioned test PAC (git-ignored; get_pac.py creates it)
│   ├── stm32-rs/            Reference submodules (NOT fetched by default; not
│   └── stm32f4xx-hal/       needed for tests — kept for SVD/HAL reference work)
├── generated/               Runtime codegen output (created on demand)
└── README.md                (this file)
```

## Provisioning the test PAC

svd2rust PAC crates publish their **generated source**, so the pinned crates.io
package is a byte-authentic generated PAC:

```sh
python applications/pac_codegen/get_pac.py     # ~4 MB download, checksum-verified
```

That is the only setup the compile tests need (plus a Rust toolchain).

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
3. **`test_illegal_programs_rejected`** — the enforcement table: nine
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

`collect_constraints.py` scans a generator-output run directory
(`agent_output/<mfg>/<device>/<run>/`), reads each register's
**`access_constraints_v2`** (grammar v2, emitted natively; see
[`../../docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`](../../docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md)),
validates/dedups each constraint, applies the stage-0 lint and repair/reject
policy, computes `enforceability`, and writes per-register JSON plus a grouped
`manifest.json`. Old **v1** runs are converted first with `convert_v1_to_v2.py`.
Validating constraints against the datasheet is the Constraint Validator's job
(plan §7).
