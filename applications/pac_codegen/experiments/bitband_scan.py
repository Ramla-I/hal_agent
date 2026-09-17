#!/usr/bin/env python3
"""bitband_scan.py -- register writes that walk around the type system.

WHAT THIS IS FOR
----------------
Our enforcement is a trait bound. Gating a register means withholding a marker
so the access method stops compiling::

    pub fn write<F>(&self, f: F) -> REG::Ux
    where
        REG: UnconstrainedWrite,        // <- the gate

Every violation the sweep reports is the compiler refusing that bound, which
means the mechanism sees exactly the accesses that go THROUGH `Reg`'s methods.

Bit banding does not. ARM maps each peripheral bit to its own word address, so
a driver can set one bit atomically by writing the alias -- and the helper
takes the register as a RAW POINTER::

    pub unsafe fn set<T>(register: *const T, bit: u8) { .. }
    bb::set(rcc.bdcr(), 0);          // RCC_BDCR bit 0 = LSEON

`rcc.bdcr()` yields `&BDCR`, which coerces to `*const BDCR`. Taking a reference
to a register is not gated -- only the read/write/modify methods are -- so this
is a write to a constrained field that the gate structurally cannot see.

It is not hypothetical. stm32f4xx-hal 0.23 writes RCC_BDCR this way at four
sites in rtc.rs, hitting LSEON, LSEBYP and RTCEN; RM0368, RM0383, RM0390 and
RM0401 all constrain exactly those fields on `PWR_CR.DBP set`. Sixteen
(manual x site) accesses the sweep cannot report.

So the sweep's hit counts are a LOWER BOUND, and this script says by how much.
It does not replace the compiler -- it finds what the compiler was never given
the chance to check.

WHAT IT CAN AND CANNOT RESOLVE
------------------------------
Three shapes occur, and conflating them would be the whole bug again:

  RESOLVED        `bb::set(rcc.bdcr(), 0)` -- receiver names the peripheral,
                  the bit is a literal, so the field is known exactly. These
                  are reportable candidates.
  BIT DYNAMIC     `bb::write(tim.ccer(), c*4 + 1, ..)` -- the register is known
                  but the bit is computed, so the field is one of several. The
                  register's constrained fields are listed rather than guessed.
  OPAQUE          `bb::set(Self::Bus::enr(rcc), $bit)` -- macro-generated;
                  neither register nor bit survives. Counted and shown, never
                  silently dropped: this is how every peripheral enable in
                  stm32f4xx-hal's RCC is written.

Field offsets come from the PAC's own generated reader accessors, so the
bit-to-field map is the chip's, not a guess::

    LSEON_R::new((self.bits & 1) != 0)                  -> offset 0,  width 1
    RTCSEL_R::new(((self.bits >> 8) & 3) as u8)         -> offset 8,  width 2

Usage:
    python applications/pac_codegen/experiments/bitband_scan.py \\
        --device stm32f401 --constraints out/constraints/rm0368_stm32f401.json \\
        --src ~/.cargo/registry/src/*/stm32f4xx-hal-0.23.0/src --label stm32f4xx-hal
"""

import argparse
import json
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
import rust_codegen                                   # noqa: E402

OUT = APP_DIR / "experiments" / "out"

# `bb::set(rcc.bdcr(), 0)` / `bb::write(tim.ccer(), c*4 + 1, b)`.
# The receiver is captured because it is the only thing naming the peripheral;
# the bit argument is captured raw so a computed one can be reported as such
# rather than parsed into a wrong answer.
_BB_RE = re.compile(
    r"\bbb::(?P<op>set|clear|write)\(\s*(?P<target>[^,]+?)\s*,\s*"
    r"(?P<bit>[^,)]+?)\s*[,)]")
# `rcc.bdcr()` or `rcc.bdcr` -- receiver and register.
_TARGET_RE = re.compile(r"^&?(?P<recv>[A-Za-z_]\w*)\.(?P<reg>[a-z0-9_]+)\(?\)?$")
# The generated reader accessor carries the shift and mask.
# The generated reader accessor carries the shift and mask. The `\)?` before
# the mask is load-bearing: a field at offset 0 reads `(self.bits & 1)` while
# every other field reads `((self.bits >> 2) & 1)`, with a closing paren
# between the shift and the mask. Without it the map contained ONLY offset-0
# fields, so this scanner found LSEON and silently missed LSEBYP, RTCEN and
# BDRST -- three of the four sites it exists to find.
_FIELD_RE = re.compile(
    r"pub fn (?P<name>[a-z0-9_]+)\(&self\)[^{]*\{\s*"
    r"\w+_R::new\(\(*self\.bits(?:\s*>>\s*(?P<shift>\d+))?"
    r"\s*\)?\s*&\s*(?P<mask>\d+)")


