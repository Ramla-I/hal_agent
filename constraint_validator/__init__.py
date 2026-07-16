"""Constraint Validator (plan §7).

Legs: deterministic quote anchoring + derived context (quote_anchor.py,
§7.1), the closed-book LLM judge (judge.py, §7.0 stage 1), and the
corruption-calibration harness (corruption.py + calibrate.py, §7.2).
The LLM validates; runtime Rust checks; the compiler enforces.
"""
