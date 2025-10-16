import csv
import argparse

def parse_and_calculate(input_csv_path, output_csv_path, input_cost_per_million, output_cost_per_million):
    rows = []
    total_input = 0
    total_output = 0
    total_total = 0

    # Read input CSV
    with open(input_csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        header = reader.fieldnames if reader.fieldnames else []
        # We'll only process the required columns
        for row in reader:
            # Defensive: skip rows with missing data
            try:
                input_tokens = int(float(row['input_tokens_sum']))
                output_tokens = int(float(row['output_tokens_sum']))
                total_tokens = int(float(row['total_tokens_sum']))
                iteration = row['iteration']
            except Exception as e:
                continue

            # Calculate cost for this row
            cost = (input_cost_per_million / 1_000_000) * input_tokens + (output_cost_per_million / 1_000_000) * output_tokens

            rows.append({
                "iteration": iteration,
                "input_tokens_sum": input_tokens,
                "output_tokens_sum": output_tokens,
                "total_tokens_sum": total_tokens,
                "total_cost": cost
            })
            total_input += input_tokens
            total_output += output_tokens
            total_total += total_tokens

    # Add totals row
    total_cost = (input_cost_per_million / 1_000_000) * total_input + (output_cost_per_million / 1_000_000) * total_output
    rows.append({
        "iteration": "TOTAL",
        "input_tokens_sum": total_input,
        "output_tokens_sum": total_output,
        "total_tokens_sum": total_total,
        "total_cost": total_cost
    })

    # Write output CSV
    with open(output_csv_path, "w", newline='') as csvfile:
        fieldnames = ["iteration", "input_tokens_sum", "output_tokens_sum", "total_tokens_sum", "total_cost"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            # Round cost to e.g. 6 decimals
            row_out = dict(row)
            row_out['total_cost'] = f"{row['total_cost']:.2f}"
            writer.writerow(row_out)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize LLM usage table, adding total and cost columns.")
    parser.add_argument("usage_stats_csv", help="CSV input with usage statistics")
    parser.add_argument("output_csv", help="Where to write output (summed) CSV")
    parser.add_argument("--ip_cost_pm", type=float, required=True, help="Input tokens cost per million tokens")
    parser.add_argument("--op_cost_pm", type=float, required=True, help="Output tokens cost per million tokens")
    args = parser.parse_args()

    parse_and_calculate(args.usage_stats_csv, args.output_csv, args.ip_cost_pm, args.op_cost_pm)
