#!/usr/bin/env python3
"""trace_hal.py -- does a constraint ever reach the APPLICATION, or does the
driver absorb every one of them?

THE QUESTION
------------
`scan_projects.py` reads a project's own source and reports hits on registers
that carry a datasheet constraint. For these three applications that number is
ZERO, and for a different reason in each case: `stm32f469i-disc` touches no
registers at all, while `booster` and `px4flow_bsp` touch 24 and 50 of them but
none that is constrained. Either way the scan says nothing about the registers
these applications reach THROUGH the driver, which is most of them.

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
1. Start from the compile-CONFIRMED violation sites in stm32f4xx-hal 0.23 for
   THE APPLICATION'S OWN MANUAL (out/sweep.json -- real `cargo check`
   diagnostics against an injected chip crate, not a text match). The driver
   source is shared across the F4 family but the constraint set is not, so
   tracing an F407 application against RM0368 sites would be a cross-chip join.
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

# Each application is traced against THE MANUAL FOR ITS OWN CHIP. This used to
# be one `--rm` default inherited from the retired patch_hal.py, which pointed
# at RM0368 (STM32F401) -- the chip of none of these three. The driver source is
# shared across the F4 family, so the call paths were real, but whether the
# constraint applies to the application's part was never asked.
APPS = {
    "booster": ("RF power-amplifier firmware (F407)", "rm0090"),
    "px4flow_bsp": ("optical-flow sensor board support (F407)", "rm0090"),
    "stm32f469i-disc": ("discovery-board BSP (F469)", "rm0386"),
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


def sweep_sites(rm: str, crate: str) -> list:
    """Enforcement sites for one (manual, driver), from the sweep summary.

    Each row carries file, line, register, operation AND the triage verdict --
    `corroborated` where the driver already establishes the precondition,
    `unchecked` where it does not. The retired patch_hal.py had no verdict, so
    a caller could not tell a finding from an already-safe access.

    NOTE: the sweep stores at most 40 rows per pairing and reports the rest in
    `triage_truncated`; a pairing over that cap yields a sample, not the set.
    """
    out = []
    for name in ("sweep.json", "register_only/sweep.json"):
        p = OUT / name
        if not p.is_file():
            continue
        for t in json.loads(p.read_text()):
            if t["rm"] != rm:
                continue
            for h in t.get("hal_results") or []:
                if h.get("crate") != crate:
                    continue
                if h.get("triage_truncated"):
                    print(f"  WARNING: {h['triage_truncated']} site(s) beyond "
                          f"the sweep's 40-row cap are not listed")
                out.extend(h.get("triage") or [])
        if out:
            # Returned, not just used: the two sweeps gate different things, so
            # a reader has to be told which one these rows describe rather than
            # discovering it from a silent fallback.
            return out, name
    return out, "none"


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

_FALLBACK_FIELDS = {"ccr": ["pe"], "trise": ["pe"], "cr1": ["spe", "pe", "ue"],
                    "cr2": ["pe"], "brr": ["ue"], "dr": ["ue", "te"],
                    "prlh": ["cnf"], "prll": ["cnf"], "crh": ["cnf"]}


def precondition_fields(site: dict) -> list:
    """Fields the datasheet rule depends on.

    The sweep row already carries them, computed from the constraint that
    produced the gate. The hand-written table below is the fallback and used to
    be the ONLY source, because the retired patch_hal.py recorded a diagnostic
    string and no fields; it covers nine registers and silently returned [] for
    everything else, which reads as "no precondition to look for" rather than
    "we did not know"."""
    fields = site.get("fields")
    if fields:
        return list(fields)
    reg = str(site.get("register") or "").split("::")[-1]
    return _FALLBACK_FIELDS.get(reg.removesuffix("rs").lower(), [])


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

# `Base64Display::with_config(..)` -- the qualifier is what lets a call be
# rejected as belonging to another crate.
_APP_CALL_RE = re.compile(r"(?:(?P<qual>[A-Z]\w*)\s*::\s*)?"
                          r"(?:\.|::|\b)(?P<name>[a-z_]\w*)\s*\(")


def app_calls(root: Path) -> tuple:
    """(calls, defined) for one application.

    calls   method name -> [(file, line, source line, qualifier)]. The
            qualifier is the `Foo` of an explicit `Foo::bar(..)` and None for
            `x.bar(..)`, whose receiver type needs inference to know.
    defined function names the APPLICATION ITSELF declares. booster declares
            its own `convert`, which forwards to the driver's; without this,
            `self.pins.output_power.convert(..)` was counted as a call into
            the driver on the strength of the shared name."""
    calls, defined = defaultdict(list), set()
    for f in sorted(root.rglob("*.rs")):
        if "target" in f.parts:
            continue
        try:
            lines = f.read_text(errors="replace").splitlines()
        except OSError:
            continue
        rel = str(f.relative_to(root))
        in_block = False
        for i, text in enumerate(lines):
            # Commented-out code is not a call. booster's only "affected
            # today" site was a 40-line commented-out block, which made an app
            # look impacted by a path it does not take.
            stripped = text.strip()
            if in_block:
                if "*/" in stripped:
                    in_block = False
                continue
            if stripped.startswith("/*"):
                in_block = "*/" not in stripped
                continue
            if stripped.startswith("//"):
                continue
            # A declaration is not a call. `pub fn convert(&self, ..)` was
            # being read as a call to the driver's `convert`.
            fm = _FN_RE.match(text)
            if fm:
                defined.add(fm.group("name"))
                continue
            for m in _APP_CALL_RE.finditer(text):
                n = m.group("name")
                if n not in _NOISE:
                    calls[n].append((rel, i + 1, text.strip()[:130],
                                     m.group("qual")))
    return calls, defined


# --------------------------------------------------------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apps-dir", default=None,
                    help="directory holding the cloned applications")
    ap.add_argument("--hal", default=str(HAL_SRC))
    # A FILTER now, not a default. It used to be a single hardcoded manual
    # inherited from patch_hal.py, which silently traced every application
    # against RM0368 whatever chip it actually ran on.
    ap.add_argument("--rm", action="append", default=[],
                    help="restrict to these manuals (default: each app's own)")
    ap.add_argument("--hal-crate", dest="hal_crate", default="stm32f4xx-hal")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    hal = Path(args.hal)
    if not hal.is_dir():
        sys.exit(f"driver source not found: {hal}")
    apps_dir = Path(args.apps_dir) if args.apps_dir else None
    if apps_dir is None or not apps_dir.is_dir():
        sys.exit("--apps-dir must point at the cloned applications")

    # The call graph is a property of the driver, not of any one manual, so it
    # is built once and reused across them.
    fns = index_functions(hal)
    rev = callers_of(fns)
    driver_types = {f.impl_ty for f in fns if f.impl_ty}
    print(f"driver: {hal.name}  ({len(fns)} functions, "
          f"{len(driver_types)} types)\n")

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

    results, traced = [], {}
    wanted = set(args.rm)
    for rm in sorted({m for _, m in APPS.values()}):
        if wanted and rm not in wanted:
            continue
        apps = [n for n, (_, m) in APPS.items() if m == rm]

        # From the sweep, which is the finding pipeline. patch_hal.py used to
        # supply this and was retired: its list recorded every site it managed
        # to rewrite, with no triage, so on stm32f4xx-hal all seven entries were
        # sites the driver already guarded and none of the four real candidates
        # appeared.
        sites, src = sweep_sites(rm, args.hal_crate)
        if not sites:
            print(f"!! no enforcement sites for {rm}/{args.hal_crate} in "
                  f"{OUT}/sweep.json -- skipping {', '.join(apps)}\n")
            continue
        cand = [s for s in sites if s.get("verdict") == "unchecked"]
        print(f"--- {rm} [{src}]: {len(sites)} compile-confirmed sites, "
              f"{len(cand)} unguarded")

        entries = {}
        for s in sites:
            fn = enclosing(fns, s["file"], s["line"])
            if fn is None:
                continue
            eps = public_entry_points(fns, rev, fn)
            fields = precondition_fields(s)
            entries[(s["file"], s["line"])] = {
                "site": s, "inner": fn.label, "fields": fields,
                "entries": [{"label": e.label, "name": e.name, "file": e.file,
                             "line": e.start,
                             "path": " -> ".join(f.label for f in path),
                             **classify(path, fields)}
                            for e, path in eps],
            }
        traced[rm] = {f"{k[0]}:{k[1]}": v for k, v in entries.items()}

        reachable_names, ambiguous_names = defaultdict(set), defaultdict(set)
        for key, rec in entries.items():
            for e in rec["entries"]:
                bucket = (reachable_names if len(all_names[e["name"]]) == 1
                          else ambiguous_names)
                bucket[e["name"]].add(key)

        for name in apps:
            desc = APPS[name][0]
            root = apps_dir / name
            if not root.is_dir():
                print(f"!! {name}: not cloned, skipping")
                continue
            calls, defined = app_calls(root)
            touched, foreign, unresolved = [], set(), []
            for meth, keys in reachable_names.items():
                # An explicit `Type::method(..)` in the application NAMES the
                # type it is calling. If the driver does not define that type,
                # the match is a same-name collision with another crate --
                # px4flow's `Base64Display::with_config` was reported as the
                # driver's `Rtc::with_config` and counted as a finding, because
                # the name is unique WITHIN the driver, which is the only thing
                # the ambiguity check above looks at.
                here = []
                for f, ln, srcline, qual in calls.get(meth, ()):
                    if qual and qual not in driver_types:
                        foreign.add(f"{qual}::{meth}")
                        continue
                    here.append((f, ln, srcline))
                # The application declares a function of this name too, so
                # `x.convert(..)` could be either its own or the driver's and
                # only the receiver's type decides -- which needs inference
                # this tool does not do. Shown to a human, never counted:
                # three of booster's four claimed sites were its own method.
                if meth in defined:
                    unresolved += [(meth, f, ln, srcline) for f, ln, srcline
                                   in here]
                    continue
                for key in keys:
                    rec = entries[key]
                    ent = next(e for e in rec["entries"] if e["name"] == meth)
                    site = f"{rec['site']['file']}:{rec['site']['line']}"
                    for f, ln, srcline in here:
                        touched.append({
                            "app_call": meth, "app_file": f, "app_line": ln,
                            "app_src": srcline,
                            "driver_entry": ent["label"],
                            "driver_inner": rec["inner"],
                            "register": rec["site"]["register"].split("::")[-1],
                            "operation": rec["site"]["operation"],
                            "site": site,
                            # Examples are the application for a BSP whose own
                            # crate is a library, so they are kept -- but
                            # labelled, because scan_projects deliberately
                            # excludes them and the two must be comparable.
                            "in_example": f.startswith(("examples/", "tests/")),
                            "verdict": ent["verdict"],
                            "evidence": ent["evidence"],
                            # The sweep's triage of the DRIVER site:
                            # `unchecked` means the driver does not establish
                            # the precondition today. That is a different fact
                            # from `escaping`, which is about what would remain
                            # after the driver is fixed.
                            "driver_site_verdict": rec["site"].get("verdict", ""),
                        })
            amb = sorted({m for m in ambiguous_names if m in calls})
            esc = [t for t in touched if t["verdict"] == "escaping"]
            con = [t for t in touched if t["verdict"] == "contained"]
            # TWO DIFFERENT QUESTIONS, and conflating them reads as one result.
            #
            #   AFFECTED TODAY -- the app calls a driver function whose register
            #   access the sweep marks `unchecked`: the driver does not
            #   establish the precondition, so this app is running on a broken
            #   path NOW, whether or not the constraint would escape a fixed
            #   driver.
            #
            #   RESIDUAL AFTER A FIX -- the constraint ESCAPES: even a correct
            #   driver cannot discharge it alone, because the obligation depends
            #   on what the caller does. Fixing the driver leaves the app work.
            #
            # A constraint can be one, the other, both or neither.
            today = [t for t in touched
                     if t["driver_site_verdict"] == "unchecked"]
            print(f"\n=== {name} ({desc}, {rm})")
            print(f"    driver entry points it calls that reach a gated "
                  f"register: {len({t['driver_entry'] for t in touched})}")
            print(f"    AFFECTED TODAY (driver violates the rule on this "
                  f"path): {len(today)}")
            for x in today[:6]:
                ex = "  [example]" if x["in_example"] else ""
                print(f"      {x['app_file']}:{x['app_line']}  "
                      f"{x['app_call']}() -> {x['driver_entry']} -> "
                      f"{x['driver_inner']} -> {x['register']} "
                      f"{x['operation']}   @{x['site']}{ex}")
            if len(today) > 6:
                print(f"      ... and {len(today) - 6} more, in the json")
            print(f"    RESIDUAL AFTER A DRIVER FIX: {len(esc)} escaping, "
                  f"{len(con)} contained")
            for x in esc[:8]:
                ex = "  [example]" if x["in_example"] else ""
                print(f"      {x['app_file']}:{x['app_line']}  "
                      f"{x['app_call']}() -> {x['driver_entry']} -> "
                      f"{x['register']} {x['operation']}   @{x['site']}{ex}")
                print(f"        {x['app_src']}")
            if len(esc) > 8:
                print(f"      ... and {len(esc) - 8} more, in the json")
            if amb:
                print(f"    ambiguous method names (not claimed): "
                      f"{', '.join(amb)}")
            if foreign:
                print(f"    rejected, another crate's type: "
                      f"{', '.join(sorted(foreign))}")
            if unresolved:
                print(f"    UNRESOLVED -- the app declares a function of the "
                      f"same name, so the receiver decides and we do not "
                      f"infer types ({len(unresolved)}):")
                for meth, f, ln, srcline in unresolved[:8]:
                    print(f"      {f}:{ln}  {meth}()   {srcline[:88]}")
            results.append({"app": name, "desc": desc, "rm": rm,
                            "sweep": src, "sites": len(sites),
                            "touched": touched, "affected_today": len(today),
                            "escaping": len(esc), "contained": len(con),
                            "ambiguous": amb, "rejected_foreign":
                            sorted(foreign),
                            "unresolved": [{"call": m, "file": f, "line": ln,
                                            "src": s}
                                           for m, f, ln, s in unresolved]})
        print()

    out = Path(args.out) if args.out else OUT / "trace_hal.json"
    out.write_text(json.dumps(
        {"hal": hal.name, "entries": traced, "apps": results},
        indent=1, default=str) + "\n")
    print(f"json: {out}")


if __name__ == "__main__":
    main()
