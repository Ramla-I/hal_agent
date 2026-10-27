#!/usr/bin/env python3
"""Inspect and review the constraints a device's crate actually gates.

`constraints/<rm>_<device>.json` is the durable record of what a crate gates.
This reads it three ways:

  show <rm>         print it the way a person reads it -- one block per
                    register, the rule, the datasheet sentence it came from,
                    and how firmly that sentence anchored.
  review <rm>       pull the review-ledger rows for the subset that became a
                    compile-time gate, out for tp/fp labelling (joined by id).
  merge <rm> FILE   copy edited tp_fp/devices from FILE back into the ledger.

`show` is read-only off the committed artifact; `review`/`merge` round-trip
through the generator's review ledger. The ledger lives in the phase-1d run
tree -- point elsewhere with --phase1d or the HAL_PHASE1D env var.

Usage:
    python applications/pac_codegen/injected_constraints.py show rm0008 [--quotes]
    python applications/pac_codegen/injected_constraints.py show --all
    python applications/pac_codegen/injected_constraints.py review rm0008 -o to_review.jsonl
    python applications/pac_codegen/injected_constraints.py merge rm0008 to_review.jsonl
"""
import argparse
import json
import os
import textwrap
from pathlib import Path

APP = Path(__file__).resolve().parent
DIR = APP / "constraints"
# The review ledger lives in the phase-1d run tree (STM); override per invocation.
DEFAULT_PHASE1D = Path(os.environ.get("HAL_PHASE1D", "/home/ramla/hal_agent-phase-1d"))


# --------------------------------------------------------------------------- #
# shared: the injected-constraints artifact
# --------------------------------------------------------------------------- #
def _files(pattern: str):
    return sorted(DIR.glob(f"{pattern}*.json"))


def _injected_ids(rm: str) -> set:
    ids = set()
    for f in DIR.glob(f"{rm}_*.json"):
        d = json.loads(f.read_text())
        for r in d["registers"]:
            ids.update(r.get("constraint_ids") or [])
    return ids


def _ledger(phase1d: Path, rm: str) -> Path:
    return phase1d / f"evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl"


# --------------------------------------------------------------------------- #
# show -- human-readable view of the committed artifact
# --------------------------------------------------------------------------- #
def _show(path: Path, quotes: bool) -> tuple[int, int]:
    d = json.loads(path.read_text())
    regs = d["registers"]
    mode = "field-level" if d.get("field_level_gating") else "whole-register"
    checked = "attribution-checked" if d.get("attribution_checked_against") \
        else "NOT attribution-checked"
    print(f"\n{path.stem}   {d['device']}   {mode}, {checked}")
    print("=" * 74)
    ops = 0
    for r in regs:
        head = f"{r['peripheral']}/{r['register']}"
        gated = ", ".join(r["gated_operations"]) or "-"
        print(f"\n  {head:<22} gates: {gated}"
              + (f"   [{','.join(r.get('constraint_ids') or [])}]"
                 if r.get("constraint_ids") else ""))
        ops += len(r["gated_operations"])
        # One line per distinct rule; the file repeats it per operation.
        seen = set()
        for op, pres in (r.get("preconditions") or {}).items():
            for p in pres:
                if p in seen:
                    continue
                seen.add(p)
                print(f"      requires  {p}")
        for field, g in (r.get("gated_fields") or {}).items():
            ops += 1
            print(f"      field {field}: {', '.join(g['preconditions'])}")
        if quotes:
            said = set()
            for texts in (r.get("datasheet_text") or {}).values():
                for t in texts:
                    if t not in said:
                        said.add(t)
                        for line in textwrap.wrap(t, 64):
                            print(f"        > {line}")
            tiers = {t for ts in (r.get("quote_verification") or {}).values()
                     for t in ts}
            if tiers:
                print(f"        anchored: {', '.join(sorted(tiers))}")
    return len(regs), ops


def cmd_show(a):
    if not a.rm and not a.all:
        raise SystemExit("show: name a manual, or pass --all")
    paths = _files("" if a.all else a.rm)
    if not paths:
        raise SystemExit(f"show: no constraints file matching {a.rm!r} in {DIR}")
    if a.ids:
        for path in paths:
            d = json.loads(path.read_text())
            for r in d["registers"]:
                for cid in r.get("constraint_ids", []):
                    print(cid)
        return
    tr = to = 0
    for p in paths:
        r, o = _show(p, a.quotes)
        tr += r
        to += o
    if len(paths) > 1:
        print(f"\n{'=' * 74}\n{len(paths)} devices, {tr} registers, {to} gates")


