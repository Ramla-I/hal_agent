#!/usr/bin/env python3
"""LLM judge for the Constraint Validator (plan §7.0 stage 1, §7.1).

Closed-book validation of extracted register-access constraints: for every
quote-ANCHORED row (tier ``exact`` or ``fuzzy`` in ``anchors.jsonl``) the
judge sees ONLY the verbatim quote, its derived surrounding context, and the
structured encoding — no retrieval, no file access. It answers:

  (a) is_constraint      — does the quoted text state a genuine access or
                           ordering REQUIREMENT (vs. descriptive behavior,
                           flag semantics, validity notes)?
  (b) encoding_faithful  — do target register, operation, fields, polarities
                           and values match the text?
  (c) verdict            — "confirmed" | "encoding_error" | "not_constraint",
                           plus confidence 0-1 and a one-sentence reason.

Model: openai/gpt-oss-120b via Groq (OpenAI SDK, base_url override; env
GROQ_API_KEY). NO structured-output / json_schema mode — Groq OSS models
hard-error on it; instead free-form completion + robust JSON-block recovery
(fenced or bare) with one per-item repair retry. ``run_judge(batch_size=N)``
judges N items per call (the big system prompt is sent once per batch), with a
per-item ``judge_one`` fallback for any item the batch response omits.

The constraint under validation is the native grammar-v2 object of ANY kind
(``state_gate``, ``sequence``, ``delay``, ``clock_gate``, ``write_once``,
``read_effect``, ``value_relation``, ``other``); ``constraint_payload`` shows it
kind-agnostically.

This module is a LIBRARY: s0 (``--constraint-validation``) and the calibration
harness call ``make_client`` / ``load_items`` / ``run_judge`` directly. The
manual calibration CLI and its tuning-only helpers (stratified sampling,
corruption-row loading, and judgment writing with the §7.2 blindness guard)
live in ``tune_constraint_validator/judge_cli.py``.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL = "openai/gpt-oss-120b"          # Groq's model id (verified by smoke run)
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

JUDGEABLE_TIERS = ("exact", "fuzzy")   # plan §7.1: unanchored rows die earlier
VERDICTS = ("confirmed", "encoding_error", "not_constraint")

CALL_TIMEOUT_S = 120.0
MAX_HTTP_RETRIES = 6                   # 429/5xx/timeout retries per API call
BACKOFF_BASE_S = 2.0
BACKOFF_CAP_S = 60.0
DEFAULT_CONCURRENCY = 6

# ---------------------------------------------------------------------------
# Prompts (the LLM *validates*; runtime Rust *checks*; the compiler *enforces*)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are validating hardware register access constraints extracted from a \
microcontroller reference manual (datasheet). Each item gives you:
- CONSTRAINT: a structured object the extractor produced. It has a "kind" \
field and kind-specific fields (see below).
- QUOTE: the verbatim datasheet sentence(s) the extractor cited as evidence,
- CONTEXT: the true surrounding text, derived programmatically from the manual.

Validate the encoding against ONLY the given QUOTE and CONTEXT. Do not rely \
on outside knowledge of any specific device; a detail the given text does not \
support is unsupported.

The "kind" is one of:
- state_gate: an operation (target_operation "read" or "write") on \
target_register / target_fields is permitted only while the preconditions hold \
(postconditions must then follow). Each condition names a register + field and \
a required state ("cleared", "set", or "equals" a value).
- sequence: an ordered multi-step protocol (steps, each a register "write" or \
"read" with an optional value), optionally unlocking something (enables).
- write_once: target_register / target_fields may be written only once until a \
reset (reset_scope).
- delay: a required wait (duration + unit) after one access, before a \
dependent one.
- read_effect: reading read_register changes flags (effects: a field \
"becomes" cleared/set).
- clock_gate: a peripheral clock (clock) must be enabled before any access.
- value_relation: a required relationship between field values (fields); the \
relation itself is stated in the quote.
- other: a genuine access/ordering requirement described in words \
(description, involved).

Answer three questions:
(a) is_constraint — does the quoted text state a genuine access or ordering \
REQUIREMENT that software must respect (e.g. "write only when X", "set A \
before B", unlock/key sequences, "wait N cycles", "enable the clock first")? \
Purely descriptive behavior, status-flag semantics (how a flag is set or \
cleared, write-1-to-clear / write-0-to-clear acknowledge notes), reset-value \
notes, and validity or don't-care notes are NOT constraints.
(b) encoding_faithful — does EVERY field of the object match the text, for its \
kind? For state_gate: the target register, operation, the fields named, the \
polarities (set vs cleared), and any required values -- the operation is \
"read" or "write" only, so datasheet text about "modifying"/"changing" a \
register means WRITING it (established_by and action_operation are method \
details that need not appear in the quote; flag them only if the text plainly \
contradicts them). For sequence: the steps, their ORDER, and the values. For \
delay: the duration, unit, and what it gates. For read_effect: the register \
read and which flags change and how. For clock_gate: the clock/enable bit. For \
write_once: the register/fields and reset scope. For value_relation / other: \
the registers/fields involved and the stated relation. A field that \
contradicts, misstates, or is absent from the text makes the encoding \
unfaithful. Judge ONLY against the given text and context.
(c) verdict —
  "confirmed"      : genuine constraint AND the encoding is faithful.
  "encoding_error" : genuine constraint, but the encoding misstates it (wrong \
register, operation, field, polarity, value, step order, duration, ...).
  "not_constraint" : the quoted text is not an access/ordering requirement.
If is_constraint is false, use verdict "not_constraint" and set \
encoding_faithful to false.

Also report confidence (a number from 0 to 1) and a one-sentence reason.

Respond with a single JSON object and nothing else, keys exactly:
{"is_constraint": <bool>, "encoding_faithful": <bool>, \
"verdict": "<confirmed|encoding_error|not_constraint>", \
"confidence": <float>, "reason": "<one sentence>"}

Worked example 1 — a genuine state_gate, faithfully encoded (target register \
usart1 brr):
CONSTRAINT: {"kind": "state_gate", "target_operation": "write", \
"target_fields": [], "preconditions": [{"register": "USART_CR1", "field": \
"UE", "state": "cleared"}], "postconditions": [], "severity": "error"}
QUOTE: This register can only be written when the USART is disabled (UE=0).
Correct response:
{"is_constraint": true, "encoding_faithful": true, "verdict": "confirmed", \
"confidence": 0.97, "reason": "The text requires the USART to be disabled \
(UE=0) before writing this register, exactly matching the encoded \
precondition."}

Worked example 2 — a sequence, faithfully encoded (target register rtc wpr):
CONSTRAINT: {"kind": "sequence", "steps": [{"register": "RTC_WPR", \
"operation": "write", "value": 202}, {"register": "RTC_WPR", "operation": \
"write", "value": 83}], "severity": "error"}
QUOTE: To unlock write protection, write 0xCA into the RTC_WPR register, then \
write 0x53.
Correct response:
{"is_constraint": true, "encoding_faithful": true, "verdict": "confirmed", \
"confidence": 0.95, "reason": "The text prescribes writing 0xCA (202) then \
0x53 (83) to RTC_WPR in that order, matching the two encoded step values and \
their sequence."}

Worked example 3 — flag-acknowledge semantics, not a constraint (target \
register wwdg sr):
CONSTRAINT: {"kind": "state_gate", "target_operation": "write", \
"target_fields": [], "preconditions": [], "postconditions": [{"register": \
"WWDG_SR", "field": "EWIF", "state": "cleared"}], "severity": "error"}
QUOTE: This bit is set by hardware when the counter has reached the value \
0x40. It must be cleared by software by writing '0'. A write of '1' has no \
effect.
Correct response:
{"is_constraint": false, "encoding_faithful": false, \
"verdict": "not_constraint", "confidence": 0.93, "reason": "The text \
describes how a status flag is set by hardware and acknowledged by software \
(write-0-to-clear semantics), not an access or ordering requirement on the \
register."}
"""

