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
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

EXP = Path(__file__).resolve().parent
OUT = EXP / "out"
# The review ledger is a TREE, one folder per PAC family, one CSV per
# manual: applications/pac_codegen/bug_review/<pac>/<rm>.csv. It used to be
# a single bug_review.csv; splitting it keeps each manual's marks in a small
# reviewable file and groups families the way the coverage artifact does.
REVIEW_DIR = EXP.parent / "bug_review"
TABLE = OUT / "bug_review_table.md"


def _rm_to_pac() -> dict:
    """manual -> PAC family, so the ledger can be ordered the way the
    coverage artifact is (by PAC family, not by manual). Built from the
    sweep's own TARGETS plus the master-PAC manuals."""
    m = {"rm0505": "stm32wb0", "rm0529": "stm32wb0", "rm0530": "stm32wb0",
         "rm0493": "stm32wba"}
    try:
        sys.path.insert(0, str(EXP))
        import stm_sweep
        for t in stm_sweep.TARGETS:
            m.setdefault(t.rm, t.pac)
    except Exception:                                      # noqa: BLE001
        pass
    return m


RM2PAC = _rm_to_pac()
_MASTER_PACS = {"stm32wb0", "stm32wba"}


def artifact_order(r) -> tuple:
    """Match the coverage artifact's ordering: PAC family (alphabetical,
    master PACs last) -> crate -> device -> file -> line."""
    pac = RM2PAC.get(r["rm"], "zzz-" + r["rm"])
    return (pac in _MASTER_PACS, pac, r["crate"], r["device"],
            r["file"], int(r["line"] or 0))

FIELDS = ["status", "tp_fp", "note", "claude_review", "rm", "device", "crate",
          "version", "file", "line", "peripheral", "register", "operation",
          "gated_field", "static_verdict", "count", "compiled_in",
          "precondition_fields", "field_source", "machine_note",
          "constraint_ids", "quote"]

# claude_review holds a one-time automated triage verdict (tp/fp/unsure). Like
# the human marks it is preserved verbatim across --init (never recomputed from
# the sweep); a genuinely new row gets it blank.
HUMAN = {"tp_fp", "note", "claude_review"}   # never machine-overwritten
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


_HAL_MARKERS = ("-hal", "hal2", "hrtim")

# Records whose HAL-layer hits tell us which downstream crates COMPILE a HAL
# site (the dependent-compile probes + the whole-app ports). Their fired
# gates all land in a HAL, so they are not ledger rows of their own (that
# would duplicate the sweep); instead they annotate the sweep's HAL rows.
_DOWNSTREAM_RECORDS = ["port_blackpill.json", "port_stm32_eth.json",
                       "dependent_semtech_radios.json",
                       "dependent_stm32f469i_disc.json",
                       "dependent_embassy_stm32.json"]


def _rel_src(f: str) -> str:
    """Normalise a hit's file to the crate-relative `src/...` path so a
    dependent's absolute path matches the sweep row's relative one."""
    return "src/" + f.split("src/", 1)[1] if "src/" in f else f


def _downstream_map() -> dict:
    """(rm, device, crate, rel_file, line) -> set(project) : which compiled
    dependents fire a gate at each HAL site. Keyed by device too, so a g4
    dependent (semtech) only annotates the g4 rows, not another family's
    same-named source line."""
    m = defaultdict(set)
    for name in _DOWNSTREAM_RECORDS:
        p = OUT / name
        if not p.is_file():
            continue
        r = json.loads(p.read_text())
        if r.get("baseline") != "PASS":
            continue
        proj = r.get("project") or r.get("dependent") or name
        for h in r.get("hits") or []:
            if not _is_hal_site(h):
                continue
            lay = h.get("layer") or h.get("file", "").split("/", 1)[0]
            crate = lay if any(x in lay for x in _HAL_MARKERS) else \
                h.get("file", "").split("/", 1)[0]
            key = (r["rm"], r["device"], crate,
                   _rel_src(h.get("file", "")), str(h.get("line", "")))
            m[key].add(proj)
    return m


DOWNSTREAM = None   # built lazily on first init


