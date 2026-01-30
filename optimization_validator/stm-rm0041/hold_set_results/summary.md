# Prompt Optimization Results Summary

## Accuracy Metrics

| Model Name | True Positives | False Negatives | False Positives | True Negatives | Accuracy | Precision | Recall | F1 Score |
|------------|----------------|-----------------|-----------------|----------------|----------|-----------|--------|----------|
| gpt-5.2 | 278 | 22 | 16 | 184 | 0.924 | 0.946 | 0.927 | 0.936 |
| gpt-oss-120b | 289 | 9 | 3 | 197 | 0.976 | 0.990 | 0.970 | 0.980 |
| gpt-5-nano | 285 | 14 | 40 | 160 | 0.892 | 0.877 | 0.953 | 0.913 |
| gpt-4.1-nano | 283 | 17 | 55 | 144 | 0.856 | 0.837 | 0.943 | 0.887 |

## Token Usage and Costs

| Model Name | Input Tokens | Input Tokens Cached | Output Tokens | Output Tokens Reasoning | Total Tokens | Cost ($) |
|------------|--------------|---------------------|---------------|-------------------------|--------------|----------|
| gpt-5.2 | 2,553,761 | 820,224 | 72,356 | 0 | 2,626,117 | 4.19 |
| gpt-oss-120b | 2,585,261 | 845,824 | 213,264 | 134,950 | 2,798,525 | 0.45 |
| gpt-5-nano | 2,553,755 | 801,024 | 184,761 | 121,344 | 2,738,516 | 0.17 |
| gpt-4.1-nano | 2,554,294 | 1,664 | 172,542 | 0 | 2,726,836 | 0.32 |