#!/usr/bin/env python3
"""Hubris on PAC 0.16: upgrade its chip-crate dependency, then measure.

Hubris (Oxide) is the best structural fit in the corpus and the reason is that
it has no HAL: its drivers talk to the svd2rust chip crate directly, so a gate
that fires lands on Hubris's own line rather than inside somebody else's
abstraction. The project scan could only mark it `pac-gap` -- it pins stm32h7
0.14, the injector targets 0.16 -- and a scan cannot tell you whether that gap
is a afternoon or a quarter.

It is an afternoon, and this script is it. The distance is one version line in
the workspace manifest plus three mechanical edits in one driver, all of them
the same classes port_hal.py already applies to community HALs:

    usart.cr3        -> usart.cr3()          register-block fields became
                                             accessor methods
    w.brr().bits(..) -> unsafe { .. }        raw field writes became unsafe fns
    orecf().set_bit  -> clear_bit_by_one()   write-1-to-clear fields renamed

Nothing here is written by hand: the edits come from port_hal's rules, which
take their spans from rustc and their new names from the PAC, and refuse
anything that is not one of those shapes.

Why a probe crate rather than `cargo check` in the Hubris tree: building a
Hubris driver standalone pulls userlib/abi/counters from the hubris GIT repo
via idol-runtime, which would then coexist with the local path copies and
duplicate the `panic_impl` lang item. The probe mirrors Hubris's own workspace
patches so exactly one copy of each is in the graph.

Usage:
    python applications/pac_codegen/experiments/port_hubris.py
    python applications/pac_codegen/experiments/port_hubris.py --keep
"""

import argparse
import collections
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
REPO = APP_DIR.parent.parent
sys.path.insert(0, str(APP_DIR))
import enforcement  # noqa: E402
sys.path.insert(0, str(APP_DIR / "experiments"))
import get_pac                                    # noqa: E402
import corroboration                              # noqa: E402
import port_hal                                   # noqa: E402

WORK = APP_DIR / "experiments" / "ported" / "hubris"
OUT = APP_DIR / "experiments" / "out"
PHASE1D = Path("/home/ramla/hal_agent-phase-1d")

REPO_URL = "https://github.com/oxidecomputer/hubris.git"
# Bumped from 4924a12b (the August measurement) after verifying upstream
# HEAD of 2026-09-18 carries the identical UE-before-BRR ordering at the
# same lines. The pin is still a pin -- the measurement stays deterministic
# -- it just names the newest commit the finding is verified against.
REF = "f6e5849734d4e7d965a2f1cd71ca4ed4b24532de"
PAC, PAC_VERSION, DEVICE, RM = "stm32h7", "0.16.0", "stm32h753v", "rm0433"
TARGET = "thumbv7em-none-eabihf"
DRIVER, DRIVER_FEATURE = "drv-stm32h7-usart", "h753"
TIMEOUT = 3600

# ssmarshal 1.0 does not build on a modern compiler; Hubris's own workspace
# carries this same patch.
SSMARSHAL_REV = "10e90cbe389c8f07c52815857551a051946881ab"

# What `corroborated` does and does not mean, recorded with the numbers
# because Hubris is the clearest example of the gap.
#
# deterministic_scan asks whether a precondition field is REFERENCED before the
# access, not whether it holds the required VALUE. In this driver the two come
# apart: RM0433 says BRR is writable only while UE = 0, and line 72 --
# `cr1().write(|w| w.fifoen().set_bit().ue().enabled())` -- sets UE to 1, the
# opposite. The scan sees `.ue(` before line 76 and calls it corroborated. It
# is the strongest evidence AGAINST the write being legal.
#
# So `guarded` is an upper bound on real guards, everywhere this scan is used,
# and the effect is largest exactly where a driver enables a peripheral and
# then keeps configuring it.
TRIAGE_CAVEAT = (
    "corroborated = the precondition field is referenced before the access, "
    "NOT that it holds the required value; a driver that sets the field to "
    "the WRONG state still reads as corroborated (see lib.rs:76, where UE is "
    "enabled at line 72 and RM0433 requires UE=0)")
