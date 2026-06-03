#!/usr/bin/env python3
"""
Generate cross-manufacturer comparison figures for OpenEvolve retrieval.

Produces two figures:
  1. Complete Accuracy & Coverage grouped by target datasheet
  2. Token Usage vs Complete Accuracy scatter plot

Also prints summary tables to stdout.

Usage:
    source .venv/bin/activate && python3 optimization/retrieval/plot_cross_manufacturer.py
"""

import json
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

# ---------------------------------------------------------------------------
# Data (FROZEN SNAPSHOT — last refreshed 2026-03-21; commit fae5ef9)
# ---------------------------------------------------------------------------
# These numbers are copied from per-config artifacts; they DO NOT auto-refresh
# when sweeps are rerun. If you re-evolve OE programs, re-tune D2, or change
# the batched generator, you must update these literals by hand.
#
# Sources:
#   - D2 hand-tuned: optimization/retrieval/reports/retrieval_evolution_report.md
#     (section: "D2 vs OpenEvolve comparison")
#   - OE-Evolved (STM/NXP): openevolve_retrieval/output_<dev>/full_eval_results.json
#
# Schema for each entry: dict with keys
#   label, evolved_for, tested_on, complete_acc, found_acc, coverage,
#   regs_found, regs_total, correct, wrong, missing, total_tokens

RESULTS = [
    # D2 hand-tuned on STM (from d2_vs_openevolve_comparison.md)
    {
        "label": "D2 Hand-tuned",
        "evolved_for": "STM",
        "tested_on": "STM",
        "complete_acc": 73.39,
        "found_acc": 97.37,
        "coverage": 75.37,
        "regs_found": 78,
        "regs_total": 97,
        "correct": 1296,
        "wrong": 20,
        "missing": 450,
        "total_tokens": 830_634,
    },
    # OE-STM on STM (from full_eval_results.json)
    {
        "label": "OE-Evolved (STM)",
        "evolved_for": "STM",
        "tested_on": "STM",
        "complete_acc": 79.84,
        "found_acc": 85.87,
        "coverage": 92.98,
        "regs_found": 95,
        "regs_total": 97,
        "correct": 1410,
        "wrong": 44,
        "missing": 188,
        "total_tokens": 719_124,
    },
    # OE-STM on NXP (from full_eval_ke04.py run)
    {
        "label": "OE-Evolved (STM)",
        "evolved_for": "STM",
        "tested_on": "NXP",
        "complete_acc": 42.32,
        "found_acc": 45.58,
        "coverage": 92.85,
        "regs_found": 80,
        "regs_total": 87,
        "correct": 645,
        "wrong": 107,
        "missing": 663,
        "total_tokens": 565_495,
    },
    # OE-KE04 on NXP (from full_eval_ke04.py run)
    {
        "label": "OE-Evolved (KE04)",
        "evolved_for": "NXP",
        "tested_on": "NXP",
        "complete_acc": 71.78,
        "found_acc": 75.07,
        "coverage": 95.60,
        "regs_found": 80,
        "regs_total": 87,
        "correct": 1094,
        "wrong": 92,
        "missing": 271,
        "total_tokens": 493_165,
    },
]

# Colors
COLOR_D2 = "#5B8DB8"       # steel blue — hand-tuned
COLOR_OE_STM = "#E07B54"   # warm orange — STM-evolved
COLOR_OE_KE04 = "#6AAF6A"  # green — KE04-evolved
COLOR_CROSS = "#C45B5B"    # red — cross-manufacturer failure

COLORS_BY_KEY = {
    ("D2 Hand-tuned", "STM"): COLOR_D2,
    ("OE-Evolved (STM)", "STM"): COLOR_OE_STM,
    ("OE-Evolved (STM)", "NXP"): COLOR_CROSS,
    ("OE-Evolved (KE04)", "NXP"): COLOR_OE_KE04,
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "openevolve_retrieval")


# ---------------------------------------------------------------------------
# Figure 1: Accuracy & Coverage bar chart
# ---------------------------------------------------------------------------

