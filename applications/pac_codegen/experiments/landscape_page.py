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
import re
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
                # A port ATTEMPT that hit a wall, established by building,
                # not by reading a version out of a file.
                "blocked": "no",
                "not-applicable": "none"}


@functools.lru_cache(maxsize=1)
def measured_projects() -> dict:
    """Projects that were taken past the scan and actually compiled.

    A scan can only say a project is `pac-gap`; it cannot say whether that gap
    is an afternoon or a quarter. Where a harness has since closed one, the row
    should report what the compiler found instead of what the scan guessed."""
    out = {}
    for name in ("port_hubris.json", "port_anne_key.json",
                 "port_stm32_eth.json", "port_stm32f7_discovery.json",
                 "port_blackpill.json", "port_elodin.json"):
        pth = OUT / name
        if not pth.is_file():
            continue
        r = json.loads(pth.read_text())
        if r.get("baseline") == "PASS" and "gate_fired" in r:
            out[r["project"]] = r
        elif r.get("baseline") == "FAIL" and r.get("verdict"):
            # An attempt that hit a wall is a result too, and a more useful one
            # than the scan's guess: it says the gap is not the one the scan
            # named. Rendered separately, since there are no hits to table.
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
    if mm:
        # The compiler results live in their own top-level section now; the
        # scan section carries a pointer, not a copy.
        word = ("build blocked" if mm.get("baseline") == "FAIL"
                else f'{mm.get("gate_fired", 0)} gates fired')
        cls = "no" if mm.get("baseline") == "FAIL" else "ok"
        h.append(
            f'<p class="note"><span class="pill {cls}">{word}</span> '
            f'&nbsp;compiled against an injected crate &mdash; '
            f'<a href="#compiled-{_e(p["name"])}">results above</a>. '
            f'Below: what the static scan claims for the same project.</p>')
    else:
        cls = EFFORT_CLASS.get(r["effort"], "none")
        blockers = "; ".join(r["blockers"]) or "none"
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
            note = s.get("site_note")
            if note:
                # A human-verified note beats the computed rationale; when
                # it contradicts a `corroborated`, say so loudly.
                pill = ('<span class="pill no">known wrong</span> '
                        if t["verdict"] == "corroborated"
                        and "wrong" in note else "")
                why_cell = pill + _e(note)
            else:
                why_cell = _e(why)
            h.append(f'<tr><td class="pin">{_e(s["file"])}:{s["line"]}</td>'
                     f'<td class="mono">{_e(s["operation"])}</td>'
                     f'<td class="mono dim">'
                     f'{_e(", ".join(s.get("fields") or []) or "—")}</td>'
                     f'<td>{verdict_pill(t["verdict"])}</td>'
                     f'<td class="wide">{why_cell}</td></tr>')
        h.append("</tbody></table></div></div>")
    h.append("</section>")
    return h


