"""End-to-end test for s0's Step-6 constraint-validation phase (Phase 2): the
generator run -> in-memory items (ALL grammar-v2 kinds) -> quote anchoring ->
LLM judge -> judgments.jsonl flow, with NO intermediate CSV and NO network (the
judge call is monkeypatched).

Guards the two things Phase 2 changed: (1) every kind reaches the judge (the old
state_gate-only filter is gone), and (2) items carry the native constraint
object + target_registers, anchored in memory.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import s0_run_full_analysis as s0  # noqa: E402  (adds core/ to sys.path)
import constraint_validator as cv            # noqa: E402  (module s0's phase imports)

RM = "rm9999"


def _make_chunks(chunks_root, page_text):
    md = chunks_root / RM / "chunks" / "md"
    md.mkdir(parents=True)
    (md / f"{RM}_p001_c01.txt").write_text(page_text, encoding="utf-8")
    (md / "chunks_index.csv").write_text("chunk_id,page\n", encoding="utf-8")
    (md / "metadata.json").write_text("{}", encoding="utf-8")


# one constraint of three different kinds, each with a distinct cited quote
Q_SG = "The STOP bit can only be set while the I2C bus is not busy."
Q_SEQ = "Write key A then key B to the write protection register to unlock it."
Q_RE = "Reading the status register clears the RXNE flag."

CONSTRAINTS = {
    "I2C1_cr1": {"kind": "state_gate", "severity": "error", "consequence": "x",
                 "datasheet_text": Q_SG, "target_register": "I2C1_CR1",
                 "target_fields": ["STOP"], "target_operation": "write",
                 "preconditions": [{"register": "I2C1_SR2", "field": "BUSY",
                                    "state": "cleared"}],
                 "postconditions": []},
    "RTC_wpr": {"kind": "sequence", "severity": "error", "consequence": "x",
                "datasheet_text": Q_SEQ,
                "steps": [{"register": "RTC_WPR", "operation": "write", "value": 202},
                          {"register": "RTC_WPR", "operation": "write", "value": 83}]},
    "USART1_sr": {"kind": "read_effect", "severity": "warning", "consequence": "x",
                  "datasheet_text": Q_RE, "read_register": "USART1_SR",
                  "effects": [{"field": "RXNE", "becomes": "cleared"}]},
}


def _make_run(run_dir):
    run_dir.mkdir()
    for fn, constraint in CONSTRAINTS.items():
        (run_dir / fn).write_text(
            json.dumps({"datasheet_register_abbreviation": fn.upper(),
                        "access_constraints_v2": [constraint]}),
            encoding="utf-8")


def test_phase_processes_all_kinds_in_memory(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    _make_run(run_dir)
    chunks_root = tmp_path / "chunks"
    _make_chunks(chunks_root, " ".join([Q_SG, Q_SEQ, Q_RE]))

    captured = {}

    def fake_run_judge(items, client=None, model=None, quiet=True,
                       batch_size=1, **kw):
        captured["items"] = items
        captured["batch_size"] = batch_size
        records = [{
            "id": it["id"], "verdict": "confirmed", "is_constraint": True,
            "encoding_faithful": True, "confidence": 0.9, "reason": "r",
            "parse_recovered": False,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                      "total_tokens": 0, "calls": 0},
        } for it in items]
        return records, {"items": len(records)}

    # the phase does `from constraint_validator import run_judge, make_client`
    # -> patch the module attributes it looks up (referenced_registers stays real)
    monkeypatch.setattr(cv, "run_judge", fake_run_judge)
    monkeypatch.setattr(cv, "make_client", lambda: object())

    summary = s0.run_constraint_validation_phase(
        run_dir=str(run_dir), reference_manual=RM,
        chunks_root=str(chunks_root), batch_size=4)

    # (1) every kind was extracted and reached the judge — no state_gate filter
    assert summary["extracted"] == 3
    kinds = {it["constraint"]["kind"] for it in captured["items"]}
    assert kinds == {"state_gate", "sequence", "read_effect"}
    assert captured["batch_size"] == 4                # batch wired through

    # (2) items carry the native object + target_registers, anchored in memory
    for it in captured["items"]:
        assert isinstance(it["constraint"], dict) and "kind" in it["constraint"]
        assert it["target_registers"]                 # non-empty
        assert it["tier"] in ("exact", "fuzzy") and it.get("context")
    seq = next(it for it in captured["items"]
               if it["constraint"]["kind"] == "sequence")
    assert "RTC_WPR" in seq["target_registers"]       # from the steps

    # all three anchored + confirmed; artifacts written; NO constraints.csv
    assert summary["anchored"] == 3 and summary["confirmed"] == 3
    out_dir = run_dir / "constraint_validation"
    assert (out_dir / "anchors.jsonl").exists()
    assert len((out_dir / "judgments.jsonl").read_text().splitlines()) == 3
    assert (out_dir / "summary.json").exists()
    assert not (out_dir / "constraints.csv").exists()   # in-memory, no CSV


def test_phase_defaults_to_unbatched(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    _make_run(run_dir)
    chunks_root = tmp_path / "chunks"
    _make_chunks(chunks_root, " ".join([Q_SG, Q_SEQ, Q_RE]))

    captured = {}

    def fake_run_judge(items, client=None, model=None, quiet=True,
                       batch_size=1, **kw):
        captured["batch_size"] = batch_size
        return ([{"id": it["id"], "verdict": "confirmed", "is_constraint": True,
                  "encoding_faithful": True, "confidence": 0.9, "reason": "r",
                  "parse_recovered": False,
                  "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                            "total_tokens": 0, "calls": 0}} for it in items],
                {"items": len(items)})

    monkeypatch.setattr(cv, "run_judge", fake_run_judge)
    monkeypatch.setattr(cv, "make_client", lambda: object())

    s0.run_constraint_validation_phase(
        run_dir=str(run_dir), reference_manual=RM, chunks_root=str(chunks_root))
    assert captured["batch_size"] == 1                # per-item by default
