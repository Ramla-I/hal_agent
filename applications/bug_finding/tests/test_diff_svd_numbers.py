"""SVD numbers may be decimal (``<resetValue>0``), hex, or ``#``binary — all must parse to int,
or a decimal SVD value never equals the generator's int and every such register becomes a
spurious diff (the lpc55s16 case: 357 fake reset-value 'bugs')."""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from applications.bug_finding.diff import _svd_int, compute_diffs, parse_svd_registers

_SVD = """<?xml version="1.0"?>
<device><name>T</name><peripherals><peripheral><name>P</name><baseAddress>0x40000000</baseAddress>
<registers>
  <register><name>DEC</name><addressOffset>16</addressOffset><size>32</size><resetValue>0</resetValue></register>
  <register><name>HEX</name><addressOffset>0x4</addressOffset><size>32</size><resetValue>0x1F</resetValue></register>
  <register><name>BIN</name><addressOffset>0x8</addressOffset><size>32</size><resetValue>#101</resetValue></register>
</registers></peripheral></peripherals></device>"""


def test_svd_int_forms():
    assert [_svd_int(x) for x in ("0", "4096", "0x1F", "0X10", "#101", " 0x0 ")] == [0, 4096, 31, 16, 5, 0]
    assert _svd_int("#1x0x") == "#1x0x"  # don't-care bits: left as-is


def test_decimal_reset_is_not_a_spurious_diff(tmp_path):
    svd = tmp_path / "t.svd"
    svd.write_text(_SVD)
    regs = parse_svd_registers(str(svd))
    p = regs["p"]
    assert (p["dec"]["reset_value"], p["dec"]["address_offset"]) == (0, 16)
    assert (p["hex"]["reset_value"], p["bin"]["reset_value"]) == (31, 5)
    gen = {"p": {name: {**r, "fields": []} for name, r in p.items()}}
    gen["p"]["dec"]["reset_value"] = "0x0"   # generator writes hex; must still match decimal 0
    diffs = [d for d in compute_diffs(regs, gen) if d.key in ("reset_value", "address_offset")]
    assert diffs == []
