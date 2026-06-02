#!/usr/bin/env python3
"""
Analyze a folder containing many generator "run" subdirectories.

This script is intentionally generic: it scans RUNS_ROOT for subdirectories that look like
experiment runs (contain timing/usage/comparison files), aggregates metrics into tables,
and generates a few high-signal plots.

No CLI args by design. Edit variables at the top of `main()` and run:

    python3 optimization/retrieval/analyze_experiment_runs.py

Optional: you can also pass filtering thresholds without editing the file:
    python3 optimization/retrieval/analyze_experiment_runs.py --min-accuracy 95 --max-timing 5 --max-usage 7000
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

# Ensure matplotlib/fontconfig caches are writable (Cursor sandbox often blocks $HOME caches).
# Do this *before* importing matplotlib anywhere.
_SCRIPT_DIR = Path(__file__).resolve().parent
_MPLCONFIGDIR = _SCRIPT_DIR / ".mplconfig"
_XDG_CACHE_HOME = _SCRIPT_DIR / ".cache"
_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
_XDG_CACHE_HOME.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPLCONFIGDIR))
os.environ.setdefault("XDG_CACHE_HOME", str(_XDG_CACHE_HOME))


@dataclass(frozen=True)
class RunConfig:
    run_name: str
    run_dir: Path
    peripheral: Optional[str] = None
    vs_type: Optional[str] = None
    embeddings: Optional[int] = None
    pages_after: Optional[int] = None
    table_pages_only_expansion: Optional[bool] = None
    metadata_filter: Optional[bool] = None
    config_name: Optional[str] = None


def short_name(s: Any) -> str:
    """
    Shorten run/config names to reduce label overlap.

    User-preferred shortening:
    - enriched -> e
    - emb4 -> e4
    - pages2 -> p2
    - tableonly -> to

    Abbreviation key (used across plots + CSVs + reports):
    - **e**: "enriched" (e.g. `md_enriched` -> `md_e`)
    - **eN**: embedding count N (e.g. `_emb4` -> `_e4`)
    - **pN**: pages_after N (e.g. `_pages2` -> `_p2`)
    - **to**: table-only contiguous expansion enabled (from `_tableonly` suffix)
    """
    s = "" if s is None else str(s)
    s = s.replace("enriched", "e")
    s = re.sub(r"_emb(\d+)", r"_e\1", s)
    s = re.sub(r"_pages(\d+)", r"_p\1", s)
    s = s.replace("tableonly", "to")
    # Local vector DB abbreviations: local_ -> l_, _rrlocal -> _rrl, _kb -> _kb (already short)
    s = re.sub(r"^local_", "l_", s)
    s = re.sub(r"_rr(\w+)", lambda m: f"_rr{m.group(1)[0]}", s)  # _rrlocal -> _rrl
    return s


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
        return float(x)
    except Exception:
        return None


def _safe_int(x: Any) -> Optional[int]:
    try:
        if x is None:
            return None
        return int(float(x))
    except Exception:
        return None


def _parse_run_config_from_name(run_name: str, run_dir: Path) -> RunConfig:
    """
    Best-effort parse of run config from directory name.

    Supports common patterns like:
      - md_emb4_pages2
      - md_emb4_pages2_tableonly
      - md_enriched_emb1_pages0_tableonly
      - local_rm0041_md_emb1_kb_rrlocal  (local vector DB)

    If parsing fails, config fields remain None.
    """
    # Pattern for local vector DB runs: local_{db_name}_emb{N}[_kb][_rr{type}][_mf][_pa{N}][_tpo]
    local_pattern = re.compile(
        r"^local_(?P<db_name>.+?)_emb(?P<embeddings>\d+)(?P<kb>_kb)?(?:_rr(?P<reranker>\w+))?(?P<mf>_mf)?(?:_pa(?P<pages_after>\d+))?(?P<tpo>_tpo)?$"
    )
    m_local = local_pattern.match(run_name)
    if m_local:
        db_name = m_local.group("db_name")
        embeddings = int(m_local.group("embeddings"))
        metadata_filter = bool(m_local.group("mf"))
        pages_after = int(m_local.group("pages_after")) if m_local.group("pages_after") is not None else None
        table_pages_only = bool(m_local.group("tpo"))
        return RunConfig(
            run_name=run_name,
            run_dir=run_dir,
            peripheral=None,
            vs_type=f"local_{db_name}",
            embeddings=embeddings,
            pages_after=pages_after,
            table_pages_only_expansion=table_pages_only,
            metadata_filter=metadata_filter,
            config_name=run_name,
        )

    # Pattern for non-local runs with db name prefix but no pages: {db_name}_emb{N}[_kb][_rr{type}]
    db_emb_pattern = re.compile(
        r"^(?P<db_name>.+?)_emb(?P<embeddings>\d+)(?P<kb>_kb)?(?:_rr(?P<reranker>\w+))?$"
    )

    pattern = re.compile(
        r"^(?P<vs_type>.+?)_emb(?P<embeddings>\d+)_pages(?P<pages_after>\d+)(?P<tableonly>_tableonly)?$"
    )
    m = pattern.match(run_name)
    if not m:
        # Try the db_emb pattern (no pages_after, e.g. "md_emb1_kb_rrlocal")
        m_db = db_emb_pattern.match(run_name)
        if m_db:
            return RunConfig(
                run_name=run_name,
                run_dir=run_dir,
                peripheral=None,
                vs_type=m_db.group("db_name"),
                embeddings=int(m_db.group("embeddings")),
                pages_after=None,
                table_pages_only_expansion=None,
                config_name=run_name,
            )

        # Try "<peripheral>_<config...>" pattern, e.g. "bkp_md_emb1_pages0"
        if "_" in run_name:
            peripheral_candidate, rest = run_name.split("_", 1)
            m2 = pattern.match(rest)
            if m2:
                vs_type = m2.group("vs_type")
                embeddings = int(m2.group("embeddings"))
                pages_after = int(m2.group("pages_after"))
                tableonly = bool(m2.group("tableonly"))
                config_name = rest
                return RunConfig(
                    run_name=run_name,
                    run_dir=run_dir,
                    peripheral=peripheral_candidate,
                    vs_type=vs_type,
                    embeddings=embeddings,
                    pages_after=pages_after,
                    table_pages_only_expansion=tableonly,
                    config_name=config_name,
                )

        return RunConfig(run_name=run_name, run_dir=run_dir)

    vs_type = m.group("vs_type")
    embeddings = int(m.group("embeddings"))
    pages_after = int(m.group("pages_after"))
    tableonly = bool(m.group("tableonly"))
    config_name = run_name
    return RunConfig(
        run_name=run_name,
        run_dir=run_dir,
        peripheral=None,
        vs_type=vs_type,
        embeddings=embeddings,
        pages_after=pages_after,
        table_pages_only_expansion=tableonly,
        config_name=config_name,
    )


def _is_run_dir(d: Path) -> bool:
    if not d.is_dir():
        return False
    return any(
        [
            (d / "info" / "timing_stats.json").exists(),
            (d / "timing_stats.json").exists(),
            (d / "info" / "usage.csv").exists(),
            (d / "info" / "comparison_results.json").exists(),
            (d / "info" / "comparison_register_results.csv").exists(),
            (d / "info" / "comparison_fact_errors.csv").exists(),
            (d / "comparison_results.json").exists(),
            (d / "comparison_register_results.csv").exists(),
            (d / "comparison_fact_errors.csv").exists(),
        ]
    )


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _read_usage_csv(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _read_csv(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _first_df(*candidates: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    for df in candidates:
        if df is not None:
            return df
    return None


def _summarize_usage(df: pd.DataFrame) -> Dict[str, Any]:
    # Columns observed: model_name,input_tokens,cached_tokens,output_tokens,reasoning_tokens,total_tokens,file_search_tokens,peripheral_name,register_name
    summary: Dict[str, Any] = {}
    for col in [
        "input_tokens",
        "cached_tokens",
        "output_tokens",
        "reasoning_tokens",
        "total_tokens",
        "file_search_tokens",
    ]:
        if col in df.columns:
            summary[f"usage_{col}_sum"] = _safe_int(df[col].fillna(0).sum())
        else:
            summary[f"usage_{col}_sum"] = None

    summary["usage_rows"] = int(len(df))
    if "register_name" in df.columns:
        summary["usage_registers"] = int(df["register_name"].nunique(dropna=True))
    else:
        summary["usage_registers"] = None

    if "model_name" in df.columns:
        models = sorted(set(str(x) for x in df["model_name"].dropna().tolist()))
        summary["usage_models"] = ",".join(models) if models else None
    else:
        summary["usage_models"] = None
    return summary


def _summarize_timing(timing: Dict[str, Any]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    total_time = 0.0
    for stage_name, stats in timing.items():
        if not isinstance(stats, dict):
            continue
        stage_total = _safe_float(stats.get("total_time")) or 0.0
        stage_count = _safe_int(stats.get("count"))
        total_time += stage_total

        # Keep a couple key fields per stage.
        safe_stage = re.sub(r"[^a-zA-Z0-9_]+", "_", stage_name)
        summary[f"timing_{safe_stage}_total_time"] = stage_total
        summary[f"timing_{safe_stage}_count"] = stage_count

    summary["timing_total_time_sum"] = total_time

    # Common stages (if present)
    for stage in ["vector_store_search", "generator_llm_call"]:
        stats = timing.get(stage, {}) if isinstance(timing.get(stage), dict) else {}
        summary[f"timing_{stage}_total_time"] = _safe_float(stats.get("total_time"))
        summary[f"timing_{stage}_count"] = _safe_int(stats.get("count"))
    return summary


def _derive_accuracy_from_register_results(df: pd.DataFrame) -> Dict[str, Any]:
    # Expected columns: peripheral, register, register_found, correct, wrong, missing, total_facts, accuracy
    if df is None or df.empty:
        return {
            "accuracy": None,
            "found_accuracy": None,
            "complete_accuracy": None,
            "coverage": None,
            "correct": None,
            "wrong": None,
            "missing": None,
            "total_facts": None,
            "correct_all": None,
            "wrong_all": None,
            "missing_all": None,
            "total_facts_all": None,
            "registers_found": None,
            "total_registers": None,
        }

    total_registers = int(len(df))
    registers_found = int(df["register_found"].fillna(False).astype(bool).sum()) if "register_found" in df.columns else None

    # All registers
    correct_all = int(df["correct"].fillna(0).sum()) if "correct" in df.columns else None
    wrong_all = int(df["wrong"].fillna(0).sum()) if "wrong" in df.columns else None
    missing_all = int(df["missing"].fillna(0).sum()) if "missing" in df.columns else None
    total_facts_all = int(df["total_facts"].fillna(0).sum()) if "total_facts" in df.columns else None
    complete_accuracy = (correct_all / total_facts_all * 100.0) if (correct_all is not None and total_facts_all) else None

    # Found registers only
    if "register_found" in df.columns:
        found_df = df[df["register_found"].fillna(False).astype(bool)]
    else:
        found_df = df
    correct = int(found_df["correct"].fillna(0).sum()) if "correct" in found_df.columns else correct_all
    wrong = int(found_df["wrong"].fillna(0).sum()) if "wrong" in found_df.columns else wrong_all
    missing = int(found_df["missing"].fillna(0).sum()) if "missing" in found_df.columns else missing_all
    total_facts = int(found_df["total_facts"].fillna(0).sum()) if "total_facts" in found_df.columns else total_facts_all
    found_accuracy = (correct / total_facts * 100.0) if (correct is not None and total_facts) else None

    # Coverage: fraction of total facts that come from found registers
    coverage = (total_facts / total_facts_all * 100.0) if (total_facts is not None and total_facts_all) else None

    return {
        "accuracy": found_accuracy,
        "found_accuracy": found_accuracy,
        "complete_accuracy": complete_accuracy,
        "coverage": coverage,
        "correct": correct,
        "wrong": wrong,
        "missing": missing,
        "total_facts": total_facts,
        "correct_all": correct_all,
        "wrong_all": wrong_all,
        "missing_all": missing_all,
        "total_facts_all": total_facts_all,
        "registers_found": registers_found,
        "total_registers": total_registers,
    }


def _pareto_front_indices(points: List[Tuple[float, float]]) -> List[int]:
    """
    Compute indices of non-dominated points minimizing both objectives.

    points: List[(x, y)] where smaller is better.
    """
    front: List[int] = []
    for i, (xi, yi) in enumerate(points):
        dominated = False
        for j, (xj, yj) in enumerate(points):
            if j == i:
                continue
            if (xj <= xi and yj <= yi) and (xj < xi or yj < yi):
                dominated = True
                break
        if not dominated:
            front.append(i)
    return front


def _plot_scatter(
    df: pd.DataFrame,
    x: str,
    y: str,
    out_path: Path,
    title: str,
    label_col: str = "run_name",
    highlight_pareto: bool = True,
) -> None:
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    plot_df = df[[x, y, label_col]].copy()
    plot_df = plot_df.dropna(subset=[x, y])
    if plot_df.empty:
        return

    xs = plot_df[x].astype(float).tolist()
    ys = plot_df[y].astype(float).tolist()
    labels = [short_name(v) for v in plot_df[label_col].tolist()]

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(xs, ys, alpha=0.7)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(title)
    ax.grid(True, alpha=0.25)

    # Labels (one per point). Keep it small; 30-50 points is still readable.
    for xi, yi, label in zip(xs, ys, labels):
        if not label:
            continue
        ax.annotate(
            label,
            (xi, yi),
            textcoords="offset points",
            xytext=(5, 5),
            ha="left",
            va="bottom",
            fontsize=7,
            alpha=0.85,
        )

    if highlight_pareto and len(xs) >= 3:
        # For accuracy plots, we want to minimize x and maximize y, so we convert to "minimize both".
        # We assume y is accuracy-like (higher is better). Convert y -> (100 - y).
        points = list(zip(xs, [100.0 - yy for yy in ys]))
        front_idx = _pareto_front_indices(points)
        ax.scatter(
            [xs[i] for i in front_idx],
            [ys[i] for i in front_idx],
            s=90,
            facecolors="none",
            edgecolors="red",
            linewidths=1.5,
            label="Pareto",
        )
        ax.legend(loc="best")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def _plot_heatmaps(
    df: pd.DataFrame,
    value_col: str,
    out_dir: Path,
    title_prefix: str,
) -> None:
    """
    Heatmap of value_col over (embeddings x pages_after), faceted by vs_type and table_pages_only_expansion.
    Only runs when embeddings/pages_after are available.
    """
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    required = {"embeddings", "pages_after", value_col}
    if not required.issubset(df.columns):
        return

    plot_df = df.dropna(subset=["embeddings", "pages_after", value_col]).copy()
    if plot_df.empty:
        return

    facets = ["vs_type", "table_pages_only_expansion"]
    # If facets are missing (or fully null), treat as a single group.
    if not set(facets).issubset(plot_df.columns):
        plot_df["vs_type"] = "unknown"
        plot_df["table_pages_only_expansion"] = "unknown"
    else:
        plot_df["vs_type"] = plot_df["vs_type"].fillna("unknown")
        plot_df["table_pages_only_expansion"] = plot_df["table_pages_only_expansion"].fillna("unknown")

    for (vs_type, table_only), group in plot_df.groupby(facets, dropna=False):
        pivot = group.pivot_table(
            index="embeddings",
            columns="pages_after",
            values=value_col,
            aggfunc="mean",
        ).sort_index(axis=0).sort_index(axis=1)

        if pivot.empty:
            continue

        fig, ax = plt.subplots(figsize=(8, 5))
        im = ax.imshow(pivot.values, aspect="auto")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([str(c) for c in pivot.columns])
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels([str(r) for r in pivot.index])
        ax.set_xlabel("pages_after")
        ax.set_ylabel("embeddings")
        ax.set_title(f"{title_prefix} ({value_col}) | vs={short_name(vs_type)} | to={table_only}")

        # Annotate cells
        for i in range(pivot.shape[0]):
            for j in range(pivot.shape[1]):
                val = pivot.values[i, j]
                if pd.isna(val):
                    continue
                ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=8)

        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        ax.grid(False)

        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"heatmap_{value_col}__vs-{short_name(vs_type)}__to-{table_only}.png"
        fig.tight_layout()
        fig.savefig(out_path, dpi=200)
        plt.close(fig)


def _write_text_report(df_runs: pd.DataFrame, out_path: Path) -> None:
    lines: List[str] = []
    lines.append("Experiment run analysis summary")
    lines.append("")
    lines.append(f"Runs analyzed: {len(df_runs)}")
    lines.append("")

    df = df_runs.copy()
    df = df.dropna(subset=["accuracy"])

    # Prefer SUM usage/time. For this analysis we compare configs on the same input set,
    # so sums reflect total cost to process the full benchmark.
    usage_sort = "usage_total_tokens_sum"
    timing_sort = "timing_total_time_sum"

    df = df.sort_values(
        by=["accuracy", usage_sort, timing_sort],
        ascending=[False, True, True],
        na_position="last",
    )

    def _format_row(r: pd.Series) -> str:
        name = r.get("config_name") if "config_name" in r.index else r.get("run_name")
        label = r.get("config_label") if "config_label" in r.index else short_name(name)
        tokens = r.get(usage_sort)
        time_s = r.get(timing_sort)
        extra = ""
        if "peripheral_count" in r.index:
            extra = f" | periph={int(r.get('peripheral_count') or 0)}"
        # Show all three metrics when available
        found_acc = r.get("found_accuracy") if "found_accuracy" in r.index and pd.notna(r.get("found_accuracy")) else r.get("accuracy")
        complete_acc = r.get("complete_accuracy") if "complete_accuracy" in r.index else None
        coverage = r.get("coverage") if "coverage" in r.index else None
        acc_str = f"found={float(found_acc):.1f}%"
        if complete_acc is not None and pd.notna(complete_acc):
            acc_str += f" complete={float(complete_acc):.1f}%"
        if coverage is not None and pd.notna(coverage):
            acc_str += f" cov={float(coverage):.1f}%"
        return (
            f"{label}{extra} | {acc_str} | "
            f"tokens={float(tokens):.0f} | time={float(time_s):.2f}s | "
            f"vs={short_name(r.get('vs_type'))} emb={r.get('embeddings')} pages={r.get('pages_after')} to={r.get('table_pages_only_expansion')} mf={r.get('metadata_filter')}"
        )

    lines.append("Top 10 by accuracy (tie-break: fewer tokens, then faster):")
    if df.empty:
        lines.append("  (no accuracy data)")
    else:
        for _, row in df.head(10).iterrows():
            lines.append("  " + _format_row(row))
    lines.append("")

    # Pareto: minimize tokens, maximize accuracy (use SUM tokens)
    pareto_df = df_runs.dropna(subset=["accuracy", "usage_total_tokens_sum"]).copy()
    if not pareto_df.empty:
        points = list(zip(pareto_df["usage_total_tokens_sum"].astype(float).tolist(), (100.0 - pareto_df["accuracy"].astype(float)).tolist()))
        front = _pareto_front_indices(points)
        lines.append("Pareto (min tokens, max accuracy):")
        for idx in front[:15]:
            lines.append("  " + _format_row(pareto_df.iloc[idx]))
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _clear_pngs(dir_path: Path) -> None:
    if not dir_path.exists() or not dir_path.is_dir():
        return
    for p in dir_path.iterdir():
        if p.is_file() and p.suffix.lower() == ".png":
            try:
                p.unlink()
            except Exception:
                pass


def _delete_if_exists(path: Path) -> None:
    try:
        if path.exists() and path.is_file():
            path.unlink()
    except Exception:
        pass


def _parse_args(
    default_runs_root: str,
    default_output_dir: Optional[str],
    default_title_prefix: Optional[str],
    default_min_accuracy: Optional[float],
    default_max_timing: Optional[float],
    default_max_usage: Optional[int],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze a folder of experiment run subdirectories.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--runs-root", default=default_runs_root, help="Folder containing many run subdirectories")
    parser.add_argument("--output-dir", default=default_output_dir, help="Output directory (default: <runs-root>/analysis)")
    parser.add_argument("--title-prefix", default=default_title_prefix, help="Plot/report title prefix (default: runs-root folder name)")

    parser.add_argument("--min-accuracy", type=float, default=default_min_accuracy, help="Minimum accuracy (%) to include")
    parser.add_argument("--max-timing", type=float, default=default_max_timing, help="Maximum total timing (seconds) to include")
    parser.add_argument("--max-usage", type=int, default=default_max_usage, help="Maximum total token usage to include (usage_total_tokens_sum)")
    return parser.parse_args()


def _apply_filters(
    df_runs: pd.DataFrame,
    min_accuracy: Optional[float],
    max_timing: Optional[float],
    max_usage: Optional[int],
) -> pd.DataFrame:
    df = df_runs.copy()
    if min_accuracy is not None:
        df = df[df["accuracy"].notna() & (df["accuracy"].astype(float) >= float(min_accuracy))]
    if max_timing is not None:
        df = df[df["timing_total_time_sum"].notna() & (df["timing_total_time_sum"].astype(float) <= float(max_timing))]
    if max_usage is not None:
        df = df[df["usage_total_tokens_sum"].notna() & (df["usage_total_tokens_sum"].astype(float) <= float(max_usage))]
    return df


def main() -> None:
    # =========================
    # EDIT THESE VARIABLES
    # =========================
    RUNS_ROOT = "optimization/retrieval/experiments/local_vector_db_v4"
    OUTPUT_DIR: Optional[str] = None  # default: f"{RUNS_ROOT}/analysis"
    TITLE_PREFIX = None  # e.g. "AFIO peripheral sweep"
    MIN_ACCURACY: Optional[float] = None          # e.g. 95.0
    MAX_TIMING_SECONDS: Optional[float] = None    # e.g. 5.0
    MAX_TOTAL_TOKENS: Optional[int] = None        # e.g. 7000
    # =========================

    args = _parse_args(
        default_runs_root=RUNS_ROOT,
        default_output_dir=OUTPUT_DIR,
        default_title_prefix=TITLE_PREFIX,
        default_min_accuracy=MIN_ACCURACY,
        default_max_timing=MAX_TIMING_SECONDS,
        default_max_usage=MAX_TOTAL_TOKENS,
    )

    runs_root = Path(args.runs_root)
    if args.output_dir is None:
        output_dir = runs_root / "analysis"
    else:
        output_dir = Path(args.output_dir)

    if not runs_root.exists():
        raise FileNotFoundError(f"RUNS_ROOT does not exist: {runs_root}")

    title_prefix = args.title_prefix or runs_root.name

    run_dirs = [d for d in sorted(runs_root.iterdir()) if _is_run_dir(d)]
    if not run_dirs:
        print(f"No run directories found under: {runs_root}")
        return

    run_rows: List[Dict[str, Any]] = []
    register_rows: List[Dict[str, Any]] = []
    error_rows: List[Dict[str, Any]] = []

    for d in run_dirs:
        cfg = _parse_run_config_from_name(d.name, d)

        row: Dict[str, Any] = {
            "run_name": cfg.run_name,
            "run_label": short_name(cfg.run_name),
            "run_dir": str(cfg.run_dir),
            "peripheral": cfg.peripheral,
            "vs_type": cfg.vs_type,
            "vs_label": short_name(cfg.vs_type),
            "embeddings": cfg.embeddings,
            "pages_after": cfg.pages_after,
            "table_pages_only_expansion": cfg.table_pages_only_expansion,
            "metadata_filter": cfg.metadata_filter,
            "config_name": cfg.config_name,
            "config_label": short_name(cfg.config_name),
        }

        # Usage
        usage_df = _read_usage_csv(d / "info" / "usage.csv")
        if usage_df is not None:
            row.update(_summarize_usage(usage_df))
        else:
            row.update(_summarize_usage(pd.DataFrame()))

        # Timing (prefer info/ folder)
        timing = _load_json(d / "info" / "timing_stats.json") or _load_json(d / "timing_stats.json") or {}
        row.update(_summarize_timing(timing))

        # Accuracy + per-register + errors
        # Support both layouts:
        # 1) Single-peripheral run dirs: comparison_results.json + comparison_*.csv
        # 2) Multi-peripheral-per-config dirs: comparison_results_<peripheral>.json + comparison_*_<peripheral>.csv
        periph_comparisons: List[Tuple[str, Dict[str, Any]]] = []

        # Prefer new combined comparison file if present.
        combined_used = False
        combined = _load_json(d / "info" / "comparison_results.json") or _load_json(d / "comparison_results.json")
        if isinstance(combined, dict) and "peripheral_count" in combined and "peripherals" in combined:
            combined_used = True
            # Read found_accuracy if present, fall back to legacy "accuracy"
            found_acc = combined.get("found_accuracy") if combined.get("found_accuracy") is not None else combined.get("accuracy")
            row.update(
                {
                    "peripheral_count": combined.get("peripheral_count"),
                    "peripherals": ",".join(combined.get("peripherals") or []) if isinstance(combined.get("peripherals"), list) else combined.get("peripherals"),
                    "registers_found": combined.get("registers_found"),
                    "total_registers": combined.get("total_registers"),
                    "correct": combined.get("correct"),
                    "wrong": combined.get("wrong"),
                    "missing": combined.get("missing"),
                    "total_facts": combined.get("total_facts"),
                    "found_accuracy": found_acc,
                    "correct_all": combined.get("correct_all"),
                    "wrong_all": combined.get("wrong_all"),
                    "missing_all": combined.get("missing_all"),
                    "total_facts_all": combined.get("total_facts_all"),
                    "complete_accuracy": combined.get("complete_accuracy"),
                    "coverage": combined.get("coverage"),
                    # Legacy alias so existing plots/reports still work
                    "accuracy": found_acc,
                }
            )
            # Derive complete_accuracy/coverage from register CSV if JSON doesn't have them
            if row.get("complete_accuracy") is None or row.get("coverage") is None:
                _reg_df_for_derive = _first_df(
                    _read_csv(d / "info" / "comparison_register_results.csv"),
                    _read_csv(d / "comparison_register_results.csv"),
                )
                if _reg_df_for_derive is not None and not _reg_df_for_derive.empty:
                    derived = _derive_accuracy_from_register_results(_reg_df_for_derive)
                    if row.get("complete_accuracy") is None:
                        row["complete_accuracy"] = derived.get("complete_accuracy")
                    if row.get("coverage") is None:
                        row["coverage"] = derived.get("coverage")
                    if row.get("correct_all") is None:
                        row["correct_all"] = derived.get("correct_all")
                    if row.get("wrong_all") is None:
                        row["wrong_all"] = derived.get("wrong_all")
                    if row.get("missing_all") is None:
                        row["missing_all"] = derived.get("missing_all")
                    if row.get("total_facts_all") is None:
                        row["total_facts_all"] = derived.get("total_facts_all")

            # Convenience means
            if row.get("peripheral_count"):
                pc = float(row["peripheral_count"])
                if row.get("usage_total_tokens_sum") is not None:
                    row["usage_total_tokens_mean"] = float(row["usage_total_tokens_sum"]) / pc
                if row.get("timing_total_time_sum") is not None:
                    row["timing_total_time_mean"] = float(row["timing_total_time_sum"]) / pc

            # Details
            reg_df = _first_df(
                _read_csv(d / "info" / "comparison_register_results.csv"),
                _read_csv(d / "comparison_register_results.csv"),
            )
            if reg_df is not None and not reg_df.empty:
                for _, rr in reg_df.iterrows():
                    register_rows.append(
                        {
                            "run_name": cfg.run_name,
                            "run_label": short_name(cfg.run_name),
                            "vs_type": cfg.vs_type,
                            "vs_label": short_name(cfg.vs_type),
                            "embeddings": cfg.embeddings,
                            "pages_after": cfg.pages_after,
                            "table_pages_only_expansion": cfg.table_pages_only_expansion,
                            "metadata_filter": cfg.metadata_filter,
                            "peripheral": rr.get("peripheral"),
                            "register": rr.get("register"),
                            "register_found": rr.get("register_found"),
                            "correct": rr.get("correct"),
                            "wrong": rr.get("wrong"),
                            "missing": rr.get("missing"),
                            "total_facts": rr.get("total_facts"),
                            "accuracy": rr.get("accuracy"),
                        }
                    )

            err_df = _first_df(
                _read_csv(d / "info" / "comparison_fact_errors.csv"),
                _read_csv(d / "comparison_fact_errors.csv"),
            )
            if err_df is not None and not err_df.empty:
                for _, er in err_df.iterrows():
                    error_rows.append(
                        {
                            "run_name": cfg.run_name,
                            "run_label": short_name(cfg.run_name),
                            "vs_type": cfg.vs_type,
                            "vs_label": short_name(cfg.vs_type),
                            "embeddings": cfg.embeddings,
                            "pages_after": cfg.pages_after,
                            "table_pages_only_expansion": cfg.table_pages_only_expansion,
                            "metadata_filter": cfg.metadata_filter,
                            "error_type": er.get("error_type"),
                            "peripheral": er.get("peripheral"),
                            "register": er.get("register"),
                            "field_name": er.get("field_name"),
                            "key": er.get("key"),
                            "correct_value": er.get("correct_value"),
                            "generated_value": er.get("generated_value"),
                        }
                    )
        else:
            # Multi-peripheral legacy layout: comparison_results_<peripheral>.json
            legacy_candidates: List[Path] = []
            legacy_candidates.extend(sorted(d.glob("comparison_results_*.json")))
            legacy_candidates.extend(sorted((d / "info" / "peripheral_comparisons").glob("comparison_results_*.json")))
            for p in sorted({pp.resolve() for pp in legacy_candidates}):
                peripheral_name = p.stem.replace("comparison_results_", "")
                payload = _load_json(p)
                if isinstance(payload, dict):
                    periph_comparisons.append((peripheral_name, payload))

        if periph_comparisons:
            # Aggregate across peripherals within this config-dir.
            correct_sum = sum(int(c.get("correct") or 0) for _, c in periph_comparisons)
            wrong_sum = sum(int(c.get("wrong") or 0) for _, c in periph_comparisons)
            missing_sum = sum(int(c.get("missing") or 0) for _, c in periph_comparisons)
            total_facts_sum = sum(int(c.get("total_facts") or 0) for _, c in periph_comparisons)
            registers_found_sum = sum(int(c.get("registers_found") or 0) for _, c in periph_comparisons)
            total_registers_sum = sum(int(c.get("total_registers") or 0) for _, c in periph_comparisons)
            found_accuracy = (correct_sum / total_facts_sum * 100.0) if total_facts_sum > 0 else None

            # Complete metrics (from per-peripheral data if available)
            correct_all_sum = sum(int(c.get("correct_all") or c.get("correct") or 0) for _, c in periph_comparisons)
            wrong_all_sum = sum(int(c.get("wrong_all") or c.get("wrong") or 0) for _, c in periph_comparisons)
            missing_all_sum = sum(int(c.get("missing_all") or c.get("missing") or 0) for _, c in periph_comparisons)
            total_facts_all_sum = sum(int(c.get("total_facts_all") or c.get("total_facts") or 0) for _, c in periph_comparisons)
            complete_accuracy = (correct_all_sum / total_facts_all_sum * 100.0) if total_facts_all_sum > 0 else None
            coverage = (total_facts_sum / total_facts_all_sum * 100.0) if total_facts_all_sum > 0 else None

            row.update(
                {
                    "peripheral_count": len(periph_comparisons),
                    "peripherals": ",".join(p for p, _ in periph_comparisons),
                    "registers_found": registers_found_sum,
                    "total_registers": total_registers_sum,
                    "correct": correct_sum,
                    "wrong": wrong_sum,
                    "missing": missing_sum,
                    "total_facts": total_facts_sum,
                    "found_accuracy": found_accuracy,
                    "correct_all": correct_all_sum,
                    "wrong_all": wrong_all_sum,
                    "missing_all": missing_all_sum,
                    "total_facts_all": total_facts_all_sum,
                    "complete_accuracy": complete_accuracy,
                    "coverage": coverage,
                    "accuracy": found_accuracy,
                }
            )
            # Convenience means for comparing configs across different peripheral counts.
            if row.get("peripheral_count"):
                pc = float(row["peripheral_count"])
                if row.get("usage_total_tokens_sum") is not None:
                    row["usage_total_tokens_mean"] = float(row["usage_total_tokens_sum"]) / pc
                if row.get("timing_total_time_sum") is not None:
                    row["timing_total_time_mean"] = float(row["timing_total_time_sum"]) / pc

            # Register/error detail rows: concatenate per-peripheral CSVs if present.
            for peripheral_name, _comp in periph_comparisons:
                reg_df = _first_df(
                    _read_csv(d / f"comparison_register_results_{peripheral_name}.csv"),
                    _read_csv(d / "info" / "peripheral_comparisons" / f"comparison_register_results_{peripheral_name}.csv"),
                )
                if reg_df is not None and not reg_df.empty:
                    for _, rr in reg_df.iterrows():
                        register_rows.append(
                            {
                                "run_name": cfg.run_name,
                                "run_label": short_name(cfg.run_name),
                                "vs_type": cfg.vs_type,
                                "vs_label": short_name(cfg.vs_type),
                                "embeddings": cfg.embeddings,
                                "pages_after": cfg.pages_after,
                                "table_pages_only_expansion": cfg.table_pages_only_expansion,
                                "peripheral": rr.get("peripheral"),
                                "register": rr.get("register"),
                                "register_found": rr.get("register_found"),
                                "correct": rr.get("correct"),
                                "wrong": rr.get("wrong"),
                                "missing": rr.get("missing"),
                                "total_facts": rr.get("total_facts"),
                                "accuracy": rr.get("accuracy"),
                            }
                        )

                err_df = _first_df(
                    _read_csv(d / f"comparison_fact_errors_{peripheral_name}.csv"),
                    _read_csv(d / "info" / "peripheral_comparisons" / f"comparison_fact_errors_{peripheral_name}.csv"),
                )
                if err_df is not None and not err_df.empty:
                    for _, er in err_df.iterrows():
                        error_rows.append(
                            {
                                "run_name": cfg.run_name,
                                "run_label": short_name(cfg.run_name),
                                "vs_type": cfg.vs_type,
                                "vs_label": short_name(cfg.vs_type),
                                "embeddings": cfg.embeddings,
                                "pages_after": cfg.pages_after,
                                "table_pages_only_expansion": cfg.table_pages_only_expansion,
                                "error_type": er.get("error_type"),
                                "peripheral": er.get("peripheral"),
                                "register": er.get("register"),
                                "field_name": er.get("field_name"),
                                "key": er.get("key"),
                                "correct_value": er.get("correct_value"),
                                "generated_value": er.get("generated_value"),
                            }
                        )
        elif not combined_used:
            comparison = _load_json(d / "comparison_results.json") or _load_json(d / "info" / "comparison_results.json")
            if isinstance(comparison, dict):
                found_acc = comparison.get("found_accuracy") if comparison.get("found_accuracy") is not None else comparison.get("accuracy")
                row.update(
                    {
                        "registers_found": comparison.get("registers_found"),
                        "total_registers": comparison.get("total_registers"),
                        "correct": comparison.get("correct"),
                        "wrong": comparison.get("wrong"),
                        "missing": comparison.get("missing"),
                        "total_facts": comparison.get("total_facts"),
                        "found_accuracy": found_acc,
                        "correct_all": comparison.get("correct_all"),
                        "wrong_all": comparison.get("wrong_all"),
                        "missing_all": comparison.get("missing_all"),
                        "total_facts_all": comparison.get("total_facts_all"),
                        "complete_accuracy": comparison.get("complete_accuracy"),
                        "coverage": comparison.get("coverage"),
                        "accuracy": found_acc,
                    }
                )
            else:
                # Try to derive from register-level CSV if JSON is missing.
                reg_df = _first_df(
                    _read_csv(d / "comparison_register_results.csv"),
                    _read_csv(d / "info" / "comparison_register_results.csv"),
                )
                row.update(_derive_accuracy_from_register_results(reg_df if reg_df is not None else pd.DataFrame()))

            # Register-level table (if present)
            reg_df = _first_df(
                _read_csv(d / "comparison_register_results.csv"),
                _read_csv(d / "info" / "comparison_register_results.csv"),
            )
            if reg_df is not None and not reg_df.empty:
                for _, rr in reg_df.iterrows():
                    register_rows.append(
                        {
                            "run_name": cfg.run_name,
                            "run_label": short_name(cfg.run_name),
                            "vs_type": cfg.vs_type,
                            "vs_label": short_name(cfg.vs_type),
                            "embeddings": cfg.embeddings,
                            "pages_after": cfg.pages_after,
                            "table_pages_only_expansion": cfg.table_pages_only_expansion,
                            "metadata_filter": cfg.metadata_filter,
                            "peripheral": rr.get("peripheral"),
                            "register": rr.get("register"),
                            "register_found": rr.get("register_found"),
                            "correct": rr.get("correct"),
                            "wrong": rr.get("wrong"),
                            "missing": rr.get("missing"),
                            "total_facts": rr.get("total_facts"),
                            "accuracy": rr.get("accuracy"),
                        }
                    )

            # Fact-level errors (if present)
            err_df = _first_df(
                _read_csv(d / "comparison_fact_errors.csv"),
                _read_csv(d / "info" / "comparison_fact_errors.csv"),
            )
            if err_df is not None and not err_df.empty:
                for _, er in err_df.iterrows():
                    error_rows.append(
                        {
                            "run_name": cfg.run_name,
                            "run_label": short_name(cfg.run_name),
                            "vs_type": cfg.vs_type,
                            "vs_label": short_name(cfg.vs_type),
                            "embeddings": cfg.embeddings,
                            "pages_after": cfg.pages_after,
                            "table_pages_only_expansion": cfg.table_pages_only_expansion,
                            "metadata_filter": cfg.metadata_filter,
                            "error_type": er.get("error_type"),
                            "peripheral": er.get("peripheral"),
                            "register": er.get("register"),
                            "field_name": er.get("field_name"),
                            "key": er.get("key"),
                            "correct_value": er.get("correct_value"),
                            "generated_value": er.get("generated_value"),
                        }
                    )

            # Single-peripheral run convenience
            if cfg.peripheral:
                row["peripheral_count"] = 1
                row["peripherals"] = cfg.peripheral
            elif "peripheral_count" not in row:
                row["peripheral_count"] = None
                row["peripherals"] = None
            if row.get("peripheral_count"):
                pc = float(row["peripheral_count"])
                if row.get("usage_total_tokens_sum") is not None:
                    row["usage_total_tokens_mean"] = float(row["usage_total_tokens_sum"]) / pc
                if row.get("timing_total_time_sum") is not None:
                    row["timing_total_time_mean"] = float(row["timing_total_time_sum"]) / pc

        run_rows.append(row)

    df_runs = pd.DataFrame(run_rows)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Apply optional filtering
    df_runs_all = df_runs
    df_runs_filtered = _apply_filters(df_runs_all, args.min_accuracy, args.max_timing, args.max_usage)
    filters_active = any(v is not None for v in (args.min_accuracy, args.max_timing, args.max_usage))

    selected_run_names = set(df_runs_filtered["run_name"].tolist()) if not df_runs_filtered.empty else set()
    df_regs_all = pd.DataFrame(register_rows)
    df_errs_all = pd.DataFrame(error_rows)
    df_regs_filtered = df_regs_all[df_regs_all["run_name"].isin(selected_run_names)].copy() if not df_regs_all.empty else df_regs_all
    df_errs_filtered = df_errs_all[df_errs_all["run_name"].isin(selected_run_names)].copy() if not df_errs_all.empty else df_errs_all

    # Write tables
    # Under the new layout, each directory is a configuration, so these are config summaries.
    config_summary_all_path = output_dir / "config_summary_all.csv"
    df_runs_all.to_csv(config_summary_all_path, index=False)
    config_summary_path = None
    if filters_active:
        config_summary_path = output_dir / "config_summary.csv"
        df_runs_filtered.to_csv(config_summary_path, index=False)

    if not df_regs_all.empty:
        df_regs_all.to_csv(output_dir / "register_summary_all.csv", index=False)
    if filters_active and not df_regs_filtered.empty:
        df_regs_filtered.to_csv(output_dir / "register_summary.csv", index=False)

    if not df_errs_all.empty:
        df_errs_all.to_csv(output_dir / "fact_errors_all.csv", index=False)
    if filters_active and not df_errs_filtered.empty:
        df_errs_filtered.to_csv(output_dir / "fact_errors.csv", index=False)
    if not filters_active:
        # Avoid confusing stale filtered outputs from previous runs.
        for stale in [
            output_dir / "config_summary.csv",
            output_dir / "register_summary.csv",
            output_dir / "fact_errors.csv",
            # legacy names from older script versions
            output_dir / "run_summary.csv",
            output_dir / "run_summary_all.csv",
        ]:
            _delete_if_exists(stale)

    # Plots
    plots_dir = output_dir / "plots"
    # Remove old plot PNGs so renamed outputs don't accumulate.
    _clear_pngs(plots_dir)
    _clear_pngs(plots_dir / "heatmaps")
    # Under the new layout, each run directory is already a configuration folder that (may) contain
    # multiple peripherals. So we always plot/report over df_runs_filtered.
    plot_df = df_runs_filtered if (filters_active and not df_runs_filtered.empty) else df_runs_all
    plot_label_col = "config_label" if "config_label" in plot_df.columns else ("run_label" if "run_label" in plot_df.columns else "run_name")
    if not plot_df.empty and "accuracy" in plot_df.columns:
        # Prefer SUMs for cost/time comparisons on a fixed input set.
        usage_x = "usage_total_tokens_sum"
        timing_x = "timing_total_time_sum"
        usage_title = "total tokens"
        timing_title = "total time"
        _plot_scatter(
            plot_df,
            x=usage_x,
            y="accuracy",
            out_path=plots_dir / "accuracy_vs_total_tokens.png",
            title=f"{title_prefix}: accuracy vs {usage_title}",
            label_col=plot_label_col,
        )
        _plot_scatter(
            plot_df,
            x=timing_x,
            y="accuracy",
            out_path=plots_dir / "accuracy_vs_total_time.png",
            title=f"{title_prefix}: accuracy vs {timing_title}",
            label_col=plot_label_col,
        )

        _plot_heatmaps(plot_df, value_col="accuracy", out_dir=plots_dir / "heatmaps", title_prefix=title_prefix)
        if usage_x in plot_df.columns:
            _plot_heatmaps(plot_df, value_col=usage_x, out_dir=plots_dir / "heatmaps", title_prefix=title_prefix)
        if timing_x in plot_df.columns:
            _plot_heatmaps(plot_df, value_col=timing_x, out_dir=plots_dir / "heatmaps", title_prefix=title_prefix)

    # Text report
    report_path = output_dir / "top_configs.txt"
    _write_text_report(plot_df, report_path)

    print("Analysis written to:")
    print(f"  {output_dir}")
    print("Tables:")
    if config_summary_path:
        print(f"  {config_summary_path}")
    print(f"  {config_summary_all_path}")
    if filters_active and not df_regs_filtered.empty:
        print(f"  {output_dir / 'register_summary.csv'}")
    if not df_regs_all.empty:
        print(f"  {output_dir / 'register_summary_all.csv'}")
    if filters_active and not df_errs_filtered.empty:
        print(f"  {output_dir / 'fact_errors.csv'}")
    if not df_errs_all.empty:
        print(f"  {output_dir / 'fact_errors_all.csv'}")
    print("Plots:")
    print(f"  {plots_dir}")


if __name__ == "__main__":
    main()

