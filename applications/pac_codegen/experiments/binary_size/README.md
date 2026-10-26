# Injection cost: source LOC vs. binary size

How much does the constraint injection *cost*? Two numbers, measured here:

- **Source:** it adds **5k–123k generated lines per PAC crate** (field-level
  gating, the injection default), 33–95% of it zero-cost marker scaffolding and
  the rest gate-proportional enforcement code.
- **Binary:** it adds **0 bytes** to the compiled firmware — the executable code
  (`.text`) is byte-identical to a build against the un-injected PAC. The gating
  is marker traits + zero-sized witnesses + trait bounds, all erased by
  monomorphisation and dead-code elimination. The only runtime cost is a handful
  of bytes per opt-in checked write (`write_when_ready`) — the datasheet
  precondition check itself; `verify_binary_size.py` measures the exact count
  (**+12 bytes** for the RCC.BDCR/DBP check, recorded in `binary_size.json`).

Companion to `docs/injection_tracking.md` (which reports gates/constraints per
crate); this directory reports the *code-size* cost.

## Files

| file | what |
|---|---|
| `measure_injection_loc.py` | inject every crate, diff vs pristine → `injection_loc.json` (no cargo) |
| `injection_loc.json` | measured LOC per (rm, device, crate): total / enforcement modules / scaffolding |
| `plot_injection_cost.py` | render the single-column figure from the JSON → `.svg` + `.html` |
| `pac_injection_cost.svg` | the figure (LaTeX drop-in) |
| `verify_binary_size.py` | build `sizefw/` against pristine vs injected, compare `.text` (needs cargo) |
| `sizefw/` | minimal firmware that writes only *ungated* registers, so it builds against either PAC |

## Regenerate

```sh
# 1. LOC per crate (field-level default; --register-only for the whole-register variant)
python measure_injection_loc.py           # ~10 min, no cargo; writes injection_loc.json

# 2. the figure
python plot_injection_cost.py             # writes pac_injection_cost.{svg,html}

# 3. the binary-size claim (needs cargo + thumbv7em-none-eabihf)
python verify_binary_size.py              # builds sizefw twice, compares .text
```

`measure_*` and `verify_*` read PAC crates from `../../vendored/pac` (the pinned
0.16.0 corpus) and `../../vendored/pac_master` (the two master-only crates,
`stm32wba`/`stm32wb0`), and pipeline artifacts from the sibling
`hal_agent-phase-1d` worktree — the same conventions as `experiments/stm_sweep.py`.

## The figure

One bar per PAC crate (23), each the device with the **most** injected lines,
split into marker scaffolding (zero-cost) vs enforcement modules, sorted by size.
The paired stat shows the contrast: large in source, **+0 bytes** in the binary.
Use in LaTeX with `\includegraphics[width=\columnwidth]{pac_injection_cost}`
(SVG → PDF via `rsvg-convert -f pdf` or Inkscape).
