import csv
from statistics import median, mean
import os

def get_token_statistics(usage_csv_path):
    input_tokens_list = []
    output_tokens_list = []
    total_tokens_list = []

    with open(usage_csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                input_tokens = int(row['input_tokens'])
                output_tokens = int(row['output_tokens'])
                total_tokens = int(row.get('total_tokens', input_tokens + output_tokens))
            except Exception:
                continue
            input_tokens_list.append(input_tokens)
            output_tokens_list.append(output_tokens)
            total_tokens_list.append(total_tokens)

    def percentile(data, percent):
        if not data:
            return None
        k = (len(data)-1) * percent/100
        f = int(k)
        c = k - f
        data_sorted = sorted(data)
        if f+1 < len(data):
            return data_sorted[f] + (data_sorted[f+1] - data_sorted[f]) * c
        else:
            return data_sorted[f]

    stats = {
        'input_tokens_sum': sum(input_tokens_list),
        'output_tokens_sum': sum(output_tokens_list),
        'total_tokens_sum': sum(total_tokens_list),
        'input_tokens': {
            'min': min(input_tokens_list) if input_tokens_list else None,
            '25': percentile(input_tokens_list, 25),
            'median': median(input_tokens_list) if input_tokens_list else None,
            '75': percentile(input_tokens_list, 75),
            'max': max(input_tokens_list) if input_tokens_list else None,
            'avg': mean(input_tokens_list) if input_tokens_list else None,
        },
        'output_tokens': {
            'min': min(output_tokens_list) if output_tokens_list else None,
            '25': percentile(output_tokens_list, 25),
            'median': median(output_tokens_list) if output_tokens_list else None,
            '75': percentile(output_tokens_list, 75),
            'max': max(output_tokens_list) if output_tokens_list else None,
            'avg': mean(output_tokens_list) if output_tokens_list else None,
        },
        'total_tokens': {
            'min': min(total_tokens_list) if total_tokens_list else None,
            '25': percentile(total_tokens_list, 25),
            'median': median(total_tokens_list) if total_tokens_list else None,
            '75': percentile(total_tokens_list, 75),
            'max': max(total_tokens_list) if total_tokens_list else None,
            'avg': mean(total_tokens_list) if total_tokens_list else None,
        }
    }
    return stats

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Get LLM usage statistics for a device.")
    parser.add_argument('usage_csv_path', help='Path to the finder1 usage CSV file')
    parser.add_argument('output_dir', help='Path to the output directory')
    parser.add_argument('--judge', action='store_true', help='Whether to also add judge iteration rows to the output CSV')
    args = parser.parse_args()

    usage_csv_path = args.usage_csv_path
    output_dir = args.output_dir
    stats = get_token_statistics(usage_csv_path)

    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    csvfile = open(os.path.join(output_dir, "usage_stats.csv"), 'w', newline='')
    writer = csv.writer(csvfile)
    writer.writerow(['iteration','input_tokens_sum', 'output_tokens_sum', 'total_tokens_sum', 'input_tokens_min', 'input_tokens_25', 'input_tokens_median', 'input_tokens_75', 'input_tokens_max', 'input_tokens_avg', 'output_tokens_min', 'output_tokens_25', 'output_tokens_median', 'output_tokens_75', 'output_tokens_max', 'output_tokens_avg', 'total_tokens_min', 'total_tokens_25', 'total_tokens_median', 'total_tokens_75', 'total_tokens_max', 'total_tokens_avg'])
    writer.writerow(["finder1", stats['input_tokens_sum'], stats['output_tokens_sum'], stats['total_tokens_sum'], stats['input_tokens']['min'], stats['input_tokens']['25'], stats['input_tokens']['median'], stats['input_tokens']['75'], stats['input_tokens']['max'], stats['input_tokens']['avg'], stats['output_tokens']['min'], stats['output_tokens']['25'], stats['output_tokens']['median'], stats['output_tokens']['75'], stats['output_tokens']['max'], stats['output_tokens']['avg'], stats['total_tokens']['min'], stats['total_tokens']['25'], stats['total_tokens']['median'], stats['total_tokens']['75'], stats['total_tokens']['max'], stats['total_tokens']['avg']])

    print(args.judge)
    if args.judge:
        judge_usage_csv_path = os.path.join(os.path.dirname(usage_csv_path), "judge_iteration", "usage_judge.csv")
        stats = get_token_statistics(judge_usage_csv_path)
        writer.writerow(["judge", stats['input_tokens_sum'], stats['output_tokens_sum'], stats['total_tokens_sum'], stats['input_tokens']['min'], stats['input_tokens']['25'], stats['input_tokens']['median'], stats['input_tokens']['75'], stats['input_tokens']['max'], stats['input_tokens']['avg'], stats['output_tokens']['min'], stats['output_tokens']['25'], stats['output_tokens']['median'], stats['output_tokens']['75'], stats['output_tokens']['max'], stats['output_tokens']['avg'], stats['total_tokens']['min'], stats['total_tokens']['25'], stats['total_tokens']['median'], stats['total_tokens']['75'], stats['total_tokens']['max'], stats['total_tokens']['avg']])

        finder2_usage_csv_path = os.path.join(os.path.dirname(usage_csv_path), "judge_iteration", "usage_info.csv")
        stats = get_token_statistics(finder2_usage_csv_path)
        writer.writerow(["finder2", stats['input_tokens_sum'], stats['output_tokens_sum'], stats['total_tokens_sum'], stats['input_tokens']['min'], stats['input_tokens']['25'], stats['input_tokens']['median'], stats['input_tokens']['75'], stats['input_tokens']['max'], stats['input_tokens']['avg'], stats['output_tokens']['min'], stats['output_tokens']['25'], stats['output_tokens']['median'], stats['output_tokens']['75'], stats['output_tokens']['max'], stats['output_tokens']['avg'], stats['total_tokens']['min'], stats['total_tokens']['25'], stats['total_tokens']['median'], stats['total_tokens']['75'], stats['total_tokens']['max'], stats['total_tokens']['avg']])

if __name__ == "__main__":
    main()
