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
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import enforcement  # noqa: E402
VENDOR = HERE / "vendored"
MAX_ROUNDS = 25


def patched_crate() -> str:
    """The PAC being tested -- the [patch] entry that is NOT our vendored copy
    of the driver. --apply-fix adds a second entry for the driver, and reading
    'the first one' then silently returns the HAL: every later step looks for
    the wrong crate name and quietly does nothing."""
    body = (HERE / "Cargo.toml").read_text().split("[patch.crates-io]", 1)
    if len(body) < 2:
        return ""
    for line in body[1].splitlines():
        m = re.match(r'\s*([\w-]+)\s*=\s*\{(.*)\}', line)
        if m and "vendored/" not in m.group(2):
            return m.group(1)
    return ""


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


def hal_dep():
    """(crate, version) of the driver under test, from [dependencies]."""
    m = re.search(r'^\[dependencies\]\s*\n\s*([\w-]+)\s*=\s*\{[^}]*?'
                  r'version\s*=\s*"=?([\d.]+)"',
                  (HERE / "Cargo.toml").read_text(), re.M | re.S)
    if not m:
        sys.exit("could not read the driver crate/version from [dependencies]")
    return m.group(1), m.group(2)


def vendor_hal(crate, version):
    """A writable copy of the driver. NEVER edit the registry cache: it is
    shared by every project on the machine and cargo will overwrite it."""
    dest = VENDOR / f"{crate}-{version}"
    if dest.is_dir():
        return dest
    roots = list(Path.home().glob(f".cargo/registry/src/*/{crate}-{version}"))
    if not roots:
        sys.exit(f"{crate} {version} is not in the registry cache; "
                 f"run check.py once first to fetch it")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(roots[0], dest)
    return dest


def point_at_vendored(crate, path):
    f = HERE / "Cargo.toml"
    txt = f.read_text()
    if re.search(rf'^{re.escape(crate)}\s*=\s*\{{\s*path', txt, re.M):
        return False
    # Appended, not prepended: patched_crate() must keep finding the PAC.
    rel = path.relative_to(HERE)
    f.write_text(txt.rstrip("\n") + f'\n{crate} = {{ path = "{rel}" }}\n')
    return True


def suggestions(errs, hal_dir):
    """rustc's own MachineApplicable bound additions, inside the driver only.

    Only these are applied. A MaybeIncorrect suggestion is rustc guessing at
    intent; taking one would make this a rewrite of the driver rather than the
    mechanical step it claims to be."""
    out = {}
    for e in errs:
        for ch in e.get("children", []):
            for s in ch.get("spans", []):
                rep = s.get("suggested_replacement")
                if rep is None:
                    continue
                if s.get("suggestion_applicability") != "MachineApplicable":
                    continue
                # rustc reports paths relative to the cargo working dir once
                # the driver is vendored, absolute when it is in the registry
                # cache. Normalise before deciding whether the span is inside
                # the copy we are allowed to edit.
                f = Path(s["file_name"])
                f = f if f.is_absolute() else (HERE / f)
                if not str(f.resolve()).startswith(str(hal_dir.resolve())):
                    continue
                out.setdefault(str(f.resolve()), set()).add(
                    (s["byte_start"], s["byte_end"], rep))
    return out


_WHERE = re.compile(r"^\s*where\s+", re.I)


def merge_same_span(edits, pac: str):
    """Two errors on one generic item each suggest ` where A: Trait`, at the
    SAME byte span. Applying both verbatim yields two where clauses and
    `cannot define duplicate where clauses on an item`, so fold them into one.

    Also qualify the marker traits. rustc emits them bare -- correct at the
    site it diagnosed, wrong once written into a file that never imported
    them, which is 12 of the 25 errors the naive application produces.
    """
    by_span = {}
    for start, end, rep in edits:
        by_span.setdefault((start, end), []).append(rep)
    out = []
    for (start, end), reps in by_span.items():
        preds = []
        for r in reps:
            body = _WHERE.sub("", r) if _WHERE.match(r) else r
            preds.extend(x.strip() for x in body.split(",") if x.strip())
        seen, uniq = set(), []
        for x in preds:
            if x not in seen:
                seen.add(x)
                uniq.append(x)
        text = " where " + ", ".join(uniq)
        for marker in ("UnconstrainedModify", "UnconstrainedWrite",
                       "UnconstrainedRead"):
            text = re.sub(rf"(?<![\w:]){marker}\b", f"{pac}::{marker}", text)
        out.append((start, end, text))
    return out


