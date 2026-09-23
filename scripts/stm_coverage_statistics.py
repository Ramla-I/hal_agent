#!/usr/bin/env python3
"""SVD-vs-generator coverage statistics for the STM manuals.

Answers, per attribute category and in aggregate:
  * how many facts the SVD carries that the generator did NOT produce (svd_only),
    split by whether the fact's peripheral produced any generator output at all;
  * how many facts the generator produced that the SVD has no counterpart for
    (gen_only);
plus a register-level coverage summary and a subfield-coverage summary for
registers present on both sides.

This is SEPARATE from stm_structure_statistics.py (the disagreement funnel):
coverage compares the generator's output against the SVD directly and does not
read the review CSVs.

Name reconciliation (applied HERE ONLY, not in the pipeline -- see issue #24):
  * peripherals are matched by longest-prefix against the real SVD peripheral
    names, so underscore-named peripherals (OTG_FS_GLOBAL, ETHERNET_MAC, ...)
    line up instead of being split on the first '_';
  * SVD <dim> arrays are expanded (registers DR%s -> dr1..drN, and dim fields),
    so they match the generator's concrete names;
  * SUBFIELDS are matched by BIT POSITION (start bit), not by name -- so
    `cnf%s`/`exti1` vs the generator's `cnf0`/`exti1[3:0]` count as the same
    field. Matching by name badly understates subfield coverage (~half of the
    apparent misses are pure naming differences).

These reconciliations live only in this analysis script; the pipeline's diff
still uses the naive matching (issue #24), so its numbers differ.

Usage:
    python scripts/stm_coverage_statistics.py --exclude access
    python scripts/stm_coverage_statistics.py --by-rm
    python scripts/stm_coverage_statistics.py --exclude access --csv cov.csv
"""
import argparse
import collections
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PHASE1D = Path(__file__).resolve().parent.parent

# review key -> (level, generator-JSON attribute). bit_offset and bit_width both
# derive from one bit_number object; both are matched by bit position here.
REVIEW_TO_GENERATOR = {
    "address_offset": ("register", "address_offset"),
    "size":           ("register", "size"),
    "reset_value":    ("register", "reset_value"),
    "bit_offset":     ("field",    "bit_number"),
    "bit_width":      ("field",    "bit_number"),
    "access":         ("field",    "access"),
}


def _pint(s):
    try:
        return int(str(s), 0)
    except (ValueError, TypeError):
        return None


def _dim_tokens(di, dim):
    di = (di or "").strip()
    if not di:
        return [str(i) for i in range(dim)]
    if "-" in di and "," not in di:
        a, b = di.split("-", 1)
        ai, bi = _pint(a), _pint(b)
        if ai is not None and bi is not None:
            return [str(i) for i in range(ai, bi + 1)]
    return [t.strip() for t in di.split(",")]


def _expand(nm, dim, di):
    """Expand a <dim> name (DR%s / DR[%s] / DR) into concrete lowercase names."""
    if not dim:
        return [nm]
    out = []
    for t in _dim_tokens(di, dim):
        if "[%s]" in nm:
            out.append(nm.replace("[%s]", t))
        elif "%s" in nm:
            out.append(nm.replace("%s", t))
        else:
            out.append(nm + t)
    return out


def _field_lsb(f):
    """Lowest bit of an SVD field, from bitOffset / lsb / bitRange."""
    bo = _pint(f.findtext("bitOffset"))
    if bo is not None:
        return bo
    lsb = _pint(f.findtext("lsb"))
    if lsb is not None:
        return lsb
    m = re.match(r"\[(\d+):(\d+)\]", (f.findtext("bitRange") or "").strip())
    if m:
        return int(m.group(2))
    return None


def _gen_lsb(sf):
    bn = sf.get("bit_number") or {}
    s, e = bn.get("start_bit"), bn.get("end_bit")
    if s is None:
        return None
    return min(s, e) if e is not None else s


