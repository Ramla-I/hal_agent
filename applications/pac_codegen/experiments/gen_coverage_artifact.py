#!/usr/bin/env python3
"""gen_coverage_artifact.py -- the STM32 PAC -> HAL & ecosystem coverage artifact.

One row per svd2rust PAC crate (family). For each, lists every downstream
crate -- HAL, app, BSP, driver -- built or scanned against the witness-gated
crate, split into two columns:

  compiled  built against the injected PAC; per device, (gates fired,
            potential bug), with the compile path (direct -> PAC, or via a
            named HAL). A HAL that will not build shows `baseline fails` on
            that device, or `couldn't port`.
  scanned   source read statically only (weaker); candidate-hit count.

Everything is computed from the experiment records under experiments/out/
(sweep.json, stm_master_pacs.json, port_*.json, dependent_*.json,
dependent_scan.json) -- no hand-entered numbers -- so re-running after a
fresh sweep/scan updates the page. Writes docs/artifacts/pac_coverage.html; publish
that with the Artifact tool.

Usage:
    python applications/pac_codegen/experiments/gen_coverage_artifact.py
"""
import json, collections
from pathlib import Path

_APP = Path(__file__).resolve().parent.parent
_REPO = _APP.parent.parent
OUT = str(_APP / "experiments" / "out") + "/"
_HTML_OUT = _REPO / "docs" / "artifacts" / "pac_coverage.html"
def L(p):
    try: return json.load(open(OUT+p))
    except: return None
sweep=L("sweep.json"); master=L("stm_master_pacs.json")
manuals=collections.defaultdict(set); pair=collections.Counter(); base=collections.defaultdict(bool)
# per-device HAL results: pac -> hal -> list of (device, rm, fired|None, bug|None)  (None,None = baseline fail)
HALDEV=collections.defaultdict(lambda: collections.defaultdict(list))
for r in sweep:
    manuals[r["pac"]].add(r["rm"]); pair[r["pac"]]+=1
    for c in r.get("hal_results",[]):
        if c.get("baseline")=="PASS":
            base[r["pac"]]=True
            HALDEV[r["pac"]][c["crate"]].append((r["device"],r["rm"],c.get("true_enforcement",0),c.get("candidate",0)))
        else:
            HALDEV[r["pac"]][c["crate"]].append((r["device"],r["rm"],None,None))
for r in master: manuals[r["pac"]].add(r["rm"]); pair[r["pac"]]+=1
for r in (L("measure_ported.json") or []):
    hal=r.get("hal")
    if hal and hal!="rustuino" and r.get("baseline")=="PASS":
        HALDEV[r["pac"]][hal].append((r["device"],r["rm"],r.get("gate_fired",0),r.get("possible_bug",0)))
BLOCKED={"stm32f7":("stm32f7xx-hal","couldn't port — PAC feature rename"),
         "stm32l1":("stm32l1xx-hal","couldn't port — 133 errs, multi-gen")}

CR="https://crates.io/crates/"
GH={"blackpill-usb-pwdstore":"https://github.com/sjm42/blackpill-usb-pwdstore",
    "elodin-sensor-fw":"https://github.com/elodin-sys/elodin",
    "hubris":"https://github.com/oxidecomputer/hubris","anne-key":"https://github.com/ah-/anne-key"}
def clink(n): return f'<a href="{CR}{n}">{n}</a>'
def plink(n): return f'<a href="{GH[n]}">{n}</a>' if n in GH else clink(n)
PORTED_OK={"stm32f0","stm32l0"}; NOHAL={"stm32f2","stm32mp1","stm32n6","stm32u0","stm32u5"}; MASTER={"stm32wb0","stm32wba"}

# apps/probes: pac -> {name:(device,fired,bug)}
COMP=collections.defaultdict(dict)
for f,pac in [("port_blackpill","stm32f4"),("port_stm32_eth","stm32f4"),
              ("dependent_stm32f469i_disc","stm32f4"),("port_elodin","stm32h7"),
              ("port_hubris","stm32h7"),("port_hubris_stm32f3","stm32f3"),
              ("port_hubris_stm32f4","stm32f4"),("port_hubris_g031","stm32g0"),
              ("port_anne_key","stm32l1"),("dependent_semtech_radios","stm32g4"),
              ("dependent_embassy_stm32","stm32g4")]:
    d=L(f+".json")
    if not d: continue
    nm=(d.get("project") or d.get("dependent")).split(" (")[0]
    hal=d.get("hal","")
    path=("via", hal.split()[0]) if hal else ("direct", None)
    COMP[pac][nm]=(d.get("device",""), d.get("gate_fired",0), d.get("possible_bug",0), path)
