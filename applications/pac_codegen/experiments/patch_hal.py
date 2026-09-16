#!/usr/bin/env python3
"""Patch a HAL so it compiles against the injected PAC -- the adoption step.

Until the HAL builds, nothing downstream of it is ever type-checked, so the
enforcement is invisible to the application developer it is meant to protect
(see docs/hopter.md). This script performs the adoption a HAL maintainer would
eventually perform, mechanically, and records exactly what it took.

The injected PAC produces two error classes in a HAL, and they need opposite
treatment:

  GENERIC FRICTION -- the diagnostic names an associated-type PROJECTION
    (`<Self as UartRB>::SRrs`). No register is constrained; the generic code
    simply cannot prove the marker for an unresolved type. Fix: declare the
    bound, exactly as rustc suggests. Cost only.

  TRUE ENFORCEMENT -- the diagnostic names a CONCRETE register we gated. The
    HAL really does write a register the datasheet says has a precondition,
    without establishing it. These are candidate BUGS in the HAL, and each one
    is recorded with its file, line and source text before being neutralised.

    They are neutralised with the `unsafe` escape (`write_unwitnessed` etc.)
    rather than `write_when_ready`, deliberately: the escape preserves the
    HAL's behaviour byte-for-byte, so the resulting build measures what the
    APPLICATION does, not what our rewrite did to the driver. Switching to
    `write_when_ready` would change the driver's control flow and confound the
    experiment. Every escape is greppable and listed in the report.

Output: a patched HAL source tree plus `out/patch_hal.json` -- the candidate
bug list, the bound additions, and whether the HAL ends up compiling.

Usage:
    python applications/pac_codegen/experiments/patch_hal.py \\
        [--rm rm0368] [--hal stm32f4xx-hal] [--hal-version 0.23.0]
"""

import argparse
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
import enforcement as enforcement_mod  # noqa: E402
sys.path.insert(0, str(APP_DIR / "experiments"))
import get_pac  # noqa: E402
import rust_codegen  # noqa: E402
from stm_sweep import Target, run_inject, PacSnapshot  # noqa: E402

OUT = APP_DIR / "experiments" / "out"
PAC_VERSION = "0.16.0"
MAX_ROUNDS = 20

# gated method -> its unsafe escape, from the injected generic.rs surface.
_ESCAPE = {
    "write": "write_unwitnessed",
    "modify": "modify_unwitnessed",
    "read": "read_unwitnessed",
    "reset": "reset_unwitnessed",
    "write_with_zero": "write_with_zero_unwitnessed",
    "from_write": "from_write_unwitnessed",
    "from_modify": "from_modify_unwitnessed",
}
_MARKERS = ["UnconstrainedRead", "UnconstrainedWrite", "UnconstrainedModify"]


def fetch_hal(hal: str, version: str) -> Path:
    url = f"https://static.crates.io/crates/{hal}/{hal}-{version}.crate"
    td = Path(tempfile.mkdtemp(prefix=f"patch_hal_{hal}_"))
    (td / "c.crate").write_bytes(urllib.request.urlopen(url, timeout=300).read())
    with tarfile.open(td / "c.crate", "r:gz") as tf:
        tf.extractall(td, filter="data")
    return td / f"{hal}-{version}"


def workspace(hal: str, hal_root: Path, pac: str, pac_dir: Path,
              features: list) -> Path:
    ws = Path(tempfile.mkdtemp(prefix="patch_hal_ws_"))
    (ws / "src").mkdir()
    (ws / "src" / "lib.rs").write_text(
        f"#![no_std]\npub use {hal.replace('-', '_')} as hal;\n")
    feats = ", ".join(f'"{f}"' for f in features)
    (ws / "Cargo.toml").write_text(
        '[package]\nname = "patch-hal-probe"\nversion = "0.1.0"\n'
        'edition = "2021"\n\n[dependencies]\n'
        f'{hal} = {{ path = "{hal_root}", features = [{feats}] }}\n\n'
        "[patch.crates-io]\n"
        f'{pac} = {{ path = "{pac_dir}" }}\n')
    return ws


