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
sys.path.insert(0, str(REPO / "scripts"))
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

DEFAULT_FIGURE = REPO / "docs" / "figures" / "constraint_generation.pdf"

# Palette and spacing are lifted from stm_structure_statistics so the two
# figures sit together in a paper without looking like they came from different
# tools. Colour carries the STAGE, texture separates neighbours of one family.
#
#   blue-grey, no hatch / hatched : the two SILENT skips -- one family, because
#                                   they fail the same way (stderr only, in no
#                                   manifest), and texture tells them apart
#   orange                        : collect's own lint, which does report
#   amber                         : the quote anchor, which stops a constraint
#                                   before the judge ever sees it
#   pink / blue / light           : the judge's three verdicts, ending in the
#                                   light fill the structure figure uses for
#                                   its "agrees" segment
# Each label names the CHECK that decided the constraint's fate, not how the
# outcome felt. "not scanned" said nothing about what did the not-scanning;
# "SVD lookup" says a name was looked up in the SVD and was not there, which is
# the thing a reader can go and verify. The three validator segments keep the
# prefix so it is clear one stage produced all three verdicts -- colour groups
# them, but the legend should not need the colour to be read.
# TWO BANDS, because there are two units and pretending otherwise is what the
# single-bar version got wrong. Band one counts SOURCE constraints -- what the
# generator wrote, and what each deterministic stage did with it. Band two
# counts REVIEW ROWS. They are not the same quantity: collect splits an "any"
# gate into per-operation gates, so 11,557 survivors become 11,895 linted
# constraints. A net difference hides that; a connector states it.
#
# Band two is the magnification of band one's final segment, drawn with the
# same zoom connector the structure cascade uses.
BAND1 = [
    ("schema_invalid",   "schema check",              "#a3c8ee", (45,)),
    ("deduped",          "exact duplicate",           "#eb6834", (135,)),
    ("rejected",         "deterministic reject",      "#eda100", (45, 135)),
    ("survived",         "survived collection",       "#6f57a8", (0,)),
]
BAND2 = [
    ("never_judged",    "quote anchor",              "#e87ba4", (90,)),
    ("not_constraint",  "validator: not constraint", "#eb6834", (135,)),
    ("encoding_error",  "validator: encoding error", "#2a78d6", (45,)),
    ("confirmed",       "validator: confirmed",      "#c9d3e2", ()),
]

# Within a band every segment carries its own texture, so hue and texture each
# identify a segment on their own and the bar survives greyscale.
for _band in (BAND1, BAND2):
    assert len({h for _k, _l, _c, h in _band}) == len(_band), \
        "two segments in one band share a hatch pattern"
SOURCES = [
    ("generated",
     "agent_output/stm/<rm>/1/<peripheral>_<register>",
     "every entry of `access_constraints_v2` in each per-register JSON file"),
    ("schema check",
     "the same files, validated against defs.RegisterInfo",
     "collect's _load_register_info returns None for the WHOLE file, so every "
     "constraint in it is lost; the reason only reaches stderr"),
    ("out of scope",
     "manifest.registers -- the list of registers collect actually scanned",
     "a later generator pass added registers to runs whose collect and judge "
     "had already finished. Those constraints live only in agent_output: never "
     "collected, anchored or judged, and in no review file. EXCLUDED from "
     "every figure below, because counting them beside the reviewed set shows "
     "a loss rate that is partly just work not yet done"),
    ("exact duplicate / deterministic reject / expansion",
     "agent_output/stm/<rm>/1/constraint_validation/manifest.json",
     "summary.constraints_deduped and _rejected are collect's own counts. "
     "Note collect also EXPANDS: an `any` gate becomes one gate per operation, "
     "so constraints_v2 exceeds native - dedup - rejected by 242 across 21 "
     "manuals. Source constraints and review rows are therefore different "
     "units, which is why the figure has two bands and not one bar"),
    ("verdicts",
     "evaluation/stm/<rm>/1/<rm>_constraints_review.jsonl",
     "one row per constraint that reached the validator. `verdict` empty and "
     "`anchor_tier` unanchored coincide exactly (490/490): the quote anchor is "
     "a gate before the judge, so an unanchorable sentence is never judged"),
]

_LEG_TRAIL = 8.0


