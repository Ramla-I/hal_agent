# verified_datasheet/

Human-verified **ground-truth slices** of hardware datasheets, plus the tooling to build them.

A *verified datasheet* is a CSV in which a human has recorded the **authoritative, datasheet-true value** of each register-layout invariant for a device (one verified file per device). These slices are the trustworthy reference the rest of the pipeline is measured and tuned against.

## Why these exist

Upstream merges are the *external* ground truth for the bugs we actually file. Verified datasheets are the *internal* ground truth that lets us get there safely. They serve two jobs:

1. **Fitness signal for per-vendor auto-adaptation.** When the pipeline configures itself to a new vendor (retrieval rules, chunking, extraction), it is scored against this slice. A contaminated slice would make adaptation optimize toward the wrong target, so creation must be **blind** (see below).
2. **Measuring Validator precision.** The Validator is a precision filter upstream of human PR review. We benchmark its precision per vendor on these slices and require it to clear a bar before filing PRs to that vendor's crate.

> Per-vendor amortization is the cost model: ~2 verified datasheets per vendor (from *different device families*) let us measure both validator precision and device-to-device transfer, while many additional devices are processed without verification and validated by merges.

## Devices (the evaluation set)

Three vendors × two devices each. The two devices per vendor are deliberately from **different families** — same-family parts are near-identical, so transfer would be trivial and the "calibrate once per vendor, reuse across its devices" claim would prove nothing. **STM** is the *development* vendor (hand-tuned baseline + the bulk of merged bugs); **NXP** and **TI** are *held out* to test that per-vendor auto-adaptation generalizes to vendors we did not co-develop.

| Vendor | Device 1 | Device 2 | Why this pair |
|---|---|---|---|
| **STM** *(dev)* | **rm0041** — STM32**F1**, Cortex-M3 (`stm32f100`) · *slice exists, 14 merges* | **rm0090** — STM32**F4**, Cortex-M4 (`stm32f405`) · *assets in repo, 18 merges* | F1↔F4 is a real generational jump; rm0090 has the most merge evidence, so the amortization demo (calibrate on rm0041 → freeze → apply to rm0090) is reconstructible. |
| **NXP** *(held-out)* | **ke04** — Kinetis E, Cortex-M0+ (`mke04z4`) · *slice exists* | **s32k1xx** — S32K automotive (`s32k116`) · *PDF + 8 SVDs in repo* | Kinetis-E vs S32K-automotive are documented very differently within one vendor — a genuine within-vendor transfer test, and assets are already present. |
| **TI** *(held-out)* | **msp430g2** — MSP430 G2 Value Line, 16-bit (`msp430g2553`) · *in repo* | **MSP430FR5969** — MSP430 FR (FRAM), 16-bit · *assets to obtain* | The diversity pick: 16-bit, non-ARM, TI documentation style — the strongest test that adaptation generalizes beyond ARM/CMSIS conventions. msp430g2 is small → a cheap first non-ARM slice. |

