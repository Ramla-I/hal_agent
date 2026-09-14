#!/usr/bin/env python3
"""Build hal_probe and say what the errors mean -- after proving the patch took.

`cargo check` alone is not enough here. Cargo does NOT fail when a
`[patch.crates-io]` cannot be applied: it prints a warning and resolves the
registry crate, so a probe pointed at the wrong crate name or an unsatisfiable
version compiles cleanly against the PRISTINE PAC and looks like "zero
violations". This refuses to report anything until Cargo.lock proves the local
path won.

Usage:
    python applications/pac_codegen/experiments/hal_probe/check.py
    python .../check.py --errors        # dump every diagnostic, unclassified
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def patched_crate() -> str:
    m = re.search(r'^\[patch\.crates-io\]\s*\n\s*([\w-]+)\s*=',
                  (HERE / "Cargo.toml").read_text(), re.M)
    return m.group(1) if m else ""


def patch_applied(pac: str) -> bool:
    """A path dependency has no `source` key in Cargo.lock; a registry one does."""
    lock = HERE / "Cargo.lock"
    if not lock.is_file():
        return False
    block, in_pac = [], False
    for line in lock.read_text().splitlines():
        if line.strip() == "[[package]]":
            if in_pac:
                return not any(l.startswith("source = ") for l in block)
            block, in_pac = [], False
        else:
            block.append(line)
            if line.strip() == f'name = "{pac}"':
                in_pac = True
    return in_pac and not any(l.startswith("source = ") for l in block)


def diagnostics():
    r = subprocess.run(["cargo", "check", "--message-format=json"],
                       cwd=HERE, capture_output=True, text=True)
    out = []
    for line in r.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") == "compiler-message" and \
                m["message"].get("level") == "error":
            out.append(m["message"])
    return out, r


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--errors", action="store_true",
                    help="print every diagnostic verbatim")
    a = ap.parse_args()

    pac = patched_crate()
    if not pac:
        sys.exit("Cargo.toml has no [patch.crates-io] entry")
    errs, run = diagnostics()

    if not patch_applied(pac):
        sys.exit(
            f"\n!! the [patch.crates-io] for `{pac}` did NOT apply.\n"
            f"   Cargo resolved the registry crate instead, so this build says\n"
            f"   nothing about your injected PAC. Usual causes:\n"
            f"     - the crate name does not match what the HAL depends on\n"
            f"     - the path does not point at a crate directory\n"
            f"     - the HAL's version requirement excludes the patched version\n"
            f"   Check with: grep -A3 'name = \"{pac}\"' Cargo.lock\n")

    # Our gates are E0277 on the marker traits; the message carries the
    # datasheet sentence, which is what makes a hit self-explaining.
    #
    # But not every one of our diagnostics is a violation. A driver written
    # GENERICALLY over register blocks names the register through an
    # associated-type projection -- `<<ADC as Ptr>::RB as AdcRB>::CR2rs` --
    # and such a definition needs the marker bounds even when nothing on this
    # device is gated. Counting those as findings would inflate the result
    # with the encoding's adoption cost. Same split stm_sweep.classify makes.
    ours = [e for e in errs
            if (e.get("code") or {}).get("code") == "E0277"
            and "constrained by its datasheet" in e.get("message", "")]
    hits = [e for e in ours if "<<" not in e["message"].split("`")[1]]
    friction = [e for e in ours if e not in hits]
    other = [e for e in errs if e not in ours]

    print(f"patch applied: {pac} <- local path   OK")
    print(f"errors {len(errs)}   violations {len(hits)}   "
          f"generic friction {len(friction)}   other {len(other)}")

    def sites(group):
        out = {}
        for e in group:
            for s in e.get("spans", []):
                if s.get("is_primary"):
                    out.setdefault(s["file_name"].split("/src/")[-1],
                                   []).append(s["line_start"])
        return out

    if hits:
        print("\n  VIOLATIONS -- the driver touches a gated register here:")
        for e in hits[:1]:
            pass
        regs = {}
        for e in hits:
            regs[e["message"].split("`")[1]] = regs.get(
                e["message"].split("`")[1], 0) + 1
        for r, n in sorted(regs.items(), key=lambda x: -x[1]):
            print(f"    {n:>3}x {r}")
        for f, lines in sorted(sites(hits).items()):
            print(f"      {f}: lines {sorted(lines)}")
        print("\n    Each is a CANDIDATE, not a proven bug: the driver may "
              "establish the\n    precondition a few lines up. "
              "experiments/corroboration.py triages that.")
    if friction:
        print(f"\n  GENERIC FRICTION -- {len(friction)} error(s) in code "
              f"generic over register")
        print("  blocks, naming no concrete gated register. This is the "
              "encoding's adoption")
        print("  cost, not a finding: mechanical `where` bounds fix it.")
        for f, lines in sorted(sites(friction).items()):
            print(f"      {f}: lines {sorted(lines)}")
    if other:
        print(f"\n  OTHER -- {len(other)} error(s) that are not ours. "
              f"Re-run with --errors.")

    if a.errors:
        for e in errs:
            print("\n---", (e.get('code') or {}).get('code', ''),
                  e.get("message", "")[:400])
    if not errs:
        print("\n  clean build: this driver never touches a constrained "
              "register on this device.")


if __name__ == "__main__":
    main()