def diagnostics(ws: Path):
    run = subprocess.run(["cargo", "check", "--message-format=json"], cwd=str(ws),
                         capture_output=True, text=True, timeout=2400)
    out = []
    for line in run.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") == "compiler-message" and m["message"].get("level") == "error":
            out.append(m["message"])
    return out, run.returncode == 0


def _is_projection(msg: str) -> bool:
    """`<Self as UartRB>::SRrs` is a placeholder; `stm32f4::…::CCRrs` is not."""
    return " as " in msg.split("`")[1] if "`" in msg else False


def statement_span(text: str, offset: int) -> "tuple[int, int] | None":
    """Bounds of the statement containing `offset`: back to the previous `;`,
    `{` or `}` at depth 0, forward to the terminating `;`. Used to wrap a call
    in `unsafe { … }`, which is where an unsafe escape has to live."""
    start = offset
    depth = 0
    while start > 0:
        c = text[start - 1]
        if c in ")]}":
            depth += 1
        elif c in "([{":
            if depth == 0:
                break
            depth -= 1
        elif c == ";" and depth == 0:
            break
        start -= 1
    end, depth = offset, 0
    while end < len(text):
        c = text[end]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                return None            # call is an expression, not a statement
            depth -= 1
        elif c == ";" and depth == 0:
            return start, end + 1
        end += 1
    return None


def neutralise(d, hal_root: Path, bugs: list) -> bool:
    """Rewrite one true-enforcement site to the unsafe escape, recording it."""
    for span in d.get("spans", []):
        if not span.get("is_primary"):
            continue
        f = Path(span["file_name"])
        if not f.is_file():
            continue
        text = f.read_text()
        line_starts = [0]
        for ln in text.splitlines(keepends=True):
            line_starts.append(line_starts[-1] + len(ln))
        try:
            off = line_starts[span["line_start"] - 1] + span["column_start"] - 1
        except IndexError:
            return False
        method = text[off:off + 32].split("(")[0].strip()
        escape = _ESCAPE.get(method)
        if not escape:
            return False
        stmt = statement_span(text, off)
        if stmt is None:
            return False
        s, e = stmt
        body = text[s:e]
        if "write_unwitnessed" in body or "unsafe {" in body[:12]:
            return False
        patched = body.replace(f".{method}(", f".{escape}(", 1)
        bugs.append({
            "file": str(f.relative_to(hal_root)) if str(f).startswith(str(hal_root))
                    else f.name,
            "line": span["line_start"],
            "register": d["message"].split("`")[1],
            "operation": method,
            "source": body.strip()[:200],
            "diagnostic": d["message"][:200],
        })
        text = text[:s] + " unsafe {" + patched + " }" + text[e:]
        f.write_text(text)
        return True
    return False


_BOUND_RE = re.compile(r"consider further restricting", re.I)
_EXTRA_RE = re.compile(r"impl has extra requirement `(.+)`")


def widen_trait_bounds(diags, hal_root: Path) -> int:
    """Thread a bound up into the TRAIT DECLARATION (E0276).

    This is where "just declare the bound" stops being additive. rustc's
    suggestion puts the bound on the impl, but an impl may not be stricter
    than the trait it implements, so the trait's own method signature has to
    carry it too -- which changes the trait's public contract and every other
    implementor. rustc offers no machine-applicable fix for that step; the
    diagnostic only points at the trait method and names the requirement.
    """
    todo = []
    for d in diags:
        if (d.get("code") or {}).get("code") != "E0276":
            continue
        req = defn = None
        for s in d.get("spans", []):
            lbl = s.get("label") or ""
            m = _EXTRA_RE.search(lbl)
            if m:
                req = m.group(1)
            elif "from trait" in lbl:
                defn = s
        if req and defn:
            todo.append((defn, req))

    applied = 0
    by_file: dict = {}
    for defn, req in todo:
        by_file.setdefault(defn["file_name"], []).append((defn, req))
    for fn, items in by_file.items():
        f = Path(fn)
        if not f.is_file():
            continue
        text = f.read_text()
        starts = [0]
        for ln in text.splitlines(keepends=True):
            starts.append(starts[-1] + len(ln))
        # bottom-up so earlier offsets stay valid
        for defn, req in sorted(items, key=lambda x: -x[0]["line_end"]):
            try:
                end = starts[defn["line_end"] - 1] + defn["column_end"] - 1
            except IndexError:
                continue
            # a trait method declaration ends at `;` (no body) or `{`
            stop = len(text)
            for ch in (";", "{"):
                i = text.find(ch, end)
                if i != -1:
                    stop = min(stop, i)
            head = text[end:stop]
            if req in text[max(0, end - 400):stop]:
                continue                      # already carries it
            if re.search(r"\bwhere\b", head):
                text = text[:stop] + f", {req}" + text[stop:]
            else:
                text = text[:stop] + f" where {req} " + text[stop:]
            applied += 1
        f.write_text(text)
    return applied


