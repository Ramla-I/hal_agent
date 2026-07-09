"""Offline tests for the derivedFrom expansion logic (verified_datasheet/expand_derived.py).

`expand_rows` is the single implementation shared by the CLI (`expand_derived.py`) and the
Validator benchmark harness (`optimization_validator/kfold.py`), so it is unit-tested here
against synthetic rows plus a real-CSV smoke.

No network / no pandas. Run in the project container:
    scripts/docker_run.sh run -m verified_datasheet.tests.test_offline
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from verified_datasheet.expand_derived import expand_rows

VERIFIED = "verified_datasheet/stm/rm0041_stm32f100.csv"
FIELDS = ["peripheral", "register", "field_name", "key", "correct_value", "status",
          "derived_from", "set_method"]

_failures = []


def check(cond, msg):
    if not cond:
        _failures.append(msg)
        print(f"  FAIL: {msg}")
    else:
        print(f"  ok:   {msg}")


def _row(peripheral, register="", field_name="", key="", value="", derived_from="",
         set_method="human-verified", status="verified"):
    return {"peripheral": peripheral, "register": register, "field_name": field_name,
            "key": key, "correct_value": value, "status": status,
            "derived_from": derived_from, "set_method": set_method}


def _proto(name):
    """A prototype peripheral: its base_address row plus two field rows."""
    return [
        _row(name, key="base_address", value="0x40010800"),
        _row(name, register="CRL", field_name="MODE0", key="bit_offset", value="0"),
        _row(name, register="CRL", field_name="MODE0", key="bit_width", value="2"),
    ]


def test_basic_expansion():
    print("\n== basic derived expansion ==")
    rows = _proto("GPIOA") + [
        # derived GPIOB: only its own base_address + a derived marker row
        _row("GPIOB", key="base_address", value="0x40010C00", derived_from="gpioa"),
        _row("GPIOB", derived_from="gpioa", status="derived", set_method="derived"),
    ]
    out, info = expand_rows(rows, FIELDS)

    check(info["proto_of"] == {"gpiob": "gpioa"}, f"proto_of maps derived->prototype ({info['proto_of']})")
    check(info["n_expanded"] == 2, f"expanded both prototype layout rows (got {info['n_expanded']})")
    check(info["missing_prototypes"] == [], f"no missing prototypes ({info['missing_prototypes']})")

    gpiob = [r for r in out if r["peripheral"] == "GPIOB"]
    base = [r for r in gpiob if r["key"] == "base_address"]
    layout = [r for r in gpiob if r["register"] == "CRL"]
    check(len(base) == 1 and base[0]["correct_value"] == "0x40010C00",
          "derived peripheral keeps its OWN base_address (not the prototype's)")
    check(len(layout) == 2, f"prototype's 2 layout rows copied under the derived peripheral ({len(layout)})")
    check(all(r["peripheral"] == "GPIOB" for r in layout),
          "copied rows carry the derived peripheral's original-case name (GPIOB, not gpiob)")
    check(all(r["set_method"] == "derived-expanded" for r in layout),
          "copied rows are tagged set_method=derived-expanded")
    check(all(r["derived_from"] == "gpioa" for r in layout),
          "copied rows record the prototype in derived_from")
    check([r["key"] for r in layout] == ["bit_offset", "bit_width"],
          "copied rows inherit the prototype's field values/order")


def test_no_derived_is_noop():
    print("\n== no derived peripherals -> unchanged ==")
    rows = _proto("GPIOA")
    out, info = expand_rows(rows, FIELDS)
    check(info["n_expanded"] == 0 and info["proto_of"] == {}, "nothing expanded when no derived_from")
    check(out == rows, "rows returned unchanged")


def test_missing_column_is_noop():
    print("\n== a missing prototype is reported, not fabricated ==")
    rows = [
        _row("GPIOB", key="base_address", value="0x40010C00", derived_from="gpioa"),
    ]  # prototype GPIOA is absent from the CSV
    out, info = expand_rows(rows, FIELDS)
    check(info["missing_prototypes"] == ["gpioa"], f"absent prototype flagged ({info['missing_prototypes']})")
    check(info["n_expanded"] == 0, "no layout rows fabricated for a missing prototype")
    check(len([r for r in out if r["peripheral"] == "GPIOB"]) == 1,
          "derived peripheral keeps only its own base row when prototype is missing")


def test_multiple_derived_from_one_prototype():
    print("\n== several peripherals derive from one prototype ==")
    rows = _proto("TIM2") + [
        _row("TIM3", key="base_address", value="0x40000400", derived_from="tim2"),
        _row("TIM4", key="base_address", value="0x40000800", derived_from="tim2"),
    ]
    out, info = expand_rows(rows, FIELDS)
    check(info["proto_of"] == {"tim3": "tim2", "tim4": "tim2"}, f"both mapped ({info['proto_of']})")
    check(info["n_expanded"] == 4, f"2 prototype rows x 2 derived peripherals ({info['n_expanded']})")
    for p, addr in (("TIM3", "0x40000400"), ("TIM4", "0x40000800")):
        got = [r for r in out if r["peripheral"] == p]
        base = [r for r in got if r["key"] == "base_address"]
        layout = [r for r in got if r["register"] == "CRL"]
        check(len(base) == 1 and base[0]["correct_value"] == addr, f"{p} keeps its own base {addr}")
        check(len(layout) == 2, f"{p} inherits the 2 prototype layout rows")


def test_derived_marker_dedup():
    print("\n== duplicate compact rows for a derived peripheral expand once ==")
    rows = _proto("GPIOA") + [
        _row("GPIOB", derived_from="gpioa", status="derived", set_method="derived"),  # marker first
        _row("GPIOB", key="base_address", value="0x40010C00", derived_from="gpioa"),   # then base
        _row("GPIOB", derived_from="gpioa", status="derived"),                          # extra dup marker
    ]
    out, info = expand_rows(rows, FIELDS)
    gpiob = [r for r in out if r["peripheral"] == "GPIOB"]
    base = [r for r in gpiob if r["key"] == "base_address"]
    layout = [r for r in gpiob if r["register"] == "CRL"]
    check(len(base) == 1, "base row emitted exactly once regardless of marker/base ordering")
    check(len(layout) == 2, "layout copied once (no duplication from extra marker rows)")
    check(info["n_expanded"] == 2, f"n_expanded counts one copy of the layout ({info['n_expanded']})")


def test_row_count_accounting():
    print("\n== output row count is fully accounted for ==")
    proto = _proto("GPIOA")                       # 3 rows, not derived
    derived = [_row("GPIOB", key="base_address", value="0x40010C00", derived_from="gpioa"),
               _row("GPIOB", derived_from="gpioa", status="derived")]
    rows = proto + derived
    out, info = expand_rows(rows, FIELDS)
    # out = prototype rows (unchanged) + derived's own base (1) + copied layout (n_expanded)
    expected = len(proto) + 1 + info["n_expanded"]
    check(len(out) == expected, f"len(out)={len(out)} == prototype({len(proto)}) + base(1) + copies({info['n_expanded']})")


def test_real_csv_smoke():
    print("\n== real rm0041 CSV expansion smoke ==")
    if not os.path.exists(VERIFIED):
        check(False, f"missing {VERIFIED} (run from repo root)")
        return
    with open(VERIFIED, newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    out, info = expand_rows(rows, fields)

    check(len(info["proto_of"]) > 0, f"CSV has derived peripherals ({len(info['proto_of'])})")
    check(info["missing_prototypes"] == [], f"every prototype present in the CSV ({info['missing_prototypes']})")
    check(info["n_expanded"] > 0 and len(out) > len(rows),
          f"expansion adds rows ({len(rows)} -> {len(out)}, +{info['n_expanded']})")

    def layout_keys(rows_, periph):
        return sorted((r["register"], r.get("field_name", ""), r["key"])
                      for r in rows_ if (r.get("peripheral") or "").lower() == periph
                      and str(r.get("register") or "").strip())

    # Every derived peripheral now carries the SAME register/field layout as its prototype.
    ok = True
    for derived, proto in info["proto_of"].items():
        if layout_keys(out, derived) != layout_keys(out, proto):
            ok = False
            print(f"     mismatch: {derived} layout != prototype {proto}")
            break
    check(ok, "each derived peripheral inherits its prototype's full register/field layout")


if __name__ == "__main__":
    test_basic_expansion()
    test_no_derived_is_noop()
    test_missing_column_is_noop()
    test_multiple_derived_from_one_prototype()
    test_derived_marker_dedup()
    test_row_count_accounting()
    test_real_csv_smoke()
    print("\n" + ("=" * 50))
    if _failures:
        print(f"{len(_failures)} FAILURE(S):")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL EXPAND-DERIVED TESTS PASSED")
