#!/usr/bin/env python3
"""Overview of a verified datasheet's annotation progress.

Reads a verified-datasheet CSV (the --out of annotate.py, which holds the full
SVD worklist plus whatever has been annotated) and reports:

  * peripherals covered / total           (touched, fully done, partial, untouched)
  * per-peripheral register completion %   (registers fully done / total)
  * overall cells done / all cells         (the "lines" total)

Usage:
    python3 verified_datasheet/overview.py verified_datasheet/stm/rm0041_stm32f100.csv
    python3 verified_datasheet/overview.py --sort name <csv>
"""
import argparse
import csv
import os
import sys
from collections import OrderedDict

# A cell counts as DONE when it carries a real annotation status. Pending cells have an
# empty status; 'derived' rows are dedup markers (not annotated); 'skipped' is left pending.
DONE = {"verified", "datasheet-ambiguous", "not-specified"}

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
def _c(code):
    return (lambda s: f"\033[{code}m{s}\033[0m") if _COLOR else (lambda s: str(s))
GREEN, YELLOW, RED, DIM, BOLD = _c("92"), _c("93"), _c("91"), _c("2"), _c("1")


def _pct_color(p):
    return GREEN if p >= 100 else YELLOW if p > 0 else RED


def bar(pct, width=20):
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def load(csv_path):
    """Return (peripherals, derived_markers).

    peripherals: OrderedDict[name] -> OrderedDict[register] -> {'total': n, 'done': n}
    derived_markers: list of (peripheral, prototype) dedup rows.
    """
    peripherals = OrderedDict()
    derived = []
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            status = (r.get("status") or "").strip()
            if status == "derived":
                derived.append((r.get("peripheral", ""), r.get("derived_from", "")))
                continue
            p, reg = r.get("peripheral", ""), r.get("register", "")
            if not p or not reg:
                continue
            regs = peripherals.setdefault(p, OrderedDict())
            cell = regs.setdefault(reg, {"total": 0, "done": 0})
            cell["total"] += 1
            # Done = a real status, or a filled correct_value (legacy CSVs carry values
            # with an empty status — annotate.py treats those as imported/verified).
            if status in DONE or (r.get("correct_value") or "").strip():
                cell["done"] += 1
    return peripherals, derived


def main():
    ap = argparse.ArgumentParser(description="Annotation-progress overview of a verified datasheet CSV.")
    ap.add_argument("csv", help="verified-datasheet CSV (annotate.py --out)")
    ap.add_argument("--sort", choices=["pct", "name"], default="pct",
                    help="order peripherals by completion %% (default, least-done first) or by name")
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        ap.error(f"no such file: {args.csv}")

    peripherals, derived = load(args.csv)
    if not peripherals:
        print("No worklist cells found (is this a verified-datasheet CSV?).")
        return

    # per-peripheral rollup
    rows = []
    tot_cells = done_cells = 0
    for p, regs in peripherals.items():
        p_cells = sum(c["total"] for c in regs.values())
        p_done = sum(c["done"] for c in regs.values())
        regs_total = len(regs)
        regs_done = sum(1 for c in regs.values() if c["done"] == c["total"])
        tot_cells += p_cells
        done_cells += p_done
        rows.append({
            "p": p, "regs_total": regs_total, "regs_done": regs_done,
            "reg_pct": 100 * regs_done / regs_total if regs_total else 0,
            "cells": p_cells, "cells_done": p_done,
        })

    touched = [r for r in rows if r["cells_done"] > 0]
    full = [r for r in rows if r["cells_done"] == r["cells"]]
    untouched = [r for r in rows if r["cells_done"] == 0]
    partial = [r for r in rows if 0 < r["cells_done"] < r["cells"]]

    if args.sort == "pct":
        rows.sort(key=lambda r: (r["reg_pct"], r["p"]))
    else:
        rows.sort(key=lambda r: r["p"])

    overall = 100 * done_cells / tot_cells if tot_cells else 0
    print(f"\n{BOLD(os.path.basename(args.csv))}")
    print(f"Peripherals:  {len(touched)}/{len(rows)} touched   "
          f"({GREEN(f'{len(full)} done')}, {YELLOW(f'{len(partial)} partial')}, "
          f"{RED(f'{len(untouched)} untouched')})"
          + (f"   {DIM(f'[+{len(derived)} derived markers]')}" if derived else ""))
    print(f"Cells:        {done_cells}/{tot_cells} done   "
          f"{_pct_color(overall)(f'{overall:.1f}%')}   {bar(overall)}\n")

    name_w = max(len(r["p"]) for r in rows)
    print(DIM(f"  {'peripheral':<{name_w}}  {'registers':>12}  {'':<20}  {'cells':>11}"))
    for r in rows:
        pc = _pct_color(r["reg_pct"])
        print(f"  {r['p']:<{name_w}}  "
              f"{r['regs_done']:>4}/{r['regs_total']:<4} {pc(f'{r['reg_pct']:>3.0f}%')}  "
              f"{pc(bar(r['reg_pct']))}  "
              f"{DIM(f'{r['cells_done']:>5}/{r['cells']:<5}')}")
    print()


if __name__ == "__main__":
    main()
