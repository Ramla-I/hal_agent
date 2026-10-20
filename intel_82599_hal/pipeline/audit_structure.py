#!/usr/bin/env python3
"""Audit the non-subfield register-structure dimensions against the datasheet:
address OFFSET, register ACCESS code, and RESET value. The subfield bit
positions are audited separately (audit_full_subfields.py); this covers the
other three dimensions the reports claim, so none rests only on the emitter's
internal checks.

Standalone: reads the run's extracted JSONs + the datasheet (via the s1
heading/offset parsers). It does NOT read the other audits or the emitter.

Per register (the extraction vs the datasheet's own section heading + Init-Val
column, deterministic / no LLM):
  OFFSET  extracted address_offset == element-0 offset from the heading's
          offset expression (e.g. "0x01008 + 0x40*n" -> 0x01008).
  ACCESS  extracted register_access == heading access code (RW/RO/WO/RC/RW1C),
          canonicalized (RW1C->RW, RC->RO for the read/write-direction compare).
  RESET   extracted reset_value == the 32-bit value assembled from each field's
          Init-Val cell; if ANY field's Init Val is 'X'/undefined the datasheet
          leaves it undefined, so the extraction should be null.

Usage: python3 audit_structure.py r006
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from s1_enumerate_targets import parse_detail_headings, parse_offset_expr, DATASHEET_MD  # noqa: E402

RUN = sys.argv[1] if len(sys.argv) > 1 else "r006"


def canon_access(a):
    a = re.sub(r"[^A-Za-z0-9/]", "", str(a or "")).upper()
    if not a:
        return None
    a = a.split("/")[0]                      # "RO/RW" -> RO (heading's primary)
    return {"RW1C": "RW", "RW1S": "RW", "RC": "RO", "RO1C": "RO"}.get(a, a)


def parse_int(s):
    if s is None:
        return None
    m = re.search(r"0x[0-9A-Fa-f]+", str(s))
    if m:
        return int(m.group(0), 16)
    try:
        return int(str(s).strip())
    except ValueError:
        return None


def parse_initval(cell):
    """A field's Init-Val cell -> int, or None if undefined ('X'/'see desc')."""
    raw = str(cell)
    if "*" in raw:            # 82599 marks spec/EEPROM-derived defaults with '*',
        return None           # not a fixed hardware reset -> treat as undefined
    c = re.sub(r"[\\\s]", "", raw).strip()
    if c == "" or c.upper().startswith("X") or "see" in c.lower():
        return None
    if re.fullmatch(r"[01]+b", c):
        return int(c[:-1], 2)
    if re.fullmatch(r"0x[0-9A-Fa-f]+", c):
        return int(c, 16)
    if re.fullmatch(r"\d+", c):
        return int(c)
    return None


