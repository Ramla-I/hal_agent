"""The one register-access validator core, shared by both placements:

  * BEFORE the SVD diff (s0 Step 4): validate ALL extracted invariants against the
    datasheet — a full-extraction QA pass.
  * AFTER the SVD diff (s6): validate only the bug-candidate invariants, then
    ``apply_verdicts`` writes the advisory ``validator_verdict`` into the review.

Both call ``validate_invariants`` with a list of invariants; the only differences
are *which* invariants and whether ``apply_verdicts`` runs afterward. Routed through
``retrieve_context`` (so it works on the openevolve retrieval the generator uses —
unlike the old s4 ``search_context`` path, which raised on OPENEVOLVE) and through
``call_llm`` for retry-after resilience, with the calibrated batched prompt.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

import tiktoken

from defs import ContextRetrievalParameters
from context_retrieval.retrieve_context import retrieve_context
from utils.llm import call_llm
from utils.result_saver import ResultSaver, UsageStats
from utils.utils import setup_logger
from utils.parse_output import get_json_block_from_response
from prompts.validator import (
    create_batched_validator_system_prompt,
    create_batched_validator_user_prompt,
)
from optimization_validator.access_notation import access_legend

logger = setup_logger(__name__)


def validate_invariants(models: list, invariants: list, output_dir: str,
                        cr_params: ContextRetrievalParameters,
                        device_name: str, device_dir: str, manufacturer,
                        agent_output_dir: str,
                        reasoning_effort: str | None = None) -> tuple[int, int]:
    """Validate ``invariants`` against the datasheet, one LLM call per register
    batch, writing a fresh ``classification.csv``/``usage.csv``/``output.txt`` in
    ``output_dir``. Returns ``(true_count, false_count)``. Retrieval goes through
    ``retrieve_context`` (openevolve-compatible); calls go through ``call_llm``
    (retry-after resilient); the system prompt carries the vendor access-notation
    legend + name aliasing the validator card was calibrated with."""
    os.makedirs(output_dir, exist_ok=True)
    for fn in ("classification.csv", "usage.csv", "output.txt"):     # fresh run
        p = os.path.join(output_dir, fn)
        if os.path.exists(p):
            os.remove(p)
    saver = ResultSaver(output_dir)

    batches: dict[tuple, list] = defaultdict(list)
    for inv in invariants:
        batches[(inv["peripheral_name"], inv["register_name"])].append(inv)
    logger.info("Validating %d invariants in %d register batches",
                len(invariants), len(batches))

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