REPAIR_PROMPT = (
    "Your previous reply was not a single valid JSON object. Respond again "
    "with ONLY the JSON object, keys exactly: is_constraint, "
    "encoding_faithful, verdict, confidence, reason."
)

# Batch mode: the validation RULES and worked examples are identical; only the
# output envelope changes (a JSON ARRAY keyed by id, not one object), so the
# costly system prompt is sent ONCE per batch instead of once per item. Derived
# by swapping the single-object instruction so the two prompts can't drift.
_SINGLE_OUTPUT = (
    'Respond with a single JSON object and nothing else, keys exactly:\n'
    '{"is_constraint": <bool>, "encoding_faithful": <bool>, '
    '"verdict": "<confirmed|encoding_error|not_constraint>", '
    '"confidence": <float>, "reason": "<one sentence>"}'
)
_BATCH_OUTPUT = (
    'You are given MULTIPLE items below, each in a block headed by '
    '"ITEM id=<id>". Judge each INDEPENDENTLY against ONLY its own QUOTE and '
    'CONTEXT. Respond with a single JSON ARRAY and nothing else: one object '
    'per item, each with keys exactly:\n'
    '{"id": "<the item id>", "is_constraint": <bool>, '
    '"encoding_faithful": <bool>, '
    '"verdict": "<confirmed|encoding_error|not_constraint>", '
    '"confidence": <float>, "reason": "<one sentence>"}\n'
    '(The worked examples below each show ONE item; in a batch you return an '
    'array of such objects, each carrying its "id".)'
)
SYSTEM_PROMPT_BATCH = SYSTEM_PROMPT.replace(_SINGLE_OUTPUT, _BATCH_OUTPUT)

