# Validator Optimization Analysis - Test Set Results

## Executive Summary

**Winner: Batched with 16 embeddings**
- ✅ Best quality: 97.00% F1 score (0.69% better than sequential baseline)
- ✅ 4.07x faster (731s vs 2975s, saves 37 minutes)
- ✅ 85.9% fewer API calls (141 vs 1000)
- ⚠️ Uses 4x more tokens per call (12,866 vs 3,212 file search tokens)

## Detailed Performance Comparison

### 1. Execution Time Breakdown

```
Configuration            LLM Time      Search Time   Total Time   Time Split   API Calls
─────────────────────────────────────────────────────────────────────────────────────────
Sequential, 4 emb        1547s (52%)   1428s (48%)   2975s       50/50         1000
Batched, 4 emb            445s (72%)    172s (28%)    617s       72/28          141
Batched, 8 emb            428s (68%)    202s (32%)    630s       68/32          141
Batched, 16 emb           488s (67%)    242s (33%)    731s       67/33          141
Batched, 16 emb (bs=20)   943s (69%)    414s (31%)   1357s       69/31           37
```

**Key Observations:**
- Sequential mode: 50/50 split between LLM and search (both are bottlenecks)
- Batched mode: 67-72% LLM time (search bottleneck eliminated)
- Batching by register provides 4x speedup vs sequential
- Larger batches (bs=20) are slower despite 74% fewer API calls (1357s vs 731s)
  - More context per call increases LLM processing time non-linearly
  - Demonstrates that API call count alone doesn't determine performance

### 2. Quality Metrics Analysis

#### Confusion Matrix Comparison

```
Configuration            TP      FP      TN      FN      Total
───────────────────────────────────────────────────────────────
Sequential, 4 emb        548     5       389     37      979
Batched, 4 emb           471     11      375     112     969
Batched, 8 emb           515     11      377     62      965
Batched, 16 emb          566     9       383     26      984
Batched, 16 emb (bs=20)  550     7       393     50     1000
```

**Analysis:**
- Sequential baseline: 548 TP, 37 FN (missed 37 true invariants)
- Batched 4 emb: 471 TP, 112 FN (missed 112 true invariants) - too little context
- Batched 8 emb: 515 TP, 62 FN (missed 62 true invariants) - better but not enough
- **Batched 16 emb (by register): 566 TP, 26 FN** (only missed 26) - best performance!
- Batched 16 emb (bs=20): 550 TP, 50 FN - combining registers degrades quality

**Surprising Finding:** Batched with 16 embeddings caught 18 MORE true positives than sequential (566 vs 548)

**Batch Size Impact:** Combining multiple registers (bs=20) results in 16 fewer TPs and 24 more FNs compared to batching by register, showing that natural register boundaries provide better context coherence.

#### Precision-Recall Trade-off

```
Configuration            Precision   Recall    F1 Score   Accuracy
────────────────────────────────────────────────────────────────────
Sequential, 4 emb        99.10%      93.68%    96.31%     95.71%
Batched, 4 emb           97.72%      80.79%    88.45%     87.31%
Batched, 8 emb           97.91%      89.25%    93.38%     92.44%
Batched, 16 emb          98.43%      95.61%    97.00%     96.44%
Batched, 16 emb (bs=20)  98.74%      91.67%    95.07%     94.30%
```

**Key Insights:**
- 4 embeddings: High precision but poor recall (missing too many true facts)
- 8 embeddings: Better balance but still 4% behind sequential
- 16 embeddings (by register): Best of both worlds - high precision AND high recall
- 16 embeddings surpasses sequential on all metrics except precision (98.43% vs 99.10%)
- Larger batches (bs=20): Precision slightly higher but recall drops significantly (91.67% vs 95.61%), resulting in lower F1 score

### 3. Token Usage Analysis

```
Configuration          File Search Tokens   Input Tokens   Increase vs 4 emb
─────────────────────────────────────────────────────────────────────────────
Sequential, 4 emb      3,212               5,174          baseline
Batched, 4 emb         3,212               4,011          1.0x
Batched, 8 emb         6,437               7,241          2.0x
Batched, 16 emb        12,866              13,661         4.0x
```

