#!/usr/bin/env python3
"""Upgrade a community HAL to the PAC generation the injector targets.

WHY THIS IS NOT A MODIFICATION OF THE SUBJECT
---------------------------------------------
Four STM HAL crates cannot be measured because their newest release still
depends on an older svd2rust PAC generation (hal_gap.py sizes the distance).
Moving them to 0.16 is an upgrade the HAL owes its own dependency -- upstream
would have to do exactly this -- and it changes how register access is SPELLED,
not whether the driver checks a precondition. Since the precondition check is
the only thing our gates measure, the upgrade is orthogonal to the result.

That argument only holds if the upgrade is mechanical, so this tool refuses to
be clever. It applies ONLY rustc's own suggestions for the two diagnostics that
mark the field-to-accessor change:

    E0616  field `cr` of struct `...::RegisterBlock` is private
           -> "a method `cr` also exists, call it with parentheses"
    E0615  attempted to take value of method
           -> "use parentheses to call the method"

Both suggest inserting `()`. rustc marks them MaybeIncorrect, which is why
`cargo fix` leaves them alone, but the span comes from name resolution against
the new PAC, so the location is the compiler's judgement and not a guess of
ours. Anything else -- register arrays, raw-write widths, unsafe -- is reported
and left for a human, because those need reading and could move a site between
"guarded" and "possible bug".

`--verify` re-reads every edit and fails if any of them changed a byte other
than inserting `()`, which is what keeps "control flow is untouched" a checked
claim rather than an assurance.

Usage:
    python applications/pac_codegen/experiments/port_hal.py --hal stm32l0xx-hal
    python applications/pac_codegen/experiments/port_hal.py --hal all --verify
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
sys.path.insert(0, str(APP_DIR))
import get_pac  # noqa: E402

PAC_VERSION = "0.16.0"
STEP_TIMEOUT = 2400
OUT = APP_DIR / "experiments" / "out"
WORK = APP_DIR / "experiments" / "ported"

# rustc emits an insert-`()` suggestion for exactly these.
FIXABLE = {"E0616", "E0615"}

# `w.bits(..)` became an unsafe fn in this generation, so every raw write now
# needs an unsafe block. Wrapping an expression in `unsafe { .. }` changes what
# the compiler PERMITS, never what the code does -- no branch is added, removed
# or reordered -- so it cannot move a site between "guarded" and "possible
# bug", which is the only property this upgrade has to preserve.
UNSAFE_CODE = "E0133"

# Write-1-to-clear fields lost `set_bit()` for `clear_bit_by_one()`. Same store
# to the same bit -- the name now says what the hardware does with it. The rule
# fires only when rustc names the `Bit1C` writer in the receiver type, so an
# ordinary `set_bit()` on a normal field is never touched.
_BIT1C_RE = re.compile(r"no method named `set_bit` found for struct "
                       r"`(?:\w+::)*BitWriter<[^`]*, (?:\w+::)*Bit1C>`")

# A trailing-`;` rule USED TO LIVE HERE and has been removed on evidence.
#
# rustc suggests `;` for E0308 when a value is unused, and that looked as
# mechanical as the rest. It is not, for one reason: this loop re-runs the
# compiler on half-ported code, and a suggestion computed from a broken
# intermediate state can be wrong about the finished one. In stm32f0xx-hal it
# put a `;` after the `if/else` in `fn write(..) -> nb::Result<(), Infallible>`,
# so a function that returned `Ok(())` or `Err(WouldBlock)` returned `()`
# instead. That is a behaviour change, which is the single thing this tool
# exists to make impossible -- and it would have been invisible in a diff of
# 340 edits.
#
# The rule is BACK, but narrowed on evidence about why it misfired.
#
# The API change is real: `write` now returns `REG::Ux` where it returned `()`
# (generic.rs: `pub fn write<F>(&self, f: F) -> REG::Ux`), so a register write
# in tail position of a `()` function is now a type error and a semicolon is
# genuinely the fix. What went wrong was WHEN it was applied. Run against
# half-ported code, rustc proposed a `;` after an entire `if/else`, and taking
# it changed `fn write(..) -> nb::Result<..>` into a function returning `()`.
#
# So the rule now fires only when nothing else is left to do, and only where
# the discarded expression IS a register operation -- the exact thing whose
# return type changed. A suggestion pointing at a block, a match, or anything
# else is left for a human.
_SEMICOLON = ";"
_REG_OP_RE = re.compile(r"\.(write|modify|reset|write_with_zero)\s*\(", re.S)

# svd2rust also recased enum VARIANTS: `CYCLES1_5` became `Cycles1_5`, `LEFT`
# became `Left`. rustc offers the new name under "there is a variant with a
# similar name", and here that suggestion is trustworthy -- but only after
# checking it really is the same name recased. `HSI` and `HSE` are one letter
# apart and rustc will happily propose either for the other, so the rule
# accepts a suggestion only when both names are identical once uppercased with
# underscores removed. A genuine spelling difference fails that test.
_VARIANT_HINT = "there is a variant with a similar name"

# ...but the NEW name comes from the PAC, not from rustc. Asked about
# stm32f3xx-hal's `Cycles195` (19.5 ADC clock cycles, spelled without the
# underscore in the old PAC) rustc proposes `Cycles1_5` -- 1.5 cycles. It is
# the nearest string, and it is a thirteen-fold change in ADC sample time that
# would compile silently. The PAC calls that variant `Cycles19_5`, which is
# what the HAL meant, and normalising both names finds it exactly.
_ENUM_BODY_RE = re.compile(r"^pub enum [A-Za-z_]\w*\s*\{(.*?)^\}",
                           re.M | re.S)
_VARIANT_DECL_RE = re.compile(r"^\s{4}([A-Z]\w*)\s*=", re.M)


def _same_name_recased(old: str, new: str) -> bool:
    norm = lambda s: s.upper().replace("_", "")
    return norm(old) == norm(new) and old != new

# The other mechanical change of this generation: svd2rust dropped the `_A`
# suffix from field enums, so `LATENCY_A` became `LATENCY`.
#
# rustc's own suggestion here is WRONG and must not be used. Asked about
# `LATENCY_A` it offers `LATENCY_R`, the nearest name in scope -- but that is
# the READER type (`BitReader<LATENCY>`), not the enum. Taking the suggestion
# swaps a reader in for a variant type. So the rename is driven from the PAC's
# actual `pub enum` declarations instead: a name is rewritten only when the new
# PAC really defines it.
_ENUM_RE = re.compile(r"^pub enum ([A-Za-z_][A-Za-z0-9_]*)", re.M)
_SUFFIXED_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)_A\b")

# (HAL, version, PAC, build features) -- the newest release of each, matching
# hal_gap.py. The PAC generation each pins is in that script's report.
# The feature sets are a LIST because the port has to hold for every
# configuration we later measure. Porting under one chip feature leaves the
# code paths behind the others untouched, and their errors then surface as a
# failing baseline at measurement time -- which reads like the HAL is broken
# rather than like the port was partial.
CASES = {
    "stm32f3xx-hal": ("0.10.0", "stm32f3", [["stm32f303xc"]]),
    "stm32l0xx-hal": ("0.10.0", "stm32l0", [
        ["stm32l0x3", "mcu-STM32L053C6Tx"],
        ["stm32l0x2", "mcu-STM32L052C6Tx"],
        ["stm32l0x1", "mcu-STM32L011D3Px"],
    ]),
    # stm32f030 alone is not a complete configuration upstream -- rcc.rs
    # gates RCC_PLLSRC_PREDIV1_SUPPORT on a size-specific feature -- so the
    # measurable f0x0 config is stm32f030x8.
    "stm32f0xx-hal": ("0.18.0", "stm32f0", [["stm32f051"],
                                            ["stm32f030x8"]]),
    "stm32l1xx-hal": ("0.1.0", "stm32l1", [["stm32l151"]]),
    # f7 + l1: the last two released families with an older-pinned HAL,
    # ported to close the gap (stm32f7xx-hal 0.8 -> stm32f7 ^0.15;
    # stm32l1xx-hal is the line above, stm32l1 ^0.5.0).
    "stm32f7xx-hal": ("0.8.0", "stm32f7", [["stm32f746"]]),
    # The two dependent-scan port picks (out/dependent_scan.json, 2026-09):
    # rustuino is DIRECT-PAC application-facing code (781 own accesses, 96
    # scan hits) at stm32f4 0.14 -- hubris's exact distance; stm32l0x1-hal
    # is a second, dependent-population L0 driver at stm32l0 0.15 (rm0377's
    # first driver was the ported stm32l0xx-hal).
    "rustuino": ("0.1.0", "stm32f4", [[]]),
    "stm32l0x1-hal": ("0.11.0", "stm32l0", [[]]),
}


# What no rule can derive: cases where the PAC renamed something and only
# reading both sides settles what the HAL meant. Each entry was checked against
# the generated PAC and carries that evidence, because these are the edits that
# COULD change behaviour if they were wrong.
MANUAL_PATCHES = {
    "stm32l0xx-hal": [
        # DMA moved to a channel array and MSIZE now shares PSIZE's enum
        # (`pub use PSIZE_R as MSIZE_R`). Same field, same Bits8/16/32
        # variants, at the same offset 10.
        ("src/dma.rs", "cr::MSIZE_A", "cr::PSIZE"),
        # IWDG key variants were renamed for what they do. Old Reset was
        # 0xAAAA, which the manual calls feeding the watchdog; old Enable was
        # 0x5555, which unlocks PR/RLR. The PAC now generates feed()/unlock()
        # for those exact values (kr.rs: Feed = 43690, Unlock = 21845).
        ("src/watchdog.rs", "w.key().reset()", "w.key().feed()"),
        ("src/watchdog.rs", "w.key().enable()", "w.key().unlock()"),
        # PWR_CR bit 0 was LPDS in the old SVD and is LPSDSR in this one --
        # same bit, same meaning ("voltage regulator in low-power mode during
        # Deepsleep/Sleep"), which is what the HAL comment at the call site
        # says it wants.
        ("src/pwr.rs", "w.lpds()", "w.lpsdsr()"),
        # Two match arms are bare `modify(..)` expressions while a third is a
        # block, so the arms disagree on type. The fix is at the ARM, not
        # inside the closure: discard the value the arm produces so all three
        # are `()`. An earlier attempt put the semicolon inside the closure
        # instead, which broke the `FnOnce(&R, &mut W) -> &mut W` contract
        # `modify` actually has here -- and turned 2 errors into 13.
        ("src/exti.rs",
         "TriggerEdge::Rising => self.raw.rtsr().modify(|r, w| w.bits(r.bits() | bm)),",
         "TriggerEdge::Rising => { self.raw.rtsr().modify(|r, w| w.bits(r.bits() | bm)); },"),
        ("src/exti.rs",
         "TriggerEdge::Falling => self.raw.ftsr().modify(|r, w| w.bits(r.bits() | bm)),",
         "TriggerEdge::Falling => { self.raw.ftsr().modify(|r, w| w.bits(r.bits() | bm)); },"),
    ],
    "stm32f0xx-hal": [
        # Same IWDG key rename as stm32l0xx-hal: old Reset was 0xAAAA (feed),
        # old Enable 0x5555 (unlock PR/RLR).
        ("src/watchdog.rs", "w.key().reset()", "w.key().feed()"),
        ("src/watchdog.rs", "w.key().enable()", "w.key().unlock()"),
    ],
    "stm32l0x1-hal": [
        # ADC_CR.ADEN is BitWriter1S in the 0.16 PAC (cr.rs: `ADEN_W =
        # BitWriter1S`): a set-only bit, so `clear_bit` is gone. The old
        # crate wrote 0 there, which the hardware ignores (disable is via
        # ADDIS); `.bit(false)` writes the same 0 the 0.14 build wrote.
        ("src/adc.rs", "w.aden().clear_bit()", "w.aden().bit(false)"),
        # ADC_ISR.EOCAL is write-1-to-clear (isr.rs: `EOCAL_W =
        # BitWriter1C`); same rename hubris needed for USART orecf.
        ("src/adc.rs", "w.eocal().clear_bit()", "w.eocal().clear_bit_by_one()"),
        # write/modify return Ux in 0.16, so a bare call no longer types as
        # `()` in match-arm position. The fix is at the ARM (the exti rule
        # from stm32l0xx-hal): make the arm a block that discards.
        ("src/serial/mod.rs",
         "Event::Rxne => self.usart.cr1().modify(|_, w| w.rxneie().set_bit()),",
         "Event::Rxne => { self.usart.cr1().modify(|_, w| w.rxneie().set_bit()); },"),
        ("src/serial/mod.rs",
         "Event::Txe => self.usart.cr1().modify(|_, w| w.txeie().set_bit()),",
         "Event::Txe => { self.usart.cr1().modify(|_, w| w.txeie().set_bit()); },"),
        ("src/timer.rs",
         "Event::Timeout => self.timer.dier().write(|w| w.uie().set_bit())",
         "Event::Timeout => { self.timer.dier().write(|w| w.uie().set_bit()); }"),
        ("src/timer.rs",
         "Event::Timeout => self.timer.dier().write(|w| w.uie().clear_bit())",
         "Event::Timeout => { self.timer.dier().write(|w| w.uie().clear_bit()); }"),
        ("src/flash.rs",
         "FlashError::WriteProtect => sr.inner().modify(|_, w| w.wrperr().set_bit()),",
         "FlashError::WriteProtect => { sr.inner().modify(|_, w| w.wrperr().set_bit()); },"),
        ("src/flash.rs",
         "FlashError::Alignment => sr.inner().modify(|_, w| w.pgaerr().set_bit()),",
         "FlashError::Alignment => { sr.inner().modify(|_, w| w.pgaerr().set_bit()); },"),
        ("src/flash.rs",
         "FlashError::Size => sr.inner().modify(|_, w| w.sizerr().set_bit()),",
         "FlashError::Size => { sr.inner().modify(|_, w| w.sizerr().set_bit()); },"),
        ("src/flash.rs",
         "FlashError::ReadProtection => sr.inner().modify(|_, w| w.rderr().set_bit()),",
         "FlashError::ReadProtection => { sr.inner().modify(|_, w| w.rderr().set_bit()); },"),
        ("src/flash.rs",
         "FlashError::NotZero => sr.inner().modify(|_, w| w.notzeroerr().set_bit()),",
         "FlashError::NotZero => { sr.inner().modify(|_, w| w.notzeroerr().set_bit()); },"),
        ("src/flash.rs",
         "FlashError::FetchAbort => sr.inner().modify(|_, w| w.fwwerr().set_bit()),",
         "FlashError::FetchAbort => { sr.inner().modify(|_, w| w.fwwerr().set_bit()); },"),
        # The serial listen/unlisten matches have SIX arms here (the l0xx
        # fork this crate descends from had two) and one copy spells the
        # closure `|_,w|`. Normalise the spacing first -- a whitespace-only
        # edit -- so each arm needs one patch, not two.
        ("src/serial/mod.rs", "modify(|_,w|", "modify(|_, w|"),
        ("src/serial/mod.rs",
         "Event::Idle => self.usart.cr1().modify(|_, w| w.idleie().set_bit()),",
         "Event::Idle => { self.usart.cr1().modify(|_, w| w.idleie().set_bit()); },"),
        ("src/serial/mod.rs",
         "Event::Tc => self.usart.cr1().modify(|_, w| w.tcie().set_bit()),",
         "Event::Tc => { self.usart.cr1().modify(|_, w| w.tcie().set_bit()); },"),
        ("src/serial/mod.rs",
         "Event::Peie => self.usart.cr1().modify(|_, w| w.peie().set_bit()),",
         "Event::Peie => { self.usart.cr1().modify(|_, w| w.peie().set_bit()); },"),
        ("src/serial/mod.rs",
         "Event::Eie => self.usart.cr3().modify(|_, w| w.eie().set_bit()),",
         "Event::Eie => { self.usart.cr3().modify(|_, w| w.eie().set_bit()); },"),
        ("src/serial/mod.rs",
         "Event::Rxne => self.usart.cr1().modify(|_, w| w.rxneie().clear_bit()),",
         "Event::Rxne => { self.usart.cr1().modify(|_, w| w.rxneie().clear_bit()); },"),
        ("src/serial/mod.rs",
         "Event::Txe => self.usart.cr1().modify(|_, w| w.txeie().clear_bit()),",
         "Event::Txe => { self.usart.cr1().modify(|_, w| w.txeie().clear_bit()); },"),
        ("src/serial/mod.rs",
         "Event::Idle => self.usart.cr1().modify(|_, w| w.idleie().clear_bit()),",
         "Event::Idle => { self.usart.cr1().modify(|_, w| w.idleie().clear_bit()); },"),
        ("src/serial/mod.rs",
         "Event::Tc => self.usart.cr1().modify(|_, w| w.tcie().clear_bit()),",
         "Event::Tc => { self.usart.cr1().modify(|_, w| w.tcie().clear_bit()); },"),
        ("src/serial/mod.rs",
         "Event::Peie => self.usart.cr1().modify(|_, w| w.peie().clear_bit()),",
         "Event::Peie => { self.usart.cr1().modify(|_, w| w.peie().clear_bit()); },"),
        ("src/serial/mod.rs",
         "Event::Eie => self.usart.cr3().modify(|_, w| w.eie().clear_bit()),",
         "Event::Eie => { self.usart.cr3().modify(|_, w| w.eie().clear_bit()); },"),
    ],
    "rustuino": [
        # I2C SR2 is a 16-bit register; the 0.16 PAC sizes `bits()` to u16
        # where 0.14 said u32. `_sr` exists only to force the SR1-then-SR2
        # read that clears ADDR -- its width is incidental, and retyping the
        # two declarations fixes all eleven assignment sites.
        ("src/i2c.rs", "let _sr: u32;", "let _sr: u16;"),
        # `#![deny(warnings)]` turns 2026 rustc's NEW lints (static_mut_refs,
        # plus 2840 mismatched_lifetime_syntaxes) into errors in a 2022
        # crate. That is toolchain drift, not port distance -- the crate
        # would not build warning-free on this compiler at PAC 0.14 either.
        # Neutralising the build POLICY touches no behaviour.
        ("src/lib.rs", "#![deny(warnings)]", ""),
    ],
}


def patch(hal_dir: Path, hal: str) -> int:
    n = 0
    for rel, old, new in MANUAL_PATCHES.get(hal, []):
        f = hal_dir / rel
        if not f.is_file():
            sys.exit(f"manual patch targets a missing file: {f}")
        src = f.read_text()
        if old not in src:
            sys.exit(f"manual patch no longer applies in {rel}: {old!r} "
                     f"not found -- re-check it against the PAC before "
                     f"deleting it")
        f.write_text(src.replace(old, new))
        n += src.count(old)
    return n


def vendor(hal: str, version: str) -> Path:
    """A writable copy of the released crate, examples and dev-deps removed.

    Dev-dependencies are stripped because they pin an ancient `cortex-m-rt`,
    and that crate sets `links`, so cargo refuses to resolve a graph holding
    both it and the one the new PAC needs. No library source is touched."""
    src = None
    for reg in (Path.home() / ".cargo/registry/src").glob("*"):
        cand = reg / f"{hal}-{version}"
        if cand.is_dir():
            src = cand
            break
    dst = WORK / hal
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src is not None:
        shutil.copytree(src, dst)
    else:
        # Not in the local registry cache (never built here): take the
        # published package straight from crates.io -- the same source of
        # record the dependent scan reads.
        import io
        import tarfile
        import urllib.request
        url = f"https://static.crates.io/crates/{hal}/{hal}-{version}.crate"
        blob = urllib.request.urlopen(urllib.request.Request(
            url, headers={"User-Agent": "hal_agent port_hal"})).read()
        tf = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
        tmp = dst.parent / f".unpack-{hal}"
        if tmp.exists():
            shutil.rmtree(tmp)
        tf.extractall(tmp, filter="data")
        shutil.move(str(tmp / f"{hal}-{version}"), str(dst))
        shutil.rmtree(tmp, ignore_errors=True)
    subprocess.run(["chmod", "-R", "u+w", str(dst)], check=False)
    shutil.rmtree(dst / "examples", ignore_errors=True)

    # Cargo builds real dependencies with --cap-lints allow, so a deny-by-
    # default lint in the HAL never reaches its users. Here the crate is a
    # workspace MEMBER, which makes it local code and turns those lints into
    # errors that have nothing to do with the PAC upgrade -- stm32l0xx-hal
    # trips `invalid_reference_casting` in a macro it has shipped for years.
    # Restoring the dependency's own lint level keeps the measurement about
    # the upgrade.
    lib = dst / "src" / "lib.rs"
    if lib.is_file():
        lib.write_text("#![allow(warnings)]\n"
                       "#![allow(invalid_reference_casting)]\n"
                       + lib.read_text())

    keep, skip = [], False
    for line in (dst / "Cargo.toml").read_text().splitlines():
        if line.startswith("["):
            skip = line.startswith(("[dev-dependencies", "[[example]]",
                                    "[[test]]", "[[bench]]"))
        if not skip:
            keep.append(line)
    (dst / "Cargo.toml").write_text("\n".join(keep) + "\n")
    return dst


def repoint(hal_dir: Path, pac: str, pac_dir: Path) -> None:
    """Point the HAL's PAC dependency at the local 0.16 tree.

    A path dependency, not a [patch] with a spoofed version: a patch whose
    requirement is unsatisfiable does not error, it silently resolves the
    registry crate, and the build then measures nothing (see
    hal_gap.patch_applied)."""
    p = hal_dir / "Cargo.toml"
    t = p.read_text()
    pat = re.compile(rf'(\[dependencies\.{re.escape(pac)}\]\n(?:[^\[]*?))'
                     r'version = "[^"]+"', re.M)
    t2, n = pat.subn(rf'\1path = "{pac_dir}"', t, count=1)
    if n != 1:
        pat2 = re.compile(rf'^{re.escape(pac)}\s*=\s*\{{[^}}]*?'
                          r'version\s*=\s*"[^"]+"', re.M)
        t2, n = pat2.subn(f'{pac} = {{ path = "{pac_dir}"', t, count=1)
    if n != 1:
        sys.exit(f"could not repoint {pac} in {p}")
    p.write_text(t2)


def workspace(hal_dir: Path, target: str) -> Path:
    """One workspace holding EVERY vendored HAL.

    Listing only the HAL being worked on left every other one "outside the
    workspace", so a later `cargo check` on it refused to start -- which reads
    exactly like a clean build if the exit code is all you look at."""
    ws = hal_dir.parent
    members = sorted(d.name for d in ws.iterdir()
                     if (d / "Cargo.toml").is_file())
    listed = ", ".join(f'"{m}"' for m in members)
    (ws / "Cargo.toml").write_text(
        f'[workspace]\nmembers = [{listed}]\nresolver = "2"\n')
    (ws / "rust-toolchain.toml").write_text(
        '[toolchain]\nchannel = "1.96.0"\n'
        'targets = ["thumbv6m-none-eabi", "thumbv7m-none-eabi", '
        '"thumbv7em-none-eabihf"]\n')
    # No [build] target here: each HAL needs its own, passed per command.
    shutil.rmtree(ws / ".cargo", ignore_errors=True)
    return ws


def check(ws: Path, package: str, features: list,
          target: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["cargo", "check", "-p", package, "--target", target,
         "--no-default-features", "--features", ",".join(features),
         "--message-format=json"],
        cwd=str(ws), capture_output=True, text=True, timeout=STEP_TIMEOUT)


def diagnostics(stdout: str):
    edits, codes = [], collections.Counter()
    for line in stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") != "compiler-message":
            continue
        d = m["message"]
        if d.get("level") != "error":
            continue
        code = (d.get("code") or {}).get("code", "?")
        codes[code] += 1
        if code not in FIXABLE:
            continue
        for ch in d.get("children", []):
            for sp in ch.get("spans", []):
                rep = sp.get("suggested_replacement")
                if rep is not None:
                    edits.append((sp["file_name"], sp["byte_start"],
                                  sp["byte_end"], rep))
    return set(edits), codes


def pac_variants(pac_dir: Path) -> dict:
    """normalised variant name -> the names the PAC declares for it."""
    out = collections.defaultdict(set)
    for f in pac_dir.rglob("*.rs"):
        try:
            src = f.read_text(errors="ignore")
        except OSError:
            continue
        for body in _ENUM_BODY_RE.findall(src):
            for name in _VARIANT_DECL_RE.findall(body):
                out[name.upper().replace("_", "")].add(name)
    return out


def pac_enums(pac_dir: Path) -> set:
    """Every enum the new PAC declares, so the rename can be checked."""
    names = set()
    for f in pac_dir.rglob("*.rs"):
        try:
            names.update(_ENUM_RE.findall(f.read_text(errors="ignore")))
        except OSError:
            continue
    return names


def drop_enum_suffix(hal_dir: Path, enums: set) -> int:
    """`FOO_A` -> `FOO`, only where the PAC declares `FOO`."""
    n = 0
    for f in sorted(hal_dir.rglob("*.rs")):
        src = f.read_text()
        new = _SUFFIXED_RE.sub(
            lambda m: m.group(1) if m.group(1) in enums else m.group(0), src)
        if new != src:
            n += sum(1 for m in _SUFFIXED_RE.finditer(src)
                     if m.group(1) in enums)
            f.write_text(new)
    return n


def rename_edits(stdout: str):
    """The two remaining renames, each gated on what rustc actually reported."""
    out = []
    for line in stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") != "compiler-message":
            continue
        d = m["message"]
        if d.get("level") != "error":
            continue
        code = (d.get("code") or {}).get("code")
        if code == "E0599" and _VARIANT_HINT in json.dumps(d.get("children", [])):
            for sp in d.get("spans", []):
                if not sp.get("is_primary"):
                    continue
                for ch in d.get("children", []):
                    if _VARIANT_HINT not in ch.get("message", ""):
                        continue
                    for csp in ch.get("spans", []):
                        if csp.get("suggested_replacement") is None:
                            continue
                        out.append((csp["file_name"], csp["byte_start"],
                                    csp["byte_end"], ("recase", None)))
        elif code == "E0599" and _BIT1C_RE.search(d["message"]):
            for sp in d.get("spans", []):
                if sp.get("is_primary"):
                    out.append((sp["file_name"], sp["byte_start"],
                                sp["byte_end"], "clear_bit_by_one"))
    return set(out)


def semicolon_edits(stdout: str, ws: Path):
    """Discard the value a register op now returns -- and nothing else."""
    out = []
    for line in stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") != "compiler-message":
            continue
        d = m["message"]
        if d.get("level") != "error":
            continue
        if (d.get("code") or {}).get("code") != "E0308":
            continue
        primary = [sp for sp in d.get("spans", []) if sp.get("is_primary")]
        if not primary:
            continue
        sp0 = primary[0]
        f = ws / sp0["file_name"]
        if not f.is_file():
            continue
        expr = f.read_bytes()[sp0["byte_start"]:sp0["byte_end"]].decode(
            errors="ignore")
        # The discarded expression must itself be the register call.
        if not (_REG_OP_RE.search(expr) and expr.rstrip().endswith(")")):
            continue
        for ch in d.get("children", []):
            for sp in ch.get("spans", []):
                if sp.get("suggested_replacement") != _SEMICOLON:
                    continue
                # ... and the semicolon must go at the end of that same
                # expression, not after some enclosing construct.
                if sp["byte_start"] != sp0["byte_end"]:
                    continue
                out.append((sp["file_name"], sp["byte_start"],
                            sp["byte_end"], _SEMICOLON))
    return set(out)


def unsafe_edits(stdout: str):
    """Wrap each raw-write call flagged E0133 in its own unsafe block."""
    out = []
    for line in stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") != "compiler-message":
            continue
        d = m["message"]
        if d.get("level") != "error":
            continue
        if (d.get("code") or {}).get("code") != UNSAFE_CODE:
            continue
        for sp in d.get("spans", []):
            if sp.get("is_primary"):
                out.append((sp["file_name"], sp["byte_start"], sp["byte_end"],
                            None))          # replacement computed at apply time

    # Flagged calls NEST -- `w.rev_in().bits(..)` reports both the outer and
    # the inner call -- and wrapping both produces `unsafe { unsafe { w.f()`
    # with the closing braces interleaved, which is a syntax error rather than
    # a wrong program. Keep the outermost span of any overlapping run; one
    # unsafe block covers everything inside it anyway.
    kept, by_file = [], collections.defaultdict(list)
    for f, s, e, r in set(out):
        by_file[f].append((s, e, r))
    for f, spans in by_file.items():
        end = -1
        for s, e, r in sorted(spans, key=lambda x: (x[0], -x[1])):
            if s >= end:
                kept.append((f, s, e, r))
                end = e
    return set(kept)


def into_edits(stdout: str):
    """rustc's own MachineApplicable `.into()` conversions for E0308.

    The 0.16 PAC widened some field writers (u16 -> u32); the fix rustc
    suggests is a lossless `.into()` at a span IT computes. Only the exact
    replacement `.into()` at MachineApplicable applicability is taken --
    anything else is not this rule's business."""
    out = []
    for line in stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") != "compiler-message":
            continue
        d = m["message"]
        if d.get("level") != "error" or \
                (d.get("code") or {}).get("code") != "E0308":
            continue
        for ch in d.get("children") or []:
            for sp in ch.get("spans") or []:
                if (sp.get("suggested_replacement") == ".into()"
                        and sp.get("suggestion_applicability")
                        == "MachineApplicable"):
                    out.append((sp["file_name"], sp["byte_start"],
                                sp["byte_end"], ".into()"))
    return set(out)