KNOWN_WRONG = {("drv/stm32h7-usart/src/lib.rs", 76): (
    "verdict is wrong: UE is ENABLED at line 72, so the precondition RM0433 "
    "states (UE=0) is violated, not established. Present since the driver's "
    "FIRST commit (ad216b74, 2022-04-04, 'Add usart lib', #475) through "
    "the measured commit f6e58497 (upstream HEAD of 2026-09-18) -- the "
    "ordering has never been correct in four and a half years"),
    ("drv/stm32fx-usart/src/main.rs", 74): (
        "second wrong-way instance: UE is ENABLED at :65 and this is the "
        "cfg(stm32f3) branch -- RM0316 forbids BRR writes with UE=1. The "
        "identical enable is LEGAL for the f4 branch (RM0090 has no such "
        "rule): one source line, family-dependent bug"),
    ("drv/stm32g0-usart/src/main.rs", 74): (
        "the CONTROL: correct ordering -- BRR written before UE is set at "
        ":75; the gate still fires because the witness API is absent, but "
        "the ordering satisfies RM0444"),
    ("drv/stm32g0-usart/src/main.rs", 82): (
        "g0b1 branch of the same correct ordering: BRR before UE (:83)")}


# ---- the OTHER PAC families hubris pins ------------------------------------
# hubris/Cargo.toml lists stm32f3 + stm32f4 (0.13, drv/stm32fx-*), stm32g0
# (0.15.1, drv/stm32g0-usart) beside the measured stm32h7. Each is measured
# IN-TREE: `cargo check -p <task>` works inside hubris's own workspace (the
# probe dance above is only needed OUTSIDE it), with the family's PAC bumped
# to 0.16 and [patch.crates-io] pointing at a private injected copy.
# (package, crate subdir, cargo feature, pac crate, device, rm, target)
FAMILIES = [
    ("drv-stm32fx-usart", "drv/stm32fx-usart", "stm32f3", "stm32f3",
     "stm32f303", "rm0316", "thumbv7em-none-eabihf"),
    ("drv-stm32fx-usart", "drv/stm32fx-usart", "stm32f4", "stm32f4",
     "stm32f407", "rm0090", "thumbv7em-none-eabihf"),
    ("drv-stm32g0-usart", "drv/stm32g0-usart", "g031", "stm32g0",
     "stm32g031", "rm0444", "thumbv6m-none-eabi"),
]


def archive_pac(save_dir: Path, pac: str, device: str, rm: str,
                pristine: Path, injected: Path, records: list) -> None:
    """Copy the pristine and witness-gated PAC side by side under save_dir,
    so `diff -ru` shows exactly what injection did (markers removed, witness
    methods added). Both trees, because the ask is to diff them directly."""
    d = save_dir / f"{pac}-{device}"
    for src, sub in ((pristine, "pristine-pac"), (injected, "injected-pac")):
        dst = d / sub
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst,
                        ignore=shutil.ignore_patterns("target", ".git"))
    records.append({"pac": pac, "device": device, "rm": rm,
                    "pristine": d / "pristine-pac",
                    "injected": d / "injected-pac"})


def stub_task_build(src: Path, subdir: str) -> None:
    """Neutralise a task's build.rs to unblock a standalone `cargo check`.

    These are TASKS (main.rs), not the H7 library: their build.rs calls
    build_util::build_notifications(), which demands HUBRIS_TASK_CONFIG /
    HUBRIS_TASKS and the whole app-TOML machinery to generate a
    notifications module that main.rs `include!`s. The register-access code
    under test references exactly one symbol from it -- USART_IRQ_MASK, a
    u32 IPC mask -- so the stub emits that and nothing else. main.rs is
    byte-for-byte unchanged; this is build scaffolding, the task-crate
    analogue of the probe crate's workspace-patch mirroring."""
    b = src / subdir / "build.rs"
    b.write_text(
        'fn main() {\n'
        '    let out = std::path::Path::new('
        '&std::env::var("OUT_DIR").unwrap()).join("notifications.rs");\n'
        '    std::fs::write(out, "pub mod notifications { '
        'pub const USART_IRQ_BIT: u8 = 0; '
        'pub const USART_IRQ_MASK: u32 = 1 << USART_IRQ_BIT; }").unwrap();\n'
        '}\n')


