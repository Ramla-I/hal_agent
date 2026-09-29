#!/usr/bin/env python3
"""Step 4 (structural part) — emit the generated regs.rs from an extraction run.

Inputs:
  register_info/<run>/<ABBREV>.json   LLM-extracted specs (offsets, access, fields)
  targets/registers_join.json         deterministic Table 8-2 geometry (stride/count)
  packaging.json                      the driver-API packaging contract (struct split,
                                      naming rule) — interface shape, not datasheet fact
  name_map.json (optional)            abbrev -> driver field name exceptions (friction)
  constants_map.json (optional)       driver const name -> field-derived expression

Offset policy (--offset-source, default "llm"): the LLM's extracted offset is
authoritative — this is the extraction experiment. The Table 8-2 parse is the
deterministic cross-check; disagreements and fallbacks (LLM offset missing or
colliding) are counted and listed in the emit report. Array geometry (stride,
count) always comes from the Table 8-2 parse (the LLM does not emit dims).

Array rules (documented divergences produce the reference shape from geometry):
  R1 contiguous stride-4 range        -> [Volatile<u32>; count]
  R2 non-contiguous stride (8, 0x40)  -> element n=0 as a scalar (interleaved
     banks like RAL/RAH; per-queue registers are instead folded into the queue
     element struct when their range starts inside a queue region)
  R3 ranges after the first           -> skipped (the driver models only the
     first bank; the 0xD000 Rx bank is range 2 of the queue registers and IS
     emitted, via its queue region)

Output: hal_out/<run>/regs.rs + hal_out/<run>/emit_report.json
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_json(path, default=None):
    if default is not None and not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def parse_hex(s):
    if s is None:
        return None
    m = re.search(r"0x[0-9A-Fa-f]+", str(s))
    if m:
        return int(m.group(0), 16)
    try:
        return int(str(s).strip())
    except ValueError:
        return None


def map_access(code, subfields):
    """Register-level access code -> volatile wrapper type."""
    if code:
        c = str(code).strip().upper()
        if re.fullmatch(r"WO", c):
            return "WriteOnly"
        if c in ("RO", "RC"):
            return "ReadOnly"
        if c:
            return "Volatile"
    # fallback: fold non-reserved subfield accesses
    accs = {s.get("access") for s in (subfields or [])
            if not str(s.get("name", "")).lower().startswith("reserv")}
    if accs == {"read-only"}:
        return "ReadOnly"
    if accs == {"write-only"}:
        return "WriteOnly"
    return "Volatile"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", help="run tag under register_info/, e.g. r003")
    ap.add_argument("--offset-source", choices=["llm", "summary"], default="llm")
    ap.add_argument("--no-overrides", action="store_true",
                    help="pure datasheet access typing (no adjudicated overrides)")
    args = ap.parse_args()

    run_dir = os.path.join(HERE, "register_info", args.run)
    out_dir = os.path.join(HERE, "hal_out", args.run)
    os.makedirs(out_dir, exist_ok=True)

    join = {r["abbrev_base"].upper(): r
            for r in load_json(os.path.join(HERE, "targets", "registers_join.json"))["registers"]}
    pack = load_json(os.path.join(HERE, "packaging.json"))
    name_map = {k.upper(): v for k, v in
                load_json(os.path.join(HERE, "name_map.json"), default={}).items()
                if not k.startswith("_")}
    overrides = load_json(os.path.join(HERE, "access_overrides.json"),
                          default={"overrides": {}})["overrides"]

    report = {"offset_mismatches": [], "offset_fallbacks": [], "collisions": [],
              "access": [], "missing_specs": [], "skipped_ranges": [],
              "scalar_from_strided": []}

    # ---- collect per-register placement decisions ----
    entries = []          # placed registers: dict(name, addr, type, array, ...)
    for abbrev, j in sorted(join.items()):
        spec_path = os.path.join(run_dir, abbrev + ".json")
        spec = load_json(spec_path) if os.path.exists(spec_path) else None
        if spec is None:
            report["missing_specs"].append(abbrev)
            spec = {}
        # detail-heading geometry carries second banks the summary omits
        gp = j.get("offset_parsed_detail") or j["offset_parsed"]
        geo = gp["ranges"] if gp["ranges"] else j["offset_parsed"]["ranges"]
        summary_addr = geo[0]["start_addr"] if geo else None
        llm_addr = parse_hex(spec.get("address_offset"))

        addr = llm_addr if args.offset_source == "llm" else summary_addr
        if addr is None:
            addr = summary_addr
            report["offset_fallbacks"].append(
                {"register": abbrev, "reason": "no LLM offset", "used": summary_addr})
        if llm_addr is not None and summary_addr is not None and llm_addr != summary_addr:
            report["offset_mismatches"].append(
                {"register": abbrev, "llm": hex(llm_addr), "summary": hex(summary_addr)})

        rtype = map_access(spec.get("register_access"), spec.get("subfields"))
        if abbrev in overrides and not args.no_overrides:
            report.setdefault("access_overridden", []).append(
                {"register": abbrev, "datasheet_type": rtype,
                 "override": overrides[abbrev]["type"]})
            rtype = overrides[abbrev]["type"]
        report["access"].append({"register": abbrev,
                                 "code": spec.get("register_access"),
                                 "type": rtype,
                                 "ref": j["access_type_ref"]})

        r0 = geo[0] if geo else {"stride": None, "count": None}
        for extra in geo[1:]:
            # range 2+ : emitted only if it starts inside a queue region
            in_queue = any(reg.get("queue_container")
                           and reg["start"] <= extra["start_addr"] < reg["end"]
                           for reg in pack["regions"])
            if in_queue:
                entries.append(dict(abbrev=abbrev, j=j, spec=spec, addr=extra["start_addr"],
                                    rtype=rtype, stride=extra["stride"], count=extra["count"]))
            else:
                report["skipped_ranges"].append({"register": abbrev,
                                                 "range_start": hex(extra["start_addr"])})
        entries.append(dict(abbrev=abbrev, j=j, spec=spec, addr=addr, rtype=rtype,
                            stride=r0["stride"], count=r0["count"]))

    # ---- assign to regions; build member lists ----
    regions = [dict(r) for r in pack["regions"]]
    for r in regions:
        r["members"] = []
    for e in entries:
        if e["addr"] is None:
            continue
        home = next((r for r in regions if r["start"] <= e["addr"] < r["end"]), None)
        if home is None:
            report["collisions"].append({"register": e["abbrev"], "addr": hex(e["addr"]),
                                         "reason": "outside 0x0-0x20000"})
            continue
        home["members"].append(e)

    lines = []
    w = lines.append
    w("//! Register structs for the Intel 82599 10 GbE controller, GENERATED from the")
    w("//! datasheet by the hal_agent pipeline (intel_82599_hal case study).")
    w("//! Packaging (struct split, field naming) follows the driver contract in")
    w("//! packaging.json; offsets, access types, and array sizes are extracted.")
    w("")
    w("use volatile::{Volatile, ReadOnly, WriteOnly};")
    w("use zerocopy::FromBytes;")
    w("")

    def field_name(abbrev):
        return name_map.get(abbrev, abbrev.lower())

    def emit_struct(struct_name, doc, members, start, end, elem_mode=False):
        """members: entries sorted by addr. elem_mode: offsets relative to start,
        struct covers [start, end) of ONE element (queue struct)."""
        pad_i = [0]
        w(f"/// {doc}")
        w("#[derive(FromBytes)]")
        w("#[repr(C)]")
        w(f"pub struct {struct_name} {{")
        cursor = start
        for m in sorted(members, key=lambda x: x["addr"]):
            addr = m["addr"]
            if addr < cursor:
                report["collisions"].append(
                    {"register": m["abbrev"], "addr": hex(addr),
                     "struct": struct_name,
                     "reason": f"overlaps previous field (cursor {hex(cursor)})"})
                continue
            if addr > cursor:
                w(f"    _padding{pad_i[0]}: [u8; {addr - cursor}], // {hex(cursor)} - {hex(addr - 1)}")
                pad_i[0] += 1
            name = field_name(m["abbrev"])
            fullname = m["j"]["abbrev"] if not elem_mode else m["j"]["abbrev"]
            doc_name = m.get("doc_name") or ""
            if doc_name:
                w(f"    /// {doc_name}")
            if m["count"] and m["stride"] == 4 and not elem_mode:
                w(f"    pub {name}: [{m['rtype']}<u32>; {m['count']}], // {hex(addr)} - {hex(addr + 4 * m['count'] - 1)}")
                cursor = addr + 4 * m["count"]
            else:
                w(f"    pub {name}: {m['rtype']}<u32>, // {hex(addr)}")
                cursor = addr + 4
                if m["count"] and m["stride"] not in (4, None) and not elem_mode:
                    report["scalar_from_strided"].append(
                        {"register": m["abbrev"], "stride": m["stride"],
                         "count": m["count"], "rule": "R2 element-0 scalar"})
        if cursor < end:
            w(f"    _padding{pad_i[0]}: [u8; {end - cursor}], // {hex(cursor)} - {hex(end - 1)}")
        w("}")
        w("")
        w(f"const _: () = assert!(core::mem::size_of::<{struct_name}>() == {end - start});")
        w("")

    # names for doc comments come from the summary (datasheet full names)
    import csv
    names = {}
    with open(os.path.join(HERE, "targets", "datasheet_register_summary.csv")) as f:
        for row in csv.DictReader(f):
            base = re.sub(r"\[[^\]]*\]$", "", row["abbrev"]).strip().upper()
            names.setdefault(base, row["name"])

    queue_elem_emitted = {}
    for r in regions:
        qc = r.get("queue_container")
        for m in r["members"]:
            m["doc_name"] = names.get(m["abbrev"], "")
        if qc:
            # queue region: members define the element struct (offsets mod stride)
            elem = qc["elem_struct"]
            if elem not in queue_elem_emitted:
                elem_members = []
                strides = {m["stride"] for m in r["members"]}
                bad = [m for m in r["members"] if m["stride"] != 64]
                for m in bad:
                    report["collisions"].append(
                        {"register": m["abbrev"], "addr": hex(m["addr"]),
                         "struct": elem, "reason": f"stride {m['stride']} != 0x40 in queue region"})
                elem_members = [dict(m, addr=m["addr"] - r["start"], count=None)
                                for m in r["members"] if m["stride"] == 64]
                queue_elem_emitted[elem] = (qc["elem_doc"], elem_members)
            # region struct is just the container array
            w(f"/// {r['doc']}")
            w("#[derive(FromBytes)]")
            w("#[repr(C)]")
            w(f"pub struct {r['struct']} {{")
            w(f"    /// {qc['field_doc']}")
            w(f"    pub {qc['field']}: [{qc['elem_struct']}; {qc['count']}], // {hex(r['start'])} - {hex(r['end'] - 1)}")
            w("}")
            w("")
            w(f"const _: () = assert!(core::mem::size_of::<{r['struct']}>() == {r['end'] - r['start']});")
            w("")
        else:
            emit_struct(r["struct"], r["doc"], r["members"], r["start"], r["end"])

    # queue element structs (64 B each)
    for elem, (doc, members) in queue_elem_emitted.items():
        emit_struct(elem, doc, members, 0, 64, elem_mode=True)

    # whole-space assert, as in the reference
    w("// check that the sum of all the register structs is equal to the memory of the ixgbe device (128 KiB).")
    w("const _: () = assert!(")
    for i, r in enumerate(regions):
        sep = "    + " if i else "    "
        w(f"{sep}core::mem::size_of::<{r['struct']}>()")
    w(f"    == {hex(pack['total_size'])}")
    w(");")
    w("")

    # ---- geometry-derived layout constants the driver imports ----
    def range_info(abbrev, idx):
        j = join[abbrev]
        gp = j.get("offset_parsed_detail") or j["offset_parsed"]
        return gp["ranges"][idx]

    rdt1, rdt2 = range_info("RDT", 0), range_info("RDT", 1)
    tdt = range_info("TDT", 0)
    w("/// Offset where the RDT register starts for the first 64 rx queues")
    w(f"pub const RDT_1: usize = {hex(rdt1['start_addr'])};")
    w("/// Offset where the RDT register starts for the second set of 64 rx queues")
    w(f"pub const RDT_2: usize = {hex(rdt2['start_addr'])};")
    w("/// Number of bytes between consecutive RDT registers")
    w(f"pub const RDT_DIST: usize = {hex(rdt1['stride'])};")
    w("/// Offset where the TDT register starts for the first 64 queues")
    w(f"pub const TDT: usize = {hex(tdt['start_addr'])};")
    w("/// Number of bytes between consecutive TDT registers")
    w(f"pub const TDT_DIST: usize = {hex(tdt['stride'])};")
    w("")

    # ---- field-derived + policy constants (constants_map.json) ----
    cmap_path = os.path.join(HERE, "constants_map.json")
    if os.path.exists(cmap_path):
        cmap = load_json(cmap_path)
        specs = {}
        for abbrev in join:
            p = os.path.join(run_dir, abbrev + ".json")
            if os.path.exists(p):
                specs[abbrev] = load_json(p)
        const_lines, const_report = emit_constants(cmap, specs, report)
        lines.extend(const_lines)

    with open(os.path.join(out_dir, "regs.rs"), "w") as f:
        f.write("\n".join(lines))
    with open(os.path.join(out_dir, "emit_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print(f"emitted {out_dir}/regs.rs")
    for k in ("missing_specs", "offset_mismatches", "offset_fallbacks",
              "collisions", "skipped_ranges", "scalar_from_strided"):
        if report[k]:
            print(f"  {k}: {len(report[k])}")
            for item in report[k][:10]:
                print("    ", item)
    if "constants" in report:
        cr = report["constants"]
        print(f"  constants: {len(cr['derived_agree'])} field-derived agree, "
              f"{len(cr['derived_disagree'])} disagree (bug candidates), "
              f"{len(cr['fallback'])} fallback (recall misses), "
              f"{len(cr['policy'])} policy")
        for d in cr["derived_disagree"]:
            print("     DISAGREE:", d)
        for d in cr["fallback"]:
            print("     MISS:", d)
    acc_dis = [a for a in report["access"] if a["type"] != a["ref"]]
    print(f"  access type vs reference: {len(report['access']) - len(acc_dis)}"
          f"/{len(report['access'])} agree; disagreements:")
    for a in acc_dis:
        print(f"     {a['register']}: code={a['code']} -> {a['type']} (ref {a['ref']})")


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def find_field(spec, names):
    """Fuzzy-find a subfield by datasheet name (+ alternates)."""
    if not spec:
        return None, None
    wanted = [_norm(n) for n in names if n]
    for sf in spec.get("subfields") or []:
        if _norm(sf.get("name")) in wanted:
            return sf, sf.get("name")
    # prefix/containment fallback (e.g. "ITR Interval" vs "ITR_Interval(9:3)")
    for sf in spec.get("subfields") or []:
        n = _norm(sf.get("name"))
        if any(w and (w in n or n in w) for w in wanted):
            return sf, sf.get("name")
    return None, None


def emit_constants(cmap, specs, report):
    """Emit the driver-referenced constants, deriving values from extracted
    fields where the map says they are field-derived. Falls back to the
    reference expression when the field is missing (each fallback is a logged
    field-level recall miss). Derived values that DISAGREE with the reference
    are emitted with the DERIVED value (the extraction is the product) and
    flagged as bug candidates for adjudication."""
    lines = []
    rep = {"derived_agree": [], "derived_disagree": [], "fallback": [],
           "policy": []}
    lines.append("// Driver constants. field-derived values come from the extracted")
    lines.append("// subfield bit positions; 'policy' values are driver-chosen and kept")
    lines.append("// verbatim (see constants_map.json).")
    for c in cmap["constants"]:
        name, kind = c["name"], c["kind"]
        ty = c.get("type", "u32")
        ref_expr = c["ref"]
        ref_val = eval(ref_expr.replace("<<", "<<"))  # arithmetic only, trusted file
        if kind == "policy":
            expr = c["value"]
            lines.append(f"/// {c.get('comment', 'driver policy value')}")
            lines.append(f"pub const {name}: {ty} = {expr};")
            rep["policy"].append(name)
            continue
        spec = specs.get(c["register"].upper())
        sf, matched = find_field(spec, [c.get("field")] + c.get("alt", []))
        derived = None
        note = ""
        if sf and sf.get("bit_number"):
            lo = sf["bit_number"].get("start_bit")
            hi = sf["bit_number"].get("end_bit")
            if lo is not None:
                if kind == "field_bit":
                    derived = 1 << lo
                    expr = f"1 << {lo}"
                elif kind == "field_bit_at":
                    derived = 1 << (lo + c["bit_offset"])
                    expr = f"1 << {lo + c['bit_offset']}"
                elif kind == "field_shift":
                    derived = lo
                    expr = str(lo)
                elif kind == "field_mask":
                    width = (hi - lo + 1) if hi is not None else 1
                    derived = ((1 << width) - 1) << lo
                    expr = f"{hex((1 << width) - 1)} << {lo}"
                elif kind == "field_value":
                    v = int(str(c["value"]), 0)
                    derived = v << lo
                    expr = f"{c['value']} << {lo}" if lo else c["value"]
        if derived is None:
            expr = ref_expr
            rep["fallback"].append({"name": name, "register": c["register"],
                                    "field": c.get("field"),
                                    "reason": "field not extracted" if spec else "register spec missing"})
            note = " // FALLBACK: field not extracted; reference value"
        elif derived == ref_val:
            rep["derived_agree"].append(name)
        else:
            rep["derived_disagree"].append(
                {"name": name, "derived": expr, "reference": ref_expr,
                 "matched_field": matched})
            note = f" // BUG CANDIDATE: reference has {ref_expr}"
        src_field = f"{c['register']}.{matched or c.get('field')}"
        lines.append(f"/// {kind} of {src_field}")
        lines.append(f"pub const {name}: {ty} = {expr};{note}")
    report["constants"] = rep
    return lines, rep


if __name__ == "__main__":
    main()
