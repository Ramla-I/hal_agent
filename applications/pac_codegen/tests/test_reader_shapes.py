#!/usr/bin/env python3
"""test_reader_shapes.py -- a precondition must match its field's reader shape.

WHAT THIS GUARDS
----------------
svd2rust gives a 1-bit field a ``BitReader`` (``bit_is_set``/``bit_is_clear``,
NO ``bits()``) and a multi-bit field a ``FieldReader`` (``bits()``, no
``bit_is_*``). The two share no accessor, so a precondition emitted against the
wrong shape calls a method that does not exist -- E0599 *inside the PAC*, which
breaks the crate and every downstream consumer of it, not just the constrained
call site.

That is exactly how the first whole-corpus injection run failed: RM0008's CAN
filter gates carry ``FINIT == 0x1``, an `equals` condition on a 1-bit field, and
the emitter spelled it ``r_fmr.finit().bits() == 0x1``.

``prune_plans_for_device`` now reconciles every precondition against the
GENERATED register file, which is the ground truth (same contract the
access-mode prune already used):

  * ``equals 0`` / ``equals 1`` on a 1-bit field -> RESPELLED cleared/set
    (identical condition, compilable API -- the constraint survives);
  * anything the generated API cannot express -> the WHOLE gate is dropped,
    never just the offending conjunct (a gate short one condition would
    silently demand less than the datasheet does).

Resolution follows svd2rust's de-duplicating re-exports, which is where a naive
"grep for `pub type FIELD_R`" fails: ``PLLON_R`` is usually not declared at all,
it is ``pub use HSION_R as PLLON_R;``.

No toolchain needed -- the fixtures are synthetic register files.

Run directly (``python test_reader_shapes.py``) or under pytest.
"""

import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR.parent.parent))

import rust_codegen  # noqa: E402
from defs import RegisterInfo  # noqa: E402


# --------------------------------------------------------------------------- #
# Synthetic device module (the shapes svd2rust really emits)
# --------------------------------------------------------------------------- #

_FMR_RS = """\
///Field `FINIT` reader - FINIT
pub type FINIT_R = crate::BitReader;
///Field `CAN2SB` reader - CAN2SB
pub type CAN2SB_R = crate::FieldReader;
impl crate::Readable for FMRrs {}
impl crate::Writable for FMRrs {}
"""

# PLLON is a RE-EXPORT of HSION, the way svd2rust de-duplicates identical
# readers. A resolver that only reads `pub type` declarations misses it.
_CR_RS = """\
///Field `HSION` reader - HSION
pub type HSION_R = crate::BitReader<HSION>;
///Field `PLLON` reader - Main PLL enable
pub use HSION_R as PLLON_R;
///Field `SW` reader - clock switch
pub type SW_R = crate::FieldReader<SW>;
impl crate::Readable for CRrs {}
impl crate::Writable for CRrs {}
"""

_TARGET_RS = """\
///Field `X` reader - X
pub type X_R = crate::BitReader;
impl crate::Readable for TGTrs {}
impl crate::Writable for TGTrs {}
"""


def _device(tmp: Path) -> Path:
    dev = tmp / "stm32fake"
    for periph, regs in {
        "can": {"fmr": _FMR_RS, "tgt": _TARGET_RS},
        "rcc": {"cr": _CR_RS},
    }.items():
        (dev / periph).mkdir(parents=True)
        for reg, text in regs.items():
            (dev / periph / f"{reg}.rs").write_text(text)
        (dev / f"{periph}.rs").write_text("// peripheral module\n")
    return dev


def _plan(cond: dict, peripheral: str = "can", register: str = "TGT"):
    """One state_gate on `register`.write with a single precondition."""
    info = RegisterInfo(**{
        "datasheet_register_abbreviation": register,
        "address_offset": "0x0",
        "reset_value": "0x0",
        "size": 32,
        "subfields": [],
        "access_constraints_v2": [{
            "kind": "state_gate",
            "severity": "error",
            "consequence": "test",
            "datasheet_text": "test constraint",
            "target_register": register,
            "target_fields": [],
            "target_operation": "write",
            "preconditions": [{
                "whole_register": False, "values": [],
                "established_by": "hardware", "action_operation": None,
                **cond,
            }],
            "postconditions": [],
        }],
    })
    return rust_codegen.RegisterPlan(info, peripheral)


def _prune(dev: Path, plan):
    return rust_codegen.prune_plans_for_device(dev, [plan])


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

