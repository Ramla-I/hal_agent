#!/usr/bin/env python3
"""dependent_compile.py -- do the HAL's bug sites ship in its dependents?

THE QUESTION
------------
The sweep finds candidate bug sites inside driver crates. bug_review.csv
records them. What none of that says is who DOWNSTREAM compiles those sites:
a violation in a HAL nobody depends on is a weaker finding than the same
violation shipping inside every dependent build.

The population is the crates.io reverse-dependents of the swept HALs,
filtered to crates that (a) carry the HAL as a normal, non-example
dependency and (b) pin the GENERATION WE SWEPT -- a crate pinning
stm32f4xx-hal 0.8 contains none of the 0.23 code we measured, so "impact"
would be a version join. The 2026-09 census (91 dependents, 49 normal)
leaves exactly three measurable crates, one per buggy HAL:

  stm32f469i-disc 0.3.1   stm32f4xx-hal 0.23 (stm32f469 -> RM0386)
  semtech_radios  0.1.6   stm32-hal2 2.1 (g474 -> RM0440)
  embassy-stm32   0.6.0   stm32-hrtim 0.2 -- the surprise. embassy's own
      register blocks can never be gated, but its G474/G484/F334 chip
      features auto-enable stm32-hrtim, and stm32-hrtim/stm32g474 is the
      stm32-rs PAC backend: `stm32g4 = 0.16.0`, the exact crate we inject.
      Every embassy build for those chips compiles the pairing the sweep
      measured. (F334's manual, RM0364, is outside the corpus; G474 is in.)

hsm-rs (stm32f4xx-hal ^0.23) is NOT here: its HAL dependency is optional
and pulled only by its `blinky-example` feature -- the library is HAL-free,
so it is a dependent of the HAL's examples, not of the HAL.

METHOD (port_blackpill's flow, generalized)
------------------------------------------
A probe crate that depends on the dependent from crates.io, with the PAC
[patch]ed to a private copy. Baseline against the pristine copy must PASS
and the patch must be proven applied in Cargo.lock (cargo does not fail an
unapplied [patch]). Then inject and recompile: every gate that fires is a
sweep site that THIS dependent's build actually contains, attributed to the
layer (registry crate) it fired in and triaged with the same static
corroboration pass as everything else.

Because a bare probe instantiates no generics, gates that fire here are in
code the dependent compiles UNCONDITIONALLY -- a floor, not a ceiling: a
real firmware instantiating generic entry points can only add sites.

A crate's own examples/bins DO instantiate the HAL, so `--examples` builds those
(a ceiling) instead of the bare probe (floor). Both paths bake in the
`patch_applied` guard: an unused [patch] (e.g. stm32f4xx-hal 0.22 pulls
`stm32f4-staging`, not `stm32f4`) reports UNMEASURED, never a silent false 0.

Usage:
    python applications/pac_codegen/experiments/dependent_compile.py --work DIR
    python applications/pac_codegen/experiments/dependent_compile.py --work DIR --only embassy-stm32
    python applications/pac_codegen/experiments/dependent_compile.py --work DIR --examples
    python applications/pac_codegen/experiments/dependent_compile.py --work DIR --examples --only stm32-hrtim
"""

import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "experiments"))
import enforcement                                   # noqa: E402
import corroboration                                 # noqa: E402

OUT = APP_DIR / "experiments" / "out"
PHASE1D = Path("/home/ramla/hal_agent-phase-1d")
TARGET = "thumbv7em-none-eabihf"
TIMEOUT = 3600

DEPENDENTS = {
    "stm32f469i-disc": {
        "version": "0.3.1", "features": [], "default_features": True,
        "rm": "rm0386", "device": "stm32f469", "pac": "stm32f4",
        "hal": "stm32f4xx-hal 0.23",
    },
    "semtech_radios": {
        "version": "0.1.6", "features": ["g474"], "default_features": True,
        "rm": "rm0440", "device": "stm32g474", "pac": "stm32g4",
        "hal": "stm32-hal2 2.1.10",
    },
    "embassy-stm32": {
        # single-bank: the build script refuses to guess the G474's flash
        # bank layout; the choice has no bearing on the hrtim path we measure
        "version": "0.6.0", "features": ["stm32g474ve", "single-bank"],
        "default_features": True,
        "rm": "rm0440", "device": "stm32g474", "pac": "stm32g4",
        "hal": "stm32-hrtim 0.2.0",
    },
}

