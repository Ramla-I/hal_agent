# Generator Chunking Strategy Comparison

**Date:** 2026-01-26
**Peripheral:** AFIO (7 registers, 147 verified facts)
**Datasheet:** rm0041 (STM32F100)

---

## Executive Summary

This analysis compares generator performance across **four chunking strategies**:
1. **Text Chunks** - Plain text, manually split with trackable IDs
2. **Markdown Chunks** - Markdown formatted, manually split with trackable IDs
3. **Markdown + Expansion** - Markdown chunks with contiguous page expansion (pages_after=2)
4. **MD Enriched + Expansion** - Markdown with embedded metadata headers + page expansion

All strategies tested with 4, 8, 16, and 50 embeddings (md_enriched only tested with 4, 8, 16).

### Key Findings

| Rank | Configuration | Embeddings | Accuracy | Tokens | Efficiency |
|------|---------------|------------|----------|--------|------------|
| 1 | **md_enriched+exp** | 16 | **75.5%** | 110,611 | 0.68 |
| 2 | md_enriched+exp | 4 | 74.8% | 56,645 | **1.32** |
| 3 | md+expansion | 8 | 73.5% | 192,784 | 0.38 |
| 4 | md+expansion | 16 | 73.5% | 290,819 | 0.25 |
| 5 | md_chunks | 4 | 72.8% | 60,268 | 1.21 |
| 6 | md_chunks | 50 | 72.8% | 257,144 | 0.28 |

**Best overall accuracy:** md_enriched+expansion @ 16 embeddings (75.5%)
**Best efficiency:** md_enriched+expansion @ 4 embeddings (1.32 accuracy/1K tokens)

---

## Comprehensive Results

### Accuracy Comparison

| Configuration | 4 emb | 8 emb | 16 emb | 50 emb |
|---------------|-------|-------|--------|--------|
| text_chunks | 49.0% | 43.5% | 48.3% | 67.3% |
| md_chunks | **72.8%** | 63.9% | 71.4% | 72.8% |
| md+expansion | 66.0% | **73.5%** | **73.5%** | 66.7% |
| md_enriched+exp | 74.8% | 68.0% | **75.5%** | - |

### Detailed Breakdown

| Run | Configuration | Embeddings | Correct | Wrong | Missing | Accuracy |
|-----|---------------|------------|---------|-------|---------|----------|
| 3 | text_chunks | 4 | 72 | 0 | 75 | 49.0% |
| 3 | text_chunks | 8 | 64 | 5 | 78 | 43.5% |
| 3 | text_chunks | 16 | 71 | 7 | 69 | 48.3% |
| 3 | text_chunks | 50 | 99 | 12 | 36 | 67.3% |
| 3 | md_chunks | 4 | 107 | 1 | 39 | 72.8% |
| 3 | md_chunks | 8 | 94 | 5 | 48 | 63.9% |
| 3 | md_chunks | 16 | 105 | 6 | 36 | 71.4% |
| 3 | md_chunks | 50 | 107 | 5 | 35 | 72.8% |
| 5 | md+expansion | 4 | 97 | 14 | 36 | 66.0% |
| 5 | md+expansion | 8 | 108 | 3 | 36 | 73.5% |
| 5 | md+expansion | 16 | 108 | 3 | 36 | 73.5% |
| 5 | md+expansion | 50 | 98 | 13 | 36 | 66.7% |
| 6 | md_enriched+exp | 4 | 110 | 1 | 36 | 74.8% |
| 6 | md_enriched+exp | 8 | 100 | 11 | 36 | 68.0% |
| 6 | md_enriched+exp | 16 | 111 | 0 | 36 | 75.5% |

---

## Token Usage Analysis

| Configuration | Embeddings | Input | Output | Reasoning | Search | Total | Efficiency |
|---------------|------------|-------|--------|-----------|--------|-------|------------|
| text_chunks | 4 | 48,473 | 8,911 | 3,354 | 18,108 | 57,384 | 0.85 |
| text_chunks | 8 | 65,655 | 9,979 | 3,657 | 35,372 | 75,634 | 0.58 |
| text_chunks | 16 | 99,153 | 9,049 | 3,231 | 68,910 | 108,202 | 0.45 |
| text_chunks | 50 | 233,290 | 12,412 | 5,163 | 203,379 | 245,702 | 0.27 |
| md_chunks | 4 | 50,423 | 9,845 | 3,282 | 19,888 | 60,268 | 1.21 |
| md_chunks | 8 | 71,142 | 10,337 | 3,570 | 40,502 | 81,479 | 0.78 |
| md_chunks | 16 | 105,386 | 11,690 | 4,485 | 74,581 | 117,076 | 0.61 |
| md_chunks | 50 | 244,888 | 12,256 | 5,177 | 214,198 | 257,144 | 0.28 |
| md+expansion | 4 | 116,102 | 12,793 | 5,242 | 85,562 | 128,895 | 0.51 |
| md+expansion | 8 | 180,536 | 12,248 | 4,397 | 149,929 | 192,784 | 0.38 |
| md+expansion | 16 | 279,714 | 11,105 | 4,101 | 248,699 | 290,819 | 0.25 |
| md+expansion | 50 | 721,435 | 12,973 | 4,123 | 689,702 | 734,408 | 0.09 |
| md_enriched+exp | 4 | 45,232 | 11,413 | 4,988 | 19,146 | 56,645 | **1.32** |
| md_enriched+exp | 8 | 65,045 | 10,554 | 3,564 | 39,004 | 75,599 | 0.90 |
| md_enriched+exp | 16 | 100,424 | 10,187 | 3,546 | 74,409 | 110,611 | 0.68 |

