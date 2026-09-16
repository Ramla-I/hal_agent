#!/usr/bin/env python3
"""What an enforcement hit looks like — the one place that decides.

A gate fires as a COMPILE ERROR, and the shape of that error depends on how the
gate was built. Until field-level gating shipped there was only one shape, so
every consumer wrote the test inline:

    code == "E0277" and "constrained by its datasheet" in message

Field gating broke that, and because the rule lived in eight copies it was
wrong in eight places, found one at a time. Each miss put real violations in
the bucket that means *the encoding broke something it had no business
touching* -- 295 in the corpus sweep, 50 in the ported HALs -- while the
enforcement counts read LOW, which is the direction least likely to prompt a
second look.

THE TWO SHAPES

WHOLE-REGISTER gate: the marker impl is withheld, so the stock method does not
exist. E0277, and `#[diagnostic::on_unimplemented]` puts the datasheet sentence
in the message:

    `stm32f1::stm32f103::rtc::crh::CRHrs` is modify-constrained by its datasheet

FIELD gate: a witness parameter is added to the field's writer, so calling it is
an ARITY error. E0061, and there is no hook to attach custom text to -- the
message says only "this method takes 1 argument but 0 arguments were supplied".
The witness TYPE is the only thing naming the register, and it appears in a span
LABEL rather than the message:

    argument #1 of type `&CrHsebypFieldWitness` is missing

So a consumer that reads only `message` cannot see a field-gate hit at all.

GENERIC FRICTION is a third case and not a finding: our diagnostic naming an
associated-type projection (`<<ADC as Ptr>::RB as AdcRB>::CR2rs`) rather than a
concrete register. Driver code written generically over register blocks must
declare the marker bound even where nothing is constrained; that is the
encoding's adoption cost, discharged mechanically.

Usage:
    from enforcement import classify_diagnostic
    hit = classify_diagnostic(diag)          # None if not ours
    if hit and not hit.projection: ...       # a real violation
"""
from __future__ import annotations

import re
from typing import NamedTuple

_CONSTRAINED_RE = re.compile(r"`([^`]+)` is (\w+)-constrained by its datasheet")
# `&CrHsebypFieldWitness` -> register Cr, field Hsebyp. The witness is named
# <Register><Field>FieldWitness, both in CamelCase.
_FIELD_WITNESS_RE = re.compile(r"&(\w+?)([A-Z]\w*)FieldWitness")
_SPEC_SUFFIX_RE = re.compile(r"(\w+)rs$")


class Hit(NamedTuple):
    """One firing of a gate."""
    kind: str            # "register" | "field"
    spec: str            # svd2rust spec type, e.g. "CR1rs"
    register: str        # lowercase register, e.g. "cr1"
    field: str           # gated field for a field hit, "" otherwise
    operation: str       # "read" | "write" | "modify"
    projection: bool     # named through an associated type -> generic friction


def _code(diag: dict) -> str:
    """The error code, from either shape.

    Callers pass two things: a raw rustc diagnostic, where `code` is a dict,
    and a flattened record of their own, where it is already a string. Both are
    legitimate and both reach here."""
    c = diag.get("code")
    return (c or {}).get("code", "") if isinstance(c, dict) else (c or "")


def span_labels(diag: dict) -> str:
    """Every span label on a diagnostic, including its children's.

    A field-gate hit identifies its register ONLY here. Consumers that read
    `message` alone were blind to them. A flattened record may have collected
    the labels already, under `labels`."""
    pre = diag.get("labels")
    if isinstance(pre, str):
        return pre
    spans = list(diag.get("spans") or [])
    for ch in diag.get("children") or []:
        spans.extend(ch.get("spans") or [])
    return " ".join(s.get("label") or "" for s in spans)


def _is_projection(name: str) -> bool:
    """`<Self as UartRB>::SRrs` is a placeholder; `stm32f4::…::CCRrs` is not."""
    return " as " in name


def classify_diagnostic(diag: dict) -> "Hit | None":
    """The hit this diagnostic represents, or None if it is not one of ours."""
    code = _code(diag)
    msg = diag.get("message", "") or ""

    m = _CONSTRAINED_RE.search(msg)
    if code == "E0277" and m:
        named, op = m.group(1), m.group(2)
        spec = named.split("::")[-1]
        rm = _SPEC_SUFFIX_RE.search(spec)
        return Hit("register", spec, (rm.group(1).lower() if rm else spec.lower()),
                   "", op, _is_projection(named))

    if code == "E0061":
        fm = _FIELD_WITNESS_RE.search(span_labels(diag))
        if fm:
            # One writer accessor serves write and modify alike, so a field
            # gate's operation is always a write.
            return Hit("field", f"{fm.group(1).upper()}rs",
                       fm.group(1).lower(), fm.group(2).lower(), "write", False)
    return None


def is_ours(diag: dict) -> bool:
    """Did one of our gates produce this error?"""
    return classify_diagnostic(diag) is not None
