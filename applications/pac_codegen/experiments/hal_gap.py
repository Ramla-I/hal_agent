#!/usr/bin/env python3
"""How far is each unpaired HAL from the PAC generation the injector targets?

Four of the six STM HAL crates our corpus touches cannot be used for the
adoption experiment because no released version depends on PAC 0.16.0. That
statement is true but uninformative on its own: "upstream has not moved" could
mean the HAL is three method renames away from the new PAC, or that it is a
year of work. The difference decides whether waiting is the right call.

This measures it. For each unpaired HAL: take the PRISTINE PAC 0.16.0 (no
injection anywhere in this script), spoof the local copy's version string to
whatever the HAL's dependency requires so `[patch.crates-io]` will accept it,
and `cargo check` the unmodified HAL against it. Every error is the HAL using
an API that changed between the svd2rust generation it was written for and
0.36.1 -- i.e. the size of the upstream gap, with our work entirely absent.

The two PAIRED HALs (stm32f1xx-hal, stm32f4xx-hal) run as controls with no
spoofing: they must come back with zero errors, which is what makes the other
numbers readable as gap size rather than harness noise.

Usage:
    python applications/pac_codegen/experiments/hal_gap.py [--only stm32f3xx-hal]
"""

import argparse
import collections
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
import get_pac  # noqa: E402

PAC_VERSION = "0.16.0"
STEP_TIMEOUT = 2400
OUT = APP_DIR / "experiments" / "out"

# (HAL crate, HAL version, PAC crate, version req the HAL declares, features)
# `spoof` is the version the local PAC must CLAIM for [patch.crates-io] to
# apply; None = already compatible (control).
CASES = [
    ("stm32f1xx-hal", "0.11.0", "stm32f1", None, ["stm32f103", "medium"]),
    ("stm32f4xx-hal", "0.23.0", "stm32f4", None, ["stm32f401"]),
    ("stm32f3xx-hal", "0.10.0", "stm32f3", "0.15.1", ["stm32f303xc"]),
    ("stm32l0xx-hal", "0.10.0", "stm32l0", "0.15.1", ["stm32l0x3", "mcu-STM32L073RZTx"]),
    ("stm32f0xx-hal", "0.18.0", "stm32f0", "0.14.0", ["stm32f051"]),
    ("stm32l1xx-hal", "0.1.0", "stm32l1", "0.5.0", ["stm32l151"]),
]


def spoofed_pac(crate: str, claim: str) -> Path:
    """A copy of the provisioned PAC whose Cargo.toml claims `claim`. Cargo
    only applies a [patch] whose version satisfies the requirement; the SOURCE
    is untouched, so what compiles is the real 0.16.0 code."""
    src = get_pac.provision(crate=crate, version=PAC_VERSION)
    dst = Path(tempfile.mkdtemp(prefix=f"hal_gap_pac_{crate}_")) / crate
    shutil.copytree(src, dst)
    manifest = dst / "Cargo.toml"
    text = manifest.read_text()
    new, n = re.subn(rf'^version = "{re.escape(PAC_VERSION)}"$',
                     f'version = "{claim}"', text, count=1, flags=re.M)
    if n != 1:
        raise RuntimeError(f"could not spoof version in {manifest}")
    manifest.write_text(new)
    return dst


def workspace(hal: str, hal_version: str, pac: str, pac_dir: Path,
              features: list) -> Path:
    ws = Path(tempfile.mkdtemp(prefix=f"hal_gap_{hal}_"))
    (ws / "src").mkdir()
    (ws / "src" / "lib.rs").write_text(
        "#![no_std]\n"
        f"pub use {hal.replace('-', '_')} as hal;\n")
    feats = ", ".join(f'"{f}"' for f in features)
    (ws / "Cargo.toml").write_text(
        "[package]\n"
        f'name = "hal-gap-{hal}"\nversion = "0.1.0"\nedition = "2021"\n\n'
        "[dependencies]\n"
        f'{hal} = {{ version = "={hal_version}", features = [{feats}] }}\n\n'
        "[patch.crates-io]\n"
        f'{pac} = {{ path = "{pac_dir}" }}\n')
    return ws


def patch_applied(ws: Path, pac: str) -> bool:
    """Did cargo actually swap in our local PAC?

    If the spoofed version does not satisfy the HAL's requirement, cargo does
    NOT fail -- it prints "patch ... was not used in the crate graph" on stderr
    and quietly resolves the registry crate instead. The build then succeeds
    with zero errors while measuring nothing at all, which is
    indistinguishable from "the HAL compiles fine against 0.16" unless you
    check. A path dependency has no `source` key in Cargo.lock; a registry one
    does. That is the authoritative signal.
    """
    lock = ws / "Cargo.lock"
    if not lock.is_file():
        return False
    block, in_block = [], False
    for line in lock.read_text().splitlines():
        if line.strip() == "[[package]]":
            if in_block and any(l.strip() == f'name = "{pac}"' for l in block):
                return not any(l.startswith("source = ") for l in block)
            block, in_block = [], True
            continue
        if in_block:
            block.append(line)
    if block and any(l.strip() == f'name = "{pac}"' for l in block):
        return not any(l.startswith("source = ") for l in block)
    return False