def compiled_entry(p: dict, mm: dict) -> list:
    """One project's compiler results, first-class."""
    name = p["name"]
    r = p["readiness"]
    blockers = "; ".join(r["blockers"]) or "none"
    h = [f'<div class="card" id="compiled-{_e(name)}">',
         f'<h3><a href="#{_e(name)}">{_e(name)}</a></h3>',
         f'<p class="note">{_e(p.get("note", ""))}</p>']
    if mm.get("baseline") == "FAIL":
        h.append(
            f'<p class="note"><span class="pill no">attempted &mdash; '
            f'blocked</span> &nbsp;the scan called this '
            f'<em>{_e(r["effort"])}</em> ({_e(blockers)}). A build attempt '
            f'says otherwise: {_e(mm["verdict"])}</p>')
        h.append(
            f'<p class="note"><b>Evidence.</b> {_e(mm["attempt"])}: '
            f'{mm["errors"]} errors, <b>{mm["errors_in_own_src"]}</b> of them '
            f'in the project\'s own source. By crate: '
            f'{_e(", ".join(f"{k} {v}" for k, v in mm["errors_by_crate"].items() if k))}. '
            f'It pins <code>{_e(mm["pinned_toolchain"])}</code>; the PAC needs '
            f'Rust {_e(mm["pac_requires"]["rust_version"])} / edition '
            f'{_e(mm["pac_requires"]["edition"])}.</p>')
        h.append(f'<p class="note">{_e(mm["unreached_sites"])}</p>')
        h.append("</div>")
        return h
    h.append(
        f'<p class="note"><span class="pill ok">baseline PASS</span> '
        f'&nbsp;{_e(r["pac_needed"] or mm.get("pac", ""))} &mdash; the scan '
        f'called this <em>{_e(r["effort"])}</em> ({_e(blockers)}); the gap '
        f'was closed and the project built. One version line in the '
        f'workspace manifest plus {mm["mechanical_edits"]} mechanical edits, '
        f'baseline passing against the pristine crate, then '
        f'<b>{mm["gate_fired"]}</b> gate-fired sites across '
        f'{mm["registers_gated"]} gated registers with '
        f'{mm["collateral"]} collateral errors.</p>')
    if mm.get("hits"):
        h.append('<div class="scroll"><table><thead><tr>'
                 '<th class="pin">site</th><th>register</th><th>operation</th>'
                 '<th>static verdict</th></tr></thead><tbody>')
        for hit in mm["hits"]:
            note = hit.get("triage_note")
            h.append(
                f'<tr><td class="pin mono">{_e(hit["file"])}:{hit["line"]}</td>'
                f'<td class="mono">{_e(hit["register"])}</td>'
                f'<td>{_e(hit["operation"])}</td>'
                f'<td>{_e(hit["verdict"])}'
                + (' <span class="pill no">known wrong</span>' if note else "")
                + (f'<br><span class="dim">{_e(note)}</span>' if note else "")
                + "</td></tr>")
        h.append("</tbody></table></div>")
    else:
        h.append('<p class="note dim">No gate fired &mdash; a compiler-'
                 'confirmed true negative.</p>')
    if mm.get("triage_caveat"):
        h.append(f'<p class="note"><b>Read the verdicts with this in '
                 f'mind:</b> {_e(mm["triage_caveat"])}.</p>')
    h.append("</div>")
    return h


def compiled_section(scan: list) -> list:
    mm_all = measured_projects()
    by_name = {p["name"]: p for p in scan}
    entries = [(n, r) for n, r in mm_all.items() if n in by_name]
    entries.sort(key=lambda nr: (nr[1].get("baseline") == "FAIL",
                                 -(nr[1].get("gate_fired") or 0)))
    h = ['<section id="compiled"><h2>Ported and actually run &mdash; what '
         'the compiler found</h2>',
         '<p class="note">Each project below was <b>built against an '
         'injected crate</b>: constraints in, whole dependency graph '
         'compiled, every listed site a real diagnostic. This is the '
         'stronger evidence grade on this page; the scan (next section) '
         'covers everything a build cannot yet reach.</p>']
    for n, r in entries:
        h += compiled_entry(by_name[n], r)
    h.append("</section>")
    return h


def dependent_records() -> list:
    """crates.io dependents of the swept drivers, probed by
    experiments/dependent_compile.py. A different population from the ported
    projects above: nobody hand-picked these builds -- cargo's resolver pulls
    the swept driver into them, so a fired site here ships downstream."""
    out = []
    for pth in sorted(OUT.glob("dependent_*.json")):
        r = json.loads(pth.read_text())
        # dependent_scan.json matches this glob too and is a LIST (the scan
        # record, rendered separately by dependent_scan_rows).
        if isinstance(r, dict) and r.get("baseline"):
            out.append(r)
    return out


