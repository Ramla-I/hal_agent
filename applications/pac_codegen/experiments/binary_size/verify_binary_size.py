#!/usr/bin/env python3
"""Measure the injection's firmware-binary cost, and record it to binary_size.json.

Builds the firmware (sizefw/, which only touches UNGATED registers so it compiles
against either PAC) and compares the executable code across:

  * pristine PAC vs field-level-injected PAC  -> is .text byte-identical?
  * on the injected PAC, one write to a GATED register done two ways:
      write_unwitnessed (the unsafe bypass = a plain store) vs
      write_when_ready  (the checked path)  -> the runtime cost of ONE check.

Writes ``binary_size.json`` (read by plot_injection_cost.py so the figure's
binary-side numbers are measured, not hardcoded):

  {"identical": true, "text_bytes": <N>, "check_cost_bytes": <N>, ...}

Needs cargo + the thumbv7em-none-eabihf target. Defaults to stm32g4 / rm0440
(the RCC.BDCR gate); other crates run the identical-check only.

    python verify_binary_size.py
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile, glob
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
REPO = APP.parents[1]
DATA = Path("/home/ramla/hal_agent-phase-1d")
INJECT = APP / "inject_from_run.py"
HERE = Path(__file__).resolve().parent
FW = HERE / "sizefw"
TARGET = "thumbv7em-none-eabihf"

BASE = FW / "src" / "main.rs"
# a gated-register write done two ways (g4 RCC.BDCR needs PWR.CR1.DBP); injected-PAC only
CHECKED = '    let _ = dp.RCC.bdcr().write_when_ready(|w| unsafe { w.bits(0x100) }, dp.PWR.cr1());'
BYPASS  = '    let _ = unsafe { dp.RCC.bdcr().write_unwitnessed(|w| unsafe { w.bits(0x100) }) };'


def tool(name):
    hits = glob.glob(str(Path.home()/f".rustup/toolchains/*/lib/rustlib/*/bin/{name}"))
    return hits[0] if hits else name


def set_pac(pac_path):
    BASE.parent.parent.joinpath("Cargo.toml").write_text(
        re.sub(r'(stm32g4 = \{ path = )"[^"]*"', rf'\1"{pac_path}"',
               (FW/"Cargo.toml").read_text()))


def build(pac_path, main_src, tag):
    set_pac(pac_path)
    BASE.write_text(main_src)
    td = FW / f"target_{tag}"
    shutil.rmtree(td, ignore_errors=True)
    r = subprocess.run(["cargo", "build", "--release"], cwd=str(FW),
                       capture_output=True, text=True,
                       env={**os.environ, "CARGO_TARGET_DIR": str(td)})
    if r.returncode != 0:
        sys.exit(f"build ({tag}) failed:\n{r.stderr[-1500:]}")
    return td / TARGET / "release" / "sizefw"


def text_size(elf):
    out = subprocess.run([tool("llvm-size"), str(elf)], capture_output=True, text=True).stdout
    return int(out.splitlines()[1].split()[0])   # .text column


def text_sha(elf):
    b = tempfile.mktemp(suffix=".bin")
    subprocess.run([tool("llvm-objcopy"), "-O", "binary", "--only-section=.text",
                    str(elf), b], check=True)
    return hashlib.sha256(open(b, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rm", default="rm0440")
    ap.add_argument("--device", default="stm32g474")
    ap.add_argument("--crate", default="stm32g4")
    args = ap.parse_args()
    ungated = BASE.read_text()
    checked = ungated.replace("    loop {}", CHECKED + "\n    loop {}", 1)
    bypass  = ungated.replace("    loop {}", BYPASS  + "\n    loop {}", 1)
    pristine = APP / "vendored/pac" / args.crate
    rd = DATA / f"agent_output/stm/{args.rm}/1"
    val = rd / "constraint_validation/validated.jsonl"
    svd = DATA / f"devices/stm/{args.rm}/svd"
    result = {"crate": args.crate, "device": args.device, "rm": args.rm}
    with tempfile.TemporaryDirectory() as td:
        injected = Path(td) / args.crate
        shutil.copytree(pristine, injected)
        subprocess.run([sys.executable, str(INJECT), str(rd), "--pac", str(injected),
                        "--device", args.device, "--constraints", str(val),
                        "--svd-dir", str(svd)], check=True, cwd=str(REPO), capture_output=True)
        try:
            ep = build(pristine, ungated, "pristine")
            ei = build(injected, ungated, "injected")
            tp, ti = text_size(ep), text_size(ei)
            sp, si = text_sha(ep), text_sha(ei)
            result.update(text_bytes=ti, identical=(tp == ti and sp == si),
                          sha_pristine=sp, sha_injected=si)
            print(f"ungated .text: pristine={tp} injected={ti}  identical={result['identical']}")
            if args.crate == "stm32g4":   # the RCC.BDCR checked/bypass delta
                tb = text_size(build(injected, bypass, "bypass"))
                tc = text_size(build(injected, checked, "checked"))
                result["check_cost_bytes"] = tc - tb
                print(f"checked={tc} bypass={tb} -> +{tc-tb} B per opt-in check")
        finally:
            BASE.write_text(ungated); set_pac("PACPATH")
            for t in ("pristine", "injected", "bypass", "checked"):
                shutil.rmtree(FW / f"target_{t}", ignore_errors=True)
    (HERE/"binary_size.json").write_text(json.dumps(result, indent=1))
    print("wrote binary_size.json:", result)


if __name__ == "__main__":
    main()
