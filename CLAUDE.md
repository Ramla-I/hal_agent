# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

hal_agent is an AI-powered tool for extracting hardware register information from device datasheets (embedded systems such as STM32 and NXP Kinetis microcontrollers). It uses OpenAI's API and agents SDK to parse datasheets, identify register details, and map them to driver code for hardware abstraction layer (HAL) development.

The project implements a multi-stage pipeline that:
1. Generates register information from datasheets using LLMs
2. Improves coverage iteratively based on SVD file comparisons
3. Validates extracted information using an LLM agent that classifies invariants against the datasheet
4. Analyzes differences between agent output and SVD files to remove irrelevant differences (e.g., legitimate SVD bugs, acceptable variations)

## Repository Structure

```
hal_agent/
├── core/                       # Main pipeline scripts (s0-s5)
├── optimization/               # Optimization experiments & analysis scripts
│   ├── common/                # Shared sweep harness + comparison helpers
│   ├── retrieval/             # Manual retrieval sweep + analysis + reports
│   │   ├── evaluate_retrieval.py       # Parameter sweep experiments
│   │   ├── plot_*.py          # Visualization scripts
│   │   └── reports/*.md       # Analysis reports
│   ├── generator/             # Generator sweep (batching, prompting) + plots
│   ├── test_outputs/          # Test results (gitignored, see STRUCTURE.md)
│   ├── s*a_*.py               # Optimization experiment scripts
│   ├── compare_*.py           # Analysis scripts
│   └── analyze_*.py           # Analysis scripts
├── docs/                       # Documentation files
├── agent_tools/                # Utilities for agents (SVD parsing, PDF ops, etc.)
├── context_retrieval/          # Context retrieval system
│   ├── preprocessing/         # Chunking, enrichment, and vector store ingestion
│   │   ├── pipeline.py        # Unified pipeline (p1+p2+p3 + backend upload)
│   │   ├── ingest_local_vector_db.py  # Local ChromaDB ingestion
│   │   └── p1_*, p2_*, p3_*   # Individual preprocessing stages
│   └── vector_db/             # Local ChromaDB package
├── prompts/                    # LLM prompts for each component
├── utils/                      # General utilities
├── devices/                    # Device datasheets and SVD files
├── scripts/                    # Helper scripts
├── verified_datasheet/         # Verified ground truth data (register structure +
│                               #   constraints/stm.csv for access constraints)
├── openevolve_retrieval/       # OpenEvolve evolutionary retrieval optimization
│   ├── initial_program.py     # Evolvable retrieval program
│   ├── evaluator*.py          # Fitness functions (per device)
│   ├── config*.yaml           # OpenEvolve configs (per device)
│   └── output_*/              # Evolution outputs (best programs, checkpoints, logs)
├── core/quote_anchor.py        # ENFORCEMENT ARM — the constraint validator:
│   core/constraint_validator.py #   deterministic quote anchoring + target-location
│                               #   gate + closed-book gpt-oss judge (plan §7). The
│                               #   tuning harness + verified-constraints datasheet
│                               #   ship in a follow-up (branch constraint_validator_tuning)
└── applications/pac_codegen/   # ENFORCEMENT ARM — turn access constraints into
                                #   witness-gated PAC crates (rust_codegen.py emitter,
                                #   inject_from_run.py driver, compile tests,
                                #   convert_v1_to_v2.py = the one v1→v2 migration tool)
```

## The Enforcement Arm (grammar v2 → witness-gated PAC crates)

Beyond extracting register facts, the project's second arm turns *register
access constraints* (when a register may be read/written/modified) into
compile-time guarantees in Rust PAC crates. The authoritative design and
status doc is **`docs/register_constraints_plan.md`** (enforcement mechanics in
§3 and Appendix A; roadmap + divergence log); the constraint grammar itself is
specified in **`docs/REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`**. Key pieces:

- **Grammar v2** (`defs.py`, `prompts/register_info_stm.py`): a discriminated
  union of constraint kinds (`state_gate`, `sequence`, `write_once`,
  `clock_gate`, `delay`, `read_effect`, `value_relation`, `other`); the
  generator emits it natively. Enforceability is *computed*
  (`derive_enforceability`): `action_witnessed` / `state_witnessed` (both
  compile-time witness-gated), `dynamic_check`, or `doc_only`. The pipeline
  (grammar, collection, codegen) is **grammar-v2 only**; old grammar-v1
  generator output is converted first with
  `applications/pac_codegen/convert_v1_to_v2.py` — the single tool that still
  parses the retired v1 access-constraint grammar.
- **Constraint Validator** (`core/quote_anchor.py` + `core/constraint_validator.py`):
  deterministic quote anchoring + target-location gate, then a closed-book
  gpt-oss judge, wired into `core/s0` (`--constraint-validation`) and
  `inject_from_run.py` (`--chunks`). Its corruption/calibration tuning harness
  and the verified-constraints datasheet (`verified_datasheet/constraints/`) ship
  in a follow-up PR (branch `constraint_validator_tuning`), keeping this PR
  focused on the enforcement mechanism.
- **Codegen** (`applications/pac_codegen/rust_codegen.py`): whole-register
  gating via marker traits in `generic.rs`; **field-level gating is opt-in**
  (`--field-level-gating`, default off). `inject_from_run.py` is the
  end-to-end driver (generator run → collect → static validation → inject).
- **Full pipeline in s0**: `core/s0_run_full_analysis.py --constraint-validation`
  runs generator (v2) → static validation → constraint validator.

## Key Commands

### Setup
```bash
# Set environment variables (required)
export OPENAI_API_KEY="your-key-here"
export GROQ_API_KEY="your-key-here"  # if using Groq models

# Activate virtual environment
source .venv/bin/activate
```

> **IMPORTANT FOR CLAUDE**: Always activate the virtual environment before running Python commands:
> ```bash
> source .venv/bin/activate && python <script>
> ```
> The system Python does not have required dependencies (pydantic, openai, tiktoken, etc.).

### Running the Pipeline

```bash
# Run the full analysis pipeline (generator + coverage improver + evaluation)
python3 core/s0_run_full_analysis.py

# Run individual stages
python3 core/s1a_generator.py                    # Generate register info from datasheet
python3 core/s2_coverage_improver.py             # Improve coverage based on SVD comparison
python3 core/s4_validator.py                     # Validate extracted information
python3 core/s5_analyzer.py                      # Analyze differences
```

### Optimization Scripts

```bash
# Run optimization experiments for specific components
python3 optimization/s2a_coverage_improver_optimization.py   # Optimize coverage improver
python3 optimization/s4a_validator_optimization.py           # Optimize validator (sequential & batched modes)

# Analysis scripts (compare test results against verified data)
python3 optimization/compare_generator_with_verified.py      # Compare generator output
python3 optimization/analyze_generator_errors.py             # Detailed generator analysis
```

### Preprocessing

```bash
# Recommended: chunk + enrich + upload to OpenAI + update devices/.../vector_stores.json
python3 context_retrieval/preprocessing/pipeline.py devices/<mfg>/<dev>/<dev>.pdf <dev> --format markdown --embed-metadata

# Upload to local ChromaDB instead of OpenAI (free, offline)
python3 context_retrieval/preprocessing/pipeline.py devices/<mfg>/<dev>/<dev>.pdf <dev> --format markdown --embed-metadata --backend local

# Chunk + enrich only (no upload)
python3 context_retrieval/preprocessing/pipeline.py devices/<mfg>/<dev>/<dev>.pdf <dev> --format markdown --backend none

# Legacy (raw PDF upload, no chunking/enrichment)
python3 context_retrieval/preprocessing/old/create_vector_store_openai.py
```

## Configuration

All pipeline configuration is centralized in `config.py`:

