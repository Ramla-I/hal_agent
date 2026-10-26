#!/usr/bin/env python3
"""Pull the review-ledger rows for the constraints a crate ACTUALLY gates.

The ledger (`<rm>_constraints_review.jsonl`) holds every constraint the judge
saw -- 11,030 rows corpus-wide. Only 2,474 of those became a compile-time gate.
Reviewing the gates means reading the second set, and the two are joined by
constraint id, which the injected-constraints artifact now carries.

Writes a ledger-shaped JSONL of just those rows. Edit `tp_fp` in it (FP removes
that gate on the next injection), then merge back with --merge: only `tp_fp`
and `devices` are copied over, keyed on id, so nothing else can drift.

Usage:
    python applications/pac_codegen/review_injected.py rm0008 -o to_review.jsonl
    python applications/pac_codegen/review_injected.py rm0008 --merge to_review.jsonl
"""
import argparse
import json
from pathlib import Path

APP = Path(__file__).resolve().parent
PHASE1D = Path("/home/ramla/hal_agent-phase-1d")


def ledger(rm: str) -> Path:
    return PHASE1D / f"evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl"


def injected_ids(rm: str) -> set:
    ids = set()
    for f in APP.glob(f"constraints/{rm}_*.json"):
        d = json.loads(f.read_text())
        for r in d["registers"]:
            ids.update(r.get("constraint_ids") or [])
    return ids


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("rm")
    ap.add_argument("-o", "--out", help="write the gated rows here")
    ap.add_argument("--merge", metavar="FILE",
                    help="copy tp_fp/devices from FILE back into the ledger")
    a = ap.parse_args()

    led = ledger(a.rm)
    if not led.is_file():
        ap.error(f"no ledger at {led}")
    rows = [json.loads(l) for l in led.read_text().splitlines() if l.strip()]

    if a.merge:
        edits = {r["id"]: r for r in
                 (json.loads(l) for l in Path(a.merge).read_text().splitlines()
                  if l.strip())}
        # Rewrite ONLY the lines whose label changed, and pass every other line
        # through byte-for-byte. A wholesale re-dump is not safe here: the
        # ledger on disk holds raw UTF-8 while its writer uses
        # ensure_ascii=True, so re-serialising every row reformats a dozen
        # lines that nobody edited and buries the real change in the diff.
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
        print(f"{led}: {n} row(s) relabelled, {len(raw) - n} passed through "
              f"unchanged")
        return

    ids = injected_ids(a.rm)
    if not ids:
        ap.error(f"no injected-constraints artifact for {a.rm}; run "
                 f"inject_from_run.py --save-constraints first")
    gated = [r for r in rows if r["id"] in ids]
    out = Path(a.out) if a.out else None
    text = "".join(json.dumps(r) + "\n" for r in gated)
    if out:
        out.write_text(text)
        print(f"{len(gated)} of {len(rows)} ledger rows gate a register -> {out}")
        print("edit tp_fp (FP drops that gate), then re-run with --merge")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