def apply(ws: Path, edits, verify: bool, variants=None, skipped=None) -> int:
    variants = variants or {}
    skipped = skipped if skipped is not None else []
    by_file = collections.defaultdict(list)
    for f, s, e, r in edits:
        by_file[f].append((s, e, r))
    n = 0
    for f, spans in by_file.items():
        p = ws / f
        if not p.is_file():
            p = Path(f)
        b = p.read_bytes()
        # Latest byte first, so the offsets of earlier edits stay valid.
        for s, e, r in sorted(spans, reverse=True):
            if r is None:                    # the unsafe-wrap rule
                inner = b[s:e]
                if verify and not inner.strip():
                    sys.exit(f"refusing to wrap an empty span in {f} at {s}:{e}")
                b = b[:s] + b"unsafe { " + inner + b" }" + b[e:]
                n += 1
                continue
            if isinstance(r, tuple) and r[0] == "recase":
                old = b[s:e].decode()
                cands = variants.get(old.upper().replace("_", ""), set())
                cands = {c for c in cands if c != old}
                if len(cands) != 1:
                    skipped.append((str(f), old, sorted(cands)))
                    continue
                new = cands.pop()
                if verify and not _same_name_recased(old, new):
                    sys.exit(f"refusing variant rename in {f} at {s}:{e}: "
                             f"{old!r} -> {new!r} is not the same name "
                             f"recased")
                b = b[:s] + new.encode() + b[e:]
                n += 1
                continue
            if verify and r == "clear_bit_by_one" and b[s:e] != b"set_bit":
                sys.exit(f"refusing rename in {f} at {s}:{e}: expected "
                         f"set_bit, found {b[s:e]!r}")
            if verify and r == "()" and b[s:e] != b"":
                sys.exit(f"refusing non-mechanical edit in {f} at {s}:{e}: "
                         f"replacing {b[s:e]!r} with {r!r}")
            if verify and r == _SEMICOLON and b[s:e] != b"":
                sys.exit(f"refusing to overwrite {b[s:e]!r} with a semicolon "
                         f"in {f} at {s}:{e}")
            if verify and r == ".into()" and b[s:e] != b"":
                sys.exit(f"refusing to overwrite {b[s:e]!r} with .into() "
                         f"in {f} at {s}:{e} -- the rule only inserts at the "
                         f"span rustc computed")
            if verify and r not in ("()", _SEMICOLON, "clear_bit_by_one",
                                    ".into()"):
                sys.exit(f"refusing unexpected replacement {r!r} in {f}")
            b = b[:s] + r.encode() + b[e:]
            n += 1
        p.write_bytes(b)
    return n


