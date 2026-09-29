# Whole-corpus statistics & figures

Standalone analysis scripts over the STM corpus (the `evaluation/stm/*/1/` reviews,
`bug_reports/`, and the verified datasheets). They read committed artifacts and
produce printed tables + PDF figures; they do **not** run the pipeline or change any
data. Run them inside the venv (they need `pandas` etc.):

```bash
source .venv/bin/activate
```

## Scripts

### `scripts/stm_structure_statistics.py`
Whole-corpus structure-review statistics per attribute category (address_offset,
reset_value, size, bit_offset, bit_width, access), and the **structure cascade
figure** — a linear walk from every generated fact down to the reviewer's verdict.

```bash
python scripts/stm_structure_statistics.py --marked                       # printed breakdown
python scripts/stm_structure_statistics.py --marked --cascade-figure      # -> docs/figures/structure_cascade.pdf
python scripts/stm_structure_statistics.py --marked --exclude access --with-prefilter --cascade-figure
```
- `--marked` — add the reviewer TP/FP columns (out of rows *labelled*, not rows disagreed).
- `--exclude CATEGORY` — drop a category everywhere (repeatable), e.g. `--exclude access`.
- `--with-prefilter` — project the issue-#23 width-variant / placeholder screen into the deterministic (mechanical-FP) stage.
- `--cascade-figure [PATH]` / `--agreement-figure [PATH]` — write the figure (default under `docs/figures/`).
- `--by-rm`, `--csv PATH`, `--root DIR`.

The cascade's last band splits the reviewed pile by the reviewer's own label:
**`trivial`** (FP — survived every automated filter but judged not a real bug) vs
**`real`** (TP — a genuine SVD bug).

### `scripts/stm_coverage_statistics.py`
SVD-vs-generator coverage per attribute category and in aggregate: how many facts the
SVD has that the generator doesn't and vice-versa. Subfields are reconciled by
**bit position** (a collapsed `MRx[17:0]` credits the SVD's `mr0..mr17`), so the
numbers aren't deflated by the array-granularity artifact.

```bash
python scripts/stm_coverage_statistics.py            # aggregate + per-category
python scripts/stm_coverage_statistics.py --by-rm --csv coverage.csv
```
Flags: `--exclude`, `--by-rm`, `--csv`, `--root`.

### `scripts/stm_constraint_generation_statistics.py`
What the generator extracted and what survived to a judged verdict — the constraint
pipeline up to the review files (not injection). Prints the funnel and can draw it.

```bash
python scripts/stm_constraint_generation_statistics.py
python scripts/stm_constraint_generation_statistics.py --figure docs/figures/constraint_generation.pdf
```
Flags: `--by-rm`, `--csv`, `--figure [PATH]`, `--width-in`, `--height-in`.

### `scripts/plot_peripheral_bugs.py`
Register-structure bugs per peripheral family, as a bubble scatter or dual-axis bars
(bug density + RM count).

```bash
python scripts/plot_peripheral_bugs.py out.pdf                # bubble scatter
python scripts/plot_peripheral_bugs.py out.pdf --style bars   # dual-axis bars
```

### `scripts/analyze_review_fps.py`
Statistics on the hand-labelled structure reviews, focused on the validator's false
positives and whether they fit a mechanical pattern that could be screened *before*
the validator runs. Includes a TP/FP-across-categories breakdown.

```bash
python scripts/analyze_review_fps.py
python scripts/analyze_review_fps.py --glob 'evaluation/stm/*/1/*_structure_review.csv' --dump
```
Flags: `--glob`, `--dump`, `--dump-tp`.

### `scripts/pdfwriter.py`
A minimal dependency-free PDF writer used by the figures above (not a CLI).

## Figures
Generated PDFs land under `docs/figures/` (gitignored). Regenerate them from the
commands above; the scripts are the source of truth for every number.