- `DEVICE_NAME`: Target device (e.g., "rm0041" for STM devices)
- `GENERATOR_MODEL_NAME`: Model for register generation (e.g., "gpt-4o", "gpt-oss-120b")
- `COVERAGE_IMPROVER_MODEL_NAME`: Model for coverage improvement
- `VALIDATOR_MODEL_NAME`: Model for validation
- `CONTEXT_RETRIEVAL_PARAMETERS`: Controls how context is retrieved from datasheets
  - `context_retrieval_method`: "keyword_search", "openai_file_search", "local_vector_db", or "regex"
  - `pages_after_keyword`: Pages to include after keyword match
  - `number_embeddings`: Number of embedding results for semantic search
  - `re_ranking`: Enable/disable re-ranking of search results
  - `vs_id`: Vector store ID for the device datasheet
- `user_contexts`: List of device configurations with run numbers, file IDs, and vector store IDs

## Architecture

### Pipeline Flow (s0_run_full_analysis.py)

The main pipeline orchestrates a feedback loop:

1. **Vector Store Setup**: Creates/uses OpenAI vector store for datasheet context retrieval
2. **Iterative Loop** (runs `COVERAGE_IMPROVER_ITERATIONS` times):
   - **Generator (S1)**: Extracts register info for each peripheral/register from SVD files
   - **Coverage Improver (S2)**: Analyzes coverage gaps and adjusts context retrieval parameters
3. **Post-Loop Evaluation**:
   - **Validator (S4)**: TODO - Should run once after loop exits, but currently not integrated into s0_run_full_analysis.py
   - Compare agent output with SVD files (creates diff CSVs)
   - Run analyzer to filter out irrelevant differences (keeps only actual agent errors)
   - Generate diff tables and compare with verified datasheets

### Key Components

**Generator (s1a_generator.py)**
- Iterates through peripherals and registers from SVD files
- Retrieves datasheet context using keyword/semantic search
- Generates structured JSON output with register details (address, reset value, fields, etc.)
- Uses function calling to retrieve additional context when needed
- Output: `{peripheral}_{register}` JSON files + usage/reasoning in `info/`

**Coverage Improver (s2_coverage_improver.py)**
- Compares generator output with ground truth SVD files
- Calculates peripheral/register/field coverage metrics
- Uses reasoning to suggest improved context retrieval parameters
- Output: `coverage_improver_output.json` with updated parameters + `coverage_info.json`

**Validator (s4_validator.py)**
- Builds invariants from agent output (address offsets, reset values, bit ranges, etc.)
- Uses an LLM agent with file search to classify each invariant as true/false based on the datasheet
- The agent searches the datasheet and provides a confidence-based classification
- Output: `classification.csv`, `output.txt`, `usage.csv` in validator directory

**Analyzer (s5_analyzer.py)**
- Reviews differences between agent output and SVD files from `register_diff.csv`
- Filters out irrelevant differences (e.g., legitimate bugs in SVD, acceptable variations)
- Identifies which differences represent actual agent errors vs. correct deviations
- Output: JSON with list of valid bug row IDs, plus filtered `register_diff_analyzer.csv`

### Context Retrieval System

Located in `context_retrieval/`:
- **keyword_search.py**: Searches for register/peripheral names in markdown sections
- **openai_file_search.py**: Uses OpenAI vector store for semantic retrieval
- **local_vector_search.py**: Uses local ChromaDB for semantic retrieval (free, offline)
- **search.py**: Unified search function (`search_context()`) for both OpenAI and local backends
- **retrieve_context.py**: Main interface that dispatches to keyword search or delegates to `search.py` for semantic search

### Agent Tools

Located in `agent_tools/`:
- **tools.py**: Core utilities (SVD parsing, address calculation, file operations)
- **pdf_ops.py**: PDF processing (page extraction, text extraction)
- **md_ops.py**: Markdown operations (table extraction, header parsing)
- **get_pages_with_keyword.py**: Keyword-based page retrieval
- **svd_parsing.py**: SVD file parsing utilities

### Utilities

Located in `utils/`:
- **function_call_handler.py**: Provides unified abstraction for function calling
- **result_saver.py**: Standardized output saving (JSON, CSV, text, usage tracking)
- **parse_output.py**: Extracts JSON blocks and reasoning from LLM responses
- **models.py**: Model name mapping and configuration

### Prompts

