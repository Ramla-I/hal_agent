#!/usr/bin/env python3
"""Find constrained register accesses in third-party projects, WITHOUT compiling.

Every finding so far lives in one driver crate (stm32f4xx-hal), because that is
the only thing we could build against an injected PAC. Every other candidate
target pins an older HAL or PAC, so "build first, look second" does not scale --
and Tock has no PAC at all, so it can never be built against one.

This scans instead. It reads a project's own Rust source, extracts every
hardware register access, maps it to (peripheral, register, field, operation),
cross-references our extracted datasheet constraints, and triages each hit. It
also records, per project, whether it could EVER be built against an injected
crate and what that would take -- which is the ranked shortlist the build phase
consumes.

ONLY THE FRONT-END IS NEW. experiments/corroboration.py already implements
everything downstream of "here is a flagged site": `enclosing_function` finds
the containing function, `deterministic_scan` answers "is a precondition field
accessor called before the flagged line?" (corroborated vs unchecked), and
`judge_hit` runs the calibrated closed-book judge. Its input today is
`enforcement_hits()`, which parses `cargo check` diagnostics; this module is a
second producer of the same {file, line, register, operation} shape, from text.

WHAT A HIT MEANS. `unchecked` is a CANDIDATE, not a bug: a static scan cannot
see a guard in a caller, and `deterministic_scan` only looks inside the
enclosing function. `corroborated` means the project already performs the
datasheet-prescribed check nearby. Compile confirmation remains the arbiter.

Usage:
    python applications/pac_codegen/experiments/scan_projects.py
    python applications/pac_codegen/experiments/scan_projects.py --only hubris
    python applications/pac_codegen/experiments/scan_projects.py --local <name>=<path>
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent      # applications/pac_codegen
REPO = APP_DIR.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "experiments"))

import rust_codegen  # noqa: E402
from core import collect_constraints as cc  # noqa: E402
from corroboration import enclosing_function, deterministic_scan  # noqa: E402

OUT = APP_DIR / "experiments" / "out"
DATA = Path("/home/ramla/hal_agent-phase-1d")
PAC_VERSION = "0.16.0"
CLONE_TIMEOUT = 900


# --------------------------------------------------------------------------- #
# The project registry
# --------------------------------------------------------------------------- #

@dataclass
class Project:
    """A third-party project to scan.

    ``style`` decides which extractor runs:
      pac_direct -- svd2rust accessors in the project's own source
                    (`i2c.cr1.modify(|_, w| ...)`, `dp.TIM5.psc.write(...)`)
      tock       -- tock-registers: hand-written `register_structs!` /
                    `register_bitfields!`, accessed as `self.registers.cr1...`
      hal_only   -- all register access is inside a HAL; nothing to scan in the
                    project itself. Recorded so the report says WHY it is empty.
    """
    name: str
    repo: str
    style: str
    rms: list                       # manuals in our corpus this maps to
    device: str                     # PAC device module, for name resolution
    pac: str                        # PAC crate it would need
    pac_pinned: str = ""            # what it pins today ("" = via a HAL)
    hal: str = ""
    hal_pinned: str = ""
    subdirs: list = field(default_factory=list)   # limit the scan (large repos)
    ref: str = ""
    note: str = ""
    # Path prefix -> the manuals that govern code under it. A repo can target
    # several chip families at once: Hubris has drv/stm32h7-* beside
    # drv/stm32fx-*, and matching H7 driver code against an F4 manual is
    # unsound even when the register name happens to exist on both. A prefix
    # mapping to [] means "we have no constraints for that family" and its
    # files are skipped rather than mis-attributed.
    chip_paths: dict = field(default_factory=dict)
    # Peripheral name the project uses -> the name our constraints use. A
    # project vendoring its own register module names it whatever it likes:
    # `fdcan` ships `src/pac/fdcan.rs` reached through a field called `can`,
    # so every access reads as `can/<reg>` while every constraint says
    # `fdcan/<reg>` and nothing ever joins -- 380 rules available, 0 hits.
    periph_alias: dict = field(default_factory=dict)
    # How this project spells a field access, for guard detection. "pac" is
    # svd2rust (`r.acc64()`), "tock" is tock-registers (`ACR::ACC64`),
    # "metapac" is embassy (`w.set_acc64(true)` for writes).
    dialect: str = ""

    def rms_for(self, rel: str) -> list:
        """Manuals governing one file, by longest matching path prefix."""
        best, best_len = None, -1
        for pref, rms in self.chip_paths.items():
            if rel.startswith(pref) and len(pref) > best_len:
                best, best_len = rms, len(pref)
        return self.rms if best is None else best


def _ground_truth_n() -> str:
    """How many enforcement sites the COMPILE route finds on stm32f4xx-hal,
    read from the sweep rather than remembered.

    This used to come from patch_hal.py, now retired: its list recorded every
    site it managed to rewrite and carried no triage, so it counted sites the
    driver already guarded and missed the real candidates entirely.
    """
    p = OUT / "sweep.json"
    if not p.is_file():
        return "an unrecorded number of"
    try:
        data = json.loads(p.read_text())
    except Exception:                                      # noqa: BLE001
        return "an unrecorded number of"
    for t in data:
        if t.get("rm") != "rm0368":
            continue
        for h in t.get("hal_results") or []:
            if h.get("crate") == "stm32f4xx-hal" and h.get("status") == "ran":
                return str(h.get("true_enforcement"))
    return "an unrecorded number of"


PROJECTS = [
    # --- track 2: PACs used directly, no HAL. Errors land on their own lines.
    # Chip attribution here is derived from each driver crate's OWN Cargo
    # features, not from the family in its name. Getting this wrong is not
    # conservative: `drv/stm32xx-i2c` builds ONLY for H7 and G0, and an earlier
    # run matched it against RM0386, an F4 manual whose I2C is a different
    # peripheral generation (START/STOP/PEC live in CR1 there, in CR2 here).
    # Every one of its 14 "hits" was an artefact of that mismatch.
    Project("hubris", "https://github.com/oxidecomputer/hubris", "pac_direct",
            ["rm0316", "rm0090", "rm0433", "rm0444", "rm0454"],
            "stm32h753", "stm32h7", pac_pinned="0.14",
            subdirs=["drv"],
            chip_paths={
                "drv/lpc55": [],            # NXP, not STM
                # features stm32h743/stm32h753 -> RM0433
                "drv/stm32h7": ["rm0433"],
                # features stm32g031/g070/g0b1 -> RM0444 (G0x1) + RM0454 (G0x0)
                "drv/stm32g0": ["rm0444", "rm0454"],
                # features stm32f303 + stm32f407 -> RM0316 + RM0090
                "drv/stm32fx": ["rm0316", "rm0090"],
                # features stm32g030/g031/g070/g0b1 + stm32h743/h753
                "drv/stm32xx": ["rm0433", "rm0444", "rm0454"],
            },
            note="Oxide service processor. 23 STM32 driver crates; also uses "
                 "stm32f3/stm32g0/stm32h7 directly."),
    Project("anne-key", "https://github.com/ah-/anne-key", "pac_direct",
            ["rm0038"], "stm32l151", "stm32l1", pac_pinned="0.11.0",
            note="Keyboard firmware on stm32l1 with no HAL layer."),

    # --- track 3: Tock. Hand-written register maps; can never be injected.
    Project("tock", "https://github.com/tock/tock", "tock",
            ["rm0368", "rm0402", "rm0390", "rm0316"],
            "stm32f401", "stm32f4",
            subdirs=["chips/stm32f4xx", "chips/stm32f303xc"],
            chip_paths={
                # F4 chip crate: F401 / F412 / F446. NOT RM0316 -- F3's USART
                # and I2C are a different peripheral generation.
                "chips/stm32f4xx": ["rm0368", "rm0402", "rm0390"],
                "chips/stm32f303xc": ["rm0316"],
            },
            note="tock-registers, not svd2rust. Scan-only by construction."),

    # --- track 1: stm32f4xx-hal reverse dependencies that touch registers.
    Project("stm32-eth", "https://github.com/stm32-rs/stm32-eth", "pac_direct",
            ["rm0090", "rm0386", "rm0390"], "stm32f469", "stm32f4",
            hal="stm32f4xx-hal", hal_pinned="^0.21",
            note="Ethernet MAC/DMA driver; programs ETH registers directly."),
    Project("stm32f469i-disc", "https://github.com/tegimeki/stm32f469i-disc",
            "hal_only", ["rm0386"], "stm32f469", "stm32f4",
            hal="stm32f4xx-hal", hal_pinned="^0.23",
            note="ALREADY on the HAL version that pairs with PAC 0.16."),
    Project("booster", "https://github.com/quartiq/booster", "hal_only",
            ["rm0090"], "stm32f407", "stm32f4",
            hal="stm32f4xx-hal", hal_pinned="^0.21",
            note="RF power amplifier firmware. F407 = RM0090, now in the "
                 "corpus."),
    Project("px4flow_bsp", "https://github.com/tstellanova/px4flow_bsp",
            "hal_only", ["rm0090"], "stm32f407", "stm32f4",
            hal="stm32f4xx-hal", hal_pinned="^0.8.3",
            note="Optical-flow sensor BSP; F407 = RM0090."),

    # --- peripheral drivers that exist BECAUSE the HAL does not cover their
    # peripheral, so they drive registers themselves. Highest density of the
    # set, and on exactly the peripherals where constraints cluster.
    Project("stm32f7-discovery", "https://github.com/embed-rs/stm32f7-discovery",
            "pac_direct", ["rm0385"], "stm32f7x6", "stm32f7",
            pac_pinned="0.7", subdirs=["src"],
            note="Board framework with its own SD, Ethernet and LCD drivers; "
                 "261 register accesses, the densest project scanned."),
    Project("fdcan", "https://github.com/stm32-rs/fdcan", "pac_direct",
            ["rm0440", "rm0433"], "stm32g4a1", "stm32g4",
            subdirs=["src"], periph_alias={"can": "fdcan"},
            note="FDCAN driver carrying its OWN vendored svd2rust register "
                 "module (src/pac). RM0440's CCE rule is the one whose "
                 "multi-line quote broke our emitter."),
    Project("bxcan", "https://github.com/stm32-rs/bxcan", "pac_direct",
            ["rm0008"], "stm32f103", "stm32f1", subdirs=["src"],
            note="bxCAN driver. The filter-init FINIT rule is the constraint "
                 "behind the BitReader shape bug."),
    Project("stm32-usbd", "https://github.com/stm32-rs/stm32-usbd",
            "pac_direct", ["rm0008"], "stm32f103", "stm32f1",
            subdirs=["src"],
            note="usb-device implementation; drives the USB peripheral "
                 "directly on F0/F1/F3/L0/L4/WB."),
    Project("stm32f103xx-usb", "https://github.com/mvirkkunen/stm32f103xx-usb",
            "pac_direct", ["rm0008"], "stm32f103", "stm32f1",
            subdirs=["src"], note="USB device stack for F103."),
    Project("stm32-fmc", "https://github.com/stm32-rs/stm32-fmc", "pac_direct",
            ["rm0433"], "stm32h753v", "stm32h7", subdirs=["src"],
            note="FMC/FSMC memory-controller driver (SDRAM init)."),

    # --- bootloaders: they do nothing but program flash, and flash is where
    # four of the thirty-one stm32f4xx-hal violations landed.
    Project("blethrs", "https://github.com/AirborneEngineering/blethrs",
            "pac_direct", ["rm0090"], "stm32f429", "stm32f4",
            pac_pinned="0.11", subdirs=["src"],
            note="Ethernet bootloader on F407, stm32f4 PAC with no HAL. "
                 "85 register accesses in 7 files."),
    Project("loadstone", "https://github.com/absw/loadstone", "pac_direct",
            ["rm0402"], "stm32f412", "stm32f4", subdirs=["src"],
            chip_paths={
                # wgm160p is a Silicon Labs part, not ST -- skip, do not
                # match it against an STM32 manual.
                "src/ports/wgm160p": [],
                "src/ports/stm32f412": ["rm0402"],
                "src/devices": ["rm0402"],
            },
            note="Secure bootloader; F412 port plus a non-ST port."),

    # --- application firmware and RTOSes
    Project("lilos", "https://github.com/cbiffle/lilos", "pac_direct",
            ["rm0090", "rm0433", "rm0444"], "stm32f429", "stm32f4",
            chip_paths={
                "examples/stm32f4": ["rm0090"],
                "examples/stm32h7": ["rm0433"],
                "examples/stm32g0": ["rm0444"],
                # os/ and testsuite/ are chip-agnostic cortex-m code.
                "os": [], "testsuite": [], "extra": [],
            },
            note="Cliff Biffle's async RTOS; examples drive three families."),
    Project("keyboard-labs", "https://github.com/rgoulter/keyboard-labs",
            "pac_direct", ["rm0368"], "stm32f401", "stm32f4",
            subdirs=["firmware"],
            note="Keyboard firmware on F401."),

    # --- board support packages: mostly re-export, scanned to confirm that
    Project("stm32f3-discovery",
            "https://github.com/rubberduck203/stm32f3-discovery", "pac_direct",
            ["rm0316"], "stm32f303", "stm32f3", subdirs=["src"],
            note="F3DISCOVERY board support."),
    Project("stm32f407g-disc", "https://github.com/stm32-rs/stm32f407g-disc",
            "hal_only", ["rm0090"], "stm32f407", "stm32f4",
            hal="stm32f4xx-hal", hal_pinned="^0.14",
            note="F4DISCOVERY board support; re-exports the HAL."),

    # --- the largest register surface in the ecosystem, and the reason it is
    # scannable at all: embassy encodes the peripheral GENERATION and the chip
    # family in its file layout. `i2c/v1.rs` vs `i2c/v2.rs` is exactly the
    # old-vs-new I2C split that manufactured 14 false findings in Hubris when
    # it was inferred from a crate name instead. Here the project states it.
    #
    # Attribution is therefore an ALLOW-LIST: the "" prefix maps to [], so any
    # path not named below is skipped rather than matched against whatever the
    # project's default manuals happen to be.
    Project("embassy", "https://github.com/embassy-rs/embassy", "pac_direct",
            ["rm0008", "rm0033", "rm0038", "rm0090", "rm0091", "rm0316",
             "rm0367", "rm0385", "rm0394", "rm0433", "rm0438", "rm0440",
             "rm0444", "rm0456", "rm0481", "rm0486", "rm0490"],
            "stm32f429", "stm32f4", subdirs=["embassy-stm32/src"],
            chip_paths={
                "": [],                       # allow-list: skip by default
                # I2C: v1 is the old peripheral (START/STOP/PEC in CR1),
                # v2 the new one (they live in CR2). Different rules entirely.
                "embassy-stm32/src/i2c/v1.rs": ["rm0008", "rm0033", "rm0090", "rm0038"],
                "embassy-stm32/src/i2c/v2.rs": ["rm0091", "rm0316", "rm0385", "rm0444",
                                 "rm0440", "rm0433", "rm0367", "rm0394",
                                 "rm0438", "rm0456"],
                # RCC, split by family in the filename.
                "embassy-stm32/src/rcc/f013.rs": ["rm0091", "rm0008", "rm0316"],
                "embassy-stm32/src/rcc/f247.rs": ["rm0033", "rm0090", "rm0385"],
                "embassy-stm32/src/rcc/g0.rs": ["rm0444"],
                "embassy-stm32/src/rcc/g4.rs": ["rm0440"],
                "embassy-stm32/src/rcc/h.rs": ["rm0433", "rm0481"],
                "embassy-stm32/src/rcc/l.rs": ["rm0367", "rm0038", "rm0394", "rm0438"],
                "embassy-stm32/src/rcc/u5.rs": ["rm0456"],
                "embassy-stm32/src/rcc/c0.rs": ["rm0490"],
                "embassy-stm32/src/rcc/n6.rs": ["rm0486"],
                # CAN, split by controller generation.
                "embassy-stm32/src/can/bxcan": ["rm0008", "rm0090", "rm0385"],
                "embassy-stm32/src/can/fd": ["rm0440", "rm0433"],
                "embassy-stm32/src/can/fdcan.rs": ["rm0440", "rm0433"],
                # ADC: only the family-named files. v1..v4 and adc4 are
                # generation-numbered with no documented family mapping, and
                # guessing it is how the earlier attribution bugs happened.
                "embassy-stm32/src/adc/f1.rs": ["rm0008"],
                "embassy-stm32/src/adc/f3.rs": ["rm0316"],
                "embassy-stm32/src/adc/g4.rs": ["rm0440"],
                "embassy-stm32/src/adc/l1.rs": ["rm0038"],
                "embassy-stm32/src/adc/c0.rs": ["rm0490"],
                # Ethernet.
                "embassy-stm32/src/eth/v1": ["rm0090", "rm0385"],
                "embassy-stm32/src/eth/v2": ["rm0433"],
            },
            dialect="metapac",
            note="Async embedded framework; embassy-stm32 alone carries 4,049 "
                 "register accesses, more than Tock and Hubris combined. Uses "
                 "stm32-metapac, so field writes are `w.set_ff(true)` rather "
                 "than `w.ff().set_bit()`. Only the paths whose family is "
                 "named in the layout are scanned."),
]

# Looked at and deliberately NOT scanned. Recorded because a project absent
# from the report is indistinguishable from one that scanned clean.
EXCLUDED = {
    "turbo-resin": (
        "https://github.com/nviennot/turbo-resin",
        "Resin 3D-printer firmware, 86 register accesses -- but through "
        "embassy-stm32 (stm32-metapac), a different generator with different "
        "register naming, and its default target is a GigaDevice GD32F307 "
        "clone rather than an ST part. Scanning it with the svd2rust "
        "extractor would attribute accesses we cannot check."),
    "drone-stm32-map": (
        "https://github.com/drone-os/drone-stm32-map",
        "Drone OS's STM32 register maps. 118 Rust files and ZERO register "
        "accesses: it generates maps through macros and ships no driver code, "
        "so there is nothing for a register scanner to read."),
    "ariel-os": (
        "https://github.com/ariel-os/ariel-os",
        "Embedded OS, 362 Rust files, 7 register accesses. It delegates "
        "hardware access to Embassy, which is scanned directly instead."),
    "rtic": (
        "https://github.com/rtic-rs/rtic",
        "Real-time concurrency framework. 267 files, 133 accesses -- but it "
        "is a scheduler, not a driver layer: the accesses are timer-monotonic "
        "code and some of it targets Silicon Labs parts, not ST."),
    "stm32-emulator": (
        "https://github.com/nviennot/stm32-emulator",
        "Emulates an STM32 rather than running on one: 28 files, 9 accesses. "
        "It MODELS register behaviour, which makes it a possible cross-check "
        "on our extracted rules -- a different experiment, not a scan target."),
    "trezor-firmware": (
        "https://github.com/trezor/trezor-firmware",
        "Hardware wallet. 491 Rust files but only 4 register accesses: the "
        "Rust portion is the UI layer and the drivers are C. Nothing for a "
        "register scanner to find."),
}


# --------------------------------------------------------------------------- #
# Constraints for a manual, keyed for lookup
# --------------------------------------------------------------------------- #

def load_constraints(rm: str) -> list:
    """Judge-`enforce` constraints for one manual, field-exact.

    The review JSONL is the only artifact carrying `target_fields` and
    structured preconditions; the per-device constraints file is
    whole-register only (field gating is off by default)."""
    p = DATA / f"evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl"
    if not p.is_file():
        p = DATA / f"agent_output/stm/{rm}/1/constraint_validation/validated.jsonl"
    if not p.is_file():
        return []
    out = []
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        enf, tp = r.get("enforcement", ""), r.get("tp_fp", "")
        if tp == "FP":
            continue
        if enf != "enforce" and not (tp == "TP" and enf == "drop"):
            continue
        c = r.get("constraint") or {}
        if not c:
            continue
        out.append({
            "rm": rm, "peripheral": (r.get("peripheral") or "").lower(),
            "register": (r.get("register") or "").lower(),
            "kind": c.get("kind"),
            "operation": c.get("target_operation", ""),
            "fields": [f.lower() for f in (c.get("target_fields") or [])],
            "preconditions": [
                {"register": q.get("register", ""), "field": q.get("field", ""),
                 "state": q.get("state", "")}
                for q in (c.get("preconditions") or [])],
            "quote": c.get("datasheet_text", ""),
        })
    return out


def constraint_index(rms: list) -> dict:
    """(peripheral_family, register) -> [constraint]. Family-keyed so a hit on
    any instance matches (instances share one register-block module, so a gate
    on i2c1 covers I2C2/I2C3 -- see rust_codegen.peripheral_instance_map)."""
    idx = defaultdict(list)
    for rm in rms:
        for c in load_constraints(rm):
            fam = cc._family(c["peripheral"]) or c["peripheral"]
            idx[(fam, c["register"])].append(c)
    return idx


# --------------------------------------------------------------------------- #
# Extractors: project source -> register access sites
# --------------------------------------------------------------------------- #

# svd2rust accessor styles, both the method form used by newer PACs
# (`i2c.cr1().modify(..)`) and the field form used by 0.13-0.15
# (`i2c.cr1.modify(..)`). The receiver is captured for peripheral attribution.
_PAC_ACCESS = re.compile(
    r"(?P<recv>[A-Za-z_][A-Za-z0-9_.]*)\s*\.\s*(?P<reg>[a-z][a-z0-9_]*)\s*"
    r"(?:\(\s*\))?\s*\.\s*(?P<op>read|write|modify|reset)\s*\(")

# tock-registers: `self.registers.cr1.modify(CR1::PE::SET)`, `.read(SR1::SB)`
_TOCK_ACCESS = re.compile(
    r"(?P<recv>[A-Za-z_][A-Za-z0-9_.]*)\s*\.\s*(?P<reg>[a-z][a-z0-9_]*)\s*"
    r"\.\s*(?P<op>read|write|modify|set|get|is_set|modify_no_read)\s*\(")

# Field accessors inside a closure body: `w.pe().set_bit()`, `w.trise().set(x)`
_FIELD_CALL = re.compile(r"\bw\s*\.\s*([a-z][a-z0-9_]*)\s*\(")
# tock field references: `CR1::PE::SET`, `SR1::SB`
_TOCK_FIELD = re.compile(r"\b[A-Z][A-Z0-9_]*::([A-Z][A-Z0-9_]*)")

_SKIP_DIRS = {"target", ".git", "tests", "examples", "benches"}
# Method names that look like registers but are not (common Rust/embedded API).
_NOT_A_REGISTER = {
    "lock", "borrow", "clone", "iter", "len", "get", "set", "as_ref", "unwrap",
    "map", "value", "data", "buf", "inner", "state", "config", "peripherals",
    "regs", "registers", "device", "port", "pin", "clocks", "byte", "word",
}


def _rust_files(root: Path, subdirs: list) -> list:
    """Rust sources to scan, from the declared subdirectories.

    A declared subdirectory that is not in the checkout is a HARD error. A
    scan that silently finds nothing reports zero hits, and zero hits reads
    exactly like a clean project -- an earlier run recorded Tock as "0 .rs
    files, 0 register accesses" and it went unquestioned. Fail loudly instead.
    """
    roots = [root / s for s in subdirs] if subdirs else [root]
    missing = [str(r) for r in roots if not r.is_dir()]
    if missing:
        raise FileNotFoundError(
            "declared subdirs absent from the checkout (bad ref, failed "
            f"clone, or the project moved them): {missing}")
    out = []
    for r in roots:
        for f in r.rglob("*.rs"):
            if any(p in _SKIP_DIRS for p in f.parts):
                continue
            out.append(f)
    return out


# Receiver names that carry no peripheral information -- the peripheral is the
# module's, not the expression's. `regs.tr().write(..)` inside src/rtc.rs is an
# RTC access; attributing it to a peripheral called "regs" loses 14 of the 31
# known sites in stm32f4xx-hal.
_GENERIC_RECEIVERS = {"registers", "regs", "self", "rb", "reg", "periph",
                      "peripheral", "block", "inner", "p"}


def _peripheral_from_receiver(recv: str, file_stem: str) -> str:
    """Best-effort peripheral name from the receiver expression, falling back
    to the file it lives in.

    `i2c.cr1` -> i2c;  `dp.TIM5.psc` -> tim5;  `self.regs.tr()` in rtc.rs ->
    rtc. Heuristic by nature, so the receiver text is carried into the report
    for review."""
    last = recv.split(".")[-1].lower()
    if last in _GENERIC_RECEIVERS or not last:
        return file_stem.lower()
    return last


def scan_pac_direct(f: Path, root: Path) -> list:
    """svd2rust-style register accesses in one file."""
    text = f.read_text(errors="replace")
    lines = text.splitlines()
    stem = f.stem
    hits = []
    for m in _PAC_ACCESS.finditer(text):
        reg = m.group("reg")
        if reg in _NOT_A_REGISTER:
            continue
        # Attribute to the OPERATION token, not the receiver: rustc reports
        # `self.spi\n  .cr1()\n  .modify(..)` at the `.modify` line, and the
        # ground-truth comparison against compiled diagnostics needs to agree.
        line_no = text.count("\n", 0, m.start("op")) + 1
        # fields written: scan the rest of the statement for `w.<field>()`
        tail = text[m.end():m.end() + 400]
        raw = [x.lower() for x in _FIELD_CALL.findall(tail)]
        # svd2rust writes a field as `w.ff().set_bit()`; embassy's metapac
        # writes it as `w.set_ff(true)`. Emitting BOTH spellings costs nothing
        # on svd2rust (no field is named `set_*` there) and is what lets a
        # field-scoped rule bite on metapac code at all.
        fields = raw + [x[4:] for x in raw if x.startswith("set_") and len(x) > 4]
        hits.append({
            "file": str(f.relative_to(root)), "abs": str(f), "line": line_no,
            "receiver": m.group("recv"),
            "peripheral": _peripheral_from_receiver(m.group("recv"), stem),
            "register": reg, "operation": m.group("op"),
            "fields": sorted(set(fields)),
            "source": (lines[line_no - 1].strip()[:160] if line_no <= len(lines) else ""),
        })
    return hits


def _tock_register_map(f: Path) -> set:
    """Register names declared in this file's `register_structs!` block."""
    text = f.read_text(errors="replace")
    return {m.group(1).lower() for m in
            re.finditer(r"^\s*(?:\(\s*0x[0-9A-Fa-f]+\s*=>\s*)?([a-z][a-z0-9_]*)\s*:\s*"
                        r"(?:ReadWrite|ReadOnly|WriteOnly)<", text, re.M)}


