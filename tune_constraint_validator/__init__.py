"""Constraint-validator tuning harness (plan §7.2).

The constraint validator *itself* lives in ``core/``: deterministic quote
anchoring (``core/quote_anchor.py``, §7.1) and the closed-book LLM judge
(``core/constraint_validator.py``, §7.0 stage 1). This package holds only the
*tuning* leg that calibrates that judge — the corruption generator
(``corruption.py``) and the calibration harness (``calibrate.py``, §7.2). It
imports the product (never the reverse), mirroring how ``optimization_validator/``
tunes ``core/s4_validator.py``.
"""
