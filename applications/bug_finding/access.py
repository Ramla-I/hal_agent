"""Field-ACCESS diff: generator vs SVD -> a SEPARATE review file.

The structure review compares address_offset/reset_value/size + bit_offset/
bit_width, never access. The generator extracts per-field access
(BitField.access) and the SVD carries <access> (cascading field->register->
peripheral->device, parsed in diff._parse_svd_fields). This joins them and writes
ONLY the access mismatches to ``{rm}_access_review.csv`` with the SAME column
layout as the structure review, so the s6 candidate validator (which already
supports the access_type key + vendor access legend) can fill verdicts and the
interactive labeler works unchanged.

Light screen: a mismatch is dropped only when the GENERATOR access is empty/
unknown (a not-found artifact); every real read-only/read-write/write-only
disagreement is surfaced.
"""
from __future__ import annotations

import csv
import glob
import os

from .diff import parse_svd_registers, load_generator_registers

# Structure-review layout, verbatim (so the labeler + apply_verdicts match). The
# validator inserts validator_verdict/validator_confidence before tp_fp.
REVIEW_HEADER = ["RM", "peripheral", "register", "field", "key", "svd_value",
                 "generator_value", "status", "svd_count", "svd_files",
                 "tp_fp", "correct_value"]

_ACCESS_NORM = {
    "read-write": "read-write", "read-only": "read-only", "write-only": "write-only",
    "writeonce": "write-only", "read-writeonce": "read-write",
}
_NOT_FOUND = {"", "unknown", "n/a", "none", "not found", "not specified"}


def _norm(a: str) -> str:
    a = (a or "").strip().lower().replace("_", "-")
    return _ACCESS_NORM.get(a, a)


def access_diff_rows(rm: str, manufacturer: str, run: int, repo_root: str) -> list[dict]:
    """One row per (peripheral, register, field) where generator and SVD access
    disagree, deduped across the RM's SVDs (svd_files ;-joined)."""
    dev_dir = os.path.join(repo_root, "devices", manufacturer, rm)
    ao_dir = os.path.join(repo_root, "agent_output", manufacturer, rm, str(run))
    if not os.path.isdir(ao_dir):
        return []
    gen = load_generator_registers(ao_dir)

    hits: dict[tuple, dict] = {}
    for svd in sorted(glob.glob(os.path.join(dev_dir, "svd", "*.svd"))):
        stem = os.path.basename(svd).replace(".svd", "")
        for per, regs in parse_svd_registers(svd).items():
            for reg, rinfo in regs.items():
                gfields = ((gen.get(per) or {}).get(reg) or {}).get("fields") or []
                gacc = {f["name"]: _norm(f.get("access", "")) for f in gfields}
                for sf in rinfo.get("fields") or []:
                    name = sf["name"]
                    s, g = _norm(sf.get("access", "")), gacc.get(name, "")
                    if name not in gacc or g in _NOT_FOUND:      # light screen
                        continue
                    if s == g or s in _NOT_FOUND:
                        continue
                    h = hits.setdefault((per, reg, name, g), {"svd_value": s, "svds": set()})
                    h["svds"].add(stem)

    rows = [{
        "RM": rm, "peripheral": per, "register": reg, "field": field, "key": "access",
        "svd_value": h["svd_value"], "generator_value": g, "status": "",
        "svd_count": len(h["svds"]), "svd_files": ";".join(sorted(h["svds"])),
        "tp_fp": "", "correct_value": "",
    } for (per, reg, field, g), h in hits.items()]
    rows.sort(key=lambda r: (r["peripheral"], r["register"], r["field"]))
    return rows


def write_access_review(rm: str, manufacturer: str, run: int, repo_root: str) -> tuple[str, int]:
    """Write ``{rm}_access_review.csv`` (structure-review layout). Returns (path, n).
    Preserves existing reviewer tp_fp/correct_value by (peripheral,register,field)."""
    rows = access_diff_rows(rm, manufacturer, run, repo_root)
    out_dir = os.path.join(repo_root, "evaluation", manufacturer, rm, str(run))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{rm}_access_review.csv")

    prior: dict[tuple, dict] = {}
    if os.path.isfile(out):
        with open(out, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                prior[(r.get("peripheral"), r.get("register"), r.get("field"))] = r
    for r in rows:
        p = prior.get((r["peripheral"], r["register"], r["field"]))
        if p:                                   # keep human labels across regen
            r["tp_fp"] = (p.get("tp_fp") or "").strip()
            r["correct_value"] = (p.get("correct_value") or "").strip()

    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in REVIEW_HEADER})
    return out, len(rows)
