"""In-memory diff between a ground-truth SVD and the generator's register output.

Replaces ``scripts/s2_compare_agent_output_with_svd.py``: instead of writing
``register_diff.csv`` / ``field_diff.csv`` / ``*_summary.csv``, this returns a
``list[Diff]`` that downstream stages consume directly.

A ``Diff`` is either:
  * a **value mismatch** (``presence == BOTH``) — the register/field exists on
    both sides but a value differs; these are the candidate SVD bugs; or
  * a **coverage gap** (``SVD_ONLY`` / ``GENERATOR_ONLY``) — a peripheral,
    register, or field present on only one side.

Comparison semantics (offset/reset hex normalization, the size 16↔32 / size-0
skips, the empty-generator-value skip, field bit_offset/bit_width) are preserved
from the original script. Enumerated values are intentionally not diffed:
verified datasheets are layout-only and enums are out of scope.
"""
from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from typing import Any, Optional

from agent_tools.svd_parsing import resolve_peripheral_registers, expand_dim_indices
from utils.generator_facts import convert_generator_register_to_svd_like
from .models import Diff, Presence

# Register-level attributes compared (in a stable order).
_REGISTER_KEYS = ("address_offset", "reset_value", "size")
_HEX_KEYS = ("address_offset", "reset_value")
# Field-level attributes compared. `access` is validated downstream (s6, datasheet-
# grounded) rather than by the context-free analyzer — see pipeline.run_bug_finding.
_FIELD_KEYS = ("bit_offset", "bit_width", "access")

# Access is canonicalized to read-write/read-only/write-only via the SAME shared
# notation map the validator uses (optimization_validator/access_notations.json),
# so vocabulary variants (rw, write, rc_w1, write-1-to-clear, …) collapse and don't
# become spurious diffs. Unicode hyphens (U+2011 etc.) -> ASCII first, since the
# generator sometimes emits them. An unrecognized token falls back to its cleaned
# form so a genuinely novel value still compares.
from optimization_validator.access_notation import canonical_access  # noqa: E402

_UNI_HYPHENS = str.maketrans({c: "-" for c in "‐‑‒–—−"})


def _norm_access(a) -> str:
    s = str(a or "").strip().lower().translate(_UNI_HYPHENS)
    return canonical_access(s) or s


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------

def _to_int_if_hex(value: Any) -> Any:
    """Parse a ``0x...`` string to int; pass through anything else unchanged."""
    if isinstance(value, str) and value.strip().startswith("0x"):
        try:
            return int(value.strip().replace(" ", ""), 16)
        except ValueError:
            return value
    return value


def _hex_display(value: Any) -> Optional[str]:
    """Render an int as ``0xNN`` for display; stringify others; None stays None."""
    if value is None:
        return None
    if isinstance(value, int):
        return f"0x{value:X}"
    return str(value)


