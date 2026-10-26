# `constraints/` — what each device's crate actually enforces

One file per **(reference manual, device)** pair, named `<rm>_<device>.json`,
written by `inject_from_run.py --save-constraints`. Keyed by manual *and* device
because the mapping is not one-to-one: two manuals can project onto the same PAC
family, and a manual can be measured on two devices.

Each file answers *"show me exactly what you gated, and where it came from"* —
the register, the operations gated on it, the precondition behind each one, the
datasheet sentence that states it, and the tier the quote anchored at, plus
provenance (the generator run, the SVD, and the chunked datasheet the quotes
were verified against). These are the **end** of the pipeline — after collection
lint, emitter selection, access-mode pruning, validator gating and quote
verification. A constraint that appears here survived every stage.

## These files are generated, not committed

The corpus is a derived artifact of the current generator runs and PACs: it
drifts whenever a run directory is regenerated underneath it (the same manual
that recorded 19 gated registers on one run yields 6 on another). Committing it
only bakes in staleness, so this directory holds **only this README** and a
`.gitignore`; regenerate the JSON on demand:

```sh
python applications/pac_codegen/experiments/stm_sweep.py --dry-run --skip-hal
python applications/pac_codegen/experiments/stm_master_pacs.py
cp applications/pac_codegen/experiments/out/constraints/*.json \
   applications/pac_codegen/constraints/
```

`--dry-run` is enough for the sweep (`--save-constraints` writes without touching
a PAC); `stm_master_pacs.py` has no dry mode — it injects and compiles. Both
write into the gitignored `experiments/out/` tree. **Field-level gating is the
default**, so `out/constraints/` is the canonical (field-level) corpus; the
whole-register baseline (`--register-only`) is written separately to
`out/register_only/constraints/`, so the two modes never share a file.

**Expected output: 53 files.** 49 from `stm_sweep.py` (48 manuals, plus rm0440
measured on a second device as a control), 4 from `stm_master_pacs.py`
(rm0493/0505/0529/0530 — crate exists only on stm32-rs master, which the sweep
cannot provision). rm0475 yields none (no chip crate covers STM32MP13x).

## Read one

```sh
python applications/pac_codegen/injected_constraints.py show rm0008 --quotes
python applications/pac_codegen/injected_constraints.py show --all
```

One block per register: the gated operations, each distinct rule once, and with
`--quotes` the datasheet sentence and the tier it anchored at. The raw JSON
repeats a rule once per operation gated, so it reads as duplication; this
dedupes.

## Attribution

`attribution_checked_against` names the chunked datasheet each file's constraints
were verified against — the `--attribution-check` pass runs for all 53. It does
two things: confirms the supporting quote exists in the manual, and confirms it
actually attributes to the register the constraint claims. The second earns its
keep — datasheets say *"this bit"* far more often than they name the register,
so a quote that names none **and** anchors outside the target's section supports
the claim neither textually nor positionally, and its gate is dropped.
