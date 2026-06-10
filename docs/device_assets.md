# Migrating device assets (PDFs + SVDs)

`.gitignore` excludes `devices/**/*.pdf` and `devices/**/*.svd`, so the ~2.4 GB of
datasheets and SVD files under `devices/` **do not travel with `git clone`**. To move
the repo to another server without losing them, they are bundled into
**per-manufacturer archives** published as **GitHub Release assets**, and restored on
the new machine from a committed manifest.

Two scripts, in `scripts/`:

| script | role |
|---|---|
| `pack_device_assets.py` | bundle every PDF/SVD into `dist/device_assets/<mfg>.tar.gz`, write `devices/ASSETS_MANIFEST.tsv`, and (optionally) upload to a GitHub Release |
| `unpack_device_assets.py` | download those archives from the release, extract them back into `devices/`, and verify every asset against the manifest's sha256 |

## What gets produced

- One archive per manufacturer: `stm.tar.gz`, `nxp.tar.gz`, `ti.tar.gz`, `intel.tar.gz`
  (~645 MB total compressed; STM is the bulk). Members are repo-root-relative, so they
  extract straight back to e.g. `devices/stm/rm0041/rm0041.pdf`.
- **Auto-split safety net:** GitHub caps a single release asset at 2 GB. If a
  manufacturer's built archive ever exceeds `--max-archive-mb` (default 1900) it is
  split into `<mfg>.part01.tar.gz`, `<mfg>.part02.tar.gz`, … instead — extract them all
  to restore that manufacturer. (STM currently fits in one file, so no split today.)
- `devices/ASSETS_MANIFEST.tsv` — **committed to git.** One row per asset (path, size,
  sha256, which archive holds it) plus one row per archive. This is the source of truth
  a fresh clone uses to know what should exist and to verify it.
- Archives live under `dist/` which is **gitignored** — they never get committed.

## Migrating to a new server

**On the old machine** (publish the assets once):

```bash
source .venv/bin/activate
python scripts/pack_device_assets.py --upload --tag device-assets
git add scripts/pack_device_assets.py scripts/unpack_device_assets.py \
        devices/ASSETS_MANIFEST.tsv docs/device_assets.md
git commit -m "device-assets: pack/unpack tooling + manifest"
git push
```

**On the new machine** (restore them):

```bash
git clone https://github.com/Ramla-I/hal_agent.git
cd hal_agent && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # or your usual setup
gh auth login                     # unpack downloads release assets via gh

python scripts/unpack_device_assets.py --tag device-assets
# -> downloads <mfg>.tar.gz from the release, extracts into devices/, verifies all 395 assets
```

That's it — every PDF/SVD is back in its original path, sha256-verified.

## Common operations

```bash
# rebuild + re-upload after adding/changing datasheets (only changed mfgs rebuild)
python scripts/pack_device_assets.py --upload

# work on one manufacturer only
python scripts/pack_device_assets.py --only stm --upload
python scripts/unpack_device_assets.py --only stm

# restore from archives already downloaded under dist/device_assets (no network)
python scripts/unpack_device_assets.py --no-download

# audit an existing checkout against the manifest (no download, no extract)
python scripts/unpack_device_assets.py --verify-only
```

## Notes

- **Incremental:** `pack` rebuilds a manufacturer only when its asset set or any file's
  sha256 changed since the last manifest. `--force` rebuilds everything.
- **Idempotent restore:** `unpack` skips any asset already present with the correct
  sha256; `--force` re-extracts. It exits non-zero if anything is missing or mismatched.
- **Already-tracked assets:** 174 PDFs + 26 SVDs were committed before the ignore rule
  and still live in git history, so they'd survive a clone anyway. The archives include
  them too (so each archive is a complete per-manufacturer set and the manifest covers
  100% of `devices/`), which is harmless redundancy.
- **Determinism:** archives normalize mtime/uid/gid, so an unchanged manufacturer packs
  to byte-identical output across runs.
- **Requirements:** `gh` (authenticated) for upload/download; PyMuPDF etc. are not
  needed by these scripts — only the Python stdlib.
```