# ---------------------------------------------------------------------------
# Client (two-line Groq convention from config.py, replicated locally so this
# module never imports config.py / pipeline deps)
# ---------------------------------------------------------------------------


def make_client():
    from openai import OpenAI  # lazy: tests inject a fake client instead
    return OpenAI(api_key=os.environ.get("GROQ_API_KEY"),
                  base_url=GROQ_BASE_URL)


# ---------------------------------------------------------------------------
# Data loading / item preparation
# ---------------------------------------------------------------------------


def parse_json_list(value):
    """CSV cells hold JSON arrays as strings; corruption records may hold
    real lists. Return a list either way ([] on blank/garbage)."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    try:
        out = json.loads(value)
    except (ValueError, TypeError):
        return []
    return out if isinstance(out, list) else []


def load_csv_rows(csv_path: str) -> list:
    with open(csv_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_anchors(anchors_path: str) -> dict:
    """anchors.jsonl -> {id: anchor_record}."""
    out = {}
    with open(anchors_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                out[rec["id"]] = rec
    return out


def _row_constraint(row: dict) -> dict:
    """The native grammar-v2 constraint object for a CSV row. Prefer a
    ``constraint_json`` column (any kind); fall back to synthesizing a
    ``state_gate`` object from the legacy flat columns, so pre-migration
    datasets (``stm.csv``) still judge until they are rebuilt."""
    raw = row.get("constraint_json")
    if raw:
        try:
            obj = json.loads(raw)
        except (ValueError, TypeError):
            obj = None
        if isinstance(obj, dict):
            return obj
    return {
        "kind": "state_gate",
        "target_operation": row.get("target_operation", ""),
        "target_fields": parse_json_list(row.get("target_fields")),
        "preconditions": parse_json_list(row.get("preconditions")),
        "postconditions": parse_json_list(row.get("postconditions")),
        "severity": row.get("severity", ""),
    }


def load_items(csv_path: str, anchors_path: str) -> list:
    """Join CSV rows with anchors by id; keep only judgeable tiers (exact,
    fuzzy) that carry a derived context. Attaches the native constraint object
    as ``item["constraint"]``. Returns item dicts sorted by id. (This is the
    calibration reader; the product path builds items in memory instead.)"""
    anchors = load_anchors(anchors_path)
    items = []
    for row in load_csv_rows(csv_path):
        anc = anchors.get(row.get("id", ""))
        if not anc or anc.get("tier") not in JUDGEABLE_TIERS:
            continue
        if not anc.get("context"):
            continue
        item = dict(row)
        item["constraint"] = _row_constraint(row)
        item["context"] = anc["context"]
        item["tier"] = anc["tier"]
        items.append(item)
    items.sort(key=lambda it: it["id"])
    return items


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


_HIDDEN_PAYLOAD_KEYS = ("consequence", "datasheet_text", "enforceability")


def constraint_payload(item: dict) -> dict:
    """The structured encoding shown to the judge: the native grammar-v2
    constraint object (any ``kind``), minus three keys — ``datasheet_text``
    (shown separately as QUOTE), ``consequence`` (free-text extractor
    commentary; showing it would let the judge detect corruptions by internal
    inconsistency instead of against the datasheet), and the *computed*
    ``enforceability`` label (not an extraction to validate)."""
    constraint = item.get("constraint") or {}
    return {k: v for k, v in constraint.items()
            if k not in _HIDDEN_PAYLOAD_KEYS}


def referenced_registers(constraint: dict) -> list:
    """Every register a grammar-v2 constraint names, across all kinds
    (SVD-canonical). Lets anchoring verify a quote against ANY register the
    constraint touches — cross-register ``state_gate`` conditions, ``sequence``
    steps, ``value_relation`` fields, a ``read_effect``'s read register, etc.,
    not only the register it is filed under. The caller adds the filed one."""
    regs = set()

    def add(ref):
        r = ref.get("register") if isinstance(ref, dict) else ref
        if r:
            regs.add(str(r))

    add(constraint.get("target_register"))   # state_gate, write_once
    add(constraint.get("read_register"))     # read_effect
    add(constraint.get("clock"))             # clock_gate (a condition object)
    for key in ("preconditions", "postconditions", "steps", "fields",
                "involved"):
        for x in constraint.get(key) or []:
            add(x)
    for key in ("enables", "after", "before"):   # sequence / delay references
        add(constraint.get(key))
    return sorted(regs)


def build_user_message(item: dict) -> str:
    payload = constraint_payload(item)
    return "\n".join([
        f"Reference manual: {item.get('reference_manual', '')}",
        f"Peripheral: {item.get('peripheral', '')}",
        f"Register: {item.get('register', '')}",
        "",
        "CONSTRAINT (structured encoding under validation):",
        json.dumps(payload, indent=2, ensure_ascii=False),
        "",
        "QUOTE (verbatim datasheet text cited as evidence):",
        item.get("datasheet_text", "") or "",
        "",
        "CONTEXT (surrounding text derived from the manual):",
        item.get("context", "") or "",
    ])


# ---------------------------------------------------------------------------
# JSON-block recovery (no structured-output mode — see module docstring)
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json_block(text):
    """Best-effort extraction of one JSON object from free-form model output:
    whole text, fenced block, or first balanced {...} span (string-aware)."""
    if not text:
        return None
    candidates = [text.strip()]
    for m in _FENCE_RE.finditer(text):
        candidates.append(m.group(1).strip())
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except ValueError:
            continue
        if isinstance(obj, dict):
            return obj
    # balanced-brace scan over the raw text (handles prose-wrapped JSON)
    for m in re.finditer(r"\{", text):
        start = m.start()
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                    except ValueError:
                        break
                    if isinstance(obj, dict):
                        return obj
                    break
        # else: unbalanced from this start; try next '{'
    return None


def extract_json_array(text):
    """Best-effort extraction of one top-level JSON array (the batch response):
    whole text, fenced block, or the first balanced [...] span."""
    if not text:
        return None
    candidates = [text.strip()]
    for m in _FENCE_RE.finditer(text):
        candidates.append(m.group(1).strip())
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except ValueError:
            continue
        if isinstance(obj, list):
            return obj
    for m in re.finditer(r"\[", text):
        start = m.start()
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                    except ValueError:
                        break
                    if isinstance(obj, list):
                        return obj
                    break
    return None


def _to_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    if isinstance(v, str):
        t = v.strip().lower()
        if t in ("true", "yes"):
            return True
        if t in ("false", "no"):
            return False
    return None


def coerce_judgment(obj):
    """Validate/normalize a recovered dict into the judgment shape, or None
    if it cannot be salvaged (triggers the per-item retry)."""
    if not isinstance(obj, dict):
        return None
    verdict = obj.get("verdict")
    if isinstance(verdict, str):
        verdict = re.sub(r"[\s\-]+", "_", verdict.strip().lower())
    is_c = _to_bool(obj.get("is_constraint"))
    faith = _to_bool(obj.get("encoding_faithful"))
    if verdict not in VERDICTS:
        # derive from the booleans when the verdict string drifted
        if is_c is False:
            verdict = "not_constraint"
        elif is_c and faith:
            verdict = "confirmed"
        elif is_c and faith is False:
            verdict = "encoding_error"
        else:
            return None
    if is_c is None:
        is_c = verdict != "not_constraint"
    if faith is None:
        faith = verdict == "confirmed"
    try:
        conf = float(obj.get("confidence"))
    except (TypeError, ValueError):
        conf = 0.5
    conf = min(max(conf, 0.0), 1.0)
    reason = obj.get("reason")
    reason = str(reason).strip() if reason is not None else ""
    return {
        "verdict": verdict,
        "is_constraint": is_c,
        "encoding_faithful": faith,
        "confidence": conf,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# API call with backoff
# ---------------------------------------------------------------------------


def _status_of(exc):
    st = getattr(exc, "status_code", None)
    if st is None:
        st = getattr(getattr(exc, "response", None), "status_code", None)
    return st


def _retry_after_seconds(exc):
    headers = getattr(getattr(exc, "response", None), "headers", None)
    if headers:
        ra = headers.get("retry-after") or headers.get("Retry-After")
        try:
            return float(ra)
        except (TypeError, ValueError):
            return None
    return None


def _call_with_backoff(client, model, messages, timeout=CALL_TIMEOUT_S,
                       sleep=time.sleep):
    """One chat completion with exponential backoff on 429/5xx/timeouts
    (respecting Retry-After when present). Returns (content, ptok, ctok)."""
    for attempt in range(MAX_HTTP_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=model, messages=messages, temperature=0,
                timeout=timeout)
            content = resp.choices[0].message.content or ""
            u = getattr(resp, "usage", None)
            ptok = getattr(u, "prompt_tokens", 0) or 0
            ctok = getattr(u, "completion_tokens", 0) or 0
            return content, ptok, ctok
        except Exception as exc:  # noqa: BLE001 — classified below
            st = _status_of(exc)
            name = type(exc).__name__
            retryable = (st in (408, 429)
                         or (st is not None and st >= 500)
                         or "Timeout" in name or "Connection" in name)
            if not retryable or attempt == MAX_HTTP_RETRIES:
                raise
            delay = _retry_after_seconds(exc)
            if delay is None:
                delay = min(BACKOFF_BASE_S * (2 ** attempt), BACKOFF_CAP_S)
            sleep(delay)


# ---------------------------------------------------------------------------
# Per-item judging
# ---------------------------------------------------------------------------


def judge_one(client, item, model=MODEL, timeout=CALL_TIMEOUT_S,
              sleep=time.sleep) -> dict:
    """Judge one item; on unparseable output retry once with a repair
    message appended. Returns a judgment record (never raises on parse
    failure — verdict becomes "parse_failed")."""
    base = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(item)},
    ]
    ptok = ctok = calls = 0
    first_raw = None
    messages = base
    for attempt in (0, 1):
        content, pt, ct = _call_with_backoff(client, model, messages,
                                             timeout=timeout, sleep=sleep)
        calls += 1
        ptok += pt
        ctok += ct
        j = coerce_judgment(extract_json_block(content))
        if j is not None:
            rec = _base_record(item, model)
            rec.update(j)
            rec["parse_recovered"] = attempt > 0
            rec["usage"] = {"prompt_tokens": ptok, "completion_tokens": ctok,
                            "total_tokens": ptok + ctok, "calls": calls}
            return rec
        if first_raw is None:
            first_raw = content
            messages = base + [
                {"role": "assistant", "content": content},
                {"role": "user", "content": REPAIR_PROMPT},
            ]
    rec = _base_record(item, model)
    rec.update(verdict="parse_failed", is_constraint=None,
               encoding_faithful=None, confidence=0.0,
               reason="model output unparseable after one repair retry",
               parse_recovered=False, raw=(first_raw or "")[:400])
    rec["usage"] = {"prompt_tokens": ptok, "completion_tokens": ctok,
                    "total_tokens": ptok + ctok, "calls": calls}
    return rec


def _base_record(item, model):
    rec = {"id": item["id"], "model": model}
    if item.get("corruption_type"):
        rec["corruption_type"] = item["corruption_type"]
        rec["original_id"] = item.get("original_id", "")
    return rec


# ---------------------------------------------------------------------------
# Batch judging (one LLM call for many items; amortizes the system prompt)
# ---------------------------------------------------------------------------


def build_batch_user_message(items: list) -> str:
    """One user message carrying many items; each item's block is the same
    Register / CONSTRAINT / QUOTE / CONTEXT as the single path, headed by its
    id so the array response can be mapped back."""
    blocks = [f"You are given {len(items)} items to validate below."]
    for it in items:
        blocks += ["", f"===== ITEM id={it['id']} =====",
                   build_user_message(it)]
    return "\n".join(blocks)


def _empty_usage():
    return {"prompt_tokens": 0, "completion_tokens": 0,
            "total_tokens": 0, "calls": 0}


def judge_batch(client, items, model=MODEL, timeout=CALL_TIMEOUT_S,
                sleep=time.sleep):
    """Judge many items in ONE call. Returns (records_by_id, usage). Items the
    array response did not carry a salvageable judgment for are ABSENT from
    records_by_id — the caller re-judges those with judge_one."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_BATCH},
        {"role": "user", "content": build_batch_user_message(items)},
    ]
    content, pt, ct = _call_with_backoff(client, model, messages,
                                         timeout=timeout, sleep=sleep)
    by_id = {str(o["id"]): o for o in (extract_json_array(content) or [])
             if isinstance(o, dict) and "id" in o}
    records = {}
    for it in items:
        j = coerce_judgment(by_id.get(str(it["id"])))
        if j is not None:
            rec = _base_record(it, model)
            rec.update(j)
            records[it["id"]] = rec
    return records, {"prompt_tokens": pt, "completion_tokens": ct,
                     "total_tokens": pt + ct, "calls": 1}