def scan_tock(f: Path, root: Path) -> list:
    """tock-registers accesses; the peripheral is the file stem."""
    declared = _tock_register_map(f)
    if not declared:
        return []
    text = f.read_text(errors="replace")
    lines = text.splitlines()
    periph = f.stem.lower()
    hits = []
    for m in _TOCK_ACCESS.finditer(text):
        reg = m.group("reg")
        if reg not in declared:
            continue
        line_no = text.count("\n", 0, m.start("op")) + 1
        tail = text[m.end():m.end() + 300]
        fields = [x.lower() for x in _TOCK_FIELD.findall(tail)
                  if x not in ("SET", "CLEAR")]
        op = m.group("op")
        op = {"set": "write", "get": "read", "is_set": "read",
              "modify_no_read": "modify"}.get(op, op)
        hits.append({
            "file": str(f.relative_to(root)), "abs": str(f), "line": line_no,
            "receiver": m.group("recv"), "peripheral": periph,
            "register": reg, "operation": op, "fields": sorted(set(fields)),
            "source": (lines[line_no - 1].strip()[:160] if line_no <= len(lines) else ""),
        })
    return hits


# --------------------------------------------------------------------------- #
# Matching a hit against the constraints
# --------------------------------------------------------------------------- #

def _ops_match(constraint_op: str, hit_op: str) -> bool:
    """A `write` constraint gates write AND modify (a modify performs a write);
    a `read` constraint gates read and modify; `any` gates everything. Mirrors
    RegisterPlan._emit_state_gate's op expansion."""
    if constraint_op in ("any", "read/write", "read-write"):
        return True
    if constraint_op == "write":
        return hit_op in ("write", "modify", "reset")
    if constraint_op == "read":
        return hit_op in ("read", "modify")
    return constraint_op == hit_op