def trim_workspace(src: Path) -> None:
    """Drop app/* and test/* from the scratch clone's workspace members.

    Adding a [patch] forces cargo to re-resolve the WHOLE workspace, and
    hubris's H7 apps (stm32h7 0.16 with `rt` -> cortex-m-rt 0.7) cannot
    coexist with the NXP side (lpc55-pac -> cortex-m-rt 0.6): both `links =
    "cortex-m-rt"`, and cargo allows one links provider per graph. The apps
    and tests are irrelevant to the task crates measured here; the drv/*
    members all stay."""
    p = src / "Cargo.toml"
    t = p.read_text()
    t2 = t.replace('    "app/*",\n', "").replace('    "test/*",\n', "")
    if t2 != t:
        p.write_text(t2)


def copy_pristine(src: Path, dest: Path) -> None:
    """Fresh mtimes, or cargo reuses a previous run's INJECTED artifacts
    against a pristine-on-disk tree (see port_stm32_eth.py)."""
    import os
    import time
    if dest.is_dir():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("target"))
    now = time.time()
    for p in dest.rglob("*"):
        try:
            os.utime(p, (now, now))
        except OSError:
            pass


def bump_family(src: Path, pac: str) -> str:
    p = src / "Cargo.toml"
    t = p.read_text()
    m = re.search(rf'^{pac} = \{{ version = "([^"]+)"', t, re.M)
    if not m:
        sys.exit(f"could not find the {pac} dependency in hubris/Cargo.toml")
    was = m.group(1)
    if was != "0.16":
        t = t[:m.start(1)] + "0.16" + t[m.end(1):]
        p.write_text(t)
    return was


def ensure_patch(src: Path, pac: str, pac_dir: Path) -> None:
    p = src / "Cargo.toml"
    t = p.read_text()
    line = f'{pac} = {{ path = "{pac_dir}" }}\n'
    if line in t:
        return
    if "[patch.crates-io]" in t:
        t = t.replace("[patch.crates-io]\n", "[patch.crates-io]\n" + line, 1)
    else:
        t += "\n[patch.crates-io]\n" + line
    p.write_text(t)


def fam_check(src: Path, pkg: str, feature: str, target: str) -> tuple:
    run = subprocess.run(
        ["cargo", "check", "-p", pkg, "--no-default-features",
         "--features", feature, "--target", target,
         "--message-format=json"],
        cwd=str(src), capture_output=True, text=True, timeout=TIMEOUT)
    errs = []
    for line in run.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") == "compiler-message" and \
                m["message"].get("level") == "error":
            errs.append(m["message"])
    if run.returncode != 0 and not errs:
        sys.exit(f"cargo exited without compiling anything ({pkg}):\n"
                 f"{(run.stderr or run.stdout)[-1200:]}")
    return errs, run.stdout


def fam_patch_applied(src: Path, pac: str) -> bool:
    """Cargo does not fail an unapplied [patch]; it warns and uses the
    registry crate, and the whole experiment silently measures nothing."""
    lock = src / "Cargo.lock"
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


