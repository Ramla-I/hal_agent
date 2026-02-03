import csv
import json
import sys
from pathlib import Path

# Add parent directory to path to import models
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.models import model_costs

# This function reads accuracy and usage CSV files for each model (in subdirectories of the specified results directory),
# aggregates the results, and writes a markdown summary (output file "summary.md" in the results directory).
# It expects per-model subfolders, each containing accuracy and usage results files,
# and compiles these into both table and summary formats for easy comparison and reporting.
def summarize_results(results_dir="stm-rm0041/experiments/batch_sizes_embeddings", halve_vector_store_time: bool = False):
    """
    Summarize prompt optimization results into a markdown file.
    
    Args:
        results_dir: Path to the prompt_optimization_results directory
        halve_vector_store_time: If True, halve vector_store_search total_time
    """
    script_dir = Path(__file__).resolve().parent
    results_path = Path(results_dir)
    if not results_path.is_absolute():
        results_path = script_dir / results_path
    output_path = results_path / "summary.md"
    
    # Collect accuracy data
    accuracy_data = []
    usage_data = []
    timing_data = []
    
    # Find all model directories
    model_dirs = [d for d in results_path.iterdir() if d.is_dir()]
    
    for model_dir in model_dirs:
        model_name = model_dir.name
        
        # Read accuracy file
        accuracy_files = list(model_dir.glob("validator_accuracy_*.csv"))
        if accuracy_files:
            with open(accuracy_files[0], 'r') as f:
                reader = csv.DictReader(f)
                # Strip whitespace from column names
                if reader.fieldnames:
                    reader.fieldnames = [col.strip() for col in reader.fieldnames]
                for row in reader:
                    # Replace model_name with the folder name (full model name)
                    row['model_name'] = model_name
                    accuracy_data.append(row)
        
        # Read usage file
        usage_files = list(model_dir.glob("validator_usage_*.csv"))
        if usage_files:
            # Initialize sums
            total_input = 0
            total_cached = 0
            total_output = 0
            total_reasoning = 0
            total_tokens = 0
            
            with open(usage_files[0], 'r') as f:
                reader = csv.DictReader(f)
                # Check column names
                if not reader.fieldnames:
                    print(f"Warning: {usage_files[0]} appears to be empty or has no headers")
                    continue
                
                # Strip whitespace from column names
                reader.fieldnames = [col.strip() for col in reader.fieldnames]
                
                for row in reader:
                    input_tokens = int(row['input_tokens'])
                    cached_tokens = int(row['cached_tokens'])
                    output_tokens = int(row['output_tokens'])
                    reasoning_tokens = int(row.get('reasoning_tokens', 0))
                    total_row_tokens = int(row['total_tokens'])
                    
                    # Validate: total_tokens should equal input + output
                    expected_total = input_tokens + output_tokens
                    if total_row_tokens != expected_total:
                        print(f"Warning: For {model_name}, row has total_tokens={total_row_tokens} but input+output={expected_total}")
                    
                    total_input += input_tokens
                    total_cached += cached_tokens
                    total_output += output_tokens
                    total_reasoning += reasoning_tokens
                    total_tokens += total_row_tokens
            
            # Validate total
            expected_total = total_input + total_output
            if total_tokens != expected_total:
                print(f"Warning: For {model_name}, total_tokens={total_tokens} but sum(input+output)={expected_total}")
            
            # Calculate cost
            # Map model name to cost key (handle variations like gpt-5-nano-low-reasoning -> gpt-5-nano)
            cost_key = model_name
            if model_name not in model_costs:
                # Try to find a matching cost entry
                if "gpt-5-nano" in model_name:
                    cost_key = "gpt-5-nano"
                elif "gpt-4.1-nano" in model_name:
                    cost_key = "gpt-4.1-nano"
                elif "gpt-5.2" in model_name:
                    cost_key = "gpt-5.2"
                elif "gpt-oss-120b" in model_name:
                    cost_key = "gpt-oss-120b"
                else:
                    print(f"Warning: No cost data found for {model_name}, using default costs")
                    cost_key = None
            
            if cost_key and cost_key in model_costs:
                costs = model_costs[cost_key]
                input_cost_pm = costs["input_cost_pm"]
                input_cached_cost_pm = costs["input_cached_cost_pm"]
                output_cost_pm = costs["output_cost_pm"]
                # Use output_reasoning_cost_pm if available, otherwise use output_cost_pm
                output_reasoning_cost_pm = costs.get("output_reasoning_cost_pm", output_cost_pm)
                
                # Calculate cost: (input_cost_pm * (input - input_cached)) + input_cached_cost_pm * input_cached + output_cost_pm * output
                # Formula from user: (input_cost_pm * (input- input_cached))+ input_cached_cost_pm * input_cached + output_cost_pm * output
                # Note: output includes reasoning tokens. If output_reasoning_cost_pm exists, use it for reasoning tokens
                if "output_reasoning_cost_pm" in costs:
                    cost = (
                        (input_cost_pm / 1_000_000) * (total_input - total_cached) +
                        (input_cached_cost_pm / 1_000_000) * total_cached +
                        (output_cost_pm / 1_000_000) * (total_output - total_reasoning) +
                        (output_reasoning_cost_pm / 1_000_000) * total_reasoning
                    )
                else:
                    # All output tokens use the same cost
                    cost = (
                        (input_cost_pm / 1_000_000) * (total_input - total_cached) +
                        (input_cached_cost_pm / 1_000_000) * total_cached +
                        (output_cost_pm / 1_000_000) * total_output
                    )
            else:
                cost = 0.0
                print(f"Warning: Could not calculate cost for {model_name}")
            
            usage_data.append({
                'model_name': model_name,
                'input_tokens': total_input,
                'input_tokens_cached': total_cached,
                'output_tokens': total_output,
                'output_tokens_reasoning': total_reasoning,
                'total_tokens': total_tokens,
                'cost': cost
            })

        # Read timing file
        timing_files = list(model_dir.glob("timing_stats.json"))
        if timing_files:
            with open(timing_files[0], 'r') as f:
                timing_stats = json.load(f)
            for operation, stats in timing_stats.items():
                total_time = stats.get('total_time', '')
                if halve_vector_store_time and operation == "vector_store_search":
                    try:
                        total_time = float(total_time) / 2
                    except (TypeError, ValueError):
                        pass
                timing_data.append({
                    'model_name': model_name,
                    'operation': operation,
                    'count': stats.get('count', ''),
                    'total_time': total_time,
                    'avg_time': stats.get('avg_time', ''),
                    'min_time': stats.get('min_time', ''),
                    'p25_time': stats.get('p25_time', ''),
                    'median_time': stats.get('median_time', ''),
                    'p75_time': stats.get('p75_time', ''),
                    'p90_time': stats.get('p90_time', ''),
                    'p95_time': stats.get('p95_time', ''),
                    'p99_time': stats.get('p99_time', ''),
                    'max_time': stats.get('max_time', '')
                })
    
    # Generate markdown
    markdown_lines = ["# Prompt Optimization Results Summary\n"]
    
    # Accuracy table
    markdown_lines.append("## Accuracy Metrics\n")
    markdown_lines.append("| Model Name | True Positives | False Negatives | False Positives | True Negatives | Accuracy | Precision | Recall | F1 Score |")
    markdown_lines.append("|------------|----------------|-----------------|-----------------|----------------|----------|-----------|--------|----------|")
    
    for row in accuracy_data:
        model_name = row.get('model_name', '').strip()
        tp = row.get('true_positives', '').strip()
        fn = row.get('false_negatives', '').strip()
        fp = row.get('false_positives', '').strip()
        tn = row.get('true_negatives', '').strip()
        # Round accuracy metrics to 3 decimal places
        try:
            accuracy = f"{float(row.get('accuracy', 0)):.3f}"
            precision = f"{float(row.get('precision', 0)):.3f}"
            recall = f"{float(row.get('recall', 0)):.3f}"
            f1 = f"{float(row.get('f1_score', 0)):.3f}"
        except (ValueError, TypeError):
            accuracy = row.get('accuracy', '').strip()
            precision = row.get('precision', '').strip()
            recall = row.get('recall', '').strip()
            f1 = row.get('f1_score', '').strip()
        markdown_lines.append(f"| {model_name} | {tp} | {fn} | {fp} | {tn} | {accuracy} | {precision} | {recall} | {f1} |")
    
    markdown_lines.append("\n")
    
    # Usage table
    markdown_lines.append("## Token Usage and Costs\n")
    markdown_lines.append("| Model Name | Input Tokens | Input Tokens Cached | Output Tokens | Output Tokens Reasoning | Total Tokens | Cost ($) |")
    markdown_lines.append("|------------|--------------|---------------------|---------------|-------------------------|--------------|----------|")
    
    for row in usage_data:
        model_name = row['model_name']
        input_tokens = row['input_tokens']
        input_cached = row['input_tokens_cached']
        output_tokens = row['output_tokens']
        output_reasoning = row['output_tokens_reasoning']
        total_tokens = row['total_tokens']
        cost = row['cost']
        
        # Format cost to 2 decimal places (cents)
        cost_str = f"{cost:.2f}"
        
        markdown_lines.append(f"| {model_name} | {input_tokens:,} | {input_cached:,} | {output_tokens:,} | {output_reasoning:,} | {total_tokens:,} | {cost_str} |")

    markdown_lines.append("\n")

    # Timing table
    markdown_lines.append("## Timing Metrics\n")
    markdown_lines.append("| Model Name | Operation | Count | Total (s) | Avg (s) | Min (s) | P25 (s) | Median (s) | P75 (s) | P90 (s) | P95 (s) | P99 (s) | Max (s) |")
    markdown_lines.append("|------------|-----------|-------|-----------|---------|---------|---------|------------|---------|---------|---------|---------|---------|")

    def format_time(value):
        if value == "" or value is None:
            return ""
        try:
            return f"{float(value):.3f}"
        except (ValueError, TypeError):
            return str(value).strip()

    for row in timing_data:
        markdown_lines.append(
            "| {model_name} | {operation} | {count} | {total_time} | {avg_time} | {min_time} | {p25_time} | {median_time} | {p75_time} | {p90_time} | {p95_time} | {p99_time} | {max_time} |".format(
                model_name=row['model_name'],
                operation=row['operation'],
                count=row['count'],
                total_time=format_time(row['total_time']),
                avg_time=format_time(row['avg_time']),
                min_time=format_time(row['min_time']),
                p25_time=format_time(row['p25_time']),
                median_time=format_time(row['median_time']),
                p75_time=format_time(row['p75_time']),
                p90_time=format_time(row['p90_time']),
                p95_time=format_time(row['p95_time']),
                p99_time=format_time(row['p99_time']),
                max_time=format_time(row['max_time'])
            )
        )
    
    # Write markdown file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write('\n'.join(markdown_lines))
    
    print(f"Summary written to {output_path}")
    
    # Write accuracy CSV file
    accuracy_csv_path = output_path.parent / "summary_accuracy.csv"
    if accuracy_data:
        with open(accuracy_csv_path, 'w', newline='') as f:
            fieldnames = ['model_name', 'true_positives', 'false_negatives', 'false_positives', 
                         'true_negatives', 'accuracy', 'precision', 'recall', 'f1_score']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in accuracy_data:
                # Clean up the row data and round accuracy metrics to 3 decimal places
                cleaned_row = {}
                for k, v in row.items():
                    k_clean = k.strip()
                    if k_clean in fieldnames:
                        if k_clean in ['accuracy', 'precision', 'recall', 'f1_score']:
                            try:
                                cleaned_row[k_clean] = f"{float(v):.3f}"
                            except (ValueError, TypeError):
                                cleaned_row[k_clean] = v.strip() if isinstance(v, str) else v
                        else:
                            cleaned_row[k_clean] = v.strip() if isinstance(v, str) else v
                writer.writerow(cleaned_row)
        print(f"Accuracy CSV written to {accuracy_csv_path}")
    
    # Write usage CSV file
    usage_csv_path = output_path.parent / "summary_usage.csv"
    if usage_data:
        with open(usage_csv_path, 'w', newline='') as f:
            fieldnames = ['model_name', 'input_tokens', 'input_tokens_cached', 'output_tokens', 
                         'output_tokens_reasoning', 'total_tokens', 'cost']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in usage_data:
                # Round cost to 2 decimal places (cents) and format as string to preserve trailing zeros
                row_copy = row.copy()
                row_copy['cost'] = f"{row['cost']:.2f}"
                writer.writerow(row_copy)
        print(f"Usage CSV written to {usage_csv_path}")

    # Write timing CSV file
    timing_csv_path = output_path.parent / "summary_timing.csv"
    if timing_data:
        with open(timing_csv_path, 'w', newline='') as f:
            fieldnames = [
                'model_name', 'operation', 'count', 'total_time', 'avg_time', 'min_time',
                'p25_time', 'median_time', 'p75_time', 'p90_time', 'p95_time', 'p99_time', 'max_time'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in timing_data:
                row_copy = row.copy()
                for key in ['total_time', 'avg_time', 'min_time', 'p25_time', 'median_time', 'p75_time', 'p90_time', 'p95_time', 'p99_time', 'max_time']:
                    if row_copy.get(key, "") != "":
                        try:
                            row_copy[key] = f"{float(row_copy[key]):.6f}"
                        except (ValueError, TypeError):
                            pass
                writer.writerow(row_copy)
        print(f"Timing CSV written to {timing_csv_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Summarize optimization results into markdown/CSV files.")
    parser.add_argument(
        "--results-dir",
        default="stm-rm0041/experiments/batch_sizes_embeddings",
        help="Path to the results directory",
    )
    parser.add_argument(
        "--halve-file-search-time",
        action="store_true",
        help="Halve vector_store_search total time (for legacy double-counted runs)",
    )
    args = parser.parse_args()

    summarize_results(args.results_dir, halve_vector_store_time=args.halve_file_search_time)

