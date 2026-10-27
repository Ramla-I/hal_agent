#!/usr/bin/env python3
"""Render the injection source-vs-binary cost figure (single-column paper figure).

Reads ``injection_loc.json`` (produced by ``measure_injection_loc.py``) and emits
a standalone column-width SVG plus an HTML preview, both next to this script:

    pac_injection_cost.svg    # \\includegraphics[width=\\columnwidth]{...}
    pac_injection_cost.html   # browser preview

One bar per PAC crate (each the device with the MOST injected lines), split into
zero-cost marker scaffolding vs gate-proportional enforcement modules. The "+0
bytes" binary figure is the measured result from ``verify_binary_size.py``.

    python gen_injection_cost_artifact.py
"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ART = HERE.parents[3] / "docs" / "artifacts"   # repo-root/docs/artifacts
ART.mkdir(parents=True, exist_ok=True)
data = json.load(open(HERE/"injection_loc.json"))
allrows = data["rows"]

# Binary-side numbers are MEASURED by verify_binary_size.py, not hardcoded.
_bf = HERE/"binary_size.json"
measured = _bf.exists()
if measured:
    b = json.load(open(_bf))
    identical = bool(b.get("identical"))
    bin_str = "+0 bytes" if identical else f"+{b.get('text_delta','?')} bytes"
    check_cost = b.get("check_cost_bytes")
else:                                   # figure still renders before verify has run
    b, identical = {}, False
    bin_str, check_cost = "not measured", None
# Binary-side claims must match the measurement, not assert identity by default.
if identical:
    bin_sub = "identical .text · same size"
    cap_bin = ("<b>byte-identical</b> to one built against the un-injected PAC, "
               "at the\n    same size")
elif measured:
    bin_sub = f".text {bin_str}"
    cap_bin = (f"<b>{bin_str}</b> of <code>.text</code> versus the un-injected "
               "PAC")
else:
    bin_sub = "not yet measured"
    cap_bin = "<b>not yet measured</b> — run <code>verify_binary_size.py</code>"
# Field-level vs register-only: read the mode the loc measurement recorded
# rather than always claiming the field-level default.
mode_label = ("whole-register gating (--register-only)"
              if "register-only" in str(data.get("mode", "")) else
              "field-level gating (the injection default)")
check_str = (f"+{check_cost} B per opt-in check is the only runtime cost"
             if check_cost is not None else "opt-in checks are the only runtime cost")
check_cap = (f"<b>+{check_cost}&nbsp;bytes</b> per opt-in checked write"
             if check_cost is not None else "a small per-call cost for opt-in checked writes")

# One bar per PAC crate; choose the device with the MOST injected lines.
bycrate = {}
for r in allrows:
    if r["pac"] not in bycrate or r["total"] > bycrate[r["pac"]]["total"]:
        bycrate[r["pac"]] = r
rows = sorted(bycrate.values(), key=lambda r: r["total"])
N = len(rows)
enf = [100*r["modules"]/r["total"] for r in rows]
tot_min = min(r["total"] for r in rows); tot_max = max(r["total"] for r in rows)
scaff_lo, scaff_hi = 100-max(enf), 100-min(enf)
mx = tot_max

# ---- geometry (units == points; scales to a ~3.4in single column) ----
W = 240
INK="#1b1f24"; INK2="#55606c"; MUT="#98a2ad"; GRID="#e9ebee"; LINE="#dfe2e6"
SCAFF="#9aa7b8"; ENF="#d9772e"; ZERO="#2f8f5b"; CARD="#f5f6f7"
bin_color = ZERO if identical else (ENF if measured else MUT)
LW=26; RW=24; BW=W-LW-RW
ROW=11
cy=2; cy_h=34
note_y=cy+cy_h+8; leg_y=cy+cy_h+20; chart_y=leg_y+8
chart_h=N*ROW; axis_y=chart_y+chart_h; H=axis_y+18
def x(v): return LW + BW*v/mx
e=[]
def T(x_,y_,s,size,fill=INK,anchor="start",weight="normal",mono=False,ls=0):
    fam='ui-monospace,Menlo,Consolas,monospace' if mono else 'Helvetica,Arial,sans-serif'
    lsp=f' letter-spacing="{ls}"' if ls else ''
    e.append(f'<text x="{x_:.1f}" y="{y_:.1f}" font-size="{size}" fill="{fill}" '
             f'text-anchor="{anchor}" font-weight="{weight}" font-family="{fam}"{lsp}>{s}</text>')

# contrast strip: SOURCE -> BINARY
b1w=104; ax=b1w; aw=18; b2x=b1w+aw; b2w=W-b2x
e.append(f'<rect x="0" y="{cy}" width="{b1w}" height="{cy_h}" rx="4" fill="{CARD}" stroke="{LINE}"/>')
T(6, cy+9, "GENERATED SOURCE", 4.6, MUT, weight="bold", ls=0.4)
T(6, cy+22, f"{tot_min/1000:.0f}k–{tot_max/1000:.0f}k", 12.5, INK, weight="bold")
T(6, cy+30, "lines / crate", 5.4, INK2)
T(ax+aw/2, cy+cy_h/2-2, "→", 11, MUT, anchor="middle")
T(ax+aw/2, cy+cy_h/2+7, "compiles", 3.9, MUT, anchor="middle")
T(ax+aw/2, cy+cy_h/2+11.5, "to", 3.9, MUT, anchor="middle")
e.append(f'<rect x="{b2x}" y="{cy}" width="{b2w}" height="{cy_h}" rx="4" fill="{CARD}" stroke="{ZERO}" stroke-opacity="0.5"/>')
T(b2x+6, cy+9, "FIRMWARE BINARY", 4.6, MUT, weight="bold", ls=0.4)
T(b2x+6, cy+22, bin_str, 12.5, bin_color, weight="bold")
T(b2x+6, cy+30, bin_sub, 5.1, INK2)
T(W/2, note_y, f"{mode_label} · {N} PAC crates · {check_str}",
  4.6, MUT, anchor="middle")

# legend
e.append(f'<rect x="0" y="{leg_y-4.5}" width="6" height="6" rx="1.3" fill="{SCAFF}"/>')
T(8, leg_y, "marker scaffolding (zero-cost)", 5.2, INK2)
e.append(f'<rect x="112" y="{leg_y-4.5}" width="6" height="6" rx="1.3" fill="{ENF}"/>')
T(120, leg_y, "enforcement modules", 5.2, INK2)

# gridlines
for gv in range(0, int(mx)+1, 30000):
    gx=x(gv)
    e.append(f'<line x1="{gx:.1f}" y1="{chart_y-2:.1f}" x2="{gx:.1f}" y2="{axis_y:.1f}" stroke="{GRID}" stroke-width="0.6"/>')
    T(gx, axis_y+8, f"{gv//1000}k", 5, MUT, anchor="middle")
T(LW+BW/2, axis_y+16, "generated lines added to the PAC crate", 5.6, INK2, anchor="middle")

# bars: one per crate, labeled by crate
for i,r in enumerate(rows):
    yy=chart_y+i*ROW
    xs=x(r["scaffolding"]); xe=x(r["total"])
    e.append(f'<rect x="{LW}" y="{yy+1.6:.1f}" width="{xs-LW:.1f}" height="{ROW-3.2}" rx="1.5" fill="{SCAFF}"/>')
    e.append(f'<rect x="{xs+1:.1f}" y="{yy+1.6:.1f}" width="{max(xe-xs-1,0.6):.1f}" height="{ROW-3.2}" rx="1.5" fill="{ENF}"/>')
    T(LW-3, yy+ROW/2+1.9, r["pac"].replace("stm32",""), 5.4, INK2, anchor="end", mono=True)
    T(xe+3, yy+ROW/2+1.9, f"{r['total']/1000:.0f}k", 5.2, MUT)

svg_body="\n".join(e)
svg_open=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" width="{W}pt" height="{H:.0f}pt" font-family="Helvetica,Arial,sans-serif">'
(ART/"pac_injection_cost.svg").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n{svg_open}\n{svg_body}\n</svg>\n')

inline=f'<svg viewBox="0 0 {W} {H:.0f}" class="fig" role="img" aria-label="Injection source vs binary cost">\n{svg_body}\n</svg>'
page=f'''<style>
:root{{--bg:#eef0f2;--ink:#1b1f24;--ink2:#55606c;--paper:#ffffff;--line:#dfe2e6}}
@media (prefers-color-scheme:dark){{:root{{--bg:#14171a;--ink:#eef1f4;--ink2:#aeb7c1}}}}
:root[data-theme="dark"]{{--bg:#14171a;--ink:#eef1f4;--ink2:#aeb7c1}}
:root[data-theme="light"]{{--bg:#eef0f2;--ink:#1b1f24;--ink2:#55606c}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;line-height:1.55}}
main{{max-width:640px;margin:0 auto;padding:34px 22px 52px}}
.eyebrow{{font-size:12px;letter-spacing:.13em;text-transform:uppercase;color:#c85a1b;font-weight:600;margin:0 0 6px}}
h1{{font-size:23px;line-height:1.2;margin:0 0 14px;font-weight:700;letter-spacing:-.01em}}
.col{{background:var(--paper);border:1px solid var(--line);border-radius:10px;width:360px;max-width:100%;
  margin:0 auto;padding:16px 16px 10px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.colcap{{font-size:12px;color:#8a949f;text-align:center;margin:7px 0 0}}
.fig{{width:100%;height:auto;display:block}}
figcaption{{font-size:13.5px;color:var(--ink2);max-width:56ch;margin:22px auto 0;border-left:2px solid #d9772e;padding-left:12px}}
figcaption b{{color:var(--ink)}}
.meta{{font-size:12.5px;color:var(--ink2);max-width:56ch;margin:18px auto 0}}
code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.92em;background:rgba(127,127,127,.14);padding:1px 5px;border-radius:4px}}
</style>
<main>
  <p class="eyebrow">Single-column paper figure &middot; field-level default</p>
  <h1>Injection cost: large in source, free in the binary</h1>
  <figure style="margin:0">
    <div class="col">{inline}<div class="colcap">shown at column width ({W}pt ≈ 3.3in)</div></div>
    <figcaption><b>Figure.</b> With {mode_label}, compiling
    datasheet access rules into the PAC adds {tot_min/1000:.0f}k&ndash;{tot_max/1000:.0f}k
    generated lines per crate (one bar per PAC crate, {N} total, each the device with the most
    injected lines), of which {scaff_lo:.0f}&ndash;{scaff_hi:.0f}% is zero-cost marker scaffolding
    and the rest gate-proportional enforcement code. The compiled firmware's executable code
    (<code>.text</code>) is {cap_bin}; the sole runtime cost is {check_cap}.</figcaption>
  </figure>
</main>'''
(ART/"pac_injection_cost.html").write_text(page)
print(f"SVG {W}x{H:.0f}pt, {N} crates; totals {tot_min}-{tot_max}; scaffolding {scaff_lo:.0f}-{scaff_hi:.0f}%")
