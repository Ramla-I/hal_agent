# Prompt Optimization Results Summary

## Accuracy Metrics

| Model Name | True Positives | False Negatives | False Positives | True Negatives | Accuracy | Precision | Recall | F1 Score |
|------------|----------------|-----------------|-----------------|----------------|----------|-----------|--------|----------|
| gpt-5.2 | 546 | 54 | 32 | 368 | 0.914 | 0.945 | 0.910 | 0.927 |
| gpt-oss-120b | 559 | 40 | 16 | 383 | 0.944 | 0.972 | 0.933 | 0.952 |
| gpt-4.1-nano | 551 | 40 | 85 | 302 | 0.872 | 0.866 | 0.932 | 0.898 |
| gpt-5-nano | 563 | 37 | 64 | 336 | 0.899 | 0.898 | 0.938 | 0.918 |


## Token Usage and Costs

| Model Name | Input Tokens | Input Tokens Cached | Output Tokens | Output Tokens Reasoning | Total Tokens | Cost ($) |
|------------|--------------|---------------------|---------------|-------------------------|--------------|----------|
| gpt-5.2 | 4,733,092 | 1,251,840 | 140,067 | 0 | 4,873,159 | 8.28 |
| gpt-oss-120b | 4,796,513 | 1,373,952 | 366,383 | 222,038 | 5,162,896 | 0.84 |
| gpt-4.1-nano | 4,734,319 | 0 | 368,956 | 0 | 5,103,275 | 0.62 |
| gpt-5-nano | 4,733,157 | 1,324,928 | 330,252 | 209,408 | 5,063,409 | 0.32 |