def apply_import_suggestions(diags, hal_root: Path) -> int:
    """E0405/E0412: the bound names a trait the module does not import. rustc
    supplies the exact `use` line; apply it."""
    applied = 0
    for d in diags:
        if (d.get("code") or {}).get("code") not in ("E0405", "E0412", "E0433"):
            continue
        for ch in d.get("children", []):
            if "consider importing" not in ch.get("message", ""):
                continue
            for s in ch.get("spans", []):
                rep = s.get("suggested_replacement")
                if rep is None or str(hal_root) not in s.get("file_name", ""):
                    continue
                f = Path(s["file_name"])
                text = f.read_text()
                if rep.strip() in text:
                    continue
                lines = text.splitlines(keepends=True)
                idx = max(0, s["line_start"] - 1)
                lines.insert(idx, rep if rep.endswith("\n") else rep + "\n")
                f.write_text("".join(lines))
                applied += 1
                break
    return applied


def add_bounds(diags, hal_root: Path) -> int:
    edits = []
    for d in diags:
        for ch in d.get("children", []):
            if not _BOUND_RE.search(ch.get("message", "")):
                continue
            for s in ch.get("spans", []):
                if s.get("suggested_replacement") is None:
                    continue
                if str(hal_root) not in s.get("file_name", ""):
                    continue
                edits.append((s["file_name"], s["line_start"], s["column_start"],
                              s["line_end"], s["column_end"],
                              s["suggested_replacement"]))
    applied, by_file = 0, {}
    for e in edits:
        by_file.setdefault(e[0], []).append(e)
    for fn, es in by_file.items():
        p, seen = Path(fn), set()
        lines = p.read_text().splitlines(keepends=True)
        for (_, l0, c0, l1, c1, rep) in sorted(es, key=lambda e: (-e[1], -e[2])):
            if (l0, c0, l1, c1, rep) in seen or l0 != l1 or l0 > len(lines):
                continue
            seen.add((l0, c0, l1, c1, rep))
            ln = lines[l0 - 1]
            lines[l0 - 1] = ln[:c0 - 1] + rep + ln[c1 - 1:]
            applied += 1
        p.write_text("".join(lines))
    return applied