# a diagnostic's file path -> which registry crate it fired in
_REGISTRY_RE = re.compile(r"registry/src/[^/]+/([A-Za-z0-9_.-]+?)-\d[\w.+-]*/")
# Spec matching is token-exact, mirroring stm_sweep.classify: gated `CRrs`
# must not claim a definition-side failure on ungated `CPT1CRrs` -- that is
# generic friction, and substring matching mislabeled hrtim's whole API.
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd and str(cwd), capture_output=True,
                          text=True, timeout=TIMEOUT)


def copy_pristine(src: Path, dest: Path) -> None:
    """Fresh mtimes, or cargo reuses the previous run's INJECTED artifacts
    against a pristine-on-disk tree (see port_stm32_eth.py)."""
    if dest.is_dir():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("target"))
    now = time.time()
    for p in dest.rglob("*"):
        try:
            os.utime(p, (now, now))
        except OSError:
            pass


def errors(probe: Path) -> list:
    """A build that never ran is not a build with no errors."""
    r = run(["cargo", "check", "--target", TARGET, "--message-format=json"],
            cwd=probe)
    out = []
    for line in r.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") == "compiler-message" and \
                m["message"].get("level") == "error":
            out.append(m["message"])
    if r.returncode != 0 and not out:
        sys.exit(f"cargo exited without compiling anything:\n"
                 f"{(r.stderr or r.stdout)[-1200:]}")
    return out


def patch_applied(probe: Path, pac: str) -> bool:
    """Cargo does not fail an unapplied [patch]; it warns and uses the
    registry crate, and the whole experiment silently measures nothing."""
    lock = probe / "Cargo.lock"
    if not lock.is_file():
        return False
    block, hit = [], False
    for line in lock.read_text().splitlines() + ["[[package]]"]:
        if line.strip() == "[[package]]":
            if any(l == f'name = "{pac}"' for l in block):
                hit = True
                if any(l.startswith("source = ") for l in block):
                    return False
            block = []
        else:
            block.append(line.strip())
    return hit


def write_probe(probe: Path, name: str, cfg: dict, pac_dir: Path) -> None:
    probe.mkdir(parents=True, exist_ok=True)
    feats = ", ".join(f'"{f}"' for f in cfg["features"])
    df = "true" if cfg["default_features"] else "false"
    (probe / "Cargo.toml").write_text(
        '[package]\nname = "probe"\nversion = "0.0.0"\nedition = "2021"\n\n'
        '[lib]\npath = "lib.rs"\n\n'
        "[dependencies]\n"
        f'{name} = {{ version = "={cfg["version"]}", '
        f"features = [{feats}], default-features = {df} }}\n\n"
        "[patch.crates-io]\n"
        f'{cfg["pac"]} = {{ path = "{pac_dir}" }}\n')
    (probe / "lib.rs").write_text("#![no_std]\n")


def inject(cfg: dict, pac_dir: Path, saved: Path, report: Path) -> dict:
    rm, device = cfg["rm"], cfg["device"]
    r = run([sys.executable, str(APP_DIR / "inject_from_run.py"),
             "--save-constraints", str(saved),
             str(PHASE1D / f"agent_output/stm/{rm}/1"),
             "--pac", str(pac_dir), "--device", device,
             "--svd-dir", str(PHASE1D / f"devices/stm/{rm}/svd/{device}.svd"),
             "--constraints", str(PHASE1D /
                                  f"evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl"),
             "--attribution-check", str(PHASE1D / "chunked_datasheets/stm"),
             "--report", str(report)])
    if r.returncode != 0:
        sys.exit(f"injection failed:\n{(r.stderr or r.stdout)[-800:]}")
    return json.loads(report.read_text())