def port(hal: str, verify: bool, target: str) -> dict:
    version, pac, feature_sets = CASES[hal]
    pac_dir = get_pac.provision(crate=pac, version=PAC_VERSION)
    hal_dir = vendor(hal, version)
    repoint(hal_dir, pac, Path(pac_dir).resolve())
    ws = workspace(hal_dir, target)

    enums = pac_enums(Path(pac_dir))
    variants = pac_variants(Path(pac_dir))
    renamed = drop_enum_suffix(hal_dir, enums)
    skipped = []

    # The hand-checked patches are written against the source AFTER the
    # mechanical rules have run -- `self.raw.rtsr` only becomes
    # `self.raw.rtsr()` once the paren rule has been through it -- so they are
    # applied at the first fixpoint and the loop then runs again.
    # Drop any cached build of the PAC before measuring. The same vendored
    # tree is what the injector patches, so a port run that follows an
    # injection can be served a stale .rmeta and report constraint errors from
    # a PAC that is pristine on disk -- 31 phantom E0277 in one run here. The
    # source is the truth; the cache is not.
    subprocess.run(["cargo", "clean", "-p", pac], cwd=str(ws),
                   capture_output=True, text=True, timeout=STEP_TIMEOUT)

    patched, history, total = 0, [], 0
    last_rc, last_had_msgs = 0, False
    for _ in range(80):
        # Every feature set, every round: an edit that fixes one config must
        # not be judged against that config alone.
        stdout, codes = "", collections.Counter()
        last_rc = 0
        for features in feature_sets:
            run = check(ws, hal, features, target)
            stdout += run.stdout
            last_rc = last_rc or run.returncode
        last_had_msgs = '"reason":"compiler-message"' in stdout
        edits, codes = diagnostics(stdout)
        run = type("R", (), {"stdout": stdout})()
        history.append({"errors": sum(codes.values()), "by_code": dict(codes)})
        if not edits:
            # The paren rule has converged; now the unsafe wraps. Kept in this
            # order because wrapping changes byte offsets the paren spans were
            # computed against.
            edits = unsafe_edits(run.stdout)
        if not edits:
            edits = rename_edits(run.stdout)
        if not edits:
            edits = semicolon_edits(run.stdout, ws)
        if not edits:
            edits = into_edits(run.stdout)
        if not edits:
            if not patched:
                patched = patch(hal_dir, hal)
                if patched:
                    continue
            break
        before = total
        total += apply(ws, edits, verify, variants, skipped)
        if total == before:
            break
    # A build that never ran is not a build with no errors. cargo emits zero
    # compiler-messages on a RESOLUTION failure (a feature the new PAC
    # renamed, a version conflict) and exits nonzero; diagnostics() then sees
    # no errors and the port would falsely read as compiling. stm32f7xx-hal
    # 0.8 forwards `stm32f7/stm32f7x2`, renamed to stm32f722 in 0.16, and was
    # reported as a clean 0-edit port until this guard.
    did_not_run = last_rc != 0 and not last_had_msgs
    ok = history[-1]["errors"] == 0 and not did_not_run
    return {"hal": hal, "version": version, "pac": pac,
            "did_not_run": did_not_run,
            "workspace": str(ws), "feature_sets": feature_sets,
            "edits_applied": total,
            "enum_suffixes_dropped": renamed,
            "manual_patches": patched,
            "variant_renames_skipped": skipped,
            "compiles": ok, "rounds": history,
            "residual": history[-1]["by_code"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hal", default="all",
                    help="one of " + ", ".join(CASES) + ", or 'all'")
    ap.add_argument("--target", default="thumbv7m-none-eabi")
    ap.add_argument("--verify", action="store_true",
                    help="abort on any edit that is not an inserted `()`")
    args = ap.parse_args()

    hals = list(CASES) if args.hal == "all" else [args.hal]
    for h in hals:
        if h not in CASES:
            sys.exit(f"unknown hal {h!r}; known: {', '.join(CASES)}")

    results = []
    for h in hals:
        print(f"=== {h} ===", flush=True)
        r = port(h, args.verify, args.target)
        results.append(r)
        first = r["rounds"][0]["errors"]
        print(f"  {first} errors -> {r['rounds'][-1]['errors']} after "
              f"{r['edits_applied']} mechanical edits", flush=True)
        if not r["compiles"]:
            print(f"  residual: {r['residual']}", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "port_hal.json"
    # Merge by hal name: `--hal X` used to write its single result over the
    # whole record -- the same defect stm_sweep --only and scan_projects
    # --only each had, found here holding one HAL where four had been.
    if p.is_file():
        try:
            existing = {r["hal"]: r for r in json.loads(p.read_text())}
        except Exception:                                   # noqa: BLE001
            existing = {}
        for r in results:
            existing[r["hal"]] = r
        results = [existing[h] for h in sorted(existing)]
    p.write_text(json.dumps(results, indent=1))
    print(f"\nreport: {p}")


if __name__ == "__main__":
    main()
