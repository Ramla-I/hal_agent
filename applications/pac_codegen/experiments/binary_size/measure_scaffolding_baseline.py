#!/usr/bin/env python3
"""Pure-scaffolding baseline: what injection costs with ZERO constraints.

Turns the witness mechanism on crate-wide but gates nothing -- every register in
every device tree gets its full ``impl Unconstrained{Read,Write,Modify}`` marker,
generic.rs gets all three bounds, and NO ``pub mod constraints`` module is emitted
(C = 0 by construction). This is the floor: the cost of making a whole crate
witness-gate-able before a single datasheet constraint is added. Compared against
the with-constraints marker walk (B), the gated registers here get their withheld
markers back, so B grows.

    A  generic.rs header  (all three bounds -> 260 lines)
    B_full  marker walk with NOTHING withheld
    C  = 0

Writes scaffolding_baseline.json next to this script. NO cargo, no pipeline
artifacts needed -- only the pristine crates.
"""
import json, glob, shutil, subprocess, sys, tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))
import rust_codegen as rc

VEND = APP / "vendored/pac"
VEND_MASTER = APP / "vendored/pac_master"
HERE = Path(__file__).resolve().parent

# one representative device per crate (target tree; siblings get full markers too)
CRATES = [
    ("stm32c0","stm32c031",VEND),("stm32f0","stm32f0x1",VEND),("stm32f1","stm32f103",VEND),
    ("stm32f2","stm32f215",VEND),("stm32f3","stm32f303",VEND),("stm32f4","stm32f401",VEND),
    ("stm32f7","stm32f746",VEND),("stm32g0","stm32g070",VEND),("stm32g4","stm32g474",VEND),
    ("stm32h5","stm32h573",VEND),("stm32h7","stm32h753",VEND),("stm32l0","stm32l0x3",VEND),
    ("stm32l1","stm32l151",VEND),("stm32l4","stm32l4x6",VEND),("stm32l5","stm32l562",VEND),
    ("stm32mp1","stm32mp157",VEND),("stm32n6","stm32n657",VEND),("stm32u0","stm32u083",VEND),
    ("stm32u5","stm32u5a9",VEND),("stm32wb","stm32wb55",VEND),("stm32wl","stm32wl5x_cm4",VEND),
    ("stm32wba","stm32wba55",VEND_MASTER),("stm32wb0","stm32wb09",VEND_MASTER),
]


def is_code(s):
    s = s.strip()
    return bool(s) and not s.startswith(("//", "/*", "*/", "*"))


def added(a, b):
    """(gen_raw, gen_sloc, tot_raw, tot_sloc) from the pristine->baseline diff."""
    r = subprocess.run(["git","diff","--no-index","-U0",str(a),str(b)],
                       capture_output=True, text=True)
    g_r=g_s=t_r=t_s=0; generic=False
    for line in r.stdout.splitlines():
        if line.startswith("+++ "):
            generic = line[4:].endswith("/generic.rs")
        elif line.startswith(("--- ","diff ","index ","@@ ","\\")):
            continue
        elif line.startswith("+"):
            c = is_code(line[1:]); t_r+=1; t_s+=c
            if generic: g_r+=1; g_s+=c
    return g_r,g_s,t_r,t_s


def main():
    out=[]
    with tempfile.TemporaryDirectory() as td:
        for pac,dev,root in CRATES:
            src = root/pac
            dst = Path(td)/pac
            shutil.copytree(src, dst)
            generic = dst/"src"/"generic.rs"
            device_dir = dst/"src"/dev
            rc.patch_generic_rs(generic, None)          # all bounds -> A=260
            rc.add_marker_impls(device_dir, set())      # target: full walk
            rc.add_sibling_markers(dst/"src", dev)      # siblings: full walk
            a_r,a_s,t_r,t_s = added(src, dst)
            b_r,b_s = t_r-a_r, t_s-a_s                  # C=0, so B_full = total-A
            out.append({"pac":pac,"device":dev,
                        "A_raw":a_r,"A_sloc":a_s,
                        "Bfull_raw":b_r,"Bfull_sloc":b_s,
                        "scaffold_raw":t_r,"scaffold_sloc":t_s})
            print(f"{pac:10}{dev:14} A={a_r:4}/{a_s:<4} B_full={b_r:>8,}/{b_s:<8,} "
                  f"scaffold={t_r:>8,}/{t_s:<8,}", flush=True)
            shutil.rmtree(dst)
    json.dump({"rows":out}, open(HERE/"scaffolding_baseline.json","w"), indent=1)
    A=sum(r["A_raw"] for r in out); B=sum(r["Bfull_raw"] for r in out)
    As=sum(r["A_sloc"] for r in out); Bs=sum(r["Bfull_sloc"] for r in out)
    print(f"\n== PURE SCAFFOLDING (23 crates, zero constraints, C=0) ==")
    print(f"   A generic.rs : raw {A:,}  sloc {As:,}")
    print(f"   B_full walk  : raw {B:,}  sloc {Bs:,}")
    print(f"   TOTAL        : raw {A+B:,}  sloc {As+Bs:,}")


if __name__ == "__main__":
    main()
