#!/usr/bin/env python3
"""Statistics on the hand-labelled structure-review files, focused on the validator's
false positives and whether they fit a mechanical pattern that could be filtered out
BEFORE the validator runs.

Labels used (columns in {rm}_structure_review.csv):
  validator_verdict  what the validator decided (TP/FP/blank)
  tp_fp              YOUR label (TP/FP/blank)

Headline counts:
  TPs  = rows you marked TP
  FPs  = validator said TP but you marked FP  (the validator's misses)

The two mechanical rules below (width_variant, placeholder) are treated as a
PRE-FILTER: the reported FP numbers and the per-bug-type breakdown ALWAYS exclude
them (they should never reach the validator). The reporting categories are the
bug types (address_offset, reset_value, size, bit_offset, bit_width).

The FPs are screened by two candidate pre-filter rules:
  A. width-variant registers — the SVD gives a byte/half-word alias (dr8, rxdr16, …)
     its own narrower size/reset/bit-width, but the generator carries the base
     register's full-width values. Signature: register name ends in 8/16/32 and the
     SVD value equals that width (or the SVD reset fits in that width while the
     generator's is wider).
  B. generator placeholder mask — the generator emitted a literal `0x..X..` template
     (e.g. 0x0000XXXX) and the SVD value is a VALID instantiation of it (every fixed
     nibble matches, so 0x0 is one of the allowed values). These never should have
     reached the validator.
  other — everything else (left for inspection).

For each rule we also report "TP-collateral": rows you marked TP that the rule would
also catch — these are the rule's risk (a real bug it would wrongly drop, or a label
worth re-checking). A safe pre-filter wants this near zero.

  python scripts/analyze_review_fps.py
  python scripts/analyze_review_fps.py --dump width_variant   # list rows in a category
  python scripts/analyze_review_fps.py --dump placeholder --dump-tp   # its TP-collateral
"""
from __future__ import annotations

import argparse, csv, glob, os, re
from collections import Counter, defaultdict

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GLOB = os.path.join(_REPO, "evaluation", "stm", "*", "*", "*_structure_review.csv")
_KEYS = ("address_offset", "reset_value", "size", "bit_offset", "bit_width")


def num(v):
    v = (v or "").strip()
    if re.fullmatch(r"0x[0-9a-fA-F]+", v):
        return int(v, 16)
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return None


def is_width_variant(r) -> bool:
    reg = (r.get("register") or "").strip().lower()
    key = (r.get("key") or "").strip()
    m = re.match(r"^(.*[a-z])(8|16|32)$", reg)   # base ends in a letter, then a width suffix
    if not m or key not in ("size", "reset_value", "bit_width"):
        return False
    n = int(m.group(2))
    sv, gv = num(r.get("svd_value")), num(r.get("generator_value"))
    if key in ("size", "bit_width"):
        return sv == n and (gv is None or gv > n)
    return sv is not None and gv is not None and sv < (1 << n) <= gv   # reset fits in n bits, gen wider


def is_placeholder(r) -> bool:
    g = (r.get("generator_value") or "").strip().replace(" ", "")
    m = re.fullmatch(r"0x([0-9a-fA-FX]+)", g)
    if not m or "X" not in m.group(1).upper():
        return False
    body = m.group(1).upper()
    sv = num(r.get("svd_value"))
    if sv is None or sv >= (1 << (4 * len(body))):
        return False
    fixed_mask = fixed_val = 0
    for i, ch in enumerate(reversed(body)):
        if ch != "X":
            fixed_mask |= 0xF << (4 * i)
            fixed_val |= int(ch, 16) << (4 * i)
    return (sv & fixed_mask) == (fixed_val & fixed_mask)


_RULES = [("width_variant", is_width_variant), ("placeholder", is_placeholder)]


def category(r) -> str:
    for name, fn in _RULES:
        if fn(r):
            return name
    return "other"


