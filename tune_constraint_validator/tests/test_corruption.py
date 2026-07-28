"""Offline tests for the corruption generator (plan §7.2, β leg).

Verify the realism invariants: sibling fields are real names, values stay
in-range (bit-length <= the original literal's width), operations stay in
vocabulary, retargets come from the same RM — and that every corruption
changes exactly the targeted part of the encoding while quote+context stay
byte-identical to the original.
"""

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tune_constraint_validator import corruption  # noqa: E402


def rng():
    return random.Random("test")


def base_row(**over):
    row = {
        "id": "abc123",
        "reference_manual": "rm0001",
        "peripheral": "usart1",
        "register": "brr",
        "target_operation": "write",
        "target_fields": "[]",
        "preconditions": ('[{"register_name":"USART_CR1","field_name":"UE",'
                          '"required_state":"cleared"}]'),
        "postconditions": "[]",
        "severity": "error",
        "consequence": "c",
        "datasheet_text": "quote text",
        "dup_count": "1", "lint_flags": "", "status": "", "note": "",
        "run": "1", "source_file": "rm0001/1/usart1_brr",
    }
    row.update(over)
    return row


def indexes_for(rows):
    return corruption.build_indexes(rows)


EMPTY_IDX = {"siblings": {}, "register_pool": {}}


# ---------------------------------------------------------------------------
# flip_polarity
# ---------------------------------------------------------------------------

def test_flip_polarity_flips_one_precondition_only():
    parsed = corruption.parse_row(base_row())
    got = corruption.corrupt_flip_polarity(parsed, rng(), EMPTY_IDX)
    assert got is not None
    assert got["preconditions"][0]["required_state"] == "set"
    # nothing else moved
    assert got["target_operation"] == "write"
    assert got["register"] == "brr"
    assert got["preconditions"][0]["field_name"] == "UE"


def test_flip_polarity_inapplicable_without_cleared_or_set():
    row = base_row(preconditions='[{"register_name":"IWDG_KR",'
                                 '"field_name":"KEY",'
                                 '"required_state":"equals:0x5555"}]')
    assert corruption.corrupt_flip_polarity(
        corruption.parse_row(row), rng(), EMPTY_IDX) is None


# ---------------------------------------------------------------------------
# swap_field
# ---------------------------------------------------------------------------

def test_swap_field_uses_same_row_sibling():
    row = base_row(preconditions=(
        '[{"register_name":"I2C_CR1","field_name":"STOP",'
        '"required_state":"cleared"},'
        '{"register_name":"I2C_CR1","field_name":"START",'
        '"required_state":"cleared"}]'))
    got = corruption.corrupt_swap_field(corruption.parse_row(row), rng(),
                                        EMPTY_IDX)
    assert got is not None
    assert got["preconditions"][0]["field_name"] == "START"  # only sibling
    assert got["preconditions"][1]["field_name"] == "START"  # untouched


def test_swap_field_uses_mined_same_register_sibling():
    # another CSV row names PE and PEC on the same register in the same RM
    other = base_row(id="other1", preconditions=(
        '[{"register_name":"USART_CR1","field_name":"PCE",'
        '"required_state":"set"}]'))
    idx = indexes_for([base_row(), other])
    got = corruption.corrupt_swap_field(corruption.parse_row(base_row()),
                                        rng(), idx)
    assert got is not None
    assert got["preconditions"][0]["field_name"] == "PCE"   # mined, real name


def test_swap_field_never_picks_bracket_variant_of_same_field():
    # pool contains only UE[0] which is the same field as UE -> inapplicable
    other = base_row(id="other1", preconditions=(
        '[{"register_name":"USART_CR1","field_name":"UE[0]",'
        '"required_state":"set"}]'))
    idx = indexes_for([base_row(), other])
    assert corruption.corrupt_swap_field(corruption.parse_row(base_row()),
                                         rng(), idx) is None


def test_swap_field_sibling_pool_respects_rm_boundary():
    other_rm = base_row(id="other1", reference_manual="rm0999",
                        preconditions=('[{"register_name":"USART_CR1",'
                                       '"field_name":"TE",'
                                       '"required_state":"set"}]'))
    idx = indexes_for([base_row(), other_rm])
    # TE lives in rm0999, not rm0001 -> no sibling available
    assert corruption.corrupt_swap_field(corruption.parse_row(base_row()),
                                         rng(), idx) is None


