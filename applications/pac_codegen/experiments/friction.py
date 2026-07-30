#!/usr/bin/env python3
"""What actually causes generic friction, and what would it take to remove it?

"Generic friction" is the error class where a HAL fails to compile with our
datasheet diagnostic naming an ASSOCIATED-TYPE PROJECTION (``<Self as
UartRB>::SRrs``) rather than a register we gated. Generic code must declare
its requirements in its signature, and ``REG: UnconstrainedRead`` is now one of
them; code written before the markers existed cannot name it.

Two questions, two experiments:

  A. IS FRICTION PROPORTIONAL TO CONSTRAINTS?
     Patch generic.rs and add markers for EVERY register -- i.e. install the
     encoding while gating NOTHING. The PAC is then semantically identical to
     pristine: no register loses a method. If the friction errors are still
     there, friction is a FIXED one-time cost of the encoding, not something
     that grows with the constraints we inject -- and "inject fewer
     constraints" is not a mitigation.

  C. WOULD WRITING THE CODE CONCRETELY REMOVE IT?
     Compile the SAME body twice against the SAME injected PAC -- once
     generically over an associated register type, once against the concrete
     register type. If only the generic one fails, friction is a property of
     the abstraction, not of the register or the encoding, and "monomorphize
     the driver" is a real (if large) fix.

  B. HOW BIG IS THE HAL-SIDE FIX?
     Take the friction errors and apply rustc's own suggested bounds to the
     HAL source, iterating until it compiles or stops converging. The number
     of edits (and whether it converges at all, or cascades through callers)
     is the honest answer to "is there an easy way".

Neither experiment touches the committed PAC: everything runs on copies.

Usage:
    python applications/pac_codegen/experiments/friction.py [--only A|B]
"""

import argparse
import collections
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR.parent.parent))
import get_pac  # noqa: E402
import rust_codegen  # noqa: E402

OUT = APP_DIR / "experiments" / "out"
PAC_VERSION = "0.16.0"
STEP_TIMEOUT = 2400

# The two HALs with real friction, and the chip each was measured on.
CASES = [
    {"hal": "stm32f4xx-hal", "hal_version": "0.23.0", "pac": "stm32f4",
     "device": "stm32f401", "features": ["stm32f401"]},
    {"hal": "stm32f1xx-hal", "hal_version": "0.11.0", "pac": "stm32f1",
     "device": "stm32f103", "features": ["stm32f103", "medium"]},
]

MAX_ROUNDS = 25


