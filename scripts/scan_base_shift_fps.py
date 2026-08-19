#!/usr/bin/env python3
"""Find TP'd `address_offset` rows that are actually baseAddress-convention FPs.

The generator reports register offsets relative to the datasheet's peripheral
base; an SVD may instead bake part of that offset into `baseAddress` (e.g. STM32
BKP: base 0x40006C04 + offset 0x0 == datasheet base 0x40006C00 + offset 0x4).
Then every register of the peripheral differs from the datasheet by the SAME
constant, yet the *absolute* address matches — a representation difference, not a
bug. This scans the structure reviews for peripherals whose TP address_offset
rows are a uniform nonzero shift, and (when the SVD is present) prints the
peripheral's `baseAddress` so the shift can be confirmed by eye (its low bits
usually equal the shift). These rows should NOT be submitted.

  python scripts/scan_base_shift_fps.py                     # all evaluation/stm reviews
  python scripts/scan_base_shift_fps.py evaluation/stm/rm0041/1/rm0041_structure_review.csv
"""
from __future__ import annotations

import csv
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# match the classifier in applications/bug_finding/classify.py
_MIN_REGS = 3
_ALIGN = 0x100


def _as_int(v: str | None):
    v = (v or "").strip()
    if re.fullmatch(r"0x[0-9a-fA-F]+", v):
        return int(v, 16)
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return None


def _svd_base_addresses(rm: str) -> dict[str, list[int]]:
    """peripheral(upper) -> [baseAddress ...] across the RM's SVD files."""
    bases: dict[str, list[int]] = defaultdict(list)
    for svd in glob.glob(os.path.join(_REPO, "devices", "stm", rm, "svd", "*.svd")):
        try:
            root = ET.parse(svd).getroot()
        except ET.ParseError:
            continue
        for p in root.iter("peripheral"):
            name = (p.findtext("name") or "").upper()
            base = _as_int(p.findtext("baseAddress"))
            if name and base is not None:
                bases[name].append(base)
    return bases


def scan(review: str) -> tuple[list[str], list[str]]:
    with open(review, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)
                if (r.get("tp_fp") or "").strip().upper() == "TP"
                and (r.get("key") or "").strip() == "address_offset"]
    if not rows:
        return [], []
    rm = (rows[0].get("RM") or os.path.basename(review).split("_")[0])
    bases = _svd_base_addresses(rm)

    by_per: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for r in rows:
        s, g = _as_int(r.get("svd_value")), _as_int(r.get("generator_value"))
        if s is not None and g is not None:
            by_per[(r.get("peripheral") or "")].append((r.get("register") or "", g - s))

    dropped: list[str] = []   # base convention proven: the classifier auto-drops as FP
    keep: list[str] = []      # uniform shift but base doesn't prove it — verify (may be real)
    for per, regs in sorted(by_per.items()):
        deltas = {d for _, d in regs}
        if len(deltas) != 1:
            continue
        delta = next(iter(deltas))
        if delta == 0:
            continue
        base_list = sorted(set(bases.get(per.upper(), [])))
        base_str = ", ".join(hex(b) for b in base_list) or "?"
        # same proof the classifier uses: a base is a convention artifact iff it is
        # non-aligned and removing the shift re-aligns it (BKP 0x40006C04 - 4).
        convention = (len(regs) >= _MIN_REGS and abs(delta) < _ALIGN and base_list
                      and all(b % _ALIGN != 0 and (b - delta) % _ALIGN == 0 for b in base_list))
        sign = "+" if delta > 0 else "-"
        head = (f"  {rm:8} {per.upper():10} shift={sign}0x{abs(delta):X} "
                f"regs={len(regs)} base={base_str}")
        body = f"           registers: {', '.join(rg for rg, _ in regs)}"
        (dropped if convention else keep).extend([head, body])
    return dropped, keep


def main() -> None:
    reviews = sys.argv[1:] or sorted(
        glob.glob(os.path.join(_REPO, "evaluation", "stm", "*", "*", "*_structure_review.csv")))
    dropped: list[str] = []
    keep: list[str] = []
    for rv in reviews:
        d, k = scan(rv)
        dropped += d
        keep += k

    print("=== Uniform whole-peripheral address shifts in TP'd address_offset rows ===\n")
    print("Base convention PROVEN — the classifier DROPS these as FPs")
    print("(non-aligned baseAddress absorbs the shift; absolute address matches — do NOT submit):\n")
    print("\n".join(dropped) if dropped else "  none")
    print("\nUniform shift but base does NOT prove a convention — the classifier KEEPS these")
    print("(aligned base => likely a real bug, e.g. an SVD carrying another variant's bank — verify each):\n")
    print("\n".join(keep) if keep else "  none")
    nd = sum(1 for l in dropped if l.startswith("  rm"))
    nk = sum(1 for l in keep if l.startswith("  rm"))
    print(f"\n{nd} auto-dropped, {nk} to-verify across {len(reviews)} review(s)")


if __name__ == "__main__":
    main()
