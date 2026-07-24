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
(fenced or bare) with one per-item repair retry.

BLINDNESS (plan §7.2): judge verdicts are never written into
``verified_datasheet/`` — output lives under ``constraint_validator/out/``
(git-ignored). This module refuses out-paths under ``verified_datasheet/``.

CLI:
    python3 constraint_validator/judge.py \
        --anchors constraint_validator/out/anchors.jsonl \
        --csv verified_datasheet/constraints/stm.csv \
        --out constraint_validator/out/judgments.jsonl \
        [--limit 150 --sample-seed 7] [--ids ids.txt] \
        [--rows-jsonl corruptions.jsonl] [--concurrency 6]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
import threading
import time
from collections import defaultdict
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
- CONSTRAINT: the structured encoding the extractor produced for a target \
register (operation, target fields, preconditions, postconditions, severity),
- QUOTE: the verbatim datasheet sentence(s) the extractor cited as evidence,
- CONTEXT: the true surrounding text, derived programmatically from the manual.

Validate the encoding against ONLY the given QUOTE and CONTEXT. Do not rely \
on outside knowledge of any specific device; a detail the given text does not \
support is unsupported.

Answer three questions:
(a) is_constraint — does the quoted text state a genuine access or ordering \
REQUIREMENT that software must respect when accessing the target register \
(e.g. "write only when X", "set A before B", unlock/key sequences)? Purely \
descriptive behavior, status-flag semantics (how a flag is set or cleared, \
write-1-to-clear / write-0-to-clear acknowledge notes), reset-value notes, \
and validity or don't-care notes are NOT constraints.
(b) encoding_faithful — does the structured encoding match the text: target \
register, operation, the fields named, the polarities (set vs cleared), and \
any required values? The operation is "read" or "write" only: a datasheet \
sentence about "modifying" or "changing" a register means WRITING it, so \
"write" is the faithful encoding of such text -- there is no separate "modify" \
operation. A precondition may also carry `established_by` (hardware = the \
device brings the state about and software only observes it; software = the \
driver must establish it first) and, when software, `action_operation` naming \
HOW the driver does it -- "modify" (a read-modify-write that preserves the \
register's other bits) or "write" (composing a whole-register value); this is a \
method detail that need not appear in the quote, so flag it only if the text \
plainly contradicts it. A precondition or postcondition that contradicts, \
misstates, or is absent from the text makes the encoding unfaithful. Judge \
ONLY against the given text and context.
(c) verdict —
  "confirmed"      : genuine constraint AND the encoding is faithful.
  "encoding_error" : genuine constraint, but the encoding misstates it \
(wrong register, operation, field, polarity, or value; or a condition the \
text does not support).
  "not_constraint" : the quoted text is not an access/ordering requirement.
If is_constraint is false, use verdict "not_constraint" and set \
encoding_faithful to false.

Also report confidence (a number from 0 to 1) and a one-sentence reason.

Respond with a single JSON object and nothing else, keys exactly:
{"is_constraint": <bool>, "encoding_faithful": <bool>, \
"verdict": "<confirmed|encoding_error|not_constraint>", \
"confidence": <float>, "reason": "<one sentence>"}

Worked example 1 — a genuine mode-gate, faithfully encoded (target register \
usart1 brr):
CONSTRAINT: {"target_operation": "write", "target_fields": [], \
"preconditions": [{"register_name": "USART_CR1", "field_name": "UE", \
"required_state": "cleared"}], "postconditions": [], "severity": "error"}
QUOTE: This register can only be written when the USART is disabled (UE=0).
Correct response:
{"is_constraint": true, "encoding_faithful": true, "verdict": "confirmed", \
"confidence": 0.97, "reason": "The text requires the USART to be disabled \
(UE=0) before writing this register, exactly matching the encoded \
precondition."}

Worked example 2 — flag-acknowledge semantics, not a constraint (target \
register wwdg sr):
CONSTRAINT: {"target_operation": "write", "target_fields": [], \
"preconditions": [], "postconditions": [{"register_name": "WWDG_SR", \
"field_name": "EWIF", "required_state": "cleared"}], "severity": "error"}
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


def load_items(csv_path: str, anchors_path: str) -> list:
    """Join CSV rows with anchors by id; keep only judgeable tiers (exact,
    fuzzy) that carry a derived context. Returns flat item dicts sorted by
    id (deterministic)."""
    anchors = load_anchors(anchors_path)
    items = []
    for row in load_csv_rows(csv_path):
        anc = anchors.get(row.get("id", ""))
        if not anc or anc.get("tier") not in JUDGEABLE_TIERS:
            continue
        if not anc.get("context"):
            continue
        item = dict(row)
        item["context"] = anc["context"]
        item["tier"] = anc["tier"]
        items.append(item)
    items.sort(key=lambda it: it["id"])
    return items


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
# Prompt construction
# ---------------------------------------------------------------------------


def constraint_payload(item: dict) -> dict:
    """The structured encoding shown to the judge. Deliberately excludes
    ``consequence`` (free-text extractor commentary — showing it would let
    the judge detect corruptions via internal inconsistency instead of
    against the datasheet text)."""
    return {
        "target_operation": item.get("target_operation", ""),
        "target_fields": parse_json_list(item.get("target_fields")),
        "preconditions": parse_json_list(item.get("preconditions")),
        "postconditions": parse_json_list(item.get("postconditions")),
        "severity": item.get("severity", ""),
    }


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
# Sampling (deterministic, stratified across RMs and constraint shapes)
# ---------------------------------------------------------------------------


def constraint_shape(item: dict) -> tuple:
    """Coarse shape key: (operation, pre-count bucket, post-count bucket,
    carries an equals-value?). Used to stratify samples so mode-gates,
    value unlocks, postcondition rows etc. are all represented."""
    pre = parse_json_list(item.get("preconditions"))
    post = parse_json_list(item.get("postconditions"))
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
# Batch run
# ---------------------------------------------------------------------------


def run_judge(items: list, client=None, model=MODEL,
              concurrency=DEFAULT_CONCURRENCY, timeout=CALL_TIMEOUT_S,
              quiet=False, sleep=time.sleep):
    """Judge all items with a small thread pool. Returns (records, totals);
    records sorted by id (deterministic ordering regardless of completion
    order)."""
    if client is None:
        client = make_client()
    t0 = time.monotonic()
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
        records = [work(it) for it in items]
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            records = list(ex.map(work, items))
    records.sort(key=lambda r: r["id"])
    totals = {
        "items": len(records),
        "prompt_tokens": sum(r["usage"]["prompt_tokens"] for r in records),
        "completion_tokens": sum(r["usage"]["completion_tokens"]
                                 for r in records),
        "calls": sum(r["usage"]["calls"] for r in records),
        "parse_recovered": sum(1 for r in records if r["parse_recovered"]),
        "parse_failed": sum(1 for r in records
                            if r["verdict"] == "parse_failed"),
        "elapsed_s": round(time.monotonic() - t0, 1),
    }
    totals["total_tokens"] = (totals["prompt_tokens"]
                              + totals["completion_tokens"])
    return records, totals


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
    ap.add_argument("--anchors", default="constraint_validator/out/anchors.jsonl")
    ap.add_argument("--csv", default="verified_datasheet/constraints/stm.csv")
    ap.add_argument("--rows-jsonl", default=None,
                    help="judge pre-built rows (e.g. corruption.py output) "
                         "instead of the csv+anchors join")
    ap.add_argument("--out", default="constraint_validator/out/judgments.jsonl")
    ap.add_argument("--limit", type=int, default=None,
                    help="judge only a deterministic stratified sample of N")
    ap.add_argument("--sample-seed", default="0",
                    help="seed for the stratified sample (with --limit)")
    ap.add_argument("--ids", default=None,
                    help="file with one constraint id per line")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    ap.add_argument("--timeout", type=float, default=CALL_TIMEOUT_S)
    args = ap.parse_args(argv)

    assert_blind_output(args.out)
    if args.rows_jsonl:
        items = load_rows_jsonl(args.rows_jsonl)
    else:
        items = load_items(args.csv, args.anchors)
    if args.ids:
        with open(args.ids, encoding="utf-8") as f:
            wanted = {line.strip() for line in f if line.strip()}
        items = [it for it in items if it["id"] in wanted]
    if args.limit is not None:
        items = stratified_sample(items, args.limit, args.sample_seed)
    print(f"judging {len(items)} items with {args.model} "
          f"(concurrency {args.concurrency})", file=sys.stderr)

    records, totals = run_judge(items, model=args.model,
                                concurrency=args.concurrency,
                                timeout=args.timeout)
    write_judgments(records, args.out)
    print(json.dumps(totals, indent=2))
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