def field_map(device_dir: Path) -> dict:
    """(module, register) -> {field: (offset, width)}, read from the PAC."""
    out = {}
    for reg_file in sorted(device_dir.rglob("*.rs")):
        rel = reg_file.relative_to(device_dir)
        if len(rel.parts) != 2:            # <peripheral>/<register>.rs
            continue
        module, reg = rel.parts[0], rel.parts[1][:-3]
        try:
            text = reg_file.read_text(errors="replace")
        except OSError:
            continue
        fields = {}
        for m in _FIELD_RE.finditer(text):
            shift = int(m.group("shift") or 0)
            mask = int(m.group("mask"))
            fields[m.group("name")] = (shift, mask.bit_length())
        if fields:
            out[(module, reg)] = fields
    return out


def constrained_fields(path: Path) -> dict:
    """(peripheral, register) -> {field: [preconditions]} for gated FIELDS."""
    if not path or not path.is_file():
        return {}
    data = json.loads(path.read_text())
    entries = data.get("registers", data) if isinstance(data, dict) else data
    out = {}
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        key = ((e.get("peripheral") or "").lower(),
               (e.get("register") or "").lower())
        fields = {f.lower(): (g.get("preconditions") or [])
                  for f, g in (e.get("gated_fields") or {}).items()}
        # A whole-register gate constrains every field in it.
        if e.get("gated_operations"):
            fields["*"] = [p for v in (e.get("preconditions") or {}).values()
                           for p in v]
        if fields:
            out[key] = fields
    return out


def field_at(fields: dict, bit: int) -> str:
    for name, (offset, width) in fields.items():
        if offset <= bit < offset + width:
            return name
    return ""


def scan(src_dirs, fmap, cmap, aliases) -> list:
    rows = []
    for root in src_dirs:
        root = Path(root)
        for f in sorted(root.rglob("*.rs")):
            try:
                lines = f.read_text(errors="replace").splitlines()
            except OSError:
                continue
            rel = str(f.relative_to(root))
            for i, text in enumerate(lines):
                s = text.strip()
                if s.startswith("//"):
                    continue
                for m in _BB_RE.finditer(text):
                    rows.append(classify(rel, i + 1, s, m, fmap, cmap, aliases))
    return rows


def classify(rel, line, src, m, fmap, cmap, aliases) -> dict:
    row = {"file": rel, "line": line, "op": m.group("op"),
           "target": m.group("target").strip(), "bit_expr": m.group("bit").strip(),
           "source": src[:150]}
    t = _TARGET_RE.match(row["target"])
    if not t:
        # Macro-generated or otherwise not a `recv.reg()` -- the register does
        # not survive, so neither does any judgement about it.
        row.update(state="opaque", peripheral="", register="", field="",
                   constrained=False)
        return row
    recv, reg = t.group("recv").lower(), t.group("reg").lower()
    module = aliases.get(recv, recv)
    fields = fmap.get((module, reg)) or {}
    row.update(peripheral=recv, register=reg)
    if not fields:
        row.update(state="unknown-register", field="", constrained=False)
        return row
    # The constraint is recorded against the INSTANCE the manual names, which
    # may not be the module the types live in, so try both.
    cons = cmap.get((recv, reg)) or cmap.get((module, reg)) or {}
    if not re.fullmatch(r"\d+", row["bit_expr"]):
        # The register is known, the bit is computed. Say which of its fields
        # are constrained instead of picking one.
        row.update(state="bit-dynamic", field="",
                   constrained=bool(cons),
                   candidate_fields=sorted(f for f in cons if f != "*"))
        return row
    name = field_at(fields, int(row["bit_expr"]))
    row.update(state="resolved", field=name,
               constrained=bool(cons) and (name in cons or "*" in cons),
               preconditions=cons.get(name) or cons.get("*") or [])
    return row


# The (driver, family) pairings the corpus mode scans: every locally available
# sweep consumer that uses bit banding at all. Explicit, so a driver that
# starts using `bb::` without being added here is a gap in THIS list, not a
# silent zero -- the corpus run prints what it scanned.
CORPUS_DRIVERS = [
    ("stm32f4xx-hal-0.23.0", "stm32f4"),
    ("stm32f1xx-hal-0.11.0", "stm32f1"),
    ("stm32f1-hal-0.14.1", "stm32f1"),
    ("stm32g4xx-hal-0.1.0", "stm32g4"),
]
_REGISTRY = Path.home() / ".cargo" / "registry" / "src"