def plot_accuracy_coverage(results, output_path, stm_only=False):
    from matplotlib.patches import Patch

    fig, ax1 = plt.subplots(figsize=(11, 6))
    if stm_only:
        fig.suptitle(
            "Automated LLM Algorithm Search Discovers\nHigh-Coverage Retrieval Strategy",
            fontsize=14, fontweight="bold", y=0.98,
        )
    else:
        fig.suptitle(
            "Cross-Manufacturer Generalization:\nPer-Manufacturer Retrieval Tuning is Essential",
            fontsize=14, fontweight="bold", y=0.98,
        )

    COLOR_FOUND = "#E07B54"    # warm orange for found accuracy
    COLOR_COV = "#6AAF6A"      # green for coverage
    COLOR_TOK = "#5B8DB8"      # steel blue for tokens

    x = np.arange(len(results))
    bar_width = 0.3

    # Bars: found accuracy and coverage (consistent colors across all algorithms)
    acc_bars = ax1.bar(
        x - bar_width / 2,
        [r["found_acc"] for r in results],
        bar_width,
        color=COLOR_FOUND,
        edgecolor="white",
        linewidth=0.5,
        label="Found Accuracy",
    )
    cov_bars = ax1.bar(
        x + bar_width / 2,
        [r["coverage"] for r in results],
        bar_width,
        color=COLOR_COV,
        alpha=0.5,
        edgecolor="white",
        linewidth=0.5,
        label="Coverage",
    )

    # Value labels on bars (skip zeros)
    for bar in acc_bars:
        h = bar.get_height()
        if h > 0:
            ax1.text(
                bar.get_x() + bar.get_width() / 2, h + 1,
                f"{h:.1f}%", ha="center", va="bottom", fontsize=9,
                fontweight="bold", color=COLOR_FOUND,
            )
    for bar in cov_bars:
        h = bar.get_height()
        if h > 0:
            ax1.text(
                bar.get_x() + bar.get_width() / 2, h + 1,
                f"{h:.1f}%", ha="center", va="bottom", fontsize=8,
                color=COLOR_COV,
            )

    ax1.set_ylim(0, 115)
    ax1.set_ylabel("Percentage", fontsize=11)
    ax1.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # X-axis labels
    xlabels = [
        "Coding Agent\nwith HITL\n(STM)",
        "OpenEvolve\n(STM)",
        "OpenEvolve\n(STM) on NXP",
        "OpenEvolve\n(NXP)",
    ]
    ax1.set_xticks(x)
    ax1.set_xticklabels(xlabels, fontsize=9)

    # Legend
    legend_elements = [
        Patch(facecolor=COLOR_FOUND, edgecolor="white", label="Found Accuracy"),
        Patch(facecolor=COLOR_COV, alpha=0.5, edgecolor="white", label="Coverage"),
    ]
    ax1.legend(handles=legend_elements, loc="upper center", fontsize=9, framealpha=0.9,
               bbox_to_anchor=(0.5, 1.12))

    # Separator line between STM and NXP groups
    ax1.axvline(x=1.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax1.text(0.5, 112, "Tested on STM RM0041 (11 peripherals, 97 registers)",
             ha="center", fontsize=9, color="gray")
    ax1.text(2.5, 112, "Tested on NXP KE04 (12 peripherals, 87 registers)",
             ha="center", fontsize=9, color="gray")

    # Definition line with bold terms
    fig.text(
        0.5, -0.03,
        r"$\bf{Found\ Accuracy}$ = correct / (correct + wrong + missing) for registers with output.    "
        r"$\bf{Coverage}$ = facts from found registers / total facts.",
        ha="center", fontsize=9, style="italic", color="#444444",
    )
    # Key insight line, fully bold (skip for STM-only presentation slide)
    if not stm_only:
        fig.text(
            0.5, -0.07,
            "STM-evolved drops from 85.9% → 45.6% found accuracy on NXP (−40.3pp). "
            "Per-manufacturer evolution recovers to 75.1% (+29.5pp).",
            ha="center", fontsize=9, fontweight="bold", color="#444444",
        )

    plt.tight_layout(rect=[0, 0.02, 1, 0.95])
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {output_path}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2: Token efficiency scatter
# ---------------------------------------------------------------------------

def plot_token_efficiency(results, output_path):
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.set_title(
        "Token Efficiency: Accuracy vs Cost",
        fontsize=14, fontweight="bold",
    )

    markers = {
        ("D2 Hand-tuned", "STM"): ("o", COLOR_D2, 120),       # circle
        ("OE-Evolved (STM)", "STM"): ("D", COLOR_OE_STM, 120),  # diamond
        ("OE-Evolved (STM)", "NXP"): ("X", COLOR_CROSS, 140),   # X marker
        ("OE-Evolved (KE04)", "NXP"): ("D", COLOR_OE_KE04, 120),
    }

    for r in results:
        key = (r["label"], r["tested_on"])
        marker, color, size = markers[key]
        tokens_k = r["total_tokens"] / 1000
        tpf = r["total_tokens"] / r["correct"] if r["correct"] > 0 else 0

        ax.scatter(
            tokens_k, r["found_acc"],
            marker=marker, c=color, s=size, edgecolors="black", linewidths=0.5,
            zorder=5,
        )

        # Annotation
        target_tag = f"on {r['tested_on']}"
        offset = (12, 8)
        if r["label"] == "D2 Hand-tuned":
            offset = (-15, 12)
        elif key == ("OE-Evolved (STM)", "NXP"):
            offset = (12, -15)

        ax.annotate(
            f"{r['label']}\n{target_tag}\n{r['found_acc']:.1f}%, {tokens_k:.0f}K tok\n({tpf:.0f} tok/fact)",
            xy=(tokens_k, r["found_acc"]),
            xytext=offset,
            textcoords="offset points",
            fontsize=8,
            arrowprops=dict(arrowstyle="-", color="gray", lw=0.5),
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
        )

    ax.set_xlabel("Total Tokens (thousands)", fontsize=11)
    ax.set_ylabel("Found Accuracy (%)", fontsize=11)
    ax.set_ylim(30, 105)
    ax.set_xlim(400, 900)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.grid(True, alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLOR_D2,
               markersize=10, markeredgecolor="black", markeredgewidth=0.5,
               label="D2 Hand-tuned"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor=COLOR_OE_STM,
               markersize=10, markeredgecolor="black", markeredgewidth=0.5,
               label="OE-Evolved (matched)"),
        Line2D([0], [0], marker="X", color="w", markerfacecolor=COLOR_CROSS,
               markersize=11, markeredgecolor="black", markeredgewidth=0.5,
               label="OE-Evolved (cross-mfg)"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor=COLOR_OE_KE04,
               markersize=10, markeredgecolor="black", markeredgewidth=0.5,
               label="OE-Evolved (matched)"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=9, framealpha=0.9)

    # Annotation
    fig.text(
        0.5, -0.04,
        "Per-manufacturer evolution: best accuracy at lowest cost (451 tok/fact).\n"
        "Cross-manufacturer wastes tokens: 877 tok/fact for 46% found accuracy.",
        ha="center", fontsize=10, style="italic", color="#444444",
    )

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {output_path}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3: Token usage bar chart
# ---------------------------------------------------------------------------

def plot_token_usage_bars(results, output_path):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.set_title(
        "Token Usage by Algorithm",
        fontsize=14, fontweight="bold",
    )

    x = np.arange(len(results))
    bar_width = 0.5

    colors = [COLORS_BY_KEY[(r["label"], r["tested_on"])] for r in results]
    tokens_k = [r["total_tokens"] / 1000 for r in results]

    bars = ax.bar(x, tokens_k, bar_width, color=colors, edgecolor="white", linewidth=0.5)

    # Labels on bars: total tokens + tokens/correct fact
    for i, bar in enumerate(bars):
        h = bar.get_height()
        r = results[i]
        tpf = r["total_tokens"] / r["correct"] if r["correct"] > 0 else 0
        ax.text(
            bar.get_x() + bar.get_width() / 2, h + 8,
            f"{tokens_k[i]:.0f}K\n({tpf:.0f} tok/fact)",
            ha="center", va="bottom", fontsize=9, fontweight="bold",
        )

    # X-axis labels
    xlabels = []
    for r in results:
        target = r["tested_on"]
        if r["label"] == "D2 Hand-tuned":
            xlabels.append(f"D2 Hand-tuned\non STM")
        elif r["evolved_for"] == r["tested_on"]:
            xlabels.append(f"OE-{r['evolved_for']}\non {target} ★")
        else:
            xlabels.append(f"OE-{r['evolved_for']}\non {target} ✗")

    ax.set_xticks(x)
    ax.set_xticklabels(xlabels, fontsize=9)
    ax.set_ylabel("Total Tokens (thousands)", fontsize=11)
    ax.set_ylim(0, max(tokens_k) * 1.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)

    # Add found accuracy as text below each bar
    for i, r in enumerate(results):
        ax.text(
            x[i], -max(tokens_k) * 0.06,
            f"Found: {r['found_acc']:.1f}%",
            ha="center", va="top", fontsize=8, color="#444444",
        )

    fig.text(
        0.5, -0.06,
        "★ = manufacturer-matched evolution    ✗ = cross-manufacturer\n"
        "Matched evolution achieves best accuracy at lowest token cost.",
        ha="center", fontsize=10, style="italic", color="#444444",
    )

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {output_path}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def print_tables(results):
    print("\n" + "=" * 95)
    print("TABLE 1: ACCURACY & COVERAGE")
    print("=" * 95)
    header = (
        f"{'Algorithm':<22} {'Tested On':<10} {'Complete':>10} {'Found':>10} "
        f"{'Coverage':>10} {'Regs':>10} {'Correct':>8} {'Wrong':>6} {'Missing':>8}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['label']:<22} {r['tested_on']:<10} "
            f"{r['complete_acc']:>9.1f}% {r['found_acc']:>9.1f}% "
            f"{r['coverage']:>9.1f}% "
            f"{r['regs_found']:>4}/{r['regs_total']:<5} "
            f"{r['correct']:>8} {r['wrong']:>6} {r['missing']:>8}"
        )
    print("-" * len(header))

    print(f"\n{'=' * 80}")
    print("TABLE 2: TOKEN EFFICIENCY")
    print("=" * 80)
    header2 = (
        f"{'Algorithm':<22} {'Tested On':<10} {'Complete':>10} "
        f"{'Tokens':>12} {'Tok/Correct':>12} {'Correct':>8}"
    )
    print(header2)
    print("-" * len(header2))
    for r in results:
        tpf = r["total_tokens"] / r["correct"] if r["correct"] > 0 else 0
        print(
            f"{r['label']:<22} {r['tested_on']:<10} "
            f"{r['complete_acc']:>9.1f}% "
            f"{r['total_tokens']:>12,} "
            f"{tpf:>12.0f} "
            f"{r['correct']:>8}"
        )
    print("-" * len(header2))

    # Key insights
    print("\nKEY INSIGHTS:")
    stm_on_stm = next(r for r in results if r["label"] == "OE-Evolved (STM)" and r["tested_on"] == "STM")
    stm_on_nxp = next(r for r in results if r["label"] == "OE-Evolved (STM)" and r["tested_on"] == "NXP")
    ke04_on_nxp = next(r for r in results if r["label"] == "OE-Evolved (KE04)" and r["tested_on"] == "NXP")
    d2 = next(r for r in results if r["label"] == "D2 Hand-tuned")

    print(f"  • Cross-manufacturer accuracy drop: {stm_on_stm['complete_acc']:.1f}% → {stm_on_nxp['complete_acc']:.1f}% "
          f"(−{stm_on_stm['complete_acc'] - stm_on_nxp['complete_acc']:.1f}pp)")
    print(f"  • Per-manufacturer recovery: {stm_on_nxp['complete_acc']:.1f}% → {ke04_on_nxp['complete_acc']:.1f}% "
          f"(+{ke04_on_nxp['complete_acc'] - stm_on_nxp['complete_acc']:.1f}pp)")
    print(f"  • OE vs hand-tuned (STM): +{stm_on_stm['complete_acc'] - d2['complete_acc']:.1f}pp accuracy, "
          f"−{(1 - stm_on_stm['total_tokens'] / d2['total_tokens']) * 100:.0f}% tokens")
    tpf_matched = ke04_on_nxp["total_tokens"] / ke04_on_nxp["correct"]
    tpf_cross = stm_on_nxp["total_tokens"] / stm_on_nxp["correct"]
    print(f"  • Token efficiency: matched={tpf_matched:.0f} tok/fact vs cross-mfg={tpf_cross:.0f} tok/fact "
          f"({tpf_cross / tpf_matched:.1f}× waste)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print_tables(RESULTS)

    fig1_path = os.path.join(OUTPUT_DIR, "fig_accuracy_coverage.png")
    fig2_path = os.path.join(OUTPUT_DIR, "fig_token_efficiency.png")
    fig3_path = os.path.join(OUTPUT_DIR, "fig_token_usage_bars.png")

    plot_accuracy_coverage(RESULTS, fig1_path)

    # Stage 1 version: STM only, NXP zeroed out
    results_stm_only = []
    for r in RESULTS:
        if r["tested_on"] == "NXP":
            r2 = dict(r)
            r2["found_acc"] = 0
            r2["coverage"] = 0
            results_stm_only.append(r2)
        else:
            results_stm_only.append(r)
    fig1_stm_path = os.path.join(OUTPUT_DIR, "fig_accuracy_coverage_stm_only.png")
    plot_accuracy_coverage(results_stm_only, fig1_stm_path, stm_only=True)

    plot_token_efficiency(RESULTS, fig2_path)
    plot_token_usage_bars(RESULTS, fig3_path)

    print(f"\nFigures saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