def datasheet_reset(section_lines):
    """Assemble the register reset from its field table's Init-Val column.
    Returns (value|None, defined) where defined is False if any field's Init
    Val is undefined (so the datasheet reset is undefined -> expect null)."""
    bitcol = namecol = initcol = None
    value, defined, saw_row = 0, True, False
    for line in section_lines:
        if not line.lstrip().startswith("|"):
            continue
        cells = [re.sub(r"\\([_\[\]*])", r"\1", c.strip())
                 for c in line.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        low = [c.lower() for c in cells]
        if "field" in low and any("bit" in c for c in low):
            bitcol = next(j for j, c in enumerate(low) if "bit" in c)
            namecol = low.index("field")
            initcol = next((j for j, c in enumerate(low) if "init" in c), None)
            continue
        if bitcol is None or initcol is None or len(cells) <= max(bitcol, initcol):
            continue
        bits = cells[bitcol].strip()
        m = re.fullmatch(r"(\d+)\s*:\s*(\d+)", bits) or re.fullmatch(r"(\d+)", bits)
        if not m:
            continue
        g = m.groups()
        hi, lo = (int(g[0]), int(g[1])) if len(g) == 2 and g[1] is not None else (int(g[0]), int(g[0]))
        lo, hi = min(lo, hi), max(lo, hi)
        saw_row = True
        iv = parse_initval(cells[initcol])
        if iv is None:
            defined = False
        else:
            width = hi - lo + 1
            value |= (iv & ((1 << width) - 1)) << lo
    if not saw_row:
        return None, None                    # no parseable field table
    return (value if defined else None), defined


def section_lines(reg, heads, lines, head_lines):
    h = heads.get(reg.lower()) or heads.get(reg.lower() + "n")
    if not h:
        return None
    start = h["line"]
    nxt = [l for l in head_lines if l > start]
    end = nxt[0] if nxt else len(lines) + 1
    return lines[start - 1:end - 1], h


def main():
    lines = open(DATASHEET_MD).readlines()
    heads = parse_detail_headings()
    head_lines = sorted({h["line"] for h in heads.values()})

    rows = []
    for p in sorted(glob.glob(os.path.join(HERE, "register_info", RUN, "*.json"))):
        reg = os.path.basename(p)[:-5]
        d = json.load(open(p))
        sec = section_lines(reg, heads, lines, head_lines)
        row = {"register": reg}
        if sec is None:
            row["note"] = "no datasheet heading"
            rows.append(row)
            continue
        seclines, h = sec

        # OFFSET
        ds = parse_offset_expr(h["offset_raw"])
        ds_off = ds["ranges"][0]["start_addr"] if ds.get("ranges") else None
        ex_off = parse_int(d.get("address_offset"))
        row["offset"] = {"extracted": hex(ex_off) if ex_off is not None else None,
                         "datasheet": hex(ds_off) if ds_off is not None else None,
                         "verdict": ("agree" if ex_off == ds_off and ex_off is not None
                                     else "disagree" if ex_off is not None and ds_off is not None
                                     else "unknown")}
        # ACCESS
        ex_acc, ds_acc = canon_access(d.get("register_access")), canon_access(h["rw"])
        row["access"] = {"extracted": d.get("register_access"), "datasheet": h["rw"],
                         "verdict": ("agree" if ex_acc and ex_acc == ds_acc
                                     else "disagree" if ex_acc and ds_acc else "unknown")}
        # RESET
        ds_reset, defined = datasheet_reset(seclines)
        ex_reset = parse_int(d.get("reset_value"))
        if defined is None:
            rv = "unknown"                       # no parseable field table
        elif not defined:
            # datasheet reset is undefined ('X'/'*') -> extraction should be null
            rv = "agree" if ex_reset is None else "extra"      # extra = assembled where undefined
        elif ex_reset is None:
            rv = "missing"                       # datasheet defines it; extraction nulled (recall gap)
        else:
            rv = "agree" if ex_reset == ds_reset else "wrong"  # wrong = a different value
        row["reset"] = {"extracted": (hex(ex_reset) if ex_reset is not None else None),
                        "datasheet": (hex(ds_reset) if ds_reset is not None else ("undefined" if defined is False else None)),
                        "verdict": rv}
        rows.append(row)

    def tally(dim):
        from collections import Counter
        return dict(Counter(r[dim]["verdict"] for r in rows if dim in r))

    summary = {d: tally(d) for d in ("offset", "access", "reset")}
    out = {"run": RUN, "registers": len(rows), "summary": summary, "rows": rows}
    json.dump(out, open(os.path.join(HERE, "..", "reports", "audit_structure.json"), "w"),
              indent=2)

    print(f"run {RUN}: {len(rows)} registers")
    for dim in ("offset", "access", "reset"):
        print(f"  {dim:7s}: {summary[dim]}")
        for r in rows:
            if dim in r and r[dim]["verdict"] in ("disagree", "wrong", "missing", "extra"):
                print(f"     {r[dim]['verdict'].upper()} {r['register']}.{dim}: "
                      f"extracted {r[dim]['extracted']} vs datasheet {r[dim]['datasheet']}")
    print("wrote reports/audit_structure.json")


if __name__ == "__main__":
    main()
