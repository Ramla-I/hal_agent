#!/usr/bin/env python3
"""
unpack_device_assets.py — restore the device datasheet binaries (PDF + SVD) that
git does not carry, on a fresh clone / new server.

It reads the committed manifest (devices/ASSETS_MANIFEST.tsv), downloads the
per-manufacturer archives from a GitHub Release (or uses ones already on disk),
extracts them back into devices/, and verifies every asset against the manifest's
sha256. Built by `scripts/pack_device_assets.py`.

Usage
-----
  # full restore: download all archives from the release and extract + verify
  python scripts/unpack_device_assets.py --tag device-assets

  # restore only one manufacturer
  python scripts/unpack_device_assets.py --only stm

  # use archives already downloaded under dist/device_assets (no gh call)
  python scripts/unpack_device_assets.py --no-download

  # verify an existing checkout against the manifest without extracting anything
  python scripts/unpack_device_assets.py --verify-only

Exit status is non-zero if any expected asset ends up missing or sha-mismatched.
Idempotent: assets already present with the correct sha256 are left untouched
(pass --force to re-extract).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tarfile

DEFAULT_MANIFEST = "devices/ASSETS_MANIFEST.tsv"
DEFAULT_DIR = "dist/device_assets"


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256_file(path: str, _buf=1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_buf), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path: str):
    """Return (assets, archives): {asset_path:(archive,bytes,sha)}, {archive:(bytes,sha)}."""
    if not os.path.exists(path):
        sys.exit(f"manifest not found: {path}\n(run scripts/pack_device_assets.py first, "
                 f"or pass --manifest)")
    assets, archives = {}, {}
    with open(path) as f:
        if not f.readline().startswith("kind\t"):
            sys.exit(f"unrecognized manifest format: {path}")
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 5:
                continue
            kind, p, arc, size, sha = parts
            if kind == "asset":
                assets[p] = (arc, int(size), sha)
            elif kind == "archive":
                archives[p] = (int(size), sha)
    return assets, archives


def asset_ok(root: str, rel: str, sha: str) -> bool:
    p = os.path.join(root, rel)
    return os.path.exists(p) and sha256_file(p) == sha


def safe_extract(archive_path: str, root: str) -> None:
    """Extract a tar.gz into `root`, refusing any member that escapes it."""
    root_real = os.path.realpath(root)
    with tarfile.open(archive_path, "r:gz") as tar:
        members = tar.getmembers()
        for m in members:
            dest = os.path.realpath(os.path.join(root, m.name))
            if dest != root_real and not dest.startswith(root_real + os.sep):
                sys.exit(f"unsafe path in {os.path.basename(archive_path)}: {m.name}")
        try:
            tar.extractall(root, members=members, filter="data")  # py>=3.12
        except TypeError:
            tar.extractall(root, members=members)


def gh_download(tag: str, dest_dir: str, patterns: list[str]) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    cmd = ["gh", "release", "download", tag, "--dir", dest_dir, "--clobber"]
    for pat in patterns:
        cmd += ["--pattern", pat]
    print(f"downloading {', '.join(patterns)} from release {tag} ...")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(f"gh release download failed (tag {tag}). Is the release published and gh authed?")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default="device-assets", help="release tag to download from (default device-assets)")
    ap.add_argument("--dir", default=DEFAULT_DIR, help=f"where archives are downloaded to / read from (default {DEFAULT_DIR})")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST, help=f"manifest path (default {DEFAULT_MANIFEST})")
    ap.add_argument("--only", action="append", default=[], metavar="MFG",
                    help="restore only this manufacturer (repeatable), e.g. --only stm")
    ap.add_argument("--no-download", action="store_true", help="use archives already in --dir; do not call gh")
    ap.add_argument("--verify-only", action="store_true", help="only verify the checkout against the manifest")
    ap.add_argument("--force", action="store_true", help="re-extract even if assets are already present and correct")
    ap.add_argument("--no-verify", action="store_true", help="skip sha256 verification (faster, less safe)")
    args = ap.parse_args()

    root = repo_root()
    assets, archives = load_manifest(os.path.join(root, args.manifest))

    def selected(mfg_of: str) -> bool:
        return not args.only or mfg_of in args.only

    want_archives = sorted(
        a for a in archives if selected(a.split(".")[0])
    )
    if not want_archives:
        sys.exit("no archives matched --only " + ", ".join(args.only))
    want_assets = {p: v for p, v in assets.items() if v[0] in set(want_archives)}

    if args.verify_only:
        print(f"verifying {len(want_assets)} assets against {args.manifest} ...")
    else:
        dest_dir = os.path.join(root, args.dir)
        if not args.no_download:
            gh_download(args.tag, dest_dir, [f"{m}*.tar.gz" for m in (args.only or ["*"])])

        for arc in want_archives:
            arc_path = os.path.join(dest_dir, arc)
            arc_assets = [(p, sha) for p, (a, _s, sha) in want_assets.items() if a == arc]

            # idempotent: skip if everything this archive carries is already correct
            if not args.force and all(asset_ok(root, p, sha) for p, sha in arc_assets):
                print(f"  ok (present) {arc}")
                continue
            if not os.path.exists(arc_path):
                print(f"  MISSING archive {arc} — cannot restore {len(arc_assets)} assets "
                      f"(download it to {args.dir} or drop --no-download)")
                continue
            if not args.no_verify and arc in archives:
                want_sha = archives[arc][1]
                if sha256_file(arc_path) != want_sha:
                    sys.exit(f"  archive sha mismatch for {arc} — corrupt/incomplete download")
            print(f"  extracting {arc} ({len(arc_assets)} assets) ...")
            safe_extract(arc_path, root)

    # Final verification pass against the manifest.
    missing, mismatch = [], []
    for rel, (_arc, _size, sha) in sorted(want_assets.items()):
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            missing.append(rel)
        elif not args.no_verify and sha256_file(p) != sha:
            mismatch.append(rel)

    ok = len(want_assets) - len(missing) - len(mismatch)
    print(f"\n{ok}/{len(want_assets)} assets verified.", end="")
    print(f"  missing: {len(missing)}  mismatch: {len(mismatch)}")
    for rel in missing[:20]:
        print(f"  MISSING  {rel}")
    for rel in mismatch[:20]:
        print(f"  MISMATCH {rel}")
    if missing or mismatch:
        sys.exit(1)
    print("all device assets present and verified.")


if __name__ == "__main__":
    main()
