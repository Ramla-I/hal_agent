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


# Min fields for a whole-register bit-layout signature to be trusted.
_REGISTER_SHIFT_MIN_FIELDS = 3


def _register_bit_shift_classes(diffs: list[Diff]) -> dict[tuple[str, str], str]:
    """Classify each register's bit_offset diffs as a whole-register artifact:

      'scrambled'     — >=3 fields whose shifts are NOT all equal (a permutation);
      'uniform_shift' — >=3 fields ALL shifted by the same nonzero amount
                        (off-by-one / table-misalignment, not isolated bugs).

    Registers with fewer differing fields are left unclassified (real isolated
    bugs look like one or two fields, so they stay candidates).
    """
    by_reg: dict[tuple[str, str], list[int]] = {}
    for d in diffs:
        if d.key == "bit_offset":
            s, g = _as_int(d.svd_value), _as_int(d.generator_value)
            if s is not None and g is not None:
                by_reg.setdefault((d.peripheral, d.register), []).append(g - s)
    classes: dict[tuple[str, str], str] = {}
    for key, deltas in by_reg.items():
        if len(deltas) < _REGISTER_SHIFT_MIN_FIELDS:
            continue
        uniq = set(deltas)
        if len(uniq) > 1:
            classes[key] = "scrambled"
        elif 0 not in uniq:
            classes[key] = "uniform_shift"
    return classes


