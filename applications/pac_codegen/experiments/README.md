# `experiments/` — what each script is for

These are not unit tests. Each one answers a question the enforcement arm ran
into, in roughly the order the questions arrived: *where can this be tried at
all → what happens when it is → what does a failure mean → does any of it
generalise.* Read them in that order and the folder tells a story; read them
alphabetically and it looks like a pile.

A few of the files are **shared libraries, not experiments** — imported by the
others, not run on their own. They are listed in their own section at the end,
so the rest of the folder reads as the experiments it is.

**Everything writes to `out/`, which is gitignored.** The reports there are the
only durable record of a run, so a result nobody copied out of `out/` is a
result nobody can check. The committed artifacts live elsewhere, and are
**regenerated, not hand-kept**: `../constraints/` (what each device gates — see
its README) and `docs/artifacts/` (the rendered pages).

**All of them read the pipeline's output from a sibling worktree**,
`/home/ramla/hal_agent-phase-1d` — the generator runs, the SVDs, the validated
constraints, the chunked datasheets. That path is a module constant (`DATA` or
`PHASE1D`); to reproduce elsewhere, point it at your own run tree.

**The three-stage finding story — compile it, read it, make more of it
compilable — is written up in
[`../../../docs/PAC_CODEGEN.md`](../../../docs/PAC_CODEGEN.md#finding-violations-in-real-code),
with current numbers. This file is the per-script index.**

---

## Where can this be tried at all?

| script | question | output |
|---|---|---|
| `build_map.py` | which manual maps to which PAC crate, device module and HAL — and is each pairing still true? | `out/injection_map.json` |

It re-checks every HAL pairing against the live crates.io index rather than
trusting `../rm_pac_mappings/stm.toml`, whose data was hand-verified once. A
pairing that has drifted is how an experiment silently measures the wrong crate.

## The main measurement — compile real drivers against injected PACs

| script | question | output |
|---|---|---|
| `stm_sweep.py` | inject every manual into its PAC and compile real drivers against it — what breaks? | `out/` (field gating, the default) or `out/register_only/` (`--register-only`) |
| `stm_master_pacs.py` | same, for the 4 manuals whose crate exists only on stm32-rs master | `out/stm_master_pacs.json` |
| `gen_injection_tracking_artifact.py` | turn every report into the published per-manual table | `out/tracking.csv`, `docs/artifacts/injection_tracking.{md,html}` |

`stm_sweep` is the one to reach for. Per target it provisions the PAC,
**snapshots** it, injects, compiles a probe crate and the paired HAL, restores,
and asserts the tree is byte-for-byte pristine — targets share crates (four
manuals share `stm32f3`), so a crate left dirty contaminates the next run.

```sh
python applications/pac_codegen/experiments/stm_sweep.py --only rm0008
python applications/pac_codegen/experiments/stm_sweep.py --dry-run --skip-hal
python applications/pac_codegen/experiments/stm_sweep.py --register-only   # baseline
```

**Field-level gating is the default.** A constraint that names fields gates
only those fields' writer accessors; one that names none gates the register.
`--register-only` is the old behaviour — whole registers only, field-scoped
constraints skipped — kept because every previously published number was
measured that way, and the comparison should be runnable rather than asserted.
Its artifacts go to `out/register_only/`, a separate tree: the two modes plan
different gate sets, and a shared path once let one overwrite the other.

`gen_injection_tracking_artifact.py` reads results, never recomputes them: every
number in the published table traces to a file in `out/`.

## Whole applications and downstream crates

`stm_sweep` compiles the paired HAL; these go further — real firmware, flight
software, and the crates that depend on a swept HAL — each a compiler verdict on
source nobody wrote for this.

| script | question | output |
|---|---|---|
| `port_blackpill.py` | the first whole **application** built against an injected PAC — does it still compile, with zero edits? | `out/port_blackpill.json` |
| `port_elodin.py` | compiler verdicts inside commercial flight software (patched via `patches/elodin`) | `out/port_elodin.json` |
| `port_anne_key.py` | does the source **scanner** agree with the **compiler** on the same project? | `out/port_anne_key.json` |
| `port_stm32_eth.py` | confirm a **true negative** against the compiler — a site the gate must NOT flag | `out/port_stm32_eth.json` |
| `dependent_compile.py` | do the HAL's gated bug-sites actually ship in its dependents' builds? | `out/` |
| `hopter.py` | a real embedded OS against an injected PAC | `out/hopter.json` |

## Nothing to compile against — make more measurable

Four community HALs could not be measured at all: their newest release still
depends on an older svd2rust PAC generation than the injector targets.

| script | question | output |
|---|---|---|
| `hal_gap.py` | how far is each unpaired HAL from PAC 0.16? | `out/hal_gap.json` |
| `old_pac_probe.py` | could the injector just target the OLD PAC generation instead? | `out/old_pac_probe.json` |
| `port_hal.py` | upgrade the HAL to PAC 0.16 — mechanically, provably | `out/port_hal.json`, `ported/` |
| `port_hubris.py` | same for Hubris, which has no HAL at all | `out/port_hubris.json` |
| `measure_ported.py` | what do the gates find in what the upgrade made visible? | `out/measure_ported.json` |

`port_hal.py` is the load-bearing one, and its discipline is the point: it
applies **only** rustc's own suggestions for the two diagnostics that mark the
field-to-accessor change, and `--verify` re-reads every edit and fails if any
changed a byte other than inserting `()`. That is what makes *"the driver's
control flow is untouched"* a checked claim rather than an assurance — without
it, "we upgraded the HAL" and "we fixed the HAL" are indistinguishable.

## A compile error is not automatically a bug

| script | question | output |
|---|---|---|
| `corroboration.py` | does the driver already perform the datasheet check at this site? | stdout only |
| `friction.py` | what causes generic friction, and what would remove it? | `out/friction.json` |
| `trace_hal.py` | does a constraint ever reach the APPLICATION, or does the driver absorb it? | `out/trace_hal.json` |
| `bitband_scan.py` | which register writes evade the gate entirely — bit-banding, raw pointers? | `out/bitband_scan.json` |

`corroboration.py` splits *guarded* from *candidate bug*: it scans back to the
enclosing function, looks for the precondition's field accessor before the
flagged line, then puts a calibrated closed-book judge on the disagreements and
shortlists those for a human. `friction.py` measures the cost side — a HAL
generic over register blocks needs the marker bounds even where nothing is
constrained. `trace_hal.py` asks who the enforcement actually protects.
`bitband_scan.py` is the honest-limits probe: it finds the writes the gate can
*never* see, because they go around the typed API.

## Beyond what can be compiled — scan the source instead

Every remaining candidate project pins an older HAL or PAC, so building first
and looking second does not scale.

| script | question | output |
|---|---|---|
| `scan_projects.py` | find constrained register accesses in third-party source, WITHOUT compiling | `out/scan_projects.json` |
| `dependent_scan.py` | scan every crates.io **dependent's** own source for constrained accesses | `out/`, `hal_dependents_census.json` |
| `landscape_page.py` | publish that scan as a page | `docs/artifacts/project_landscape.html` |

## Adjudicate and publish

| script | question | output |
|---|---|---|
| `bug_review.py` | step through the sweep's possible-bug sites and record tp/fp — the human ledger | `../bug_review/` CSV tree |
| `coverage_page.py` | the STM32 PAC → HAL & ecosystem coverage artifact | a page, reproducible from the records |

## Does any of this generalise?

| script | question | output |
|---|---|---|
| `cross_pac.py` | the injector was built against stm32f4 — does it work unchanged elsewhere? | stdout only |
| `check_pac_generation.py` | would a NEWER svd2rust break the injector? | `out/check_pac_generation.json` |

`cross_pac.py` is what `stm_sweep` generalises from: four hand-picked fixtures
(`fixtures/`), proving the injector was not stm32f4-shaped. `check_pac_generation.py`
guards the pin — the corpus is on svd2rust 0.36.1, and it answers the upgrade
question by running the newer generator, not by reading its changelog.

---

## Shared libraries (imported by the experiments, not run on their own)

| module | role | imported by |
|---|---|---|
| `enforcement.py` | the one place that decides what an enforcement hit *is* — every experiment that classifies a site calls it, so the definition lives in exactly one spot | 12 scripts |
| `corroboration.py` | the guarded-vs-candidate-bug split and the closed-book judge (also runnable on its own, above) | 8 scripts |

`stm_sweep.py` and `scan_projects.py` are runnable experiments (above) that other
scripts also import — treat their public functions as an interface.

## Subdirectories

- [`binary_size/`](binary_size/README.md) — the injection's **cost**: source LOC
  added per crate, and the firmware-binary bytes (large in source, ~free in the
  binary). Measurement JSON is committed (re-measuring needs a full build); the
  rendered figure regenerates into `docs/artifacts/`.
- [`hal_probe/`](hal_probe/README.md) — build **any** driver against **any**
  injected PAC, one pairing at a time, and explain the errors.
- `fixtures/` — the four cross-PAC fixtures `cross_pac.py` runs on.
- `patches/` — source patches an experiment applies before building (`elodin`).

---

## Conventions worth knowing before you add one

- **Module docstring opens with the question**, then `Usage:`. Every script
  here follows it; the folder is navigable because of it.
- **Snapshot and restore any PAC you touch**, and verify pristine afterwards.
  `get_pac.py --force` is the recovery. A dirty PAC is the single most common
  way a run in this folder fails for a reason that has nothing to do with what
  it was measuring.
- **Mode-suffix every output filename.** Whole-register and field-level gating
  plan different gate sets; an unsuffixed name let a field-gating run overwrite
  a default run's numbers, and the published table reported one as the other.
- **Report what you dropped.** Every fate, with a reason. A script that reports
  only successes cannot be distinguished from one that silently lost half its
  input.
- **Write a JSON report, not just stdout.** `cross_pac.py` and
  `corroboration.py` print their results and keep nothing, so re-reading a past
  run means re-running it — and for `corroboration.py` that means paying for
  the judge again. Everything newer writes to `out/`.
