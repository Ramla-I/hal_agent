#!/usr/bin/env python3
"""STM-wide injection sweep: every reference manual with validated constraints,
injected into its PAC crate, then compiled -- probe crate and (where a released
HAL pairs with the PAC) the real third-party HAL.

This generalizes experiments/cross_pac.py from four hand-picked fixtures to the
whole corpus, and swaps the fixture for the real pipeline artifact: each target
runs ``inject_from_run.py`` over the RM's generator run directory, gated on the
constraint validator (``--constraints``) and attribution-checked against the
chunked
datasheet (``--chunks``).

Per target:
    provision -> snapshot -> inject_from_run -> [probe check] -> [HAL check]
    -> restore -> verify the PAC tree byte-for-byte pristine.

The PAC tree is snapshotted BEFORE injection and restored even when a step
fails, so targets sharing a crate (four RMs share stm32f3) never contaminate
each other.

Two guards keep a run honest, and both exist because their absence produced
wrong numbers rather than an error:

* the PAC is verified PRISTINE before injection, not merely provisioned --
  get_pac's stamp file records the version, not the tree's state, so a crate
  left injected by a crash or a hand-run is otherwise snapshotted as if clean;
* ``patch_applied()`` reads Cargo.lock after every HAL check, because cargo
  does NOT fail when a ``[patch.crates-io]`` does not apply -- it warns and
  resolves the registry crate, so the whole experiment silently measures the
  UNPATCHED PAC and reports zero enforcement.

Usage:
    python applications/pac_codegen/experiments/stm_sweep.py --dry-run
    python applications/pac_codegen/experiments/stm_sweep.py --only rm0316
    python applications/pac_codegen/experiments/stm_sweep.py --skip-hal
    python applications/pac_codegen/experiments/stm_sweep.py --register-only
    python applications/pac_codegen/experiments/stm_sweep.py --only rm0008 \
        --keep-pac /tmp/kept          # inspect the injected crate afterwards
"""

import argparse
import hashlib
import json
import re
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
class Consumer:
    """A third-party crate that consumes the PAC and can therefore be compiled
    against the injected one. NOT limited to the family `*xx-hal` crate: any
    crates.io consumer whose released version depends on PAC 0.16.0 counts, and
    a reverse-dependency sweep finds more of them than stm.toml lists."""
    crate: str
    version: str
    features: list[str]
    note: str = ""


# (rm, device) injected IN ADDITION to that manual's representative chip, to
# measure something rather than to cover something. Excluded from the corpus
# tables so the rule stays "one device per manual", and reported separately.
CONTROL_DEVICES = {
    ("rm0440", "stm32g4a1"):
        "a second G4 part for the same manual and the same drivers, to show "
        "how much the choice of representative chip moves the numbers. G474 "
        "alone reaches all three G4 drivers, so this is not needed for "
        "coverage.",
}


@dataclass
class Target:
    rm: str
    pac: str            # crates.io PAC package
    device: str         # device module inside the PAC == cargo feature
    svd: str            # SVD basename for the collection lint
    consumers: list[Consumer] = field(default_factory=list)

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


# DEVICE SELECTION POLICY
#
# One device module per RM: the RM's primary chip, chosen so that every driver
# crate supporting that manual can select it. Checked across all 48 manuals --
# no manual needs a second device to reach a driver.
#
# The 48 manuals project onto 154 device modules in total, so this is one
# representative chip each, not the whole silicon line. That does not
# understate the constraints (a manual is read once, and its constraints are
# the same whichever chip they are applied to) but it does mean register
# counts are per representative chip: the spread across sibling chips of the
# same manual is not measured, except where noted below.
#
# Injection is per device module and generic.rs is patched crate-wide, so a
# device is injected from a pristine crate one at a time. That is a property
# of the harness, not a limit of the technique: in the 20 flat-layout crates
# the device modules are independent, and only stm32h7 shares register blocks
# between devices (188 of its 430 peripheral modules), where two devices'
# constraints could collide on one Rust type.
# stm32-hal2 is a SECOND, independent HAL family covering c0/f3/f4/g0/g4/h5/
# h7/l4/l5 -- and it is already on PAC 0.16.0. It is what makes the f3 family
# measurable at all: stm32f3xx-hal is ~850 errors away from this PAC
# generation (experiments/hal_gap.py), stm32-hal2 compiles against it clean.
def _hal2(feature: str) -> Consumer:
    return Consumer("stm32-hal2", "2.1.10", [feature],
                    note="second HAL family, already on PAC 0.16")