def mechanical_fp_reason(diff: Diff, shift_classes: dict[tuple[str, str], str]) -> Optional[str]:
    """Reason string if *diff* is a clear generator false positive, else None.

    Deterministic signatures only (no LLM): not-found placeholders, absolute
    addresses where an offset is expected, ranges/formulas instead of a single
    value, and whole-register bit layouts that are scrambled or uniformly shifted.
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
        if diff.key == "bit_offset":
            cls = shift_classes.get((diff.peripheral, diff.register))
            if cls == "scrambled":
                return "whole-register bit layout misparse (fields scrambled)"
            if cls == "uniform_shift":
                return "whole-register uniform bit shift (likely off-by-one)"
    return None


def split_mechanical_fps(diffs: list[Diff]) -> tuple[list[tuple[Diff, str]], list[Diff]]:
    """Split value-mismatch diffs into (fp_pairs, candidates).

    fp_pairs are deterministic generator FPs (with a reason); candidates go to the
    analyzer. Keeps the FPs (the caller records them pre-marked) so the generator's
    FP rate stays visible rather than being silently dropped.
    """
    mism = [d for d in diffs if d.is_value_mismatch]
    shift_classes = _register_bit_shift_classes(mism)
    fps: list[tuple[Diff, str]] = []
    candidates: list[Diff] = []
    for d in mism:
        reason = mechanical_fp_reason(d, shift_classes)
        (fps.append((d, reason)) if reason else candidates.append(d))
    return fps, candidates

_SYSTEM_PROMPT = (
    "You are an expert embedded-systems engineer screening differences between an SVD "
    "file (`svd_value`) and a value another agent extracted from the datasheet "
    "(`generator_value`). Your ONLY job is to drop rows that are clearly NOT real SVD "
    "bugs; deeper datasheet verification happens in a later validation stage, so keep "
    "every plausible value mismatch. Drop a row only when it is obviously not a bug:\n"
    "- generator_value is a not-found placeholder (empty, 'N/A', 'not found', 'unknown');\n"
    "- the two values are the same thing in a different representation;\n"
    "- generator_value is an absolute address, a range, or a formula rather than a value.\n"
    "Do NOT try to determine which value is actually correct from memory. "
    "Return ONLY a JSON object in a ```json code block with this shape:\n"
    '{"bugs": [{"id": <int>, "confidence": <float 0..1>}]}\n'
    "Include the rows that remain plausible SVD bugs; `confidence` is how likely the "
    "row is a genuine mismatch (not a representation artifact). Do not add other fields."
)


def _format_candidates(candidates: list[Diff]) -> str:
    lines = ["id | location | key | svd_value | generator_value"]
    for i, d in enumerate(candidates):
        lines.append(f"{i} | {d.location} | {d.key} | {d.svd_value} | {d.generator_value}")
    return "\n".join(lines)


def _diff_key(d: Diff) -> str:
    """Stable identity of a candidate diff (independent of list position) so the
    analyzer verdict cache survives re-runs where the candidate set changes."""
    return "|".join((
        d.peripheral, d.register, d.field or "", d.key,
        str(d.svd_value), str(d.generator_value),
    ))


def run_analyzer(
    svd_file_name: str,
    diffs: list[Diff],
    output_dir: str,
    models: list[str] | None = None,
) -> list[Bug]:
    """Screen value-mismatch diffs, dropping obvious non-bugs via the analyzer LLM.

    Lightweight by design: it removes obvious junk (not-found placeholders,
    representation differences) and keeps plausible mismatches. Datasheet-grounded
    verification is the (separate) validator's job, not the analyzer's. Uses the
    central call layer with ``models`` (default config.STAGE_MODELS["analyzer"]).

    Incremental (like the generator and validator): each candidate's verdict is
    cached by stable identity in ``{svd}_analyzer_cache.json``. On a re-run only
    candidates the analyzer has never seen are sent to the LLM — an SVD whose
    candidate set is unchanged makes no call at all. A fresh run has no cache, so
    every candidate is judged exactly as before.
    """
    candidates = [d for d in diffs if d.is_value_mismatch]
    logger.info(
        "Analyzer for %s: %d value-mismatch candidates", svd_file_name, len(candidates),
    )
    if not candidates:
        return []

    saver = ResultSaver(output_dir)
    cache_name = f"{svd_file_name}_analyzer_cache.json"
    cache_path = os.path.join(output_dir, cache_name)
    cache: dict = {}
    if os.path.exists(cache_path):
        try:
            cache = json.load(open(cache_path, encoding="utf-8"))
        except Exception:
            cache = {}

    keys = [_diff_key(d) for d in candidates]
    new_positions = [i for i, k in enumerate(keys) if k not in cache]
    provisional_keys: set = set()  # keys kept-but-not-cached after a hard analyzer miss

    if new_positions:
        new_candidates = [candidates[i] for i in new_positions]
        logger.info("Analyzer for %s: %d new candidate(s) to judge (%d cached)",
                    svd_file_name, len(new_candidates), len(candidates) - len(new_candidates))
        model_list = models or config.STAGE_MODELS.get("analyzer")
        user_prompt = (
            "Differences to screen:\n"
            f"{_format_candidates(new_candidates)}\n\n"
            "Return the JSON object of rows that remain plausible SVD bugs."
        )
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
            additional_fields={"svd_name": svd_file_name, "candidates": len(new_candidates)},
        )
        # Verdict ids index into new_candidates; kept ids get their confidence, the
        # rest are recorded as judged-and-dropped so they are not re-sent next run.
        verdicts = _parse_verdicts(response.output_text, svd_file_name)
        if verdicts is None:
            # Hard analyzer failure (no JSON block) — a transient LLM hiccup, not a
            # genuine "drop everything". Do NOT cache (so a re-run re-judges) and keep
            # this batch's candidates provisionally, so real bugs aren't silently lost.
            logger.warning("Analyzer produced no parseable output for %s — keeping %d "
                           "candidate(s) provisionally, not cached (re-judged next run)",
                           svd_file_name, len(new_candidates))
            provisional_keys.update(keys[pos] for pos in new_positions)
        else:
            kept_conf: dict[int, float] = {}
            for v in verdicts:
                idx = v.get("id")
                if not isinstance(idx, int) or not (0 <= idx < len(new_candidates)):
                    logger.warning("Analyzer returned out-of-range id %r for %s", idx, svd_file_name)
                    continue
                try:
                    kept_conf[idx] = float(v.get("confidence", 0.0))
                except (TypeError, ValueError):
                    kept_conf[idx] = 0.0
            for j, pos in enumerate(new_positions):
                cache[keys[pos]] = {"kept": j in kept_conf, "confidence": kept_conf.get(j, 0.0)}
            saver.save_json(cache, cache_name)
    else:
        logger.info("Analyzer for %s: all %d candidate(s) cached — no LLM call",
                    svd_file_name, len(candidates))

    bugs: list[Bug] = []
    for d, k in zip(candidates, keys):
        entry = cache.get(k)
        if entry and entry.get("kept"):
            bugs.append(Bug(diff=d, confidence=entry.get("confidence", 0.0)))
        elif k in provisional_keys:  # analyzer-miss batch: keep, uncached, re-judged next run
            bugs.append(Bug(diff=d, confidence=0.0))

    logger.info("Analyzer for %s: kept %d/%d as bugs", svd_file_name, len(bugs), len(candidates))
    return bugs


def _parse_verdicts(output_text: str, svd_file_name: str):
    """Parsed verdict dicts, ``[]`` for a valid empty answer, or ``None`` for a hard
    failure (no JSON block at all) so the caller can avoid caching a transient miss."""
    block = get_json_block_from_response(output_text)
    if not block:
        logger.error("Analyzer returned no JSON block for %s", svd_file_name)
        return None
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
