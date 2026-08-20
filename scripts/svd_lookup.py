#!/usr/bin/env python3
"""Look up SVD entries by peripheral / register / key.

Shows the SVD *faithfully*: literal register names (so HASH keeps both `HR0` @0xC
and `HASH_HR0` @0x310 instead of colliding), peripheral `derivedFrom` resolved
(so ADC3 shows the registers it inherits from ADC1), `<dim>` arrays expanded to
concrete names, and size/resetValue/access inheritance applied. It also prints
each register's absolute address (baseAddress + offset).

Matching is flexible: a register query matches the literal name OR its
peripheral-prefix-stripped form, so `-r hr0` finds both `hr0` and `hash_hr0`
(the latter is how the bug review would name it).

  # whole register: offsets, reset, size, absolute address, fields
  python scripts/svd_lookup.py devices/stm/rm0090/svd/stm32f417.svd -p hash -r hr0

  # one attribute only
  python scripts/svd_lookup.py <svd> -p bkp -r dr1 -k address_offset
  python scripts/svd_lookup.py <svd> -p hash -r hr0 -k access          # field-level key

  # broader queries
  python scripts/svd_lookup.py <svd> -p bkp        # every register in a peripheral
  python scripts/svd_lookup.py <svd> -r jdr1       # a register across all peripherals
  python scripts/svd_lookup.py <svd>               # list peripherals

Keys: address_offset, reset_value, size (register-level);
      bit_offset, bit_width, access (field-level, one line per field).
"""
from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_tools.svd_parsing import (  # noqa: E402
    resolve_peripheral_registers, expand_dim_indices, _strip_peripheral_prefix,
)

_REGISTER_KEYS = ("address_offset", "reset_value", "size")
_FIELD_KEYS = ("bit_offset", "bit_width", "access")
_HEX_KEYS = ("address_offset", "reset_value")


