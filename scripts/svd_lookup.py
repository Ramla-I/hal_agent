#!/usr/bin/env python3
"""Look up SVD entries by peripheral / register / key, across one or many SVDs.

Shows the SVD *faithfully*: literal register names (so HASH keeps both `HR0` @0xC
and `HASH_HR0` @0x310 instead of colliding), peripheral `derivedFrom` resolved
(so ADC3 shows the registers it inherits from ADC1), `<dim>` arrays expanded to
concrete names, size/resetValue/access inheritance applied, and each register's
absolute address (baseAddress + offset).

Register matching is flexible: `-r hr0` matches the literal name OR its
peripheral-prefix-stripped form, so it finds both `hr0` and `hash_hr0`.

Fields are hidden by default; pass --fields to include them (or query a
field-level key with -k, which always shows per field).

Selecting SVDs:
  - one or more positional paths, OR
  - -d/--dir DIR with -f/--files a,b,c  (picks files whose name contains each
    fragment); --patched uses the `.svd.patched` variants svdtools writes.
  With 2+ SVDs the output is a comparison table.

  # single SVD, whole register (no fields unless --fields)
  python scripts/svd_lookup.py devices/stm/rm0090/svd/stm32f417.svd -p hash -r hr0
  python scripts/svd_lookup.py <svd> -p bkp -r dr1 -k address_offset
  python scripts/svd_lookup.py <svd> -p hash -r hr0 --fields

  # compare a register across a set of SVDs (table)
  python scripts/svd_lookup.py -d svd -f f101,f102,f103,f107 --patched -p fsmc -r bcr1
  python scripts/svd_lookup.py -d svd -f f101,f103 -p fsmc -r bcr1 -k address_offset
  python scripts/svd_lookup.py -d svd -f f101,f103 -p fsmc -r bcr1 --fields   # field pivot

Keys: address_offset, reset_value, size (register-level);
      bit_offset, bit_width, access (field-level).
"""
from __future__ import annotations

import argparse
import glob
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
    """0x/decimal via base-0, else bare hex (resetValue ``00000010``). None if bad."""
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
    """Faithful ``{peripheral: {register: {...}}}`` (lowercase keys, literal names)."""
    root = ET.parse(svd_path).getroot()
    ns = root.tag[: root.tag.index("}") + 1] if "}" in root.tag else ""

    def txt(elem, tag):
        return (elem.findtext(f"{ns}{tag}") or "").strip() if elem is not None else ""

    dev_size = _int0(txt(root, "size"))
    dev_reset = _int0(txt(root, "resetValue"))
    dev_access = txt(root, "access").lower()

    per_elem = {(p.findtext(f"{ns}name") or "").strip().lower(): p
                for p in root.iter(f"{ns}peripheral")}
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
            if bo is None and txt(fl, "bitRange"):
                hi, lo = (int(x, 0) for x in txt(fl, "bitRange").strip("[]").split(":"))
                bo, bw = lo, hi - lo + 1
            out.append({"name": txt(fl, "name").lower(), "bit_offset": bo,
                        "bit_width": bw, "access": txt(fl, "access").lower()})
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
                        registers[tmpl.replace("%s", ix).lower()] = dict(rd, address_offset=boff + pos * inc)
                else:
                    registers[raw.lower()] = rd
        out[pn] = registers
    return out


# ------------------------------------------------------------------ selecting --

def _label(path: str) -> str:
    b = os.path.basename(path)
    for suf in (".svd.patched", ".svd"):
        if b.endswith(suf):
            return b[: -len(suf)]
    return b


def resolve_svds(args) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    fellback: list[str] = []

    def pick(base_svd: str) -> str:
        """Path to read: the .svd.patched when --patched and it exists, else fall
        back to the base .svd (recording the fallback so we can warn about it)."""
        if args.patched:
            patched = base_svd + ".patched"
            if os.path.exists(patched):
                return patched
            fellback.append(_label(base_svd))
        return base_svd

    directory = args.dir or ("." if args.files else None)
    if directory:
        frags = [f.strip() for f in (args.files or "").split(",") if f.strip()] or ["*"]
        for frag in frags:
            for base in sorted(glob.glob(os.path.join(directory, f"*{frag}*.svd"))):
                pairs.append((_label(base), pick(base)))
    for p in args.svd:
        if p.endswith(".patched"):        # explicit patched path — respect it as given
            pairs.append((_label(p), p))
        else:
            pairs.append((_label(p), pick(p)))

    seen, out = set(), []
    for lbl, pth in pairs:
        if pth not in seen:
            seen.add(pth)
            out.append((lbl, pth))
    if fellback:
        print(f"note: no .svd.patched for {', '.join(sorted(set(fellback)))} — used the raw .svd",
              file=sys.stderr)
    return out


