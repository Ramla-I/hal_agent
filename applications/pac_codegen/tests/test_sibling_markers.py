#!/usr/bin/env python3
"""test_sibling_markers.py -- generic.rs is crate-wide, so markers must be too.

WHAT THIS GUARDS
----------------
A multi-device PAC (stm32f1 ships stm32f100/f101/f102/f103/f107, stm32f4 ships
eleven) has ONE ``generic.rs`` shared by every device module, selected by cargo
feature. Injection patches that file crate-wide but gates one device module.

If the marker walk covers only the injected module, every register in the
SIBLING modules is left without ``Unconstrained*`` -- which, under the bounds
now on the stock methods, means downstream code selecting a sibling chip gets::

    error[E0277]: `stm32f1::stm32f101::rcc::cr::CRrs` is write-constrained
                  by its datasheet

for a register no datasheet constrained. A false positive, and an INVISIBLE
one: a generic bound is only checked at a call site, so the PAC itself still
compiles and a probe crate that merely depends on it notices nothing. It
surfaces only in real downstream code on another chip of the same family.

``add_sibling_markers`` gives every other device module FULL markers, so those
chips behave exactly as an unpatched PAC. They are deliberately NOT gated: a
manual's constraints belong to its own chip, and one crate can serve several
manuals (four RMs share stm32f3).

No toolchain needed -- the fixtures are synthetic device modules.

Run directly (``python test_sibling_markers.py``) or under pytest.
"""

import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR.parent.parent))

import rust_codegen  # noqa: E402

_REG_RS = """\
pub struct {spec};
impl crate::Readable for {spec} {{}}
impl crate::Writable for {spec} {{}}
"""

_READ_ONLY_RS = """\
pub struct {spec};
impl crate::Readable for {spec} {{}}
"""


def _crate(tmp: Path, devices=("stm32f103", "stm32f101")) -> Path:
    """A synthetic multi-device PAC src/ tree."""
    src = tmp / "src"
    for dev in devices:
        (src / dev / "rcc").mkdir(parents=True)
        (src / dev / "rcc.rs").write_text("// peripheral module\n")
        (src / dev / "rcc" / "cr.rs").write_text(_REG_RS.format(spec="CRrs"))
        (src / dev / "rcc" / "csr.rs").write_text(
            _READ_ONLY_RS.format(spec="CSRrs"))
    (src / "generic.rs").write_text("// generic\n")
    return src


def _markers(src: Path, device: str, reg: str) -> str:
    return (src / device / "rcc" / f"{reg}.rs").read_text()


def test_sibling_module_gets_full_markers():
    """The uninjected sibling must end up with every marker its registers can
    carry -- otherwise downstream code on that chip breaks for no reason."""
    with tempfile.TemporaryDirectory() as td:
        src = _crate(Path(td))
        rust_codegen.add_marker_impls(src / "stm32f103",
                                      {("rcc", "CRrs", "write")})
        n = rust_codegen.add_sibling_markers(src, "stm32f103")
        assert n > 0, "no sibling files were marked"
        sib = _markers(src, "stm32f101", "cr")
        assert "impl crate::UnconstrainedRead for CRrs {}" in sib
        assert "impl crate::UnconstrainedWrite for CRrs {}" in sib
        assert "impl crate::UnconstrainedModify for CRrs {}" in sib


def test_gate_does_not_leak_into_siblings():
    """The injected module's gate must NOT propagate sideways: the sibling is
    a different chip, possibly from a different reference manual."""
    with tempfile.TemporaryDirectory() as td:
        src = _crate(Path(td))
        rust_codegen.add_marker_impls(src / "stm32f103",
                                      {("rcc", "CRrs", "write")})
        rust_codegen.add_sibling_markers(src, "stm32f103")
        target = _markers(src, "stm32f103", "cr")
        assert "impl crate::UnconstrainedWrite for CRrs {}" not in target, \
            "the injected module's write gate was lost"
        sib = _markers(src, "stm32f101", "cr")
        assert "impl crate::UnconstrainedWrite for CRrs {}" in sib, \
            "the gate leaked into a sibling chip"


def test_read_only_register_gets_no_write_marker():
    """`UnconstrainedWrite: Writable` is a supertrait -- emitting the marker for
    a non-writable register would not compile."""
    with tempfile.TemporaryDirectory() as td:
        src = _crate(Path(td))
        rust_codegen.add_sibling_markers(src, "stm32f103")
        sib = _markers(src, "stm32f101", "csr")
        assert "impl crate::UnconstrainedRead for CSRrs {}" in sib
        assert "UnconstrainedWrite for CSRrs" not in sib
        assert "UnconstrainedModify for CSRrs" not in sib


def test_injected_module_is_not_touched_twice():
    """Marking is one-shot per file; the sibling walk must skip the injected
    module rather than trip its own guard."""
    with tempfile.TemporaryDirectory() as td:
        src = _crate(Path(td))
        rust_codegen.add_marker_impls(src / "stm32f103", set())
        rust_codegen.add_sibling_markers(src, "stm32f103")   # must not raise
        target = _markers(src, "stm32f103", "cr")
        assert target.count(rust_codegen.MARKER_SENTINEL) == 1


def test_every_device_module_is_covered():
    """A crate with many device modules (stm32f4 ships eleven) must have all of
    them marked, not just the first sibling found."""
    devices = ("stm32f401", "stm32f405", "stm32f407", "stm32f429")
    with tempfile.TemporaryDirectory() as td:
        src = _crate(Path(td), devices)
        rust_codegen.add_marker_impls(src / "stm32f401", set())
        rust_codegen.add_sibling_markers(src, "stm32f401")
        for dev in devices:
            assert rust_codegen.MARKER_SENTINEL in _markers(src, dev, "cr"), \
                f"{dev} was left unmarked"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    print("Running sibling-marker tests...\n")
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