# ---------------------------------------------------------------------------
# change_operation
# ---------------------------------------------------------------------------

def test_change_operation_write_becomes_read_never_modify():
    # write->modify is entailed-true (a modify performs a write), so it is
    # banned as a corruption; write's only falsifying swap is read.
    got = corruption.corrupt_change_operation(
        corruption.parse_row(base_row()), rng(), EMPTY_IDX)
    assert got["target_operation"] == "read"


def test_change_operation_never_produces_modify():
    # No direction may corrupt TOWARD modify: rules over all writes or all
    # reads entail the modify claim, so such swaps are true statements.
    for op in ("write", "read", "modify"):
        got = corruption.corrupt_change_operation(
            corruption.parse_row(base_row(target_operation=op)), rng(),
            EMPTY_IDX)
        assert got["target_operation"] != "modify"
        assert got["target_operation"] != op


def test_change_operation_read_and_modify_become_write():
    for op in ("read", "modify"):
        got = corruption.corrupt_change_operation(
            corruption.parse_row(base_row(target_operation=op)), rng(),
            EMPTY_IDX)
        assert got["target_operation"] == "write"


def test_change_operation_skips_off_vocab_ops():
    for op in ("read/write", "any", "access", ""):
        assert corruption.corrupt_change_operation(
            corruption.parse_row(base_row(target_operation=op)), rng(),
            EMPTY_IDX) is None


# ---------------------------------------------------------------------------
# perturb_value
# ---------------------------------------------------------------------------

def _perturb(state):
    row = base_row(preconditions=json.dumps([{
        "register_name": "IWDG_KR", "field_name": "KEY",
        "required_state": state}]))
    got = corruption.corrupt_perturb_value(corruption.parse_row(row), rng(),
                                           EMPTY_IDX)
    return None if got is None else got["preconditions"][0]["required_state"]


def test_perturb_binary_stays_in_width_and_changes():
    out = _perturb("equals:0b0010")
    assert out in ("equals:0b0001", "equals:0b0011")


def test_perturb_binary_at_max_goes_down():
    assert _perturb("equals:0b11") == "equals:0b10"   # 3 is max for 2 bits


def test_perturb_zero_goes_up():
    assert _perturb("equals:0b00") == "equals:0b01"
    assert _perturb("equals:0") == "equals:1"


def test_perturb_hex_preserves_style_and_width():
    out = _perturb("equals:0x5555")
    assert out in ("equals:0x5554", "equals:0x5556")


def test_perturb_new_value_bit_length_never_exceeds_original_width():
    for state, width in (("equals:0b0010", 4), ("equals:0x5555", 16),
                         ("equals:1", 1)):
        out = _perturb(state)
        lit = out.split(":", 1)[1]
        val = int(lit, 0)
        assert val.bit_length() <= width
        assert lit != state.split(":", 1)[1]


def test_perturb_inapplicable_without_simple_equals():
    assert _perturb("cleared") is None
    assert _perturb("equals:0xCA then 0x53") is None
    assert _perturb("equals:output") is None


# ---------------------------------------------------------------------------
# retarget_register
# ---------------------------------------------------------------------------

def test_retarget_picks_different_register_from_same_rm():
    rows = [base_row(),
            base_row(id="r2", peripheral="spi1", register="cr1"),
            base_row(id="r3", reference_manual="rm0999",
                     peripheral="tim1", register="ccr1")]
    idx = indexes_for(rows)
    got = corruption.corrupt_retarget_register(
        corruption.parse_row(base_row()), rng(), idx)
    assert (got["peripheral"], got["register"]) == ("spi1", "cr1")
    # conditions untouched
    assert got["preconditions"][0]["field_name"] == "UE"


def test_retarget_inapplicable_when_rm_has_no_other_register():
    idx = indexes_for([base_row()])
    assert corruption.corrupt_retarget_register(
        corruption.parse_row(base_row()), rng(), idx) is None


# ---------------------------------------------------------------------------
# generate(): determinism, provenance, quote/context preservation
# ---------------------------------------------------------------------------