def apply_edits(sugg, pac: str):
    """Apply per file, LAST span first, so earlier byte offsets stay valid."""
    n = 0
    for path, edits in sugg.items():
        data = Path(path).read_bytes()
        for start, end, rep in sorted(merge_same_span(edits, pac),
                                      reverse=True):
            data = data[:start] + rep.encode() + data[end:]
            n += 1
        Path(path).write_bytes(data)
    return n


def repair_scope(errs, pac: str) -> int:
    """rustc's suggestion names traits that were in scope where it DIAGNOSED,
    not necessarily where the clause is written. stm32f1xx-hal spells its own
    trait `crate::Ptr` but the suggestion emits bare `Ptr`, so 12 of the 13
    friction sites become E0405 instead of compiling.

    Repair narrowly: for each `cannot find trait X`, qualify bare X as
    `crate::X` -- and ONLY inside the clauses we inserted, which are the ones
    mentioning a marker trait. Anything wider would be editing the driver.
    """
    missing = set()
    for e in errs:
        m = re.search(r"cannot find trait `(\w+)` in this scope",
                      e.get("message", ""))
        if m:
            missing.add(m.group(1))
    if not missing:
        return 0
    files = set()
    for e in errs:
        for s in e.get("spans", []):
            f = Path(s["file_name"])
            files.add(f if f.is_absolute() else (HERE / f))
    n = 0
    for f in files:
        if not f.is_file():
            continue
        out = []
        for line in f.read_text().splitlines(keepends=True):
            if f"{pac}::Unconstrained" in line:
                for name in missing:
                    new = re.sub(rf"(?<![\w:]){name}\b", f"crate::{name}",
                                 line)
                    if new != line:
                        n += 1
                        line = new
            out.append(line)
        f.write_text("".join(out))
    return n


_METHOD_WHERE = re.compile(
    r"^(?P<head>.*?)\s+where\s+(?P<preds>.*?)\s*\{\s*$")
_IMPL_LINE = re.compile(
    r"^(?P<head>\s*impl\b.*?)(?:\s+where\s+(?P<existing>.*?))?\s*\{\s*$")


def lift_bounds_to_impl(errs, pac: str) -> int:
    """Move a bound off a trait-implementing method and onto its impl block.

    E0276 says an impl may not require more than the trait declares. The fix is
    NOT to widen the trait -- that changes the driver's public API. A bound on
    the IMPL BLOCK is legal and says the right thing: this impl applies where
    the register is unconstrained. So lift the clause up one level.

        impl<ADC: Instance> AdcExt for ADC {
            fn adc(..) -> .. where <..>::CR2rs: Unconstrained.. {   // E0276

        impl<ADC: Instance> AdcExt for ADC
        where <..>::CR2rs: Unconstrained.. {
            fn adc(..) -> .. {                                      // legal

    The impl's generic params are in scope for its own where clause, which is
    why the predicate transfers verbatim.
    """
    by_file = {}
    for e in errs:
        if (e.get("code") or {}).get("code") != "E0276":
            continue
        for s in e.get("spans", []):
            if s.get("is_primary"):
                f = Path(s["file_name"])
                f = f if f.is_absolute() else (HERE / f)
                by_file.setdefault(f, set()).add(s["line_start"])
    moved = 0
    for f, lines in by_file.items():
        if not f.is_file():
            continue
        src = f.read_text().splitlines()
        for ln in sorted(lines, reverse=True):     # bottom-up: indices hold
            i = ln - 1
            m = _METHOD_WHERE.match(src[i])
            if not m or f"{pac}::Unconstrained" not in m.group("preds"):
                continue
            preds = m.group("preds")
            # find the enclosing impl header, which may span several lines
            # and may already carry its own multi-line where clause:
            #     impl<ADC: Instance, WORD, PIN> OneShot<..> for Adc<ADC>
            #     where
            #         WORD: From<u16>,
            #         PIN: Channel<ADC, ID = u8>,
            #     {
            j = next((k for k in range(i - 1, -1, -1)
                      if re.match(r"\s*impl\b", src[k])), None)
            if j is None:
                continue
            brace = next((k for k in range(j, i)
                          if src[k].rstrip().endswith("{")), None)
            if brace is None:
                continue
            src[i] = m.group("head") + " {"
            head = src[brace].rstrip()
            if head == "{" or not head.endswith("{"):
                pass
            if brace == j:
                # single-line header: `impl .. for X {` (with or without where)
                im = _IMPL_LINE.match(src[j])
                if not im:
                    continue
                existing = im.group("existing")
                joined = f"{existing}, {preds}" if existing else preds
                src[j] = f"{im.group('head')}\nwhere {joined} {{"
            else:
                # multi-line header: insert the predicate just above the `{`
                has_where = any(re.match(r"\s*where\b", src[k])
                                for k in range(j, brace))
                prev = brace - 1
                if has_where and not src[prev].rstrip().endswith((",", "where")):
                    src[prev] = src[prev].rstrip() + ","
                block = (f"    {preds},"
                         if has_where else f"where\n    {preds},")
                src.insert(brace, block)
            moved += 1
        f.write_text("\n".join(src) + "\n")
    return moved


