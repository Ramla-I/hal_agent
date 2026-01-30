# Prompt Optimization Results Summary

## Accuracy Metrics

| Model Name | True Positives | False Negatives | False Positives | True Negatives | Accuracy | Precision | Recall | F1 Score |
|------------|----------------|-----------------|-----------------|----------------|----------|-----------|--------|----------|
| gpt-5.2 | 649 | 51 | 0 | 300 | 0.949 | 1.000 | 0.927 | 0.962 |
| gpt-5-nano-low-reasoning | 661 | 38 | 5 | 294 | 0.957 | 0.992 | 0.946 | 0.968 |
| gpt-4.1-nano | 649 | 41 | 22 | 268 | 0.936 | 0.967 | 0.941 | 0.954 |
| gpt-5-nano | 667 | 33 | 4 | 296 | 0.963 | 0.994 | 0.953 | 0.973 |


## Token Usage and Costs

| Model Name | Input Tokens | Input Tokens Cached | Output Tokens | Output Tokens Reasoning | Total Tokens | Cost ($) |
|------------|--------------|---------------------|---------------|-------------------------|--------------|----------|
| gpt-5.2 | 4,733,982 | 1,227,008 | 130,335 | 0 | 4,864,317 | 8.18 |
| gpt-oss-120b | 4,797,099 | 1,476,096 | 361,949 | 210,287 | 5,159,048 | 0.83 |
| gpt-5-nano-low-reasoning | 4,733,949 | 1,329,152 | 317,750 | 196,352 | 5,051,699 | 0.31 |
| gpt-4.1-nano | 4,734,761 | 1,280 | 327,815 | 0 | 5,062,576 | 0.60 |
| gpt-5-nano | 4,734,330 | 1,239,424 | 1,288,585 | 1,166,016 | 6,022,915 | 0.70 |