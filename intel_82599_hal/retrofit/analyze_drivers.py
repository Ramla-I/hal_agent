#!/usr/bin/env python3
"""Retrofit study — can ixy.rs, RedLeaf's ixgbe, and Redox's ixgbed run on the
generated intralingual 82599 HAL?

For each driver: extract every register it actually touches (from its own
offset constants / enum maps + the access-helper call sites), resolve each to
a BAR0 address, and join BY ADDRESS against (a) the full Table 8-2 register
list (380 registers, with aliases and array ranges) and (b) the 75 registers
of the generated HAL, plus the gated set. Names are only a cross-check —
an address whose datasheet register disagrees with the driver's own name for
it is a bug lead, not a join failure.

Outputs: retrofit/driver_analysis.json + a printed per-driver summary.
"""
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.join(HERE, "..", "pipeline")
sys.path.insert(0, PIPE)
from enumerate_targets import _RANGE_RE  # noqa: E402

CLONES = os.path.join(HERE, "clones")
GATED = {"FCTRL", "TDH", "HLREG0", "RDRXCTL", "DMATXCTL", "EIAC", "EEC", "EIAM"}


# ---------------------------------------------------------------------------
# datasheet-side resolver: address -> Table 8-2 register (aliases included)
# ---------------------------------------------------------------------------
def parse_all_ranges(offset_raw):
    """Like enumerate_targets.parse_offset_expr but keeps EVERY alternative
    (aliases after '/', extra banks after 'and'), tagged."""
    out = []
    for part in re.split(r"\s+and\s+", offset_raw.strip()):
        for ai, alt in enumerate(part.split("/")):
            m = _RANGE_RE.search(alt)
            if not m:
                continue
            base = int(m.group(1), 16)
            stride = int(m.group(2), 0) if m.group(2) else None
            shift = int(m.group(3)) if m.group(3) else 0
            n0 = int(m.group(4)) if m.group(4) else None
            n1 = int(m.group(5)) if m.group(5) else None
            start = base + (stride or 0) * ((n0 or 0) - shift) if stride else base
            count = (n1 - n0 + 1) if n0 is not None else None
            out.append({"start": start, "stride": stride, "count": count,
                        "alias": ai > 0})
    return out


def build_resolver():
    import csv
    rows = list(csv.DictReader(open(os.path.join(PIPE, "targets",
                                                 "datasheet_register_summary.csv"))))
    join = json.load(open(os.path.join(PIPE, "targets", "registers_join.json")))
    in75 = {r["abbrev_base"].upper() for r in join["registers"]}
    regs = []
    for r in rows:
        base = re.sub(r"\[[^\]]*\]$", "", r["abbrev"]).strip()
        base = re.sub(r"n$", "", base) if re.search(r"\dn$|[a-z]n$", base) else base
        ranges = parse_all_ranges(r["offset_raw"])
        # detail headings carry second banks the summary omits; reuse join info
        regs.append({"abbrev": base.upper(), "name": r["name"], "ranges": ranges})
    for j in join["registers"]:
        det = j.get("offset_raw_detail")
        if det:
            for rg in parse_all_ranges(det):
                regs.append({"abbrev": j["abbrev_base"].upper(),
                             "name": "", "ranges": [rg]})

    def resolve(addr):
        hits = []
        for rg_owner in regs:
            for rg in rg_owner["ranges"]:
                if rg["stride"] and rg["count"]:
                    span = rg["stride"] * rg["count"]
                    if rg["start"] <= addr < rg["start"] + span \
                       and (addr - rg["start"]) % rg["stride"] == 0:
                        hits.append((rg_owner["abbrev"], rg["alias"]))
                elif addr == rg["start"]:
                    hits.append((rg_owner["abbrev"], rg["alias"]))
        # prefer non-alias exact hits, dedupe preserving order
        hits.sort(key=lambda h: h[1])
        seen, out = set(), []
        for h in hits:
            if h[0] not in seen:
                seen.add(h[0])
                out.append(h)
        return out
    return resolve, in75