def precondition_fields(saved_c: dict) -> dict:
    fields_by = collections.defaultdict(set)
    for e in saved_c.get("registers", []):
        per = (e.get("peripheral") or "").lower()
        reg = (e.get("register") or "").lower()
        conds = [c for v in (e.get("preconditions") or {}).values() for c in v]
        conds += [c for fg in (e.get("gated_fields") or {}).values()
                  for c in (fg.get("preconditions") or [])]
        for c in conds:
            head = c.split()[0] if c.split() else ""
            f = head.rsplit(".", 1)[-1].lower()
            if f:
                fields_by[(per, reg)].add(f)
                fields_by[reg].add(f)
    return fields_by


def classify(rep: dict, saved_c: dict, diags: list) -> dict:
    """Turn a build's error diagnostics into hits / friction / collateral.
    Shared by the bare-probe (floor) and example-build (ceiling) paths."""
    gated_specs = sorted({f"{r['register'].upper()}rs"
                          for r in rep.get("rows", [])
                          if r.get("fate") == "planned"},
                         key=lambda s: (-len(s), s))
    fields_by = precondition_fields(saved_c)
    hits, collateral, friction = [], [], []
    for d in diags:
        h = enforcement.classify_diagnostic(d)
        spans = [s for s in d.get("spans") or [] if s.get("is_primary")]
        loc = spans[0]["file_name"] if spans else "?"
        line = spans[0]["line_start"] if spans else 0
        m = _REGISTRY_RE.search(loc)
        layer = m.group(1) if m else "local"
        rel = _REGISTRY_RE.sub(lambda mm: mm.group(1) + "/", loc)
        if h is None:
            collateral.append({"file": rel, "layer": layer,
                               "message": d["message"][:140]})
            continue
        blob = d["message"] + " " + enforcement.span_labels(d)
        tokens = set(_IDENT_RE.findall(blob))
        named = next((s for s in gated_specs
                      if (s in tokens if "::" not in s else s in blob)), None)
        if named is None and h.spec not in gated_specs:
            friction.append({"file": rel, "line": line, "spec": h.spec,
                             "layer": layer})
            continue
        reg = h.spec.split("::")[-1].lower().removesuffix("rs")
        parts = [s for s in str(h.spec).split("::") if s]
        periph = parts[-3].lower() if len(parts) >= 3 else ""
        fields = sorted(fields_by.get((periph, reg)) or fields_by.get(reg) or [])
        verdict = "untriaged"
        p = Path(loc)
        if p.is_file() and fields:
            start, snip = corroboration.enclosing_function(str(p), line)
            verdict = corroboration.deterministic_scan(
                snip, line - start, fields)["verdict"]
        hits.append({"file": rel, "line": line, "layer": layer,
                     "register": h.spec, "operation": h.operation,
                     "fields": fields, "verdict": verdict})

    v = collections.Counter(x["verdict"] for x in hits)
    layers = collections.Counter(x["layer"] for x in hits)
    print(f"  registers gated {rep.get('registers_planned')}  gate fired "
          f"{len(hits)} {dict(layers)}  guarded {v.get('corroborated', 0)}  "
          f"possible bug {v.get('unchecked', 0)}  "
          f"friction {len(friction)}  collateral {len(collateral)}")
    for x in hits[:12]:
        print(f"    [{x['layer']}] {x['file']}:{x['line']}  "
              f"{x['register']} {x['operation']}  {x['verdict']}")
    return {"baseline": "PASS",
            "registers_gated": rep.get("registers_planned"),
            "gate_fired": len(hits), "by_layer": dict(layers),
            "guarded": v.get("corroborated", 0),
            "possible_bug": v.get("unchecked", 0),
            "untriaged": v.get("untriaged", 0),
            "generic_friction": len(friction),
            "friction_detail": friction[:6],
            "collateral": len(collateral), "collateral_detail": collateral[:8],
            "hits": hits}


