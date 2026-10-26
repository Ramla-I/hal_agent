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

This script only JOINS artifacts -- it runs no injection and no compiler. Any
column whose artifact is missing shows as empty, so produce them first:

    # from the repo root, with the venv that has pydantic
    python applications/pac_codegen/get_pac.py --crate stm32f4 --version 0.16.0
    #   ... one per PAC crate the corpus needs (f0 f1 f2 f3 f4 l0 l1)

    python applications/pac_codegen/experiments/stm_sweep.py --dry-run
    #   -> out/<rm>_<device>_dry.json   (extraction/enforcement columns; fast,
    #      no cargo needed -- enough for the whole first table on its own)

    python applications/pac_codegen/experiments/stm_sweep.py
    #   -> out/sweep.json               (compile columns; needs cargo, ~1h)

    python applications/pac_codegen/experiments/hal_gap.py
    #   -> out/hal_gap.json             (the "why no HAL" notes; needs cargo)

    python applications/pac_codegen/experiments/gen_injection_tracking_artifact.py
    #   -> docs/artifacts/injection_tracking.{md,html} + out/tracking.csv

`--no-network` skips the GitHub last-commit lookup used in the blocked-HAL
notes. Sweep result files are merged in SWEEP_FILES order, later wins, so a
re-measured run can be added there without discarding the earlier ones.

Usage:
    python applications/pac_codegen/experiments/gen_injection_tracking_artifact.py
    python applications/pac_codegen/experiments/gen_injection_tracking_artifact.py --no-network
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
from stm_sweep import (TARGETS, UNMAPPED, DATA, Consumer,  # noqa: E402
                       CONTROL_DEVICES, MASTER_TARGETS)

OUT = APP_DIR / "experiments" / "out"
DOC = APP_DIR.parent.parent / "docs" / "artifacts" / "injection_tracking.md"

# Grammar-v2 kinds, in the order they are reported.
KINDS = ["state_gate", "sequence", "write_once", "clock_gate", "delay",
         "read_effect", "value_relation", "other"]

# Which sweep result files to merge (later files win per (rm, consumer)).
# The earlier files are partial runs kept for provenance; `sweep_all48.json`
# is the whole-corpus re-measurement (every target, every consumer, one code
# version) and must merge LAST so it wins wherever the two disagree.
# ONE run per mode, not a merge. These used to be lists of a dozen partial
# sweeps combined later-wins, because the corpus was measured in pieces as it
# grew. That is now a liability: a number from a months-old partial run can
# outlive the code that produced it, and the merged table carried 48 driver
# pairings where a single clean run finds 43.
SWEEP_FILES = ["register_only/sweep.json"]      # baseline: whole-register only

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


def injection_report(rm: str, device: str, field_gating: bool = False) -> dict:
    """The most RECENT report for this target IN THIS GATING MODE.

    The mode is part of the filename, not a tiebreak on mtime. The two modes
    plan different gate sets, and while they shared a name a field-gating run
    overwrote the default run's reports -- after which the table published one
    mode's registers and kinds under the other's heading.

    Within a mode, a dry run and a real run select identically (the prune runs
    either way), so freshness is what matters: an older file predates report
    schema changes and would silently report zeros."""
    # The two modes write to separate TREES now, not one tree with suffixed
    # filenames -- a shared path is what let a field run overwrite the default
    # run's numbers and the table publish one as the other.
    root = OUT if field_gating else OUT / "register_only"
    cands = [root / f"{rm}_{device}.json",
             root / f"{rm}_{device}_dry.json"]
    cands = [p for p in cands if p.is_file()]
    if not cands:
        return {}
    newest = max(cands, key=lambda p: p.stat().st_mtime)
    return json.loads(newest.read_text())


# Field-level gating is a SECOND configuration of the same injector, not a
# newer measurement of the first, so its results are read from their own file
# and shown beside the default rather than merged into it. Both columns are
# live numbers from a real 49-target build.
FIELD_SWEEP_FILES = ["sweep.json"]              # default: field-level gating


def sweep_results(files=None) -> dict:
    """(rm, device, consumer crate) -> classified compile result.

    The device belongs in the key. RM0440 is injected into two different G4
    parts and each is measured against its own consumers; keying on (rm,
    crate) alone silently collapsed them, so one chip's numbers overwrote the
    other's depending on file order."""
    out = {}
    for name in (files if files is not None else SWEEP_FILES):
        p = OUT / name
        if not p.is_file():
            continue
        for r in json.loads(p.read_text()):
            for h in (r.get("hal_results") or
                      ([r["hal_result"]] if r.get("hal_result") else [])):
                if not h:
                    continue
                crate = h.get("crate") or r.get("hal")
                out[(r["rm"], r.get("device", ""), crate)] = {
                    "version": h.get("version", ""),
                    "baseline": h.get("baseline"),
                    "status": h.get("status", "ran"),
                    "true_enforcement": h.get("true_enforcement"),
                    "guarded": h.get("guarded"),
                    "candidate": h.get("candidate"),
                    "untriaged": h.get("untriaged"),
                    "generic_friction": h.get("generic_friction"),
                    "other": h.get("other"),
                    "other_detail": (h.get("other_detail") or [])[:4],
                    "files": (h.get("files") or {}).get("true_enforcement", []),
                }
            if r.get("probe") and r["probe"] != "-":
                out.setdefault((r["rm"], r.get("device", ""),
                               "__probe__"), {})["probe"] = r["probe"]
            # The injection report on disk belongs to whichever mode ran last,
            # so the register count has to come from the sweep row itself or
            # the two columns would share one number.
            if r.get("planned") is not None:
                out.setdefault((r["rm"], r.get("device", ""),
                                "__planned__"), {})["planned"] = r["planned"]
    return out


def ported_results(field_gating: bool = False) -> dict:
    """(rm, device, crate) -> result for a HAL that only became measurable
    after its PAC dependency was upgraded (experiments/port_hal.py).

    Kept in the same shape as sweep_results so the table treats it the same
    way, but flagged `ported` so the row can say so. The upgrade is one the
    HAL owes its own dependency and touches only how register access is
    spelled -- but a reader still deserves to know which crate came off
    crates.io unmodified and which did not."""
    p = (OUT if field_gating else OUT / "register_only") / "measure_ported.json"
    if not p.is_file():
        return {}
    out = {}
    for r in json.loads(p.read_text()):
        if r.get("baseline") != "PASS":
            continue
        out[(r["rm"], r["device"], r["hal"])] = {
            "version": PORTED_VERSIONS.get(r["hal"], ""),
            "baseline": "PASS", "status": "ran", "ported": True,
            "true_enforcement": r["gate_fired"],
            "guarded": r["guarded"], "candidate": r["possible_bug"],
            "untriaged": r.get("untriaged", 0),
            "generic_friction": 0, "other": r["collateral"],
            "files": sorted({h["file"].split("/")[-1] for h in r["hits"]}),
        }
    return out


PORTED_VERSIONS = {"stm32l0xx-hal": "0.10.0", "stm32f0xx-hal": "0.18.0"}


def master_results() -> dict:
    """manual -> enforceability against a crate built from stm32-rs master.

    These count in the totals. The totals are about what was FOUND and
    APPLIED, and these manuals have no earlier version to be inconsistent
    with -- what matters is that the version is stated wherever it differs,
    which is why their PAC column reads `latest`."""
    p = OUT / "stm_master_pacs.json"
    if not p.is_file():
        return {}
    return {r["rm"]: r for r in json.loads(p.read_text())}