def match_hits(hits: list, idx: dict, periph_map: dict,
               alias: dict = None) -> list:
    """Attach every constraint that covers each hit."""
    alias = alias or {}
    out = []
    for h in hits:
        periph = alias.get(h["peripheral"], h["peripheral"])
        # resolve an instance to its register-block family (I2C3 -> i2c)
        module = periph_map.get(periph, periph)
        fam = cc._family(module) or module
        cands = idx.get((fam, h["register"]), [])
        matched = []
        for c in cands:
            if not _ops_match(c["operation"], h["operation"]):
                continue
            # field-scoped constraints only bite if the hit writes that field
            if c["fields"] and h["fields"] and not (set(c["fields"]) & set(h["fields"])):
                continue
            matched.append(c)
        if matched:
            out.append({**h, "constraints": matched})
    return out


# A call that hands a closure to a helper: `self.set_cr(|| ...)`, `foo(move |x|`.
_CLOSURE_CALL_RE = re.compile(r"(?:self\.)?(\w+)\(\s*(?:move\s*)?\|")
# A plain method call on self: `self.disable();`
_SELF_CALL_RE = re.compile(r"\bself\.(\w+)\s*\(")
_FN_DEF_RE_T = r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+{name}\b"
# The helper running its closure parameter: `f();` on a line of its own.
_CLOSURE_INVOKE_RE = re.compile(r"^\s*(\w+)\(\)\s*;\s*$")
_MAX_INLINED = 4