# WHY THE CONSUMER LIST IS SHORT, AND CANNOT SIMPLY BE LENGTHENED.
# A consumer is only measurable if its released version depends on PAC ^0.16 --
# the generation the injector targets. `[patch.crates-io]` does NOT error when
# the version requirement is unsatisfiable; it silently keeps the original
# crate, so an unpaired consumer compiles cleanly against a PRISTINE PAC and
# reports zero enforcement. (patch_applied() reads Cargo.lock to catch that.)
#
# A crates.io reverse-dependency sweep over all 21 PAC crates found exactly
# NINETEEN released consumers requiring ^0.16, and they collapse to six
# distinct crates. The first-party family HALs are mostly NOT among them:
#
#   stm32h7xx-hal 0.16.0 -> stm32h7 ^0.15.1     stm32f3xx-hal -> ^0.15.1
#   stm32f7xx-hal  0.8.0 -> stm32f7 ^0.15       stm32wlxx-hal -> ^0.15.1
#   stm32f0xx-hal 0.18.0 -> stm32f0 ^0.14       stm32l0xx-hal -> ^0.15.1
#   stm32l4xx-hal  0.7.1 -> stm32l4 ^0.14.0     stm32l1xx-hal -> ^0.5.0
#   stm32g0xx-hal  0.2.0 -> stm32g0 ^0.14.0
#
# Their git masters do not help: h7/f7/f0/f3/l0/l4 are still on 0.14/0.15, and
# stm32g0xx-hal master has moved PAST us to 0.17.0. Pairing them would mean
# injecting into the 0.14/0.15 svd2rust template, whose register API differs
# (field access vs accessor methods) -- the `pac-gap` blocker, not a config
# change. Adding them here would produce silent zeros, which is worse than
# an honest absence.
def _hrtim(feature: str) -> Consumer:
    return Consumer("stm32-hrtim", "0.2.0", [feature],
                    note="high-resolution timer driver; drives HRTIM "
                         "registers directly, and the most-downloaded "
                         "PAC-0.16 consumer of all")


