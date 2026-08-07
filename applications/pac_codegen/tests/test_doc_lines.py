"""A datasheet quote must survive into Rust as legal doc comments.

Quotes are lifted verbatim from the manual, and plenty of them span several
lines. RM0440's FDCAN rule is a sentence followed by a bulleted list::

    The following registers can be written only when the CCE bit is cleared:
    - CCCR
    - ...

Interpolated into a single `/// {doc}`, only the FIRST line gets the `///`;
the remainder lands as bare text inside an `impl` block and rustc stops
parsing the file:

    error: expected item after doc comment
       --> src/stm32g4a1/fdcan.rs:813:9

That does not fail one register -- it fails the entire chip crate, and with it
every driver above it. Seven of the 48 sweep targets went down this way, and
because the emitter itself succeeded, the failure showed up only at the probe
compile, several stages downstream.
"""
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR.parent.parent))

from rust_codegen import doc_lines  # noqa: E402

_LEGAL = re.compile(r"^\s*///")


def test_single_line_quote_is_one_doc_line():
    assert doc_lines("Write only when SPE = 0.") == [
        "    /// Write only when SPE = 0."]


def test_every_line_of_a_multiline_quote_is_prefixed():
    quote = ("The following registers can be written only when the CCE bit "
             "is cleared:\n- CCCR\n- NBTP")
    out = doc_lines(quote)
    assert len(out) == 3
    assert all(_LEGAL.match(line) for line in out), out


def test_blank_lines_survive_as_bare_doc_markers():
    out = doc_lines("First paragraph.\n\nSecond paragraph.")
    assert out == ["    /// First paragraph.", "    ///",
                   "    /// Second paragraph."]


def test_crlf_and_trailing_space_do_not_leak_raw_text():
    out = doc_lines("Line one.  \r\nLine two.\t")
    assert all(_LEGAL.match(line) for line in out), out
    assert "\r" not in "".join(out)


def test_empty_quote_still_yields_a_legal_line():
    assert doc_lines("") == ["    ///"]


def test_indent_is_configurable_for_nested_impls():
    assert doc_lines("x", indent="        ") == ["        /// x"]


# --------------------------------------------------------------------------- #
# A field named after a Rust keyword
# --------------------------------------------------------------------------- #

from rust_codegen import Precondition, field_accessor  # noqa: E402


def test_ordinary_field_keeps_its_lowercased_name():
    assert field_accessor("SPE") == "spe"
    assert field_accessor("CEN") == "cen"


def test_keyword_fields_get_svd2rusts_trailing_underscore():
    """svd2rust cannot emit `pub fn priv(&self)`, so it emits `priv_`.
    Spelling the precondition `r.priv()` is a PARSE error, which kills the
    entire chip crate -- L5, H5 and H7-S all carry a PRIV bit and all three
    failed this way."""
    assert field_accessor("PRIV") == "priv_"
    assert field_accessor("TYPE") == "type_"
    assert field_accessor("MATCH") == "match_"


class _Cond:
    """Minimal stand-in for a grammar-v2 FieldCondition."""
    def __init__(self, field, state):
        self.register, self.field, self.state, self.values = "PWR_PRIVCFGR", field, state, []


def test_precondition_on_a_keyword_field_emits_a_legal_call():
    p = Precondition(_Cond("PRIV", "cleared"))
    expr = p.check_expr()
    assert expr == "r.priv_().bit_is_clear()"
    assert "r.priv(" not in expr
