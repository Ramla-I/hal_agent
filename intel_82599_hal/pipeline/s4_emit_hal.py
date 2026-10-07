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

KNOWN LIMITATIONS of the --gated encoding (what a witness token does and does
NOT prove). These are reported, not silently assumed:
  #1 Register-INSTANCE provenance. An establish-minted witness mints from any
     `&mut Volatile<u32>` the caller claims is the prerequisite register — the
     type does not prove it is the RIGHT register instance/device. The variant
     emitter s4b_emit_hal_minted.py closes the register-TYPE hole (it mints the
     token through the prerequisite register's own newtype, so only that register
     can produce it); instance/device binding (branded lifetimes) and TOCTOU
     (a retained borrow) remain future work.
  #3 A check-minted witness is only instantiable when its check_ constructor is
     emitted (on the gated register that IS the prerequisite). Otherwise the
     token has no constructor and write_full is unreachable: the register
     degrades to read + write_preserving. Flagged in uninstantiable_witnesses.
  #4 Coupled relation setters are two separate volatile writes, not one atomic
     transaction: the two registers are momentarily unequal between the writes.
     The invariant holds at rest, not continuously.
  #5 A value_relation whose meaning lives in the VALUE (alignment, inequality,
     conditional) is NOT ENCODED — no runtime check is emitted. It is listed in
     not_encoded, never counted as enforced.
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


def build_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", help="run tag under register_info/, e.g. r003")
    ap.add_argument("--offset-source", choices=["llm", "summary"], default="llm")
    ap.add_argument("--no-overrides", action="store_true",
                    help="pure datasheet access typing (no adjudicated overrides)")
    ap.add_argument("--plain", action="store_true",
                    help="portable variant: no zerocopy/FromBytes derives "
                    "(for consumers outside Theseus, e.g. the ixy.rs retrofit)")
    ap.add_argument("--gated", action="store_true",
                    help="constraint-encoded configuration: witness-gate the "
                    "registers whose extracted state_gates match the "
                    "whole-register action-witness rule; output goes to "
                    "hal_out/<run>-gated/")
    ap.add_argument("--extra-constraints", metavar="PATH",
                    help="JSON file of additional grammar-v2 constraints "
                    "({constraints:[{register, enforceability, constraint}]}) to "
                    "fold into the gated set alongside the run's collection — e.g. "
                    "config/recovered_constraints.json (the recovered constraints), "
                    "so the gated HAL encodes the combined set. Needs --gated.")
    return ap


def main():
    run(build_parser().parse_args())


