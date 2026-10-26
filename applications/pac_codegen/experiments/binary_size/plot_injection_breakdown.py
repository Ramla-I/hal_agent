#!/usr/bin/env python3
"""Per-PAC bar figure: injected SLOC split into the three categories.

One horizontal stacked bar per PAC crate, reconciled across all the devices we
injected (one per reference manual): the shared generic.rs header (A) and the
marker walk (B) are counted ONCE per crate; the constraint-encoding code (C) is
summed over the crate's devices. Each part is drawn with a distinct COLOUR and a
distinct HATCH pattern (A solid, B forward diagonal, C back diagonal), so the
figure survives greyscale printing. The number at the end of each bar is the
count of distinct register-access constraints that crate enforces (the top bar
carries the word "constraints" so the column is self-explanatory).

No title or caption. Key sits below the x-axis. Reads the numbers from
injection_loc.json (per_pac, from measure_injection_loc.py) and renders a PDF via
the same pdfwriter used for the cascade figure.

    python plot_injection_breakdown.py                 # SLOC (default)
    python plot_injection_breakdown.py --raw           # raw added lines
    python plot_injection_breakdown.py --out F --width IN
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "scripts"))
from pdfwriter import Pdf, _HELV_ADV                       # noqa: E402

A_FILL, A_HATCH = "#8aa4c8", ()            # generic.rs   : solid
B_FILL, B_HATCH = "#e08a3c", (45,)         # marker impls : forward diagonal
C_FILL, C_HATCH = "#3aa06b", (135,)        # constraints  : back diagonal
INK, GRID, AXIS, HAIR = "#333333", "#e6e9ee", "#8a94a2", "#ffffff"

# font sizes (pt)
F_CRATE, F_NUM, F_TICK, F_AXIS, F_LEGT, F_LEG = 10.0, 9.0, 9.0, 12.0, 11.0, 10.0


def fmt_tick(t):
    return "0" if t == 0 else f"{t // 1000}k"


def build(per_pac, metric, out, width_in):
    sk = {"sloc": ("A_sloc", "B_sloc", "C_sloc"),
          "raw":  ("A_raw", "B_raw", "C_raw")}[metric]
    rows = sorted(({"pac": p["pac"].replace("stm32", ""),
                    "A": p[sk[0]], "B": p[sk[1]], "C": p[sk[2]],
                    "nc": p.get("n_constraints", 0),
                    "tot": p[sk[0]] + p[sk[1]] + p[sk[2]]}
                   for p in per_pac), key=lambda r: -r["tot"])
    n = len(rows)

    W = width_in * 72.0
    ML, MR = 56.0, 50.0                    # ML: y-label + crate names; MR: bar-end counts
    pw = W - ML - MR
    BH, ROW = 12.0, 17.0
    TOP_PAD = 10.0
    AX_Y = 82.0                            # x-axis height: leaves room BELOW for the key
    plot_h = n * ROW
    plot_top = AX_Y + plot_h
    H = plot_top + TOP_PAD

    step = 20000
    axis_max = max(step, math.ceil(max(r["tot"] for r in rows) / step) * step)
    ticks = list(range(0, axis_max + 1, step))

    def xpix(v):
        return ML + pw * v / axis_max

    p = Pdf(W, H)
    yb = 2.8                               # text baseline offset inside a bar row

    p.stroke(GRID)
    for t in ticks[1:]:
        p.line(xpix(t), AX_Y, xpix(t), plot_top, 0.6)

    # bars, largest at top; distinct-constraint count at the bar end
    for i, r in enumerate(rows):
        by = plot_top - (i + 1) * ROW + (ROW - BH) / 2.0
        x = ML
        for val, fill, hatch in ((r["A"], A_FILL, A_HATCH),
                                 (r["B"], B_FILL, B_HATCH),
                                 (r["C"], C_FILL, C_HATCH)):
            w = pw * val / axis_max
            if w <= 0:
                continue
            p.fill(fill)
            p.stroke(HAIR)
            p.rect(x, by, w, BH, 0.6)
            p.hatch(x, by, w, BH, hatch, gap=2.7, lw=0.5)
            x += w
        p.fill(INK)
        p.text(ML - 5, by + yb, r["pac"], F_CRATE, "F1", "end")
        num = f"{r['nc']:,} constraints" if i == 0 else f"{r['nc']:,}"
        p.text(x + 4, by + yb, num, F_NUM, "F1", "start")

    # x-axis
    p.stroke(AXIS)
    p.line(ML, AX_Y, ML + pw, AX_Y, 0.9)
    for t in ticks:
        p.stroke(AXIS)
        p.line(xpix(t), AX_Y, xpix(t), AX_Y - 4.0, 0.9)
        p.fill("#555555")
        p.text(xpix(t), AX_Y - 15.0, fmt_tick(t), F_TICK, "F1", "middle")
    p.fill(INK)
    unit = "Added lines of code (SLOC)" if metric == "sloc" else "Added lines of code"
    p.text(ML + pw / 2.0, AX_Y - 30.0, unit, F_AXIS, "F1", "middle")

    # y-axis label (left, rotated, centred on the plot)
    plot_mid = (AX_Y + plot_top) / 2.0
    lwdt = 0.60 * F_AXIS * len("stm32 PAC crates")
    p.fill(INK)
    p.rot_text(16.0, plot_mid + lwdt / 2.0, "stm32 PAC crates", F_AXIS, 90.0, "F1")

    # key BELOW the x-axis: a title line, then the swatches
    p.fill(INK)
    p.text(ML, AX_Y - 48.0, "Added code, by category:", F_LEGT, "F1", "start")
    sw_cy = AX_Y - 66.0
    lx = ML
    for label, fill, hatch in (("generic.rs", A_FILL, A_HATCH),
                               ("marker impls", B_FILL, B_HATCH),
                               ("constraint code", C_FILL, C_HATCH)):
        p.fill(fill)
        p.stroke(HAIR)
        p.rect(lx, sw_cy - 5.0, 10.0, 10.0, 0.6)
        p.hatch(lx, sw_cy - 5.0, 10.0, 10.0, hatch, gap=2.7, lw=0.5)
        p.fill(INK)
        p.text(lx + 13.0, sw_cy - 3.2, label, F_LEG, "F1", "start")
        lx += 13.0 + _HELV_ADV * F_LEG * len(label) + 22.0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(p.to_bytes())
    return rows, axis_max


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", action="store_true", help="raw added lines instead of SLOC")
    ap.add_argument("--out", default=str(REPO / "docs" / "figures" / "injection_breakdown.pdf"))
    ap.add_argument("--width", type=float, default=7.0, help="figure width in inches")
    a = ap.parse_args()
    data = json.load(open(HERE / "injection_loc.json"))
    metric = "raw" if a.raw else "sloc"
    rows, amax = build(data["per_pac"], metric, Path(a.out), a.width)
    print(f"wrote {a.out}  ({len(rows)} crates, metric={metric}, axis_max={amax:,}, "
          f"total added={sum(r['tot'] for r in rows):,}, "
          f"total constraints={sum(r['nc'] for r in rows):,})")


if __name__ == "__main__":
    main()
