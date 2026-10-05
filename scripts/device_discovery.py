"""Per-device extraction discovery: structure coverage + constraint funnel +
residual-gap breakdown + group-aware recommendations.

Standalone (no config/LLM import): reads the generator output, the review CSV, and
the constraint_validation artifacts for a device, and compares structure against
the SVD ground truth. Run after a device's s0 pipeline completes.

    python3 scripts/device_discovery.py <device> [--manufacturer nxp] [--run 1]
"""
from __future__ import annotations
import argparse, csv, glob, json, os, re
import xml.etree.ElementTree as ET
from collections import Counter

FORMAT_GROUP = {
    "lpc845": "C (classic LPC: summary table, relative offset, no size col)",
    "k32l3a": "A (modern Kinetis: summary table, relative offset, has Width)",
    "s32k1xx": "A (modern Kinetis: summary table, relative offset, has Width)",
    "ke04": "B (classic Kinetis: summary table, ABSOLUTE addr, Label(NAME), Width)",
    "ke04_old": "B (classic Kinetis)",
    "k64": "B (classic Kinetis: summary table, ABSOLUTE addr, Label(NAME), Width)",
    "mk20d7": "B (classic Kinetis)",
    "mk20d5": "B (classic Kinetis)",
    "lpc55s69": "D (modern NXP: caption offset, no summary table)",
    "mimxrt685s": "D (modern NXP: caption offset, no summary table)",
    "mimxrt633s": "D (modern NXP: caption offset, no summary table)",
}


def _sns(t): return t.rsplit("}", 1)[-1]
def _nn(s): return re.sub(r"[^A-Z0-9]", "", (s or "").upper())
def _hx(v):
    try: return int(str(v).replace(" ", "").replace("_", ""), 16)
    except Exception: return None
def _digit_tail(s): return bool(re.search(r"\d$", s or ""))


def load_svd(dev_dir):
    out = {}
    for s in glob.glob(os.path.join(dev_dir, "svd", "*.svd")) + glob.glob(os.path.join(dev_dir, "svd", "*.xml")):
        for per in ET.parse(s).getroot().iter():
            if _sns(per.tag) != "peripheral":
                continue
            pn = next((c.text for c in per if _sns(c.tag) == "name"), None)
            if not pn:
                continue
            for reg in per.iter():
                if _sns(reg.tag) != "register":
                    continue
                rn = ro = rr = None
                for c in reg:
                    t = _sns(c.tag)
                    if t == "name": rn = c.text
                    elif t == "addressOffset": ro = c.text
                    elif t == "resetValue": rr = c.text
                if rn:
                    out[(_nn(pn).rstrip("0123456789"), _nn(rn))] = {"peripheral": pn, "register": rn,
                                                                     "address_offset": ro, "reset_value": rr}
    return out


def load_gen(ao_dir):
    out = {}
    for f in glob.glob(os.path.join(ao_dir, "*")):
        if os.path.isdir(f):
            continue
        n = os.path.basename(f)
        if "_" not in n:
            continue
        try:
            d = json.loads(open(f).read())
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        per, reg = n.split("_", 1)
        out[(_nn(per).rstrip("0123456789"), _nn(reg))] = (n, d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device")
    ap.add_argument("--manufacturer", default="nxp")
    ap.add_argument("--run", default="1")
    a = ap.parse_args()
    dev, mfr, run = a.device, a.manufacturer, a.run
    dev_dir = os.path.join("devices", mfr, dev)
    ao_dir = os.path.join("agent_output", mfr, dev, run)
    ev_dir = os.path.join("evaluation", mfr, dev, run)

    print(f"{'='*72}\nDISCOVERY: {dev}  (group {FORMAT_GROUP.get(dev,'?')})\n{'='*72}")

    svd = load_svd(dev_dir)
    gen = load_gen(ao_dir)
    if not gen:
        print(f"  NO generator output at {ao_dir} — run s0 first.")
        return
    matched = [k for k in svd if k in gen]
    has_off = sum(1 for k in matched if gen[k][1].get("address_offset") not in (None, ""))
    has_rst = sum(1 for k in matched if gen[k][1].get("reset_value") not in (None, ""))
    has_sz = sum(1 for k in matched if gen[k][1].get("size") not in (None, "", 0))
    absent = [svd[k] for k in svd if k not in gen]
    m = max(len(matched), 1)
    print(f"\n-- STRUCTURE COVERAGE (vs SVD) --")
    print(f"  SVD registers: {len(svd)} | matched in generator: {len(matched)} | absent: {len(absent)}")
    print(f"  address_offset: {has_off}/{m} = {100*has_off//m}%")
    print(f"  reset_value   : {has_rst}/{m} = {100*has_rst//m}%")
    print(f"  size          : {has_sz}/{m} = {100*has_sz//m}%")

    # residual missing offset: array vs name-variant
    miss_off = [svd[k] for k in matched_keys(svd, gen) if gen[k][1].get("address_offset") in (None, "")]
    arr = [x for x in miss_off if _digit_tail(x["register"])]
    print(f"  missing offset (matched): {len(miss_off)} | array-indexed names: {len(arr)} | absent regs: {len(absent)}")
    if absent[:8]:
        print(f"    absent sample: {[a['peripheral']+'_'+a['register'] for a in absent[:8]]}")

    # constraint funnel
    print(f"\n-- CONSTRAINT FUNNEL --")
    raw = 0
    kinds = Counter()
    for _, d in gen.values():
        for c in (d.get("access_constraints_v2") or []):
            raw += 1
            kinds[c.get("kind")] += 1
    print(f"  raw extracted (agent_output): {raw}  kinds={dict(kinds)}")
    cvs = os.path.join(ao_dir, "constraint_validation", "summary.json")
    if os.path.isfile(cvs):
        s = json.load(open(cvs))
        print(f"  pipeline funnel: extracted={s.get('extracted')} anchored={s.get('anchored')} "
              f"static_pass={s.get('static_pass')} confirmed={s.get('confirmed')} "
              f"enforce={s.get('enforce')} drop={s.get('drop')}")
    man = os.path.join(ao_dir, "constraint_validation", "manifest.json")
    if os.path.isfile(man):
        sm = json.load(open(man)).get("summary", {})
        print(f"  collect: native_v2={sm.get('constraints_native_v2')} survived_lint={sm.get('constraints_v2')} "
              f"rejected={sm.get('constraints_rejected')} reasons={sm.get('reject_reasons')}")

    # structure review
    rv = os.path.join(ev_dir, f"{dev}_structure_review.csv")
    if os.path.isfile(rv):
        rows = list(csv.DictReader(open(rv)))
        print(f"\n-- STRUCTURE REVIEW --  rows={len(rows)}")
        print(f"  by key: {dict(Counter(r.get('key','') for r in rows))}")
        print(f"  by status: {dict(Counter(r.get('status','') for r in rows))}")

    cr = os.path.join(ev_dir, f"{dev}_constraints_review.jsonl")
    if os.path.isfile(cr):
        n = sum(1 for _ in open(cr))
        print(f"  constraints_review records: {n}")


def matched_keys(svd, gen):
    return [k for k in svd if k in gen]


if __name__ == "__main__":
    main()
