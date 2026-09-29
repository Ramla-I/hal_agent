#!/usr/bin/env python3
"""Re-score the evolved-pipeline output crediting BIT-POSITION subfield matches
(the reconciliation logic from scripts/stm_coverage_statistics.py), to remove the
array-granularity artifact: the model emits one collapsed field (e.g. EXTI `MRx[17:0]`)
where the verified datasheet enumerates 18 (`mr0..mr17`). Strict scoring counts the
18 as missing; here a verified subfield fact (bit_offset / bit_width / access) is
credited if SOME generator subfield's [start,end] bit range covers that field's bit
(and, for `access`, the covering field's access matches).

Register-level facts (address_offset / size / reset_value) are UNCHANGED — the
collapse artifact only touches subfields. We also separately report how many of the
strict "wrong" facts are pure representation (e.g. size 0x20 vs 32).

Reads only: verified CSV + register_info/ + analysis/generator_comparison_fact_errors.csv.
Writes nothing. Run:  python oneoff_evolved_rm0041/rescore_bitpos.py
"""
import csv, json, os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _repo_root(start):
    """Walk up until we find the repo (marked by verified_datasheet/), so this runs
    regardless of where the folder is checked out."""
    for d in [start, *start.parents]:
        if (d / "verified_datasheet/stm/rm0041_stm32f100.csv").exists():
            return d
    raise SystemExit("could not locate repo root (verified_datasheet/) above " + str(start))


VERIFIED = _repo_root(HERE) / "verified_datasheet/stm/rm0041_stm32f100.csv"
REGDIR = HERE / "register_info"                                  # final run (enum-free + name-fix)
ERRORS = HERE / "analysis/generator_comparison_fact_errors.csv"

# strict totals from analysis/generator_comparison.csv (the summary row)
STRICT = dict(correct=2506, wrong=57, missing=793, total=3356)


def _pint(s):
    try:
        return int(str(s), 0)
    except (TypeError, ValueError):
        return None


def _norm_access(a):
    return (a or "").strip().lower().replace("_", "-")


# --- verified: per (peripheral, register, field) -> {bit_offset, access} ---
vfield = {}   # (p,r,f) -> dict
with open(VERIFIED) as f:
    for row in csv.DictReader(f):
        cv = row["correct_value"].strip()
        if not cv:
            continue
        p, r, fn, key = row["peripheral"], row["register"], row["field_name"], row["key"]
        if not fn:
            continue
        vfield.setdefault((p, r, fn), {})[key] = cv

# --- generator: per (peripheral, register) -> list of (lo, hi, access) covered ranges ---
gen_ranges = {}
for fname in os.listdir(REGDIR):
    try:
        data = json.loads((REGDIR / fname).read_text())
    except Exception:
        continue
    if not isinstance(data, dict):
        continue
    ranges = []
    for sf in data.get("subfields", []) or []:
        bn = sf.get("bit_number") or {}
        s, e = _pint(bn.get("start_bit")), _pint(bn.get("end_bit"))
        if s is None or e is None:
            continue
        lo, hi = min(s, e), max(s, e)
        ranges.append((lo, hi, _norm_access(sf.get("access"))))
    gen_ranges[fname] = ranges   # filename == f"{peripheral}_{register}"


def covered(p, r, fn, key):
    """Is this missing subfield fact actually covered by a collapsed generator field?"""
    v = vfield.get((p, r, fn), {})
    bit = _pint(v.get("bit_offset"))
    if bit is None:
        return False
    ranges = gen_ranges.get(f"{p}_{r}")
    if not ranges:
        return False
    for lo, hi, acc in ranges:
        if lo <= bit <= hi:
            if key == "access":
                return _norm_access(v.get("access")) == acc  # access must match
            return True   # bit_offset / bit_width: positional coverage is enough
    return False


# --- walk the strict error list and reclassify ---
reclaimed = 0                 # missing subfield facts now credited by bit position
repr_wrong = 0                # "wrong" facts that are pure representation (value-equal)
reclaimed_by_periph = {}
with open(ERRORS) as f:
    for row in csv.DictReader(f):
        et, p, r, fn, key = (row["error_type"], row["peripheral"], row["register"],
                             row["field_name"], row["key"])
        cv, gv = row["correct_value"].strip(), row["generated_value"].strip()
        if et == "wrong":
            if _pint(cv) is not None and _pint(cv) == _pint(gv):   # e.g. 0x20 == 32
                repr_wrong += 1
            continue
        if et == "missing" and fn and key in ("bit_offset", "bit_width", "access"):
            if covered(p, r, fn, key):
                reclaimed += 1
                reclaimed_by_periph[p] = reclaimed_by_periph.get(p, 0) + 1

# --- recompute ---
tot = STRICT["total"]
strict_correct = STRICT["correct"]
recon_correct = strict_correct + reclaimed
strict_ca = 100 * strict_correct / tot
recon_ca = 100 * recon_correct / tot
# also credit the representation-"wrong" as correct (they are value-equal)
recon_correct_plus = recon_correct + repr_wrong
recon_ca_plus = 100 * recon_correct_plus / tot

print("=== re-scoring the evolved pipeline (enum-free + name-reconciled run) ===\n")
print(f"strict complete accuracy:                 {strict_correct}/{tot} = {strict_ca:.1f}%")
print(f"  + bit-position subfield credit (+{reclaimed}):  {recon_correct}/{tot} = {recon_ca:.1f}%")
print(f"  + representation 'wrong' credit  (+{repr_wrong}):  {recon_correct_plus}/{tot} = {recon_ca_plus:.1f}%")
print(f"\nof the strict {STRICT['missing']} 'missing' facts, {reclaimed} were actually covered "
      f"by a collapsed generator field ({100*reclaimed/STRICT['missing']:.0f}%).")
print(f"of the strict {STRICT['wrong']} 'wrong' facts, {repr_wrong} are pure representation "
      f"(e.g. size 0x20 vs 32).")
print("\nbit-position credit by peripheral (top):")
for p in sorted(reclaimed_by_periph, key=lambda k: -reclaimed_by_periph[k])[:10]:
    print(f"  {p:10s} +{reclaimed_by_periph[p]}")
