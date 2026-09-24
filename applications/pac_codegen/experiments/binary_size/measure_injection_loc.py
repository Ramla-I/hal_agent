#!/usr/bin/env python3
"""Measure how many lines the constraint injection adds to each PAC crate.

For every (reference manual, device, PAC crate) target, copy the pristine crate,
run ``inject_from_run.py`` over it (field-level gating by default -- the injection
default; ``--register-only`` for the whole-register variant), and diff against the
pristine tree. Splits the added lines into:

    modules      lines inside the generated ``pub mod constraints { .. }`` blocks
                 (the datasheet-enforcement code -- witnesses, gates, checks)
    scaffolding  everything else = the per-register `impl Unconstrained* for ..`
                 marker walk + the generic.rs header (zero-cost, erased by the
                 compiler; see verify_binary_size.py)

Writes ``injection_loc.json`` next to this script. NO cargo needed.

    python measure_injection_loc.py                # field-level (default)
    python measure_injection_loc.py --register-only

Targets are read from experiments/stm_sweep.py; the two master-only crates
(stm32wba, stm32wb0) come from vendored/pac_master. Pipeline artifacts are read
from the sibling hal_agent-phase-1d worktree (same convention as stm_sweep.py).
"""
import argparse, glob, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2]          # applications/pac_codegen
REPO = APP.parents[1]
DATA = Path("/home/ramla/hal_agent-phase-1d")       # sibling worktree (gitignored outputs)
INJECT = APP / "inject_from_run.py"
VEND = APP / "vendored/pac"
VEND_MASTER = APP / "vendored/pac_master"
HERE = Path(__file__).resolve().parent

# (rm, pac crate, device, source_root)
targets = [(rm, pac, dev, VEND) for rm, pac, dev in
           re.findall(r'Target\("(\w+)",\s*"(\w+)",\s*"(\w+)",',
                      (APP/"experiments/stm_sweep.py").read_text())]
# master-only crates (not in the 0.16.0 corpus); pick a device per crate
targets += [("rm0493", "stm32wba", "stm32wba55", VEND_MASTER),
            ("rm0505", "stm32wb0", "stm32wb09", VEND_MASTER),
            ("rm0529", "stm32wb0", "stm32wb05", VEND_MASTER),
            ("rm0530", "stm32wb0", "stm32wb06", VEND_MASTER)]


def numstat_total(a, b):
    r = subprocess.run(["git", "diff", "--no-index", "--numstat", str(a), str(b)],
                       capture_output=True, text=True)
    return sum(int(p.split("\t")[0]) for p in r.stdout.splitlines()
               if p.split("\t")[0].isdigit())


def module_lines(root):
    tot = 0
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
            tot += t[i:j].count("\n")
    return tot


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--register-only", action="store_true",
                    help="whole-register gating instead of the field-level default")
    args = ap.parse_args()
    out = []
    with tempfile.TemporaryDirectory() as td:
        for rm, pac, dev, src_root in targets:
            rd = DATA / f"agent_output/stm/{rm}/1"
            val = rd / "constraint_validation/validated.jsonl"
            svd = DATA / f"devices/stm/{rm}/svd"
            src = src_root / pac
            if not (rd.exists() and val.exists() and src.exists()):
                print(f"skip {rm} {pac} {dev}: missing inputs", flush=True); continue
            dst = Path(td) / f"{rm}_{dev}"
            shutil.copytree(src, dst)
            cmd = [sys.executable, str(INJECT), str(rd), "--pac", str(dst),
                   "--device", dev, "--constraints", str(val), "--svd-dir", str(svd)]
            if args.register_only:
                cmd.append("--register-only")
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
            if r.returncode != 0:
                tail = r.stderr.strip().splitlines()[-1][:70] if r.stderr.strip() else "?"
                print(f"ERR {rm} {pac}: {tail}", flush=True); shutil.rmtree(dst); continue
            total = numstat_total(src, dst); mods = module_lines(dst)
            out.append({"rm": rm, "pac": pac, "device": dev,
                        "total": total, "modules": mods, "scaffolding": total - mods})
            print(f"{rm:8}{pac:10}{dev:14} total={total:7} enforcement={mods:6} "
                  f"scaffolding={total-mods:7}", flush=True)
            shutil.rmtree(dst)
    mode = "register-only (whole-register)" if args.register_only else "field-level (inject_from_run default)"
    json.dump({"mode": mode, "rows": out}, open(HERE/"injection_loc.json", "w"), indent=1)
    print(f"\nwrote injection_loc.json: {len(out)} rows, "
          f"{len({r['pac'] for r in out})} crates, mode={mode}")


if __name__ == "__main__":
    main()