# ------------------------------------------------------------------- querying --

def _fmt(key: str, val) -> str:
    if val is None or val == "":
        return "?"
    if key in _HEX_KEYS and isinstance(val, int):
        return f"0x{val:X}"
    return str(val)


def _bits(fld: dict) -> str:
    lo, w = fld.get("bit_offset"), fld.get("bit_width")
    return f"[{lo + w - 1}:{lo}]" if isinstance(lo, int) and isinstance(w, int) else "?"


def _reg_matches(regname: str, query: str, peripheral: str) -> bool:
    return query in (regname, _strip_peripheral_prefix(regname, peripheral))


def _matched(peripherals: dict, peripheral, register):
    """Yield (per, reg, regdict) for the query, in sorted order."""
    p = peripheral.lower() if peripheral else None
    r = register.lower() if register else None
    for per in sorted(peripherals):
        if p and per != p:
            continue
        for reg in sorted(peripherals[per]):
            if r and not _reg_matches(reg, r, per):
                continue
            yield per, reg, peripherals[per][reg]


def _abs(rd: dict) -> str:
    off, base = rd.get("address_offset"), rd.get("_peripheral_base")
    return _fmt("address_offset", base + off) if isinstance(base, int) and isinstance(off, int) else "?"


def _print_table(headers: list[str], rows: list[list[str]]) -> None:
    cols = range(len(headers))
    widths = [max([len(str(headers[i]))] + [len(str(r[i])) for r in rows]) for i in cols]
    line = lambda cells: "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells))
    print(line(headers))
    print("  ".join("-" * widths[i] for i in cols))
    for r in rows:
        print(line(r))


# ---------------------------------------------------------------- rendering ----

def render_vertical(peripherals: dict, args) -> list[str]:
    if not args.peripheral and not args.register:
        return [f"{n}  ({len(peripherals[n])} registers)" for n in sorted(peripherals)]
    key, fld = args.key, (args.field.lower() if args.field else None)
    field_level = key in _FIELD_KEYS
    lines: list[str] = []
    for per, reg, rd in _matched(peripherals, args.peripheral, args.register):
        if key in _REGISTER_KEYS:
            lines.append(f"{per}.{reg}  {key}={_fmt(key, rd.get(key))}")
        elif field_level:
            for f in rd.get("fields") or []:
                if fld and f.get("name") != fld:
                    continue
                lines.append(f"{per}.{reg}.{f.get('name','')}  {key}={_fmt(key, f.get(key))}")
        else:
            lines.append(f"{per}.{reg}  offset={_fmt('address_offset', rd.get('address_offset'))}  "
                         f"reset={_fmt('reset_value', rd.get('reset_value'))}  "
                         f"size={_fmt('size', rd.get('size'))}  access={rd.get('access') or '?'}  "
                         f"abs={_abs(rd)}")
            if args.fields:
                for f in rd.get("fields") or []:
                    if fld and f.get("name") != fld:
                        continue
                    lines.append(f"    {f.get('name',''):<18} bits={_bits(f):<9} "
                                 f"width={_fmt('bit_width', f.get('bit_width')):<4} "
                                 f"access={f.get('access') or '?'}")
    return lines


