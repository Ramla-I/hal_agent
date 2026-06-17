"""Typed in-memory structures for the bug-finding pipeline.

These replace the intermediate CSV round-trips (``register_diff.csv`` /
``field_diff.csv`` / ``*_summary.csv``) that the old diff → analyze flow used to
pass between stages. The pipeline now passes ``list[Diff]`` / ``list[Bug]`` /
``list[BugClass]`` in memory; the only file written is the per-SVD review CSV.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Presence(str, Enum):
    """Where a register/field/value was found."""
    BOTH = "both"                    # present in both SVD and generator output
    SVD_ONLY = "svd_only"            # coverage gap: generator missed it
    GENERATOR_ONLY = "generator_only"  # generator emitted something not in the SVD


class Diff(BaseModel):
    """One structured difference between the SVD and the generator output.

    Covers both register-level diffs (``field is None``) and field-level diffs
    (``field`` set). ``key`` names the differing attribute, e.g. ``reset_value``,
    ``address_offset``, ``size`` (register-level) or ``bit_offset``,
    ``bit_width``, ``enumerated_values`` (field-level).

    For ``presence == BOTH`` both ``svd_value`` and ``generator_value`` are set
    and differ — these are the candidate bugs. For the coverage presences only
    one side is populated.
    """
    peripheral: str
    register: str
    field: Optional[str] = None
    key: str
    svd_value: Optional[str] = None
    generator_value: Optional[str] = None
    presence: Presence = Presence.BOTH

    @property
    def is_field_level(self) -> bool:
        return self.field is not None

    @property
    def is_value_mismatch(self) -> bool:
        """A value present on both sides but differing — a candidate SVD bug."""
        return self.presence == Presence.BOTH

    @property
    def location(self) -> str:
        """Human-readable location, e.g. ``tim2.cr1`` or ``tim2.cr1.cen``."""
        loc = f"{self.peripheral}.{self.register}"
        if self.field:
            loc += f".{self.field}"
        return loc


class BugStatus(str, Enum):
    """Reviewer disposition for a bug row in the review CSV.

    Blank initially; a later submit step consumes only ``APPROVE`` classes.
    ``FALSE_POSITIVE`` records a generator/datasheet mismatch (a generator error,
    not an SVD bug) — kept in the CSV as a noted FP, not dropped.
    """
    PENDING = ""
    APPROVE = "approve"
    REJECT = "reject"
    FALSE_POSITIVE = "false_positive"


class Bug(BaseModel):
    """A value-mismatch diff the analyzer confirmed as a candidate SVD bug,
    enriched with datasheet evidence and confidence.

    The proposed SVD fix is always the generator's value, so reviewer approval is
    a one-click confirm; if the evidence shows the generator's value is wrong, the
    reviewer marks the row ``false_positive`` instead.
    """
    diff: Diff
    confidence: float = 0.0
    datasheet_evidence: str = ""
    status: BugStatus = BugStatus.PENDING

    @property
    def proposed_svd_fix(self) -> Optional[str]:
        return self.diff.generator_value


class BugClass(BaseModel):
    """A reviewer-facing group of bugs that maps 1:1 to a prospective PR.

    Keyed by ``(svd_file, peripheral, key)`` — i.e. all bugs of one type
    (e.g. ``reset_value``) in one peripheral of one SVD cluster together.
    """
    svd_file: str
    peripheral: str
    key: str
    bugs: list[Bug] = []

    @property
    def bug_class_id(self) -> str:
        return f"{self.svd_file}:{self.peripheral}:{self.key}"
