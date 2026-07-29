#!/usr/bin/env python3
"""Corruption calibration of the constraint-validator judge (plan §7.2).

Runs the judge over (a) a deterministic stratified sample of ORIGINAL
anchored constraints and (b) known-bad CORRUPTIONS of anchored constraints
(corruption.py), then computes the scorecard:

  * corruption-detection rate, overall and per corruption type
    (a detected corruption = verdict != "confirmed");
  * flag rate on originals — reported as a FLAG RATE, NOT a false-positive
    rate: originals carry no human ground truth until Ramla annotates
    (plan §7.2 — the human audit is retrospective, never blocking);
  * confidence distributions, parse-recovery counts, token usage,
    estimated cost, wall time.

All artifacts land under --out-dir (default tune_constraint_validator/out/
calibration/, git-ignored); the committed narrative of the real run lives in
docs/validator_calibration.md. The blindness rule applies: nothing here may
be written under verified_datasheet/.

CLI:
    python3 tune_constraint_validator/calibrate.py \
        --anchors tune_constraint_validator/out/anchors.jsonl \
        --csv verified_datasheet/constraints/stm.csv \
        --out-dir tune_constraint_validator/out/calibration \
        --originals 150 --per-type 30 --seed 20260716 --concurrency 6
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tune_constraint_validator import corruption
from core import constraint_validator as judge  # noqa: E402
from tune_constraint_validator import judge_cli  # noqa: E402

# Groq list price for openai/gpt-oss-120b (USD per 1M tokens) as of 2026-07.
# Estimate only — adjust here if pricing changes.
PRICE_IN_PER_M = 0.15
PRICE_OUT_PER_M = 0.75


# ---------------------------------------------------------------------------
# Scorecard math (pure — unit-tested offline)
# ---------------------------------------------------------------------------


def _confidence_stats(records: list) -> dict:
    vals = sorted(r["confidence"] for r in records
                  if r.get("confidence") is not None)
    if not vals:
        return {"n": 0}
    mid = len(vals) // 2
    median = (vals[mid] if len(vals) % 2
              else (vals[mid - 1] + vals[mid]) / 2.0)
    hist = Counter(min(int(v * 10), 9) for v in vals)  # 0.0-0.1 ... 0.9-1.0
    return {
        "n": len(vals),
        "mean": round(sum(vals) / len(vals), 4),
        "median": round(median, 4),
        "min": round(vals[0], 4),
        "max": round(vals[-1], 4),
        "histogram_decile": {f"{b / 10:.1f}": hist.get(b, 0)
                             for b in range(10)},
    }


def estimated_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    return round(prompt_tokens / 1e6 * PRICE_IN_PER_M
                 + completion_tokens / 1e6 * PRICE_OUT_PER_M, 4)


def compute_scorecard(original_records: list, corruption_records: list) -> dict:
    """original_records / corruption_records: judgment records from
    judge.run_judge (corruption records carry ``corruption_type``)."""
    # -- originals: flag rate (NOT a false-positive rate; no ground truth) --
    o_verdicts = Counter(r["verdict"] for r in original_records)
    n_orig = len(original_records)
    flagged = sum(1 for r in original_records if r["verdict"] != "confirmed")
    originals = {
        "n": n_orig,
        "verdicts": dict(o_verdicts),
        "flag_rate": round(flagged / n_orig, 4) if n_orig else None,
        "note": ("flag rate, not a false-positive rate: originals have no "
                 "human ground truth yet (plan §7.2)"),
        "confidence": {
            "confirmed": _confidence_stats(
                [r for r in original_records if r["verdict"] == "confirmed"]),
            "flagged": _confidence_stats(
                [r for r in original_records if r["verdict"] != "confirmed"]),
        },
    }

    # -- corruptions: detection = verdict != "confirmed" ------------------
    by_type = defaultdict(list)
    for r in corruption_records:
        by_type[r.get("corruption_type", "unknown")].append(r)
    per_type = {}
    for ctype in sorted(by_type):
        recs = by_type[ctype]
        detected = sum(1 for r in recs if r["verdict"] != "confirmed")
        per_type[ctype] = {
            "n": len(recs),
            "detected": detected,
            "detection_rate": round(detected / len(recs), 4),
            "verdicts": dict(Counter(r["verdict"] for r in recs)),
        }
    n_corr = len(corruption_records)
    detected_all = sum(1 for r in corruption_records
                       if r["verdict"] != "confirmed")
    corruptions = {
        "n": n_corr,
        "detected": detected_all,
        "detection_rate": round(detected_all / n_corr, 4) if n_corr else None,
        "per_type": per_type,
        "confidence": {
            "detected": _confidence_stats(
                [r for r in corruption_records
                 if r["verdict"] != "confirmed"]),
            "missed": _confidence_stats(
                [r for r in corruption_records
                 if r["verdict"] == "confirmed"]),
        },
    }

    all_records = original_records + corruption_records
    ptok = sum(r["usage"]["prompt_tokens"] for r in all_records)
    ctok = sum(r["usage"]["completion_tokens"] for r in all_records)
    return {
        "originals": originals,
        "corruptions": corruptions,
        "parse": {
            "recovered": sum(1 for r in all_records if r["parse_recovered"]),
            "failed": sum(1 for r in all_records
                          if r["verdict"] == "parse_failed"),
        },
        "usage": {
            "prompt_tokens": ptok,
            "completion_tokens": ctok,
            "total_tokens": ptok + ctok,
            "calls": sum(r["usage"]["calls"] for r in all_records),
            "estimated_cost_usd": estimated_cost_usd(ptok, ctok),
        },
    }


def print_scorecard(sc: dict) -> None:
    o, c = sc["originals"], sc["corruptions"]
    print("== originals ==")
    print(f"  n={o['n']}  flag_rate={o['flag_rate']}  "
          f"verdicts={o['verdicts']}")
    print("  (flag rate, not a false-positive rate — no ground truth yet)")
    print("== corruptions ==")
    print(f"  n={c['n']}  detected={c['detected']}  "
          f"overall_detection={c['detection_rate']}")
    for ctype, t in c["per_type"].items():
        print(f"    {ctype:<20} {t['detected']:>3}/{t['n']:<3} "
              f"({t['detection_rate']:.2%})  {t['verdicts']}")
    print(f"== parse ==  recovered={sc['parse']['recovered']}  "
          f"failed={sc['parse']['failed']}")
    u = sc["usage"]
    print(f"== usage ==  {u['total_tokens']} tokens "
          f"({u['prompt_tokens']} in / {u['completion_tokens']} out), "
          f"{u['calls']} calls, est ${u['estimated_cost_usd']}")
    if "wall_time_s" in sc:
        print(f"== wall time ==  {sc['wall_time_s']}s")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anchors", default="tune_constraint_validator/out/anchors.jsonl")
    ap.add_argument("--csv", default="verified_datasheet/constraints/stm.csv")
    ap.add_argument("--out-dir", default="tune_constraint_validator/out/calibration")
    ap.add_argument("--originals", type=int, default=150)
    ap.add_argument("--per-type", type=int, default=30)
    ap.add_argument("--seed", default="20260716")
    ap.add_argument("--model", default=judge.MODEL)
    ap.add_argument("--concurrency", type=int, default=judge.DEFAULT_CONCURRENCY)
    ap.add_argument("--timeout", type=float, default=judge.CALL_TIMEOUT_S)
    args = ap.parse_args(argv)

    judge_cli.assert_blind_output(os.path.join(args.out_dir, "x"))
    os.makedirs(args.out_dir, exist_ok=True)
    t0 = time.monotonic()

    # 1. originals: deterministic stratified sample of anchored rows
    items = judge.load_items(args.csv, args.anchors)
    originals = judge_cli.stratified_sample(items, args.originals, args.seed)
    print(f"originals: {len(originals)} of {len(items)} anchored rows "
          f"(seed {args.seed})", file=sys.stderr)

    # 2. corruptions: known-bad encodings, original quote+context
    csv_rows = judge.load_csv_rows(args.csv)
    anchors = judge.load_anchors(args.anchors)
    corr_rows = corruption.generate(csv_rows, anchors, args.per_type,
                                    args.seed)
    corruption.write_records(corr_rows,
                             os.path.join(args.out_dir, "corruptions.jsonl"))
    print(f"corruptions: {len(corr_rows)} "
          f"({args.per_type} requested per type)", file=sys.stderr)

    # 3. judge both sets (one client, sequential batches)
    client = judge.make_client()
    orig_recs, orig_totals = judge.run_judge(
        originals, client, model=args.model, concurrency=args.concurrency,
        timeout=args.timeout)
    judge_cli.write_judgments(orig_recs,
                          os.path.join(args.out_dir,
                                       "judgments_originals.jsonl"))
    print(f"originals judged: {orig_totals}", file=sys.stderr)

    corr_recs, corr_totals = judge.run_judge(
        corr_rows, client, model=args.model, concurrency=args.concurrency,
        timeout=args.timeout)
    judge_cli.write_judgments(corr_recs,
                          os.path.join(args.out_dir,
                                       "judgments_corruptions.jsonl"))
    print(f"corruptions judged: {corr_totals}", file=sys.stderr)

    # 4. scorecard
    sc = compute_scorecard(orig_recs, corr_recs)
    sc["model"] = args.model
    sc["seed"] = args.seed
    sc["sample"] = {"originals": len(originals),
                    "corruptions": len(corr_rows),
                    "per_type_requested": args.per_type,
                    "anchored_pool": len(items)}
    sc["wall_time_s"] = round(time.monotonic() - t0, 1)
    with open(os.path.join(args.out_dir, "scorecard.json"), "w",
              encoding="utf-8") as f:
        json.dump(sc, f, indent=2, sort_keys=True)
    print_scorecard(sc)
    print(f"-> {args.out_dir}/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