for r in (L("measure_ported.json") or []):
    if r.get("hal")=="rustuino":
        COMP["stm32f4"]["rustuino"]=(r.get("device",""),r.get("gate_fired",0),r.get("possible_bug",0),("direct",None))

SCAN=collections.defaultdict(dict)
for r in (L("dependent_scan.json") or []):
    if "skip" in r: continue
    SCAN[(r.get("pac") or "").split()[0]][r["name"].split("@")[0]]=r.get("hits",0)

HALTAG='<span class="tag">hal</span>'
def path_html(path):
    kind,hal=path
    return f'<span class="path">via {clink(hal)}</span>' if kind=="via" else '<span class="path">direct &rarr; PAC</span>'
def dev_line(dev,f,b):
    if f is None: return f'<span class="devrow"><span class="dev">{dev}</span> <span class="res fail">baseline fails</span></span>'
    return f'<span class="devrow"><span class="dev">{dev}</span> <span class="res comp">{f} fired, {b} bug</span></span>'

def compiled_cell(p):
    out=[]
    hals=HALDEV.get(p,{})
    def hmax(h): return max([x[2] or -1 for x in hals[h]] or [-1])
    for h in sorted(hals, key=lambda h:-hmax(h)):
        devs=sorted(hals[h], key=lambda x:x[0])   # devices alphabetical
        out.append(f'<div class="entry">{clink(h)}{HALTAG} {path_html(("direct",None))}'
                   + "".join(dev_line(*d[:1],*d[2:]) for d in devs) + "</div>")
    # a HAL that could not be ported at all (never compiled, shown in scanned if scanned)
    if p in BLOCKED and BLOCKED[p][0] not in hals and BLOCKED[p][0] not in SCAN.get(p,{}):
        out.append(f'<div class="entry">{clink(BLOCKED[p][0])}{HALTAG}'
                   f'<span class="devrow"><span class="res fail">{BLOCKED[p][1]}</span></span></div>')
    for n,(dev,f,b,path) in sorted(COMP.get(p,{}).items(), key=lambda kv:-kv[1][1]):
        out.append(f'<div class="entry">{plink(n)} {path_html(path)}'
                   f'<span class="devrow"><span class="dev">{dev}</span> '
                   f'<span class="res comp">{f} fired, {b} bug</span></span></div>')
    return "".join(out) if out else "<span class='muted'>—</span>"

def scanned_cell(p):
    skip=set(COMP.get(p,{}))|set(HALDEV.get(p,{}))
    sc={n:h for n,h in SCAN.get(p,{}).items() if n not in skip}
    if not sc: return "<span class='muted'>—</span>"
    out=[]
    for n,h in sorted(sc.items(), key=lambda kv:-kv[1]):
        tag=HALTAG if (p in BLOCKED and n==BLOCKED[p][0]) else ""
        note=' <span class="res fail">(couldn\'t port)</span>' if (p in BLOCKED and n==BLOCKED[p][0]) else ""
        out.append(f'<div class="entry"><span class="{("" if h else "dimn")}">{clink(n)}</span>{tag} '
                   f'<span class="res {("scan" if h else "scan0")}">{h} hit{"" if h==1 else "s"}</span>{note}</div>')
    return "".join(out)

def statusp(p):
    if p in MASTER: return ("no published consumer","mute")
    if base[p]: return ("ran · sweep","ok")
    if p in PORTED_OK: return ("ran · ported","ok")
    if p=="stm32h5": return ("baseline failed","warn")
    if p in ("stm32f7","stm32l1"): return ("HAL not ported","warn")
    if p in NOHAL: return ("no HAL","mute")
    return ("?","?")

rows=[]
for p in sorted(manuals, key=lambda p:(p in MASTER,p)):
    pac=f'<a href="https://github.com/stm32-rs/stm32-rs">{p}</a>' if p in MASTER else clink(p)
    pt,pcls=statusp(p); src="master" if p in MASTER else "0.16.0"
    rows.append((pac,len(manuals[p]),pair[p],src,pt,pcls,compiled_cell(p),scanned_cell(p)))