# Why a manual in a PORTED family still has no pairing. Read from the
# measurement report so it cannot drift from what actually ran.
def _ported_unpaired(field_gating: bool = False) -> dict:
    p = (OUT if field_gating else OUT / "register_only") / "measure_ported.json"
    if not p.is_file():
        return {}
    return {r["rm"]: r["unpaired_reason"] for r in json.loads(p.read_text())
            if r.get("unpaired_reason")}


PORTED_UNPAIRED = _ported_unpaired()


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
# The community HAL each family has, or None when none exists at any PAC
# version. Needed for every family we inject into, not just the measured ones:
# without an entry the note would claim "no HAL exists" for a family whose HAL
# merely sits on an older PAC.
FAMILY_HAL = {
    "stm32f0": "stm32f0xx-hal", "stm32f1": "stm32f1xx-hal",
    "stm32f2": None, "stm32f3": "stm32f3xx-hal", "stm32f4": "stm32f4xx-hal",
    "stm32f7": "stm32f7xx-hal", "stm32l0": "stm32l0xx-hal",
    "stm32l1": "stm32l1xx-hal", "stm32l4": "stm32l4xx-hal",
    "stm32g0": "stm32g0xx-hal", "stm32c0": "stm32c0xx-hal",
    "stm32wb": "stm32wb-hal",
}


# WHY a baseline fails, diagnosed from the recorded errors rather than
# hand-entered per pairing: the diagnosis is keyed to the ERROR PATTERN, so a
# future failure with a new cause falls through to its raw samples instead of
# wearing a stale explanation. Both current patterns are upstream stm32-hal2
# gaps against PAC 0.16 -- the same species the elodin port hit (missing GPIO
# J/K, missing embedded-hal I2C).
_BASELINE_DIAGNOSES = [
    ("unresolved import `crate::pac::DMA",
     "the H5-family PAC names its DMA engine GPDMA1 -- there is no DMA1 "
     "module -- while stm32-hal2's shared DAC/I2C/timer/USART code imports "
     "the old name, and everything downstream cascades"),
    ("`ADC3",
     "stm32-hal2's h7b3 feature gating still compiles its ADC3/SAI3 paths, "
     "but the H7B3's SVD (and therefore its PAC module) has neither "
     "peripheral -- a per-chip cfg map out of step with the part"),
]


def _baseline_fail_note(res) -> str:
    head = (f"baseline against pristine PAC: {res.get('baseline')}"
            + (f" ({res.get('other')} errors)" if res.get("other") else ""))
    samples = res.get("other_detail") or []
    blob = " ".join(samples)
    for needle, why in _BASELINE_DIAGNOSES:
        if needle in blob:
            return f"{head} — {why}. The driver never compiles against the "                    f"UNMODIFIED crate, so nothing after injection is "                    f"attributable; fixing this is an upstream stm32-hal2 "                    f"change, not a pipeline one"
    if samples:
        return f"{head} — e.g. {samples[0][:110]}"
    return head


