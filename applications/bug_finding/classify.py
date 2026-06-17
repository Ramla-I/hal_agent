"""SVD-bug filter (the s5 analyzer) + bug-class grouping, in memory.

Replaces ``core/s5_analyzer.py``. Two differences from the old analyzer:

  * It consumes ``list[Diff]`` directly (no register_diff.csv round-trip) and
    returns ``list[Bug]``.
  * It runs via ``client.responses.create()`` — the same path the generator and
    validator use — so ``model_name`` actually selects the model. (The old
    analyzer used the agents SDK without setting a model, silently running on the
    SDK default and ignoring the requested model.)

The analyzer reads only **value-mismatch** diffs (a value present on both sides
but differing) and decides which are real SVD bugs vs. generator noise
("N/A", "not found", representational differences). It also returns a confidence
per kept bug. Datasheet evidence is attached separately from the generator's
reasoning (it requires no extra LLM call).
"""
from __future__ import annotations

import json
import os
from typing import Optional

from groq import Groq
from openai import OpenAI

from utils.utils import get_model_string, setup_logger, responses_create_with_retry
from utils.parse_output import get_json_block_from_response
from utils.result_saver import ResultSaver, UsageStats
from utils.models import model_costs
from .models import Diff, Bug, BugClass

logger = setup_logger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert embedded-systems engineer auditing an SVD file against a "
    "device datasheet. You are given a numbered list of differences. For each row, "
    "`svd_value` is what the SVD file says and `generator_value` is what another "
    "agent extracted from the datasheet for the same attribute. "
    "Decide which rows are REAL SVD bugs — i.e. the SVD value is wrong and the "
    "datasheet-derived value is the correct one. "
    "A row is NOT a bug when the generator_value indicates the information wasn't "
    "found (e.g. 'N/A', 'not found', 'not specified', 'unknown', empty), or when "
    "the two values are just different representations of the same thing. "
    "Return ONLY a JSON object in a ```json code block with this shape:\n"
    '{"bugs": [{"id": <int>, "confidence": <float 0..1>}]}\n'
    "Include only rows that are real candidate bugs. `confidence` is your "
    "confidence that it is a genuine SVD bug. Do not add any other fields."
)


def _format_candidates(candidates: list[Diff]) -> str:
    lines = ["id | location | key | svd_value | generator_value"]
    for i, d in enumerate(candidates):
        lines.append(f"{i} | {d.location} | {d.key} | {d.svd_value} | {d.generator_value}")
    return "\n".join(lines)


