"""Per-device extraction discovery: structure coverage + constraint funnel +
residual-gap breakdown + group-aware recommendations.

Standalone. Structure coverage is measured against the generator's OWN register
enumeration (``agent_tools.svd_parsing.get_register_names_for_peripheral``, the
exact names it writes files under) — NOT a second hand-rolled SVD walk, which
mis-keyed cluster/array registers (``FTFE_FlashConfig_BACKKEY0`` vs the generator's
``ftfe_flashconfig_backkey0``) and inflated "absent" ~3x. "Expected" = what the
generator was asked to produce; "absent" = expected minus files actually written.

    python3 scripts/device_discovery.py <device> [--manufacturer nxp] [--run 1]
"""
from __future__ import annotations
import argparse, csv, glob, json, os, re, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral

FORMAT_GROUP = {
    "lpc845": "C (classic LPC)", "k32l3a": "A (modern Kinetis)",
    "s32k1xx": "A (modern Kinetis)", "ke04": "B (classic Kinetis)",
    "ke04_old": "B", "k64": "B (classic Kinetis)", "mk20d7": "B (classic Kinetis)",
    "mk20d5": "B", "lpc55s69": "D (modern NXP, caption offset)",
    "mimxrt685s": "D (modern NXP, caption offset)", "mimxrt633s": "D",
}


def _nn(s): return re.sub(r"[^A-Z0-9]", "", (s or "").upper())
def _empty(v): return v is None or (isinstance(v, str) and not v.strip()) or v == 0
def _digit_tail(s): return bool(re.search(r"\d$", s or ""))


def expected_registers(dev_dir):
    """The exact register filenames the generator enumerates (keyed normalized)."""
    svds = glob.glob(os.path.join(dev_dir, "svd", "*.svd")) + glob.glob(os.path.join(dev_dir, "svd", "*.xml"))
    exp = {}
    for p in get_peripheral_names(svds):
        try:
            for r in get_register_names_for_peripheral(svds, p):
                exp[_nn(f"{p}_{r}")] = f"{p}_{r}"
        except ValueError:
            pass
    return exp


def load_produced(ao_dir):
    out = {}
    for f in glob.glob(os.path.join(ao_dir, "*")):
        if os.path.isdir(f) or "_" not in os.path.basename(f):
            continue
        try:
            d = json.loads(open(f).read())
        except Exception:
            continue
        if isinstance(d, dict):
            out[_nn(os.path.basename(f))] = d
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

    produced = load_produced(ao_dir)
    if not produced:
        print(f"  NO generator output at {ao_dir} — run s0 first.")
        return
    expected = expected_registers(dev_dir)
    matched = [k for k, v in expected.items() if k in produced]
    absent = sorted(v for k, v in expected.items() if k not in produced)
    m = max(len(matched), 1)
    ao = sum(1 for k in matched if not _empty(produced[k].get("address_offset")))
    rv = sum(1 for k in matched if not _empty(produced[k].get("reset_value")))
    sz = sum(1 for k in matched if not _empty(produced[k].get("size")))
    print(f"\n-- STRUCTURE COVERAGE (vs generator's own SVD enumeration) --")
    print(f"  expected registers: {len(expected)} | produced+matched: {len(matched)} "
          f"({100*len(matched)//max(len(expected),1)}%) | absent: {len(absent)}")
    print(f"  address_offset: {ao}/{m} = {100*ao//m}%")
    print(f"  reset_value   : {rv}/{m} = {100*rv//m}%")
    print(f"  size          : {sz}/{m} = {100*sz//m}%")
    arr = [x for x in absent if _digit_tail(x)]
    print(f"  absent: {len(absent)} | array-indexed (ends in digit): {len(arr)}")
    if absent[:8]:
        print(f"    sample: {absent[:8]}")

    # constraint funnel
    print(f"\n-- CONSTRAINT FUNNEL --")
    raw = 0
    from collections import Counter
    kinds = Counter()
    for d in produced.values():
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

    rv_path = os.path.join(ev_dir, f"{dev}_structure_review.csv")
    if os.path.isfile(rv_path):
        rows = list(csv.DictReader(open(rv_path)))
        print(f"\n-- STRUCTURE REVIEW --  rows={len(rows)}")
        print(f"  by key: {dict(Counter(r.get('key','') for r in rows))}")
        print(f"  by status: {dict(Counter(r.get('status','') for r in rows))}")
    cr_path = os.path.join(ev_dir, f"{dev}_constraints_review.jsonl")
    if os.path.isfile(cr_path):
        print(f"  constraints_review records: {sum(1 for _ in open(cr_path))}")


if __name__ == "__main__":
    main()
