#!/usr/bin/env python3
"""landscape_page.py -- the project-landscape scan as a published page.

Reads out/scan_projects.json (and out/trace_hal.json, when present, for the
driver-only applications) and writes docs/project_landscape.html: a summary
table over every project scanned, then one section per project listing its
candidate sites with the datasheet sentence each one is measured against.

Sibling of docs/injection_tracking.html and deliberately shares its tokens --
same neutrals, same copper accent -- so the two read as one series. The one
addition is semantic colour for the triage verdict: amber for `unchecked`
(a candidate) and green for `corroborated` (the project already performs the
datasheet check). Those never double as the accent.

Usage:
    python applications/pac_codegen/experiments/landscape_page.py
"""

import argparse
import functools
import html
import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
OUT = APP_DIR / "experiments" / "out"
DOC = APP_DIR.parent.parent / "docs" / "project_landscape.html"

STYLE_LABEL = {
    "pac_direct": "talks to the chip crate directly",
    "tock": "hand-written register maps",
    "hal_only": "everything through a driver",
}
EFFORT_CLASS = {"measured": "ok", "ready": "ok", "hal-bump": "warn",
                "pac-gap": "warn", "missing-manual": "no",
                "not-applicable": "none"}


@functools.lru_cache(maxsize=1)
def measured_projects() -> dict:
    """Projects that were taken past the scan and actually compiled.

    A scan can only say a project is `pac-gap`; it cannot say whether that gap
    is an afternoon or a quarter. Where a harness has since closed one, the row
    should report what the compiler found instead of what the scan guessed."""
    out = {}
    pth = OUT / "port_hubris.json"
    if pth.is_file():
        r = json.loads(pth.read_text())
        if r.get("baseline") == "PASS" and "gate_fired" in r:
            out[r["project"]] = r
    return out


def _e(x) -> str:
    return html.escape(str(x if x is not None else ""), quote=True)


