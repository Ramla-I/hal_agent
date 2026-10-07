#!/usr/bin/env python3
"""Step 1 — enumerate the two register target sets for the 82599 case study.

Outputs (committed, small, reproducible):
  targets/driver_registers.json        registers the current Theseus ixgbe driver
                                       actually touches (the compile target),
                                       with struct, layout, and usage info parsed
                                       from reference/src/
  targets/driver_constants.json        regs.rs bit-field constants the driver
                                       references (field-level target set)
  targets/datasheet_register_summary.csv  every row of Table 8-2 in 82599.md
                                       (the recall denominator)
  targets/join_report.md               driver<->datasheet name join + counts +
                                       unmatched names (seeds name_map.json;
                                       every manual entry there = logged friction)

Run:  python3 enumerate_targets.py   (from intel_82599_hal/pipeline/)
"""
import csv
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REF_SRC = os.path.join(HERE, "..", "reference", "src")
DATASHEET_MD = os.path.join(HERE, "..", "..", "devices", "intel", "82599", "82599.md")
OUT = os.path.join(HERE, "targets")

DRIVER_FILES = ["lib.rs", "virtual_function.rs", "queue_registers.rs", "test_packets.rs"]
REGS_RS = os.path.join(REF_SRC, "regs.rs")


# --------------------------------------------------------------------------
# Parse regs.rs: struct -> ordered fields (name, type, array len, offset comment)
# --------------------------------------------------------------------------
def parse_regs_rs():
    structs = {}
    cur = None
    field_re = re.compile(
        r"^\s*(?:pub\s+)?([a-z0-9_]+):\s+"
        r"(?:\[)?\s*(Volatile|ReadOnly|WriteOnly|RegistersRx|RegistersTx|u8)"
        r"(?:<u32>)?\s*(?:;\s*(\d+)\s*\])?\s*,\s*(?://\s*(.*))?$"
    )
    with open(REGS_RS) as f:
        for line in f:
            m = re.match(r"pub struct (\w+)", line)
            if m:
                cur = m.group(1)
                structs[cur] = []
                continue
            if cur is None:
                continue
            if line.startswith("}"):
                cur = None
                continue
            fm = field_re.match(line)
            if fm:
                name, ty, arr, comment = fm.groups()
                structs[cur].append({
                    "field": name,
                    "type": ty,
                    "array_len": int(arr) if arr else None,
                    "offset_comment": (comment or "").strip().rstrip(";").strip(),
                })
    return structs


# --------------------------------------------------------------------------
# Parse driver sources: which register fields are read/written
# --------------------------------------------------------------------------
def parse_driver_usage(register_fields):
    """register_fields: set of field names defined in regs.rs (non-padding)."""
    usage = defaultdict(set)  # field -> {"read","write"}
    # any receiver: regsN. / rxq. / txq. / self.regs. etc.
    acc_re = re.compile(r"\.([a-z0-9_]+)(?:\[[^\]]*\])?\s*\.\s*(read|write|iter_mut|iter)\b")
    for fn in DRIVER_FILES:
        path = os.path.join(REF_SRC, fn)
        with open(path) as f:
            text = f.read()
        for m in acc_re.finditer(text):
            field, meth = m.groups()
            if field not in register_fields:
                continue
            if meth == "read":
                usage[field].add("read")
            elif meth == "write":
                usage[field].add("write")
            else:  # iter/iter_mut over a register array; look at loop body writes
                usage[field].add("iter")
        # `for x in regs.NAME.iter_mut() { x.write(..) }` -> treat iter as write
        for m in re.finditer(r"for\s+\w+\s+in\s+[\w.]+\.([a-z0-9_]+)\.iter_mut\(\)", text):
            if m.group(1) in register_fields:
                usage[m.group(1)].add("write")
    return usage


# --------------------------------------------------------------------------
# Parse regs.rs constants + which the driver references
# --------------------------------------------------------------------------
def parse_constants():
    consts = {}
    with open(REGS_RS) as f:
        for line in f:
            m = re.match(r"pub const ([A-Z0-9_]+):\s*(\w+)\s*=\s*(.+?);", line.strip())
            if m:
                consts[m.group(1)] = {"type": m.group(2), "value": m.group(3).strip()}
    used = set()
    for fn in DRIVER_FILES:
        with open(os.path.join(REF_SRC, fn)) as f:
            text = f.read()
        for name in consts:
            if re.search(r"\b%s\b" % re.escape(name), text):
                used.add(name)
    return consts, used


