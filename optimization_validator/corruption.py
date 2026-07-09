"""Realistic corruption of register-layout invariants for Validator benchmarking.

The Validator is benchmarked as a noisy binary labeler (paper section "Benchmarking
the Validator as a Noisy Labeler"). To do that we need negative examples that look
like *plausible* extraction mistakes, not obvious garbage. Uniform-random values
(`bit_width=69`) and gibberish names (`vvayurpxfkp`) are trivially rejectable and
inflate specificity, so they tell us nothing about how the Validator behaves on the
confusable errors a real Generator/SVD actually produces.

This module corrupts an invariant *in place* (the original is replaced by its
corrupted version — no true/corrupted pairs) using per-key strategies calibrated to
the value formats observed in the verified datasheets:

    register-level   address_offset   hex  (0x0, 0x8, 0x6C, 0x00000000)
                     reset_value      hex or decimal (0x00000000, 0xFFFF, 0)
                     size             one of {8, 16, 32} (occasionally 64)
    field-level      bit_offset       int in [0, size)
                     bit_width        int in [1, size]
                     access           {read-only, write-only, read-write, reserved}

Field names are corrupted either to a *real sibling* field name from the same
register (the most confusable kind of error) or to a realistic typo of the original.

Every function takes an explicit `rng` (`random.Random`) so corruption is fully
deterministic given a seed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

# Keys that live at register level (field_name is empty) vs. field level.
REGISTER_KEYS = ("address_offset", "reset_value", "size")
FIELD_KEYS = ("bit_offset", "bit_width", "access")

ACCESS_VALUES = ("read-only", "write-only", "read-write", "reserved")
COMMON_SIZES = (8, 16, 32, 64)

_HEX_RE = re.compile(r"^0x[0-9a-fA-F]+$")
_DEC_RE = re.compile(r"^-?\d+$")


@dataclass
class RegisterContext:
    """Per-register layout facts used to make corruptions in-range and confusable.

    Built once per (peripheral, register) from the verified datasheet so that, e.g.,
    a corrupted bit_offset stays inside the register and a corrupted field name is a
    name that genuinely belongs to a *sibling* field of the same register.
    """

    size: Optional[int] = None
    # field_name -> {"bit_offset": int|None, "bit_width": int|None}
    fields: dict = field(default_factory=dict)

    def sibling_names(self, exclude: str) -> list[str]:
        return [n for n in self.fields if n and n != exclude]

    def sibling_values(self, key: str, exclude_field: str, exclude_value) -> list[int]:
        out = []
        for name, attrs in self.fields.items():
            if name == exclude_field:
                continue
            v = attrs.get(key)
            if v is not None and v != exclude_value:
                out.append(v)
        return out


def build_register_contexts(df: pd.DataFrame) -> dict:
    """Index the verified datasheet into per-(peripheral, register) layout facts.

    Expects the verified-datasheet schema: peripheral, register, field_name, key,
    correct_value (plus optional svd_value/agent_value, ignored here).
    """
    contexts: dict = {}
    for (peripheral, register), group in df.groupby(["peripheral", "register"], dropna=False):
        ctx = RegisterContext()
        for _, row in group.iterrows():
            key = row["key"]
            raw = row.get("correct_value")
            field_name = row.get("field_name")
            field_name = "" if pd.isna(field_name) else str(field_name)
            if key == "size":
                ctx.size = _to_int(raw)
            elif key in ("bit_offset", "bit_width") and field_name:
                attrs = ctx.fields.setdefault(field_name, {})
                attrs[key] = _to_int(raw)
            elif key == "access" and field_name:
                ctx.fields.setdefault(field_name, {})
        contexts[(peripheral, register)] = ctx
    return contexts


def _to_int(value) -> Optional[int]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        if _HEX_RE.match(s):
            return int(s, 16)
        return int(s)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Value corruption
# --------------------------------------------------------------------------- #

def _corrupt_hex(s: str, rng) -> str:
    """Flip a single nibble of a hex literal, preserving the 0x prefix and width."""
    body = s[2:]
    if not body:
        return "0x1"
    width = len(body)
    value = int(body, 16)
    # Prefer flipping one nibble so the result is one-digit-off (a realistic typo /
    # transcription slip) rather than an arbitrarily distant number.
    for _ in range(8):
        pos = rng.randrange(width)
        old_digit = (value >> (4 * (width - 1 - pos))) & 0xF
        new_digit = rng.randrange(16)
        if new_digit != old_digit:
            new_value = value & ~(0xF << (4 * (width - 1 - pos)))
            new_value |= new_digit << (4 * (width - 1 - pos))
            if new_value != value:
                return f"0x{new_value:0{width}X}"
    # Degenerate fallback (e.g. width 1, unlucky draws): bump by one.
    return f"0x{(value + 1) & ((1 << (4 * width)) - 1):0{width}X}"


def _corrupt_address_offset(s: str, ctx: RegisterContext, rng) -> str:
    """Nibble-flip, or shift by a register-size stride (a plausible neighbour offset)."""
    if _HEX_RE.match(s) and rng.random() < 0.5:
        stride_bytes = max(1, (ctx.size or 32) // 8)
        steps = rng.choice([-2, -1, 1, 2])
        width = len(s) - 2
        value = int(s, 16) + steps * stride_bytes
        if value < 0:
            value = abs(value)
        return f"0x{value:0{width}X}"
    if _HEX_RE.match(s):
        return _corrupt_hex(s, rng)
    return _corrupt_decimal(s, rng)


def _corrupt_decimal(s: str, rng) -> str:
    value = int(s)
    delta = rng.choice([-2, -1, 1, 2, 4, 8])
    new_value = value + delta
    if new_value == value:
        new_value += 1
    if new_value < 0:
        new_value = abs(new_value) + 1
    return str(new_value)


def _corrupt_reset_value(s: str, rng) -> str:
    if _HEX_RE.match(s):
        # 0 -> a plausible non-zero reset, non-zero -> nibble flip. Both are common
        # real mistakes (missed a non-zero default, or mis-copied one digit).
        if int(s, 16) == 0:
            width = len(s) - 2
            choices = ["1", "F", "FF", "8000"]
            digits = rng.choice(choices)
            return f"0x{int(digits, 16):0{width}X}"
        return _corrupt_hex(s, rng)
    if _DEC_RE.match(s):
        return _corrupt_decimal(s, rng)
    return "0x1"


def _corrupt_size(s: str, rng) -> str:
    current = _to_int(s)
    options = [sz for sz in COMMON_SIZES if sz != current]
    return str(rng.choice(options))


def _corrupt_bit_offset(s: str, ctx: RegisterContext, field_name: str, rng) -> str:
    current = _to_int(s)
    size = ctx.size or 32
    # Half the time, swap in a sibling field's offset (a classic mis-attribution).
    siblings = ctx.sibling_values("bit_offset", field_name, current)
    if siblings and rng.random() < 0.5:
        return str(rng.choice(siblings))
    # Otherwise nudge by a small amount, staying inside the register.
    if current is None:
        return str(rng.randrange(0, max(1, size)))
    for _ in range(8):
        delta = rng.choice([-3, -2, -1, 1, 2, 3])
        candidate = current + delta
        if 0 <= candidate < size and candidate != current:
            return str(candidate)
    return str((current + 1) % max(1, size))


def _corrupt_bit_width(s: str, ctx: RegisterContext, field_name: str, rng) -> str:
    current = _to_int(s)
    size = ctx.size or 32
    offset = (ctx.fields.get(field_name) or {}).get("bit_offset") or 0
    max_width = max(1, size - offset)
    candidates = [w for w in range(1, max_width + 1) if w != current]
    if not candidates:
        candidates = [w for w in (1, 2, 4, 8, 16) if w != current]
    # Bias toward small widths and toward a near neighbour of the true width.
    if current is not None:
        near = [w for w in candidates if abs(w - current) <= 2]
        if near and rng.random() < 0.6:
            return str(rng.choice(near))
    return str(rng.choice(candidates))


def _corrupt_access(s: str, rng) -> str:
    current = (s or "").strip().lower()
    options = [a for a in ACCESS_VALUES if a != current]
    return rng.choice(options)


def corrupt_value(key: str, value, ctx: RegisterContext, field_name: str, rng) -> str:
    """Return a realistic wrong value for `key`, given register-layout context.

    Falls back gracefully for unexpected/empty inputs. Always returns a string that
    differs from the input (best-effort).
    """
    s = "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value).strip()
    if s == "":
        # No verified value to perturb — emit a benign-but-wrong default.
        return "0x1" if key in ("address_offset", "reset_value") else "1"

    if key == "address_offset":
        out = _corrupt_address_offset(s, ctx, rng)
    elif key == "reset_value":
        out = _corrupt_reset_value(s, rng)
    elif key == "size":
        out = _corrupt_size(s, rng)
    elif key == "bit_offset":
        out = _corrupt_bit_offset(s, ctx, field_name, rng)
    elif key == "bit_width":
        out = _corrupt_bit_width(s, ctx, field_name, rng)
    elif key == "access":
        out = _corrupt_access(s, rng)
    elif _HEX_RE.match(s):  # unknown key: nibble fallback
        out = _corrupt_hex(s, rng)
    elif _DEC_RE.match(s):
        out = _corrupt_decimal(s, rng)
    else:
        out = s + "_x"

    # Guarantee a difference: tiny registers / saturated bit fields can occasionally
    # produce the original back (e.g. a 1-bit field's offset). Force a change.
    if str(out).strip() == s:
        out = _force_different(s, rng)
    return out


def _force_different(s: str, rng) -> str:
    if _HEX_RE.match(s):
        width = len(s) - 2
        return f"0x{(int(s, 16) + 1) & ((1 << (4 * width)) - 1) or 1:0{width}X}"
    if _DEC_RE.match(s):
        return str(int(s) + 1)
    return s + "_x"


# --------------------------------------------------------------------------- #
# Field-name corruption
# --------------------------------------------------------------------------- #

def _typo(name: str, rng) -> str:
    """A one-edit typo: transpose, drop, duplicate, or substitute a character."""
    if len(name) < 2:
        return name + name  # duplicate single char
    mode = rng.choice(["transpose", "drop", "dup", "sub"])
    i = rng.randrange(len(name) - 1)
    if mode == "transpose":
        chars = list(name)
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
        return "".join(chars)
    if mode == "drop":
        return name[:i] + name[i + 1:]
    if mode == "dup":
        return name[:i] + name[i] + name[i:]
    # substitute with an adjacent-ish letter/digit
    repl = rng.choice("abcdefghijklmnopqrstuvwxyz0123456789")
    return name[:i] + repl + name[i + 1:]


def corrupt_field_name(field_name: str, ctx: RegisterContext, rng) -> str:
    """Replace a field name with a real sibling (preferred) or a realistic typo."""
    siblings = ctx.sibling_names(exclude=field_name)
    if siblings and rng.random() < 0.6:
        return rng.choice(siblings)
    typo = _typo(field_name, rng)
    if typo == field_name:
        typo = field_name + "x"
    return typo


# --------------------------------------------------------------------------- #
# Row-level corruption
# --------------------------------------------------------------------------- #

def corrupt_row(row: dict, ctx: RegisterContext, rng, name_corruption_prob: float = 0.3) -> dict:
    """Corrupt a single invariant row, replacing it with a wrong version.

    Returns a new dict with the corrupted value/field name plus bookkeeping columns:
      is_correct (False), corruption_type ("value"|"field_name").

    For field-level rows we corrupt the *name* with probability `name_corruption_prob`
    (a sibling/typo), otherwise the value. Register-level rows always corrupt the value.
    """
    out = dict(row)
    field_name = row.get("field_name")
    field_name = "" if field_name is None or (isinstance(field_name, float) and pd.isna(field_name)) else str(field_name)

    # Stash the ground truth (pre-corruption) so the curation-candidate export can show a
    # human the correct value/name when they write the supporting datasheet excerpt.
    out["original_value"] = row.get("correct_value")
    out["original_field_name"] = field_name

    if field_name and rng.random() < name_corruption_prob:
        out["field_name"] = corrupt_field_name(field_name, ctx, rng)
        out["corruption_type"] = "field_name"
        if "alt_name" in out:
            # The fabricated name has no datasheet alias; blanking also prevents leaking
            # the real field's datasheet name (which would betray the corruption).
            out["alt_name"] = ""
    else:
        out["correct_value"] = corrupt_value(row["key"], row.get("correct_value"), ctx, field_name, rng)
        out["corruption_type"] = "value"
    out["is_correct"] = False
    return out
