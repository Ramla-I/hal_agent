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

from constraint_validator import quote_anchor  # noqa: E402
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


# ---------------------------------------------------------------------------
# Target verification (2026-07-17): self-referential quotes must be vouched
# for by their anchor LOCATION; named quotes verify textually.
# ---------------------------------------------------------------------------

def _matcher_for(tmp_path, text, page=10):
    make_chunks(tmp_path, {page: [text]})
    return quote_anchor.RMMatcher(RM, str(tmp_path / RM / "chunks" / "md"))


def test_target_verification_named_in_text(tmp_path):
    m = _matcher_for(tmp_path,
        "The I2C_CR1 register must not be written while STOP is set.")
    rec = quote_anchor.anchor_row(m, {
        "datasheet_text": "The I2C_CR1 register must not be written while STOP is set.",
        "register": "CR1", "peripheral": "i2c1"})
    assert rec["tier"] == "exact"
    assert rec["self_referential"] is False   # CR1 appears in the quote


def test_target_verification_self_referential_located(tmp_path):
    m = _matcher_for(tmp_path,
        "Section: I2C_CR1 control register. "
        "This register can be written only when the flag is cleared.")
    rec = quote_anchor.anchor_row(m, {
        "datasheet_text": "This register can be written only when the flag is cleared.",
        "register": "CR1", "peripheral": "i2c1"})
    assert rec["tier"] == "exact"
    assert rec["self_referential"] is True
    assert rec["target_located"] is True      # page names I2C_CR1


def test_target_verification_retarget_caught(tmp_path):
    # The calibration blind spot: a nameless quote anchored in ANOTHER
    # register's section, while the constraint claims a different target.
    m = _matcher_for(tmp_path,
        "Section: SPI_TXCRCR. "
        "This register can be written only when the flag is cleared.")
    rec = quote_anchor.anchor_row(m, {
        "datasheet_text": "This register can be written only when the flag is cleared.",
        "register": "WUTR", "peripheral": "rtc"})   # retargeted claim
    assert rec["tier"] == "exact"
    assert rec["self_referential"] is True
    assert rec["target_located"] is False     # page never mentions RTC/WUTR


def test_target_verification_family_placeholder_names_register(tmp_path):
    # "AFIO_EXTICRX" is the manual's own family placeholder for EXTICR1..4 —
    # it NAMES the register; the location requirement must not fire.
    m = _matcher_for(tmp_path,
        "To read/write the AFIO_EVCR, AFIO_MAPR and AFIO_EXTICRX registers, "
        "the AFIO clock should first be enabled.")
    rec = quote_anchor.anchor_row(m, {
        "datasheet_text": "To read/write the AFIO_EVCR, AFIO_MAPR and "
                          "AFIO_EXTICRX registers, the AFIO clock should "
                          "first be enabled.",
        "register": "EXTICR1", "peripheral": "afio"})
    assert rec["tier"] == "exact"
    assert rec["self_referential"] is False


def test_target_verification_section_header_on_previous_page(tmp_path):
    # Register sections span pages: the header naming the register sits on
    # the page before the quoted note (the USART_CR2 case, rm0008 p823/824).
    make_chunks(tmp_path, {
        20: ["Section 27.6.5: USART_CR2 control register 2. Bits above."],
        21: ["These 3 bits should not be written while the transmitter is enabled."],
    })
    m = quote_anchor.RMMatcher(RM, str(tmp_path / RM / "chunks" / "md"))
    rec = quote_anchor.anchor_row(m, {
        "datasheet_text": "These 3 bits should not be written while the transmitter is enabled.",
        "register": "CR2", "peripheral": "usart1"})
    assert rec["tier"] == "exact"
    assert rec["self_referential"] is True
    assert rec["target_located"] is True      # named on the neighbor page


def test_target_verification_compound_name_tail(tmp_path):
    # Run-file names are peripheral-scoped compounds; the manual writes a
    # prefixed tail: register "dma_dmardlar" appears as "ETH_DMARDLAR".
    m = _matcher_for(tmp_path,
        "The ETH_DMARDLAR register description. "
        "This register can be written only when transmission has stopped.")
    rec = quote_anchor.anchor_row(m, {
        "datasheet_text": "This register can be written only when transmission has stopped.",
        "register": "dma_dmardlar", "peripheral": "ethernet"})
    assert rec["tier"] == "exact"
    assert rec["self_referential"] is True
    assert rec["target_located"] is True


