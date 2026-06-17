"""Bug-finding application (Phase 1d).

The layout/SVD-diff arm: run the generator, diff its register info against the
ground-truth SVD, filter to real SVD bugs with the s5 analyzer, group bugs into
reviewer-facing classes, and emit one review CSV per SVD file.

Public surface:
    models   — typed in-memory diff/bug structures (Diff, Bug, BugClass)
    diff     — SVD vs generator comparison → list[Diff]
    classify — analyzer filter + bug-class grouping
    report   — per-SVD review CSV
    pipeline — run_bug_finding(): orchestrates diff → analyze → classify → report
    driver   — CLI entry point
"""
