#!/usr/bin/env python3
"""dependent_scan.py -- scan every crates.io dependent's OWN source.

The compile probe (dependent_compile.py) demands the swept driver
generation, because a compile against a different generation measures
nothing. The SCANNER has no such constraint: a project's own register
accesses are readable at any pin. So this runs scan_projects' extractor
over every normal dependent in the census -- sourced from the published
crates.io package, the version of record, not a git HEAD -- with the chip
and manual read from each dependent's own manifest, never hand-entered.

What it answers: which dependents touch constrained registers in their own
source (PORT CANDIDATES -- a version gap is an afternoon when the yield
justifies it, see hubris), and which route every access through the HAL
(nothing of their own to measure; the HAL rows already cover them).

Dependents already in scan_projects' PROJECTS or EXCLUDED are skipped here
-- they are recorded there. A dependent whose chip maps to no corpus manual
is recorded with reason `missing-manual`, because a name absent from the
report is indistinguishable from one that scanned clean.

Usage:
    python applications/pac_codegen/experiments/dependent_scan.py
    python applications/pac_codegen/experiments/dependent_scan.py --only NAME
"""

import argparse
import io
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

try:
    import tomllib
except ImportError:                                        # pragma: no cover
    tomllib = None

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "experiments"))
import rust_codegen                                        # noqa: E402
import scan_projects                                       # noqa: E402
import stm_sweep                                           # noqa: E402

OUT = APP_DIR / "experiments" / "out"
CENSUS = APP_DIR / "experiments" / "hal_dependents_census.json"
UA = {"User-Agent": "hal_agent dependent_scan (research; see repo)"}

PAC_CRATES = {p.name for p in (APP_DIR / "vendored" / "pac").iterdir()
              if p.is_dir()} if (APP_DIR / "vendored" / "pac").is_dir() else set()
HAL_CRATES = {"stm32f4xx-hal", "stm32-hal2", "stm32f1xx-hal", "stm32g4xx-hal",
              "stm32-hrtim", "stm32f1-hal", "stm32l151-hal", "stm32f7xx-hal",
              "stm32h7xx-hal", "stm32l4xx-hal", "stm32f0xx-hal",
              "stm32g0xx-hal", "stm32l0xx-hal", "stm32f3xx-hal"}


def _get(url: str, raw: bool = False):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA))
    return r.read() if raw else json.load(r)


def device_map() -> dict:
    """chip token (device name minus `stm32`) -> (rm, device, pac crate),
    from the sweep's own TARGETS table -- the one list that already knows
    which devices the corpus covers."""
    out = {}
    for t in stm_sweep.TARGETS:
        out[t.device.removeprefix("stm32")] = (t.rm, t.device, t.pac)
    return out


DEVICES = device_map()
RM_INDEX = {rm: (dev, pac) for tok, (rm, dev, pac) in DEVICES.items()}

# Chip-catalog knowledge: which manual governs an order code the TARGETS
# list spells differently. `h743v` and `h7x3` are RM0433 parts as surely as
# the corpus device `h753` is; a prefix matcher cannot know that, and the
# first scan pass skipped stabilizer, thermostat-eem, the Daisy audio
# platform and a flight controller over exactly these spellings. Order
# codes are catalogue facts, not measurements -- this table is the one
# hand-entered thing here, and it only maps into manuals the corpus has.
import re as _re
FAMILY_RM = [
    (r"h7[45]3|h750|h742", "rm0433"),
    (r"h7[45][57]", "rm0399"),
    (r"h7a3|h7b[03]", "rm0455"),
    (r"h72[35]|h73[05]", "rm0468"),
    (r"f4[01][57]|f4[23][79]", "rm0090"),
    (r"f10[57]", "rm0008"),
    (r"l4x2|l4[1-4]\d", "rm0394"),
    (r"l4[5-9]\d|l4x[36]", "rm0351"),
    (r"f7[45]\d|f7x6", "rm0385"),
    (r"f7[67]\d|f7x7", "rm0410"),
    (r"f7[23]\d", "rm0431"),
    (r"f0[357]0", "rm0360"),
    (r"f0[4-9][128]|f0x[128]", "rm0091"),
    (r"g0[34]1", "rm0444"),
]


def resolve_token(tok: str):
    """(rm, device, pac) for a chip token, or None."""
    for dev_tok, rd in DEVICES.items():
        if tok.startswith(dev_tok) or dev_tok.startswith(tok):
            return rd
    base = tok.rstrip("v")          # h743v, h750v: package variant suffix
    for dev_tok, rd in DEVICES.items():
        if base.startswith(dev_tok) or dev_tok.startswith(base):
            return rd
    for pat, rm in FAMILY_RM:
        if _re.fullmatch(pat, base) and rm in RM_INDEX:
            dev, pac = RM_INDEX[rm]
            return (rm, dev, pac)
    return None