def _legend_row(p, x, y, items, width, size=7.0):
    """Swatch + name + count for every segment, wrapping within `width`.

    Same helper as the structure figure: in one column the narrow segments
    cannot hold text, and dropping a small segment's label silently is how a
    whole stage becomes an unexplained sliver."""
    from pdfwriter import _HELV_ADV
    cx, cy = x, y
    for col, hat, text in items:
        w = 7 + 4 + _HELV_ADV * size * len(text) + _LEG_TRAIL
        if cx + w > x + width:
            cx, cy = x, cy - (size + 4)
        p.fill(col)
        p.stroke("#ffffff")
        p.rect(cx, cy, 7, 7, 0.5)
        p.hatch(cx, cy, 7, 7, hat, gap=2.0, lw=0.4)
        p.fill("#1b212b")
        p.text(cx + 11, cy + 1, text, size, "F1")
        cx += w
    return cy


def write_figure(b1: dict, b2: dict, bridge: str, path: Path,
                 width_in=3.4, height_in=None):
    """Two bands: source constraints, then the review rows they became.

    Band two is band one's `survived` segment opened up, so the zoom connector
    runs between them exactly as it does in the structure cascade. The bridge
    line carries the adjustment that makes the two totals differ -- expansion
    of `any` gates, and the duplicates removed after collection -- because that
    difference is a fact about the pipeline, not rounding to be absorbed."""
    from pdfwriter import Pdf, _HELV_ADV
    W = width_in * 72.0
    ml, mr = 14.0, 8.0
    pw = W - ml - mr
    bh = 21.0
    TOP_PAD, TITLE_GAP, LABEL_GAP, BAND_GAP = 16.0, 6.0, 13.0, 22.0
    F_TITLE, F_LEG, F_NOTE = 8.0, 7.6, 6.6

    bands = [
        ("every access constraint the generator produced",
         [(lab, b1.get(k, 0), c, h) for k, lab, c, h in BAND1]),
        ("the survivors, by the validator's verdict",
         [(lab, b2.get(k, 0), c, h) for k, lab, c, h in BAND2]),
    ]

    def items_for(segs):
        return [(c, h, "%s %s" % (lab, "{:,}".format(n)))
                for lab, n, c, h in segs if n]

    def rows_for(items):
        cx, rows = 0.0, 1
        for _c, _h, text in items:
            w = 7 + 4 + _HELV_ADV * F_LEG * len(text) + 8.0
            if cx + w > pw:
                rows += 1
                cx = 0.0
            cx += w
        return rows

    legs = [items_for(segs) for _t, segs in bands]
    if height_in:
        H = height_in * 72.0
    else:
        H = TOP_PAD + F_TITLE + TITLE_GAP
        for i in range(len(bands)):
            H += bh + LABEL_GAP + (rows_for(legs[i]) - 1) * (F_LEG + 4)
            H += (BAND_GAP + F_NOTE + 4) if i == 0 else 12.0
    p = Pdf(W, H)

    top = H - TOP_PAD - TITLE_GAP - F_TITLE
    zoom = None
    for bi, (title, segs) in enumerate(bands):
        total = sum(n for _l, n, _c, _h in segs)
        if not total:
            continue
        p.fill("#5c6675")
        p.text(ml + pw / 2, top + TITLE_GAP, title, F_TITLE, "F1", "middle")
        y, x = top - bh, ml
        for lab, n, col, hat in segs:
            if not n:
                continue
            wseg = max(0.9, pw * n / total)
            p.fill(col)
            p.stroke("#ffffff")
            p.rect(x, y, wseg, bh, 0.7)
            p.hatch(x, y, wseg, bh, hat)
            if bi == 0 and lab.startswith("survived"):
                zoom = (x, x + wseg)
            x += wseg
        if bi == 1 and zoom:
            p.stroke("#c0c7d2")
            p.line(zoom[0], prev_bottom, ml, top, 0.5)
            p.line(zoom[1], prev_bottom, ml + pw, top, 0.5)
        bottom = _legend_row(p, ml, y - LABEL_GAP, legs[bi], pw, size=F_LEG)
        if bi == 0:
            p.fill("#8b8f97")
            p.text(ml + pw / 2, bottom - F_NOTE - 5, bridge, F_NOTE, "F1", "middle")
            prev_bottom = bottom - F_NOTE - 7
            top = prev_bottom - BAND_GAP
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(p.to_bytes())

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


