#!/usr/bin/env python3
"""Re-normalize existing access rows and drop vocabulary/notation non-diffs.

The access diff originally compared raw access tokens, so vocabulary variants
(`rw`, `write`), unicode hyphens, and CMSIS modify-notations (`rc-w1`,
`write-1-to-clear`, `read-clear` — all read-write) became spurious diffs. The
diff now canonicalizes via optimization_validator (the same map the validator
uses). This backfills that onto already-written review CSVs: for every `access`
row it re-canonicalizes both sides; if they now match it DROPS the row (it was
never a real diff); otherwise it rewrites the stored values to canonical. Then it
re-sorts into the canonical peripheral -> register -> field -> key order.

Access rows carry no human tp/fp marks, so nothing labeled is lost. Idempotent.
Stdlib + the (stdlib-only) access-notation module.

  python scripts/clean_access_vocab.py --dry-run
  python scripts/clean_access_vocab.py               # structure + access reviews
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import re
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
from optimization_validator.access_notation import canonical_access  # stdlib-only

_UNI_HYPHENS = str.maketrans({c: "-" for c in "‐‑‒–—−"})


def _norm_access(a) -> str:
    s = str(a or "").strip().lower().translate(_UNI_HYPHENS)
    return canonical_access(s) or s


# canonical peripheral -> register -> field -> key sort (matches report.py / the merge)
def _nat(s: str) -> tuple:
    return tuple((1, int(t)) if t.isdigit() else (0, t.lower())
                 for t in re.split(r"(\d+)", s or "") if t)


def _sort_key(r: dict) -> tuple:
    return (_nat(r.get("peripheral", "")), _nat(r.get("register", "")),
            _nat(r.get("field", "")), _nat(r.get("key", "")),
            r.get("svd_value") or "", r.get("generator_value") or "")


def clean_file(path: str, dry_run: bool) -> dict:
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        fields = list(rd.fieldnames or [])
        rows = list(rd)
    kept, dropped, canon = [], 0, 0
    for r in rows:
        if r.get("key") != "access":
            kept.append(r)
            continue
        ns, ng = _norm_access(r.get("svd_value")), _norm_access(r.get("generator_value"))
        if ns == ng:                      # vocabulary/notation non-diff -> drop
            dropped += 1
            continue
        if (ns, ng) != (r.get("svd_value"), r.get("generator_value")):
            r["svd_value"], r["generator_value"] = ns, ng
            canon += 1
        kept.append(r)
    if dropped or canon:
        kept.sort(key=_sort_key)
        if not dry_run:
            tmp = path + ".tmp"
            with open(tmp, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                for r in kept:
                    w.writerow({k: r.get(k, "") for k in fields})
            os.replace(tmp, path)
    return {"dropped": dropped, "canonicalized": canon, "rows": len(kept)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--glob", default="evaluation/*/*/*/*_{structure,access}_review.csv",
                    help="brace-glob of review CSVs (default: structure + access reviews)")
    args = ap.parse_args()

    patterns = []
    m = re.match(r"(.*)\{(.+)\}(.*)", args.glob)
    patterns = [f"{m.group(1)}{opt}{m.group(3)}" for opt in m.group(2).split(",")] if m else [args.glob]
    files = sorted({p for pat in patterns for p in glob.glob(os.path.join(_REPO, pat))})

    tot_d = tot_c = 0
    for path in files:
        res = clean_file(path, args.dry_run)
        if res["dropped"] or res["canonicalized"]:
            tot_d += res["dropped"]; tot_c += res["canonicalized"]
            print(f"  {os.path.relpath(path, _REPO):55} drop {res['dropped']:4}  canon {res['canonicalized']:4}")
    verb = "would drop" if args.dry_run else "dropped"
    print(f"\n{verb} {tot_d} vocabulary/notation non-diffs; canonicalized {tot_c} kept rows "
          f"across {len(files)} files")


if __name__ == "__main__":
    main()
