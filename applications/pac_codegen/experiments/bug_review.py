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
          "gated_field", "static_verdict", "count",
          "precondition_fields", "field_source", "machine_note",
          "constraint_ids", "quote"]

HUMAN = {"tp_fp", "note"}          # never machine-overwritten
# gated_field is part of the identity: four field gates firing on one
# `cfgr.modify(..)` line are four different bits, and without it they were
# four indistinguishable rows sharing one merge key -- 172 keys covered 397
# extra rows, and a mark on one of them was ambiguous on the next --init.
# What remains identical after that (per-macro-expansion, per-instance
# duplicates) is AGGREGATED into one row whose `count` says how many times
# the compiler reported it.
KEY = ("rm", "device", "crate", "file", "line", "register", "operation",
       "gated_field")


def key(row) -> tuple:
    return tuple(str(row.get(k, "")) for k in KEY)


# The compiled PROJECTS record their hits in port_*.json, not in triage side
# files -- and the ledger's first version silently covered only the HALs,
# while the handover advice pointed the reviewer at elodin/blackpill rows
# that did not exist. Port hits lack constraint identity, so it is joined
# here from the per-device constraints file the sweep saves: one match ->
# exact; several peripherals sharing the register name -> the labelled
# candidate list, same rule as the sweep's union.
PORT_RECORDS = ["port_blackpill.json", "port_elodin.json", "port_hubris.json",
                "port_anne_key.json", "port_stm32_eth.json",
                # hubris's other PAC families (drv/stm32fx-* on F3+F4,
                # drv/stm32g0-usart on G0), each a distinct pkg@device.
                "port_hubris_stm32f3.json", "port_hubris_stm32f4.json",
                "port_hubris_g031.json"]


def _constraint_index(rm: str, device: str, path: Path = None) -> dict:
    p = path or OUT / "constraints" / f"{rm}_{device}.json"
    if not p.is_file():
        return {}
    idx = {}
    for e in json.loads(p.read_text()).get("registers", []):
        quotes = [q for v in (e.get("datasheet_text") or {}).values()
                  for q in (v if isinstance(v, list) else [v])]
        quotes += [q for fg in (e.get("gated_fields") or {}).values()
                   for q in (fg.get("datasheet_text") or [])]
        idx.setdefault((e.get("register") or "").lower(), []).append({
            "peripheral": (e.get("peripheral") or "").lower(),
            "constraint_ids": list(e.get("constraint_ids") or []),
            "quote": quotes[0] if quotes else "",
        })
    return idx


def load_port_sites() -> list:
    rows = []
    for name in PORT_RECORDS:
        f = OUT / name
        if not f.is_file():
            continue
        r = json.loads(f.read_text())
        if r.get("baseline") != "PASS":
            continue
        idx = _constraint_index(r["rm"], r["device"])
        if not idx:
            # A pairing whose device is not the sweep's for that manual
            # (hubris drives g031, the sweep injects g071) has no shared
            # constraints file; fall back to the constraints THIS pairing
            # saved at injection.
            glob = sorted(OUT.glob(f"{r['rm']}_{r['device']}*_constraints.json"))
            if glob:
                idx = _constraint_index(r["rm"], r["device"], path=glob[0])
        # Port rows carry EVERY static verdict, labelled, because the ports
        # are where corroborated has already been wrong once: hubris enables
        # UE at lib.rs:72 and writes a UE=0-gated register at :76, and the
        # static pass reads that as corroborated. A reviewer must be able to
        # see those rows in the same file. (Sweep and ported-HAL rows stay
        # unchecked-only -- a thousand guarded driver rows would drown the
        # review, and their counts live on the tracking page.)
        for h in r.get("hits") or []:
            reg = str(h.get("register", "")).split("::")[-1].lower()
            reg = reg[:-2] if reg.endswith("rs") else reg
            cands = idx.get(reg, [])
            per = (h.get("peripheral") or "").lower()
            if per:
                cands = [c for c in cands if c["peripheral"] == per] or cands
            if len(cands) == 1:
                ids = cands[0]["constraint_ids"]
                quote = cands[0]["quote"]
                per = per or cands[0]["peripheral"]
            else:
                ids = sorted({i for c in cands for i in c["constraint_ids"]})
                quote = " | OR: ".join(
                    f"[{c['peripheral']}] {c['quote']}" for c in cands)
            rows.append({
                "status": "", "tp_fp": "", "note": "",
                "rm": r["rm"], "device": r["device"],
                "crate": r["project"],
                "version": r.get("hal") or r.get("pac") or "",
                "file": h.get("file", ""), "line": h.get("line", 0),
                "peripheral": per, "register": reg,
                "operation": h.get("operation", ""),
                "gated_field": h.get("gated_field", ""),
                "static_verdict": h.get("verdict", ""),
                "precondition_fields": " ".join(h.get("fields") or []),
                "field_source": "exact" if len(cands) == 1 else "union",
                "machine_note": h.get("triage_note", ""),
                "constraint_ids": " ".join(ids),
                "quote": quote,
            })
    return rows


