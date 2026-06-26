"""Vendor-aware access-notation handling for the Validator.

Datasheets denote register/field access with vendor-specific abbreviations (STM, for
example, writes a read/write-with-clear bit as `rc_w0`). The verified datasheets use
only the canonical CMSIS-style labels `read-write` / `read-only` / `write-only`. Without
a translation the Validator rejects a correct `read-write` invariant simply because the
datasheet text says `rc_w0` — this was the single largest residual false-negative class
for *both* models benchmarked (see docs/validator_paper_plan.md).

This module turns the editable mapping in `access_notations.json` into:
  * access_legend(vendor)  -> prompt text telling the model which datasheet codes map to
                              which canonical access type.
  * canonical_access(value, vendor) -> normalise a raw notation to its canonical label
                              (or None if unknown), for non-LLM comparison if needed.

TO ADD/EDIT A VENDOR: edit `access_notations.json` only — no code change required.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Optional

_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "access_notations.json")

CANONICAL = ("read-write", "read-only", "write-only")


@lru_cache(maxsize=None)
def _load(path: str = _JSON_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _vendor_key(vendor: str) -> str:
    """Map a Manufacturer name/slug to a notations key, falling back to 'default'."""
    notations = _load()
    v = (vendor or "").strip().lower()
    return v if v in notations else "default"


def vendor_notations(vendor: str) -> dict:
    """Return {canonical_access: [synonyms...]} for a vendor (or the default block)."""
    return _load()[_vendor_key(vendor)]


def canonical_access(value: str, vendor: str = "default") -> Optional[str]:
    """Normalise a raw access notation (e.g. 'rc_w0', 'RW', 'read/write') to a canonical
    label, or None if not recognised. Case-insensitive, exact-token match (so 'r' does
    not match 'rc_w0'). Falls back to the default block for unknown synonyms.
    """
    if value is None:
        return None
    token = str(value).strip().lower()
    if not token:
        return None
    for block in (vendor_notations(vendor), _load()["default"]):
        for canonical, synonyms in block.items():
            if canonical not in CANONICAL:
                continue
            if token in (s.lower() for s in synonyms):
                return canonical
    return None


def access_legend(vendor: str = "default") -> str:
    """Build the prompt section that tells the Validator which datasheet access codes
    map to which canonical access type for this vendor. Returns "" if the vendor has no
    non-trivial synonyms beyond the canonical names themselves.
    """
    block = vendor_notations(vendor)
    key = _vendor_key(vendor)

    lines = []
    has_extra = False
    for canonical in CANONICAL:
        syns = [s for s in block.get(canonical, []) if s.lower() != canonical]
        if syns:
            has_extra = True
        shown = block.get(canonical, [canonical])
        lines.append(f"  - {canonical}  ⇐  " + ", ".join(shown))
    if not has_extra:
        return ""

    header = f"# ACCESS-TYPE NOTATION ({key.upper()})"
    return (
        f"{header}\n"
        "The datasheet may denote register/field access with vendor-specific "
        "abbreviations. Treat the following as EQUIVALENT to the canonical access type "
        "when validating an `access` invariant:\n"
        + "\n".join(lines)
        + "\nA bit shown as e.g. `rc_w0` (read, cleared by writing 0) is access "
        "`read-write` — it is both readable and writable. Do NOT reject a correct "
        "canonical access value just because the datasheet writes it with one of these "
        "codes; conversely, a genuinely different access type is still wrong."
    )