def fixup(hal_root: Path, pac: str) -> int:
    """Repair the mechanical artifacts of applying rustc suggestions verbatim:
    duplicated `where` clauses, and marker traits the module has not imported
    (they live at the PAC CRATE ROOT, while a HAL's `crate::pac` usually
    aliases the DEVICE MODULE)."""
    ident, touched = pac.replace("-", "_"), 0
    for f in (hal_root / "src").rglob("*.rs"):
        text = orig = f.read_text()
        prev = None
        while prev != text:
            prev = text
            text = re.sub(r"(where\s+[^\n{]*?)\s+where\s+", r"\1, ", text)
        need = [m for m in _MARKERS if re.search(rf"\b{m}\b", text)]
        ins = []
        if need and not re.search(rf"use {ident}::\{{[^}}]*Unconstrained", text):
            ins.append(f"use {ident}::{{{', '.join(need)}}};\n")
        if (re.search(r"<\s*\w+\s+as\s+Ptr\s*>", text)
                and not re.search(r"use crate::Ptr\b", text)
                and not re.search(r"^\s*(pub )?trait Ptr\b", text, re.M)):
            ins.append("use crate::Ptr;\n")
        if ins:
            ls = text.splitlines(keepends=True)
            i = 0
            while i < len(ls) and (ls[i].startswith(("//", "#!")) or not ls[i].strip()):
                i += 1
            ls[i:i] = ins
            text = "".join(ls)
        if text != orig:
            f.write_text(text)
            touched += 1
    return touched


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rm", default="rm0368")
    ap.add_argument("--device", default="stm32f401")
    ap.add_argument("--svd", default="stm32f401.svd")
    ap.add_argument("--pac", default="stm32f4")
    ap.add_argument("--hal", default="stm32f4xx-hal")
    ap.add_argument("--hal-version", default="0.23.0")
    ap.add_argument("--keep", default=None, help="copy the patched HAL here")
    ap.add_argument("--keep-pac", default=None,
                    help="copy the INJECTED PAC here before the tree is "
                         "restored, so a downstream build can use it")
    args = ap.parse_args()

    target = Target(args.rm, args.pac, args.device, args.svd)
    pac_dir = get_pac.provision(crate=args.pac, version=PAC_VERSION)
    snap = PacSnapshot(pac_dir, args.device)
    result = {"rm": args.rm, "hal": f"{args.hal} {args.hal_version}"}
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        rep = OUT / f"patch_hal_{args.rm}_inject.json"
        run = run_inject(target, pac_dir, rep, dry=False)
        if run.returncode != 0:
            sys.exit("injection failed:\n" + (run.stderr or run.stdout)[-2000:])
        summary = json.loads(rep.read_text())
        print(f"injected {args.rm}: {summary['registers_planned']} registers gated")

        hal_root = fetch_hal(args.hal, args.hal_version)
        ws = workspace(args.hal, hal_root, args.pac, pac_dir, [args.device])
        bugs, bounds, history = [], 0, []

        for rnd in range(1, MAX_ROUNDS + 1):
            diags, ok = diagnostics(ws)
            witness = [d for d in diags if enforcement_mod.is_ours(d)]
            enforcement = [d for d in witness
                           if not enforcement_mod.classify_diagnostic(d).projection]
            friction = [d for d in witness
                        if enforcement_mod.classify_diagnostic(d).projection]
            other = [d for d in diags if d not in witness]
            history.append({"round": rnd, "enforcement": len(enforcement),
                            "friction": len(friction), "other": len(other)})
            print(f"  round {rnd}: enforcement={len(enforcement)} "
                  f"friction={len(friction)} other={len(other)}")
            if ok:
                print("  HAL COMPILES against the injected PAC")
                break
            progress = 0
            for d in enforcement:
                if neutralise(d, hal_root, bugs):
                    progress += 1
            n = add_bounds(friction + other, hal_root)
            bounds += n
            widened = widen_trait_bounds(other, hal_root)
            imports = apply_import_suggestions(other, hal_root)
            progress += n + widened + imports + fixup(hal_root, args.pac)
            if widened or imports:
                print(f"    trait declarations widened: {widened}; "
                      f"imports added: {imports}")
            result_trait_widenings = result.get("trait_widenings", 0) + widened
            result["trait_widenings"] = result_trait_widenings
            if not progress:
                print("  stuck: no further mechanical fix available")
                break

        result.update({
            "registers_gated": summary["registers_planned"],
            "compiles": ok, "history": history,
            "bound_edits": bounds,
            "hal_constraint_violations": bugs,
            "hal_source": str(hal_root), "workspace": str(ws),
        })
        print(f"\nHAL sites writing a gated register unchecked: {len(bugs)}")
        for b in bugs[:10]:
            print(f"  {b['file']}:{b['line']}  {b['register']} ({b['operation']})")
            print(f"      {b['source'][:110]}")
        if args.keep_pac:
            import shutil as _sh
            dstp = Path(args.keep_pac)
            if dstp.exists():
                _sh.rmtree(dstp)
            _sh.copytree(pac_dir, dstp)
            result["injected_pac_at"] = str(dstp)
            print(f"injected PAC kept at: {dstp}")
        if args.keep:
            import shutil
            dst = Path(args.keep)
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(hal_root, dst)
            result["kept_at"] = str(dst)
            print(f"\npatched HAL: {dst}")
    finally:
        print("restored pristine PAC:", snap.restore_and_verify())

    (OUT / "patch_hal.json").write_text(json.dumps(result, indent=1) + "\n")
    print(f"report: {OUT / 'patch_hal.json'}")


if __name__ == "__main__":
    main()