def _fn_body(path: str, name: str) -> str:
    """Body of a same-file `fn name`, or "" if it is not defined here."""
    src = Path(path).read_text().splitlines()
    fn_re = re.compile(_FN_DEF_RE_T.format(name=re.escape(name)))
    hit = next((i for i, ln in enumerate(src) if fn_re.match(ln)), None)
    if hit is None:
        return ""
    _start, body = enclosing_function(path, hit + 2)
    return body


_IMPL_HDR_RE = re.compile(
    r"^\s*impl(?:\s*<[^>]*>)?\s+(?:[\w:<>, '\$]+\s+for\s+)?(?P<ty>\$?\w+)")
_CTOR_RE = r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:const\s+|unsafe\s+)*fn\s+(?:new|new_\w+|acquire|enter|begin|start)\b"


def owning_type(path: str, line: int) -> str:
    """The type whose impl block contains `line`, or ''."""
    src = Path(path).read_text(errors="replace").splitlines()
    for j in range(min(line, len(src)) - 1, -1, -1):
        m = _IMPL_HDR_RE.match(src[j])
        if m:
            return m.group("ty").lstrip("$")
    return ""


def scope_guard(path: str, fields: list) -> str:
    """Does this file implement an RAII scope guard over `fields`?

    THE SHAPE. A project can hold a datasheet precondition open for the
    lifetime of a value. bxcan does it twice:

        MasterFilters::new()  sets CAN_FMR.FINIT ... Drop clears it
        Can::modify_config()  sets CAN_MCR.INRQ  ... Drop clears it

    Every filter-bank and bit-timing write happens while one of those values
    is alive, so the borrow checker guarantees the precondition for the whole
    borrow. The constraint is enforced by the type system, by hand -- which is
    exactly what witness gating automates, and the strongest evidence in this
    corpus that these rules are real and that careful projects already encode
    them.

    Nothing frame-local can see it. The precondition is not established before
    the access in any function; it is established before the VALUE exists, and
    the value is often not even the type performing the access -- bxcan writes
    through a `FilterBanks` view handed out by `MasterFilters`. Chasing that
    ownership properly needs type inference.

    So the test is file-scoped and deliberately explicit, three conditions:

      1. the file contains an `impl Drop for T`   -- something owns a scope
      2. every precondition field is SET somewhere in the file
      3. and CLEARED somewhere in the file        -- it is held, then released

    Set-and-cleared-and-Drop is the idiom and little else looks like it. A
    constructor that merely reads the field would not qualify. Returns the
    guard type, or "".
    """
    src = Path(path).read_text(errors="replace")
    guards = re.findall(r"^\s*impl(?:\s*<[^>]*>)?\s+Drop\s+for\s+(\$?\w+)",
                        src, re.M)
    if not guards or not fields:
        return ""
    for f in fields:
        setp = re.search(rf"\.{re.escape(f)}\s*\(\s*\)\s*\.\s*(set_bit|enabled)", src)
        clrp = re.search(rf"\.{re.escape(f)}\s*\(\s*\)\s*\.\s*(clear_bit|disabled)", src)
        if not (setp and clrp):
            return ""
    return guards[0].lstrip("$")


