# Performance Optimization Plan for hal_agent Pipeline

## Current Performance Issues

Based on codebase analysis:
- **1,000-3,500 vector store search calls** per device processing run
- **NO caching** of search results
- **Sequential processing** (no parallelization)
- **Query rewriting enabled** by default (doubles search calls)
- **Validator is slowest component** (500-2,000 invariant validations)

## Optimization Strategies (Prioritized)

---

### ⭐⭐⭐⭐⭐ **#1: Cache Vector Store Search Results**

**Impact:** 50-70% reduction in search API calls
**Difficulty:** Low
**Implementation Time:** 30 minutes

#### Current Problem
```python
# s1a_generator.py - called 500-1500 times
for peripheral in peripherals:
    for register in registers:
        # EVERY call searches vector store from scratch
        context = retrieve_context(...)  # → search_vector_store()
```

**Same queries repeated across:**
- Multiple registers in same peripheral (similar queries)
- Multiple iterations of coverage improver
- Query rewriter and generator context retrieval

#### Solution: Add In-Memory Cache

**Step 1:** Already created `context_retrieval/search_cache.py`

**Step 2:** Update `context_retrieval/semantic_search.py`:

```python
# Add at top
from context_retrieval.search_cache import get_cache

def search_vector_store(query: str, vs_id: str, num_results: int, re_rank: bool, score_threshold: float):
    # Try cache first
    cache = get_cache()
    cached_result = cache.get(query, vs_id, num_results, re_rank, score_threshold)
    if cached_result is not None:
        logger.debug(f"Cache hit for query (length: {len(query)})")
        return cached_result

    # Query truncation
    if len(query) > 4096:
        logger.warning(f"Query is too long, truncating to 4096 characters. Original length: {len(query)}")
        query = query[:4096]

    # Fetch from API
    if re_rank:
        ranker = "auto"
    else:
        ranker = None

    results = client.vector_stores.search(
        vector_store_id=vs_id,
        query=query,
        max_num_results=num_results,
        ranking_options={
            "ranker": ranker,
            "score_threshold": score_threshold,
        },
    )

    # Store in cache
    cache.put(query, vs_id, num_results, re_rank, score_threshold, results)
    logger.debug(f"Cache miss for query (length: {len(query)})")

    return results
```

**Step 3:** Add cache stats logging in `s0_run_full_analysis.py`:

```python
from context_retrieval.search_cache import get_cache

# At end of run
cache = get_cache()
stats = cache.stats()
print(f"Search cache stats: {stats}")
# Clear cache for next run (optional)
# cache.clear()
```

**Expected Results:**
- First iteration: 0% cache hits
- Second iteration: 40-60% cache hits
- Third+ iterations: 60-80% cache hits
- **Overall reduction: 50-70% fewer API calls**

---

### ⭐⭐⭐⭐ **#2: Disable Query Rewriting by Default**

**Impact:** 50% reduction in generator search calls
**Difficulty:** Trivial
**Implementation Time:** 1 minute

#### Current Problem
```python
# config.py - CURRENT
CONTEXT_RETRIEVAL_PARAMETERS = ContextRetrievalParameters(
    query_rewrite=True,  # ← Doubles search calls!
    ...
)
```

Every register search triggers:
1. Query rewrite search (4 results)
2. Query rewrite LLM call
3. Original context search (16 results)
4. Generator LLM call

**4 API calls per register instead of 2**

#### Solution

```python
# config.py - RECOMMENDED
CONTEXT_RETRIEVAL_PARAMETERS = ContextRetrievalParameters(
    query_rewrite=False,  # ← Disable unless needed
    ...
)
```

**When to enable:**
- Only if coverage is low (<70%)
- Only in coverage improver iterations (not first run)
- Let coverage improver decide via its output

#### Expected Results:
- **50% reduction in generator API calls**
- Faster generator phase
- Minimal impact on quality (test first!)

---

### ⭐⭐⭐⭐ **#3: Batch Validator Invariants**

**Impact:** 80-90% reduction in validator API calls
**Difficulty:** Medium
**Implementation Time:** 2-3 hours

#### Current Problem
```python
# s4_validator.py - CURRENT SEQUENTIAL APPROACH
for invariant in invariants:  # 500-2000 invariants
    query = create_validator_file_search_query(...)
    file_search = search_vector_store(...)  # Search #1
    response = client.responses.create(...)  # LLM call #1
```

**500-2000 sequential API calls** (search + LLM)

#### Solution: Batch Validation

