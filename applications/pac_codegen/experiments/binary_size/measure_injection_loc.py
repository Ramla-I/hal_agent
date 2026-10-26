#!/usr/bin/env python3
"""Measure how many lines the constraint injection adds to each PAC crate.

The core experiment injects **one device per reference manual** (a crate can hold
several such devices -- the stm32f4 crate serves f401/f411/f469/... from different
RMs). For every (reference manual, device, crate) target we copy the pristine
crate, run ``inject_from_run.py`` over it (field-level gating by default;
``--register-only`` for the whole-register variant), and diff against pristine.

Added lines split THREE ways:

    A  generic.rs   the witness machinery DEFINED once per crate in generic.rs:
                    the Unconstrained{Read,Write,Modify} trait decls, the
                    ``where REG: Unconstrained..`` bounds on read/write/modify/
                    reset, the witnessed accessors on ``Reg``. 255 lines, or 260
                    when the device gates a read surface (+5 = read() bound +
                    the UnconstrainedRead marker). ONE generic.rs per crate.
    B  marker walk  the ``impl crate::Unconstrained* for <REG> {}`` lines emitted
                    for EVERY register in the WHOLE crate (all device trees). They
                    exist only to satisfy A's bounds: a register WITH the impl is
                    unconstrained, one WITHOUT it is gated. Whole-crate, ~constant
                    across a crate's RMs, zero binary cost.
    C  enforcement  the ``pub mod constraints { .. }`` blocks (witnesses, gates,
                    checks, field witnesses). Land ONLY in the target device tree;
                    per-device, proportional to the constraints.

A + B is the (zero-cost) scaffolding; C is the enforcement logic. A and B are
whole-crate -> count once per crate; C is per-device -> summed. Both raw and SLOC
(non-blank/non-comment; ``#[..]`` attributes count as code) are recorded, plus the
gated-register / gated-field counts and the pristine crate size.

Writes ``injection_loc.json`` next to this script. NO cargo needed.

    python measure_injection_loc.py                # inject + measure (field-level)
    python measure_injection_loc.py --register-only

Targets from experiments/stm_sweep.py; master-only crates from vendored/pac_master.
Pipeline artifacts from the sibling hal_agent-phase-1d worktree.
"""
import argparse, glob, json, re, shutil, statistics, subprocess, sys, tempfile
from collections import defaultdict
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
REPO = APP.parents[1]
DATA = Path("/home/ramla/hal_agent-phase-1d")
INJECT = APP / "inject_from_run.py"
VEND = APP / "vendored/pac"
VEND_MASTER = APP / "vendored/pac_master"
HERE = Path(__file__).resolve().parent
READ_GATE_LINES = 5

targets = [(rm, pac, dev, VEND) for rm, pac, dev in
           re.findall(r'Target\("(\w+)",\s*"(\w+)",\s*"(\w+)",',
                      (APP/"experiments/stm_sweep.py").read_text())]
targets += [("rm0493", "stm32wba", "stm32wba55", VEND_MASTER),
            ("rm0505", "stm32wb0", "stm32wb09", VEND_MASTER),
            ("rm0529", "stm32wb0", "stm32wb05", VEND_MASTER),
            ("rm0530", "stm32wb0", "stm32wb06", VEND_MASTER)]


def is_code(s):
    s = s.strip()
    return bool(s) and not s.startswith(("//", "/*", "*/", "*"))


def file_size(path):
    """(raw, sloc) of a single file."""
    raw = sloc = 0
    for ln in open(path, errors="ignore"):
        raw += 1
        sloc += is_code(ln)
    return raw, sloc


def crate_size(root):
    """(raw, sloc) over every .rs under src/ -- the pristine crate size."""
    raw = sloc = 0
    for f in glob.glob(f"{root}/src/**/*.rs", recursive=True):
        r, s = file_size(f); raw += r; sloc += s
    return raw, sloc


def added_generic(a, b):
    """(raw, sloc) of the added lines that live in generic.rs (bucket A)."""
    r = subprocess.run(["git", "diff", "--no-index", "-U0", str(a), str(b)],
                       capture_output=True, text=True)
    raw = sloc = tot_raw = tot_sloc = 0
    generic = False
    for line in r.stdout.splitlines():
        if line.startswith("+++ "):
            generic = line[4:].endswith("/generic.rs")
        elif line.startswith(("--- ", "diff ", "index ", "@@ ", "\\")):
            continue
        elif line.startswith("+"):
            code = is_code(line[1:])
            tot_raw += 1; tot_sloc += code
            if generic:
                raw += 1; sloc += code
    return raw, sloc, tot_raw, tot_sloc


