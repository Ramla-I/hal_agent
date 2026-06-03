#!/usr/bin/env python3
"""
Measure retrieval quality directly from a sweep run's embedding_ids.jsonl,
without re-running the generator.

For each `(peripheral, register)` query, the relevance label comes from the
labels ChromaDB's boolean `reg_{PERIPHERAL}_{REGISTER}` metadata: a chunk is
relevant iff that flag is True. The script computes recall@k, precision@k,
MRR, and hit@k at several k cutoffs and aggregates them per peripheral and
overall.

Supported backends (those whose retrieved chunk_ids match the labels DB's
`source` paths):
  - `local_vector_db` — rank reflects retrieval relevance; all metrics
    meaningful.
  - `openevolve` — the evolved program sorts its final output by page
    number, so each entry's `rank_meaning` is `"document_order"`. recall@k
    and hit@k (set-membership at the cutoff) remain valid; MRR and
    precision@k are nulled out for these queries since rank-0 reflects
    lowest page number, not best relevance.

OpenAI file_search runs are skipped because they don't emit chunk_ids that
can be cross-referenced against the labels DB.

Usage:
    python3 optimization/retrieval/metrics_retrieval.py RUN_DIR [RUN_DIR ...] \
        [--db-name rm0041_md_chunks] [--db-path databases/]

Writes `info/retrieval_quality.json` inside each RUN_DIR. When multiple run
dirs are given, also writes `retrieval_quality_summary.csv` to their common
parent.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from context_retrieval.vector_db.vector_store import VectorStore
from context_retrieval.vector_db import config as vdb_config


DEFAULT_K_CUTOFFS = [1, 5, 10]


def _rank_dependent_metric_keys(k_cutoffs: List[int]) -> Set[str]:
    """Metrics whose value depends on retrieval-relevance ranking, not just set membership.

    These are nulled out for runs that log document-ordered chunks (e.g. OpenEvolve),
    because the rank-0 position there reflects lowest page number, not best relevance.
    """
    return {"mrr"} | {f"precision@{k}" for k in k_cutoffs}


def _load_embedding_ids(run_dir: Path) -> List[dict]:
    path = run_dir / "info" / "embedding_ids.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"missing {path}")
    records = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _expand_to_queries(records: List[dict]) -> List[dict]:
    """Normalize batched and per-register records into a flat list of queries.

    Each output entry has: peripheral, register, num_embeddings, ranked_sources
    (list of chunk source paths in retrieval order), and rank_meaning
    (`"relevance"` or `"document_order"`). Batched records produce one query per
    register in `registers`, all sharing the same `ranked_sources`.
    """
    out = []
    for rec in records:
        peripheral = rec.get("peripheral", "")
        num_embeddings = int(rec.get("num_embeddings", 0))
        items = rec.get("embedding_ids", [])
        ranked_sources = []
        for item in items:
            src = item.get("chunk_id") or item.get("source") or ""
            if src:
                ranked_sources.append(src)
        # Inherit the rank_meaning marker from the first item that carries one.
        # OE writes "document_order"; local backend omits the field, which we
        # treat as "relevance" (the default semantics).
        rank_meaning = "relevance"
        for item in items:
            if "rank_meaning" in item:
                rank_meaning = item["rank_meaning"]
                break

        if "registers" in rec:
            for register in rec["registers"]:
                out.append({
                    "peripheral": peripheral,
                    "register": register,
                    "num_embeddings": num_embeddings,
                    "ranked_sources": ranked_sources,
                    "batched": True,
                    "rank_meaning": rank_meaning,
                })
        elif "register" in rec:
            out.append({
                "peripheral": peripheral,
                "register": rec["register"],
                "num_embeddings": num_embeddings,
                "ranked_sources": ranked_sources,
                "batched": False,
                "rank_meaning": rank_meaning,
            })
    return out


def load_db_labels(
    db_name: str, db_path: str
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """Return (sources_for_reg, regs_for_source).

    - sources_for_reg["AFIO_EXTICR4"] -> set of chunk source paths flagged True
    - regs_for_source["chunked_datasheets/.../p126_c01.txt"] -> set of "AFIO_EXTICR4" labels
    """
    if db_path:
        vdb_config.DATABASES_DIR = Path(db_path)
    store = VectorStore(db_name)
    raw = store.collection.get(include=["metadatas"])

    sources_for_reg: Dict[str, Set[str]] = defaultdict(set)
    regs_for_source: Dict[str, Set[str]] = defaultdict(set)
    for meta in raw["metadatas"]:
        src = meta.get("source", "")
        if not src:
            continue
        for k, v in meta.items():
            if not k.startswith("reg_") or v is not True:
                continue
            label = k[len("reg_"):]
            sources_for_reg[label].add(src)
            regs_for_source[src].add(label)
    return sources_for_reg, regs_for_source


def _metrics_for_query(
    ranked: List[str],
    relevant: Set[str],
    k_values: List[int],
) -> Dict[str, float]:
    """Compute recall@k, precision@k, hit@k for each k, and MRR. relevant must be non-empty."""
    out: Dict[str, float] = {}
    n_rel = len(relevant)

    # MRR — rank of first relevant in ranked list
    mrr = 0.0
    for rank, src in enumerate(ranked, start=1):
        if src in relevant:
            mrr = 1.0 / rank
            break
    out["mrr"] = mrr

    for k in k_values:
        topk = ranked[:k]
        n_hit = sum(1 for src in topk if src in relevant)
        out[f"recall@{k}"] = n_hit / n_rel if n_rel > 0 else 0.0
        out[f"precision@{k}"] = n_hit / k if k > 0 else 0.0
        out[f"hit@{k}"] = 1.0 if n_hit > 0 else 0.0
    return out


def _average(rows: Iterable[Dict[str, Optional[float]]], keys: List[str]) -> Dict[str, Optional[float]]:
    """Mean over rows, skipping None for each metric independently.

    Returns None for a metric when every row's value is None (e.g. an all-OE run
    aggregating MRR — no query has a relevance ranking, so the mean is undefined).
    """
    rows = list(rows)
    out: Dict[str, Optional[float]] = {}
    for k in keys:
        vals = [r[k] for r in rows if r.get(k) is not None]
        out[k] = sum(vals) / len(vals) if vals else None
    return out


def measure_run(run_dir: Path, sources_for_reg, k_cutoffs: List[int]) -> dict:
    queries = _expand_to_queries(_load_embedding_ids(run_dir))

    # Pick k values: standard cutoffs + num_embeddings if not already in
    per_query: List[dict] = []
    unmeasurable: List[Tuple[str, str]] = []

    # Metric keys we'll compute (consistent ordering)
    metric_keys = ["mrr"]
    for k in k_cutoffs:
        metric_keys += [f"recall@{k}", f"precision@{k}", f"hit@{k}"]

    rank_dep = _rank_dependent_metric_keys(k_cutoffs)

    for q in queries:
        peripheral = q["peripheral"]
        register = q["register"]
        label = f"{peripheral.upper()}_{register.upper()}"
        relevant = sources_for_reg.get(label, set())
        if not relevant:
            unmeasurable.append((peripheral, register))
            continue
        metrics = _metrics_for_query(q["ranked_sources"], relevant, k_cutoffs)
        # Null out rank-dependent metrics for document-ordered queries.
        if q["rank_meaning"] == "document_order":
            for key in rank_dep:
                metrics[key] = None
        per_query.append({
            "peripheral": peripheral,
            "register": register,
            "label": label,
            "rank_meaning": q["rank_meaning"],
            "relevant_in_db": len(relevant),
            "retrieved_count": len(q["ranked_sources"]),
            "num_embeddings": q["num_embeddings"],
            "batched": q["batched"],
            **metrics,
        })

    overall = _average(per_query, metric_keys)

    per_peripheral: Dict[str, Dict[str, float]] = {}
    by_periph = defaultdict(list)
    for row in per_query:
        by_periph[row["peripheral"]].append(row)
    for periph, rows in sorted(by_periph.items()):
        per_peripheral[periph] = {
            "n_queries": len(rows),
            **_average(rows, metric_keys),
        }

    rank_breakdown = {"relevance": 0, "document_order": 0}
    for row in per_query:
        rank_breakdown[row["rank_meaning"]] = rank_breakdown.get(row["rank_meaning"], 0) + 1

    return {
        "run_dir": str(run_dir),
        "queries": {
            "total": len(queries),
            "measurable": len(per_query),
            "unmeasurable": len(unmeasurable),
            "unmeasurable_list": [f"{p}/{r}" for p, r in unmeasurable],
        },
        "rank_meaning_breakdown": rank_breakdown,
        "rank_dependent_metrics": sorted(rank_dep),
        "k_cutoffs": k_cutoffs,
        "overall": overall,
        "per_peripheral": per_peripheral,
        "per_query": per_query,
    }


def _fmt(v: Optional[float]) -> str:
    return f"{v:.3f}" if v is not None else "  N/A"


def _print_run_summary(result: dict) -> None:
    name = Path(result["run_dir"]).name
    q = result["queries"]
    o = result["overall"]
    cutoffs = result["k_cutoffs"]
    breakdown = result["rank_meaning_breakdown"]
    print(f"\n{name}")
    print(f"  measurable queries: {q['measurable']}/{q['total']}"
          + (f" (skipped: {q['unmeasurable']})" if q['unmeasurable'] else ""))
    if breakdown.get("document_order", 0) > 0:
        n_rel = breakdown["relevance"]
        n_doc = breakdown["document_order"]
        if n_rel == 0:
            note = "(rank-dependent metrics — MRR, precision@k — are N/A for all queries)"
        else:
            note = (f"(MRR / precision@k below are aggregated over the {n_rel} "
                    f"relevance-ranked queries only; recall@k / hit@k cover all {n_rel + n_doc})")
        print(f"  rank meaning: {n_rel} relevance-ranked, {n_doc} document-ordered\n"
              f"                {note}")
    print(f"  MRR: {_fmt(o['mrr'])}")
    for k in cutoffs:
        print(f"  k={k:>2}: recall {_fmt(o[f'recall@{k}'])}  "
              f"precision {_fmt(o[f'precision@{k}'])}  hit {_fmt(o[f'hit@{k}'])}")


def _write_summary_csv(results: List[dict], path: Path) -> None:
    cutoffs = results[0]["k_cutoffs"]
    fields = ["config", "measurable", "total", "mrr"]
    for k in cutoffs:
        fields += [f"recall@{k}", f"precision@{k}", f"hit@{k}"]

    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            row = {
                "config": Path(r["run_dir"]).name,
                "measurable": r["queries"]["measurable"],
                "total": r["queries"]["total"],
                **{k: (round(v, 4) if v is not None else "")
                   for k, v in r["overall"].items()},
            }
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dirs", nargs="+", type=Path,
                        help="One or more sweep run directories (containing info/embedding_ids.jsonl)")
    parser.add_argument("--db-name", default="rm0041_md_chunks",
                        help="ChromaDB collection name (default: rm0041_md_chunks)")
    parser.add_argument("--db-path", default="",
                        help="Override databases directory (default: databases/)")
    parser.add_argument("--k", type=int, nargs="+", default=DEFAULT_K_CUTOFFS,
                        help=f"k cutoffs (default: {DEFAULT_K_CUTOFFS})")
    args = parser.parse_args()

    print(f"Loading labels from ChromaDB '{args.db_name}'...")
    sources_for_reg, _ = load_db_labels(args.db_name, args.db_path)
    print(f"  {len(sources_for_reg)} unique reg_* labels")

    results: List[dict] = []
    for run_dir in args.run_dirs:
        if not (run_dir / "info" / "embedding_ids.jsonl").exists():
            print(f"SKIP {run_dir}: no info/embedding_ids.jsonl")
            continue
        result = measure_run(run_dir, sources_for_reg, args.k)
        out_path = run_dir / "info" / "retrieval_quality.json"
        with out_path.open("w") as f:
            json.dump(result, f, indent=2)
        _print_run_summary(result)
        print(f"  -> {out_path}")
        results.append(result)

    if len(results) > 1:
        # Resolve to absolute paths so commonpath doesn't choke on mixed relative/absolute inputs.
        abs_dirs = [str(Path(r["run_dir"]).resolve()) for r in results]
        common = Path(os.path.commonpath(abs_dirs))
        # If runs live in unrelated trees, commonpath bottoms out at "/" — fall back to cwd.
        if common == Path("/") or not str(common).startswith(str(Path.cwd())):
            common = Path.cwd()
        summary_path = common / "retrieval_quality_summary.csv"
        _write_summary_csv(results, summary_path)
        print(f"\nSummary: {summary_path}")


if __name__ == "__main__":
    main()