def guard_prologue(path: str, snippet: str, flagged_rel: int,
                   abs_line: int = 0) -> dict:
    """Code that provably runs BEFORE a flagged line but lives in a helper.

    Drivers do not open-code the datasheet dance at every call site; they
    factor it out. Both shapes appear in Tock's STM32 chip crate:

    A COMBINATOR taking a closure -- the guard brackets the closure body::

        fn set_cr<F>(&self, f: F) {
            self.registers.cr1.modify(CR1::SPE::CLEAR);   // <- the guard
            f();
            self.registers.cr1.modify(CR1::SPE::SET);
        }
        fn set_polarity(&self, p: ClockPolarity) {
            self.set_cr(|| self.registers.cr1.modify(CR1::CPOL::SET));  // flagged
        }

    A HELPER CALLED FIRST -- the guard is a preceding statement::

        fn set_speed(&self, speed: I2CSpeed, mhz: usize) {
            self.disable();                              // <- clears CR1::PE
            self.registers.ccr.modify(...);              // flagged
        }

    Both are correct code that a frame-local scan reports as unchecked. This
    resolves ONE level: same-file helpers only, no call graph, at most four
    inlined. Deeper chains still read as unchecked, which is stated in the
    report rather than hidden.

    Returns {"text": prologue, "inlined": [helper names]}.
    """
    before = snippet.splitlines()[:flagged_rel]
    names, closure_hosts = [], set()
    # The closure host wraps the flagged line, so its call site is at or above.
    for text in reversed(before):
        m = _CLOSURE_CALL_RE.search(text)
        if m:
            closure_hosts.add(m.group(1))
            names.append(m.group(1))
            break
    # Plain `self.foo()` statements preceding the flagged line, in order.
    for text in before:
        for m in _SELF_CALL_RE.finditer(text):
            if m.group(1) not in names:
                names.append(m.group(1))
    chunks, inlined = [], []
    for name in names:
        if len(inlined) >= _MAX_INLINED:
            break
        body = _fn_body(path, name)
        if not body:
            continue
        if name in closure_hosts:       # only the part that runs before f()
            keep = []
            for text in body.splitlines():
                m = _CLOSURE_INVOKE_RE.match(text)
                if m and m.group(1) not in ("return", "loop"):
                    break
                keep.append(text)
            body = "\n".join(keep)
        chunks.append(body)
        inlined.append(name)
    return {"text": "\n".join(chunks), "inlined": inlined}