def run_analyzer(
    client: OpenAI | Groq,
    model_name: str,
    svd_file_name: str,
    diffs: list[Diff],
    output_dir: str,
) -> list[Bug]:
    """Filter value-mismatch diffs to real SVD bugs via the analyzer LLM.

    Returns a list of Bugs (diff + confidence); datasheet evidence is left empty
    here and filled by ``attach_evidence``.
    """
    candidates = [d for d in diffs if d.is_value_mismatch]
    logger.info(
        "Analyzer for %s: %d value-mismatch candidates", svd_file_name, len(candidates),
    )
    if not candidates:
        return []

    saver = ResultSaver(output_dir)
    user_prompt = (
        "Differences to analyze:\n"
        f"{_format_candidates(candidates)}\n\n"
        "Return the JSON object of real candidate bugs."
    )

    # Generous output budget: gpt-oss-120b is a reasoning model, so reasoning
    # tokens share the budget with the JSON answer. Without a high cap the JSON
    # can be truncated for SVDs with many candidates.
    model_max = model_costs.get(model_name, {}).get("max_output_tokens", 32_768)
    response = responses_create_with_retry(
        client,
        model=get_model_string(model_name),
        input=[
            {"role": "developer", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        tool_choice="none",
        truncation="auto",
        max_output_tokens=model_max,
    )

    saver.save_usage_stats(
        UsageStats.from_response_usage(model_name, response.usage),
        "usage.csv",
        additional_fields={"svd_name": svd_file_name, "candidates": len(candidates)},
    )

    verdicts = _parse_verdicts(response.output_text, svd_file_name)
    saver.save_json(verdicts, f"{svd_file_name}_verdicts.json")

    bugs: list[Bug] = []
    for v in verdicts:
        idx = v.get("id")
        if not isinstance(idx, int) or not (0 <= idx < len(candidates)):
            logger.warning("Analyzer returned out-of-range id %r for %s", idx, svd_file_name)
            continue
        confidence = v.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        bugs.append(Bug(diff=candidates[idx], confidence=confidence))

    logger.info("Analyzer for %s: kept %d/%d as bugs", svd_file_name, len(bugs), len(candidates))
    return bugs


def _parse_verdicts(output_text: str, svd_file_name: str) -> list[dict]:
    block = get_json_block_from_response(output_text)
    if not block:
        logger.error("Analyzer returned no JSON block for %s", svd_file_name)
        return []
    try:
        data = json.loads(block)
    except json.JSONDecodeError as e:
        # Truncated/malformed JSON — salvage the complete bug objects we can.
        salvaged = _salvage_bug_objects(block)
        logger.warning(
            "Analyzer JSON parse failed for %s (%s); salvaged %d object(s)",
            svd_file_name, e, len(salvaged),
        )
        return salvaged
    bugs = data.get("bugs", []) if isinstance(data, dict) else []
    return bugs if isinstance(bugs, list) else []


def _salvage_bug_objects(block: str) -> list[dict]:
    """Recover complete ``{...}`` entries from a truncated ``"bugs": [ ... ]`` array."""
    start_array = block.find("[")
    if start_array < 0:
        return []
    objects: list[dict] = []
    depth = 0
    obj_start: Optional[int] = None
    for i in range(start_array, len(block)):
        ch = block[i]
        if ch == "{":
            if depth == 0:
                obj_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and obj_start is not None:
                try:
                    obj = json.loads(block[obj_start:i + 1])
                    if isinstance(obj, dict) and "id" in obj:
                        objects.append(obj)
                except json.JSONDecodeError:
                    pass
                obj_start = None
    return objects


# ---------------------------------------------------------------------------
# Datasheet evidence (from generator reasoning.jsonl — no extra LLM call)
# ---------------------------------------------------------------------------

def load_generator_evidence(agent_output_dir: str) -> tuple[dict[tuple[str, str], str], dict[str, str]]:
    """Load generator reasoning as evidence, keyed by (peripheral, register) and
    by peripheral (batched fallback).

    Reads ``info/reasoning.jsonl`` (written by the generator). Returns
    ``(by_register, by_peripheral)``; both empty if the file is absent.
    """
    by_register: dict[tuple[str, str], str] = {}
    by_peripheral: dict[str, str] = {}
    path = os.path.join(agent_output_dir, "info", "reasoning.jsonl")
    if not os.path.exists(path):
        return by_register, by_peripheral

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            peripheral = (row.get("peripheral") or "").lower()
            reasoning = row.get("reasoning") or ""
            if not peripheral:
                continue
            by_peripheral.setdefault(peripheral, reasoning)
            register = row.get("register")
            if register:
                by_register[(peripheral, register.lower())] = reasoning
    return by_register, by_peripheral


def attach_evidence(bugs: list[Bug], agent_output_dir: str, max_chars: int = 1500) -> list[Bug]:
    """Fill each bug's ``datasheet_evidence`` from generator reasoning (in place)."""
    by_register, by_peripheral = load_generator_evidence(agent_output_dir)
    if not by_register and not by_peripheral:
        return bugs
    for bug in bugs:
        d = bug.diff
        evidence = by_register.get((d.peripheral, d.register)) or by_peripheral.get(d.peripheral, "")
        if evidence and len(evidence) > max_chars:
            evidence = evidence[:max_chars].rstrip() + " …"
        bug.datasheet_evidence = evidence
    return bugs


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------

def classify_bug_classes(bugs: list[Bug], svd_file: str) -> list[BugClass]:
    """Group bugs into reviewer-facing classes keyed by (svd_file, peripheral, key).

    Each class maps 1:1 to a prospective PR. Classes are sorted by peripheral then
    key for stable output; bugs within a class are sorted by location.
    """
    groups: dict[tuple[str, str], list[Bug]] = {}
    for bug in bugs:
        key = (bug.diff.peripheral, bug.diff.key)
        groups.setdefault(key, []).append(bug)

    classes: list[BugClass] = []
    for (peripheral, key) in sorted(groups):
        class_bugs = sorted(groups[(peripheral, key)], key=lambda b: b.diff.location)
        classes.append(BugClass(svd_file=svd_file, peripheral=peripheral, key=key, bugs=class_bugs))
    return classes
