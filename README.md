# hal_agent

hal_agent is an AI-powered tool for extracting hardware register information from device datasheets (embedded systems such as STM32 and NXP Kinetis microcontrollers). It uses OpenAI's API and agents SDK to parse datasheets, identify register details, and map them to driver code for hardware abstraction layer (HAL) development.

## Pipeline Overview

The project implements a multi-stage pipeline:

1. **Generator (S1)** — Extracts register info from datasheets using LLMs (supports single-register and batched modes)
2. **Coverage Improver (S2)** — Iteratively adjusts context retrieval parameters based on SVD comparison
3. **Validator (S4)** — Classifies extracted invariants against the datasheet using an LLM agent
4. **Analyzer (S5)** — Filters irrelevant differences between agent output and SVD files

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

## Quick Start

```bash
# Preprocess a device datasheet (chunk + enrich + ingest)
python3 context_retrieval/preprocessing/pipeline.py devices/<mfg>/<dev>/<dev>.pdf <dev> --format markdown --embed-metadata --backend local

# Run the full analysis pipeline
python3 core/s0_run_full_analysis.py

# Or run individual stages
python3 core/s1a_generator.py          # Generator
python3 core/s2_coverage_improver.py   # Coverage improver
python3 core/s4_validator.py           # Validator
python3 core/s5_analyzer.py            # Analyzer
```

## Adding a New Device

1. Add datasheet PDF and SVD files to `devices/{manufacturer}/{device_name}/`
2. Create vector store: `python3 context_retrieval/preprocessing/pipeline.py devices/<mfg>/<dev>/<dev>.pdf <dev> --format markdown --embed-metadata`
3. Add device entry to `config.user_contexts` with manufacturer, run number, and IDs
4. Update `config.DEVICE_NAME` to target the new device
5. Run `python3 core/s0_run_full_analysis.py`

## Documentation

See [CLAUDE.md](CLAUDE.md) for detailed architecture, configuration, data models, and directory structure documentation.
