"""Tests for the verified-constraints datasheet builder + annotator
(verified_datasheet/build_constraints_datasheet.py, annotate_constraints.py).

Covers: dedup across runs/instances (dup_count), id stability, annotation
preservation across rebuilds, lint-flag derivation, the annotator's pure
row-selection (round-robin / --rm / --flagged-only / --limit), and a --stats
smoke test via subprocess against the real generated CSV.
"""
import csv
import json
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_VD = os.path.dirname(_HERE)  # verified_datasheet/
sys.path.insert(0, _VD)

import annotate_constraints as ann  # noqa: E402
import build_constraints_datasheet as bcd  # noqa: E402

REAL_CSV = os.path.join(_VD, "constraints", "stm.csv")


# ---------------------------------------------------------------------------
# Synthetic corpus helpers
# ---------------------------------------------------------------------------

def make_constraint(**overrides):
    c = {
        "target_register": "USART_CR1",
        "target_fields": ["UE"],
        "target_operation": "write",
        "preconditions": [
            {"register_name": "USART_CR1", "field_name": "UE",
             "required_state": "cleared"},
        ],
        "postconditions": [],
        "severity": "error",
        "consequence": "Write is ignored while the USART is enabled.",
        "datasheet_text": "This bit can only be written when the USART is "
                          "disabled (UE=0).",
    }
    c.update(overrides)
    return c


def write_reg(rundir, filename, constraints):
    os.makedirs(rundir, exist_ok=True)
    with open(os.path.join(rundir, filename), "w", encoding="utf-8") as f:
        json.dump({"datasheet_register_abbreviation": filename.upper(),
                   "access_constraints": constraints}, f)


@pytest.fixture
def corpus(tmp_path):
    """Two RMs, one with two runs; instance + cross-run duplicates; every lint flag."""
    root = tmp_path / "corpus"

    # rm0001: constraint A occurs 3x (usart1 + usart2 in run 1, usart1 in run 2)
    write_reg(str(root / "rm0001" / "1"), "usart1_cr1", [make_constraint()])
    write_reg(str(root / "rm0001" / "1"), "usart2_cr1", [make_constraint()])
    write_reg(str(root / "rm0001" / "2"), "usart1_cr1", [make_constraint()])

    # rm0001: w1c postcondition pathology (many_postconditions + w1c_suspect)
    write_reg(str(root / "rm0001" / "1"), "rcc_csr", [make_constraint(
        target_register="RCC_CSR",
        target_operation="write",
        preconditions=[],
        postconditions=[
            {"register_name": "RCC_CSR", "field_name": f,
             "required_state": "cleared"}
            for f in ("PINRSTF", "PORRSTF", "SFTRSTF", "IWDGRSTF")
        ],
        datasheet_text="These bits are cleared by writing a '1' to the RMVF bit.",
    )])

    # rm0001: %s placeholder file (placeholder_source)
    write_reg(str(root / "rm0001" / "1"), "tim3_ccr%s", [make_constraint(
        target_register="TIM3_CCR%s",
        datasheet_text="CCR can be written at any time only when OCxPE is cleared to 0.",
    )])

    # rm0002: off-vocab operation and off-vocab state
    write_reg(str(root / "rm0002" / "1"), "rtc_wpr", [make_constraint(
        target_register="RTC_WPR",
        target_operation="read/write",
        preconditions=[{"register_name": "RTC_WPR", "field_name": "KEY",
                        "required_state": "equals:0xCA then 0x53"}],
        datasheet_text="Write 0xCA then 0x53 into the RTC_WPR register.",
    )])

    # rm0002: read op + cleared-by-read text + no conditions
    write_reg(str(root / "rm0002" / "1"), "dsi_isr", [make_constraint(
        target_register="DSI_ISR",
        target_operation="read",
        preconditions=[],
        postconditions=[],
        datasheet_text="This flag is cleared by a read of the DSI_ISR register.",
    )])

    # noise that must be ignored: subdirs + bookkeeping files
    vdir = root / "rm0001" / "1" / "validator"
    vdir.mkdir(parents=True)
    (vdir / "classification.csv").write_text("verdict\nTP\n")
    (root / "rm0001" / "1" / "run_manifest.json").write_text("{}")
    (root / "rm0001" / "1" / "usage.csv").write_text("tokens\n1\n")

    return str(root)