def enforcement_size(root):
    """(raw, sloc) inside every ``pub mod constraints { .. }`` block (bucket C)."""
    raw = sloc = 0
    for f in glob.glob(f"{root}/src/**/*.rs", recursive=True):
        t = open(f, errors="ignore").read()
        for m in re.finditer(r"pub mod constraints \{", t):
            i = t.index("{", m.start()); d = 0; j = i
            while j < len(t):
                if t[j] == "{": d += 1
                elif t[j] == "}":
                    d -= 1
                    if d == 0: break
                j += 1
            block = t[i:j]
            raw += block.count("\n")
            sloc += sum(is_code(ln) for ln in block.splitlines())
    return raw, sloc


def gate_counts(path):
    """From a device-constraints file: (whole-reg gated, op-surfaces, field
    accessors, registers-with-field-gates, sorted constraint ids)."""
    regs = json.load(open(path))["registers"]
    whole = sum(1 for r in regs if r.get("gated_operations"))
    opsurf = sum(len(r.get("gated_operations", [])) for r in regs)
    fld_acc = sum(len(r.get("gated_fields", {})) for r in regs)
    fld_regs = sum(1 for r in regs if r.get("gated_fields"))
    ids = set()
    for r in regs:
        ids.update(r.get("constraint_ids") or [])
    return whole, opsurf, fld_acc, fld_regs, sorted(ids)


def inject_all(register_only):
    out = []
    prist = {}
    with tempfile.TemporaryDirectory() as td:
        for rm, pac, dev, src_root in targets:
            rd = DATA / f"agent_output/stm/{rm}/1"
            val = rd / "constraint_validation/validated.jsonl"
            svd = DATA / f"devices/stm/{rm}/svd"
            src = src_root / pac
            if not (rd.exists() and val.exists() and src.exists()):
                print(f"skip {rm} {pac} {dev}: missing inputs", flush=True); continue
            if pac not in prist:
                prist[pac] = crate_size(src)
            dst = Path(td) / f"{rm}_{dev}"
            shutil.copytree(src, dst)
            gates_file = Path(td) / f"{rm}_{dev}_gates.json"
            cmd = [sys.executable, str(INJECT), str(rd), "--pac", str(dst),
                   "--device", dev, "--constraints", str(val), "--svd-dir", str(svd),
                   "--save-constraints", str(gates_file)]
            if register_only:
                cmd.append("--register-only")
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
            if r.returncode != 0:
                tail = r.stderr.strip().splitlines()[-1][:70] if r.stderr.strip() else "?"
                print(f"ERR {rm} {pac}: {tail}", flush=True); shutil.rmtree(dst); continue
            a_raw, a_sloc, t_raw, t_sloc = added_generic(src, dst)   # A + totals
            c_raw, c_sloc = enforcement_size(dst)                    # C
            b_raw, b_sloc = t_raw - a_raw - c_raw, t_sloc - a_sloc - c_sloc  # B walk
            whole, opsurf, fld_acc, fld_regs, cids = gate_counts(gates_file)
            pr, ps = prist[pac]
            out.append({"rm": rm, "pac": pac, "device": dev,
                        "total": t_raw, "sloc": t_sloc,
                        "generic_raw": a_raw, "generic_sloc": a_sloc,   # A
                        "walk_raw": b_raw, "walk_sloc": b_sloc,         # B
                        "enforce_raw": c_raw, "enforce_sloc": c_sloc,   # C
                        # legacy keys kept for gen_injection_cost_artifact.py
                        "modules": c_raw, "scaffolding": t_raw - c_raw,
                        "regs_gated": whole, "op_surfaces": opsurf,
                        "fields_gated": fld_acc, "regs_with_field_gates": fld_regs,
                        "n_constraints": len(cids), "constraint_ids": cids,
                        "pristine_raw": pr, "pristine_sloc": ps})
            print(f"{rm:8}{pac:10}{dev:14} add={t_raw:7}(A{a_raw:4} B{b_raw:6} C{c_raw:6}) "
                  f"regs_gated={whole:4} fields={fld_acc:4} | pristine={pr:7}", flush=True)
            shutil.rmtree(dst)
    return out