def _field_msb(f):
    """Highest bit of an SVD field, from bitOffset+bitWidth / msb / bitRange."""
    bo = _pint(f.findtext("bitOffset")); bw = _pint(f.findtext("bitWidth"))
    if bo is not None:
        return bo + (bw or 1) - 1
    lsb = _pint(f.findtext("lsb")); msb = _pint(f.findtext("msb"))
    if lsb is not None and msb is not None:
        return max(lsb, msb)
    mm = re.match(r"\[(\d+):(\d+)\]", (f.findtext("bitRange") or "").strip())
    if mm:
        return int(mm.group(1))
    return None


def _norm_name(n):
    """Generator field names carry a trailing [x:y]; strip it for name comparison."""
    return re.sub(r"\[[^\]]*\]$", "", (n or "").lower())


def coverage_counts(rm, root, keys):
    """SVD-vs-generator coverage for one manual (name reconciliation applied).

    Returns (svd_only, svd_found, svd_absent, gen_only, regcov, subf). Field
    categories are matched by bit position; registers by reconciled name.
    """
    svd_only = collections.Counter()
    svd_found = collections.Counter()
    svd_absent = collections.Counter()
    gen_only = collections.Counter()
    regcov = {"total": set(), "covered": set(),
              "missed_found": set(), "missed_absent": set()}
    subf = collections.Counter()
    svds = list((root / "devices" / "stm" / rm / "svd").glob("*.svd"))
    gens = list((root / "agent_output" / "stm" / rm / "1").glob("*"))
    if not svds or not gens:
        return svd_only, svd_found, svd_absent, gen_only, regcov, subf

    # ---- SVD side: reconciled register names + per-register field bit positions.
    reg_attr = {}                                   # (per,reg) -> {attr: True}
    svd_lsbs = collections.defaultdict(set)         # (per,reg) -> {start bits}
    svd_lsbs_acc = collections.defaultdict(set)     # ... with access defined
    svd_names = collections.defaultdict(lambda: collections.defaultdict(set))  # (per,reg) -> lsb -> {names}
    svd_ranges = collections.defaultdict(set)       # (per,reg) -> {(lsb,msb)}
    peris_set = set()
    for s in svds:
        try:
            el = ET.parse(s).getroot()
        except ET.ParseError as e:
            print(f"!! WARNING: unparseable SVD skipped: {s} ({e}) -- its registers "
                  f"are absent from coverage", file=sys.stderr)
            continue
        peris = {(pe.findtext("name") or "").lower(): pe
                 for pe in el.iter("peripheral") if pe.findtext("name")}
        peris_set |= set(peris)
        for n, pe in peris.items():
            src = peris.get((pe.get("derivedFrom") or "").lower(), pe)
            for r in src.iter("register"):
                rn = (r.findtext("name") or "").lower()
                if not rn:
                    continue
                rnames = _expand(rn, _pint(r.findtext("dim")), r.findtext("dimIndex"))
                lsbs, lsbs_acc = set(), set()
                fnames = collections.defaultdict(set)   # lsb -> names (this register)
                franges = set()                          # (lsb, msb)
                for f in r.iter("field"):
                    lsb = _field_lsb(f); msb = _field_msb(f)
                    if lsb is None:
                        continue
                    if msb is None or msb < lsb:
                        msb = lsb
                    fn = (f.findtext("name") or "").lower()
                    fdim = _pint(f.findtext("dim"))
                    if fdim:
                        inc = _pint(f.findtext("dimIncrement")) or 1
                        toks = _dim_tokens(f.findtext("dimIndex"), fdim)
                        insts = []
                        for i, t in enumerate(toks):
                            nm = (fn.replace("[%s]", t) if "[%s]" in fn
                                  else fn.replace("%s", t) if "%s" in fn
                                  else fn + t) if fn else ""
                            insts.append((lsb + i * inc, msb + i * inc, nm))
                    else:
                        insts = [(lsb, msb, fn)]
                    has_acc = f.findtext("access") is not None
                    for il, im, nm in insts:
                        lsbs.add(il); franges.add((il, im))
                        if nm:
                            fnames[il].add(nm)
                        if has_acc:
                            lsbs_acc.add(il)
                for rnm in rnames:
                    key = (n, rnm)
                    a = reg_attr.setdefault(key, {})
                    if r.findtext("addressOffset") is not None:
                        a["address_offset"] = True
                    if r.findtext("size") is not None:
                        a["size"] = True
                    if r.findtext("resetValue") is not None:
                        a["reset_value"] = True
                    svd_lsbs[key] |= lsbs
                    svd_lsbs_acc[key] |= lsbs_acc
                    svd_ranges[key] |= franges
                    for il, nms in fnames.items():
                        svd_names[key][il] |= nms

    # ---- generator side: longest-prefix peripheral match + field bit positions.
    gen_valid = {}
    gen_lsbs = collections.defaultdict(set)
    gen_lsbs_acc = collections.defaultdict(set)
    gen_names = collections.defaultdict(lambda: collections.defaultdict(set))  # (per,reg) -> lsb -> {names}
    gen_ranges = collections.defaultdict(set)       # (per,reg) -> {(lsb,end)}
    gen_peris = set()
    for g in gens:
        name = os.path.basename(g).lower()
        if os.path.isdir(g) or "_" not in name:
            continue
        cand = [p for p in peris_set if name.startswith(p + "_")]
        if cand:
            per = max(cand, key=len)
            reg = name[len(per) + 1:]
        else:
            per, _, reg = name.partition("_")
        try:
            d = json.loads(Path(g).read_text())
        except (OSError, json.JSONDecodeError):
            continue
        gen_peris.add(per)
        gen_valid[(per, reg)] = d
        for sf in d.get("subfields") or []:
            lsb = _gen_lsb(sf)
            if lsb is None:
                continue
            bn = sf.get("bit_number") or {}
            e0 = bn.get("end_bit")
            gen_lsbs[(per, reg)].add(lsb)
            gen_ranges[(per, reg)].add((lsb, max(lsb, e0) if e0 is not None else lsb))
            nm = _norm_name(sf.get("name"))
            if nm:
                gen_names[(per, reg)][lsb].add(nm)
            if sf.get("access") is not None:
                gen_lsbs_acc[(per, reg)].add(lsb)

    reg_keys = [k for k in keys if REVIEW_TO_GENERATOR.get(k, ("", ""))[0] == "register"]
    fld_keys = [k for k in keys if REVIEW_TO_GENERATOR.get(k, ("", ""))[0] == "field"]

    # ---- register-level coverage (fields excluded) + shared-register subfields.
    for key in reg_attr:
        regcov["total"].add(key)
        if key in gen_valid:
            regcov["covered"].add(key)
            s, gg = svd_lsbs.get(key, set()), gen_lsbs.get(key, set())
            subf["shared_regs"] += 1
            subf["svd_total"] += len(s)
            subf["matched"] += len(s & gg)
            subf["svd_extra"] += len(s - gg)   # SVD subfields the generator omitted
            subf["gen_extra"] += len(gg - s)   # generator subfields not in the SVD
            # three-way split of each bucket (name / boundary / genuine).
            sn, gn = svd_names.get(key, {}), gen_names.get(key, {})
            sr, grg = svd_ranges.get(key, set()), gen_ranges.get(key, set())
            gen_bits = set()
            for a, b in grg:
                gen_bits.update(range(a, b + 1))
            svd_bits = set()
            for a, b in sr:
                svd_bits.update(range(a, b + 1))
            svd_msb = {}
            for a, b in sr:
                svd_msb[a] = max(svd_msb.get(a, a), b)
            for lsb in s & gg:                                  # matched by start bit
                if sn.get(lsb, set()) & gn.get(lsb, set()):
                    subf["matched_exact"] += 1
                else:
                    subf["matched_reconciled"] += 1
            for lsb in s - gg:                                  # SVD-only start bit
                if lsb in gen_bits:
                    subf["svd_boundary"] += 1
                    hi = svd_msb.get(lsb, lsb)
                    if all(x in gen_bits for x in range(lsb, hi + 1)):
                        subf["svd_boundary_full"] += 1
                else:
                    subf["svd_missing"] += 1
            for lsb in gg - s:                                  # generator-only start bit
                if lsb in svd_bits:
                    subf["gen_boundary"] += 1
                else:
                    subf["gen_reserved"] += 1
        elif key[0] in gen_peris:
            regcov["missed_found"].add(key)
        else:
            regcov["missed_absent"].add(key)

    def bump(k, per):
        svd_only[k] += 1
        (svd_found if per in gen_peris else svd_absent)[k] += 1

    # ---- svd_only: SVD facts with no generator counterpart.
    for key, attrs in reg_attr.items():
        d = gen_valid.get(key)
        for k in reg_keys:
            attr = REVIEW_TO_GENERATOR[k][1]
            if attr in attrs and (d is None or d.get(attr) is None):
                bump(k, key[0])
        glsb, glsb_acc = gen_lsbs.get(key, set()), gen_lsbs_acc.get(key, set())
        for lsb in svd_lsbs.get(key, set()):
            for k in fld_keys:
                if k == "access":
                    if lsb in svd_lsbs_acc.get(key, set()) and lsb not in glsb_acc:
                        bump(k, key[0])
                elif lsb not in glsb:
                    bump(k, key[0])

    # ---- gen_only: generator facts with no SVD counterpart.
    for key, d in gen_valid.items():
        in_svd = key in reg_attr
        for k in reg_keys:
            attr = REVIEW_TO_GENERATOR[k][1]
            if d.get(attr) is not None and not in_svd:
                gen_only[k] += 1
        slsb, slsb_acc = svd_lsbs.get(key, set()), svd_lsbs_acc.get(key, set())
        for lsb in gen_lsbs.get(key, set()):
            for k in fld_keys:
                if k == "access":
                    if lsb in gen_lsbs_acc.get(key, set()) and lsb not in slsb_acc:
                        gen_only[k] += 1
                elif lsb not in slsb:
                    gen_only[k] += 1

    return svd_only, svd_found, svd_absent, gen_only, regcov, subf


