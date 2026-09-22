#!/usr/bin/env python3
"""review.py -- step through the bug-review ledger one hit at a time.

Walks the per-PAC / per-manual CSV tree in this folder (the same order the
coverage artifact uses: PAC family, then manual, then crate/device/file/
line), shows each hit's full context, and records your true/false-positive
verdict and an optional note straight back into its CSV. Every mark is
written the instant you make it, so quitting mid-review never loses work,
and re-running resumes at the first unreviewed hit.

Only the two human columns are ever touched: `tp_fp` and `note`. Everything
else (and the file layout) is owned by bug_review.py, whose --init merge
preserves your marks by key on the next sweep.

Usage:
    python applications/pac_codegen/bug_review/review.py
    python applications/pac_codegen/bug_review/review.py --pac stm32h7
    python applications/pac_codegen/bug_review/review.py --rm rm0433
    python applications/pac_codegen/bug_review/review.py --unchecked   # candidates only
    python applications/pac_codegen/bug_review/review.py --all         # revisit marked rows too
"""

import argparse
import csv
import functools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Constraint records (the full datasheet rule behind each constraint_id).
PHASE1D = Path.home() / "hal_agent-phase-1d"
_TTY = sys.stdout.isatty()


def _c(s, code):
    return f"\033[{code}m{s}\033[0m" if _TTY else s


BOLD = lambda s: _c(s, "1")
DIM = lambda s: _c(s, "90")       # solid gray, not faint (2 renders washed-out)
CYAN = lambda s: _c(s, "36")
YEL = lambda s: _c(s, "33")
RED = lambda s: _c(s, "31")
GRN = lambda s: _c(s, "32")
LABEL = lambda s: _c(s, "38;5;110")   # soft blue-gray for field labels
QUOTE = lambda s: _c(s, "38;5;180")   # warm tan — the datasheet text, readable


@functools.lru_cache(maxsize=None)
def _constraints_for_rm(rm):
    """constraint_id -> full record, from the manual's reviewed-constraints
    jsonl. Cached per manual."""
    f = PHASE1D / "evaluation" / "stm" / rm / "1" / f"{rm}_constraints_review.jsonl"
    out = {}
    if f.is_file():
        for line in f.read_text().splitlines():
            try:
                c = json.loads(line)
            except ValueError:
                continue
            cid = c.get("id") or c.get("constraint_id")
            if cid:
                out[cid] = c
    return out


def show_constraint(rm, ids):
    """Print the full datasheet rule behind each of a row's constraint ids."""
    recs = _constraints_for_rm(rm)
    if not ids:
        print(f"  {DIM('(no constraint id on this row)')}")
        return
    for cid in ids:
        c = recs.get(cid)
        print()
        if not c:
            print(f"  {BOLD(cid)}  {RED('not found in '+rm+' constraints')}")
            continue
        con = c.get("constraint", c)
        print(f"  {BOLD(cid)}  {CYAN(c.get('peripheral','')+'/'+c.get('register',''))}"
              f"   {DIM('verdict='+str(c.get('verdict',''))+'  confidence='+str(c.get('confidence','')))}")
        print(f"    {LABEL('kind')}        {con.get('kind','')}  {DIM('('+str(con.get('severity',''))+')')}")
        print(f"    {LABEL('text')}        {QUOTE(con.get('datasheet_text',''))}")
        tf = ", ".join(con.get("target_fields") or []) or "(whole register)"
        print(f"    {LABEL('target')}      {BOLD(con.get('target_register',''))} . {tf}"
              f"   [{con.get('target_operation','')}]")
        for p in con.get("preconditions") or []:
            fld = ("." + p["field"]) if p.get("field") else ""
            print(f"    {LABEL('precond')}     {p.get('register','')}{fld} = "
                  f"{YEL(str(p.get('state','')) or str(p.get('values','')))}"
                  f"   {DIM('('+str(p.get('established_by',''))+')')}")
        if con.get("consequence"):
            print(f"    {LABEL('effect')}      {DIM(con['consequence'])}")
        print(f"    {LABEL('enforce')}     {con.get('enforceability','')}")


def load(pac=None, rm=None):
    """Return (files, order): files maps path -> (fieldnames, [rows]);
    order is a flat list of (path, index) in tree order."""
    files, order = {}, []
    for f in sorted(ROOT.glob("*/*.csv")):
        fam = f.parent.name
        if pac and fam != pac:
            continue
        if rm and f.stem != rm:
            continue
        with open(f, newline="") as fh:
            r = csv.DictReader(fh)
            rows = list(r)
            files[f] = (r.fieldnames, rows)
        for i in range(len(rows)):
            order.append((f, i))
    return files, order


