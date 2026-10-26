"""Deterministic fill of missing register structural values from the datasheet's
register-summary / memory-map tables.

NXP/Kinetis manuals put each register's address offset and reset value in a
peripheral register-overview table (one row: ``| Name | Access | Offset | … |
Reset value |``), separate from the register's own bit-field section. The
openevolve retriever returns the bit-field section but downranks that summary
table, so the generator frequently leaves ``address_offset`` / ``reset_value``
null even though the manual states them.

These summary tables are long and the chunker splits them at page/chunk
boundaries: each page's first chunk re-emits the header row (and the peripheral
name), while overflow register rows land in the next chunk with NO header and NO
peripheral string. A per-chunk parser therefore sees orphaned rows it can't
column-map and can't peripheral-scope, and misses most of the table.

This module instead concatenates the chunks in page order and does a single
sticky-header linear scan: a header row (with an offset/address column) sets the
active column map and captures the preceding text window (which carries the
peripheral name); every following pipe row — even across the chunk boundary — is
read with that column map and attributed to a peripheral via the captured window.
We fill ONLY values the generator left empty, and ONLY when the summary yields a
single unambiguous value for that (peripheral, register) — so we never overwrite
an extracted value, never guess, and short colliding names (CTRL, STAT) that
resolve to two distinct values are skipped rather than mis-filled. Validated on
lpc845: recovers address_offset / reset_value with zero disagreements vs SVD.
"""
from __future__ import annotations
import glob
import json
import os
import re

__all__ = ["fill_run", "summary_values", "build_index"]

# ``{device}_p{page}_c{chunk}.txt`` — used to order chunks so split tables rejoin.
_CHUNK_ORDER_RE = re.compile(r"_p(\d+)_c(\d+)\.txt$")
# Characters of text before a header row scanned for the owning peripheral name.
_HEADER_WINDOW = 2000


def _nn(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _is_hex(s: str) -> bool:
    s = (s or "").strip()
    try:
        int(s.replace(" ", ""), 16)
        return bool(s)
    except ValueError:
        return False


def _cells(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _col(hdr, *keys):
    for i, h in enumerate(hdr):
        if any(k in h for k in keys):
            return i
    return None


def _ordered_corpus(chunks_dir: str) -> str:
    """Concatenate every ``*.txt`` chunk in (page, chunk) order so a summary table
    split across chunk files is rejoined into one contiguous table."""
    def sort_key(path):
        m = _CHUNK_ORDER_RE.search(os.path.basename(path))
        return (int(m.group(1)), int(m.group(2))) if m else (1 << 30, os.path.basename(path))

    files = sorted(glob.glob(os.path.join(chunks_dir, "*.txt")), key=sort_key)
    return "\n".join(open(f, encoding="utf-8", errors="ignore").read() for f in files)


def build_index(chunks_dir: str) -> list:
    """Return a list of summary-table rows ``(name_norm, offset, reset, window_upper)``
    parsed from the page-ordered corpus with a sticky-header scan. ``window_upper``
    is the uppercased text just before the governing header (carries the peripheral
    name, used for peripheral scoping in :func:`summary_values`)."""
    corpus = _ordered_corpus(chunks_dir)
    lines = corpus.splitlines()
    # char offset of each line start, so a header can capture its preceding window
    starts, c = [], 0
    for ln in lines:
        starts.append(c)
        c += len(ln) + 1

    rows: list = []
    active = None  # (name_i, offset_i, reset_i, window_upper)
    for idx, ln in enumerate(lines):
        s = ln.strip()
        if not s.startswith("|"):
            continue
        is_header = idx + 1 < len(lines) and re.match(r"^\|[\s:|\-]+\|?\s*$", lines[idx + 1].strip())
        if is_header:
            hdr = [h.lower() for h in _cells(s)]
            oi = _col(hdr, "offset", "address")
            if oi is None:
                active = None
                continue
            ni = _col(hdr, "name", "register")
            ri = _col(hdr, "reset")
            win = corpus[max(0, starts[idx] - _HEADER_WINDOW):starts[idx]].upper()
            active = (0 if ni is None else ni, oi, ri, win)
            continue
        if active is None:
            continue
        ni, oi, ri, win = active
        row = _cells(s)
        if max(ni, oi, ri if ri is not None else 0) >= len(row):
            continue
        name = row[ni]
        if not name or name.lower() in ("-", "name", "register"):
            continue
        offv = row[oi].strip() if _is_hex(row[oi]) else None
        rstv = row[ri].strip() if (ri is not None and ri < len(row) and _is_hex(row[ri])) else None
        if offv or rstv:
            rows.append((_nn(name), offv, rstv, win))
    return rows


def summary_values(peripheral: str, register: str, index: list) -> dict:
    """Return ``{'address_offset': ..., 'reset_value': ...}`` for the register's
    summary-table row — only values that are unambiguous across all peripheral-
    scoped matches. Peripheral scope: the governing header's preceding window must
    mention the peripheral base (disambiguates short names shared across
    peripherals, e.g. ``CTRL``)."""
    r_norm = _nn(register)
    p_base = peripheral.upper().rstrip("0123456789")
    offsets, resets = set(), set()
    for name_n, offv, rstv, win in index:
        if name_n != r_norm or p_base not in win:
            continue
        if offv:
            offsets.add(offv)
        if rstv:
            resets.add(rstv)
    out = {}
    if len(offsets) == 1:
        out["address_offset"] = next(iter(offsets))
    if len(resets) == 1:
        out["reset_value"] = next(iter(resets))
    return out


def _empty(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def fill_run(agent_output_dir: str, chunks_dir: str) -> dict:
    """Fill missing address_offset / reset_value in each register output file from
    the datasheet summary tables. Only fills empties; never overwrites. Returns
    stats. Register files are named ``{peripheral}_{register}`` (peripheral has no
    underscore for NXP; split on the first underscore)."""
    index = build_index(chunks_dir)
    if not index:
        return {"error": f"no summary-table rows parsed from {chunks_dir}",
                "filled_offset": 0, "filled_reset": 0, "registers_with_gaps": 0}

    filled_off = filled_rst = considered = 0
    for f in glob.glob(os.path.join(agent_output_dir, "*")):
        if os.path.isdir(f):
            continue
        name = os.path.basename(f)
        if "_" not in name:
            continue
        try:
            data = json.loads(open(f, encoding="utf-8").read())
        except (ValueError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        need_off = _empty(data.get("address_offset"))
        need_rst = _empty(data.get("reset_value"))
        if not (need_off or need_rst):
            continue
        considered += 1
        peripheral, register = name.split("_", 1)
        vals = summary_values(peripheral, register, index)
        changed = False
        if need_off and "address_offset" in vals:
            data["address_offset"] = vals["address_offset"]; filled_off += 1; changed = True
        if need_rst and "reset_value" in vals:
            data["reset_value"] = vals["reset_value"]; filled_rst += 1; changed = True
        if changed:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
    return {"registers_with_gaps": considered, "filled_offset": filled_off, "filled_reset": filled_rst}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("agent_output_dir")
    ap.add_argument("chunks_dir")
    args = ap.parse_args()
    print(json.dumps(fill_run(args.agent_output_dir, args.chunks_dir), indent=2))