def collect(root, exclude=()):
    """Aggregate coverage across every STM manual with a run under evaluation/."""
    keys = [k for k in REVIEW_TO_GENERATOR if k not in exclude]
    per_rm = {}
    svd_only = collections.Counter()
    svd_found = collections.Counter()
    svd_absent = collections.Counter()
    gen_only = collections.Counter()
    subf_total = collections.Counter()
    regcov_by_rm = {}
    rms = sorted({p.parent.name for p in root.glob("evaluation/stm/*/1") if p.is_dir()})
    for rm in rms:
        so, sf, sa, go, rc, subf = coverage_counts(rm, root, keys)
        if not (so or go or rc["total"]):
            continue
        per_rm[rm] = (so, sf, sa, go, rc, subf)
        for k in keys:
            svd_only[k] += so[k]
            svd_found[k] += sf[k]
            svd_absent[k] += sa[k]
            gen_only[k] += go[k]
        subf_total.update(subf)
        regcov_by_rm[rm] = rc
    return {"keys": keys, "per_rm": per_rm,
            "svd_only": svd_only, "svd_found": svd_found, "svd_absent": svd_absent,
            "gen_only": gen_only, "regcov": regcov_by_rm, "subf": subf_total}


def level_of(k):
    return REVIEW_TO_GENERATOR.get(k, ("?", ""))[0]


