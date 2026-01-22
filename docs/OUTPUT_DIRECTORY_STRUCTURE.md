# Output Directory Structure

This document summarizes the output files created by scripts `s0` through `s5`,
and what each file contains.

## s0_run_full_analysis

`s0_run_full_analysis.py` does not write its own files directly. It orchestrates
other steps and creates directories for their outputs:

- `s1a_generator.run_generator(...)` (see s1a)
- `s2_coverage_improver.run_coverage_improver(...)` (see s2)
- `scripts.s2_compare_agent_output_with_svd` (per-SVD diff CSVs)
- `s5_analyzer.run_analyzer(...)` (analyzer JSON + usage)
- `scripts.s4_generate_diff_table` (diff tables in CSV)
- `scripts.s5_compare_diff_with_verified_output` (verified diff CSVs)

## s1a_generator

Outputs under the provided `agent_output_dir`:

- `info/summary.txt`: Context retrieval parameters and model name.
- `info/usage.csv`: Per-register token usage (input/cached/output/reasoning/total).
- `info/reasoning.txt`: Reasoning text per register.
- `{peripheral}_{register}` files: JSON output for each register.

## s1b_generator_dependencies

Legacy generator flow (not used by `s0` directly), with outputs similar to s1a:

- `info/summary.txt`: Context retrieval parameters and model name.
- `info/usage.csv`: Per-register token usage.
- `info/reasoning.txt`: Reasoning text per register.
- `{peripheral}_{register}` files: JSON output for each register.

## s2_coverage_improver

Outputs under the provided `output_dir` (e.g., `agent_output_dir/coverage_improver`):

- `coverage_improver_output.json`: `CoverageImproverOutput` with updated context parameters and the stop flag.
- `coverage_info.json`: Coverage summary (peripheral/register/field coverage and diffs) that the Coverage Improver is aiming to improve.
- `reasoning.txt`: Reasoning text (if present).
- `usage.csv`: One row per run with token usage.

## s3_query_rewriter

Outputs under `aagent_output_dir/query_rewrite/`:

- `query_rewrite.txt`: Appends rewritten query output per register.
- `usage.csv`: Token usage per rewritten query.

## s4_validator

Outputs under the provided `output_dir` (via `ResultSaver`):

- `classification.csv`: Per-invariant classification as T/F rows with confidence.
- `output.txt`: Full model output text per invariant/
- `usage.csv`: Token usage per invariant.

## s4a_validator_optimization

Outputs under the provided `output_dir` (via `ResultSaver`):

- `validator_output_{model}_rm0041.csv`: Per-field judgement rows with confidence.
- `validator_reasoning_{model}_rm0041.txt`: Full model output text per test row.
- `validator_usage_{model}_rm0041.csv`: Token usage per test row.
- `validator_accuracy_{model}_rm0041.csv`: Aggregate accuracy/precision/recall/F1.

## s5_analyzer

Outputs under the provided `analyzer_output_dir`:

- `usage.csv`: Token usage for each analyzer run.
- `{svd_file_name}`: JSON `ValidBugsList` with `bugs: [row_ids]`.