# --------------------------------------------------------------------------
# Parse Table 8-2 register summary out of 82599.md
# --------------------------------------------------------------------------
def parse_table_8_2():
    """Parse every register row of the PF BAR0 summary (Table 8-2).

    The summary spans many markdown tables between the '8.2.2 Registers
    Summary PF - BAR 0' header and the '8.2.3 Detailed Register Descriptions'
    header, interleaved with category sub-headers and page markers, and one
    table has its columns shifted (offset header detached -> no Reset column).
    Robust rule: within that range, any table row whose first cell starts with
    0x is a register row.
    """
    with open(DATASHEET_MD) as f:
        lines = f.readlines()
    start = end = None
    for i, line in enumerate(lines):
        if start is None and re.match(r"#\s*8\.2\.2\s", line):
            start = i
        if re.match(r"#\s*8\.2\.3\s", line):
            end = i
            break
    assert start is not None and end is not None, "summary range not found"

    rows, section = [], ""
    for line in lines[start:end]:
        if line.startswith("#"):
            h = line.lstrip("#").strip()
            if "Intel" not in h and "Table 8-2" not in h and "8.2.2" not in h:
                section = h
            continue
        if not line.strip().startswith("|"):
            continue
        cells = [re.sub(r"\\([_\[\]*])", r"\1", c.strip())
                 for c in line.strip().strip("|").split("|")]
        if not cells or not cells[0].lower().startswith("0x"):
            continue
        cells = (cells + [""] * 7)[:7]
        offset, abbrev, name, block, rw, c5, c6 = cells
        if c6.strip():                       # normal: Reset, Page present
            reset, page = c5, c6
        elif re.fullmatch(r"\d+", c5.strip()):  # shifted table: c5 is the page
            reset, page = "", c5
        else:
            reset, page = c5, ""
        rows.append({
            "offset_raw": offset, "abbrev": abbrev, "name": name,
            "block": block, "rw": rw, "reset": reset, "page": page,
            "section": section,
        })
    return rows


def parse_detail_headings():
    """Parse every detailed register-description heading:

        # <Full Name> \u2014 ABBREV[n] (<offset expr>; <ACCESS>)

    Returns {abbrev_base_lower: {"abbrev", "offset_raw", "rw", "line"}} keeping
    the FIRST occurrence (PF sections precede any VF/duplicate mention). The
    Table 8-2 summary omits second register banks (e.g. the 0x0D000 Rx queue
    bank) that these headings carry, so the join records both sources.
    """
    # separator is an em-dash or a plain hyphen glued to the name ("...Register- EICR");
    # the offset expr may itself contain parentheses ("4*(n-24)") — split at the LAST ';'
    head_re = re.compile(r"^#+\s*(?:[\d.]+\s+)?(.*?)\s*(?:\u2014|-)\s*"
                         r"([A-Z0-9_]+n?(?:\[[^\]]*\])?)\s*\((.*);\s*([^);]*)\)")
    out = {}
    with open(DATASHEET_MD) as f:
        for ln, line in enumerate(f, 1):
            if not line.startswith("#"):
                continue
            m = head_re.match(line.strip())
            if not m:
                continue
            _name, abbrev, expr, rw = m.groups()
            if "0x" not in expr:
                continue
            base = abbrev_base(abbrev).lower()
            keys = [base]
            # FCTTVn-style trailing index letter (no brackets)
            if base.endswith("n") and "n=" in expr.replace(" ", ""):
                keys.append(base[:-1])
            for k in keys:
                if k not in out:
                    out[k] = {"abbrev": abbrev, "offset_raw": expr.strip(),
                              "rw": rw.strip(), "line": ln}
    return out


def abbrev_base(abbrev):
    """Normalize a Table 8-2 abbreviation to a joinable base name.

    'FCRTL[n]' -> FCRTL ; 'FCTTVn' -> FCTTV ; 'RAL0/RAL[n]' handled per-row;
    'GSCL_5_8' stays as-is. Lowercased for join with driver field names.
    """
    a = abbrev.strip()
    a = re.sub(r"\s+", "", a)
    a = re.sub(r"\[[^\]]*\]$", "", a)      # trailing [n]
    a = re.sub(r"\((\w+)\)$", "", a)       # trailing (n)
    # trailing index letter n only when offset suggests an array is handled by caller
    return a


