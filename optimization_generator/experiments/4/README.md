# Generator Test Run 4: Markdown Enriched Chunks + Contiguous Expansion

**Date:** 2026-01-26
**Peripheral:** AFIO (7 registers, 147 verified facts)

## Test Configuration

This test evaluated two new retrieval optimization features:

1. **Embedded Metadata Headers** - Each chunk includes a metadata block at the top:
   ```
   <!-- CHUNK METADATA
   Chunk ID: rm0041_p187_c01
   Page: 187
   Peripheral: ADC
   Registers: ADC_DR
   Content Type: register_table
   Importance: critical
   Contains: tables, diagrams
   Keywords: data, conversion, injected
   -->
   ```

2. **Contiguous Chunk Expansion** - After semantic search, automatically pull chunks from subsequent pages (page+1, page+2) to provide additional context.

### Parameters
- Vector store: `vs_6973a4df01bc81919940212995712255` (md_enriched chunks)
- Chunk expansion: **Enabled**
- Pages after: 2
- Chunk index: `devices/stm/rm0041/chunks/md/upload_summary.csv`
- Model: gpt-oss-120b
- Embedding counts: 4, 8, 16, 50

## Results Summary

| Embeddings | Correct | Wrong | Missing | Accuracy | Registers | Total Time |
|------------|---------|-------|---------|----------|-----------|------------|
| 4          | 87      | 0     | 60      | 59.2%    | 6/7       | 41.12s     |
| 8          | 88      | 2     | 57      | 59.9%    | 6/7       | 48.86s     |
| 16         | 93      | 3     | 51      | 63.3%    | 7/7       | 58.90s     |
| 50         | 94      | 2     | 51      | 63.9%    | 7/7       | 125.10s    |

## Comparison with Plain Markdown (Run 3)

| Config | MD Enriched + Expansion | Plain Markdown | Delta |
|--------|------------------------|----------------|-------|
| 4 emb  | 59.2%                  | 70.7%          | **-11.5%** |
| 8 emb  | 59.9%                  | 53.7%          | +6.2%  |
| 16 emb | 63.3%                  | 74.1%          | **-10.8%** |
| 50 emb | 63.9%                  | 62.6%          | +1.3%  |

## Key Findings

1. **Underperformed expectations** - The combination of metadata headers + chunk expansion decreased accuracy at 4 and 16 embeddings compared to plain markdown.

2. **Marginal improvement at lower-performing configs** - 8 and 50 embeddings showed small gains where plain markdown was already struggling.

3. **Significant timing overhead** - 58.9s at 16 emb vs 45.2s for plain markdown (+30%).

## Conclusion

**NOT RECOMMENDED for production.** Plain markdown at 16 embeddings (74.1%) remains the best configuration.

Future experiments should test:
- Expansion only (without metadata headers)
- Metadata only (without expansion)
- Selective expansion for register_table chunks only
- pages_after=1 instead of pages_after=2

## Files

- `md_enriched_expansion_comparison.csv` - Accuracy comparison across embedding counts
- `md_enriched_expansion_embeddings_{4,8,16,50}/` - Output directories for each configuration
- `run_test.py` - Test script used for this run