def dependents_section() -> list:
    recs = dependent_records()
    if not recs:
        return []
    census_p = APP_DIR / "experiments" / "hal_dependents_census.json"
    census = json.loads(census_p.read_text()) if census_p.is_file() else {}
    meta = census.pop("_meta", {})
    n_dep = sum(len(v) for v in census.values())
    n_normal = sum(1 for v in census.values()
                   for req, kind in v.values() if kind == "normal")
    h = ['<section id="dependents"><h2>Downstream &mdash; who compiles the '
         'swept drivers&rsquo; sites</h2>',
         f'<p class="note">The swept drivers have <b>{n_dep}</b> dependents '
         f'on crates.io ({n_normal} carrying the driver as a normal, '
         'non-example dependency). Impact is only an honest claim where the '
         'dependent pins <b>the generation the sweep measured</b> &mdash; '
         'an older pin contains none of the code the sites live in &mdash; '
         'and that filter leaves the crates below. Each was probed with a '
         'bare crate depending on it from crates.io, the chip crate '
         '<code>[patch]</code>ed to an injected copy, baseline proven '
         'passing against the pristine copy first. A bare probe '
         'instantiates no generics, so these are sites the dependent '
         'compiles <b>unconditionally</b> &mdash; a floor, not a ceiling. '
         'Site identity and human verdicts live on the tracking page and '
         'in the review ledger; what this section adds is <b>who ships '
         'them</b>.</p>']
    for r in sorted(recs, key=lambda x: -(x.get("gate_fired") or 0)):
        name = r["dependent"]
        layers = ", ".join(f"{k} ({v})"
                           for k, v in (r.get("by_layer") or {}).items())
        h += [f'<div class="card" id="dependent-{_e(name)}">',
              f'<h3>{_e(name)} {_e(r["version"])}</h3>',
              f'<p class="note"><span class="pill ok">baseline PASS</span>'
              f'&nbsp; depends on <b>{_e(r["hal"])}</b>, probed as '
              f'{_e(r["device"])} ({_e(r["rm"].upper())}) against '
              f'{_e(r["pac"])}, features '
              f'<code>{_e(", ".join(r.get("features") or []) or "default")}'
              '</code>.</p>']
        if r.get("gate_fired"):
            h.append(
                f'<p class="note"><b>{r["gate_fired"]}</b> gate-fired sites, '
                f'every one inside {_e(layers)} &mdash; this build contains '
                'the sweep&rsquo;s fired surface for that pairing verbatim, '
                f'plus {r.get("generic_friction", 0)} generic-friction '
                f'errors and {r.get("collateral", 0)} collateral.</p>')
        else:
            h.append(
                f'<p class="note"><b>No true site fires.</b> The build stops '
                f'on <b>{r.get("generic_friction", 0)}</b> adoption-friction '
                'errors: the driver&rsquo;s generic register API needs '
                'witness bounds before anything on this chip compiles '
                '&mdash; the encoding&rsquo;s adoption cost surfacing in a '
                'dependent, not a bug.</p>')
        h.append("</div>")
    if meta.get("excluded"):
        for k, why in meta["excluded"].items():
            h.append(f'<p class="note dim"><b>{_e(k)}</b> is deliberately '
                     f'absent: {_e(why)}.</p>')
    h += dependent_scan_rows()
    h.append("</section>")
    return h


