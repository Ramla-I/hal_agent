#!/usr/bin/env python3
"""The per-manual tracking table: what was extracted, what got enforced, what
compiled, and -- where nothing could be compiled -- exactly why.

One row per (reference manual, chip, HAL crate). Every number is READ
FROM A PIPELINE ARTIFACT, never hand-entered, so re-running this after the
pipeline produces more manuals refreshes the whole table:

  constraints found       generator run dir: access_constraints_v2 per register
  judge verdict           constraint_validation/validated.jsonl (enforcement)
  applied to the PAC      injection report rows with fate == "planned"
                          (their structured `kinds` counts)
  where the rest went     the other fates in the same report
  compilation             stm_sweep.py results (baseline + error classification)
  blocked-HAL notes       hal_gap.py + old_pac_probe.py + a crates.io
                          reverse-dependency sweep

Writes a CSV (for tracking / spreadsheets) and a Markdown table.

Usage:
    python applications/pac_codegen/experiments/tracking_table.py
    python applications/pac_codegen/experiments/tracking_table.py --no-network
"""

import argparse
import collections
import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR / "experiments"))
from stm_sweep import TARGETS, DATA  # noqa: E402

OUT = APP_DIR / "experiments" / "out"
DOC = APP_DIR.parent.parent / "docs" / "injection_tracking.md"

# Grammar-v2 kinds, in the order they are reported.
KINDS = ["state_gate", "sequence", "write_once", "clock_gate", "delay",
         "read_effect", "value_relation", "other"]

# Which sweep result files to merge (later files win per (rm, consumer)).
SWEEP_FILES = ["sweep.json", "sweep_hal.json", "sweep_hal2.json",
               "sweep_opsel.json", "sweep_alias.json"]

UA = {"User-Agent": "hal_agent-research (ramla.ijaz@yale.edu)"}


# --------------------------------------------------------------------------- #
# Sources
# --------------------------------------------------------------------------- #

