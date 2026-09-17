#!/usr/bin/env python3
"""port_anne_key.py -- does the SCANNER agree with the COMPILER?

WHY THIS ONE
------------
`scan_projects.py` reads a project's source and reports register accesses that
a datasheet constrains. Nothing checks that claim. Every other number in this
project comes from a compiler; the scanner's does not, and it is the number the
landscape page is built on.

anne-key is the cheapest place to check it. It is a keyboard firmware that
drives an STM32L151 through the PAC directly, 91 register accesses, and the
scanner claims exactly 3 constrained sites -- all in one function, all on
FLASH_ACR, all verdict `corroborated`. Small enough to port, specific enough
that agreement or disagreement means something.

    RM0038  FLASH_ACR.PRFTEN   write requires ACC64 set
            FLASH_ACR.LATENCY  write requires ACC64 set

    src/clock.rs:6   p.FLASH.acr.modify(|_, w| w.acc64().set_bit());
    src/clock.rs:7   p.FLASH.acr.modify(|_, w| w.prften().set_bit());
    src/clock.rs:8   p.FLASH.acr.modify(|_, w| w.latency().set_bit());

THE PREDICTION, made before building
------------------------------------
The scanner works at REGISTER granularity: it flags any write to a register
that carries a constraint, so it flags all three lines. Field gating is finer
-- it gates only PRFTEN and LATENCY, the fields the manual actually names --
so line 6, which writes ACC64, should not fire. Two hits, not three, and both
guarded, because ACC64 is established on line 6 before either.

RESULT

    scanner (static, register granularity)      3 sites, 3 corroborated
    field gating (compiler)                     2 sites, 2 guarded, 0 bugs
    whole-register gating (compiler)            0 sites

The scanner's verdict is right and its count is coarse, in the direction its
granularity predicts. The register-only zero is the other half of the same
fact: RM0038 constrains two FIELDS of ACR and nothing about the register as a
whole, so whole-register mode has nothing to gate and drops ACR entirely.

THE PORT
--------
anne-key pins stm32l1 0.11.0; the injector targets 0.16.0. Nine rules, each
dictated by a compiler error rather than guessed, and R7 and R9 are findings in
their own right:

  R1  DMA per-channel registers (ccr1, cndtr1, cpar1, cmar1) became a CH
      cluster: ch1().cr(), ch1().ndtr(), and their types moved to `dma1::ch`.
  R2  Register-block fields became accessor methods: `.acr` -> `.acr()`.
      Applied from the compiler's own list of names, not a guessed one, and
      repeated until the class is empty. R2c covers chains split across lines.
  R6  `Reg::write`/`modify` return the written value where they returned ();
      callers that declare no return type must discard it.
  R7  EP0R and EP1R were distinct Rust types and are now one EPR behind eight
      accessors. anne-key used that distinction to give endpoint 1 a DIFFERENT
      toggle_tx_out -- without EP_STATUS_OUT -- and one type cannot carry two
      impls of one trait. Behaviour is preserved by naming the endpoint-1 body
      separately; what is lost is the type system choosing it for you. This is
      the only place the newer PAC destroys a distinction the application was
      relying on.
  R8  Field writers' `bits()` is unsafe where it was safe.
  R9  RTFM 0.4.2 bounds interrupts on `bare_metal::Nr`, which svd2rust no
      longer emits -- it emits `cortex_m::interrupt::InterruptNumber`. An
      application on RTFM 0.4 therefore cannot name ANY interrupt from a modern
      PAC. This is an ABI mismatch between the application's framework and the
      PAC generation, with nothing to do with the registers under test, so it
      is shimmed rather than worked around. cortex-m 0.7 carries a blanket
      `impl<T: Nr + Copy> InterruptNumber for T`, so the shim REPLACES the
      generated impl instead of joining it -- writing both is a conflicting
      implementation. It touches no register and no gate.

The baseline is checked before anything is injected and must be zero errors;
otherwise a gate hit cannot be told from a port defect, and nothing is counted.

Usage:
    python applications/pac_codegen/experiments/port_anne_key.py --work DIR
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
REPO = APP_DIR.parent.parent
sys.path.insert(0, str(APP_DIR / "experiments"))
import enforcement                                   # noqa: E402
import corroboration                                 # noqa: E402

OUT = APP_DIR / "experiments" / "out"
PHASE1D = Path("/home/ramla/hal_agent-phase-1d")
RM, DEVICE, PAC_CRATE = "rm0038", "stm32l151", "stm32l1"
APP_REPO = "https://github.com/ah-/anne-key"
HAL_REPO = "https://github.com/hdhoang/stm32l151-hal"
HAL_BRANCH = "stm32l1-0.11"
# anne-key pins nightly-2020-03-19, whose cargo can no longer read the
# crates.io index. The code itself builds on a current nightly.
TOOLCHAIN = "+nightly-2025-06-23"
TARGET = "thumbv7m-none-eabi"
TIMEOUT = 1800


def run(cmd, cwd=None, **kw):
    return subprocess.run(cmd, cwd=cwd and str(cwd), capture_output=True,
                          text=True, timeout=TIMEOUT, **kw)


def clone(url, dest: Path, branch=None):
    """Clone, or RESET an existing clone to pristine.

    The port below is a sequence of textual edits, and making every one of them
    idempotent is a losing game -- the first re-run inserted a trait method a
    second time and the baseline failed with a duplicate-definition error that
    had nothing to do with the port. These are git checkouts, so resetting them
    is exact and costs nothing. `target/` is kept: it is untracked build cache,
    and throwing it away turns every re-run into a full rebuild."""
    if dest.is_dir():
        run(["git", "checkout", "--", "."], cwd=dest)
        run(["git", "clean", "-fdq", "-e", "target"], cwd=dest)
        return dest
    cmd = ["git", "clone", "-q", "--depth", "1"]
    if branch:
        cmd += ["-b", branch]
    run(cmd + [url, str(dest)])
    return dest


def sub_count(text, pattern, repl, flags=0):
    new, n = re.subn(pattern, repl, text, flags=flags)
    return new, n


# --------------------------------------------------------------------------- #
# The port
# --------------------------------------------------------------------------- #

def port_pac(pac: Path) -> None:
    """R9: the RTFM 0.4 / modern-svd2rust interrupt ABI shim."""
    c = pac / "Cargo.toml"
    t = c.read_text()
    if "[dependencies.bare-metal]" not in t:
        c.write_text(t.replace(
            "[dependencies.cortex-m]",
            '[dependencies.bare-metal]\nversion = "0.2.5"\n\n'
            '[dependencies.cortex-m]', 1))
    m = pac / "src" / DEVICE / "mod.rs"
    t = m.read_text()
    generated = """unsafe impl cortex_m::interrupt::InterruptNumber for Interrupt {
    #[inline(always)]
    fn number(self) -> u16 {
        self as u16
    }
}"""
    if "bare_metal::Nr" in t:
        return
    if generated not in t:
        sys.exit("R9: the generated InterruptNumber impl was not found")
    m.write_text(t.replace(generated, """// BUILD-COMPATIBILITY SHIM (R9), not a constraint change. RTFM 0.4.2 bounds
