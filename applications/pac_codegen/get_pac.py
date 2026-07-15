#!/usr/bin/env python3
"""Provision the generated stm32f4 PAC that the compile tests inject into.

svd2rust PAC crates publish their *generated source*, so the crates.io package
is a byte-authentic generated PAC — no submodule fetch, no svd2rust run, no
rustfmt. This script downloads the pinned package, verifies its sha256 against
the crates.io index checksum, and unpacks it to::

    applications/pac_codegen/vendored/pac/stm32f4/

(git-ignored; a stamp file makes re-runs a no-op). The constraint_test crate
path-depends on that directory, and test_codegen.py looks for the PAC there.

Usage:
    python applications/pac_codegen/get_pac.py [--force]

Exits 0 and prints the PAC directory on success (already-provisioned counts).
"""

import argparse
import hashlib
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

PAC_NAME = "stm32f4"
PAC_VERSION = "0.16.0"
# sha256 of the .crate tarball, from https://index.crates.io/st/m3/stm32f4
PAC_SHA256 = "c41bd8922df364cb7054cae71a95dcbb32cffd25b5c0f9c00272ef8c82279a65"
CRATE_URL = (
    f"https://static.crates.io/crates/{PAC_NAME}/{PAC_NAME}-{PAC_VERSION}.crate"
)

APP_DIR = Path(__file__).resolve().parent
PAC_ROOT = APP_DIR / "vendored" / "pac"
PAC_DIR = PAC_ROOT / PAC_NAME
STAMP = PAC_DIR / ".lidar_pac_version"


def provisioned() -> bool:
    return STAMP.is_file() and STAMP.read_text().strip() == PAC_VERSION


def provision(force: bool = False) -> Path:
    if provisioned() and not force:
        return PAC_DIR

    if PAC_DIR.exists():
        shutil.rmtree(PAC_DIR)
    PAC_ROOT.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {PAC_NAME} {PAC_VERSION} from crates.io ...")
    with urllib.request.urlopen(CRATE_URL) as resp:
        data = resp.read()

    digest = hashlib.sha256(data).hexdigest()
    if digest != PAC_SHA256:
        raise RuntimeError(
            f"checksum mismatch for {CRATE_URL}:\n"
            f"  expected {PAC_SHA256}\n  got      {digest}"
        )

    with tempfile.TemporaryDirectory() as td:
        tarball = Path(td) / "pac.crate"
        tarball.write_bytes(data)
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(td, filter="data")
        unpacked = Path(td) / f"{PAC_NAME}-{PAC_VERSION}"
        if not (unpacked / "src" / "generic.rs").is_file():
            raise RuntimeError(f"unexpected package layout under {unpacked}")
        shutil.move(str(unpacked), str(PAC_DIR))

    STAMP.write_text(PAC_VERSION + "\n")
    print(f"Provisioned {PAC_DIR}")
    return PAC_DIR


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true",
                    help="re-download and re-unpack even if already provisioned")
    args = ap.parse_args()
    print(provision(force=args.force))


if __name__ == "__main__":
    main()
