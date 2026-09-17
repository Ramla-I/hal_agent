#!/usr/bin/env python3
"""bug_review.py -- the human's ledger over the sweep's possible bugs.

WHAT THIS IS
------------
The sweep's `possible bug` verdict is a machine claim: a compile-confirmed
access whose precondition the static scan could not find nearby. Whether it is
a REAL bug is a human judgement, and until now there was nowhere durable to
record it -- the artifact shows counts, the summary keeps a 40-row sample, and
490 of 930 candidate sites were recorded nowhere at all.

This maintains ONE tracked CSV, `experiments/bug_review.csv`, with a row per
candidate site and two columns that belong to the human:

    tp_fp   leave empty until reviewed; then `tp`, `fp`, or `unsure`
    note    anything worth keeping ("guard is two frames up in caller", ...)

Everything else in the row is machine-written: the site (rm, device, crate,
version, file, line), the register with its PERIPHERAL, the precondition
fields and how they were resolved (`exact`/`only` vs `union` -- a union row's
constraint identity is a candidate list, and the quote column says so), the
constraint ids and the datasheet sentence, so review does not require chasing
four files.

MERGE, NEVER REPLACE. `--init` after a fresh sweep keeps every human mark by
stable site key (rm|device|crate|file|line|register|operation -- deliberately
NOT the version, so a driver bump keeps your marks where the site survived).
New sites get empty tp_fp; sites the new sweep no longer produces are kept
with status `stale`, because a mark you made is evidence even after the site
moves -- the LOST_FINDINGS rule.

Usage:
    python applications/pac_codegen/experiments/bug_review.py --init
    # ... edit bug_review.csv: fill tp_fp / note ...
    python applications/pac_codegen/experiments/bug_review.py --table
    python applications/pac_codegen/experiments/bug_review.py --stats
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

EXP = Path(__file__).resolve().parent
OUT = EXP / "out"
REVIEW = EXP / "bug_review.csv"
TABLE = OUT / "bug_review_table.md"

FIELDS = ["status", "tp_fp", "note", "rm", "device", "crate", "version",
          "file", "line", "peripheral", "register", "operation",
          "precondition_fields", "field_source", "constraint_ids", "quote"]

HUMAN = {"tp_fp", "note"}          # never machine-overwritten
KEY = ("rm", "device", "crate", "file", "line", "register", "operation")


def key(row) -> tuple:
    return tuple(str(row.get(k, "")) for k in KEY)


def load_sites() -> list:
    rows = []
    tri = OUT / "triage"
    for f in sorted(tri.glob("*.jsonl")) if tri.is_dir() else []:
        for line in f.read_text().splitlines():
            r = json.loads(line)
            if r.get("verdict") != "unchecked":
                continue
            if "candidates" in r:
                ids = sorted({i for c in r["candidates"]
                              for i in c.get("constraint_ids", [])})
                quote = " | OR: ".join(
                    f"[{c['peripheral']}] {c.get('quote', '')}"
                    for c in r["candidates"])
            else:
                ids = r.get("constraint_ids") or []
                quote = r.get("quote", "")
            rows.append({
                "status": "", "tp_fp": "", "note": "",
                "rm": r["rm"], "device": r["device"], "crate": r["crate"],
                "version": r.get("version", ""),
                "file": r["file"], "line": r["line"],
                "peripheral": r.get("peripheral", ""),
                "register": r["register"], "operation": r["operation"],
                "precondition_fields": " ".join(r.get("fields") or []),
                "field_source": r.get("field_source", ""),
                "constraint_ids": " ".join(ids),
                "quote": quote,
            })
    return rows


def read_review() -> list:
    if not REVIEW.is_file():
        return []
    with open(REVIEW, newline="") as fh:
        return list(csv.DictReader(fh))


def write_review(rows) -> None:
    with open(REVIEW, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def init() -> None:
    fresh = load_sites()
    if not fresh:
        sys.exit(f"no triage side files under {OUT/'triage'} — "
                 f"run stm_sweep.py first (the field-mode sweep writes them)")
    old = {key(r): r for r in read_review()}
    seen = set()
    merged = []
    added = kept = stale = 0
    for r in fresh:
        k = key(r)
        seen.add(k)
        prev = old.get(k)
        if prev:
            for h in HUMAN:
                r[h] = prev.get(h, "")
            kept += 1
        else:
            added += 1
        merged.append(r)
    for k, prev in old.items():
        if k in seen:
            continue
        # A mark on a vanished site stays; unreviewed vanished rows do not.
        if any((prev.get(h) or "").strip() for h in HUMAN):
            prev["status"] = "stale"
            merged.append(prev)
            stale += 1
    merged.sort(key=lambda r: (r["rm"], r["device"], r["crate"],
                               r["file"], int(r["line"] or 0)))
    write_review(merged)
    print(f"{REVIEW.name}: {len(merged)} rows "
          f"({added} new, {kept} carried marks/blank, {stale} stale-kept)")


def stats() -> Counter:
    c = Counter()
    for r in read_review():
        if r.get("status") == "stale":
            c["stale"] += 1
            continue
        mark = (r.get("tp_fp") or "").strip().lower()
        c[mark or "unreviewed"] += 1
    total = sum(c.values()) - c.get("stale", 0)
    print(f"{total} live candidate sites: " +
          ", ".join(f"{k}={v}" for k, v in sorted(c.items())))
    return c


def table() -> None:
    rows = read_review()
    if not rows:
        sys.exit(f"{REVIEW} is empty — run --init first")
    c = Counter()
    per = Counter()
    for r in rows:
        if r.get("status") == "stale":
            continue
        mark = (r.get("tp_fp") or "").strip().lower() or "unreviewed"
        c[mark] += 1
        per[(r["rm"], r["crate"], mark)] += 1
    md = ["# Possible-bug review", "",
          f"{sum(c.values())} live sites: " +
          ", ".join(f"**{v}** {k}" for k, v in sorted(c.items())), "",
          "## Per pairing", "",
          "| RM | crate | tp | fp | unsure | unreviewed |", "|---|---|---|---|---|---|"]
    pairs = sorted({(rm, cr) for (rm, cr, _m) in per})
    for rm, cr in pairs:
        md.append(f"| {rm} | {cr} | {per[(rm,cr,'tp')]} | {per[(rm,cr,'fp')]} "
                  f"| {per[(rm,cr,'unsure')]} | {per[(rm,cr,'unreviewed')]} |")
    md += ["", "## Reviewed sites", "",
           "| mark | site | register | rule | note |", "|---|---|---|---|---|"]
    for r in rows:
        mark = (r.get("tp_fp") or "").strip()
        if not mark and r.get("status") != "stale":
            continue
        tag = mark or "stale"
        site = f"{r['rm']}/{r['crate']} {r['file']}:{r['line']}"
        reg = f"{r['peripheral']}/{r['register']} {r['operation']}"
        quote = (r.get("quote") or "").replace("|", "\\|")[:110]
        note = (r.get("note") or "").replace("|", "\\|")
        md.append(f"| {tag} | {site} | {reg} | {quote} | {note} |")
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text("\n".join(md) + "\n")
    print(f"table: {TABLE}")
    stats()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--init", action="store_true",
                   help="build/refresh the review CSV from the sweep's triage "
                        "side files, preserving human marks")
    g.add_argument("--table", action="store_true",
                   help="render the markdown table from the CSV")
    g.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    if args.init:
        init()
    elif args.table:
        table()
    else:
        stats()


if __name__ == "__main__":
    main()