def _int0(text):
    """Parse an SVD integer: 0x/decimal via base-0, else bare hex (e.g. resetValue
    ``00000010``, ``30D0``). None if unparseable."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        return int(text, 0)
    except ValueError:
        try:
            return int(text, 16)
        except ValueError:
            return None


# ---------------------------------------------------------------- SVD parsing --

def parse_svd(svd_path: str) -> dict:
    """Faithful ``{peripheral: {register: {...}}}`` (lowercase keys, literal names).

    Mirrors the pipeline parser's inheritance/dim handling but keeps literal
    register names (no prefix stripping, no name collisions).
    """
    root = ET.parse(svd_path).getroot()
    ns = root.tag[: root.tag.index("}") + 1] if "}" in root.tag else ""

    def txt(elem, tag):
        return (elem.findtext(f"{ns}{tag}") or "").strip() if elem is not None else ""

    dev_size = _int0(txt(root, "size"))
    dev_reset = _int0(txt(root, "resetValue"))
    dev_access = txt(root, "access").lower()

    per_elem = {(p.findtext(f"{ns}name") or "").strip().lower(): p
                for p in root.iter(f"{ns}peripheral")}
    # every register element, for register-level derivedFrom
    reg_index: dict[tuple[str, str], ET.Element] = {}
    for pn, p in per_elem.items():
        regs = p.find(f"{ns}registers")
        if regs is not None:
            for r in regs.findall(f"{ns}register"):
                reg_index.setdefault((pn, (r.findtext(f"{ns}name") or "").strip().lower()), r)

    def fields_of(reg):
        fe = reg.find(f"{ns}fields")
        if fe is None:
            return None
        out = []
        for fl in fe.findall(f"{ns}field"):
            bo, bw = _int0(txt(fl, "bitOffset")), _int0(txt(fl, "bitWidth"))
            if bo is None and txt(fl, "bitRange"):  # "[hi:lo]" form
                hi, lo = (int(x, 0) for x in txt(fl, "bitRange").strip("[]").split(":"))
                bo, bw = lo, hi - lo + 1
            out.append({
                "name": txt(fl, "name").lower(),
                "bit_offset": bo, "bit_width": bw,
                "access": txt(fl, "access").lower(),
            })
        return out

    def resolve(pn, reg, seen=()):
        base = None
        df = reg.get("derivedFrom")
        if df:
            bp, br = df.split(".", 1) if "." in df else (pn, df)
            k = (bp.strip().lower(), br.strip().lower())
            if k in reg_index and k not in seen:
                base = resolve(k[0], reg_index[k], seen + (k,))
        offset = _int0(txt(reg, "addressOffset"))
        if offset is None and base:
            offset = base["address_offset"]
        size = _int0(txt(reg, "size"))
        reset = _int0(txt(reg, "resetValue"))
        access = txt(reg, "access").lower()
        flds = fields_of(reg)
        pdef = per_elem.get(pn)
        per_size, per_reset = _int0(txt(pdef, "size")), _int0(txt(pdef, "resetValue"))
        per_access = txt(pdef, "access").lower()
        if size is None:
            size = (base or {}).get("size") or per_size or dev_size
        if reset is None:
            reset = (base or {}).get("reset_value") if base and base.get("reset_value") is not None \
                else (per_reset if per_reset is not None else dev_reset)
        if not access:
            access = (base or {}).get("access") or per_access or dev_access
        if flds is None:
            flds = (base or {}).get("fields") or []
        # a field without its own access inherits the register's (CMSIS cascade)
        for fld in flds:
            if not fld.get("access"):
                fld["access"] = access
        return {"address_offset": offset, "reset_value": reset, "size": size,
                "access": access, "fields": flds}

    out: dict[str, dict] = {}
    for pname, regs_elem in resolve_peripheral_registers(root, ns).items():
        pn = pname.strip().lower()
        base_addr = _int0(txt(per_elem.get(pn), "baseAddress"))
        registers: dict[str, dict] = {}
        if regs_elem is not None:
            for reg in regs_elem.findall(f"{ns}register"):
                rd = resolve(pn, reg)
                rd["_peripheral_base"] = base_addr
                raw = (reg.findtext(f"{ns}name") or "").strip()
                idxs = expand_dim_indices(reg, ns) if "%s" in raw else []
                if idxs:
                    inc = _int0(txt(reg, "dimIncrement")) or 0
                    boff = rd["address_offset"] if isinstance(rd["address_offset"], int) else 0
                    tmpl = raw.replace("[%s]", "%s")
                    for pos, ix in enumerate(idxs):
                        inst = dict(rd, address_offset=boff + pos * inc)
                        registers[tmpl.replace("%s", ix).lower()] = inst
                else:
                    registers[raw.lower()] = rd
        out[pn] = registers
    return out


# ------------------------------------------------------------------- querying --

def _fmt(key: str, val) -> str:
    if val is None or val == "":
        return "?"
    if key in _HEX_KEYS and isinstance(val, int):
        return f"0x{val:X}"
    return str(val)


def _reg_matches(regname: str, query: str, peripheral: str) -> bool:
    return query in (regname, _strip_peripheral_prefix(regname, peripheral))


def _reg_header(per: str, reg: str, r: dict) -> str:
    off, base = r.get("address_offset"), r.get("_peripheral_base")
    absolute = (f"  abs={_fmt('address_offset', base + off)}"
                if isinstance(base, int) and isinstance(off, int) else "")
    return (f"{per}.{reg}  offset={_fmt('address_offset', off)}  "
            f"reset={_fmt('reset_value', r.get('reset_value'))}  "
            f"size={_fmt('size', r.get('size'))}  access={r.get('access') or '?'}{absolute}")


def _field_line(fld: dict) -> str:
    lo, w = fld.get("bit_offset"), fld.get("bit_width")
    bits = f"[{lo + w - 1}:{lo}]" if isinstance(lo, int) and isinstance(w, int) else "?"
    return (f"    {fld.get('name',''):<18} bits={bits:<9} "
            f"width={_fmt('bit_width', w):<4} access={fld.get('access') or '?'}")


def lookup(peripherals: dict, peripheral=None, register=None, key=None, field=None) -> list[str]:
    """Filter the parsed SVD and render matching lines (pure — easy to test)."""
    p, r, f = (x.lower() if x else None for x in (peripheral, register, field))
    out: list[str] = []

    if not p and not r:
        return [f"{name}  ({len(peripherals[name])} registers)" for name in sorted(peripherals)]

    field_level = key in _FIELD_KEYS
    for per in sorted(peripherals):
        if p and per != p:
            continue
        for reg in sorted(peripherals[per]):
            if r and not _reg_matches(reg, r, per):
                continue
            rd = peripherals[per][reg]
            if key in _REGISTER_KEYS:
                out.append(f"{per}.{reg}  {key}={_fmt(key, rd.get(key))}")
            elif field_level:
                for fld in rd.get("fields") or []:
                    if f and fld.get("name") != f:
                        continue
                    out.append(f"{per}.{reg}.{fld.get('name','')}  {key}={_fmt(key, fld.get(key))}")
            else:
                out.append(_reg_header(per, reg, rd))
                for fld in rd.get("fields") or []:
                    if f and fld.get("name") != f:
                        continue
                    out.append(_field_line(fld))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svd", help="path to an .svd file")
    ap.add_argument("-p", "--peripheral", help="peripheral name (e.g. bkp, hash)")
    ap.add_argument("-r", "--register", help="register name (e.g. dr1, hr0)")
    ap.add_argument("-k", "--key", choices=_REGISTER_KEYS + _FIELD_KEYS,
                    help="show only this attribute")
    ap.add_argument("-f", "--field", help="restrict field-level output to this field")
    args = ap.parse_args()

    peripherals = parse_svd(args.svd)
    lines = lookup(peripherals, args.peripheral, args.register, args.key, args.field)
    if not lines:
        print("no match", file=sys.stderr)
        sys.exit(1)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