def run_corpus(out_path: Path) -> None:
    """One merged record over every (driver, manual) pairing: the artifact's
    input. Results used to live only in a session scratchpad, which meant the
    published section could not be regenerated from the repo."""
    results = []
    cdir = OUT / "constraints"
    for drv, family in CORPUS_DRIVERS:
        srcs = sorted(_REGISTRY.glob(f"*/{drv}/src"))
        if not srcs:
            print(f"!! {drv}: not in the local cargo registry, skipped")
            continue
        pac = APP_DIR / "vendored" / "pac" / family
        for cpath in sorted(cdir.glob("*.json")):
            device = cpath.stem.split("_", 1)[1]
            device_dir = pac / "src" / device
            if not device_dir.is_dir():
                continue
            fmap = field_map(device_dir)
            aliases = rust_codegen.peripheral_instance_map(device_dir)
            cmap = constrained_fields(cpath)
            rows = scan([srcs[0]], fmap, cmap, aliases)
            by_state = {}
            for r in rows:
                by_state[r["state"]] = by_state.get(r["state"], 0) + 1
            hits = [r for r in rows if r.get("constrained")]
            results.append({
                "driver": drv, "pairing": cpath.stem,
                "sites": len(rows), "by_state": by_state,
                "constrained_hits": len(hits),
                # Only the hits carry full rows; the artifact renders them.
                "hits": hits,
            })
            print(f"  {drv:26s} {cpath.stem:22s} sites={len(rows):<3d} "
                  f"invisible-hits={len(hits)}")
    out_path.write_text(json.dumps(
        {"drivers": CORPUS_DRIVERS, "pairings": results}, indent=1) + "\n")
    print(f"json: {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", action="store_true",
                    help="scan every known bb-using driver against every "
                         "manual of its family; writes out/bitband_scan.json")
    ap.add_argument("--pac", default=None,
                    help="vendored PAC dir (default: the stm32 family of --device)")
    ap.add_argument("--device", default=None)
    ap.add_argument("--constraints", default=None,
                    help="out/constraints/<rm>_<device>.json")
    ap.add_argument("--src", action="append", default=[],
                    help="source tree to scan (repeatable)")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.corpus:
        run_corpus(Path(args.out) if args.out else OUT / "bitband_scan.json")
        return
    if not args.device or not args.src:
        ap.error("--device and --src are required (or use --corpus)")

    pac = Path(args.pac) if args.pac else None
    if pac is None:
        fam = re.match(r"(stm32[a-z]\d|stm32[a-z]{2}|stm32\w\d)", args.device)
        guess = APP_DIR / "vendored" / "pac" / (fam.group(1) if fam else "")
        pac = guess
    device_dir = pac / "src" / args.device
    if not device_dir.is_dir():
        sys.exit(f"device module not found: {device_dir}")

    fmap = field_map(device_dir)
    aliases = rust_codegen.peripheral_instance_map(device_dir)
    cmap = constrained_fields(Path(args.constraints) if args.constraints else None)
    rows = scan(args.src, fmap, cmap, aliases)

    by_state = {}
    for r in rows:
        by_state.setdefault(r["state"], []).append(r)
    hits = [r for r in rows if r.get("constrained")]

    print(f"{args.label or args.device}: {len(rows)} bit-band sites "
          f"across {len(args.src)} tree(s)")
    for st in ("resolved", "bit-dynamic", "unknown-register", "opaque"):
        if st in by_state:
            print(f"  {st:16s} {len(by_state[st]):4d}")
    print(f"\n  WRITES TO A CONSTRAINED FIELD, invisible to the gate: {len(hits)}")
    for r in hits:
        what = (r["field"].upper() if r["field"]
                else "/".join(x.upper() for x in r.get("candidate_fields", [])))
        pre = ", ".join(r.get("preconditions") or []) or "see the register's rule"
        print(f"    {r['file']}:{r['line']}  bb::{r['op']}("
              f"{r['peripheral']}.{r['register']}(), {r['bit_expr']}) -> "
              f"{what}   requires {pre}")
    if by_state.get("opaque"):
        print(f"\n  OPAQUE ({len(by_state['opaque'])}) -- macro-generated, the "
              f"register does not survive; counted, not judged:")
        for r in by_state["opaque"][:5]:
            print(f"    {r['file']}:{r['line']}  {r['source'][:96]}")

    p = Path(args.out) if args.out else OUT / "bitband_scan.json"
    p.write_text(json.dumps(
        {"label": args.label, "device": args.device,
         "constraints": args.constraints, "src": args.src,
         "sites": len(rows), "by_state": {k: len(v) for k, v in by_state.items()},
         "constrained_hits": len(hits), "rows": rows}, indent=1) + "\n")
    print(f"\njson: {p}")


if __name__ == "__main__":
    main()