def fam_port(src: Path, pkg: str, feature: str, target: str,
             pac_dir: Path, verify: bool) -> dict:
    """port_hal's rule chain, run in-tree against one task crate."""
    variants = port_hal.pac_variants(pac_dir)
    skipped, history, total = [], [], 0
    for _ in range(60):
        errs, stdout = fam_check(src, pkg, feature, target)
        edits, codes = port_hal.diagnostics(stdout)
        history.append({"errors": len(errs), "by_code": dict(codes)})
        if not edits:
            edits = port_hal.unsafe_edits(stdout)
        if not edits:
            edits = port_hal.rename_edits(stdout)
        if not edits:
            edits = port_hal.semicolon_edits(stdout, src)
        if not edits:
            edits = port_hal.into_edits(stdout)
        if not edits:
            break
        before = total
        total += port_hal.apply(src, edits, verify, variants, skipped)
        if total == before:
            break
    return {"edits": total, "rounds": history, "skipped": skipped,
            "residual": history[-1]["by_code"] if history else {}}


def measure_family(src: Path, pkg: str, subdir: str, feature: str, pac: str,
                   device: str, rm: str, verify: bool,
                   target: str, save_dir: Path = None,
                   records: list = None) -> dict:
    print(f"\n=== {pkg} --features {feature} -> {pac} 0.16.0 / {device} "
          f"({rm}) ===", flush=True)
    pac_dir = WORK / f"pac-{feature}"
    copy_pristine(APP_DIR / "vendored" / "pac" / pac, pac_dir)
    was = bump_family(src, pac)
    ensure_patch(src, pac, pac_dir)
    stub_task_build(src, subdir)

    p = fam_port(src, pkg, feature, target, pac_dir, verify)
    first = p["rounds"][0]["errors"] if p["rounds"] else 0
    print(f"  port: {first} errors -> {p['rounds'][-1]['errors']} "
          f"after {p['edits']} mechanical edits", flush=True)

    base, _ = fam_check(src, pkg, feature, target)
    if not fam_patch_applied(src, pac):
        sys.exit(f"the {pac} [patch] did not apply; nothing was measured")
    if base:
        codes = collections.Counter(
            (e.get("code") or {}).get("code", "?") for e in base)
        print(f"  baseline FAILS ({len(base)} errors {dict(codes)})")
        result = {"baseline": "FAIL", "baseline_errors": len(base),
                  "by_code": dict(codes)}
    else:
        print("  baseline PASS (pristine PAC)")
        report = OUT / f"{rm}_{device}_hubris_{feature}.json"
        saved = OUT / f"{rm}_{device}_hubris_{feature}_constraints.json"
        r = subprocess.run(
            [sys.executable, str(APP_DIR / "inject_from_run.py"),
             str(PHASE1D / f"agent_output/stm/{rm}/1"),
             "--pac", str(pac_dir), "--device", device,
             "--svd-dir", str(PHASE1D / f"devices/stm/{rm}/svd/{device}.svd"),
             "--constraints",
             str(PHASE1D / f"evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl"),
             "--attribution-check", str(PHASE1D / "chunked_datasheets/stm"),
             "--save-constraints", str(saved), "--report", str(report)],
            capture_output=True, text=True, cwd=str(REPO), timeout=TIMEOUT)
        if r.returncode != 0:
            print(f"  injection FAILED: {(r.stderr or r.stdout)[-300:]}")
            result = {"baseline": "PASS", "inject": "FAILED"}
        else:
            rep = json.loads(report.read_text())
            saved_c = json.loads(saved.read_text()) if saved.is_file() else {}
            subprocess.run(["cargo", "clean", "-p", pac], cwd=str(src),
                           capture_output=True, text=True, timeout=TIMEOUT)
            diags, _ = fam_check(src, pkg, feature, target)
            rows = triage(diags, precondition_fields(saved_c), src)
            other = len(diags) - len(rows)
            v = collections.Counter(x["verdict"] for x in rows)
            for x in rows:
                note = KNOWN_WRONG.get((x["file"], x["line"]))
                if note:
                    x["triage_note"] = note
                print(f"    {x['file']}:{x['line']}  {x['register']} "
                      f"{x['operation']}  -> {x['verdict']}"
                      + ("   [noted]" if note else ""))
            result = {"baseline": "PASS",
                      "registers_gated": rep.get("registers_planned"),
                      "gate_fired": len(rows),
                      "guarded": v.get("corroborated", 0),
                      "possible_bug": v.get("unchecked", 0),
                      "untriaged": v.get("untriaged", 0),
                      "collateral": other, "hits": rows,
                      "triage_caveat": TRIAGE_CAVEAT}
            print(f"  registers gated {rep.get('registers_planned')}  "
                  f"fired {len(rows)}  guarded {v.get('corroborated', 0)}  "
                  f"possible bug {v.get('unchecked', 0)}  "
                  f"untriaged {v.get('untriaged', 0)}  collateral {other}")
    result.update({"project": f"hubris ({pkg} @ {device})", "ref": REF,
                   "pac": pac, "pac_version": "0.16.0", "device": device,
                   "rm": rm, "driver": pkg, "pac_version_was": was,
                   "mechanical_edits": p["edits"],
                   "port_residual": p["residual"]})
    out = OUT / f"port_hubris_{feature}.json"
    out.write_text(json.dumps(result, indent=1))
    print(f"  report: {out}")
    # Both trees are present at once: the private injected copy (pac_dir)
    # and the still-pristine shared vendored crate (families never inject
    # the shared tree).
    if save_dir is not None and result.get("baseline") == "PASS":
        archive_pac(save_dir, pac, device, rm,
                    APP_DIR / "vendored" / "pac" / pac, pac_dir, records)
    return result


