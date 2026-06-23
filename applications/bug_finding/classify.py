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
import re
from typing import Optional

import config
from utils.utils import setup_logger
from utils.llm import call_llm
from utils.parse_output import get_json_block_from_response
from utils.result_saver import ResultSaver, UsageStats
from utils.models import model_costs
from .models import Diff, Bug, BugClass, BugStatus

logger = setup_logger(__name__)

# Register offsets within a peripheral are small; a larger value is an absolute address.
_OFFSET_ABS_THRESHOLD = 0x1000
_NOT_FOUND_TOKENS = {"", "n/a", "na", "none", "not found", "not specified", "unknown"}


def _as_int(value: Optional[str]) -> Optional[int]:
    v = (value or "").strip()
    if re.fullmatch(r"0x[0-9a-fA-F]+", v):
        return int(v, 16)
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return None


def _scrambled_registers(diffs: list[Diff]) -> set[tuple[str, str]]:
    """(peripheral, register) whose bit_offset diffs look like a whole-register
    misparse: >=3 differing fields whose shifts are not all equal (a permutation,
    not a uniform shift)."""
    by_reg: dict[tuple[str, str], list[int]] = {}
    for d in diffs:
        if d.key == "bit_offset":
            s, g = _as_int(d.svd_value), _as_int(d.generator_value)
            if s is not None and g is not None:
                by_reg.setdefault((d.peripheral, d.register), []).append(g - s)
    return {k for k, deltas in by_reg.items() if len(deltas) >= 3 and len(set(deltas)) > 1}


def mechanical_fp_reason(diff: Diff, scrambled: set[tuple[str, str]]) -> Optional[str]:
    """Reason string if *diff* is a clear generator false positive, else None.

    Deterministic signatures only (no LLM): not-found placeholders, absolute
    addresses where an offset is expected, ranges/formulas instead of a single
    value, and whole-register scrambled bit layouts.
    """
    g = (diff.generator_value or "").strip()
    if g.lower() in _NOT_FOUND_TOKENS:
        return "generator value empty / not-found"
    gi = _as_int(g)
    if diff.key == "address_offset":
        if "%" in diff.register:
            return "array/template register reported as range/formula"
        if gi is None:
            return "address_offset is a range/formula, not a single offset"
        if gi >= _OFFSET_ABS_THRESHOLD:
            return "absolute address emitted instead of peripheral offset"
        return None
    if diff.key in ("bit_offset", "bit_width"):
        if gi is None:
            return "bit value is a range/multi-value, not a single integer"
        if diff.key == "bit_offset" and (diff.peripheral, diff.register) in scrambled:
            return "whole-register bit layout misparse (fields scrambled)"
    return None


def split_mechanical_fps(diffs: list[Diff]) -> tuple[list[tuple[Diff, str]], list[Diff]]:
    """Split value-mismatch diffs into (fp_pairs, candidates).

    fp_pairs are deterministic generator FPs (with a reason); candidates go to the
    analyzer. Keeps the FPs (the caller records them pre-marked) so the generator's
    FP rate stays visible rather than being silently dropped.
    """
    mism = [d for d in diffs if d.is_value_mismatch]
    scrambled = _scrambled_registers(mism)
    fps: list[tuple[Diff, str]] = []
    candidates: list[Diff] = []
    for d in mism:
        reason = mechanical_fp_reason(d, scrambled)
        (fps.append((d, reason)) if reason else candidates.append(d))
    return fps, candidates

_SYSTEM_PROMPT = (
    "You are an expert embedded-systems engineer auditing an SVD file against a "
    "device datasheet. For each numbered difference, `svd_value` is what the SVD "
    "file says and `generator_value` is what an extracting agent read from the "
    "datasheet. You are ALSO given that agent's per-register datasheet REASONING. "
    "A row is a REAL SVD bug ONLY if the datasheet (as reflected in the reasoning) "
    "clearly supports generator_value over svd_value. EXCLUDE a row when:\n"
    "- the reasoning does not actually support generator_value, or is absent/uncertain;\n"
    "- generator_value is a not-found placeholder (empty, 'N/A', 'not found', 'unknown');\n"
    "- generator_value is an absolute address rather than a register offset;\n"
    "- generator_value is a range, formula, or multiple values;\n"
    "- many fields of the SAME register differ together — that is a likely whole-register "
    "misparse, not many independent bugs, so exclude them.\n"
    "Be conservative: structural values (address offsets, bit positions and widths) are "
    "easy to mis-extract, so require clear datasheet support to keep a row. "
    "Return ONLY a JSON object in a ```json code block with this shape:\n"
    '{"bugs": [{"id": <int>, "confidence": <float 0..1>}]}\n'
    "Include only rows that are real candidate bugs; `confidence` reflects how strongly "
    "the datasheet supports the bug. Do not add other fields."
)