def save_file(path, fieldnames, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def show(row, path, pos, total, left):
    fam, rm = path.parent.name, path.stem
    print()
    print(DIM("─" * 70))
    head = f" {BOLD(fam)} / {rm}"
    prog = DIM(f"[hit {pos}/{total} · {left} unreviewed left]")
    print(f"{head}   {prog}")
    def line(name, val):
        print(f"  {LABEL(name.ljust(10))} {val}")
    crate = row.get("crate", "")
    ver = row.get("version", "")
    line("crate", f"{CYAN(crate)}   {DIM(ver)}")
    line("site", f"{BOLD(row.get('file',''))}:{BOLD(row.get('line',''))}")
    gf = row.get("gated_field") or "—"
    line("access", f"{row.get('peripheral','') or '?'} / "
         f"{BOLD(row.get('register',''))}  {row.get('operation','')}"
         f"   {DIM('gated field: '+gf)}")
    if row.get("precondition_fields"):
        line("precond", YEL(row["precondition_fields"]))
    sv = row.get("static_verdict", "")
    svc = {"unchecked": YEL, "corroborated": GRN}.get(sv, DIM)
    line("static", f"{svc(sv)}   {DIM('(field_source: '+row.get('field_source','')+')')}")
    cr = (row.get("claude_review") or "").strip()
    if cr:
        crc = {"tp": RED, "fp": GRN, "unsure": YEL}.get(cr, DIM)
        line("claude", crc(cr) + DIM("  (automated triage verdict — see claude_review.md)"))
    cnt = row.get("count", "")
    if cnt and cnt not in ("1", ""):
        line("count", f"{cnt} identical compiler reports")
    if row.get("compiled_in"):
        line("hit in", CYAN(row["compiled_in"])
             + DIM("  (downstream crates that compile this HAL site)"))
    if row.get("machine_note"):
        line("machine", RED(row["machine_note"]))
    q = " ".join((row.get("quote", "") or "").split())
    if q:
        line("quote", QUOTE(chr(34) + q + chr(34)))
    if row.get("constraint_ids"):
        line("ids", DIM(row["constraint_ids"]))
    if row.get("tp_fp"):
        print(f"  {'MARKED':10} {BOLD(row['tp_fp'])}"
              + (f"  — {row.get('note','')}" if row.get("note") else ""))
    print(DIM("─" * 70))


HELP = ("  [t] true-positive   [f] false-positive   [enter] skip\n"
        "  [i] show full constraint   [n] note only   [c] clear mark   "
        "[b] back   [q] quit")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pac", help="only this PAC family folder, e.g. stm32h7")
    ap.add_argument("--rm", help="only this manual, e.g. rm0433")
    ap.add_argument("--unchecked", action="store_true",
                    help="only rows whose static verdict is 'unchecked'")
    ap.add_argument("--all", action="store_true",
                    help="revisit already-marked rows too")
    args = ap.parse_args()

    files, order = load(args.pac, args.rm)
    if not order:
        sys.exit("no rows match (is the tree built? run bug_review.py --init)")

    def eligible(pr):
        path, i = pr
        row = files[path][1][i]
        if args.unchecked and row.get("static_verdict") != "unchecked":
            return False
        if row.get("status") == "stale":
            return False
        if not args.all and (row.get("tp_fp") or "").strip():
            return False
        return True

    queue = [pr for pr in order if eligible(pr)]
    if not queue:
        print("nothing to review — every matching row is already marked "
              "(use --all to revisit).")
        return
    total = len(order)
    marked = sum(1 for p, i in order if (files[p][1][i].get("tp_fp") or "").strip())
    print(f"{len(queue)} rows to review "
          f"({marked}/{total} already marked). {HELP}")

    def dirty(path):
        fn, rows = files[path]
        save_file(path, fn, rows)

    k = 0
    while 0 <= k < len(queue):
        path, i = queue[k]
        row = files[path][1][i]
        left = sum(1 for j in range(k, len(queue))
                   if not (files[queue[j][0]][1][queue[j][1]].get("tp_fp") or "").strip())
        show(row, path, k + 1, len(queue), left)
        try:
            cmd = input(f"  {BOLD('verdict')} > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nsaved. bye.")
            return
        if cmd in ("t", "tp", "f", "fp"):
            row["tp_fp"] = "tp" if cmd in ("t", "tp") else "fp"
            note = input(f"  note (optional) > ").strip()
            if note:
                row["note"] = note
            dirty(path)
            k += 1
        elif cmd in ("n", "note"):
            row["note"] = input(f"  note > ").strip()
            dirty(path)
        elif cmd in ("i", "info", "id"):
            show_constraint(path.stem, (row.get("constraint_ids") or "").split())
        elif cmd in ("c", "clear"):
            row["tp_fp"] = ""
            row["note"] = ""
            dirty(path)
        elif cmd in ("b", "back"):
            k = max(0, k - 1)
        elif cmd in ("q", "quit"):
            break
        elif cmd in ("?", "h", "help"):
            print(HELP)
        else:                                    # enter / anything = skip
            k += 1

    m = sum(1 for p, i in order if (files[p][1][i].get("tp_fp") or "").strip())
    tp = sum(1 for p, i in order if files[p][1][i].get("tp_fp") == "tp")
    fp = sum(1 for p, i in order if files[p][1][i].get("tp_fp") == "fp")
    print(f"\nsaved. {m}/{total} marked so far  ({tp} tp, {fp} fp, "
          f"{total - m} left).")


if __name__ == "__main__":
    main()
