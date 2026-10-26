#!/usr/bin/env python3
"""Join rm_pac_mappings/stm.toml x available pipeline data x live crates.io index.

Produces the RM -> SVD -> PAC crate/device-module -> HAL-consumer map that the
injection + HAL-adoption runs consume, and RE-VERIFIES every HAL pairing
against the crates.io sparse index (stm.toml's data was checked 2026-07-16).

Usage:
    python applications/pac_codegen/experiments/build_map.py   # -> out/injection_map.json
"""
import json
import sys
import tomllib
import urllib.request
from pathlib import Path

REPO = Path("/home/ramla/hal_agent-pac-injection")
DATA = Path("/home/ramla/hal_agent-phase-1d")
TARGETS = REPO / "applications/pac_codegen/rm_pac_mappings/stm.toml"
PAC_VERSION = "0.16.0"


def index_prefix(name):
    if len(name) == 1:
        return "1"
    if len(name) == 2:
        return "2"
    if len(name) == 3:
        return f"3/{name[0]}"
    return f"{name[:2]}/{name[2:4]}"


_CACHE = {}


def index(crate):
    if crate in _CACHE:
        return _CACHE[crate]
    url = f"https://index.crates.io/{index_prefix(crate)}/{crate}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            rows = [json.loads(l) for l in r.read().decode().splitlines() if l.strip()]
    except Exception as e:                                    # noqa: BLE001
        rows = []
        print(f"  !! index fetch failed for {crate}: {e}", file=sys.stderr)
    _CACHE[crate] = rows
    return rows


def caret_matches_0_16(req: str) -> bool:
    """Does a cargo version req admit 0.16.0? Handles the shapes that appear
    in these manifests: '^0.16.0', '0.16', '=0.16.0', '^0.15.1' (no)."""
    r = req.strip().lstrip("^")
    if r.startswith("="):
        return r[1:].strip().startswith("0.16")
    if r.startswith((">=", "<", ">")):        # ranges: be conservative
        return "0.16" in r
    parts = r.split(".")
    # 0.x semver: compatible iff major AND minor match
    return len(parts) >= 2 and parts[0] == "0" and parts[1] == "16"


def hal_versions_on_pac(hal: str, pac: str):
    """Released, non-yanked HAL versions whose dep on `pac` admits 0.16.0."""
    hits = []
    for row in index(hal):
        if row.get("yanked"):
            continue
        for d in row.get("deps", []):
            if d.get("name") == pac and d.get("kind") in (None, "normal") \
                    and caret_matches_0_16(d.get("req", "")):
                hits.append((row["vers"], d["req"], d.get("features", [])))
                break
    return hits


def vkey(v):
    out = []
    for p in v.split("-")[0].split("."):
        out.append(int(p) if p.isdigit() else 0)
    return out


def main():
    cfg = tomllib.loads(TARGETS.read_text())
    rows = []
    for m in cfg["manual"]:
        rm = m["id"]
        validated = DATA / f"agent_output/stm/{rm}/1/constraint_validation/validated.jsonl"
        review = DATA / f"evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl"
        run_dir = DATA / f"agent_output/stm/{rm}/1"
        svd_dir = DATA / f"devices/stm/{rm}/svd"
        chunks = DATA / "chunked_datasheets/stm" / rm
        if not validated.is_file():
            continue
        recs = [json.loads(l) for l in validated.read_text().splitlines() if l.strip()]
        enforce = sum(1 for r in recs if r.get("enforcement") == "enforce")
        consumers = m.get("consumer", [])
        rows.append({
            "rm": rm,
            "pac": m["pac"]["crate"],
            "pac_version": m["pac"]["version"],
            "devices": m["devices"],
            "svds": sorted(p.name for p in svd_dir.glob("*.svd")) if svd_dir.is_dir() else [],
            "run_dir": str(run_dir),
            "svd_dir": str(svd_dir),
            "review": str(review) if review.is_file() else None,
            "chunks_root": str(DATA / "chunked_datasheets/stm") if chunks.is_dir() else None,
            "n_constraints": len(recs),
            "n_enforce": enforce,
            "consumers": consumers,
        })

    print(f"{len(rows)} RMs with validated constraint data\n")

    # --- re-verify HAL pairings live ---
    checked = {}
    for r in rows:
        for c in r["consumers"]:
            key = (c["name"], r["pac"])
            if key in checked:
                continue
            hits = hal_versions_on_pac(c["name"], r["pac"])
            hits.sort(key=lambda h: vkey(h[0]))
            checked[key] = hits
            r_status = c.get("status", "?")
            newest = hits[-1] if hits else None
            print(f"{c['name']:16s} -> {r['pac']:8s}  stm.toml={r_status:12s}  "
                  f"live: {'v' + newest[0] + ' (req ' + newest[1] + ')' if newest else 'NO released version on 0.16'}")

    for r in rows:
        for c in r["consumers"]:
            hits = checked[(c["name"], r["pac"])]
            c["live_pairing"] = hits[-1][0] if hits else None
            c["live_req"] = hits[-1][1] if hits else None

    out = REPO / "applications/pac_codegen/experiments/out/injection_map.json"
    out.write_text(json.dumps({"pac_version": PAC_VERSION, "rms": rows}, indent=1) + "\n")
    print(f"\nmap: {out}")

    print("\n| RM | constraints | enforce | PAC crate | device modules | HAL consumer | released pairing |")
    print("|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: -x["n_enforce"]):
        mods = ",".join(sorted({d["feature"] for d in r["devices"] if d["feature"]}))
        cons = r["consumers"][0]["name"] if r["consumers"] else "—"
        pair = (r["consumers"][0].get("live_pairing") or "none") if r["consumers"] else "—"
        print(f"| {r['rm']} | {r['n_constraints']} | {r['n_enforce']} | {r['pac']} "
              f"| {mods} | {cons} | {pair} |")


if __name__ == "__main__":
    main()