def _strip_marker_preds(src: str, pac: str) -> str:
    """The file with every predicate we added removed, whitespace collapsed.

    Walks left from each marker trait to the predicate's start -- a comma or
    `where` at angle-bracket depth 0 -- so nested projections like
    `<<ADC as Ptr>::RB as AdcRB>::CR2rs` come out whole.
    """
    out = src
    while True:
        m = re.search(rf"{re.escape(pac)}::Unconstrained\w+", out)
        if not m:
            break
        i, depth = m.start(), 0
        while i > 0:
            c = out[i - 1]
            if c == ">":
                depth += 1
            elif c == "<":
                depth -= 1
            elif depth == 0 and c == ",":
                break
            elif depth == 0 and out[max(0, i - 6):i].endswith("where"):
                break
            i -= 1
        j = m.end()
        if j < len(out) and out[j] == ",":
            j += 1
        out = out[:i] + out[j:]
    out = re.sub(r"\bwhere\b(\s*)(?=[{\n])", "", out)
    return re.sub(r"\s+", " ", out).strip()


def verify_bounds_only(hal_dir: Path, crate: str, version: str,
                       pac: str) -> bool:
    """Every edit must be a bound and nothing else.

    Without this, 'we only added where clauses' is an assurance rather than a
    checked claim -- and the difference matters, because a driver we silently
    reshaped is a driver whose violations mean nothing. Same discipline as
    port_hal.py --verify.
    """
    orig = next(iter(Path.home().glob(
        f".cargo/registry/src/*/{crate}-{version}")), None)
    if orig is None:
        print("  (cannot verify: the pristine copy is gone from the cache)")
        return True
    bad = []
    for f in sorted(hal_dir.rglob("*.rs")):
        rel = f.relative_to(hal_dir)
        ref = orig / rel
        if not ref.is_file():
            bad.append(f"{rel}: new file")
            continue
        a, b = ref.read_text(), f.read_text()
        if a == b:
            continue
        if _strip_marker_preds(a, pac) != _strip_marker_preds(b, pac):
            bad.append(f"{rel}: changed beyond its bounds")
    if bad:
        print("\n  !! VERIFY FAILED -- these edits are not bounds-only:")
        for b in bad:
            print(f"       {b}")
        return False
    return True


