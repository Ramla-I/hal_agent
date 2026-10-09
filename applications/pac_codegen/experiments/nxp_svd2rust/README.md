# NXP svd2rust injection

Can the svd2rust witness-gating arm (the one built for stm32-rs PACs) inject the
constraints we extracted for NXP devices into NXP's *published* PACs, and do the
injected crates still compile? This experiment runs the whole arm over every NXP
device for which we have (a) confirmed access constraints and (b) a published
svd2rust PAC on crates.io.

## Why this needed emitter work

The stm32-rs PACs are all one svd2rust flavour. NXP's published PACs are not —
they span **five svd2rust versions in two generic.rs dialects** plus three
distinct `RegisterSpec` / field-reader naming conventions:

| svd2rust | PACs | generic.rs | RegisterSpec | 1-bit reader |
|---|---|---|---|---|
| 0.19–0.21 | lpc55, ke04, s32k1xx, lpc845 | **early** (`REG::Writer` closures, no return, no `from_*`/atomics, no `Reg` Debug) | `CTRL_SPEC` | `struct X_R(FieldReader<bool,..>)` |
| 0.35–0.37 | mimxrt685s/633s, mk20d5/d7 | **modern** (`W<REG>` closures, `-> REG::Ux`, `from_*`) | `CtrlSpec` | `type SeqidleR = BitReader` |
| (stm32-rs) | stm32* | **modern** | `CRrs` | `type X_R = BitReader` |

The injector (`rust_codegen.py`) is now dialect-aware: it detects the generic.rs
dialect, emits the matching witnessed surface, **discovers** each register's
`RegisterSpec` name from the PAC instead of deriving it, resolves the flat
single-device instance map (`impl Deref for I2C1 { Target = i2c0::.. }`), and
reads all three field-reader forms. See the commit "make the svd2rust injector
dialect-aware for NXP PACs".

## What the run does (`run_all.py`)

Per device: provision the crates.io PAC → stage its SVD → `inject_from_run.py`
(generator run + human-reviewed constraint ledger → gated PAC, `--device .` for
the flat single-device layout) → `cargo build --lib`. Inputs (constraint ledgers
and generator runs) come from the sibling `hal_agent-phase-1d` worktree (the NXP
full-sweep campaign); nothing here regenerates them.

```sh
python run_all.py            # all devices
python run_all.py lpc55s69   # one
```

## Results

**8 of 9 devices inject and compile** — covering both generic.rs dialects and
all three naming conventions — gating **149 registers** in total from the
confirmed constraint ledgers. (`summary.json` / `run_all.log` are authoritative.)

| device | PAC (crates.io) | svd2rust | registers gated | compiles |
|---|---|---|--:|:--:|
| lpc55s69 | lpc55-pac 0.5.0 | 0.20 (early) | 8 | ✅ |
| ke04 | ke04z4-pac 0.1.0 | 0.19 (early) | 8 | ✅ |
| s32k1xx | s32k144-pac 0.1.0 | 0.21 (early) | 28 | ✅ |
| lpc845 | lpc845-pac 0.4.1 | 0.19 (early) | 3 | ✅ |
| mk20d7 | mk20d7-pac 0.1.1 | 0.37 (modern) | 31 | ✅ |
| mk20d5 | mk20d5-pac 0.1.1 | 0.37 (modern) | 33 | ✅ |
| mimxrt685s | mimxrt685s-pac 0.5.0 | 0.35 (modern) | 17 | ✅ |
| mimxrt633s | mimxrt633s-pac 0.5.0 | 0.35 (modern) | 21 | ✅ |
| k64 | k64 0.1.0 | **0.14** | — | — (out of scope) |

**k64** is out of scope: its published PAC is svd2rust **0.14.0**, which predates
the shared `generic.rs` / `Reg<REG>` proxy the gating rides on — there is no
generic method surface to bound. Injecting it would require regenerating the PAC
from `MK64F12.svd` with a modern svd2rust (the "regenerate" path, not the
"inject the published crate" path this experiment uses). k64 has no HAL or
downstream users, so this is a low-value gap.

A within-dialect sub-variant surfaced: svd2rust **0.35** (mimxrt) writes
`REG::Ux::default()` where **0.37** (mk20) and stm32-rs write `REG::Ux::ZERO` in
`write_with_zero`; `patch_generic_rs` mirrors whichever the stock crate uses.

## Notes / limitations

- `k32l3a60` has no crates.io PAC (svd2rust source never published), so it is not
  in this set even though we have its constraints.
- Field-level gating is ON by default here (`inject_from_run` default; pass
  `--register-only` to disable) — a field-scoped constraint gates the field's
  writer accessor as an advisory, the whole-register ones are the hard gate.
- The gate is proven to bite on lpc55 (a witness-free `I2C MSTCTL` write fails
  with `E0277: MSTCTL_SPEC is write-constrained by its datasheet`); compilation
  of the whole injected crate is the per-device check here.
