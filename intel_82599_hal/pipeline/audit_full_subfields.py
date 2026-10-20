#!/usr/bin/env python3
"""Audit ALL extracted subfields against the datasheet's own field tables.

The datasheet detail section for each register carries a bit-layout table
(Field | Bit(s) | Init Val | Description). This parses those tables
deterministically (no LLM) and diffs them field-by-field against the
extraction, so every one of the 406 subfields gets a referee. It is the
strongest referee available \u2014 the ground-truth document itself \u2014 and
independent of the extraction path (a different, mechanical reader), so a
disagreement is an LLM extraction error or a parser artifact, resolved by
hand against the raw text.

Per register, the parser scans from its detail heading to the next numbered
register section, collecting every table row whose Bit(s) cell is `m:l` or a
single bit, merging continuation tables across page-break headers.

Join (by bit position, the unambiguous key):
  - AGREE      extracted (lo,hi) equals a datasheet row's (lo,hi) [+ name check]
  - NAME_DIFF  same (lo,hi) present, but names disagree -> adjudicate
  - ONLY_EXTRACTION  extracted (lo,hi) matches no datasheet row -> a field
               present ONLY in the extraction, not the datasheet (the
               precision-side counterpart to MISSED), e.g. RDRXCTL.Drop_En
  - MISSED     datasheet field row with no extracted field at those bits (recall)

Registers whose field table the parser cannot locate are listed as
UNPARSED (never scored as agree). Usage: python3 audit_full_subfields.py r006
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from s1_enumerate_targets import parse_detail_headings, DATASHEET_MD  # noqa: E402

RUN = sys.argv[1] if len(sys.argv) > 1 else "r006"


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def parse_bits(cell):
    cell = cell.strip()
    m = re.fullmatch(r"(\d+)\s*:\s*(\d+)", cell)
    if m:
        hi, lo = int(m.group(1)), int(m.group(2))
        return (min(lo, hi), max(lo, hi))
    if re.fullmatch(r"\d+", cell):
        return (int(cell), int(cell))
    return None


def datasheet_fields(reg, heads, lines, head_lines):
    """Return list of (name, lo, hi) rows from reg's detail section, or None.
    The section runs from reg's heading to the NEXT different register's heading
    (head_lines = sorted heading line numbers); same-register repeats (LINKS,
    EICR document two tables under one abbrev) are merged, since they share a
    line only via the first occurrence."""
    h = heads.get(reg.lower()) or heads.get(reg.lower() + "n")
    if not h:
        return None
    start = h["line"]  # 1-indexed heading line
    nexts = [l for l in head_lines if l > start]
    end = nexts[0] if nexts else len(lines) + 1
    fields = []
    bitcol = None
    for i in range(start, end):
        line = lines[i - 1].rstrip("\n")
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        cells = [re.sub(r"\\([_\[\]*])", r"\1", c) for c in cells]
        if set("".join(cells)) <= set("-: "):
            continue  # md separator row
        low = [c.lower() for c in cells]
        if "field" in low and any("bit" in c for c in low):
            bitcol = next(j for j, c in enumerate(low) if "bit" in c)
            namecol = low.index("field")
            continue
        if bitcol is None or len(cells) <= bitcol:
            continue
        bits = parse_bits(cells[bitcol])
        if bits is None:
            continue
        name = cells[namecol] if namecol < len(cells) else cells[0]
        fields.append((name, bits[0], bits[1]))
    return fields or None


def main():
    lines = open(DATASHEET_MD).readlines()
    heads = parse_detail_headings()

    head_lines = sorted({h["line"] for h in heads.values()})
    rows = []
    unparsed = []
    for p in sorted(glob.glob(os.path.join(HERE, "register_info", RUN, "*.json"))):
        reg = os.path.basename(p)[:-5]
        d = json.load(open(p))
        ext = []
        for sf in d.get("subfields") or []:
            bn = sf.get("bit_number") or {}
            if bn.get("start_bit") is not None:
                ext.append((sf["name"], bn["start_bit"], bn["end_bit"]))
        ds = datasheet_fields(reg, heads, lines, head_lines)
        if ds is None:
            unparsed.append((reg, len(ext)))
            continue
        ds_by_bits = {}
        for n, lo, hi in ds:
            ds_by_bits.setdefault((lo, hi), []).append(n)
        for n, lo, hi in ext:
            reserved = norm(n).startswith(("reserv", "rsv"))
            if (lo, hi) in ds_by_bits:
                names = ds_by_bits[(lo, hi)]
                hit = any(norm(n) == norm(dn) or (len(norm(n)) >= 3 and len(norm(dn)) >= 3
                          and (norm(n) in norm(dn) or norm(dn) in norm(n))) for dn in names)
                grade = "AGREE" if (hit or reserved) else "NAME_DIFF"
            else:
                grade = "ONLY_EXTRACTION"
            rows.append({"reg": reg, "name": n, "lo": lo, "hi": hi,
                         "reserved": reserved, "grade": grade,
                         "ds_names": ds_by_bits.get((lo, hi), [])})
        # recall: datasheet non-reserved rows with no extracted field at those bits
        ext_bits = {(lo, hi) for _, lo, hi in ext}
        for n, lo, hi in ds:
            if norm(n).startswith(("reserv", "rsv")):
                continue
            if (lo, hi) not in ext_bits:
                rows.append({"reg": reg, "name": n, "lo": lo, "hi": hi,
                             "reserved": False, "grade": "MISSED", "ds_names": []})

    from collections import Counter
    g = Counter(r["grade"] for r in rows)
    scored_regs = len({r["reg"] for r in rows})
    print(f"run {RUN}: parsed field tables for {scored_regs} registers; "
          f"{len(unparsed)} unparsed")
    print(f"grades: {dict(g)}")
    for grade in ("ONLY_EXTRACTION", "NAME_DIFF", "MISSED"):
        flagged = [r for r in rows if r["grade"] == grade]
        if flagged:
            print(f"\n--- {grade} ({len(flagged)}) ---")
            for r in flagged:
                print(f"  {r['reg']:11s} {r['name']:32s} {r['hi']}:{r['lo']}"
                      + (f"   ds@bits={r['ds_names']}" if r["ds_names"] else ""))
    if unparsed:
        print(f"\n--- UNPARSED registers ({len(unparsed)}) ---")
        print("  " + ", ".join(f"{r}({n})" for r, n in unparsed))
    json.dump({"run": RUN, "grades": dict(g), "unparsed": unparsed, "rows": rows},
              open(os.path.join(HERE, "..", "reports", "audit_full_subfields.json"), "w"), indent=2)
    print("\nwrote audit_full_subfields.json")


if __name__ == "__main__":
    main()
