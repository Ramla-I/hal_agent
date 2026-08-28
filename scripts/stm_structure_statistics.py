#!/usr/bin/env python3
"""Whole-corpus structure-review statistics, per attribute category.

Counts, for every reference manual, how many structure facts the generator
produced, how many the vendor SVD agreed with, and where each disagreement was
dropped on its way to a human. Raw numbers only -- no ratios, no percentages;
the point is to have the counts so ratios can be chosen afterwards.

    python scripts/stm_structure_statistics.py
    python scripts/stm_structure_statistics.py --by-rm
    python scripts/stm_structure_statistics.py --marked          # + labels
    python scripts/stm_structure_statistics.py --csv out.csv

NOTHING IS HARDCODED. Attribute categories are discovered from the review
files, whether a category is register- or field-level is inferred from whether
its rows carry a field name, and every count is read from disk. The only fixed
mapping is REVIEW_TO_GENERATOR below, which cannot be derived: the review CSVs
and the generator's JSON use different names for the same fact.

THE PIPELINE, as it actually runs (read from the artifacts, not assumed):

  generated        every attribute the generator emitted for a register or
                   field that also exists in the SVD. Registers or fields
                   present on only one side are COVERAGE, not agreement, and
                   are excluded -- counting them would credit or penalise the
                   wrong thing.
  agreed           generated minus disagreed.
  disagreed        a row in the consolidated review CSV.
  dropped mech     `status == false_positive`. Despite the name this stage is
                   entirely deterministic (`split_mechanical_fps`): every one
                   carries an `[auto-FP: ...]` reason such as "whole-register
                   uniform bit shift" or "generator value empty".
  dropped analyzer the LLM analyzer's own keep/drop decision. It is NOT in the
                   consolidated CSV -- dropped rows are never written there --
                   so it is read from the per-SVD analyzer caches and
                   deduplicated on the same key the CSV dedupes on.
  dropped valid.   `validator_verdict == FP`.
  no verdict       survived the drops but the validator returned nothing.
  remaining        `validator_verdict == TP`: what a human is asked to read.

  --marked adds tp/marked, i.e. of the rows a human has actually labelled,
  how many were true positives. The denominator is rows LABELLED, never rows
  disagreed, because labelling is partial and dividing by the full pile would
  understate the hit rate.
"""

import argparse
import collections
import csv
import glob
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pdfwriter import Pdf, _HELV_ADV  # noqa: E402
from analyze_review_fps import is_width_variant, is_placeholder  # noqa: E402

# This script now lives inside the repo it reads, so the root is derived
# rather than hardcoded to an absolute path on one machine.
PHASE1D = Path(__file__).resolve().parent.parent

# The one mapping that cannot be inferred: a review `key` names a fact, and the
# generator's JSON stores it under a different name (or derives it, as both
# bit_offset and bit_width come from one bit_number object). A key absent here
# is reported as unmapped rather than silently counted as zero.
REVIEW_TO_GENERATOR = {
    "address_offset": ("register", "address_offset"),
    "size":           ("register", "size"),
    "reset_value":    ("register", "reset_value"),
    "bit_offset":     ("field",    "bit_number"),
    "bit_width":      ("field",    "bit_number"),
    "access":         ("field",    "access"),
}


def parse_svd(path):
    """(peripheral, register) -> field names, following peripheral derivedFrom."""
    root = ET.parse(path).getroot()
    peris = {}
    for pe in root.iter("peripheral"):
        n = (pe.findtext("name") or "").lower()
        if n:
            peris[n] = pe
    out = {}
    for n, pe in peris.items():
        src = peris.get((pe.get("derivedFrom") or "").lower(), pe)
        for r in src.iter("register"):
            rn = (r.findtext("name") or "").lower()
            if rn:
                out[(n, rn)] = {(f.findtext("name") or "").lower()
                                for f in r.iter("field") if f.findtext("name")}
    return out