Located in `prompts/`:
- **register_info_stm.py**: Generator system/user prompts for STM devices
- **coverage_improver.py**: Coverage improver prompts and query generation
- **validator.py**: Validator prompts for invariant checking
- **examples.py**: Few-shot examples for register extraction

## Performance Testing and Optimization

When running performance tests or optimization experiments, follow the organization guidelines in:

**`optimization/test_outputs/STRUCTURE.md`**

This document defines:
- How to organize test outputs by component and run number
- Required files for each test run (README, analysis/, comparison CSVs)
- Naming conventions and directory structure
- How to write comprehensive analysis documents
- Relationship between scripts and their outputs

**Key principle:** All test outputs go in `optimization/test_outputs/{component}/{run_number}/` and are git-ignored. Each run should be self-contained with documentation, analysis, and raw data.

## Data Organization

### Device Directory Structure
```
devices/{manufacturer}/{device_name}/
├── {device_name}.pdf              # Original datasheet
├── {device_name}.md               # Converted markdown (if applicable)
├── svd/*.svd                      # Ground truth SVD files
└── keyword_infos.json             # Keyword search metadata
```

### Output Directory Structure
```
agent_output/{manufacturer}/{device_name}/{run_number}/
├── {peripheral}_{register}        # Generated register JSON files
├── info/
│   ├── summary.txt                # Model and parameters
│   ├── usage.csv                  # Token usage per register
│   └── reasoning.txt              # Reasoning text per register
├── coverage_improver/
│   ├── coverage_improver_output.json
│   ├── coverage_info.json
│   ├── reasoning.txt
│   └── usage.csv
└── validator/
    ├── classification.csv
    ├── output.txt
    └── usage.csv
```

### Evaluation Directory Structure
```
evaluation/{manufacturer}/{device_name}/{run_number}/{svd_name}/
├── register_diff.csv              # Register-level differences
├── field_diff.csv                 # Field-level differences
└── ...                            # Other comparison outputs
```

## Data Models (defs.py)

Key Pydantic models:
- `RegisterInfo`: Complete register specification with fields, dependencies
- `BitField`: Individual field with bit range, access, enumerated values
- `ContextRetrievalParameters`: Configuration for datasheet context retrieval
- `CoverageInfo`: Coverage metrics and diff lists
- `CoverageImproverOutput`: Updated parameters and stop flag

## Adding a New Device

1. Add datasheet PDF and SVD files to `devices/{manufacturer}/{device_name}/`
2. Create vector store: `python3 context_retrieval/preprocessing/pipeline.py devices/<mfg>/<dev>/<dev>.pdf <dev> --format markdown --embed-metadata`
3. Add device entry to `config.user_contexts` with manufacturer, run number, and IDs
4. Update `config.DEVICE_NAME` to target the new device
5. Run `python3 core/s0_run_full_analysis.py`

## Deprecated/Unused Files

The following files are no longer used in the current pipeline:

- **context_retrieval/preprocessing/old/create_vector_store_openai.py**: Legacy raw-PDF vector store creation. Only used by `s0_run_full_analysis.py` for backward compat.
- **core/s1b_generator_dependencies.py**: Legacy generator flow that handled register dependencies. Not used by `core/s0_run_full_analysis.py`. Use `core/s1a_generator.py` instead.
- **core/s3_query_rewriter.py**: Removed — query rewrite feature was never enabled in practice.
- **prompts/query_rewriter.py**: Removed — prompts for the deleted query rewriter.
- **context_retrieval/search_cache.py**: Removed — was never imported anywhere.

## Important Notes

- The project uses both OpenAI and Groq clients (configured in `config.py`)
- Model name "gpt-oss-120b" routes to Groq, others to OpenAI (see `determine_client()`)
- Context truncation is handled in `scripts/limit_context.py` based on model limits
- The generator uses function calling to request additional context during extraction
- Coverage improver adjusts retrieval parameters between iterations to improve results
- All search-based components (validator, coverage improver) use `search_context()` from `context_retrieval/search.py`
- ResultSaver class provides standardized output formatting across all components