CSS = """
:root{
  --ground:#f6f7f9; --surface:#ffffff; --surface-2:#f0f2f6;
  --ink:#1b212b; --ink-dim:#5c6675; --rule:#dde2e9;
  --accent:#a85b2a; --accent-soft:#f3e6dc;
  --ok:#2e7d5b; --warn:#8a6a12; --drop:#a8443a;
  --shadow:rgba(27,33,43,.13);
}
@media (prefers-color-scheme: dark){
  :root{
    --ground:#10131a; --surface:#171b23; --surface-2:#1d222c;
    --ink:#e2e7ef; --ink-dim:#929baa; --rule:#262c37;
    --accent:#d8834a; --accent-soft:#2a1d14;
    --ok:#5cbb8d; --warn:#d0a83c; --drop:#e08074;
    --shadow:rgba(0,0,0,.5);
  }
}
:root[data-theme="dark"]{
  --ground:#10131a; --surface:#171b23; --surface-2:#1d222c;
  --ink:#e2e7ef; --ink-dim:#929baa; --rule:#262c37;
  --accent:#d8834a; --accent-soft:#2a1d14;
  --ok:#5cbb8d; --warn:#d0a83c; --drop:#e08074;
  --shadow:rgba(0,0,0,.5);
}
:root[data-theme="light"]{
  --ground:#f6f7f9; --surface:#ffffff; --surface-2:#f0f2f6;
  --ink:#1b212b; --ink-dim:#5c6675; --rule:#dde2e9;
  --accent:#a85b2a; --accent-soft:#f3e6dc;
  --ok:#2e7d5b; --warn:#8a6a12; --drop:#a8443a;
  --shadow:rgba(27,33,43,.13);
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  font-size:15px; line-height:1.55; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1180px;margin:0 auto;padding:40px 24px 72px;
      display:flex;flex-direction:column;gap:38px}
header{display:flex;flex-direction:column;gap:10px;
       border-left:3px solid var(--accent);padding-left:16px}
h1{margin:0;font-size:27px;line-height:1.2;letter-spacing:-.015em;
   text-wrap:balance;font-weight:640}
.sub{margin:0;color:var(--ink-dim);max-width:68ch}
.eyebrow{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:11px;letter-spacing:.13em;text-transform:uppercase;color:var(--accent);}
section{display:flex;flex-direction:column;gap:12px}
h2{margin:0;font-size:17px;font-weight:640;letter-spacing:-.01em}
h3{margin:26px 0 0;font-size:15.5px;font-weight:640;letter-spacing:-.005em;
   display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
h3 .sm{font-size:12.5px;font-weight:400;color:var(--ink-dim)}
.note{margin:0;color:var(--ink-dim);font-size:13.5px;max-width:76ch}
.row{display:flex;flex-wrap:wrap;gap:10px}
.stat{background:var(--surface);border:1px solid var(--rule);border-radius:7px;
      padding:11px 15px;min-width:124px;flex:1 1 124px}
.stat .k{display:block;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-dim)}
.stat .v{display:block;font-size:24px;font-weight:660;letter-spacing:-.02em;
  font-variant-numeric:tabular-nums;margin-top:3px}
.stat.hi .v{color:var(--accent)}
.stat.warn .v{color:var(--warn)}
.stat.ok .v{color:var(--ok)}
.scroll{overflow-x:auto;border:1px solid var(--rule);border-radius:8px;
        background:var(--surface)}
table{border-collapse:separate;border-spacing:0;width:max-content;min-width:100%}
th,td{padding:9px 13px;text-align:left;white-space:nowrap;
  border-bottom:1px solid var(--rule);font-size:13px;vertical-align:top}
thead th{position:sticky;top:0;z-index:2;background:var(--surface-2);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;
  color:var(--ink-dim);font-weight:600}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:var(--surface-2)}
th.pin,td.pin{position:sticky;left:0;z-index:1;background:var(--surface);
  box-shadow:1px 0 0 var(--rule),6px 0 10px -8px var(--shadow);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-weight:600}
thead th.pin{z-index:3;background:var(--surface-2)}
tbody tr:hover td.pin{background:var(--surface-2)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px}
.num{text-align:right;font-variant-numeric:tabular-nums;
     font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.num.lead{font-weight:680;color:var(--accent)}
.dim{color:var(--ink-dim)}
.pill{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11px;
  font-weight:640;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  letter-spacing:.02em}
.pill.ok{color:var(--ok);background:color-mix(in srgb,var(--ok) 13%,transparent)}
.pill.warn{color:var(--warn);background:color-mix(in srgb,var(--warn) 15%,transparent)}
.pill.no{color:var(--drop);background:color-mix(in srgb,var(--drop) 13%,transparent)}
.pill.none{color:var(--ink-dim);background:var(--surface-2)}
.rule{background:var(--surface);border:1px solid var(--rule);border-left:3px solid var(--accent);
      border-radius:0 8px 8px 0;padding:13px 16px;display:flex;flex-direction:column;gap:7px}
.rule .hd{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:12.5px;font-weight:640}
.rule .meta{font-size:12px;color:var(--ink-dim);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.quote{margin:0;font-size:13.5px;line-height:1.55;color:var(--ink);
  border-left:2px solid var(--rule);padding-left:12px;max-width:80ch}
.quote .who{display:block;font-size:11px;color:var(--ink-dim);margin-top:5px;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.06em}
.proj{display:flex;flex-direction:column;gap:14px;padding-top:6px}
.card{background:var(--surface);border:1px solid var(--rule);border-radius:8px;
      padding:14px 16px;display:flex;flex-direction:column;gap:8px}
.card h4{margin:0;font-size:13.5px;font-weight:640}
.card p{margin:0;font-size:13px;color:var(--ink-dim);max-width:78ch}
td.wide{white-space:normal;min-width:300px;max-width:460px;color:var(--ink-dim);
        font-size:12.5px;line-height:1.5}
footer{color:var(--ink-dim);font-size:12.5px;border-top:1px solid var(--rule);
       padding-top:16px;display:flex;flex-direction:column;gap:6px}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;
     background:var(--surface-2);padding:1px 5px;border-radius:4px}
a{color:var(--accent)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:640px){
  .wrap{padding:26px 14px 56px;gap:28px}
  h1{font-size:22px}
}
"""


def verdict_pill(v: str) -> str:
    cls = {"unchecked": "warn", "corroborated": "ok"}.get(v, "none")
    return f'<span class="pill {cls}">{_e(v)}</span>'


def group_findings(findings: list) -> dict:
    """(peripheral, register) -> {constraint, sites}. One card per rule."""
    out = {}
    for f in findings:
        key = (f["peripheral"], f["register"])
        rec = out.setdefault(key, {"c": f["constraints"][0], "sites": []})
        rec["sites"].append(f)
    return dict(sorted(out.items(), key=lambda kv: -len(kv[1]["sites"])))


