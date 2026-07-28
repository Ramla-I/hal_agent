"""Calibration math tests (plan §7.2): pure functions over synthetic
judgments — no network, no LLM. Exercises tune_constraint_validator/calibrate.py
(scorecard, confidence stats, cost estimate). The judge itself
(core/constraint_validator.py) is tested in tests/test_constraint_validator.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tune_constraint_validator import calibrate  # noqa: E402


def _rec(id_, verdict, conf=0.9, ctype=None, recovered=False):
    rec = {"id": id_, "verdict": verdict, "confidence": conf,
           "is_constraint": verdict != "not_constraint",
           "encoding_faithful": verdict == "confirmed",
           "reason": "r", "model": "m", "parse_recovered": recovered,
           "usage": {"prompt_tokens": 100, "completion_tokens": 10,
                     "total_tokens": 110, "calls": 1}}
    if ctype:
        rec["corruption_type"] = ctype
        rec["original_id"] = id_.rsplit("-", 1)[0]
    return rec


def test_scorecard_math():
    originals = [_rec("a", "confirmed"), _rec("b", "confirmed"),
                 _rec("c", "not_constraint", conf=0.6),
                 _rec("d", "encoding_error", recovered=True)]
    corr = [_rec("a-flip_polarity", "encoding_error", ctype="flip_polarity"),
            _rec("b-flip_polarity", "confirmed", ctype="flip_polarity"),
            _rec("c-swap_field", "encoding_error", ctype="swap_field"),
            _rec("d-swap_field", "not_constraint", ctype="swap_field")]
    sc = calibrate.compute_scorecard(originals, corr)
    assert sc["originals"]["n"] == 4
    assert sc["originals"]["flag_rate"] == 0.5
    assert "not a false-positive rate" in sc["originals"]["note"]
    assert sc["corruptions"]["detection_rate"] == 0.75
    pt = sc["corruptions"]["per_type"]
    assert pt["flip_polarity"]["detection_rate"] == 0.5
    assert pt["swap_field"]["detection_rate"] == 1.0   # any != confirmed
    assert sc["parse"]["recovered"] == 1
    assert sc["parse"]["failed"] == 0
    assert sc["usage"]["total_tokens"] == 8 * 110
    assert sc["usage"]["calls"] == 8


def test_scorecard_confidence_stats():
    recs = [_rec("a", "confirmed", conf=0.8), _rec("b", "confirmed", conf=1.0)]
    stats = calibrate._confidence_stats(recs)
    assert stats["n"] == 2
    assert stats["mean"] == 0.9
    assert stats["median"] == 0.9
    assert stats["histogram_decile"]["0.8"] == 1
    assert stats["histogram_decile"]["0.9"] == 1     # 1.0 folds into top bin
    assert calibrate._confidence_stats([]) == {"n": 0}


def test_cost_estimate():
    assert calibrate.estimated_cost_usd(1_000_000, 0) == calibrate.PRICE_IN_PER_M
    assert calibrate.estimated_cost_usd(0, 1_000_000) == calibrate.PRICE_OUT_PER_M
