import matplotlib.pyplot as plt
import numpy as np

# -----------------------------
# Example data (replace with yours)
# -----------------------------
datasheets = [
    "RM0041",
    "RM0090",
    "RM0091",
    "RM0360",
    "RM0490",
]

reference_manual_tokens = np.array([3140952, 7585239, 2204534, 1975675, 5619088])
other_input_tokens      = np.array([206976, 405636, 210672, 168168, 316932])
output_tokens           = np.array([61500,139883, 72773, 66294, 116890])

# -----------------------------
# Token pricing (USD per 1M tokens)
# -----------------------------
INPUT_COST_PER_1M  = 2.50
OUTPUT_COST_PER_1M = 10.00

# -----------------------------
# Cost calculation
# -----------------------------
input_tokens = reference_manual_tokens + other_input_tokens

input_cost = input_tokens / 1_000_000 * INPUT_COST_PER_1M
output_cost = output_tokens / 1_000_000 * OUTPUT_COST_PER_1M

total_tokens = input_tokens + output_tokens

# -----------------------------
# Plot
# -----------------------------
x = np.arange(len(datasheets))
width = 0.6

fig, ax = plt.subplots(figsize=(8, 4.5))

LIGHT_BLUE  = "#c6dbef"  # reference manual input
LIGHT_GREEN = "#c7e9c0"  # other input
LIGHT_ORANGE = "#fde0c5" # output

MID_BLUE   = "#9ecae1"  # reference manual input
MID_GREEN = "#a1d99b"  # other input
MID_ORANGE = "#fdd0a2" # output

ax.bar(x, reference_manual_tokens, width, color = MID_BLUE, hatch="xx", label="Reference manual input")
ax.bar(x, other_input_tokens, width, bottom=reference_manual_tokens, color = MID_GREEN, label="Other input")
ax.bar(x, output_tokens, width, bottom=reference_manual_tokens + other_input_tokens, color = MID_ORANGE, hatch="////", label="Output")

# -----------------------------
# Add input/output cost labels
# -----------------------------
for i in range(len(datasheets)):
    ax.text(
        x[i],
        total_tokens[i] * 1.02,
        f"\\${input_cost[i]:.2f} / \\${output_cost[i]:.2f}",
        ha="center",
        va="bottom",
        fontsize=9,
        fontweight="bold",
    )

# -----------------------------
# Formatting
# -----------------------------
ax.set_ylabel("Tokens")
ax.set_xlabel("Datasheet")
ax.set_xticks(x)
ax.set_xticklabels(datasheets, rotation=20, ha="right")
ax.legend(frameon=False)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

ax.set_ylim(0, total_tokens.max() * 1.18)

plt.tight_layout()

# -----------------------------
# Save
# -----------------------------
plt.savefig("generator_token_breakdown.pdf")
plt.savefig("generator_token_breakdown.png", dpi=300)
plt.show()
