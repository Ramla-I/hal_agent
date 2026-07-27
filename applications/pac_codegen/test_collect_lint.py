"""
Stage-0 lint tests (roadmap step E, plan section 7.0): exact dedup,
SVD-metadata lint, and structural flags in collect_constraints.

Covers, on top of tests/test_grammar.py's lift/collection coverage:

- exact dedup within one register file (per-bit fan-out: identical except
  target_fields), keep-first with duplicate_of back-reference, run-level
  dedup stats, and the duplicate_across_instances cross-instance lint flag;
- value-vs-field-width rejects (field bitWidth, msb/lsb, bitRange, and
  whole-register size);
- write/modify constraints on SVD read-only targets (register- and
  field-granular) rejected as FPs by construction;
- w1c reclassification: modifiedWriteValues oneToClear/... postconditions
  and status-register readAction postconditions rejected with
  w1c_flag_semantics (not the generic observed-state reason);
- read_side_effect flag for read gates touching readAction registers;
- self_defeating_read_gate rejects (with and without SVD, per expanded
  operation, hardware established_by only);
- cross_peripheral lint flag (name-prefix heuristic + SVD refinement,
  usart/uart and gpioa/gpiob family compatibility);
- --svd-dir accepting a single .svd file (the corpus-sweep shape).

Run: .venv/bin/python -m pytest applications/pac_codegen/test_collect_lint.py
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from applications.pac_codegen.collect_constraints import (
    _families_compatible,
    _load_svd_index,
    collect_constraints,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _register_json(abbrev, constraints, subfields=()):
    return {
        "datasheet_register_abbreviation": abbrev,
        "address_offset": "0x00",
        "reset_value": "0x0000",
        "size": 32,
        "subfields": list(subfields),
        "access_constraints_v2": constraints,
    }


def _constraint(target, op="write", pre=(), post=(), text="quote", fields=(),
                severity="error", consequence="c"):
    return {
        "kind": "state_gate",
        "target_register": target, "target_fields": list(fields),
        "target_operation": op,
        "preconditions": list(pre), "postconditions": list(post),
        "severity": severity, "consequence": consequence,
        "datasheet_text": text,
    }


def _cond(register, field, state="cleared", **extra):
    # grammar-v2 FieldCondition, translating the few retired v1 spellings used
    # by existing call sites (evidence_kind -> established_by; "equals:<v>" ->
    # state "equals" + values; empty field -> whole_register).
    if "evidence_kind" in extra:
        extra["established_by"] = {"software_action": "software",
                                   "observed_state": "hardware"}.get(
                                       extra.pop("evidence_kind"), "hardware")
    values = []
    if isinstance(state, str) and state.startswith("equals:"):
        values = [int(state.split(":", 1)[1], 0)]
        state = "equals"
    cond = {"register": register, "field": field, "state": state}
    if not field:
        cond["whole_register"] = True
    if values:
        cond["values"] = values
    cond.update(extra)
    return cond


LINT_SVD = """<?xml version="1.0" encoding="utf-8"?>
<device>
  <name>LINTDEV</name>
  <size>0x20</size>
  <peripherals>
    <peripheral>
      <name>RCC</name>
      <registers>
        <register><name>CSR</name>
          <fields>
            <field><name>RMVF</name><bitOffset>24</bitOffset><bitWidth>1</bitWidth>
              <modifiedWriteValues>oneToClear</modifiedWriteValues></field>
            <field><name>LSION</name><bitOffset>0</bitOffset><bitWidth>1</bitWidth></field>
          </fields>
        </register>
        <register><name>CR</name>
          <fields>
            <field><name>HSEON</name><bitOffset>16</bitOffset><bitWidth>1</bitWidth></field>
          </fields>
        </register>
      </registers>
    </peripheral>
    <peripheral>
      <name>USART1</name>
      <registers>
        <register><name>SR</name><access>read-only</access>
          <fields>
            <field><name>TC</name><bitOffset>6</bitOffset><bitWidth>1</bitWidth></field>
          </fields>
        </register>
        <register><name>DR</name><readAction>clear</readAction>
          <fields>
            <field><name>DATA</name><bitOffset>0</bitOffset><bitWidth>9</bitWidth></field>
          </fields>
        </register>
        <register><name>CR1</name>
          <fields>
            <field><name>UE</name><bitOffset>13</bitOffset><bitWidth>1</bitWidth></field>
            <field><name>M</name><msb>12</msb><lsb>12</lsb></field>
            <field><name>PS</name><bitRange>[10:9]</bitRange></field>
          </fields>
        </register>
        <register><name>BRR</name>
          <fields>
            <field><name>DIV_Mantissa</name><bitOffset>4</bitOffset><bitWidth>12</bitWidth></field>
          </fields>
        </register>
      </registers>
    </peripheral>
    <peripheral>
      <name>PWR</name>
      <registers>
        <register><name>CR</name>
          <fields>
            <field><name>DBP</name><bitOffset>8</bitOffset><bitWidth>1</bitWidth></field>
          </fields>
        </register>
      </registers>
    </peripheral>
  </peripherals>
