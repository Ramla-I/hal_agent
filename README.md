# hal_agent

hal_agent is an AI-powered tool for extracting hardware register information from device datasheets (embedded systems such as STM32 and NXP Kinetis microcontrollers). It uses OpenAI's API and agents SDK to parse datasheets, identify register details, and map them to driver code for hardware abstraction layer (HAL) development.

## Pipeline Overview

The project implements a multi-stage pipeline, all orchestrated per-device by
`core/s0_run_full_analysis.py`:

1. **Preprocess** — chunk the PDF + build the local vector store.
2. **Generator** — extract register info per peripheral/register (batched; expands `<dim>` arrays; retries empty-field registers).
3. **Constraints** — extract + validate register-access constraints → `{rm}_constraints_review.jsonl`.
4. **Bug-finding** — diff against the ground-truth SVDs; an in-memory **analyzer** drops obvious non-bugs → `{rm}_structure_review.csv`.
5. **Validator** — one core (`core/validator_core.py`) run after the diff to fill the advisory `validator_verdict` on the bug candidates (or before the diff as a full-extraction QA pass).

## Getting the Code

This repo uses git submodules (including the **private** `verified_datasheet/`
repo of verified ground-truth CSVs, which the pipeline and tests depend on).
Clone with submodules, or initialize them after cloning:

```bash
# Fresh clone with all submodules
git clone --recurse-submodules https://github.com/Ramla-I/hal_agent.git

# Already cloned? Initialize/update submodules
git submodule update --init --recursive
```

> Fetching the `verified_datasheet` submodule requires access to the private
> `Ramla-I/verified_datasheets` repo. Without it, that folder stays empty and
> pipeline/optimization steps that read the verified CSVs will fail.

## Prerequisites

```bash
# Python virtual environment
source .venv/bin/activate

# Required API keys
export OPENAI_API_KEY="your-key-here"
export GROQ_API_KEY="your-key-here"  # if using Groq models
```

## Run a new STM datasheet (start to finish)

One host command takes a **brand-new** reference manual all the way to the two review
files. `{rm}` is the reference-manual id (e.g. `rm0444`).

- **Add the device assets.** Put the datasheet and its SVD(s) here (the id is the RM number):
  - `devices/stm/{rm}/{rm}.pdf`
  - `devices/stm/{rm}/svd/*.svd`  (one or more ground-truth SVD files)
- **Set the API keys** the models use:
  - `export GROQ_API_KEY=...`  (generator/validator run on `gpt-oss-120b` via Groq)
  - `export OPENAI_API_KEY=...`  (analyzer + fallbacks)
- **Run the one command — on the HOST, not inside Docker** (it registers the device in
  the host-owned `config_devices.json`, which the container can't write, then launches
  the pipeline in Docker):
  ```bash
  python scripts/run_stm_batch.py --devices {rm} --auto-register
  ```
- **What it does, in order** (all automatic, per device):
  - registers `{rm}` in `config_devices.json` (host-side)
  - **preprocess** — converts the PDF to chunks + builds the local vector store (`chunked_datasheets/stm/{rm}/…`, `databases/{rm}_md_chunks`)
  - **generate** — extracts register info per peripheral/register → `agent_output/stm/{rm}/1/`
  - **constraints** — extracts + validates access constraints → `evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl`
  - **bug-finding + validate** — diffs against the SVDs, then fills the advisory verdict column → `evaluation/stm/{rm}/1/{rm}_structure_review.csv`
- **Read the path manifest.** The first lines of the run print every input read and every
  file written — use it to confirm each artifact landed.
- **The two deliverables** (both under `evaluation/stm/{rm}/1/`):
  - `{rm}_structure_review.csv` — candidate register/field bugs, with `validator_verdict`
  - `{rm}_constraints_review.jsonl` — extracted access constraints, with the validator verdict
- **Review them** with the interactive labelers:
  ```bash
  python scripts/label_structure_review.py --rm {rm}        # add --validator-tp / --field-keys to filter
  python scripts/label_constraints_review.py --rm {rm}      # add --confirmed to filter
  ```
- **Re-running** is safe: a completed RM is skipped (delete its resume marker
  `logs/stm_batch/{rm}_run1.done` or pass `--force` to redo). Multiple RMs at once:
  `--devices rm0444 rm0091 --parallel 2`.
- **Progress/logs:** per-RM log at `logs/stm_batch/{rm}.log`; batch status at `logs/stm_batch/status.json`.

> The step-by-step manual/debugging path (and the roadblocks it works around) is in
> [docs/PREPROCESSING.md](docs/PREPROCESSING.md).

## Running individual stages

`core/s0_run_full_analysis.py` is the per-device engine the driver above launches; run it
directly (inside Docker) to control individual steps — see its `--help` and
[CLAUDE.md](CLAUDE.md).

## Counting bugs (register structure)

We count one bug as a unique *incorrect structural attribute* of a register or field
within a single reference manual (RM) — the tuple `(RM, peripheral, register, field,
key)`, where `key` is one of `address_offset`, `reset_value`, `size`, `bit_offset`,
`bit_width`, or `access`. The count is keyed on **identity, not value**: it ignores
both the SVD's wrong value and the datasheet's correct value. So a bug that appears
across many SVD files collapses to one — even when the wrong value differs between
silicon families (e.g. a field width mis-specified as 5/6/8 across chips) or the
correct value is genuinely chip-specific (e.g. a per-device ID-code reset value). Two
facts are distinct bugs only if they differ in location or attribute.

This is deliberately anti-inflationary. The per-SVD, per-value rows kept in
`bug_reports/bug_tracker.csv` for patching and de-duplication are **not** counted as
separate bugs, and facts already fixed upstream before we submitted them (no PR link +
`Patched`) are excluded. The reported number is the count of distinct structural errors
a maintainer would recognize as separate issues — not the number of individual edits,
affected device files, or value variants.

The count unions `bug_reports/bug_tracker.csv` with every reviewed
`bug_reports/checked/{rm}_bug_report.csv` (same columns); a bug appearing in both is
counted once. Compute it with:

```bash
python scripts/count_bugs.py                 # tracker + checked, upstream-patched excluded
python scripts/count_bugs.py --no-checked    # tracker only
python scripts/count_bugs.py --by pr         # broken down by PR (--by rm|status too)
```

## Documentation

See [CLAUDE.md](CLAUDE.md) for detailed architecture, configuration, data models, and directory structure documentation.
