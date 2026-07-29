#!/usr/bin/env python3
"""Provision generated svd2rust PAC crates that the compile tests inject into.

svd2rust PAC crates publish their *generated source*, so the crates.io package
is a byte-authentic generated PAC — no submodule fetch, no svd2rust run, no
rustfmt. This script downloads a package, verifies its sha256 against the
crates.io index checksum, and unpacks it to::

    applications/pac_codegen/vendored/pac/<crate>/

(git-ignored; a stamp file makes re-runs a no-op). The default crate is the
pinned stm32f4 test PAC (its checksum is hardcoded); any other crate/version
fetches its checksum from the crates.io index at runtime. The constraint_test
crate path-depends on the stm32f4 directory, and test_codegen.py looks for
the PAC there — the no-argument behavior is unchanged.

Usage:
    python applications/pac_codegen/get_pac.py [--force]
    python applications/pac_codegen/get_pac.py --crate stm32f1 --version 0.16.0

Exits 0 and prints the PAC directory on success (already-provisioned counts).
"""

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

PAC_NAME = "stm32f4"
PAC_VERSION = "0.16.0"
# sha256 of the .crate tarball, from https://index.crates.io/st/m3/stm32f4
# (the DEFAULT crate stays pinned; other crates are verified against the
# index checksum fetched at provision time).
PAC_SHA256 = "c41bd8922df364cb7054cae71a95dcbb32cffd25b5c0f9c00272ef8c82279a65"

APP_DIR = Path(__file__).resolve().parent
PAC_ROOT = APP_DIR / "vendored" / "pac"
# Default-crate paths, kept for existing callers (test_codegen.py, CI).
PAC_DIR = PAC_ROOT / PAC_NAME
STAMP = PAC_DIR / ".lidar_pac_version"
STAMP_NAME = ".lidar_pac_version"


def _index_prefix(name: str) -> str:
    """crates.io sparse-index path prefix for a crate name."""
    if len(name) == 1:
        return "1"
    if len(name) == 2:
        return "2"
    if len(name) == 3:
        return f"3/{name[0]}"
    return f"{name[:2]}/{name[2:4]}"


def _index_checksum(crate: str, version: str) -> str:
    """Fetch the sha256 for crate-version from the crates.io sparse index."""
    url = f"https://index.crates.io/{_index_prefix(crate)}/{crate}"
    with urllib.request.urlopen(url) as resp:
        body = resp.read().decode()
    for line in body.splitlines():
        entry = json.loads(line)
        if entry["vers"] == version:
            return entry["cksum"]
    raise RuntimeError(f"{crate} {version} not found in the crates.io index ({url})")


def pac_dir(crate: str = PAC_NAME) -> Path:
    return PAC_ROOT / crate


def provisioned(crate: str = PAC_NAME, version: str = PAC_VERSION) -> bool:
    stamp = pac_dir(crate) / STAMP_NAME
    return stamp.is_file() and stamp.read_text().strip() == version


def provision(force: bool = False, crate: str = PAC_NAME,
              version: str = PAC_VERSION) -> Path:
    target_dir = pac_dir(crate)
    if provisioned(crate, version) and not force:
        return target_dir

    if (crate, version) == (PAC_NAME, PAC_VERSION):
        sha256 = PAC_SHA256
    else:
        sha256 = _index_checksum(crate, version)

    if target_dir.exists():
        shutil.rmtree(target_dir)
    PAC_ROOT.mkdir(parents=True, exist_ok=True)

    url = f"https://static.crates.io/crates/{crate}/{crate}-{version}.crate"
    print(f"Downloading {crate} {version} from crates.io ...")
    with urllib.request.urlopen(url) as resp:
        data = resp.read()

    digest = hashlib.sha256(data).hexdigest()
    if digest != sha256:
        raise RuntimeError(
            f"checksum mismatch for {url}:\n"
            f"  expected {sha256}\n  got      {digest}"
        )

    with tempfile.TemporaryDirectory() as td:
        tarball = Path(td) / "pac.crate"
        tarball.write_bytes(data)
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(td, filter="data")
        unpacked = Path(td) / f"{crate}-{version}"
        if not (unpacked / "src" / "generic.rs").is_file():
            raise RuntimeError(f"unexpected package layout under {unpacked}")
        shutil.move(str(unpacked), str(target_dir))

    (target_dir / STAMP_NAME).write_text(version + "\n")
    print(f"Provisioned {target_dir}")
    return target_dir


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true",
                    help="re-download and re-unpack even if already provisioned")
    ap.add_argument("--crate", default=PAC_NAME,
                    help=f"crates.io package name (default: {PAC_NAME})")
    ap.add_argument("--version", default=None,
                    help=f"crate version (default: {PAC_VERSION} for the "
                         "default crate; required for any other crate)")
    args = ap.parse_args()
    if args.version is None:
        if args.crate != PAC_NAME:
            ap.error("--version is required with a non-default --crate "
                     "(the pinned default applies only to "
                     f"{PAC_NAME} {PAC_VERSION})")
        args.version = PAC_VERSION
    print(provision(force=args.force, crate=args.crate, version=args.version))


if __name__ == "__main__":
    main()
