"""Unit tests for classify.mechanical_fp_reason (the deterministic generator-FP
screen). Imports config transitively, so run in Docker:

  scripts/docker_run.sh run applications/bug_finding/tests/test_classify.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from applications.bug_finding.classify import (
    mechanical_fp_reason,
    _peripheral_address_shift_classes,
)
from applications.bug_finding.models import Diff


def _d(**kw) -> Diff:
    base = dict(peripheral="P", register="R", key="reset_value",
                svd_value="0x0", generator_value="0x1")
    base.update(kw)
    return Diff(**base)


def test_reset_value_width():
    # value needs more bits than the register is wide -> generator misread (FP).
    r = mechanical_fp_reason(_d(svd_value="0xC0", generator_value="0xC00000", reg_size=16), {})
    assert r and "exceeds register width" in r, r
    # value fits -> real candidate, not screened.
    assert mechanical_fp_reason(_d(svd_value="0xC0", generator_value="0xC0", reg_size=16), {}) is None
    # genuinely wide value in a 32-bit register -> NOT a false positive.
    assert mechanical_fp_reason(_d(generator_value="0xFFFFFFFF", reg_size=32), {}) is None
    # unknown width -> can't judge, don't screen.
    assert mechanical_fp_reason(_d(generator_value="0xC00000", reg_size=None), {}) is None
    print("  reset_value width OK")


def test_existing_signatures_intact():
    # not-found placeholder
    assert mechanical_fp_reason(_d(generator_value=""), {}) is not None
    # absolute address where an offset is expected
    r = mechanical_fp_reason(_d(key="address_offset", generator_value="0x40010000"), {})
    assert r and "absolute address" in r, r
    # a normal small offset is a real candidate
    assert mechanical_fp_reason(_d(key="address_offset", svd_value="0x0", generator_value="0x4"), {}) is None
    print("  existing signatures OK")


def _addr(peripheral, register, svd, gen) -> Diff:
    return _d(peripheral=peripheral, register=register, key="address_offset",
              svd_value=svd, generator_value=gen)


def test_peripheral_uniform_address_shift():
    # STM32 BKP-style: the SVD bakes +4 into baseAddress, so every register's
    # offset differs from the datasheet's by the same constant. Absolute address
    # matches -> representation difference, not a bug.
    bkp = [_addr("BKP", f"DR{i}", "0x0", "0x4") for i in range(1, 11)]
    bkp += [_addr("BKP", "CR", "0x2C", "0x30"),
            _addr("BKP", "CSR", "0x30", "0x34"),
            _addr("BKP", "RTCCR", "0x28", "0x2C")]
    cls = _peripheral_address_shift_classes(bkp)
    assert cls == {"BKP": 4}, cls
    r = mechanical_fp_reason(bkp[0], {}, cls)
    assert r and "uniform address shift" in r and "+0x4" in r, r

    # a single shifted register is an isolated bug, not a peripheral convention
    one = [_addr("TIM2", "ARR", "0x2C", "0x30")]
    assert _peripheral_address_shift_classes(one) == {}
    assert mechanical_fp_reason(one[0], {}, {}) is None

    # mixed deltas within a peripheral -> real bugs, left as candidates
    mixed = [_addr("X", "A", "0x0", "0x4"), _addr("X", "B", "0x4", "0x8"),
             _addr("X", "C", "0x8", "0x10")]  # +4, +4, +8
    assert _peripheral_address_shift_classes(mixed) == {}

    # negative uniform shift is handled too
    neg = [_addr("Y", f"R{i}", "0x10", "0xC") for i in range(3)]
    cls_neg = _peripheral_address_shift_classes(neg)
    assert cls_neg == {"Y": -4}, cls_neg
    assert "-0x4" in (mechanical_fp_reason(neg[0], {}, cls_neg) or "")
    print("  peripheral uniform address shift OK")


if __name__ == "__main__":
    test_reset_value_width()
    test_existing_signatures_intact()
    test_peripheral_uniform_address_shift()
    print("classify tests OK")
