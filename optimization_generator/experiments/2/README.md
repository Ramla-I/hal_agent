# Generator Embedding Count Test Results

This directory contains the results from testing different embedding counts for the generator's context retrieval.

## Test Configuration

- **Peripheral:** afio (Alternate Function I/O)
- **Registers:** 7 total (evcr, exticr1, exticr2, exticr3, exticr4, mapr, mapr2)
- **Verified Facts:** 147 from verified datasheet (rm0041)
- **Embedding Counts Tested:** 4, 8, 16, 50
- **Model:** gpt-oss-120b
- **Date:** January 22, 2026

## Directory Structure

```
generator/2/
├── README.md (this file)
├── analysis/                                      # Analysis files
│   ├── GENERATOR_EMBEDDING_ANALYSIS.md            # Comprehensive analysis
│   ├── generator_test_raw_output.txt              # Raw console output
│   ├── generator_embedding_comparison.csv         # Accuracy comparison
│   └── timing_comparison.csv                      # Timing breakdown
├── generator_test_embeddings_4/                   # Results with 4 embeddings
│   ├── afio_* (register JSON files)
│   ├── info/
│   └── timing_stats.json
├── generator_test_embeddings_8/                   # Results with 8 embeddings
├── generator_test_embeddings_16/                  # Results with 16 embeddings
└── generator_test_embeddings_50/                  # Results with 50 embeddings
```

## Files

### Analysis and Summary (in `analysis/` subdirectory)

- **GENERATOR_EMBEDDING_ANALYSIS.md** - Comprehensive analysis with recommendations
  - Overall results and key findings
  - Register-level breakdown
  - Timing analysis
  - Parser fix impact
  - Why more embeddings help
  - Problem areas identified
  - Production recommendations

- **generator_test_raw_output.txt** - Raw console output from test run
  - Timing summaries for each embedding count
  - Overall test completion status

### Structured Data (in `analysis/` subdirectory)

- **generator_embedding_comparison.csv** - Accuracy metrics
  - Columns: embeddings, registers_found, total_registers, correct, wrong, missing, total, accuracy

- **timing_comparison.csv** - Performance metrics
  - Columns: embeddings, llm_time_s, search_time_s, total_time_s, avg_llm_time_s, avg_search_time_s, percentages

### Raw Test Outputs

Each `generator_test_embeddings_N/` directory contains:
- `afio_*` - JSON output for each register
- `info/` - Subdirectory with:
  - `reasoning.txt` - LLM reasoning for each register
  - `summary.txt` - Test configuration summary
  - `usage.csv` - Token usage per register
- `timing_stats.json` - Timing breakdown for this embedding count

## Key Findings

**Winner: 50 embeddings for accuracy, 16 embeddings for balance**
- ✅ 50 embeddings: Best accuracy (69.4%), zero errors, 55.41s
- ✅ 16 embeddings: Good balance (65.3% accuracy, 44.85s, only 4% behind)
- ⚠️ 4 embeddings: Too little context (34.7% accuracy)
- ✅ **Critical achievement:** Zero wrong predictions after parser fix

### Accuracy by Embedding Count

| Embeddings | Correct | Missing | Accuracy | Time |
|------------|---------|---------|----------|------|
| 4          | 51/147  | 96/147  | 34.7%    | 33.64s |
| 8          | 84/147  | 63/147  | 57.1%    | 42.42s |
| 16         | 96/147  | 51/147  | 65.3%    | 44.85s |
| 50         | 102/147 | 45/147  | 69.4%    | 55.41s |

### Timing Breakdown

- **LLM time dominates:** 73-82% of total time
- **Search time stable:** ~9-10s regardless of embedding count
- **Total time scales with embeddings:** 33.64s (4 emb) → 55.41s (50 emb)

## Recommendations

1. **Use 50 embeddings when accuracy is critical**
   - Best coverage (69.4%)
   - Zero errors
   - Worth the extra 20% time cost

2. **Use 16 embeddings for routine work**
   - Good accuracy (65.3%)
   - 19% faster than 50 embeddings
   - Zero errors
   - Best balance of speed and quality

3. **Avoid 4 or 8 embeddings**
   - Insufficient context for complex registers
   - Poor accuracy (34-57%)
   - Speed advantage doesn't justify quality loss

## Notable Issues

1. **mapr register (39 facts):**
   - 4 emb: Only 8% correct
   - 16/50 emb: Both achieve 92%
   - Demonstrates importance of sufficient context for complex registers

2. **mapr2 register:**
   - Only 25% accuracy even at 50 embeddings
   - May have documentation quality issues
   - Needs investigation

3. **Missing registers vary by embedding count:**
   - Each configuration misses different registers
   - Likely due to vector search ranking variations

## Related Scripts

- **Test script:** `core/s1a_generator.py` (with __main__ test mode)
- **Analysis scripts:**
  - `optimization/compare_generator_with_verified.py` - Compare against verified datasheet
  - `optimization/analyze_generator_errors.py` - Detailed error analysis by register

## Date Generated

January 22, 2026