def review_rows(run_dir: Path):
    """Every consolidated review row for one manual, from every review file.

    Access lives in its own `*_access_review.csv`; structure attributes in
    `*_structure_review.csv`. Both share a schema, so they are read together
    and separated by their own `key` column rather than by filename.
    """
    for p in sorted(run_dir.glob("*_review.csv")):
        if p.parent != run_dir:
            continue
        with p.open(newline="") as fh:
            for row in csv.DictReader(fh):
                if row.get("key"):
                    yield row


def analyzer_dropped(run_dir: Path):
    """Keys the LLM analyzer discarded, deduplicated across the manual's SVDs.

    These rows are NEVER WRITTEN to the consolidated review CSV -- the CSV
    holds the mechanical false positives and whatever the analyzer kept, and
    nothing else. So they cannot be found by walking review rows; they have to
    be read from the per-SVD caches and added to the disagreement total
    separately, or the funnel silently loses them.

    Cache keys are `peripheral|register|field|key|svd_value|generator_value`,
    the same tuple the consolidated CSV dedupes on, so a discrepancy shared by
    four sibling SVDs counts once here exactly as it does there. A key kept in
    any SVD is not counted as dropped.
    """
    dropped, kept = set(), set()
    for p in run_dir.glob("*/*_analyzer_cache.json"):
        try:
            cache = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for k, v in cache.items():
            (kept if v.get("kept") else dropped).add(k)
    return dropped - kept, kept