def _stringify(value: Any) -> Optional[str]:
    return None if value is None else str(value)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_svd_registers(svd_path: str) -> dict[str, dict[str, dict]]:
    """Parse an SVD file into ``{peripheral: {register: {...}}}`` (all lowercase),
    resolving peripheral- AND register-level ``derivedFrom`` (with device/peripheral
    size/resetValue/access property inheritance) and expanding ``<dim>`` arrays to
    concrete names (``BCR%s`` -> ``bcr2/bcr3/bcr4``). Dim expansion is controlled by
    env ``SVD_DIM_EXPAND`` (default on; set ``0`` to keep collapsed ``%s`` names, for
    diffing against legacy pre-expansion generator output).

    Each register dict has ``address_offset`` (int), ``reset_value`` (int or ''),
    ``size`` (int or None), and ``fields`` (list of ``{name, bit_offset,
    bit_width, enumerated_values}``).
    """
    root = ET.parse(svd_path).getroot()
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""

    # Resolve derivedFrom so derived instances (i2c2, usart2..8, ...) inherit the
    # base peripheral's registers instead of parsing to zero.
    resolved = resolve_peripheral_registers(root, ns)

    # CMSIS-SVD register properties (size/resetValue) cascade device -> peripheral
    # -> register, and a register may inherit another via register-level
    # derivedFrom (e.g. ADC2.CR2 derivedFrom="ADC1.CR2" — only addressOffset given).
    # resolve_peripheral_registers only handles peripheral-level derivedFrom, so
    # resolve register-level derivedFrom + property inheritance here (else the
    # inheriting registers parse to None and look like spurious diffs).
    def _int0(elem):
        return int(elem.text.strip(), 0) if elem is not None and (elem.text or "").strip() else None

    def _reset(elem):
        e = elem.find(f"{ns}resetValue") if elem is not None else None
        return _to_int_if_hex(e.text.strip()) if e is not None and (e.text or "").strip() else None

    dev_size = _int0(root.find(f"{ns}size"))
    dev_reset = _reset(root)
    dev_access = (root.findtext(f"{ns}access") or "").strip().lower()

    per_elem = {(p.findtext(f"{ns}name") or "").strip().lower(): p for p in root.iter(f"{ns}peripheral")}
    reg_index: dict[tuple[str, str], Any] = {}
    for pn, p in per_elem.items():
        regs = p.find(f"{ns}registers")
        if regs is None:
            continue
        for r in regs.findall(f"{ns}register"):
            reg_index.setdefault((pn, (r.findtext(f"{ns}name") or "").strip().lower()), r)

    def _per_defaults(pn):
        p = per_elem.get(pn)
        return (_int0(p.find(f"{ns}size")) if p is not None else None, _reset(p))

    def _per_access(pn):
        p = per_elem.get(pn)
        return ((p.findtext(f"{ns}access") or "").strip().lower() if p is not None else "") or dev_access

    def _fields_of(reg, fallback_access=""):
        fe = reg.find(f"{ns}fields")
        if fe is None:
            return None  # not specified locally -> inheritable
        out = []
        for field in fe.findall(f"{ns}field"):
            enum_values = []
            enum_elem = field.find(f"{ns}enumeratedValues")
            if enum_elem is not None:
                for enum in enum_elem.findall(f"{ns}enumeratedValue"):
                    if enum.find(f"{ns}value") is not None:
                        enum_values.append({
                            "name": enum.find(f"{ns}name").text.strip().lower(),
                            "value": enum.find(f"{ns}value").text.strip(),
                        })
            out.append({
                "name": field.find(f"{ns}name").text.strip().lower(),
                "bit_offset": int(field.find(f"{ns}bitOffset").text.strip()),
                "bit_width": int(field.find(f"{ns}bitWidth").text.strip()),
                "enumerated_values": enum_values,
                # access cascades field -> register -> peripheral -> device (CMSIS).
                "access": (field.findtext(f"{ns}access") or "").strip().lower() or fallback_access,
            })
        return out

    def _resolve_reg(pn, reg, seen=()):
        base = None
        df = reg.get("derivedFrom")
        if df:
            bp, br = df.split(".", 1) if "." in df else (pn, df)
            key = (bp.strip().lower(), br.strip().lower())
            if key in reg_index and key not in seen:
                base = _resolve_reg(key[0], reg_index[key], seen + (key,))
        ao_e = reg.find(f"{ns}addressOffset")
        address_offset = (_to_int_if_hex(ao_e.text.strip()) if ao_e is not None and (ao_e.text or "").strip()
                          else (base["address_offset"] if base else None))
        size = _int0(reg.find(f"{ns}size"))
        reset_value = _reset(reg)
        reg_access = (reg.findtext(f"{ns}access") or "").strip().lower() or _per_access(pn)
        fields = _fields_of(reg, reg_access)
        per_size, per_reset = _per_defaults(pn)
        if size is None:
            size = base["size"] if base and base.get("size") is not None else (per_size if per_size is not None else dev_size)
        if reset_value is None:
            reset_value = (base["reset_value"] if base and base.get("reset_value") not in (None, "")
                           else (per_reset if per_reset is not None else dev_reset))
        if fields is None:
            fields = base["fields"] if base else []
        return {
            "address_offset": address_offset,
            "reset_value": reset_value if reset_value is not None else "",
            "size": size,
            "fields": fields,
        }

    def _strip(name):
        prefix = peripheral_name + "_"
        return name[len(prefix):] if name.startswith(prefix) else name

    # Expand <dim> arrays to match the generator (which now expands them too).
    # Set SVD_DIM_EXPAND=0 only to regenerate reviews against LEGACY generator
    # output that still has the collapsed `%s` files (else bcr2/3/4 would show as
    # coverage gaps against the on-disk bcr%s).
    expand_dim = os.environ.get("SVD_DIM_EXPAND", "1") != "0"

    peripherals: dict[str, dict[str, dict]] = {}
    for peripheral_name, registers_elem in resolved.items():
        registers: dict[str, dict] = {}
        if registers_elem is not None:
            for reg in registers_elem.findall(f"{ns}register"):
                base = _resolve_reg(peripheral_name, reg)
                raw = reg.find(f"{ns}name").text.strip()
                idxs = expand_dim_indices(reg, ns) if (expand_dim and "%s" in raw) else []
                if idxs:
                    # Expand a <dim> array (BCR%s -> bcr2/bcr3/bcr4), each at its own
                    # offset = base + position*dimIncrement, matching the generator's
                    # expanded output so they compare register-for-register.
                    inc_txt = (reg.findtext(f"{ns}dimIncrement") or "").strip()
                    try:
                        inc = int(inc_txt, 0) if inc_txt else 0
                    except ValueError:
                        inc = 0
                    base_off = base["address_offset"] if isinstance(base["address_offset"], int) else 0
                    tmpl = raw.replace("[%s]", "%s")
                    for pos, ix in enumerate(idxs):
                        inst = dict(base)
                        inst["address_offset"] = base_off + pos * inc
                        registers[_strip(tmpl.replace("%s", ix).lower())] = inst
                else:
                    registers[_strip(raw.lower())] = base
        peripherals[peripheral_name] = registers
    return peripherals