def triage(matched: list, dialect: str = "pac") -> list:
    """corroborated / unchecked, via corroboration.deterministic_scan."""
    out = []
    for h in matched:
        fields = sorted({p["field"].lower() for c in h["constraints"]
                         for p in c["preconditions"] if p.get("field")})
        verdict = {"verdict": "no_precondition_fields", "fields": []}
        snippet = ""
        if fields:
            try:
                start, snippet = enclosing_function(h["abs"], h["line"])
                rel = h["line"] - start + 1
                pro = guard_prologue(h["abs"], snippet, rel, h["line"])
                if pro["text"]:
                    snippet = pro["text"] + "\n" + snippet
                    rel += len(pro["text"].splitlines())
                verdict = deterministic_scan(snippet, rel, fields, dialect)
                verdict["helpers_inlined"] = pro["inlined"]
                if verdict["verdict"] == "unchecked":
                    g = scope_guard(h["abs"], fields)
                    if g:
                        verdict["verdict"] = "corroborated"
                        verdict["scope_guard"] = g
            except Exception as e:                            # noqa: BLE001
                verdict = {"verdict": "scan_error", "fields": fields,
                           "error": str(e)[:120]}
        out.append({**h, "triage": verdict,
                    "snippet": snippet[:1500] if snippet else ""})
    return out


# --------------------------------------------------------------------------- #
# Build-readiness
# --------------------------------------------------------------------------- #

_PAC_DEP_RE = None


_SKIP_MANIFEST = re.compile(
    r"(^|/)(testsuite|tests|examples?|xtask|benches?|fuzz|ci)(/|$)")


def declared_pac_dependency(root: Path, pac: str) -> "tuple[bool, str]":
    """Does this project actually DEPEND on a PAC we can inject into?

    Readiness used to answer from `p.pac`, a hand-declared field naming which
    family's registers the project touches. That is not the same question. A
    crate can access CAN_FA1R by name while reaching it through its own
    `vcell` register block, and injecting gates into stm32f1 would never touch
    it -- bxcan, fdcan, stm32-fmc and lilos were all marked `ready` on exactly
    that confusion.

    Two things this must NOT count, both found by getting them wrong:

    * a manifest under testsuite/, examples/ or tests/. bxcan's testsuite
      pins stm32f1 0.14 to drive its hardware tests; the library it tests
      depends on vcell and nothing else. Gating the PAC would not touch the
      library, which is the thing being scanned.
    * a [dev-dependencies] entry, for the same reason at a smaller scale.

    A dependency on a `*xx-hal` counts, since the HAL consumes the PAC on the
    project's behalf. Returns (reachable, evidence naming the manifest).
    """
    hal_hit = None
    for man in sorted(root.rglob("Cargo.toml"))[:80]:
        rel = str(man.relative_to(root))
        if _SKIP_MANIFEST.search(rel.replace("\\", "/")):
            continue
        try:
            text = man.read_text(errors="replace")
        except OSError:
            continue
        section = ""
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("["):
                section = s.strip("[]")
                continue
            if s.startswith("#") or "=" not in s:
                continue
            if "dev-dependencies" in section or "build-dependencies" in section:
                continue
            # `[dependencies.stm32f1]` names the crate in the header itself
            name = (section.split(".", 1)[1] if section.startswith("dependencies.")
                    else s.split("=", 1)[0].strip().strip('"'))
            if name == pac:
                return True, f"depends on {pac} ({rel})"
            if re.fullmatch(r"stm32\w*xx-hal", name) and hal_hit is None:
                hal_hit = f"depends on {name} ({rel})"
    if hal_hit:
        return True, hal_hit
    return False, ("no dependency on a PAC or a *xx-hal in any library "
                   "manifest (test and example crates excluded)")


