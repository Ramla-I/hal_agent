#!/usr/bin/env python3
"""What the generator extracted, and what survived to a judged verdict.

Covers the constraint pipeline UP TO the review files and no further. Injection
is a separate question with a separate denominator: the cascade figure in the
injection repo counts fewer constraints because it is built from injection
reports, and a manual with no chip crate never produces one. Nothing here needs
a chip crate, so all manuals are present.

Every number prints the file it came from and how it was derived, because two
of the largest drops in this pipeline are SILENT -- they write to stderr during
a collect run and appear in no manifest or report.

Usage:
    python scripts/stm_constraint_generation_statistics.py
    python scripts/stm_constraint_generation_statistics.py --by-rm
    python scripts/stm_constraint_generation_statistics.py --csv out.csv
"""

import argparse
import collections
import csv
import json
import re
import statistics as stats
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
try:
    from defs import RegisterInfo                 # noqa: E402
except ModuleNotFoundError as e:                  # pydantic, typically
    # This worktree has no .venv of its own -- the dependencies live in the
    # sibling checkout. Say so, rather than leaving a bare ImportError for a
    # module the reader never asked for.
    sibling = REPO.parent / "hal_agent-pac-injection" / ".venv"
    hint = (f"source {sibling}/bin/activate" if sibling.is_dir()
            else "create a venv and pip install pydantic")
    sys.exit(f"{e.name} is missing: the schema check needs defs.RegisterInfo.\n"
             f"  {hint}\n"
             f"then re-run from {REPO}")

AGENT = REPO / "agent_output" / "stm"
EVAL = REPO / "evaluation" / "stm"
DEVICES = REPO / "devices" / "stm"

# The judge returns exactly these three. `encoding_error` IS a verdict -- "a
# genuine constraint, but the encoding misstates it" -- not a failure to
# answer, and it carries a confidence like the others. Excluding it from the
# judged denominator hides the single most useful generation-quality signal
# there is.
JUDGED = ("confirmed", "encoding_error", "not_constraint")

_REG_RE = re.compile(r"<register[^>]*>.*?<name>([^<]+)</name>", re.S)

SOURCES = [
    ("generated",
     "agent_output/stm/<rm>/1/<peripheral>_<register>",
     "every entry of `access_constraints_v2` in each per-register JSON file"),
    ("schema-invalid",
     "the same files, validated against defs.RegisterInfo",
     "collect's _load_register_info returns None for the WHOLE file, so every "
     "constraint in it is lost; the reason only reaches stderr"),
    ("not scanned by collect",
     "derived: generated - schema-invalid - manifest.constraints_native_v2",
     "DERIVED BY DIFFERENCE, not detected. Sampling RM0008 shows 26 of 27 are "
     "registers the SVD declares as a <dim> array (bkp_dr11, bkp_dr13...) "
     "while the generator wrote one file per element, so the name resolves "
     "nowhere. Matching those by name directly is unreliable -- peripherals "
     "like otg_fs_global contain underscores, so splitting a filename on the "
     "first '_' misattributes them -- and the manifest is authoritative"),
    ("collect lint",
     "agent_output/stm/<rm>/1/constraint_validation/manifest.json",
     "summary.constraints_native_v2 / _deduped / _v2 / _rejected, and the "
     "per-register reject reasons"),
    ("review rows",
     "evaluation/stm/<rm>/1/<rm>_constraints_review.jsonl",
     "one row per constraint that reached the validator; verdict, "
     "anchor_tier and enforcement are read from it"),
]


def manuals():
    if not AGENT.is_dir():
        sys.exit(f"no generator output under {AGENT}")
    return sorted(d.name for d in AGENT.iterdir()
                  if d.is_dir() and (d / "1").is_dir())


def svd_registers(rm: str) -> set:
    out = set()
    d = DEVICES / rm / "svd"
    if d.is_dir():
        for f in d.glob("*.svd"):
            out |= {x.lower() for x in _REG_RE.findall(f.read_text(errors="ignore"))}
    return out