def build(corpus_root, out_path):
    bcd.main([corpus_root, "--out", str(out_path)])
    return bcd.read_rows(str(out_path))


def by_register(rows):
    return {(r["reference_manual"], r["peripheral"], r["register"]): r for r in rows}


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def test_dedup_across_runs_and_instances(corpus, tmp_path):
    rows = build(corpus, tmp_path / "out.csv")
    # A collapses usart1(run1) + usart2(run1) + usart1(run2) into one row
    usart = [r for r in rows if r["target_operation"] == "write"
             and "USART" in r["datasheet_text"]]
    assert len(usart) == 1
    row = usart[0]
    assert row["dup_count"] == "3"
    assert row["source_file"] == "rm0001/1/usart1_cr1"  # first seen
    assert row["run"] == "1"
    assert row["peripheral"] == "usart1"
    assert row["register"] == "cr1"
    # total: A + rcc_csr + tim3 + rtc_wpr + dsi_isr
    assert len(rows) == 5


def test_columns_and_json_cells(corpus, tmp_path):
    out = tmp_path / "out.csv"
    build(corpus, out)
    with open(out, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == bcd.COLUMNS
    rows = bcd.read_rows(str(out))
    row = by_register(rows)[("rm0001", "usart1", "cr1")]
    assert json.loads(row["target_fields"]) == ["UE"]
    assert json.loads(row["preconditions"]) == [
        {"register_name": "USART_CR1", "field_name": "UE",
         "required_state": "cleared"}]
    assert json.loads(row["postconditions"]) == []
    # blindness: only the spec'd columns exist — no verdict column can hide
    assert "verdict" not in header


def test_id_stability(corpus, tmp_path):
    rows1 = build(corpus, tmp_path / "a.csv")
    rows2 = build(corpus, tmp_path / "b.csv")
    assert {r["id"] for r in rows1} == {r["id"] for r in rows2}
    assert all(len(r["id"]) == 12 for r in rows1)

    # id is insensitive to dict key order and condition list order
    ac = make_constraint(preconditions=[
        {"register_name": "A", "field_name": "X", "required_state": "set"},
        {"register_name": "B", "field_name": "Y", "required_state": "cleared"},
    ])
    ac_permuted = json.loads(json.dumps(ac))
    ac_permuted["preconditions"].reverse()
    assert (bcd.constraint_id(bcd.dedup_key("rm0001", ac))
            == bcd.constraint_id(bcd.dedup_key("rm0001", ac_permuted)))
    # ...but sensitive to the reference manual and the quote
    assert (bcd.constraint_id(bcd.dedup_key("rm0002", ac))
            != bcd.constraint_id(bcd.dedup_key("rm0001", ac)))


def test_rebuild_preserves_annotations(corpus, tmp_path):
    out = tmp_path / "out.csv"
    rows = build(corpus, out)
    target = by_register(rows)[("rm0001", "usart1", "cr1")]
    target["status"], target["note"] = "confirmed", "checked against rm0001"
    other = by_register(rows)[("rm0002", "rtc", "wpr")]
    other["status"] = "encoding_error"
    bcd.save_atomic(str(out), rows)

    # corpus grows: one more duplicate of A (dup_count must refresh) + a new file
    write_reg(os.path.join(corpus, "rm0001", "2"), "usart3_cr1", [make_constraint()])
    write_reg(os.path.join(corpus, "rm0002", "1"), "spi1_cr1", [make_constraint(
        target_register="SPI_CR1",
        preconditions=[{"register_name": "SPI_CR1", "field_name": "SPE",
                        "required_state": "cleared"}],
        datasheet_text="This bit should be written only when SPI is disabled.",
    )])

    rows2 = build(corpus, out)
    assert len(rows2) == len(rows) + 1  # new row added, nothing lost
    again = by_register(rows2)[("rm0001", "usart1", "cr1")]
    assert again["status"] == "confirmed"           # never clobbered
    assert again["note"] == "checked against rm0001"
    assert again["dup_count"] == "4"                # machine column refreshed
    assert by_register(rows2)[("rm0002", "rtc", "wpr")]["status"] == "encoding_error"
    new = by_register(rows2)[("rm0002", "spi1", "cr1")]
    assert new["status"] == "" and new["note"] == ""


def test_rebuild_keeps_orphaned_rows(corpus, tmp_path):
    out = tmp_path / "out.csv"
    rows = build(corpus, out)
    # simulate a row whose constraint vanished from the corpus
    os.remove(os.path.join(corpus, "rm0002", "1", "dsi_isr"))
    rows2 = build(corpus, out)
    assert len(rows2) == len(rows)
    assert ("rm0002", "dsi", "isr") in by_register(rows2)


def test_lint_flags(corpus, tmp_path):
    rows = by_register(build(corpus, tmp_path / "out.csv"))

    def flags(key):
        return set(f for f in rows[key]["lint_flags"].split(";") if f)

    assert flags(("rm0001", "usart1", "cr1")) == set()
    assert flags(("rm0001", "rcc", "csr")) == {"many_postconditions", "w1c_suspect"}
    assert "placeholder_source" in flags(("rm0001", "tim3", "ccr%s"))
    assert {"off_vocab_op", "off_vocab_state"} <= flags(("rm0002", "rtc", "wpr"))
    assert flags(("rm0002", "dsi", "isr")) == {"empty_conditions", "read_clear_suspect"}


def test_state_vocabulary():
    ok = ["cleared", "set", "equals:0x5555", "equals:0b01", "equals:7", "equals: 0xCA"]
    bad = ["", "unchanged", "equals:output", "equals:0xCA then 0x53",
           "equals:0b01|0b10", "not cleared", "equals:>=0x300"]
    assert all(bcd._state_ok(s) for s in ok)
    assert not any(bcd._state_ok(s) for s in bad)


def test_ignores_bookkeeping_and_subdirs(corpus):
    # validator/, run_manifest.json, usage.csv must never contribute constraints
    seen = [(rm, run, fn) for rm, run, fn, _ in bcd.iter_corpus(corpus)]
    names = {fn for _, _, fn in seen}
    assert "run_manifest.json" not in names
    assert "usage.csv" not in names
    assert all("classification" not in fn for fn in names)


# ---------------------------------------------------------------------------
# Annotator row selection (pure function — no TTY)
# ---------------------------------------------------------------------------

def _row(rm, i, status="", flags=""):
    return {"id": f"{rm}-{i}", "reference_manual": rm,
            "status": status, "lint_flags": flags}


def test_select_round_robin_order():
    rows = ([_row("rm0008", i) for i in range(3)]
            + [_row("rm0091", i) for i in range(2)]
            + [_row("rm0505", 0)]
            + [_row("rm0008", 9, status="confirmed")])  # annotated: excluded
    picked = ann.select_pending(rows)
    assert [r["reference_manual"] for r in picked] == [
        "rm0008", "rm0091", "rm0505",   # cycle 1: one per RM, sorted order
        "rm0008", "rm0091",             # cycle 2
        "rm0008",                       # cycle 3
    ]
    # within an RM, CSV order is preserved
    assert [r["id"] for r in picked if r["reference_manual"] == "rm0008"] == [
        "rm0008-0", "rm0008-1", "rm0008-2"]


def test_select_filters_and_limit():
    rows = [_row("rm0008", 0, flags="w1c_suspect"), _row("rm0008", 1),
            _row("rm0091", 0), _row("rm0091", 1, flags="off_vocab_op"),
            _row("rm0091", 2, status="unsure", flags="off_vocab_op")]
    assert [r["id"] for r in ann.select_pending(rows, rm="rm0091")] == [
        "rm0091-0", "rm0091-1"]
    assert [r["id"] for r in ann.select_pending(rows, flagged_only=True)] == [
        "rm0008-0", "rm0091-1"]
    assert len(ann.select_pending(rows, limit=2)) == 2
    assert ann.select_pending([]) == []


def test_select_returns_row_references():
    rows = [_row("rm0008", 0)]
    picked = ann.select_pending(rows)
    picked[0]["status"] = "confirmed"
    assert rows[0]["status"] == "confirmed"  # annotator mutates the same dicts


# ---------------------------------------------------------------------------
# --stats smoke test on the real generated CSV
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not os.path.exists(REAL_CSV),
                    reason="constraints/stm.csv not built yet")
def test_stats_smoke_on_real_csv():
    r = subprocess.run(
        [sys.executable, os.path.join(_VD, "annotate_constraints.py"),
         "--stats", "--csv", REAL_CSV],
        capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    assert "overall:" in r.stdout
    assert "remaining:" in r.stdout
    assert "rm0008" in r.stdout and "rm0505" in r.stdout  # every RM listed