TARGETS = [
    Target("rm0008", "stm32f1", "stm32f103", "stm32f103.svd", [
        Consumer("stm32f1xx-hal", "0.11.0", ["stm32f103", "medium"]),
        Consumer("stm32f1-hal", "0.14.1", ["f103", "medium"],
                 note="independent F1 HAL, also on PAC 0.16")]),
    Target("rm0033", "stm32f2", "stm32f215", "stm32f215.svd"),
    Target("rm0038", "stm32l1", "stm32l151", "stm32l151.svd"),
    Target("rm0091", "stm32f0", "stm32f0x1", "stm32f0x1.svd"),
    Target("rm0313", "stm32f3", "stm32f373", "stm32f373.svd", [_hal2("f373")]),
    Target("rm0316", "stm32f3", "stm32f303", "stm32f303.svd", [_hal2("f303")]),
    Target("rm0360", "stm32f0", "stm32f0x0", "stm32f0x0.svd"),
    Target("rm0365", "stm32f3", "stm32f302", "stm32f302.svd", [_hal2("f302")]),
    Target("rm0366", "stm32f3", "stm32f301", "stm32f301.svd", [_hal2("f301")]),
    Target("rm0367", "stm32l0", "stm32l0x3", "stm32l0x3.svd"),
    Target("rm0368", "stm32f4", "stm32f401", "stm32f401.svd", [
        Consumer("stm32f4xx-hal", "0.23.0", ["stm32f401"]), _hal2("f401"),
        Consumer("rivet-bsp-stm32f401re", "0.1.0", [],
                 note="board support package pinned to this exact chip")]),
    Target("rm0376", "stm32l0", "stm32l0x2", "stm32l0x2.svd"),
    Target("rm0377", "stm32l0", "stm32l0x1", "stm32l0x1.svd"),
    Target("rm0383", "stm32f4", "stm32f411", "stm32f411.svd", [
        Consumer("stm32f4xx-hal", "0.23.0", ["stm32f411"]), _hal2("f411")]),
    # stm32f7 has no crates.io consumer on PAC 0.16 at any version.
    Target("rm0385", "stm32f7", "stm32f746", "stm32f746.svd"),
    Target("rm0386", "stm32f4", "stm32f469", "stm32f469.svd", [
        Consumer("stm32f4xx-hal", "0.23.0", ["stm32f469"]), _hal2("f469")]),
    Target("rm0390", "stm32f4", "stm32f446", "stm32f446.svd", [
        Consumer("stm32f4xx-hal", "0.23.0", ["stm32f446"]), _hal2("f446")]),
    Target("rm0394", "stm32l4", "stm32l412", "stm32l412.svd", [_hal2("l412")]),
    Target("rm0401", "stm32f4", "stm32f410", "stm32f410.svd", [
        Consumer("stm32f4xx-hal", "0.23.0", ["stm32f410"]), _hal2("f410")]),
    Target("rm0402", "stm32f4", "stm32f412", "stm32f412.svd", [
        Consumer("stm32f4xx-hal", "0.23.0", ["stm32f412"]), _hal2("f412")]),
    # stm32f7 has no crates.io consumer on PAC 0.16 at any version.
    Target("rm0410", "stm32f7", "stm32f767", "stm32f767.svd"),
    Target("rm0430", "stm32f4", "stm32f413", "stm32f413.svd", [
        Consumer("stm32f4xx-hal", "0.23.0", ["stm32f413"]), _hal2("f413")]),
    Target("rm0431", "stm32f7", "stm32f722", "stm32f722.svd"),
    Target("rm0434", "stm32wb", "stm32wb55", "stm32wb55.svd", [_hal2("wb55")]),
    Target("rm0444", "stm32g0", "stm32g071", "stm32g071.svd", [_hal2("g071")]),
    # stm32l0 has no crates.io consumer on PAC 0.16 at any version.
    Target("rm0451", "stm32l0", "stm32l0x0", "stm32l0x0.svd"),
    Target("rm0454", "stm32g0", "stm32g070", "stm32g070.svd", [_hal2("g070")]),
    Target("rm0490", "stm32c0", "stm32c031", "stm32c031.svd", [_hal2("c031")]),
    # --- the rest of the validated corpus. The device for each is chosen so
    # --- the PAC module, the SVD file and (where one exists) a stm32-hal2
    # --- feature all line up; without that a baseline cannot even be built.
    # RM0041 is the F1 value line. It shares stm32f1xx-hal with RM0008 -- the
    # HAL already builds against PAC 0.16 -- and only needed its own device
    # feature naming, not a port.
    Target("rm0041", "stm32f1", "stm32f100", "stm32f100.svd", [
        Consumer("stm32f1xx-hal", "0.11.0", ["stm32f100", "medium"]),
        # the independent F1 HAL selects the same device
        Consumer("stm32f1-hal", "0.14.1", ["f100", "medium"],
                 note="second F1 HAL on PAC 0.16")]),
    # stm32f4xx-hal selects stm32f429 too, on the device already injected --
    # it was simply never listed, so the corpus's most-used driver went
    # unmeasured on the F4 flagship manual.
    Target("rm0090", "stm32f4", "stm32f429", "stm32f439.svd", [
        Consumer("stm32f4xx-hal", "0.23.0", ["stm32f429"]), _hal2("f429")]),
    Target("rm0351", "stm32l4", "stm32l4x6", "stm32l496.svd", [_hal2("l4x6")]),
    Target("rm0399", "stm32h7", "stm32h747cm7", "stm32h747cm7.svd",
           [_hal2("h747cm7"), _hrtim("stm32h747cm7")]),
    Target("rm0432", "stm32l4", "stm32l4r9", "stm32l4r9.svd"),
    # H753 rather than H753V: both are RM0433 parts and stm32-hal2 selects
    # either, but only the non-V part is offered by stm32-hrtim -- and it is
    # also the feature Hubris's drv-stm32h7-usart builds with. One device,
    # all three consumers.
    Target("rm0433", "stm32h7", "stm32h753", "stm32h753.svd", [
        _hal2("h753"), _hrtim("stm32h753")]),
    Target("rm0436", "stm32mp1", "stm32mp157", "stm32mp157.svd"),
    Target("rm0438", "stm32l5", "stm32l562", "stm32l562.svd", [_hal2("l562")]),
    Target("rm0440", "stm32g4", "stm32g4a1", "stm32g4a1.svd", [
        _hal2("g4a1"),
        Consumer("stm32g4xx-hal", "0.1.0", ["stm32g4a1"],
                 note="the one first-party family HAL released against 0.16")]),
    # CONTROL, not coverage -- excluded from the headline tables, reported
    # after them. See CONTROL_DEVICES.
    # G474 alone would reach all three G4 drivers (stm32-hal2, stm32g4xx-hal
    # and stm32-hrtim all offer it), so this is not needed for coverage. It is
    # kept as the corpus's only control on how much the choice of chip moves
    # the numbers: same manual, same drivers, different device -- 71 gates and
    # 41 registers on G4A1 against 81 and 38 here.
    Target("rm0440", "stm32g4", "stm32g474", "stm32g474.svd", [
        _hal2("g474"),
        Consumer("stm32g4xx-hal", "0.1.0", ["stm32g474"]),
        _hrtim("stm32g474")]),
    Target("rm0442", "stm32mp1", "stm32mp153", "stm32mp153.svd"),
    Target("rm0453", "stm32wl", "stm32wl5x_cm4", "stm32wl5x_cm4.svd"),
    Target("rm0455", "stm32h7", "stm32h7b3", "stm32h7b3.svd", [_hal2("h7b3")]),
    Target("rm0456", "stm32u5", "stm32u5a9", "stm32u5a9.svd"),
    Target("rm0461", "stm32wl", "stm32wle5", "stm32wle5.svd", [_hal2("wle5")]),
    Target("rm0468", "stm32h7", "stm32h735", "stm32h735.svd", [_hal2("h735")]),
    Target("rm0477", "stm32h7", "stm32h7s", "stm32h7s.svd"),
    Target("rm0481", "stm32h5", "stm32h573", "stm32h573.svd", [_hal2("h573")]),
    Target("rm0486", "stm32n6", "stm32n657", "stm32n657.svd"),
    Target("rm0492", "stm32h5", "stm32h503", "stm32h503.svd", [_hal2("h503")]),
    Target("rm0503", "stm32u0", "stm32u083", "stm32u083.svd"),
    # NOT injectable -- validated, but their PAC crate ships no module for the
    # chip: rm0475 (STM32MP13xx), rm0493 (STM32WBA5x), rm0505 (STM32WB09),
    # rm0529 (STM32WB05), rm0530 (STM32WB06/07). 978 enforce-verdict
    # constraints waiting on a PAC that covers those parts.
]


