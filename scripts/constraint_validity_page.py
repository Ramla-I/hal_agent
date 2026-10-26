#!/usr/bin/env python3
"""Per-manual constraint validity, as a browsable page.

Rebuilt as a generator. The previous version of this page was written by hand,
so it could not be regenerated and drifted out of date the moment the review
files changed -- which they did when the `sec` peripheral re-attribution
removed 571 duplicate constraints and re-attributed 661 more.

Everything here is read from the injection reports through
stm_constraint_statistics, so the two never disagree: same stages, same roles,
same annotation handling.

WHAT THE PAGE SEPARATES, AND WHY

A constraint can fail for two unrelated reasons and reporting them as one
number blames extraction for what is really coverage:

  VALIDITY      is the constraint true? A fact about the manual and our
                reading of it -- collection rejects, the quote-anchor gate,
                and the closed-book judge.
  APPLICABILITY can it be enforced on this chip crate? A fact about the crate
                and the emitter. A rule can be perfectly true and still have
                nowhere to land: the peripheral is absent from this part, or
                its grammar kind has no emitter yet.

Usage:
    python scripts/constraint_validity_page.py
    python scripts/constraint_validity_page.py --out docs/constraint_validity.html
"""

import argparse
import html
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import stm_constraint_statistics as S            # noqa: E402

DEFAULT_OUT = REPO / "docs" / "constraint_validity.html"

VALIDITY = [k for k, v in S.STAGE_ROLE.items() if v == "validity"]
APPLIC = [k for k, v in S.STAGE_ROLE.items() if v == "applicability"]


def _e(x):
    return html.escape(str(x), quote=True)