# ---------------------------------------------------------------------------
# Run (per-item or batched)
# ---------------------------------------------------------------------------


def run_judge(items: list, client=None, model=MODEL,
              concurrency=DEFAULT_CONCURRENCY, timeout=CALL_TIMEOUT_S,
              quiet=False, sleep=time.sleep, batch_size=1):
    """Judge all items. ``batch_size`` > 1 sends that many items per LLM call
    (one shared system prompt), with a per-item judge_one fallback for any the
    batch response omits. Returns (records, totals); records sorted by id."""
    if client is None:
        client = make_client()
    t0 = time.monotonic()
    if batch_size and batch_size > 1:
        records = _run_batched(items, client, model, concurrency, timeout,
                               quiet, sleep, batch_size)
    else:
        records = _run_per_item(items, client, model, concurrency, timeout,
                                quiet, sleep)
    records.sort(key=lambda r: r["id"])
    totals = {
        "items": len(records),
        "prompt_tokens": sum(r["usage"]["prompt_tokens"] for r in records),
        "completion_tokens": sum(r["usage"]["completion_tokens"]
                                 for r in records),
        "calls": sum(r["usage"]["calls"] for r in records),
        "parse_recovered": sum(1 for r in records if r.get("parse_recovered")),
        "parse_failed": sum(1 for r in records
                            if r["verdict"] == "parse_failed"),
        "elapsed_s": round(time.monotonic() - t0, 1),
    }
    totals["total_tokens"] = (totals["prompt_tokens"]
                              + totals["completion_tokens"])
    return records, totals