def readiness(p: Project, root: Path = None) -> dict:
    """Could this project ever be built against an injected crate, and what
    would it take? This is the ranked shortlist the build phase consumes."""
    if p.style == "tock":
        return {"reachable": False, "effort": "not-applicable",
                "pac_needed": None,
                "blockers": ["hand-written register maps; no PAC to inject into"]}
    if root is not None:
        ok, why = declared_pac_dependency(root, p.pac)
        if not ok:
            # Same category as tock: the registers are real and the findings
            # are real, but nothing we inject can reach them.
            return {"reachable": False, "effort": "not-applicable",
                    "pac_needed": None,
                    "blockers": [f"{why}; register access goes through the "
                                 f"project's own register block, so an "
                                 f"injected PAC cannot reach it"]}
    if not p.rms:
        return {"reachable": False, "effort": "missing-manual",
                "pac_needed": f"{p.pac} {PAC_VERSION}",
                "blockers": [f"no constraints for this chip "
                             f"({p.device}); its manual is not in the corpus"]}
    blockers = []
    if p.pac_pinned and p.pac_pinned != PAC_VERSION:
        blockers.append(f"pins {p.pac} {p.pac_pinned}, injector targets "
                        f"{PAC_VERSION}")
    if p.hal:
        pairs = p.hal_pinned.lstrip("^").startswith("0.23")
        if not pairs:
            blockers.append(f"{p.hal} {p.hal_pinned} does not pair with PAC "
                            f"{PAC_VERSION}; needs the 0.23 bump")
        blockers.append(f"{p.hal} must be patched (4-line associated-type "
                        "bound; see docs/generic_friction.md)")
    effort = ("ready" if not blockers else
              "pac-gap" if any("pins" in b for b in blockers) else "hal-bump")
    return {"reachable": True, "effort": effort,
            "pac_needed": f"{p.pac} {PAC_VERSION}", "blockers": blockers}


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

def clone(p: Project, dest: Path) -> Path | None:
    cmd = ["git", "clone", "-q", "--depth", "1"]
    if p.ref:
        cmd += ["--branch", p.ref]
    try:
        subprocess.run(cmd + [p.repo, str(dest)], check=True,
                       capture_output=True, timeout=CLONE_TIMEOUT)
        return dest
    except Exception as e:                                    # noqa: BLE001
        print(f"  clone failed: {str(e)[:160]}")
        return None


def scan_project(p: Project, root: Path, periph_map: dict) -> dict:
    files = _rust_files(root, p.subdirs)
    scanner = {"pac_direct": scan_pac_direct, "tock": scan_tock}.get(p.style)
    hits = []
    if scanner:
        for f in files:
            hits.extend(scanner(f, root))
    # Group hits by the manuals that govern their file, so a multi-family repo
    # is never matched across families.
    by_rms: dict = {}
    for h in hits:
        key = tuple(p.rms_for(h["file"]))
        by_rms.setdefault(key, []).append(h)
    idx_all, matched = {}, []
    for key, group in by_rms.items():
        if not key:
            continue                      # family with no manuals: skip
        idx = constraint_index(list(key))
        idx_all.update(idx)
        matched.extend(match_hits(group, idx, periph_map,
                                  p.periph_alias))
    idx = idx_all
    triaged = triage(matched,
                     p.dialect or ("tock" if p.style == "tock" else "pac"))
    regs = Counter(f"{h['peripheral']}/{h['register']}" for h in hits)
    verdicts = Counter(h["triage"]["verdict"] for h in triaged)
    return {
        "name": p.name, "repo": p.repo, "style": p.style, "note": p.note,
        "rms": p.rms, "device": p.device, "pac": p.pac,
        "pac_pinned": p.pac_pinned, "hal": p.hal, "hal_pinned": p.hal_pinned,
        "rust_files": len(files),
        "register_accesses": len(hits),
        "distinct_registers": len(regs),
        "top_registers": regs.most_common(12),
        "constraints_available": sum(len(v) for v in idx.values()),
        "hits": len(triaged),
        "verdicts": dict(verdicts),
        "findings": triaged,
        "readiness": readiness(p, root),
    }


_EFFORT_NOTE = {
    "ready": "already on a HAL that pairs with PAC 0.16 — buildable now",
    "hal-bump": "needs the HAL bumped to a PAC-0.16 pairing, then the 4-line "
                "associated-type patch",
    "pac-gap": "pins a PAC generation the injector does not target; the "
               "svd2rust template moved (see docs/stm_injection_sweep.md §1)",
    "missing-manual": "its chip's reference manual is not in the corpus — "
                      "nothing to check against, not a clean result",
    "not-applicable": "no PAC to inject into",
}


