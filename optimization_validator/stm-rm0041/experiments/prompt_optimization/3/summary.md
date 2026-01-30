# Prompt Optimization Results Summary

## Accuracy Metrics

| Model Name | True Positives | False Negatives | False Positives | True Negatives | Accuracy | Precision | Recall | F1 Score |
|------------|----------------|-----------------|-----------------|----------------|----------|-----------|--------|----------|
| gpt-5.2 | 541 | 59 | 16 | 384 | 0.925 | 0.971 | 0.902 | 0.935 |
| gpt-oss-120b | 563 | 35 | 6 | 394 | 0.959 | 0.989 | 0.941 | 0.965 |
| gpt-4.1-nano | 562 | 31 | 83 | 312 | 0.885 | 0.871 | 0.948 | 0.908 |
| gpt-5-nano | 575 | 25 | 65 | 335 | 0.910 | 0.898 | 0.958 | 0.927 |


## Token Usage and Costs

| Model Name | Input Tokens | Input Tokens Cached | Output Tokens | Output Tokens Reasoning | Total Tokens | Cost ($) |
|------------|--------------|---------------------|---------------|-------------------------|--------------|----------|
| gpt-5.2 | 5,113,179 | 1,630,720 | 142,349 | 0 | 5,255,528 | 8.38 |
| gpt-oss-120b | 5,176,149 | 1,747,200 | 386,265 | 239,520 | 5,562,414 | 0.88 |
| gpt-4.1-nano | 5,113,819 | 0 | 329,693 | 0 | 5,443,512 | 0.64 |
| gpt-5-nano | 5,113,046 | 1,645,056 | 325,273 | 203,584 | 5,438,319 | 0.32 |