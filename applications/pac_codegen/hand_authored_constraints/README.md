# Hand-authored constraints

Register-access constraints read straight from a datasheet by hand, for cases
where the automated generator under-produced. One file per reference manual,
named `<rm>.jsonl` (e.g. `rm0440.jsonl`), same grammar-v2 record shape as
`evaluation/stm/<rm>/1/<rm>_constraints_review.jsonl` so they can feed
`inject_from_run.py --constraints` (alongside or instead of the generated set).

Each record: `id`, `rm`, `peripheral`, `register`, `devices`, `constraint`
(the grammar-v2 discriminated union: `kind`, `target_register`, `target_fields`,
`target_operation`, `preconditions`, `postconditions`, `enforceability`, …),
plus `hand_authored: true`, `verdict: "confirmed"` (human-verified), a `source`
citation, and a `note` on scope/generalization.

## rm0440 (STM32G4 HRTIM) — why it's here

The generator produced **one** HRTIM constraint for rm0440 (`common_adc2r`),
but §27 clearly has many. The two clean, witness-enforceable ordering rules:

1. **CHP-before-OEN** — chopper bits (`CHP1/CHP2` in `HRTIM_TIMxOUTR`) must be
   set before enabling the output (`TxyOEN` in `HRTIM_OENR`). Unconditional
   `sequence`.
2. **TxUDIS-before-preload-write** — before re-writing preloadable timing
   registers at runtime, freeze updates (`TxUDIS` in `HRTIM_CR`). Conditional
   (runtime set-point adjustment); a `sequence`.

Left out on purpose: the **preload mechanism itself** (`PREEN`, write→shadow→
update-event) is a write-effect/timing behavior that doesn't map cleanly to the
gate grammar, and the **BKDSRM re-arm poll** is a runtime `dynamic_check` (poll
until hardware clears) with no compile-time witness. Both are real but not
"clean" for witness gating.
