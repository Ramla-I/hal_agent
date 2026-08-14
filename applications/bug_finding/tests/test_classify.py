"""Unit tests for classify.mechanical_fp_reason (the deterministic generator-FP
screen). Imports config transitively, so run in Docker:

  scripts/docker_run.sh run applications/bug_finding/tests/test_classify.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from applications.bug_finding.classify import mechanical_fp_reason
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


if __name__ == "__main__":
    test_reset_value_width()
    test_existing_signatures_intact()
    print("classify tests OK")
