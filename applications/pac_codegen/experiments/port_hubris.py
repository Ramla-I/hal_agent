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
REF = "4924a12b7da3c1ff864d311532f5f692a33c8aee"
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
    "states (UE=0) is violated, not established")}


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
                             "register": reg, "operation": m.group(2),
                             "verdict": "untriaged"})
                continue
            start, snippet = corroboration.enclosing_function(
                str(path), sp["line_start"])
            det = corroboration.deterministic_scan(
                snippet, sp["line_start"] - start, fields)
            rows.append({"file": rel, "line": sp["line_start"],
                         "register": reg, "operation": m.group(2),
                         "fields": fields, "verdict": det["verdict"]})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--keep", action="store_true",
                    help="reuse an existing clone instead of re-cloning")
    ap.add_argument("--no-verify", action="store_true")
    args = ap.parse_args()

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
    get_pac.provision(force=True, crate=PAC, version=PAC_VERSION)
    out = OUT / "port_hubris.json"
    out.write_text(json.dumps(result, indent=1))
    print(f"\nreport: {out}")


if __name__ == "__main__":
    main()
