# Hand-authored constraints

Register-access constraints read straight from a datasheet by hand, for cases
where the automated generator under-produced or mis-filed a rule. One file per
reference manual, named `<rm>.jsonl` (e.g. `rm0440.jsonl`), same grammar-v2 record
shape as `evaluation/stm/<rm>/1/<rm>_constraints_review.jsonl`.

## How they're injected

Feed the folder (or a single `<rm>.jsonl`) to the injector with **`--hand-authored`**:

```
inject_from_run.py <run_dir> --pac <pac> --device <dev> \
    --hand-authored applications/pac_codegen/hand_authored_constraints
```

It merges **before planning**: for each `(peripheral, register, kind)` a record
carries, the hand-authored constraint **replaces** the generated one on that
register (and is **added** if the register had none). Everything else passes
through unchanged. This is the injection-side override input (plan item B4).

> NOTE: `--constraints` is **not** the flag for this. That one loads a gate-*map*
> (`id → enforce|doc_only|drop`) that only *filters* constraints already in the
> generated run and ignores the `constraint` body — it can't *add* a hand-authored
> rule. Before `--hand-authored` existed, this folder had no working path into the
> emitter.

Each record: `id`, `rm`, `peripheral`, `register`, `devices`, `constraint`
(the grammar-v2 discriminated union: `kind`, `target_register`, `target_fields`,
`target_operation`, `preconditions`, `postconditions`, `enforceability`, …),
plus `hand_authored: true`, `verdict: "confirmed"` (human-verified), a `source`
citation, and a `note` on scope/generalization.

**Use the kind the emitter actually enforces.** A rule of the form "write R only
when F is in state Z / after F is set" is a **`state_gate`** (target + a
`preconditions` list) — NOT a steps-less `sequence`. A `sequence` must carry a
`steps` list (≥2); a `sequence` with `preconditions` and no `steps` is
grammar-invalid and is rejected at collection.

## rm0440 (STM32G4 HRTIM) — status

The generator produced **one** HRTIM constraint for rm0440 (`common_adc2r`), but
§27 has many. Two clean, witness-enforceable precondition rules are recorded here:

1. **CHP-before-OEN** — `HRTIM_OENR.TxyOEN` write gated by `HRTIM_TIMxOUTR.CHP1/CHP2`
   being set.
2. **TxUDIS-before-preload-write** — `HRTIM_TIMxCMP1R` (and the other preloadable
   timing registers) write gated by `HRTIM_CR.TxUDIS` being set (runtime set-point
   adjustment only).

Both are `state_gate`s (a precondition on the target write). They were first
authored as `sequence` + `action_witnessed`, which is grammar-invalid (no `steps`)
— corrected to `state_gate` so they validate and the current emitter can enforce
them.

**Not yet landing:** even as valid `state_gate`s these prune at injection, because
the datasheet register names (`HRTIM_TIMxOUTR`, `HRTIM_CR`) don't resolve against
the svd2rust PAC's **multi-module HRTIM layout** — the PAC splits HRTIM into
`hrtim_master` / `hrtim_tima..f` / `hrtim_common`, so `HRTIM_TIMAOUTR` lives at
`hrtim_tima::outr`, which the cross-register resolver doesn't bridge. Landing them
needs that name mapping, not a change to the kind. (By contrast `mk20d7.jsonl`'s
FTM_FILTER `state_gate` resolves cleanly — FILTER and QDCTRL share one module — and
is caught in mk20dx-hal.)

Left out on purpose: the **preload mechanism itself** (`PREEN`, write→shadow→
update-event) is a write-effect/timing behavior that doesn't map cleanly to the
gate grammar, and the **BKDSRM re-arm poll** is a runtime `dynamic_check` (poll
until hardware clears) with no compile-time witness. Both are real but not "clean"
for witness gating.
