# applications/pac_codegen/ — linear-types PAC application

This is the **enforcement arm** of LIDAR: it turns extracted register **access
constraints** (dependency / ordering invariants from datasheets) into
compile-time–safe Rust for STM32 Peripheral Access Crates (PACs). The design
uses affine witness proofs — a constrained register write requires a non-`Copy`
composite proof that all hardware preconditions were checked, so an illegal
access sequence fails to compile.

This is one application under [`../`](../); the layout arm (SVD-diff bug-finding
and reporting) is a separate sibling. See [`../README.md`](../README.md).

## Layout (separation of concerns)

```
applications/pac_codegen/
├── rust_codegen.py          Code generator: RegisterInfo JSON -> Rust constraint modules
├── collect_constraints.py   Bridge: generator run dir -> per-register constraints JSON
├── constraint_test/         Standalone Rust crate that compiles the generated, injected code
│   ├── stm32f405_i2c1.json  Example constraint fixture (RegisterInfo JSON) — input to rust_codegen.py
│   ├── src/main.rs          (a no_std compile test of the safe/unsafe access paths)
│   ├── Cargo.toml
│   ├── Cargo.lock
│   └── .gitignore           (ignores /target build cache)
├── vendored/                The two upstream PACs, registered as git submodules
│   ├── stm32-rs/            (NOT checked in; fetch on demand — see below)
│   └── stm32f4xx-hal/
├── constraints/             Bridge output: collected constraints (created on demand)
├── generated/               Runtime codegen output (created on demand)
└── README.md                (this file)
```

The constraint grammar/design lives at
[`../../docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`](../../docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md).
Other PAC design docs live under [`../../docs/pac/`](../../docs/pac/):
`SVD2RUST_PAC_GUIDE.md` and the phased change logs/plans
(`PHASE2_CHANGES.md`, `PHASE3_CHANGES.md`, `PHASE4_PLAN.md`).

## Vendored PACs are git submodules

The two PACs are pinned **submodules**, not vendored source — the ~1.5 GB of PAC
code is *not* committed here; only commit pointers (gitlinks) are. Fetch them
on demand:

```sh
git submodule update --init applications/pac_codegen/vendored/stm32-rs
git submodule update --init applications/pac_codegen/vendored/stm32f4xx-hal
```

Pinned to the same commits the PAC fork used:
`stm32-rs` @ `75790df` (v0.16.0) and `stm32f4xx-hal` @ `eca3bd5` (v0.23.0-7).

`rust_codegen.py` **patches** the checked-out `stm32-rs` PAC in place (it edits
`generic.rs` to widen field visibility and add a `ConstrainedReg<REG>` wrapper,
and injects a `pub mod constraints { … }` into the target peripheral's
`mod.rs`). Run it against the submodule checkout after fetching; re-run
`git submodule update` to discard the patches.

## Generating constrained Rust

`rust_codegen.py` reads a `RegisterInfo` JSON (shared schema from the repo-root
`defs.py`) and emits a Rust constraints module — either standalone or injected
into a PAC:

```sh
# Standalone module:
python applications/pac_codegen/rust_codegen.py \
    applications/pac_codegen/constraint_test/stm32f405_i2c1.json \
    --peripheral i2c1 --output applications/pac_codegen/generated/i2c1/constraints.rs

# Inject into the (fetched) PAC and patch generic.rs:
python applications/pac_codegen/rust_codegen.py \
    applications/pac_codegen/constraint_test/stm32f405_i2c1.json \
    --peripheral i2c1 \
    --inject applications/pac_codegen/vendored/stm32-rs/stm32f4/src/stm32f405/mod.rs
```

For each constrained operation, verification performs one fresh read of every
register named by its preconditions and returns an operation-specific proof with
a private constructor. Same-register rules use an inherent
`verify_*_ready()` method. Cross-register rules use a peripheral-level function
such as `constraints::verify_mtqc_modify_ready(&rttdcs)`, which receives the
relevant register handles and reads them internally. `write`,
`modify`, and `read` constraints produce distinct proof types, so proof for one
operation cannot authorize another. A write constraint gates `write`, `reset`,
`write_with_zero`, and `from_write`; a modify constraint gates `modify` and
`from_modify`; a read constraint gates `read`. Unconstrained operations retain
the stock PAC methods through `Deref`.

Cooperative developers can intentionally bypass enforcement through the
explicit unsafe facade:

```rust
unsafe {
    i2c1.cr1().bypass_constraints().write(|w| w.pe().enabled());
}
```

`Deref<Target = Reg<REG>>` remains for PAC compatibility, so a fully qualified
`Reg` call is also a possible low-level escape. The named facade is preferred
because it makes the decision to override a datasheet procedure visible and
auditable.

`constraint_test/` is a minimal `no_std` crate that compiles the injected PAC and
exercises both the safe (proof-bearing) and would-be-unsafe access paths, serving
as a compile-time regression check. Its `Cargo.toml` depends on the vendored PAC
via the relative path `../vendored/stm32-rs/stm32f4`, so it builds once the
submodule above is fetched.

## The constraint-collection bridge

`collect_constraints.py` establishes the datasheet → extraction → codegen data
path. It scans a generator-output **run directory**
(`agent_output/<mfg>/<device>/<run>/`, one file per register named
`{peripheral}_{register}`), reads each register's `access_constraints`, and
writes per-register `RegisterInfo` JSON files plus a grouped `manifest.json`:

```sh
python applications/pac_codegen/collect_constraints.py agent_output/stm/rm0041/24 \
    --output-dir applications/pac_codegen/constraints/rm0041_24

python applications/pac_codegen/rust_codegen.py \
    --manifest applications/pac_codegen/constraints/rm0041_24/manifest.json \
    --peripheral i2c1 \
    --output applications/pac_codegen/generated/i2c1/constraints.rs
```

Manifest codegen emits one flat constraints module per peripheral, allowing
proof verifiers to refer to source registers other than the constrained target.
Injection adds that module once and converts every constrained target register
alias to `ConstrainedReg`.

It only **collects and forwards** dependency invariants. This application treats
its inputs as already validated and does not check consistency, satisfiability,
or datasheet fidelity; the pipeline validator in `core/s4_validator.py` is left
untouched.

## TODO: advanced constraint forms

- **Multi-step precondition/postcondition procedures:** Rules such as “set
  ARBDIS, configure MTQC, then clear ARBDIS” need more than a precondition
  witness. A future implementation should generate a closure-scoped typestate
  session: generated code performs the required setup and cleanup, while the
  closure receives a restricted API exposing only operations valid during the
  intermediate state.
- **Field-level constraints:** The current design promotes the whole register to
  `ConstrainedReg`. A future implementation may generate restricted writer
  types so writes to unconstrained fields remain available without proof while
  constrained fields require it.

Both features are intentionally deferred until the application has enough
representative datasheet examples to establish the right generated API.

## Testing

`test_codegen.py` is the regression guard for the code generator. Run it
directly or under pytest:

```sh
python applications/pac_codegen/test_codegen.py
# or: pytest applications/pac_codegen/test_codegen.py
```

- **`test_codegen_matches_golden`** (always runs) regenerates the constraints
  module from `constraint_test/stm32f405_i2c1.json` and diffs it against the
  committed golden `constraint_test/i2c1_expected_constraints.rs`. Any change to
  `rust_codegen.py`'s output fails this with a diff — if the change is intended,
  refresh the golden (see its header for the one-line command).
- **`test_constraint_test_compiles`** injects into the PAC and `cargo check`s the
  `constraint_test` crate (legal, proof-bearing paths) — it must pass.
- **`test_cross_register_proofs_compile_and_enforce`** checks a synthetic
  CR2→CR1 rule, including the legal verifier flow and rejection of missing or
  operation-mismatched proofs.
- **`test_unconstrained_operations_fail_to_compile`** injects and checks every
  ordinary write-capable method without proof, plus a program that reuses a
  consumed proof or passes proof for the wrong operation. They must be rejected
  with `E0061`, `E0382`, and `E0308`, respectively.

The two `cargo check` tests **skip** (they do not fail) unless `cargo` is on
PATH **and** a *generated* `stm32f4` PAC exists at
`vendored/stm32-rs/stm32f4/src/`. The `stm32-rs` submodule ships SVDs and the
build system but **not** the generated crate, so fetching the submodule alone is
not enough — the PAC must be generated first (svd2rust). They use `cargo check`
rather than `cargo build` because the constraint enforcement is a front-end type
error; a full build would codegen the Cortex-M PAC for the host and fail for
unrelated target reasons. Each test backs up, restores, and verifies the PAC
(and its own `main.rs`) so a run leaves the tree untouched.