# ---------------------------------------------------------------------------
# per-driver extraction: {sym: {"addrs": [...], "ops": set, "sites": n}}
# ---------------------------------------------------------------------------
def parse_c_style_defs(path):
    """pub const IXGBE_X: u32 = 0x...; and pub fn IXGBE_X(i: u32) -> u32 {...}"""
    text = open(path).read()
    defs = {}
    for m in re.finditer(r"pub const IXGBE_([A-Z0-9_]+): u32\s*=\s*(0x[0-9A-Fa-f_]+)\s*;", text):
        defs[m.group(1)] = [int(m.group(2).replace("_", ""), 16)]
    for m in re.finditer(r"pub fn IXGBE_([A-Z0-9_]+)\(\w+: u32\) -> u32 \{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
                         text):
        name, body = m.groups()
        addrs = []
        for bm in re.finditer(r"(0x[0-9A-Fa-f_]+)", body):
            addrs.append(int(bm.group(1).replace("_", ""), 16))
        # first hex literal of each branch is the base; strides are small (<0x100)
        bases = [a for a in addrs if a >= 0x100 or a == 0x0]
        defs[name] = bases or addrs[:1]
    return defs


WRITE_HELPERS = r"set_reg32|set_flags32|clear_flags32|write_flag|clear_flag|write_reg|write_reg_idx|write_reg_tdt|write_reg_rdt"
READ_HELPERS = r"get_reg32|wait_clear_reg32|wait_set_reg32|wait_write_reg|wait_clear_reg|read_reg|read_reg_idx|read_qreg|wait_"


def scan_ixy_style(src_files, defs):
    used = defaultdict(lambda: {"ops": set(), "sites": 0})
    # (?<![\w]) so 'wait_write_reg' cannot match its embedded 'write_reg'
    call_re = re.compile(r"(?<![A-Za-z0-9_])(" + READ_HELPERS + r"|" + WRITE_HELPERS + r")\s*\(\s*"
                         r"(?:(?!IXGBE_)[\w.:]+,\s*)*IXGBE_([A-Z0-9_]+)")
    for path in src_files:
        for line in open(path):
            for m in call_re.finditer(line):
                helper, sym = m.groups()
                if sym not in defs:
                    continue
                op = "read" if re.match(READ_HELPERS, helper) else "write"
                if helper in ("set_flags32", "clear_flags32"):
                    used[sym]["ops"].add("read")
                used[sym]["ops"].add(op)
                used[sym]["sites"] += 1
    return {s: {"addrs": defs[s], **v} for s, v in used.items()}


def camel_to_snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).upper()


def scan_redleaf(root):
    regs_rs = open(os.path.join(root, "src", "ixgbe_regs.rs")).read()
    defs = {}
    # scalar enums: NAME = 0xADDR,
    for m in re.finditer(r"^\s{4}([A-Z][A-Z0-9_]*)\s*=\s*(0x[0-9A-Fa-f]+)\s*,",
                         regs_rs, re.M):
        defs[("IxgbeRegs", m.group(1))] = [int(m.group(2), 16)]
    # array reg base consts inside impls
    consts = {m.group(1): int(m.group(2), 16) for m in
              re.finditer(r"const ([A-Z0-9_]+): u64\s*=\s*(0x[0-9A-Fa-f]+)\s*;", regs_rs)}
    for enum in ("IxgbeDmaArrayRegs", "IxgbeNoDmaArrayRegs"):
        em = re.search(r"pub enum %s \{(.*?)\}" % enum, regs_rs, re.S)
        if not em:
            continue
        for v in re.finditer(r"([A-Z][A-Za-z0-9]*)\s*,", em.group(1)):
            snake = camel_to_snake(v.group(1))
            if snake in consts:
                defs[(enum, v.group(1))] = [consts[snake]]
    used = defaultdict(lambda: {"ops": set(), "sites": 0})
    lib = os.path.join(root, "src", "lib.rs")
    use_re = re.compile(r"(\w+)\s*\(\s*(?:&?\w+(?:\.\w+)*,\s*)*(Ixgbe(?:Dma|NoDma)?(?:Array)?Regs)::(\w+)")
    for line in open(lib):
        for m in use_re.finditer(line):
            helper, enum, variant = m.groups()
            key = (enum, variant)
            if key not in defs:
                continue
            op = "write" if "write" in helper else ("read" if ("read" in helper or "wait" in helper) else None)
            if op is None:
                continue
            used[key]["ops"].add(op)
            used[key]["sites"] += 1
    return {f"{e}::{v}": {"addrs": defs[(e, v)], **d, "sym_short": v}
            for (e, v), d in used.items()}


