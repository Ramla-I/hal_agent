#!/usr/bin/env python3
"""Recover constraints filed under a peripheral that does not exist.

On TrustZone-capable families the reference manual has a security chapter
listing every register that can be marked secure. The generator reads that
chapter's heading as a peripheral -- `sec` -- and leaves the real peripheral
inside the register name:

    sec / adc1_awd2cr        should be    adc1 / awd2cr
    sec / hash_cr            should be    hash / cr

No SVD has a peripheral called `sec`, so every one of these is dropped at
injection as `peripheral_not_in_device`. Corpus-wide that is 737 of 991 such
drops, across RM0438 (L5), RM0481 (H5), RM0456 (U5) and RM0493 (WBA).

THE RULE, AND WHY IT CANNOT INVENT AN ATTRIBUTION

    peripheral is absent from the SVD
    AND register is "<prefix>_<rest>"
    AND <prefix> IS a peripheral in the SVD
      -> peripheral = <prefix>, register = <rest>

The third condition is the whole safety argument: the new name is read off the
device's own peripheral list, so a register whose prefix is not a real
peripheral is left exactly as it was. Nothing is guessed.

MOST OF IT IS REDUNDANT, WHICH IS THE REASSURING PART

About 71% of these restate a constraint the same run already extracted
correctly from the peripheral chapters -- the security chapter is largely a
cross-reference table. So this recovers coverage rather than correcting wrong
results, and duplicates are dropped rather than double-counted.

Usage:
    python scripts/reattribute_peripherals.py --review <dir>            # dry run
    python scripts/reattribute_peripherals.py --review <dir> --apply
"""

import argparse
import collections
import json
import re
import shutil
import sys
from pathlib import Path

PHASE1D = Path("/home/ramla/hal_agent-phase-1d")
_PERIPH_RE = re.compile(r"<peripheral[^>]*>.*?<name>([^<]+)</name>", re.S)


def svd_peripherals(rm: str) -> set:
    """Every peripheral name the manual's SVDs declare, lowercased."""
    out = set()
    for svd in (PHASE1D / "devices" / "stm" / rm / "svd").glob("*.svd"):
        try:
            out.update(m.lower() for m in _PERIPH_RE.findall(
                svd.read_text(errors="ignore")))
        except OSError:
            continue
    return out


def dedup_key(entry: dict) -> tuple:
    """What makes two review entries the same rule.

    NOT the `id`: it is derived from the source file, so the security-chapter
    copy and the peripheral-chapter copy of one rule always differ."""
    c = entry.get("constraint") or {}
    return (entry.get("peripheral"), entry.get("register"),
            c.get("kind"), c.get("target_operation"),
            " ".join((c.get("datasheet_text") or "").split()))


def process(path: Path, periphs: set) -> dict:
    entries = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    seen = {dedup_key(e) for e in entries
            if (e.get("peripheral") or "").lower() in periphs}

    kept, stats = [], collections.Counter()
    for e in entries:
        per = (e.get("peripheral") or "").lower()
        reg = (e.get("register") or "").lower()
        if per in periphs:
            kept.append(e)
            stats["untouched"] += 1
            continue
        if "_" not in reg:
            kept.append(e)
            stats["left_alone_no_prefix"] += 1
            continue
        prefix, rest = reg.split("_", 1)
        if prefix not in periphs:
            kept.append(e)
            stats["left_alone_prefix_unknown"] += 1
            continue
        moved = dict(e)
        moved["peripheral"], moved["register"] = prefix, rest
        moved["reattributed_from"] = {"peripheral": e.get("peripheral"),
                                      "register": e.get("register")}
        k = dedup_key(moved)
        if k in seen:
            stats["dropped_duplicate"] += 1
            continue
        seen.add(k)
        kept.append(moved)
        stats["reattributed"] += 1
    return {"entries": kept, "stats": stats, "before": len(entries)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--review", default=str(PHASE1D / "evaluation" / "stm"),
                    help="directory holding <rm>/<run>/<rm>_constraints_review.jsonl")
    ap.add_argument("--rm", action="append", default=[],
                    help="restrict to these manuals (default: all found)")
    ap.add_argument("--apply", action="store_true",
                    help="write the files (a .bak copy is kept)")
    args = ap.parse_args()

    root = Path(args.review)
    files = sorted(root.glob("*/*/*_constraints_review.jsonl"))
    if args.rm:
        files = [f for f in files if any(r in f.name for r in args.rm)]
    if not files:
        sys.exit(f"no constraint review files under {root}")

    grand = collections.Counter()
    touched = 0
    print("%-9s %8s %8s %8s %8s" % ("manual", "entries", "re-attr", "dupes", "after"))
    for f in files:
        rm = f.name.split("_constraints_review")[0]
        periphs = svd_peripherals(rm)
        if not periphs:
            print("%-9s  (no SVD found — skipped)" % rm)
            continue
        r = process(f, periphs)
        s = r["stats"]
        if not (s["reattributed"] or s["dropped_duplicate"]):
            continue
        touched += 1
        grand.update(s)
        print("%-9s %8d %8d %8d %8d" % (rm, r["before"], s["reattributed"],
                                        s["dropped_duplicate"], len(r["entries"])))
        if args.apply:
            shutil.copy2(f, f.with_suffix(".jsonl.bak"))
            f.write_text("".join(json.dumps(e) + "\n" for e in r["entries"]))

    print("\nmanuals affected      : %d" % touched)
    print("constraints recovered : %d" % grand["reattributed"])
    print("duplicates dropped    : %d" % grand["dropped_duplicate"])
    print("left alone (guarded)  : %d" % (grand["left_alone_no_prefix"]
                                          + grand["left_alone_prefix_unknown"]))
    print("\n" + ("WROTE the files (.bak kept)" if args.apply
                  else "DRY RUN — pass --apply to write"))


if __name__ == "__main__":
    main()