def cargo_check_json(ws: Path):
    try:
        return subprocess.run(["cargo", "check", "--message-format=json"],
                              cwd=str(ws), capture_output=True, text=True,
                              timeout=STEP_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None


def diagnostics(run) -> list:
    out = []
    for line in run.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") == "compiler-message" and m["message"].get("level") == "error":
            out.append(m["message"])
    return out


def classify_witness(diags) -> dict:
    """Split errors into witness-diagnostic ones (ours) and everything else."""
    ours, other = [], []
    for d in diags:
        code = (d.get("code") or {}).get("code", "")
        if code == "E0277" and "constrained by its datasheet" in d.get("message", ""):
            ours.append(d)
        else:
            other.append(d)
    return {"ours": ours, "other": other}


# --------------------------------------------------------------------------- #
# Experiment A: encoding installed, nothing gated
# --------------------------------------------------------------------------- #

def pac_copy(pac: str) -> Path:
    src = get_pac.provision(crate=pac, version=PAC_VERSION)
    dst = Path(tempfile.mkdtemp(prefix=f"friction_pac_{pac}_")) / pac
    shutil.copytree(src, dst)
    return dst


def install_encoding_only(pac_dir: Path, device: str) -> int:
    """Patch generic.rs and give EVERY register every marker: the encoding is
    present, but no register loses any method. Semantically a no-op PAC."""
    rust_codegen.patch_generic_rs(pac_dir / "src" / "generic.rs")
    return rust_codegen.add_marker_impls(pac_dir / "src" / device, set())


def hal_ws(case: dict, pac_dir: Path, hal_path: Path | None = None) -> Path:
    ws = Path(tempfile.mkdtemp(prefix=f"friction_ws_{case['hal']}_"))
    (ws / "src").mkdir()
    (ws / "src" / "lib.rs").write_text(
        f"#![no_std]\npub use {case['hal'].replace('-', '_')} as hal;\n")
    feats = ", ".join(f'"{f}"' for f in case["features"])
    hal_dep = (f'{case["hal"]} = {{ path = "{hal_path}", features = [{feats}] }}'
               if hal_path else
               f'{case["hal"]} = {{ version = "={case["hal_version"]}", '
               f'features = [{feats}] }}')
    (ws / "Cargo.toml").write_text(
        "[package]\n"
        f'name = "friction-{case["hal"]}"\nversion = "0.1.0"\nedition = "2021"\n\n'
        "[dependencies]\n" + hal_dep + "\n\n"
        "[patch.crates-io]\n"
        f'{case["pac"]} = {{ path = "{pac_dir}" }}\n')
    return ws


def experiment_a(case: dict) -> dict:
    print(f"\n=== A: {case['hal']} vs {case['pac']} with the encoding installed "
          f"but NOTHING gated ===", flush=True)
    pac_dir = pac_copy(case["pac"])
    n = install_encoding_only(pac_dir, case["device"])
    print(f"  patched generic.rs; markers added to {n} register files "
          "(every register keeps every method)")
    ws = hal_ws(case, pac_dir)
    run = cargo_check_json(ws)
    if run is None:
        return {"hal": case["hal"], "status": "TIMEOUT"}
    diags = diagnostics(run)
    split = classify_witness(diags)
    files = collections.Counter()
    for d in split["ours"]:
        for s in d.get("spans", []):
            fn = s.get("file_name", "")
            if case["hal"] in fn:
                files[fn.split(f"{case['hal']}-{case['hal_version']}/")[-1]] += 1
    print(f"  witness-diagnostic errors: {len(split['ours'])}")
    print(f"  other errors:              {len(split['other'])}")
    for f, c in files.most_common(6):
        print(f"    {c:4d}  {f}")
    for d in split["ours"][:3]:
        print(f"    e.g. {d['message'][:120]}")
    return {"hal": case["hal"], "pac": case["pac"], "status": "ran",
            "zero_constraint_friction": len(split["ours"]),
            "other": len(split["other"]),
            "files": dict(files),
            "samples": [d["message"][:200] for d in split["ours"][:5]],
            "workspace": str(ws)}


# --------------------------------------------------------------------------- #
# Experiment B: apply rustc's own suggested bounds to the HAL
# --------------------------------------------------------------------------- #

def fetch_hal_source(hal: str, version: str) -> Path:
    url = f"https://static.crates.io/crates/{hal}/{hal}-{version}.crate"
    td = Path(tempfile.mkdtemp(prefix=f"friction_src_{hal}_"))
    data = urllib.request.urlopen(url, timeout=120).read()
    tarball = td / "c.crate"
    tarball.write_bytes(data)
    import tarfile
    with tarfile.open(tarball, "r:gz") as tf:
        tf.extractall(td, filter="data")
    return td / f"{hal}-{version}"


_BOUND_RE = re.compile(r"consider further restricting", re.I)

_MARKERS = ["UnconstrainedRead", "UnconstrainedWrite", "UnconstrainedModify"]


def fixup(hal_root: Path, pac: str) -> int:
    """Repair the two purely mechanical artifacts of applying rustc's
    suggestions verbatim, which a human patch author would never produce:

      1. two `where` clauses on one item (each suggestion adds its own) ->
         one comma-joined clause;
      2. the bound names a marker trait, or `Ptr`, that the module does not
         import. NOTE the marker traits live at the PAC CRATE ROOT
         (`stm32f4::UnconstrainedRead`), while a HAL's `crate::pac` usually
         aliases the DEVICE MODULE (`stm32f4::stm32f401`) -- importing from
         `crate::pac` does not resolve.

    Returns the number of files touched. Without this, the run stalls on
    scope errors and understates how far the bound approach actually gets."""
    pac_ident = pac.replace("-", "_")
    touched = 0
    for f in (hal_root / "src").rglob("*.rs"):
        text = f.read_text()
        orig = text
        prev = None
        while prev != text:
            prev = text
            text = re.sub(r"(where\s+[^\n{]*?)\s+where\s+", r"\1, ", text)
        needed = [m for m in _MARKERS if re.search(rf"\b{m}\b", text)]
        inserts = []
        if needed and not re.search(rf"use {pac_ident}::\{{[^}}]*Unconstrained", text):
            inserts.append(f"use {pac_ident}::{{{', '.join(needed)}}};\n")
        if (re.search(r"<\s*\w+\s+as\s+Ptr\s*>", text)
                and not re.search(r"use crate::Ptr\b", text)
                and not re.search(r"^\s*(pub )?trait Ptr\b", text, re.M)):
            inserts.append("use crate::Ptr;\n")
        if inserts:
            lines = text.splitlines(keepends=True)
            i = 0
            while i < len(lines) and (lines[i].startswith("//")
                                      or lines[i].startswith("#![")
                                      or not lines[i].strip()):
                i += 1
            lines[i:i] = inserts
            text = "".join(lines)
        if text != orig:
            f.write_text(text)
            touched += 1
    return touched


def apply_suggestions(diags, hal_root: Path) -> int:
    """Apply rustc's `consider further restricting ...` machine-applicable
    suggestions. Returns how many distinct edits were made this round."""
    edits = []          # (file, line0, col0, line1, col1, replacement)
    for d in diags:
        for ch in d.get("children", []):
            if not _BOUND_RE.search(ch.get("message", "")):
                continue
            for s in ch.get("spans", []):
                if s.get("suggested_replacement") is None:
                    continue
                fn = s.get("file_name", "")
                if not fn.startswith(str(hal_root)) and str(hal_root) not in fn:
                    continue
                edits.append((fn, s["line_start"], s["column_start"],
                              s["line_end"], s["column_end"],
                              s["suggested_replacement"]))
    if not edits:
        return 0
    # Apply per file, bottom-up, de-duplicated.
    by_file = collections.defaultdict(list)
    for e in edits:
        by_file[e[0]].append(e)
    applied = 0
    for fn, es in by_file.items():
        p = Path(fn)
        if not p.is_file():
            continue
        lines = p.read_text().splitlines(keepends=True)
        seen = set()
        for (_, l0, c0, l1, c1, rep) in sorted(es, key=lambda e: (-e[1], -e[2])):
            key = (l0, c0, l1, c1, rep)
            if key in seen:
                continue
            seen.add(key)
            if l0 != l1:
                continue                       # multi-line: skip, count as stuck
            idx = l0 - 1
            if idx >= len(lines):
                continue
            line = lines[idx]
            lines[idx] = line[:c0 - 1] + rep + line[c1 - 1:]
            applied += 1
        p.write_text("".join(lines))
    return applied


def experiment_b(case: dict) -> dict:
    print(f"\n=== B: how many HAL edits to clear {case['hal']}'s friction? ===",
          flush=True)
    pac_dir = pac_copy(case["pac"])
    install_encoding_only(pac_dir, case["device"])
    try:
        hal_root = fetch_hal_source(case["hal"], case["hal_version"])
    except Exception as e:                                    # noqa: BLE001
        print(f"  could not fetch HAL source: {e}")
        return {"hal": case["hal"], "status": "SOURCE_FETCH_FAILED"}
    ws = hal_ws(case, pac_dir, hal_path=hal_root)
    history = []
    total_edits = 0
    for rnd in range(1, MAX_ROUNDS + 1):
        run = cargo_check_json(ws)
        if run is None:
            history.append({"round": rnd, "status": "TIMEOUT"})
            break
        diags = diagnostics(run)
        split = classify_witness(diags)
        history.append({"round": rnd, "witness_errors": len(split["ours"]),
                        "other_errors": len(split["other"])})
        print(f"  round {rnd}: {len(split['ours'])} witness errors, "
              f"{len(split['other'])} other")
        if not diags:
            print(f"  CLEAN after {total_edits} edit(s)")
            break
        n = apply_suggestions(diags, hal_root)
        total_edits += n
        fixed = fixup(hal_root, case["pac"])
        print(f"    applied {n} compiler-suggested bound(s) "
              f"(total {total_edits}); fixup touched {fixed} file(s)")
        if n == 0 and fixed == 0:
            print("    no further machine-applicable suggestion — stuck")
            break
    return {"hal": case["hal"], "pac": case["pac"], "status": "ran",
            "total_edits": total_edits, "history": history,
            "hal_source": str(hal_root), "workspace": str(ws)}


_GENERIC_PROBE = """#![no_std]
use {pac}::{device} as pac;
// The shape stm32f4xx-hal uses: a trait with an associated register type, and
// the body written ONCE against the placeholder.
pub trait UartRB {{
    type SRrs: {pac}::Readable;
    fn sr(&self) -> &{pac}::Reg<Self::SRrs>;
}}
pub trait Impl: UartRB {{
    fn poll(&self) -> bool {{ self.sr().read().bits() != 0 }}
}}
"""

_CONCRETE_PROBE = """#![no_std]
use {pac}::{device} as pac;
// The same body, against the CONCRETE register type.
pub fn poll(u: &pac::{periph}) -> bool {{ u.sr().read().bits() != 0 }}
"""


def experiment_c(case: dict) -> dict:
    """Same body, same PAC, generic vs concrete."""
    print(f"\n=== C: {case['pac']} — is friction a property of the ABSTRACTION? ===",
          flush=True)
    pac_dir = pac_copy(case["pac"])
    install_encoding_only(pac_dir, case["device"])
    ident = case["pac"].replace("-", "_")
    out = {}
    for label, tpl in (("generic", _GENERIC_PROBE), ("concrete", _CONCRETE_PROBE)):
        ws = Path(tempfile.mkdtemp(prefix=f"friction_c_{label}_"))
        (ws / "src").mkdir()
        (ws / "src" / "lib.rs").write_text(tpl.format(
            pac=ident, device=case["device"], periph="USART1"))
        (ws / "Cargo.toml").write_text(
            f'[package]\nname = "friction-c-{label}"\nversion = "0.1.0"\n'
            'edition = "2021"\n\n[dependencies]\n'
            f'{case["pac"]} = {{ path = "{pac_dir}", '
            f'features = ["{case["device"]}"] }}\n')
        run = cargo_check_json(ws)
        if run is None:
            out[label] = "TIMEOUT"
            continue
        diags = diagnostics(run)
        witness = classify_witness(diags)["ours"]
        out[label] = ("compiles" if run.returncode == 0
                      else f"fails ({len(witness)} witness error(s))")
        print(f"  {label:9s} -> {out[label]}")
        for d in witness[:1]:
            print(f"      {d['message'][:110]}")
    return {"pac": case["pac"], "status": "ran", **out}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", choices=["A", "B", "C"], help="run one experiment")
    ap.add_argument("--hal", action="append", default=[])
    args = ap.parse_args()
    cases = [c for c in CASES if not args.hal or c["hal"] in args.hal]

    res = {"A": [], "B": [], "C": []}
    if args.only in (None, "A"):
        res["A"] = [experiment_a(c) for c in cases]
    if args.only in (None, "C"):
        res["C"] = [experiment_c(cases[0])]
    if args.only in (None, "B"):
        res["B"] = [experiment_b(c) for c in cases]

    print("\n\n## A. Friction with the encoding installed but NOTHING gated\n")
    print("| HAL | witness errors | other errors | verdict |")
    print("|---|---|---|---|")
    for r in res["A"]:
        if r.get("status") != "ran":
            print(f"| {r['hal']} | — | — | {r.get('status')} |")
            continue
        v = ("fixed cost of the encoding — independent of how many "
             "constraints are injected" if r["zero_constraint_friction"]
             else "friction is caused by the constraints themselves")
        print(f"| {r['hal']} | {r['zero_constraint_friction']} | "
              f"{r['other']} | {v} |")

    if res["B"]:
        print("\n## B. HAL-side fix: compiler-suggested bounds, applied\n")
        print("| HAL | edits applied | rounds | final witness errors | outcome |")
        print("|---|---|---|---|---|")
        for r in res["B"]:
            if r.get("status") != "ran":
                print(f"| {r['hal']} | — | — | — | {r.get('status')} |")
                continue
            last = r["history"][-1]
            outcome = ("converged" if last.get("witness_errors") == 0
                       and last.get("other_errors") == 0 else "did not converge")
            print(f"| {r['hal']} | {r['total_edits']} | {len(r['history'])} | "
                  f"{last.get('witness_errors', '—')} | {outcome} |")

    for r in res["C"]:
        print("\n## C. Same body, same injected PAC\n")
        print("| written as | result |")
        print("|---|---|")
        print(f"| generic over an associated register type | {r.get('generic')} |")
        print(f"| against the concrete register type | {r.get('concrete')} |")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "friction.json").write_text(json.dumps(res, indent=1) + "\n")
    print(f"\nreport: {OUT / 'friction.json'}")


if __name__ == "__main__":
    main()
