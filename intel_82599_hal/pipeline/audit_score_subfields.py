#!/usr/bin/env python3
"""Score the extracted subfields (bit fields) of a run against an independent
referee: the Linux ixgbe driver's field constants, as transcribed in ixy.rs's
constants.rs (MIT; descends from ixgbe_type.h).

Method (conservative by construction — under-join rather than mis-join):
  - referee entries are `pub const IXGBE_<REG>_<SUFFIX>: u32 = <expr>;` where
    <REG> longest-prefix-matches one of the run's 75 registers and the entry's
    set bits are CONTIGUOUS (non-contiguous combo masks are skipped);
    `_SHIFT` entries assert a start bit, `_MASK` entries a bit range, other
    entries are field values/bit flags whose set bits must lie INSIDE the field
  - the referee suffix joins to an extracted subfield by normalized name
    (strip non-alphanumerics + trailing 82599/82598/X540 qualifiers; exact or
    containment, either direction, len >= 3); an entry matching several
    distinct fields is discarded
  - AGREE: every joined entry's bits lie inside our extracted bit range
    (shift == our start_bit); DISAGREE: any entry falls outside -> adjudicate
    by hand against the datasheet; no join -> UNSCORED (never counted as ok)

Usage: python3 audit_score_subfields.py r006 [path/to/constants.rs]
"""
import json
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = sys.argv[1] if len(sys.argv) > 1 else "r006"
REF = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    HERE, "..", "retrofit", "clones", "ixy.rs", "src", "constants.rs")


def norm(s):
    s = re.sub(r"[^A-Za-z0-9]", "", str(s)).lower()
    return re.sub(r"(82599|82598|x540|8259x)$", "", s)


regs = {}
for p in sorted(glob.glob(os.path.join(HERE, "register_info", RUN, "*.json"))):
    name = os.path.basename(p)[:-5]
    d = json.load(open(p))
    fields = []
    for sf in d.get("subfields") or []:
        bn = sf.get("bit_number") or {}
        if bn.get("start_bit") is None:
            continue
        fields.append({"name": sf["name"], "lo": bn["start_bit"], "hi": bn["end_bit"],
                       "reserved": norm(sf["name"]).startswith(("reserv", "rsv"))})
    regs[name] = fields
by_len = sorted(regs, key=len, reverse=True)

OTHER_GEN = ("X540", "X550", "82598", "E610", "X557")
ref_text = open(REF, errors="replace").read()
if REF.endswith(".h"):
    # C header: parameterless #define IXGBE_<NAME> <expr>  (macros with args skipped)
    raw_iter = [(m.group(1), m.group(2).split("/*")[0].strip())
                for m in re.finditer(r"^#define IXGBE_([A-Z0-9_]+)[ \t]+([^\n]+)",
                                     ref_text, re.M)]
else:
    raw_iter = [(m.group(1), m.group(2))
                for m in re.finditer(r"pub const IXGBE_([A-Z0-9_]+): u32\s*=\s*([^;]+);",
                                     ref_text)]
entries = []
for rest, expr in raw_iter:
    if any(g in rest for g in OTHER_GEN):
        continue  # different chip generation's layout
    if not re.fullmatch(r"[0-9a-fA-FxXuU_\s<|()]+", expr):
        continue
    try:
        val = eval(re.sub(r"[uU]\b|_", "", expr))
    except Exception:
        continue
    reg = next((r for r in by_len if rest == r or rest.startswith(r + "_")), None)
    if reg is None or rest == reg:
        continue
    tail = re.sub(r"_82599$", "", rest[len(reg) + 1:])
    kind = "shift" if tail.endswith("_SHIFT") else ("mask" if tail.endswith("_MASK") else "value")
    suffix = re.sub(r"_(SHIFT|MASK)$", "", tail)
    if kind != "shift":
        if not isinstance(val, int) or val <= 0 or val > 0xFFFFFFFF:
            continue
        bits = [i for i in range(32) if val >> i & 1]
        if bits[-1] - bits[0] + 1 != len(bits):
            continue
        entries.append((reg, suffix, kind, (bits[0], bits[-1]), rest))
    else:
        if not isinstance(val, int) or val > 31:
            continue
        entries.append((reg, suffix, kind, val, rest))

shifts = {}
for reg, suffix, kind, info, raw in entries:
    if kind == "shift":
        shifts[(reg, norm(suffix))] = info
score = {}
for reg, suffix, kind, info, raw in entries:
    ns = norm(suffix)
    if len(ns) < 3:
        continue
    def name_match(f):
        nf = norm(f["name"])
        if nf == ns:
            return True
        return len(nf) >= 3 and (ns in nf or nf in ns)
    cands = [f for f in regs.get(reg, []) if not f["reserved"] and name_match(f)]
    if len({(c["lo"], c["hi"]) for c in cands}) != 1:
        continue
    f = cands[0]
    key = (reg, f["name"])
    if kind == "shift":
        ok = (info == f["lo"])
        ev = f"{raw}={info} vs start_bit {f['lo']}"
    else:
        lo, hi = info
        sh = shifts.get((reg, ns))
        if kind == "mask" and lo == 0 and sh is not None and sh > 0:
            lo, hi = sh, sh + (hi - info[0])  # Linux pre-shift mask idiom
        ok = (lo >= f["lo"] and hi <= f["hi"])
        ev = f"{raw}=bits {lo}..{hi} vs extracted {f['lo']}..{f['hi']}"
    cur = score.setdefault(key, {"ok": True, "evidence": []})
    cur["ok"] = cur["ok"] and ok
    cur["evidence"].append(("AGREE" if ok else "DISAGREE") + ": " + ev)

total = sum(len(v) for v in regs.values())
reserved = sum(1 for v in regs.values() for f in v if f["reserved"])
agree = sum(1 for v in score.values() if v["ok"])
dis = {k: v for k, v in score.items() if not v["ok"]}
print(f"run {RUN}: {total} subfields over {len(regs)} registers "
      f"({reserved} reserved, {total - reserved} named)")
print(f"linux-referee joins: {len(score)} fields -> {agree} agree, {len(dis)} disagree")
for (reg, fld), v in sorted(dis.items()):
    print(f"  DISAGREE {reg}.{fld}")
    for e in v["evidence"]:
        print(f"      {e}")
out = {"run": RUN, "total_subfields": total, "reserved": reserved,
       "referee_joined": len(score), "agree": agree,
       "disagree": {f"{r}.{f}": v["evidence"] for (r, f), v in dis.items()},
       "scored_fields": sorted(f"{r}.{f}" for r, f in score)}
json.dump(out, open(os.path.join(HERE, "..", "reports", "audit_score_subfields.json"), "w"), indent=2)
print("wrote audit_score_subfields.json")