def dependent_scan_rows() -> list:
    """The census population SCANNED at its own pin (dependent_scan.py).

    The compile probes above demand the swept driver generation; the
    scanner does not. Rendered from out/dependent_scan.json, computed,
    never prose."""
    pth = OUT / "dependent_scan.json"
    if not pth.is_file():
        return []
    rows = json.loads(pth.read_text())
    scanned = [r for r in rows if "skip" not in r]
    hot = sorted((r for r in scanned if r.get("hits")),
                 key=lambda r: -r["hits"])
    quiet = [r for r in scanned if not r.get("hits")]
    skipped = [r for r in rows if "skip" in r]
    h = ['<h3>The rest of the census, scanned at its own pin</h3>',
         '<p class="note">A dependent pinning an older driver generation '
         'cannot be compile-probed, but its <b>own source</b> is readable '
         'at any pin. Every census dependent not already in the survey was '
         'scanned from its published crates.io package, the chip and manual '
         f'read from its own manifest: <b>{len(scanned)}</b> scanned, '
         f'<b>{len(hot)}</b> with hits on constrained registers, '
         f'{len(quiet)} clean, {len(skipped)} skipped with the reason '
         'recorded below. A hit here is a <b>scan claim</b> (the weaker '
         'evidence grade); the pinned generation next to it says what a '
         'compile confirmation would cost.</p>']
    if hot:
        # Where a scanned dependent has since been PORTED and compiled
        # against an injected crate (measure_ported.json), the compiler's
        # verdict sits beside the scan's claim.
        mp = OUT / "measure_ported.json"
        compiled = {}
        if mp.is_file():
            for r in json.loads(mp.read_text()):
                if r.get("baseline") == "PASS" and r.get("hal"):
                    compiled[r["hal"]] = (f'{r.get("gate_fired", 0)} fired '
                                          f'({r.get("possible_bug", 0)} '
                                          'unchecked)')
        h.append('<div class="scroll"><table><thead><tr>'
                 '<th class="pin">dependent</th><th>pins</th><th>manual</th>'
                 '<th>own accesses</th><th>hits</th><th>unchecked</th>'
                 '<th>corroborated</th><th>compiled (after port)</th>'
                 '</tr></thead><tbody>')
        for r in hot:
            v = r.get("verdicts") or {}
            h.append(
                f'<tr><td class="pin mono">{_e(r["name"])} '
                f'{_e(r.get("version", ""))}</td>'
                f'<td class="mono dim">{_e(", ".join(r.get("pins") or []))}</td>'
                f'<td class="mono">{_e((r.get("rms") or ["?"])[0])}</td>'
                f'<td class="num">{r.get("register_accesses", 0)}</td>'
                f'<td class="num">{r["hits"]}</td>'
                f'<td class="num">{v.get("unchecked", 0)}</td>'
                f'<td class="num">{v.get("corroborated", 0)}</td>'
                f'<td>{_e(compiled.get(r["name"], "&mdash;")) if r["name"] in compiled else "&mdash;"}</td></tr>')
        h.append("</tbody></table></div>")
        if compiled:
            h.append(
                '<p class="note">The <b>compiled</b> column is the stronger '
                'grade catching up with the scan: the crate was ported to '
                'PAC 0.16 with compiler-dictated edits (port_hal.py), built '
                'clean against the pristine crate, then against the injected '
                'one. The gap between a scan count and a fired count is not '
                'error &mdash; it decomposes into constraints that did not '
                'survive collection or validation, field-level gates '
                'narrower than a register-level scan, and code the feature '
                'selection never compiles.</p>')
    zero_access = sum(1 for r in quiet if not r.get("register_accesses"))
    h.append(
        f'<p class="note dim">Of the {len(quiet)} clean dependents, '
        f'{zero_access} contain <b>no register access of their own at all</b> '
        '&mdash; every access routes through their HAL, so their exposure is '
        'exactly the driver rows already measured. That list includes the '
        'deployed firmware the census surfaced: '
        + _e(", ".join(sorted(r["name"] for r in quiet
                              if not r.get("register_accesses"))[:10]))
        + "&hellip;</p>")
    if skipped:
        by_reason = {}
        for r in skipped:
            by_reason.setdefault(str(r["skip"]).split(":")[0], []).append(r["name"])
        for reason, names in sorted(by_reason.items()):
            h.append(f'<p class="note dim"><b>{_e(reason)}</b> '
                     f'({len(names)}): {_e(", ".join(sorted(names)))}</p>')
    return h


