#!/usr/bin/env python3
"""trace_hal.py -- does a constraint ever reach the APPLICATION, or does the
driver absorb every one of them?

THE QUESTION
------------
`scan_projects.py` reads a project's own source. For an application that drives
its chip entirely through a driver crate (`booster`, `px4flow_bsp`,
`stm32f469i-disc`), that source contains ZERO register accesses, so the scan
reports zero hits -- true, and uninformative. The registers are still being
touched; they are being touched one layer down.

So: if the driver were FIXED -- rewritten to use the witness API correctly --
would anything still be wrong at the application level? There are two ways a
constraint can land, and only one of them is the driver's problem:

  CONTAINED   The precondition is established and consumed inside a single
              driver call. `I2c::new()` disables the peripheral, writes CCR and
              TRISE, re-enables. The obligation never escapes; the maintainer
              fixes it locally and no application line is implicated.

  ESCAPING    The precondition spans two driver calls. The driver exposes one
              entry point that leaves the peripheral enabled and another that
              writes a register requiring it disabled. Now the ORDER in which
              the application calls them decides correctness, and no local fix
              inside the driver can recover it -- the obligation has to appear
              in the driver's signature, and applications that call them in the
              wrong order stop compiling.

Only ESCAPING produces an application-level finding. This tool separates them.

METHOD
------
1. Start from the 31 compile-CONFIRMED violation sites in stm32f4xx-hal 0.23
   (out/patch_hal.json -- these are E0277s from a real `cargo check` against an
   injected chip crate, not a text match).
2. Walk UP the driver's call graph to every `pub` entry point that reaches each
   site.
3. Read the application's source for calls to those entry points.
4. For each reachable site, decide CONTAINED vs ESCAPING by asking whether the
   precondition field is written inside the same public entry point.

Usage:
    python applications/pac_codegen/experiments/trace_hal.py
    python applications/pac_codegen/experiments/trace_hal.py --apps-dir DIR
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "experiments"))
sys.path.insert(0, str(APP_DIR.parent.parent))

OUT = APP_DIR / "experiments" / "out"
HAL_SRC = Path.home() / (".cargo/registry/src/index.crates.io-"
                         "1949cf8c6b5b557f/stm32f4xx-hal-0.23.0")

# Applications that reach the chip only through a driver crate. `scan_projects`
# records them at zero register accesses; that is the fact this tool explains.
APPS = {
    "booster": "RF power-amplifier firmware (F407 / RM0090)",
    "px4flow_bsp": "optical-flow sensor board support (F407 / RM0090)",
    "stm32f469i-disc": "discovery-board BSP (F469 / RM0386)",
}

_FN_RE = re.compile(
    r"^(?P<indent>\s*)(?P<vis>pub(?:\([^)]*\))?\s+)?"
    r"(?:const\s+|async\s+|unsafe\s+|extern\s+\"[^\"]*\"\s+)*"
    r"fn\s+(?P<name>\w+)")
# A call to a named function/method, ignoring the receiver.
_CALL_RE = re.compile(r"(?:\.|::|\b)(?P<name>[a-z_]\w*)\s*\(")
# The `$` accepts a macro metavariable: this crate generates its SPI API from
# a template whose header is `impl<..> $Spi<SPI, BIDI, W> {`. Rejecting that
# left every function inside the macro unattributed, and the fallback picked up
# whatever impl came before -- which is how `Spi::transfer` got reported as
# `DmaBuilder::transfer`. The metavariable is stripped, so the label is the
# template's name; a macro instantiated for two types (Spi and SpiSlave) yields
# one label, which is approximate but never wrong about the module.
_IMPL_RE = re.compile(r"^\s*impl(?:\s*<[^>]*>)?\s+(?:(?P<tr>\$?[\w:]+)\s+for\s+)?"
                      r"(?P<ty>\$?[\w:]+)")

# Never treat these as driver API -- they are language/std noise that would
# otherwise connect every function to every other one.
_NOISE = {
    "new", "into", "from", "clone", "iter", "len", "get", "set", "unwrap",
    "expect", "map", "and_then", "ok_or", "as_ref", "as_mut", "borrow",
    "to_owned", "default", "drop", "min", "max", "abs", "pow", "wrapping_add",
    "read", "write", "modify", "bit", "bits", "bit_is_set", "bit_is_clear",
    "set_bit", "clear_bit", "enabled", "disabled", "variant", "if", "while",
    "for", "match", "return", "assert", "assert_eq", "panic", "some", "none",
    "ok", "err", "is_some", "is_none", "is_ok", "is_err", "push", "pop",
}


# --------------------------------------------------------------------------- #
# Driver call graph
# --------------------------------------------------------------------------- #

class Fn:
    __slots__ = ("name", "file", "start", "end", "public", "impl_ty", "body")

    def __init__(self, name, file, start, end, public, impl_ty, body):
        self.name, self.file, self.start, self.end = name, file, start, end
        self.public, self.impl_ty, self.body = public, impl_ty, body

    @property
    def label(self):
        return f"{self.impl_ty}::{self.name}" if self.impl_ty else self.name


def index_functions(root: Path) -> list:
    """Every function in the crate, with its line span, body and owning type.

    Ownership is resolved by scanning BACKWARDS from the function to the
    nearest `impl ... {` at a strictly smaller indent. Tracking the "most
    recent impl seen" while reading forwards does not survive this crate:
    `stm32f4xx-hal` generates its SPI API inside macro bodies, and a forward
    scan attributed `Spi::transfer` to `DmaBuilder` -- the last impl header it
    had happened to pass. Labels feed the report a human reads, so a wrong one
    is worse than none.
    """
    out = []
    for f in sorted(root.rglob("*.rs")):
        if "target" in f.parts:
            continue
        try:
            lines = f.read_text(errors="replace").splitlines()
        except OSError:
            continue
        rel = str(f.relative_to(root))
        for i, text in enumerate(lines):
            m = _FN_RE.match(text)
            if not m:
                continue
            indent = len(m.group("indent"))
            impl_ty = None
            for j in range(i - 1, max(-1, i - 400), -1):
                prev = lines[j]
                if not prev.strip():
                    continue
                pind = len(prev) - len(prev.lstrip())
                if pind >= indent:
                    continue
                im = _IMPL_RE.match(prev)
                if im:
                    impl_ty = im.group("ty").split("::")[-1].lstrip("$")
                    break
                if prev.lstrip().startswith(("fn ", "pub fn ", "mod ", "pub mod ")):
                    break
            depth, started, end = 0, False, i
            for j in range(i, min(i + 400, len(lines))):
                depth += lines[j].count("{") - lines[j].count("}")
                if "{" in lines[j]:
                    started = True
                if started and depth <= 0:
                    end = j
                    break
            out.append(Fn(m.group("name"), rel, i + 1, end + 1,
                          bool(m.group("vis")), impl_ty,
                          "\n".join(lines[i:end + 1])))
    return out


def callers_of(fns: list) -> dict:
    """name -> set of Fn that call it.

    Rust calls cannot be resolved by name alone, and pretending otherwise
    explodes. `stm32f4xx-hal` defines 2043 functions; a great many share a
    name across modules (`init`, `set_speed`, `enable`, `listen`). Linking
    every caller of every same-named function makes `Pin::into_push_pull_output`
    "reach" the RTC control register, which is nonsense -- the first run of
    this tool reported 105 escaping sites in booster on exactly that basis.

    Two edge kinds are trustworthy, and nothing else is:

      SAME FILE   the callee is defined in the file doing the calling. The
                  driver's modules are self-contained, so this is the common
                  case and is safe even for a shared name.
      UNIQUE      the name is defined exactly once in the whole crate, so the
                  call site has only one possible target.

    Everything else is dropped. That under-approximates reachability, which is
    the safe direction here: a missed edge costs a finding, an invented edge
    manufactures one.
    """
    by_name = defaultdict(list)
    for f in fns:
        by_name[f.name].append(f)
    unique = {n for n, v in by_name.items() if len(v) == 1}

    rev = defaultdict(set)
    for f in fns:
        for m in _CALL_RE.finditer(f.body):
            n = m.group("name")
            if n == f.name or n in _NOISE or n not in by_name:
                continue
            for callee in by_name[n]:
                if callee.file == f.file or n in unique:
                    rev[(callee.file, callee.name)].add(f)
    return rev


def enclosing(fns: list, file: str, line: int):
    """Innermost function containing file:line."""
    best = None
    for f in fns:
        if f.file == file and f.start <= line <= f.end:
            if best is None or f.start > best.start:
                best = f
    return best


def public_entry_points(fns, rev, start: Fn, max_depth: int = 4) -> list:
    """Public functions from which `start` is reachable (including itself),
    with the path that got there."""
    seen = {(start.file, start.label)}
    found, frontier = [], [(start, 0, [start])]
    while frontier:
        fn, d, path = frontier.pop()
        if fn.public:
            found.append((fn, path))
        if d >= max_depth:
            continue
        for up in rev.get((fn.file, fn.name), ()):
            key = (up.file, up.label)
            if key in seen:
                continue
            seen.add(key)
            frontier.append((up, d + 1, [up] + path))
    return found


# --------------------------------------------------------------------------- #
# Containment
# --------------------------------------------------------------------------- #

def precondition_fields(diagnostic: str, site_src: str) -> list:
    """Fields the datasheet rule depends on, recovered from the register the
    diagnostic names. Kept deliberately small: the point is containment, not
    re-deriving the constraint."""
    reg = diagnostic.split("`")[1] if "`" in diagnostic else ""
    reg = reg.split("::")[-1].removesuffix("rs").lower()
    return {"ccr": ["pe"], "trise": ["pe"], "cr1": ["spe", "pe", "ue"],
            "cr2": ["pe"], "brr": ["ue"], "dr": ["ue", "te"],
            "prlh": ["cnf"], "prll": ["cnf"], "crh": ["cnf"],
            }.get(reg, [])


def classify(path: list, fields: list) -> dict:
    """CONTAINED if the precondition is established ANYWHERE along the path
    from the public entry point down to the register write.

    Judging the entry point's own body alone is wrong and was wrong here:
    `Spi::new` does not mention SPE, but the `Spi::init` it calls clears it
    before touching CR1. From the application's side that is one call, and the
    obligation never becomes its problem. Containment is a property of the
    whole application-visible call, so the whole path is what gets read."""
    if not fields:
        return {"verdict": "unknown", "evidence": "no precondition field known"}
    body = "\n".join(f.body for f in path)
    for f in fields:
        # `.pe().clear_bit()`, `.ue().disabled()`, `w.spe().clear_bit()`
        pat = re.compile(rf"\.{f}\s*\(\s*\)\s*\.\s*(clear_bit|disabled|set_bit"
                         r"|enabled|bit\()")
        m = pat.search(body)
        if m:
            where = next((fn.label for fn in path if pat.search(fn.body)), "?")
            return {"verdict": "contained",
                    "evidence": f"{where} establishes {f.upper()}: {m.group(0)}"}
    return {"verdict": "escaping",
            "evidence": f"writes the register but never touches "
                        f"{'/'.join(x.upper() for x in fields)}"}


# --------------------------------------------------------------------------- #
# Application side
# --------------------------------------------------------------------------- #

def app_calls(root: Path) -> dict:
    """method name -> [(file, line, source line)] across the application."""
    calls = defaultdict(list)
    for f in sorted(root.rglob("*.rs")):
        if "target" in f.parts:
            continue
        try:
            lines = f.read_text(errors="replace").splitlines()
        except OSError:
            continue
        rel = str(f.relative_to(root))
        for i, text in enumerate(lines):
            for m in _CALL_RE.finditer(text):
                n = m.group("name")
                if n not in _NOISE:
                    calls[n].append((rel, i + 1, text.strip()[:130]))
    return calls


# --------------------------------------------------------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apps-dir", default=None,
                    help="directory holding the cloned applications")
    ap.add_argument("--hal", default=str(HAL_SRC))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    hal = Path(args.hal)
    if not hal.is_dir():
        sys.exit(f"driver source not found: {hal}")
    apps_dir = Path(args.apps_dir) if args.apps_dir else None
    if apps_dir is None or not apps_dir.is_dir():
        sys.exit("--apps-dir must point at the cloned applications")

    viol = json.loads((OUT / "patch_hal.json").read_text())
    sites = viol["hal_constraint_violations"]
    print(f"driver: {hal.name}   compile-confirmed violation sites: {len(sites)}")

    fns = index_functions(hal)
    rev = callers_of(fns)
    print(f"indexed {len(fns)} driver functions\n")

    # site -> public entry points
    entries = {}
    for s in sites:
        fn = enclosing(fns, s["file"], s["line"])
        if fn is None:
            continue
        eps = public_entry_points(fns, rev, fn)
        fields = precondition_fields(s["diagnostic"], s.get("source", ""))
        entries[(s["file"], s["line"])] = {
            "site": s, "inner": fn.label, "fields": fields,
            "entries": [{"label": e.label, "name": e.name, "file": e.file,
                         "line": e.start,
                         "path": " -> ".join(f.label for f in path),
                         **classify(path, fields)}
                        for e, path in eps],
        }

    # An application writes `spi.transfer(..)`; the driver defines `transfer`
    # eight times. Joining on the bare method name cannot tell which one, and
    # guessing produced a "finding" in booster that was really `Spi::transfer`
    # (a data transfer) mis-read as `DmaBuilder::transfer`. A name is only
    # claimed when it resolves to ONE public entry point across the whole
    # driver; everything else is reported as ambiguous, for a human.
    all_names = defaultdict(set)
    for f in fns:
        if f.public:
            all_names[f.name].add(f.label)

    reachable_names, ambiguous_names = defaultdict(set), defaultdict(set)
    for key, rec in entries.items():
        for e in rec["entries"]:
            bucket = (reachable_names if len(all_names[e["name"]]) == 1
                      else ambiguous_names)
            bucket[e["name"]].add(key)

    results = []
    for name, desc in APPS.items():
        root = apps_dir / name
        if not root.is_dir():
            print(f"!! {name}: not cloned, skipping")
            continue
        calls = app_calls(root)
        touched = []
        for meth, keys in reachable_names.items():
            if meth not in calls:
                continue
            for key in keys:
                rec = entries[key]
                ent = next(e for e in rec["entries"] if e["name"] == meth)
                touched.append({
                    "app_call": meth,
                    "app_sites": calls[meth][:6],
                    "driver_entry": ent["label"],
                    "driver_inner": rec["inner"],
                    "register": rec["site"]["register"].split("::")[-1],
                    "operation": rec["site"]["operation"],
                    "site": f"{rec['site']['file']}:{rec['site']['line']}",
                    "verdict": ent["verdict"],
                    "evidence": ent["evidence"],
                })
        amb = sorted({m for m in ambiguous_names if m in calls})
        esc = [t for t in touched if t["verdict"] == "escaping"]
        con = [t for t in touched if t["verdict"] == "contained"]
        print(f"=== {name} ({desc})")
        print(f"    driver entry points it calls that reach a gated register: "
              f"{len({t['driver_entry'] for t in touched})}")
        print(f"    CONTAINED (driver absorbs it): {len(con)}")
        print(f"    ESCAPING  (would surface in the app): {len(esc)}")
        if amb:
            print(f"    ambiguous method names (not claimed): "
                  f"{', '.join(amb)}")
        for t in esc[:8]:
            f, l, src = t["app_sites"][0]
            print(f"      {f}:{l}  {t['app_call']}() -> {t['driver_entry']}"
                  f" -> {t['register']} {t['operation']}")
            print(f"        {src}")
        results.append({"app": name, "desc": desc, "touched": touched,
                        "escaping": len(esc), "contained": len(con),
                        "ambiguous": amb})
        print()

    out = Path(args.out) if args.out else OUT / "trace_hal.json"
    out.write_text(json.dumps(
        {"hal": hal.name, "sites": len(sites),
         "entries": {f"{k[0]}:{k[1]}": v for k, v in entries.items()},
         "apps": results}, indent=1, default=str) + "\n")
    print(f"json: {out}")


if __name__ == "__main__":
    main()
