# verified_datasheet/constraints/ — the verified-CONSTRAINTS datasheet

Human-verified ground truth for **access/ordering constraints** extracted from datasheets — the "separate dependency-verified files" that the layout-only scope of `verified_datasheet/README.md` explicitly reserves. Its job (plan §7.2): measure the Constraint Validator's precision (α) on real data, **retrospectively and never blocking** — the validator ships calibrated by the corruption harness alone; every annotated row here tightens the α confidence interval afterwards.

```
constraints/
├── README.md      # this file
└── stm.csv        # one row per unique extracted constraint per reference manual (30 STM RMs)
```

## Building / refreshing `stm.csv`

```bash
python3 verified_datasheet/build_constraints_datasheet.py \
    /home/ramla/hal_agent-phase-1d/agent_output/stm
```

The builder walks the extraction corpus (`<rm>/<run>/{peripheral}_{register}` register JSONs, v1 `access_constraints` schema) and is **re-runnable/idempotent**: rebuilding preserves existing annotations (matched by `id`), refreshes machine columns (`dup_count`, `lint_flags`, provenance), adds rows for new constraints, and keeps rows whose constraint vanished from the corpus. A non-empty `status`/`note` is **never** clobbered. Rebuilding against an unchanged corpus is byte-identical.

**Dedup.** One row per unique constraint per reference manual. Dedup key:

> `(reference_manual, target_register, target_operation, sorted preconditions, sorted postconditions, datasheet_text)`

`dup_count` records how many raw occurrences collapsed into the row (repeats across runs, peripheral instances USART1..8, and per-bit fan-out of register-level notes); `source_file` is the first-seen example. `id` is the first 12 hex chars of sha256 over the dedup key — stable across rebuilds, so annotations survive and the validator's verdicts can later be joined by `id`.

Note the count is per-RM by design: the same boilerplate sentence appearing in several reference manuals yields one row per RM (each RM is annotated independently), which is why `stm.csv` has ~4.2k rows rather than the ~2.6k a corpus-global dedup would give.

## Columns

| column | meaning |
|---|---|
| `id` | stable content hash (12 hex chars of sha256 over the dedup key) |
| `reference_manual` | rm0008 … rm0505 |
| `run`, `source_file` | provenance of the first-seen occurrence (`source_file` = `<rm>/<run>/<file>`) |
| `peripheral`, `register` | parsed from the first-seen filename (`{peripheral}_{register}`; may contain a literal `%s` — a known derivedFrom plumbing bug, kept and flagged) |
| `target_operation` | generator output, verbatim (`write`/`read`/`modify`, plus drift) |
| `target_fields` | compact JSON list of field names (empty = whole register) |
| `preconditions`, `postconditions` | compact JSON lists of `{register_name, field_name, required_state}` |
| `severity`, `consequence`, `datasheet_text` | generator output, verbatim — `datasheet_text` is the quote under judgment |
| `dup_count` | raw occurrences collapsed into this row (within the RM) |
| `lint_flags` | machine-derived, semicolon-separated, **informational only** (below) |
| `status`, `note` | the human annotation columns (empty = unannotated) |

## `status` vocabulary

| status | meaning |
|---|---|
| `confirmed` | the quote is a genuine access/ordering requirement AND the encoding represents it faithfully (TP) |
| `encoding_error` | real constraint, but the encoding is wrong or incomplete (target, operation, polarity, fields, dropped condition) |
| `not_constraint` | the quoted text is not an access/ordering requirement — w1c flag semantics, access-width, privilege/secure, validity notes (FP) |
| `quote_missing` | the quote cannot be found in the reference manual |
| `unsure` | can't decide |
| *(empty)* | unannotated |

## `lint_flags` (mechanical, NOT judgments)

Derived by the builder to aid *stratified* annotation — e.g. sampling `w1c_suspect` rows first. They are text/vocabulary heuristics, never verdicts:

| flag | trigger |
|---|---|
| `off_vocab_op` | `target_operation` not in write/read/modify |
| `off_vocab_state` | a `required_state` that is not `cleared`/`set`/`equals:<single numeric>` |
| `empty_conditions` | no preconditions and no postconditions |
| `placeholder_source` | literal `%s` in the source filename or any register/field name |
| `many_postconditions` | more than 3 postconditions (the w1c fan-out pathology) |
| `w1c_suspect` | `datasheet_text` matches write-1-to-clear / cleared-by-writing phrasings |
| `read_clear_suspect` | read-operation constraint whose text says the flag is cleared by/after a read |

## Blindness rule (plan §7.2)

The row shows *generator output + its quote* — that pair **is** the object under judgment — but **no LLM-validator verdict of any kind may ever appear in or near this file**. The builder reads only the register JSONs (run-dir subfolders such as `validator/` are skipped wholesale), and the schema has no column a verdict could occupy. The human label must never be anchored by the machine's.

## Annotating

```bash
python3 verified_datasheet/annotate_constraints.py               # annotate (round-robin)
python3 verified_datasheet/annotate_constraints.py --stats       # progress per RM + ETA
python3 verified_datasheet/annotate_constraints.py --rm rm0008   # one RM only
python3 verified_datasheet/annotate_constraints.py --flagged-only --limit 25
```

The judgment is a **closed local task** — quote vs encoding — so no PDF is needed (~20 s/row). Keys: `c` confirmed · `e` encoding_error · `n` not_constraint · `m` quote_missing · `u` unsure · `s` skip · `q` save+quit · `?` help; `e/n/m/u` prompt for an optional note. The CSV is saved **atomically after every answer** (temp file + `os.replace`, as in `annotate.py`), so a crash never loses work, and any session is resumable.

Rows are served in **strict round-robin across reference manuals** (one row per RM per cycle, RMs in sorted order), so any partial effort covers all 30 RMs evenly — the stratification the retrospective α measurement relies on.

## Tests

```bash
.venv/bin/python -m pytest verified_datasheet/tests/ -q
```
