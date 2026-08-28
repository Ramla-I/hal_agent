#!/usr/bin/env python3
"""Bubble scatter of register-structure bugs per peripheral family.

Three quantities per peripheral in one figure:
  x (log)      = distinct register types the generator produced for the family
  y            = distinct TP bug types (array-collapsed, base-convention excluded)
  bubble area  = number of RMs the peripheral appears in

The point: bugs rise with register count (peripheral size); bubble size (how common
the peripheral is) shows no pattern -- rarity does not predict bugs.

  python scripts/plot_peripheral_bugs.py [out.pdf]
"""
import csv, glob, math, os, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdfwriter import Pdf, _HELV_ADV  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fam(per):
    per = (per or "").lower()
    return "gpio" if per.startswith("gpio") else re.sub(r"\d+$", "", per)


def rfam(reg):
    return re.sub(r"\d+$", "", (reg or "").lower())


def collect():
    btypes = defaultdict(set)
    for f in glob.glob(os.path.join(_REPO, "evaluation/stm/*/*/*_structure_review.csv")):
        for r in csv.DictReader(open(f, newline="")):
            if (r.get("tp_fp") or "").strip() != "TP":
                continue
            if (r.get("Notes") or "").strip() == "GEN_AND_SVD_CORRECT":
                continue
            btypes[fam(r.get("peripheral"))].add(
                (rfam(r.get("register")), (r.get("field") or "").lower(), r.get("key")))
    rms, regs = defaultdict(set), defaultdict(set)
    for run in glob.glob(os.path.join(_REPO, "agent_output/stm/*/1")):
        rm = run.split("/")[-2]
        for fn in os.listdir(run):
            if "_" in fn and not os.path.isdir(os.path.join(run, fn)):
                per, reg = fn.split("_", 1)
                rms[fam(per)].add(rm)
                regs[fam(per)].add(rfam(reg))
    return [(fm, len(b), len(rms.get(fm, set())), len(regs.get(fm, set())))
            for fm, b in btypes.items() if regs.get(fm)]


def draw(data, path):
    W, H = 5.4 * 72, 3.7 * 72
    p = Pdf(W, H)
    L, Rm, Tm, Bm = 34.0, 96.0, 16.0, 34.0     # margins (Rm leaves room for the size legend)
    x0, x1, y0, y1 = L, W - Rm, Bm, H - Tm

    regs = [d[3] for d in data]
    ymax = max(d[1] for d in data) + 2
    xmin, xmax = math.log10(2), math.log10(max(regs) * 1.25)

    def X(r):
        return x0 + (math.log10(r) - xmin) / (xmax - xmin) * (x1 - x0)

    def Y(b):
        return y0 + b / ymax * (y1 - y0)

    def dia(nr):
        return 5.0 + 13.0 * math.sqrt(nr / 53.0)

    # grid + ticks
    p.fill("#5c6675")
    for xt in [3, 10, 30, 100, 300, 800]:
        if not (2 <= xt <= max(regs) * 1.25):
            continue
        gx = X(xt)
        p.stroke("#e7ebf1")
        p.line(gx, y0, gx, y1, 0.5)
        p.fill("#8a93a2")
        p.text(gx, y0 - 11, str(xt), 6.5, "F1", "middle")
    for yt in range(0, int(ymax) + 1, 5):
        gy = Y(yt)
        p.stroke("#e7ebf1")
        p.line(x0, gy, x1, gy, 0.5)
        p.fill("#8a93a2")
        p.text(x0 - 5, gy - 2, str(yt), 6.5, "F1", "end")
    # axes
    p.stroke("#b7bfca")
    p.line(x0, y0, x1, y0, 0.7)
    p.line(x0, y0, x0, y1, 0.7)
    p.fill("#5c6675")
    p.text((x0 + x1) / 2, y0 - 24, "distinct register types in the peripheral (log scale)", 7.4, "F1", "middle")
    p.rot_text(x0 - 20, (y0 + y1) / 2 - 34, "distinct bug types", 7.4, 90.0, "F1")

    # bubbles: biggest first so small ones stay visible on top
    for fm, nb, nr, ng in sorted(data, key=lambda d: -d[2]):
        cx, cy, d = X(ng), Y(nb), dia(nr)
        p.fill("#9cc3e6")
        p.stroke("#2f6fae")
        p.cap_rect(cx - d / 2, cy - d / 2, d, d, d / 2, 0.7)
    # labels on top of everything (>=2 bugs), placed to the right of the bubble
    for fm, nb, nr, ng in data:
        if nb < 2:
            continue
        cx, cy, d = X(ng), Y(nb), dia(nr)
        p.fill("#1b212b")
        p.text(cx + d / 2 + 2.0, cy - 2.2, fm, 5.6, "F1")

    # bubble-size legend (right margin)
    lx, ly = x1 + 20, y1 - 6
    p.fill("#5c6675")
    p.text(lx, ly + 10, "# RMs", 6.6, "F1")
    for nr in (1, 10, 30, 53):
        d = dia(nr)
        p.fill("#9cc3e6")
        p.stroke("#2f6fae")
        p.cap_rect(lx, ly - d, d, d, d / 2, 0.7)
        p.fill("#5c6675")
        p.text(lx + 20, ly - d / 2 - 2, str(nr), 6.2, "F1")
        ly -= d + 8

    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(p.to_bytes())


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_REPO, "docs/figures/peripheral_bugs.pdf")
    data = collect()
    draw(data, out)
    print("wrote", out, "(%d peripheral families)" % len(data))


if __name__ == "__main__":
    main()