def _format_candidates(candidates: list[Diff]) -> str:
    lines = ["id | location | key | svd_value | generator_value"]
    for i, d in enumerate(candidates):
        lines.append(f"{i} | {d.location} | {d.key} | {d.svd_value} | {d.generator_value}")
    return "\n".join(lines)


def _build_user_prompt(
    candidates: list[Diff],
    evidence_by_register: dict[tuple[str, str], str] | None,
    evidence_by_peripheral: dict[str, str] | None,
    max_evidence_chars: int = 500,
) -> str:
    """User prompt = per-register datasheet reasoning + the numbered diff table."""
    by_reg = evidence_by_register or {}
    by_per = evidence_by_peripheral or {}
    blocks: list[str] = []
    seen: set[tuple[str, str]] = set()
    for d in candidates:
        key = (d.peripheral, d.register)
        if key in seen:
            continue
        seen.add(key)
        ev = by_reg.get(key) or by_per.get(d.peripheral) or ""
        ev = " ".join(ev.split())
        if ev:
            if len(ev) > max_evidence_chars:
                ev = ev[:max_evidence_chars].rstrip() + " …"
            blocks.append(f"[{d.peripheral}.{d.register}] {ev}")
    evidence_section = "\n".join(blocks) if blocks else "(no datasheet reasoning available)"
    return (
        "Datasheet reasoning per register (from the extracting agent):\n"
        f"{evidence_section}\n\n"
        "Differences to analyze:\n"
        f"{_format_candidates(candidates)}\n\n"
        "Return the JSON object of real candidate bugs."
    )


def run_analyzer(
    svd_file_name: str,
    diffs: list[Diff],
    output_dir: str,
    models: list[str] | None = None,
    evidence_by_register: dict[tuple[str, str], str] | None = None,
    evidence_by_peripheral: dict[str, str] | None = None,
) -> list[Bug]:
    """Filter value-mismatch diffs to real SVD bugs via the analyzer LLM.

    The analyzer is given the generator's per-register datasheet reasoning as
    evidence so it can judge whether generator_value is actually supported.
    Uses the central call layer with ``models`` (default config.STAGE_MODELS
    ["analyzer"]). Returns Bugs (diff + confidence).
    """
    candidates = [d for d in diffs if d.is_value_mismatch]
    logger.info(
        "Analyzer for %s: %d value-mismatch candidates", svd_file_name, len(candidates),
    )
    if not candidates:
        return []

    model_list = models or config.STAGE_MODELS.get("analyzer")
    saver = ResultSaver(output_dir)
    user_prompt = _build_user_prompt(candidates, evidence_by_register, evidence_by_peripheral)

    # Generous output budget: reasoning models share the budget between reasoning
    # and the JSON answer; without a high cap the JSON truncates for many candidates.
    model_max = model_costs.get(model_list[0], {}).get("max_output_tokens", 32_768)
    response, used_model = call_llm(
        "analyzer", models=model_list,
        input=[
            {"role": "developer", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        tool_choice="none",
        truncation="auto",
        max_output_tokens=model_max,
    )

    saver.save_usage_stats(
        UsageStats.from_response_usage(used_model, response.usage),
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


def attach_evidence(
    bugs: list[Bug],
    by_register: dict[tuple[str, str], str],
    by_peripheral: dict[str, str],
    max_chars: int = 1500,
) -> list[Bug]:
    """Fill each bug's ``datasheet_evidence`` from preloaded generator reasoning maps."""
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