def aggregate(out):
    base = min(r["generic_raw"] for r in out); gated = base + READ_GATE_LINES
    bycrate = defaultdict(list)
    for r in out:
        bycrate[r["pac"]].append(r)
    per_pac, anomalies = [], []
    for pac, rows in sorted(bycrate.items()):
        vals = {r["generic_raw"] for r in rows}
        if not vals <= {base, gated}:
            anomalies.append({"pac": pac, "generic_raw": sorted(vals)})
        # A,B once per crate (representative = max); C summed per device
        A1 = max(r["generic_raw"] for r in rows); A1s = max(r["generic_sloc"] for r in rows)
        B1 = max(r["walk_raw"] for r in rows);    B1s = max(r["walk_sloc"] for r in rows)
        Cr = sum(r["enforce_raw"] for r in rows); Cs = sum(r["enforce_sloc"] for r in rows)
        cids = set()                                    # distinct constraints the crate enforces
        for r in rows:
            cids |= set(r.get("constraint_ids") or [])
        per_pac.append({"pac": pac, "n_devices": len(rows),
                        "n_constraints": len(cids),
                        "devices": [r["device"] for r in rows],
                        "read_gated_devices": [r["device"] for r in rows if r["generic_raw"] == gated],
                        "pristine_raw": rows[0]["pristine_raw"], "pristine_sloc": rows[0]["pristine_sloc"],
                        "A_raw": A1, "A_sloc": A1s, "B_raw": B1, "B_sloc": B1s,
                        "C_raw": Cr, "C_sloc": Cs,
                        "crate_added_raw": A1 + B1 + Cr, "crate_added_sloc": A1s + B1s + Cs,
                        "naive_sum_raw": sum(r["total"] for r in rows),
                        "naive_sum_sloc": sum(r["sloc"] for r in rows),
                        "regs_gated": sum(r["regs_gated"] for r in rows),
                        "fields_gated": sum(r["fields_gated"] for r in rows)})
    sanity = {"generic_values": {"ungated": base, "read_gated": gated},
              "n_read_gated_devices": sum(1 for r in out if r["generic_raw"] == gated),
              "only_read_gate_toggle": not anomalies, "anomalies": anomalies}
    return per_pac, sanity


def report(out, per_pac, sanity, mode):
    def col(rows, k): return sum(r[k] for r in rows)
    A, B, C = col(out, "generic_raw"), col(out, "walk_raw"), col(out, "enforce_raw")
    T = col(out, "total")
    honest = sum(p["crate_added_raw"] for p in per_pac)
    honest_s = sum(p["crate_added_sloc"] for p in per_pac)
    print(f"\n== generic.rs sanity: {sanity['generic_values']}, "
          f"{sanity['n_read_gated_devices']}/{len(out)} read-gated; "
          f"clean? {'YES' if sanity['only_read_gate_toggle'] else sanity['anomalies']}")
    print(f"\n== THREE BUCKETS (raw, summed over {len(out)} device injections) ==")
    print(f"   A generic.rs   {A:>10,} ({100*A/T:4.1f}%)")
    print(f"   B marker walk  {B:>10,} ({100*B/T:4.1f}%)")
    print(f"   C enforcement  {C:>10,} ({100*C/T:4.1f}%)")
    print(f"\n== TOTALS ==")
    print(f"   naive per-device sum : raw {T:,}  sloc {col(out,'sloc'):,}")
    print(f"   honest per-crate     : raw {honest:,}  sloc {honest_s:,}  "
          f"(A+B once/crate, C per device)")
    print(f"   pristine (23 crates) : raw {sum(p['pristine_raw'] for p in per_pac):,}  "
          f"sloc {sum(p['pristine_sloc'] for p in per_pac):,}")
    print(f"\n{'crate':10}{'#dev':>5}{'pristine raw/sloc':>20}{'A':>6}{'B(walk)':>9}"
          f"{'C(enf)':>8}{'crate+ raw/sloc':>18}{'regs':>6}{'flds':>6}")
    for p in per_pac:
        print(f"{p['pac']:10}{p['n_devices']:>5}{p['pristine_raw']:>12,}/{p['pristine_sloc']:<7,}"
              f"{p['A_raw']:>6}{p['B_raw']:>9,}{p['C_raw']:>8,}"
              f"{p['crate_added_raw']:>11,}/{p['crate_added_sloc']:<6,}"
              f"{p['regs_gated']:>6}{p['fields_gated']:>6}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--register-only", action="store_true")
    args = ap.parse_args()
    mode = "register-only (whole-register)" if args.register_only else "field-level (inject_from_run default)"
    out = inject_all(args.register_only)
    per_pac, sanity = aggregate(out)
    json.dump({"mode": mode, "rows": out, "per_pac": per_pac, "sanity": sanity},
              open(HERE/"injection_loc.json", "w"), indent=1)
    print(f"\nwrote injection_loc.json: {len(out)} devices, {len(per_pac)} crates, mode={mode}")
    report(out, per_pac, sanity, mode)


if __name__ == "__main__":
    main()
