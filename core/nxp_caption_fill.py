"""Deterministic fill of missing register address offsets from datasheet
register-TABLE CAPTIONS (NXP Group D: LPC55xx / i.MX RT).

Group-D manuals (modern NXP) have no register-summary table; each register's
bit-field table is captioned with its offset, e.g.::

    Table 197. Run configuration register 0 (SYSCTL0_PDRUNCFG0: offset = 0x620)
    Memory remap control register (MEMORYREMAP, offset = 0x0)

(the separator is ``:`` on i.MX RT, ``,`` on LPC55xx). The generator extracts the
offset for only ~47% of Group-D registers; this pass parses the captions and fills
the empties. The caption name may be the full ``PERIPHERAL_REG`` (i.MX RT) or the
bare register name (LPC55xx) — we match either, and for the bare form we require
the peripheral to appear in the text just before the caption (peripheral scope),
so a short name shared across peripherals (e.g. ``CTRL``) can't be mis-filled.
Fills empties only, only when a single unambiguous offset is found; never
overwrites. Validated: 0 disagreements with the SVD when scoped.
"""
from __future__ import annotations
import glob
import json
import os
import re

__all__ = ["fill_run", "build_index", "caption_offset"]

# name, separator (, or :), offset. Name is letters/digits/underscore.
_CAPTION = re.compile(r"\(([A-Za-z0-9_]+)\s*[,:]\s*offset\s*=\s*(0x[0-9A-Fa-f]+)\)")
_WINDOW = 400  # chars before the caption scanned for the owning peripheral name


def _nn(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def build_index(chunks_dir: str) -> dict:
    """``nn(caption_name) -> list[(offset_lower, preceding_window_upper)]``."""
    idx: dict = {}
    for f in glob.glob(os.path.join(chunks_dir, "*.txt")):
        txt = open(f, encoding="utf-8", errors="ignore").read()
        for m in _CAPTION.finditer(txt):
            win = txt[max(0, m.start() - _WINDOW):m.start()].upper()
            idx.setdefault(_nn(m.group(1)), []).append((m.group(2).lower(), win))
    return idx


def caption_offset(peripheral: str, register: str, index: dict):
    """A single unambiguous caption offset for this register, or None."""
    p_base = peripheral.upper().rstrip("0123456789")
    bare = _nn(register)
    prefixed = {_nn(f"{peripheral}_{register}"), _nn(f"{peripheral}{register}")}
    offsets = set()
    for key, scoped in [(bare, True)] + [(k, False) for k in prefixed]:
        for off, win in index.get(key, []):
            # bare register name shared across peripherals → require the peripheral
            # near the caption; prefixed keys already carry the peripheral.
            if scoped and p_base and p_base not in win and p_base not in key:
                continue
            offsets.add(off)
    return next(iter(offsets)) if len(offsets) == 1 else None


def _empty(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def fill_run(agent_output_dir: str, chunks_dir: str) -> dict:
    """Fill empty ``address_offset`` from register-table captions. Empties only."""
    index = build_index(chunks_dir)
    if not index:
        return {"caption_names": 0, "filled_offset": 0, "offset_gaps": 0}
    filled = considered = 0
    for f in glob.glob(os.path.join(agent_output_dir, "*")):
        if os.path.isdir(f) or "_" not in os.path.basename(f):
            continue
        try:
            d = json.loads(open(f, encoding="utf-8").read())
        except (ValueError, OSError):
            continue
        if not isinstance(d, dict) or not _empty(d.get("address_offset")):
            continue
        considered += 1
        peripheral, register = os.path.basename(f).split("_", 1)
        off = caption_offset(peripheral, register, index)
        if off is not None:
            d["address_offset"] = off
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(d, fh)
            filled += 1
    return {"caption_names": len(index), "offset_gaps": considered, "filled_offset": filled}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_output_dir")
    ap.add_argument("chunks_dir")
    a = ap.parse_args()
    print(json.dumps(fill_run(a.agent_output_dir, a.chunks_dir), indent=2))
