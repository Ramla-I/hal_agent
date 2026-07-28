"""Offline tests for the LLM constraint-validator judge
(core/constraint_validator.py, plan §7.0 stage 1).

No network: every test injects a FAKE client. The real Groq client is never
constructed here (make_client is only called when client=None).

The calibration math (compute_scorecard, confidence stats, cost) is exercised
separately by tune_constraint_validator/tests/test_calibrate.py.
"""

import json
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import constraint_validator as judge  # noqa: E402


# ---------------------------------------------------------------------------
# Fake client
# ---------------------------------------------------------------------------

class FakeClient:
    """Mimics the OpenAI SDK surface used by the judge.

    ``script`` is a list whose entries are either response strings or
    Exception instances (raised in order). Use concurrency=1 for list-based
    scripts so pop order is deterministic.
    """

    def __init__(self, script):
        self._script = list(script)
        self.calls = []
        outer = self

        class _Completions:
            def create(self, **kw):
                outer.calls.append(kw)
                nxt = outer._script.pop(0)
                if isinstance(nxt, Exception):
                    raise nxt
                return SimpleNamespace(
                    choices=[SimpleNamespace(
                        message=SimpleNamespace(content=nxt))],
                    usage=SimpleNamespace(prompt_tokens=100,
                                          completion_tokens=20),
                )

        self.chat = SimpleNamespace(completions=_Completions())


VALID = json.dumps({
    "is_constraint": True, "encoding_faithful": True,
    "verdict": "confirmed", "confidence": 0.9,
    "reason": "matches the text.",
})


def make_item(id_="aaa111", rm="rm0091", **over):
    item = {
        "id": id_,
        "reference_manual": rm,
        "peripheral": "usart1",
        "register": "brr",
        "target_operation": "write",
        "target_fields": "[]",
        "preconditions": ('[{"register_name":"USART_CR1","field_name":"UE",'
                          '"required_state":"cleared"}]'),
        "postconditions": "[]",
        "severity": "error",
        "consequence": "must disable the USART first",
        "datasheet_text": ("This register can only be written when the "
                           "USART is disabled (UE=0)."),
        "context": ("27.8.4 USART baud rate register (USART_BRR)\n\n"
                    "This register can only be written when the USART is "
                    "disabled (UE=0). It may be automatically updated by "
                    "hardware in auto baud rate detection mode."),
        "tier": "exact",
    }
    item.update(over)
    return item


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def test_user_message_contains_quote_context_and_encoding():
    item = make_item()
    msg = judge.build_user_message(item)
    assert item["datasheet_text"] in msg
    assert "auto baud rate detection" in msg      # context made it in
    assert "USART_CR1" in msg and "cleared" in msg  # encoding made it in
    assert "rm0091" in msg and "usart1" in msg and "brr" in msg
    assert "QUOTE" in msg and "CONTEXT" in msg and "CONSTRAINT" in msg


def test_encoding_shown_to_judge_excludes_consequence():
    payload = judge.constraint_payload(make_item())
    assert set(payload) == {"target_operation", "target_fields",
                            "preconditions", "postconditions", "severity"}
    assert "consequence" not in json.dumps(payload)


def test_system_prompt_has_examples_and_exact_keys():
    sp = judge.SYSTEM_PROMPT
    for key in ("is_constraint", "encoding_faithful", "verdict",
                "confidence", "reason"):
        assert key in sp
    assert "UE=0" in sp                    # worked positive example
    assert "not_constraint" in sp          # worked negative example
    # terminology: the LLM validates (never "verify" as its role)
    assert "validating" in sp.lower()


# ---------------------------------------------------------------------------
# JSON recovery
# ---------------------------------------------------------------------------

def test_extract_json_clean():
    assert judge.extract_json_block(VALID)["verdict"] == "confirmed"


def test_extract_json_fenced():
    text = "Here is my answer:\n```json\n" + VALID + "\n```\nDone."
    assert judge.extract_json_block(text)["verdict"] == "confirmed"


def test_extract_json_prose_wrapped():
    text = "After careful review I conclude " + VALID + " which is final."
    obj = judge.extract_json_block(text)
    assert obj is not None and obj["confidence"] == 0.9


