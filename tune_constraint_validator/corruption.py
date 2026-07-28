#!/usr/bin/env python3
"""Corruption generator for validator calibration (plan §7.2, β leg).

From quote-ANCHORED constraint rows, generate known-bad encoding variants:
the quote + derived context are kept byte-identical to the original, only
the structured encoding is corrupted — so a competent judge must return
verdict != "confirmed". Detection rate over these = β estimate, human-free.

Phase-1b realism lesson (plan §7.2): unrealistic corruptions inflate the
numbers. All corruptions here stay in-distribution:

  flip_polarity      cleared <-> set on ONE precondition.
  swap_field         replace a precondition field with a SIBLING — another
                     field named in the same row's conditions, or a real
                     same-register field name mined from other rows of the
                     CSV. Never gibberish.
  change_operation   write <-> read; modify -> write. Never toward modify:
                     a modify contains a read AND a write, so write->modify
                     and read->modify are entailed-true, not corruptions.
  perturb_value      equals value +/-1, staying in range (the new value's
                     bit-length never exceeds the original literal's width).
  retarget_register  point the target at a DIFFERENT register that appears
                     in the same reference manual's rows.

One corruption type per variant; deterministic given --seed (per-row RNG is
keyed by (seed, type, original id), so row content is independent of
selection order). Each record carries {id, corruption_type, original_id}.

Output records mirror the CSV schema (JSON-array cells as strings) plus
``context``/``tier`` from the anchor, so ``judge.py --rows-jsonl`` consumes
them directly.

CLI:
    python3 tune_constraint_validator/corruption.py \
        --anchors tune_constraint_validator/out/anchors.jsonl \
        --csv verified_datasheet/constraints/stm.csv \
        --out tune_constraint_validator/out/corruptions.jsonl \
        --per-type 30 --seed 20260716
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.constraint_validator import (  # noqa: E402
    JUDGEABLE_TIERS,
    load_anchors,
    load_csv_rows,
    parse_json_list,
)

CORRUPTION_TYPES = ("flip_polarity", "swap_field", "change_operation",
                    "perturb_value", "retarget_register")

POLARITY_FLIP = {"cleared": "set", "set": "cleared"}
# Never corrupt TOWARD modify (Ramla, 2026-07-17): a modify performs both a
# read and a write, so a rule over all writes (or all reads) entails the
# modify claim -- write->modify / read->modify manufacture TRUE statements
# a correct judge must confirm (6 of the 7 op-swap "escapes" in the first
# calibration were exactly this). Away from modify is falsifying: a rule
# about the read-modify-write cycle says nothing about standalone ops.
OP_ALTERNATIVES = {"write": ("read",),
                   "read": ("write",),
                   "modify": ("write",)}
_EQUALS_RE = re.compile(r"^equals:(0[bB][01]+|0[xX][0-9a-fA-F]+|\d+)$")


# ---------------------------------------------------------------------------
# Row parsing / serialization
# ---------------------------------------------------------------------------


def parse_row(row: dict) -> dict:
    """CSV row -> parsed working copy (conditions as lists of dicts)."""
    return {
        "id": row.get("id", ""),
        "reference_manual": row.get("reference_manual", ""),
        "peripheral": row.get("peripheral", ""),
        "register": row.get("register", ""),
        "target_operation": row.get("target_operation", ""),
        "target_fields": parse_json_list(row.get("target_fields")),
        "preconditions": [dict(c) for c in
                          parse_json_list(row.get("preconditions"))],
        "postconditions": [dict(c) for c in
                           parse_json_list(row.get("postconditions"))],
        "severity": row.get("severity", ""),
        "consequence": row.get("consequence", ""),
        "datasheet_text": row.get("datasheet_text", ""),
    }


def make_record(parsed: dict, original: dict, anchor: dict,
                corruption_type: str) -> dict:
    """Corrupted encoding + ORIGINAL quote/context (that's the point: the
    encoding no longer matches the text)."""
    return {
        "id": f"{original['id']}-{corruption_type}",
        "original_id": original["id"],
        "corruption_type": corruption_type,
        "reference_manual": parsed["reference_manual"],
        "peripheral": parsed["peripheral"],
        "register": parsed["register"],
        "target_operation": parsed["target_operation"],
        "target_fields": json.dumps(parsed["target_fields"],
                                    separators=(",", ":")),
        "preconditions": json.dumps(parsed["preconditions"],
                                    separators=(",", ":")),
        "postconditions": json.dumps(parsed["postconditions"],
                                     separators=(",", ":")),
        "severity": parsed["severity"],
        "consequence": parsed["consequence"],
        "datasheet_text": original.get("datasheet_text", ""),
        "context": anchor.get("context", ""),
        "tier": anchor.get("tier", ""),
    }


# ---------------------------------------------------------------------------
# Sibling / register indexes (mined from the WHOLE CSV — realistic names only)
# ---------------------------------------------------------------------------


def _canon_reg(name) -> str:
    return (name or "").strip().upper()


def _field_base(name) -> str:
    """DUALMOD[3:0] -> DUALMOD, for 'is this really a different field' tests."""
    return re.sub(r"\[.*$", "", (name or "").strip()).upper()


def build_indexes(all_rows: list) -> dict:
    """siblings: (rm, REGISTER_NAME) -> set of real field names seen there;
    register_pool: rm -> set of (peripheral, register) target pairs."""
    siblings = defaultdict(set)
    register_pool = defaultdict(set)
    for r in all_rows:
        rm = r.get("reference_manual", "")
        per = (r.get("peripheral") or "").strip()
        reg = (r.get("register") or "").strip()
        if per and reg:
            register_pool[rm].add((per, reg))
        for c in (parse_json_list(r.get("preconditions"))
                  + parse_json_list(r.get("postconditions"))):
            rn = _canon_reg(c.get("register_name"))
            fn = (c.get("field_name") or "").strip()
            if rn and fn:
                siblings[(rm, rn)].add(fn)
        tf = [f for f in parse_json_list(r.get("target_fields"))
              if isinstance(f, str) and f.strip()]
        if tf and per and reg:
            base = per.rstrip("0123456789")
            for key in {f"{per}_{reg}", f"{base}_{reg}"}:
                siblings[(rm, key.upper())].update(tf)
    return {"siblings": siblings, "register_pool": register_pool}


# ---------------------------------------------------------------------------
# The five corruptions (each returns the mutated parsed row, or None when
# inapplicable to this row)
# ---------------------------------------------------------------------------


def corrupt_flip_polarity(parsed, rng, idx):
    cands = [i for i, c in enumerate(parsed["preconditions"])
             if c.get("required_state") in POLARITY_FLIP]
    if not cands:
        return None
    i = rng.choice(cands)
    c = dict(parsed["preconditions"][i])
    c["required_state"] = POLARITY_FLIP[c["required_state"]]
    parsed["preconditions"][i] = c
    return parsed


def corrupt_swap_field(parsed, rng, idx):
    rm = parsed["reference_manual"]
    pre = parsed["preconditions"]
    post = parsed["postconditions"]
    for i, c in enumerate(pre):
        orig = (c.get("field_name") or "").strip()
        if not orig:
            continue
        orig_base = _field_base(orig)
        same_row = {(cc.get("field_name") or "").strip()
                    for cc in pre + post}
        mined = idx["siblings"].get((rm, _canon_reg(c.get("register_name"))),
                                    set())
        pool = sorted(f for f in (same_row | set(mined))
                      if f and _field_base(f) != orig_base)
        if not pool:
            continue
        cc = dict(c)
        cc["field_name"] = rng.choice(pool)
        pre[i] = cc
        return parsed
    return None


def corrupt_change_operation(parsed, rng, idx):
    op = (parsed["target_operation"] or "").strip().lower()
    alts = OP_ALTERNATIVES.get(op)
    if not alts:
        return None                     # off-vocab ops: skip, stay realistic
    parsed["target_operation"] = rng.choice(alts) if len(alts) > 1 else alts[0]
    return parsed


def _parse_equals(state):
    m = _EQUALS_RE.match((state or "").strip())
    if not m:
        return None
    lit = m.group(1)
    if lit[:2].lower() == "0b":
        return int(lit, 2), "bin", len(lit) - 2, lit
    if lit[:2].lower() == "0x":
        return int(lit, 16), "hex", (len(lit) - 2) * 4, lit
    v = int(lit)
    return v, "dec", max(v.bit_length(), 1), lit


def _format_value(v, style, orig_lit):
    if style == "bin":
        return "0b" + format(v, f"0{len(orig_lit) - 2}b")
    if style == "hex":
        digits = orig_lit[2:]
        s = format(v, f"0{len(digits)}x")
        lower = digits.islower() and any(ch.isalpha() for ch in digits)
        return "0x" + (s if lower else s.upper())
    return str(v)


def corrupt_perturb_value(parsed, rng, idx):
    pre = parsed["preconditions"]
    for i, c in enumerate(pre):
        p = _parse_equals(c.get("required_state"))
        if p is None:
            continue
        v, style, width, lit = p
        maxv = (1 << width) - 1
        choices = [x for x in (v - 1, v + 1) if 0 <= x <= maxv]
        if not choices:
            continue
        nv = rng.choice(choices)
        cc = dict(c)
        cc["required_state"] = "equals:" + _format_value(nv, style, lit)
        pre[i] = cc
        return parsed
    return None


def corrupt_retarget_register(parsed, rng, idx):
    rm = parsed["reference_manual"]
    cur = (parsed["register"] or "").strip().lower()
    pool = sorted(pr for pr in idx["register_pool"].get(rm, ())
                  if pr[1].strip().lower() != cur)
    if not pool:
        return None
    per, reg = rng.choice(pool)
    parsed["peripheral"], parsed["register"] = per, reg
    return parsed


CORRUPTORS = {
    "flip_polarity": corrupt_flip_polarity,
    "swap_field": corrupt_swap_field,
    "change_operation": corrupt_change_operation,
    "perturb_value": corrupt_perturb_value,
    "retarget_register": corrupt_retarget_register,
}


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def generate(csv_rows: list, anchors: dict, per_type: int, seed,
             types=CORRUPTION_TYPES) -> list:
    """Deterministic corruption set: per type, candidates are taken
    round-robin across reference manuals (seeded order within each RM) until
    ``per_type`` succeed or candidates run out. Rows lacking the material a
    type needs (e.g. no cleared/set precondition for flip_polarity) are
    skipped, never faked."""
    idx = build_indexes(csv_rows)
    anchored = []
    for r in sorted(csv_rows, key=lambda r: r.get("id", "")):
        a = anchors.get(r.get("id", ""))
        if a and a.get("tier") in JUDGEABLE_TIERS and a.get("context"):
            anchored.append((r, a))

    out = []
    for ctype in types:
        sel_rng = random.Random(f"{seed}:{ctype}")
        by_rm = defaultdict(list)
        for r, a in anchored:
            by_rm[r.get("reference_manual", "")].append((r, a))
        rms = sorted(by_rm)
        for rm in rms:
            sel_rng.shuffle(by_rm[rm])
        picked = 0
        while picked < per_type and any(by_rm[rm] for rm in rms):
            for rm in rms:
                if picked >= per_type:
                    break
                q = by_rm[rm]
                while q:
                    r, a = q.pop()
                    row_rng = random.Random(f"{seed}:{ctype}:{r['id']}")
                    got = CORRUPTORS[ctype](parse_row(r), row_rng, idx)
                    if got is not None:
                        out.append(make_record(got, r, a, ctype))
                        picked += 1
                        break
    out.sort(key=lambda rec: (rec["corruption_type"], rec["original_id"]))
    return out


def write_records(records: list, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=True) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anchors", default="tune_constraint_validator/out/anchors.jsonl")
    ap.add_argument("--csv", default="verified_datasheet/constraints/stm.csv")
    ap.add_argument("--out", default="tune_constraint_validator/out/corruptions.jsonl")
    ap.add_argument("--per-type", type=int, default=30)
    ap.add_argument("--seed", default="20260716")
    args = ap.parse_args(argv)

    csv_rows = load_csv_rows(args.csv)
    anchors = load_anchors(args.anchors)
    records = generate(csv_rows, anchors, args.per_type, args.seed)
    write_records(records, args.out)

    counts = defaultdict(int)
    for rec in records:
        counts[rec["corruption_type"]] += 1
    for ctype in CORRUPTION_TYPES:
        print(f"  {ctype:<20} {counts.get(ctype, 0):>4}")
    print(f"total {len(records)} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
