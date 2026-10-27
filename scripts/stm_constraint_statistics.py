#!/usr/bin/env python3
"""Whole-corpus access-constraint statistics, and the cascade figure.

Counts every constraint the Generator extracted from a reference manual and
follows it through two questions: is the constraint TRUE, and can it be
ENFORCED on this chip crate. Raw numbers only in the table -- ratios are
chosen afterwards.

    python scripts/stm_constraint_statistics.py
    python scripts/stm_constraint_statistics.py --by-rm
    python scripts/stm_constraint_statistics.py --cascade-figure
    python scripts/stm_constraint_statistics.py --csv out.csv

NOTHING IS HARDCODED. Stages are discovered from the injection reports, and
each is classified by which of the two questions it answers (see STAGE_ROLE);
an unrecognised stage is reported rather than silently binned.

THE TWO QUESTIONS ARE DIFFERENT KINDS OF CLAIM, which is why the cascade
separates them. Whether a constraint is true is a fact about the manual and
our reading of it. Whether it can be enforced is a fact about the chip crate
and the code generator -- a rule can be perfectly true and still have nowhere
to land, because the peripheral is absent from this part or its grammar kind
has no emitter yet. Reporting them as one number would blame extraction for
what is really coverage.

  VALIDITY, in the order a constraint meets them
    rejected at collection  could not be turned into a gate at all: no
                            precondition to check, a field name that is not an
                            SVD identifier, a register resolving nowhere
    failed quote anchor     the target-location gate -- the quoted sentence
                            could not be tied to the register it constrains
    gated out by validator  the closed-book judge read it against the datasheet
                            and returned a verdict other than enforce

  APPLICABILITY, for constraints that survived all three
    kind not emitted        a grammar kind with no code generator yet
    field gating disabled   field-scoped, and field-level gating is opt-in
    peripheral not in device this chip crate has no such peripheral
    pruned for device       the register or field is absent from this part
    instance conflict       sibling instances disagree, so the group is dropped
    emitter rejected        the emitter could not build a witness for it
"""

import argparse
import collections
import csv
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pdfwriter import Pdf, _HELV_ADV  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
REPORTS = REPO / "applications" / "pac_codegen" / "experiments" / "out"
DEFAULT_CASCADE = REPO / "docs" / "figures" / "constraint_cascade.pdf"

# Which question each stage answers. "success" is the one that got a gate.
# Fates that are ANNOTATIONS about a group of constraints, not constraints.
# `inject_from_run` writes one of these per colliding or merged instance group,
# with an empty `constraints` list, alongside the per-constraint rows that
# record what actually happened. Counting them as constraints inflates both the
# total and the applicability loss -- RM0433 has one `instance_conflict` row
# describing the two `instance_conflict_dropped` constraints beside it. They
# are reported separately rather than binned.
ANNOTATION_FATES = {"instance_conflict", "instance_merged_for_review"}

STAGE_ROLE = {
    "rejected_at_collection":        "validity",
    "target_unverified_by_location": "validity",
    "gated_out_by_validator":        "validity",
    "kind_not_emitted":              "applicability",
    "field_gating_disabled":         "applicability",
    "peripheral_not_in_device":      "applicability",
    "pruned_for_device":             "applicability",
    "instance_conflict_dropped":     "applicability",
    "emitter_rejected":              "applicability",
    "unsupported_by_emitter":        "applicability",
    "planned":                       "success",
}
LABEL = {
    "rejected_at_collection": "rejected at collection",
    "target_unverified_by_location": "failed quote anchor",
    "gated_out_by_validator": "gated out by validator",
    "kind_not_emitted": "kind not emitted",
    "field_gating_disabled": "field gating disabled",
    "instance_merged_for_review": "instance merge (note only)",
    "instance_conflict": "instance conflict (note only)",
    "peripheral_not_in_device": "peripheral not on chip",
    "pruned_for_device": "pruned for device",
    "instance_conflict_dropped": "instance conflict",
    "emitter_rejected": "emitter rejected",
    "unsupported_by_emitter": "unsupported by emitter",
    "planned": "gate emitted",
}

# Green marks the outcome that SURVIVES a band, not the segment the next band
# magnifies -- those differ here. Band three opens band two's failure segment,
# not its success, so the nesting is carried by the connector lines and an
# explicit per-segment flag rather than by hue. Overloading green to mean both
# "good" and "expanded next" would have made "gate emitted" and "cannot be
# applied" fight for it.
#
# Band three is a light tint of the BLUE it magnifies, for the same reason.
KEEP_FILL, KEEP_HATCH = "#1baf7a", (135,)
DROP_FILL, DROP_HATCH = "#2a78d6", (45,)
CAT_FILL = "#b8d4f0"
PAINT = [("#a3c8ee", ()), ("#eb6834", (45,)), ("#eda100", (45, 135)),
         ("#e87ba4", (90,)), ("#4a3aa7", (0,)), ("#e34948", (0, 90))]