```python
# s4_validator.py - BATCHED APPROACH
BATCH_SIZE = 50  # Validate 50 invariants per LLM call

def batch_invariants(invariants, batch_size=50):
    """Group invariants into batches"""
    for i in range(0, len(invariants), batch_size):
        yield invariants[i:i + batch_size]

def run_validator_batched(...):
    for batch in batch_invariants(invariants, BATCH_SIZE):
        # Single comprehensive search query
        combined_query = "\n\n".join([
            f"Invariant {i}: {inv['peripheral_name']}.{inv['register_name']}.{inv['field_name']} - {inv['key']}={inv['value']}"
            for i, inv in enumerate(batch)
        ])

        file_search = search_vector_store(combined_query, vs_id, 20, True, 0.25)  # More results for batch
        file_search_text = format_results(file_search)

        # Single LLM call for entire batch
        batch_prompt = create_batch_validator_prompt(batch, file_search_text)
        response = client.responses.create(
            model=model_name,
            input=[{"role": "user", "content": batch_prompt}]
        )

        # Parse batch results
        results = parse_batch_validator_response(response.output_text, batch)
        for invariant, result in zip(batch, results):
            # Save individual results
            ...
```

**Prompt Structure:**
```python
def create_batch_validator_prompt(invariants, file_search):
    prompt = f"""Validate the following {len(invariants)} invariants against the datasheet.

File Search Results:
{file_search}

Invariants to validate:
"""
    for i, inv in enumerate(invariants):
        prompt += f"\n{i+1}. {inv['peripheral_name']}.{inv['register_name']}"
        if inv['field_name']:
            prompt += f".{inv['field_name']}"
        prompt += f" - {inv['key']} = {inv['value']}"

    prompt += """

For each invariant, respond with:
{
  "invariant_id": <number>,
  "classification": "true" or "false",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation>"
}

Output as JSON array.
"""
    return prompt
```

**Expected Results:**
- **500-2000 API calls → 10-40 batched calls**
- **80-90% reduction in validator time**
- Maintained validation quality

---

### ⭐⭐⭐ **#4: Parallelize Generator Register Processing**

**Impact:** 3-5x speedup for generator phase
**Difficulty:** Medium
**Implementation Time:** 2-3 hours

#### Current Problem
```python
# s1a_generator.py - SEQUENTIAL
for peripheral_name in register_names_to_process.keys():
    for register_name in register_names_to_process[peripheral_name]:
        # Process one register at a time (2-5 seconds each)
        ...
```

**500-1500 registers processed sequentially**

#### Solution: Parallel Processing

```python
# s1a_generator.py - PARALLEL
import concurrent.futures
from functools import partial

def process_single_register(peripheral_name, register_name, device_dir, context_params, ...):
    """Process one register (thread-safe)"""
    # Same logic as current loop body
    context = retrieve_context(...)
    response = client.responses.create(...)
    # Save results
    return (peripheral_name, register_name, result)

def run_generator_parallel(..., max_workers=10):
    # Build work items
    work_items = [
        (peripheral, register)
        for peripheral in register_names_to_process.keys()
        for register in register_names_to_process[peripheral]
    ]

    # Process in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        process_fn = partial(
            process_single_register,
            device_dir=device_directory,
            context_params=context_retrieval_parameters,
            ...
        )

        futures = [
            executor.submit(process_fn, peripheral, register)
            for peripheral, register in work_items
        ]

        # Collect results as they complete
        for future in concurrent.futures.as_completed(futures):
            peripheral, register, result = future.result()
            # Log or process result
            ...
```

**Considerations:**
- OpenAI API has rate limits (check tier)
- Use `max_workers=10` to start (adjust based on rate limits)
- Search cache becomes even more valuable with parallelization
- ResultSaver needs thread-safe file writes (use threading.Lock)

**Expected Results:**
- **3-5x speedup** (depends on rate limits)
- Generator phase: 30-60 minutes → 6-15 minutes

---

### ⭐⭐⭐ **#5: Reduce Vector Store Search Results Count**

**Impact:** 10-20% faster searches
**Difficulty:** Trivial
**Implementation Time:** 5 minutes

#### Current Settings
```python
# config.py
CONTEXT_RETRIEVAL_PARAMETERS = ContextRetrievalParameters(
    number_embeddings=16,  # ← Too many?
    ...
)
```

#### Experiment with Lower Values

```python
# Try different values and measure impact on coverage
number_embeddings=8,   # 50% reduction → faster searches
number_embeddings=12,  # 25% reduction
```

**Method:**
1. Run generator with `number_embeddings=8`
2. Compare coverage with baseline (16)
3. If coverage drop < 5%, keep lower value

**Expected Results:**
- **10-20% faster search calls**
- Potential minor coverage decrease (test first)

---

### ⭐⭐ **#6: Skip Validator on Early Iterations**

**Impact:** Skip 500-2000 calls on iteration 1
**Difficulty:** Low
**Implementation Time:** 15 minutes