// its interrupt argument on bare_metal::Nr, which svd2rust no longer emits.
// cortex-m 0.7 carries a blanket impl<T: Nr + Copy> InterruptNumber for T, so
// this REPLACES the generated impl rather than joining it. Touches no register.
unsafe impl bare_metal::Nr for Interrupt {
    #[inline(always)]
    fn nr(&self) -> u8 {
        *self as u8
    }
}""", 1))


def port_hal(hal: Path) -> dict:
    """R1, R2, R6 in the tiny git HAL anne-key depends on."""
    counts = {}
    d = hal / "src" / "dma.rs"
    t = d.read_text()
    t = t.replace("""            $($CX:ident: (
                $ccrX:ident,
                $CCRX:ident,
                $cndtrX:ident,
                $CNDTRX:ident,
                $cparX:ident,
                $CPARX:ident,
                $cmarX:ident,
                $CMARX:ident,
                $htifX:ident,""", """            $($CX:ident: (
                $chX:ident,
                $htifX:ident,""")
    t = t.replace("(*$DMAX::ptr()).isr.read()", "(*$DMAX::ptr()).isr().read()")
    t = t.replace("(*$DMAX::ptr()).ifcr.write", "(*$DMAX::ptr()).ifcr().write")
    for hal_fn, pac_fn, ty, var in (("ccr", "cr", "CR", "$ccrX"),
                                    ("cndtr", "ndtr", "NDTR", "$cndtrX"),
                                    ("cpar", "par", "PAR", "$cparX"),
                                    ("cmar", "mar", "MAR", "$cmarX")):
        old_ty = {"ccr": "$CCRX", "cndtr": "$CNDTRX",
                  "cpar": "$CPARX", "cmar": "$CMARX"}[hal_fn]
        t = t.replace(
            f"pub fn {hal_fn}(&mut self) -> &dma1::{old_ty} {{\n"
            f"                            unsafe {{ &(*$DMAX::ptr()).{var} }}\n"
            f"                        }}",
            f"pub fn {hal_fn}(&mut self) -> &dma1::ch::{ty} {{\n"
            f"                            unsafe {{ (*$DMAX::ptr()).$chX().{pac_fn}() }}\n"
            f"                        }}")
    t, counts["dma_channels"] = sub_count(
        t, r"\n\s*ccr(\d), CCR\1,\n\s*cndtr\1, CNDTR\1,"
           r"\n\s*cpar\1, CPAR\1,\n\s*cmar\1, CMAR\1,",
        lambda m: f"\n            ch{m.group(1)},")
    for fn in ("ctcif", "chtif", "cgif"):
        t = t.replace(
            f"unsafe {{ (*$DMAX::ptr()).ifcr().write(|w| w.${fn}X().set_bit()) }}",
            f"unsafe {{ (*$DMAX::ptr()).ifcr().write(|w| w.${fn}X().set_bit()); }}")
    d.write_text(t)

    g = hal / "src" / "gpio.rs"
    t = g.read_text()
    n = 0
    for fld in ("moder", "pupdr", "idr", "bsrr", "$afr"):
        n += t.count(f"::ptr()).{fld}.")
        t = t.replace(f"::ptr()).{fld}.", f"::ptr()).{fld}().")
    counts["gpio_accessors"] = n
    for sh in ("1 << $i", "1 << (16 + $i)"):
        t = t.replace(
            f"Ok(unsafe {{ (*$GPIOX::ptr()).bsrr().write(|w| w.bits({sh})) }})",
            f"Ok(unsafe {{ (*$GPIOX::ptr()).bsrr().write(|w| w.bits({sh})); }})")
    g.write_text(t)
    return counts


def port_app(app: Path) -> dict:
    """R7 and R8 by hand; R2 driven by the compiler in `converge` below."""
    counts = {}
    e = app / "src" / "usb" / "usb_ext.rs"
    t = e.read_text()
    t = t.replace("use stm32l1::stm32l151::usb::{EP0R, EP1R};",
                  "use stm32l1::stm32l151::usb::EPR;")
    t = t.replace(
        "    fn toggle_tx_out(&self);",
        "    fn toggle_tx_out(&self);\n"
        "    /// R7: endpoint 1's variant, without EP_STATUS_OUT. In PAC 0.11\n"
        "    /// EP0R and EP1R were distinct types and each carried its own\n"
        "    /// impl; 0.16 gives both endpoints one EPR type, so the choice\n"
        "    /// moves from the type system to the call site.\n"
        "    fn toggle_tx_out_ep1(&self);")
    t = t.replace("impl UsbEpExt for EP0R {", "impl UsbEpExt for EPR {")
    m = re.search(r"\nimpl UsbEpExt for EP1R \{.*?\n\}\n", t, re.S)
    if m:
        t = t[:m.start()] + "\n" + t[m.end():]
        counts["ep1r_impl_folded"] = 1
    t = t.replace("""    fn toggle_out(&self) {
        self.toggle(EP_TX_RX_MASK, EP_TX_RX_VALID, EP_STATUS_OUT)
    }""", """    fn toggle_tx_out_ep1(&self) {
        self.toggle(EP_TX_MASK, EP_TX_VALID, 0)
    }

    fn toggle_out(&self) {
        self.toggle(EP_TX_RX_MASK, EP_TX_RX_VALID, EP_STATUS_OUT)
    }""", 1)
    t = t.replace(
        "self.modify(|r, w| unsafe { w.bits(((r.bits() & (EP_MASK | mask)) ^ val) | flags) })",
        "self.modify(|r, w| unsafe { w.bits(((r.bits() & (EP_MASK | mask)) ^ val) | flags) });")
    e.write_text(t)

    h = app / "src" / "usb" / "hid.rs"
    t = h.read_text()
    h.write_text(t.replace("usb.ep1r.toggle_tx_out();",
                           "usb.ep1r().toggle_tx_out_ep1();"))

    return counts


def port_app_unsafe(app: Path) -> dict:
    """R8: field writers' `bits()` is unsafe where it was safe.

    MUST RUN AFTER `converge`. These patterns name the accessor in its ported
    form -- `ep0r()` -- so running them first matches nothing and the baseline
    fails with seven E0133s that look like a porting gap rather than an
    ordering mistake. That is exactly what happened the first time.
    """
    u = app / "src" / "usb" / "mod.rs"
    t = u.read_text()
    n = 0
    for old, new in (
        ("self.usb.ep0r().modify(|_, w| {\n            w.ep_type()",
         "self.usb.ep0r().modify(|_, w| unsafe {\n            w.ep_type()"),
        ("self.usb.ep1r().modify(|_, w| {\n            w.ep_type()",
         "self.usb.ep1r().modify(|_, w| unsafe {\n            w.ep_type()"),
        (".modify(|_, w| w.add().bits(self.pending_daddr));",
         ".modify(|_, w| unsafe { w.add().bits(self.pending_daddr) });"),
    ):
        if old in t:
            n += 1
            t = t.replace(old, new)
        elif new not in t:
            # Neither form present: the upstream source moved under us, which
            # is worth stopping for. Already-ported is fine -- the script has
            # to be re-runnable on an existing work directory.
            sys.exit(f"R8: neither form found, the port drifted: {old[:48]!r}")
    u.write_text(t)
    return {"unsafe_bits_wrapped": n}


_NAME_RE = re.compile(r"(?:method|field) `([a-z0-9_]+)` (?:on type|of struct)")


def converge(app: Path, rounds: int = 12) -> dict:
    """R2: rewrite `.reg` to `.reg()` using the names RUSTC asks for.

    Never a guessed list. Each round reads the diagnostics, rewrites exactly
    the accessors they name, and stops when the class is empty or a round
    changes nothing -- a round that finds names but edits no file means the
    remaining sites are in a shape these patterns do not reach, and silently
    looping forever would hide that.
    """
    src = app / "src"
    seen = {}
    for i in range(1, rounds + 1):
        err = run(["cargo", TOOLCHAIN, "check", "--target", TARGET],
                  cwd=app).stderr
        names = sorted(set(_NAME_RE.findall(err)))
        if not names:
            return {"rounds": i, "converged": True, "accessors": seen}
        touched = 0
        for f in sorted(src.rglob("*.rs")):
            t = f.read_text()
            before = t
            for name in names:
                t = re.sub(rf"\.{name}\.(?![a-z_]*\()", f".{name}().", t)
                t = re.sub(rf"\.{name}\.(\w)", rf".{name}().\1", t)
                # R2c: the same chain, split across lines.
                t = re.sub(rf"\.{name}\n(\s*)\.", rf".{name}()\n\1.", t)
            if t != before:
                f.write_text(t)
                touched += 1
        seen[i] = names
        if not touched:
            return {"rounds": i, "converged": False, "accessors": seen,
                    "stuck_on": names}
    return {"rounds": rounds, "converged": False, "accessors": seen}


# --------------------------------------------------------------------------- #

def errors(app: Path) -> list:
    """Compiler errors -- and a hard stop if the compiler never ran.

    THE TRAP THIS CLOSES. A manifest error, an unresolvable dependency or a
    missing toolchain makes cargo exit before it compiles anything, so it emits
    NO `compiler-message` records at all. Reading only those records, such a
    build is indistinguishable from a clean one: this function returned [], the
    baseline gate read PASS, and the injected build reported 0 gate hits. That
    is exactly what happened when a re-run appended a second [patch] section
    and cargo refused the manifest -- a run that compiled nothing was reported
    as a project with no violations.

    So a non-zero exit with no compiler errors to explain it is fatal, not
    empty."""
    r = run(["cargo", TOOLCHAIN, "check", "--target", TARGET,
             "--message-format=json"], cwd=app)
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
        sys.exit(f"cargo failed without emitting a single compiler error, so "
                 f"nothing was compiled and nothing can be concluded:\n"
                 f"{(r.stderr or r.stdout)[-1200:]}")
    return out


def inject(pac: Path, work: Path, register_only: bool) -> dict:
    tag = "regonly" if register_only else "field"
    saved = work / f"anne_constraints_{tag}.json"
    report = work / f"anne_inject_{tag}.json"
    argv = [sys.executable, str(APP_DIR / "inject_from_run.py"),
            "--save-constraints", str(saved),
            str(PHASE1D / f"agent_output/stm/{RM}/1"),
            "--pac", str(pac), "--device", DEVICE,
            "--svd-dir", str(PHASE1D / f"devices/stm/{RM}/svd/{DEVICE}.svd"),
            "--constraints", str(PHASE1D /
                                 f"evaluation/stm/{RM}/1/{RM}_constraints_review.jsonl"),
            "--attribution-check", str(PHASE1D / "chunked_datasheets/stm"),
            "--report", str(report)]
    if register_only:
        argv.append("--register-only")
    r = run(argv, cwd=REPO)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout)[-600:]}
    out = json.loads(report.read_text())
    out["_constraints"] = json.loads(saved.read_text()) if saved.is_file() else {}
    return out


def measure(app: Path, pac: Path, work: Path, register_only: bool) -> dict:
    run(["cargo", TOOLCHAIN, "clean", "-p", PAC_CRATE], cwd=app)
    rep = inject(pac, work, register_only)
    if "error" in rep:
        return {"error": rep["error"]}
    # The injector rewrites the same tree cargo cached, so a stale .rmeta would
    # report gates from a crate that is pristine on disk.
    run(["cargo", TOOLCHAIN, "clean", "-p", PAC_CRATE], cwd=app)
    hits, other = [], 0
    for d in errors(app):
        h = enforcement.classify_diagnostic(d)
        if h is None:
            other += 1
            continue
        spans = [s for s in d.get("spans") or [] if s.get("is_primary")]
        if not spans:
            other += 1
            continue
        f, line = spans[0]["file_name"], spans[0]["line_start"]
        fields = []
        for e in (rep["_constraints"] or {}).get("registers", []):
            for fg in (e.get("gated_fields") or {}).values():
                for p in fg.get("preconditions") or []:
                    fields.append(p.split()[0].rsplit(".", 1)[-1].lower())
        fields = sorted(set(fields))
        verdict = "untriaged"
        path = app / f
        if path.is_file() and fields:
            start, snip = corroboration.enclosing_function(str(path), line)
            verdict = corroboration.deterministic_scan(
                snip, line - start, fields)["verdict"]
        hits.append({"file": f, "line": line, "register": h.spec,
                     "field": h.field, "operation": h.operation,
                     "fields": fields, "verdict": verdict})
    return {"registers_planned": rep.get("registers_planned"),
            "hits": hits, "collateral": other,
            "guarded": sum(1 for x in hits if x["verdict"] == "corroborated"),
            "possible_bug": sum(1 for x in hits if x["verdict"] == "unchecked")}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", required=True,
                    help="scratch directory for the clones and the PAC copy")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    app = clone(APP_REPO, work / "anne-key")
    hal = clone(HAL_REPO, work / "stm32l151-hal", HAL_BRANCH)
    # A COPY. The shared vendored crate feeds every other measurement in this
    # project, and R9 would contaminate all of them.
    pac = work / "stm32l1-anne"
    if pac.is_dir():
        shutil.rmtree(pac)
    shutil.copytree(APP_DIR / "vendored" / "pac" / PAC_CRATE, pac,
                    ignore=shutil.ignore_patterns("target"))

    # After the reset above, not before: the pin is a tracked file.
    (app / "rust-toolchain").unlink(missing_ok=True)
    for man, extra in ((app / "Cargo.toml",
                        f'\n[patch."{HAL_REPO}"]\n'
                        f'stm32l151-hal = {{ path = "{hal}" }}\n'),
                       (hal / "Cargo.toml", "")):
        t = man.read_text()
        # A path dependency, not [patch.crates-io]: 0.16.0 does not satisfy
        # `^0.11.0`, so cargo declines the patch and says so only in a warning.
        for req in ('version = "0.11.0"', 'version = "0.11"'):
            t = t.replace(
                f'[dependencies.stm32l1]\nfeatures = ["stm32l151", "rt"]\n{req}',
                f'[dependencies.stm32l1]\nfeatures = ["stm32l151", "rt"]\n'
                f'path = "{pac}"')
        # Appending unconditionally added a SECOND [patch] section on a
        # re-run, which is an invalid manifest -- see `errors` for what that
        # then looked like.
        man.write_text(t if (extra and extra.strip() in t) else t + extra)

    port_pac(pac)
    counts = port_hal(hal)
    counts.update(port_app(app))
    counts.update(converge(app))
    counts.update(port_app_unsafe(app))

    base = errors(app)
    if base:
        sys.exit(f"BASELINE FAILS ({len(base)} errors) -- nothing is "
                 f"measurable; a gate hit could not be told from a port defect")
    print("baseline PASS (0 errors against the pristine 0.16 PAC)")

    result = {"project": "anne-key", "rm": RM, "device": DEVICE,
              "pac": f"{PAC_CRATE} 0.16.0", "port": counts,
              "baseline": "PASS"}
    for mode, reg_only in (("field", False), ("register_only", True)):
        shutil.rmtree(pac)
        shutil.copytree(APP_DIR / "vendored" / "pac" / PAC_CRATE, pac,
                        ignore=shutil.ignore_patterns("target"))
        port_pac(pac)
        result[mode] = measure(app, pac, work, reg_only)
        r = result[mode]
        print(f"{mode:14s} registers gated {r.get('registers_planned')}  "
              f"hits {len(r.get('hits') or [])}  "
              f"guarded {r.get('guarded')}  bug {r.get('possible_bug')}")
        for h in r.get("hits") or []:
            print(f"    {h['file']}:{h['line']}  {h['register']}.{h['field']} "
                  f"{h['operation']}  {h['verdict']}")

    # The landscape page renders one shape for every measured project; anne-key
    # reports in it rather than growing a second renderer. `field` is the
    # headline because field gating is the default mode.
    f = result["field"]
    result.update({
        "mechanical_edits": sum(v for v in counts.values()
                                if isinstance(v, int)),
        "registers_gated": f.get("registers_planned"),
        "gate_fired": len(f.get("hits") or []),
        "collateral": f.get("collateral", 0),
        "hits": f.get("hits") or [],
        "triage_caveat":
            "the scanner claimed 3 sites and the compiler fired on 2; the "
            "third writes ACC64, which is the PRECONDITION rather than a "
            "constrained field, so field gating correctly leaves it alone. "
            "Whole-register mode fires on none of them: RM0038 constrains two "
            "fields of FLASH_ACR and nothing about the register as a whole",
    })

    p = Path(args.out) if args.out else OUT / "port_anne_key.json"
    p.write_text(json.dumps(result, indent=1) + "\n")
    print(f"report: {p}")


if __name__ == "__main__":
    main()