def clone(keep: bool) -> Path:
    src = WORK / "hubris"
    if src.is_dir() and keep:
        return src
    if src.exists():
        shutil.rmtree(src)
    src.parent.mkdir(parents=True, exist_ok=True)
    print(f"  cloning hubris @ {REF[:12]} ...", flush=True)
    subprocess.run(["git", "clone", "--filter=blob:none", REPO_URL, str(src)],
                   check=True, capture_output=True, text=True, timeout=TIMEOUT)
    subprocess.run(["git", "-C", str(src), "checkout", "--detach", REF],
                   check=True, capture_output=True, text=True, timeout=TIMEOUT)
    return src


def bump_pac(src: Path) -> str:
    """The one hand-written change: the version line Hubris would have to
    change itself to adopt the new PAC generation."""
    p = src / "Cargo.toml"
    t = p.read_text()
    m = re.search(r'^stm32h7 = \{ version = "([^"]+)"', t, re.M)
    if not m:
        sys.exit("could not find the stm32h7 dependency in hubris/Cargo.toml")
    was = m.group(1)
    t = t[:m.start(1)] + "0.16" + t[m.end(1):]
    p.write_text(t)
    return was


def probe(src: Path, pac_dir: Path) -> Path:
    ws = WORK / "probe"
    (ws / "src").mkdir(parents=True, exist_ok=True)
    (ws / "src" / "lib.rs").write_text(
        "#![no_std]\n#[allow(unused_imports)]\n"
        "pub use drv_stm32h7_usart as _;\n")
    (ws / "Cargo.toml").write_text(f"""[package]
name = "hubris-probe"
version = "0.0.0"
edition = "2021"

[lib]
test = false
doctest = false
bench = false

[dependencies]
{DRIVER} = {{ path = "{src}/drv/stm32h7-usart", features = ["{DRIVER_FEATURE}"] }}

# Mirrors hubris's own workspace patches: idol-runtime pulls these from the
# hubris GIT repo, and two copies duplicate the panic_impl lang item.
[patch."https://github.com/oxidecomputer/hubris".userlib]
path = "{src}/sys/userlib"
[patch."https://github.com/oxidecomputer/hubris".abi]
path = "{src}/sys/abi"
[patch."https://github.com/oxidecomputer/hubris".counters]
path = "{src}/lib/counters"

[patch.crates-io]
{PAC} = {{ path = "{pac_dir}" }}
ssmarshal = {{ git = "https://gitlab.com/de-vri-es/ssmarshal", rev = "{SSMARSHAL_REV}" }}

[workspace]
""")
    shutil.copy(src / "rust-toolchain.toml", ws / "rust-toolchain.toml")
    (ws / ".cargo").mkdir(exist_ok=True)
    (ws / ".cargo" / "config.toml").write_text(
        f'[build]\ntarget = "{TARGET}"\n')
    return ws