def scan_generated(rm: str, scanned: set, manifest_mtime: float):
    """(kinds, schema_invalid, valid, per_register, out_of_scope) for one manual.

    ONLY register files the validation pipeline actually processed are counted.
    A later generator pass added registers to runs whose collect and judge had
    already finished, and those constraints exist solely as JSON in
    agent_output -- never collected, never anchored, never judged, in no review
    file. Counting them beside the reviewed set would show a loss rate that is
    partly just work not yet done.

    In scope means: the register is in the manifest's own list of what collect
    scanned, or it fails the RegisterInfo schema and predates the manifest --
    collect saw those and skipped the whole file, which is a real loss and
    belongs in the funnel."""
    kinds = collections.Counter()
    per_register = []          # constraints carried by each register file
    bad_schema = valid = out_of_scope = out_of_scope_files = 0
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
        per, _, reg = f.name.partition("_")
        try:
            RegisterInfo(**{k: v for k, v in data.items()
                            if k != "access_constraints_v2"})
            ok = True
        except Exception:                                     # noqa: BLE001
            ok = False
        if (per.lower(), reg.lower()) in scanned:
            pass                                   # collect scanned it
        elif not ok and f.stat().st_mtime <= manifest_mtime + 1:
            pass                                   # collect saw it, schema skip
        else:
            out_of_scope += len(raw)
            out_of_scope_files += 1
            continue
        for c in raw:
            kinds[c.get("kind") or "?"] += 1
        per_register.append(len(raw))
        if ok:
            valid += len(raw)
        else:
            bad_schema += len(raw)
    return (kinds, bad_schema, valid, per_register, out_of_scope,
            out_of_scope_files)