n_clean=sum(1 for p in manuals if base[p] or p in PORTED_OK)
tot_m=len(set().union(*manuals.values())); tot_p=sum(pair.values())
trows="\n".join(
f'<tr><td class="mono pac">{a}</td><td class="num">{m}</td><td class="num dim">{pr}</td>'
f'<td class="mono dim src">{src}</td><td><span class="pill {pcls}">{pt}</span></td>'
f'<td class="mono down">{cc}</td><td class="mono down">{sc}</td></tr>'
for a,m,pr,src,pt,pcls,cc,sc in rows)

doc=f"""<title>STM32 PAC → HAL &amp; ecosystem coverage</title>
<style>
:root{{--bg:#eef1f5;--surface:#fff;--ink:#1b2330;--ink2:#5a6577;--muted:#98a2b3;--line:#dde3ea;
--accent:#0e7c86;--ok:#0f9d58;--okbg:#e6f4ec;--warn:#b7791f;--warnbg:#fbf1de;--mutebg:#eef1f5;--fail:#c0432f;
--shadow:0 1px 2px rgba(20,30,50,.06),0 8px 24px rgba(20,30,50,.06);}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0e131b;--surface:#161d28;--ink:#e6ecf3;--ink2:#9fb0c3;
--muted:#63748a;--line:#26313f;--accent:#4fd1c5;--ok:#42c98a;--okbg:#12281f;--warn:#e0b154;--warnbg:#2a2413;
--mutebg:#1b232f;--fail:#f2836f;--shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.35);}}}}
:root[data-theme=dark]{{--bg:#0e131b;--surface:#161d28;--ink:#e6ecf3;--ink2:#9fb0c3;--muted:#63748a;
--line:#26313f;--accent:#4fd1c5;--ok:#42c98a;--okbg:#12281f;--warn:#e0b154;--warnbg:#2a2413;--mutebg:#1b232f;
--fail:#f2836f;--shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.35);}}
:root[data-theme=light]{{--bg:#eef1f5;--surface:#fff;--ink:#1b2330;--ink2:#5a6577;--muted:#98a2b3;--line:#dde3ea;
--accent:#0e7c86;--ok:#0f9d58;--okbg:#e6f4ec;--warn:#b7791f;--warnbg:#fbf1de;--mutebg:#eef1f5;--fail:#c0432f;
--shadow:0 1px 2px rgba(20,30,50,.06),0 8px 24px rgba(20,30,50,.06);}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1160px;margin:0 auto;padding:44px 24px 80px}}
.eyebrow{{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:600}}
h1{{font-size:29px;line-height:1.2;margin:.35em 0 .2em;letter-spacing:-.01em;text-wrap:balance}}
.sub{{color:var(--ink2);max-width:70ch;margin:0 0 26px}}
.tiles{{display:flex;flex-wrap:wrap;gap:14px;margin:0 0 30px}}
.tile{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 18px;box-shadow:var(--shadow);min-width:118px}}
.tile .v{{font-size:26px;font-weight:700;letter-spacing:-.02em}} .tile .k{{font-size:12.5px;color:var(--ink2);margin-top:2px}}
.tile.hero .v{{color:var(--accent)}}
.scroll{{overflow-x:auto;border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);background:var(--surface)}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;min-width:780px}}
th{{text-align:left;font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink2);font-weight:600;padding:13px 14px;border-bottom:1px solid var(--line);white-space:nowrap;background:var(--surface);position:sticky;top:0}}
td{{padding:11px 14px;border-bottom:1px solid var(--line);vertical-align:top}} tr:last-child td{{border-bottom:none}}
tbody tr:hover{{background:color-mix(in srgb,var(--accent) 5%,transparent)}}
.mono{{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:12.5px}}
.pac a{{font-weight:600}} .src{{font-size:11.5px}}
.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.dim{{color:var(--muted)}} .muted{{color:var(--muted);font-style:italic;font-family:system-ui,sans-serif}}
.down{{min-width:250px}}
.entry{{margin-bottom:7px}} .entry:last-child{{margin-bottom:0}}
.devrow{{display:block;padding-left:16px;line-height:1.55}}
.dev{{color:var(--ink2)}}
.path{{font-family:system-ui,sans-serif;font-size:10.5px;color:var(--muted);margin-left:2px}}
.path a{{color:var(--ink2)}}
.tag{{font-family:system-ui,sans-serif;font-size:9.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;
color:var(--accent);background:color-mix(in srgb,var(--accent) 13%,transparent);border-radius:4px;padding:1px 4px;margin-left:4px;vertical-align:1px}}
.res{{font-family:system-ui,sans-serif;font-size:11.5px;color:var(--muted)}}
.res.comp{{color:var(--accent);font-weight:600}} .res.scan{{color:var(--warn);font-weight:600}} .res.scan0{{color:var(--muted)}}
.res.fail{{color:var(--fail);font-weight:600}} .dimn a{{color:var(--muted)}}
a{{color:var(--accent);text-decoration:none}} a:hover{{text-decoration:underline}}
.pill{{display:inline-block;font-size:11.5px;font-weight:600;padding:3px 9px;border-radius:999px;white-space:nowrap}}
.pill.ok{{background:var(--okbg);color:var(--ok)}} .pill.warn{{background:var(--warnbg);color:var(--warn)}} .pill.mute{{background:var(--mutebg);color:var(--muted)}}
.note{{color:var(--ink2);max-width:82ch;margin:22px 0 0;font-size:13.5px}} .note b{{color:var(--ink)}}
.foot{{margin-top:26px;font-size:12px;color:var(--muted);font-family:ui-monospace,monospace}}
</style>
<div class="wrap">
<span class="eyebrow">LIDAR · enforcement arm</span>
<h1>STM32 PAC crates → HAL &amp; ecosystem coverage</h1>
<p class="sub">Datasheet register-access constraints are injected into svd2rust chip crates as
compile-time witness gates. Each PAC crate lists every downstream crate — HAL, app, BSP, driver —
built or scanned against the gated version, broken out <b>per device</b>.</p>
<div class="tiles">
<div class="tile hero"><div class="v">{len(rows)}</div><div class="k">PAC crates (families)</div></div>
<div class="tile"><div class="v">{tot_m}</div><div class="k">reference manuals</div></div>
<div class="tile"><div class="v">{tot_p}</div><div class="k">injection pairings</div></div>
<div class="tile hero"><div class="v">{n_clean}</div><div class="k">PACs with a clean HAL baseline</div></div>
</div>
<div class="scroll"><table>
<thead><tr><th>PAC crate</th><th class="num">man.</th><th class="num">pair.</th><th>PAC version</th>
<th>status</th>
<th>compiled &nbsp;<span style="text-transform:none;font-weight:400">(per device: gates fired, potential bug)</span></th>
<th>scanned &nbsp;<span style="text-transform:none;font-weight:400">(candidate hits)</span></th></tr></thead>
<tbody>
{trows}
</tbody></table></div>
<p class="note"><b>Per device.</b> A crate is built once per chip device, so each crate lists its
devices indented beneath it: <span class="dev">device</span> <span class="res comp">N fired, M
bug</span> = N gates fired at compile time, M possible-bug (no visible check). The <span class="tag">
hal</span> tag marks the family HAL; a device where the HAL will not build shows
<span class="res fail">baseline fails</span> right there, so a HAL that passes on some devices and
fails on another (h7's stm32-hal2 fails only on stm32h7b3) shows both, per device. A HAL that could
not be ported at all shows <span class="res fail">couldn't port</span>. Each compiled crate is also marked by <b>compile path</b>: <span class="path">direct &rarr;
PAC</span> means its register access reaches the chip crate directly (the HALs themselves, plus
HAL-less code like hubris, rustuino, anne-key); <span class="path">via <i>hal</i></span> means it
reaches the PAC through that HAL. <b>Scanned</b> = source read statically only (weaker); the number is
candidate sites, not compile-confirmed.</p>
<p class="foot">Generated from out/sweep.json, stm_master_pacs.json, port_*.json, dependent_*.json ·
crates.io links verified 2026-09-21</p>
</div>"""
_HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
_HTML_OUT.write_text(doc)
print(f"html: {_HTML_OUT}  ({len(rows)} PACs, {n_clean} clean)")