_RANGE_RE = re.compile(
    r"(0x[0-9A-Fa-f]+)"                                   # base
    r"(?:\s*\+\s*(0x[0-9A-Fa-f]+|\d+)\s*\*\s*\(?\s*n(?:\s*-\s*(\d+))?\s*\)?)?"  # +stride*(n-k)
    r"(?:\s*,\s*n\s*=\s*(\d+)\s*(?:\.\.\.|\u2026)\s*(\d+))?"                        # , n=A...B
)


def parse_offset_expr(offset_raw):
    """Deterministically parse a Table 8-2 offset expression into ranges.

    Handles: plain '0x00008'; alias '0x00000 / 0x00004' (first kept, alias
    recorded); arrays '0x01000+0x40*n, n=0...63'; shifted second banks
    '0x0D000 + 0x40*(n-64), n=64...127'; multi-range 'A and B'; hex or
    decimal strides; unicode ellipsis. Returns {"ranges": [...], "alias_raw":
    str|None}; each range = {base, stride, n_first, n_last, count} with ints
    (stride/count None for scalars).
    """
    s = offset_raw.strip()
    parts = re.split(r"\s+and\s+", s)
    ranges, alias_raw = [], None
    for pi, part in enumerate(parts):
        aliases = [a.strip() for a in part.split("/")]
        if len(aliases) > 1:
            alias_raw = "/".join(aliases[1:])
        m = _RANGE_RE.search(aliases[0])
        if not m:
            return {"ranges": [], "alias_raw": alias_raw, "unparsed": s}
        base = int(m.group(1), 16)
        stride = m.group(2)
        stride = int(stride, 0) if stride else None
        shift = int(m.group(3)) if m.group(3) else 0
        n_first = int(m.group(4)) if m.group(4) else None
        n_last = int(m.group(5)) if m.group(5) else None
        count = (n_last - n_first + 1) if n_first is not None else None
        # element-0 address of THIS range: base + stride*(n_first - shift)
        start_addr = base
        if stride is not None and n_first is not None:
            start_addr = base + stride * (n_first - shift)
        ranges.append({
            "base": base, "stride": stride, "n_first": n_first,
            "n_last": n_last, "count": count, "start_addr": start_addr,
        })
    return {"ranges": ranges, "alias_raw": alias_raw}