def analyze(name, used, resolve, in75):
    rows, summary = [], defaultdict(int)
    for sym, info in sorted(used.items()):
        hits = resolve(info["addrs"][0])
        abbrev = hits[0][0] if hits else None
        alias = hits[0][1] if hits else None
        short = info.get("sym_short", sym)
        name_norm = re.sub(r"[^A-Z0-9]", "", camel_to_snake(short) if not short.isupper()
                           else short)
        name_match = abbrev is not None and (
            re.sub(r"[^A-Z0-9]", "", abbrev) in name_norm
            or name_norm in re.sub(r"[^A-Z0-9]", "", abbrev))
        row = {
            "sym": sym, "addr": hex(info["addrs"][0]),
            "extra_addrs": [hex(a) for a in info["addrs"][1:]],
            "ops": sorted(info["ops"]), "sites": info["sites"],
            "matched": abbrev, "via_alias": alias,
            "in_generated_75": abbrev in in75 if abbrev else False,
            "gated": abbrev in GATED if abbrev else False,
            "name_agrees": name_match,
        }
        rows.append(row)
        summary["registers"] += 1
        summary["matched"] += bool(abbrev)
        summary["in_75"] += row["in_generated_75"]
        summary["gated_regs"] += row["gated"]
        if row["gated"] and "write" in info["ops"]:
            summary["gated_write_sites"] += info["sites"]
        if abbrev and not name_match:
            summary["name_disagreements"] += 1
        if not abbrev:
            summary["unmatched"] += 1
    return {"driver": name, "summary": dict(summary), "rows": rows}


def main():
    resolve, in75 = build_resolver()
    results = []

    ixy = os.path.join(CLONES, "ixy.rs", "src")
    defs = parse_c_style_defs(os.path.join(ixy, "constants.rs"))
    used = scan_ixy_style([os.path.join(ixy, f) for f in ("ixgbe.rs", "interrupts.rs")],
                          defs)
    results.append(analyze("ixy.rs (PF driver)", used, resolve, in75))

    rx = os.path.join(CLONES, "base", "drivers", "net", "ixgbed", "src")
    defs = parse_c_style_defs(os.path.join(rx, "ixgbe.rs"))
    used = scan_ixy_style([os.path.join(rx, f) for f in ("device.rs", "main.rs")], defs)
    results.append(analyze("redox ixgbed", used, resolve, in75))

    rl = os.path.join(CLONES, "redleaf", "lib", "devices", "ixgbe")
    used = scan_redleaf(rl)
    results.append(analyze("redleaf ixgbe", used, resolve, in75))

    out = os.path.join(HERE, "driver_analysis.json")
    json.dump(results, open(out, "w"), indent=2)
    for r in results:
        s = r["summary"]
        print(f"\n== {r['driver']} ==")
        print(f"  distinct registers used: {s.get('registers', 0)}; "
              f"address-matched to Table 8-2: {s.get('matched', 0)} "
              f"(unmatched: {s.get('unmatched', 0)})")
        print(f"  covered by the generated 75-register HAL: {s.get('in_75', 0)}")
        print(f"  gated registers touched: {s.get('gated_regs', 0)} "
              f"(write sites on gated registers: {s.get('gated_write_sites', 0)})")
        print(f"  driver-name vs datasheet-register disagreements (leads): "
              f"{s.get('name_disagreements', 0)}")
        missing = [x["sym"] for x in r["rows"] if x["matched"] and not x["in_generated_75"]]
        if missing:
            print(f"  in Table 8-2 but NOT yet generated ({len(missing)}): "
                  f"{', '.join(sorted(missing)[:20])}")
        for x in r["rows"]:
            if x["matched"] and not x["name_agrees"]:
                print(f"  LEAD name/address disagreement: {x['sym']} @ {x['addr']} "
                      f"resolves to {x['matched']}"
                      f"{' (alias range)' if x['via_alias'] else ''}")
        for x in r["rows"]:
            if not x["matched"]:
                print(f"  unmatched: {x['sym']} @ {x['addr']} ops={x['ops']}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