# Validated manuals with NO chip crate to inject into. stm32-rs publishes a
# crate per family and a device module per part; these five parts have neither,
# so their constraints are extracted and judged but have nowhere to land. They
# are carried in the tracking table with empty crate columns rather than
# dropped, because "no row" and "zero enforced" look the same in a summary.
# Manuals with no chip crate in the RELEASE the corpus is pinned to. Four of
# the five that used to sit here are now built from stm32-rs master instead
# (MASTER_TARGETS below); only MP13x has no patch set anywhere.
#
# WHY WE DO NOT JUST GENERATE ONE. We tried, with svd2rust 0.36.1 over the
# vendor SVD (experiments/gen_pac.py, since retired). The attempt is what
# taught us the rule now recorded in the tracking table: a stm32-rs crate is
# the vendor SVD PLUS a large layer of YAML patches, and the patches are
# load-bearing. Raw ST SVDs omit `<access>`, so svd2rust emits no
# `impl Writable` and the register comes out read-only; a write gate on a
# read-only register is not expressible and the injector correctly drops it.
# RM0475's SVD does not even parse: its TIM2 CCMR1 declares an enumerated
# value of 8 in a 3-bit field. The missing piece was never the crate -- it is
# the patched register map, which is exactly what stm32-rs would have to write
# to publish the part at all.
UNMAPPED = {
    # stm32mp1 exists but ships only stm32mp153 / stm32mp157, and master has
    # no MP13x patch set either.
    "rm0475": ("STM32MP13x", "stm32mp1", 486, 395,
               "Generating one ourselves does not work either: svd2rust over "
               "the raw vendor SVD fails to parse RM0475 at all (TIM2 CCMR1 "
               "declares an enumerated value of 8 in a 3-bit field), and more "
               "generally a stm32-rs crate is the vendor SVD plus a "
               "load-bearing YAML patch layer -- the raw file omits "
               "`<access>`, so svd2rust marks registers read-only and a write "
               "gate on them is not expressible. The missing piece is the "
               "patched register map, not the crate."),
}

# Manuals whose chip crate exists only on stm32-rs MASTER, in two crates that
# postdate v0.16.0. Measured by experiments/stm_master_pacs.py, not by this
# sweep: there is no crates.io release to provision and no driver can depend on
# an unpublished crate, so only enforceability is measurable. Their PAC version
# reads `latest` in the tables so released and unreleased rows are never
# confused for one another.
MASTER_TARGETS = {
    "rm0493": ("STM32WBA5x", "stm32wba", "stm32wba55"),
    "rm0505": ("STM32WB09", "stm32wb0", "stm32wb09"),
    "rm0529": ("STM32WB05", "stm32wb0", "stm32wb05"),
    "rm0530": ("STM32WB06/07", "stm32wb0", "stm32wb06"),
}


# --------------------------------------------------------------------------- #
# Snapshot / restore  (same contract as experiments/cross_pac.py)
# --------------------------------------------------------------------------- #

