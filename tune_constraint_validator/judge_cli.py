#!/usr/bin/env python3
"""Calibration / manual CLI for the constraint-validator judge (plan §7.0/§7.2).

The judge itself is a LIBRARY in ``core/constraint_validator.py`` (used by
``core/s0`` and the calibration harness via make_client / load_items /
run_judge). This module holds the tuning-only pieces lifted out of it: the
manual CLI plus its helpers — stratified sampling, corruption-row loading, and
judgment writing with the §7.2 blindness guard.

CLI:
    python3 tune_constraint_validator/judge_cli.py \
        --anchors tune_constraint_validator/out/anchors.jsonl \
        --csv verified_datasheet/constraints/stm.csv \
        --out tune_constraint_validator/out/judgments.jsonl \
        [--limit 150 --sample-seed 7] [--ids ids.txt] \
        [--rows-jsonl corruptions.jsonl] [--concurrency 6]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import constraint_validator as judge  # noqa: E402


def load_rows_jsonl(path: str) -> list:
    """Load pre-built judge items (e.g. corruption.py output): flat dicts
    already carrying ``context``."""
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    items.sort(key=lambda it: it["id"])
    return items


# ---------------------------------------------------------------------------
# Sampling (deterministic, stratified across RMs and constraint shapes)
# ---------------------------------------------------------------------------


def constraint_shape(item: dict) -> tuple:
    """Coarse shape key: (operation, pre-count bucket, post-count bucket,
    carries an equals-value?). Used to stratify samples so mode-gates,
    value unlocks, postcondition rows etc. are all represented."""
    pre = judge.parse_json_list(item.get("preconditions"))
    post = judge.parse_json_list(item.get("postconditions"))
    has_eq = any(str(c.get("required_state", "")).startswith("equals")
                 for c in pre + post)
    op = (item.get("target_operation") or "").strip().lower()
    return (op, min(len(pre), 2), min(len(post), 1), has_eq)


def stratified_sample(items: list, n: int, seed) -> list:
    """Deterministic sample of ``n`` items: round-robin across reference
    manuals (sorted), and within each RM round-robin across constraint
    shapes (each shape's items in seeded shuffled order). Same inputs and
    seed -> same ids."""
    if n >= len(items):
        return sorted(items, key=lambda it: it["id"])
    rng = random.Random(f"sample:{seed}")
    queues = {}
    for rm in sorted({it.get("reference_manual", "") for it in items}):
        rm_items = [it for it in items if it.get("reference_manual", "") == rm]
        by_shape = defaultdict(list)
        for it in sorted(rm_items, key=lambda it: it["id"]):
            by_shape[constraint_shape(it)].append(it)
        shape_lists = []
        for shape in sorted(by_shape, key=repr):
            lst = by_shape[shape]
            rng.shuffle(lst)
            shape_lists.append(lst)
        # interleave shapes within the RM
        merged, i = [], 0
        while any(shape_lists):
            lst = shape_lists[i % len(shape_lists)]
            if lst:
                merged.append(lst.pop())
            i += 1
            shape_lists = [l for l in shape_lists if l]
        queues[rm] = merged
    rms = sorted(queues)
    picked = []
    while len(picked) < n and any(queues.values()):
        for rm in rms:
            if len(picked) >= n:
                break
            if queues[rm]:
                picked.append(queues[rm].pop(0))
    picked.sort(key=lambda it: it["id"])
    return picked


# ---------------------------------------------------------------------------
# Output (with the blindness guard)
# ---------------------------------------------------------------------------


def assert_blind_output(out_path: str) -> None:
    """BLINDNESS rule (plan §7.2): no judge verdict is ever written into or
    near the verified datasheet."""
    parts = os.path.normpath(os.path.realpath(out_path)).split(os.sep)
    if "verified_datasheet" in parts:
        raise SystemExit(
            "refusing to write judge output under verified_datasheet/ "
            "(blindness rule, plan §7.2 — human labels must not be anchored "
            "by the machine's)")


def write_judgments(records: list, out_path: str) -> None:
    assert_blind_output(out_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for rec in sorted(records, key=lambda r: r["id"]):
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=True) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anchors", default="tune_constraint_validator/out/anchors.jsonl")
    ap.add_argument("--csv", default="verified_datasheet/constraints/stm.csv")
    ap.add_argument("--rows-jsonl", default=None,
                    help="judge pre-built rows (e.g. corruption.py output) "
                         "instead of the csv+anchors join")
    ap.add_argument("--out", default="tune_constraint_validator/out/judgments.jsonl")
    ap.add_argument("--limit", type=int, default=None,
                    help="judge only a deterministic stratified sample of N")
    ap.add_argument("--sample-seed", default="0",
                    help="seed for the stratified sample (with --limit)")
    ap.add_argument("--ids", default=None,
                    help="file with one constraint id per line")
    ap.add_argument("--model", default=judge.MODEL)
    ap.add_argument("--concurrency", type=int, default=judge.DEFAULT_CONCURRENCY)
    ap.add_argument("--timeout", type=float, default=judge.CALL_TIMEOUT_S)
    args = ap.parse_args(argv)

    assert_blind_output(args.out)
    if args.rows_jsonl:
        items = load_rows_jsonl(args.rows_jsonl)
    else:
        items = judge.load_items(args.csv, args.anchors)
    if args.ids:
        with open(args.ids, encoding="utf-8") as f:
            wanted = {line.strip() for line in f if line.strip()}
        items = [it for it in items if it["id"] in wanted]
    if args.limit is not None:
        items = stratified_sample(items, args.limit, args.sample_seed)
    print(f"judging {len(items)} items with {args.model} "
          f"(concurrency {args.concurrency})", file=sys.stderr)

    records, totals = judge.run_judge(items, model=args.model,
                                      concurrency=args.concurrency,
                                      timeout=args.timeout)
    write_judgments(records, args.out)
    print(json.dumps(totals, indent=2))
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