def load_measured_hal_sites() -> list:
    """Possible-bug sites from the PORTED HALs (measure_ported.json).

    These never reached the ledger: the sweep's side files cover released
    drivers and PORT_RECORDS covers the project ports, but the HALs that
    only became measurable after port_hal.py moved them to PAC 0.16 --
    stm32l0xx-hal, stm32f0xx-hal, and the dependent-scan picks -- reported
    into measure_ported.json and stopped there. Constraint identity is
    joined from each pairing's saved-constraints file, exactly the way the
    project ports join theirs."""
    p = OUT / "measure_ported.json"
    if not p.is_file():
        return []
    rows = []
    for r in json.loads(p.read_text()):
        if r.get("baseline") != "PASS" or not r.get("hal"):
            continue
        idx = _constraint_index(
            r["rm"], r["device"],
            path=OUT / f"{r['rm']}_{r['device']}_ported_constraints.json")
        for h in r.get("hits") or []:
            if h.get("verdict") != "unchecked":
                continue
            reg = str(h.get("register", "")).split("::")[-1].lower()
            reg = reg[:-2] if reg.endswith("rs") else reg
            cands = idx.get(reg, [])
            if len(cands) == 1:
                per, ids, quote = (cands[0]["peripheral"],
                                   cands[0]["constraint_ids"],
                                   cands[0]["quote"])
            else:
                per = ""
                ids = sorted({i for c in cands for i in c["constraint_ids"]})
                quote = " | OR: ".join(
                    f"[{c['peripheral']}] {c['quote']}" for c in cands)
            f = str(h.get("file", ""))
            f = f.split(r["hal"] + "/", 1)[-1]
            rows.append({
                "status": "", "tp_fp": "", "note": "",
                "rm": r["rm"], "device": r["device"], "crate": r["hal"],
                "version": "ported-to-0.16",
                "file": f, "line": h.get("line", 0),
                "peripheral": per, "register": reg,
                "operation": h.get("operation", ""),
                "gated_field": h.get("gated_field", ""),
                "static_verdict": "unchecked",
                "precondition_fields": " ".join(h.get("fields") or []),
                "field_source": "exact" if len(cands) == 1 else "union",
                "machine_note": "",
                "constraint_ids": " ".join(ids),
                "quote": quote,
            })
    return rows


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
                "gated_field": r.get("gated_field", ""),
                "static_verdict": "unchecked",
                "precondition_fields": " ".join(r.get("fields") or []),
                "field_source": r.get("field_source", ""),
                "machine_note": "",
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


def aggregate(rows: list) -> list:
    """Collapse rows identical in every machine column into one, counting.

    A macro body reports once per expansion and a per-instance impl once per
    instance -- same file, line, register, operation, gated field, fields,
    constraint identity. Those are one site for a reviewer; `count` keeps the
    multiplicity honest. Rows differing in ANY machine column stay separate."""
    out, index = [], {}
    ident_cols = [c for c in FIELDS if c not in ("status", "tp_fp", "note",
                                                 "count")]
    for r in rows:
        k = tuple(str(r.get(c, "")) for c in ident_cols)
        prev = index.get(k)
        if prev is None:
            r = dict(r, count=int(r.get("count") or 1))
            index[k] = r
            out.append(r)
        else:
            prev["count"] += int(r.get("count") or 1)
    for r in out:
        r["count"] = str(r["count"])
    return out


def init() -> None:
    fresh = aggregate(load_sites() + load_port_sites()
                      + load_measured_hal_sites())
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