**Efficiency** = accuracy per 1K tokens (higher is better)

---

## Timing Analysis

| Configuration | Embeddings | Search (s) | LLM (s) | Total (s) | Time/1% Acc |
|---------------|------------|------------|---------|-----------|-------------|
| text_chunks | 4 | 10.1 | 23.6 | 33.7 | 0.69 |
| text_chunks | 50 | 10.5 | 39.1 | 49.6 | 0.74 |
| md_chunks | 4 | 10.5 | 28.5 | 39.0 | **0.54** |
| md_chunks | 16 | 9.7 | 35.5 | 45.2 | 0.63 |
| md+expansion | 4 | 10.6 | 37.7 | 48.3 | 0.73 |
| md+expansion | 16 | 10.7 | 44.4 | 55.2 | 0.75 |

**Key observations:**
- Search time is constant (~10s) regardless of embedding count
- LLM time increases with more embeddings (more context to process)
- md_chunks @ 4 embeddings is most time-efficient (0.54s per 1% accuracy)

---

## Cost-Benefit Summary

### 4 Embeddings vs 16 Embeddings

For md_enriched+expansion:
- **4 embeddings**: 74.8% accuracy, 56K tokens, 1.32 efficiency
- **16 embeddings**: 75.5% accuracy, 111K tokens, 0.68 efficiency
- **Delta**: +0.7% accuracy costs +95% more tokens

**Conclusion:** 4 embeddings is the sweet spot for md_enriched. The marginal accuracy gain from 16 embeddings is not worth the token cost.

### Strategy Comparison at 4 Embeddings

| Strategy | Accuracy | Tokens | Efficiency | Recommendation |
|----------|----------|--------|------------|----------------|
| md_enriched+exp | **74.8%** | 56,645 | **1.32** | Best overall |
| md_chunks | 72.8% | 60,268 | 1.21 | Good alternative |
| md+expansion | 66.0% | 128,895 | 0.51 | Not recommended |
| text_chunks | 49.0% | 57,384 | 0.85 | Not recommended |

---

## Production Recommendations

### Best Configuration
**md_enriched+expansion @ 4 embeddings**
- 74.8% accuracy
- 56,645 tokens (lowest among high-accuracy configs)
- 1.32 efficiency (best overall)
- Only 1 wrong answer

### Alternative (Maximum Accuracy)
**md_enriched+expansion @ 16 embeddings**
- 75.5% accuracy (highest overall)
- 110,611 tokens
- 0 wrong answers (perfect precision)
- Use when accuracy is critical and cost is not a concern

### Not Recommended
- **text_chunks** - consistently underperforms at all embedding counts
- **md+expansion without enriched metadata** - high token overhead without proportional accuracy gain
- **50 embeddings** - context overload causes performance degradation

---

## Test Output Structure

```
optimization/test_outputs/generator/
├── 3/                          # text_chunks and md_chunks tests
│   ├── text_chunks_embeddings_{4,8,16,50}/
│   └── md_chunks_embeddings_{4,8,16,50}/
├── 5/                          # md+expansion tests
│   └── md_plain_expansion_embeddings_{4,8,16,50}/
├── 6/                          # md_enriched+expansion tests
│   ├── md_enriched_expansion_embeddings_{4,8,16}/
│   └── md_enriched_expansion_comparison.csv
├── comprehensive_comparison.csv
└── token_usage_comparison.csv
```

---

## Vector Stores

| Name | VS ID | Description |
|------|-------|-------------|
| text_chunks | vs_69739f0610d8819183584c2d343e88a6 | Plain text chunks |
| md_chunks | vs_6973a4df01bc81919940212995712255 | Markdown formatted chunks |
| md_enriched | vs_6977b8e021f4819193431da11fd05f1c | Markdown with embedded metadata headers |

Configuration stored in: `devices/stm/rm0041/vector_stores.json`