#### Current Problem
```python
# s0_run_full_analysis.py
for i in range(coverage_improver_iterations):
    run_generator(...)
    run_validator(...)  # ← Slow, run every iteration
    run_coverage_improver(...)
```

Validator is expensive but not needed on early iterations.

#### Solution
```python
for i in range(coverage_improver_iterations):
    run_generator(...)

    # Only validate on last iteration
    if i == coverage_improver_iterations - 1:
        run_validator(...)

    if i < coverage_improver_iterations - 1:
        run_coverage_improver(...)
```

**Expected Results:**
- **Skip validator on iterations 1-N (keep only on final)**
- Faster feedback loop
- Final validation still occurs

---

### ⭐⭐ **#7: Use Smaller Model for Validator**

**Impact:** 2-3x faster validator LLM calls
**Difficulty:** Trivial
**Implementation Time:** 2 minutes

#### Current
```python
# config.py
VALIDATOR_MODEL_NAME = "gpt-4o"  # or similar
```

#### Suggested
```python
VALIDATOR_MODEL_NAME = "gpt-4o-mini"  # Much faster, cheaper
# or
VALIDATOR_MODEL_NAME = "gpt-oss-120b"  # If using Groq
```

Validation is a simpler task than generation - doesn't need the most powerful model.

**Test first:** Run on sample dataset, compare accuracy

**Expected Results:**
- **2-3x faster validator calls**
- **90% cost reduction**
- Possible minor accuracy decrease (test!)

---

### ⭐ **#8: Add Progress Bars and Timing**

**Impact:** Better visibility, no performance gain
**Difficulty:** Low
**Implementation Time:** 30 minutes

```python
from tqdm import tqdm
import time

# s1a_generator.py
total_registers = sum(len(regs) for regs in register_names_to_process.values())
with tqdm(total=total_registers, desc="Generating registers") as pbar:
    for peripheral_name in register_names_to_process.keys():
        for register_name in register_names_to_process[peripheral_name]:
            start = time.time()
            # Process register
            elapsed = time.time() - start
            pbar.set_postfix({"last": f"{elapsed:.1f}s", "periph": peripheral_name})
            pbar.update(1)
```

---

## Implementation Priority

### Phase 1: Quick Wins (1 hour)
1. ✅ Add search result caching
2. ✅ Disable query rewriting by default
3. ✅ Reduce `number_embeddings` to 8-12
4. ✅ Use smaller validator model

**Expected Impact:** 60-70% reduction in API calls, 2-3x faster

### Phase 2: Batching (2-3 hours)
5. ✅ Batch validator invariants (50 per call)

**Expected Impact:** Additional 50-60% reduction in validator time

### Phase 3: Parallelization (2-3 hours)
6. ✅ Parallelize generator register processing

**Expected Impact:** 3-5x speedup for generator

### Phase 4: Refinement
7. ✅ Skip validator on early iterations
8. ✅ Add progress bars and timing

---

## Measurement Plan

Before and after each optimization, measure:

```python
# Add to s0_run_full_analysis.py
import time

metrics = {
    "generator_time": 0,
    "validator_time": 0,
    "coverage_improver_time": 0,
    "total_api_calls": 0,
}

# Time each phase
start = time.time()
run_generator(...)
metrics["generator_time"] = time.time() - start

# Log at end
print(f"Performance Metrics: {json.dumps(metrics, indent=2)}")
```

**Baseline (current):**
- Total runtime: ~2-4 hours per device
- API calls: ~1,000-3,500

**Target (after all optimizations):**
- Total runtime: ~20-40 minutes per device
- API calls: ~200-500
- **Speedup: 3-6x**

---

## Cache Statistics Monitoring

Add to end of `s0_run_full_analysis.py`:

```python
from context_retrieval.search_cache import get_cache

cache = get_cache()
stats = cache.stats()
logger.info(f"Search Cache Statistics: {json.dumps(stats, indent=2)}")
```

This shows cache effectiveness.

---

## Risk Assessment

| Optimization | Risk | Mitigation |
|-------------|------|------------|
| Search caching | Stale results | Clear cache between runs or add TTL |
| Disable query rewrite | Lower coverage | Test on sample first, enable if needed |
| Batch validator | Accuracy loss | Compare batch vs individual results |
| Parallelization | Rate limits | Use conservative `max_workers`, add backoff |
| Smaller model | Accuracy loss | Validate on test set before deployment |

---

## Next Steps

1. **Implement search caching** (start here - highest impact, lowest risk)
2. **Test with single device** (rm0041) and measure
3. **Gradually add other optimizations**
4. **Monitor cache hit rates and accuracy**
5. **Tune batch sizes and parallelism** based on rate limits