def _split_peripheral_register(filename: str) -> Optional[tuple[str, str]]:
    """Split a ``{peripheral}_{register}`` output filename on the first underscore.

    Splitting on the first ``_`` (vs. the old ``split('_')[0]``/``[1]``) keeps
    multi-token register names intact (e.g. ``GPIOA_AFRL`` → ``gpioa``/``afrl``),
    matching how the SVD register names are stored.
    """
    peripheral, sep, register = filename.partition("_")
    if not sep:
        return None
    return peripheral.lower(), register.lower()


def load_generator_registers(agent_output_dir: str) -> dict[str, dict[str, dict]]:
    """Load generator output into ``{peripheral: {register: svd_like_dict}}``.

    Each register JSON (one file per ``{peripheral}_{register}``, no extension) is
    converted to the SVD-like shape used by the comparison.
    """
    peripherals: dict[str, dict[str, dict]] = {}
    for entry in os.listdir(agent_output_dir):
        path = os.path.join(agent_output_dir, entry)
        if os.path.isdir(path):
            continue
        split = _split_peripheral_register(entry)
        if split is None:
            continue
        peripheral_name, register_name = split
        with open(path, "r", encoding="utf-8") as f:
            register_data = json.load(f)
        svd_like = convert_generator_register_to_svd_like(
            register_data, include_enums=True, default_zero=False,
        )
        peripherals.setdefault(peripheral_name, {})[register_name] = svd_like
    return peripherals


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def _skip_register_value(key: str, svd_value: Any, gen_value: Any) -> bool:
    """Replicate the original script's skip rules for register-level values."""
    if gen_value == "":
        return True
    if key == "size":
        # 16/32-bit width is an accepted representational variation; size 0 means
        # the generator didn't determine a size.
        if {svd_value, gen_value} == {16, 32}:
            return True
        if gen_value == 0:
            return True
    return False