def _row_str(r) -> str:
    loc = f"{r.get('peripheral')}.{r.get('register')}" + (f".{r['field']}" if (r.get('field') or '').strip() else "")
    return f"{r.get('RM'):8} {loc:34} {r.get('key'):15} svd={r.get('svd_value')!s:12} gen={r.get('generator_value')}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--glob", default=_GLOB)
    ap.add_argument("--dump", action="append", default=[], help="list FP rows in a category (repeatable)")
    ap.add_argument("--dump-tp", action="store_true", help="with --dump, list that rule's TP-collateral instead")
    args = ap.parse_args()

    rows = []
    for f in sorted(glob.glob(args.glob)):
        rows.extend(csv.DictReader(open(f, newline="", encoding="utf-8")))

    def vv(r): return (r.get("validator_verdict") or "").strip() or "-"
    def ul(r): return (r.get("tp_fp") or "").strip() or "-"

    labelled = [r for r in rows if ul(r) in ("TP", "FP")]
    tps = [r for r in rows if ul(r) == "TP"]
    fps = [r for r in rows if vv(r) == "TP" and ul(r) == "FP"]   # validator TP, you FP

    print(f"structure-review rows: {len(rows)}   you labelled: {len(labelled)} "
          f"(TP={len(tps)}, FP={sum(ul(r)=='FP' for r in rows)})\n")

    print("validator_verdict x your label:")
    grid = Counter((vv(r), ul(r)) for r in rows)
    for (v, u), n in sorted(grid.items(), key=lambda x: -x[1]):
        if u in ("TP", "FP"):
            print(f"   validator={v:3}  you={u:3}  {n}")

    # The two mechanical rules are a PRE-FILTER: their FPs are always removed from
    # the reported FP numbers (they should never reach the validator). Reported
    # categories are the bug types (address_offset, reset_value, ...).
    cats = defaultdict(list)
    for r in fps:
        cats[category(r)].append(r)
    fps_net = cats["other"]

    print("\n" + "=" * 60)
    print(f"TPs (you marked TP):                        {len(tps)}")
    print(f"FPs (validator=TP, you=FP), raw:            {len(fps)}")
    print(f"  - width_variant (pre-filtered out):       {len(cats['width_variant'])}")
    print(f"  - placeholder   (pre-filtered out):       {len(cats['placeholder'])}")
    print(f"FPs after removing the two categories:      {len(fps_net)}")
    print("=" * 60)

    print("\nby bug type  (FP excludes width_variant + placeholder):")
    print(f"  {'bug type':16}{'TP':>7}{'FP':>7}")
    for k in _KEYS:
        tp_n = sum((r.get("key") or "") == k for r in tps)
        fp_n = sum((r.get("key") or "") == k for r in fps_net)
        if tp_n or fp_n:
            print(f"  {k:16}{tp_n:>7}{fp_n:>7}")
    print(f"  {'TOTAL':16}{len(tps):>7}{len(fps_net):>7}")

    # TP-collateral: your-TP rows each rule would also catch (its risk)
    print("\nTP-collateral (rows you marked TP that a rule would also drop — re-check these):")
    for name, fn in _RULES:
        hits = [r for r in tps if fn(r)]
        print(f"  {name}: {len(hits)}")
        for r in hits:
            print("     " + _row_str(r))

    # optional dumps
    rule_fns = dict(_RULES)
    for name in args.dump:
        if args.dump_tp:
            if name not in rule_fns:
                print(f"\n--- '{name}' has no rule; --dump-tp only works for {list(rule_fns)} ---")
                continue
            pool = [r for r in tps if rule_fns[name](r)]
        else:
            pool = cats.get(name, [])
        print(f"\n--- {'TP-collateral' if args.dump_tp else 'FP rows'} in '{name}' ({len(pool)}) ---")
        for r in pool:
            print("  " + _row_str(r))


if __name__ == "__main__":
    main()