def main():
    os.makedirs(OUT, exist_ok=True)

    structs = parse_regs_rs()
    # non-padding register fields, with their struct
    field_info = {}
    for sname, fields in structs.items():
        for fdict in fields:
            if fdict["field"].startswith("_padding"):
                continue
            field_info[fdict["field"]] = dict(fdict, struct=sname)
    # rx_regs1/rx_regs2/tx_regs are containers of RegistersRx/Tx, not registers
    containers = {k for k, v in field_info.items() if v["type"] in ("RegistersRx", "RegistersTx")}

    usage = parse_driver_usage(set(field_info))
    consts, used_consts = parse_constants()

    driver_regs = []
    for field, info in sorted(field_info.items()):
        if field in containers:
            continue
        u = usage.get(field, set())
        driver_regs.append({
            "field": field,
            "struct": info["struct"],
            "access_type": info["type"],
            "array_len": info["array_len"],
            "offset_comment": info["offset_comment"],
            "driver_uses": sorted(u - {"iter"}) if u else [],
            "in_driver_set": bool(u),
        })
    n_driver_needed = sum(1 for r in driver_regs if r["in_driver_set"])

    with open(os.path.join(OUT, "driver_registers.json"), "w") as f:
        json.dump({
            "note": "Registers defined in reference regs.rs; in_driver_set = "
                    "touched by the current Theseus ixgbe driver (lib.rs etc.). "
                    "The generated HAL must reproduce ALL fields for a drop-in "
                    "layout; in_driver_set is the end-to-end compile target.",
            "counts": {
                "defined_in_regs_rs": len(driver_regs),
                "driver_needed": n_driver_needed,
            },
            "registers": driver_regs,
        }, f, indent=2)

    with open(os.path.join(OUT, "driver_constants.json"), "w") as f:
        json.dump({
            "note": "pub consts in regs.rs; used = referenced by driver sources. "
                    "These are the field/bit-level specs the driver depends on.",
            "counts": {"defined": len(consts), "driver_used": len(used_consts)},
            "constants": {k: dict(v, driver_used=(k in used_consts))
                          for k, v in sorted(consts.items())},
        }, f, indent=2)

    ds_rows = parse_table_8_2()
    with open(os.path.join(OUT, "datasheet_register_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["offset_raw", "abbrev", "name", "block",
                                          "rw", "reset", "page", "section"])
        w.writeheader()
        w.writerows(ds_rows)

    # ---- join driver field names <-> datasheet abbreviations ----
    ds_by_base = defaultdict(list)
    for r in ds_rows:
        base = abbrev_base(r["abbrev"]).lower()
        ds_by_base[base].append(r)
        # FCTTVn-style: also register the n-stripped variant
        if re.search(r"[a-z0-9]n$", base) and ("n=" in r["offset_raw"].replace(" ", "")):
            ds_by_base[base[:-1]].append(r)

    matched, unmatched = [], []
    for r in driver_regs:
        base = r["field"].lower()
        hits = ds_by_base.get(base, [])
        if hits:
            matched.append((r, hits))
        else:
            unmatched.append(r)

    detail = parse_detail_headings()
    join_out = []
    for r, hits in matched:
        h = hits[0]
        det = detail.get(abbrev_base(h["abbrev"]).lower())
        join_out.append({
            "field": r["field"],
            "struct": r["struct"],
            "access_type_ref": r["access_type"],
            "array_len_ref": r["array_len"],
            "offset_comment_ref": r["offset_comment"],
            "driver_uses": r["driver_uses"],
            "in_driver_set": r["in_driver_set"],
            "abbrev": h["abbrev"],
            "abbrev_base": abbrev_base(h["abbrev"]),
            "offset_raw": h["offset_raw"],
            "rw": h["rw"],
            "section": h.get("section", ""),
            "offset_parsed": parse_offset_expr(h["offset_raw"]),
            "offset_raw_detail": det["offset_raw"] if det else None,
            "rw_detail": det["rw"] if det else None,
            "offset_parsed_detail": parse_offset_expr(det["offset_raw"]) if det else None,
        })
    with open(os.path.join(OUT, "registers_join.json"), "w") as f:
        json.dump({
            "note": "Machine-readable driver<->Table 8-2 join. offset_parsed is "
                    "deterministic geometry (base/stride/count) from the summary "
                    "offset expression; *_ref fields are the reference regs.rs "
                    "shape (used for evaluation only, never fed to generation).",
            "registers": join_out,
        }, f, indent=2)
    unparsed = [j["field"] for j in join_out if j["offset_parsed"].get("unparsed")]
    assert not unparsed, f"offset expressions failed to parse: {unparsed}"

    uniq_ds_abbrevs = {abbrev_base(r["abbrev"]).lower() for r in ds_rows}
    lines = []
    lines.append("# Driver <-> Table 8-2 join report\n")
    lines.append(f"- Table 8-2 rows parsed: **{len(ds_rows)}** "
                 f"({len(uniq_ds_abbrevs)} unique abbreviation bases)")
    lines.append(f"- regs.rs registers: **{len(driver_regs)}** "
                 f"(driver-needed: **{n_driver_needed}**)")
    lines.append(f"- Auto-joined by name: **{len(matched)}** / {len(driver_regs)}")
    lines.append(f"- Unmatched (need name_map.json entries — logged friction): "
                 f"**{len(unmatched)}**\n")
    if unmatched:
        lines.append("## Unmatched regs.rs fields")
        lines.append("| field | struct | offset comment | driver-needed |")
        lines.append("|---|---|---|---|")
        for r in unmatched:
            lines.append(f"| {r['field']} | {r['struct']} | {r['offset_comment']} "
                         f"| {'yes' if r['in_driver_set'] else 'no'} |")
    lines.append("\n## Auto-join (field -> datasheet abbrev @ offset)")
    lines.append("| field | abbrev | offset_raw | rw |")
    lines.append("|---|---|---|---|")
    for r, hits in matched:
        h = hits[0]
        lines.append(f"| {r['field']} | {h['abbrev']} | {h['offset_raw']} | {h['rw']} |")
    with open(os.path.join(OUT, "join_report.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Table 8-2 rows: {len(ds_rows)}  (unique bases: {len(uniq_ds_abbrevs)})")
    print(f"regs.rs registers: {len(driver_regs)}  driver-needed: {n_driver_needed}")
    print(f"auto-joined: {len(matched)}  unmatched: {len(unmatched)}")
    for r in unmatched:
        print("  unmatched:", r["field"], "|", r["offset_comment"],
              "| needed" if r["in_driver_set"] else "")


if __name__ == "__main__":
    main()