**Observations:**
- File search tokens scale linearly with embedding count
- Batched mode uses slightly fewer input tokens than sequential (4,011 vs 5,174) at same embedding count
- 16 embeddings = 4x token cost but provides comprehensive context

**Cost-Benefit:**
- 4x more tokens but 4x faster execution
- Total API calls reduced by 86% (141 vs 1000)
- Overall cost likely similar or lower due to fewer API calls

### 4. Error Analysis

#### JSON Parsing Errors

```
Mode                   Errors    Total Batches   Error Rate
────────────────────────────────────────────────────────────
Sequential, 4 emb      21        1000           2.1%
Batched, 4 emb         3         141            2.1%
Batched, 8 emb         3         141            2.1%
Batched, 16 emb        5         141            3.5%
```

**Error Types:**
1. "Expecting property name enclosed in double quotes" - malformed JSON
2. "Expecting ',' delimiter" - missing commas in JSON
3. "Invalid invariant_index -1" - model didn't return proper index
4. "Extra data" - JSON followed by additional text

**Root Cause:** Model occasionally produces malformed JSON, especially for:
- Registers with invalid/corrupted names (e.g., "lxvfskh", "hzcevsteuss")
- Complex registers with many fields (bkp_dr*, exti_*)
- Edge cases in test set

**Impact:** Errors are rare (2-4%) and don't significantly affect overall metrics

### 5. Batch Size Distribution

```
Average batch size: 7.1 invariants per register
Total batches: 141
Total invariants: 1000
```

**Interpretation:**
- Most registers have 5-10 invariants to validate
- Batching provides natural grouping by (peripheral, register)
- Model can see full register context when validating

## Why Batched 16 Embeddings Outperforms Sequential

### Hypothesis: Context Matters

**Sequential (4 emb):**
- Validates each invariant independently
- Limited context (4 embeddings = ~3,200 tokens of datasheet)
- May miss relationships between fields in same register
- Makes 1000 separate decisions

**Batched (16 emb):**
- Validates all invariants for a register together
- Rich context (16 embeddings = ~12,900 tokens of datasheet)
- Can cross-reference fields and detect inconsistencies
- Makes 141 batch decisions with full register context

**Result:** The model makes better decisions when it sees:
1. All fields in a register together
2. More comprehensive datasheet context
3. Relationships between related invariants

### Example Benefit

Register: `afio_mapr` (39 invariants in verified set)

**Sequential approach:**
- Validates each field independently
- May not catch that multiple fields share bit ranges
- Limited datasheet context per validation

**Batched approach:**
- Sees all 39 invariants at once
- Can verify that bit offsets don't overlap
- Can cross-reference field descriptions
- Has 4x more datasheet context to work with

## Batch Size Optimization

### Testing Larger Batches (batch_size=20)

We tested combining multiple registers into larger batches (~20-30 invariants) to reduce API calls further:

**Results:**
```
Configuration              API Calls  Total Time   F1 Score   TP/FP/TN/FN
──────────────────────────────────────────────────────────────────────────
Batched, 16 emb (by reg)   141        731s         97.00%     566/9/383/26
Batched, 16 emb (bs=20)     37       1357s         95.07%     550/7/393/50
```

**Key Findings:**

1. **API call reduction:** 74% fewer calls (37 vs 141) by grouping registers
2. **Quality degradation:** F1 dropped from 97.00% to 95.07% (-1.93%)
   - 16 fewer true positives (550 vs 566)
   - 24 more false negatives (50 vs 26)
3. **Performance paradox:** Despite 74% fewer API calls, total time increased 86% (1357s vs 731s)
   - LLM time: 943s vs 488s (93% increase)
   - Search time: 414s vs 242s (71% increase)
4. **Context limits hit:** One batch exceeded context length and required automatic splitting
   - `batch_32_(13_registers)` with 28 invariants triggered split
   - Demonstrates that larger batches can hit model limits

**Why Larger Batches Are Slower:**