def chips_from_manifest(root: Path) -> tuple:
    """(matched {token: (rm, device, pac)}, unmatched tokens, style, deps).

    Chip identity comes from the FEATURES the dependent enables on its PAC
    or HAL dependencies: `stm32f4xx-hal = {features = ["stm32f469", ..]}`
    names the chip as surely as a datasheet order code."""
    man = root / "Cargo.toml"
    if not (tomllib and man.is_file()):
        return {}, [], "hal_only", []
    data = tomllib.loads(man.read_text())
    deps = {}
    for sect in ("dependencies", "build-dependencies"):
        for name, spec in (data.get(sect) or {}).items():
            real = spec.get("package", name) if isinstance(spec, dict) else name
            feats = spec.get("features", []) if isinstance(spec, dict) else []
            deps[real] = feats
    style = "pac_direct" if PAC_CRATES & set(deps) else "hal_only"
    tokens = set()
    for name, feats in deps.items():
        if name in PAC_CRATES or name in HAL_CRATES:
            for f in feats:
                tokens.add(str(f).lower().removeprefix("stm32"))
    matched, unmatched = {}, []
    for tok in sorted(tokens):
        hit = resolve_token(tok)
        if hit:
            matched[tok] = hit
        else:
            unmatched.append(tok)
    return matched, unmatched, style, sorted(deps)


def refresh_census() -> None:
    """Rebuild hal_dependents_census.json from crates.io: reverse dependents
    of the six swept HALs AND of every vendored family PAC. The first census
    was HALs-only and hand-run; the PAC dependents (blue_hal, rustuino,
    openmv_h7_bsp, ...) existed only in a conversation. A census that cannot
    be regenerated is a census that rots."""
    import time

    def get_retry(url):
        # crates.io asks for ~1 req/s; a 429 mid-crawl silently DROPPED six
        # subjects on the first run, and because the rebuild replaced the
        # file wholesale, their old entries went with them.
        for pause in (0, 10, 30):
            time.sleep(pause)
            try:
                return _get(url)
            except Exception as e:                          # noqa: BLE001
                err = e
        raise err

    subjects = sorted(HAL_CRATES) + sorted(PAC_CRATES)
    out = {}
    for crate in subjects:
        try:
            d = get_retry(f"https://crates.io/api/v1/crates/{crate}"
                          f"/reverse_dependencies?per_page=100")
        except Exception as e:                              # noqa: BLE001
            print(f"{crate}: FAILED after retries ({e}); keeping old entry")
            continue
        vers = {v["id"]: v["crate"] for v in d.get("versions", [])}
        deps = {}
        for dep in d.get("dependencies", []):
            n = vers.get(dep["version_id"])
            if n:
                deps.setdefault(n, dep["req"])
        entry = {}
        for name, req in sorted(deps.items()):
            kind = "err"
            try:
                c = get_retry(f"https://crates.io/api/v1/crates/{name}")["crate"]
                v = c["max_stable_version"] or c["max_version"]
                dd = get_retry(f"https://crates.io/api/v1/crates/{name}/{v}"
                               f"/dependencies")["dependencies"]
                kind = {x["crate_id"]: x["kind"] for x in dd}.get(crate, "gone")
            except Exception:                               # noqa: BLE001
                pass
            entry[name] = [req, kind]
            time.sleep(1.0)
        if entry:
            out[crate] = entry
        print(f"{crate}: {len(entry)} dependents", flush=True)
    old = json.loads(CENSUS.read_text()) if CENSUS.is_file() else {}
    # Merge over the old census: a subject that failed this crawl keeps its
    # previous entry rather than vanishing.
    for k, v in old.items():
        if k != "_meta" and k not in out:
            out[k] = v
    meta = old.get("_meta", {})
    meta["method"] = ("crates.io /reverse_dependencies per swept driver AND "
                      "per vendored family PAC, then each dependent's "
                      "latest-version /dependencies for kind and requirement; "
                      "regenerate with dependent_scan.py --refresh-census")
    out["_meta"] = meta
    CENSUS.write_text(json.dumps(out, indent=1) + "\n")
    print(f"census: {CENSUS} ({sum(len(v) for k, v in out.items() if k != '_meta')} rows)")


