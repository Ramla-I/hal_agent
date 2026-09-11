#!/usr/bin/env python3
"""Can the injector reach the HAL families that have no PAC-0.16 pairing?

Four of the six STM HAL crates our corpus touches still depend on an OLDER
PAC than the 0.16.0 release the injector targets (checked live against the
crates.io index): stm32f3xx-hal -> stm32f3 0.15.1, stm32l0xx-hal -> stm32l0
0.15.1, stm32f0xx-hal -> stm32f0 0.14, stm32l1xx-hal -> stm32l1 0.5.

rm_pac_mappings/stm.toml's POLICY is to prefer a HAL's development branch on the new
PAC over back-porting the injector. That policy is only *cheaper* if the
back-port is actually expensive -- which is an empirical question about
svd2rust template drift, and this script answers it: provision each older PAC
into a SEPARATE root (never touching vendored/pac/, which the 0.16 sweep
uses), read its svd2rust stamp, and check every generic.rs anchor the
injector must find.

Downloads are checksum-verified against the crates.io index, same as
get_pac.py.

Usage:
    python applications/pac_codegen/experiments/old_pac_probe.py
"""

import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "experiments"))
import get_pac  # noqa: E402
from cross_pac import diagnose_template, svd2rust_version  # noqa: E402

# Deliberately NOT vendored/pac/: get_pac.provision() rmtree's a crate's
# directory when the version differs, so sharing the root would delete the
# 0.16.0 trees the main sweep depends on.
OLD_ROOT = APP_DIR / "vendored" / "pac_old"

# (HAL crate, PAC crate, PAC version its newest release requires)
PAIRS = [
    ("stm32f3xx-hal", "stm32f3", "0.15.1"),
    ("stm32l0xx-hal", "stm32l0", "0.15.1"),
    ("stm32f0xx-hal", "stm32f0", "0.14.0"),
    ("stm32l1xx-hal", "stm32l1", "0.5.0"),
]


def provision_old(crate: str, version: str) -> Path:
    target = OLD_ROOT / f"{crate}-{version}"
    if (target / "src" / "generic.rs").is_file():
        return target
    sha = get_pac._index_checksum(crate, version)
    url = f"https://static.crates.io/crates/{crate}/{crate}-{version}.crate"
    print(f"  downloading {crate} {version} ...", flush=True)
    with urllib.request.urlopen(url) as resp:
        data = resp.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha:
        raise RuntimeError(f"checksum mismatch for {url}: {got} != {sha}")
    OLD_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tarball = Path(td) / "pac.crate"
        tarball.write_bytes(data)
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(td, filter="data")
        unpacked = Path(td) / f"{crate}-{version}"
        if not (unpacked / "src" / "generic.rs").is_file():
            raise RuntimeError(f"unexpected package layout under {unpacked}")
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(unpacked), str(target))
    return target


def main() -> None:
    results = []
    for hal, crate, version in PAIRS:
        print(f"\n=== {hal} needs {crate} {version} ===")
        try:
            pac = provision_old(crate, version)
        except Exception as e:                                # noqa: BLE001
            print(f"  provision FAILED: {e}")
            results.append((hal, crate, version, "?", None, str(e)))
            continue
        sv = svd2rust_version(pac)
        rows = diagnose_template(pac)
        missing = [n for n, ok in rows if not ok]
        print(f"  svd2rust: {sv}")
        for name, ok in rows:
            print(f"    anchor {'MATCH  ' if ok else 'MISSING'} {name}")
        results.append((hal, crate, version, sv, rows, None))

    ref = get_pac.pac_dir("stm32f4")
    ref_sv = svd2rust_version(ref) if (ref / "src" / "lib.rs").is_file() else "?"

    print("\n\n## Older-PAC template compatibility\n")
    print(f"(injector targets the svd2rust {ref_sv} template, PAC 0.16.0)\n")
    print("| HAL crate | PAC | version | svd2rust | anchors matched | verdict |")
    print("|---|---|---|---|---|---|")
    for hal, crate, version, sv, rows, err in results:
        if rows is None:
            print(f"| {hal} | {crate} | {version} | — | — | provision failed: {err} |")
            continue
        ok = sum(1 for _, o in rows if o)
        verdict = ("injector applies unchanged" if ok == len(rows)
                   else f"template drift — {len(rows) - ok} anchor(s) missing")
        print(f"| {hal} | {crate} | {version} | {sv} | {ok}/{len(rows)} | {verdict} |")

    out = APP_DIR / "experiments" / "out" / "old_pac_probe.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        [{"hal": h, "pac": c, "version": v, "svd2rust": s,
          "anchors": dict(r) if r else None, "error": e}
         for h, c, v, s, r, e in results], indent=1) + "\n")
    print(f"\nreport: {out}")


if __name__ == "__main__":
    main()