def test_extract_json_nested_braces_in_strings():
    inner = json.dumps({"verdict": "confirmed", "is_constraint": True,
                        "encoding_faithful": True, "confidence": 1.0,
                        "reason": 'field {UE} must be "cleared" (see {})'})
    assert judge.extract_json_block("x " + inner + " y") is not None


def test_extract_json_garbage_returns_none():
    assert judge.extract_json_block("no json here { broken") is None
    assert judge.extract_json_block("") is None


def test_coerce_normalizes_verdict_spelling():
    j = judge.coerce_judgment({"is_constraint": True,
                               "encoding_faithful": False,
                               "verdict": "Encoding Error",
                               "confidence": "0.8", "reason": "r"})
    assert j["verdict"] == "encoding_error"
    assert j["confidence"] == 0.8


def test_coerce_derives_verdict_from_booleans():
    j = judge.coerce_judgment({"is_constraint": False,
                               "encoding_faithful": False,
                               "verdict": "rejected",   # off-vocab
                               "confidence": 1.0, "reason": "r"})
    assert j["verdict"] == "not_constraint"
    assert judge.coerce_judgment({"verdict": "maybe"}) is None


def test_coerce_clamps_confidence():
    j = judge.coerce_judgment({"is_constraint": True,
                               "encoding_faithful": True,
                               "verdict": "confirmed",
                               "confidence": 1.7, "reason": "r"})
    assert j["confidence"] == 1.0


# ---------------------------------------------------------------------------
# judge_one: success / retry / parse failure
# ---------------------------------------------------------------------------

def test_judge_one_first_try():
    client = FakeClient([VALID])
    rec = judge.judge_one(client, make_item())
    assert rec["verdict"] == "confirmed"
    assert rec["parse_recovered"] is False
    assert rec["usage"] == {"prompt_tokens": 100, "completion_tokens": 20,
                            "total_tokens": 120, "calls": 1}
    assert rec["model"] == judge.MODEL
    # no structured-output mode is ever requested (Groq OSS hard-errors)
    assert "response_format" not in client.calls[0]
    assert client.calls[0]["temperature"] == 0


def test_judge_one_retry_recovers():
    client = FakeClient(["I think it is fine, thanks!", VALID])
    rec = judge.judge_one(client, make_item())
    assert rec["verdict"] == "confirmed"
    assert rec["parse_recovered"] is True
    assert rec["usage"]["calls"] == 2
    # the retry appends the bad reply + a repair instruction
    msgs = client.calls[1]["messages"]
    assert msgs[-1]["content"] == judge.REPAIR_PROMPT
    assert msgs[-2]["role"] == "assistant"


def test_judge_one_parse_failed_after_retry():
    client = FakeClient(["garbage one", "garbage two"])
    rec = judge.judge_one(client, make_item())
    assert rec["verdict"] == "parse_failed"
    assert rec["is_constraint"] is None
    assert rec["parse_recovered"] is False
    assert rec["usage"]["calls"] == 2
    assert rec["raw"].startswith("garbage one")


def test_backoff_retries_on_429_and_respects_retry_after():
    err = Exception("rate limited")
    err.status_code = 429
    err.response = SimpleNamespace(headers={"retry-after": "3"})
    client = FakeClient([err, VALID])
    sleeps = []
    rec = judge.judge_one(client, make_item(), sleep=sleeps.append)
    assert rec["verdict"] == "confirmed"
    assert sleeps == [3.0]
    assert len(client.calls) == 2


def test_backoff_does_not_retry_client_errors():
    err = Exception("bad request")
    err.status_code = 400
    client = FakeClient([err])
    with pytest.raises(Exception, match="bad request"):
        judge.judge_one(client, make_item(), sleep=lambda s: None)


# ---------------------------------------------------------------------------
# run_judge: ordering, totals, corruption passthrough
# ---------------------------------------------------------------------------

def test_run_judge_output_sorted_by_id_with_totals():
    items = [make_item("zzz"), make_item("aaa"), make_item("mmm")]
    client = FakeClient([VALID, VALID, VALID])
    recs, totals = judge.run_judge(items, client, concurrency=1, quiet=True)
    assert [r["id"] for r in recs] == ["aaa", "mmm", "zzz"]
    assert totals["items"] == 3
    assert totals["total_tokens"] == 3 * 120
    assert totals["parse_recovered"] == 0 and totals["parse_failed"] == 0


