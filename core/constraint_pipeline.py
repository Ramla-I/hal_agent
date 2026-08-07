"""Chained constraint stage: generator -> collect (lint) -> constraint validator
-> ONE validated artifact that both the review file and PAC codegen consume.

Replaces the old *sibling* design where the constraint validator and
collect_constraints each read the generator output independently and were joined
after the fact by a fragile shared hash. Here collect's LINTED set is the single
row set; the judge only ever sees linted constraints; each record carries the
codegen gate decision (``enforcement``).

ID SCHEME
---------
The old id ``sha1(rm|register|kind|datasheet_text)`` omitted the peripheral AND
the operation, so the same-named register across peripheral instances
(usart1_brr..usart8_brr) and an "any"-gate split into read+write both collapsed
to one id -- one shared verdict, clobbered human labels. Chaining removes the
cross-process join, so we mint the id once on the LINTED object over the full
identity:

    id = sha1(rm|peripheral|register|kind|target_operation|sorted(fields)|text)[:12]

ENFORCEMENT GATE (what codegen does with each constraint)
---------------------------------------------------------
- ``enforce``  : judge ``confirmed`` AND enforceable (action/state_witnessed) AND
                 confidence >= min_confidence -> compile-time witness-gated.
- ``doc_only`` : genuine but not compile-enforceable here -- confirmed-but-not-
                 witnessed, ``encoding_error``, or unanchored/unjudged. Documented
                 in the crate, not gated.
- ``drop``     : judge ``not_constraint`` -- excluded from codegen entirely.

The human ``tp_fp`` label (applied on the review file) overrides: ``FP`` forces a
drop, ``TP`` rescues a non-``enforce`` row to ``doc_only`` at least. That override
lives in the codegen consumer, not here.

``min_confidence`` defaults to 0.0 (inert). The constraint validator is currently
UNCALIBRATED -- ``verdict`` is categorical, no threshold. When constraint
calibration lands (branch ``constraint_validator_tuning``) a tuned threshold
flows in through this one knob. Note: the structure validator's card threshold
(0.98) is a DIFFERENT validator and must not be reused here.

VERDICT SOURCE
--------------
``build_validated`` reuses an existing constraint_validation run's
``anchors.jsonl`` / ``judgments.jsonl`` (matched by the OLD id) when present:
collect's repairs never touch ``datasheet_text`` or the anchored context, so
re-judging the linted set would deterministically reproduce those verdicts. This
keeps the artifact reproducible without spending LLM calls. (Live judging plugs
in at the marked extension point for a from-scratch run.)

Stdlib only.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ENFORCEABLE = ("action_witnessed", "state_witnessed")


def new_constraint_id(rm: str, peripheral: str, register: str, c: dict) -> str:
    """Identity of a LINTED constraint (peripheral + operation + fields included)."""
    key = "|".join([
        rm, peripheral, register,
        c.get("kind", ""), c.get("target_operation", ""),
        ",".join(sorted(c.get("target_fields") or [])),
        c.get("datasheet_text", ""),
    ])
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def old_constraint_id(rm: str, register: str, kind: str, datasheet_text: str) -> str:
    """The retired id -- used ONLY to look up cached verdicts from a prior run."""
    return hashlib.sha1(f"{rm}|{register}|{kind}|{datasheet_text}".encode()).hexdigest()[:12]


def enforcement_decision(verdict: str, enforceability: str,
                         confidence, min_confidence: float = 0.0) -> str:
    """Map (judge verdict, enforceability) -> codegen gate: enforce|doc_only|drop."""
    if verdict == "not_constraint":
        return "drop"
    if verdict == "confirmed":
        conf = confidence if isinstance(confidence, (int, float)) else 0.0
        if enforceability in ENFORCEABLE and conf >= min_confidence:
            return "enforce"
        return "doc_only"
    return "doc_only"  # encoding_error, unanchored, unjudged: keep, document


def _index_jsonl(path: str, keep: tuple) -> dict:
    out: dict = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if "id" in r:
                out[r["id"]] = {k: r.get(k) for k in keep}
    return out


def load_linted(collect_dir: str) -> list[dict]:
    """The linted per-register collected files -> one dict per constraint."""
    items: list[dict] = []
    for path in sorted(glob.glob(os.path.join(collect_dir, "*.json"))):
        if os.path.basename(path) == "manifest.json":
            continue
        stem = os.path.basename(path)[:-5]
        peripheral, _, register = stem.partition("_")
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        for c in (data.get("access_constraints_v2") or []):
            if isinstance(c, dict):
                items.append({"peripheral": peripheral, "register": register, "constraint": c})
    return items


def build_validated(rm: str, run: str, collect_dir: str, validator_dir: str,
                    out_path: str, min_confidence: float = 0.0) -> dict:
    """Write ``validated.jsonl`` (one record per linted constraint) and return counts.

    Reuses ``anchors.jsonl`` / ``judgments.jsonl`` from ``validator_dir`` by old id.
    """
    anchors = _index_jsonl(os.path.join(validator_dir, "anchors.jsonl"), ("tier",))
    judgments = _index_jsonl(os.path.join(validator_dir, "judgments.jsonl"),
                             ("verdict", "confidence", "reason"))

    records: list[dict] = []
    for it in load_linted(collect_dir):
        per, reg, c = it["peripheral"], it["register"], it["constraint"]
        oid = old_constraint_id(rm, reg, c.get("kind", "state_gate"), c.get("datasheet_text", ""))
        nid = new_constraint_id(rm, per, reg, c)
        # --- extension point: if oid not in judgments and anchored, live-judge here.
        judged = judgments.get(oid, {})
        verdict = judged.get("verdict", "")
        conf = judged.get("confidence")
        enforceability = c.get("enforceability", "")
        records.append({
            "id": nid,
            "rm": rm, "peripheral": per, "register": reg,
            "source_file": f"{rm}/{run}/{per}_{reg}",
            "constraint": c,
            "anchor_tier": (anchors.get(oid) or {}).get("tier", "unanchored"),
            "verdict": verdict,
            "confidence": conf,
            "reason": judged.get("reason", ""),
            "enforcement": enforcement_decision(verdict, enforceability, conf, min_confidence),
        })

    records.sort(key=lambda r: (r["peripheral"], r["register"], r["id"]))
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=True) + "\n")
    os.replace(tmp, out_path)

    counts = {"constraints": len(records), "distinct_ids": len({r["id"] for r in records})}
    for k in ("enforce", "doc_only", "drop"):
        counts[k] = sum(1 for r in records if r["enforcement"] == k)
    for v in ("confirmed", "encoding_error", "not_constraint", ""):
        counts[f"verdict_{v or 'blank'}"] = sum(1 for r in records if r["verdict"] == v)
    return counts


def run_stage_live(rm: str, run: str, run_dir: str, svd_dir, chunks_root: str,
                   judge_model: str, out_dir: str, batch_size: int = 8,
                   min_confidence: float = 0.0) -> dict:
    """The full chained stage for s0 Step 6: collect (lint, in-memory, no payload
    files) -> anchor the LINTED set -> judge anchored -> write ``validated.jsonl``
    (+ ``anchors.jsonl`` / ``judgments.jsonl`` / ``manifest.json`` / ``summary.json``).
    Everything is keyed on the NEW id. Returns the funnel + enforcement counts.

    Heavy deps (pydantic via collect, the LLM client) are imported lazily so the
    reuse-mode ``build_validated`` above stays stdlib-only and host-testable."""
    # core/ on sys.path either way (imported as core.constraint_pipeline or bare).
    try:
        from collect_constraints import collect_constraints
        from quote_anchor import RMMatcher, anchor_row
        from constraint_validator import run_judge, make_client, referenced_registers
    except ImportError:  # pragma: no cover - import-path shim
        from core.collect_constraints import collect_constraints
        from core.quote_anchor import RMMatcher, anchor_row
        from core.constraint_validator import run_judge, make_client, referenced_registers

    os.makedirs(out_dir, exist_ok=True)

    # 1. Collect LINTED constraints in memory (manifest written to out_dir for
    #    audit; per-register payload files dropped).
    results = collect_constraints(run_dir, output_dir=out_dir, svd_dir=svd_dir,
                                  write_payload=False)

    # 2. Build items on the linted set with the NEW id.
    items: list[dict] = []
    for r in results:
        per, reg = r["peripheral"], r["register"]
        for c in (r["data"].get("access_constraints_v2") or []):
            if not isinstance(c, dict):
                continue
            items.append({
                "id": new_constraint_id(rm, per, reg, c),
                "reference_manual": rm,
                "source_file": f"{rm}/{run}/{per}_{reg}",
                "peripheral": per, "register": reg,
                "datasheet_text": c.get("datasheet_text", ""),
                "constraint": c,
                "enforceability": c.get("enforceability", ""),
                "target_registers": sorted({reg} | set(referenced_registers(c))),
            })
    items.sort(key=lambda it: it["id"])

    # 3. Static validation: quote anchoring (deterministic).
    md_dir = os.path.join(chunks_root, rm, "chunks", "md")
    if not os.path.isdir(md_dir):
        raise FileNotFoundError(f"no chunked markdown for {rm} at {md_dir}")
    matcher = RMMatcher(rm, md_dir)
    with open(os.path.join(out_dir, "anchors.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for it in items:
            rec = anchor_row(matcher, it)
            it["tier"] = rec.get("tier")
            if rec.get("context"):
                it["context"] = rec["context"]
            it["_anchor"] = rec
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=True) + "\n")

    anchored = [it for it in items if it.get("tier") in ("exact", "fuzzy")]
    static_pass = [it for it in anchored
                   if not (it["_anchor"].get("self_referential")
                           and not it["_anchor"].get("target_located"))]

    # 4. Closed-book LLM judge on anchored items carrying a context.
    judgeable = [it for it in anchored if it.get("context")]
    verdict_by_id: dict = {}
    if judgeable:
        records, _ = run_judge(judgeable, client=make_client(), model=judge_model,
                               quiet=True, batch_size=batch_size)
        with open(os.path.join(out_dir, "judgments.jsonl"), "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
                verdict_by_id[rec.get("id")] = rec

    # 5. Unified validated artifact + enforcement gate.
    out_records = []
    for it in items:
        j = verdict_by_id.get(it["id"], {})
        verdict = j.get("verdict", "")
        conf = j.get("confidence")
        out_records.append({
            "id": it["id"], "rm": rm, "peripheral": it["peripheral"], "register": it["register"],
            "source_file": it["source_file"], "constraint": it["constraint"],
            "anchor_tier": it.get("tier") or "unanchored",
            "verdict": verdict, "confidence": conf, "reason": j.get("reason", ""),
            "enforcement": enforcement_decision(verdict, it["enforceability"], conf, min_confidence),
        })
    out_records.sort(key=lambda r: (r["peripheral"], r["register"], r["id"]))
    with open(os.path.join(out_dir, "validated.jsonl"), "w", encoding="utf-8") as f:
        for r in out_records:
            f.write(json.dumps(r, ensure_ascii=True) + "\n")

    summary = {
        "extracted": len(items), "anchored": len(anchored),
        "static_pass": len(static_pass),
        "confirmed": sum(1 for r in out_records if r["verdict"] == "confirmed"),
        "enforce": sum(1 for r in out_records if r["enforcement"] == "enforce"),
        "doc_only": sum(1 for r in out_records if r["enforcement"] == "doc_only"),
        "drop": sum(1 for r in out_records if r["enforcement"] == "drop"),
    }
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Build the chained validated-constraints artifact")
    ap.add_argument("--rm", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--manufacturer", default="stm")
    ap.add_argument("--min-confidence", type=float, default=0.0)
    ap.add_argument("--collect-dir", default=None)
    ap.add_argument("--validator-dir", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    collect_dir = args.collect_dir or os.path.join(
        _REPO_ROOT, "applications", "pac_codegen", "constraints", "collected", f"{args.rm}_{args.run}")
    validator_dir = args.validator_dir or os.path.join(
        _REPO_ROOT, "agent_output", args.manufacturer, args.rm, args.run, "constraint_validation")
    out_path = args.out or os.path.join(validator_dir, "validated.jsonl")

    counts = build_validated(args.rm, args.run, collect_dir, validator_dir, out_path,
                             min_confidence=args.min_confidence)
    print(f"wrote {counts['constraints']} record(s) -> {out_path}")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