# --------------------------------------------------------------------------- #
# review / merge -- round-trip through the generator's review ledger
# --------------------------------------------------------------------------- #
def cmd_review(a):
    led = _ledger(a.phase1d, a.rm)
    if not led.is_file():
        raise SystemExit(f"review: no ledger at {led}")
    rows = [json.loads(l) for l in led.read_text().splitlines() if l.strip()]
    ids = _injected_ids(a.rm)
    if not ids:
        raise SystemExit(f"review: no injected-constraints artifact for {a.rm}; "
                         f"run inject_from_run.py --save-constraints first")
    gated = [r for r in rows if r["id"] in ids]
    text = "".join(json.dumps(r) + "\n" for r in gated)
    if a.out:
        Path(a.out).write_text(text)
        print(f"{len(gated)} of {len(rows)} ledger rows gate a register -> {a.out}")
        print(f"edit tp_fp (FP drops that gate), then: "
              f"injected_constraints.py merge {a.rm} {a.out}")
    else:
        print(text, end="")


def cmd_merge(a):
    led = _ledger(a.phase1d, a.rm)
    if not led.is_file():
        raise SystemExit(f"merge: no ledger at {led}")
    edits = {r["id"]: r for r in
             (json.loads(l) for l in Path(a.file).read_text().splitlines()
              if l.strip())}
    # Rewrite ONLY the lines whose label changed, and pass every other line
    # through byte-for-byte. A wholesale re-dump is not safe: the ledger on disk
    # holds raw UTF-8 while its writer uses ensure_ascii=True, so re-serialising
    # every row reformats lines nobody edited and buries the real change.
    raw = led.read_text().splitlines(keepends=True)
    ascii_only = all(ord(c) < 128 for c in "".join(raw))
    out, n = [], 0
    for line in raw:
        s = line.strip()
        if not s:
            out.append(line)
            continue
        r = json.loads(s)
        e = edits.get(r.get("id"))
        if not e:
            out.append(line)
            continue
        changed = False
        if e.get("tp_fp", "") != r.get("tp_fp", ""):
            r["tp_fp"] = e.get("tp_fp", "")
            changed = True
        if e.get("devices") is not None and e["devices"] != r.get("devices"):
            r["devices"] = e["devices"]
            changed = True
        if not changed:
            out.append(line)
            continue
        out.append(json.dumps(r, ensure_ascii=ascii_only) + "\n")
        n += 1
    if not n:
        print(f"{led}: no label changed; file untouched")
        return
    led.write_text("".join(out))
    print(f"{led}: {n} row(s) relabelled, {len(raw) - n} passed through unchanged")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="print what a crate gates, human-readably")
    s.add_argument("rm", nargs="?", default=None,
                   help="manual, e.g. rm0008 (prefix match)")
    s.add_argument("--all", action="store_true", help="every manual")
    s.add_argument("--quotes", action="store_true",
                   help="also print the datasheet sentence and anchor tier")
    s.add_argument("--ids", action="store_true",
                   help="print only the review-ledger ids, one per line")
    s.set_defaults(func=cmd_show)

    r = sub.add_parser("review",
                       help="pull the gated subset of the review ledger for tp/fp labelling")
    r.add_argument("rm")
    r.add_argument("-o", "--out", help="write the gated rows here")
    r.add_argument("--phase1d", type=Path, default=DEFAULT_PHASE1D,
                   help="phase-1d run tree holding the review ledgers (or $HAL_PHASE1D)")
    r.set_defaults(func=cmd_review)

    m = sub.add_parser("merge",
                       help="copy edited tp_fp/devices back into the review ledger")
    m.add_argument("rm")
    m.add_argument("file", help="the edited JSONL written by `review -o`")
    m.add_argument("--phase1d", type=Path, default=DEFAULT_PHASE1D,
                   help="phase-1d run tree holding the review ledgers (or $HAL_PHASE1D)")
    m.set_defaults(func=cmd_merge)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