def corpus(n_per_rm=6, rms=("rm0001", "rm0002")):
    """Rows rich enough for every corruption type, plus anchors."""
    rows, anchors = [], {}
    for rm in rms:
        for i in range(n_per_rm):
            rid = f"{rm}r{i:02d}"
            rows.append(base_row(
                id=rid, reference_manual=rm,
                peripheral=f"per{i % 3}", register=f"reg{i}",
                preconditions=json.dumps([
                    {"register_name": "PER_CR", "field_name": f"EN{i}",
                     "required_state": "cleared"},
                    {"register_name": "PER_KR", "field_name": "KEY",
                     "required_state": "equals:0b0101"}]),
                datasheet_text=f"quote {rid}"))
            anchors[rid] = {"id": rid, "tier": "exact",
                            "context": f"context {rid}",
                            "reference_manual": rm}
    return rows, anchors


def test_generate_deterministic_and_counts():
    rows, anchors = corpus()
    out1 = corruption.generate(rows, anchors, per_type=3, seed="s1")
    out2 = corruption.generate(rows, anchors, per_type=3, seed="s1")
    assert out1 == out2
    by_type = {}
    for rec in out1:
        by_type.setdefault(rec["corruption_type"], []).append(rec)
    assert set(by_type) == set(corruption.CORRUPTION_TYPES)
    assert all(len(v) == 3 for v in by_type.values())
    out3 = corruption.generate(rows, anchors, per_type=3, seed="s2")
    assert [r["id"] for r in out3] != [r["id"] for r in out1] or out3 != out1


def test_generate_skips_unanchored_rows():
    rows, anchors = corpus()
    anchors = {k: v for k, v in anchors.items() if k.endswith("00")}
    out = corruption.generate(rows, anchors, per_type=99, seed="s")
    used = {rec["original_id"] for rec in out}
    assert used <= set(anchors)


def test_generate_records_keep_original_quote_and_context():
    rows, anchors = corpus()
    out = corruption.generate(rows, anchors, per_type=2, seed="s")
    assert out, "expected corruptions"
    for rec in out:
        oid = rec["original_id"]
        assert rec["id"] == f"{oid}-{rec['corruption_type']}"
        assert rec["datasheet_text"] == f"quote {oid}"
        assert rec["context"] == f"context {oid}"
        assert rec["tier"] == "exact"


def test_generate_changes_exactly_the_targeted_encoding_part():
    rows, anchors = corpus()
    originals = {r["id"]: corruption.parse_row(r) for r in rows}
    out = corruption.generate(rows, anchors, per_type=2, seed="s")
    for rec in out:
        orig = originals[rec["original_id"]]
        ctype = rec["corruption_type"]
        pre_changed = (json.loads(rec["preconditions"])
                       != orig["preconditions"])
        op_changed = rec["target_operation"] != orig["target_operation"]
        reg_changed = ((rec["peripheral"], rec["register"])
                       != (orig["peripheral"], orig["register"]))
        post_changed = (json.loads(rec["postconditions"])
                        != orig["postconditions"])
        tf_changed = (json.loads(rec["target_fields"])
                      != orig["target_fields"])
        if ctype in ("flip_polarity", "swap_field", "perturb_value"):
            assert pre_changed and not (op_changed or reg_changed)
        elif ctype == "change_operation":
            assert op_changed and not (pre_changed or reg_changed)
        elif ctype == "retarget_register":
            assert reg_changed and not (pre_changed or op_changed)
        assert not post_changed and not tf_changed
        # exactly one condition differs for precondition corruptions
        if ctype in ("flip_polarity", "swap_field", "perturb_value"):
            new_pre = json.loads(rec["preconditions"])
            diffs = [1 for a, b in zip(new_pre, orig["preconditions"])
                     if a != b]
            assert len(new_pre) == len(orig["preconditions"])
            assert sum(diffs) == 1


def test_generate_row_content_independent_of_per_type():
    """Per-row RNG is keyed by (seed, type, id): the same original corrupted
    the same way regardless of how many others are requested."""
    rows, anchors = corpus()
    small = corruption.generate(rows, anchors, per_type=1, seed="s")
    big = corruption.generate(rows, anchors, per_type=4, seed="s")
    big_by_id = {r["id"]: r for r in big}
    for rec in small:
        assert big_by_id.get(rec["id"]) == rec
