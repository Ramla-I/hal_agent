#!/usr/bin/env python3
"""test_trace_hal_calls.py -- a shared method NAME is not a call into the driver.

WHAT THIS GUARDS
----------------
`trace_hal.py` joins an application to a driver by method name, because Rust
call resolution needs type inference this tool does not do. Name-only joins
invent findings, and each test below is a false positive that was actually
reported before the check it pins existed:

  1. ANOTHER CRATE'S TYPE. px4flow_bsp calls `Base64Display::with_config(..)`
     from the `base64` crate. `with_config` is defined exactly ONCE inside
     stm32f4xx-hal (`Rtc::with_config`), so the uniqueness check -- which only
     ever looks inside the driver -- claimed it, and an RTC/BDCR constraint was
     reported as reaching the application. The qualifier names the type, and
     `Base64Display` is not a type the driver defines.

  2. A DECLARATION. `pub fn convert(&self, ..)` is where a function is
     declared, not a place it is called. It was being counted as a call.

  3. THE APPLICATION'S OWN METHOD. booster declares its own `convert`, which
     forwards to the driver's. `self.pins.output_power.convert(..)` is a call
     to booster's, and only the receiver's type says so. Such lines are
     reported for a human, never counted.

Together these took booster from 4 claimed sites to 3 shown-and-unclaimed, and
px4flow_bsp from 2 to 0.
"""

import sys
import tempfile
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent / "experiments"
sys.path.insert(0, str(EXP))
import trace_hal  # noqa: E402


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class AppCalls(unittest.TestCase):
    def scan(self, rel: str, text: str):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write(root, rel, text)
            return trace_hal.app_calls(root)

    def test_qualifier_is_captured(self):
        """`Foo::bar(..)` records Foo, so a foreign type can be rejected."""
        calls, _ = self.scan("src/a.rs", "let w = Base64Display::with_config(x);\n")
        self.assertIn("with_config", calls)
        self.assertEqual(calls["with_config"][0][3], "Base64Display")

    def test_method_call_has_no_qualifier(self):
        """`x.bar(..)` cannot name its type; None means 'not known'."""
        calls, _ = self.scan("src/a.rs", "adc.convert(pin, t);\n")
        self.assertEqual(calls["convert"][0][3], None)

    def test_declaration_is_not_a_call(self):
        """The line that declares `convert` must not be reported as calling it."""
        calls, defined = self.scan(
            "src/a.rs",
            "pub fn convert(&self, adc: &mut Adc<ADC3>) -> u16 {\n    0\n}\n")
        self.assertIn("convert", defined)
        self.assertEqual(calls.get("convert", []), [],
                         "a declaration was counted as a call")

    def test_app_declared_name_is_reported(self):
        """Declaring it AND calling it: the call is still recorded, but
        `defined` is what tells main() not to claim it."""
        calls, defined = self.scan(
            "src/a.rs",
            "pub fn convert(&self, adc: &mut Adc) -> u16 {\n"
            "    self.pins.output_power.convert(adc)\n"
            "}\n")
        self.assertIn("convert", defined)
        self.assertEqual(len(calls["convert"]), 1)
        self.assertEqual(calls["convert"][0][1], 2)

    def test_comments_are_not_calls(self):
        """A commented-out block is not a code path the application takes."""
        calls, _ = self.scan(
            "src/a.rs",
            "// adc.convert(a);\n"
            "/*\nadc.convert(b);\n*/\n"
            "adc.convert(c);\n")
        self.assertEqual(len(calls["convert"]), 1)
        self.assertEqual(calls["convert"][0][1], 5)


class ForeignTypeRejection(unittest.TestCase):
    """The rule main() applies: a NAMED type the driver does not define is not
    the driver's function, however unique the name is inside the driver."""

    def reject(self, qual, driver_types):
        return bool(qual) and qual not in driver_types

    def test_foreign_type_rejected(self):
        self.assertTrue(self.reject("Base64Display", {"Rtc", "Adc", "Spi"}))

    def test_driver_type_kept(self):
        self.assertFalse(self.reject("Rtc", {"Rtc", "Adc", "Spi"}))

    def test_unqualified_call_is_not_rejected(self):
        """`x.with_config(..)` names no type; rejecting it would drop every
        method call in the corpus."""
        self.assertFalse(self.reject(None, {"Rtc"}))


class AppsCarryTheirManual(unittest.TestCase):
    """Every application is traced against the manual for ITS OWN chip. The
    default used to be one manual (rm0368 / STM32F401) inherited from the
    retired patch_hal.py, and none of these three parts is an F401."""

    def test_each_app_names_a_manual(self):
        for name, (desc, rm) in trace_hal.APPS.items():
            self.assertTrue(rm.startswith("rm"), f"{name}: {rm!r}")
            self.assertTrue(desc)

    def test_f407_apps_use_rm0090(self):
        self.assertEqual(trace_hal.APPS["booster"][1], "rm0090")
        self.assertEqual(trace_hal.APPS["px4flow_bsp"][1], "rm0090")

    def test_f469_app_uses_rm0386(self):
        self.assertEqual(trace_hal.APPS["stm32f469i-disc"][1], "rm0386")


if __name__ == "__main__":
    unittest.main(verbosity=2)