The counterintuitive slowdown appears to be due to:
- **Token processing overhead:** Larger batches mean more context per API call, which increases LLM processing time quadratically (attention mechanism scales with context length squared)
- **Search overhead:** Retrieving embeddings for multiple registers multiplies search costs
- **Lost parallelism:** Sequential processing of 37 large batches vs 141 smaller batches that could potentially benefit from caching/optimization
- **Quality degradation → confidence issues:** Model may spend more reasoning time when context is cluttered with multiple unrelated registers

**Conclusion:**

Batching by register (one register per batch) is optimal. Trying to combine multiple registers into larger batches:
- ❌ Reduces quality (97.00% → 95.07% F1)
- ❌ Increases total time (731s → 1357s, despite fewer API calls)
- ❌ Risks hitting context limits
- ✅ Only benefit: 74% fewer API calls (marginal cost savings offset by performance loss)

The "by register" batching naturally aligns with the model's ability to reason about related invariants while keeping context manageable.

## Recommendations

### 1. Use Batched with 16 Embeddings (by register) for Production
**Rationale:**
- Best quality (97.00% F1 score)
- 4x faster than sequential
- 86% fewer API calls
- Token cost offset by reduced API call count
- **Use `batch_size=None`** to batch by register (one register per batch)
- Avoid larger batch sizes (e.g., batch_size=20) which reduce quality and increase time

### 2. Acceptable Alternative: Batched with 8 Embeddings
**Use case:** When token cost is a primary concern
- Still 4.7x faster
- 93.38% F1 score (good but not best)
- 2x token cost vs 4 embeddings
- Reasonable quality-cost trade-off

### 3. Avoid: Batched with 4 Embeddings
**Reason:**
- Poor F1 score (88.45%)
- Too little context leads to 112 false negatives
- Speed advantage doesn't justify quality loss

### 4. Sequential Mode: Only for Benchmarking
**Characteristics:**
- High quality (96.31% F1) but slower than batched 16
- 5x slower than batched alternatives
- No longer the quality leader
- Higher API call costs

## Cost Analysis

### API Call Reduction

```
Sequential:  1000 calls × $X per call = 1000X
Batched:      141 calls × $Y per call =  141Y

Where Y ≈ 4X (due to 4x tokens with 16 embeddings)

Total cost: 141 × 4X = 564X
Savings: 1000X - 564X = 436X (43.6% cost reduction)
```

**Conclusion:** Even with 4x tokens per call, batched mode costs 43.6% less due to 86% fewer API calls.

### Time Value

For a dataset with 5,607 invariants (like the full rm0041 validation):
- Sequential: ~16,677 seconds (4.6 hours)
- Batched 16 emb: ~4,095 seconds (1.1 hours)
- **Time saved: 3.5 hours per full validation run**

## Implemented Features

### Automatic Batch Splitting for Context Limits
✅ **Status: Implemented and tested**

When a batch exceeds the model's context limit, the system now automatically:
1. Detects context length errors
2. Splits the batch in half (by registers or by invariants)
3. Recursively processes sub-batches until they succeed
4. Aggregates results from all sub-batches

**Demonstrated in batch_size=20 test:**
- `batch_32_(13_registers)` with 28 invariants hit context limit
- Automatically split into 2 sub-batches (6 and 7 registers)
- Both sub-batches succeeded and results were combined

This provides robustness against edge cases where very large registers or unusual batching might exceed limits.

## Future Improvements

### 1. Reduce JSON Parsing Errors
- Add output schema validation in prompt
- Provide clear JSON format examples
- Add error recovery for malformed JSON

### 2. Adaptive Embedding Count
- Simple registers (few fields): Use 8 embeddings
- Complex registers (many fields): Use 16 embeddings
- Could save tokens while maintaining quality

### 3. Investigate "Better than Sequential" Effect
- Why does batched 16 catch more TPs than sequential?
- Can we leverage this in other parts of the pipeline?
- Is there emergent reasoning from seeing related invariants together?

## Conclusion

Batched validation with 16 embeddings represents a significant improvement over sequential validation:
- ✅ **Better quality** (97.00% vs 96.31% F1 score)
- ✅ **4x faster** (12 minutes vs 50 minutes)
- ✅ **44% lower cost** (fewer API calls despite more tokens)
- ✅ **Scales better** (141 batches vs 1000 calls for any dataset)

This is a clear win-win: better, faster, and cheaper.
