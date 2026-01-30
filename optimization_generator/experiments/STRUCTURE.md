# Test Outputs Structure

This directory contains all optimization test results, organized by component and run number.

## Directory Organization

```
test_outputs/
├── generator/
│   ├── 1/          # First generator test run
│   └── 2/          # Second generator test run (embedding comparison)
│       ├── analysis/                      # Analysis files
│       ├── generator_test_embeddings_4/   # Results with 4 embeddings
│       ├── generator_test_embeddings_8/   # Results with 8 embeddings
│       ├── generator_test_embeddings_16/  # Results with 16 embeddings
│       └── generator_test_embeddings_50/  # Results with 50 embeddings
│
└── validator/
    ├── 1/          # First validator test run
    │   ├── analysis/
    │   ├── validator_test_batched/        # Initial batched test (500 inv)
    │   └── validator_test_single/         # Initial single test (200 inv)
    │
    └── 2/          # Second validator test run (full comparison)
        ├── analysis/                              # Analysis files
        │   ├── VALIDATOR_OPTIMIZATION_ANALYSIS.md
        │   ├── validator_comparison_results_raw.txt
        │   ├── accuracy_comparison.csv
        │   ├── timing_comparison.csv
        │   └── token_usage_comparison.csv
        ├── gpt-oss-120b_sequential_test_emb4/     # Baseline (1000 inv)
        ├── gpt-oss-120b_batched_test_emb4/        # Batched with 4 embeddings
        ├── gpt-oss-120b_batched_test_emb8/        # Batched with 8 embeddings
        ├── gpt-oss-120b_batched_test_emb16/       # Batched with 16 embeddings
        └── README.md
```

## Naming Convention

### Run Numbers
- **Run 1**: Initial/exploratory tests
- **Run 2**: Comprehensive comparison tests
- **Run N**: Future test runs (increment as needed)

### Test Output Directories

**Generator:**
- `generator_test_embeddings_{N}/` - Generator output with N embeddings
- Contains: register JSON files, info/ subdirectory with usage/reasoning

**Validator:**
- `gpt-oss-120b_{mode}_test_emb{N}/` - Validator output
  - `{mode}` = sequential or batched
  - `{N}` = number of embeddings used
- Contains: validator output CSVs, usage stats, timing stats

## Analysis Structure

Each run should have an `analysis/` subdirectory containing:
- Summary markdown document (e.g., `VALIDATOR_OPTIMIZATION_ANALYSIS.md`)
- Raw results (e.g., `validator_comparison_results_raw.txt`)
- Comparison CSVs (accuracy, timing, token usage)
- Optional: visualizations, additional analysis

## Relationship to Scripts

### Generator Tests
- **Main Script:** `core/s1a_generator.py` (main script with __main__ test mode)
- **Analysis Scripts:** `optimization/compare_generator_with_verified.py`, `optimization/analyze_generator_errors.py`
- **Outputs:** `optimization/test_outputs/generator/{run}/`
- **Purpose:** Compare different embedding counts for context retrieval
- **Note:** Generator script is in core/, not optimization/, because it's part of the main pipeline. Analysis scripts are in optimization/ to be colocated with test outputs.

### Validator Tests
- **Main Script:** `optimization/s4a_validator_optimization.py`
- **Outputs:** `optimization/test_outputs/validator/{run}/`
- **Purpose:** Compare sequential vs batched validation modes

### Coverage Improver Tests
- **Main Script:** `optimization/s2a_coverage_improver_optimization.py`
- **Outputs:** `optimization/test_outputs/coverage_improver/{run}/` (TBD)
- **Purpose:** Optimize coverage improvement strategy

## Current State

### Generator Run 2 (Latest)
- **Date:** 2026-01-22
- **Configuration:** afio peripheral, all 7 registers, 4 embedding counts
- **Result:** 50 embeddings = 69.4% accuracy (best), 16 embeddings = 65.3% (good balance)
- **Analysis:** Located in `generator/2/analysis/` (TBD - needs to be added)

### Validator Run 2 (Latest)
- **Date:** 2026-01-22
- **Configuration:** Test set (1000 invariants), 4 modes tested
- **Result:** Batched 16 emb = 97.00% F1, 4.07x faster than sequential
- **Analysis:** Complete in `validator/2/analysis/`

## Maintenance

When adding new test runs:
1. Create new numbered subdirectory (e.g., `generator/3/`, `validator/3/`)
2. Put raw test outputs in the numbered directory
3. Create `analysis/` subdirectory
4. Add summary document explaining what was tested and results
5. Include comparison CSVs for quantitative analysis
6. Update this STRUCTURE.md if adding new test types

## Cleanup Policy

- Keep latest 2-3 runs for each component
- Archive older runs if needed for historical reference
- Never delete runs with novel findings or benchmarks