def _run_per_item(items, client, model, concurrency, timeout, quiet, sleep):
    done_lock = threading.Lock()
    done = [0]

    def work(item):
        rec = judge_one(client, item, model=model, timeout=timeout,
                        sleep=sleep)
        with done_lock:
            done[0] += 1
            if not quiet and done[0] % 25 == 0:
                print(f"  judged {done[0]}/{len(items)}", file=sys.stderr)
        return rec

    if concurrency <= 1:
        return [work(it) for it in items]
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        return list(ex.map(work, items))


def _run_batched(items, client, model, concurrency, timeout, quiet, sleep,
                 batch_size):
    batches = [items[i:i + batch_size]
               for i in range(0, len(items), batch_size)]

    def work(batch):
        try:
            covered, usage = judge_batch(client, batch, model=model,
                                         timeout=timeout, sleep=sleep)
        except Exception:  # noqa: BLE001 — a dead batch falls back per item
            covered, usage = {}, _empty_usage()
        out = []
        for it in batch:
            rec = covered.get(it["id"])
            if rec is None:                       # missing/unparseable -> solo
                rec = judge_one(client, it, model=model, timeout=timeout,
                                sleep=sleep)
                rec["batched"] = False
            else:
                rec["parse_recovered"] = False
                rec["batched"] = True
                rec["usage"] = _empty_usage()
            out.append(rec)
        # attribute the one batch call's tokens to the batch (on out[0]);
        # per-record token counts aren't meaningful in batch mode, totals are.
        if out:
            u = out[0]["usage"]
            out[0]["usage"] = {
                "prompt_tokens": u["prompt_tokens"] + usage["prompt_tokens"],
                "completion_tokens": (u["completion_tokens"]
                                      + usage["completion_tokens"]),
                "total_tokens": u["total_tokens"] + usage["total_tokens"],
                "calls": u["calls"] + usage["calls"],
            }
        return out

    if concurrency <= 1:
        nested = [work(b) for b in batches]
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            nested = list(ex.map(work, batches))
    return [r for group in nested for r in group]