def run(args):
    # The alternate entry point s4b_emit_hal_minted.py sets args.minted=True to
    # mint each witness THROUGH the prerequisite register's own newtype, so only
    # that register can produce the token (register-TYPE provenance; limitation
    # #1). Default emitter leaves it False and is byte-for-byte unchanged.
    minted = getattr(args, "minted", False)
    run_dir = os.path.join(HERE, "register_info", args.run)
    out_dir = os.path.join(HERE, "hal_out", args.run + ("-gated" if args.gated else "")
                           + ("-minted" if minted else "")
                           + ("-plain" if args.plain else ""))
    os.makedirs(out_dir, exist_ok=True)

    join = {r["abbrev_base"].upper(): r
            for r in load_json(os.path.join(HERE, "targets", "registers_join.json"))["registers"]}
    pack = load_json(os.path.join(HERE, "config", "packaging.json"))
    name_map = {k.upper(): v for k, v in
                load_json(os.path.join(HERE, "config", "name_map.json"), default={}).items()
                if not k.startswith("_")}
    overrides = load_json(os.path.join(HERE, "config", "access_overrides.json"),
                          default={"overrides": {}})["overrides"]

    gates = {}
    couplings = []
    gate_report = {"encoded": [], "not_encoded": []}
    if args.gated:
        cpath = os.path.join(HERE, "constraints", f"{args.run}_constraints.json")
        cons = load_json(cpath)
        # fold in any extra (e.g. recall-recovered) constraints so the gated HAL
        # encodes the COMBINED set, not just one run's collection. The file is a
        # committed, already-validated grammar-v2 snapshot (same shape as the
        # collection's accepted[]), so no re-validation is needed here.
        extra_added = 0
        if args.extra_constraints:
            extra = load_json(os.path.join(HERE, args.extra_constraints)
                              if not os.path.isabs(args.extra_constraints)
                              else args.extra_constraints)
            for e in extra.get("constraints", []):
                cons["accepted"].append(e)
                extra_added += 1
        gate_report["extra_folded_in"] = extra_added

        def spec_of(reg):
            p = os.path.join(run_dir, reg.upper() + ".json")
            return load_json(p) if os.path.exists(p) else None

        def fields_mask(reg, names):
            """Union bit mask of the named fields, from extraction. None if any
            name fails to resolve (constraint then not encodable faithfully)."""
            sp = spec_of(reg)
            mask = 0
            resolved = []
            for n in names:
                sf, matched = find_field(sp, [n])
                if not sf or not sf.get("bit_number"):
                    return None, None
                lo, hi = sf["bit_number"]["start_bit"], sf["bit_number"]["end_bit"]
                mask |= ((1 << (hi - lo + 1)) - 1) << lo
                resolved.append(matched)
            return mask, resolved

        def gate_for(reg):
            return gates.setdefault(reg.upper(), {
                "gtype": f"Gated{reg.title().replace('_','')}",
                "hold_mask": 0,      # bits write_preserving keeps at current value
                "clamp_mask": 0,     # bits write_preserving forces to 0 (never-set)
                "whole": False,      # whole-register witness gate (no free write)
                "witness": None,     # witnessed write_full / write
                "quotes": [],
            })

        def wname(reg, field, suffix):
            return (f"{reg.title().replace('_','')}"
                    f"{re.sub(r'[^A-Za-z0-9]', '', field.title())}{suffix}")

        # --- pass 1: state_gates (field-level is the DEFAULT; target_fields=[]
        #     is the whole-register special case) ---
        for a in cons["accepted"]:
            c = a["constraint"]
            reg = c.get("target_register", a["register"]).upper()
            entry = {"register": reg, "kind": c["kind"],
                     "text": c["datasheet_text"][:90]}
            if c["kind"] == "state_gate":
                if not (c.get("target_operation") in ("write", "any")
                        and len(c.get("preconditions", [])) == 1
                        and not c.get("postconditions")):
                    gate_report["not_encoded"].append(dict(entry,
                        reason="state_gate shape outside the one-precondition write-gate rule"))
                    continue
                p = c["preconditions"][0]
                tf = c.get("target_fields") or []
                # self-referential 'field must stay cleared when written' ->
                # the only always-satisfying encoding is never-set (clamp)
                if (tf and p["register"].upper() == reg
                        and p.get("field") in tf and p["state"] == "cleared"):
                    mask, resolved = fields_mask(reg, tf)
                    if mask is None:
                        gate_report["not_encoded"].append(dict(entry,
                            reason="target field not resolvable in extraction"))
                        continue
                    g = gate_for(reg)
                    g["clamp_mask"] |= mask
                    g["quotes"].append(("clamp", c["datasheet_text"],
                                        c.get("consequence", "")))
                    gate_report["encoded"].append(dict(entry,
                        encoding=f"never-set clamp of {resolved} (mask {hex(mask)})"))
                    continue
                if not (p.get("field") and not p.get("whole_register")
                        and p["state"] in ("cleared", "set")):
                    gate_report["not_encoded"].append(dict(entry,
                        reason="precondition not a single named-field cleared/set state"))
                    continue
                pmask, presolved = fields_mask(p["register"], [p["field"]])
                if pmask is None:
                    gate_report["not_encoded"].append(dict(entry,
                        reason="precondition field not resolvable in extraction"))
                    continue
                g = gate_for(reg)
                suffix = "Cleared" if p["state"] == "cleared" else "Set"
                new_wit = {
                    "name": wname(p["register"], p["field"], suffix),
                    "pre_register": p["register"].upper(),
                    "pre_field": presolved[0],
                    "pre_mask": pmask,
                    "mode": p["state"],
                    # hardware-established state -> fallible check() mints the
                    # witness; software-established -> establish() performs the
                    # action (clear/set) and mints it
                    "minted_by": "check" if p["established_by"] == "hardware"
                                 else "establish",
                    "quote": c["datasheet_text"],
                    "consequence": c.get("consequence", ""),
                }
                # resolve the gated target (field-level default / whole-register)
                if tf:
                    mask, resolved = fields_mask(reg, tf)
                    if mask is None:
                        gate_report["not_encoded"].append(dict(entry,
                            reason="target fields not resolvable in extraction"))
                        continue
                    what = f"fields {resolved} (mask {hex(mask)})"
                else:
                    mask, resolved = None, None
                    what = "whole register"
                # Single witness slot per register: the FIRST witnessed gate wins.
                # We have one token type per gated struct, so a second, DIFFERENT
                # witness on the same register cannot be faithfully encoded — keep
                # the first and FAIL LOUD about the drop. The dropped gate's target
                # fields are conservatively LOCKED (hold_mask, NOT wit_mask), so they
                # are never left writable under the wrong witness (over-restrictive,
                # not unsound). (#2)
                if g["witness"] is not None and g["witness"]["name"] != new_wit["name"]:
                    gate_report.setdefault("witness_conflicts", []).append(dict(entry,
                        kept=g["witness"]["name"], dropped=new_wit["name"],
                        reason="register already has a witnessed gate; the second "
                               "witness was dropped and its target fields locked "
                               "(single-witness-slot limitation)"))
                    if mask is not None:
                        g["hold_mask"] |= mask
                    g["quotes"].append(("witness-dropped", c["datasheet_text"],
                                        c.get("consequence", "")))
                    continue
                g["witness"] = new_wit
                if mask is not None:
                    g["hold_mask"] |= mask
                    g["wit_mask"] = g.get("wit_mask", 0) | mask
                else:
                    g["whole"] = True
                g["quotes"].append(("witness", c["datasheet_text"],
                                    c.get("consequence", "")))
                gate_report["encoded"].append(dict(entry,
                    encoding=f"{new_wit['minted_by']}-minted witness "
                             f"{new_wit['name']} gating {what}"))
            elif c["kind"] == "value_relation":
                flds = c.get("fields") or []
                text = c["datasheet_text"]
                emitted_regs = {r.upper() for r in join}
                if (len(flds) == 2
                        and re.search(r"set the same|same as", text, re.I)
                        and all(f["register"].upper() in emitted_regs for f in flds)
                        and flds[0]["register"].upper() != flds[1]["register"].upper()):
                    pair = []
                    ok = True
                    for f in flds:
                        m, resolved = fields_mask(f["register"], [f["field"]])
                        if m is None:
                            ok = False
                            break
                        pair.append({"register": f["register"].upper(),
                                     "field": resolved[0], "mask": m})
                    if not ok:
                        gate_report["not_encoded"].append(dict(entry,
                            reason="relation field not resolvable in extraction"))
                        continue
                    key = frozenset((x["register"], x["field"]) for x in pair)
                    if any(cp["key"] == key for cp in couplings):
                        # the relation is stated on both registers; one coupling
                        for cp in couplings:
                            if cp["key"] == key:
                                cp["quotes"].append(text)
                        gate_report["encoded"].append(dict(entry,
                            encoding="same coupled setter (relation stated on both sides)"))
                        continue
                    pair.sort(key=lambda x: x["register"])
                    fn = "set_" + "_".join(
                        re.sub(r"[^a-z0-9]", "", x["field"].lower()) for x in pair)
                    couplings.append({"key": key, "fn": fn, "pair": pair,
                                      "quotes": [text]})
                    for x in pair:
                        g = gate_for(x["register"])
                        g["hold_mask"] |= x["mask"]
                        g["quotes"].append(("coupled", text, c.get("consequence", "")))
                    gate_report["encoded"].append(dict(entry,
                        encoding=f"coupled setter {fn}() — independent writes "
                                 f"preserve the related bits"))
                elif re.search(r"must not change", text, re.I) and flds:
                    own = [f for f in flds if f["register"].upper() in emitted_regs
                           and f["register"].upper() == reg]
                    if own:
                        m, resolved = fields_mask(reg, [own[0]["field"]])
                        if m is not None:
                            g = gate_for(reg)
                            g["hold_mask"] |= m
                            g["quotes"].append(("hold", text, c.get("consequence", "")))
                            gate_report["encoded"].append(dict(entry,
                                encoding=f"hold mask on {resolved} (field kept at "
                                         f"current value; no API can change it)"))
                            continue
                    gate_report["not_encoded"].append(dict(entry,
                        reason="'must not change' field not on an emitted register"))
                else:
                    gate_report["not_encoded"].append(dict(entry,
                        reason="relation semantics live in the value (alignment/"
                               "inequality/conditional) — not visible at u32 "
                               "granularity; NOT ENCODED (no runtime check emitted)"))
            else:
                gate_report["not_encoded"].append(dict(entry,
                    reason=f"kind {c['kind']} is {a['enforceability']} by the "
                           f"computed taxonomy"))

    # --- minted mode: which registers are witness prerequisites? Each gets a
    #     newtype that is the SOLE minter of its witness token (register-TYPE
    #     provenance). A prerequisite that is itself a gated register folds its
    #     minter into that Gated* impl; the rest get a standalone *Minter newtype
    #     (plain read/write PLUS the minting method) placed at the register's slot
    #     instead of a bare Volatile<u32>. ---
    prereqs = {}            # pre_register abbrev -> its witness (shared by name)
    if minted:
        for ab, g in gates.items():
            wit = g.get("witness")
            if wit:
                prereqs.setdefault(wit["pre_register"], wit)
    standalone_prereqs = {pr: wit for pr, wit in prereqs.items() if pr not in gates}

    def minter_type(abbrev):
        return f"{abbrev.title().replace('_', '')}Minter"

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
        if abbrev in gates:
            pass  # gate supersedes overrides; recorded in report["gating"]
        elif abbrev in overrides and not args.no_overrides:
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
    if not args.plain:
        w("use zerocopy::FromBytes;")
    w("")

    def field_name(abbrev):
        return name_map.get(abbrev, abbrev.lower())

    def emit_minter_methods(wit):
        """Emit the witness-minting method(s) for a prerequisite register, as
        methods on a newtype wrapping Volatile<u32> in field .0. Register-TYPE
        provenance fix (#1): the token can ONLY be produced here, so a write to
        the wrong register cannot supply it. (minted mode)"""
        nm = wit["name"]
        pr, pf = wit["pre_register"], wit["pre_field"]
        mconst = f"GATE_{pr}_{re.sub(r'[^A-Za-z0-9]', '_', pf).upper()}"
        fn = re.sub(r'[^A-Za-z0-9]', '_', pf).lower()
        if wit["minted_by"] == "establish":
            if wit["mode"] == "cleared":
                w(f"    /// Clear {pr}.{pf} and mint the witness that it is cleared.")
                w(f"    pub fn clear_{fn}(&mut self) -> {nm} {{")
                w(f"        let v = self.0.read();")
                w(f"        self.0.write(v & !{mconst});")
                w(f"        {nm}(())")
                w("    }")
                w(f"    /// Re-set {pr}.{pf}, consuming the witness (leave the gated state).")
                w(f"    pub fn release_{fn}(&mut self, _w: {nm}) {{")
                w(f"        let v = self.0.read();")
                w(f"        self.0.write(v | {mconst});")
                w("    }")
            else:
                w(f"    /// Set {pr}.{pf} and mint the witness that it is set.")
                w(f"    /// No release: the condition must persist while gated fields are used.")
                w(f"    pub fn set_{fn}(&mut self) -> {nm} {{")
                w(f"        let v = self.0.read();")
                w(f"        self.0.write(v | {mconst});")
                w(f"        {nm}(())")
                w("    }")
        else:  # check (hardware-established state)
            cmp_expr = (f"(v & {mconst}) == {mconst}" if wit["mode"] == "set"
                        else f"(v & {mconst}) == 0")
            w(f"    /// Fallible check minting the state witness: {pr}.{pf} must read {wit['mode']}.")
            w(f"    pub fn check_{fn}(&self) -> Option<{nm}> {{")
            w(f"        let v = self.0.read();")
            w(f"        if {cmp_expr} {{ Some({nm}(())) }} else {{ None }}")
            w("    }")

    def emit_struct(struct_name, doc, members, start, end, elem_mode=False):
        """members: entries sorted by addr. elem_mode: offsets relative to start,
        struct covers [start, end) of ONE element (queue struct)."""
        pad_i = [0]
        w(f"/// {doc}")
        args.plain or w("#[derive(FromBytes)]")
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
            doc_name = m.get("doc_name") or ""
            if doc_name:
                w(f"    /// {doc_name}")
            gate = gates.get(m["abbrev"])
            sp_wit = standalone_prereqs.get(m["abbrev"]) if minted else None
            if m["count"] and m["stride"] == 4 and not elem_mode:
                w(f"    pub {name}: [{m['rtype']}<u32>; {m['count']}], // {hex(addr)} - {hex(addr + 4 * m['count'] - 1)}")
                cursor = addr + 4 * m["count"]
            elif gate:
                wnote = (f"write gated on {gate['witness']['pre_register']}."
                         f"{gate['witness']['pre_field']}" if gate.get("witness")
                         else "protected bits — see gating section")
                w(f"    pub {name}: {gate['gtype']}, // {hex(addr)} — {wnote}")
                cursor = addr + 4
            elif sp_wit:
                w(f"    pub {name}: {minter_type(m['abbrev'])}, // {hex(addr)} — "
                  f"sole minter of {sp_wit['name']}")
                cursor = addr + 4
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
            args.plain or w("#[derive(FromBytes)]")
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

    # ---- gating section (constraint-encoded configuration) ----
    if gates or couplings:
        w("// ============================================================================")
        w("// Access-constraint gating — GENERATED from extracted access_constraints_v2.")
        w("// Field-level by default: a gated register exposes write_preserving(), which")
        w("// structurally cannot change protected bits (witnessed fields, coupled")
        w("// relation bits, held fields; never-set bits are forced to 0), and — where a")
        w("// witness exists — write_full(value, &Witness). Whole-register gates expose")
        w("// only write(value, &Witness). The raw write() does not exist on gated")
        w("// registers: every previously-legal raw write site fails to compile and the")
        w("// author must choose the preserving, witnessed, or coupled path.")
        w("// ============================================================================")
        w("")
        # Which witnesses actually get a constructor emitted? An establish-minted
        # witness always does (establish() takes the prerequisite register by ref).
        # A check-minted witness gets its check_ constructor ONLY on the gated
        # register whose abbrev IS the prerequisite register (see the check_ emit
        # below). So a check-minted witness whose prerequisite register is not
        # itself a gated register carrying it has NO constructor anywhere: the
        # token can never be minted and write_full is unreachable. Flag those
        # (FAIL LOUD) — the register then degrades to read + write_preserving. (#3)
        # In minted mode every witness is minted on its prerequisite newtype, so
        # it is always instantiable (and #3 cannot occur).
        has_ctor = set()
        for ab, g in gates.items():
            wit = g.get("witness")
            if not wit:
                continue
            if minted or wit["minted_by"] == "establish" or wit["pre_register"] == ab:
                has_ctor.add(wit["name"])
        # witness types, deduped by name
        seen_w = set()
        for abbrev, g in gates.items():
            wit = g.get("witness")
            if not wit or wit["name"] in seen_w:
                continue
            seen_w.add(wit["name"])
            nm = wit["name"]
            pm = wit["pre_mask"]
            pr, pf = wit["pre_register"], wit["pre_field"]
            uninstantiable = nm not in has_ctor
            if uninstantiable:
                gate_report.setdefault("uninstantiable_witnesses", []).append(
                    {"register": abbrev, "witness": nm, "pre_register": pr,
                     "pre_field": pf, "minted_by": wit["minted_by"],
                     "reason": "check-minted witness whose prerequisite register is "
                               "not itself gated; no constructor is emitted, so the "
                               "token cannot be minted and write_full is unreachable "
                               "(register degrades to read + write_preserving only)"})
            w(f"/// Datasheet: \"{wit['quote']}\"")
            w(f"/// Violation consequence: {wit['consequence']}")
            state = "cleared" if wit["mode"] == "cleared" else "set"
            w(f"/// Witness token attesting {pr}.{pf} is {state}.")
            if uninstantiable:
                w(f"// NOTE: no constructor is emitted for {nm} (its prerequisite")
                w(f"// register {pr} is not gated), so this token can never be minted")
                w(f"// and {g['gtype']}::write_full is unreachable — see emit_report.json.")
            w(f"pub struct {nm}(());")
            w(f"/// Bit mask of {pr}.{pf} (from extraction).")
            w(f"pub const GATE_{pr}_{re.sub(r'[^A-Za-z0-9]', '_', pf).upper()}: u32 = {hex(pm)};")
            mconst = f"GATE_{pr}_{re.sub(r'[^A-Za-z0-9]', '_', pf).upper()}"
            # Default emitter: establish-minted witnesses expose a free
            # establish()/release() taking the prerequisite register by &mut ref
            # (the caller asserts it is the right register — limitation #1). In
            # minted mode the minter moves onto the prerequisite newtype below, so
            # this free function is omitted.
            if wit["minted_by"] == "establish" and not minted:
                w(f"impl {nm} {{")
                if wit["mode"] == "cleared":
                    w(f"    /// Establish the precondition (action witness): clear {pr}.{pf}.")
                    w(f"    pub fn establish(reg: &mut Volatile<u32>) -> {nm} {{")
                    w(f"        let v = reg.read();")
                    w(f"        reg.write(v & !{mconst});")
                    w(f"        {nm}(())")
                    w("    }")
                    w(f"    /// Leave the gated state: re-set {pr}.{pf}, consuming the witness.")
                    w(f"    pub fn release(self, reg: &mut Volatile<u32>) {{")
                    w(f"        let v = reg.read();")
                    w(f"        reg.write(v | {mconst});")
                    w("    }")
                else:
                    w(f"    /// Establish the precondition (action witness): set {pr}.{pf}.")
                    w(f"    /// No release: the condition must persist while gated fields are in use.")
                    w(f"    pub fn establish(reg: &mut Volatile<u32>) -> {nm} {{")
                    w(f"        let v = reg.read();")
                    w(f"        reg.write(v | {mconst});")
                    w(f"        {nm}(())")
                    w("    }")
                w("}")
            w("")
        # minted mode: standalone minter newtypes for prerequisite registers that
        # are not themselves gated (a gated prerequisite folds its minter into its
        # Gated* impl below). Each is a plain Volatile<u32> (read + write still
        # available for unrelated bits) PLUS the sole minting method for its token.
        if minted:
            for pr, wit in standalone_prereqs.items():
                nt = minter_type(pr)
                w(f"/// {pr}: witness-minter newtype — the ONLY type that can produce")
                w(f"/// {wit['name']} (register-TYPE provenance; #1). Plain read/write")
                w(f"/// remain available for unrelated bits.")
                args.plain or w("#[derive(FromBytes)]")
                w("#[repr(transparent)]")
                w(f"pub struct {nt}(Volatile<u32>);")
                w(f"impl {nt} {{")
                w("    pub fn read(&self) -> u32 { self.0.read() }")
                w("    pub fn write(&mut self, value: u32) { self.0.write(value) }")
                emit_minter_methods(wit)
                w("}")
                w("")
        # gated register types
        for abbrev, g in gates.items():
            gt = g["gtype"]
            wit = g.get("witness")
            hold, clamp = g["hold_mask"], g["clamp_mask"]
            wmask = g.get("wit_mask", 0)
            w(f"/// {abbrev}: constraint-gated register (see the quotes on its methods).")
            args.plain or w("#[derive(FromBytes)]")
            w("#[repr(transparent)]")
            w(f"pub struct {gt}(Volatile<u32>);")
            w(f"impl {gt} {{")
            w("    pub fn read(&self) -> u32 { self.0.read() }")
            if g["whole"]:
                w(f"    /// Datasheet: \"{wit['quote']}\"")
                w(f"    /// Whole-register gated write — requires the {wit['name']} witness token.")
                w(f"    pub fn write(&mut self, value: u32, _witness: &{wit['name']}) {{ self.0.write(value) }}")
            else:
                pres = hold | clamp
                w(f"    /// Free write that CANNOT change the protected bits:")
                for tag, quote, _cons in g["quotes"]:
                    w(f"    /// - ({tag}) \"{quote[:140]}\"")
                w(f"    pub fn write_preserving(&mut self, value: u32) {{")
                w(f"        let cur = self.0.read();")
                w(f"        self.0.write((value & !{hex(pres)}) | (cur & {hex(hold)}));")
                w("    }")
                if wit:
                    keep = hold & ~wmask
                    w(f"    /// Witnessed write: may change the gated fields (mask {hex(wmask)}),")
                    w(f"    /// still preserving other protected bits and never-set bits.")
                    w(f"    pub fn write_full(&mut self, value: u32, _witness: &{wit['name']}) {{")
                    w(f"        let cur = self.0.read();")
                    w(f"        self.0.write((value & !{hex(clamp | keep)}) | (cur & {hex(keep)}));")
                    w("    }")
                    # default emitter: a check-minted witness whose prerequisite
                    # IS this register mints via an inline check_ method.
                    if (not minted and wit["minted_by"] == "check"
                            and wit["pre_register"] == abbrev):
                        nm = wit["name"]
                        mconst = f"GATE_{wit['pre_register']}_{re.sub(r'[^A-Za-z0-9]', '_', wit['pre_field']).upper()}"
                        cmp_expr = f"(v & {mconst}) == {mconst}" if wit["mode"] == "set" else f"(v & {mconst}) == 0"
                        w(f"    /// Fallible check minting the state witness: {wit['pre_register']}.{wit['pre_field']} must read {wit['mode']}.")
                        w(f"    pub fn check_{re.sub(r'[^A-Za-z0-9]', '_', wit['pre_field']).lower()}(&self) -> Option<{nm}> {{")
                        w(f"        let v = self.0.read();")
                        w(f"        if {cmp_expr} {{ Some({nm}(())) }} else {{ None }}")
                        w("    }")
            # minted mode: a gated register that is itself a witness prerequisite
            # folds its minter into this impl (covers both whole- and field-gated).
            if minted and abbrev in prereqs:
                emit_minter_methods(prereqs[abbrev])
            w("}")
            w("")
        # coupled relation setters
        for cp in couplings:
            a, b = cp["pair"]
            ga, gb = gates[a["register"]]["gtype"], gates[b["register"]]["gtype"]
            for q in cp["quotes"]:
                w(f"/// Datasheet: \"{q}\"")
            w(f"/// The related bits can ONLY be changed together, keeping them equal —")
            w(f"/// independent writes preserve them (write_preserving).")
            w(f"pub fn {cp['fn']}(a: &mut {ga}, b: &mut {gb}, enable: bool) {{")
            for var, x in (("a", a), ("b", b)):
                w(f"    let v = {var}.0.read();")
                w(f"    {var}.0.write(if enable {{ v | {hex(x['mask'])} }} else {{ v & !{hex(x['mask'])} }}); // {x['register']}.{x['field']}")
            w("}")
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
    cmap_path = os.path.join(HERE, "config", "constants_map.json")
    if os.path.exists(cmap_path):
        cmap = load_json(cmap_path)
        specs = {}
        for abbrev in join:
            p = os.path.join(run_dir, abbrev + ".json")
            if os.path.exists(p):
                specs[abbrev] = load_json(p)
        const_lines, const_report = emit_constants(cmap, specs, report)
        lines.extend(const_lines)

    if args.gated:
        report["gating"] = gate_report
        report["couplings"] = [{k: v for k, v in cp.items() if k != "key"}
                               for cp in couplings]
        if minted:
            report["minted"] = True
            report["minters"] = {
                pr: {"witness": wit["name"], "minted_by": wit["minted_by"],
                     "newtype": minter_type(pr) if pr not in gates
                                else gates[pr]["gtype"],
                     "folded_into_gated": pr in gates}
                for pr, wit in prereqs.items()}
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
    if args.gated:
        if minted:
            print(f"  MINTED mode: {len(prereqs)} prerequisite register(s) mint their "
                  f"own witness ({len(standalone_prereqs)} standalone *Minter newtype(s), "
                  f"{len(prereqs) - len(standalone_prereqs)} folded into a Gated* impl)")
            for pr, wit in prereqs.items():
                where = gates[pr]["gtype"] if pr in gates else minter_type(pr)
                print(f"    MINTS {wit['name']:22s} via {where} ({pr})")
        if gate_report.get("extra_folded_in"):
            print(f"  folded in {gate_report['extra_folded_in']} extra constraint(s) "
                  f"from {args.extra_constraints}")
        print(f"  gating: {len(gate_report['encoded'])} constraints encoded on "
              f"{len(gates)} registers (+{len(couplings)} coupled setters); "
              f"{len(gate_report['not_encoded'])} not encoded")
        for e in gate_report["encoded"]:
            print(f"    ENCODED {e['register']:9s} {e['kind']:14s} -> {e['encoding']}")
        for e in gate_report["not_encoded"]:
            print(f"    -       {e['register']:9s} {e['kind']:14s} {e['reason']}")
        if gate_report.get("witness_conflicts"):
            print(f"  witness conflicts (second witness dropped, fields locked): "
                  f"{len(gate_report['witness_conflicts'])}")
            for e in gate_report["witness_conflicts"]:
                print(f"    CONFLICT {e['register']:9s} kept {e['kept']}, dropped {e['dropped']}")
        if gate_report.get("uninstantiable_witnesses"):
            print(f"  uninstantiable witnesses (no constructor; write_full unreachable): "
                  f"{len(gate_report['uninstantiable_witnesses'])}")
            for e in gate_report["uninstantiable_witnesses"]:
                print(f"    UNINSTANTIABLE {e['witness']} on {e['register']} "
                      f"(prereq {e['pre_register']} not gated)")
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