def _compare_fields(peripheral: str, register: str,
                    svd_fields: list[dict], gen_fields: list[dict]) -> list[Diff]:
    diffs: list[Diff] = []
    svd_by = {f["name"]: f for f in svd_fields}
    gen_by = {f["name"]: f for f in gen_fields}
    svd_names, gen_names = set(svd_by), set(gen_by)

    for name in sorted(svd_names - gen_names):
        diffs.append(Diff(peripheral=peripheral, register=register, field=name,
                          key="field", presence=Presence.SVD_ONLY))
    for name in sorted(gen_names - svd_names):
        diffs.append(Diff(peripheral=peripheral, register=register, field=name,
                          key="field", presence=Presence.GENERATOR_ONLY))

    for name in sorted(svd_names & gen_names):
        sf, gf = svd_by[name], gen_by[name]
        for key in _FIELD_KEYS:
            sv, gv = sf.get(key), gf.get(key)
            if key == "access":
                sv, gv = _norm_access(sv), _norm_access(gv)
            if sv != gv:
                diffs.append(Diff(
                    peripheral=peripheral, register=register, field=name, key=key,
                    svd_value=_stringify(sv), generator_value=_stringify(gv),
                    presence=Presence.BOTH,
                ))
    return diffs


def _compare_register(peripheral: str, register: str,
                      svd_reg: dict, gen_reg: dict) -> list[Diff]:
    diffs: list[Diff] = []
    for key in _REGISTER_KEYS:
        svd_value, gen_value = svd_reg.get(key), gen_reg.get(key)
        if key in _HEX_KEYS:
            svd_value, gen_value = _to_int_if_hex(svd_value), _to_int_if_hex(gen_value)
        if _skip_register_value(key, svd_value, gen_value):
            continue
        if svd_value != gen_value:
            if key in _HEX_KEYS:
                svd_disp, gen_disp = _hex_display(svd_value), _hex_display(gen_value)
            else:
                svd_disp, gen_disp = _stringify(svd_value), _stringify(gen_value)
            diffs.append(Diff(
                peripheral=peripheral, register=register, key=key,
                svd_value=svd_disp, generator_value=gen_disp, presence=Presence.BOTH,
                reg_size=svd_reg.get("size"),
            ))
    diffs.extend(_compare_fields(peripheral, register,
                                 svd_reg.get("fields", []), gen_reg.get("fields", [])))
    return diffs


def compute_diffs(svd_peripherals: dict[str, dict[str, dict]],
                  gen_peripherals: dict[str, dict[str, dict]]) -> list[Diff]:
    """Compare parsed SVD vs generator registers and return all diffs."""
    diffs: list[Diff] = []
    svd_names, gen_names = set(svd_peripherals), set(gen_peripherals)

    for name in sorted(svd_names - gen_names):
        diffs.append(Diff(peripheral=name, register="", key="peripheral",
                          presence=Presence.SVD_ONLY))
    for name in sorted(gen_names - svd_names):
        diffs.append(Diff(peripheral=name, register="", key="peripheral",
                          presence=Presence.GENERATOR_ONLY))

    for peripheral in sorted(svd_names & gen_names):
        svd_regs, gen_regs = svd_peripherals[peripheral], gen_peripherals[peripheral]
        svd_reg_names, gen_reg_names = set(svd_regs), set(gen_regs)

        for reg in sorted(svd_reg_names - gen_reg_names):
            diffs.append(Diff(peripheral=peripheral, register=reg, key="register",
                              presence=Presence.SVD_ONLY))
        for reg in sorted(gen_reg_names - svd_reg_names):
            diffs.append(Diff(peripheral=peripheral, register=reg, key="register",
                              presence=Presence.GENERATOR_ONLY))
        for reg in sorted(svd_reg_names & gen_reg_names):
            diffs.extend(_compare_register(peripheral, reg, svd_regs[reg], gen_regs[reg]))

    return diffs


def diff_generator_against_svd(svd_path: str, agent_output_dir: str) -> list[Diff]:
    """Top-level convenience: parse both sides and return all diffs."""
    svd = parse_svd_registers(svd_path)
    gen = load_generator_registers(agent_output_dir)
    return compute_diffs(svd, gen)
