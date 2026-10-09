#!/usr/bin/env python3
"""Inject every NXP device's confirmed access constraints into its published
svd2rust PAC and compile the result.

For each device: provision the crates.io PAC (byte-authentic generated source),
stage its SVD, run the end-to-end injector against the device's generator run
and human-reviewed constraint ledger, then `cargo build --lib` the injected
crate. Emits a summary table + per-device JSON reports.

The constraint ledgers and generator runs live in the sibling phase-1d worktree
(the NXP full-sweep campaign); this experiment only consumes them.

    python run_all.py            # all devices
    python run_all.py lpc55s69   # one device
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parents[1]                      # applications/pac_codegen
REPO = APP.parents[1]                      # repo root
P1D = Path("/home/ramla/hal_agent-phase-1d")
GET_PAC = APP / "get_pac.py"
INJECT = APP / "inject_from_run.py"
VENDORED = APP / "vendored" / "pac"

# device -> (crate, version, svd filename under devices/nxp/<dev>/svd/)
DEVICES = {
    "lpc55s69":   ("lpc55-pac",     "0.5.0", "LPC55S69_cm33_core0.xml"),
    "ke04":       ("ke04z4-pac",    "0.1.0", "MKE04Z4.xml"),
    "s32k1xx":    ("s32k144-pac",   "0.1.0", "S32K144.svd"),
    "lpc845":     ("lpc845-pac",    "0.4.1", "LPC845.xml"),
    "mk20d7":     ("mk20d7-pac",    "0.1.1", "MK20D7.svd"),
    "mk20d5":     ("mk20d5-pac",    "0.1.1", "MK20D5.svd"),
    "mimxrt685s": ("mimxrt685s-pac", "0.5.0", "MIMXRT685S_cm33.xml"),
    "mimxrt633s": ("mimxrt633s-pac", "0.5.0", "MIMXRT633S.xml"),
    "k64":        ("k64",           "0.1.0", "MK64F12.xml"),
}


def sh(cmd, **kw):
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, **kw)


def run_device(dev):
    crate, ver, svd_name = DEVICES[dev]
    out = {"device": dev, "crate": crate, "version": ver}
    devdir = HERE / dev
    devdir.mkdir(parents=True, exist_ok=True)

    # 1. provision pristine PAC
    p = sh([sys.executable, str(GET_PAC), "--crate", crate, "--version", ver, "--force"])
    pac = VENDORED / crate
    if p.returncode != 0 or not (pac / "src" / "generic.rs").is_file():
        out["status"] = "provision_failed"
        out["detail"] = (p.stderr or p.stdout).strip().splitlines()[-1:]
        return out

    # 2. stage the SVD as .svd (the loader globs *.svd; NXP ships .xml)
    src_svd = P1D / "devices" / "nxp" / dev / "svd" / svd_name
    if not src_svd.is_file():
        out["status"] = "svd_missing"
        out["detail"] = str(src_svd)
        return out
    svd_dir = devdir / "svd"
    svd_dir.mkdir(exist_ok=True)
    staged = svd_dir / (src_svd.stem + ".svd")
    staged.write_bytes(src_svd.read_bytes())

    # 3. inject
    run_dir = P1D / "agent_output" / "nxp" / dev / "1"
    review = P1D / "evaluation" / "nxp" / dev / "1" / f"{dev}_constraints_review.jsonl"
    report = devdir / "inject_report.json"
    inj = sh([sys.executable, str(INJECT), str(run_dir),
              "--pac", str(pac), "--device", ".",
              "--svd-dir", str(svd_dir),
              "--constraints", str(review),
              "--report", str(report)])
    if report.is_file():
        r = json.loads(report.read_text())
        out["registers_planned"] = r.get("registers_planned", 0)
        out["injected"] = r.get("injected", False)
        out["fates"] = r.get("fates", {})
        gated = [f"{row['peripheral']}/{row['register']}"
                 for row in r.get("rows", []) if row.get("fate") == "planned"]
        out["gated_registers"] = sorted(set(gated))
    else:
        out["status"] = "inject_failed"
        out["detail"] = (inj.stderr or inj.stdout).strip().splitlines()[-3:]
        return out

    if not out.get("injected"):
        out["status"] = "nothing_injected"
        return out

    # 4. compile the injected PAC
    b = subprocess.run(["cargo", "build", "--lib"], cwd=str(pac),
                       capture_output=True, text=True)
    out["compiles"] = (b.returncode == 0)
    if b.returncode != 0:
        errs = [l for l in b.stderr.splitlines() if l.startswith("error")]
        out["compile_errors"] = errs[:6]
    out["status"] = "ok" if out["compiles"] else "compile_failed"
    return out


def main():
    want = sys.argv[1:] or list(DEVICES)
    results = []
    for dev in want:
        print(f"=== {dev} ===", flush=True)
        res = run_device(dev)
        results.append(res)
        print(f"    status={res.get('status')} planned={res.get('registers_planned')} "
              f"compiles={res.get('compiles')}", flush=True)
    (HERE / "summary.json").write_text(json.dumps(results, indent=1))

    # table
    print("\n" + "=" * 78)
    print(f"{'device':12} {'crate':16} {'planned':>7} {'compiles':>8}  gated registers")
    print("-" * 78)
    for r in results:
        gr = ", ".join(r.get("gated_registers", []))
        if len(gr) > 30:
            gr = gr[:27] + "..."
        print(f"{r['device']:12} {r['crate']:16} "
              f"{str(r.get('registers_planned','-')):>7} "
              f"{str(r.get('compiles','-')):>8}  {r.get('status')}: {gr}")


if __name__ == "__main__":
    main()
