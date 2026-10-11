#!/usr/bin/env python3
"""Build each downstream crate (HAL / firmware) against the injected PACs and
isolate the witness-gate firings from pre-existing build breakage.

Method per target: clone → build PRISTINE (no patch). If pristine fails, the
target is not evaluable (record why). If pristine builds, add
`[patch.crates-io] <pac> = { path = <injected> }` and rebuild; every NEW error
is a gate firing (E0277 whole-register hard gate, or E0061 field advisory).

Targets are configured in DOWNSTREAM below. Writes a per-target firing report
and a downstream_summary.json.

    python run_downstream.py                  # all
    python run_downstream.py lpc55-hal        # one
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parents[1]
VENDORED = APP / "vendored" / "pac"
# When the vendored PACs were injected with the field-level advisory
# (GATE_MODE=field), route outputs to *_field.json so the whole-register
# downstream results are not clobbered.
SUF = "_field" if os.environ.get("GATE_MODE") == "field" else ""
SCRATCH = Path("/tmp/claude-1006/-home-ramla-hal-agent-pac-injection/"
               "777dc301-e753-406b-a6c8-f0cf2b5598fe/scratchpad/downstream")

def inj(pac):           # injected PAC path
    return str(VENDORED / pac)

# name -> config. patch: {crate_name: injected_pac_dir}. build: extra cargo args.
DOWNSTREAM = [
    {"name": "lpc55-hal", "kind": "hal", "repo": "https://github.com/lpc55/lpc55-hal",
     "patch": {"lpc55-pac": "lpc55-pac"}, "target": "thumbv8m.main-none-eabihf"},
    {"name": "mk20dx-hal-mk20d7", "kind": "hal", "repo": "https://github.com/cosmikwolf/mk20dx-hal",
     "patch": {"mk20d7-pac": "mk20d7-pac", "mk20d5-pac": "mk20d5-pac"},
     "target": "thumbv7em-none-eabihf"},
    {"name": "mk20dx-hal-mk20d5", "kind": "hal", "repo": "https://github.com/cosmikwolf/mk20dx-hal",
     "patch": {"mk20d7-pac": "mk20d7-pac", "mk20d5-pac": "mk20d5-pac"},
     "target": "thumbv7em-none-eabihf",
     "build": ["--no-default-features", "--features", "mk20d5,rt"]},
    {"name": "lpc8xx-hal", "kind": "hal", "repo": "https://github.com/lpc-rs/lpc8xx-hal",
     "branch": "master",
     "patch": {"lpc845-pac": "lpc845-pac"}, "target": "thumbv6m-none-eabi",
     "build": ["--no-default-features", "--features", "845m301jbd48"]},
    {"name": "embassy-imxrt", "kind": "hal", "repo": "https://github.com/OpenDevicePartnership/embassy-imxrt",
     "patch": {"mimxrt685s-pac": "mimxrt685s-pac", "mimxrt633s-pac": "mimxrt633s-pac"},
     "target": "thumbv8m.main-none-eabihf",
     "build": ["--features", "mimxrt685s,time-driver-os-timer"]},
    {"name": "bootleby", "kind": "firmware", "repo": "https://github.com/oxidecomputer/bootleby",
     "patch": {"lpc55-pac": "lpc55-pac"}, "target": "thumbv8m.main-none-eabihf"},
    # Nitrokey 3 LPC55 firmware: version-matched (lpc55-pac 0.5, lpc55-hal
    # 0.7.1, both crates.io). Build the embedded runner lib for the LPC55 board
    # (board-nk3xn => soc-lpc55).
    {"name": "nitrokey-3-firmware", "kind": "firmware",
     "repo": "https://github.com/Nitrokey/nitrokey-3-firmware",
     "patch": {"lpc55-pac": "lpc55-pac"}, "target": "thumbv8m.main-none-eabi",
     "build": ["-p", "embedded-runner-lib", "--no-default-features",
               "--features", "board-nk3xn"]},
    # solo2 (lpc55-hal 0.6 -> lpc55-pac ^0.4, + `-Dwarnings`) and hubris
    # (lpc55-pac ^0.4 + xtask build) are version/build-incompatible with the
    # 0.5.0 injection and are documented as out of scope rather than run here.
    #
    # Low-value scan: canadensis's s32k146 UAVCAN example — the only remaining
    # project that pairs a device we have constraints for (s32k1xx RM, injected
    # into s32k146-pac) with a real consumer. It drives FlexCAN registers RAW
    # (no HAL), so it is a good bug-hunt target. Build just the example package.
    {"name": "canadensis-s32k146", "kind": "firmware",
     "repo": "https://github.com/samcrow/canadensis",
     "patch": {"s32k146-pac": "s32k146-pac"}, "target": "thumbv7em-none-eabihf",
     "build": ["-p", "s32k146_node"]},
]


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


def errors(stderr):
    return [l for l in stderr.splitlines() if re.match(r'error(\[|:)', l)]


def firings(stderr):
    lines = stderr.splitlines()
    out, i = [], 0
    while i < len(lines):
        m = re.match(r'error\[E0277\]: `(\w+)` is (write|modify|read)-constrained', lines[i])
        if m:
            loc = next((re.search(r'--> (\S+:\d+)', lines[j]).group(1)
                        for j in range(i+1, min(i+6, len(lines)))
                        if re.search(r'--> \S+:\d+', lines[j])), "?")
            out.append(("E0277", f"{m.group(1)} {m.group(2)}", loc))
        elif re.match(r'error\[E0061\]:', lines[i]):
            window = "\n".join(lines[i:i+14])
            loc = next((re.search(r'--> (\S+:\d+)', lines[j]).group(1)
                        for j in range(i+1, min(i+8, len(lines)))
                        if re.search(r'--> \S+:\d+', lines[j])), "?")
            # The field identity is in the witness type the accessor now wants:
            # `...constraints::<Reg><Field>FieldWitness`.
            w = re.search(r'constraints::(\w+FieldWitness)', window)
            out.append(("E0061-field", w.group(1) if w else "", loc))
        i += 1
    return out


def do(cfg):
    name = cfg["name"]
    res = {"name": name, "kind": cfg["kind"], "repo": cfg["repo"]}
    SCRATCH.mkdir(parents=True, exist_ok=True)
    d = SCRATCH / name
    if not d.exists():
        clone = ["git", "clone", "--depth", "1"]
        if cfg.get("branch"):
            clone += ["--branch", cfg["branch"]]
        c = run(clone + [cfg["repo"], str(d)], SCRATCH)
        if c.returncode != 0:
            res["status"] = "clone_failed"; res["detail"] = c.stderr.strip()[-300:]; return res
    base = ["cargo", "build", "--target", cfg["target"]] + cfg.get("build", [])

    # restore a clean manifest if we patched a prior run
    root_toml = d / "Cargo.toml"
    orig = root_toml.read_text()
    orig = re.split(r"\n# === LIDAR patch ===", orig)[0]
    root_toml.write_text(orig)

    pristine = run(base, d)
    if pristine.returncode != 0:
        res["status"] = "pristine_build_failed"
        res["pristine_errors"] = errors(pristine.stderr)[:8]
        return res

    patch = "\n# === LIDAR patch ===\n[patch.crates-io]\n" + "".join(
        f'{c} = {{ path = "{inj(p)}" }}\n' for c, p in cfg["patch"].items())
    root_toml.write_text(orig + patch)

    injected = run(base, d)
    fr = firings(injected.stderr)
    res["status"] = "ok" if injected.returncode == 0 else "fired"
    res["compiles_injected"] = injected.returncode == 0
    res["n_e0277"] = sum(1 for k, *_ in fr if k == "E0277")
    res["n_e0061_field"] = sum(1 for k, *_ in fr if k == "E0061-field")
    res["firings"] = [{"kind": k, "what": w, "loc": l} for k, w, l in fr]
    # non-firing new errors (may indicate an injection artifact, not a bug)
    other = [e for e in errors(injected.stderr)
             if "constrained by its datasheet" not in e
             and "E0277" not in e and "E0061" not in e]
    res["other_new_errors"] = other[:6]
    (HERE / f"{name}.firings{SUF}.json").write_text(json.dumps(res, indent=1))
    return res


def main():
    want = sys.argv[1:]
    cfgs = [c for c in DOWNSTREAM if not want or c["name"] in want]
    results = []
    for c in cfgs:
        print(f"=== {c['name']} ===", flush=True)
        r = do(c)
        results.append(r)
        print(f"    {r.get('status')}  E0277={r.get('n_e0277','-')} "
              f"E0061={r.get('n_e0061_field','-')}", flush=True)
    (HERE / f"downstream_summary{SUF}.json").write_text(json.dumps(results, indent=1))
    print("\n" + "=" * 70)
    print(f"{'downstream':22} {'kind':9} {'status':22} {'E0277':>5} {'E0061':>5}")
    for r in results:
        print(f"{r['name']:22} {r['kind']:9} {r.get('status',''):22} "
              f"{str(r.get('n_e0277','-')):>5} {str(r.get('n_e0061_field','-')):>5}")


if __name__ == "__main__":
    main()