def measure(name: str, cfg: dict, work: Path) -> dict:
    print(f"=== {name} {cfg['version']} (features {cfg['features'] or '[]'}) "
          f"-> {cfg['pac']} 0.16.0 / {cfg['device']} ===")
    pac_dir = work / f"pac-{name}"
    copy_pristine(APP_DIR / "vendored" / "pac" / cfg["pac"], pac_dir)
    probe = work / f"probe-{name}"
    write_probe(probe, name, cfg, pac_dir)

    base = errors(probe)
    if not patch_applied(probe, cfg["pac"]):
        return {"baseline": "UNMEASURED",
                "why": "the [patch] did not apply; nothing was measured"}
    if base:
        codes = collections.Counter(
            (e.get("code") or {}).get("code", "?") for e in base)
        print(f"  baseline FAILS ({len(base)} errors {dict(codes)})")
        return {"baseline": "FAIL", "baseline_errors": len(base),
                "by_code": dict(codes),
                "sample": [e["message"][:140] for e in base[:4]]}
    print("  baseline PASS (pristine PAC)")

    rep = inject(cfg, pac_dir, work / f"{name}_constraints.json",
                 work / f"{name}_inject.json")
    saved_c = json.loads((work / f"{name}_constraints.json").read_text())
    run(["cargo", "clean", "-p", cfg["pac"]], cwd=probe)
    return classify(rep, saved_c, errors(probe))


# --------------------------------------------------------------------------- #
# Example / firmware ceiling: build the dependent's OWN examples/bins, which
# instantiate the HAL's generic entry points (a bare probe does not), so gates
# fire in monomorphised code -- a ceiling, >= the floor. Same inject + classify.
# --------------------------------------------------------------------------- #
EXAMPLE_TARGETS = {
    "dht11-driver": {
        "repo": "https://github.com/Wkesther2/dht11-driver-rust.git",
        "subdir": ".", "build": ["--examples"],
        "rm": "rm0090", "device": "stm32f407", "pac": "stm32f4",
        "hal": "stm32f4xx-hal 0.23", "downloads": 95,
    },
    "stm32f469i-disc": {
        "repo": "https://codeberg.org/tegimeki/stm32f469i-disc.git",
        "subdir": ".", "build": ["--examples"],
        "rm": "rm0386", "device": "stm32f469", "pac": "stm32f4",
        "hal": "stm32f4xx-hal 0.23", "downloads": 2851,
    },
    "stm32-hrtim": {
        # actual HRTIM firmware for the embassy/hrtim pairing -- embassy's own
        # peripherals go through stm32-metapac (uninjected); only this path
        # touches the injected stm32g4. Nested example crate, bins + feature.
        "repo": "https://github.com/usbalbin/stm32-hrtim",
        "subdir": "examples/stm32g4",
        "build": ["--bins", "--features", "stm32g474"],
        "rm": "rm0440", "device": "stm32g474", "pac": "stm32g4",
        "hal": "stm32-hrtim 0.2 + stm32g4xx-hal", "downloads": None,
    },
    # NOTE: stm32f4xx-hal 0.22.x dependents (adafruit-seesaw, f4-w25q) depend on
    # `stm32f4-staging` aliased as `stm32f4`; a `stm32f4` [patch] is silently
    # unused (the guard below flags them UNMEASURED, not a false 0). Measuring
    # them needs an injected `stm32f4-staging` PAC or a bump of the dep to 0.23.
}


def clone_repo(repo: str, dest: Path) -> None:
    if dest.is_dir():
        shutil.rmtree(dest)
    r = run(["git", "clone", "--depth", "1", repo, str(dest)])
    if r.returncode != 0:
        sys.exit(f"clone failed ({repo}):\n{(r.stderr or r.stdout)[-400:]}")


def add_patch(cargo_toml: Path, pac_crate: str, pac_dir: Path) -> None:
    """Redirect `pac_crate` to the injected copy, preserving any existing
    [patch.crates-io] block (e.g. stm32-hrtim's own path patch)."""
    txt = cargo_toml.read_text()
    line = f'{pac_crate} = {{ path = "{pac_dir}" }}'
    if line in txt:
        return
    if "[patch.crates-io]" in txt:
        txt = txt.replace("[patch.crates-io]\n",
                          f"[patch.crates-io]\n{line}\n", 1)
    else:
        txt += f"\n[patch.crates-io]\n{line}\n"
    cargo_toml.write_text(txt)