</device>
"""


@pytest.fixture
def svd_file(tmp_path):
    """A single .svd FILE (not a directory) -- the corpus-sweep shape."""
    path = tmp_path / "lintdev.svd"
    path.write_text(LINT_SVD)
    return str(path)


def _run(tmp_path, files, svd=None, subdir="run"):
    """Write a run dir from {file_name: register_json}, collect, and return
    (results, manifest, out_dir)."""
    run = tmp_path / subdir
    run.mkdir()
    for name, data in files.items():
        (run / name).write_text(json.dumps(data))
    out = tmp_path / f"{subdir}_collected"
    results = collect_constraints(str(run), output_dir=str(out), svd_dir=svd)
    manifest = json.loads((out / "manifest.json").read_text())
    return results, manifest, out


def _register_entry(manifest, file_name):
    return {r["file"]: r for r in manifest["registers"]}[file_name]


# ---------------------------------------------------------------------------
# exact dedup (task 1)
# ---------------------------------------------------------------------------

def test_dedup_within_register_per_bit_fanout(tmp_path):
    # Three constraints: #0 and #1 are the per-bit fan-out pattern (identical
    # except target_fields -- dedup key deliberately ignores target_fields);
    # #2 differs in the quote and survives.
    pre = [_cond("USART_CR1", "UE", "cleared")]
    files = {"usart1_brr": _register_json("USART_BRR", [
        _constraint("USART_BRR", pre=pre, fields=["DIV_Mantissa"], text="same note"),
        _constraint("USART_BRR", pre=pre, fields=["DIV_Fraction"], text="same note"),
        _constraint("USART_BRR", pre=pre, fields=[], text="a different note"),
    ])}
    results, manifest, _ = _run(tmp_path, files)

    (row,) = results
    assert row["num_constraints"] == 3       # raw v1 untouched
    assert row["num_constraints_v2"] == 2    # duplicate produced no v2

    reg = _register_entry(manifest, "usart1_brr")
    assert reg["duplicates_dropped"] == 1
    kept, dup, other = reg["constraints"]
    assert kept["kinds"] == ["state_gate"]
    assert dup["kinds"] == [] and dup["rejects"] == []
    assert "exact_duplicate" in dup["lint_flags"]
    assert dup["duplicate_of"] == 0          # keep FIRST
    assert other["kinds"] == ["state_gate"]

    summary = manifest["summary"]
    assert summary["constraints_native_v2"] == 3
    assert summary["constraints_deduped"] == 1
    assert summary["constraints_native_v2_unique"] == 2
    assert summary["dedup_rate"] == pytest.approx(1 / 3)
    # A duplicate is NOT a reject; reject-rate uses the unique denominator.
    assert summary["constraints_rejected"] == 0
    assert summary["reject_rate"] == 0.0
    assert summary["constraint_lint_flag_counts"]["exact_duplicate"] == 1


def test_dedup_does_not_merge_distinct_conditions(tmp_path):
    # Same quote but different condition polarity: NOT a duplicate.
    files = {"usart1_brr": _register_json("USART_BRR", [
        _constraint("USART_BRR", pre=[_cond("USART_CR1", "UE", "cleared")]),
        _constraint("USART_BRR", pre=[_cond("USART_CR1", "UE", "set")]),
    ])}
    _, manifest, _ = _run(tmp_path, files)
    assert manifest["summary"]["constraints_deduped"] == 0
    assert manifest["summary"]["constraints_v2"] == 2


def test_duplicate_across_instances_flagged_not_dropped(tmp_path):
    # usart1_brr and usart2_brr carry the identical constraint: both rows
    # survive (step H emits per-instance paths) with the lint flag.
    c = _constraint("USART_BRR", pre=[_cond("USART_CR1", "UE", "cleared")])
    files = {
        "usart1_brr": _register_json("USART_BRR", [dict(c)]),
        "usart2_brr": _register_json("USART_BRR", [dict(c)]),
        # Same family, DIFFERENT register: must not be grouped.
        "usart1_cr3": _register_json("USART_CR3", [
            _constraint("USART_CR3", pre=[_cond("USART_CR1", "UE", "cleared")])]),
    }
    results, manifest, _ = _run(tmp_path, files)
    assert len(results) == 3                          # separate rows kept
    assert manifest["summary"]["constraints_deduped"] == 0
    for name in ("usart1_brr", "usart2_brr"):
        (rep,) = _register_entry(manifest, name)["constraints"]
        assert "duplicate_across_instances" in rep["lint_flags"]
        assert rep["kinds"] == ["state_gate"]         # still lifted
    (cr3_rep,) = _register_entry(manifest, "usart1_cr3")["constraints"]
    assert "duplicate_across_instances" not in cr3_rep["lint_flags"]
    assert manifest["summary"]["constraint_lint_flag_counts"][
        "duplicate_across_instances"] == 2


# ---------------------------------------------------------------------------
# SVD-metadata lint (task 2)
# ---------------------------------------------------------------------------

def test_value_exceeds_field_width_rejected(tmp_path, svd_file):
    files = {"usart1_cr1": _register_json("USART_CR1", [
        # M is 1 bit wide (declared via msb/lsb): equals:2 cannot fit.
        _constraint("USART_CR1", pre=[_cond("USART_CR1", "M", "equals:2")],
                    text="bad width"),
        # PS is 2 bits wide (declared via bitRange): equals:0b10 fits.
        _constraint("USART_CR1", pre=[_cond("USART_CR1", "PS", "equals:0b10")],
                    text="good width"),
    ])}
    _, manifest, _ = _run(tmp_path, files, svd=svd_file)
    reg = _register_entry(manifest, "usart1_cr1")
    bad, good = reg["constraints"]
    assert bad["kinds"] == []
    (rej,) = bad["rejects"]
    assert rej["reason"] == "value_exceeds_field_width"
    assert rej["field"] == "preconditions[0].values"
    assert good["kinds"] == ["state_gate"]
    assert manifest["summary"]["reject_reasons"]["value_exceeds_field_width"] == 1


def test_whole_register_value_checked_against_register_size(tmp_path, svd_file):
    files = {"usart1_cr1": _register_json("USART_CR1", [
        # Whole-register condition: device default size is 0x20 = 32 bits.
        _constraint("USART_CR1",
                    pre=[_cond("PWR_CR", "", "equals:0x1FFFFFFFF")],  # 33 bits
                    text="too wide"),
        _constraint("USART_CR1",
                    pre=[_cond("PWR_CR", "", "equals:0xFFFFFFFF")],   # fits
                    text="fits"),
    ])}
    _, manifest, _ = _run(tmp_path, files, svd=svd_file)
    reg = _register_entry(manifest, "usart1_cr1")
    bad, good = reg["constraints"]
    assert [r["reason"] for r in bad["rejects"]] == ["value_exceeds_field_width"]
    assert good["kinds"] == ["state_gate"]


def test_write_constraint_on_read_only_register_rejected(tmp_path, svd_file):
    files = {"usart1_sr": _register_json("USART_SR", [
        # USART_SR is access=read-only: a WRITE gate on it is an FP by
        # construction ...
        _constraint("USART_SR", op="write",
                    pre=[_cond("USART_CR1", "UE", "cleared")], text="w"),
        # ... and so is a field-granular one (TC inherits read-only).
        _constraint("USART_SR", op="modify", fields=["TC"],
                    pre=[_cond("USART_CR1", "UE", "cleared")], text="m"),
        # A READ gate on the same register is fine (cross-register condition).
        _constraint("USART_SR", op="read",
                    pre=[_cond("USART_CR1", "UE", "set")], text="r"),
    ])}
    _, manifest, _ = _run(tmp_path, files, svd=svd_file)
    reg = _register_entry(manifest, "usart1_sr")
    w, m, r = reg["constraints"]
    assert [x["reason"] for x in w["rejects"]] == ["write_constraint_on_read_only"]
    assert [x["reason"] for x in m["rejects"]] == ["write_constraint_on_read_only"]
    assert w["kinds"] == [] and m["kinds"] == []
    assert r["kinds"] == ["state_gate"]
    assert manifest["summary"]["reject_reasons"]["write_constraint_on_read_only"] == 2


def test_writable_target_not_rejected(tmp_path, svd_file):
    files = {"usart1_cr1": _register_json("USART_CR1", [
        _constraint("USART_CR1", op="write",
                    pre=[_cond("RCC_CR", "HSEON", "set")], text="w"),
    ])}
    _, manifest, _ = _run(tmp_path, files, svd=svd_file)
    (rep,) = _register_entry(manifest, "usart1_cr1")["constraints"]
    assert rep["kinds"] == ["state_gate"]
    assert rep["rejects"] == []


def test_w1c_postcondition_rejected_via_modified_write_values(tmp_path, svd_file):
    # RCC_CSR.RMVF is oneToClear: a (software) "RMVF becomes cleared"
    # postcondition merely restates the flag-clear behavior (class 1).
    files = {"rcc_csr": _register_json("RCC_CSR", [
        _constraint("RCC_CSR", op="write",
                    pre=[_cond("RCC_CR", "HSEON", "set")],
                    post=[_cond("RCC_CSR", "RMVF", "cleared",
                               established_by="software", action_operation="modify")],
                    text="w1c note"),
    ])}
    _, manifest, _ = _run(tmp_path, files, svd=svd_file)
    (rep,) = _register_entry(manifest, "rcc_csr")["constraints"]
    # The precise w1c reason, NOT the generic observed-state drop.
    assert [r["reason"] for r in rep["rejects"]] == ["w1c_flag_semantics"]
    assert "w1c_semantics" in rep["lint_flags"]
    # The precondition gate itself survives.
    assert rep["kinds"] == ["state_gate"]


def test_w1c_postcondition_rejected_via_register_read_action(tmp_path, svd_file):
    # USART_DR has register-level readAction=clear (status-register signal):
    # a (software) "DATA becomes cleared" postcondition restates read-to-clear.
    files = {"usart1_cr1": _register_json("USART_CR1", [
        _constraint("USART_CR1", op="write",
                    pre=[_cond("RCC_CR", "HSEON", "set")],
                    post=[_cond("USART_DR", "DATA", "cleared",
                               established_by="software", action_operation="modify")],
                    text="read-clear note"),
    ])}
    _, manifest, _ = _run(tmp_path, files, svd=svd_file)
    (rep,) = _register_entry(manifest, "usart1_cr1")["constraints"]
    assert [r["reason"] for r in rep["rejects"]] == ["w1c_flag_semantics"]
    assert "w1c_semantics" in rep["lint_flags"]
    assert rep["kinds"] == ["state_gate"]


def test_without_svd_w1c_postcondition_not_reclassified(tmp_path):
    # Same (software) postcondition, no SVD: w1c cannot be detected without the
    # SVD, so the postcondition is NOT reclassified -- the gate survives intact.
    files = {"rcc_csr": _register_json("RCC_CSR", [
        _constraint("RCC_CSR", op="write",
                    pre=[_cond("RCC_CR", "HSEON", "set")],
                    post=[_cond("RCC_CSR", "RMVF", "cleared",
                               established_by="software", action_operation="modify")],
                    text="w1c note"),
    ])}
    _, manifest, _ = _run(tmp_path, files)
    (rep,) = _register_entry(manifest, "rcc_csr")["constraints"]
    assert rep["rejects"] == []
    assert rep["kinds"] == ["state_gate"]
    assert "w1c_semantics" not in rep["lint_flags"]


def test_w1c_precondition_flagged_not_rejected(tmp_path, svd_file):
    # A PRECONDITION on a w1c flag field is only flagged for review.
    files = {"rcc_cr": _register_json("RCC_CR", [
        _constraint("RCC_CR", op="write",
                    pre=[_cond("RCC_CSR", "RMVF", "cleared")], text="q"),
    ])}
    _, manifest, _ = _run(tmp_path, files, svd=svd_file)
    (rep,) = _register_entry(manifest, "rcc_cr")["constraints"]
    assert rep["kinds"] == ["state_gate"]
    assert rep["rejects"] == []
    assert "w1c_semantics" in rep["lint_flags"]


def test_read_side_effect_flag(tmp_path, svd_file):
    files = {"usart1_cr1": _register_json("USART_CR1", [
        # Read gate whose check reads USART_DR (readAction=clear).
        _constraint("USART_CR1", op="read",
                    pre=[_cond("USART_DR", "DATA", "cleared")], text="r"),
        # Read gate on a side-effect-free condition: no flag.
        _constraint("USART_CR1", op="read",
                    pre=[_cond("RCC_CR", "HSEON", "set")], text="r2"),
    ])}
    _, manifest, _ = _run(tmp_path, files, svd=svd_file)
    flagged, clean = _register_entry(manifest, "usart1_cr1")["constraints"]
    assert flagged["kinds"] == ["state_gate"]       # flag, not reject
    assert "read_side_effect" in flagged["lint_flags"]
    assert "read_side_effect" not in clean["lint_flags"]


# ---------------------------------------------------------------------------
# structural flags (task 3) -- no SVD needed
# ---------------------------------------------------------------------------

def test_self_defeating_read_gate_rejected_without_svd(tmp_path):
    files = {"spi1_txcrcr": _register_json("SPI_TXCRCR", [
        # The rm0008 spi1_txcrcr shape: read gated on the register's own BSY
        # -- checking it performs the constrained read.
        _constraint("SPI_TXCRCR", op="read",
                    pre=[_cond("SPI_TXCRCR", "BSY", "cleared")], text="r"),
    ])}
    _, manifest, _ = _run(tmp_path, files)
    (rep,) = _register_entry(manifest, "spi1_txcrcr")["constraints"]
    assert rep["kinds"] == []
    assert [r["reason"] for r in rep["rejects"]] == ["self_defeating_read_gate"]
    assert manifest["summary"]["reject_reasons"]["self_defeating_read_gate"] == 1


def test_self_defeating_check_spares_other_expanded_operations(tmp_path):
    # target_operation "any" expands to read+write; only the READ gate is
    # self-defeating (its check would read the target), and the write gate
    # survives. modify() is NOT a gate here -- the emitter derives it from
    # the read+write union.
    files = {"spi1_txcrcr": _register_json("SPI_TXCRCR", [
        _constraint("SPI_TXCRCR", op="any",
                    pre=[_cond("SPI_TXCRCR", "BSY", "cleared")], text="q"),
    ])}
    _, manifest, out = _run(tmp_path, files)
    (rep,) = _register_entry(manifest, "spi1_txcrcr")["constraints"]
    assert sorted(rep["kinds"]) == ["state_gate"]
    assert [r["reason"] for r in rep["rejects"]] == ["self_defeating_read_gate"]
    data = json.loads((out / "spi1_txcrcr.json").read_text())
    assert sorted(g["target_operation"] for g in data["access_constraints_v2"]) == \
        ["write"]


def test_cross_register_read_gate_survives(tmp_path):
    files = {"spi1_txcrcr": _register_json("SPI_TXCRCR", [
        _constraint("SPI_TXCRCR", op="read",
                    pre=[_cond("SPI_SR", "BSY", "cleared")], text="r"),
    ])}
    _, manifest, _ = _run(tmp_path, files)
    (rep,) = _register_entry(manifest, "spi1_txcrcr")["constraints"]
    assert rep["kinds"] == ["state_gate"]
    assert rep["rejects"] == []


def test_software_evidence_read_gate_not_self_defeating(tmp_path):
    # Task spec: the reject is for HARDWARE-established_by checks (a software-action
    # witness does not read the target register to check).
    files = {"spi1_txcrcr": _register_json("SPI_TXCRCR", [
        _constraint("SPI_TXCRCR", op="read",
                    pre=[_cond("SPI_TXCRCR", "BSY", "cleared",
                               evidence_kind="software_action",
                               action_operation="modify")],
                    text="r"),
    ])}
    _, manifest, _ = _run(tmp_path, files)
    (rep,) = _register_entry(manifest, "spi1_txcrcr")["constraints"]
    assert rep["kinds"] == ["state_gate"]
    assert rep["rejects"] == []


def test_self_defeating_detects_bare_register_name(tmp_path):
    # Condition names the target in bare form ("TXCRCR" vs "SPI_TXCRCR").
    files = {"spi1_txcrcr": _register_json("SPI_TXCRCR", [
        _constraint("SPI_TXCRCR", op="read",
                    pre=[_cond("TXCRCR", "BSY", "cleared")], text="r"),
    ])}
    _, manifest, _ = _run(tmp_path, files)
    (rep,) = _register_entry(manifest, "spi1_txcrcr")["constraints"]
    assert [r["reason"] for r in rep["rejects"]] == ["self_defeating_read_gate"]


def test_cross_peripheral_flag_heuristic_without_svd(tmp_path):
    files = {"rtc_crl": _register_json("RTC_CRL", [
        # The flagship cross-peripheral case: PWR_CR.DBP gating RTC writes.
        _constraint("RTC_CRL", op="write",
                    pre=[_cond("PWR_CR", "DBP", "set")], text="dbp"),
        # Same-peripheral condition: no flag.
        _constraint("RTC_CRL", op="write",
                    pre=[_cond("RTC_ISR", "RSF", "set")], text="own"),
    ])}
    _, manifest, _ = _run(tmp_path, files)
    cross, own = _register_entry(manifest, "rtc_crl")["constraints"]
    assert "cross_peripheral" in cross["lint_flags"]
    assert cross["kinds"] == ["state_gate"]          # flag, NOT a reject
    assert "cross_peripheral" not in own["lint_flags"]
    assert manifest["summary"]["constraint_lint_flag_counts"]["cross_peripheral"] == 1


def test_cross_peripheral_flag_with_svd(tmp_path, svd_file):
    files = {"usart1_cr1": _register_json("USART_CR1", [
        _constraint("USART_CR1", op="write",
                    pre=[_cond("PWR_CR", "DBP", "set")], text="dbp"),
    ])}
    _, manifest, _ = _run(tmp_path, files, svd=svd_file)
    (rep,) = _register_entry(manifest, "usart1_cr1")["constraints"]
    assert "cross_peripheral" in rep["lint_flags"]
    assert rep["kinds"] == ["state_gate"]


def test_cross_peripheral_family_compatibility():
    # usart/uart share a manual chapter; gpioa/gpiob are instances of one
    # family -- neither pair is cross-PERIPHERAL.
    assert _families_compatible("usart", "uart")
    assert _families_compatible("uart", "usart")
    assert _families_compatible("gpioa", "gpiob")
    assert _families_compatible("i2c", "fmpi2c")
    assert not _families_compatible("pwr", "rtc")
    assert not _families_compatible("adc", "dac")


def test_cross_peripheral_not_flagged_for_related_families(tmp_path):
    files = {"uart4_cr1": _register_json("UART_CR1", [
        # The manual's shared-chapter style: USART_-prefixed names in a UART
        # instance's section.
        _constraint("UART_CR1", op="write",
                    pre=[_cond("USART_CR3", "DMAR", "cleared")], text="q"),
    ])}
    _, manifest, _ = _run(tmp_path, files)
    (rep,) = _register_entry(manifest, "uart4_cr1")["constraints"]
    assert "cross_peripheral" not in rep["lint_flags"]


# ---------------------------------------------------------------------------
# SVD index details
# ---------------------------------------------------------------------------

def test_svd_index_accepts_single_file(svd_file):
    index = _load_svd_index(svd_file)
    assert "usart1_cr1" in index["registers"]


def test_svd_index_metadata(svd_file):
    index = _load_svd_index(svd_file)
    # Widths from all three SVD encodings.
    assert index["field_meta"][("usart1_cr1", "ue")]["widths"] == {1}   # bitWidth
    assert index["field_meta"][("usart1_cr1", "m")]["widths"] == {1}    # msb/lsb
    assert index["field_meta"][("usart1_cr1", "ps")]["widths"] == {2}   # bitRange
    # Register size from the device default (0x20).
    assert index["reg_meta"]["usart1_sr"]["sizes"] == {32}
    # Access inheritance: TC inherits the register's read-only.
    assert index["field_meta"][("usart1_sr", "tc")]["accesses"] == {"read-only"}
    assert index["reg_meta"]["usart1_sr"]["read_only"] == [True]
    assert index["reg_meta"]["usart1_cr1"]["read_only"] == [False]
    # modifiedWriteValues and readAction.
    assert index["field_meta"][("rcc_csr", "rmvf")]["mwv"] == {"onetoclear"}
    assert index["reg_meta"]["usart1_dr"]["read_actions"] == {"clear"}
    # Peripheral attribution for the cross-peripheral lint.
    assert "pwr" in index["peripheral_names"]
    assert "cr" in index["peripheral_registers"]["pwr"]
