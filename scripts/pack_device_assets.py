#!/usr/bin/env python3
"""
pack_device_assets.py — bundle the device datasheet binaries (PDF + SVD/XML) into
per-manufacturer tar.gz archives and (optionally) publish them as GitHub Release
assets.

Why this exists
---------------
`.gitignore` excludes `devices/**/*.pdf`, `devices/**/*.svd` and `devices/**/*.xml`
(SVDs and device-mapping files), so ~2.4 GB of datasheets and register descriptions
do not travel with a `git clone`. Migrating the repo to a new server would silently
drop them. This tool packages every PDF/SVD/XML so they can be restored on the new
machine with `scripts/unpack_device_assets.py`. Gitignored intermediate dirs
(ddm/, chunks/, peripheral_pages_md/, other/) are skipped.

What it produces
----------------
  * One archive per manufacturer at  dist/device_assets/<mfg>.tar.gz
    Members are repo-root-relative (e.g. `devices/stm/rm0041/rm0041.pdf`) so the
    unpacker restores them to their exact original location.
  * AUTO-SPLIT (safety net): GitHub caps a single release asset at 2 GB. If a
    manufacturer's *built* archive exceeds --max-archive-mb (default 1900) it is
    instead split into standalone volumes `<mfg>.part01.tar.gz`, `...part02...`,
    each a complete tar.gz over a subset of files (extract them all to restore the
    manufacturer). Assets are bin-packed in path order so a device stays together.
  * A manifest at devices/ASSETS_MANIFEST.tsv (COMMITTED to git) recording, for
    every asset, its size + sha256 and which archive holds it, plus a row per
    archive. A fresh clone uses this to verify nothing is missing or corrupt.

Usage
-----
  # build all archives locally + (re)write the manifest (no upload)
  python scripts/pack_device_assets.py

  # build only one manufacturer (fast iteration / smoke test)
  python scripts/pack_device_assets.py --only ti

  # build everything AND publish to a GitHub Release
  python scripts/pack_device_assets.py --upload --tag device-assets

Incremental: a manufacturer is rebuilt only when its asset set or any asset's
content (sha256) changed since the last manifest. Use --force to rebuild all.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import re
import subprocess
import sys
import tarfile

ASSET_EXTS = (".pdf", ".svd", ".xml")
# Gitignored intermediate/generated dirs that may contain .xml but are NOT assets.
SKIP_DIRS = {"ddm", "chunks", "peripheral_pages_md", "other"}
DEFAULT_OUT = "dist/device_assets"
DEFAULT_MANIFEST = "devices/ASSETS_MANIFEST.tsv"
MANIFEST_HEADER = ["kind", "path", "archive", "bytes", "sha256"]


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256_file(path: str, _buf=1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_buf), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_assets(root: str) -> list[str]:
    """Repo-root-relative paths of every PDF/SVD/XML under devices/, sorted.

    Gitignored intermediate dirs (see SKIP_DIRS) are pruned so their generated
    .xml files never get packed."""
    out = []
    for dirpath, dirs, files in os.walk(os.path.join(root, "devices")):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.lower().endswith(ASSET_EXTS):
                out.append(os.path.relpath(os.path.join(dirpath, fn), root))
    return sorted(out)


def manufacturer(rel_path: str) -> str:
    """devices/<mfg>/<device>/... -> '<mfg>'."""
    return rel_path.split(os.sep)[1]


def bin_pack(members, mfg, cap_bytes):
    """Split one manufacturer's path-sorted (rel,size,sha) into raw-size <= cap_bytes
    volumes (used only when the single archive overflows). Returns [(name, members)]."""
    bins = [[]]
    used = 0
    for m in members:
        if bins[-1] and used + m[1] > cap_bytes:
            bins.append([])
            used = 0
        bins[-1].append(m)
        used += m[1]
    width = max(2, len(str(len(bins))))
    return [(f"{mfg}.part{str(i + 1).zfill(width)}.tar.gz", b) for i, b in enumerate(bins)]


def parse_manifest(path: str):
    """Return ({asset_path: (archive, bytes, sha256)}, {archive: (bytes, sha256)})."""
    assets, archives = {}, {}
    if not os.path.exists(path):
        return assets, archives
    with open(path) as f:
        if not f.readline().startswith("kind\t"):
            return assets, archives  # unknown format; treat as empty
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


def build_archive(root: str, out_path: str, members) -> tuple[int, str]:
    """Write a deterministic gzip-compressed tar of `members` (repo-relative paths) and
    return (size, sha256). mtime/uid/gid are normalized so re-runs are reproducible."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"
    with gzip.GzipFile(tmp, "wb", compresslevel=6, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w") as tar:
            for rel, _size, _sha in members:
                abs_path = os.path.join(root, rel)
                ti = tar.gettarinfo(abs_path, arcname=rel)
                ti.mtime = 0
                ti.uid = ti.gid = 0
                ti.uname = ti.gname = ""
                with open(abs_path, "rb") as f:
                    tar.addfile(ti, f)
    os.replace(tmp, out_path)
    return os.path.getsize(out_path), sha256_file(out_path)


def remove_mfg_archives(out_dir: str, mfg: str) -> None:
    """Delete any existing <mfg>.tar.gz / <mfg>.partNN.tar.gz so a rebuild can't leave
    a stale volume from a previous (e.g. split vs single) layout behind."""
    pat = re.compile(rf"^{re.escape(mfg)}(\.part\d+)?\.tar\.gz$")
    if os.path.isdir(out_dir):
        for fn in os.listdir(out_dir):
            if pat.match(fn):
                os.remove(os.path.join(out_dir, fn))


def write_manifest(path: str, asset_rows, archive_rows) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write("\t".join(MANIFEST_HEADER) + "\n")
        for p, arc, size, sha in asset_rows:
            f.write(f"asset\t{p}\t{arc}\t{size}\t{sha}\n")
        for arc, size, sha in archive_rows:
            f.write(f"archive\t{arc}\t\t{size}\t{sha}\n")
    os.replace(tmp, path)


def upload_release(out_dir: str, manifest: str, tag: str, title: str) -> None:
    archives = sorted(
        os.path.join(out_dir, fn) for fn in os.listdir(out_dir) if fn.endswith(".tar.gz")
    )
    if not archives:
        sys.exit("nothing to upload — no .tar.gz in " + out_dir)
    exists = subprocess.run(["gh", "release", "view", tag], capture_output=True).returncode == 0
    if not exists:
        print(f"creating release {tag} ...")
        subprocess.run(
            ["gh", "release", "create", tag, "--title", title, "--notes",
             "Device datasheet PDFs + SVDs kept out of git (too large). "
             "Restore with `python scripts/unpack_device_assets.py`."],
            check=True,
        )
    files = archives + [manifest]
    total = sum(os.path.getsize(f) for f in files) / 1e6
    print(f"uploading {len(files)} assets ({total:.0f} MB) to release {tag} (this can take a while) ...")
    subprocess.run(["gh", "release", "upload", tag, *files, "--clobber"], check=True)
    print("upload complete.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=DEFAULT_OUT, help=f"archive output dir (default {DEFAULT_OUT}, gitignored)")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST, help=f"manifest path (default {DEFAULT_MANIFEST})")
    ap.add_argument("--only", action="append", default=[], metavar="MFG",
                    help="build only this manufacturer (repeatable), e.g. --only stm")
    ap.add_argument("--max-archive-mb", type=int, default=1900,
                    help="split a manufacturer into volumes if its archive exceeds this (default 1900; <2 GB GitHub cap)")
    ap.add_argument("--force", action="store_true", help="rebuild every archive even if unchanged")
    ap.add_argument("--upload", action="store_true", help="publish archives + manifest to a GitHub Release")
    ap.add_argument("--tag", default="device-assets", help="release tag (default device-assets)")
    ap.add_argument("--title", default="Device assets (PDF + SVD)", help="release title")
    args = ap.parse_args()

    root = repo_root()
    out_dir = os.path.join(root, args.out)
    manifest_path = os.path.join(root, args.manifest)
    cap = args.max_archive_mb * 1_000_000

    assets = discover_assets(root)
    if not assets:
        sys.exit("no PDF/SVD found under devices/")

    # Group assets by manufacturer, computing each asset's sha256 once.
    by_mfg: dict[str, list[tuple[str, int, str]]] = {}
    print(f"hashing {len(assets)} assets ...")
    for rel in assets:
        mfg = manufacturer(rel)
        if args.only and mfg not in args.only:
            continue
        size = os.path.getsize(os.path.join(root, rel))
        by_mfg.setdefault(mfg, []).append((rel, size, sha256_file(os.path.join(root, rel))))

    if not by_mfg:
        sys.exit("no manufacturers matched --only " + ", ".join(args.only))

    prev_assets, prev_archives = parse_manifest(manifest_path)

    asset_rows, archive_rows = [], []
    built = reused = 0
    for mfg in sorted(by_mfg):
        members = sorted(by_mfg[mfg])
        prev_m = {p: v for p, v in prev_assets.items() if manufacturer(p) == mfg}
        prev_arcs = {v[0] for v in prev_m.values()}

        # Reuse the whole manufacturer if its asset set + content is unchanged and every
        # archive file it maps to is still on disk.
        reuse = (
            not args.force
            and set(prev_m) == {rel for rel, _, _ in members}
            and all(prev_m[rel] == (prev_m[rel][0], size, sha) for rel, size, sha in members)
            and all(os.path.exists(os.path.join(out_dir, a)) for a in prev_arcs)
        )
        if reuse:
            for rel, size, sha in members:
                asset_rows.append((rel, prev_m[rel][0], size, sha))
            for a in prev_arcs:
                archive_rows.append((a, prev_archives[a][0], prev_archives[a][1]))
            reused += len(prev_arcs)
            continue

        # Rebuild: try a single archive; split only if it overflows the cap.
        remove_mfg_archives(out_dir, mfg)
        single = f"{mfg}.tar.gz"
        size, sha = build_archive(root, os.path.join(out_dir, single), members)
        if size <= cap:
            volumes = [(single, members, size, sha)]
        else:
            os.remove(os.path.join(out_dir, single))
            volumes = []
            for name, mem in bin_pack(members, mfg, cap):
                vs, vsha = build_archive(root, os.path.join(out_dir, name), mem)
                volumes.append((name, mem, vs, vsha))

        for name, mem, vs, vsha in volumes:
            print(f"  built {name}  ({vs / 1e6:.1f} MB, {len(mem)} files)")
            for rel, m_size, m_sha in mem:
                asset_rows.append((rel, name, m_size, m_sha))
            archive_rows.append((name, vs, vsha))
        built += len(volumes)

    # When building a subset (--only), preserve manifest rows for untouched manufacturers.
    if args.only:
        for p, (arc, size, sha) in prev_assets.items():
            if manufacturer(p) not in args.only:
                asset_rows.append((p, arc, size, sha))
        kept = {a for a, *_ in asset_rows}
        for arc, (size, sha) in prev_archives.items():
            if arc in kept and arc not in {r[0] for r in archive_rows}:
                archive_rows.append((arc, size, sha))

    asset_rows.sort()
    archive_rows.sort()
    write_manifest(manifest_path, asset_rows, archive_rows)
    print(f"\n{built} built, {reused} reused.  {len(asset_rows)} assets across "
          f"{len(archive_rows)} archives.\nmanifest: {os.path.relpath(manifest_path, root)}")

    if args.upload:
        upload_release(out_dir, manifest_path, args.tag, args.title)
    else:
        print("\n(local only — pass --upload to publish to a GitHub Release)")


if __name__ == "__main__":
    main()
