"""Tests for the deterministic quote-anchoring leg (plan §7.1).

All fixtures are synthetic chunk trees written to tmp_path; the real chunked
datasheets are never touched.
"""

import csv
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from constraint_validator.quote_anchor import (  # noqa: E402
    FUZZY_THRESHOLD,
    normalize_text,
    normalize_with_offsets,
    paragraph_context,
    run,
)

RM = "rm9999"


# ---------------------------------------------------------------------------
# fixture helpers
# ---------------------------------------------------------------------------

def make_chunks(root, pages):
    """pages: {page_number: [chunk_text, ...]} -> chunk tree under root."""
    md = root / RM / "chunks" / "md"
    md.mkdir(parents=True)
    for page, chunks in pages.items():
        for ci, text in enumerate(chunks, start=1):
            (md / f"{RM}_p{page:03d}_c{ci:02d}.txt").write_text(text, encoding="utf-8")
    # non-chunk files that must be ignored by the loader
    (md / "chunks_index.csv").write_text("chunk_id,page\n", encoding="utf-8")
    (md / "metadata.json").write_text("{}", encoding="utf-8")
    return root


def make_csv(path, rows):
    """rows: list of (id, peripheral, register, quote)."""
    fields = ["id", "reference_manual", "peripheral", "register", "datasheet_text"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for rid, per, reg, quote in rows:
            w.writerow({"id": rid, "reference_manual": RM, "peripheral": per,
                        "register": reg, "datasheet_text": quote})
    return path


def anchor(tmp_path, pages, rows):
    chunks = make_chunks(tmp_path / "chunks", pages)
    csv_path = make_csv(tmp_path / "c.csv", rows)
    out = tmp_path / "out" / "anchors.jsonl"
    summary = run(str(csv_path), str(chunks), str(out), quiet=True)
    recs = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    return summary, {r["id"]: r for r in recs}


# ---------------------------------------------------------------------------
# normalization
# ---------------------------------------------------------------------------

NASTY = [
    "plain ascii text",
    "curly ‘quotes’ and “double” ones",
    "en–dash em—dash minus−sign non‑breaking",
    "soft­hyphen zero​width ﻿bom",
    "NBSP and narrow space",
    "**bold** _italic_ `code` and ADC_CR1 stays",
    "## Heading line\nbody text",
    "  #not a heading?  ##yes leading\ttext",
    "|table|cells|here|",
    "multi   space\t\ttabs\n\nnewlines",
    "ligature ﬁle Ω ohm µs",
    "trailing underscore_ _leading a_b mid",
    "UPPER Case MiXeD",
    "",
    "   \n\t  ",
    "a__b and __dunder__ and x_1_y",
]


@pytest.mark.parametrize("text", NASTY)
def test_normalizers_agree(text):
    fast = normalize_text(text)
    slow, offs = normalize_with_offsets(text)
    assert fast == slow
    assert len(offs) == len(slow)


def test_normalize_basics():
    assert normalize_text("It’s  “set”") == "it's \"set\""
    assert normalize_text("sample‑time") == "sample-time"
    # markdown stripped, register names preserved
    assert normalize_text("**ADC_CR1** must be _cleared_") == "adc_cr1 must be cleared"
    # heading hashes dropped, mid-line '#' kept
    assert normalize_text("## 9.2 GPIO\nsee #note") == "9.2 gpio see #note"


def test_offsets_map_back_to_original():
    orig = "Alpha **beta** ‘gamma’  delta"
    norm, offs = normalize_with_offsets(orig)
    start = norm.find("beta")
    assert start != -1
    o_start = offs[start]
    o_end = offs[start + len("beta") - 1] + 1
    assert orig[o_start:o_end] == "beta"


# ---------------------------------------------------------------------------
# paragraph context
# ---------------------------------------------------------------------------

def test_paragraph_context_neighbors():
    text = "Para A.\n\nPara B has the match.\n\nPara C.\n\nPara D."
    m = text.find("match")
    ctx = paragraph_context(text, m, m + 5)
    assert ctx == "Para A.\n\nPara B has the match.\n\nPara C."


def test_paragraph_context_cap():
    text = "P1.\n\n" + "x" * 3000 + " MATCH " + "y" * 3000 + "\n\nP3."
    m = text.find("MATCH")
    ctx = paragraph_context(text, m, m + 5, cap=200)
    assert len(ctx) == 200
    assert "MATCH" in ctx


# ---------------------------------------------------------------------------
# anchoring tiers
# ---------------------------------------------------------------------------

QUOTE = ("The DUALMOD bits must be kept at reset value before enabling "
         "the analog watchdog on the selected channel.")


def test_exact_match(tmp_path):
    pages = {5: ["Intro paragraph.\n\n" + QUOTE + "\n\nTrailing paragraph."]}
    _, recs = anchor(tmp_path, pages, [("r1", "adc1", "cr1", QUOTE)])
    r = recs["r1"]
    assert r["tier"] == "exact"
    assert r["ratio"] == 1.0
    assert r["pages"] == [5]
    assert r["occurrences"] == 1
    assert r["ambiguous"] is False
    assert QUOTE in r["context"]
    assert r["quote_len"] == len(QUOTE)


def test_exact_via_normalization(tmp_path):
    # page uses curly quotes, non-breaking hyphen, markdown bold, odd spacing
    page = ("Header.\n\nIt’s required that the sample‑time   bits of "
            "**ADC_SMPR1** remain\nunchanged during conversion.\n\nFooter.")
    quote = ('It\'s required that the sample-time bits of ADC_SMPR1 '
             'remain unchanged during conversion.')
    _, recs = anchor(tmp_path, {3: [page]}, [("r1", "adc1", "smpr1", quote)])
    r = recs["r1"]
    assert r["tier"] == "exact"
    # context is the ORIGINAL text: curly apostrophe and bold markers intact
    assert "It’s" in r["context"]
    assert "**ADC_SMPR1**" in r["context"]


def test_page_boundary_span(tmp_path):
    first = "Filler text for page two.\n\nThe TIMx_CR1 register must be configured"
    second = "before the counter is enabled by software.\n\nMore page three text."
    quote = ("The TIMx_CR1 register must be configured before the counter "
             "is enabled by software.")
    pages = {2: [first], 3: [second], 4: ["Unrelated page four."]}
    _, recs = anchor(tmp_path, pages, [("r1", "tim1", "cr1", quote)])
    r = recs["r1"]
    assert r["tier"] == "exact"
    assert r["pages"] == [2, 3]
    assert r["occurrences"] == 1
    assert "must be configured" in r["context"]


def test_fuzzy_one_word_changed(tmp_path):
    page_sentence = ("The PLL configuration bits must not be modified while "
                     "the PLL is enabled and used as the system clock source.")
    quote = ("The PLL configuration bits must not be changed while "
             "the PLL is enabled and used as the system clock source.")
    pages = {7: ["Intro.\n\n" + page_sentence + "\n\nOutro."]}
    _, recs = anchor(tmp_path, pages, [("r1", "rcc", "cfgr", quote)])
    r = recs["r1"]
    assert r["tier"] == "fuzzy"
    assert r["ratio"] >= FUZZY_THRESHOLD
    assert r["pages"] == [7]
    assert "modified" in r["context"]  # original page text, not the quote


def test_unanchored(tmp_path):
    pages = {1: ["Some real datasheet text about GPIO configuration registers."]}
    quote = "Completely unrelated nonsense that appears nowhere in any manual whatsoever."
    _, recs = anchor(tmp_path, pages, [("r1", "gpioa", "crl", quote)])
    r = recs["r1"]
    assert r["tier"] == "unanchored"
    assert r["ratio"] < FUZZY_THRESHOLD
    assert "context" not in r


BOILER = ("These bits must be kept at reset value to guarantee correct "
          "operation of the peripheral in all modes.")


def test_boilerplate_ambiguous(tmp_path):
    pages = {
        7: ["Something about SPI.\n\n" + BOILER],
        8: ["Something about UART.\n\n" + BOILER],
        9: ["Something about CAN.\n\n" + BOILER],
    }
    _, recs = anchor(tmp_path, pages, [("r1", "adc1", "cr2", BOILER)])
    r = recs["r1"]
    assert r["tier"] == "exact"
    assert r["occurrences"] == 3
    assert r["pages"] == [7, 8, 9]
    assert r["ambiguous"] is True  # no matched page mentions the register


def test_boilerplate_disambiguated_by_register_mention(tmp_path):
    pages = {
        7: ["Something about SPI.\n\n" + BOILER],
        8: ["The ADC_CR2 register description sits here.\n\n" + BOILER],
        9: ["Something about CAN.\n\n" + BOILER],
    }
    _, recs = anchor(tmp_path, pages, [("r1", "adc1", "cr2", BOILER)])
    r = recs["r1"]
    assert r["tier"] == "exact"
    assert r["occurrences"] == 3
    assert r["ambiguous"] is False  # exactly one page mentions ADC_CR2
    assert "ADC_CR2" in r["context"]  # context taken from the mentioning page


def test_chunk_overlap_merge(tmp_path):
    # two chunks of the SAME page overlap by > MIN_CHUNK_OVERLAP chars;
    # a quote spanning the overlap must match exactly once
    body = ("Configuration notes follow. The watchdog counter must be "
            "reloaded before the timeout expires or a reset is generated.")
    c1 = "Page intro paragraph.\n\n" + body[:80]
    c2 = body[40:] + "\n\nPage outro paragraph."
    quote = "The watchdog counter must be reloaded before the timeout expires"
    _, recs = anchor(tmp_path, {6: [c1, c2]}, [("r1", "iwdg", "kr", quote)])
    r = recs["r1"]
    assert r["tier"] == "exact"
    assert r["occurrences"] == 1
    assert r["pages"] == [6]


def test_context_is_original_with_neighbor_paragraphs(tmp_path):
    page = ("Before paragraph with ‘original’ punctuation.\n\n"
            "The **BKP** domain write protection must be disabled by setting "
            "the DBP bit.\n\n"
            "After paragraph mentioning PWR_CR.\n\n"
            "Far paragraph that must NOT appear.")
    quote = ("The BKP domain write protection must be disabled by setting "
             "the DBP bit.")
    _, recs = anchor(tmp_path, {12: [page]}, [("r1", "pwr", "cr", quote)])
    ctx = recs["r1"]["context"]
    assert "‘original’" in ctx          # previous paragraph, un-normalized
    assert "**BKP**" in ctx                       # match paragraph, un-normalized
    assert "After paragraph mentioning PWR_CR." in ctx
    assert "Far paragraph" not in ctx


# ---------------------------------------------------------------------------
# determinism / summary / CLI
# ---------------------------------------------------------------------------

def _standard_fixture(tmp_path):
    pages = {
        1: ["Intro paragraph.\n\n" + QUOTE + "\n\nTrailing."],
        2: ["Second page filler."],
    }
    rows = [
        ("r1", "adc1", "cr1", QUOTE),
        ("r2", "adc1", "cr1", "Nonsense that anchors nowhere in this document at all."),
    ]
    chunks = make_chunks(tmp_path / "chunks", pages)
    csv_path = make_csv(tmp_path / "c.csv", rows)
    return chunks, csv_path


def test_determinism_byte_identical(tmp_path):
    chunks, csv_path = _standard_fixture(tmp_path)
    out1 = tmp_path / "a.jsonl"
    out2 = tmp_path / "b.jsonl"
    run(str(csv_path), str(chunks), str(out1), quiet=True)
    run(str(csv_path), str(chunks), str(out2), quiet=True)
    assert out1.read_bytes() == out2.read_bytes()


def test_summary_counts(tmp_path):
    chunks, csv_path = _standard_fixture(tmp_path)
    out = tmp_path / "a.jsonl"
    s = run(str(csv_path), str(chunks), str(out), quiet=True)
    assert s["csv_rows"] == 2
    assert s["attempted"] == 2
    assert s["tiers"].get("exact") == 1
    assert s["tiers"].get("unanchored") == 1
    assert s["rms_with_chunks"] == [RM]
    assert s["rms_without_chunks"] == []
    assert s["per_rm"][RM]["rows"] == 2
    assert s["context_warnings"] == 0


def test_missing_chunks_reported(tmp_path):
    chunks = tmp_path / "chunks"
    chunks.mkdir()
    csv_path = make_csv(tmp_path / "c.csv", [("r1", "adc1", "cr1", QUOTE)])
    out = tmp_path / "a.jsonl"
    s = run(str(csv_path), str(chunks), str(out), quiet=True)
    assert s["attempted"] == 0
    assert s["skipped_no_chunks"] == 1
    assert s["rms_without_chunks"] == [RM]


def test_cli(tmp_path):
    chunks, csv_path = _standard_fixture(tmp_path)
    out = tmp_path / "cli.jsonl"
    script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "quote_anchor.py")
    proc = subprocess.run(
        [sys.executable, script, "--csv", str(csv_path), "--chunks", str(chunks),
         "--out", str(out), "--rm", RM],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "exact" in proc.stdout
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    # JSON keys sorted for deterministic bytes
    rec = json.loads(lines[0])
    assert list(rec) == sorted(rec)