def _is_hal_site(h: dict) -> bool:
    """A compiled project's hit that fired INSIDE a HAL, not the project's own
    source. Those sites are already in the ledger from the sweep's HAL rows
    (and shown per-dependent on the coverage artifact), so ingesting them here
    only duplicates review -- e.g. every blackpill hit is a stm32f4xx-hal
    site the sweep already recorded. The ledger keeps a project's OWN-code
    hits (hubris's drivers, elodin's SDMMC, rustuino's ADC); HAL-layer hits
    are pruned."""
    if (h.get("where") or "").lower() == "hal":
        return True
    lay = (h.get("layer") or "")
    if any(m in lay for m in _HAL_MARKERS):
        return True
    f = h.get("file", "")
    root = f.split("/", 1)[0]
    if any(m in root for m in _HAL_MARKERS):
        return True
    if "/.cargo/" in f and any(m in f for m in _HAL_MARKERS):
        return True
    return False


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
            if _is_hal_site(h):
                continue          # HAL-layer hit; covered by the sweep rows
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
            if h.get("verdict") not in ("unchecked", "corroborated"):
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
                "static_verdict": h.get("verdict", "unchecked"),
                "precondition_fields": " ".join(h.get("fields") or []),
                "field_source": "exact" if len(cands) == 1 else "union",
                "machine_note": "",
                "constraint_ids": " ".join(ids),
                "quote": quote,
            })
    return rows


def load_sites() -> list:
    dmap = DOWNSTREAM if DOWNSTREAM is not None else _downstream_map()
    rows = []
    tri = OUT / "triage"
    for f in sorted(tri.glob("*.jsonl")) if tri.is_dir() else []:
        for line in f.read_text().splitlines():
            r = json.loads(line)
            # Include corroborated too (per request): the static scan's
            # "corroborated" auto-clear is value-blind and has been wrong (it
            # cleared the confirmed hubris UE/BRR bug), so keep those rows in
            # the ledger, tagged by static_verdict, rather than dropping them.
            if r.get("verdict") not in ("unchecked", "corroborated"):
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
                "static_verdict": r.get("verdict", "unchecked"),
                "compiled_in": ", ".join(sorted(dmap.get(
                    (r["rm"], r["device"], r["crate"],
                     _rel_src(r["file"]), str(r["line"])), set()))),
                "precondition_fields": " ".join(r.get("fields") or []),
                "field_source": r.get("field_source", ""),
                "machine_note": "",
                "constraint_ids": " ".join(ids),
                "quote": quote,
            })
    return rows


def _pac_of(rm: str) -> str:
    return RM2PAC.get(rm, "other")


def review_path(pac: str, rm: str) -> Path:
    return REVIEW_DIR / pac / f"{rm}.csv"


def read_review() -> list:
    """Every row across the whole tree, concatenated."""
    rows = []
    if REVIEW_DIR.is_dir():
        for f in sorted(REVIEW_DIR.glob("*/*.csv")):
            with open(f, newline="") as fh:
                rows.extend(csv.DictReader(fh))
    return rows


def write_review(rows) -> None:
    """Split rows into <pac>/<rm>.csv. The tree is rebuilt from scratch each
    time: `rows` is the fully-merged set (including stale-kept marked rows),
    so clearing and rewriting cannot lose a mark and drops files for pairings
    that no longer have any row."""
    # Clear only the per-PAC subdirectories, NOT the whole REVIEW_DIR: the
    # reviewer (review.py) and any notes live directly in bug_review/, and an
    # rmtree of the parent would delete them on every --init.
    if REVIEW_DIR.is_dir():
        for sub in REVIEW_DIR.iterdir():
            if sub.is_dir():
                shutil.rmtree(sub)
    groups = defaultdict(list)
    for r in rows:
        groups[(_pac_of(r["rm"]), r["rm"])].append(r)
    for (pac, rm), grp in groups.items():
        p = review_path(pac, rm)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            for r in grp:
                w.writerow({k: r.get(k, "") for k in FIELDS})


def aggregate(rows: list) -> list:
    """Collapse rows identical in every machine column into one, counting.

    A macro body reports once per expansion and a per-instance impl once per
    instance -- same file, line, register, operation, gated field, fields,
    constraint identity. Those are one site for a reviewer; `count` keeps the
    multiplicity honest. Rows differing in ANY machine column stay separate."""
    out, index = [], {}
    ident_cols = [c for c in FIELDS if c not in ("status", "tp_fp", "note",
                                                 "claude_review", "count")]
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
    merged.sort(key=artifact_order)
    write_review(merged)
    n_files = len({(_pac_of(r["rm"]), r["rm"]) for r in merged})
    n_pacs = len({_pac_of(r["rm"]) for r in merged})
    print(f"{REVIEW_DIR.name}/: {len(merged)} rows across {n_pacs} PAC "
          f"folders / {n_files} manual files "
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
        sys.exit(f"{REVIEW_DIR} is empty — run --init first")
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