def report(cov, out_csv=None):
    keys = cov["keys"]
    so, sf, sa, go = cov["svd_only"], cov["svd_found"], cov["svd_absent"], cov["gen_only"]
    regcov = cov["regcov"]

    cats = sorted((k for k in keys if so.get(k) or go.get(k)),
                  key=lambda k: (level_of(k), -(so.get(k, 0) + go.get(k, 0))))

    print(f"{len(cov['per_rm'])} manuals  (name reconciliation applied; see issue #24)\n")
    print("SVD facts absent from the generator (svd_only), by category "
          "(split by whether\nthe peripheral produced any output), and generator "
          "facts with no SVD\ncounterpart (gen_only):\n")
    w = max((len(k) for k in cats), default=8)
    print(f"   {'category'.ljust(w)}  {'level':<8}  {'svd_only':>9}  "
          f"{'found-peri':>10}  {'absent-peri':>11}  {'gen_only':>9}")
    rows = []
    for k in cats:
        f, a = sf.get(k, 0), sa.get(k, 0)
        print(f"   {k.ljust(w)}  {level_of(k):<8}  {f + a:>9,}  "
              f"{f:>10,}  {a:>11,}  {go.get(k, 0):>9,}")
        rows.append([k, level_of(k), f + a, f, a, go.get(k, 0)])

    tot = sum(len(r["total"]) for r in regcov.values())
    if tot:
        covd = sum(len(r["covered"]) for r in regcov.values())
        mf = sum(len(r["missed_found"]) for r in regcov.values())
        ma = sum(len(r["missed_absent"]) for r in regcov.values())
        miss = mf + ma
        pct = lambda x: 100.0 * x / tot
        print("\nSVD register coverage (register-level; fields excluded, since the "
              "generator\ndoes not enumerate the SVD's field list):")
        print(f"   SVD registers:                                 {tot:>7,}")
        print(f"   covered by generator:                          {covd:>7,}  ({pct(covd):5.1f}%)")
        print(f"   NOT covered by generator:                      {miss:>7,}  ({pct(miss):5.1f}%)")
        print(f"      of that, in peripherals WITH some output:   {mf:>7,}  ({pct(mf):5.1f}%)")
        print(f"      of that, in peripherals with NO output:     {ma:>7,}  ({pct(ma):5.1f}%)")

    subf = cov["subf"]
    st = subf.get("svd_total", 0)
    if st:
        spct = lambda x: 100.0 * x / st
        g = lambda k: subf.get(k, 0)
        print("\nSubfield coverage within registers present on BOTH sides "
              "(matched by bit position):")
        print(f"   shared registers:                               {g('shared_regs'):>7,}")
        print(f"   SVD subfields in those registers:               {st:>7,}")
        print(f"   matched (start bit on both sides):              {g('matched'):>7,}  ({spct(g('matched')):5.1f}%)")
        print(f"      exact (same name + bit):                     {g('matched_exact'):>7,}")
        print(f"      name-reconciled (same bit, different name):  {g('matched_reconciled'):>7,}")
        print(f"   EXTRA in the SVD (generator omitted):           {g('svd_extra'):>7,}  ({spct(g('svd_extra')):5.1f}%)")
        print(f"      boundary diff (bits covered, split differs): {g('svd_boundary'):>7,}  ({g('svd_boundary_full'):,} fully covered)")
        print(f"      genuinely missing (no gen field at bit):     {g('svd_missing'):>7,}")
        print(f"   generator subfields not in SVD:                 {g('gen_extra'):>7,}")
        print(f"      boundary diff (bit inside an SVD field):     {g('gen_boundary'):>7,}")
        print(f"      extra detail (bit SVD leaves reserved):      {g('gen_reserved'):>7,}")

    if out_csv:
        with open(out_csv, "w", newline="") as fh:
            wr = csv.writer(fh)
            wr.writerow(["category", "level", "svd_only", "svd_only_found_peri",
                         "svd_only_absent_peri", "gen_only"])
            wr.writerows(rows)
        print(f"\ncsv: {out_csv}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(PHASE1D),
                    help="repo holding evaluation/, devices/ and agent_output/")
    ap.add_argument("--exclude", action="append", default=[], metavar="CATEGORY",
                    help="drop a category (repeatable), e.g. --exclude access")
    ap.add_argument("--by-rm", action="store_true",
                    help="also print a per-manual register-coverage table")
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    root = Path(args.root)
    if not (root / "evaluation" / "stm").is_dir():
        sys.exit(f"no evaluation/stm under {root}")
    cov = collect(root, set(args.exclude))
    if args.exclude:
        print(f'excluding: {", ".join(sorted(set(args.exclude)))}\n')
    if not cov["per_rm"]:
        sys.exit("no manuals with both SVDs and generator output found")

    if args.by_rm:
        print(f"{'rm':<10}  {'svd_regs':>9}  {'covered':>8}  {'miss_found':>10}  {'miss_absent':>11}")
        for rm in sorted(cov["regcov"]):
            r = cov["regcov"][rm]
            print(f"{rm:<10}  {len(r['total']):>9,}  {len(r['covered']):>8,}  "
                  f"{len(r['missed_found']):>10,}  {len(r['missed_absent']):>11,}")
        print()
    report(cov, args.csv)


if __name__ == "__main__":
    main()