def generated_counts(rm: str, root: Path, keys):
    """category -> attributes emitted for something the SVD also has."""
    svds = list((root / "devices" / "stm" / rm / "svd").glob("*.svd"))
    gens = list((root / "agent_output" / "stm" / rm / "1").glob("*"))
    counts = collections.Counter()
    if not svds or not gens:
        return counts
    svd = {}
    for s in svds:
        try:
            for k, v in parse_svd(s).items():
                svd.setdefault(k, set()).update(v)
        except ET.ParseError:
            continue
    reg_keys = [k for k in keys if REVIEW_TO_GENERATOR.get(k, ("", ""))[0] == "register"]
    fld_keys = [k for k in keys if REVIEW_TO_GENERATOR.get(k, ("", ""))[0] == "field"]
    for g in gens:
        name = os.path.basename(g)
        if os.path.isdir(g) or "_" not in name:
            continue
        per, _, reg = name.partition("_")
        if (per.lower(), reg.lower()) not in svd:
            continue
        try:
            d = json.loads(Path(g).read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for k in reg_keys:
            if d.get(REVIEW_TO_GENERATOR[k][1]) is not None:
                counts[k] += 1
        fields = svd[(per.lower(), reg.lower())]
        for sf in d.get("subfields") or []:
            fn = (sf.get("name") or "").lower()
            if not fn or fn not in fields:
                continue
            for k in fld_keys:
                if sf.get(REVIEW_TO_GENERATOR[k][1]) is not None:
                    counts[k] += 1
    return counts


def collect(root: Path, exclude=(), with_prefilter=False):
    """Per (rm, category) counters for every stage.

    `exclude` drops whole categories before any counting, so the totals, the
    agreement denominator and the figure all shrink together. Useful for
    `access`, which runs a separate pipeline -- no mechanical filter, no
    analyzer -- and has no labels, so leaving it in mixes two different
    processes in one funnel and hands nearly half of band three to a category
    nothing is known about.
    """
    stats = collections.defaultdict(collections.Counter)
    level = {}
    unmapped = set()
    run_dirs = sorted(p for p in root.glob("evaluation/stm/*/1") if p.is_dir())
    for run in run_dirs:
        rm = run.parent.name
        rows = list(review_rows(run))
        if not rows:
            continue
        dropped, _kept = analyzer_dropped(run)
        for r in rows:
            k = r["key"]
            if k in exclude:
                continue
            if k not in REVIEW_TO_GENERATOR:
                unmapped.add(k)
            level.setdefault(k, "field" if (r.get("field") or "").strip()
                             else "register")
            c = stats[(rm, k)]
            c["disagreed"] += 1
            status = (r.get("status") or "").strip()
            verdict = (r.get("validator_verdict") or "").strip()
            bug_key = "|".join([r.get("peripheral", ""), r.get("register", ""),
                                r.get("field", ""), k,
                                r.get("svd_value", ""), r.get("generator_value", "")])
            if with_prefilter and (is_width_variant(r) or is_placeholder(r)):
                # projected pre-validator screen (issue #23): the width-variant and
                # placeholder rules would drop these deterministically, so count them
                # under dropped_mechanical regardless of their actual status/verdict.
                c["dropped_mechanical"] += 1
            elif status == "false_positive":
                c["dropped_mechanical"] += 1
            elif bug_key in dropped:
                c["dropped_analyzer"] += 1
            elif verdict == "FP":
                c["dropped_validator"] += 1
            elif verdict == "TP":
                c["remaining"] += 1
                lab = (r.get("tp_fp") or "").strip()
                if lab == "TP":
                    c["remaining_tp"] += 1
                elif lab == "FP":
                    c["remaining_fp"] += 1
            else:
                c["no_verdict"] += 1
            t = (r.get("tp_fp") or "").strip()
            if t in ("TP", "FP"):
                c["marked"] += 1
                if t == "TP":
                    c["marked_tp"] += 1
        # Analyzer drops never reach the CSV, so they are added here from the
        # cache. Their category is field 3 of the cache key.
        for bug_key in dropped:
            parts = bug_key.split("|")
            if len(parts) < 4 or not parts[3] or parts[3] in exclude:
                continue
            k = parts[3]
            level.setdefault(k, "field" if parts[2] else "register")
            c = stats[(rm, k)]
            c["disagreed"] += 1
            c["dropped_analyzer"] += 1
        for k, n in generated_counts(rm, root, list(level)).items():
            if k not in exclude:
                stats[(rm, k)]["generated"] += n
    for (_rm, k), c in stats.items():
        c["agreed"] = max(0, c["generated"] - c["disagreed"])
    return stats, level, unmapped


COLS = ["generated", "agreed", "disagreed", "dropped_mechanical",
        "dropped_analyzer", "dropped_validator", "no_verdict", "remaining"]


def emit(stats, level, by_rm, marked, out_csv):
    cols = COLS + (["marked", "marked_tp"] if marked else [])
    rows = []
    if by_rm:
        for (rm, k) in sorted(stats):
            rows.append([rm, k, level.get(k, "?")]
                        + [stats[(rm, k)][c] for c in cols])
        head = ["rm", "category", "level"] + cols
    else:
        agg = collections.defaultdict(collections.Counter)
        for (_rm, k), c in stats.items():
            agg[k].update(c)
        order = sorted(agg, key=lambda k: (level.get(k, "?"), -agg[k]["generated"]))
        for k in order:
            rows.append([k, level.get(k, "?")] + [agg[k][c] for c in cols])
        total = collections.Counter()
        for c in agg.values():
            total.update(c)
        rows.append(["TOTAL", ""] + [total[c] for c in cols])
        head = ["category", "level"] + cols

    w = [max(len(str(r[i])) for r in ([head] + rows)) for i in range(len(head))]
    print("  ".join(h.rjust(w[i]) if i >= (3 if by_rm else 2) else h.ljust(w[i])
                    for i, h in enumerate(head)))
    for r in rows:
        print("  ".join(str(v).rjust(w[i]) if i >= (3 if by_rm else 2)
                        else str(v).ljust(w[i]) for i, v in enumerate(r)))
    if out_csv:
        with open(out_csv, "w", newline="") as fh:
            wr = csv.writer(fh)
            wr.writerow(head)
            wr.writerows(rows)
        print(f"\ncsv: {out_csv}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(PHASE1D),
                    help="repo holding evaluation/, devices/ and agent_output/")
    ap.add_argument("--by-rm", action="store_true",
                    help="one row per (manual, category) instead of totals")
    ap.add_argument("--marked", action="store_true",
                    help="add marked and marked_tp; tp is out of rows LABELLED, "
                         "not rows disagreed")
    ap.add_argument("--exclude", action="append", default=[], metavar="CATEGORY",
                    help="drop a category everywhere (repeatable), e.g. "
                         "--exclude access")
    ap.add_argument("--with-prefilter", action="store_true",
                    help="PROJECTED: also count rows matching the width_variant / "
                         "placeholder rules (issue #23) as dropped_mechanical")
    ap.add_argument("--csv", default=None)
    ap.add_argument("--cascade-figure", nargs="?",
                    const="docs/figures/structure_cascade.pdf", default=None,
                    help="write the cascade figure (that figure only)")
    ap.add_argument("--agreement-figure", nargs="?",
                    const="docs/figures/structure_agreement.pdf", default=None,
                    help="write the per-attribute agreement figure")
    args = ap.parse_args()

    root = Path(args.root)
    if not (root / "evaluation" / "stm").is_dir():
        sys.exit(f"no evaluation/stm under {root}")
    stats, level, unmapped = collect(root, set(args.exclude), args.with_prefilter)
    if args.with_prefilter:
        print("projecting the width_variant + placeholder pre-filter into "
              "dropped_mechanical (issue #23)\n")
    if args.exclude:
        print(f'excluding: {", ".join(sorted(set(args.exclude)))}\n')
    if not stats:
        sys.exit("no review rows found")
    if unmapped:
        print(f"!! categories with no generator mapping, `generated` will read 0: "
              f"{sorted(unmapped)}\n", file=sys.stderr)
    n_rm = len({rm for rm, _ in stats})
    print(f"{n_rm} manuals\n")
    emit(stats, level, args.by_rm, args.marked, args.csv)
    if args.cascade_figure:
        fp = Path(args.cascade_figure)
        write_cascade(stats, level, fp)
        print(f"\ncascade:   {fp}")
    if args.agreement_figure:
        fp = Path(args.agreement_figure)
        write_agreement(stats, level, fp)
        print(f"agreement: {fp}")


# --------------------------------------------------------------------------- #
# Figure
# --------------------------------------------------------------------------- #
#
# THE SCALE PROBLEM. The quantities span 658,011 down to 2,703 -- a factor of
# 243. On one linear axis everything after the first bar is a hairline, which
# is exactly the misreading to avoid: it would show the disagreements as
# nothing, or (drawn on their own) as though the generator were wrong
# constantly. So the figure is a zoom cascade: each band is a magnification of
# the previous band's last segment, with connectors showing the nesting.
#
# WHAT THE FIGURE CAN AND CANNOT CLAIM. Agreement with the SVD is an INDIRECT
# accuracy measure -- indirect because the SVD is itself sometimes wrong, which
# is the whole reason the disagreements are interesting. Recall through the
# drop stages is NOT measurable here and never will be: the point of the
# pipeline is to avoid manual labour, so nobody labels the discarded pile. The
# validator was instead characterised separately, on a labelled held-out set,
# and those numbers are printed on the figure so the drop is not a black box.

VALIDATOR_NOTE = ("validator characterised separately on a labelled set: "
                  "precision 0.948 -> 0.941 across STM devices (-0.007), "
                  "recall 0.689 -> 0.843")

# GREEN IS RESERVED for the segment that carries into the next band, in every
# band, so the eye can follow the zoom without reading a caption: green always
# means "this is what we magnify next".
#
# Everything else is drawn from the non-green slots, six of them, because the
# widest band has six segments and cycling a shorter list would put the same
# paint on two different things in one row -- which is how `remaining` and
# `mechanical` came out identically orange. Each also gets its own texture, so
# a row stays readable in greyscale and to a colourblind reader.
# Colour carries continuity down the cascade. Band one's disagreements are
# BLUE, and band two opens them with the mechanical drops in a LIGHTER BLUE --
# they are 61% of that band, so the tint says "this is most of what you just
# saw" without repainting it identically. Green stays the carry-forward marker
# for the band two -> band three step, and band three is its light tint.
AGREE_FILL = "#c9d3e2"
DISAGREE_FILL, DISAGREE_HATCH = "#2a78d6", (45,)
MECH_FILL = "#a3c8ee"
ZOOM_FILL, ZOOM_HATCH = "#6f57a8", (135,)   # carry-forward marker: violet, not green
# analyzer, validator, no verdict -- distinct from both blues and from green
STAGE_PAINT = [(MECH_FILL, ()), ("#eb6834", (45,)), ("#eda100", (45, 135)),
               ("#e87ba4", (90,))]

# The last band is ONE COLOUR, separated by texture alone. Bands two and three
# answer different questions -- why a disagreement was dropped, and what kind
# of fact the survivors are about -- so painting them from the same hue list
# implied a correspondence between "mechanical" and "reset_value" that does not
# exist. Dropping hue there removes the false pairing and leaves texture, which
# was already carrying the distinction.
#
# That colour is a light tint of the zoom green, because band three IS the
# magnification of band two's green segment: the tint says "this is that
# segment, opened up" without competing with the zoom marker itself.
CAT_FILL = "#8ed1b4"
CAT_HATCH = [(), (45,), (135,), (45, 135), (90,), (0,)]

# The last band divides the reviewer's pile into FP (left) and TP (right) by
# COLOUR, and within each side splits the five attributes by their CAT_HATCH
# pattern -- so colour = verdict, hatch = attribute. A bold divider marks the seam.
# FP is a lighter shade of the band-two carry-forward violet (it IS the bulk of
# that segment magnified); TP stays green so the real bugs stand out.
FP_FILL = "#b6a6d8"   # the validator's miss (false positive) -- tint of ZOOM_FILL
TP_FILL = "#4fae82"   # a real SVD bug the validator surfaced (true positive)
DIVIDER = "#1b212b"

# "deterministic" rather than "mechanical": that stage is a fixed set of rules
# over the diff values themselves -- same input, same verdict, no model in the
# loop -- and it is the only stage of the three that is not an LLM, which is
# the distinction a reader needs. ("rule-based" reads equally well if a shorter
# label is wanted.)
BAND_LABEL = {"agreed": "agrees with SVD", "disagreed": "disagrees",
              "dropped_mechanical": "deterministic",
              "dropped_analyzer": "analyzer",
              "dropped_validator": "validator", "no_verdict": "no verdict",
              "remaining": "review"}
STAGE_BAND = ["dropped_mechanical", "dropped_analyzer", "dropped_validator",
              "no_verdict", "remaining"]


# Horizontal gap after each legend entry. 8 (was 12) so band two's five stage
# labels pack into two rows -- "review" joins validator/no-verdict rather than
# spilling onto a third row of its own.
_LEG_TRAIL = 8.0


def _legend_row(p, x, y, items, width, size=7.0):
    """Swatch + name + count for every segment, wrapping within `width`.

    A band gets one of these instead of in-bar labels as soon as any segment is
    too narrow to hold text. Dropping the label of a small segment silently is
    what left a 3,749-row stage on the figure as an unexplained green sliver.
    """
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


def _title_boxes(p, cx, y, size, prefix, af, al, bf, bl, sep="  |  "):
    """Centred title 'prefix [box] al sep [box] bl' -- a small colour box sits just
    before each verdict label so the title doubles as the FP/TP colour key."""
    bs, gap = size * 0.8, 2.5

    def tw(s):
        return _HELV_ADV * size * len(s)

    total = tw(prefix) + bs + gap + tw(al) + tw(sep) + bs + gap + tw(bl)
    x = [cx - total / 2]

    def txt(s):
        p.fill("#5c6675")
        p.text(x[0], y, s, size, "F1")
        x[0] += tw(s)

    def box(fill):
        p.fill(fill)
        p.stroke("#ffffff")
        p.rect(x[0], y, bs, bs, 0.4)
        x[0] += bs + gap

    txt(prefix)
    box(af)
    txt(al)
    txt(sep)
    box(bf)
    txt(bl)


def write_cascade(stats, level, path: Path, width_in=3.4, height_in=None):
    """The cascade alone -- no side panel, no caption.

    One figure per file, and nothing on it that belongs in a LaTeX caption:
    what recall can and cannot be claimed, and how the validator was separately
    characterised, are prose about the figure rather than parts of it. Band
    titles stay, because without them the bars are unreadable on their own.
    """
    agg = collections.defaultdict(collections.Counter)
    for (_rm, k), c in stats.items():
        agg[k].update(c)
    tot = collections.Counter()
    for c in agg.values():
        tot.update(c)

    W = width_in * 72.0
    ml, mr = 14.0, 8.0
    pw = W - ml - mr
    # Explicit vertical spacing. An earlier version advanced by a single
    # constant and put the next band's title exactly where the last legend row
    # sat, so they overlapped; each gap is now named, and the page height is
    # computed from them rather than guessed.
    bh = 21.0          # bar height
    TOP_PAD = 16.0     # above the first title
    TITLE_GAP = 6.0    # title baseline to bar top
    LABEL_GAP = 13.0   # bar bottom to its labels
    BAND_GAP = 24.0    # labels of one band to the next band's title
    F_TITLE, F_LEG = 8.0, 7.6

    cats = [k for k in sorted(agg, key=lambda k: -agg[k]["remaining"])
            if agg[k]["remaining"]]
    stages_but_last = STAGE_BAND[:-1]
    # Every band labels through a legend row. In one column the narrow
    # segments -- disagreements are 6% of band one, 13pt of bar -- cannot hold
    # text, and silently skipping a label is what once left a 3,749-row stage
    # as an unexplained sliver.
    bands = [
        ("every structure fact the generator produced",
         [("agreed", tot["agreed"], AGREE_FILL, ()),
          ("disagreed", tot["disagreed"], DISAGREE_FILL, DISAGREE_HATCH)]),
        ("the disagreements, by the stage that dropped them",
         [(k, tot[k], STAGE_PAINT[i][0], STAGE_PAINT[i][1])
          for i, k in enumerate(stages_but_last)]
         + [("remaining", tot["remaining"], ZOOM_FILL, ZOOM_HATCH)]),
        ("judgement by reviewer: FP | TP",   # rendered with colour boxes via _title_boxes
         [(k, agg[k]["remaining"], CAT_FILL, CAT_HATCH[i % len(CAT_HATCH)])
          for i, k in enumerate(cats)]),
    ]

    def legend_texts(segs):
        return [(c, h, "%s %s" % (BAND_LABEL.get(k, k), "{:,}".format(n)))
                for k, n, c, h in segs]

    # The last band's legend is per-attribute "FP | TP" counts; the others are the
    # generic stage labels. Build the actual items once so the height calc and the
    # drawing agree (the FP|TP text is longer than the generic label it replaces).
    def cat_items():
        return [("#d7dbe1", CAT_HATCH[i % len(CAT_HATCH)],
                 "%s %d | %d" % (BAND_LABEL.get(k, k),
                                 agg[k]["remaining_fp"], agg[k]["remaining_tp"]))
                for i, k in enumerate(cats)]
    band_legends = [cat_items() if bi == len(bands) - 1 else legend_texts(segs)
                    for bi, (_t, segs) in enumerate(bands)]

    def legend_rows(items):
        cx, rows = 0.0, 1
        for _c, _h, text in items:
            w = 7 + 4 + _HELV_ADV * F_LEG * len(text) + _LEG_TRAIL
            if cx + w > pw:
                rows += 1
                cx = 0.0
            cx += w
        return rows

    if height_in is None:
        need = TOP_PAD + F_TITLE + TITLE_GAP
        for i, (_ti, _segs) in enumerate(bands):
            need += bh + LABEL_GAP + (legend_rows(band_legends[i]) - 1) * (F_LEG + 4)
            need += BAND_GAP if i < len(bands) - 1 else 12.0
        H = need
    else:
        H = height_in * 72.0
    p = Pdf(W, H)

    top = H - TOP_PAD - TITLE_GAP - F_TITLE    # top edge of the first bar
    prev = None
    for bi, (title, segs) in enumerate(bands):
        total = sum(n for _k, n, _c, _h in segs)
        if not total:
            continue
        is_cat = bi == len(bands) - 1            # last band: split each category by TP/FP
        if is_cat:
            _title_boxes(p, ml + pw / 2, top + TITLE_GAP, F_TITLE,
                         "judgement by reviewer:  ", FP_FILL, "FP", TP_FILL, "TP")
        else:
            p.fill("#5c6675")
            p.text(ml + pw / 2, top + TITLE_GAP, title, F_TITLE, "F1", "middle")
        y = top - bh
        x = ml
        zoom = None
        if is_cat:
            fp_tot = sum(agg[k]["remaining_fp"] for k in cats)
            tp_tot = sum(agg[k]["remaining_tp"] for k in cats)
            grand = max(1, fp_tot + tp_tot)
            for fill, pick in ((FP_FILL, "remaining_fp"), (TP_FILL, "remaining_tp")):
                for i, k in enumerate(cats):
                    cnt = agg[k][pick]
                    if cnt <= 0:
                        continue
                    wsub = pw * cnt / grand
                    p.fill(fill)
                    p.stroke("#ffffff")
                    p.rect(x, y, wsub, bh, 0.7)
                    p.hatch(x, y, wsub, bh, CAT_HATCH[i % len(CAT_HATCH)])
                    x += wsub
            seam = ml + pw * fp_tot / grand   # FP | TP boundary, drawn on top
            p.stroke(DIVIDER)
            p.line(seam, y, seam, y + bh, 1.8)
        else:
            for k, n, col, hat in segs:
                wseg = max(0.9, pw * n / total)
                p.fill(col)
                p.stroke("#ffffff")
                p.rect(x, y, wseg, bh, 0.7)
                p.hatch(x, y, wseg, bh, hat)
                if k in ("disagreed", "remaining"):
                    zoom = (x, x + wseg)
                x += wseg
        if prev is not None:
            p.stroke("#c0c7d2")
            p.line(prev[0], prev[1], ml, top, 0.5)
            p.line(prev[2], prev[1], ml + pw, top, 0.5)
        bottom = _legend_row(p, ml, y - LABEL_GAP, band_legends[bi], pw, size=F_LEG)
        prev = (zoom[0], bottom, zoom[1]) if zoom else None
        top = bottom - BAND_GAP

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(p.to_bytes())


def write_agreement(stats, level, path: Path, width_in=7.0, height_in=1.9):
    """Agreement per attribute, on its own."""
    agg = collections.defaultdict(collections.Counter)
    for (_rm, k), c in stats.items():
        agg[k].update(c)
    tot = collections.Counter()
    for c in agg.values():
        tot.update(c)

    W, H = width_in * 72.0, height_in * 72.0
    p = Pdf(W, H)
    ml, mr = 22.0, 10.0
    pw = W - ml - mr
    order = [k for k in sorted(agg, key=lambda k: -(agg[k]["agreed"]
                                                    / max(1, agg[k]["generated"])))
             if agg[k]["generated"]]
    lblw, plw = 66.0, pw - 66.0 - 78
    y = H - 22
    for k in order:
        g = agg[k]["generated"]
        a = agg[k]["agreed"] / g
        p.fill("#5c6675")
        p.text(ml, y, k, 6.4, "F1")
        p.fill(AGREE_FILL)
        p.stroke("#ffffff")
        p.rect(ml + lblw, y - 2, max(0.6, plw * a), 8.0, 0.5)
        p.fill("#1b212b")
        p.text(ml + lblw + plw + 4, y, "%.1f%%" % (a * 100), 6.4, "F1")
        p.fill("#929baa")
        p.text(ml + lblw + plw + 30, y, "of %s emitted" % "{:,}".format(g),
               5.8, "F1")
        y -= 15
    p.fill("#5c6675")
    p.text(ml, y - 1, "%s facts compared with the SVD, %s agree (%.1f%%)"
           % ("{:,}".format(tot["generated"]), "{:,}".format(tot["agreed"]),
              tot["agreed"] / tot["generated"] * 100), 6.2, "F1")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(p.to_bytes())



if __name__ == "__main__":
    main()
