"""DeviceLayout: the injector has to walk BOTH svd2rust device layouts.

stm32-rs 0.16 ships peripherals two ways. Twenty of the twenty-one crates we
provision use the flat one (``device/<periph>.rs`` + ``device/<periph>/<reg>.rs``).
stm32h7 alone deduplicates: the device module is nothing but a ``mod.rs`` full of

    #[path = "../common/i2c1/75d0aa88/mod.rs"]
    pub mod i2c1;

with the register files living beside that shared ``mod.rs``. Before this was
supported, every one of the five H7 manuals injected ZERO registers -- each
peripheral reported "not in device" -- so these tests pin the resolution rules.
"""
import sys
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR.parent.parent))

from rust_codegen import DeviceLayout, add_marker_impls  # noqa: E402


def _flat(root: Path, device: str = "stm32f401") -> Path:
    d = root / "src" / device
    (d / "i2c1").mkdir(parents=True)
    (d / "i2c1.rs").write_text("pub mod cr1;\n")
    (d / "i2c1" / "cr1.rs").write_text(
        "pub struct CR1rs;\nimpl crate::Writable for CR1rs {}\n")
    (d / "mod.rs").write_text("pub mod i2c1;\n")
    return d


def _dedup(root: Path, device: str = "stm32h753v") -> Path:
    shared = root / "src" / "common" / "i2c1" / "75d0aa88"
    shared.mkdir(parents=True)
    (shared / "mod.rs").write_text("pub mod cr1;\n")
    (shared / "cr1.rs").write_text(
        "pub struct CR1rs;\nimpl crate::Writable for CR1rs {}\n")
    d = root / "src" / device
    d.mkdir(parents=True)
    (d / "mod.rs").write_text(
        '#[path = "../common/i2c1/75d0aa88/mod.rs"]\npub mod i2c1;\n')
    return d


def test_flat_layout_is_not_deduplicated(tmp_path):
    layout = DeviceLayout(_flat(tmp_path))
    assert layout.deduplicated is False
    assert layout.module_file("i2c1").name == "i2c1.rs"
    assert layout.register_file("i2c1", "cr1").read_text().startswith("pub struct")


def test_dedup_layout_resolves_through_the_path_attribute(tmp_path):
    d = _dedup(tmp_path)
    layout = DeviceLayout(d)
    assert layout.deduplicated is True
    # the module file is the SHARED one, not device/i2c1.rs (which does not exist)
    assert layout.module_file("i2c1") == (
        tmp_path / "src" / "common" / "i2c1" / "75d0aa88" / "mod.rs")
    assert not (d / "i2c1.rs").exists()
    assert layout.register_file("i2c1", "cr1").is_file()


def test_dedup_register_files_carry_the_declared_peripheral_name(tmp_path):
    """Attribution cannot come from the path -- it is a content hash. It has to
    come from the `pub mod <name>` the device's mod.rs declares."""
    layout = DeviceLayout(_dedup(tmp_path))
    found = {periph for periph, _ in layout.iter_register_files()}
    assert found == {"i2c1"}


def test_unknown_peripheral_falls_back_to_the_flat_guess(tmp_path):
    layout = DeviceLayout(_dedup(tmp_path))
    missing = layout.module_file("nosuch")
    assert missing.name == "nosuch.rs" and not missing.is_file()


def test_markers_land_in_the_shared_block(tmp_path):
    d = _dedup(tmp_path)
    assert add_marker_impls(d, set()) == 1
    shared = tmp_path / "src" / "common" / "i2c1" / "75d0aa88" / "cr1.rs"
    assert "impl crate::UnconstrainedWrite for CR1rs {}" in shared.read_text()


def test_gate_suppresses_the_marker_in_the_shared_block(tmp_path):
    d = _dedup(tmp_path)
    add_marker_impls(d, {("i2c1", "CR1rs", "write")})
    shared = tmp_path / "src" / "common" / "i2c1" / "75d0aa88" / "cr1.rs"
    assert "UnconstrainedWrite" not in shared.read_text()


def test_second_pass_over_a_shared_block_is_skippable_not_fatal(tmp_path):
    """A sibling device reaching the SAME shared block must not re-mark it --
    that is how add_sibling_markers survives the deduplicated layout."""
    d = _dedup(tmp_path)
    add_marker_impls(d, set())
    with pytest.raises(RuntimeError, match="one-shot"):
        add_marker_impls(d, set())
    assert add_marker_impls(d, set(), skip_marked=True) == 0