def test_run_judge_passes_through_corruption_fields():
    item = make_item("aaa-flip_polarity", corruption_type="flip_polarity",
                     original_id="aaa")
    recs, _ = judge.run_judge([item], FakeClient([VALID]), concurrency=1,
                              quiet=True)
    assert recs[0]["corruption_type"] == "flip_polarity"
    assert recs[0]["original_id"] == "aaa"


# ---------------------------------------------------------------------------
# Data loading / join / sampling
# ---------------------------------------------------------------------------

def _write_inputs(tmp_path, n_per_rm=4, rms=("rm0001", "rm0002")):
    import csv as csv_mod
    csv_path = tmp_path / "stm.csv"
    anchors_path = tmp_path / "anchors.jsonl"
    fields = ["id", "reference_manual", "run", "source_file", "peripheral",
              "register", "target_operation", "target_fields",
              "preconditions", "postconditions", "severity", "consequence",
              "datasheet_text", "dup_count", "lint_flags", "status", "note"]
    rows, anchors = [], []
    for rm in rms:
        for i in range(n_per_rm):
            rid = f"{rm}x{i:02d}"
            rows.append({
                "id": rid, "reference_manual": rm, "run": "1",
                "source_file": f"{rm}/1/per_reg", "peripheral": "per",
                "register": f"reg{i}", "target_operation": "write",
                "target_fields": "[]",
                "preconditions": ('[{"register_name":"PER_CR","field_name":'
                                  '"EN","required_state":"cleared"}]'),
                "postconditions": "[]", "severity": "error",
                "consequence": "c", "datasheet_text": f"quote {rid}",
                "dup_count": "1", "lint_flags": "", "status": "", "note": "",
            })
            tier = "unanchored" if i == n_per_rm - 1 else "exact"
            anc = {"id": rid, "tier": tier, "reference_manual": rm}
            if tier != "unanchored":
                anc["context"] = f"context for {rid}"
            anchors.append(anc)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv_mod.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(anchors_path, "w", encoding="utf-8") as f:
        for a in anchors:
            f.write(json.dumps(a) + "\n")
    return str(csv_path), str(anchors_path)


def test_load_items_joins_and_filters_unanchored(tmp_path):
    csv_path, anchors_path = _write_inputs(tmp_path)
    items = judge.load_items(csv_path, anchors_path)
    assert len(items) == 6                       # 8 rows - 2 unanchored
    assert all(it["tier"] == "exact" for it in items)
    assert all(it["context"].startswith("context for") for it in items)
    assert [it["id"] for it in items] == sorted(it["id"] for it in items)


def test_stratified_sample_deterministic_and_covers_rms(tmp_path):
    csv_path, anchors_path = _write_inputs(tmp_path, n_per_rm=6,
                                           rms=("rm1", "rm2", "rm3"))
    items = judge.load_items(csv_path, anchors_path)
    s1 = judge.stratified_sample(items, 6, seed="s")
    s2 = judge.stratified_sample(items, 6, seed="s")
    assert [i["id"] for i in s1] == [i["id"] for i in s2]
    assert len(s1) == 6
    assert {i["reference_manual"] for i in s1} == {"rm1", "rm2", "rm3"}
    s3 = judge.stratified_sample(items, 6, seed="other")
    assert isinstance(s3, list) and len(s3) == 6  # valid under any seed
    # n >= population returns everything
    assert len(judge.stratified_sample(items, 999, seed="s")) == len(items)


# ---------------------------------------------------------------------------
# Blindness rule
# ---------------------------------------------------------------------------

def test_refuses_output_under_verified_datasheet(tmp_path):
    bad = tmp_path / "verified_datasheet" / "constraints" / "j.jsonl"
    with pytest.raises(SystemExit, match="blindness"):
        judge.write_judgments([], str(bad))
    ok = tmp_path / "out" / "j.jsonl"
    judge.write_judgments([], str(ok))           # must not raise
    assert ok.exists()
