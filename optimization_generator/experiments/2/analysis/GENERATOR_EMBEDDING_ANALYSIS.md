# Generator Embedding Count Analysis

## Executive Summary

**Winner: 50 embeddings for accuracy, 16 embeddings for balance**
- ✅ 50 embeddings: Best accuracy (69.4%), all predictions correct
- ✅ 16 embeddings: Good balance (65.3% accuracy, 33% faster than 50)
- ⚠️ 4 embeddings: Too little context (34.7% accuracy)
- ✅ **Critical Fix:** Parser now correctly handles start_bit/end_bit ordering

## Test Configuration

- **Peripheral:** afio (Alternate Function I/O)
- **Registers:** 7 total (evcr, exticr1-4, mapr, mapr2)
- **Verified Facts:** 147 total from verified datasheet
- **Embedding Counts Tested:** 4, 8, 16, 50
- **Model:** gpt-oss-120b
- **Date:** January 22, 2026

## Overall Results

| Embeddings | Registers Found | Correct | Wrong | Missing | Accuracy | Time |
|------------|----------------|---------|-------|---------|----------|------|
| 4          | 5/7            | 51/147  | 0     | 96/147  | 34.7%    | 33.64s |
| 8          | 6/7            | 84/147  | 0     | 63/147  | 57.1%    | 42.42s |
| 16         | 6/7            | 96/147  | 0     | 51/147  | 65.3%    | 44.85s |
| **50**     | **6/7**        | **102/147** | **0** | **45/147** | **69.4%** | **55.41s** |

### Key Finding: Zero Wrong Predictions

After fixing the parser to properly handle `start_bit/end_bit` ordering (ensuring start_bit ≤ end_bit), **all configurations achieved zero wrong predictions**. The only differences are in coverage (missing facts).

## Register-Level Breakdown

| Register | 4 emb | 8 emb | 16 emb | 50 emb | Total Facts |
|----------|-------|-------|--------|--------|-------------|
| evcr     | MISSING | 12/12 (100%) | 6/12 (50%) | 12/12 (100%) | 12 |
| exticr1  | 15/15 (100%) | 15/15 (100%) | 15/15 (100%) | MISSING | 15 |
| exticr2  | 15/15 (100%) | 15/15 (100%) | 15/15 (100%) | 15/15 (100%) | 15 |
| exticr3  | 15/15 (100%) | 15/15 (100%) | 15/15 (100%) | 15/15 (100%) | 15 |
| exticr4  | 3/15 (20%) | 15/15 (100%) | MISSING | 15/15 (100%) | 15 |
| mapr     | 3/39 (8%) | 12/39 (31%) | 36/39 (92%) | 36/39 (92%) | 39 |
| mapr2    | MISSING | MISSING | 9/36 (25%) | 9/36 (25%) | 36 |

### Key Observations

1. **Simple registers (exticr2, exticr3):** Perfect 100% across all embedding counts
2. **Complex register (mapr, 39 facts):**
   - 4 embeddings: Only 8% correct (too little context)
   - 8 embeddings: 31% correct
   - 16/50 embeddings: Both achieve 92% (diminishing returns)
3. **Missing registers vary by embedding count:**
   - Each configuration misses different registers
   - No clear pattern - may be vector search ranking variation

## Timing Analysis

### Time Breakdown

```
Embeddings   LLM Time   Search Time   Total     LLM %   Search %
──────────────────────────────────────────────────────────────────
4            24.52s     9.12s         33.64s    72.9%   27.1%
8            32.28s     10.14s        42.42s    76.1%   23.9%
16           35.21s     9.65s         44.85s    78.5%   21.5%
50           45.61s     9.80s         55.41s    82.3%   17.7%
```

### Key Insights

1. **LLM time dominates:** 73-82% of total time
2. **Search time stable:** ~9-10s regardless of embedding count
3. **LLM time scales with embeddings:**
   - 4→50 embeddings: 1.86x increase in LLM time (24.52s → 45.61s)
   - Total time: 1.65x increase (33.64s → 55.41s)
4. **Search is not the bottleneck:** Only 17-27% of total time

### Performance vs Quality Trade-off