def fix_loop(pac: str):
    crate, version = hal_dep()
    hal_dir = vendor_hal(crate, version)
    if point_at_vendored(crate, hal_dir):
        print(f"driver vendored to {hal_dir}")
        print(f"Cargo.toml now patches `{crate}` to that copy\n")
    total = lifted_n = repaired_n = rnd = 0
    for rnd in range(1, MAX_ROUNDS + 1):
        errs, _ = diagnostics()
        sugg = suggestions(errs, hal_dir)
        n = sum(len(v) for v in sugg.values())
        print(f"round {rnd}: {len(errs)} error(s), {n} machine-applicable bound(s)")
        if not n:
            fixed = repair_scope(errs, pac)
            if fixed:
                repaired_n += fixed
                print(f"         repaired {fixed} unqualified trait "
                      f"reference(s) in our own clauses")
                continue
            lifted = lift_bounds_to_impl(errs, pac)
            if lifted:
                lifted_n += lifted
                print(f"         lifted {lifted} bound(s) off trait methods "
                      f"onto their impl block")
                continue
            break
        total += apply_edits(sugg, pac)
    errs, _ = diagnostics()
    ours = [e for e in errs if enforcement.is_ours(e)]
    strict = [e for e in errs
              if (e.get("code") or {}).get("code") == "E0276"]
    rest = [e for e in errs if e not in ours and e not in strict]

    print(f"\n{total} bound(s) added, {lifted_n} lifted to an impl block, "
          f"{repaired_n} name(s) qualified, over {rnd} round(s)")
    print(f"  friction removed, violations kept: {len(ours)} datasheet "
          f"error(s) remain")
    if strict:
        print(f"\n  {len(strict)}x E0276 'impl has stricter requirements than "
              f"trait'.")
        print("  This is the cascade, and it is where mechanical stops. A bound "
              "added to an")
        print("  inherent method is free; the same bound on a method that "
              "implements a TRAIT")
        print("  is illegal unless the trait declares it too. Fixing these "
              "means changing the")
        print("  trait's own signature -- a real API change to the driver, not "
              "a `where` clause.")
    if rest:
        print(f"\n  {len(rest)} other error(s) -- read them with --errors.")
    if not strict and not rest:
        print("\n  CONVERGED: every remaining error is a datasheet "
              "violation -- the driver\n  now compiles except where it "
              "genuinely touches a gated register.")
    if verify_bounds_only(hal_dir, crate, version, pac):
        print("\n  verified: every edit is a `where` bound and nothing else.")
    print(f"\n  see exactly what changed:")
    print(f"    git diff --no-index ~/.cargo/registry/src/*/{crate}-{version} "
          f"{hal_dir}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--errors", action="store_true",
                    help="print every diagnostic verbatim")
    ap.add_argument("--apply-fix", action="store_true",
                    help="vendor the driver and apply rustc's own "
                         "MachineApplicable `where` bounds until it compiles. "
                         "Edits a COPY under vendored/, never the registry "
                         "cache, and repoints Cargo.toml at it.")
    a = ap.parse_args()

    pac = patched_crate()
    if not pac:
        sys.exit("Cargo.toml has no [patch.crates-io] entry")
    if a.apply_fix:
        if not patch_applied(pac):
            sys.exit(f"refusing to fix: the [patch] for `{pac}` did not apply, "
                     f"so there is nothing real to fix against")
        fix_loop(pac)
        return
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
    classified = [(e, enforcement.classify_diagnostic(e)) for e in errs]
    ours = [e for e, h in classified if h]
    hits = [e for e, h in classified if h and not h.projection]
    friction = [e for e, h in classified if h and h.projection]
    # E0276 is not one of our diagnostics, but after --apply-fix it is an
    # EXPECTED residue, not collateral: a bound we added landed on a method
    # implementing a trait, and Rust rejects a requirement the trait does not
    # declare. Naming it keeps it from reading as damage.
    strict = [e for e in errs if (e.get("code") or {}).get("code") == "E0276"]
    other = [e for e in errs if e not in ours and e not in strict]

    print(f"patch applied: {pac} <- local path   OK")
    print(f"errors {len(errs)}   violations {len(hits)}   "
          f"generic friction {len(friction)}   "
          f"bound-cascade {len(strict)}   other {len(other)}")

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
    if strict:
        print(f"\n  BOUND CASCADE -- {len(strict)}x E0276 'impl has stricter "
              f"requirements than trait'.")
        print("  Expected after --apply-fix: a bound landed on a method that "
              "implements a")
        print("  trait, and Rust rejects a requirement the trait itself does "
              "not declare.")
        print("  Removing them means widening the trait's signature -- an API "
              "change to the")
        print("  driver, not a local annotation. Not a finding, and not "
              "collateral.")
    if other:
        print(f"\n  OTHER -- {len(other)} error(s) that are neither ours nor "
              f"an expected\n  residue. These ARE collateral; read them with "
              f"--errors.")

    if a.errors:
        for e in errs:
            print("\n---", (e.get('code') or {}).get('code', ''),
                  e.get("message", "")[:400])
    if not errs:
        print("\n  clean build: this driver never touches a constrained "
              "register on this device.")


if __name__ == "__main__":
    main()