def constraints_found(rm: str) -> collections.Counter:
    """Raw generator output: every grammar-v2 constraint the extractor emitted
    for this manual, by kind. This is the denominator."""
    run = DATA / f"agent_output/stm/{rm}/1"
    c = collections.Counter()
    if not run.is_dir():
        return c
    for f in run.iterdir():
        if not f.is_file() or f.name.startswith("."):
            continue
        try:
            d = json.loads(f.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(d, dict):
            continue
        for g in (d.get("access_constraints_v2") or []):
            c[g.get("kind", "?")] += 1
    return c


def raw_kinds_by_index(rm: str) -> dict:
    """(register file, v2 index) -> kind, straight from the generator output.

    A constraint rejected for failing grammar-v2 validation has no PARSED kind
    for the report to carry, but it still has a kind in the raw output -- and
    that is often the interesting part (a whole kind failing validation looks
    identical to scattered noise without it)."""
    run = DATA / f"agent_output/stm/{rm}/1"
    out = {}
    if not run.is_dir():
        return out
    for f in run.iterdir():
        if not f.is_file() or f.name.startswith("."):
            continue
        try:
            d = json.loads(f.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(d, dict):
            continue
        for i, g in enumerate(d.get("access_constraints_v2") or []):
            out[(f.name, i)] = g.get("kind", "?")
    return out


def judge_verdicts(rm: str) -> dict:
    """validated.jsonl: kind -> {enforce, doc_only, drop}.

    NOTE the denominator: this file holds only the constraints that SURVIVED
    the stage-0 collection lint, so its total is smaller than the raw
    generator count. `judge says enforce` is a fraction of `reach the judge`,
    never of `constraints found`."""
    p = DATA / f"evaluation/stm/{rm}/1/{rm}_constraints_review.jsonl"
    if not p.is_file():
        p = DATA / f"agent_output/stm/{rm}/1/constraint_validation/validated.jsonl"
    out = collections.defaultdict(collections.Counter)
    if not p.is_file():
        return out
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        kind = (r.get("constraint") or {}).get("kind") or r.get("kind") or "?"
        enf = r.get("enforcement", "")
        if r.get("tp_fp") == "FP":
            enf = "drop"
        elif r.get("tp_fp") == "TP" and enf == "drop":
            enf = "doc_only"
        out[kind][enf] += 1
    return out


def injection_report(rm: str, device: str) -> dict:
    """The most RECENT report for this target. A dry run and a real run produce
    identical selection (the prune runs either way), so freshness is what
    matters — an older file predates report-schema changes and would silently
    report zeros."""
    cands = [OUT / f"{rm}_{device}.json", OUT / f"{rm}_{device}_dry.json"]
    cands = [p for p in cands if p.is_file()]
    if not cands:
        return {}
    newest = max(cands, key=lambda p: p.stat().st_mtime)
    return json.loads(newest.read_text())


def sweep_results() -> dict:
    """(rm, consumer crate) -> classified compile result."""
    out = {}
    for name in SWEEP_FILES:
        p = OUT / name
        if not p.is_file():
            continue
        for r in json.loads(p.read_text()):
            for h in (r.get("hal_results") or
                      ([r["hal_result"]] if r.get("hal_result") else [])):
                if not h:
                    continue
                crate = h.get("crate") or r.get("hal")
                out[(r["rm"], crate)] = {
                    "version": h.get("version", ""),
                    "baseline": h.get("baseline"),
                    "status": h.get("status", "ran"),
                    "true_enforcement": h.get("true_enforcement"),
                    "generic_friction": h.get("generic_friction"),
                    "other": h.get("other"),
                    "files": (h.get("files") or {}).get("true_enforcement", []),
                }
            if r.get("probe") and r["probe"] != "-":
                out.setdefault((r["rm"], "__probe__"), {})["probe"] = r["probe"]
    return out


def gap_notes() -> dict:
    """PAC crate -> why its community HAL cannot be used (from hal_gap.py)."""
    p = OUT / "hal_gap.json"
    if not p.is_file():
        return {}
    out = {}
    for r in json.loads(p.read_text()):
        if r.get("errors") or r.get("status") in ("PATCH_UNUSED", "TIMEOUT"):
            bc = r.get("by_code") or {}
            top = max(bc, key=bc.get) if bc else ""
            out[r["pac"]] = {
                "hal": r["hal"], "hal_version": r["hal_version"],
                "req": r.get("spoof"), "errors": len(r.get("errors", [])),
                "top_code": top, "top_n": bc.get(top, 0),
            }
    return out


# Last-commit dates (GitHub) for the community HALs that cannot be used, so the
# "why not" note says whether waiting for upstream is realistic.
def hal_activity(no_network: bool) -> dict:
    repos = {
        "stm32f0xx-hal": "stm32-rs/stm32f0xx-hal",
        "stm32f3xx-hal": "stm32-rs/stm32f3xx-hal",
        "stm32l0xx-hal": "stm32-rs/stm32l0xx-hal",
        "stm32l1xx-hal": "stm32-rs/stm32l1xx-hal",
        "stm32f7xx-hal": "stm32-rs/stm32f7xx-hal",
    }
    out = {}
    if no_network:
        return out
    for name, repo in repos.items():
        try:
            req = urllib.request.Request(
                f"https://api.github.com/repos/{repo}/commits?per_page=1",
                headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read().decode())
            if isinstance(d, list) and d:
                out[name] = d[0]["commit"]["committer"]["date"][:10]
        except Exception:                                     # noqa: BLE001
            pass
        time.sleep(0.4)
    return out


# The community HAL each PAC family has, and whether ANY crates.io consumer is
# on PAC 0.16 (established by the reverse-dependency sweep; see
# docs/stm_injection_sweep.md §1).
FAMILY_HAL = {
    "stm32f0": "stm32f0xx-hal", "stm32f1": "stm32f1xx-hal",
    "stm32f2": None, "stm32f3": "stm32f3xx-hal", "stm32f4": "stm32f4xx-hal",
    "stm32l0": "stm32l0xx-hal", "stm32l1": "stm32l1xx-hal",
}


def build_note(t, res, gaps, activity) -> str:
    """Why this row has (or has not) a compile result against a HAL."""
    if res:
        if res.get("status") == "PATCH_UNUSED":
            return "INVALID: cargo did not apply the local PAC patch"
        if res.get("baseline") != "PASS":
            return f"baseline against pristine PAC: {res.get('baseline')}"
        return ""
    hal = FAMILY_HAL.get(t.pac)
    if hal is None:
        return (f"no HAL crate exists for {t.pac} at any PAC version, and "
                "nothing else on crates.io depends on it")
    g = gaps.get(t.pac)
    bits = [f"{hal} is on an older PAC"]
    if g:
        bits = [f"{hal} {g['hal_version']} needs PAC {g['req']}; forced "
                f"onto 0.16 it fails with {g['errors']} errors "
                f"({g['top_n']}x {g['top_code']}) - a port, not a version bump"]
    if hal in activity:
        bits.append(f"last upstream commit {activity[hal]}")
    bits.append(f"no other crates.io consumer of {t.pac} is on 0.16 either")
    return "; ".join(bits)


# --------------------------------------------------------------------------- #
# Table
# --------------------------------------------------------------------------- #

def kinds_str(counter, sep=", ") -> str:
    parts = [f"{k}={counter[k]}" for k in KINDS if counter.get(k)]
    extra = [f"{k}={v}" for k, v in sorted(counter.items())
             if k not in KINDS and v]
    return sep.join(parts + extra) or "—"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-network", action="store_true",
                    help="skip the GitHub activity lookup")
    args = ap.parse_args()

    sweeps = sweep_results()
    gaps = gap_notes()
    activity = hal_activity(args.no_network)

    rows = []
    for t in TARGETS:
        found = constraints_found(t.rm)
        verdicts = judge_verdicts(t.rm)
        rep = injection_report(t.rm, t.device)

        applied = collections.Counter()
        via_alias = 0
        elsewhere = collections.defaultdict(collections.Counter)
        raw_kinds = raw_kinds_by_index(t.rm)
        for r in rep.get("rows", []):
            ks = r.get("kinds") or ({r["kind"]: 1} if r.get("kind") else {})
            if not ks and r.get("constraints"):
                # Recover the kind of a constraint that never parsed.
                ks = collections.Counter(
                    raw_kinds.get((r["file"], i), "unparseable")
                    for i in r["constraints"] if i is not None)
            if r["fate"] == "planned":
                applied.update(ks)
                if r.get("via_alias"):
                    via_alias += sum(ks.values())
            else:
                for k, n in ks.items():
                    elsewhere[r["fate"]][k] += n

        enforce_total = sum(v.get("enforce", 0) for v in verdicts.values())
        enforce_kinds = collections.Counter(
            {k: v.get("enforce", 0) for k, v in verdicts.items()
             if v.get("enforce", 0)})
        probe = sweeps.get((t.rm, "__probe__"), {}).get("probe", "—")

        consumers = t.consumers or [None]
        for c in consumers:
            res = sweeps.get((t.rm, c.crate)) if c else None
            rows.append({
                "RM": t.rm,
                "device": t.device,
                "pac_crate": f"{t.pac} 0.16.0",
                "constraints_found_raw": sum(found.values()),
                "found_by_kind_raw": kinds_str(found),
                "validator_enforce": enforce_total,
                "validator_enforce_by_kind": kinds_str(enforce_kinds),
                "enforced": sum(applied.values()),
                "enforced_by_kind": kinds_str(applied),
                "enforced_via_instance_alias": via_alias,
                "registers_gated": rep.get("registers_planned", 0),
                "pac_compiles": probe,
                "hal_crate": (f"{c.crate} {c.version}" if c else "—"),
                "hal_baseline": (res or {}).get("baseline", "—"),
                "true_enforcement": (res or {}).get("true_enforcement", "—"),
                "generic_friction": (res or {}).get("generic_friction", "—"),
                "other_errors": (res or {}).get("other", "—"),
                "enforcement_sites": ", ".join((res or {}).get("files", [])) or "—",
                "dropped_by_stage": "; ".join(
                    f"{fate}: {kinds_str(cnt, ',')}"
                    for fate, cnt in sorted(elsewhere.items())) or "—",
                "note": build_note(t, res, gaps, activity),
            })

    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "tracking.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"csv: {csv_path}")

    # ---- Markdown ----
    md = ["# Injection tracking table",
          "",
          "Generated by `applications/pac_codegen/experiments/tracking_table.py`",
          "— every number is read from a pipeline artifact, so re-running the",
          "script after new manuals land refreshes the table. One row per",
          "(reference manual, chip, HAL crate).",
          "",
          "**PAC** = the generated register-access crate for a chip family",
          "(e.g. `stm32f3`); constraints are injected here. **HAL** = a",
          "higher-level driver crate built on it (e.g. `stm32-hal2`); these are",
          "compiled UNMODIFIED against the injected PAC.",
          "",
          "**Each column is a different stage — and they have different",
          "denominators.** The pipeline is:",
          "",
          "```",
          "generator  ->  collection lint  ->  judge  ->  emitter + device prune",
          "```",
          "",
          "- `constraints found` / `found by kind` = **RAW generator output**,",
          "  before any validation, lint, or de-duplication.",
          "- `validator says enforce` = confirmed by the closed-book judge AND",
          "  witness-enforceable. Its denominator is what survived the stage-0",
          "  collection lint (SVD-resolvable name, valid grammar v2, no",
          "  placeholder, de-duplicated) — NOT the raw count, which is always",
          "  larger. The shortfall is itemised under `where the rest went`.",
          "- `of which via instance alias` — svd2rust gives every peripheral",
          "  INSTANCE a type alias over one shared register-block module",
          "  (`pub type I2C2 = crate::Periph<i2c1::RegisterBlock, ...>`), so",
          "  `i2c2.rs` does not exist and I2C2's registers ARE `i2c1`'s types.",
          "  Constraints extracted for a non-first instance are resolved through",
          "  that map instead of being discarded. Because instances share the",
          "  type, such a gate necessarily covers EVERY instance of the block.",
          "- `enforced` = what actually became **compile-time gates**,",
          "  after the emitter (only `state_gate` has an emitter today) and the",
          "  device-level prune. Every other kind is accounted for under",
          "  `where the rest went`, with the stage that dropped it.",
          "",
          "## Extraction → enforcement",
          "",
          "| RM | device | PAC crate | constraints found (raw) | found by kind (raw) | validator says enforce | validator enforce by kind | enforced | enforced by kind | of which via instance alias | registers gated | PAC still compiles |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    seen = set()
    for r in rows:
        if r["RM"] in seen:
            continue
        seen.add(r["RM"])
        md.append(
            f"| {r['RM']} | {r['device']} | {r['pac_crate']} | "
            f"{r['constraints_found_raw']} | {r['found_by_kind_raw']} | "
            f"{r['validator_enforce']} | {r['validator_enforce_by_kind']} | "
            f"**{r['enforced']}** | {r['enforced_by_kind']} | "
            f"{r['enforced_via_instance_alias']} | "
            f"{r['registers_gated']} | {r['pac_compiles']} |")

    md += ["", "## Compilation against real HAL crates", "",
           "| RM | device | HAL crate | baseline vs pristine PAC | true enforcement errors | generic friction | other errors | enforcement sites | note (why no HAL) |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(
            f"| {r['RM']} | {r['device']} | {r['hal_crate']} | "
            f"{r['hal_baseline']} | {r['true_enforcement']} | "
            f"{r['generic_friction']} | {r['other_errors']} | "
            f"{r['enforcement_sites']} | {r['note'] or '—'} |")

    md += ["", "## Where the non-applied constraints went", "",
           "| RM | stage → kinds dropped there |", "|---|---|"]
    seen = set()
    for r in rows:
        if r["RM"] in seen:
            continue
        seen.add(r["RM"])
        md.append(f"| {r['RM']} | {r['dropped_by_stage']} |")

    md += ["", "---", "",
           "**Fate glossary** — `rejected_at_collection`: stage-0 lint (name not "
           "resolvable in the SVD, fails grammar-v2 validation, placeholder "
           "name). `gated_out_by_validator`: the closed-book judge called it "
           "`doc_only` or `drop`. `kind_not_emitted`: no codegen emitter for "
           "that grammar kind yet. `peripheral_not_in_device`: the manual covers "
           "a family; this chip lacks that peripheral. `emitter_rejected`: "
           "nothing enforceable left, or a non-identifier field name. "
           "`pruned_for_device`: not expressible against the generated PAC "
           "(access mode or field-reader shape). "
           "`target_unverified_by_location`: the supporting quote could not be "
           "anchored to the target register's section.", ""]

    DOC.write_text("\n".join(md))
    print(f"markdown: {DOC}")


if __name__ == "__main__":
    main()