def scan_generated(rm: str):
    """(kinds, schema_invalid, valid) constraint counts.

    `valid` is what a schema-valid file carries; how much of it collect
    actually scanned is taken from the manifest, not guessed here."""
    kinds = collections.Counter()
    per_register = []          # constraints carried by each register file
    bad_schema = valid = 0
    for f in sorted((AGENT / rm / "1").iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        try:
            data = json.loads(f.read_text())
        except (ValueError, UnicodeDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        raw = data.get("access_constraints_v2")
        if not isinstance(raw, list) or not raw:
            continue
        for c in raw:
            kinds[c.get("kind") or "?"] += 1
        per_register.append(len(raw))
        try:
            RegisterInfo(**{k: v for k, v in data.items()
                            if k != "access_constraints_v2"})
        except Exception:                                     # noqa: BLE001
            bad_schema += len(raw)
            continue
        valid += len(raw)
    return kinds, bad_schema, valid, per_register


def scan_manifest(rm: str) -> tuple:
    m = AGENT / rm / "1" / "constraint_validation" / "manifest.json"
    if not m.is_file():
        return {}, collections.Counter()
    j = json.loads(m.read_text())
    reasons = collections.Counter()
    for reg in j.get("registers", []):
        for r in (reg.get("rejects") or reg.get("reject_details") or []):
            reasons[r.get("reason") if isinstance(r, dict) else str(r)] += 1
    return j.get("summary", {}), reasons


def scan_review(rm: str):
    f = EVAL / rm / "1" / f"{rm}_constraints_review.jsonl"
    v, e, a = (collections.Counter() for _ in range(3))
    n = 0
    if f.is_file():
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            n += 1
            v[d.get("verdict") or "(blank)"] += 1
            e[d.get("enforcement") or "(blank)"] += 1
            a[d.get("anchor_tier") or "(blank)"] += 1
    return n, v, e, a


def describe(name, xs):
    q = stats.quantiles(xs, n=4) if len(xs) > 3 else [float("nan")] * 3
    print("  %-16s total=%-8s mean=%-7.1f median=%-7.1f sd=%-7.1f "
          "Q1=%-6.0f Q3=%-6.0f min=%-5d max=%d"
          % (name, f"{sum(xs):,}", stats.mean(xs), stats.median(xs),
             stats.stdev(xs) if len(xs) > 1 else 0.0, q[0], q[2],
             min(xs), max(xs)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--by-rm", action="store_true")
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    rms = manuals()

    print(f"repository: {REPO}")
    print(f"manuals:    {len(rms)} (discovered under agent_output/stm/*/1)\n")
    print("WHERE EACH NUMBER COMES FROM")
    for name, where, how in SOURCES:
        print(f"  {name}")
        print(f"      path   {where}")
        print(f"      method {how}")
    print()

    per, kinds, regcounts = {}, collections.Counter(), []
    verd = collections.Counter(); enf = collections.Counter()
    anch = collections.Counter(); rej = collections.Counter()
    man = collections.Counter()
    for rm in rms:
        k, bad, valid, pr = scan_generated(rm)
        regcounts.extend(pr)
        summ, reasons = scan_manifest(rm)
        scanned = summ.get("constraints_native_v2", 0) or 0
        absent = max(0, valid - scanned)
        n, v, e, a = scan_review(rm)
        kinds.update(k); verd.update(v); enf.update(e); anch.update(a)
        rej.update(reasons)
        for key in ("constraints_native_v2", "constraints_deduped",
                    "constraints_v2", "constraints_rejected"):
            man[key] += summ.get(key, 0) or 0
        per[rm] = {"generated": sum(k.values()), "schema_invalid": bad,
                   "svd_absent": absent, "reviewed": n,
                   "judged": sum(v[x] for x in JUDGED),
                   "confirmed": v.get("confirmed", 0),
                   "encoding_error": v.get("encoding_error", 0),
                   "enforce": e.get("enforce", 0)}

    gen = [p["generated"] for p in per.values()]
    rev = [p["reviewed"] for p in per.values()]
    jud = [p["judged"] for p in per.values()]

    tg, tr = sum(gen), sum(rev)
    bad = sum(p["schema_invalid"] for p in per.values())
    # Derived at CORPUS level. Summing per-manual differences and clamping each
    # at zero adds a couple of units where a manifest is newer than its run.
    absent = tg - bad - man["constraints_native_v2"]
    tj = sum(verd[x] for x in JUDGED)

    print("FUNNEL  (each line names its source above)")
    print("  %-38s %7s" % ("generated", f"{tg:,}"))
    print("  %-38s %7s   silent, stderr only" % ("  file failed RegisterInfo", f"-{bad:,}"))
    print("  %-38s %7s   silent, stderr only" % ("  not scanned by collect", f"-{absent:,}"))
    print("  %-38s %7s   manifest constraints_native_v2"
          % ("reached collect's lint", f"{man['constraints_native_v2']:,}"))
    print("  %-38s %7s" % ("  exact duplicates", f"-{man['constraints_deduped']:,}"))
    print("  %-38s %7s" % ("  rejected per-constraint", f"-{man['constraints_rejected']:,}"))
    print("  %-38s %7s   manifest constraints_v2" % ("collect kept", f"{man['constraints_v2']:,}"))
    print("  %-38s %7s   review rows on disk" % ("review rows", f"{tr:,}"))
    print("  %-38s %7s   %.0f%% of reviewed"
          % ("judged", f"{tj:,}", 100 * tj / tr if tr else 0))
    for k in JUDGED:
        print("      %-34s %7s" % (k, f"{verd[k]:,}"))
    for k, n in verd.most_common():
        if k not in JUDGED:
            print("      %-34s %7s   never reached the judge" % (k, f"{n:,}"))

    print("\n  per-constraint reject reasons (manifest; entries, not constraints)")
    for k, n in rej.most_common():
        print("      %-34s %7s" % (k, f"{n:,}"))
    print("\n  enforcement gate (review rows)")
    for k, n in enf.most_common():
        print("      %-34s %7s" % (k, f"{n:,}"))
    print("\n  quote anchor tier (review rows)")
    for k, n in anch.most_common():
        print("      %-34s %7s" % (k, f"{n:,}"))

    print("\nPER MANUAL")
    describe("generated", gen)
    describe("reached review", rev)
    describe("judged", jud)

    print("\nGENERATOR ACCURACY, over constraints the judge ruled on")
    for k in JUDGED:
        print("  %-18s %7s  %5.1f%%" % (k, f"{verd[k]:,}", 100 * verd[k] / tj))

    if regcounts:
        h = collections.Counter(regcounts)
        print("\nCONSTRAINTS PER REGISTER  (register files carrying at least one)")
        print("  registers with a constraint : %s" % f"{len(regcounts):,}")
        print("  constraints                 : %s" % f"{sum(regcounts):,}")
        print("  mean=%.2f  median=%.0f  sd=%.2f  max=%d"
              % (stats.mean(regcounts), stats.median(regcounts),
                 stats.stdev(regcounts) if len(regcounts) > 1 else 0.0,
                 max(regcounts)))
        print("  distribution")
        for n in sorted(h):
            if n > 8:
                break
            print("      %2d constraint%s %7s  %5.1f%%"
                  % (n, " " if n == 1 else "s", f"{h[n]:,}",
                     100 * h[n] / len(regcounts)))
        tail = sum(v for k, v in h.items() if k > 8)
        if tail:
            print("      9+ constraints %7s  %5.1f%%"
                  % (f"{tail:,}", 100 * tail / len(regcounts)))

    print("\nBY GRAMMAR KIND  (generator output)")
    for k, n in kinds.most_common():
        print("  %-18s %7s  %5.1f%%" % (k, f"{n:,}", 100 * n / tg))

    unknown = set(verd) - set(JUDGED) - {"(blank)"}
    if unknown:
        print(f"\n!! unrecognised verdicts: {sorted(unknown)}")

    if args.by_rm:
        print("\nPER-MANUAL DETAIL")
        cols = ("generated", "schema_invalid", "svd_absent", "reviewed",
                "judged", "confirmed", "encoding_error", "enforce")
        print("  %-8s %s" % ("rm", " ".join(c[:9].rjust(10) for c in cols)))
        for rm in rms:
            p = per[rm]
            print("  %-8s %s" % (rm, " ".join(str(p[c]).rjust(10) for c in cols)))

    if args.csv:
        cols = ("generated", "schema_invalid", "svd_absent", "reviewed",
                "judged", "confirmed", "encoding_error", "enforce")
        with open(args.csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["rm", *cols])
            for rm in rms:
                w.writerow([rm, *(per[rm][c] for c in cols)])
        print(f"\ncsv: {args.csv}")


if __name__ == "__main__":
    main()