class PacSnapshot:
    def __init__(self, pac_root: Path, device: str):
        src = pac_root / "src"
        self.base = pac_root
        # The WHOLE src/ tree: generic.rs is patched crate-wide and injection
        # marks every sibling device module too, so a narrower snapshot would
        # leave the crate modified after "restore".
        self.paths = [src]
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

def out_root(field_gating: bool) -> Path:
    """Where a run's artifacts go. The two modes plan DIFFERENT gate sets, so
    they get separate trees rather than a filename suffix -- a suffix once let
    a field run overwrite the default run's numbers, and the published table
    reported one as the other."""
    return OUT if field_gating else OUT / "register_only"


def run_inject(t: Target, pac_dir: Path, report: Path, dry: bool,
               field_gating: bool = True) -> subprocess.CompletedProcess:
    argv = [
        sys.executable, str(INJECT), str(t.run_dir),
        "--pac", str(pac_dir), "--device", t.device,
        "--svd-dir", str(t.svd_path),
        "--constraints", str(t.validated),
        "--attribution-check", str(t.chunks),
        "--report", str(report),
        # NOTE: --save-constraints writes even under --dry-run, so this must
        # never point at the committed applications/pac_codegen/constraints/
        # tree; the sweep's artifacts stay in the gitignored out/ dir.
        # Mode-suffixed for the same reason the report is: the two modes plan
        # different gate sets, and an unsuffixed name let a field-gating run
        # overwrite the default run's file.
        "--save-constraints", str(out_root(field_gating) / "constraints" /
                                  f"{t.rm}_{t.device}.json"),
        *([] if field_gating else ["--register-only"]),
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


def hal_workspace(t: Target, c: Consumer, pac_dir: Path) -> Path:
    ws = Path(tempfile.mkdtemp(prefix=f"stm_sweep_hal_{t.rm}_{c.crate}_"))
    (ws / "src").mkdir()
    (ws / "src" / "lib.rs").write_text(
        "//! Compiling this crate compiles the UNMODIFIED consumer against the\n"
        "//! locally patched PAC. The build itself is the experiment.\n"
        "#![no_std]\n"
        f"pub use {c.crate.replace('-', '_')} as hal;\n")
    feats = ", ".join(f'"{f}"' for f in c.features)
    (ws / "Cargo.toml").write_text(
        "[package]\n"
        f'name = "hal-eval-{t.rm}"\nversion = "0.1.0"\nedition = "2021"\n\n'
        "[dependencies]\n"
        f'{c.crate} = {{ version = "={c.version}", features = [{feats}] }}\n\n'
        "[patch.crates-io]\n"
        f'{t.pac} = {{ path = "{pac_dir}" }}\n')
    return ws


# The marker traits injection adds to generic.rs. Their presence means the
# crate is ALREADY injected.
_INJECTED_MARKER = "UnconstrainedWrite"


def ensure_pristine(crate: str) -> Path:
    """Provision, and re-provision by force if the tree is already injected.

    get_pac.provision() trusts a stamp file that records the VERSION, not the
    tree's state, so a crate left injected by a crashed run, an interrupt, or a
    hand-run inject_from_run is returned as if it were clean. PacSnapshot would
    then take the DIRTY tree as its baseline and report "restored pristine" for
    restoring the dirt -- and injection's one-shot guard would refuse, failing
    the target for a reason that has nothing to do with what it measures. This
    is the single most common way a run in this folder fails spuriously.
    """
    pac_dir = get_pac.provision(crate=crate, version=PAC_VERSION)
    generic = pac_dir / "src" / "generic.rs"
    if generic.is_file() and _INJECTED_MARKER in generic.read_text():
        print(f"  !! {crate} was left injected; re-provisioning from crates.io")
        pac_dir = get_pac.provision(crate=crate, version=PAC_VERSION, force=True)
    return pac_dir


def patch_applied(ws: Path, pac: str) -> bool:
    """Cargo does NOT fail when a [patch] does not apply -- it warns and
    resolves the registry crate, so the whole experiment silently measures the
    unpatched PAC. A path dependency has no `source` key in Cargo.lock."""
    lock = ws / "Cargo.lock"
    if not lock.is_file():
        return False
    blocks, cur = [], None
    for line in lock.read_text().splitlines():
        if line.strip() == "[[package]]":
            cur = []
            blocks.append(cur)
        elif cur is not None:
            cur.append(line)
    for b in blocks:
        if any(l.strip() == f'name = "{pac}"' for l in b):
            return not any(l.startswith("source = ") for l in b)
    return False


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
        # (absolute path, line) for every span inside the HAL. Keeping the LINE
        # is what makes the hits triageable at all: without it an enforcement
        # count says a rule bit somewhere in a file, and there is no way to ask
        # whether the driver already establishes the precondition there.
        sites: set = set()

        def _walk(spans):
            for s in spans:
                fn = s.get("file_name", "")
                if hal_dirname in fn:
                    files.add(fn.split(f"{hal_dirname}/")[-1])
                    ln = s.get("line_start")
                    if ln:
                        sites.add((fn, int(ln)))
                exp = s.get("expansion")
                if exp and exp.get("span"):
                    _walk([exp["span"]])

        _walk(d.get("spans", []))
        for ch in d.get("children", []):
            _walk(ch.get("spans", []))
        out.append({"code": (d.get("code") or {}).get("code", ""),
                    "message": d.get("message", ""), "hal_files": sorted(files),
                    "sites": sorted(sites)})
    return out


# --------------------------------------------------------------------------- #
# Static triage of the enforcement hits
# --------------------------------------------------------------------------- #
#
# An enforcement hit means the gate FIRED at a named constrained register: the
# driver performed that operation through the stock API, without a witness. It
# does NOT mean the driver is wrong. The gate demands a witness -- a value
# proving the precondition was observed true in one fresh read -- so code that
# obeys the datasheet by some other route still fails to compile.
#
# stm32f1xx-hal is the clearest case. RM0008 says RTC_CRH cannot be written
# while a previous write is in flight (RTOFF=0), and four of its five hits are
# `crh().modify(..)` calls sitting inside:
#
#     fn perform_write(&mut self, func: impl Fn(&mut Self)) {
#         while !self.regs.crl().read().rtoff().bit() {}   // waits for RTOFF
#         ...
#         func(self);                                      // the flagged writes
#
# It waits for exactly the flag the datasheet names. Correct, and it would
# still fail to compile. Counting those as findings would overstate the result
# badly, so every hit is triaged the same way the scan arm triages its own:
# the enclosing function, one level of helper (closure host or preceding call),
# and the RAII scope-guard test.

_SPEC_REG_RE = re.compile(r"(\w+)rs$")


def _gate_fields(constraints_path: Path) -> dict:
    """register (lower) -> operation -> [precondition field names].

    Read from the constraints file the injection was driven by, so the fields
    triage looks for are exactly the ones the gate was built from.
    """
    if not constraints_path.is_file():
        return {}
    try:
        data = json.loads(constraints_path.read_text())
    except Exception:                                     # noqa: BLE001
        return {}
    entries = data.get("registers", data) if isinstance(data, dict) else data
    if isinstance(entries, dict):
        entries = list(entries.values())
    out = {}
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        reg = (e.get("register") or "").lower()
        if not reg:
            continue
        per_op = {}
        for op, pres in (e.get("preconditions") or {}).items():
            fields = []
            for text in pres or []:
                # "CAN_FMR.FINIT set" -> finit
                m = re.search(r"\.(\w+)", str(text))
                if m:
                    fields.append(m.group(1).lower())
            if fields:
                per_op[op] = sorted(set(fields))
        # Field gates too. Reading only `preconditions` left every field-only
        # register with nothing for the triage to look for, so its hits came
        # back untriaged instead of guarded/candidate -- and under field
        # gating those are 600+ registers, the majority of what is new.
        # A field gate rides the writer accessor, which serves write and
        # modify alike, so its preconditions belong under both.
        for fg in (e.get("gated_fields") or {}).values():
            fields = []
            for text in fg.get("preconditions") or []:
                m = re.search(r"\.(\w+)", str(text))
                fields.append(m.group(1).lower() if m
                              else str(text).split()[0].lower())
            for op in ("write", "modify"):
                if fields:
                    per_op[op] = sorted(set(per_op.get(op, [])) | set(fields))
        if per_op:
            out[reg] = per_op
    return out


def triage_hit(abs_path: str, line: int, fields: list) -> dict:
    """corroborated / unchecked for one enforcement hit, statically."""
    try:
        from scan_projects import guard_prologue, scope_guard
        from corroboration import enclosing_function, deterministic_scan
    except Exception as exc:                              # noqa: BLE001
        return {"verdict": "scan_error", "error": str(exc)[:120]}
    if not fields:
        return {"verdict": "no_precondition_fields", "fields": []}
    try:
        start, snippet = enclosing_function(abs_path, line)
        rel = line - start + 1
        pro = guard_prologue(abs_path, snippet, rel, line)
        if pro["text"]:
            snippet = pro["text"] + "\n" + snippet
            rel += len(pro["text"].splitlines())
        v = deterministic_scan(snippet, rel, fields, "pac")
        v["helpers_inlined"] = pro["inlined"]
        if v["verdict"] == "unchecked":
            g = scope_guard(abs_path, fields)
            if g:
                v["verdict"] = "corroborated"
                v["scope_guard"] = g
        return v
    except Exception as exc:                              # noqa: BLE001
        return {"verdict": "scan_error", "error": str(exc)[:120]}


def classify(errors, gated_specs: set[str], gate_fields=None) -> dict:
    """Split HAL errors into: TRUE ENFORCEMENT (our diagnostic naming a register
    we actually gated), GENERIC FRICTION (our diagnostic in generic code that
    never names a gated register), OTHER (anything else -- collateral damage)."""
    gate_fields = gate_fields or {}
    res = {"true_enforcement": 0, "generic_friction": 0, "other": 0,
           "guarded": 0, "candidate": 0, "untriaged": 0, "triage": [],
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
            # --- static triage: does the driver already establish it here?
            reg = ""
            m = _SPEC_REG_RE.search(named[0].split("::")[-1])
            if m:
                reg = m.group(1).lower()
            op = ("write" if "write-constrained" in e["message"] else
                  "modify" if "modify-constrained" in e["message"] else "read")
            fields = (gate_fields.get(reg, {}).get(op)
                      or sorted({f for v in gate_fields.get(reg, {}).values()
                                 for f in v}))
            site = e["sites"][0] if e.get("sites") else None
            if site and fields:
                v = triage_hit(site[0], site[1], fields)
                if v["verdict"] == "corroborated":
                    res["guarded"] += 1
                elif v["verdict"] == "unchecked":
                    res["candidate"] += 1
                else:
                    res["untriaged"] += 1
                if len(res["triage"]) < 40:
                    res["triage"].append({
                        "file": e["hal_files"][0] if e["hal_files"] else "",
                        "line": site[1], "register": reg, "operation": op,
                        "fields": fields, "verdict": v["verdict"],
                        "helpers": v.get("helpers_inlined") or [],
                        "scope_guard": v.get("scope_guard", "")})
            else:
                res["untriaged"] += 1
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

def run_target(t: Target, dry: bool, skip_hal: bool, hal_baseline_cache: dict,
               field_gating: bool = True, keep_pac: Path = None) -> dict:
    res = {"rm": t.rm, "pac": t.pac, "device": t.device,
           "consumers": [c.crate for c in t.consumers],
           "inject": "?", "planned": 0, "fates": {}, "gated_specs": [],
           "probe": "-", "hal_results": [], "pristine": None, "detail": []}
    print(f"\n=== {t.rm} -> {t.pac} 0.16.0 / {t.device} ===")
    if not t.run_dir.is_dir():
        res["inject"] = "NO DATA"
        print(f"  no run dir: {t.run_dir}")
        return res

    pac_dir = ensure_pristine(t.pac)
    OUT.mkdir(parents=True, exist_ok=True)
    # The two gating modes plan DIFFERENT gate sets, so their reports must not
    # share a filename -- a field-gating run silently overwrote the default
    # run's numbers, and the tracking table then published one as the other.
    root = out_root(field_gating)
    root.mkdir(parents=True, exist_ok=True)
    report = root / f"{t.rm}_{t.device}{'_dry' if dry else ''}.json"

    snap = None if dry else PacSnapshot(pac_dir, t.device)
    try:
        run = run_inject(t, pac_dir, report, dry, field_gating)
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

        for c in (t.consumers if not skip_hal else []):
            ws = hal_workspace(t, c, pac_dir)
            base = hal_baseline_cache.get((t.rm, c.crate))
            entry = {"crate": c.crate, "version": c.version,
                     "features": c.features, "baseline": base,
                     "workspace": str(ws)}
            errors = hal_errors(ws, f"{c.crate}-{c.version}")
            if not patch_applied(ws, t.pac):
                entry["status"] = "PATCH_UNUSED"
                print(f"  !! {c.crate}: patch not applied — result discarded")
            elif errors is None:
                entry["status"] = "TIMEOUT"
            else:
                entry.update(classify(
                    errors, set(res["gated_specs"]),
                    _gate_fields(out_root(field_gating) / "constraints" /
                                 f"{t.rm}_{t.device}.json")))
                entry["status"] = "ran"
                print(f"  HAL {c.crate} {c.version} (baseline {base}): "
                      f"true_enforcement={entry['true_enforcement']} "
                      f"(guarded={entry['guarded']} "
                      f"candidate={entry['candidate']} "
                      f"untriaged={entry['untriaged']}) "
                      f"generic_friction={entry['generic_friction']} "
                      f"other={entry['other']}")
                print(f"    enforcement sites: {entry['files']['true_enforcement']}")
                if entry["other"]:
                    for d in entry["other_detail"]:
                        print(f"    other: {d}")
            res["hal_results"].append(entry)
        return res
    finally:
        # Keep a copy of the INJECTED crate before restoring it. The sweep
        # exists to measure, so it always puts the crate back -- which leaves
        # nothing to read afterwards. This is the flag for "I want to look at
        # what was generated", and it copies before the restore because after
        # it there is nothing to copy.
        if keep_pac is not None and not dry and res["inject"] == "ok":
            dest = Path(keep_pac) / f"{t.rm}_{t.device}_{t.pac}"
            if dest.exists():
                shutil.rmtree(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(pac_dir, dest)
            res["kept_pac"] = str(dest)
            print(f"  injected crate kept: {dest}")
        if snap is not None:
            res["pristine"] = snap.restore_and_verify()
            print(f"  restored pristine: {res['pristine']}")
            if not res["pristine"]:
                print(f"  !! {t.pac} left non-pristine; re-provision with "
                      f"get_pac.py --crate {t.pac} --version {PAC_VERSION} --force",
                      file=sys.stderr)


def hal_baseline(t: Target, c: Consumer) -> str:
    """The consumer must compile against the PRISTINE PAC, else the injected
    result means nothing. A patch that did not apply is also a non-result."""
    pac_dir = ensure_pristine(t.pac)
    ws = hal_workspace(t, c, pac_dir)
    run = cargo_check(ws)
    ok_patch = patch_applied(ws, t.pac)
    shutil.rmtree(ws, ignore_errors=True)
    if run is None:
        return "TIMEOUT"
    if not ok_patch:
        return "PATCH_UNUSED"
    return "PASS" if run.returncode == 0 else "FAIL"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=[],
                    help="run a single RM (repeatable)")
    ap.add_argument("--dry-run", action="store_true",
                    help="selection + planning only; never touch a PAC")
    ap.add_argument("--skip-hal", action="store_true")
    ap.add_argument("--register-only", action="store_true",
                    help="BASELINE MODE: whole-register gating only. Writes to "
                         "out/register_only/ so the two modes never share a "
                         "path; the default (field) run keeps out/.")
    ap.add_argument("--field-level-gating", action="store_true",
                    help=argparse.SUPPRESS)   # now the default; a no-op
    ap.add_argument("--keep-pac", nargs="?", const="", default=None,
                    metavar="DIR",
                    help="copy each INJECTED crate here before it is restored, "
                         "as <rm>_<device>_<crate>/. Without a DIR a temporary "
                         "one is made and its path printed. The sweep always "
                         "restores the PAC, so without this there is nothing "
                         "left to inspect. Ignored under --dry-run.")
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
            for c in t.consumers:
                print(f"baseline: {c.crate} {c.version} vs pristine {t.pac} ...",
                      flush=True)
                baselines[(t.rm, c.crate)] = hal_baseline(t, c)
                print(f"  {baselines[(t.rm, c.crate)]}")

    keep = None
    if args.keep_pac is not None and not args.dry_run:
        keep = Path(args.keep_pac) if args.keep_pac else Path(
            tempfile.mkdtemp(prefix="stm_sweep_kept_"))
        print(f"keeping injected crates under: {keep}\n")
    elif args.keep_pac is not None:
        print("--keep-pac ignored: --dry-run never touches a PAC\n")

    results = [run_target(t, args.dry_run, args.skip_hal, baselines,
                          (not args.register_only), keep) for t in targets]

    print("\n\n## Summary\n")
    print("| RM | PAC | device | injection | registers gated | probe | consumer | "
          "baseline | true enforcement | generic friction | other | pristine |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        head = (f"| {r['rm']} | {r['pac']} | {r['device']} | {r['inject']} | "
                f"{r['planned']} | {r['probe']} ")
        if not r["hal_results"]:
            print(head + f"| — | — | — | — | — | {r['pristine']} |")
        for h in r["hal_results"]:
            print(head + f"| {h['crate']} {h['version']} | {h.get('baseline','—')} | "
                  f"{h.get('true_enforcement', '—')} | "
                  f"{h.get('generic_friction', '—')} | "
                  f"{h.get('other', '—')} | {r['pristine']} |")

    OUT.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else out_root(
        not args.register_only) / (
        "sweep_dry.json" if args.dry_run else "sweep.json")
    out.write_text(json.dumps(results, indent=1, default=str) + "\n")
    print(f"\nsummary: {out}")

    bad = [r for r in results if r["pristine"] is False]
    if bad:
        sys.exit("ERROR: a PAC tree was left non-pristine (see above)")


if __name__ == "__main__":
    main()