def check(ws: Path) -> list:
    """Errors from a clean build of the PAC. The injector rewrites that same
    tree, so a stale .rmeta would report gates from a pristine PAC."""
    subprocess.run(["cargo", "clean", "-p", PAC], cwd=str(ws),
                   capture_output=True, text=True, timeout=TIMEOUT)
    run = subprocess.run(["cargo", "check", "--message-format=json"],
                         cwd=str(ws), capture_output=True, text=True,
                         timeout=TIMEOUT)
    out = []
    for line in run.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") == "compiler-message" \
                and m["message"].get("level") == "error":
            out.append(m["message"])
    if run.returncode != 0 and not out:
        # A build that never ran is not a clean baseline. Matches the guard in
        # dependent_compile.errors() and port_hubris's own in-tree builder.
        raise SystemExit("hubris baseline: cargo exited without compiling "
                         "anything:\n" + (run.stderr or run.stdout)[-800:])
    return out


def port(ws: Path, pac_dir: Path, verify: bool) -> dict:
    """port_hal's rules, driven by this workspace's diagnostics."""
    variants = port_hal.pac_variants(Path(pac_dir))
    skipped, total, history = [], 0, []
    for _ in range(40):
        subprocess.run(["cargo", "clean", "-p", PAC], cwd=str(ws),
                       capture_output=True, text=True, timeout=TIMEOUT)
        run = subprocess.run(["cargo", "check", "--message-format=json"],
                             cwd=str(ws), capture_output=True, text=True,
                             timeout=TIMEOUT)
        edits, codes = port_hal.diagnostics(run.stdout)
        history.append({"errors": sum(codes.values()), "by_code": dict(codes)})
        if not edits:
            edits = port_hal.unsafe_edits(run.stdout)
        if not edits:
            edits = port_hal.rename_edits(run.stdout)
        if not edits:
            edits = port_hal.semicolon_edits(run.stdout, ws)
        if not edits:
            break
        before = total
        total += port_hal.apply(ws, edits, verify, variants, skipped)
        if total == before:
            break
    return {"edits": total, "rounds": history, "skipped": skipped,
            "residual": history[-1]["by_code"] if history else {}}


def inject() -> dict:
    report = OUT / f"{RM}_{DEVICE}_hubris.json"
    saved = OUT / f"{RM}_{DEVICE}_hubris_constraints.json"
    run = subprocess.run(
        [sys.executable, str(APP_DIR / "inject_from_run.py"),
         str(PHASE1D / f"agent_output/stm/{RM}/1"),
         "--pac", str(APP_DIR / "vendored" / "pac" / PAC),
         "--device", DEVICE,
         "--svd-dir", str(PHASE1D / f"devices/stm/{RM}/svd/{DEVICE}.svd"),
         "--constraints",
         str(PHASE1D / f"evaluation/stm/{RM}/1/{RM}_constraints_review.jsonl"),
         "--attribution-check", str(PHASE1D / "chunked_datasheets/stm"),
         "--save-constraints", str(saved),
         "--report", str(report)],
        capture_output=True, text=True, cwd=str(REPO), timeout=TIMEOUT)
    if run.returncode != 0:
        return {"error": (run.stderr or run.stdout)[-800:]}
    rep = json.loads(report.read_text())
    rep["_constraints"] = json.loads(saved.read_text()) if saved.is_file() else {}
    return rep