def build_note(t, res, gaps, activity) -> str:
    """Why this row has (or has not) a compile result against a HAL."""
    if res and res.get("ported"):
        return ("HAL's PAC dependency upgraded to 0.16 by "
                "experiments/port_hal.py before measuring — mechanical edits "
                "only (rustc's own suggestions plus renames read off the PAC), "
                "verified not to touch control flow, and the baseline against "
                "the pristine PAC passes")
    if not res and FAMILY_HAL.get(t.pac) in PORTED_VERSIONS:
        # The family's HAL HAS been upgraded and measured elsewhere, so the
        # PAC-generation note below would be false here. Say what actually
        # blocks this chip instead.
        hal = FAMILY_HAL[t.pac]
        why = PORTED_UNPAIRED.get(t.rm)
        return (f"{hal} was upgraded to PAC 0.16 (experiments/port_hal.py) "
                f"and measured on this family's other manuals; "
                + (why or f"this chip has no matching {hal} feature"))
    if res:
        if res.get("status") == "PATCH_UNUSED":
            return "INVALID: cargo did not apply the local PAC patch"
        if res.get("baseline") != "PASS":
            return _baseline_fail_note(res)
        return ""
    if t.consumers:
        # A driver exists and is wired up; the compile sweep just has not
        # produced a result for it yet. Saying "no HAL" here would be wrong.
        return ("compile measurement not run yet — a driver crate on PAC 0.16 "
                "exists for this family")
    if t.pac not in FAMILY_HAL:
        return (f"no driver crate on {t.pac} 0.16 — the gates are injected and "
                "the crate compiles; there is simply nothing third-party to "
                "compile against")
    hal = FAMILY_HAL[t.pac]
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
    bits.append(f"no other crates.io consumer of {t.pac} is on 0.16 either. "
                "The gates ARE injected and the crate compiles — only the "
                "adoption measurement is missing")
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
    ported = ported_results()                 # baseline
    ported_fg = ported_results(field_gating=True)
    sweeps.update(ported)
    fsweeps = sweep_results(FIELD_SWEEP_FILES)
    gaps = gap_notes()
    activity = hal_activity(args.no_network)

    rows = []
    for t in TARGETS:
        found = constraints_found(t.rm)
        verdicts = judge_verdicts(t.rm)
        rep = injection_report(t.rm, t.device)

        raw_kinds = raw_kinds_by_index(t.rm)

        def fate_kinds(report):
            applied = collections.Counter()
            via_alias = 0
            elsewhere = collections.defaultdict(collections.Counter)
            for r in report.get("rows", []):
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
            return applied, via_alias, elsewhere

        applied, via_alias, elsewhere = fate_kinds(rep)
        # The fates table describes THE DEFAULT PIPELINE, which is field
        # gating. It used to read the register-only report, whose
        # `field_gating_disabled` fate is that mode's own policy -- so the
        # published table said field gating was off long after it became the
        # default. The baseline columns above keep their own report; only the
        # drop story switches.
        _, _, felsewhere = fate_kinds(
            injection_report(t.rm, t.device, field_gating=True))

        enforce_total = sum(v.get("enforce", 0) for v in verdicts.values())
        enforce_kinds = collections.Counter(
            {k: v.get("enforce", 0) for k, v in verdicts.items()
             if v.get("enforce", 0)})
        probe = sweeps.get((t.rm, t.device, "__probe__"), {}).get("probe", "—")

        fg_probe = fsweeps.get((t.rm, t.device, "__probe__"), {}).get("probe", "—")
        fg_rep = injection_report(t.rm, t.device, field_gating=True)
        fg_regs = fg_rep.get("registers_planned", "—")
        # Counted exactly as the default column is, so the two are comparable:
        # constraint instances on `planned` rows, with the kind recovered from
        # the raw generator output when the row did not carry one.
        fg_applied = 0
        for r in fg_rep.get("rows", []):
            if r["fate"] != "planned":
                continue
            ks = r.get("kinds") or ({r["kind"]: 1} if r.get("kind") else {})
            if not ks and r.get("constraints"):
                ks = collections.Counter(
                    raw_kinds.get((r["file"], i), "unparseable")
                    for i in r["constraints"] if i is not None)
            fg_applied += sum(ks.values())

        consumers = list(t.consumers or [])
        for (prm, pdev, pcrate), _v in ported.items():
            if prm == t.rm and pdev == t.device and not any(
                    c.crate == pcrate for c in consumers):
                consumers.append(Consumer(pcrate,
                                          PORTED_VERSIONS.get(pcrate, ""),
                                          [], note="PAC dependency upgraded"))
        consumers = consumers or [None]
        for c in consumers:
            res = sweeps.get((t.rm, t.device, c.crate)) if c else None
            fres = fsweeps.get((t.rm, t.device, c.crate)) if c else None
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
                "guarded": (res or {}).get("guarded", "—"),
                "candidate": (res or {}).get("candidate", "—"),
                "generic_friction": (res or {}).get("generic_friction", "—"),
                "other_errors": (res or {}).get("other", "—"),
                "enforcement_sites": ", ".join((res or {}).get("files", [])) or "—",
                # --- the same driver, measured with field-level gating on ---
                "fg_gates": fg_applied,
                "fg_registers_gated": fg_regs,
                "fg_pac_compiles": fg_probe,
                "fg_true_enforcement": (fres or {}).get("true_enforcement", "—"),
                "fg_guarded": (fres or {}).get("guarded", "—"),
                "fg_candidate": (fres or {}).get("candidate", "—"),
                "fg_generic_friction": (fres or {}).get("generic_friction", "—"),
                # pipeline order, not alphabetical: a row should read as the
                # path a constraint takes, so `rejected_at_collection` first.
                "dropped_by_stage": "; ".join(
                    f"{fate}: {kinds_str(felsewhere[fate], ',')}"
                    for fate, _s, _d in _STAGES if fate in felsewhere) or "—",
                "note": build_note(t, res, gaps, activity),
            })

    # Manuals with no chip crate to inject into still get a row. Omitting them
    # would make the corpus look smaller than it is, and "absent" would read
    # identically to "enforced nothing".
    master = master_results()
    for rm, (chip, crate, device) in sorted(MASTER_TARGETS.items()):
        found = constraints_found(rm)
        verdicts = judge_verdicts(rm)
        enforce_kinds = collections.Counter(
            {k: v.get("enforce", 0) for k, v in verdicts.items()
             if v.get("enforce", 0)})
        m = master.get(rm, {})
        rep = injection_report(rm, f"{device}_master")
        applied = collections.Counter()
        for r in rep.get("rows", []):
            if r["fate"] == "planned":
                ks = r.get("kinds") or ({r["kind"]: 1} if r.get("kind") else {})
                applied.update(ks)
        rows.append({
            "RM": rm, "device": device, "pac_crate": f"{crate} latest",
            "constraints_found_raw": sum(found.values()),
            "found_by_kind_raw": kinds_str(found),
            "validator_enforce": sum(v.get("enforce", 0)
                                     for v in verdicts.values()),
            "validator_enforce_by_kind": kinds_str(enforce_kinds),
            "enforced": sum(applied.values()) or 0,
            "enforced_by_kind": kinds_str(applied),
            "enforced_via_instance_alias": 0,
            "registers_gated": m.get("whole_registers", 0),
            "pac_compiles": m.get("probe", "—"),
            "hal_crate": "—", "hal_baseline": "—",
            "true_enforcement": "—", "guarded": "—", "candidate": "—",
            "generic_friction": "—", "other_errors": "—",
            "fg_gates": 0, "fg_registers_gated": m.get("field_registers", 0),
            "fg_pac_compiles": m.get("probe", "—"),
            "fg_true_enforcement": "—", "fg_guarded": "—",
            "fg_candidate": "—", "fg_generic_friction": "—",
            "enforcement_sites": "—",
            "dropped_by_stage": "—",
            "note": ("chip crate exists only on stm32-rs master "
                     f"({(m.get('stm32rs_commit') or '')[:12]}), not in the "
                     "0.16.0 release the rest of the corpus is pinned to; "
                     "no crates.io driver can depend on it, so gates are "
                     "measured but adoption is not"),
        })

    for rm, (chip, crate, found_n, enforce_n, why) in sorted(UNMAPPED.items()):
        found = constraints_found(rm)
        verdicts = judge_verdicts(rm)
        enforce_kinds = collections.Counter(
            {k: v.get("enforce", 0) for k, v in verdicts.items()
             if v.get("enforce", 0)})
        rows.append({
            "RM": rm, "device": chip, "pac_crate": "—",
            "constraints_found_raw": sum(found.values()) or found_n,
            "found_by_kind_raw": kinds_str(found),
            "validator_enforce": (sum(v.get("enforce", 0)
                                      for v in verdicts.values()) or enforce_n),
            "validator_enforce_by_kind": kinds_str(enforce_kinds),
            "enforced": 0, "enforced_by_kind": "—",
            "enforced_via_instance_alias": 0, "registers_gated": 0,
            "pac_compiles": "—", "hal_crate": "—", "hal_baseline": "—",
            "true_enforcement": "—", "guarded": "—", "candidate": "—",
            "generic_friction": "—",
            "fg_gates": "—", "fg_registers_gated": "—", "fg_pac_compiles": "—",
            "fg_true_enforcement": "—", "fg_guarded": "—",
            "fg_candidate": "—", "fg_generic_friction": "—",
            "other_errors": "—", "enforcement_sites": "—",
            "dropped_by_stage": "no_chip_crate: all",
            "note": (f"No chip crate covers {chip}. "
                     + (f"stm32-rs ships {crate} but no {chip} device module."
                        if crate else
                        f"stm32-rs 0.16 has no crate for this family.")
                     + " Extracted and judged; nothing to inject into. "
                     + why),
        })

    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "tracking.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"csv: {csv_path}")

    # ---- Markdown ----
    # Control injections are measurements ABOUT the corpus, not members of
    # it. Split here so the markdown, the CSV and the HTML all state the same
    # rule -- one device module per manual -- and the controls are reported
    # once, after the tables.
    control_rows = [r for r in rows if (r["RM"], r["device"]) in CONTROL_DEVICES]
    rows = [r for r in rows if (r["RM"], r["device"]) not in CONTROL_DEVICES]

    md = ["# Injection tracking table",
          "",
          "## Regenerating this table",
          "",
          "```sh",
          "# extraction/enforcement columns — fast, no cargo needed",
          "python applications/pac_codegen/experiments/stm_sweep.py --dry-run",
          "python applications/pac_codegen/experiments/gen_injection_tracking_artifact.py",
          "",
          "# the compile columns additionally need cargo (~1h) ...",
          "python applications/pac_codegen/experiments/stm_sweep.py",
          "# ... and the blocked-HAL notes need",
          "python applications/pac_codegen/experiments/hal_gap.py",
          "```",
          "",
          "PAC crates must be provisioned first (`get_pac.py --crate <c> "
          "--version 0.16.0`), and the pipeline outputs are read from the",
          "sibling `hal_agent-phase-1d` worktree (`DATA` in `stm_sweep.py`).",
          "",
          "Generated by `applications/pac_codegen/experiments/gen_injection_tracking_artifact.py`",
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
          "## The kinds of constraint",
          "",
          "What the grammar can express. Only `state_gate` has a code",
          "generator today; the rest are extracted and recorded, and appear",
          "under *where the rest went* as `kind_not_emitted`.",
          ""]
    md += [f"- **`{k}`** — {d}" for k, d in _KIND_DEFS]
    md += ["",
          "## Extraction → enforcement",
          "",
          "| # | RM | device | PAC crate | constraints found (raw) | found by kind (raw) | validator says enforce | validator enforce by kind | enforced | enforced by kind | of which via instance alias | registers gated | PAC still compiles |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in enumerate(per_manual(rows), start=1):
        md.append(
            f"| {n} | {r['RM']} | {r['device']} | {r['pac_crate']} | "
            f"{r['constraints_found_raw']} | {r['found_by_kind_raw']} | "
            f"{r['validator_enforce']} | {r['validator_enforce_by_kind']} | "
            f"**{r['enforced']}** | {r['enforced_by_kind']} | "
            f"{r['enforced_via_instance_alias']} | "
            f"{r['registers_gated']} | {r['pac_compiles']} |")

    md += ["", "## What each PAC enforces, and what could be compiled against it",
           "",
           "EVERY injected chip crate is listed. The gates and the "
           "`PAC compiles` check are independent of any driver — injection "
           "needs nothing from a HAL. Where no driver crate depends on PAC "
           "0.16, the HAL columns are empty and the note says why; the "
           "enforcement is still there.",
           "",
           "Two gating modes are shown. The default gates a whole register; "
           "`--field-level-gating` (opt-in) gates individual bitfields "
           "instead, reaching constraints the datasheet states about single "
           "bits at the cost of asking less of the driver elsewhere.",
           "",
           "| RM | device | PAC crate | gates | registers | PAC compiles | "
           "HAL crate | baseline | true enforcement | guarded | possible bug | "
           "generic friction | other | "
           "field: gates | field: registers | field: gate fired | "
           "field: possible bug | field: generic friction | "
           "enforcement sites | note |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(
            f"| {r['RM']} | {r['device']} | {r['pac_crate']} | "
            f"**{r['enforced']}** | {r['registers_gated']} | "
            f"{r['pac_compiles']} | {r['hal_crate']} | "
            f"{r['hal_baseline']} | {r['true_enforcement']} | "
            f"{r['guarded']} | {r['candidate']} | "
            f"{r['generic_friction']} | {r['other_errors']} | "
            f"{r['fg_gates']} | {r['fg_registers_gated']} | "
            f"{r['fg_true_enforcement']} | {r['fg_candidate']} | "
            f"{r['fg_generic_friction']} | "
            f"{r['enforcement_sites']} | {r['note'] or '—'} |")

    md += ["", "## Where the non-applied constraints went", "",
           "In the **default pipeline (field-level gating)**. The "
           "register-only baseline drops one extra class the default does "
           "not: constraints whose every restriction names a field "
           "(`field_gating_disabled`), which under the default become field "
           "gates instead.", "",
           "| RM | stage → kinds dropped there |", "|---|---|"]
    seen = set()
    for r in rows:
        if r["RM"] in seen:
            continue
        seen.add(r["RM"])
        md.append(f"| {r['RM']} | {r['dropped_by_stage']} |")

    md += ["", "---", "",
           "**Fate glossary**, in the order a constraint meets the stages:", ""]
    md += [f"{i}. `{fate}` ({short}) — {desc}"
           for i, (fate, short, desc) in enumerate(_STAGES, 1)]
    if control_rows:
        md += ["", "## Control: how much does the chip choice matter?", "",
               "Every table above follows one rule — **one device module per "
               "reference manual**, chosen so that every driver supporting "
               "that manual can select it. These manuals cover 154 device "
               "modules in total, so each row is one representative chip. "
               "One manual is injected a second time to measure how much that "
               "choice moves the numbers; it is excluded from every figure "
               "above.", "",
               "| RM | device | role | gates | registers | HAL crate | "
               "gate fired | guarded | possible bug |",
               "|---|---|---|---|---|---|---|---|---|"]
        for rm in sorted({r["RM"] for r in control_rows}):
            for r in ([x for x in rows if x["RM"] == rm]
                      + [x for x in control_rows if x["RM"] == rm]):
                role = ("control" if (r["RM"], r["device"]) in CONTROL_DEVICES
                        else "corpus")
                md.append(f"| {r['RM']} | {r['device']} | {role} | "
                          f"**{r['enforced']}** | {r['registers_gated']} | "
                          f"{r['hal_crate']} | {r['true_enforcement']} | "
                          f"{r['guarded']} | {r['candidate']} |")
        md += [""]
        for (rm, dev), why in sorted(CONTROL_DEVICES.items()):
            md.append(f"`{rm}` / `{dev}` — {why}")
        md += ["",
               "**One device at a time is a choice, not a limit of the "
               "technique.** The harness injects into a single device module "
               "from a pristine crate because `generic.rs` is patched "
               "crate-wide, which keeps attribution simple. In the 20 "
               "flat-layout crates the device modules are independent files, "
               "so several could be injected in one pass. Only `stm32h7` is "
               "deduplicated — 188 of its 430 peripheral modules are shared "
               "between devices — and there two devices' constraints can land "
               "on one Rust type, the same problem the instance-alias "
               "resolver already solves for peripherals. Revisiting it would "
               "buy coverage and variation, not new constraints: a manual is "
               "read once, and its constraints do not change with the chip "
               "they are applied to."]
    md += [""]

    DOC.write_text("\n".join(md))
    print(f"markdown: {DOC}")

    write_html(rows, DOC.with_suffix(".html"), control_rows)



# --------------------------------------------------------------------------- #
# HTML view: the same rows, but scrollable                                     #
# --------------------------------------------------------------------------- #

# Markdown wraps long cells, and several of these columns are genuinely long
# (a kind breakdown, a blocked-HAL note). The HTML view keeps every cell on one
# line and puts each table in its own horizontal scroll region, with the header
# row and the RM column pinned so context survives scrolling.

_CSS = """
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
  font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1180px;margin:0 auto;padding:40px 24px 72px;display:flex;flex-direction:column;gap:38px}
header{display:flex;flex-direction:column;gap:10px;border-left:3px solid var(--accent);padding-left:16px}
h1{margin:0;font-size:27px;line-height:1.2;letter-spacing:-.015em;text-wrap:balance;font-weight:640}
.sub{margin:0;color:var(--ink-dim);max-width:66ch}
.eyebrow{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:11px;letter-spacing:.13em;text-transform:uppercase;color:var(--accent);
}
section{display:flex;flex-direction:column;gap:12px}
h2{margin:0;font-size:17px;font-weight:640;letter-spacing:-.01em}
.note{margin:0;color:var(--ink-dim);font-size:13.5px;max-width:74ch}
.funnel{display:flex;flex-wrap:wrap;gap:10px}
.stat{
  background:var(--surface);border:1px solid var(--rule);border-radius:7px;
  padding:11px 15px;min-width:132px;flex:1 1 132px;
}
.stat .k{
  display:block;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-dim);
}
.stat .v{
  display:block;font-size:25px;font-weight:660;letter-spacing:-.02em;
  font-variant-numeric:tabular-nums;margin-top:3px;
}
.stat.hi .v{color:var(--accent)}
.scroll{
  overflow-x:auto;border:1px solid var(--rule);border-radius:8px;background:var(--surface);
}
table{border-collapse:separate;border-spacing:0;width:max-content;min-width:100%}
th,td{
  padding:9px 13px;text-align:left;white-space:nowrap;
  border-bottom:1px solid var(--rule);font-size:13px;vertical-align:top;
}
thead th{
  position:sticky;top:0;z-index:2;background:var(--surface-2);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;
  color:var(--ink-dim);font-weight:600;
}
tbody tr:last-child td{border-bottom:none}
tfoot td{
  border-top:2px solid var(--accent);border-bottom:none;
  background:var(--surface-2);font-weight:640;
  position:sticky;bottom:0;
}
tfoot td.pin{background:var(--surface-2);letter-spacing:.06em}
tbody tr:hover td{background:var(--surface-2)}
th.pin,td.pin{
  position:sticky;left:0;z-index:1;background:var(--surface);
  box-shadow:1px 0 0 var(--rule),6px 0 10px -8px var(--shadow);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-weight:600;
}
thead th.pin{z-index:3;background:var(--surface-2)}
/* Row numbers on the extraction table, so a row can be cited by number in
   discussion. The number column takes over as the leftmost sticky cell, and
   the RM column -- still sticky -- sits just behind it. Only the rightmost of
   the two carries the edge shadow, or the seam shows twice. */
.numbered th.rownum,.numbered td.rownum{
  position:sticky;left:0;z-index:1;background:var(--surface);
  width:2.9em;min-width:2.9em;text-align:right;
  font-variant-numeric:tabular-nums;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  color:var(--ink-dim);font-weight:500;box-shadow:none;
}
.numbered thead th.rownum{z-index:3;background:var(--surface-2)}
.numbered tbody tr:hover td.rownum{background:var(--surface-2)}
.numbered th.pin,.numbered td.pin{left:2.9em}
tbody tr:hover td.pin{background:var(--surface-2)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px}
.num{text-align:right;font-variant-numeric:tabular-nums;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.num.lead{font-weight:680;color:var(--accent)}
.num.ok{color:var(--ok);font-weight:640}
/* The two gating modes sit side by side, so the second one needs a tint that
   separates it without competing with the accent used for lead figures. */
th.alt,td.alt{background:color-mix(in oklab,var(--accent) 7%,transparent)}
tbody tr:hover td.alt{background:color-mix(in oklab,var(--accent) 13%,transparent)}
tfoot td.alt{background:color-mix(in oklab,var(--accent) 12%,var(--surface-2))}
th.grp{
  text-align:center;font-size:11.5px;letter-spacing:.07em;text-transform:uppercase;
  color:var(--ink-dim);font-weight:640;border-bottom:1px solid var(--rule);
  padding-top:10px;padding-bottom:6px;
}
th.grp.mode{color:var(--ink)}
th.grp code{font-size:10.5px;text-transform:none;letter-spacing:0}
.dim{color:var(--ink-dim)}
.kind{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;
  color:var(--ink-dim);
}
.kind b{color:var(--ink);font-weight:620}
.kind+.kind::before{content:"·";margin:0 6px;color:var(--rule)}
.pill{
  display:inline-block;padding:1px 8px;border-radius:99px;font-size:11px;font-weight:640;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.02em;
}
.pill.ok{color:var(--ok);background:color-mix(in srgb,var(--ok) 13%,transparent)}
.pill.no{color:var(--drop);background:color-mix(in srgb,var(--drop) 13%,transparent)}
.pill.none{color:var(--ink-dim);background:var(--surface-2)}
.hint{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:11px;color:var(--ink-dim);letter-spacing:.05em;
}
td.wide{white-space:normal;min-width:430px;max-width:520px;color:var(--ink-dim);font-size:12.5px;line-height:1.5}
footer{color:var(--ink-dim);font-size:12.5px;border-top:1px solid var(--rule);padding-top:16px}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;
     background:var(--surface-2);padding:1px 5px;border-radius:4px}
a{color:var(--accent)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
"""


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _kinds_html(s: str) -> str:
    if not s or s == "—":
        return '<span class="dim">—</span>'
    out = []
    for part in s.split(", "):
        if "=" in part:
            k, _, v = part.partition("=")
            out.append(f'<span class="kind">{_esc(k)}=<b>{_esc(v)}</b></span>')
        else:
            out.append(f'<span class="kind">{_esc(part)}</span>')
    return "".join(out)


# What each grammar-v2 kind means, in plain terms, in the order they appear in
# the breakdowns. Only `state_gate` has a code emitter today; the rest are
# listed so a kind breakdown reads without opening the grammar spec.
_KIND_DEFS = [
    ("state_gate",
     "You may only touch this register while some other bit is in the right "
     "state \u2014 \u201conly write CR1 while the STOP bit is clear\u201d. "
     "The workhorse kind, and the only one with a code generator today."),
    ("sequence",
     "Several steps that must happen in a fixed order \u2014 write 0xCA to "
     "the key register, then 0x53. Doing them out of order does not work."),
    ("write_once",
     "A lock bit you may set only once after reset. A second write is "
     "silently ignored by the hardware, so it has to be caught."),
    ("clock_gate",
     "The peripheral\u2019s clock must be switched on before any of its "
     "registers respond. Applies to the whole peripheral, not one register."),
    ("delay",
     "You must wait \u2014 some clock cycles or microseconds \u2014 after "
     "one access before the next one is valid."),
    ("read_effect",
     "Reading the register changes something: it clears a flag, or pops a "
     "byte. Not a rule to enforce, but it tells us a check-by-reading would "
     "disturb the very state it is checking."),
    ("value_relation",
     "Two fields must agree with each other or with the outside world "
     "\u2014 \u201cCR2.FREQ must equal the APB1 clock frequency\u201d. "
     "Documented, not enforceable."),
    ("other",
     "A genuine access rule that fits none of the shapes above. Recorded so "
     "it is not lost, never turned into a gate."),
]


# What each fate means, IN THE ORDER A CONSTRAINT MEETS THEM -- the same order
# inject_from_run applies them: collection lint -> emitter-kind filter ->
# validator gate -> instance/module resolution -> emitter -> instance-collision
# resolution -> device prune -> quote re-verification. Both the definition list
# and the per-RM rows are rendered in this order, so a row reads as a path
# through the pipeline rather than an alphabetical jumble.
_STAGES = [
    ("rejected_at_collection", "stage-0 lint",
     "Names a register or field that cannot be resolved in the SVD, fails "
     "grammar-v2 validation outright, or carries a placeholder name."),
    ("kind_not_emitted", "emitter coverage",
     "The grammar kind has no code generator yet \u2014 sequence, delay, "
     "write_once, read_effect, value_relation, other. The single largest "
     "enforcement gap."),
    ("gated_out_by_validator", "closed-book judge",
     "The validator read the quote without the datasheet in front of it and "
     "called the constraint doc_only (genuine but not witness-enforceable) or "
     "drop (not a constraint at all)."),
    ("peripheral_not_in_device", "device projection",
     "The manual covers a chip family; this peripheral is genuinely not on the "
     "chip injected. Instances that merely share another instance's "
     "register-block module are resolved, not dropped."),
    ("field_gating_disabled", "baseline-mode drop",
     "Every constraint on the register applies to a named FIELD rather than "
     "the whole register. Field-level gating is the default, so in the "
     "default pipeline these become field gates and this fate never appears; "
     "it exists only in the register-only BASELINE (--register-only), where "
     "gating the whole register would demand the precondition for writes to "
     "unrelated fields. A policy of that mode, not a codegen gap."),
    ("emitter_rejected", "emitter cannot express it",
     "A shape the emitter genuinely cannot translate: a field name that is "
     "not an SVD identifier (empty, a bit range, a wildcard), OR-values it "
     "cannot express as one check, a self-defeating same-register read gate, "
     "or a cross-register source it cannot resolve to a module."),
    ("instance_conflict_dropped", "instance conflict",
     "Peripheral instances share one Rust type and disagreed on the gate for "
     "it \u2014 two readings of one datasheet sentence with no way to tell "
     "which is right, so no gate is emitted at all."),
    ("pruned_for_device", "generated-PAC reality",
     "Not expressible against the generated code: the register's access mode "
     "has no such operation, or the precondition's field reader is the wrong "
     "shape (a 1-bit BitReader has no bits(); a multi-bit FieldReader has no "
     "bit_is_set())."),
    ("target_unverified_by_location", "quote anchoring",
     "The supporting quote never names the register and could not be anchored "
     "to the target's own section of the manual, so the evidence cannot be "
     "tied to what it claims to constrain."),
]


def _pill(v: str) -> str:
    if v in ("PASS",):
        return '<span class="pill ok">PASS</span>'
    if v in ("—", "", None):
        return '<span class="pill none">n/a</span>'
    return f'<span class="pill no">{_esc(v)}</span>'


def _n(v) -> int:
    """A column is "—" when its artifact does not exist yet (a newly added
    manual whose compile sweep has not run). Pending is not zero, but it must
    not crash the summary either."""
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


# Per-injection columns in BOTH gating modes. The field-level pair belongs
# here for exactly the reason the whole-register pair does: RM0440 has two
# chips and summing only one of them undercounts.
_INJECTION_COLS = ("enforced", "enforced_via_instance_alias",
                   "registers_gated", "fg_gates", "fg_registers_gated")


def per_manual(rows: list) -> list:
    """One row per manual, with the per-injection columns summed over its
    chips.

    A manual is read once, so extraction columns are already per manual. Gates
    and registers are not: RM0440 is injected into two G4 parts and both are
    real. Keeping only the first row per manual showed one chip and dropped
    the other's 81 gates, and the column stopped summing to the headline."""
    seen, out = {}, []
    for r in rows:
        if r["RM"] not in seen:
            row = dict(r)
            row["_devices"] = {}
            seen[r["RM"]] = row
            out.append(row)
        seen[r["RM"]]["_devices"].setdefault(r["device"], r)
    for row in out:
        devs = list(row["_devices"].values())
        row["device"] = ", ".join(d["device"] for d in devs)
        for k in _INJECTION_COLS:
            row[k] = sum(_n(d[k]) for d in devs)
        states = {d["pac_compiles"] for d in devs}
        row["pac_compiles"] = (devs[0]["pac_compiles"] if len(states) == 1
                               else "/".join(sorted(states)))
    return out


def write_html(rows: list, path: Path, control_rows: list = ()) -> None:
    # Control injections are measurements ABOUT the corpus, not members of it.
    # Leaving them in would make one manual contribute two chips to every
    # total and break the "one device per manual" rule the tables state.
    per_rm = per_manual(rows)

    # One basis now, not two. per_manual() has already summed the per-injection
    # columns over each manual's chips, so the extraction columns (per manual)
    # and the injection columns (per manual, summed over chips) can both be
    # totalled from the same list. The earlier version kept a separate per_inj
    # list for the injection columns, which is what let the funnel and the
    # table below it disagree.
    tot = {k: sum(_n(r[k]) for r in per_rm) for k in
           ("constraints_found_raw", "validator_enforce", "enforced",
            "enforced_via_instance_alias", "registers_gated")}

    # Only pairings whose driver compiles against the PRISTINE chip crate can
    # be measured. Where the baseline already fails, the driver is broken for
    # reasons of its own -- stm32-hal2 references an ADC3 that stm32h7b3 does
    # not have -- and every error on top of it would be miscounted as ours.
    hal_rows = [r for r in rows
                if r["hal_crate"] != "\u2014" and r["true_enforcement"] != "\u2014"]
    measurable = [r for r in hal_rows if r["hal_baseline"] == "PASS"]
    unmeasurable = len(hal_rows) - len(measurable)
    collateral = sum(_n(r["other_errors"]) for r in measurable)
    enforcement = sum(_n(r["true_enforcement"]) for r in measurable)
    fg_enforcement = sum(_n(r["fg_true_enforcement"]) for r in measurable)
    fg_gates_tot = sum(_n(r["fg_gates"]) for r in per_rm)
    fg_regs_tot = sum(_n(r["fg_registers_gated"]) for r in per_rm)

    h = ['<div class="wrap">', "<header>",
         '<span class="eyebrow">LIDAR · enforcement arm</span>',
         "<h1>Register constraints: extraction to compile-time enforcement</h1>",
         f'<p class="sub">{len(per_rm)} ST reference manuals, each injected into its '
         "chip crate and compiled against unmodified third-party drivers. Every number "
         "is read from a pipeline artifact.</p>", "</header>"]

    h += ['<section><h2>The funnel</h2>', '<div class="funnel">']
    # Everything from `compile-time gates` onward depends on which gating mode
    # ran, so each says which. The two above it are extraction figures, settled
    # before any gate exists, and are the same number in both modes -- marking
    # them would imply a distinction they do not have.
    _WR = ' <em>(whole-register)</em>'
    for key, label, hi in (
            ("constraints_found_raw", "found (raw)", False),
            ("validator_enforce", "validator: enforce", False),
            ("enforced", "compile-time gates" + _WR, True),
            ("enforced_via_instance_alias", "via instance alias" + _WR, False),
            ("registers_gated", "registers gated" + _WR, False)):
        h.append(f'<div class="stat{" hi" if hi else ""}"><span class="k">{label}</span>'
                 f'<span class="v">{tot[key]}</span></div>')
    h.append(f'<div class="stat"><span class="k">driver enforcement hits{_WR}'
             f'</span><span class="v">{enforcement}</span></div>')
    h.append(f'<div class="stat"><span class="k">collateral errors{_WR}</span>'
             f'<span class="v">{collateral}</span></div>')
    h.append("</div>")
    h.append('<p class="note"><b>found (raw)</b> and <b>validator: enforce</b> '
             "are extraction figures and are the same in both modes; every "
             "figure below them depends on how the gate is drawn, so each "
             "says which. The default gates a whole register. The injector "
             "can also gate individual bitfields "
             "(<code>--field-level-gating</code>, opt-in), which is a "
             "different trade rather than a better one: it gates fewer "
             "registers and asks less of the driver, so it fires on fewer "
             "sites, but it reaches constraints the datasheet states about "
             "single bits. Both are measured over the same 49 injections and "
             "the same drivers; the table below carries both.</p>")
    h.append('<div class="funnel">')
    h.append(f'<div class="stat"><span class="k">compile-time gates '
             f'<em>(field-level)</em></span>'
             f'<span class="v">{fg_gates_tot}</span></div>')
    h.append(f'<div class="stat"><span class="k">registers gated '
             f'<em>(field-level)</em></span>'
             f'<span class="v">{fg_regs_tot}</span></div>')
    h.append(f'<div class="stat"><span class="k">driver enforcement hits '
             f'<em>(field-level)</em></span>'
             f'<span class="v">{fg_enforcement}</span></div>')
    h += ["</div>",
          '<p class="note"><b>gate fired</b> is a compile error naming a '
          "constrained register: the driver performed that operation without "
          "a witness. That is not a bug by itself &mdash; the gate demands a "
          "witness, so code obeying the datasheet another way still fails to "
          "compile. Every hit is then triaged the way the project scan "
          "triages its own: <b>guarded</b> means the driver does establish "
          "the precondition (in the enclosing function, in a helper one level "
          "up, or via an RAII scope guard); <b>possible bug</b> means it does "
          "not, and is the column worth reading. stm32f1xx-hal is why the "
          "split exists &mdash; four of its five hits sit inside a "
          "<code>perform_write</code> that waits for the exact flag RM0008 "
          "names.</p>",
          f'<p class="note">Driver figures cover the {len(measurable)} of '
          f'{len(hal_rows)} driver pairings whose baseline compiles. The other '
          f'{unmeasurable} fail against the <em>pristine</em> chip crate — '
          "broken for their own reasons, so nothing measured on top of them "
          "would be attributable to injection.</p>",
          "</section>"]

    # --- table 1 -----------------------------------------------------------
    h += ['<section><h2>The kinds of constraint</h2>',
          '<p class="note">What the grammar can express. Only '
          '<code>state_gate</code> has a code generator today \u2014 the rest '
          'are extracted and recorded, and show up under '
          '<em>where the rest went</em> as <code>kind_not_emitted</code>.</p>',
          '<div class="scroll"><table><thead><tr><th class="pin">kind</th>'
          '<th>what it means</th></tr></thead><tbody>']
    for kind, desc in _KIND_DEFS:
        h.append(f'<tr><td class="pin">{_esc(kind)}</td>'
                 f'<td class="wide">{_esc(desc)}</td></tr>')
    h += ["</tbody></table></div></section>"]

    h += ['<section><h2>Extraction → enforcement</h2>',
          '<p class="note">Columns are pipeline stages with <em>different</em> '
          'denominators: <code>found</code> is raw generator output; '
          '<code>validator: enforce</code> counts only what survived the stage-0 '
          'collection lint. <span class="hint">— scroll →</span></p>',
          '<p class="note"><b>One device per manual.</b> A manual covers '
          'several chips &mdash; these 48 project onto 154 device modules '
          '&mdash; and each is injected into one, chosen so that every driver '
          'crate supporting that manual can select it. Checked across all 48: '
          'none needs a second device to reach a driver. Constraints are '
          'unaffected (a manual is read once), but <b>registers gated is per '
          'representative chip, not per family</b>. RM0440 is injected into '
          'two G4 parts on purpose &mdash; G474 alone would reach all three of '
          'its drivers, so the second is the one control we have on how much '
          'the choice of chip moves the numbers: 71 gates and 41 registers on '
          'G4A1 against 81 and 38 on G474.</p>',
          '<div class="scroll"><table class="numbered"><thead><tr>',
          '<th class="rownum">#</th>',
          '<th class="pin">RM</th><th>device</th><th>PAC crate</th>',
          '<th>found</th><th>found by kind</th><th>validator: enforce</th>',
          '<th>enforce by kind</th><th>enforced</th><th>enforced by kind</th>',
          '<th>via alias</th><th>regs</th><th>PAC compiles</th>',
          "</tr></thead><tbody>"]
    for n, r in enumerate(per_rm, start=1):
        h.append(
            f'<tr><td class="rownum">{n}</td>'
            f'<td class="pin">{_esc(r["RM"])}</td>'
            f'<td class="mono">{_esc(r["device"])}</td>'
            f'<td class="mono dim">{_esc(r["pac_crate"])}</td>'
            f'<td class="num">{_esc(r["constraints_found_raw"])}</td>'
            f'<td>{_kinds_html(r["found_by_kind_raw"])}</td>'
            f'<td class="num">{_esc(r["validator_enforce"])}</td>'
            f'<td>{_kinds_html(r["validator_enforce_by_kind"])}</td>'
            f'<td class="num lead">{_esc(r["enforced"])}</td>'
            f'<td>{_kinds_html(r["enforced_by_kind"])}</td>'
            f'<td class="num">{_esc(r["enforced_via_instance_alias"])}</td>'
            f'<td class="num">{_esc(r["registers_gated"])}</td>'
            f'<td>{_pill(r["pac_compiles"])}</td></tr>')
    h += ["</tbody></table></div></section>"]

    # --- table 2 -----------------------------------------------------------
    h += ['<section><h2>What each PAC enforces, and what could be compiled '
          'against it</h2>',
          '<p class="note"><strong>Every injected chip crate is listed.</strong> '
          'The gates and the <code>PAC compiles</code> check are independent of '
          'any driver — injection needs nothing from a HAL. Where no driver '
          'crate depends on PAC 0.16 the HAL columns are empty and the note '
          'says why; the enforcement is still there. The unmodified HAL, where '
          'one exists, is swapped onto the injected PAC with one '
          '<code>[patch.crates-io]</code> line, and its baseline must pass '
          'against the pristine PAC first.</p>',
          '<div class="scroll"><table><thead>',
          '<tr><th class="pin grp" colspan="8"></th>',
          '<th class="grp mode" colspan="5">whole-register gating (default)</th>',
          '<th class="grp mode alt" colspan="5">field-level gating '
          '(<code>--field-level-gating</code>)</th>',
          '<th class="grp" colspan="2"></th></tr>',
          '<tr>',
          '<th class="pin">RM</th><th>device</th><th>PAC crate</th>',
          '<th>gates</th><th>regs</th><th>PAC compiles</th>',
          '<th>HAL crate</th><th>baseline</th>',
          '<th>gate fired</th><th>guarded</th><th>possible bug</th>',
          '<th>generic friction</th><th>other</th>',
          '<th class="alt">gates</th><th class="alt">regs</th>',
          '<th class="alt">gate fired</th>',
          '<th class="alt">possible bug</th><th class="alt">generic friction</th>',
          '<th>enforcement sites</th><th>note</th>',
          "</tr></thead><tbody>"]
    for r in rows:
        note = r["note"] or ("" if r["hal_crate"] != "—" else "—")
        h.append(
            f'<tr><td class="pin">{_esc(r["RM"])}</td>'
            f'<td class="mono">{_esc(r["device"])}</td>'
            f'<td class="mono dim">{_esc(r["pac_crate"])}</td>'
            f'<td class="num lead">{_esc(r["enforced"])}</td>'
            f'<td class="num">{_esc(r["registers_gated"])}</td>'
            f'<td>{_pill(r["pac_compiles"])}</td>'
            f'<td class="mono">{_esc(r["hal_crate"])}</td>'
            f'<td>{_pill(r["hal_baseline"])}</td>'
            f'<td class="num">{_esc(r["true_enforcement"])}</td>'
            f'<td class="num ok">{_esc(r["guarded"])}</td>'
            f'<td class="num lead">{_esc(r["candidate"])}</td>'
            f'<td class="num">{_esc(r["generic_friction"])}</td>'
            f'<td class="num">{_esc(r["other_errors"])}</td>'
            f'<td class="num alt lead">{_esc(r["fg_gates"])}</td>'
            f'<td class="num alt">{_esc(r["fg_registers_gated"])}</td>'
            f'<td class="num alt">{_esc(r["fg_true_enforcement"])}</td>'
            f'<td class="num alt lead">{_esc(r["fg_candidate"])}</td>'
            f'<td class="num alt">{_esc(r["fg_generic_friction"])}</td>'
            f'<td class="mono dim">{_esc(r["enforcement_sites"])}</td>'
            f'<td class="wide">{_esc(note) or "—"}</td></tr>')

    # ---- totals row -------------------------------------------------------
    # Rows are one per (manual x driver crate), so the extraction columns must
    # be de-duplicated or a manual with three drivers is counted three times.
    # Gates and registers are per INJECTION, keyed by (manual, chip) -- RM0440
    # is injected into two different G4 parts and both are real. The compile
    # columns are per row and restricted to pairings whose baseline passes,
    # since errors stacked on an already-broken build are not ours.
    seen_rm, seen_inj = set(), set()
    tot_gates = tot_regs = 0
    for r in rows:
        seen_rm.add(r["RM"])
        if r["pac_crate"] == "—":
            continue            # no chip crate exists; not an injection
        key = (r["RM"], r["device"])
        if key not in seen_inj:
            seen_inj.add(key)
            tot_gates += _n(r["enforced"])
            tot_regs += _n(r["registers_gated"])
    pac_ok = len({(r["RM"], r["device"]) for r in rows
                  if r["pac_compiles"] == "PASS"})
    drivers = {r["hal_crate"] for r in rows if r["hal_crate"] != "—"}
    pairings = [r for r in rows if r["hal_crate"] != "—"]
    ok_pairings = [r for r in pairings if r["hal_baseline"] == "PASS"]
    t_true = sum(_n(r["true_enforcement"]) for r in ok_pairings)
    t_guard = sum(_n(r["guarded"]) for r in ok_pairings)
    t_cand = sum(_n(r["candidate"]) for r in ok_pairings)
    # Hits the static pass could not reach: the diagnostic named a register
    # whose precondition fields did not resolve, or the span carried no line.
    # Reported rather than folded into either column -- an untriaged hit is
    # not evidence of a guard and it is not evidence of a bug.
    t_untri = max(0, t_true - t_guard - t_cand)
    t_fric = sum(_n(r["generic_friction"]) for r in ok_pairings)
    t_other = sum(_n(r["other_errors"]) for r in ok_pairings)
    # Field-level totals follow the SAME rules: registers once per injection,
    # driver figures only over pairings whose baseline compiles.
    seen_fg, tot_fg_regs, tot_fg_gates = set(), 0, 0
    for r in rows:
        if r["pac_crate"] == "\u2014":
            continue
        key = (r["RM"], r["device"])
        if key not in seen_fg:
            seen_fg.add(key)
            tot_fg_regs += _n(r["fg_registers_gated"])
            tot_fg_gates += _n(r["fg_gates"])
    f_true = sum(_n(r["fg_true_enforcement"]) for r in ok_pairings)
    f_cand = sum(_n(r["fg_candidate"]) for r in ok_pairings)
    f_fric = sum(_n(r["fg_generic_friction"]) for r in ok_pairings)
    h += ["</tbody><tfoot>",
          f'<tr><td class="pin">TOTAL</td>'
          f'<td class="mono">{len(seen_inj)} injections</td>'
          f'<td class="mono dim">{len(seen_rm)} manuals</td>'
          f'<td class="num lead">{tot_gates}</td>'
          f'<td class="num">{tot_regs}</td>'
          f'<td>{pac_ok}/{len(seen_inj)} PASS</td>'
          f'<td class="mono">{len(drivers)} crates, {len(pairings)} pairings</td>'
          f'<td>{len(ok_pairings)}/{len(pairings)} PASS</td>'
          f'<td class="num">{t_true}</td>'
          f'<td class="num ok">{t_guard}</td>'
          f'<td class="num lead">{t_cand}</td>'
          f'<td class="num">{t_fric}</td>'
          f'<td class="num">{t_other}</td>'
          f'<td class="num alt lead">{tot_fg_gates}</td>'
          f'<td class="num alt">{tot_fg_regs}</td>'
          f'<td class="num alt">{f_true}</td>'
          f'<td class="num alt lead">{f_cand}</td>'
          f'<td class="num alt">{f_fric}</td>'
          f'<td class="mono dim">—</td>'
          f'<td class="wide">Gates and registers counted once per '
          f'(manual, chip) injection; driver figures cover only the '
          f'{len(ok_pairings)} pairings whose baseline compiles. '
          f'{t_untri} hits are untriaged &mdash; the static pass could not '
          f'resolve their precondition fields, and an untriaged hit is '
          f'neither a guard nor a bug.</td></tr>',
          "</tfoot></table></div>",
          '<p class="note">Driver crates measured: '
          + ", ".join(f"<code>{_esc(d)}</code>" for d in sorted(drivers))
          + ".</p>"]

    # --- the control, reported after the corpus rather than inside it -------
    h += ['<div class="card"><h3>Control: how much does the chip choice '
          'matter?</h3>',
          '<p class="note">Every table above follows one rule &mdash; <b>one '
          'device module per reference manual</b>, chosen so that every driver '
          'supporting that manual can select it. These 48 manuals cover 154 '
          'device modules in total, so each row is one representative chip, '
          'and the obvious question is how much that choice moves the '
          'numbers. One manual is injected a second time to answer it. It is '
          'excluded from every figure above.</p>']
    if control_rows:
        h += ['<div class="scroll"><table><thead><tr>',
              '<th class="pin">RM</th><th>device</th><th>role</th>',
              '<th>gates</th><th>regs</th>',
              '<th>HAL crate</th><th>gate fired</th><th>guarded</th>',
              '<th>possible bug</th></tr></thead><tbody>']
        by_rm = {r["RM"] for r in control_rows}
        for rm in sorted(by_rm):
            for r in [x for x in rows if x["RM"] == rm] + \
                     [x for x in control_rows if x["RM"] == rm]:
                is_ctl = (r["RM"], r["device"]) in CONTROL_DEVICES
                h.append(
                    f'<tr><td class="pin">{_esc(r["RM"])}</td>'
                    f'<td class="mono">{_esc(r["device"])}</td>'
                    f'<td>{"control" if is_ctl else "corpus"}</td>'
                    f'<td class="num lead">{_esc(r["enforced"])}</td>'
                    f'<td class="num">{_esc(r["registers_gated"])}</td>'
                    f'<td class="mono">{_esc(r["hal_crate"])}</td>'
                    f'<td class="num">{_esc(r["true_enforcement"])}</td>'
                    f'<td class="num ok">{_esc(r["guarded"])}</td>'
                    f'<td class="num lead">{_esc(r["candidate"])}</td></tr>')
        h += ["</tbody></table></div>"]
        for (rm, dev), why in sorted(CONTROL_DEVICES.items()):
            h.append(f'<p class="note"><code>{_esc(rm)}</code> / '
                     f'<code>{_esc(dev)}</code> &mdash; {_esc(why)}</p>')
    h += ['<p class="note"><b>One device at a time is a choice, not a limit '
          'of the technique.</b> The harness injects into a single device '
          'module from a pristine crate because <code>generic.rs</code> is '
          'patched crate-wide, which keeps attribution simple. In the 20 '
          'flat-layout crates the device modules are independent files, so '
          'several could be injected in one pass. Only <code>stm32h7</code> '
          'is deduplicated &mdash; 188 of its 430 peripheral modules are '
          'shared between devices &mdash; and there two devices&rsquo; '
          'constraints can land on one Rust type, which is the same problem '
          'the instance-alias resolver already solves for peripherals. '
          'Revisiting it would buy coverage and variation, not new '
          'constraints: a manual is read once, and its constraints do not '
          'change with the chip they are applied to.</p>', "</div>",
          "</section>"]

    # --- table 3 -----------------------------------------------------------
    h += ['<section><h2>Where the rest went</h2>',
          '<p class="note">Every constraint that did not become a gate, with the stage '
          'that dropped it and the grammar kinds involved. The stages, in the order a '
          'constraint would meet them:</p>',
          '<div class="scroll"><table><thead><tr><th class="pin">stage</th>',
          '<th>what it is</th><th>what lands here</th></tr></thead><tbody>']
    for fate, short, desc in _STAGES:
        h.append(f'<tr><td class="pin">{_esc(fate)}</td>'
                 f'<td class="mono dim">{_esc(short)}</td>'
                 f'<td class="wide">{_esc(desc)}</td></tr>')
    h += ["</tbody></table></div>",
          '<div class="scroll"><table><thead><tr>',
          '<th class="pin">RM</th><th>stage → kinds dropped there</th>',
          "</tr></thead><tbody>"]
    for r in per_rm:
        stages = "".join(
            f'<span class="kind"><b>{_esc(s.split(":")[0])}</b> '
            f'{_esc(s.split(":", 1)[1].strip() if ":" in s else "")}</span>'
            for s in r["dropped_by_stage"].split("; ") if s and s != "—")
        h.append(f'<tr><td class="pin">{_esc(r["RM"])}</td>'
                 f'<td>{stages or "<span class=dim>—</span>"}</td></tr>')
    h += ["</tbody></table></div></section>"]

    h += ['<footer>Generated by <code>applications/pac_codegen/experiments/'
          'gen_injection_tracking_artifact.py</code>. Regenerate: <code>stm_sweep.py --dry-run</code> '
          'then <code>gen_injection_tracking_artifact.py</code>; the compile columns additionally need '
          'the full <code>stm_sweep.py</code> and <code>hal_gap.py</code>.</footer>',
          "</div>"]

    path.write_text(
        "<title>Register constraint tracking</title>\n"
        f"<style>{_CSS}</style>\n" + "\n".join(h) + "\n")
    print(f"html: {path}")

if __name__ == "__main__":
    main()