def build_diags(crate_dir: Path, extra: list) -> tuple:
    r = run(["cargo", "build", *extra, "--target", TARGET,
             "--message-format=json"], cwd=crate_dir)
    diags = []
    for line in r.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") == "compiler-message" and \
                m["message"].get("level") == "error":
            diags.append(m["message"])
    return diags, r.stderr, r.returncode


def measure_examples(name: str, cfg: dict, work: Path) -> dict:
    print(f"=== {name} EXAMPLES ({cfg['hal']}) "
          f"-> {cfg['pac']} 0.16.0 / {cfg['device']} ===")
    repo_dir = work / f"repo-{name}"
    clone_repo(cfg["repo"], repo_dir)
    crate = repo_dir / cfg.get("subdir", ".")
    pac_dir = work / f"pac-{name}"
    copy_pristine(APP_DIR / "vendored" / "pac" / cfg["pac"], pac_dir)
    pac_crate = cfg.get("pac_crate", cfg["pac"])
    add_patch(crate / "Cargo.toml", pac_crate, pac_dir)

    base, base_err, base_rc = build_diags(crate, cfg["build"])
    # THE GUARD: cargo only warns on an unused [patch], then builds against the
    # pristine registry PAC -- a false 0. Refuse to report a number then.
    if "was not used in the crate graph" in base_err or \
            not patch_applied(crate, pac_crate):
        return {"baseline": "UNMEASURED",
                "why": f"[patch] for {pac_crate} not applied -- would build "
                       f"against the pristine PAC (a false 0). 0.22-era "
                       f"stm32f4xx-hal uses stm32f4-staging; bump to 0.23 or "
                       f"patch stm32f4-staging."}
    base_gates = [d for d in base if enforcement.classify_diagnostic(d)]
    if base_gates:
        return {"baseline": "FAIL",
                "why": f"{len(base_gates)} gate errors on the pristine PAC"}
    if base_rc != 0 and not base:
        return {"baseline": "UNMEASURED", "why": "baseline build did not run"}
    print("  baseline PASS (pristine PAC, patch applied)")

    rep = inject(cfg, pac_dir, work / f"{name}_constraints.json",
                 work / f"{name}_inject.json")
    saved_c = json.loads((work / f"{name}_constraints.json").read_text())
    run(["cargo", "clean"], cwd=crate)   # full clean: examples pull the HAL in
    diags, _, _ = build_diags(crate, cfg["build"])
    res = classify(rep, saved_c, diags)
    res["note"] = ("example/firmware ceiling -- instantiates the HAL, so >= the "
                   "bare-probe floor")
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", required=True)
    ap.add_argument("--examples", action="store_true",
                    help="build each dependent's OWN examples/bins (ceiling) "
                         "instead of a bare probe (floor)")
    ap.add_argument("--only", help="a single target name")
    args = ap.parse_args()
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)

    table = EXAMPLE_TARGETS if args.examples else DEPENDENTS
    measure_fn = measure_examples if args.examples else measure
    if args.only and args.only not in table:
        sys.exit(f"unknown target {args.only!r}; choices: {sorted(table)}")
    names = [args.only] if args.only else list(table)
    for name in names:
        cfg = table[name]
        result = measure_fn(name, cfg, work)
        result.update({"dependent": name, "hal": cfg["hal"],
                       "pac": f"{cfg['pac']} 0.16.0",
                       "rm": cfg["rm"], "device": cfg["device"],
                       "mode": "examples" if args.examples else "bare-probe"})
        if not args.examples:
            result.update({"version": cfg["version"],
                           "features": cfg["features"],
                           "floor_note":
                               "a bare probe instantiates no generics, so these "
                               "are sites the dependent compiles UNCONDITIONALLY "
                               "-- a floor; real firmware can only add sites"})
        tag = "depexamples" if args.examples else "dependent"
        out = OUT / f"{tag}_{name.replace('-', '_')}.json"
        out.write_text(json.dumps(result, indent=1) + "\n")
        print(f"  report: {out}\n")


if __name__ == "__main__":
    main()
