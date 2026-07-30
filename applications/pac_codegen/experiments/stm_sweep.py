#!/usr/bin/env python3
"""STM-wide injection sweep: every reference manual with validated constraints,
injected into its PAC crate, then compiled -- probe crate and (where a released
HAL pairs with the PAC) the real third-party HAL.

This generalizes experiments/cross_pac.py from four hand-picked fixtures to the
whole corpus, and swaps the fixture for the real pipeline artifact: each target
runs ``inject_from_run.py`` over the RM's generator run directory, gated on the
constraint validator (``--validated``) and re-verified against the chunked
datasheet (``--chunks``).

Per target:
    provision -> snapshot -> inject_from_run -> [probe check] -> [HAL check]
    -> restore -> verify the PAC tree byte-for-byte pristine.

The PAC tree is snapshotted BEFORE injection and restored even when a step
fails, so targets sharing a crate (four RMs share stm32f3) never contaminate
each other.

Usage:
    python applications/pac_codegen/experiments/stm_sweep.py --dry-run
    python applications/pac_codegen/experiments/stm_sweep.py --only rm0316
    python applications/pac_codegen/experiments/stm_sweep.py --skip-hal
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent          # applications/pac_codegen
REPO = APP_DIR.parent.parent
sys.path.insert(0, str(APP_DIR))
import get_pac  # noqa: E402

INJECT = APP_DIR / "inject_from_run.py"
OUT = APP_DIR / "experiments" / "out"
PAC_VERSION = "0.16.0"
STEP_TIMEOUT = 1800

# Where the STM pipeline run lives (gitignored outputs in a sibling worktree).
DATA = Path("/home/ramla/hal_agent-phase-1d")


@dataclass
class Target:
    rm: str
    pac: str            # crates.io PAC package
    device: str         # device module inside the PAC == cargo feature
    svd: str            # SVD basename for the collection lint
    hal: str | None = None       # HAL crate that pairs with PAC 0.16.0
    hal_version: str | None = None
    hal_features: list[str] = field(default_factory=list)

    @property
    def run_dir(self) -> Path:
        return DATA / f"agent_output/stm/{self.rm}/1"

    @property
    def svd_path(self) -> Path:
        return DATA / f"devices/stm/{self.rm}/svd/{self.svd}"

    @property
    def validated(self) -> Path:
        p = DATA / f"evaluation/stm/{self.rm}/1/{self.rm}_constraints_review.jsonl"
        return p if p.is_file() else (
            DATA / f"agent_output/stm/{self.rm}/1/constraint_validation/validated.jsonl")

    @property
    def chunks(self) -> Path:
        return DATA / "chunked_datasheets/stm"


# One device module per RM: the RM's primary chip, preferring one a paired HAL
# can select. (An RM projects onto several chips; injection is per device
# module, and generic.rs is patched crate-wide, so one at a time.)
TARGETS = [
    Target("rm0008", "stm32f1", "stm32f103", "stm32f103.svd",
           hal="stm32f1xx-hal", hal_version="0.11.0",
           hal_features=["stm32f103", "medium"]),
    Target("rm0033", "stm32f2", "stm32f215", "stm32f215.svd"),
    Target("rm0038", "stm32l1", "stm32l151", "stm32l151.svd"),
    Target("rm0091", "stm32f0", "stm32f0x1", "stm32f0x1.svd"),
    Target("rm0313", "stm32f3", "stm32f373", "stm32f373.svd"),
    Target("rm0316", "stm32f3", "stm32f303", "stm32f303.svd"),
    Target("rm0360", "stm32f0", "stm32f0x0", "stm32f0x0.svd"),
    Target("rm0365", "stm32f3", "stm32f302", "stm32f302.svd"),
    Target("rm0366", "stm32f3", "stm32f301", "stm32f301.svd"),
    Target("rm0367", "stm32l0", "stm32l0x3", "stm32l0x3.svd"),
    Target("rm0368", "stm32f4", "stm32f401", "stm32f401.svd",
           hal="stm32f4xx-hal", hal_version="0.23.0",
           hal_features=["stm32f401"]),
    Target("rm0376", "stm32l0", "stm32l0x2", "stm32l0x2.svd"),
    Target("rm0377", "stm32l0", "stm32l0x1", "stm32l0x1.svd"),
]


# --------------------------------------------------------------------------- #
# Snapshot / restore  (same contract as experiments/cross_pac.py)
# --------------------------------------------------------------------------- #

class PacSnapshot:
    def __init__(self, pac_root: Path, device: str):
        src = pac_root / "src"
        self.base = pac_root
        self.paths = [src / "generic.rs", src / device]
        self._tmp = tempfile.TemporaryDirectory(prefix="stm_sweep_snap_")
        self.digest = self._digest()
        for i, p in enumerate(self.paths):
            dst = Path(self._tmp.name) / str(i)
            shutil.copy2(p, dst) if p.is_file() else shutil.copytree(p, dst)

    def _digest(self) -> str:
        h = hashlib.sha256()
        for root in self.paths:
            files = [root] if root.is_file() else sorted(root.rglob("*"))
            for f in files:
                if f.is_file():
                    h.update(str(f.relative_to(self.base)).encode())
                    h.update(f.read_bytes())
        return h.hexdigest()

    def restore_and_verify(self) -> bool:
        for i, p in enumerate(self.paths):
            saved = Path(self._tmp.name) / str(i)
            if saved.is_file():
                shutil.copy2(saved, p)
            else:
                shutil.rmtree(p)
                shutil.copytree(saved, p)
        ok = self._digest() == self.digest
        self._tmp.cleanup()
        return ok


# --------------------------------------------------------------------------- #
# Steps
# --------------------------------------------------------------------------- #

def run_inject(t: Target, pac_dir: Path, report: Path, dry: bool) -> subprocess.CompletedProcess:
    argv = [
        sys.executable, str(INJECT), str(t.run_dir),
        "--pac", str(pac_dir), "--device", t.device,
        "--svd-dir", str(t.svd_path),
        "--validated", str(t.validated),
        "--chunks", str(t.chunks),
        "--report", str(report),
        # NOTE: --save-constraints writes even under --dry-run, so this must
        # never point at the committed applications/pac_codegen/constraints/
        # tree; the sweep's artifacts stay in the gitignored out/ dir.
        "--save-constraints", str(OUT / "constraints" / f"{t.rm}_{t.device}.json"),
    ]
    if dry:
        argv.append("--dry-run")
    return subprocess.run(argv, capture_output=True, text=True,
                          timeout=STEP_TIMEOUT, cwd=str(REPO))


def cargo_check(workdir: Path, extra=None):
    try:
        return subprocess.run(["cargo", "check"] + (extra or []), cwd=str(workdir),
                              capture_output=True, text=True, timeout=STEP_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None


_PROBE_LIB = """\
//! Compiling this crate against the injected PAC is the experiment: it names
//! no constrained register, so it must keep building exactly as before.
#![no_std]
pub use {crate_ident}::{device} as device;
"""


def probe_check(t: Target, pac_dir: Path) -> tuple[str, str]:
    """A minimal downstream crate that merely depends on the injected device
    module. It must still compile: injection must not break the PAC itself."""
    ws = Path(tempfile.mkdtemp(prefix=f"stm_sweep_{t.rm}_"))
    (ws / "src").mkdir()
    (ws / "Cargo.toml").write_text(
        "[package]\n"
        f'name = "probe-{t.rm}"\nversion = "0.1.0"\nedition = "2021"\n\n'
        "[dependencies]\n"
        f'{t.pac} = {{ path = "{pac_dir}", features = ["{t.device}"] }}\n')
    (ws / "src" / "lib.rs").write_text(
        _PROBE_LIB.format(crate_ident=t.pac.replace("-", "_"), device=t.device))
    run = cargo_check(ws)
    if run is None:
        return "TIMEOUT", str(ws)
    if run.returncode == 0:
        shutil.rmtree(ws, ignore_errors=True)
        return "PASS", ""
    return "FAIL", str(ws) + "\n" + run.stderr[-3000:]


def hal_workspace(t: Target, pac_dir: Path) -> Path:
    ws = Path(tempfile.mkdtemp(prefix=f"stm_sweep_hal_{t.rm}_"))
    (ws / "src").mkdir()
    (ws / "src" / "lib.rs").write_text(
        "//! Compiling this crate compiles the UNMODIFIED HAL against the\n"
        "//! locally patched PAC. The build itself is the experiment.\n"
        "#![no_std]\n"
        f"pub use {t.hal.replace('-', '_')} as hal;\n")
    feats = ", ".join(f'"{f}"' for f in t.hal_features)
    (ws / "Cargo.toml").write_text(
        "[package]\n"
        f'name = "hal-eval-{t.rm}"\nversion = "0.1.0"\nedition = "2021"\n\n'
        "[dependencies]\n"
        f'{t.hal} = {{ version = "={t.hal_version}", features = [{feats}] }}\n\n'
        "[patch.crates-io]\n"
        f'{t.pac} = {{ path = "{pac_dir}" }}\n')
    return ws


def hal_errors(ws: Path, hal_dirname: str):
    """cargo check --message-format=json -> error diagnostics with the HAL
    source files attributed (primary spans + macro expansions)."""
    run = cargo_check(ws, ["--message-format=json"])
    if run is None:
        return None
    out = []
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
        files: set[str] = set()

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
        out.append({"code": (d.get("code") or {}).get("code", ""),
                    "message": d.get("message", ""), "hal_files": sorted(files)})
    return out


def classify(errors, gated_specs: set[str]) -> dict:
    """Split HAL errors into: TRUE ENFORCEMENT (our diagnostic naming a register
    we actually gated), GENERIC FRICTION (our diagnostic in generic code that
    never names a gated register), OTHER (anything else -- collateral damage)."""
    res = {"true_enforcement": 0, "generic_friction": 0, "other": 0,
           "files": {"true_enforcement": set(), "generic_friction": set(),
                     "other": set()},
           "specs": {}, "samples": {"true_enforcement": [],
                                    "generic_friction": [], "other": []},
           "other_detail": []}

    def sample(bucket: str, e):
        # Keep verbatim diagnostics: the enforcement/friction split is the
        # whole adoption claim, so it has to be checkable, not just counted.
        if len(res["samples"][bucket]) < 4:
            res["samples"][bucket].append(
                {"code": e["code"], "message": e["message"][:400],
                 "files": e["hal_files"]})

    for e in errors:
        witness = (e["code"] == "E0277"
                   and "constrained by its datasheet" in e["message"])
        named = [s for s in gated_specs if s in e["message"]]
        if witness and named:
            res["true_enforcement"] += 1
            res["files"]["true_enforcement"] |= set(e["hal_files"])
            for s in named:
                res["specs"][s] = res["specs"].get(s, 0) + 1
            sample("true_enforcement", e)
        elif witness:
            res["generic_friction"] += 1
            res["files"]["generic_friction"] |= set(e["hal_files"])
            sample("generic_friction", e)
        else:
            res["other"] += 1
            res["files"]["other"] |= set(e["hal_files"])
            sample("other", e)
            if len(res["other_detail"]) < 12:
                res["other_detail"].append(
                    f"{e['code']} {e['message'][:150]} @ {e['hal_files']}")
    res["files"] = {k: sorted(v) for k, v in res["files"].items()}
    return res


# --------------------------------------------------------------------------- #
# One target
# --------------------------------------------------------------------------- #

def run_target(t: Target, dry: bool, skip_hal: bool, hal_baseline_cache: dict) -> dict:
    res = {"rm": t.rm, "pac": t.pac, "device": t.device, "hal": t.hal,
           "inject": "?", "planned": 0, "fates": {}, "gated_specs": [],
           "probe": "-", "hal_result": None, "pristine": None, "detail": []}
    print(f"\n=== {t.rm} -> {t.pac} 0.16.0 / {t.device} ===")
    if not t.run_dir.is_dir():
        res["inject"] = "NO DATA"
        print(f"  no run dir: {t.run_dir}")
        return res

    pac_dir = get_pac.provision(crate=t.pac, version=PAC_VERSION)
    OUT.mkdir(parents=True, exist_ok=True)
    report = OUT / f"{t.rm}_{t.device}{'_dry' if dry else ''}.json"

    snap = None if dry else PacSnapshot(pac_dir, t.device)
    try:
        run = run_inject(t, pac_dir, report, dry)
        if run.returncode != 0:
            res["inject"] = "FAILED"
            res["detail"].append((run.stderr or run.stdout)[-4000:])
            print(f"  injection FAILED (exit {run.returncode})")
            print("  " + (run.stderr or run.stdout).strip()[-1500:].replace("\n", "\n  "))
            return res
        res["inject"] = "dry-run ok" if dry else "ok"
        summary = json.loads(report.read_text())
        res["planned"] = summary["registers_planned"]
        res["fates"] = summary["fates"]
        specs = set()
        for row in summary["rows"]:
            if row["fate"] == "planned":
                specs.add(f"{row['register'].upper()}rs")
        res["gated_specs"] = sorted(specs)
        print(f"  registers planned: {res['planned']}   fates: {res['fates']}")
        if dry:
            return res

        res["probe"], detail = probe_check(t, pac_dir)
        print(f"  probe crate: {res['probe']}")
        if detail:
            res["detail"].append("probe:\n" + detail)

        if t.hal and not skip_hal:
            ws = hal_workspace(t, pac_dir)
            hal_dirname = f"{t.hal}-{t.hal_version}"
            base = hal_baseline_cache.get(t.rm)
            errors = hal_errors(ws, hal_dirname)
            res["hal_result"] = {"baseline": base, "workspace": str(ws)}
            if errors is None:
                res["hal_result"]["status"] = "TIMEOUT"
            else:
                res["hal_result"].update(classify(errors, set(res["gated_specs"])))
                res["hal_result"]["status"] = "ran"
                h = res["hal_result"]
                print(f"  HAL {t.hal} {t.hal_version}: "
                      f"true_enforcement={h['true_enforcement']} "
                      f"generic_friction={h['generic_friction']} other={h['other']}")
                print(f"    enforcement sites: {h['files']['true_enforcement']}")
                if h["other"]:
                    for d in h["other_detail"]:
                        print(f"    other: {d}")
        return res
    finally:
        if snap is not None:
            res["pristine"] = snap.restore_and_verify()
            print(f"  restored pristine: {res['pristine']}")
            if not res["pristine"]:
                print(f"  !! {t.pac} left non-pristine; re-provision with "
                      f"get_pac.py --crate {t.pac} --version {PAC_VERSION} --force",
                      file=sys.stderr)


def hal_baseline(t: Target) -> str:
    """The HAL must compile against the PRISTINE PAC, else the injected result
    means nothing."""
    pac_dir = get_pac.provision(crate=t.pac, version=PAC_VERSION)
    ws = hal_workspace(t, pac_dir)
    run = cargo_check(ws)
    shutil.rmtree(ws, ignore_errors=True)
    if run is None:
        return "TIMEOUT"
    return "PASS" if run.returncode == 0 else "FAIL"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=[],
                    help="run a single RM (repeatable)")
    ap.add_argument("--dry-run", action="store_true",
                    help="selection + planning only; never touch a PAC")
    ap.add_argument("--skip-hal", action="store_true")
    ap.add_argument("--out", default=None, help="write the JSON summary here")
    args = ap.parse_args()

    targets = [t for t in TARGETS if not args.only or t.rm in args.only]
    if not targets:
        sys.exit(f"no target matching {args.only}")
    if not args.dry_run and shutil.which("cargo") is None:
        sys.exit("cargo is required (use --dry-run to plan only)")

    baselines = {}
    if not args.dry_run and not args.skip_hal:
        for t in targets:
            if t.hal:
                print(f"baseline: {t.hal} {t.hal_version} vs pristine {t.pac} ...",
                      flush=True)
                baselines[t.rm] = hal_baseline(t)
                print(f"  {baselines[t.rm]}")

    results = [run_target(t, args.dry_run, args.skip_hal, baselines) for t in targets]

    print("\n\n## Summary\n")
    print("| RM | PAC | device | injection | registers gated | probe | HAL | "
          "true enforcement | generic friction | other | pristine |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        h = r["hal_result"] or {}
        print(f"| {r['rm']} | {r['pac']} | {r['device']} | {r['inject']} | "
              f"{r['planned']} | {r['probe']} | {r['hal'] or '—'} | "
              f"{h.get('true_enforcement', '—')} | {h.get('generic_friction', '—')} | "
              f"{h.get('other', '—')} | {r['pristine']} |")

    OUT.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else OUT / (
        "sweep_dry.json" if args.dry_run else "sweep.json")
    out.write_text(json.dumps(results, indent=1, default=str) + "\n")
    print(f"\nsummary: {out}")

    bad = [r for r in results if r["pristine"] is False]
    if bad:
        sys.exit("ERROR: a PAC tree was left non-pristine (see above)")


if __name__ == "__main__":
    main()
