# `constraints/` — what each device's crate actually enforces

One file per **(reference manual, device)** pair, named `<rm>_<device>.json`,
written by `inject_from_run.py --save-constraints`. Keyed by manual *and*
device because the mapping is not one-to-one: two manuals can project onto the
same PAC family, and a manual can be measured on two devices.

Each file is the answer to *"show me exactly what you gated, and where it came
from"* — the register, the operations gated on it, the precondition behind
each one, the datasheet sentence that states it, and the tier the quote
anchored at. Plus provenance: the generator run, the SVD, and the chunked
datasheet the quotes were verified against.

These are the **end** of the pipeline, after collection lint, emitter
selection, access-mode pruning, validator gating and quote verification. A
constraint that appears here survived every stage.

## Regenerating

```sh
python applications/pac_codegen/experiments/stm_sweep.py --dry-run --skip-hal
cp applications/pac_codegen/experiments/out/constraints/*.json \
   applications/pac_codegen/constraints/
```

`--dry-run` is enough: `--save-constraints` writes without touching a PAC.
The sweep's own copies land in the gitignored `experiments/out/` tree; this
directory is the committed, reviewable set, so it is only ever updated
deliberately.

## Gating mode

`field_level_gating` in each file records which mode produced it. The two
modes plan **different** gate sets, so a file from one cannot be read as the
other. Everything committed here is whole-register (`false`); the field-level
sweep writes `<rm>_<device>_fieldgate.json` and stays in `out/`.

## One caveat on reading these

They describe the *pipeline as it stands*, not a frozen result. The rm0008
artifact committed on 2026-07-29 recorded 19 gated registers; the same manual
yields 6 today, because the generator run directory was regenerated underneath
it. `docs/stm_injection_sweep.md` §5 analyses that divergence and cites the
old file by git revision. Regenerate this directory whenever the run
directories change, or it drifts the same way.
