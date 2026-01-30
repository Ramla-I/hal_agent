# Prompt Optimization Results Summary

## Accuracy Metrics

| Model Name | True Positives | False Negatives | False Positives | True Negatives | Accuracy | Precision | Recall | F1 Score |
|------------|----------------|-----------------|-----------------|----------------|----------|-----------|--------|----------|
| gpt-oss-120b_test_bs2_emb8 | 491 | 109 | 3 | 397 | 0.888 | 0.994 | 0.818 | 0.898 |
| gpt-oss-120b_test_bs3_emb8 | 501 | 99 | 6 | 392 | 0.895 | 0.988 | 0.835 | 0.905 |
| gpt-oss-120b_test_bs1_emb4 | 471 | 112 | 11 | 375 | 0.873 | 0.977 | 0.808 | 0.885 |
| gpt-oss-120b_test_sequential_emb4 | 548 | 37 | 5 | 389 | 0.957 | 0.991 | 0.937 | 0.963 |
| gpt-oss-120b_test_bs3_emb16 | 530 | 70 | 8 | 392 | 0.922 | 0.985 | 0.883 | 0.931 |
| gpt-oss-120b_test_bs1_emb16 | 566 | 26 | 9 | 383 | 0.964 | 0.984 | 0.956 | 0.970 |
| gpt-oss-120b_test_bs1_emb8 | 515 | 62 | 11 | 377 | 0.924 | 0.979 | 0.893 | 0.934 |
| gpt-oss-120b_test_bs2_emb16 | 524 | 76 | 7 | 393 | 0.917 | 0.987 | 0.873 | 0.927 |


## Token Usage and Costs

| Model Name | Input Tokens | Input Tokens Cached | Output Tokens | Output Tokens Reasoning | Total Tokens | Cost ($) |
|------------|--------------|---------------------|---------------|-------------------------|--------------|----------|
| gpt-oss-120b_test_bs2_emb8 | 533,833 | 55,296 | 95,613 | 51,807 | 629,446 | 0.13 |
| gpt-oss-120b_test_bs3_emb8 | 364,222 | 18,432 | 87,419 | 47,330 | 451,641 | 0.11 |
| gpt-oss-120b_test_bs1_emb4 | 565,612 | 61,440 | 118,596 | 64,583 | 684,208 | 0.15 |
| gpt-oss-120b_test_sequential_emb4 | 5,173,864 | 1,718,528 | 380,529 | 233,557 | 5,554,393 | 0.88 |
| gpt-oss-120b_test_bs3_emb16 | 666,331 | 100,352 | 90,539 | 49,621 | 756,870 | 0.15 |
| gpt-oss-120b_test_bs1_emb16 | 1,926,140 | 147,200 | 123,905 | 68,587 | 2,050,045 | 0.35 |
| gpt-oss-120b_test_bs1_emb8 | 1,020,994 | 114,688 | 121,732 | 66,499 | 1,142,726 | 0.22 |
| gpt-oss-120b_test_bs2_emb16 | 988,703 | 35,840 | 101,329 | 55,898 | 1,090,032 | 0.21 |


## Timing Metrics

| Model Name | Operation | Count | Total (s) | Avg (s) | Min (s) | P25 (s) | Median (s) | P75 (s) | P90 (s) | P95 (s) | P99 (s) | Max (s) |
|------------|-----------|-------|-----------|---------|---------|---------|------------|---------|---------|---------|---------|---------|
| gpt-oss-120b_test_bs2_emb8 | vector_store_search | 142 | 174.078 | 1.226 | 0.998 | 1.082 | 1.172 | 1.316 | 1.474 | 1.599 | 1.889 | 1.922 |
| gpt-oss-120b_test_bs2_emb8 | validator_llm_call | 71 | 306.830 | 4.322 | 1.470 | 2.643 | 3.697 | 5.121 | 8.424 | 9.280 | 10.593 | 10.916 |
| gpt-oss-120b_test_bs3_emb8 | vector_store_search | 94 | 119.740 | 1.274 | 1.032 | 1.117 | 1.181 | 1.428 | 1.535 | 1.717 | 2.145 | 2.145 |
| gpt-oss-120b_test_bs3_emb8 | validator_llm_call | 47 | 253.222 | 5.388 | 2.050 | 3.360 | 4.559 | 6.987 | 9.646 | 10.661 | 11.299 | 11.487 |
| gpt-oss-120b_test_bs1_emb4 | vector_store_search | 141 | 171.750 | 1.218 | 1.017 |  |  |  |  |  |  | 2.281 |
| gpt-oss-120b_test_bs1_emb4 | validator_llm_call | 141 | 444.769 | 3.154 | 1.009 |  |  |  |  |  |  | 11.755 |
| gpt-oss-120b_test_sequential_emb4 | vector_store_search | 1000 | 1428.155 | 1.428 | 0.966 |  |  |  |  |  |  | 50.130 |
| gpt-oss-120b_test_sequential_emb4 | validator_llm_call | 1000 | 1547.219 | 1.547 | 0.724 |  |  |  |  |  |  | 6.763 |
| gpt-oss-120b_test_bs3_emb16 | vector_store_search | 94 | 125.712 | 1.337 | 1.082 | 1.155 | 1.230 | 1.356 | 1.633 | 2.190 | 2.552 | 2.552 |
| gpt-oss-120b_test_bs3_emb16 | validator_llm_call | 47 | 286.653 | 6.099 | 2.249 | 4.387 | 5.093 | 7.014 | 9.698 | 12.003 | 16.799 | 19.120 |
| gpt-oss-120b_test_bs1_emb16 | vector_store_search | 141 | 242.197 | 1.718 | 1.080 |  |  |  |  |  |  | 18.635 |
| gpt-oss-120b_test_bs1_emb16 | validator_llm_call | 141 | 488.306 | 3.463 | 1.449 |  |  |  |  |  |  | 14.013 |
| gpt-oss-120b_test_bs1_emb8 | vector_store_search | 141 | 201.912 | 1.432 | 1.035 |  |  |  |  |  |  | 16.725 |
| gpt-oss-120b_test_bs1_emb8 | validator_llm_call | 141 | 428.146 | 3.036 | 1.102 |  |  |  |  |  |  | 11.853 |
| gpt-oss-120b_test_bs2_emb16 | vector_store_search | 142 | 175.194 | 1.234 | 1.024 | 1.118 | 1.199 | 1.332 | 1.429 | 1.554 | 1.732 | 1.811 |
| gpt-oss-120b_test_bs2_emb16 | validator_llm_call | 71 | 312.118 | 4.396 | 1.551 | 2.718 | 3.789 | 5.208 | 7.363 | 9.201 | 10.413 | 10.822 |