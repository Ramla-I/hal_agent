import csv
import argparse
import os

FINDER1_PROMPT_TOKENS = 924
JUDGE_FINDER1_PROMPT_TOKENS = 414
FINDER2_PROMPT_TOKENS = 967

def parse_and_calculate(input_csv_path, output_csv_path, input_cost_per_million, output_cost_per_million):
    rows = []
    total_input = 0
    total_output = 0
    total_total = 0
    total_num_prompts = 0
    total_input_tokens_prompt = 0
    total_datasheet_tokens = 0
    total_feedback_tokens = 0

    # Read input CSV
    with open(input_csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        header = reader.fieldnames if reader.fieldnames else []

        finder1_output_tokens = 0
        judge_output_tokens = 0
        # We'll only process the required columns
        for row in reader:
            # Defensive: skip rows with missing data
            try:
                input_tokens = int(float(row['input_tokens_sum']))
                output_tokens = int(float(row['output_tokens_sum']))
                total_tokens = int(float(row['total_tokens_sum']))
                iteration = row['iteration']
                num_prompts = int(float(row['num_prompts']))
            except Exception as e:
                continue

            # Calculate cost for this row
            input_cost = (input_cost_per_million / 1_000_000) * input_tokens
            output_cost = (output_cost_per_million / 1_000_000) * output_tokens
            total_cost = input_cost + output_cost

            if iteration == "finder1":
                input_tokens_prompt = FINDER1_PROMPT_TOKENS * num_prompts
                datasheet_tokens = input_tokens - input_tokens_prompt
                finder1_output_tokens = output_tokens
                feedback_tokens = 0
            elif iteration == "judge":
                input_tokens_prompt = JUDGE_FINDER1_PROMPT_TOKENS * num_prompts
                feedback_tokens = finder1_output_tokens
                datasheet_tokens = input_tokens - input_tokens_prompt - feedback_tokens
                judge_output_tokens = output_tokens
            else: #finder2
                input_tokens_prompt = FINDER2_PROMPT_TOKENS * num_prompts
                feedback_tokens = judge_output_tokens + finder1_output_tokens
                datasheet_tokens = input_tokens - input_tokens_prompt - feedback_tokens
                
            rows.append({
                "iteration": iteration,
                "num_prompts": num_prompts,
                "input_tokens_prompt": input_tokens_prompt,
                "datasheet_tokens": datasheet_tokens,
                "feedback_tokens": feedback_tokens,
                "input_tokens_sum": input_tokens,
                "input_cost": input_cost,
                "output_tokens_sum": output_tokens,
                "output_cost": output_cost,
                "total_tokens_sum": total_tokens,
                "total_cost": total_cost,
            })
            total_input += input_tokens
            total_input_tokens_prompt += input_tokens_prompt
            total_datasheet_tokens += datasheet_tokens
            total_feedback_tokens += feedback_tokens
            total_output += output_tokens
            total_total += total_tokens
            total_num_prompts += num_prompts

    # Add totals row
    total_input_cost = (input_cost_per_million / 1_000_000) * total_input
    total_output_cost = (output_cost_per_million / 1_000_000) * total_output
    total_total_cost = total_input_cost + total_output_cost
    rows.append({
        "iteration": "TOTAL",
        "num_prompts": total_num_prompts,
        "input_tokens_prompt": total_input_tokens_prompt,
        "datasheet_tokens": total_datasheet_tokens,
        "feedback_tokens": total_feedback_tokens,
        "input_tokens_sum": total_input,
        "input_cost": total_input_cost,
        "output_tokens_sum": total_output,
        "output_cost": total_output_cost,
        "total_tokens_sum": total_total,
        "total_cost": total_total_cost
    })

    # Write output CSV
    with open(output_csv_path, "w", newline='') as csvfile:
        fieldnames = ["iteration", "num_prompts", "input_tokens_prompt", "datasheet_tokens", "feedback_tokens", "input_tokens_sum", "input_cost", "output_tokens_sum", "output_cost", "total_tokens_sum", "total_cost"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize LLM usage table, adding total and cost columns.")
    parser.add_argument("usage_stats_csv", help="CSV input with usage statistics")
    parser.add_argument("--ip_cost_pm", type=float, required=True, help="Input tokens cost per million tokens")
    parser.add_argument("--op_cost_pm", type=float, required=True, help="Output tokens cost per million tokens")
    args = parser.parse_args()

    # Derive the output CSV path from the input file's directory by removing 'usage_stats.csv' if present
    input_dir = os.path.dirname(os.path.abspath(args.usage_stats_csv))
    output_csv = os.path.join(input_dir, "usage_table.csv")

    parse_and_calculate(args.usage_stats_csv, output_csv, args.ip_cost_pm, args.op_cost_pm)
