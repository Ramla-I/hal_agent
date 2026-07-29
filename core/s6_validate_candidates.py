"""s6 — loop the datasheet validator over each run's BUG CANDIDATES.

Unlike the full Step-4 validator (every register/field), this validates only the
candidate invariants (blank-status review rows) using the generator's value, then
writes structure_verdict / structure_confidence back into the consolidated
{device}_structure_review.csv (never touching tp_fp — advisory only).

Calibration guard: the carded (primary) model's verdicts use the card threshold;
if a Groq rate-limit/outage forces a fall over to the cheap OpenAI fallback, those
rows are uncalibrated and use a conservative default threshold instead (the judging
model is recorded per row via the classification 'model' column). Resilient
without silently invalidating the calibrated numbers.

    python core/s6_validate_candidates.py --devices rm0360
    python core/s6_validate_candidates.py --all --parallel 2
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Put repo root + core/ on sys.path so `python core/s6_...py` resolves config,
# s0_run_full_analysis, etc. (mirrors s0's bootstrap).
_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_CORE_DIR)
for _p in (_REPO_ROOT, _CORE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tiktoken

import config
from defs import ContextRetrievalParameters
from context_retrieval.retrieve_context import retrieve_context
from utils.llm import call_llm
from utils.result_saver import ResultSaver, UsageStats
from utils.utils import setup_logger
from prompts.validator import (
    create_batched_validator_system_prompt,
    create_batched_validator_file_search_query,
    create_batched_validator_user_prompt,
)
from utils.parse_output import get_json_block_from_response
from s0_run_full_analysis import (
    resolve_device_paths, build_context_retrieval_params, apply_retrieval_override,
)
from applications.bug_finding.validate_candidates import (
    candidate_invariants, load_card, card_threshold, apply_verdicts,
)
from optimization_validator.access_notation import access_legend

logger = setup_logger(__name__)

_CARDS_DIR = os.path.join("optimization_validator", "validator_cards")


def run_validator_batched_resilient(models: list, invariants: list, output_dir: str,
                                    cr_params: ContextRetrievalParameters,
                                    device_name: str, device_dir: str, manufacturer,
                                    agent_output_dir: str,
                                    reasoning_effort: str | None = None) -> tuple[int, int]:
    """Batched validator (one LLM call per register) routed through call_llm for
    retry-after resilience. Writes a fresh classification.csv. Mirrors
    s4_validator.run_validator_batched but single-model + resilient."""
    os.makedirs(output_dir, exist_ok=True)
    for fn in ("classification.csv", "usage.csv", "output.txt"):     # fresh run
        p = os.path.join(output_dir, fn)
        if os.path.exists(p):
            os.remove(p)
    saver = ResultSaver(output_dir)

    batches: dict[tuple, list] = defaultdict(list)
    for inv in invariants:
        batches[(inv["peripheral_name"], inv["register_name"])].append(inv)
    logger.info("Validating %d candidate invariants in %d register batches",
                len(invariants), len(batches))

    # Build the system prompt once with the vendor's access-notation legend +
    # name aliasing — the configuration the validator_card was calibrated with.
    vendor = getattr(manufacturer, "value", str(manufacturer)).lower()
    system_prompt = create_batched_validator_system_prompt(access_legend(vendor), name_aliasing=True)

    total_true = total_false = 0
    for (peripheral_name, register_name), batch in batches.items():
        file_search, _ = retrieve_context(
            cr_params, device_name, device_dir, peripheral_name, register_name,
            manufacturer, agent_output_dir)
        file_search = file_search or ""
        try:
            file_search_tokens = len(tiktoken.get_encoding("cl100k_base").encode(file_search))
        except Exception:
            file_search_tokens = 0

        input_list = [
            {"role": "developer", "content": [
                {"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [
                {"type": "input_text", "text": create_batched_validator_user_prompt(
                    [(peripheral_name, register_name)],
                    [{"peripheral": i["peripheral_name"], "register": i["register_name"],
                      "field_name": i["field_name"], "key": i["key"], "value": i["value"]}
                     for i in batch],
                    file_search)}]},
        ]
        kwargs = {"input": input_list}
        if reasoning_effort is not None:
            kwargs["reasoning"] = {"effort": reasoning_effort}
        response, used_model = call_llm(models=models, **kwargs)

        saver.append_text(f"---{peripheral_name}_{register_name}---\n{response.output_text}\n\n", "output.txt")
        json_block = get_json_block_from_response(response.output_text)
        if json_block is not None:
            try:
                results = json.loads(json_block)
                if isinstance(results, list):
                    for result in results:
                        idx = result.get("invariant_index", -1)
                        if not (0 <= idx < len(batch)):
                            continue
                        inv = batch[idx]
                        is_true = bool(result.get("is_true", False))
                        conf = result.get("confidence_score", 0.0)
                        saver.save_csv_row({
                            "peripheral_name": inv["peripheral_name"], "register_name": inv["register_name"],
                            "field_name": inv["field_name"], "key": inv["key"], "value": inv["value"],
                            "agent_judgement": is_true, "confidence_score": conf,
                            "model": used_model,   # which model judged it (calibration guard downstream)
                        }, "classification.csv")
                        total_true += is_true
                        total_false += (not is_true)
            except Exception as e:
                logger.error("Parse error %s_%s: %s", peripheral_name, register_name, e)

        usage = UsageStats.from_response_usage(used_model, response.usage, file_search_tokens)
        saver.save_usage_stats(usage, "usage.csv", additional_fields={
            "peripheral_name": peripheral_name, "register_name": register_name, "batch_size": len(batch)})

    logger.info("Validation complete: %d true, %d false", total_true, total_false)
    return total_true, total_false


def _update_manifest(agent_output_dir: str, fields: dict) -> None:
    path = os.path.join(agent_output_dir, "run_manifest.json")
    data = {}
    if os.path.exists(path):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception:
            data = {}
    data.update(fields)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def validate_run(ctx, repo_root: str, run_number: int, models: list,
                 cards_dir: str = _CARDS_DIR, reasoning_effort: str | None = None) -> dict:
    paths = resolve_device_paths(ctx, repo_root, run_number)
    device = ctx.device_name
    review_csv = os.path.join(paths.results_dir, f"{device}_structure_review.csv")
    if not os.path.isfile(review_csv):
        return {"device": device, "run": run_number, "skipped": "no review CSV"}

    invs = candidate_invariants(review_csv)
    if not invs:
        return {"device": device, "run": run_number, "candidates": 0, "skipped": "no candidates"}

    # OpenEvolve retrieval via retrieve_context — the retrieval the generator AND
    # the validator_card were calibrated with, and (unlike search_context) it works
    # for every device regardless of its vector_stores.json default.
    cr_params = build_context_retrieval_params(paths.device_dir, ctx)
    cr_params = apply_retrieval_override(cr_params, "openevolve", device, repo_root, ctx.manufacturer)

    validator_dir = os.path.join(paths.agent_output_dir, "validator")
    true_count, false_count = run_validator_batched_resilient(
        models, invs, validator_dir, cr_params,
        device, paths.device_dir, ctx.manufacturer, paths.agent_output_dir,
        reasoning_effort)

    vendor = getattr(ctx.manufacturer, "value", str(ctx.manufacturer)).lower()
    # The card matches the primary (carded) model = models[0]; fallback-model rows
    # are treated as uncalibrated inside apply_verdicts.
    card, calibrated_for = load_card(vendor, device, models[0], cards_dir)
    threshold = card_threshold(card)
    counts = apply_verdicts(review_csv, os.path.join(validator_dir, "classification.csv"),
                            threshold, carded_model=models[0])

    _update_manifest(paths.agent_output_dir, {
        "candidate_validator_used": True,
        "candidate_validator_vendor": vendor,
        "candidate_validator_model": models[0],
        "candidate_validator_models": models,
        "candidate_validator_retrieval": cr_params.context_retrieval_method.value,
        "candidate_validator_calibrated_for": calibrated_for,
        "candidate_validator_threshold": threshold,
        "candidate_validator_true": true_count,
        "candidate_validator_false": false_count,
        "candidate_validator_verdicts": counts,
    })
    return {"device": device, "run": run_number, "candidates": len(invs),
            "raw_true": true_count, "raw_false": false_count,
            "threshold": threshold, "calibrated_for": calibrated_for, **counts}


def main() -> None:
    ap = argparse.ArgumentParser(description="s6: validate bug candidates against the datasheet")
    ap.add_argument("--devices", nargs="*", help="device names (default: all in config.user_contexts)")
    ap.add_argument("--all", action="store_true", help="all devices in config.user_contexts")
    ap.add_argument("--run", type=int, default=None, help="run number (default: latest)")
    ap.add_argument("--validator-model", default=None,
                    help="pin a single model; default uses STAGE_MODELS['validator'] "
                         "(carded primary -> cheap OpenAI fallback)")
    ap.add_argument("--cards-dir", default=_CARDS_DIR)
    ap.add_argument("--parallel", type=int, default=1)
    args = ap.parse_args()

    repo_root = _REPO_ROOT
    from s0_run_full_analysis import resolve_run_number

    contexts = config.user_contexts
    if args.devices:
        want = {d.lower() for d in args.devices}
        contexts = [c for c in contexts if c.device_name.lower() in want]
    if not contexts:
        print("no matching devices"); return

    # carded primary first, then cheap OpenAI fallback (calibration guard in
    # apply_verdicts keeps the card threshold valid despite the fallback).
    models = [args.validator_model] if args.validator_model else list(config.STAGE_MODELS["validator"])
    jobs = []
    for ctx in contexts:
        run_number = args.run if args.run is not None else resolve_run_number(repo_root, ctx)
        jobs.append((ctx, run_number))

    results = []
    if args.parallel > 1:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futs = {ex.submit(validate_run, ctx, repo_root, rn, models, args.cards_dir): ctx.device_name
                    for ctx, rn in jobs}
            for fut in as_completed(futs):
                try:
                    results.append(fut.result())
                except Exception as e:
                    results.append({"device": futs[fut], "error": str(e)})
    else:
        for ctx, rn in jobs:
            try:
                results.append(validate_run(ctx, repo_root, rn, models, args.cards_dir))
            except Exception as e:
                results.append({"device": ctx.device_name, "error": str(e)})

    print("\n=== candidate validation summary ===")
    for r in results:
        print(" ", json.dumps(r))


if __name__ == "__main__":
    main()
