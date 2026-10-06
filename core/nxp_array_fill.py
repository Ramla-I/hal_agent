"""Deterministic recovery of absent register-array instances by cloning a
datasheet-extracted sibling.

SVDs expand register arrays to concrete instances (``DMA_TCD0_SADDR`` …
``DMA_TCD15_SADDR``, ``CAN0_RAMn0`` … ``CAN0_RAMn127``). The datasheet documents
the array ONCE, so the generator extracts some instances and drops others
(retrieval/batch misses a given index). The dropped instances are structurally
identical to their produced siblings — same fields, size, reset — differing only
by a constant address stride.

This pass fills an absent instance ``{prefix}{N}{suffix}`` by cloning the nearest
produced sibling ``{prefix}{M}{suffix}`` (its datasheet-extracted subfields / size
/ reset_value) and computing ``address_offset = off(M) + (N-M)*stride``, where the
stride is derived from the produced siblings' OWN offsets (datasheet-grounded — the
SVD is used only to enumerate which instances exist, never for a value). Instances
with <2 produced siblings carrying an offset get the cloned structure with a null
offset (never a fabricated one). Cloned files carry ``"provenance":"array_clone"``
and NO constraints (constraints are not duplicated across instances).

Not run: scatter misses with no produced sibling (a whole array the generator never
emitted, or a one-off batch failure) — those need a re-run, not a clone.
"""
from __future__ import annotations
import glob
import json
import os
import re

from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral

__all__ = ["fill_run"]


def _nn(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _split(filename: str):
    p, _, r = filename.partition("_")
    return p, r


def _array_key(peripheral: str, register: str):
    """(peripheral, pattern) with the FIRST digit-run in the register blanked, +
    the index. ``tcd8_saddr`` -> (('dma','tcd#_saddr'), 8)."""
    m = re.search(r"\d+", register)
    if not m:
        return None, None
    pattern = register[:m.start()] + "#" + register[m.end():]
    return (peripheral.lower(), pattern.lower()), int(m.group())


def _hx(v):
    try:
        return int(str(v).replace(" ", "").replace("_", ""), 16)
    except (ValueError, AttributeError):
        return None


def _stride(pairs):
    """pairs: list of (index, offset_int) from produced siblings. Return a stride
    consistent across all pairs, else None."""
    pts = sorted((i, o) for i, o in pairs if o is not None)
    if len(pts) < 2:
        return None, None
    (i0, o0), (i1, o1) = pts[0], pts[-1]
    if i1 == i0:
        return None, None
    stride, rem = divmod(o1 - o0, i1 - i0)
    if rem != 0:
        return None, None
    # verify every point fits o0 + (i-i0)*stride
    for i, o in pts:
        if o != o0 + (i - i0) * stride:
            return None, None
    return (i0, o0), stride


def fill_run(agent_output_dir: str, device_dir: str) -> dict:
    """Clone absent array instances from produced siblings. Returns stats.
    ``device_dir`` supplies the SVD(s) for register ENUMERATION only."""
    svds = sorted(glob.glob(os.path.join(device_dir, "svd", "*.svd"))
                  + glob.glob(os.path.join(device_dir, "svd", "*.xml")))
    if not svds:
        return {"error": f"no SVDs in {device_dir}", "filled": 0}

    produced = {}  # norm(filename) -> (filename, data)
    for f in glob.glob(os.path.join(agent_output_dir, "*")):
        if os.path.isdir(f) or "_" not in os.path.basename(f):
            continue
        try:
            d = json.loads(open(f).read())
        except Exception:
            continue
        if isinstance(d, dict):
            produced[_nn(os.path.basename(f))] = (os.path.basename(f), d)

    # Group produced array instances by (peripheral, pattern).
    siblings: dict = {}
    for norm, (fn, data) in produced.items():
        per, reg = _split(fn)
        ak, idx = _array_key(per, reg)
        if ak is None:
            continue
        siblings.setdefault(ak, {})[idx] = (fn, data, reg)

    # Expected instances the generator enumerated (names only).
    expected = {}  # norm -> (peripheral, register)
    for p in get_peripheral_names(svds):
        try:
            for r in get_register_names_for_peripheral(svds, p):
                expected[_nn(f"{p}_{r}")] = (p, r)
        except ValueError:
            pass

    filled = filled_with_offset = 0
    for norm, (p, r) in expected.items():
        if norm in produced:
            continue
        ak, idx = _array_key(p, r)
        if ak is None or ak not in siblings:
            continue
        pool = siblings[ak]
        # nearest produced sibling by index distance (for structure)
        base_idx = min(pool, key=lambda m: abs(m - idx))
        _, base_data, _ = pool[base_idx]
        clone = {
            "datasheet_register_abbreviation": f"{p}_{r}".upper(),
            "address_offset": None,
            "reset_value": base_data.get("reset_value"),
            "size": base_data.get("size"),
            "subfields": base_data.get("subfields") or [],
            "access_constraints_v2": [],
            "provenance": "array_clone",
            "array_cloned_from": pool[base_idx][0],
        }
        anchor, stride = _stride([(m, _hx(pool[m][1].get("address_offset"))) for m in pool])
        if anchor is not None and stride is not None:
            i0, o0 = anchor
            clone["address_offset"] = hex(o0 + (idx - i0) * stride)
            filled_with_offset += 1
        with open(os.path.join(agent_output_dir, f"{p}_{r}"), "w") as fh:
            json.dump(clone, fh)
        filled += 1

    return {"filled": filled, "filled_with_offset": filled_with_offset,
            "array_groups": len(siblings)}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_output_dir")
    ap.add_argument("device_dir")
    print(json.dumps(fill_run(ap.parse_args().agent_output_dir, ap.parse_args().device_dir), indent=2))