def build(per: dict) -> str:
    tot, total, invalid, inapplicable, emitted = S.roll(per)
    valid = total - invalid

    rows = []
    for rm in sorted(per):
        c = per[rm]
        n = sum(v for k, v in c.items() if k not in S.ANNOTATION_FATES)
        inv = sum(c.get(k, 0) for k in VALIDITY)
        ina = sum(c.get(k, 0) for k in APPLIC)
        ok = c.get("planned", 0)
        rows.append((rm, n, inv, n - inv, ina, ok))

    h = [f"""<style>
:root{{--bg:#f7f6f3;--surface:#fff;--surface-2:#efeee9;--ink:#1a1c20;
--ink-2:#5d6169;--ink-3:#8b8f97;--rule:#e4e3de;--accent:#2f5d50;
--invalid:#a4462d;--inapplic:#b8862b;--ok:#2f5d50;--shadow:rgba(26,28,32,.10)}}
@media (prefers-color-scheme:dark){{:root{{--bg:#131417;--surface:#191b1f;
--surface-2:#1f2126;--ink:#e9e8e4;--ink-2:#a5a9b0;--ink-3:#767b83;
--rule:#2b2d33;--accent:#7cb3a1;--invalid:#dd8f72;--inapplic:#d7b25e;
--ok:#7cb3a1;--shadow:rgba(0,0,0,.5)}}}}
:root[data-theme="dark"]{{--bg:#131417;--surface:#191b1f;--surface-2:#1f2126;
--ink:#e9e8e4;--ink-2:#a5a9b0;--ink-3:#767b83;--rule:#2b2d33;--accent:#7cb3a1;
--invalid:#dd8f72;--inapplic:#d7b25e;--ok:#7cb3a1;--shadow:rgba(0,0,0,.5)}}
:root[data-theme="light"]{{--bg:#f7f6f3;--surface:#fff;--surface-2:#efeee9;
--ink:#1a1c20;--ink-2:#5d6169;--ink-3:#8b8f97;--rule:#e4e3de;--accent:#2f5d50;
--invalid:#a4462d;--inapplic:#b8862b;--ok:#2f5d50;--shadow:rgba(26,28,32,.10)}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
.wrap{{max-width:62rem;margin:0 auto;padding:3.5rem 1.5rem 5rem}}
header{{border-bottom:1px solid var(--rule);padding-bottom:1.6rem;margin-bottom:2.2rem}}
.eyebrow{{font:600 11.5px/1 ui-monospace,Menlo,monospace;letter-spacing:.14em;
text-transform:uppercase;color:var(--ink-3)}}
h1{{font-family:Georgia,"Iowan Old Style",serif;font-weight:600;
font-size:clamp(1.85rem,4.2vw,2.6rem);line-height:1.15;margin:.7rem 0 .5rem;
letter-spacing:-.012em;text-wrap:balance}}
.sub{{color:var(--ink-2);max-width:62ch;margin:0}}
h2{{font-family:Georgia,serif;font-weight:600;font-size:1.35rem;margin:2.6rem 0 .8rem}}
p{{max-width:66ch}}
code{{font-family:ui-monospace,Menlo,monospace;font-size:.87em;
background:var(--surface-2);padding:.1em .32em;border-radius:3px}}
.stats{{display:flex;flex-wrap:wrap;gap:.7rem;margin-top:1.6rem}}
.stat{{background:var(--surface);border:1px solid var(--rule);border-radius:7px;
padding:.65rem 1rem;min-width:8rem;box-shadow:0 1px 2px var(--shadow)}}
.stat .k{{display:block;font-size:.71rem;letter-spacing:.06em;text-transform:uppercase;
color:var(--ink-3);font-weight:600}}
.stat .v{{display:block;font:650 1.45rem/1.2 ui-monospace,Menlo,monospace;
font-variant-numeric:tabular-nums;margin-top:.15rem}}
.stat.bad .v{{color:var(--invalid)}} .stat.warn .v{{color:var(--inapplic)}}
.stat.good .v{{color:var(--ok)}}
.bar{{display:flex;height:12px;border-radius:6px;overflow:hidden;margin:.35rem 0 0;
background:var(--surface-2);min-width:8rem}}
.bar i{{display:block;height:100%}}
.bar .v1{{background:var(--invalid)}} .bar .v2{{background:var(--inapplic)}}
.bar .v3{{background:var(--ok)}}
.scroll{{overflow-x:auto;border:1px solid var(--rule);border-radius:8px;
background:var(--surface);box-shadow:0 1px 2px var(--shadow)}}
table{{border-collapse:collapse;width:100%;font-size:.9rem;min-width:40rem}}
th,td{{text-align:left;padding:.55rem .8rem;border-bottom:1px solid var(--rule)}}
thead th{{background:var(--surface-2);font-size:.71rem;letter-spacing:.07em;
text-transform:uppercase;color:var(--ink-2);font-weight:650;white-space:nowrap}}
tbody tr:last-child td{{border-bottom:none}}
tbody tr:hover td{{background:var(--surface-2)}}
td.rm{{font-family:ui-monospace,Menlo,monospace;font-weight:600}}
td.n{{text-align:right;font-family:ui-monospace,Menlo,monospace;
font-variant-numeric:tabular-nums;white-space:nowrap}}
td.n.bad{{color:var(--invalid)}} td.n.warn{{color:var(--inapplic)}}
td.n.good{{color:var(--ok);font-weight:650}}
tfoot td{{border-top:2px solid var(--accent);background:var(--surface-2);font-weight:650}}
.note{{border-left:3px solid var(--accent);background:var(--surface);
padding:.85rem 1.05rem;border-radius:0 7px 7px 0;margin:1rem 0;
box-shadow:0 1px 2px var(--shadow)}}
.note p{{margin:0;max-width:none}}
footer{{margin-top:3rem;padding-top:1.4rem;border-top:1px solid var(--rule);
color:var(--ink-3);font-size:.83rem}}
</style>

<div class="wrap">
<header>
  <span class="eyebrow">LIDAR &middot; enforcement arm</span>
  <h1>Constraint validity by reference manual</h1>
  <p class="sub">Every access constraint the generator extracted from {len(per)}
  ST reference manuals, followed through two questions that are often
  conflated: is it <em>true</em>, and can it be <em>enforced</em> on this chip
  crate. Read from the injection reports, not transcribed.</p>
  <div class="stats">
    <div class="stat"><span class="k">extracted</span><span class="v">{total:,}</span></div>
    <div class="stat bad"><span class="k">failed validity</span><span class="v">{invalid:,}</span></div>
    <div class="stat"><span class="k">valid</span><span class="v">{valid:,}</span></div>
    <div class="stat warn"><span class="k">not applicable</span><span class="v">{inapplicable:,}</span></div>
    <div class="stat good"><span class="k">gate emitted</span><span class="v">{emitted:,}</span></div>
  </div>
</header>

<h2>Two questions, not one</h2>
<p><b>Validity</b> is a fact about the manual and our reading of it: a
constraint rejected at collection, one whose quoted sentence could not be tied
to the register it constrains, or one the closed-book judge read against the
datasheet and declined. <b>Applicability</b> is a fact about the chip crate and
the code generator: a rule can be perfectly true and still have nowhere to
land, because the peripheral is absent from this part or its grammar kind has
no emitter yet.</p>
<div class="note"><p>Reporting them as one number would blame extraction for
what is really coverage. {inapplicable:,} of the {valid:,} constraints that
survived validity were never <em>wrong</em> &mdash; they had nowhere to go.</p></div>

<h2>Per manual</h2>
<div class="scroll"><table>
<thead><tr><th>RM</th><th>extracted</th><th>failed validity</th><th>valid</th>
<th>not applicable</th><th>gate emitted</th><th>shape</th></tr></thead><tbody>"""]

    for rm, n, inv, val, ina, ok in rows:
        w = max(n, 1)
        h.append(
            f'<tr><td class="rm">{_e(rm)}</td>'
            f'<td class="n">{n:,}</td>'
            f'<td class="n bad">{inv:,}</td>'
            f'<td class="n">{val:,}</td>'
            f'<td class="n warn">{ina:,}</td>'
            f'<td class="n good">{ok:,}</td>'
            f'<td><span class="bar">'
            f'<i class="v1" style="width:{100*inv/w:.1f}%"></i>'
            f'<i class="v2" style="width:{100*ina/w:.1f}%"></i>'
            f'<i class="v3" style="width:{100*ok/w:.1f}%"></i>'
            f'</span></td></tr>')

    h.append(
        f'</tbody><tfoot><tr><td class="rm">TOTAL</td>'
        f'<td class="n">{total:,}</td><td class="n bad">{invalid:,}</td>'
        f'<td class="n">{valid:,}</td><td class="n warn">{inapplicable:,}</td>'
        f'<td class="n good">{emitted:,}</td><td></td></tr></tfoot></table></div>')

    h.append("<h2>Where constraints are lost, corpus-wide</h2>"
             '<div class="scroll"><table><thead><tr><th>stage</th><th>role</th>'
             "<th>count</th></tr></thead><tbody>")
    order = [k for k in S.ORDER if k in tot] if hasattr(S, "ORDER") else list(tot)
    for k in sorted(tot, key=lambda x: -tot[x]):
        role = ("annotation" if k in S.ANNOTATION_FATES
                else S.STAGE_ROLE.get(k, "?"))
        cls = {"validity": "bad", "applicability": "warn",
               "success": "good"}.get(role, "")
        h.append(f'<tr><td>{_e(S.LABEL.get(k, k))}</td><td>{_e(role)}</td>'
                 f'<td class="n {cls}">{tot[k]:,}</td></tr>')
    h.append("</tbody></table></div>")
    h.append('<div class="note"><p><b>Annotation rows are not constraints.</b> '
             "The injector writes one row per colliding or merged instance "
             "group describing what happened to the constraints beside it. "
             "They are listed for completeness and excluded from every total "
             "on this page.</p></div>")

    h.append("<footer>Generated by <code>scripts/constraint_validity_page.py</code> "
             "from the injection reports in "
             "<code>applications/pac_codegen/experiments/out/</code>; stage "
             "roles shared with <code>scripts/stm_constraint_statistics.py</code>."
             "</footer></div>")
    return "\n".join(h)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reports", default=str(S.REPORTS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    per, unknown = S.collect(Path(args.reports))
    if not per:
        sys.exit(f"no injection reports in {args.reports}")
    if unknown:
        sys.exit(f"unclassified stages, refusing to publish a wrong page: "
                 f"{sorted(unknown)}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(per) + "\n")
    print(f"html: {out}  ({out.stat().st_size // 1024} KB, {len(per)} manuals)")


if __name__ == "__main__":
    main()