def precond_text(c: dict) -> str:
    parts = []
    for p in c.get("preconditions") or []:
        reg, fld = p.get("register", ""), p.get("field", "")
        st = p.get("state") or (f"= {p['values']}" if p.get("values") else "")
        parts.append(f"{reg}.{fld} {st}".strip())
    return ", ".join(parts) or "—"


def project_section(p: dict, trace: dict) -> list:
    h = [f'<section id="{_e(p["name"])}">']
    h.append(f'<h3><a href="{_e(p["repo"])}">{_e(p["name"])}</a>'
             f'<span class="sm">{_e(STYLE_LABEL.get(p["style"], p["style"]))}'
             f' · {_e(", ".join(p["rms"]) or "no manual in corpus")}</span></h3>')
    h.append(f'<p class="note">{_e(p.get("note", ""))}</p>')

    v = p["verdicts"]
    h.append('<div class="row">')
    for k, label, cls in (
            ("rust_files", "source files", ""),
            ("register_accesses", "register accesses", ""),
            ("distinct_registers", "distinct registers", ""),
            ("constraints_available", "rules to check against", ""),
            ("hits", "candidate sites", "hi")):
        h.append(f'<div class="stat {cls}"><span class="k">{label}</span>'
                 f'<span class="v">{p[k]}</span></div>')
    h.append(f'<div class="stat warn"><span class="k">unchecked</span>'
             f'<span class="v">{v.get("unchecked", 0)}</span></div>')
    h.append(f'<div class="stat ok"><span class="k">corroborated</span>'
             f'<span class="v">{v.get("corroborated", 0)}</span></div>')
    h.append("</div>")

    r = p["readiness"]
    mm = measured_projects().get(p["name"])
    cls = EFFORT_CLASS.get("measured" if mm else r["effort"], "none")
    blockers = "; ".join(r["blockers"]) or "none"
    if mm:
        h.append(
            f'<p class="note"><span class="pill {cls}">measured</span> '
            f'&nbsp;{_e(r["pac_needed"])} &mdash; the scan called this '
            f'<em>{_e(r["effort"])}</em> ({_e(blockers)}); the gap was then '
            f'closed and the project built. One version line in the workspace '
            f'manifest plus {mm["mechanical_edits"]} mechanical edits, '
            f'baseline passing against the pristine crate, then '
            f'<b>{mm["gate_fired"]}</b> gate-fired sites across '
            f'{mm["registers_gated"]} gated registers with '
            f'{mm["collateral"]} collateral errors.</p>')
        h.append('<div class="card"><h4>What the compiler found</h4>'
                 '<div class="scroll"><table><thead><tr>'
                 '<th class="pin">site</th><th>register</th><th>operation</th>'
                 '<th>static verdict</th></tr></thead><tbody>')
        for hit in mm["hits"]:
            note = hit.get("triage_note")
            h.append(
                f'<tr><td class="pin mono">{_e(hit["file"])}:{hit["line"]}</td>'
                f'<td class="mono">{_e(hit["register"])}</td>'
                f'<td>{_e(hit["operation"])}</td>'
                f'<td>{_e(hit["verdict"])}'
                + (f' <span class="pill no">known wrong</span>' if note else "")
                + (f'<br><span class="dim">{_e(note)}</span>' if note else "")
                + "</td></tr>")
        h.append("</tbody></table></div>")
        if mm.get("triage_caveat"):
            h.append(f'<p class="note"><b>Read the verdicts with this in '
                     f'mind:</b> {_e(mm["triage_caveat"])}.</p>')
        h.append("</div>")
    else:
        h.append(
            f'<p class="note"><span class="pill {cls}">{_e(r["effort"])}</span> '
            f'&nbsp;{_e(r["pac_needed"] or "no chip crate to inject into")} '
            f'&mdash; {_e(blockers)}</p>')

    tr = trace.get(p["name"])
    if tr:
        h.append('<div class="card">')
        h.append("<h4>Traced through the driver</h4>")
        h.append(f'<p>Its own source touches no registers, so the question is '
                 f'whether a rule survives the driver. Of the driver entry '
                 f'points it calls that reach a gated register, '
                 f'<b>{tr["contained"]}</b> are absorbed inside a single call '
                 f'and <b>{tr["escaping"]}</b> would reach this application. '
                 + (f'Ambiguous method names, not claimed either way: '
                    f'<code>{_e(", ".join(tr["ambiguous"]))}</code>.'
                    if tr.get("ambiguous") else "") + "</p>")
        h.append("</div>")

    if not p["findings"]:
        h.append('<p class="note dim">No candidate sites.</p>')
        h.append("</section>")
        return h

    for (periph, reg), rec in group_findings(p["findings"]).items():
        c = rec["c"]
        h.append('<div class="rule">')
        h.append(f'<div class="hd">{_e(periph)}/{_e(reg)} '
                 f'<span class="dim">&mdash; {len(rec["sites"])} site'
                 f'{"s" if len(rec["sites"]) != 1 else ""}</span></div>')
        h.append(f'<div class="meta">{_e(c["kind"])} · {_e(c["operation"])} · '
                 f'requires {_e(precond_text(c))} · fields restricted: '
                 f'{_e(", ".join(c.get("fields") or []) or "whole register")}</div>')
        h.append(f'<p class="quote">{_e(" ".join((c.get("quote") or "").split()))}'
                 f'<span class="who">{_e(c["rm"])}</span></p>')
        h.append('<div class="scroll"><table><thead><tr>'
                 '<th class="pin">file:line</th><th>op</th>'
                 '<th>fields written</th><th>verdict</th><th>why</th>'
                 "</tr></thead><tbody>")
        for s in rec["sites"]:
            t = s["triage"]
            why = ("held open by " + t["scope_guard"]
                   + ", released in its Drop" if t.get("scope_guard") else
                   "guard found in " + ", ".join(t["helpers_inlined"])
                   if t.get("helpers_inlined") else
                   ("check precedes the access" if t["verdict"] == "corroborated"
                    else "no check on "
                         + "/".join(x.upper() for x in t.get("fields", []))))
            h.append(f'<tr><td class="pin">{_e(s["file"])}:{s["line"]}</td>'
                     f'<td class="mono">{_e(s["operation"])}</td>'
                     f'<td class="mono dim">'
                     f'{_e(", ".join(s.get("fields") or []) or "—")}</td>'
                     f'<td>{verdict_pill(t["verdict"])}</td>'
                     f'<td class="wide">{_e(why)}</td></tr>')
        h.append("</tbody></table></div></div>")
    h.append("</section>")
    return h