def _field_pivot(per, reg, by_label, labels, attr, fld_filter) -> None:
    """attr None => show bit ranges; else the field-level key value. One column per SVD."""
    fmap = {l: {f["name"]: f for f in (by_label.get(l) or {}).get("fields") or []} for l in labels}
    order, seen = [], set()
    for l in labels:
        for f in (by_label.get(l) or {}).get("fields") or []:
            n = f["name"]
            if n not in seen and (not fld_filter or n == fld_filter):
                seen.add(n)
                order.append(n)
    order.sort(key=lambda n: next((fmap[l][n]["bit_offset"] for l in labels
                                   if n in fmap[l] and fmap[l][n].get("bit_offset") is not None), 1 << 30))
    rows = []
    for n in order:
        cells = [n]
        for l in labels:
            f = fmap[l].get(n)
            cells.append("-" if not f else (_bits(f) if attr is None else _fmt(attr, f.get(attr))))
        rows.append(cells)
    if rows:
        print(f"\n{per}.{reg} fields ({'bits' if attr is None else attr}):")
        _print_table(["field"] + labels, rows)


def render_table(parsed: list[tuple[str, dict]], args) -> None:
    labels = [lbl for lbl, _ in parsed]
    key = args.key
    field_level = key in _FIELD_KEYS

    if not field_level:
        headers = ["svd", "location"] + (
            [key] if key in _REGISTER_KEYS else ["offset", "reset", "size", "access", "abs"])
        rows = []
        for lbl, per_dict in parsed:
            for per, reg, rd in _matched(per_dict, args.peripheral, args.register):
                if key in _REGISTER_KEYS:
                    rows.append([lbl, f"{per}.{reg}", _fmt(key, rd.get(key))])
                else:
                    rows.append([lbl, f"{per}.{reg}", _fmt("address_offset", rd.get("address_offset")),
                                 _fmt("reset_value", rd.get("reset_value")), _fmt("size", rd.get("size")),
                                 rd.get("access") or "?", _abs(rd)])
        if rows:
            _print_table(headers, rows)
        else:
            print("no match", file=sys.stderr)
            sys.exit(1)

    # field pivots: when a field-level key is asked, or --fields with a full-register view
    if field_level or (args.fields and key not in _REGISTER_KEYS):
        regkeys, regmap = [], {}
        for lbl, per_dict in parsed:
            for per, reg, rd in _matched(per_dict, args.peripheral, args.register):
                if (per, reg) not in regmap:
                    regmap[(per, reg)] = {}
                    regkeys.append((per, reg))
                regmap[(per, reg)][lbl] = rd
        attr = key if field_level else None
        fld = args.field.lower() if args.field else None
        for per, reg in regkeys:
            _field_pivot(per, reg, regmap[(per, reg)], labels, attr, fld)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("svd", nargs="*", help="one or more .svd paths (or use -d/-f)")
    ap.add_argument("-d", "--dir", help="directory to select SVDs from")
    ap.add_argument("-f", "--files", help="comma-separated name fragments to pick from --dir")
    ap.add_argument("--patched", action="store_true",
                    help="use the .svd.patched variants (falls back to the raw .svd if missing)")
    ap.add_argument("-p", "--peripheral", help="peripheral name (e.g. bkp, hash)")
    ap.add_argument("-r", "--register", help="register name (e.g. dr1, hr0)")
    ap.add_argument("-k", "--key", choices=_REGISTER_KEYS + _FIELD_KEYS, help="show only this attribute")
    ap.add_argument("--field", help="restrict field output to this field")
    ap.add_argument("--fields", action="store_true", help="include register fields in the output")
    args = ap.parse_args()

    svds = resolve_svds(args)
    if not svds:
        print("no SVDs selected (give a path, or -d DIR with -f a,b,c)", file=sys.stderr)
        sys.exit(2)

    parsed: list[tuple[str, dict]] = []
    for lbl, path in svds:
        try:
            parsed.append((lbl, parse_svd(path)))
        except (ET.ParseError, FileNotFoundError, OSError) as e:
            print(f"!! {lbl}: {type(e).__name__}: {e}", file=sys.stderr)
    if not parsed:
        sys.exit(1)

    if len(parsed) == 1:
        lines = render_vertical(parsed[0][1], args)
        if not lines:
            print("no match", file=sys.stderr)
            sys.exit(1)
        print("\n".join(lines))
    else:
        if not args.peripheral and not args.register:
            for lbl, per_dict in parsed:
                print(f"# {lbl}")
                for n in sorted(per_dict):
                    print(f"  {n}  ({len(per_dict[n])} registers)")
            return
        render_table(parsed, args)


if __name__ == "__main__":
    main()
