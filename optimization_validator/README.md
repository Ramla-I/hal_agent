# OPTIMIZATION VALIDATOR

Tools and results for benchmarking validator accuracy, cost, and latency across
models and batching configurations.

## DIRECTORY STRUCTURE

```
optimization_validator/
|__ README.md
|__ create_test_set.py
|__ summarize_results.py
|__ plot_experiment_scatter.py
|__ plot_experiment_tradeoffs.py
|__ plot_file_search_tokens_vs_chunks.py
|__ run_all_plots.py
|__ validator_optimization.py
|__ stm-rm0041/
    |__ test_set_rm0041.csv
    |__ hold_set_rm0041.csv
    |__ hold_set_results/
        |__ <model>/
            |__ validator_accuracy_*.csv
            |__ validator_output_*.csv
            |__ validator_reasoning_*.txt
            |__ validator_usage_*.csv
        |__ summary.md
        |__ summary_accuracy.csv
        |__ summary_usage.csv
    |__ experiments/
        |__ <experiment_name>/
            |__ <model_run>/
                |__ validator_accuracy_*.csv
                |__ validator_output_*.csv
                |__ validator_reasoning_*.txt
                |__ validator_usage_*.csv
            |__ validator_batch_info_*.csv
                |__ timing_stats.json
            |__ summary.md
            |__ summary_accuracy.csv
            |__ summary_usage.csv
            |__ summary_timing.csv
        |__ time_vs_f1_scatter.png
        |__ time_vs_tokens_f1_filtered.png
        |__ f1_vs_tokens_time_filtered.png
        |__ time_breakdown_bars.png
        |__ token_breakdown_bars.png
        |__ file_search_tokens_vs_chunks.png
```

## SCRIPTS

### `VALIDATOR_OPTIMIZATION.PY`
Runs the validator against a test or hold set with configurable batching and
embedding counts, then writes per-run outputs.

Outputs per model/run folder:
- `validator_accuracy_*.csv`: accuracy metrics (TP/FP/TN/FN, accuracy, precision, recall, F1)
- `validator_output_*.csv`: per-invariant validator decisions
- `validator_reasoning_*.txt`: raw model reasoning text
- `validator_usage_*.csv`: per-call token usage
- `validator_batch_info_*.csv`: per-batch metadata (batch size, context limits)
- `timing_stats.json`: aggregated timing stats from `utils/timing.py`

### `SUMMARIZE_RESULTS.PY`
Aggregates per-run results into a single summary in an experiment directory.
Produces:
- `summary.md`: markdown tables for accuracy, usage/costs, and timing
- `summary_accuracy.csv`
- `summary_usage.csv`
- `summary_timing.csv`

### `CREATE_TEST_SET.PY`
Builds synthetic test sets by perturbing a verified CSV with incorrect values
and/or incorrect names. Useful for controlled accuracy testing.

### `PLOT_EXPERIMENT_SCATTER.PY`
Creates a scatter plot of total time vs F1 score, with point size proportional
to total tokens and labels including API call counts.

### `PLOT_EXPERIMENT_TRADEOFFS.PY`
Generates filtered tradeoff plots (time vs tokens, F1 vs tokens) and stacked
bar charts for time and token breakdowns. Filters are controlled by min F1 and
max time thresholds.

### `PLOT_FILE_SEARCH_TOKENS_VS_CHUNKS.PY`
Builds a bar chart comparing file search tokens per experiment against
the total_peripheral_tokens derived from the test set and mapping CSV.

### `RUN_ALL_PLOTS.PY`
Runs the scatter and tradeoff plotting scripts in one command.

## NOTES

- Experiment results are grouped under `stm-rm0041/experiments/<experiment_name>/`.
- Hold/test datasets live in `stm-rm0041/` and are referenced by the scripts.