def scan_manifest(rm: str) -> tuple:
    m = AGENT / rm / "1" / "constraint_validation" / "manifest.json"
    if not m.is_file():
        return {}, collections.Counter(), set(), 0.0
    j = json.loads(m.read_text())
    scanned = {(r.get("peripheral", "").lower(), r.get("register", "").lower())
               for r in j.get("registers", [])}
    reasons = collections.Counter()
    for reg in j.get("registers", []):
        for r in (reg.get("rejects") or reg.get("reject_details") or []):
            reasons[r.get("reason") if isinstance(r, dict) else str(r)] += 1
    return j.get("summary", {}), reasons, scanned, m.stat().st_mtime


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
    ap.add_argument("--figure", nargs="?", const=str(DEFAULT_FIGURE),
                    default=None, help="write the single-bar breakdown")
    ap.add_argument("--width-in", type=float, default=3.4)
    ap.add_argument("--height-in", type=float, default=None)
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
    excluded = excluded_files = 0
    verd = collections.Counter(); enf = collections.Counter()
    anch = collections.Counter(); rej = collections.Counter()
    man = collections.Counter()
    for rm in rms:
        summ, reasons, scanned, mmt = scan_manifest(rm)
        k, bad, valid, pr, oos, oosf = scan_generated(rm, scanned, mmt)
        regcounts.extend(pr)
        excluded += oos
        excluded_files += oosf
        n, v, e, a = scan_review(rm)
        kinds.update(k); verd.update(v); enf.update(e); anch.update(a)
        rej.update(reasons)
        for key in ("constraints_native_v2", "constraints_deduped",
                    "constraints_v2", "constraints_rejected"):
            man[key] += summ.get(key, 0) or 0
        per[rm] = {"generated": sum(k.values()), "schema_invalid": bad,
                   "out_of_scope": oos, "reviewed": n,
                   "judged": sum(v[x] for x in JUDGED),
                   "confirmed": v.get("confirmed", 0),
                   "encoding_error": v.get("encoding_error", 0),
                   "enforce": e.get("enforce", 0)}

    gen = [p["generated"] for p in per.values()]
    rev = [p["reviewed"] for p in per.values()]
    jud = [p["judged"] for p in per.values()]

    tg, tr = sum(gen), sum(rev)
    bad = sum(p["schema_invalid"] for p in per.values())
    valid_total = tg - bad
    # Derived at CORPUS level. Summing per-manual differences and clamping each
    # at zero adds a couple of units where a manifest is newer than its run.
    # What collect scanned, minus what the files now carry. Should be near
    # zero once scope is enforced; reported rather than absorbed so a drift
    # between the manifest and the run dir cannot hide.
    residual = man["constraints_native_v2"] - valid_total
    tj = sum(verd[x] for x in JUDGED)

    if excluded:
        print("EXCLUDED FROM EVERYTHING BELOW")
        print("  cannot collect statistics for %s generator output files: they "
              "have not" % f"{excluded_files:,}")
        print("  passed through the validation pipeline. A later generator pass "
              "added them")
        print("  after collect and the judge had run, so they carry %s "
              "constraints that" % f"{excluded:,}")
        print("  no manifest, review file or injection report accounts for.\n")

    print("FUNNEL  (each line names its source above)")
    print("  %-38s %7s" % ("generated", f"{tg:,}"))
    print("  %-38s %7s   silent, stderr only" % ("  file failed RegisterInfo", f"-{bad:,}"))
    print("  %-38s %7s   manifest constraints_native_v2"
          % ("reached collect's lint", f"{man['constraints_native_v2']:,}"))
    if residual:
        print("  %-38s %7s   manifest vs run dir; see --by-rm"
              % ("  (unreconciled)", f"{residual:+,}"))
    print("  %-38s %7s" % ("  exact duplicates", f"-{man['constraints_deduped']:,}"))
    print("  %-38s %7s" % ("  rejected per-constraint", f"-{man['constraints_rejected']:,}"))
    print("  %-38s %7s   manifest constraints_v2" % ("collect kept", f"{man['constraints_v2']:,}"))
    print("  %-38s %7s   review rows on disk" % ("review rows", f"{tr:,}"))
    print("  %-38s %7s   %.0f%% of reviewed"
          % ("judged", f"{tj:,}", 100 * tj / tr if tr else 0))
    for k in JUDGED:
        print("      %-34s %7s" % (k, f"{verd[k]:,}"))
    # A blank verdict is not a category of its own: it is exactly the set the
    # quote anchor rejected. Verified 1:1 -- every blank-verdict row is
    # `unanchored` and every unanchored row has a blank verdict -- so print the
    # gate that caused it, matching the figure, rather than the empty field
    # value the file happens to carry.
    for k, n in verd.most_common():
        if k not in JUDGED:
            label = ("quote anchor (unanchored)" if k == "(blank)" else k)
            print("      %-34s %7s   never reached the judge"
                  % (label, f"{n:,}"))

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
        cols = ("generated", "schema_invalid", "out_of_scope", "reviewed",
                "judged", "confirmed", "encoding_error", "enforce")
        print("  %-8s %s" % ("rm", " ".join(c[:9].rjust(10) for c in cols)))
        for rm in rms:
            p = per[rm]
            print("  %-8s %s" % (rm, " ".join(str(p[c]).rjust(10) for c in cols)))

    if args.figure:
        # Band one is SOURCE constraints; `survived` is the remainder, so the
        # band sums to what the generator produced in scope. Band two is REVIEW
        # ROWS. The two totals differ, and the bridge says by how much and why
        # rather than letting a net difference swallow it.
        ded = man["constraints_deduped"]
        rej = man["constraints_rejected"]
        survived = tg - bad - ded - rej
        b1 = {"schema_invalid": bad, "deduped": ded, "rejected": rej,
              "survived": survived}
        b2 = {"never_judged": tr - tj,
              "not_constraint": verd.get("not_constraint", 0),
              "encoding_error": verd.get("encoding_error", 0),
              "confirmed": verd.get("confirmed", 0)}
        assert sum(b1.values()) == tg, (sum(b1.values()), tg)
        assert sum(b2.values()) == tr, (sum(b2.values()), tr)
        expand = man["constraints_v2"] - (man["constraints_native_v2"] - ded - rej)
        post = man["constraints_v2"] - tr
        bridge = ("%s survivors -> %s linted (+%d 'any' split per operation)"
                  " -> %s rows (-%d duplicates)"
                  % ("{:,}".format(survived),
                     "{:,}".format(man["constraints_v2"]), expand,
                     "{:,}".format(tr), post))
        out = Path(args.figure)
        write_figure(b1, b2, bridge, out, args.width_in, args.height_in)
        print(f"\nfigure: {out}")
        print(f"  band 1  {sum(b1.values()):,} source constraints")
        print(f"  bridge  {bridge}")
        print(f"  band 2  {sum(b2.values()):,} review rows")

    if args.csv:
        cols = ("generated", "schema_invalid", "out_of_scope", "reviewed",
                "judged", "confirmed", "encoding_error", "enforce")
        with open(args.csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["rm", *cols])
            for rm in rms:
                w.writerow([rm, *(per[rm][c] for c in cols)])
        print(f"\ncsv: {args.csv}")


if __name__ == "__main__":
    main()