def write_report(results: list, path: Path) -> None:
    """docs/project_landscape.md — the deliverable this phase produces."""
    md = ["# Where our constraints would bite: a scan of higher-level projects",
          "",
          "Generated by `applications/pac_codegen/experiments/scan_projects.py`.",
          "This is a **static** survey: it reads each project's own Rust source,",
          "extracts hardware register accesses, and cross-references our",
          "extracted datasheet constraints. Nothing is compiled.",
          "",
          "**A hit is a candidate, not a bug.** `unchecked` means no precondition",
          "field is referenced before the access; `corroborated` means the",
          "project already performs the datasheet-prescribed check nearby.",
          "",
          "**Guards in a helper are followed one level.** Drivers factor the",
          "datasheet dance into a combinator — Tock's SPI wraps every config",
          "write in `set_cr(|| ...)`, which clears `SPE` first and restores it",
          "after. A frame-local scan calls that correct code unchecked; six of",
          "Tock's seventeen SPI CR1 sites are exactly this shape. When a flagged",
          "line sits inside a closure handed to a same-file helper, the part of",
          "that helper which runs before the closure is scanned too. Deeper",
          "chains, and guards in a caller that is not a closure host, still read",
          "as unchecked.",
          "",
          "**Guard syntax is dialect-specific.** svd2rust spells a field as an",
          "accessor — `r.stop().bit_is_set()` — while tock-registers spells it",
          "as a path, `CR1::STOP::SET`, and never as `.stop()`. Matching Tock",
          "with the svd2rust pattern fails twice: it misses every real guard and",
          "it fires on unrelated methods that share a field's name. Tock's I2C",
          "driver calls a helper `self.stop()` beside its `CR1::STOP::SET`",
          "writes, and that — not any datasheet check — was what marked three",
          "sites corroborated in an earlier run.",
          "",
          "**Triage caveat: a whole-register gate over-approximates.** When a",
          "constraint lists no `fields restricted`, it gates the whole register",
          "even though the datasheet note usually attaches to specific bits, so",
          "read the *fields written* column before the verdict. Field-level",
          "gating is now the default and states these rules against the bits",
          "the datasheet names, which removes most of this caveat; a",
          "whole-register gate whose condition is a field of that same register",
          "is no longer emitted at all.",
          "",
          "**Scanner accuracy — NOT re-measured in this run.** The check is to",
          "scan `stm32f4xx-hal` and confirm the scanner independently finds the",
          "sites the COMPILE route finds. That HAL is not among the",
          "projects scanned here, so this page cannot compute the agreement,",
          "and the figure previously quoted (*31 of 31*) is stale: it was",
          "measured against a gate set that no longer exists, before",
          "whole-register gates on a bit of the same register were refused.",
          f"The sweep currently finds {_ground_truth_n()} enforcement sites in",
          "that driver. Re-establishing the comparison means adding the HAL to",
          "the scan.",
          "",
          "## Summary",
          "",
          "| project | style | manuals | .rs files | register accesses | hits | unchecked | corroborated | build-readiness |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        v = r["verdicts"]
        md.append(
            f"| [{r['name']}]({r['repo']}) | {r['style']} | "
            f"{', '.join(r['rms']) or '—'} | {r['rust_files']} | "
            f"{r['register_accesses']} | **{r['hits']}** | "
            f"{v.get('unchecked', 0)} | {v.get('corroborated', 0)} | "
            f"`{r['readiness']['effort']}` |")

    md += ["", "## Build-readiness", "",
           "What each project would need before it could be built against an",
           "injected chip crate — the ranked input to the build phase.", "",
           "| project | reachable | PAC needed | blockers |", "|---|---|---|---|"]
    for r in sorted(results, key=lambda x: (x["readiness"]["effort"] != "ready",
                                            -x["hits"])):
        rd = r["readiness"]
        md.append(f"| {r['name']} | {'yes' if rd['reachable'] else 'no'} | "
                  f"{rd['pac_needed'] or '—'} | "
                  f"{'; '.join(rd['blockers']) or 'none'} |")
    md += ["", "Effort key:", ""]
    md += [f"- `{k}` — {v}" for k, v in _EFFORT_NOTE.items()]

    for r in results:
        if not r["findings"]:
            continue
        md += ["", f"## {r['name']} — {r['hits']} candidate sites", "",
               f"*{r['note']}*", ""]
        by_reg = defaultdict(list)
        for h in r["findings"]:
            by_reg[f"{h['peripheral']}/{h['register']}"].append(h)
        for reg, hs in sorted(by_reg.items(), key=lambda kv: -len(kv[1])):
            c = hs[0]["constraints"][0]
            pre = ", ".join(f"{q['register']}.{q['field']} {q['state']}"
                            for q in c["preconditions"]) or "—"
            md += [f"### `{reg}` — {len(hs)} site(s)", "",
                   f"- **rule** ({c['kind']}, {c['operation']}): {pre}",
                   f"- **fields restricted**: {', '.join(c['fields']) or 'whole register'}",
                   f"- **datasheet** ({c['rm']}): \"{c['quote'][:220]}\"", ""]
            md.append("| file:line | op | fields written | verdict |")
            md.append("|---|---|---|---|")
            for h in hs[:20]:
                md.append(f"| `{h['file']}:{h['line']}` | {h['operation']} | "
                          f"{', '.join(h['fields']) or '—'} | "
                          f"**{h['triage']['verdict']}** |")
            md.append("")

    md += ["", "## Limits", "",
           "- Peripheral attribution is heuristic: it comes from the receiver",
           "  expression, falling back to the module the code lives in. The",
           "  receiver text is carried in the JSON for review.",
           "- Chip attribution is per path prefix, and derived from each driver",
           "  crate's OWN Cargo features rather than the family in its name.",
           "  Getting this wrong is not conservative: Hubris's `drv/stm32xx-i2c`",
           "  builds only for H7 and G0, and an earlier run matched it against",
           "  RM0386, an F4 manual whose I2C is a different peripheral",
           "  generation — START/STOP/PEC sit in CR1 there and in CR2 here. All",
           "  14 of its reported hits were artefacts of that mismatch.",
           "- A declared subdirectory missing from a checkout is now a hard",
           "  error. Silence looked like a clean project: an earlier run",
           "  recorded Tock as \"0 .rs files, 0 register accesses\" and the zero",
           "  went unquestioned. It is 45 files and 1203 accesses.",
           "- A project on a manual we have not processed scans clean for the",
           "  wrong reason — that is the `missing-manual` verdict, and it is not",
           "  the same as 'no constrained registers touched'.", ""]
    path.write_text("\n".join(md))
    print(f"report: {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=[],
                    help="scan a single project by name (repeatable)")
    ap.add_argument("--local", action="append", default=[], metavar="NAME=PATH",
                    help="use an existing checkout instead of cloning")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    local = dict(s.split("=", 1) for s in args.local)
    projects = [p for p in PROJECTS if not args.only or p.name in args.only]
    if not projects:
        sys.exit(f"no project matching {args.only}")

    # Instance -> register-block module, from a provisioned PAC. One map per
    # PAC crate is enough: instance naming is a family property.
    periph_maps = {}
    for p in projects:
        if p.pac in periph_maps:
            continue
        d = APP_DIR / "vendored" / "pac" / p.pac / "src" / p.device
        periph_maps[p.pac] = (rust_codegen.peripheral_instance_map(d)
                              if d.is_dir() else {})

    results, tmpdirs = [], []
    try:
        for p in projects:
            print(f"\n=== {p.name} ({p.style}) ===", flush=True)
            if p.name in local:
                root = Path(local[p.name])
            else:
                td = Path(tempfile.mkdtemp(prefix=f"scan_{p.name}_"))
                tmpdirs.append(td)
                root = clone(p, td / p.name)
                if root is None:
                    continue
            r = scan_project(p, root, periph_maps.get(p.pac, {}))
            results.append(r)
            print(f"  {r['rust_files']} .rs files | "
                  f"{r['register_accesses']} register accesses on "
                  f"{r['distinct_registers']} distinct registers")
            print(f"  constraints available for its manuals: "
                  f"{r['constraints_available']}")
            print(f"  HITS on constrained registers: {r['hits']}  {r['verdicts']}")
            print(f"  readiness: {r['readiness']['effort']} "
                  f"({r['readiness']['pac_needed']})")
            for h in r["findings"][:5]:
                print(f"    {h['file']}:{h['line']} {h['peripheral']}/"
                      f"{h['register']} {h['operation']} -> "
                      f"{h['triage']['verdict']}")
    finally:
        for td in tmpdirs:
            shutil.rmtree(td, ignore_errors=True)

    OUT.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else OUT / "scan_projects.json"
    out.write_text(json.dumps(results, indent=1, default=str) + "\n")
    print(f"\njson: {out}")
    if results:
        write_report(results, REPO / "docs" / "project_landscape.md")


if __name__ == "__main__":
    main()
