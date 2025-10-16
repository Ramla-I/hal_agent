import matplotlib.pyplot as plt
import csv
import sys
import os
from collections import defaultdict
INPUT_TOKEN_COST_PM = 2.5
OUTPUT_TOKEN_COST_PM = 10.0

def extract_stats_from_file(file_path):
    stats = {}
    with open(file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            iteration = row["iteration"]
            if iteration.lower() in ["finder1", "judge", "finder2"]:
                # Get medians
                try:
                    input_med = float(row["input_tokens_median"])
                    output_med = float(row["output_tokens_median"])
                    input_25 = float(row.get("input_tokens_25", 0))
                    input_75 = float(row.get("input_tokens_75", 0))
                    output_25 = float(row.get("output_tokens_25", 0))
                    output_75 = float(row.get("output_tokens_75", 0))
                except KeyError:
                    # If header is not present in file, skip
                    continue
                stats[iteration.lower()] = {
                    "input_tokens_median": input_med,
                    "output_tokens_median": output_med,
                    "input_tokens_25": input_25,
                    "input_tokens_75": input_75,
                    "output_tokens_25": output_25,
                    "output_tokens_75": output_75,
                }
    return stats

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_usage_per_reg_graph.py usage_stats1.csv usage_stats2.csv ...")
        sys.exit(1)

    files = sys.argv[1:]
    all_stats = []
    # If you want to hardcode labels, set them here; leave empty to derive from paths
    x_labels = ["RM0041", "RM0090", "RM0091"]
    labels_from_files = []

    # Gather stats from all files
    for file_path in files:
        stats = extract_stats_from_file(file_path)
        all_stats.append(stats)
        # Use folder name above file (or filename) for x-label
        base_label = os.path.basename(os.path.dirname(file_path))
        if not base_label or base_label == "":
            base_label = os.path.basename(file_path)
        labels_from_files.append(base_label)

    # Normalize x_labels to match the number of files
    if not x_labels or len(x_labels) != len(all_stats):
        x_labels = labels_from_files

    # Map display labels to underlying iteration keys in the CSV
    column_mappings = [
        ("Generator Iter1", "finder1"),
        ("Judge", "judge"),
        ("Generator Iter2", "finder2"),
    ]
    columns = [disp for disp, _ in column_mappings]
    bar_width = 0.2
    x = range(len(files))

    index_array = [i for i in range(len(all_stats))]

    # Build datasets for input and output separately
    input_data = {}
    output_data = {}
    for disp_label, data_key in column_mappings:
        in_meds = []
        in_err_low = []
        in_err_up = []
        out_meds = []
        out_err_low = []
        out_err_up = []
        for stats in all_stats:
            row = stats.get(data_key, {})
            in_med = float(row.get("input_tokens_median", 0))
            in_p25 = float(row.get("input_tokens_25", 0))
            in_p75 = float(row.get("input_tokens_75", 0))
            out_med = float(row.get("output_tokens_median", 0))
            out_p25 = float(row.get("output_tokens_25", 0))
            out_p75 = float(row.get("output_tokens_75", 0))
            in_meds.append(in_med)
            in_err_low.append(max(in_med - in_p25, 0))
            in_err_up.append(max(in_p75 - in_med, 0))
            out_meds.append(out_med)
            out_err_low.append(max(out_med - out_p25, 0))
            out_err_up.append(max(out_p75 - out_med, 0))
        input_data[disp_label] = (in_meds, [in_err_low, in_err_up])
        output_data[disp_label] = (out_meds, [out_err_low, out_err_up])

    # Define hatch patterns per role/column
    patterns = ['/', '\\', 'x']  # one per role in columns

    # Figure 1: Input tokens
    fig_in, ax_in = plt.subplots(figsize=(10, 6))
    for col_idx, col in enumerate(columns):
        x_pos = [i + (col_idx - 1) * bar_width for i in index_array]
        in_meds, in_err = input_data[col]
        ax_in.bar(x_pos, in_meds, width=bar_width, color=f"C{col_idx}", edgecolor='k', label=col, hatch=patterns[col_idx])
        ax_in.errorbar(x_pos, in_meds, yerr=in_err, fmt='none', ecolor='black', capsize=3)
        # Add value labels offset to the side and above error bars to avoid overlap
        for idx, (xp, val) in enumerate(zip(x_pos, in_meds)):
            label = f"${float(val) * INPUT_TOKEN_COST_PM / 1000000:.2f}"
            y_pad = max(1, 0.01 * max(1, val))
            ax_in.text(xp + bar_width * 0.12, val + y_pad, label, ha='left', va='bottom', fontsize=8, rotation=90, weight='bold')
            
            # Add 75th percentile labels above error bars
            if idx < len(in_err[1]):
                p75_val = val + in_err[1][idx]
                p75_label = f"${float(p75_val) * INPUT_TOKEN_COST_PM / 1000000:.2f}"
                ax_in.text(xp + bar_width * 0.12, p75_val + y_pad, p75_label, ha='left', va='bottom', fontsize=7, rotation=90, color='black', weight='bold')
            
            # Add 25th percentile labels below error bars
            if idx < len(in_err[0]):
                p25_val = val - in_err[0][idx]
                p25_label = f"${float(p25_val) * INPUT_TOKEN_COST_PM / 1000000:.2f}"
                ax_in.text(xp + bar_width * 0.12, p25_val - y_pad, p25_label, ha='left', va='top', fontsize=7, rotation=90, color='white', weight='bold')
    ax_in.set_xticks([i for i in index_array])
    ax_in.set_xticklabels(x_labels[:len(index_array)], rotation=45)
    ax_in.set_ylabel("Input tokens (median)")
    ax_in.set_xlabel("Datasheet")
    # Increase y-axis limits to accommodate labels
    ax_in.set_ylim(bottom=0, top=ax_in.get_ylim()[1] * 1.3)
    from matplotlib.patches import Patch
    input_legend = [Patch(facecolor=f"C{i}", edgecolor='k', label=columns[i], hatch=patterns[i]) for i in range(len(columns))]
    ax_in.legend(handles=input_legend, loc="upper left")
    ax_in.set_title("Median Input Tokens per Register Across Datasheet")
    fig_in.tight_layout()

    # Figure 2: Output tokens
    fig_out, ax_out = plt.subplots(figsize=(10, 6))
    for col_idx, col in enumerate(columns):
        x_pos = [i + (col_idx - 1) * bar_width for i in index_array]
        out_meds, out_err = output_data[col]
        ax_out.bar(x_pos, out_meds, width=bar_width, color=f"C{col_idx}", edgecolor='k', label=col, hatch=patterns[col_idx])
        ax_out.errorbar(x_pos, out_meds, yerr=out_err, fmt='none', ecolor='black', capsize=3)
        # Add value labels offset to the side and above error bars to avoid overlap
        for idx, (xp, val) in enumerate(zip(x_pos, out_meds)):
            label = f"${float(val) * OUTPUT_TOKEN_COST_PM / 1000000:.2f}"
            y_pad = max(1, 0.01 * max(1, val))
            ax_out.text(xp + bar_width * 0.12, val + y_pad, label, ha='left', va='bottom', fontsize=8, rotation=90, weight='bold')
            
            # Add 75th percentile labels above error bars
            if idx < len(out_err[1]):
                p75_val = val + out_err[1][idx]
                p75_label = f"${float(p75_val) * OUTPUT_TOKEN_COST_PM / 1000000:.2f}"
                ax_out.text(xp + bar_width * 0.12, p75_val + y_pad, p75_label, ha='left', va='bottom', fontsize=7, rotation=90, color='black', weight='bold')
            
            # Add 25th percentile labels below error bars
            if idx < len(out_err[0]):
                p25_val = val - out_err[0][idx]
                p25_label = f"${float(p25_val) * OUTPUT_TOKEN_COST_PM / 1000000:.2f}"
                ax_out.text(xp + bar_width * 0.12, p25_val - y_pad, p25_label, ha='left', va='top', fontsize=7, rotation=90, color='white', weight='bold')
    ax_out.set_xticks([i for i in index_array])
    ax_out.set_xticklabels(x_labels[:len(index_array)], rotation=45)
    ax_out.set_ylabel("Output tokens (median)")
    ax_out.set_xlabel("Datasheet")
    # Increase y-axis limits to accommodate labels
    ax_out.set_ylim(bottom=0, top=ax_out.get_ylim()[1] * 1.3)
    output_legend = [Patch(facecolor=f"C{i}", edgecolor='k', label=columns[i], hatch=patterns[i]) for i in range(len(columns))]
    ax_out.legend(handles=output_legend, loc="upper left")
    ax_out.set_title("Median Output Tokens per Register Across Datasheets")
    fig_out.tight_layout()

    plt.show()

if __name__ == "__main__":
    main()