# Eight, because the applicability band has seven segments and a modulo wrap
# put two of them in the same fill AND the same texture -- indistinguishable.
# _paint_cat asserts rather than wrapping, so growing the pipeline a fate
# fails loudly instead of silently drawing two segments identically.
CAT_HATCH = [(), (45,), (135,), (45, 135), (90,), (0,), (0, 90), (45, 90)]


def _paint_cat(i):
    if i >= len(CAT_HATCH):
        raise ValueError(
            f"{i + 1} applicability segments but only {len(CAT_HATCH)} "
            "distinct textures; add one to CAT_HATCH")
    return CAT_FILL, CAT_HATCH[i]

_RM_RE = re.compile(r"(rm\d{4})_(\w+)\.json$")


def collect(reports_dir: Path):
    """(rm -> Counter of stages). One report per manual: where a manual was
    injected into more than one chip the larger report wins, since the
    extraction side is identical and the bigger one resolved more of it."""
    per, unknown = {}, set()
    for f in sorted(reports_dir.glob("rm*_stm32*.json")):
        if "_dry" in f.name:
            continue
        m = _RM_RE.search(f.name)
        if not m:
            continue
        try:
            d = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        c = collections.Counter(r.get("fate") for r in d.get("rows", []))
        if not c:
            continue
        unknown |= {k for k in c if k not in STAGE_ROLE
                    and k not in ANNOTATION_FATES}
        rm = m.group(1)
        if rm not in per or sum(c.values()) > sum(per[rm].values()):
            per[rm] = c
    return per, unknown


def roll(per):
    """Totals, plus the three chained quantities the cascade needs.

    Annotation fates are excluded from every figure here: they describe a
    group of constraints rather than being one, so counting them inflates the
    total and the applicability loss alike."""
    tot = collections.Counter()
    for c in per.values():
        tot.update(c)
    total = sum(n for k, n in tot.items() if k not in ANNOTATION_FATES)
    invalid = sum(n for k, n in tot.items() if STAGE_ROLE.get(k) == "validity")
    inapplicable = sum(n for k, n in tot.items()
                       if STAGE_ROLE.get(k) == "applicability")
    emitted = tot["planned"]
    return tot, total, invalid, inapplicable, emitted


ORDER = ["rejected_at_collection", "target_unverified_by_location",
         "gated_out_by_validator", "kind_not_emitted", "field_gating_disabled",
         "peripheral_not_in_device", "pruned_for_device",
         "instance_conflict_dropped", "instance_conflict", "emitter_rejected",
         "unsupported_by_emitter", "planned"]


def emit_table(per, by_rm, out_csv):
    tot, total, invalid, inapplicable, emitted = roll(per)
    keys = [k for k in ORDER if tot[k]] + [k for k in tot if k not in ORDER]
    if by_rm:
        head = ["rm", "total"] + keys
        rows = [[rm, sum(c.values())] + [c[k] for k in keys]
                for rm, c in sorted(per.items())]
    else:
        head = ["stage", "role", "n"]
        rows = [[LABEL.get(k, k),
                 "annotation" if k in ANNOTATION_FATES else STAGE_ROLE.get(k, "?"),
                 tot[k]] for k in keys]
        rows.append(["TOTAL", "", total])
    w = [max(len(str(r[i])) for r in [head] + rows) for i in range(len(head))]
    print("  ".join(h.ljust(w[i]) if i < 2 else h.rjust(w[i])
                    for i, h in enumerate(head)))
    for r in rows:
        print("  ".join(str(v).ljust(w[i]) if i < 2 else str(v).rjust(w[i])
                        for i, v in enumerate(r)))
    print(f"\n  extracted           {total:>7,}")
    print(f"  failed validity     {invalid:>7,}")
    print(f"  valid               {total - invalid:>7,}")
    print(f"  not applicable      {inapplicable:>7,}")
    print(f"  gate emitted        {emitted:>7,}")
    if out_csv:
        with open(out_csv, "w", newline="") as fh:
            wr = csv.writer(fh)
            wr.writerow(head)
            wr.writerows(rows)
        print(f"\ncsv: {out_csv}")


def _legend_row(p, x, y, items, width, size=7.6):
    """Swatch, name and count for every segment, wrapping within `width`.

    Every band labels this way rather than writing inside the bars: at one
    column a segment worth a few hundred rows is a few points wide and cannot
    hold text, and skipping the label of whatever does not fit is how a stage
    ends up on a figure as an unexplained sliver."""
    cx, cy = x, y
    for col, hat, text in items:
        w = 7 + 4 + _HELV_ADV * size * len(text) + 12
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