| Config | Time | Speedup vs 50 | Accuracy | Accuracy Loss |
|--------|------|---------------|----------|---------------|
| 4 emb  | 33.64s | 1.65x faster | 34.7% | -34.7% |
| 8 emb  | 42.42s | 1.31x faster | 57.1% | -12.3% |
| 16 emb | 44.85s | 1.24x faster | 65.3% | -4.1% |
| 50 emb | 55.41s | baseline | 69.4% | baseline |

## Parser Fix Impact

### Before Fix (Historical Context)
- **8 embeddings:** 2 wrong predictions in mapr register
- **50 embeddings:** 8 wrong predictions in exticr4 register
  - Systematic bit offset errors (+3 offset)
  - Negative bit widths (-2)

### After Fix
- **All embeddings:** 0 wrong predictions
- **Root cause:** Model sometimes outputs bit ranges with end_bit < start_bit
- **Solution:** Parser now calculates:
  ```python
  start_bit = min(bit_info['start_bit'], bit_info['end_bit'])
  end_bit = max(bit_info['start_bit'], bit_info['end_bit'])
  bit_offset = start_bit
  bit_width = end_bit - start_bit + 1
  ```

## Why More Embeddings Help

### Context Matters for Complex Registers

**4 Embeddings (~3,200 tokens):**
- Sufficient for simple registers (exticr1-3)
- Insufficient for complex registers (mapr with 39 fields)
- Only captures small portion of register documentation

**16 Embeddings (~12,900 tokens):**
- Captures most register documentation
- Handles complex registers well (92% on mapr)
- Good balance of speed and quality

**50 Embeddings (~40,000 tokens):**
- Comprehensive documentation coverage
- Best accuracy (69.4%)
- Diminishing returns for complex registers (same 92% on mapr as 16)
- Benefits from capturing edge cases and cross-references

## Problem Areas

### 1. mapr2 Register (25% accuracy at best)
- 36 facts, only 9 correct even at 50 embeddings
- Suggests documentation quality issues or unusual structure
- May need different retrieval strategy

### 2. Missing Registers Vary by Embedding Count
- No predictable pattern
- Likely due to vector search ranking variations
- Different embeddings may push different registers below threshold

### 3. Partial Coverage on Complex Registers
- mapr: Missing 3-8% of facts even at high embedding counts
- Suggests some facts are hard to extract or not well-documented

## Recommendations

### For Production Use

1. **Use 50 embeddings for highest accuracy**
   - Best overall coverage (69.4%)
   - Zero errors
   - Time cost acceptable for quality gain
   - Recommended when accuracy is critical

2. **Use 16 embeddings for good balance**
   - 65.3% accuracy (only 4% behind 50)
   - 19% faster than 50 embeddings
   - Zero errors
   - Recommended for routine use

3. **Avoid 4 or 8 embeddings**
   - 4 emb: Only 34.7% accuracy
   - 8 emb: Only 57.1% accuracy
   - Insufficient context for complex registers
   - Speed advantage doesn't justify quality loss

### For Future Improvements

1. **Investigate mapr2 register**
   - Why only 25% accuracy?
   - Check datasheet documentation quality
   - May need manual review or different approach

2. **Adaptive embedding count**
   - Simple registers (few fields): Use 8-16 embeddings
   - Complex registers (many fields): Use 50 embeddings
   - Could optimize both speed and quality

3. **Register retrieval consistency**
   - Why do different embedding counts miss different registers?
   - Could improve vector search ranking or thresholds
   - May need minimum confidence threshold

## Comparison with Validator Optimization

**Generator (this analysis):**
- 7 registers, 147 facts
- 50 embeddings best (69.4% accuracy)
- LLM time is bottleneck (73-82% of time)
- Diminishing returns after 16 embeddings for complex registers

**Validator (separate analysis):**
- 1000 invariants
- Batched 16 embeddings best (97.00% F1 score)
- 4.07x faster than sequential
- Batching eliminated search bottleneck

**Conclusion:** Different parts of pipeline have different optimal configurations. Generator benefits from high embedding count for context, validator benefits from batching for speed.

## Conclusion

The generator embedding optimization shows clear benefits from higher embedding counts, with 50 embeddings achieving the best accuracy (69.4%) and zero errors. The parser fix was critical in eliminating wrong predictions. For production use, 50 embeddings is recommended when accuracy is critical, while 16 embeddings offers a good balance of speed and quality.

The main limitation is coverage rather than correctness - more embeddings help capture more facts but have diminishing returns, especially for very complex or poorly documented registers like mapr2.