def build(scan: list, trace: dict, excluded: dict) -> str:
    ranked = sorted(scan, key=lambda p: (-p["hits"], p["name"]))
    tot_hits = sum(p["hits"] for p in scan)
    tot_unch = sum(p["verdicts"].get("unchecked", 0) for p in scan)
    tot_corr = sum(p["verdicts"].get("corroborated", 0) for p in scan)
    tot_acc = sum(p["register_accesses"] for p in scan)

    # From the port records, never prose: the subtitle said "Nothing is
    # compiled" for a while after three projects were.
    mm = measured_projects()
    measured_names = sorted(n for n, r in mm.items()
                            if r.get("baseline") == "PASS")
    n_measured = len(measured_names)
    n_blocked = sum(1 for r in mm.values() if r.get("baseline") == "FAIL")

    h = [f"<title>Where datasheet rules would bite</title><style>{CSS}</style>",
         '<div class="wrap">', "<header>",
         '<span class="eyebrow">LIDAR · enforcement arm</span>',
         "<h1>Where our datasheet rules would bite &mdash; and where "
         "the compiler agrees</h1>",
         f'<p class="sub">{len(scan)} open-source embedded projects read '
         "against constraints extracted from their chips' reference manuals. "
         "The survey is <b>static</b> &mdash; each project's own Rust source "
         "is parsed for register accesses and cross-referenced &mdash; and "
         "where a project could be brought to the PAC generation we inject, "
         "it was then <b>compiled against the injected crate</b>: "
         f"{n_measured} project{'s' if n_measured != 1 else ''} measured "
         f"that way ({', '.join(measured_names)}), {n_blocked} attempt "
         "recorded as blocked, and the scan's blind spot (writes that leave "
         "the typed API) is bounded at the bottom of the page.</p>",
         "</header>"]

    h += ['<section><h2>Purpose</h2>',
          '<p class="note">Datasheets attach <b>preconditions</b> to register '
          'writes ("SWSTART may be set only when ADON&nbsp;=&nbsp;1"). This '
          'project extracts those rules from ST reference manuals and injects '
          'them into the generated chip crates as compile-time gates. The '
          'question this page answers: <b>where would those rules bite in '
          'real, third-party code?</b></p>',
          '<p class="note">Two evidence grades, kept separate throughout. '
          '<b>Compiled</b> (next section): the project was built against an '
          'injected crate and every listed site is a compiler diagnostic. '
          '<b>Scanned</b> (the section after): the project&rsquo;s own source '
          'was read statically and cross-referenced against the constraints '
          '&mdash; the reach is wider, the claim weaker. Driver-level compile '
          'results across the whole 49-manual corpus live on the companion '
          '<i>register-constraints tracking</i> page, not here. Nothing on '
          'this page is a confirmed bug: gates prove an access is real, '
          'triage says whether a check is visible nearby, and the human '
          'verdict lives in the review ledger.</p>',
          "</section>"]

    h += compiled_section(scan)
    h += dependents_section()

    h += ['<section><h2>Results of the scan &mdash; across all projects</h2>',
          '<div class="row">',
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
          "<th>compiler</th>"
          "<th>build-readiness</th></tr></thead><tbody>"]
    for p in ranked:
        v = p["verdicts"]
        # Two evidence grades share this table, and until this column a
        # reader could not tell them apart without opening the section: the
        # count columns are the SCANNER's claims; this one says what the
        # COMPILER established, where a build exists.
        rec = measured_projects().get(p["name"])
        if rec is None:
            comp = '<span class="dim">scan only</span>'
        elif rec.get("baseline") == "FAIL":
            comp = '<span class="pill no">build blocked</span>'
        else:
            # Mechanism words, no verdict implied. "N confirmed" invited the
            # reading "N confirmed BUGS", which overstates it exactly the way
            # this page tries never to: what the compiler confirms is that
            # the ACCESS is real and the build reaches it. The verdict lives
            # in triage, and its word is "unchecked" -- a candidate, not a
            # finding.
            n = rec.get("gate_fired", 0)
            bug = rec.get("possible_bug")
            comp = (f'<span class="pill ok">{n} gate'
                    f'{"s" if n != 1 else ""} fired</span>'
                    + (f' <span class="dim">({bug} unchecked)</span>'
                       if bug is not None else ""))
        eff = ("measured" if (rec and rec.get("baseline") == "PASS")
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
            f'<td>{comp}</td>'
            f'<td><span class="pill {EFFORT_CLASS.get(eff, "none")}">'
            f'{_e(eff)}</span></td></tr>')
    h += ["</tbody></table></div>",
          '<p class="note"><b>compiler</b>: <i>N gates fired</i> means the '
          "project was built against an injected crate and N compile errors "
          "landed on constrained-register accesses &mdash; the compiler "
          "confirms the ACCESS is real and the build reaches it, never that "
          "it is a bug. <i>(M unchecked)</i> is the subset where static "
          "triage then found no precondition check in the enclosing function "
          "&mdash; candidates for human review, the same word the count "
          "columns use. <i>scan only</i> means no build exists yet and the "
          "count columns are the static scanner&rsquo;s; <i>build "
          "blocked</i> means a build was attempted and recorded as "
          "impossible. Where both grades exist they need not match &mdash; "
          "the compiler sees only what a build can reach (elodin: SDMMC "
          "subset), and field gates are finer than register-level "
          "scanning.</p>"
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
          "<i>fields written</i> column before the verdict.</p>"]

    bb = OUT / "bitband_scan.json"
    if bb.is_file():
        d = json.loads(bb.read_text())
        pairs = d.get("pairings") or []
        hot = [q for q in pairs if q.get("constrained_hits")]
        total = sum(q.get("constrained_hits") or 0 for q in pairs)
        sites = {}
        for q in pairs:
            sites[q["driver"]] = q.get("sites") or 0
        h += ['<h3>Register writes that leave the typed API entirely</h3>',
              '<p class="note">Every compile-confirmed number on this page is '
              'a <b>lower bound</b>, and this measures the gap. Enforcement '
              'is a trait bound on the register type&rsquo;s access methods; '
              '<b>bit banding</b> writes a register through a raw pointer '
              '(<code>bb::set(rcc.bdcr(), 0)</code> &mdash; ARM maps each '
              'peripheral bit to its own word address), so the write never '
              'calls a gated method and compiles whatever markers the '
              'register carries. <code>experiments/bitband_scan.py</code> '
              'finds these calls, resolves the bit number to a field through '
              'the PAC&rsquo;s own generated accessors, and cross-references '
              'the constraints. '
              f'Across {len(pairs)} (driver, manual) pairings &mdash; every '
              'locally available sweep consumer that uses bit banding &mdash; '
              f'it finds <b>{total}</b> writes to constrained fields that no '
              'gate can see. &ldquo;Zero hits&rdquo; on this page means '
              '&ldquo;nothing went through the gated API&rdquo;, not '
              '&ldquo;nothing touched the register&rdquo;.</p>']
        if hot:
            h += ['<div class="card"><h4>Invisible writes, by pairing</h4>',
                  '<div class="scroll"><table><thead><tr><th class="pin">'
                  'driver</th><th>manual</th><th>site</th><th>field</th>'
                  '<th>requires</th></tr></thead><tbody>']
            for q in hot:
                for r in q.get("hits") or []:
                    what = (r.get("field") or "").upper() or                         "/".join(x.upper() for x in r.get("candidate_fields", []))
                    pre = ", ".join(r.get("preconditions") or []) or "&mdash;"
                    h += [f'<tr><td class="pin mono">{_e(q["driver"])}</td>'
                          f'<td class="mono">{_e(q["pairing"])}</td>'
                          f'<td class="mono">{_e(r["file"])}:{r["line"]} '
                          f'bb::{_e(r["op"])}(&hellip;, {_e(r["bit_expr"])})</td>'
                          f'<td class="mono">{_e(what)}</td>'
                          f'<td>{_e(pre)}</td></tr>']
            h += ['</tbody></table></div>',
                  '<p class="note">Whether each is a live defect is '
                  'unresolved by design: the access is invisible to the '
                  'gate, so the triage that would decide never runs. The '
                  'scan also reports, without judging, sites whose bit is '
                  'computed (the register&rsquo;s constrained fields are '
                  'listed, never guessed) and macro-generated sites where '
                  'the register name does not survive (counted, never '
                  'dropped). The typed atomic path '
                  '(<code>set_bits</code>/<code>clear_bits</code>, now '
                  'gated) offers the same single-instruction write with the '
                  'field named by the compiler.</p></div>']
    h += ["</section>"]

    h += ["<footer>",
          "<div>Generated by <code>applications/pac_codegen/experiments/"
          "landscape_page.py</code> from <code>out/scan_projects.json</code>,"
          " <code>out/trace_hal.json</code> and "
          "<code>out/bitband_scan.json</code>.</div>",
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

    html_text = build(scan, trace, excluded) + "\n"

    # The page is assembled from string fragments, so a branch that emits one
    # </div> too many closes the CONTENT WRAPPER mid-page and everything after
    # it renders flush against the viewport edge -- which shipped, and a
    # reader caught it before we did. Unbalanced divs inside any <section>
    # fail the build rather than the reader.
    for m in re.finditer(r'<section id="([^"]+)">(.*?)</section>',
                         html_text, re.S):
        opens = len(re.findall(r"<div\b", m.group(2)))
        closes = m.group(2).count("</div>")
        if opens != closes:
            sys.exit(f"unbalanced divs in section {m.group(1)!r}: "
                     f"{opens} opened, {closes} closed")

    out = Path(args.out)
    out.write_text(html_text)
    print(f"html: {out}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