def build(scan: list, trace: dict, excluded: dict) -> str:
    ranked = sorted(scan, key=lambda p: (-p["hits"], p["name"]))
    tot_hits = sum(p["hits"] for p in scan)
    tot_unch = sum(p["verdicts"].get("unchecked", 0) for p in scan)
    tot_corr = sum(p["verdicts"].get("corroborated", 0) for p in scan)
    tot_acc = sum(p["register_accesses"] for p in scan)

    h = [f"<title>Where datasheet rules would bite</title><style>{CSS}</style>",
         '<div class="wrap">', "<header>",
         '<span class="eyebrow">LIDAR · enforcement arm</span>',
         "<h1>Where our datasheet rules would bite: a scan of "
         "higher-level projects</h1>",
         f'<p class="sub">{len(scan)} open-source embedded projects read '
         "against constraints extracted from their chips' reference manuals. "
         "This is a <b>static</b> survey &mdash; each project's own Rust source "
         "is parsed for hardware register accesses and cross-referenced. "
         "Nothing is compiled.</p>", "</header>"]

    h += ['<section><h2>Across all projects</h2>', '<div class="row">',
          f'<div class="stat"><span class="k">projects</span>'
          f'<span class="v">{len(scan)}</span></div>',
          f'<div class="stat"><span class="k">register accesses</span>'
          f'<span class="v">{tot_acc}</span></div>',
          f'<div class="stat hi"><span class="k">candidate sites</span>'
          f'<span class="v">{tot_hits}</span></div>',
          f'<div class="stat warn"><span class="k">unchecked</span>'
          f'<span class="v">{tot_unch}</span></div>',
          f'<div class="stat ok"><span class="k">corroborated</span>'
          f'<span class="v">{tot_corr}</span></div>', "</div>",
          '<p class="note"><b>A hit is a candidate, not a bug.</b> '
          "<i>unchecked</i> means no precondition field is referenced before "
          "the access; <i>corroborated</i> means the project already performs "
          "the datasheet-prescribed check nearby. Guards factored into a "
          "same-file helper are followed one level, both the wrap-in-a-closure "
          "idiom and a plain call beforehand; deeper chains still read as "
          "unchecked.</p>",
          "</section>"]

    # ---- summary table ----
    h += ['<section><h2>Summary</h2>',
          '<div class="scroll"><table><thead><tr>'
          '<th class="pin">project</th><th>how it reaches the chip</th>'
          '<th>manuals</th><th>files</th><th>accesses</th>'
          '<th>candidates</th><th>unchecked</th><th>corroborated</th>'
          "<th>build-readiness</th></tr></thead><tbody>"]
    for p in ranked:
        v = p["verdicts"]
        eff = ("measured" if p["name"] in measured_projects()
               else p["readiness"]["effort"])
        h.append(
            f'<tr><td class="pin"><a href="#{_e(p["name"])}">{_e(p["name"])}</a></td>'
            f'<td class="dim">{_e(STYLE_LABEL.get(p["style"], p["style"]))}</td>'
            f'<td class="mono dim">{_e(", ".join(p["rms"]) or "—")}</td>'
            f'<td class="num">{p["rust_files"]}</td>'
            f'<td class="num">{p["register_accesses"]}</td>'
            f'<td class="num lead">{p["hits"]}</td>'
            f'<td class="num">{v.get("unchecked", 0)}</td>'
            f'<td class="num">{v.get("corroborated", 0)}</td>'
            f'<td><span class="pill {EFFORT_CLASS.get(eff, "none")}">'
            f'{_e(eff)}</span></td></tr>')
    h += ["</tbody></table></div>",
          '<p class="note"><code>ready</code> already on a driver version that '
          "pairs with our chip crate &middot; <code>hal-bump</code> needs the "
          "driver bumped, then a four-line patch &middot; <code>pac-gap</code> "
          "pins a chip-crate generation the injector does not target &middot; "
          "<code>not-applicable</code> no chip crate to inject into.</p>",
          "</section>"]

    h += ["<section><h2>Project by project</h2>"]
    for p in ranked:
        h += project_section(p, trace)
    h += ["</section>"]

    if excluded:
        h += ["<section><h2>Looked at, not scanned</h2>",
              '<p class="note">Recorded because a project absent from a report '
              "is indistinguishable from one that scanned clean.</p>"]
        for name, (repo, why) in sorted(excluded.items()):
            h += ['<div class="card">',
                  f'<h4><a href="{_e(repo)}">{_e(name)}</a></h4>',
                  f"<p>{_e(why)}</p>", "</div>"]
        h += ["</section>"]

    h += ["<section><h2>What this cannot see</h2>",
          '<p class="note">A static scan sees no runtime guards, so '
          "<i>unchecked</i> means candidate, not bug; compile confirmation is "
          "the eventual arbiter. Peripheral attribution is heuristic &mdash; it "
          "comes from the receiver expression, falling back to the module the "
          "code lives in. Chip attribution is per path prefix and derived from "
          "each driver crate's own build features, not the family in its name; "
          "getting that wrong is not conservative, and an earlier run matched "
          "Hubris's shared I&sup2;C driver against an F4 manual whose I&sup2;C "
          "is a different peripheral generation, manufacturing 14 findings. "
          "Whole-register gates over-approximate: when a rule lists no "
          "restricted fields it gates the whole register, though the datasheet "
          "note usually attaches to specific bits &mdash; read the "
          "<i>fields written</i> column before the verdict.</p>",
          "</section>"]

    h += ["<footer>",
          "<div>Generated by <code>applications/pac_codegen/experiments/"
          "landscape_page.py</code> from <code>out/scan_projects.json</code>"
          " and <code>out/trace_hal.json</code>.</div>",
          "<div>Scanner accuracy: run against stm32f4xx-hal 0.23 with RM0383's "
          "constraints it finds all 31 sites the compile route found, plus 8 "
          "the compiler structurally cannot reach because their gate was never "
          "emitted.</div>", "</footer>", "</div>"]
    return "\n".join(h)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(DOC))
    args = ap.parse_args()

    scan_path = OUT / "scan_projects.json"
    if not scan_path.is_file():
        sys.exit(f"missing {scan_path}; run scan_projects.py first")
    scan = json.loads(scan_path.read_text())

    sys.path.insert(0, str(APP_DIR / "experiments"))
    try:
        from scan_projects import EXCLUDED as excluded
    except Exception:
        excluded = {}

    trace = {}
    tp = OUT / "trace_hal.json"
    if tp.is_file():
        for a in json.loads(tp.read_text()).get("apps", []):
            trace[a["app"]] = a

    out = Path(args.out)
    out.write_text(build(scan, trace, excluded) + "\n")
    print(f"html: {out}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
