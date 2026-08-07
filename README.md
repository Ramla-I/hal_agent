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

## Documentation

See [CLAUDE.md](CLAUDE.md) for detailed architecture, configuration, data models, and directory structure documentation.