def check(ws: Path, hal_dirname: str, pac: str) -> dict:
    try:
        run = subprocess.run(["cargo", "check", "--message-format=json"],
                             cwd=str(ws), capture_output=True, text=True,
                             timeout=STEP_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT"}

    if not patch_applied(ws, pac):
        return {"status": "PATCH_UNUSED", "returncode": run.returncode,
                "errors": [],
                "resolve_error": "cargo resolved the REGISTRY " + pac +
                                 " instead of the local patch; this result "
                                 "measures nothing. stderr:\n"
                                 + run.stderr.strip()[-800:]}

    errors, resolve_error = [], ""
    for line in run.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") != "compiler-message":
            continue
        d = m["message"]
        if d.get("level") != "error":
            continue
        files = set()

        def _walk(spans):
            for s in spans:
                fn = s.get("file_name", "")
                if hal_dirname in fn:
                    files.add(fn.split(f"{hal_dirname}/")[-1])
                exp = s.get("expansion")
                if exp and exp.get("span"):
                    _walk([exp["span"]])

        _walk(d.get("spans", []))
        for ch in d.get("children", []):
            _walk(ch.get("spans", []))
        errors.append({"code": (d.get("code") or {}).get("code", ""),
                       "message": d.get("message", ""),
                       "files": sorted(files)})
    if run.returncode != 0 and not errors:
        # Resolution / manifest failures never reach the JSON stream.
        resolve_error = run.stderr.strip()[-1500:]
    return {"status": "ok" if run.returncode == 0 else "errors",
            "returncode": run.returncode, "errors": errors,
            "resolve_error": resolve_error}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=[])
    args = ap.parse_args()
    cases = [c for c in CASES if not args.only or c[0] in args.only]

    results = []
    for hal, hv, pac, spoof, feats in cases:
        label = "control" if spoof is None else f"spoofed {PAC_VERSION} -> {spoof}"
        print(f"\n=== {hal} {hv} vs pristine {pac} {PAC_VERSION} ({label}) ===",
              flush=True)
        pac_dir = (spoofed_pac(pac, spoof) if spoof
                   else get_pac.provision(crate=pac, version=PAC_VERSION))
        ws = workspace(hal, hv, pac, pac_dir, feats)
        res = check(ws, f"{hal}-{hv}", pac)
        res.update({"hal": hal, "hal_version": hv, "pac": pac,
                    "spoof": spoof, "workspace": str(ws)})
        if res["status"] == "TIMEOUT":
            print("  TIMEOUT")
        elif res["status"] == "PATCH_UNUSED":
            print("  !! PATCH NOT APPLIED — result discarded")
            print("  " + res["resolve_error"].replace("\n", "\n  ")[:600])
        elif res.get("resolve_error"):
            print("  did not reach compilation:")
            print("  " + res["resolve_error"].replace("\n", "\n  ")[:900])
        else:
            errs = res["errors"]
            print(f"  {len(errs)} error(s)")
            by_code = collections.Counter(e["code"] for e in errs)
            by_file = collections.Counter(f for e in errs for f in e["files"])
            res["by_code"] = dict(by_code)
            res["by_file"] = dict(by_file)
            res["distinct_messages"] = len({e["message"] for e in errs})
            for code, n in by_code.most_common(6):
                print(f"    {n:4d}  {code or '(no code)'}")
            print(f"    distinct messages: {res['distinct_messages']}; "
                  f"HAL files touched: {len(by_file)}")
            for f, n in by_file.most_common(6):
                print(f"      {n:4d}  {f}")
            for e in errs[:3]:
                print(f"    e.g. [{e['code']}] {e['message'][:140]}")
        results.append(res)

    print("\n\n## HAL gap against pristine PAC 0.16.0 (no injection)\n")
    print("| HAL | version | PAC req | errors | distinct messages | HAL files | verdict |")
    print("|---|---|---|---|---|---|---|")
    for r in results:
        if r["status"] == "TIMEOUT":
            print(f"| {r['hal']} | {r['hal_version']} | {r['spoof'] or PAC_VERSION} "
                  f"| — | — | — | timed out |")
            continue
        if r["status"] == "PATCH_UNUSED":
            print(f"| {r['hal']} | {r['hal_version']} | {r['spoof'] or PAC_VERSION} "
                  f"| — | — | — | INVALID: patch not applied |")
            continue
        if r.get("resolve_error"):
            print(f"| {r['hal']} | {r['hal_version']} | {r['spoof'] or PAC_VERSION} "
                  f"| — | — | — | did not resolve/build |")
            continue
        n = len(r["errors"])
        verdict = ("compiles unchanged" if n == 0 else
                   "small compat gap" if n <= 25 else
                   "substantial API gap")
        print(f"| {r['hal']} | {r['hal_version']} | {r['spoof'] or PAC_VERSION} | {n} "
              f"| {r.get('distinct_messages','—')} | {len(r.get('by_file', {}))} "
              f"| {verdict} |")

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "hal_gap.json"
    out.write_text(json.dumps(results, indent=1) + "\n")
    print(f"\nreport: {out}")


if __name__ == "__main__":
    main()