def test_equals_one_on_bit_field_is_respelled():
    """`FINIT == 0x1` on a 1-bit field must survive as `set` -- the constraint
    is real; only its spelling was uncompilable."""
    with tempfile.TemporaryDirectory() as td:
        dev = _device(Path(td))
        plan = _plan({"register": "CAN_FMR", "field": "FINIT",
                      "state": "equals", "values": [1]})
        kept = _prune(dev, plan)
        assert kept, "gate was dropped instead of respelled"
        pre = kept[0].preconditions["write"][0]
        assert pre.kind == "set", f"expected set, got {pre.kind}"
        assert pre.check_expr("r_fmr") == "r_fmr.finit().bit_is_set()"


def test_equals_zero_on_bit_field_becomes_cleared():
    with tempfile.TemporaryDirectory() as td:
        dev = _device(Path(td))
        plan = _plan({"register": "CAN_FMR", "field": "FINIT",
                      "state": "equals", "values": [0]})
        kept = _prune(dev, plan)
        assert kept
        assert kept[0].preconditions["write"][0].check_expr("r_fmr") == \
            "r_fmr.finit().bit_is_clear()"


def test_equals_out_of_range_on_bit_field_drops_the_gate():
    """`FINIT == 0x3` cannot hold for a 1-bit field: unsatisfiable, so the gate
    goes -- it must not be silently weakened to something that compiles."""
    with tempfile.TemporaryDirectory() as td:
        dev = _device(Path(td))
        plan = _plan({"register": "CAN_FMR", "field": "FINIT",
                      "state": "equals", "values": [3]})
        assert _prune(dev, plan) == []


def test_set_on_multibit_field_drops_the_gate():
    """`bit_is_set()` does not exist on FieldReader."""
    with tempfile.TemporaryDirectory() as td:
        dev = _device(Path(td))
        plan = _plan({"register": "CAN_FMR", "field": "CAN2SB",
                      "state": "set"})
        assert _prune(dev, plan) == []


def test_equals_on_multibit_field_survives():
    with tempfile.TemporaryDirectory() as td:
        dev = _device(Path(td))
        plan = _plan({"register": "CAN_FMR", "field": "CAN2SB",
                      "state": "equals", "values": [5]})
        kept = _prune(dev, plan)
        assert kept
        assert kept[0].preconditions["write"][0].check_expr("r_fmr") == \
            "r_fmr.can2sb().bits() == 0x5"


def test_reexported_reader_is_resolved():
    """PLLON is `pub use HSION_R as PLLON_R;` -- a declaration-only resolver
    would see no reader and drop a perfectly good cross-peripheral gate."""
    with tempfile.TemporaryDirectory() as td:
        dev = _device(Path(td))
        plan = _plan({"register": "RCC_CR", "field": "PLLON",
                      "state": "cleared"})
        kept = _prune(dev, plan)
        assert kept, "re-exported BitReader was not resolved"
        assert kept[0].preconditions["write"][0].check_expr("r_rcc_cr") == \
            "r_rcc_cr.pllon().bit_is_clear()"


def test_unknown_field_drops_the_gate():
    with tempfile.TemporaryDirectory() as td:
        dev = _device(Path(td))
        plan = _plan({"register": "CAN_FMR", "field": "NOSUCHFIELD",
                      "state": "set"})
        assert _prune(dev, plan) == []


def test_absent_source_register_drops_the_gate():
    with tempfile.TemporaryDirectory() as td:
        dev = _device(Path(td))
        plan = _plan({"register": "PWR_CR", "field": "DBP", "state": "set"})
        assert _prune(dev, plan) == []


def test_prune_is_idempotent():
    """Drivers run the prune before saving the artifact AND again at injection;
    the second pass must not further change a respelled gate."""
    with tempfile.TemporaryDirectory() as td:
        dev = _device(Path(td))
        plan = _plan({"register": "CAN_FMR", "field": "FINIT",
                      "state": "equals", "values": [1]})
        once = _prune(dev, plan)
        twice = rust_codegen.prune_plans_for_device(dev, once)
        assert twice and twice[0].preconditions["write"][0].kind == "set"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    print("Running reader-shape tests...\n")
    for t in tests:
        try:
            t()
            print(f"✓ {t.__name__}")
            passed += 1
        except Exception as e:                                # noqa: BLE001
            print(f"✗ {t.__name__}: {e}")
            failed += 1
    print(f"\n{'=' * 60}\nResults: {passed} passed, {failed} failed\n{'=' * 60}")
    if failed:
        sys.exit(1)