**Keep effort bounded.** rm0041 and ke04 are full anchors; for the other four, annotate a **representative slice** (~8–12 peripherals) — enough to measure transfer and validator precision (rm0090 alone is 442 registers; don't do all of it). Where a device ships several SVD variants, pick the **smallest** (e.g. `s32k116`, not the M4F parts).

**Suggested order** — covers all three vendors fast, then the within-vendor transfer second-devices:

> rm0041 (finish) → ke04 → msp430g2 → rm0090 slice → s32k116 slice → MSP430FR slice *(most deferrable; needs new assets)*

**Merge caveat.** Merges-as-ground-truth flow freely for **STM** (stm32-rs, large active community); **NXP and TI have thinner Rust communities**, so their role is the *generalization* claim — measured against the verified slice — with any merges a bonus. STM carries scale + merges; NXP and TI prove the adaptation generalizes to increasingly different vendors.

## Scope: layout only

These slices cover **register-layout invariants** only. Six keys:

| Level | Keys |
|---|---|
| register | `address_offset`, `reset_value`, `size` |
| field | `bit_offset`, `bit_width`, `access` |

**Out of scope (by design):**
- **Enumerated values** — omitted for now; add a separate optional pass if a quantitative enum-bug claim is ever needed.
- **Dependency / ordering invariants** — unstructured and scattered in datasheets, so they are *not* verified here. Their quality is checked by the compiler + typestate compile-pass/fail examples + PR review, not by a verified-datasheet diff. If a quantitative dependency claim is later wanted, create separate dependency-verified files.

## File layout

```
verified_datasheet/
├── README.md
├── annotate.py                          # the tool — build a verified datasheet (use this)
├── create_digital_datasheet.py          # legacy: seed a comparison CSV from SVD + agent output
├── correlate_digital_with_pdf_datasheet.py   # legacy/DEPRECATED — anchored, do not use (see below)
├── retrieve_checked_values_from_csv.py  # utility: extract only the checked (correct_value) rows
├── stm/
│   └── rm0041_stm32f100.csv             # one verified datasheet per device, directly under the vendor
└── nxp/
    └── ke04_mke04z4.csv
```
Convention: one verified CSV per device, directly under the vendor folder, at `{manufacturer}/{device}_{svd}.csv` — a single self-contained file, no sidecars.

## CSV schema

Tall — one row per invariant cell — keyed by the **SVD's** `(peripheral, register, field, key)` so the downstream diff joins without any datasheet↔SVD name mapping.

| column | meaning |
|---|---|
| `peripheral`, `register`, `field_name`, `key` | the SVD-keyed cell identity (`field_name` empty for register-level keys) |
| `alt_name` | the field/register's name **as printed in the datasheet**, when it differs from the SVD's — e.g. SVD `bkp.dr1.d1` is just `D` in the datasheet (the SVD suffixed it to disambiguate per-register). Recorded for provenance only; the row stays keyed by the SVD name so the diff join is unaffected. Empty when the names match. |
| `correct_value` | **the human-verified datasheet value** (canonical form); the column the diff pipeline reads |
| `svd_value` | the value the SVD asserts (shown as the confirm-or-override default) |
| `agent_value` | the generator's value — stored only to *target* blind annotation at disagreements; **never shown during annotation** |
| `status` | `verified` · `datasheet-ambiguous` · `not-specified` · `skipped` · *(empty = pending)* |
| `page` | best-effort hint — the first page where the register name appears (you may navigate elsewhere in Preview) |
| `set_method` | how the value was set: `human-verified` · `overridden` · `blind` · `imported` |
| `derived_from` | empty for normal rows; on a **marker row** (one per `derivedFrom` peripheral) it names the prototype, e.g. `gpiob → gpioa` |

Dedup is recorded **in the CSV**: each `derivedFrom` peripheral gets one compact **marker row** (only `peripheral` + `derived_from` set, `status=derived`) instead of repeating the prototype's rows. The diff expands these against the prototype's verified values.

### What `set_method` means

`set_method` is the **provenance** of each value — how it entered the CSV — so you can judge how much to trust a row (which rows to weight for the validator-precision measurement, and which to re-verify):

- **`human-verified`** — you confirmed the SVD value (pressed Enter), or marked the cell `datasheet-ambiguous` / `not-specified`. You asserted the SVD value matches the datasheet.
- **`overridden`** — you typed a value *different* from the SVD's. A deliberate correction — frequently the SVD-bug cases.
- **`blind`** — you entered the value with the SVD value hidden (`--blind*` modes), transcribing it from the datasheet page. Fully un-anchored, so the most trustworthy: it reflects the datasheet independently of the SVD.
- **`imported`** — carried over from a pre-existing/legacy CSV (had a `correct_value` but no provenance); set automatically on load. Unknown provenance — likely from the old anchored tool, so a prime candidate for blind re-verification.

Trust / anchoring order: **`blind` ≥ `overridden` ≥ `human-verified` > `imported`**. The risk to watch is *anchoring*: a `human-verified` or `imported` value on an SVD-vs-datasheet **disagreement** could be a wrong SVD value confirmed by reflex — exactly where a real bug hides. Audit a sample with the blind modes, and lean on `blind` / `overridden` / `human-verified` (not `imported`) for the precision numbers.

(Marker rows carry `status=derived` and an empty `set_method` — they aren't annotated.)

## Core principles

- **Blind / un-anchored.** To avoid circular ground truth, the annotator is never shown the **generator** value. The **SVD** value is shown as a default for speed (confirming is far faster than transcribing thousands of rows), but anchoring on a *wrong* SVD value would hide exactly the bugs we hunt — so use the blind modes (below) to keep the fast path honest.
- **SVD-keyed worklist.** The SVD's cells *are* the worklist; you fill the datasheet's value for each. This bounds the task and makes the diff join trivial.
- **Dedup.** Peripherals declared with `derivedFrom` in the SVD (e.g. `GPIOB..G ← GPIOA`, `TIM3/4/5 ← TIM2`) are annotated once via the prototype; the inheritance is recorded as a `derived_from` **marker row** in the CSV for the diff to expand.

---

## `annotate.py`

A CLI for building a layout verified datasheet from an SVD worklist, reading values from the datasheet PDF.

### Quick start

```bash
cd ~/Projects/hal_agent && source .venv/bin/activate

python3 verified_datasheet/annotate.py \
  --svd devices/stm/rm0041/svd/stm32f100.svd \
  --pdf devices/stm/rm0041/rm0041.pdf \
  --out verified_datasheet/stm/rm0041_stm32f100.csv
```

The tool builds the SVD-keyed worklist (deduping `derivedFrom` peripherals), opens the full datasheet in **Preview** and drives its **Find** to jump to each register's name, and walks you cell by cell. Progress is saved after **every** entry and the run is fully **resumable** — rerun the same command to continue where you left off. A legacy CSV is upgraded to this format automatically the first time you resume it.

### Interactive commands (per cell)

| input | action |
|---|---|
| `Enter` | confirm the shown SVD value |
| `<value>` | type a different value (override) |
| `f` | re-run Preview's Find for this register (⌘G in Preview steps to the next match) |
| `a` | mark `datasheet-ambiguous` |
| `n` | mark `not-specified` in the datasheet |
| `pn` | mark the **whole peripheral** `not-specified` — all of its still-pending cells at once (after a `[y/N]` confirm). For a peripheral the datasheet mentions but doesn't detail (e.g. `NVIC`), so you don't have to step through every field |
| `r` | record the datasheet's name for this field/register (alias) when it differs from the SVD's — applied to all cells of the field/register, into the `alt_name` column; the SVD key is kept, so you still enter the value afterward |
| `s` | skip (leave pending for later) |
| `q` | save and quit |

Values are canonicalized on override (hex → `0x…`, access → CMSIS vocab; shorthands `rw`/`ro`/`wo` accepted). Confirming keeps the SVD's literal value.

### Blind modes (keep the fast path honest)

The fast path (confirm the SVD value) is efficient but anchored. Annotate an unanchored subset to measure and bound that bias:

```bash
# blind on a deterministic 15% sample
python3 verified_datasheet/annotate.py ... --blind-sample 0.15

# blind specifically on the bug-candidate cells (SVD disagrees with the generator)
python3 verified_datasheet/annotate.py ... \
  --agent-output agent_output/stm/rm0041/<run> --blind-disagreements

# blind everything
python3 verified_datasheet/annotate.py ... --blind
```
In blind mode the SVD value is hidden; you read the page and type the value, recorded with `set_method = blind`.

### Adding a new vendor / device

A new device needs only **two inputs** — its SVD and its datasheet PDF:

```bash
python3 verified_datasheet/annotate.py \
  --svd devices/<mfg>/<dev>/svd/<dev>.svd \
  --pdf devices/<mfg>/<dev>/<dev>.pdf \
  --out verified_datasheet/<mfg>/<dev>_<svd>.csv
```
The worklist parser is vendor-general (verified on STM and NXP). Candidate pages are found by **searching the PDF directly** — no precomputed index to build per device. Without `--pdf` you navigate the PDF manually.

### Dry run / sanity check (no annotation)

```bash
python3 verified_datasheet/annotate.py --svd <svd> --pdf <pdf> --stats
```
Prints the worklist size, peripherals annotated vs deduped, cells-per-key, the `derivedFrom` map, the search-term hit rate, and sample cells.

### All flags

| flag | purpose |
|---|---|
| `--svd` *(required)* | SVD file defining the worklist |
| `--pdf` | datasheet PDF — searched directly for candidate pages and rendered to open them |
| `--out` | output CSV (required for annotation) |
| `--agent-output` | generator JSON dir — only to target `--blind-disagreements`; never displayed |
| `--blind`, `--blind-sample <0..1>`, `--blind-disagreements` | hide the SVD value (see above) |
| `--no-open` | do not auto-open pages |
| `--stats` | print worklist stats and exit |

### Known v1 limitations

- SVD `dim`/`dimIncrement` register **arrays** are not yet expanded (not needed for STM RM0041 / NXP KE04; will add when a vendor requires it).
- Navigation is **macOS Preview only**. The tool opens the full datasheet and jumps to the register by *name* (Preview can't be told a page from the CLI). It **always copies the register name to the clipboard**, so you can press **⌘F then ⌘V ↵** in Preview — no typing — and, when your terminal has **Accessibility** permission, it *also* drives Preview's Find automatically (grant it in System Settings ▸ Privacy & Security ▸ Accessibility, then restart the terminal; the tool tells you which mode is active). The first match may be an overview mention, so use **⌘G** to step to the authoritative definition. Without `--pdf` (or with `--no-open`) nothing opens. PyMuPDF (in the `.venv`) picks the right search term and the `page` hint.

---

## Other scripts (legacy / utilities)

- **`create_digital_datasheet.py`** — builds a comparison CSV `(peripheral, register, field_name, key, correct_value, svd_value, agent_value)` from an SVD plus a generator-output directory. Historically used to *seed* a slice with `svd_value`/`agent_value` filled in. `annotate.py` builds its own worklist directly from the SVD, so this is optional.
- **`retrieve_checked_values_from_csv.py`** — extracts only the rows that have a `correct_value`, deduped by register- or field-level key. Useful for pulling the verified subset out of a larger comparison CSV.
- **`correlate_digital_with_pdf_datasheet.py`** — **deprecated, do not use for new verified datasheets.** It prepopulates the annotator with *both* the SVD and the generator values and lets you pick one, which **anchors** the ground truth on the system under test (the circular-ground-truth problem). Use `annotate.py` (generator value hidden, blind modes available) instead.