def test_target_verification_dim_template_placeholder(tmp_path):
    # SVD dim-templates keep a literal "%s" ("alrm%sr" covers ALRMAR/ALRMBR);
    # the manual never prints it. Strip the placeholder and let one-edit
    # tolerance absorb the concrete letter (Ramla, 2026-07-17).
    m = _matcher_for(tmp_path,
        "Section: RTC_ALRMAR alarm A register. "
        "This register can be written only when ALRAWF is set.")
    rec = quote_anchor.anchor_row(m, {
        "datasheet_text": "This register can be written only when ALRAWF is set.",
        "register": "alrm%sr", "peripheral": "rtc"})
    assert rec["tier"] == "exact"
    assert rec["self_referential"] is True
    assert rec["target_located"] is True      # alrmr ~ alrmar (one edit)


def test_target_verification_one_edit_family_placeholder(tmp_path):
    # The manual's family placeholder sits one edit from the SVD's concrete
    # name: register cpar4 is described under "DMA_CPARx".
    m = _matcher_for(tmp_path,
        "Section: DMA_CPARx channel x peripheral address register. "
        "This register must not be written when the channel is enabled.")
    rec = quote_anchor.anchor_row(m, {
        "datasheet_text": "This register must not be written when the channel is enabled.",
        "register": "cpar4", "peripheral": "dma1"})
    assert rec["tier"] == "exact"
    assert rec["self_referential"] is True
    assert rec["target_located"] is True      # cpar4 ~ cparx via dma_cparx


def test_target_verification_one_edit_in_peripheral_half(tmp_path):
    # Placeholder in the PERIPHERAL half: gpioa's idr appears as "GPIOx_IDR";
    # the compound candidate gpioa_idr is one edit from the page's token.
    m = _matcher_for(tmp_path,
        "Section: GPIOx_IDR port input data register. "
        "This register is read-only and can be accessed in word mode only.")
    rec = quote_anchor.anchor_row(m, {
        "datasheet_text": "This register is read-only and can be accessed in word mode only.",
        "register": "idr", "peripheral": "gpioa"})
    assert rec["tier"] == "exact"
    assert rec["self_referential"] is True
    assert rec["target_located"] is True


def test_target_verification_short_names_never_fuzzed(tmp_path):
    # One-edit tolerance must not let a short register name drift into
    # ordinary prose ("calr" is one edit from "call"): short names still
    # require an exact mention.
    m = _matcher_for(tmp_path,
        "Software should call the initialization routine. "
        "This register can be written only in initialization mode.")
    rec = quote_anchor.anchor_row(m, {
        "datasheet_text": "This register can be written only in initialization mode.",
        "register": "calr", "peripheral": "rtc"})
    assert rec["tier"] == "exact"
    assert rec["self_referential"] is True
    assert rec["target_located"] is False


def test_target_verification_retarget_still_caught_with_tolerance(tmp_path):
    # The corruption class the location gate exists for must survive the
    # tolerance: a nameless quote in a distant register's section still
    # fails to locate a retargeted claim.
    m = _matcher_for(tmp_path,
        "Section: SPI_TXCRCR CRC register. "
        "This register can be written only when the peripheral is disabled.")
    rec = quote_anchor.anchor_row(m, {
        "datasheet_text": "This register can be written only when the peripheral is disabled.",
        "register": "wutr", "peripheral": "rtc"})
    assert rec["tier"] == "exact"
    assert rec["self_referential"] is True
    assert rec["target_located"] is False


def test_within_one_edit():
    f = quote_anchor._within_one_edit
    assert f("alrmr", "alrmar")      # insertion
    assert f("cpar4", "cparx")       # substitution
    assert f("usartcr2", "uartcr2")  # deletion
    assert f("abcd", "abcd")         # equal
    assert not f("alrmr", "alarm")   # distance 3
    assert not f("cpar4", "cmar5")   # two substitutions
    assert not f("ab", "abcd")       # length gap 2