def write_cascade(per, path: Path, width_in=3.4, height_in=None):
    tot, total, invalid, inapplicable, emitted = roll(per)
    valid = total - invalid

    W = width_in * 72.0
    ml, mr = 14.0, 8.0
    pw = W - ml - mr
    bh = 21.0
    TOP_PAD, TITLE_GAP, LABEL_GAP, BAND_GAP = 16.0, 6.0, 13.0, 24.0
    F_TITLE, F_LEG = 8.0, 7.6

    # Merge stages that share a display label -- instance_conflict and
    # instance_conflict_dropped both read "instance conflict", and as separate
    # segments the legend listed that name twice with two different counts,
    # which looks like an error in the figure rather than two fates of one
    # cause.
    merged = collections.Counter()
    for k in ORDER:
        if STAGE_ROLE.get(k) == "applicability" and tot[k]:
            merged[LABEL.get(k, k)] += tot[k]
    # (label, n, fill, hatch, is_zoom_target)
    v_keys = [k for k in ORDER if STAGE_ROLE.get(k) == "validity" and tot[k]]
    bands = [
        ("every constraint extracted",
         [(LABEL.get(k, k), tot[k], PAINT[i][0], PAINT[i][1], False)
          for i, k in enumerate(v_keys)]
         + [("holds up", valid, KEEP_FILL, KEEP_HATCH, True)]),
        ("of those that hold up, what can be enforced",
         [("cannot be applied", inapplicable, DROP_FILL, DROP_HATCH, True),
          ("gate emitted", emitted, KEEP_FILL, KEEP_HATCH, False)]),
        ("why a valid constraint could not be applied",
         [(nm, n, *_paint_cat(i), False)
          for i, (nm, n) in enumerate(merged.most_common())]),
    ]

    def texts(segs):
        return [(c, h, "%s %s" % (nm, "{:,}".format(n)))
                for nm, n, c, h, _z in segs]

    def rows_needed(segs):
        cx, rows = 0.0, 1
        for _c, _h, text in texts(segs):
            w = 7 + 4 + _HELV_ADV * F_LEG * len(text) + 12
            if cx + w > pw:
                rows += 1
                cx = 0.0
            cx += w
        return rows

    if height_in is None:
        need = TOP_PAD + F_TITLE + TITLE_GAP
        for i, (_t, segs) in enumerate(bands):
            need += bh + LABEL_GAP + (rows_needed(segs) - 1) * (F_LEG + 4)
            need += BAND_GAP if i < len(bands) - 1 else 12.0
        H = need
    else:
        H = height_in * 72.0
    p = Pdf(W, H)

    top = H - TOP_PAD - TITLE_GAP - F_TITLE
    prev = None
    for title, segs in bands:
        band_total = sum(n for _nm, n, _c, _h, _z in segs)
        if not band_total:
            continue
        p.fill("#5c6675")
        p.text(ml + pw, top + TITLE_GAP, title, F_TITLE, "F1", "end")
        y = top - bh
        x = ml
        zoom = None
        for nm, n, col, hat, is_zoom in segs:
            wseg = max(0.9, pw * n / band_total)
            p.fill(col)
            p.stroke("#ffffff")
            p.rect(x, y, wseg, bh, 0.7)
            p.hatch(x, y, wseg, bh, hat)
            if is_zoom:
                zoom = (x, x + wseg)
            x += wseg
        if prev is not None:
            p.stroke("#c0c7d2")
            p.line(prev[0], prev[1], ml, top, 0.5)
            p.line(prev[2], prev[1], ml + pw, top, 0.5)
        bottom = _legend_row(p, ml, y - LABEL_GAP, texts(segs), pw, size=F_LEG)
        prev = (zoom[0], bottom, zoom[1]) if zoom else None
        top = bottom - BAND_GAP

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(p.to_bytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reports", default=str(REPORTS),
                    help="directory of <rm>_<device>.json injection reports")
    ap.add_argument("--by-rm", action="store_true")
    ap.add_argument("--csv", default=None)
    ap.add_argument("--cascade-figure", nargs="?", const=str(DEFAULT_CASCADE),
                    default=None, help="write the cascade figure")
    ap.add_argument("--width-in", type=float, default=3.4)
    ap.add_argument("--height-in", type=float, default=None)
    args = ap.parse_args()

    per, unknown = collect(Path(args.reports))
    if not per:
        sys.exit(f"no injection reports found in {args.reports}")
    if unknown:
        print(f"!! stages with no role assigned, excluded from the roll-up: "
              f"{sorted(unknown)}\n", file=sys.stderr)
    print(f"{len(per)} manuals\n")
    emit_table(per, args.by_rm, args.csv)
    if args.cascade_figure:
        fp = Path(args.cascade_figure)
        write_cascade(per, fp, args.width_in, args.height_in)
        print(f"\ncascade: {fp}")


if __name__ == "__main__":
    main()