def precondition_fields(saved) -> dict:
    out = collections.defaultdict(set)
    for entry in (saved or {}).get("registers", []):
        reg = (entry.get("register") or "").lower()
        for conds in (entry.get("preconditions") or {}).values():
            for c in conds:
                head = c.split()[0] if c.split() else ""
                f = head.rsplit(".", 1)[-1]
                if f:
                    out[reg].add(f.lower())
    return {k: sorted(v) for k, v in out.items()}


def triage(diags: list, fields_by_reg: dict, src: Path) -> list:
    rows = []
    for d in diags:
        hit = enforcement.classify_diagnostic(d)
        if hit is None:
            continue
        reg, key = hit.spec, hit.register
        for sp in d.get("spans", []):
            if not sp.get("is_primary"):
                continue
            path = Path(sp["file_name"])
            if not path.is_absolute():
                path = src / sp["file_name"]
            if not path.is_file():
                continue
            rel = str(path).split("hubris/")[-1]
            fields = fields_by_reg.get(key)
            if not fields:
                rows.append({"file": rel, "line": sp["line_start"],
                             "register": reg, "operation": hit.operation,
                             "verdict": "untriaged"})
                continue
            start, snippet = corroboration.enclosing_function(
                str(path), sp["line_start"])
            det = corroboration.deterministic_scan(
                snippet, sp["line_start"] - start, fields)
            rows.append({"file": rel, "line": sp["line_start"],
                         "register": reg, "operation": hit.operation,
                         "fields": fields, "verdict": det["verdict"]})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--keep", action="store_true",
                    help="reuse an existing clone instead of re-cloning")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--save-artifacts", metavar="DIR", default=None,
                    help="archive pristine + witness-gated PAC for every "
                         "pairing here, and the source port as a patch, then "
                         "print diff-ready paths")
    args = ap.parse_args()
    save_dir = Path(args.save_artifacts) if args.save_artifacts else None
    records = []

    print(f"=== hubris @ {REF[:12]} -> {PAC} {PAC_VERSION} / {DEVICE} ===")
    pac_dir = Path(get_pac.provision(force=True, crate=PAC,
                                     version=PAC_VERSION))
    src = clone(args.keep)
    was = bump_pac(src)
    print(f"  workspace Cargo.toml: stm32h7 {was} -> 0.16")
    ws = probe(src, pac_dir)

    p = port(ws, pac_dir, not args.no_verify)
    first = p["rounds"][0]["errors"] if p["rounds"] else 0
    print(f"  port: {first} errors -> {p['rounds'][-1]['errors']} "
          f"after {p['edits']} mechanical edits")

    base = check(ws)
    if base:
        codes = collections.Counter(
            (e.get("code") or {}).get("code", "?") for e in base)
        print(f"  baseline FAILS ({len(base)} errors {dict(codes)}) "
              f"-- nothing measured")
        result = {"baseline": "FAIL", "baseline_errors": len(base),
                  "by_code": dict(codes)}
    else:
        print("  baseline PASS (pristine PAC)")
        rep = inject()
        if "error" in rep:
            print(f"  injection FAILED: {rep['error'][:200]}")
            result = {"baseline": "PASS", "inject": "FAILED"}
        else:
            diags = check(ws)
            rows = triage(diags, precondition_fields(rep["_constraints"]), src)
            other = len(diags) - len(rows)
            v = collections.Counter(r["verdict"] for r in rows)
            print(f"  registers gated: {rep.get('registers_planned')}  "
                  f"gate fired: {len(rows)}  "
                  f"guarded: {v.get('corroborated', 0)}  "
                  f"possible bug: {v.get('unchecked', 0)}  "
                  f"untriaged: {v.get('untriaged', 0)}  "
                  f"collateral: {other}")
            for r in rows:
                note = KNOWN_WRONG.get((r["file"], r["line"]))
                if note:
                    r["triage_note"] = note
                print(f"    {r['file']}:{r['line']}  {r['register']} "
                      f"{r['operation']}  -> {r['verdict']}"
                      + (f"   [{note}]" if note else ""))
            print(f"\n  NOTE: {TRIAGE_CAVEAT}")
            result = {"baseline": "PASS",
                      "registers_gated": rep.get("registers_planned"),
                      "gate_fired": len(rows),
                      "guarded": v.get("corroborated", 0),
                      "possible_bug": v.get("unchecked", 0),
                      "untriaged": v.get("untriaged", 0),
                      "collateral": other, "hits": rows,
                      "triage_caveat": TRIAGE_CAVEAT}

    result.update({"project": "hubris", "ref": REF, "pac": PAC,
                   "pac_version": PAC_VERSION, "device": DEVICE, "rm": RM,
                   "driver": DRIVER, "pac_version_was": was,
                   "mechanical_edits": p["edits"], "port_residual": p["residual"]})
    # Snapshot the injected shared H7 crate BEFORE it is restored, then the
    # pristine one AFTER -- the shared tree is the same path at two times.
    if save_dir is not None and "hits" in result:
        save_dir.mkdir(parents=True, exist_ok=True)
        tmp_inj = save_dir / f"{PAC}-{DEVICE}" / "injected-pac"
        if tmp_inj.exists():
            shutil.rmtree(tmp_inj)
        shutil.copytree(APP_DIR / "vendored" / "pac" / PAC, tmp_inj,
                        ignore=shutil.ignore_patterns("target", ".git"))
    get_pac.provision(force=True, crate=PAC, version=PAC_VERSION)
    if save_dir is not None and "hits" in result:
        pri = save_dir / f"{PAC}-{DEVICE}" / "pristine-pac"
        if pri.exists():
            shutil.rmtree(pri)
        shutil.copytree(APP_DIR / "vendored" / "pac" / PAC, pri,
                        ignore=shutil.ignore_patterns("target", ".git"))
        records.append({"pac": PAC, "device": DEVICE, "rm": RM,
                        "pristine": pri,
                        "injected": save_dir / f"{PAC}-{DEVICE}"
                        / "injected-pac"})
    out = OUT / "port_hubris.json"
    out.write_text(json.dumps(result, indent=1))
    print(f"\nreport: {out}")

    # The other three pairings, measured in the same clone. f3 runs before
    # f4 deliberately: they share drv/stm32fx-usart's source, and the first
    # port pass carries most of the shared edits.
    trim_workspace(src)
    for pkg, subdir, feature, pac, device, rm, target in FAMILIES:
        measure_family(src, pkg, subdir, feature, pac, device, rm,
                       not args.no_verify, target, save_dir, records)

    if save_dir is not None:
        patch = save_dir / "hubris-source-port.patch"
        diff = subprocess.run(["git", "-C", str(src), "diff"],
                              capture_output=True, text=True, timeout=TIMEOUT)
        patch.write_text(diff.stdout)
        print(f"\n{'=' * 66}")
        print(f"Artifacts saved under {save_dir}")
        print("\nSource port (the mechanical 0.14 -> 0.16 driver edits):")
        print(f"  pristine : upstream hubris @ {REF[:12]}  "
              f"(git checkout of the pinned ref)")
        print(f"  ported   : {src}")
        print(f"  edits    : git -C {src} diff")
        print(f"             (also saved as {patch})")
        print("\nPAC injection (pristine vs witness-gated), per pairing:")
        for r in records:
            print(f"  {r['pac']} / {r['device']} ({r['rm']})")
            print(f"    pristine : {r['pristine']}")
            print(f"    injected : {r['injected']}")
            print(f"    diff     : diff -ru {r['pristine']} {r['injected']}")
        print("\n  (full PAC source trees are copied so you can diff "
              "directly; the H7 crate is large -- remove DIR when done. "
              "A gate reads as three lines per register: UnconstrainedRead "
              "kept, Write/Modify withheld -> the write needs a witness.)")
        print(f"{'=' * 66}")


if __name__ == "__main__":
    main()