def fetch(name: str, work: Path) -> tuple:
    import time

    def get(url, raw=False):
        # crates.io asks for ~1 req/s and answers a burst with 429s; one
        # unpaced run turned 91 dependents into 91 fetch-failure rows.
        for pause in (1, 15, 45):
            time.sleep(pause)
            try:
                return _get(url, raw=raw)
            except Exception as e:                          # noqa: BLE001
                err = e
        raise err

    c = get(f"https://crates.io/api/v1/crates/{name}")["crate"]
    version = c["max_stable_version"] or c["max_version"]
    blob = get(f"https://static.crates.io/crates/{name}/{name}-{version}.crate",
               raw=True)
    tf = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
    tf.extractall(work, filter="data")
    return work / f"{name}-{version}", version, c.get("repository") or ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--refresh-census", action="store_true",
                    help="rebuild hal_dependents_census.json from crates.io "
                         "(HALs + all vendored family PACs), then exit")
    args = ap.parse_args()
    if args.refresh_census:
        refresh_census()
        return

    census = json.loads(CENSUS.read_text())
    census.pop("_meta", None)
    # PROJECTS/EXCLUDED are recorded in the main scan; the swept HALs and
    # the PAC crates appear in the census as each other's dependents but are
    # measurement SUBJECTS here, not downstream of one.
    already = ({p.name for p in scan_projects.PROJECTS}
               | set(scan_projects.EXCLUDED) | HAL_CRATES | PAC_CRATES)
    dependents = {}
    for hal, deps in census.items():
        for name, (req, kind) in deps.items():
            if kind != "normal" or name in already:
                continue
            dependents.setdefault(name, []).append(f"{hal} {req}")
    if args.only:
        dependents = {n: v for n, v in dependents.items() if n in args.only}

    periph_maps, results = {}, []
    tmp = Path(tempfile.mkdtemp(prefix="dependent_scan_"))
    try:
        for name in sorted(dependents):
            print(f"\n=== {name} ===", flush=True)
            try:
                root, version, repo = fetch(name, tmp / name)
            except Exception as e:                          # noqa: BLE001
                results.append({"name": name, "skip": f"fetch failed: {e}",
                                "pins": dependents[name]})
                print(f"  SKIP: fetch failed: {e}")
                continue
            matched, unmatched, style, deps = chips_from_manifest(root)
            if not matched:
                why = ("missing-manual" if unmatched else
                       "no chip feature in manifest")
                results.append({"name": name, "version": version,
                                "repo": repo, "skip": why,
                                "chips_unmatched": unmatched,
                                "style": style, "pins": dependents[name]})
                print(f"  SKIP: {why} (features: {unmatched or '-'})")
                continue
            # One scan per matched FAMILY; cross-family matching is unsound.
            by_family = {}
            for tok, (rm, device, pac) in matched.items():
                by_family.setdefault(pac, (rm, device))
            for pac, (rm, device) in sorted(by_family.items()):
                if pac not in periph_maps:
                    d = APP_DIR / "vendored" / "pac" / pac / "src" / device
                    periph_maps[pac] = (rust_codegen.peripheral_instance_map(d)
                                        if d.is_dir() else {})
                p = scan_projects.Project(
                    name=name if len(by_family) == 1 else f"{name}@{device}",
                    repo=f"https://crates.io/crates/{name}",
                    style=style, rms=[rm], device=device, pac=pac,
                    note=f"crates.io dependent ({', '.join(dependents[name])})")
                r = scan_projects.scan_project(p, root, periph_maps[pac])
                r["version"] = version
                r["pins"] = dependents[name]
                r["source_repo"] = repo
                results.append(r)
                print(f"  [{rm}/{device}] {r['rust_files']} files | "
                      f"{r['register_accesses']} accesses | "
                      f"HITS {r['hits']} {r['verdicts']}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "dependent_scan.json"
    if out.is_file():
        # ALWAYS merge, and a fetch failure never replaces a real result --
        # one rate-limited run replaced 36 scanned rows with 91 "fetch
        # failed" rows because the full-run branch wrote wholesale.
        existing = {r["name"]: r for r in json.loads(out.read_text())}
        merged = dict(existing)
        for r in results:
            prev = merged.get(r["name"])
            if (str(r.get("skip", "")).startswith("fetch failed")
                    and prev is not None
                    and not str(prev.get("skip", "")).startswith("fetch")):
                continue
            merged[r["name"]] = r
        # A multi-family crate scans under `name@device` rows; its bare-name
        # fetch-failure row from an earlier run is then obsolete, not
        # unresolved -- without this, four resolved crates kept wearing
        # "fetch failed" next to their own results.
        for n in list(merged):
            if (str(merged[n].get("skip", "")).startswith("fetch failed")
                    and any(m.startswith(n + "@") for m in merged)):
                del merged[n]
        results = sorted(merged.values(), key=lambda r: r["name"])
    out.write_text(json.dumps(results, indent=1, default=str) + "\n")

    scanned = [r for r in results if "skip" not in r]
    hot = sorted((r for r in scanned if r["hits"]),
                 key=lambda r: -r["hits"])
    print(f"\n{'='*60}\n{len(results)} dependents recorded: "
          f"{len(scanned)} scanned, {len(results)-len(scanned)} skipped "
          f"with reason, {len(hot)} with hits on constrained registers")
    for r in hot:
        print(f"  {r['name']} {r.get('version','')}: {r['hits']} hits "
              f"{r['verdicts']} | {r['register_accesses']} accesses | "
              f"pins {', '.join(r['pins'])}")
    print(f"\njson: {out}")


if __name__ == "__main__":
    main()
